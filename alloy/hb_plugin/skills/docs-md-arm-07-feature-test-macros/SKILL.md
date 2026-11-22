---
name: docs-md-arm-07-feature-test-macros
description: "Arm ACLE: Feature test macros (vendor documentation for Arm NEON, SVE and SME)."
when: "when you need Arm ACLE: Feature test macros while writing a kernel for Arm NEON, SVE and SME."
---

# Feature test macros

## Introduction

The feature test macros allow programmers to determine the availability
of ACLE or subsets of it, or of target architectural features. This may
indicate the availability of some source language extensions (for example
intrinsics) or the likely level of performance of some standard C
features, such as integer division and floating-point.

Several macros are defined as numeric values to indicate the level of
support for particular features. These macros are undefined if the
feature is not present. (Aside: in Standard C/C++, references to
undefined macros expand to 0 in preprocessor expressions, so a
comparison such as:

``` c
  #if __ARM_ARCH >= 7
```

will have the expected effect of evaluating to false if the macro is not
defined.)

All ACLE macros begin with the prefix `__ARM_`. All ACLE macros expand
to integral constant expressions suitable for use in an #if directive,
unless otherwise specified. Syntactically, they must be
primary-expressions generally this means an implementation should
enclose them in parentheses if they are not simple constants.

## Testing for Arm C Language Extensions

An implementation that supports the Arm C Language Extensions defines `__ARM_ACLE`.
For compatibility with existing code, the recommended value of this macro is `202420`.

## Endianness

`__ARM_BIG_ENDIAN` is defined as 1 if data is stored by default in
big-endian format. If the macro is not set, data is stored in
little-endian format. (Aside: the "mixed-endian" format for
double-precision numbers, used on some very old Arm FPU implementations,
is not supported by ACLE or the Arm ABI.)

## Instruction set architecture and features

References to the target architecture refer to the target as
configured in the tools, for example by appropriate command-line
options. This may be a subset or intersection of actual targets, in
order to produce a binary that runs on more than one real architecture.
For example, use of specific features may be disabled.

In the 32-bit architecture, some hardware features may be accessible from
only one or other of A32 or T32 state. For example, in the v5TE and v6
architectures, DSP instructions and (where available) VFP
instructions, are only accessible in A32 state, while in the v7-R
architecture, hardware divide is only accessible from T32 state. Where
both states are available, the implementation should set feature test
macros indicating that the hardware feature is accessible. To provide
access to the hardware feature, an implementation might override the
programmer's preference for target instruction set, or generate an
interworking call to a helper function. This mechanism is outside the
scope of ACLE. In cases where the implementation is given a hard
requirement to use only one state (for example to support validation, or
post-processing) then it should set feature test macros only for the
hardware features available in that state as if compiling for a core
where the other instruction set was not present.

An implementation that allows a user to indicate which functions go into
which state (either as a hard requirement or a preference) is not
required to change the settings of architectural feature test macros.

### Arm architecture level

