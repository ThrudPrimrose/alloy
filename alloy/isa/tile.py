# Copyright 2026 ETH Zurich and the Alloy authors.
"""The tile ISA (A11): a matrix tile operation, such as a 64x64x64 GEMM, answered per target with the loop of
instructions that fits it, the layout and descriptors its loads need, and a C or C++ program that uses Alloy's tile
functions on row-major tiles, checked against a host reference before it is printed.

Targets: ``sm90`` (GH200), ``gfx942`` (MI300A), and ``cpu``. A CPU has no swizzle, and the evaluated CPUs have neither
AMX nor SME, so ``mma`` on a CPU is an FMA loop over blocks of four rows that the host compiler vectorizes (the
fallback).

    python -m alloy.isa tile cpu gemm 64 64 64 --in f32 --acc f32
"""

import pathlib
import subprocess
import tempfile
from dataclasses import dataclass, field

__all__ = ["CPU_TYPES", "TilePlan", "cpu_plan", "plan", "verify"]

HERE = pathlib.Path(__file__).parent
#: Element types a CPU tile takes: (input, accumulator) pairs with a C spelling each.
CPU_TYPES = {
    ("f32", "f32"): ("float", "float"),
    ("f64", "f64"): ("double", "double"),
    ("f32", "f64"): ("float", "double"),
}
#: Rows of A one CPU micro-kernel step keeps in registers.
CPU_MR = 4
#: Relative error a product may show against the f64 reference, per accumulator type.
TOLERANCE = {"f32": 1e-5, "f64": 1e-12}
TIMEOUT = 300


@dataclass(frozen=True, slots=True)
class TilePlan:
    """A tile operation on one target: the shape and types, the instruction loop as steps, the descriptors and the
    layout its operands need, the program that runs it once against a reference, and the check's outcome
    (``run``: matched the reference here; ``compiled``: built, no device to run it; ``unverified``)."""

    target: str
    m: int
    n: int
    k: int
    in_type: str
    acc_type: str
    steps: tuple[str, ...]
    layout: str
    program: str
    descriptors: dict[str, str] = field(default_factory=dict)
    verified: str = "unverified"
    detail: str = ""


def cpu_header() -> str:
    return (HERE / "alloy_tile_cpu.h").read_text()


def cpu_plan(m: int, n: int, k: int, in_type: str, acc_type: str) -> TilePlan:
    """The CPU fallback: ``alloy_mma`` from ``alloy_tile_cpu.h`` on row-major A (m x k), B (k x n), C (m x n)."""
    if (in_type, acc_type) not in CPU_TYPES:
        legal = ", ".join(f"--in {i} --acc {a}" for i, a in CPU_TYPES)
        raise KeyError(f"a CPU tile takes {legal}; no AMX or SME here, so f16 and bf16 have no CPU MMA")
    a_type, c_type = CPU_TYPES[in_type, acc_type]
    steps = (
        f"no matrix unit on this CPU: alloy_mma_{in_type}_{acc_type} is the fallback, an FMA loop",
        f"for each block of {CPU_MR} rows of C, for each k: broadcast A[i][k] of the {CPU_MR} rows and multiply-add "
        "row k of B into the block (the compiler vectorizes along n)",
    )
    layout = "row-major A, B, and C with leading dimensions lda, ldb, ldc; no swizzle on a CPU"
    program = cpu_program(m, n, k, a_type, c_type, in_type, acc_type)
    return TilePlan("cpu", m, n, k, in_type, acc_type, steps, layout, program)


def cpu_program(m: int, n: int, k: int, a_type: str, c_type: str, in_type: str, acc_type: str) -> str:
    """A program that runs the tile once on deterministic inputs and prints the largest relative error against an
    f64 reference; it exits 1 above the accumulator's tolerance."""
    return f"""#include <math.h>
#include <stdio.h>
#include "alloy_tile_cpu.h"

enum {{ M = {m}, N = {n}, K = {k} }};
static {a_type} A[M * K], B[K * N];
static {c_type} C[M * N];

int main(void) {{
  for (int i = 0; i < M * K; ++i) A[i] = ({a_type})((i % 13) - 6) / 8;
  for (int i = 0; i < K * N; ++i) B[i] = ({a_type})((i % 7) - 3) / 4;
  for (int i = 0; i < M * N; ++i) C[i] = ({c_type})((i % 5) - 2);
  double want[M * N];
  for (int i = 0; i < M; ++i)
    for (int j = 0; j < N; ++j) {{
      double s = C[i * N + j];
      for (int p = 0; p < K; ++p) s += (double)A[i * K + p] * (double)B[p * N + j];
      want[i * N + j] = s;
    }}
  alloy_mma_{in_type}_{acc_type}(M, N, K, A, K, B, N, C, N);
  double worst = 0.0;
  for (int i = 0; i < M * N; ++i) {{
    double rel = fabs((double)C[i] - want[i]) / fmax(1.0, fabs(want[i]));
    if (rel > worst) worst = rel;
  }}
  printf("%.3e\\n", worst);
  return worst <= {TOLERANCE[acc_type]} ? 0 : 1;
}}
"""


def verify(plan_: TilePlan) -> TilePlan:
    """``plan_`` with its program compiled and run here: ``run`` when it matched the reference."""
    with tempfile.TemporaryDirectory(prefix="alloy_tile_") as folder:
        source, binary = pathlib.Path(folder) / "tile.c", pathlib.Path(folder) / "tile"
        source.write_text(plan_.program)
        (pathlib.Path(folder) / "alloy_tile_cpu.h").write_text(cpu_header())
        built = subprocess.run(
            ["cc", "-O3", "-march=native", "-std=c11", str(source), "-o", str(binary), "-lm"],
            capture_output=True, text=True, check=False, timeout=TIMEOUT,
        )  # fmt: skip
        if built.returncode != 0:
            return replace_check(plan_, "unverified", f"did not compile: {built.stderr.strip()[-500:]}")
        ran = subprocess.run([str(binary)], capture_output=True, text=True, check=False, timeout=TIMEOUT)
    error = ran.stdout.strip()
    if ran.returncode != 0:
        return replace_check(plan_, "unverified", f"relative error {error} against the f64 reference")
    return replace_check(plan_, "run", f"relative error {error} against the f64 reference")


def replace_check(plan_: TilePlan, verified: str, detail: str) -> TilePlan:
    return TilePlan(
        plan_.target, plan_.m, plan_.n, plan_.k, plan_.in_type, plan_.acc_type, plan_.steps, plan_.layout,
        plan_.program, plan_.descriptors, verified, detail,
    )  # fmt: skip


def plan(target: str, m: int, n: int, k: int, in_type: str, acc_type: str) -> TilePlan:
    """The tile plan of ``target``; a target or shape it cannot take is a ``KeyError`` naming what it takes."""
    if min(m, n, k) <= 0:
        raise KeyError(f"a tile has positive extents; got {m}x{n}x{k}")
    if target == "cpu":
        return cpu_plan(m, n, k, in_type, acc_type)
    raise KeyError(f"tile targets: cpu (sm90 and gfx942 follow); got {target!r}")
