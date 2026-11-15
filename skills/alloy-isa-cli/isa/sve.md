# sve — Arm SVE (scalable vectors, predicated)

Vector bytes: length-agnostic; lanes: f64: runtime, f32: runtime, f16: runtime, i64: runtime, i32: runtime; opmask/predicate.

Legal schedules: scalar, scalar_remainder, masked_remainder, full_mask, sve_intrinsics. gen_mask: svwhilelt_b{64,32,16}_s64(i, N).

- **scalar** (Scalar loop): No vectorization: one element per iteration, no tail handling. The baseline every speedup is measured against. Tail: none.
  - gcc: -fno-tree-vectorize
  - clang: #pragma clang loop vectorize(disable)
- **scalar_remainder** (Vector main loop + scalar remainder): The vectorizer's default shape on maskless ISAs: a full-width main loop while i + VL <= N, then a scalar loop for the last N mod VL elements (AVX2, NEON; AVX-512 may also use it instead of masking). Tail: scalar remainder loop after the vector main loop.
  - gcc: --param vect-partial-vector-usage=0 --param vect-epilogues-nomask=0
  - clang: #pragma clang loop vectorize_width(VL) interleave_count(k) (scalar epilogue on maskless ISAs)
- **masked_remainder** (Unmasked main loop + masked epilogue): AVX-512 shape: the main loop runs unmasked while a whole vector fits; only the final partial iteration is predicated (AVX-512: opmask epilogue; the compiler emits it from vect-partial-vector-usage). Tail: masked epilogue (opmask or predicate) after the unmasked main loop.
  - gcc: --param vect-partial-vector-usage=1 (masked epilogue, AVX-512 hosts)
  - clang: no masked epilogue: use full_mask on AVX-512 or scalar_remainder elsewhere
- **full_mask** (Every iteration masked): AVX-512 shape: a single loop where every iteration applies its opmask (prefer-predicate-over-epilogue); no separate epilogue at all. Costs a mask per iteration in the main loop. Tail: every iteration predicated, no epilogue.
  - gcc: --param vect-partial-vector-usage=2 (masked loop body)
  - clang: -mllvm -prefer-predicate-over-epilogue=predicate-dont-vectorize
- **sve_intrinsics** (Explicit predicated SVE loops): SVE shape rendered by DaCe's SVEVectorization (the sve_intrinsics tail): the loop steps by svcntd()/svcntw() and svwhilelt builds the tail predicate every iteration, so there is no remainder loop at all. Loop predicates are named __pg_{param}. Tail: predicate every iteration (svwhilelt), runtime vector length, no remainder.
  - gcc: -fopenmp-simd -march=armv8-a+sve with #pragma omp simd (auto SVE), or explicit intrinsics via this skeleton
  - clang: -march=armv8-a+sve -mllvm -prefer-predicate-over-epilogue=predicate-dont-vectorize, or DaCe SVEVectorization (this skeleton)

