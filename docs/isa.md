# The ISA lookup

`alloy.isa` answers the questions an agent or a person asks while writing vector code by hand. Which intrinsic spells
this op on this ISA? What does a disassembled instruction compute? Which math kernel holds this error bound, and what
does it cost? Every answer says whether it was checked on this machine. The command line is `python -m alloy.isa`, and
agents reach it as the `alloy_isa` tool of the `alloy-isa` and `alloy` packets.

## What the table holds

The table spells 37 abstract ops (`alloy/isa/ops.py`) on five SIMD ISAs (504 `(isa, dtype, op)` rows plus 24 hardware assists). The ops cover loads and stores, gather and
scatter, arithmetic, `fma`, `sqrt`, comparisons and `select`, integer bit/shift/logical operations, the reductions `reduce_add`,
`reduce_min`, and `reduce_max`, the scan `scan_add`, `gen_mask`, and the math functions `exp`, `sin`, and `cos`. The ISAs are AVX2, AVX-512, NEON, SVE, and RVV, and `avx512_256` names AVX-512 under
a 256-bit compiler width, so it has no spellings of its own.

| ISA | f64 | f32 | f16 | i64 | i32 | Total rows | Assists |
|---|---|---|---|---|---|---|---|
| `avx2` | 26 | 30 | 14 | 16 | 16 | 102 | 3 |
| `avx512` | 27 | 31 | 15 | 16 | 16 | 105 | 9 |
| `neon` | 26 | 30 | 14 | 16 | 16 | 102 | 4 |
| `sve` | 27 | 31 | 15 | 16 | 16 | 105 | 6 |

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
The column records 474 of the 504 CPU rows in `costs.toml`. The rest are composite recipes or rows without a single modelled mnemonic.

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
other is compiled for its targets (`gfx90a` and `gfx942` for HIP, `sm_90a` for CUDA) and recorded as compiled, not run. The recorded checks
(`simt_verified.toml`, run 2026-11-25) cover all 31 CUDA rows (verified on GH200; the five f64 rows on an A100) and all 31 HIP rows (verified on MI250X and
MI300A; the five f64 rows on an MI50, gfx906).

## Tenstorrent Tensix

`tensix` is a target of its own (`alloy/isa/tensix.py`), because Tensix has no SIMD intrinsics. A row is the
compute-kernel call that applies an op to a 32x32 tile in the destination registers (DST). Unary math (`exp`, `log`,
`sqrt`, `rsqrt`, `recip`, `abs`, `neg`, `tanh`, `sin`, and `cos`) runs on the SFPU. Binary arithmetic has two rows.
The FPU row (`add_tiles`) reads both operands from SrcA and SrcB, which hold TF32. The SFPU row (`add_binary_tile`)
copies both operands into DST and keeps f32. The dtypes are `f32` and `bf16`, since Tensix has no f64.
`reduce_add` and `reduce_max` run `reduce_tile` on the FPU: every data tile reduces into one DST tile against a scaler
tile (1 in the first row of each 16x16 face), and the value lands at `[0, 0]` of the packed tile. `scan_add` runs
`cumsum_tile` on the SFPU down each column, with `first` set only for the top tile of a column.

Each row is verified by running it. `tensix_harness.py` builds a one-core program from an inline reader, a compute
kernel around the row's call, and a writer, launches it with `ttnn.generic_op`, and compares the result with torch.
`python -m alloy.isa.tensix verify` runs every row on Tenstorrent's simulator ttsim (v1.16.0, Blackhole) inside a
pinned tt-metal 0.8x release image and records the result in `tensix_verified.toml`. The CI job `tensix` reruns it
and uploads the file it would write (artifact `tensix-verified`), so a new row, added with `pending = true`, is
recorded from CI. All 23 rows (46 row-and-dtype pairs) pass on ttsim. The measured errors are what a kernel author needs to
know.

| Path | f32 max relative error | bf16 |
|---|---|---|
| SFPU unary (`exp_tile`, `log_tile`, ...) | 6e-8 to 1.2e-7 | 4e-3 to 6e-3 |
| FPU binary (`add_tiles`, `mul_tiles`) | 4.9e-4 (add), 2.0e-3 (mul) | 2e-3 to 9e-3 |
| SFPU binary (`add_binary_tile`, ...) | 4e-8 to 7e-8 | 2e-3 to 6e-3 |
| FPU `mma` (`matmul_tiles`, over 2 K tiles) | 1.0e-3 | 2.9e-3 |
| FPU reduction (`reduce_tile`, sum and max of 2 tiles) | 8.3e-4 (sum), 0 (max) | 1.5e-6 (sum), 0 (max) |
| SFPU scan (`cumsum_tile`, 2 tiles of a column) | 5.7e-7 | 7.5e-3 |

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

