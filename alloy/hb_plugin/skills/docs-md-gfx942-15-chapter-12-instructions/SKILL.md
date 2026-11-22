---
name: docs-md-gfx942-15-chapter-12-instructions
description: "AMD CDNA3 ISA: Chapter 12. Instructions (vendor documentation for AMD gfx942 (CDNA3))."
when: "when you need AMD CDNA3 ISA: Chapter 12. Instructions while writing a kernel for AMD gfx942 (CDNA3)."
---

"AMD Instinct MI300" Instruction Set Architecture



# **Chapter 12. Instructions**

This chapter lists, and provides descriptions for, all instructions in the CDNA Generation environment. Instructions are grouped according to their format.

#### **Instruction suffixes have the following definitions:**

- B32 Bitfield (untyped data) 32-bit

- B64 Bitfield (untyped data) 64-bit

- F32 floating-point 32-bit (IEEE 754 single-precision float)

- F64 floating-point 64-bit (IEEE 754 double-precision float)

- BF16 floating-point 16 bit (Bfloat16 format)

- I8 signed 8-bit integer

- I16 signed 16-bit integer

- I32 signed 32-bit integer

- I64 signed 64-bit integer

- U32 unsigned 32-bit integer

- U64 unsigned 64-bit integer

If an instruction has two suffixes (for example, _I32_F32), the first suffix indicates the destination type, the second the source type.

The following abbreviations are used in instruction definitions:

- D = destination

- U = unsigned integer

- S = source

- SCC = scalar condition code

- I = signed integer

- B = bitfield

Note: .u or .i specifies to interpret the argument as an unsigned or signed float.

Note: Rounding and Denormal modes apply to all floating-point operations unless otherwise specified in the instruction description.

## **12.1. SOP2 Instructions**



Instructions in this format may use a 32-bit literal constant which occurs immediately after the instruction.

**S_ADD_U32**

**0**

Add two unsigned 32-bit integer inputs, store the result into a scalar register and store the carry-out bit into SCC.

88 of 553

12.1. SOP2 Instructions

"AMD Instinct MI300" Instruction Set Architecture



tmp = 64'U(S0.u32) + 64'U(S1.u32); SCC = tmp >= 0x100000000ULL ? 1'1U : 1'0U; // unsigned overflow or carry-out for S_ADDC_U32. D0.u32 = tmp.u32

#### **S_SUB_U32**

**1**

Subtract the second unsigned 32-bit integer input from the first input, store the result into a scalar register and store the carry-out bit into SCC.

tmp = S0.u32 - S1.u32; SCC = S1.u32 > S0.u32 ? 1'1U : 1'0U; // unsigned overflow or carry-out for S_SUBB_U32. D0.u32 = tmp.u32

#### **S_ADD_I32**

**2**

Add two signed 32-bit integer inputs, store the result into a scalar register and store the carry-out bit into SCC.

tmp = S0.i32 + S1.i32; SCC = ((S0.u32[31] == S1.u32[31]) && (S0.u32[31] != tmp.u32[31])); // signed overflow. D0.i32 = tmp.i32

#### **Notes**

This opcode is not suitable for use with S_ADDC_U32 for implementing 64-bit operations.

**S_SUB_I32 3**

Subtract the second signed 32-bit integer input from the first input, store the result into a scalar register and store the carry-out bit into SCC.

tmp = S0.i32 - S1.i32; SCC = ((S0.u32[31] != S1.u32[31]) && (S0.u32[31] != tmp.u32[31])); // signed overflow. D0.i32 = tmp.i32

#### **Notes**

This opcode is not suitable for use with S_SUBB_U32 for implementing 64-bit operations.

89 of 553

12.1. SOP2 Instructions

"AMD Instinct MI300" Instruction Set Architecture



#### **S_ADDC_U32**

**4**

Add two unsigned 32-bit integer inputs and a carry-in bit from SCC, store the result into a scalar register and store the carry-out bit into SCC.

tmp = 64'U(S0.u32) + 64'U(S1.u32) + SCC.u64; SCC = tmp >= 0x100000000ULL ? 1'1U : 1'0U; // unsigned overflow or carry-out for S_ADDC_U32. D0.u32 = tmp.u32

#### **S_SUBB_U32**

**5**

Subtract the second unsigned 32-bit integer input from the first input, subtract the carry-in bit, store the result into a scalar register and store the carry-out bit into SCC.

tmp = S0.u32 - S1.u32 - SCC.u32; SCC = 64'U(S1.u32) + SCC.u64 > 64'U(S0.u32) ? 1'1U : 1'0U; // unsigned overflow or carry-out for S_SUBB_U32. D0.u32 = tmp.u32

**S_MIN_I32**

**6**

Select the minimum of two signed 32-bit integer inputs, store the selected value into a scalar register and set SCC iff the first value is selected.

SCC = S0.i32 < S1.i32; D0.i32 = SCC ? S0.i32 : S1.i32

**S_MIN_U32**

**7**

Select the minimum of two unsigned 32-bit integer inputs, store the selected value into a scalar register and set SCC iff the first value is selected.

SCC = S0.u32 < S1.u32; D0.u32 = SCC ? S0.u32 : S1.u32

**S_MAX_I32**

**8**

90 of 553

12.1. SOP2 Instructions

"AMD Instinct MI300" Instruction Set Architecture



Select the maximum of two signed 32-bit integer inputs, store the selected value into a scalar register and set SCC iff the first value is selected.

SCC = S0.i32 >= S1.i32; D0.i32 = SCC ? S0.i32 : S1.i32

#### **S_MAX_U32**

**9**

Select the maximum of two unsigned 32-bit integer inputs, store the selected value into a scalar register and set SCC iff the first value is selected.

SCC = S0.u32 >= S1.u32; D0.u32 = SCC ? S0.u32 : S1.u32

#### **S_CSELECT_B32**

**10**

Select the first input if SCC is true otherwise select the second input, then store the selected input into a scalar register.

D0.u32 = SCC ? S0.u32 : S1.u32

#### **S_CSELECT_B64**

**11**

Select the first input if SCC is true otherwise select the second input, then store the selected input into a scalar register.

D0.u64 = SCC ? S0.u64 : S1.u64

#### **S_AND_B32**

**12**

Calculate bitwise AND on two scalar inputs, store the result into a scalar register and set SCC iff the result is nonzero.

D0.u32 = (S0.u32 & S1.u32); SCC = D0.u32 != 0U

91 of 553

12.1. SOP2 Instructions

"AMD Instinct MI300" Instruction Set Architecture

**13**



#### **S_AND_B64**

Calculate bitwise AND on two scalar inputs, store the result into a scalar register and set SCC iff the result is nonzero.

D0.u64 = (S0.u64 & S1.u64); SCC = D0.u64 != 0ULL

**S_OR_B32 14**

Calculate bitwise OR on two scalar inputs, store the result into a scalar register and set SCC iff the result is nonzero.

D0.u32 = (S0.u32 | S1.u32); SCC = D0.u32 != 0U

**S_OR_B64 15**

Calculate bitwise OR on two scalar inputs, store the result into a scalar register and set SCC iff the result is nonzero.

D0.u64 = (S0.u64 | S1.u64); SCC = D0.u64 != 0ULL

**S_XOR_B32 16**

Calculate bitwise XOR on two scalar inputs, store the result into a scalar register and set SCC iff the result is nonzero.

D0.u32 = (S0.u32 ^ S1.u32); SCC = D0.u32 != 0U

#### **S_XOR_B64**

**17**

Calculate bitwise XOR on two scalar inputs, store the result into a scalar register and set SCC iff the result is nonzero.

D0.u64 = (S0.u64 ^ S1.u64);

92 of 553

12.1. SOP2 Instructions

"AMD Instinct MI300" Instruction Set Architecture



SCC = D0.u64 != 0ULL

#### **S_ANDN2_B32**

**18**

Calculate bitwise AND with the first input and the negation of the second input, store the result into a scalar register and set SCC if the result is nonzero.

D0.u32 = (S0.u32 & ~S1.u32); SCC = D0.u32 != 0U

**S_ANDN2_B64**

**19**

Calculate bitwise AND with the first input and the negation of the second input, store the result into a scalar register and set SCC if the result is nonzero.

D0.u64 = (S0.u64 & ~S1.u64); SCC = D0.u64 != 0ULL

**S_ORN2_B32**

**20**

Calculate bitwise OR with the first input and the negation of the second input, store the result into a scalar register and set SCC if the result is nonzero.

D0.u32 = (S0.u32 | ~S1.u32); SCC = D0.u32 != 0U

**S_ORN2_B64**

**21**

Calculate bitwise OR with the first input and the negation of the second input, store the result into a scalar register and set SCC if the result is nonzero.

D0.u64 = (S0.u64 | ~S1.u64); SCC = D0.u64 != 0ULL

**S_NAND_B32**

**22**

Calculate bitwise NAND on two scalar inputs, store the result into a scalar register and set SCC if the result is

93 of 553

12.1. SOP2 Instructions

"AMD Instinct MI300" Instruction Set Architecture

**23**



nonzero.

D0.u32 = ~(S0.u32 & S1.u32); SCC = D0.u32 != 0U

#### **S_NAND_B64**

Calculate bitwise NAND on two scalar inputs, store the result into a scalar register and set SCC if the result is nonzero.

D0.u64 = ~(S0.u64 & S1.u64); SCC = D0.u64 != 0ULL

#### **S_NOR_B32**

**24**

Calculate bitwise NOR on two scalar inputs, store the result into a scalar register and set SCC if the result is nonzero.

D0.u32 = ~(S0.u32 | S1.u32); SCC = D0.u32 != 0U

#### **S_NOR_B64**

**25**

Calculate bitwise NOR on two scalar inputs, store the result into a scalar register and set SCC if the result is nonzero.

D0.u64 = ~(S0.u64 | S1.u64); SCC = D0.u64 != 0ULL

#### **S_XNOR_B32**

**26**

Calculate bitwise XNOR on two scalar inputs, store the result into a scalar register and set SCC if the result is nonzero.

D0.u32 = ~(S0.u32 ^ S1.u32); SCC = D0.u32 != 0U

94 of 553

12.1. SOP2 Instructions

"AMD Instinct MI300" Instruction Set Architecture

**27**



#### **S_XNOR_B64**

Calculate bitwise XNOR on two scalar inputs, store the result into a scalar register and set SCC if the result is nonzero.

D0.u64 = ~(S0.u64 ^ S1.u64); SCC = D0.u64 != 0ULL

#### **S_LSHL_B32**

**28**

Given a shift count in the second scalar input, calculate the logical shift left of the first scalar input, store the result into a scalar register and set SCC iff the result is nonzero.

D0.u32 = (S0.u32 << S1[4 : 0].u32); SCC = D0.u32 != 0U

**S_LSHL_B64**

**29**

Given a shift count in the second scalar input, calculate the logical shift left of the first scalar input, store the result into a scalar register and set SCC iff the result is nonzero.

D0.u64 = (S0.u64 << S1[5 : 0].u32); SCC = D0.u64 != 0ULL

#### **S_LSHR_B32**

**30**

Given a shift count in the second scalar input, calculate the logical shift right of the first scalar input, store the result into a scalar register and set SCC iff the result is nonzero.

D0.u32 = (S0.u32 >> S1[4 : 0].u32); SCC = D0.u32 != 0U

#### **S_LSHR_B64**

**31**

Given a shift count in the second scalar input, calculate the logical shift right of the first scalar input, store the result into a scalar register and set SCC iff the result is nonzero.

D0.u64 = (S0.u64 >> S1[5 : 0].u32);

95 of 553

12.1. SOP2 Instructions

"AMD Instinct MI300" Instruction Set Architecture



SCC = D0.u64 != 0ULL

#### **S_ASHR_I32**

**32**

Given a shift count in the second scalar input, calculate the arithmetic shift right (preserving sign bit) of the first scalar input, store the result into a scalar register and set SCC iff the result is nonzero.

D0.i32 = 32'I(signext(S0.i32) >> S1[4 : 0].u32); SCC = D0.i32 != 0

#### **S_ASHR_I64**

**33**

Given a shift count in the second scalar input, calculate the arithmetic shift right (preserving sign bit) of the first scalar input, store the result into a scalar register and set SCC iff the result is nonzero.

D0.i64 = (signext(S0.i64) >> S1[5 : 0].u32); SCC = D0.i64 != 0LL

**S_BFM_B32**

**34**

Calculate a bitfield mask given a field offset and size and store the result in a scalar register.

D0.u32 = (((1U << S0[4 : 0].u32) - 1U) << S1[4 : 0].u32)

**S_BFM_B64**

**35**

Calculate a bitfield mask given a field offset and size and store the result in a scalar register.

D0.u64 = (((1ULL << S0[5 : 0].u32) - 1ULL) << S1[5 : 0].u32)

**S_MUL_I32**

**36**

Multiply two signed 32-bit integer inputs and store the result into a scalar register.

D0.i32 = S0.i32 * S1.i32

96 of 553

12.1. SOP2 Instructions

"AMD Instinct MI300" Instruction Set Architecture



**S_BFE_U32**

**37**

Extract an unsigned bitfield from the first input using field offset and size encoded in the second input, store the result into a scalar register and set SCC iff the result is nonzero.

D0.u32 = ((S0.u32 >> S1[4 : 0].u32) & ((1U << S1[22 : 16].u32) - 1U)); SCC = D0.u32 != 0U

**S_BFE_I32**

**38**

Extract a signed bitfield from the first input using field offset and size encoded in the second input, store the result into a scalar register and set SCC iff the result is nonzero.

tmp.i32 = ((S0.i32 >> S1[4 : 0].u32) & ((1 << S1[22 : 16].u32) - 1)); D0.i32 = signext_from_bit(tmp.i32, S1[22 : 16].u32); SCC = D0.i32 != 0

**S_BFE_U64**

**39**

Extract an unsigned bitfield from the first input using field offset and size encoded in the second input, store the result into a scalar register and set SCC iff the result is nonzero.

D0.u64 = ((S0.u64 >> S1[5 : 0].u32) & ((1ULL << S1[22 : 16].u32) - 1ULL)); SCC = D0.u64 != 0ULL

**S_BFE_I64**

**40**

Extract a signed bitfield from the first input using field offset and size encoded in the second input, store the result into a scalar register and set SCC iff the result is nonzero.

tmp.i64 = ((S0.i64 >> S1[5 : 0].u32) & ((1LL << S1[22 : 16].u32) - 1LL)); D0.i64 = signext_from_bit(tmp.i64, S1[22 : 16].u32); SCC = D0.i64 != 0LL

**S_CBRANCH_G_FORK**

**41**

Conditional branch using branch-stack.

97 of 553

12.1. SOP2 Instructions

"AMD Instinct MI300" Instruction Set Architecture



S0 = compare mask (VCC or any SGPR) and S1 = 64-bit byte address of target instruction. See also S_CBRANCH_JOIN.

mask_pass = (S0.u64 & EXEC.u64); mask_fail = (~S0.u64 & EXEC.u64); if mask_pass == EXEC.u64 then PC = 64'I(S1.u64) elsif mask_fail == EXEC.u64 then PC += 4LL elsif bitCount(mask_fail.b64) < bitCount(mask_pass.b64) then EXEC = mask_fail.b64; SGPR[WAVE_MODE.CSP.u32 * 4U].b128 = { S1.u64, mask_pass }; WAVE_MODE.CSP += 3'1U; PC += 4LL else EXEC = mask_pass.b64; SGPR[WAVE_MODE.CSP.u32 * 4U].b128 = { (PC + 4LL), mask_fail }; WAVE_MODE.CSP += 3'1U; PC = 64'I(S1.u64) endif

**S_ABSDIFF_I32**

**42**

Calculate the absolute value of difference between two scalar inputs, store the result into a scalar register and set SCC iff the result is nonzero.

D0.i32 = S0.i32 - S1.i32; if D0.i32 < 0 then D0.i32 = -D0.i32 endif; SCC = D0.i32 != 0

#### **Notes**

Functional examples:

S_ABSDIFF_I32(0x00000002, 0x00000005) => 0x00000003 S_ABSDIFF_I32(0xffffffff, 0x00000000) => 0x00000001 S_ABSDIFF_I32(0x80000000, 0x00000000) => 0x80000000     // Note: result is negative! S_ABSDIFF_I32(0x80000000, 0x00000001) => 0x7fffffff S_ABSDIFF_I32(0x80000000, 0xffffffff) => 0x7fffffff S_ABSDIFF_I32(0x80000000, 0xfffffffe) => 0x7ffffffe

**S_MUL_HI_U32**

**44**

Multiply two unsigned integers and store the high 32 bits of the result into a scalar register.

98 of 553

12.1. SOP2 Instructions

"AMD Instinct MI300" Instruction Set Architecture

**45**



D0.u32 = 32'U((64'U(S0.u32) * 64'U(S1.u32)) >> 32U)

**S_MUL_HI_I32**

Multiply two signed integers and store the high 32 bits of the result into a scalar register.

D0.i32 = 32'I((64'I(S0.i32) * 64'I(S1.i32)) >> 32U)

#### **S_LSHL1_ADD_U32**

**46**

Calculate the logical shift left of the first input by 1, then add the second input, store the result into a scalar register and set SCC iff the summation results in an unsigned overflow.

tmp = (64'U(S0.u32) << 1U) + 64'U(S1.u32); SCC = tmp >= 0x100000000ULL ? 1'1U : 1'0U; // unsigned overflow. D0.u32 = tmp.u32

#### **S_LSHL2_ADD_U32**

**47**

Calculate the logical shift left of the first input by 2, then add the second input, store the result into a scalar register and set SCC iff the summation results in an unsigned overflow.

tmp = (64'U(S0.u32) << 2U) + 64'U(S1.u32); SCC = tmp >= 0x100000000ULL ? 1'1U : 1'0U; // unsigned overflow. D0.u32 = tmp.u32

#### **S_LSHL3_ADD_U32**

**48**

Calculate the logical shift left of the first input by 3, then add the second input, store the result into a scalar register and set SCC iff the summation results in an unsigned overflow.

tmp = (64'U(S0.u32) << 3U) + 64'U(S1.u32); SCC = tmp >= 0x100000000ULL ? 1'1U : 1'0U; // unsigned overflow. D0.u32 = tmp.u32

99 of 553

12.1. SOP2 Instructions

"AMD Instinct MI300" Instruction Set Architecture

**S_LSHL4_ADD_U32**

**49**



Calculate the logical shift left of the first input by 4, then add the second input, store the result into a scalar register and set SCC iff the summation results in an unsigned overflow.

tmp = (64'U(S0.u32) << 4U) + 64'U(S1.u32); SCC = tmp >= 0x100000000ULL ? 1'1U : 1'0U; // unsigned overflow. D0.u32 = tmp.u32

**S_PACK_LL_B32_B16 50**

Pack two 16-bit scalar values into a scalar register.

D0 = { S1[15 : 0].u16, S0[15 : 0].u16 }

**S_PACK_LH_B32_B16 51**

Pack two 16-bit scalar values into a scalar register.

D0 = { S1[31 : 16].u16, S0[15 : 0].u16 }

**S_PACK_HH_B32_B16**

**52**

Pack two 16-bit scalar values into a scalar register.

D0 = { S1[31 : 16].u16, S0[31 : 16].u16 }

100 of 553

12.1. SOP2 Instructions

"AMD Instinct MI300" Instruction Set Architecture

**0**



## **12.2. SOPK Instructions**



Instructions in this format may use a 32-bit literal constant which occurs immediately after the instruction.

**S_MOVK_I32**

Sign extend a literal 16-bit constant and store the result into a scalar register.

D0.i32 = 32'I(signext(S0.i16))

**S_CMOVK_I32 1**

Move the sign extension of a literal 16-bit constant into a scalar register iff SCC is nonzero.

if SCC then D0.i32 = 32'I(signext(S0.i16)) endif

#### **S_CMPK_EQ_I32**

**2**

Set SCC to 1 iff scalar input is equal to the sign extension of a literal 16-bit constant.

SCC = S0.i32 == 32'I(signext(S1.i16))

**S_CMPK_LG_I32 3**

Set SCC to 1 iff scalar input is less than or greater than the sign extension of a literal 16-bit constant.

SCC = S0.i32 != 32'I(signext(S1.i16))

**S_CMPK_GT_I32 4**

Set SCC to 1 iff scalar input is greater than the sign extension of a literal 16-bit constant.

101 of 553

12.2. SOPK Instructions

"AMD Instinct MI300" Instruction Set Architecture

**5**



SCC = S0.i32 > 32'I(signext(S1.i16))

**S_CMPK_GE_I32**

Set SCC to 1 iff scalar input is greater than or equal to the sign extension of a literal 16-bit constant.

SCC = S0.i32 >= 32'I(signext(S1.i16))

**S_CMPK_LT_I32 6**

Set SCC to 1 iff scalar input is less than the sign extension of a literal 16-bit constant.

SCC = S0.i32 < 32'I(signext(S1.i16))

**S_CMPK_LE_I32 7**

Set SCC to 1 iff scalar input is less than or equal to the sign extension of a literal 16-bit constant.

SCC = S0.i32 <= 32'I(signext(S1.i16))

**S_CMPK_EQ_U32 8**

Set SCC to 1 iff scalar input is equal to the zero extension of a literal 16-bit constant.

SCC = S0.u32 == 32'U(S1.u16)

#### **S_CMPK_LG_U32**

**9**

Set SCC to 1 iff scalar input is less than or greater than the zero extension of a literal 16-bit constant.

SCC = S0.u32 != 32'U(S1.u16)

102 of 553

12.2. SOPK Instructions

"AMD Instinct MI300" Instruction Set Architecture

**S_CMPK_GT_U32**

**10**



Set SCC to 1 iff scalar input is greater than the zero extension of a literal 16-bit constant.

SCC = S0.u32 > 32'U(S1.u16)

**S_CMPK_GE_U32 11**

Set SCC to 1 iff scalar input is greater than or equal to the zero extension of a literal 16-bit constant.

SCC = S0.u32 >= 32'U(S1.u16)

**S_CMPK_LT_U32 12**

Set SCC to 1 iff scalar input is less than the zero extension of a literal 16-bit constant.

SCC = S0.u32 < 32'U(S1.u16)

**S_CMPK_LE_U32 13**

Set SCC to 1 iff scalar input is less than or equal to the zero extension of a literal 16-bit constant.

SCC = S0.u32 <= 32'U(S1.u16)

**S_ADDK_I32 14**

Add a scalar input and the sign extension of a literal 16-bit constant, store the result into a scalar register and store the carry-out bit into SCC.

tmp = D0.i32; // Save value to check sign bits for overflow later. D0.i32 = D0.i32 + 32'I(signext(S0.i16)); SCC = ((tmp[31] == S0.i16[15]) && (tmp[31] != D0.i32[31])); // signed overflow.

**S_MULK_I32**

**15**

103 of 553

12.2. SOPK Instructions

"AMD Instinct MI300" Instruction Set Architecture



Multiply a scalar input with the sign extension of a literal 16-bit constant and store the result into a scalar register.

D0.i32 = D0.i32 * 32'I(signext(S0.i16))

**S_CBRANCH_I_FORK 16**

Conditional branch using branch-stack.

S0 = compare mask (VCC or any SGPR), and SIMM16 = signed DWORD branch offset relative to next instruction. See also S_CBRANCH_JOIN.

// Initial setup. mask_pass = (S0.u64 & EXEC.u64); mask_fail = (~S0.u64 & EXEC.u64); target_addr = PC + signext(SIMM16.i32 * 4) + 4LL; // Decide where to jump to. if mask_pass == EXEC.u64 then PC = target_addr elsif mask_fail == EXEC.u64 then PC += 4LL elsif bitCount(mask_fail.b64) < bitCount(mask_pass.b64) then EXEC = mask_fail.b64; SGPR[WAVE_MODE.CSP.u32 * 4U].b128 = { target_addr, mask_pass }; WAVE_MODE.CSP += 3'1U; PC += 4LL else EXEC = mask_pass.b64; SGPR[WAVE_MODE.CSP.u32 * 4U].b128 = { (PC + 4LL), mask_fail }; WAVE_MODE.CSP += 3'1U; PC = target_addr endif

#### **S_GETREG_B32**

**17**

Read some or all of a hardware register into the LSBs of destination.

hwRegId = SIMM16.u16[5 : 0]; offset = SIMM16.u16[10 : 6]; size = SIMM16.u16[15 : 11].u32 + 1U; // logical size is in range 1:32 value = HW_REGISTERS[hwRegId]; D0.u32 = 32'U(32'I(value >> offset.u32) & ((1 << size) - 1))

**S_SETREG_B32**

**18**

104 of 553

12.2. SOPK Instructions

"AMD Instinct MI300" Instruction Set Architecture



Write some or all of the LSBs of source argument into a hardware register.

hwRegId = SIMM16.u16[5 : 0]; offset = SIMM16.u16[10 : 6]; size = SIMM16.u16[15 : 11].u32 + 1U; // logical size is in range 1:32 mask = (1 << size) - 1; mask = (mask << offset.u32); mask = (mask & HwRegWriteMask(hwRegId, WAVE_STATUS.PRIV)); // Mask of bits that can be modified value = ((S0.u32 << offset.u32) & mask.u32); value = (value | 32'U(HW_REGISTERS[hwRegId].i32 & ~mask)); HW_REGISTERS[hwRegId] = value.b32; // Side-effects may trigger here if certain bits are modified

#### **S_SETREG_IMM32_B32**

**20**

Write some or all of the LSBs of a 32-bit literal constant into a hardware register; this instruction requires a 32bit literal constant.

hwRegId = SIMM16.u16[5 : 0]; offset = SIMM16.u16[10 : 6]; size = SIMM16.u16[15 : 11].u32 + 1U; // logical size is in range 1:32 mask = (1 << size) - 1; mask = (mask << offset.u32); mask = (mask & HwRegWriteMask(hwRegId, WAVE_STATUS.PRIV)); // Mask of bits that can be modified value = ((SIMM32.u32 << offset.u32) & mask.u32); value = (value | 32'U(HW_REGISTERS[hwRegId].i32 & ~mask)); HW_REGISTERS[hwRegId] = value.b32; // Side-effects may trigger here if certain bits are modified

#### **S_CALL_B64**

**21**

Store the address of the next instruction to a scalar register and then jump to a constant offset relative to the current PC.

The literal argument is a signed DWORD offset relative to the PC of the next instruction. The byte address of the instruction immediately _following_ this instruction is saved to the destination.

D0.i64 = PC + 4LL; PC = PC + signext(SIMM16.i16 * 16'4) + 4LL

**Notes**

105 of 553

12.2. SOPK Instructions

"AMD Instinct MI300" Instruction Set Architecture



This implements a short subroutine call where the return address (the next instruction after the S_CALL_B64) is saved to D. Long calls should consider S_SWAPPC_B64 instead.

This instruction must be 4 bytes.

106 of 553

12.2. SOPK Instructions

"AMD Instinct MI300" Instruction Set Architecture



## **12.3. SOP1 Instructions**



Instructions in this format may use a 32-bit literal constant which occurs immediately after the instruction.

**S_MOV_B32 0**

Move scalar input into a scalar register.

D0.b32 = S0.b32

**S_MOV_B64**

**1**

Move scalar input into a scalar register.

D0.b64 = S0.b64

**S_CMOV_B32**

**2**

Move scalar input into a scalar register iff SCC is nonzero.

if SCC then D0.b32 = S0.b32 endif

#### **S_CMOV_B64**

**3**

Move scalar input into a scalar register iff SCC is nonzero.

if SCC then D0.b64 = S0.b64 endif

**S_NOT_B32 4**

Calculate bitwise negation on a scalar input, store the result into a scalar register and set SCC iff the result is nonzero.

107 of 553

12.3. SOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture

**5**



D0.u32 = ~S0.u32; SCC = D0.u32 != 0U

#### **S_NOT_B64**

Calculate bitwise negation on a scalar input, store the result into a scalar register and set SCC iff the result is nonzero.

D0.u64 = ~S0.u64; SCC = D0.u64 != 0ULL

#### **S_WQM_B32**

**6**

Given an active pixel mask in a scalar input, calculate whole quad mode mask for that input, store the result into a scalar register and set SCC iff the result is nonzero.

In whole quad mode, if any pixel in a quad is active then all pixels of the quad are marked active.

tmp = 0U; declare i : 6'U; for i in 6'0U : 6'31U do tmp[i] = S0.u32[i & 6'60U +: 6'4U] != 0U endfor; D0.u32 = tmp; SCC = D0.u32 != 0U

#### **S_WQM_B64**

**7**

Given an active pixel mask in a scalar input, calculate whole quad mode mask for that input, store the result into a scalar register and set SCC iff the result is nonzero.

In whole quad mode, if any pixel in a quad is active then all pixels of the quad are marked active.

tmp = 0ULL; declare i : 6'U; for i in 6'0U : 6'63U do tmp[i] = S0.u64[i & 6'60U +: 6'4U] != 0ULL endfor; D0.u64 = tmp; SCC = D0.u64 != 0ULL

108 of 553

12.3. SOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture

**S_BREV_B32**

**8**



Reverse the order of bits in a scalar input and store the result into a scalar register.

D0.u32[31 : 0] = S0.u32[0 : 31]

**S_BREV_B64 9**

Reverse the order of bits in a scalar input and store the result into a scalar register.

D0.u64[63 : 0] = S0.u64[0 : 63]

#### **S_BCNT0_I32_B32**

**10**

Count the number of "0" bits in a scalar input, store the result into a scalar register and set SCC iff the result is nonzero.

tmp = 0; for i in 0 : 31 do tmp += S0.u32[i] == 1'0U ? 1 : 0 endfor; D0.i32 = tmp; SCC = D0.u32 != 0U

#### **Notes**

Functional examples:

S_BCNT0_I32_B32(0x00000000) => 32 S_BCNT0_I32_B32(0xcccccccc) => 16 S_BCNT0_I32_B32(0xffffffff) => 0

#### **S_BCNT0_I32_B64**

**11**

Count the number of "0" bits in a scalar input, store the result into a scalar register and set SCC iff the result is nonzero.

tmp = 0; for i in 0 : 63 do tmp += S0.u64[i] == 1'0U ? 1 : 0 endfor;

109 of 553

12.3. SOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture

**12**



D0.i32 = tmp; SCC = D0.u64 != 0ULL

#### **S_BCNT1_I32_B32**

Count the number of "1" bits in a scalar input, store the result into a scalar register and set SCC iff the result is nonzero.

tmp = 0; for i in 0 : 31 do tmp += S0.u32[i] == 1'1U ? 1 : 0 endfor; D0.i32 = tmp; SCC = D0.u32 != 0U

#### **Notes**

Functional examples:

S_BCNT1_I32_B32(0x00000000) => 0 S_BCNT1_I32_B32(0xcccccccc) => 16 S_BCNT1_I32_B32(0xffffffff) => 32

#### **S_BCNT1_I32_B64**

**13**

Count the number of "1" bits in a scalar input, store the result into a scalar register and set SCC iff the result is nonzero.

tmp = 0; for i in 0 : 63 do tmp += S0.u64[i] == 1'1U ? 1 : 0 endfor; D0.i32 = tmp; SCC = D0.u64 != 0ULL

#### **S_FF0_I32_B32**

**14**

Count the number of trailing "1" bits before the first "0" in a scalar input and store the result into a scalar register. Store -1 if there are no "0" bits in the input.

tmp = -1; // Set if no zeros are found

110 of 553

12.3. SOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture



for i in 0 : 31 do // Search from LSB if S0.u32[i] == 1'0U then tmp = i; break endif endfor; D0.i32 = tmp

#### **Notes**

Functional examples:

S_FF0_I32_B32(0xaaaaaaaa) => 0 S_FF0_I32_B32(0x55555555) => 1 S_FF0_I32_B32(0x00000000) => 0 S_FF0_I32_B32(0xffffffff) => 0xffffffff S_FF0_I32_B32(0xfffeffff) => 16

#### **S_FF0_I32_B64**

**15**

Count the number of trailing "1" bits before the first "0" in a scalar input and store the result into a scalar register. Store -1 if there are no "0" bits in the input.

tmp = -1; // Set if no zeros are found for i in 0 : 63 do // Search from LSB if S0.u64[i] == 1'0U then tmp = i; break endif endfor; D0.i32 = tmp

#### **S_FF1_I32_B32**

**16**

Count the number of trailing "0" bits before the first "1" in a scalar input and store the result into a scalar register. Store -1 if there are no "1" bits in the input.

tmp = -1; // Set if no ones are found for i in 0 : 31 do // Search from LSB if S0.u32[i] == 1'1U then tmp = i; break

111 of 553

12.3. SOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture



endif endfor; D0.i32 = tmp

#### **Notes**

Functional examples:

S_FF1_I32_B32(0xaaaaaaaa) => 1 S_FF1_I32_B32(0x55555555) => 0 S_FF1_I32_B32(0x00000000) => 0xffffffff S_FF1_I32_B32(0xffffffff) => 0 S_FF1_I32_B32(0x00010000) => 16

#### **S_FF1_I32_B64**

**17**

Count the number of trailing "0" bits before the first "1" in a scalar input and store the result into a scalar register. Store -1 if there are no "1" bits in the input.

tmp = -1; // Set if no ones are found for i in 0 : 63 do // Search from LSB if S0.u64[i] == 1'1U then tmp = i; break endif endfor; D0.i32 = tmp

#### **S_FLBIT_I32_B32**

**18**

Count the number of leading "0" bits before the first "1" in a scalar input and store the result into a scalar register. Store -1 if there are no "1" bits.

tmp = -1; // Set if no ones are found for i in 0 : 31 do // Search from MSB if S0.u32[31 - i] == 1'1U then tmp = i; break endif endfor; D0.i32 = tmp

112 of 553

12.3. SOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture



#### **Notes**

Functional examples:

S_FLBIT_I32_B32(0x00000000) => 0xffffffff S_FLBIT_I32_B32(0x0000cccc) => 16 S_FLBIT_I32_B32(0xffff3333) => 0 S_FLBIT_I32_B32(0x7fffffff) => 1 S_FLBIT_I32_B32(0x80000000) => 0 S_FLBIT_I32_B32(0xffffffff) => 0

#### **S_FLBIT_I32_B64**

**19**

Count the number of leading "0" bits before the first "1" in a scalar input and store the result into a scalar register. Store -1 if there are no "1" bits.

tmp = -1; // Set if no ones are found for i in 0 : 63 do // Search from MSB if S0.u64[63 - i] == 1'1U then tmp = i; break endif endfor; D0.i32 = tmp

#### **S_FLBIT_I32**

**20**

Count the number of leading bits that are the same as the sign bit of a scalar input and store the result into a scalar register. Store -1 if all input bits are the same.

tmp = -1; // Set if all bits are the same for i in 1 : 31 do // Search from MSB if S0.u32[31 - i] != S0.u32[31] then tmp = i; break endif endfor; D0.i32 = tmp

#### **Notes**

Functional examples:

113 of 553

12.3. SOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture



S_FLBIT_I32(0x00000000) => 0xffffffff S_FLBIT_I32(0x0000cccc) => 16 S_FLBIT_I32(0xffff3333) => 16 S_FLBIT_I32(0x7fffffff) => 1 S_FLBIT_I32(0x80000000) => 1 S_FLBIT_I32(0xffffffff) => 0xffffffff

**S_FLBIT_I32_I64 21**

Count the number of leading bits that are the same as the sign bit of a scalar input and store the result into a scalar register. Store -1 if all input bits are the same.

tmp = -1; // Set if all bits are the same for i in 1 : 63 do // Search from MSB if S0.u64[63 - i] != S0.u64[63] then tmp = i; break endif endfor; D0.i32 = tmp

**S_SEXT_I32_I8 22**

Sign extend a signed 8 bit scalar input to 32 bits and store the result into a scalar register.

D0.i32 = 32'I(signext(S0.i8))

**S_SEXT_I32_I16 23**

Sign extend a signed 16 bit scalar input to 32 bits and store the result into a scalar register.

D0.i32 = 32'I(signext(S0.i16))

**S_BITSET0_B32**

**24**

Given a bit offset in a scalar input, set the indicated bit in the destination scalar register to 0.

114 of 553

12.3. SOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture



D0.u32[S0.u32[4 : 0]] = 1'0U

#### **S_BITSET0_B64**

**25**

Given a bit offset in a scalar input, set the indicated bit in the destination scalar register to 0.

D0.u64[S0.u32[5 : 0]] = 1'0U

#### **S_BITSET1_B32**

**26**

Given a bit offset in a scalar input, set the indicated bit in the destination scalar register to 1.

D0.u32[S0.u32[4 : 0]] = 1'1U

#### **S_BITSET1_B64**

**27**

Given a bit offset in a scalar input, set the indicated bit in the destination scalar register to 1.

D0.u64[S0.u32[5 : 0]] = 1'1U

#### **S_GETPC_B64**

**28**

Store the address of the next instruction to a scalar register.

The byte address of the instruction immediately _following_ this instruction is saved to the destination.

D0.i64 = PC + 4LL

#### **Notes**

This instruction must be 4 bytes.

**S_SETPC_B64**

**29**

Jump to an address specified in a scalar register.

115 of 553

12.3. SOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture



The argument is a byte address of the instruction to jump to.

PC = S0.i64

#### **S_SWAPPC_B64**

**30**

Store the address of the next instruction to a scalar register and then jump to an address specified in the scalar input.

The argument is a byte address of the instruction to jump to. The byte address of the instruction immediately _following_ this instruction is saved to the destination.

jump_addr = S0.i64; D0.i64 = PC + 4LL; PC = jump_addr.i64

#### **Notes**

This instruction must be 4 bytes.

#### **S_RFE_B64**

**31**

Return from the exception handler. Clear the wave's PRIV bit and then jump to an address specified by the scalar input.

The argument is a byte address of the instruction to jump to; this address is likely derived from the state passed into the trap handler.

This instruction may only be used within a trap handler.

WAVE_STATUS.PRIV = 1'0U; PC = S0.i64

#### **S_AND_SAVEEXEC_B64**

**32**

Calculate bitwise AND on the scalar input and the EXEC mask, store the calculated result into the EXEC mask, set SCC iff the calculated result is nonzero and store the _original_ value of the EXEC mask into the scalar destination register.

The original EXEC mask is saved to the destination SGPRs before the bitwise operation is performed.

saveexec = EXEC.u64;

116 of 553

12.3. SOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture

**33**



EXEC.u64 = (S0.u64 & EXEC.u64); D0.u64 = saveexec.u64; SCC = EXEC.u64 != 0ULL

#### **S_OR_SAVEEXEC_B64**

Calculate bitwise OR on the scalar input and the EXEC mask, store the calculated result into the EXEC mask, set SCC iff the calculated result is nonzero and store the _original_ value of the EXEC mask into the scalar destination register.

The original EXEC mask is saved to the destination SGPRs before the bitwise operation is performed.

saveexec = EXEC.u64; EXEC.u64 = (S0.u64 | EXEC.u64); D0.u64 = saveexec.u64; SCC = EXEC.u64 != 0ULL

#### **S_XOR_SAVEEXEC_B64**

**34**

Calculate bitwise XOR on the scalar input and the EXEC mask, store the calculated result into the EXEC mask, set SCC iff the calculated result is nonzero and store the _original_ value of the EXEC mask into the scalar destination register.

The original EXEC mask is saved to the destination SGPRs before the bitwise operation is performed.

saveexec = EXEC.u64; EXEC.u64 = (S0.u64 ^ EXEC.u64); D0.u64 = saveexec.u64; SCC = EXEC.u64 != 0ULL

#### **S_ANDN2_SAVEEXEC_B64**

**35**

Calculate bitwise AND on the scalar input and the negation of the EXEC mask, store the calculated result into the EXEC mask, set SCC iff the calculated result is nonzero and store the _original_ value of the EXEC mask into the scalar destination register.

The original EXEC mask is saved to the destination SGPRs before the bitwise operation is performed.

saveexec = EXEC.u64; EXEC.u64 = (S0.u64 & ~EXEC.u64); D0.u64 = saveexec.u64; SCC = EXEC.u64 != 0ULL

117 of 553

12.3. SOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture

**36**



#### **S_ORN2_SAVEEXEC_B64**

Calculate bitwise OR on the scalar input and the negation of the EXEC mask, store the calculated result into the EXEC mask, set SCC iff the calculated result is nonzero and store the _original_ value of the EXEC mask into the scalar destination register.

The original EXEC mask is saved to the destination SGPRs before the bitwise operation is performed.

saveexec = EXEC.u64; EXEC.u64 = (S0.u64 | ~EXEC.u64); D0.u64 = saveexec.u64; SCC = EXEC.u64 != 0ULL

#### **S_NAND_SAVEEXEC_B64**

**37**

Calculate bitwise NAND on the scalar input and the EXEC mask, store the calculated result into the EXEC mask, set SCC iff the calculated result is nonzero and store the _original_ value of the EXEC mask into the scalar destination register.

saveexec = EXEC.u64; EXEC.u64 = ~(S0.u64 & EXEC.u64); D0.u64 = saveexec.u64; SCC = EXEC.u64 != 0ULL

#### **S_NOR_SAVEEXEC_B64**

**38**

Calculate bitwise NOR on the scalar input and the EXEC mask, store the calculated result into the EXEC mask, set SCC iff the calculated result is nonzero and store the _original_ value of the EXEC mask into the scalar destination register.

saveexec = EXEC.u64; EXEC.u64 = ~(S0.u64 | EXEC.u64); D0.u64 = saveexec.u64; SCC = EXEC.u64 != 0ULL

#### **S_XNOR_SAVEEXEC_B64**

**39**

Calculate bitwise XNOR on the scalar input and the EXEC mask, store the calculated result into the EXEC mask, set SCC iff the calculated result is nonzero and store the _original_ value of the EXEC mask into the scalar destination register.

118 of 553

12.3. SOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture

**40**



saveexec = EXEC.u64; EXEC.u64 = ~(S0.u64 ^ EXEC.u64); D0.u64 = saveexec.u64; SCC = EXEC.u64 != 0ULL

#### **S_QUADMASK_B32**

Reduce a pixel mask from the scalar input into a quad mask, store the result in a scalar register and set SCC iff the result is nonzero.

tmp = 0U; for i in 0 : 7 do tmp[i] = S0.u32[i * 4 +: 4] != 0U endfor; D0.u32 = tmp; SCC = D0.u32 != 0U

#### **Notes**

To perform the inverse operation see S_BITREPLICATE_B64_B32.

#### **S_QUADMASK_B64**

**41**

Reduce a pixel mask from the scalar input into a quad mask, store the result in a scalar register and set SCC iff the result is nonzero.

tmp = 0ULL; for i in 0 : 15 do tmp[i] = S0.u64[i * 4 +: 4] != 0ULL endfor; D0.u64 = tmp; SCC = D0.u64 != 0ULL

#### **Notes**

To perform the inverse operation see S_BITREPLICATE_B64_B32.

#### **S_MOVRELS_B32**

**42**

Move data from a relatively-indexed scalar register into another scalar register.

addr = SRC0.u32; // Raw value from instruction

119 of 553

12.3. SOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture

**43**



addr += M0.u32[31 : 0]; D0.b32 = SGPR[addr].b32

#### **Notes**

Example: The following instruction sequence performs the move s5 <= s17:

s_mov_b32 m0, 10 s_movrels_b32 s5, s7

#### **S_MOVRELS_B64**

Move data from a relatively-indexed scalar register into another scalar register.

The index in M0.u and the operand address in SRC0.u must be even for this operation.

addr = SRC0.u32; // Raw value from instruction addr += M0.u32[31 : 0]; D0.b64 = SGPR[addr].b64

**S_MOVRELD_B32 44**

Move data from a scalar input into a relatively-indexed scalar register.

addr = DST.u32; // Raw value from instruction addr += M0.u32[31 : 0]; SGPR[addr].b32 = S0.b32

#### **Notes**

Example: The following instruction sequence performs the move s15 <= s7:

s_mov_b32 m0, 10 s_movreld_b32 s5, s7

#### **S_MOVRELD_B64**

**45**

Move data from a scalar input into a relatively-indexed scalar register.

120 of 553

12.3. SOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture



The index in M0.u and the operand address in DST.u must be even for this operation.

addr = DST.u32; // Raw value from instruction addr += M0.u32[31 : 0]; SGPR[addr].b64 = S0.b64

#### **S_CBRANCH_JOIN**

**46**

Conditional branch join point (end of conditional branch block).

S0 is saved CSP value. See S_CBRANCH_G_FORK and S_CBRANCH_I_FORK for related instructions.

saved_csp = S0.u32; if WAVE_MODE.CSP.u32 == saved_csp then PC += 4LL; // Second time to JOIN: continue with program. else WAVE_MODE.CSP -= 3'1U; // First time to JOIN; jump to other FORK path. { PC, EXEC } = SGPR[WAVE_MODE.CSP.u32 * 4U].b128; // Read 128 bits from 4 consecutive SGPRs. endif

**S_ABS_I32**

**48**

Compute the absolute value of a scalar input, store the result into a scalar register and set SCC iff the result is nonzero.

D0.i32 = S0.i32 < 0 ? -S0.i32 : S0.i32; SCC = D0.i32 != 0

#### **Notes**

Functional examples:

S_ABS_I32(0x00000001) => 0x00000001 S_ABS_I32(0x7fffffff) => 0x7fffffff S_ABS_I32(0x80000000) => 0x80000000     // Note this is negative! S_ABS_I32(0x80000001) => 0x7fffffff S_ABS_I32(0x80000002) => 0x7ffffffe S_ABS_I32(0xffffffff) => 0x00000001

121 of 553

12.3. SOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture

**50**



#### **S_SET_GPR_IDX_IDX**

Set the index used in vector GPR indexing.

S_SET_GPR_IDX_ON, S_SET_GPR_IDX_OFF, S_SET_GPR_IDX_MODE and S_SET_GPR_IDX_IDX are related instructions.

M0[7 : 0] = S0.u32[7 : 0].b8

#### **S_ANDN1_SAVEEXEC_B64**

**51**

Calculate bitwise AND on the EXEC mask and the negation of the scalar input, store the calculated result into the EXEC mask, set SCC iff the calculated result is nonzero and store the _original_ value of the EXEC mask into the scalar destination register.

The original EXEC mask is saved to the destination SGPRs before the bitwise operation is performed.

saveexec = EXEC.u64; EXEC.u64 = (~S0.u64 & EXEC.u64); D0.u64 = saveexec.u64; SCC = EXEC.u64 != 0ULL

#### **S_ORN1_SAVEEXEC_B64**

**52**

Calculate bitwise OR on the EXEC mask and the negation of the scalar input, store the calculated result into the EXEC mask, set SCC iff the calculated result is nonzero and store the _original_ value of the EXEC mask into the scalar destination register.

The original EXEC mask is saved to the destination SGPRs before the bitwise operation is performed.

saveexec = EXEC.u64; EXEC.u64 = (~S0.u64 | EXEC.u64); D0.u64 = saveexec.u64; SCC = EXEC.u64 != 0ULL

#### **S_ANDN1_WREXEC_B64**

**53**

Calculate bitwise AND on the EXEC mask and the negation of the scalar input, store the calculated result into the EXEC mask and also into the scalar destination register, and set SCC iff the calculated result is nonzero.

Unlike the SAVEEXEC series of opcodes, the value written to destination SGPRs is the result of the bitwise-op result. EXEC and the destination SGPRs have the same value at the end of this instruction. This instruction is intended to help accelerate waterfalling.

122 of 553

12.3. SOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture

**54**



EXEC.u64 = (~S0.u64 & EXEC.u64); D0.u64 = EXEC.u64; SCC = EXEC.u64 != 0ULL

#### **S_ANDN2_WREXEC_B64**

Calculate bitwise AND on the scalar input and the negation of the EXEC mask, store the calculated result into the EXEC mask and also into the scalar destination register, and set SCC iff the calculated result is nonzero.

Unlike the SAVEEXEC series of opcodes, the value written to destination SGPRs is the result of the bitwise-op result. EXEC and the destination SGPRs have the same value at the end of this instruction. This instruction is intended to help accelerate waterfalling.

EXEC.u64 = (S0.u64 & ~EXEC.u64); D0.u64 = EXEC.u64; SCC = EXEC.u64 != 0ULL

#### **Notes**

In particular, the following sequence of waterfall code is optimized by using a WREXEC instead of two separate scalar ops:

// V0 holds the index value per lane // save exec mask for restore at the end s_mov_b64 s2, exec // exec mask of remaining (unprocessed) threads s_mov_b64 s4, exec loop: // get the index value for the first active lane v_readfirstlane_b32  s0, v0 // find all other lanes with same index value v_cmpx_eq s0, v0 <OP>        // do the operation using the current EXEC mask. S0 holds the index. // mask out thread that was just executed // s_andn2_b64  s4, s4, exec // s_mov_b64    exec, s4 s_andn2_wrexec_b64 s4, s4     // replaces above 2 ops // repeat until EXEC==0 s_cbranch_scc1  loop s_mov_b64    exec, s2

#### **S_BITREPLICATE_B64_B32**

**55**

Substitute each bit of a 32 bit scalar input with two instances of itself and store the result into a 64 bit scalar register.

123 of 553

12.3. SOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture



tmp = S0.u32; for i in 0 : 31 do D0.u64[i * 2] = tmp[i]; D0.u64[i * 2 + 1] = tmp[i] endfor

#### **Notes**

This opcode can be used to convert a quad mask into a pixel mask; given quad mask in s0, the following sequence produces a pixel mask in s2:

s_bitreplicate_b64 s2, s0 s_bitreplicate_b64 s2, s2

To perform the inverse operation see S_QUADMASK_B64.

124 of 553

12.3. SOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture



## **12.4. SOPC Instructions**



Instructions in this format may use a 32-bit literal constant which occurs immediately after the instruction.

**S_CMP_EQ_I32**

**0**

Set SCC to 1 iff the first scalar input is equal to the second scalar input.

SCC = S0.i32 == S1.i32

#### **Notes**

Note that S_CMP_EQ_I32 and S_CMP_EQ_U32 are identical opcodes, but both are provided for symmetry.

**S_CMP_LG_I32 1**

Set SCC to 1 iff the first scalar input is less than or greater than the second scalar input.

SCC = S0.i32 <> S1.i32

#### **Notes**

Note that S_CMP_LG_I32 and S_CMP_LG_U32 are identical opcodes, but both are provided for symmetry.

**S_CMP_GT_I32 2**

Set SCC to 1 iff the first scalar input is greater than the second scalar input.

SCC = S0.i32 > S1.i32

**S_CMP_GE_I32 3**

Set SCC to 1 iff the first scalar input is greater than or equal to the second scalar input.

SCC = S0.i32 >= S1.i32

125 of 553

12.4. SOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture

**S_CMP_LT_I32 4**



Set SCC to 1 iff the first scalar input is less than the second scalar input.

SCC = S0.i32 < S1.i32

**S_CMP_LE_I32 5**

Set SCC to 1 iff the first scalar input is less than or equal to the second scalar input.

SCC = S0.i32 <= S1.i32

**S_CMP_EQ_U32 6**

Set SCC to 1 iff the first scalar input is equal to the second scalar input.

SCC = S0.u32 == S1.u32

#### **Notes**

Note that S_CMP_EQ_I32 and S_CMP_EQ_U32 are identical opcodes, but both are provided for symmetry.

**S_CMP_LG_U32 7**

Set SCC to 1 iff the first scalar input is less than or greater than the second scalar input.

SCC = S0.u32 <> S1.u32

#### **Notes**

Note that S_CMP_LG_I32 and S_CMP_LG_U32 are identical opcodes, but both are provided for symmetry.

**S_CMP_GT_U32 8**

Set SCC to 1 iff the first scalar input is greater than the second scalar input.

SCC = S0.u32 > S1.u32

126 of 553

12.4. SOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture

**9**



**S_CMP_GE_U32**

Set SCC to 1 iff the first scalar input is greater than or equal to the second scalar input.

SCC = S0.u32 >= S1.u32

**S_CMP_LT_U32**

**10**

Set SCC to 1 iff the first scalar input is less than the second scalar input.

SCC = S0.u32 < S1.u32

**S_CMP_LE_U32 11**

Set SCC to 1 iff the first scalar input is less than or equal to the second scalar input.

SCC = S0.u32 <= S1.u32

**S_BITCMP0_B32 12**

Extract a bit from the first scalar input based on an index in the second scalar input, and set SCC to 1 iff the extracted bit is equal to 0.

SCC = S0.u32[S1.u32[4 : 0]] == 1'0U

**S_BITCMP1_B32 13**

Extract a bit from the first scalar input based on an index in the second scalar input, and set SCC to 1 iff the extracted bit is equal to 1.

SCC = S0.u32[S1.u32[4 : 0]] == 1'1U

**S_BITCMP0_B64**

**14**

127 of 553

12.4. SOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture

**15**



Extract a bit from the first scalar input based on an index in the second scalar input, and set SCC to 1 iff the extracted bit is equal to 0.

SCC = S0.u64[S1.u32[5 : 0]] == 1'0U

#### **S_BITCMP1_B64**

Extract a bit from the first scalar input based on an index in the second scalar input, and set SCC to 1 iff the extracted bit is equal to 1.

SCC = S0.u64[S1.u32[5 : 0]] == 1'1U

#### **S_SETVSKIP**

**16**

Enables or disables VSKIP mode.

When VSKIP is enabled, no VOP*/M*BUF/MIMG/DS/FLAT instructions are issued. Note that VSKIPped memory instructions do not manipulate the waitcnt counters; as a result, if there are outstanding memory requests the shader may want to issue S_WAITCNT 0 prior to enabling VSKIP, otherwise the shader must be careful not to count VSKIPped instructions in waitcnt calculations.

VSKIP = S0.u32[S1.u32[4 : 0]]

#### **Notes**

Functional examples:

s_setvskip 1, 0     // Enable vskip mode. s_setvskip 0, 0     // Disable vskip mode.

#### **S_SET_GPR_IDX_ON**

**17**

#### Enable GPR indexing mode.

Vector operations after this perform relative GPR addressing based on the contents of M0. The index is specified in the SRC0 operand. The raw bits of the SRC1 field are read and used to set the enable bits. S1[0] = VSRC0_REL, S1[1] = VSRC1_REL, S1[2] = VSRC2_REL and S1[3] = VDST_REL.

S_SET_GPR_IDX_ON, S_SET_GPR_IDX_OFF, S_SET_GPR_IDX_MODE and S_SET_GPR_IDX_IDX are related instructions.

128 of 553

12.4. SOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture



WAVE_MODE.GPR_IDX_EN = 1'1U; M0[7 : 0] = S0.u32[7 : 0].b8; M0[15 : 12] = SRC1.u32[3 : 0].b4; // this is the direct content of raw S1 field // Remaining bits of M0 are unmodified.

**S_CMP_EQ_U64 18**

Set SCC to 1 iff the first scalar input is equal to the second scalar input.

SCC = S0.u64 == S1.u64 **S_CMP_LG_U64 19**

Set SCC to 1 iff the first scalar input is less than or greater than the second scalar input.

SCC = S0.u64 <> S1.u64

129 of 553

12.4. SOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture



## **12.5. SOPP Instructions**



**S_NOP 0**

Do nothing. Delay issue of next instruction by a small, fixed amount.

Insert 0..15 wait states based on SIMM16[3:0]. 0x0 means the next instruction can issue on the next clock, 0xf means the next instruction can issue 16 clocks later.

for i in 0U : SIMM16.u16[3 : 0].u32 do nop() endfor

#### **Notes**

Examples:

s_nop 0         // Wait 1 cycle. s_nop 0xf       // Wait 16 cycles.

**S_ENDPGM 1**

End of program; terminate wavefront.

The hardware implicitly executes S_WAITCNT 0 before executing this instruction. See S_ENDPGM_SAVED for the context-switch version of this instruction.

**S_BRANCH 2**

Jump to a constant offset relative to the current PC.

The literal argument is a signed DWORD offset relative to the PC of the next instruction.

PC = PC + signext(SIMM16.i16 * 16'4) + 4LL; // short jump.

#### **Notes**

For a long jump or an indirect jump use S_SETPC_B64.

Examples:

130 of 553

12.5. SOPP Instructions

"AMD Instinct MI300" Instruction Set Architecture



s_branch label    // Set SIMM16 = +4 = 0x0004 s_nop 0    // 4 bytes label: s_nop 0    // 4 bytes s_branch label    // Set SIMM16 = -8 = 0xfff8

#### **S_WAKEUP**

**3**

Allow a wave to 'ping' all the other waves in its threadgroup to force them to wake up early from an S_SLEEP instruction.

The ping is ignored if the waves are not sleeping. This allows for efficient polling on a memory location. The waves which are polling can sit in a long S_SLEEP between memory reads, but the wave which writes the value can tell them all to wake up early now that the data is available. This method is also safe from races since any waves that miss the ping resume when they complete their S_SLEEP.

If the wave executing S_WAKEUP is in a threadgroup (in_tg set), then it wakes up all waves associated with the same threadgroup ID. Otherwise, S_WAKEUP is treated as an S_NOP.

**S_CBRANCH_SCC0 4**

If SCC is 0 then jump to a constant offset relative to the current PC.

The literal argument is a signed DWORD offset relative to the PC of the next instruction.

if SCC == 1'0U then PC = PC + signext(SIMM16.i16 * 16'4) + 4LL else PC = PC + 4LL endif

**S_CBRANCH_SCC1 5**

If SCC is 1 then jump to a constant offset relative to the current PC.

The literal argument is a signed DWORD offset relative to the PC of the next instruction.

if SCC == 1'1U then PC = PC + signext(SIMM16.i16 * 16'4) + 4LL else PC = PC + 4LL endif

131 of 553

12.5. SOPP Instructions

"AMD Instinct MI300" Instruction Set Architecture

**6**



#### **S_CBRANCH_VCCZ**

If VCCZ is 1 then jump to a constant offset relative to the current PC.

The literal argument is a signed DWORD offset relative to the PC of the next instruction.

if VCCZ.u1 == 1'1U then PC = PC + signext(SIMM16.i16 * 16'4) + 4LL else PC = PC + 4LL endif

**S_CBRANCH_VCCNZ 7**

If VCCZ is 0 then jump to a constant offset relative to the current PC.

The literal argument is a signed DWORD offset relative to the PC of the next instruction.

if VCCZ.u1 == 1'0U then PC = PC + signext(SIMM16.i16 * 16'4) + 4LL else PC = PC + 4LL endif

**S_CBRANCH_EXECZ 8**

If EXECZ is 1 then jump to a constant offset relative to the current PC.

The literal argument is a signed DWORD offset relative to the PC of the next instruction.

if EXECZ.u1 == 1'1U then PC = PC + signext(SIMM16.i16 * 16'4) + 4LL else PC = PC + 4LL endif

**S_CBRANCH_EXECNZ 9**

If EXECZ is 0 then jump to a constant offset relative to the current PC.

The literal argument is a signed DWORD offset relative to the PC of the next instruction.

if EXECZ.u1 == 1'0U then

132 of 553

12.5. SOPP Instructions

"AMD Instinct MI300" Instruction Set Architecture

**10**



PC = PC + signext(SIMM16.i16 * 16'4) + 4LL else PC = PC + 4LL endif

#### **S_BARRIER**

#### Synchronize waves within a threadgroup.

If not all waves of the threadgroup have been created yet, waits for entire group before proceeding. If some waves in the threadgroup have already terminated, this waits on only the surviving waves. Barriers are legal inside trap handlers.

Barrier instructions do not wait for any counters to go to zero before issuing. If the barrier is being used to protect an outstanding memory operation use the appropriate S_WAITCNT instruction before the barrier.

#### **S_SETKILL**

**11**

Kill this wave if the least significant bit of the immediate constant is 1.

Used primarily for debugging kill wave host command behavior.

**S_WAITCNT 12**

Wait for the counts of outstanding local data share, vector memory and export instructions to be at or below the specified levels.

SIMM16[3:0] = vmcount (vector memory operations) lower bits [3:0],

SIMM16[6:4] = export/mem-write-data count,

SIMM16[11:8] = LGKMcnt (scalar-mem/GDS/LDS count),

SIMM16[15:14] = vmcount (vector memory operations) upper bits [5:4].

#### **S_SETHALT**

**13**

Set or clear the HALT status bit.

133 of 553

12.5. SOPP Instructions

"AMD Instinct MI300" Instruction Set Architecture



Set HALT bit to value of SIMM16[0]; 1 = halt, 0 = clear HALT bit. The halt flag is ignored while PRIV == 1 (inside trap handlers) but the shader halts after the handler returns if HALT is still set at that time.

**S_SLEEP 14**

Cause a wave to sleep for up to ~8000 clocks.

The wave sleeps for (64*(SIMM16[6:0]-1) .. 64*SIMM16[6:0]) clocks. The exact amount of delay is approximate. Compare with S_NOP. When SIMM16[6:0] is zero then no sleep occurs.

#### **Notes**

Examples:

s_sleep 0       // Wait for 0 clocks. s_sleep 1       // Wait for 1-64 clocks. s_sleep 2       // Wait for 65-128 clocks.

**S_SETPRIO 15**

Change wave user priority.

User settable wave priority is set to SIMM16[1:0]. 0 = lowest, 3 = highest. The overall wave priority is {SPIPrio[1:0], UserPrio[1:0], WaveAge[3:0]}.

|**S_SENDMSG**<br>**16**|
|---|



Send a message upstream to graphics control hardware.

SIMM16[9:0] contains the message type.

#### **Notes**

**S_SENDMSGHALT 17**

Send a message to upstream control hardware and then HALT the wavefront; see S_SENDMSG for details.

**S_TRAP 18**

Enter the trap handler.

This instruction may be generated internally as well in response to a host trap (HT = 1) or an exception. TrapID

134 of 553

12.5. SOPP Instructions

"AMD Instinct MI300" Instruction Set Architecture

**S_ICACHE_INV 19**



0 is reserved for hardware use and should not be used in a shader-generated trap.

TrapID = SIMM16.u16[7 : 0]; "Wait for all instructions to complete"; // PC passed into trap handler points to S_TRAP itself, // *not* to the next instruction. { TTMP[1], TTMP[0] } = { 3'0, PCRewind[3 : 0], HT[0], TrapID[7 : 0], PC[47 : 0] }; PC = TBA.i64; // trap base address WAVE_STATUS.PRIV = 1'1U

Invalidate entire first level instruction cache.

There must be 16 separate S_NOP instructions or a jump/branch instruction after this instruction to ensure the internal instruction buffers are also invalidated.

|**S_INCPERFLEVEL**|**20**|
|---|---|
|Increment performance counter specified in SIMM16[3:0] by 1.||
|**S_DECPERFLEVEL**|**21**|
|Decrement performance counter specified in SIMM16[3:0] by 1.||
|**S_TTRACEDATA**|**22**|
|Send M0 as user data to the thread trace stream.||



|**S_CBRANCH_CDBGSYS**<br>**23**|
|---|



If the system debug flag is set then jump to a constant offset relative to the current PC.

The literal argument is a signed DWORD offset relative to the PC of the next instruction.

if WAVE_STATUS.COND_DBG_SYS.u32 != 0U then PC = PC + signext(SIMM16.i16 * 16'4) + 4LL else PC = PC + 4LL endif

135 of 553

12.5. SOPP Instructions

"AMD Instinct MI300" Instruction Set Architecture

**24**



#### **S_CBRANCH_CDBGUSER**

If the user debug flag is set then jump to a constant offset relative to the current PC.

The literal argument is a signed DWORD offset relative to the PC of the next instruction.

if WAVE_STATUS.COND_DBG_USER.u32 != 0U then PC = PC + signext(SIMM16.i16 * 16'4) + 4LL else PC = PC + 4LL endif

#### **S_CBRANCH_CDBGSYS_OR_USER**

**25**

If either the system debug flag or the user debug flag is set then jump to a constant offset relative to the current PC.

The literal argument is a signed DWORD offset relative to the PC of the next instruction.

if (WAVE_STATUS.COND_DBG_SYS || WAVE_STATUS.COND_DBG_USER) then PC = PC + signext(SIMM16.i16 * 16'4) + 4LL else PC = PC + 4LL endif

#### **S_CBRANCH_CDBGSYS_AND_USER**

**26**

If both the system debug flag and the user debug flag are set then jump to a constant offset relative to the current PC.

The literal argument is a signed DWORD offset relative to the PC of the next instruction.

if (WAVE_STATUS.COND_DBG_SYS && WAVE_STATUS.COND_DBG_USER) then PC = PC + signext(SIMM16.i16 * 16'4) + 4LL else PC = PC + 4LL endif

**S_ENDPGM_SAVED**

**27**

End of program; signal that a wave has been saved by the context-switch trap handler and terminate wavefront.

136 of 553

12.5. SOPP Instructions

"AMD Instinct MI300" Instruction Set Architecture

**28**



The hardware implicitly executes S_WAITCNT 0 before executing this instruction.

See S_ENDPGM for additional variants.

#### **S_SET_GPR_IDX_OFF**

Clear GPR indexing mode.

Vector operations after this do not perform relative GPR addressing regardless of the contents of M0. This instruction does not modify M0.

S_SET_GPR_IDX_ON, S_SET_GPR_IDX_OFF, S_SET_GPR_IDX_MODE and S_SET_GPR_IDX_IDX are related instructions.

WAVE_MODE.GPR_IDX_EN = 1'0U

#### **S_SET_GPR_IDX_MODE**

**29**

Modify the mode used for vector GPR indexing.

The raw contents of the source field are read and used to set the enable bits. SIMM16[0] = VSRC0_REL, SIMM16[1] = VSRC1_REL, SIMM16[2] = VSRC2_REL and SIMM16[3] = VDST_REL.

S_SET_GPR_IDX_ON, S_SET_GPR_IDX_OFF, S_SET_GPR_IDX_MODE and S_SET_GPR_IDX_IDX are related instructions.

M0[15 : 12] = SIMM16.u16[3 : 0].b4

137 of 553

12.5. SOPP Instructions

"AMD Instinct MI300" Instruction Set Architecture



### **12.5.1. Send Message**

The S_SENDMSG instruction encodes the message type in M0, and can also send data from the SIMM16 field and in some cases from EXEC.

|**Message**|**SIMM16[3:0]**|**SIMM16[6:4]**|**Payload**|
|---|---|---|---|
|none|0|-|illegal|
|Interrupt|1|-|M0[23:0] carries data payload|
|Save wave|4|-|used in context switching|
|Stall Wave Gen|5|-|stop new wave generation|
|Halt Waves|6|-|halt all running waves of this vmid|
|Get Doorbell ID|10|-|Returns doorbell into EXEC, with the doorbell physical address in bits<br>[12:3].|



## **12.6. SMEM Instructions**



**S_LOAD_DWORD 0**

Load 32 bits of data from the scalar memory into a scalar register.

addr = CalcScalarGlobalAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); SDATA[31 : 0] = MEM[addr].b32

#### **Notes**

If the offset is specified as an SGPR, the SGPR contains an UNSIGNED BYTE offset (the 2 LSBs are ignored).

If the offset is specified as an immediate 21-bit constant, the constant is a SIGNED BYTE offset.

**S_LOAD_DWORDX2 1**

Load 64 bits of data from the scalar memory into a scalar register.

addr = CalcScalarGlobalAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); SDATA[31 : 0] = MEM[addr].b32; SDATA[63 : 32] = MEM[addr + 4U].b32

#### **Notes**

If the offset is specified as an SGPR, the SGPR contains an UNSIGNED BYTE offset (the 2 LSBs are ignored).

138 of 553

12.6. SMEM Instructions

"AMD Instinct MI300" Instruction Set Architecture



If the offset is specified as an immediate 21-bit constant, the constant is a SIGNED BYTE offset.

#### **S_LOAD_DWORDX4**

**2**

Load 128 bits of data from the scalar memory into a scalar register.

addr = CalcScalarGlobalAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); SDATA[31 : 0] = MEM[addr].b32; SDATA[63 : 32] = MEM[addr + 4U].b32; SDATA[95 : 64] = MEM[addr + 8U].b32; SDATA[127 : 96] = MEM[addr + 12U].b32

#### **Notes**

If the offset is specified as an SGPR, the SGPR contains an UNSIGNED BYTE offset (the 2 LSBs are ignored).

If the offset is specified as an immediate 21-bit constant, the constant is a SIGNED BYTE offset.

**S_LOAD_DWORDX8 3**

Load 256 bits of data from the scalar memory into a scalar register.

addr = CalcScalarGlobalAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); SDATA[31 : 0] = MEM[addr].b32; SDATA[63 : 32] = MEM[addr + 4U].b32; SDATA[95 : 64] = MEM[addr + 8U].b32; SDATA[127 : 96] = MEM[addr + 12U].b32; SDATA[159 : 128] = MEM[addr + 16U].b32; SDATA[191 : 160] = MEM[addr + 20U].b32; SDATA[223 : 192] = MEM[addr + 24U].b32; SDATA[255 : 224] = MEM[addr + 28U].b32

#### **Notes**

If the offset is specified as an SGPR, the SGPR contains an UNSIGNED BYTE offset (the 2 LSBs are ignored).

If the offset is specified as an immediate 21-bit constant, the constant is a SIGNED BYTE offset.

#### **S_LOAD_DWORDX16**

**4**

Load 512 bits of data from the scalar memory into a scalar register.

addr = CalcScalarGlobalAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); SDATA[31 : 0] = MEM[addr].b32; SDATA[63 : 32] = MEM[addr + 4U].b32;

139 of 553

12.6. SMEM Instructions

"AMD Instinct MI300" Instruction Set Architecture



SDATA[95 : 64] = MEM[addr + 8U].b32; SDATA[127 : 96] = MEM[addr + 12U].b32; SDATA[159 : 128] = MEM[addr + 16U].b32; SDATA[191 : 160] = MEM[addr + 20U].b32; SDATA[223 : 192] = MEM[addr + 24U].b32; SDATA[255 : 224] = MEM[addr + 28U].b32; SDATA[287 : 256] = MEM[addr + 32U].b32; SDATA[319 : 288] = MEM[addr + 36U].b32; SDATA[351 : 320] = MEM[addr + 40U].b32; SDATA[383 : 352] = MEM[addr + 44U].b32; SDATA[415 : 384] = MEM[addr + 48U].b32; SDATA[447 : 416] = MEM[addr + 52U].b32; SDATA[479 : 448] = MEM[addr + 56U].b32; SDATA[511 : 480] = MEM[addr + 60U].b32

#### **Notes**

If the offset is specified as an SGPR, the SGPR contains an UNSIGNED BYTE offset (the 2 LSBs are ignored).

If the offset is specified as an immediate 21-bit constant, the constant is a SIGNED BYTE offset.

**S_SCRATCH_LOAD_DWORD**

**5**

Load 32 bits of data from the scalar scratch aperture into a scalar register.

addr = CalcScalarScratchAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); SDATA[31 : 0] = MEM[addr].b32

#### **Notes**

If the offset is specified as an SGPR, the SGPR contains an UNSIGNED 64-byte offset, consistent with other scratch operations.

If the offset is specified as an immediate 21-bit constant, the constant is a SIGNED BYTE offset.

**S_SCRATCH_LOAD_DWORDX2**

**6**

Load 64 bits of data from the scalar scratch aperture into a scalar register.

addr = CalcScalarScratchAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); SDATA[31 : 0] = MEM[addr].b32; SDATA[63 : 32] = MEM[addr + 4U].b32

#### **Notes**

If the offset is specified as an SGPR, the SGPR contains an UNSIGNED 64-byte offset, consistent with other scratch operations.

140 of 553

12.6. SMEM Instructions

"AMD Instinct MI300" Instruction Set Architecture



If the offset is specified as an immediate 21-bit constant, the constant is a SIGNED BYTE offset.

#### **S_SCRATCH_LOAD_DWORDX4**

**7**

Load 128 bits of data from the scalar scratch aperture into a scalar register.

addr = CalcScalarScratchAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); SDATA[31 : 0] = MEM[addr].b32; SDATA[63 : 32] = MEM[addr + 4U].b32; SDATA[95 : 64] = MEM[addr + 8U].b32; SDATA[127 : 96] = MEM[addr + 12U].b32

#### **Notes**

If the offset is specified as an SGPR, the SGPR contains an UNSIGNED 64-byte offset, consistent with other scratch operations.

If the offset is specified as an immediate 21-bit constant, the constant is a SIGNED BYTE offset.

**S_BUFFER_LOAD_DWORD 8**

Load 32 bits of data from a scalar buffer surface into a scalar register.

addr = CalcScalarBufferAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); SDATA[31 : 0] = MEM[addr].b32

#### **Notes**

If the offset is specified as an SGPR, the SGPR contains an UNSIGNED BYTE offset (the 2 LSBs are ignored).

If the offset is specified as an immediate 21-bit constant, the constant is a SIGNED BYTE offset.

**S_BUFFER_LOAD_DWORDX2 9**

Load 64 bits of data from a scalar buffer surface into a scalar register.

addr = CalcScalarBufferAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); SDATA[31 : 0] = MEM[addr].b32; SDATA[63 : 32] = MEM[addr + 4U].b32

#### **Notes**

If the offset is specified as an SGPR, the SGPR contains an UNSIGNED BYTE offset (the 2 LSBs are ignored).

141 of 553

12.6. SMEM Instructions

"AMD Instinct MI300" Instruction Set Architecture



If the offset is specified as an immediate 21-bit constant, the constant is a SIGNED BYTE offset.

#### **S_BUFFER_LOAD_DWORDX4**

**10**

Load 128 bits of data from a scalar buffer surface into a scalar register.

addr = CalcScalarBufferAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); SDATA[31 : 0] = MEM[addr].b32; SDATA[63 : 32] = MEM[addr + 4U].b32; SDATA[95 : 64] = MEM[addr + 8U].b32; SDATA[127 : 96] = MEM[addr + 12U].b32

#### **Notes**

If the offset is specified as an SGPR, the SGPR contains an UNSIGNED BYTE offset (the 2 LSBs are ignored).

If the offset is specified as an immediate 21-bit constant, the constant is a SIGNED BYTE offset.

#### **S_BUFFER_LOAD_DWORDX8**

**11**

Load 256 bits of data from a scalar buffer surface into a scalar register.

addr = CalcScalarBufferAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); SDATA[31 : 0] = MEM[addr].b32; SDATA[63 : 32] = MEM[addr + 4U].b32; SDATA[95 : 64] = MEM[addr + 8U].b32; SDATA[127 : 96] = MEM[addr + 12U].b32; SDATA[159 : 128] = MEM[addr + 16U].b32; SDATA[191 : 160] = MEM[addr + 20U].b32; SDATA[223 : 192] = MEM[addr + 24U].b32; SDATA[255 : 224] = MEM[addr + 28U].b32

#### **Notes**

If the offset is specified as an SGPR, the SGPR contains an UNSIGNED BYTE offset (the 2 LSBs are ignored).

If the offset is specified as an immediate 21-bit constant, the constant is a SIGNED BYTE offset.

#### **S_BUFFER_LOAD_DWORDX16**

**12**

Load 512 bits of data from a scalar buffer surface into a scalar register.

addr = CalcScalarBufferAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); SDATA[31 : 0] = MEM[addr].b32; SDATA[63 : 32] = MEM[addr + 4U].b32;

142 of 553

12.6. SMEM Instructions

"AMD Instinct MI300" Instruction Set Architecture



SDATA[95 : 64] = MEM[addr + 8U].b32; SDATA[127 : 96] = MEM[addr + 12U].b32; SDATA[159 : 128] = MEM[addr + 16U].b32; SDATA[191 : 160] = MEM[addr + 20U].b32; SDATA[223 : 192] = MEM[addr + 24U].b32; SDATA[255 : 224] = MEM[addr + 28U].b32; SDATA[287 : 256] = MEM[addr + 32U].b32; SDATA[319 : 288] = MEM[addr + 36U].b32; SDATA[351 : 320] = MEM[addr + 40U].b32; SDATA[383 : 352] = MEM[addr + 44U].b32; SDATA[415 : 384] = MEM[addr + 48U].b32; SDATA[447 : 416] = MEM[addr + 52U].b32; SDATA[479 : 448] = MEM[addr + 56U].b32; SDATA[511 : 480] = MEM[addr + 60U].b32

#### **Notes**

If the offset is specified as an SGPR, the SGPR contains an UNSIGNED BYTE offset (the 2 LSBs are ignored).

If the offset is specified as an immediate 21-bit constant, the constant is a SIGNED BYTE offset.

#### **S_STORE_DWORD**

**16**

Store 32 bits of data from a scalar register into the scalar memory.

addr = CalcScalarGlobalAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); MEM[addr].b32 = SDATA[31 : 0]

#### **Notes**

If the offset is specified as an SGPR, the SGPR contains an UNSIGNED BYTE offset (the 2 LSBs are ignored).

If the offset is specified as an immediate 21-bit constant, the constant is a SIGNED BYTE offset.

**S_STORE_DWORDX2**

**17**

Store 64 bits of data from a scalar register into the scalar memory.

addr = CalcScalarGlobalAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); MEM[addr].b32 = SDATA[31 : 0]; MEM[addr + 4U].b32 = SDATA[63 : 32]

#### **Notes**

If the offset is specified as an SGPR, the SGPR contains an UNSIGNED BYTE offset (the 2 LSBs are ignored).

If the offset is specified as an immediate 21-bit constant, the constant is a SIGNED BYTE offset.

143 of 553

12.6. SMEM Instructions

"AMD Instinct MI300" Instruction Set Architecture

**18**



#### **S_STORE_DWORDX4**

Store 128 bits of data from a scalar register into the scalar memory.

addr = CalcScalarGlobalAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); MEM[addr].b32 = SDATA[31 : 0]; MEM[addr + 4U].b32 = SDATA[63 : 32]; MEM[addr + 8U].b32 = SDATA[95 : 64]; MEM[addr + 12U].b32 = SDATA[127 : 96]

#### **Notes**

If the offset is specified as an SGPR, the SGPR contains an UNSIGNED BYTE offset (the 2 LSBs are ignored).

If the offset is specified as an immediate 21-bit constant, the constant is a SIGNED BYTE offset.

**S_SCRATCH_STORE_DWORD**

**21**

Store 32 bits of data from a scalar register into the scalar scratch aperture.

addr = CalcScalarScratchAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); MEM[addr].b32 = SDATA[31 : 0]

#### **Notes**

If the offset is specified as an SGPR, the SGPR contains an UNSIGNED 64-byte offset, consistent with other scratch operations.

If the offset is specified as an immediate 21-bit constant, the constant is a SIGNED BYTE offset.

**S_SCRATCH_STORE_DWORDX2**

**22**

Store 64 bits of data from a scalar register into the scalar scratch aperture.

addr = CalcScalarScratchAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); MEM[addr].b32 = SDATA[31 : 0]; MEM[addr + 4U].b32 = SDATA[63 : 32]

#### **Notes**

If the offset is specified as an SGPR, the SGPR contains an UNSIGNED 64-byte offset, consistent with other scratch operations.

144 of 553

12.6. SMEM Instructions

"AMD Instinct MI300" Instruction Set Architecture



If the offset is specified as an immediate 21-bit constant, the constant is a SIGNED BYTE offset.

#### **S_SCRATCH_STORE_DWORDX4**

**23**

Store 128 bits of data from a scalar register into the scalar scratch aperture.

addr = CalcScalarScratchAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); MEM[addr].b32 = SDATA[31 : 0]; MEM[addr + 4U].b32 = SDATA[63 : 32]; MEM[addr + 8U].b32 = SDATA[95 : 64]; MEM[addr + 12U].b32 = SDATA[127 : 96]

#### **Notes**

If the offset is specified as an SGPR, the SGPR contains an UNSIGNED 64-byte offset, consistent with other scratch operations.

If the offset is specified as an immediate 21-bit constant, the constant is a SIGNED BYTE offset.

**S_BUFFER_STORE_DWORD**

**24**

Store 32 bits of data from a scalar register into a scalar buffer surface.

addr = CalcScalarBufferAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); MEM[addr].b32 = SDATA[31 : 0]

#### **Notes**

If the offset is specified as an SGPR, the SGPR contains an UNSIGNED BYTE offset (the 2 LSBs are ignored).

If the offset is specified as an immediate 21-bit constant, the constant is a SIGNED BYTE offset.

#### **S_BUFFER_STORE_DWORDX2**

**25**

Store 64 bits of data from a scalar register into a scalar buffer surface.

addr = CalcScalarBufferAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); MEM[addr].b32 = SDATA[31 : 0]; MEM[addr + 4U].b32 = SDATA[63 : 32]

#### **Notes**

If the offset is specified as an SGPR, the SGPR contains an UNSIGNED BYTE offset (the 2 LSBs are ignored).

145 of 553

12.6. SMEM Instructions

"AMD Instinct MI300" Instruction Set Architecture

**S_BUFFER_STORE_DWORDX4 26**



If the offset is specified as an immediate 21-bit constant, the constant is a SIGNED BYTE offset.

Store 128 bits of data from a scalar register into a scalar buffer surface.

addr = CalcScalarBufferAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); MEM[addr].b32 = SDATA[31 : 0]; MEM[addr + 4U].b32 = SDATA[63 : 32]; MEM[addr + 8U].b32 = SDATA[95 : 64]; MEM[addr + 12U].b32 = SDATA[127 : 96]

#### **Notes**

If the offset is specified as an SGPR, the SGPR contains an UNSIGNED BYTE offset (the 2 LSBs are ignored).

If the offset is specified as an immediate 21-bit constant, the constant is a SIGNED BYTE offset.

|**S_DCACHE_INV**<br>**32**|
|---|



Invalidate the scalar (L0) data cache.

|**S_DCACHE_WB**|**33**|
|---|---|
|Write back dirty data in the scalar (L0) data cache.||
|**S_DCACHE_INV_VOL**|**34**|
|Invalidate the scalar (L0) data cache volatile lines.||
|**S_DCACHE_WB_VOL**|**35**|
|Write back dirty data in the scalar (L0) data cache volatile lines.||
|**S_MEMTIME**|**36**|
|Return current 64-bit timestamp.||



146 of 553

12.6. SMEM Instructions

"AMD Instinct MI300" Instruction Set Architecture

**37**



#### **S_MEMREALTIME**

Return current 64-bit RTC.

#### **S_DCACHE_DISCARD**

**40**

Discard one dirty scalar (L0) data cache line. A cache line is 64 bytes.

Typically, dirty cachelines (one which have been written by the shader) are written back to memory, but this instruction allows the shader to invalidate and not write back cachelines which it has previously written. This is a performance optimization to be used when the shader knows it no longer needs that data.

Address is calculated the same as S_STORE_DWORD, except the 6 LSBs are ignored to get the 64 byte aligned address. LGKM count is incremented by 1 for this opcode.

#### **S_DCACHE_DISCARD_X2**

**41**

Discard two consecutive dirty scalar (L0) data cache lines. A cache line is 64 bytes.

Typically, dirty cachelines (one which have been written by the shader) are written back to memory, but this instruction allows the shader to invalidate and not write back cachelines which it has previously written. This is a performance optimization to be used when the shader knows it no longer needs that data.

Address is calculated the same as S_STORE_DWORD, except the 6 LSBs are ignored to get the 64 byte aligned address. LGKM count is incremented by 2 for this opcode.

#### **S_BUFFER_ATOMIC_SWAP**

**64**

Swap an unsigned 32-bit integer value in the data register with a location in a scalar buffer surface.

addr = CalcScalarBufferAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].b32; MEM[addr].b32 = DATA.b32; RETURN_DATA.b32 = tmp

#### **S_BUFFER_ATOMIC_CMPSWAP**

**65**

Compare two unsigned 32-bit integer values stored in the data comparison register and a location in a scalar buffer surface. Modify the memory location with a value in the data source register iff the comparison is equal.

addr = CalcScalarBufferAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].u32; src = DATA[31 : 0].u32;

147 of 553

12.6. SMEM Instructions

"AMD Instinct MI300" Instruction Set Architecture

**66**



cmp = DATA[63 : 32].u32; MEM[addr].u32 = tmp == cmp ? src : tmp; RETURN_DATA.u32 = tmp

#### **S_BUFFER_ATOMIC_ADD**

Add two unsigned 32-bit integer values stored in the data register and a location in a scalar buffer surface.

addr = CalcScalarBufferAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].u32; MEM[addr].u32 += DATA.u32; RETURN_DATA.u32 = tmp

#### **S_BUFFER_ATOMIC_SUB**

**67**

Subtract an unsigned 32-bit integer value stored in the data register from a value stored in a location in a scalar buffer surface.

addr = CalcScalarBufferAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].u32; MEM[addr].u32 -= DATA.u32; RETURN_DATA.u32 = tmp

#### **S_BUFFER_ATOMIC_SMIN**

**68**

Select the minimum of two signed 32-bit integer inputs, given two values stored in the data register and a location in a scalar buffer surface. Update the scalar buffer with the selected value.

addr = CalcScalarBufferAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].i32; src = DATA.i32; MEM[addr].i32 = src < tmp ? src : tmp; RETURN_DATA.i32 = tmp

#### **S_BUFFER_ATOMIC_UMIN**

**69**

Select the minimum of two unsigned 32-bit integer inputs, given two values stored in the data register and a location in a scalar buffer surface. Update the scalar buffer with the selected value.

addr = CalcScalarBufferAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32);

148 of 553

12.6. SMEM Instructions

"AMD Instinct MI300" Instruction Set Architecture



tmp = MEM[addr].u32; src = DATA.u32; MEM[addr].u32 = src < tmp ? src : tmp; RETURN_DATA.u32 = tmp

#### **S_BUFFER_ATOMIC_SMAX**

**70**

Select the maximum of two signed 32-bit integer inputs, given two values stored in the data register and a location in a scalar buffer surface. Update the scalar buffer with the selected value.

addr = CalcScalarBufferAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].i32; src = DATA.i32; MEM[addr].i32 = src >= tmp ? src : tmp; RETURN_DATA.i32 = tmp

**S_BUFFER_ATOMIC_UMAX 71**

Select the maximum of two unsigned 32-bit integer inputs, given two values stored in the data register and a location in a scalar buffer surface. Update the scalar buffer with the selected value.

addr = CalcScalarBufferAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].u32; src = DATA.u32; MEM[addr].u32 = src >= tmp ? src : tmp; RETURN_DATA.u32 = tmp

#### **S_BUFFER_ATOMIC_AND**

**72**

Calculate bitwise AND given two unsigned 32-bit integer values stored in the data register and a location in a scalar buffer surface.

addr = CalcScalarBufferAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].b32; MEM[addr].b32 = (tmp & DATA.b32); RETURN_DATA.b32 = tmp

**S_BUFFER_ATOMIC_OR**

**73**

Calculate bitwise OR given two unsigned 32-bit integer values stored in the data register and a location in a scalar buffer surface.

149 of 553

12.6. SMEM Instructions

"AMD Instinct MI300" Instruction Set Architecture



addr = CalcScalarBufferAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].b32; MEM[addr].b32 = (tmp | DATA.b32); RETURN_DATA.b32 = tmp

#### **S_BUFFER_ATOMIC_XOR**

**74**

Calculate bitwise XOR given two unsigned 32-bit integer values stored in the data register and a location in a scalar buffer surface.

addr = CalcScalarBufferAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].b32; MEM[addr].b32 = (tmp ^ DATA.b32); RETURN_DATA.b32 = tmp

#### **S_BUFFER_ATOMIC_INC**

**75**

Increment an unsigned 32-bit integer value from a location in a scalar buffer surface with wraparound to 0 if the value exceeds a value in the data register.

addr = CalcScalarBufferAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].u32; src = DATA.u32; MEM[addr].u32 = tmp >= src ? 0U : tmp + 1U; RETURN_DATA.u32 = tmp

**S_BUFFER_ATOMIC_DEC 76**

Decrement an unsigned 32-bit integer value from a location in a scalar buffer surface with wraparound to a value in the data register if the decrement yields a negative value.

addr = CalcScalarBufferAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].u32; src = DATA.u32; MEM[addr].u32 = ((tmp == 0U) || (tmp > src)) ? src : tmp - 1U; RETURN_DATA.u32 = tmp

#### **S_BUFFER_ATOMIC_SWAP_X2**

**96**

Swap an unsigned 64-bit integer value in the data register with a location in a scalar buffer surface.

150 of 553

12.6. SMEM Instructions

"AMD Instinct MI300" Instruction Set Architecture



addr = CalcScalarBufferAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].b64; MEM[addr].b64 = DATA.b64; RETURN_DATA.b64 = tmp

#### **S_BUFFER_ATOMIC_CMPSWAP_X2**

**97**

Compare two unsigned 64-bit integer values stored in the data comparison register and a location in a scalar buffer surface. Modify the memory location with a value in the data source register iff the comparison is equal.

addr = CalcScalarBufferAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].u64; src = DATA[63 : 0].u64; cmp = DATA[127 : 64].u64; MEM[addr].u64 = tmp == cmp ? src : tmp; RETURN_DATA.u64 = tmp

#### **S_BUFFER_ATOMIC_ADD_X2**

**98**

Add two unsigned 64-bit integer values stored in the data register and a location in a scalar buffer surface.

addr = CalcScalarBufferAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].u64; MEM[addr].u64 += DATA.u64; RETURN_DATA.u64 = tmp

#### **S_BUFFER_ATOMIC_SUB_X2**

**99**

Subtract an unsigned 64-bit integer value stored in the data register from a value stored in a location in a scalar buffer surface.

addr = CalcScalarBufferAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].u64; MEM[addr].u64 -= DATA.u64; RETURN_DATA.u64 = tmp

#### **S_BUFFER_ATOMIC_SMIN_X2**

**100**

Select the minimum of two signed 64-bit integer inputs, given two values stored in the data register and a location in a scalar buffer surface. Update the scalar buffer with the selected value.

151 of 553

12.6. SMEM Instructions

"AMD Instinct MI300" Instruction Set Architecture



addr = CalcScalarBufferAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].i64; src = DATA.i64; MEM[addr].i64 = src < tmp ? src : tmp; RETURN_DATA.i64 = tmp

#### **S_BUFFER_ATOMIC_UMIN_X2**

**101**

Select the minimum of two unsigned 64-bit integer inputs, given two values stored in the data register and a location in a scalar buffer surface. Update the scalar buffer with the selected value.

addr = CalcScalarBufferAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].u64; src = DATA.u64; MEM[addr].u64 = src < tmp ? src : tmp; RETURN_DATA.u64 = tmp

#### **S_BUFFER_ATOMIC_SMAX_X2**

**102**

Select the maximum of two signed 64-bit integer inputs, given two values stored in the data register and a location in a scalar buffer surface. Update the scalar buffer with the selected value.

addr = CalcScalarBufferAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].i64; src = DATA.i64; MEM[addr].i64 = src >= tmp ? src : tmp; RETURN_DATA.i64 = tmp

#### **S_BUFFER_ATOMIC_UMAX_X2**

**103**

Select the maximum of two unsigned 64-bit integer inputs, given two values stored in the data register and a location in a scalar buffer surface. Update the scalar buffer with the selected value.

addr = CalcScalarBufferAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].u64; src = DATA.u64; MEM[addr].u64 = src >= tmp ? src : tmp; RETURN_DATA.u64 = tmp

**S_BUFFER_ATOMIC_AND_X2**

**104**

152 of 553

12.6. SMEM Instructions

"AMD Instinct MI300" Instruction Set Architecture



Calculate bitwise AND given two unsigned 64-bit integer values stored in the data register and a location in a scalar buffer surface.

addr = CalcScalarBufferAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].b64; MEM[addr].b64 = (tmp & DATA.b64); RETURN_DATA.b64 = tmp

**S_BUFFER_ATOMIC_OR_X2**

**105**

Calculate bitwise OR given two unsigned 64-bit integer values stored in the data register and a location in a scalar buffer surface.

addr = CalcScalarBufferAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].b64; MEM[addr].b64 = (tmp | DATA.b64); RETURN_DATA.b64 = tmp

**S_BUFFER_ATOMIC_XOR_X2**

**106**

Calculate bitwise XOR given two unsigned 64-bit integer values stored in the data register and a location in a scalar buffer surface.

addr = CalcScalarBufferAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].b64; MEM[addr].b64 = (tmp ^ DATA.b64); RETURN_DATA.b64 = tmp

**S_BUFFER_ATOMIC_INC_X2**

**107**

Increment an unsigned 64-bit integer value from a location in a scalar buffer surface with wraparound to 0 if the value exceeds a value in the data register.

addr = CalcScalarBufferAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].u64; src = DATA.u64; MEM[addr].u64 = tmp >= src ? 0ULL : tmp + 1ULL; RETURN_DATA.u64 = tmp

**S_BUFFER_ATOMIC_DEC_X2**

**108**

153 of 553

12.6. SMEM Instructions

"AMD Instinct MI300" Instruction Set Architecture



Decrement an unsigned 64-bit integer value from a location in a scalar buffer surface with wraparound to a value in the data register if the decrement yields a negative value.

addr = CalcScalarBufferAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].u64; src = DATA.u64; MEM[addr].u64 = ((tmp == 0ULL) || (tmp > src)) ? src : tmp - 1ULL; RETURN_DATA.u64 = tmp

#### **S_ATOMIC_SWAP**

**128**

Swap an unsigned 32-bit integer value in the data register with a location in the scalar memory.

addr = CalcScalarGlobalAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].b32; MEM[addr].b32 = DATA.b32; RETURN_DATA.b32 = tmp

#### **S_ATOMIC_CMPSWAP**

**129**

Compare two unsigned 32-bit integer values stored in the data comparison register and a location in the scalar memory. Modify the memory location with a value in the data source register iff the comparison is equal.

addr = CalcScalarGlobalAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].u32; src = DATA[31 : 0].u32; cmp = DATA[63 : 32].u32; MEM[addr].u32 = tmp == cmp ? src : tmp; RETURN_DATA.u32 = tmp

#### **S_ATOMIC_ADD**

**130**

Add two unsigned 32-bit integer values stored in the data register and a location in the scalar memory.

addr = CalcScalarGlobalAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].u32; MEM[addr].u32 += DATA.u32; RETURN_DATA.u32 = tmp

**S_ATOMIC_SUB**

**131**

154 of 553

12.6. SMEM Instructions

"AMD Instinct MI300" Instruction Set Architecture



Subtract an unsigned 32-bit integer value stored in the data register from a value stored in a location in the scalar memory.

addr = CalcScalarGlobalAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].u32; MEM[addr].u32 -= DATA.u32; RETURN_DATA.u32 = tmp

#### **S_ATOMIC_SMIN**

**132**

Select the minimum of two signed 32-bit integer inputs, given two values stored in the data register and a location in the scalar memory. Update the scalar memory with the selected value.

addr = CalcScalarGlobalAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].i32; src = DATA.i32; MEM[addr].i32 = src < tmp ? src : tmp; RETURN_DATA.i32 = tmp

#### **S_ATOMIC_UMIN**

**133**

Select the minimum of two unsigned 32-bit integer inputs, given two values stored in the data register and a location in the scalar memory. Update the scalar memory with the selected value.

addr = CalcScalarGlobalAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].u32; src = DATA.u32; MEM[addr].u32 = src < tmp ? src : tmp; RETURN_DATA.u32 = tmp

#### **S_ATOMIC_SMAX**

**134**

Select the maximum of two signed 32-bit integer inputs, given two values stored in the data register and a location in the scalar memory. Update the scalar memory with the selected value.

addr = CalcScalarGlobalAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].i32; src = DATA.i32; MEM[addr].i32 = src >= tmp ? src : tmp; RETURN_DATA.i32 = tmp

155 of 553

12.6. SMEM Instructions

"AMD Instinct MI300" Instruction Set Architecture

**135**



#### **S_ATOMIC_UMAX**

Select the maximum of two unsigned 32-bit integer inputs, given two values stored in the data register and a location in the scalar memory. Update the scalar memory with the selected value.

addr = CalcScalarGlobalAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].u32; src = DATA.u32; MEM[addr].u32 = src >= tmp ? src : tmp; RETURN_DATA.u32 = tmp

#### **S_ATOMIC_AND**

**136**

Calculate bitwise AND given two unsigned 32-bit integer values stored in the data register and a location in the scalar memory.

addr = CalcScalarGlobalAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].b32; MEM[addr].b32 = (tmp & DATA.b32); RETURN_DATA.b32 = tmp

#### **S_ATOMIC_OR**

**137**

Calculate bitwise OR given two unsigned 32-bit integer values stored in the data register and a location in the scalar memory.

addr = CalcScalarGlobalAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].b32; MEM[addr].b32 = (tmp | DATA.b32); RETURN_DATA.b32 = tmp

#### **S_ATOMIC_XOR**

**138**

Calculate bitwise XOR given two unsigned 32-bit integer values stored in the data register and a location in the scalar memory.

addr = CalcScalarGlobalAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].b32; MEM[addr].b32 = (tmp ^ DATA.b32); RETURN_DATA.b32 = tmp

156 of 553

12.6. SMEM Instructions

"AMD Instinct MI300" Instruction Set Architecture

**139**



#### **S_ATOMIC_INC**

Increment an unsigned 32-bit integer value from a location in the scalar memory with wraparound to 0 if the value exceeds a value in the data register.

addr = CalcScalarGlobalAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].u32; src = DATA.u32; MEM[addr].u32 = tmp >= src ? 0U : tmp + 1U; RETURN_DATA.u32 = tmp

#### **S_ATOMIC_DEC**

**140**

Decrement an unsigned 32-bit integer value from a location in the scalar memory with wraparound to a value in the data register if the decrement yields a negative value.

addr = CalcScalarGlobalAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].u32; src = DATA.u32; MEM[addr].u32 = ((tmp == 0U) || (tmp > src)) ? src : tmp - 1U; RETURN_DATA.u32 = tmp

#### **S_ATOMIC_SWAP_X2**

**160**

Swap an unsigned 64-bit integer value in the data register with a location in the scalar memory.

addr = CalcScalarGlobalAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].b64; MEM[addr].b64 = DATA.b64; RETURN_DATA.b64 = tmp

#### **S_ATOMIC_CMPSWAP_X2**

**161**

Compare two unsigned 64-bit integer values stored in the data comparison register and a location in the scalar memory. Modify the memory location with a value in the data source register iff the comparison is equal.

addr = CalcScalarGlobalAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].u64; src = DATA[63 : 0].u64; cmp = DATA[127 : 64].u64; MEM[addr].u64 = tmp == cmp ? src : tmp; RETURN_DATA.u64 = tmp

157 of 553

12.6. SMEM Instructions

"AMD Instinct MI300" Instruction Set Architecture

**162**



#### **S_ATOMIC_ADD_X2**

Add two unsigned 64-bit integer values stored in the data register and a location in the scalar memory.

addr = CalcScalarGlobalAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].u64; MEM[addr].u64 += DATA.u64; RETURN_DATA.u64 = tmp

#### **S_ATOMIC_SUB_X2**

**163**

Subtract an unsigned 64-bit integer value stored in the data register from a value stored in a location in the scalar memory.

addr = CalcScalarGlobalAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].u64; MEM[addr].u64 -= DATA.u64; RETURN_DATA.u64 = tmp

#### **S_ATOMIC_SMIN_X2**

**164**

Select the minimum of two signed 64-bit integer inputs, given two values stored in the data register and a location in the scalar memory. Update the scalar memory with the selected value.

addr = CalcScalarGlobalAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].i64; src = DATA.i64; MEM[addr].i64 = src < tmp ? src : tmp; RETURN_DATA.i64 = tmp

#### **S_ATOMIC_UMIN_X2**

**165**

Select the minimum of two unsigned 64-bit integer inputs, given two values stored in the data register and a location in the scalar memory. Update the scalar memory with the selected value.

addr = CalcScalarGlobalAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].u64; src = DATA.u64; MEM[addr].u64 = src < tmp ? src : tmp; RETURN_DATA.u64 = tmp

158 of 553

12.6. SMEM Instructions

"AMD Instinct MI300" Instruction Set Architecture



#### **S_ATOMIC_SMAX_X2**

**166**

Select the maximum of two signed 64-bit integer inputs, given two values stored in the data register and a location in the scalar memory. Update the scalar memory with the selected value.

addr = CalcScalarGlobalAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].i64; src = DATA.i64; MEM[addr].i64 = src >= tmp ? src : tmp; RETURN_DATA.i64 = tmp

#### **S_ATOMIC_UMAX_X2**

**167**

Select the maximum of two unsigned 64-bit integer inputs, given two values stored in the data register and a location in the scalar memory. Update the scalar memory with the selected value.

addr = CalcScalarGlobalAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].u64; src = DATA.u64; MEM[addr].u64 = src >= tmp ? src : tmp; RETURN_DATA.u64 = tmp

#### **S_ATOMIC_AND_X2**

**168**

Calculate bitwise AND given two unsigned 64-bit integer values stored in the data register and a location in the scalar memory.

addr = CalcScalarGlobalAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].b64; MEM[addr].b64 = (tmp & DATA.b64); RETURN_DATA.b64 = tmp

#### **S_ATOMIC_OR_X2**

**169**

Calculate bitwise OR given two unsigned 64-bit integer values stored in the data register and a location in the scalar memory.

addr = CalcScalarGlobalAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].b64; MEM[addr].b64 = (tmp | DATA.b64);

159 of 553

12.6. SMEM Instructions

"AMD Instinct MI300" Instruction Set Architecture



RETURN_DATA.b64 = tmp

#### **S_ATOMIC_XOR_X2**

**170**

Calculate bitwise XOR given two unsigned 64-bit integer values stored in the data register and a location in the scalar memory.

addr = CalcScalarGlobalAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].b64; MEM[addr].b64 = (tmp ^ DATA.b64); RETURN_DATA.b64 = tmp

#### **S_ATOMIC_INC_X2**

**171**

Increment an unsigned 64-bit integer value from a location in the scalar memory with wraparound to 0 if the value exceeds a value in the data register.

addr = CalcScalarGlobalAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].u64; src = DATA.u64; MEM[addr].u64 = tmp >= src ? 0ULL : tmp + 1ULL; RETURN_DATA.u64 = tmp

#### **S_ATOMIC_DEC_X2**

**172**

Decrement an unsigned 64-bit integer value from a location in the scalar memory with wraparound to a value in the data register if the decrement yields a negative value.

addr = CalcScalarGlobalAddr(SBASE.b32, SOFFSET.b32, OFFSET.i32); tmp = MEM[addr].u64; src = DATA.u64; MEM[addr].u64 = ((tmp == 0ULL) || (tmp > src)) ? src : tmp - 1ULL; RETURN_DATA.u64 = tmp

160 of 553

12.6. SMEM Instructions

"AMD Instinct MI300" Instruction Set Architecture

**0**



## **12.7. VOP2 Instructions**



Instructions in this format may use a 32-bit literal constant, DPP or SDWA which occurs immediately after the instruction.

**V_CNDMASK_B32**

Copy data from one of two inputs based on the per-lane condition code and store the result into a vector register.

D0.u32 = VCC.u64[laneId] ? S1.u32 : S0.u32

#### **Notes**

In VOP3 the VCC source may be a scalar GPR specified in S2.

Floating-point modifiers are valid for this instruction if S0 and S1 are 32-bit floating point values. This instruction is suitable for negating or taking the absolute value of a floating-point value.

**V_ADD_F32**

**1**

Add two floating point inputs and store the result into a vector register.

D0.f32 = S0.f32 + S1.f32

#### **Notes**

0.5ULP precision, denormals are supported.

**V_SUB_F32 2**

Subtract the second floating point input from the first input and store the result into a vector register.

D0.f32 = S0.f32 - S1.f32

#### **Notes**

0.5ULP precision, denormals are supported.

161 of 553

12.7. VOP2 Instructions

"AMD Instinct MI300" Instruction Set Architecture

**V_SUBREV_F32**

**3**



Subtract the _first_ floating point input from the _second_ input and store the result into a vector register.

D0.f32 = S1.f32 - S0.f32

#### **Notes**

0.5ULP precision, denormals are supported.

**V_FMAC_F64 4**

Multiply two floating point inputs and accumulate the result into the destination register using fused multiply add.

D0.f64 = fma(S0.f64, S1.f64, D0.f64)

**V_MUL_F32 5**

Multiply two floating point inputs and store the result into a vector register.

D0.f32 = S0.f32 * S1.f32

#### **Notes**

0.5ULP precision, denormals are supported.

**V_MUL_I32_I24 6**

Multiply two signed 24-bit integer inputs and store the result as a signed 32-bit integer into a vector register.

D0.i32 = 32'I(S0.i24) * 32'I(S1.i24)

#### **Notes**

This opcode is expected to be as efficient as basic single-precision opcodes since it utilizes the single-precision floating point multiplier. See also V_MUL_HI_I32_I24.

**V_MUL_HI_I32_I24**

**7**

162 of 553

12.7. VOP2 Instructions

"AMD Instinct MI300" Instruction Set Architecture



Multiply two signed 24-bit integer inputs and store the high 32 bits of the result as a signed 32-bit integer into a vector register.

D0.i32 = 32'I((64'I(S0.i24) * 64'I(S1.i24)) >> 32U)

#### **Notes**

See also V_MUL_I32_I24.

**V_MUL_U32_U24**

**8**

Multiply two unsigned 24-bit integer inputs and store the result as an unsigned 32-bit integer into a vector register.

D0.u32 = 32'U(S0.u24) * 32'U(S1.u24)

#### **Notes**

This opcode is expected to be as efficient as basic single-precision opcodes since it utilizes the single-precision floating point multiplier. See also V_MUL_HI_U32_U24.

**V_MUL_HI_U32_U24 9**

Multiply two unsigned 24-bit integer inputs and store the high 32 bits of the result as an unsigned 32-bit integer into a vector register.

D0.u32 = 32'U((64'U(S0.u24) * 64'U(S1.u24)) >> 32U)

#### **Notes**

See also V_MUL_U32_U24.

#### **V_MIN_F32**

**10**

Select the minimum of two single-precision float inputs and store the result into a vector register.

if (WAVE_MODE.IEEE && isSignalNAN(64'F(S0.f32))) then D0.f32 = 32'F(cvtToQuietNAN(64'F(S0.f32))) elsif (WAVE_MODE.IEEE && isSignalNAN(64'F(S1.f32))) then D0.f32 = 32'F(cvtToQuietNAN(64'F(S1.f32))) elsif isNAN(64'F(S0.f32)) then D0.f32 = S1.f32

163 of 553

12.7. VOP2 Instructions

"AMD Instinct MI300" Instruction Set Architecture



elsif isNAN(64'F(S1.f32)) then D0.f32 = S0.f32 elsif ((64'F(S0.f32) == +0.0) && (64'F(S1.f32) == -0.0)) then D0.f32 = S1.f32 elsif ((64'F(S0.f32) == -0.0) && (64'F(S1.f32) == +0.0)) then D0.f32 = S0.f32 else // Note: there's no IEEE case here like there is for V_MAX_F32. D0.f32 = S0.f32 < S1.f32 ? S0.f32 : S1.f32 endif

#### **V_MAX_F32**

**11**

Select the maximum of two single-precision float inputs and store the result into a vector register.

if (WAVE_MODE.IEEE && isSignalNAN(64'F(S0.f32))) then D0.f32 = 32'F(cvtToQuietNAN(64'F(S0.f32))) elsif (WAVE_MODE.IEEE && isSignalNAN(64'F(S1.f32))) then D0.f32 = 32'F(cvtToQuietNAN(64'F(S1.f32))) elsif isNAN(64'F(S0.f32)) then D0.f32 = S1.f32 elsif isNAN(64'F(S1.f32)) then D0.f32 = S0.f32 elsif ((64'F(S0.f32) == +0.0) && (64'F(S1.f32) == -0.0)) then D0.f32 = S0.f32 elsif ((64'F(S0.f32) == -0.0) && (64'F(S1.f32) == +0.0)) then D0.f32 = S1.f32 elsif WAVE_MODE.IEEE then D0.f32 = S0.f32 >= S1.f32 ? S0.f32 : S1.f32 else D0.f32 = S0.f32 > S1.f32 ? S0.f32 : S1.f32 endif

#### **V_MIN_I32**

**12**

Select the minimum of two signed 32-bit integer inputs and store the selected value into a vector register.

D0.i32 = S0.i32 < S1.i32 ? S0.i32 : S1.i32

#### **V_MAX_I32**

**13**

Select the maximum of two signed 32-bit integer inputs and store the selected value into a vector register.

D0.i32 = S0.i32 >= S1.i32 ? S0.i32 : S1.i32

164 of 553

12.7. VOP2 Instructions

"AMD Instinct MI300" Instruction Set Architecture

**14**



#### **V_MIN_U32**

Select the minimum of two unsigned 32-bit integer inputs and store the selected value into a vector register.

D0.u32 = S0.u32 < S1.u32 ? S0.u32 : S1.u32

#### **V_MAX_U32**

**15**

Select the maximum of two unsigned 32-bit integer inputs and store the selected value into a vector register.

D0.u32 = S0.u32 >= S1.u32 ? S0.u32 : S1.u32

#### **V_LSHRREV_B32**

**16**

Given a shift count in the _first_ vector input, calculate the logical shift right of the _second_ vector input and store the result into a vector register.

D0.u32 = (S1.u32 >> S0[4 : 0].u32)

#### **V_ASHRREV_I32**

**17**

Given a shift count in the _first_ vector input, calculate the arithmetic shift right (preserving sign bit) of the _second_ vector input and store the result into a vector register.

D0.i32 = (S1.i32 >> S0[4 : 0].u32)

#### **V_LSHLREV_B32**

**18**

Given a shift count in the _first_ vector input, calculate the logical shift left of the _second_ vector input and store the result into a vector register.

D0.u32 = (S1.u32 << S0[4 : 0].u32)

165 of 553

12.7. VOP2 Instructions

"AMD Instinct MI300" Instruction Set Architecture

**V_AND_B32**

**19**



Calculate bitwise AND on two vector inputs and store the result into a vector register.

D0.u32 = (S0.u32 & S1.u32)

#### **Notes**

Input and output modifiers not supported.

**V_OR_B32 20**

Calculate bitwise OR on two vector inputs and store the result into a vector register.

D0.u32 = (S0.u32 | S1.u32)

#### **Notes**

Input and output modifiers not supported.

**V_XOR_B32 21**

Calculate bitwise XOR on two vector inputs and store the result into a vector register.

D0.u32 = (S0.u32 ^ S1.u32)

#### **Notes**

Input and output modifiers not supported.

**V_FMAMK_F32 23**

Multiply a single-precision float input with a literal constant and add a second single-precision float input using fused multiply add, and store the result into a vector register.

D0.f32 = fma(S0.f32, SIMM32.f32, S1.f32)

#### **Notes**

This opcode cannot use the VOP3 encoding and cannot use input/output modifiers.

166 of 553

12.7. VOP2 Instructions

"AMD Instinct MI300" Instruction Set Architecture

**V_FMAAK_F32**

**24**



Multiply two single-precision float inputs and add a literal constant using fused multiply add, and store the result into a vector register.

D0.f32 = fma(S0.f32, S1.f32, SIMM32.f32)

#### **Notes**

This opcode cannot use the VOP3 encoding and cannot use input/output modifiers.

#### **V_ADD_CO_U32**

**25**

Add two unsigned 32-bit integer inputs, store the result into a vector register and store the carry-out mask into a scalar register.

tmp = 64'U(S0.u32) + 64'U(S1.u32); VCC.u64[laneId] = tmp >= 0x100000000ULL ? 1'1U : 1'0U; // VCC is an UNSIGNED overflow/carry-out for V_ADDC_CO_U32. D0.u32 = tmp.u32

#### **Notes**

In VOP3 the VCC destination may be an arbitrary SGPR-pair.

Supports saturation (unsigned 32-bit integer domain).

**V_SUB_CO_U32**

**26**

Subtract the second unsigned 32-bit integer input from the first input, store the result into a vector register and store the carry-out mask into a scalar register.

tmp = S0.u32 - S1.u32; VCC.u64[laneId] = S1.u32 > S0.u32 ? 1'1U : 1'0U; // VCC is an UNSIGNED overflow/carry-out for V_SUBB_CO_U32. D0.u32 = tmp.u32

#### **Notes**

In VOP3 the VCC destination may be an arbitrary SGPR-pair.

Supports saturation (unsigned 32-bit integer domain).

167 of 553

12.7. VOP2 Instructions

"AMD Instinct MI300" Instruction Set Architecture

**V_SUBREV_CO_U32**

**27**



Subtract the _first_ unsigned 32-bit integer input from the _second_ input, store the result into a vector register and store the carry-out mask into a scalar register.

tmp = S1.u32 - S0.u32; VCC.u64[laneId] = S0.u32 > S1.u32 ? 1'1U : 1'0U; // VCC is an UNSIGNED overflow/carry-out for V_SUBB_CO_U32. D0.u32 = tmp.u32

#### **Notes**

In VOP3 the VCC destination may be an arbitrary SGPR-pair.

Supports saturation (unsigned 32-bit integer domain).

#### **V_ADDC_CO_U32**

**28**

Add two unsigned 32-bit integer inputs and a bit from a carry-in mask, store the result into a vector register and store the carry-out mask into a scalar register.

tmp = 64'U(S0.u32) + 64'U(S1.u32) + VCC.u64[laneId].u64; VCC.u64[laneId] = tmp >= 0x100000000ULL ? 1'1U : 1'0U; // VCC is an UNSIGNED overflow/carry-out for V_ADDC_CO_U32. D0.u32 = tmp.u32

#### **Notes**

In VOP3 the VCC destination may be an arbitrary SGPR-pair, and the VCC source comes from the SGPR-pair at S2.u.

Supports saturation (unsigned 32-bit integer domain).

**V_SUBB_CO_U32 29**

Subtract the second unsigned 32-bit integer input from the first input, subtract a bit from the carry-in mask, store the result into a vector register and store the carry-out mask into a scalar register.

tmp = S0.u32 - S1.u32 - VCC.u64[laneId].u32; VCC.u64[laneId] = 64'U(S1.u32) + VCC.u64[laneId].u64 > 64'U(S0.u32) ? 1'1U : 1'0U; // VCC is an UNSIGNED overflow/carry-out for V_SUBB_CO_U32. D0.u32 = tmp.u32

#### **Notes**

168 of 553

12.7. VOP2 Instructions

"AMD Instinct MI300" Instruction Set Architecture



In VOP3 the VCC destination may be an arbitrary SGPR-pair, and the VCC source comes from the SGPR-pair at S2.u.

Supports saturation (unsigned 32-bit integer domain).

#### **V_SUBBREV_CO_U32**

**30**

Subtract the _first_ unsigned 32-bit integer input from the _second_ input, subtract a bit from the carry-in mask, store the result into a vector register and store the carry-out mask into a scalar register.

tmp = S1.u32 - S0.u32 - VCC.u64[laneId].u32; VCC.u64[laneId] = 64'U(S0.u32) + VCC.u64[laneId].u64 > 64'U(S1.u32) ? 1'1U : 1'0U; // VCC is an UNSIGNED overflow/carry-out for V_SUBB_CO_U32. D0.u32 = tmp.u32

#### **Notes**

In VOP3 the VCC destination may be an arbitrary SGPR-pair, and the VCC source comes from the SGPR-pair at S2.u.

Supports saturation (unsigned 32-bit integer domain).

**V_ADD_F16**

**31**

Add two floating point inputs and store the result into a vector register.

D0.f16 = S0.f16 + S1.f16

#### **Notes**

0.5ULP precision. Supports denormals, round mode, exception flags and saturation.

**V_SUB_F16 32**

Subtract the second floating point input from the first input and store the result into a vector register.

D0.f16 = S0.f16 - S1.f16

#### **Notes**

0.5ULP precision. Supports denormals, round mode, exception flags and saturation.

169 of 553

12.7. VOP2 Instructions

"AMD Instinct MI300" Instruction Set Architecture

**V_SUBREV_F16**

**33**



Subtract the _first_ floating point input from the _second_ input and store the result into a vector register.

D0.f16 = S1.f16 - S0.f16

#### **Notes**

0.5ULP precision. Supports denormals, round mode, exception flags and saturation.

**V_MUL_F16 34**

Multiply two floating point inputs and store the result into a vector register.

D0.f16 = S0.f16 * S1.f16

#### **Notes**

0.5ULP precision. Supports denormals, round mode, exception flags and saturation.

**V_MAC_F16 35**

Multiply two floating point inputs and accumulate the result into the destination register. Implements IEEE rules and non-standard rule for OPSEL.

tmp = S0.f16 * S1.f16 + D0.f16; if OPSEL.u4[3] then D0 = { tmp.f16, D0[15 : 0] } else D0 = { 16'0, tmp.f16 } endif

#### **Notes**

Supports round mode, exception flags, saturation.

**V_MADMK_F16**

**36**

Multiply a floating point input with a literal constant and add a second floating point input, and store the result into a vector register. Implements IEEE rules.

tmp = S0.f16 * SIMM16.f16 + S1.f16;

170 of 553

12.7. VOP2 Instructions

"AMD Instinct MI300" Instruction Set Architecture

**37**



D0 = { 16'0, tmp.f16 }

#### **Notes**

This opcode cannot use the VOP3 encoding and cannot use input/output modifiers. Supports round mode, exception flags, saturation.

**V_MADAK_F16**

Multiply two floating point inputs and add a literal constant, and store the result into a vector register. Implements IEEE rules.

tmp = S0.f16 * S1.f16 + SIMM16.f16; D0 = { 16'0, tmp.f16 }

#### **Notes**

This opcode cannot use the VOP3 encoding and cannot use input/output modifiers. Supports round mode, exception flags, saturation.

**V_ADD_U16 38**

Add two unsigned 16-bit integer inputs and store the result into a vector register. No carry-in or carry-out support.

D0.u16 = S0.u16 + S1.u16

#### **Notes**

Supports saturation (unsigned 16-bit integer domain).

**V_SUB_U16**

**39**

Subtract the second unsigned 16-bit integer input from the first input and store the result into a vector register. No carry-in or carry-out support.

D0.u16 = S0.u16 - S1.u16

#### **Notes**

Supports saturation (unsigned 16-bit integer domain).

171 of 553

12.7. VOP2 Instructions

"AMD Instinct MI300" Instruction Set Architecture

**40**



#### **V_SUBREV_U16**

Subtract the _first_ unsigned 16-bit integer input from the _second_ input and store the result into a vector register. No carry-in or carry-out support.

D0.u16 = S1.u16 - S0.u16

#### **Notes**

Supports saturation (unsigned 16-bit integer domain).

**V_MUL_LO_U16**

**41**

Multiply two unsigned 16-bit integer inputs and store the low bits of the result into a vector register.

D0.u16 = S0.u16 * S1.u16

#### **Notes**

Supports saturation (unsigned 16-bit integer domain).

**V_LSHLREV_B16 42**

Given a shift count in the _first_ vector input, calculate the logical shift left of the _second_ vector input and store the result into a vector register.

D0.u16 = (S1.u16 << S0[3 : 0].u32)

#### **V_LSHRREV_B16**

**43**

Given a shift count in the _first_ vector input, calculate the logical shift right of the _second_ vector input and store the result into a vector register.

D0.u16 = (S1.u16 >> S0[3 : 0].u32)

**V_ASHRREV_I16 44**

Given a shift count in the _first_ vector input, calculate the arithmetic shift right (preserving sign bit) of the _second_

172 of 553

12.7. VOP2 Instructions

"AMD Instinct MI300" Instruction Set Architecture



vector input and store the result into a vector register.

D0.i16 = (S1.i16 >> S0[3 : 0].u32)

#### **V_MAX_F16**

**45**

Select the maximum of two half-precision float inputs and store the result into a vector register.

if (WAVE_MODE.IEEE && isSignalNAN(64'F(S0.f16))) then D0.f16 = 16'F(cvtToQuietNAN(64'F(S0.f16))) elsif (WAVE_MODE.IEEE && isSignalNAN(64'F(S1.f16))) then D0.f16 = 16'F(cvtToQuietNAN(64'F(S1.f16))) elsif isNAN(64'F(S0.f16)) then D0.f16 = S1.f16 elsif isNAN(64'F(S1.f16)) then D0.f16 = S0.f16 elsif ((64'F(S0.f16) == +0.0) && (64'F(S1.f16) == -0.0)) then D0.f16 = S0.f16 elsif ((64'F(S0.f16) == -0.0) && (64'F(S1.f16) == +0.0)) then D0.f16 = S1.f16 elsif WAVE_MODE.IEEE then D0.f16 = S0.f16 >= S1.f16 ? S0.f16 : S1.f16 else D0.f16 = S0.f16 > S1.f16 ? S0.f16 : S1.f16 endif

#### **Notes**

IEEE compliant. Supports denormals, round mode, exception flags, saturation.

#### **V_MIN_F16**

**46**

Select the minimum of two half-precision float inputs and store the result into a vector register.

if (WAVE_MODE.IEEE && isSignalNAN(64'F(S0.f16))) then D0.f16 = 16'F(cvtToQuietNAN(64'F(S0.f16))) elsif (WAVE_MODE.IEEE && isSignalNAN(64'F(S1.f16))) then D0.f16 = 16'F(cvtToQuietNAN(64'F(S1.f16))) elsif isNAN(64'F(S0.f16)) then D0.f16 = S1.f16 elsif isNAN(64'F(S1.f16)) then D0.f16 = S0.f16 elsif ((64'F(S0.f16) == +0.0) && (64'F(S1.f16) == -0.0)) then D0.f16 = S1.f16 elsif ((64'F(S0.f16) == -0.0) && (64'F(S1.f16) == +0.0)) then D0.f16 = S0.f16 else // Note: there's no IEEE case here like there is for V_MAX_F16.

173 of 553

12.7. VOP2 Instructions

"AMD Instinct MI300" Instruction Set Architecture



D0.f16 = S0.f16 < S1.f16 ? S0.f16 : S1.f16 endif

#### **Notes**

IEEE compliant. Supports denormals, round mode, exception flags, saturation.

#### **V_MAX_U16**

**47**

Select the maximum of two unsigned 16-bit integer inputs and store the selected value into a vector register.

D0.u16 = S0.u16 >= S1.u16 ? S0.u16 : S1.u16

#### **V_MAX_I16**

**48**

Select the maximum of two signed 16-bit integer inputs and store the selected value into a vector register.

D0.i16 = S0.i16 >= S1.i16 ? S0.i16 : S1.i16

#### **V_MIN_U16**

**49**

Select the minimum of two unsigned 16-bit integer inputs and store the selected value into a vector register.

D0.u16 = S0.u16 < S1.u16 ? S0.u16 : S1.u16

**V_MIN_I16 50**

Select the minimum of two signed 16-bit integer inputs and store the selected value into a vector register.

D0.i16 = S0.i16 < S1.i16 ? S0.i16 : S1.i16

#### **V_LDEXP_F16**

**51**

Multiply the first input, a floating point value, by an integral power of 2 specified in the second input, a signed integer value, and store the floating point result into a vector register.

174 of 553

12.7. VOP2 Instructions

"AMD Instinct MI300" Instruction Set Architecture

**52**



D0.f16 = S0.f16 * 16'F(2.0F ** 32'I(S1.i16))

#### **Notes**

Compare with the ldexp() function in C. Note that the S1 has a format of f16 since floating point literal constants are interpreted as 16 bit value for this opcode.

**V_ADD_U32**

Add two unsigned 32-bit integer inputs and store the result into a vector register. No carry-in or carry-out support.

D0.u32 = S0.u32 + S1.u32

#### **Notes**

Supports saturation (unsigned 32-bit integer domain).

**V_SUB_U32 53**

Subtract the second unsigned 32-bit integer input from the first input and store the result into a vector register. No carry-in or carry-out support.

D0.u32 = S0.u32 - S1.u32

#### **Notes**

Supports saturation (unsigned 32-bit integer domain).

**V_SUBREV_U32**

**54**

Subtract the _first_ unsigned 32-bit integer input from the _second_ input and store the result into a vector register. No carry-in or carry-out support.

D0.u32 = S1.u32 - S0.u32

#### **Notes**

Supports saturation (unsigned 32-bit integer domain).

175 of 553

12.7. VOP2 Instructions

"AMD Instinct MI300" Instruction Set Architecture

**55**



#### **V_DOT2C_F32_F16**

Compute the dot product of two packed 2-D half-precision float inputs in the single-precision float domain and accumulate with the single-precision float value in the destination register.

tmp = D0.f32; tmp += f16_to_f32(S0[15 : 0].f16) * f16_to_f32(S1[15 : 0].f16); tmp += f16_to_f32(S0[31 : 16].f16) * f16_to_f32(S1[31 : 16].f16); D0.f32 = tmp

#### **V_DOT2C_I32_I16**

**56**

Compute the dot product of two packed 2-D signed 16-bit integer inputs in the signed 32-bit integer domain and accumulate with the signed 32-bit integer value in the destination register.

tmp = D0.i32; tmp += i16_to_i32(S0[15 : 0].i16) * i16_to_i32(S1[15 : 0].i16); tmp += i16_to_i32(S0[31 : 16].i16) * i16_to_i32(S1[31 : 16].i16); D0.i32 = tmp

**V_DOT4C_I32_I8 57**

Compute the dot product of two packed 4-D signed 8-bit integer inputs in the signed 32-bit integer domain and accumulate with the signed 32-bit integer value in the destination register.

tmp = D0.i32; tmp += i8_to_i32(S0[7 : 0].i8) * i8_to_i32(S1[7 : 0].i8); tmp += i8_to_i32(S0[15 : 8].i8) * i8_to_i32(S1[15 : 8].i8); tmp += i8_to_i32(S0[23 : 16].i8) * i8_to_i32(S1[23 : 16].i8); tmp += i8_to_i32(S0[31 : 24].i8) * i8_to_i32(S1[31 : 24].i8); D0.i32 = tmp

#### **V_DOT8C_I32_I4**

**58**

Compute the dot product of two packed 8-D signed 4-bit integer inputs in the signed 32-bit integer domain and accumulate with the signed 32-bit integer value in the destination register.

tmp = D0.i32; tmp += i4_to_i32(S0[3 : 0].i4) * i4_to_i32(S1[3 : 0].i4); tmp += i4_to_i32(S0[7 : 4].i4) * i4_to_i32(S1[7 : 4].i4); tmp += i4_to_i32(S0[11 : 8].i4) * i4_to_i32(S1[11 : 8].i4); tmp += i4_to_i32(S0[15 : 12].i4) * i4_to_i32(S1[15 : 12].i4); tmp += i4_to_i32(S0[19 : 16].i4) * i4_to_i32(S1[19 : 16].i4);

176 of 553

12.7. VOP2 Instructions

"AMD Instinct MI300" Instruction Set Architecture



tmp += i4_to_i32(S0[23 : 20].i4) * i4_to_i32(S1[23 : 20].i4); tmp += i4_to_i32(S0[27 : 24].i4) * i4_to_i32(S1[27 : 24].i4); tmp += i4_to_i32(S0[31 : 28].i4) * i4_to_i32(S1[31 : 28].i4); D0.i32 = tmp

#### **V_FMAC_F32**

**59**

Multiply two floating point inputs and accumulate the result into the destination register using fused multiply add.

D0.f32 = fma(S0.f32, S1.f32, D0.f32)

#### **V_PK_FMAC_F16**

**60**

Multiply two packed half-precision float inputs component-wise and accumulate the result into the destination register using fused multiply add.

D0[15 : 0].f16 = fma(S0[15 : 0].f16, S1[15 : 0].f16, D0[15 : 0].f16); D0[31 : 16].f16 = fma(S0[31 : 16].f16, S1[31 : 16].f16, D0[31 : 16].f16)

#### **V_XNOR_B32**

**61**

Calculate bitwise XNOR on two vector inputs and store the result into a vector register.

D0.u32 = ~(S0.u32 ^ S1.u32)

#### **Notes**

Input and output modifiers not supported.

177 of 553

12.7. VOP2 Instructions

"AMD Instinct MI300" Instruction Set Architecture



### **12.7.1. VOP2 using VOP3 encoding**

Instructions in this format may also be encoded as VOP3. This allows access to the extra control bits (e.g. ABS, OMOD) in exchange for not being able to use a literal constant. The VOP3 opcode is: VOP2 opcode + 0x100.





## **12.8. VOP1 Instructions**



Instructions in this format may use a 32-bit literal constant, DPP or SDWA which occurs immediately after the instruction.

**V_NOP 0**

Do nothing.

#### **Notes**

This instruction can be used to insert a single-cycle bubble in the vector ALU pipeline. For multiple cycles repeat this opcode.

**V_MOV_B32**

**1**

Move 32-bit data from a vector input into a vector register.

D0.b32 = S0.b32

#### **Notes**

Floating-point modifiers are valid for this instruction if S0 is a 32-bit floating point value. This instruction is suitable for negating or taking the absolute value of a floating-point value.

Functional examples:

v_mov_b32 v0, v1    // Move into v0 from v1 v_mov_b32 v0, -v1   // Set v0 to the negation of v1

178 of 553

12.8. VOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture

**2**



v_mov_b32 v0, abs(v1)   // Set v0 to the absolute value of v1

#### **V_READFIRSTLANE_B32**

Read the scalar value in the lowest active lane of the input vector register and store it into a scalar register.

declare lane : 32'I; if EXEC == 0x0LL then lane = 0; // Force lane 0 if all lanes are disabled else lane = s_ff1_i32_b64(EXEC); // Lowest active lane endif; D0.b32 = VGPR[lane][SRC0.u32]

#### **Notes**

Overrides EXEC mask for the VGPR read. Input and output modifiers not supported; this is an untyped operation.

**V_CVT_I32_F64**

**3**

Convert from a double-precision float input to a signed 32-bit integer value and store the result into a vector register.

D0.i32 = f64_to_i32(S0.f64)

#### **Notes**

0.5ULP accuracy, out-of-range floating point values (including infinity) saturate. NAN is converted to 0.

Generation of the INEXACT exception is controlled by the CLAMP bit. INEXACT exceptions are enabled for this conversion iff CLAMP == 1.

**V_CVT_F64_I32**

**4**

Convert from a signed 32-bit integer input to a double-precision float value and store the result into a vector register.

D0.f64 = i32_to_f64(S0.i32)

179 of 553

12.8. VOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture



#### **Notes**

0ULP accuracy.

**V_CVT_F32_I32**

**5**

Convert from a signed 32-bit integer input to a single-precision float value and store the result into a vector register.

D0.f32 = i32_to_f32(S0.i32)

#### **Notes**

0.5ULP accuracy.

**V_CVT_F32_U32 6**

Convert from an unsigned 32-bit integer input to a single-precision float value and store the result into a vector register.

D0.f32 = u32_to_f32(S0.u32)

#### **Notes**

0.5ULP accuracy.

**V_CVT_U32_F32**

**7**

Convert from a single-precision float input to an unsigned 32-bit integer value and store the result into a vector register.

D0.u32 = f32_to_u32(S0.f32)

#### **Notes**

1ULP accuracy, out-of-range floating point values (including infinity) saturate. NAN is converted to 0.

Generation of the INEXACT exception is controlled by the CLAMP bit. INEXACT exceptions are enabled for this conversion iff CLAMP == 1.

180 of 553

12.8. VOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture

**V_CVT_I32_F32**

**8**



Convert from a single-precision float input to a signed 32-bit integer value and store the result into a vector register.

D0.i32 = f32_to_i32(S0.f32)

#### **Notes**

1ULP accuracy, out-of-range floating point values (including infinity) saturate. NAN is converted to 0.

Generation of the INEXACT exception is controlled by the CLAMP bit. INEXACT exceptions are enabled for this conversion iff CLAMP == 1.

**V_CVT_F16_F32 10**

Convert from a single-precision float input to a half-precision float value and store the result into a vector register.

D0.f16 = f32_to_f16(S0.f32)

#### **Notes**

0.5ULP accuracy, supports input modifiers and creates FP16 denormals when appropriate. Flush denorms on output if specified based on DP denorm mode. Output rounding based on DP rounding mode.

**V_CVT_F32_F16 11**

Convert from a half-precision float input to a single-precision float value and store the result into a vector register.

D0.f32 = f16_to_f32(S0.f16)

#### **Notes**

0ULP accuracy, FP16 denormal inputs are accepted. Flush denorms on input if specified based on DP denorm mode.

**V_CVT_RPI_I32_F32 12**

Convert from a single-precision float input to a signed 32-bit integer value using round to nearest integer semantics (ignore the default rounding mode) and store the result into a vector register.

181 of 553

12.8. VOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture



D0.i32 = f32_to_i32(floor(S0.f32 + 0.5F))

#### **Notes**

0.5ULP accuracy, denormals are supported.

**V_CVT_FLR_I32_F32 13**

Convert from a single-precision float input to a signed 32-bit integer value using round-down semantics (ignore the default rounding mode) and store the result into a vector register.

D0.i32 = f32_to_i32(floor(S0.f32))

#### **Notes**

1ULP accuracy, denormals are supported.

**V_CVT_OFF_F32_I4 14**

Convert from a signed 4-bit integer input to a single-precision float value using an offset table and store the result into a vector register.

Used for interpolation in shader. Lookup table on S0[3:0]:

S0 binary Result 1000 -0.5000f 1001 -0.4375f 1010 -0.3750f 1011 -0.3125f 1100 -0.2500f 1101 -0.1875f 1110 -0.1250f 1111 -0.0625f 0000 +0.0000f 0001 +0.0625f 0010 +0.1250f 0011 +0.1875f 0100 +0.2500f 0101 +0.3125f 0110 +0.3750f 0111 +0.4375f

declare CVT_OFF_TABLE : 32'F[16]; D0.f32 = CVT_OFF_TABLE[S0.u32[3 : 0]]

182 of 553

12.8. VOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture

**15**



**V_CVT_F32_F64**

Convert from a double-precision float input to a single-precision float value and store the result into a vector register.

D0.f32 = f64_to_f32(S0.f64)

#### **Notes**

0.5ULP accuracy, denormals are supported.

**V_CVT_F64_F32**

**16**

Convert from a single-precision float input to a double-precision float value and store the result into a vector register.

D0.f64 = f32_to_f64(S0.f32)

#### **Notes**

0ULP accuracy, denormals are supported.

**V_CVT_F32_UBYTE0**

**17**

Convert an unsigned byte in byte 0 of the input to a single-precision float value and store the result into a vector register.

D0.f32 = u32_to_f32(S0[7 : 0].u32)

#### **V_CVT_F32_UBYTE1**

**18**

Convert an unsigned byte in byte 1 of the input to a single-precision float value and store the result into a vector register.

D0.f32 = u32_to_f32(S0[15 : 8].u32)

**V_CVT_F32_UBYTE2**

**19**

183 of 553

12.8. VOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture



Convert an unsigned byte in byte 2 of the input to a single-precision float value and store the result into a vector register.

D0.f32 = u32_to_f32(S0[23 : 16].u32)

**V_CVT_F32_UBYTE3 20**

Convert an unsigned byte in byte 3 of the input to a single-precision float value and store the result into a vector register.

D0.f32 = u32_to_f32(S0[31 : 24].u32)

**V_CVT_U32_F64 21**

Convert from a double-precision float input to an unsigned 32-bit integer value and store the result into a vector register.

D0.u32 = f64_to_u32(S0.f64)

#### **Notes**

0.5ULP accuracy, out-of-range floating point values (including infinity) saturate. NAN is converted to 0.

Generation of the INEXACT exception is controlled by the CLAMP bit. INEXACT exceptions are enabled for this conversion iff CLAMP == 1.

**V_CVT_F64_U32**

**22**

Convert from an unsigned 32-bit integer input to a double-precision float value and store the result into a vector register.

D0.f64 = u32_to_f64(S0.u32)

#### **Notes**

0ULP accuracy.

**V_TRUNC_F64**

**23**

184 of 553

12.8. VOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture



Compute the integer part of a double-precision float input using round toward zero semantics and store the result in floating point format into a vector register.

D0.f64 = trunc(S0.f64)

**V_CEIL_F64 24**

Round the double-precision float input up to next integer and store the result in floating point format into a vector register.

D0.f64 = trunc(S0.f64); if ((S0.f64 > 0.0) && (S0.f64 != D0.f64)) then D0.f64 += 1.0 endif

**V_RNDNE_F64 25**

Round the double-precision float input to the nearest even integer and store the result in floating point format into a vector register.

D0.f64 = floor(S0.f64 + 0.5); if (isEven(floor(S0.f64)) && (fract(S0.f64) == 0.5)) then D0.f64 -= 1.0 endif

**V_FLOOR_F64 26**

Round the double-precision float input down to previous integer and store the result in floating point format into a vector register.

D0.f64 = trunc(S0.f64); if ((S0.f64 < 0.0) && (S0.f64 != D0.f64)) then D0.f64 += -1.0 endif

**V_FRACT_F32**

**27**

Compute the fractional portion of a single-precision float input and store the result in floating point format into a vector register.

185 of 553

12.8. VOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture



D0.f32 = S0.f32 + -floor(S0.f32)

#### **Notes**

#### 0.5ULP accuracy, denormals are accepted.

This is intended to comply with the DX specification of fract where the function behaves like an extension of integer modulus; be aware this may differ from how fract() is defined in other domains. For example: fract(1.2) = 0.8 in DX.

Obey round mode, result clamped to 0x3f7fffff.

#### **V_TRUNC_F32**

**28**

Compute the integer part of a single-precision float input using round toward zero semantics and store the result in floating point format into a vector register.

D0.f32 = trunc(S0.f32)

**V_CEIL_F32**

**29**

Round the single-precision float input up to next integer and store the result in floating point format into a vector register.

D0.f32 = trunc(S0.f32); if ((S0.f32 > 0.0F) && (S0.f32 != D0.f32)) then D0.f32 += 1.0F endif

#### **V_RNDNE_F32**

**30**

Round the single-precision float input to the nearest even integer and store the result in floating point format into a vector register.

D0.f32 = floor(S0.f32 + 0.5F); if (isEven(64'F(floor(S0.f32))) && (fract(S0.f32) == 0.5F)) then D0.f32 -= 1.0F endif

186 of 553

12.8. VOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture

**31**



#### **V_FLOOR_F32**

Round the single-precision float input down to previous integer and store the result in floating point format into a vector register.

D0.f32 = trunc(S0.f32); if ((S0.f32 < 0.0F) && (S0.f32 != D0.f32)) then D0.f32 += -1.0F endif

**V_EXP_F32 32**

Calculate 2 raised to the power of the single-precision float input and store the result into a vector register.

D0.f32 = pow(2.0F, S0.f32)

#### **Notes**

1ULP accuracy, denormals are flushed.

Functional examples:

V_EXP_F32(0xff800000) => 0x00000000     // exp(-INF) = 0 V_EXP_F32(0x80000000) => 0x3f800000     // exp(-0.0) = 1 V_EXP_F32(0x7f800000) => 0x7f800000     // exp(+INF) = +INF

**V_LOG_F32 33**

Calculate the base 2 logarithm of the single-precision float input and store the result into a vector register.

D0.f32 = log2(S0.f32)

#### **Notes**

1ULP accuracy, denormals are flushed.

Functional examples:

V_LOG_F32(0xff800000) => 0xffc00000     // log(-INF) = NAN V_LOG_F32(0xbf800000) => 0xffc00000     // log(-1.0) = NAN V_LOG_F32(0x80000000) => 0xff800000     // log(-0.0) = -INF V_LOG_F32(0x00000000) => 0xff800000     // log(+0.0) = -INF V_LOG_F32(0x3f800000) => 0x00000000     // log(+1.0) = 0

187 of 553

12.8. VOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture

**34**



V_LOG_F32(0x7f800000) => 0x7f800000     // log(+INF) = +INF

**V_RCP_F32**

Calculate the reciprocal of the single-precision float input using IEEE rules and store the result into a vector register.

D0.f32 = 1.0F / S0.f32

#### **Notes**

1ULP accuracy. Accuracy converges to < 0.5ULP when using the Newton-Raphson method and 2 FMA operations. Denormals are flushed.

Functional examples:

V_RCP_F32(0xff800000) => 0x80000000     // rcp(-INF) = -0 V_RCP_F32(0xc0000000) => 0xbf000000     // rcp(-2.0) = -0.5 V_RCP_F32(0x80000000) => 0xff800000     // rcp(-0.0) = -INF V_RCP_F32(0x00000000) => 0x7f800000     // rcp(+0.0) = +INF V_RCP_F32(0x7f800000) => 0x00000000     // rcp(+INF) = +0

**V_RCP_IFLAG_F32**

**35**

Calculate the reciprocal of the vector float input in a manner suitable for integer division and store the result into a vector register. This opcode is intended for use as part of an integer division macro.

D0.f32 = 1.0F / S0.f32; // Can only raise integer DIV_BY_ZERO exception

#### **Notes**

Can raise integer DIV_BY_ZERO exception but cannot raise floating-point exceptions. To be used in an integer reciprocal macro by the compiler with one of the sequences listed below (depending on signed or unsigned operation).

Unsigned usage: CVT_F32_U32 RCP_IFLAG_F32 MUL_F32 (2**32 - 1) CVT_U32_F32

Signed usage: CVT_F32_I32

188 of 553

12.8. VOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture

**36**



RCP_IFLAG_F32 MUL_F32 (2**31 - 1) CVT_I32_F32

#### **V_RSQ_F32**

Calculate the reciprocal of the square root of the single-precision float input using IEEE rules and store the result into a vector register.

D0.f32 = 1.0F / sqrt(S0.f32)

#### **Notes**

1ULP accuracy, denormals are flushed.

Functional examples:

V_RSQ_F32(0xff800000) => 0xffc00000     // rsq(-INF) = NAN V_RSQ_F32(0x80000000) => 0xff800000     // rsq(-0.0) = -INF V_RSQ_F32(0x00000000) => 0x7f800000     // rsq(+0.0) = +INF V_RSQ_F32(0x40800000) => 0x3f000000     // rsq(+4.0) = +0.5 V_RSQ_F32(0x7f800000) => 0x00000000     // rsq(+INF) = +0

#### **V_RCP_F64**

**37**

Calculate the reciprocal of the double-precision float input using IEEE rules and store the result into a vector register.

D0.f64 = 1.0 / S0.f64

#### **Notes**

This opcode has (2**29)ULP accuracy and supports denormals.

**V_RSQ_F64**

**38**

Calculate the reciprocal of the square root of the double-precision float input using IEEE rules and store the result into a vector register.

D0.f64 = 1.0 / sqrt(S0.f64)

189 of 553

12.8. VOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture



#### **Notes**

This opcode has (2**29)ULP accuracy and supports denormals.

**V_SQRT_F32**

**39**

Calculate the square root of the single-precision float input using IEEE rules and store the result into a vector register.

D0.f32 = sqrt(S0.f32)

#### **Notes**

1ULP accuracy, denormals are flushed.

Functional examples:

V_SQRT_F32(0xff800000) => 0xffc00000     // sqrt(-INF) = NAN V_SQRT_F32(0x80000000) => 0x80000000     // sqrt(-0.0) = -0 V_SQRT_F32(0x00000000) => 0x00000000     // sqrt(+0.0) = +0 V_SQRT_F32(0x40800000) => 0x40000000     // sqrt(+4.0) = +2.0 V_SQRT_F32(0x7f800000) => 0x7f800000     // sqrt(+INF) = +INF

#### **V_SQRT_F64**

**40**

Calculate the square root of the double-precision float input using IEEE rules and store the result into a vector register.

D0.f64 = sqrt(S0.f64)

#### **Notes**

This opcode has (2**29)ULP accuracy and supports denormals.

#### **V_SIN_F32**

**41**

Calculate the trigonometric sine of a single-precision float value using IEEE rules and store the result into a vector register. The operand is calculated by scaling the vector input by 2 PI.

D0.f32 = sin(S0.f32 * 32'F(PI * 2.0))

190 of 553

12.8. VOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture



#### **Notes**

Denormals are supported. Full range input is supported.

Functional examples:

V_SIN_F32(0xff800000) => 0xffc00000     // sin(-INF) = NAN V_SIN_F32(0xff7fffff) => 0x00000000     // -MaxFloat, finite V_SIN_F32(0x80000000) => 0x80000000     // sin(-0.0) = -0 V_SIN_F32(0x3e800000) => 0x3f800000     // sin(0.25) = 1 V_SIN_F32(0x7f800000) => 0xffc00000     // sin(+INF) = NAN

**V_COS_F32 42**

Calculate the trigonometric cosine of a single-precision float value using IEEE rules and store the result into a vector register. The operand is calculated by scaling the vector input by 2 PI.

D0.f32 = cos(S0.f32 * 32'F(PI * 2.0))

#### **Notes**

Denormals are supported. Full range input is supported.

Functional examples:

V_COS_F32(0xff800000) => 0xffc00000     // cos(-INF) = NAN V_COS_F32(0xff7fffff) => 0x3f800000     // -MaxFloat, finite V_COS_F32(0x80000000) => 0x3f800000     // cos(-0.0) = 1 V_COS_F32(0x3e800000) => 0x00000000     // cos(0.25) = 0 V_COS_F32(0x7f800000) => 0xffc00000     // cos(+INF) = NAN

**V_NOT_B32**

**43**

Calculate bitwise negation on a vector input and store the result into a vector register.

D0.u32 = ~S0.u32

#### **Notes**

Input and output modifiers not supported.

**V_BFREV_B32**

**44**

191 of 553

12.8. VOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture



Reverse the order of bits in a vector input and store the result into a vector register.

D0.u32[31 : 0] = S0.u32[0 : 31]

#### **Notes**

Input and output modifiers not supported.

#### **V_FFBH_U32**

**45**

Count the number of leading "0" bits before the first "1" in a vector input and store the result into a vector register. Store -1 if there are no "1" bits.

D0.i32 = -1; // Set if no ones are found for i in 0 : 31 do // Search from MSB if S0.u32[31 - i] == 1'1U then D0.i32 = i; break endif endfor

#### **Notes**

Functional examples:

V_FFBH_U32(0x00000000) => 0xffffffff V_FFBH_U32(0x800000ff) => 0 V_FFBH_U32(0x100000ff) => 3 V_FFBH_U32(0x0000ffff) => 16 V_FFBH_U32(0x00000001) => 31

**V_FFBL_B32**

**46**

Count the number of trailing "0" bits before the first "1" in a vector input and store the result into a vector register. Store -1 if there are no "1" bits in the input.

D0.i32 = -1; // Set if no ones are found for i in 0 : 31 do // Search from LSB if S0.u32[i] == 1'1U then D0.i32 = i; break endif

192 of 553

12.8. VOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture



endfor

#### **Notes**

Functional examples:

V_FFBL_B32(0x00000000) => 0xffffffff V_FFBL_B32(0xff000001) => 0 V_FFBL_B32(0xff000008) => 3 V_FFBL_B32(0xffff0000) => 16 V_FFBL_B32(0x80000000) => 31

**V_FFBH_I32**

**47**

Count the number of leading bits that are the same as the sign bit of a vector input and store the result into a vector register. Store -1 if all input bits are the same.

D0.i32 = -1; // Set if all bits are the same for i in 1 : 31 do // Search from MSB if S0.i32[31 - i] != S0.i32[31] then D0.i32 = i; break endif endfor

#### **Notes**

Functional examples:

V_FFBH_I32(0x00000000) => 0xffffffff V_FFBH_I32(0x40000000) => 1 V_FFBH_I32(0x80000000) => 1 V_FFBH_I32(0x0fffffff) => 4 V_FFBH_I32(0xffff0000) => 16 V_FFBH_I32(0xfffffffe) => 31 V_FFBH_I32(0xffffffff) => 0xffffffff

**V_FREXP_EXP_I32_F64**

**48**

Extract the exponent of a double-precision float input and store the result as a signed 32-bit integer into a vector register.

if ((S0.f64 == +INF) || (S0.f64 == -INF) || isNAN(S0.f64)) then

193 of 553

12.8. VOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture

**49**



D0.i32 = 0 else D0.i32 = exponent(S0.f64) - 1023 + 1 endif

#### **Notes**

This operation satisfies the invariant S0.f64 = significand * (2 ** exponent). See also V_FREXP_MANT_F64, which returns the significand. See the C library function frexp() for more information.

#### **V_FREXP_MANT_F64**

Extract the binary significand, or mantissa, of a double-precision float input and store the result as a doubleprecision float into a vector register.

if ((S0.f64 == +INF) || (S0.f64 == -INF) || isNAN(S0.f64)) then D0.f64 = S0.f64 else D0.f64 = mantissa(S0.f64) endif

#### **Notes**

This operation satisfies the invariant S0.f64 = significand * (2 ** exponent). Result range is in (-1.0,-0.5][0.5,1.0) in normal cases. See also V_FREXP_EXP_I32_F64, which returns integer exponent. See the C library function frexp() for more information.

**V_FRACT_F64**

**50**

Compute the fractional portion of a double-precision float input and store the result in floating point format into a vector register.

D0.f64 = S0.f64 + -floor(S0.f64)

#### **Notes**

0.5ULP accuracy, denormals are accepted.

This is intended to comply with the DX specification of fract where the function behaves like an extension of integer modulus; be aware this may differ from how fract() is defined in other domains. For example: fract(1.2) = 0.8 in DX.

Obey round mode, result clamped to 0x3fefffffffffffff.

194 of 553

12.8. VOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture

**51**



#### **V_FREXP_EXP_I32_F32**

Extract the exponent of a single-precision float input and store the result as a signed 32-bit integer into a vector register.

if ((64'F(S0.f32) == +INF) || (64'F(S0.f32) == -INF) || isNAN(64'F(S0.f32))) then D0.i32 = 0 else D0.i32 = exponent(S0.f32) - 127 + 1 endif

#### **Notes**

This operation satisfies the invariant S0.f32 = significand * (2 ** exponent). See also V_FREXP_MANT_F32, which returns the significand. See the C library function frexp() for more information.

**V_FREXP_MANT_F32**

**52**

Extract the binary significand, or mantissa, of a single-precision float input and store the result as a singleprecision float into a vector register.

if ((64'F(S0.f32) == +INF) || (64'F(S0.f32) == -INF) || isNAN(64'F(S0.f32))) then D0.f32 = S0.f32 else D0.f32 = mantissa(S0.f32) endif

#### **Notes**

This operation satisfies the invariant S0.f32 = significand * (2 ** exponent). Result range is in (-1.0,-0.5][0.5,1.0) in normal cases. See also V_FREXP_EXP_I32_F32, which returns integer exponent. See the C library function frexp() for more information.

**V_CLREXCP 53**

Clear this wave's exception state in the vector ALU.

**V_MOV_B64 56**

Move data from a 64-bit vector input into a vector register.

D0.b64 = S0.b64

195 of 553

12.8. VOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture



#### **Notes**

Floating-point modifiers are valid for this instruction if S0.u64 is a 64-bit floating point value. This instruction is suitable for negating or taking the absolute value of a floating-point value.

**V_CVT_F16_U16 57**

Convert from an unsigned 16-bit integer input to a half-precision float value and store the result into a vector register.

D0.f16 = u16_to_f16(S0.u16)

#### **Notes**

0.5ULP accuracy, supports denormals, rounding, exception flags and saturation.

**V_CVT_F16_I16 58**

Convert from a signed 16-bit integer input to a half-precision float value and store the result into a vector register.

D0.f16 = i16_to_f16(S0.i16)

#### **Notes**

0.5ULP accuracy, supports denormals, rounding, exception flags and saturation.

**V_CVT_U16_F16 59**

Convert from a half-precision float input to an unsigned 16-bit integer value and store the result into a vector register.

D0.u16 = f16_to_u16(S0.f16)

#### **Notes**

1ULP accuracy, supports rounding, exception flags and saturation. FP16 denormals are accepted. Conversion is done with truncation.

Generation of the INEXACT exception is controlled by the CLAMP bit. INEXACT exceptions are enabled for this conversion iff CLAMP == 1.

196 of 553

12.8. VOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture

**V_CVT_I16_F16**

**60**



Convert from a half-precision float input to a signed 16-bit integer value and store the result into a vector register.

D0.i16 = f16_to_i16(S0.f16)

#### **Notes**

1ULP accuracy, supports rounding, exception flags and saturation. FP16 denormals are accepted. Conversion is done with truncation.

Generation of the INEXACT exception is controlled by the CLAMP bit. INEXACT exceptions are enabled for this conversion iff CLAMP == 1.

#### **V_RCP_F16**

**61**

Calculate the reciprocal of the half-precision float input using IEEE rules and store the result into a vector register.

D0.f16 = 16'1.0 / S0.f16

#### **Notes**

1ULP accuracy.

Functional examples:

V_RCP_F16(0xfc00) => 0x8000     // rcp(-INF) = -0 V_RCP_F16(0xc000) => 0xb800     // rcp(-2.0) = -0.5 V_RCP_F16(0x8000) => 0xfc00     // rcp(-0.0) = -INF V_RCP_F16(0x0000) => 0x7c00     // rcp(+0.0) = +INF V_RCP_F16(0x7c00) => 0x0000     // rcp(+INF) = +0

#### **V_SQRT_F16**

**62**

Calculate the square root of the half-precision float input using IEEE rules and store the result into a vector register.

D0.f16 = sqrt(S0.f16)

#### **Notes**

197 of 553

12.8. VOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture



1ULP accuracy, denormals are supported.

Functional examples:

V_SQRT_F16(0xfc00) => 0xfe00     // sqrt(-INF) = NAN V_SQRT_F16(0x8000) => 0x8000     // sqrt(-0.0) = -0 V_SQRT_F16(0x0000) => 0x0000     // sqrt(+0.0) = +0 V_SQRT_F16(0x4400) => 0x4000     // sqrt(+4.0) = +2.0 V_SQRT_F16(0x7c00) => 0x7c00     // sqrt(+INF) = +INF

**V_RSQ_F16**

**63**

Calculate the reciprocal of the square root of the half-precision float input using IEEE rules and store the result into a vector register.

D0.f16 = 16'1.0 / sqrt(S0.f16)

#### **Notes**

1ULP accuracy, denormals are supported.

Functional examples:

V_RSQ_F16(0xfc00) => 0xfe00     // rsq(-INF) = NAN V_RSQ_F16(0x8000) => 0xfc00     // rsq(-0.0) = -INF V_RSQ_F16(0x0000) => 0x7c00     // rsq(+0.0) = +INF V_RSQ_F16(0x4400) => 0x3800     // rsq(+4.0) = +0.5 V_RSQ_F16(0x7c00) => 0x0000     // rsq(+INF) = +0

**V_LOG_F16**

**64**

Calculate the base 2 logarithm of the half-precision float input and store the result into a vector register.

D0.f16 = log2(S0.f16)

#### **Notes**

1ULP accuracy, denormals are supported.

Functional examples:

V_LOG_F16(0xfc00) => 0xfe00     // log(-INF) = NAN V_LOG_F16(0xbc00) => 0xfe00     // log(-1.0) = NAN

198 of 553

12.8. VOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture

**65**



V_LOG_F16(0x8000) => 0xfc00     // log(-0.0) = -INF V_LOG_F16(0x0000) => 0xfc00     // log(+0.0) = -INF V_LOG_F16(0x3c00) => 0x0000     // log(+1.0) = 0 V_LOG_F16(0x7c00) => 0x7c00     // log(+INF) = +INF

#### **V_EXP_F16**

Calculate 2 raised to the power of the half-precision float input and store the result into a vector register.

D0.f16 = pow(16'2.0, S0.f16)

#### **Notes**

1ULP accuracy, denormals are supported.

Functional examples:

V_EXP_F16(0xfc00) => 0x0000     // exp(-INF) = 0 V_EXP_F16(0x8000) => 0x3c00     // exp(-0.0) = 1 V_EXP_F16(0x7c00) => 0x7c00     // exp(+INF) = +INF

#### **V_FREXP_MANT_F16**

**66**

Extract the binary significand, or mantissa, of a half-precision float input and store the result as a halfprecision float into a vector register.

if ((64'F(S0.f16) == +INF) || (64'F(S0.f16) == -INF) || isNAN(64'F(S0.f16))) then D0.f16 = S0.f16 else D0.f16 = mantissa(S0.f16) endif

#### **Notes**

This operation satisfies the invariant S0.f16 = significand * (2 ** exponent). Result range is in (-1.0,-0.5][0.5,1.0) in normal cases. See also V_FREXP_EXP_I16_F16, which returns integer exponent. See the C library function frexp() for more information.

**V_FREXP_EXP_I16_F16**

**67**

Extract the exponent of a half-precision float input and store the result as a signed 16-bit integer into a vector register.

199 of 553

12.8. VOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture



if ((64'F(S0.f16) == +INF) || (64'F(S0.f16) == -INF) || isNAN(64'F(S0.f16))) then D0.i16 = 16'0 else D0.i16 = 16'I(exponent(S0.f16) - 15 + 1) endif

#### **Notes**

This operation satisfies the invariant S0.f16 = significand * (2 ** exponent). See also V_FREXP_MANT_F16, which returns the significand. See the C library function frexp() for more information.

#### **V_FLOOR_F16**

**68**

Round the half-precision float input down to previous integer and store the result in floating point format into a vector register.

D0.f16 = trunc(S0.f16); if ((S0.f16 < 16'0.0) && (S0.f16 != D0.f16)) then D0.f16 += -16'1.0 endif

#### **V_CEIL_F16**

**69**

Round the half-precision float input up to next integer and store the result in floating point format into a vector register.

D0.f16 = trunc(S0.f16); if ((S0.f16 > 16'0.0) && (S0.f16 != D0.f16)) then D0.f16 += 16'1.0 endif

#### **V_TRUNC_F16**

**70**

Compute the integer part of a half-precision float input using round toward zero semantics and store the result in floating point format into a vector register.

D0.f16 = trunc(S0.f16)

**V_RNDNE_F16**

**71**

200 of 553

12.8. VOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture



Round the half-precision float input to the nearest even integer and store the result in floating point format into a vector register.

D0.f16 = floor(S0.f16 + 16'0.5); if (isEven(64'F(floor(S0.f16))) && (fract(S0.f16) == 16'0.5)) then D0.f16 -= 16'1.0 endif

**V_FRACT_F16**

**72**

Compute the fractional portion of a half-precision float input and store the result in floating point format into a vector register.

D0.f16 = S0.f16 + -floor(S0.f16)

#### **Notes**

0.5ULP accuracy, denormals are accepted.

This is intended to comply with the DX specification of fract where the function behaves like an extension of integer modulus; be aware this may differ from how fract() is defined in other domains. For example: fract(1.2) = 0.8 in DX.

#### **V_SIN_F16**

**73**

Calculate the trigonometric sine of a half-precision float value using IEEE rules and store the result into a vector register. The operand is calculated by scaling the vector input by 2 PI.

D0.f16 = sin(S0.f16 * 16'F(PI * 2.0))

#### **Notes**

Denormals are supported. Full range input is supported.

Functional examples:

V_SIN_F16(0xfc00) => 0xfe00     // sin(-INF) = NAN V_SIN_F16(0xfbff) => 0x0000     // Most negative finite FP16 V_SIN_F16(0x8000) => 0x8000     // sin(-0.0) = -0 V_SIN_F16(0x3400) => 0x3c00     // sin(0.25) = 1 V_SIN_F16(0x7bff) => 0x0000     // Most positive finite FP16 V_SIN_F16(0x7c00) => 0xfe00     // sin(+INF) = NAN

201 of 553

12.8. VOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture

**V_COS_F16**

**74**



Calculate the trigonometric cosine of a half-precision float value using IEEE rules and store the result into a vector register. The operand is calculated by scaling the vector input by 2 PI.

D0.f16 = cos(S0.f16 * 16'F(PI * 2.0))

#### **Notes**

Denormals are supported. Full range input is supported.

Functional examples:

V_COS_F16(0xfc00) => 0xfe00     // cos(-INF) = NAN V_COS_F16(0xfbff) => 0x3c00     // Most negative finite FP16 V_COS_F16(0x8000) => 0x3c00     // cos(-0.0) = 1 V_COS_F16(0x3400) => 0x0000     // cos(0.25) = 0 V_COS_F16(0x7bff) => 0x3c00     // Most positive finite FP16 V_COS_F16(0x7c00) => 0xfe00     // cos(+INF) = NAN

**V_CVT_NORM_I16_F16 77**

Convert from a half-precision float input to a signed normalized short and store the result into a vector register.

D0.i16 = f16_to_snorm(S0.f16)

#### **Notes**

0.5ULP accuracy, supports rounding, exception flags and saturation, denormals are supported.

**V_CVT_NORM_U16_F16 78**

Convert from a half-precision float input to an unsigned normalized short and store the result into a vector register.

D0.u16 = f16_to_unorm(S0.f16)

#### **Notes**

0.5ULP accuracy, supports rounding, exception flags and saturation, denormals are supported.

202 of 553

12.8. VOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture

**V_SAT_PK_U8_I16**

**79**



Given 2 signed 16-bit integer inputs, saturate each input over an unsigned 8-bit integer range, pack the resulting values into a packed 16-bit value and store the result into a vector register.

SAT8 = lambda(n) ( if n <= 16'0 then return 8'0U elsif n >= 16'255 then return 8'255U else return n[7 : 0].u8 endif); tmp = 16'0; tmp[7 : 0].u8 = SAT8(S0[15 : 0].i16); tmp[15 : 8].u8 = SAT8(S0[31 : 16].i16); D0.b16 = tmp.b16

#### **Notes**

Used for 4x16bit data packed as 4x8bit data.

**V_SWAP_B32 81**

Swap the values in two vector registers.

tmp = D0.b32; D0.b32 = S0.b32; S0.b32 = tmp

#### **Notes**

Input and output modifiers not supported; this is an untyped operation.

**V_ACCVGPR_MOV_B32 82**

Move data from one accumulator register to another accumulator register.

**V_CVT_F32_FP8 84**

Convert from an FP8 float input to a single-precision float value and store the result into a vector register.

if SDWA_SRC0_SEL == BYTE1.b3 then D0.f32 = fp8_to_f32(S0[15 : 8].fp8) elsif SDWA_SRC0_SEL == BYTE2.b3 then

203 of 553

12.8. VOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture



D0.f32 = fp8_to_f32(S0[23 : 16].fp8) elsif SDWA_SRC0_SEL == BYTE3.b3 then D0.f32 = fp8_to_f32(S0[31 : 24].fp8) else // BYTE0 implied D0.f32 = fp8_to_f32(S0[7 : 0].fp8) endif

#### **Notes**

SDWA encoding allows SRC0_SEL to control which byte of S0 is converted. Only the BYTE selects of SRC0_SEL are legal. If this instruction is not encoded in SDWA then BYTE0 is implied.

**V_CVT_F32_BF8**

**85**

Convert from a BF8 float input to a single-precision float value and store the result into a vector register.

if SDWA_SRC0_SEL == BYTE1.b3 then D0.f32 = bf8_to_f32(S0[15 : 8].bf8) elsif SDWA_SRC0_SEL == BYTE2.b3 then D0.f32 = bf8_to_f32(S0[23 : 16].bf8) elsif SDWA_SRC0_SEL == BYTE3.b3 then D0.f32 = bf8_to_f32(S0[31 : 24].bf8) else // BYTE0 implied D0.f32 = bf8_to_f32(S0[7 : 0].bf8) endif

#### **Notes**

SDWA encoding allows SRC0_SEL to control which byte of S0 is converted. Only the BYTE selects of SRC0_SEL are legal. If this instruction is not encoded in SDWA then BYTE0 is implied.

**V_CVT_PK_F32_FP8**

**86**

Convert from a packed 2-component FP8 float input to a packed single-precision float value and store the result into a vector register.

tmp = SDWA_SRC0_SEL[1 : 0] == WORD1.b2 ? S0[31 : 16] : S0[15 : 0]; D0[31 : 0].f32 = fp8_to_f32(tmp[7 : 0].fp8); D0[63 : 32].f32 = fp8_to_f32(tmp[15 : 8].fp8)

#### **Notes**

SDWA encoding allows SRC0_SEL to control which word of S0 is converted. Only the WORD selects of SRC0_SEL are legal. If this instruction is not encoded in SDWA then WORD0 is implied.

204 of 553

12.8. VOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture

**V_CVT_PK_F32_BF8**

**87**



Convert from a packed 2-component BF8 float input to a packed single-precision float value and store the result into a vector register.

tmp = SDWA_SRC0_SEL[1 : 0] == WORD1.b2 ? S0[31 : 16] : S0[15 : 0]; D0[31 : 0].f32 = bf8_to_f32(tmp[7 : 0].bf8); D0[63 : 32].f32 = bf8_to_f32(tmp[15 : 8].bf8)

#### **Notes**

SDWA encoding allows SRC0_SEL to control which word of S0 is converted. Only the WORD selects of SRC0_SEL are legal. If this instruction is not encoded in SDWA then WORD0 is implied.

205 of 553

12.8. VOP1 Instructions

"AMD Instinct MI300" Instruction Set Architecture



### **12.8.1. VOP1 using VOP3 encoding**

Instructions in this format may also be encoded as VOP3. This allows access to the extra control bits (e.g. ABS, OMOD) in exchange for not being able to use a literal constant. The VOP3 opcode is: VOP2 opcode + 0x140.





## **12.9. VOPC Instructions**

The bitfield map for VOPC is:



where: SRC0  = First operand for instruction. VSRC1 = Second operand for instruction. OP    = Instructions. All VOPC instructions can alternatively be encoded in the VOP3A format.

Compare instructions perform the same compare operation on each lane (workItem or thread) using that lane’s private data, and producing a 1 bit result per lane into VCC or EXEC.

Instructions in this format may use a 32-bit literal constant which occurs immediately after the instruction.

Most compare instructions fall into one of two categories:

- Those which can use one of 16 compare operations (floating point types). "{COMPF}"

- Those which can use one of 8 compare operations (integer types). "{COMPI}"

The opcode number is such that for these the opcode number can be calculated from a base opcode number for the data type, plus an offset for the specific compare operation.

_Table 58. Float Compare Operations_

|**Compare Operation**|**Opcode Offset**|**Description**|
|---|---|---|
|F|0|D.u = 0|
|LT|1|D.u = (S0 < S1)|
|EQ|2|D.u = (S0 == S1)|
|LE|3|D.u = (S0 <= S1)|
|GT|4|D.u = (S0 > S1)|
|LG|5|D.u = (S0 <> S1)|



206 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture



|**Compare Operation**|**Opcode Offset**|**Description**|
|---|---|---|
|GE|6|D.u = (S0 >= S1)|
|O|7|D.u = (!isNaN(S0) && !isNaN(S1))|
|U|8|D.u = (!isNaN(S0)||!isNaN(S1))|
|NGE|9|D.u = !(S0 >= S1)|
|NLG|10|D.u = !(S0 <> S1)|
|NGT|11|D.u = !(S0 > S1)|
|NLE|12|D.u = !(S0 <= S1)|
|NEQ|13|D.u = !(S0 == S1)|
|NLT|14|D.u = !(S0 < S1)|
|TRU|15|D.u = 1|



_Table 59. Instructions with Sixteen Compare Operations_

|**Instruction**|**Description**|**Hex Range**|
|---|---|---|
|V_CMP_{COMPF}_F16|16-bit float compare.|0x20 to 0x2F|
|V_CMPX_{COMPF}_F16|16-bit float compare. Also writes EXEC.|0x30 to 0x3F|
|V_CMP_{COMPF}_F32|32-bit float compare.|0x40 to 0x4F|
|V_CMPX_{COMPF}_F32|32-bit float compare. Also writes EXEC.|0x50 to 0x5F|
|V_CMPS_{COMPF}_F64|64-bit float compare.|0x60 to 0x6F|
|V_CMPSX_{COMPF}_F64|64-bit float compare. Also writes EXEC.|0x70 to 0x7F|



_Table 60. Integer Compare Operations_

|**Compare Operation**|**Opcode Offset**|**Description**|
|---|---|---|
|F|0|D.u = 0|
|LT|1|D.u = (S0 < S1)|
|EQ|2|D.u = (S0 == S1)|
|LE|3|D.u = (S0 <= S1)|
|GT|4|D.u = (S0 > S1)|
|LG|5|D.u = (S0 <> S1)|
|GE|6|D.u = (S0 >= S1)|
|TRU|7|D.u = 1|



_Table 61. Instructions with Eight Compare Operations_

|**Instruction**|**Description**|**Hex Range**|
|---|---|---|
|V_CMP_{COMPI}_I16|16-bit signed integer compare.|0xA0 - 0xA7|
|V_CMP_{COMPI}_U16|16-bit signed integer compare.|0xA8 - 0xAF|
|V_CMPX_{COMPI}_I16|16-bit unsigned integer compare. Also writes EXEC.|0xB0 - 0xB7|
|V_CMPX_{COMPI}_U16|16-bit unsigned integer compare. Also writes EXEC.|0xB8 - 0xBF|
|V_CMP_{COMPI}_I32|32-bit signed integer compare.|0xC0 - 0xC7|
|V_CMP_{COMPI}_U32|32-bit signed integer compare.|0xC8 - 0xCF|
|V_CMPX_{COMPI}_I32|32-bit unsigned integer compare. Also writes EXEC.|0xD0 - 0xD7|
|V_CMPX_{COMPI}_U32|32-bit unsigned integer compare. Also writes EXEC.|0xD8 - 0xDF|
|V_CMP_{COMPI}_I64|64-bit signed integer compare.|0xE0 - 0xE7|
|V_CMP_{COMPI}_U64|64-bit signed integer compare.|0xE8 - 0xEF|
|V_CMPX_{COMPI}_I64|64-bit unsigned integer compare. Also writes EXEC.|0xF0 - 0xF7|
|V_CMPX_{COMPI}_U64|64-bit unsigned integer compare. Also writes EXEC.|0xF8 - 0xFF|



_Table 62. VOPC Compare Opcodes_

207 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture

**V_CMP_CLASS_F32**

**16**



Evaluate the IEEE numeric class function specified as a 10 bit mask in the second input on the first input, a single-precision float, and set the per-lane condition code to the result. Store the result into VCC or a scalar register.

The function reports true if the floating point value is _any_ of the numeric types selected in the 10 bit mask according to the following list:

S1.u[0] value is a signaling NAN. S1.u[1] value is a quiet NAN. S1.u[2] value is negative infinity. S1.u[3] value is a negative normal value. S1.u[4] value is a negative denormal value. S1.u[5] value is negative zero. S1.u[6] value is positive zero. S1.u[7] value is a positive denormal value. S1.u[8] value is a positive normal value. S1.u[9] value is positive infinity.

declare result : 1'U; if isSignalNAN(64'F(S0.f32)) then result = S1.u32[0] elsif isQuietNAN(64'F(S0.f32)) then result = S1.u32[1] elsif exponent(S0.f32) == 255 then // +-INF result = S1.u32[sign(S0.f32) ? 2 : 9] elsif exponent(S0.f32) > 0 then // +-normal value result = S1.u32[sign(S0.f32) ? 3 : 8] elsif 64'F(abs(S0.f32)) > 0.0 then // +-denormal value result = S1.u32[sign(S0.f32) ? 4 : 7] else // +-0.0 result = S1.u32[sign(S0.f32) ? 5 : 6] endif; D0.u64[laneId] = result; // D0 = VCC in VOPC encoding.

#### **V_CMPX_CLASS_F32**

**17**

Evaluate the IEEE numeric class function specified as a 10 bit mask in the second input on the first input, a single-precision float, and set the per-lane condition code to the result. Store the result into the EXEC mask and to VCC or a scalar register.

The function reports true if the floating point value is _any_ of the numeric types selected in the 10 bit mask according to the following list:

208 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture

**18**



S1.u[0] value is a signaling NAN. S1.u[1] value is a quiet NAN. S1.u[2] value is negative infinity. S1.u[3] value is a negative normal value. S1.u[4] value is a negative denormal value. S1.u[5] value is negative zero. S1.u[6] value is positive zero. S1.u[7] value is a positive denormal value. S1.u[8] value is a positive normal value. S1.u[9] value is positive infinity.

declare result : 1'U; if isSignalNAN(64'F(S0.f32)) then result = S1.u32[0] elsif isQuietNAN(64'F(S0.f32)) then result = S1.u32[1] elsif exponent(S0.f32) == 255 then // +-INF result = S1.u32[sign(S0.f32) ? 2 : 9] elsif exponent(S0.f32) > 0 then // +-normal value result = S1.u32[sign(S0.f32) ? 3 : 8] elsif 64'F(abs(S0.f32)) > 0.0 then // +-denormal value result = S1.u32[sign(S0.f32) ? 4 : 7] else // +-0.0 result = S1.u32[sign(S0.f32) ? 5 : 6] endif; EXEC.u64[laneId] = D0.u64[laneId] = result

**V_CMP_CLASS_F64**

Evaluate the IEEE numeric class function specified as a 10 bit mask in the second input on the first input, a double-precision float, and set the per-lane condition code to the result. Store the result into VCC or a scalar register.

The function reports true if the floating point value is _any_ of the numeric types selected in the 10 bit mask according to the following list:

S1.u[0] value is a signaling NAN. S1.u[1] value is a quiet NAN. S1.u[2] value is negative infinity. S1.u[3] value is a negative normal value. S1.u[4] value is a negative denormal value. S1.u[5] value is negative zero. S1.u[6] value is positive zero. S1.u[7] value is a positive denormal value. S1.u[8] value is a positive normal value. S1.u[9] value is positive infinity.

209 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture

**19**



declare result : 1'U; if isSignalNAN(S0.f64) then result = S1.u32[0] elsif isQuietNAN(S0.f64) then result = S1.u32[1] elsif exponent(S0.f64) == 2047 then // +-INF result = S1.u32[sign(S0.f64) ? 2 : 9] elsif exponent(S0.f64) > 0 then // +-normal value result = S1.u32[sign(S0.f64) ? 3 : 8] elsif abs(S0.f64) > 0.0 then // +-denormal value result = S1.u32[sign(S0.f64) ? 4 : 7] else // +-0.0 result = S1.u32[sign(S0.f64) ? 5 : 6] endif; D0.u64[laneId] = result; // D0 = VCC in VOPC encoding.

#### **V_CMPX_CLASS_F64**

Evaluate the IEEE numeric class function specified as a 10 bit mask in the second input on the first input, a double-precision float, and set the per-lane condition code to the result. Store the result into the EXEC mask and to VCC or a scalar register.

The function reports true if the floating point value is _any_ of the numeric types selected in the 10 bit mask according to the following list:

S1.u[0] value is a signaling NAN. S1.u[1] value is a quiet NAN. S1.u[2] value is negative infinity. S1.u[3] value is a negative normal value. S1.u[4] value is a negative denormal value. S1.u[5] value is negative zero. S1.u[6] value is positive zero. S1.u[7] value is a positive denormal value. S1.u[8] value is a positive normal value. S1.u[9] value is positive infinity.

declare result : 1'U; if isSignalNAN(S0.f64) then result = S1.u32[0] elsif isQuietNAN(S0.f64) then result = S1.u32[1] elsif exponent(S0.f64) == 2047 then // +-INF result = S1.u32[sign(S0.f64) ? 2 : 9] elsif exponent(S0.f64) > 0 then // +-normal value

210 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture



result = S1.u32[sign(S0.f64) ? 3 : 8] elsif abs(S0.f64) > 0.0 then // +-denormal value result = S1.u32[sign(S0.f64) ? 4 : 7] else // +-0.0 result = S1.u32[sign(S0.f64) ? 5 : 6] endif; EXEC.u64[laneId] = D0.u64[laneId] = result

#### **V_CMP_CLASS_F16**

**20**

Evaluate the IEEE numeric class function specified as a 10 bit mask in the second input on the first input, a half-precision float, and set the per-lane condition code to the result. Store the result into VCC or a scalar register.

The function reports true if the floating point value is _any_ of the numeric types selected in the 10 bit mask according to the following list:

S1.u[0] value is a signaling NAN. S1.u[1] value is a quiet NAN. S1.u[2] value is negative infinity. S1.u[3] value is a negative normal value. S1.u[4] value is a negative denormal value. S1.u[5] value is negative zero. S1.u[6] value is positive zero. S1.u[7] value is a positive denormal value. S1.u[8] value is a positive normal value. S1.u[9] value is positive infinity.

declare result : 1'U; if isSignalNAN(64'F(S0.f16)) then result = S1.u32[0] elsif isQuietNAN(64'F(S0.f16)) then result = S1.u32[1] elsif exponent(S0.f16) == 31 then // +-INF result = S1.u32[sign(S0.f16) ? 2 : 9] elsif exponent(S0.f16) > 0 then // +-normal value result = S1.u32[sign(S0.f16) ? 3 : 8] elsif 64'F(abs(S0.f16)) > 0.0 then // +-denormal value result = S1.u32[sign(S0.f16) ? 4 : 7] else // +-0.0 result = S1.u32[sign(S0.f16) ? 5 : 6] endif; D0.u64[laneId] = result; // D0 = VCC in VOPC encoding.

211 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture

**21**



#### **Notes**

Note that the S1 has a format of f16 since floating point literal constants are interpreted as 16 bit value for this opcode.

#### **V_CMPX_CLASS_F16**

Evaluate the IEEE numeric class function specified as a 10 bit mask in the second input on the first input, a half-precision float, and set the per-lane condition code to the result. Store the result into the EXEC mask and to VCC or a scalar register.

The function reports true if the floating point value is _any_ of the numeric types selected in the 10 bit mask according to the following list:

S1.u[0] value is a signaling NAN. S1.u[1] value is a quiet NAN. S1.u[2] value is negative infinity. S1.u[3] value is a negative normal value. S1.u[4] value is a negative denormal value. S1.u[5] value is negative zero. S1.u[6] value is positive zero. S1.u[7] value is a positive denormal value. S1.u[8] value is a positive normal value. S1.u[9] value is positive infinity.

declare result : 1'U; if isSignalNAN(64'F(S0.f16)) then result = S1.u32[0] elsif isQuietNAN(64'F(S0.f16)) then result = S1.u32[1] elsif exponent(S0.f16) == 31 then // +-INF result = S1.u32[sign(S0.f16) ? 2 : 9] elsif exponent(S0.f16) > 0 then // +-normal value result = S1.u32[sign(S0.f16) ? 3 : 8] elsif 64'F(abs(S0.f16)) > 0.0 then // +-denormal value result = S1.u32[sign(S0.f16) ? 4 : 7] else // +-0.0 result = S1.u32[sign(S0.f16) ? 5 : 6] endif; EXEC.u64[laneId] = D0.u64[laneId] = result

#### **Notes**

Note that the S1 has a format of f16 since floating point literal constants are interpreted as 16 bit value for this opcode.

212 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture

**V_CMP_F_F16**

**32**



Set the per-lane condition code to 0. Store the result into VCC or a scalar register.

D0.u64[laneId] = 1'0U; // D0 = VCC in VOPC encoding.

#### **V_CMP_LT_F16**

**33**

Set the per-lane condition code to 1 iff the first input is less than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.f16 < S1.f16; // D0 = VCC in VOPC encoding.

#### **V_CMP_EQ_F16**

**34**

Set the per-lane condition code to 1 iff the first input is equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.f16 == S1.f16; // D0 = VCC in VOPC encoding.

#### **V_CMP_LE_F16**

**35**

Set the per-lane condition code to 1 iff the first input is less than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.f16 <= S1.f16; // D0 = VCC in VOPC encoding.

#### **V_CMP_GT_F16**

**36**

Set the per-lane condition code to 1 iff the first input is greater than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.f16 > S1.f16; // D0 = VCC in VOPC encoding.

213 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture



**V_CMP_LG_F16**

**37**

Set the per-lane condition code to 1 iff the first input is less than or greater than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.f16 <> S1.f16; // D0 = VCC in VOPC encoding.

**V_CMP_GE_F16 38**

Set the per-lane condition code to 1 iff the first input is greater than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.f16 >= S1.f16; // D0 = VCC in VOPC encoding.

**V_CMP_O_F16 39**

Set the per-lane condition code to 1 iff the first input is orderable to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = (!isNAN(64'F(S0.f16)) && !isNAN(64'F(S1.f16))); // D0 = VCC in VOPC encoding.

**V_CMP_U_F16 40**

Set the per-lane condition code to 1 iff the first input is not orderable to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = (isNAN(64'F(S0.f16)) || isNAN(64'F(S1.f16))); // D0 = VCC in VOPC encoding.

**V_CMP_NGE_F16 41**

Set the per-lane condition code to 1 iff the first input is not greater than or equal to the second input. Store the result into VCC or a scalar register.

214 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture

**42**



D0.u64[laneId] = !(S0.f16 >= S1.f16); // With NAN inputs this is not the same operation as < // D0 = VCC in VOPC encoding.

#### **V_CMP_NLG_F16**

Set the per-lane condition code to 1 iff the first input is not less than or greater than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = !(S0.f16 <> S1.f16); // With NAN inputs this is not the same operation as == // D0 = VCC in VOPC encoding.

#### **V_CMP_NGT_F16**

**43**

Set the per-lane condition code to 1 iff the first input is not greater than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = !(S0.f16 > S1.f16); // With NAN inputs this is not the same operation as <= // D0 = VCC in VOPC encoding.

#### **V_CMP_NLE_F16**

**44**

Set the per-lane condition code to 1 iff the first input is not less than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = !(S0.f16 <= S1.f16); // With NAN inputs this is not the same operation as > // D0 = VCC in VOPC encoding.

#### **V_CMP_NEQ_F16**

**45**

Set the per-lane condition code to 1 iff the first input is not equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = !(S0.f16 == S1.f16);

// With NAN inputs this is not the same operation as !=

215 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture



// D0 = VCC in VOPC encoding.

#### **V_CMP_NLT_F16**

**46**

Set the per-lane condition code to 1 iff the first input is not less than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = !(S0.f16 < S1.f16); // With NAN inputs this is not the same operation as >= // D0 = VCC in VOPC encoding.

#### **V_CMP_TRU_F16**

**47**

Set the per-lane condition code to 1. Store the result into VCC or a scalar register.

D0.u64[laneId] = 1'1U; // D0 = VCC in VOPC encoding.

#### **V_CMPX_F_F16**

**48**

Set the per-lane condition code to 0. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = 1'0U; // D0 = VCC in VOPC encoding.

#### **V_CMPX_LT_F16**

**49**

Set the per-lane condition code to 1 iff the first input is less than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.f16 < S1.f16; // D0 = VCC in VOPC encoding.

#### **V_CMPX_EQ_F16**

**50**

Set the per-lane condition code to 1 iff the first input is equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

216 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture

**51**



EXEC.u64[laneId] = D0.u64[laneId] = S0.f16 == S1.f16; // D0 = VCC in VOPC encoding.

#### **V_CMPX_LE_F16**

Set the per-lane condition code to 1 iff the first input is less than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.f16 <= S1.f16; // D0 = VCC in VOPC encoding.

#### **V_CMPX_GT_F16**

**52**

Set the per-lane condition code to 1 iff the first input is greater than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.f16 > S1.f16; // D0 = VCC in VOPC encoding.

#### **V_CMPX_LG_F16**

**53**

Set the per-lane condition code to 1 iff the first input is less than or greater than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.f16 <> S1.f16; // D0 = VCC in VOPC encoding.

#### **V_CMPX_GE_F16**

**54**

Set the per-lane condition code to 1 iff the first input is greater than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.f16 >= S1.f16; // D0 = VCC in VOPC encoding.

**V_CMPX_O_F16**

**55**

217 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture



Set the per-lane condition code to 1 iff the first input is orderable to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = (!isNAN(64'F(S0.f16)) && !isNAN(64'F(S1.f16))); // D0 = VCC in VOPC encoding.

#### **V_CMPX_U_F16**

**56**

Set the per-lane condition code to 1 iff the first input is not orderable to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = (isNAN(64'F(S0.f16)) || isNAN(64'F(S1.f16))); // D0 = VCC in VOPC encoding.

#### **V_CMPX_NGE_F16**

**57**

Set the per-lane condition code to 1 iff the first input is not greater than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = !(S0.f16 >= S1.f16); // With NAN inputs this is not the same operation as < // D0 = VCC in VOPC encoding.

#### **V_CMPX_NLG_F16**

**58**

Set the per-lane condition code to 1 iff the first input is not less than or greater than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = !(S0.f16 <> S1.f16); // With NAN inputs this is not the same operation as == // D0 = VCC in VOPC encoding.

#### **V_CMPX_NGT_F16**

**59**

Set the per-lane condition code to 1 iff the first input is not greater than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = !(S0.f16 > S1.f16); // With NAN inputs this is not the same operation as <=

218 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture



// D0 = VCC in VOPC encoding.

#### **V_CMPX_NLE_F16**

**60**

Set the per-lane condition code to 1 iff the first input is not less than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = !(S0.f16 <= S1.f16); // With NAN inputs this is not the same operation as > // D0 = VCC in VOPC encoding.

#### **V_CMPX_NEQ_F16**

**61**

Set the per-lane condition code to 1 iff the first input is not equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = !(S0.f16 == S1.f16); // With NAN inputs this is not the same operation as != // D0 = VCC in VOPC encoding.

#### **V_CMPX_NLT_F16**

**62**

Set the per-lane condition code to 1 iff the first input is not less than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = !(S0.f16 < S1.f16); // With NAN inputs this is not the same operation as >= // D0 = VCC in VOPC encoding.

#### **V_CMPX_TRU_F16**

**63**

Set the per-lane condition code to 1. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = 1'1U; // D0 = VCC in VOPC encoding.

**V_CMP_F_F32**

**64**

219 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture



Set the per-lane condition code to 0. Store the result into VCC or a scalar register.

D0.u64[laneId] = 1'0U; // D0 = VCC in VOPC encoding.

#### **V_CMP_LT_F32**

**65**

Set the per-lane condition code to 1 iff the first input is less than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.f32 < S1.f32; // D0 = VCC in VOPC encoding.

#### **V_CMP_EQ_F32**

**66**

Set the per-lane condition code to 1 iff the first input is equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.f32 == S1.f32; // D0 = VCC in VOPC encoding.

#### **V_CMP_LE_F32**

**67**

Set the per-lane condition code to 1 iff the first input is less than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.f32 <= S1.f32; // D0 = VCC in VOPC encoding.

#### **V_CMP_GT_F32**

**68**

Set the per-lane condition code to 1 iff the first input is greater than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.f32 > S1.f32; // D0 = VCC in VOPC encoding.

220 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture

**V_CMP_LG_F32**

**69**



Set the per-lane condition code to 1 iff the first input is less than or greater than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.f32 <> S1.f32; // D0 = VCC in VOPC encoding.

**V_CMP_GE_F32 70**

Set the per-lane condition code to 1 iff the first input is greater than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.f32 >= S1.f32; // D0 = VCC in VOPC encoding.

**V_CMP_O_F32 71**

Set the per-lane condition code to 1 iff the first input is orderable to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = (!isNAN(64'F(S0.f32)) && !isNAN(64'F(S1.f32))); // D0 = VCC in VOPC encoding.

**V_CMP_U_F32 72**

Set the per-lane condition code to 1 iff the first input is not orderable to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = (isNAN(64'F(S0.f32)) || isNAN(64'F(S1.f32))); // D0 = VCC in VOPC encoding.

#### **V_CMP_NGE_F32**

**73**

Set the per-lane condition code to 1 iff the first input is not greater than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = !(S0.f32 >= S1.f32);

221 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture



// With NAN inputs this is not the same operation as <

// D0 = VCC in VOPC encoding.

#### **V_CMP_NLG_F32**

**74**

Set the per-lane condition code to 1 iff the first input is not less than or greater than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = !(S0.f32 <> S1.f32);

// With NAN inputs this is not the same operation as == // D0 = VCC in VOPC encoding.

#### **V_CMP_NGT_F32**

**75**

Set the per-lane condition code to 1 iff the first input is not greater than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = !(S0.f32 > S1.f32); // With NAN inputs this is not the same operation as <= // D0 = VCC in VOPC encoding.

#### **V_CMP_NLE_F32**

**76**

Set the per-lane condition code to 1 iff the first input is not less than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = !(S0.f32 <= S1.f32); // With NAN inputs this is not the same operation as > // D0 = VCC in VOPC encoding.

#### **V_CMP_NEQ_F32**

**77**

Set the per-lane condition code to 1 iff the first input is not equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = !(S0.f32 == S1.f32);

// With NAN inputs this is not the same operation as !=

// D0 = VCC in VOPC encoding.

222 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture

**78**



#### **V_CMP_NLT_F32**

Set the per-lane condition code to 1 iff the first input is not less than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = !(S0.f32 < S1.f32); // With NAN inputs this is not the same operation as >= // D0 = VCC in VOPC encoding.

#### **V_CMP_TRU_F32**

**79**

Set the per-lane condition code to 1. Store the result into VCC or a scalar register.

D0.u64[laneId] = 1'1U; // D0 = VCC in VOPC encoding.

#### **V_CMPX_F_F32**

**80**

Set the per-lane condition code to 0. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = 1'0U; // D0 = VCC in VOPC encoding.

#### **V_CMPX_LT_F32**

**81**

Set the per-lane condition code to 1 iff the first input is less than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.f32 < S1.f32; // D0 = VCC in VOPC encoding.

#### **V_CMPX_EQ_F32**

**82**

Set the per-lane condition code to 1 iff the first input is equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.f32 == S1.f32;

223 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture



// D0 = VCC in VOPC encoding.

#### **V_CMPX_LE_F32**

**83**

Set the per-lane condition code to 1 iff the first input is less than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.f32 <= S1.f32; // D0 = VCC in VOPC encoding.

#### **V_CMPX_GT_F32**

**84**

Set the per-lane condition code to 1 iff the first input is greater than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.f32 > S1.f32; // D0 = VCC in VOPC encoding.

#### **V_CMPX_LG_F32**

**85**

Set the per-lane condition code to 1 iff the first input is less than or greater than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.f32 <> S1.f32; // D0 = VCC in VOPC encoding.

#### **V_CMPX_GE_F32**

**86**

Set the per-lane condition code to 1 iff the first input is greater than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.f32 >= S1.f32; // D0 = VCC in VOPC encoding.

**V_CMPX_O_F32**

**87**

Set the per-lane condition code to 1 iff the first input is orderable to the second input. Store the result into the

224 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture



EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = (!isNAN(64'F(S0.f32)) && !isNAN(64'F(S1.f32))); // D0 = VCC in VOPC encoding.

#### **V_CMPX_U_F32**

**88**

Set the per-lane condition code to 1 iff the first input is not orderable to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = (isNAN(64'F(S0.f32)) || isNAN(64'F(S1.f32))); // D0 = VCC in VOPC encoding.

#### **V_CMPX_NGE_F32**

**89**

Set the per-lane condition code to 1 iff the first input is not greater than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = !(S0.f32 >= S1.f32); // With NAN inputs this is not the same operation as < // D0 = VCC in VOPC encoding.

#### **V_CMPX_NLG_F32**

**90**

Set the per-lane condition code to 1 iff the first input is not less than or greater than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = !(S0.f32 <> S1.f32); // With NAN inputs this is not the same operation as == // D0 = VCC in VOPC encoding.

#### **V_CMPX_NGT_F32**

**91**

Set the per-lane condition code to 1 iff the first input is not greater than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = !(S0.f32 > S1.f32); // With NAN inputs this is not the same operation as <=

225 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture



// D0 = VCC in VOPC encoding.

#### **V_CMPX_NLE_F32**

**92**

Set the per-lane condition code to 1 iff the first input is not less than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = !(S0.f32 <= S1.f32); // With NAN inputs this is not the same operation as > // D0 = VCC in VOPC encoding.

#### **V_CMPX_NEQ_F32**

**93**

Set the per-lane condition code to 1 iff the first input is not equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = !(S0.f32 == S1.f32); // With NAN inputs this is not the same operation as != // D0 = VCC in VOPC encoding.

#### **V_CMPX_NLT_F32**

**94**

Set the per-lane condition code to 1 iff the first input is not less than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = !(S0.f32 < S1.f32); // With NAN inputs this is not the same operation as >= // D0 = VCC in VOPC encoding.

#### **V_CMPX_TRU_F32**

**95**

Set the per-lane condition code to 1. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = 1'1U; // D0 = VCC in VOPC encoding.

**V_CMP_F_F64**

**96**

226 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture



Set the per-lane condition code to 0. Store the result into VCC or a scalar register.

D0.u64[laneId] = 1'0U; // D0 = VCC in VOPC encoding.

#### **V_CMP_LT_F64**

**97**

Set the per-lane condition code to 1 iff the first input is less than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.f64 < S1.f64; // D0 = VCC in VOPC encoding.

#### **V_CMP_EQ_F64**

**98**

Set the per-lane condition code to 1 iff the first input is equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.f64 == S1.f64; // D0 = VCC in VOPC encoding.

#### **V_CMP_LE_F64**

**99**

Set the per-lane condition code to 1 iff the first input is less than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.f64 <= S1.f64; // D0 = VCC in VOPC encoding.

#### **V_CMP_GT_F64**

**100**

Set the per-lane condition code to 1 iff the first input is greater than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.f64 > S1.f64; // D0 = VCC in VOPC encoding.

227 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture

**101**



#### **V_CMP_LG_F64**

Set the per-lane condition code to 1 iff the first input is less than or greater than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.f64 <> S1.f64; // D0 = VCC in VOPC encoding.

**V_CMP_GE_F64 102**

Set the per-lane condition code to 1 iff the first input is greater than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.f64 >= S1.f64; // D0 = VCC in VOPC encoding.

**V_CMP_O_F64 103**

Set the per-lane condition code to 1 iff the first input is orderable to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = (!isNAN(S0.f64) && !isNAN(S1.f64)); // D0 = VCC in VOPC encoding.

**V_CMP_U_F64 104**

Set the per-lane condition code to 1 iff the first input is not orderable to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = (isNAN(S0.f64) || isNAN(S1.f64)); // D0 = VCC in VOPC encoding.

#### **V_CMP_NGE_F64**

**105**

Set the per-lane condition code to 1 iff the first input is not greater than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = !(S0.f64 >= S1.f64);

228 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture



// With NAN inputs this is not the same operation as <

// D0 = VCC in VOPC encoding.

#### **V_CMP_NLG_F64**

**106**

Set the per-lane condition code to 1 iff the first input is not less than or greater than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = !(S0.f64 <> S1.f64);

// With NAN inputs this is not the same operation as == // D0 = VCC in VOPC encoding.

#### **V_CMP_NGT_F64**

**107**

Set the per-lane condition code to 1 iff the first input is not greater than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = !(S0.f64 > S1.f64); // With NAN inputs this is not the same operation as <= // D0 = VCC in VOPC encoding.

#### **V_CMP_NLE_F64**

**108**

Set the per-lane condition code to 1 iff the first input is not less than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = !(S0.f64 <= S1.f64); // With NAN inputs this is not the same operation as > // D0 = VCC in VOPC encoding.

#### **V_CMP_NEQ_F64**

**109**

Set the per-lane condition code to 1 iff the first input is not equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = !(S0.f64 == S1.f64);

// With NAN inputs this is not the same operation as !=

// D0 = VCC in VOPC encoding.

229 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture

**V_CMP_NLT_F64**

**110**



Set the per-lane condition code to 1 iff the first input is not less than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = !(S0.f64 < S1.f64); // With NAN inputs this is not the same operation as >= // D0 = VCC in VOPC encoding.

#### **V_CMP_TRU_F64**

**111**

Set the per-lane condition code to 1. Store the result into VCC or a scalar register.

D0.u64[laneId] = 1'1U; // D0 = VCC in VOPC encoding.

#### **V_CMPX_F_F64**

**112**

Set the per-lane condition code to 0. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = 1'0U; // D0 = VCC in VOPC encoding.

#### **V_CMPX_LT_F64**

**113**

Set the per-lane condition code to 1 iff the first input is less than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.f64 < S1.f64; // D0 = VCC in VOPC encoding.

#### **V_CMPX_EQ_F64**

**114**

Set the per-lane condition code to 1 iff the first input is equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.f64 == S1.f64;

230 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture



// D0 = VCC in VOPC encoding.

#### **V_CMPX_LE_F64**

**115**

Set the per-lane condition code to 1 iff the first input is less than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.f64 <= S1.f64; // D0 = VCC in VOPC encoding.

#### **V_CMPX_GT_F64**

**116**

Set the per-lane condition code to 1 iff the first input is greater than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.f64 > S1.f64; // D0 = VCC in VOPC encoding.

#### **V_CMPX_LG_F64**

**117**

Set the per-lane condition code to 1 iff the first input is less than or greater than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.f64 <> S1.f64; // D0 = VCC in VOPC encoding.

#### **V_CMPX_GE_F64**

**118**

Set the per-lane condition code to 1 iff the first input is greater than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.f64 >= S1.f64; // D0 = VCC in VOPC encoding.

**V_CMPX_O_F64**

**119**

Set the per-lane condition code to 1 iff the first input is orderable to the second input. Store the result into the

231 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture

**120**



EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = (!isNAN(S0.f64) && !isNAN(S1.f64)); // D0 = VCC in VOPC encoding.

#### **V_CMPX_U_F64**

Set the per-lane condition code to 1 iff the first input is not orderable to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = (isNAN(S0.f64) || isNAN(S1.f64)); // D0 = VCC in VOPC encoding.

#### **V_CMPX_NGE_F64**

**121**

Set the per-lane condition code to 1 iff the first input is not greater than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = !(S0.f64 >= S1.f64); // With NAN inputs this is not the same operation as < // D0 = VCC in VOPC encoding.

#### **V_CMPX_NLG_F64**

**122**

Set the per-lane condition code to 1 iff the first input is not less than or greater than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = !(S0.f64 <> S1.f64); // With NAN inputs this is not the same operation as == // D0 = VCC in VOPC encoding.

#### **V_CMPX_NGT_F64**

**123**

Set the per-lane condition code to 1 iff the first input is not greater than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = !(S0.f64 > S1.f64); // With NAN inputs this is not the same operation as <=

232 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture



// D0 = VCC in VOPC encoding.

#### **V_CMPX_NLE_F64**

**124**

Set the per-lane condition code to 1 iff the first input is not less than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = !(S0.f64 <= S1.f64); // With NAN inputs this is not the same operation as > // D0 = VCC in VOPC encoding.

#### **V_CMPX_NEQ_F64**

**125**

Set the per-lane condition code to 1 iff the first input is not equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = !(S0.f64 == S1.f64); // With NAN inputs this is not the same operation as != // D0 = VCC in VOPC encoding.

#### **V_CMPX_NLT_F64**

**126**

Set the per-lane condition code to 1 iff the first input is not less than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = !(S0.f64 < S1.f64); // With NAN inputs this is not the same operation as >= // D0 = VCC in VOPC encoding.

#### **V_CMPX_TRU_F64**

**127**

Set the per-lane condition code to 1. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = 1'1U; // D0 = VCC in VOPC encoding.

**V_CMP_F_I16**

**160**

233 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture



Set the per-lane condition code to 0. Store the result into VCC or a scalar register.

D0.u64[laneId] = 1'0U; // D0 = VCC in VOPC encoding.

#### **V_CMP_LT_I16**

**161**

Set the per-lane condition code to 1 iff the first input is less than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.i16 < S1.i16; // D0 = VCC in VOPC encoding.

#### **V_CMP_EQ_I16**

**162**

Set the per-lane condition code to 1 iff the first input is equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.i16 == S1.i16; // D0 = VCC in VOPC encoding.

#### **V_CMP_LE_I16**

**163**

Set the per-lane condition code to 1 iff the first input is less than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.i16 <= S1.i16; // D0 = VCC in VOPC encoding.

#### **V_CMP_GT_I16**

**164**

Set the per-lane condition code to 1 iff the first input is greater than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.i16 > S1.i16; // D0 = VCC in VOPC encoding.

234 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture

**165**



#### **V_CMP_NE_I16**

Set the per-lane condition code to 1 iff the first input is not equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.i16 <> S1.i16; // D0 = VCC in VOPC encoding.

#### **V_CMP_GE_I16**

**166**

Set the per-lane condition code to 1 iff the first input is greater than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.i16 >= S1.i16; // D0 = VCC in VOPC encoding.

**V_CMP_T_I16 167**

Set the per-lane condition code to 1. Store the result into VCC or a scalar register.

D0.u64[laneId] = 1'1U; // D0 = VCC in VOPC encoding.

**V_CMP_F_U16 168**

Set the per-lane condition code to 0. Store the result into VCC or a scalar register.

D0.u64[laneId] = 1'0U; // D0 = VCC in VOPC encoding.

#### **V_CMP_LT_U16**

**169**

Set the per-lane condition code to 1 iff the first input is less than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.u16 < S1.u16; // D0 = VCC in VOPC encoding.

235 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture

**170**



#### **V_CMP_EQ_U16**

Set the per-lane condition code to 1 iff the first input is equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.u16 == S1.u16; // D0 = VCC in VOPC encoding.

#### **V_CMP_LE_U16**

**171**

Set the per-lane condition code to 1 iff the first input is less than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.u16 <= S1.u16; // D0 = VCC in VOPC encoding.

#### **V_CMP_GT_U16**

**172**

Set the per-lane condition code to 1 iff the first input is greater than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.u16 > S1.u16; // D0 = VCC in VOPC encoding.

#### **V_CMP_NE_U16**

**173**

Set the per-lane condition code to 1 iff the first input is not equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.u16 <> S1.u16; // D0 = VCC in VOPC encoding.

#### **V_CMP_GE_U16**

**174**

Set the per-lane condition code to 1 iff the first input is greater than or equal to the second input. Store the result into VCC or a scalar register.

236 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture

**175**



D0.u64[laneId] = S0.u16 >= S1.u16; // D0 = VCC in VOPC encoding.

#### **V_CMP_T_U16**

Set the per-lane condition code to 1. Store the result into VCC or a scalar register.

D0.u64[laneId] = 1'1U; // D0 = VCC in VOPC encoding.

#### **V_CMPX_F_I16**

**176**

Set the per-lane condition code to 0. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = 1'0U; // D0 = VCC in VOPC encoding.

#### **V_CMPX_LT_I16**

**177**

Set the per-lane condition code to 1 iff the first input is less than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.i16 < S1.i16; // D0 = VCC in VOPC encoding.

#### **V_CMPX_EQ_I16**

**178**

Set the per-lane condition code to 1 iff the first input is equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.i16 == S1.i16; // D0 = VCC in VOPC encoding.

#### **V_CMPX_LE_I16**

**179**

Set the per-lane condition code to 1 iff the first input is less than or equal to the second input. Store the result

237 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture

**180**



into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.i16 <= S1.i16; // D0 = VCC in VOPC encoding.

#### **V_CMPX_GT_I16**

Set the per-lane condition code to 1 iff the first input is greater than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.i16 > S1.i16; // D0 = VCC in VOPC encoding.

#### **V_CMPX_NE_I16**

**181**

Set the per-lane condition code to 1 iff the first input is not equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.i16 <> S1.i16; // D0 = VCC in VOPC encoding.

#### **V_CMPX_GE_I16**

**182**

Set the per-lane condition code to 1 iff the first input is greater than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.i16 >= S1.i16; // D0 = VCC in VOPC encoding.

#### **V_CMPX_T_I16**

**183**

Set the per-lane condition code to 1. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = 1'1U; // D0 = VCC in VOPC encoding.

238 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture

**V_CMPX_F_U16**

**184**



Set the per-lane condition code to 0. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = 1'0U; // D0 = VCC in VOPC encoding.

#### **V_CMPX_LT_U16**

**185**

Set the per-lane condition code to 1 iff the first input is less than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.u16 < S1.u16; // D0 = VCC in VOPC encoding.

#### **V_CMPX_EQ_U16**

**186**

Set the per-lane condition code to 1 iff the first input is equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.u16 == S1.u16; // D0 = VCC in VOPC encoding.

#### **V_CMPX_LE_U16**

**187**

Set the per-lane condition code to 1 iff the first input is less than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.u16 <= S1.u16; // D0 = VCC in VOPC encoding.

#### **V_CMPX_GT_U16**

**188**

Set the per-lane condition code to 1 iff the first input is greater than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.u16 > S1.u16; // D0 = VCC in VOPC encoding.

239 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture

**189**



#### **V_CMPX_NE_U16**

Set the per-lane condition code to 1 iff the first input is not equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.u16 <> S1.u16; // D0 = VCC in VOPC encoding.

**V_CMPX_GE_U16**

**190**

Set the per-lane condition code to 1 iff the first input is greater than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.u16 >= S1.u16; // D0 = VCC in VOPC encoding.

**V_CMPX_T_U16**

**191**

Set the per-lane condition code to 1. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = 1'1U; // D0 = VCC in VOPC encoding.

**V_CMP_F_I32 192**

Set the per-lane condition code to 0. Store the result into VCC or a scalar register.

D0.u64[laneId] = 1'0U; // D0 = VCC in VOPC encoding.

**V_CMP_LT_I32**

**193**

Set the per-lane condition code to 1 iff the first input is less than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.i32 < S1.i32;

240 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture



// D0 = VCC in VOPC encoding.

**V_CMP_EQ_I32**

**194**

Set the per-lane condition code to 1 iff the first input is equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.i32 == S1.i32; // D0 = VCC in VOPC encoding.

#### **V_CMP_LE_I32**

**195**

Set the per-lane condition code to 1 iff the first input is less than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.i32 <= S1.i32; // D0 = VCC in VOPC encoding.

#### **V_CMP_GT_I32**

**196**

Set the per-lane condition code to 1 iff the first input is greater than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.i32 > S1.i32; // D0 = VCC in VOPC encoding.

#### **V_CMP_NE_I32**

**197**

Set the per-lane condition code to 1 iff the first input is not equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.i32 <> S1.i32; // D0 = VCC in VOPC encoding.

**V_CMP_GE_I32**

**198**

Set the per-lane condition code to 1 iff the first input is greater than or equal to the second input. Store the

241 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture



result into VCC or a scalar register.

D0.u64[laneId] = S0.i32 >= S1.i32; // D0 = VCC in VOPC encoding.

#### **V_CMP_T_I32**

**199**

Set the per-lane condition code to 1. Store the result into VCC or a scalar register.

D0.u64[laneId] = 1'1U; // D0 = VCC in VOPC encoding.

**V_CMP_F_U32**

**200**

Set the per-lane condition code to 0. Store the result into VCC or a scalar register.

D0.u64[laneId] = 1'0U; // D0 = VCC in VOPC encoding.

#### **V_CMP_LT_U32**

**201**

Set the per-lane condition code to 1 iff the first input is less than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.u32 < S1.u32; // D0 = VCC in VOPC encoding.

#### **V_CMP_EQ_U32**

**202**

Set the per-lane condition code to 1 iff the first input is equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.u32 == S1.u32; // D0 = VCC in VOPC encoding.

**V_CMP_LE_U32**

**203**

242 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture



Set the per-lane condition code to 1 iff the first input is less than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.u32 <= S1.u32; // D0 = VCC in VOPC encoding.

#### **V_CMP_GT_U32**

**204**

Set the per-lane condition code to 1 iff the first input is greater than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.u32 > S1.u32; // D0 = VCC in VOPC encoding.

#### **V_CMP_NE_U32**

**205**

Set the per-lane condition code to 1 iff the first input is not equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.u32 <> S1.u32; // D0 = VCC in VOPC encoding.

#### **V_CMP_GE_U32**

**206**

Set the per-lane condition code to 1 iff the first input is greater than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.u32 >= S1.u32; // D0 = VCC in VOPC encoding.

#### **V_CMP_T_U32**

**207**

Set the per-lane condition code to 1. Store the result into VCC or a scalar register.

D0.u64[laneId] = 1'1U; // D0 = VCC in VOPC encoding.

243 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture

**V_CMPX_F_I32**

**208**



Set the per-lane condition code to 0. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = 1'0U; // D0 = VCC in VOPC encoding.

#### **V_CMPX_LT_I32**

**209**

Set the per-lane condition code to 1 iff the first input is less than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.i32 < S1.i32; // D0 = VCC in VOPC encoding.

#### **V_CMPX_EQ_I32**

**210**

Set the per-lane condition code to 1 iff the first input is equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.i32 == S1.i32; // D0 = VCC in VOPC encoding.

#### **V_CMPX_LE_I32**

**211**

Set the per-lane condition code to 1 iff the first input is less than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.i32 <= S1.i32; // D0 = VCC in VOPC encoding.

#### **V_CMPX_GT_I32**

**212**

Set the per-lane condition code to 1 iff the first input is greater than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.i32 > S1.i32; // D0 = VCC in VOPC encoding.

244 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture

**213**



#### **V_CMPX_NE_I32**

Set the per-lane condition code to 1 iff the first input is not equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.i32 <> S1.i32; // D0 = VCC in VOPC encoding.

#### **V_CMPX_GE_I32**

**214**

Set the per-lane condition code to 1 iff the first input is greater than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.i32 >= S1.i32; // D0 = VCC in VOPC encoding.

**V_CMPX_T_I32**

**215**

Set the per-lane condition code to 1. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = 1'1U; // D0 = VCC in VOPC encoding.

#### **V_CMPX_F_U32**

**216**

Set the per-lane condition code to 0. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = 1'0U; // D0 = VCC in VOPC encoding.

#### **V_CMPX_LT_U32**

**217**

Set the per-lane condition code to 1 iff the first input is less than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.u32 < S1.u32;

245 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture



// D0 = VCC in VOPC encoding.

#### **V_CMPX_EQ_U32**

**218**

Set the per-lane condition code to 1 iff the first input is equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.u32 == S1.u32; // D0 = VCC in VOPC encoding.

#### **V_CMPX_LE_U32**

**219**

Set the per-lane condition code to 1 iff the first input is less than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.u32 <= S1.u32; // D0 = VCC in VOPC encoding.

#### **V_CMPX_GT_U32**

**220**

Set the per-lane condition code to 1 iff the first input is greater than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.u32 > S1.u32; // D0 = VCC in VOPC encoding.

#### **V_CMPX_NE_U32**

**221**

Set the per-lane condition code to 1 iff the first input is not equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.u32 <> S1.u32; // D0 = VCC in VOPC encoding.

**V_CMPX_GE_U32**

**222**

Set the per-lane condition code to 1 iff the first input is greater than or equal to the second input. Store the

246 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture



result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.u32 >= S1.u32; // D0 = VCC in VOPC encoding.

#### **V_CMPX_T_U32**

**223**

Set the per-lane condition code to 1. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = 1'1U; // D0 = VCC in VOPC encoding.

#### **V_CMP_F_I64**

**224**

Set the per-lane condition code to 0. Store the result into VCC or a scalar register.

D0.u64[laneId] = 1'0U; // D0 = VCC in VOPC encoding.

#### **V_CMP_LT_I64**

**225**

Set the per-lane condition code to 1 iff the first input is less than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.i64 < S1.i64; // D0 = VCC in VOPC encoding.

#### **V_CMP_EQ_I64**

**226**

Set the per-lane condition code to 1 iff the first input is equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.i64 == S1.i64; // D0 = VCC in VOPC encoding.

**V_CMP_LE_I64**

**227**

247 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture



Set the per-lane condition code to 1 iff the first input is less than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.i64 <= S1.i64; // D0 = VCC in VOPC encoding.

#### **V_CMP_GT_I64**

**228**

Set the per-lane condition code to 1 iff the first input is greater than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.i64 > S1.i64; // D0 = VCC in VOPC encoding.

#### **V_CMP_NE_I64**

**229**

Set the per-lane condition code to 1 iff the first input is not equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.i64 <> S1.i64; // D0 = VCC in VOPC encoding.

#### **V_CMP_GE_I64**

**230**

Set the per-lane condition code to 1 iff the first input is greater than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.i64 >= S1.i64; // D0 = VCC in VOPC encoding.

#### **V_CMP_T_I64**

**231**

Set the per-lane condition code to 1. Store the result into VCC or a scalar register.

D0.u64[laneId] = 1'1U; // D0 = VCC in VOPC encoding.

248 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture

**232**



#### **V_CMP_F_U64**

Set the per-lane condition code to 0. Store the result into VCC or a scalar register.

D0.u64[laneId] = 1'0U; // D0 = VCC in VOPC encoding.

#### **V_CMP_LT_U64**

**233**

Set the per-lane condition code to 1 iff the first input is less than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.u64 < S1.u64; // D0 = VCC in VOPC encoding.

#### **V_CMP_EQ_U64**

**234**

Set the per-lane condition code to 1 iff the first input is equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.u64 == S1.u64; // D0 = VCC in VOPC encoding.

#### **V_CMP_LE_U64**

**235**

Set the per-lane condition code to 1 iff the first input is less than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.u64 <= S1.u64; // D0 = VCC in VOPC encoding.

#### **V_CMP_GT_U64**

**236**

Set the per-lane condition code to 1 iff the first input is greater than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.u64 > S1.u64; // D0 = VCC in VOPC encoding.

249 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture

**237**



**V_CMP_NE_U64**

Set the per-lane condition code to 1 iff the first input is not equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.u64 <> S1.u64; // D0 = VCC in VOPC encoding.

**V_CMP_GE_U64**

**238**

Set the per-lane condition code to 1 iff the first input is greater than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.u64 >= S1.u64; // D0 = VCC in VOPC encoding.

**V_CMP_T_U64**

**239**

Set the per-lane condition code to 1. Store the result into VCC or a scalar register.

D0.u64[laneId] = 1'1U; // D0 = VCC in VOPC encoding.

#### **V_CMPX_F_I64**

**240**

Set the per-lane condition code to 0. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = 1'0U; // D0 = VCC in VOPC encoding.

#### **V_CMPX_LT_I64**

**241**

Set the per-lane condition code to 1 iff the first input is less than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.i64 < S1.i64;

250 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture



// D0 = VCC in VOPC encoding.

#### **V_CMPX_EQ_I64**

**242**

Set the per-lane condition code to 1 iff the first input is equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.i64 == S1.i64; // D0 = VCC in VOPC encoding.

#### **V_CMPX_LE_I64**

**243**

Set the per-lane condition code to 1 iff the first input is less than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.i64 <= S1.i64; // D0 = VCC in VOPC encoding.

#### **V_CMPX_GT_I64**

**244**

Set the per-lane condition code to 1 iff the first input is greater than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.i64 > S1.i64; // D0 = VCC in VOPC encoding.

#### **V_CMPX_NE_I64**

**245**

Set the per-lane condition code to 1 iff the first input is not equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.i64 <> S1.i64; // D0 = VCC in VOPC encoding.

**V_CMPX_GE_I64**

**246**

Set the per-lane condition code to 1 iff the first input is greater than or equal to the second input. Store the

251 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture



result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.i64 >= S1.i64; // D0 = VCC in VOPC encoding.

#### **V_CMPX_T_I64**

**247**

Set the per-lane condition code to 1. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = 1'1U; // D0 = VCC in VOPC encoding.

#### **V_CMPX_F_U64**

**248**

Set the per-lane condition code to 0. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = 1'0U; // D0 = VCC in VOPC encoding.

#### **V_CMPX_LT_U64**

**249**

Set the per-lane condition code to 1 iff the first input is less than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.u64 < S1.u64; // D0 = VCC in VOPC encoding.

#### **V_CMPX_EQ_U64**

**250**

Set the per-lane condition code to 1 iff the first input is equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.u64 == S1.u64; // D0 = VCC in VOPC encoding.

**V_CMPX_LE_U64**

**251**

252 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture



Set the per-lane condition code to 1 iff the first input is less than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.u64 <= S1.u64; // D0 = VCC in VOPC encoding.

#### **V_CMPX_GT_U64**

**252**

Set the per-lane condition code to 1 iff the first input is greater than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.u64 > S1.u64; // D0 = VCC in VOPC encoding.

#### **V_CMPX_NE_U64**

**253**

Set the per-lane condition code to 1 iff the first input is not equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.u64 <> S1.u64; // D0 = VCC in VOPC encoding.

#### **V_CMPX_GE_U64**

**254**

Set the per-lane condition code to 1 iff the first input is greater than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.u64 >= S1.u64; // D0 = VCC in VOPC encoding.

#### **V_CMPX_T_U64**

**255**

Set the per-lane condition code to 1. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = 1'1U; // D0 = VCC in VOPC encoding.

253 of 553

12.9. VOPC Instructions

"AMD Instinct MI300" Instruction Set Architecture



### **12.9.1. VOPC using VOP3A encoding**

Instructions in this format may also be encoded as VOP3A. This allows access to the extra control bits (e.g. ABS, OMOD) in exchange for not being able to use a literal constant. The VOP3 opcode is: VOP2 opcode + 0x000.

When the CLAMP microcode bit is set to 1, these compare instructions signal an exception when either of the inputs is NaN. When CLAMP is set to zero, NaN does not signal an exception. The second eight VOPC instructions have {OP8} embedded in them. This refers to each of the compare operations listed below.



where:

VDST = Destination for instruction in the VGPR. ABS = Floating-point absolute value. CLMP = Clamp output. OP = Instructions. SRC0 = First operand for instruction. SRC1 = Second operand for instruction. SRC2 = Third operand for instruction. Unused in VOPC instructions. OMOD = Output modifier for instruction. Unused in VOPC instructions. NEG = Floating-point negation.

## **12.10. VOP3P Instructions**





**V_PK_MAD_I16 0**

Multiply two packed signed 16-bit integer inputs component-wise, add a packed signed 16-bit integer value from a third input component-wise, and store the result into a vector register.

declare tmp : 32'B; tmp[15 : 0].i16 = S0[15 : 0].i16 * S1[15 : 0].i16 + S2[15 : 0].i16; tmp[31 : 16].i16 = S0[31 : 16].i16 * S1[31 : 16].i16 + S2[31 : 16].i16; D0.b32 = tmp

254 of 553

12.10. VOP3P Instructions

"AMD Instinct MI300" Instruction Set Architecture



#### **V_PK_MUL_LO_U16**

**1**

Multiply two packed unsigned 16-bit integer inputs component-wise and store the low bits of each resulting component into a vector register.

tmp[31 : 16].u16 = S0[31 : 16].u16 * S1[31 : 16].u16; tmp[15 : 0].u16 = S0[15 : 0].u16 * S1[15 : 0].u16; D0.b32 = tmp.b32

**V_PK_ADD_I16**

**2**

Add two packed signed 16-bit integer inputs component-wise and store the result into a vector register. No carry-in or carry-out support.

declare tmp : 32'B; tmp[15 : 0].i16 = S0[15 : 0].i16 + S1[15 : 0].i16; tmp[31 : 16].i16 = S0[31 : 16].i16 + S1[31 : 16].i16; D0.b32 = tmp

**V_PK_SUB_I16 3**

Subtract the second packed signed 16-bit integer input from the first input component-wise and store the result into a vector register. No carry-in or carry-out support.

declare tmp : 32'B; tmp[15 : 0].i16 = S0[15 : 0].i16 - S1[15 : 0].i16; tmp[31 : 16].i16 = S0[31 : 16].i16 - S1[31 : 16].i16; D0.b32 = tmp

#### **V_PK_LSHLREV_B16**

**4**

Given a packed shift count in the _first_ vector input, calculate the component-wise logical shift left of the _second_ packed vector input and store the result into a vector register.

tmp[31 : 16].u16 = (S1[31 : 16].u16 << S0.u32[19 : 16].u32); tmp[15 : 0].u16 = (S1[15 : 0].u16 << S0.u32[3 : 0].u32); D0.b32 = tmp.b32

**V_PK_LSHRREV_B16**

**5**

255 of 553

12.10. VOP3P Instructions

"AMD Instinct MI300" Instruction Set Architecture



Given a packed shift count in the _first_ vector input, calculate the component-wise logical shift right of the _second_ packed vector input and store the result into a vector register.

tmp[31 : 16].u16 = (S1[31 : 16].u16 >> S0.u32[19 : 16].u32); tmp[15 : 0].u16 = (S1[15 : 0].u16 >> S0.u32[3 : 0].u32); D0.b32 = tmp.b32

**V_PK_ASHRREV_I16 6**

Given a packed shift count in the _first_ vector input, calculate the component-wise arithmetic shift right (preserving sign bit) of the _second_ packed vector input and store the result into a vector register.

tmp[31 : 16].i16 = (S1[31 : 16].i16 >> S0.u32[19 : 16].u32); tmp[15 : 0].i16 = (S1[15 : 0].i16 >> S0.u32[3 : 0].u32); D0.b32 = tmp.b32

**V_PK_MAX_I16 7**

Select the component-wise maximum of two packed signed 16-bit integer inputs and store the selected values into a vector register.

declare tmp : 32'B; tmp[15 : 0].i16 = S0[15 : 0].i16 >= S1[15 : 0].i16 ? S0[15 : 0].i16 : S1[15 : 0].i16; tmp[31 : 16].i16 = S0[31 : 16].i16 >= S1[31 : 16].i16 ? S0[31 : 16].i16 : S1[31 : 16].i16; D0.b32 = tmp

**V_PK_MIN_I16 8**

Select the component-wise minimum of two packed signed 16-bit integer inputs and store the selected values into a vector register.

declare tmp : 32'B; tmp[15 : 0].i16 = S0[15 : 0].i16 < S1[15 : 0].i16 ? S0[15 : 0].i16 : S1[15 : 0].i16; tmp[31 : 16].i16 = S0[31 : 16].i16 < S1[31 : 16].i16 ? S0[31 : 16].i16 : S1[31 : 16].i16; D0.b32 = tmp

**V_PK_MAD_U16**

**9**

Multiply two packed unsigned 16-bit integer inputs component-wise, add a packed unsigned 16-bit integer value from a third input component-wise, and store the result into a vector register.

256 of 553

12.10. VOP3P Instructions

"AMD Instinct MI300" Instruction Set Architecture



declare tmp : 32'B; tmp[15 : 0].u16 = S0[15 : 0].u16 * S1[15 : 0].u16 + S2[15 : 0].u16; tmp[31 : 16].u16 = S0[31 : 16].u16 * S1[31 : 16].u16 + S2[31 : 16].u16; D0.b32 = tmp

#### **V_PK_ADD_U16**

**10**

Add two packed unsigned 16-bit integer inputs component-wise and store the result into a vector register. No carry-in or carry-out support.

declare tmp : 32'B; tmp[15 : 0].u16 = S0[15 : 0].u16 + S1[15 : 0].u16; tmp[31 : 16].u16 = S0[31 : 16].u16 + S1[31 : 16].u16; D0.b32 = tmp

#### **V_PK_SUB_U16**

**11**

Subtract the second packed unsigned 16-bit integer input from the first input component-wise and store the result into a vector register. No carry-in or carry-out support.

declare tmp : 32'B; tmp[15 : 0].u16 = S0[15 : 0].u16 - S1[15 : 0].u16; tmp[31 : 16].u16 = S0[31 : 16].u16 - S1[31 : 16].u16; D0.b32 = tmp

**V_PK_MAX_U16 12**

Select the component-wise maximum of two packed unsigned 16-bit integer inputs and store the selected values into a vector register.

declare tmp : 32'B; tmp[15 : 0].u16 = S0[15 : 0].u16 >= S1[15 : 0].u16 ? S0[15 : 0].u16 : S1[15 : 0].u16; tmp[31 : 16].u16 = S0[31 : 16].u16 >= S1[31 : 16].u16 ? S0[31 : 16].u16 : S1[31 : 16].u16; D0.b32 = tmp

**V_PK_MIN_U16 13**

Select the component-wise minimum of two packed unsigned 16-bit integer inputs and store the selected values into a vector register.

257 of 553

12.10. VOP3P Instructions

"AMD Instinct MI300" Instruction Set Architecture



declare tmp : 32'B; tmp[15 : 0].u16 = S0[15 : 0].u16 < S1[15 : 0].u16 ? S0[15 : 0].u16 : S1[15 : 0].u16; tmp[31 : 16].u16 = S0[31 : 16].u16 < S1[31 : 16].u16 ? S0[31 : 16].u16 : S1[31 : 16].u16; D0.b32 = tmp

#### **V_PK_FMA_F16**

**14**

Multiply two packed half-precision float inputs component-wise and add a third input component-wise using fused multiply add, and store the result into a vector register.

declare tmp : 32'B; tmp[15 : 0].f16 = fma(S0[15 : 0].f16, S1[15 : 0].f16, S2[15 : 0].f16); tmp[31 : 16].f16 = fma(S0[31 : 16].f16, S1[31 : 16].f16, S2[31 : 16].f16); D0.b32 = tmp

**V_PK_ADD_F16**

**15**

Add two packed half-precision float inputs component-wise and store the result into a vector register. No carryin or carry-out support.

declare tmp : 32'B; tmp[15 : 0].f16 = S0[15 : 0].f16 + S1[15 : 0].f16; tmp[31 : 16].f16 = S0[31 : 16].f16 + S1[31 : 16].f16; D0.b32 = tmp

#### **V_PK_MUL_F16**

**16**

Multiply two packed half-precision float inputs component-wise and store the result into a vector register.

declare tmp : 32'B; tmp[15 : 0].f16 = S0[15 : 0].f16 * S1[15 : 0].f16; tmp[31 : 16].f16 = S0[31 : 16].f16 * S1[31 : 16].f16; D0.b32 = tmp

#### **V_PK_MIN_F16**

**17**

Select the component-wise minimum of two packed half-precision float inputs and store the result into a vector register.

258 of 553

12.10. VOP3P Instructions

"AMD Instinct MI300" Instruction Set Architecture



declare tmp : 32'B; tmp[15 : 0].f16 = v_min_f16(S0[15 : 0].f16, S1[15 : 0].f16); tmp[31 : 16].f16 = v_min_f16(S0[31 : 16].f16, S1[31 : 16].f16); D0.b32 = tmp

#### **V_PK_MAX_F16**

**18**

Select the component-wise maximum of two packed half-precision float inputs and store the result into a vector register.

declare tmp : 32'B; tmp[15 : 0].f16 = v_max_f16(S0[15 : 0].f16, S1[15 : 0].f16); tmp[31 : 16].f16 = v_max_f16(S0[31 : 16].f16, S1[31 : 16].f16); D0.b32 = tmp

#### **V_MAD_MIX_F32**

**32**

Multiply two inputs and add a third input where the inputs are a mix of half-precision float and singleprecision float values. Store the result into a vector register.

Size and location of the three inputs are controlled by { OPSEL_HI[i], OPSEL[i] }: 0=src[31:0], 1=src[31:0], 2=src[15:0], 3=src[31:16]. For MIX opcodes the NEG_HI instruction field acts as an absolute-value modifier for the three inputs.

declare in : 32'F[3]; declare S : 32'B[3]; for i in 0 : 2 do if !OPSEL_HI.u3[i] then in[i] = S[i].f32 elsif OPSEL.u3[i] then in[i] = f16_to_f32(S[i][31 : 16].f16) else in[i] = f16_to_f32(S[i][15 : 0].f16) endif endfor; D0[31 : 0].f32 = in[0] * in[1] + in[2]

#### **Notes**

**V_MAD_MIXLO_F16**

**33**

Multiply two inputs and add a third input where the inputs are a mix of half-precision float and singleprecision float values. Convert the result to a half-precision float. Store the result into the low bits of a vector register.

259 of 553

12.10. VOP3P Instructions

"AMD Instinct MI300" Instruction Set Architecture



Size and location of the three inputs are controlled by { OPSEL_HI[i], OPSEL[i] }: 0=src[31:0], 1=src[31:0], 2=src[15:0], 3=src[31:16]. For MIX opcodes the NEG_HI instruction field acts as an absolute-value modifier for the three inputs.

declare in : 32'F[3]; declare S : 32'B[3]; for i in 0 : 2 do if !OPSEL_HI.u3[i] then in[i] = S[i].f32 elsif OPSEL.u3[i] then in[i] = f16_to_f32(S[i][31 : 16].f16) else in[i] = f16_to_f32(S[i][15 : 0].f16) endif endfor; D0[15 : 0].f16 = f32_to_f16(in[0] * in[1] + in[2])

#### **Notes**

#### **V_MAD_MIXHI_F16**

**34**

Multiply two inputs and add a third input where the inputs are a mix of half-precision float and singleprecision float values. Convert the result to a half-precision float. Store the result into the high bits of a vector register.

Size and location of the three inputs are controlled by { OPSEL_HI[i], OPSEL[i] }: 0=src[31:0], 1=src[31:0], 2=src[15:0], 3=src[31:16]. For MIX opcodes the NEG_HI instruction field acts as an absolute-value modifier for the three inputs.

declare in : 32'F[3]; declare S : 32'B[3]; for i in 0 : 2 do if !OPSEL_HI.u3[i] then in[i] = S[i].f32 elsif OPSEL.u3[i] then in[i] = f16_to_f32(S[i][31 : 16].f16) else in[i] = f16_to_f32(S[i][15 : 0].f16) endif endfor; D0[31 : 16].f16 = f32_to_f16(in[0] * in[1] + in[2])

#### **Notes**

**V_DOT2_F32_F16**

**35**

Compute the dot product of two packed 2-D half-precision float inputs in the single-precision float domain, add a single-precision float value from the third input and store the result into a vector register.

260 of 553

12.10. VOP3P Instructions

"AMD Instinct MI300" Instruction Set Architecture



tmp = S2.f32; tmp += f16_to_f32(S0[15 : 0].f16) * f16_to_f32(S1[15 : 0].f16); tmp += f16_to_f32(S0[31 : 16].f16) * f16_to_f32(S1[31 : 16].f16); D0.f32 = tmp

#### **V_DOT2_I32_I16**

**38**

Compute the dot product of two packed 2-D signed 16-bit integer inputs in the signed 32-bit integer domain, add a signed 32-bit integer value from the third input and store the result into a vector register.

tmp = S2.i32; tmp += i16_to_i32(S0[15 : 0].i16) * i16_to_i32(S1[15 : 0].i16); tmp += i16_to_i32(S0[31 : 16].i16) * i16_to_i32(S1[31 : 16].i16); D0.i32 = tmp

**V_DOT2_U32_U16**

**39**

Compute the dot product of two packed 2-D unsigned 16-bit integer inputs in the unsigned 32-bit integer domain, add an unsigned 32-bit integer value from the third input and store the result into a vector register.

tmp = S2.u32; tmp += u16_to_u32(S0[15 : 0].u16) * u16_to_u32(S1[15 : 0].u16); tmp += u16_to_u32(S0[31 : 16].u16) * u16_to_u32(S1[31 : 16].u16); D0.u32 = tmp

#### **V_DOT4_I32_I8**

**40**

Compute the dot product of two packed 4-D signed 8-bit integer inputs in the signed 32-bit integer domain, add a signed 32-bit integer value from the third input and store the result into a vector register.

tmp = S2.i32; tmp += i8_to_i32(S0[7 : 0].i8) * i8_to_i32(S1[7 : 0].i8); tmp += i8_to_i32(S0[15 : 8].i8) * i8_to_i32(S1[15 : 8].i8); tmp += i8_to_i32(S0[23 : 16].i8) * i8_to_i32(S1[23 : 16].i8); tmp += i8_to_i32(S0[31 : 24].i8) * i8_to_i32(S1[31 : 24].i8); D0.i32 = tmp

**V_DOT4_U32_U8**

**41**

Compute the dot product of two packed 4-D unsigned 8-bit integer inputs in the unsigned 32-bit integer

261 of 553

12.10. VOP3P Instructions

"AMD Instinct MI300" Instruction Set Architecture



domain, add an unsigned 32-bit integer value from the third input and store the result into a vector register.

tmp = S2.u32; tmp += u8_to_u32(S0[7 : 0].u8) * u8_to_u32(S1[7 : 0].u8); tmp += u8_to_u32(S0[15 : 8].u8) * u8_to_u32(S1[15 : 8].u8); tmp += u8_to_u32(S0[23 : 16].u8) * u8_to_u32(S1[23 : 16].u8); tmp += u8_to_u32(S0[31 : 24].u8) * u8_to_u32(S1[31 : 24].u8); D0.u32 = tmp

#### **V_DOT8_I32_I4**

**42**

Compute the dot product of two packed 8-D signed 4-bit integer inputs in the signed 32-bit integer domain, add a signed 32-bit integer value from the third input and store the result into a vector register.

tmp = S2.i32; tmp += i4_to_i32(S0[3 : 0].i4) * i4_to_i32(S1[3 : 0].i4); tmp += i4_to_i32(S0[7 : 4].i4) * i4_to_i32(S1[7 : 4].i4); tmp += i4_to_i32(S0[11 : 8].i4) * i4_to_i32(S1[11 : 8].i4); tmp += i4_to_i32(S0[15 : 12].i4) * i4_to_i32(S1[15 : 12].i4); tmp += i4_to_i32(S0[19 : 16].i4) * i4_to_i32(S1[19 : 16].i4); tmp += i4_to_i32(S0[23 : 20].i4) * i4_to_i32(S1[23 : 20].i4); tmp += i4_to_i32(S0[27 : 24].i4) * i4_to_i32(S1[27 : 24].i4); tmp += i4_to_i32(S0[31 : 28].i4) * i4_to_i32(S1[31 : 28].i4); D0.i32 = tmp

#### **V_DOT8_U32_U4**

**43**

Compute the dot product of two packed 8-D unsigned 4-bit integer inputs in the unsigned 32-bit integer domain, add an unsigned 32-bit integer value from the third input and store the result into a vector register.

tmp = S2.u32; tmp += u4_to_u32(S0[3 : 0].u4) * u4_to_u32(S1[3 : 0].u4); tmp += u4_to_u32(S0[7 : 4].u4) * u4_to_u32(S1[7 : 4].u4); tmp += u4_to_u32(S0[11 : 8].u4) * u4_to_u32(S1[11 : 8].u4); tmp += u4_to_u32(S0[15 : 12].u4) * u4_to_u32(S1[15 : 12].u4); tmp += u4_to_u32(S0[19 : 16].u4) * u4_to_u32(S1[19 : 16].u4); tmp += u4_to_u32(S0[23 : 20].u4) * u4_to_u32(S1[23 : 20].u4); tmp += u4_to_u32(S0[27 : 24].u4) * u4_to_u32(S1[27 : 24].u4); tmp += u4_to_u32(S0[31 : 28].u4) * u4_to_u32(S1[31 : 28].u4); D0.u32 = tmp

#### **V_PK_FMA_F32**

**48**

Multiply two packed single-precision float inputs component-wise and add a third input component-wise using

262 of 553

12.10. VOP3P Instructions

"AMD Instinct MI300" Instruction Set Architecture



fused multiply add, and store the result into a vector register.

declare tmp : 64'B; tmp[31 : 0].f32 = fma(S0[31 : 0].f32, S1[31 : 0].f32, S2[31 : 0].f32); tmp[63 : 32].f32 = fma(S0[63 : 32].f32, S1[63 : 32].f32, S2[63 : 32].f32); D0.b64 = tmp

**V_PK_MUL_F32**

**49**

Multiply two packed single-precision float inputs component-wise and store the result into a vector register.

declare tmp : 64'B; tmp[31 : 0].f32 = S0[31 : 0].f32 * S1[31 : 0].f32; tmp[63 : 32].f32 = S0[63 : 32].f32 * S1[63 : 32].f32; D0.b64 = tmp

**V_PK_ADD_F32 50**

Add two packed single-precision float inputs component-wise and store the result into a vector register. No carry-in or carry-out support.

declare tmp : 64'B; tmp[31 : 0].f32 = S0[31 : 0].f32 + S1[31 : 0].f32; tmp[63 : 32].f32 = S0[63 : 32].f32 + S1[63 : 32].f32; D0.b64 = tmp

**V_PK_MOV_B32 51**

Move data from two vector inputs into two vector registers.

tmp0.u32 = S0.u32[OPSEL[0].i32 * 32 + 31 : OPSEL[0].i32 * 32]; tmp1.u32 = S1.u32[OPSEL[1].i32 * 32 + 31 : OPSEL[1].i32 * 32]; D0.u32[31 : 0] = tmp0.u32; D0.u32[63 : 32] = tmp1.u32

#### **Notes**

The source operands are treated as 64 bit and are subject to alignment restrictions for both SGPR and VGPR.

For two VGPR inputs this opcode can be used as an arbitrary gather by using OP_SEL to select either the even VGPR specified or the next odd VGPR.

263 of 553

12.10. VOP3P Instructions

"AMD Instinct MI300" Instruction Set Architecture

**62**



v_pk_mov_b32 v0, v2, v4 op_sel:[0,1] // evaluates v0 <- v2 and v1 <- v5.

Due to scalar broadcast restrictions if two SGPRs are specified as operands, they must be the same SGPR.

v_pk_mov_b32 v0, s6, s6 op_sel:[0,1] // 64-bit move from scalar s[6:7].

#### **V_MFMA_F32_16X16X8_XF32**

Multiply the 16x8 matrix in the first input by the 8x16 matrix in the second input and add the 16x16 matrix in the third input using fused multiply add. Store the resulting matrix into vector registers.

D = A (16x8) * B (8x16) + C (16x16)

Each operand contains a single matrix whose elements are distributed across all lanes of the wave. A single matrix multiply is computed and the row-column dot products are distributed across the vector ALU for higher performance.

Matrices A and B are single-precision float format. Matrices C and D are single-precision float format. XF32 is a FP32 operation with FP32 inputs and outputs but implemented at reduced intermediate precision where mantissa is truncated to 10 bits (not including leading 1 for non-zero values) and results are accumulated into FP32 value with 23 bit mantissa.

#### **Notes**

This instruction performs 4 passes.

**V_MFMA_F32_32X32X4_XF32**

**63**

Multiply the 32x4 matrix in the first input by the 4x32 matrix in the second input and add the 32x32 matrix in the third input using fused multiply add. Store the resulting matrix into vector registers.

D = A (32x4) * B (4x32) + C (32x32)

Each operand contains a single matrix whose elements are distributed across all lanes of the wave. A single matrix multiply is computed and the row-column dot products are distributed across the vector ALU for higher performance.

Matrices A and B are single-precision float format. Matrices C and D are single-precision float format.

#### **Notes**

This instruction performs 8 passes.

264 of 553

12.10. VOP3P Instructions

"AMD Instinct MI300" Instruction Set Architecture

**V_MFMA_F32_32X32X1_2B_F32**

**64**



Multiply the 32x1 matrix in the first input by the 1x32 matrix in the second input and add the 32x32 matrix in the third input using fused multiply add. Store the resulting matrix into vector registers.

D = A (32x1) * B (1x32) + C (32x32)

This instruction performs 2 matrix multiplies. Each operand contains 2 matrices back to back, and each matrix has elements distributed across all lanes of the wave. Each matrix multiple is computed and the row-column dot products are distributed across the vector ALU for higher performance. The result matrices are stored back-to-back in the destination vector registers.

Matrices A and B are single-precision float format. Matrices C and D are single-precision float format.

#### **Notes**

This instruction performs 16 passes.

#### **V_MFMA_F32_16X16X1_4B_F32**

**65**

Multiply the 16x1 matrix in the first input by the 1x16 matrix in the second input and add the 16x16 matrix in the third input using fused multiply add. Store the resulting matrix into vector registers.

D = A (16x1) * B (1x16) + C (16x16)

This instruction performs 4 matrix multiplies. Each operand contains 4 matrices back to back, and each matrix has elements distributed across all lanes of the wave. Each matrix multiple is computed and the row-column dot products are distributed across the vector ALU for higher performance. The result matrices are stored back-to-back in the destination vector registers.

Matrices A and B are single-precision float format. Matrices C and D are single-precision float format.

#### **Notes**

This instruction performs 8 passes.

**V_MFMA_F32_4X4X1_16B_F32**

**66**

Multiply the 4x1 matrix in the first input by the 1x4 matrix in the second input and add the 4x4 matrix in the third input using fused multiply add. Store the resulting matrix into vector registers.

D = A (4x1) * B (1x4) + C (4x4)

265 of 553

12.10. VOP3P Instructions

"AMD Instinct MI300" Instruction Set Architecture

**68**



This instruction performs 16 matrix multiplies. Each operand contains 16 matrices back to back, and each matrix has elements distributed across all lanes of the wave. Each matrix multiple is computed and the rowcolumn dot products are distributed across the vector ALU for higher performance. The result matrices are stored back-to-back in the destination vector registers.

Matrices A and B are single-precision float format. Matrices C and D are single-precision float format.

#### **Notes**

This instruction performs 2 passes.

**V_MFMA_F32_32X32X2_F32**

Multiply the 32x2 matrix in the first input by the 2x32 matrix in the second input and add the 32x32 matrix in the third input using fused multiply add. Store the resulting matrix into vector registers.

D = A (32x2) * B (2x32) + C (32x32)

Each operand contains a single matrix whose elements are distributed across all lanes of the wave. A single matrix multiply is computed and the row-column dot products are distributed across the vector ALU for higher performance.

Matrices A and B are single-precision float format. Matrices C and D are single-precision float format.

#### **Notes**

This instruction performs 16 passes.

**V_MFMA_F32_16X16X4_F32**

**69**

Multiply the 16x4 matrix in the first input by the 4x16 matrix in the second input and add the 16x16 matrix in the third input using fused multiply add. Store the resulting matrix into vector registers.

D = A (16x4) * B (4x16) + C (16x16)

Each operand contains a single matrix whose elements are distributed across all lanes of the wave. A single matrix multiply is computed and the row-column dot products are distributed across the vector ALU for higher performance.

Matrices A and B are single-precision float format. Matrices C and D are single-precision float format.

#### **Notes**

This instruction performs 8 passes.

266 of 553

12.10. VOP3P Instructions

"AMD Instinct MI300" Instruction Set Architecture

**V_MFMA_F32_32X32X4_2B_F16**

**72**



Multiply the 32x4 matrix in the first input by the 4x32 matrix in the second input and add the 32x32 matrix in the third input using fused multiply add. Store the resulting matrix into vector registers.

D = A (32x4) * B (4x32) + C (32x32)

This instruction performs 2 matrix multiplies. Each operand contains 2 matrices back to back, and each matrix has elements distributed across all lanes of the wave. Each matrix multiple is computed and the row-column dot products are distributed across the vector ALU for higher performance. The result matrices are stored back-to-back in the destination vector registers.

Matrices A and B are half-precision float format. Matrices C and D are single-precision float format.

#### **Notes**

This instruction performs 16 passes.

**V_MFMA_F32_16X16X4_4B_F16**

**73**

Multiply the 16x4 matrix in the first input by the 4x16 matrix in the second input and add the 16x16 matrix in the third input using fused multiply add. Store the resulting matrix into vector registers.

D = A (16x4) * B (4x16) + C (16x16)

This instruction performs 4 matrix multiplies. Each operand contains 4 matrices back to back, and each matrix has elements distributed across all lanes of the wave. Each matrix multiple is computed and the row-column dot products are distributed across the vector ALU for higher performance. The result matrices are stored back-to-back in the destination vector registers.

Matrices A and B are half-precision float format. Matrices C and D are single-precision float format.

#### **Notes**

This instruction performs 8 passes.

**V_MFMA_F32_4X4X4_16B_F16**

**74**

Multiply the 4x4 matrix in the first input by the 4x4 matrix in the second input and add the 4x4 matrix in the third input using fused multiply add. Store the resulting matrix into vector registers.

D = A (4x4) * B (4x4) + C (4x4)

This instruction performs 16 matrix multiplies. Each operand contains 16 matrices back to back, and each

267 of 553

12.10. VOP3P Instructions

"AMD Instinct MI300" Instruction Set Architecture

**76**



matrix has elements distributed across all lanes of the wave. Each matrix multiple is computed and the rowcolumn dot products are distributed across the vector ALU for higher performance. The result matrices are stored back-to-back in the destination vector registers.

Matrices A and B are half-precision float format. Matrices C and D are single-precision float format.

#### **Notes**

This instruction performs 2 passes.

**V_MFMA_F32_32X32X8_F16**

Multiply the 32x8 matrix in the first input by the 8x32 matrix in the second input and add the 32x32 matrix in the third input using fused multiply add. Store the resulting matrix into vector registers.

D = A (32x8) * B (8x32) + C (32x32)

Each operand contains a single matrix whose elements are distributed across all lanes of the wave. A single matrix multiply is computed and the row-column dot products are distributed across the vector ALU for higher performance.

Matrices A and B are half-precision float format. Matrices C and D are single-precision float format.

#### **Notes**

This instruction performs 8 passes.

**V_MFMA_F32_16X16X16_F16**

**77**

Multiply the 16x16 matrix in the first input by the 16x16 matrix in the second input and add the 16x16 matrix in the third input using fused multiply add. Store the resulting matrix into vector registers.

D = A (16x16) * B (16x16) + C (16x16)

Each operand contains a single matrix whose elements are distributed across all lanes of the wave. A single matrix multiply is computed and the row-column dot products are distributed across the vector ALU for higher performance.

Matrices A and B are half-precision float format. Matrices C and D are single-precision float format.

#### **Notes**

This instruction performs 4 passes.

268 of 553

12.10. VOP3P Instructions

"AMD Instinct MI300" Instruction Set Architecture

**V_MFMA_I32_32X32X4_2B_I8**

**80**



Multiply the 32x4 matrix in the first input by the 4x32 matrix in the second input and add the 32x32 matrix in the third input using fused multiply add. Store the resulting matrix into vector registers.

D = A (32x4) * B (4x32) + C (32x32)

This instruction performs 2 matrix multiplies. Each operand contains 2 matrices back to back, and each matrix has elements distributed across all lanes of the wave. Each matrix multiple is computed and the row-column dot products are distributed across the vector ALU for higher performance. The result matrices are stored back-to-back in the destination vector registers.

Matrices A and B are signed 8-bit integer format. Matrices C and D are signed 32-bit integer format.

#### **Notes**

This instruction performs 16 passes.

**V_MFMA_I32_16X16X4_4B_I8**

**81**

Multiply the 16x4 matrix in the first input by the 4x16 matrix in the second input and add the 16x16 matrix in the third input using fused multiply add. Store the resulting matrix into vector registers.

D = A (16x4) * B (4x16) + C (16x16)

This instruction performs 4 matrix multiplies. Each operand contains 4 matrices back to back, and each matrix has elements distributed across all lanes of the wave. Each matrix multiple is computed and the row-column dot products are distributed across the vector ALU for higher performance. The result matrices are stored back-to-back in the destination vector registers.

Matrices A and B are signed 8-bit integer format. Matrices C and D are signed 32-bit integer format.

#### **Notes**

This instruction performs 8 passes.

**V_MFMA_I32_4X4X4_16B_I8**

**82**

Multiply the 4x4 matrix in the first input by the 4x4 matrix in the second input and add the 4x4 matrix in the third input using fused multiply add. Store the resulting matrix into vector registers.

D = A (4x4) * B (4x4) + C (4x4)

This instruction performs 16 matrix multiplies. Each operand contains 16 matrices back to back, and each

269 of 553

12.10. VOP3P Instructions

"AMD Instinct MI300" Instruction Set Architecture

**86**



matrix has elements distributed across all lanes of the wave. Each matrix multiple is computed and the rowcolumn dot products are distributed across the vector ALU for higher performance. The result matrices are stored back-to-back in the destination vector registers.

Matrices A and B are signed 8-bit integer format. Matrices C and D are signed 32-bit integer format.

#### **Notes**

This instruction performs 2 passes.

#### **V_MFMA_I32_32X32X16_I8**

Multiply the 32x16 matrix in the first input by the 16x32 matrix in the second input and add the 32x32 matrix in the third input using fused multiply add. Store the resulting matrix into vector registers.

D = A (32x16) * B (16x32) + C (32x32)

Each operand contains a single matrix whose elements are distributed across all lanes of the wave. A single matrix multiply is computed and the row-column dot products are distributed across the vector ALU for higher performance.

Matrices A and B are signed 8-bit integer format. Matrices C and D are signed 32-bit integer format.

#### **Notes**

This instruction performs 8 passes.

#### **V_MFMA_I32_16X16X32_I8**

**87**

Multiply the 16x32 matrix in the first input by the 32x16 matrix in the second input and add the 16x16 matrix in the third input using fused multiply add. Store the resulting matrix into vector registers.

D = A (16x32) * B (32x16) + C (16x16)

Each operand contains a single matrix whose elements are distributed across all lanes of the wave. A single matrix multiply is computed and the row-column dot products are distributed across the vector ALU for higher performance.

Matrices A and B are signed 8-bit integer format. Matrices C and D are signed 32-bit integer format.

#### **Notes**

This instruction performs 4 passes.

270 of 553

12.10. VOP3P Instructions

"AMD Instinct MI300" Instruction Set Architecture

**V_ACCVGPR_READ**

**88**



Move 32 bits of data from an accumulator vector register into an architectural vector register.

**V_ACCVGPR_WRITE 89**

Move 32 bits of data from an architectural vector register into an accumulator vector register.

**V_MFMA_F32_32X32X4_2B_BF16 93**

Multiply the 32x4 matrix in the first input by the 4x32 matrix in the second input and add the 32x32 matrix in the third input using fused multiply add. Store the resulting matrix into vector registers.

D = A (32x4) * B (4x32) + C (32x32)

This instruction performs 2 matrix multiplies. Each operand contains 2 matrices back to back, and each matrix has elements distributed across all lanes of the wave. Each matrix multiple is computed and the row-column dot products are distributed across the vector ALU for higher performance. The result matrices are stored back-to-back in the destination vector registers.

Matrices A and B are BF16 float format. Matrices C and D are single-precision float format.

#### **Notes**

This instruction performs 16 passes.

#### **V_MFMA_F32_16X16X4_4B_BF16**

**94**

Multiply the 16x4 matrix in the first input by the 4x16 matrix in the second input and add the 16x16 matrix in the third input using fused multiply add. Store the resulting matrix into vector registers.

D = A (16x4) * B (4x16) + C (16x16)

This instruction performs 4 matrix multiplies. Each operand contains 4 matrices back to back, and each matrix has elements distributed across all lanes of the wave. Each matrix multiple is computed and the row-column dot products are distributed across the vector ALU for higher performance. The result matrices are stored back-to-back in the destination vector registers.

Matrices A and B are BF16 float format. Matrices C and D are single-precision float format.

#### **Notes**

This instruction performs 8 passes.

271 of 553

12.10. VOP3P Instructions

"AMD Instinct MI300" Instruction Set Architecture

**V_MFMA_F32_4X4X4_16B_BF16**

**95**



Multiply the 4x4 matrix in the first input by the 4x4 matrix in the second input and add the 4x4 matrix in the third input using fused multiply add. Store the resulting matrix into vector registers.

D = A (4x4) * B (4x4) + C (4x4)

This instruction performs 16 matrix multiplies. Each operand contains 16 matrices back to back, and each matrix has elements distributed across all lanes of the wave. Each matrix multiple is computed and the rowcolumn dot products are distributed across the vector ALU for higher performance. The result matrices are stored back-to-back in the destination vector registers.

Matrices A and B are BF16 float format. Matrices C and D are single-precision float format.

#### **Notes**

This instruction performs 2 passes.

**V_MFMA_F32_32X32X8_BF16**

**96**

Multiply the 32x8 matrix in the first input by the 8x32 matrix in the second input and add the 32x32 matrix in the third input using fused multiply add. Store the resulting matrix into vector registers.

D = A (32x8) * B (8x32) + C (32x32)

Each operand contains a single matrix whose elements are distributed across all lanes of the wave. A single matrix multiply is computed and the row-column dot products are distributed across the vector ALU for higher performance.

Matrices A and B are BF16 float format. Matrices C and D are single-precision float format.

#### **Notes**

This instruction performs 8 passes.

**V_MFMA_F32_16X16X16_BF16**

**97**

Multiply the 16x16 matrix in the first input by the 16x16 matrix in the second input and add the 16x16 matrix in the third input using fused multiply add. Store the resulting matrix into vector registers.

D = A (16x16) * B (16x16) + C (16x16)

Each operand contains a single matrix whose elements are distributed across all lanes of the wave. A single

272 of 553

12.10. VOP3P Instructions

"AMD Instinct MI300" Instruction Set Architecture

**98**



matrix multiply is computed and the row-column dot products are distributed across the vector ALU for higher performance.

Matrices A and B are BF16 float format. Matrices C and D are single-precision float format.

#### **Notes**

This instruction performs 4 passes.

#### **V_SMFMAC_F32_16X16X32_F16**

Multiply the 16x32 sparse matrix in the first input by the 32x16 matrix in the second input and accumulate the result into the 16x16 matrix stored in the destination registers using fused multiply add. Sparse indexes for the first matrix are given in the third input.

D = A (sparse 16x32) * B (32x16) + D (16x16)

Each operand contains a single matrix whose elements are distributed across all lanes of the wave. A single matrix multiply is computed and the row-column dot products are distributed across the vector ALU for higher performance.

Matrix A is a sparse matrix in half-precision float format, consuming half the physical storage of a dense matrix with same dimensions. Matrix B is a dense matrix in half-precision float format. Matrix D is singleprecision float format and is both the output and the accumulate input.

2 out of every 4 elements on the K axis of matrix A are zero. The sparse indexes are used to determine which 2 elements are zero.

#### **Notes**

This instruction performs 4 passes.

**V_SMFMAC_F32_32X32X16_F16**

**100**

Multiply the 32x16 sparse matrix in the first input by the 16x32 matrix in the second input and accumulate the result into the 32x32 matrix stored in the destination registers using fused multiply add. Sparse indexes for the first matrix are given in the third input.

D = A (sparse 32x16) * B (16x32) + D (32x32)

Each operand contains a single matrix whose elements are distributed across all lanes of the wave. A single matrix multiply is computed and the row-column dot products are distributed across the vector ALU for higher performance.

Matrix A is a sparse matrix in half-precision float format, consuming half the physical storage of a dense matrix with same dimensions. Matrix B is a dense matrix in half-precision float format. Matrix D is single-

273 of 553

12.10. VOP3P Instructions

"AMD Instinct MI300" Instruction Set Architecture

**102**



precision float format and is both the output and the accumulate input.

2 out of every 4 elements on the K axis of matrix A are zero. The sparse indexes are used to determine which 2 elements are zero.

#### **Notes**

This instruction performs 8 passes.

#### **V_SMFMAC_F32_16X16X32_BF16**

Multiply the 16x32 sparse matrix in the first input by the 32x16 matrix in the second input and accumulate the result into the 16x16 matrix stored in the destination registers using fused multiply add. Sparse indexes for the first matrix are given in the third input.

D = A (sparse 16x32) * B (32x16) + D (16x16)

Each operand contains a single matrix whose elements are distributed across all lanes of the wave. A single matrix multiply is computed and the row-column dot products are distributed across the vector ALU for higher performance.

Matrix A is a sparse matrix in BF16 float format, consuming half the physical storage of a dense matrix with same dimensions. Matrix B is a dense matrix in BF16 float format. Matrix D is single-precision float format and is both the output and the accumulate input.

2 out of every 4 elements on the K axis of matrix A are zero. The sparse indexes are used to determine which 2 elements are zero.

#### **Notes**

This instruction performs 4 passes.

**V_SMFMAC_F32_32X32X16_BF16 104**

Multiply the 32x16 sparse matrix in the first input by the 16x32 matrix in the second input and accumulate the result into the 32x32 matrix stored in the destination registers using fused multiply add. Sparse indexes for the first matrix are given in the third input.

D = A (sparse 32x16) * B (16x32) + D (32x32)

Each operand contains a single matrix whose elements are distributed across all lanes of the wave. A single matrix multiply is computed and the row-column dot products are distributed across the vector ALU for higher performance.

Matrix A is a sparse matrix in BF16 float format, consuming half the physical storage of a dense matrix with same dimensions. Matrix B is a dense matrix in BF16 float format. Matrix D is single-precision float format and

274 of 553

12.10. VOP3P Instructions

"AMD Instinct MI300" Instruction Set Architecture

**106**



is both the output and the accumulate input.

2 out of every 4 elements on the K axis of matrix A are zero. The sparse indexes are used to determine which 2 elements are zero.

#### **Notes**

This instruction performs 8 passes.

#### **V_SMFMAC_I32_16X16X64_I8**

Multiply the 16x64 sparse matrix in the first input by the 64x16 matrix in the second input and accumulate the result into the 16x16 matrix stored in the destination registers using fused multiply add. Sparse indexes for the first matrix are given in the third input.

D = A (sparse 16x64) * B (64x16) + D (16x16)

Each operand contains a single matrix whose elements are distributed across all lanes of the wave. A single matrix multiply is computed and the row-column dot products are distributed across the vector ALU for higher performance.

Matrix A is a sparse matrix in signed 8-bit integer format, consuming half the physical storage of a dense matrix with same dimensions. Matrix B is a dense matrix in signed 8-bit integer format. Matrix D is signed 32bit integer format and is both the output and the accumulate input.

2 out of every 4 elements on the K axis of matrix A are zero. The sparse indexes are used to determine which 2 elements are zero.

#### **Notes**

This instruction performs 4 passes.

**V_SMFMAC_I32_32X32X32_I8**

**108**

Multiply the 32x32 sparse matrix in the first input by the 32x32 matrix in the second input and accumulate the result into the 32x32 matrix stored in the destination registers using fused multiply add. Sparse indexes for the first matrix are given in the third input.

D = A (sparse 32x32) * B (32x32) + D (32x32)

Each operand contains a single matrix whose elements are distributed across all lanes of the wave. A single matrix multiply is computed and the row-column dot products are distributed across the vector ALU for higher performance.

Matrix A is a sparse matrix in signed 8-bit integer format, consuming half the physical storage of a dense matrix with same dimensions. Matrix B is a dense matrix in signed 8-bit integer format. Matrix D is signed 32-

275 of 553

12.10. VOP3P Instructions

"AMD Instinct MI300" Instruction Set Architecture

**110**



bit integer format and is both the output and the accumulate input.

2 out of every 4 elements on the K axis of matrix A are zero. The sparse indexes are used to determine which 2 elements are zero.

#### **Notes**

This instruction performs 8 passes.

#### **V_MFMA_F64_16X16X4_F64**

Multiply the 16x4 matrix in the first input by the 4x16 matrix in the second input and add the 16x16 matrix in the third input using fused multiply add. Store the resulting matrix into vector registers.

D = A (16x4) * B (4x16) + C (16x16)

Each operand contains a single matrix whose elements are distributed across all lanes of the wave. A single matrix multiply is computed and the row-column dot products are distributed across the vector ALU for higher performance.

Matrices A and B are double-precision float format. Matrices C and D are double-precision float format.

#### **Notes**

This instruction performs 8 passes.

**V_MFMA_F64_4X4X4_4B_F64**

**111**

Multiply the 4x4 matrix in the first input by the 4x4 matrix in the second input and add the 4x4 matrix in the third input using fused multiply add. Store the resulting matrix into vector registers.

D = A (4x4) * B (4x4) + C (4x4)

This instruction performs 4 matrix multiplies. Each operand contains 4 matrices back to back, and each matrix has elements distributed across all lanes of the wave. Each matrix multiple is computed and the row-column dot products are distributed across the vector ALU for higher performance. The result matrices are stored back-to-back in the destination vector registers.

Matrices A and B are double-precision float format. Matrices C and D are double-precision float format.

#### **Notes**

This instruction performs 4 passes.

276 of 553

12.10. VOP3P Instructions

"AMD Instinct MI300" Instruction Set Architecture

**V_MFMA_F32_16X16X32_BF8_BF8**

**112**



Multiply the 16x32 matrix in the first input by the 32x16 matrix in the second input and add the 16x16 matrix in the third input using fused multiply add. Store the resulting matrix into vector registers.

D = A (16x32) * B (32x16) + C (16x16)

Each operand contains a single matrix whose elements are distributed across all lanes of the wave. A single matrix multiply is computed and the row-column dot products are distributed across the vector ALU for higher performance.

Matrix A is BF8 float format. Matrix B is BF8 float format. Matrices C and D are single-precision float format.

#### **Notes**

This instruction performs 4 passes.

**V_MFMA_F32_16X16X32_BF8_FP8**

**113**

Multiply the 16x32 matrix in the first input by the 32x16 matrix in the second input and add the 16x16 matrix in the third input using fused multiply add. Store the resulting matrix into vector registers.

D = A (16x32) * B (32x16) + C (16x16)

Each operand contains a single matrix whose elements are distributed across all lanes of the wave. A single matrix multiply is computed and the row-column dot products are distributed across the vector ALU for higher performance.

Matrix A is BF8 float format. Matrix B is FP8 float format. Matrices C and D are single-precision float format.

#### **Notes**

This instruction performs 4 passes.

**V_MFMA_F32_16X16X32_FP8_BF8**

**114**

Multiply the 16x32 matrix in the first input by the 32x16 matrix in the second input and add the 16x16 matrix in the third input using fused multiply add. Store the resulting matrix into vector registers.

D = A (16x32) * B (32x16) + C (16x16)

Each operand contains a single matrix whose elements are distributed across all lanes of the wave. A single matrix multiply is computed and the row-column dot products are distributed across the vector ALU for higher performance.

277 of 553

12.10. VOP3P Instructions

"AMD Instinct MI300" Instruction Set Architecture



Matrix A is FP8 float format. Matrix B is BF8 float format. Matrices C and D are single-precision float format.

#### **Notes**

This instruction performs 4 passes.

#### **V_MFMA_F32_16X16X32_FP8_FP8**

**115**

Multiply the 16x32 matrix in the first input by the 32x16 matrix in the second input and add the 16x16 matrix in the third input using fused multiply add. Store the resulting matrix into vector registers.

D = A (16x32) * B (32x16) + C (16x16)

Each operand contains a single matrix whose elements are distributed across all lanes of the wave. A single matrix multiply is computed and the row-column dot products are distributed across the vector ALU for higher performance.

Matrix A is FP8 float format. Matrix B is FP8 float format. Matrices C and D are single-precision float format.

#### **Notes**

This instruction performs 4 passes.

#### **V_MFMA_F32_32X32X16_BF8_BF8**

**116**

Multiply the 32x16 matrix in the first input by the 16x32 matrix in the second input and add the 32x32 matrix in the third input using fused multiply add. Store the resulting matrix into vector registers.

D = A (32x16) * B (16x32) + C (32x32)

Each operand contains a single matrix whose elements are distributed across all lanes of the wave. A single matrix multiply is computed and the row-column dot products are distributed across the vector ALU for higher performance.

Matrix A is BF8 float format. Matrix B is BF8 float format. Matrices C and D are single-precision float format.

#### **Notes**

This instruction performs 8 passes.

#### **V_MFMA_F32_32X32X16_BF8_FP8**

**117**

Multiply the 32x16 matrix in the first input by the 16x32 matrix in the second input and add the 32x32 matrix in the third input using fused multiply add. Store the resulting matrix into vector registers.

278 of 553

12.10. VOP3P Instructions

"AMD Instinct MI300" Instruction Set Architecture



D = A (32x16) * B (16x32) + C (32x32)

Each operand contains a single matrix whose elements are distributed across all lanes of the wave. A single matrix multiply is computed and the row-column dot products are distributed across the vector ALU for higher performance.

Matrix A is BF8 float format. Matrix B is FP8 float format. Matrices C and D are single-precision float format.

#### **Notes**

This instruction performs 8 passes.

#### **V_MFMA_F32_32X32X16_FP8_BF8**

#### **118**

Multiply the 32x16 matrix in the first input by the 16x32 matrix in the second input and add the 32x32 matrix in the third input using fused multiply add. Store the resulting matrix into vector registers.

D = A (32x16) * B (16x32) + C (32x32)

Each operand contains a single matrix whose elements are distributed across all lanes of the wave. A single matrix multiply is computed and the row-column dot products are distributed across the vector ALU for higher performance.

Matrix A is FP8 float format. Matrix B is BF8 float format. Matrices C and D are single-precision float format.

#### **Notes**

This instruction performs 8 passes.

#### **V_MFMA_F32_32X32X16_FP8_FP8**

**119**

Multiply the 32x16 matrix in the first input by the 16x32 matrix in the second input and add the 32x32 matrix in the third input using fused multiply add. Store the resulting matrix into vector registers.

D = A (32x16) * B (16x32) + C (32x32)

Each operand contains a single matrix whose elements are distributed across all lanes of the wave. A single matrix multiply is computed and the row-column dot products are distributed across the vector ALU for higher performance.

Matrix A is FP8 float format. Matrix B is FP8 float format. Matrices C and D are single-precision float format.

#### **Notes**

279 of 553

12.10. VOP3P Instructions

"AMD Instinct MI300" Instruction Set Architecture

**120**



This instruction performs 8 passes.

#### **V_SMFMAC_F32_16X16X64_BF8_BF8**

Multiply the 16x64 sparse matrix in the first input by the 64x16 matrix in the second input and accumulate the result into the 16x16 matrix stored in the destination registers using fused multiply add. Sparse indexes for the first matrix are given in the third input.

D = A (sparse 16x64) * B (64x16) + D (16x16)

Each operand contains a single matrix whose elements are distributed across all lanes of the wave. A single matrix multiply is computed and the row-column dot products are distributed across the vector ALU for higher performance.

Matrix A is a sparse matrix in BF8 float format, consuming half the physical storage of a dense matrix with same dimensions. Matrix B is a dense matrix in BF8 float format. Matrix D is single-precision float format and is both the output and the accumulate input.

2 out of every 4 elements on the K axis of matrix A are zero. The sparse indexes are used to determine which 2 elements are zero.

#### **Notes**

This instruction performs 4 passes.

#### **V_SMFMAC_F32_16X16X64_BF8_FP8**

**121**

Multiply the 16x64 sparse matrix in the first input by the 64x16 matrix in the second input and accumulate the result into the 16x16 matrix stored in the destination registers using fused multiply add. Sparse indexes for the first matrix are given in the third input.

D = A (sparse 16x64) * B (64x16) + D (16x16)

Each operand contains a single matrix whose elements are distributed across all lanes of the wave. A single matrix multiply is computed and the row-column dot products are distributed across the vector ALU for higher performance.

Matrix A is a sparse matrix in BF8 float format, consuming half the physical storage of a dense matrix with same dimensions. Matrix B is a dense matrix in FP8 float format. Matrix D is single-precision float format and is both the output and the accumulate input.

2 out of every 4 elements on the K axis of matrix A are zero. The sparse indexes are used to determine which 2 elements are zero.

#### **Notes**

280 of 553

12.10. VOP3P Instructions

"AMD Instinct MI300" Instruction Set Architecture

**122**



This instruction performs 4 passes.

#### **V_SMFMAC_F32_16X16X64_FP8_BF8**

Multiply the 16x64 sparse matrix in the first input by the 64x16 matrix in the second input and accumulate the result into the 16x16 matrix stored in the destination registers using fused multiply add. Sparse indexes for the first matrix are given in the third input.

D = A (sparse 16x64) * B (64x16) + D (16x16)

Each operand contains a single matrix whose elements are distributed across all lanes of the wave. A single matrix multiply is computed and the row-column dot products are distributed across the vector ALU for higher performance.

Matrix A is a sparse matrix in FP8 float format, consuming half the physical storage of a dense matrix with same dimensions. Matrix B is a dense matrix in BF8 float format. Matrix D is single-precision float format and is both the output and the accumulate input.

2 out of every 4 elements on the K axis of matrix A are zero. The sparse indexes are used to determine which 2 elements are zero.

#### **Notes**

This instruction performs 4 passes.

#### **V_SMFMAC_F32_16X16X64_FP8_FP8**

**123**

Multiply the 16x64 sparse matrix in the first input by the 64x16 matrix in the second input and accumulate the result into the 16x16 matrix stored in the destination registers using fused multiply add. Sparse indexes for the first matrix are given in the third input.

D = A (sparse 16x64) * B (64x16) + D (16x16)

Each operand contains a single matrix whose elements are distributed across all lanes of the wave. A single matrix multiply is computed and the row-column dot products are distributed across the vector ALU for higher performance.

Matrix A is a sparse matrix in FP8 float format, consuming half the physical storage of a dense matrix with same dimensions. Matrix B is a dense matrix in FP8 float format. Matrix D is single-precision float format and is both the output and the accumulate input.

2 out of every 4 elements on the K axis of matrix A are zero. The sparse indexes are used to determine which 2 elements are zero.

#### **Notes**

281 of 553

12.10. VOP3P Instructions

"AMD Instinct MI300" Instruction Set Architecture

**124**



This instruction performs 4 passes.

#### **V_SMFMAC_F32_32X32X32_BF8_BF8**

Multiply the 32x32 sparse matrix in the first input by the 32x32 matrix in the second input and accumulate the result into the 32x32 matrix stored in the destination registers using fused multiply add. Sparse indexes for the first matrix are given in the third input.

D = A (sparse 32x32) * B (32x32) + D (32x32)

Each operand contains a single matrix whose elements are distributed across all lanes of the wave. A single matrix multiply is computed and the row-column dot products are distributed across the vector ALU for higher performance.

Matrix A is a sparse matrix in BF8 float format, consuming half the physical storage of a dense matrix with same dimensions. Matrix B is a dense matrix in BF8 float format. Matrix D is single-precision float format and is both the output and the accumulate input.

2 out of every 4 elements on the K axis of matrix A are zero. The sparse indexes are used to determine which 2 elements are zero.

#### **Notes**

This instruction performs 8 passes.

#### **V_SMFMAC_F32_32X32X32_BF8_FP8**

**125**

Multiply the 32x32 sparse matrix in the first input by the 32x32 matrix in the second input and accumulate the result into the 32x32 matrix stored in the destination registers using fused multiply add. Sparse indexes for the first matrix are given in the third input.

D = A (sparse 32x32) * B (32x32) + D (32x32)

Each operand contains a single matrix whose elements are distributed across all lanes of the wave. A single matrix multiply is computed and the row-column dot products are distributed across the vector ALU for higher performance.

Matrix A is a sparse matrix in BF8 float format, consuming half the physical storage of a dense matrix with same dimensions. Matrix B is a dense matrix in FP8 float format. Matrix D is single-precision float format and is both the output and the accumulate input.

2 out of every 4 elements on the K axis of matrix A are zero. The sparse indexes are used to determine which 2 elements are zero.

#### **Notes**

282 of 553

12.10. VOP3P Instructions

"AMD Instinct MI300" Instruction Set Architecture

**126**



This instruction performs 8 passes.

#### **V_SMFMAC_F32_32X32X32_FP8_BF8**

Multiply the 32x32 sparse matrix in the first input by the 32x32 matrix in the second input and accumulate the result into the 32x32 matrix stored in the destination registers using fused multiply add. Sparse indexes for the first matrix are given in the third input.

D = A (sparse 32x32) * B (32x32) + D (32x32)

Each operand contains a single matrix whose elements are distributed across all lanes of the wave. A single matrix multiply is computed and the row-column dot products are distributed across the vector ALU for higher performance.

Matrix A is a sparse matrix in FP8 float format, consuming half the physical storage of a dense matrix with same dimensions. Matrix B is a dense matrix in BF8 float format. Matrix D is single-precision float format and is both the output and the accumulate input.

2 out of every 4 elements on the K axis of matrix A are zero. The sparse indexes are used to determine which 2 elements are zero.

#### **Notes**

This instruction performs 8 passes.

#### **V_SMFMAC_F32_32X32X32_FP8_FP8**

**127**

Multiply the 32x32 sparse matrix in the first input by the 32x32 matrix in the second input and accumulate the result into the 32x32 matrix stored in the destination registers using fused multiply add. Sparse indexes for the first matrix are given in the third input.

D = A (sparse 32x32) * B (32x32) + D (32x32)

Each operand contains a single matrix whose elements are distributed across all lanes of the wave. A single matrix multiply is computed and the row-column dot products are distributed across the vector ALU for higher performance.

Matrix A is a sparse matrix in FP8 float format, consuming half the physical storage of a dense matrix with same dimensions. Matrix B is a dense matrix in FP8 float format. Matrix D is single-precision float format and is both the output and the accumulate input.

2 out of every 4 elements on the K axis of matrix A are zero. The sparse indexes are used to determine which 2 elements are zero.

#### **Notes**

283 of 553

12.10. VOP3P Instructions

"AMD Instinct MI300" Instruction Set Architecture



This instruction performs 8 passes.

284 of 553

12.10. VOP3P Instructions

"AMD Instinct MI300" Instruction Set Architecture



## **12.11. VOP3A & VOP3B Instructions**

VOP3 instructions use one of two encodings:





|**VOP3B**|this encoding allows specifying a unique scalar destination, and is used only for:<br>V_ADD_CO_U32<br>V_SUB_CO_U32<br>V_SUBREV_CO_U32||
|---|---|---|
||V_ADDC_CO_U32||
||V_SUBB_CO_U32||
||V_SUBBREV_CO_U32<br>V_DIV_SCALE_F32||
||V_DIV_SCALE_F64||
||V_MAD_U64_U32||
||V_MAD_I64_I32||
|**VOP3A**|all other VALU instructions use this encoding||
|**V_NOP**||**384**|



Do nothing.

#### **Notes**

This instruction can be used to insert a single-cycle bubble in the vector ALU pipeline. For multiple cycles repeat this opcode.

**V_MOV_B32 385**

Move 32-bit data from a vector input into a vector register.

D0.b32 = S0.b32

#### **Notes**

Floating-point modifiers are valid for this instruction if S0 is a 32-bit floating point value. This instruction is suitable for negating or taking the absolute value of a floating-point value.

Functional examples:

285 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**V_READFIRSTLANE_B32 386**



v_mov_b32 v0, v1    // Move into v0 from v1 v_mov_b32 v0, -v1   // Set v0 to the negation of v1 v_mov_b32 v0, abs(v1)   // Set v0 to the absolute value of v1

Read the scalar value in the lowest active lane of the input vector register and store it into a scalar register.

declare lane : 32'I; if EXEC == 0x0LL then lane = 0; // Force lane 0 if all lanes are disabled else lane = s_ff1_i32_b64(EXEC); // Lowest active lane endif; D0.b32 = VGPR[lane][SRC0.u32]

#### **Notes**

Overrides EXEC mask for the VGPR read. Input and output modifiers not supported; this is an untyped operation.

**V_CVT_I32_F64**

**387**

Convert from a double-precision float input to a signed 32-bit integer value and store the result into a vector register.

D0.i32 = f64_to_i32(S0.f64)

#### **Notes**

0.5ULP accuracy, out-of-range floating point values (including infinity) saturate. NAN is converted to 0.

Generation of the INEXACT exception is controlled by the CLAMP bit. INEXACT exceptions are enabled for this conversion iff CLAMP == 1.

**V_CVT_F64_I32**

**388**

Convert from a signed 32-bit integer input to a double-precision float value and store the result into a vector register.

286 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



D0.f64 = i32_to_f64(S0.i32)

#### **Notes**

0ULP accuracy.

**V_CVT_F32_I32**

**389**

Convert from a signed 32-bit integer input to a single-precision float value and store the result into a vector register.

D0.f32 = i32_to_f32(S0.i32)

#### **Notes**

0.5ULP accuracy.

**V_CVT_F32_U32**

**390**

Convert from an unsigned 32-bit integer input to a single-precision float value and store the result into a vector register.

D0.f32 = u32_to_f32(S0.u32)

#### **Notes**

0.5ULP accuracy.

**V_CVT_U32_F32**

**391**

Convert from a single-precision float input to an unsigned 32-bit integer value and store the result into a vector register.

D0.u32 = f32_to_u32(S0.f32)

#### **Notes**

1ULP accuracy, out-of-range floating point values (including infinity) saturate. NAN is converted to 0.

Generation of the INEXACT exception is controlled by the CLAMP bit. INEXACT exceptions are enabled for this conversion iff CLAMP == 1.

287 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**392**



**V_CVT_I32_F32**

Convert from a single-precision float input to a signed 32-bit integer value and store the result into a vector register.

D0.i32 = f32_to_i32(S0.f32)

#### **Notes**

1ULP accuracy, out-of-range floating point values (including infinity) saturate. NAN is converted to 0.

Generation of the INEXACT exception is controlled by the CLAMP bit. INEXACT exceptions are enabled for this conversion iff CLAMP == 1.

**V_CVT_F16_F32**

**394**

Convert from a single-precision float input to a half-precision float value and store the result into a vector register.

D0.f16 = f32_to_f16(S0.f32)

#### **Notes**

0.5ULP accuracy, supports input modifiers and creates FP16 denormals when appropriate. Flush denorms on output if specified based on DP denorm mode. Output rounding based on DP rounding mode.

**V_CVT_F32_F16**

**395**

Convert from a half-precision float input to a single-precision float value and store the result into a vector register.

D0.f32 = f16_to_f32(S0.f16)

#### **Notes**

0ULP accuracy, FP16 denormal inputs are accepted. Flush denorms on input if specified based on DP denorm mode.

**V_CVT_RPI_I32_F32**

**396**

288 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**V_CVT_FLR_I32_F32 397**



Convert from a single-precision float input to a signed 32-bit integer value using round to nearest integer semantics (ignore the default rounding mode) and store the result into a vector register.

D0.i32 = f32_to_i32(floor(S0.f32 + 0.5F))

#### **Notes**

0.5ULP accuracy, denormals are supported.

Convert from a single-precision float input to a signed 32-bit integer value using round-down semantics (ignore the default rounding mode) and store the result into a vector register.

D0.i32 = f32_to_i32(floor(S0.f32))

#### **Notes**

1ULP accuracy, denormals are supported.

**V_CVT_OFF_F32_I4 398**

Convert from a signed 4-bit integer input to a single-precision float value using an offset table and store the result into a vector register.

Used for interpolation in shader. Lookup table on S0[3:0]:

S0 binary Result 1000 -0.5000f 1001 -0.4375f 1010 -0.3750f 1011 -0.3125f 1100 -0.2500f 1101 -0.1875f 1110 -0.1250f 1111 -0.0625f 0000 +0.0000f 0001 +0.0625f 0010 +0.1250f 0011 +0.1875f 0100 +0.2500f 0101 +0.3125f 0110 +0.3750f 0111 +0.4375f

289 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**399**



declare CVT_OFF_TABLE : 32'F[16]; D0.f32 = CVT_OFF_TABLE[S0.u32[3 : 0]]

**V_CVT_F32_F64**

Convert from a double-precision float input to a single-precision float value and store the result into a vector register.

D0.f32 = f64_to_f32(S0.f64)

#### **Notes**

0.5ULP accuracy, denormals are supported.

**V_CVT_F64_F32**

**400**

Convert from a single-precision float input to a double-precision float value and store the result into a vector register.

D0.f64 = f32_to_f64(S0.f32)

#### **Notes**

0ULP accuracy, denormals are supported.

**V_CVT_F32_UBYTE0**

**401**

Convert an unsigned byte in byte 0 of the input to a single-precision float value and store the result into a vector register.

D0.f32 = u32_to_f32(S0[7 : 0].u32)

**V_CVT_F32_UBYTE1**

**402**

Convert an unsigned byte in byte 1 of the input to a single-precision float value and store the result into a vector register.

290 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



D0.f32 = u32_to_f32(S0[15 : 8].u32)

#### **V_CVT_F32_UBYTE2**

**403**

Convert an unsigned byte in byte 2 of the input to a single-precision float value and store the result into a vector register.

D0.f32 = u32_to_f32(S0[23 : 16].u32)

**V_CVT_F32_UBYTE3**

**404**

Convert an unsigned byte in byte 3 of the input to a single-precision float value and store the result into a vector register.

D0.f32 = u32_to_f32(S0[31 : 24].u32)

**V_CVT_U32_F64**

**405**

Convert from a double-precision float input to an unsigned 32-bit integer value and store the result into a vector register.

D0.u32 = f64_to_u32(S0.f64)

#### **Notes**

0.5ULP accuracy, out-of-range floating point values (including infinity) saturate. NAN is converted to 0.

Generation of the INEXACT exception is controlled by the CLAMP bit. INEXACT exceptions are enabled for this conversion iff CLAMP == 1.

**V_CVT_F64_U32**

**406**

Convert from an unsigned 32-bit integer input to a double-precision float value and store the result into a vector register.

D0.f64 = u32_to_f64(S0.u32)

291 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



#### **Notes**

0ULP accuracy.

#### **V_TRUNC_F64**

**407**

Compute the integer part of a double-precision float input using round toward zero semantics and store the result in floating point format into a vector register.

D0.f64 = trunc(S0.f64)

#### **V_CEIL_F64**

**408**

Round the double-precision float input up to next integer and store the result in floating point format into a vector register.

D0.f64 = trunc(S0.f64); if ((S0.f64 > 0.0) && (S0.f64 != D0.f64)) then D0.f64 += 1.0 endif

#### **V_RNDNE_F64**

**409**

Round the double-precision float input to the nearest even integer and store the result in floating point format into a vector register.

D0.f64 = floor(S0.f64 + 0.5); if (isEven(floor(S0.f64)) && (fract(S0.f64) == 0.5)) then D0.f64 -= 1.0 endif

#### **V_FLOOR_F64**

**410**

Round the double-precision float input down to previous integer and store the result in floating point format into a vector register.

D0.f64 = trunc(S0.f64); if ((S0.f64 < 0.0) && (S0.f64 != D0.f64)) then D0.f64 += -1.0 endif

292 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**411**



**V_FRACT_F32**

Compute the fractional portion of a single-precision float input and store the result in floating point format into a vector register.

D0.f32 = S0.f32 + -floor(S0.f32)

#### **Notes**

#### 0.5ULP accuracy, denormals are accepted.

This is intended to comply with the DX specification of fract where the function behaves like an extension of integer modulus; be aware this may differ from how fract() is defined in other domains. For example: fract(1.2) = 0.8 in DX.

Obey round mode, result clamped to 0x3f7fffff.

#### **V_TRUNC_F32**

**412**

Compute the integer part of a single-precision float input using round toward zero semantics and store the result in floating point format into a vector register.

D0.f32 = trunc(S0.f32)

**V_CEIL_F32 413**

Round the single-precision float input up to next integer and store the result in floating point format into a vector register.

D0.f32 = trunc(S0.f32); if ((S0.f32 > 0.0F) && (S0.f32 != D0.f32)) then D0.f32 += 1.0F endif

**V_RNDNE_F32**

**414**

Round the single-precision float input to the nearest even integer and store the result in floating point format into a vector register.

D0.f32 = floor(S0.f32 + 0.5F);

293 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



if (isEven(64'F(floor(S0.f32))) && (fract(S0.f32) == 0.5F)) then D0.f32 -= 1.0F endif

**V_FLOOR_F32**

**415**

Round the single-precision float input down to previous integer and store the result in floating point format into a vector register.

D0.f32 = trunc(S0.f32); if ((S0.f32 < 0.0F) && (S0.f32 != D0.f32)) then D0.f32 += -1.0F endif

**V_EXP_F32**

**416**

Calculate 2 raised to the power of the single-precision float input and store the result into a vector register.

D0.f32 = pow(2.0F, S0.f32)

#### **Notes**

1ULP accuracy, denormals are flushed.

Functional examples:

V_EXP_F32(0xff800000) => 0x00000000     // exp(-INF) = 0 V_EXP_F32(0x80000000) => 0x3f800000     // exp(-0.0) = 1 V_EXP_F32(0x7f800000) => 0x7f800000     // exp(+INF) = +INF

**V_LOG_F32**

**417**

Calculate the base 2 logarithm of the single-precision float input and store the result into a vector register.

D0.f32 = log2(S0.f32)

#### **Notes**

1ULP accuracy, denormals are flushed.

Functional examples:

294 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



V_LOG_F32(0xff800000) => 0xffc00000     // log(-INF) = NAN V_LOG_F32(0xbf800000) => 0xffc00000     // log(-1.0) = NAN V_LOG_F32(0x80000000) => 0xff800000     // log(-0.0) = -INF V_LOG_F32(0x00000000) => 0xff800000     // log(+0.0) = -INF V_LOG_F32(0x3f800000) => 0x00000000     // log(+1.0) = 0 V_LOG_F32(0x7f800000) => 0x7f800000     // log(+INF) = +INF

**V_RCP_F32**

**418**

Calculate the reciprocal of the single-precision float input using IEEE rules and store the result into a vector register.

D0.f32 = 1.0F / S0.f32

#### **Notes**

1ULP accuracy. Accuracy converges to < 0.5ULP when using the Newton-Raphson method and 2 FMA operations. Denormals are flushed.

Functional examples:

V_RCP_F32(0xff800000) => 0x80000000     // rcp(-INF) = -0 V_RCP_F32(0xc0000000) => 0xbf000000     // rcp(-2.0) = -0.5 V_RCP_F32(0x80000000) => 0xff800000     // rcp(-0.0) = -INF V_RCP_F32(0x00000000) => 0x7f800000     // rcp(+0.0) = +INF V_RCP_F32(0x7f800000) => 0x00000000     // rcp(+INF) = +0

**V_RCP_IFLAG_F32**

**419**

Calculate the reciprocal of the vector float input in a manner suitable for integer division and store the result into a vector register. This opcode is intended for use as part of an integer division macro.

D0.f32 = 1.0F / S0.f32; // Can only raise integer DIV_BY_ZERO exception

#### **Notes**

Can raise integer DIV_BY_ZERO exception but cannot raise floating-point exceptions. To be used in an integer reciprocal macro by the compiler with one of the sequences listed below (depending on signed or unsigned operation).

Unsigned usage: CVT_F32_U32 RCP_IFLAG_F32

295 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



MUL_F32 (2**32 - 1) CVT_U32_F32

Signed usage: CVT_F32_I32 RCP_IFLAG_F32 MUL_F32 (2**31 - 1) CVT_I32_F32

**V_RSQ_F32**

**420**

Calculate the reciprocal of the square root of the single-precision float input using IEEE rules and store the result into a vector register.

D0.f32 = 1.0F / sqrt(S0.f32)

#### **Notes**

1ULP accuracy, denormals are flushed.

Functional examples:

V_RSQ_F32(0xff800000) => 0xffc00000     // rsq(-INF) = NAN V_RSQ_F32(0x80000000) => 0xff800000     // rsq(-0.0) = -INF V_RSQ_F32(0x00000000) => 0x7f800000     // rsq(+0.0) = +INF V_RSQ_F32(0x40800000) => 0x3f000000     // rsq(+4.0) = +0.5 V_RSQ_F32(0x7f800000) => 0x00000000     // rsq(+INF) = +0

**V_RCP_F64 421**

Calculate the reciprocal of the double-precision float input using IEEE rules and store the result into a vector register.

D0.f64 = 1.0 / S0.f64

#### **Notes**

This opcode has (2**29)ULP accuracy and supports denormals.

**V_RSQ_F64 422**

Calculate the reciprocal of the square root of the double-precision float input using IEEE rules and store the result into a vector register.

296 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**423**



D0.f64 = 1.0 / sqrt(S0.f64)

#### **Notes**

This opcode has (2**29)ULP accuracy and supports denormals.

**V_SQRT_F32**

Calculate the square root of the single-precision float input using IEEE rules and store the result into a vector register.

D0.f32 = sqrt(S0.f32)

#### **Notes**

1ULP accuracy, denormals are flushed.

Functional examples:

V_SQRT_F32(0xff800000) => 0xffc00000     // sqrt(-INF) = NAN V_SQRT_F32(0x80000000) => 0x80000000     // sqrt(-0.0) = -0 V_SQRT_F32(0x00000000) => 0x00000000     // sqrt(+0.0) = +0 V_SQRT_F32(0x40800000) => 0x40000000     // sqrt(+4.0) = +2.0 V_SQRT_F32(0x7f800000) => 0x7f800000     // sqrt(+INF) = +INF

**V_SQRT_F64 424**

Calculate the square root of the double-precision float input using IEEE rules and store the result into a vector register.

D0.f64 = sqrt(S0.f64)

#### **Notes**

This opcode has (2**29)ULP accuracy and supports denormals.

**V_SIN_F32 425**

Calculate the trigonometric sine of a single-precision float value using IEEE rules and store the result into a vector register. The operand is calculated by scaling the vector input by 2 PI.

297 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



D0.f32 = sin(S0.f32 * 32'F(PI * 2.0))

#### **Notes**

Denormals are supported. Full range input is supported.

Functional examples:

V_SIN_F32(0xff800000) => 0xffc00000     // sin(-INF) = NAN V_SIN_F32(0xff7fffff) => 0x00000000     // -MaxFloat, finite V_SIN_F32(0x80000000) => 0x80000000     // sin(-0.0) = -0 V_SIN_F32(0x3e800000) => 0x3f800000     // sin(0.25) = 1 V_SIN_F32(0x7f800000) => 0xffc00000     // sin(+INF) = NAN

**V_COS_F32**

**426**

Calculate the trigonometric cosine of a single-precision float value using IEEE rules and store the result into a vector register. The operand is calculated by scaling the vector input by 2 PI.

D0.f32 = cos(S0.f32 * 32'F(PI * 2.0))

#### **Notes**

Denormals are supported. Full range input is supported.

Functional examples:

V_COS_F32(0xff800000) => 0xffc00000     // cos(-INF) = NAN V_COS_F32(0xff7fffff) => 0x3f800000     // -MaxFloat, finite V_COS_F32(0x80000000) => 0x3f800000     // cos(-0.0) = 1 V_COS_F32(0x3e800000) => 0x00000000     // cos(0.25) = 0 V_COS_F32(0x7f800000) => 0xffc00000     // cos(+INF) = NAN

**V_NOT_B32**

**427**

Calculate bitwise negation on a vector input and store the result into a vector register.

D0.u32 = ~S0.u32

#### **Notes**

Input and output modifiers not supported.

298 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**428**



#### **V_BFREV_B32**

Reverse the order of bits in a vector input and store the result into a vector register.

D0.u32[31 : 0] = S0.u32[0 : 31]

#### **Notes**

Input and output modifiers not supported.

#### **V_FFBH_U32**

**429**

Count the number of leading "0" bits before the first "1" in a vector input and store the result into a vector register. Store -1 if there are no "1" bits.

D0.i32 = -1; // Set if no ones are found for i in 0 : 31 do // Search from MSB if S0.u32[31 - i] == 1'1U then D0.i32 = i; break endif endfor

#### **Notes**

Functional examples:

V_FFBH_U32(0x00000000) => 0xffffffff V_FFBH_U32(0x800000ff) => 0 V_FFBH_U32(0x100000ff) => 3 V_FFBH_U32(0x0000ffff) => 16 V_FFBH_U32(0x00000001) => 31

**V_FFBL_B32**

**430**

Count the number of trailing "0" bits before the first "1" in a vector input and store the result into a vector register. Store -1 if there are no "1" bits in the input.

D0.i32 = -1; // Set if no ones are found for i in 0 : 31 do

299 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



// Search from LSB if S0.u32[i] == 1'1U then D0.i32 = i; break endif endfor

#### **Notes**

Functional examples:

V_FFBL_B32(0x00000000) => 0xffffffff V_FFBL_B32(0xff000001) => 0 V_FFBL_B32(0xff000008) => 3 V_FFBL_B32(0xffff0000) => 16 V_FFBL_B32(0x80000000) => 31

#### **V_FFBH_I32**

**431**

Count the number of leading bits that are the same as the sign bit of a vector input and store the result into a vector register. Store -1 if all input bits are the same.

D0.i32 = -1; // Set if all bits are the same for i in 1 : 31 do // Search from MSB if S0.i32[31 - i] != S0.i32[31] then D0.i32 = i; break endif endfor

#### **Notes**

Functional examples:

V_FFBH_I32(0x00000000) => 0xffffffff V_FFBH_I32(0x40000000) => 1 V_FFBH_I32(0x80000000) => 1 V_FFBH_I32(0x0fffffff) => 4 V_FFBH_I32(0xffff0000) => 16 V_FFBH_I32(0xfffffffe) => 31 V_FFBH_I32(0xffffffff) => 0xffffffff

**V_FREXP_EXP_I32_F64**

**432**

300 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



Extract the exponent of a double-precision float input and store the result as a signed 32-bit integer into a vector register.

if ((S0.f64 == +INF) || (S0.f64 == -INF) || isNAN(S0.f64)) then D0.i32 = 0 else D0.i32 = exponent(S0.f64) - 1023 + 1 endif

#### **Notes**

This operation satisfies the invariant S0.f64 = significand * (2 ** exponent). See also V_FREXP_MANT_F64, which returns the significand. See the C library function frexp() for more information.

**V_FREXP_MANT_F64**

**433**

Extract the binary significand, or mantissa, of a double-precision float input and store the result as a doubleprecision float into a vector register.

if ((S0.f64 == +INF) || (S0.f64 == -INF) || isNAN(S0.f64)) then D0.f64 = S0.f64 else D0.f64 = mantissa(S0.f64) endif

#### **Notes**

This operation satisfies the invariant S0.f64 = significand * (2 ** exponent). Result range is in (-1.0,-0.5][0.5,1.0) in normal cases. See also V_FREXP_EXP_I32_F64, which returns integer exponent. See the C library function frexp() for more information.

**V_FRACT_F64 434**

Compute the fractional portion of a double-precision float input and store the result in floating point format into a vector register.

D0.f64 = S0.f64 + -floor(S0.f64)

#### **Notes**

0.5ULP accuracy, denormals are accepted.

This is intended to comply with the DX specification of fract where the function behaves like an extension of integer modulus; be aware this may differ from how fract() is defined in other domains. For example: fract(1.2) = 0.8 in DX.

301 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



Obey round mode, result clamped to 0x3fefffffffffffff.

#### **V_FREXP_EXP_I32_F32**

**435**

Extract the exponent of a single-precision float input and store the result as a signed 32-bit integer into a vector register.

if ((64'F(S0.f32) == +INF) || (64'F(S0.f32) == -INF) || isNAN(64'F(S0.f32))) then D0.i32 = 0 else D0.i32 = exponent(S0.f32) - 127 + 1 endif

#### **Notes**

This operation satisfies the invariant S0.f32 = significand * (2 ** exponent). See also V_FREXP_MANT_F32, which returns the significand. See the C library function frexp() for more information.

#### **V_FREXP_MANT_F32**

**436**

Extract the binary significand, or mantissa, of a single-precision float input and store the result as a singleprecision float into a vector register.

if ((64'F(S0.f32) == +INF) || (64'F(S0.f32) == -INF) || isNAN(64'F(S0.f32))) then D0.f32 = S0.f32 else D0.f32 = mantissa(S0.f32) endif

#### **Notes**

This operation satisfies the invariant S0.f32 = significand * (2 ** exponent). Result range is in (-1.0,-0.5][0.5,1.0) in normal cases. See also V_FREXP_EXP_I32_F32, which returns integer exponent. See the C library function frexp() for more information.

**V_CLREXCP 437**

Clear this wave's exception state in the vector ALU.

**V_MOV_B64 440**

Move data from a 64-bit vector input into a vector register.

302 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



D0.b64 = S0.b64

#### **Notes**

Floating-point modifiers are valid for this instruction if S0.u64 is a 64-bit floating point value. This instruction is suitable for negating or taking the absolute value of a floating-point value.

**V_CVT_F16_U16**

**441**

Convert from an unsigned 16-bit integer input to a half-precision float value and store the result into a vector register.

D0.f16 = u16_to_f16(S0.u16)

#### **Notes**

0.5ULP accuracy, supports denormals, rounding, exception flags and saturation.

**V_CVT_F16_I16 442**

Convert from a signed 16-bit integer input to a half-precision float value and store the result into a vector register.

D0.f16 = i16_to_f16(S0.i16)

#### **Notes**

0.5ULP accuracy, supports denormals, rounding, exception flags and saturation.

**V_CVT_U16_F16 443**

Convert from a half-precision float input to an unsigned 16-bit integer value and store the result into a vector register.

D0.u16 = f16_to_u16(S0.f16)

#### **Notes**

1ULP accuracy, supports rounding, exception flags and saturation. FP16 denormals are accepted. Conversion is done with truncation.

303 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



Generation of the INEXACT exception is controlled by the CLAMP bit. INEXACT exceptions are enabled for this conversion iff CLAMP == 1.

**V_CVT_I16_F16**

**444**

Convert from a half-precision float input to a signed 16-bit integer value and store the result into a vector register.

D0.i16 = f16_to_i16(S0.f16)

#### **Notes**

1ULP accuracy, supports rounding, exception flags and saturation. FP16 denormals are accepted. Conversion is done with truncation.

Generation of the INEXACT exception is controlled by the CLAMP bit. INEXACT exceptions are enabled for this conversion iff CLAMP == 1.

**V_RCP_F16**

**445**

Calculate the reciprocal of the half-precision float input using IEEE rules and store the result into a vector register.

D0.f16 = 16'1.0 / S0.f16

#### **Notes**

1ULP accuracy.

Functional examples:

V_RCP_F16(0xfc00) => 0x8000     // rcp(-INF) = -0 V_RCP_F16(0xc000) => 0xb800     // rcp(-2.0) = -0.5 V_RCP_F16(0x8000) => 0xfc00     // rcp(-0.0) = -INF V_RCP_F16(0x0000) => 0x7c00     // rcp(+0.0) = +INF V_RCP_F16(0x7c00) => 0x0000     // rcp(+INF) = +0

**V_SQRT_F16**

**446**

Calculate the square root of the half-precision float input using IEEE rules and store the result into a vector register.

304 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



D0.f16 = sqrt(S0.f16)

#### **Notes**

1ULP accuracy, denormals are supported.

Functional examples:

V_SQRT_F16(0xfc00) => 0xfe00     // sqrt(-INF) = NAN V_SQRT_F16(0x8000) => 0x8000     // sqrt(-0.0) = -0 V_SQRT_F16(0x0000) => 0x0000     // sqrt(+0.0) = +0 V_SQRT_F16(0x4400) => 0x4000     // sqrt(+4.0) = +2.0 V_SQRT_F16(0x7c00) => 0x7c00     // sqrt(+INF) = +INF

**V_RSQ_F16**

**447**

Calculate the reciprocal of the square root of the half-precision float input using IEEE rules and store the result into a vector register.

D0.f16 = 16'1.0 / sqrt(S0.f16)

#### **Notes**

1ULP accuracy, denormals are supported.

Functional examples:

V_RSQ_F16(0xfc00) => 0xfe00     // rsq(-INF) = NAN V_RSQ_F16(0x8000) => 0xfc00     // rsq(-0.0) = -INF V_RSQ_F16(0x0000) => 0x7c00     // rsq(+0.0) = +INF V_RSQ_F16(0x4400) => 0x3800     // rsq(+4.0) = +0.5 V_RSQ_F16(0x7c00) => 0x0000     // rsq(+INF) = +0

**V_LOG_F16**

**448**

Calculate the base 2 logarithm of the half-precision float input and store the result into a vector register.

D0.f16 = log2(S0.f16)

#### **Notes**

1ULP accuracy, denormals are supported.

305 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



Functional examples:

V_LOG_F16(0xfc00) => 0xfe00     // log(-INF) = NAN V_LOG_F16(0xbc00) => 0xfe00     // log(-1.0) = NAN V_LOG_F16(0x8000) => 0xfc00     // log(-0.0) = -INF V_LOG_F16(0x0000) => 0xfc00     // log(+0.0) = -INF V_LOG_F16(0x3c00) => 0x0000     // log(+1.0) = 0 V_LOG_F16(0x7c00) => 0x7c00     // log(+INF) = +INF

**V_EXP_F16**

**449**

Calculate 2 raised to the power of the half-precision float input and store the result into a vector register.

D0.f16 = pow(16'2.0, S0.f16)

#### **Notes**

1ULP accuracy, denormals are supported.

Functional examples:

V_EXP_F16(0xfc00) => 0x0000     // exp(-INF) = 0 V_EXP_F16(0x8000) => 0x3c00     // exp(-0.0) = 1 V_EXP_F16(0x7c00) => 0x7c00     // exp(+INF) = +INF

**V_FREXP_MANT_F16**

**450**

Extract the binary significand, or mantissa, of a half-precision float input and store the result as a halfprecision float into a vector register.

if ((64'F(S0.f16) == +INF) || (64'F(S0.f16) == -INF) || isNAN(64'F(S0.f16))) then D0.f16 = S0.f16 else D0.f16 = mantissa(S0.f16) endif

#### **Notes**

This operation satisfies the invariant S0.f16 = significand * (2 ** exponent). Result range is in (-1.0,-0.5][0.5,1.0) in normal cases. See also V_FREXP_EXP_I16_F16, which returns integer exponent. See the C library function frexp() for more information.

306 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**V_FREXP_EXP_I16_F16**

**451**



Extract the exponent of a half-precision float input and store the result as a signed 16-bit integer into a vector register.

if ((64'F(S0.f16) == +INF) || (64'F(S0.f16) == -INF) || isNAN(64'F(S0.f16))) then D0.i16 = 16'0 else D0.i16 = 16'I(exponent(S0.f16) - 15 + 1) endif

#### **Notes**

This operation satisfies the invariant S0.f16 = significand * (2 ** exponent). See also V_FREXP_MANT_F16, which returns the significand. See the C library function frexp() for more information.

**V_FLOOR_F16**

**452**

Round the half-precision float input down to previous integer and store the result in floating point format into a vector register.

D0.f16 = trunc(S0.f16); if ((S0.f16 < 16'0.0) && (S0.f16 != D0.f16)) then D0.f16 += -16'1.0 endif

#### **V_CEIL_F16**

**453**

Round the half-precision float input up to next integer and store the result in floating point format into a vector register.

D0.f16 = trunc(S0.f16); if ((S0.f16 > 16'0.0) && (S0.f16 != D0.f16)) then D0.f16 += 16'1.0 endif

#### **V_TRUNC_F16**

**454**

Compute the integer part of a half-precision float input using round toward zero semantics and store the result in floating point format into a vector register.

D0.f16 = trunc(S0.f16)

307 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



#### **V_RNDNE_F16**

**455**

Round the half-precision float input to the nearest even integer and store the result in floating point format into a vector register.

D0.f16 = floor(S0.f16 + 16'0.5); if (isEven(64'F(floor(S0.f16))) && (fract(S0.f16) == 16'0.5)) then D0.f16 -= 16'1.0 endif

#### **V_FRACT_F16**

**456**

Compute the fractional portion of a half-precision float input and store the result in floating point format into a vector register.

D0.f16 = S0.f16 + -floor(S0.f16)

#### **Notes**

#### 0.5ULP accuracy, denormals are accepted.

This is intended to comply with the DX specification of fract where the function behaves like an extension of integer modulus; be aware this may differ from how fract() is defined in other domains. For example: fract(1.2) = 0.8 in DX.

#### **V_SIN_F16**

**457**

Calculate the trigonometric sine of a half-precision float value using IEEE rules and store the result into a vector register. The operand is calculated by scaling the vector input by 2 PI.

D0.f16 = sin(S0.f16 * 16'F(PI * 2.0))

#### **Notes**

Denormals are supported. Full range input is supported.

Functional examples:

V_SIN_F16(0xfc00) => 0xfe00     // sin(-INF) = NAN V_SIN_F16(0xfbff) => 0x0000     // Most negative finite FP16 V_SIN_F16(0x8000) => 0x8000     // sin(-0.0) = -0 V_SIN_F16(0x3400) => 0x3c00     // sin(0.25) = 1

308 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



V_SIN_F16(0x7bff) => 0x0000     // Most positive finite FP16 V_SIN_F16(0x7c00) => 0xfe00     // sin(+INF) = NAN

#### **V_COS_F16**

**458**

Calculate the trigonometric cosine of a half-precision float value using IEEE rules and store the result into a vector register. The operand is calculated by scaling the vector input by 2 PI.

D0.f16 = cos(S0.f16 * 16'F(PI * 2.0))

#### **Notes**

Denormals are supported. Full range input is supported.

Functional examples:

V_COS_F16(0xfc00) => 0xfe00     // cos(-INF) = NAN V_COS_F16(0xfbff) => 0x3c00     // Most negative finite FP16 V_COS_F16(0x8000) => 0x3c00     // cos(-0.0) = 1 V_COS_F16(0x3400) => 0x0000     // cos(0.25) = 0 V_COS_F16(0x7bff) => 0x3c00     // Most positive finite FP16 V_COS_F16(0x7c00) => 0xfe00     // cos(+INF) = NAN

**V_CVT_NORM_I16_F16**

**461**

Convert from a half-precision float input to a signed normalized short and store the result into a vector register.

D0.i16 = f16_to_snorm(S0.f16)

#### **Notes**

0.5ULP accuracy, supports rounding, exception flags and saturation, denormals are supported.

**V_CVT_NORM_U16_F16 462**

Convert from a half-precision float input to an unsigned normalized short and store the result into a vector register.

D0.u16 = f16_to_unorm(S0.f16)

309 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**463**



#### **Notes**

0.5ULP accuracy, supports rounding, exception flags and saturation, denormals are supported.

#### **V_SAT_PK_U8_I16**

Given 2 signed 16-bit integer inputs, saturate each input over an unsigned 8-bit integer range, pack the resulting values into a packed 16-bit value and store the result into a vector register.

SAT8 = lambda(n) ( if n <= 16'0 then return 8'0U elsif n >= 16'255 then return 8'255U else return n[7 : 0].u8 endif); tmp = 16'0; tmp[7 : 0].u8 = SAT8(S0[15 : 0].i16); tmp[15 : 8].u8 = SAT8(S0[31 : 16].i16); D0.b16 = tmp.b16

#### **Notes**

Used for 4x16bit data packed as 4x8bit data.

**V_SWAP_B32 465**

Swap the values in two vector registers.

tmp = D0.b32; D0.b32 = S0.b32; S0.b32 = tmp

#### **Notes**

Input and output modifiers not supported; this is an untyped operation.

**V_ACCVGPR_MOV_B32 466**

Move data from one accumulator register to another accumulator register.

**V_CVT_F32_FP8 468**

310 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



Convert from an FP8 float input to a single-precision float value and store the result into a vector register.

if SDWA_SRC0_SEL == BYTE1.b3 then D0.f32 = fp8_to_f32(S0[15 : 8].fp8) elsif SDWA_SRC0_SEL == BYTE2.b3 then D0.f32 = fp8_to_f32(S0[23 : 16].fp8) elsif SDWA_SRC0_SEL == BYTE3.b3 then D0.f32 = fp8_to_f32(S0[31 : 24].fp8) else // BYTE0 implied D0.f32 = fp8_to_f32(S0[7 : 0].fp8) endif

#### **Notes**

SDWA encoding allows SRC0_SEL to control which byte of S0 is converted. Only the BYTE selects of SRC0_SEL are legal. If this instruction is not encoded in SDWA then BYTE0 is implied.

#### **V_CVT_F32_BF8**

**469**

Convert from a BF8 float input to a single-precision float value and store the result into a vector register.

if SDWA_SRC0_SEL == BYTE1.b3 then D0.f32 = bf8_to_f32(S0[15 : 8].bf8) elsif SDWA_SRC0_SEL == BYTE2.b3 then D0.f32 = bf8_to_f32(S0[23 : 16].bf8) elsif SDWA_SRC0_SEL == BYTE3.b3 then D0.f32 = bf8_to_f32(S0[31 : 24].bf8) else // BYTE0 implied D0.f32 = bf8_to_f32(S0[7 : 0].bf8) endif

#### **Notes**

SDWA encoding allows SRC0_SEL to control which byte of S0 is converted. Only the BYTE selects of SRC0_SEL are legal. If this instruction is not encoded in SDWA then BYTE0 is implied.

**V_CVT_PK_F32_FP8**

**470**

Convert from a packed 2-component FP8 float input to a packed single-precision float value and store the result into a vector register.

tmp = SDWA_SRC0_SEL[1 : 0] == WORD1.b2 ? S0[31 : 16] : S0[15 : 0]; D0[31 : 0].f32 = fp8_to_f32(tmp[7 : 0].fp8); D0[63 : 32].f32 = fp8_to_f32(tmp[15 : 8].fp8)

311 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



#### **Notes**

SDWA encoding allows SRC0_SEL to control which word of S0 is converted. Only the WORD selects of SRC0_SEL are legal. If this instruction is not encoded in SDWA then WORD0 is implied.

**V_CVT_PK_F32_BF8**

**471**

Convert from a packed 2-component BF8 float input to a packed single-precision float value and store the result into a vector register.

tmp = SDWA_SRC0_SEL[1 : 0] == WORD1.b2 ? S0[31 : 16] : S0[15 : 0]; D0[31 : 0].f32 = bf8_to_f32(tmp[7 : 0].bf8); D0[63 : 32].f32 = bf8_to_f32(tmp[15 : 8].bf8)

#### **Notes**

SDWA encoding allows SRC0_SEL to control which word of S0 is converted. Only the WORD selects of SRC0_SEL are legal. If this instruction is not encoded in SDWA then WORD0 is implied.

**V_CNDMASK_B32 256**

Copy data from one of two inputs based on the per-lane condition code and store the result into a vector register.

D0.u32 = VCC.u64[laneId] ? S1.u32 : S0.u32

#### **Notes**

In VOP3 the VCC source may be a scalar GPR specified in S2.

Floating-point modifiers are valid for this instruction if S0 and S1 are 32-bit floating point values. This instruction is suitable for negating or taking the absolute value of a floating-point value.

**V_ADD_F32 257**

Add two floating point inputs and store the result into a vector register.

D0.f32 = S0.f32 + S1.f32

#### **Notes**

0.5ULP precision, denormals are supported.

312 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**V_SUB_F32**

**258**



Subtract the second floating point input from the first input and store the result into a vector register.

D0.f32 = S0.f32 - S1.f32

#### **Notes**

0.5ULP precision, denormals are supported.

**V_SUBREV_F32**

**259**

Subtract the _first_ floating point input from the _second_ input and store the result into a vector register.

D0.f32 = S1.f32 - S0.f32

#### **Notes**

0.5ULP precision, denormals are supported.

**V_FMAC_F64 260**

Multiply two floating point inputs and accumulate the result into the destination register using fused multiply add.

D0.f64 = fma(S0.f64, S1.f64, D0.f64)

**V_MUL_F32**

**261**

Multiply two floating point inputs and store the result into a vector register.

D0.f32 = S0.f32 * S1.f32

#### **Notes**

0.5ULP precision, denormals are supported.

**V_MUL_I32_I24**

**262**

313 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



Multiply two signed 24-bit integer inputs and store the result as a signed 32-bit integer into a vector register.

D0.i32 = 32'I(S0.i24) * 32'I(S1.i24)

#### **Notes**

This opcode is expected to be as efficient as basic single-precision opcodes since it utilizes the single-precision floating point multiplier. See also V_MUL_HI_I32_I24.

**V_MUL_HI_I32_I24**

**263**

Multiply two signed 24-bit integer inputs and store the high 32 bits of the result as a signed 32-bit integer into a vector register.

D0.i32 = 32'I((64'I(S0.i24) * 64'I(S1.i24)) >> 32U)

#### **Notes**

See also V_MUL_I32_I24.

**V_MUL_U32_U24**

**264**

Multiply two unsigned 24-bit integer inputs and store the result as an unsigned 32-bit integer into a vector register.

D0.u32 = 32'U(S0.u24) * 32'U(S1.u24)

#### **Notes**

This opcode is expected to be as efficient as basic single-precision opcodes since it utilizes the single-precision floating point multiplier. See also V_MUL_HI_U32_U24.

**V_MUL_HI_U32_U24**

**265**

Multiply two unsigned 24-bit integer inputs and store the high 32 bits of the result as an unsigned 32-bit integer into a vector register.

D0.u32 = 32'U((64'U(S0.u24) * 64'U(S1.u24)) >> 32U)

#### **Notes**

314 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



See also V_MUL_U32_U24.

#### **V_MIN_F32**

**266**

Select the minimum of two single-precision float inputs and store the result into a vector register.

if (WAVE_MODE.IEEE && isSignalNAN(64'F(S0.f32))) then D0.f32 = 32'F(cvtToQuietNAN(64'F(S0.f32))) elsif (WAVE_MODE.IEEE && isSignalNAN(64'F(S1.f32))) then D0.f32 = 32'F(cvtToQuietNAN(64'F(S1.f32))) elsif isNAN(64'F(S0.f32)) then D0.f32 = S1.f32 elsif isNAN(64'F(S1.f32)) then D0.f32 = S0.f32 elsif ((64'F(S0.f32) == +0.0) && (64'F(S1.f32) == -0.0)) then D0.f32 = S1.f32 elsif ((64'F(S0.f32) == -0.0) && (64'F(S1.f32) == +0.0)) then D0.f32 = S0.f32 else // Note: there's no IEEE case here like there is for V_MAX_F32. D0.f32 = S0.f32 < S1.f32 ? S0.f32 : S1.f32 endif

#### **V_MAX_F32**

**267**

Select the maximum of two single-precision float inputs and store the result into a vector register.

if (WAVE_MODE.IEEE && isSignalNAN(64'F(S0.f32))) then D0.f32 = 32'F(cvtToQuietNAN(64'F(S0.f32))) elsif (WAVE_MODE.IEEE && isSignalNAN(64'F(S1.f32))) then D0.f32 = 32'F(cvtToQuietNAN(64'F(S1.f32))) elsif isNAN(64'F(S0.f32)) then D0.f32 = S1.f32 elsif isNAN(64'F(S1.f32)) then D0.f32 = S0.f32 elsif ((64'F(S0.f32) == +0.0) && (64'F(S1.f32) == -0.0)) then D0.f32 = S0.f32 elsif ((64'F(S0.f32) == -0.0) && (64'F(S1.f32) == +0.0)) then D0.f32 = S1.f32 elsif WAVE_MODE.IEEE then D0.f32 = S0.f32 >= S1.f32 ? S0.f32 : S1.f32 else D0.f32 = S0.f32 > S1.f32 ? S0.f32 : S1.f32 endif

**V_MIN_I32**

**268**

315 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



Select the minimum of two signed 32-bit integer inputs and store the selected value into a vector register.

D0.i32 = S0.i32 < S1.i32 ? S0.i32 : S1.i32

#### **V_MAX_I32**

**269**

Select the maximum of two signed 32-bit integer inputs and store the selected value into a vector register.

D0.i32 = S0.i32 >= S1.i32 ? S0.i32 : S1.i32

#### **V_MIN_U32**

**270**

Select the minimum of two unsigned 32-bit integer inputs and store the selected value into a vector register.

D0.u32 = S0.u32 < S1.u32 ? S0.u32 : S1.u32

#### **V_MAX_U32**

**271**

Select the maximum of two unsigned 32-bit integer inputs and store the selected value into a vector register.

D0.u32 = S0.u32 >= S1.u32 ? S0.u32 : S1.u32

#### **V_LSHRREV_B32**

**272**

Given a shift count in the _first_ vector input, calculate the logical shift right of the _second_ vector input and store the result into a vector register.

D0.u32 = (S1.u32 >> S0[4 : 0].u32)

**V_ASHRREV_I32 273**

Given a shift count in the _first_ vector input, calculate the arithmetic shift right (preserving sign bit) of the _second_ vector input and store the result into a vector register.

316 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**274**



D0.i32 = (S1.i32 >> S0[4 : 0].u32)

#### **V_LSHLREV_B32**

Given a shift count in the _first_ vector input, calculate the logical shift left of the _second_ vector input and store the result into a vector register.

D0.u32 = (S1.u32 << S0[4 : 0].u32)

**V_AND_B32**

**275**

Calculate bitwise AND on two vector inputs and store the result into a vector register.

D0.u32 = (S0.u32 & S1.u32)

#### **Notes**

Input and output modifiers not supported.

**V_OR_B32**

**276**

Calculate bitwise OR on two vector inputs and store the result into a vector register.

D0.u32 = (S0.u32 | S1.u32)

#### **Notes**

Input and output modifiers not supported.

**V_XOR_B32 277**

Calculate bitwise XOR on two vector inputs and store the result into a vector register.

D0.u32 = (S0.u32 ^ S1.u32)

#### **Notes**

Input and output modifiers not supported.

317 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**281**



#### **V_ADD_CO_U32**

Add two unsigned 32-bit integer inputs, store the result into a vector register and store the carry-out mask into a scalar register.

tmp = 64'U(S0.u32) + 64'U(S1.u32); VCC.u64[laneId] = tmp >= 0x100000000ULL ? 1'1U : 1'0U; // VCC is an UNSIGNED overflow/carry-out for V_ADDC_CO_U32. D0.u32 = tmp.u32

#### **Notes**

In VOP3 the VCC destination may be an arbitrary SGPR-pair.

Supports saturation (unsigned 32-bit integer domain).

**V_SUB_CO_U32**

**282**

Subtract the second unsigned 32-bit integer input from the first input, store the result into a vector register and store the carry-out mask into a scalar register.

tmp = S0.u32 - S1.u32; VCC.u64[laneId] = S1.u32 > S0.u32 ? 1'1U : 1'0U; // VCC is an UNSIGNED overflow/carry-out for V_SUBB_CO_U32. D0.u32 = tmp.u32

#### **Notes**

In VOP3 the VCC destination may be an arbitrary SGPR-pair.

Supports saturation (unsigned 32-bit integer domain).

#### **V_SUBREV_CO_U32**

**283**

Subtract the _first_ unsigned 32-bit integer input from the _second_ input, store the result into a vector register and store the carry-out mask into a scalar register.

tmp = S1.u32 - S0.u32; VCC.u64[laneId] = S0.u32 > S1.u32 ? 1'1U : 1'0U; // VCC is an UNSIGNED overflow/carry-out for V_SUBB_CO_U32. D0.u32 = tmp.u32

#### **Notes**

318 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**284**



In VOP3 the VCC destination may be an arbitrary SGPR-pair.

Supports saturation (unsigned 32-bit integer domain).

#### **V_ADDC_CO_U32**

Add two unsigned 32-bit integer inputs and a bit from a carry-in mask, store the result into a vector register and store the carry-out mask into a scalar register.

tmp = 64'U(S0.u32) + 64'U(S1.u32) + VCC.u64[laneId].u64; VCC.u64[laneId] = tmp >= 0x100000000ULL ? 1'1U : 1'0U; // VCC is an UNSIGNED overflow/carry-out for V_ADDC_CO_U32. D0.u32 = tmp.u32

#### **Notes**

In VOP3 the VCC destination may be an arbitrary SGPR-pair, and the VCC source comes from the SGPR-pair at S2.u.

Supports saturation (unsigned 32-bit integer domain).

#### **V_SUBB_CO_U32**

**285**

Subtract the second unsigned 32-bit integer input from the first input, subtract a bit from the carry-in mask, store the result into a vector register and store the carry-out mask into a scalar register.

tmp = S0.u32 - S1.u32 - VCC.u64[laneId].u32; VCC.u64[laneId] = 64'U(S1.u32) + VCC.u64[laneId].u64 > 64'U(S0.u32) ? 1'1U : 1'0U; // VCC is an UNSIGNED overflow/carry-out for V_SUBB_CO_U32. D0.u32 = tmp.u32

#### **Notes**

In VOP3 the VCC destination may be an arbitrary SGPR-pair, and the VCC source comes from the SGPR-pair at S2.u.

Supports saturation (unsigned 32-bit integer domain).

#### **V_SUBBREV_CO_U32**

**286**

Subtract the _first_ unsigned 32-bit integer input from the _second_ input, subtract a bit from the carry-in mask, store the result into a vector register and store the carry-out mask into a scalar register.

tmp = S1.u32 - S0.u32 - VCC.u64[laneId].u32;

319 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**V_ADD_F16 287**



VCC.u64[laneId] = 64'U(S0.u32) + VCC.u64[laneId].u64 > 64'U(S1.u32) ? 1'1U : 1'0U; // VCC is an UNSIGNED overflow/carry-out for V_SUBB_CO_U32. D0.u32 = tmp.u32

#### **Notes**

In VOP3 the VCC destination may be an arbitrary SGPR-pair, and the VCC source comes from the SGPR-pair at S2.u.

Supports saturation (unsigned 32-bit integer domain).

Add two floating point inputs and store the result into a vector register.

D0.f16 = S0.f16 + S1.f16

#### **Notes**

0.5ULP precision. Supports denormals, round mode, exception flags and saturation.

**V_SUB_F16 288**

Subtract the second floating point input from the first input and store the result into a vector register.

D0.f16 = S0.f16 - S1.f16

#### **Notes**

0.5ULP precision. Supports denormals, round mode, exception flags and saturation.

**V_SUBREV_F16**

**289**

Subtract the _first_ floating point input from the _second_ input and store the result into a vector register.

D0.f16 = S1.f16 - S0.f16

#### **Notes**

0.5ULP precision. Supports denormals, round mode, exception flags and saturation.

320 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**V_MUL_F16**

**290**



Multiply two floating point inputs and store the result into a vector register.

D0.f16 = S0.f16 * S1.f16

#### **Notes**

0.5ULP precision. Supports denormals, round mode, exception flags and saturation.

**V_MAC_F16**

**291**

Multiply two floating point inputs and accumulate the result into the destination register. Implements IEEE rules and non-standard rule for OPSEL.

tmp = S0.f16 * S1.f16 + D0.f16; if OPSEL.u4[3] then D0 = { tmp.f16, D0[15 : 0] } else D0 = { 16'0, tmp.f16 } endif

#### **Notes**

Supports round mode, exception flags, saturation.

**V_ADD_U16 294**

Add two unsigned 16-bit integer inputs and store the result into a vector register. No carry-in or carry-out support.

D0.u16 = S0.u16 + S1.u16

#### **Notes**

Supports saturation (unsigned 16-bit integer domain).

**V_SUB_U16**

**295**

Subtract the second unsigned 16-bit integer input from the first input and store the result into a vector register. No carry-in or carry-out support.

321 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



D0.u16 = S0.u16 - S1.u16

#### **Notes**

Supports saturation (unsigned 16-bit integer domain).

#### **V_SUBREV_U16**

**296**

Subtract the _first_ unsigned 16-bit integer input from the _second_ input and store the result into a vector register. No carry-in or carry-out support.

D0.u16 = S1.u16 - S0.u16

#### **Notes**

Supports saturation (unsigned 16-bit integer domain).

**V_MUL_LO_U16**

**297**

Multiply two unsigned 16-bit integer inputs and store the low bits of the result into a vector register.

D0.u16 = S0.u16 * S1.u16

#### **Notes**

Supports saturation (unsigned 16-bit integer domain).

#### **V_LSHLREV_B16**

**298**

Given a shift count in the _first_ vector input, calculate the logical shift left of the _second_ vector input and store the result into a vector register.

D0.u16 = (S1.u16 << S0[3 : 0].u32)

#### **V_LSHRREV_B16**

**299**

Given a shift count in the _first_ vector input, calculate the logical shift right of the _second_ vector input and store the result into a vector register.

322 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



D0.u16 = (S1.u16 >> S0[3 : 0].u32)

#### **V_ASHRREV_I16**

**300**

Given a shift count in the _first_ vector input, calculate the arithmetic shift right (preserving sign bit) of the _second_ vector input and store the result into a vector register.

D0.i16 = (S1.i16 >> S0[3 : 0].u32)

**V_MAX_F16**

**301**

Select the maximum of two half-precision float inputs and store the result into a vector register.

if (WAVE_MODE.IEEE && isSignalNAN(64'F(S0.f16))) then D0.f16 = 16'F(cvtToQuietNAN(64'F(S0.f16))) elsif (WAVE_MODE.IEEE && isSignalNAN(64'F(S1.f16))) then D0.f16 = 16'F(cvtToQuietNAN(64'F(S1.f16))) elsif isNAN(64'F(S0.f16)) then D0.f16 = S1.f16 elsif isNAN(64'F(S1.f16)) then D0.f16 = S0.f16 elsif ((64'F(S0.f16) == +0.0) && (64'F(S1.f16) == -0.0)) then D0.f16 = S0.f16 elsif ((64'F(S0.f16) == -0.0) && (64'F(S1.f16) == +0.0)) then D0.f16 = S1.f16 elsif WAVE_MODE.IEEE then D0.f16 = S0.f16 >= S1.f16 ? S0.f16 : S1.f16 else D0.f16 = S0.f16 > S1.f16 ? S0.f16 : S1.f16 endif

#### **Notes**

IEEE compliant. Supports denormals, round mode, exception flags, saturation.

**V_MIN_F16**

**302**

Select the minimum of two half-precision float inputs and store the result into a vector register.

if (WAVE_MODE.IEEE && isSignalNAN(64'F(S0.f16))) then D0.f16 = 16'F(cvtToQuietNAN(64'F(S0.f16))) elsif (WAVE_MODE.IEEE && isSignalNAN(64'F(S1.f16))) then D0.f16 = 16'F(cvtToQuietNAN(64'F(S1.f16))) elsif isNAN(64'F(S0.f16)) then

323 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



D0.f16 = S1.f16 elsif isNAN(64'F(S1.f16)) then D0.f16 = S0.f16 elsif ((64'F(S0.f16) == +0.0) && (64'F(S1.f16) == -0.0)) then D0.f16 = S1.f16 elsif ((64'F(S0.f16) == -0.0) && (64'F(S1.f16) == +0.0)) then D0.f16 = S0.f16 else // Note: there's no IEEE case here like there is for V_MAX_F16. D0.f16 = S0.f16 < S1.f16 ? S0.f16 : S1.f16 endif

#### **Notes**

IEEE compliant. Supports denormals, round mode, exception flags, saturation.

#### **V_MAX_U16**

**303**

Select the maximum of two unsigned 16-bit integer inputs and store the selected value into a vector register.

D0.u16 = S0.u16 >= S1.u16 ? S0.u16 : S1.u16

#### **V_MAX_I16**

**304**

Select the maximum of two signed 16-bit integer inputs and store the selected value into a vector register.

D0.i16 = S0.i16 >= S1.i16 ? S0.i16 : S1.i16

**V_MIN_U16 305**

Select the minimum of two unsigned 16-bit integer inputs and store the selected value into a vector register.

D0.u16 = S0.u16 < S1.u16 ? S0.u16 : S1.u16

#### **V_MIN_I16**

**306**

Select the minimum of two signed 16-bit integer inputs and store the selected value into a vector register.

D0.i16 = S0.i16 < S1.i16 ? S0.i16 : S1.i16

324 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**307**



#### **V_LDEXP_F16**

Multiply the first input, a floating point value, by an integral power of 2 specified in the second input, a signed integer value, and store the floating point result into a vector register.

D0.f16 = S0.f16 * 16'F(2.0F ** 32'I(S1.i16))

#### **Notes**

Compare with the ldexp() function in C. Note that the S1 has a format of f16 since floating point literal constants are interpreted as 16 bit value for this opcode.

**V_ADD_U32**

**308**

Add two unsigned 32-bit integer inputs and store the result into a vector register. No carry-in or carry-out support.

D0.u32 = S0.u32 + S1.u32

#### **Notes**

Supports saturation (unsigned 32-bit integer domain).

#### **V_SUB_U32**

**309**

Subtract the second unsigned 32-bit integer input from the first input and store the result into a vector register. No carry-in or carry-out support.

D0.u32 = S0.u32 - S1.u32

#### **Notes**

Supports saturation (unsigned 32-bit integer domain).

#### **V_SUBREV_U32**

**310**

Subtract the _first_ unsigned 32-bit integer input from the _second_ input and store the result into a vector register. No carry-in or carry-out support.

325 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



D0.u32 = S1.u32 - S0.u32

#### **Notes**

Supports saturation (unsigned 32-bit integer domain).

#### **V_DOT2C_F32_F16**

**311**

Compute the dot product of two packed 2-D half-precision float inputs in the single-precision float domain and accumulate with the single-precision float value in the destination register.

tmp = D0.f32; tmp += f16_to_f32(S0[15 : 0].f16) * f16_to_f32(S1[15 : 0].f16); tmp += f16_to_f32(S0[31 : 16].f16) * f16_to_f32(S1[31 : 16].f16); D0.f32 = tmp

#### **V_DOT2C_I32_I16**

**312**

Compute the dot product of two packed 2-D signed 16-bit integer inputs in the signed 32-bit integer domain and accumulate with the signed 32-bit integer value in the destination register.

tmp = D0.i32; tmp += i16_to_i32(S0[15 : 0].i16) * i16_to_i32(S1[15 : 0].i16); tmp += i16_to_i32(S0[31 : 16].i16) * i16_to_i32(S1[31 : 16].i16); D0.i32 = tmp

#### **V_DOT4C_I32_I8**

**313**

Compute the dot product of two packed 4-D signed 8-bit integer inputs in the signed 32-bit integer domain and accumulate with the signed 32-bit integer value in the destination register.

tmp = D0.i32; tmp += i8_to_i32(S0[7 : 0].i8) * i8_to_i32(S1[7 : 0].i8); tmp += i8_to_i32(S0[15 : 8].i8) * i8_to_i32(S1[15 : 8].i8); tmp += i8_to_i32(S0[23 : 16].i8) * i8_to_i32(S1[23 : 16].i8); tmp += i8_to_i32(S0[31 : 24].i8) * i8_to_i32(S1[31 : 24].i8); D0.i32 = tmp

**V_DOT8C_I32_I4**

**314**

326 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



Compute the dot product of two packed 8-D signed 4-bit integer inputs in the signed 32-bit integer domain and accumulate with the signed 32-bit integer value in the destination register.

tmp = D0.i32; tmp += i4_to_i32(S0[3 : 0].i4) * i4_to_i32(S1[3 : 0].i4); tmp += i4_to_i32(S0[7 : 4].i4) * i4_to_i32(S1[7 : 4].i4); tmp += i4_to_i32(S0[11 : 8].i4) * i4_to_i32(S1[11 : 8].i4); tmp += i4_to_i32(S0[15 : 12].i4) * i4_to_i32(S1[15 : 12].i4); tmp += i4_to_i32(S0[19 : 16].i4) * i4_to_i32(S1[19 : 16].i4); tmp += i4_to_i32(S0[23 : 20].i4) * i4_to_i32(S1[23 : 20].i4); tmp += i4_to_i32(S0[27 : 24].i4) * i4_to_i32(S1[27 : 24].i4); tmp += i4_to_i32(S0[31 : 28].i4) * i4_to_i32(S1[31 : 28].i4); D0.i32 = tmp

#### **V_FMAC_F32**

**315**

Multiply two floating point inputs and accumulate the result into the destination register using fused multiply add.

D0.f32 = fma(S0.f32, S1.f32, D0.f32)

**V_PK_FMAC_F16 316**

Multiply two packed half-precision float inputs component-wise and accumulate the result into the destination register using fused multiply add.

D0[15 : 0].f16 = fma(S0[15 : 0].f16, S1[15 : 0].f16, D0[15 : 0].f16); D0[31 : 16].f16 = fma(S0[31 : 16].f16, S1[31 : 16].f16, D0[31 : 16].f16)

**V_XNOR_B32**

**317**

Calculate bitwise XNOR on two vector inputs and store the result into a vector register.

D0.u32 = ~(S0.u32 ^ S1.u32)

#### **Notes**

Input and output modifiers not supported.

**V_MAD_I32_I24**

**450**

327 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



Multiply two signed 24-bit integer inputs in the signed 32-bit integer domain, add a signed 32-bit integer value from a third input, and store the result as a signed 32-bit integer into a vector register.

D0.i32 = 32'I(S0.i24) * 32'I(S1.i24) + S2.i32

**V_MAD_U32_U24**

**451**

Multiply two unsigned 24-bit integer inputs in the unsigned 32-bit integer domain, add a unsigned 32-bit integer value from a third input, and store the result as an unsigned 32-bit integer into a vector register.

D0.u32 = 32'U(S0.u24) * 32'U(S1.u24) + S2.u32

**V_CUBEID_F32 452**

Compute the cubemap face ID of a 3D coordinate specified as three single-precision float inputs. Store the result in _single-precision float_ format into a vector register.

// Set D0.f = cubemap face ID ({0.0, 1.0, ..., 5.0}). // XYZ coordinate is given in (S0.f, S1.f, S2.f). // S0.f = x // S1.f = y // S2.f = z if ((abs(S2.f32) >= abs(S0.f32)) && (abs(S2.f32) >= abs(S1.f32))) then if S2.f32 < 0.0F then D0.f32 = 5.0F else D0.f32 = 4.0F endif elsif abs(S1.f32) >= abs(S0.f32) then if S1.f32 < 0.0F then D0.f32 = 3.0F else D0.f32 = 2.0F endif else if S0.f32 < 0.0F then D0.f32 = 1.0F else D0.f32 = 0.0F endif endif

**V_CUBESC_F32**

**453**

328 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



Compute the cubemap S coordinate of a 3D coordinate specified as three single-precision float inputs. Store the result in _single-precision float_ format into a vector register.

// D0.f = cubemap S coordinate. // XYZ coordinate is given in (S0.f, S1.f, S2.f). // S0.f = x // S1.f = y // S2.f = z if ((abs(S2.f32) >= abs(S0.f32)) && (abs(S2.f32) >= abs(S1.f32))) then if S2.f32 < 0.0F then D0.f32 = -S0.f32 else D0.f32 = S0.f32 endif elsif abs(S1.f32) >= abs(S0.f32) then D0.f32 = S0.f32 else if S0.f32 < 0.0F then D0.f32 = S2.f32 else D0.f32 = -S2.f32 endif endif

**V_CUBETC_F32**

**454**

Compute the cubemap T coordinate of a 3D coordinate specified as three single-precision float inputs. Store the result in _single-precision float_ format into a vector register.

// D0.f = cubemap T coordinate. // XYZ coordinate is given in (S0.f, S1.f, S2.f). // S0.f = x // S1.f = y // S2.f = z if ((abs(S2.f32) >= abs(S0.f32)) && (abs(S2.f32) >= abs(S1.f32))) then D0.f32 = -S1.f32 elsif abs(S1.f32) >= abs(S0.f32) then if S1.f32 < 0.0F then D0.f32 = -S2.f32 else D0.f32 = S2.f32 endif else D0.f32 = -S1.f32 endif

**V_CUBEMA_F32**

**455**

Compute the cubemap major axis of a 3D coordinate specified as three single-precision float inputs. Store the

329 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



result in _single-precision float_ format into a vector register.

// D0.f = 2.0 * cubemap major axis. // XYZ coordinate is given in (S0.f, S1.f, S2.f). // S0.f = x // S1.f = y // S2.f = z if ((abs(S2.f32) >= abs(S0.f32)) && (abs(S2.f32) >= abs(S1.f32))) then D0.f32 = S2.f32 * 2.0F elsif abs(S1.f32) >= abs(S0.f32) then D0.f32 = S1.f32 * 2.0F else D0.f32 = S0.f32 * 2.0F endif

**V_BFE_U32**

**456**

Extract an unsigned bitfield from the first input using field offset from the second input and size from the third input, then store the result into a vector register.

D0.u32 = ((S0.u32 >> S1[4 : 0].u32) & ((1U << S2[4 : 0].u32) - 1U))

**V_BFE_I32 457**

Extract a signed bitfield from the first input using field offset from the second input and size from the third input, then store the result into a vector register.

tmp.i32 = ((S0.i32 >> S1[4 : 0].u32) & ((1 << S2[4 : 0].u32) - 1)); D0.i32 = signext_from_bit(tmp.i32, S2[4 : 0].u32)

**V_BFI_B32 458**

Overwrite a bitfield in the third input with a bitfield from the second input using a mask from the first input, then store the result into a vector register.

D0.u32 = ((S0.u32 & S1.u32) | (~S0.u32 & S2.u32))

**V_FMA_F32**

**459**

Multiply two single-precision float inputs and add a third input using fused multiply add, and store the result

330 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**460**



into a vector register.

D0.f32 = fma(S0.f32, S1.f32, S2.f32)

#### **Notes**

0.5ULP accuracy, denormals are supported.

**V_FMA_F64**

Multiply two double-precision float inputs and add a third input using fused multiply add, and store the result into a vector register.

D0.f64 = fma(S0.f64, S1.f64, S2.f64)

#### **Notes**

0.5ULP accuracy, denormals are supported.

#### **V_LERP_U8**

**461**

Average two 4-D vectors stored as packed bytes in the first two inputs with rounding control provided by the third input, then store the result into a vector register. Each byte in the third input acts as a rounding mode for the corresponding element; if the LSB is set then 0.5 rounds up, otherwise 0.5 truncates.

tmp = ((S0.u32[31 : 24] + S1.u32[31 : 24] + S2.u32[24].u8) >> 1U << 24U); tmp += ((S0.u32[23 : 16] + S1.u32[23 : 16] + S2.u32[16].u8) >> 1U << 16U); tmp += ((S0.u32[15 : 8] + S1.u32[15 : 8] + S2.u32[8].u8) >> 1U << 8U); tmp += ((S0.u32[7 : 0] + S1.u32[7 : 0] + S2.u32[0].u8) >> 1U); D0.u32 = tmp.u32

#### **V_ALIGNBIT_B32**

**462**

Align a 64-bit value encoded in the first two inputs to a bit position specified in the third input, then store the result into a 32-bit vector register.

D0.u32 = 32'U(({ S0.u32, S1.u32 } >> S2.u32[4 : 0]) & 0xffffffffLL)

#### **Notes**



S0 carries the MSBs and S1 carries the LSBs of the value being aligned.

331 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**463**



#### **V_ALIGNBYTE_B32**

Align a 64-bit value encoded in the first two inputs to a byte position specified in the third input, then store the result into a 32-bit vector register.

D0.u32 = 32'U(({ S0.u32, S1.u32 } >> (S2.u32[1 : 0] * 8U)) & 0xffffffffLL)

#### **Notes**



S0 carries the MSBs and S1 carries the LSBs of the value being aligned.

**V_MIN3_F32**

**464**

Select the minimum of three single-precision float inputs and store the selected value into a vector register.

D0.f32 = v_min_f32(v_min_f32(S0.f32, S1.f32), S2.f32)

**V_MIN3_I32 465**

Select the minimum of three signed 32-bit integer inputs and store the selected value into a vector register.

D0.i32 = v_min_i32(v_min_i32(S0.i32, S1.i32), S2.i32)

#### **V_MIN3_U32**

**466**

Select the minimum of three unsigned 32-bit integer inputs and store the selected value into a vector register.

D0.u32 = v_min_u32(v_min_u32(S0.u32, S1.u32), S2.u32)

**V_MAX3_F32**

**467**

Select the maximum of three single-precision float inputs and store the selected value into a vector register.

D0.f32 = v_max_f32(v_max_f32(S0.f32, S1.f32), S2.f32)

332 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**V_MAX3_I32**

**468**



Select the maximum of three signed 32-bit integer inputs and store the selected value into a vector register.

D0.i32 = v_max_i32(v_max_i32(S0.i32, S1.i32), S2.i32)

**V_MAX3_U32 469**

Select the maximum of three unsigned 32-bit integer inputs and store the selected value into a vector register.

D0.u32 = v_max_u32(v_max_u32(S0.u32, S1.u32), S2.u32)

**V_MED3_F32 470**

Select the median of three single-precision float values and store the selected value into a vector register.

if (isNAN(64'F(S0.f32)) || isNAN(64'F(S1.f32)) || isNAN(64'F(S2.f32))) then D0.f32 = v_min3_f32(S0.f32, S1.f32, S2.f32) elsif v_max3_f32(S0.f32, S1.f32, S2.f32) == S0.f32 then D0.f32 = v_max_f32(S1.f32, S2.f32) elsif v_max3_f32(S0.f32, S1.f32, S2.f32) == S1.f32 then D0.f32 = v_max_f32(S0.f32, S2.f32) else D0.f32 = v_max_f32(S0.f32, S1.f32) endif

**V_MED3_I32 471**

Select the median of three signed 32-bit integer values and store the selected value into a vector register.

if v_max3_i32(S0.i32, S1.i32, S2.i32) == S0.i32 then D0.i32 = v_max_i32(S1.i32, S2.i32) elsif v_max3_i32(S0.i32, S1.i32, S2.i32) == S1.i32 then D0.i32 = v_max_i32(S0.i32, S2.i32) else D0.i32 = v_max_i32(S0.i32, S1.i32) endif

**V_MED3_U32**

**472**

333 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



Select the median of three unsigned 32-bit integer values and store the selected value into a vector register.

if v_max3_u32(S0.u32, S1.u32, S2.u32) == S0.u32 then D0.u32 = v_max_u32(S1.u32, S2.u32) elsif v_max3_u32(S0.u32, S1.u32, S2.u32) == S1.u32 then D0.u32 = v_max_u32(S0.u32, S2.u32) else D0.u32 = v_max_u32(S0.u32, S1.u32) endif

**V_SAD_U8**

**473**

Calculate the sum of absolute differences of elements in two packed 4-component unsigned 8-bit integer inputs, add an unsigned 32-bit integer value from the third input and store the result into a vector register.

ABSDIFF = lambda(x, y) ( x > y ? x - y : y - x); // UNSIGNED comparison tmp = S2.u32; tmp += 32'U(ABSDIFF(S0.u32[7 : 0], S1.u32[7 : 0])); tmp += 32'U(ABSDIFF(S0.u32[15 : 8], S1.u32[15 : 8])); tmp += 32'U(ABSDIFF(S0.u32[23 : 16], S1.u32[23 : 16])); tmp += 32'U(ABSDIFF(S0.u32[31 : 24], S1.u32[31 : 24])); D0.u32 = tmp

#### **Notes**

Overflow into the upper bits is allowed.

**V_SAD_HI_U8 474**

Calculate the sum of absolute differences of elements in two packed 4-component unsigned 8-bit integer inputs, shift the sum left by 16 bits, add an unsigned 32-bit integer value from the third input and store the result into a vector register.

D0.u32 = (32'U(v_sad_u8(S0, S1, 0U)) << 16U) + S2.u32

#### **Notes**

Overflow into the upper bits is allowed.

**V_SAD_U16**

**475**

Calculate the sum of absolute differences of elements in two packed 2-component unsigned 16-bit integer

334 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



inputs, add an unsigned 32-bit integer value from the third input and store the result into a vector register.

ABSDIFF = lambda(x, y) ( x > y ? x - y : y - x); // UNSIGNED comparison tmp = S2.u32; tmp += ABSDIFF(S0[15 : 0].u16, S1[15 : 0].u16); tmp += ABSDIFF(S0[31 : 16].u16, S1[31 : 16].u16); D0.u32 = tmp

#### **V_SAD_U32**

**476**

Calculate the absolute difference of two unsigned 32-bit integer inputs, add an unsigned 32-bit integer value from the third input and store the result into a vector register.

ABSDIFF = lambda(x, y) ( x > y ? x - y : y - x); // UNSIGNED comparison D0.u32 = ABSDIFF(S0.u32, S1.u32) + S2.u32

#### **V_CVT_PK_U8_F32**

**477**

Convert a single-precision float value from the first input to an unsigned 8-bit integer value and pack the result into one byte of the third input using the second input as a byte select. Store the result into a vector register.

tmp = (S2.u32 & 32'U(~(0xff << (S1.u32[1 : 0].u32 * 8U)))); tmp = (tmp | ((32'U(f32_to_u8(S0.f32)) & 255U) << (S1.u32[1 : 0].u32 * 8U))); D0.u32 = tmp

**V_DIV_FIXUP_F32 478**

Given a single-precision float quotient in the first input, a denominator in the second input and a numerator in the third input, detect and apply corner cases related to division, including divide by zero, NaN inputs and overflow, and modify the quotient accordingly. Generate any invalid, denormal and divide-by-zero exceptions that are a result of the division. Store the modified quotient into a vector register.

This operation handles corner cases in a division macro such as divide by zero and NaN inputs. This operation is well defined when the quotient is approximately equal to the numerator divided by the denominator. Other inputs produce a predictable result but may not be mathematically useful.

> sign_out = (sign(S1.f32) ^ sign(S2.f32)); if isNAN(64'F(S2.f32)) then D0.f32 = 32'F(cvtToQuietNAN(64'F(S2.f32)))

335 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**V_DIV_FIXUP_F64 479**



elsif isNAN(64'F(S1.f32)) then D0.f32 = 32'F(cvtToQuietNAN(64'F(S1.f32))) elsif ((64'F(S1.f32) == 0.0) && (64'F(S2.f32) == 0.0)) then // 0/0 D0.f32 = 32'F(0xffc00000) elsif ((64'F(abs(S1.f32)) == +INF) && (64'F(abs(S2.f32)) == +INF)) then // inf/inf D0.f32 = 32'F(0xffc00000) elsif ((64'F(S1.f32) == 0.0) || (64'F(abs(S2.f32)) == +INF)) then // x/0, or inf/y D0.f32 = sign_out ? -INF.f32 : +INF.f32 elsif ((64'F(abs(S1.f32)) == +INF) || (64'F(S2.f32) == 0.0)) then // x/inf, 0/y D0.f32 = sign_out ? -0.0F : 0.0F elsif exponent(S2.f32) - exponent(S1.f32) < -150 then D0.f32 = sign_out ? -UNDERFLOW_F32 : UNDERFLOW_F32 elsif exponent(S1.f32) == 255 then D0.f32 = sign_out ? -OVERFLOW_F32 : OVERFLOW_F32 else D0.f32 = sign_out ? -abs(S0.f32) : abs(S0.f32) endif

#### **Notes**

This operation is the final step of a high precision division macro and handles all exceptional cases of division.

Given a double-precision float quotient in the first input, a denominator in the second input and a numerator in the third input, detect and apply corner cases related to division, including divide by zero, NaN inputs and overflow, and modify the quotient accordingly. Generate any invalid, denormal and divide-by-zero exceptions that are a result of the division. Store the modified quotient into a vector register.

This operation handles corner cases in a division macro such as divide by zero and NaN inputs. This operation is well defined when the quotient is approximately equal to the numerator divided by the denominator. Other inputs produce a predictable result but may not be mathematically useful.

sign_out = (sign(S1.f64) ^ sign(S2.f64)); if isNAN(S2.f64) then D0.f64 = cvtToQuietNAN(S2.f64) elsif isNAN(S1.f64) then D0.f64 = cvtToQuietNAN(S1.f64) elsif ((S1.f64 == 0.0) && (S2.f64 == 0.0)) then // 0/0 D0.f64 = 64'F(0xfff8000000000000LL) elsif ((abs(S1.f64) == +INF) && (abs(S2.f64) == +INF)) then // inf/inf D0.f64 = 64'F(0xfff8000000000000LL) elsif ((S1.f64 == 0.0) || (abs(S2.f64) == +INF)) then // x/0, or inf/y D0.f64 = sign_out ? -INF : +INF elsif ((abs(S1.f64) == +INF) || (S2.f64 == 0.0)) then // x/inf, 0/y

336 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



D0.f64 = sign_out ? -0.0 : 0.0 elsif exponent(S2.f64) - exponent(S1.f64) < -1075 then D0.f64 = sign_out ? -UNDERFLOW_F64 : UNDERFLOW_F64 elsif exponent(S1.f64) == 2047 then D0.f64 = sign_out ? -OVERFLOW_F64 : OVERFLOW_F64 else D0.f64 = sign_out ? -abs(S0.f64) : abs(S0.f64) endif

#### **Notes**

This operation is the final step of a high precision division macro and handles all exceptional cases of division.

#### **V_DIV_SCALE_F32**

**480**

Given a single-precision float value to scale in the first input, a denominator in the second input and a numerator in the third input, scale the first input for division if required to avoid subnormal terms appearing during application of the Newton-Raphson correction method. Store the scaled result into a vector register and set the vector condition code iff post-scaling is required.

This operation is designed for use in a high precision division macro. The first input should be the same value as either the second or third input; other scale values produce predictable results but may not be mathematically useful. The vector condition code is used by V_DIV_FMAS_F32 to determine if the quotient requires post-scaling.

VCC = 0x0LL; if ((64'F(S2.f32) == 0.0) || (64'F(S1.f32) == 0.0)) then D0.f32 = NAN.f32 elsif exponent(S2.f32) - exponent(S1.f32) >= 96 then // N/D near MAX_FLOAT_F32 VCC = 0x1LL; if S0.f32 == S1.f32 then // Only scale the denominator D0.f32 = ldexp(S0.f32, 64) endif elsif S1.f32 == DENORM.f32 then D0.f32 = ldexp(S0.f32, 64) elsif ((1.0 / 64'F(S1.f32) == DENORM.f64) && (S2.f32 / S1.f32 == DENORM.f32)) then VCC = 0x1LL; if S0.f32 == S1.f32 then // Only scale the denominator D0.f32 = ldexp(S0.f32, 64) endif elsif 1.0 / 64'F(S1.f32) == DENORM.f64 then D0.f32 = ldexp(S0.f32, -64) elsif S2.f32 / S1.f32 == DENORM.f32 then VCC = 0x1LL; if S0.f32 == S2.f32 then // Only scale the numerator D0.f32 = ldexp(S0.f32, 64) endif elsif exponent(S2.f32) <= 23 then // Numerator is tiny

337 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**481**



D0.f32 = ldexp(S0.f32, 64) endif

#### **Notes**

V_DIV_SCALE_F32, V_DIV_FMAS_F32 and V_DIV_FIXUP_F32 are all designed for use in a high precision division macro that utilizes V_RCP_F32 and V_MUL_F32 to compute the approximate result and then applies two steps of the Newton-Raphson method to converge to the quotient. If subnormal terms appear during this calculation then a loss of precision occurs. This loss of precision can be avoided by scaling the inputs and then post-scaling the quotient after Newton-Raphson is applied.

#### **V_DIV_SCALE_F64**

Given a double-precision float value to scale in the first input, a denominator in the second input and a numerator in the third input, scale the first input for division if required to avoid subnormal terms appearing during application of the Newton-Raphson correction method. Store the scaled result into a vector register and set the vector condition code iff post-scaling is required.

This operation is designed for use in a high precision division macro. The first input should be the same value as either the second or third input; other scale values produce predictable results but may not be mathematically useful. The vector condition code is used by V_DIV_FMAS_F64 to determine if the quotient requires post-scaling.

VCC = 0x0LL; if ((S2.f64 == 0.0) || (S1.f64 == 0.0)) then D0.f64 = NAN.f64 elsif exponent(S2.f64) - exponent(S1.f64) >= 768 then // N/D near MAX_FLOAT_F64 VCC = 0x1LL; if S0.f64 == S1.f64 then // Only scale the denominator D0.f64 = ldexp(S0.f64, 128) endif elsif S1.f64 == DENORM.f64 then D0.f64 = ldexp(S0.f64, 128) elsif ((1.0 / S1.f64 == DENORM.f64) && (S2.f64 / S1.f64 == DENORM.f64)) then VCC = 0x1LL; if S0.f64 == S1.f64 then // Only scale the denominator D0.f64 = ldexp(S0.f64, 128) endif elsif 1.0 / S1.f64 == DENORM.f64 then D0.f64 = ldexp(S0.f64, -128) elsif S2.f64 / S1.f64 == DENORM.f64 then VCC = 0x1LL; if S0.f64 == S2.f64 then // Only scale the numerator D0.f64 = ldexp(S0.f64, 128) endif elsif exponent(S2.f64) <= 53 then // Numerator is tiny D0.f64 = ldexp(S0.f64, 128)

338 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



endif

#### **Notes**

V_DIV_SCALE_F64, V_DIV_FMAS_F64 and V_DIV_FIXUP_F64 are all designed for use in a high precision division macro that utilizes V_RCP_F64 and V_MUL_F64 to compute the approximate result and then applies two steps of the Newton-Raphson method to converge to the quotient. If subnormal terms appear during this calculation then a loss of precision occurs. This loss of precision can be avoided by scaling the inputs and then post-scaling the quotient after Newton-Raphson is applied.

#### **V_DIV_FMAS_F32**

**482**

Multiply two single-precision float inputs and add a third input using fused multiply add, then scale the exponent of the result by a fixed factor if the vector condition code is set. Store the result into a vector register.

This operation is designed for use in floating point division macros and relies on V_DIV_SCALE_F32 to set the vector condition code iff the quotient requires post-scaling.

if VCC.u64[laneId] then D0.f32 = 2.0F ** 32 * fma(S0.f32, S1.f32, S2.f32) else D0.f32 = fma(S0.f32, S1.f32, S2.f32) endif

#### **Notes**

Input denormals are not flushed but output flushing is allowed.

V_DIV_SCALE_F32, V_DIV_FMAS_F32 and V_DIV_FIXUP_F32 are all designed for use in a high precision division macro that utilizes V_RCP_F32 and V_MUL_F32 to compute the approximate result and then applies two steps of the Newton-Raphson method to converge to the quotient. If subnormal terms appear during this calculation then a loss of precision occurs. This loss of precision can be avoided by scaling the inputs and then post-scaling the quotient after Newton-Raphson is applied.

#### **V_DIV_FMAS_F64**

**483**

Multiply two double-precision float inputs and add a third input using fused multiply add, then scale the exponent of the result by a fixed factor if the vector condition code is set. Store the result into a vector register.

This operation is designed for use in floating point division macros and relies on V_DIV_SCALE_F64 to set the vector condition code iff the quotient requires post-scaling.

if VCC.u64[laneId] then D0.f64 = 2.0 ** 64 * fma(S0.f64, S1.f64, S2.f64) else D0.f64 = fma(S0.f64, S1.f64, S2.f64)

339 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



endif

#### **Notes**

Input denormals are not flushed but output flushing is allowed.

V_DIV_SCALE_F64, V_DIV_FMAS_F64 and V_DIV_FIXUP_F64 are all designed for use in a high precision division macro that utilizes V_RCP_F64 and V_MUL_F64 to compute the approximate result and then applies two steps of the Newton-Raphson method to converge to the quotient. If subnormal terms appear during this calculation then a loss of precision occurs. This loss of precision can be avoided by scaling the inputs and then post-scaling the quotient after Newton-Raphson is applied.

#### **V_MSAD_U8**

**484**

Calculate the sum of absolute differences of elements in two packed 4-component unsigned 8-bit integer inputs, except that elements where the _second_ input (known as the reference input) is zero are not included in the sum. Add an unsigned 32-bit integer value from the third input and store the result into a vector register.

ABSDIFF = lambda(x, y) ( x > y ? x - y : y - x); // UNSIGNED comparison tmp = S2.u32; tmp += S1.u32[7 : 0] == 8'0U ? 0U : 32'U(ABSDIFF(S0.u32[7 : 0], S1.u32[7 : 0])); tmp += S1.u32[15 : 8] == 8'0U ? 0U : 32'U(ABSDIFF(S0.u32[15 : 8], S1.u32[15 : 8])); tmp += S1.u32[23 : 16] == 8'0U ? 0U : 32'U(ABSDIFF(S0.u32[23 : 16], S1.u32[23 : 16])); tmp += S1.u32[31 : 24] == 8'0U ? 0U : 32'U(ABSDIFF(S0.u32[31 : 24], S1.u32[31 : 24])); D0.u32 = tmp

#### **Notes**

Overflow into the upper bits is allowed.

#### **V_QSAD_PK_U16_U8**

**485**

Perform the V_SAD_U8 operation four times using different slices of the first array, all entries of the second array and each entry of the third array. Truncate each result to 16 bits, pack the values into a 4-entry array and store the array into a vector register. The first input is an 8-entry array of unsigned 8-bit integers, the second input is a 4-entry array of unsigned 8-bit integers and the third input is a 4-entry array of unsigned 16-bit integers.

tmp[63 : 48] = 16'B(v_sad_u8(S0[55 : 24], S1[31 : 0], S2[63 : 48].u32)); tmp[47 : 32] = 16'B(v_sad_u8(S0[47 : 16], S1[31 : 0], S2[47 : 32].u32)); tmp[31 : 16] = 16'B(v_sad_u8(S0[39 : 8], S1[31 : 0], S2[31 : 16].u32)); tmp[15 : 0] = 16'B(v_sad_u8(S0[31 : 0], S1[31 : 0], S2[15 : 0].u32)); D0.b64 = tmp.b64

340 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**V_MQSAD_PK_U16_U8**

**486**



Perform the V_MSAD_U8 operation four times using different slices of the first array, all entries of the second array and each entry of the third array. Truncate each result to 16 bits, pack the values into a 4-entry array and store the array into a vector register. The first input is an 8-entry array of unsigned 8-bit integers, the second input is a 4-entry array of unsigned 8-bit integers and the third input is a 4-entry array of unsigned 16-bit integers.

tmp[63 : 48] = 16'B(v_msad_u8(S0[55 : 24], S1[31 : 0], S2[63 : 48].u32)); tmp[47 : 32] = 16'B(v_msad_u8(S0[47 : 16], S1[31 : 0], S2[47 : 32].u32)); tmp[31 : 16] = 16'B(v_msad_u8(S0[39 : 8], S1[31 : 0], S2[31 : 16].u32)); tmp[15 : 0] = 16'B(v_msad_u8(S0[31 : 0], S1[31 : 0], S2[15 : 0].u32)); D0.b64 = tmp.b64

#### **V_MQSAD_U32_U8**

**487**

Perform the V_MSAD_U8 operation four times using different slices of the first array, all entries of the second array and each entry of the third array. Pack each 32-bit value into a 4-entry array and store the array into a vector register. The first input is an 8-entry array of unsigned 8-bit integers, the second input is a 4-entry array of unsigned 8-bit integers and the third input is a 4-entry array of unsigned 32-bit integers.

tmp[127 : 96] = 32'B(v_msad_u8(S0[55 : 24], S1[31 : 0], S2[127 : 96].u32)); tmp[95 : 64] = 32'B(v_msad_u8(S0[47 : 16], S1[31 : 0], S2[95 : 64].u32)); tmp[63 : 32] = 32'B(v_msad_u8(S0[39 : 8], S1[31 : 0], S2[63 : 32].u32)); tmp[31 : 0] = 32'B(v_msad_u8(S0[31 : 0], S1[31 : 0], S2[31 : 0].u32)); D0.b128 = tmp.b128

#### **V_MAD_U64_U32**

**488**

Multiply two unsigned integer inputs, add a third unsigned integer input, store the result into a 64-bit vector register and store the overflow/carryout into a scalar mask register.

{ D1.u1, D0.u64 } = 65'B(65'U(S0.u32) * 65'U(S1.u32) + 65'U(S2.u64))

#### **Notes**

In VOP3 the VCC destination may be an arbitrary SGPR-pair.

**V_MAD_I64_I32**

**489**

Multiply two signed integer inputs, add a third signed integer input, store the result into a 64-bit vector register and store the overflow/carryout into a scalar mask register.

341 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



{ D1.i1, D0.i64 } = 65'B(65'I(S0.i32) * 65'I(S1.i32) + 65'I(S2.i64))

#### **Notes**

In VOP3 the VCC destination may be an arbitrary SGPR-pair.

**V_MAD_LEGACY_F16**

**490**

Multiply add of FP16 values. Implements IEEE rules and non-standard rule for OPSEL.

tmp = S0.f16 * S1.f16 + S2.f16; if OPSEL.u4[3] then D0 = { tmp.f16, D0[15 : 0] } else D0 = { 16'0, tmp.f16 } endif

#### **Notes**

Supports round mode, exception flags, saturation.

If OPSEL[3] is 0 Result is written to 16 LSBs of destination VGPR and hi 16 bits are written as 0 (this is different from V_MAD_F16).

If OPSEL[3] is 1 Result is written to 16 MSBs of destination VGPR and lo 16 bits are preserved.

**V_MAD_LEGACY_U16**

**491**

Multiply add of unsigned short values. Has non-standard rule for OPSEL.

tmp = S0.u16 * S1.u16 + S2.u16; if OPSEL.u4[3] then D0 = { tmp.u16, D0[15 : 0] } else D0 = { 16'0, tmp.u16 } endif

#### **Notes**

Supports saturation (unsigned 16-bit integer domain).

If OPSEL[3] is 0 Result is written to 16 LSBs of destination VGPR and hi 16 bits are written as 0 (this is different from V_MAD_U16).

If OPSEL[3] is 1 Result is written to 16 MSBs of destination VGPR and lo 16 bits are preserved.

342 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**V_MAD_LEGACY_I16**

**492**



Multiply add of signed short values. Has non-standard rule for OPSEL.

tmp = S0.i16 * S1.i16 + S2.i16; if OPSEL.u4[3] then D0 = { tmp.i16, D0[15 : 0] } else D0 = { 16'0, tmp.i16 } endif

#### **Notes**

Supports saturation (signed 16-bit integer domain).

If OPSEL[3] is 0 Result is written to 16 LSBs of destination VGPR and hi 16 bits are written as 0 (this is different from V_MAD_I16).

If OPSEL[3] is 1 Result is written to 16 MSBs of destination VGPR and lo 16 bits are preserved.

#### **V_PERM_B32**

**493**

Permute a 64-bit value constructed from two vector inputs (most significant bits come from the first input) using a per-lane selector from the third input. The lane selector allows each byte of the result to choose from any of the 8 input bytes, perform sign extension or pad with 0/1 bits. Store the result into a vector register.

BYTE_PERMUTE = lambda(data, sel) ( declare in : 8'B[8]; for i in 0 : 7 do in[i] = data[i * 8 + 7 : i * 8].b8 endfor; if sel.u32 >= 13U then return 8'0xff elsif sel.u32 == 12U then return 8'0x0 elsif sel.u32 == 11U then return in[7][7].b8 * 8'0xff elsif sel.u32 == 10U then return in[5][7].b8 * 8'0xff elsif sel.u32 == 9U then return in[3][7].b8 * 8'0xff elsif sel.u32 == 8U then return in[1][7].b8 * 8'0xff else return in[sel] endif); D0[31 : 24] = BYTE_PERMUTE({ S0.u32, S1.u32 }, S2.u32[31 : 24]); D0[23 : 16] = BYTE_PERMUTE({ S0.u32, S1.u32 }, S2.u32[23 : 16]); D0[15 : 8] = BYTE_PERMUTE({ S0.u32, S1.u32 }, S2.u32[15 : 8]);

343 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



D0[7 : 0] = BYTE_PERMUTE({ S0.u32, S1.u32 }, S2.u32[7 : 0])

#### **Notes**

Selects 0 through 7 select the corresponding byte of the 64-bit input value.

Selects 8 through 11 are useful in modeling sign extension of a smaller-precision signed integer to a largerprecision result by replicating the leading bit of a selected byte.

Selects 12 and 13 return padding values of 0 and 1 bits respectively.

Note the MSBs of the 64-bit value being selected are stored in S0. This is counterintuitive for a little-endian architecture.

**V_FMA_LEGACY_F16**

**494**

Fused half precision multiply add. Implements IEEE rules and non-standard rule for OPSEL.

tmp = fma(S0.f16, S1.f16, S2.f16); if OPSEL.u4[3] then D0 = { tmp.f16, D0[15 : 0] } else D0 = { 16'0, tmp.f16 } endif

**V_DIV_FIXUP_LEGACY_F16**

**495**

Half precision division fixup. Has non-standard rule for OPSEL.

S0 = Quotient, S1 = Denominator, S2 = Numerator.

Given a numerator, denominator, and quotient from a divide, this opcode detects and applies specific case numerics, touching up the quotient if necessary. This opcode also generates invalid, denorm and divide by zero exceptions caused by the division.

sign_out = (sign(S1.f16) ^ sign(S2.f16)); if isNAN(64'F(S2.f16)) then tmp = cvtToQuietNAN(64'F(S2.f16)) elsif isNAN(64'F(S1.f16)) then tmp = cvtToQuietNAN(64'F(S1.f16)) elsif ((64'F(S1.f16) == 0.0) && (64'F(S2.f16) == 0.0)) then // 0/0 tmp = 16'F(0xfe00) elsif ((64'F(abs(S1.f16)) == +INF) && (64'F(abs(S2.f16)) == +INF)) then // inf/inf tmp = 16'F(0xfe00) elsif ((64'F(S1.f16) == 0.0) || (64'F(abs(S2.f16)) == +INF)) then // x/0, or inf/y

344 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



tmp = sign_out ? -INF : +INF elsif ((64'F(abs(S1.f16)) == +INF) || (64'F(S2.f16) == 0.0)) then // x/inf, 0/y tmp = sign_out ? -0.0 : 0.0 else tmp = sign_out ? -abs(S0.f16) : abs(S0.f16) endif; if OPSEL.u4[3] then D0 = { tmp.f16, D0[15 : 0] } else D0 = { 16'0, tmp.f16 } endif

#### **V_CVT_PKACCUM_U8_F32**

**496**

Convert a single-precision float value in the first input to an unsigned 8-bit integer value and store the result into one byte of the destination register using the second input as a byte select.

byte = S1.u32[1 : 0]; bit = byte.u32 * 8U; D0.u32[bit + 7U : bit] = 32'U(f32_to_u8(S0.f32))

#### **Notes**

This opcode uses src_c to pass destination in as a source.

**V_MAD_U32_U16**

**497**

Multiply two unsigned 16-bit integer inputs in the unsigned 32-bit integer domain, add an unsigned 32-bit integer value from a third input, and store the result as an unsigned 32-bit integer into a vector register.

D0.u32 = 32'U(S0.u16) * 32'U(S1.u16) + S2.u32

#### **V_MAD_I32_I16**

**498**

Multiply two signed 16-bit integer inputs in the signed 32-bit integer domain, add a signed 32-bit integer value from a third input, and store the result as a signed 32-bit integer into a vector register.

D0.i32 = 32'I(S0.i16) * 32'I(S1.i16) + S2.i32

**499**

**V_XAD_U32**

345 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



Calculate bitwise XOR of the first two vector inputs, then add the third vector input to the intermediate result, then store the final result into a vector register.

D0.u32 = (S0.u32 ^ S1.u32) + S2.u32

#### **Notes**

No carryin/carryout and no saturation. This opcode is designed to help accelerate the SHA256 hash algorithm.

#### **V_MIN3_F16**

**500**

Select the minimum of three half-precision float inputs and store the selected value into a vector register.

D0.f16 = v_min_f16(v_min_f16(S0.f16, S1.f16), S2.f16)

#### **V_MIN3_I16**

**501**

Select the minimum of three signed 16-bit integer inputs and store the selected value into a vector register.

D0.i16 = v_min_i16(v_min_i16(S0.i16, S1.i16), S2.i16)

#### **V_MIN3_U16**

**502**

Select the minimum of three unsigned 16-bit integer inputs and store the selected value into a vector register.

D0.u16 = v_min_u16(v_min_u16(S0.u16, S1.u16), S2.u16)

**V_MAX3_F16 503**

Select the maximum of three half-precision float inputs and store the selected value into a vector register.

D0.f16 = v_max_f16(v_max_f16(S0.f16, S1.f16), S2.f16)

#### **V_MAX3_I16**

**504**

Select the maximum of three signed 16-bit integer inputs and store the selected value into a vector register.

346 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**505**



D0.i16 = v_max_i16(v_max_i16(S0.i16, S1.i16), S2.i16)

#### **V_MAX3_U16**

Select the maximum of three unsigned 16-bit integer inputs and store the selected value into a vector register.

D0.u16 = v_max_u16(v_max_u16(S0.u16, S1.u16), S2.u16)

#### **V_MED3_F16**

**506**

Select the median of three half-precision float values and store the selected value into a vector register.

if (isNAN(64'F(S0.f16)) || isNAN(64'F(S1.f16)) || isNAN(64'F(S2.f16))) then D0.f16 = v_min3_f16(S0.f16, S1.f16, S2.f16) elsif v_max3_f16(S0.f16, S1.f16, S2.f16) == S0.f16 then D0.f16 = v_max_f16(S1.f16, S2.f16) elsif v_max3_f16(S0.f16, S1.f16, S2.f16) == S1.f16 then D0.f16 = v_max_f16(S0.f16, S2.f16) else D0.f16 = v_max_f16(S0.f16, S1.f16) endif

#### **V_MED3_I16**

**507**

Select the median of three signed 16-bit integer values and store the selected value into a vector register.

if v_max3_i16(S0.i16, S1.i16, S2.i16) == S0.i16 then D0.i16 = v_max_i16(S1.i16, S2.i16) elsif v_max3_i16(S0.i16, S1.i16, S2.i16) == S1.i16 then D0.i16 = v_max_i16(S0.i16, S2.i16) else D0.i16 = v_max_i16(S0.i16, S1.i16) endif

#### **V_MED3_U16**

**508**

Select the median of three unsigned 16-bit integer values and store the selected value into a vector register.

if v_max3_u16(S0.u16, S1.u16, S2.u16) == S0.u16 then D0.u16 = v_max_u16(S1.u16, S2.u16)

347 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



elsif v_max3_u16(S0.u16, S1.u16, S2.u16) == S1.u16 then D0.u16 = v_max_u16(S0.u16, S2.u16) else D0.u16 = v_max_u16(S0.u16, S1.u16) endif

#### **V_LSHL_ADD_U32**

**509**

Given a shift count in the second input, calculate the logical shift left of the first input, then add the third input to the intermediate result, then store the final result into a vector register.

D0.u32 = (S0.u32 << S1.u32[4 : 0].u32) + S2.u32

#### **V_ADD_LSHL_U32**

**510**

Add the first two integer inputs, then given a shift count in the third input, calculate the logical shift left of the intermediate result, then store the final result into a vector register.

D0.u32 = ((S0.u32 + S1.u32) << S2.u32[4 : 0].u32)

**V_ADD3_U32 511**

Add three unsigned inputs and store the result into a vector register. No carry-in or carry-out support.

D0.u32 = S0.u32 + S1.u32 + S2.u32

#### **V_LSHL_OR_B32**

**512**

Given a shift count in the second input, calculate the logical shift left of the first input, then calculate the bitwise OR of the intermediate result and the third input, then store the final result into a vector register.

D0.u32 = ((S0.u32 << S1.u32[4 : 0].u32) | S2.u32)

**V_AND_OR_B32 513**

Calculate bitwise AND on the first two vector inputs, then compute the bitwise OR of the intermediate result and the third vector input, then store the final result into a vector register.

348 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



D0.u32 = ((S0.u32 & S1.u32) | S2.u32)

#### **Notes**

Input and output modifiers not supported.

**V_OR3_B32**

**514**

Calculate the bitwise OR of three vector inputs and store the result into a vector register.

D0.u32 = (S0.u32 | S1.u32 | S2.u32)

#### **Notes**

Input and output modifiers not supported.

**V_MAD_F16 515**

Multiply two half-precision float inputs and add a third input, and store the result into a vector register.

D0.f16 = S0.f16 * S1.f16 + S2.f16

#### **Notes**

Supports round mode, exception flags, saturation. 1ULP accuracy, denormals are flushed.

If OPSEL[3] is 0 Result is written to 16 LSBs of destination VGPR and hi 16 bits are preserved.

If OPSEL[3] is 1 Result is written to 16 MSBs of destination VGPR and lo 16 bits are preserved.

**V_MAD_U16**

**516**

Multiply two unsigned 16-bit integer inputs, add an unsigned 16-bit integer value from a third input, and store the result into a vector register.

D0.u16 = S0.u16 * S1.u16 + S2.u16

#### **Notes**

Supports saturation (unsigned 16-bit integer domain).

349 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**517**



If OPSEL[3] is 0 the result is written to 16 LSBs of destination VGPR and the high 16 bits are preserved.

If OPSEL[3] is 1 the result is written to 16 MSBs of destination VGPR and the low 16 bits are preserved.

#### **V_MAD_I16**

Multiply two signed 16-bit integer inputs, add a signed 16-bit integer value from a third input, and store the result into a vector register.

D0.i16 = S0.i16 * S1.i16 + S2.i16

#### **Notes**

Supports saturation (signed 16-bit integer domain).

If OPSEL[3] is 0 the result is written to 16 LSBs of destination VGPR and the high 16 bits are preserved.

If OPSEL[3] is 1 the result is written to 16 MSBs of destination VGPR and the low 16 bits are preserved.

#### **V_FMA_F16**

**518**

Multiply two half-precision float inputs and add a third input using fused multiply add, and store the result into a vector register.

D0.f16 = fma(S0.f16, S1.f16, S2.f16)

#### **Notes**

0.5ULP accuracy, denormals are supported.

If OPSEL[3] is 0 Result is written to 16 LSBs of destination VGPR and hi 16 bits are preserved.

If OPSEL[3] is 1 Result is written to 16 MSBs of destination VGPR and lo 16 bits are preserved.

#### **V_DIV_FIXUP_F16**

**519**

Given a half-precision float quotient in the first input, a denominator in the second input and a numerator in the third input, detect and apply corner cases related to division, including divide by zero, NaN inputs and overflow, and modify the quotient accordingly. Generate any invalid, denormal and divide-by-zero exceptions that are a result of the division. Store the modified quotient into a vector register.

This operation handles corner cases in a division macro such as divide by zero and NaN inputs. This operation is well defined when the quotient is approximately equal to the numerator divided by the denominator. Other inputs produce a predictable result but may not be mathematically useful.

350 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



sign_out = (sign(S1.f16) ^ sign(S2.f16)); if isNAN(64'F(S2.f16)) then D0.f16 = 16'F(cvtToQuietNAN(64'F(S2.f16))) elsif isNAN(64'F(S1.f16)) then D0.f16 = 16'F(cvtToQuietNAN(64'F(S1.f16))) elsif ((64'F(S1.f16) == 0.0) && (64'F(S2.f16) == 0.0)) then // 0/0 D0.f16 = 16'F(0xfe00) elsif ((64'F(abs(S1.f16)) == +INF) && (64'F(abs(S2.f16)) == +INF)) then // inf/inf D0.f16 = 16'F(0xfe00) elsif ((64'F(S1.f16) == 0.0) || (64'F(abs(S2.f16)) == +INF)) then // x/0, or inf/y D0.f16 = sign_out ? -INF.f16 : +INF.f16 elsif ((64'F(abs(S1.f16)) == +INF) || (64'F(S2.f16) == 0.0)) then // x/inf, 0/y D0.f16 = sign_out ? -16'0.0 : 16'0.0 else D0.f16 = sign_out ? -abs(S0.f16) : abs(S0.f16) endif

#### **Notes**

This operation is the final step of a high precision division macro and handles all exceptional cases of division.

If OPSEL[3] is 0 Result is written to 16 LSBs of destination VGPR and hi 16 bits are preserved.

If OPSEL[3] is 1 Result is written to 16 MSBs of destination VGPR and lo 16 bits are preserved.

**V_LSHL_ADD_U64**

**520**

Given a shift count in the second input, calculate the logical shift left of the first input, then add the third input to the intermediate result, then store the final result into a vector register.

For this opcode the shift count must be between 0 and 4, higher shift counts are unsupported.

D0.u64 = (S0.u64 << S1.u32[2 : 0].u32) + S2.u64

#### **Notes**

The design treats unsupported shift counts as a shift of zero.

**V_ADD_F64**

**640**

Add two floating point inputs and store the result into a vector register.

351 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



D0.f64 = S0.f64 + S1.f64

#### **Notes**

0.5ULP precision, denormals are supported.

**V_MUL_F64**

**641**

Multiply two floating point inputs and store the result into a vector register.

D0.f64 = S0.f64 * S1.f64

#### **Notes**

0.5ULP precision, denormals are supported.

#### **V_MIN_F64**

**642**

Select the minimum of two double-precision float inputs and store the result into a vector register.

if (WAVE_MODE.IEEE && isSignalNAN(S0.f64)) then D0.f64 = cvtToQuietNAN(S0.f64) elsif (WAVE_MODE.IEEE && isSignalNAN(S1.f64)) then D0.f64 = cvtToQuietNAN(S1.f64) elsif isNAN(S0.f64) then D0.f64 = S1.f64 elsif isNAN(S1.f64) then D0.f64 = S0.f64 elsif ((S0.f64 == +0.0) && (S1.f64 == -0.0)) then D0.f64 = S1.f64 elsif ((S0.f64 == -0.0) && (S1.f64 == +0.0)) then D0.f64 = S0.f64 else // Note: there's no IEEE case here like there is for V_MAX_F64. D0.f64 = S0.f64 < S1.f64 ? S0.f64 : S1.f64 endif

#### **V_MAX_F64**

**643**

Select the maximum of two double-precision float inputs and store the result into a vector register.

if (WAVE_MODE.IEEE && isSignalNAN(S0.f64)) then D0.f64 = cvtToQuietNAN(S0.f64)

352 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



elsif (WAVE_MODE.IEEE && isSignalNAN(S1.f64)) then D0.f64 = cvtToQuietNAN(S1.f64) elsif isNAN(S0.f64) then D0.f64 = S1.f64 elsif isNAN(S1.f64) then D0.f64 = S0.f64 elsif ((S0.f64 == +0.0) && (S1.f64 == -0.0)) then D0.f64 = S0.f64 elsif ((S0.f64 == -0.0) && (S1.f64 == +0.0)) then D0.f64 = S1.f64 elsif WAVE_MODE.IEEE then D0.f64 = S0.f64 >= S1.f64 ? S0.f64 : S1.f64 else D0.f64 = S0.f64 > S1.f64 ? S0.f64 : S1.f64 endif

#### **V_LDEXP_F64**

**644**

Multiply the first input, a floating point value, by an integral power of 2 specified in the second input, a signed integer value, and store the floating point result into a vector register.

D0.f64 = S0.f64 * 2.0 ** S1.i32

#### **Notes**

Compare with the ldexp() function in C.

**V_MUL_LO_U32 645**

Multiply two unsigned 32-bit integer inputs and store the result into a vector register.

D0.u32 = S0.u32 * S1.u32

#### **Notes**

To multiply integers with small magnitudes consider V_MUL_U32_U24, which is intended to be a more efficient implementation.

**V_MUL_HI_U32 646**

Multiply two unsigned 32-bit integer inputs and store the high 32 bits of the result into a vector register.

D0.u32 = 32'U((64'U(S0.u32) * 64'U(S1.u32)) >> 32U)

353 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**647**



#### **Notes**

To multiply integers with small magnitudes consider V_MUL_HI_U32_U24, which is intended to be a more efficient implementation.

**V_MUL_HI_I32**

Multiply two signed 32-bit integer inputs and store the high 32 bits of the result into a vector register.

D0.i32 = 32'I((64'I(S0.i32) * 64'I(S1.i32)) >> 32U)

#### **Notes**

To multiply integers with small magnitudes consider V_MUL_HI_I32_I24, which is intended to be a more efficient implementation.

**V_LDEXP_F32**

**648**

Multiply the first input, a floating point value, by an integral power of 2 specified in the second input, a signed integer value, and store the floating point result into a vector register.

D0.f32 = S0.f32 * 2.0F ** S1.i32

#### **Notes**

Compare with the ldexp() function in C.

#### **V_READLANE_B32**

**649**

Read the scalar value in the specified lane of the first input where the lane select is in the second input. Store the result into a scalar register.

lane = S1.u32[5 : 0]; // Lane select D0.b32 = VGPR[lane][SRC0.u32]

#### **Notes**

Overrides EXEC mask for the VGPR read. Input and output modifiers not supported; this is an untyped operation.

354 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**650**



#### **V_WRITELANE_B32**

Write the scalar value in the first input into the specified lane of a vector register where the lane select is in the second input.

lane = S1.u32[5 : 0]; // Lane select VGPR[lane][VDST.u32] = S0.b32

#### **Notes**

Overrides EXEC mask for the VGPR write. Input and output modifiers not supported; this is an untyped operation.

**V_BCNT_U32_B32**

**651**

Count the number of "1" bits in the vector input and store the result into a vector register.

tmp = S1.u32; for i in 0 : 31 do tmp += S0[i].u32; // count i'th bit endfor; D0.u32 = tmp

**V_MBCNT_LO_U32_B32**

**652**

For each lane 0 <= _N_ < 32, examine the _N_ least significant bits of the first input and count how many of those bits are "1". For each lane 32 <= _N_ < 64, all "1" bits in the first input are counted. Add this count to the value in the second input and store the result into a vector register.

In conjunction with V_MBCNT_HI_U32_B32 and with a vector condition code as input, this counts the number of lanes at or below the current lane number that have set their vector condition code bit.

ThreadMask = (1LL << laneId.u32) - 1LL; MaskedValue = (S0.u32 & ThreadMask[31 : 0].u32); tmp = S1.u32; for i in 0 : 31 do tmp += MaskedValue[i] == 1'1U ? 1U : 0U endfor; D0.u32 = tmp

#### **Notes**

See also V_MBCNT_HI_U32_B32.

355 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**653**



#### **V_MBCNT_HI_U32_B32**

For each lane 32 <= _N_ < 64, examine the _N_ least significant bits of the first input and count how many of those bits are "1". For lane positions 0 <= _N_ < 32 _no_ bits are examined and the count is zero. Add this count to the value in the second input and store the result into a vector register.

In conjunction with V_MBCNT_LO_U32_B32 and with a vector condition code as input, this counts the number of lanes at or below the current lane number that have set their vector condition code bit.

ThreadMask = (1LL << laneId.u32) - 1LL; MaskedValue = (S0.u32 & ThreadMask[63 : 32].u32); tmp = S1.u32; for i in 0 : 31 do tmp += MaskedValue[i] == 1'1U ? 1U : 0U endfor; D0.u32 = tmp

#### **Notes**

Example to compute each lane's position in 0..63:

v_mbcnt_lo_u32_b32 v0, -1, 0 v_mbcnt_hi_u32_b32 v0, -1, v0 // v0 now contains laneId

Example to compute each lane's position in a list of all lanes whose VCC bits are set, where the first lane with VCC set is assigned position 1, the second lane with VCC set is assigned position 2, etc.:

v_mbcnt_lo_u32_b32 v0, vcc_lo, 0 v_mbcnt_hi_u32_b32 v0, vcc_hi, v0 // Note vcc_hi is passed in for second instruction // v0 now contains position among lanes with VCC=1

See also V_MBCNT_LO_U32_B32.

**V_LSHLREV_B64**

**655**

Given a shift count in the _first_ vector input, calculate the logical shift left of the _second_ vector input and store the result into a vector register.

D0.u64 = (S1.u64 << S0[5 : 0].u32)

**V_LSHRREV_B64**

**656**

356 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



Given a shift count in the _first_ vector input, calculate the logical shift right of the _second_ vector input and store the result into a vector register.

D0.u64 = (S1.u64 >> S0[5 : 0].u32)

#### **V_ASHRREV_I64**

**657**

Given a shift count in the _first_ vector input, calculate the arithmetic shift right (preserving sign bit) of the _second_ vector input and store the result into a vector register.

D0.i64 = (S1.i64 >> S0[5 : 0].u32)

#### **V_TRIG_PREOP_F64**

**658**

Look up a 53-bit segment of 2/PI using an integer segment select in the second input. Scale the intermediate result by the exponent from the first double-precision float input and store the double-precision float result into a vector register.

This operation returns an aligned, double precision segment of 2/PI needed to do trigonometric argument reduction on the floating point input. Multiple segments can be accessed using the first input. Rounding is toward zero. Large floating point inputs (with an exponent > 1968) are scaled to avoid loss of precision through denormalization.

shift = 32'I(S1[4 : 0].u32) * 53; if exponent(S0.f64) > 1077 then shift += exponent(S0.f64) - 1077 endif; // (2.0/PI) == 0.{b_1200, b_1199, b_1198, ..., b_1, b_0} // b_1200 is the MSB of the fractional part of 2.0/PI // Left shift operation indicates which bits are brought // into the whole part of the number. // Only whole part of result is kept. result = 64'F((1201'B(2.0 / PI)[1200 : 0] << shift.u32) & 1201'0x1fffffffffffff); scale = -53 - shift; if exponent(S0.f64) >= 1968 then scale += 128 endif; D0.f64 = ldexp(result, scale)

#### **Notes**

For a more complete treatment of trigonometric argument reduction refer to _Argument Reduction for Huge Arguments: Good to the Last Bit_ , K. C. Ng et.al., March 1992, available online.

357 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**V_BFM_B32**

**659**



Calculate a bitfield mask given a field offset and size and store the result into a vector register.

D0.u32 = (((1U << S0[4 : 0].u32) - 1U) << S1[4 : 0].u32)

**V_CVT_PKNORM_I16_F32**

**660**

Convert from two single-precision float inputs to a packed signed normalized short and store the result into a vector register.

declare tmp : 32'B; tmp[15 : 0].i16 = f32_to_snorm(S0.f32); tmp[31 : 16].i16 = f32_to_snorm(S1.f32); D0 = tmp.b32

**V_CVT_PKNORM_U16_F32**

**661**

Convert from two single-precision float inputs to a packed unsigned normalized short and store the result into a vector register.

declare tmp : 32'B; tmp[15 : 0].u16 = f32_to_unorm(S0.f32); tmp[31 : 16].u16 = f32_to_unorm(S1.f32); D0 = tmp.b32

#### **V_CVT_PKRTZ_F16_F32**

**662**

Convert two single-precision float inputs to a packed half-precision float value using round toward zero semantics (ignore the current rounding mode), and store the result into a vector register.

prev_mode = ROUND_MODE; ROUND_MODE = ROUND_TOWARD_ZERO; tmp[15 : 0].f16 = f32_to_f16(S0.f32); tmp[31 : 16].f16 = f32_to_f16(S1.f32); D0 = tmp.b32; ROUND_MODE = prev_mode; // Round-toward-zero regardless of current round mode setting in hardware.

#### **Notes**

This opcode is intended for use with 16-bit compressed exports. See V_CVT_F16_F32 for a version that respects

358 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



the current rounding mode.

#### **V_CVT_PK_U16_U32**

**663**

Convert from two unsigned 32-bit integer inputs to a packed unsigned 16-bit integer value and store the result into a vector register.

declare tmp : 32'B; tmp[15 : 0].u16 = u32_to_u16(S0.u32); tmp[31 : 16].u16 = u32_to_u16(S1.u32); D0 = tmp.b32

#### **V_CVT_PK_I16_I32**

**664**

Convert from two signed 32-bit integer inputs to a packed signed 16-bit integer value and store the result into a vector register.

declare tmp : 32'B; tmp[15 : 0].i16 = i32_to_i16(S0.i32); tmp[31 : 16].i16 = i32_to_i16(S1.i32); D0 = tmp.b32

#### **V_CVT_PKNORM_I16_F16**

**665**

Convert from two half-precision float inputs to a packed signed normalized short and store the result into a vector register.

declare tmp : 32'B; tmp[15 : 0].i16 = f16_to_snorm(S0.f16); tmp[31 : 16].i16 = f16_to_snorm(S1.f16); D0 = tmp.b32

#### **V_CVT_PKNORM_U16_F16**

**666**

Convert from two half-precision float inputs to a packed unsigned normalized short and store the result into a vector register.

declare tmp : 32'B; tmp[15 : 0].u16 = f16_to_unorm(S0.f16); tmp[31 : 16].u16 = f16_to_unorm(S1.f16);

359 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**668**



D0 = tmp.b32

**V_ADD_I32**

Add two signed 32-bit integer inputs and store the result into a vector register. No carry-in or carry-out support.

D0.i32 = S0.i32 + S1.i32

#### **Notes**

Supports saturation (signed 32-bit integer domain).

**V_SUB_I32**

**669**

Subtract the second signed 32-bit integer input from the first input and store the result into a vector register. No carry-in or carry-out support.

D0.i32 = S0.i32 - S1.i32

#### **Notes**

Supports saturation (signed 32-bit integer domain).

**V_ADD_I16**

**670**

Add two signed 16-bit integer inputs and store the result into a vector register. No carry-in or carry-out support.

D0.i16 = S0.i16 + S1.i16

#### **Notes**

Supports saturation (signed 16-bit integer domain).

**V_SUB_I16 671**

Subtract the second signed 16-bit integer input from the first input and store the result into a vector register. No carry-in or carry-out support.

360 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



D0.i16 = S0.i16 - S1.i16

#### **Notes**

Supports saturation (signed 16-bit integer domain).

#### **V_PACK_B32_F16**

**672**

Pack two half-precision float values into a single 32-bit value and store the result into a vector register.

D0[31 : 16].f16 = S1.f16; D0[15 : 0].f16 = S0.f16

#### **V_MUL_LEGACY_F32**

**673**

Multiply two floating point inputs and store the result into a vector register. Follows DX9 rules where 0.0 times anything produces 0.0 (this differs from other APIs when the other input is infinity or NaN).

if ((64'F(S0.f32) == 0.0) || (64'F(S1.f32) == 0.0)) then // DX9 rules, 0.0 * x = 0.0 D0.f32 = 0.0F else D0.f32 = S0.f32 * S1.f32 endif

#### **V_CVT_PK_FP8_F32**

**674**

Convert from two single-precision float inputs to a packed FP8 float value with round to nearest even semantics and store the result into 16 bits of a vector register using OPSEL.

prev_mode = ROUND_MODE; ROUND_MODE = ROUND_NEAREST_EVEN; if OPSEL[3].u32 == 0U then VGPR[laneId][VDST.u32][15 : 0].b16 = { f32_to_fp8(S1.f32), f32_to_fp8(S0.f32) }; // D0[31:16] are preserved else VGPR[laneId][VDST.u32][31 : 16].b16 = { f32_to_fp8(S1.f32), f32_to_fp8(S0.f32) }; // D0[15:0] are preserved endif; ROUND_MODE = prev_mode

#### **Notes**

361 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**675**



Round to nearest even. Ignores OMOD and clamp.

#### **V_CVT_PK_BF8_F32**

Convert from two single-precision float inputs to a packed BF8 float value with round to nearest even semantics and store the result into 16 bits of a vector register using OPSEL.

prev_mode = ROUND_MODE; ROUND_MODE = ROUND_NEAREST_EVEN; if OPSEL[3].u32 == 0U then VGPR[laneId][VDST.u32][15 : 0].b16 = { f32_to_bf8(S1.f32), f32_to_bf8(S0.f32) }; // D0[31:16] are preserved else VGPR[laneId][VDST.u32][31 : 16].b16 = { f32_to_bf8(S1.f32), f32_to_bf8(S0.f32) }; // D0[15:0] are preserved endif; ROUND_MODE = prev_mode

#### **Notes**

Round to nearest even. Ignores OMOD and clamp.

**V_CVT_SR_FP8_F32**

**676**

Convert from a single-precision float input to an FP8 value with stochastic rounding using seed data from the second input. Store the result into 8 bits of a vector register using OPSEL to determine which byte of the destination to overwrite.

prev_mode = ROUND_MODE; ROUND_MODE = ROUND_NEAREST_EVEN; s = sign(S0.f32); e = exponent(S0.f32); m = 23'U(32'U(23'B(mantissa(S0.f32))) + S1[31 : 12].u32); tmp = float32(s, e, m); // Add stochastic value to mantissa, wrap around on overflow if OPSEL[3 : 2].u2 == 2'0U then VGPR[laneId][VDST.u32][7 : 0].fp8 = f32_to_fp8(tmp.f32) elsif OPSEL[3 : 2].u2 == 2'1U then VGPR[laneId][VDST.u32][15 : 8].fp8 = f32_to_fp8(tmp.f32) elsif OPSEL[3 : 2].u2 == 2'2U then VGPR[laneId][VDST.u32][23 : 16].fp8 = f32_to_fp8(tmp.f32) else VGPR[laneId][VDST.u32][31 : 24].fp8 = f32_to_fp8(tmp.f32) endif; // Unwritten bytes of D are preserved. ROUND_MODE = prev_mode

#### **Notes**

362 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**677**



Stochastic rounding. Ignores OMOD and clamp.

#### **V_CVT_SR_BF8_F32**

Convert from a single-precision float input to a BF8 value with stochastic rounding using seed data from the second input. Store the result into 8 bits of a vector register using OPSEL to determine which byte of the destination to overwrite.

prev_mode = ROUND_MODE; ROUND_MODE = ROUND_NEAREST_EVEN; s = sign(S0.f32); e = exponent(S0.f32); m = 23'U(32'U(23'B(mantissa(S0.f32))) + S1[31 : 11].u32); tmp = float32(s, e, m); // Add stochastic value to mantissa, wrap around on overflow if OPSEL[3 : 2].u2 == 2'0U then VGPR[laneId][VDST.u32][7 : 0].bf8 = f32_to_bf8(tmp.f32) elsif OPSEL[3 : 2].u2 == 2'1U then VGPR[laneId][VDST.u32][15 : 8].bf8 = f32_to_bf8(tmp.f32) elsif OPSEL[3 : 2].u2 == 2'2U then VGPR[laneId][VDST.u32][23 : 16].bf8 = f32_to_bf8(tmp.f32) else VGPR[laneId][VDST.u32][31 : 24].bf8 = f32_to_bf8(tmp.f32) endif; // Unwritten bytes of D are preserved. ROUND_MODE = prev_mode

#### **Notes**

Stochastic rounding. Ignores OMOD and clamp.

**V_CMP_CLASS_F32**

**16**

Evaluate the IEEE numeric class function specified as a 10 bit mask in the second input on the first input, a single-precision float, and set the per-lane condition code to the result. Store the result into VCC or a scalar register.

The function reports true if the floating point value is _any_ of the numeric types selected in the 10 bit mask according to the following list:

S1.u[0] value is a signaling NAN. S1.u[1] value is a quiet NAN. S1.u[2] value is negative infinity. S1.u[3] value is a negative normal value. S1.u[4] value is a negative denormal value. S1.u[5] value is negative zero. S1.u[6] value is positive zero. S1.u[7] value is a positive denormal value. S1.u[8] value is a positive normal value.

363 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



S1.u[9] value is positive infinity.

declare result : 1'U; if isSignalNAN(64'F(S0.f32)) then result = S1.u32[0] elsif isQuietNAN(64'F(S0.f32)) then result = S1.u32[1] elsif exponent(S0.f32) == 255 then // +-INF result = S1.u32[sign(S0.f32) ? 2 : 9] elsif exponent(S0.f32) > 0 then // +-normal value result = S1.u32[sign(S0.f32) ? 3 : 8] elsif 64'F(abs(S0.f32)) > 0.0 then // +-denormal value result = S1.u32[sign(S0.f32) ? 4 : 7] else // +-0.0 result = S1.u32[sign(S0.f32) ? 5 : 6] endif; D0.u64[laneId] = result; // D0 = VCC in VOPC encoding.

#### **V_CMPX_CLASS_F32**

**17**

Evaluate the IEEE numeric class function specified as a 10 bit mask in the second input on the first input, a single-precision float, and set the per-lane condition code to the result. Store the result into the EXEC mask and to VCC or a scalar register.

The function reports true if the floating point value is _any_ of the numeric types selected in the 10 bit mask according to the following list:

S1.u[0] value is a signaling NAN. S1.u[1] value is a quiet NAN. S1.u[2] value is negative infinity. S1.u[3] value is a negative normal value. S1.u[4] value is a negative denormal value. S1.u[5] value is negative zero. S1.u[6] value is positive zero. S1.u[7] value is a positive denormal value. S1.u[8] value is a positive normal value. S1.u[9] value is positive infinity.

declare result : 1'U; if isSignalNAN(64'F(S0.f32)) then result = S1.u32[0] elsif isQuietNAN(64'F(S0.f32)) then result = S1.u32[1] elsif exponent(S0.f32) == 255 then // +-INF result = S1.u32[sign(S0.f32) ? 2 : 9]

364 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**18**



elsif exponent(S0.f32) > 0 then // +-normal value result = S1.u32[sign(S0.f32) ? 3 : 8] elsif 64'F(abs(S0.f32)) > 0.0 then // +-denormal value result = S1.u32[sign(S0.f32) ? 4 : 7] else // +-0.0 result = S1.u32[sign(S0.f32) ? 5 : 6] endif; EXEC.u64[laneId] = D0.u64[laneId] = result

#### **V_CMP_CLASS_F64**

Evaluate the IEEE numeric class function specified as a 10 bit mask in the second input on the first input, a double-precision float, and set the per-lane condition code to the result. Store the result into VCC or a scalar register.

The function reports true if the floating point value is _any_ of the numeric types selected in the 10 bit mask according to the following list:

S1.u[0] value is a signaling NAN. S1.u[1] value is a quiet NAN. S1.u[2] value is negative infinity. S1.u[3] value is a negative normal value. S1.u[4] value is a negative denormal value. S1.u[5] value is negative zero. S1.u[6] value is positive zero. S1.u[7] value is a positive denormal value. S1.u[8] value is a positive normal value. S1.u[9] value is positive infinity.

declare result : 1'U; if isSignalNAN(S0.f64) then result = S1.u32[0] elsif isQuietNAN(S0.f64) then result = S1.u32[1] elsif exponent(S0.f64) == 2047 then // +-INF result = S1.u32[sign(S0.f64) ? 2 : 9] elsif exponent(S0.f64) > 0 then // +-normal value result = S1.u32[sign(S0.f64) ? 3 : 8] elsif abs(S0.f64) > 0.0 then // +-denormal value result = S1.u32[sign(S0.f64) ? 4 : 7] else // +-0.0 result = S1.u32[sign(S0.f64) ? 5 : 6] endif; D0.u64[laneId] = result;

365 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

// D0 = VCC in VOPC encoding.

**19**



#### **V_CMPX_CLASS_F64**

Evaluate the IEEE numeric class function specified as a 10 bit mask in the second input on the first input, a double-precision float, and set the per-lane condition code to the result. Store the result into the EXEC mask and to VCC or a scalar register.

The function reports true if the floating point value is _any_ of the numeric types selected in the 10 bit mask according to the following list:

S1.u[0] value is a signaling NAN. S1.u[1] value is a quiet NAN. S1.u[2] value is negative infinity. S1.u[3] value is a negative normal value. S1.u[4] value is a negative denormal value. S1.u[5] value is negative zero. S1.u[6] value is positive zero. S1.u[7] value is a positive denormal value. S1.u[8] value is a positive normal value. S1.u[9] value is positive infinity.

declare result : 1'U; if isSignalNAN(S0.f64) then result = S1.u32[0] elsif isQuietNAN(S0.f64) then result = S1.u32[1] elsif exponent(S0.f64) == 2047 then // +-INF result = S1.u32[sign(S0.f64) ? 2 : 9] elsif exponent(S0.f64) > 0 then // +-normal value result = S1.u32[sign(S0.f64) ? 3 : 8] elsif abs(S0.f64) > 0.0 then // +-denormal value result = S1.u32[sign(S0.f64) ? 4 : 7] else // +-0.0 result = S1.u32[sign(S0.f64) ? 5 : 6] endif; EXEC.u64[laneId] = D0.u64[laneId] = result

#### **V_CMP_CLASS_F16**

**20**

Evaluate the IEEE numeric class function specified as a 10 bit mask in the second input on the first input, a half-precision float, and set the per-lane condition code to the result. Store the result into VCC or a scalar register.

366 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



The function reports true if the floating point value is _any_ of the numeric types selected in the 10 bit mask according to the following list:

S1.u[0] value is a signaling NAN. S1.u[1] value is a quiet NAN. S1.u[2] value is negative infinity. S1.u[3] value is a negative normal value. S1.u[4] value is a negative denormal value. S1.u[5] value is negative zero. S1.u[6] value is positive zero. S1.u[7] value is a positive denormal value. S1.u[8] value is a positive normal value. S1.u[9] value is positive infinity.

declare result : 1'U; if isSignalNAN(64'F(S0.f16)) then result = S1.u32[0] elsif isQuietNAN(64'F(S0.f16)) then result = S1.u32[1] elsif exponent(S0.f16) == 31 then // +-INF result = S1.u32[sign(S0.f16) ? 2 : 9] elsif exponent(S0.f16) > 0 then // +-normal value result = S1.u32[sign(S0.f16) ? 3 : 8] elsif 64'F(abs(S0.f16)) > 0.0 then // +-denormal value result = S1.u32[sign(S0.f16) ? 4 : 7] else // +-0.0 result = S1.u32[sign(S0.f16) ? 5 : 6] endif; D0.u64[laneId] = result; // D0 = VCC in VOPC encoding.

#### **Notes**

Note that the S1 has a format of f16 since floating point literal constants are interpreted as 16 bit value for this opcode.

#### **V_CMPX_CLASS_F16**

**21**

Evaluate the IEEE numeric class function specified as a 10 bit mask in the second input on the first input, a half-precision float, and set the per-lane condition code to the result. Store the result into the EXEC mask and to VCC or a scalar register.

The function reports true if the floating point value is _any_ of the numeric types selected in the 10 bit mask according to the following list:

S1.u[0] value is a signaling NAN.

S1.u[1] value is a quiet NAN.

367 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



S1.u[2] value is negative infinity. S1.u[3] value is a negative normal value. S1.u[4] value is a negative denormal value. S1.u[5] value is negative zero. S1.u[6] value is positive zero. S1.u[7] value is a positive denormal value. S1.u[8] value is a positive normal value. S1.u[9] value is positive infinity.

declare result : 1'U; if isSignalNAN(64'F(S0.f16)) then result = S1.u32[0] elsif isQuietNAN(64'F(S0.f16)) then result = S1.u32[1] elsif exponent(S0.f16) == 31 then // +-INF result = S1.u32[sign(S0.f16) ? 2 : 9] elsif exponent(S0.f16) > 0 then // +-normal value result = S1.u32[sign(S0.f16) ? 3 : 8] elsif 64'F(abs(S0.f16)) > 0.0 then // +-denormal value result = S1.u32[sign(S0.f16) ? 4 : 7] else // +-0.0 result = S1.u32[sign(S0.f16) ? 5 : 6] endif; EXEC.u64[laneId] = D0.u64[laneId] = result

#### **Notes**

Note that the S1 has a format of f16 since floating point literal constants are interpreted as 16 bit value for this opcode.

**V_CMP_F_F16 32**

Set the per-lane condition code to 0. Store the result into VCC or a scalar register.

D0.u64[laneId] = 1'0U; // D0 = VCC in VOPC encoding.

**V_CMP_LT_F16 33**

Set the per-lane condition code to 1 iff the first input is less than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.f16 < S1.f16;

368 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



// D0 = VCC in VOPC encoding.

#### **V_CMP_EQ_F16**

**34**

Set the per-lane condition code to 1 iff the first input is equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.f16 == S1.f16; // D0 = VCC in VOPC encoding.

**V_CMP_LE_F16**

**35**

Set the per-lane condition code to 1 iff the first input is less than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.f16 <= S1.f16; // D0 = VCC in VOPC encoding.

#### **V_CMP_GT_F16**

**36**

Set the per-lane condition code to 1 iff the first input is greater than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.f16 > S1.f16; // D0 = VCC in VOPC encoding.

#### **V_CMP_LG_F16**

**37**

Set the per-lane condition code to 1 iff the first input is less than or greater than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.f16 <> S1.f16; // D0 = VCC in VOPC encoding.

**V_CMP_GE_F16**

**38**

Set the per-lane condition code to 1 iff the first input is greater than or equal to the second input. Store the

369 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**39**



result into VCC or a scalar register.

D0.u64[laneId] = S0.f16 >= S1.f16; // D0 = VCC in VOPC encoding.

#### **V_CMP_O_F16**

Set the per-lane condition code to 1 iff the first input is orderable to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = (!isNAN(64'F(S0.f16)) && !isNAN(64'F(S1.f16))); // D0 = VCC in VOPC encoding.

#### **V_CMP_U_F16**

**40**

Set the per-lane condition code to 1 iff the first input is not orderable to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = (isNAN(64'F(S0.f16)) || isNAN(64'F(S1.f16))); // D0 = VCC in VOPC encoding.

#### **V_CMP_NGE_F16**

**41**

Set the per-lane condition code to 1 iff the first input is not greater than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = !(S0.f16 >= S1.f16); // With NAN inputs this is not the same operation as < // D0 = VCC in VOPC encoding.

#### **V_CMP_NLG_F16**

**42**

Set the per-lane condition code to 1 iff the first input is not less than or greater than the second input. Store the result into VCC or a scalar register.

> D0.u64[laneId] = !(S0.f16 <> S1.f16);

> // With NAN inputs this is not the same operation as ==

// D0 = VCC in VOPC encoding.

370 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



#### **V_CMP_NGT_F16**

**43**

Set the per-lane condition code to 1 iff the first input is not greater than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = !(S0.f16 > S1.f16); // With NAN inputs this is not the same operation as <= // D0 = VCC in VOPC encoding.

#### **V_CMP_NLE_F16**

**44**

Set the per-lane condition code to 1 iff the first input is not less than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = !(S0.f16 <= S1.f16); // With NAN inputs this is not the same operation as > // D0 = VCC in VOPC encoding.

#### **V_CMP_NEQ_F16**

**45**

Set the per-lane condition code to 1 iff the first input is not equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = !(S0.f16 == S1.f16); // With NAN inputs this is not the same operation as != // D0 = VCC in VOPC encoding.

#### **V_CMP_NLT_F16**

**46**

Set the per-lane condition code to 1 iff the first input is not less than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = !(S0.f16 < S1.f16); // With NAN inputs this is not the same operation as >= // D0 = VCC in VOPC encoding.

**47**

**V_CMP_TRU_F16**

371 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



Set the per-lane condition code to 1. Store the result into VCC or a scalar register.

D0.u64[laneId] = 1'1U; // D0 = VCC in VOPC encoding.

#### **V_CMPX_F_F16**

**48**

Set the per-lane condition code to 0. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = 1'0U; // D0 = VCC in VOPC encoding.

#### **V_CMPX_LT_F16**

**49**

Set the per-lane condition code to 1 iff the first input is less than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.f16 < S1.f16; // D0 = VCC in VOPC encoding.

#### **V_CMPX_EQ_F16**

**50**

Set the per-lane condition code to 1 iff the first input is equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.f16 == S1.f16; // D0 = VCC in VOPC encoding.

#### **V_CMPX_LE_F16**

**51**

Set the per-lane condition code to 1 iff the first input is less than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.f16 <= S1.f16; // D0 = VCC in VOPC encoding.

372 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**52**



#### **V_CMPX_GT_F16**

Set the per-lane condition code to 1 iff the first input is greater than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.f16 > S1.f16; // D0 = VCC in VOPC encoding.

#### **V_CMPX_LG_F16**

**53**

Set the per-lane condition code to 1 iff the first input is less than or greater than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.f16 <> S1.f16; // D0 = VCC in VOPC encoding.

#### **V_CMPX_GE_F16**

**54**

Set the per-lane condition code to 1 iff the first input is greater than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.f16 >= S1.f16; // D0 = VCC in VOPC encoding.

#### **V_CMPX_O_F16**

**55**

Set the per-lane condition code to 1 iff the first input is orderable to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = (!isNAN(64'F(S0.f16)) && !isNAN(64'F(S1.f16))); // D0 = VCC in VOPC encoding.

#### **V_CMPX_U_F16**

**56**

Set the per-lane condition code to 1 iff the first input is not orderable to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = (isNAN(64'F(S0.f16)) || isNAN(64'F(S1.f16)));

373 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



// D0 = VCC in VOPC encoding.

#### **V_CMPX_NGE_F16**

**57**

Set the per-lane condition code to 1 iff the first input is not greater than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = !(S0.f16 >= S1.f16); // With NAN inputs this is not the same operation as < // D0 = VCC in VOPC encoding.

#### **V_CMPX_NLG_F16**

**58**

Set the per-lane condition code to 1 iff the first input is not less than or greater than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = !(S0.f16 <> S1.f16); // With NAN inputs this is not the same operation as == // D0 = VCC in VOPC encoding.

#### **V_CMPX_NGT_F16**

**59**

Set the per-lane condition code to 1 iff the first input is not greater than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = !(S0.f16 > S1.f16); // With NAN inputs this is not the same operation as <= // D0 = VCC in VOPC encoding.

#### **V_CMPX_NLE_F16**

**60**

Set the per-lane condition code to 1 iff the first input is not less than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = !(S0.f16 <= S1.f16); // With NAN inputs this is not the same operation as > // D0 = VCC in VOPC encoding.

374 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**61**



#### **V_CMPX_NEQ_F16**

Set the per-lane condition code to 1 iff the first input is not equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = !(S0.f16 == S1.f16); // With NAN inputs this is not the same operation as != // D0 = VCC in VOPC encoding.

#### **V_CMPX_NLT_F16**

**62**

Set the per-lane condition code to 1 iff the first input is not less than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = !(S0.f16 < S1.f16); // With NAN inputs this is not the same operation as >= // D0 = VCC in VOPC encoding.

**V_CMPX_TRU_F16**

**63**

Set the per-lane condition code to 1. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = 1'1U; // D0 = VCC in VOPC encoding.

**V_CMP_F_F32 64**

Set the per-lane condition code to 0. Store the result into VCC or a scalar register.

D0.u64[laneId] = 1'0U; // D0 = VCC in VOPC encoding.

#### **V_CMP_LT_F32**

**65**

Set the per-lane condition code to 1 iff the first input is less than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.f32 < S1.f32;

375 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



// D0 = VCC in VOPC encoding.

**V_CMP_EQ_F32**

**66**

Set the per-lane condition code to 1 iff the first input is equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.f32 == S1.f32; // D0 = VCC in VOPC encoding.

**V_CMP_LE_F32**

**67**

Set the per-lane condition code to 1 iff the first input is less than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.f32 <= S1.f32; // D0 = VCC in VOPC encoding.

**V_CMP_GT_F32**

**68**

Set the per-lane condition code to 1 iff the first input is greater than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.f32 > S1.f32; // D0 = VCC in VOPC encoding.

#### **V_CMP_LG_F32**

**69**

Set the per-lane condition code to 1 iff the first input is less than or greater than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.f32 <> S1.f32; // D0 = VCC in VOPC encoding.

**V_CMP_GE_F32**

**70**

Set the per-lane condition code to 1 iff the first input is greater than or equal to the second input. Store the

376 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**71**



result into VCC or a scalar register.

D0.u64[laneId] = S0.f32 >= S1.f32; // D0 = VCC in VOPC encoding.

#### **V_CMP_O_F32**

Set the per-lane condition code to 1 iff the first input is orderable to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = (!isNAN(64'F(S0.f32)) && !isNAN(64'F(S1.f32))); // D0 = VCC in VOPC encoding.

#### **V_CMP_U_F32**

**72**

Set the per-lane condition code to 1 iff the first input is not orderable to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = (isNAN(64'F(S0.f32)) || isNAN(64'F(S1.f32))); // D0 = VCC in VOPC encoding.

#### **V_CMP_NGE_F32**

**73**

Set the per-lane condition code to 1 iff the first input is not greater than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = !(S0.f32 >= S1.f32); // With NAN inputs this is not the same operation as < // D0 = VCC in VOPC encoding.

#### **V_CMP_NLG_F32**

**74**

Set the per-lane condition code to 1 iff the first input is not less than or greater than the second input. Store the result into VCC or a scalar register.

> D0.u64[laneId] = !(S0.f32 <> S1.f32);

> // With NAN inputs this is not the same operation as ==

// D0 = VCC in VOPC encoding.

377 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



#### **V_CMP_NGT_F32**

**75**

Set the per-lane condition code to 1 iff the first input is not greater than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = !(S0.f32 > S1.f32); // With NAN inputs this is not the same operation as <= // D0 = VCC in VOPC encoding.

#### **V_CMP_NLE_F32**

**76**

Set the per-lane condition code to 1 iff the first input is not less than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = !(S0.f32 <= S1.f32); // With NAN inputs this is not the same operation as > // D0 = VCC in VOPC encoding.

#### **V_CMP_NEQ_F32**

**77**

Set the per-lane condition code to 1 iff the first input is not equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = !(S0.f32 == S1.f32); // With NAN inputs this is not the same operation as != // D0 = VCC in VOPC encoding.

#### **V_CMP_NLT_F32**

**78**

Set the per-lane condition code to 1 iff the first input is not less than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = !(S0.f32 < S1.f32); // With NAN inputs this is not the same operation as >= // D0 = VCC in VOPC encoding.

**V_CMP_TRU_F32**

**79**

378 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



Set the per-lane condition code to 1. Store the result into VCC or a scalar register.

D0.u64[laneId] = 1'1U; // D0 = VCC in VOPC encoding.

#### **V_CMPX_F_F32**

**80**

Set the per-lane condition code to 0. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = 1'0U; // D0 = VCC in VOPC encoding.

#### **V_CMPX_LT_F32**

**81**

Set the per-lane condition code to 1 iff the first input is less than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.f32 < S1.f32; // D0 = VCC in VOPC encoding.

#### **V_CMPX_EQ_F32**

**82**

Set the per-lane condition code to 1 iff the first input is equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.f32 == S1.f32; // D0 = VCC in VOPC encoding.

#### **V_CMPX_LE_F32**

**83**

Set the per-lane condition code to 1 iff the first input is less than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.f32 <= S1.f32; // D0 = VCC in VOPC encoding.

379 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**84**



#### **V_CMPX_GT_F32**

Set the per-lane condition code to 1 iff the first input is greater than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.f32 > S1.f32; // D0 = VCC in VOPC encoding.

#### **V_CMPX_LG_F32**

**85**

Set the per-lane condition code to 1 iff the first input is less than or greater than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.f32 <> S1.f32; // D0 = VCC in VOPC encoding.

**V_CMPX_GE_F32 86**

Set the per-lane condition code to 1 iff the first input is greater than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.f32 >= S1.f32; // D0 = VCC in VOPC encoding.

**V_CMPX_O_F32 87**

Set the per-lane condition code to 1 iff the first input is orderable to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = (!isNAN(64'F(S0.f32)) && !isNAN(64'F(S1.f32))); // D0 = VCC in VOPC encoding.

#### **V_CMPX_U_F32**

**88**

Set the per-lane condition code to 1 iff the first input is not orderable to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = (isNAN(64'F(S0.f32)) || isNAN(64'F(S1.f32)));

380 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



// D0 = VCC in VOPC encoding.

#### **V_CMPX_NGE_F32**

**89**

Set the per-lane condition code to 1 iff the first input is not greater than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = !(S0.f32 >= S1.f32); // With NAN inputs this is not the same operation as < // D0 = VCC in VOPC encoding.

#### **V_CMPX_NLG_F32**

**90**

Set the per-lane condition code to 1 iff the first input is not less than or greater than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = !(S0.f32 <> S1.f32); // With NAN inputs this is not the same operation as == // D0 = VCC in VOPC encoding.

#### **V_CMPX_NGT_F32**

**91**

Set the per-lane condition code to 1 iff the first input is not greater than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = !(S0.f32 > S1.f32); // With NAN inputs this is not the same operation as <= // D0 = VCC in VOPC encoding.

#### **V_CMPX_NLE_F32**

**92**

Set the per-lane condition code to 1 iff the first input is not less than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = !(S0.f32 <= S1.f32); // With NAN inputs this is not the same operation as > // D0 = VCC in VOPC encoding.

381 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**93**



#### **V_CMPX_NEQ_F32**

Set the per-lane condition code to 1 iff the first input is not equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = !(S0.f32 == S1.f32); // With NAN inputs this is not the same operation as != // D0 = VCC in VOPC encoding.

#### **V_CMPX_NLT_F32**

**94**

Set the per-lane condition code to 1 iff the first input is not less than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = !(S0.f32 < S1.f32); // With NAN inputs this is not the same operation as >= // D0 = VCC in VOPC encoding.

**V_CMPX_TRU_F32**

**95**

Set the per-lane condition code to 1. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = 1'1U; // D0 = VCC in VOPC encoding.

**V_CMP_F_F64**

**96**

Set the per-lane condition code to 0. Store the result into VCC or a scalar register.

D0.u64[laneId] = 1'0U; // D0 = VCC in VOPC encoding.

#### **V_CMP_LT_F64**

**97**

Set the per-lane condition code to 1 iff the first input is less than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.f64 < S1.f64;

382 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



// D0 = VCC in VOPC encoding.

**V_CMP_EQ_F64**

**98**

Set the per-lane condition code to 1 iff the first input is equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.f64 == S1.f64; // D0 = VCC in VOPC encoding.

**V_CMP_LE_F64**

**99**

Set the per-lane condition code to 1 iff the first input is less than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.f64 <= S1.f64; // D0 = VCC in VOPC encoding.

#### **V_CMP_GT_F64**

**100**

Set the per-lane condition code to 1 iff the first input is greater than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.f64 > S1.f64; // D0 = VCC in VOPC encoding.

**V_CMP_LG_F64**

**101**

Set the per-lane condition code to 1 iff the first input is less than or greater than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.f64 <> S1.f64; // D0 = VCC in VOPC encoding.

**V_CMP_GE_F64**

**102**

Set the per-lane condition code to 1 iff the first input is greater than or equal to the second input. Store the

383 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**103**



result into VCC or a scalar register.

D0.u64[laneId] = S0.f64 >= S1.f64; // D0 = VCC in VOPC encoding.

#### **V_CMP_O_F64**

Set the per-lane condition code to 1 iff the first input is orderable to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = (!isNAN(S0.f64) && !isNAN(S1.f64)); // D0 = VCC in VOPC encoding.

#### **V_CMP_U_F64**

**104**

Set the per-lane condition code to 1 iff the first input is not orderable to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = (isNAN(S0.f64) || isNAN(S1.f64)); // D0 = VCC in VOPC encoding.

#### **V_CMP_NGE_F64**

**105**

Set the per-lane condition code to 1 iff the first input is not greater than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = !(S0.f64 >= S1.f64); // With NAN inputs this is not the same operation as < // D0 = VCC in VOPC encoding.

#### **V_CMP_NLG_F64**

**106**

Set the per-lane condition code to 1 iff the first input is not less than or greater than the second input. Store the result into VCC or a scalar register.

> D0.u64[laneId] = !(S0.f64 <> S1.f64);

> // With NAN inputs this is not the same operation as ==

// D0 = VCC in VOPC encoding.

384 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



#### **V_CMP_NGT_F64**

**107**

Set the per-lane condition code to 1 iff the first input is not greater than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = !(S0.f64 > S1.f64); // With NAN inputs this is not the same operation as <= // D0 = VCC in VOPC encoding.

#### **V_CMP_NLE_F64**

**108**

Set the per-lane condition code to 1 iff the first input is not less than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = !(S0.f64 <= S1.f64); // With NAN inputs this is not the same operation as > // D0 = VCC in VOPC encoding.

#### **V_CMP_NEQ_F64**

**109**

Set the per-lane condition code to 1 iff the first input is not equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = !(S0.f64 == S1.f64); // With NAN inputs this is not the same operation as != // D0 = VCC in VOPC encoding.

#### **V_CMP_NLT_F64**

**110**

Set the per-lane condition code to 1 iff the first input is not less than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = !(S0.f64 < S1.f64); // With NAN inputs this is not the same operation as >= // D0 = VCC in VOPC encoding.

**V_CMP_TRU_F64**

**111**

385 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



Set the per-lane condition code to 1. Store the result into VCC or a scalar register.

D0.u64[laneId] = 1'1U; // D0 = VCC in VOPC encoding.

#### **V_CMPX_F_F64**

**112**

Set the per-lane condition code to 0. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = 1'0U; // D0 = VCC in VOPC encoding.

#### **V_CMPX_LT_F64**

**113**

Set the per-lane condition code to 1 iff the first input is less than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.f64 < S1.f64; // D0 = VCC in VOPC encoding.

#### **V_CMPX_EQ_F64**

**114**

Set the per-lane condition code to 1 iff the first input is equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.f64 == S1.f64; // D0 = VCC in VOPC encoding.

#### **V_CMPX_LE_F64**

**115**

Set the per-lane condition code to 1 iff the first input is less than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.f64 <= S1.f64; // D0 = VCC in VOPC encoding.

386 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**116**



#### **V_CMPX_GT_F64**

Set the per-lane condition code to 1 iff the first input is greater than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.f64 > S1.f64; // D0 = VCC in VOPC encoding.

#### **V_CMPX_LG_F64**

**117**

Set the per-lane condition code to 1 iff the first input is less than or greater than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.f64 <> S1.f64; // D0 = VCC in VOPC encoding.

#### **V_CMPX_GE_F64**

**118**

Set the per-lane condition code to 1 iff the first input is greater than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.f64 >= S1.f64; // D0 = VCC in VOPC encoding.

#### **V_CMPX_O_F64**

**119**

Set the per-lane condition code to 1 iff the first input is orderable to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = (!isNAN(S0.f64) && !isNAN(S1.f64)); // D0 = VCC in VOPC encoding.

#### **V_CMPX_U_F64**

**120**

Set the per-lane condition code to 1 iff the first input is not orderable to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = (isNAN(S0.f64) || isNAN(S1.f64));

387 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



// D0 = VCC in VOPC encoding.

#### **V_CMPX_NGE_F64**

**121**

Set the per-lane condition code to 1 iff the first input is not greater than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = !(S0.f64 >= S1.f64); // With NAN inputs this is not the same operation as < // D0 = VCC in VOPC encoding.

#### **V_CMPX_NLG_F64**

**122**

Set the per-lane condition code to 1 iff the first input is not less than or greater than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = !(S0.f64 <> S1.f64); // With NAN inputs this is not the same operation as == // D0 = VCC in VOPC encoding.

#### **V_CMPX_NGT_F64**

**123**

Set the per-lane condition code to 1 iff the first input is not greater than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = !(S0.f64 > S1.f64); // With NAN inputs this is not the same operation as <= // D0 = VCC in VOPC encoding.

#### **V_CMPX_NLE_F64**

**124**

Set the per-lane condition code to 1 iff the first input is not less than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = !(S0.f64 <= S1.f64); // With NAN inputs this is not the same operation as > // D0 = VCC in VOPC encoding.

388 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**125**



#### **V_CMPX_NEQ_F64**

Set the per-lane condition code to 1 iff the first input is not equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = !(S0.f64 == S1.f64); // With NAN inputs this is not the same operation as != // D0 = VCC in VOPC encoding.

#### **V_CMPX_NLT_F64**

**126**

Set the per-lane condition code to 1 iff the first input is not less than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = !(S0.f64 < S1.f64); // With NAN inputs this is not the same operation as >= // D0 = VCC in VOPC encoding.

**V_CMPX_TRU_F64**

**127**

Set the per-lane condition code to 1. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = 1'1U; // D0 = VCC in VOPC encoding.

**V_CMP_F_I16 160**

Set the per-lane condition code to 0. Store the result into VCC or a scalar register.

D0.u64[laneId] = 1'0U; // D0 = VCC in VOPC encoding.

#### **V_CMP_LT_I16**

**161**

Set the per-lane condition code to 1 iff the first input is less than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.i16 < S1.i16;

389 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



// D0 = VCC in VOPC encoding.

#### **V_CMP_EQ_I16**

**162**

Set the per-lane condition code to 1 iff the first input is equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.i16 == S1.i16; // D0 = VCC in VOPC encoding.

#### **V_CMP_LE_I16**

**163**

Set the per-lane condition code to 1 iff the first input is less than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.i16 <= S1.i16; // D0 = VCC in VOPC encoding.

#### **V_CMP_GT_I16**

**164**

Set the per-lane condition code to 1 iff the first input is greater than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.i16 > S1.i16; // D0 = VCC in VOPC encoding.

#### **V_CMP_NE_I16**

**165**

Set the per-lane condition code to 1 iff the first input is not equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.i16 <> S1.i16; // D0 = VCC in VOPC encoding.

**V_CMP_GE_I16**

**166**

Set the per-lane condition code to 1 iff the first input is greater than or equal to the second input. Store the

390 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**167**



result into VCC or a scalar register.

D0.u64[laneId] = S0.i16 >= S1.i16; // D0 = VCC in VOPC encoding.

#### **V_CMP_T_I16**

Set the per-lane condition code to 1. Store the result into VCC or a scalar register.

D0.u64[laneId] = 1'1U; // D0 = VCC in VOPC encoding.

#### **V_CMP_F_U16**

**168**

Set the per-lane condition code to 0. Store the result into VCC or a scalar register.

D0.u64[laneId] = 1'0U; // D0 = VCC in VOPC encoding.

#### **V_CMP_LT_U16**

**169**

Set the per-lane condition code to 1 iff the first input is less than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.u16 < S1.u16; // D0 = VCC in VOPC encoding.

#### **V_CMP_EQ_U16**

**170**

Set the per-lane condition code to 1 iff the first input is equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.u16 == S1.u16; // D0 = VCC in VOPC encoding.

**V_CMP_LE_U16**

**171**

391 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



Set the per-lane condition code to 1 iff the first input is less than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.u16 <= S1.u16; // D0 = VCC in VOPC encoding.

#### **V_CMP_GT_U16**

**172**

Set the per-lane condition code to 1 iff the first input is greater than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.u16 > S1.u16; // D0 = VCC in VOPC encoding.

#### **V_CMP_NE_U16**

**173**

Set the per-lane condition code to 1 iff the first input is not equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.u16 <> S1.u16; // D0 = VCC in VOPC encoding.

#### **V_CMP_GE_U16**

**174**

Set the per-lane condition code to 1 iff the first input is greater than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.u16 >= S1.u16; // D0 = VCC in VOPC encoding.

#### **V_CMP_T_U16**

**175**

Set the per-lane condition code to 1. Store the result into VCC or a scalar register.

D0.u64[laneId] = 1'1U; // D0 = VCC in VOPC encoding.

392 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**V_CMPX_F_I16**

**176**



Set the per-lane condition code to 0. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = 1'0U; // D0 = VCC in VOPC encoding.

#### **V_CMPX_LT_I16**

**177**

Set the per-lane condition code to 1 iff the first input is less than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.i16 < S1.i16; // D0 = VCC in VOPC encoding.

#### **V_CMPX_EQ_I16**

**178**

Set the per-lane condition code to 1 iff the first input is equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.i16 == S1.i16; // D0 = VCC in VOPC encoding.

#### **V_CMPX_LE_I16**

**179**

Set the per-lane condition code to 1 iff the first input is less than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.i16 <= S1.i16; // D0 = VCC in VOPC encoding.

#### **V_CMPX_GT_I16**

**180**

Set the per-lane condition code to 1 iff the first input is greater than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.i16 > S1.i16; // D0 = VCC in VOPC encoding.

393 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**181**



#### **V_CMPX_NE_I16**

Set the per-lane condition code to 1 iff the first input is not equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.i16 <> S1.i16; // D0 = VCC in VOPC encoding.

#### **V_CMPX_GE_I16**

**182**

Set the per-lane condition code to 1 iff the first input is greater than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.i16 >= S1.i16; // D0 = VCC in VOPC encoding.

**V_CMPX_T_I16**

**183**

Set the per-lane condition code to 1. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = 1'1U; // D0 = VCC in VOPC encoding.

#### **V_CMPX_F_U16**

**184**

Set the per-lane condition code to 0. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = 1'0U; // D0 = VCC in VOPC encoding.

#### **V_CMPX_LT_U16**

**185**

Set the per-lane condition code to 1 iff the first input is less than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.u16 < S1.u16;

394 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



// D0 = VCC in VOPC encoding.

#### **V_CMPX_EQ_U16**

**186**

Set the per-lane condition code to 1 iff the first input is equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.u16 == S1.u16; // D0 = VCC in VOPC encoding.

#### **V_CMPX_LE_U16**

**187**

Set the per-lane condition code to 1 iff the first input is less than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.u16 <= S1.u16; // D0 = VCC in VOPC encoding.

#### **V_CMPX_GT_U16**

**188**

Set the per-lane condition code to 1 iff the first input is greater than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.u16 > S1.u16; // D0 = VCC in VOPC encoding.

#### **V_CMPX_NE_U16**

**189**

Set the per-lane condition code to 1 iff the first input is not equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.u16 <> S1.u16; // D0 = VCC in VOPC encoding.

**V_CMPX_GE_U16**

**190**

Set the per-lane condition code to 1 iff the first input is greater than or equal to the second input. Store the

395 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.u16 >= S1.u16; // D0 = VCC in VOPC encoding.

#### **V_CMPX_T_U16**

**191**

Set the per-lane condition code to 1. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = 1'1U; // D0 = VCC in VOPC encoding.

**V_CMP_F_I32**

**192**

Set the per-lane condition code to 0. Store the result into VCC or a scalar register.

D0.u64[laneId] = 1'0U; // D0 = VCC in VOPC encoding.

#### **V_CMP_LT_I32**

**193**

Set the per-lane condition code to 1 iff the first input is less than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.i32 < S1.i32; // D0 = VCC in VOPC encoding.

#### **V_CMP_EQ_I32**

**194**

Set the per-lane condition code to 1 iff the first input is equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.i32 == S1.i32; // D0 = VCC in VOPC encoding.

**V_CMP_LE_I32**

**195**

396 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



Set the per-lane condition code to 1 iff the first input is less than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.i32 <= S1.i32; // D0 = VCC in VOPC encoding.

#### **V_CMP_GT_I32**

**196**

Set the per-lane condition code to 1 iff the first input is greater than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.i32 > S1.i32; // D0 = VCC in VOPC encoding.

#### **V_CMP_NE_I32**

**197**

Set the per-lane condition code to 1 iff the first input is not equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.i32 <> S1.i32; // D0 = VCC in VOPC encoding.

#### **V_CMP_GE_I32**

**198**

Set the per-lane condition code to 1 iff the first input is greater than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.i32 >= S1.i32; // D0 = VCC in VOPC encoding.

#### **V_CMP_T_I32**

**199**

Set the per-lane condition code to 1. Store the result into VCC or a scalar register.

D0.u64[laneId] = 1'1U; // D0 = VCC in VOPC encoding.

397 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**V_CMP_F_U32**

**200**



Set the per-lane condition code to 0. Store the result into VCC or a scalar register.

D0.u64[laneId] = 1'0U; // D0 = VCC in VOPC encoding.

**V_CMP_LT_U32**

**201**

Set the per-lane condition code to 1 iff the first input is less than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.u32 < S1.u32; // D0 = VCC in VOPC encoding.

#### **V_CMP_EQ_U32**

**202**

Set the per-lane condition code to 1 iff the first input is equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.u32 == S1.u32; // D0 = VCC in VOPC encoding.

#### **V_CMP_LE_U32**

**203**

Set the per-lane condition code to 1 iff the first input is less than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.u32 <= S1.u32; // D0 = VCC in VOPC encoding.

#### **V_CMP_GT_U32**

**204**

Set the per-lane condition code to 1 iff the first input is greater than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.u32 > S1.u32; // D0 = VCC in VOPC encoding.

398 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**205**



**V_CMP_NE_U32**

Set the per-lane condition code to 1 iff the first input is not equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.u32 <> S1.u32; // D0 = VCC in VOPC encoding.

**V_CMP_GE_U32**

**206**

Set the per-lane condition code to 1 iff the first input is greater than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.u32 >= S1.u32; // D0 = VCC in VOPC encoding.

**V_CMP_T_U32 207**

Set the per-lane condition code to 1. Store the result into VCC or a scalar register.

D0.u64[laneId] = 1'1U; // D0 = VCC in VOPC encoding.

#### **V_CMPX_F_I32**

**208**

Set the per-lane condition code to 0. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = 1'0U; // D0 = VCC in VOPC encoding.

#### **V_CMPX_LT_I32**

**209**

Set the per-lane condition code to 1 iff the first input is less than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.i32 < S1.i32;

399 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



// D0 = VCC in VOPC encoding.

#### **V_CMPX_EQ_I32**

**210**

Set the per-lane condition code to 1 iff the first input is equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.i32 == S1.i32; // D0 = VCC in VOPC encoding.

#### **V_CMPX_LE_I32**

**211**

Set the per-lane condition code to 1 iff the first input is less than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.i32 <= S1.i32; // D0 = VCC in VOPC encoding.

#### **V_CMPX_GT_I32**

**212**

Set the per-lane condition code to 1 iff the first input is greater than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.i32 > S1.i32; // D0 = VCC in VOPC encoding.

#### **V_CMPX_NE_I32**

**213**

Set the per-lane condition code to 1 iff the first input is not equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.i32 <> S1.i32; // D0 = VCC in VOPC encoding.

**V_CMPX_GE_I32**

**214**

Set the per-lane condition code to 1 iff the first input is greater than or equal to the second input. Store the

400 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.i32 >= S1.i32; // D0 = VCC in VOPC encoding.

#### **V_CMPX_T_I32**

**215**

Set the per-lane condition code to 1. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = 1'1U; // D0 = VCC in VOPC encoding.

#### **V_CMPX_F_U32**

**216**

Set the per-lane condition code to 0. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = 1'0U; // D0 = VCC in VOPC encoding.

#### **V_CMPX_LT_U32**

**217**

Set the per-lane condition code to 1 iff the first input is less than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.u32 < S1.u32; // D0 = VCC in VOPC encoding.

#### **V_CMPX_EQ_U32**

**218**

Set the per-lane condition code to 1 iff the first input is equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.u32 == S1.u32; // D0 = VCC in VOPC encoding.

**V_CMPX_LE_U32**

**219**

401 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



Set the per-lane condition code to 1 iff the first input is less than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.u32 <= S1.u32; // D0 = VCC in VOPC encoding.

#### **V_CMPX_GT_U32**

**220**

Set the per-lane condition code to 1 iff the first input is greater than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.u32 > S1.u32; // D0 = VCC in VOPC encoding.

#### **V_CMPX_NE_U32**

**221**

Set the per-lane condition code to 1 iff the first input is not equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.u32 <> S1.u32; // D0 = VCC in VOPC encoding.

#### **V_CMPX_GE_U32**

**222**

Set the per-lane condition code to 1 iff the first input is greater than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.u32 >= S1.u32; // D0 = VCC in VOPC encoding.

#### **V_CMPX_T_U32**

**223**

Set the per-lane condition code to 1. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = 1'1U; // D0 = VCC in VOPC encoding.

402 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**V_CMP_F_I64**

**224**



Set the per-lane condition code to 0. Store the result into VCC or a scalar register.

D0.u64[laneId] = 1'0U; // D0 = VCC in VOPC encoding.

**V_CMP_LT_I64**

**225**

Set the per-lane condition code to 1 iff the first input is less than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.i64 < S1.i64; // D0 = VCC in VOPC encoding.

#### **V_CMP_EQ_I64**

**226**

Set the per-lane condition code to 1 iff the first input is equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.i64 == S1.i64; // D0 = VCC in VOPC encoding.

#### **V_CMP_LE_I64**

**227**

Set the per-lane condition code to 1 iff the first input is less than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.i64 <= S1.i64; // D0 = VCC in VOPC encoding.

#### **V_CMP_GT_I64**

**228**

Set the per-lane condition code to 1 iff the first input is greater than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.i64 > S1.i64; // D0 = VCC in VOPC encoding.

403 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**229**



**V_CMP_NE_I64**

Set the per-lane condition code to 1 iff the first input is not equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.i64 <> S1.i64; // D0 = VCC in VOPC encoding.

**V_CMP_GE_I64**

**230**

Set the per-lane condition code to 1 iff the first input is greater than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.i64 >= S1.i64; // D0 = VCC in VOPC encoding.

**V_CMP_T_I64 231**

Set the per-lane condition code to 1. Store the result into VCC or a scalar register.

D0.u64[laneId] = 1'1U; // D0 = VCC in VOPC encoding.

#### **V_CMP_F_U64**

**232**

Set the per-lane condition code to 0. Store the result into VCC or a scalar register.

D0.u64[laneId] = 1'0U; // D0 = VCC in VOPC encoding.

#### **V_CMP_LT_U64**

**233**

Set the per-lane condition code to 1 iff the first input is less than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.u64 < S1.u64;

404 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



// D0 = VCC in VOPC encoding.

**V_CMP_EQ_U64**

**234**

Set the per-lane condition code to 1 iff the first input is equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.u64 == S1.u64; // D0 = VCC in VOPC encoding.

#### **V_CMP_LE_U64**

**235**

Set the per-lane condition code to 1 iff the first input is less than or equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.u64 <= S1.u64; // D0 = VCC in VOPC encoding.

#### **V_CMP_GT_U64**

**236**

Set the per-lane condition code to 1 iff the first input is greater than the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.u64 > S1.u64; // D0 = VCC in VOPC encoding.

#### **V_CMP_NE_U64**

**237**

Set the per-lane condition code to 1 iff the first input is not equal to the second input. Store the result into VCC or a scalar register.

D0.u64[laneId] = S0.u64 <> S1.u64; // D0 = VCC in VOPC encoding.

**V_CMP_GE_U64**

**238**

Set the per-lane condition code to 1 iff the first input is greater than or equal to the second input. Store the

405 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



result into VCC or a scalar register.

D0.u64[laneId] = S0.u64 >= S1.u64; // D0 = VCC in VOPC encoding.

#### **V_CMP_T_U64**

**239**

Set the per-lane condition code to 1. Store the result into VCC or a scalar register.

D0.u64[laneId] = 1'1U; // D0 = VCC in VOPC encoding.

#### **V_CMPX_F_I64**

**240**

Set the per-lane condition code to 0. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = 1'0U; // D0 = VCC in VOPC encoding.

#### **V_CMPX_LT_I64**

**241**

Set the per-lane condition code to 1 iff the first input is less than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.i64 < S1.i64; // D0 = VCC in VOPC encoding.

#### **V_CMPX_EQ_I64**

**242**

Set the per-lane condition code to 1 iff the first input is equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.i64 == S1.i64; // D0 = VCC in VOPC encoding.

**V_CMPX_LE_I64**

**243**

406 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



Set the per-lane condition code to 1 iff the first input is less than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.i64 <= S1.i64; // D0 = VCC in VOPC encoding.

#### **V_CMPX_GT_I64**

**244**

Set the per-lane condition code to 1 iff the first input is greater than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.i64 > S1.i64; // D0 = VCC in VOPC encoding.

#### **V_CMPX_NE_I64**

**245**

Set the per-lane condition code to 1 iff the first input is not equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.i64 <> S1.i64; // D0 = VCC in VOPC encoding.

#### **V_CMPX_GE_I64**

**246**

Set the per-lane condition code to 1 iff the first input is greater than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.i64 >= S1.i64; // D0 = VCC in VOPC encoding.

#### **V_CMPX_T_I64**

**247**

Set the per-lane condition code to 1. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = 1'1U; // D0 = VCC in VOPC encoding.

407 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**V_CMPX_F_U64**

**248**



Set the per-lane condition code to 0. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = 1'0U; // D0 = VCC in VOPC encoding.

#### **V_CMPX_LT_U64**

**249**

Set the per-lane condition code to 1 iff the first input is less than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.u64 < S1.u64; // D0 = VCC in VOPC encoding.

#### **V_CMPX_EQ_U64**

**250**

Set the per-lane condition code to 1 iff the first input is equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.u64 == S1.u64; // D0 = VCC in VOPC encoding.

#### **V_CMPX_LE_U64**

**251**

Set the per-lane condition code to 1 iff the first input is less than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.u64 <= S1.u64; // D0 = VCC in VOPC encoding.

#### **V_CMPX_GT_U64**

**252**

Set the per-lane condition code to 1 iff the first input is greater than the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.u64 > S1.u64; // D0 = VCC in VOPC encoding.

408 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture

**253**



#### **V_CMPX_NE_U64**

Set the per-lane condition code to 1 iff the first input is not equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.u64 <> S1.u64; // D0 = VCC in VOPC encoding.

**V_CMPX_GE_U64 254**

Set the per-lane condition code to 1 iff the first input is greater than or equal to the second input. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = S0.u64 >= S1.u64; // D0 = VCC in VOPC encoding.

**V_CMPX_T_U64 255**

Set the per-lane condition code to 1. Store the result into the EXEC mask and to VCC or a scalar register.

EXEC.u64[laneId] = D0.u64[laneId] = 1'1U; // D0 = VCC in VOPC encoding.

409 of 553

12.11. VOP3A & VOP3B Instructions

"AMD Instinct MI300" Instruction Set Architecture



## **12.12. LDS & GWS Instructions**

This suite of instructions operates on data stored within the data share memory. The instructions transfer data between VGPRs and data share memory. The bitfield map for the LDS/GWS is:



GWS instructions operate only on a single lane (the first lane active in the EXEC mask).

where: OFFSET0 = Unsigned byte offset added to the address from the ADDR VGPR. OFFSET1 = Unsigned byte offset added to the address from the ADDR VGPR. GDS = Set if GWS, cleared if LDS. OP = DS instructions. ADDR = Source LDS address VGPR 0 - 255. DATA0 = Source data0 VGPR 0 - 255. DATA1 = Source data1 VGPR 0 - 255. VDST = Destination VGPR 0- 255.

 All instructions with RTN in the name return the value that was in memory before theoperation was performed.

**DS_ADD_U32**

**0**

Add two unsigned 32-bit integer values stored in the data register and a location in a data share.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].u32; MEM[addr].u32 += DATA.u32; RETURN_DATA.u32 = tmp

**DS_SUB_U32**

**1**

Subtract an unsigned 32-bit integer value stored in the data register from a value stored in a location in a data share.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].u32; MEM[addr].u32 -= DATA.u32; RETURN_DATA.u32 = tmp

410 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture

**2**



#### **DS_RSUB_U32**

Subtract an unsigned 32-bit integer value stored in a location in a data share from a value stored in the data register.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].u32; MEM[addr].u32 = DATA.u32 - MEM[addr].u32; RETURN_DATA.u32 = tmp

**DS_INC_U32 3**

Increment an unsigned 32-bit integer value from a location in a data share with wraparound to 0 if the value exceeds a value in the data register.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].u32; src = DATA.u32; MEM[addr].u32 = tmp >= src ? 0U : tmp + 1U; RETURN_DATA.u32 = tmp

**DS_DEC_U32 4**

Decrement an unsigned 32-bit integer value from a location in a data share with wraparound to a value in the data register if the decrement yields a negative value.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].u32; src = DATA.u32; MEM[addr].u32 = ((tmp == 0U) || (tmp > src)) ? src : tmp - 1U; RETURN_DATA.u32 = tmp

#### **DS_MIN_I32**

**5**

Select the minimum of two signed 32-bit integer inputs, given two values stored in the data register and a location in a data share. Update the data share with the selected value.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].i32; src = DATA.i32; MEM[addr].i32 = src < tmp ? src : tmp; RETURN_DATA.i32 = tmp

411 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture



#### **DS_MAX_I32**

**6**

Select the maximum of two signed 32-bit integer inputs, given two values stored in the data register and a location in a data share. Update the data share with the selected value.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].i32; src = DATA.i32; MEM[addr].i32 = src >= tmp ? src : tmp; RETURN_DATA.i32 = tmp

#### **DS_MIN_U32**

**7**

Select the minimum of two unsigned 32-bit integer inputs, given two values stored in the data register and a location in a data share. Update the data share with the selected value.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].u32; src = DATA.u32; MEM[addr].u32 = src < tmp ? src : tmp; RETURN_DATA.u32 = tmp

#### **DS_MAX_U32**

**8**

Select the maximum of two unsigned 32-bit integer inputs, given two values stored in the data register and a location in a data share. Update the data share with the selected value.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].u32; src = DATA.u32; MEM[addr].u32 = src >= tmp ? src : tmp; RETURN_DATA.u32 = tmp

#### **DS_AND_B32**

**9**

Calculate bitwise AND given two unsigned 32-bit integer values stored in the data register and a location in a data share.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].b32; MEM[addr].b32 = (tmp & DATA.b32);

412 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture



RETURN_DATA.b32 = tmp

#### **DS_OR_B32**

**10**

Calculate bitwise OR given two unsigned 32-bit integer values stored in the data register and a location in a data share.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].b32; MEM[addr].b32 = (tmp | DATA.b32); RETURN_DATA.b32 = tmp

#### **DS_XOR_B32**

**11**

Calculate bitwise XOR given two unsigned 32-bit integer values stored in the data register and a location in a data share.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].b32; MEM[addr].b32 = (tmp ^ DATA.b32); RETURN_DATA.b32 = tmp

#### **DS_MSKOR_B32**

**12**

Calculate masked bitwise OR on an unsigned 32-bit integer location in a data share, given mask value and bits to OR in the data registers.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].b32; MEM[addr].b32 = ((tmp & ~DATA.b32) | DATA2.b32); RETURN_DATA.b32 = tmp

#### **DS_WRITE_B32**

**13**

Store 32 bits of data from a vector input register into a data share.

addr = CalcDsAddr(ADDR.b32, 0x0, 0x0); MEM[addr + OFFSET.u32].b32 = DATA[31 : 0]

413 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture

**14**



#### **DS_WRITE2_B32**

Store 32 bits of data from one vector input register and then 32 bits of data from a second vector input register into a data share.

addr = CalcDsAddr(ADDR.b32, 0x0, 0x0); MEM[addr + OFFSET0.u32 * 4U].b32 = DATA[31 : 0]; addr = CalcDsAddr(ADDR.b32, 0x0, 0x0); MEM[addr + OFFSET1.u32 * 4U].b32 = DATA2[31 : 0]

#### **DS_WRITE2ST64_B32**

**15**

Store 32 bits of data from one vector input register and then 32 bits of data from a second vector input register into a data share. Treat each offset as an index and multiply by a stride of 64 elements (256 bytes) to generate an offset for each DS address.

addr = CalcDsAddr(ADDR.b32, 0x0, 0x0); MEM[addr + OFFSET0.u32 * 256U].b32 = DATA[31 : 0]; addr = CalcDsAddr(ADDR.b32, 0x0, 0x0); MEM[addr + OFFSET1.u32 * 256U].b32 = DATA2[31 : 0]

#### **DS_CMPST_B32**

**16**

Compare an unsigned 32-bit integer value in the data comparison register with a location in a data share, and modify the memory location with a value in the data source register if the comparison is equal.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].b32; src = DATA2.b32; cmp = DATA.b32; MEM[addr].b32 = tmp == cmp ? src : tmp; RETURN_DATA.b32 = tmp

#### **Notes**

Caution, the order of src and cmp are the opposite of the BUFFER_ATOMIC_CMPSWAP opcode.

#### **DS_CMPST_F32**

**17**

Compare a single-precision float value in the data comparison register with a location in a data share, and modify the memory location with a value in the data source register if the comparison is equal.

414 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture



addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].f32; src = DATA2.f32; cmp = DATA.f32; MEM[addr].f32 = tmp == cmp ? src : tmp; RETURN_DATA.f32 = tmp

#### **Notes**

Caution, the order of src and cmp are the opposite of the BUFFER_ATOMIC_CMPSWAP opcode.

**DS_MIN_F32**

**18**

Select the minimum of two single-precision float inputs, given two values stored in the data register and a location in a data share. Update the data share with the selected value.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].f32; src = DATA.f32; MEM[addr].f32 = src < tmp ? src : tmp; RETURN_DATA.f32 = tmp

#### **Notes**

Floating-point compare handles NAN/INF/denorm.

**DS_MAX_F32**

**19**

Select the maximum of two single-precision float inputs, given two values stored in the data register and a location in a data share. Update the data share with the selected value.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].f32; src = DATA.f32; MEM[addr].f32 = src > tmp ? src : tmp; RETURN_DATA.f32 = tmp

#### **Notes**

Floating-point compare handles NAN/INF/denorm.

**DS_NOP**

**20**

Do nothing.

415 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture

**21**



**DS_ADD_F32**

Add two single-precision float values stored in the data register and a location in a data share.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].f32; MEM[addr].f32 += DATA.f32; RETURN_DATA.f32 = tmp

#### **Notes**

Floating-point addition handles NAN/INF/denorm.

**DS_PK_ADD_F16 23**

Add a packed 2-component half-precision float value in the data register to a location in a data share.

tmp = MEM[ADDR]; src = DATA; dst[31 : 16].f16 = tmp[31 : 16].f16 + src[31 : 16].f16; dst[15 : 0].f16 = tmp[15 : 0].f16 + src[15 : 0].f16; MEM[ADDR] = dst.b32; RETURN_DATA = tmp

#### **Notes**

Floating-point addition handles NAN/INF/denorm.

**DS_PK_ADD_BF16 24**

Add a packed 2-component BF16 float value in the data register to a location in a data share.

tmp = MEM[ADDR]; src = DATA; dst[31 : 16].bf16 = tmp[31 : 16].bf16 + src[31 : 16].bf16; dst[15 : 0].bf16 = tmp[15 : 0].bf16 + src[15 : 0].bf16; MEM[ADDR] = dst.b32; RETURN_DATA = tmp

#### **Notes**

Floating-point addition handles NAN/INF/denorm.

416 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture

**29**



#### **DS_WRITE_ADDTID_B32**

Store 32 bits of data from a vector input register into a data share. The memory base address is provided as an immediate value and the lane ID is used as an offset.

declare OFFSET0 : 8'U; declare OFFSET1 : 8'U; MEM[32'I({ OFFSET1, OFFSET0 } + M0[15 : 0]) + laneID.i32 * 4].u32 = DATA0.u32

**DS_WRITE_B8**

**30**

Store 8 bits of data from a vector register into a data share.

MEM[ADDR].b8 = DATA[7 : 0]

**DS_WRITE_B16 31**

Store 16 bits of data from a vector register into a data share.

MEM[ADDR].b16 = DATA[15 : 0]

**DS_ADD_RTN_U32 32**

Add two unsigned 32-bit integer values stored in the data register and a location in a data share. Store the original value from data share into a vector register.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].u32; MEM[addr].u32 += DATA.u32; RETURN_DATA.u32 = tmp

#### **DS_SUB_RTN_U32**

**33**

Subtract an unsigned 32-bit integer value stored in the data register from a value stored in a location in a data share. Store the original value from data share into a vector register.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].u32; MEM[addr].u32 -= DATA.u32;

417 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture



RETURN_DATA.u32 = tmp

#### **DS_RSUB_RTN_U32**

**34**

Subtract an unsigned 32-bit integer value stored in a location in a data share from a value stored in the data register. Store the original value from data share into a vector register.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].u32; MEM[addr].u32 = DATA.u32 - MEM[addr].u32; RETURN_DATA.u32 = tmp

**DS_INC_RTN_U32**

**35**

Increment an unsigned 32-bit integer value from a location in a data share with wraparound to 0 if the value exceeds a value in the data register. Store the original value from data share into a vector register.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].u32; src = DATA.u32; MEM[addr].u32 = tmp >= src ? 0U : tmp + 1U; RETURN_DATA.u32 = tmp

#### **DS_DEC_RTN_U32**

**36**

Decrement an unsigned 32-bit integer value from a location in a data share with wraparound to a value in the data register if the decrement yields a negative value. Store the original value from data share into a vector register.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].u32; src = DATA.u32; MEM[addr].u32 = ((tmp == 0U) || (tmp > src)) ? src : tmp - 1U; RETURN_DATA.u32 = tmp

#### **DS_MIN_RTN_I32**

**37**

Select the minimum of two signed 32-bit integer inputs, given two values stored in the data register and a location in a data share. Update the data share with the selected value. Store the original value from data share into a vector register.

418 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture



addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].i32; src = DATA.i32; MEM[addr].i32 = src < tmp ? src : tmp; RETURN_DATA.i32 = tmp

#### **DS_MAX_RTN_I32**

**38**

Select the maximum of two signed 32-bit integer inputs, given two values stored in the data register and a location in a data share. Update the data share with the selected value. Store the original value from data share into a vector register.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].i32; src = DATA.i32; MEM[addr].i32 = src >= tmp ? src : tmp; RETURN_DATA.i32 = tmp

#### **DS_MIN_RTN_U32**

**39**

Select the minimum of two unsigned 32-bit integer inputs, given two values stored in the data register and a location in a data share. Update the data share with the selected value. Store the original value from data share into a vector register.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].u32; src = DATA.u32; MEM[addr].u32 = src < tmp ? src : tmp; RETURN_DATA.u32 = tmp

#### **DS_MAX_RTN_U32**

**40**

Select the maximum of two unsigned 32-bit integer inputs, given two values stored in the data register and a location in a data share. Update the data share with the selected value. Store the original value from data share into a vector register.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].u32; src = DATA.u32; MEM[addr].u32 = src >= tmp ? src : tmp; RETURN_DATA.u32 = tmp

419 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture

**41**



#### **DS_AND_RTN_B32**

Calculate bitwise AND given two unsigned 32-bit integer values stored in the data register and a location in a data share. Store the original value from data share into a vector register.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].b32; MEM[addr].b32 = (tmp & DATA.b32); RETURN_DATA.b32 = tmp

#### **DS_OR_RTN_B32**

**42**

Calculate bitwise OR given two unsigned 32-bit integer values stored in the data register and a location in a data share. Store the original value from data share into a vector register.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].b32; MEM[addr].b32 = (tmp | DATA.b32); RETURN_DATA.b32 = tmp

#### **DS_XOR_RTN_B32**

**43**

Calculate bitwise XOR given two unsigned 32-bit integer values stored in the data register and a location in a data share. Store the original value from data share into a vector register.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].b32; MEM[addr].b32 = (tmp ^ DATA.b32); RETURN_DATA.b32 = tmp

#### **DS_MSKOR_RTN_B32**

**44**

Calculate masked bitwise OR on an unsigned 32-bit integer location in a data share, given mask value and bits to OR in the data registers.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].b32; MEM[addr].b32 = ((tmp & ~DATA.b32) | DATA2.b32); RETURN_DATA.b32 = tmp

420 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture

**45**



#### **DS_WRXCHG_RTN_B32**

Swap an unsigned 32-bit integer value in the data register with a location in a data share.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].b32; MEM[addr].b32 = DATA.b32; RETURN_DATA.b32 = tmp

#### **DS_WRXCHG2_RTN_B32**

**46**

Swap two unsigned 32-bit integer values in the data registers with two locations in a data share.

addr1 = ADDR_BASE.u32 + OFFSET0.u32 * 4U; addr2 = ADDR_BASE.u32 + OFFSET1.u32 * 4U; tmp1 = MEM[addr1].b32; tmp2 = MEM[addr2].b32; MEM[addr1].b32 = DATA.b32; MEM[addr2].b32 = DATA2.b32; // Note DATA2 can be any other register RETURN_DATA[31 : 0] = tmp1; RETURN_DATA[63 : 32] = tmp2

#### **DS_WRXCHG2ST64_RTN_B32**

**47**

Swap two unsigned 32-bit integer values in the data registers with two locations in a data share. Treat each offset as an index and multiply by a stride of 64 elements (256 bytes) to generate an offset for each DS address.

addr1 = ADDR_BASE.u32 + OFFSET0.u32 * 256U; addr2 = ADDR_BASE.u32 + OFFSET1.u32 * 256U; tmp1 = MEM[addr1].b32; tmp2 = MEM[addr2].b32; MEM[addr1].b32 = DATA.b32; MEM[addr2].b32 = DATA2.b32; // Note DATA2 can be any other register RETURN_DATA[31 : 0] = tmp1; RETURN_DATA[63 : 32] = tmp2

#### **DS_CMPST_RTN_B32**

**48**

Compare an unsigned 32-bit integer value in the data comparison register with a location in a data share, and modify the memory location with a value in the data source register if the comparison is equal.

421 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture



addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].b32; src = DATA2.b32; cmp = DATA.b32; MEM[addr].b32 = tmp == cmp ? src : tmp; RETURN_DATA.b32 = tmp

#### **Notes**

Caution, the order of src and cmp are the opposite of the BUFFER_ATOMIC_CMPSWAP opcode.

#### **DS_CMPST_RTN_F32**

**49**

Compare a single-precision float value in the data comparison register with a location in a data share, and modify the memory location with a value in the data source register if the comparison is equal.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].f32; src = DATA2.f32; cmp = DATA.f32; MEM[addr].f32 = tmp == cmp ? src : tmp; RETURN_DATA.f32 = tmp

#### **Notes**

Caution, the order of src and cmp are the opposite of the BUFFER_ATOMIC_CMPSWAP opcode.

**DS_MIN_RTN_F32**

**50**

Select the minimum of two single-precision float inputs, given two values stored in the data register and a location in a data share. Update the data share with the selected value. Store the original value from data share into a vector register.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].f32; src = DATA.f32; MEM[addr].f32 = src < tmp ? src : tmp; RETURN_DATA.f32 = tmp

#### **Notes**

Floating-point compare handles NAN/INF/denorm.

**DS_MAX_RTN_F32**

**51**

422 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture



Select the maximum of two single-precision float inputs, given two values stored in the data register and a location in a data share. Update the data share with the selected value. Store the original value from data share into a vector register.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].f32; src = DATA.f32; MEM[addr].f32 = src > tmp ? src : tmp; RETURN_DATA.f32 = tmp

#### **Notes**

Floating-point compare handles NAN/INF/denorm.

**DS_WRAP_RTN_B32 52**

Given a minuend from a location in data share and a subtrahend from a vector register, subtract the two values _iff_ the result is nonnegative; otherwise add a value from a second vector register to the memory location.

This calculation provides flexible wraparound semantics for subtraction.

tmp = MEM[ADDR].u32; MEM[ADDR].u32 = tmp >= DATA.u32 ? tmp - DATA.u32 : tmp + DATA2.u32; RETURN_DATA = tmp

#### **Notes**

This instruction is designed to for use in ring buffer management.

**DS_ADD_RTN_F32 53**

Add two single-precision float values stored in the data register and a location in a data share. Store the original value from data share into a vector register.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].f32; MEM[addr].f32 += DATA.f32; RETURN_DATA.f32 = tmp

#### **Notes**

Floating-point addition handles NAN/INF/denorm.

423 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture

**DS_READ_B32**

**54**



Load 32 bits of data from a data share into a vector register.

addr = CalcDsAddr(ADDR.b32, 0x0, 0x0); RETURN_DATA[31 : 0] = MEM[addr + OFFSET.u32].b32

#### **DS_READ2_B32**

**55**

Load 32 bits of data from one location in a data share and then 32 bits of data from a second location in a data share and store the results into a 64-bit vector register.

addr = CalcDsAddr(ADDR.b32, 0x0, 0x0); RETURN_DATA[31 : 0] = MEM[addr + OFFSET0.u32 * 4U].b32; addr = CalcDsAddr(ADDR.b32, 0x0, 0x0); RETURN_DATA[63 : 32] = MEM[addr + OFFSET1.u32 * 4U].b32

#### **DS_READ2ST64_B32**

**56**

Load 32 bits of data from one location in a data share and then 32 bits of data from a second location in a data share and store the results into a 64-bit vector register. Treat each offset as an index and multiply by a stride of 64 elements (256 bytes) to generate an offset for each DS address.

addr = CalcDsAddr(ADDR.b32, 0x0, 0x0); RETURN_DATA[31 : 0] = MEM[addr + OFFSET0.u32 * 256U].b32; addr = CalcDsAddr(ADDR.b32, 0x0, 0x0); RETURN_DATA[63 : 32] = MEM[addr + OFFSET1.u32 * 256U].b32

#### **DS_READ_I8**

**57**

Load 8 bits of signed data from a data share, sign extend to 32 bits and store the result into a vector register.

RETURN_DATA.i32 = 32'I(signext(MEM[ADDR].i8))

#### **DS_READ_U8**

**58**

Load 8 bits of unsigned data from a data share, zero extend to 32 bits and store the result into a vector register.

424 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture

**59**

**60**

**61**



RETURN_DATA.u32 = 32'U({ 24'0U, MEM[ADDR].u8 })

#### **DS_READ_I16**

Load 16 bits of signed data from a data share, sign extend to 32 bits and store the result into a vector register.

RETURN_DATA.i32 = 32'I(signext(MEM[ADDR].i16))

#### **DS_READ_U16**

Load 16 bits of unsigned data from a data share, zero extend to 32 bits and store the result into a vector register.

RETURN_DATA.u32 = 32'U({ 16'0U, MEM[ADDR].u16 })

#### **DS_SWIZZLE_B32**

Dword swizzle, no data is written to LDS memory.

Swizzles input thread data based on offset mask and returns; note does not read or write the DS memory banks.

Note that reading from an invalid thread results in 0x0.

This opcode supports two specific modes, FFT and rotate, plus two basic modes which swizzle in groups of 4 or 32 consecutive threads.

The FFT mode (offset >= 0xe000) swizzles the input based on offset[4:0] to support FFT calculation. Example swizzles using input {1, 2, … 20} are:

Offset[4:0]: Swizzle 0x00: {1,11,9,19,5,15,d,1d,3,13,b,1b,7,17,f,1f,2,12,a,1a,6,16,e,1e,4,14,c,1c,8,18,10,20} 0x10: {1,9,5,d,3,b,7,f,2,a,6,e,4,c,8,10,11,19,15,1d,13,1b,17,1f,12,1a,16,1e,14,1c,18,20} 0x1f: No swizzle

The rotate mode (offset >= 0xc000 and offset < 0xe000) rotates the input either left (offset[10] == 0) or right (offset[10] == 1) a number of threads equal to offset[9:5]. The rotate mode also uses a mask value which can alter the rotate result. For example, mask == 1 swaps the odd threads across every other even thread (rotate left), or even threads across every other odd thread (rotate right).

Offset[9:5]: Swizzle 0x01, mask=0, rotate left: {2,3,4,5,6,7,8,9,a,b,c,d,e,f,10,11,12,13,14,15,16,17,18,19,1a,1b,1c,1d,1e,1f,20,1}

425 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture



0x01, mask=0, rotate right: {20,1,2,3,4,5,6,7,8,9,a,b,c,d,e,f,10,11,12,13,14,15,16,17,18,19,1a,1b,1c,1d,1e,1f} 0x01, mask=1, rotate left: {1,4,3,6,5,8,7,a,9,c,b,e,d,10,f,12,11,14,13,16,15,18,17,1a,19,1c,1b,1e,1d,20,1f,2} 0x01, mask=1, rotate right: {1f,2,1,4,3,6,5,8,7,a,9,c,b,e,d,10,f,12,11,14,13,16,15,18,17,1a,19,1c,1b,1e,1d,20}

If offset < 0xc000, one of the basic swizzle modes is used based on offset[15]. If offset[15] == 1, groups of 4 consecutive threads are swizzled together. If offset[15] == 0, all 32 threads are swizzled together.

The first basic swizzle mode (when offset[15] == 1) allows full data sharing between a group of 4 consecutive threads. Any thread within the group of 4 can get data from any other thread within the group of 4, specified by the corresponding offset bits --- [1:0] for the first thread, [3:2] for the second thread, [5:4] for the third thread, [7:6] for the fourth thread. Note that the offset bits apply to all groups of 4 within a wavefront; thus if offset[1:0] == 1, then thread0 grabs thread1, thread4 grabs thread5, etc.

The second basic swizzle mode (when offset[15] == 0) allows limited data sharing between 32 consecutive threads. In this case, the offset is used to specify a 5-bit xor-mask, 5-bit or-mask, and 5-bit and-mask used to generate a thread mapping. Note that the offset bits apply to each group of 32 within a wavefront. The details of the thread mapping are listed below. Some example usages:

SWAPX16 : xor_mask = 0x10, or_mask = 0x00, and_mask = 0x1f

SWAPX8 : xor_mask = 0x08, or_mask = 0x00, and_mask = 0x1f SWAPX4 : xor_mask = 0x04, or_mask = 0x00, and_mask = 0x1f SWAPX2 : xor_mask = 0x02, or_mask = 0x00, and_mask = 0x1f SWAPX1 : xor_mask = 0x01, or_mask = 0x00, and_mask = 0x1f REVERSEX32 : xor_mask = 0x1f, or_mask = 0x00, and_mask = 0x1f REVERSEX16 : xor_mask = 0x0f, or_mask = 0x00, and_mask = 0x1f REVERSEX8 : xor_mask = 0x07, or_mask = 0x00, and_mask = 0x1f REVERSEX4 : xor_mask = 0x03, or_mask = 0x00, and_mask = 0x1f REVERSEX2 : xor_mask = 0x01 or_mask = 0x00, and_mask = 0x1f BCASTX32: xor_mask = 0x00, or_mask = thread, and_mask = 0x00 BCASTX16: xor_mask = 0x00, or_mask = thread, and_mask = 0x10 BCASTX8: xor_mask = 0x00, or_mask = thread, and_mask = 0x18

BCASTX4: xor_mask = 0x00, or_mask = thread, and_mask = 0x1c

BCASTX2: xor_mask = 0x00, or_mask = thread, and_mask = 0x1e Pseudocode follows:

426 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture



offset = offset1:offset0; if (offset >= 0xe000) { // FFT decomposition mask = offset[4:0]; for (i = 0; i < 64; i++) { j = reverse_bits(i & 0x1f); j = (j >> count_ones(mask)); j |= (i & mask); j |= i & 0x20; thread_out[i] = thread_valid[j] ? thread_in[j] : 0; } } elsif (offset >= 0xc000) { // rotate rotate = offset[9:5]; mask = offset[4:0]; if (offset[10]) { rotate = -rotate; } for (i = 0; i < 64; i++) { j = (i & mask) | ((i + rotate) & ~mask); j |= i & 0x20; thread_out[i] = thread_valid[j] ? thread_in[j] : 0; } } elsif (offset[15]) { // full data sharing within 4 consecutive threads for (i = 0; i < 64; i+=4) { thread_out[i+0] = thread_valid[i+offset[1:0]]?thread_in[i+offset[1:0]]:0; thread_out[i+1] = thread_valid[i+offset[3:2]]?thread_in[i+offset[3:2]]:0; thread_out[i+2] = thread_valid[i+offset[5:4]]?thread_in[i+offset[5:4]]:0; thread_out[i+3] = thread_valid[i+offset[7:6]]?thread_in[i+offset[7:6]]:0; }

} else { // offset[15] == 0 // limited data sharing within 32 consecutive threads xor_mask = offset[14:10]; or_mask = offset[9:5]; and_mask = offset[4:0]; for (i = 0; i < 64; i++) { j = (((i & 0x1f) & and_mask) | or_mask) ^ xor_mask; j |= (i & 0x20); // which group of 32 thread_out[i] = thread_valid[j] ? thread_in[j] : 0; } }

**DS_PERMUTE_B32**

**62**

427 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture



Forward permute. This does not access LDS memory and may be called even if no LDS memory is allocated to the wave. It uses LDS to implement an arbitrary swizzle across threads in a wavefront.

Note the address passed in is the thread ID multiplied by 4.

If multiple sources map to the same destination lane, standard LDS arbitration rules determine which write wins.

See also DS_BPERMUTE_B32.

// VGPR[laneId][index] is the VGPR RAM // VDST, ADDR and DATA0 are from the microcode DS encoding declare tmp : 32'B[64]; declare OFFSET : 16'U; declare DATA0 : 32'U; declare VDST : 32'U; for i in 0 : 63 do tmp[i] = 0x0 endfor; for i in 0 : 63 do // If a source thread is disabled, it does not propagate data. if EXEC[i].u1 then // ADDR needs to be divided by 4. // High-order bits are ignored. dst_lane = (VGPR[i][ADDR].u32 + OFFSET.u32) / 4U % 64U; tmp[dst_lane] = VGPR[i][DATA0] endif endfor; // Copy data into destination VGPRs. If multiple sources // select the same destination thread, the highest-numbered // source thread wins. for i in 0 : 63 do if EXEC[i].u1 then VGPR[i][VDST] = tmp[i] endif endfor

#### **Notes**

Examples (simplified 4-thread wavefronts):

VGPR[SRC0] = { A, B, C, D } VGPR[ADDR] = { 0, 0, 12, 4 } EXEC = 0xF, OFFSET = 0 VGPR[VDST] = { B, D, 0, C } VGPR[SRC0] = { A, B, C, D } VGPR[ADDR] = { 0, 0, 12, 4 } EXEC = 0xA, OFFSET = 0 VGPR[VDST] = { -, D, -, 0 }

428 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture

**DS_BPERMUTE_B32**

**63**



Backward permute. This does not access LDS memory and may be called even if no LDS memory is allocated to the wave. It uses LDS hardware to implement an arbitrary swizzle across threads in a wavefront.

Note the address passed in is the thread ID multiplied by 4.

Note that EXEC mask is applied to both VGPR read and write. If src_lane selects a disabled thread then zero is returned.

See also DS_PERMUTE_B32.

// VGPR[laneId][index] is the VGPR RAM // VDST, ADDR and DATA0 are from the microcode DS encoding declare tmp : 32'B[64]; declare OFFSET : 16'U; declare DATA0 : 32'U; declare VDST : 32'U; for i in 0 : 63 do tmp[i] = 0x0 endfor; for i in 0 : 63 do // ADDR needs to be divided by 4. // High-order bits are ignored. src_lane = (VGPR[i][ADDR].u32 + OFFSET.u32) / 4U % 64U; // EXEC is applied to the source VGPR reads. if EXEC[src_lane].u1 then tmp[i] = VGPR[src_lane][DATA0] endif endfor; // Copy data into destination VGPRs. Some source // data may be broadcast to multiple lanes. for i in 0 : 63 do if EXEC[i].u1 then VGPR[i][VDST] = tmp[i] endif endfor

#### **Notes**

Examples (simplified 4-thread wavefronts):

VGPR[SRC0] = { A, B, C, D } VGPR[ADDR] = { 0, 0, 12, 4 } EXEC = 0xF, OFFSET = 0 VGPR[VDST] = { A, A, D, B }

VGPR[SRC0] = { A, B, C, D } VGPR[ADDR] = { 0, 0, 12, 4 } EXEC = 0xA, OFFSET = 0 VGPR[VDST] = { -, 0, -, B }

429 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture

**DS_ADD_U64**

**64**



Add two unsigned 64-bit integer values stored in the data register and a location in a data share.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].u64; MEM[addr].u64 += DATA.u64; RETURN_DATA.u64 = tmp

#### **DS_SUB_U64**

**65**

Subtract an unsigned 64-bit integer value stored in the data register from a value stored in a location in a data share.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].u64; MEM[addr].u64 -= DATA.u64; RETURN_DATA.u64 = tmp

#### **DS_RSUB_U64**

**66**

Subtract an unsigned 64-bit integer value stored in a location in a data share from a value stored in the data register.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].u64; MEM[addr].u64 = DATA.u64 - MEM[addr].u64; RETURN_DATA.u64 = tmp

#### **DS_INC_U64**

**67**

Increment an unsigned 64-bit integer value from a location in a data share with wraparound to 0 if the value exceeds a value in the data register.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].u64; src = DATA.u64; MEM[addr].u64 = tmp >= src ? 0ULL : tmp + 1ULL; RETURN_DATA.u64 = tmp

430 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture

**68**



#### **DS_DEC_U64**

Decrement an unsigned 64-bit integer value from a location in a data share with wraparound to a value in the data register if the decrement yields a negative value.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].u64; src = DATA.u64; MEM[addr].u64 = ((tmp == 0ULL) || (tmp > src)) ? src : tmp - 1ULL; RETURN_DATA.u64 = tmp

#### **DS_MIN_I64**

**69**

Select the minimum of two signed 64-bit integer inputs, given two values stored in the data register and a location in a data share. Update the data share with the selected value.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].i64; src = DATA.i64; MEM[addr].i64 = src < tmp ? src : tmp; RETURN_DATA.i64 = tmp

#### **DS_MAX_I64**

**70**

Select the maximum of two signed 64-bit integer inputs, given two values stored in the data register and a location in a data share. Update the data share with the selected value.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].i64; src = DATA.i64; MEM[addr].i64 = src >= tmp ? src : tmp; RETURN_DATA.i64 = tmp

#### **DS_MIN_U64**

**71**

Select the minimum of two unsigned 64-bit integer inputs, given two values stored in the data register and a location in a data share. Update the data share with the selected value.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].u64; src = DATA.u64; MEM[addr].u64 = src < tmp ? src : tmp;

431 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture



RETURN_DATA.u64 = tmp

#### **DS_MAX_U64**

**72**

Select the maximum of two unsigned 64-bit integer inputs, given two values stored in the data register and a location in a data share. Update the data share with the selected value.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].u64; src = DATA.u64; MEM[addr].u64 = src >= tmp ? src : tmp; RETURN_DATA.u64 = tmp

#### **DS_AND_B64**

**73**

Calculate bitwise AND given two unsigned 64-bit integer values stored in the data register and a location in a data share.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].b64; MEM[addr].b64 = (tmp & DATA.b64); RETURN_DATA.b64 = tmp

**DS_OR_B64**

**74**

Calculate bitwise OR given two unsigned 64-bit integer values stored in the data register and a location in a data share.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].b64; MEM[addr].b64 = (tmp | DATA.b64); RETURN_DATA.b64 = tmp

#### **DS_XOR_B64**

**75**

Calculate bitwise XOR given two unsigned 64-bit integer values stored in the data register and a location in a data share.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].b64;

432 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture

**76**



MEM[addr].b64 = (tmp ^ DATA.b64); RETURN_DATA.b64 = tmp

#### **DS_MSKOR_B64**

Calculate masked bitwise OR on an unsigned 64-bit integer location in a data share, given mask value and bits to OR in the data registers.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].b64; MEM[addr].b64 = ((tmp & ~DATA.b64) | DATA2.b64); RETURN_DATA.b64 = tmp

#### **DS_WRITE_B64**

**77**

Store 64 bits of data from a vector input register into a data share.

addr = CalcDsAddr(ADDR.b32, 0x0, 0x0); MEM[addr + OFFSET.u32].b32 = DATA[31 : 0]; MEM[addr + OFFSET.u32 + 4U].b32 = DATA[63 : 32]

#### **DS_WRITE2_B64**

**78**

Store 64 bits of data from one vector input register and then 64 bits of data from a second vector input register into a data share.

addr = CalcDsAddr(ADDR.b32, 0x0, 0x0); MEM[addr + OFFSET0.u32 * 8U].b32 = DATA[31 : 0]; MEM[addr + OFFSET0.u32 * 8U + 4U].b32 = DATA[63 : 32]; addr = CalcDsAddr(ADDR.b32, 0x0, 0x0); MEM[addr + OFFSET1.u32 * 8U].b32 = DATA2[31 : 0]; MEM[addr + OFFSET1.u32 * 8U + 4U].b32 = DATA2[63 : 32]

#### **DS_WRITE2ST64_B64**

**79**

Store 64 bits of data from one vector input register and then 64 bits of data from a second vector input register into a data share. Treat each offset as an index and multiply by a stride of 64 elements (256 bytes) to generate an offset for each DS address.

addr = CalcDsAddr(ADDR.b32, 0x0, 0x0);

433 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture



MEM[addr + OFFSET0.u32 * 512U].b32 = DATA[31 : 0]; MEM[addr + OFFSET0.u32 * 512U + 4U].b32 = DATA[63 : 32]; addr = CalcDsAddr(ADDR.b32, 0x0, 0x0); MEM[addr + OFFSET1.u32 * 512U].b32 = DATA2[31 : 0]; MEM[addr + OFFSET1.u32 * 512U + 4U].b32 = DATA2[63 : 32]

#### **DS_CMPST_B64**

**80**

Compare an unsigned 64-bit integer value in the data comparison register with a location in a data share, and modify the memory location with a value in the data source register if the comparison is equal.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].b64; src = DATA2.b64; cmp = DATA.b64; MEM[addr].b64 = tmp == cmp ? src : tmp; RETURN_DATA.b64 = tmp

#### **Notes**

Caution, the order of src and cmp are the opposite of the BUFFER_ATOMIC_CMPSWAP opcode.

#### **DS_CMPST_F64**

**81**

Compare a double-precision float value in the data comparison register with a location in a data share, and modify the memory location with a value in the data source register if the comparison is equal.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].f64; src = DATA2.f64; cmp = DATA.f64; MEM[addr].f64 = tmp == cmp ? src : tmp; RETURN_DATA.f64 = tmp

#### **Notes**

Caution, the order of src and cmp are the opposite of the BUFFER_ATOMIC_CMPSWAP opcode.

#### **DS_MIN_F64**

**82**

Select the minimum of two double-precision float inputs, given two values stored in the data register and a location in a data share. Update the data share with the selected value.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32);

434 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture



tmp = MEM[addr].f64; src = DATA.f64; MEM[addr].f64 = src < tmp ? src : tmp; RETURN_DATA.f64 = tmp

#### **Notes**

Floating-point compare handles NAN/INF/denorm.

**DS_MAX_F64**

**83**

Select the maximum of two double-precision float inputs, given two values stored in the data register and a location in a data share. Update the data share with the selected value.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].f64; src = DATA.f64; MEM[addr].f64 = src > tmp ? src : tmp; RETURN_DATA.f64 = tmp

#### **Notes**

Floating-point compare handles NAN/INF/denorm.

**DS_WRITE_B8_D16_HI 84**

Store 8 bits of data from the high bits of a vector register into a data share.

MEM[ADDR].b8 = DATA[23 : 16]

**DS_WRITE_B16_D16_HI 85**

Store 16 bits of data from the high bits of a vector register into a data share.

MEM[ADDR].b16 = DATA[31 : 16]

**DS_READ_U8_D16 86**

Load 8 bits of unsigned data from a data share, zero extend to 16 bits and store the result into the low 16 bits of a vector register.

435 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture

**87**



RETURN_DATA[15 : 0].u16 = 16'U({ 8'0U, MEM[ADDR].u8 }); // RETURN_DATA[31:16] is preserved.

#### **DS_READ_U8_D16_HI**

Load 8 bits of unsigned data from a data share, zero extend to 16 bits and store the result into the high 16 bits of a vector register.

RETURN_DATA[31 : 16].u16 = 16'U({ 8'0U, MEM[ADDR].u8 }); // RETURN_DATA[15:0] is preserved.

#### **DS_READ_I8_D16**

**88**

Load 8 bits of signed data from a data share, sign extend to 16 bits and store the result into the low 16 bits of a vector register.

RETURN_DATA[15 : 0].i16 = 16'I(signext(MEM[ADDR].i8)); // RETURN_DATA[31:16] is preserved.

#### **DS_READ_I8_D16_HI**

**89**

Load 8 bits of signed data from a data share, sign extend to 16 bits and store the result into the high 16 bits of a vector register.

RETURN_DATA[31 : 16].i16 = 16'I(signext(MEM[ADDR].i8)); // RETURN_DATA[15:0] is preserved.

**DS_READ_U16_D16**

**90**

Load 16 bits of unsigned data from a data share and store the result into the low 16 bits of a vector register.

RETURN_DATA[15 : 0].u16 = MEM[ADDR].u16; // RETURN_DATA[31:16] is preserved.

**DS_READ_U16_D16_HI**

**91**

436 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture



Load 16 bits of unsigned data from a data share and store the result into the high 16 bits of a vector register.

RETURN_DATA[31 : 16].u16 = MEM[ADDR].u16; // RETURN_DATA[15:0] is preserved.

**DS_ADD_F64**

**92**

Add a double-precision float value in the data register to a location in a data share.

tmp = MEM[ADDR].f64; MEM[ADDR].f64 += DATA.f64; RETURN_DATA = tmp

#### **Notes**

Floating-point addition handles NAN/INF/denorm.

**DS_ADD_RTN_U64**

**96**

Add two unsigned 64-bit integer values stored in the data register and a location in a data share. Store the original value from data share into a vector register.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].u64; MEM[addr].u64 += DATA.u64; RETURN_DATA.u64 = tmp

#### **DS_SUB_RTN_U64**

**97**

Subtract an unsigned 64-bit integer value stored in the data register from a value stored in a location in a data share. Store the original value from data share into a vector register.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].u64; MEM[addr].u64 -= DATA.u64; RETURN_DATA.u64 = tmp

**DS_RSUB_RTN_U64**

**98**

Subtract an unsigned 64-bit integer value stored in a location in a data share from a value stored in the data

437 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture



register. Store the original value from data share into a vector register.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].u64; MEM[addr].u64 = DATA.u64 - MEM[addr].u64; RETURN_DATA.u64 = tmp

**DS_INC_RTN_U64**

**99**

Increment an unsigned 64-bit integer value from a location in a data share with wraparound to 0 if the value exceeds a value in the data register. Store the original value from data share into a vector register.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].u64; src = DATA.u64; MEM[addr].u64 = tmp >= src ? 0ULL : tmp + 1ULL; RETURN_DATA.u64 = tmp

#### **DS_DEC_RTN_U64**

**100**

Decrement an unsigned 64-bit integer value from a location in a data share with wraparound to a value in the data register if the decrement yields a negative value. Store the original value from data share into a vector register.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].u64; src = DATA.u64; MEM[addr].u64 = ((tmp == 0ULL) || (tmp > src)) ? src : tmp - 1ULL; RETURN_DATA.u64 = tmp

#### **DS_MIN_RTN_I64**

**101**

Select the minimum of two signed 64-bit integer inputs, given two values stored in the data register and a location in a data share. Update the data share with the selected value. Store the original value from data share into a vector register.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].i64; src = DATA.i64; MEM[addr].i64 = src < tmp ? src : tmp; RETURN_DATA.i64 = tmp

438 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture

**102**



#### **DS_MAX_RTN_I64**

Select the maximum of two signed 64-bit integer inputs, given two values stored in the data register and a location in a data share. Update the data share with the selected value. Store the original value from data share into a vector register.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].i64; src = DATA.i64; MEM[addr].i64 = src >= tmp ? src : tmp; RETURN_DATA.i64 = tmp

#### **DS_MIN_RTN_U64**

**103**

Select the minimum of two unsigned 64-bit integer inputs, given two values stored in the data register and a location in a data share. Update the data share with the selected value. Store the original value from data share into a vector register.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].u64; src = DATA.u64; MEM[addr].u64 = src < tmp ? src : tmp; RETURN_DATA.u64 = tmp

#### **DS_MAX_RTN_U64**

**104**

Select the maximum of two unsigned 64-bit integer inputs, given two values stored in the data register and a location in a data share. Update the data share with the selected value. Store the original value from data share into a vector register.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].u64; src = DATA.u64; MEM[addr].u64 = src >= tmp ? src : tmp; RETURN_DATA.u64 = tmp

#### **DS_AND_RTN_B64**

**105**

Calculate bitwise AND given two unsigned 64-bit integer values stored in the data register and a location in a data share. Store the original value from data share into a vector register.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32);

439 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture



tmp = MEM[addr].b64; MEM[addr].b64 = (tmp & DATA.b64); RETURN_DATA.b64 = tmp

#### **DS_OR_RTN_B64**

**106**

Calculate bitwise OR given two unsigned 64-bit integer values stored in the data register and a location in a data share. Store the original value from data share into a vector register.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].b64; MEM[addr].b64 = (tmp | DATA.b64); RETURN_DATA.b64 = tmp

#### **DS_XOR_RTN_B64**

**107**

Calculate bitwise XOR given two unsigned 64-bit integer values stored in the data register and a location in a data share. Store the original value from data share into a vector register.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].b64; MEM[addr].b64 = (tmp ^ DATA.b64); RETURN_DATA.b64 = tmp

#### **DS_MSKOR_RTN_B64**

**108**

Calculate masked bitwise OR on an unsigned 64-bit integer location in a data share, given mask value and bits to OR in the data registers.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].b64; MEM[addr].b64 = ((tmp & ~DATA.b64) | DATA2.b64); RETURN_DATA.b64 = tmp

**DS_WRXCHG_RTN_B64**

**109**

Swap an unsigned 64-bit integer value in the data register with a location in a data share.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].b64;

440 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture



MEM[addr].b64 = DATA.b64; RETURN_DATA.b64 = tmp

#### **DS_WRXCHG2_RTN_B64**

**110**

Swap two unsigned 64-bit integer values in the data registers with two locations in a data share.

addr1 = ADDR_BASE.u32 + OFFSET0.u32 * 8U; addr2 = ADDR_BASE.u32 + OFFSET1.u32 * 8U; tmp1 = MEM[addr1].b64; tmp2 = MEM[addr2].b64; MEM[addr1].b64 = DATA.b64; MEM[addr2].b64 = DATA2.b64; // Note DATA2 can be any other register RETURN_DATA[63 : 0] = tmp1; RETURN_DATA[127 : 64] = tmp2

#### **DS_WRXCHG2ST64_RTN_B64**

**111**

Swap two unsigned 64-bit integer values in the data registers with two locations in a data share. Treat each offset as an index and multiply by a stride of 64 elements (256 bytes) to generate an offset for each DS address.

addr1 = ADDR_BASE.u32 + OFFSET0.u32 * 512U; addr2 = ADDR_BASE.u32 + OFFSET1.u32 * 512U; tmp1 = MEM[addr1].b64; tmp2 = MEM[addr2].b64; MEM[addr1].b64 = DATA.b64; MEM[addr2].b64 = DATA2.b64; // Note DATA2 can be any other register RETURN_DATA[63 : 0] = tmp1; RETURN_DATA[127 : 64] = tmp2

#### **DS_CMPST_RTN_B64**

**112**

Compare an unsigned 64-bit integer value in the data comparison register with a location in a data share, and modify the memory location with a value in the data source register if the comparison is equal.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].b64; src = DATA2.b64; cmp = DATA.b64; MEM[addr].b64 = tmp == cmp ? src : tmp; RETURN_DATA.b64 = tmp

441 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture



#### **Notes**

Caution, the order of src and cmp are the opposite of the BUFFER_ATOMIC_CMPSWAP opcode.

#### **DS_CMPST_RTN_F64**

**113**

Compare a double-precision float value in the data comparison register with a location in a data share, and modify the memory location with a value in the data source register if the comparison is equal.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].f64; src = DATA2.f64; cmp = DATA.f64; MEM[addr].f64 = tmp == cmp ? src : tmp; RETURN_DATA.f64 = tmp

#### **Notes**

Caution, the order of src and cmp are the opposite of the BUFFER_ATOMIC_CMPSWAP opcode.

#### **DS_MIN_RTN_F64**

**114**

Select the minimum of two double-precision float inputs, given two values stored in the data register and a location in a data share. Update the data share with the selected value. Store the original value from data share into a vector register.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].f64; src = DATA.f64; MEM[addr].f64 = src < tmp ? src : tmp; RETURN_DATA.f64 = tmp

#### **Notes**

Floating-point compare handles NAN/INF/denorm.

#### **DS_MAX_RTN_F64**

**115**

Select the maximum of two double-precision float inputs, given two values stored in the data register and a location in a data share. Update the data share with the selected value. Store the original value from data share into a vector register.

addr = CalcDsAddr(ADDR.b32, OFFSET0.b32, OFFSET1.b32); tmp = MEM[addr].f64;

442 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture

**118**



src = DATA.f64; MEM[addr].f64 = src > tmp ? src : tmp; RETURN_DATA.f64 = tmp

#### **Notes**

Floating-point compare handles NAN/INF/denorm.

**DS_READ_B64**

Load 64 bits of data from a data share into a vector register.

addr = CalcDsAddr(ADDR.b32, 0x0, 0x0); RETURN_DATA[31 : 0] = MEM[addr + OFFSET.u32].b32; RETURN_DATA[63 : 32] = MEM[addr + OFFSET.u32 + 4U].b32

#### **DS_READ2_B64**

**119**

Load 64 bits of data from one location in a data share and then 64 bits of data from a second location in a data share and store the results into a 128-bit vector register.

addr = CalcDsAddr(ADDR.b32, 0x0, 0x0); RETURN_DATA[31 : 0] = MEM[addr + OFFSET0.u32 * 8U].b32; RETURN_DATA[63 : 32] = MEM[addr + OFFSET0.u32 * 8U + 4U].b32; addr = CalcDsAddr(ADDR.b32, 0x0, 0x0); RETURN_DATA[95 : 64] = MEM[addr + OFFSET1.u32 * 8U].b32; RETURN_DATA[127 : 96] = MEM[addr + OFFSET1.u32 * 8U + 4U].b32

#### **DS_READ2ST64_B64**

**120**

Load 64 bits of data from one location in a data share and then 64 bits of data from a second location in a data share and store the results into a 128-bit vector register. Treat each offset as an index and multiply by a stride of 64 elements (256 bytes) to generate an offset for each DS address.

addr = CalcDsAddr(ADDR.b32, 0x0, 0x0); RETURN_DATA[31 : 0] = MEM[addr + OFFSET0.u32 * 512U].b32; RETURN_DATA[63 : 32] = MEM[addr + OFFSET0.u32 * 512U + 4U].b32; addr = CalcDsAddr(ADDR.b32, 0x0, 0x0); RETURN_DATA[95 : 64] = MEM[addr + OFFSET1.u32 * 512U].b32; RETURN_DATA[127 : 96] = MEM[addr + OFFSET1.u32 * 512U + 4U].b32

443 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture

**124**



#### **DS_ADD_RTN_F64**

Add a double-precision float value in the data register to a location in a data share. Store the original value from data share into a vector register.

tmp = MEM[ADDR].f64; MEM[ADDR].f64 += DATA.f64; RETURN_DATA = tmp

#### **Notes**

Floating-point addition handles NAN/INF/denorm.

#### **DS_CONDXCHG32_RTN_B64**

**126**

Perform 2 conditional write exchanges, where each conditional write exchange writes a 32 bit value from a data register to a location in data share iff the most significant bit of the data value is set.

declare OFFSET0 : 8'U; declare OFFSET1 : 8'U; declare RETURN_DATA : 32'U[2]; ADDR = S0.u32; DATA = S1.u64; offset = { OFFSET1, OFFSET0 }; ADDR0 = ((ADDR + offset.u32) & 0xfff8U); ADDR1 = ADDR0 + 4U; RETURN_DATA[0] = LDS[ADDR0].u32; if DATA[31] then LDS[ADDR0] = { 1'0, DATA[30 : 0] } endif; RETURN_DATA[1] = LDS[ADDR1].u32; if DATA[63] then LDS[ADDR1] = { 1'0, DATA[62 : 32] } endif

#### **DS_GWS_SEMA_RELEASE_ALL**

**152**

GDS Only: The GWS resource (rid) indicated processes this opcode by updating the counter and labeling the specified resource as a semaphore.

// Determine the GWS resource to work on rid[5:0] = gds_base[5:0] + offset0[5:0];

// Incr the state counter of the resource state.counter[rid] = state.wave_in_queue; state.type = SEMAPHORE;

444 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture

**153**



return rd_done; //release calling wave

This action releases ALL queued waves; it has no effect if no waves are present.

#### **DS_GWS_INIT**

GDS Only: Initialize a barrier or semaphore resource.

// Determine the GWS resource to work on rid[5:0] = gds_base[5:0] + offset0[5:0]; // Get the value to use in init index = find_first_valid(vector mask) value = DATA[thread: index] // Set the state of the resource state.counter[rid] = lsb(value); //limit #waves state.flag[rid] = 0; return rd_done; //release calling wave

**CAUTION** : The VGPR operand MUST be even-aligned for this instruction. Only 32 bits are used but hardware treats this instruction as a 64 bit read.

#### **DS_GWS_SEMA_V**

**154**

GDS Only: The GWS resource indicated processes this opcode by updating the counter and labeling the resource as a semaphore.

//Determine the GWS resource to work on rid[5:0] = gds_base[5:0] + offset0[5:0]; //Incr the state counter of the resource state.counter[rid] += 1; state.type = SEMAPHORE; return rd_done; //release calling wave

This action releases one wave if any are queued in this resource.

**DS_GWS_SEMA_BR**

**155**

GDS Only: The GWS resource indicated processes this opcode by updating the counter by the bulk release delivered count and labeling the resource as a semaphore.

//Determine the GWS resource to work on rid[5:0] = gds_base[5:0] + offset0[5:0];

445 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture



index =  find first valid (vector mask) count = DATA[thread: index]; //Add count to the resource state counter state.counter[rid] += count; state.type = SEMAPHORE; return rd_done; //release calling wave

This action releases count number of waves, promptly if queued, or as they arrive from the noted resource.

**CAUTION** : The VGPR operand MUST be even-aligned for this instruction. Only 32 bits are used but hardware treats this instruction as a 64 bit read.

#### **DS_GWS_SEMA_P**

**156**

GDS Only: The GWS resource indicated processes this opcode by queueing it until counter enables a release and then decrementing the counter of the resource as a semaphore.

//Determine the GWS resource to work on rid[5:0] = gds_base[5:0] + offset0[5:0]; state.type = SEMAPHORE; ENQUEUE until(state[rid].counter > 0) state[rid].counter -= 1; return rd_done;

#### **DS_GWS_BARRIER**

**157**

GDS Only: The GWS resource indicated processes this opcode by queueing it until barrier is satisfied. The number of waves needed is passed in as DATA of first valid thread.

//Determine the GWS resource to work on rid[5:0] = gds_base[5:0] + OFFSET0[5:0]; index =  find first valid (vector mask); value = DATA[thread: index]; // Input Decision Machine state.type[rid] = BARRIER; if(state[rid].counter <= 0) then thread[rid].flag = state[rid].flag; ENQUEUE; state[rid].flag = !state.flag; state[rid].counter = value; return rd_done; else state[rid].counter -= 1; thread.flag = state[rid].flag; ENQUEUE; endif.

446 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture



Since the waves deliver the count for the next barrier, this function can have a different size barrier for each occurrence.

// Release Machine if(state.type == BARRIER) then if(state.flag != thread.flag) then return rd_done; endif; endif.

**CAUTION** : The VGPR operand MUST be even-aligned for this instruction. Only 32 bits are used but hardware treats this instruction as a 64 bit read.

#### **DS_READ_ADDTID_B32**

**182**

Load 32 bits of data from a data share into a vector register. The memory base address is provided as an immediate value and the lane ID is used as an offset.

declare OFFSET0 : 8'U; declare OFFSET1 : 8'U; RETURN_DATA.u32 = MEM[32'I({ OFFSET1, OFFSET0 } + M0[15 : 0]) + laneID.i32 * 4].u32

#### **DS_PK_ADD_RTN_F16**

**183**

Add a packed 2-component half-precision float value in the data register to a location in a data share. Store the original value from data share into a vector register.

tmp = MEM[ADDR]; src = DATA; dst[31 : 16].f16 = tmp[31 : 16].f16 + src[31 : 16].f16; dst[15 : 0].f16 = tmp[15 : 0].f16 + src[15 : 0].f16; MEM[ADDR] = dst.b32; RETURN_DATA = tmp

#### **Notes**

Floating-point addition handles NAN/INF/denorm.

**DS_PK_ADD_RTN_BF16**

**184**

Add a packed 2-component BF16 float value in the data register to a location in a data share. Store the original value from data share into a vector register.

447 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture



tmp = MEM[ADDR]; src = DATA; dst[31 : 16].bf16 = tmp[31 : 16].bf16 + src[31 : 16].bf16; dst[15 : 0].bf16 = tmp[15 : 0].bf16 + src[15 : 0].bf16; MEM[ADDR] = dst.b32; RETURN_DATA = tmp

#### **Notes**

Floating-point addition handles NAN/INF/denorm.

#### **DS_CONSUME**

**189**

Subtract (count_bits(exec_mask)) from the value stored in DS memory at (M0.base + instr_offset) if GDS, or at instr_offset if LDS. Return the pre-operation value to VGPRs.

**DS_APPEND 190**

Add (count_bits(exec_mask)) to the value stored in DS memory at (M0.base + instr_offset) if GDS, or at instr_offset if LDS. Return the pre-operation value to VGPRs.

**DS_WRITE_B96 222**

Store 96 bits of data from a vector input register into a data share.

addr = CalcDsAddr(ADDR.b32, 0x0, 0x0); MEM[addr + OFFSET.u32].b32 = DATA[31 : 0]; MEM[addr + OFFSET.u32 + 4U].b32 = DATA[63 : 32]; MEM[addr + OFFSET.u32 + 8U].b32 = DATA[95 : 64]

**DS_WRITE_B128 223**

Store 128 bits of data from a vector input register into a data share.

addr = CalcDsAddr(ADDR.b32, 0x0, 0x0); MEM[addr + OFFSET.u32].b32 = DATA[31 : 0]; MEM[addr + OFFSET.u32 + 4U].b32 = DATA[63 : 32]; MEM[addr + OFFSET.u32 + 8U].b32 = DATA[95 : 64]; MEM[addr + OFFSET.u32 + 12U].b32 = DATA[127 : 96]

448 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture

**DS_READ_B96**

**254**



Load 96 bits of data from a data share into a vector register.

addr = CalcDsAddr(ADDR.b32, 0x0, 0x0); RETURN_DATA[31 : 0] = MEM[addr + OFFSET.u32].b32; RETURN_DATA[63 : 32] = MEM[addr + OFFSET.u32 + 4U].b32; RETURN_DATA[95 : 64] = MEM[addr + OFFSET.u32 + 8U].b32

**DS_READ_B128**

**255**

Load 128 bits of data from a data share into a vector register.

addr = CalcDsAddr(ADDR.b32, 0x0, 0x0); RETURN_DATA[31 : 0] = MEM[addr + OFFSET.u32].b32; RETURN_DATA[63 : 32] = MEM[addr + OFFSET.u32 + 4U].b32; RETURN_DATA[95 : 64] = MEM[addr + OFFSET.u32 + 8U].b32; RETURN_DATA[127 : 96] = MEM[addr + OFFSET.u32 + 12U].b32

449 of 553

12.12. LDS & GWS Instructions

"AMD Instinct MI300" Instruction Set Architecture



## **12.13. MUBUF Instructions**

The bitfield map of the MUBUF format is:



where:

OFFSET  = Unsigned immediate byte offset. OFFEN   = Send offset either as VADDR or as zero.. IDXEN   = Send index either as VADDR or as zero. LDS     = Data read from/written to LDS or VGPR. OP      = Instruction Opcode. VADDR   = VGPR address source. VDATA   = Destination vector GPR. SRSRC   = Scalar GPR that specifies resource constant. ACC     = Return to ACC VGPRs SC      = Scope NT      = Non-Temporal SOFFSET = Byte offset added to the memory address of an SGPR.

#### **BUFFER_LOAD_FORMAT_X**

**0**

Load 1-component formatted data from a buffer surface, convert the data to 32 bit integral or floating point format, then store the result into a vector register. The resource descriptor specifies the data format of the surface.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); VDATA[31 : 0].b32 = ConvertFromFormat(MEM[addr + ChannelOffsetX()]); // Mem access size depends on format

#### **BUFFER_LOAD_FORMAT_XY**

**1**

Load 2-component formatted data from a buffer surface, convert the data to 32 bit integral or floating point format, then store the result into a vector register. The resource descriptor specifies the data format of the surface.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); VDATA[31 : 0].b32 = ConvertFromFormat(MEM[addr + ChannelOffsetX()]); // Mem access size depends on format VDATA[63 : 32].b32 = ConvertFromFormat(MEM[addr + ChannelOffsetY()])

**BUFFER_LOAD_FORMAT_XYZ**

**2**

450 of 553

12.13. MUBUF Instructions

"AMD Instinct MI300" Instruction Set Architecture



Load 3-component formatted data from a buffer surface, convert the data to 32 bit integral or floating point format, then store the result into a vector register. The resource descriptor specifies the data format of the surface.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); VDATA[31 : 0].b32 = ConvertFromFormat(MEM[addr + ChannelOffsetX()]); // Mem access size depends on format VDATA[63 : 32].b32 = ConvertFromFormat(MEM[addr + ChannelOffsetY()]); VDATA[95 : 64].b32 = ConvertFromFormat(MEM[addr + ChannelOffsetZ()])

#### **BUFFER_LOAD_FORMAT_XYZW**

**3**

Load 4-component formatted data from a buffer surface, convert the data to 32 bit integral or floating point format, then store the result into a vector register. The resource descriptor specifies the data format of the surface.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); VDATA[31 : 0].b32 = ConvertFromFormat(MEM[addr + ChannelOffsetX()]); // Mem access size depends on format VDATA[63 : 32].b32 = ConvertFromFormat(MEM[addr + ChannelOffsetY()]); VDATA[95 : 64].b32 = ConvertFromFormat(MEM[addr + ChannelOffsetZ()]); VDATA[127 : 96].b32 = ConvertFromFormat(MEM[addr + ChannelOffsetW()])

**BUFFER_STORE_FORMAT_X 4**

Convert 32 bits of data from vector input registers into 1-component formatted data and store the data into a buffer surface. The instruction specifies the data format of the surface, overriding the resource descriptor.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); MEM[addr + ChannelOffsetX()] = ConvertToFormat(VDATA[31 : 0].b32); // Mem access size depends on format

#### **BUFFER_STORE_FORMAT_XY**

**5**

Convert 64 bits of data from vector input registers into 2-component formatted data and store the data into a buffer surface. The instruction specifies the data format of the surface, overriding the resource descriptor.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); MEM[addr + ChannelOffsetX()] = ConvertToFormat(VDATA[31 : 0].b32); // Mem access size depends on format MEM[addr + ChannelOffsetY()] = ConvertToFormat(VDATA[63 : 32].b32)

451 of 553

12.13. MUBUF Instructions

"AMD Instinct MI300" Instruction Set Architecture

**6**



#### **BUFFER_STORE_FORMAT_XYZ**

Convert 96 bits of data from vector input registers into 3-component formatted data and store the data into a buffer surface. The instruction specifies the data format of the surface, overriding the resource descriptor.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); MEM[addr + ChannelOffsetX()] = ConvertToFormat(VDATA[31 : 0].b32); // Mem access size depends on format MEM[addr + ChannelOffsetY()] = ConvertToFormat(VDATA[63 : 32].b32); MEM[addr + ChannelOffsetZ()] = ConvertToFormat(VDATA[95 : 64].b32)

#### **BUFFER_STORE_FORMAT_XYZW**

**7**

Convert 128 bits of data from vector input registers into 4-component formatted data and store the data into a buffer surface. The instruction specifies the data format of the surface, overriding the resource descriptor.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); MEM[addr + ChannelOffsetX()] = ConvertToFormat(VDATA[31 : 0].b32); // Mem access size depends on format MEM[addr + ChannelOffsetY()] = ConvertToFormat(VDATA[63 : 32].b32); MEM[addr + ChannelOffsetZ()] = ConvertToFormat(VDATA[95 : 64].b32); MEM[addr + ChannelOffsetW()] = ConvertToFormat(VDATA[127 : 96].b32)

#### **BUFFER_LOAD_FORMAT_D16_X**

**8**

Load 1-component formatted data from a buffer surface, convert the data to packed 16 bit integral or floating point format, then store the result into the low 16 bits of a 32-bit vector register. The resource descriptor specifies the data format of the surface.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); VDATA[15 : 0].b16 = 16'B(ConvertFromFormat(MEM[addr + ChannelOffsetX()])); // Mem access size depends on format // VDATA[31:16].b16 is preserved.

#### **BUFFER_LOAD_FORMAT_D16_XY**

**9**

Load 2-component formatted data from a buffer surface, convert the data to packed 16 bit integral or floating point format, then store the result into a vector register. The resource descriptor specifies the data format of the surface.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); VDATA[15 : 0].b16 = 16'B(ConvertFromFormat(MEM[addr + ChannelOffsetX()]));

452 of 553

12.13. MUBUF Instructions

"AMD Instinct MI300" Instruction Set Architecture



// Mem access size depends on format VDATA[31 : 16].b16 = 16'B(ConvertFromFormat(MEM[addr + ChannelOffsetY()]))

#### **BUFFER_LOAD_FORMAT_D16_XYZ**

**10**

Load 3-component formatted data from a buffer surface, convert the data to packed 16 bit integral or floating point format, then store the result into a vector register. The resource descriptor specifies the data format of the surface.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); VDATA[15 : 0].b16 = 16'B(ConvertFromFormat(MEM[addr + ChannelOffsetX()])); // Mem access size depends on format VDATA[31 : 16].b16 = 16'B(ConvertFromFormat(MEM[addr + ChannelOffsetY()])); VDATA[47 : 32].b16 = 16'B(ConvertFromFormat(MEM[addr + ChannelOffsetZ()])); // VDATA[63:48].b16 is preserved.

#### **BUFFER_LOAD_FORMAT_D16_XYZW**

**11**

Load 4-component formatted data from a buffer surface, convert the data to packed 16 bit integral or floating point format, then store the result into a vector register. The resource descriptor specifies the data format of the surface.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); VDATA[15 : 0].b16 = 16'B(ConvertFromFormat(MEM[addr + ChannelOffsetX()])); // Mem access size depends on format VDATA[31 : 16].b16 = 16'B(ConvertFromFormat(MEM[addr + ChannelOffsetY()])); VDATA[47 : 32].b16 = 16'B(ConvertFromFormat(MEM[addr + ChannelOffsetZ()])); VDATA[63 : 48].b16 = 16'B(ConvertFromFormat(MEM[addr + ChannelOffsetW()]))

#### **BUFFER_STORE_FORMAT_D16_X**

**12**

Convert 16 bits of data from the low 16 bits of a 32-bit vector input register into 1-component formatted data and store the data into a buffer surface. The instruction specifies the data format of the surface, overriding the resource descriptor.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); MEM[addr + ChannelOffsetX()] = ConvertToFormat(32'B(VDATA[15 : 0].b16)); // Mem access size depends on format

**BUFFER_STORE_FORMAT_D16_XY**

**13**

453 of 553

12.13. MUBUF Instructions

"AMD Instinct MI300" Instruction Set Architecture



Convert 32 bits of data from vector input registers into 2-component formatted data and store the data into a buffer surface. The instruction specifies the data format of the surface, overriding the resource descriptor.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); MEM[addr + ChannelOffsetX()] = ConvertToFormat(32'B(VDATA[15 : 0].b16)); // Mem access size depends on format MEM[addr + ChannelOffsetY()] = ConvertToFormat(32'B(VDATA[31 : 16].b16))

#### **BUFFER_STORE_FORMAT_D16_XYZ**

**14**

Convert 48 bits of data from vector input registers into 3-component formatted data and store the data into a buffer surface. The instruction specifies the data format of the surface, overriding the resource descriptor.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); MEM[addr + ChannelOffsetX()] = ConvertToFormat(32'B(VDATA[15 : 0].b16)); // Mem access size depends on format MEM[addr + ChannelOffsetY()] = ConvertToFormat(32'B(VDATA[31 : 16].b16)); MEM[addr + ChannelOffsetZ()] = ConvertToFormat(32'B(VDATA[47 : 32].b16))

#### **BUFFER_STORE_FORMAT_D16_XYZW**

**15**

Convert 64 bits of data from vector input registers into 4-component formatted data and store the data into a buffer surface. The instruction specifies the data format of the surface, overriding the resource descriptor.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); MEM[addr + ChannelOffsetX()] = ConvertToFormat(32'B(VDATA[15 : 0].b16)); // Mem access size depends on format MEM[addr + ChannelOffsetY()] = ConvertToFormat(32'B(VDATA[31 : 16].b16)); MEM[addr + ChannelOffsetZ()] = ConvertToFormat(32'B(VDATA[47 : 32].b16)); MEM[addr + ChannelOffsetW()] = ConvertToFormat(32'B(VDATA[63 : 48].b16))

#### **BUFFER_LOAD_UBYTE**

**16**

Load 8 bits of unsigned data from a buffer surface, zero extend to 32 bits and store the result into a vector register.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); VDATA.u32 = 32'U({ 24'0U, MEM[addr].u8 })

#### **BUFFER_LOAD_SBYTE**

**17**

454 of 553

12.13. MUBUF Instructions

"AMD Instinct MI300" Instruction Set Architecture



Load 8 bits of signed data from a buffer surface, sign extend to 32 bits and store the result into a vector register.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); VDATA.i32 = 32'I(signext(MEM[addr].i8))

#### **BUFFER_LOAD_USHORT**

**18**

Load 16 bits of unsigned data from a buffer surface, zero extend to 32 bits and store the result into a vector register.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); VDATA.u32 = 32'U({ 16'0U, MEM[addr].u16 })

#### **BUFFER_LOAD_SSHORT**

**19**

Load 16 bits of signed data from a buffer surface, sign extend to 32 bits and store the result into a vector register.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); VDATA.i32 = 32'I(signext(MEM[addr].i16))

#### **BUFFER_LOAD_DWORD**

**20**

Load 32 bits of data from a buffer surface into a vector register.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); VDATA[31 : 0] = MEM[addr].b32

#### **BUFFER_LOAD_DWORDX2**

**21**

Load 64 bits of data from a buffer surface into a vector register.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); VDATA[31 : 0] = MEM[addr].b32; VDATA[63 : 32] = MEM[addr + 4U].b32

455 of 553

12.13. MUBUF Instructions

"AMD Instinct MI300" Instruction Set Architecture

**22**



#### **BUFFER_LOAD_DWORDX3**

Load 96 bits of data from a buffer surface into a vector register.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); VDATA[31 : 0] = MEM[addr].b32; VDATA[63 : 32] = MEM[addr + 4U].b32; VDATA[95 : 64] = MEM[addr + 8U].b32

#### **BUFFER_LOAD_DWORDX4**

**23**

Load 128 bits of data from a buffer surface into a vector register.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); VDATA[31 : 0] = MEM[addr].b32; VDATA[63 : 32] = MEM[addr + 4U].b32; VDATA[95 : 64] = MEM[addr + 8U].b32; VDATA[127 : 96] = MEM[addr + 12U].b32

**BUFFER_STORE_BYTE 24**

Store 8 bits of data from a vector register into a buffer surface.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); MEM[addr].b8 = VDATA[7 : 0]

**BUFFER_STORE_BYTE_D16_HI 25**

Store 8 bits of data from the high 16 bits of a 32-bit vector register into a buffer surface.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); MEM[addr].b8 = VDATA[23 : 16]

**BUFFER_STORE_SHORT 26**

Store 16 bits of data from a vector register into a buffer surface.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32);

456 of 553

12.13. MUBUF Instructions

"AMD Instinct MI300" Instruction Set Architecture

**27**



MEM[addr].b16 = VDATA[15 : 0]

#### **BUFFER_STORE_SHORT_D16_HI**

Store 16 bits of data from the high 16 bits of a 32-bit vector register into a buffer surface.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); MEM[addr].b16 = VDATA[31 : 16]

**BUFFER_STORE_DWORD 28**

Store 32 bits of data from vector input registers into a buffer surface.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); MEM[addr].b32 = VDATA[31 : 0]

**BUFFER_STORE_DWORDX2 29**

Store 64 bits of data from vector input registers into a buffer surface.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); MEM[addr].b32 = VDATA[31 : 0]; MEM[addr + 4U].b32 = VDATA[63 : 32]

**BUFFER_STORE_DWORDX3 30**

Store 96 bits of data from vector input registers into a buffer surface.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); MEM[addr].b32 = VDATA[31 : 0]; MEM[addr + 4U].b32 = VDATA[63 : 32]; MEM[addr + 8U].b32 = VDATA[95 : 64]

**BUFFER_STORE_DWORDX4 31**

Store 128 bits of data from vector input registers into a buffer surface.

457 of 553

12.13. MUBUF Instructions

"AMD Instinct MI300" Instruction Set Architecture



addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); MEM[addr].b32 = VDATA[31 : 0]; MEM[addr + 4U].b32 = VDATA[63 : 32]; MEM[addr + 8U].b32 = VDATA[95 : 64]; MEM[addr + 12U].b32 = VDATA[127 : 96]

#### **BUFFER_LOAD_UBYTE_D16**

**32**

Load 8 bits of unsigned data from a buffer surface, zero extend to 16 bits and store the result into the low 16 bits of a 32-bit vector register.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); VDATA[15 : 0].u16 = 16'U({ 8'0U, MEM[addr].u8 }); // VDATA[31:16] is preserved.

**BUFFER_LOAD_UBYTE_D16_HI 33**

Load 8 bits of unsigned data from a buffer surface, zero extend to 16 bits and store the result into the high 16 bits of a 32-bit vector register.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); VDATA[31 : 16].u16 = 16'U({ 8'0U, MEM[addr].u8 }); // VDATA[15:0] is preserved.

**BUFFER_LOAD_SBYTE_D16 34**

Load 8 bits of signed data from a buffer surface, sign extend to 16 bits and store the result into the low 16 bits of a 32-bit vector register.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); VDATA[15 : 0].i16 = 16'I(signext(MEM[addr].i8)); // VDATA[31:16] is preserved.

#### **BUFFER_LOAD_SBYTE_D16_HI**

**35**

Load 8 bits of signed data from a buffer surface, sign extend to 16 bits and store the result into the high 16 bits of a 32-bit vector register.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32);

458 of 553

12.13. MUBUF Instructions

"AMD Instinct MI300" Instruction Set Architecture



VDATA[31 : 16].i16 = 16'I(signext(MEM[addr].i8)); // VDATA[15:0] is preserved.

#### **BUFFER_LOAD_SHORT_D16**

**36**

Load 16 bits of unsigned data from a buffer surface and store the result into the low 16 bits of a 32-bit vector register.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); VDATA[15 : 0].b16 = MEM[addr].b16; // VDATA[31:16] is preserved.

**BUFFER_LOAD_SHORT_D16_HI**

**37**

Load 16 bits of unsigned data from a buffer surface and store the result into the high 16 bits of a 32-bit vector register.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); VDATA[31 : 16].b16 = MEM[addr].b16; // VDATA[15:0] is preserved.

#### **BUFFER_LOAD_FORMAT_D16_HI_X**

**38**

Load 1-component formatted data from a buffer surface, convert the data to packed 16 bit integral or floating point format, then store the result into the high 16 bits of a 32-bit vector register. The resource descriptor specifies the data format of the surface.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); VDATA[31 : 16].b16 = 16'B(ConvertFromFormat(MEM[addr + ChannelOffsetX()])); // Mem access size depends on format // VDATA[15:0].b16 is preserved.

#### **BUFFER_STORE_FORMAT_D16_HI_X**

**39**

Convert 16 bits of data from the high 16 bits of a 32-bit vector input register into 1-component formatted data and store the data into a buffer surface. The instruction specifies the data format of the surface, overriding the resource descriptor.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); MEM[addr + ChannelOffsetX()] = ConvertToFormat(32'B(VDATA[31 : 16].b16));

459 of 553

12.13. MUBUF Instructions

"AMD Instinct MI300" Instruction Set Architecture

**40**



// Mem access size depends on format

#### **BUFFER_WBL2**

Write back L2 cache. Returns ACK to shader.

#### **BUFFER_INV**

**41**

Invalidate CU and/or L2 cache depending on sc0 and sc1 bits. Returns ACK to shader.

#### **BUFFER_ATOMIC_SWAP**

**64**

Swap an unsigned 32-bit integer value in the data register with a location in a buffer surface. Store the original value from buffer surface into a vector register iff the SC0 bit is set.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); tmp = MEM[addr].b32; MEM[addr].b32 = DATA.b32; RETURN_DATA.b32 = tmp

#### **BUFFER_ATOMIC_CMPSWAP**

**65**

Compare two unsigned 32-bit integer values stored in the data comparison register and a location in a buffer surface. Modify the memory location with a value in the data source register iff the comparison is equal. Store the original value from buffer surface into a vector register iff the SC0 bit is set.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); tmp = MEM[addr].u32; src = DATA[31 : 0].u32; cmp = DATA[63 : 32].u32; MEM[addr].u32 = tmp == cmp ? src : tmp; RETURN_DATA.u32 = tmp

#### **BUFFER_ATOMIC_ADD**

**66**

Add two unsigned 32-bit integer values stored in the data register and a location in a buffer surface. Store the original value from buffer surface into a vector register iff the SC0 bit is set.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32);

460 of 553

12.13. MUBUF Instructions

"AMD Instinct MI300" Instruction Set Architecture

**67**



tmp = MEM[addr].u32; MEM[addr].u32 += DATA.u32; RETURN_DATA.u32 = tmp

#### **BUFFER_ATOMIC_SUB**

Subtract an unsigned 32-bit integer value stored in the data register from a value stored in a location in a buffer surface. Store the original value from buffer surface into a vector register iff the SC0 bit is set.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); tmp = MEM[addr].u32; MEM[addr].u32 -= DATA.u32; RETURN_DATA.u32 = tmp

#### **BUFFER_ATOMIC_SMIN**

**68**

Select the minimum of two signed 32-bit integer inputs, given two values stored in the data register and a location in a buffer surface. Update the buffer surface with the selected value. Store the original value from buffer surface into a vector register iff the SC0 bit is set.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); tmp = MEM[addr].i32; src = DATA.i32; MEM[addr].i32 = src < tmp ? src : tmp; RETURN_DATA.i32 = tmp

#### **BUFFER_ATOMIC_UMIN**

**69**

Select the minimum of two unsigned 32-bit integer inputs, given two values stored in the data register and a location in a buffer surface. Update the buffer surface with the selected value. Store the original value from buffer surface into a vector register iff the SC0 bit is set.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); tmp = MEM[addr].u32; src = DATA.u32; MEM[addr].u32 = src < tmp ? src : tmp; RETURN_DATA.u32 = tmp

#### **BUFFER_ATOMIC_SMAX**

**70**

Select the maximum of two signed 32-bit integer inputs, given two values stored in the data register and a

461 of 553

12.13. MUBUF Instructions

"AMD Instinct MI300" Instruction Set Architecture



location in a buffer surface. Update the buffer surface with the selected value. Store the original value from buffer surface into a vector register iff the SC0 bit is set.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); tmp = MEM[addr].i32; src = DATA.i32; MEM[addr].i32 = src >= tmp ? src : tmp; RETURN_DATA.i32 = tmp

#### **BUFFER_ATOMIC_UMAX**

**71**

Select the maximum of two unsigned 32-bit integer inputs, given two values stored in the data register and a location in a buffer surface. Update the buffer surface with the selected value. Store the original value from buffer surface into a vector register iff the SC0 bit is set.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); tmp = MEM[addr].u32; src = DATA.u32; MEM[addr].u32 = src >= tmp ? src : tmp; RETURN_DATA.u32 = tmp

#### **BUFFER_ATOMIC_AND**

**72**

Calculate bitwise AND given two unsigned 32-bit integer values stored in the data register and a location in a buffer surface. Store the original value from buffer surface into a vector register iff the SC0 bit is set.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); tmp = MEM[addr].b32; MEM[addr].b32 = (tmp & DATA.b32); RETURN_DATA.b32 = tmp

#### **BUFFER_ATOMIC_OR**

**73**

Calculate bitwise OR given two unsigned 32-bit integer values stored in the data register and a location in a buffer surface. Store the original value from buffer surface into a vector register iff the SC0 bit is set.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); tmp = MEM[addr].b32; MEM[addr].b32 = (tmp | DATA.b32); RETURN_DATA.b32 = tmp

462 of 553

12.13. MUBUF Instructions

"AMD Instinct MI300" Instruction Set Architecture

**74**



#### **BUFFER_ATOMIC_XOR**

Calculate bitwise XOR given two unsigned 32-bit integer values stored in the data register and a location in a buffer surface. Store the original value from buffer surface into a vector register iff the SC0 bit is set.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); tmp = MEM[addr].b32; MEM[addr].b32 = (tmp ^ DATA.b32); RETURN_DATA.b32 = tmp

#### **BUFFER_ATOMIC_INC**

**75**

Increment an unsigned 32-bit integer value from a location in a buffer surface with wraparound to 0 if the value exceeds a value in the data register. Store the original value from buffer surface into a vector register iff the SC0 bit is set.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); tmp = MEM[addr].u32; src = DATA.u32; MEM[addr].u32 = tmp >= src ? 0U : tmp + 1U; RETURN_DATA.u32 = tmp

#### **BUFFER_ATOMIC_DEC**

**76**

Decrement an unsigned 32-bit integer value from a location in a buffer surface with wraparound to a value in the data register if the decrement yields a negative value. Store the original value from buffer surface into a vector register iff the SC0 bit is set.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); tmp = MEM[addr].u32; src = DATA.u32; MEM[addr].u32 = ((tmp == 0U) || (tmp > src)) ? src : tmp - 1U; RETURN_DATA.u32 = tmp

#### **BUFFER_ATOMIC_ADD_F32**

**77**

Add a single-precision float value in the data register to a location in a buffer surface. Store the original value from buffer surface into a vector register iff the SC0 bit is set.

tmp = MEM[ADDR].f32; MEM[ADDR].f32 += DATA.f32; RETURN_DATA = tmp

463 of 553

12.13. MUBUF Instructions

"AMD Instinct MI300" Instruction Set Architecture

**78**



#### **Notes**

Floating-point addition handles NAN/INF/denorm.

#### **BUFFER_ATOMIC_PK_ADD_F16**

Add a packed 2-component half-precision float value in the data register to a location in a buffer surface. Store the original value from buffer surface into a vector register iff the SC0 bit is set.

tmp = MEM[ADDR]; src = DATA; dst[31 : 16].f16 = tmp[31 : 16].f16 + src[31 : 16].f16; dst[15 : 0].f16 = tmp[15 : 0].f16 + src[15 : 0].f16; MEM[ADDR] = dst.b32; RETURN_DATA = tmp

#### **Notes**

Floating-point addition handles NAN/INF/denorm.

**BUFFER_ATOMIC_ADD_F64**

**79**

Add a double-precision float value in the data register to a location in a buffer surface. Store the original value from buffer surface into a vector register iff the SC0 bit is set.

tmp = MEM[ADDR].f64; MEM[ADDR].f64 += DATA.f64; RETURN_DATA = tmp

#### **Notes**

Floating-point addition handles NAN/INF/denorm.

#### **BUFFER_ATOMIC_MIN_F64**

**80**

Select the minimum of two double-precision float inputs, given two values stored in the data register and a location in a buffer surface. Update the buffer surface with the selected value. Store the original value from buffer surface into a vector register iff the SC0 bit is set.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); tmp = MEM[addr].f64; src = DATA.f64; MEM[addr].f64 = src < tmp ? src : tmp;

464 of 553

12.13. MUBUF Instructions

"AMD Instinct MI300" Instruction Set Architecture

**81**



RETURN_DATA.f64 = tmp

#### **BUFFER_ATOMIC_MAX_F64**

Select the maximum of two double-precision float inputs, given two values stored in the data register and a location in a buffer surface. Update the buffer surface with the selected value. Store the original value from buffer surface into a vector register iff the SC0 bit is set.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); tmp = MEM[addr].f64; src = DATA.f64; MEM[addr].f64 = src > tmp ? src : tmp; RETURN_DATA.f64 = tmp

#### **BUFFER_ATOMIC_SWAP_X2**

**96**

Swap an unsigned 64-bit integer value in the data register with a location in a buffer surface. Store the original value from buffer surface into a vector register iff the SC0 bit is set.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); tmp = MEM[addr].b64; MEM[addr].b64 = DATA.b64; RETURN_DATA.b64 = tmp

#### **BUFFER_ATOMIC_CMPSWAP_X2**

**97**

Compare two unsigned 64-bit integer values stored in the data comparison register and a location in a buffer surface. Modify the memory location with a value in the data source register iff the comparison is equal. Store the original value from buffer surface into a vector register iff the SC0 bit is set.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); tmp = MEM[addr].u64; src = DATA[63 : 0].u64; cmp = DATA[127 : 64].u64; MEM[addr].u64 = tmp == cmp ? src : tmp; RETURN_DATA.u64 = tmp

#### **BUFFER_ATOMIC_ADD_X2**

**98**

Add two unsigned 64-bit integer values stored in the data register and a location in a buffer surface. Store the original value from buffer surface into a vector register iff the SC0 bit is set.

465 of 553

12.13. MUBUF Instructions

"AMD Instinct MI300" Instruction Set Architecture



addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); tmp = MEM[addr].u64; MEM[addr].u64 += DATA.u64; RETURN_DATA.u64 = tmp

#### **BUFFER_ATOMIC_SUB_X2**

**99**

Subtract an unsigned 64-bit integer value stored in the data register from a value stored in a location in a buffer surface. Store the original value from buffer surface into a vector register iff the SC0 bit is set.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); tmp = MEM[addr].u64; MEM[addr].u64 -= DATA.u64; RETURN_DATA.u64 = tmp

#### **BUFFER_ATOMIC_SMIN_X2**

**100**

Select the minimum of two signed 64-bit integer inputs, given two values stored in the data register and a location in a buffer surface. Update the buffer surface with the selected value. Store the original value from buffer surface into a vector register iff the SC0 bit is set.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); tmp = MEM[addr].i64; src = DATA.i64; MEM[addr].i64 = src < tmp ? src : tmp; RETURN_DATA.i64 = tmp

#### **BUFFER_ATOMIC_UMIN_X2**

**101**

Select the minimum of two unsigned 64-bit integer inputs, given two values stored in the data register and a location in a buffer surface. Update the buffer surface with the selected value. Store the original value from buffer surface into a vector register iff the SC0 bit is set.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); tmp = MEM[addr].u64; src = DATA.u64; MEM[addr].u64 = src < tmp ? src : tmp; RETURN_DATA.u64 = tmp

**BUFFER_ATOMIC_SMAX_X2**

**102**

466 of 553

12.13. MUBUF Instructions

"AMD Instinct MI300" Instruction Set Architecture



Select the maximum of two signed 64-bit integer inputs, given two values stored in the data register and a location in a buffer surface. Update the buffer surface with the selected value. Store the original value from buffer surface into a vector register iff the SC0 bit is set.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); tmp = MEM[addr].i64; src = DATA.i64; MEM[addr].i64 = src >= tmp ? src : tmp; RETURN_DATA.i64 = tmp

#### **BUFFER_ATOMIC_UMAX_X2**

**103**

Select the maximum of two unsigned 64-bit integer inputs, given two values stored in the data register and a location in a buffer surface. Update the buffer surface with the selected value. Store the original value from buffer surface into a vector register iff the SC0 bit is set.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); tmp = MEM[addr].u64; src = DATA.u64; MEM[addr].u64 = src >= tmp ? src : tmp; RETURN_DATA.u64 = tmp

#### **BUFFER_ATOMIC_AND_X2**

**104**

Calculate bitwise AND given two unsigned 64-bit integer values stored in the data register and a location in a buffer surface. Store the original value from buffer surface into a vector register iff the SC0 bit is set.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); tmp = MEM[addr].b64; MEM[addr].b64 = (tmp & DATA.b64); RETURN_DATA.b64 = tmp

#### **BUFFER_ATOMIC_OR_X2**

**105**

Calculate bitwise OR given two unsigned 64-bit integer values stored in the data register and a location in a buffer surface. Store the original value from buffer surface into a vector register iff the SC0 bit is set.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); tmp = MEM[addr].b64; MEM[addr].b64 = (tmp | DATA.b64); RETURN_DATA.b64 = tmp

467 of 553

12.13. MUBUF Instructions

"AMD Instinct MI300" Instruction Set Architecture

**BUFFER_ATOMIC_XOR_X2**

**106**



Calculate bitwise XOR given two unsigned 64-bit integer values stored in the data register and a location in a buffer surface. Store the original value from buffer surface into a vector register iff the SC0 bit is set.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); tmp = MEM[addr].b64; MEM[addr].b64 = (tmp ^ DATA.b64); RETURN_DATA.b64 = tmp

#### **BUFFER_ATOMIC_INC_X2**

**107**

Increment an unsigned 64-bit integer value from a location in a buffer surface with wraparound to 0 if the value exceeds a value in the data register. Store the original value from buffer surface into a vector register iff the SC0 bit is set.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); tmp = MEM[addr].u64; src = DATA.u64; MEM[addr].u64 = tmp >= src ? 0ULL : tmp + 1ULL; RETURN_DATA.u64 = tmp

#### **BUFFER_ATOMIC_DEC_X2**

**108**

Decrement an unsigned 64-bit integer value from a location in a buffer surface with wraparound to a value in the data register if the decrement yields a negative value. Store the original value from buffer surface into a vector register iff the SC0 bit is set.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); tmp = MEM[addr].u64; src = DATA.u64; MEM[addr].u64 = ((tmp == 0ULL) || (tmp > src)) ? src : tmp - 1ULL; RETURN_DATA.u64 = tmp

468 of 553

12.13. MUBUF Instructions

"AMD Instinct MI300" Instruction Set Architecture



## **12.14. MTBUF Instructions**

The bitfield map of the MTBUF format is:



where:

OFFSET  = Unsigned immediate byte offset. OFFEN   = Send offset either as VADDR or as zero. IDXEN   = Send index either as VADDR or as zero. LDS     = Data is transferred between LDS and Memory, not VGPRs. OP      = Instruction Opcode. DFMT    = Data format for typed buffer. NFMT    = Number format for typed buffer. VADDR   = VGPR address source. VDATA   = Vector GPR for read/write result.

SRSRC   = Scalar GPR that specifies resource constant. SOFFSET = Unsigned byte offset from an SGPR. SC      = Scope NT      = Non-Temporal ACC     = Return to ACC VGPRs

#### **TBUFFER_LOAD_FORMAT_X**

**0**

Load 1-component formatted data from a buffer surface, convert the data to 32 bit integral or floating point format, then store the result into a vector register. The instruction specifies the data format of the surface, overriding the resource descriptor.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); VDATA[31 : 0].b32 = ConvertFromFormat(MEM[addr + ChannelOffsetX()]); // Mem access size depends on format

#### **TBUFFER_LOAD_FORMAT_XY**

**1**

Load 2-component formatted data from a buffer surface, convert the data to 32 bit integral or floating point format, then store the result into a vector register. The instruction specifies the data format of the surface, overriding the resource descriptor.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); VDATA[31 : 0].b32 = ConvertFromFormat(MEM[addr + ChannelOffsetX()]); // Mem access size depends on format VDATA[63 : 32].b32 = ConvertFromFormat(MEM[addr + ChannelOffsetY()])

469 of 553

12.14. MTBUF Instructions

"AMD Instinct MI300" Instruction Set Architecture

**2**



#### **TBUFFER_LOAD_FORMAT_XYZ**

Load 3-component formatted data from a buffer surface, convert the data to 32 bit integral or floating point format, then store the result into a vector register. The instruction specifies the data format of the surface, overriding the resource descriptor.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); VDATA[31 : 0].b32 = ConvertFromFormat(MEM[addr + ChannelOffsetX()]); // Mem access size depends on format VDATA[63 : 32].b32 = ConvertFromFormat(MEM[addr + ChannelOffsetY()]); VDATA[95 : 64].b32 = ConvertFromFormat(MEM[addr + ChannelOffsetZ()])

#### **TBUFFER_LOAD_FORMAT_XYZW**

**3**

Load 4-component formatted data from a buffer surface, convert the data to 32 bit integral or floating point format, then store the result into a vector register. The instruction specifies the data format of the surface, overriding the resource descriptor.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); VDATA[31 : 0].b32 = ConvertFromFormat(MEM[addr + ChannelOffsetX()]); // Mem access size depends on format VDATA[63 : 32].b32 = ConvertFromFormat(MEM[addr + ChannelOffsetY()]); VDATA[95 : 64].b32 = ConvertFromFormat(MEM[addr + ChannelOffsetZ()]); VDATA[127 : 96].b32 = ConvertFromFormat(MEM[addr + ChannelOffsetW()])

#### **TBUFFER_STORE_FORMAT_X**

**4**

Convert 32 bits of data from vector input registers into 1-component formatted data and store the data into a buffer surface. The instruction specifies the data format of the surface, overriding the resource descriptor.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); MEM[addr + ChannelOffsetX()] = ConvertToFormat(VDATA[31 : 0].b32); // Mem access size depends on format

#### **TBUFFER_STORE_FORMAT_XY**

**5**

Convert 64 bits of data from vector input registers into 2-component formatted data and store the data into a buffer surface. The instruction specifies the data format of the surface, overriding the resource descriptor.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); MEM[addr + ChannelOffsetX()] = ConvertToFormat(VDATA[31 : 0].b32); // Mem access size depends on format

470 of 553

12.14. MTBUF Instructions

"AMD Instinct MI300" Instruction Set Architecture

**6**



MEM[addr + ChannelOffsetY()] = ConvertToFormat(VDATA[63 : 32].b32)

#### **TBUFFER_STORE_FORMAT_XYZ**

Convert 96 bits of data from vector input registers into 3-component formatted data and store the data into a buffer surface. The instruction specifies the data format of the surface, overriding the resource descriptor.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); MEM[addr + ChannelOffsetX()] = ConvertToFormat(VDATA[31 : 0].b32); // Mem access size depends on format MEM[addr + ChannelOffsetY()] = ConvertToFormat(VDATA[63 : 32].b32); MEM[addr + ChannelOffsetZ()] = ConvertToFormat(VDATA[95 : 64].b32)

#### **TBUFFER_STORE_FORMAT_XYZW**

**7**

Convert 128 bits of data from vector input registers into 4-component formatted data and store the data into a buffer surface. The instruction specifies the data format of the surface, overriding the resource descriptor.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); MEM[addr + ChannelOffsetX()] = ConvertToFormat(VDATA[31 : 0].b32); // Mem access size depends on format MEM[addr + ChannelOffsetY()] = ConvertToFormat(VDATA[63 : 32].b32); MEM[addr + ChannelOffsetZ()] = ConvertToFormat(VDATA[95 : 64].b32); MEM[addr + ChannelOffsetW()] = ConvertToFormat(VDATA[127 : 96].b32)

#### **TBUFFER_LOAD_FORMAT_D16_X**

**8**

Load 1-component formatted data from a buffer surface, convert the data to packed 16 bit integral or floating point format, then store the result into a vector register. The instruction specifies the data format of the surface, overriding the resource descriptor.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); VDATA[15 : 0].b16 = 16'B(ConvertFromFormat(MEM[addr + ChannelOffsetX()])); // Mem access size depends on format // VDATA[31:16].b16 is preserved.

#### **TBUFFER_LOAD_FORMAT_D16_XY**

**9**

Load 2-component formatted data from a buffer surface, convert the data to packed 16 bit integral or floating point format, then store the result into a vector register. The instruction specifies the data format of the surface, overriding the resource descriptor.

471 of 553

12.14. MTBUF Instructions

"AMD Instinct MI300" Instruction Set Architecture



addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); VDATA[15 : 0].b16 = 16'B(ConvertFromFormat(MEM[addr + ChannelOffsetX()])); // Mem access size depends on format VDATA[31 : 16].b16 = 16'B(ConvertFromFormat(MEM[addr + ChannelOffsetY()]))

#### **TBUFFER_LOAD_FORMAT_D16_XYZ**

**10**

Load 3-component formatted data from a buffer surface, convert the data to packed 16 bit integral or floating point format, then store the result into a vector register. The instruction specifies the data format of the surface, overriding the resource descriptor.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); VDATA[15 : 0].b16 = 16'B(ConvertFromFormat(MEM[addr + ChannelOffsetX()])); // Mem access size depends on format VDATA[31 : 16].b16 = 16'B(ConvertFromFormat(MEM[addr + ChannelOffsetY()])); VDATA[47 : 32].b16 = 16'B(ConvertFromFormat(MEM[addr + ChannelOffsetZ()])); // VDATA[63:48].b16 is preserved.

#### **TBUFFER_LOAD_FORMAT_D16_XYZW**

**11**

Load 4-component formatted data from a buffer surface, convert the data to packed 16 bit integral or floating point format, then store the result into a vector register. The instruction specifies the data format of the surface, overriding the resource descriptor.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); VDATA[15 : 0].b16 = 16'B(ConvertFromFormat(MEM[addr + ChannelOffsetX()])); // Mem access size depends on format VDATA[31 : 16].b16 = 16'B(ConvertFromFormat(MEM[addr + ChannelOffsetY()])); VDATA[47 : 32].b16 = 16'B(ConvertFromFormat(MEM[addr + ChannelOffsetZ()])); VDATA[63 : 48].b16 = 16'B(ConvertFromFormat(MEM[addr + ChannelOffsetW()]))

#### **TBUFFER_STORE_FORMAT_D16_X**

**12**

Convert 16 bits of data from vector input registers into 1-component formatted data and store the data into a buffer surface. The instruction specifies the data format of the surface, overriding the resource descriptor.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); MEM[addr + ChannelOffsetX()] = ConvertToFormat(32'B(VDATA[15 : 0].b16)); // Mem access size depends on format

472 of 553

12.14. MTBUF Instructions

"AMD Instinct MI300" Instruction Set Architecture

**13**



#### **TBUFFER_STORE_FORMAT_D16_XY**

Convert 32 bits of data from vector input registers into 2-component formatted data and store the data into a buffer surface. The instruction specifies the data format of the surface, overriding the resource descriptor.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); MEM[addr + ChannelOffsetX()] = ConvertToFormat(32'B(VDATA[15 : 0].b16)); // Mem access size depends on format MEM[addr + ChannelOffsetY()] = ConvertToFormat(32'B(VDATA[31 : 16].b16))

#### **TBUFFER_STORE_FORMAT_D16_XYZ**

**14**

Convert 48 bits of data from vector input registers into 3-component formatted data and store the data into a buffer surface. The instruction specifies the data format of the surface, overriding the resource descriptor.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); MEM[addr + ChannelOffsetX()] = ConvertToFormat(32'B(VDATA[15 : 0].b16)); // Mem access size depends on format MEM[addr + ChannelOffsetY()] = ConvertToFormat(32'B(VDATA[31 : 16].b16)); MEM[addr + ChannelOffsetZ()] = ConvertToFormat(32'B(VDATA[47 : 32].b16))

#### **TBUFFER_STORE_FORMAT_D16_XYZW**

**15**

Convert 64 bits of data from vector input registers into 4-component formatted data and store the data into a buffer surface. The instruction specifies the data format of the surface, overriding the resource descriptor.

addr = CalcBufferAddr(VADDR.b32, SRSRC.b32, SOFFSET.b32, OFFSET.b32); MEM[addr + ChannelOffsetX()] = ConvertToFormat(32'B(VDATA[15 : 0].b16)); // Mem access size depends on format MEM[addr + ChannelOffsetY()] = ConvertToFormat(32'B(VDATA[31 : 16].b16)); MEM[addr + ChannelOffsetZ()] = ConvertToFormat(32'B(VDATA[47 : 32].b16)); MEM[addr + ChannelOffsetW()] = ConvertToFormat(32'B(VDATA[63 : 48].b16))

473 of 553

12.14. MTBUF Instructions

"AMD Instinct MI300" Instruction Set Architecture



## **12.15. FLAT, Scratch and Global Instructions**

The bitfield map of the FLAT format is:



where:

OP     = Instruction Opcode. ADDR   = Source of flat address VGPR. DATA   = Source data. VDST   = Destination VGPR. NV     = Access to non-volatile memory. SADDR  = SGPR holding address or offset SEG    = Instruction type: Flat, Scratch, or Global LDS    = Data is transferred between LDS and Memory, not VGPRs. OFFSET = Immediate address byte-offset. SC      = Scope NT      = Non-Temporal

### **12.15.1. Flat Instructions**

Flat instructions look at the per-workitem address and determine for each work item if the target memory address is in global, private or scratch memory.

#### **FLAT_LOAD_UBYTE**

**16**

Load 8 bits of unsigned data from the flat aperture, zero extend to 32 bits and store the result into a vector register.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); VDATA.u32 = 32'U({ 24'0U, MEM[addr].u8 })

**FLAT_LOAD_SBYTE 17**

Load 8 bits of signed data from the flat aperture, sign extend to 32 bits and store the result into a vector register.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); VDATA.i32 = 32'I(signext(MEM[addr].i8))

474 of 553

12.15. FLAT, Scratch and Global Instructions

"AMD Instinct MI300" Instruction Set Architecture

**18**



#### **FLAT_LOAD_USHORT**

Load 16 bits of unsigned data from the flat aperture, zero extend to 32 bits and store the result into a vector register.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); VDATA.u32 = 32'U({ 16'0U, MEM[addr].u16 })

#### **FLAT_LOAD_SSHORT**

**19**

Load 16 bits of signed data from the flat aperture, sign extend to 32 bits and store the result into a vector register.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); VDATA.i32 = 32'I(signext(MEM[addr].i16))

**FLAT_LOAD_DWORD 20**

Load 32 bits of data from the flat aperture into a vector register.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); VDATA[31 : 0] = MEM[addr].b32

#### **FLAT_LOAD_DWORDX2**

**21**

Load 64 bits of data from the flat aperture into a vector register.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); VDATA[31 : 0] = MEM[addr].b32; VDATA[63 : 32] = MEM[addr + 4U].b32

#### **FLAT_LOAD_DWORDX3**

**22**

Load 96 bits of data from the flat aperture into a vector register.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); VDATA[31 : 0] = MEM[addr].b32; VDATA[63 : 32] = MEM[addr + 4U].b32;

475 of 553

12.15. FLAT, Scratch and Global Instructions

"AMD Instinct MI300" Instruction Set Architecture

**23**



VDATA[95 : 64] = MEM[addr + 8U].b32

#### **FLAT_LOAD_DWORDX4**

Load 128 bits of data from the flat aperture into a vector register.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); VDATA[31 : 0] = MEM[addr].b32; VDATA[63 : 32] = MEM[addr + 4U].b32; VDATA[95 : 64] = MEM[addr + 8U].b32; VDATA[127 : 96] = MEM[addr + 12U].b32

**FLAT_STORE_BYTE 24**

Store 8 bits of data from a vector register into the flat aperture.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); MEM[addr].b8 = VDATA[7 : 0]

#### **FLAT_STORE_BYTE_D16_HI**

**25**

Store 8 bits of data from the high 16 bits of a 32-bit vector register into the flat aperture.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); MEM[addr].b8 = VDATA[23 : 16]

#### **FLAT_STORE_SHORT**

**26**

Store 16 bits of data from a vector register into the flat aperture.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); MEM[addr].b16 = VDATA[15 : 0]

#### **FLAT_STORE_SHORT_D16_HI**

**27**

Store 16 bits of data from the high 16 bits of a 32-bit vector register into the flat aperture.

476 of 553

12.15. FLAT, Scratch and Global Instructions

"AMD Instinct MI300" Instruction Set Architecture

**28**



addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); MEM[addr].b16 = VDATA[31 : 16]

#### **FLAT_STORE_DWORD**

Store 32 bits of data from vector input registers into the flat aperture.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); MEM[addr].b32 = VDATA[31 : 0]

#### **FLAT_STORE_DWORDX2**

**29**

Store 64 bits of data from vector input registers into the flat aperture.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); MEM[addr].b32 = VDATA[31 : 0]; MEM[addr + 4U].b32 = VDATA[63 : 32]

**FLAT_STORE_DWORDX3 30**

Store 96 bits of data from vector input registers into the flat aperture.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); MEM[addr].b32 = VDATA[31 : 0]; MEM[addr + 4U].b32 = VDATA[63 : 32]; MEM[addr + 8U].b32 = VDATA[95 : 64]

**FLAT_STORE_DWORDX4 31**

Store 128 bits of data from vector input registers into the flat aperture.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); MEM[addr].b32 = VDATA[31 : 0]; MEM[addr + 4U].b32 = VDATA[63 : 32]; MEM[addr + 8U].b32 = VDATA[95 : 64]; MEM[addr + 12U].b32 = VDATA[127 : 96]

477 of 553

12.15. FLAT, Scratch and Global Instructions

"AMD Instinct MI300" Instruction Set Architecture

**32**



#### **FLAT_LOAD_UBYTE_D16**

Load 8 bits of unsigned data from the flat aperture, zero extend to 16 bits and store the result into the low 16 bits of a 32-bit vector register.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); VDATA[15 : 0].u16 = 16'U({ 8'0U, MEM[addr].u8 }); // VDATA[31:16] is preserved.

**FLAT_LOAD_UBYTE_D16_HI**

**33**

Load 8 bits of unsigned data from the flat aperture, zero extend to 16 bits and store the result into the high 16 bits of a 32-bit vector register.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); VDATA[31 : 16].u16 = 16'U({ 8'0U, MEM[addr].u8 }); // VDATA[15:0] is preserved.

**FLAT_LOAD_SBYTE_D16 34**

Load 8 bits of signed data from the flat aperture, sign extend to 16 bits and store the result into the low 16 bits of a 32-bit vector register.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); VDATA[15 : 0].i16 = 16'I(signext(MEM[addr].i8)); // VDATA[31:16] is preserved.

**FLAT_LOAD_SBYTE_D16_HI 35**

Load 8 bits of signed data from the flat aperture, sign extend to 16 bits and store the result into the high 16 bits of a 32-bit vector register.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); VDATA[31 : 16].i16 = 16'I(signext(MEM[addr].i8)); // VDATA[15:0] is preserved.

**FLAT_LOAD_SHORT_D16 36**

Load 16 bits of unsigned data from the flat aperture and store the result into the low 16 bits of a 32-bit vector

478 of 553

12.15. FLAT, Scratch and Global Instructions

"AMD Instinct MI300" Instruction Set Architecture



register.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); VDATA[15 : 0].b16 = MEM[addr].b16; // VDATA[31:16] is preserved.

#### **FLAT_LOAD_SHORT_D16_HI**

**37**

Load 16 bits of unsigned data from the flat aperture and store the result into the high 16 bits of a 32-bit vector register.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); VDATA[31 : 16].b16 = MEM[addr].b16; // VDATA[15:0] is preserved.

#### **FLAT_ATOMIC_SWAP**

**64**

Swap an unsigned 32-bit integer value in the data register with a location in the flat aperture. Store the original value from flat aperture into a vector register iff the SC0 bit is set.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); tmp = MEM[addr].b32; MEM[addr].b32 = DATA.b32; RETURN_DATA.b32 = tmp

#### **FLAT_ATOMIC_CMPSWAP**

**65**

Compare two unsigned 32-bit integer values stored in the data comparison register and a location in the flat aperture. Modify the memory location with a value in the data source register iff the comparison is equal. Store the original value from flat aperture into a vector register iff the SC0 bit is set.

NOTE: RETURN_DATA[1] is not modified.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); tmp = MEM[addr].u32; src = DATA[31 : 0].u32; cmp = DATA[63 : 32].u32; MEM[addr].u32 = tmp == cmp ? src : tmp; RETURN_DATA.u32 = tmp

479 of 553

12.15. FLAT, Scratch and Global Instructions

"AMD Instinct MI300" Instruction Set Architecture

**66**



#### **FLAT_ATOMIC_ADD**

Add two unsigned 32-bit integer values stored in the data register and a location in the flat aperture. Store the original value from flat aperture into a vector register iff the SC0 bit is set.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); tmp = MEM[addr].u32; MEM[addr].u32 += DATA.u32; RETURN_DATA.u32 = tmp

#### **FLAT_ATOMIC_SUB**

**67**

Subtract an unsigned 32-bit integer value stored in the data register from a value stored in a location in the flat aperture. Store the original value from flat aperture into a vector register iff the SC0 bit is set.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); tmp = MEM[addr].u32; MEM[addr].u32 -= DATA.u32; RETURN_DATA.u32 = tmp

#### **FLAT_ATOMIC_SMIN**

**68**

Select the minimum of two signed 32-bit integer inputs, given two values stored in the data register and a location in the flat aperture. Update the flat aperture with the selected value. Store the original value from flat aperture into a vector register iff the SC0 bit is set.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); tmp = MEM[addr].i32; src = DATA.i32; MEM[addr].i32 = src < tmp ? src : tmp; RETURN_DATA.i32 = tmp

#### **FLAT_ATOMIC_UMIN**

**69**

Select the minimum of two unsigned 32-bit integer inputs, given two values stored in the data register and a location in the flat aperture. Update the flat aperture with the selected value. Store the original value from flat aperture into a vector register iff the SC0 bit is set.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); tmp = MEM[addr].u32; src = DATA.u32; MEM[addr].u32 = src < tmp ? src : tmp;

480 of 553

12.15. FLAT, Scratch and Global Instructions

"AMD Instinct MI300" Instruction Set Architecture



RETURN_DATA.u32 = tmp

#### **FLAT_ATOMIC_SMAX**

**70**

Select the maximum of two signed 32-bit integer inputs, given two values stored in the data register and a location in the flat aperture. Update the flat aperture with the selected value. Store the original value from flat aperture into a vector register iff the SC0 bit is set.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); tmp = MEM[addr].i32; src = DATA.i32; MEM[addr].i32 = src >= tmp ? src : tmp; RETURN_DATA.i32 = tmp

#### **FLAT_ATOMIC_UMAX**

**71**

Select the maximum of two unsigned 32-bit integer inputs, given two values stored in the data register and a location in the flat aperture. Update the flat aperture with the selected value. Store the original value from flat aperture into a vector register iff the SC0 bit is set.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); tmp = MEM[addr].u32; src = DATA.u32; MEM[addr].u32 = src >= tmp ? src : tmp; RETURN_DATA.u32 = tmp

#### **FLAT_ATOMIC_AND**

**72**

Calculate bitwise AND given two unsigned 32-bit integer values stored in the data register and a location in the flat aperture. Store the original value from flat aperture into a vector register iff the SC0 bit is set.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); tmp = MEM[addr].b32; MEM[addr].b32 = (tmp & DATA.b32); RETURN_DATA.b32 = tmp

#### **FLAT_ATOMIC_OR**

**73**

Calculate bitwise OR given two unsigned 32-bit integer values stored in the data register and a location in the flat aperture. Store the original value from flat aperture into a vector register iff the SC0 bit is set.

481 of 553

12.15. FLAT, Scratch and Global Instructions

"AMD Instinct MI300" Instruction Set Architecture



addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); tmp = MEM[addr].b32; MEM[addr].b32 = (tmp | DATA.b32); RETURN_DATA.b32 = tmp

#### **FLAT_ATOMIC_XOR**

**74**

Calculate bitwise XOR given two unsigned 32-bit integer values stored in the data register and a location in the flat aperture. Store the original value from flat aperture into a vector register iff the SC0 bit is set.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); tmp = MEM[addr].b32; MEM[addr].b32 = (tmp ^ DATA.b32); RETURN_DATA.b32 = tmp

#### **FLAT_ATOMIC_INC**

**75**

Increment an unsigned 32-bit integer value from a location in the flat aperture with wraparound to 0 if the value exceeds a value in the data register. Store the original value from flat aperture into a vector register iff the SC0 bit is set.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); tmp = MEM[addr].u32; src = DATA.u32; MEM[addr].u32 = tmp >= src ? 0U : tmp + 1U; RETURN_DATA.u32 = tmp

**FLAT_ATOMIC_DEC 76**

Decrement an unsigned 32-bit integer value from a location in the flat aperture with wraparound to a value in the data register if the decrement yields a negative value. Store the original value from flat aperture into a vector register iff the SC0 bit is set.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); tmp = MEM[addr].u32; src = DATA.u32; MEM[addr].u32 = ((tmp == 0U) || (tmp > src)) ? src : tmp - 1U; RETURN_DATA.u32 = tmp

**FLAT_ATOMIC_ADD_F32**

**77**

482 of 553

12.15. FLAT, Scratch and Global Instructions

"AMD Instinct MI300" Instruction Set Architecture



Add a single-precision float value in the data register to a location in the flat aperture. Store the original value from flat aperture into a vector register iff the SC0 bit is set.

tmp = MEM[ADDR].f32; MEM[ADDR].f32 += DATA.f32; RETURN_DATA = tmp

#### **Notes**

Floating-point addition handles NAN/INF/denorm.

**FLAT_ATOMIC_PK_ADD_F16**

**78**

Add a packed 2-component half-precision float value in the data register to a location in the flat aperture. Store the original value from flat aperture into a vector register iff the SC0 bit is set.

tmp = MEM[ADDR]; src = DATA; dst[31 : 16].f16 = tmp[31 : 16].f16 + src[31 : 16].f16; dst[15 : 0].f16 = tmp[15 : 0].f16 + src[15 : 0].f16; MEM[ADDR] = dst.b32; RETURN_DATA = tmp

#### **Notes**

Floating-point addition handles NAN/INF/denorm.

**FLAT_ATOMIC_ADD_F64**

**79**

Add a double-precision float value in the data register to a location in the flat aperture. Store the original value from flat aperture into a vector register iff the SC0 bit is set.

tmp = MEM[ADDR].f64; MEM[ADDR].f64 += DATA.f64; RETURN_DATA = tmp

#### **Notes**

Floating-point addition handles NAN/INF/denorm.

**FLAT_ATOMIC_MIN_F64**

**80**

Select the minimum of two double-precision float inputs, given two values stored in the data register and a

483 of 553

12.15. FLAT, Scratch and Global Instructions

"AMD Instinct MI300" Instruction Set Architecture



location in the flat aperture. Update the flat aperture with the selected value. Store the original value from flat aperture into a vector register iff the SC0 bit is set.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); tmp = MEM[addr].f64; src = DATA.f64; MEM[addr].f64 = src < tmp ? src : tmp; RETURN_DATA.f64 = tmp

#### **FLAT_ATOMIC_MAX_F64**

**81**

Select the maximum of two double-precision float inputs, given two values stored in the data register and a location in the flat aperture. Update the flat aperture with the selected value. Store the original value from flat aperture into a vector register iff the SC0 bit is set.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); tmp = MEM[addr].f64; src = DATA.f64; MEM[addr].f64 = src > tmp ? src : tmp; RETURN_DATA.f64 = tmp

**FLAT_ATOMIC_PK_ADD_BF16**

**82**

Add a packed 2-component BF16 float value in the data register to a location in the flat aperture. Store the original value from flat aperture into a vector register iff the SC0 bit is set.

tmp = MEM[ADDR]; src = DATA; dst[31 : 16].bf16 = tmp[31 : 16].bf16 + src[31 : 16].bf16; dst[15 : 0].bf16 = tmp[15 : 0].bf16 + src[15 : 0].bf16; MEM[ADDR] = dst.b32; RETURN_DATA = tmp

#### **Notes**

Floating-point addition handles NAN/INF/denorm.

**FLAT_ATOMIC_SWAP_X2**

**96**

Swap an unsigned 64-bit integer value in the data register with a location in the flat aperture. Store the original value from flat aperture into a vector register iff the SC0 bit is set.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32);

484 of 553

12.15. FLAT, Scratch and Global Instructions

"AMD Instinct MI300" Instruction Set Architecture

**97**



tmp = MEM[addr].b64; MEM[addr].b64 = DATA.b64; RETURN_DATA.b64 = tmp

#### **FLAT_ATOMIC_CMPSWAP_X2**

Compare two unsigned 64-bit integer values stored in the data comparison register and a location in the flat aperture. Modify the memory location with a value in the data source register iff the comparison is equal. Store the original value from flat aperture into a vector register iff the SC0 bit is set.

NOTE: RETURN_DATA[2:3] is not modified.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); tmp = MEM[addr].u64; src = DATA[63 : 0].u64; cmp = DATA[127 : 64].u64; MEM[addr].u64 = tmp == cmp ? src : tmp; RETURN_DATA.u64 = tmp

#### **FLAT_ATOMIC_ADD_X2**

**98**

Add two unsigned 64-bit integer values stored in the data register and a location in the flat aperture. Store the original value from flat aperture into a vector register iff the SC0 bit is set.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); tmp = MEM[addr].u64; MEM[addr].u64 += DATA.u64; RETURN_DATA.u64 = tmp

#### **FLAT_ATOMIC_SUB_X2**

**99**

Subtract an unsigned 64-bit integer value stored in the data register from a value stored in a location in the flat aperture. Store the original value from flat aperture into a vector register iff the SC0 bit is set.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); tmp = MEM[addr].u64; MEM[addr].u64 -= DATA.u64; RETURN_DATA.u64 = tmp

**FLAT_ATOMIC_SMIN_X2**

**100**

485 of 553

12.15. FLAT, Scratch and Global Instructions

"AMD Instinct MI300" Instruction Set Architecture



Select the minimum of two signed 64-bit integer inputs, given two values stored in the data register and a location in the flat aperture. Update the flat aperture with the selected value. Store the original value from flat aperture into a vector register iff the SC0 bit is set.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); tmp = MEM[addr].i64; src = DATA.i64; MEM[addr].i64 = src < tmp ? src : tmp; RETURN_DATA.i64 = tmp

#### **FLAT_ATOMIC_UMIN_X2**

**101**

Select the minimum of two unsigned 64-bit integer inputs, given two values stored in the data register and a location in the flat aperture. Update the flat aperture with the selected value. Store the original value from flat aperture into a vector register iff the SC0 bit is set.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); tmp = MEM[addr].u64; src = DATA.u64; MEM[addr].u64 = src < tmp ? src : tmp; RETURN_DATA.u64 = tmp

#### **FLAT_ATOMIC_SMAX_X2**

**102**

Select the maximum of two signed 64-bit integer inputs, given two values stored in the data register and a location in the flat aperture. Update the flat aperture with the selected value. Store the original value from flat aperture into a vector register iff the SC0 bit is set.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); tmp = MEM[addr].i64; src = DATA.i64; MEM[addr].i64 = src >= tmp ? src : tmp; RETURN_DATA.i64 = tmp

**FLAT_ATOMIC_UMAX_X2**

**103**

Select the maximum of two unsigned 64-bit integer inputs, given two values stored in the data register and a location in the flat aperture. Update the flat aperture with the selected value. Store the original value from flat aperture into a vector register iff the SC0 bit is set.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); tmp = MEM[addr].u64; src = DATA.u64;

486 of 553

12.15. FLAT, Scratch and Global Instructions

"AMD Instinct MI300" Instruction Set Architecture

**104**



MEM[addr].u64 = src >= tmp ? src : tmp; RETURN_DATA.u64 = tmp

#### **FLAT_ATOMIC_AND_X2**

Calculate bitwise AND given two unsigned 64-bit integer values stored in the data register and a location in the flat aperture. Store the original value from flat aperture into a vector register iff the SC0 bit is set.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); tmp = MEM[addr].b64; MEM[addr].b64 = (tmp & DATA.b64); RETURN_DATA.b64 = tmp

#### **FLAT_ATOMIC_OR_X2**

**105**

Calculate bitwise OR given two unsigned 64-bit integer values stored in the data register and a location in the flat aperture. Store the original value from flat aperture into a vector register iff the SC0 bit is set.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); tmp = MEM[addr].b64; MEM[addr].b64 = (tmp | DATA.b64); RETURN_DATA.b64 = tmp

#### **FLAT_ATOMIC_XOR_X2**

**106**

Calculate bitwise XOR given two unsigned 64-bit integer values stored in the data register and a location in the flat aperture. Store the original value from flat aperture into a vector register iff the SC0 bit is set.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); tmp = MEM[addr].b64; MEM[addr].b64 = (tmp ^ DATA.b64); RETURN_DATA.b64 = tmp

#### **FLAT_ATOMIC_INC_X2**

**107**

Increment an unsigned 64-bit integer value from a location in the flat aperture with wraparound to 0 if the value exceeds a value in the data register. Store the original value from flat aperture into a vector register iff the SC0 bit is set.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32);

487 of 553

12.15. FLAT, Scratch and Global Instructions

"AMD Instinct MI300" Instruction Set Architecture

**108**



tmp = MEM[addr].u64; src = DATA.u64; MEM[addr].u64 = tmp >= src ? 0ULL : tmp + 1ULL; RETURN_DATA.u64 = tmp

#### **FLAT_ATOMIC_DEC_X2**

Decrement an unsigned 64-bit integer value from a location in the flat aperture with wraparound to a value in the data register if the decrement yields a negative value. Store the original value from flat aperture into a vector register iff the SC0 bit is set.

addr = CalcFlatAddr(ADDR.b32, OFFSET.b32); tmp = MEM[addr].u64; src = DATA.u64; MEM[addr].u64 = ((tmp == 0ULL) || (tmp > src)) ? src : tmp - 1ULL; RETURN_DATA.u64 = tmp

488 of 553

12.15. FLAT, Scratch and Global Instructions

"AMD Instinct MI300" Instruction Set Architecture



### **12.15.2. Scratch Instructions**

Scratch instructions are like Flat, but assume all workitem addresses fall in scratch (private) space.

#### **SCRATCH_LOAD_UBYTE**

**16**

Load 8 bits of unsigned data from the scratch aperture, zero extend to 32 bits and store the result into a vector register.

addr = CalcScratchAddr(ADDR.b32, SADDR.b32, OFFSET.b32); VDATA.u32 = 32'U({ 24'0U, MEM[addr].u8 })

#### **SCRATCH_LOAD_SBYTE**

**17**

Load 8 bits of signed data from the scratch aperture, sign extend to 32 bits and store the result into a vector register.

addr = CalcScratchAddr(ADDR.b32, SADDR.b32, OFFSET.b32); VDATA.i32 = 32'I(signext(MEM[addr].i8))

**SCRATCH_LOAD_USHORT 18**

Load 16 bits of unsigned data from the scratch aperture, zero extend to 32 bits and store the result into a vector register.

addr = CalcScratchAddr(ADDR.b32, SADDR.b32, OFFSET.b32); VDATA.u32 = 32'U({ 16'0U, MEM[addr].u16 })

**SCRATCH_LOAD_SSHORT 19**

Load 16 bits of signed data from the scratch aperture, sign extend to 32 bits and store the result into a vector register.

addr = CalcScratchAddr(ADDR.b32, SADDR.b32, OFFSET.b32); VDATA.i32 = 32'I(signext(MEM[addr].i16))

#### **SCRATCH_LOAD_DWORD**

**20**

Load 32 bits of data from the scratch aperture into a vector register.

489 of 553

12.15. FLAT, Scratch and Global Instructions

"AMD Instinct MI300" Instruction Set Architecture



addr = CalcScratchAddr(ADDR.b32, SADDR.b32, OFFSET.b32); VDATA[31 : 0] = MEM[addr].b32

#### **SCRATCH_LOAD_DWORDX2**

**21**

Load 64 bits of data from the scratch aperture into a vector register.

addr = CalcScratchAddr(ADDR.b32, SADDR.b32, OFFSET.b32); VDATA[31 : 0] = MEM[addr].b32; VDATA[63 : 32] = MEM[addr + 4U].b32

#### **SCRATCH_LOAD_DWORDX3**

**22**

Load 96 bits of data from the scratch aperture into a vector register.

addr = CalcScratchAddr(ADDR.b32, SADDR.b32, OFFSET.b32); VDATA[31 : 0] = MEM[addr].b32; VDATA[63 : 32] = MEM[addr + 4U].b32; VDATA[95 : 64] = MEM[addr + 8U].b32

**SCRATCH_LOAD_DWORDX4 23**

Load 128 bits of data from the scratch aperture into a vector register.

addr = CalcScratchAddr(ADDR.b32, SADDR.b32, OFFSET.b32); VDATA[31 : 0] = MEM[addr].b32; VDATA[63 : 32] = MEM[addr + 4U].b32; VDATA[95 : 64] = MEM[addr + 8U].b32; VDATA[127 : 96] = MEM[addr + 12U].b32

#### **SCRATCH_STORE_BYTE**

**24**

Store 8 bits of data from a vector register into the scratch aperture.

addr = CalcScratchAddr(ADDR.b32, SADDR.b32, OFFSET.b32); MEM[addr].b8 = VDATA[7 : 0]

490 of 553

12.15. FLAT, Scratch and Global Instructions

"AMD Instinct MI300" Instruction Set Architecture

**SCRATCH_STORE_BYTE_D16_HI**

**25**



Store 8 bits of data from the high 16 bits of a 32-bit vector register into the scratch aperture.

addr = CalcScratchAddr(ADDR.b32, SADDR.b32, OFFSET.b32); MEM[addr].b8 = VDATA[23 : 16]

**SCRATCH_STORE_SHORT 26**

Store 16 bits of data from a vector register into the scratch aperture.

addr = CalcScratchAddr(ADDR.b32, SADDR.b32, OFFSET.b32); MEM[addr].b16 = VDATA[15 : 0]

**SCRATCH_STORE_SHORT_D16_HI 27**

Store 16 bits of data from the high 16 bits of a 32-bit vector register into the scratch aperture.

addr = CalcScratchAddr(ADDR.b32, SADDR.b32, OFFSET.b32); MEM[addr].b16 = VDATA[31 : 16]

**SCRATCH_STORE_DWORD 28**

Store 32 bits of data from vector input registers into the scratch aperture.

addr = CalcScratchAddr(ADDR.b32, SADDR.b32, OFFSET.b32); MEM[addr].b32 = VDATA[31 : 0]

#### **SCRATCH_STORE_DWORDX2**

**29**

Store 64 bits of data from vector input registers into the scratch aperture.

addr = CalcScratchAddr(ADDR.b32, SADDR.b32, OFFSET.b32); MEM[addr].b32 = VDATA[31 : 0]; MEM[addr + 4U].b32 = VDATA[63 : 32]

491 of 553

12.15. FLAT, Scratch and Global Instructions

"AMD Instinct MI300" Instruction Set Architecture

**30**



#### **SCRATCH_STORE_DWORDX3**

Store 96 bits of data from vector input registers into the scratch aperture.

addr = CalcScratchAddr(ADDR.b32, SADDR.b32, OFFSET.b32); MEM[addr].b32 = VDATA[31 : 0]; MEM[addr + 4U].b32 = VDATA[63 : 32]; MEM[addr + 8U].b32 = VDATA[95 : 64]

**SCRATCH_STORE_DWORDX4 31**

Store 128 bits of data from vector input registers into the scratch aperture.

addr = CalcScratchAddr(ADDR.b32, SADDR.b32, OFFSET.b32); MEM[addr].b32 = VDATA[31 : 0]; MEM[addr + 4U].b32 = VDATA[63 : 32]; MEM[addr + 8U].b32 = VDATA[95 : 64]; MEM[addr + 12U].b32 = VDATA[127 : 96]

**SCRATCH_LOAD_UBYTE_D16 32**

Load 8 bits of unsigned data from the scratch aperture, zero extend to 16 bits and store the result into the low 16 bits of a 32-bit vector register.

addr = CalcScratchAddr(ADDR.b32, SADDR.b32, OFFSET.b32); VDATA[15 : 0].u16 = 16'U({ 8'0U, MEM[addr].u8 }); // VDATA[31:16] is preserved.

**SCRATCH_LOAD_UBYTE_D16_HI 33**

Load 8 bits of unsigned data from the scratch aperture, zero extend to 16 bits and store the result into the high 16 bits of a 32-bit vector register.

addr = CalcScratchAddr(ADDR.b32, SADDR.b32, OFFSET.b32); VDATA[31 : 16].u16 = 16'U({ 8'0U, MEM[addr].u8 }); // VDATA[15:0] is preserved.

**SCRATCH_LOAD_SBYTE_D16 34**

Load 8 bits of signed data from the scratch aperture, sign extend to 16 bits and store the result into the low 16

492 of 553

12.15. FLAT, Scratch and Global Instructions

"AMD Instinct MI300" Instruction Set Architecture



bits of a 32-bit vector register.

addr = CalcScratchAddr(ADDR.b32, SADDR.b32, OFFSET.b32); VDATA[15 : 0].i16 = 16'I(signext(MEM[addr].i8)); // VDATA[31:16] is preserved.

#### **SCRATCH_LOAD_SBYTE_D16_HI**

**35**

Load 8 bits of signed data from the scratch aperture, sign extend to 16 bits and store the result into the high 16 bits of a 32-bit vector register.

addr = CalcScratchAddr(ADDR.b32, SADDR.b32, OFFSET.b32); VDATA[31 : 16].i16 = 16'I(signext(MEM[addr].i8)); // VDATA[15:0] is preserved.

**SCRATCH_LOAD_SHORT_D16 36**

Load 16 bits of unsigned data from the scratch aperture and store the result into the low 16 bits of a 32-bit vector register.

addr = CalcScratchAddr(ADDR.b32, SADDR.b32, OFFSET.b32); VDATA[15 : 0].b16 = MEM[addr].b16; // VDATA[31:16] is preserved.

#### **SCRATCH_LOAD_SHORT_D16_HI**

**37**

Load 16 bits of unsigned data from the scratch aperture and store the result into the high 16 bits of a 32-bit vector register.

addr = CalcScratchAddr(ADDR.b32, SADDR.b32, OFFSET.b32); VDATA[31 : 16].b16 = MEM[addr].b16; // VDATA[15:0] is preserved.

#### **SCRATCH_LOAD_LDS_UBYTE**

**38**

Load 8 bits of untyped data from the scratch aperture, zero extend to 32 bits and store the result into a data share.

493 of 553

12.15. FLAT, Scratch and Global Instructions

"AMD Instinct MI300" Instruction Set Architecture



|**SCRATCH_LOAD_LDS_SBYTE**<br>**39**|
|---|
|Load 8 bits of untyped data from the scratch aperture, sign extend to 32 bits and store the result into a data<br>share.|
|**SCRATCH_LOAD_LDS_USHORT**<br>**40**|
|Load 16 bits of untyped data from the scratch aperture, zero extend to 32 bits and store the result into a data<br>share.|
|**SCRATCH_LOAD_LDS_SSHORT**<br>**41**|
|Load 16 bits of untyped data from the scratch aperture, sign extend to 32 bits and store the result into a data<br>share.|
|**SCRATCH_LOAD_LDS_DWORD**<br>**42**|
|Load 32 bits of untyped data from the scratch aperture and store the result into a data share.|



494 of 553

12.15. FLAT, Scratch and Global Instructions

"AMD Instinct MI300" Instruction Set Architecture



### **12.15.3. Global Instructions**

Global instructions are like Flat, but assume all workitem addresses fall in global memory space.

#### **GLOBAL_LOAD_UBYTE**

**16**

Load 8 bits of unsigned data from the global aperture, zero extend to 32 bits and store the result into a vector register.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); VDATA.u32 = 32'U({ 24'0U, MEM[addr].u8 })

#### **GLOBAL_LOAD_SBYTE**

**17**

Load 8 bits of signed data from the global aperture, sign extend to 32 bits and store the result into a vector register.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); VDATA.i32 = 32'I(signext(MEM[addr].i8))

**GLOBAL_LOAD_USHORT 18**

Load 16 bits of unsigned data from the global aperture, zero extend to 32 bits and store the result into a vector register.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); VDATA.u32 = 32'U({ 16'0U, MEM[addr].u16 })

**GLOBAL_LOAD_SSHORT 19**

Load 16 bits of signed data from the global aperture, sign extend to 32 bits and store the result into a vector register.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); VDATA.i32 = 32'I(signext(MEM[addr].i16))

#### **GLOBAL_LOAD_DWORD**

**20**

Load 32 bits of data from the global aperture into a vector register.

495 of 553

12.15. FLAT, Scratch and Global Instructions

"AMD Instinct MI300" Instruction Set Architecture

**21**



addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); VDATA[31 : 0] = MEM[addr].b32

#### **GLOBAL_LOAD_DWORDX2**

Load 64 bits of data from the global aperture into a vector register.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); VDATA[31 : 0] = MEM[addr].b32; VDATA[63 : 32] = MEM[addr + 4U].b32

#### **GLOBAL_LOAD_DWORDX3**

**22**

Load 96 bits of data from the global aperture into a vector register.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); VDATA[31 : 0] = MEM[addr].b32; VDATA[63 : 32] = MEM[addr + 4U].b32; VDATA[95 : 64] = MEM[addr + 8U].b32

**GLOBAL_LOAD_DWORDX4 23**

Load 128 bits of data from the global aperture into a vector register.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); VDATA[31 : 0] = MEM[addr].b32; VDATA[63 : 32] = MEM[addr + 4U].b32; VDATA[95 : 64] = MEM[addr + 8U].b32; VDATA[127 : 96] = MEM[addr + 12U].b32

#### **GLOBAL_STORE_BYTE**

**24**

Store 8 bits of data from a vector register into the global aperture.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); MEM[addr].b8 = VDATA[7 : 0]

496 of 553

12.15. FLAT, Scratch and Global Instructions

"AMD Instinct MI300" Instruction Set Architecture

**GLOBAL_STORE_BYTE_D16_HI**

**25**



Store 8 bits of data from the high 16 bits of a 32-bit vector register into the global aperture.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); MEM[addr].b8 = VDATA[23 : 16]

**GLOBAL_STORE_SHORT 26**

Store 16 bits of data from a vector register into the global aperture.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); MEM[addr].b16 = VDATA[15 : 0]

**GLOBAL_STORE_SHORT_D16_HI 27**

Store 16 bits of data from the high 16 bits of a 32-bit vector register into the global aperture.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); MEM[addr].b16 = VDATA[31 : 16]

**GLOBAL_STORE_DWORD 28**

Store 32 bits of data from vector input registers into the global aperture.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); MEM[addr].b32 = VDATA[31 : 0]

#### **GLOBAL_STORE_DWORDX2**

**29**

Store 64 bits of data from vector input registers into the global aperture.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); MEM[addr].b32 = VDATA[31 : 0]; MEM[addr + 4U].b32 = VDATA[63 : 32]

497 of 553

12.15. FLAT, Scratch and Global Instructions

"AMD Instinct MI300" Instruction Set Architecture

**30**



#### **GLOBAL_STORE_DWORDX3**

Store 96 bits of data from vector input registers into the global aperture.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); MEM[addr].b32 = VDATA[31 : 0]; MEM[addr + 4U].b32 = VDATA[63 : 32]; MEM[addr + 8U].b32 = VDATA[95 : 64]

**GLOBAL_STORE_DWORDX4 31**

Store 128 bits of data from vector input registers into the global aperture.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); MEM[addr].b32 = VDATA[31 : 0]; MEM[addr + 4U].b32 = VDATA[63 : 32]; MEM[addr + 8U].b32 = VDATA[95 : 64]; MEM[addr + 12U].b32 = VDATA[127 : 96]

**GLOBAL_LOAD_UBYTE_D16 32**

Load 8 bits of unsigned data from the global aperture, zero extend to 16 bits and store the result into the low 16 bits of a 32-bit vector register.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); VDATA[15 : 0].u16 = 16'U({ 8'0U, MEM[addr].u8 }); // VDATA[31:16] is preserved.

**GLOBAL_LOAD_UBYTE_D16_HI 33**

Load 8 bits of unsigned data from the global aperture, zero extend to 16 bits and store the result into the high 16 bits of a 32-bit vector register.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); VDATA[31 : 16].u16 = 16'U({ 8'0U, MEM[addr].u8 }); // VDATA[15:0] is preserved.

**GLOBAL_LOAD_SBYTE_D16 34**

Load 8 bits of signed data from the global aperture, sign extend to 16 bits and store the result into the low 16

498 of 553

12.15. FLAT, Scratch and Global Instructions

"AMD Instinct MI300" Instruction Set Architecture



bits of a 32-bit vector register.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); VDATA[15 : 0].i16 = 16'I(signext(MEM[addr].i8)); // VDATA[31:16] is preserved.

#### **GLOBAL_LOAD_SBYTE_D16_HI**

**35**

Load 8 bits of signed data from the global aperture, sign extend to 16 bits and store the result into the high 16 bits of a 32-bit vector register.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); VDATA[31 : 16].i16 = 16'I(signext(MEM[addr].i8)); // VDATA[15:0] is preserved.

**GLOBAL_LOAD_SHORT_D16 36**

Load 16 bits of unsigned data from the global aperture and store the result into the low 16 bits of a 32-bit vector register.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); VDATA[15 : 0].b16 = MEM[addr].b16; // VDATA[31:16] is preserved.

**GLOBAL_LOAD_SHORT_D16_HI 37**

Load 16 bits of unsigned data from the global aperture and store the result into the high 16 bits of a 32-bit vector register.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); VDATA[31 : 16].b16 = MEM[addr].b16; // VDATA[15:0] is preserved.

#### **GLOBAL_LOAD_LDS_UBYTE**

**38**

Load 8 bits of untyped data from the global aperture, zero extend to 32 bits and store the result into a data share.

499 of 553

12.15. FLAT, Scratch and Global Instructions

"AMD Instinct MI300" Instruction Set Architecture



|**GLOBAL_LOAD_LDS_SBYTE**|**39**|
|---|---|
|Load 8 bits of untyped data from the global aperture, sign extend to 32 bits and store the result into a data<br>share.||
|**GLOBAL_LOAD_LDS_USHORT**|**40**|
|Load 16 bits of untyped data from the global aperture, zero extend to 32 bits and store the result into a data<br>share.||
|**GLOBAL_LOAD_LDS_SSHORT**|**41**|
|Load 16 bits of untyped data from the global aperture, sign extend to 32 bits and store the result into a data<br>share.||
|**GLOBAL_LOAD_LDS_DWORD**|**42**|
|Load 32 bits of untyped data from the global aperture and store the result into a data share.||
|**GLOBAL_ATOMIC_SWAP**<br>Swap an unsigned 32-bit integer value in the data register with a location in the global aperture. Store the<br>original value from global aperture into a vector register iff the SC0 bit is set.|**64**|
|addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32);<br>tmp = MEM[addr].b32;<br>MEM[addr].b32 = DATA.b32;<br>RETURN_DATA.b32 = tmp<br>**GLOBAL_ATOMIC_CMPSWAP**|**65**|



Compare two unsigned 32-bit integer values stored in the data comparison register and a location in the global aperture. Modify the memory location with a value in the data source register iff the comparison is equal. Store the original value from global aperture into a vector register iff the SC0 bit is set.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); tmp = MEM[addr].u32; src = DATA[31 : 0].u32; cmp = DATA[63 : 32].u32; MEM[addr].u32 = tmp == cmp ? src : tmp;

500 of 553

12.15. FLAT, Scratch and Global Instructions

"AMD Instinct MI300" Instruction Set Architecture



RETURN_DATA.u32 = tmp

#### **GLOBAL_ATOMIC_ADD**

**66**

Add two unsigned 32-bit integer values stored in the data register and a location in the global aperture. Store the original value from global aperture into a vector register iff the SC0 bit is set.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); tmp = MEM[addr].u32; MEM[addr].u32 += DATA.u32; RETURN_DATA.u32 = tmp

#### **GLOBAL_ATOMIC_SUB**

**67**

Subtract an unsigned 32-bit integer value stored in the data register from a value stored in a location in the global aperture. Store the original value from global aperture into a vector register iff the SC0 bit is set.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); tmp = MEM[addr].u32; MEM[addr].u32 -= DATA.u32; RETURN_DATA.u32 = tmp

#### **GLOBAL_ATOMIC_SMIN**

**68**

Select the minimum of two signed 32-bit integer inputs, given two values stored in the data register and a location in the global aperture. Update the global aperture with the selected value. Store the original value from global aperture into a vector register iff the SC0 bit is set.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); tmp = MEM[addr].i32; src = DATA.i32; MEM[addr].i32 = src < tmp ? src : tmp; RETURN_DATA.i32 = tmp

#### **GLOBAL_ATOMIC_UMIN**

**69**

Select the minimum of two unsigned 32-bit integer inputs, given two values stored in the data register and a location in the global aperture. Update the global aperture with the selected value. Store the original value from global aperture into a vector register iff the SC0 bit is set.

501 of 553

12.15. FLAT, Scratch and Global Instructions

"AMD Instinct MI300" Instruction Set Architecture

**70**



addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); tmp = MEM[addr].u32; src = DATA.u32; MEM[addr].u32 = src < tmp ? src : tmp; RETURN_DATA.u32 = tmp

#### **GLOBAL_ATOMIC_SMAX**

Select the maximum of two signed 32-bit integer inputs, given two values stored in the data register and a location in the global aperture. Update the global aperture with the selected value. Store the original value from global aperture into a vector register iff the SC0 bit is set.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); tmp = MEM[addr].i32; src = DATA.i32; MEM[addr].i32 = src >= tmp ? src : tmp; RETURN_DATA.i32 = tmp

#### **GLOBAL_ATOMIC_UMAX**

**71**

Select the maximum of two unsigned 32-bit integer inputs, given two values stored in the data register and a location in the global aperture. Update the global aperture with the selected value. Store the original value from global aperture into a vector register iff the SC0 bit is set.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); tmp = MEM[addr].u32; src = DATA.u32; MEM[addr].u32 = src >= tmp ? src : tmp; RETURN_DATA.u32 = tmp

#### **GLOBAL_ATOMIC_AND**

**72**

Calculate bitwise AND given two unsigned 32-bit integer values stored in the data register and a location in the global aperture. Store the original value from global aperture into a vector register iff the SC0 bit is set.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); tmp = MEM[addr].b32; MEM[addr].b32 = (tmp & DATA.b32); RETURN_DATA.b32 = tmp

502 of 553

12.15. FLAT, Scratch and Global Instructions

"AMD Instinct MI300" Instruction Set Architecture

**73**



#### **GLOBAL_ATOMIC_OR**

Calculate bitwise OR given two unsigned 32-bit integer values stored in the data register and a location in the global aperture. Store the original value from global aperture into a vector register iff the SC0 bit is set.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); tmp = MEM[addr].b32; MEM[addr].b32 = (tmp | DATA.b32); RETURN_DATA.b32 = tmp

#### **GLOBAL_ATOMIC_XOR**

**74**

Calculate bitwise XOR given two unsigned 32-bit integer values stored in the data register and a location in the global aperture. Store the original value from global aperture into a vector register iff the SC0 bit is set.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); tmp = MEM[addr].b32; MEM[addr].b32 = (tmp ^ DATA.b32); RETURN_DATA.b32 = tmp

#### **GLOBAL_ATOMIC_INC**

**75**

Increment an unsigned 32-bit integer value from a location in the global aperture with wraparound to 0 if the value exceeds a value in the data register. Store the original value from global aperture into a vector register iff the SC0 bit is set.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); tmp = MEM[addr].u32; src = DATA.u32; MEM[addr].u32 = tmp >= src ? 0U : tmp + 1U; RETURN_DATA.u32 = tmp

#### **GLOBAL_ATOMIC_DEC**

**76**

Decrement an unsigned 32-bit integer value from a location in the global aperture with wraparound to a value in the data register if the decrement yields a negative value. Store the original value from global aperture into a vector register iff the SC0 bit is set.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); tmp = MEM[addr].u32; src = DATA.u32; MEM[addr].u32 = ((tmp == 0U) || (tmp > src)) ? src : tmp - 1U;

503 of 553

12.15. FLAT, Scratch and Global Instructions

"AMD Instinct MI300" Instruction Set Architecture



RETURN_DATA.u32 = tmp

#### **GLOBAL_ATOMIC_ADD_F32**

**77**

Add a single-precision float value in the data register to a location in the global aperture. Store the original value from global aperture into a vector register iff the SC0 bit is set.

tmp = MEM[ADDR].f32; MEM[ADDR].f32 += DATA.f32; RETURN_DATA = tmp

#### **Notes**

Floating-point addition handles NAN/INF/denorm.

**GLOBAL_ATOMIC_PK_ADD_F16**

**78**

Add a packed 2-component half-precision float value in the data register to a location in the global aperture. Store the original value from global aperture into a vector register iff the SC0 bit is set.

tmp = MEM[ADDR]; src = DATA; dst[31 : 16].f16 = tmp[31 : 16].f16 + src[31 : 16].f16; dst[15 : 0].f16 = tmp[15 : 0].f16 + src[15 : 0].f16; MEM[ADDR] = dst.b32; RETURN_DATA = tmp

#### **Notes**

Floating-point addition handles NAN/INF/denorm.

**GLOBAL_ATOMIC_ADD_F64**

**79**

Add a double-precision float value in the data register to a location in the global aperture. Store the original value from global aperture into a vector register iff the SC0 bit is set.

tmp = MEM[ADDR].f64; MEM[ADDR].f64 += DATA.f64; RETURN_DATA = tmp

#### **Notes**

Floating-point addition handles NAN/INF/denorm.

504 of 553

12.15. FLAT, Scratch and Global Instructions

"AMD Instinct MI300" Instruction Set Architecture



#### **GLOBAL_ATOMIC_MIN_F64**

**80**

Select the minimum of two double-precision float inputs, given two values stored in the data register and a location in the global aperture. Update the global aperture with the selected value. Store the original value from global aperture into a vector register iff the SC0 bit is set.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); tmp = MEM[addr].f64; src = DATA.f64; MEM[addr].f64 = src < tmp ? src : tmp; RETURN_DATA.f64 = tmp

#### **GLOBAL_ATOMIC_MAX_F64**

**81**

Select the maximum of two double-precision float inputs, given two values stored in the data register and a location in the global aperture. Update the global aperture with the selected value. Store the original value from global aperture into a vector register iff the SC0 bit is set.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); tmp = MEM[addr].f64; src = DATA.f64; MEM[addr].f64 = src > tmp ? src : tmp; RETURN_DATA.f64 = tmp

#### **GLOBAL_ATOMIC_PK_ADD_BF16**

**82**

Add a packed 2-component BF16 float value in the data register to a location in the global aperture. Store the original value from global aperture into a vector register iff the SC0 bit is set.

tmp = MEM[ADDR]; src = DATA; dst[31 : 16].bf16 = tmp[31 : 16].bf16 + src[31 : 16].bf16; dst[15 : 0].bf16 = tmp[15 : 0].bf16 + src[15 : 0].bf16; MEM[ADDR] = dst.b32; RETURN_DATA = tmp

#### **Notes**

Floating-point addition handles NAN/INF/denorm.

**GLOBAL_ATOMIC_SWAP_X2**

**96**

505 of 553

12.15. FLAT, Scratch and Global Instructions

"AMD Instinct MI300" Instruction Set Architecture



Swap an unsigned 64-bit integer value in the data register with a location in the global aperture. Store the original value from global aperture into a vector register iff the SC0 bit is set.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); tmp = MEM[addr].b64; MEM[addr].b64 = DATA.b64; RETURN_DATA.b64 = tmp

#### **GLOBAL_ATOMIC_CMPSWAP_X2**

**97**

Compare two unsigned 64-bit integer values stored in the data comparison register and a location in the global aperture. Modify the memory location with a value in the data source register iff the comparison is equal. Store the original value from global aperture into a vector register iff the SC0 bit is set.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); tmp = MEM[addr].u64; src = DATA[63 : 0].u64; cmp = DATA[127 : 64].u64; MEM[addr].u64 = tmp == cmp ? src : tmp; RETURN_DATA.u64 = tmp

**GLOBAL_ATOMIC_ADD_X2 98**

Add two unsigned 64-bit integer values stored in the data register and a location in the global aperture. Store the original value from global aperture into a vector register iff the SC0 bit is set.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); tmp = MEM[addr].u64; MEM[addr].u64 += DATA.u64; RETURN_DATA.u64 = tmp

#### **GLOBAL_ATOMIC_SUB_X2**

**99**

Subtract an unsigned 64-bit integer value stored in the data register from a value stored in a location in the global aperture. Store the original value from global aperture into a vector register iff the SC0 bit is set.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); tmp = MEM[addr].u64; MEM[addr].u64 -= DATA.u64; RETURN_DATA.u64 = tmp

506 of 553

12.15. FLAT, Scratch and Global Instructions

"AMD Instinct MI300" Instruction Set Architecture

**100**



#### **GLOBAL_ATOMIC_SMIN_X2**

Select the minimum of two signed 64-bit integer inputs, given two values stored in the data register and a location in the global aperture. Update the global aperture with the selected value. Store the original value from global aperture into a vector register iff the SC0 bit is set.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); tmp = MEM[addr].i64; src = DATA.i64; MEM[addr].i64 = src < tmp ? src : tmp; RETURN_DATA.i64 = tmp

#### **GLOBAL_ATOMIC_UMIN_X2**

**101**

Select the minimum of two unsigned 64-bit integer inputs, given two values stored in the data register and a location in the global aperture. Update the global aperture with the selected value. Store the original value from global aperture into a vector register iff the SC0 bit is set.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); tmp = MEM[addr].u64; src = DATA.u64; MEM[addr].u64 = src < tmp ? src : tmp; RETURN_DATA.u64 = tmp

#### **GLOBAL_ATOMIC_SMAX_X2**

**102**

Select the maximum of two signed 64-bit integer inputs, given two values stored in the data register and a location in the global aperture. Update the global aperture with the selected value. Store the original value from global aperture into a vector register iff the SC0 bit is set.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); tmp = MEM[addr].i64; src = DATA.i64; MEM[addr].i64 = src >= tmp ? src : tmp; RETURN_DATA.i64 = tmp

#### **GLOBAL_ATOMIC_UMAX_X2**

**103**

Select the maximum of two unsigned 64-bit integer inputs, given two values stored in the data register and a location in the global aperture. Update the global aperture with the selected value. Store the original value from global aperture into a vector register iff the SC0 bit is set.

507 of 553

12.15. FLAT, Scratch and Global Instructions

"AMD Instinct MI300" Instruction Set Architecture



addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); tmp = MEM[addr].u64; src = DATA.u64; MEM[addr].u64 = src >= tmp ? src : tmp; RETURN_DATA.u64 = tmp

#### **GLOBAL_ATOMIC_AND_X2**

**104**

Calculate bitwise AND given two unsigned 64-bit integer values stored in the data register and a location in the global aperture. Store the original value from global aperture into a vector register iff the SC0 bit is set.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); tmp = MEM[addr].b64; MEM[addr].b64 = (tmp & DATA.b64); RETURN_DATA.b64 = tmp

**GLOBAL_ATOMIC_OR_X2**

**105**

Calculate bitwise OR given two unsigned 64-bit integer values stored in the data register and a location in the global aperture. Store the original value from global aperture into a vector register iff the SC0 bit is set.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); tmp = MEM[addr].b64; MEM[addr].b64 = (tmp | DATA.b64); RETURN_DATA.b64 = tmp

**GLOBAL_ATOMIC_XOR_X2 106**

Calculate bitwise XOR given two unsigned 64-bit integer values stored in the data register and a location in the global aperture. Store the original value from global aperture into a vector register iff the SC0 bit is set.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); tmp = MEM[addr].b64; MEM[addr].b64 = (tmp ^ DATA.b64); RETURN_DATA.b64 = tmp

#### **GLOBAL_ATOMIC_INC_X2**

**107**

Increment an unsigned 64-bit integer value from a location in the global aperture with wraparound to 0 if the value exceeds a value in the data register. Store the original value from global aperture into a vector register iff

508 of 553

12.15. FLAT, Scratch and Global Instructions

"AMD Instinct MI300" Instruction Set Architecture



the SC0 bit is set.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); tmp = MEM[addr].u64; src = DATA.u64; MEM[addr].u64 = tmp >= src ? 0ULL : tmp + 1ULL; RETURN_DATA.u64 = tmp

**GLOBAL_ATOMIC_DEC_X2 108**

Decrement an unsigned 64-bit integer value from a location in the global aperture with wraparound to a value in the data register if the decrement yields a negative value. Store the original value from global aperture into a vector register iff the SC0 bit is set.

addr = CalcGlobalAddr(ADDR.b32, SADDR.b32, OFFSET.b32); tmp = MEM[addr].u64; src = DATA.u64; MEM[addr].u64 = ((tmp == 0ULL) || (tmp > src)) ? src : tmp - 1ULL; RETURN_DATA.u64 = tmp

509 of 553

12.15. FLAT, Scratch and Global Instructions

"AMD Instinct MI300" Instruction Set Architecture



## **12.16. Instruction Limitations**

### **12.16.1. DPP**

The following instructions cannot use DPP:

- V_MADMK_F32

- V_MADAK_F32

- V_MADMK_F16

- V_MADAK_F16

- V_READFIRSTLANE_B32

- V_CVT_I32_F64

- V_CVT_F64_I32

- V_CVT_F32_F64

- V_CVT_F64_F32

- V_CVT_U32_F64

- V_CVT_F64_U32

- V_TRUNC_F64

- V_CEIL_F64

- V_RNDNE_F64

- V_FLOOR_F64

- V_RCP_F64

- V_RSQ_F64

- V_SQRT_F64

- V_FREXP_EXP_I32_F64

- V_FREXP_MANT_F64

- V_FRACT_F64

- V_CLREXCP

- V_SWAP_B32

- V_CMP_CLASS_F64

- V_CMPX_CLASS_F64

- V_CMP_*_F64

- V_CMPX_*_F64

- V_CMP_*_I64

- V_CMP_*_U64

- V_CMPX_*_I64

- V_CMPX_*_U64

### **12.16.2. SDWA**

The following instructions cannot use SDWA:

- V_MAC_F32

- V_MADMK_F32

510 of 553

12.16. Instruction Limitations

"AMD Instinct MI300" Instruction Set Architecture



- V_MADAK_F32

- V_MAC_F16

- V_MADMK_F16

- V_MADAK_F16

- V_FMAC_F32

- V_READFIRSTLANE_B32

- V_CLREXCP

- V_SWAP_B32

511 of 553

12.16. Instruction Limitations
