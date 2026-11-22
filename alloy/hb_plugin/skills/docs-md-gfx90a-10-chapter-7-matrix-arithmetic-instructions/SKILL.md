---
name: docs-md-gfx90a-10-chapter-7-matrix-arithmetic-instructions
description: "AMD CDNA2 ISA: Chapter 7. Matrix Arithmetic Instructions (MAI) (vendor documentation for AMD gfx90a (CDNA2))."
when: "when you need AMD CDNA2 ISA: Chapter 7. Matrix Arithmetic Instructions (MAI) while writing a AMD gfx90a (CDNA2) kernel."
---

"AMD Instinct MI200" Instruction Set Architecture



# **Chapter 7. Matrix Arithmetic Instructions (MAI)**

MAI is an extension to CDNA architecture shader instruction set supporting the new Machine Intelligence SIMD (miSIMD). The new miSIMD has its own VGPR file: the Accumulation ("Acc") GPRs. This is separate from the normal (Architectural, or "Arch") VGPRs in the original SIMD. Shader I/O can only use both types of VGPRs. Instructions have an ACC bit to indicate if data is transferred to/from architectural or accumulation VGPRs.

The primary operation of the miSIMD is a 4-way DOT product:

D.f32 = A.f16[0] * B.f16[0] + A.f16[1] * B.f16[1] + A.f16[2] * B.f16[2] + A.f16[3] * B.f16[3] + C.f32

The diagram below illustrates how these new MFMA operations can be used to perform matrix multiplication:



The dot product uses 4 matrices: A, B, C and D.

The A and B matrices are source data and can come from either Arch or Acc VGPRs. The C matrix is the accumulation source matrix, and comes from Acc VGPRs. The D matrix is the result matrix, and uses the Acc VGPRs.

Data can be moved between the ACC and ARCH VGPRs via the V_ACCVGPR_READ and V_ACCVGPR_WRITE instructions.

## **7.1. Matrix Arithmetic Opcodes**

These instructions use the VOP3P-MAI instruction encoding.

Matrix-Fused-Multiply-Add (MFMA) instructions perform the dot-product and support mixed

7.1. Matrix Arithmetic Opcodes

45 of 267

"AMD Instinct MI200" Instruction Set Architecture



precision. The first format specifier (F32 or I32) indicates the data format of the C and D matrices, and the final format specifier (F32, F16, I8 or BF16) indicates the data format of the A and B matrices.

### **MFMA Instruction Naming:**

### V_MFMA_ **CDFmt** _MxNxK **ABFmt**

- CDfmt is the data format of the C & D matrices

- ABfmt is the data format of the A & B matrices

- Partial results of the calculation are performed in CDfmt

### **M, N and K are matrix dimensions** :

- mA[M][K] Source A matrix

- mB[K][N] Source B matrix

- mC[M][N] Accumulation input matrix C

- mD[M][N] Accumulation result matrix C

_Table 25. VOP3P-MAI VALU Opcodes:_

|**Instruction**|**Variants**|**Description**|
|---|---|---|
|V_MFMA_F32_{*}F32|32x32x1<br>16x16x1<br>4x4x1<br>32x32x2<br>16x16x4|Matrix multiply, using FMA with F32 A & B matrices.<br>Supports denorm allow/flush from MODE.denorm.|
|V_MFMA_F32_{*}F16|32x32x4<br>16x16x4<br>4x4x4<br>32x32x8<br>16x16x16|Matrix multiply, using FMA with F16 A & B matrices. Flushes<br>input and output denorms.|
|V_MFMA_I32_{*}I8|32x32x4<br>16x16x4<br>4x4x4<br>32x32x8<br>16x16x16|Matrix multiply, using FMA with I8 A & B matrices.|
|V_MFMA_F32_{*}_BF16|32x32x2<br>16x16x2<br>4x4x2<br>32x32x4<br>16x16x8|Matrix multiply, using FMA with BF16 A & B matrices.<br>Flushes input and output denorms.|



7.1. Matrix Arithmetic Opcodes

46 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Instruction**|**Variants**|**Description**|
|---|---|---|
|V_MFMA_{*}_BF16_1K|4x4x4<br>16x16x4|Matrix multiply, using FMA with BF16. Flushes input and<br>output denorms.|
||16x16x16||
||32x32x4<br>32x32x8||
||16x16x16||
|V_MFMA_F64_{*}_F64|16x16x4<br>4x4x4|Matrix Multiply on F64 data. Ignores MODE and forces:<br>round to nearest even, allow input and output denorms.|



MFMA instructions do not support the following inline constants:

- SGPRs, SRC_SHARED*, SRC_PRIVATE*, DPP, SDWA, VCCZ, EXECZ, SCC, LDS_DIRECT, LITERAL

