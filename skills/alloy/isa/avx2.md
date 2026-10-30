# avx2 — AVX2 + FMA3 (256-bit VEX)

Vector bytes: 32; lanes: f64: 4, f32: 8, f16: 16, i64: 4, i32: 8; no predication.

Legal schedules: scalar, scalar_remainder. gen_mask: unsupported (no predication).

- **scalar** (Scalar loop): No vectorization: one element per iteration, no tail handling. The baseline every speedup is measured against. Tail: none.
  - gcc: -fno-tree-vectorize
  - clang: #pragma clang loop vectorize(disable)
- **scalar_remainder** (Vector main loop + scalar remainder): The vectorizer's default shape on maskless ISAs: a full-width main loop while i + VL <= N, then a scalar loop for the last N mod VL elements (AVX2, NEON; AVX-512 may also use it instead of masking). Tail: scalar remainder loop after the vector main loop.
  - gcc: --param vect-partial-vector-usage=0 (epilogue vectorization off)
  - clang: #pragma clang loop vectorize_width(VL) interleave_count(k) (scalar epilogue on maskless ISAs)

No predication: every tail is a remainder loop. Cross-lane ops (vhaddpd, vperm2f128) are slow; keep reductions out of inner loops. Mixing SSE and VEX stalls on old targets: vzeroupper after 256-bit code.

### f64

| op | spelling | mnemonic | signature | masked |
|---|---|---|---|---|
| `load` | `_mm256_loadu_pd` | `vmovupd` | `(p) -> v` | — |
| `store` | `_mm256_storeu_pd` | `vmovupd` | `(p, v) -> void` | — |
| `broadcast` | `_mm256_set1_pd` | `vbroadcastsd` | `(s) -> v` | — |
| `add` | `_mm256_add_pd` | `vaddpd` | `(a, b) -> v` | — |
| `sub` | `_mm256_sub_pd` | `vsubpd` | `(a, b) -> v` | — |
| `mul` | `_mm256_mul_pd` | `vmulpd` | `(a, b) -> v` | — |
| `div` | `_mm256_div_pd` | `vdivpd` | `(a, b) -> v` | — |
| `fma` | `_mm256_fmadd_pd` | `vfmadd` | `(a, b, c) -> v` | — |
| `reduce_add` | recipe: _mm256_castpd256_pd128 -> _mm256_extractf128_pd -> _mm_add_pd -> ... | `vextractf128 + vaddpd + vunpckhpd + vaddsd` | `(v) -> s` | — |
| `zero` | `_mm256_setzero_pd` | `vxorpd` | `() -> v` | — |
| `exp` | 6 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — |
| `sin` | 5 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — |
| `cos` | 5 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — |
| `sqrt` | `_mm256_sqrt_pd` | `vsqrtpd` | `(v) -> v` | — |
| `min` | `_mm256_min_pd` | `vminpd` | `(a, b) -> v` | — |
| `max` | `_mm256_max_pd` | `vmaxpd` | `(a, b) -> v` | — |
| `abs` | recipe: _mm256_castsi256_pd -> _mm256_set1_epi64x -> _mm256_and_pd | `vandpd` | `(v) -> v` | — |
| `neg` | recipe: _mm256_castsi256_pd -> _mm256_set1_epi64x -> _mm256_xor_pd | `vxorpd` | `(v) -> v` | — |
| `select` | `_mm256_blendv_pd` | `vblendvpd` | `(a, b, mask) -> v` | — |
| `mod` | recipe: _mm256_div_pd -> _mm256_round_pd -> _mm256_fnmadd_pd | `vdivpd+vroundpd+vfnmadd` | `(a, b) -> v` | — |
| `gather` | `_mm256_i64gather_pd` | `vgatherqpd` | `(base, idx, scale) -> v` | — |
| `scatter` | recipe: no vector scatter before AVX-512: _mm256_storeu_pd(v) to a scratch buffer, then scalar per-lane stores; restructure to gather-on-load where possible | `storeu+scalar` | `(base, idx, v) -> void` | — |

### f32