On that Blackhole (tt-metal 0.63, runs of 2026-11-16 and card probes of 2026-11-18 in `tensix_card.toml`) every row compiles and runs, and 30 of the 34 earlier elementwise row-and-dtype
pairs held the table's bound. Quantitative card probes recorded in `tensix_card.toml` measure `exp_tile` at `1.73e-3` max relative error (bf16-level accuracy), `log_tile` at `0.0165` max absolute error (relative error > 1 near $x=1$), `sqrt_tile` at `5.54e-6` relative (`9.3e-8` with `legacy_compat = false`), and `div_binary_tile` at `2.43e-7` relative; `tanh_tile` misses the bound by 0.1--0.3 relative near zero. To restore f32 accuracy on tt-metal 0.63, `tensix.toml` ships two card-checked SFPI math rungs (`alloy_log_f32_sfpi` at 3.79 ulp / `2.26e-7` max relative error and `alloy_exp_f32_sfpi` at 2.0 ulp / `1.19e-7` max relative error over [-100, 100], saturating to inf and 0), which `alloy.tensixgen` automatically substitutes for `v06`.

## Arm SME and SoftHier v1

- **Arm SME (`sme`, `alloy_tile_sme.h`).** Outer-product matrix tile kernel (`svmopa_za32_f32_m`) into 2D `ZA` tiles (`SVL/32 x SVL/32`, f32) under `__arm_locally_streaming` mode with transposed `A` (streaming mode has no gather) and `svwhilelt` edge predication. Checked by cross-compilation and execution under QEMU (`-cpu max,sme=on`).
- **SoftHier v1 (`softhier`, `alloy/isa/softhier.py`, `softhier.toml`, `softhier_verified.toml`).** Simulated $2\times 2$ cluster mesh (`pulp.chips.soft_hier_old.flex_cluster` on pinned GVSoC; never pooled with native hardware timings). Covers 14 operations across Spatz RVV (`f32`/`f16` vector arithmetic and reductions), `iDMA` (`copy_1d`, `copy_2d`, `wait_idma`), `RedMulE` (`mma` in f16 with `(m,k,n)` config order and `wait_redmule`), and cluster/global barriers (`barrier_cluster`, `barrier_global`). All 19 row-and-dtype programs pass on GVSoC, and 8 of 8 planted mutants (wrong order, missing waits, invalid HBM loads) fail the gate.

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
| `ask <target> <op> --a ... --x ... --src ... --dst ...` | one request form for every target: feasible with its steps, or infeasible or invalid with the reason |

## Requests on logical data

`ask` takes one of six primitives on logical data (design: `notes/isa-design.md`, section 2.8 of the workspace): `load`
and `store`, an elementwise operation or a math function, a reduction (`reduce_add`, `reduce_min`, `reduce_max`), the
scan `scan_add` (the inclusive prefix sum), and `mma`. `copy` moves data between two memories. An operand is
`space:dtype:shape[:layout[:swizzle]]`, and its shape is the extent of the data, not of a register. A 2-D operand may
also give its layout as relayout operations (`--a-layout '<JSON>'`, `a_layout=<JSON>|@file` in `ask-all`;
`alloy.isa.layouts`). Every layout check compares index maps, so `b128` on 128-byte rows and `xor:8` are one layout.

Every lowering has a block, the extent one instruction takes: the lanes of a register (16 f32 on AVX-512), one 32x32
tile on Tensix, and the K block of a GPU product (128 bytes of a row: 64 f16 or bf16, 128 e4m3 or e5m2). A shape that is a whole multiple of the block is feasible, and
each step of the answer carries how often the request runs it:

