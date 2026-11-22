---
name: docs-md-x86-01-chapter-1-about-this-manual
description: "Intel SDM Vol. 2: Chapter 1 About This Manual (vendor documentation for x86 AVX2, AVX-512 and AVX-512 FP16)."
when: "when you need Intel SDM Vol. 2: Chapter 1 About This Manual while writing a kernel for x86 AVX2, AVX-512 and AVX-512 FP16."
---

CHAPTER 1 ABOUT THIS MANUAL

The _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volumes 2A, 2B, 2C & 2D_ : _Instruction Set Reference_ (order numbers 253666, 253667, 326018, and 334569) are part of a set that describes the architecture and programming environment of all Intel 64 and IA-32 architecture processors. Other volumes in this set are:

- The _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1: Basic Architecture_ (Order Number 253665).

- The _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volumes 3A, 3B, 3C & 3D: System Programming Guide_ (order numbers 253668, 253669, 326019, and 332831).

- The _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 4: Model-Specific Registers_ (order number 335592).

The _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1,_ describes the basic architecture and programming environment of Intel 64 and IA-32 processors. The _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volumes 2A, 2B, 2C & 2D_ , describe the instruction set of the processor and the opcode structure. These volumes apply to application programmers and to programmers who write operating systems or executives. The _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volumes 3A, 3B, 3C & 3D,_ describe the operating-system support environment of Intel 64 and IA-32 processors. These volumes target operatingsystem and BIOS designers. In addition, the _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 3B_ , addresses the programming environment for classes of software that host operating systems. The _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 4,_ describes the model-specific registers of Intel 64 and IA-32 processors.

# 1.1 INTEL<sup>®</sup> 64 AND IA-32 PROCESSORS COVERED IN THIS MANUAL

This manual set includes information pertaining primarily to the most recent Intel 64 and IA-32 processors, which include:

- Pentium<sup>®</sup> processors

- P6 family processors

- Pentium<sup>®</sup> 4 processors

- Pentium<sup>®</sup> M processors

- Intel<sup>®</sup> Xeon<sup>_®_</sup> processors

- Pentium<sup>®</sup> D processors

- Pentium<sup>®</sup> processor Extreme Editions

- 64-bit Intel<sup>®</sup> Xeon<sup>_®_</sup> processors

- Intel<sup>®</sup> Core™ Duo processor

- Intel<sup>®</sup> Core™ Solo processor

- Dual-Core Intel<sup>®</sup> Xeon<sup>®</sup> processor LV

- Intel<sup>®</sup> Core™2 Duo processor

- Intel<sup>®</sup> Core™2 Quad processor Q6000 series

- Intel<sup>®</sup> Xeon<sup>®</sup> processor 3000, 3200 series

- Intel<sup>®</sup> Xeon<sup>®</sup> processor 5000 series

- Intel<sup>®</sup> Xeon<sup>®</sup> processor 5100, 5300 series

- Intel<sup>®</sup> Core™2 Extreme processor X7000 and X6800 series

- Intel<sup>®</sup> Core™2 Extreme processor QX6000 series

- Intel<sup>®</sup> Xeon<sup>®</sup> processor 7100 series

Vol. 2A 1-1

ABOUT THIS MANUAL

- Intel<sup>®</sup> Pentium<sup>®</sup> Dual-Core processor

- Intel<sup>®</sup> Xeon<sup>®</sup> processor 7200, 7300 series

- Intel<sup>®</sup> Xeon<sup>®</sup> processor 5200, 5400, 7400 series

- Intel<sup>®</sup> Core™2 Extreme processor QX9000 and X9000 series

- Intel<sup>®</sup> Core™2 Quad processor Q9000 series

- Intel<sup>®</sup> Core™2 Duo processor E8000, T9000 series

- Intel Atom<sup>®</sup> processor family

- Intel Atom<sup>®</sup> processors 200, 300, D400, D500, D2000, N200, N400, N2000, E2000, Z500, Z600, Z2000, C1000 series are built from 45 nm and 32 nm processes

- Intel<sup>®</sup> Core™ i7 processor

- Intel<sup>®</sup> Core™ i5 processor