`__ARM_ARCH` is defined as an integer value indicating the current Arm
instruction set architecture (for example 7 for the Arm v7-A architecture
implemented by Cortex-A8 or the Armv7-M architecture implemented by
Cortex-M3 or 8 for the Armv8-A architecture implemented by Cortex-A57).
Armv8.1-A [[ARMARMv81]](#ARMARMv81) onwards, the value of `__ARM_ARCH` is scaled up to
include minor versions. The formula to calculate the value of
`__ARM_ARCH` from Armv8.1-A [[ARMARMv81]](#ARMARMv81) onwards is given by the following
formula:

> For an Arm architecture ArmvX.Y, `__ARM_ARCH` = X * 100 + Y.
> For example, for Armv8.1 `__ARM_ARCH` = 801.

Since ACLE only supports the Arm architecture, this macro would always
be defined in an ACLE implementation.

Note that the `__ARM_ARCH` macro is defined even for cores which only
support the T32 instruction set.

### Instruction set architecture (A32/T32/A64)

`__ARM_ARCH_ISA_ARM` is defined to 1 if the core supports the Arm
instruction set. It is not defined for M-profile cores.

`__ARM_ARCH_ISA_THUMB` is defined to 1 if the core supports the
original T32 instruction set (including the v6-M architecture) and 2
if it supports the T32 instruction set as found in the v6T2
architecture and all v7 architectures.

`__ARM_ARCH_ISA_A64` is defined to 1 if the core supports AArch64's
A64 instruction set.

`__ARM_32BIT_STATE` is defined to 1 if code is being generated for
AArch32.

`__ARM_64BIT_STATE` is defined to 1 if code is being generated for
AArch64.

### Architectural profile (A, R, M or pre-Cortex)

`__ARM_ARCH_PROFILE` is defined to be one of the char literals
`'A'`, `'R'`, `'M'` or `'S'`, or unset, according to the
architectural profile of the target. `'S'` indicates the common
subset of the A and R profiles. The common subset of the A, R and M
profiles is indicated by

``` c
  __ARM_ARCH == 7 && !defined (__ARM_ARCH_PROFILE)
```

This macro corresponds to the `Tag_CPU_arch_profile` object build
attribute. It may be useful to writers of system code. It is expected in
most cases programmers will use more feature-specific tests.

The macro is undefined for architectural targets which predate the use
of architectural profiles.

### Unaligned access supported in hardware

`__ARM_FEATURE_UNALIGNED` is defined if the target supports unaligned
access in hardware, at least to the extent of being able to load or
store an integer word at any alignment with a single instruction. (There
may be restrictions on load-multiple and floating-point accesses.) Note
that whether a code generation target permits unaligned access will in
general depend on the settings of system register bits, so an
implementation should define this macro to match the user's expectations
and intentions. For example, a command-line option might be provided to
disable the use of unaligned access, in which case this macro would not
be defined.

### LDREX/STREX

This feature was deprecated in ACLE 2.0. It is strongly recommended that
C11/C++11 atomics be used instead.  (See also [Synchronization, barrier,
and hint intrinsics](#synchronization-barrier-and-hint-intrinsics).)

`__ARM_FEATURE_LDREX` is defined if the load/store-exclusive
instructions (LDREX/STREX) are supported. Its value is a set of bits
indicating available widths of the access, as powers of 2. The following
bits are used:

| **Bit** | **Value** | **Access width** | **Instruction** |
| ------- | --------- | ---------------- | --------------- |
| 0       | 0x01      | byte             | LDREXB/STREXB   |
| 1       | 0x02      | halfword         | LDREXH/STREXH   |
| 2       | 0x04      | word             | LDREX/STREX     |
| 3       | 0x08      | doubleword       | LDREXD/STREXD   |

Other bits are reserved.

The following values of `__ARM_FEATURE_LDREX` may occur:

| **Macro value** | **Access widths**                | **Example architecture** |
| --------------- | -------------------------------- | ------------------------ |
| (undefined)     | none                             | Armv5, Armv6-M           |
| 0x04            | word                             | Armv6                    |
| 0x07            | word, halfword, byte             | Armv7-M                  |
| 0x0F            | doubleword, word, halfword, byte | Armv6K, Armv7-A/R        |

Other values are reserved.

The LDREX/STREX instructions are introduced in recent versions of the
Arm architecture and supersede the SWP instruction. Where both are
available, Arm strongly recommends programmers to use LDREX/STREX rather
than SWP. Note that platforms may choose to make SWP unavailable in user
mode and emulate it through a trap to a platform routine, or fault it.

### CLZ

`__ARM_FEATURE_CLZ` is defined to 1 if the CLZ (count leading zeros)
instruction is supported in hardware. Note that ACLE provides the
`__clz()` family of intrinsics (see [Miscellaneous data-processing
intrinsics](#miscellaneous-data-processing-intrinsics)) even
when `__ARM_FEATURE_CLZ` is not defined.

### Q (saturation) flag

`__ARM_FEATURE_QBIT` is defined to 1 if the Q (saturation) global flag
exists and the intrinsics defined in [The Q (saturation)
flag](#the-q-saturation-flag) are available. This
flag is used with the DSP saturating-arithmetic instructions (such
as QADD) and the width-specified saturating instructions (SSAT and USAT).
Note that either of these classes of instructions may exist without the
other: for example, v5E has only QADD while v7-M has only SSAT.

Intrinsics associated with the Q-bit and their feature macro
`__ARM_FEATURE_QBIT` are deprecated in ACLE 2.0 for A-profile. They
are fully supported for M-profile and R-profile. This macro is defined
for AArch32 only.

### DSP instructions

`__ARM_FEATURE_DSP` is defined to 1 if the DSP (v5E) instructions are
supported and the intrinsics defined in [Saturating
intrinsics](#saturating-intrinsics) are available. These instructions include
QADD, SMULBB and others. This feature also implies support for the Q flag.

`__ARM_FEATURE_DSP` and its associated intrinsics are deprecated in
ACLE 2.0 for A-profile. They are fully supported for M and R-profiles.
This macro is defined for AArch32 only.

### Saturation instructions

`__ARM_FEATURE_SAT` is defined to 1 if the SSAT and USAT instructions
are supported and the intrinsics defined in [Width-specified saturation
intrinsics](#width-specified-saturation-intrinsics) are available. This
feature also implies support for the Q flag.

`__ARM_FEATURE_SAT` and its associated intrinsics are deprecated in
ACLE 2.0 for A-profile. They are fully supported for M and R-profiles.
This macro is defined for AArch32 only.

<span id="32-bit-simd-instructions"></span>

### 32-bit SIMD instructions

`__ARM_FEATURE_SIMD32` is defined to 1 if the 32-bit SIMD instructions
are supported and the intrinsics defined in
[32-bit SIMD Operations](#32-bit-simd-operations) are available. This also
implies support for the GE global flags which indicate byte-by-byte
comparison results.

`__ARM_FEATURE_SIMD32` is deprecated in ACLE 2.0 for A-profile. Users
are encouraged to use Neon Intrinsics as an equivalent for the 32-bit
SIMD intrinsics functionality. However they are fully supported for M
and R-profiles. This is defined for AArch32 only.

### Hardware integer divide

`__ARM_FEATURE_IDIV` is defined to 1 if the target has hardware
support for 32-bit integer division in all available instruction sets.
Signed and unsigned versions are both assumed to be available. The
intention is to allow programmers to choose alternative algorithm
implementations depending on the likely speed of integer division.

Some older R-profile targets have hardware divide available in the T32
instruction set only. This can be tested for using the following test:

``` c
    #if __ARM_FEATURE_IDIV || (__ARM_ARCH_PROFILE == 'R')
```

### CRC32 extension

`__ARM_FEATURE_CRC32` is defined to 1 if the CRC32 instructions are
supported and the intrinsics defined in [CRC32 intrinsics](#crc32-intrinsics)
are available. These instructions include CRC32B, CRC32H and others.
This is only available when `__ARM_ARCH >= 8`.

### Random Number Generation Extension

`__ARM_FEATURE_RNG` is defined to 1 if the Random Number Generation
instructions are supported and the intrinsics defined in
[Random number generation intrinsics](#random-number-generation-intrinsics)
are available.

### Branch Target Identification

`__ARM_FEATURE_BTI_DEFAULT` is defined to 1 if the Branch Target
Identification extension is used to protect branch destinations by default.
The protection applied to any particular function may be overridden by
mechanisms such as function attributes.

`__ARM_FEATURE_BTI` is defined to 1 if Branch Target Identification
extension is available on the target. It is undefined otherwise.

### Pointer Authentication

`__ARM_FEATURE_PAC_DEFAULT` is defined as a bitmap to indicate the use of the
Pointer Authentication extension to protect code against code reuse attacks
by default.
The bits are defined as follows:

| **Bit** | **Meaning**                          |
| ------- | ------------------------------------ |
| 0       | Protection using the A key           |
| 1       | Protection using the B key           |
| 2       | Protection including leaf functions  |
| 3       | Protection using PC as a diversifier |

For example, a value of `0x5` indicates that the Pointer Authentication
extension is used to protect function entry points, including leaf functions,
using the A key for signing.
The protection applied to any particular function may be overridden by
mechanisms such as function attributes.

`__ARM_FEATURE_PAUTH` is defined to 1 if Pointer Authentication extension
(FEAT_PAuth) is available on the target. It is undefined otherwise.

`__ARM_FEATURE_PAUTH_LR` is defined to 1 if Armv9.5-A enhancements to the
Pointer Authentication extension (FEAT_PAuth_LR) are available on the target.
It is undefined otherwise.

### Guarded Control Stack

`__ARM_FEATURE_GCS_DEFAULT` is defined to `1` if the code generation is
compatible with enabling the Guarded Control Stack (GCS) extension based
protection. It is undefined otherwise.

`__ARM_FEATURE_GCS` is defined to `1` if the Guarded Control Stack (GCS)
extension is available on the target. It is undefined otherwise.

### Large System Extensions

`__ARM_FEATURE_ATOMICS` is defined if the Large System Extensions introduced in
the Armv8.1-A [[ARMARMv81]](#ARMARMv81) architecture are supported on this target.
Note: It is strongly recommended that standardized C11/C++11 atomics are used to
implement atomic operations in user code.

### Load and Store Consistency Pair instructions

`__ARM_FEATURE_LSCP` is defined to 1 if the Load and Store Consistency
Pair instructions (FEAT_LSCP) are supported on this target. It is undefined
otherwise.

### Armv8.7-A Load/Store 64 Byte extension

`__ARM_FEATURE_LS64` is defined to 1 if the Armv8.7-A `LD64B`,
`ST64B`, `ST64BV` and `ST64BV0` instructions for atomic 64-byte
access to device memory are supported.
This macro may only ever be defined in the AArch64 execution state.
Intrinsics for using these instructions are specified in
[Load/store 64 Byte intrinsics](#loadstore-64-byte-intrinsics).

### memcpy family of memory operations standardization instructions - MOPS

If the `CPYF*`, `CPY*`, `SET*` and `SETG*` instructions are supported,
`__ARM_FEATURE_MOPS` is defined to 1. These instructions were
introduced in the Armv8.8-A and Armv9.3-A architecture updates for
standardization of `memcpy`, `memset`, and `memmove` family of memory
operations (MOPS).

The `__ARM_FEATURE_MOPS` macro can only be implemented in the AArch64
execution state. Intrinsics for the use of these instructions are
specified in [memcpy family of operations intrinsics -
MOPS](#memcpy-family-of-operations-intrinsics---mops)

### RCPC

`__ARM_FEATURE_RCPC` is set if the weaker RCpc (Release Consistent
processor consistent) model is supported. It is undefined otherwise.
The value indicates the set of Load-Acquire and Store-Release
instructions available. The intention is to allow programmers to guard
the usage of these instructions in inline assembly.

If defined, the value of `__ARM_FEATURE_RCPC` remains consistent with the decimal
value of `LRCPC` field (bits [23:20]) in the `ID_AA64ISAR1_EL1` register.
For convenience these are shown below:

| **Value** | **Feature** | **Instructions**                | **Availability**          |
| --------- | ----------- | ------------------------------- | ------------------------- |
| 1         | FEAT_LRCPC  | LDAPR* instructions             | Armv8.3, optional Armv8.2 |
| 2         | FEAT_LRCPC2 | LDAPUR* and STLUR* instructions | Armv8.4, optional Armv8.2 |
| 3         | FEAT_LRCPC3 | See FEAT_LRCPC3 documentation   | Armv8.9, optional Armv8.2 |

The `__ARM_FEATURE_RCPC` macro can only be implemented in the AArch64
execution state.

### 128-bit system registers

If the `MRRS` and `MSRR` instructions are supported, `__ARM_FEATURE_SYSREG128`
is defined to 1. These instructions were introduced in the Armv9.4-A
architecture updates to support 128-bit system register accesses.

The `__ARM_FEATURE_SYSREG128` macro can only be implemented in the AArch64
execution state. Intrinsics for the use of these instructions are specified in
[Special register intrinsics](#special-register-intrinsics).

### Producer-consumer data placement hints

`__ARM_FEATURE_PCDPHINT` is defined to `1` if the producer-consumer
data placement hints (FEAT_PCDPHINT) instructions and their associated
intrinsics are available on the target.

### Contention Management hints

`__ARM_FEATURE_CMH` is defined to `1` if the Contention Management hints
(FEAT_CMH) instructions and their associated intrinsics are available on the target.

## Floating-point and vector hardware

### Hardware floating point

`__ARM_FP` is set if hardware floating-point is available. The value is
a set of bits indicating the floating-point precisions supported. The
following bits are used:

| **Bit** | **Value** | **Precision**                |
| ------- | --------- | ---------------------------- |
| 1       | 0x02      | half (16-bit) data type only |
| 2       | 0x04      | single (32-bit)              |
| 3       | 0x08      | double (64-bit)              |

Bits 0 and 4..31 are reserved

Currently, the following values of `__ARM_FP` may occur (assuming the
processor configuration option for hardware floating-point support is
selected where available):

| **Value**   | **Precisions**       | **Example processor**                                 |
| ----------- | -------------------- | ----------------------------------------------------- |
| (undefined) | none                 | any processor without hardware floating-point support |
| 0x04        | single               | Cortex-R5 when configured with SP only                |
| 0x06        | single, half         | Cortex-M4.fp                                          |
| 0x0C        | double, single       | Arm9, Arm11, Cortex-A8, Cortex-R4                     |
| 0x0E        | double, single, half | Cortex-A9, Cortex-A15, Cortex-R7                      |

Other values are reserved.

Standard C implementations support single and double precision
floating-point irrespective of whether floating-point hardware is
available. However, an implementation might choose to offer a mode to
diagnose or fault use of floating-point arithmetic at a precision not
supported in hardware.

Support for 16-bit floating-point language or 16-bit brain floating-point
language extensions (see [Half-precision (16-bit) floating-point
format](#half-precision-16-bit-floating-point-format) and [Brain
16-bit floating-point support](#brain-16-bit-floating-point-support))
is only required if supported in hardware.

### Half-precision (16-bit) floating-point format

`__ARM_FP16_FORMAT_IEEE` is defined to 1 if the IEEE 754-2008
[[IEEE-FP]](#IEEE-FP) 16-bit floating-point format is used.

`__ARM_FP16_FORMAT_ALTERNATIVE` is defined to 1 if the Arm
alternative [[ARMARM]](#ARMARM) 16-bit floating-point format is used. This format
removes support for infinities and NaNs in order to provide an
additional binade.

At most one of these macros will be defined. See [Half-precision
floating-point](#half-precision-floating-point) for details of
half-precision floating-point types.

### Half-precision argument and result

`__ARM_FP16_ARGS` is defined to 1 if `__fp16` can be used as an
argument and result.

### Vector extensions

#### Advanced SIMD architecture extension (Neon)

`__ARM_NEON` is defined to a value indicating the Advanced SIMD (Neon)
architecture supported. The only current value is 1.

In principle, for AArch32, the Neon architecture can exist in an
integer-only version. To test for the presence of Neon floating-point
vector instructions, test `__ARM_NEON_FP`. When Neon does occur in an
integer-only version, the VFP scalar instruction set is also not
present. See [[ARMARM]](#ARMARM) (table A2-4) for architecturally permitted
combinations.

`__ARM_NEON` is always set to 1 for AArch64.

#### Neon floating-point

`__ARM_NEON_FP` is defined as a bitmap to indicate floating-point
support in the Neon architecture. The meaning of the values is the same
as for `__ARM_FP`. This macro is undefined when the Neon extension is
not present or does not support floating-point.

Current AArch32 Neon implementations do not support double-precision
floating-point even when it is present in VFP. 16-bit floating-point
format is supported in Neon if and only if it is supported in VFP.
Consequently, the definition of `__ARM_NEON_FP` is the same as
`__ARM_FP` except that the bit to indicate double-precision is not set
for AArch32. Double-precision is always set for AArch64.

If `__ARM_FEATURE_FMA` and `__ARM_NEON_FP` are both defined,
fused-multiply instructions are available in Neon also.

#### Scalable Vector Extension (SVE)

`__ARM_FEATURE_SVE` is defined to 1 if there is hardware support
for the FEAT_SVE instructions and if the associated [ACLE
features](#sve-language-extensions-and-intrinsics) are available.
This implies that `__ARM_NEON` and `__ARM_NEON_FP` are both nonzero.

The following macros indicate the presence of various optional
SVE language extensions:

**`__ARM_FEATURE_SVE_BITS==N`**

> When N is nonzero, this indicates that the implementation is generating
> code for an N-bit SVE target and that the implementation supports the
> `arm_sve_vector_bits(N)` attribute. N may also be zero, but this carries
> the same meaning as not defining the macro. See
> [The __ARM_FEATURE_SVE_BITS macro](#the-__arm_feature_sve_bits-macro)
> for details.

**`__ARM_FEATURE_SVE_VECTOR_OPERATORS==N`**

> `N >= 1` indicates that applying the `arm_sve_vector_bits` attribute
> to an SVE vector type creates a type that supports the GNU vector
> extensions. This condition is only meaningful when
> `__ARM_FEATURE_SVE_BITS` is nonzero. See [`arm_sve_vector_bits` behavior
> specific to vectors](#arm_sve_vector_bits-behavior-specific-to-vectors)
> for details.

> `N >= 2` indicates that the operators outlined in the GNU vector
> extensions additionally work on sizeless SVE vector types like `svint32_t`.
> The availability of operators on sizeless types is independent of
> `__ARM_FEATURE_SVE_BITS`.

**`__ARM_FEATURE_SVE_PREDICATE_OPERATORS==N`**

> `N >= 1` indicates that applying the `arm_sve_vector_bits` attribute to
> `svbool_t` creates a type that supports basic built-in vector operations.
> The state of this macro is only meaningful when `__ARM_FEATURE_SVE_BITS`
> is nonzero. See [`arm_sve_vector_bits` behavior specific to
> predicates](#arm_sve_vector_bits-behavior-specific-to-predicates)
> for details.

> `N >= 2` indicates that the built-in vector operations described above
> additionally work on `svbool_t`.
> The availability of operators on `svbool_t` is independent of
> `__ARM_FEATURE_SVE_BITS`.

#### SVE2

`__ARM_FEATURE_SVE2` is defined to 1 if there is hardware support for
the Armv9-A SVE2 extension (FEAT_SVE2) and if the associated ACLE intrinsics
are available. This implies that `__ARM_FEATURE_SVE` is nonzero.

`__ARM_FEATURE_SVE2p1` is defined to 1 if the FEAT_SVE2p1 instructions
 are available and if the associated [ACLE features]
(#sme-language-extensions-and-intrinsics) are supported.

`__ARM_FEATURE_SVE2p2` is defined to 1 if the FEAT_SVE2p2 instructions
 are available and if the associated [ACLE features]
(#sme-language-extensions-and-intrinsics) are supported.

`__ARM_FEATURE_SVE2p3` is defined to 1 if the FEAT_SVE2p3 instructions
 are available and if the associated [ACLE features]
(#sme-language-extensions-and-intrinsics) are supported.

#### Neon-SVE Bridge macro

`__ARM_NEON_SVE_BRIDGE` is defined to 1 if the [`<arm_neon_sve_bridge.h>`](#arm_neon_sve_bridge.h)
header file is available.

#### Scalable Matrix Extension (SME)

The specification for SME2.1 is in
[**Beta** state](#support-levels) and the
specification for the rest of SME is in
[**Beta** state](#support-levels).  The
specifications may change or be extended in the future.

ACLE provides [features](#sme-language-extensions-and-intrinsics)
for accessing the Scalable Matrix Extension (SME). Each revision
of SME has an associated preprocessor macro, given in the table below:

| **Feature** | **Macro**                  |
| ----------- | -------------------------- |
| FEAT_SME    | __ARM_FEATURE_SME          |
| FEAT_SME2   | __ARM_FEATURE_SME2         |
| FEAT_SME2p1 | __ARM_FEATURE_SME2p1       |
| FEAT_SME2p2 | __ARM_FEATURE_SME2p2       |
| FEAT_SME2p3 | __ARM_FEATURE_SME2p3       |

Each macro is defined if there is hardware support for the associated
architecture feature and if all of the [ACLE
features](#sme-language-extensions-and-intrinsics) that are conditional
on the macro are supported.

In addition, `__ARM_FEATURE_LOCALLY_STREAMING` is defined to 1 if
the [`arm_locally_streaming`](#arm_locally_streaming) attribute
is available.

#### M-profile Vector Extension

`__ARM_FEATURE_MVE` is defined as a bitmap to indicate M-profile Vector
Extension (MVE) support.

| **Bit** | **Value** | **Support**        |
| ------- | --------- | ------------------ |
| 0       | 0x01      | Integer MVE        |
| 1       | 0x02      | Floating-point MVE |

#### Wireless MMX

If Wireless MMX operations are available on the target, `__ARM_WMMX` is
defined to a value that indicates the level of support, corresponding to
the `Tag_WMMX_arch` build attribute.

This specification does not further define source-language features to
support Wireless MMX.

### 16-bit floating-point extensions

<span id="16-bit-floating-point-data-processing-operations"></span>

#### 16-bit floating-point data processing operations

`__ARM_FEATURE_FP16_SCALAR_ARITHMETIC` is defined to `1` if the
16-bit floating-point arithmetic instructions are supported in hardware and
the associated scalar intrinsics defined by ACLE are available. Note that
this implies:

* `__ARM_FP16_FORMAT_IEEE == 1`
* `__ARM_FP16_FORMAT_ALTERNATIVE == 0`
* `__ARM_FP & 0x02 == 1`

`__ARM_FEATURE_FP16_VECTOR_ARITHMETIC` is defined to `1` if the 16-bit
floating-point arithmetic instructions are supported in hardware and the
associated vector intrinsics defined by ACLE are available. Note that
this implies:

* `__ARM_FP16_FORMAT_IEEE == 1`
* `__ARM_FP16_FORMAT_ALTERNATIVE == 0`
* `__ARM_FP & 0x02 == 1`
* `__ARM_NEON_FP & 0x02 == 1`

#### FP16 FML extension

`__ARM_FEATURE_FP16_FML` is defined to 1 if the FP16 multiplication variant
instructions from Armv8.2-A are supported and intrinsics targeting them are
available. This implies that `__ARM_FEATURE_FP16_SCALAR_ARITHMETIC` is
defined to a nonzero value.

#### Half-precision floating-point SME intrinsics

The specification for SME2.1 is in
[**Beta** state](#support-levels) and might change or be
extended in the future.

`__ARM_FEATURE_SME_F16F16` is defined to `1` if there is hardware support
for the SME2 half-precision (FEAT_SME_F16F16) instructions and if their
associated intrinsics are available.

#### Brain 16-bit floating-point support

`__ARM_BF16_FORMAT_ALTERNATIVE` is defined to 1 if the Arm
alternative [[ARMARM]](#ARMARM) 16-bit brain floating-point format is used. This format
closely resembles the IEEE 754 single-precision format.  As such a brain
half-precision floating point value can be converted to an IEEE 754
single-floating point format by appending 16 zero bits at the end.

`__ARM_FEATURE_BF16_VECTOR_ARITHMETIC` is defined to `1` if there is
hardware support for the Advanced SIMD brain 16-bit floating-point
arithmetic instructions and if the associated ACLE vector intrinsics
are available. This implies:

* `__ARM_FP & 0x02 == 1`
* `__ARM_NEON_FP & 0x02 == 1`

Similarly, `__ARM_FEATURE_SVE_BF16` is defined to `1` if there is hardware
support for the SVE BF16 extensions and if the associated ACLE intrinsics
are available. This implies that `__ARM_FEATURE_BF16_VECTOR_ARITHMETIC`
and `__ARM_FEATURE_SVE` are both nonzero.

See [Half-precision brain
floating-point](#half-precision-brain-floating-point) for details
of half-precision brain floating-point types.

#### Non-widening brain 16-bit floating-point support

The specification for B16B16 is in
[**Beta** state](#support-levels) and might change or be
extended in the future.

`__ARM_FEATURE_SVE_B16B16` is defined to `1` if there is hardware support
for the FEAT_SVE_B16B16 instructions and if their associated intrinsics
are available.  Specifically, if this macro is defined to `1`, then:

*    the SVE subset of the FEAT_SVE_B16B16 intrinsics are available in
     [non-streaming statements](#non-streaming-statement)
     if `__ARM_FEATURE_SVE` is nonzero.

*    the SVE subset of the FEAT_SVE_B16B16 intrinsics are available in
     [streaming-compatible statements](#streaming-compatible-statement)
     if `__ARM_FEATURE_SME` is nonzero.

*    all FEAT_SVE_B16B16 intrinsics are available in
     [streaming statements](#streaming-statement) if `__ARM_FEATURE_SME`
     is nonzero.

`__ARM_FEATURE_SME_B16B16` is defined to `1` if there is hardware support
for the FEAT_SME_B16B16 instructions and if their associated intrinsics
are available.

#### Brain 16-bit floating-point vector multiplication support

This section is in
[**Beta** state](#support-levels) and might change or be
extended in the future.

`__ARM_FEATURE_SVE_BFSCALE` is defined to `1` if there is hardware
support for the SVE BF16 vector multiplication extensions and if the
associated ACLE intrinsics are available.

See [Half-precision brain
floating-point](#half-precision-brain-floating-point) for details
of half-precision brain floating-point types.

#### Brain 16-bit floating-point matrix multiplication support

This section is in
[**Alpha** state](#support-levels) and might change or be
extended in the future.

`__ARM_FEATURE_SVE_B16MM` is defined to `1` if there is hardware
support for the SVE BF16 matrix multiply extension and if the
associated ACLE intrinsics are available.

See [Half-precision brain
floating-point](#half-precision-brain-floating-point) for details
of half-precision brain floating-point types.

### Cryptographic extensions

#### “Crypto” extension

NOTE: The `__ARM_FEATURE_CRYPTO` macro is deprecated in favor of the finer
grained feature macros described below.

`__ARM_FEATURE_CRYPTO` is defined to 1 if the Armv8-A Crypto instructions are
supported and intrinsics targeting them are available. These
instructions include AES{E, D}, SHA1{C, P, M} and others. This also implies
`__ARM_FEATURE_AES` and `__ARM_FEATURE_SHA2`.

#### AES extension

`__ARM_FEATURE_AES` is defined to 1 if there is hardware support for the
Advanced SIMD AES Crypto instructions from Armv8-A and if the associated
ACLE intrinsics are available. These instructions are identified by
`FEAT_AES` and `FEAT_PMULL` in [[ARMARMv8]](#ARMARMv8), and they include
AES{E, D}, AESMC, AESIMC and others.

In addition, `__ARM_FEATURE_SVE2_AES` is defined to `1` if there is hardware
support for the SVE2 AES (FEAT_SVE_AES) instructions and if the associated
ACLE intrinsics are available. This implies that `__ARM_FEATURE_AES`
and `__ARM_FEATURE_SVE2` are both nonzero.

In addition, `__ARM_FEATURE_SVE_AES2` is defined to `1` if there is hardware
support for the SVE AES2 (FEAT_SVE_AES2) instructions and if the associated
ACLE intrinsics are available.

`__ARM_FEATURE_SSVE_AES` is defined to 1 if there is hardware support for
SVE AES2 (FEAT_SVE_AES2) instructions in Streaming SVE mode (FEAT_SSVE_AES)
and if the associated ACLE intrinsics are available.

The specification for SVE AES2 (FEAT_SVE_AES2, FEAT_SSVE_AES) instructions is in
[**Beta** state](#support-levels) and might change or be
extended in the future.

#### SHA2 extension

`__ARM_FEATURE_SHA2` is defined to 1 if the SHA1 & SHA2-256 Crypto
instructions from Armv8-A are supported and intrinsics targeting them
are available. These instructions are identified by `FEAT_SHA1` and
`FEAT_SHA256` in [[ARMARMv8]](#ARMARMv8), and they include SHA1{C, P,
M}, SHA256H, SHA256H2... and others.

#### SHA512 extension

`__ARM_FEATURE_SHA512` is defined to 1 if the SHA2-512 Crypto instructions
from Armv8.2-A are supported and intrinsics targeting them are
available. These instructions are identified by `FEAT_SHA512` in
[[ARMARMv82]](#ARMARMv82), and they include SHA1{C, P, M}, SHA256H,
SHA256H2, ..., SHA512H, SHA512H2, SHA512SU0... and others. Note:
`FEAT_SHA512` requires both `FEAT_SHA1` and `FEAT_SHA256`.

#### SHA3 extension

`__ARM_FEATURE_SHA3` is defined to 1 if there is hardware support for
the Advanced SIMD SHA1 & SHA2 Crypto instructions from Armv8-A and the
SHA2 and SHA3 instructions from Armv8.2-A and newer and if the associated
ACLE intrinsics are available. These instructions include AES{E, D}, SHA1{C,
P, M}, RAX, and others.

In addition, `__ARM_FEATURE_SVE2_SHA3` is defined to `1` if there is hardware
support for the SVE2 SHA3 (FEAT_SVE_SHA3) instructions and if the associated
ACLE intrinsics are available. This implies that `__ARM_FEATURE_SHA3` and
`__ARM_FEATURE_SVE2` are both nonzero.

#### SM3 extension

`__ARM_FEATURE_SM3` is defined to 1 if there is hardware support for
Advanced SIMD SM3 Crypto instructions from Armv8.2-A and if the associated
ACLE intrinsics are available. These instructions include SM3{TT1A,
TT1B}, and others.

In addition, `__ARM_FEATURE_SVE2_SM3` is defined to `1` if there is hardware
support for the SVE2 SM3 (FEAT_SVE_SM3) instructions and if the associated
ACLE intrinsics are available. This implies that `__ARM_FEATURE_SM3` and
`__ARM_FEATURE_SVE2` are both nonzero.

#### SM4 extension

`__ARM_FEATURE_SM4` is defined to 1 if there is hardware support for the
Advanced SIMD SM4 Crypto instructions from Armv8.2-A and if the associated
ACLE intrinsics are available. These instructions include SM4{E, EKEY}
and others.

In addition, `__ARM_FEATURE_SVE2_SM4` is defined to `1` if there is hardware
support for the SVE2 SM4 (FEAT_SVE_SM4) instructions and if the associated
ACLE intrinsics are available. This implies that `__ARM_FEATURE_SM4` and
`__ARM_FEATURE_SVE2` are both nonzero.

### Floating-point absolute minimum and maximum extension

`__ARM_FEATURE_FAMINMAX` is defined to 1 if there is hardware support for
floating-point absolute minimum and maximum instructions (FEAT_FAMINMAX)
and if the associated ACLE intrinsics are available.

### FPRCVT extension

`__ARM_FEATURE_FPRCVT` is defined to `1` if there is hardware
support for floating-point to/from integer conversion instructions
with only scalar SIMD&FP register operands and results, and with
different input and output register sizes.

### Lookup table extensions

`__ARM_FEATURE_LUT` is defined to 1 if there is hardware support for
lookup table instructions with 2-bit and 4-bit indices (FEAT_LUT)
and if the associated ACLE intrinsics are available.

`__ARM_FEATURE_SME_LUTv2` is defined to 1 if there is hardware support for
lookup table instructions with 4-bit indices and 8-bit elements (FEAT_SME_LUTv2)
and if the associated ACLE intrinsics are available.

### Modal 8-bit floating point extensions

`__ARM_FEATURE_FP8` is defined to 1 if there is hardware support for FP8 conversion
instructions (FEAT_FP8) and if the associated ACLE intrinsics are available.

`__ARM_FEATURE_FP8FMA` is defined to 1 if there is hardware support for
FP8 multiply-accumulate to half-precision and single-precision instructions
(FEAT_FP8FMA) and if the associated ACLE intrinsics are available.

`__ARM_FEATURE_FP8DOT2` is defined to 1 if there is hardware support for
FP8 2-way dot product to half-precision instructions (FEAT_FP8DOT2)
and if the associated ACLE intrinsics are available.

`__ARM_FEATURE_FP8DOT4` is defined to 1 if there is hardware support for
FP8 4-way dot product to single-precision instructions (FEAT_FP8DOT4)
and if the associated ACLE intrinsics are available.

`__ARM_FEATURE_SSVE_FP8DOT4` is defined to 1 if there is hardware support for
SVE2 FP8 4-way dot product to single-precision instructions
in Streaming SVE mode (FEAT_SSVE_FP8DOT4) and if the associated ACLE
intrinsics are available.

`__ARM_FEATURE_SSVE_FP8DOT2` is defined to 1 if there is hardware support for
SVE2 FP8 2-way dot product to half-precision instructions
in Streaming SVE mode (FEAT_SSVE_FP8DOT2) and if the associated ACLE intrinsics
are available.

`__ARM_FEATURE_SSVE_FP8FMA` is defined to 1 if there is hardware support for
SVE2 FP8 multiply-accumulate to half-precision and single-precision
instructions in Streaming SVE mode (FEAT_SSVE_FP8FMA) and if the associated
ACLE intrinsics are available.

`__ARM_FEATURE_SME_F8F32` is defined to 1 if there is hardware support for SME2
FP8 dot product, multiply-accumulate, and outer product to single-precision
instructions (FEAT_SME_F8F32) and if the associated ACLE intrinsics are
available.

`__ARM_FEATURE_SME_F8F16` is defined to 1 if there is hardware support for SME2
FP8 dot product, multiply-accumulate, and outer product to half-precision
instructions (FEAT_SME_F8F16) and if the associated ACLE intrinsics are
available.

### Other floating-point and vector extensions

#### Fused multiply-accumulate (FMA)

`__ARM_FEATURE_FMA` is defined to 1 if the hardware floating-point
architecture supports fused floating-point multiply-accumulate, that is,
without intermediate rounding. Note that C implementations are
encouraged [[C99]](#C99) (7.12) to ensure that <math.h> defines `FP_FAST_FMAF` or
`FP_FAST_FMA`, which can be tested by portable C code. A C
implementation on Arm might define these macros by testing
`__ARM_FEATURE_FMA` and `__ARM_FP`.

This macro implies support for floating-point instructions but it
does not in itself imply support for vector instructions.  See [Neon
floating-point](#neon-floating-point) for the conditions under
which vector fused multiply-accumulate operations are available.

#### Directed rounding

`__ARM_FEATURE_DIRECTED_ROUNDING` is defined to 1 if the directed
rounding and conversion vector instructions are supported and rounding
and conversion intrinsics are available. This is only available when
`__ARM_ARCH >= 8`.

#### Armv8.5-A Floating-point rounding extension

`__ARM_FEATURE_FRINT`  is defined to 1 if the Armv8.5-A rounding number
instructions are supported and the scalar and vector intrinsics are available.
This macro may only ever be defined in the AArch64 execution state.
The scalar intrinsics are specified in [Floating-point data-processing
intrinsics](#floating-point-data-processing-intrinsics) and are not expected
to be for general use.  They are defined for uses that require the specialist
rounding behavior of the relevant instructions.
The vector intrinsics are specified in the Arm Neon Intrinsics Reference
Architecture Specification [[Neon]](#Neon).

#### Javascript floating-point conversion

`__ARM_FEATURE_JCVT` is defined to 1 if the FJCVTZS (AArch64)
or VJCVT (AArch32) instruction and the [associated
intrinsic](#floating-point-data-processing-intrinsics) are available.

#### Numeric maximum and minimum

`__ARM_FEATURE_NUMERIC_MAXMIN` is defined to 1 if the IEEE 754-2008
compliant floating point maximum and minimum vector instructions are
supported and intrinsics targeting these instructions are available. This
is only available when `__ARM_ARCH >= 8`.

#### Rounding doubling multiplies

`__ARM_FEATURE_QRDMX` is defined to 1 if SQRDMLAH and SQRDMLSH
instructions and their associated intrinsics are available.

#### Dot Product extension

`__ARM_FEATURE_DOTPROD`  is defined if the dot product data manipulation
instructions are supported and the vector intrinsics are available. Note that
this implies:

  * `__ARM_NEON == 1`

#### Half-precision to single-precision dot product extension

This section is in
[**Alpha** state](#support-levels) and might change or be
extended in the future.

`__ARM_FEATURE_F16F32DOT` is defined if the half-precision dot product
accumulating to single-precision instructions are supported and the vector
intrinsics are available. Note that this implies:

  * `__ARM_NEON == 1`

#### Complex number intrinsics

`__ARM_FEATURE_COMPLEX` is defined if the complex addition and complex
multiply-accumulate vector instructions are supported. Note that this implies:

  * `__ARM_NEON == 1`

These instructions require that the input vectors are organized such that the
real and imaginary parts of the complex number are stored in alternating sequences:
real, imag, real, imag, ... etc.

#### Matrix Multiply Intrinsics

##### Multiplication of 8-bit integer matrices

`__ARM_FEATURE_MATMUL_INT8` is defined to `1` if there is hardware support
for the Advanced SIMD integer matrix multiply instructions are if the
associated ACLE intrinsics are available. This implies that `__ARM_NEON` is
nonzero.

In addition, `__ARM_FEATURE_SVE_MATMUL_INT8` is defined to `1` if there
is hardware support for the SVE forms of these instructions and if the
associated ACLE intrinsics are available. This implies that
`__ARM_FEATURE_MATMUL_INT8` and `__ARM_FEATURE_SVE` are both nonzero.

##### Multiplication of modal 8-bit floating-point matrices

This section is in
[**Beta** state](#support-levels) and might change or be
extended in the future.

`__ARM_FEATURE_F8F16MM` is defined to `1` if there is hardware support
for the Neon and SVE modal 8-bit floating-point matrix multiply-accumulate to half-precision (FEAT_F8F16MM)
instructions and if the associated ACLE intrinsics are available.

`__ARM_FEATURE_F8F32MM` is defined to `1` if there is hardware support
for the Neon and SVE modal 8-bit floating-point matrix multiply-accumulate to single-precision (FEAT_F8F32MM)
instructions and if the associated ACLE intrinsics are available.

##### Multiplication of 16-bit floating-point matrices

`__ARM_FEATURE_SVE_F16F32MM` is defined to `1` if there is hardware support
for the SVE 16-bit floating-point to 32-bit floating-point matrix multiply and add
(FEAT_SVE_F16F32MM) instructions and if the associated ACLE intrinsics are available.

##### Multiplication of 16-bit floating-point matrices (AdvSIMD)

This section is in
[**Alpha** state](#support-levels) and might change or be
extended in the future.

`__ARM_FEATURE_F16F32MM` is defined if the Neon half-precision matrix multiply
accumulating to single-precision instruction is supported. Note that this implies:

  * `__ARM_NEON == 1`

`__ARM_FEATURE_F16MM` is defined if the Neon non-widening half-precision matrix multiply instruction is supported. Note that this implies:

  * `__ARM_NEON == 1`

##### Multiplication of 32-bit floating-point matrices

`__ARM_FEATURE_SVE_MATMUL_FP32` is defined to `1` if there is hardware support
for the SVE 32-bit floating-point matrix multiply (FEAT_F32MM) instructions
and if the associated ACLE intrinsics are available. This implies that
`__ARM_FEATURE_SVE` is nonzero.

##### Multiplication of 64-bit floating-point matrices

`__ARM_FEATURE_SVE_MATMUL_FP64` is defined to `1` if there is hardware support
for the SVE 64-bit floating-point matrix multiply (FEAT_F64MM) instructions
and if the associated ACLE intrinsics are available. This implies that
`__ARM_FEATURE_SVE` is nonzero.

#### Bit permute extension

`__ARM_FEATURE_SVE2_BITPERM` is defined to 1 if there is hardware support for
the SVE2 bit permute (FEAT_SVE_BitPerm) instructions and if the associated
ACLE intrinsics are available. This implies that `__ARM_FEATURE_SVE2` is
nonzero.

`__ARM_FEATURE_SSVE_BITPERM` is defined to 1 if there is hardware support for
the SVE2 bit permute instructions in Streaming SVE mode (FEAT_SSVE_BitPerm) and if the associated ACLE intrinsics are available.

<span id="16-bit-to-64-bit-integer-widening-outer-product-intrinsics"></span>

#### Streaming SVE FEXPA extension

`__ARM_FEATURE_SSVE_FEXPA` is defined to 1 if there is hardware support for the SVE FEXPA instruction in Streaming SVE mode (FEAT_SSVE_FEXPA) and if the associated ACLE intrinsics are available.

#### 16-bit to 64-bit integer widening outer product intrinsics

The specification for SME is in
[**Beta** state](#support-levels) and might change or be
extended in the future.

`__ARM_FEATURE_SME_I16I64` is defined to `1` if there is hardware
support for the SME 16-bit to 64-bit integer widening outer product
(FEAT_SME_I16I64) instructions and if their associated intrinsics are
available. This implies that `__ARM_FEATURE_SME` is nonzero.

#### Double precision floating-point outer product intrinsics

The specification for SME is in
[**Beta** state](#support-levels) and might change or be
extended in the future.

`__ARM_FEATURE_SME_F64F64` is defined to `1` if there is hardware
support for the SME double precision floating-point outer product
(FEAT_SME_F64F64) instructions and if their associated intrinsics are
available. This implies that `__ARM_FEATURE_SME` is nonzero.

#### Structured sparsity outer product intrinsics

The specification for Structured sparsity outer product intrinsics
is in [**Beta** state](#support-levels) and may change or be
extended in the future.

`__ARM_FEATURE_SME_TMOP` is defined to `1` if there is hardware
support for the SME structured sparsity outer product (FEAT_SME_TMOP)
instructions and if their associated intrinsics are
available. This implies that `__ARM_FEATURE_SME2` is nonzero.

#### Quarter-tile outer product intrinsics

The specification for SME is in
[**Beta** state](#support-levels) and may change or be
extended in the future.

`__ARM_FEATURE_SME_MOP4` is defined to `1` if there is hardware
support for the SME quarter-tile outer product (FEAT_SME_MOP4)
instructions and if their associated intrinsics are
available. This implies that `__ARM_FEATURE_SME2` is nonzero.

#### CSSC Extension

`__ARM_FEATURE_CSSC` is defined to `1` if there is hardware
support for common short sequence compression instructions.
This includes the instructions ABS, CNT, CTZ and SMAX, SMIN, UMAX, UMIN
(register/immediate).

## Floating-point model

These macros test the floating-point model implemented by the compiler
and libraries. The model determines the guarantees on arithmetic and
exceptions.

`__ARM_FP_FAST` is defined to 1 if floating-point optimizations may
occur such that the computed results are different from those prescribed
by the order of operations according to the C standard. Examples of such
optimizations would be reassociation of expressions to reduce depth, and
replacement of a division by constant with multiplication by its
reciprocal.

`__ARM_FP_FENV_ROUNDING` is defined to 1 if the implementation allows
the rounding to be configured at runtime using the standard C
fesetround() function and will apply this rounding to future
floating-point operations. The rounding mode applies to both scalar
floating-point and Neon.

The floating-point implementation might or might not support denormal
values. If denormal values are not supported then they are flushed to
zero.

Implementations may also define the following macros in appropriate
floating-point modes:

`__STDC_IEC_559__` is defined if the implementation conforms to IEC
This implies support for floating-point exception status flags,
including the inexact exception. This macro is specified by [[C99]](#C99)
(6.10.8).

`__SUPPORT_SNAN__` is defined if the implementation supports
signaling NaNs. This macro is specified by the C standards proposal
WG14 N965 Optional support for Signaling NaNs. (Note: this was not
adopted into C11.)

## Procedure call standard

`__ARM_PCS` is defined to 1 if the default procedure calling standard
for the translation unit conforms to the base PCS defined in [[AAPCS]](#AAPCS).
This is supported on AArch32 only.

`__ARM_PCS_VFP` is defined to 1 if the default is to pass
floating-point parameters in hardware floating-point registers using the
VFP variant PCS defined in [[AAPCS]](#AAPCS). This is supported on AArch32 only.

`__ARM_PCS_AAPCS64` is defined to 1 if the default procedure calling
standard for the translation unit conforms to the [[AAPCS64]](#AAPCS64).

Note that this should reflect the implementation default for the
translation unit. Implementations which allow the PCS to be set for a
function, class or namespace are not expected to redefine the macro
within that scope.

## Position-independent code

`__ARM_ROPI` is defined to 1 if the translation unit is being compiled in
read-only position independent mode. In this mode, all read-only data and
functions are at a link-time constant offset from the program counter.

`__ARM_RWPI` is defined to 1 if the translation unit is being compiled in
read-write position independent mode. In this mode, all writable data is at a
link-time constant offset from the static base register defined in [[AAPCS]](#AAPCS).

The ROPI and RWPI position independence modes are compatible with each other,
so the `__ARM_ROPI` and `__ARM_RWPI` macros may be defined at the same
time.

## Coprocessor intrinsics

`__ARM_FEATURE_COPROC` is defined as a bitmap to indicate the presence of
coprocessor intrinsics for the target architecture. If `__ARM_FEATURE_COPROC`
is undefined or zero, that means there is no support for coprocessor intrinsics
on the target architecture. The following bits are used:

| **Bit** | **Value** | **Intrinsics Available**                                                                |
| ------- | --------- | --------------------------------------------------------------------------------------- |
| 0       | 0x1       | __arm_cdp __arm_ldc, __arm_ldcl, __arm_stc, __arm_stcl, __arm_mcr and __arm_mrc         |
| 1       | 0x2       | __arm_cdp2, __arm_ldc2, __arm_stc2, __arm_ldc2l, __arm_stc2l, __arm_mcr2 and __arm_mrc2 |
| 2       | 0x4       | __arm_mcrr and __arm_mrrc                                                               |
| 3       | 0x8       | __arm_mcrr2 and __arm_mrrc2                                                             |

## Custom Datapath Extension

`__ARM_FEATURE_CDE` is defined to 1 if the Arm Custom Datapath Extension
(CDE) is supported.

`__ARM_FEATURE_CDE_COPROC` is a bitmap indicating the CDE coprocessors
available.  The following bits are used:

| **Bit** | **Value** | **CDE Coprocessor available**     |
| ------- | --------- | --------------------------------- |
| 0       | 0x01      | `p0`                              |
| 1       | 0x02      | `p1`                              |
| 2       | 0x04      | `p2`                              |
| 3       | 0x08      | `p3`                              |
| 4       | 0x10      | `p4`                              |
| 5       | 0x20      | `p5`                              |
| 6       | 0x40      | `p6`                              |
| 7       | 0x80      | `p7`                              |

## Mapping of object build attributes to predefines

This section is provided for guidance. Details of build attributes can
be found in [[BA]](#BA).

| **Tag no.**              | **Tag**                      | **Predefined macro**              |
| ------------------------ | ---------------------------- | --------------------------------- |
| 6                        | `Tag_CPU_arch`               | `__ARM_ARCH`, `__ARM_FEATURE_DSP` |
| 7                        | `Tag_CPU_arch_profile`       | `__ARM_PROFILE`                   |
| 8                        | `Tag_ARM_ISA_use`            | `__ARM_ISA_ARM`                   |
| 9                        | `Tag_THUMB_ISA_use`          | `__ARM_ISA_THUMB`                 |
| 11                       | `Tag_WMMX_arch`              | `__ARM_WMMX`                      |
| 18                       | `Tag_ABI_PCS_wchar_t`        | `__ARM_SIZEOF_WCHAR_T`            |
| 20                       | `Tag_ABI_FP_denormal`        |                                   |
| 21                       | `Tag_ABI_FP_exceptions`      |                                   |
| 22                       | `Tag_ABI_FP_user_exceptions` |                                   |
| 23                       | `Tag_ABI_FP_number_model`    |                                   |
| 26                       | `Tag_ABI_enum_size`          | `__ARM_SIZEOF_MINIMAL_ENUM`       |
| 34                       | `Tag_CPU_unaligned_access`   | `__ARM_FEATURE_UNALIGNED`         |
| 36                       | `Tag_FP_HP_extension`        | `__ARM_FP16_FORMAT_IEEE`          |
|                          |                              | `__ARM_FP16_FORMAT_ALTERNATIVE`   |
| 38                       | `Tag_ABI_FP_16bit_for`       | `__ARM_FP16_FORMAT_IEEE`          |
|                          |                              | `__ARM_FP16_FORMAT_ALTERNATIVE`   |

## Summary of predefined macros

| **Macro name**                                                                                                                                          | **Meaning**                                                                                        | **Example** |
|---------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------|-------------|
| [`__ARM_32BIT_STATE`](#instruction-set-architecture-a32t32a64)                                                                                          | Code is for AArch32 state                                                                          | 1           |
| [`__ARM_64BIT_STATE`](#instruction-set-architecture-a32t32a64)                                                                                          | Code is for AArch64 state                                                                          | 1           |
| [`__ARM_ACLE`](#testing-for-arm-c-language-extensions)                                                                                                  | Indicates ACLE implemented                                                                         | 101         |
| [`__ARM_ALIGN_MAX_PWR`](#alignment-of-static-objects)                                                                                                   | Log of maximum alignment of static object                                                          | 20          |
| [`__ARM_ALIGN_MAX_STACK_PWR`](#alignment-of-stack-objects)                                                                                              | Log of maximum alignment of stack object                                                           | 3           |
| [`__ARM_ARCH`](#arm-architecture-level)                                                                                                                 | Arm architecture level                                                                             | 7           |
| [`__ARM_ARCH_ISA_A64`](#instruction-set-architecture-a32t32a64)                                                                                         | AArch64 ISA present                                                                                | 1           |
| [`__ARM_ARCH_ISA_ARM`](#instruction-set-architecture-a32t32a64)                                                                                         | Arm instruction set present                                                                        | 1           |
| [`__ARM_ARCH_ISA_THUMB`](#instruction-set-architecture-a32t32a64)                                                                                       | T32 instruction set present                                                                        | 2           |
| [`__ARM_ARCH_PROFILE`](#architectural-profile-a-r-m-or-pre-cortex)                                                                                      | Architecture profile                                                                               | `'A'`       |
| [`__ARM_BF16_FORMAT_ALTERNATIVE`](#brain-16-bit-floating-point-support)                                                                                 | 16-bit brain floating-point, alternative format                                                    | 1           |
| [`__ARM_BIG_ENDIAN`](#endianness)                                                                                                                       | Memory is big-endian                                                                               | 1           |
| [`__ARM_FEATURE_AES`](#aes-extension)                                                                                                                   | AES Crypto extension (Arm v8-A)                                                                    | 1           |
| [`__ARM_FEATURE_ATOMICS`](#large-system-extensions)                                                                                                     | Large System Extensions                                                                            | 1           |
| [`__ARM_FEATURE_BF16`](#brain-16-bit-floating-point-support)                                                                                            | 16-bit brain floating-point, vector instruction                                                    | 1           |
| [`__ARM_FEATURE_BTI_DEFAULT`](#branch-target-identification)                                                                                            | Branch Target Identification                                                                       | 1           |
| [`__ARM_FEATURE_CDE`](#custom-datapath-extension)                                                                                                       | Custom Datapath Extension                                                                          | 0x01        |
| [`__ARM_FEATURE_CDE_COPROC`](#custom-datapath-extension)                                                                                                | Custom Datapath Extension                                                                          | 0xf         |
| [`__ARM_FEATURE_CLZ`](#clz)                                                                                                                             | CLZ instruction                                                                                    | 1           |
| [`__ARM_FEATURE_CMH`](#contention-management-hints)                                                                                                     | Contention management hints                                                                        | 1           |
| [`__ARM_FEATURE_COMPLEX`](#complex-number-intrinsics)                                                                                                   | Armv8.3-A extension                                                                                | 1           |
| [`__ARM_FEATURE_COPROC`](#coprocessor-intrinsics)                                                                                                       | Coprocessor Intrinsics                                                                             | 1           |
| [`__ARM_FEATURE_CRC32`](#crc32-extension)                                                                                                               | CRC32 extension                                                                                    | 1           |
| [`__ARM_FEATURE_CRYPTO`](#crypto-extension)                                                                                                             | Crypto extension                                                                                   | 1           |
| [`__ARM_FEATURE_CSSC`](#cssc-extension)                                                                                                                 | CSSC extension                                                                                     | 1           |
| [`__ARM_FEATURE_DIRECTED_ROUNDING`](#directed-rounding)                                                                                                 | Directed Rounding                                                                                  | 1           |
| [`__ARM_FEATURE_DOTPROD`](#availability-of-dot-product-intrinsics)                                                                                      | Dot product extension (ARM v8.2-A)                                                                 | 1           |
| [`__ARM_FEATURE_DSP`](#dsp-instructions)                                                                                                                | DSP instructions (Arm v5E) (32-bit-only)                                                           | 1           |
| [`__ARM_FEATURE_F16F32DOT`](#half-precision-to-single-precision-dot-product-extension)                                                                  | Half-precision to single-precision dot product extension (FEAT_F16F32DOT)                          | 1           |
| [`__ARM_FEATURE_F16F32MM`](#multiplication-of-16-bit-floating-point-matrices-advsimd)                                                                   | Half-precision to single-precision matrix multiply accumulating extension (FEAT_F16F32MM).         | 1           |
| [`__ARM_FEATURE_F16MM`](#multiplication-of-16-bit-floating-point-matrices-advsimd)                                                                      | Half-precision matrix multiply accumulating extension (FEAT_F16MM)                                 | 1           |
| [`__ARM_FEATURE_FAMINMAX`](#floating-point-absolute-minimum-and-maximum-extension)                                                                      | Floating-point absolute minimum and maximum extension                                              | 1           |
| [`__ARM_FEATURE_FMA`](#fused-multiply-accumulate-fma)                                                                                                   | Floating-point fused multiply-accumulate                                                           | 1           |
| [`__ARM_FEATURE_FP16_FML`](#fp16-fml-extension)                                                                                                         | FP16 FML extension (Arm v8.4-A, optional Armv8.2-A, Armv8.3-A)                                     | 1           |
| [`__ARM_FEATURE_FP8`](#modal-8-bit-floating-point-extensions)                                                                                           | Modal 8-bit floating-point extensions                                                              | 1           |
| [`__ARM_FEATURE_FP8DOT2`](#modal-8-bit-floating-point-extensions)                                                                                       | Modal 8-bit floating-point extensions                                                              | 1           |
| [`__ARM_FEATURE_FP8DOT4`](#modal-8-bit-floating-point-extensions)                                                                                       | Modal 8-bit floating-point extensions                                                              | 1           |
| [`__ARM_FEATURE_FP8FMA`](#modal-8-bit-floating-point-extensions)                                                                                        | Modal 8-bit floating-point extensions                                                              | 1           |
| [`__ARM_FEATURE_FPRCVT`](#fprcvt-extension)                                                                                                             | FPRCVT extension                                                                                   | 1           |
| [`__ARM_FEATURE_FRINT`](#availability-of-armv8.5-a-floating-point-rounding-intrinsics)                                                                  | Floating-point rounding extension (Arm v8.5-A)                                                     | 1           |
| [`__ARM_FEATURE_GCS`](#guarded-control-stack)                                                                                                           | Guarded Control Stack                                                                              | 1           |
| [`__ARM_FEATURE_GCS_DEFAULT`](#guarded-control-stack)                                                                                                   | Guarded Control Stack protection can be enabled                                                    | 1           |
| [`__ARM_FEATURE_IDIV`](#hardware-integer-divide)                                                                                                        | Hardware Integer Divide                                                                            | 1           |
| [`__ARM_FEATURE_JCVT`](#javascript-floating-point-conversion)                                                                                           | Javascript conversion (ARMv8.3-A)                                                                  | 1           |
| [`__ARM_FEATURE_LDREX`](#ldrexstrex) *(Deprecated)*                                                                                                     | Load/store exclusive instructions                                                                  | 0x0F        |
| [`__ARM_FEATURE_LSCP`](#load-and-store-consistency-pair-instructions)                                                                                   | Load and Store Consistency Pair instructions (FEAT_LSCP)                                           | 1           |
| [`__ARM_FEATURE_LUT`](#lookup-table-extensions)                                                                                                         | Lookup table extensions (FEAT_LUT)                                                                 | 1           |
| [`__ARM_FEATURE_MATMUL_INT8`](#availability-of-armv8.6-a-integer-matrix-multiply-intrinsics)                                                            | Integer Matrix Multiply extension (Armv8.6-A, optional Armv8.2-A, Armv8.3-A, Armv8.4-A, Armv8.5-A) | 1           |
| [`__ARM_FEATURE_MEMORY_TAGGING`](#memory-tagging)                                                                                                       | Memory Tagging (Armv8.5-A)                                                                         | 1           |
| [`__ARM_FEATURE_MOPS`](#memcpy-family-of-memory-operations-standardization-instructions---mops)                                                        | `memcpy`, `memset`, and `memmove` family of operations standardization instructions               | 1           |
| [`__ARM_FEATURE_MVE`](#m-profile-vector-extension)                                                                                                      | M-profile Vector Extension                                                                         | 1           |
| [`__ARM_FEATURE_NUMERIC_MAXMIN`](#numeric-maximum-and-minimum)                                                                                          | Numeric Maximum and Minimum                                                                        | 1           |
| [`__ARM_FEATURE_PAC_DEFAULT`](#pointer-authentication)                                                                                                  | Pointer authentication protection                                                                  | 0x5         |
| [`__ARM_FEATURE_PAUTH`](#pointer-authentication)                                                                                                        | Pointer Authentication Extension (FEAT_PAuth)                                                      | 1           |
| [`__ARM_FEATURE_PAUTH_LR`](#pointer-authentication)                                                                                                     | Armv9.5-A Enhancements to Pointer Authentication Extension (FEAT_PAuth_LR)                         | 1           |
| [`__ARM_FEATURE_PCDPHINT`](#producer-consumer-data-placement-hints)                                                                                     | Producer-consumer data placement hint instructions (FEAT_PCDPHINT)                                 | 1           |
| [`__ARM_FEATURE_QBIT`](#q-saturation-flag)                                                                                                              | Q (saturation) flag (32-bit-only)                                                                  | 1           |
| [`__ARM_FEATURE_QRDMX`](#rounding-doubling-multiplies)                                                                                                  | SQRDMLxH instructions and associated intrinsics availability                                       | 1           |
| [`__ARM_FEATURE_RCPC`](#rcpc)                                                                                                                           | Release Consistent processor consistent Model (64-bit-only)                      | 1           |
| [`__ARM_FEATURE_RNG`](#random-number-generation-extension)                                                                                              | Random Number Generation Extension (Armv8.5-A)                                                     | 1           |
| [`__ARM_FEATURE_SAT`](#saturation-instructions)                                                                                                         | Width-specified saturation instructions (32-bit-only)                                              | 1           |
| [`__ARM_FEATURE_SHA2`](#sha2-extension)                                                                                                                 | SHA2 Crypto extension (Arm v8-A)                                                                   | 1           |
| [`__ARM_FEATURE_SHA3`](#sha3-extension)                                                                                                                 | SHA3 Crypto extension (Arm v8.4-A)                                                                 | 1           |
| [`__ARM_FEATURE_SHA512`](#sha512-extension)                                                                                                             | SHA2 Crypto ext. (Arm v8.4-A, optional Armv8.2-A, Armv8.3-A)                                       | 1           |
| [`__ARM_FEATURE_SIMD32`](#32-bit-simd-instructions)                                                                                                     | 32-bit SIMD instructions (Armv6) (32-bit-only)                                                     | 1           |
| [`__ARM_FEATURE_SM3`](#sm3-extension)                                                                                                                   | SM3 Crypto extension (Arm v8.4-A, optional Armv8.2-A, Armv8.3-A)                                   | 1           |
| [`__ARM_FEATURE_SM4`](#sm4-extension)                                                                                                                   | SM4 Crypto extension (Arm v8.4-A, optional Armv8.2-A, Armv8.3-A)                                   | 1           |
| [`__ARM_FEATURE_SME`](#scalable-matrix-extension-sme)                                                                                                   | Scalable Matrix Extension (FEAT_SME)                                                               | 1           |
| [`__ARM_FEATURE_SME2`](#scalable-matrix-extension-sme)                                                                                                  | Scalable Matrix Extension (FEAT_SME2)                                                              | 1           |
| [`__ARM_FEATURE_SME_B16B16`](#non-widening-brain-16-bit-floating-point-support)                                                                         | Non-widening brain 16-bit floating-point SME intrinsics (FEAT_SME_B16B16)                          | 1           |
| [`__ARM_FEATURE_SME_F16F16`](#half-precision-floating-point-sme-intrinsics)                                                                             | Half-precision floating-point SME intrinsics (FEAT_SME_F16F16)                                     | 1           |
| [`__ARM_FEATURE_SME_F64F64`](#double-precision-floating-point-outer-product-intrinsics)                                                                 | Double precision floating-point outer product intrinsics (FEAT_SME_F64F64)                         | 1           |
| [`__ARM_FEATURE_SME_F8F16`](#modal-8-bit-floating-point-extensions)                                                                                     | Modal 8-bit floating-point extensions                                                              | 1           |
| [`__ARM_FEATURE_SME_F8F32`](#modal-8-bit-floating-point-extensions)                                                                                     | Modal 8-bit floating-point extensions                                                              | 1           |
| [`__ARM_FEATURE_SME_I16I64`](#16-bit-to-64-bit-integer-widening-outer-product-intrinsics)                                                               | 16-bit to 64-bit integer widening outer product intrinsics (FEAT_SME_I16I64)                       | 1           |
| [`__ARM_FEATURE_SME_TMOP`](#structured-sparsity-outer-product-intrinsics)                                                                               | Structured sparsity outer product intrinsics (FEAT_SME_TMOP)                                       | 1           |
| [`__ARM_FEATURE_SME_MOP4`](#quarter-tile-outer-product-intrinsics)                                                                                      | quarter-tile outer product intrinsics (FEAT_SME_MOP4)                                              | 1           |
| [`__ARM_FEATURE_SME_LOCALLY_STREAMING`](#scalable-matrix-extension-sme)                                                                                 | Support for the `arm_locally_streaming` attribute                                                  | 1           |
| [`__ARM_FEATURE_SME_LUTv2`](#lookup-table-extensions)                                                                                                   | Lookup table extensions (FEAT_SME_LUTv2)                                                           | 1           |
| [`__ARM_FEATURE_SSVE_FP8DOT2`](#modal-8-bit-floating-point-extensions)                                                                                  | Modal 8-bit floating-point extensions                                                              | 1           |
| [`__ARM_FEATURE_SSVE_FP8DOT4`](#modal-8-bit-floating-point-extensions)                                                                                  | Modal 8-bit floating-point extensions                                                              | 1           |
| [`__ARM_FEATURE_SSVE_FP8FMA`](#modal-8-bit-floating-point-extensions)                                                                                   | Modal 8-bit floating-point extensions                                                              | 1           |
| [`__ARM_FEATURE_SVE`](#scalable-vector-extension-sve)                                                                                                   | Scalable Vector Extension (FEAT_SVE)                                                               | 1           |
| [`__ARM_FEATURE_SVE_B16B16`](#non-widening-brain-16-bit-floating-point-support)                                                                         | Non-widening brain 16-bit floating-point intrinsics (FEAT_SVE_B16B16)                              | 1           |
| [`__ARM_FEATURE_SVE_B16MM`](#brain-16-bit-floating-point-matrix-multiplication-support)                                                                 | SVE brain 16-bit floating-point matrix multiply extension (FEAT_SVE_B16MM)                         | 1           |
| [`__ARM_FEATURE_SVE_BF16`](#brain-16-bit-floating-point-support)                                                                                        | SVE support for the 16-bit brain floating-point extension (FEAT_BF16)                              | 1           |
| [`__ARM_FEATURE_SVE_BFSCALE`](#brain-16-bit-floating-point-vector-multiplication-support)                                                               | SVE support for the 16-bit brain floating-point vector multiplication extension (FEAT_SVE_BFSCALE) | 1           |
| [`__ARM_FEATURE_SVE_BITS`](#scalable-vector-extension-sve)                                                                                              | The number of bits in an SVE vector, when known in advance                                         | 256         |
| [`__ARM_FEATURE_SVE_MATMUL_FP32`](#multiplication-of-32-bit-floating-point-matrices)                                                                    | 32-bit floating-point matrix multiply extension (FEAT_F32MM)                                       | 1           |
| [`__ARM_FEATURE_SVE_MATMUL_FP64`](#multiplication-of-64-bit-floating-point-matrices)                                                                    | 64-bit floating-point matrix multiply extension (FEAT_F64MM)                                       | 1           |
| [`__ARM_FEATURE_F8F16MM`](#multiplication-of-modal-8-bit-floating-point-matrices)                                                                       | Modal 8-bit floating-point matrix multiply-accumulate to half-precision extension (FEAT_F8F16MM)   | 1           |
| [`__ARM_FEATURE_F8F32MM`](#multiplication-of-modal-8-bit-floating-point-matrices)                                                                       | Modal 8-bit floating-point matrix multiply-accumulate to single-precision extension (FEAT_F8F32MM) | 1           |
| [`__ARM_FEATURE_SVE_F16F32MM`](#multiplication-of-16-bit-floating-point-matrices)                                                                       | 16-bit floating-point matrix multiply-accumulate to single-precision extension (FEAT_SVE_F16F32MM) | 1           |
| [`__ARM_FEATURE_SVE_MATMUL_INT8`](#multiplication-of-8-bit-integer-matrices)                                                                            | SVE support for the integer matrix multiply extension (FEAT_I8MM)                                  | 1           |
| [`__ARM_FEATURE_SVE_PREDICATE_OPERATORS`](#scalable-vector-extension-sve)                                                                               | Level of support for C and C++ operators on SVE vector types                                        | 1           |
| [`__ARM_FEATURE_SVE_VECTOR_OPERATORS`](#scalable-vector-extension-sve)                                                                                  | Level of support for C and C++ operators on SVE predicate types                                     | 1           |
| [`__ARM_FEATURE_SVE2`](#sve2)                                                                                                                           | SVE version 2 (FEAT_SVE2)                                                                          | 1           |
| [`__ARM_FEATURE_SVE2_AES`](#aes-extension)                                                                                                              | SVE2 support for the AES cryptographic extension (FEAT_SVE_AES)                                     | 1           |
| [`__ARM_FEATURE_SVE_AES2`](#aes-extension)                                                                                                              | SVE support for the multi-vector AES cryptographic and 128-bit polynomial multiply long extension (FEAT_SVE_AES2)   | 1           |
| [`__ARM_FEATURE_SSVE_AES`](#aes-extension)                                                                                                              | Streaming SVE support for the multi-vector AES cryptographic and 128-bit polynomial multiply long extension (FEAT_SSVE_AES)   | 1           |
| [`__ARM_FEATURE_SVE2_BITPERM`](#bit-permute-extension)                                                                                                  | SVE2 bit permute extension                                                    | 1           |
| [`__ARM_FEATURE_SSVE_BITPERM`](#bit-permute-extension)                                                                                                  | SVE2 bit permute extension                                                    | 1           |
| [`__ARM_FEATURE_SSVE_FEXPA`](#streaming-sve-fexpa-extension)                                                                                            | Streaming SVE FEXPA extension                                                 | 1           |
| [`__ARM_FEATURE_SVE2_SHA3`](#sha3-extension)                                                                                                            | SVE2 support for the SHA3 cryptographic extension (FEAT_SVE_SHA3)                                   | 1           |
| [`__ARM_FEATURE_SVE2_SM3`](#sm3-extension)                                                                                                              | SVE2 support for the SM3 cryptographic extension (FEAT_SVE_SM3)                                     | 1           |
| [`__ARM_FEATURE_SVE2_SM4`](#sm4-extension)                                                                                                              | SVE2 support for the SM4 cryptographic extension (FEAT_SVE_SM4)                                     | 1           |
| [`__ARM_FEATURE_SVE2p1`](#sve2)                                                                                                                         | SVE version 2.1 (FEAT_SVE2p1)
| [`__ARM_FEATURE_SVE2p2`](#sve2)                                                                                                                         | SVE version 2.2 (FEAT_SVE2p2)
| [`__ARM_FEATURE_SVE2p3`](#sve2)                                                                                                                         | SVE version 2.3 (FEAT_SVE2p3)
| [`__ARM_FEATURE_SYSREG128`](#bit-system-registers)                                                                                                      | Support for 128-bit system registers (FEAT_SYSREG128)                                              | 1           |
| [`__ARM_FEATURE_UNALIGNED`](#unaligned-access-supported-in-hardware)                                                                                    | Hardware support for unaligned access                                                              | 1           |
| [`__ARM_FP`](#hardware-floating-point)                                                                                                                  | Hardware floating-point                                                                            | 1           |
| [`__ARM_FP16_ARGS`](#half-precision-argument-and-result)                                                                                                | `__fp16` argument and result                                                                       | 0x0C        |
| [`__ARM_FP16_FORMAT_ALTERNATIVE`](#half-precision-16-bit-floating-point-format)                                                                         | 16-bit floating-point, alternative format                                                          | 1           |
| [`__ARM_FP16_FORMAT_IEEE`](#half-precision-16-bit-floating-point-format)                                                                                | 16-bit floating-point, IEEE format                                                                 | 1           |
| [`__ARM_FP_FAST`](#floating-point-model)                                                                                                                | Accuracy-losing optimizations                                                                      | 1           |
| [`__ARM_FP_FENV_ROUNDING`](#floating-point-model)                                                                                                       | Rounding is configurable at runtime                                                                | 1           |
| [`__ARM_NEON`](#advanced-simd-architecture-extension-neon)                                                                                              | Advanced SIMD (Neon) extension                                                                     | 1           |
| [`__ARM_NEON_FP`](#neon-floating-point)                                                                                                                 | Advanced SIMD (Neon) floating-point                                                                | 0x04        |
| [`__ARM_NEON_SVE_BRIDGE`](#neon-sve-bridge-macro)                                                                                                       | Availability of [`arm_neon_sve_brdge.h`](#arm_neon_sve_bridge.h)                                   | 1           |
| [`__ARM_PCS`](#procedure-call-standard)                                                                                                                 | Arm procedure call standard (32-bit-only)                                                          | 0x01        |
| [`__ARM_PCS_AAPCS64`](#procedure-call-standard)                                                                                                         | Arm PCS for AArch64.                                                                               | 1           |
| [`__ARM_PCS_VFP`](#procedure-call-standard)                                                                                                             | Arm PCS hardware FP variant in use (32-bit-only)                                                   | 1           |
| [`__ARM_ROPI`](#position-independent-code)                                                                                                              | Read-only PIC in use                                                                               | 1           |
| [`__ARM_RWPI`](#position-independent-code)                                                                                                              | Read-write PIC in use                                                                              | 1           |
| [`__ARM_SIZEOF_MINIMAL_ENUM`](#implementation-defined-type-properties)                                                                                  | Size of minimal enumeration type: 1 or 4                                                           | 1           |
| [`__ARM_SIZEOF_WCHAR_T`](#implementation-defined-type-properties)                                                                                       | Size of `wchar_t`: 2 or 4                                                                          | 2           |
| [`__ARM_WMMX`](#wireless-mmx)                                                                                                                           | Wireless MMX extension (32-bit-only)                                                               | 1           |
