---
name: docs-md-gfx90a-09-chapter-6-vector-alu-operations
description: "AMD CDNA2 ISA: Chapter 6. Vector ALU Operations (vendor documentation for AMD gfx90a (CDNA2))."
when: "when you need AMD CDNA2 ISA: Chapter 6. Vector ALU Operations while writing a kernel for AMD gfx90a (CDNA2)."
---

"AMD Instinct MI200" Instruction Set Architecture



# **Chapter 6. Vector ALU Operations**

Vector ALU instructions (VALU) perform an arithmetic or logical operation on data for each of 64 threads and write results back to VGPRs, SGPRs or the EXEC mask.

Parameter interpolation is a mixed VALU and LDS instruction, and is described in the Data Share chapter.

## **6.1. Microcode Encodings**

Most VALU instructions are available in two encodings: VOP3 which uses 64-bits of instruction and has the full range of capabilities, and one of three 32-bit encodings that offer a restricted set of capabilities. A few instructions are only available in the VOP3 encoding. The only instructions that cannot use the VOP3 format are the parameter interpolation instructions.

When an instruction is available in two microcode formats, it is up to the user to decide which to use. It is recommended to use the 32-bit encoding whenever possible.

The microcode encodings are shown below.

VOP2 is for instructions with two inputs and a single vector destination. Instructions that have a carry-out implicitly write the carry-out to the VCC register.



VOP1 is for instructions with no inputs or a single input and one destination.



VOPC is for comparison instructions.



VOP3 is for instructions with up to three inputs, input modifiers (negate and absolute value), and output modifiers. There are two forms of VOP3: one which uses a scalar destination field (used only for div_scale, integer add and subtract); this is designated VOP3b. All other instructions use the common form, designated VOP3a.



6.1. Microcode Encodings

35 of 267

"AMD Instinct MI200" Instruction Set Architecture





Any of the 32-bit microcode formats may use a 32-bit literal constant, but not VOP3.

VOP3P is for instructions that use "packed math": They perform the operation on a pair of input values that are packed into the high and low 16-bits of each operand; the two 16-bit results are written to a single VGPR as two packed values.



VOP3P-MAI is a varation of the VOP3P format for use with the Matrix Arithmetic Instructions (MAI).



## **6.2. Operands**

All VALU instructions take at least one input operand (except V_NOP and V_CLREXCP). The data-size of the operands is explicitly defined in the name of the instruction. For example, V_MAD_F32 operates on 32-bit floating point data.

### **6.2.1. Instruction Inputs**

VALU instructions can use any of the following sources for input, subject to restrictions listed below:

- VGPRs.

- SGPRs.

- Inline constants - constant selected by a specific VSRC value.

- Literal constant - 32-bit value in the instruction stream. When a literal constant is used with a 64bit instruction, the literal is expanded to 64 bits by: padding the LSBs with zeros for floats, padding the MSBs with zeros for unsigned ints, and by sign-extending signed ints.

- LDS direct data read.

- M0.

- EXEC mask.

#### **Limitations**

6.2. Operands

36 of 267

"AMD Instinct MI200" Instruction Set Architecture



- At most one SGPR can be read per instruction, but the value can be used for more than one operand.

- At most one literal constant can be used, and only when an SGPR or M0 is not used as a source.

- Only SRC0 can use LDS_DIRECT (see Chapter 10, "Data Share Operations").

#### **Limitations for Constants**

VALU "ADDC", "SUBB" and CNDMASK all implicitly use an SGPR value (VCC), so these instructions cannot use an additional SGPR or literal constant.

Instructions using the VOP3 form and also using floating-point inputs have the option of applying absolute value (ABS field) or negate (NEG field) to any of the input operands.

#### **6.2.1.1. Literal Expansion to 64 bits**

Literal constants are 32-bits, but they can be used as sources which normally require 64-bit data:

- 64 bit float: the lower 32-bit are padded with zero.

- 64-bit unsigned integer: zero extended to 64 bits

- 64-bit signed integer: sign extended to 64 bits

### **6.2.2. Instruction Outputs**

VALU instructions typically write their results to VGPRs specified in the VDST field of the microcode word. A thread only writes a result if the associated bit in the EXEC mask is set to 1.

All V_CMPX instructions write the result of their comparison (one bit per thread) to both an SGPR (or VCC) and the EXEC mask.

Instructions producing a carry-out (integer add and subtract) write their result to VCC when used in the VOP2 form, and to an arbitrary SGPR-pair when used in the VOP3 form.

