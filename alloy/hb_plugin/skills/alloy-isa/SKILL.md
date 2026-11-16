---
name: alloy-isa
description: "How to write vector intrinsics with the alloy_isa tool: which ISAs this machine runs, an op's intrinsic and its traps, math functions (sin, exp, log, pow, ...) as C functions at the error bound you need, loop skeletons in a legal schedule, and what a disassembled instruction computes. Read it before writing any intrinsic by hand."
when: Before writing intrinsics, and when a loop calls a math function the compiler left scalar.
---

# Writing intrinsics with `alloy_isa`

The compiler vectorizes most loops on its own: write intrinsics only for a loop it left scalar, and check the
result with `score`.

Ask `alloy_isa` instead of recalling a spelling. `command="host"` says which ISAs this machine runs; `lookup`,
`kernel` and `skeleton` answers carry a compiled check there and say `unverified` elsewhere.

- `command="kernel", arguments=["avx512", "sin", "f64"]`: `sin`, `cos`, `tan`, `exp`, `exp2`, `exp10`, `expm1`, `log`
  (`ln`), `log2`, `log10`, `log1p`, `pow`, `atan`, `asin`, `acos`, `sinh`, `cosh`, `tanh`, `fmod` as C functions to
  paste into the scope, replacing the library call (add `<math.h>` and the ISA's header: `<immintrin.h>` on x86,
  `<arm_neon.h>` or `<arm_sve.h>` on Arm). Each rung lists its measured ulp and contract:
  - `strict` gives libm's special values on every input through one cold branch, within its listed ulp elsewhere.
    It is a compile error under `-ffast-math`.
  - `relaxed` has no branch and needs finite inputs in its stated range.
  - `fast` trades about half the digits for speed. Use it where a tolerance allows.
  - `strict` buys special values and domain, not digits: it can be less accurate than `relaxed`.
  - The answer's `ladder` line lists every rung with its error and intrinsic count. Which `mid` rungs exist differs
    per function and dtype, so ask by bound, not by rung name: `arguments=["avx512", "sin", "f64", "--max-ulp",
    "100"]`, or `"--max-abs", "1e-9"` for a bounded function, returns the cheapest kernel that holds it.
- `command="time", arguments=["avx512", "sin", "f64"]`: nanoseconds per element of every rung and of the library
  calls, measured on this machine, when the intrinsic count is not enough to choose.
  A kernel pays off in a loop with other work: the gain is the call and its spills.
- `command="lookup", arguments=["avx2", "fma", "f64"]`: an op's intrinsic, signature and traps. An op with no single
  intrinsic prints a recipe and its `code`: copy that, it holds the operand order. Its `cost:` line is the compiled
  instruction's latency and cycles per instruction on this kind of CPU (llvm-mca).
- `command="reverse", arguments=["vfmadd231pd"]`: what a disassembled instruction or a vector library symbol
  (`_ZGVdN4v_sin`, `__svml_sin8`) computes.
- `command="assist", arguments=["svexpa_f64"]`: what a hardware assist (`vscalefpd`, `svexpa`, `vrcpps`) helps
  with, for a reduction you write by hand.
- `command="tiers", arguments=["sin"]`: bare polynomials on the reduced domain with their absolute error, without the
  range reduction; a reference, take `kernel` for code.
- `command="skeleton", arguments=["avx512", "<schedule>", "f64"]`: a loop in a legal schedule; `command="schedule",
  arguments=["avx512"]` lists the schedules.
- `command="tile", arguments=["sm90", "gemm", "128", "128", "128", "--in", "f16", "--acc", "f32"]`: a matrix tile
  plan with a complete kernel to copy. On `sm90` (GH200) it loads row-major f16 tiles with TMA into 128B-swizzled
  shared memory and multiplies them with `wgmma`; the answer gives the tensor map's parameters and the build line
  (`compute_90a`, `-lcuda`). On `gfx942` (MI300A) and `gfx90a` (MI250X) it loads into LDS with an XOR swizzle and
  multiplies with `v_mfma_f32_32x32x8_f16`. On `cpu` there is no matrix unit, and the answer is a vectorized FMA loop. B is given as
  N x K row-major on the GPUs. A shape or type the kernels do not cover is refused with what they take; the answer
  says `run` where this machine has the GPU, and `compiled` elsewhere.
- `command="ask", arguments=["sm90", "mma", "--a", "shared:f16:64x64", "--b", "shared:f16:64x64", "--c",
  "register:f32:64x64"]`: one form for every target (`avx2`, `avx512`, `neon`, `sve`, `sme`, `sm90`, `gfx942`,
  `gfx90a`, `tensix`) and every operation, including `mma` and `copy` with each operand's place, type, shape, layout,
  and swizzle (`space:dtype:RxC:layout:swizzle`, for example `shared:f16:128x64:row_major:b128`). The answer is feasible,
  with the unit that runs it (`--unit tma` pins one), its steps, its setup, and code, or infeasible, with the reason
  and the nearest requests the target takes. Ask one of those instead.
  The operations are six primitives on your data: `load` and `store` (`--src global:f32:96 --dst vector:f32:96`),
  elementwise operations and math functions, the reductions `reduce_add`, `reduce_min`, and `reduce_max`, the prefix
  sum `scan_add`, and `mma`; `copy` moves data between two memories. A shape is the extent of your data. A whole
  multiple of the target's block (the lanes of a register, a 32x32 Tensix tile, a 64-row GPU block) is feasible, and
  each step says how often it runs (`6 x vector: _mm512_add_ps`). Any other shape is infeasible, and the answer
  states the block, the multiples below and above as nearest requests, and how to finish the remainder (a mask on
  AVX-512 and SVE, a scalar loop on AVX2 and NEON, padding on Tensix).
