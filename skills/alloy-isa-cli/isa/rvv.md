# rvv — RISC-V V 1.0 (scalable vectors, vl-driven)

Vector bytes: length-agnostic; lanes: f64: runtime, f32: runtime, i64: runtime, i32: runtime; opmask/predicate.

Legal schedules: scalar, rvv_vsetvl. gen_mask: __riscv_vmsltu_vx_u{64,32}m1_b{64,32}(__riscv_vid_v_u{64,32}m1(vl), N - i, vl).

- **scalar** (Scalar loop): No vectorization: one element per iteration, no tail handling. The baseline every speedup is measured against. Tail: none.
  - gcc: -fno-tree-vectorize
  - clang: #pragma clang loop vectorize(disable)
- **rvv_vsetvl** (Strip-mined RVV loop): RISC-V V shape: each pass asks vsetvl for vl = min(N - i, VLMAX) and every intrinsic takes vl, so the last pass is the tail and no mask or remainder loop exists. The loop steps by the vl it got. Tail: none: vsetvl shortens the last pass.
  - gcc: -march=rv64gcv -O3 (auto-vectorizes to this shape), or explicit intrinsics via this skeleton
  - clang: -march=rv64gcv -O3 (auto-vectorizes to this shape), or explicit intrinsics via this skeleton

