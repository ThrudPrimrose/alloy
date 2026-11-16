# The ISA lookup

`alloy.isa` answers the questions an agent or a person asks while writing vector code by hand. Which intrinsic spells
this op on this ISA? What does a disassembled instruction compute? Which math kernel holds this error bound, and what
does it cost? Every answer says whether it was checked on this machine. The command line is `python -m alloy.isa`, and
agents reach it as the `alloy_isa` tool of the `alloy-isa` and `alloy` packets.

## What the table holds

The table spells 30 abstract ops (`alloy/isa/ops.py`) on four SIMD ISAs. The ops are loads and stores, gather and
scatter, arithmetic, `fma`, `sqrt`, comparisons and `select`, integer bit operations, `reduce_add`, `gen_mask`, and the
math functions `exp`, `sin`, and `cos`. The ISAs are AVX2, AVX-512, NEON, and SVE, and `avx512_256` names AVX-512 under
a 256-bit compiler width, so it has no spellings of its own.

| ISA | f64 | f32 | f16 | i64 | i32 | Assists |
|---|---|---|---|---|---|---|
| `avx2` | 23 | 23 | 14 | 16 | 16 | 3 |
| `avx512` | 24 | 24 | 14 | 16 | 16 | 9 |
| `neon` | 23 | 23 | 14 | 16 | 16 | 4 |
| `sve` | 24 | 24 | 15 | 16 | 16 | 6 |

A row of `intrinsics.toml` holds the C intrinsic, its signature, the lane semantics, the masked form where the ISA has
one, the assembly mnemonic, and a note on traps such as operand order. Where no single intrinsic exists, the row holds
a recipe and the C `code` that runs it. Assists are instructions that help a hand-written kernel without being an op
(`vscalefpd`, `svexpa`, `vrcpps`). The rows are written by hand and checked against the clang resource headers.

The schedules section describes five loop shapes, from a scalar loop to explicit predicated SVE loops. It lists which
shapes each ISA allows and gives a compiled skeleton for each one.

## How an answer is checked

A `lookup` runs its row before printing it. A small kernel calls the intrinsic, or the recipe's `code`, on test lanes
and compares each lane with a scalar reference. For AVX-512, the masked form runs as well. The compiled row is then
disassembled, and the stated mnemonic must appear in it. If the compiler chose another instruction, the answer says so
and stays verified. A failed check prints nothing to stdout, exits with code 3, and lists related spellings on stderr.

A row this host cannot run is marked `unverified`. On x86 that applies to NEON and SVE, unless `qemu-aarch64` and an
aarch64 cross compiler are installed. `reverse`, `assist`, and `schedule` answers are not checked.

## Math functions

`kernel` returns 19 functions as intrinsic code: `sin`, `cos`, `tan`, `exp`, `exp2`, `exp10`, `expm1`, `log`, `log2`,
`log10`, `log1p`, `pow`, `fmod`, `atan`, `asin`, `acos`, `sinh`, `cosh`, and `tanh`. Each function has a ladder of
up to six rungs: `strict`, `relaxed`, `mid3`, `mid2`, `mid1`, and `fast`. The rungs come from weighted minimax (Remez)
fits on the reduced domain (`helpers/mathfit.py` writes `mathkernels.toml`). Which mid rungs exist depends on the
function and dtype, so a caller asks by bound: `--max-ulp` or `--max-abs` returns the cheapest rung that holds it.
`strict` buys IEEE special values and the full domain at the price of accuracy elsewhere. For `sin` f64, `strict`
measures 2.58 ulp and `relaxed` 1.61 ulp. The errors of one-argument f32 kernels are measured over every input.

The `scalar` rendering gives the same kernels as one-lane C, which a compiler vectorizes inside the caller's loop.
The command line does not take it as an ISA: it is the candidate matrix's approximation axis
(`alloy/isa/approximation.py`), and its kernels pass the same error gate as the vector ones.