When the VOP3 form is used, instructions with a floating-point result can apply an output modifier (OMOD field) that multiplies the result by: 0.5, 1.0, 2.0 or 4.0. Optionally, the result can be clamped (CLAMP field) to the range [0.0, +1.0].

Output modifiers apply only to floating point results and are ignored for integer or bit results. Output modifiers are not compatible with output denormals: if output denormals are enabled, then output modifiers are ignored. If output demormals are disabled, then the output modifier is applied and denormals are flushed to zero. Output modifiers are not IEEE compatible: -0 is flushed to +0. Output modifiers are ignored if the IEEE mode bit is set to 1.

6.2. Operands

37 of 267

"AMD Instinct MI200" Instruction Set Architecture



In the table below, all codes can be used when the vector source is nine bits; codes 0 to 255 can be the scalar source if it is eight bits; codes 0 to 127 can be the scalar source if it is seven bits; and codes 256 to 511 can be the vector source or destination.

_Table 20. Instruction Operands_

|**Value**|**Name**|**Description**|
|---|---|---|
|0-101|SGPR|0 .. 101|
|102|FLATSCR_LO|Flat Scratch[31:0].|
|103|FLATSCR_HI|Flat Scratch[63:32].|
|104|XNACK_MASK_LO||
|105|XNACK_MASK_HI||
|106|VCC_LO|vcc[31:0].|
|107|VCC_HI|vcc[63:32].|
|108-123|TTMP0 to TTMP 15|Trap handler temps (privileged).|
|124|M0||
|125|reserved||
|126|EXEC_LO|exec[31:0].|
|127|EXEC_HI|exec[63:32].|
|128|0||
|129-192|int 1.. 64|Integer inline constants.|
|193-208|int -1 .. -16||
|209-234|reserved|Unused.|
|235|SHARED_BASE|Memory Aperture definition.|
|236|SHARED_LIMIT||
|237|PRIVATE_BASE||
|238|PRIVATE_LIMIT||
|239|POPS_EXITING_WAVE_ID|Primitive Ordered Pixel Shading wave ID.|
|240|0.5|Single, double, or half-precision inline floats.|
|241|-0.5|1/(2*PI) is 0.15915494.|
|242|1.0|The exact value used is:<br>half: 0x3118|
|243|-1.0|<br>single: 0x3e22f983|
|244|2.0|double: 0x3fc45f306dc9c882|
|245|-2.0||
|246|4.0||
|247|-4.0||
|248|1/(2*PI)||



6.2. Operands

38 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Value**|**Name**|**Description**|
|---|---|---|
|249|SDWA|Sub Dword Address (only valid as Source-0)|
|250|DPP|DPP over 16 lanes (only valid as Source-0)|
|251|VCCZ|{ zeros, VCCZ }|
|252|EXECZ|{ zeros, EXECZ }|
|253|SCC|{ zeros, SCC }|
|254|LDS direct|Use LDS direct read to supply 32-bit value Vector-alu instructions only.|
|255|Literal|constant 32-bit constant from instruction stream.|
|256-511|VGPR|0 .. 255|



### **6.2.3. Out-of-Range GPRs**

When a source VGPR is out-of-range, the instruction uses as input the value from VGPR0.

When the destination GPR is out-of-range, the instruction executes but does not write the results.

## **6.3. Instructions**

The table below lists the complete VALU instruction set by microcode encoding, except for VOP3P instructions which are listed in a later section.

_Table 21. VALU Instruction Set_

|**VOP3**|**VOP3 - 1-2 operand opcodes**|**VOP2**|**VOP1**|
|---|---|---|---|
|V_MAD_LEGACY_F32|V_ADD_F64|V_ADD_{ F16,F32,<br>U16,U32}|V_NOP|
|V_MAD_{<br>F16,I16,U16,F32}|V_MUL_F64|V_SUB_{ F16,F32,U16,<br>U32}|V_MOV_B32|
|V_MAD_LEGACY_{F16,U16,<br>I16}|V_MIN_F64|V_SUBREV_{ F16,F32,<br>U16,U32}||
|V_MAD_I32_I24|V_MAX_F64|V_ADD_CO_U32|V_READFIRSTLANE_B32|
|V_MAD_U32_U24|V_LDEXP_F64|V_SUB_CO_U32|V_CVT_F32_{I32,U32,F16,<br>F64 }|
|V_CUBEID_F32|V_MUL_LO_U32|V_SUBREV_CO_U32|V_CVT_{I32,U32,F16,<br>F64}_F32|
|V_CUBESC_F32|V_MUL_HI_{I32,U32}|V_ADDC_U32|V_CVT_{I32,U32}_F64|
|V_CUBETC_F32|V_LSHLREV_B64|V_SUBB_U32|V_CVT_F64_{I32,U32}|
|V_CUBEMA_F32|V_LSHRREV_B64|V_SUBBREV_U32|V_CVT_F32_UBYTE{0,1,2,3<br>}|
|V_BFE_{U32 , I32 }|V_ASHRREV_I64||V_CVT_F16_{U16, I16}|



