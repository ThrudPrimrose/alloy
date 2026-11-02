# Copyright 2026 ETH Zurich and the Alloy authors.
"""Measures a math kernel: compiles it into a driver that samples its grids against a wider libm reference, and on
``strict`` kernels also compares the special values with libm: NaN, infinities and signed zeros must match exactly.
"""

import concurrent.futures
import dataclasses
import pathlib
import re
import subprocess
import tempfile

from alloy.isa.mathkernels import LEVELS, Grid, Kernel, Renderer, functions, kernel, literal, render
from alloy.isa.validate import (
    COMPILE_TIMEOUT,
    CROSS,
    HEADERS,
    Verdict,
    c_compiler,
    c_flags,
    compile_unit,
    emulated,
    host_can_run,
    target_compiler,
)

__all__ = ["Measured", "compiles", "measure", "validate_kernel", "validate_kernels"]

SAMPLES = 1 << 17
GATE_SAMPLES = 1 << 14
#: A kernel's re-measured error may exceed the recorded one by this factor.
SLACK = 1.5
EMULATED_TIMEOUT = 600  # seconds
LINE = re.compile(r"ULP=(\S+) ABS=(\S+) X=(\S+) Y=(\S+) SPECIAL=(\d+)")

DRIVER = """
#define _GNU_SOURCE
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
typedef @C@ lane;
typedef @REFTYPE@ ref_t;
void alloy_run(const lane *xs, const lane *ys, lane *vs);
int alloy_lanes(void);
#define MAX_LANES 64  /* the longest vector: SVE at 2048 bits, f32 */
static int LANES;
static uint64_t state = 0x9e3779b97f4a7c15ULL;
static double uniform(void) {
    state ^= state << 13; state ^= state >> 7; state ^= state << 17;
    return (state >> 11) * 0x1p-53;
}
static double draw(double lo, double hi, int kind) {
    double u = uniform();
    if (kind == 0) return lo + (hi - lo) * u;
    double m = exp(log(lo) + (log(hi) - log(lo)) * u);
    if (kind == 2) return m;
    if (kind == 3) {
        double k = rint(m / 1.5707963267948966);
        double x = k * 1.5707963267948966;
        for (int i = (int)(uniform() * 5); i > 0; i--) x = nextafter(x, uniform() < 0.5 ? -INFINITY : INFINITY);
        return uniform() < 0.5 ? x : -x;
    }
    return uniform() < 0.5 ? m : -m;
}
static double max_ulp = 0, max_abs = 0, worst_x = 0, worst_y = 0;
static long special = 0;
static double spacing(ref_t r) {
    lane m = (lane)fabsl((long double)r);
    return (double)(nextafter@SUFFIX@(m, (lane)INFINITY) - m);
}
static void compare(lane v, ref_t r, lane x, lane y) {
    double ulp, a = 0;
    lane rounded = (lane)r;  /* an overflow of the lane is the expected result, not an error */
    if ((isnan(rounded) && isnan(v)) || v == rounded) ulp = 0;
    else if (isnan(v) || isnan(rounded) || isinf(v) || isinf(rounded)) ulp = a = INFINITY;
    else {
        ulp = (double)(fabsl((long double)v - (long double)r) / (long double)spacing(r));
        a = (double)fabsl((long double)v - (long double)r);
    }
    if (ulp > max_ulp) { max_ulp = ulp; worst_x = x; worst_y = y; }
    if (a > max_abs) max_abs = a;
}
static int same(lane a, lane b) {
    if (isnan(a) || isnan(b)) return isnan(a) && isnan(b);
    if (a == 0 || b == 0 || isinf(a) || isinf(b)) return a == b && signbit(a) == signbit(b);
    return fabsl((long double)a - (long double)b) <= 4 * spacing(b);
}
static lane xs[MAX_LANES], ys[MAX_LANES], vs[MAX_LANES];
static void run(void) { alloy_run(xs, ys, vs); }
static void sweep(double lo, double hi, int kind, double ylo, double yhi) {
    for (long i = 0; i < @SAMPLES@; i += LANES) {
        for (int j = 0; j < LANES; j++) {
            xs[j] = (lane)draw(lo, hi, kind);
            ys[j] = (lane)(yhi > ylo ? ylo + (yhi - ylo) * uniform() : 0);
@CLIP@
        }
        run();
        for (int j = 0; j < LANES; j++) compare(vs[j], @REF@, xs[j], ys[j]);
    }
}
int main(void) {
    LANES = alloy_lanes();
@GRIDS@
    static const lane sp[] = {@SPECIALS@};
    int n = sizeof(sp) / sizeof(sp[0]);
    for (int i = 0; i < n * @ARGS2@; i++) {
        for (int j = 0; j < LANES; j++) {
            xs[j] = sp[(i / @ARGS2@ + j) % n];
            ys[j] = sp[(i + j) % n];
        }
        run();
        for (int j = 0; j < LANES; j++)
            if (!same(vs[j], @SCALAR@)) {
                special++;
                if (special < 4) fprintf(stderr, "x=%g y=%g v=%g\\n", (double)xs[j], (double)ys[j], (double)vs[j]);
            }
    }
    printf("ULP=%.6g ABS=%.6g X=%.17g Y=%.17g SPECIAL=%ld\\n", max_ulp, max_abs, worst_x, worst_y, special);
    return 0;
}
"""