`tiers` lists the bare Taylor and Chebyshev polynomials on the reduced domain with their absolute error, without the
range reduction. The tiers are a reference for how degree buys accuracy. Code should come from `kernel`. `time`
measures nanoseconds per element of every rung on this machine, and of the same loop calling scalar libm and,
where the compiler vectorizes the call, libmvec.

## Cost of an instruction

A `lookup` ends with a `cost:` line when `costs.toml` has the row: µops, latency, and cycles per instruction in a
stream, as llvm-mca models the row's compiled instruction. x86 rows are modelled on Zen 4 (`znver4`, the host of
beverin's MI300A) and Arm rows on Neoverse V2 (`neoverse-v2`, GH200's Grace). The cost is the arithmetic's own cost.
Clang folds a row's operand load into the instruction, so `helpers/isacost.py` measures the register form instead.
The column records 307 of 349 rows that name a mnemonic. The rest are rows whose instruction the compiler replaced.

The column shows what an intrinsic name hides. On Zen 4 a 512-bit `vaddpd` has the latency of a 256-bit one and
half its throughput, because Zen 4 issues it as two 256-bit halves. Where AVX-512 wins on Zen 4, masking and the
lower instruction count account for it. Rerun `python helpers/isacost.py` after changing the table.

## CUDA and HIP

`cuda` and `hip` are targets of device code (`alloy/isa/simt.py`, `simt.toml`), because a GPU thread has no vector
intrinsics of its own. A row is an expression one thread evaluates (`fmaf`, `__expf`, `__fdividef`, `rsqrtf`, a
packed `__hadd2`, a 16-byte `float4` load) or statements one warp runs (a shuffle reduction, a broadcast, a ballot,
an `atomicAdd`). The rows keep the differences an author gets wrong from memory. CUDA's cross-lane intrinsics take a
member mask first (`__shfl_down_sync`), and its warp has 32 lanes. HIP's take none (`__shfl_down`), its wavefront has
64 lanes on CDNA (MI200, MI300), so a reduction starts at `warpSize/2`, and its ballot is a 64-bit mask.

`python -m alloy.isa.simt verify` checks every row with a generated program: one warp runs the row on every thread,
and the host compares each thread's value with the row's C reference. A dialect whose GPU the machine has is run; the
other is compiled for its targets (gfx90a and gfx942 for HIP) and recorded as compiled, not run. The recorded checks
ran on an NVIDIA RTX 4050, where all 11 rows are correct, and compiled all 11 HIP rows for both CDNA targets.

## Tenstorrent Tensix

`tensix` is a target of its own (`alloy/isa/tensix.py`), because Tensix has no SIMD intrinsics. A row is the
compute-kernel call that applies an op to a 32x32 tile in the destination registers (DST). Unary math (`exp`, `log`,
`sqrt`, `rsqrt`, `recip`, `abs`, `neg`, `tanh`, `sin`, and `cos`) runs on the SFPU. Binary arithmetic has two rows.
The FPU row (`add_tiles`) reads both operands from SrcA and SrcB, which hold TF32. The SFPU row (`add_binary_tile`)
copies both operands into DST and keeps f32. The dtypes are `f32` and `bf16`, since Tensix has no f64.

Each row is verified by running it. `tensix_harness.py` builds a one-core program from an inline reader, a compute
kernel around the row's call, and a writer, launches it with `ttnn.generic_op`, and compares the result with torch.
`python -m alloy.isa.tensix verify` runs every row on Tenstorrent's simulator ttsim (v1.16.0, Blackhole) inside a
pinned tt-metal 0.8x release image and records the result in `tensix_verified.toml`. The CI job `tensix` reruns it.
All 34 row and dtype pairs pass. The measured errors are what a kernel author needs to know.

| Path | f32 max relative error | bf16 |
|---|---|---|
| SFPU unary (`exp_tile`, `log_tile`, ...) | 6e-8 to 1.2e-7 | 4e-3 to 6e-3 |
| FPU binary (`add_tiles`, `mul_tiles`) | 4.9e-4 (add), 2.0e-3 (mul) | 2e-3 to 9e-3 |
| SFPU binary (`add_binary_tile`, ...) | 4e-8 to 7e-8 | 2e-3 to 6e-3 |