6.3. Instructions

39 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**VOP3**|**VOP3 - 1-2 operand opcodes**|**VOP2**|**VOP1**|
|---|---|---|---|
|V_FMA_{ F16, F32 ,<br>F64}|V_LDEXP_F32|V_MUL_{F16, F32}|V_CVT_RPI_I32_F32|
|V_FMA_LEGACY_F16|V_READLANE_B32|V_MUL_I32_I24|V_CVT_FLR_I32_F32|
|V_BFI_B32|V_WRITELANE_B32|V_MUL_HI_I32_I24|V_CVT_OFF_F32_I4|
|V_LERP_U8|V_BCNT_U32_B32|V_MUL_U32_U24|V_FRACT_{ F16,F32,F64}|
|V_ALIGNBIT_B32|V_MBCNT_LO_U32_B32|V_MUL_HI_U32_U24|V_TRUNC_{ F16,F32, F64}|
|V_ALIGNBYTE_B32|V_MBCNT_HI_U32_B32|V_MIN_{ F16,U16,<br>I16,F32,I32,U32}|V_CEIL_{ F16,F32, F64}|
|V_MIN3_{F32,I32,U32}|V_CVT_PKACCUM_U8_F32|V_MAX_{ F16,U16,<br>I16,F32,I32,U32}|V_RNDNE_{ F16,F32, F64}|
|V_MAX3_{F32,I32,U32}|V_CVT_PKNORM_I16_F32|V_LSHRREV_{ B16,B32}|V_FLOOR_{ F16,F32, F64}|
|V_MED3_{F32,I32,U32}|V_CVT_PKNORM_U16_F32|V_ASHRREV_{I16,I32}|V_EXP_{ F16,F32}|
|V_SAD_{U8, HI_U8, U16,<br>U32}|V_CVT_PKRTZ_F16_F32|V_LSHLREV_{ B16,B32}|V_LOG_ {F16,F32}|
|V_CVT_PK_U8_F32|V_CVT_PK_U16_U32|V_AND_B32|V_RCP_{ F16,F32,F64}|
|V_DIV_FIXUP_{<br>F16,F32,F64}|V_CVT_PK_I16_I32|V_OR_B32|V_RCP_IFLAG_F32|
|V_DIV_FIXUP_LEGACY_F16||V_XOR_B32|V_RSQ_{ F16,F32, F64}|
|V_DIV_SCALE_{F32,F64}|V_BFM_B32|V_MAC_{ F16,F32}|V_SQRT_{ F16,F32,F64}|
|V_DIV_FMAS_{F32,F64}|V_INTERP_P1_F32|V_MADMK_{ F16,F32}|V_SIN_ {F16,F32}|
|V_MSAD_U8|V_INTERP_P2_F32|V_MADAK_{ F16,F32}|V_COS_ {F16,F32}|
|V_QSAD_PK_U16_U8|V_INTERP_MOV_F32|V_CNDMASK_B32|V_NOT_B32|
|V_MQSAD_PK_U16_U8|V_INTERP_P1LL_F16|V_LDEXP_F16|V_BFREV_B32|
|V_MQSAD_PK_U32_U8|V_INTERP_P1LV_F16|MUL_LO_U16|V_FFBH_{U32, I32}|
|V_TRIG_PREOP_F64|V_INTERP_P2_F16||V_FFBL_B32|
|V_MAD_{U64_U32,<br>I64_I32}|V_INTERP_P2_LEGACY_F16|V_DOT2C_F32_F16|V_FREXP_EXP_I32_F64|
|V_MUL_LEGACY_F32|V_CVT_PKNORM_I16_F16|V_DOT2C_I32_I16|V_FREXP_MANT_{<br>F16,F32,64}|
|V_FMAC_F64|V_CVT_PKNORM_U16_F16|V_DOT4C_I32_I8|V_FREXP_EXP_I32_F32|
||V_MAD_U32_U16|V_DOT8C_I32_I4|V_FREXP_EXP_I16_F16|
||V_MAD_I32_I16|V_PK_FMAC_F16|V_CLREXCP|
||V_XAD_U32||V_ACCVGPR_MOV_B32|
||V_MIN3_{F16,I16,U16}||V_CVT_NORM_I16_F16|
||V_MAX3_{F16,I16,U16}||V_CVT_NORM_U16_F16|
||V_MED3_{F16,I16,U16}||V_SAT_PK_U8_I16|
||V_CVT_PKNORM_{I16_F16,<br>U16_F16}|||
||V_READLANE_REGRD_B32||V_SWAP_B32|



