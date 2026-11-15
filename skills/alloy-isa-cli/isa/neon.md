# neon — Arm NEON / AdvSIMD (fixed 128-bit)

Vector bytes: 16; lanes: f64: 2, f32: 4, f16: 8, i64: 2, i32: 4; no predication.

Legal schedules: scalar, scalar_remainder. gen_mask: unsupported (no predication).

- **scalar** (Scalar loop): No vectorization: one element per iteration, no tail handling. The baseline every speedup is measured against. Tail: none.
  - gcc: -fno-tree-vectorize
  - clang: #pragma clang loop vectorize(disable)
- **scalar_remainder** (Vector main loop + scalar remainder): The vectorizer's default shape on maskless ISAs: a full-width main loop while i + VL <= N, then a scalar loop for the last N mod VL elements (AVX2, NEON; AVX-512 may also use it instead of masking). Tail: scalar remainder loop after the vector main loop.
  - gcc: --param vect-partial-vector-usage=0 --param vect-epilogues-nomask=0
  - clang: #pragma clang loop vectorize_width(VL) interleave_count(k) (scalar epilogue on maskless ISAs)

AArch64 baseline (no -m flag). No predication: every tail is a remainder loop. NEON and SVE coexist on one core; gcc --param=aarch64-autovec-preference and clang -mllvm -scalable-vectorization=off gate which the auto-vectorizer prefers. fma availability: vfmaq_f64 (ACLE __ARM_FEATURE_FMA).

### f64

