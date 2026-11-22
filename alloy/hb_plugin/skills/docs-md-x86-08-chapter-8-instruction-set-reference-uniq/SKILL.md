---
name: docs-md-x86-08-chapter-8-instruction-set-reference-uniq
description: "Intel SDM Vol. 2: Chapter 8 Instruction Set Reference Unique to Intel\u00ae Xeon Phi\u2122 Processors (vendor documentation for x86 AVX2, AVX-512 and AVX-512 FP16)."
when: "when you need Intel SDM Vol. 2: Chapter 8 Instruction Set Reference Unique to Intel\u00ae Xeon Phi\u2122 Processors while writing a kernel for x86 AVX2, AVX-512 and AVX-512 FP16."
---

CHAPTER 8 INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

This chapter describes the instruction set that is unique to Intel<sup>®</sup> Xeon Phi™ Processors based on the Knights Landing and Knights Mill microarchitectures. The set is not supported in any other Intel processors. Included are Intel<sup>®</sup> AVX-512 instructions. For additional instructions supported on these processors, see Chapter 3, “Instruction Set Reference, A-L”; Chapter 4, “Instruction Set Reference, M-U”; Chapter 5, “Instruction Set Reference, V”; and Chapter 6, “Instruction Set Reference, W-Z”.

Vol. 2D 8-1

INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

# PREFETCHWT1—Prefetch Vector Data Into Caches with Intent to Write and T1 Hint

|Opcode/|Op/|64/32 bit|CPUID Feature|Description|
|---|---|---|---|---|
|Instruction|En|Mode|Flag||
|||Support|||
|0F 0D /2|M|V/V|PREFETCHWT1|Move data from m8 closer to the processor using T1 hint|
|PREFETCHWT1 m8||||with intent to write.|



## Instruction Operand Encoding

|Op/En|Operand 1|Operand 2|Operand 3|Operand 4|
|---|---|---|---|---|
|M|ModRM:r/m (r)|NA|NA|NA|



## Description

Fetches the line of data from memory that contains the byte specified with the source operand to a location in the cache hierarchy specified by an intent to write hint (so that data is brought into ‘Exclusive’ state via a request for ownership) and a locality hint:

• T1 (temporal data with respect to first level cache)—prefetch data into the second level cache.

The source operand is a byte memory location. (The locality hints are encoded into the machine level instruction using bits 3 through 5 of the ModR/M byte. Use of any ModR/M value other than the specified ones will lead to unpredictable behavior.)

If the line selected is already present in the cache hierarchy at a level closer to the processor, no data movement occurs. Prefetches from uncacheable or WC memory are ignored.

The PREFETCHWT1 instruction is merely a hint and does not affect program behavior. If executed, this instruction moves data closer to the processor in anticipation of future use.

The implementation of prefetch locality hints is implementation-dependent, and can be overloaded or ignored by a processor implementation. The amount of data prefetched is also processor implementation-dependent. It will, however, be a minimum of 32 bytes. Additional details of the implementation-dependent locality hints are described in Section 9.5, “Memory Optimization Using Prefetch” of the Intel® 64 and IA-32 Architectures Optimization Reference Manual.

It should be noted that processors are free to speculatively fetch and cache data from system memory regions that are assigned a memory-type that permits speculative reads (that is, the WB, WC, and WT memory types). A PREFETCHWT1 instruction is considered a hint to this speculative behavior. Because this speculative fetching can occur at any time and is not tied to instruction execution, a PREFETCHWT1 instruction is not ordered with respect to the fence instructions (MFENCE, SFENCE, and LFENCE) or locked memory references. A PREFETCHWT1 instruction is also unordered with respect to CLFLUSH and CLFLUSHOPT instructions, other PREFETCHWT1 instructions, or any other general instruction. It is ordered with respect to serializing instructions such as CPUID, WRMSR, OUT, and MOV CR.

This instruction’s operation is the same in non-64-bit modes and 64-bit mode.

## Operation

PREFETCH(mem, Level, State) Prefetches a byte memory location pointed by ‘mem’ into the cache level specified by ‘Level’; a request for exclusive/ownership is done if ‘State’ is 1. Note that the memory location ignore cache line splits. This operation is considered a hint for the processor and may be skipped depending on implementation.

Prefetch (m8, Level = 1, EXCLUSIVE=1);

## Flags Affected

All flags are affected

## C/C++ Compiler Intrinsic Equivalent

void _mm_prefetch( char const *, int hint= _MM_HINT_ET1);

PREFETCHWT1—Prefetch Vector Data Into Caches with Intent to Write and T1 Hint

8-2 Vol. 2D

INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

Protected Mode Exceptions #UD If the LOCK prefix is used. Real-Address Mode Exceptions #UD If the LOCK prefix is used. Virtual-8086 Mode Exceptions #UD If the LOCK prefix is used. Compatibility Mode Exceptions #UD If the LOCK prefix is used. 64-Bit Mode Exceptions #UD If the LOCK prefix is used.

PREFETCHWT1—Prefetch Vector Data Into Caches with Intent to Write and T1 Hint

Vol. 2D 8-3

INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

# V4FMADDPS/V4FNMADDPS — Packed Single Precision Floating-Point Fused Multiply-Add

<u>(4-iterations)</u>

|Opcode/<br>Instruction|Op/<br>En|64/32<br>bit Mode<br>Support|CPUID Feature<br>Flag|Description|
|---|---|---|---|---|
|EVEX.512.F2.0F38.W0 9A /r<br>V4FMADDPS zmm1{k1}{z}, zmm2+3,<br>m128|A|V/V|AVX512_4FMAPS|Multiply packed single-precision floating-point<br>values from source register block indicated by<br>zmm2 by values from m128 and accumulate the<br>result in zmm1.|
|EVEX.512.F2.0F38.W0 AA /r<br>V4FNMADDPS zmm1{k1}{z},<br>zmm2+3, m128|A|V/V|AVX512_4FMAPS|Multiply and negate packed single-precision<br>floating-point values from source register block<br>indicated by zmm2 by values from m128 and<br>accumulate the result in zmm1.|



## Instruction Operand Encoding

|Op/En|Tuple|Operand 1|Operand 2|Operand 3|Operand 4|
|---|---|---|---|---|---|
|A|Tuple1_4X|ModRM:reg (r, w)|EVEX.vvvv (r)|ModRM:r/m (r)|NA|



### Description

This instruction computes 4 sequential packed fused single-precision floating-point multiply-add instructions with a sequentially selected memory operand in each of the four steps.

In the above box, the notation of “+3” is used to denote that the instruction accesses 4 source registers based on that operand; sources are consecutive, start in a multiple of 4 boundary, and contain the encoded register operand.

This instruction supports memory fault suppression. The entire memory operand is loaded if any of the 16 lowest significant mask bits is set to 1 or if a “no masking” encoding is used.

The tuple type Tuple1_4X implies that four 32-bit elements (16 bytes) are referenced by the memory operation portion of this instruction.

Rounding is performed at every FMA (fused multiply and add) boundary. Exceptions are also taken sequentially. Pre- and post-computational exceptions of the first FMA take priority over the pre- and post-computational exceptions of the second FMA, etc.

V4FMADDPS/V4FNMADDPS — Packed Single Precision Floating-Point Fused Multiply-Add (4-iterations)

8-4 Vol. 2D

INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

### Operation

src_reg_id is the 5 bit index of the vector register specified in the instruction as the src1 register.

define NFMA_PS(kl, vl, dest, k1, msrc, regs_loaded, src_base, posneg): tmpdest := dest

// reg[] is an array representing the SIMD register file. FOR j := 0 to regs_loaded-1: FOR i := 0 to kl-1: IF k1[i] or *no writemask*: IF posneg = 0: tmpdest.single[i] := RoundFPControl_MXCSR(tmpdest.single[i] - reg[src_base + j ].single[i] * msrc.single[j]) ELSE: tmpdest.single[i] := RoundFPControl_MXCSR(tmpdest.single[i] + reg[src_base + j ].single[i] * msrc.single[j]) ELSE IF *zeroing*: tmpdest.single[i] := 0 dest := tmpdst dest[MAX_VL-1:VL] := 0

V4FMADDPS and V4FNMADDPS dest{k1}, src1, msrc (AVX512) KL, VL = (16,512)

regs_loaded := 4 src_base := src_reg_id & ~3 // for src1 operand posneg := 0 if negative form, 1 otherwise NFMA_PS(kl, vl, dest, k1, msrc, regs_loaded, src_base, posneg)

### Intel C/C++ Compiler Intrinsic Equivalent

V4FMADDPS __m512 _mm512_4fmadd_ps( __m512, __m512x4, __m128 *); V4FMADDPS __m512 _mm512_mask_4fmadd_ps(__m512, __mmask16, __m512x4, __m128 *); V4FMADDPS __m512 _mm512_maskz_4fmadd_ps(__mmask16, __m512, __m512x4, __m128 *); V4FNMADDPS __m512 _mm512_4fnmadd_ps(__m512, __m512x4, __m128 *); V4FNMADDPS __m512 _mm512_mask_4fnmadd_ps(__m512, __mmask16, __m512x4, __m128 *); V4FNMADDPS __m512 _mm512_maskz_4fnmadd_ps(__mmask16, __m512, __m512x4, __m128 *);

SIMD Floating-Point Exceptions Overflow, Underflow, Invalid, Precision, Denormal.

Other Exceptions

See Type E2; additionally #UD If the EVEX broadcast bit is set to 1. #UD If the MODRM.mod = 0b11.

V4FMADDPS/V4FNMADDPS — Packed Single Precision Floating-Point Fused Multiply-Add (4-iterations)

Vol. 2D 8-5

INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

# V4FMADDSS/V4FNMADDSS —Scalar Single Precision Floating-Point Fused Multiply-Add

||(4-i|terations|)||
|---|---|---|---|---|
|Opcode/<br>Instruction|Op/<br>En|64/32<br>bit Mode<br>Support|CPUID Feature<br>Flag|Description|
|EVEX.LLIG.F2.0F38.W0 9B /r<br>V4FMADDSS xmm1{k1}{z},<br>xmm2+3, m128|A|V/V|AVX512_4FMAPS|Multiply scalar single-precision floating-point<br>values from source register block indicated by<br>xmm2 by values from m128 and accumulate the<br>result in xmm1.|
|EVEX.LLIG.F2.0F38.W0 AB /r<br>V4FNMADDSS xmm1{k1}{z},<br>xmm2+3, m128|A|V/V|AVX512_4FMAPS|Multiply and negate scalar single-precision<br>floating-point values from source register block<br>indicated by xmm2 by values from m128 and<br>accumulate the result in xmm1.|



## Instruction Operand Encoding

|Op/En|Tuple|Operand 1|Operand 2|Operand 3|Operand 4|
|---|---|---|---|---|---|
|A|Tuple1_4X|ModRM:reg (r, w)|EVEX.vvvv (r)|ModRM:r/m (r)|NA|



### Description

This instruction computes 4 sequential scalar fused single-precision floating-point multiply-add instructions with a sequentially selected memory operand in each of the four steps.