#: Built apart from the driver, so flags under test reach the kernel and not the error arithmetic.
UNIT = """
#include <math.h>
#include <@HEADER@>
typedef @C@ lane;
@KERNEL@
void alloy_run(const lane *xs, const lane *ys, lane *vs) {
    (void)ys;
@CALL@
}
int alloy_lanes(void) { return (int)@LANES@; }
"""

KINDS = {"lin": 0, "log": 1, "logp": 2, "near": 3}


@dataclasses.dataclass(slots=True, frozen=True)
class Measured:
    """What the driver saw: the worst error, where, and how many special values differ from libm."""

    ulp: float
    abs: float
    x: float
    y: float
    special: int


def reference(k: Kernel) -> str:
    """The wider libm call ``k`` is measured against."""
    wide, cast = ("l", "(long double)") if k.dtype == "f64" else ("", "(double)")
    arguments = ", ".join(f"{cast}{name}s[j]" for name in k.args)
    return f"(ref_t){k.fn}{wide}({arguments})"


def clip(k: Kernel) -> str:
    """For ``pow``: keep y*log(x) inside the exponent's range."""
    if len(k.args) != 2:
        return ""
    limit = 700.0 if k.dtype == "f64" else 87.0
    logarithm = "double l = fabs((double)ys[j] * log((double)xs[j]));"
    return f"            {{ {logarithm} if (l > {limit}) ys[j] = (lane)((double)ys[j] * {limit} / l); }}"


def grid_line(g: Grid) -> str:
    bounds = (literal(g.lo, "f64"), literal(g.hi, "f64"), KINDS[g.kind], literal(g.ylo, "f64"), literal(g.yhi, "f64"))
    return f"    sweep({', '.join(map(str, bounds))});"


def filled(template: str, holes: dict[str, str]) -> str:
    for key, value in holes.items():
        template = template.replace(f"@{key}@", value)
    return template


def driver(k: Kernel, isa: str, samples: int) -> tuple[str, str]:
    """The C sources of ``k`` for ``isa``: the kernel unit, then the driver."""
    r = Renderer(isa, k.dtype)
    f64 = k.dtype == "f64"
    computed = f"{k.name}({', '.join(r.call('load', f'{name}s') for name in k.args)})"
    scalar_args = ", ".join(f"{name}s[j]" for name in k.args)
    holes = {
        "HEADER": HEADERS[isa],
        "C": r.fields["c"],
        "REFTYPE": "long double" if f64 else "double",
        "KERNEL": render(k, isa).source,
        "LANES": r.fields["lanes"],
        "SUFFIX": "" if f64 else "f",
        "CALL": f"    {r.call('store', 'vs', computed)};",
        "SAMPLES": str(samples),
        "CLIP": clip(k),
        "REF": reference(k),
        "GRIDS": "\n".join(grid_line(g) for g in k.grids),
        "SPECIALS": ", ".join(literal(v, k.dtype) for v in k.specials or (0.0,)),
        "ARGS2": str(max(len(k.specials), 1)) if len(k.args) == 2 else "1",
        "SCALAR": f"{k.fn}{'' if f64 else 'f'}({scalar_args})" if k.guard or k.specials else "vs[j]",
    }
    return filled(UNIT, holes), filled(DRIVER, holes)


