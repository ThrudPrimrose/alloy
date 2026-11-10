---
name: alloy-isa
description: "How to write vector intrinsics with the alloy_isa tool: which ISAs this machine runs, an op's intrinsic and its traps, math functions (sin, exp, log, pow, ...) as C functions at three accuracy levels, loop skeletons in a legal schedule, and what a disassembled instruction computes. Read it before writing any intrinsic by hand."
when: Before writing intrinsics, and when a loop calls a math function the compiler left scalar.
---

# Writing intrinsics with `alloy_isa`

The compiler vectorizes most loops on its own: write intrinsics only for a loop it left scalar, and check the
result with `score`.

Ask `alloy_isa` instead of recalling a spelling. `command="host"` says which ISAs this machine runs; `lookup`,
`kernel` and `skeleton` answers carry a compiled check there and say `unverified` elsewhere.

- `command="kernel", arguments=["avx512", "sin", "f64"]`: `sin`, `cos`, `tan`, `exp`, `exp2`, `exp10`, `expm1`, `log`
  (`ln`), `log2`, `log10`, `log1p`, `pow`, `atan`, `asin`, `acos`, `sinh`, `cosh`, `tanh` as C functions to paste
  into the scope, replacing the library call (add `#include <immintrin.h>` and `<math.h>`). Each level lists its
  measured ulp and contract:
  - `strict` gives libm's special values on every input through one cold branch, within its listed ulp elsewhere.
    It is a compile error under `-ffast-math`.
  - `relaxed` has no branch and needs finite inputs in its stated range.
  - `fast` trades about half the digits for speed. Use it where a tolerance allows.
  A kernel pays off in a loop with other work: the gain is the call and its spills.
- `command="lookup", arguments=["avx2", "fma", "f64"]`: an op's intrinsic, signature and traps. An op with no single
  intrinsic prints a recipe and its `code`: copy that, it holds the operand order.
- `command="reverse", arguments=["vfmadd231pd"]`: what a disassembled instruction computes.
- `command="skeleton", arguments=["avx512", "<schedule>", "f64"]`: a loop in a legal schedule; `command="schedule",
  arguments=["avx512"]` lists the schedules.
