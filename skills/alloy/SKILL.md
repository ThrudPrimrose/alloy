---
name: alloy
description: "Alloy: DaCe's per-scope codegen backend, and the machine abstract math ISA (load, store, broadcast, +, -, *, /, fma, lanewise reduction, gen_mask) that maps auto-vectorized intrinsics back to math. Use when optimizing a kernel Alloy/DaCe vectorized, when reading vector intrinsic code or SIMD disassembly, or when you need the correct intrinsic spelling for avx2/avx512/neon/sve."
when: "you work on an HPCAgent-Bench kernel through Alloy or DaCe's extended backend, or you face vector intrinsic code / vectorized loops (source or disassembly) on x86 or AArch64 and need the spelling, the operand order, or the math an instruction computes"
---

# Alloy + the machine abstract math ISA

Alloy splits a DaCe program into scopes, builds each under many configurations (compiler, FP level, ISA
width, loop tails), verifies and times them, and links the best. DaCe's auto-vectorization is the base
layer: `compiler.alloy.mode` runs Alloy as DaCe's CPU backend, and the `sve_intrinsics` tail renders
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
| `mod` | `a[j] % b[j]` — fmod (floats) or truncated remainder (ints); no native vector form, recipes + libraries | elementwise |
| `and` `or` `shl` `shr` `land` `lor` | integer lanes, looked up under **i64/i32** (`land`/`lor` give all-ones/0 lanes or, on AVX-512/SVE, mask/predicate ops) | bitwise/shift/logical |

Dtypes are `f64`, `f32`, optional `f16` (AVX-512 FP16, NEON Armv8.2, SVE — **AVX2 emulates through
f32** with `cvtph_ps`/`cvtps_ph` recipes; bitwise f16 ops work directly on the storage), and `i64`/`i32`
for the integer ops. A binary op also accepts a scalar operand in either position — it is broadcast:
free as an EVEX embedded broadcast on AVX-512 (`{1to8}`), an explicit `set1`/`vdup`/`svdup`
elsewhere (`embedded_broadcast = true` marks the ISAs that fuse).

## Transcendentals: polynomial tiers with measured ULP, or a library call

`exp`, `sin`, `cos` have no hardware instruction on avx2/avx512/neon/sve. Each entry lists:

- **tiers** — Horner recipes in abstract-op steps (`fma`/`mul` with inline coefficients) with ULP
  error measured against libm: plain Taylor rungs (bad: sin-taylor7 ≈ 7e11 ulp on [-π/2, π/2]) and
  Chebyshev near-minimax tiers on the reduced domain (sin-quad-cheb13 ≈ 8.5 ulp). The ladder is the
  argument for minimax + careful range reduction — and why the library route usually wins.
- **libraries** — the vector math call per veclib (glibc libmvec `_ZGVcN4v_sin`, SVML `_mm256_sin_pd`,
  SLEEF `Sleef_sind4_u10`, all ≤ ~1–3.5 ulp documented). `reverse` knows these names, so a
  `call __svml_sin4` / `_ZGVcN4v_sin` in disassembly maps back to `sin`.

