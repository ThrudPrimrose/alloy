---
name: alloy-isa
description: "How to use the alloy_isa tool: ask whether an operation on your data runs on a target (a CPU vector ISA, a GH200, MI200 or MI300A GPU, or a Tensix core), and get the checked code, the instruction steps, and the setup, or the reason it does not run and the nearest requests that do. Also math functions (sin, exp, log, pow, ...) as C kernels at the error bound you need, the device rows of HIP and CUDA, matrix tiles in f16, bf16, and FP8, and what a disassembled instruction computes. Read it before writing intrinsics, a device kernel's inner loop, or a matrix-core kernel by hand."
when: Before writing intrinsics, a wavefront or warp primitive, or a matrix-core (MFMA, wgmma) kernel by hand, and when a loop calls a math function the compiler left scalar.
---

# Checked instructions with `alloy_isa`

The compiler vectorizes most loops on its own. Write intrinsics or a matrix-core kernel only for a loop it left
slow, and check the result with `score`. Ask `alloy_isa` instead of recalling a spelling: its answers are checked
(compiled, and run where this machine has the hardware), and a refusal says what would run instead.

Start with `command="host"`: the CPU ISAs this machine runs. Every answer's `check` says where it was checked: `run`
names the hardware or simulator it ran on (this machine, a recorded run on an MI250X, MI300A, or GH200, or ttsim),
`compiled` means built for the target and not run, and `unverified` means neither.

## One request form: `ask`

`command="ask", arguments=[<target>, <op>, --<operand> <space:dtype:shape[:layout[:swizzle]]>, ...]`

- **Targets.** `avx2`, `avx512`, `avx512_fp16` (AVX-512 with f16 arithmetic, Sapphire Rapids on; Zen 4 has none), `neon`, `sve`, `sme`; `sm90` (GH200's H100); `gfx90a` (MI200, the MI250X);
  `gfx942` (MI300A); `tensix`; `softhier` (SoftHier v1 on the GVSoC simulator).
- **Operations.** Six primitives on your data:
  - `load` and `store`;
  - an elementwise operation or a math function (`add`, `fma`, `exp`, `sin`, ...);
  - the reductions `reduce_add`, `reduce_min`, and `reduce_max`;
  - the inclusive prefix sum `scan_add`;
  - `mma` (D = A x B + C on tiles);
  - `copy`, which moves data between two memories.
- **Operands.** `space:dtype:shape[:layout[:swizzle]]`, for example `global:f32:4096` or
  `shared:bf16:64x64:row_major:xor:8`. Operands are named `--a --b --c` for `mma`, `--src --dst` for `copy`, and
  `--x` for the rest.
  - Spaces: `register`, `vector`, `tile_register`, `shared`, `global`, `constant`.
  - Layouts: `row_major`, `col_major`.
  - Swizzles: `none`, `b32`, `b64`, `b128` (the TMA swizzles of `sm90`), `xor:8` (the LDS swizzle of CDNA).
  - The shape is the extent of your data, not of one register. A `broadcast` takes its scalar source as
    `--x register:f64` (or `register:f64:1`).
- **Options.** `--unit <name>` pins an implementation, for example `--unit tma`. `--max-ulp` bounds a math
  function's error.

The answer has one of three states:

- **feasible**: the unit that runs it, the `steps` with how often each runs (`6 x vector: _mm512_add_ps`), the
  `setup` (the exact `build` line; on a CPU the `header` and the compiler `flags`; on AVX-512 the row's `masked`
  form for the last block and the `mask` k it takes; on a GPU the tensor map, shared-memory size and alignment,
  launch, and the FP8 encoding), the `code` to copy, and the `check` (above).
  - The `code` is self-contained: a GPU, SME, or tile answer carries the helper functions it calls inline, trimmed
    to the requested type and shape, followed by the kernel or device function. There is no Alloy header to
    include: save the code under the file name the `build` line names and run that line.
  - On a CPU the `code` is one C statement on the operand names of the row's signature (`v = _mm512_add_pd(a,
    b);`); a math function's `code` is its kernel with its includes.
- **infeasible**: the `reason`; the `nearest` requests the target takes, so ask one of them; the `block` the shape
  must be a whole multiple of; and the `fix` for the rest (a mask, a scalar remainder loop, padding, another swizzle).
- **invalid**: the request itself is malformed (operands missing, shapes that do not chain, mixed types). The answer
  says what was expected.

`command="ask-all"` takes several requests, one per argument (`"copy src=global:f16:256x256
dst=shared:f16:64x64:row_major:xor:8"`, `"mma a=... b=... c=..."`), as one kernel. The answer says which copy fills
which mma operand, or why they do not combine.