In the above box, the notation of “+3” is used to denote that the instruction accesses 4 source registers based that operand; sources are consecutive, start in a multiple of 4 boundary, and contain the encoded register operand.

This instruction supports memory fault suppression. The entire memory operand is loaded if the least significant mask bit is set to 1 or if a “no masking” encoding is used.

The tuple type Tuple1_4X implies that four 32-bit elements (16 bytes) are referenced by the memory operation portion of this instruction.

Rounding is performed at every FMA boundary. Exceptions are also taken sequentially. Pre- and post-computational exceptions of the first FMA take priority over the pre- and post-computational exceptions of the second FMA, etc.

### Operation

src_reg_id is the 5 bit index of the vector register specified in the instruction as the src1 register.

define NFMA_SS(vl, dest, k1, msrc, regs_loaded, src_base, posneg): tmpdest := dest // reg[] is an array representing the SIMD register file. IF k1[0] or *no writemask*:

FOR j := 0 to regs_loaded - 1:

IF posneg = 0:

tmpdest.single[0] := RoundFPControl_MXCSR(tmpdest.single[0] - reg[src_base + j ].single[0] * msrc.single[j]) ELSE:

tmpdest.single[0] := RoundFPControl_MXCSR(tmpdest.single[0] + reg[src_base + j ].single[0] * msrc.single[j]) ELSE IF *zeroing*:

tmpdest.single[0] := 0 dest := tmpdst dest[MAX_VL-1:VL] := 0

V4FMADDSS/V4FNMADDSS —Scalar Single Precision Floating-Point Fused Multiply-Add (4-iterations)

8-6 Vol. 2D

INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

V4FMADDSS and V4FNMADDSS dest{k1}, src1, msrc (AVX512) VL = 128

regs_loaded := 4 src_base := src_reg_id & ~3 // for src1 operand posneg := 0 if negative form, 1 otherwise NFMA_SS(vl, dest, k1, msrc, regs_loaded, src_base, posneg)

Intel C/C++ Compiler Intrinsic Equivalent

V4FMADDSS __m128 _mm_4fmadd_ss(__m128, __m128x4, __m128 *); V4FMADDSS __m128 _mm_mask_4fmadd_ss(__m128, __mmask8, __m128x4, __m128 *); V4FMADDSS __m128 _mm_maskz_4fmadd_ss(__mmask8, __m128, __m128x4, __m128 *); V4FNMADDSS __m128 _mm_4fnmadd_ss(__m128, __m128x4, __m128 *); V4FNMADDSS __m128 _mm_mask_4fnmadd_ss(__m128, __mmask8, __m128x4, __m128 *); V4FNMADDSS __m128 _mm_maskz_4fnmadd_ss(__mmask8, __m128, __m128x4, __m128 *);

SIMD Floating-Point Exceptions

Overflow, Underflow, Invalid, Precision, Denormal.

Other Exceptions

See Type E2; additionally #UD If the EVEX broadcast bit is set to 1. #UD If the MODRM.mod = 0b11.

V4FMADDSS/V4FNMADDSS —Scalar Single Precision Floating-Point Fused Multiply-Add (4-iterations)

Vol. 2D 8-7

INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

VEXP2PD—Approximation to the Exponential 2^x of Packed Double Precision Floating-Point Values with Less Than 2^-23 Relative Error

|Opcode/<br>Instruction|Op /<br>En|64/32<br>bit Mode<br>Support|CPUID<br>Feature<br>Flag|Description|
|---|---|---|---|---|
|EVEX.512.66.0F38.W1 C8 /r|A|V/V|AVX512ER|Computes approximations to the exponential 2^x (with less|
|VEXP2PD zmm1 {k1}{z},<br>zmm2/m512/m64bcst {sae}||||than 2^-23 of maximum relative error) of the packed double<br>precision floating-point values from zmm2/m512/m64bcst and<br>stores the floating-point result in zmm1with writemask k1.|



|||Instru|ction Operand Encodin|g||
|---|---|---|---|---|---|
|Op/En|Tuple Type|Operand 1|Operand 2|Operand 3|Operand 4|
|A|Full|ModRM:reg (r, w)|ModRM:r/m (r)|NA|NA|



### Description

Computes the approximate base-2 exponential evaluation of the double precision floating-point values in the source operand (the second operand) and stores the results to the destination operand (the first operand) using the writemask k1. The approximate base-2 exponential is evaluated with less than 2^-23 of relative error. Denormal input values are treated as zeros and do not signal #DE, irrespective of MXCSR.DAZ. Denormal results are flushed to zeros and do not signal #UE, irrespective of MXCSR.FTZ.

The source operand is a ZMM register, a 512-bit memory location or a 512-bit vector broadcasted from a 64-bit memory location. The destination operand is a ZMM register, conditionally updated using writemask k1.

EVEX.vvvv is reserved and must be 1111b otherwise instructions will #UD.

A numerically exact implementation of VEXP2xx can be found at <u>https://software.intel.com/en-us/articles/reference-implementations-for-IA-approximation-instructions-vrcp14-vrsqrt14-vrcp28-vrsqrt28-vexp2.</u>

### Operation

### VEXP2PD

(KL, VL) = (8, 512) FOR j := 0 TO KL-1

i := j * 64

IF k1[j] OR *no writemask* THEN IF (EVEX.b = 1) AND (SRC *is memory*)

THEN DEST[i+63:i] := EXP2_23_DP(SRC[63:0]) ELSE DEST[i+63:i] := EXP2_23_DP(SRC[i+63:i])

FI;

### ELSE

IF *merging-masking* ; merging-masking THEN *DEST[i+63:i] remains unchanged* ELSE ; zeroing-masking DEST[i+63:i] := 0

FI;

FI; ENDFOR;

VEXP2PD—Approximation to the Exponential 2^x of Packed Double Precision Floating-Point Values with Less Than 2^-23 Relative Er-

8-8 Vol. 2D

INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

Table 8-1. Special Values Behavior

|Source Input|Result|Comments|
|---|---|---|
|NaN|QNaN(src)|If (SRC = SNaN) then #I|
|+∞|+∞||
|+/-0|1.0f|_Exact result_|
|-∞|+0.0f||
|Integral value N|2^ (N)|_Exact result_|



Intel C/C++ Compiler Intrinsic Equivalent

VEXP2PD __m512d _mm512_exp2a23_round_pd (__m512d a, int sae); VEXP2PD __m512d _mm512_mask_exp2a23_round_pd (__m512d a, __mmask8 m, __m512d b, int sae); VEXP2PD __m512d _mm512_maskz_exp2a23_round_pd ( __mmask8 m, __m512d b, int sae);

SIMD Floating-Point Exceptions

Invalid (if SNaN input), Overflow

### Other Exceptions

See Table 2-46, “Type E2 Class Exception Conditions”.

VEXP2PD—Approximation to the Exponential 2^x of Packed Double Precision Floating-Point Values with Less Than 2^-23 Relative

Vol. 2D 8-9

INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

VEXP2PS—Approximation to the Exponential 2^x of Packed Single Precision Floating-Point Values with Less Than 2^-23 Relative Error

|Opcode/<br>Instruction|Op /<br>En|64/32<br>bit Mode<br>Support|CPUID<br>Feature<br>Flag|Description|
|---|---|---|---|---|
|EVEX.512.66.0F38.W0 C8 /r|A|V/V|AVX512ER|Computes approximations to the exponential 2^x (with less|
|VEXP2PS zmm1 {k1}{z},<br>zmm2/m512/m32bcst {sae}||||than 2^-23 of maximum relative error) of the packed single-<br>precision floating-point values from zmm2/m512/m32bcst and<br>stores the floating-point result in zmm1with writemask k1.|



## Instruction Operand Encoding

|Op/En|Tuple Type|Operand 1|Operand 2|Operand 3|Operand 4|
|---|---|---|---|---|---|
|A|Full|ModRM:reg (r, w)|ModRM:r/m (r)|NA|NA|



### Description

Computes the approximate base-2 exponential evaluation of the single-precision floating-point values in the source operand (the second operand) and store the results in the destination operand (the first operand) using the writemask k1. The approximate base-2 exponential is evaluated with less than 2^-23 of relative error.

Denormal input values are treated as zeros and do not signal #DE, irrespective of MXCSR.DAZ. Denormal results are flushed to zeros and do not signal #UE, irrespective of MXCSR.FTZ.

The source operand is a ZMM register, a 512-bit memory location, or a 512-bit vector broadcasted from a 32-bit memory location. The destination operand is a ZMM register, conditionally updated using writemask k1.

EVEX.vvvv is reserved and must be 1111b otherwise instructions will #UD.

A numerically exact implementation of VEXP2xx can be found at <u>https://software.intel.com/en-us/articles/reference-implementations-for-IA-approximation-instructions-vrcp14-vrsqrt14-vrcp28-vrsqrt28-vexp2.</u>

### Operation

### VEXP2PS

(KL, VL) = (16, 512) FOR j := 0 TO KL-1 i := j * 32

IF k1[j] OR *no writemask* THEN IF (EVEX.b = 1) AND (SRC *is memory*) THEN DEST[i+31:i] := EXP2_23_SP(SRC[31:0]) ELSE DEST[i+31:i] := EXP2_23_SP(SRC[i+31:i])

FI;

### ELSE

IF *merging-masking* ; merging-masking THEN *DEST[i+31:i] remains unchanged* ELSE ; zeroing-masking DEST[i+31:i] := 0

FI;

FI; ENDFOR;

VEXP2PS—Approximation to the Exponential 2^x of Packed Single Precision Floating-Point Values with Less Than 2^-23 Relative Error

8-10 Vol. 2D

INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

Table 8-2. Special Values Behavior

|Source Input|Result|Comments|
|---|---|---|
|NaN|QNaN(src)|If (SRC = SNaN) then #I|
|+∞|+∞||
|+/-0|1.0f|_Exact result_|
|-∞|+0.0f||
|Integral value N|2^ (N)|_Exact result_|



Intel C/C++ Compiler Intrinsic Equivalent

VEXP2PS __m512 _mm512_exp2a23_round_ps (__m512 a, int sae); VEXP2PS __m512 _mm512_mask_exp2a23_round_ps (__m512 a, __mmask16 m, __m512 b, int sae); VEXP2PS __m512 _mm512_maskz_exp2a23_round_ps (__mmask16 m, __m512 b, int sae);

SIMD Floating-Point Exceptions

Invalid (if SNaN input), Overflow

### Other Exceptions

See Table 2-46, “Type E2 Class Exception Conditions”.

VEXP2PS—Approximation to the Exponential 2^x of Packed Single Precision Floating-Point Values with Less Than 2^-23 Relative Er-

Vol. 2D 8-11

INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

VGATHERPF0DPS/VGATHERPF0QPS/VGATHERPF0DPD/VGATHERPF0QPD—Sparse Prefetch Packed SP/DP Data Values with Signed Dword, Signed Qword Indices Using T0 Hint

