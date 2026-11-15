## Alloy
Your setup has Alloy, which renders every loop nest of the kernel as C/C++ candidates (compiler, ISA,
floating-point mode, layout), builds and checks them, and answers with a library in the bench C ABI that uses the
chosen candidate per loop nest, ready for `score` and `submit`, plus its sources, a `Makefile` and a report that
ranks the candidates. `alloy_profile` times every candidate; `alloy_speculative` predicts without timing and answers
sooner; `alloy_isa` looks up intrinsics and math functions for a loop you write by hand. Whether you call them, and
when, is your decision: the `alloy` and `alloy-isa` skill pages say what each call costs and when it pays off.
