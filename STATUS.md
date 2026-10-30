# Status — Alloy ISA layer (agent-facing math ISA + lookup table)

Update this file at every snapshot: bump the snapshot counter, date it, and move items between
**Implemented** and **Open tasks**. Keep claims verifiable: a feature counts as implemented only when
its tests pass (`pytest tests/test_isa.py -q`) and every new spelling is verified against the clang
resource headers (the test `test_every_spelling_exists_in_the_clang_headers` does this on hosts that
have them; CI installs clang).

## What this is

`alloy/isa/` is the bridge between DaCe's auto-vectorized intrinsic code (today: `tails.sve_intrinsics`
rendering explicit SVE loops, plus vectorized builds whose objects carry the same math as machine
instructions) and the math an agent reasons in. An agent phrases its plan in the machine abstract math
ISA and looks up the spelling per target; it never reads ISA manuals. Design context: `docs/design.md`
("ISA lookup: the agent's math ISA") and `~/Work/Plans/alloy-isa-abstractor-plan/` (work item 2 of
PLAN.md; the vector-schedule translator, work item 3, is still open below).

## Folder structure

```
alloy/isa/
  ops.py            the abstract math ISA: op name -> math, kind, arity, result (no spellings)
  table.py          schema (Entry/Approx/Isa), loader, invariants, forward + reverse indexes
  intrinsics.toml   the checked-in data: op x dtype x ISA -> intrinsic/mnemonic/recipe, [approx] tiers
  __main__.py       the CLI: python -m alloy.isa lookup|reverse|ops|isas|schedule
  __init__.py       public API: OPS, lookup, reverse, isas, load
skills/alloy/SKILL.md   the agent skill (mirrored to ~/.kimi-code/skills/alloy/)
tests/test_isa.py       one test file per module, matching the repo convention
```

Conventions the structure encodes: spellings live in TOML (data, regenerated per clang version), never
in Python; operand-order traps live in `signature`/`semantics`/`note` fields so no caller hardcodes an
order; anything hardware lacks is a `recipe` over the intrinsics that provide it (the fallback story).

## Snapshots

### Snapshot 12 — 2026-10-30 (latent-bug sweep)

Full-review fixes, all with regression tests (289 total): masked-variant reverse names with trailing
spaces lost (the f16 masked loads/stores carried cast notes); `_flags()` now parses aarch64
`Features:` so host_can_run works on ARM; honest message for entries without a compiled validator;
f32 mod/reduce_add tolerances got real single-precision slack (the old values passed by luck of the
fixed inputs); `hints._uses` checks the whole memlet tree for the summing write-conflict (real DaCe
reductions park the WCR on the map exit's edge).

### Snapshot 11 — 2026-10-30 (review round 2: assists, one namespace, skill polish)

- The ISA survey's hardware assists are now queryable table data: 22 `[[isa.*.assists]]` rows
  (AVX-512 scalef/getexp/getmant/reduce/fixupimm/range/rcp14/rsqrt14/fpclass; SVE expa/scale/logb/
  recpe/rsqrte/recps; NEON recpe/rsqrte/recps/ld2; AVX2 rcp/rsqrt/dp), each with mnemonic, the op it
  helps, and a note. Reverse-lookup only: `python -m alloy.isa assist <name>`; listed on the per-ISA
  pages. AVX512ER (Phi-only vexp2pd/rcp28) deliberately absent.
- `alloy.isa` is now one namespace: `validate`, `skeleton`, `advice`, `tasklet_hints`,
  `compiler_spelling`, `legal` all import from the package (every module stays dace-free at import).
- Skills polished: the `assist` command documented in the agent skill; the maintainer skill gains the
  assists workflow. 287 tests.

### Snapshot 10 — 2026-10-30 (skeleton self-verification)

- `schedules.verify(isa, schedule, dtype)` compiles and runs a skeleton against the scalar reference
  — the same numerical gate as table entries, applied to composed loop shapes; `skeleton --verify`
  exposes it. Closes the review's gap 2 (skeletons now self-validate at emission time, not only in
  tests). 284 tests.
- Review round (snapshot 9): both skills and the docs brought current with the code; review gap 1
  (nothing calls `advice()` yet — the emission paths must adopt the failure body) stays open.
