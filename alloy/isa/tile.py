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
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field

__all__ = ["CPU_TYPES", "GPU_TILES", "TilePlan", "cpu_plan", "gpu_plan", "native_gpu", "plan", "verify"]

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
    """``plan_`` with its program compiled and run here: ``run`` when it matched the reference, ``compiled`` for a GPU
    target this machine does not have."""
    if plan_.target in GPU_TILES:
        return gpu_verify(plan_)
    if plan_.target == "sme":
        return sme_verify(plan_)
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


#: GPU tile shapes per target: (BM, BN) output tile per block and the kernel computing it; K is a multiple of 64.
GPU_TILES = {
    "sm90": {(64, 64): "alloy_gemm_64x64x64", (128, 128): "alloy_gemm_128x128x64"},
    "gfx942": {(64, 64): "alloy_gemm_64x64x64"},
}
GPU_HEADER = {"sm90": "alloy_tile_sm90.cuh", "gfx942": "alloy_tile_gfx942.hip.h"}
#: Threads per block of each kernel: one warpgroup (128) per 64 rows on sm_90, four wave64 on gfx942.
GPU_THREADS = {("sm90", 64): 128, ("sm90", 128): 256, ("gfx942", 64): 256}


def gpu_steps(target: str, bm: int, bn: int, k: int) -> tuple[tuple[str, ...], str, dict[str, str]]:
    """The instruction loop, the layout, and the descriptors of a ``bm x bn`` f16 tile with f32 accumulation."""
    blocks = k // 64
    if target == "sm90":
        shape = f"m64n{bn}k16"
        steps: tuple[str, ...] = (
            "thread 0: mbarrier.init (count 1), then fence.proxy.async.shared::cta; __syncthreads",
            f"for each of the {blocks} K blocks of 64:",
            f"  thread 0: mbarrier.arrive.expect_tx with {(bm + bn) * 64 * 2} bytes, then two "
            "cp.async.bulk.tensor.2d loads (A box {64, BM}, B box {64, BN}) into 1024-byte-aligned shared memory",
            "  every thread: mbarrier.try_wait.parity on the phase, then flips it",
            f"  wgmma.fence; 4 x wgmma.mma_async.{shape}.f32.f16.f16 per warpgroup (K = 64 in steps of 16, each "
            "descriptor advanced by 32 bytes); wgmma.commit_group; wgmma.wait_group 0; __syncthreads",
            f"store: each thread writes its {bn // 2} accumulators as float2 pairs (rows lane/4 and lane/4 + 8 of its "
            "warp's 16)",
        )
        layout = (
            "shared tiles of 64 halves (128 bytes) per row, 128B swizzle, 1024-byte aligned; wgmma descriptor: start "
            "address >> 4, LBO 1, SBO 1024 bytes (8 rows), swizzle code 1 (128B)"
        )
        descriptors = {
            "tensor map": "cuTensorMapEncodeTiled(FLOAT16, rank 2, dims {K, rows}, strides {K * 2 bytes}, box {64, "
            f"{bm} for A or {bn} for B}}, element strides {{1, 1}}, INTERLEAVE_NONE, SWIZZLE_128B, L2_PROMOTION_L2_128B, "
            "OOB_FILL_NONE): alloy_make_tmap; the global address 16-byte aligned, K * 2 a multiple of 16",
            "build": "nvcc -gencode arch=compute_90a,code=sm_90a (plain sm_90 rejects wgmma) and -lcuda",
        }
        return steps, layout, descriptors
    steps = (
        f"for each of the {blocks} K blocks of 64:",
        "  each of 256 threads: two global_load_dwordx4 per operand (16 bytes = 8 halves) and ds_write_b128 into LDS, "
        "chunk c of row r at slot c ^ (r % 8); __syncthreads",
        "  each wave64 owns a 32 x 32 sub-tile: 4 ds_read_b128 per operand and 8 x v_mfma_f32_32x32x8_f16 "
        "(__builtin_amdgcn_mfma_f32_32x32x8f16(a, b, acc, 0, 0, 0)) cover K = 64; __syncthreads",
        "store: accumulator g of a lane is D[8 * (g / 4) + 4 * (lane / 32) + g % 4][lane % 32], 16 per lane",
    )
    layout = "LDS: 64 rows x 8 chunks of 16 bytes per operand, XOR swizzle slot = chunk ^ (row % 8), no padding"
    descriptors = {"build": "hipcc --offload-arch=gfx942"}
    return steps, layout, descriptors


