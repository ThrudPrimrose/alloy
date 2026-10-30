# neon — Arm NEON / AdvSIMD (fixed 128-bit)

Vector bytes: 16; lanes: f64: 2, f32: 4, f16: 8, i64: 2, i32: 4; no predication.

Legal schedules: scalar, scalar_remainder. gen_mask: unsupported (no predication).

- **scalar** (Scalar loop): No vectorization: one element per iteration, no tail handling. The baseline every speedup is measured against. Tail: none.
  - gcc: -fno-tree-vectorize
  - clang: #pragma clang loop vectorize(disable)
- **scalar_remainder** (Vector main loop + scalar remainder): The vectorizer's default shape on maskless ISAs: a full-width main loop while i + VL <= N, then a scalar loop for the last N mod VL elements (AVX2, NEON; AVX-512 may also use it instead of masking). Tail: scalar remainder loop after the vector main loop.
  - gcc: --param vect-partial-vector-usage=0 (epilogue vectorization off)
  - clang: #pragma clang loop vectorize_width(VL) interleave_count(k) (scalar epilogue on maskless ISAs)

AArch64 baseline (no -m flag). No predication: every tail is a remainder loop. NEON and SVE coexist on one core; gcc --param=aarch64-autovec-preference and clang -mllvm -scalable-vectorization=off gate which the auto-vectorizer prefers. fma availability: vfmaq_f64 (ACLE __ARM_FEATURE_FMA).

### f64

| op | spelling | mnemonic | signature | masked |
|---|---|---|---|---|
| `load` | `vld1q_f64` | `ld1` | `(p) -> v` | — |
| `store` | `vst1q_f64` | `st1` | `(p, v) -> void` | — |
| `broadcast` | `vdupq_n_f64` | `dup` | `(s) -> v` | — |
| `add` | `vaddq_f64` | `fadd` | `(a, b) -> v` | — |
| `sub` | `vsubq_f64` | `fsub` | `(a, b) -> v` | — |
| `mul` | `vmulq_f64` | `fmul` | `(a, b) -> v` | — |
| `div` | `vdivq_f64` | `fdiv` | `(a, b) -> v` | — |
| `fma` | `vfmaq_f64` | `fmla` | `(a, b, c) -> v` | — |
| `reduce_add` | recipe: vpaddq_f64 -> vgetq_lane_f64 | `faddp + fmov` | `(v) -> s` | — |
| `zero` | `vdupq_n_f64` | `movi` | `(0.0) -> v` | — |
| `exp` | 6 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — |
| `sin` | 5 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — |
| `cos` | 5 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — |
| `sqrt` | `vsqrtq_f64` | `fsqrt` | `(v) -> v` | — |
| `min` | `vminq_f64` | `fmin` | `(a, b) -> v` | — |
| `max` | `vmaxq_f64` | `fmax` | `(a, b) -> v` | — |
| `abs` | `vabsq_f64` | `fabs` | `(v) -> v` | — |
| `neg` | `vnegq_f64` | `fneg` | `(v) -> v` | — |
| `select` | `vbslq_f64` | `bsl` | `(mask, t, f) -> v` | — |
| `mod` | recipe: vdivq_f64 -> vrndq_f64 -> vfmsq_f64 | `fdiv+frintz+fmls` | `(a, b) -> v` | — |
| `gather` | recipe: per-lane scalar loads via vld1q_lane_f64(base + idx[j], v, j); keep indices affine to use vld1q instead | `ldr+ins` | `(base, idx) -> v` | — |
| `scatter` | recipe: per-lane scalar stores via vst1q_lane_f64(v, base + idx[j], j) | `str+ext` | `(base, idx, v) -> void` | — |

### f32

| op | spelling | mnemonic | signature | masked |
|---|---|---|---|---|
| `load` | `vld1q_f32` | `ld1` | `(p) -> v` | — |
| `store` | `vst1q_f32` | `st1` | `(p, v) -> void` | — |
| `broadcast` | `vdupq_n_f32` | `dup` | `(s) -> v` | — |
| `add` | `vaddq_f32` | `fadd` | `(a, b) -> v` | — |
| `sub` | `vsubq_f32` | `fsub` | `(a, b) -> v` | — |
| `mul` | `vmulq_f32` | `fmul` | `(a, b) -> v` | — |
| `div` | `vdivq_f32` | `fdiv` | `(a, b) -> v` | — |
| `fma` | `vfmaq_f32` | `fmla` | `(a, b, c) -> v` | — |
| `reduce_add` | `vaddvq_f32` | `faddp` | `(v) -> s` | — |
| `zero` | `vdupq_n_f32` | `movi` | `(0.0f) -> v` | — |
| `exp` | 6 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — |
| `sin` | 5 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — |
| `cos` | 5 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — |
| `sqrt` | `vsqrtq_f32` | `fsqrt` | `(v) -> v` | — |
| `min` | `vminq_f32` | `fmin` | `(a, b) -> v` | — |
| `max` | `vmaxq_f32` | `fmax` | `(a, b) -> v` | — |
| `abs` | `vabsq_f32` | `fabs` | `(v) -> v` | — |
| `neg` | `vnegq_f32` | `fneg` | `(v) -> v` | — |
| `select` | `vbslq_f32` | `bsl` | `(mask, t, f) -> v` | — |
| `mod` | recipe: vdivq_f32 -> vrndq_f32 -> vfmsq_f32 | `fdiv+frintz+fmls` | `(a, b) -> v` | — |
| `gather` | recipe: per-lane scalar loads via vld1q_lane_f32(base + idx[j], v, j); keep indices affine to use vld1q instead | `ldr+ins` | `(base, idx) -> v` | — |
| `scatter` | recipe: per-lane scalar stores via vst1q_lane_f32(v, base + idx[j], j) | `str+ext` | `(base, idx, v) -> void` | — |