- Intel<sup>®</sup> Xeon<sup>®</sup> processor E7-8800/4800/2800 product families

- Intel<sup>®</sup> Core™ i7-3930K processor

- 2nd generation Intel<sup>®</sup> Core™ i7-2xxx, Intel<sup>®</sup> Core™ i5-2xxx, Intel<sup>®</sup> Core™ i3-2xxx processor series

- Intel<sup>®</sup> Xeon<sup>®</sup> processor E3-1200 product family

- Intel<sup>®</sup> Xeon<sup>®</sup> processor E5-2400/1400 product family

- Intel<sup>®</sup> Xeon<sup>®</sup> processor E5-4600/2600/1600 product family

- 3rd generation Intel<sup>®</sup> Core™ processors

- Intel<sup>®</sup> Xeon<sup>®</sup> processor E3-1200 v2 product family

- Intel<sup>®</sup> Xeon<sup>®</sup> processor E5-2400/1400 v2 product families

- Intel<sup>®</sup> Xeon<sup>®</sup> processor E5-4600/2600/1600 v2 product families

- Intel<sup>®</sup> Xeon<sup>®</sup> processor E7-8800/4800/2800 v2 product families

- 4th generation Intel<sup>®</sup> Core™ processors

- The Intel<sup>®</sup> Core™ M processor family

- Intel<sup>®</sup> Core™ i7-59xx Processor Extreme Edition

- Intel<sup>®</sup> Core™ i7-49xx Processor Extreme Edition

- Intel<sup>®</sup> Xeon<sup>®</sup> processor E3-1200 v3 product family

- Intel<sup>®</sup> Xeon<sup>®</sup> processor E5-2600/1600 v3 product families

- 5th generation Intel<sup>®</sup> Core™ processors

- Intel<sup>®</sup> Xeon<sup>®</sup> processor D-1500 product family

- Intel<sup>®</sup> Xeon<sup>®</sup> processor E5 v4 family

- Intel Atom<sup>®</sup> processor X7-Z8000 and X5-Z8000 series

- Intel Atom<sup>®</sup> processor Z3400 series

- Intel Atom<sup>®</sup> processor Z3500 series

- 6th generation Intel<sup>®</sup> Core™ processors

- Intel<sup>®</sup> Xeon<sup>®</sup> processor E3-1500m v5 product family

- 7th generation Intel<sup>®</sup> Core™ processors

- Intel<sup>®</sup> Xeon Phi™ Processor 3200, 5200, 7200 Series

- Intel<sup>®</sup> Xeon<sup>®</sup> Scalable Processor Family

- 8th generation Intel<sup>®</sup> Core™ processors

- Intel<sup>®</sup> Xeon Phi™ Processor 7215, 7285, 7295 Series

- Intel<sup>®</sup> Xeon<sup>®</sup> E processors

- 9th generation Intel<sup>®</sup> Core™ processors

- 2nd generation Intel<sup>®</sup> Xeon<sup>®</sup> Scalable Processor Family

1-2 Vol. 2A

ABOUT THIS MANUAL

- 10th generation Intel<sup>®</sup> Core™ processors

- 11th generation Intel<sup>®</sup> Core™ processors

- 3rd generation Intel<sup>®</sup> Xeon<sup>®</sup> Scalable Processor Family

- 12th generation Intel<sup>®</sup> Core™ processors

- 13th generation Intel<sup>®</sup> Core™ processors

- 4th generation Intel<sup>®</sup> Xeon<sup>®</sup> Scalable Processor Family

P6 family processors are IA-32 processors based on the P6 family microarchitecture. This includes the Pentium<sup>®</sup> Pro, Pentium<sup>®</sup> II, Pentium<sup>®</sup> III, and Pentium<sup>®</sup> III Xeon<sup>®</sup> processors.

The Pentium<sup>®</sup> 4, Pentium<sup>®</sup> D, and Pentium<sup>®</sup> processor Extreme Editions are based on the Intel NetBurst<sup>®</sup> microarchitecture. Most early Intel<sup>®</sup> Xeon<sup>®</sup> processors are based on the Intel NetBurst<sup>®</sup> microarchitecture. Intel Xeon processor 5000, 7100 series are based on the Intel NetBurst<sup>®</sup> microarchitecture.