|Opcode/<br>Instruction|Op/<br>En|64/32<br>bit Mode<br>Support|CPUID<br>Feature<br>Flag|Description|
|---|---|---|---|---|
|EVEX.512.66.0F38.W0 C6 /1 /vsib<br>VGATHERPF0DPS vm32z {k1}|A|V/V|AVX512PF|Using signed dword indices, prefetch sparse byte<br>memory locations containing single-precision data<br>usingopmask k1 and T0 hint.|
|EVEX.512.66.0F38.W0 C7 /1 /vsib<br>VGATHERPF0QPS vm64z {k1}|A|V/V|AVX512PF|Using signed qword indices, prefetch sparse byte<br>memory locations containing single-precision data<br>usingopmask k1 and T0 hint.|
|EVEX.512.66.0F38.W1 C6 /1 /vsib<br>VGATHERPF0DPD vm32y {k1}|A|V/V|AVX512PF|Using signed dword indices, prefetch sparse byte<br>memory locations containing double precision data<br>usingopmask k1 and T0 hint.|
|EVEX.512.66.0F38.W1 C7 /1 /vsib<br>VGATHERPF0QPD vm64z {k1}|A|V/V|AVX512PF|Using signed qword indices, prefetch sparse byte<br>memory locations containing double precision data<br>usingopmask k1 and T0 hint.|



## Instruction Operand Encoding

|Op/En|Tuple Type|Operand 1|Operand 2|Operand 3|Operand 4|
|---|---|---|---|---|---|
|A|Tuple1 Scalar|BaseReg (R): VSIB:base,<br>VectorReg(R): VSIB:index|NA|NA|NA|



### Description

The instruction conditionally prefetches up to sixteen 32-bit or eight 64-bit integer byte data elements. The elements are specified via the VSIB (i.e., the index register is an zmm, holding packed indices). Elements will only be prefetched if their corresponding mask bit is one.

Lines prefetched are loaded into to a location in the cache hierarchy specified by a locality hint (T0):

- T0 (temporal data)—prefetch data into the first level cache.

[PS data] For dword indices, the instruction will prefetch sixteen memory locations. For qword indices, the instruction will prefetch eight values.

[PD data] For dword and qword indices, the instruction will prefetch eight memory locations.

Note that:

- (1) The prefetches may happen in any order (or not at all). The instruction is a hint.

- (2) The mask is left unchanged.

- (3) Not valid with 16-bit effective addresses. Will deliver a #UD fault.

- (4) No FP nor memory faults may be produced by this instruction.

- (5) Prefetches do not handle cache line splits

- (6) A #UD is signaled if the memory operand is encoded without the SIB byte.

### Operation

BASE_ADDR stands for the memory operand base address (a GPR); may not exist VINDEX stands for the memory operand vector of indices (a vector register) SCALE stands for the memory operand scalar (1, 2, 4 or 8) DISP is the optional 1, 2 or 4 byte displacement

PREFETCH(mem, Level, State) Prefetches a byte memory location pointed by ‘mem’ into the cache level specified by ‘Level’; a request for exclusive/ownership is done if ‘State’ is 1. Note that the memory location ignore cache line splits. This operation is considered a hint for the processor and may be skipped depending on implementation.

8-12 Vol. 2D VGATHERPF0DPS/VGATHERPF0QPS/VGATHERPF0DPD/VGATHERPF0QPD—Sparse Prefetch Packed SP/DP Data Values with Signed

INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

VGATHERPF0DPS (EVEX encoded version) (KL, VL) = (16, 512) FOR j := 0 TO KL-1 i := j * 32 IF k1[j] Prefetch( [BASE_ADDR + SignExtend(VINDEX[i+31:i]) * SCALE + DISP], Level=0, RFO = 0) FI; ENDFOR

VGATHERPF0DPD (EVEX encoded version) (KL, VL) = (8, 512) FOR j := 0 TO KL-1 i := j * 64 k := j * 32 IF k1[j] Prefetch( [BASE_ADDR + SignExtend(VINDEX[k+31:k]) * SCALE + DISP], Level=0, RFO = 0) FI; ENDFOR

VGATHERPF0QPS (EVEX encoded version) (KL, VL) = (8, 256) FOR j := 0 TO KL-1 i := j * 64 IF k1[j] Prefetch( [BASE_ADDR + SignExtend(VINDEX[i+63:i]) * SCALE + DISP], Level=0, RFO = 0) FI; ENDFOR

VGATHERPF0QPD (EVEX encoded version) (KL, VL) = (8, 512) FOR j := 0 TO KL-1 i := j * 64 k := j * 64 IF k1[j] Prefetch( [BASE_ADDR + SignExtend(VINDEX[k+63:k]) * SCALE + DISP], Level=0, RFO = 0) FI; ENDFOR

Intel C/C++ Compiler Intrinsic Equivalent

VGATHERPF0DPD void _mm512_mask_prefetch_i32gather_pd(__m256i vdx, __mmask8 m, void * base, int scale, int hint); VGATHERPF0DPS void _mm512_mask_prefetch_i32gather_ps(__m512i vdx, __mmask16 m, void * base, int scale, int hint); VGATHERPF0QPD void _mm512_mask_prefetch_i64gather_pd(__m512i vdx, __mmask8 m, void * base, int scale, int hint); VGATHERPF0QPS void _mm512_mask_prefetch_i64gather_ps(__m512i vdx, __mmask8 m, void * base, int scale, int hint);

SIMD Floating-Point Exceptions

None

Other Exceptions

See Table 2-62, “Type E12NP Class Exception Conditions”.

VGATHERPF0DPS/VGATHERPF0QPS/VGATHERPF0DPD/VGATHERPF0QPD—Sparse Prefetch Packed SP/DP Data Values with Signed

Vol. 2D 8-13

INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

VGATHERPF1DPS/VGATHERPF1QPS/VGATHERPF1DPD/VGATHERPF1QPD—Sparse Prefetch Packed SP/DP Data Values with Signed Dword, Signed Qword Indices Using T1 Hint

|Opcode/<br>Instruction|Op/<br>En|64/32<br>bit Mode<br>Support|CPUID<br>Feature<br>Flag|Description|
|---|---|---|---|---|
|EVEX.512.66.0F38.W0 C6 /2 /vsib<br>VGATHERPF1DPS vm32z {k1}|A|V/V|AVX512PF|Using signed dword indices, prefetch sparse byte<br>memory locations containing single-precision data using<br>opmask k1 and T1 hint.|
|EVEX.512.66.0F38.W0 C7 /2 /vsib<br>VGATHERPF1QPS vm64z {k1}|A|V/V|AVX512PF|Using signed qword indices, prefetch sparse byte<br>memory locations containing single-precision data using<br>opmask k1 and T1 hint.|
|EVEX.512.66.0F38.W1 C6 /2 /vsib<br>VGATHERPF1DPD vm32y {k1}|A|V/V|AVX512PF|Using signed dword indices, prefetch sparse byte<br>memory locations containing double precision data using<br>opmask k1 and T1 hint.|
|EVEX.512.66.0F38.W1 C7 /2 /vsib<br>VGATHERPF1QPD vm64z {k1}|A|V/V|AVX512PF|Using signed qword indices, prefetch sparse byte<br>memory locations containing double precision data using<br>opmask k1 and T1 hint.|



## Instruction Operand Encoding

|Op/En|Tuple Type|Operand 1|Operand 2|Operand 3|Operand 4|
|---|---|---|---|---|---|
|A|Tuple1 Scalar|BaseReg (R): VSIB:base,<br>VectorReg(R): VSIB:index|NA|NA|NA|



### Description

The instruction conditionally prefetches up to sixteen 32-bit or eight 64-bit integer byte data elements. The elements are specified via the VSIB (i.e., the index register is an zmm, holding packed indices). Elements will only be prefetched if their corresponding mask bit is one.

Lines prefetched are loaded into to a location in the cache hierarchy specified by a locality hint (T1):

- T1 (temporal data)—prefetch data into the second level cache.

[PS data] For dword indices, the instruction will prefetch sixteen memory locations. For qword indices, the instruction will prefetch eight values.

[PD data] For dword and qword indices, the instruction will prefetch eight memory locations.

Note that:

- (1) The prefetches may happen in any order (or not at all). The instruction is a hint.

- (2) The mask is left unchanged.

- (3) Not valid with 16-bit effective addresses. Will deliver a #UD fault.

- (4) No FP nor memory faults may be produced by this instruction.

- (5) Prefetches do not handle cache line splits

- (6) A #UD is signaled if the memory operand is encoded without the SIB byte.

### Operation

BASE_ADDR stands for the memory operand base address (a GPR); may not exist VINDEX stands for the memory operand vector of indices (a vector register) SCALE stands for the memory operand scalar (1, 2, 4 or 8) DISP is the optional 1, 2 or 4 byte displacement

PREFETCH(mem, Level, State) Prefetches a byte memory location pointed by ‘mem’ into the cache level specified by ‘Level’; a request for exclusive/ownership is done if ‘State’ is 1. Note that the memory location ignore cache line splits. This operation is considered a hint for the processor and may be skipped depending on implementation.

8-14 Vol. 2D VGATHERPF1DPS/VGATHERPF1QPS/VGATHERPF1DPD/VGATHERPF1QPD—Sparse Prefetch Packed SP/DP Data Values with Signed

INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

VGATHERPF1DPS (EVEX encoded version) (KL, VL) = (16, 512) FOR j := 0 TO KL-1 i := j * 32 IF k1[j] Prefetch( [BASE_ADDR + SignExtend(VINDEX[i+31:i]) * SCALE + DISP], Level=1, RFO = 0) FI; ENDFOR

VGATHERPF1DPD (EVEX encoded version) (KL, VL) = (8, 512) FOR j := 0 TO KL-1 i := j * 64 k := j * 32 IF k1[j] Prefetch( [BASE_ADDR + SignExtend(VINDEX[k+31:k]) * SCALE + DISP], Level=1, RFO = 0) FI; ENDFOR

VGATHERPF1QPS (EVEX encoded version) (KL, VL) = (8, 256) FOR j := 0 TO KL-1 i := j * 64 IF k1[j] Prefetch( [BASE_ADDR + SignExtend(VINDEX[i+63:i]) * SCALE + DISP], Level=1, RFO = 0) FI; ENDFOR

VGATHERPF1QPD (EVEX encoded version) (KL, VL) = (8, 512) FOR j := 0 TO KL-1 i := j * 64 k := j * 64 IF k1[j] Prefetch( [BASE_ADDR + SignExtend(VINDEX[k+63:k]) * SCALE + DISP], Level=1, RFO = 0) FI; ENDFOR

Intel C/C++ Compiler Intrinsic Equivalent

VGATHERPF1DPD void _mm512_mask_prefetch_i32gather_pd(__m256i vdx, __mmask8 m, void * base, int scale, int hint); VGATHERPF1DPS void _mm512_mask_prefetch_i32gather_ps(__m512i vdx, __mmask16 m, void * base, int scale, int hint); VGATHERPF1QPD void _mm512_mask_prefetch_i64gather_pd(__m512i vdx, __mmask8 m, void * base, int scale, int hint); VGATHERPF1QPS void _mm512_mask_prefetch_i64gather_ps(__m512i vdx, __mmask8 m, void * base, int scale, int hint);