| op | spelling | mnemonic | signature | masked | semantics | note |
|---|---|---|---|---|---|---|
| `load` | `vld1q_f64` | `ld1` | `(p) -> v` | — | v[j] = p[j], j = 0..1 |  |
| `store` | `vst1q_f64` | `st1` | `(p, v) -> void` | — | p[j] = v[j], j = 0..1 |  |
| `broadcast` | `vdupq_n_f64` | `dup` | `(s) -> v` | — | v[j] = s, j = 0..1 |  |
| `add` | `vaddq_f64` | `fadd` | `(a, b) -> v` | — | v[j] = a[j] + b[j] |  |
| `sub` | `vsubq_f64` | `fsub` | `(a, b) -> v` | — | v[j] = a[j] - b[j] |  |
| `mul` | `vmulq_f64` | `fmul` | `(a, b) -> v` | — | v[j] = a[j] * b[j] |  |
| `div` | `vdivq_f64` | `fdiv` | `(a, b) -> v` | — | v[j] = a[j] / b[j] |  |
| `fma` | `vfmaq_f64` | `fmla` | `(a, b, c) -> v` | — | v[j] = a[j] + b[j]*c[j] | operand-order trap: the accumulator is FIRST, the products last (a + b*c) — the opposite of Intel's fmadd |
| `reduce_add` | `vaddvq_f64` | `faddp` | `(v) -> s` | — | s = sum of the 2 lanes of v | one faddp |
| `zero` | `vdupq_n_f64` | `movi` | `(0.0) -> v` | — | v[j] = 0.0 |  |
| `exp` | 6 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — | v[j] = exp(v[j]) | no native transcendental: range-reduce (Cody-Waite / quadrant) then a tier from [approx], or call SLEEF/ArmPL; NEON has no exponent or scaling assist - build 2^k by integer-adding k<<52 to the exponent bits (vreinterpretq_u64_f64 + vaddq_u64); split x = k*ln2 + r first (k = round(x/ln2)); the polynomial approximates exp(r) and the result scales by 2^k - a plain ln2 split loses accuracy for \|x\| > ~10, hi/lo ln2 constants fix that |
| `sin` | 5 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — | v[j] = sin(v[j]) | no native transcendental: range-reduce (Cody-Waite / quadrant) then a tier from [approx], or call SLEEF/ArmPL; NEON has no exponent or scaling assist - build 2^k by integer-adding k<<52 to the exponent bits (vreinterpretq_u64_f64 + vaddq_u64); range reduction dominates accuracy: the tiers assume x already reduced; without hi/lo pi/2 constants the reduction error exceeds the polynomial error for \|x\| beyond a few pi |
| `cos` | 5 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — | v[j] = cos(v[j]) | no native transcendental: range-reduce (Cody-Waite / quadrant) then a tier from [approx], or call SLEEF/ArmPL; NEON has no exponent or scaling assist - build 2^k by integer-adding k<<52 to the exponent bits (vreinterpretq_u64_f64 + vaddq_u64); range reduction dominates accuracy: the tiers assume x already reduced; without hi/lo pi/2 constants the reduction error exceeds the polynomial error for \|x\| beyond a few pi |
| `sqrt` | `vsqrtq_f64` | `fsqrt` | `(v) -> v` | — | v[j] = sqrt(x[j]) |  |
| `min` | `vminq_f64` | `fmin` | `(a, b) -> v` | — | v[j] = min(a[j], b[j]) | vminq/vmaxq propagate NaN; vminnmq/vmaxnmq are the IEEE minNum forms |
| `max` | `vmaxq_f64` | `fmax` | `(a, b) -> v` | — | v[j] = max(a[j], b[j]) |  |
| `abs` | `vabsq_f64` | `fabs` | `(v) -> v` | — | v[j] = \|x[j]\| | native on NEON, unlike x86 where abs is an AND-mask recipe |
| `neg` | `vnegq_f64` | `fneg` | `(v) -> v` | — | v[j] = -x[j] | native on NEON, unlike x86 where neg is an XOR-mask recipe |
| `select` | `vbslq_f64` | `bsl` | `(mask, t, f) -> v` | — | v[j] = mask[j] ? t[j] : f[j] | mask FIRST: all-ones lanes (from a compare) pick t; x86 puts the mask last and calls the op blend |
| `mod` | recipe: `float64x2_t q = vrndq_f64(vdivq_f64(a, b))`; `vfmsq_f64(a, q, b)` | `fdiv+frintz+fmls` | `(a, b) -> v` | — | v[j] = a[j] - trunc(a[j]/b[j])*b[j]: fmod only for finite b and \|a/b\| below 2^p | no fmod: q = vrndq_f64(a/b) (frintz, toward zero), r = vfmsq_f64(a, q, b) = a - q*b. The kernel of fmod is exact on every input (`kernel ISA fmod DTYPE`); this recipe holds only for finite b and \|a/b\| < 2^52 (f32: 2^23): a/b rounds, so correct with r += copysign(b, a) when sign(r) != sign(a), copysign the zero result, and call scalar fmod outside that domain |
| `gather` | recipe: `float64x2_t g = vdupq_n_f64(0)`; `g = vld1q_lane_f64(base + idx[0], g, 0)`; `vld1q_lane_f64(base + idx[1], g, 1)` | `ld1` | `(base, idx) -> v` | — | v[j] = base[idx[j]], scale = 8 (bytes per lane) |  |
| `scatter` | recipe: `vst1q_lane_f64(base + idx[0], v, 0)`; `vst1q_lane_f64(base + idx[1], v, 1)` | `str` | `(base, idx, v) -> void` | — | base[idx[j]] = v[j] |  |
| `lt` | `vcltq_f64` | `fcmgt` | `(a, b) -> mask` | — | lane j true iff a[j] < b[j]; false on NaN | all-ones lanes |

### f32