Full f32 needs `fp32_dest_acc_en`, and `UnpackToDestFp32` for tiles copied into DST. Without them f32 data passes
DST at bf16 precision (2^-9). The FPU error does not improve at the `HiFi4` fidelity, because SrcA and SrcB hold TF32.

tt-metal renamed the kernel scaffolding between 0.6x and 0.8x. In 0.6x a kernel has `namespace NAMESPACE { void MAIN }`
and starts with `init_sfpu` or `binary_op_init_common`, while 0.8x has `kernel_main()`, `compute_kernel_hw_startup`,
and `copy_init`. The headers moved from `compute_kernel_api/` to `api/compute/`. A row whose call was renamed holds
both spellings (`add_tiles_init` in 0.6x, `add_init` in 0.8x), and the harness builds either version.

Two limits apply to the simulator. ttsim does not model `SFPLOADMACRO`, so verification runs with
`TT_METAL_DISABLE_SFPLOADMACRO=1` and tt-metal takes its plain SFPU path. ttsim also speaks only the current
simulator interface, which tt-metal 0.6x does not, so 0.6x spellings are checked on hardware. The Daisytuner Blackhole
runs 0.6x, and its jobs live in the `alloy-tenstorrent` repository.

On that Blackhole (tt-metal 0.63, runs of 2026-11-16) every row compiles and runs, and 30 of the 34 row and dtype
pairs hold the table's bound. All six FPU pairs pass, and so do 12 of the 14 SFPU rows at each dtype. The two f32
rows that miss the bound are `log` and `tanh`. tt-metal 0.63 computes `log` with a low-order approximation and `tanh`
from a lookup table, and their relative error near the function's zero exceeds 0.3 and 0.1. The two rows carry a
`note` that the lookup prints. The job reports only exit codes, so it gives these error ranges and not exact values,
and it does not name the two failing bf16 rows.

The Python side of `ttnn.generic_op` also differs in 0.6x, and the harness handles both versions. In 0.6x the
runtime arguments are nested lists, `SourceType` and `UnpackToDestMode` live in `ttnn._ttnn.program_descriptor`, and
a kernel has 32 circular buffers, so `unpack_to_dest_mode` takes 32 entries where 0.8x takes 64.

## Commands

| Command | Answer |
|---|---|
| `lookup <isa> <op> <dtype>` | the row, its cost and its check; `--json` for a record |
| `reverse <name>` | what an intrinsic, recipe step, library symbol or mnemonic computes |
| `assist <name>` | what a hardware assist helps with |
| `kernel <isa> <function> <dtype>` | a math kernel as intrinsics; `--max-ulp`/`--max-abs` pick the rung |
| `tiers <function>` | the bare polynomials and their absolute error |
| `time <isa> <function or all> <dtype>` | nanoseconds per element of each rung and library call here |
| `schedule <isa>`, `skeleton <isa> <schedule> <dtype>` | legal loop shapes and a compiled loop in one |
| `validate [<isa> <op> <dtype>]` | the check over everything this host runs, or one row |
| `lookup cuda <op> f32`, `lookup hip <op> f32` | a device-code row and its check |
| `host`, `ops`, `isas` | what runs here, the op set, the targets |

## Maintaining the table

1. Add or change a row in `intrinsics.toml`, checking the spelling in the clang resource headers. The
   `skills/alloy-isa-gen` skill walks through it.
2. Run `python -m alloy.isa validate` and the `tests/test_isa*.py` suite.
3. Rerun `python helpers/isacost.py`, and `python helpers/mathfit.py` when a kernel changed.
4. Regenerate the skill pages with `python -m alloy.isa.render` and commit them with the table.
5. For a Tensix row, edit `tensix.toml` and run `python -m alloy.isa.tensix verify` (docker).
6. For a CUDA or HIP row, edit `simt.toml` and run `python -m alloy.isa.simt verify` on a machine with a GPU.