## Asynchronous work: `wait` and `fence`

A TMA copy, a `wgmma`, and the CDNA LDS copy run asynchronously: their answer has an `async` line with the token that
completes the work, the `wait` request for it, and the fences that must come before the issue. Reading the result
before the wait is a race, and issuing without the fence reads stale data.

- `command="ask", arguments=["sm90", "wait", "--on", "mbarrier"]` gives the wait's instruction. Tokens: `mbarrier`
  (TMA load), `bulk_group` (TMA store), `cp_async_group`, `wgmma_group` on `sm90`; `vmcnt` (global loads, LDS DMA)
  and `lgkmcnt` (LDS) on `gfx90a` and `gfx942`; `noc` and `cb` on `tensix`; `idma` and `redmule` on `softhier`.
- `command="ask", arguments=["sm90", "fence", "--kind", "proxy"]`: `proxy` (thread writes to shared memory, or an
  mbarrier's init, before TMA or `wgmma` reads them) and `operand` (before a `wgmma` after touching its accumulator
  registers) exist on `sm90` only; the AMD GPUs order these in hardware or with `__syncthreads`.
- In `ask-all`, list the waits and fences between the requests (`"fence kind=proxy"`, `"wait on=mbarrier"`). A list
  that states none gets them back in order (`order:` lines); a list that states some must state all, and a request
  that reads before its wait, or issues without its fence, is refused with the missing request and where it goes.
  Double buffering is two copies into two tiles, each waited on just before the mma that reads it.

## What each target runs

- **CPUs** (`avx2`, `avx512`, `neon`, `sve`). Data is one run of elements (`vector:f32:96`); a 2-D shape is refused,
  and the flattened run is offered as nearest. A length that is not a whole multiple of the lanes is refused with the
  multiples below and above, and with how to finish: a mask on AVX-512 and SVE, a scalar remainder loop on AVX2 and
  NEON. `ask avx512 load` (or `store`, `gen_mask`) shows the masked spelling and how to build the mask. A reduction
  over many registers combines lane-wise, then once across lanes; a scan carries the last lane of each register into
  the next. On `sve` the lane count is known at run time only: a request for N elements (`vector:f64:64`) is
  answered as one `svwhilelt` loop. `reduce_add` and `scan_add` reassociate, so they need permission to; min and max
  are exact. A CPU has no matrix unit: `mma` is an FMA loop the compiler vectorizes, on row-major arrays in global
  memory: `--a global:f64:64x64 --b global:f64:64x64 --c global:f64:64x64` (D = A x B + C).
- **`sme`.** FMOPA outer products into ZA, f32. No evaluated CPU has SME, so the answer is checked by compiling and
  under an emulator.
- **`sm90`** (GH200). `copy` from global to shared is a TMA load: a tensor map, a 128B swizzle (`b128`), an
  mbarrier, and 1024-byte alignment. `mma` is `wgmma` on one warpgroup (128 threads) per 64 rows. B is held
  transposed (N rows of K) because wgmma reads both inputs K-contiguous.
- **`gfx90a`** (MI200) **and `gfx942`** (MI300A). `copy` from global to LDS is two 16-byte loads per thread, each
  chunk c of row r stored at slot c ^ (r % 8) (`xor:8`). `mma` is a 32x32 MFMA per wave64, four waves per 64x64
  block. B is held transposed here too.
- **Matrix types on the GPUs.**
  - `--in f16` and `bf16` run on `sm90`, `gfx942`, and `gfx90a`.
  - `e4m3` and `e5m2` (FP8) run on `sm90` and `gfx942`; MI200 (`gfx90a`) has no FP8.
  - The accumulator is f32. K is a multiple of 64 for the 16-bit types and of 128 for FP8: every K block is one row
    of 128 bytes.
  - FP8 is encoded differently per GPU, and the answer names the encoding: gfx942 reads FNUZ (no infinity, no
    negative zero, bias 8 or 16), sm90 reads OCP (bias 7 or 15). Convert with the type the answer names
    (`__hip_fp8_e4m3_fnuz`, `__nv_fp8_e4m3`), never by reinterpreting bytes from the other GPU.
- **`tensix`.** 32x32 tiles in DST: SFPU rows keep f32, FPU rows (`add_tiles`, `matmul_tiles`, `reduce_tile`) read
  TF32 sources. The answer gives the tile calls; `command="lookup", arguments=["tensix", "<op>", "f32"]` prints the
  error each row measured on the simulator.
