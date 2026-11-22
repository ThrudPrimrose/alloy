---
name: docs-md-arm-06-architecture-and-cpu-names
description: "Arm ACLE: Architecture and CPU names (vendor documentation for Arm NEON, SVE and SME)."
when: "when you need Arm ACLE: Architecture and CPU names while writing a kernel for Arm NEON, SVE and SME."
---

# Architecture and CPU names

## Introduction

The intention of this section is to standardize architecture names, for example
for use in compiler command lines. Toolchains should accept these names
case-insensitively where possible, or use all lowercase where not
possible. Tools may apply local conventions such as using hyphens
instead of underscores.

(Note: processor names, including from the Arm Cortex |reg| processor family,
are used as illustrative examples. This specification is applicable to any
processors implementing the Arm architecture.)

## Architecture names

### CPU architecture

The recommended CPU architecture names are as specified under
`Tag_CPU_arch` in [[BA]](#BA). For details of how to use predefined macros to
test architecture in source code, see [Instruction set architecture and
features](#instruction-set-architecture-and-features).

The following table lists the architectures and the A32 and
T32 instruction set versions.

| **Name**        | **Features**                                             | **A32** | **T32** | **Example processor**  |
| --------------- | -------------------------------------------------------- | ------- | ------- | ---------------------- |
| Armv4           | Armv4                                                    | 4       |         | DEC/Intel StrongARM    |
| Armv4T          | Armv4 with Thumb instruction set                         | 4       | 2       | Arm7TDMI               |
| Armv5T          | Armv5 with Thumb instruction set                         | 5       | 2       | Arm10TDMI              |
| Armv5TE         | Armv5T with DSP extensions                               | 5       | 2       | Arm9E, Intel XScale    |
| Armv5TEJ        | Armv5TE with Jazelle ® extensions                        | 5       | 2       | Arm926EJ               |
| Armv6           | Armv6 (includes TEJ)                                     | 6       | 2       | Arm1136J r0            |
| Armv6K          | Armv6 with kernel extensions                             | 6       | 2       | Arm1136J r1            |
| Armv6T2         | Armv6 with Thumb-2 architecture                          | 6       | 3       | Arm1156T2              |
| Armv6Z          | Armv6K with Security Extensions (includes K)             | 6       | 2       | Arm1176JZ-S            |
| Armv6-M         | T32 (M-profile)                                          |         | 2       | Cortex-M0, Cortex-M1   |
| Armv7-A         | Armv7 application profile                                | 7       | 4       | Cortex-A8, Cortex-A9   |
| Armv7-R         | Armv7 realtime profile                                   | 7       | 4       | Cortex-R4              |
| Armv7-M         | Armv7 microcontroller profile: Thumb-2 instructions only |         | 4       | Cortex-M3              |
| Armv7E-M        | Armv7-M with DSP extensions                              |         | 4       | Cortex-M4              |
| Armv8-A AArch32 | Armv8 application profile                                | 8       | 4       | Cortex-A57, Cortex-A53 |
| Armv8-A AArch64 | Armv8 application profile                                | 8       |         | Cortex-A57, Cortex-A53 |

Note that there is some architectural variation that is not visible
through ACLE; either because it is only relevant at the system level
(for example the Large Physical Address Extension) or because it would be
handled by the compiler (for example hardware divide might or might not be
present in the Armv7-A architecture).

### FPU architecture

For details of how to test FPU features in source code, see
[Floating-point and vector hardware](#floating-point-and-vector-hardware).
In particular, for testing which precisions are supported in hardware,
see [Hardware floating point](#hardware-floating-point).

| **Name**         | **Features**                                       | **Example processor**               |
| ---------------- | -------------------------------------------------- | ----------------------------------- |
| `VFPv2`          | VFPv2                                              | Arm1136JF-S                         |
| `VFPv3`          | VFPv3                                              | Cortex-A8                           |
| `VFPv3_FP16`     | VFPv3 with FP16                                    | Cortex-A9 (with Neon)               |
| `VFPv3_D16`      | VFPv3 with 16 D-registers                          | Cortex-R4F                          |
| `VFPv3_D16_FP16` | VFPv3 with 16 D-registers and FP16                 | Cortex-A9 (without Neon), Cortex-R7 |
| `VFPv3_SP_D16`   | VFPv3 with 16 D-registers, single-precision only   | Cortex-R5 with SP-only              |
| `VFPv4`          | VFPv4 (including FMA and FP16)                     | Cortex-A15                          |
| `VFPv4_D16`      | VFPv4 (including FMA and FP16) with 16 D-registers | Cortex-A5 (VFP option)              |
| `FPv4_SP`        | FPv4 with single-precision only                    | Cortex-M4.fp                        |

## CPU names

ACLE does not standardize CPU names for use in command-line options and
similar contexts. Standard vendor product names should be used.

Object producers should place the CPU name in the `Tag_CPU_name` build
attribute.