### f16

| op | spelling | mnemonic | signature | masked |
|---|---|---|---|---|
| `add` | `vaddq_f16` | `fadd` | `(a, b) -> v` | — |
| `sub` | `vsubq_f16` | `fsub` | `(a, b) -> v` | — |
| `mul` | `vmulq_f16` | `fmul` | `(a, b) -> v` | — |
| `div` | `vdivq_f16` | `fdiv` | `(a, b) -> v` | — |
| `sqrt` | `vsqrtq_f16` | `fsqrt` | `(v) -> v` | — |
| `min` | `vminq_f16` | `fmin` | `(a, b) -> v` | — |
| `max` | `vmaxq_f16` | `fmax` | `(a, b) -> v` | — |
| `abs` | `vabsq_f16` | `fabs` | `(v) -> v` | — |
| `neg` | `vnegq_f16` | `fneg` | `(v) -> v` | — |
| `fma` | `vfmaq_f16` | `fmla` | `(a, b, c) -> v` | — |
| `load` | `vld1q_f16` | `ld1` | `(p) -> v` | — |
| `store` | `vst1q_f16` | `st1` | `(p, v) -> void` | — |
| `broadcast` | `vdupq_n_f16` | `dup` | `(s) -> v` | — |
| `select` | `vbslq_f16` | `bsl` | `(mask, t, f) -> v` | — |

### i64 (integer lanes)

| op | spelling | mnemonic | signature | masked |
|---|---|---|---|---|
| `and` | `vandq_u64` | `and` | `(a, b) -> v` | — |
| `or` | `vorrq_u64` | `orr` | `(a, b) -> v` | — |
| `shl` | `vshlq_u64` | `ushl` | `(a, counts) -> v` | — |
| `shr` | `vshlq_u64` | `ushl` | `(a, counts) -> v` | — |
| `land` | recipe: vceqzq_u64 -> veorq_u64 -> vandq_u64 | `cmeqz+eor+and` | `(a, b) -> v` | — |
| `lor` | recipe: vceqzq_u64 -> vandq_u64 -> veorq_u64 | `cmeqz+and+eor` | `(a, b) -> v` | — |
| `mod` | recipe: no vector remainder: divide scalar per lane, or double division while |a| < 2^53 -> r = a - q * b | `sdiv+mul` | `(a, b) -> v` | — |

### i32 (integer lanes)

| op | spelling | mnemonic | signature | masked |
|---|---|---|---|---|
| `and` | `vandq_u32` | `and` | `(a, b) -> v` | — |
| `or` | `vorrq_u32` | `orr` | `(a, b) -> v` | — |
| `shl` | `vshlq_u32` | `ushl` | `(a, counts) -> v` | — |
| `shr` | `vshlq_u32` | `ushl` | `(a, counts) -> v` | — |
| `land` | recipe: vceqzq_u32 -> vmvnq_u32 -> vandq_u32 | `cmeqz+mvn+and` | `(a, b) -> v` | — |
| `lor` | recipe: vceqzq_u32 -> vandq_u32 -> vmvnq_u32 | `cmeqz+and+mvn` | `(a, b) -> v` | — |
| `mod` | recipe: no vector remainder: divide scalar per lane, or double division while |a| < 2^53 -> r = a - q * b | `sdiv+mul` | `(a, b) -> v` | — |

## Hardware assists

| intrinsic | mnemonic | helps | note |
|---|---|---|---|
| `vrecpeq_f64` | `frecpe` | div | reciprocal estimate; refine with vrecpsq for a fast divide |
| `vrsqrteq_f64` | `frsqrte` | sqrt | rsqrt estimate; refine for a fast reciprocal square root |
| `vrecpsq_f64` | `frecps` | div | the Newton refinement step for vrecpeq |
| `vld2q_f64` | `ld2` | load | structure load: deinterleaves an AoS pair (vld3/vld4 for 3- and 4-wide) - the SoA idiom for stencil kernels |

## Traps

- **fma** (f64): operand-order trap: the accumulator is FIRST, the products last (a + b*c) — the opposite of Intel's fmadd
- **fma** (f32): operand-order trap: the accumulator is FIRST, the products last (a + b*c) — the opposite of Intel's fmadd