| op | spelling | mnemonic | signature | masked | semantics | note |
|---|---|---|---|---|---|---|
| `load` | `vld1q_f32` | `ld1` | `(p) -> v` | — | v[j] = p[j], j = 0..3 |  |
| `store` | `vst1q_f32` | `st1` | `(p, v) -> void` | — | p[j] = v[j], j = 0..3 |  |
| `broadcast` | `vdupq_n_f32` | `dup` | `(s) -> v` | — | v[j] = s, j = 0..3 |  |
| `add` | `vaddq_f32` | `fadd` | `(a, b) -> v` | — | v[j] = a[j] + b[j] |  |
| `sub` | `vsubq_f32` | `fsub` | `(a, b) -> v` | — | v[j] = a[j] - b[j] |  |
| `mul` | `vmulq_f32` | `fmul` | `(a, b) -> v` | — | v[j] = a[j] * b[j] |  |
| `div` | `vdivq_f32` | `fdiv` | `(a, b) -> v` | — | v[j] = a[j] / b[j] |  |
| `fma` | `vfmaq_f32` | `fmla` | `(a, b, c) -> v` | — | v[j] = a[j] + b[j]*c[j] | operand-order trap: the accumulator is FIRST, the products last (a + b*c) — the opposite of Intel's fmadd |
| `reduce_add` | `vaddvq_f32` | `faddp` | `(v) -> s` | — | s = sum of the 4 lanes of v | two faddp |
| `zero` | `vdupq_n_f32` | `movi` | `(0.0f) -> v` | — | v[j] = 0.0f |  |
| `exp` | 6 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — | v[j] = exp(v[j]) | no native transcendental: range-reduce (Cody-Waite / quadrant) then a tier from [approx], or call SLEEF/ArmPL; NEON has no exponent or scaling assist - build 2^k by integer-adding k<<23 to the exponent bits (vreinterpretq_u32_f32 + vaddq_u32); split x = k*ln2 + r first (k = round(x/ln2)); the polynomial approximates exp(r) and the result scales by 2^k - a plain ln2 split loses accuracy for \|x\| > ~10, hi/lo ln2 constants fix that |
| `sin` | 5 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — | v[j] = sin(v[j]) | no native transcendental: range-reduce (Cody-Waite / quadrant) then a tier from [approx], or call SLEEF/ArmPL; NEON has no exponent or scaling assist - build 2^k by integer-adding k<<23 to the exponent bits (vreinterpretq_u32_f32 + vaddq_u32); range reduction dominates accuracy: the tiers assume x already reduced; without hi/lo pi/2 constants the reduction error exceeds the polynomial error for \|x\| beyond a few pi |
| `cos` | 5 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — | v[j] = cos(v[j]) | no native transcendental: range-reduce (Cody-Waite / quadrant) then a tier from [approx], or call SLEEF/ArmPL; NEON has no exponent or scaling assist - build 2^k by integer-adding k<<23 to the exponent bits (vreinterpretq_u32_f32 + vaddq_u32); range reduction dominates accuracy: the tiers assume x already reduced; without hi/lo pi/2 constants the reduction error exceeds the polynomial error for \|x\| beyond a few pi |
| `sqrt` | `vsqrtq_f32` | `fsqrt` | `(v) -> v` | — | v[j] = sqrt(x[j]) |  |
| `min` | `vminq_f32` | `fmin` | `(a, b) -> v` | — | v[j] = min(a[j], b[j]) | vminq/vmaxq propagate NaN; vminnmq/vmaxnmq are the IEEE minNum forms |
| `max` | `vmaxq_f32` | `fmax` | `(a, b) -> v` | — | v[j] = max(a[j], b[j]) |  |
| `abs` | `vabsq_f32` | `fabs` | `(v) -> v` | — | v[j] = \|x[j]\| | native on NEON, unlike x86 where abs is an AND-mask recipe |
| `neg` | `vnegq_f32` | `fneg` | `(v) -> v` | — | v[j] = -x[j] | native on NEON, unlike x86 where neg is an XOR-mask recipe |
| `select` | `vbslq_f32` | `bsl` | `(mask, t, f) -> v` | — | v[j] = mask[j] ? t[j] : f[j] | mask FIRST: all-ones lanes (from a compare) pick t; x86 puts the mask last and calls the op blend |
| `mod` | recipe: `float32x4_t q = vrndq_f32(vdivq_f32(a, b))`; `vfmsq_f32(a, q, b)` | `fdiv+frintz+fmls` | `(a, b) -> v` | — | v[j] = a[j] - trunc(a[j]/b[j])*b[j]: fmod only for finite b and \|a/b\| below 2^p | no fmod: q = vrndq_f32(a/b) (frintz, toward zero), r = vfmsq_f32(a, q, b) = a - q*b. The kernel of fmod is exact on every input (`kernel ISA fmod DTYPE`); this recipe holds only for finite b and \|a/b\| < 2^52 (f32: 2^23): a/b rounds, so correct with r += copysign(b, a) when sign(r) != sign(a), copysign the zero result, and call scalar fmod outside that domain |
| `gather` | recipe: `float32x4_t g = vdupq_n_f32(0)`; `g = vld1q_lane_f32(base + idx[0], g, 0)`; `g = vld1q_lane_f32(base + idx[1], g, 1)`; `g = vld1q_lane_f32(base + idx[2], g, 2)`; `vld1q_lane_f32(base + idx[3], g, 3)` | `ld1` | `(base, idx) -> v` | — | v[j] = base[idx[j]], scale = 4 (bytes per lane) |  |
| `scatter` | recipe: `vst1q_lane_f32(base + idx[0], v, 0)`; `vst1q_lane_f32(base + idx[1], v, 1)`; `vst1q_lane_f32(base + idx[2], v, 2)`; `vst1q_lane_f32(base + idx[3], v, 3)` | `str` | `(base, idx, v) -> void` | — | base[idx[j]] = v[j] |  |
| `lt` | `vcltq_f32` | `fcmgt` | `(a, b) -> mask` | — | lane j true iff a[j] < b[j]; false on NaN | all-ones lanes |

