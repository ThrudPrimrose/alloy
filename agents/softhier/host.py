"""The judge of the SoftHier agent study (SPEC.md): puts a task's inputs in HBM, builds a submission's kernel.c into the
fixed host program with the SDK, runs it on GVSoC, compares the output with the float64 program, and prints one JSON
verdict: ok, the error, and the simulated time of the kernel call. Standalone: python3 inside the SoftHier v1 image
(SOFTHIER_SDK and SOFTHIER_GVSOC set, the GCC 14 RISC-V toolchain on PATH), the standard library only.

    python3 host.py grade TASK FOLDER          # FOLDER/kernel.c; the verdict on stdout and in FOLDER/verdict.json
    python3 host.py reference TASK FOLDER      # writes the scalar reference kernel.c of TASK (the baseline)
    python3 host.py tasks                      # the task names

Timing: GVSoC's performance counter (flex_timer_start/end around the call, after a global barrier on both sides),
in simulated ns. A run is deterministic, so one run per program.
"""

import json
import math
import os
import pathlib
import random
import re
import struct
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
TASKS = {t["name"]: t for t in json.loads((HERE / "tasks.json").read_text())}
#: Elements of every input of a map or reduce task; the GEMM task is GEMM x GEMM x GEMM.
N, GEMM = 65536, 64
CLUSTERS = 4
SEED = 2026
#: |got - ref| <= ABS + REL |ref| per element (map, the Tensix study's bound); a sum may also drift by
#: 2^-23 sqrt(N) |ref| (fp32 reassociation); the f16 GEMM: max |got - ref| / max |ref| <= MMA (softhier.toml mma_f16).
ABS, REL, MMA = 1e-5, 1e-3, 1e-3
FLAGS = ["-mabi=ilp32d", "-mcmodel=medlow", "-march=rv32imafdv_zfh_zvfh", "-O3", "-ffast-math", "-fno-builtin",
         "-fno-tree-vectorize", "-fno-common", "-ffunction-sections"]  # fmt: skip
TARGET = "pulp.chips.soft_hier_old.flex_cluster"
BUILD_TIMEOUT, RUN_TIMEOUT = 300, 3600
# The tasks' calls in the reference's C. Newlib's libm reads tables and errno state that the linker places beside the
# code, where the cores cannot load (the simulation stops at once), so the reference carries its own (REFERENCE_MATH)
# and the judge links no libm.
CALLS = {"log": "alloy_ref_logf", "sin": "alloy_ref_sinf", "cos": "alloy_ref_cosf", "sqrt": "__builtin_sqrtf",
         "abs": "__builtin_fabsf"}  # fmt: skip
REFERENCE_MATH = """static inline float alloy_ref_sin_poly(float r) {  // |r| <= pi/4: Taylor to r^9
    const float r2 = r * r;
    return r * (1.0f + r2 * (-1.6666667e-1f + r2 * (8.3333333e-3f + r2 * (-1.9841270e-4f + r2 * 2.7557319e-6f))));
}
static inline float alloy_ref_cos_poly(float r) {  // |r| <= pi/4: Taylor to r^8
    const float r2 = r * r;
    return 1.0f + r2 * (-0.5f + r2 * (4.1666667e-2f + r2 * (-1.3888889e-3f + r2 * 2.4801587e-5f)));
}
static inline float alloy_ref_trig(float x, int cosine) {  // Cody-Waite: x = k pi/2 + r, quadrant k mod 4
    const float t = x * 0.63661977f;
    const int k = (int)(t + (t >= 0.0f ? 0.5f : -0.5f));
    const float r = (x - (float)k * 1.5707964f) + (float)k * 4.3711388e-8f;
    const int q = (k + cosine) & 3;
    return q == 0 ? alloy_ref_sin_poly(r) : q == 1 ? alloy_ref_cos_poly(r) : q == 2 ? -alloy_ref_sin_poly(r)
                                                                              : -alloy_ref_cos_poly(r);
}
static inline float alloy_ref_sinf(float x) { return alloy_ref_trig(x, 0); }
static inline float alloy_ref_cosf(float x) { return alloy_ref_trig(x, 1); }
static inline float alloy_ref_logf(float x) {  // x > 0: x = m 2^e, m in [sqrt(1/2), sqrt(2)), log m = 2 atanh(s)
    union { float f; uint32_t u; } v = {x};
    int e = (int)(v.u >> 23) - 127;
    v.u = (v.u & 0x7fffffu) | 0x3f800000u;
    float m = v.f;
    if (m > 1.4142135f) { m *= 0.5f; e += 1; }
    const float s = (m - 1.0f) / (m + 1.0f), s2 = s * s;
    return (float)e * 0.69314718f + 2.0f * s * (1.0f + s2 * (3.3333333e-1f + s2 * (0.2f + s2 * (1.4285714e-1f + s2 * 1.1111111e-1f))));
}
"""


