# Copyright 2026 ETH Zurich and the Alloy authors.
"""The tile ISA (A11): a matrix tile operation, such as a 64x64x64 GEMM, answered per target with the loop of
instructions that fits it, the layout and descriptors its loads need, and a C or C++ program that uses Alloy's tile
functions on row-major tiles, checked against a host reference before it is printed.

Targets: ``sm90`` (GH200), ``gfx942`` (MI300A), ``gfx90a`` (MI250X), and ``cpu``. A CPU has no swizzle, and the
evaluated CPUs have neither AMX nor SME, so ``mma`` on a CPU is an FMA loop over blocks of four rows that the host
compiler vectorizes (the fallback).

    python -m alloy.isa tile cpu gemm 64 64 64 --in f32 --acc f32
"""

import pathlib
import re
import shlex
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field

from alloy.isa.schedules import lanes_of
from alloy.isa.table import load
from alloy.isa.validate import c_compiler, c_flags, emulated, host_can_run

__all__ = [
    "CPU_TYPES",
    "GPU_BYTES",
    "GPU_TILES",
    "TYPES",
    "TilePlan",
    "cpu_plan",
    "gpu_block",
    "gpu_plan",
    "inlined",
    "k_block",
    "native_gpu",
    "plan",
    "verify",
]

HERE = pathlib.Path(__file__).parent
#: Element types a CPU tile takes: (input, accumulator) pairs with a C spelling each.
CPU_TYPES = {
    ("f32", "f32"): ("float", "float"),
    ("f64", "f64"): ("double", "double"),
    ("f32", "f64"): ("float", "double"),
}
#: The AMD CDNA targets: one tile kernel per input type (a 32x32 MFMA, plain LDS stores), built for each arch.
CDNA = ("gfx90a", "gfx942")
#: Bytes per element of a GPU tile input. A K block is 128 bytes of a row: 64 two-byte or 128 one-byte elements.
GPU_BYTES = {"f16": 2, "bf16": 2, "e4m3": 1, "e5m2": 1, "f64": 8}
#: The input types of the f32-accumulating tile kernels; f64 is CDNA's own kernel (v_mfma_f64_16x16x4f64).
F32_ACC = ("f16", "bf16", "e4m3", "e5m2")
#: Each GPU input type with an f32 accumulator; gfx90a (MI250X) has no FP8 MFMA.
GPU_TYPES = {
    "sm90": tuple((t, "f32") for t in F32_ACC),
    "gfx942": (*((t, "f32") for t in F32_ACC), ("f64", "f64")),
    "gfx90a": (("f16", "f32"), ("bf16", "f32"), ("f64", "f64")),
}
#: The (input, accumulator) element types each tile target's checked kernels take.
TYPES: dict[str, tuple[tuple[str, str], ...]] = {
    "cpu": tuple(CPU_TYPES), "sme": (("f32", "f32"), ("f64", "f64")),
} | GPU_TYPES | dict.fromkeys(("avx2", "avx512", "neon", "sve"), (("f32", "f32"), ("f64", "f64")))  # fmt: skip
#: The FP8 encodings per target (exponent bits, mantissa bits, bias): sm_90 reads OCP E4M3 (E4M3FN) and E5M2;
#: gfx942 reads the FNUZ variants (no infinity, no negative zero, one more in the bias).
FP8_FORMATS = {
    "sm90": {"e4m3": (4, 3, 7), "e5m2": (5, 2, 15)},
    "gfx942": {"e4m3": (4, 3, 8), "e5m2": (5, 2, 16)},
}
#: How each target names an FP8 type in its sources.
FP8_NAMES = {
    "sm90": {"e4m3": "OCP E4M3 (__nv_fp8_e4m3)", "e5m2": "OCP E5M2 (__nv_fp8_e5m2)"},
    "gfx942": {"e4m3": "E4M3FNUZ (__hip_fp8_e4m3_fnuz)", "e5m2": "E5M2FNUZ (__hip_fp8_e5m2_fnuz)"},
}
#: The bit layouts of the 16-bit types: (exponent bits, mantissa bits, bias).
HALF_FORMATS = {"f16": (5, 10, 15), "bf16": (8, 7, 127)}
#: The instruction a tile kernel issues per input type, with the K one instruction covers.
CDNA_MFMA = {
    "f16": ("v_mfma_f32_32x32x8_f16", "__builtin_amdgcn_mfma_f32_32x32x8f16", 8),
    "bf16": (
        "v_mfma_f32_32x32x8_bf16 (gfx90a: v_mfma_f32_32x32x8bf16_1k)",
        "__builtin_amdgcn_mfma_f32_32x32x8bf16_1k",
        8,
    ),
    "e4m3": ("v_mfma_f32_32x32x16_fp8_fp8", "__builtin_amdgcn_mfma_f32_32x32x16_fp8_fp8", 16),
    "e5m2": ("v_mfma_f32_32x32x16_bf8_bf8", "__builtin_amdgcn_mfma_f32_32x32x16_bf8_bf8", 16),
}
#: The template argument of the tile kernels (alloy_elem in both headers) per input type.
ELEM = {"f16": "ALLOY_F16", "bf16": "ALLOY_BF16", "e4m3": "ALLOY_E4M3", "e5m2": "ALLOY_E5M2"}