SIMD Floating-Point Exceptions

None

Other Exceptions

See Table 2-62, “Type E12NP Class Exception Conditions”.

VGATHERPF1DPS/VGATHERPF1QPS/VGATHERPF1DPD/VGATHERPF1QPD—Sparse Prefetch Packed SP/DP Data Values with Signed

Vol. 2D 8-15

INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

VP4DPWSSDS — Dot Product of Signed Words with Dword Accumulation and Saturation <u>(4-iterations)</u>

|Opcode/<br>Instruction|Op/<br>En|64/32<br>bit Mode<br>Support|CPUID Feature<br>Flag|Description|
|---|---|---|---|---|
|EVEX.512.F2.0F38.W0 53 /r|A|V/V|AVX512_4VNNIW|Multiply signed words from source register block|
|VP4DPWSSDS zmm1{k1}{z},<br>zmm2+3, m128||||indicated by zmm2 by signed words from m128<br>and accumulate the resulting dword results with<br>signed saturation in zmm1.|



## Instruction Operand Encoding

|Op/En|Tuple|Operand 1|Operand 2|Operand 3|Operand 4|
|---|---|---|---|---|---|
|A|Tuple1_4X|ModRM:reg (r, w)|EVEX.vvvv (r)|ModRM:r/m (r)|NA|



### Description

This instruction computes 4 sequential register source-block dot-products of two signed word operands with doubleword accumulation and signed saturation. The memory operand is sequentially selected in each of the four steps.

In the above box, the notation of “+3” is used to denote that the instruction accesses 4 source registers based on that operand; sources are consecutive, start in a multiple of 4 boundary, and contain the encoded register operand.

This instruction supports memory fault suppression. The entire memory operand is loaded if any bit of the lowest 16-bits of the mask is set to 1 or if a “no masking” encoding is used.

The tuple type Tuple1_4X implies that four 32-bit elements (16 bytes) are referenced by the memory operation portion of this instruction.

### Operation

src_reg_id is the 5 bit index of the vector register specified in the instruction as the src1 register.

VP4DPWSSDS dest, src1, src2 (KL,VL) = (16,512) N := 4

ORIGDEST := DEST

src_base := src_reg_id & ~ (N-1) // for src1 operand

FOR i := 0 to KL-1: IF k1[i] or *no writemask*: FOR m := 0 to N-1: t := SRC2.dword[m] p1dword := reg[src_base+m].word[2*i] * t.word[0] p2dword := reg[src_base+m].word[2*i+1] * t.word[1] DEST.dword[i] := SIGNED_DWORD_SATURATE(DEST.dword[i] + p1dword + p2dword) ELSE IF *zeroing*: DEST.dword[i] := 0

ELSE

DEST.dword[i] := ORIGDEST.dword[i] DEST[MAX_VL-1:VL] := 0

VP4DPWSSDS — Dot Product of Signed Words with Dword Accumulation and Saturation (4-iterations)

8-16 Vol. 2D

INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

Intel C/C++ Compiler Intrinsic Equivalent

VP4DPWSSDS __m512i _mm512_4dpwssds_epi32(__m512i, __m512ix4, __m128i *); VP4DPWSSDS __m512i _mm512_mask_4dpwssds_epi32(__m512i, __mmask16, __m512ix4, __m128i *); VP4DPWSSDS __m512i _mm512_maskz_4dpwssds_epi32(__mmask16, __m512i, __m512ix4, __m128i *);

SIMD Floating-Point Exceptions

None.

Other Exceptions

See Type E4; additionally #UD If the EVEX broadcast bit is set to 1. #UD If the MODRM.mod = 0b11.

VP4DPWSSDS — Dot Product of Signed Words with Dword Accumulation and Saturation (4-iterations)

Vol. 2D 8-17

INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

# VP4DPWSSD — Dot Product of Signed Words with Dword Accumulation (4-iterations)

|Opcode/<br>Instruction|Op/<br>En|64/32<br>bit Mode<br>Support|CPUID Feature<br>Flag|Description|
|---|---|---|---|---|
|EVEX.512.F2.0F38.W0 52 /r|A|V/V|AVX512_4VNNIW|Multiply signed words from source register block|
|VP4DPWSSD zmm1{k1}{z}, zmm2+3,||||indicated by zmm2 by signed words from m128|
|m128||||and accumulate resulting signed dwords in zmm1.|



## Instruction Operand Encoding

|Op/En|Tuple|Operand 1|Operand 2|Operand 3|Operand 4|
|---|---|---|---|---|---|
|A|Tuple1_4X|ModRM:reg (r, w)|EVEX.vvvv (r)|ModRM:r/m (r)|NA|



### Description

This instruction computes 4 sequential register source-block dot-products of two signed word operands with doubleword accumulation; see Figure 8-1 below. The memory operand is sequentially selected in each of the four steps.

In the above box, the notation of “+3”' is used to denote that the instruction accesses 4 source registers based on that operand; sources are consecutive, start in a multiple of 4 boundary, and contain the encoded register operand. This instruction supports memory fault suppression. The entire memory operand is loaded if any bit of the lowest 16-bits of the mask is set to 1 or if a “no masking” encoding is used.

The tuple type Tuple1_4X implies that four 32-bit elements (16 bytes) are referenced by the memory operation portion of this instruction.



<!-- Start of picture text -->
16b 16b 16b 16b<br>a3 a2 a1 a0<br>b1 b0 b1 b0<br>32b 32b<br>c1 c0<br>c1=c1+a2*b0+a3*b1 c0=c0+a0*b0+a1*b1<br>32b 32b<br><!-- End of picture text -->

Figure 8-1.  Register Source-Block Dot Product of Two Signed Word Operands with Doubleword Accumulation<sup>1</sup>

- NOTES:

1. For illustration purposes, one source-block dot product instance is shown out of the four.

VP4DPWSSD — Dot Product of Signed Words with Dword Accumulation (4-iterations)

8-18 Vol. 2D

INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

### Operation

src_reg_id is the 5 bit index of the vector register specified in the instruction as the src1 register.

VP4DPWSSD dest, src1, src2 (KL,VL) = (16,512) N := 4

ORIGDEST := DEST src_base := src_reg_id & ~ (N-1) // for src1 operand

FOR i := 0 to KL-1: IF k1[i] or *no writemask*: FOR m := 0 to N-1: t := SRC2.dword[m] p1dword := reg[src_base+m].word[2*i] * t.word[0] p2dword := reg[src_base+m].word[2*i+1] * t.word[1] DEST.dword[i] := DEST.dword[i] + p1dword + p2dword ELSE IF *zeroing*: DEST.dword[i] := 0 ELSE DEST.dword[i] := ORIGDEST.dword[i] DEST[MAX_VL-1:VL] := 0

Intel C/C++ Compiler Intrinsic Equivalent

VP4DPWSSD __m512i _mm512_4dpwssd_epi32(__m512i, __m512ix4, __m128i *); VP4DPWSSD __m512i _mm512_mask_4dpwssd_epi32(__m512i, __mmask16, __m512ix4, __m128i *); VP4DPWSSD __m512i _mm512_maskz_4dpwssd_epi32(__mmask16, __m512i, __m512ix4, __m128i *);

SIMD Floating-Point Exceptions None.

Other Exceptions

See Type E4; additionally #UD If the EVEX broadcast bit is set to 1. #UD If the MODRM.mod = 0b11.

VP4DPWSSD — Dot Product of Signed Words with Dword Accumulation (4-iterations)

Vol. 2D 8-19

INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

VRCP28PD—Approximation to the Reciprocal of Packed Double Precision Floating-Point Values with Less Than 2^-28 Relative Error

|Opcode/<br>Instruction|Op /<br>En|64/32<br>bit Mode<br>Support|CPUID<br>Feature<br>Flag|Description|
|---|---|---|---|---|
|EVEX.512.66.0F38.W1 CA /r|A|V/V|AVX512ER|Computes the approximate reciprocals ( < 2^-28 relative error)|
|VRCP28PD zmm1 {k1}{z},<br>zmm2/m512/m64bcst {sae}||||of the packed double precision floating-point values in<br>zmm2/m512/m64bcst and stores the results in zmm1. Under<br>writemask.|



|||Inst|ruction Operand Encodi|ng||
|---|---|---|---|---|---|
|Op/En|Tuple Type|Operand 1|Operand 2|Operand 3|Operand 4|
|A|Full|ModRM:reg (w)|ModRM:r/m (r)|NA|NA|



### Description

Computes the reciprocal approximation of the float64 values in the source operand (the second operand) and store the results to the destination operand (the first operand). The approximate reciprocal is evaluated with less than 2^-28 of maximum relative error.

Denormal input values are treated as zeros and do not signal #DE, irrespective of MXCSR.DAZ. Denormal results are flushed to zeros and do not signal #UE, irrespective of MXCSR.FTZ.

If any source element is NaN, the quietized NaN source value is returned for that element. If any source element is ±∞, ±0.0 is returned for that element. Also, if any source element is ±0.0, ±∞ is returned for that element.

The source operand is a ZMM register, a 512-bit memory location or a 512-bit vector broadcasted from a 64-bit memory location. The destination operand is a ZMM register, conditionally updated using writemask k1.

EVEX.vvvv is reserved and must be 1111b otherwise instructions will #UD.

A numerically exact implementation of VRCP28xx can be found at <u>https://software.intel.com/en-us/articles/reference-implementations-for-IA-approximation-instructions-vrcp14-vrsqrt14-vrcp28-vrsqrt28-vexp2.</u>

### Operation

### VRCP28PD (EVEX encoded versions)

(KL, VL) = (8, 512)

FOR j := 0 TO KL-1

i := j * 64 IF k1[j] OR *no writemask* THEN IF (EVEX.b = 1) AND (SRC *is memory*) THEN DEST[i+63:i] := RCP_28_DP(1.0/SRC[63:0]); ELSE DEST[i+63:i] := RCP_28_DP(1.0/SRC[i+63:i]);

FI;

ELSE

IF *merging-masking* ; merging-masking THEN *DEST[i+63:i] remains unchanged* ELSE ; zeroing-masking DEST[i+63:i] := 0 FI; FI; ENDFOR;

VRCP28PD—Approximation to the Reciprocal of Packed Double Precision Floating-Point Values with Less Than 2^-28 Relative Error

8-20 Vol. 2D

INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

Table 8-3. VRCP28PD Special Cases

|Input value|Result value|Comments|
|---|---|---|
|NAN|QNAN(input)|If (SRC = SNaN) then #I|
|0≤X < 2<sup>-1022</sup>|INF|Positive input denormal or zero; #Z|
|-2<sup>-1022</sup>< X≤-0|-INF|Negative input denormal or zero; #Z|
|X > 2<sup>1022</sup>|+0.0f||
|X < -2<sup>1022</sup>|-0.0f||
|X = +∞|+0.0f||
|X = -∞|-0.0f||
|X = 2<sup>-n</sup>|2<sup>n</sup>|Exact result (unless input/output is a denormal)|
|X = -2<sup>-n</sup>|-2<sup>n</sup>|Exact result (unless input/output is a denormal)|