def gpu_program(target: str, bm: int, bn: int, m: int, n: int, k: int) -> str:
    """A program that runs the tile kernel over an m x n x k product once and checks it against an f64 reference."""
    kernel, threads = GPU_TILES[target][bm, bn], GPU_THREADS[target, bm]
    api = "cuda" if target == "sm90" else "hip"
    if target == "sm90":
        setup = f"""  CUtensorMap ta, tb;
  if (alloy_make_tmap(&ta, dA, M, K, {bm}) != CUDA_SUCCESS || alloy_make_tmap(&tb, dB, N, K, {bn}) != CUDA_SUCCESS) {{
    printf("tensor map refused\\n");
    return 2;
  }}
  {kernel}<<<dim3(N / {bn}, M / {bm}), {threads}>>>(ta, tb, dC, N, K);"""
        half, include = "__half", f'#include "{GPU_HEADER[target]}"\n#include <cuda_runtime.h>'
    else:
        setup = f"  {kernel}<<<dim3(N / {bn}, M / {bm}), {threads}>>>(dA, dB, dC, N, K);"
        half, include = "_Float16", f'#include "{GPU_HEADER[target]}"'
    return f"""{include}
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

enum {{ M = {m}, N = {n}, K = {k} }};

int main(void) {{
  {half}* hA = ({half}*)malloc(sizeof({half}) * M * K);
  {half}* hB = ({half}*)malloc(sizeof({half}) * N * K);  // B transposed: N x K row-major
  float* hC = (float*)malloc(sizeof(float) * M * N);
  for (int i = 0; i < M * K; ++i) hA[i] = ({half})((float)((i % 13) - 6) / 8);
  for (int i = 0; i < N * K; ++i) hB[i] = ({half})((float)((i % 7) - 3) / 4);
  {half} *dA, *dB;
  float* dC;
  {api}Malloc((void**)&dA, sizeof({half}) * M * K);
  {api}Malloc((void**)&dB, sizeof({half}) * N * K);
  {api}Malloc((void**)&dC, sizeof(float) * M * N);
  {api}Memcpy(dA, hA, sizeof({half}) * M * K, {api}MemcpyHostToDevice);
  {api}Memcpy(dB, hB, sizeof({half}) * N * K, {api}MemcpyHostToDevice);
{setup}
  if ({api}DeviceSynchronize() != {api}Success) {{
    printf("launch failed\\n");
    return 2;
  }}
  {api}Memcpy(hC, dC, sizeof(float) * M * N, {api}MemcpyDeviceToHost);
  double worst = 0.0;
  for (int i = 0; i < M; ++i)
    for (int j = 0; j < N; ++j) {{
      double want = 0.0;
      for (int p = 0; p < K; ++p) want += (double)(float)hA[i * K + p] * (double)(float)hB[j * K + p];
      double rel = fabs((double)hC[i * N + j] - want) / fmax(1.0, fabs(want));
      if (rel > worst) worst = rel;
    }}
  printf("%.3e\\n", worst);
  return worst <= {TOLERANCE["f32"]} ? 0 : 1;
}}
"""


def gpu_plan(target: str, m: int, n: int, k: int, in_type: str, acc_type: str) -> TilePlan:
    """An f16 GEMM on sm_90 or gfx942, tiled by the target's tile kernel; refuses what the kernels do not cover."""
    tiles = GPU_TILES[target]
    legal = ", ".join(f"{bm}x{bn} blocks" for bm, bn in tiles)
    if (in_type, acc_type) != ("f16", "f32"):
        raise KeyError(
            f"{target} tiles take --in f16 --acc f32 (the kernels the table checks); got {in_type}, {acc_type}"
        )
    fitting = [(bm, bn) for bm, bn in tiles if m % bm == 0 and n % bn == 0]
    if not fitting or k % 64:
        raise KeyError(f"{target}: M and N multiples of a tile ({legal}), K a multiple of 64; got {m}x{n}x{k}")
    bm, bn = max(fitting)
    steps, layout, descriptors = gpu_steps(target, bm, bn, k)
    descriptors = {"tile": f"{tiles[bm, bn]}, {bm} x {bn} per block, {GPU_THREADS[target, bm]} threads"} | descriptors
    return TilePlan(
        target, m, n, k, in_type, acc_type, steps, layout, gpu_program(target, bm, bn, m, n, k), descriptors
    )