The Intel<sup>®</sup> Core™ Duo, Intel<sup>®</sup> Core™ Solo and dual-core Intel<sup>®</sup> Xeon<sup>®</sup> processor LV are based on an improved Pentium<sup>®</sup> M processor microarchitecture.

The Intel<sup>®</sup> Xeon<sup>®</sup> processor 3000, 3200, 5100, 5300, 7200, and 7300 series, Intel<sup>®</sup> Pentium<sup>®</sup> dual-core, Intel<sup>®</sup> Core™2 Duo, Intel<sup>®</sup> Core™2 Quad, and Intel<sup>®</sup> Core™2 Extreme processors are based on Intel<sup>®</sup> Core™ microarchitecture.

The Intel<sup>®</sup> Xeon<sup>®</sup> processor 5200, 5400, 7400 series, Intel<sup>®</sup> Core™2 Quad processor Q9000 series, and Intel<sup>®</sup> Core™2 Extreme processors QX9000, X9000 series, Intel<sup>®</sup> Core™2 processor E8000 series are based on Enhanced Intel<sup>®</sup> Core™ microarchitecture.

The Intel Atom<sup>®</sup> processors 200, 300, D400, D500, D2000, N200, N400, N2000, E2000, Z500, Z600, Z2000, C1000 series are based on the Intel Atom<sup>®</sup> microarchitecture and supports Intel 64 architecture.

P6 family, Pentium<sup>®</sup> M, Intel<sup>®</sup> Core™ Solo, Intel<sup>®</sup> Core™ Duo processors, dual-core Intel<sup>®</sup> Xeon<sup>®</sup> processor LV, and early generations of Pentium 4 and Intel Xeon processors support IA-32 architecture. The Intel<sup>®</sup> Atom<sup>TM</sup> processor Z5xx series support IA-32 architecture.

The Intel<sup>®</sup> Xeon<sup>®</sup> processor 3000, 3200, 5000, 5100, 5200, 5300, 5400, 7100, 7200, 7300, 7400 series, Intel<sup>®</sup> Core™2 Duo, Intel<sup>®</sup> Core™2 Extreme, Intel<sup>®</sup> Core™2 Quad processors, Pentium<sup>®</sup> D processors, Pentium<sup>®</sup> DualCore processor, newer generations of Pentium 4 and Intel Xeon processor family support Intel<sup>®</sup> 64 architecture.

The Intel<sup>®</sup> Core™ i7 processor and Intel<sup>®</sup> Xeon<sup>®</sup> processor 3400, 5500, 7500 series are based on 45 nm Nehalem microarchitecture. Westmere microarchitecture is a 32 nm version of the Nehalem microarchitecture. Intel<sup>®</sup> Xeon<sup>®</sup> processor 5600 series, Intel Xeon processor E7 and various Intel Core i7, i5, i3 processors are based on the Westmere microarchitecture. These processors support Intel 64 architecture.

The Intel<sup>®</sup> Xeon<sup>®</sup> processor E5 family, Intel<sup>®</sup> Xeon<sup>®</sup> processor E3-1200 family, Intel<sup>®</sup> Xeon<sup>®</sup> processor E78800/4800/2800 product families, Intel<sup>®</sup> Core™ i7-3930K processor, and 2nd generation Intel<sup>®</sup> Core™ i7-2xxx, Intel<sup>®</sup> Core<sup>TM</sup> i5-2xxx, Intel<sup>®</sup> Core™ i3-2xxx processor series are based on the Sandy Bridge microarchitecture and support Intel 64 architecture.

The Intel<sup>®</sup> Xeon<sup>®</sup> processor E7-8800/4800/2800 v2 product families, Intel<sup>®</sup> Xeon<sup>®</sup> processor E3-1200 v2 product family and 3rd generation Intel<sup>®</sup> Core™ processors are based on the Ivy Bridge microarchitecture and support Intel 64 architecture.