def k_block(in_type: str) -> int:
    """Elements of K per block of a GPU tile kernel: one row of 128 bytes."""
    return 128 // GPU_BYTES[in_type]


#: Rows of A one CPU micro-kernel step keeps in registers.
CPU_MR = 4
#: The CPU vector ISAs whose mma is the row-wise FMA tile in their own intrinsics (the table's load, broadcast, fma,
#: and store entries): a block of CPU_MR rows of C, one vector register per row.
SIMD = ("avx2", "avx512", "neon", "sve")
VECTOR_TYPE = {
    ("avx2", "f32"): "__m256", ("avx2", "f64"): "__m256d", ("avx512", "f32"): "__m512", ("avx512", "f64"): "__m512d",
    ("neon", "f32"): "float32x4_t", ("neon", "f64"): "float64x2_t", ("sve", "f32"): "svfloat32_t",
    ("sve", "f64"): "svfloat64_t",
}  # fmt: skip
SIMD_HEADER = {"avx2": "immintrin.h", "avx512": "immintrin.h", "neon": "arm_neon.h", "sve": "arm_sve.h"}
#: Relative error a product may show against the f64 reference, per accumulator type.
TOLERANCE = {"f32": 1e-5, "f64": 1e-12}
TIMEOUT = 300


@dataclass(frozen=True, slots=True)
class TilePlan:
    """A tile operation on one target: the shape and types, the instruction loop as steps, the descriptors and the
    layout its operands need, the program that runs it once against a reference, and the check's outcome
    (``run``: matched the reference here; ``compiled``: built, no device to run it; ``failed``: did not build or
    missed the reference; ``unverified``: no tool here to check it)."""

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


#: A tag that ties a header line to types and shapes: "// alloy-only: <tokens>" at its end, or alone on the line that
#: opens a block closed by "// alloy-end".
ONLY = re.compile(r"\s*// alloy-only: ([\w ]+)$")


def inlined(header: str, keep: frozenset[str]) -> str:
    """The text of Alloy's tile header ``header`` as an answer pastes it instead of including the file: the blocks
    and lines tagged for tokens outside ``keep`` (other types, shapes, the mma when only a copy is asked) left out."""
    kept: list[str] = []
    blocks: list[set[str]] = []
    for line in (HERE / header).read_text().splitlines():
        opened = ONLY.fullmatch(line)
        if opened:
            blocks.append(set(opened.group(1).split()))
        elif line.strip() == "// alloy-end":
            blocks.pop()
        elif line.strip() != "#pragma once":
            tag = ONLY.search(line)
            tokens = set().union(*blocks, tag.group(1).split() if tag else ())
            if tokens <= keep:
                kept.append(ONLY.sub("", line))
    return "\n".join(kept)


#: The line that builds each tile target's program, saved as tile.c, tile.cu, or tile.hip in the current folder. The
#: program pastes Alloy's tile functions, so it needs no include path.
BUILD = {
    "cpu": "cc -O3 -march=native -std=c11 tile.c -o tile -lm",
    "sm90": "nvcc -gencode arch=compute_90a,code=sm_90a -std=c++17 -O2 tile.cu -o tile -lcuda",
    "sme": "clang --target=aarch64-linux-gnu -march=armv9-a+sme+sme-f64f64 -O2 -c tile.c -o tile.o",
} | {arch: f"hipcc --offload-arch={arch} -O2 tile.hip -o tile" for arch in ("gfx90a", "gfx942")}
#: SME's link: the aarch64 cross compiler's libgcc has the SME ABI routines (gcc 14 or later).
SME_LINK = "aarch64-linux-gnu-gcc -static tile.o -o tile -lm"


def compile_only(argv: list[str]) -> list[str]:
    """``argv`` building an object, not a program: -c, no libraries (a machine without the GPU often lacks them)."""
    argv = [a for a in argv if not a.startswith("-l")]
    at = argv.index("-o")
    return [*argv[:at], "-c", "-o", f"{argv[at + 1]}.o", *argv[at + 2 :]]


def cpu_plan(m: int, n: int, k: int, in_type: str, acc_type: str) -> TilePlan:
    """The CPU fallback: ``alloy_mma`` from ``alloy_tile_cpu.h`` on row-major A (m x k), B (k x n), C (m x n)."""
    if (in_type, acc_type) not in CPU_TYPES:
        legal = ", ".join(f"--in {i} --acc {a}" for i, a in CPU_TYPES)
        raise KeyError(f"a CPU tile takes {legal}; no AMX or SME here, so f16 and bf16 have no CPU MMA")
    a_type, c_type = CPU_TYPES[in_type, acc_type]
    steps = (
        f"no matrix unit on this CPU: alloy_mma_{in_type}_{acc_type} is the fallback, an FMA loop",
        (
            f"for each block of {CPU_MR} rows of C, for each k: broadcast A[i][k] of the {CPU_MR} rows and multiply-add "
            "row k of B into the block (the compiler vectorizes along n)"
        ),
    )
    layout = "row-major A, B, and C with leading dimensions lda, ldb, ldc; no swizzle on a CPU"
    program = cpu_program(m, n, k, a_type, c_type, in_type, acc_type)
    return TilePlan("cpu", m, n, k, in_type, acc_type, steps, layout, program, {"build": BUILD["cpu"]})