def native_gpu() -> str:
    """The tile target of this machine's GPU ("" without sm_90 or gfx942)."""
    for argv, target, wanted in ((["nvidia-smi", "--query-gpu=compute_cap", "--format=csv,noheader"], "sm90", "9.0"),
                                 (["amdgpu-arch"], "gfx942", "gfx942")):  # fmt: skip
        try:
            found = subprocess.run(argv, capture_output=True, text=True, check=False, timeout=60).stdout.split()
        except FileNotFoundError:
            continue
        if wanted in found:
            return target
    return ""


def gpu_verify(plan_: TilePlan) -> TilePlan:
    """Compile ``plan_``'s program for its target; run it when this machine has that GPU."""
    with tempfile.TemporaryDirectory(prefix="alloy_tile_") as folder:
        here = pathlib.Path(folder)
        suffix = "cu" if plan_.target == "sm90" else "hip"
        source, binary = here / f"tile.{suffix}", here / "tile"
        source.write_text(plan_.program)
        here_too = native_gpu() == plan_.target  # without the GPU (and often its runtime), compile without linking
        output = ["-o", str(binary)] if here_too else ["-c", "-o", str(binary.with_suffix(".o"))]
        if plan_.target == "sm90":
            argv = ["nvcc", "-gencode", "arch=compute_90a,code=sm_90a", "-std=c++17", "-O2", f"-I{HERE}", *output,
                    str(source), *(["-lcuda"] if here_too else [])]  # fmt: skip
        else:
            argv = ["hipcc", "--offload-arch=gfx942", "-O2", f"-I{HERE}", *output, str(source)]
        try:
            built = subprocess.run(argv, capture_output=True, text=True, check=False, timeout=TIMEOUT)
        except FileNotFoundError:
            return replace_check(plan_, "unverified", f"{argv[0]} is not installed here")
        if built.returncode != 0:
            return replace_check(plan_, "unverified", f"did not compile: {built.stderr.strip()[-500:]}")
        if not here_too:
            return replace_check(
                plan_, "compiled", f"compiled for {plan_.target}; no {plan_.target} GPU here to run it"
            )
        ran = subprocess.run([str(binary)], capture_output=True, text=True, check=False, timeout=TIMEOUT)
    error = ran.stdout.strip()
    verdict = "run" if ran.returncode == 0 else "unverified"
    return replace_check(plan_, verdict, f"relative error {error} against the f64 reference")


CROSS_CC = "aarch64-linux-gnu-gcc"


