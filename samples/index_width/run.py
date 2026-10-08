# Copyright 2026 ETH Zurich and the Alloy authors.
"""Time each kernel under four index-width renderings, per compiler and size, and write their C++.

Arms: int64 (default), counters32 (int32 loop counters), helpers32 (int32 ``_idx`` helpers), all32 (both).
Arms alternate back to back so drift hits all of them equally. Threads come from OMP_NUM_THREADS.

Usage: OMP_NUM_THREADS=16 python run.py [--reps 20] [--kernels row_gather stencil3d]"""

import argparse
import os
import pathlib
import platform
import subprocess
import time
from collections.abc import Callable

import dace
import numpy as np
from dace.config import set_temporary

import kernels

HERE = pathlib.Path(__file__).parent
COMPILERS = {"gcc": "g++", "clang": "clang++-21"}
ARMS = {
    "int64": ("int64", "inferred"),
    "counters32": ("int64", "int32"),
    "helpers32": ("int32", "inferred"),
    "all32": ("int32", "int32"),
}
FLAGS = "-O3 -march=native"
Inputs = dict[str, np.ndarray | int]


def gather_rows_inputs(rows: int, width: int, reps: int, rng: np.random.Generator) -> Inputs:
    return dict(
        table=rng.random((rows, width)),
        idx=rng.permutation(rows).astype(np.int64),
        out=np.zeros((rows, width)),
        N=rows,
        M=width,
        R=rows,
        T=reps,
    )


def gather_elements_inputs(n: int, reps: int, rng: np.random.Generator) -> Inputs:
    return dict(table=rng.random(n), idx=rng.permutation(n).astype(np.int64), out=np.zeros(n), N=n, R=n, T=reps)


def stencil2d_inputs(n: int, m: int, reps: int, rng: np.random.Generator) -> Inputs:
    return dict(a=rng.random((n, m)), out=np.zeros((n, m)), N=n, M=m, T=reps)


def stencil3d_inputs(n: int, reps: int, rng: np.random.Generator) -> Inputs:
    return dict(a=rng.random((n, n, n)), out=np.zeros((n, n, n)), N=n, M=n, K=n, T=reps)


# kernel -> (program, [(size label, input factory)]); cache ~0.5 MiB, screen ~64 MiB (4x LLC), large ~256 MiB per array.
KERNELS: dict[str, tuple[dace.frontend.python.parser.DaceProgram, list[tuple[str, Callable]]]] = {
    "row_gather": (
        kernels.row_gather,
        [
            ("cache", lambda g: gather_rows_inputs(512, 64, 2000, g)),
            ("screen", lambda g: gather_rows_inputs(1 << 16, 64, 4, g)),
            ("large", lambda g: gather_rows_inputs(1 << 19, 64, 1, g)),
        ],
    ),
    "element_gather": (
        kernels.element_gather,
        [
            ("cache", lambda g: gather_elements_inputs(1 << 15, 2000, g)),
            ("screen", lambda g: gather_elements_inputs(1 << 22, 8, g)),
            ("large", lambda g: gather_elements_inputs(1 << 25, 1, g)),
        ],
    ),
    "stencil2d": (
        kernels.stencil2d,
        [
            ("cache", lambda g: stencil2d_inputs(160, 160, 2000, g)),
            ("screen", lambda g: stencil2d_inputs(2048, 2048, 8, g)),
            ("large", lambda g: stencil2d_inputs(5792, 5792, 1, g)),
        ],
    ),
    "stencil3d": (
        kernels.stencil3d,
        [
            ("cache", lambda g: stencil3d_inputs(32, 2000, g)),
            ("screen", lambda g: stencil3d_inputs(160, 8, g)),
            ("large", lambda g: stencil3d_inputs(320, 1, g)),
        ],
    ),
}


