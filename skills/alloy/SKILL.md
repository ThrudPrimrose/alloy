---
name: alloy
description: "Alloy: DaCe's per-scope codegen backend, the machine abstract math ISA (+ - * / %, fma, sqrt, min/max/abs/neg, select, gather/scatter, lanewise reduction, integer bitwise/shift/logical, exp/sin/cos) for avx2/avx512/neon/sve, loop schedules with verified C skeletons, and a numerical validation gate. Use when optimizing a kernel Alloy/DaCe vectorized, when reading vector intrinsic code or SIMD disassembly, when choosing a vector loop schedule, or when you need a spelling, an operand order, or the math an instruction computes."
when: "you work on an HPCAgent-Bench kernel through Alloy or DaCe's extended backend, or you face vector intrinsic code / vectorized loops (source or disassembly) on x86 or AArch64 and need the spelling, the operand order, the loop schedule, or the math an instruction computes — or Alloy answers a request with a failure body and you must do it yourself"
---

# Alloy + the machine abstract math ISA

Alloy splits a DaCe program into scopes, builds each under many configurations (compiler, FP level, ISA
width, loop tails), verifies and times them, and links the best. DaCe's auto-vectorization is the base
layer: `compiler.build_plugin = alloy-speculative` runs Alloy as DaCe's CPU backend, and the `sve_intrinsics` tail renders
scopes as explicit predicated SVE loops (DaCe `SVEVectorization`, CPF-rendered) — real intrinsics in the
generated C, not just compiler hints. An agent continues optimizing from that intrinsic-level code.

You do not need to know the intrinsics. Reason in the abstract math ISA; look up the spelling.

## The abstract math ISA

| op | math | kind |
|---|---|---|
| `load` | `v[j] = p[j]` | memory |
| `store` | `p[j] = v[j]` | memory |
| `broadcast` | `v[j] = s` (scalar s) | elementwise |
| `add` / `sub` / `mul` / `div` | `v[j] = a[j] ± b[j]` etc. | elementwise |
| `fma` | `v[j] = a[j]*b[j] + c[j]`, one rounding | elementwise |
| `reduce_add` | `s = Σ lanes of v` — full vector width to one scalar | reduction |
| `gen_mask` | lane j active iff `i + j < N` (the tail predicate) | mask |
| `zero` | `v[j] = 0` | constant |
| `exp` / `sin` / `cos` | `v[j] = f(v[j])` — transcendentals: **no native instruction** on any covered ISA | transcendental |
| `sqrt` `min` `max` `abs` `neg` | `v[j] = f(a[j], b[j])` — native nearly everywhere; **x86 has no FP abs/neg** (sign-mask AND/XOR recipes) | elementwise |
| `select` | `v[j] = mask[j] ? t[j] : f[j]` — called *blend* on x86; operand order differs per ISA (see traps) | elementwise |
| `gather` / `scatter` | `v[j] = base[idx[j]]` / `base[idx[j]] = v[j]` — scatter needs AVX-512 or SVE; NEON and AVX2 get per-lane/scalar recipes | memory |
| `mod` | `a[j] - trunc(a[j]/b[j])*b[j]` on floats, fmod only for finite b and small `a/b`; truncated remainder on ints; no native vector form, recipes + libraries | elementwise |
| `and` `or` `shl` `shr` `land` `lor` | integer lanes, looked up under **i64/i32** (`land`/`lor` give all-ones/0 lanes or, on AVX-512/SVE, mask/predicate ops) | bitwise/shift/logical |

Dtypes are `f64`, `f32`, optional `f16` (AVX-512 FP16, NEON Armv8.2, SVE — **AVX2 emulates through
f32** with `cvtph_ps`/`cvtps_ph` recipes; bitwise f16 ops work directly on the storage), and `i64`/`i32`
for the integer ops. The integer dtypes hold only those ops: no integer add, mul, load or compare row exists,
and float rows are not valid for integer lanes. A binary op also accepts a scalar operand: it is broadcast, free
as an EVEX embedded broadcast on AVX-512 when it is the last source (`{1to8}`), an explicit `set1`/`vdup`/`svdup`
elsewhere (`embedded_broadcast = true` marks the ISAs that fuse).

