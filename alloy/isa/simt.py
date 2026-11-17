# Copyright 2026 ETH Zurich and the Alloy authors.
"""The CUDA and HIP rows (``simt.toml``) and their verdicts (``simt_verified.toml``).

A row is device code for one thread or one warp. Each is checked by a generated program: one block of one warp runs the
row on every thread, and the host compares each thread's value with the row's C reference. A dialect whose GPU this
machine has is run; otherwise its program is compiled for the target archs and recorded as compiled, not run.

    python -m alloy.isa.simt verify   # rerun every row, rewrite simt_verified.toml
"""

import argparse
import dataclasses
import datetime
import functools
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import tomllib

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from alloy import gpu

__all__ = ["DIALECTS", "Row", "Verdict", "digest", "merged", "program", "rows", "verdicts", "verify"]

HERE = pathlib.Path(__file__).parent
ROWS_PATH = HERE / "simt.toml"
VERDICTS_PATH = HERE / "simt_verified.toml"
DIALECTS = ("cuda", "hip")
#: Threads per warp the program runs: NVIDIA's warp, CDNA's wavefront (MI200, MI300).
LANES = {"cuda": 32, "hip": 64}
#: The archs a HIP row compiles for when this machine has no AMD GPU to run it on.
HIP_ARCHS = ("gfx90a", "gfx942")
DOMAIN = (-2.0, 2.0)
#: Per dialect and element type: the C type of the arrays x and y a row moves, and the host's conversion from float.
ELEMENTS = {
    ("cuda", "f32"): ("float", "(float)"), ("hip", "f32"): ("float", "(float)"),
    ("cuda", "f16"): ("__half", "__float2half_rn"), ("hip", "f16"): ("__half", "__float2half_rn"),
    ("cuda", "bf16"): ("__nv_bfloat16", "__float2bfloat16_rn"), ("hip", "bf16"): ("__hip_bfloat16", "__float2bfloat16"),
}  # fmt: skip
TIMEOUT = 300

API = {
    "cuda": {"malloc": "cudaMalloc", "memcpy": "cudaMemcpy", "h2d": "cudaMemcpyHostToDevice",
             "d2h": "cudaMemcpyDeviceToHost", "sync": "cudaDeviceSynchronize", "memset": "cudaMemset",
             "error": "cudaGetLastError", "ok": "cudaSuccess", "string": "cudaGetErrorString"},
    "hip": {"malloc": "hipMalloc", "memcpy": "hipMemcpy", "h2d": "hipMemcpyHostToDevice",
            "d2h": "hipMemcpyDeviceToHost", "sync": "hipDeviceSynchronize", "memset": "hipMemset",
            "error": "hipGetLastError", "ok": "hipSuccess", "string": "hipGetErrorString"},
}  # fmt: skip


@dataclass(frozen=True, slots=True, config=ConfigDict(extra="forbid"))
class Row:
    op: str
    kind: str
    cuda: str
    hip: str
    ref: str
    tol: float
    domain: tuple[float, float] = DOMAIN
    check: str = "all"
    #: The element type the row computes in or moves (its arguments a, b, c and its checked result are f32).
    dtype: str = "f32"
    note: str = ""
    #: The request op the row answers when its key differs (the key load_f16 answers load at f16).
    spells: str = ""
    #: Statements the check runs after a "thread" row to set ``out`` from what the row wrote; not part of the row.
    read: str = ""

    def spelled(self, dialect: str) -> str:
        return self.cuda if dialect == "cuda" else self.hip

    def answers(self) -> str:
        return self.spells or self.op


@dataclass(frozen=True, slots=True, config=ConfigDict(extra="forbid"))
class Verdict:
    """One row's check: ``ok`` None means compiled but not run (no such GPU here). ``digest`` is :func:`digest` of
    the row as it was checked."""

    op: str
    dialect: str
    basis: str
    ok: bool | None = None
    rel: float | None = None
    error: str = ""
    digest: str = ""


