---
name: alloy-isa
description: "How to use the alloy_isa tool: ask whether an operation on your data runs on a target (a CPU vector ISA, a GH200, MI200 or MI300A GPU, or a Tensix core), and get the checked code, the instruction steps, and the setup, or the reason it does not run and the nearest requests that do. Also math functions (sin, exp, log, pow, ...) as C kernels at the error bound you need, the device rows of HIP and CUDA, matrix tiles in f16, bf16, and FP8, and what a disassembled instruction computes. Read it before writing intrinsics, a device kernel's inner loop, or a matrix-core kernel by hand."
when: Before writing intrinsics, a wavefront or warp primitive, or a matrix-core (MFMA, wgmma) kernel by hand, and when a loop calls a math function the compiler left scalar.
---

# Checked instructions with `alloy_isa`

The compiler vectorizes most loops on its own. Write intrinsics or a matrix-core kernel only for a loop it left
slow, and check the result with `score`. Ask `alloy_isa` instead of recalling a spelling: its answers are checked
(compiled, and run where this machine has the hardware), and a refusal says what would run instead.

Start with `command="host"`: the ISAs and GPUs this machine runs. An answer for anything else says `compiled` or
`unverified`, never `run`.

## One request form: `ask`

`command="ask", arguments=[<target>, <op>, --<operand> <space:dtype:shape[:layout[:swizzle]]>, ...]`

- **Targets.** `avx2`, `avx512`, `neon`, `sve`, `sme`; `sm90` (GH200's H100); `gfx90a` (MI200, the MI250X);
  `gfx942` (MI300A); `tensix`.
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
  - The shape is the extent of your data, not of one register.
- **Options.** `--unit <name>` pins an implementation, for example `--unit tma`. `--max-ulp` bounds a math
  function's error.

The answer has one of three states:

- **feasible**: the unit that runs it, the `steps` with how often each runs (`6 x vector: _mm512_add_ps`), the
  `setup` (tensor map, shared-memory size and alignment, build line, the FP8 encoding), the `code` to copy, and the
  `check`. The check is `run` (matched a reference on this machine), `compiled` (built for the target, no such
  hardware here), or `unverified`.
- **infeasible**: the `reason`; the `nearest` requests the target takes, so ask one of them; the `block` the shape
  must be a whole multiple of; and the `fix` for the rest (a mask, a scalar remainder loop, padding, another swizzle).
- **invalid**: the request itself is malformed (operands missing, shapes that do not chain, mixed types). The answer
  says what was expected.

`command="ask-all"` takes several requests, one per argument (`"copy src=global:f16:256x256
dst=shared:f16:64x64:row_major:xor:8"`, `"mma a=... b=... c=..."`), as one kernel. The answer says which copy fills
which mma operand, or why they do not combine.

## What each target runs

- **CPUs** (`avx2`, `avx512`, `neon`, `sve`). Data is one run of elements (`vector:f32:96`); a 2-D shape is refused,
  and the flattened run is offered as nearest. A length that is not a whole multiple of the lanes is refused with the
  multiples below and above, and with how to finish: a mask on AVX-512 and SVE, a scalar remainder loop on AVX2 and
  NEON. A reduction over many registers combines lane-wise, then once across lanes. `reduce_add` and `scan_add`
  reassociate, so they need permission to; min and max are exact. A CPU has no matrix unit: `mma` is an FMA loop
  the compiler vectorizes.
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
  TF32 sources. The answer gives the tile calls and the error measured on the simulator.

## Short forms

- `command="lookup", arguments=["avx2", "fma", "f64"]`: one op's intrinsic, signature, traps, and cost (llvm-mca
  latency and throughput). An op with no single intrinsic prints a recipe and its `code`: copy that, since it holds
  the operand order.
- `command="lookup", arguments=["hip", "reduce_add", "f32"]`: a device row of HIP or CUDA, in f32.
  - Rows: `fma`, `exp_fast`, `sin_fast`, `div_fast`, `rsqrt`, the reductions and `scan_add`, `broadcast`,
    `gen_mask`, `add_half2`, `load_wide`, `atomic_add`.
  - A wavefront has 64 lanes on MI200 and MI300A, so a reduction loops from `warpSize / 2`.
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
