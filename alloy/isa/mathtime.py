# Copyright 2026 ETH Zurich and the Alloy authors.
"""Times a math kernel on this host: nanoseconds per element of ``y[i] += f(x[i])`` over an array that fits the
first-level cache, for a kernel inlined in the loop and for the library calls the compiler makes of the same loop.
A time belongs to the machine that measured it, so none is recorded in ``mathkernels.toml``.
"""

import dataclasses
import functools
import pathlib
import re
import subprocess
import tempfile

from alloy.isa.mathcheck import built, filled
from alloy.isa.mathkernels import Kernel, Renderer, kernel, ladder, render, target_of
from alloy.isa.validate import HEADERS, c_compiler, c_flags, host_can_run

__all__ = ["Timed", "time_function", "time_kernel", "time_library"]

ELEMENTS = 4096
RUN_TIMEOUT = 120  # seconds
LINE = re.compile(r"NS=(\S+)")

DRIVER = """
#define _GNU_SOURCE
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <time.h>
typedef @C@ lane;
void alloy_bench(const lane *xs, const lane *x2, lane *ys, int n);
#define N @ELEMENTS@
static lane xs[N], x2[N], ys[N];
static uint64_t state = 0x9e3779b97f4a7c15ULL;
static double uniform(void) {
    state ^= state << 13; state ^= state >> 7; state ^= state << 17;
    return (state >> 11) * 0x1p-53;
}
static double now(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (double)t.tv_sec + 1e-9 * (double)t.tv_nsec;
}
int main(void) {
    for (int i = 0; i < N; i++) {
        xs[i] = (lane)(@LO@ + (@HI@ - @LO@) * uniform());
        x2[i] = (lane)(@YLO@ + (@YHI@ - @YLO@) * uniform());
    }
    double best = INFINITY;
    for (int rep = 0; rep < 9; rep++) {
        for (int i = 0; i < N; i++) ys[i] = 0;  /* the sum stays finite: no rep pays for an overflow */
        double start = now();
        for (int pass = 0; pass < 64; pass++) alloy_bench(xs, x2, ys, N);
        double each = (now() - start) / (64.0 * N);
        if (each < best) best = each;
    }
    printf("NS=%.4f SINK=%g\\n", best * 1e9, (double)ys[7]);
    return 0;
}
"""

INLINED = """
#include <math.h>
#include <@HEADER@>
typedef @C@ lane;
@KERNEL@
void alloy_bench(const lane *xs, const lane *x2, lane *ys, int n) {
    (void)x2;
    for (int i = 0; i + (int)@LANES@ <= n; i += (int)@LANES@)
        @STEP@;
}
"""

LIBRARY = """
#define _GNU_SOURCE
#include <math.h>
typedef @C@ lane;
void alloy_bench(const lane *restrict xs, const lane *restrict x2, lane *restrict ys, int n) {
    (void)x2;
    for (int i = 0; i < n; i++) ys[i] += @CALL@;
}
"""

#: What makes each compiler turn the loop's call into its vector library's.
VECTOR_CALLS = {"gcc": ("-O3", "-ffast-math"), "clang": ("-O3", "-ffast-math", "-fveclib=libmvec")}


@dataclasses.dataclass(slots=True, frozen=True)
class Timed:
    """One way to compute a function and what an element costs with it here. ``error_ulp`` is None for a library."""

    name: str
    ns: float
    error_ulp: float | None = None
    intrinsics: int | None = None


def bounds(k: Kernel) -> dict[str, str]:
    """The driver's input ranges: the kernel's first grid, which every level of a function shares."""
    grid = k.grids[0]
    return {"LO": repr(grid.lo), "HI": repr(grid.hi), "YLO": repr(grid.ylo), "YHI": repr(grid.yhi)}


def run(unit: str, unit_flags: list[str], k: Kernel, isa: str) -> tuple[float, str]:
    """Nanoseconds per element of ``unit``'s loop, and the symbols it leaves to the linker."""
    cc = str(c_compiler())
    with tempfile.TemporaryDirectory(prefix="alloy_time_") as tmp:
        folder = pathlib.Path(tmp)
        (folder / "k.c").write_text(unit)
        (folder / "d.c").write_text(
            filled(DRIVER, {"C": Renderer(isa, k.dtype).fields["c"], "ELEMENTS": str(ELEMENTS), **bounds(k)})
        )
        built([cc, *unit_flags, "-c", str(folder / "k.c"), "-o", str(folder / "k.o")], k, isa)
        built([cc, "-O2", str(folder / "d.c"), str(folder / "k.o"), "-lm", "-o", str(folder / "k")], k, isa)
        undefined = subprocess.run(["nm", "-u", str(folder / "k.o")], capture_output=True, text=True, check=False)
        done = subprocess.run([str(folder / "k")], capture_output=True, text=True, check=False, timeout=RUN_TIMEOUT)
    match = LINE.search(done.stdout)
    if match is None:
        raise RuntimeError(f"{k.name} on {isa} printed no time: {done.stderr[:300]}")
    return float(match.group(1)), undefined.stdout


def time_kernel(k: Kernel, isa: str) -> Timed | None:
    """``k`` inlined in the loop; None when the host cannot run ``isa``."""
    target = target_of(isa)
    if not host_can_run(target, k.dtype) or c_compiler() is None:
        return None
    r = Renderer(target, k.dtype)
    spelled = render(k, target)
    arguments = ", ".join(r.call("load", f"{name} + i") for name in ("xs", "x2")[: len(k.args)])
    step = r.call("store", "ys + i", r.call("add", r.call("load", "ys + i"), f"{k.name}({arguments})"))
    holes = {"HEADER": HEADERS[target], "C": r.fields["c"], "KERNEL": spelled.source, "LANES": r.fields["lanes"]}
    ns, _ = run(filled(INLINED, {**holes, "STEP": step}), ["-O2", *c_flags(target, k.dtype)], k, target)
    return Timed(k.level, ns, k.error_ulp, spelled.intrinsics)


def time_library(k: Kernel, isa: str) -> list[Timed]:
    """The loop with ``k``'s function as a call: scalar libm, and the vector library when the compiler takes it."""
    target = target_of(isa)
    cc = c_compiler()
    if not host_can_run(target, k.dtype) or cc is None:
        return []
    suffix = "f" if k.dtype == "f32" else ""
    call = f"{k.fn}{suffix}({', '.join(('xs[i]', 'x2[i]')[: len(k.args)])})"
    unit = filled(LIBRARY, {"C": Renderer(target, k.dtype).fields["c"], "CALL": call})
    scalar, _ = run(unit, ["-O2", "-fno-tree-vectorize", *c_flags(target, k.dtype)], k, target)
    out = [Timed("libm (scalar)", scalar)]
    family = "clang" if "clang" in pathlib.Path(cc).resolve().name else "gcc"
    vector, undefined = run(unit, [*VECTOR_CALLS[family], *c_flags(target, k.dtype)], k, target)
    if "_ZGV" in undefined:  # the libmvec mangling: without it the compiler left the call scalar
        out.append(Timed("libmvec", vector))
    return out


@functools.lru_cache(maxsize=None, typed=True)
def time_function(fn: str, dtype: str, isa: str) -> tuple[Timed, ...]:
    """Every kernel of ``fn`` and the library calls, timed once per process; empty when the host cannot run ``isa``."""
    kernels = [timed for k in ladder(fn, dtype) if (timed := time_kernel(k, isa)) is not None]
    if not kernels:
        return ()
    return (*kernels, *time_library(kernel(fn, dtype, "relaxed"), isa))