## Transcendentals: polynomial tiers with measured ULP, or a library call

`exp`, `sin`, `cos` have no hardware instruction on avx2/avx512/neon/sve. Each entry lists:

- **tiers** — Horner recipes in abstract-op steps (`fma`/`mul` with inline coefficients) with their error
  measured against libm in units of 2^-52: plain Taylor rungs (bad: sin-taylor7 ≈ 7e11 on [-π/2, π/2]) and
  Chebyshev tiers on the reduced domain (sin-quad-cheb13 ≈ 8.5). `kernel` gives better polynomials.
- **libraries** — the vector math call per veclib (glibc libmvec `_ZGVdN4v_sin`, SVML `__svml_sin4`,
  SLEEF `Sleef_sind4_u10avx2`). `reverse` knows every name `kernel` prints, so `call __svml_sin4` or
  `_ZGVdN4v_sin` in disassembly maps back to `sin`.

Range reduction dominates accuracy: the tiers assume `x` already reduced (Cody-Waite / quadrant for
sin/cos; k·ln2 + r split for exp, then scale by 2^k). Without hi/lo constants the reduction error
exceeds the polynomial error beyond a few multiples of π. Native assists: AVX-512 `vreducepd` (strips
multiples of 2^-M; scale by 2/π first for sin/cos) and `vscalefpd` (2^k scaling); SVE `svexpa_f64` — a
hardware 2^(I/64) table taking the biased input `(k + 1023)*64 + j` (ACLE SVE 6.16.30) — plus `svscale`
and, on SVE2 only, `svlogb`.
Sub-1-ulp exp otherwise needs a 64-entry 2^(j/64) table (which is exactly what SVE's EXPA is).

**Assists are queryable too**: single intrinsics that help an op without being one — AVX-512
`vscalefpd`/`vgetexppd`/`vreducepd`/`vrcp14pd`, SVE `svexpa`/`fscale`/`frecpe`, NEON `vrecpeq`,
AVX2 `vrcpps`. `python -m alloy.isa assist svexpa_f64` (or the mnemonic) names what it helps and
how; the per-ISA pages list them.

## Lookup (cheap tool calls, no manuals)

```bash
python -m alloy.isa host                        # which ISA and dtype this machine runs: start here
python -m alloy.isa lookup <isa> <op> <dtype>   # op -> intrinsic, signature, semantics, traps (--json)
python -m alloy.isa kernel <isa> <fn> <dtype>   # sin, exp, log (ln), pow, ... -> C (--level strict|relaxed|fast)
python -m alloy.isa reverse <name>              # intrinsic or mnemonic -> the math it computes (--json)
python -m alloy.isa validate [isa op dtype]     # the numerical gate: everything the host can execute; takes minutes
python -m alloy.isa skeleton <isa> <schedule> <dtype>   # the C loop shape, compiled and checked on this host
python -m alloy.isa assist <name>               # hardware assists: _mm512_scalef_pd | svexpa_f64 | vrcpps
python -m alloy.isa ops | isas | schedule <isa>
```

A `lookup` of an intrinsic or recipe on an x86 row this host runs is **numerically checked before it is
returned**: a small compiled kernel runs the spelling against a scalar reference, and transcendental tiers are
re-measured against libm. The check covers the intrinsic in its signature's operand order, or the recipe's names,
not the masked form, mnemonic or note. The output ends in `verified:`; on failure nothing is printed to stdout, the exit code is 3, and stderr lists
potentially relevant spellings. `unverified:` marks what cannot run here (NEON and SVE rows, or a missing ISA or
compiler); `reverse`, `assist` and `schedule` answers are not checked at all.

- ISAs: `avx2`, `avx512`, `neon`, `sve`. `avx512_256` is a compiler width knob: `kernel` maps it to AVX2 and
  `lookup` refuses it, because explicit `_mm512_*` intrinsics stay 512-bit. Dtypes: `f64`/`f32` everywhere, `f16`
  where the hardware has it, `i64`/`i32` for the integer ops. Names may be upper case.
- `reverse` accepts C intrinsics (`_mm512_add_pd`), SVE `_m`/`_z` and AVX-512 `maskz`/`mask3` forms, recipe steps,
  library symbols, and disassembler mnemonics as printed (`vaddpd`, `vfmadd231pd`, `fmla`, `ld1d`, `vaddpd.z`).
  A mnemonic that is one step of a composite reads `may be one step of`, not an equality. Use it to read a
  build's disassembly back into math: `llvm-objdump -d <archive>` → mnemonics → `reverse` → the loop's dataflow.

## Loop schedules: pick the tail, get the skeleton

Five schedules, each legal only where the hardware allows (the `schedule <isa>` command says why not):

- `scalar` — no vectorization, the baseline. `-fno-tree-vectorize` / `#pragma clang loop vectorize(disable)`.
- `scalar_remainder` — vector main loop + scalar tail loop; the only shape on maskless AVX2/NEON.
  gcc `--param vect-partial-vector-usage=0 --param vect-epilogues-nomask=0`; clang `#pragma clang loop vectorize_width(VL) interleave_count(k)`.
- `masked_remainder` — unmasked main loop + masked epilogue (AVX-512 opmask, SVE predicate). gcc `=1`; clang has
  **no masked epilogue** — use `full_mask` on AVX-512 or `scalar_remainder` elsewhere.
- `full_mask` — every iteration predicated, no epilogue (AVX-512, SVE). gcc `=2`; clang
  `-mllvm -prefer-predicate-over-epilogue=predicate-dont-vectorize`.
- `sve_intrinsics` — explicit predicated SVE loops (`svwhilelt` every iteration, runtime `svcntd()`
  step, no remainder); what DaCe's `SVEVectorization` renders.

```bash
python -m alloy.isa schedule avx512      # per-schedule LEGAL/refused matrix with reasons; LEGAL is not "fast"
python -m alloy.isa skeleton avx2 scalar_remainder f64   # the canonical axpy C, ready to edit
```

`skeleton` composes the loop from the table's own entries, so operand-order traps hold by
construction; a skeleton this host can execute is compiled and run before it is returned, and its header names
the build flags. No rule picks among the legal schedules: time them. A reduction under a tail predicate needs
SVE `_m`, or `_mm512_mask3_fmadd_*` on AVX-512, to keep the accumulator's inactive lanes.
The vector body is the canonical `C[i] = a*X[i] + Y[i]` — swap the expression for your kernel's.

## When the answer is no: the do-it-yourself body

If Alloy cannot emit or validate what you asked for, the response is a failure body, not silence:

1. **Reason** — one line, what failed and why.
2. **Do it yourself** — hand-write the C with intrinsics (this skill's pages, `lookup`, `kernel`, `skeleton`).
3. **Hints from your tasklets** — every tasklet and library node in the scope, classified (elementwise /
   reduction / libm), mapped to the spellings for your ISA in the tasklet's own lane, each carrying its note and
   its `verified` / `unverified` / `FAILED` status, and naming what the table has no row for (`alloy/isa/hints.py: advice()`). A run puts this text
   in `report.md` under "Do it yourself" and in the tool answer's `advice`, per scope (`alloy/guidance.py`).

```bash
python -m alloy.isa lookup sve fma f64
#   sve/f64/fma: v[j] = add[j] + m1[j]*m2[j] for active lanes j   <- accumulator FIRST
#   intrinsic: svmla_f64_x(pg, add, m1, m2) -> v
python -m alloy.isa reverse vfmadd231pd
#   vfmadd231pd: dest = src2*src3 + dest    <- the digits say which registers multiply
```

## Traps the table encodes (never hardcode an operand order)

- **fma**: Intel `_mm256/_mm512_fmadd(a, b, c)` = `a*b + c` (products first); NEON `vfmaq(a, b, c)` and SVE
  `svmla_x(pg, add, m1, m2)` = `a + b*c` / `add + m1*m2` (accumulator first).
- **lane reduction**: one instruction on SVE (`svaddv`) and NEON f64 (`vaddvq_f64`), two on NEON f32 (`vaddvq_f32`),
  a header composite on AVX-512 (`_mm512_reduce_add_pd`), a shuffle-add recipe on AVX2. All of them pair lanes, so
  they differ from a scalar left fold: they need reassociation permission.
- **min/max**: x86 is not IEEE minNum: `min(NaN, x) = x`, `min(x, NaN) = NaN`, equal zeros return the second operand.
  NEON `vminq` and SVE `svmin` propagate NaN; `vminnmq` and `svminnm` are minNum.
- **select/blend**: three different surfaces. AVX2 `_mm256_blendv_pd(a, b, mask)` puts the mask LAST and
  tests its **sign bit**; AVX-512 `_mm512_mask_blend_pd(k, a, b)` puts it FIRST and it picks b; NEON
  `vbslq_f64(mask, t, f)` and SVE `svsel_f64(pg, t, f)` also put it first and pick t.
- **gather/scatter**: AVX-512 gathers take `(idx, base)` — AVX2 took `(base, idx)`. Scatter needs AVX-512
  or SVE (`svld1_gather_*`/`svst1_scatter_*`); on AVX2/NEON the table gives the fallback recipes
  (scratch store + scalar per-lane accesses). Same fallback idea everywhere hardware lacks an op:
  FP abs/neg are sign-mask AND/XOR recipes on x86, fmod is div+trunc+fnmadd only for finite b and small `a/b`
  (a/b rounds, so add a sign correction, and call scalar fmod outside that domain), integer mod is scalar
  division guarding b == 0 and b == -1 (SVE has `svdiv`+`svmls`), AVX2 f16 arithmetic converts through f32 (but f16 abs/neg/select work bitwise on the storage).
- **tails**: AVX2/NEON have no predication — remainder loop only. AVX-512 masks with
  `_mm512_cmplt_epu{64,32}_mask`; SVE's `svwhilelt` predicate subsumes every tail strategy (no remainder
  loop, runtime `svcntd()`/`svcntw()` step).
- Loads/stores: always the unaligned forms (`loadu`/`storeu`, `vld1q`, `svld1`); unaligned load on aligned
  memory is free, aligned load on unaligned memory faults.

## Reference priority (the lookup-before-docs rule)

1. Alloy's `report.md` / `report.json` — what the sweep already measured; never re-derive it.
2. `python -m alloy.isa ...` — one call is about 300 bytes; `kernel --level` keeps a function to one kernel.
3. The generated pages in this skill's `isa/` folder (`index.md`, one page per ISA, `kernels.md`,
   `transcendentals.md`) — 60 KB of static context rendered from `intrinsics.toml`, for reading a whole ISA.

The `isa/` pages are generated: `python -m alloy.isa.render` after changing the table (maintenance
workflow: the `alloy-isa-gen` skill). Never edit them by hand.

Tenstorrent Tensix is out of scope for the table (no C intrinsic path). Coverage is the core op set
plus exp/sin/cos as polynomial tiers (Taylor + Chebyshev, error measured against libm) and
per-veclib library spellings (libmvec names verified against the host's libmvec, SLEEF names per
sleef.org); extend `alloy/isa/intrinsics.toml` (spellings verified against the clang resource headers)
when a kernel needs more.