def built(command: list[str], k: Kernel, isa: str) -> None:
    done = subprocess.run(command, capture_output=True, text=True, check=False, timeout=COMPILE_TIMEOUT)
    if done.returncode != 0:
        raise RuntimeError(f"{k.name} on {isa} does not build: {done.stderr.strip()[:600]}")


def measure(k: Kernel, isa: str, samples: int = SAMPLES, flags: tuple[str, ...] = ()) -> Measured | None:
    """Run ``k`` on this host, under qemu for an aarch64 ``isa``; None when neither can execute ``isa``."""
    arm = emulated(isa)
    if arm is None and (not host_can_run(isa, k.dtype) or c_compiler() is None):
        return None
    with tempfile.TemporaryDirectory(prefix="alloy_math_") as tmp:
        folder = pathlib.Path(tmp)
        unit, main = driver(k, isa, samples)
        (folder / "k.c").write_text(unit)
        (folder / "d.c").write_text(main)
        cc, machine, launcher = arm or (str(c_compiler()), c_flags(isa, k.dtype), [])
        link = [flag for flag in machine if flag == "-static"]
        unit_flags = [flag for flag in machine if flag != "-static"]
        built([cc, "-O2", *flags, *unit_flags, "-c", str(folder / "k.c"), "-o", str(folder / "k.o")], k, isa)
        built([cc, "-O2", *link, str(folder / "d.c"), str(folder / "k.o"), "-lm", "-o", str(folder / "k")], k, isa)
        exe = folder / "k"
        run = subprocess.run(
            [*launcher, str(exe)], capture_output=True, text=True, check=False, timeout=EMULATED_TIMEOUT
        )
    match = LINE.search(run.stdout)
    if match is None:
        raise RuntimeError(f"{k.name} on {isa} printed nothing: {run.stderr[:300]}")
    ulp, abs_err, x, y, special = match.groups()
    return Measured(float(ulp), float(abs_err), float(x), float(y), int(special))


def compiles(k: Kernel, isa: str) -> bool:
    """Whether a compiler is there to take ``k`` for an aarch64 ``isa``; it raises when ``k`` does not build."""
    cc = target_compiler(isa)
    if cc is None:
        return False
    compile_unit(
        f"#include <math.h>\n#include <{HEADERS[isa]}>\n{render(k, isa).source}\n", cc, [f"-march={CROSS[isa]}"]
    )
    return True


def validate_kernel(fn: str, dtype: str, level: str, isa: str, samples: int = GATE_SAMPLES) -> Verdict:
    """The gate on one kernel: run it where the host can, cross-compile it where it cannot."""
    k = kernel(fn, dtype, level)
    try:
        if isa in CROSS and emulated(isa) is None and not host_can_run(isa, dtype):
            return Verdict(None, "cross-compiled, never run", "builds" if compiles(k, isa) else "no cross compiler")
        seen = measure(k, isa, samples)
    except (RuntimeError, subprocess.TimeoutExpired) as exc:
        return Verdict(False, "kernel build", str(exc))
    if seen is None:
        return Verdict(None, f"host cannot run {isa}/{dtype}", "")
    return judged(k, seen, "kernel under qemu" if isa in CROSS else "kernel vs wider libm")


def judged(k: Kernel, seen: Measured, basis: str) -> Verdict:
    """A measurement against the kernel's record: its ulp within :data:`SLACK`, no special value off libm."""
    ok = seen.ulp <= k.error_ulp * SLACK and seen.special == 0
    specials = f", {seen.special} special values off libm" if k.specials else ""
    return Verdict(ok, basis, f"{seen.ulp:.4g} ulp (recorded {k.error_ulp:.4g}){specials}")


def validate_kernels() -> list[tuple[str, Verdict]]:
    """Every kernel on every ISA; (id, verdict) pairs."""
    ids = [
        (fn, dtype, level, isa) for fn in functions() for dtype in ("f64", "f32") for level in LEVELS for isa in HEADERS
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        verdicts = list(pool.map(lambda key: validate_kernel(*key), ids))
    return [("/".join(key), verdict) for key, verdict in zip(ids, verdicts, strict=True)]
