# sve — Arm SVE (scalable vectors, predicated)

Vector bytes: length-agnostic; lanes: f64: runtime, f32: runtime, f16: runtime, i64: runtime, i32: runtime; opmask/predicate.

Legal schedules: scalar, sve_intrinsics. gen_mask: svwhilelt_b{64,32}_u64(i, N).

Scalable: the vector length is fixed at reset (128..2048 bits, 128-bit steps) and known only at runtime via svcntd()/svcntw() — lanes 0 here mean 'runtime length'. Everything is predicated: every op takes a leading svbool_t pg plus an activity-policy suffix _x (don't-care, fastest), _z (inactive lanes zeroed), _m (inactive lanes from a source operand). The predicate subsumes every tail schedule: no remainder loop. Host flag: -march=armv8-a+sve.

### f64

| op | spelling | mnemonic | signature | masked |
|---|---|---|---|---|
| `load` | `svld1_f64` | `ld1d` | `(pg, p) -> v` | — |
| `store` | `svst1_f64` | `st1d` | `(pg, p, v) -> void` | — |
| `broadcast` | `svdup_f64` | `dup` | `(s) -> v` | — |
| `add` | `svadd_f64_x` | `fadd` | `(pg, a, b) -> v` | — |
| `sub` | `svsub_f64_x` | `fsub` | `(pg, a, b) -> v` | — |
| `mul` | `svmul_f64_x` | `fmul` | `(pg, a, b) -> v` | — |
| `div` | `svdiv_f64_x` | `fdiv` | `(pg, a, b) -> v` | — |
| `fma` | `svmla_f64_x` | `fmla` | `(pg, add, m1, m2) -> v` | — |
| `reduce_add` | `svaddv_f64` | `addv` | `(pg, v) -> s` | — |
| `zero` | `svdup_f64` | `mov` | `(0.0) -> v` | — |
| `gen_mask` | `svwhilelt_b64_u64` | `whilelt` | `(i, N) -> pg` | — |
| `exp` | 6 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — |
| `sin` | 5 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — |
| `cos` | 5 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — |
| `sqrt` | `svsqrt_f64_x` | `fsqrt` | `(pg, v) -> v` | — |
| `min` | `svmin_f64_x` | `fmin` | `(pg, a, b) -> v` | — |
| `max` | `svmax_f64_x` | `fmax` | `(pg, a, b) -> v` | — |
| `abs` | `svabs_f64_x` | `fabs` | `(pg, v) -> v` | — |
| `neg` | `svneg_f64_x` | `fneg` | `(pg, v) -> v` | — |
| `select` | `svsel_f64` | `sel` | `(pg, t, f) -> v` | — |
| `mod` | recipe: svdiv_f64_x -> svcvt_s64_f64_x -> svcvt_f64_s64_x | `fdiv+fcvt` | `(pg, a, b) -> v` | — |
| `gather` | `svld1_gather_s64index_f64` | `ld1d (gather)` | `(pg, base, idx) -> v` | — |
| `scatter` | `svst1_scatter_u64index_f64` | `st1d (scatter)` | `(pg, base, idx, v) -> void` | — |

### f32

| op | spelling | mnemonic | signature | masked |
|---|---|---|---|---|
| `load` | `svld1_f32` | `ld1w` | `(pg, p) -> v` | — |
| `store` | `svst1_f32` | `st1w` | `(pg, p, v) -> void` | — |
| `broadcast` | `svdup_f32` | `dup` | `(s) -> v` | — |
| `add` | `svadd_f32_x` | `fadd` | `(pg, a, b) -> v` | — |
| `sub` | `svsub_f32_x` | `fsub` | `(pg, a, b) -> v` | — |
| `mul` | `svmul_f32_x` | `fmul` | `(pg, a, b) -> v` | — |
| `div` | `svdiv_f32_x` | `fdiv` | `(pg, a, b) -> v` | — |
| `fma` | `svmla_f32_x` | `fmla` | `(pg, add, m1, m2) -> v` | — |
| `reduce_add` | `svaddv_f32` | `addv` | `(pg, v) -> s` | — |
| `zero` | `svdup_f32` | `mov` | `(0.0f) -> v` | — |
| `gen_mask` | `svwhilelt_b32_u64` | `whilelt` | `(i, N) -> pg` | — |
| `exp` | 6 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — |
| `sin` | 5 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — |
| `cos` | 5 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — |
| `sqrt` | `svsqrt_f32_x` | `fsqrt` | `(pg, v) -> v` | — |
| `min` | `svmin_f32_x` | `fmin` | `(pg, a, b) -> v` | — |
| `max` | `svmax_f32_x` | `fmax` | `(pg, a, b) -> v` | — |
| `abs` | `svabs_f32_x` | `fabs` | `(pg, v) -> v` | — |
| `neg` | `svneg_f32_x` | `fneg` | `(pg, v) -> v` | — |
| `select` | `svsel_f32` | `sel` | `(pg, t, f) -> v` | — |
| `mod` | recipe: svdiv_f32_x -> svcvt_s32_f32_x -> svcvt_f32_s32_x | `fdiv+fcvt` | `(pg, a, b) -> v` | — |
| `gather` | `svld1_gather_s32index_f32` | `ld1w (gather)` | `(pg, base, idx) -> v` | — |
| `scatter` | `svst1_scatter_u32index_f32` | `st1w (scatter)` | `(pg, base, idx, v) -> void` | — |

### f16

| op | spelling | mnemonic | signature | masked |
|---|---|---|---|---|
| `add` | `svadd_f16_x` | `add` | `(pg, a, b) -> v` | — |
| `sub` | `svsub_f16_x` | `sub` | `(pg, a, b) -> v` | — |
| `mul` | `svmul_f16_x` | `mul` | `(pg, a, b) -> v` | — |
| `div` | `svdiv_f16_x` | `div` | `(pg, a, b) -> v` | — |
| `fma` | `svmla_f16_x` | `fmla` | `(pg, add, m1, m2) -> v` | — |
| `sqrt` | `svsqrt_f16_x` | `fsqrt` | `(pg, v) -> v` | — |
| `min` | `svmin_f16_x` | `fmin` | `(pg, a, b) -> v` | — |
| `max` | `svmax_f16_x` | `fmax` | `(pg, a, b) -> v` | — |
| `abs` | `svabs_f16_x` | `fabs` | `(pg, v) -> v` | — |
| `neg` | `svneg_f16_x` | `fneg` | `(pg, v) -> v` | — |
| `load` | `svld1_f16` | `ld1h` | `(pg, p) -> v` | — |
| `store` | `svst1_f16` | `st1h` | `(pg, p, v) -> void` | — |
| `broadcast` | `svdup_f16` | `dup` | `(s) -> v` | — |
| `select` | `svsel_f16` | `sel` | `(pg, t, f) -> v` | — |

### i64 (integer lanes)

| op | spelling | mnemonic | signature | masked |
|---|---|---|---|---|
| `and` | `svand_u64_x` | `and` | `(pg, a, b) -> v` | — |
| `or` | `svorr_u64_x` | `orr` | `(pg, a, b) -> v` | — |
| `shl` | `svlsl_u64_x` | `lsl` | `(pg, a, counts) -> v` | — |
| `shr` | `svlsr_u64_x` | `lsr` | `(pg, a, counts) -> v` | — |
| `land` | recipe: svcmpne_u64 -> svand_b_z | `cmpne+and_b` | `(pg, a, b) -> pg` | — |
| `lor` | recipe: svcmpne_u64 -> svorr_b_z | `cmpne+orr_b` | `(pg, a, b) -> pg` | — |
| `mod` | recipe: no vector remainder: divide scalar per lane, or double division while |a| < 2^53 -> r = a - q * b | `sdiv+mul` | `(a, b) -> v` | — |

### i32 (integer lanes)

| op | spelling | mnemonic | signature | masked |
|---|---|---|---|---|
| `and` | `svand_u32_x` | `and` | `(pg, a, b) -> v` | — |
| `or` | `svorr_u32_x` | `orr` | `(pg, a, b) -> v` | — |
| `shl` | `svlsl_u32_x` | `lsl` | `(pg, a, counts) -> v` | — |
| `shr` | `svlsr_u32_x` | `lsr` | `(pg, a, counts) -> v` | — |
| `land` | recipe: svcmpne_u32 -> svand_b_z | `cmpne+and_b` | `(pg, a, b) -> pg` | — |
| `lor` | recipe: svcmpne_u32 -> svorr_b_z | `cmpne+orr_b` | `(pg, a, b) -> pg` | — |
| `mod` | recipe: no vector remainder: divide scalar per lane, or double division while |a| < 2^53 -> r = a - q * b | `sdiv+mul` | `(a, b) -> v` | — |

## Traps

- **fma** (f64): operand-order trap: the accumulator is FIRST (add + m1*m2), like NEON — differs from Intel's fmadd
- **fma** (f32): operand-order trap: the accumulator is FIRST (add + m1*m2), like NEON — differs from Intel's fmadd