### Intel C/C++ Compiler Intrinsic Equivalent

VRCP28PD __m512d _mm512_rcp28_round_pd ( __m512d a, int sae); VRCP28PD __m512d _mm512_mask_rcp28_round_pd(__m512d a, __mmask8 m, __m512d b, int sae); VRCP28PD __m512d _mm512_maskz_rcp28_round_pd( __mmask8 m, __m512d b, int sae);

SIMD Floating-Point Exceptions

Invalid (if SNaN input), Divide-by-zero

### Other Exceptions

See Table 2-46, “Type E2 Class Exception Conditions”.

VRCP28PD—Approximation to the Reciprocal of Packed Double Precision Floating-Point Values with Less Than 2^-28 Relative Error

Vol. 2D 8-21

INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

VRCP28SD—Approximation to the Reciprocal of Scalar Double Precision Floating-Point Value with Less Than 2^-28 Relative Error

|Opcode/<br>Instruction|Op /<br>En|64/32<br>bit Mode<br>Support|CPUID<br>Feature<br>Flag|Description|
|---|---|---|---|---|
|EVEX.LLIG.66.0F38.W1 CB /r<br>VRCP28SD xmm1 {k1}{z}, xmm2,<br>xmm3/m64 {sae}|A|V/V|AVX512ER|Computes the approximate reciprocal ( < 2^-28 relative<br>error) of the scalar double precision floating-point value in<br>xmm3/m64 and stores the results in xmm1. Under<br>writemask. Also, upper double precision floating-point<br>value (bits[127:64]) from xmm2 is copied to<br>xmm1[127:64].|



Instruction Operand Encoding

|Op/En|Tuple Type|Operand 1|Operand 2|Operand 3|Operand 4|
|---|---|---|---|---|---|
|A|Tuple1 Scalar|ModRM:reg (w)|EVEX.vvvv (r)|ModRM:r/m (r)|NA|



### Description

Computes the reciprocal approximation of the low float64 value in the second source operand (the third operand) and store the result to the destination operand (the first operand). The approximate reciprocal is evaluated with less than 2^-28 of maximum relative error. The result is written into the low float64 element of the destination operand according to the writemask k1. Bits 127:64 of the destination is copied from the corresponding bits of the first source operand (the second operand).

A denormal input value is treated as zero and does not signal #DE, irrespective of MXCSR.DAZ. A denormal result is flushed to zero and does not signal #UE, irrespective of MXCSR.FTZ.

If any source element is NaN, the quietized NaN source value is returned for that element. If any source element is ±∞, ±0.0 is returned for that element. Also, if any source element is ±0.0, ±∞ is returned for that element.

The first source operand is an XMM register. The second source operand is an XMM register or a 64-bit memory location. The destination operand is a XMM register, conditionally updated using writemask k1.

A numerically exact implementation of VRCP28xx can be found at <u>https://software.intel.com/en-us/articles/reference-implementations-for-IA-approximation-instructions-vrcp14-vrsqrt14-vrcp28-vrsqrt28-vexp2.</u>

### Operation

### VRCP28SD ((EVEX encoded versions)

IF k1[0] OR *no writemask* THEN

DEST[63: 0] := RCP_28_DP(1.0/SRC2[63: 0]);

### ELSE

IF *merging-masking* ; merging-masking THEN *DEST[63: 0] remains unchanged* ELSE ; zeroing-masking DEST[63: 0] := 0

FI;

FI; ENDFOR; DEST[127:64] := SRC1[127: 64] DEST[MAXVL-1:128] := 0

VRCP28SD—Approximation to the Reciprocal of Scalar Double Precision Floating-Point Value with Less Than 2^-28 Relative Error

8-22 Vol. 2D

INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

Table 8-4. VRCP28SD Special Cases

|Input value|Result value|Comments|
|---|---|---|
|NAN|QNAN(input)|If (SRC = SNaN) then #I|
|0≤X < 2<sup>-1022</sup>|INF|Positive input denormal or zero; #Z|
|-2<sup>-1022</sup>< X≤-0|-INF|Negative input denormal or zero; #Z|
|X > 2<sup>1022</sup>|+0.0f||
|X < -2<sup>1022</sup>|-0.0f||
|X = +∞|+0.0f||
|X = -∞|-0.0f||
|X = 2<sup>-n</sup>|2<sup>n</sup>|Exact result (unless input/output is a denormal)|
|X = -2<sup>-n</sup>|-2<sup>n</sup>|Exact result (unless input/output is a denormal)|



### Intel C/C++ Compiler Intrinsic Equivalent

VRCP28SD __m128d _mm_rcp28_round_sd ( __m128d a, __m128d b, int sae); VRCP28SD __m128d _mm_mask_rcp28_round_sd(__m128d s, __mmask8 m, __m128d a, __m128d b, int sae); VRCP28SD __m128d _mm_maskz_rcp28_round_sd(__mmask8 m, __m128d a, __m128d b, int sae);

SIMD Floating-Point Exceptions

Invalid (if SNaN input), Divide-by-zero

### Other Exceptions

See Table 2-47, “Type E3 Class Exception Conditions”.

VRCP28SD—Approximation to the Reciprocal of Scalar Double Precision Floating-Point Value with Less Than 2^-28 Relative Error

Vol. 2D 8-23

INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

VRCP28PS—Approximation to the Reciprocal of Packed Single Precision Floating-Point Values with Less Than 2^-28 Relative Error

|Opcode/<br>Instruction|Op /<br>En|64/32<br>bit Mode<br>Support|CPUID<br>Feature<br>Flag|Description|
|---|---|---|---|---|
|EVEX.512.66.0F38.W0 CA /r|A|V/V|AVX512ER|Computes the approximate reciprocals ( < 2^-28 relative|
|VRCP28PS zmm1 {k1}{z},<br>zmm2/m512/m32bcst {sae}||||error) of the packed single-precision floating-point values in<br>zmm2/m512/m32bcst and stores the results in zmm1. Under<br>writemask.|



|||Inst|ruction Operand Encodi|ng||
|---|---|---|---|---|---|
|Op/En|Tuple Type|Operand 1|Operand 2|Operand 3|Operand 4|
|A|Full|ModRM:reg (w)|ModRM:r/m (r)|NA|NA|



### Description

Computes the reciprocal approximation of the float32 values in the source operand (the second operand) and store the results to the destination operand (the first operand) using the writemask k1. The approximate reciprocal is evaluated with less than 2^-28 of maximum relative error prior to final rounding. The final results are rounded to < 2^-23 relative error before written to the destination.

Denormal input values are treated as zeros and do not signal #DE, irrespective of MXCSR.DAZ. Denormal results are flushed to zeros and do not signal #UE, irrespective of MXCSR.FTZ.

If any source element is NaN, the quietized NaN source value is returned for that element. If any source element is ±∞, ±0.0 is returned for that element. Also, if any source element is ±0.0, ±∞ is returned for that element.

The source operand is a ZMM register, a 512-bit memory location, or a 512-bit vector broadcasted from a 32-bit memory location. The destination operand is a ZMM register, conditionally updated using writemask k1.

EVEX.vvvv is reserved and must be 1111b otherwise instructions will #UD.

A numerically exact implementation of VRCP28xx can be found at <u>https://software.intel.com/en-us/articles/reference-implementations-for-IA-approximation-instructions-vrcp14-vrsqrt14-vrcp28-vrsqrt28-vexp2.</u>

### Operation

VRCP28PS (EVEX encoded versions) (KL, VL) = (16, 512)

FOR j := 0 TO KL-1 i := j * 32 IF k1[j] OR *no writemask* THEN IF (EVEX.b = 1) AND (SRC *is memory*) THEN DEST[i+31:i] := RCP_28_SP(1.0/SRC[31:0]); ELSE DEST[i+31:i] := RCP_28_SP(1.0/SRC[i+31:i]); FI;

ELSE

IF *merging-masking* ; merging-masking THEN *DEST[i+31:i] remains unchanged* ELSE ; zeroing-masking DEST[i+31:i] := 0 FI; FI; ENDFOR;

VRCP28PS—Approximation to the Reciprocal of Packed Single Precision Floating-Point Values with Less Than 2^-28 Relative Error

8-24 Vol. 2D

INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

Table 8-5. VRCP28PS Special Cases

|Input value|Result value|Comments|
|---|---|---|
|NAN|QNAN(input)|If (SRC = SNaN) then #I|
|0≤X < 2<sup>-126</sup>|INF|Positive input denormal or zero; #Z|
|-2<sup>-126</sup>< X≤-0|-INF|Negative input denormal or zero; #Z|
|X > 2<sup>126</sup>|+0.0f||
|X < -2<sup>126</sup>|-0.0f||
|X = +∞|+0.0f||
|X = -∞|-0.0f||
|X = 2<sup>-n</sup>|2<sup>n</sup>|Exact result (unless input/output is a denormal)|
|X = -2<sup>-n</sup>|-2<sup>n</sup>|Exact result (unless input/output is a denormal)|



### Intel C/C++ Compiler Intrinsic Equivalent

VRCP28PS _mm512_rcp28_round_ps ( __m512 a, int sae); VRCP28PS __m512 _mm512_mask_rcp28_round_ps(__m512 s, __mmask16 m, __m512 a, int sae); VRCP28PS __m512 _mm512_maskz_rcp28_round_ps( __mmask16 m, __m512 a, int sae);

SIMD Floating-Point Exceptions

Invalid (if SNaN input), Divide-by-zero

### Other Exceptions

See Table 2-46, “Type E2 Class Exception Conditions”.

VRCP28PS—Approximation to the Reciprocal of Packed Single Precision Floating-Point Values with Less Than 2^-28 Relative Error

Vol. 2D 8-25

INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

VRCP28SS—Approximation to the Reciprocal of Scalar Single Precision Floating-Point Value with Less Than 2^-28 Relative Error

|Opcode/<br>Instruction|Op /<br>En|64/32<br>bit Mode<br>Support|CPUID<br>Feature<br>Flag|Description|
|---|---|---|---|---|
|EVEX.LLIG.66.0F38.W0 CB /r<br>VRCP28SS xmm1 {k1}{z},<br>xmm2, xmm3/m32 {sae}|A|V/V|AVX512ER|Computes the approximate reciprocal ( < 2^-28 relative<br>error) of the scalar single-precision floating-point value in<br>xmm3/m32 and stores the results in xmm1. Under<br>writemask. Also, upper 3 single-precision floating-point<br>values (bits[127:32]) from xmm2 is copied to<br>xmm1[127:32].|



Instruction Operand Encoding

|Op/En|Tuple Type|Operand 1|Operand 2|Operand 3|Operand 4|
|---|---|---|---|---|---|
|A|Tuple1 Scalar|ModRM:reg (w)|EVEX.vvvv (r)|ModRM:r/m (r)|NA|



### Description

Computes the reciprocal approximation of the low float32 value in the second source operand (the third operand) and store the result to the destination operand (the first operand). The approximate reciprocal is evaluated with less than 2^-28 of maximum relative error prior to final rounding. The final result is rounded to < 2^-23 relative error before written into the low float32 element of the destination according to writemask k1. Bits 127:32 of the destination is copied from the corresponding bits of the first source operand (the second operand).