The Intel<sup>®</sup> Xeon<sup>®</sup> processor E5-4600/2600/1600 v2 product families, Intel<sup>®</sup> Xeon<sup>®</sup> processor E5-2400/1400 v2 product families and Intel<sup>®</sup> Core™ i7-49xx Processor Extreme Edition are based on the Ivy Bridge-E microarchitecture and support Intel 64 architecture.

The Intel<sup>®</sup> Xeon<sup>®</sup> processor E3-1200 v3 product family and 4th Generation Intel<sup>®</sup> Core™ processors are based on the Haswell microarchitecture and support Intel 64 architecture.

The Intel<sup>®</sup> Xeon<sup>®</sup> processor E5-2600/1600 v3 product families and the Intel<sup>®</sup> Core™ i7-59xx Processor Extreme Edition are based on the Haswell-E microarchitecture and support Intel 64 architecture.

The Intel Atom<sup>®</sup> processor Z8000 series is based on the Airmont microarchitecture.

The Intel Atom<sup>®</sup> processor Z3400 series and the Intel Atom<sup>®</sup> processor Z3500 series are based on the Silvermont microarchitecture.

Vol. 2A 1-3

ABOUT THIS MANUAL

The Intel<sup>®</sup> Core™ M processor family, 5th generation Intel<sup>®</sup> Core™ processors, Intel<sup>®</sup> Xeon<sup>®</sup> processor D-1500 product family and the Intel<sup>®</sup> Xeon<sup>®</sup> processor E5 v4 family are based on the Broadwell microarchitecture and support Intel 64 architecture.

The Intel<sup>®</sup> Xeon<sup>®</sup> Scalable Processor Family, Intel<sup>®</sup> Xeon<sup>®</sup> processor E3-1500m v5 product family and 6th generation Intel<sup>®</sup> Core™ processors are based on the Skylake microarchitecture and support Intel 64 architecture.

The 7th generation Intel<sup>®</sup> Core™ processors are based on the Kaby Lake microarchitecture and support Intel 64 architecture.

The Intel Atom<sup>®</sup> processor C series, the Intel Atom<sup>®</sup> processor X series, the Intel<sup>®</sup> Pentium<sup>®</sup> processor J series, the Intel<sup>®</sup> Celeron<sup>®</sup> processor J series, and the Intel<sup>®</sup> Celeron<sup>®</sup> processor N series are based on the Goldmont microarchitecture.

The Intel<sup>®</sup> Xeon Phi™ Processor 3200, 5200, 7200 Series is based on the Knights Landing microarchitecture and supports Intel 64 architecture.

The Intel<sup>®</sup> Pentium<sup>®</sup> Silver processor series, the Intel<sup>®</sup> Celeron<sup>®</sup> processor J series, and the Intel<sup>®</sup> Celeron<sup>®</sup> processor N series are based on the Goldmont Plus microarchitecture.

The 8th generation Intel<sup>®</sup> Core™ processors, 9th generation Intel<sup>®</sup> Core™ processors, and Intel<sup>®</sup> Xeon<sup>®</sup> E processors are based on the Coffee Lake microarchitecture and support Intel 64 architecture.

The Intel<sup>®</sup> Xeon Phi™ Processor 7215, 7285, 7295 Series is based on the Knights Mill microarchitecture and supports Intel 64 architecture.

The 2nd generation Intel<sup>®</sup> Xeon<sup>®</sup> Scalable Processor Family is based on the Cascade Lake product and supports Intel 64 architecture.

Some 10th generation Intel<sup>®</sup> Core™ processors are based on the Ice Lake microarchitecture, and some are based on the Comet Lake microarchitecture; both support Intel 64 architecture.

Some 11th generation Intel<sup>®</sup> Core™ processors are based on the Tiger Lake microarchitecture, and some are based on the Rocket Lake microarchitecture; both support Intel 64 architecture.

Some 3rd generation Intel<sup>®</sup> Xeon<sup>®</sup> Scalable Processor Family processors are based on the Cooper Lake product, and some are based on the Ice Lake microarchitecture; both support Intel 64 architecture.

The 12th generation Intel<sup>®</sup> Core™ processors are based on the Alder Lake performance hybrid architecture and support Intel 64 architecture.