@functools.lru_cache(maxsize=None, typed=True)
def table(path: pathlib.Path = ROWS_PATH) -> dict:
    return tomllib.loads(path.read_text())


def rows() -> tuple[Row, ...]:
    return tuple(Row(op=op, **row) for op, row in table()["ops"].items())


@functools.lru_cache(maxsize=None, typed=True)
def recorded(path: pathlib.Path = VERDICTS_PATH) -> dict:
    return tomllib.loads(path.read_text()) if path.is_file() else {}


def digest(row: Row, dialect: str) -> str:
    """What a check of ``row`` on ``dialect`` ran: the spelling, the inputs, the reference, and what it compared."""
    checked = [row.kind, row.spelled(dialect), row.ref, list(row.domain), row.check, row.tol, row.dtype]
    checked += [row.read] if row.read else []  # rows without a read keep the digest of their recorded runs
    return hashlib.sha256(json.dumps(checked).encode()).hexdigest()[:16]


def verdicts(path: pathlib.Path = VERDICTS_PATH) -> dict[tuple[str, str], Verdict]:
    """The recorded verdict of each row as it is now: a record of a row changed since its check is stale and left
    out, so the row is unverified until it runs again."""
    current = {(row.op, dialect): digest(row, dialect) for row in rows() for dialect in DIALECTS}
    found = (Verdict(**v) for v in recorded(path).get("verdicts", []))
    return {(v.op, v.dialect): v for v in found if current.get((v.op, v.dialect)) == v.digest}


def bindings(dialect: str) -> str:
    """The names a row's code uses and what to bind them to in a kernel of any block size."""
    return (
        f"bind: lanes = warpSize ({LANES[dialect]} on {dialect}); lane = threadIdx.x % warpSize (the lane in its "
        "warp, not threadIdx.x once a block holds several warps); v = this lane's input, a, b, c = its operands; "
        "out = the result; x, y = the arrays a load reads and a store writes, i = this thread's element"
    )


