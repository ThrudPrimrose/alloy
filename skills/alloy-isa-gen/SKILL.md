---
name: alloy-isa-gen
description: "Extending or regenerating Alloy's ISA lookup table (alloy/isa/): how to add an op, dtype, or ISA; the verification workflow against clang headers; measuring ULP for approximation tiers; keeping the generated skill pages in sync. Use when adding intrinsics to intrinsics.toml, adding a new vector op, or regenerating the alloy ISA reference pages."
when: "you extend alloy/isa/intrinsics.toml or alloy/isa/ops.py - add an op, an ISA, a dtype (f16, i64/i32), an approximation tier, or library spellings - or regenerate the skill pages under skills/alloy/isa/ from the table"
---

# Generating the Alloy ISA table

`alloy/isa/` is one source of truth (`intrinsics.toml`, validated by `table.py`) rendered into two
consumers: the lookup CLI (`python -m alloy.isa`, cheap tool calls) and the generated skill pages
(`skills/alloy/isa/*.md`, static context — never edit those by hand). This page is the maintainer's
workflow for changing the table.

## The pipeline

```
source facts (clang headers / ESSENTIALS / itemized PDFs)
        |  verify every spelling
        v
ops.py (abstract op)  +  intrinsics.toml (spelling, traps, recipes, tiers, schedules)
        |  table.py invariants + tests/test_isa*.py (header, kernels, tiers, schedules)
        v
consumers: the CLI · validate.py (numerical gate) · schedules.py (skeletons)
        · hints.py (do-it-yourself advice) · render.py -> skills/alloy/isa/*.md
```

## Adding an op (the workflow)

1. **Claim the abstract op in `ops.py`**: name, symbol, kind (`memory`/`elementwise`/`bitwise`/`shift`/
   `logical`/`reduction`/`mask`/`transcendental`/`constant`), arity, result, lane semantics. Kinds drive
   the invariants (bitwise/shift/logical are integer-only; transcendentals carry tiers, no intrinsic).
2. **Spell it per ISA and dtype in `intrinsics.toml`** under `[isa.<isa>.<dtype>.<op>]`. Sources, in
   priority order:
   - **clang resource headers are the spelling authority** — verify before committing:
     `grep -r "_mm512_foo_pd(" /usr/lib/clang/*/include/`. Get the dir from `clang -print-resource-dir`.
   - **ESSENTIALS sheets** (`~/Work/Plans/alloy-isa-abstractor-plan/isa-docs-trimmed/<isa>/ESSENTIALS.md`)
     for the machine model and naming grammar.
   - **itemized PDFs** (`python3 pdf_itemize.py find <key> <term>`; keys: avx2ch, avx512ch, avxenc, neon,
     acle, sveacle, wormhole, blackhole) — a needle query for the one fact the table lacks, never an
     end-to-end read.
3. **Record traps in `note`** (operand order, sign-bit vs boolean masks, argument order swaps) — the
   table is where traps live, so no caller hardcodes them.
   **Assists** (single intrinsics that help an op without being one — `vscalefpd`, `svexpa`,
   `vrecpeq`) go in `[[isa.<isa>.assists]]` rows (`name`, `mnemonic`, `helps`, `note`); they are
   reverse-lookup only (`python -m alloy.isa assist <name>`), never abstract ops.