| op | spelling | mnemonic | signature | masked |
|---|---|---|---|---|
| `load` | `_mm256_loadu_ps` | `vmovups` | `(p) -> v` | — |
| `store` | `_mm256_storeu_ps` | `vmovups` | `(p, v) -> void` | — |
| `broadcast` | `_mm256_set1_ps` | `vbroadcastss` | `(s) -> v` | — |
| `add` | `_mm256_add_ps` | `vaddps` | `(a, b) -> v` | — |
| `sub` | `_mm256_sub_ps` | `vsubps` | `(a, b) -> v` | — |
| `mul` | `_mm256_mul_ps` | `vmulps` | `(a, b) -> v` | — |
| `div` | `_mm256_div_ps` | `vdivps` | `(a, b) -> v` | — |
| `fma` | `_mm256_fmadd_ps` | `vfmadd` | `(a, b, c) -> v` | — |
| `reduce_add` | recipe: _mm256_castps256_ps128 -> _mm256_extractf128_ps -> _mm_add_ps -> ... | `vextractf128 + vaddps + vmovshdup + vmovhlps + vaddss` | `(v) -> s` | — |
| `zero` | `_mm256_setzero_ps` | `vxorps` | `() -> v` | — |
| `exp` | 6 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — |
| `sin` | 5 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — |
| `cos` | 5 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — |
| `sqrt` | `_mm256_sqrt_ps` | `vsqrtps` | `(v) -> v` | — |
| `min` | `_mm256_min_ps` | `vminps` | `(a, b) -> v` | — |
| `max` | `_mm256_max_ps` | `vmaxps` | `(a, b) -> v` | — |
| `abs` | recipe: _mm256_castsi256_ps -> _mm256_set1_epi32 -> _mm256_and_ps | `vandps` | `(v) -> v` | — |
| `neg` | recipe: _mm256_castsi256_ps -> _mm256_set1_epi32 -> _mm256_xor_ps | `vxorps` | `(v) -> v` | — |
| `select` | `_mm256_blendv_ps` | `vblendvps` | `(a, b, mask) -> v` | — |
| `mod` | recipe: _mm256_div_ps -> _mm256_round_ps -> _mm256_fnmadd_ps | `vdivps+vroundps+vfnmadd` | `(a, b) -> v` | — |
| `gather` | `_mm256_i32gather_ps` | `vgatherdps` | `(base, idx, scale) -> v` | — |
| `scatter` | recipe: no vector scatter before AVX-512: _mm256_storeu_ps(v) to a scratch buffer, then scalar per-lane stores | `storeu+scalar` | `(base, idx, v) -> void` | — |

### f16

| op | spelling | mnemonic | signature | masked |
|---|---|---|---|---|
| `load` | `_mm256_loadu_si256` | `vmovdqu` | `(p) -> v` | — |
| `store` | `_mm256_storeu_si256` | `vmovdqu` | `(p, v) -> void` | — |
| `broadcast` | `_mm256_set1_epi16` | `vpbroadcastw` | `(s) -> v` | — |
| `add` | recipe: _mm256_cvtph_ps -> _mm256_add_ps -> _mm256_cvtps_ph | `vcvtph2ps+op+vcvtps2ph` | `(a, b) -> v` | — |
| `sub` | recipe: _mm256_cvtph_ps -> _mm256_sub_ps -> _mm256_cvtps_ph | `vcvtph2ps+op+vcvtps2ph` | `(a, b) -> v` | — |
| `mul` | recipe: _mm256_cvtph_ps -> _mm256_mul_ps -> _mm256_cvtps_ph | `vcvtph2ps+op+vcvtps2ph` | `(a, b) -> v` | — |
| `div` | recipe: _mm256_cvtph_ps -> _mm256_div_ps -> _mm256_cvtps_ph | `vcvtph2ps+op+vcvtps2ph` | `(a, b) -> v` | — |
| `fma` | recipe: _mm256_cvtph_ps -> _mm256_fmadd_ps -> _mm256_cvtps_ph | `vcvtph2ps+op+vcvtps2ph` | `(a, b, c) -> v` | — |
| `sqrt` | recipe: _mm256_cvtph_ps -> _mm256_sqrt_ps -> _mm256_cvtps_ph | `vcvtph2ps+op+vcvtps2ph` | `(v) -> v` | — |
| `min` | recipe: _mm256_cvtph_ps -> _mm256_min_ps -> _mm256_cvtps_ph | `vcvtph2ps+op+vcvtps2ph` | `(a, b) -> v` | — |
| `max` | recipe: _mm256_cvtph_ps -> _mm256_max_ps -> _mm256_cvtps_ph | `vcvtph2ps+op+vcvtps2ph` | `(a, b) -> v` | — |
| `abs` | recipe: _mm256_set1_epi16 -> _mm256_and_si256 | `vpand` | `(v) -> v` | — |
| `neg` | recipe: _mm256_set1_epi16 -> _mm256_xor_si256 | `vpxor` | `(v) -> v` | — |
| `select` | recipe: _mm256_and_si256 -> _mm256_andnot_si256 -> _mm256_or_si256 | `vpand+vpandn+vpor` | `(mask, t, f) -> v` | — |

