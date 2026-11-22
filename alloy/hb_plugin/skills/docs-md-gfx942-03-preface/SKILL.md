---
name: docs-md-gfx942-03-preface
description: "AMD CDNA3 ISA: Preface (vendor documentation for AMD gfx942 (CDNA3))."
when: "when you need AMD CDNA3 ISA: Preface while writing a kernel for AMD gfx942 (CDNA3)."
---

"AMD Instinct MI300" Instruction Set Architecture



# **Preface**

## **About This Document**

This document describes the current environment, organization and program state of AMD CDNA "Instinct MI300" devices. It details the instruction set and the microcode formats native to this family of processors that are accessible to programmers and compilers.

The document specifies the instructions (including the format of each type of instruction) and the relevant program state (including how the program state interacts with the instructions). Some instruction fields are mutually dependent; not all possible settings for all fields are legal. This document specifies the valid combinations.

The main purposes of this document are to:

1. Specify the language constructs and behavior, including the organization of each type of instruction in both text syntax and binary format.

2. Provide a reference of instruction operation that compiler writers can use to maximize performance of the processor.

## **Audience**

This document is intended for programmers writing application and system software, including operating systems, compilers, loaders, linkers, device drivers, and system utilities. It assumes that programmers are writing compute-intensive parallel applications (streaming applications) and assumes an understanding of requisite programming practices.

## **Organization**

This document begins with an overview of the AMD CDNA processors' hardware and programming environment (Chapter 1).

Chapter 2 describes the organization of CDNA programs.

Chapter 3 describes the program state that is maintained.

Chapter 4 describes the program flow.

Chapter 5 describes the scalar ALU operations. Chapter 6 describes the vector ALU operations. Chapter 7 describes the vector Matrix ALU operations. Chapter 8 describes the scalar memory operations.

Chapter 9 describes the vector memory operations.

Chapter 10 provides information about the flat memory instructions.

Chapter 11 describes the data share operations.

Chapter 12 describes instruction details, first by the microcode format to which they belong, then in alphabetic order.

Finally, Chapter 13 provides a detailed specification of each microcode format.

1 of 553

About This Document

"AMD Instinct MI300" Instruction Set Architecture



## **Conventions**

The following conventions are used in this document:

|mono-spaced font|A filename, file path or code.|
|---|---|
|*|Any number of alphanumeric characters in the name of a code format, parameter, or<br>instruction.|
|< >|Angle brackets denote streams.|
|[1,2)|A range that includes the left-most value (in this case, 1), but excludes the right-most<br>value (in this case, 2).|
|[1,2]|A range that includes both the left-most and right-most values.|
|{x| y}|One of the multiple options listed. In this case, X or Y.|
|0.0|A single-precision (32-bit) floating-point value.|
|1011b|A binaryvalue, in this example a 4-bit value.|
|7:4|A bit range, from bit 7 to bit 4, inclusive. The high-order bit is shown first.|
|_italicized word or phrase_|The first use of a term or concept basic to the understanding of stream computing.|



## **Contact Information**

For information concerning AMD Accelerated Parallel Processing development, please see: http://developer.amd.com/

2 of 553

Conventions