- The following inline constants are interpreted as FP32 for all V_MFMA and V_ACCVGPR instructions:

0.5, -0,5, 1.0, -1.0, 2.0, -2.0, 4.0, -4.0

The miSIMD does not support arithmetic exceptions.

## **7.2. Dependency Resolution: Required NOPs**

The table below indicates timing conditions which require the user to insert NOPs (or independent instructions).

**DLop** Dot products

**XDLOP** Matrix math

_Table 26. VOP3P-MAI Opcodes Required NOPs_

|**First Instruction**|**Second Instruction**|**SW Inserted**<br>**Waits (NOPs)**|**Comments**|
|---|---|---|---|
|VALU op (non-|V_MFMA|2|-|
|DLop) writes<br>VGPR||||
|DL op writes<br>VGPR|DLop reads VGPR as SrcC and<br>opcode is the same as previous<br>op|0|Supports same opcode of DLops back-to-<br>back SrcC forwarding which is used for<br>accumulation|
||DLop reads VGPR as SrcA or|3|-|
||SrcB and opcode is the same|||
||Different opcode|3|-|



7.2. Dependency Resolution: Required NOPs

47 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**First Instruction**|**Second Instruction**|**SW Inserted**<br>**Waits (NOPs)**|**Comments**|
|---|---|---|---|
|XDL op writes<br>VGPR|V_MFMA reads VGPR as SrcC<br>the same as previous op|0|-|
||XDL reads VGPR as SrcC<br>overlapped with first Vdst|2 if 1st is<br>V_MFMA 2<br>pass|-|
|||8 if 1st is<br>V_MFMA 8<br>pass|-|
|||16 if 1st is<br>V_MFMA 16<br>pass|-|
||DGEMM reads VGPR as SrcC<br>overlapped with first Vdst|3 if 1st is<br>V_MFMA 2<br>pass|-|
|||9 if 1st is<br>V_MFMA 8<br>pass|-|
|||17 if 1st is<br>V_MFMA 16<br>pass|-|
||V_MFMA reads VGPR as SrcA or<br>SrcB|5 if 1st is<br>V_MFMA 2<br>pass|-|
|||11 if 1st is<br>V_MFMA 8<br>pass|-|
|||19 if 1st is<br>V_MFMA 16<br>pass|-|
||VMEM, LDS, Flat orverlapped<br>with 1st Vdst, or VALU read/write<br>VGPR|5 if 1st is<br>V_MFMA 2<br>pass|-|
|||11 if 1st is<br>V_MFMA 8<br>pass|-|
|||19 if 1st is<br>V_MFMA 16<br>pass|-|



7.2. Dependency Resolution: Required NOPs

48 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**First Instruction**|**Second Instruction**|**SW Inserted**<br>**Waits (NOPs)**|**Comments**|
|---|---|---|---|
|XDL Read VGPR<br>SrcC|VALU writes VGPR (WAR hazard)|1 if 1st is<br>V_MFMA 2<br>pass|-|
|||11 if 1st is<br>V_MFMA 8<br>pass|-|
|||19 if 1st is<br>V_MFMA 16<br>pass|-|
|V_MFMA_16x16<br>x4_F64|V_MFMA_16x16x4_F64 reads<br>VGPR as SrcC same as Vdst of<br>first op|0|the two MFMA must have the same number<br>of passes|
||DGEMM read VGPR as SrcC<br>overlapped with 1st Vdst|9|-|
||XDL reads VGPR as SrcC<br>overlapped with first Vdst|0|-|
||DGEMM reads VGPR as SrcA or<br>SrcB|11|-|
||XDL reads VGPR as SrcA or SrcB|11|-|
||VALU read/writes VGPR|11|-|
||VMEM, LDS, Flat reads VGPR<br>overlapped with first Vdst|18|-|
|V_MFMA_4x4x4<br>_F64|V_MFMA_4xx4_F64 reads VGPR<br>as SrcC same as Vdst of first op|4|the two MFMA must have the same number<br>of passes|
||DGEMM read VGPR as SrcC<br>overlapped with 1st Vdst|4|-|
||XDL reads VGPR as SrcC<br>overlapped with first Vdst|0|-|
||DGEMM reads VGPR as SrcA or<br>SrcB|6|-|
||XDL reads VGPR as SrcA or SrcB|6|-|
||VALU read/writes VGPR|6|-|
||VMEM, LDS, Flat reads VGPR<br>overlapped with first Vdst|9|-|
|V_CMPX writes<br>EXEC|V_MFMA_*|4|-|



- "DGEMM" means V_MFMA…F64

- "XDL" means V_MFMA…{I8, F16, BF16, F32}

7.2. Dependency Resolution: Required NOPs

49 of 267
