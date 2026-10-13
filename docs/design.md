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
`api.generate(..., matrix=)` swaps it; every output folder keeps a copy). Code holds only the gating rules.

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
- Vector math library (libmvec / SVML / SLEEF): opened only when the region calls libm (sin, cos, exp, log, pow, ...),
  at its FP level's requirement: gcc reaches libmvec only under `-ffast-math`, so that build needs finite inputs.
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

Status: built (`alloy/evaluate/timing.py`). Every whole program verification builds wraps each region's entry in a
timer (`-Wl,--wrap`, `alloy_seconds_<symbol>()`), so a region is timed inside the program, after the regions before
it, without recompiling. Sizes, cores and repetitions come from `[timing]` in the matrix.

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
- The timer wraps each region's entry with `clock_gettime`; the region is an external call, so inlining is
  unchanged.
- Arms alternate forward and reversed order every round. A win needs a CI entirely below the reference's; otherwise
  it is a tie and the reference stays.
- Baselines: DaCe's default CPU codegen, then alloy-full, both timed as whole programs.

## Heuristic mode

Status: not built. Picks one candidate per region from the builds alone, without timing; the pick is still verified.

- FP level: a region with a reduction or scan gets `reassoc`; without one, `fast` unless the inputs can be NaN or Inf
  (then `noerrno` + `contract`). A failed verification falls back one level (`fast` to `noerrno`, `reassoc` to
  `contract`).
- `-ffast-math` stays on the region's compile, never on the link line: gcc then links `crtfastmath.o`, which sets
  FTZ/DAZ for the whole process, `strict` regions included.
- Compiler: the one that vectorized the most distinct source loops (`file:line` from the remarks; gcc's epilogue and
  versioned loops count once), ties broken by the widest vectors in bytes (clang `vectorization width` x element
  size, gcc `using N byte vectors`).
- Order: FP level, then compiler, then knobs. A failed verification lowers the FP level and keeps the compiler.
- Rendering and knobs: chosen from build signals (vectorized loops from remarks, packed vector instruction share,
  spills, `llvm-mca` throughput; GPU: occupancy from register and shared memory use). Evaluated as regret against
  the timed winner.

## Bench experiments: dace+alloy (decided 10-12; `alloy/bench.py`, adapters `alloy-par` / `alloy-canon`)

- Columns: `dace-par + alloy` and `dace-canon + alloy`: the bench's `parallel_cpu` / `canon_cpu` pipeline output is
  Alloy's input SDFG. Profile (timed) and speculative (heuristic, verify only) flavors of each.
- Framework columns (no judge): bench `dace_cpu_alloy` / `dace_cpu_canonicalize_alloy` (`AlloyFramework`, bench main
  4c14f18) call `compiled_winners`: each region's local winner, linked and built by DaCe; the bench times
  that program like any DaCe flavor (`hpcagent-bench job baseline`). Optimizers (`alloy-par` / `alloy-canon`) are the
  judged path below.
- Region coverage over 259 LLR kernels (10-12): `parallel_cpu` 257 outline, `canon_cpu` 215. canon misses 28 that
  keep a library node with its `CPU` (C++) expansion (Reduce 9, ScatterConflictCheck 7, Scan 4, ArgReduce 3, none 5)
  and 15 whose region needs `__dace_num_threads` (ExternalCall cannot type it); `inc` fails both. These record
  `unsupported`.
- 10-13: both fixed in DaCe extended. Regions never take a reserved `__dace*` symbol as an argument (e086e38); a
  library node whose implementation a pipeline chose stays whole as its own region, rendered with that implementation
  (`outline_to_external_calls(library_nodes=True)`, 83a95d2), while an unchosen one still expands into a nest Alloy
  generates. Its accumulation length: input elements per output element (reduce), the whole input (scan).
- 10-13 coverage re-run (dace 8fd302b): `parallel_cpu` 258/259, `canon_cpu` 252/259; the rest have no nest or
  library node left. CPF renders Reduce as an OpenMP `reduction` (canon argmax 515 ms -> 0.73 ms per call at 6M,
  Alloy's argmax run 594 s -> 97 s), never emits `omp critical`, and argmax / argmin reduce through the declared
  `arg_max_pair` / `arg_min_pair` reductions of `dace/arg_reduction.h`.
- Budget: verify every candidate locally, screen them locally at small sizes on few threads, many runners and
  compilers in parallel; start from each region's local winner; `/score` the top 5 per region on the judge while the
  kernel's budget (`resolve_kernel_timeout`) still holds one more score and the harness's own grade; `/submit` the
  best. Measured on argmax_value (16 cores): Alloy 23 s (candidates compile one per core), one judge `/score`
  200-240 s, the harness grade 144 s (noop). So L2 (300 s) submits the local winner unscored (judge: correct, 1.74x
  vs auto) and only L3 (600 s) scores; at L1 (180 s) Alloy plus the harness grade still times out on this box.
- Submission: CPF renders the outlined program in the bench C ABI (the bench's `cpf_bridge` preparation and
  `EntrySignature`), the region archives come from `Rendering.link` (DaCe extended 844ebca; the bench must pin it).
  No DaCe build, no libdace.
- OpenMP: the library links LLVM libomp, which exports `GOMP_*` and `__kmpc_*`, so gcc, clang, icx and nvc objects
  share it. Measured: `clang-21 -fopenmp=libgomp` emits no OpenMP calls (the pragmas are dropped), so libgomp would
  leave gcc as the only parallel compiler. Probe the judge process once for a second runtime.

## Report format

Status: built. Per region: the candidate table, then the re-timed arms with screening median, final median and CI,
speedup over the reference, and the winner. On top: alloy-full against DaCe default with its speedup.

One table per region: the best candidate, the worst candidate, and the cause, taken from the compiler remark. Every
interesting win or loss also becomes an A/B folder in `samples/` (see `measurement.md`).