Scalable: the vector length is fixed at reset (128..2048 bits, 128-bit steps) and known only at runtime via svcntd()/svcntw() — lanes 0 here mean 'runtime length'. Everything is predicated: every op takes a leading svbool_t pg plus an activity-policy suffix _x (don't-care, fastest), _z (inactive lanes zeroed), _m (inactive lanes from a source operand). The predicate subsumes every tail schedule: no remainder loop. Host flag: -march=armv8-a+sve.

### f64

| op | spelling | mnemonic | signature | masked | semantics | note |
|---|---|---|---|---|---|---|
| `load` | `svld1_f64` | `ld1d` | `(pg, p) -> v` | — | v[j] = p[j] for active lanes j |  |
| `store` | `svst1_f64` | `st1d` | `(pg, p, v) -> void` | — | p[j] = v[j] for active lanes j |  |
| `broadcast` | `svdup_f64` | `dup` | `(s) -> v` | — | v[j] = s for every lane j |  |
| `add` | `svadd_f64_x` | `fadd` | `(pg, a, b) -> v` | — | v[j] = a[j] + b[j] for active lanes j | _x policy: inactive lanes are unspecified; use _z to zero them, _m to merge |
| `sub` | `svsub_f64_x` | `fsub` | `(pg, a, b) -> v` | — | v[j] = a[j] - b[j] for active lanes j |  |
| `mul` | `svmul_f64_x` | `fmul` | `(pg, a, b) -> v` | — | v[j] = a[j] * b[j] for active lanes j |  |
| `div` | `svdiv_f64_x` | `fdiv` | `(pg, a, b) -> v` | — | v[j] = a[j] / b[j] for active lanes j |  |
| `fma` | `svmla_f64_x` | `fmla` | `(pg, add, m1, m2) -> v` | — | v[j] = add[j] + m1[j]*m2[j] for active lanes j | operand-order trap: the accumulator is FIRST (add + m1*m2), like NEON — differs from Intel's fmadd; a loop-carried accumulator under a tail predicate needs the _m form: _x leaves inactive lanes unspecified |
| `reduce_add` | `svaddv_f64` | `faddv` | `(pg, v) -> s` | — | s = sum of the active lanes of v | cleanest horizontal add of all targets |
| `zero` | `svdup_f64` | `mov` | `(0.0) -> v` | — | v[j] = 0.0 for every lane j |  |
| `gen_mask` | `svwhilelt_b64_s64` | `whilelt` | `(i, N) -> pg` | — | lane j active iff i + j < N | the standardized gen_mask; the loop steps by svcntd() and never needs a remainder loop |
| `exp` | 6 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — | v[j] = exp(v[j]) | no native transcendental instruction, but SVE has the best exp assist: SVEXPA (ACLE SVE 6.16.30, svexpa_f64(svuint64)) returns 2^(I/64) with the exponent field replaced - the hardware 2^(j/64) table of the sub-1-ulp route: input (k + 1023)*64 + j, SVEXPA yields 2^k*2^(j/64) and a short polynomial finishes; SVSCALE_F64_X does ldexp-style scaling, SVLOGB (SVE2) extracts exponents, SVRECPE/SVRSQRTE give estimates refined by SVRECPS; SLEEF also ships SVE implementations - check the installed sleef.h for the exact spelling; split x = k*ln2 + r first (k = round(x/ln2)); the polynomial approximates exp(r) and the result scales by 2^k - a plain ln2 split loses accuracy for \|x\| > ~10, hi/lo ln2 constants fix that |
| `sin` | 5 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — | v[j] = sin(v[j]) | no native transcendental instruction, but SVE has the best exp assist: SVEXPA (ACLE SVE 6.16.30, svexpa_f64(svuint64)) returns 2^(I/64) with the exponent field replaced - the hardware 2^(j/64) table of the sub-1-ulp route: input (k + 1023)*64 + j, SVEXPA yields 2^k*2^(j/64) and a short polynomial finishes; SVSCALE_F64_X does ldexp-style scaling, SVLOGB (SVE2) extracts exponents, SVRECPE/SVRSQRTE give estimates refined by SVRECPS; SLEEF also ships SVE implementations - check the installed sleef.h for the exact spelling; range reduction dominates accuracy: the tiers assume x already reduced; without hi/lo pi/2 constants the reduction error exceeds the polynomial error for \|x\| beyond a few pi |
| `cos` | 5 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — | v[j] = cos(v[j]) | no native transcendental instruction, but SVE has the best exp assist: SVEXPA (ACLE SVE 6.16.30, svexpa_f64(svuint64)) returns 2^(I/64) with the exponent field replaced - the hardware 2^(j/64) table of the sub-1-ulp route: input (k + 1023)*64 + j, SVEXPA yields 2^k*2^(j/64) and a short polynomial finishes; SVSCALE_F64_X does ldexp-style scaling, SVLOGB (SVE2) extracts exponents, SVRECPE/SVRSQRTE give estimates refined by SVRECPS; SLEEF also ships SVE implementations - check the installed sleef.h for the exact spelling; range reduction dominates accuracy: the tiers assume x already reduced; without hi/lo pi/2 constants the reduction error exceeds the polynomial error for \|x\| beyond a few pi |
| `sqrt` | `svsqrt_f64_x` | `fsqrt` | `(pg, v) -> v` | — | v[j] = sqrt(x[j]) for active lanes |  |
| `min` | `svmin_f64_x` | `fmin` | `(pg, a, b) -> v` | — | v[j] = min(a[j], b[j]) for active lanes | svmin propagates NaN; svminnm_f64_x is the IEEE minNum form |
| `max` | `svmax_f64_x` | `fmax` | `(pg, a, b) -> v` | — | v[j] = max(a[j], b[j]) for active lanes |  |
| `abs` | `svabs_f64_x` | `fabs` | `(pg, v) -> v` | — | v[j] = \|x[j]\| for active lanes | native, unlike x86 |
| `neg` | `svneg_f64_x` | `fneg` | `(pg, v) -> v` | — | v[j] = -x[j] for active lanes | native, unlike x86 |
| `select` | `svsel_f64` | `sel` | `(pg, t, f) -> v` | — | v[j] = pg[j] ? t[j] : f[j] | predicate FIRST; no activity suffix - SEL is not predicated on a second predicate |
| `mod` | recipe: `svfloat64_t q = svrintz_f64_x(pg, svdiv_f64_x(pg, a, b))`; `svmls_f64_x(pg, a, q, b)` | `fdiv+frintz+fmls` | `(pg, a, b) -> v` | — | v[j] = a[j] - trunc(a[j]/b[j])*b[j]: fmod only for finite b and \|a/b\| below 2^p | no fmod: q = svrintz(a/b) (frintz, toward zero), r = svmls(a, q, b) = a - q*b. The kernel of fmod is exact on every input (`kernel ISA fmod DTYPE`); this recipe holds only for finite b and \|a/b\| < 2^52 (f32: 2^23): a/b rounds, so correct with r += copysign(b, a) when sign(r) != sign(a), copysign the zero result, and call scalar fmod outside that domain |
| `gather` | `svld1_gather_s64index_f64` | `ld1d (gather)` | `(pg, base, idx) -> v` | — | v[j] = base[idx[j]] for active lanes | first-faulting svldff1_gather_... variants exist for speculative access |
| `scatter` | `svst1_scatter_s64index_f64` | `st1d (scatter)` | `(pg, base, idx, v) -> void` | — | base[idx[j]] = v[j] for active lanes |  |
| `lt` | `svcmplt_f64` | `fcmgt` | `(pg, a, b) -> mask` | — | lane j true iff a[j] < b[j]; false on NaN | a predicate |

### f32

| op | spelling | mnemonic | signature | masked | semantics | note |
|---|---|---|---|---|---|---|
| `load` | `svld1_f32` | `ld1w` | `(pg, p) -> v` | — | v[j] = p[j] for active lanes j |  |
| `store` | `svst1_f32` | `st1w` | `(pg, p, v) -> void` | — | p[j] = v[j] for active lanes j |  |
| `broadcast` | `svdup_f32` | `dup` | `(s) -> v` | — | v[j] = s for every lane j |  |
| `add` | `svadd_f32_x` | `fadd` | `(pg, a, b) -> v` | — | v[j] = a[j] + b[j] for active lanes j | _x policy: inactive lanes are unspecified; use _z to zero them, _m to merge |
| `sub` | `svsub_f32_x` | `fsub` | `(pg, a, b) -> v` | — | v[j] = a[j] - b[j] for active lanes j |  |
| `mul` | `svmul_f32_x` | `fmul` | `(pg, a, b) -> v` | — | v[j] = a[j] * b[j] for active lanes j |  |
| `div` | `svdiv_f32_x` | `fdiv` | `(pg, a, b) -> v` | — | v[j] = a[j] / b[j] for active lanes j |  |
| `fma` | `svmla_f32_x` | `fmla` | `(pg, add, m1, m2) -> v` | — | v[j] = add[j] + m1[j]*m2[j] for active lanes j | operand-order trap: the accumulator is FIRST (add + m1*m2), like NEON — differs from Intel's fmadd; a loop-carried accumulator under a tail predicate needs the _m form: _x leaves inactive lanes unspecified |
| `reduce_add` | `svaddv_f32` | `faddv` | `(pg, v) -> s` | — | s = sum of the active lanes of v |  |
| `zero` | `svdup_f32` | `mov` | `(0.0f) -> v` | — | v[j] = 0.0f for every lane j |  |
| `gen_mask` | `svwhilelt_b32_s64` | `whilelt` | `(i, N) -> pg` | — | lane j active iff i + j < N | the standardized gen_mask; the loop steps by svcntw() and never needs a remainder loop |
| `exp` | 6 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — | v[j] = exp(v[j]) | no native transcendental instruction, but SVE has the best exp assist: SVEXPA (ACLE SVE 6.16.30, svexpa_f32(svuint32)) returns 2^(I/64) with the exponent field replaced - the hardware 2^(j/64) table of the sub-1-ulp route: input (k + 127)*64 + j, SVEXPA yields 2^k*2^(j/64) and a short polynomial finishes; svscale_f32_x does ldexp-style scaling, SVLOGB (SVE2) extracts exponents, SVRECPE/SVRSQRTE give estimates refined by SVRECPS; SLEEF also ships SVE implementations - check the installed sleef.h for the exact spelling; split x = k*ln2 + r first (k = round(x/ln2)); the polynomial approximates exp(r) and the result scales by 2^k - a plain ln2 split loses accuracy for \|x\| > ~10, hi/lo ln2 constants fix that |
| `sin` | 5 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — | v[j] = sin(v[j]) | no native transcendental instruction, but SVE has the best exp assist: SVEXPA (ACLE SVE 6.16.30, svexpa_f32(svuint32)) returns 2^(I/64) with the exponent field replaced - the hardware 2^(j/64) table of the sub-1-ulp route: input (k + 127)*64 + j, SVEXPA yields 2^k*2^(j/64) and a short polynomial finishes; svscale_f32_x does ldexp-style scaling, SVLOGB (SVE2) extracts exponents, SVRECPE/SVRSQRTE give estimates refined by SVRECPS; SLEEF also ships SVE implementations - check the installed sleef.h for the exact spelling; range reduction dominates accuracy: the tiers assume x already reduced; without hi/lo pi/2 constants the reduction error exceeds the polynomial error for \|x\| beyond a few pi |
| `cos` | 5 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — | v[j] = cos(v[j]) | no native transcendental instruction, but SVE has the best exp assist: SVEXPA (ACLE SVE 6.16.30, svexpa_f32(svuint32)) returns 2^(I/64) with the exponent field replaced - the hardware 2^(j/64) table of the sub-1-ulp route: input (k + 127)*64 + j, SVEXPA yields 2^k*2^(j/64) and a short polynomial finishes; svscale_f32_x does ldexp-style scaling, SVLOGB (SVE2) extracts exponents, SVRECPE/SVRSQRTE give estimates refined by SVRECPS; SLEEF also ships SVE implementations - check the installed sleef.h for the exact spelling; range reduction dominates accuracy: the tiers assume x already reduced; without hi/lo pi/2 constants the reduction error exceeds the polynomial error for \|x\| beyond a few pi |
| `sqrt` | `svsqrt_f32_x` | `fsqrt` | `(pg, v) -> v` | — | v[j] = sqrt(x[j]) for active lanes |  |
| `min` | `svmin_f32_x` | `fmin` | `(pg, a, b) -> v` | — | v[j] = min(a[j], b[j]) for active lanes | svmin propagates NaN; svminnm_f32_x is the IEEE minNum form |
| `max` | `svmax_f32_x` | `fmax` | `(pg, a, b) -> v` | — | v[j] = max(a[j], b[j]) for active lanes |  |
| `abs` | `svabs_f32_x` | `fabs` | `(pg, v) -> v` | — | v[j] = \|x[j]\| for active lanes | native, unlike x86 |
| `neg` | `svneg_f32_x` | `fneg` | `(pg, v) -> v` | — | v[j] = -x[j] for active lanes | native, unlike x86 |
| `select` | `svsel_f32` | `sel` | `(pg, t, f) -> v` | — | v[j] = pg[j] ? t[j] : f[j] | predicate FIRST; no activity suffix - SEL is not predicated on a second predicate |
| `mod` | recipe: `svfloat32_t q = svrintz_f32_x(pg, svdiv_f32_x(pg, a, b))`; `svmls_f32_x(pg, a, q, b)` | `fdiv+frintz+fmls` | `(pg, a, b) -> v` | — | v[j] = a[j] - trunc(a[j]/b[j])*b[j]: fmod only for finite b and \|a/b\| below 2^p | no fmod: q = svrintz(a/b) (frintz, toward zero), r = svmls(a, q, b) = a - q*b. The kernel of fmod is exact on every input (`kernel ISA fmod DTYPE`); this recipe holds only for finite b and \|a/b\| < 2^52 (f32: 2^23): a/b rounds, so correct with r += copysign(b, a) when sign(r) != sign(a), copysign the zero result, and call scalar fmod outside that domain |
| `gather` | `svld1_gather_s32index_f32` | `ld1w (gather)` | `(pg, base, idx) -> v` | — | v[j] = base[idx[j]] for active lanes | first-faulting svldff1_gather_... variants exist for speculative access |
| `scatter` | `svst1_scatter_s32index_f32` | `st1w (scatter)` | `(pg, base, idx, v) -> void` | — | base[idx[j]] = v[j] for active lanes |  |
| `lt` | `svcmplt_f32` | `fcmgt` | `(pg, a, b) -> mask` | — | lane j true iff a[j] < b[j]; false on NaN | a predicate |

### f16

| op | spelling | mnemonic | signature | masked | semantics | note |
|---|---|---|---|---|---|---|
| `add` | `svadd_f16_x` | `fadd` | `(pg, a, b) -> v` | — | v[j] = a[j] + b[j] for active lanes |  |
| `sub` | `svsub_f16_x` | `fsub` | `(pg, a, b) -> v` | — | v[j] = a[j] - b[j] for active lanes |  |
| `mul` | `svmul_f16_x` | `fmul` | `(pg, a, b) -> v` | — | v[j] = a[j] * b[j] for active lanes |  |
| `div` | `svdiv_f16_x` | `fdiv` | `(pg, a, b) -> v` | — | v[j] = a[j] / b[j] for active lanes |  |
| `gen_mask` | `svwhilelt_b16_s64` | `whilelt` | `(i, N) -> pg` | — | lane j active iff i + j < N | the standardized gen_mask; the loop steps by svcnth() and never needs a remainder loop |
| `fma` | `svmla_f16_x` | `fmla` | `(pg, add, m1, m2) -> v` | — | v[j] = add[j] + m1[j]*m2[j] | accumulator FIRST, like every SVE fma |
| `sqrt` | `svsqrt_f16_x` | `fsqrt` | `(pg, v) -> v` | — | v[j] = sqrt(x[j]) |  |
| `min` | `svmin_f16_x` | `fmin` | `(pg, a, b) -> v` | — | v[j] = min(a[j], b[j]) |  |
| `max` | `svmax_f16_x` | `fmax` | `(pg, a, b) -> v` | — | v[j] = max(a[j], b[j]) |  |
| `abs` | `svabs_f16_x` | `fabs` | `(pg, v) -> v` | — | v[j] = \|x[j]\| |  |
| `neg` | `svneg_f16_x` | `fneg` | `(pg, v) -> v` | — | v[j] = -x[j] |  |
| `load` | `svld1_f16` | `ld1h` | `(pg, p) -> v` | — | v[j] = p[j] for active lanes |  |
| `store` | `svst1_f16` | `st1h` | `(pg, p, v) -> void` | — | p[j] = v[j] for active lanes |  |
| `broadcast` | `svdup_f16` | `dup` | `(s) -> v` | — | v[j] = s |  |
| `select` | `svsel_f16` | `sel` | `(pg, t, f) -> v` | — | v[j] = pg[j] ? t[j] : f[j] |  |

### i64 (integer lanes)

| op | spelling | mnemonic | signature | masked | semantics | note |
|---|---|---|---|---|---|---|
| `and` | `svand_s64_x` | `and` | `(pg, a, b) -> v` | — | v[j] = a[j] & b[j] for active lanes |  |
| `or` | `svorr_s64_x` | `orr` | `(pg, a, b) -> v` | — | v[j] = a[j] \| b[j] for active lanes |  |
| `shl` | recipe: `svreinterpret_s64_u64(svlsl_u64_x(pg, svreinterpret_u64_s64(a), svreinterpret_u64_s64(counts)))` | `lsl` | `(pg, a, counts) -> v` | — | v[j] = a[j] << counts[j] for active lanes |  |
| `shr` | recipe: `svreinterpret_s64_u64(svlsr_u64_x(pg, svreinterpret_u64_s64(a), svreinterpret_u64_s64(counts)))` | `lsr` | `(pg, a, counts) -> v` | — | v[j] = a[j] >> counts[j], logical, for active lanes |  |
| `land` | recipe: `svand_b_z(pg, svcmpne_s64(pg, a, svdup_s64(0)), svcmpne_s64(pg, b, svdup_s64(0)))` | `cmpne+and` | `(pg, a, b) -> pg` | — | lane j active iff (a[j] != 0) && (b[j] != 0) | yields a predicate; svsel turns it into 0/1 lanes |
| `lor` | recipe: `svorr_b_z(pg, svcmpne_s64(pg, a, svdup_s64(0)), svcmpne_s64(pg, b, svdup_s64(0)))` | `cmpne+orr` | `(pg, a, b) -> pg` | — | lane j active iff (a[j] != 0) \|\| (b[j] != 0) |  |
| `mod` | recipe: `svint64_t q = svdiv_s64_x(pg, a, b)`; `svsel_s64(svcmpeq_n_s64(pg, b, 0), svdup_s64(0), svmls_s64_x(pg, a, q, b))` | `sdiv+mls` | `(pg, a, b) -> v` | — | v[j] = a[j] % b[j], truncated (sign of a) | q = svdiv(pg, a, b), r = svmls(pg, a, q, b); SDIV gives 0 for b == 0, so r would be a: select 0 there like the other targets; no trap on INT_MIN / -1 |
| `add` | `svadd_s64_x` | `add` | `(pg, a, b) -> v` | — | v[j] = a[j] + b[j], wrapping |  |
| `sub` | `svsub_s64_x` | `sub` | `(pg, a, b) -> v` | — | v[j] = a[j] - b[j], wrapping |  |
| `mul` | `svmul_s64_x` | `mul` | `(pg, a, b) -> v` | — | v[j] = a[j] * b[j], low bits |  |
| `min` | `svmin_s64_x` | `smin` | `(pg, a, b) -> v` | — | v[j] = min(a[j], b[j]), signed |  |
| `max` | `svmax_s64_x` | `smax` | `(pg, a, b) -> v` | — | v[j] = max(a[j], b[j]), signed |  |
| `load` | `svld1_s64` | `ld1d` | `(pg, p) -> v` | — | v[j] = p[j] |  |
| `store` | `svst1_s64` | `st1d` | `(pg, p, v)` | — | p[j] = v[j] |  |
| `broadcast` | `svdup_s64` | `mov` | `(s) -> v` | — | v[j] = s |  |
| `lt` | `svcmplt_s64` | `cmpgt` | `(pg, a, b) -> mask` | — | lane j true iff a[j] < b[j], signed |  |

### i32 (integer lanes)

| op | spelling | mnemonic | signature | masked | semantics | note |
|---|---|---|---|---|---|---|
| `and` | `svand_s32_x` | `and` | `(pg, a, b) -> v` | — | v[j] = a[j] & b[j] for active lanes |  |
| `or` | `svorr_s32_x` | `orr` | `(pg, a, b) -> v` | — | v[j] = a[j] \| b[j] for active lanes |  |
| `shl` | recipe: `svreinterpret_s32_u32(svlsl_u32_x(pg, svreinterpret_u32_s32(a), svreinterpret_u32_s32(counts)))` | `lsl` | `(pg, a, counts) -> v` | — | v[j] = a[j] << counts[j] for active lanes |  |
| `shr` | recipe: `svreinterpret_s32_u32(svlsr_u32_x(pg, svreinterpret_u32_s32(a), svreinterpret_u32_s32(counts)))` | `lsr` | `(pg, a, counts) -> v` | — | v[j] = a[j] >> counts[j], logical, for active lanes |  |
| `land` | recipe: `svand_b_z(pg, svcmpne_s32(pg, a, svdup_s32(0)), svcmpne_s32(pg, b, svdup_s32(0)))` | `cmpne+and` | `(pg, a, b) -> pg` | — | lane j active iff (a[j] != 0) && (b[j] != 0) | yields a predicate; svsel turns it into 0/1 lanes |
| `lor` | recipe: `svorr_b_z(pg, svcmpne_s32(pg, a, svdup_s32(0)), svcmpne_s32(pg, b, svdup_s32(0)))` | `cmpne+orr` | `(pg, a, b) -> pg` | — | lane j active iff (a[j] != 0) \|\| (b[j] != 0) |  |
| `mod` | recipe: `svint32_t q = svdiv_s32_x(pg, a, b)`; `svsel_s32(svcmpeq_n_s32(pg, b, 0), svdup_s32(0), svmls_s32_x(pg, a, q, b))` | `sdiv+mls` | `(pg, a, b) -> v` | — | v[j] = a[j] % b[j], truncated (sign of a) | q = svdiv(pg, a, b), r = svmls(pg, a, q, b); SDIV gives 0 for b == 0, so r would be a: select 0 there like the other targets; no trap on INT_MIN / -1 |
| `add` | `svadd_s32_x` | `add` | `(pg, a, b) -> v` | — | v[j] = a[j] + b[j], wrapping |  |
| `sub` | `svsub_s32_x` | `sub` | `(pg, a, b) -> v` | — | v[j] = a[j] - b[j], wrapping |  |
| `mul` | `svmul_s32_x` | `mul` | `(pg, a, b) -> v` | — | v[j] = a[j] * b[j], low bits |  |
| `min` | `svmin_s32_x` | `smin` | `(pg, a, b) -> v` | — | v[j] = min(a[j], b[j]), signed |  |
| `max` | `svmax_s32_x` | `smax` | `(pg, a, b) -> v` | — | v[j] = max(a[j], b[j]), signed |  |
| `load` | `svld1_s32` | `ld1w` | `(pg, p) -> v` | — | v[j] = p[j] |  |
| `store` | `svst1_s32` | `st1w` | `(pg, p, v)` | — | p[j] = v[j] |  |
| `broadcast` | `svdup_s32` | `mov` | `(s) -> v` | — | v[j] = s |  |
| `lt` | `svcmplt_s32` | `cmpgt` | `(pg, a, b) -> mask` | — | lane j true iff a[j] < b[j], signed |  |

## Hardware assists

| intrinsic | mnemonic | helps | note |
|---|---|---|---|
| `svexpa_f64` | `fexpa` | exp | the hardware 2^(I/64) table with the exponent field replaced (ACLE SVE 6.16.30): the input is (k + 1023)*64 + j for f64 and (k + 127)*64 + j for f32 (the biased exponent), EXPA yields 2^k*2^(j/64) and a short polynomial finishes - the sub-1-ulp exp building block |
| `svscale_f64_x` | `fscale` | exp | ldexp-style scaling by 2^floor(n): the 2^k of the exp k-split, predicated |
| `svlogb_f64_x` | `flogb` | exp | SVE2 only (-march=armv8-a+sve2), returns svint64_t: floor(log2\|x\|) per lane, frexp's e minus 1, predicated |
| `svrecpe_f64` | `frecpe` | div | 8-bit reciprocal estimate; each Newton step is r = svmul(r, svrecps(d, r)), f64 needs 3 |
| `svrsqrte_f64` | `frsqrte` | sqrt | rsqrt estimate; refine with the frsqrts step for a fast reciprocal square root |
| `svrecps_f64` | `frecps` | div | returns only the factor 2 - d*r: the update is r = svmul_f64_x(pg, r, svrecps_f64(d, r)) |