The 13th generation Intel<sup>®</sup> Core™ processors are based on the Raptor Lake performance hybrid architecture and support Intel 64 architecture.

The 4th generation Intel<sup>®</sup> Xeon<sup>®</sup> Scalable Processor Family is based on Sapphire Rapids microarchitecture and supports Intel 64 architecture.

IA-32 architecture is the instruction set architecture and programming environment for Intel's 32-bit microprocessors. Intel<sup>_®_</sup> 64 architecture is the instruction set architecture and programming environment which is the superset of Intel’s 32-bit and 64-bit architectures. It is compatible with the IA-32 architecture.

# 1.2 OVERVIEW OF VOLUME 2A, 2B, 2C, AND 2D: INSTRUCTION SET REFERENCE

A description of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volumes 2A, 2B, 2C & 2D_ content follows:

**Chapter 1 — About This Manual.** Gives an overview of all ten volumes of the _Intel® 64 and IA-32 Architectures Software Developer’s Manual_ . It also describes the notational conventions in these manuals and lists related Intel<sup>®</sup> manuals and documentation of interest to programmers and hardware designers.

**Chapter 2 — Instruction Format.** Describes the machine-level instruction format used for all IA-32 instructions and gives the allowable encodings of prefixes, the operand-identifier byte (ModR/M byte), the addressing-mode specifier byte (SIB byte), and the displacement and immediate bytes.

**Chapter 3 — Instruction Set Reference, A-L.** Describes Intel 64 and IA-32 instructions in detail, including an algorithmic description of operations, the effect on flags, the effect of operand- and address-size attributes, and

1-4 Vol. 2A

ABOUT THIS MANUAL

the exceptions that may be generated. The instructions are arranged in alphabetical order. General-purpose, x87 FPU, Intel MMX™ technology, SSE/SSE2/SSE3/SSSE3/SSE4 extensions, and system instructions are included.

**Chapter 4 — Instruction Set Reference, M-U.** Continues the description of Intel 64 and IA-32 instructions started in Chapter 3. It starts _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 2B_ .

**Chapter 5 — Instruction Set Reference, V.** Continues the description of Intel 64 and IA-32 instructions started in chapters 3 and 4. This chapter starts _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 2C_ .

**Chapter 6 — Instruction Set Reference, W-Z.** Continues the description of Intel 64 and IA-32 instructions started in chapters 3, 4, and 5. It provides the balance of the alphabetized list of instructions and starts _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 2D_ .

**Chapter 7 — Safer Mode Extensions Reference.** Describes the safer mode extensions (SMX). SMX is intended for a system executive to support launching a measured environment in a platform where the identity of the software controlling the platform hardware can be measured for the purpose of making trust decisions.

**Chapter 8— Instruction Set Reference Unique to Intel® Xeon Phi™ Processors.** Describes the instruction set that is unique to Intel® Xeon Phi™ processors based on the Knights Landing and Knights Mill microarchitectures. The set is not supported in any other Intel processors.

**Appendix A — Opcode Map.** Gives an opcode map for the IA-32 instruction set.

**Appendix B — Instruction Formats and Encodings.** Gives the binary encoding of each form of each IA-32 instruction.

**Appendix C — Intel**<sup>®</sup> **C/C** ++ **Compiler Intrinsics and Functional Equivalents.** Lists the Intel<sup>®</sup> C/C ++ compiler intrinsics and their assembly code equivalents for each of the IA-32 MMX and SSE/SSE2/SSE3 instructions.

# 1.3 NOTATIONAL CONVENTIONS

This manual uses specific notation for data-structure formats, for symbolic representation of instructions, and for hexadecimal and binary numbers. A review of this notation makes the manual easier to read.

## 1.3.1 Bit and Byte Order

In illustrations of data structures in memory, smaller addresses appear toward the bottom of the figure; addresses increase toward the top. Bit positions are numbered from right to left. The numerical value of a set bit is equal to two raised to the power of the bit position. IA-32 processors are “little endian” machines; this means the bytes of a word are numbered starting from the least significant byte. Figure 1-1 illustrates these conventions.