def program(row: Row, dialect: str) -> str:
    """A program that runs ``row`` on one warp of ``dialect`` and prints the worst relative error over the threads
    it checks (only lane 0 for a row whose result lands there)."""
    api, lanes = API[dialect], LANES[dialect]
    lo, hi = row.domain
    includes = "\n".join(f"#include <{h}>" for h in ["cstdio", "cmath", *table()["target"][dialect]["headers"]])
    if dialect == "hip":
        includes = "#include <hip/hip_runtime.h>\n" + includes
    body = f"out = {row.spelled(dialect)};" if row.kind == "lane" else f"{row.spelled(dialect)} {row.read}".rstrip()
    reference = (
        row.ref
        if row.kind == "warp"
        else f"for (int k = 0; k < lanes; k++) {{ float a = A(k), b = B(k), c = C; (void)b; (void)c; want[k] = {row.ref}; }}"
    )
    elem, convert = ELEMENTS[dialect, row.dtype]
    checked = "1" if row.check == "first" else "lanes"
    return f"""{includes}
#define LANES {lanes}
__host__ __device__ static inline float A(int k) {{ return {lo}f + ({hi}f - {lo}f) * (k + 0.5f) / LANES; }}
__host__ __device__ static inline float B(int k) {{ return 0.5f + 1.5f * ((k * 7 + 3) % LANES + 0.5f) / LANES; }}
#define C 0.25f
static inline float wide_ref(int lane) {{ return (float)((lane / 4) * 4) * 0.5f; }}

typedef {elem} elem;

__global__ void row(const float* in, float* outv, const float* wide, float* total, const elem* x, elem* y) {{
    const int lane = threadIdx.x, lanes = LANES, i = lane;
    const float a = A(lane), b = B(lane), c = C, v = in[lane];
    (void)a; (void)b; (void)c; (void)v; (void)wide; (void)total; (void)x; (void)y; (void)i; (void)lanes;
    float out = 0.0f;
    {body}
    outv[lane] = out;
}}

int main() {{
    const int lanes = LANES;
    float in[LANES], got[LANES], want[LANES], wide[LANES];
    for (int k = 0; k < lanes; k++) {{ in[k] = A(k); wide[k] = k * 0.5f; want[k] = 0.0f; }}
    elem xs[LANES];
    for (int k = 0; k < lanes; k++) xs[k] = {convert}(A(k));
    float *d_in, *d_out, *d_wide, *d_total;
    elem *d_x, *d_y;
    {api["malloc"]}((void**)&d_x, sizeof xs); {api["malloc"]}((void**)&d_y, 8 * sizeof xs);
    {api["memcpy"]}(d_x, xs, sizeof xs, {api["h2d"]});
    {api["memset"]}(d_y, 0, 8 * sizeof xs);
    {api["malloc"]}((void**)&d_in, sizeof in); {api["malloc"]}((void**)&d_out, sizeof got);
    {api["malloc"]}((void**)&d_wide, sizeof wide); {api["malloc"]}((void**)&d_total, sizeof(float));
    {api["memcpy"]}(d_in, in, sizeof in, {api["h2d"]});
    {api["memcpy"]}(d_wide, wide, sizeof wide, {api["h2d"]});
    {api["memset"]}(d_total, 0, sizeof(float));
    row<<<1, LANES>>>(d_in, d_out, d_wide, d_total, d_x, d_y);
    {api["sync"]}();
    if ({api["error"]}() != {api["ok"]}) {{ printf("ALLOY-SIMT error=launch\\n"); return 2; }}
    {api["memcpy"]}(got, d_out, sizeof got, {api["d2h"]});
    {reference}
    double worst = 0.0;
    for (int k = 0; k < {checked}; k++) {{
        double scale = fabs((double)want[k]) > 1.0 ? fabs((double)want[k]) : 1.0;
        double rel = fabs((double)got[k] - (double)want[k]) / scale;
        if (rel != rel || rel > worst) worst = rel;  // a NaN stays the worst
    }}
    printf("ALLOY-SIMT rel=%.6g\\n", worst);
    return 0;
}}
"""


def build(source: str, dialect: str, folder: pathlib.Path, run: bool) -> list[str]:
    """The compile command of ``source``: a program for this machine's GPU when ``run``, else an object for
    :data:`HIP_ARCHS` (or the default CUDA arch)."""
    unit = folder / ("row.cu" if dialect == "cuda" else "row.hip")
    unit.write_text(source)
    if dialect == "cuda":
        arch = ["-arch=native"] if run else []
        return (
            ["nvcc", "-O2", *arch, str(unit), "-o", str(folder / "row")]
            if run
            else ["nvcc", "-O2", "-c", str(unit), "-o", str(folder / "row.o")]
        )
    if run:
        return ["hipcc", "-O2", "--offload-arch=native", str(unit), "-o", str(folder / "row")]
    return ["hipcc", "-O2", *(f"--offload-arch={a}" for a in HIP_ARCHS), "-c", str(unit), "-o", str(folder / "row.o")]


def check(row: Row, dialect: str, runs: bool) -> Verdict:
    """``row`` compiled for ``dialect``, and run when ``runs`` (this machine has the dialect's GPU)."""
    if shutil.which(table()["target"][dialect]["compiler"]) is None:
        return Verdict(row.op, dialect, f"no {table()['target'][dialect]['compiler']} on PATH")
    with tempfile.TemporaryDirectory(prefix="alloy_simt_") as tmp:
        folder = pathlib.Path(tmp)
        command = build(program(row, dialect), dialect, folder, runs)
        built = subprocess.run(command, capture_output=True, text=True, check=False, timeout=TIMEOUT)
        if built.returncode != 0:
            return Verdict(row.op, dialect, "compile", ok=False, error=built.stderr.strip()[-600:])
        if not runs:
            archs = ", ".join(HIP_ARCHS) if dialect == "hip" else "the default arch"
            return Verdict(row.op, dialect, f"compiled for {archs}, not run (no such GPU here)")
        done = subprocess.run([str(folder / "row")], capture_output=True, text=True, check=False, timeout=TIMEOUT)
    line = next((x for x in done.stdout.splitlines() if x.startswith("ALLOY-SIMT rel=")), "")
    if done.returncode != 0 or not line:
        return Verdict(row.op, dialect, "run", ok=False, error=(done.stdout + done.stderr).strip()[-600:])
    rel = float(line.split("=", 1)[1])
    return Verdict(row.op, dialect, f"ran on {gpu_name(dialect)}", ok=rel <= row.tol, rel=rel)