def sme_plan(m: int, n: int, k: int, in_type: str, acc_type: str) -> TilePlan:
    """SME: outer products (FMOPA) into the ZA tile za0.s, A given transposed (``alloy_tile_sme.h``)."""
    if (in_type, acc_type) != ("f32", "f32"):
        raise KeyError(f"an SME tile here takes --in f32 --acc f32 (FMOPA into za0.s); got {in_type}, {acc_type}")
    steps = (
        "for each SVL/32 x SVL/32 block of C: svld1_hor_za32 loads its rows into za0.s (predicated at the edges)",
        f"  {k} x svmopa_za32_f32_m: the outer product of a column of A (from at, contiguous) and a row of B",
        "  svst1_hor_za32 stores the rows back; the function runs in streaming mode (__arm_locally_streaming)",
    )
    layout = "A transposed (k x m row-major), B k x n row-major, C m x n row-major; ZA holds one block of C; no swizzle"
    program = f"""#include <math.h>
#include <stdio.h>
#include "alloy_tile_sme.h"

enum {{ M = {m}, N = {n}, K = {k} }};
static float AT[K * M], B[K * N], C[M * N];

int main(void) {{
  for (int i = 0; i < K * M; ++i) AT[i] = (float)((i % 13) - 6) / 8;
  for (int i = 0; i < K * N; ++i) B[i] = (float)((i % 7) - 3) / 4;
  for (int i = 0; i < M * N; ++i) C[i] = (float)((i % 5) - 2);
  static double want[M * N];
  for (int i = 0; i < M; ++i)
    for (int j = 0; j < N; ++j) {{
      double s = C[i * N + j];
      for (int p = 0; p < K; ++p) s += (double)AT[p * M + i] * (double)B[p * N + j];
      want[i * N + j] = s;
    }}
  alloy_mma_sme_f32(M, N, K, AT, M, B, N, C, N);
  double worst = 0.0;
  for (int i = 0; i < M * N; ++i) {{
    double rel = fabs((double)C[i] - want[i]) / fmax(1.0, fabs(want[i]));
    if (rel > worst) worst = rel;
  }}
  printf("%.3e\\n", worst);
  return worst <= {TOLERANCE["f32"]} ? 0 : 1;
}}
"""
    descriptors = {"build": "-march=armv9-a+sme (gcc 14 or later, clang 18 or later)",
                   "hardware": "no evaluated CPU has SME; checked under qemu -cpu max,sme=on"}  # fmt: skip
    return TilePlan("sme", m, n, k, in_type, acc_type, steps, layout, program, descriptors)


def sme_verify(plan_: TilePlan) -> TilePlan:
    """Compile ``plan_`` for armv9-a+sme with clang (gcc has the SME intrinsics only from 14), link it statically with
    the aarch64 cross compiler (gcc 14 or later: its libgcc has the SME ABI routines such as ``__arm_tpidr2_save``),
    and run it under qemu with SME; compile only without qemu."""
    cc, clang = shutil.which(CROSS_CC), shutil.which("clang")
    if cc is None or clang is None:
        return replace_check(plan_, "unverified", f"needs clang and {CROSS_CC}")
    qemu = shutil.which("qemu-aarch64") or shutil.which("qemu-aarch64-static")
    with tempfile.TemporaryDirectory(prefix="alloy_tile_") as folder:
        source, binary = pathlib.Path(folder) / "tile.c", pathlib.Path(folder) / "tile"
        source.write_text(plan_.program)
        compile_argv = [clang, "--target=aarch64-linux-gnu", "-march=armv9-a+sme", "-O2", f"-I{HERE}", "-c",
                        str(source), "-o", str(binary.with_suffix(".o"))]  # fmt: skip
        built = subprocess.run(compile_argv, capture_output=True, text=True, check=False, timeout=TIMEOUT)
        if built.returncode == 0 and qemu is not None:
            link = [cc, "-static", str(binary.with_suffix(".o")), "-o", str(binary), "-lm"]
            built = subprocess.run(link, capture_output=True, text=True, check=False, timeout=TIMEOUT)
        if built.returncode != 0:
            return replace_check(plan_, "unverified", f"did not build: {built.stderr.strip()[-500:]}")
        if qemu is None:
            return replace_check(plan_, "compiled", "compiled for armv9-a+sme; no qemu-aarch64 here to run it")
        ran = subprocess.run([qemu, "-cpu", "max,sme=on", str(binary)], capture_output=True, text=True, check=False,
                             timeout=TIMEOUT)  # fmt: skip
    verdict = "run" if ran.returncode == 0 else "unverified"
    return replace_check(plan_, verdict, f"under qemu (SME): relative error {ran.stdout.strip()}")


def plan(target: str, m: int, n: int, k: int, in_type: str, acc_type: str) -> TilePlan:
    """The tile plan of ``target``; a target or shape it cannot take is a ``KeyError`` naming what it takes."""
    if min(m, n, k) <= 0:
        raise KeyError(f"a tile has positive extents; got {m}x{n}x{k}")
    if target == "cpu":
        return cpu_plan(m, n, k, in_type, acc_type)
    if target in GPU_TILES:
        return gpu_plan(target, m, n, k, in_type, acc_type)
    if target == "sme":
        return sme_plan(m, n, k, in_type, acc_type)
    raise KeyError(f"tile targets: cpu, sme, sm90 (GH200), gfx942 (MI300A); got {target!r}")
