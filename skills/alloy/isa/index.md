# Alloy ISA reference (generated from intrinsics.toml — do not edit)

The machine abstract math ISA and its per-target spellings. The abstract ops:

| op | math | kind | result |
|---|---|---|---|
| `load` | v[j] = p[j] for every active lane j | memory | vector |
| `store` | p[j] = v[j] for every active lane j | memory | none |
| `gather` | v[j] = base[idx[j]] (indirect load) | memory | vector |
| `scatter` | base[idx[j]] = v[j] (indirect store) | memory | none |
| `broadcast` | v[j] = s for every lane j (s is a scalar) | elementwise | vector |
| `add` | v[j] = a[j] + b[j] | elementwise | vector |
| `sub` | v[j] = a[j] - b[j] | elementwise | vector |
| `mul` | v[j] = a[j] * b[j] | elementwise | vector |
| `div` | v[j] = a[j] / b[j] | elementwise | vector |
| `mod` | v[j] = a[j] % b[j]: fmod for f64/f32 (sign of a), truncated remainder for i64/i32 | elementwise | vector |
| `fma` | one rounding: v[j] = a[j]*b[j] + c[j] | elementwise | vector |
| `sqrt` | v[j] = sqrt(x[j]) | elementwise | vector |
| `min` | v[j] = min(a[j], b[j]) | elementwise | vector |
| `max` | v[j] = max(a[j], b[j]) | elementwise | vector |
| `abs` | v[j] = |x[j]| | elementwise | vector |
| `neg` | v[j] = -x[j] | elementwise | vector |
| `select` | v[j] = mask[j] ? t[j] : f[j] (per-lane blend) | elementwise | vector |
| `and` | v[j] = a[j] & b[j] (integer lanes) | bitwise | vector |
| `or` | v[j] = a[j] | b[j] (integer lanes) | bitwise | vector |
| `shl` | v[j] = a[j] << b[j] (integer lanes) | shift | vector |
| `shr` | v[j] = a[j] >> b[j], logical (integer lanes) | shift | vector |
| `land` | v[j] = (a[j] != 0) && (b[j] != 0), as 0/1 lanes | logical | vector |
| `lor` | v[j] = (a[j] != 0) || (b[j] != 0), as 0/1 lanes | logical | vector |
| `reduce_add` | s = sum of every active lane of v | reduction | scalar |
| `exp` | v[j] = exp(x[j]) | transcendental | vector |
| `sin` | v[j] = sin(x[j]) | transcendental | vector |
| `cos` | v[j] = cos(x[j]) | transcendental | vector |
| `gen_mask` | lane j active iff i + j < N (the loop tail predicate) | mask | mask |
| `zero` | v[j] = 0 for every lane j | constant | vector |

Dtypes: `f64`/`f32` everywhere, `f16` where the hardware has it, `i64`/`i32` for the integer ops. A scalar operand of a binary op is broadcast.

## Pages

- [`avx2.md`](avx2.md) — AVX2 + FMA3 (256-bit VEX)
- [`avx512.md`](avx512.md) — AVX-512F (512-bit EVEX, opmask k0..k7)
- [`neon.md`](neon.md) — Arm NEON / AdvSIMD (fixed 128-bit)
- [`sve.md`](sve.md) — Arm SVE (scalable vectors, predicated)
- [`transcendentals.md`](transcendentals.md) — the exp/sin/cos polynomial tiers with measured ULP and the vector math library calls