6.3. Instructions

40 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**VOP3**|**VOP3 - 1-2 operand opcodes**|**VOP2**|**VOP1**|
|---|---|---|---|
||V_PACK_B32_F16||V_SCREEN_PARTITION_4SE_<br>B32|



The next table lists the compare instructions.

_Table 22. VALU Instruction Set_

|**Op**|**Formats**|**Functions**|**Result**|
|---|---|---|---|
|V_CMP|I16, I32, I64, U16,<br>|F, LT, EQ, LE, GT, LG, GE, T|Write VCC..|
|V_CMPX|U32, U64||Write VCC and<br>exec.|
|V_CMP|F16, F32, F64|F, LT, EQ, LE, GT, LG, GE, T,<br>O, U, NGE, NLG, NGT, NLE, NEQ, NLT|Write VCC.|
|V_CMPX||(o = total order, u = unordered,<br>N = NaN or normal compare)|Write VCC and<br>exec.|
|V_CMP_CL<br>ASS|F16, F32, F64|Test for one of: signaling-NaN, quiet-NaN,<br>positive or negative: infinity, normal, subnormal, zero.|Write VCC.|
|V_CMPX_C<br>LASS|||Write VCC and<br>exec.|



## **6.4. Denormalized and Rounding Modes**

The shader program has explicit control over the rounding mode applied and the handling of denormalized inputs and results. The MODE register is set using the S_SETREG instruction; it has separate bits for controlling the behavior of single and double-precision floating-point numbers.

Note: that V_DOT2 instructions operating on floating point data do not support denormal and rounding modes. They always flush input and output denorms.

_Table 23. Round and Denormal Modes_

|**Field**|**Bit Position**|**Description**|
|---|---|---|
|FP_ROUND|3:0|[1:0] Single-precision round mode.<br>[3:2] Double/Half-precision round mode.<br>Round Modes: 0=nearest even; 1= +infinity; 2= -infinity, 3= toward zero.|
|FP_DENORM|7:4|[5:4] Single-precision denormal mode.<br>[7:6] Double/Half-precision denormal mode.<br>Denormal modes:<br>0 = Flush input and output denorms.<br>1 = Allow input denorms, flush output denorms.<br>2 = Flush input denorms, allow output denorms.<br>3 = Allow input and output denorms.|



6.4. Denormalized and Rounding Modes

41 of 267

"AMD Instinct MI200" Instruction Set Architecture



## **6.5. ALU Clamp Bit Usage**

When using V_CMP instructions, setting the clamp bit to 1 indicates that the compare signals if a floating point exception occurs. For integer operations, it clamps the result to the largest and smallest representable value. For floating point operations, it clamps the result to the range: [0.0, 1.0].

## **6.6. VGPR Indexing**

VGPR Indexing allows a value stored in the M0 register to act as an index into the VGPRs either for the source or destination registers in VALU instructions.

### **6.6.1. Indexing Instructions**

The table below describes the instructions which enable, disable and control VGPR indexing.

_Table 24. VGPR Indexing Instructions_

|**Instruction**|**Encoding**|**Sets**<br>**SCC?**|**Operation**|
|---|---|---|---|
|S_SET_GPR_IDX_OFF|SOPP|N|Disable VGPR indexing mode. Sets: mode.gpr_idx_en = 0.|
|S_SET_GPR_IDX_ON|SOPC|N|Enable VGPR indexing, and set the index value and mode<br>from an SGPR. mode.gpr_idx_en = 1<br>M0[7:0] = S0.u[7:0]<br>M0[15:12] = SIMM4|
|S_SET_GPR_IDX_IDX|SOP1|N|Set the VGPR index value:<br>M0[7:0] = S0.u[7:0]|
|S_SET_GPR_IDX_MODE|SOPP|N|Change the VGPR indexing mode, which is stored in<br>M0[15:12].<br>M0[15:12] = SIMM4|



