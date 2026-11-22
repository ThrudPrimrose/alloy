---
name: docs-md-gfx90a-03-preface
description: "AMD CDNA2 ISA: Preface (vendor documentation for AMD gfx90a (CDNA2))."
when: "when you need AMD CDNA2 ISA: Preface while writing a kernel for AMD gfx90a (CDNA2)."
---

"AMD Instinct MI200" Instruction Set Architecture



# **Preface**

## **About This Document**

This document describes the current environment, organization and program state of AMD CDNA "Instinct MI200" devices. It details the instruction set and the microcode formats native to this family of processors that are accessible to programmers and compilers.

The document specifies the instructions (include the format of each type of instruction) and the relevant program state (including how the program state interacts with the instructions). Some instruction fields are mutually dependent; not all possible settings for all fields are legal. This document specifies the valid combinations.

The main purposes of this document are to:

1. Specify the language constructs and behavior, including the organization of each type of instruction in both text syntax and binary format.

2. Provide a reference of instruction operation that compiler writers can use to maximize performance of the processor.

## **Audience**

This document is intended for programmers writing application and system software, including operating systems, compilers, loaders, linkers, device drivers, and system utilities. It assumes that programmers are writing compute-intensive parallel applications (streaming applications) and assumes an understanding of requisite programming practices.

## **Organization**

This document begins with an overview of the AMD CDNA processors' hardware and programming environment (Chapter 1).

Chapter 2 describes the organization of CDNA programs.

Chapter 3 describes the program state that is maintained. Chapter 4 describes the program flow. Chapter 5 describes the scalar ALU operations. Chapter 6 describes the vector ALU operations. Chapter 7 describes the vector Matrix ALU operations. Chapter 8 describes the scalar memory operations. Chapter 9 describes the vector memory operations. Chapter 10 provides information about the flat memory instructions. Chapter 11 describes the data share operations.

Chapter 12 describes instruction details, first by the microcode format to which they belong,

About This Document

1 of 267

"AMD Instinct MI200" Instruction Set Architecture



#### then in alphabetic order.

Finally, Chapter 13 provides a detailed specification of each microcode format.

## **Conventions**

The following conventions are used in this document:

|mono-spaced font|A filename, file path or code.|
|---|---|
|*|Any number of alphanumeric characters in the name of a code format,<br>parameter, or instruction.|
|< >|Angle brackets denote streams.|
|[1,2)|A range that includes the left-most value (in this case, 1), but excludes the right-<br>most value (in this case, 2).|
|[1,2]|A range that includes both the left-most and right-most values.|
|{x | y}|One of the multiple options listed. In this case, X or Y.|
|0.0|A single-precision (32-bit) floating-point value.|
|1011b|A binary value, in this example a 4-bit value.|
|7:4|A bit range, from bit 7 to bit 4, inclusive. The high-order bit is shown first.|
|_italicized word or phrase_|The first use of a term or concept basic to the understanding of stream<br>computing.|



## **Feature Changes in MI200 devices**

- Supports DPP for 64-bit data types

- Float64 memory atomic operations: ACC, MIN, MAX

- Merged Architectural and Accumulation VGPRs into one unified pool of VGPRs

- Allow memory operations to return data directly to accumulation VGPRs

- Remove GDS operations (retain GWS operations)

- Merged compute shader thread indices into a single VGPR

- Remove support for "SRC2" DS instructions

### **Removed all IMAGE and GATHER instructions except for the following:**

|IMAGE_LOAD|IMAGE_ATOMIC_AND|
|---|---|
|IMAGE_LOAD_MIP|IMAGE_ATOMIC_OR|
|IMAGE_STORE|IMAGE_ATOMIC_XOR|
|IMAGE_STORE_MIP|IMAGE_ATOMIC_INC|



Conventions

2 of 267

"AMD Instinct MI200" Instruction Set Architecture



|IMAGE_GET_RESINFO|IMAGE_ATOMIC_DEC|
|---|---|
|IMAGE_ATOMIC_SWAP|IMAGE_LOAD_PCK|
|IMAGE_ATOMIC_CMPSWAP|IMAGE_LOAD_PCK_SGN|
|IMAGE_ATOMIC_ADD|IMAGE_LOAD_MIP_PCK|
|IMAGE_ATOMIC_SUB|IMAGE_LOAD_MIP_PCK_SGN|
|IMAGE_ATOMIC_SMIN|IMAGE_STORE_PCK|
|IMAGE_ATOMIC_UMIN|IMAGE_STORE_MIP_PCK|
|IMAGE_ATOMIC_SMAX||
|IMAGE_ATOMIC_UMAX|IMAGE_SAMPLE|



### **Added Matrix Arithmetic Instructions:**

- V_MFMA_F32_{4x4x4, 16x16x4, 16x16x16, 32x32x4, 32x32x8, 16x16x16}BF16_1K

- V_MFMA_F64_{16x16x4f64, 4x4x4f64 }

### **FP32 Packed Math**

- V_PK_FMA_F32

- V_PK_MUL_F32

- V_PK_ADD_F32

- V_PK_MOV_B32

## **Contact Information**

For information concerning AMD Accelerated Parallel Processing development, please see: http://developer.amd.com/ .

For information about developing with AMD Accelerated Parallel Processing, please see: developer.amd.com/appsdk .

AMD also has a growing community of AMD Accelerated Parallel Processing users. Come visit us at the AMD Accelerated Parallel Processing Developer Forum ( http://developer.amd.com/ openclforum ) to find out what applications other users are trying on their AMD Accelerated Parallel Processing products.

Contact Information

3 of 267