def f32(x: float) -> float:
    return struct.unpack("<f", struct.pack("<f", x))[0]


def f16(x: float) -> float:
    return struct.unpack("<e", struct.pack("<e", x))[0]


def words32(xs: list[float]) -> list[int]:
    return [struct.unpack("<I", struct.pack("<f", x))[0] for x in xs]


def inputs(task: dict) -> dict[str, list[float]]:
    """The task's inputs by name: float32 (f16 for the GEMM) drawn uniformly from each input's range, seeded by name."""
    draw = random.Random(f"{task['name']}-{SEED}")
    count = GEMM * GEMM if task["kind"] == "gemm" else N
    cast = f16 if task["kind"] == "gemm" else f32
    return {name: [cast(draw.uniform(lo, hi)) for _ in range(count)] for name, lo, hi in task["inputs"]}


def evaluate(expression: str, values: dict[str, float]) -> float:
    """One element of a task expression in float64 (names are the task's inputs; calls as in CALLS)."""
    scope = {"log": math.log, "sin": math.sin, "cos": math.cos, "sqrt": math.sqrt, "abs": abs} | values
    return float(eval(expression, {"__builtins__": {}}, scope))


def reference(task: dict, data: dict[str, list[float]]) -> list[float]:
    """The float64 result: a map's output array, a reduce's sum (one value), the GEMM's C + A x B."""
    if task["kind"] == "gemm":
        a, b, c = data["A"], data["B"], data["C"]
        return [c[i * GEMM + j] + sum(a[i * GEMM + p] * b[p * GEMM + j] for p in range(GEMM))
                for i in range(GEMM) for j in range(GEMM)]  # fmt: skip
    names = [name for name, _, _ in task["inputs"]]
    lines = [tuple(part.strip() for part in line.split("=", 1)) for line in task["program"]]
    if task["kind"] == "reduce":
        ((_, expression),) = lines
        inner = re.fullmatch(r"sum\((.*)\)", expression).group(1)  # type: ignore[union-attr]
        return [math.fsum(evaluate(inner, {n: data[n][i] for n in names}) for i in range(N))]
    results = []
    for i in range(N):  # the lines in order; a name a line assigns is a temporary of this element
        values = {n: data[n][i] for n in names}
        for target, expression in lines:
            values[target] = evaluate(expression, values)
        results.append(values[task["output"]])
    return results


def operands(task: dict) -> list[str]:
    """The kernel's arguments in0..in2, out, by the task's names: inputs in order, then the output (for the GEMM and an
    in-place map, the output is also an input)."""
    names = [name for name, _, _ in task["inputs"]]
    return names + [""] * (3 - len(names)) if task["kind"] != "gemm" else ["A", "B", "", ""]


