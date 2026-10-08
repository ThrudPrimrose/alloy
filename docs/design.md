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

Status: built (one factor at a time; combining winners is open).

All axes live in `alloy/configuration_matrix.toml` (checked by `alloy/configuration_matrix.py`;
`alloy build --matrix` swaps it; every output folder keeps a copy). Code holds only the gating rules.

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

Status: not built.

- Thread-block dimensions, `__launch_bounds__`, codegen knobs, `-use_fast_math` as a GPU FP level.
- NVIDIA: nvcc and clang-cuda (local GPU).
- AMD: hipcc and raw clang with the AMDGPU target. Runs on a remote box; ask before every ssh.

## Verification

Status: built. Each candidate is linked into the whole program (its region's archive at a fixed path, every other
region at its reference archive), rebuilt by DaCe's command-cache replay (about 1 s), and run in a fork-server child on
fuzzed draws from the bench manifest. The reference runs three times per draw: an output that changes between those runs
(a parallel reduction combining partial sums in thread order) is compared under `band` at every level.

Each region candidate runs on fuzzed inputs from HPCAgent-Bench (`hpcagent_bench.fuzz` plus the input
distributions) and is compared against the region's own `strict` build. Each FP level names its test:

- `exact`: bit-identical to the reference (the `strict` level itself), across compilers too. A compiler with its own
  math library (nvc's `libnvcpumath`) therefore fails `strict` on regions that call libm; that is reported, not
  excused (owner decision, 2026-10-08).
- `band`: HPCAgent-Bench's `compare_arrays` with its per-precision band (fp64 rtol 1e-9, atol 1e-11) and the
  accumulation floor `eps_acc(p) * sqrt(l) * ||ref||_inf`. `sqrt(l)` is the random-walk growth of the difference
  between two summation orders (Higham, Sec. 4.5); the bench measured `log2(l)` rejecting correct dynamic-schedule
  reductions and `l` admitting a single lost update. `l` is `Region.accumulation_length`, derived exactly from the
  SDFG's WCR edges (matmul: K; square matmul: the contracted N; row sum: N; elementwise: 1). When
  `eps_acc * sqrt(l) >= rtol` the bench raises `UngradeableTolerance`; the report shows "ungradeable", never a pass.

## Timing

Status: not built.

- Cache: the largest cache level in `/sys/devices/system/cpu/cpu*/cache`, summed over its distinct instances
  (`shared_cpu_list`). Every timed working set is 2-4x that, so no run fits in cache.
- Cores: the usable CPUs (`os.sched_getaffinity`, what `nproc` counts), one hardware thread per physical core
  (`thread_siblings_list`); SMT siblings are never used. `OMP_PLACES=cores`, `OMP_PROC_BIND=close`,
  `OMP_NUM_THREADS` = the physical cores used.
- Screen on 4 physical cores at the 2-4x working set.
- Re-time the top 3 per region on every physical core at full size.
- Only the re-timed numbers are reported.
- Before timing, one draw at the timing size is compared to the reference: the fuzz draws are capped small, and a
  candidate can break only at large sizes (int32 index overflow).
- Every arm of a region is loaded into one process and called alternately on one set of buffers (`measurement.md`).
- A shim archive times each region's entry with `clock_gettime`; the region is an external call, so inlining is
  unchanged.
- A win needs non-overlapping 95% CIs and survives a reversed arm order; otherwise it is a tie and the default stays.
- Baselines: DaCe's default CPU codegen, then alloy-full, both timed as whole programs.

## Report format

Status: build report built (candidates, objects, remarks); good-vs-bad with times is not.

One table per region: the best candidate, the worst candidate, and the cause, taken from the compiler remark. Every
interesting win or loss also becomes an A/B folder in `samples/` (see `measurement.md`).
