---
name: docs-md-arm-03-preface
description: "Arm ACLE: Preface (vendor documentation for Arm NEON, SVE and SME)."
when: "when you need Arm ACLE: Preface while writing a kernel for Arm NEON, SVE and SME."
---

# Preface

## Abstract

This document specifies the Arm C Language Extensions to enable C/C++
programmers to exploit the Arm architecture with minimal restrictions on
source code portability.

## Keywords

ACLE, ABI, C, C++, compiler, armcc, gcc, intrinsic, macro, attribute,
Neon, SIMD, SVE, SVE2, atomic

## Latest release and defects report

For the latest release of this document, see the [ACLE project on
GitHub](https://github.com/ARM-software/acle).

Please report defects in this specification to the [issue tracker page
on GitHub](https://github.com/ARM-software/acle/issues).

## License

This work is licensed under the Creative Commons
Attribution-ShareAlike 4.0 International License. To view a copy of
this license, visit <http://creativecommons.org/licenses/by-sa/4.0/> or
send a letter to Creative Commons, PO Box 1866, Mountain View, CA
94042, USA.

Grant of Patent License. Subject to the terms and conditions of this
license (both the Public License and this Patent License), each
Licensor hereby grants to You a perpetual, worldwide, non-exclusive,
no-charge, royalty-free, irrevocable (except as stated in this
section) patent license to make, have made, use, offer to sell, sell,
import, and otherwise transfer the Licensed Material, where such
license applies only to those patent claims licensable by such
Licensor that are necessarily infringed by their contribution(s) alone
or by combination of their contribution(s) with the Licensed Material
to which such contribution(s) was submitted. If You institute patent
litigation against any entity (including a cross-claim or counterclaim
in a lawsuit) alleging that the Licensed Material or a contribution
incorporated within the Licensed Material constitutes direct or
contributory patent infringement, then any licenses granted to You
under this license for that Licensed Material shall terminate as of
the date such litigation is filed.

## About the license

As identified more fully in the [License](#license) section, this project
is licensed under CC-BY-SA-4.0 along with an additional patent
license. The language in the additional patent license is largely
identical to that in Apache-2.0 (specifically, Section 3 of Apache-2.0
as reflected at <https://www.apache.org/licenses/LICENSE-2.0>) with two
exceptions.

First, several changes were made related to the defined terms so as to
reflect the fact that such defined terms need to align with the
terminology in CC-BY-SA-4.0 rather than Apache-2.0 (for example, changing
“Work” to “Licensed Material”).

Second, the defensive termination clause was changed such that the
scope of defensive termination applies to “any licenses granted to
You” (rather than “any patent licenses granted to You”).  This change
is intended to help maintain a healthy ecosystem by providing
additional protection to the community against patent litigation
claims.

## Contributions

Contributions to this project are licensed under an inbound=outbound
model such that any such contributions are licensed by the contributor
under the same terms as those in the LICENSE file.

We do not require copyright assignment. The original contributor will
retain the copyright.

## Trademark notice

The text of and illustrations in this document are licensed by Arm
under a Creative Commons Attribution–Share Alike 4.0 International
license ("CC-BY-SA-4.0"), with an additional clause on patents.
The Arm trademarks featured here are registered trademarks or
trademarks of Arm Limited (or its subsidiaries) in the US and/or
elsewhere. All rights reserved. Please visit
<https://www.arm.com/company/policies/trademarks> for more information
about Arm’s trademarks.

## Copyright

* Copyright 2011-2026 Arm Limited and/or its affiliates <open-source-office@arm.com>.
* Copyright 2022 Google LLC.

## About this document

### Support levels

The following support level definitions are used by the ACLE
specifications:

**Release**

   Arm considers this specification to have enough implementations,
   which have received sufficient testing, to verify that it is
   correct. The details of these criteria are dependent on the scale
   and complexity of the change over previous versions: small, simple
   changes might only require one implementation, but more complex
   changes require multiple independent implementations, which have
   been rigorously tested for cross-compatibility. Arm anticipates that
   future changes to this specification will be limited to
   typographical corrections, clarifications and compatible extensions.

**Beta**

   Arm considers this specification to be complete, but existing
   implementations do not meet the requirements for confidence in its
   release quality. Arm might need to make incompatible changes if issues
   emerge from its implementation.

**Alpha**

   The content of this specification is a draft, and Arm considers the
   likelihood of future incompatible changes to be significant.

All content in this document is at the **Release** quality level,
unless a different support level is specified in the text.

### Continuously updated specification

After 2026Q1, this specification is published continuously from the
main branch. Each published version is identified by its Git commit hash.

See [Changelog for year 2026](#changelog-for-year-2026).

### Changelog for year 2026

* Added [**Alpha**](#support-levels)
  support for SVE2.3 (FEAT_SVE2p3), SME2.3 (FEAT_SME2p3), FEAT_F16F32DOT
  dot product intrinsics.
* Added [**Alpha**](#support-levels)
  support for FEAT_F16F32MM, FEAT_F16MM and FEAT_SVE_B16MM mmla intrinsics.
* Added [**Alpha**](#support-levels)
  support for SVE2.3 (FEAT_SVE2p3) and SME2.3 lookup table intrinsics.
* Added [**Alpha**](#support-levels)
  support for SVE2.3 (FEAT_SVE2p3) and SME2.3 pairwise operation intrinsics.
* Added [**Alpha**](#support-levels)
  support for SVE2.3 (FEAT_SVE2p3) and SME2.3 conversion intrinsics.
* Added [**Alpha**](#support-levels)
  support for SVE2.3 (FEAT_SVE2p3) and SME2.3 absolute difference accumulation
  intrinsics.
* Added [**Alpha**](#support-levels)
  support for SVE2.3 (FEAT_SVE2p3) and SME2.3 shift right narrow intrinsics.
* Changed the support level for the Armv9.6 intrinsics implementation to [**Beta**](#support-levels)
* Added support for producer-consumer data placement hints.
* Clarified interaction between SME keyword attributes and a common compiler
  extension whereby type attributes can be inherited between subsequent
  duplicate decls.
* Added feature test macro `__ARM_FEATURE_LSCP` for FEAT_LSCP.

### Legacy changelog

The changes between legacy releases were as follows:

| **Issue**    | **Date**          | **By** | **Change**                                                                                                           |
| ------------ | ----------------- | ------ | -------------------------------------------------------------------------------------------------------------------- |
| A            | 11/11/11          | AG     | First release                                                                                                        |
| B            | 13/11/13          | AG     | Version 1.1. Editorial changes. Corrections and completions to intrinsics as detailed in 3.3. Updated for C11/C++11. |
| C            | 09/05/14          | TB     | Version 2.0. Updated for Armv8 AArch32 and AArch64.                                                                  |
| D            | 24/03/16          | TB     | Version 2.1. Updated for Armv8.1 AArch32 and AArch64.                                                                |
| E            | 02/06/17          | Arm    | Version ACLE Q2 2017. Updated for Armv8.2-A and Armv8.3-A.                                                           |
| F            | 30/04/18          | Arm    | Version ACLE Q2 2018. Updated for Armv8.4-A.                                                                         |
| G            | 30/03/19          | Arm    | Version ACLE Q1 2019. Updated for Armv8.5-A and MVE. Various bugfixes.                                               |
| H            | 30/06/19          | Arm    | Version ACLE Q2 2019. Updated for TME and more Armv8.5-A intrinsics. Various bugfixes.                               |
| ACLE Q3 2019 | 30/09/19          | Arm    | Version ACLE Q3 2019.                                                                                                |
| ACLE Q4 2019 | 31/12/19          | Arm    | Version ACLE Q4 2019.                                                                                                |
| ACLE Q2 2020 | 31/05/20          | Arm    | Version ACLE Q2 2020.                                                                                                |
| ACLE Q3 2020 | 31/10/20          | Arm    | Version ACLE Q3 2020.                                                                                                |
| 2021Q2       | 02 July 2021      | Arm    | Version ACLE Q2 2021. Open source version. NFCI.                                                                     |
| 2021Q3       | 30 September 2021 | Arm    | Minor re-wording. NFCI.                                                                                              |
| 2021Q4       | 11 January 2022   | Arm    | See [Changes between ACLE Q3 2021 and ACLE Q4 2021](#changes-between-acle-q3-2021-and-acle-q4-2021)                  |
| 2022Q1       | 06 April 2022     | Arm    | See [Changes between ACLE Q4 2021 and ACLE Q1 2022](#changes-between-acle-q4-2021-and-acle-q1-2022)                  |
| 2022Q2       | 01 Jul 2022       | Arm    | See [Changes between ACLE Q1 2021 and ACLE Q2 2022](#changes-between-acle-q1-2022-and-acle-q2-2022)                  |
| 2022Q4       | 23 November 2022  | Arm    | See [Changes between ACLE Q2 2022 and ACLE Q4 2022](#changes-between-acle-q2-2022-and-acle-q4-2022)                  |
| 2023Q2       | 04 August 2023    | Arm    | See [Changes between ACLE Q4 2022 and ACLE Q2 2023](#changes-between-acle-q4-2022-and-acle-q2-2023)                  |
| 2024Q1       | 11 April 2024     | Arm    | See [Changes between ACLE Q2 2023 and ACLE Q1 2024](#changes-between-acle-q2-2023-and-acle-q1-2024)                  |
| 2024Q2       | 21 June 2024      | Arm    | See [Changes between ACLE Q1 2024 and ACLE Q2 2024](#changes-between-acle-q1-2024-and-acle-q2-2024)                  |
| 2024Q3       | 30 September 2024 | Arm    | See [Changes between ACLE Q2 2024 and ACLE Q3 2024](#changes-between-acle-q2-2024-and-acle-q3-2024)                  |
| 2024Q4       | 21 February 2025  | Arm    | See [Changes between ACLE Q3 2024 and ACLE Q4 2024](#changes-between-acle-q3-2024-and-acle-q4-2024)                  |
| 2025Q2       | 06 June 2025      | Arm    | See [Changes between ACLE Q4 2024 and ACLE Q2 2025](#changes-between-acle-q4-2024-and-acle-q2-2025)                  |
| 2025Q3       | 14 November 2025  | Arm    | See [Changes between ACLE Q2 2025 and ACLE Q3 2025](#changes-between-acle-q2-2025-and-acle-q3-2025)                  |
| 2026Q1       | 15 May 2026       | Arm    | See [Changes between ACLE Q3 2025 and ACLE Q1 2026](#changes-between-acle-q3-2025-and-acle-q1-2026)                  |

#### Changes between ACLE Q2 2017 and ACLE Q2 2018

Most changes in ACLE Q2 2018 are updates to support features introduced in
Armv8.3-A [[ARMARMv83]](#ARMARMv83). Support is added for the Complex addition and Complex MLA intrinsics.
Armv8.4-A [[ARMARMv84]](#ARMARMv84). Support is added for the Dot Product intrinsics.

#### Changes between ACLE Q2 2018 and ACLE Q1 2019

* Support added for features introduced in Armv8.5-A [[ARMARMv85]](#ARMARMv85) (including the MTE extension).
* Support added for MVE [[MVE-spec]](#MVE-spec) from the Armv8.1-M architecture.
* Support added for Armv8.4-A half-precision extensions through Neon intrinsics.
* Added feature detection macro for LSE atomic operations.
* Added floating-point versions of intrinsics to access coprocessor registers.

#### Changes between ACLE Q1 2019 and ACLE Q2 2019

* Support added for TME features.
* Support added for rounding intrinsics from Armv8.5-A [[ARMARMv85]](#ARMARMv85).

#### Changes between ACLE Q2 2019 and ACLE Q3 2019

* Support added for Armv8.6-A features.
* Support added for random number instruction intrinsics from Armv8.5-A [[ARMARMv85]](#ARMARMv85).

#### Changes between ACLE Q3 2019 and ACLE Q4 2019

* BETA support for the Custom Datapath Extension.
* MVE intrinsics updates and fixes.
* Feature macros for Pointer Authentication and Branch Target Identification.

#### Changes between ACLE Q4 2019 and ACLE Q2 2020

* Updates to CDE intrinsics.
* Allow some Neon intrinsics previously available in A64 only in A32 as well.

#### Changes between ACLE Q2 2020 and ACLE Q3 2020

* Add support for features introduced in the Armv8.7-a architecture update.
* Fix allowed values for __ARM_FEATURE_CDE_COPROC macro.

#### Changes between ACLE Q2 2021 and ACLE Q3 2021
* Fixed FP16 format description at [Half-precision
  floating-point](#half-precision-floating-point).
* Fixed the description of `vmul_lane_u16` at
  [Concepts](#neon-intrinsics-concepts).

#### Changes between ACLE Q3 2021 and ACLE Q4 2021

* Updated copyright statement in section [Copyright](#copyright).
* Introduced `__ARM_FEATURE_PAUTH` and `__ARM_FEATURE_BTI` in sections
  [Pointer Authentication](#pointer-authentication) and [Branch Target
  Identification](#branch-target-identification) respectively.
* Fixed the changelog of 2021Q3, as is was missing the mentioning of
  the intrinsic `vmul_lane_u16` in the second item.
* Fixed item lists rendering in [M-profile Vector
  Extension](#m-profile-vector-extension-mve-intrinsics).
* Fixed superfluous and broken backticks in code examples throughout.
* Added reference to the *Cortex-M Security Extension (CMSE)*
  specifications in [Cortex-M Security Extension
  (CMSE)](#cortex-m-security-extension-cmse).
* Added specification for [Neon-SVE Bridge](#neon-sve-bridge) and
  [Neon-SVE Bridge macros](#neon-sve-bridge-macro).
* Added feature detection macro for the memcpy family of memory
  operations (MOPS) at [memcpy family of memory operations
  standardization instructions -
  MOPS](#memcpy-family-of-memory-operations-standardization-instructions---mops)
* Added intrinsic for the memcpy family of memory operations (MOPS) at
  [memcpy family of operations intrinsics -
  MOPS](#memcpy-family-of-operations-intrinsics---mops)
* Converted document sources from reStructuredText (`.rst`) to
  Markdown (`.md`). The tool [`pandoc`](https://pandoc.org/) is now
  used to render the PDF of the specs. The PDF is rendered using the
  standard layout used in Arm specifications.
* Updated the section links in [Changes between ACLE Q2 2021 and ACLE
  Q3 2021](#changes-between-acle-q2-2021-and-acle-q3-2021) by using
  the actual section title.

#### Changes between ACLE Q4 2021 and ACLE Q1 2022

* Updated the description of the `__arm_mops_memset_tag` intrinsic in [memcpy
  family of operations intrinsics - MOPS](#memcpy-family-of-operations-intrinsics---mops)
  to require both the `__ARM_FEATURE_MOPS` and `__ARM_FEATURE_MEMORY_TAGGING`
  feature macros.
* Fixed minor formatting errors throughout.
* Replaced link text such as “sec-…” and “ssec-…” with section titles.
* Reorganized the presentation of [Feature test macros](#feature-test-macros).
  Also:
  * Generalized some AArch32-specific text to AArch64.
  * Added more cross-references to the descriptions of the macros.
  * Used embedded links for the [list of predefined macros](#summary-of-predefined-macros)
    and fixed some misdirected links.  Resorted the list into alphabetical
    order.
* Reorganized the [Intrinsics](#intrinsics) and
  [Header files](#header-files) sections.
* Added a description of [`<arm_neon_sve_bridge.h>`](#arm_neon_sve_bridge.h)
  to the [Header files](#header-files) section.
* In [Data types](#data-types), clarified that `__fp16` and `__bf16` are
  predefined types whereas vector types like `int32x4_t` are not.
* Moved the [Future directions](#future-directions) chapter to the end.
* Added a description of [support levels](#support-levels).
* Support added for [Function Multi Versioning](#function-multi-versioning).
* The sections [AES extension](#aes-extension), [SHA2
  extension](#sha2-extension) and [SHA512
  extension](#sha512-extension) have been reworded for clarity, by
  specifying the `FEAT_*` tag they refer to from the Arm Architectural
  Reference Manual.
* Sorted the items in [References](#references).
* Changed the wording of **Beta** in [support levels](#support-levels).
* Sorted the table in [Terms and abbreviations](#terms-and-abbreviations).
* Formatted `memcpy`, `memmove` and `memset` with fixed-width font all
  throughout the document.
* Minor rewording for:
  * [Introduction](#introduction) section of [memcpy family of
    operations intrinsics -
    MOPS](#memcpy-family-of-operations-intrinsics---mops).
  * [Procedure calls and the Q / GE bits](#procedure-calls-and-the-q-ge-bits).
  * [Custom calling conventions](#custom-calling-conventions) - use a
    bulleted list for the examples.

  No functional change intended.
* Reordered the sections in [Legacy changelog](#legacy-changelog) in
  chronological order.

#### Changes between ACLE Q1 2022 and ACLE Q2 2022

* Added [support for SVE and SVE2](#arm_sve.h). This incorporates the final
  00bet6 version of the separate beta document [Arm C Language Extensions for
  SVE](https://developer.arm.com/architectures/system-architectures/software-standards/acle),
  except that the optional feature `__ARM_FEATURE_SVE_NONMEMBER_OPERATORS`
  has been removed. The SVE and SVE2 support is now at “release” rather than
  beta quality and the separate beta document is no longer maintained.
* Added section [Scalable Vector Extension procedure call standard attribute](#scalable-vector-extension-procedure-call-standard-attribute)
* Fixes for [Function Multi Versioning](#function-multi-versioning):
  * typo in `FEAT_DPB2`.
  * added `FEAT_LS64*`.

#### Changes between ACLE Q2 2022 and ACLE Q4 2022

* Added [**Alpha**](#support-levels)
  [support for SME](#arm_sme.h).
* Added feature detection macro `__ARM_FEATURE_RCPC` for RCpc (Release Consistent processor consistent) model at [RCpc](#rcpc).
* Added two new valid values to the
  [SVE feature macros](#scalable-vector-extension-sve):
  * `__ARM_FEATURE_SVE_VECTOR_OPERATORS=2`
  * `__ARM_FEATURE_SVE_PREDICATE_OPERATORS=2`
* Fixes for [Function Multi Versioning](#function-multi-versioning):
  * Added missing features of `ID_AA64ISAR1_EL1` and `ID_AA64ISAR2_EL1`.
  * Renamed the feature macro to `__HAVE_FUNCTION_MULTI_VERSIONING`
  * Added some clarifications.

#### Changes between ACLE Q4 2022 and ACLE Q2 2023

* Added SLC as a valid Cache Level for the Memory prefetch intrinsics.
* Added [support for 128-bit system registers](#special-register-intrinsics),
  including two intrinsics for accessing them (`__rsr128` and `__wsr128`), and a
  feature macro to detect if they are available (`__ARM_FEATURE_SYSREG128`).
* Added support for FEAT_LRCPC3 LDAP1/STL1 intrinsics and `__ARM_FEATURE_RCPC`.
* Corrected the mandatory architecture versions for FEAT_LRCPC and FEAT_LRCPC2.
* Corrected references to `-pedantic` flag.
* Fixed typos.
* Fixes for [Function Multi Versioning](#function-multi-versioning):
  * Renamed features to `sme-f64f64` and `sme-i16i64`
  * Corrected register name to `ID_AA64SMFR0_EL1.I16I64`
* Removed incorrect optimization remark in [CMSE](#CMSE-ACLE)'s floating-point
  register clearing.
* Removed incorrect information about the floating-point ABI used in
  [CMSE](#CMSE-ACLE)'s Arguments on the stack and floating point handling.
* Corrected description and example in [CMSE](#CMSE-ACLE)'s section about
  non-secure function pointers.
* Added a requirement on [`arm_new_za`] to set the initial contents of
  ZA to zero.

#### Changes between ACLE Q2 2023 and ACLE Q1 2024

* Changed the definition of the `__ARM_ACLE` macro to reflect the current
  versioning scheme.
* Added `__ARM_ACLE_VERSION` to express a given ACLE version.
* Combined the SME `slice_base` and `slice_offset` arguments into a
  single `slice` argument.
* Added the [Keyword attributes](#keyword-attributes) section.
* Changed the [SME language extensions](#sme-language-extensions-and-intrinsics)
  to use keyword attributes instead of GNU-style attributes.
* Added description of SVE reinterpret intrinsics.
* Changes and fixes for [Function Multi Versioning](#function-multi-versioning):
  * Combination of attributes `target_version` and `target_clones` is allowed.
  * Clarify the existence of a single default version across all translation
    units with the explicitly provided version being the preferred in case
    `target_version` and `target_clones` are mixed.
  * Emphasize that all instances of the versions share the same calling convention.
  * Changed the mangling rules [Name mangling](#name-mangling), such that
    feature names are appended in lexicographic order, not in priority order.
  * Mangled names contain a unique set of features (no duplicates).
  * Added [MOPS](#memcpy-family-of-operations-intrinsics---mops).
  * Changed name mangling of the default version.
  * Aligned priorities to account for feature dependencies.
  * Introduced alternative names (aliases) `rdma` for `rdm`.
  * Corrected FEAT_BTI feature register value.
* Introduced the `__ARM_FEATURE_PAUTH_LR` feature macro in section
  [Pointer Authentication](#pointer-authentication) to indicate target support
  for the Armv9.5-A PAC Enhancements.
* Introduced a new value to the `__ARM_FEATURE_PAC_DEFAULT` macro to indicate
  the use of PC as a diversifier for [Pointer Authentication](#pointer-authentication).
* Added a [State management](#state-management) section, replacing the
  `__arm_shared_za`, `__arm_new_za`, and `__arm_preserves_za` attributes
  in the previous Alpha SME spec.
* Changed the status of the SME ACLE from Alpha to Beta.

#### Changes between ACLE Q1 2024 and ACLE Q2 2024
* Added new content for the handling of arguments in CMSE Entry functions and
  return values of CMSE Non-secure calls in order to address security issues.
* Added [**Alpha**](#support-levels)
  support for SVE2.1 (FEAT_SVE2p1).

#### Changes between ACLE Q2 2024 and ACLE Q3 2024

* Fixed incorrect system register dependencies in Function Multi Versioning.
* Added a requirement for function version declaration in Function Multi Versioning.
* Added `__FUNCTION_MULTI_VERSIONING_SUPPORT_LEVEL` to indicate the support
  level of the [Function Multi Versioning](#function-multi-versioning).
* Unified Function Multi Versioning features sha1 and sha2.
* Unified Function Multi Versioning features ls64, ls64_v, and ls64_accdata.
* Added [**Alpha**](#support-levels)
  support for SME2.1 (FEAT_SME2p1).
* Removed requirement to add preprocessor guards for header files.
* Added specifications for floating-point absolute minimum
  and maximum intrinsics (FEAT_FAMINMAX).
* Added specifications for table lookup intrinsics (FEAT_LUT, FEAT_SME_LUTv2).
* Added Release support level for the [Custom Datapath Extension](#custom-datapath-extension).
* Added [**Alpha**](#support-levels)
  support for modal 8-bit floating point intrinsics.

#### Changes between ACLE Q3 2024 and ACLE Q4 2024

* Unified Function Multi Versioning features ssbs and ssbs2.
* Unified Function Multi Versioning features memtag and memtag2.
* Unified Function Multi Versioning features aes and pmull.
* Unified Function Multi Versioning features sve2-aes and sve2-pmull128.
* Removed Function Multi Versioning features sve-bf16, sve-ebf16, and sve-i8mm.
* Removed Function Multi Versioning features ebf16, memtag3, and rpres.
* Removed Function Multi Versioning feature dgh.
* Removed Function Multi Versioning features ls64 and predres.
* Document Function Multi Versioning feature dependencies.
* Clarify Function Multi Versioning feature dependency rule.
* Simplified Function Multi Versioning version selection rules.
* Fixed range of operand `o0` (too small) in AArch64 system register designations.
* Fixed SVE2.1 quadword gather load/scatter store intrinsics.
* Removed unnecessary Zd argument from `svcvtnb_mf8[_f32_x2]_fpm`.
* Changed name mangling of function types to include SME attributes.
* Changed `__ARM_NEON_SVE_BRIDGE` to refer to the availability of the
  [`arm_neon_sve_bridge.h`](#arm_neon_sve_bridge.h) header file, rather
  than the [Neon-SVE bridge](#neon-sve-bridge) intrinsics.
* Removed extraneous `const` from SVE2.1 store intrinsics.
* Added [`__arm_agnostic`](#arm_agnostic) keyword attribute.
* Refined function versioning scope and signature rules to use the default
  version scope and signature.
* Added `_n` forms of the SVE2p1 and SME2 `svdot` intrinsics.
* Changed the status of the SME2p1 from Alpha to Beta.
* Changed the status of the SVE2p1 from Alpha to Beta.
* Added mf8 variants of SME 2.1 intrinsics.
* Added `svdot[_n_f16_mf8]_fpm` and `svdot[_n_f32_mf8]_fpm`.
* Added Guarded Control Stack (GCS) at
  [**Beta**](#support-levels) quality level.

#### Changes between ACLE Q4 2024 and ACLE Q2 2025

* Changed the Function Multi Versioning default version rules to be more explicit.
* Added [**Alpha**](#support-levels) support
  for structured sparsity outer product intrinsics
* Added [**Alpha**](#support-levels) support
  for quarter-tile outer product intrinsics.
* Removed the priority column from the mapping tables of Function Multi Versioning.
* Added Function Multi Versioning feature cssc.
* Added feature test macro for FEAT_SSVE_BitPerm.
* Upgrade to [**Beta**](#support-levels)
  support for modal 8-bit floating point intrinsics.

#### Changes between ACLE Q2 2025 and ACLE Q3 2025

* Added feature test macro for FEAT_SSVE_FEXPA.
* Added feature test macro for FEAT_CSSC.
* Added Function Multi Versioning feature priority syntax.

#### Changes between ACLE Q3 2025 and ACLE Q1 2026

* Added support for modal 8-bit floating point matrix multiply-accumulate widening intrinsics.
* Added support for 16-bit floating point matrix multiply-accumulate widening intrinsics.
* Added restrictions of Function Multi Versioning's use with other extensions.
* Upgraded Function Multi Versioning to Release support level.
* Removed _single from svmla_za16[_mf8]_vg2x1_fpm and svmla_za32[_mf8]_vg4x1_fpm.
* Improved documentation for VMLA/VMLS intrinsics for floats.
* Added support for producer-consumer data placement hints.
* Added support for range prefetch intrinsic and `__ARM_PREFETCH_RANGE` macro.
* Added [**Alpha**](#support-levels)
  support for SVE2.2 (FEAT_SVE2p2)
* Added [**Alpha**](#support-levels)
  support for SME2.2 (FEAT_SME2p2).
* Added [**Alpha**](#support-levels) support
  for FEAT_SVE_AES2, FEAT_SSVE_AES intrinsics.
* Added support for FEAT_FPRCVT intrinsics and `__ARM_FEATURE_FPRCVT`.
* Removed all references to Transactional Memory Extension (TME).
* Added [**Alpha**](#support-levels) support
  for Brain 16-bit floating-point vector multiplication intrinsics.
* Redesigned atomic store with hints intrinsics.

### References

This document refers to the following documents.

<!-- Please the list of references in alphabetical order -->

* <span id="AAPCS" class="citation-label">AAPCS</span> Arm,
  [Application Binary Interface for the Arm
  Architecture](https://developer.arm.com/products/architecture/system-architectures/software-standards/abi)

* <span id="AAPCS64" class="citation-label">AAPCS64</span> Arm,
  [Application Binary Interface for the Arm
  Architecture](https://developer.arm.com/products/architecture/system-architectures/software-standards/abi)

* <span id="ARMARM" class="citation-label">ARMARM</span> Arm, Arm
  Architecture Reference Manual (7-A / 7-R), Arm DDI 0406C

* <span id="ARMARMv8" class="citation-label">ARMARMv8</span> Arm,
  Armv8-A Reference Manual (Issue A.b), Arm DDI0487A.B

* <span id="ARMARMv81" class="citation-label">ARMARMv81</span> Arm,
  Armv8.1 Extension, [The ARMv8-A architecture and its ongoing
  development](https://developer.arm.com/community/arm-community-blogs/b/architectures-and-processors-blog/posts/the-armv8-a-architecture-and-its-ongoing-development)

* <span id="ARMARMv82" class="citation-label">ARMARMv82</span> Arm,
  Armv8.2 Extension, [Armv8-A architecture
  evolution](https://developer.arm.com/community/arm-community-blogs/b/architectures-and-processors-blog/posts/armv8-a-architecture-evolution)

* <span id="ARMARMv83" class="citation-label">ARMARMv83</span> Arm,
  Armv8.3 Extension, [Armv8-A architecture: 2016
  additions](https://developer.arm.com/community/arm-community-blogs/b/architectures-and-processors-blog/posts/armv8-a-architecture-2016-additions)

* <span id="ARMARMv84" class="citation-label">ARMARMv84</span> Arm,
  Armv8.4 Extension, [Introducing 2017’s extensions to the Arm
  Architecture](https://developer.arm.com/community/arm-community-blogs/b/architectures-and-processors-blog/posts/introducing-2017s-extensions-to-the-arm-architecture)

* <span id="ARMARMv85" class="citation-label">ARMARMv85</span> Arm,
  Armv8.5 Extension, [Arm A-Profile Architecture Developments 2018:
  Armv8.5-A](https://developer.arm.com/community/arm-community-blogs/b/architectures-and-processors-blog/posts/arm-a-profile-architecture-2018-developments-armv85a)

* <span id="ARMv7M" class="citation-label">ARMv7M</span> Arm, Arm
  Architecture Reference Manual (7-M), Arm DDI 0403C

* <span id="BA" class="citation-label">BA</span> Arm, EABI Addenda and
  Errata Build Attributes, Arm IHI 0045C

* <span id="Bfloat16" class="citation-label">Bfloat16</span> Arm,
  [BFloat16 processing for Neural Networks on
  Armv8-A](https://developer.arm.com/community/arm-community-blogs/b/ai-blog/posts/bfloat16-processing-for-neural-networks-on-armv8_2d00_a)

* <span id="C11" class="citation-label">C11</span> ISO, Standard C
  (based on draft N1570), ISO/IEC 9899:2011

* <span id="C99" class="citation-label">C99</span> ISO, Standard C
  (C99), ISO 9899:1999

* <span id="CFP15" class="citation-label">CFP15</span> ISO/IEC,
  Floating point extensions for C, ISO/IEC TS 18661-3

* <span id="CMSE-ACLE" class="citation-label">CMSE-ACLE</span> Arm,
  [Arm®v8-M Security Extensions: Requirements on Development
  Tools](https://developer.arm.com/documentation/ecm0359818/latest)

* <span id="CPP11" class="citation-label">CPP11</span> ISO, Standard
  C++ (based on draft N3337), ISO/IEC 14882:2011

* <span id="CPP14" class="citation-label">CPP14</span> ISO, Standard C++
  (based on draft N3797), ISO/IEC 14882:2014

* <span id="G.191" class="citation-label">G.191</span> ITU-T, Software
  Tool Library 2005 User's Manual, T-REC-G.191-200508-I

* <span id="GCC" class="citation-label">GCC</span> GNU/FSF, [GNU C
  Compiler Collection](http://gcc.gnu.org/onlinedocs)

* <span id="IA-64" class="citation-label">IA-64</span> Intel, Intel
  Itanium Processor-Specific ABI, 245370-003

* <span id="IEEE-FP" class="citation-label">IEEE-FP</span> IEEE, IEEE
  Floating Point, IEEE 754-2008

* <span id="MVE" class="citation-label">MVE</span> Arm, [MVE
  Intrinsics](https://developer.arm.com/architectures/instruction-sets/simd-isas/helium/mve-intrinsics)

* <span id="MVE-spec" class="citation-label">MVE-spec</span> Arm, Arm
  v8-M Architecture Reference Manual, Arm DDI0553B.F

* <span id="Neon" class="citation-label">Neon</span> Arm, [Neon
  Intrinsics](https://developer.arm.com/technologies/neon/intrinsics)

* <span id="POSIX" class="citation-label">POSIX</span> IEEE / TOG, The
  Open Group Base Specifications, IEEE 1003.1

* <span id="Warren" class="citation-label">Warren</span> 8.  Warren, Hacker's Delight, pub. Addison-Wesley 2003

* <span id="cxxabi" class="citation-label">cxxabi</span> [Itanium C++
  ABI](https://itanium-cxx-abi.github.io/cxx-abi/)

### Terms and abbreviations

This document uses the following terms and abbreviations.

<!-- Please keep the rows of the table in alphabetical order by the column "Term" -->

| **Term**         | **Meaning**                                                                                  |
| ---------------- | -------------------------------------------------------------------------------------------- |
| AAPCS            | Arm Procedure Call Standard, part of the ABI, defined in [[AAPCS]](#AAPCS).                  |
| ABI              | Arm Application Binary Interface.                                                            |
| ACLE             | Arm C Language Extensions, as defined in this document.                                      |
| Advanced SIMD    | A 64-bit/128-bit SIMD instruction set defined as part of the Arm architecture.               |
| FFR              | The SVE first-fault register.                                                                |
| FFRT             | The SVE “first-fault register token”. This is a conceptual construct that forms part of the ACLE model of first-faulting and non-faulting loads; see [First-faulting and non-faulting loads](#first-faulting-and-non-faulting-loads) for details. |
| ILP32            | A 32-bit address mode where long is a 32-bit type.                                           |
| LLP64            | A 64-bit address mode where long is a 32-bit type.                                           |
| LP64             | A 64-bit address mode where long is a 64-bit type.                                           |
| Neon             | An implementation of the Arm Advanced SIMD extensions.                                       |
| SIMD             | Any instruction set that operates simultaneously on multiple elements of a vector data type. |
| sizeless type    | A C and C++ type that can be used to create objects, but that has no measurable size; see [Sizeless types](#sizeless-types) for details. |
| SVE              | The Armv8-A Scalable Vector Extension. Also used more generally to include SVE2 and other SVE extensions. |
| SVE2             | An Armv9-A extension of SVE.                                                                 |
| SVL              | Streaming Vector Length; that is, the number of bits in an SVE vector type like ``svint32_t`` when the processor is in [streaming mode](#streaming-mode) |
| SVL.B            | As for SVL, but measured in bytes rather than bits |
| Thumb            | The Thumb instruction set extension to Arm.                                                  |
| VG               | The number of 64-bit elements (“vector granules”) in an SVE vector.                          |
| VFP              | The original Arm non-SIMD floating-point instruction set.                                    |
| build attributes | Object build attributes indicating configuration, as defined in [[BA]](#BA).                 |
| word             | A 32-bit quantity, in memory or a register.                                                  |

### Terms used to specify C and C++ semantics

The following terms are used to specify C and C++ semantics:

<span id="abstract-machine"></span>

**abstract machine**

> The conceptual machine that the C and C++ language standards use to define
> the behavior of programs.

<span id="evaluated-call"></span>

**evaluated call**

> A call that does not occur in an “unevaluated operand”;
> see section `[expr.context]` in the C++ standard for details.
>
> For example, any calls that occur in the operand of a `sizeof`
> expression are not evaluated.

<span id="external-linkage"></span>

**external linkage**

> A function has “external linkage” if there is a single definition that can be
> referenced by name from more than one translation unit. See `[basic.link]`
> in the C++ standard for more details.
>
> As noted in [Intrinsics](#intrinsics), it is unspecified whether ACLE
> intrinsics are functions and, if so, what linkage they have. However,
> certain ACLE support functions are defined to have external linkage.

<span id="ill-formed"></span>

**ill-formed** programs or pieces of programs

> Programs or pieces of programs that violate a rule due to their static
> construction rather than due to their runtime behavior.
>
> Ill-formed programs should usually be rejected with at least one
> diagnostic. However, there are some ill-formed C++ constructs for which
> “no diagnostic is required”; see the `[intro]` section of the C++
> standard for details. Many of these constructs could in principle
> use ACLE features.
>
> In order to cope with such cases, ACLE does not say when
> ill-formed programs should be rejected. However, from a
> quality-of-implementation perspective, it is better to reject
> ill-formed programs wherever possible.

<span id="unprototyped-function"></span>

**unprototyped functions**

> In early versions of C, it was possible to call a function without
> declaring it first. The function was then assumed to return an `int`.
> For example, this was a valid complete translation unit:
>
> ``` c
>   int x() { return some_func(1, 2.0, "apples"); }
> ```
>
> It was also possible to declare a function's return type without specifying
> its argument types. For example:
>
> ``` c
>   double another_func();
>   double f() { return another_func(1.0, 2, "oranges"); }
> ```
>
> Functions such as `some_func` and `another_func` are referred to as
> (K&R-style) “unprototyped” functions. The first C standard categorized
> these functions as an obsolescent feature and C18 removed all remaining
> support for them.

## Conventions

Most SVE ACLE intrinsics have two names: a longer unique name and a
shorter overloaded alias. The convention adopted in this document is to
enclose characters in square brackets if they are only present in the
longer name. For example:

``` c
  svclz[_u16]_m
```

refers to an intrinsic whose full name is `svclz_u16_m` and whose
overloaded alias is `svclz_m`.

## Scope

The Arm C Language Extensions (ACLE) specification specifies source
language extensions and implementation choices that C/C++ compilers can
implement in order to allow programmers to better exploit the Arm
architecture.

The extensions include:

 * Predefined macros that provide information about the functionality of
   the target architecture.

 * Intrinsic functions.

 * Attributes that can be applied to functions, data and other entities.

This specification does not standardize command-line options,
diagnostics or other external behavior of compilers.

The intended users of this specification are:

* Application programmers wishing to adapt or hand-optimize
  applications and libraries for Arm targets.

* System programmers needing low-level access to Arm targets beyond
  what C/C++ provides for.

* Compiler implementors, who will implement this specification.

* Implementors of IDEs, static analysis and other similar tools who wish to
  deal with the C/C++ source language extensions when encountered in
  source code.

ACLE is not a hardware abstraction layer (HAL), and does not specify a
library component but it may make it easier to write a HAL or other
low-level library in C rather than assembler.

## Cortex-M Security Extension (CMSE)

ACLE support for the Cortex-M Security Extension (CMSE) is defined in
*Arm®v8-M Security Extensions: Requirements on Development Tools*
document [CMSE-ACLE](#CMSE-ACLE).
