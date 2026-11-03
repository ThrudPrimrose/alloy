# avx2 — AVX2 + FMA3 (256-bit VEX)

Vector bytes: 32; lanes: f64: 4, f32: 8, f16: 16, i64: 4, i32: 8; no predication.

Legal schedules: scalar, scalar_remainder. gen_mask: unsupported (no predication).

- **scalar** (Scalar loop): No vectorization: one element per iteration, no tail handling. The baseline every speedup is measured against. Tail: none.
  - gcc: -fno-tree-vectorize
  - clang: #pragma clang loop vectorize(disable)
- **scalar_remainder** (Vector main loop + scalar remainder): The vectorizer's default shape on maskless ISAs: a full-width main loop while i + VL <= N, then a scalar loop for the last N mod VL elements (AVX2, NEON; AVX-512 may also use it instead of masking). Tail: scalar remainder loop after the vector main loop.
  - gcc: --param vect-partial-vector-usage=0 --param vect-epilogues-nomask=0
  - clang: #pragma clang loop vectorize_width(VL) interleave_count(k) (scalar epilogue on maskless ISAs)

Flags: -mavx2 -mfma (f16 lanes add -mf16c). No masked arithmetic, every tail is a remainder loop; vmaskmovpd/vpmaskmovd do load and store a tail without faulting past the mask. Horizontal and cross-lane ops (vhaddpd works inside each 128-bit half, vperm2f128) are slow; keep reductions out of inner loops. Mixing SSE and VEX stalls on old targets: vzeroupper after 256-bit code.

### f64