A denormal input value is treated as zero and does not signal #DE, irrespective of MXCSR.DAZ. A denormal result is flushed to zero and does not signal #UE, irrespective of MXCSR.FTZ.

If any source element is NaN, the quietized NaN source value is returned for that element. If any source element is ±∞, ±0.0 is returned for that element. Also, if any source element is ±0.0, ±∞ is returned for that element.

The first source operand is an XMM register. The second source operand is an XMM register or a 32-bit memory location. The destination operand is a XMM register, conditionally updated using writemask k1.

A numerically exact implementation of VRCP28xx can be found at <u>https://software.intel.com/en-us/articles/reference-implementations-for-IA-approximation-instructions-vrcp14-vrsqrt14-vrcp28-vrsqrt28-vexp2.</u>

### Operation

VRCP28SS ((EVEX encoded versions)

IF k1[0] OR *no writemask* THEN

DEST[31: 0] := RCP_28_SP(1.0/SRC2[31: 0]);

### ELSE

IF *merging-masking* ; merging-masking THEN *DEST[31: 0] remains unchanged* ELSE ; zeroing-masking DEST[31: 0] := 0 FI;

FI; ENDFOR; DEST[127:32] := SRC1[127: 32] DEST[MAXVL-1:128] := 0

VRCP28SS—Approximation to the Reciprocal of Scalar Single Precision Floating-Point Value with Less Than 2^-28 Relative Error

8-26 Vol. 2D

INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

Table 8-6. VRCP28SS Special Cases

|Input value|Result value|Comments|
|---|---|---|
|NAN|QNAN(input)|If (SRC = SNaN) then #I|
|0≤X < 2<sup>-126</sup>|INF|Positive input denormal or zero; #Z|
|-2<sup>-126</sup>< X≤-0|-INF|Negative input denormal or zero; #Z|
|X > 2<sup>126</sup>|+0.0f||
|X < -2<sup>126</sup>|-0.0f||
|X = +∞|+0.0f||
|X = -∞|-0.0f||
|X = 2<sup>-n</sup>|2<sup>n</sup>|Exact result (unless input/output is a denormal)|
|X = -2<sup>-n</sup>|-2<sup>n</sup>|Exact result (unless input/output is a denormal)|



Intel C/C++ Compiler Intrinsic Equivalent

VRCP28SS __m128 _mm_rcp28_round_ss ( __m128 a, __m128 b, int sae); VRCP28SS __m128 _mm_mask_rcp28_round_ss(__m128 s, __mmask8 m, __m128 a, __m128 b, int sae); VRCP28SS __m128 _mm_maskz_rcp28_round_ss(__mmask8 m, __m128 a, __m128 b, int sae);

SIMD Floating-Point Exceptions

Invalid (if SNaN input), Divide-by-zero

### Other Exceptions

See Table 2-47, “Type E3 Class Exception Conditions”.

VRCP28SS—Approximation to the Reciprocal of Scalar Single Precision Floating-Point Value with Less Than 2^-28 Relative Error

Vol. 2D 8-27

INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

VRSQRT28PD—Approximation to the Reciprocal Square Root of Packed Double Precision Floating-Point Values with Less Than 2^-28 Relative Error

|Opcode/<br>Instruction|Op /<br>En|64/32<br>bit Mode<br>Support|CPUID<br>Feature<br>Flag|Description|
|---|---|---|---|---|
|EVEX.512.66.0F38.W1 CC /r|A|V/V|AVX512ER|Computes approximations to the Reciprocal square root (<2^-|
|VRSQRT28PD zmm1 {k1}{z},<br>zmm2/m512/m64bcst {sae}||||28 relative error) of the packed double precision floating-point<br>values from zmm2/m512/m64bcst and stores result in<br>zmm1with writemask k1.|



## Instruction Operand Encoding

|Op/En|Tuple Type|Operand 1|Operand 2|Operand 3|Operand 4|
|---|---|---|---|---|---|
|A|Full|ModRM:reg (w)|ModRM:r/m (r)|NA|NA|



### Description

Computes the reciprocal square root of the float64 values in the source operand (the second operand) and store the results to the destination operand (the first operand). The approximate reciprocal is evaluated with less than 2^-28 of maximum relative error.

If any source element is NaN, the quietized NaN source value is returned for that element. Negative (non-zero) source numbers, as well as - ∞, return the canonical NaN and set the Invalid Flag (#I).

A value of -0 must return - ∞ and set the DivByZero flags (#Z). Negative numbers should return NaN and set the Invalid flag (#I). Note however that the instruction flush input denormals to zero of the same sign, so negative denormals return - ∞ and set the DivByZero flag.

The source operand is a ZMM register, a 512-bit memory location or a 512-bit vector broadcasted from a 64-bit memory location. The destination operand is a ZMM register, conditionally updated using writemask k1.

EVEX.vvvv is reserved and must be 1111b otherwise instructions will #UD.

A numerically exact implementation of VRSQRT28xx can be found at <u>https://software.intel.com/en-us/articles/reference-implementations-for-IA-approximation-instructions-vrcp14-vrsqrt14-vrcp28-vrsqrt28-vexp2.</u>

### Operation

VRSQRT28PD (EVEX encoded versions) (KL, VL) = (8, 512) FOR j := 0 TO KL-1 i := j * 64 IF k1[j] OR *no writemask* THEN IF (EVEX.b = 1) AND (SRC *is memory*) THEN DEST[i+63:i] := (1.0/ SQRT(SRC[63:0])); ELSE DEST[i+63:i] := (1.0/ SQRT(SRC[i+63:i]));

FI;

ELSE

IF *merging-masking* ; merging-masking THEN *DEST[i+63:i] remains unchanged* ELSE ; zeroing-masking DEST[i+63:i] := 0 FI; FI; ENDFOR;

8-28 Vol. 2D VRSQRT28PD—Approximation to the Reciprocal Square Root of Packed Double Precision Floating-Point Values with Less Than 2^-28

INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

Table 8-7. VRSQRT28PD Special Cases

|Input value|Result value|Comments|
|---|---|---|
|NAN|QNAN(input)|If (SRC = SNaN) then #I|
|X = 2<sup>-2n</sup>|2<sup>n</sup>||
|X < 0|QNaN_Indefinite|Including -INF|
|X = -0 or negative denormal|-INF|#Z|
|X = +0 or positive denormal|+INF|#Z|
|X = +INF|+0||



Intel C/C++ Compiler Intrinsic Equivalent

VRSQRT28PD __m512d _mm512_rsqrt28_round_pd(__m512d a, int sae); VRSQRT28PD __m512d _mm512_mask_rsqrt28_round_pd(__m512d s, __mmask8 m,__m512d a, int sae); VRSQRT28PD __m512d _mm512_maskz_rsqrt28_round_pd(__mmask8 m,__m512d a, int sae);

SIMD Floating-Point Exceptions

Invalid (if SNaN input), Divide-by-zero

Other Exceptions

See Table 2-46, “Type E2 Class Exception Conditions”.

VRSQRT28PD—Approximation to the Reciprocal Square Root of Packed Double Precision Floating-Point Values with Less Than 2^-28

Vol. 2D 8-29

INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

VRSQRT28SD—Approximation to the Reciprocal Square Root of Scalar Double Precision Floating-Point Value with Less Than 2^-28 Relative Error

|Opcode/<br>Instruction|Op /<br>En|64/32<br>bit Mode<br>Support|CPUID<br>Feature<br>Flag|Description|
|---|---|---|---|---|
|EVEX.LLIG.66.0F38.W1 CD /r<br>VRSQRT28SD xmm1 {k1}{z},<br>xmm2, xmm3/m64 {sae}|A|V/V|AVX512ER|Computes approximate reciprocal square root (<2^-28<br>relative error) of the scalar double precision floating-point<br>value from xmm3/m64 and stores result in xmm1with<br>writemask k1. Also, upper double precision floating-point<br>value (bits[127:64]) from xmm2 is copied to<br>xmm1[127:64].|



Instruction Operand Encoding

|Op/En|Tuple Type|Operand 1|Operand 2|Operand 3|Operand 4|
|---|---|---|---|---|---|
|A|Tuple1 Scalar|ModRM:reg (w)|EVEX.vvvv (r)|ModRM:r/m (r)|NA|



### Description

Computes the reciprocal square root of the low float64 value in the second source operand (the third operand) and store the result to the destination operand (the first operand). The approximate reciprocal square root is evaluated with less than 2^-28 of maximum relative error. The result is written into the low float64 element of xmm1 according to the writemask k1. Bits 127:64 of the destination is copied from the corresponding bits of the first source operand (the second operand).

If any source element is NaN, the quietized NaN source value is returned for that element. Negative (non-zero) source numbers, as well as - ∞, return the canonical NaN and set the Invalid Flag (#I).

A value of -0 must return - ∞ and set the DivByZero flags (#Z). Negative numbers should return NaN and set the Invalid flag (#I). Note however that the instruction flush input denormals to zero of the same sign, so negative denormals return - ∞ and set the DivByZero flag.

The first source operand is an XMM register. The second source operand is an XMM register or a 64-bit memory location. The destination operand is a XMM register.

A numerically exact implementation of VRSQRT28xx can be found at <u>https://software.intel.com/en-us/articles/reference-implementations-for-IA-approximation-instructions-vrcp14-vrsqrt14-vrcp28-vrsqrt28-vexp2.</u>

### Operation

### VRSQRT28SD (EVEX encoded versions)

IF k1[0] OR *no writemask* THEN

DEST[63: 0] := (1.0/ SQRT(SRC[63: 0]));

### ELSE

IF *merging-masking* ; merging-masking THEN *DEST[63: 0] remains unchanged* ELSE ; zeroing-masking DEST[63: 0] := 0 FI; FI; ENDFOR; DEST[127:64] := SRC1[127: 64] DEST[MAXVL-1:128] := 0

VRSQRT28SD—Approximation to the Reciprocal Square Root of Scalar Double Precision Floating-Point Value with Less Than 2^-28

8-30 Vol. 2D

INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

Table 8-8. VRSQRT28SD Special Cases

|Input value|Result value|Comments|
|---|---|---|
|NAN|QNAN(input)|If (SRC = SNaN) then #I|
|X = 2<sup>-2n</sup>|2<sup>n</sup>||
|X < 0|QNaN_Indefinite|Including -INF|
|X = -0 or negative denormal|-INF|#Z|
|X = +0 or positive denormal|+INF|#Z|
|X = +INF|+0||



Intel C/C++ Compiler Intrinsic Equivalent

VRSQRT28SD __m128d _mm_rsqrt28_round_sd(__m128d a, __m128d b, int rounding); VRSQRT28SD __m128d _mm_mask_rsqrt28_round_sd(__m128d s, __mmask8 m,__m128d a, __m128d b, int rounding); VRSQRT28SD __m128d _mm_maskz_rsqrt28_round_sd( __mmask8 m,__m128d a, __m128d b, int rounding);

SIMD Floating-Point Exceptions

Invalid (if SNaN input), Divide-by-zero

Other Exceptions

See Table 2-47, “Type E3 Class Exception Conditions”.

VRSQRT28SD—Approximation to the Reciprocal Square Root of Scalar Double Precision Floating-Point Value with Less Than 2^-28

Vol. 2D 8-31

INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

VRSQRT28PS—Approximation to the Reciprocal Square Root of Packed Single Precision Floating-Point Values with Less Than 2^-28 Relative Error

|Opcode/<br>Instruction|Op /<br>En|64/32<br>bit Mode<br>Support|CPUID<br>Feature<br>Flag|Description|
|---|---|---|---|---|
|EVEX.512.66.0F38.W0 CC /r|A|V/V|AVX512ER|Computes approximations to the Reciprocal square root|
|VRSQRT28PS zmm1 {k1}{z},||||(<2^-28 relative error) of the packed single-precision|
|zmm2/m512/m32bcst {sae}||||floating-point values from zmm2/m512/m32bcst and stores<br>result in zmm1with writemask k1.|



## Instruction Operand Encoding

|Op/En|Tuple Type|Operand 1|Operand 2|Operand 3|Operand 4|
|---|---|---|---|---|---|
|A|Full|ModRM:reg (w)|ModRM:r/m (r)|NA|NA|



### Description

Computes the reciprocal square root of the float32 values in the source operand (the second operand) and store the results to the destination operand (the first operand). The approximate reciprocal is evaluated with less than 2^-28 of maximum relative error prior to final rounding. The final results is rounded to < 2^-23 relative error before written to the destination.

If any source element is NaN, the quietized NaN source value is returned for that element. Negative (non-zero) source numbers, as well as - ∞, return the canonical NaN and set the Invalid Flag (#I).

A value of -0 must return - ∞ and set the DivByZero flags (#Z). Negative numbers should return NaN and set the Invalid flag (#I). Note however that the instruction flush input denormals to zero of the same sign, so negative denormals return - ∞ and set the DivByZero flag.

The source operand is a ZMM register, a 512-bit memory location, or a 512-bit vector broadcasted from a 32-bit memory location. The destination operand is a ZMM register, conditionally updated using writemask k1. EVEX.vvvv is reserved and must be 1111b otherwise instructions will #UD.

A numerically exact implementation of VRSQRT28xx can be found at <u>https://software.intel.com/en-us/articles/reference-implementations-for-IA-approximation-instructions-vrcp14-vrsqrt14-vrcp28-vrsqrt28-vexp2.</u>

### Operation

VRSQRT28PS (EVEX encoded versions) (KL, VL) = (16, 512) FOR j := 0 TO KL-1

i := j * 32 IF k1[j] OR *no writemask* THEN IF (EVEX.b = 1) AND (SRC *is memory*) THEN DEST[i+31:i] := (1.0/ SQRT(SRC[31:0])); ELSE DEST[i+31:i] := (1.0/ SQRT(SRC[i+31:i]));

FI;

ELSE

IF *merging-masking* ; merging-masking THEN *DEST[i+31:i] remains unchanged* ELSE ; zeroing-masking DEST[i+31:i] := 0 FI;

FI; ENDFOR;

8-32 Vol. 2D VRSQRT28PS—Approximation to the Reciprocal Square Root of Packed Single Precision Floating-Point Values with Less Than 2^-28

INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

Table 8-9. VRSQRT28PS Special Cases

|Input value|Result value|Comments|
|---|---|---|
|NAN|QNAN(input)|If (SRC = SNaN) then #I|
|X = 2<sup>-2n</sup>|2<sup>n</sup>||
|X < 0|QNaN_Indefinite|Including -INF|
|X = -0 or negative denormal|-INF|#Z|
|X = +0 or positive denormal|+INF|#Z|
|X = +INF|+0||



Intel C/C++ Compiler Intrinsic Equivalent

VRSQRT28PS __m512 _mm512_rsqrt28_round_ps(__m512 a, int sae); VRSQRT28PS __m512 _mm512_mask_rsqrt28_round_ps(__m512 s, __mmask16 m,__m512 a, int sae); VRSQRT28PS __m512 _mm512_maskz_rsqrt28_round_ps(__mmask16 m,__m512 a, int sae);

SIMD Floating-Point Exceptions

Invalid (if SNaN input), Divide-by-zero

Other Exceptions

See Table 2-46, “Type E2 Class Exception Conditions”.

VRSQRT28PS—Approximation to the Reciprocal Square Root of Packed Single Precision Floating-Point Values with Less Than 2^-28

Vol. 2D 8-33

INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

VRSQRT28SS—Approximation to the Reciprocal Square Root of Scalar Single Precision FloatingPoint Value with Less Than 2^-28 Relative Error

|Opcode/<br>Instruction|Op /<br>En|64/32<br>bit Mode<br>Support|CPUID<br>Feature<br>Flag|Description|
|---|---|---|---|---|
|EVEX.LLIG.66.0F38.W0 CD /r<br>VRSQRT28SS xmm1 {k1}{z},<br>xmm2, xmm3/m32 {sae}|A|V/V|AVX512ER|Computes approximate reciprocal square root (<2^-28<br>relative error) of the scalar single-precision floating-point<br>value from xmm3/m32 and stores result in xmm1with<br>writemask k1. Also, upper 3 single-precision floating-point<br>value (bits[127:32]) from xmm2 is copied to<br>xmm1[127:32].|



## Instruction Operand Encoding

|Op/En|Tuple Type|Operand 1|Operand 2|Operand 3|Operand 4|
|---|---|---|---|---|---|
|A|Tuple1 Scalar|ModRM:reg (w)|EVEX.vvvv (r)|ModRM:r/m (r)|NA|



### Description

Computes the reciprocal square root of the low float32 value in the second source operand (the third operand) and store the result to the destination operand (the first operand). The approximate reciprocal square root is evaluated with less than 2^-28 of maximum relative error prior to final rounding. The final result is rounded to < 2^-23 relative error before written to the low float32 element of the destination according to the writemask k1. Bits 127:32 of the destination is copied from the corresponding bits of the first source operand (the second operand).

If any source element is NaN, the quietized NaN source value is returned for that element. Negative (non-zero) source numbers, as well as - ∞, return the canonical NaN and set the Invalid Flag (#I).

A value of -0 must return - ∞ and set the DivByZero flags (#Z). Negative numbers should return NaN and set the Invalid flag (#I). Note however that the instruction flush input denormals to zero of the same sign, so negative denormals return - ∞ and set the DivByZero flag.

The first source operand is an XMM register. The second source operand is an XMM register or a 32-bit memory location. The destination operand is a XMM register.

A numerically exact implementation of VRSQRT28xx can be found at <u>https://software.intel.com/en-us/articles/reference-implementations-for-IA-approximation-instructions-vrcp14-vrsqrt14-vrcp28-vrsqrt28-vexp2.</u>

### Operation

### VRSQRT28SS (EVEX encoded versions)

IF k1[0] OR *no writemask* THEN

DEST[31: 0] := (1.0/ SQRT(SRC[31: 0]));

### ELSE

IF *merging-masking* ; merging-masking THEN *DEST[31: 0] remains unchanged* ELSE ; zeroing-masking DEST[31: 0] := 0 FI;

FI; ENDFOR; DEST[127:32] := SRC1[127: 32] DEST[MAXVL-1:128] := 0

8-34 Vol. 2D VRSQRT28SS—Approximation to the Reciprocal Square Root of Scalar Single Precision Floating-Point Value with Less Than 2^-28 Rel-

INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

Table 8-10. VRSQRT28SS Special Cases

|Input value|Result value|Comments|
|---|---|---|
|NAN|QNAN(input)|If (SRC = SNaN) then #I|
|X = 2<sup>-2n</sup>|2<sup>n</sup>||
|X < 0|QNaN_Indefinite|Including -INF|
|X = -0 or negative denormal|-INF|#Z|
|X = +0 or positive denormal|+INF|#Z|
|X = +INF|+0||



Intel C/C++ Compiler Intrinsic Equivalent

VRSQRT28SS __m128 _mm_rsqrt28_round_ss(__m128 a, __m128 b, int rounding); VRSQRT28SS __m128 _mm_mask_rsqrt28_round_ss(__m128 s, __mmask8 m,__m128 a,__m128 b, int rounding); VRSQRT28SS __m128 _mm_maskz_rsqrt28_round_ss(__mmask8 m,__m128 a,__m128 b, int rounding);

SIMD Floating-Point Exceptions

Invalid (if SNaN input), Divide-by-zero

Other Exceptions

See Table 2-47, “Type E3 Class Exception Conditions”.

VRSQRT28SS—Approximation to the Reciprocal Square Root of Scalar Single Precision Floating-Point Value with Less Than 2^-28 Rel-

Vol. 2D 8-35

INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

VSCATTERPF0DPS/VSCATTERPF0QPS/VSCATTERPF0DPD/VSCATTERPF0QPD—Sparse Prefetch Packed SP/DP Data Values with Signed Dword, Signed Qword Indices Using T0 Hint with Intent to Write

|Opcode/<br>Instruction|Op/<br>En|64/32<br>bit Mode<br>Support|CPUID<br>Feature<br>Flag|Description|
|---|---|---|---|---|
|EVEX.512.66.0F38.W0 C6 /5 /vsib<br>VSCATTERPF0DPS vm32z {k1}|A|V/V|AVX512PF|Using signed dword indices, prefetch sparse byte<br>memory locations containing single-precision data using<br>writemask k1 and T0 hint with intent to write.|
|EVEX.512.66.0F38.W0 C7 /5 /vsib<br>VSCATTERPF0QPS vm64z {k1}|A|V/V|AVX512PF|Using signed qword indices, prefetch sparse byte<br>memory locations containing single-precision data using<br>writemask k1 and T0 hint with intent to write.|
|EVEX.512.66.0F38.W1 C6 /5 /vsib<br>VSCATTERPF0DPD vm32y {k1}|A|V/V|AVX512PF|Using signed dword indices, prefetch sparse byte<br>memory locations containing double precision data<br>usingwritemask k1 and T0 hint with intent to write.|
|EVEX.512.66.0F38.W1 C7 /5 /vsib<br>VSCATTERPF0QPD vm64z {k1}|A|V/V|AVX512PF|Using signed qword indices, prefetch sparse byte<br>memory locations containing double precision data<br>usingwritemask k1 and T0 hint with intent to write.|



## Instruction Operand Encoding

|Op/En|Tuple Type|Operand 1|Operand 2|Operand 3|Operand 4|
|---|---|---|---|---|---|
|A|Tuple1 Scalar|BaseReg (R): VSIB:base,<br>VectorReg(R): VSIB:index|NA|NA|NA|



### Description

The instruction conditionally prefetches up to sixteen 32-bit or eight 64-bit integer byte data elements. The elements are specified via the VSIB (i.e., the index register is an zmm, holding packed indices). Elements will only be prefetched if their corresponding mask bit is one.

cache lines will be brought into exclusive state (RFO) specified by a locality hint (T0):

- T0 (temporal data)—prefetch data into the first level cache.

[PS data] For dword indices, the instruction will prefetch sixteen memory locations. For qword indices, the instruction will prefetch eight values.

[PD data] For dword and qword indices, the instruction will prefetch eight memory locations.

Note that:

- (1) The prefetches may happen in any order (or not at all). The instruction is a hint.

- (2) The mask is left unchanged.

- (3) Not valid with 16-bit effective addresses. Will deliver a #UD fault.

- (4) No FP nor memory faults may be produced by this instruction.

- (5) Prefetches do not handle cache line splits

- (6) A #UD is signaled if the memory operand is encoded without the SIB byte.

### Operation

BASE_ADDR stands for the memory operand base address (a GPR); may not exist VINDEX stands for the memory operand vector of indices (a vector register) SCALE stands for the memory operand scalar (1, 2, 4 or 8) DISP is the optional 1, 2 or 4 byte displacement

PREFETCH(mem, Level, State) Prefetches a byte memory location pointed by ‘mem’ into the cache level specified by ‘Level’; a request for exclusive/ownership is done if ‘State’ is 1. Note that the memory location ignore cache line splits. This operation is considered a hint for the processor and may be skipped depending on implementation.

8-36 Vol. 2D VSCATTERPF0DPS/VSCATTERPF0QPS/VSCATTERPF0DPD/VSCATTERPF0QPD—Sparse Prefetch Packed SP/DP Data Values with

INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

VSCATTERPF0DPS (EVEX encoded version) (KL, VL) = (16, 512) FOR j := 0 TO KL-1 i := j * 32 IF k1[j] Prefetch( [BASE_ADDR + SignExtend(VINDEX[i+31:i]) * SCALE + DISP], Level=0, RFO = 1) FI; ENDFOR

VSCATTERPF0DPD (EVEX encoded version) (KL, VL) = (8, 512) FOR j := 0 TO KL-1 i := j * 64 k := j * 32 IF k1[j] Prefetch( [BASE_ADDR + SignExtend(VINDEX[k+31:k]) * SCALE + DISP], Level=0, RFO = 1) FI; ENDFOR

VSCATTERPF0QPS (EVEX encoded version) (KL, VL) = (8, 256) FOR j := 0 TO KL-1 i := j * 64 IF k1[j] Prefetch( [BASE_ADDR + SignExtend(VINDEX[i+63:i]) * SCALE + DISP], Level=0, RFO = 1) FI; ENDFOR

VSCATTERPF0QPD (EVEX encoded version) (KL, VL) = (8, 512) FOR j := 0 TO KL-1 i := j * 64 k := j * 64 IF k1[j] Prefetch( [BASE_ADDR + SignExtend(VINDEX[k+63:k]) * SCALE + DISP], Level=0, RFO = 1) FI; ENDFOR

### Intel C/C++ Compiler Intrinsic Equivalent

VSCATTERPF0DPD void _mm512_prefetch_i32scatter_pd(void *base, __m256i vdx, int scale, int hint); VSCATTERPF0DPD void _mm512_mask_prefetch_i32scatter_pd(void *base, __mmask8 m, __m256i vdx, int scale, int hint); VSCATTERPF0DPS void _mm512_prefetch_i32scatter_ps(void *base, __m512i vdx, int scale, int hint); VSCATTERPF0DPS void _mm512_mask_prefetch_i32scatter_ps(void *base, __mmask16 m, __m512i vdx, int scale, int hint); VSCATTERPF0QPD void _mm512_prefetch_i64scatter_pd(void * base, __m512i vdx, int scale, int hint); VSCATTERPF0QPD void _mm512_mask_prefetch_i64scatter_pd(void * base, __mmask8 m, __m512i vdx, int scale, int hint); VSCATTERPF0QPS void _mm512_prefetch_i64scatter_ps(void * base, __m512i vdx, int scale, int hint); VSCATTERPF0QPS void _mm512_mask_prefetch_i64scatter_ps(void * base, __mmask8 m, __m512i vdx, int scale, int hint);

SIMD Floating-Point Exceptions

None

### Other Exceptions

See Table 2-62, “Type E12NP Class Exception Conditions”.

VSCATTERPF0DPS/VSCATTERPF0QPS/VSCATTERPF0DPD/VSCATTERPF0QPD—Sparse Prefetch Packed SP/DP Data Values with

Vol. 2D 8-37

INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

VSCATTERPF1DPS/VSCATTERPF1QPS/VSCATTERPF1DPD/VSCATTERPF1QPD—Sparse Prefetch Packed SP/DP Data Values with Signed Dword, Signed Qword Indices Using T1 Hint with Intent to Write

|Opcode/<br>Instruction|Op/<br>En|64/32<br>bit Mode<br>Support|CPUID<br>Feature<br>Flag|Description|
|---|---|---|---|---|
|EVEX.512.66.0F38.W0 C6 /6 /vsib<br>VSCATTERPF1DPS vm32z {k1}|A|V/V|AVX512PF|Using signed dword indices, prefetch sparse byte memory<br>locations containing single-precision data using writemask<br>k1 and T1 hint with intent to write.|
|EVEX.512.66.0F38.W0 C7 /6 /vsib<br>VSCATTERPF1QPS vm64z {k1}|A|V/V|AVX512PF|Using signed qword indices, prefetch sparse byte memory<br>locations containing single-precision data using writemask<br>k1 and T1 hint with intent to write.|
|EVEX.512.66.0F38.W1 C6 /6 /vsib<br>VSCATTERPF1DPD vm32y {k1}|A|V/V|AVX512PF|Using signed dword indices, prefetch sparse byte memory<br>locations containing double precision data using<br>writemask k1 and T1 hint with intent to write.|
|EVEX.512.66.0F38.W1 C7 /6 /vsib<br>VSCATTERPF1QPD vm64z {k1}|A|V/V|AVX512PF|Using signed qword indices, prefetch sparse byte memory<br>locations containing double precision data using<br>writemask k1 and T1 hint with intent to write.|



## Instruction Operand Encoding

|Op/En|Tuple Type|Operand 1|Operand 2|Operand 3|Operand 4|
|---|---|---|---|---|---|
|A|Tuple1 Scalar|BaseReg (R): VSIB:base,<br>VectorReg(R): VSIB:index|NA|NA|NA|



### Description

The instruction conditionally prefetches up to sixteen 32-bit or eight 64-bit integer byte data elements. The elements are specified via the VSIB (i.e., the index register is an zmm, holding packed indices). Elements will only be prefetched if their corresponding mask bit is one.

cache lines will be brought into exclusive state (RFO) specified by a locality hint (T1):

- T1 (temporal data)—prefetch data into the second level cache.

[PS data] For dword indices, the instruction will prefetch sixteen memory locations. For qword indices, the instruction will prefetch eight values.

[PD data] For dword and qword indices, the instruction will prefetch eight memory locations.

Note that:

- (1) The prefetches may happen in any order (or not at all). The instruction is a hint.

- (2) The mask is left unchanged.

- (3) Not valid with 16-bit effective addresses. Will deliver a #UD fault.

- (4) No FP nor memory faults may be produced by this instruction.

- (5) Prefetches do not handle cache line splits

- (6) A #UD is signaled if the memory operand is encoded without the SIB byte.

### Operation

BASE_ADDR stands for the memory operand base address (a GPR); may not exist VINDEX stands for the memory operand vector of indices (a vector register) SCALE stands for the memory operand scalar (1, 2, 4 or 8) DISP is the optional 1, 2 or 4 byte displacement

PREFETCH(mem, Level, State) Prefetches a byte memory location pointed by ‘mem’ into the cache level specified by ‘Level’; a request for exclusive/ownership is done if ‘State’ is 1. Note that the memory location ignore cache line splits. This operation is considered a hint for the processor and may be skipped depending on implementation.

8-38 Vol. 2D VSCATTERPF1DPS/VSCATTERPF1QPS/VSCATTERPF1DPD/VSCATTERPF1QPD—Sparse Prefetch Packed SP/DP Data Values with

INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

VSCATTERPF1DPS (EVEX encoded version) (KL, VL) = (16, 512) FOR j := 0 TO KL-1 i := j * 32 IF k1[j] Prefetch( [BASE_ADDR + SignExtend(VINDEX[i+31:i]) * SCALE + DISP], Level=1, RFO = 1) FI; ENDFOR

VSCATTERPF1DPD (EVEX encoded version) (KL, VL) = (8, 512) FOR j := 0 TO KL-1 i := j * 64 k := j * 32 IF k1[j] Prefetch( [BASE_ADDR + SignExtend(VINDEX[k+31:k]) * SCALE + DISP], Level=1, RFO = 1) FI; ENDFOR

VSCATTERPF1QPS (EVEX encoded version) (KL, VL) = (8, 512) FOR j := 0 TO KL-1 i := j * 64 IF k1[j] Prefetch( [BASE_ADDR + SignExtend(VINDEX[i+63:i]) * SCALE + DISP], Level=1, RFO = 1) FI; ENDFOR

VSCATTERPF1QPD (EVEX encoded version) (KL, VL) = (8, 512) FOR j := 0 TO KL-1 i := j * 64 k := j * 64 IF k1[j] Prefetch( [BASE_ADDR + SignExtend(VINDEX[k+63:k]) * SCALE + DISP], Level=1, RFO = 1) FI; ENDFOR

### Intel C/C++ Compiler Intrinsic Equivalent

VSCATTERPF1DPD void _mm512_prefetch_i32scatter_pd(void *base, __m256i vdx, int scale, int hint); VSCATTERPF1DPD void _mm512_mask_prefetch_i32scatter_pd(void *base, __mmask8 m, __m256i vdx, int scale, int hint); VSCATTERPF1DPS void _mm512_prefetch_i32scatter_ps(void *base, __m512i vdx, int scale, int hint); VSCATTERPF1DPS void _mm512_mask_prefetch_i32scatter_ps(void *base, __mmask16 m, __m512i vdx, int scale, int hint); VSCATTERPF1QPD void _mm512_prefetch_i64scatter_pd(void * base, __m512i vdx, int scale, int hint); VSCATTERPF1QPD void _mm512_mask_prefetch_i64scatter_pd(void * base, __mmask8 m, __m512i vdx, int scale, int hint); VSCATTERPF1QPS void _mm512_prefetch_i64scatter_ps(void *base, __m512i vdx, int scale, int hint); VSCATTERPF1QPS void _mm512_mask_prefetch_i64scatter_ps(void *base, __mmask8 m, __m512i vdx, int scale, int hint);

SIMD Floating-Point Exceptions

None

### Other Exceptions

See Table 2-62, “Type E12NP Class Exception Conditions”.

VSCATTERPF1DPS/VSCATTERPF1QPS/VSCATTERPF1DPD/VSCATTERPF1QPD—Sparse Prefetch Packed SP/DP Data Values with

Vol. 2D 8-39

INSTRUCTION SET REFERENCE UNIQUE TO INTEL® XEON PHI™ PROCESSORS

VSCATTERPF1DPS/VSCATTERPF1QPS/VSCATTERPF1DPD/VSCATTERPF1QPD—Sparse Prefetch Packed SP/DP Data Values with

8-40 Vol. 2D