```text
$ python -m alloy.isa ask avx512 add --a vector:f32:96 --b vector:f32:96
avx512 add: feasible on vector; check: run compiled kernel
  6 x vector: _mm512_add_ps
  setup header: #include <immintrin.h>
  setup flags: -mavx512f -mavx512dq
  setup masked: _mm512_mask_add_ps(src, k, a, b): the last block, under the mask k
  setup mask: k = _mm512_cmplt_epu32_mask(iota, n): k bit j set iff iota[j] < n, with iota = _mm512_setr_epi32(0..15), n = clamp(N - i, 0, 16)
  note: 6 registers: a loop of 6 iterations, one register each
v = _mm512_add_ps(a, b);
$ python -m alloy.isa ask avx512 add --a vector:f32:100 --b vector:f32:100
avx512 add: infeasible (shape): 100 f32 elements are not a whole multiple of the 16 f32 lanes of an avx512 register: 6 registers hold 96, 4 remain
  nearest: x vector:f32:96
  nearest: x vector:f32:112
  block: 16 (a shape the target takes is a whole multiple)
  fix: ask gen_mask for the last block's mask k, load with _mm512_maskz_loadu_ps(k, p), compute with _mm512_mask_add_ps(src, k, a, b), store with _mm512_mask_storeu_ps(p, k, v)
```

A refusal for a shape always states the block, the multiples below and above as requests that are feasible, and how
to finish the remainder (a mask on AVX-512 and SVE, a scalar remainder loop on AVX2 and NEON, padding to whole tiles
on Tensix). A reduction over several registers lists the lane-wise combination (`count` minus one times) and the one
horizontal step; a scan lists the in-register scan and the carry (the last lane of the register before, broadcast to
every lane, added to the next). On SVE the lane count is known at run time only, so a request for N elements is
answered as one loop over blocks under the `svwhilelt` predicate; a reduction combines the blocks with the `_m` form and
reduces once. `reduce_add` and `scan_add` associate differently from a scalar left fold, so they need
permission to reassociate; `reduce_min` and `reduce_max` are exact on finite lanes, and each row states its NaN rule.

On CUDA and HIP, `reduce_min` and `reduce_max` are `__shfl_down` trees into lane 0 and `scan_add` is a `__shfl_up`
scan in log2(lanes) steps (`simt.toml`). Tensix has no MIN pool, so `reduce_min` there is refused with the maximum of
the negated tiles. Not built yet: the Tensix moves and layout calls (`copy_tile`, `pack_tile`, `tilize`,
`transpose`); the lookup refuses them with `no_row`.

## GPU tile types

Each GPU tile kernel takes its input type as a template argument and accumulates in f32. A K block is 128 bytes of a
row for every type, so the LDS swizzle (chunk ^ row % 8), the 128B TMA swizzle, and the 32-byte step per instruction
are shared by all of them.

| Target | f16 | bf16 | e4m3 | e5m2 |
|---|---|---|---|---|
| `gfx90a` (MI250X) | `v_mfma_f32_32x32x8_f16` | `v_mfma_f32_32x32x8bf16_1k` | no FP8 MFMA | no FP8 MFMA |
| `gfx942` (MI300A) | `v_mfma_f32_32x32x8_f16` | `v_mfma_f32_32x32x8_bf16` | `v_mfma_f32_32x32x16_fp8_fp8`, E4M3FNUZ (bias 8) | `v_mfma_f32_32x32x16_bf8_bf8`, E5M2FNUZ (bias 16) |
| `sm90` (H100) | `wgmma m64nNk16 .f16` | `wgmma m64nNk16 .bf16` | `wgmma m64nNk32 .e4m3`, OCP (bias 7) | `wgmma m64nNk32 .e5m2`, OCP (bias 15) |

gfx942 reads the FNUZ encodings (no infinity, no negative zero, one more in the bias) and sm90 the OCP ones, so an FP8
answer names the encoding of its target. Each tile's program encodes its inputs by that bit layout and checks the
product against an f64 reference; every type compiles for its targets (`hipcc`, `nvcc -arch=sm_90a`), and a type
runs where the GPU is.

## Maintaining the table

1. Add or change a row in `intrinsics.toml`, checking the spelling in the clang resource headers. The
   `skills/alloy-isa-gen` skill walks through it.
2. Run `python -m alloy.isa validate` and the `tests/test_isa*.py` suite.
3. Rerun `python helpers/isacost.py`, and `python helpers/mathfit.py` when a kernel changed.
4. Regenerate the skill pages with `python -m alloy.isa.render` and commit them with the table.
5. For a Tensix row, edit `tensix.toml` and run `python -m alloy.isa.tensix verify` (docker).
6. For a CUDA or HIP row, edit `simt.toml` and run `python -m alloy.isa.simt verify` on a machine with a GPU.