- Full-suite stall root-caused: a fork-server child hangs (pytest idle waiting on a
  `multiprocessing.fork` pid) in the test_report/test_timing region; faulthandler-armed tail rerun in
  flight to name the exact test.

### Snapshot 9 — 2026-10-30 (full review: skills and docs brought current)

- `skills/alloy`: frontmatter now names the whole op set, schedules, and the validation gate (was the
  snapshot-1 list); added the Loop schedules section (five shapes, compiler spellings, skeletons) and
  the "when the answer is no" section describing the do-it-yourself failure body; the dtypes line now
  covers f16/i64/i32.
- `skills/alloy-isa-gen`: the pipeline diagram lists every consumer (CLI, validate, schedules, hints,
  render); new "Adding a schedule" section; new gotchas (-mavx512dq for k-mask intrinsics, 32-bit
  gather index lanes, clang's missing masked epilogue as the honest-refusal precedent); the check
  command covers all four test files.
- README, design.md, STATUS: stale CLI lists and test counts fixed; design.md records the schedule
  axis, the validation gate, and the hints response.

### Snapshot 8 — 2026-10-30 (the compiler-vectorizer route of the schedule axis)

- Every schedule now spells how to ask gcc and clang for it (data in `[schedules]`, from
  design.md): scalar `-fno-tree-vectorize` / `vectorize(disable)`; scalar_remainder gcc
  `--param vect-partial-vector-usage=0`, clang `#pragma clang loop vectorize_width(VL)
  interleave_count(k)`; masked_remainder gcc `=1` (masked epilogue), clang honestly "no masked
  epilogue: use full_mask or scalar_remainder"; full_mask gcc `=2`, clang
  `-prefer-predicate-over-epilogue`; sve_intrinsics `-march=armv8-a+sve` (+ `-mllvm
  -scalable-vectorization=on` for clang) or this skeleton. API `compiler_spelling(schedule,
  compiler)`; `schedule <isa>` and the per-ISA pages show them. 26 schedule tests (282 total).

### Snapshot 7 — 2026-10-30 (the schedule axis)

- Schedules are first-class: `[schedules]` metadata in the table (title, description, tail strategy),
  `scalar` offered everywhere, and `legal(isa, schedule)` answers with a reason ("avx2 has no
  predication", "not offered on sve (legal there: ...)"). `Table` carries `schedule_info`;
  `_checked` cross-references ISA offers against the metadata.
- `alloy/isa/schedules.py`: `skeleton(isa, schedule, dtype)` emits the canonical axpy C source for
  every legal combination, composed from the table's own entries (loads, stores, broadcast, fma,
  gen_mask) so operand-order traps (NEON/SVE accumulator-first fma) are respected by construction.
  Shapes: scalar, scalar_remainder (maskless remainder loop), masked_remainder and full_mask
  (AVX-512 opmask, iota + cmplt gen_mask), sve_intrinsics (svwhilelt predicate named __pg_i per the
  contract, svcntd/svcntw step). This is the seed of the schedule->vector-schedule translator.
  Every skeleton the host can execute is compile-and-run verified in tests (24 new; 280 total).
- CLI: `schedule <isa>` prints per-schedule legality with reasons; `skeleton <isa> <schedule>
  <dtype>` prints the C source.

### Snapshot 6 — 2026-10-30 (do-it-yourself advice)

- `alloy/isa/hints.py`: the response body for the emission path when it cannot emit or validation
  fails — a text reason, a do-it-yourself instruction, and hints computed from the scope's own Python
  tasklets: every tasklet is collected (ast walk over its code), classified (elementwise / reduction
  via summing write-conflict / libm), and mapped to the relevant intrinsics for the requested
  (isa, dtype) — spelling, signature, trap, and the host's validation verdict. Contractable
  mul+add/sub pairs surface `fma` too; transcendentals name the best tier (with its ULP) and the
  library call. Integer ops under float dtypes are absent rather than errors.
- 256 tests across the three ISA test files (hints: 5 new); ruff clean.

### Snapshot 5 — 2026-10-30 (numerical validation gate)

- `alloy/isa/validate.py`: every spelling is checked before an agent sees it. Host-executable entries
  (AVX2/FMA, AVX-512F on this box; NEON/SVE on aarch64) run a small compiled C kernel — fixed inputs
  through the looked-up intrinsic or its hand-coded fallback recipe, scalar reference, per-op tolerance.
  Transcendental tiers are re-measured against libm (recorded `error_ulp` must reproduce within 2x).
  On failure `candidates_for` attaches the potentially relevant spellings (same op other dtype/ISA,
  reverse-lookup family); the CLI's `lookup` verifies by default (exit 3 + candidate list on failure),
  `validate [isa op dtype]` runs the gate wholesale.
- The gate caught real bugs on its first run: the Chebyshev tiers' recipes had the Taylor-form final
  step (`s = fma(mul(x, t), p, x)` instead of `s = mul(x, p)` etc.) — fixed in `intrinsics.toml`, all
  16 tiers now re-measure exactly. And the libmvec ABI is by-value register
  (`extern __m256d _ZGVcN4v_sin(__m256d)`, not a memory pointer) — the library kernels use it.
- 251 tests across `tests/test_isa.py` (187) and `tests/test_isa_validate.py` (64); ruff clean.
- Review pass: removed a dead parameter in `table.py`'s invariant checker.
- Full-suite diagnosis: the 4 consistent failures are `test_hb_plugin.py` judge-submission tests (need a
  live HPCAgent-Bench judge); the mid-run "crashes" coincided with editing sessions touching files the
  suite imports. A clean-tree rerun is the arbiter.

### Snapshot 4 — 2026-10-30 (generated skill pages + generator skill)

- `alloy/isa/render.py`: renders the table into skill pages (`python -m alloy.isa.render`) —
  `skills/alloy/isa/{index,avx2,avx512,neon,sve,transcendentals}.md`. The TOML is the single source of
  truth; the pages are generated context (never hand-edited), so an agent reads mappings in-context
  without tool calls. Traps sections render from `note` fields mentioning a trap.
- `skills/alloy-isa-gen/SKILL.md`: the maintainer skill — the add-an-op workflow (abstract op →
  header-verified spelling → traps → fallback recipe → tests → re-render → mirror), the clang macro
  gotchas, the ULP measurement protocol, how to add an ISA or dtype.
- Main `alloy` skill's reference-priority rule updated: generated pages first, CLI second.
- 187 tests (added the render test); ruff clean. Both skills mirrored to `~/.kimi-code/skills/`.

### Snapshot 3 — 2026-10-29 (op expansion: arithmetic core, integers, f16)

- New abstract ops: `sqrt, min, max, abs, neg, select` (float), `gather, scatter`, `mod` (fmod on
  floats, truncated remainder on ints), `and, or, shl, shr, land, lor` (integer lanes).
- New dtypes: `i64/i32` (integer ops; AVX-512/SVE `land`/`lor` give mask/predicate forms) and `f16`
  (optional arithmetic subset; AVX2 emulates through f32 with cvtph/cvtps recipes — bitwise f16 ops
  work directly on the storage).
- Fallback recipes where hardware lacks the op: x86 FP abs/neg (sign-mask AND/XOR), AVX2 scatter
  (scratch store + scalar), NEON gather/scatter (per-lane lane loads/stores), fmod (div+trunc+fnmadd;
  SVE converts via svcvt — no FRINT in clang's SVE header), integer mod (scalar division).
- Scalar operand of a binary op is broadcast: `embedded_broadcast = true` on AVX-512 (EVEX `{1to8}`),
  explicit set1/vdup/svdup elsewhere (ISA notes).
- Traps encoded: select/blend's three surfaces (AVX2 mask-last sign-bit; AVX-512/NEON/SVE mask-first),
  AVX-512 gather `(idx, base)` vs AVX2 `(base, idx)`, NEON `vshlq` right-shifts on negative counts,
  clang 22 macro gotchas (`_kand_mask16` → `_mm512_kand`; 512 casts are macros, kept out of recipes).
- 186 tests in `tests/test_isa.py`, all passing; ruff clean. Skill/README/design.md updated.

### Snapshot 2 — 2026-10-29 (transcendentals)

- `exp, sin, cos` as abstract ops; per ISA/dtype entries with polynomial tiers from the shared
  `[approx]` section (Horner recipes in abstract-op steps, Taylor + Chebyshev near-minimax) and ULP
  errors measured against libm on dense grids (ULP at function scale, floored at `ulp(1.0)`).
  sin-quad-cheb13 = 8.5 ulp, cos-quad-cheb12 = 16 ulp, exp-cheb11 = 67 ulp; Taylor ladder shows why
  libraries use minimax + range reduction.
- Vector math library spellings per veclib, reverse-indexed: libmvec names verified against the host's
  `libmvec.so` (nm, glibc 2.43), SVML/SLEEF names per sleef.org. `reverse _ZGVcN4v_sin` → sin.
- Schema: `Entry.approximations` + `Entry.libraries`; invariants (transcendentals carry no intrinsic;
  tier keys must exist and match the op).

### Snapshot 1 — 2026-10-29 (lookup table v1)

- `alloy/isa/`: abstract ISA (load, store, broadcast, +, -, *, /, fma, lanewise reduce_add, gen_mask,
  zero) spelled per ISA (avx2, avx512, neon, sve; avx512_256 alias) and dtype (f64/f32): intrinsic,
  mnemonic, signature, semantics, masked variants, reduction recipes.
- Both directions: `lookup(isa, op, dtype)` and `reverse(name)` (intrinsics, mnemonics, `vfmadd231pd`
  family forms, EVEX `.z` suffixes).
- 40 tests; every spelling verified against clang 22 resource headers.

## Open tasks

0. **Full-suite MPI hang — FIXED 2026-10-30**: every `@dace.program` parse calls DaCe's
   `mpi4py_is_usable`, which runs `from mpi4py import MPI` — that dlopens libmpi and MPI_Inits a
   *singleton* job, whose bring-up stalls on a box without an MPI launcher (nondeterministic import
   race; killed three full-suite runs at different points). Fix in `tests/conftest.py`: no alloy test
   uses MPI, so the import is blocked (`sys.modules.setdefault("mpi4py", None)`) and the probe
   answers False. Worth an upstream DaCe report (the probe could avoid MPI_Init).
1. **Vector-schedule translator** (`alloy/vector/`, plan work item 3): schedule → vector schedule
   (clang/gcc vectorizer pragmas, SVE explicit loops), remark/asm verification, tail shapes =
   DaCe RemainderStrategy names. Makes the polynomial tiers and recipes emittable, not just readable.
2. **Report integration**: per-scope `VectorOption` rows (REPORT_DESIGN.md schema) naming which ISA/tail
   cells the host offers and why; wire `alloy.isa` lookups into `report.md` so an agent jumps from a
   variant's intrinsics to the abstract ops without a manual lookup.
3. **Full-suite diagnosis**: `pytest -m "not icx"` dies mid-run on this box (both runs crashed around
   the same tests before the ISA layer existed in the tree; F-marks at consistent positions). The
   ISA tests themselves are green (186/186). Diagnose with the file-captured run, fix or mark.
4. **Heuristic consumption**: `prune.py`/`predict.py` read the table (lanes, BITES, vector_bytes) via
   `alloy.isa` instead of duplicating ISA knowledge; cost model picks up the `mnemonic` column.
5. **Bench skill registration**: ship `skills/alloy/` as an HPCAgent-Bench external packet
   (`skills.external`) when the next study stages it.
6. **More ops when kernels ask** (candidates from the PDF survey): rcp/rsqrt estimates
   (vrcp14/vrsqrt14, recpe/rsqrte + Newton), `tbl`/in-register permutes (SVE `svtbl` — the EXPA-free
   table route), NEON `vld2/3/4` structure loads, `cvt` family, f16 gen_mask (epi16 iota).
7. **Latency/throughput columns**: llvm-mca per CPU on the hot mnemonics (plan's generator step);
   table hooks (mnemonics) are in place.
8. **Commit + CI**: nothing is committed yet; commit the ISA layer, add clang to CI so the header
   verification test runs there.

## Verification quick reference

```bash
cd alloy && uv sync --extra dev
pytest tests/test_isa*.py -q       # the ISA layer (282 tests: table, validation, hints, schedules)
ruff check alloy/ tests/test_isa.py
python -m alloy.isa lookup sve fma f64
python -m alloy.isa reverse vfmadd231pd
```