def simd_kernel(isa: str, dtype: str) -> str:
    """``alloy_mma_<isa>_<dtype>``: C += A x B on row-major tiles in blocks of CPU_MR rows x one vector of columns; each k
    broadcasts A[i][k] of the rows and multiply-adds row k of B into one accumulator register per row. SVE runs any n
    under a while-less-than predicate; the fixed-width ISAs take n in whole vectors."""
    table = load()
    ld, bc, fm, st = (table.entry(isa, op, dtype).intrinsic for op in ("load", "broadcast", "fma", "store"))
    s, v, sve = CPU_TYPES[dtype, dtype][0], VECTOR_TYPE[isa, dtype], isa == "sve"
    pg = "pg, " if sve else ""
    rows = range(CPU_MR)

    def fma(r: int) -> str:
        a = f"{bc}(a[(i + {r}) * lda + p])"
        return {"neon": f"{fm}(c{r}, {a}, bp)", "sve": f"{fm}(pg, c{r}, {a}, bp)"}.get(isa, f"{fm}({a}, bp, c{r})")

    mask = f"\n      svbool_t pg = {table.entry(isa, 'gen_mask', dtype).intrinsic}(j, n);" if sve else ""
    return "\n".join((
        f"#include <{SIMD_HEADER[isa]}>",
        f"static inline void alloy_mma_{isa}_{dtype}(int m, int n, int k, const {s} *restrict a, int lda,",
        f"                                    const {s} *restrict b, int ldb, {s} *restrict c, int ldc) {{",
        f"  for (int i = 0; i < m; i += {CPU_MR})",
        f"    for (int j = 0; j < n; j += {lanes_of(table, isa, dtype)[1]}) {{{mask}",
        *(f"      {v} c{r} = {ld}({pg}&c[(i + {r}) * ldc + j]);" for r in rows),
        "      for (int p = 0; p < k; ++p) {",
        f"        {v} bp = {ld}({pg}&b[p * ldb + j]);",
        *(f"        c{r} = {fma(r)};" for r in rows),
        "      }",
        *(f"      {st}({pg}&c[(i + {r}) * ldc + j], c{r});" for r in rows),
        "    }",
        "}",
    ))  # fmt: skip


def simd_lanes(isa: str, dtype: str) -> int:
    """The columns of C a tile of ``isa`` takes in whole multiples: one vector, or 1 on SVE (predicated)."""
    return 1 if isa == "sve" else lanes_of(load(), isa, dtype)[0]