- **`softhier`.** SoftHier v1, a 2 x 2 mesh of clusters on the GVSoC simulator (not hardware). Data a kernel computes
  on sits in the cluster's TCDM (`shared`); HBM (`global`) and other clusters' TCDM are reached only by iDMA. Vector
  operations (`load`, `store`, `add`, `mul`, `fma`, `reduce_add`, `reduce_max`, f32 and f16) are RVV loops on the
  Spatz unit whose last `vsetvl` strip is the tail; `copy` between `global` and `shared` is an iDMA transfer (`wait
  --on idma`); `mma` is an f16 RedMulE product (`wait --on redmule`); `barrier --kind cluster` or `global`. The
  answer's code compiles alone with its `build` line; the SDK headers define functions, so the kernel and `main` share
  one file (`program`), and `arch` writes the configuration's header into the SDK first.

## Short forms

- `command="lookup", arguments=["avx2", "fma", "f64"]`: one op's intrinsic, signature, traps, and cost (llvm-mca
  latency and throughput). An op with no single intrinsic prints a recipe and its `code`: copy that, since it holds
  the operand order.
- `command="lookup", arguments=["hip", "reduce_add", "f32"]`: a device row of HIP or CUDA at its element type.
  - Rows: `fma`, `exp_fast`, `sin_fast`, `div_fast`, `rsqrt`, the reductions and `scan_add`, `broadcast`,
    `ballot_count` (lanes whose predicate holds), `add_half2`, `load_wide`, `atomic_add` in f32; in `f16` and
    `bf16`: `load`, `store` (one element, with `__half2float`, `__float2half_rn` or the bf16 forms), `load_x2`,
    `store_x2` (a pair, `__half22float2`, `__floats2half2_rn`), and `load_wide`, `store_wide` (8 elements in one
    16-byte access).
  - `command="ask", arguments=["sm90", "load", "--x", "global:f16:4096"]` moves global data: the widest of those
    rows whose elements per thread divide the extent, with how many threads run it.
  - A wavefront has 64 lanes on MI200 and MI300A. The row's code names `lanes` (= `warpSize`), `lane` (=
    `threadIdx.x % warpSize`, the lane in its warp), `v` (the lane's input), and `out`; the answer's `bind:` line
    says so, and a reduction loops from `lanes / 2`.
  - `lookup` takes the dialect (`hip`, `cuda`). `tile` and `ask` take the arch (`gfx90a`, `gfx942`, `sm90`), and
    matrix instructions (`mfma`, `wgmma`) are answered there.
- `command="kernel", arguments=["avx512", "sin", "f64"]`: a math function as C to paste in place of the library
  call. Functions: `sin`, `cos`, `tan`, `exp`, `exp2`, `exp10`, `expm1`, `log`, `log2`, `log10`, `log1p`, `pow`,
  `atan`, `asin`, `acos`, `sinh`, `cosh`, `tanh`, `fmod`. Add `<math.h>` and the ISA's header. Each rung lists its
  measured ulp:
  - `strict` gives libm's special values through one cold branch, and is a compile error under `-ffast-math`.
  - `relaxed` has no branch and needs finite inputs in its range.
  - `fast` gives about half the digits.
  - Ask by bound, not by rung: `"--max-ulp", "100"`, or `"--max-abs", "1e-9"`, returns the cheapest kernel that
    holds it.
- `command="time", arguments=["avx512", "sin", "f64"]`: nanoseconds per element of each rung and the library calls,
  measured here.
- `command="tile", arguments=["gfx90a", "gemm", "128", "128", "128", "--in", "bf16", "--acc", "f32"]`: a complete
  matrix-tile program, with its steps, layout, and build line.
- `command="reverse", arguments=["vfmadd231pd"]`: what a CPU instruction or a vector-library symbol
  (`_ZGVdN4v_sin`, `__svml_sin8`) computes. GPU assembly is not indexed: for that, ask the arch.
- `command="assist", arguments=["svexpa_f64"]`: what a hardware assist (`vscalefpd`, `svexpa`, `vrcpps`) helps with.
- `command="tiers", arguments=["sin"]`: the bare polynomials and their error, as a reference; take `kernel` for code.
- `command="skeleton", arguments=["avx512", "<schedule>", "f64"]`: a loop in a legal schedule; `command="schedule",
  arguments=["avx512"]` lists them.