### f16

| op | spelling | mnemonic | signature | masked | semantics | note |
|---|---|---|---|---|---|---|
| `add` | `vaddq_f16` | `fadd` | `(a, b) -> v` | — | v[j] = add(a[j], b[j]) | requires Armv8.2 FP16 vector arithmetic; fma keeps the NEON accumulator-first order |
| `sub` | `vsubq_f16` | `fsub` | `(a, b) -> v` | — | v[j] = sub(a[j], b[j]) | requires Armv8.2 FP16 vector arithmetic; fma keeps the NEON accumulator-first order |
| `mul` | `vmulq_f16` | `fmul` | `(a, b) -> v` | — | v[j] = mul(a[j], b[j]) | requires Armv8.2 FP16 vector arithmetic; fma keeps the NEON accumulator-first order |
| `div` | `vdivq_f16` | `fdiv` | `(a, b) -> v` | — | v[j] = div(a[j], b[j]) | requires Armv8.2 FP16 vector arithmetic; fma keeps the NEON accumulator-first order |
| `sqrt` | `vsqrtq_f16` | `fsqrt` | `(v) -> v` | — | v[j] = sqrt(x[j]) | requires Armv8.2 FP16 vector arithmetic; fma keeps the NEON accumulator-first order |
| `min` | `vminq_f16` | `fmin` | `(a, b) -> v` | — | v[j] = min(a[j], b[j]) | requires Armv8.2 FP16 vector arithmetic; fma keeps the NEON accumulator-first order |
| `max` | `vmaxq_f16` | `fmax` | `(a, b) -> v` | — | v[j] = max(a[j], b[j]) | requires Armv8.2 FP16 vector arithmetic; fma keeps the NEON accumulator-first order |
| `abs` | `vabsq_f16` | `fabs` | `(v) -> v` | — | v[j] = abs(x[j]) | requires Armv8.2 FP16 vector arithmetic; fma keeps the NEON accumulator-first order |
| `neg` | `vnegq_f16` | `fneg` | `(v) -> v` | — | v[j] = neg(x[j]) | requires Armv8.2 FP16 vector arithmetic; fma keeps the NEON accumulator-first order |
| `fma` | `vfmaq_f16` | `fmla` | `(a, b, c) -> v` | — | v[j] = a[j] + b[j]*c[j] | accumulator FIRST, like every NEON fma |
| `load` | `vld1q_f16` | `ld1` | `(p) -> v` | — | v[j] = p[j], 8 lanes |  |
| `store` | `vst1q_f16` | `st1` | `(p, v) -> void` | — | p[j] = v[j] |  |
| `broadcast` | `vdupq_n_f16` | `dup` | `(s) -> v` | — | v[j] = s |  |
| `select` | `vbslq_f16` | `bsl` | `(mask, t, f) -> v` | — | v[j] = mask[j] ? t[j] : f[j] | mask first, all-ones lanes pick t |

