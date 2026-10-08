# Alloy design notes

Decisions as of 2026-10-08. Change one only with the owner's approval.

## What Alloy is

A code-generation backend for DaCe that compiles speculatively.

1. Input: a Python program written with the dace numpy frontend, with symbolic sizes (`dace.symbol`).
2. Python goes to an SDFG, which is split into regions: each top-level nest becomes its own translation unit, with its
   own compile command and its own static `.a`.
3. Alloy sweeps rendering candidates per region, verifies them, times them, and links the best one per region.
4. Output:
   - the full maximally optimized program;
   - a per-region report (`report.md` plus `report.json`) with what was good, what was bad, and why.
5. An "Alloy" skill tells agents how to write the input and how to call the tool. The paper evaluates agents with and
   without the report.

Alloy is a separate repository and is installed with uv. NestForge imports Alloy; Alloy never imports NestForge.
Imports of `hpcagent_bench` stay function-local.

## Sweep axes (CPU)

- Rendering: CPF-C (C23) and CPF-C++ (C++20).
- Compiler: gcc and clang. Always `-O3 -march=native`.
  - clang 22 needs `libomp-22-dev`, which this box lacks, so local runs use clang 21.
- Codegen knobs (`compiler.cpu.codegen_params`):
  - `loop_access_form`
  - `heap_ptr_restrict`
  - `const_scalar_abi`
  - `decl_placement`
  - `index_ctype` + `loop_index_type`, swept together. int32 is allowed only when the element-count bound fits.
  - `scalar_init_style`: screened once, then fixed.
  - Fixed: `const_init=on`; translation-unit split always on.
- FP levels:
  - `strict`
  - `contract` (FMA)
  - `noerrno` (`-fno-math-errno -fno-trapping-math`)
  - `reassoc`: only for regions with a reduction or scan.
  - `fast`: never when inputs can be NaN or Inf.
- Vector math library (libmvec / SVML / SLEEF): opened only when the region calls libm (sin, cos, exp, log, pow, ...).
- Pruning:
  - Skip timing a candidate whose `.o` hash duplicates one already timed.
  - Compiler remarks (`-Rpass-missed`, `-fopt-info-vec-all`) choose the next candidates. For example, an aliasing miss
    leads to trying `restrict` / by-value.

## Sweep axes (GPU)

- Thread-block dimensions, `__launch_bounds__`, codegen knobs, `-use_fast_math` as a GPU FP level.
- NVIDIA: nvcc and clang-cuda (local GPU).
- AMD: hipcc and raw clang with the AMDGPU target. Runs on a remote box; ask before every ssh.

## Verification

Each region candidate runs on fuzzed inputs from HPCAgent-Bench (`hpcagent_bench.fuzz` plus the input
distributions) and is compared against the region's own `strict` build, using the bench's tolerance.

## Timing

- Screen on 4 cores at a working set of 2-4x the LLC.
- Re-time the top 3 per region on the full machine at full size.
- Only the re-timed numbers are reported.
- Baselines: DaCe's default CPU codegen, then alloy-full.

## Report format

One table per region: the best candidate, the worst candidate, and the cause, taken from the compiler remark. Every
interesting win or loss also becomes an A/B folder in `samples/` (see `measurement.md`).