Scalable: VLEN is fixed per core (128 bits and up on application cores, 256 on SoftHier's Spatz) and known only at run time - lanes 0 here mean 'runtime length'. Every intrinsic takes vl last: size_t vl = __riscv_vsetvl_e64m1(N - i) per pass, or __riscv_vsetvlmax_e64m1() for a whole register. Rows use LMUL 1 (m1); m2, m4, m8 group 2, 4, 8 registers for longer strips with the same spelling. Masks are vbool<SEW/LMUL>_t. Intrinsics of the v1.0 spec (GCC 14, Clang 17 and later): older toolchains spell them without the __riscv_ prefix. Host flag: -march=rv64gcv (the f16 storage rows: rv64gcv_zvfhmin); checked under qemu-riscv64 at VLEN 256. SoftHier's Spatz rows (alloy/isa/softhier.toml) are this ISA on RV32 with LMUL 8.

### f64

| op | spelling | mnemonic | signature | masked | semantics | note |
|---|---|---|---|---|---|---|
| `load` | `__riscv_vle64_v_f64m1` | `vle64.v` | `(p, vl) -> v` | — | v[j] = p[j] for j < vl | unit stride, any alignment of the element type; vl from vsetvl bounds the lanes, so the tail needs no mask |
| `store` | `__riscv_vse64_v_f64m1` | `vse64.v` | `(p, v, vl) -> void` | — | p[j] = v[j] for j < vl |  |
| `broadcast` | `__riscv_vfmv_v_f_f64m1` | `vfmv.v.f` | `(s, vl) -> v` | — | v[j] = s for j < vl |  |
| `add` | `__riscv_vfadd_vv_f64m1` | `vfadd.vv` | `(a, b, vl) -> v` | — | v[j] = a[j] + b[j] for j < vl |  |
| `sub` | `__riscv_vfsub_vv_f64m1` | `vfsub.vv` | `(a, b, vl) -> v` | — | v[j] = a[j] - b[j] for j < vl |  |
| `mul` | `__riscv_vfmul_vv_f64m1` | `vfmul.vv` | `(a, b, vl) -> v` | — | v[j] = a[j] * b[j] for j < vl |  |
| `div` | `__riscv_vfdiv_vv_f64m1` | `vfdiv.vv` | `(a, b, vl) -> v` | — | v[j] = a[j] / b[j] for j < vl |  |
| `fma` | `__riscv_vfmacc_vv_f64m1` | `vfmacc.vv` | `(add, m1, m2, vl) -> v` | — | v[j] = add[j] + m1[j]*m2[j] for j < vl, rounded once | operand-order trap: the accumulator is FIRST (vd += vs1*vs2), like NEON and SVE, unlike Intel's fmadd; vfmadd (vd = vd*vs1 + vs2) overwrites a multiplicand instead |
| `min` | `__riscv_vfmin_vv_f64m1` | `vfmin.vv` | `(a, b, vl) -> v` | — | v[j] = the smaller of a[j], b[j]; a NaN operand gives the other operand, -0 is below +0 | IEEE 754-2019 minimumNumber/maximumNumber: a NaN lane does not propagate (x86 returns the second operand, Arm FMIN/FMAX return NaN) |
| `max` | `__riscv_vfmax_vv_f64m1` | `vfmax.vv` | `(a, b, vl) -> v` | — | v[j] = the larger of a[j], b[j]; a NaN operand gives the other operand, -0 is below +0 | IEEE 754-2019 minimumNumber/maximumNumber: a NaN lane does not propagate (x86 returns the second operand, Arm FMIN/FMAX return NaN) |
| `sqrt` | `__riscv_vfsqrt_v_f64m1` | `vfsqrt.v` | `(a, vl) -> v` | — | v[j] = sqrt(a[j]) for j < vl, correctly rounded |  |
| `abs` | `__riscv_vfabs_v_f64m1` | `vfabs.v` | `(a, vl) -> v` | — | v[j] = \|a[j]\|: the sign bit cleared, NaN included | an assembler alias of vfsgnjx.vv v, a, a |
| `neg` | `__riscv_vfneg_v_f64m1` | `vfneg.v` | `(a, vl) -> v` | — | v[j] = -a[j]: the sign bit flipped, NaN and zero included | an assembler alias of vfsgnjn.vv v, a, a |
| `zero` | `__riscv_vfmv_v_f_f64m1` | `vmv.v.i` | `(0.0, vl) -> v` | — | v[j] = 0.0 for j < vl |  |
| `reduce_add` | recipe: `__riscv_vfmv_f_s_f64m1_f64(__riscv_vfredusum_vs_f64m1_f64m1(v, __riscv_vfmv_s_f_f64m1(0, vl), vl))` | `vfredusum.vs + vfmv.f.s` | `(v, vl) -> s` | — | s = the sum of the first vl lanes of v | unordered sum (any association): needs reassociation permission; vfredosum is the ordered, slower left fold. The scalar start value sits in lane 0 of the second operand (a zero start compiles to vmv.s.x of the zero register) |
| `reduce_min` | recipe: `__riscv_vfmv_f_s_f64m1_f64(__riscv_vfredmin_vs_f64m1_f64m1(v, v, vl))` | `vfredmin.vs + vfmv.f.s` | `(v, vl) -> s` | — | s = the smallest of the first vl lanes of v | v seeds itself: lane 0 of the second operand joins the reduction, and it is one of the lanes anyway. NaN lanes are skipped (minimumNumber); all-NaN gives the canonical NaN |
| `reduce_max` | recipe: `__riscv_vfmv_f_s_f64m1_f64(__riscv_vfredmax_vs_f64m1_f64m1(v, v, vl))` | `vfredmax.vs + vfmv.f.s` | `(v, vl) -> s` | — | s = the largest of the first vl lanes of v | v seeds itself: lane 0 of the second operand joins the reduction, and it is one of the lanes anyway. NaN lanes are skipped (minimumNumber); all-NaN gives the canonical NaN |
| `lt` | `__riscv_vmflt_vv_f64m1_b64` | `vmflt.vv` | `(a, b, vl) -> mask` | — | lane j true iff a[j] < b[j]; false on NaN | a vbool64_t mask register (one bit per lane) |
| `select` | `__riscv_vmerge_vvm_f64m1` | `vmerge.vvm` | `(f, t, mask, vl) -> v` | — | v[j] = mask[j] ? t[j] : f[j] | operand-order trap: the value for a false lane comes FIRST |
| `gen_mask` | recipe: `__riscv_vmsltu_vx_u64m1_b64(__riscv_vid_v_u64m1(vl), N - i, vl)` | `vid.v + vmsltu.vx` | `(i, N, vl) -> pg` | — | lane j active iff i + j < N | rarely needed: a strip-mined loop (rvv_vsetvl) sets vl = min(N - i, VLMAX) each pass and has no tail. A mask suits a fixed vl, as in a full_mask loop |
| `gather` | recipe: `__riscv_vluxei64_v_f64m1(base, __riscv_vsll_vx_u64m1(__riscv_vle64_v_u64m1((const uint64_t*)idx, vl), 3, vl), vl)` | `vle64.v + vsll.vi + vluxei64.v` | `(base, idx, vl) -> v` | — | v[j] = base[idx[j]] for j < vl, idx holding int64 element indices | the indexed load takes BYTE offsets: scale the element indices by the element size first. vluxei is unordered; vloxei keeps the order (only matters for I/O) |
| `scatter` | recipe: `__riscv_vsuxei64_v_f64m1(base, __riscv_vsll_vx_u64m1(__riscv_vle64_v_u64m1((const uint64_t*)idx, vl), 3, vl), v, vl)` | `vle64.v + vsll.vi + vsuxei64.v` | `(base, idx, v, vl) -> void` | — | base[idx[j]] = v[j] for j < vl, idx holding int64 element indices | byte offsets, as for the gather; vsuxei is unordered, so two lanes with one index leave either value (vsoxei writes in lane order, the last lane wins) |
| `mod` | recipe: `vfloat64m1_t q = __riscv_vfcvt_f_x_v_f64m1(__riscv_vfcvt_rtz_x_f_v_i64m1(__riscv_vfdiv_vv_f64m1(a, b, vl), vl), vl)`; `__riscv_vfnmsac_vv_f64m1(a, q, b, vl)` | `vfdiv.vv + vfcvt.rtz.x.f.v + vfcvt.f.x.v + vfnmsac.vv` | `(a, b, vl) -> v` | — | v[j] = a[j] - trunc(a[j]/b[j])*b[j]: fmod only for finite b and \|a/b\| below 2^p | no fmod and no round-toward-zero to float: q = trunc(a/b) through an int64 conversion (rtz), r = vfnmsac(a, q, b) = a - q*b. Holds only for finite b and \|a/b\| < 2^52 (the conversion also saturates past 2^63); outside, call scalar fmod |
| `scan_add` | recipe: `vfloat64m1_t t = v`; `for (size_t d = 1; d < vl; d *= 2) t = __riscv_vfadd_vv_f64m1(t, __riscv_vslideup_vx_f64m1(__riscv_vfmv_v_f_f64m1(0, vl), t, d, vl), vl)`; `t` | `vslideup.vx + vfadd.vv` | `(v, vl) -> v` | — | inclusive prefix sum: v[j] = x[0] + ... + x[j] for j < vl | no single intrinsic: vslideup moves the lanes up by d onto a zero vector, for d = 1, 2, 4, ... below vl. log2(vl) shifted adds, so the sums associate differently from a scalar left fold: needs reassociation permission; across registers, add the broadcast last lane of the register before (vslidedown by vl - 1, then vfmv.f.s) |
| `exp` | 6 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — | v[j] = exp(v[j]) | no transcendental instruction and no exponent assist (only the 7-bit estimates vfrec7 and vfrsqrt7): range-reduce, run a tier's polynomial with vfmacc, and rebuild 2^k by an integer add into the exponent field (vsll by 52, vadd, vreinterpret). glibc has no RISC-V libmvec; SLEEF builds RVV versions (Sleef_expdx_u10rvvm1 and m2, check the installed sleef.h), and the Rivos veclibm covers every SLEEF function |
| `sin` | 5 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — | v[j] = sin(v[j]) | no transcendental instruction and no exponent assist (only the 7-bit estimates vfrec7 and vfrsqrt7): range-reduce, run a tier's polynomial with vfmacc, and rebuild 2^k by an integer add into the exponent field (vsll by 52, vadd, vreinterpret). glibc has no RISC-V libmvec; SLEEF builds RVV versions (Sleef_sindx_u10rvvm1 and m2, check the installed sleef.h), and the Rivos veclibm covers every SLEEF function |
| `cos` | 5 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — | v[j] = cos(v[j]) | no transcendental instruction and no exponent assist (only the 7-bit estimates vfrec7 and vfrsqrt7): range-reduce, run a tier's polynomial with vfmacc, and rebuild 2^k by an integer add into the exponent field (vsll by 52, vadd, vreinterpret). glibc has no RISC-V libmvec; SLEEF builds RVV versions (Sleef_cosdx_u10rvvm1 and m2, check the installed sleef.h), and the Rivos veclibm covers every SLEEF function |

### f32

| op | spelling | mnemonic | signature | masked | semantics | note |
|---|---|---|---|---|---|---|
| `load` | `__riscv_vle32_v_f32m1` | `vle32.v` | `(p, vl) -> v` | — | v[j] = p[j] for j < vl | unit stride, any alignment of the element type; vl from vsetvl bounds the lanes, so the tail needs no mask |
| `store` | `__riscv_vse32_v_f32m1` | `vse32.v` | `(p, v, vl) -> void` | — | p[j] = v[j] for j < vl |  |
| `broadcast` | `__riscv_vfmv_v_f_f32m1` | `vfmv.v.f` | `(s, vl) -> v` | — | v[j] = s for j < vl |  |
| `add` | `__riscv_vfadd_vv_f32m1` | `vfadd.vv` | `(a, b, vl) -> v` | — | v[j] = a[j] + b[j] for j < vl |  |
| `sub` | `__riscv_vfsub_vv_f32m1` | `vfsub.vv` | `(a, b, vl) -> v` | — | v[j] = a[j] - b[j] for j < vl |  |
| `mul` | `__riscv_vfmul_vv_f32m1` | `vfmul.vv` | `(a, b, vl) -> v` | — | v[j] = a[j] * b[j] for j < vl |  |
| `div` | `__riscv_vfdiv_vv_f32m1` | `vfdiv.vv` | `(a, b, vl) -> v` | — | v[j] = a[j] / b[j] for j < vl |  |
| `fma` | `__riscv_vfmacc_vv_f32m1` | `vfmacc.vv` | `(add, m1, m2, vl) -> v` | — | v[j] = add[j] + m1[j]*m2[j] for j < vl, rounded once | operand-order trap: the accumulator is FIRST (vd += vs1*vs2), like NEON and SVE, unlike Intel's fmadd; vfmadd (vd = vd*vs1 + vs2) overwrites a multiplicand instead |
| `min` | `__riscv_vfmin_vv_f32m1` | `vfmin.vv` | `(a, b, vl) -> v` | — | v[j] = the smaller of a[j], b[j]; a NaN operand gives the other operand, -0 is below +0 | IEEE 754-2019 minimumNumber/maximumNumber: a NaN lane does not propagate (x86 returns the second operand, Arm FMIN/FMAX return NaN) |
| `max` | `__riscv_vfmax_vv_f32m1` | `vfmax.vv` | `(a, b, vl) -> v` | — | v[j] = the larger of a[j], b[j]; a NaN operand gives the other operand, -0 is below +0 | IEEE 754-2019 minimumNumber/maximumNumber: a NaN lane does not propagate (x86 returns the second operand, Arm FMIN/FMAX return NaN) |
| `sqrt` | `__riscv_vfsqrt_v_f32m1` | `vfsqrt.v` | `(a, vl) -> v` | — | v[j] = sqrt(a[j]) for j < vl, correctly rounded |  |
| `abs` | `__riscv_vfabs_v_f32m1` | `vfabs.v` | `(a, vl) -> v` | — | v[j] = \|a[j]\|: the sign bit cleared, NaN included | an assembler alias of vfsgnjx.vv v, a, a |
| `neg` | `__riscv_vfneg_v_f32m1` | `vfneg.v` | `(a, vl) -> v` | — | v[j] = -a[j]: the sign bit flipped, NaN and zero included | an assembler alias of vfsgnjn.vv v, a, a |
| `zero` | `__riscv_vfmv_v_f_f32m1` | `vmv.v.i` | `(0.0, vl) -> v` | — | v[j] = 0.0 for j < vl |  |
| `reduce_add` | recipe: `__riscv_vfmv_f_s_f32m1_f32(__riscv_vfredusum_vs_f32m1_f32m1(v, __riscv_vfmv_s_f_f32m1(0, vl), vl))` | `vfredusum.vs + vfmv.f.s` | `(v, vl) -> s` | — | s = the sum of the first vl lanes of v | unordered sum (any association): needs reassociation permission; vfredosum is the ordered, slower left fold. The scalar start value sits in lane 0 of the second operand (a zero start compiles to vmv.s.x of the zero register) |
| `reduce_min` | recipe: `__riscv_vfmv_f_s_f32m1_f32(__riscv_vfredmin_vs_f32m1_f32m1(v, v, vl))` | `vfredmin.vs + vfmv.f.s` | `(v, vl) -> s` | — | s = the smallest of the first vl lanes of v | v seeds itself: lane 0 of the second operand joins the reduction, and it is one of the lanes anyway. NaN lanes are skipped (minimumNumber); all-NaN gives the canonical NaN |
| `reduce_max` | recipe: `__riscv_vfmv_f_s_f32m1_f32(__riscv_vfredmax_vs_f32m1_f32m1(v, v, vl))` | `vfredmax.vs + vfmv.f.s` | `(v, vl) -> s` | — | s = the largest of the first vl lanes of v | v seeds itself: lane 0 of the second operand joins the reduction, and it is one of the lanes anyway. NaN lanes are skipped (minimumNumber); all-NaN gives the canonical NaN |
| `lt` | `__riscv_vmflt_vv_f32m1_b32` | `vmflt.vv` | `(a, b, vl) -> mask` | — | lane j true iff a[j] < b[j]; false on NaN | a vbool32_t mask register (one bit per lane) |
| `select` | `__riscv_vmerge_vvm_f32m1` | `vmerge.vvm` | `(f, t, mask, vl) -> v` | — | v[j] = mask[j] ? t[j] : f[j] | operand-order trap: the value for a false lane comes FIRST |
| `gen_mask` | recipe: `__riscv_vmsltu_vx_u32m1_b32(__riscv_vid_v_u32m1(vl), N - i, vl)` | `vid.v + vmsltu.vx` | `(i, N, vl) -> pg` | — | lane j active iff i + j < N | rarely needed: a strip-mined loop (rvv_vsetvl) sets vl = min(N - i, VLMAX) each pass and has no tail. A mask suits a fixed vl, as in a full_mask loop |
| `gather` | recipe: `__riscv_vluxei64_v_f32m1(base, __riscv_vsll_vx_u64m2(__riscv_vle64_v_u64m2((const uint64_t*)idx, vl), 2, vl), vl)` | `vle64.v + vsll.vi + vluxei64.v` | `(base, idx, vl) -> v` | — | v[j] = base[idx[j]] for j < vl, idx holding int64 element indices | the indexed load takes BYTE offsets: scale the element indices by the element size first. vluxei is unordered; vloxei keeps the order (only matters for I/O) |
| `scatter` | recipe: `__riscv_vsuxei64_v_f32m1(base, __riscv_vsll_vx_u64m2(__riscv_vle64_v_u64m2((const uint64_t*)idx, vl), 2, vl), v, vl)` | `vle64.v + vsll.vi + vsuxei64.v` | `(base, idx, v, vl) -> void` | — | base[idx[j]] = v[j] for j < vl, idx holding int64 element indices | byte offsets, as for the gather; vsuxei is unordered, so two lanes with one index leave either value (vsoxei writes in lane order, the last lane wins) |
| `mod` | recipe: `vfloat32m1_t q = __riscv_vfcvt_f_x_v_f32m1(__riscv_vfcvt_rtz_x_f_v_i32m1(__riscv_vfdiv_vv_f32m1(a, b, vl), vl), vl)`; `__riscv_vfnmsac_vv_f32m1(a, q, b, vl)` | `vfdiv.vv + vfcvt.rtz.x.f.v + vfcvt.f.x.v + vfnmsac.vv` | `(a, b, vl) -> v` | — | v[j] = a[j] - trunc(a[j]/b[j])*b[j]: fmod only for finite b and \|a/b\| below 2^p | no fmod and no round-toward-zero to float: q = trunc(a/b) through an int32 conversion (rtz), r = vfnmsac(a, q, b) = a - q*b. Holds only for finite b and \|a/b\| < 2^23 (the conversion also saturates past 2^31); outside, call scalar fmod |
| `scan_add` | recipe: `vfloat32m1_t t = v`; `for (size_t d = 1; d < vl; d *= 2) t = __riscv_vfadd_vv_f32m1(t, __riscv_vslideup_vx_f32m1(__riscv_vfmv_v_f_f32m1(0, vl), t, d, vl), vl)`; `t` | `vslideup.vx + vfadd.vv` | `(v, vl) -> v` | — | inclusive prefix sum: v[j] = x[0] + ... + x[j] for j < vl | no single intrinsic: vslideup moves the lanes up by d onto a zero vector, for d = 1, 2, 4, ... below vl. log2(vl) shifted adds, so the sums associate differently from a scalar left fold: needs reassociation permission; across registers, add the broadcast last lane of the register before (vslidedown by vl - 1, then vfmv.f.s) |
| `exp` | 6 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — | v[j] = exp(v[j]) | no transcendental instruction and no exponent assist (only the 7-bit estimates vfrec7 and vfrsqrt7): range-reduce, run a tier's polynomial with vfmacc, and rebuild 2^k by an integer add into the exponent field (vsll by 23, vadd, vreinterpret). glibc has no RISC-V libmvec; SLEEF builds RVV versions (Sleef_expfx_u10rvvm1 and m2, check the installed sleef.h), and the Rivos veclibm covers every SLEEF function |
| `sin` | 5 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — | v[j] = sin(v[j]) | no transcendental instruction and no exponent assist (only the 7-bit estimates vfrec7 and vfrsqrt7): range-reduce, run a tier's polynomial with vfmacc, and rebuild 2^k by an integer add into the exponent field (vsll by 23, vadd, vreinterpret). glibc has no RISC-V libmvec; SLEEF builds RVV versions (Sleef_sinfx_u10rvvm1 and m2, check the installed sleef.h), and the Rivos veclibm covers every SLEEF function |
| `cos` | 5 polynomial tiers (see transcendentals.md) | — | `(v) -> v` | — | v[j] = cos(v[j]) | no transcendental instruction and no exponent assist (only the 7-bit estimates vfrec7 and vfrsqrt7): range-reduce, run a tier's polynomial with vfmacc, and rebuild 2^k by an integer add into the exponent field (vsll by 23, vadd, vreinterpret). glibc has no RISC-V libmvec; SLEEF builds RVV versions (Sleef_cosfx_u10rvvm1 and m2, check the installed sleef.h), and the Rivos veclibm covers every SLEEF function |
| `load_f16` | recipe: `__riscv_vfwcvt_f_f_v_f32m1(__riscv_vle16_v_f16mf2((const _Float16*)p, vl), vl)` | `vle16.v + vfwcvt.f.f.v` | `(p, vl) -> v` | — | v[j] = (float)p[j], p holding vl f16 | Zvfhmin (-march=..._zvfhmin): f16 storage and conversions only; arithmetic on f16 lanes needs Zvfh. The f16 sit in half a register (mf2) and widen into a whole one; exact |
| `store_f16` | recipe: `__riscv_vse16_v_f16mf2((_Float16*)p, __riscv_vfncvt_f_f_w_f16mf2(v, vl), vl)` | `vfncvt.f.f.w + vse16.v` | `(p, v, vl)` | — | p[j] = (f16)v[j], rounded by frm (nearest even by default) | Zvfhmin; the narrowing convert rounds by the dynamic rounding mode (frm) |
| `load_bf16` | recipe: `__riscv_vreinterpret_v_u32m1_f32m1(__riscv_vsll_vx_u32m1(__riscv_vzext_vf2_u32m1(__riscv_vle16_v_u16mf2(p, vl), vl), 16, vl))` | `vle16.v + vzext.vf2 + vsll.vi` | `(p, vl) -> v` | — | v[j] = the f32 whose upper 16 bits are p[j] | widen and shift into the top half; exact on base V (Zvfbfmin's vfwcvtbf16 does it in one instruction) |
| `store_bf16` | recipe: `vuint32m1_t x = __riscv_vreinterpret_v_f32m1_u32m1(v)`; `vuint32m1_t r = __riscv_vadd_vv_u32m1(x, __riscv_vadd_vx_u32m1(__riscv_vand_vx_u32m1(__riscv_vsrl_vx_u32m1(x, 16, vl), 1, vl), 0x7fff, vl), vl)`; `__riscv_vse16_v_u16mf2(p, __riscv_vnsrl_wx_u16mf2(r, 16, vl), vl)` | `vsrl.vi + vand.vi + vadd + vnsrl.wi + vse16.v` | `(p, v, vl)` | — | p[j] = v[j] rounded to nearest even bf16 | round to nearest even by adding 0x7fff plus the lowest kept bit; vnsrl shifts and narrows in one step. A NaN may round to infinity: quiet it first if NaN can occur. Zvfbfmin's vfncvtbf16 rounds in one instruction |

### i64 (integer lanes)

| op | spelling | mnemonic | signature | masked | semantics | note |
|---|---|---|---|---|---|---|
| `load` | `__riscv_vle64_v_i64m1` | `vle64.v` | `(p, vl) -> v` | — | v[j] = p[j] for j < vl |  |
| `store` | `__riscv_vse64_v_i64m1` | `vse64.v` | `(p, v, vl) -> void` | — | p[j] = v[j] for j < vl |  |
| `broadcast` | `__riscv_vmv_v_x_i64m1` | `vmv.v.x` | `(s, vl) -> v` | — | v[j] = s for j < vl | a scalar read from memory may fold into a zero-stride load (vlse with stride zero) |
| `add` | `__riscv_vadd_vv_i64m1` | `vadd.vv` | `(a, b, vl) -> v` | — | v[j] = a[j] + b[j] for j < vl | wraps modulo 2^64 |
| `sub` | `__riscv_vsub_vv_i64m1` | `vsub.vv` | `(a, b, vl) -> v` | — | v[j] = a[j] - b[j] for j < vl | wraps modulo 2^64 |
| `mul` | `__riscv_vmul_vv_i64m1` | `vmul.vv` | `(a, b, vl) -> v` | — | v[j] = a[j] * b[j] for j < vl | wraps modulo 2^64 |
| `and` | `__riscv_vand_vv_i64m1` | `vand.vv` | `(a, b, vl) -> v` | — | v[j] = a[j] & b[j] for j < vl |  |
| `or` | `__riscv_vor_vv_i64m1` | `vor.vv` | `(a, b, vl) -> v` | — | v[j] = a[j] \| b[j] for j < vl |  |
| `mod` | recipe: `__riscv_vmerge_vxm_i64m1(__riscv_vrem_vv_i64m1(a, b, vl), 0, __riscv_vmseq_vx_i64m1_b64(b, 0, vl), vl)` | `vrem.vv + vmseq.vi + vmerge.vim` | `(a, b, vl) -> v` | — | v[j] = a[j] % b[j], truncated (sign of a); 0 where b[j] == 0 | vrem never traps: a zero divisor gives a[j], so select 0 there like the other targets; INT_MIN % -1 gives 0 |
| `min` | `__riscv_vmin_vv_i64m1` | `vmin.vv` | `(a, b, vl) -> v` | — | v[j] = the smaller of a[j], b[j], signed | vminu is the unsigned one |
| `max` | `__riscv_vmax_vv_i64m1` | `vmax.vv` | `(a, b, vl) -> v` | — | v[j] = the larger of a[j], b[j], signed | vmaxu is the unsigned one |
| `shl` | recipe: `__riscv_vsll_vv_i64m1(a, __riscv_vreinterpret_v_i64m1_u64m1(counts), vl)` | `vsll.vv` | `(a, counts, vl) -> v` | — | v[j] = a[j] << counts[j] | the counts are an unsigned vector; only their low 6 bits count |
| `shr` | recipe: `__riscv_vreinterpret_v_u64m1_i64m1(__riscv_vsrl_vv_u64m1(__riscv_vreinterpret_v_i64m1_u64m1(a), __riscv_vreinterpret_v_i64m1_u64m1(counts), vl))` | `vsrl.vv` | `(a, counts, vl) -> v` | — | v[j] = (unsigned)a[j] >> counts[j], zeros shifted in | logical: vsrl exists only on unsigned lanes (vsra is the arithmetic shift of signed ones) |
| `land` | recipe: `__riscv_vmand_mm_b64(__riscv_vmsne_vx_i64m1_b64(a, 0, vl), __riscv_vmsne_vx_i64m1_b64(b, 0, vl), vl)` | `vmsne.vi + vmand.mm` | `(a, b, vl) -> mask` | — | lane j true iff both of a[j], b[j] are non-zero | a mask, read with vmerge |
| `lor` | recipe: `__riscv_vmor_mm_b64(__riscv_vmsne_vx_i64m1_b64(a, 0, vl), __riscv_vmsne_vx_i64m1_b64(b, 0, vl), vl)` | `vmsne.vi + vmor.mm` | `(a, b, vl) -> mask` | — | lane j true iff either of a[j], b[j] are non-zero | a mask, read with vmerge |
| `lt` | `__riscv_vmslt_vv_i64m1_b64` | `vmslt.vv` | `(a, b, vl) -> mask` | — | lane j true iff a[j] < b[j], signed | a vbool64_t mask; vmsltu compares unsigned |

### i32 (integer lanes)

| op | spelling | mnemonic | signature | masked | semantics | note |
|---|---|---|---|---|---|---|
| `load` | `__riscv_vle32_v_i32m1` | `vle32.v` | `(p, vl) -> v` | — | v[j] = p[j] for j < vl |  |
| `store` | `__riscv_vse32_v_i32m1` | `vse32.v` | `(p, v, vl) -> void` | — | p[j] = v[j] for j < vl |  |
| `broadcast` | `__riscv_vmv_v_x_i32m1` | `vmv.v.x` | `(s, vl) -> v` | — | v[j] = s for j < vl | a scalar read from memory may fold into a zero-stride load (vlse with stride zero) |
| `add` | `__riscv_vadd_vv_i32m1` | `vadd.vv` | `(a, b, vl) -> v` | — | v[j] = a[j] + b[j] for j < vl | wraps modulo 2^32 |
| `sub` | `__riscv_vsub_vv_i32m1` | `vsub.vv` | `(a, b, vl) -> v` | — | v[j] = a[j] - b[j] for j < vl | wraps modulo 2^32 |
| `mul` | `__riscv_vmul_vv_i32m1` | `vmul.vv` | `(a, b, vl) -> v` | — | v[j] = a[j] * b[j] for j < vl | wraps modulo 2^32 |
| `and` | `__riscv_vand_vv_i32m1` | `vand.vv` | `(a, b, vl) -> v` | — | v[j] = a[j] & b[j] for j < vl |  |
| `or` | `__riscv_vor_vv_i32m1` | `vor.vv` | `(a, b, vl) -> v` | — | v[j] = a[j] \| b[j] for j < vl |  |
| `mod` | recipe: `__riscv_vmerge_vxm_i32m1(__riscv_vrem_vv_i32m1(a, b, vl), 0, __riscv_vmseq_vx_i32m1_b32(b, 0, vl), vl)` | `vrem.vv + vmseq.vi + vmerge.vim` | `(a, b, vl) -> v` | — | v[j] = a[j] % b[j], truncated (sign of a); 0 where b[j] == 0 | vrem never traps: a zero divisor gives a[j], so select 0 there like the other targets; INT_MIN % -1 gives 0 |
| `min` | `__riscv_vmin_vv_i32m1` | `vmin.vv` | `(a, b, vl) -> v` | — | v[j] = the smaller of a[j], b[j], signed | vminu is the unsigned one |
| `max` | `__riscv_vmax_vv_i32m1` | `vmax.vv` | `(a, b, vl) -> v` | — | v[j] = the larger of a[j], b[j], signed | vmaxu is the unsigned one |
| `shl` | recipe: `__riscv_vsll_vv_i32m1(a, __riscv_vreinterpret_v_i32m1_u32m1(counts), vl)` | `vsll.vv` | `(a, counts, vl) -> v` | — | v[j] = a[j] << counts[j] | the counts are an unsigned vector; only their low 5 bits count |
| `shr` | recipe: `__riscv_vreinterpret_v_u32m1_i32m1(__riscv_vsrl_vv_u32m1(__riscv_vreinterpret_v_i32m1_u32m1(a), __riscv_vreinterpret_v_i32m1_u32m1(counts), vl))` | `vsrl.vv` | `(a, counts, vl) -> v` | — | v[j] = (unsigned)a[j] >> counts[j], zeros shifted in | logical: vsrl exists only on unsigned lanes (vsra is the arithmetic shift of signed ones) |
| `land` | recipe: `__riscv_vmand_mm_b32(__riscv_vmsne_vx_i32m1_b32(a, 0, vl), __riscv_vmsne_vx_i32m1_b32(b, 0, vl), vl)` | `vmsne.vi + vmand.mm` | `(a, b, vl) -> mask` | — | lane j true iff both of a[j], b[j] are non-zero | a mask, read with vmerge |
| `lor` | recipe: `__riscv_vmor_mm_b32(__riscv_vmsne_vx_i32m1_b32(a, 0, vl), __riscv_vmsne_vx_i32m1_b32(b, 0, vl), vl)` | `vmsne.vi + vmor.mm` | `(a, b, vl) -> mask` | — | lane j true iff either of a[j], b[j] are non-zero | a mask, read with vmerge |
| `lt` | `__riscv_vmslt_vv_i32m1_b32` | `vmslt.vv` | `(a, b, vl) -> mask` | — | lane j true iff a[j] < b[j], signed | a vbool32_t mask; vmsltu compares unsigned |

## Hardware assists

| intrinsic | mnemonic | helps | note |
|---|---|---|---|
| `__riscv_vfrec7_v_f64m1` | `vfrec7.v` | div | 7-bit reciprocal estimate; each Newton step r = r*(2 - d*r) (vfnmsac then vfmul) doubles the bits, f64 needs 3 |
| `__riscv_vfrsqrt7_v_f64m1` | `vfrsqrt7.v` | sqrt | 7-bit reciprocal square root estimate; refine with r = r*(1.5 - 0.5*x*r*r) for a fast rsqrt |