| op | spelling | mnemonic | signature | masked | semantics | note |
|---|---|---|---|---|---|---|
| `load` | `_mm256_loadu_pd` | `vmovupd` | `(p) -> v` | — | v[j] = p[j], j = 0..3 |  |
| `store` | `_mm256_storeu_pd` | `vmovupd` | `(p, v) -> void` | — | p[j] = v[j], j = 0..3 |  |
| `broadcast` | `_mm256_set1_pd` | `vbroadcastsd` | `(s) -> v` | — | v[j] = s, j = 0..3 |  |
| `add` | `_mm256_add_pd` | `vaddpd` | `(a, b) -> v` | — | v[j] = a[j] + b[j] |  |
| `sub` | `_mm256_sub_pd` | `vsubpd` | `(a, b) -> v` | — | v[j] = a[j] - b[j] |  |
| `mul` | `_mm256_mul_pd` | `vmulpd` | `(a, b) -> v` | — | v[j] = a[j] * b[j] |  |
| `div` | `_mm256_div_pd` | `vdivpd` | `(a, b) -> v` | — | v[j] = a[j] / b[j] | slow (~13 cycles); a*(1/b) with an invariant divisor changes rounding: reassoc or fast level only |
| `fma` | `_mm256_fmadd_pd` | `vfmadd` | `(a, b, c) -> v` | — | v[j] = a[j]*b[j] + c[j] | Intel order: products first, accumulator last; never write it from another ISA's memory |
| `reduce_add` | recipe: `__m128d s2 = _mm_add_pd(_mm256_castpd256_pd128(v), _mm256_extractf128_pd(v, 1))`; `_mm_cvtsd_f64(_mm_add_sd(s2, _mm_unpackhi_pd(s2, s2)))` | `vextractf128 + vaddpd + vunpckhpd + vaddsd` | `(v) -> s` | — | s = sum of the 4 lanes of v | no single intrinsic: add the 128-bit halves, then horizontal; pairs (l0+l2)+(l1+l3), so the result differs from a scalar left fold: needs reassociation permission |
| `zero` | `_mm256_setzero_pd` | `vxorpd` | `() -> v` | — | v[j] = 0.0 |  |
| `exp` | 6 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — | v[j] = exp(v[j]) | no native transcendental on x86, and no reduction assist either (AVX-512 vreducepd/vscalefpd have none here): range-reduce in software, evaluate a tier from [approx], or call a vector math library (the sweep's veclib axis builds the libmvec calls); split x = k*ln2 + r first (k = round(x/ln2)); the polynomial approximates exp(r) and the result scales by 2^k - a plain ln2 split loses accuracy for \|x\| > ~10, hi/lo ln2 constants fix that |
| `sin` | 5 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — | v[j] = sin(v[j]) | no native transcendental on x86, and no reduction assist either (AVX-512 vreducepd/vscalefpd have none here): range-reduce in software, evaluate a tier from [approx], or call a vector math library (the sweep's veclib axis builds the libmvec calls); range reduction dominates accuracy: the tiers assume x already reduced; without hi/lo pi/2 constants the reduction error exceeds the polynomial error for \|x\| beyond a few pi |
| `cos` | 5 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — | v[j] = cos(v[j]) | no native transcendental on x86, and no reduction assist either (AVX-512 vreducepd/vscalefpd have none here): range-reduce in software, evaluate a tier from [approx], or call a vector math library (the sweep's veclib axis builds the libmvec calls); range reduction dominates accuracy: the tiers assume x already reduced; without hi/lo pi/2 constants the reduction error exceeds the polynomial error for \|x\| beyond a few pi |
| `sqrt` | `_mm256_sqrt_pd` | `vsqrtpd` | `(v) -> v` | — | v[j] = sqrt(x[j]) |  |
| `min` | `_mm256_min_pd` | `vminpd` | `(a, b) -> v` | — | v[j] = min(a[j], b[j]) | not IEEE minNum: min(NaN,x)=x, min(x,NaN)=NaN, equal zeros return the second operand; pass the possibly-NaN value first or blend explicitly |
| `max` | `_mm256_max_pd` | `vmaxpd` | `(a, b) -> v` | — | v[j] = max(a[j], b[j]) | not IEEE minNum: min(NaN,x)=x, min(x,NaN)=NaN, equal zeros return the second operand; pass the possibly-NaN value first or blend explicitly |
| `abs` | recipe: `_mm256_and_pd(v, _mm256_castsi256_pd(_mm256_set1_epi64x(0x7fffffffffffffffLL)))` | `vandpd` | `(v) -> v` | — | v[j] = \|x[j]\| | no native FP abs (integer _mm256_abs_epi* only): AND with 0x7fff... as integer bits |
| `neg` | recipe: `_mm256_xor_pd(v, _mm256_castsi256_pd(_mm256_set1_epi64x((long long)0x8000000000000000ULL)))` | `vxorpd` | `(v) -> v` | — | v[j] = -x[j] | no native FP neg: XOR with the sign bit (0x8000...) as integer bits |
| `select` | `_mm256_blendv_pd` | `vblendvpd` | `(a, b, mask) -> v` | — | v[j] = signbit(mask[j]) ? b[j] : a[j] | operand-order trap: mask is LAST and it picks b; blendv tests the mask's SIGN BIT, not ==1 - feed it compare results (all-ones/all-zeros), x86 calls this op blend |
| `mod` | recipe: `__m256d q = _mm256_round_pd(_mm256_div_pd(a, b), _MM_FROUND_TO_ZERO \| _MM_FROUND_NO_EXC)`; `_mm256_fnmadd_pd(q, b, a)` | `vdivpd+vroundpd+vfnmadd` | `(a, b) -> v` | — | v[j] = a[j] - trunc(a[j]/b[j])*b[j]: fmod only for finite b and \|a/b\| below 2^p | no native fmod: q = trunc(a/b) via _mm256_round_{x} with _MM_FROUND_TO_ZERO\|_MM_FROUND_NO_EXC, then r = a - q*b; vector fmod calls live in the veclibs. The kernel of fmod is exact on every input (`kernel ISA fmod DTYPE`); this recipe holds only for finite b and \|a/b\| < 2^52 (f32: 2^23): a/b rounds, so correct with r += copysign(b, a) when sign(r) != sign(a), copysign the zero result, and call scalar fmod outside that domain |
| `gather` | `_mm256_i64gather_pd` | `vgatherqpd` | `(base, idx, scale) -> v` | — | v[j] = base[idx[j]], scale = 8 (bytes per lane) | slow on AMD Zen1/2 (microcoded): affine indices want a plain load |
| `scatter` | recipe: `double spill[4]`; `_mm256_storeu_pd(spill, v)`; `for (int j = 0; j < 4; j++) base[idx[j]] = spill[j]` | `storeu+scalar` | `(base, idx, v) -> void` | — | base[idx[j]] = v[j] |  |
| `lt` | `_mm256_cmp_pd` | `vcmppd` | `(a, b, _CMP_LT_OQ) -> mask` | — | lane j true iff a[j] < b[j]; false on NaN | all-ones lanes |

### f32

| op | spelling | mnemonic | signature | masked | semantics | note |
|---|---|---|---|---|---|---|
| `load` | `_mm256_loadu_ps` | `vmovups` | `(p) -> v` | — | v[j] = p[j], j = 0..7 |  |
| `store` | `_mm256_storeu_ps` | `vmovups` | `(p, v) -> void` | — | p[j] = v[j], j = 0..7 |  |
| `broadcast` | `_mm256_set1_ps` | `vbroadcastss` | `(s) -> v` | — | v[j] = s, j = 0..7 |  |
| `add` | `_mm256_add_ps` | `vaddps` | `(a, b) -> v` | — | v[j] = a[j] + b[j] |  |
| `sub` | `_mm256_sub_ps` | `vsubps` | `(a, b) -> v` | — | v[j] = a[j] - b[j] |  |
| `mul` | `_mm256_mul_ps` | `vmulps` | `(a, b) -> v` | — | v[j] = a[j] * b[j] |  |
| `div` | `_mm256_div_ps` | `vdivps` | `(a, b) -> v` | — | v[j] = a[j] / b[j] | slow; a*(1/b) with an invariant divisor changes rounding: reassoc or fast level only |
| `fma` | `_mm256_fmadd_ps` | `vfmadd` | `(a, b, c) -> v` | — | v[j] = a[j]*b[j] + c[j] | Intel order: products first, accumulator last |
| `reduce_add` | recipe: `__m128 s2 = _mm_add_ps(_mm256_castps256_ps128(v), _mm256_extractf128_ps(v, 1))`; `__m128 sh = _mm_movehdup_ps(s2)`; `s2 = _mm_add_ps(s2, sh)`; `sh = _mm_movehl_ps(sh, s2)`; `_mm_cvtss_f32(_mm_add_ss(s2, sh))` | `vextractf128 + vaddps+vaddps + vmovshdup + vmovhlps + vaddss` | `(v) -> s` | — | s = sum of the 8 lanes of v | no single intrinsic: add the 128-bit halves, then horizontal; a pairwise tree, so the result differs from a scalar left fold: needs reassociation permission |
| `zero` | `_mm256_setzero_ps` | `vxorps` | `() -> v` | — | v[j] = 0.0f |  |
| `exp` | 6 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — | v[j] = exp(v[j]) | no native transcendental on x86, and no reduction assist either (AVX-512 vreducepd/vscalefpd have none here): range-reduce in software, evaluate a tier from [approx], or call a vector math library (the sweep's veclib axis builds the libmvec calls); split x = k*ln2 + r first (k = round(x/ln2)); the polynomial approximates exp(r) and the result scales by 2^k - a plain ln2 split loses accuracy for \|x\| > ~10, hi/lo ln2 constants fix that |
| `sin` | 5 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — | v[j] = sin(v[j]) | no native transcendental on x86, and no reduction assist either (AVX-512 vreducepd/vscalefpd have none here): range-reduce in software, evaluate a tier from [approx], or call a vector math library (the sweep's veclib axis builds the libmvec calls); range reduction dominates accuracy: the tiers assume x already reduced; without hi/lo pi/2 constants the reduction error exceeds the polynomial error for \|x\| beyond a few pi |
| `cos` | 5 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — | v[j] = cos(v[j]) | no native transcendental on x86, and no reduction assist either (AVX-512 vreducepd/vscalefpd have none here): range-reduce in software, evaluate a tier from [approx], or call a vector math library (the sweep's veclib axis builds the libmvec calls); range reduction dominates accuracy: the tiers assume x already reduced; without hi/lo pi/2 constants the reduction error exceeds the polynomial error for \|x\| beyond a few pi |
| `sqrt` | `_mm256_sqrt_ps` | `vsqrtps` | `(v) -> v` | — | v[j] = sqrt(x[j]) |  |
| `min` | `_mm256_min_ps` | `vminps` | `(a, b) -> v` | — | v[j] = min(a[j], b[j]) | not IEEE minNum: min(NaN,x)=x, min(x,NaN)=NaN, equal zeros return the second operand; pass the possibly-NaN value first or blend explicitly |
| `max` | `_mm256_max_ps` | `vmaxps` | `(a, b) -> v` | — | v[j] = max(a[j], b[j]) | not IEEE minNum: min(NaN,x)=x, min(x,NaN)=NaN, equal zeros return the second operand; pass the possibly-NaN value first or blend explicitly |
| `abs` | recipe: `_mm256_and_ps(v, _mm256_castsi256_ps(_mm256_set1_epi32(0x7fffffff)))` | `vandps` | `(v) -> v` | — | v[j] = \|x[j]\| | no native FP abs (integer _mm256_abs_epi* only): AND with 0x7fff... as integer bits |
| `neg` | recipe: `_mm256_xor_ps(v, _mm256_castsi256_ps(_mm256_set1_epi32((int)0x80000000U)))` | `vxorps` | `(v) -> v` | — | v[j] = -x[j] | no native FP neg: XOR with the sign bit (0x8000...) as integer bits |
| `select` | `_mm256_blendv_ps` | `vblendvps` | `(a, b, mask) -> v` | — | v[j] = signbit(mask[j]) ? b[j] : a[j] | operand-order trap: mask is LAST and it picks b; blendv tests the mask's SIGN BIT, not ==1 - feed it compare results (all-ones/all-zeros), x86 calls this op blend |
| `mod` | recipe: `__m256 q = _mm256_round_ps(_mm256_div_ps(a, b), _MM_FROUND_TO_ZERO \| _MM_FROUND_NO_EXC)`; `_mm256_fnmadd_ps(q, b, a)` | `vdivps+vroundps+vfnmadd` | `(a, b) -> v` | — | v[j] = a[j] - trunc(a[j]/b[j])*b[j]: fmod only for finite b and \|a/b\| below 2^p | no native fmod: q = trunc(a/b) via _mm256_round_{x} with _MM_FROUND_TO_ZERO\|_MM_FROUND_NO_EXC, then r = a - q*b; vector fmod calls live in the veclibs. The kernel of fmod is exact on every input (`kernel ISA fmod DTYPE`); this recipe holds only for finite b and \|a/b\| < 2^52 (f32: 2^23): a/b rounds, so correct with r += copysign(b, a) when sign(r) != sign(a), copysign the zero result, and call scalar fmod outside that domain |
| `gather` | `_mm256_i32gather_ps` | `vgatherdps` | `(base, idx, scale) -> v` | — | v[j] = base[idx[j]], scale = 4 (bytes per lane) | 32-bit indices; slow on AMD Zen1/2 |
| `scatter` | recipe: `float spill[8]`; `_mm256_storeu_ps(spill, v)`; `for (int j = 0; j < 8; j++) base[idx[j]] = spill[j]` | `storeu+scalar` | `(base, idx, v) -> void` | — | base[idx[j]] = v[j] |  |
| `lt` | `_mm256_cmp_ps` | `vcmpps` | `(a, b, _CMP_LT_OQ) -> mask` | — | lane j true iff a[j] < b[j]; false on NaN | all-ones lanes |

### f16

| op | spelling | mnemonic | signature | masked | semantics | note |
|---|---|---|---|---|---|---|
| `load` | `_mm256_loadu_si256` | `vmovdqu` | `(p) -> v` | — | v[j] = p[j], 16 x f16 stored as integers | AVX2 has no f16 arithmetic (F16C converts only): load as integers, convert per half |
| `store` | `_mm256_storeu_si256` | `vmovdqu` | `(p, v) -> void` | — | p[j] = v[j], as integers |  |
| `broadcast` | `_mm256_set1_epi16` | `vpbroadcastw` | `(s) -> v` | — | v[j] = s, where s is the raw f16 bit pattern (bit-cast the value into a short first: a value converts wrongly) |  |
| `add` | recipe: `__m128i lo = _mm256_cvtps_ph(_mm256_add_ps(_mm256_cvtph_ps(_mm256_castsi256_si128(a)), _mm256_cvtph_ps(_mm256_castsi256_si128(b))), _MM_FROUND_TO_NEAREST_INT \| _MM_FROUND_NO_EXC)`; `__m128i hi = _mm256_cvtps_ph(_mm256_add_ps(_mm256_cvtph_ps(_mm256_extracti128_si256(a, 1)), _mm256_cvtph_ps(_mm256_extracti128_si256(b, 1))), _MM_FROUND_TO_NEAREST_INT \| _MM_FROUND_NO_EXC)`; `_mm256_set_m128i(hi, lo)` | `vcvtph2ps+op+vcvtps2ph` | `(a, b) -> v` | — | v[j] = add(a[j], b[j]) in f16, computed via f32 | convert 8 f16 -> 8 f32 (twice per 16-lane vector), compute in f32, convert back with _mm256_cvtps_ph(.., _MM_FROUND_TO_NEAREST_INT\|_MM_FROUND_NO_EXC); arithmetic effectively runs at 8 lanes; each step works on 8 lanes: load with _mm_loadu_si128 (a __m128i), step by 8, and build with -mf16c |
| `sub` | recipe: `__m128i lo = _mm256_cvtps_ph(_mm256_sub_ps(_mm256_cvtph_ps(_mm256_castsi256_si128(a)), _mm256_cvtph_ps(_mm256_castsi256_si128(b))), _MM_FROUND_TO_NEAREST_INT \| _MM_FROUND_NO_EXC)`; `__m128i hi = _mm256_cvtps_ph(_mm256_sub_ps(_mm256_cvtph_ps(_mm256_extracti128_si256(a, 1)), _mm256_cvtph_ps(_mm256_extracti128_si256(b, 1))), _MM_FROUND_TO_NEAREST_INT \| _MM_FROUND_NO_EXC)`; `_mm256_set_m128i(hi, lo)` | `vcvtph2ps+op+vcvtps2ph` | `(a, b) -> v` | — | v[j] = sub(a[j], b[j]) in f16, computed via f32 | convert 8 f16 -> 8 f32 (twice per 16-lane vector), compute in f32, convert back with _mm256_cvtps_ph(.., _MM_FROUND_TO_NEAREST_INT\|_MM_FROUND_NO_EXC); arithmetic effectively runs at 8 lanes |
| `mul` | recipe: `__m128i lo = _mm256_cvtps_ph(_mm256_mul_ps(_mm256_cvtph_ps(_mm256_castsi256_si128(a)), _mm256_cvtph_ps(_mm256_castsi256_si128(b))), _MM_FROUND_TO_NEAREST_INT \| _MM_FROUND_NO_EXC)`; `__m128i hi = _mm256_cvtps_ph(_mm256_mul_ps(_mm256_cvtph_ps(_mm256_extracti128_si256(a, 1)), _mm256_cvtph_ps(_mm256_extracti128_si256(b, 1))), _MM_FROUND_TO_NEAREST_INT \| _MM_FROUND_NO_EXC)`; `_mm256_set_m128i(hi, lo)` | `vcvtph2ps+op+vcvtps2ph` | `(a, b) -> v` | — | v[j] = mul(a[j], b[j]) in f16, computed via f32 | convert 8 f16 -> 8 f32 (twice per 16-lane vector), compute in f32, convert back with _mm256_cvtps_ph(.., _MM_FROUND_TO_NEAREST_INT\|_MM_FROUND_NO_EXC); arithmetic effectively runs at 8 lanes |
| `div` | recipe: `__m128i lo = _mm256_cvtps_ph(_mm256_div_ps(_mm256_cvtph_ps(_mm256_castsi256_si128(a)), _mm256_cvtph_ps(_mm256_castsi256_si128(b))), _MM_FROUND_TO_NEAREST_INT \| _MM_FROUND_NO_EXC)`; `__m128i hi = _mm256_cvtps_ph(_mm256_div_ps(_mm256_cvtph_ps(_mm256_extracti128_si256(a, 1)), _mm256_cvtph_ps(_mm256_extracti128_si256(b, 1))), _MM_FROUND_TO_NEAREST_INT \| _MM_FROUND_NO_EXC)`; `_mm256_set_m128i(hi, lo)` | `vcvtph2ps+op+vcvtps2ph` | `(a, b) -> v` | — | v[j] = div(a[j], b[j]) in f16, computed via f32 | convert 8 f16 -> 8 f32 (twice per 16-lane vector), compute in f32, convert back with _mm256_cvtps_ph(.., _MM_FROUND_TO_NEAREST_INT\|_MM_FROUND_NO_EXC); arithmetic effectively runs at 8 lanes |
| `fma` | recipe: `__m128i lo = _mm256_cvtps_ph(_mm256_fmadd_ps(_mm256_cvtph_ps(_mm256_castsi256_si128(a)), _mm256_cvtph_ps(_mm256_castsi256_si128(b)), _mm256_cvtph_ps(_mm256_castsi256_si128(c))), _MM_FROUND_TO_NEAREST_INT \| _MM_FROUND_NO_EXC)`; `__m128i hi = _mm256_cvtps_ph(_mm256_fmadd_ps(_mm256_cvtph_ps(_mm256_extracti128_si256(a, 1)), _mm256_cvtph_ps(_mm256_extracti128_si256(b, 1)), _mm256_cvtph_ps(_mm256_extracti128_si256(c, 1))), _MM_FROUND_TO_NEAREST_INT \| _MM_FROUND_NO_EXC)`; `_mm256_set_m128i(hi, lo)` | `vcvtph2ps+op+vcvtps2ph` | `(a, b, c) -> v` | — | v[j] = a[j]*b[j] + c[j] in f16, computed via f32; rounds twice, so not correctly rounded (about 1 f16 ulp) | convert 8 f16 -> 8 f32 (twice per 16-lane vector), compute in f32, convert back with _mm256_cvtps_ph(.., _MM_FROUND_TO_NEAREST_INT\|_MM_FROUND_NO_EXC); arithmetic effectively runs at 8 lanes |
| `sqrt` | recipe: `__m128i lo = _mm256_cvtps_ph(_mm256_sqrt_ps(_mm256_cvtph_ps(_mm256_castsi256_si128(v))), _MM_FROUND_TO_NEAREST_INT \| _MM_FROUND_NO_EXC)`; `__m128i hi = _mm256_cvtps_ph(_mm256_sqrt_ps(_mm256_cvtph_ps(_mm256_extracti128_si256(v, 1))), _MM_FROUND_TO_NEAREST_INT \| _MM_FROUND_NO_EXC)`; `_mm256_set_m128i(hi, lo)` | `vcvtph2ps+op+vcvtps2ph` | `(v) -> v` | — | v[j] = sqrt(x[j]) in f16, computed via f32 | convert 8 f16 -> 8 f32 (twice per 16-lane vector), compute in f32, convert back with _mm256_cvtps_ph(.., _MM_FROUND_TO_NEAREST_INT\|_MM_FROUND_NO_EXC); arithmetic effectively runs at 8 lanes |
| `min` | recipe: `__m128i lo = _mm256_cvtps_ph(_mm256_min_ps(_mm256_cvtph_ps(_mm256_castsi256_si128(a)), _mm256_cvtph_ps(_mm256_castsi256_si128(b))), _MM_FROUND_TO_NEAREST_INT \| _MM_FROUND_NO_EXC)`; `__m128i hi = _mm256_cvtps_ph(_mm256_min_ps(_mm256_cvtph_ps(_mm256_extracti128_si256(a, 1)), _mm256_cvtph_ps(_mm256_extracti128_si256(b, 1))), _MM_FROUND_TO_NEAREST_INT \| _MM_FROUND_NO_EXC)`; `_mm256_set_m128i(hi, lo)` | `vcvtph2ps+op+vcvtps2ph` | `(a, b) -> v` | — | v[j] = min(a[j], b[j]) in f16, computed via f32 | convert 8 f16 -> 8 f32 (twice per 16-lane vector), compute in f32, convert back with _mm256_cvtps_ph(.., _MM_FROUND_TO_NEAREST_INT\|_MM_FROUND_NO_EXC); arithmetic effectively runs at 8 lanes |
| `max` | recipe: `__m128i lo = _mm256_cvtps_ph(_mm256_max_ps(_mm256_cvtph_ps(_mm256_castsi256_si128(a)), _mm256_cvtph_ps(_mm256_castsi256_si128(b))), _MM_FROUND_TO_NEAREST_INT \| _MM_FROUND_NO_EXC)`; `__m128i hi = _mm256_cvtps_ph(_mm256_max_ps(_mm256_cvtph_ps(_mm256_extracti128_si256(a, 1)), _mm256_cvtph_ps(_mm256_extracti128_si256(b, 1))), _MM_FROUND_TO_NEAREST_INT \| _MM_FROUND_NO_EXC)`; `_mm256_set_m128i(hi, lo)` | `vcvtph2ps+op+vcvtps2ph` | `(a, b) -> v` | — | v[j] = max(a[j], b[j]) in f16, computed via f32 | convert 8 f16 -> 8 f32 (twice per 16-lane vector), compute in f32, convert back with _mm256_cvtps_ph(.., _MM_FROUND_TO_NEAREST_INT\|_MM_FROUND_NO_EXC); arithmetic effectively runs at 8 lanes |
| `abs` | recipe: `_mm256_and_si256(v, _mm256_set1_epi16(0x7fff))` | `vpand` | `(v) -> v` | — | v[j] = \|x[j]\| | sign-mask AND works directly on the f16 bits - no conversion |
| `neg` | recipe: `_mm256_xor_si256(v, _mm256_set1_epi16((short)0x8000))` | `vpxor` | `(v) -> v` | — | v[j] = -x[j] | sign-bit XOR on the f16 bits |
| `select` | recipe: `_mm256_or_si256(_mm256_and_si256(t, mask), _mm256_andnot_si256(mask, f))` | `vpand+vpandn+vpor` | `(mask, t, f) -> v` | — | v[j] = mask[j] ? t[j] : f[j] | bit select on the f16 bits: (t & mask) \| (f & ~mask), mask = all-ones/0 lanes |

### i64 (integer lanes)

| op | spelling | mnemonic | signature | masked | semantics | note |
|---|---|---|---|---|---|---|
| `and` | `_mm256_and_si256` | `vpand` | `(a, b) -> v` | — | v[j] = a[j] & b[j] |  |
| `or` | `_mm256_or_si256` | `vpor` | `(a, b) -> v` | — | v[j] = a[j] \| b[j] |  |
| `shl` | `_mm256_sllv_epi64` | `vpsllvq` | `(a, counts) -> v` | — | v[j] = a[j] << counts[j] |  |
| `shr` | `_mm256_srlv_epi64` | `vpsrlvq` | `(a, counts) -> v` | — | v[j] = a[j] >> counts[j], logical |  |
| `land` | recipe: `__m256i ones = _mm256_set1_epi64x(-1)`; `_mm256_and_si256(_mm256_andnot_si256(_mm256_cmpeq_epi64(a, _mm256_setzero_si256()), ones), _mm256_andnot_si256(_mm256_cmpeq_epi64(b, _mm256_setzero_si256()), ones))` | `vpcmpeq+vpandn+vpand` | `(a, b) -> v` | — | v[j] = (a[j] != 0) && (b[j] != 0), all-ones/0 lanes | and the andnot-equals-zero compares; the result is all-ones lanes, not 0/1 |
| `lor` | recipe: `_mm256_andnot_si256(_mm256_and_si256(_mm256_cmpeq_epi64(a, _mm256_setzero_si256()), _mm256_cmpeq_epi64(b, _mm256_setzero_si256())), _mm256_set1_epi64x(-1))` | `vpcmpeq+vpand+vpandn` | `(a, b) -> v` | — | v[j] = (a[j] != 0) \|\| (b[j] != 0), all-ones/0 lanes |  |
| `mod` | recipe: `int64_t x[4], y[4]`; `_mm256_storeu_si256((__m256i*)x, a)`; `_mm256_storeu_si256((__m256i*)y, b)`; `for (int j = 0; j < 4; j++) x[j] = y[j] == 0 \|\| y[j] == -1 ? 0 : x[j] % y[j]`; `_mm256_loadu_si256((const __m256i*)x)` | `idiv` | `(a, b) -> v` | — | v[j] = a[j] % b[j], truncated (sign of a) |  |
| `add` | `_mm256_add_epi64` | `vpaddq` | `(a, b) -> v` | — | v[j] = a[j] + b[j], wrapping |  |
| `sub` | `_mm256_sub_epi64` | `vpsubq` | `(a, b) -> v` | — | v[j] = a[j] - b[j], wrapping |  |
| `mul` | recipe: `__m256i cross = _mm256_mullo_epi32(a, _mm256_shuffle_epi32(b, 0xB1))`; `__m256i high = _mm256_slli_epi64(_mm256_add_epi64(cross, _mm256_srli_epi64(cross, 32)), 32)`; `_mm256_add_epi64(_mm256_mul_epu32(a, b), high)` | `vpmuludq+vpmulld+vpsllq+vpaddq` | `(a, b) -> v` | — | v[j] = a[j] * b[j], low bits | no vpmullq on AVX2: lo*lo + ((hi(a)*lo(b) + lo(a)*hi(b)) << 32) |
| `min` | recipe: `_mm256_blendv_epi8(a, b, _mm256_cmpgt_epi64(a, b))` | `vpcmpgtq+vpblendvb` | `(a, b) -> v` | — | v[j] = min(a[j], b[j]), signed | no vpminsq on AVX2: blend on a > b |
| `max` | recipe: `_mm256_blendv_epi8(b, a, _mm256_cmpgt_epi64(a, b))` | `vpcmpgtq+vpblendvb` | `(a, b) -> v` | — | v[j] = max(a[j], b[j]), signed | no vpmaxsq on AVX2: blend on a > b |
| `load` | `_mm256_loadu_si256` | `vmovdqu` | `(p) -> v` | — | v[j] = p[j] | takes a const __m256i*: cast the pointer |
| `store` | `_mm256_storeu_si256` | `vmovdqu` | `(p, v)` | — | p[j] = v[j] | takes a __m256i*: cast the pointer |
| `broadcast` | `_mm256_set1_epi64x` | `vpbroadcastq` | `(s) -> v` | — | v[j] = s |  |
| `lt` | `_mm256_cmpgt_epi64` | `vpcmpgtq` | `(b, a) -> mask` | — | lane j true iff a[j] < b[j], signed | only greater-than exists, so b goes first; all-ones lanes |

### i32 (integer lanes)

| op | spelling | mnemonic | signature | masked | semantics | note |
|---|---|---|---|---|---|---|
| `and` | `_mm256_and_si256` | `vpand` | `(a, b) -> v` | — | v[j] = a[j] & b[j] |  |
| `or` | `_mm256_or_si256` | `vpor` | `(a, b) -> v` | — | v[j] = a[j] \| b[j] |  |
| `shl` | `_mm256_sllv_epi32` | `vpsllvd` | `(a, counts) -> v` | — | v[j] = a[j] << counts[j] |  |
| `shr` | `_mm256_srlv_epi32` | `vpsrlvd` | `(a, counts) -> v` | — | v[j] = a[j] >> counts[j], logical |  |
| `land` | recipe: `__m256i ones = _mm256_set1_epi32(-1)`; `_mm256_and_si256(_mm256_andnot_si256(_mm256_cmpeq_epi32(a, _mm256_setzero_si256()), ones), _mm256_andnot_si256(_mm256_cmpeq_epi32(b, _mm256_setzero_si256()), ones))` | `vpcmpeq+vpandn+vpand` | `(a, b) -> v` | — | v[j] = (a[j] != 0) && (b[j] != 0), all-ones/0 lanes | and the andnot-equals-zero compares; the result is all-ones lanes, not 0/1 |
| `lor` | recipe: `_mm256_andnot_si256(_mm256_and_si256(_mm256_cmpeq_epi32(a, _mm256_setzero_si256()), _mm256_cmpeq_epi32(b, _mm256_setzero_si256())), _mm256_set1_epi32(-1))` | `vpcmpeq+vpand+vpandn` | `(a, b) -> v` | — | v[j] = (a[j] != 0) \|\| (b[j] != 0), all-ones/0 lanes |  |
| `mod` | recipe: `int32_t x[8], y[8]`; `_mm256_storeu_si256((__m256i*)x, a)`; `_mm256_storeu_si256((__m256i*)y, b)`; `for (int j = 0; j < 8; j++) x[j] = y[j] == 0 \|\| y[j] == -1 ? 0 : x[j] % y[j]`; `_mm256_loadu_si256((const __m256i*)x)` | `idiv` | `(a, b) -> v` | — | v[j] = a[j] % b[j], truncated (sign of a) |  |
| `add` | `_mm256_add_epi32` | `vpaddd` | `(a, b) -> v` | — | v[j] = a[j] + b[j], wrapping |  |
| `sub` | `_mm256_sub_epi32` | `vpsubd` | `(a, b) -> v` | — | v[j] = a[j] - b[j], wrapping |  |
| `mul` | `_mm256_mullo_epi32` | `vpmulld` | `(a, b) -> v` | — | v[j] = a[j] * b[j], low bits |  |
| `min` | `_mm256_min_epi32` | `vpminsd` | `(a, b) -> v` | — | v[j] = min(a[j], b[j]), signed |  |
| `max` | `_mm256_max_epi32` | `vpmaxsd` | `(a, b) -> v` | — | v[j] = max(a[j], b[j]), signed |  |
| `load` | `_mm256_loadu_si256` | `vmovdqu` | `(p) -> v` | — | v[j] = p[j] | takes a const __m256i*: cast the pointer |
| `store` | `_mm256_storeu_si256` | `vmovdqu` | `(p, v)` | — | p[j] = v[j] | takes a __m256i*: cast the pointer |
| `broadcast` | `_mm256_set1_epi32` | `vpbroadcastd` | `(s) -> v` | — | v[j] = s |  |
| `lt` | `_mm256_cmpgt_epi32` | `vpcmpgtd` | `(b, a) -> mask` | — | lane j true iff a[j] < b[j], signed | only greater-than exists, so b goes first; all-ones lanes |

## Hardware assists

| intrinsic | mnemonic | helps | note |
|---|---|---|---|
| `_mm256_rcp_ps` | `vrcpps` | div | 12-bit reciprocal estimate, f32 only; Newton refinement for a fast divide (no f64 form on AVX2) |
| `_mm256_rsqrt_ps` | `vrsqrtps` | sqrt | 12-bit rsqrt estimate, f32 only; Newton refinement (no f64 form on AVX2) |
| `_mm256_dp_ps` | `vdpps` | reduce_add | dot product inside EACH 128-bit half (lane 0 of each half holds that half's sum): add the two halves for a full-vector sum |