### i64 (integer lanes)

| op | spelling | mnemonic | signature | masked |
|---|---|---|---|---|
| `and` | `_mm256_and_si256` | `vpand` | `(a, b) -> v` | — |
| `or` | `_mm256_or_si256` | `vpor` | `(a, b) -> v` | — |
| `shl` | `_mm256_sllv_epi64` | `vpsllvq` | `(a, counts) -> v` | — |
| `shr` | `_mm256_srlv_epi64` | `vpsrlvq` | `(a, counts) -> v` | — |
| `land` | recipe: _mm256_cmpeq_epi64 -> _mm256_andnot_si256 -> _mm256_and_si256 | `vpcmpeq+vpandn+vpand` | `(a, b) -> v` | — |
| `lor` | recipe: _mm256_cmpeq_epi64 -> _mm256_and_si256 -> _mm256_andnot_si256 | `vpcmpeq+vpand+vpandn` | `(a, b) -> v` | — |
| `mod` | recipe: no vector remainder: divide scalar per lane, or double division while |a| < 2^53 -> r = a - q * b | `sdiv+mul` | `(a, b) -> v` | — |

### i32 (integer lanes)

| op | spelling | mnemonic | signature | masked |
|---|---|---|---|---|
| `and` | `_mm256_and_si256` | `vpand` | `(a, b) -> v` | — |
| `or` | `_mm256_or_si256` | `vpor` | `(a, b) -> v` | — |
| `shl` | `_mm256_sllv_epi32` | `vpsllvd` | `(a, counts) -> v` | — |
| `shr` | `_mm256_srlv_epi32` | `vpsrlvd` | `(a, counts) -> v` | — |
| `land` | recipe: _mm256_cmpeq_epi32 -> _mm256_andnot_si256 -> _mm256_and_si256 | `vpcmpeq+vpandn+vpand` | `(a, b) -> v` | — |
| `lor` | recipe: _mm256_cmpeq_epi32 -> _mm256_and_si256 -> _mm256_andnot_si256 | `vpcmpeq+vpand+vpandn` | `(a, b) -> v` | — |
| `mod` | recipe: no vector remainder: divide scalar per lane, or double division while |a| < 2^53 -> r = a - q * b | `sdiv+mul` | `(a, b) -> v` | — |

## Hardware assists

| intrinsic | mnemonic | helps | note |
|---|---|---|---|
| `_mm256_rcp_ps` | `vrcpps` | div | 12-bit reciprocal estimate, f32 only; Newton refinement for a fast divide (no f64 form on AVX2) |
| `_mm256_rsqrt_ps` | `vrsqrtps` | sqrt | 12-bit rsqrt estimate, f32 only; Newton refinement (no f64 form on AVX2) |
| `_mm256_dp_ps` | `vdpps` | reduce_add | dot product: horizontal add of products with an immediate lane mask; useful for short reductions |

## Traps

- **select** (f64): operand-order trap: mask is LAST and it picks b; blendv tests the mask's SIGN BIT, not ==1 - feed it compare results (all-ones/all-zeros), x86 calls this op blend
- **select** (f32): operand-order trap: mask is LAST and it picks b; blendv tests the mask's SIGN BIT, not ==1 - feed it compare results (all-ones/all-zeros), x86 calls this op blend