<!-- Start of picture text -->
Highest Data Structure<br>Address 31 24 23 16 15 8 7 0 Bit offset<br>28<br>24<br>20<br>16<br>12<br>8<br>4<br>Lowest<br>Byte 3 Byte 2 Byte 1 Byte 0 0 Address<br>Byte Offset<br><!-- End of picture text -->

Figure 1-1.  Bit and Byte Order

Vol. 2A 1-5

ABOUT THIS MANUAL

## 1.3.2 Reserved Bits and Software Compatibility

In many register and memory layout descriptions, certain bits are marked as **reserved** . When bits are marked as reserved, it is essential for compatibility with future processors that software treat these bits as having a future, though unknown, effect. The behavior of reserved bits should be regarded as not only undefined, but unpredictable. Software should follow these guidelines in dealing with reserved bits:

- Do not depend on the states of any reserved bits when testing the values of registers which contain such bits. Mask out the reserved bits before testing.

- Do not depend on the states of any reserved bits when storing to memory or to a register.

- Do not depend on the ability to retain information written into any reserved bits.

- When loading a register, always load the reserved bits with the values indicated in the documentation, if any, or reload them with values previously read from the same register.

### NOTE

Avoid any software dependence upon the state of reserved bits in IA-32 registers. Depending upon the values of reserved register bits will make software dependent upon the unspecified manner in which the processor handles these bits. Programs that depend upon reserved values risk incompatibility with future processors.

## 1.3.3 Instruction Operands

When instructions are represented symbolically, a subset of the IA-32 assembly language is used. In this subset, an instruction has the following format:

label: mnemonic argument1, argument2, argument3

where:

- A **label** is an identifier which is followed by a colon.

- A **mnemonic** is a reserved name for a class of instruction opcodes which have the same function.

- The operands _argument1_ , _argument2_ , and _argument3_ are optional. There may be from zero to three operands, depending on the opcode. When present, they take the form of either literals or identifiers for data items. Operand identifiers are either reserved names of registers or are assumed to be assigned to data items declared in another part of the program (which may not be shown in the example).

When two operands are present in an arithmetic or logical instruction, the right operand is the source and the left operand is the destination.

For example:

LOADREG: MOV EAX, SUBTOTAL

In this example, LOADREG is a label, MOV is the mnemonic identifier of an opcode, EAX is the destination operand, and SUBTOTAL is the source operand. Some assembly languages put the source and destination in reverse order.

## 1.3.4 Hexadecimal and Binary Numbers

Base 16 (hexadecimal) numbers are represented by a string of hexadecimal digits followed by the character H (for example, F82EH). A hexadecimal digit is a character from the following set: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, A, B, C, D, E, and F.

Base 2 (binary) numbers are represented by a string of 1s and 0s, sometimes followed by the character B (for example, 1010B). The “B” designation is only used in situations where confusion as to the type of number might arise.

1-6 Vol. 2A

ABOUT THIS MANUAL

## 1.3.5 Segmented Addressing

The processor uses byte addressing. This means memory is organized and accessed as a sequence of bytes. Whether one or more bytes are being accessed, a byte address is used to locate the byte or bytes in memory. The range of memory that can be addressed is called an **address space** .

The processor also supports segmented addressing. This is a form of addressing where a program may have many independent address spaces, called **segments** . For example, a program can keep its code (instructions) and stack in separate segments. Code addresses would always refer to the code space, and stack addresses would always refer to the stack space. The following notation is used to specify a byte address within a segment:

#### Segment-register:Byte-address

For example, the following segment address identifies the byte at address FF79H in the segment pointed by the DS register:

#### DS:FF79H

The following segment address identifies an instruction address in the code segment. The CS register points to the code segment and the EIP register contains the address of the instruction.

#### CS:EIP

## 1.3.6 Exceptions

An exception is an event that typically occurs when an instruction causes an error. For example, an attempt to divide by zero generates an exception. However, some exceptions, such as breakpoints, occur under other conditions. Some types of exceptions may provide error codes. An error code reports additional information about the error. An example of the notation used to show an exception and error code is shown below:

#### #PF(fault code)