@functools.lru_cache(maxsize=None, typed=True)
def gpu_name(dialect: str) -> str:
    argv = ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"] if dialect == "cuda" else ["amdgpu-arch"]
    done = subprocess.run(argv, capture_output=True, text=True, check=False)
    return done.stdout.strip().splitlines()[0] if done.returncode == 0 and done.stdout.strip() else dialect


def runnable() -> frozenset[str]:
    """The dialects whose GPU this machine has."""
    try:
        return frozenset({gpu.native_dialect()})
    except RuntimeError:
        return frozenset()


def verdicts_text(found: list[Verdict]) -> str:
    head = [
        "# Written by `python -m alloy.isa.simt verify`: every simt.toml row compiled and, where the GPU is here, run.",
        f'run = "{datetime.datetime.now(datetime.UTC).date().isoformat()}"',
        "",
    ]
    body = []
    for v in found:
        fields = {
            "op": v.op,
            "dialect": v.dialect,
            "ok": v.ok,
            "basis": v.basis,
            "rel": v.rel,
            "error": v.error or None,
            "digest": v.digest or None,
        }
        body += ["[[verdicts]]", *(f"{k} = {json.dumps(x)}" for k, x in fields.items() if x is not None), ""]
    return "\n".join(head + body)


def merged(new: Verdict, old: Verdict | None) -> Verdict:
    """``new`` with the runs of ``old`` on other GPUs of its dialect kept beside it (an MI250X's and an MI300A's run of
    one HIP row): correct only if every run is, at the worst error of them."""
    if old is None or new.ok is None or old.ok is None:
        return new
    runs = new.basis.split("; ")
    others = [part for part in old.basis.split("; ") if part.startswith("ran on ") and part not in runs]
    if not others:
        return new
    rel = max((r for r in (new.rel, old.rel) if r is not None), default=None)
    return Verdict(
        new.op, new.dialect, "; ".join([*runs, *others]), new.ok and old.ok, rel, new.error or old.error, new.digest
    )


def verify() -> list[Verdict]:
    here = runnable()
    kept = verdicts()
    found = [
        dataclasses.replace(check(row, dialect, dialect in here), digest=digest(row, dialect))
        for row in rows()
        for dialect in DIALECTS
    ]
    # a row this machine can only compile keeps the verdict of the machine that ran it
    found = [
        kept[v.op, v.dialect] if v.ok is None and (v.op, v.dialect) in kept and kept[v.op, v.dialect].ok else v
        for v in found
    ]
    # a row run here keeps its runs on the dialect's other GPUs
    found = [merged(v, kept.get((v.op, v.dialect))) for v in found]
    VERDICTS_PATH.write_text(verdicts_text(found))
    recorded.cache_clear()
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m alloy.isa.simt", description=__doc__)
    parser.add_argument("command", choices=("verify",))
    parser.parse_args(argv)
    found = verify()
    for v in found:
        state = {True: "ok", False: "FAIL", None: "unverified"}[v.ok]
        print(f"{v.op:12} {v.dialect:5} {state:10} {v.basis} {v.rel if v.rel is not None else v.error[:160]}")
    return 1 if any(v.ok is False for v in found) else 0


if __name__ == "__main__":
    sys.exit(main())