4. **Hardware missing the op → write a `recipe`**, the fallback story: the smallest sequence of real
   intrinsics (or pseudo steps, when even those don't exist) that provides it. See the existing
   patterns: x86 FP abs/neg (sign-mask AND/XOR), AVX2 scatter (scratch store + scalar), fmod
   (div+trunc+fnmadd), AVX2 f16 (cvtph_ps → f32 op → cvtps_ph).
5. **Run the checks**: `pytest tests/test_isa*.py -q` (header verification of every identifier-shaped
   spelling; compiled-kernel validation of every x86 entry the host can execute (no NEON/SVE kernels exist yet); tier re-measurement;
   skeleton compile-and-run; round-trips; invariants) and `ruff check alloy/ tests/test_isa*.py`.
6. **Regenerate the pages**: `python -m alloy.isa.render`, then mirror the skills:
   `cp skills/alloy/SKILL.md ~/.kimi-code/skills/alloy/ && cp -r skills/alloy/isa ~/.kimi-code/skills/alloy/`.

## Adding a schedule

Schedules are `[schedules.<name>]` tables (title, description, tail strategy, gcc/clang spellings),
cross-referenced by every ISA's `schedules` list — `_checked` rejects an offer with no metadata. The
skeleton emitter (`schedules.py`) composes C loop shapes from the table entries, so a new schedule
needs: the metadata block, the legality lists on the ISAs that offer it, and an emitter branch.
Keep `legal()`'s reasons true: a refusal must say whether the blocker is predication or the offer
list. When the schedule has no compiler spelling (clang's missing masked epilogue is the precedent),
say so in the `clang` field — an honest refusal beats a wrong flag.

## Gotchas already paid for

- **The validation gate catches real bugs — run it.** It has caught: wrong final steps in generated
  polynomial recipes (the Taylor-form `s = fma(mul(x, t), p, x)` was emitted for Chebyshev tiers whose
  coefficients include c0 — they need `s = mul(x, p)` / `c = p` / `e = p`), and the libmvec calling
  convention: `_ZGVdN4v_sin` takes its vector **by value in a register** (`extern __m256d
  _ZGVdN4v_sin(__m256d);`), not via a memory pointer. The gate re-measures every tier against libm
  (recorded `error_ulp` must reproduce within 2x) and compiles every host-executable entry.
- **clang macro spellings**: some "intrinsics" are macros, not functions — `_mm512_castsi512_pd`,
  `_kand_mask16` (alias of `_mm512_kand`). The header test greps `name\s*(`, so keep macros out of
  `recipe` lists (use them in `note` text). FP16 fma is `_mm512_fmadd_ph`, not `_mm512_fma_ph`;
  the 64-bit broadcast is `_mm256_set1_epi64x` (with an x).
- **A kernel must run the table's own spelling.** `validate._body` builds calls from `entry.intrinsic` and
  `entry.recipe`; `unexercised` turns a kernel that skips one into "unverified". Hardcoding the name back
  makes the gate pass on any mapping. `tests/test_isa_validate.py` swaps in wrong spellings to prove this.
- **Compare with the lane's own type and watch NaN.** An f32 lane is checked against `sqrtf`/`fmaf`, not the
  double libm; kernels use non-dyadic inputs and negative lanes, and `TRACK_ERROR` keeps a NaN (a plain
  `>` drops it). A kernel with a constant reference proves nothing.
- **Function definitions may have a space before the paren** (`_mm256_set1_epi64x (`) — the test's
  regex tolerates it; your grep should too (`\bname\b`).
- **Operand-order traps** (fma accumulator first on NEON/SVE, last on Intel; select/blend's three
  surfaces; AVX-512 gather `(idx, base)` vs AVX2 `(base, idx)`) go in `signature`/`semantics`/`note`.
- **Flag needs travel with spellings**: the AVX-512 k-mask intrinsics (`_kand_mask8`) need
  `-mavx512dq`, not just `-mavx512f`; f32 gathers/scatters index in 32-bit lanes — a 64-bit index
  vector reads every other dword; clang has no masked-epilogue form, so `masked_remainder`'s clang
  spelling is an honest refusal, not a flag.
- **Dtypes**: float ops live under `f64`/`f32` (required, full coverage), `f16` optional (arithmetic
  subset), integer ops under `i64`/`i32`. `_checked` enforces this — read its errors as the spec.
- **Transcendentals**: no `intrinsic`/`recipe` on the entry; tiers are `[approx.<name>]` tables with
  `op`, `domain`, `error_ulp`, `error_abs`, `recipe` (Horner in abstract-op steps), referenced by name
  from each entry's `approximations`. Library calls go in `libraries` (verified: libmvec by `nm -D` on
  the host; SLEEF/SVML per their references).

## Math kernels

`mathkernels.toml` is generated by `python -m alloy.isa.mathfit` (needs mpmath); never edit it. A program lives in
`mathfit.py` once per family, in the primitives of `mathprims.toml`, and renders for every ISA. To add a function:
write `program_<fn>`, add its degrees to `DEGREES` and an entry to `PROGRAMS`, rerun the fit, then `render`.

- The fit overwrites the recorded errors from a run on this host (worst of AVX2 and AVX-512), so a change that
  worsens accuracy shows in the diff. Read that diff.
- `strict` has a guard mask or none; a guard costs one cold branch that recomputes those lanes through scalar libm.
  Use it for anything the vector path cannot do, instead of more vector code.
- A new primitive needs a spelling in all four `[prims.*]` tables. NEON and SVE only cross-compile here.
- Compensated steps do not survive reassociation and no per-function attribute survives inlining, so a `strict`
  kernel is a compile error under `-ffast-math`. `tests/test_isa_kernels.py` pins that and bounds `relaxed` there.

## Measuring ULP for a new tier

Dense-grid against libm; ULP at function scale, floored at `ulp(1.0)` so function zeros stay finite
(`err / spacing(max(|ref|, 1))`). The methodology comment sits above `[approx]` in `intrinsics.toml`;
the measurement script pattern is in git history's session notes — replicate, don't quote folklore.
Taylor tiers use exact coefficients; near-minimax tiers are Chebyshev fits converted to power basis
(shortest-round-trip float reprs in the recipe steps). Record `error_abs` next to `error_ulp`; a test
asserts the ladder is monotonic.

## Adding an ISA or a dtype

- **ISA**: one `[isa.<name>]` block (title, vector_bytes 0 = length-agnostic, lanes per dtype, mask
  capability, legal schedules, gen_mask spelling), then op tables; `avx512_256`-style width knobs are
  `ALIASES` entries in `table.py`, not new ISAs. Extend `test_the_matrix_and_the_table_agree_on_isa_widths`
  if the matrix learns the ISA.
- **dtype**: extend `ALL_DTYPES`/`REQUIRED_DTYPES` in `table.py`, give every ISA its `lanes` count, and
  expect `_checked` to tell you which op tables are now incomplete. Keep `gen_mask`/`transcendental`
  rules per dtype in `entry_ok`.
