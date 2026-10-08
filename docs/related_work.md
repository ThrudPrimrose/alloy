# Related work

Notes for the Alloy paper. Citation rule: cite arXiv or the publisher (DOI) only. Rows marked
**verified** come from `mpr-paper/references.bib`. Rows marked **check** have identifiers written from memory and
must be confirmed before they go into a `.bib`.

## Own prior work Alloy builds on

| work | relation to Alloy | cite |
|---|---|---|
| DaCe / SDFG (Ben-Nun et al., SC19) | Alloy's IR and frontend: numpy with `dace.symbol` sizes is the input | 10.1145/3295500.3356173 (verified) |
| CPF (Canonical Parallel Form, `mpr-paper`) | one maximally parallel form per program; Alloy specializes its rendering per region (CPF-C / CPF-C++) | own paper |
| Vectra (ICS'26, rejected) | resubmission positioned as agent aide plus codegen backend; Alloy is that backend's sweep and report | own paper |
| NestForge | agentic optimization harness; imports Alloy as its codegen backend | own tool |
| HPCAgent-Bench | kernel corpus (frozen at 679) and the fuzzed-input correctness gate Alloy reuses per region | own benchmark |
| KernelBench (Ouyang et al., 2025) | LLM kernel-writing benchmark; contrast for the agent evaluation | arXiv:2502.10517 (verified) |

## DaCe-side mechanisms Alloy uses

These are notes, not citations; pull requests are not citable under the rule above.

- **ExternalCall library node (dace extended).** It outlines a top-level nest into a static `.a` with a recorded
  signature, `link_flags` and a global forward declaration. Alloy compiles each region as one such library with its own flags.
- **spcl/dace#2658 "Function regions" (open).** It outlines long codes into multiple functions and translation units,
  for faster compiles, fewer runtime aliasing checks and better vectorization. Alloy takes the idea of one translation
  unit per region and does not depend on the PR.
- **`split_nsdfg_translation_units` / `external_translation_units` (extended).** One `.cpp` per top-level nest; the
  existing per-TU split.
- **Readable CPU codegen knobs (`compiler.cpu.codegen_params`).** The sweep axes: `loop_access_form` (ptr-increment),
  `heap_ptr_restrict`, `const_scalar_abi`, `decl_placement`, `scalar_init_style`, `index_ctype`,
  `loop_index_type`. Removed on 10-08 as spelling-only: `index_fn_qualifier`, `loop_bound_cmp`, `loop_decl_style`,
  `inline_full_array_nsdfg`.

## Autotuning and search over code variants

| work | what it tunes | contrast with Alloy | cite |
|---|---|---|---|
| Halide (Ragan-Kelley et al., PLDI'13) | schedule separate from algorithm | Alloy tunes rendering and compiler choices of a fixed SDFG, not the schedule | 10.1145/2491956.2462176 (verified) |
| Loop transformation recipes (Rudy et al., 2010) | recipe-driven code generation plus autotuning | closest in spirit: generate variants, measure | 10.1007/978-3-642-13374-9_4 (verified) |
| Tiramisu (Baghdadi et al., CGO'19) | polyhedral layer under a scheduling language | schedule space, not codegen spelling | 10.1109/CGO.2019.8661197 (verified) |
| OpenTuner (Ansel et al., PACT'14) | generic search over flags and parameters | Alloy's search is per region and verified; OpenTuner is program-wide | 10.1145/2628071.2628092 (check) |
| ATLAS (Whaley, Dongarra, SC'98) | install-time BLAS kernel search | library-specific | 10.1109/SC.1998.10004 (check) |
| FFTW (Frigo, Johnson, Proc. IEEE 2005) | runtime planner over codelets | library-specific | 10.1109/JPROC.2004.840301 (check) |
| TVM (Chen et al., OSDI'18) / Ansor (Zheng et al., OSDI'20) | tensor-program search with cost models | DL operators; Alloy is general numpy with symbolic sizes | arXiv:1802.04799 / arXiv:2006.06762 (check) |
| Milepost GCC (Fursin et al., IJPP 2011) | ML-predicted compiler flags | Alloy measures instead of predicting, per region | 10.1007/s10766-010-0161-2 (check) |
| CompilerGym (Cummins et al., CGO'22) / MLGO (Trofin et al., 2021) | RL environments and policies for compiler decisions | inside the compiler; Alloy sits above it | arXiv:2109.08267 / arXiv:2101.04808 (check) |

## Vectorization and math libraries

| work | relevance | cite |
|---|---|---|
| Maleki et al., "An Evaluation of Vectorizing Compilers" (PACT'11) | compilers miss many vectorizable loops; supports the remark-driven "why" column | 10.1109/PACT.2011.68 (verified) |
| Callahan et al., vectorizing compiler test suite (SC'88) | historical baseline for vectorizer evaluation | 10.1109/SUPERC.1988.44642 (verified) |
| Allen, Kennedy, "Automatic translation of FORTRAN programs to vector form" (TOPLAS) | origin of dependence-based vectorization | 10.1145/29873.29875 (verified) |
| Polly (Grosser et al., PPL 2012) | polyhedral optimization inside LLVM | 10.1142/S0129626412500107 (verified) |
| SLEEF (Shibata, Petrogalli, TPDS 2020) | vector math library, one of the vector-lib axis values | arXiv:2001.09258 (check) |

## Measurement methodology

| work | relevance | cite |
|---|---|---|
| Hoefler, Belli, "Scientific Benchmarking of Parallel Computing Systems" (SC'15) | medians, CIs and reporting rules; the paper's figures follow it | 10.1145/2807591.2807644 (verified) |
| Mytkowicz et al., "Producing wrong data without doing anything obviously wrong!" (ASPLOS'09) | layout and link order bias measurements. Alloy hit this: per-arm buffers faked 20-35% effects (`samples/index_width`) | 10.1145/1508244.1508275 (check) |
| Curtsinger, Berger, "Stabilizer" (ASPLOS'13) | randomizes layout to make performance claims sound | 10.1145/2451116.2451141 (check) |