Indexing is enabled and disabled by a bit in the MODE register: gpr_idx_en. When enabled, two fields from M0 are used to determine the index value and what it applies to:

- M0[7:0] holds the unsigned index value, added to selected source or destination VGPR addresses.

- M0[15:12] holds a four-bit mask indicating to which source or destination the index is applied.

   - ◦M0[15] = dest_enable.

   - ◦M0[14] = src2_enable.

   - ◦M0[13] = src1_enable.

   - ◦M0[12] = src0_enable.

Indexing only works on VGPR source and destinations, not on inline constants or SGPRs. It is

6.5. ALU Clamp Bit Usage

42 of 267

"AMD Instinct MI200" Instruction Set Architecture



illegal for the index attempt to address VGPRs that are out of range.

### **6.6.2. VGPR Indexing Details**

This section describes how VGPR indexing is applied to instructions that use source and destination registers in unusual ways. The table below shows which M0 bits control indexing of the sources and destination registers for these specific instructions.

|**Instruction**|**Microcode Encodes**|**VALU Receives**|**M0[15]**<br>**(dst)**|**M0[15]**<br>**(s2)**|**M0[15]**<br>**(s1)**|**M0[12]**<br>**(s0)**|
|---|---|---|---|---|---|---|
|v_readlane|sdst = src0, SS1||x|x|x|src0|
|v_readfirstlane|sdst = func(src0)||x|x|x|src0|
|v_writelane|dst = func(ss0, ss1)||dst|x|x|x|
|v_mac_*|dst = src0 * src1 + dst|mad: dst, src0, src1,<br>src2|dst, s2|x|src1|src0|
|v_madak|dst = src0 * src1 + imm|mad: dst, src0, src1,<br>src2|dst|x|src1|src0|
|v_madmk|dst = S0 * imm + src1|mad: dst, src0, src1,<br>src2|dst|src2|x|src0|
|v_*sh*_rev|dst = S1 << S0|<shift> (src1, src0)|dst|x|src1|src0|
|v_cvt_pkaccum|uses dst as src2||dst, s2|x|src1|src0|
|SDWA (dest preserve,<br>sub-Dword mask)|uses dst as src2 for<br>read-mod-write|||dst, s2|||



where:

src= vector source SS = scalar source dst = vector destination sdst = scalar destination

## **6.7. Packed Math**

CDNA supports **packed math** , which performs operations on two 16-bit values within a Dword as if they were separate elements. For example, a packed add of V0=V1+V2 is really two separate adds: adding the low 16 bits of each Dword and storing the result in the low 16 bits of V0, and adding the high halves.

Packed math uses the instructions below and the microcode format "VOP3P". This format adds op_sel and neg fields for both the low and high operands, and removes ABS and OMOD.

Packed Math Opcodes:

6.7. Packed Math

43 of 267

"AMD Instinct MI200" Instruction Set Architecture



|V_PK_MAD_I16|V_PK_MUL_LO_U16|V_PK_ADD_I16|V_PK_SUB_I16|
|---|---|---|---|
|V_PK_LSHLREV_B16|V_PK_LSHRREV_B16|V_PK_ASHRREV_I16|V_PK_MAX_I16|
|V_PK_MIN_I16|V_PK_MAD_U16|V_PK_ADD_U16|V_PK_SUB_U16|
|V_PK_MAX_U16|V_PK_MIN_U16|V_PK_FMA_F16|V_PK_ADD_F16|
|V_PK_MUL_F16|V_PK_MIN_F16|V_PK_MAX_F16|V_MAD_MIX_F32|
|V_MAD_MIXLO_F16|V_MAD_MIXHI_F16|V_PK_FMA_F32|V_PK_MUL_F32|





V_MAD_MIX_* are not packed math, but perform a single Multiply-Add operation on a mixture of 16- and 32-bit inputs. The Mulitply-add is performed as an FMA - fused multiply-add. They are listed here because they use the VOP3P encoding.



Packed 32-bit instructions operate on 2 dwords at a time and those operands must be two-dword aligned (i.e. an even VGPR address). Output modifiers are not supported for these instructions. OPSEL and OPSEL_HI work to select the first or second DWORD for each source.

6.7. Packed Math

44 of 267