def simd_plan(isa: str, m: int, n: int, k: int, in_type: str, acc_type: str) -> TilePlan:
    """The row-wise FMA tile of a CPU vector ISA; a shape off its blocks is a ``KeyError`` naming the nearest."""
    if (in_type, acc_type) not in TYPES[isa]:
        raise KeyError(f"{isa} tiles take --in f32 --acc f32 or --in f64 --acc f64; the cpu target mixes f32 and f64")
    lanes = simd_lanes(isa, in_type)
    if m % CPU_MR or n % lanes:
        up_m, up_n = -(-m // CPU_MR) * CPU_MR, -(-n // lanes) * lanes
        raise KeyError(f"{isa} {in_type} tiles are blocks of {CPU_MR} rows x {lanes} lanes: M a multiple of {CPU_MR} "
                       f"and N of {lanes}; got {m}x{n}x{k}, nearest {up_m}x{up_n}x{k} (pad C)")  # fmt: skip
    table = load()
    ld, bc, fm, st = (table.entry(isa, op, in_type).intrinsic for op in ("load", "broadcast", "fma", "store"))
    steps = (
        f"for each block of {CPU_MR} rows of C and one vector of columns: {ld} the {CPU_MR} rows into accumulators",
        f"for each k: {ld} row k of B, then {CPU_MR} x {fm} with {bc}(A[i][k]) of each row",
        f"{st} the {CPU_MR} accumulators back to C",
    )
    layout = "row-major A, B, and C with leading dimensions lda, ldb, ldc; unaligned loads, no swizzle"
    ctype = CPU_TYPES[in_type, acc_type]
    program = cpu_program(m, n, k, *ctype, in_type, acc_type, simd_kernel(isa, in_type), f"alloy_mma_{isa}_{in_type}")
    build = f"cc -O3 {' '.join(c_flags(isa, in_type))} -std=c11 tile.c -o tile -lm".replace("  ", " ")
    return TilePlan(isa, m, n, k, in_type, acc_type, steps, layout, program, {"build": build})


def simd_verify(plan_: TilePlan) -> TilePlan:
    """``plan_`` run here, natively or under qemu for an Arm ISA; ``unverified`` when this host runs neither."""
    isa, dtype = plan_.target, plan_.in_type
    emulator = None if host_can_run(isa, dtype) else emulated(isa)
    if emulator is None and not host_can_run(isa, dtype):
        return replace_check(plan_, "unverified", f"this host runs no {isa} code, natively or under qemu")
    cc, extra, launcher = emulator or (c_compiler(), (), ())
    with tempfile.TemporaryDirectory(prefix="alloy_tile_") as folder:
        binary = pathlib.Path(folder) / "tile"
        (pathlib.Path(folder) / "tile.c").write_text(plan_.program)
        argv = [str(cc), "-O3", *c_flags(isa, dtype), *extra, "-std=c11", "tile.c", "-o", "tile", "-lm"]
        built = subprocess.run(argv, cwd=folder, capture_output=True, text=True, check=False, timeout=TIMEOUT)
        if built.returncode != 0:
            return replace_check(plan_, "failed", f"did not compile: {built.stderr.strip()[-500:]}")
        ran = subprocess.run([*launcher, str(binary)], capture_output=True, text=True, check=False, timeout=TIMEOUT)
    return replace_check(plan_, *outcome(ran))


def cpu_program(m: int, n: int, k: int, a_type: str, c_type: str, in_type: str, acc_type: str, tiles: str = "",
                function: str = "") -> str:  # fmt: skip
    """A program that runs the tile once on deterministic inputs and prints the largest relative error against an
    f64 reference; it exits 1 above the accumulator's tolerance. ``tiles`` defaults to the fallback's header."""
    tiles = tiles or inlined("alloy_tile_cpu.h", frozenset({f"{in_type}_{acc_type}"}))
    function = function or f"alloy_mma_{in_type}_{acc_type}"
    return f"""#include <math.h>
#include <stdio.h>
{tiles}

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
  {function}(M, N, K, A, K, B, N, C, N);
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
    if plan_.target in SIMD:
        return simd_verify(plan_)
    with tempfile.TemporaryDirectory(prefix="alloy_tile_") as folder:
        binary = pathlib.Path(folder) / "tile"
        (pathlib.Path(folder) / "tile.c").write_text(plan_.program)
        built = subprocess.run(shlex.split(BUILD["cpu"]), cwd=folder, capture_output=True, text=True, check=False,
                               timeout=TIMEOUT)  # fmt: skip
        if built.returncode != 0:
            return replace_check(plan_, "failed", f"did not compile: {built.stderr.strip()[-500:]}")
        ran = subprocess.run([str(binary)], capture_output=True, text=True, check=False, timeout=TIMEOUT)
    return replace_check(plan_, *outcome(ran))


def outcome(ran: subprocess.CompletedProcess[str]) -> tuple[str, str]:
    """The check of a tile program's run: exit 0 within the tolerance, 1 above it (both print the relative error),
    anything else a failure before the comparison, such as a refused launch, printed as the program said it."""
    said = ran.stdout.strip()
    if ran.returncode in (0, 1):
        return "run" if ran.returncode == 0 else "failed", f"relative error {said} against the f64 reference"
    return (
        "failed",
        f"the program stopped before the comparison (exit {ran.returncode}): {said or ran.stderr.strip()[-300:]}",
    )


def replace_check(plan_: TilePlan, verified: str, detail: str) -> TilePlan:
    return TilePlan(
        plan_.target, plan_.m, plan_.n, plan_.k, plan_.in_type, plan_.acc_type, plan_.steps, plan_.layout,
        plan_.program, plan_.descriptors, verified, detail,
    )  # fmt: skip


#: GPU tile shapes per target: (BM, BN) output tile per block and the kernel template computing it; K is a multiple
#: of the K block of the input type (k_block).
GPU_TILES = {
    "sm90": {(64, 64): "alloy_gemm_64x64", (128, 128): "alloy_gemm_128x128"},
} | {arch: {(64, 64): "alloy_gemm_64x64"} for arch in CDNA}
GPU_HEADER = {"sm90": "alloy_tile_sm90.cuh"} | dict.fromkeys(CDNA, "alloy_tile_cdna.hip.h")
#: Threads per block of each kernel: one warpgroup (128) per 64 rows on sm_90, four wave64 on CDNA.
GPU_THREADS = {("sm90", 64): 128, ("sm90", 128): 256} | {(arch, 64): 256 for arch in CDNA}


def type_note(target: str, in_type: str) -> str:
    """What the input type is on ``target``: its bytes and, for FP8, the encoding the target reads."""
    if in_type in FP8_NAMES.get(target, {}):
        e, m, bias = FP8_FORMATS[target][in_type]
        return f"{in_type} is {FP8_NAMES[target][in_type]}: {e} exponent bits, {m} mantissa bits, bias {bias}"
    return f"{in_type}, {GPU_BYTES[in_type]} bytes"


def gpu_steps(target: str, bm: int, bn: int, k: int, in_type: str) -> tuple[tuple[str, ...], str, dict[str, str]]:
    """The instruction loop, the layout, and the descriptors of a ``bm x bn`` tile with f32 accumulation."""
    kb = k_block(in_type)
    blocks = k // kb
    if target == "sm90":
        step = 16 if GPU_BYTES[in_type] == 2 else 32
        shape = f"m64n{bn}k{step}"
        map_type = {"f16": "FLOAT16", "bf16": "BFLOAT16"}.get(in_type, "UINT8")
        steps: tuple[str, ...] = (
            f"every thread: load its {bn // 2} accumulators from C (D = A x B + C), in the layout of the store",
            "thread 0: mbarrier.init (count 1), then fence.proxy.async.shared::cta; __syncthreads",
            f"for each of the {blocks} K blocks of {kb} ({in_type}, 128 bytes of a row):",
            (
                f"  thread 0: mbarrier.arrive.expect_tx with {(bm + bn) * 128} bytes, then two "
                f"cp.async.bulk.tensor.2d loads (A box {{{kb}, BM}}, B box {{{kb}, BN}}) into 1024-byte-aligned shared "
                "memory"
            ),
            "  every thread: mbarrier.try_wait.parity on the phase, then flips it",
            (
                f"  wgmma.fence; 4 x wgmma.mma_async.{shape}.f32.{in_type}.{in_type} per warpgroup (each descriptor "
                "advanced by 32 bytes); wgmma.commit_group; wgmma.wait_group 0; __syncthreads"
            ),
            (
                f"store: each thread writes its {bn // 2} accumulators as float2 pairs (rows lane/4 and lane/4 + 8 of its "
                "warp's 16)"
            ),
        )
        layout = (
            f"shared tiles of {kb} {in_type} (128 bytes) per row, 128B swizzle, 1024-byte aligned; wgmma descriptor: "
            "start address >> 4, LBO 1, SBO 1024 bytes (8 rows), swizzle code 1 (128B)"
        )
        descriptors = {
            "tensor map": f"cuTensorMapEncodeTiled({map_type}, rank 2, dims {{K, rows}}, strides {{K * "
            f"{GPU_BYTES[in_type]} bytes}}, box {{{kb}, {bm} for A or {bn} for B}}, element strides {{1, 1}}, "
            "INTERLEAVE_NONE, SWIZZLE_128B, L2_PROMOTION_L2_128B, OOB_FILL_NONE): alloy_make_tmap<E>; the global "
            f"address 16-byte aligned, K * {GPU_BYTES[in_type]} a multiple of 16",
            "build": BUILD["sm90"],
            "arch": "sm_90a: plain sm_90 rejects wgmma",
            "type": type_note(target, in_type),
        }
        return steps, layout, descriptors
    mnemonic, builtin, per = CDNA_MFMA[in_type]
    steps = (
        "every lane: load its 16 accumulators from C (D = A x B + C), in the layout of the store",
        f"for each of the {blocks} K blocks of {kb} ({in_type}, 128 bytes of a row):",
        (
            "  each of 256 threads: two global_load_dwordx4 per operand (16 bytes) and ds_write_b128 into LDS, "
            "chunk c of row r at slot c ^ (r % 8); __syncthreads"
        ),
        (
            f"  each wave64 owns a 32 x 32 sub-tile: 4 ds_read_b128 per operand and 8 x {mnemonic} "
            f"({builtin}(a, b, acc, 0, 0, 0), K = {per} each) cover the block; __syncthreads"
        ),
        "store: accumulator g of a lane is D[8 * (g / 4) + 4 * (lane / 32) + g % 4][lane % 32], 16 per lane",
    )
    layout = "LDS: 64 rows x 8 chunks of 16 bytes per operand, XOR swizzle slot = chunk ^ (row % 8), no padding"
    descriptors = {"build": BUILD[target], "type": type_note(target, in_type)}
    return steps, layout, descriptors


def encoding(target: str, in_type: str) -> tuple[int, int, int]:
    """(exponent bits, mantissa bits, bias) of ``in_type`` as ``target`` reads it."""
    return FP8_FORMATS[target][in_type] if in_type in ("e4m3", "e5m2") else HALF_FORMATS[in_type]


def gpu_program(target: str, bm: int, bn: int, m: int, n: int, k: int, in_type: str) -> str:
    """A program that runs the tile kernel over an m x n x k product once and checks it against an f64 reference.
    The inputs are multiples of 1/8 that every input type holds exactly, encoded on the host by bit layout."""
    kernel, threads = f"{GPU_TILES[target][bm, bn]}<{ELEM[in_type]}>", GPU_THREADS[target, bm]
    api = "cuda" if target == "sm90" else "hip"
    size, (e, mant, bias) = GPU_BYTES[in_type], encoding(target, in_type)
    if target == "sm90":
        setup = f"""  CUtensorMap ta, tb;
  if (alloy_make_tmap<{ELEM[in_type]}>(&ta, dA, M, K, {bm}) != CUDA_SUCCESS ||
      alloy_make_tmap<{ELEM[in_type]}>(&tb, dB, N, K, {bn}) != CUDA_SUCCESS) {{
    printf("tensor map refused\\n");
    return 2;
  }}
  {kernel}<<<dim3(N / {bn}, M / {bm}), {threads}>>>(ta, tb, dC, N, K);"""
        include = inlined(GPU_HEADER[target], frozenset({"mma", in_type, f"n{bn}", f"{bm}x{bn}"}))
        include += "\n#include <cuda_runtime.h>"
    else:
        setup = f"  {kernel}<<<dim3(N / {bn}, M / {bm}), {threads}>>>(dA, dB, dC, N, K);"
        include = inlined(GPU_HEADER[target], frozenset({"mma", in_type}))
    return f"""{include}
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

enum {{ M = {m}, N = {n}, K = {k}, BYTES = {size} }};

// {in_type} on {target}: {e} exponent bits, {mant} mantissa bits, bias {bias}; v is a multiple of 1/8 it holds exactly.
static void put(float v, unsigned char* at) {{
  unsigned code = 0;
  if (v != 0.0f) {{
    int exponent;
    const double fraction = frexp(fabs((double)v), &exponent);  // |v| = fraction * 2^exponent, fraction in [0.5, 1)
    const unsigned mantissa = (unsigned)((2.0 * fraction - 1.0) * (1 << {mant}));
    code = (v < 0.0f ? 1u << {e + mant} : 0u) | ((unsigned)(exponent - 1 + {bias}) << {mant}) | mantissa;
  }}
  for (int byte = 0; byte < BYTES; ++byte) at[byte] = (unsigned char)(code >> (8 * byte));
}}

int main(void) {{
  float* fA = (float*)malloc(sizeof(float) * M * K);
  float* fB = (float*)malloc(sizeof(float) * N * K);  // B transposed: N x K row-major
  unsigned char* hA = (unsigned char*)malloc((size_t)BYTES * M * K);
  unsigned char* hB = (unsigned char*)malloc((size_t)BYTES * N * K);
  float* hC = (float*)malloc(sizeof(float) * M * N);
  float* fC = (float*)malloc(sizeof(float) * M * N);  // C before the product: the kernel computes C = A x B + C
  for (int i = 0; i < M * K; ++i) put(fA[i] = (float)((i % 13) - 6) / 8, hA + (size_t)BYTES * i);
  for (int i = 0; i < N * K; ++i) put(fB[i] = (float)((i % 7) - 3) / 4, hB + (size_t)BYTES * i);
  for (int i = 0; i < M * N; ++i) hC[i] = fC[i] = (float)((i % 5) - 2);
  void *dA, *dB;
  float* dC;
  {api}Malloc(&dA, (size_t)BYTES * M * K);
  {api}Malloc(&dB, (size_t)BYTES * N * K);
  {api}Malloc((void**)&dC, sizeof(float) * M * N);
  {api}Memcpy(dA, hA, (size_t)BYTES * M * K, {api}MemcpyHostToDevice);
  {api}Memcpy(dB, hB, (size_t)BYTES * N * K, {api}MemcpyHostToDevice);
  {api}Memcpy(dC, hC, sizeof(float) * M * N, {api}MemcpyHostToDevice);
{setup}
  if ({api}DeviceSynchronize() != {api}Success) {{
    printf("launch failed\\n");
    return 2;
  }}
  {api}Memcpy(hC, dC, sizeof(float) * M * N, {api}MemcpyDeviceToHost);
  double worst = 0.0;
  for (int i = 0; i < M; ++i)
    for (int j = 0; j < N; ++j) {{
      double want = fC[i * N + j];
      for (int p = 0; p < K; ++p) want += (double)fA[i * K + p] * (double)fB[j * K + p];
      double rel = fabs((double)hC[i * N + j] - want) / fmax(1.0, fabs(want));
      if (rel > worst) worst = rel;
    }}
  printf("%.3e\\n", worst);
  return worst <= {TOLERANCE["f32"]} ? 0 : 1;
}}
"""


def gpu_block(target: str, m: int, n: int, k: int, in_type: str = "f16") -> tuple[int, int]:
    """The (BM, BN) block of the tile kernel an ``m x n x k`` product runs on ``target``: the largest that divides M
    and N. Each block loads K in blocks of 128 bytes of a row: A as BM rows and Bt as BN rows."""
    tiles, kb = GPU_TILES[target], k_block(in_type)
    fitting = [(bm, bn) for bm, bn in tiles if m % bm == 0 and n % bn == 0]
    if not fitting or k % kb:
        legal = ", ".join(f"{bm}x{bn} blocks" for bm, bn in tiles)
        raise KeyError(
            f"{target}: M and N multiples of a tile ({legal}), K a multiple of {kb} for {in_type}; got {m}x{n}x{k}"
        )
    return max(fitting)


def gpu_plan(target: str, m: int, n: int, k: int, in_type: str, acc_type: str) -> TilePlan:
    """A GEMM on sm_90 or CDNA (gfx90a, gfx942) tiled by the target's tile kernel for the input type; refuses what the
    kernels do not cover."""
    tiles = GPU_TILES[target]
    if (in_type, acc_type) not in TYPES[target]:
        legal = ", ".join(f"--in {i} --acc {a}" for i, a in TYPES[target])
        raise KeyError(f"{target} tiles take {legal} (the kernels the table checks); got {in_type}, {acc_type}")
    bm, bn = gpu_block(target, m, n, k, in_type)
    if in_type == "f64":
        return cdna_f64_plan(target, m, n, k)
    steps, layout, descriptors = gpu_steps(target, bm, bn, k, in_type)
    kernel = f"{tiles[bm, bn]}<{ELEM[in_type]}>"
    descriptors = {"tile": f"{kernel}, {bm} x {bn} per block, {GPU_THREADS[target, bm]} threads"} | descriptors
    return TilePlan(
        target, m, n, k, in_type, acc_type, steps, layout, gpu_program(target, bm, bn, m, n, k, in_type), descriptors
    )


def cdna_f64_plan(target: str, m: int, n: int, k: int) -> TilePlan:
    """f64 on CDNA: ``alloy_gemm_64x64_f64``, 2 x 2 v_mfma_f64_16x16x4f64 tiles per wave64, f64 accumulators."""
    steps = (
        "every lane: load its 16 f64 accumulators from C (D = A x B + C), 4 per 16 x 16 tile, in the layout of the store",
        f"for each of the {k // 16} K blocks of 16 (f64, 128 bytes of a row):",
        ("  each of 256 threads: two global_load_dwordx4 per operand (16 bytes) and ds_write_b128 into LDS, chunk c of "
         "row r at slot c ^ (r % 8); __syncthreads"),
        ("  each wave64 owns a 32 x 32 sub-tile of 2 x 2 tiles of 16 x 16: 4 steps of K = 4, each one double of A and "
         "of B per lane and 4 x v_mfma_f64_16x16x4f64 (__builtin_amdgcn_mfma_f64_16x16x4f64(a, b, acc, 0, 0, 0)); "
         "__syncthreads"),
        "store: accumulator i of a lane in a 16 x 16 tile is D[4 * (lane / 16) + i][lane % 16]",
    )  # fmt: skip
    layout = "LDS: 64 rows x 8 chunks of 16 bytes (2 doubles) per operand, XOR swizzle slot = chunk ^ (row % 8)"
    descriptors = {"tile": "alloy_gemm_64x64_f64, 64 x 64 per block, 256 threads", "build": BUILD[target],
                   "type": "f64, 8 bytes; f64 accumulators"}  # fmt: skip
    return TilePlan(target, m, n, k, "f64", "f64", steps, layout, cdna_f64_program(target, m, n, k), descriptors)


def cdna_f64_program(target: str, m: int, n: int, k: int) -> str:
    """The f64 tile run once over an m x n x k product against a long double reference; exit 1 above the f64
    tolerance."""
    return f"""{inlined(GPU_HEADER[target], frozenset({"f64"}))}
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

enum {{ M = {m}, N = {n}, K = {k} }};

int main(void) {{
  double* hA = (double*)malloc(sizeof(double) * M * K);
  double* hB = (double*)malloc(sizeof(double) * N * K);  // B transposed: N x K row-major
  double* hC = (double*)malloc(sizeof(double) * M * N);
  double* fC = (double*)malloc(sizeof(double) * M * N);  // C before the product: the kernel computes C = A x B + C
  for (int i = 0; i < M * K; ++i) hA[i] = (double)((i % 13) - 6) / 8;
  for (int i = 0; i < N * K; ++i) hB[i] = (double)((i % 7) - 3) / 4;
  for (int i = 0; i < M * N; ++i) hC[i] = fC[i] = (double)((i % 5) - 2);
  double *dA, *dB, *dC;
  hipMalloc((void**)&dA, sizeof(double) * M * K);
  hipMalloc((void**)&dB, sizeof(double) * N * K);
  hipMalloc((void**)&dC, sizeof(double) * M * N);
  hipMemcpy(dA, hA, sizeof(double) * M * K, hipMemcpyHostToDevice);
  hipMemcpy(dB, hB, sizeof(double) * N * K, hipMemcpyHostToDevice);
  hipMemcpy(dC, hC, sizeof(double) * M * N, hipMemcpyHostToDevice);
  alloy_gemm_64x64_f64<<<dim3(N / 64, M / 64), 256>>>(dA, dB, dC, N, K);
  if (hipDeviceSynchronize() != hipSuccess) {{
    printf("launch failed\\n");
    return 2;
  }}
  hipMemcpy(hC, dC, sizeof(double) * M * N, hipMemcpyDeviceToHost);
  double worst = 0.0;
  for (int i = 0; i < M; ++i)
    for (int j = 0; j < N; ++j) {{
      long double want = fC[i * N + j];
      for (int p = 0; p < K; ++p) want += (long double)hA[i * K + p] * hB[j * K + p];
      double rel = (double)(fabsl(hC[i * N + j] - want) / fmaxl(1.0L, fabsl(want)));
      if (rel > worst) worst = rel;
    }}
  printf("%.3e\\n", worst);
  return worst <= {TOLERANCE["f64"]} ? 0 : 1;
}}
"""


def native_gpu() -> str:
    """The tile target of this machine's GPU ("" without sm_90, gfx90a, or gfx942)."""
    for argv, target, wanted in ((["nvidia-smi", "--query-gpu=compute_cap", "--format=csv,noheader"], "sm90", "9.0"),
                                 *((["amdgpu-arch"], arch, arch) for arch in CDNA)):  # fmt: skip
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
        binary = here / "tile"
        (here / ("tile.cu" if plan_.target == "sm90" else "tile.hip")).write_text(plan_.program)
        here_too = native_gpu() == plan_.target  # without the GPU (and often its runtime), compile without linking
        argv = shlex.split(BUILD[plan_.target])
        argv = argv if here_too else compile_only(argv)
        try:
            built = subprocess.run(argv, cwd=folder, capture_output=True, text=True, check=False, timeout=TIMEOUT)
        except FileNotFoundError:
            return replace_check(plan_, "unverified", f"{argv[0]} is not installed here")
        if built.returncode != 0:
            return replace_check(plan_, "failed", f"did not compile: {built.stderr.strip()[-500:]}")
        if not here_too:
            return replace_check(
                plan_, "compiled", f"compiled for {plan_.target}; no {plan_.target} GPU here to run it"
            )
        ran = subprocess.run([str(binary)], capture_output=True, text=True, check=False, timeout=TIMEOUT)
    return replace_check(plan_, *outcome(ran))


CROSS_CC = "aarch64-linux-gnu-gcc"


def sme_plan(m: int, n: int, k: int, in_type: str, acc_type: str) -> TilePlan:
    """SME: outer products (FMOPA) into the ZA tile za0.s, A given transposed (``alloy_tile_sme.h``)."""
    if (in_type, acc_type) not in TYPES["sme"]:
        raise KeyError(f"an SME tile here takes --in f32 --acc f32 (FMOPA into za0.s) or --in f64 --acc f64 (za0.d, "
                       f"SME_F64F64); got {in_type}, {acc_type}")  # fmt: skip
    bits, ctype, tile_ = in_type[1:], CPU_TYPES[in_type, acc_type][0], "za0.s" if in_type == "f32" else "za0.d"
    steps = (
        (
            f"for each SVL/{bits} x SVL/{bits} block of C: svld1_hor_za{bits} loads its rows into {tile_} (predicated "
            "at the edges)"
        ),
        f"  {k} x svmopa_za{bits}_{in_type}_m: the outer product of a column of A (from at, contiguous) and a row of B",
        f"  svst1_hor_za{bits} stores the rows back; the function runs in streaming mode (__arm_locally_streaming)",
    )
    layout = "A transposed (k x m row-major), B k x n row-major, C m x n row-major; ZA holds one block of C; no swizzle"
    tiles = inlined("alloy_tile_sme.h", frozenset({in_type}))
    program = f"""#include <math.h>
#include <stdio.h>
{tiles}

enum {{ M = {m}, N = {n}, K = {k} }};
static {ctype} AT[K * M], B[K * N], C[M * N];

int main(void) {{
  for (int i = 0; i < K * M; ++i) AT[i] = ({ctype})((i % 13) - 6) / 8;
  for (int i = 0; i < K * N; ++i) B[i] = ({ctype})((i % 7) - 3) / 4;
  for (int i = 0; i < M * N; ++i) C[i] = ({ctype})((i % 5) - 2);
  static double want[M * N];
  for (int i = 0; i < M; ++i)
    for (int j = 0; j < N; ++j) {{
      double s = C[i * N + j];
      for (int p = 0; p < K; ++p) s += (double)AT[p * M + i] * (double)B[p * N + j];
      want[i * N + j] = s;
    }}
  alloy_mma_sme_{in_type}(M, N, K, AT, M, B, N, C, N);
  double worst = 0.0;
  for (int i = 0; i < M * N; ++i) {{
    double rel = fabs((double)C[i] - want[i]) / fmax(1.0, fabs(want[i]));
    if (rel > worst) worst = rel;
  }}
  printf("%.3e\\n", worst);
  return worst <= {TOLERANCE[in_type]} ? 0 : 1;
}}
"""
    descriptors = {"build": BUILD["sme"], "link": SME_LINK,
                   "hardware": "no evaluated CPU has SME; checked under qemu -cpu max,sme=on; the link needs gcc 14 or later"}  # fmt: skip
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
        binary = pathlib.Path(folder) / "tile"
        (pathlib.Path(folder) / "tile.c").write_text(plan_.program)
        built = subprocess.run(shlex.split(BUILD["sme"]), cwd=folder, capture_output=True, text=True, check=False,
                               timeout=TIMEOUT)  # fmt: skip
        if built.returncode == 0 and qemu is not None:
            built = subprocess.run(shlex.split(SME_LINK), cwd=folder, capture_output=True, text=True, check=False,
                                   timeout=TIMEOUT)  # fmt: skip
        if built.returncode != 0:
            return replace_check(plan_, "failed", f"did not build: {built.stderr.strip()[-500:]}")
        if qemu is None:
            return replace_check(plan_, "compiled", "compiled for armv9-a+sme; no qemu-aarch64 here to run it")
        ran = subprocess.run([qemu, "-cpu", "max,sme=on", str(binary)], capture_output=True, text=True, check=False,
                             timeout=TIMEOUT)  # fmt: skip
    verdict = "run" if ran.returncode == 0 else "failed"
    return replace_check(plan_, verdict, f"under qemu (SME): relative error {ran.stdout.strip()}")


def plan(target: str, m: int, n: int, k: int, in_type: str, acc_type: str) -> TilePlan:
    """The tile plan of ``target``; a target or shape it cannot take is a ``KeyError`` naming what it takes."""
    if min(m, n, k) <= 0:
        raise KeyError(f"a tile has positive extents; got {m}x{n}x{k}")
    if target == "cpu":
        return cpu_plan(m, n, k, in_type, acc_type)
    if target in SIMD:
        return simd_plan(target, m, n, k, in_type, acc_type)
    if target in GPU_TILES:
        return gpu_plan(target, m, n, k, in_type, acc_type)
    if target == "sme":
        return sme_plan(m, n, k, in_type, acc_type)
    raise KeyError(
        f"tile targets: cpu, avx2, avx512, neon, sve, sme, sm90 (GH200), gfx942 (MI300A), gfx90a (MI250X); got {target!r}"
    )