def configured(compiler: str, index_ctype: str, loop_index_type: str):
    return (
        set_temporary("compiler", "cpu", "implementation", value="experimental_readable"),
        set_temporary("compiler", "cpu", "codegen_params", "index_ctype", value=index_ctype),
        set_temporary("compiler", "cpu", "codegen_params", "loop_index_type", value=loop_index_type),
        set_temporary("compiler", "cpu", "executable", value=compiler),
        set_temporary("compiler", "cpu", "args", value=FLAGS),
    )


def build(program, compiler: str, kernel: str, arm: str):
    """Compile one arm and write its kernel translation unit to code/<kernel>/<arm>.cpp (compiler independent)."""
    sdfg = program.to_sdfg(simplify=True)
    sdfg.name = f"{kernel}_{arm}"
    a, b, c, d, e = configured(compiler, *ARMS[arm])
    with a, b, c, d, e:
        frame = next(o for o in sdfg.generate_code() if o.language == "cpp")
        (HERE / "code" / kernel / f"{arm}.cpp").write_text(frame.clean_code)
        return sdfg.compile()


def median_ci(samples: list[float]) -> tuple[float, float, float]:
    """Median and a distribution-free 95% CI from order statistics."""
    s = np.sort(samples)
    n = len(s)
    half = 1.96 * np.sqrt(n) / 2
    return float(np.median(s)), float(s[max(int(n / 2 - half), 0)]), float(s[min(int(np.ceil(n / 2 + half)), n - 1)])


def version(compiler: str) -> str:
    return subprocess.run([compiler, "--version"], capture_output=True, text=True, check=True).stdout.splitlines()[0]


def time_size(progs: dict, factory: Callable, reps: int) -> dict[str, tuple[float, float, float]]:
    """Every arm reads and writes the SAME buffers: per-arm buffers land at different addresses, and the
    cache-set conflicts that follow moved stencil3d by 30% between arms that emit identical loops."""
    inputs = factory(np.random.default_rng(0))
    times: dict[str, list[float]] = {arm: [] for arm in progs}
    for _ in range(reps + 1):
        for arm, prog in progs.items():
            t0 = time.perf_counter()
            prog(**inputs)
            times[arm].append(time.perf_counter() - t0)
    results = {}
    for arm, prog in progs.items():
        inputs["out"][:] = 0
        prog(**inputs)
        results[arm] = inputs["out"].copy()
    assert all(np.array_equal(out, results["int64"]) for out in results.values()), "arms disagree"
    return {arm: median_ci([t * 1e3 for t in ts[1:]]) for arm, ts in times.items()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reps", type=int, default=20)
    parser.add_argument("--kernels", nargs="*", default=list(KERNELS))
    args = parser.parse_args()
    threads = os.environ.get("OMP_NUM_THREADS", str(os.cpu_count()))
    print(f"machine: {platform.machine()}, OMP_NUM_THREADS={threads}, flags: {FLAGS}, reps: {args.reps}")
    print(
        "| kernel | compiler | size | threads | "
        + " | ".join(f"{arm} ms" for arm in ARMS)
        + " | "
        + " | ".join(f"{arm}/int64" for arm in list(ARMS)[1:])
        + " |"
    )
    print("|---|---|---|---|" + "---|" * (2 * len(ARMS) - 1))
    for kname in args.kernels:
        program, sizes = KERNELS[kname]
        for compiler in COMPILERS.values():
            (HERE / "code" / kname).mkdir(parents=True, exist_ok=True)
            progs = {arm: build(program, compiler, kname, arm) for arm in ARMS}
            for label, factory in sizes:
                stats = time_size(progs, factory, args.reps)
                base = stats["int64"][0]
                cells = " | ".join(f"{m:.3f} [{lo:.3f}, {hi:.3f}]" for m, lo, hi in stats.values())
                ratios = " | ".join(f"{stats[arm][0] / base:.3f}" for arm in list(ARMS)[1:])
                print(f"| {kname} | {version(compiler)} | {label} | {threads} | {cells} | {ratios} |", flush=True)


if __name__ == "__main__":
    main()
