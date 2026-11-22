---
name: docs-md-arm-08-attributes-and-pragmas
description: "Arm ACLE: Attributes and pragmas (vendor documentation for Arm NEON, SVE and SME)."
when: "when you need Arm ACLE: Attributes and pragmas while writing a kernel for Arm NEON, SVE and SME."
---

# Attributes and pragmas

## Attribute syntax

This section describes ACLE features that use GNU-style attributes.
The general rules for attribute syntax are described in the GCC
documentation <https://gcc.gnu.org/onlinedocs/gcc/Attribute-Syntax.html>.
Briefly, for this declaration:

``` c
  A int B x C, D y E;
```

attribute `A` applies to both `x` and `y`; `B` and `C` apply to
`x` only, and `D` and `E` apply to `y` only. Programmers are
recommended to keep declarations simple if attributes are used.

Unless otherwise stated, all attribute arguments must be compile-time
constants.

In addition to the GNU-style attributes described in this section,
ACLE also uses [keyword attributes](#keyword-attributes).

## Hardware/software floating-point calling convention

The AArch32 PCS defines a base standard, as well as several variants.

On targets with hardware FP the AAPCS provides for procedure calls to
use either integer or floating-point argument and result registers. ACLE
allows this to be selectable per function.

``` c
    __attribute__((pcs("aapcs")))
```

applied to a function, selects software (integer) FP calling convention.

``` c
    __attribute__((pcs("aapcs-vfp")))
```

applied to a function, selects hardware FP calling convention.

The AArch64 PCS standard variants do not change how parameters are
passed, so no PCS attributes are supported.

The pcs attribute applies to functions and function types.
Implementations are allowed to treat the procedure call specification as
part of the type, that is, as a language linkage in the sense of [C++ \#1].

## Target selection

The following target selection attributes are supported:

``` c
    __attribute__((target("arm")))
```

when applied to a function, forces A32 state code generation.

``` c
    __attribute__((target("thumb")))
```

when applied to a function, forces T32 state code generation.

The implementation must generate code in the required state unless it is
impossible to do so. For example, on an Armv5 or Armv6 target with VFP
(and without the T32 instruction set), if a function is forced to
T32 state, any floating-point operations or intrinsics that are only
available in A32 state must be generated as calls to library functions
or compiler-generated functions.

This attribute does not apply to AArch64.

## Function Multi Versioning

Function Multi Versioning provides a convenient way to select the most
appropriate version of a function at runtime. All versions of the
function may be in the final binary. The compiler generates all
supported versions and the runtime makes the selection at load time.

The following attributes trigger the multi version code generation:
`__attribute__((target_version("<target version string>")))` and
`__attribute__((target_clones("<target version string>",...)))`.

* Functions are allowed to have the same name and signature when
  annotated with these attributes.
* These attributes can be mixed with each other.
* `name` is the dependent features from the tables in the [Mapping](#mapping)
  section.
* The `default` version means the version of the function that would
  be generated without these attributes.
* None of these attributes enable the corresponding ACLE feature(s)
  associated to the `name` expressed in the attribute.
* These attributes have no effect on the calling convention.
* All versions must use the same calling convention.
* If only the `default` version exists, it should be linked directly.
* Function Multi Versioning might be disabled at compile time by a compiler
  flag. In this case, the `default` version is used.
* All function versions must be declared at the same scope level.
* The default version signature is the signature for calling
  the multiversioned functions. Therefore, a versioned function
  cannot be called unless the declaration of the default version
  is visible in the scope of the call site.
* Non-default versions shall have a type that is convertible to the
  type of the default version.
* All the function versions must be declared at the translation
  unit in which the definition of the default version resides.
* One `default` version of the function is required to be provided
  in one of the translation units.
  * Implicitly, as a definition without any attribute,
  * as a function annotated with `target_version("default")`,
  * or, as a function annotated with `target_clones(...)` where one
    of the versions is `default`.
* Using any C/C++ extensions or attributes that affect function name mangling,
  or that clone functions alongside Function Multi Versioning is not supported.

The attribute `__attribute__((target_version("<target version string>")))` expresses the
following:

* When applied to a function it becomes one of the versions.
* Multiple function versions may exist in the same or in different
  translation units.

The following example is valid and 2 is used as the default
value for `c` when calling the multiversioned function `f`.

```cpp
int __attribute__((target_version("simd"))) f (int c = 1);
int __attribute__((target_version("default"))) f (int c = 2);
int __attribute__((target_version("sve"))) f (int c = 3);

int g() { return f(); }
```

Additionally, the following example is not valid because the two statements
declare the same entity (the `default` version of `f`) with conflicting
signatures.

```cpp
int f (int c = 1);
int __attribute__((target_version("default"))) f (int c = 2);
```

The attribute `__attribute__((target_clones("<target version string>",...)))` expresses the
following:

* when applied to a function the compiler emits multiple versions
  based on the arguments.
* If a name is not recognized the compiler should ignore it[^fmv-note-ignore].

[^fmv-note-ignore]: The intention is to support the use case of newer code if
  compiled with an older compiler. The compiler may provide diagnostic messages
  and could block the compilation (for instance, if the `-pedantic` flag is
  present).

`__HAVE_FUNCTION_MULTI_VERSIONING` is defined to 1 if the
versioning mechanism described in this section is supported by the
compiler and it is enabled.

`__FUNCTION_MULTI_VERSIONING_SUPPORT_LEVEL` is defined as a value corresponding to the
support level listed in [Function Multi Versioning feature availability](#function-multi-versioning-feature-availability).

### Target version strings

A target version string has the following form:

```
<target version string>    := 'default'
                            | <version string>
<version string>           :=  <arch strings> ';' <priority string>
                            | <arch strings>
<priority string>          := 'priority=[1-255]'
<arch strings>             := <arch strings> '+' arch extension
                            | arch extension
```

where `arch extension` is any Names value from the Mapping table below.

Valid string examples are given below

```
default
dotprod
dotprod+flagm
sve;priority=5
sve2+sme2;priority=23
```

### Name mangling

The `"default"` version is mangled with `".default"` on top of the
language-specific name mangling. All versioned functions with their mangled names
are always resolvable.
A function is expected to be resolvable with the original mangled name of the function.

The mangling function is compatible with the mangling for version information of
the [[cxxabi]](#cxxabi), and it is defined as follows:

```
<variant name> := <c/c++mangling> `.` <vendor specific suffix>
<c/c++ mangling> := function name mangling for c/c++
<vendor specific suffix> := `_` followed by token obtained from the tables below and prefixed with `M`
```

Priority values do not affect mangling.

If multiple features are requested then those shall be appended in lexicographic
order and prefixed with `M`. The mangled name shall contain a unique set of
features (duplication of features is not allowed).

For example:
``` c
__attribute__((target_clones("default", "crc32", "aes+sha1")))
int foo(){..}
```
will produce these mangled names for C language: `foo.default`, `foo._Mcrc32`,
`foo._MaesMsha1` while `foo` is a callable external symbol which leads to one
of the versioned functions.

### Mapping

The following table lists the architectures feature mapping for AArch32.

   | **Architecture name**            | **Name**        | **Dependent feature registers** |
   | -------------------------------- | --------------- | ------------------------------- |
   | N/A                              | default         | N/A                             |
   | CRC32 instructions               | crc             | ```ID_ISAR5.CRC32 == 0b0001```  |
   | SHA1 instructions                | sha1            | ```ID_ISAR5.SHA1 == 0b0001```   |
   | SHA2 instructions                | sha2            | ```ID_ISAR5.SHA2 == 0b0001```   |
   | AES instructions                 | aes             | ```ID_ISAR5.AES >= 0b0001```    |
   | VMULL (polynomial) instructions  | vmull           | ```ID_ISAR5.AES == 0b0002```    |

The following table lists the architectures feature mapping for AArch64.

   | **Architecture name**    | **Name**      | **Dependent feature registers**           |
   | ------------------------ | ------------- | ----------------------------------------- |
   | N/A                      | default       | N/A                                       |
   | `FEAT_RNG`               | rng           | ```ID_AA64ISAR0_EL1.RNDR >= 0b0001```     |
   | `FEAT_FlagM`             | flagm         | ```ID_AA64ISAR0_EL1.TS >= 0b0001```       |
   | `FEAT_FlagM2`            | flagm2        | ```ID_AA64ISAR0_EL1.TS >= 0b0010```       |
   | `FEAT_LSE`               | lse           | ```ID_AA64ISAR0_EL1.Atomic >= 0b0010```   |
   | Floating-point           | fp            | ```ID_AA64PFR0_EL1.FP != 0b1111```        |
   | `FEAT_AdvSIMD`           | simd          | ```ID_AA64PFR0_EL1.AdvSIMD != 0b1111```   |
   | `FEAT_DotProd`           | dotprod       | ```ID_AA64ISAR0_EL1.DP >= 0b0001```       |
   | `FEAT_SM3`, `FEAT_SM4`   | sm4           | ```ID_AA64ISAR0_EL1.SM4 >= 0b0001```      |
   | `FEAT_RDM`               | rdm, rdma     | ```ID_AA64ISAR0_EL1.RDM >= 0b0001```      |
   | `FEAT_CRC32`             | crc           | ```ID_AA64ISAR0_EL1.CRC32 >= 0b0001```    |
   | `FEAT_SHA1`, `FEAT_SHA256` | sha2        | ```ID_AA64ISAR0_EL1.SHA2 >= 0b0001```     |
   | `FEAT_SHA512`, `FEAT_SHA3` | sha3        | ```ID_AA64ISAR0_EL1.SHA3 >= 0b0001```     |
   | `FEAT_AES`, `FEAT_PMULL` | aes           | ```ID_AA64ISAR0_EL1.AES >= 0b0010```      |
   | `FEAT_FP16`              | fp16          | ```ID_AA64PFR0_EL1.FP == 0b0001```        |
   | `FEAT_FHM`               | fp16fml       | ```ID_AA64ISAR0_EL1.FHM >= 0b0001```      |
   | `FEAT_DIT`               | dit           | ```ID_AA64PFR0_EL1.DIT >= 0b0001```       |
   | `FEAT_DPB`               | dpb           | ```ID_AA64ISAR1_EL1.DPB >= 0b0001```      |
   | `FEAT_DPB2`              | dpb2          | ```ID_AA64ISAR1_EL1.DPB >= 0b0010```      |
   | `FEAT_JSCVT`             | jscvt         | ```ID_AA64ISAR1_EL1.JSCVT >= 0b0001```    |
   | `FEAT_FCMA`              | fcma          | ```ID_AA64ISAR1_EL1.FCMA >= 0b0001```     |
   | `FEAT_LRCPC`             | rcpc          | ```ID_AA64ISAR1_EL1.LRCPC >= 0b0001```    |
   | `FEAT_LRCPC2`            | rcpc2         | ```ID_AA64ISAR1_EL1.LRCPC >= 0b0010```    |
   | `FEAT_LRCPC3`            | rcpc3         | ```ID_AA64ISAR1_EL1.LRCPC >= 0b0011```    |
   | `FEAT_FRINTTS`           | frintts       | ```ID_AA64ISAR1_EL1.FRINTTS >= 0b0001```  |
   | `FEAT_I8MM`              | i8mm          | ```ID_AA64ISAR1_EL1.I8MM >= 0b0001```     |
   | `FEAT_BF16`              | bf16          | ```ID_AA64ISAR1_EL1.BF16 >= 0b0001```     |
   | `FEAT_SVE`               | sve           | ```ID_AA64PFR0_EL1.SVE >= 0b0001```       |
   | `FEAT_F32MM`             | f32mm         | ```ID_AA64ZFR0_EL1.F32MM >= 0b00001```    |
   | `FEAT_F64MM`             | f64mm         | ```ID_AA64ZFR0_EL1.F64MM >= 0b00001```    |
   | `FEAT_SVE2`              | sve2          | ```ID_AA64PFR0_EL1.SVE >= 0b0001 && ID_AA64ZFR0_EL1.SVEver >= 0b0001```|
   | `FEAT_SVE_AES`, <br> `FEAT_SVE_PMULL128` | sve2-aes | ```ID_AA64ZFR0_EL1.AES >= 0b0010``` |
   | `FEAT_SVE_BitPerm`       | sve2-bitperm  | ```ID_AA64ZFR0_EL1.BitPerm >= 0b0001```   |
   | `FEAT_SVE_SHA3`          | sve2-sha3     | ```ID_AA64ZFR0_EL1.SHA3 >= 0b0001```      |
   | `FEAT_SM3`, `FEAT_SVE_SM4` | sve2-sm4    | ```ID_AA64ZFR0_EL1.SM4 >= 0b0001```       |
   | `FEAT_SME`               | sme           | ```ID_AA64PFR1_EL1.SME >= 0b0001```       |
   | `FEAT_MTE`, `FEAT_MTE2`  | memtag        | ```ID_AA64PFR1_EL1.MTE >= 0b0010```       |
   | `FEAT_SB`                | sb            | ```ID_AA64ISAR1_EL1.SB >= 0b0001```       |
   | `FEAT_SSBS`, `FEAT_SSBS2`| ssbs          | ```ID_AA64PFR1_EL1.SSBS >= 0b0010```      |
   | `FEAT_BTI`               | bti           | ```ID_AA64PFR1_EL1.BT >= 0b0001```        |
   | `FEAT_WFxT`              | wfxt          | ```ID_AA64ISAR2_EL1.WFxT >= 0b0010```     |
   | `FEAT_SME_F64F64`        | sme-f64f64    | ```ID_AA64SMFR0_EL1.F64F64 == 0b1```      |
   | `FEAT_SME_I16I64`        | sme-i16i64    | ```ID_AA64SMFR0_EL1.I16I64 == 0b1111```   |
   | `FEAT_SME2`              | sme2          | ```ID_AA64PFR1_EL1.SME >= 0b0001 && ID_AA64SMFR0_EL1.SMEver >= 0b0001```|
   | `FEAT_MOPS`              | mops          | ```ID_AA64ISAR2_EL1.MOPS >= 0b0001```     |
   | `FEAT_CSSC`              | cssc          | ```ID_AA64ISAR2_EL1.CSSC >= 0b0001```     |
   | `FEAT_GCS`               | gcs           | ```ID_AA64PFR1_EL1.GCS >= 0b0001```       |
   | `FEAT_FP8`               | fp8           | ```ID_AA64FPFR0_EL1.F8CVT == 0b1 && ID_AA64FPFR0_EL1.F8E4M3 == 0b1 && ID_AA64FPFR0_EL1.F8E5M2 == 0b1```       |
   | `FEAT_F8F32MM`           | f8f32mm       | ```ID_AA64FPFR0_EL1.F8MM8 == 0b1```       |
   | `FEAT_FP8DOT4`           | fp8dot4       | ```ID_AA64FPFR0_EL1.F8DP4 == 0b1```       |
   | `FEAT_FP8DOT2`           | fp8dot2       | ```ID_AA64FPFR0_EL1.F8DP2 == 0b1```       |
   | `FEAT_FP8FMA`            | fp8fma        | ```ID_AA64FPFR0_EL1.F8FMA == 0b1```       |
   | `FEAT_LUT`               | lut           | ```ID_AA64ISAR2_EL1.LUT >= 0b0001```      |
   | `FEAT_FAMINMAX`          | faminmax      | ```ID_AA64ISAR3_EL1.FAMINMAX >= 0b0001``` |
   | `FEAT_F8F16MM`           | f8f16mm       | ```ID_AA64FPFR0_EL1.F8MM4 == 0b1```       |
   | `FEAT_SVE2p1`            | sve2p1        | ```ID_AA64PFR0_EL1.SVE >= 0b0001 && ID_AA64ZFR0_EL1.SVEver >= 0b0010```|
   | `FEAT_SVE2p2`            | sve2p2        | ```ID_AA64PFR0_EL1.SVE >= 0b0001 && ID_AA64ZFR0_EL1.SVEver >= 0b0011```|
   | `FEAT_SVE_AES2`          | sve-aes2      | ```ID_AA64ZFR0_EL1.AES >= 0b0011```       |
   | `FEAT_SVE_BFSCALE`       | sve-bfscale   | ```ID_AA64ZFR0_EL1.B16B16 >= 0b0010```    |
   | `FEAT_SVE_F16F32MM`      | sve-f16f32mm  | ```ID_AA64ZFR0_EL1.F16MM >= 0b0001```     |
   | `FEAT_SSVE_FP8DOT4`      | ssve-fp8dot4  | ```ID_AA64SMFR0_EL1.SF8DP4 == 0b1```      |
   | `FEAT_SSVE_FP8DOT2`      | ssve-fp8dot2  | ```ID_AA64SMFR0_EL1.SF8DP2 == 0b1```      |
   | `FEAT_SSVE_FP8FMA`       | ssve-fp8fma   | ```ID_AA64SMFR0_EL1.SF8FMA == 0b1```      |
   | `FEAT_SSVE_BitPerm`      | ssve-bitperm  | ```ID_AA64SMFR0_EL1.SBitPerm == 0b1```    |
   | `FEAT_SSVE_AES`          | ssve-aes      | ```ID_AA64SMFR0_EL1.AES == 0b1```         |
   | `FEAT_SSVE_FEXPA`        | ssve-fexpa    | ```ID_AA64SMFR0_EL1.SFEXPA == 0b1```      |
   | `FEAT_SME_F8F32`         | sme-f8f32     | ```ID_AA64SMFR0_EL1.F8F32 == 0b1```       |
   | `FEAT_SME_LUTv2`         | sme-lutv2     | ```ID_AA64SMFR0_EL1.LUTv2 == 0b1```       |
   | `FEAT_SME2p1`            | sme2p1        | ```ID_AA64PFR1_EL1.SME >= 0b0001 && ID_AA64SMFR0_EL1.SMEver >= 0b0010```|
   | `FEAT_SME2p2`            | sme2p2        | ```ID_AA64PFR1_EL1.SME >= 0b0001 && ID_AA64SMFR0_EL1.SMEver >= 0b0011```|
   | `FEAT_SME_F16F16`        | sme-f16f16    | ```ID_AA64SMFR0_EL1.F16F16 == 0b1```      |
   | `FEAT_SME_F8F16`         | sme-f8f16     | ```ID_AA64SMFR0_EL1.F8F16 == 0b1```       |
   | `FEAT_SME_MOP4`          | sme-mop4      | ```ID_AA64SMFR0_EL1.SMOP4 == 0b1```       |

The tables are sorted by priority, starting from features of lowest priority ending with features of highest priority.

### Function Multi Versioning feature availability

The following table lists the Function Multi Versioning support level at
which each target version name became available.

A Function Multi Versioning target version name is supported when
`__HAVE_FUNCTION_MULTI_VERSIONING` is defined to `1` and
`__FUNCTION_MULTI_VERSIONING_SUPPORT_LEVEL` is greater than or equal to
the support level listed for that name. Support for a given support level
includes all target version names introduced at earlier support levels,
unless otherwise specified.


   | **Name**      | **Minimum support level** |
   | ------------- | ------------------------- |
   | default       | **202210**                |
   | sha1          | 202210                    |
   | aes           | 202210                    |
   | vmull         | 202210                    |
   | rng           | 202210                    |
   | flagm         | 202210                    |
   | flagm2        | 202210                    |
   | lse           | 202210                    |
   | dotprod       | 202210                    |
   | rdm           | 202210                    |
   | fp16          | 202210                    |
   | dit           | 202210                    |
   | dpb           | 202210                    |
   | dpb2          | 202210                    |
   | jscvt         | 202210                    |
   | fcma          | 202210                    |
   | frintts       | 202210                    |
   | sve           | 202210                    |
   | sve2          | 202210                    |
   | sme           | 202210                    |
   | sb            | 202210                    |
   | ssbs          | 202210                    |
   | bti           | 202210                    |
   | crc           | **202240**                |
   | sha2          | 202240                    |
   | fp            | 202240                    |
   | simd          | 202240                    |
   | sm4           | 202240                    |
   | sha3          | 202240                    |
   | fp16fml       | 202240                    |
   | rcpc          | 202240                    |
   | rcpc2         | 202240                    |
   | i8mm          | 202240                    |
   | bf16          | 202240                    |
   | f32mm         | 202240                    |
   | f64mm         | 202240                    |
   | sve2-aes      | 202240                    |
   | sve2-bitperm  | 202240                    |
   | sve2-sha3     | 202240                    |
   | sve2-sm4      | 202240                    |
   | memtag        | 202240                    |
   | wfxt          | 202240                    |
   | sme2          | 202240                    |
   | rcpc3         | **202320**                |
   | sme-f64f64    | 202320                    |
   | sme-i16i64    | 202320                    |
   | rdma          | **202410**                |
   | mops          | 202410                    |
   | cssc          | **202520**                |
   | gcs           | **202690**                |
   | fp8           | 202690                    |
   | f8f32mm       | 202690                    |
   | fp8dot4       | 202690                    |
   | fp8dot2       | 202690                    |
   | fp8fma        | 202690                    |
   | lut           | 202690                    |
   | faminmax      | 202690                    |
   | f8f16mm       | 202690                    |
   | sve2p1        | 202690                    |
   | sve2p2        | 202690                    |
   | sve-aes2      | 202690                    |
   | sve-bfscale   | 202690                    |
   | sve-f16f32mm  | 202690                    |
   | ssve-fp8dot4  | 202690                    |
   | ssve-fp8dot2  | 202690                    |
   | ssve-fp8fma   | 202690                    |
   | ssve-bitperm  | 202690                    |
   | ssve-aes      | 202690                    |
   | ssve-fexpa    | 202690                    |
   | sme-f8f32     | 202690                    |
   | sme-lutv2     | 202690                    |
   | sme2p1        | 202690                    |
   | sme2p2        | 202690                    |
   | sme-f16f16    | 202690                    |
   | sme-f8f16     | 202690                    |
   | sme-mop4      | 202690                    |

### Dependencies

If a feature depends on another feature as defined by the following table then:

* the depended-on feature *need not* be specified in the attribute,
* the depended-on feature *might* be specified in the attribute,
* the depended-on feature *must* be of lower priority.

These dependencies are taken into account transitively when selecting the
most appropriate version of a function (see section [Selection](#selection)).
The following table lists the feature dependencies for AArch64.

   | **Feature**      | **Depends on**    |
   | ---------------- | ----------------- |
   | flagm2           | flagm             |
   | simd             | fp                |
   | dotprod          | simd              |
   | sm4              | simd              |
   | rdm              | simd              |
   | sha2             | simd              |
   | sha3             | sha2              |
   | aes              | simd              |
   | fp16             | fp                |
   | fp16fml          | simd, fp16        |
   | dpb2             | dpb               |
   | jscvt            | fp                |
   | fcma             | simd              |
   | rcpc2            | rcpc              |
   | rcpc3            | rcpc2             |
   | frintts          | fp                |
   | i8mm             | simd              |
   | bf16             | simd              |
   | sve              | fp16              |
   | f32mm            | sve               |
   | f64mm            | sve               |
   | sve2             | sve               |
   | sve2-aes         | sve2, aes         |
   | sve2-bitperm     | sve2              |
   | sve2-sha3        | sve2, sha3        |
   | sve2-sm4         | sve2, sm4         |
   | sme              | fp16, bf16        |
   | sme-f64f64       | sme               |
   | sme-i16i64       | sme               |
   | sme2             | sme               |
   | fp8              | simd              |
   | f8f32mm          | simd, fp8         |
   | fp8dot4          | fp8               |
   | fp8dot2          | fp8               |
   | fp8fma           | fp8               |
   | lut              | simd              |
   | faminmax         | simd              |
   | f8f16mm          | simd, fp8         |
   | sve2p1           | sve2              |
   | sve2p2           | sve2p1            |
   | sve-f16f32mm     | sve               |
   | ssve-fp8dot4     | sme2, fp8         |
   | ssve-fp8dot2     | sme2, fp8         |
   | ssve-fp8fma      | sme2, fp8         |
   | ssve-bitperm     | sme2              |
   | ssve-aes         | sme2, aes         |
   | ssve-fexpa       | sme2              |
   | sme-f8f32        | sme2, fp8         |
   | sme-lutv2        | sme2              |
   | sme2p1           | sme2              |
   | sme2p2           | sme2p1            |
   | sme-f16f16       | sme2              |
   | sme-f8f16        | sme2, fp8         |
   | sme-mop4         | sme2              |

### Selection

The following rules shall be followed by all implementations:

1. Implementation of
the selection algorithm is platform dependent, where with platform means
CPU/Vendor/OS as in the target triplet.
2. The selection is permanent for the
lifetime of the process.
3. The selection algorithm must select the version with the highest
precedence whose dependent features are all available.

The precedence for two target version strings is determined by:

1. If both target version strings specify a `priority`, with different values,
then the version with the higher `priority` has precedence.
2. If only one target version string specifies a `priority`, this version has
precedence.
3. Otherwise, if neither target version string specifies a `priority` or both
specify the same value, then precedence is decided by identifying the highest
priority feature that is specified in exactly one of the versions, and selecting
that version.

## Weak linkage

`__attribute__((weak))` can be attached to declarations and
definitions to indicate that they have weak static linkage (`STB_WEAK` in
ELF objects). As definitions, they can be overridden by other
definitions of the same symbol. As references, they do not need to be
satisfied and will be resolved to zero if a definition is not present.

### Patchable constants

In addition, this specification requires that weakly defined initialized
constants are not used for constant propagation, allowing the value to
be safely changed by patching after the object is produced.

## Alignment

The new standards for C [[C11]](#C11) (6.7.5) and C++ [[CPP11]](#CPP11) (7.6.2) add syntax for
aligning objects and types. ACLE provides an alternative syntax
described in this section.

### Alignment attribute

`__attribute__((aligned(N)))` can be associated with data, functions,
types and fields. N must be an integral constant expression and must be
a power of 2, for example 1, 2, 4, 8. The maximum alignment depends on the
storage class of the object being aligned. The size of a data type is
always a multiple of its alignment. This is a consequence of the rule in
C that the spacing between array elements is equal to the element size.

The aligned attribute does not act as a type qualifier. For example,
given

``` c
  char x __attribute__((aligned(8)));
  int y __attribute__((aligned(1)));
```

the type of `&x` is `char *` and the type of `&y` is `int *`. The
following declarations are equivalent:

``` c
  struct S x __attribute__((aligned(16))); /* ACLE */

  struct S _Alignas(16) x/* C11 */

  #include <stdalign.h> /* C11 (alternative) */
  struct S alignas(16) x;

  struct S alignas(16) x; /* C++11 */
```

### Alignment of static objects

The macro `__ARM_ALIGN_MAX_PWR` indicates (as the exponent of a power
of 2) the maximum available alignment of static data -- for example 4 for
16-byte alignment. So the following is always valid:

``` c
  int x __attribute__((aligned(1 << __ARM_ALIGN_MAX_PWR)));
```

or, using the C11/C++11 syntax:

``` c
  alignas(1 << __ARM_ALIGN_MAX_PWR) int x;
```

Since an alignment request on an object does not change its type or
size, x in this example would have type int and size 4.

There is in principle no limit on the alignment of static objects,
within the constraints of available memory. In the Arm ABI an object
with a requested alignment would go into an ELF section with at least as
strict an alignment requirement. However, an implementation supporting
position-independent dynamic objects or overlays may need to place
restrictions on their alignment demands.

### Alignment of stack objects

It must be possible to align any local object up to the stack alignment
as specified in the AAPCS for AArch32 (that is, 8 bytes) or as specified in
AAPCS64 for AArch64 (that is, 16 bytes) this being also the maximal
alignment of any native type.

An implementation may, but is not required to, permit the allocation of
local objects with greater alignment, for example 16 or 32 bytes for AArch32.
(This would involve some runtime adjustment such that the object address
was not a fixed offset from the stack pointer on entry.)

If a program requests alignment greater than the implementation
supports, it is recommended that the compiler warn but not fault this.
Programmers should expect over-alignment of local objects to be treated
as a hint.

The macro `__ARM_ALIGN_MAX_STACK_PWR` indicates (as the exponent of
a power of 2) the maximum available stack alignment. For example, a
value of 3 indicates 8-byte alignment.

### Procedure calls

For procedure calls, where a parameter has aligned type, data should be
passed as if it was a basic type of the given type and alignment. For
example, given the aligned type:

``` c
  struct S { int a[2]; } __attribute__((aligned(8)));
```

the second argument of:

``` c
  f(int, struct S);
```

should be passed as if it were:

``` c
  f(int, long long);
```

which means that in AArch32 AAPCS the second parameter is in `R2/R3`
rather than `R1/R2`.

### Alignment of C heap storage

The standard C allocation functions [[C99]](#C99) (7.20.3), such as malloc(),
return storage aligned to the normal maximal alignment, that is, the largest
alignment of any (standard) type.

Implementations may, but are not required to, provide a function to
return heap storage of greater alignment. Suitable functions are:

``` c
  int posix_memalign(void **memptr, size_t alignment, size_t size );
```

as defined in [[POSIX]](#POSIX), or:

``` c
  void *aligned_alloc(size_t alignment, size_t size);
```

as defined in [[C11]](#C11) (7.22.3.1).

### Alignment of C++ heap allocation

In C++, an allocation (with new) knows the object's type. If the type
is aligned, the allocation should also be aligned. There are two cases
to consider depending on whether the user has provided an allocation
function.

If the user has provided an allocation function for an object or array
of over-aligned type, it is that function's responsibility to return
suitably aligned storage. The size requested by the runtime library will
be a multiple of the alignment (trivially so, for the non-array case).

(The AArch32 C++ ABI does not explicitly deal with the runtime behavior
when dealing with arrays of alignment greater than 8. In this situation,
any cookie will be 8 bytes as usual, immediately preceding the array;
this means that the cookie is not necessarily at the address seen by the
allocation and deallocation functions. Implementations will need to make
some adjustments before and after calls to the ABI-defined C++ runtime,
or may provide additional non-standard runtime helper functions.)
Example:

``` c
  struct float4 {
    void *operator new[](size_t s) {
      void *p;
      posix_memalign(&p, 16, s);
      return p;
    }
    float data[4];
  } __attribute__((aligned(16)));
```

If the user has not provided their own allocation function, the behavior
is implementation-defined.

The generic itanium C++ ABI, which we use in AArch64, already handles
arrays with arbitrarily aligned elements

## Scalable Vector Extension procedure call standard attribute

On SVE enabled AArch64 targets, the [[AAPCS64]](#AAPCS64) allows procedure
calls to use the SVE calling convention. If a subroutine takes at least one
argument in scalable vector registers or scalable predicate registers, or if
the subroutine is a function that returns results in such registers, the
subroutine must ensure that the entire contents of `z8-z23` and `p4-15` are
preserved across the call. This calling convention is described in sections
6.1.3 and 6.1.4 of [AAPCS64](#AAPCS64) (see [release 2022Q1](https://github.com/ARM-software/abi-aa/releases/tag/2022Q1)).

The ACLE allows this to be enforced per function and adds the following
function attribute to a function declaration or definition:

``` c
    __attribute__(("aarch64_sve_pcs"))
```

## Other attributes

The following attributes should be supported and their definitions
follow [[GCC]](#GCC). These attributes are not specific to Arm or the Arm ABI.

`alias`, `common`, `nocommon`, `noinline`, `packed`, `section`,
`visibility`, `weak`

Some specific requirements on the weak attribute are detailed in
[Weak linkage](#weak-linkage).