### i64 (integer lanes)

| op | spelling | mnemonic | signature | masked | semantics | note |
|---|---|---|---|---|---|---|
| `and` | `vandq_s64` | `and` | `(a, b) -> v` | — | v[j] = a[j] & b[j] |  |
| `or` | `vorrq_s64` | `orr` | `(a, b) -> v` | — | v[j] = a[j] \| b[j] |  |
| `shl` | `vshlq_s64` | `sshl` | `(a, counts) -> v` | — | v[j] = a[j] << counts[j] |  |
| `shr` | recipe: `vreinterpretq_s64_u64(vshlq_u64(vreinterpretq_u64_s64(a), vnegq_s64(counts)))` | `neg+ushl` | `(a, counts) -> v` | — | v[j] = a[j] >> counts[j], logical | vshlq shifts RIGHT for negative lane counts: negate the counts vector; only the low byte of each count is read |
| `land` | recipe: `uint64x2_t ones = vdupq_n_u64(~0ULL)`; `vreinterpretq_s64_u64(vandq_u64(veorq_u64(vceqzq_s64(a), ones), veorq_u64(vceqzq_s64(b), ones)))` | `cmeq+eor+and` | `(a, b) -> v` | — | v[j] = (a[j] != 0) && (b[j] != 0), all-ones/0 lanes | NEON has no vmvn on 64-bit lanes: complement with veorq against all-ones |
| `lor` | recipe: `vreinterpretq_s64_u64(veorq_u64(vandq_u64(vceqzq_s64(a), vceqzq_s64(b)), vdupq_n_u64(~0ULL)))` | `cmeq+and+eor` | `(a, b) -> v` | — | v[j] = (a[j] != 0) \|\| (b[j] != 0), all-ones/0 lanes |  |
| `mod` | recipe: `int64_t x[2], y[2]`; `vst1q_s64(x, a)`; `vst1q_s64(y, b)`; `for (int j = 0; j < 2; j++) x[j] = y[j] == 0 \|\| y[j] == -1 ? 0 : x[j] % y[j]`; `vld1q_s64(x)` | `sdiv+msub` | `(a, b) -> v` | — | v[j] = a[j] % b[j], truncated (sign of a) |  |
| `add` | `vaddq_s64` | `add` | `(a, b) -> v` | — | v[j] = a[j] + b[j], wrapping |  |
| `sub` | `vsubq_s64` | `sub` | `(a, b) -> v` | — | v[j] = a[j] - b[j], wrapping |  |
| `mul` | recipe: `uint64x2_t ua = vreinterpretq_u64_s64(a), ub = vreinterpretq_u64_s64(b)`; `uint32x2_t al = vmovn_u64(ua), bl = vmovn_u64(ub), ah = vshrn_n_u64(ua, 32), bh = vshrn_n_u64(ub, 32)`; `uint64x2_t cross = vaddq_u64(vmull_u32(al, bh), vmull_u32(ah, bl))`; `vreinterpretq_s64_u64(vmlal_u32(vshlq_n_u64(cross, 32), al, bl))` | `umull+umlal` | `(a, b) -> v` | — | v[j] = a[j] * b[j], low bits | no vmulq_s64: lo*lo + ((cross terms) << 32), or scalar per lane |
| `min` | recipe: `vbslq_s64(vcgtq_s64(a, b), b, a)` | `cmgt+bsl` | `(a, b) -> v` | — | v[j] = min(a[j], b[j]), signed |  |
| `max` | recipe: `vbslq_s64(vcgtq_s64(a, b), a, b)` | `cmgt+bsl` | `(a, b) -> v` | — | v[j] = max(a[j], b[j]), signed |  |
| `load` | `vld1q_s64` | `ldr` | `(p) -> v` | — | v[j] = p[j] |  |
| `store` | `vst1q_s64` | `str` | `(p, v)` | — | p[j] = v[j] |  |
| `broadcast` | `vdupq_n_s64` | `dup` | `(s) -> v` | — | v[j] = s |  |
| `lt` | `vcltq_s64` | `cmgt` | `(a, b) -> mask` | — | lane j true iff a[j] < b[j], signed |  |