Range reduction dominates accuracy: the tiers assume `x` already reduced (Cody-Waite / quadrant for
sin/cos; k·ln2 + r split for exp, then scale by 2^k). Without hi/lo constants the reduction error
exceeds the polynomial error beyond a few multiples of π. Native assists: AVX-512 `vreducepd` (folds
π/2-multiple reduction into one instruction) and `vscalefpd` (2^k scaling); SVE `svexpa_f64` — a
hardware 2^(I/64) table, the sub-1-ulp exp building block (ACLE SVE 6.16.30) — plus `svscale`/`svlogb`.
Sub-1-ulp exp otherwise needs a 64-entry 2^(j/64) table (which is exactly what SVE's EXPA is).

## Lookup (cheap tool calls, no manuals)

```bash
python -m alloy.isa lookup <isa> <op> <dtype>   # op -> intrinsic, signature, semantics, traps
python -m alloy.isa reverse <name>              # intrinsic or mnemonic -> the math it computes
python -m alloy.isa validate [isa op dtype]     # the numerical gate: everything the host can execute
python -m alloy.isa ops | isas | schedule <isa>
```

Every `lookup` is **numerically validated on the host before it is returned**: a small compiled kernel
runs the looked-up intrinsic (or its fallback recipe) against a scalar reference, and transcendentals
are re-measured against libm. The output carries a `verified:` line; on failure the exit code is 3 and
the output lists potentially relevant spellings (same op on other dtypes/ISAs, the intrinsic's family)
instead of endorsing a wrong answer. `unverified:` marks ISAs the host cannot execute (NEON/SVE on x86)
— unverified is never reported as correct.

- ISAs: `avx2`, `avx512` (also `avx512_256` = same intrinsics at 256 bits), `neon`, `sve`. Dtypes: `f64`, `f32`.
- `reverse` accepts C intrinsics (`_mm512_add_pd`), recipe steps, and disassembler mnemonics as printed
  (`vaddpd`, `vfmadd231pd`, `fmla`, `ld1d`, `vaddpd.z`). Use it to read a build's disassembly back into math:
  `llvm-objdump -d <archive>` → mnemonics → `reverse` → the loop's dataflow.

```bash
python -m alloy.isa lookup sve fma f64
#   intrinsic: svmla_f64_x(pg, add, m1, m2) -> v
#   semantics: v[j] = add[j] + m1[j]*m2[j]   <- accumulator FIRST
python -m alloy.isa reverse vfmadd231pd
#   vfmadd231pd = fma on avx2/f64 and avx512/f64; v[j] = a[j]*b[j] + c[j]   <- accumulator LAST
```

## Traps the table encodes (never hardcode an operand order)

- **fma**: Intel `_mm256/_mm512_fmadd(a, b, c)` = `a*b + c` (products first); NEON `vfmaq(a, b, c)` and SVE
  `svmla_x(pg, add, m1, m2)` = `a + b*c` / `add + m1*m2` (accumulator first).
- **lane reduction**: one instruction on SVE (`svaddv`), AVX-512 (`_mm512_reduce_add_pd`, a header composite),
  NEON f32 (`vaddvq_f32`); a shuffle-add recipe on AVX2 and NEON f64 — keep those out of inner loops.
- **select/blend**: three different surfaces. AVX2 `_mm256_blendv_pd(a, b, mask)` puts the mask LAST and
  tests its **sign bit**; AVX-512 `_mm512_mask_blend_pd(k, a, b)` puts it FIRST and it picks b; NEON
  `vbslq_f64(mask, t, f)` and SVE `svsel_f64(pg, t, f)` also put it first and pick t.
- **gather/scatter**: AVX-512 gathers take `(idx, base)` — AVX2 took `(base, idx)`. Scatter needs AVX-512
  or SVE (`svld1_gather_*`/`svst1_scatter_*`); on AVX2/NEON the table gives the fallback recipes
  (scratch store + scalar per-lane accesses). Same fallback idea everywhere hardware lacks an op:
  FP abs/neg are sign-mask AND/XOR recipes on x86, fmod is div+trunc+fnmadd, integer mod is scalar
  division, AVX2 f16 arithmetic converts through f32 (but f16 abs/neg/select work bitwise on the storage).
- **tails**: AVX2/NEON have no predication — remainder loop only. AVX-512 masks with
  `_mm512_cmplt_epu{64,32}_mask`; SVE's `svwhilelt` predicate subsumes every tail strategy (no remainder
  loop, runtime `svcntd()`/`svcntw()` step).
- Loads/stores: always the unaligned forms (`loadu`/`storeu`, `vld1q`, `svld1`); unaligned load on aligned
  memory is free, aligned load on unaligned memory faults.

## Reference priority (the lookup-before-docs rule)

1. Alloy's `report.md` / `report.json` — what the sweep already measured; never re-derive it.
2. The generated pages in this skill's `isa/` folder (`index.md`, one page per ISA, `transcendentals.md`)
   — static context rendered from `intrinsics.toml`, always current; read these before any tool call.
3. `python -m alloy.isa ...` — for what the pages don't cover (custom reverse lookups, schedule details).
4. Per-target ESSENTIALS sheets (ISA docs package) — machine model and schedules beyond the table.
5. Itemized PDF indexes — a needle query for the one fact the table lacks, never an end-to-end read.

The `isa/` pages are generated: `python -m alloy.isa.render` after changing the table (maintenance
workflow: the `alloy-isa-gen` skill). Never edit them by hand.

Tenstorrent Tensix is out of scope for the table (no C intrinsic path). Coverage is the core op set
plus exp/sin/cos as polynomial tiers (Taylor + Chebyshev near-minimax, ULP measured against libm) and
per-veclib library spellings (libmvec names verified against the host's libmvec, SLEEF names per
sleef.org); extend `alloy/isa/intrinsics.toml` (spellings verified against the clang resource headers)
when a kernel needs more.
