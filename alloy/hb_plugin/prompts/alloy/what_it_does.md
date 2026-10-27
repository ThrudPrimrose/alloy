## Alloy
Your setup has Alloy, which builds a first fast version of the kernel for you. One call (`alloy_profile` or
`alloy_speculative`, whichever your tool list has) renders every loop nest as C/C++ candidates (compiler, ISA,
floating-point mode, layout), builds and checks them, and answers with a library in the bench C ABI that uses the
chosen candidate per loop nest, ready for `score` and `submit`, plus its sources, a `Makefile` and a report that
ranks the candidates. Call it first and `score` its library, then improve the loop nests the report flags, as the
`alloy` skill page explains.