### i32 (integer lanes)

| op | spelling | mnemonic | signature | masked | semantics | note |
|---|---|---|---|---|---|---|
| `and` | `vandq_s32` | `and` | `(a, b) -> v` | — | v[j] = a[j] & b[j] |  |
| `or` | `vorrq_s32` | `orr` | `(a, b) -> v` | — | v[j] = a[j] \| b[j] |  |
| `shl` | `vshlq_s32` | `sshl` | `(a, counts) -> v` | — | v[j] = a[j] << counts[j] |  |
| `shr` | recipe: `vreinterpretq_s32_u32(vshlq_u32(vreinterpretq_u32_s32(a), vnegq_s32(counts)))` | `neg+ushl` | `(a, counts) -> v` | — | v[j] = a[j] >> counts[j], logical | vshlq shifts RIGHT for negative lane counts: negate the counts vector; only the low byte of each count is read |
| `land` | recipe: `vreinterpretq_s32_u32(vandq_u32(vmvnq_u32(vceqzq_s32(a)), vmvnq_u32(vceqzq_s32(b))))` | `cmeq+mvn+and` | `(a, b) -> v` | — | v[j] = (a[j] != 0) && (b[j] != 0), all-ones/0 lanes |  |
| `lor` | recipe: `vreinterpretq_s32_u32(vmvnq_u32(vandq_u32(vceqzq_s32(a), vceqzq_s32(b))))` | `cmeq+and+mvn` | `(a, b) -> v` | — | v[j] = (a[j] != 0) \|\| (b[j] != 0), all-ones/0 lanes |  |
| `mod` | recipe: `int32_t x[4], y[4]`; `vst1q_s32(x, a)`; `vst1q_s32(y, b)`; `for (int j = 0; j < 4; j++) x[j] = y[j] == 0 \|\| y[j] == -1 ? 0 : x[j] % y[j]`; `vld1q_s32(x)` | `sdiv+msub` | `(a, b) -> v` | — | v[j] = a[j] % b[j], truncated (sign of a) |  |
| `add` | `vaddq_s32` | `add` | `(a, b) -> v` | — | v[j] = a[j] + b[j], wrapping |  |
| `sub` | `vsubq_s32` | `sub` | `(a, b) -> v` | — | v[j] = a[j] - b[j], wrapping |  |
| `mul` | `vmulq_s32` | `mul` | `(a, b) -> v` | — | v[j] = a[j] * b[j], low bits |  |
| `min` | `vminq_s32` | `smin` | `(a, b) -> v` | — | v[j] = min(a[j], b[j]), signed |  |
| `max` | `vmaxq_s32` | `smax` | `(a, b) -> v` | — | v[j] = max(a[j], b[j]), signed |  |
| `load` | `vld1q_s32` | `ldr` | `(p) -> v` | — | v[j] = p[j] |  |
| `store` | `vst1q_s32` | `str` | `(p, v)` | — | p[j] = v[j] |  |
| `broadcast` | `vdupq_n_s32` | `dup` | `(s) -> v` | — | v[j] = s |  |
| `lt` | `vcltq_s32` | `cmgt` | `(a, b) -> mask` | — | lane j true iff a[j] < b[j], signed |  |

## Hardware assists

| intrinsic | mnemonic | helps | note |
|---|---|---|---|
| `vrecpeq_f64` | `frecpe` | div | reciprocal estimate; refine with vrecpsq for a fast divide |
| `vrsqrteq_f64` | `frsqrte` | sqrt | rsqrt estimate; refine for a fast reciprocal square root |
| `vrecpsq_f64` | `frecps` | div | the Newton refinement step for vrecpeq |
| `vld2q_f64` | `ld2` | load | structure load: deinterleaves an AoS pair (vld3/vld4 for 3- and 4-wide) - the SoA idiom for stencil kernels |
