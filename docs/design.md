# Alloy design notes

Decisions as of 2026-10-26. Change one only with the owner's approval.

## What Alloy is

A per-scope code generation backend for DaCe: each scope is built under many configurations, every build is
verified, and the best one per scope is linked. Two products share one core:

1. **DaCe backend** (`alloy/dace_backend.py`). Input: an SDFG, a manifest optional. The SDFG already states the
   signature (argument order, every non-transient's shape and dtype, the symbols; outputs are the arguments it
   writes), so it carries no manifest. `SDFG.compile` hands over when `compiler.alloy.mode` (DaCe extended; `off`
   by default) is `speculative` or `profile`; the result is a `CompiledSDFG` with the SDFG's own signature, every
   scope linked from the archive Alloy picked.
   - Without a manifest only speculative mode runs: the sizes and value domains are unknown. Inputs are verified on
     draws derived from the SDFG (every size symbol odd, arguments uniform in [0, 1)) only when any value is valid
     (`inputs.domain_gap`: no `sqrt`/`log`/`pow`/... call, no integer argument that may index); otherwise each
     scope's default build ships. Only the default (64-bit) index width is built, since the real sizes are unknown.
   - Profile mode needs a manifest: it times at the declared sizes.
2. **HPCAgent-Bench tool and skill.** Input: NumPy plus a manifest (DaCe frontend to an SDFG, then 1); the manifest
   gives the value domains, size presets and constraints. C plus a manifest waits for the bench's C-to-NumPy
   translator. Shipped as a bench user plugin in `alloy/hb_plugin` (tool and skill there); the skill assumes the
   bench.

