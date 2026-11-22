---
name: docs-md-arm-11-custom-datapath-extension
description: "Arm ACLE: Custom Datapath Extension (vendor documentation for Arm NEON, SVE and SME)."
when: "when you need Arm ACLE: Custom Datapath Extension while writing a kernel for Arm NEON, SVE and SME."
---

# Custom Datapath Extension

The intrinsics in this section provide access to instructions in the
Custom Datapath Extension.

The `<arm_cde.h>` header should be included before using these
intrinsics.  The header is available when the `__ARM_FEATURE_CDE` feature
macro is defined.

The intrinsics are stateless and pure, meaning an implementation is permitted
to discard an invocation of an intrinsic whose result is unused without
considering side-effects.

## CDE intrinsics

The following intrinsics are available when `__ARM_FEATURE_CDE` is defined.
These intrinsics use the `coproc` and `imm` compile-time constants to
generate the corresponding CDE instructions.
The `coproc` argument indicates the CDE coprocessor to use.  The range of
available coprocessors is indicated by the bitmap `__ARM_FEATURE_CDE_COPROC`,
described in [Custom Datapath Extension](#custom-datapath-extension).
The `imm` argument must fit within the immediate range of the corresponding CDE
instruction.  Values for these arguments outside these ranges must be rejected.

``` c
  uint32_t __arm_cx1(int coproc, uint32_t imm);
  uint32_t __arm_cx1a(int coproc, uint32_t acc, uint32_t imm);
  uint32_t __arm_cx2(int coproc, uint32_t n, uint32_t imm);
  uint32_t __arm_cx2a(int coproc, uint32_t acc, uint32_t n, uint32_t imm);
  uint32_t __arm_cx3(int coproc, uint32_t n, uint32_t m, uint32_t imm);
  uint32_t __arm_cx3a(int coproc, uint32_t acc, uint32_t n, uint32_t m, uint32_t imm);

  uint64_t __arm_cx1d(int coproc, uint32_t imm);
  uint64_t __arm_cx1da(int coproc, uint64_t acc, uint32_t imm);
  uint64_t __arm_cx2d(int coproc, uint32_t n, uint32_t imm);
  uint64_t __arm_cx2da(int coproc, uint64_t acc, uint32_t n, uint32_t imm);
  uint64_t __arm_cx3d(int coproc, uint32_t n, uint32_t m, uint32_t imm);
  uint64_t __arm_cx3da(int coproc, uint64_t acc, uint32_t n, uint32_t m, uint32_t imm);
```

The following intrinsics are also available when `__ARM_FEATURE_CDE` is defined,
providing access to the CDE instructions that read and write the
floating-point registers:

``` c
  uint32_t __arm_vcx1_u32(int coproc, uint32_t imm);
  uint32_t __arm_vcx1a_u32(int coproc, uint32_t acc, uint32_t imm);
  uint32_t __arm_vcx2_u32(int coproc, uint32_t n, uint32_t imm);
  uint32_t __arm_vcx2a_u32(int coproc, uint32_t acc, uint32_t n, uint32_t imm);
  uint32_t __arm_vcx3_u32(int coproc, uint32_t n, uint32_t m, uint32_t imm);
  uint32_t __arm_vcx3a_u32(int coproc, uint32_t acc, uint32_t n, uint32_t m, uint32_t imm);
```

In addition, the following intrinsics can be used to generate the D-register forms
of the instructions:

``` c
  uint64_t __arm_vcx1d_u64(int coproc, uint32_t imm);
  uint64_t __arm_vcx1da_u64(int coproc, uint64_t acc, uint32_t imm);
  uint64_t __arm_vcx2d_u64(int coproc, uint64_t m, uint32_t imm);
  uint64_t __arm_vcx2da_u64(int coproc, uint64_t acc, uint64_t m, uint32_t imm);
  uint64_t __arm_vcx3d_u64(int coproc, uint64_t n, uint64_t m, uint32_t imm);
  uint64_t __arm_vcx3da_u64(int coproc, uint64_t acc, uint64_t n, uint64_t m, uint32_t imm);
```

The above intrinsics use the `uint32_t` and `uint64_t` types as general
container types.

The following intrinsics can be used to generate CDE instructions that use the
MVE Q registers.

``` c
  uint8x16_t __arm_vcx1q_u8 (int coproc, uint32_t imm);
  T __arm_vcx1qa(int coproc, T acc, uint32_t imm);
  T __arm_vcx2q(int coproc, T n, uint32_t imm);
  uint8x16_t __arm_vcx2q_u8(int coproc, T n, uint32_t imm);
  T __arm_vcx2qa(int coproc, T acc, U n, uint32_t imm);
  T __arm_vcx3q(int coproc, T n, U m, uint32_t imm);
  uint8x16_t __arm_vcx3q_u8(int coproc, T n, U m, uint32_t imm);
  T __arm_vcx3qa(int coproc, T acc, U n, V m, uint32_t imm);

  T __arm_vcx1q_m(int coproc, T inactive, uint32_t imm, mve_pred16_t p);
  T __arm_vcx2q_m(int coproc, T inactive, U n, uint32_t imm, mve_pred16_t p);
  T __arm_vcx3q_m(int coproc, T inactive, U n, V m, uint32_t imm, mve_pred16_t p);

  T __arm_vcx1qa_m(int coproc, T acc, uint32_t imm, mve_pred16_t p);
  T __arm_vcx2qa_m(int coproc, T acc, U n, uint32_t imm, mve_pred16_t p);
  T __arm_vcx3qa_m(int coproc, T acc, U n, V m, uint32_t imm, mve_pred16_t p);
```

These intrinsics are polymorphic in the `T`, `U` and `V` types, which
must be of size 128 bits.
The `__arm_vcx1q_u8`, `__arm_vcx2q_u8` and `__arm_vcx3q_u8` intrinsics
return a container vector of 16 bytes that can be reinterpreted to other
vector types as needed using the intrinsics below:

``` c
  uint16x8_t __arm_vreinterpretq_u16_u8 (uint8x16_t in);
  int16x8_t __arm_vreinterpretq_s16_u8 (uint8x16_t in);
  uint32x4_t __arm_vreinterpretq_u32_u8 (uint8x16_t in);
  int32x4_t __arm_vreinterpretq_s32_u8 (uint8x16_t in);
  uint64x2_t __arm_vreinterpretq_u64_u8 (uint8x16_t in);
  int64x2_t __arm_vreinterpretq_s64_u8 (uint8x16_t in);
  float16x8_t __arm_vreinterpretq_f16_u8 (uint8x16_t in);
  float32x4_t __arm_vreinterpretq_f32_u8 (uint8x16_t in);
  float64x2_t __arm_vreinterpretq_f64_u8 (uint8x16_t in);
```

The parameter `inactive` can be set to an uninitialized (don't care) value
using the MVE `vuninitializedq` family of intrinsics.