This example refers to a page-fault exception under conditions where an error code naming a type of fault is reported. Under some conditions, exceptions which produce error codes may not be able to report an accurate code. In this case, the error code is zero, as shown below for a general-protection exception:

#### #GP(0)

## 1.3.7 A New Syntax for CPUID, CR, and MSR Values

Obtain feature flags, status, and system information by using the CPUID instruction, by checking control register bits, and by reading model-specific registers. We are moving toward a new syntax to represent this information. See Figure 1-2.

Vol. 2A 1-7

ABOUT THIS MANUAL



<!-- Start of picture text -->
CPUID Input and Output<br>CPUID.01H:EDX.SSE[bit 25] = 1<br>Input value for EAX register<br>Output register and feature flag or field<br>name with bit position(s)<br>Value (or range) of output<br>Control Register Values<br>CR4.OSFXSR[bit 9] = 1<br>Example CR name<br>Feature flag or field name<br>with bit position(s)<br>Value (or range) of output<br>Model-Specific Register Values<br>IA32_MISC_ENABLE.ENABLEFOPCODE[bit 2] = 1<br>Example MSR name<br>Feature flag or field name with bit position(s)<br>Value (or range) of output<br>SDM29002<br><!-- End of picture text -->

Figure 1-2.  Syntax for CPUID, CR, and MSR Data Presentation

# 1.4 RELATED LITERATURE

Literature related to Intel 64 and IA-32 processors is listed and viewable on-line at: https://software.intel.com/en-us/articles/intel-sdm

See also:

- The latest security information on Intel<sup>®</sup> products:

https://www.intel.com/content/www/us/en/security-center/default.html

- Software developer resources, guidance, and insights for security advisories: https://software.intel.com/security-software-guidance/

- The data sheet for a particular Intel 64 or IA-32 processor

- The specification update for a particular Intel 64 or IA-32 processor

- Intel<sup>®</sup> C++ Compiler documentation and online help: http://software.intel.com/en-us/articles/intel-compilers/

1-8 Vol. 2A

ABOUT THIS MANUAL

- Intel<sup>®</sup> Fortran Compiler documentation and online help: http://software.intel.com/en-us/articles/intel-compilers/

- Intel<sup>®</sup> Software Development Tools: https://software.intel.com/en-us/intel-sdp-home

- Intel<sup>®</sup> 64 and IA-32 Architectures Software Developer’s Manual (in one, four or ten volumes): https://software.intel.com/en-us/articles/intel-sdm

- Intel<sup>®</sup> 64 and IA-32 Architectures Optimization Reference Manual: https://software.intel.com/en-us/articles/intel-sdm#optimization

- Intel<sup>®</sup> Trusted Execution Technology Measured Launched Environment Programming Guide:

http://www.intel.com/content/www/us/en/software-developers/intel-txt-software-development-guide.html

- Intel<sup>®</sup> Software Guard Extensions (Intel<sup>®</sup> SGX) Information https://software.intel.com/en-us/isa-extensions/intel-sgx

- Developing Multi-threaded Applications: A Platform Consistent Approach: https://software.intel.com/sites/default/files/article/147714/51534-developing-multithreaded-applications.pdf

- Using Spin-Loops on Intel<sup>®</sup> Pentium<sup>®</sup> 4 Processor and Intel<sup>®</sup> Xeon<sup>®</sup> Processor: https://software.intel.com/sites/default/files/22/30/25602

- Performance Monitoring Unit Sharing Guide http://software.intel.com/file/30388

Literature related to select features in future Intel processors are available at:

- Intel<sup>®</sup> Architecture Instruction Set Extensions Programming Reference https://software.intel.com/en-us/isa-extensions

More relevant links are:

- Intel<sup>®</sup> Developer Zone:

https://software.intel.com/en-us

- Developer centers:

http://www.intel.com/content/www/us/en/hardware-developers/developer-centers.html

- Processor support general link:

http://www.intel.com/support/processors/

- Intel<sup>®</sup> Hyper-Threading Technology (Intel<sup>®</sup> HT Technology): http://www.intel.com/technology/platform-technology/hyper-threading/index.htm

Vol. 2A 1-9

ABOUT THIS MANUAL

1-10 Vol. 2A