Per run: the program is split into scopes (each top-level nest its own translation unit, compile command and static
`.a`); Alloy sweeps candidates per scope, verifies them, times them (profile mode) or picks from the builds' reports
and outputs (speculative mode), and links the best one per scope. Output: the linked program and the report
([Report format](#report-format)). The paper evaluates agents with and without the report.

Alloy is a separate repository and is installed with uv. NestForge imports Alloy; Alloy never imports NestForge.
Imports of `hpcagent_bench` stay function-local.

## Sweep axes (CPU)

Status: built (one factor at a time; combining winners is open).

All axes live in `alloy/configuration_matrix.toml` (validated by the pydantic dataclasses of
`alloy/configuration_matrix.py`, which refuse unknown, missing and mistyped keys, then by its cross-reference check;
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
  - `reassoc`: only for scopes with a reduction or scan.
  - `fast`: never when inputs can be NaN or Inf.
- Loop tail (`[tails]`): `scalar_remainder`, `masked_remainder` (masked epilogue) and `full_mask` (every
  iteration masked) as compiler flags (gcc `--param=vect-partial-vector-usage=0/1/2`, clang
  `-prefer-predicate-over-epilogue`, which has no masked epilogue), the masked ones only on an ISA with masks the host
  runs (AVX-512, SVE); `sve_intrinsics` renders the scope's maps as explicit SVE loops (DaCe `SVEVectorization`, CPF
  renders them), only on an SVE host. A scope the SVE loop cannot express (a libm call) is a failed build naming why.
  Every build counts its masked instructions from the object; a masked tail without any is reported "not honored".
- Vector math library (libmvec / SVML / SLEEF): opened only when the scope calls libm (sin, cos, exp, log, pow, ...),
  at its FP level's requirement: gcc reaches libmvec only under `-ffast-math`, so that build needs finite inputs.
- Pruning (`alloy/heuristics/prune.py`, built): each compiler's default builds first, then the rest minus the cells
  that cannot change the code, each kept in the report with its reason:
  - no compiler vectorized a loop: no ISA or tail cell (explicit SVE loops stay);
  - every innermost trip count a constant multiple of an ISA's lanes x 4 (clang's interleave): no tail on that ISA;
    SVE's length is unknown at compile time, so never there;
  - an FP level only where it has something to rewrite: contract needs a multiply feeding an add, noerrno a libm or
    sqrt call, reassoc a reduction, fast any of those or a division or min/max.
  - A candidate whose object (and vector library) duplicates an earlier one is built but not verified or timed.
  - Open: compiler remarks (`-Rpass-missed`, `-fopt-info-vec-all`) choosing the next candidates, e.g. an aliasing
    miss leading to `restrict` / by-value.

## Sweep axes (GPU)

Status: not built.

- Thread-block dimensions, `__launch_bounds__`, codegen knobs, `-use_fast_math` as a GPU FP level.
- NVIDIA: nvcc and clang-cuda (local GPU).
- AMD: hipcc and raw clang with the AMDGPU target. Runs on a remote box; ask before every ssh.

## Verification

Status: built. Each candidate is linked into the whole program (its scope's archive at a fixed path, every other
scope at its reference archive), rebuilt by DaCe's command-cache replay (about 1 s), and run in a fork-server child on
fuzzed draws from the bench manifest. The reference runs three times per draw: an output that changes between those runs
(a parallel reduction combining partial sums in thread order) is compared under `band` at every level.

Each scope candidate runs on fuzzed inputs from HPCAgent-Bench (`hpcagent_bench.fuzz` plus the input
distributions) and is compared against the scope's own `strict` build. Each FP level names its test:

- `exact`: bit-identical to the reference (the `strict` level itself), across compilers too. A compiler with its own
  math library (nvc's `libnvcpumath`) therefore fails `strict` on scopes that call libm; that is reported, not
  excused (owner decision, 2026-10-08).
- `band`: HPCAgent-Bench's `compare_arrays` with its per-precision band (fp64 rtol 1e-9, atol 1e-11) and the
  accumulation floor `eps_acc(p) * sqrt(l) * ||ref||_inf`. `sqrt(l)` is the random-walk growth of the difference
  between two summation orders (Higham, Sec. 4.5); the bench measured `log2(l)` rejecting correct dynamic-schedule
  reductions and `l` admitting a single lost update. `l` is `Scope.accumulation_length`, derived exactly from the
  SDFG's WCR edges (matmul: K; square matmul: the contracted N; row sum: N; elementwise: 1). When
  `eps_acc * sqrt(l) >= rtol` the bench raises `UngradeableTolerance`; the report shows "ungradeable", never a pass.

## Timing

Status: built (`alloy/evaluate/timing.py`). Every whole program verification builds wraps each scope's entry in a
timer (`-Wl,--wrap`, `alloy_seconds_<symbol>()`), so a scope is timed inside the program, after the scopes before
it, without recompiling. Sizes, cores and repetitions come from `[timing]` in the matrix.

- Cache: the largest cache level in `/sys/devices/system/cpu/cpu*/cache`, summed over its distinct instances
  (`shared_cpu_list`). Every timed working set is 2-4x that, so no run fits in cache.
- Cores: the usable CPUs (`os.sched_getaffinity`, what `nproc` counts), one hardware thread per physical core
  (`thread_siblings_list`); SMT siblings are never used. `OMP_PLACES=cores`, `OMP_PROC_BIND=close`,
  `OMP_NUM_THREADS` = the physical cores used.
- Screen on 4 physical cores at the 2-4x working set.
- Re-time the top 3 per scope on every physical core at full size.
- Variants are ranked by their screened time; the re-timed time is reported beside it.
- Before timing, one draw at the timing size is compared to the reference: the fuzz draws are capped small, and a
  candidate can break only at large sizes (int32 index overflow).
- Every arm of a scope is loaded into one process and called alternately on one set of buffers (`measurement.md`).
- The timer wraps each scope's entry with `clock_gettime`; the scope is an external call, so inlining is
  unchanged.
- Arms alternate forward and reversed order every round. A win needs a CI entirely below the reference's; otherwise
  it is a tie and the reference stays.
- Baselines: DaCe's default CPU codegen, then alloy-full, both timed as whole programs.

## Speculative mode

Status: built (`alloy/heuristics/predict.py`). Picks one candidate per scope from the builds alone, without timing; the pick is still verified.

- FP level (shared with NestForge's defaults, owner decision 2026-10-26): a scope with a reduction or scan gets
  `contract`, never `reassoc`; without one, `fast` when the inputs are declared finite, else `noerrno`. A failed
  verification falls back one level (`fast` to `noerrno`, `noerrno` to `contract`).
- `-ffast-math` stays on the scope's compile, never on the link line: gcc then links `crtfastmath.o`, which sets
  FTZ/DAZ for the whole process, `strict` scopes included.
- Compiler: the one that vectorized the most distinct source loops (`file:line` from the remarks; gcc's epilogue and
  versioned loops count once), ties broken by the widest vectors in bytes (clang `vectorization width` x element
  size, gcc `using N byte vectors`).
- Order: FP level, then compiler, then knobs. A failed verification lowers the FP level and keeps the compiler.
- Rendering and knobs: chosen from build signals (vectorized loops from remarks, packed vector instruction share,
  spills, `llvm-mca` throughput; GPU: occupancy from register and shared memory use). Evaluated as regret against
  the timed winner.

## ISA lookup: the agent's math ISA

Status: built (`alloy/isa/`). DaCe's auto-vectorization hands an agent intrinsic-level code (today the explicit
SVE loops of `tails.sve_intrinsics`, DaCe's `SVEVectorization` rendered by CPF; compiler-vectorized builds carry
the same math as vector instructions in their objects). To keep optimizing from there the agent reasons in a
machine abstract math ISA — `load, store, broadcast, +, -, *, /, fma, lanewise reduction (vector to scalar),
gen_mask, zero` — and looks up the spelling per target, instead of reading ISA manuals.

- `alloy/isa/ops.py` holds the abstract op set (the vocabulary); `alloy/isa/intrinsics.toml` spells every op per
  ISA (avx2, avx512, neon, sve; `avx512_256` resolves to avx512 as a width knob) and dtype (f64, f32): the C
  intrinsic, the assembly mnemonic, the signature, the lane semantics, the masked variant where the ISA has one,
  and a recipe where no single intrinsic exists (AVX2/NEON lane reductions). Operand-order traps (NEON/SVE fma
  take the accumulator first, Intel last) are recorded in the table so no caller hardcodes an order.
- Both directions: `lookup(isa, op, dtype)` for writing vector code; `reverse(name)` maps an intrinsic or a
  disassembler mnemonic (including `vfmadd231pd`-style family forms and EVEX dot suffixes) back to the math —
  the same mnemonics `predict.py` scores. CLI: `python -m alloy.isa lookup|reverse|ops|isas|schedule`.
- Transcendentals (`exp`, `sin`, `cos`) have no native instruction on the covered ISAs. Each entry lists
  polynomial tiers from the shared `[approx]` section — Horner recipes in abstract-op steps with ULP error
  measured against libm (Taylor ladders plus Chebyshev near-minimax on the reduced domain; ULP at function
  scale, floored at `ulp(1.0)`) — and the vector math library call per veclib. The libmvec names are
  verified against the host's `libmvec.so` (`nm -D`, glibc 2.43), SLEEF names per sleef.org; both reverse
  to the op. Accuracy insight encoded in the tiers: range reduction dominates (hi/lo π/2 and ln2
  constants), plain Taylor cannot reach low ULP at any practical degree, and sub-1-ulp exp needs a
  2^(j/64) table — which is exactly SVE's `svexpa` instruction (ACLE SVE 6.16.30); AVX-512 assists with
  `vreducepd` (argument reduction) and `vscalefpd` (2^k scaling).
- The arithmetic core extends to `sqrt, min, max, abs, neg, select (blend), gather, scatter, mod` on
  f64/f32; `and, or, shl, shr, land, lor` and integer `mod` live under the new i64/i32 dtypes; f16 is
  optional per ISA (native AVX-512 FP16 / NEON Armv8.2 / SVE). Where hardware lacks an op the entry is a
  recipe over the intrinsics that provide it — x86 FP abs/neg are sign-mask AND/XOR, scatter before
  AVX-512 is a scratch store plus scalar stores, NEON gathers lane-wise, integer mod divides scalar per
  lane, and AVX2 f16 arithmetic converts through f32 (bitwise f16 ops work directly on the storage).
  Recipes are the table's fallback story: an agent never needs a manual to know what to substitute.
  A scalar operand of a binary op is broadcast (free as an EVEX embedded broadcast on AVX-512, an
  explicit `set1`/`vdup`/`svdup` elsewhere).
- Tenstorrent Tensix is deliberately absent: no C intrinsic path (design decision 2026-10-26, recorded
  `unsupported`); lane reduction has no direct analogue there anyway.
- The schedule axis: `[schedules]` metadata (five loop shapes from scalar to explicit predicated SVE),
  legality per ISA with reasons, compile-and-run-verified C skeletons composed from the table entries
  (`alloy/isa/schedules.py` — the seed of the schedule->vector-schedule translator), and the
  compiler-vectorizer spellings (gcc's `vect-partial-vector-usage` ladder, clang's pragmas; clang has no
  masked epilogue, and the table says so instead of inventing a flag).
- Nothing is returned unverified: `validate.py` compiles and runs a small kernel for every
  host-executable entry (fallback recipes are hand-coded, not auto-translated) and re-measures every
  polynomial tier against libm; a failure attaches the candidate spellings instead of endorsing a wrong
  answer. When emission is impossible, `hints.py` answers with a text reason, a do-it-yourself
  instruction, and per-tasklet hints (classified tasklets mapped to their spellings and verdicts).
- Every spelling is verified against the clang resource headers in CI (`tests/test_isa*.py`, 282 tests);
  the table is checked-in data, regenerated per clang version when ops are added, not parsed from ISA
  PDFs. The agent-facing rule (encoded in `skills/alloy/`): candidates report first, generated pages,
  this lookup for spelling and schedules, per-target ESSENTIALS sheets for context, itemized PDFs
  last, never end-to-end.

## Bench experiments: dace+alloy

- Alloy is an HPCAgent-Bench flavor plugin (`alloy/hb_plugin`, entry point `hpcagent_bench.plugins`). Its flavor
  `alloy_profile` extends the DaCe stage columns into `dace_<cpu|gpu>_<canon|parallel|autoopt>_alloy_profile`: the
  stage's pipeline output is Alloy's input SDFG. A speculative flavor (no judge timing) is planned, not registered.
- Scope coverage over 259 LLR kernels (10-12): `parallel_cpu` 257 outline, `canon_cpu` 215. canon misses 28 that
  keep a library node with its `CPU` (C++) expansion (Reduce 9, ScatterConflictCheck 7, Scan 4, ArgReduce 3, none 5)
  and 15 whose scope needs `__dace_num_threads` (ExternalCall cannot type it); `inc` fails both. These record
  `unsupported`.
- 10-13: both fixed in DaCe extended. Scopes never take a reserved `__dace*` symbol as an argument (e086e38); a
  library node whose implementation a pipeline chose stays whole as its own scope, rendered with that implementation
  (`outline_to_external_calls(library_nodes=True)`, 83a95d2), while an unchosen one still expands into a nest Alloy
  generates. Its accumulation length: input elements per output element (reduce), the whole input (scan).
- 10-13 coverage re-run (dace 8fd302b): `parallel_cpu` 258/259, `canon_cpu` 252/259; the rest have no nest or
  library node left. CPF renders Reduce as an OpenMP `reduction` (canon argmax 515 ms -> 0.73 ms per call at 6M,
  Alloy's argmax run 594 s -> 97 s), never emits `omp critical`, and argmax / argmin reduce through the declared
  `arg_max_pair` / `arg_min_pair` reductions of `dace/arg_reduction.h`.
- Budget: verify every candidate locally, screen them locally at small sizes on few threads, many runners and
  compilers in parallel; start from each scope's local winner. Since 10-19 the judge ranks the top 5 per scope as
  `/profile` stubs (`Linker.stub`: the kernel's signature, the scopes before at their best, nothing after), then
  scores the selection once with `/score`. Measured on argmax_value (16 cores): Alloy 23 s (candidates compile one per core), one judge `/score`
  200-240 s, the harness grade 144 s (noop). So L2 (300 s) submits the local winner unscored (judge: correct, 1.74x
  vs auto) and only L3 (600 s) scores; at L1 (180 s) Alloy plus the harness grade still times out on this box.
- Submission: CPF renders the outlined program in the bench C ABI (the bench's `cpf_bridge` preparation and
  `EntrySignature`), the scope archives come from `Rendering.link` (DaCe extended 844ebca; the bench must pin it).
  No DaCe build, no libdace.
- OpenMP: the library links LLVM libomp, which exports `GOMP_*` and `__kmpc_*`, so gcc, clang, icx and nvc objects
  share it. Measured: `clang-21 -fopenmp=libgomp` emits no OpenMP calls (the pragmas are dropped), so libgomp would
  leave gcc as the only parallel compiler. Probe the judge process once for a second runtime.

## Report format

Status: built (profile mode). `report.json` is the record (`alloy/report.py`, schema 4, pydantic, refused on an
unknown key, a wrong type or another schema); `report.md` is rendered from it and nothing else.

0. The vectorization options: every ISA x loop tail, with the compilers that build it on this host or why none can.

1. The outlined program's control-flow tree (`alloy/frontend/tree.py`, NestForge's row format without work and
   depth, duplicated on purpose); each scope is a row named by its entry symbol.
2. Per scope: signature, traits (libm, reduction, accumulation length), its own tree, how many candidates were built
   and why the rest dropped out (build failed, duplicate object, failed verification, not screened), the cells
   pruned before building with their reasons, its baseline,
   and its top-k correct variants (k = 5 by default), ranked by screened time, re-timed time where taken.
3. Verdict: scope x build config (every compiler), each cell the config's fastest correct variant as
   `ms (speedup)` or why it has none; the chosen candidate per scope; the full compile and link argv that
   `best/Makefile` runs; the whole program against DaCe's default build.

Baseline: per scope, the matrix-default candidate (DaCe's compiler, default knobs, strict FP, `-march=native`); for
the program, DaCe's own default build. Every speedup is over one compiler with one flag set.

Modes (`api.generate(..., mode=)`):
- `profile`: verified and timed; variants ranked by time.
- `speculative` (`alloy/heuristics/predict.py`): verified, untimed; each build gets a roofline cost per element.
  - Loops: the object's innermost loops (backward branches), grouped into source loops by the tasklets their line
    tables render (every compiler emits line tables, `[compilers.*] line_tables`; no code change, stripped before
    objects are compared). A main loop and its epilogues are one group; its hot copy handles the most elements per
    iteration. A loop rendering no statement (OpenMP chunking) only counts when none does.
  - Compute: llvm-mca on the host CPU (loop-carried chains included) over elements per iteration (bytes the loop's
    non-stack memory operations move / (element bytes x distinct accesses)), plus a fixed cost per hot call
    (vector math in a vector loop, every call in a scalar one); weighted by each source loop's iterations at the
    preset sizes over the scope's largest map's, spread over the physical cores.
  - Memory: the source loops' bytes per element over main-memory bandwidth (cycles at the maximum clock), once the
    scope's arrays fill more than half the largest cache. Bandwidth (`machine.memory_bandwidth`): the installed
    modules' peak from a saved `dmidecode -t 17` (`$ALLOY_MEMORY_DEVICES`, default
    `$XDG_CACHE_HOME/alloy/dmidecode-17.txt`; `sudo dmidecode -t 17 > that` once), else `dmidecode` run directly,
    else a measured parallel copy.
  - Pick: the correct build with the lowest cost; builds within 2% tie and go to the default FP level
    (`heuristics/fp.py`), then sweep order. The verdict matrix shows `cycles/elem`; `best/` links the picks.
  - Fission (`heuristics/fission.py`): one more one-factor candidate per compiler when a flat top-level map keeps
    more values live than the host's vector registers (16 on x86-64, 32 with AVX-512 and on aarch64). Work/depth:
    a code node's level is 1 + its deepest producer's; the body is cut after the level that leaves the least
    pressure in either piece, then the fewest crossing values, then the most even work. Boundaries are states: a
    cut is a set of top-level states of the map's nested body, `before | set | after`, up to three maps (states
    between two chosen ones join the set), applied with DaCe's `SubgraphFission` at the boundaries, then `simplify`.
    NestForge's `expand` view is that nested body already. A flat body is staged first: the heuristic picks a node
    set (nodes between two chosen ones join it), the body is nested and `state_fission` makes `before | set | after`
    states; a value read in its own piece and a later one crosses through a copy, so each piece inlines back to a
    flat map. Verified at its FP level's tolerance; predicted on the split SDFG, the widened values added to the
    footprint and to each loop's bytes. The default heuristic cuts flat bodies only.
    - TODO (feedback phase): cut where a build's loop spills, and where the vectorizer misses a loop (scope too).
    - TODO: maps nested in maps.
  - Regret against profile mode is a paper metric. `scale` at 16 MiB (gcc + clang, 28 timed): the pick is the profile
    winner (regret 0); before the memory term it was the 27th of 28.

Every interesting win or loss also becomes an A/B folder in `samples/` (see `measurement.md`).