def program(task: dict, kernel: str, data: dict[str, list[float]]) -> str:
    """The fixed host around ``kernel``: the inputs in HBM (initialized data links there), the call on every core,
    the timer around it, and cluster 0 printing the output words."""
    gemm = task["kind"] == "gemm"
    width = 16 if gemm else 32
    lines, args = [], []
    for name in operands(task)[:3]:
        if not name:
            args.append("0")
            continue
        bits = [struct.unpack("<H", struct.pack("<e", x))[0] for x in data[name]] if gemm else words32(data[name])
        lines.append(f"uint{width}_t alloy_in_{name}[{len(bits)}] = {{{', '.join(map(hex, bits))}}};")
        args.append(f"(uint64_t)(uintptr_t)alloy_in_{name}")
    output, count = task["output"], (GEMM * GEMM if gemm else N if task["kind"] == "map" else CLUSTERS)
    if output in data:  # C += A x B, an in-place map: the output starts as that input
        out = f"alloy_in_{output}"
        if gemm:
            bits = [struct.unpack("<H", struct.pack("<e", x))[0] for x in data[output]]
            lines.append(f"uint16_t alloy_in_{output}[{count}] = {{{', '.join(map(hex, bits))}}};")
    else:
        out = "alloy_out"
        # .data like the inputs: a zero-initialized array would go to .bss, which GVSoC can neither preload nor reach
        lines.append(f'__attribute__((section(".data"))) uint{width}_t alloy_out[{count}] = {{0}};')
    chunk = min(count * width // 8, 0x40000)
    return f"""#include <stdint.h>
#include <stddef.h>
#include "flex_runtime.h"
#include "flex_printf.h"
#include "flex_dma_pattern.h"

{kernel}

{chr(10).join(lines)}

int main() {{
    flex_barrier_xy_init();
    flex_global_barrier_xy();
    if (flex_get_cluster_id() == 0 && flex_is_first_core()) flex_timer_start();
    alloy_kernel({", ".join(args)}, (uint64_t)(uintptr_t){out}, {GEMM if gemm else N});
    flex_global_barrier_xy();
    if (flex_get_cluster_id() == 0 && flex_is_first_core()) flex_timer_end();
    flex_global_barrier_xy();
    if (flex_get_cluster_id() == 0) {{  // the output back through TCDM, {chunk} bytes at a time
        for (uint32_t at = 0; at < {count * width // 8}u; at += {chunk}u) {{
            const uint32_t bytes = {count * width // 8}u - at < {chunk}u ? {count * width // 8}u - at : {chunk}u;
            if (flex_is_dm_core()) {{
                flex_dma_async_1d(local(0), (uint64_t)(uintptr_t){out} + at, bytes);
                flex_dma_async_wait_all();
            }}
            flex_intra_cluster_sync();
            if (flex_is_first_core())
                for (uint32_t i = 0; i < bytes / {width // 8}; ++i)
                    printf("ALLOY %x\\n", (uint32_t)((volatile uint{width}_t*)local(0))[i]);
            flex_intra_cluster_sync();
        }}
    }}
    flex_global_barrier_xy();
    flex_eoc(0);
    return 0;
}}
"""


def compare(task: dict, words: list[int], ref: list[float]) -> tuple[bool, float, str]:
    """Whether the printed output words hold the bound, the error (map: worst |got-ref| / (ABS + REL |ref|); reduce:
    |got-ref| / allowance; GEMM: max |got-ref| / max |ref|), and why not."""
    if task["kind"] == "gemm":
        got = [struct.unpack("<e", struct.pack("<H", w & 0xFFFF))[0] for w in words]
    else:
        got = [struct.unpack("<f", struct.pack("<I", w))[0] for w in words]
    want = len(ref) if task["kind"] != "reduce" else CLUSTERS
    if len(got) != want:
        return False, math.inf, f"printed {len(got)} output values, not {want}"
    if not all(math.isfinite(g) for g in got):
        return False, math.inf, "the output holds inf or nan"
    if task["kind"] == "gemm":
        rel = max(abs(g - r) for g, r in zip(got, ref, strict=True)) / max(max(abs(r) for r in ref), 1e-30)
        return rel <= MMA, rel, "" if rel <= MMA else f"max error {rel:.3g} of max |C| above {MMA}"
    if task["kind"] == "reduce":
        total, want_sum = math.fsum(got), ref[0]
        allowance = ABS + REL * abs(want_sum) + 2**-23 * math.sqrt(N) * abs(want_sum)
        error = abs(total - want_sum) / allowance
        return error <= 1, error, "" if error <= 1 else f"sum {total!r}, want {want_sum!r}"
    errors = [abs(g - r) / (ABS + REL * abs(r)) for g, r in zip(got, ref, strict=True)]
    worst = max(range(len(errors)), key=errors.__getitem__)
    ok = errors[worst] <= 1
    return ok, errors[worst], "" if ok else f"element {worst}: {got[worst]!r}, want {ref[worst]!r}"


def toolchain(folder: pathlib.Path, source: str) -> str:
    """Builds program.c in ``folder`` into softhier.elf; the compiler's errors, or ''."""
    sdk = pathlib.Path(os.environ["SOFTHIER_SDK"], "runtime", "runtime")
    (folder / "program.c").write_text(source)
    argv = ["riscv32-unknown-elf-gcc", "-I", str(sdk / "include"), "-T", str(sdk / "flex_memory.ld"), "-nostartfiles",
            *FLAGS, "-Wl,--gc-sections", "-o", "softhier.elf", str(sdk / "flex_start.s"), "program.c"]  # fmt: skip
    done = subprocess.run(argv, cwd=folder, capture_output=True, text=True, check=False, timeout=BUILD_TIMEOUT)
    if done.returncode == 0:
        return ""
    found = [line for line in done.stderr.splitlines() if "error" in line]
    return "\n".join(found[:20]) if found else done.stderr[-2000:]


def simulate(folder: pathlib.Path) -> tuple[str, int]:
    """GVSoC on folder/softhier.elf: its output and exit code."""
    gvsoc = pathlib.Path(os.environ["SOFTHIER_GVSOC"], "install", "bin", "gvsoc")
    env = os.environ | {"SOFTHIER_ARCH_FILE": str(HERE / "alloy_v1.py")}
    argv = [str(gvsoc), f"--target={TARGET}", "--binary", "softhier.elf", "run", "--work-dir", str(folder)]
    done = subprocess.run(argv, cwd=folder, env=env, capture_output=True, text=True, check=False, timeout=RUN_TIMEOUT)
    return done.stdout + done.stderr, done.returncode


def grade(name: str, folder: pathlib.Path) -> dict:
    task = TASKS[name]
    verdict: dict = {"task": name, "ok": False, "error_ratio": None, "ns": None, "error": ""}
    kernel = folder / "kernel.c"
    if not kernel.is_file():
        return verdict | {"error": "no kernel.c"}
    data = inputs(task)
    with tempfile.TemporaryDirectory(prefix="softhier_grade_") as tmp:
        work = pathlib.Path(tmp)
        if problem := toolchain(work, program(task, kernel.read_text(), data)):
            return verdict | {"error": f"build: {problem}"}
        try:
            output, code = simulate(work)
        except subprocess.TimeoutExpired:
            return verdict | {"error": f"the simulation ran past {RUN_TIMEOUT} s"}
    timed = re.search(r"Execution period is (\d+) ns", output)
    if code != 0:
        return verdict | {"error": f"gvsoc exit {code}: {output[-1500:]}"}
    words = [int(line.split()[1], 16) for line in output.splitlines() if line.startswith("ALLOY ")]
    if not words:
        return verdict | {"error": f"no output printed; the simulator said: {output[-1500:]}"}
    ok, ratio, why = compare(task, words, reference(task, data))
    return verdict | {"ok": ok, "error_ratio": ratio, "ns": int(timed.group(1)) if timed else None, "error": why}


def c_expression(expression: str, arrays: list[str]) -> str:
    """A task expression as C: the ``arrays`` as their element ``name[i]``, other names as scalars."""
    text = re.sub(r"\b(\d+\.\d*|\d+)\b(?![\w.])", lambda m: f"{float(m.group(1))!r}f", expression)
    text = re.sub(r"\b(" + "|".join(CALLS) + r")\(", lambda m: f"{CALLS[m.group(1)]}(", text)
    return re.sub(r"\b([A-Za-z_]\w*)\b(?!\s*\()", lambda m: f"{m.group(1)}[i]" if m.group(1) in arrays else m.group(1),
                  text)  # fmt: skip


def reference_kernel(task: dict) -> str:
    """The baseline: plain scalar C on the two compute cores of every cluster (the DM core moves the data)."""
    if task["kind"] == "gemm":
        return f"""// Scalar reference: cluster c computes rows [16c, 16c + 16) of C += A x B, f32 sums rounded to f16 once.
void alloy_kernel(uint64_t a, uint64_t b, uint64_t in2, uint64_t c, uint32_t n) {{
    const uint32_t rows = n / {CLUSTERS}, row0 = flex_get_cluster_id() * rows;
    _Float16 *sa = (_Float16*)local(0), *sb = sa + rows * n, *sc = sb + n * n;
    if (flex_is_dm_core()) {{
        flex_dma_async_1d(local(0), a + 2 * row0 * n, 2 * rows * n);
        flex_dma_async_1d(local(2 * rows * n), b, 2 * n * n);
        flex_dma_async_1d(local(2 * (rows * n + n * n)), c + 2 * row0 * n, 2 * rows * n);
        flex_dma_async_wait_all();
    }}
    flex_intra_cluster_sync();
    if (!flex_is_dm_core())
        for (uint32_t i = flex_get_core_id(); i < rows; i += 2)
            for (uint32_t j = 0; j < n; ++j) {{
                float s = (float)sc[i * n + j];
                for (uint32_t p = 0; p < n; ++p) s += (float)sa[i * n + p] * (float)sb[p * n + j];
                sc[i * n + j] = (_Float16)s;
            }}
    flex_intra_cluster_sync();
    if (flex_is_dm_core()) {{
        flex_dma_async_1d(c + 2 * row0 * n, local(2 * (rows * n + n * n)), 2 * rows * n);
        flex_dma_async_wait_all();
    }}
    flex_intra_cluster_sync();
}}
"""
    names = [name for name, _, _ in task["inputs"]]
    lines = [tuple(part.strip() for part in line.split("=", 1)) for line in task["program"]]
    target = task["output"]
    reduce = task["kind"] == "reduce"
    arrays = [*names, target]
    if reduce:
        ((_, expression),) = lines
        expression = re.fullmatch(r"sum\((.*)\)", expression).group(1)  # type: ignore[union-attr]
    body = "".join(f"const float {t} = {c_expression(e, arrays)}; " for t, e in lines if t != target)
    body += next(f"{target}[i] = {c_expression(e, arrays)};" for t, e in lines if t == target) if not reduce else ""
    params = [*(f"uint64_t {n}_hbm" for n in names), *(f"uint64_t unused{i}" for i in range(3 - len(names)))]
    loads = "".join(f"        flex_dma_async_1d(local({4 * k} * part), {n}_hbm + 4 * first, 4 * part);\n"
                    for k, n in enumerate(names))  # fmt: skip
    views = "".join(f"    float* {n} = (float*)local({4 * k} * part);\n" for k, n in enumerate(names))
    out_view = "" if target in names else f"    float* {target} = (float*)local({4 * len(names)} * part);\n"
    out_at = names.index(target) if target in names else len(names)
    if reduce:
        compute = f"""    if (!flex_is_dm_core()) {{
        float s = 0.0f;
        for (uint32_t i = flex_get_core_id(); i < part; i += 2) s += {c_expression(expression, names)};
        partial[flex_get_core_id()] = s;
    }}
    flex_intra_cluster_sync();
    if (flex_is_dm_core()) {{
        partial[2] = partial[0] + partial[1];
        flex_dma_async_1d(out_hbm + 4 * flex_get_cluster_id(), (uint64_t)(uintptr_t)&partial[2], 4);
        flex_dma_async_wait_all();
    }}"""
        views += f"    float* partial = (float*)local({4 * len(names)} * part);\n"
        out_view = ""
    else:
        compute = f"""    if (!flex_is_dm_core())
        for (uint32_t i = flex_get_core_id(); i < part; i += 2) {{ {body} }}
    flex_intra_cluster_sync();
    if (flex_is_dm_core()) {{
        flex_dma_async_1d(out_hbm + 4 * first, local({4 * out_at} * part), 4 * part);
        flex_dma_async_wait_all();
    }}"""
    return (
        REFERENCE_MATH
        + f"""// Scalar reference of {task["name"]}: each cluster's share of the {"sum" if reduce else "elements"} on its two compute cores.
void alloy_kernel({", ".join(params)}, uint64_t out_hbm, uint32_t n) {{
    const uint32_t part = n / {CLUSTERS}, first = flex_get_cluster_id() * part;
{views}{out_view}    if (flex_is_dm_core()) {{
{loads}        flex_dma_async_wait_all();
    }}
    flex_intra_cluster_sync();
{compute}
    flex_intra_cluster_sync();
}}
"""
    )


def main(argv: list[str]) -> int:
    if argv[:1] == ["tasks"]:
        print("\n".join(TASKS))
        return 0
    if len(argv) != 3 or argv[0] not in ("grade", "reference") or argv[1] not in TASKS:
        print(__doc__, file=sys.stderr)
        return 64
    folder = pathlib.Path(argv[2])
    folder.mkdir(parents=True, exist_ok=True)
    if argv[0] == "reference":
        (folder / "kernel.c").write_text(reference_kernel(TASKS[argv[1]]))
        return 0
    verdict = grade(argv[1], folder)
    (folder / "verdict.json").write_text(json.dumps(verdict, indent=1))
    print(json.dumps(verdict))
    return 0 if verdict["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
