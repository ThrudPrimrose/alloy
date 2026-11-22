---
name: docs-md-gfx90a-15-chapter-12-instructions
description: "AMD CDNA2 ISA: Chapter 12. Instructions (vendor documentation for AMD gfx90a (CDNA2))."
when: "when you need AMD CDNA2 ISA: Chapter 12. Instructions while writing a AMD gfx90a (CDNA2) kernel."
---

"AMD Instinct MI200" Instruction Set Architecture



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



Instructions in this format may use a 32-bit literal constant which occurs immediately after the

12.1. SOP2 Instructions

91 of 267

"AMD Instinct MI200" Instruction Set Architecture



instruction.

|**Opcode**|**Name**|**Description**|
|---|---|---|
|0|S_ADD_U32|D.u = S0.u + S1.u;<br>SCC = (S0.u + S1.u >= 0x100000000ULL ? 1 : 0). // unsigned<br>overflow/carry-out, S_ADDC_U32|
|1|S_SUB_U32|D.u = S0.u - S1.u;<br>SCC = (S1.u > S0.u ? 1 : 0). // unsigned overflow or carry-out for<br>S_SUBB_U32.|
|2|S_ADD_I32|D.i = S0.i + S1.i;<br>SCC = (S0.u[31] == S1.u[31] && S0.u[31] != D.u[31]). // signed<br>overflow.<br>This opcode is not suitable for use with S_ADDC_U32 for implementing<br>64-bit operations.|
|3|S_SUB_I32|D.i = S0.i - S1.i;<br>SCC = (S0.u[31] != S1.u[31] && S0.u[31] != D.u[31]). // signed<br>overflow.<br>This opcode is not suitable for use with S_SUBB_U32 for implementing<br>64-bit operations.|
|4|S_ADDC_U32|D.u = S0.u + S1.u + SCC;<br>SCC = (S0.u + S1.u + SCC >= 0x100000000ULL ? 1 : 0). // unsigned<br>overflow.|
|5|S_SUBB_U32|D.u = S0.u - S1.u - SCC;<br>SCC = (S1.u + SCC > S0.u ? 1 : 0). // unsigned overflow.|
|6|S_MIN_I32|D.i = (S0.i < S1.i) ? S0.i : S1.i;<br>SCC = (S0.i < S1.i).|
|7|S_MIN_U32|D.u = (S0.u < S1.u) ? S0.u : S1.u;<br>SCC = (S0.u < S1.u).|
|8|S_MAX_I32|D.i = (S0.i > S1.i) ? S0.i : S1.i;<br>SCC = (S0.i > S1.i).|
|9|S_MAX_U32|D.u = (S0.u > S1.u) ? S0.u : S1.u;<br>SCC = (S0.u > S1.u).|
|10|S_CSELECT_B32|D.u = SCC ? S0.u : S1.u.<br>Conditional select.|
|11|S_CSELECT_B64|D.u64 = SCC ? S0.u64 : S1.u64.<br>Conditional select.|
|12|S_AND_B32|D = S0 & S1;<br>SCC = (D != 0).|
|13|S_AND_B64|D = S0 & S1;<br>SCC = (D != 0).|
|14|S_OR_B32|D = S0 | S1;<br>SCC = (D != 0).|
|15|S_OR_B64|D = S0 | S1;<br>SCC = (D != 0).|



12.1. SOP2 Instructions

92 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|16|S_XOR_B32|D = S0 ^ S1;<br>SCC = (D != 0).|
|17|S_XOR_B64|D = S0 ^ S1;<br>SCC = (D != 0).|
|18|S_ANDN2_B32|D = S0 & ~S1;<br>SCC = (D != 0).|
|19|S_ANDN2_B64|D = S0 & ~S1;<br>SCC = (D != 0).|
|20|S_ORN2_B32|D = S0 | ~S1;<br>SCC = (D != 0).|
|21|S_ORN2_B64|D = S0 | ~S1;<br>SCC = (D != 0).|
|22|S_NAND_B32|D = ~(S0 & S1);<br>SCC = (D != 0).|
|23|S_NAND_B64|D = ~(S0 & S1);<br>SCC = (D != 0).|
|24|S_NOR_B32|D = ~(S0 | S1);<br>SCC = (D != 0).|
|25|S_NOR_B64|D = ~(S0 | S1);<br>SCC = (D != 0).|
|26|S_XNOR_B32|D = ~(S0 ^ S1);<br>SCC = (D != 0).|
|27|S_XNOR_B64|D = ~(S0 ^ S1);<br>SCC = (D != 0).|
|28|S_LSHL_B32|D.u = S0.u << S1.u[4:0];<br>SCC = (D.u != 0).|
|29|S_LSHL_B64|D.u64 = S0.u64 << S1.u[5:0];<br>SCC = (D.u64 != 0).|
|30|S_LSHR_B32|D.u = S0.u >> S1.u[4:0];<br>SCC = (D.u != 0).|
|31|S_LSHR_B64|D.u64 = S0.u64 >> S1.u[5:0];<br>SCC = (D.u64 != 0).|
|32|S_ASHR_I32|D.i = signext(S0.i) >> S1.u[4:0];<br>SCC = (D.i != 0).|
|33|S_ASHR_I64|D.i64 = signext(S0.i64) >> S1.u[5:0];<br>SCC = (D.i64 != 0).|
|34|S_BFM_B32|D.u = ((1 << S0.u[4:0]) - 1) << S1.u[4:0].<br>Bitfield mask.|
|35|S_BFM_B64|D.u64 = ((1ULL << S0.u[5:0]) - 1) << S1.u[5:0].<br>Bitfield mask.|
|36|S_MUL_I32|D.i = S0.i * S1.i.|



12.1. SOP2 Instructions

93 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|37|S_BFE_U32|D.u = (S0.u >> S1.u[4:0]) & ((1 << S1.u[22:16]) - 1);<br>SCC = (D.u != 0).<br>Bit field extract. S0 is Data, S1[4:0] is field offset, S1[22:16] is<br>field width.|
|38|S_BFE_I32|D.i = signext((S0.i >> S1.u[4:0]) & ((1 << S1.u[22:16]) - 1));<br>SCC = (D.i != 0).<br>Bit field extract. S0 is Data, S1[4:0] is field offset, S1[22:16] is<br>field width.|
|39|S_BFE_U64|D.u64 = (S0.u64 >> S1.u[5:0]) & ((1 << S1.u[22:16]) - 1);<br>SCC = (D.u64 != 0).<br>Bit field extract. S0 is Data, S1[5:0] is field offset, S1[22:16] is<br>field width.|
|40|S_BFE_I64|D.i64 = signext((S0.i64 >> S1.u[5:0]) & ((1 << S1.u[22:16]) - 1));<br>SCC = (D.i64 != 0).<br>Bit field extract. S0 is Data, S1[5:0] is field offset, S1[22:16] is<br>field width.|
|41|S_CBRANCH_G_FOR<br>K|mask_pass = S0.u64 & EXEC;<br>mask_fail = ~S0.u64 & EXEC;<br>if(mask_pass == EXEC) then<br>PC = S1.u64;<br>elsif(mask_fail == EXEC) then<br>PC += 4;<br>elsif(bitcount(mask_fail) < bitcount(mask_pass))<br>EXEC = mask_fail;<br>SGPR[CSP*4] = { S1.u64, mask_pass };<br>CSP += 1;<br>PC += 4;<br>else<br>EXEC = mask_pass;<br>SGPR[CSP*4] = { PC + 4, mask_fail };<br>CSP += 1;<br>PC = S1.u64;<br>endif.<br>Conditional branch using branch-stack. S0 = compare mask(vcc or any<br>sgpr) and S1 = 64-bit byte address of target instruction. See also<br>S_CBRANCH_JOIN.|



12.1. SOP2 Instructions

94 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|42|S_ABSDIFF_I32|D.i = S0.i - S1.i;<br>if(D.i < 0) then<br>D.i = -D.i;<br>endif;<br>SCC = (D.i != 0).<br>Compute the absolute value of difference between two values.<br>Examples:<br>S_ABSDIFF_I32(0x00000002, 0x00000005) => 0x00000003<br>S_ABSDIFF_I32(0xffffffff, 0x00000000) => 0x00000001<br>S_ABSDIFF_I32(0x80000000, 0x00000000) => 0x80000000     // Note:<br>result is negative!<br>S_ABSDIFF_I32(0x80000000, 0x00000001) => 0x7fffffff<br>S_ABSDIFF_I32(0x80000000, 0xffffffff) => 0x7fffffff<br>S_ABSDIFF_I32(0x80000000, 0xfffffffe) => 0x7ffffffe|
|43|S_RFE_RESTORE_B<br>64|PRIV = 0;<br>PC = S0.u64.<br>Return from exception handler and continue. This instruction may only<br>be used within a trap handler.<br>This instruction is provided for compatibility with older ASICs. New<br>shader code must use S_RFE_B64. The second argument is ignored.|
|44|S_MUL_HI_U32|D.u = (S0.u * S1.u) >> 32.|
|45|S_MUL_HI_I32|D.i = (S0.i * S1.i) >> 32.|
|46|S_LSHL1_ADD_U32|D.u = (S0.u << 1) + S1.u;<br>SCC = (((S0.u << 1) + S1.u) >= 0x100000000ULL ? 1 : 0). // unsigned<br>overflow.|
|47|S_LSHL2_ADD_U32|D.u = (S0.u << 2) + S1.u;<br>SCC = (((S0.u << 2) + S1.u) >= 0x100000000ULL ? 1 : 0). // unsigned<br>overflow.|
|48|S_LSHL3_ADD_U32|D.u = (S0.u << 3) + S1.u;<br>SCC = (((S0.u << 3) + S1.u) >= 0x100000000ULL ? 1 : 0). // unsigned<br>overflow.|
|49|S_LSHL4_ADD_U32|D.u = (S0.u << 4) + S1.u;<br>SCC = (((S0.u << 4) + S1.u) >= 0x100000000ULL ? 1 : 0). // unsigned<br>overflow.|
|50|S_PACK_LL_B32_B16|D.u[31:0] = { S1.u[15:0], S0.u[15:0] }.|
|51|S_PACK_LH_B32_B1<br>6|D.u[31:0] = { S1.u[31:16], S0.u[15:0] }.|
|52|S_PACK_HH_B32_B1<br>6|D.u[31:0] = { S1.u[31:16], S0.u[31:16] }.|



## **12.2. SOPK Instructions**



12.2. SOPK Instructions

95 of 267

"AMD Instinct MI200" Instruction Set Architecture



Instructions in this format may use a 32-bit literal constant which occurs immediately after the instruction.

|**Opcode**|**Name**|**Description**|
|---|---|---|
|0|S_MOVK_I32|D.i = signext(SIMM16).|
|||Sign extension from a 16-bit constant.|
|1|S_CMOVK_I32|if(SCC) then<br>D.i = signext(SIMM16);<br>endif.|
|||Conditional move with sign extension.|
|2|S_CMPK_EQ_I32|SCC = (S0.i == signext(SIMM16)).|
|3|S_CMPK_LG_I32|SCC = (S0.i != signext(SIMM16)).|
|4|S_CMPK_GT_I32|SCC = (S0.i > signext(SIMM16)).|
|5|S_CMPK_GE_I32|SCC = (S0.i >= signext(SIMM16)).|
|6|S_CMPK_LT_I32|SCC = (S0.i < signext(SIMM16)).|
|7|S_CMPK_LE_I32|SCC = (S0.i <= signext(SIMM16)).|
|8|S_CMPK_EQ_U32|SCC = (S0.u == SIMM16).|
|9|S_CMPK_LG_U32|SCC = (S0.u != SIMM16).|
|10|S_CMPK_GT_U32|SCC = (S0.u > SIMM16).|
|11|S_CMPK_GE_U32|SCC = (S0.u >= SIMM16).|
|12|S_CMPK_LT_U32|SCC = (S0.u < SIMM16).|
|13|S_CMPK_LE_U32|SCC = (S0.u <= SIMM16).|
|14|S_ADDK_I32|tmp = D.i; // save value to check sign bits for overflow later.<br>D.i = D.i + signext(SIMM16);<br>SCC = (tmp[31] == SIMM16[15] && tmp[31] != D.i[31]). // signed<br>overflow.|
|15|S_MULK_I32|D.i = D.i * signext(SIMM16).|



12.2. SOPK Instructions

96 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|16|S_CBRANCH_I_FOR<br>K|mask_pass = S0.u64 & EXEC;<br>mask_fail = ~S0.u64 & EXEC;<br>target_addr = PC + signext(SIMM16 * 4) + 4;<br>if(mask_pass == EXEC)<br>PC = target_addr;<br>elsif(mask_fail == EXEC)<br>PC += 4;<br>elsif(bitcount(mask_fail) < bitcount(mask_pass))<br>EXEC = mask_fail;<br>SGPR[CSP*4] = { target_addr, mask_pass };<br>CSP += 1;<br>PC += 4;<br>else<br>EXEC = mask_pass;<br>SGPR[CSP*4] = { PC + 4, mask_fail };<br>CSP += 1;<br>PC = target_addr;<br>endif.<br>Conditional branch using branch-stack. S0 = compare mask(vcc or any<br>sgpr), and SIMM16 = signed DWORD branch offset relative to next<br>instruction. See also S_CBRANCH_JOIN.|
|17|S_GETREG_B32|D.u = hardware-reg. Read some or all of a hardware register into the<br>LSBs of D.<br>SIMM16 = {size[4:0], offset[4:0], hwRegId[5:0]}; offset is 0..31, size<br>is 1..32.|
|18|S_SETREG_B32|hardware-reg = S0.u. Write some or all of the LSBs of D into a<br>hardware register.<br>SIMM16 = {size[4:0], offset[4:0], hwRegId[5:0]}; offset is 0..31, size<br>is 1..32.|
|20|S_SETREG_IMM32_B<br>32|Write some or all of the LSBs of IMM32 into a hardware register; this<br>instruction requires a 32-bit literal constant.<br>SIMM16 = {size[4:0], offset[4:0], hwRegId[5:0]}; offset is 0..31, size<br>is 1..32.|
|21|S_CALL_B64|D.u64 = PC + 4;<br>PC = PC + signext(SIMM16 * 4) + 4.<br>Implements a short call, where the return address (the next<br>instruction after the S_CALL_B64) is saved to D. Long calls should<br>consider S_SWAPPC_B64 instead. Note that this instruction is always 4<br>bytes.|



## **12.3. SOP1 Instructions**



Instructions in this format may use a 32-bit literal constant which occurs immediately after the

12.3. SOP1 Instructions

97 of 267

"AMD Instinct MI200" Instruction Set Architecture



#### instruction.

|**Opcode**|**Name**|**Description**|
|---|---|---|
|0|S_MOV_B32|D.u = S0.u.|
|1|S_MOV_B64|D.u64 = S0.u64.|
|2|S_CMOV_B32|if(SCC) then<br>D.u = S0.u;<br>endif.|
|||Conditional move.|
|3|S_CMOV_B64|if(SCC) then<br>D.u64 = S0.u64;<br>endif.|
|||Conditional move.|
|4|S_NOT_B32|D = ~S0;<br>SCC = (D != 0).|
|||Bitwise negation.|
|5|S_NOT_B64|D = ~S0;<br>SCC = (D != 0).<br>Bitwise negation.|
|6|S_WQM_B32|for i in 0 ... opcode_size_in_bits - 1 do<br>D[i] = (S0[(i & ~3):(i | 3)] != 0);<br>endfor;<br>SCC = (D != 0).|
|||Computes whole quad mode for an active/valid mask. If any pixel in a<br>quad is active, all pixels of the quad are marked active.|
|7|S_WQM_B64|for i in 0 ... opcode_size_in_bits - 1 do<br>D[i] = (S0[(i & ~3):(i | 3)] != 0);<br>endfor;<br>SCC = (D != 0).<br>Computes whole quad mode for an active/valid mask. If any pixel in a<br>quad is active, all pixels of the quad are marked active.|
|8|S_BREV_B32|D.u[31:0] = S0.u[0:31].|
|||Reverse bits.|
|9|S_BREV_B64|D.u64[63:0] = S0.u64[0:63].<br>Reverse bits.|



12.3. SOP1 Instructions

98 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|10|S_BCNT0_I32_B32|D = 0;<br>for i in 0 ... opcode_size_in_bits - 1 do<br>D += (S0[i] == 0 ? 1 : 0)<br>endfor;<br>SCC = (D != 0).<br>Examples:<br>S_BCNT0_I32_B32(0x00000000) => 32<br>S_BCNT0_I32_B32(0xcccccccc) => 16<br>S_BCNT0_I32_B32(0xffffffff) => 0|
|11|S_BCNT0_I32_B64|D = 0;<br>for i in 0 ... opcode_size_in_bits - 1 do<br>D += (S0[i] == 0 ? 1 : 0)<br>endfor;<br>SCC = (D != 0).|
|||Examples:|
|||S_BCNT0_I32_B32(0x00000000) => 32|
|||S_BCNT0_I32_B32(0xcccccccc) => 16<br>S_BCNT0_I32_B32(0xffffffff) => 0|
|12|S_BCNT1_I32_B32|D = 0;<br>for i in 0 ... opcode_size_in_bits - 1 do<br>D += (S0[i] == 1 ? 1 : 0)<br>endfor;<br>SCC = (D != 0).|
|||Examples:|
|||S_BCNT1_I32_B32(0x00000000) => 0<br>S_BCNT1_I32_B32(0xcccccccc) => 16|
|||S_BCNT1_I32_B32(0xffffffff) => 32|
|13|S_BCNT1_I32_B64|D = 0;<br>for i in 0 ... opcode_size_in_bits - 1 do<br>D += (S0[i] == 1 ? 1 : 0)<br>endfor;<br>SCC = (D != 0).|
|||Examples:<br>S_BCNT1_I32_B32(0x00000000) => 0|
|||S_BCNT1_I32_B32(0xcccccccc) => 16|
|||S_BCNT1_I32_B32(0xffffffff) => 32|



12.3. SOP1 Instructions

99 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|14|S_FF0_I32_B32|D.i = -1; // Set if no zeros are found<br>for i in 0 ... opcode_size_in_bits - 1 do // Search from LSB<br>if S0[i] == 0 then<br>D.i = i;<br>break for;<br>endif;<br>endfor.<br>Returns the bit position of the first zero from the LSB, or -1 if<br>there are no zeros.<br>Examples:<br>S_FF0_I32_B32(0xaaaaaaaa) => 0<br>S_FF0_I32_B32(0x55555555) => 1<br>S_FF0_I32_B32(0x00000000) => 0<br>S_FF0_I32_B32(0xffffffff) => 0xffffffff<br>S_FF0_I32_B32(0xfffeffff) => 16|
|15|S_FF0_I32_B64|D.i = -1; // Set if no zeros are found<br>for i in 0 ... opcode_size_in_bits - 1 do // Search from LSB<br>if S0[i] == 0 then<br>D.i = i;<br>break for;<br>endif;<br>endfor.|
|||Returns the bit position of the first zero from the LSB, or -1 if<br>there are no zeros.|
|||Examples:<br>S_FF0_I32_B32(0xaaaaaaaa) => 0<br>S_FF0_I32_B32(0x55555555) => 1<br>S_FF0_I32_B32(0x00000000) => 0<br>S_FF0_I32_B32(0xffffffff) => 0xffffffff<br>S_FF0_I32_B32(0xfffeffff) => 16|
|16|S_FF1_I32_B32|D.i = -1; // Set if no ones are found<br>for i in 0 ... opcode_size_in_bits - 1 do // Search from LSB<br>if S0[i] == 1 then<br>D.i = i;<br>break for;<br>endif;<br>endfor.|
|||Returns the bit position of the first one from the LSB, or -1 if there<br>are no ones.|
|||Examples:<br>S_FF1_I32_B32(0xaaaaaaaa) => 1<br>S_FF1_I32_B32(0x55555555) => 0<br>S_FF1_I32_B32(0x00000000) => 0xffffffff<br>S_FF1_I32_B32(0xffffffff) => 0<br>S_FF1_I32_B32(0x00010000) => 16|



12.3. SOP1 Instructions

100 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|17|S_FF1_I32_B64|D.i = -1; // Set if no ones are found<br>for i in 0 ... opcode_size_in_bits - 1 do // Search from LSB<br>if S0[i] == 1 then<br>D.i = i;<br>break for;<br>endif;<br>endfor.<br>Returns the bit position of the first one from the LSB, or -1 if there<br>are no ones.|
|||Examples:<br>S_FF1_I32_B32(0xaaaaaaaa) => 1<br>S_FF1_I32_B32(0x55555555) => 0<br>S_FF1_I32_B32(0x00000000) => 0xffffffff<br>S_FF1_I32_B32(0xffffffff) => 0<br>S_FF1_I32_B32(0x00010000) => 16|
|18|S_FLBIT_I32_B32|D.i = -1; // Set if no ones are found<br>for i in 0 ... opcode_size_in_bits - 1 do<br>// Note: search is from the MSB<br>if S0[opcode_size_in_bits - 1 - i] == 1 then<br>D.i = i;<br>break for;<br>endif;<br>endfor.<br>Counts how many zeros before the first one starting from the MSB.<br>Returns -1 if there are no ones.<br>Examples:<br>S_FLBIT_I32_B32(0x00000000) => 0xffffffff<br>S_FLBIT_I32_B32(0x0000cccc) => 16<br>S_FLBIT_I32_B32(0xffff3333) => 0<br>S_FLBIT_I32_B32(0x7fffffff) => 1<br>S_FLBIT_I32_B32(0x80000000) => 0<br>S_FLBIT_I32_B32(0xffffffff) => 0|
|19|S_FLBIT_I32_B64|D.i = -1; // Set if no ones are found<br>for i in 0 ... opcode_size_in_bits - 1 do<br>// Note: search is from the MSB<br>if S0[opcode_size_in_bits - 1 - i] == 1 then<br>D.i = i;<br>break for;<br>endif;<br>endfor.<br>Counts how many zeros before the first one starting from the MSB.<br>Returns -1 if there are no ones.|
|||Examples:<br>S_FLBIT_I32_B32(0x00000000) => 0xffffffff<br>S_FLBIT_I32_B32(0x0000cccc) => 16<br>S_FLBIT_I32_B32(0xffff3333) => 0<br>S_FLBIT_I32_B32(0x7fffffff) => 1<br>S_FLBIT_I32_B32(0x80000000) => 0<br>S_FLBIT_I32_B32(0xffffffff) => 0|



12.3. SOP1 Instructions

101 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|20|S_FLBIT_I32|D.i = -1; // Set if all bits are the same<br>for i in 1 ... opcode_size_in_bits - 1 do<br>// Note: search is from the MSB<br>if S0[opcode_size_in_bits - 1 - i] != S0[opcode_size_in_bits - 1]<br>then<br>D.i = i;<br>break for;<br>endif;<br>endfor.<br>Counts how many bits in a row (from MSB to LSB) are the same as the<br>sign bit. Returns -1 if all bits are the same.<br>Examples:<br>S_FLBIT_I32(0x00000000) => 0xffffffff<br>S_FLBIT_I32(0x0000cccc) => 16<br>S_FLBIT_I32(0xffff3333) => 16<br>S_FLBIT_I32(0x7fffffff) => 1<br>S_FLBIT_I32(0x80000000) => 1<br>S_FLBIT_I32(0xffffffff) => 0xffffffff|
|21|S_FLBIT_I32_I64|D.i = -1; // Set if all bits are the same<br>for i in 1 ... opcode_size_in_bits - 1 do<br>// Note: search is from the MSB<br>if S0[opcode_size_in_bits - 1 - i] != S0[opcode_size_in_bits - 1]<br>then<br>D.i = i;<br>break for;<br>endif;<br>endfor.|
|||Counts how many bits in a row (from MSB to LSB) are the same as the<br>sign bit. Returns -1 if all bits are the same.|
|||Examples:<br>|
|||S_FLBIT_I32(0x00000000) => 0xffffffff<br>S_FLBIT_I32(0x0000cccc) => 16<br>S_FLBIT_I32(0xffff3333) => 16<br>S_FLBIT_I32(0x7fffffff) => 1<br>S_FLBIT_I32(0x80000000) => 1<br>S_FLBIT_I32(0xffffffff) => 0xffffffff|
|22|S_SEXT_I32_I8|D.i = signext(S0.i[7:0]).|
|||Sign extension.|
|23|S_SEXT_I32_I16|D.i = signext(S0.i[15:0]).|
|||Sign extension.|
|24|S_BITSET0_B32|D.u[S0.u[4:0]] = 0.|
|25|S_BITSET0_B64|D.u64[S0.u[5:0]] = 0.|
|26|S_BITSET1_B32|D.u[S0.u[4:0]] = 1.|
|27|S_BITSET1_B64|D.u64[S0.u[5:0]] = 1.|



12.3. SOP1 Instructions

102 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|28|S_GETPC_B64|D.u64 = PC + 4.<br>Destination receives the byte address of the next instruction. Note<br>that this instruction is always 4 bytes.|
|29|S_SETPC_B64|PC = S0.u64.<br>S0.u64 is a byte address of the instruction to jump to.|
|30|S_SWAPPC_B64|D.u64 = PC + 4;<br>PC = S0.u64.<br>S0.u64 is a byte address of the instruction to jump to. Destination<br>receives the byte address of the instruction immediately following the<br>SWAPPC instruction. Note that this instruction is always 4 bytes.|
|31|S_RFE_B64|PRIV = 0;<br>PC = S0.u64.<br>Return from exception handler and continue. This instruction may only<br>be used within a trap handler.|
|32|S_AND_SAVEEXEC_<br>B64|D.u64 = EXEC;<br>EXEC = S0.u64 & EXEC;<br>SCC = (EXEC != 0).|
|33|S_OR_SAVEEXEC_B<br>64|D.u64 = EXEC;<br>EXEC = S0.u64 | EXEC;<br>SCC = (EXEC != 0).|
|34|S_XOR_SAVEEXEC_<br>B64|D.u64 = EXEC;<br>EXEC = S0.u64 ^ EXEC;<br>SCC = (EXEC != 0).|
|35|S_ANDN2_SAVEEXE<br>C_B64|D.u64 = EXEC;<br>EXEC = S0.u64 & ~EXEC;<br>SCC = (EXEC != 0).|
|36|S_ORN2_SAVEEXEC<br>_B64|D.u64 = EXEC;<br>EXEC = S0.u64 | ~EXEC;<br>SCC = (EXEC != 0).|
|37|S_NAND_SAVEEXEC<br>_B64|D.u64 = EXEC;<br>EXEC = ~(S0.u64 & EXEC);<br>SCC = (EXEC != 0).|
|38|S_NOR_SAVEEXEC_<br>B64|D.u64 = EXEC;<br>EXEC = ~(S0.u64 | EXEC);<br>SCC = (EXEC != 0).|
|39|S_XNOR_SAVEEXEC<br>_B64|D.u64 = EXEC;<br>EXEC = ~(S0.u64 ^ EXEC);<br>SCC = (EXEC != 0).|
|40|S_QUADMASK_B32|D = 0;<br>for i in 0 ... (opcode_size_in_bits / 4) - 1 do<br>D[i] = (S0[i * 4 + 3:i * 4] != 0);<br>endfor;<br>SCC = (D != 0).<br>Reduce a pixel mask to a quad mask. To perform the inverse operation<br>see S_BITREPLICATE_B64_B32.|



12.3. SOP1 Instructions

103 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|41|S_QUADMASK_B64|D = 0;<br>for i in 0 ... (opcode_size_in_bits / 4) - 1 do<br>D[i] = (S0[i * 4 + 3:i * 4] != 0);<br>endfor;<br>SCC = (D != 0).<br>Reduce a pixel mask to a quad mask. To perform the inverse operation<br>see S_BITREPLICATE_B64_B32.|
|42|S_MOVRELS_B32|addr = SGPR address appearing in instruction SRC0 field;<br>addr += M0.u;<br>D.u = SGPR[addr].u.<br>Move from a relative source address. For example, the following<br>instruction sequence will perform a move s5 <== s17:<br>s_mov_b32 m0, 10<br>s_movrels_b32 s5, s7|
|43|S_MOVRELS_B64|addr = SGPR address appearing in instruction SRC0 field;<br>addr += M0.u;<br>D.u64 = SGPR[addr].u64.<br>Move from a relative source address. The index in M0.u must be even<br>for this operation.|
|44|S_MOVRELD_B32|addr = SGPR address appearing in instruction DST field;<br>addr += M0.u;<br>SGPR[addr].u = S0.u.<br>Move to a relative destination address. For example, the following<br>instruction sequence will perform a move s15 <== s7:<br>s_mov_b32 m0, 10<br>s_movreld_b32 s5, s7|
|45|S_MOVRELD_B64|addr = SGPR address appearing in instruction DST field;<br>addr += M0.u;<br>SGPR[addr].u64 = S0.u64.<br>Move to a relative destination address. The index in M0.u must be even<br>for this operation.|
|46|S_CBRANCH_JOIN|saved_csp = S0.u;<br>if(CSP == saved_csp) then<br>PC += 4; // Second time to JOIN: continue with program.<br>else<br>CSP -= 1; // First time to JOIN; jump to other FORK path.<br>{PC, EXEC} = SGPR[CSP * 4]; // Read 128 bits from 4 consecutive<br>SGPRs.<br>endif.<br>Conditional branch join point (end of conditional branch block). S0 is<br>saved CSP value. See S_CBRANCH_G_FORK and S_CBRANCH_I_FORK for related<br>instructions.|



12.3. SOP1 Instructions

104 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|48|S_ABS_I32|D.i = (S.i < 0 ? -S.i : S.i);<br>SCC = (D.i != 0).<br>Integer absolute value.|
|||Examples:<br>S_ABS_I32(0x00000001) => 0x00000001<br>S_ABS_I32(0x7fffffff) => 0x7fffffff<br>S_ABS_I32(0x80000000) => 0x80000000     // Note this is negative!<br>S_ABS_I32(0x80000001) => 0x7fffffff<br>S_ABS_I32(0x80000002) => 0x7ffffffe<br>S_ABS_I32(0xffffffff) => 0x00000001|
|50|S_SET_GPR_IDX_ID<br>X|M0[7:0] = S0.u[7:0].<br>Modify the index used in vector GPR indexing.<br>S_SET_GPR_IDX_ON, S_SET_GPR_IDX_OFF, S_SET_GPR_IDX_MODE and<br>S_SET_GPR_IDX_IDX are related instructions.|
|51|S_ANDN1_SAVEEXE<br>C_B64|D.u64 = EXEC;<br>EXEC = ~S0.u64 & EXEC;<br>SCC = (EXEC != 0).|
|52|S_ORN1_SAVEEXEC<br>_B64|D.u64 = EXEC;<br>EXEC = ~S0.u64 | EXEC;<br>SCC = (EXEC != 0).|
|53|S_ANDN1_WREXEC_<br>B64|EXEC = ~S0.u64 & EXEC;<br>D.u64 = EXEC;<br>SCC = (EXEC != 0).|
|54|S_ANDN2_WREXEC_<br>B64|EXEC = S0.u64 & ~EXEC;<br>D.u64 = EXEC;<br>SCC = (EXEC != 0).|
|55|S_BITREPLICATE_B6<br>4_B32|for i in 0 ... 31 do<br>D.u64[i * 2 + 0] = S0.u32[i]<br>D.u64[i * 2 + 1] = S0.u32[i]<br>endfor.<br>Replicate the low 32 bits of S0 by 'doubling' each bit.<br>This opcode can be used to convert a quad mask into a pixel mask;<br>given quad mask in s0, the following sequence will produce a pixel mask<br>in s1:<br>s_bitreplicate_b64 s1, s0<br>s_bitreplicate_b64 s1, s1|
|||To perform the inverse operation see S_QUADMASK_B64.|



## **12.4. SOPC Instructions**



Instructions in this format may use a 32-bit literal constant which occurs immediately after the

12.4. SOPC Instructions

105 of 267

"AMD Instinct MI200" Instruction Set Architecture



#### instruction.

|**Opcode**|**Name**|**Description**|
|---|---|---|
|0|S_CMP_EQ_I32|SCC = (S0 == S1).<br>Note that S_CMP_EQ_I32 and S_CMP_EQ_U32 are identical opcodes, but<br>both are provided for symmetry.|
|1|S_CMP_LG_I32|SCC = (S0 != S1).<br>Note that S_CMP_LG_I32 and S_CMP_LG_U32 are identical opcodes, but<br>both are provided for symmetry.|
|2|S_CMP_GT_I32|SCC = (S0.i > S1.i).|
|3|S_CMP_GE_I32|SCC = (S0.i >= S1.i).|
|4|S_CMP_LT_I32|SCC = (S0.i < S1.i).|
|5|S_CMP_LE_I32|SCC = (S0.i <= S1.i).|
|6|S_CMP_EQ_U32|SCC = (S0 == S1).<br>Note that S_CMP_EQ_I32 and S_CMP_EQ_U32 are identical opcodes, but<br>both are provided for symmetry.|
|7|S_CMP_LG_U32|SCC = (S0 != S1).|
|||Note that S_CMP_LG_I32 and S_CMP_LG_U32 are identical opcodes, but<br>both are provided for symmetry.|
|8|S_CMP_GT_U32|SCC = (S0.u > S1.u).|
|9|S_CMP_GE_U32|SCC = (S0.u >= S1.u).|
|10|S_CMP_LT_U32|SCC = (S0.u < S1.u).|
|11|S_CMP_LE_U32|SCC = (S0.u <= S1.u).|
|12|S_BITCMP0_B32|SCC = (S0.u[S1.u[4:0]] == 0).|
|13|S_BITCMP1_B32|SCC = (S0.u[S1.u[4:0]] == 1).|
|14|S_BITCMP0_B64|SCC = (S0.u64[S1.u[5:0]] == 0).|
|15|S_BITCMP1_B64|SCC = (S0.u64[S1.u[5:0]] == 1).|
|16|S_SETVSKIP|VSKIP = S0.u[S1.u[4:0]].<br>Enables and disables VSKIP mode. When VSKIP is enabled, no<br>VOP*/M*BUF/MIMG/DS/FLAT/EXP instuctions are issued. Note that VSKIPped<br>memory instructions do not manipulate the waitcnt counters; as a<br>result, if you have outstanding memory requests you may want to issue<br>S_WAITCNT 0 prior to enabling VSKIP, otherwise you'll need to be<br>careful not to count VSKIPped instructions in your waitcnt<br>calculations.|
|||Examples:<br>s_setvskip 1, 0     // Enable vskip mode.<br>s_setvskip 0, 0     // Disable vskip mode.|



12.4. SOPC Instructions

106 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|17|S_SET_GPR_IDX_ON|MODE.gpr_idx_en = 1;<br>M0[7:0] = S0.u[7:0];<br>M0[15:12] = SIMM4; // this is the direct content of S1 field<br>// Remaining bits of M0 are unmodified.|
|||Enable GPR indexing mode. Vector operations after this will perform<br>relative GPR addressing based on the contents of M0. The structure<br>SQ_M0_GPR_IDX_WORD may be used to decode M0. The raw contents of the S1<br>field are read and used to set the enable bits. S1[0] = VSRC0_REL,<br>S1[1] = VSRC1_REL, S1[2] = VSRC2_REL and S1[3] = VDST_REL.|
|||S_SET_GPR_IDX_ON, S_SET_GPR_IDX_OFF, S_SET_GPR_IDX_MODE and<br>S_SET_GPR_IDX_IDX are related instructions.|
|18|S_CMP_EQ_U64|SCC = (S0.i64 == S1.i64).|
|19|S_CMP_LG_U64|SCC = (S0.i64 != S1.i64).|



## **12.5. SOPP Instructions**



|**Opcode**|**Name**|**Description**|
|---|---|---|
|0|S_NOP|Do nothing. Repeat NOP 1..16 times based on SIMM16[3:0] -- 0x0 = 1<br>time, 0xf = 16 times. This instruction may be used to introduce wait<br>states to resolve hazards. Compare with S_SLEEP.|
|1|S_ENDPGM|End of program; terminate wavefront. The hardware implicitly<br>executes S_WAITCNT 0 before executing this instruction. See<br>S_ENDPGM_SAVED for the context-switch version of this instruction and<br>S_ENDPGM_ORDERED_PS_DONE for the POPS critical region version of this<br>instruction.|
|2|S_BRANCH|PC = PC + signext(SIMM16 * 4) + 4. // short jump.<br>For a long jump, use S_SETPC_B64.|
|3|S_WAKEUP|Allow a wave to 'ping' all the other waves in its threadgroup to<br>force them to wake up immediately from an S_SLEEP instruction. The<br>ping is ignored if the waves are not sleeping. This allows for<br>efficient polling on a memory location. The waves which are polling<br>can sit in a long S_SLEEP between memory reads, but the wave which<br>writes the value can tell them all to wake up early now that the data<br>is available. This is useful for fBarrier implementations (speedup).<br>This method is also safe from races because if any wave misses the<br>ping, everything still works fine (waves which missed it just<br>complete their normal S_SLEEP).<br>If the wave executing S_WAKEUP is in a threadgroup (in_tg set), then<br>it will wake up all waves associated with the same threadgroup ID.<br>Otherwise, S_WAKEUP is treated as an S_NOP.|



12.5. SOPP Instructions

107 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|4|S_CBRANCH_SCC0|if(SCC == 0) then<br>PC = PC + signext(SIMM16 * 4) + 4;<br>endif.|
|5|S_CBRANCH_SCC1|if(SCC == 1) then<br>PC = PC + signext(SIMM16 * 4) + 4;<br>endif.|
|6|S_CBRANCH_VCCZ|if(VCC == 0) then<br>PC = PC + signext(SIMM16 * 4) + 4;<br>endif.|
|7|S_CBRANCH_VCCNZ|if(VCC != 0) then<br>PC = PC + signext(SIMM16 * 4) + 4;<br>endif.|
|8|S_CBRANCH_EXECZ|if(EXEC == 0) then<br>PC = PC + signext(SIMM16 * 4) + 4;<br>endif.|
|9|S_CBRANCH_EXECNZ|if(EXEC != 0) then<br>PC = PC + signext(SIMM16 * 4) + 4;<br>endif.|
|10|S_BARRIER|Synchronize waves within a threadgroup. If not all waves of the<br>threadgroup have been created yet, waits for entire group before<br>proceeding. If some waves in the threadgroup have already terminated,<br>this waits on only the surviving waves. Barriers are legal inside<br>trap handlers.|
|11|S_SETKILL|Set KILL bit to value of SIMM16[0]. Used primarily for debugging<br>kill wave host command behavior.|
|12|S_WAITCNT|Wait for the counts of outstanding lds, vector-memory and<br>export/vmem-write-data to be at or below the specified levels.<br>SIMM16[3:0] = vmcount (vector memory operations) lower bits [3:0],<br>SIMM16[6:4] = export/mem-write-data count,<br>SIMM16[11:8] = LGKM_cnt (scalar-mem/GDS/LDS count),<br>SIMM16[15:14] = vmcount (vector memory operations) upper bits [5:4],|
|13|S_SETHALT|Set HALT bit to value of SIMM16[0]; 1 = halt, 0 = resume. The halt<br>flag is ignored while PRIV == 1 (inside trap handlers) but the shader<br>will halt immediately after the handler returns if HALT is still set<br>at that time.|
|14|S_SLEEP|Cause a wave to sleep for (64 * SIMM16[6:0] + 1..64) clocks. The<br>exact amount of delay is approximate. Compare with S_NOP.|
|15|S_SETPRIO|User settable wave priority is set to SIMM16[1:0]. 0 = lowest, 3 =<br>highest. The overall wave priority is {SPIPrio[1:0] , UserPrio[1:0],<br>WaveAge[3:0]}.|
|16|S_SENDMSG|Send a message upstream to VGT or the interrupt handler. SIMM16[9:0]<br>contains the message type.|
|17|S_SENDMSGHALT|Send a message and then HALT the wavefront; see S_SENDMSG for<br>details.|



12.5. SOPP Instructions

108 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|18|S_TRAP|TrapID = SIMM16[7:0];<br>Wait for all instructions to complete;<br>{TTMP1, TTMP0} = {3'h0, PCRewind[3:0], HT[0], TrapID[7:0],<br>PC[47:0]};<br>PC = TBA; // trap base address<br>PRIV = 1.<br>Enter the trap handler. This instruction may be generated internally<br>as well in response to a host trap (HT = 1) or an exception. TrapID 0<br>is reserved for hardware use and should not be used in a shader-<br>generated trap.|
|19|S_ICACHE_INV|Invalidate entire L1 instruction cache.<br>Kernel must have 16 separate S_NOP instructions or a jump/branch<br>instruction after this instruction to ensure the SQ instruction<br>buffer is purged.|
|20|S_INCPERFLEVEL|Increment performance counter specified in SIMM16[3:0] by 1.|
|21|S_DECPERFLEVEL|Decrement performance counter specified in SIMM16[3:0] by 1.|
|23|S_CBRANCH_CDBGSY<br>S|if(conditional_debug_system != 0) then<br>PC = PC + signext(SIMM16 * 4) + 4;<br>endif.|
|24|S_CBRANCH_CDBGUS<br>ER|if(conditional_debug_user != 0) then<br>PC = PC + signext(SIMM16 * 4) + 4;<br>endif.|
|25|S_CBRANCH_CDBGSY<br>S_OR_USER|if(conditional_debug_system || conditional_debug_user) then<br>PC = PC + signext(SIMM16 * 4) + 4;<br>endif.|
|26|S_CBRANCH_CDBGSY<br>S_AND_USER|if(conditional_debug_system && conditional_debug_user) then<br>PC = PC + signext(SIMM16 * 4) + 4;<br>endif.|
|27|S_ENDPGM_SAVED|End of program; signal that a wave has been saved by the context-<br>switch trap handler and terminate wavefront. The hardware implicitly<br>executes S_WAITCNT 0 before executing this instruction. See S_ENDPGM<br>for additional variants.|
|28|S_SET_GPR_IDX_OFF|MODE.gpr_idx_en = 0.<br>Clear GPR indexing mode. Vector operations after this will not<br>perform relative GPR addressing regardless of the contents of M0.<br>This instruction does not modify M0.|
|||S_SET_GPR_IDX_ON, S_SET_GPR_IDX_OFF, S_SET_GPR_IDX_MODE and<br>S_SET_GPR_IDX_IDX are related instructions.|
|29|S_SET_GPR_IDX_MOD<br>E|M0[15:12] = SIMM16[3:0].<br>Modify the mode used for vector GPR indexing. The raw contents of<br>the source field are read and used to set the enable bits. SIMM16[0]<br>= VSRC0_REL, SIMM16[1] = VSRC1_REL, SIMM16[2] = VSRC2_REL and<br>SIMM16[3] = VDST_REL.|
|||S_SET_GPR_IDX_ON, S_SET_GPR_IDX_OFF, S_SET_GPR_IDX_MODE and<br>S_SET_GPR_IDX_IDX are related instructions.|



12.5. SOPP Instructions

109 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|30|S_ENDPGM_ORDERED|End of program; signal that a wave has exited its POPS critical|
||_PS_DONE|section and terminate wavefront. The hardware implicitly executes|
|||S_WAITCNT 0 before executing this instruction. This instruction is an|
|||optimization that combines S_SENDMSG(MSG_ORDERED_PS_DONE) and|
|||S_ENDPGM; there may be cases where you still need to send the message|
|||separately, in which case you can end the shader with a normal|
|||S_ENDPGM instruction. See S_ENDPGM for additional variants.|



### **12.5.1. Send Message**

The S_SENDMSG instruction encodes the message type in M0, and can also send data from the SIMM16 field and in some cases from EXEC.

|**Message**|**SIMM16[3:0]**|**SIMM16[6:4]**|**Payload**|
|---|---|---|---|
|none|0|-|illegal|
|Interrupt|1|-|M0[23:0] carries data payload|
|Save wave|4|-|used in context switching|
|Stall Wave|5|-|stop new wave generation|
|Gen||||
|Halt Waves|6|-|halt all running waves of this vmid|



## **12.6. SMEM Instructions**



|**Opcode**|**Name**|**Description**|
|---|---|---|
|0|S_LOAD_DWORD|Read 1 dword from scalar data cache. If the offset is specified<br>as an SGPR, the SGPR contains an UNSIGNED BYTE offset (the 2<br>LSBs are ignored). If the offset is specified as an immediate<br>21-bit constant, the constant is a SIGNED BYTE offset.|
|1|S_LOAD_DWORDX2|Read 2 dwords from scalar data cache. See S_LOAD_DWORD for<br>details on the offset input.|
|2|S_LOAD_DWORDX4|Read 4 dwords from scalar data cache. See S_LOAD_DWORD for<br>details on the offset input.|
|3|S_LOAD_DWORDX8|Read 8 dwords from scalar data cache. See S_LOAD_DWORD for<br>details on the offset input.|
|4|S_LOAD_DWORDX16|Read 16 dwords from scalar data cache. See S_LOAD_DWORD for<br>details on the offset input.|



12.6. SMEM Instructions

110 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|5|S_SCRATCH_LOAD_DWORD|Read 1 dword from scalar data cache. If the offset is specified<br>as an SGPR, the SGPR contains an UNSIGNED 64-byte offset,<br>consistent with other scratch operations. If the offset is<br>specified as an immediate 21-bit constant, the constant is a<br>SIGNED BYTE offset.|
|6|S_SCRATCH_LOAD_DWORD<br>X2|Read 2 dwords from scalar data cache. See S_SCRATCH_LOAD_DWORD<br>for details on the offset input.|
|7|S_SCRATCH_LOAD_DWORD<br>X4|Read 4 dwords from scalar data cache. See S_SCRATCH_LOAD_DWORD<br>for details on the offset input.|
|8|S_BUFFER_LOAD_DWORD|Read 1 dword from scalar data cache. See S_LOAD_DWORD for<br>details on the offset input.|
|9|S_BUFFER_LOAD_DWORDX<br>2|Read 2 dwords from scalar data cache. See S_LOAD_DWORD for<br>details on the offset input.|
|10|S_BUFFER_LOAD_DWORDX<br>4|Read 4 dwords from scalar data cache. See S_LOAD_DWORD for<br>details on the offset input.|
|11|S_BUFFER_LOAD_DWORDX<br>8|Read 8 dwords from scalar data cache. See S_LOAD_DWORD for<br>details on the offset input.|
|12|S_BUFFER_LOAD_DWORDX<br>16|Read 16 dwords from scalar data cache. See S_LOAD_DWORD for<br>details on the offset input.|
|16|S_STORE_DWORD|Write 1 dword to scalar data cache. If the offset is specified<br>as an SGPR, the SGPR contains an UNSIGNED BYTE offset (the 2<br>LSBs are ignored). If the offset is specified as an immediate<br>21-bit constant, the constant is an SIGNED BYTE offset.|
|17|S_STORE_DWORDX2|Write 2 dwords to scalar data cache. See S_STORE_DWORD for<br>details on the offset input.|
|18|S_STORE_DWORDX4|Write 4 dwords to scalar data cache. See S_STORE_DWORD for<br>details on the offset input.|
|21|S_SCRATCH_STORE_DWOR<br>D|Write 1 dword from scalar data cache. If the offset is<br>specified as an SGPR, the SGPR contains an UNSIGNED 64-byte<br>offset, consistent with other scratch operations. If the offset<br>is specified as an immediate 21-bit constant, the constant is a<br>SIGNED BYTE offset.|
|22|S_SCRATCH_STORE_DWOR<br>DX2|Write 2 dwords from scalar data cache. See<br>S_SCRATCH_STORE_DWORD for details on the offset input.|
|23|S_SCRATCH_STORE_DWOR<br>DX4|Write 4 dwords from scalar data cache. See<br>S_SCRATCH_STORE_DWORD for details on the offset input.|
|24|S_BUFFER_STORE_DWORD|Write 1 dword to scalar data cache. See S_STORE_DWORD for<br>details on the offset input.|
|25|S_BUFFER_STORE_DWORD<br>X2|Write 2 dwords to scalar data cache. See S_STORE_DWORD for<br>details on the offset input.|
|26|S_BUFFER_STORE_DWORD<br>X4|Write 4 dwords to scalar data cache. See S_STORE_DWORD for<br>details on the offset input.|
|32|S_DCACHE_INV|Invalidate the scalar data cache.|
|33|S_DCACHE_WB|Write back dirty data in the scalar data cache.|



12.6. SMEM Instructions

111 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|34|S_DCACHE_INV_VOL|Invalidate the scalar data cache volatile lines.|
|35|S_DCACHE_WB_VOL|Write back dirty data in the scalar data cache volatile lines.|
|36|S_MEMTIME|Return current 64-bit timestamp.|
|37|S_MEMREALTIME|Return current 64-bit RTC.|
|38|S_ATC_PROBE|Probe or prefetch an address into the SQC data cache.|
|39|S_ATC_PROBE_BUFFER|Probe or prefetch an address into the SQC data cache.|
|40|S_DCACHE_DISCARD|Discard one dirty scalar data cache line. A cache line is 64<br>bytes. Normally, dirty cachelines (one which have been written<br>by the shader) are written back to memory, but this instruction<br>allows the shader to invalidate and not write back cachelines<br>which it has previously written. This is a performance<br>optimization to be used when the shader knows it no longer needs<br>that data. Address is calculated the same as S_STORE_DWORD,<br>except the 6 LSBs are ignored to get the 64 byte aligned<br>address. LGKM count is incremented by 1 for this opcode.|
|41|S_DCACHE_DISCARD_X2|Discard two consecutive dirty scalar data cache lines. A cache<br>line is 64 bytes. Normally, dirty cachelines (one which have<br>been written by the shader) are written back to memory, but this<br>instruction allows the shader to invalidate and not write back<br>cachelines which it has previously written. This is a<br>performance optimization to be used when the shader knows it no<br>longer needs that data. Address is calculated the same as<br>S_STORE_DWORD, except the 6 LSBs are ignored to get the 64 byte<br>aligned address. LGKM count is incremented by 2 for this opcode.|
|64|S_BUFFER_ATOMIC_SWAP|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = DATA;<br>RETURN_DATA = tmp.|
|65|S_BUFFER_ATOMIC_CMPS<br>WAP|// 32bit<br>tmp = MEM[ADDR];<br>src = DATA[0];<br>cmp = DATA[1];<br>MEM[ADDR] = (tmp == cmp) ? src : tmp;<br>RETURN_DATA[0] = tmp.|
|66|S_BUFFER_ATOMIC_ADD|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] += DATA;<br>RETURN_DATA = tmp.|
|67|S_BUFFER_ATOMIC_SUB|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] -= DATA;<br>RETURN_DATA = tmp.|
|68|S_BUFFER_ATOMIC_SMIN|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (DATA < tmp) ? DATA : tmp; // signed compare<br>RETURN_DATA = tmp.|



12.6. SMEM Instructions

112 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|69|S_BUFFER_ATOMIC_UMIN|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (DATA < tmp) ? DATA : tmp; // unsigned compare<br>RETURN_DATA = tmp.|
|70|S_BUFFER_ATOMIC_SMAX|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (DATA > tmp) ? DATA : tmp; // signed compare<br>RETURN_DATA = tmp.|
|71|S_BUFFER_ATOMIC_UMAX|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (DATA > tmp) ? DATA : tmp; // unsigned compare<br>RETURN_DATA = tmp.|
|72|S_BUFFER_ATOMIC_AND|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] &= DATA;<br>RETURN_DATA = tmp.|
|73|S_BUFFER_ATOMIC_OR|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] |= DATA;<br>RETURN_DATA = tmp.|
|74|S_BUFFER_ATOMIC_XOR|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] ^= DATA;<br>RETURN_DATA = tmp.|
|75|S_BUFFER_ATOMIC_INC|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (tmp >= DATA) ? 0 : tmp + 1; // unsigned compare<br>RETURN_DATA = tmp.|
|76|S_BUFFER_ATOMIC_DEC|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (tmp == 0 || tmp > DATA) ? DATA : tmp - 1; //<br>unsigned compare<br>RETURN_DATA = tmp.|
|96|S_BUFFER_ATOMIC_SWAP_<br>X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|
|97|S_BUFFER_ATOMIC_CMPS<br>WAP_X2|// 64bit<br>tmp = MEM[ADDR];<br>src = DATA[0:1];<br>cmp = DATA[2:3];<br>MEM[ADDR] = (tmp == cmp) ? src : tmp;<br>RETURN_DATA[0:1] = tmp.|
|98|S_BUFFER_ATOMIC_ADD_X<br>2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] += DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|



12.6. SMEM Instructions

113 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|99|S_BUFFER_ATOMIC_SUB_X<br>2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] -= DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|
|100|S_BUFFER_ATOMIC_SMIN_<br>X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] -= (DATA[0:1] < tmp) ? DATA[0:1] : tmp; // signed<br>compare<br>RETURN_DATA[0:1] = tmp.|
|101|S_BUFFER_ATOMIC_UMIN_<br>X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] -= (DATA[0:1] < tmp) ? DATA[0:1] : tmp; // unsigned<br>compare<br>RETURN_DATA[0:1] = tmp.|
|102|S_BUFFER_ATOMIC_SMAX_<br>X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] -= (DATA[0:1] > tmp) ? DATA[0:1] : tmp; // signed<br>compare<br>RETURN_DATA[0:1] = tmp.|
|103|S_BUFFER_ATOMIC_UMAX_<br>X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] -= (DATA[0:1] > tmp) ? DATA[0:1] : tmp; // unsigned<br>compare<br>RETURN_DATA[0:1] = tmp.|
|104|S_BUFFER_ATOMIC_AND_X<br>2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] &= DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|
|105|S_BUFFER_ATOMIC_OR_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] |= DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|
|106|S_BUFFER_ATOMIC_XOR_X<br>2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] ^= DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|
|107|S_BUFFER_ATOMIC_INC_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (tmp >= DATA[0:1]) ? 0 : tmp + 1; // unsigned<br>compare<br>RETURN_DATA[0:1] = tmp.|
|108|S_BUFFER_ATOMIC_DEC_X<br>2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (tmp == 0 || tmp > DATA[0:1]) ? DATA[0:1] : tmp -<br>1; // unsigned compare<br>RETURN_DATA[0:1] = tmp.|
|128|S_ATOMIC_SWAP|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = DATA;<br>RETURN_DATA = tmp.|



12.6. SMEM Instructions

114 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|129|S_ATOMIC_CMPSWAP|// 32bit<br>tmp = MEM[ADDR];<br>src = DATA[0];<br>cmp = DATA[1];<br>MEM[ADDR] = (tmp == cmp) ? src : tmp;<br>RETURN_DATA[0] = tmp.|
|130|S_ATOMIC_ADD|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] += DATA;<br>RETURN_DATA = tmp.|
|131|S_ATOMIC_SUB|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] -= DATA;<br>RETURN_DATA = tmp.|
|132|S_ATOMIC_SMIN|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (DATA < tmp) ? DATA : tmp; // signed compare<br>RETURN_DATA = tmp.|
|133|S_ATOMIC_UMIN|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (DATA < tmp) ? DATA : tmp; // unsigned compare<br>RETURN_DATA = tmp.|
|134|S_ATOMIC_SMAX|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (DATA > tmp) ? DATA : tmp; // signed compare<br>RETURN_DATA = tmp.|
|135|S_ATOMIC_UMAX|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (DATA > tmp) ? DATA : tmp; // unsigned compare<br>RETURN_DATA = tmp.|
|136|S_ATOMIC_AND|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] &= DATA;<br>RETURN_DATA = tmp.|
|137|S_ATOMIC_OR|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] |= DATA;<br>RETURN_DATA = tmp.|
|138|S_ATOMIC_XOR|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] ^= DATA;<br>RETURN_DATA = tmp.|
|139|S_ATOMIC_INC|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (tmp >= DATA) ? 0 : tmp + 1; // unsigned compare<br>RETURN_DATA = tmp.|



12.6. SMEM Instructions

115 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|140|S_ATOMIC_DEC|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (tmp == 0 || tmp > DATA) ? DATA : tmp - 1; //<br>unsigned compare<br>RETURN_DATA = tmp.|
|160|S_ATOMIC_SWAP_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|
|161|S_ATOMIC_CMPSWAP_X2|// 64bit<br>tmp = MEM[ADDR];<br>src = DATA[0:1];<br>cmp = DATA[2:3];<br>MEM[ADDR] = (tmp == cmp) ? src : tmp;<br>RETURN_DATA[0:1] = tmp.|
|162|S_ATOMIC_ADD_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] += DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|
|163|S_ATOMIC_SUB_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] -= DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|
|164|S_ATOMIC_SMIN_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] -= (DATA[0:1] < tmp) ? DATA[0:1] : tmp; // signed<br>compare<br>RETURN_DATA[0:1] = tmp.|
|165|S_ATOMIC_UMIN_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] -= (DATA[0:1] < tmp) ? DATA[0:1] : tmp; // unsigned<br>compare<br>RETURN_DATA[0:1] = tmp.|
|166|S_ATOMIC_SMAX_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] -= (DATA[0:1] > tmp) ? DATA[0:1] : tmp; // signed<br>compare<br>RETURN_DATA[0:1] = tmp.|
|167|S_ATOMIC_UMAX_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] -= (DATA[0:1] > tmp) ? DATA[0:1] : tmp; // unsigned<br>compare<br>RETURN_DATA[0:1] = tmp.|
|168|S_ATOMIC_AND_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] &= DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|



12.6. SMEM Instructions

116 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|169|S_ATOMIC_OR_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] |= DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|
|170|S_ATOMIC_XOR_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] ^= DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|
|171|S_ATOMIC_INC_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (tmp >= DATA[0:1]) ? 0 : tmp + 1; // unsigned<br>compare<br>RETURN_DATA[0:1] = tmp.|
|172|S_ATOMIC_DEC_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (tmp == 0 || tmp > DATA[0:1]) ? DATA[0:1] : tmp -<br>1; // unsigned compare<br>RETURN_DATA[0:1] = tmp.|



## **12.7. VOP2 Instructions**



Instructions in this format may use a 32-bit literal constant, DPP or SDWA which occurs immediately after the instruction.

|**Opcode**|**Name**|**Description**|
|---|---|---|
|0|V_CNDMASK_B32|D.u = (VCC[threadId] ? S1.u : S0.u).|
|||Conditional mask on each thread. In VOP3 the VCC source may be a<br>scalar GPR specified in S2.u.|
|1|V_ADD_F32|D.f = S0.f + S1.f.|
|||0.5ULP precision, denormals are supported.|
|2|V_SUB_F32|D.f = S0.f - S1.f.|
|3|V_SUBREV_F32|D.f = S1.f - S0.f.|
|4|V_FMAC_F64|D.f64 = S0.f64 * S1.f64 + D.f64.|
|5|V_MUL_F32|D.f = S0.f * S1.f.|
|||0.5ULP precision, denormals are supported.|
|6|V_MUL_I32_I24|D.i = S0.i[23:0] * S1.i[23:0].|
|7|V_MUL_HI_I32_I24|D.i = (S0.i[23:0] * S1.i[23:0])>>32.|
|8|V_MUL_U32_U24|D.u = S0.u[23:0] * S1.u[23:0].|
|9|V_MUL_HI_U32_U24|D.i = (S0.u[23:0] * S1.u[23:0])>>32.|



12.7. VOP2 Instructions

117 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|10|V_MIN_F32|if (IEEE_MODE && S0.f == sNaN)<br>D.f = Quiet(S0.f);<br>else if (IEEE_MODE && S1.f == sNaN)<br>D.f = Quiet(S1.f);<br>else if (S0.f == NaN)<br>D.f = S1.f;<br>else if (S1.f == NaN)<br>D.f = S0.f;<br>else if (S0.f == +0.0 && S1.f == -0.0)<br>D.f = S1.f;<br>else if (S0.f == -0.0 && S1.f == +0.0)<br>D.f = S0.f;<br>else<br>// Note: there's no IEEE special case here like there is for<br>V_MAX_F32.<br>D.f = (S0.f < S1.f ? S0.f : S1.f);<br>endif.|
|11|V_MAX_F32|if (IEEE_MODE && S0.f == sNaN)<br>D.f = Quiet(S0.f);<br>else if (IEEE_MODE && S1.f == sNaN)<br>D.f = Quiet(S1.f);<br>else if (S0.f == NaN)<br>D.f = S1.f;<br>else if (S1.f == NaN)<br>D.f = S0.f;<br>else if (S0.f == +0.0 && S1.f == -0.0)<br>D.f = S0.f;<br>else if (S0.f == -0.0 && S1.f == +0.0)<br>D.f = S1.f;<br>else if (IEEE_MODE)<br>D.f = (S0.f >= S1.f ? S0.f : S1.f);<br>else<br>D.f = (S0.f > S1.f ? S0.f : S1.f);<br>endif.|
|12|V_MIN_I32|D.i = (S0.i < S1.i ? S0.i : S1.i).|
|13|V_MAX_I32|D.i = (S0.i >= S1.i ? S0.i : S1.i).|
|14|V_MIN_U32|D.u = (S0.u < S1.u ? S0.u : S1.u).|
|15|V_MAX_U32|D.u = (S0.u >= S1.u ? S0.u : S1.u).|
|16|V_LSHRREV_B32|D.u = S1.u >> S0.u[4:0].|
|17|V_ASHRREV_I32|D.i = signext(S1.i) >> S0.i[4:0].|
|18|V_LSHLREV_B32|D.u = S1.u << S0.u[4:0].|
|19|V_AND_B32|D.u = S0.u & S1.u.<br>Input and output modifiers not supported.|
|20|V_OR_B32|D.u = S0.u | S1.u.<br>Input and output modifiers not supported.|



12.7. VOP2 Instructions

118 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|21|V_XOR_B32|D.u = S0.u ^ S1.u.|
|||Input and output modifiers not supported.|
|22|V_MAC_F32|D.f = S0.f * S1.f + D.f.|
|23|V_MADMK_F32|D.f = S0.f * K + S1.f. // K is a 32-bit literal constant.<br>This opcode cannot use the VOP3 encoding and cannot use input/output<br>modifiers.|
|24|V_MADAK_F32|D.f = S0.f * S1.f + K. // K is a 32-bit literal constant.<br>This opcode cannot use the VOP3 encoding and cannot use input/output<br>modifiers.|
|25|V_ADD_CO_U32|D.u = S0.u + S1.u;<br>VCC[threadId] = (S0.u + S1.u >= 0x100000000ULL ? 1 : 0).<br>// VCC is an UNSIGNED overflow/carry-out for V_ADDC_CO_U32.|
|||In VOP3 the VCC destination may be an arbitrary SGPR-pair.|
|26|V_SUB_CO_U32|D.u = S0.u - S1.u;<br>VCC[threadId] = (S1.u > S0.u ? 1 : 0).<br>// VCC is an UNSIGNED overflow/carry-out for V_SUBB_CO_U32.|
|||In VOP3 the VCC destination may be an arbitrary SGPR-pair.|
|27|V_SUBREV_CO_U32|D.u = S1.u - S0.u;<br>VCC[threadId] = (S0.u > S1.u ? 1 : 0).<br>// VCC is an UNSIGNED overflow/carry-out for V_SUBB_CO_U32.|
|||In VOP3 the VCC destination may be an arbitrary SGPR-pair.|
|28|V_ADDC_CO_U32|D.u = S0.u + S1.u + VCC[threadId];<br>VCC[threadId] = (S0.u + S1.u + VCC[threadId] >= 0x100000000ULL ? 1 :<br>0).<br>// VCC is an UNSIGNED overflow.<br>In VOP3 the VCC destination may be an arbitrary SGPR-pair, and the VCC<br>source comes from the SGPR-pair at S2.u.|
|29|V_SUBB_CO_U32|D.u = S0.u - S1.u - VCC[threadId];<br>VCC[threadId] = (S1.u + VCC[threadId] > S0.u ? 1 : 0).<br>// VCC is an UNSIGNED overflow.|
|||In VOP3 the VCC destination may be an arbitrary SGPR-pair, and the VCC<br>source comes from the SGPR-pair at S2.u.|
|30|V_SUBBREV_CO_U32|D.u = S1.u - S0.u - VCC[threadId];<br>VCC[threadId] = (S1.u + VCC[threadId] > S0.u ? 1 : 0).<br>// VCC is an UNSIGNED overflow.|
|||In VOP3 the VCC destination may be an arbitrary SGPR-pair, and the VCC<br>source comes from the SGPR-pair at S2.u.|
|31|V_ADD_F16|D.f16 = S0.f16 + S1.f16.|
|||Supports denormals, round mode, exception flags, saturation. 0.5ULP<br>precision, denormals are supported.|



12.7. VOP2 Instructions

119 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|32|V_SUB_F16|D.f16 = S0.f16 - S1.f16.<br>Supports denormals, round mode, exception flags, saturation.|
|33|V_SUBREV_F16|D.f16 = S1.f16 - S0.f16.<br>Supports denormals, round mode, exception flags, saturation.|
|34|V_MUL_F16|D.f16 = S0.f16 * S1.f16.<br>Supports denormals, round mode, exception flags, saturation. 0.5ULP<br>precision, denormals are supported.|
|35|V_MAC_F16|D.f16 = S0.f16 * S1.f16 + D.f16.<br>Supports round mode, exception flags, saturation.|
|36|V_MADMK_F16|D.f16 = S0.f16 * K.f16 + S1.f16.<br>// K is a 16-bit literal constant stored in the following literal<br>DWORD.<br>This opcode cannot use the VOP3 encoding and cannot use input/output<br>modifiers. Supports round mode, exception flags, saturation.|
|37|V_MADAK_F16|D.f16 = S0.f16 * S1.f16 + K.f16.<br>// K is a 16-bit literal constant stored in the following literal<br>DWORD.|
|||This opcode cannot use the VOP3 encoding and cannot use input/output<br>modifiers. Supports round mode, exception flags, saturation.|
|38|V_ADD_U16|D.u16 = S0.u16 + S1.u16.<br>Supports saturation (unsigned 16-bit integer domain).|
|39|V_SUB_U16|D.u16 = S0.u16 - S1.u16.|
|||Supports saturation (unsigned 16-bit integer domain).|
|40|V_SUBREV_U16|D.u16 = S1.u16 - S0.u16.|
|||Supports saturation (unsigned 16-bit integer domain).|
|41|V_MUL_LO_U16|D.u16 = S0.u16 * S1.u16.|
|||Supports saturation (unsigned 16-bit integer domain).|
|42|V_LSHLREV_B16|D.u[15:0] = S1.u[15:0] << S0.u[3:0].|
|43|V_LSHRREV_B16|D.u[15:0] = S1.u[15:0] >> S0.u[3:0].|
|44|V_ASHRREV_I16|D.i[15:0] = signext(S1.i[15:0]) >> S0.i[3:0].|



12.7. VOP2 Instructions

120 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|45|V_MAX_F16|if (IEEE_MODE && S0.f16 == sNaN)<br>D.f16 = Quiet(S0.f16);<br>else if (IEEE_MODE && S1.f16 == sNaN)<br>D.f16 = Quiet(S1.f16);<br>else if (S0.f16 == NaN)<br>D.f16 = S1.f16;<br>else if (S1.f16 == NaN)<br>D.f16 = S0.f16;<br>else if (S0.f16 == +0.0 && S1.f16 == -0.0)<br>D.f16 = S0.f16;<br>else if (S0.f16 == -0.0 && S1.f16 == +0.0)<br>D.f16 = S1.f16;<br>else if (IEEE_MODE)<br>D.f16 = (S0.f16 >= S1.f16 ? S0.f16 : S1.f16);<br>else<br>D.f16 = (S0.f16 > S1.f16 ? S0.f16 : S1.f16);<br>endif.<br>IEEE compliant. Supports denormals, round mode, exception flags,<br>saturation.|
|46|V_MIN_F16|if (IEEE_MODE && S0.f16 == sNaN)<br>D.f16 = Quiet(S0.f16);<br>else if (IEEE_MODE && S1.f16 == sNaN)<br>D.f16 = Quiet(S1.f16);<br>else if (S0.f16 == NaN)<br>D.f16 = S1.f16;<br>else if (S1.f16 == NaN)<br>D.f16 = S0.f16;<br>else if (S0.f16 == +0.0 && S1.f16 == -0.0)<br>D.f16 = S1.f16;<br>else if (S0.f16 == -0.0 && S1.f16 == +0.0)<br>D.f16 = S0.f16;<br>else<br>// Note: there's no IEEE special case here like there is for<br>V_MAX_F16.<br>D.f16 = (S0.f16 < S1.f16 ? S0.f16 : S1.f16);<br>endif.<br>IEEE compliant. Supports denormals, round mode, exception flags,<br>saturation.|
|47|V_MAX_U16|D.u16 = (S0.u16 >= S1.u16 ? S0.u16 : S1.u16).|
|48|V_MAX_I16|D.i16 = (S0.i16 >= S1.i16 ? S0.i16 : S1.i16).|
|49|V_MIN_U16|D.u16 = (S0.u16 < S1.u16 ? S0.u16 : S1.u16).|
|50|V_MIN_I16|D.i16 = (S0.i16 < S1.i16 ? S0.i16 : S1.i16).|
|51|V_LDEXP_F16|D.f16 = S0.f16 * (2 ** S1.i16).<br>Note that the S1 has a format of f16 since floating point literal<br>constants are interpreted as 16 bit value for this opcode|
|52|V_ADD_U32|D.u = S0.u + S1.u.|
|53|V_SUB_U32|D.u = S0.u - S1.u.|
|54|V_SUBREV_U32|D.u = S1.u - S0.u.|



12.7. VOP2 Instructions

121 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|55|V_DOT2C_F32_F16|D.f32 = S0.f16[0] * S1.f16[0] + S0.f16[1] * S1.f16[1] + D.f32.|
|||VOP2 version of V_DOT2_F32_F16 with 3rd src VGPR address is the vDst.|
|56|V_DOT2C_I32_I16|D.i32 = S0.i16[0] * S1.i16[0] + S0.i16[1] * S1.i16[1] + D.i32.|
|||VOP2 version of V_DOT2_I32_I16 with 3rd src VGPR address is the vDst.|
|57|V_DOT4C_I32_I8|D.i32 = S0.i8[0] * S1.i8[0] + S0.i8[1] * S1.i8[1] + S0.i8[2] *<br>S1.i8[2] + S0.i8[3] * S1.i8[3] + D.i32.|
|||VOP2 version of V_DOT4_I32_I8 with 3rd src VGPR address is the vDst.|
|58|V_DOT8C_I32_I4|D.i32 = S0.i4[0] * S1.i4[0] + S0.i4[1] * S1.i4[1] + S0.i4[2] *<br>S1.i4[2] + S0.i4[3] * S1.i4[3] + S0.i4[4] * S1.i4[4] + S0.i4[5] *<br>S1.i4[5] + S0.i4[6] * S1.i4[6] + S0.i4[7] * S1.i4[7] + D.i32.|
|||VOP2 version of V_DOT8_I32_I4 with 3rd src VGPR address is the vDst.|
|59|V_FMAC_F32|D.f32 = S0.f32 * S1.f32 + D.f32.|
|||VOP2 version of V_FMA_F32 with 3rd src VGPR address is the vDst.|
|60|V_PK_FMAC_F16|D.f16[0] = S0.f16[0] * S1.f16[0] + D.f16[0]; D.f16[1] = S0.f16[1]<br>* S1.f16[1] + D.f16[1]|
|||VOP2 version of V_PK_FMA_F16 with 3rd src VGPR address is the vDst.|
|61|V_XNOR_B32|D.b32 = S0.b32 XNOR S1.b32.|



Note: V_DOT2*_F32_F16 ops ignore the MODE.denormal setting and instead always flushes denormals to zero.

### **12.7.1. VOP2 using VOP3 encoding**

Instructions in this format may also be encoded as VOP3. This allows access to the extra control bits (e.g. ABS, OMOD) in exchange for not being able to use a literal constant. The VOP3 opcode is: VOP2 opcode + 0x100.





## **12.8. VOP1 Instructions**



12.8. VOP1 Instructions

122 of 267

"AMD Instinct MI200" Instruction Set Architecture



Instructions in this format may use a 32-bit literal constant, DPP or SDWA which occurs immediately after the instruction.

|**Opcode**|**Name**|**Description**|
|---|---|---|
|0|V_NOP|Do nothing.|
|1|V_MOV_B32|D.u = S0.u.|
|||Input and output modifiers not supported; this is an untyped<br>operation.|
|2|V_READFIRSTLANE_B<br>32|Copy one VGPR value to one SGPR. D = SGPR destination, S0 = source<br>data (VGPR# or M0 for lds direct access), Lane# =<br>FindFirst1fromLSB(exec) (Lane# = 0 if exec is zero). Ignores exec mask<br>for the access.<br>Input and output modifiers not supported; this is an untyped<br>operation.|
|3|V_CVT_I32_F64|D.i = (int)S0.d.<br>0.5ULP accuracy, out-of-range floating point values (including<br>infinity) saturate. NaN is converted to 0.<br>Generation of the INEXACT exception is controlled by the CLAMP bit.<br>INEXACT exceptions are enabled for this conversion iff CLAMP == 1.|
|4|V_CVT_F64_I32|D.d = (double)S0.i.<br>0ULP accuracy.|
|5|V_CVT_F32_I32|D.f = (float)S0.i.|
|||0.5ULP accuracy.|
|6|V_CVT_F32_U32|D.f = (float)S0.u.|
|||0.5ULP accuracy.|
|7|V_CVT_U32_F32|D.u = (unsigned)S0.f.<br>1ULP accuracy, out-of-range floating point values (including infinity)<br>saturate. NaN is converted to 0.<br>Generation of the INEXACT exception is controlled by the CLAMP bit.<br>INEXACT exceptions are enabled for this conversion iff CLAMP == 1.|
|8|V_CVT_I32_F32|D.i = (int)S0.f.<br>1ULP accuracy, out-of-range floating point values (including infinity)<br>saturate. NaN is converted to 0.<br>Generation of the INEXACT exception is controlled by the CLAMP bit.<br>INEXACT exceptions are enabled for this conversion iff CLAMP == 1.|
|10|V_CVT_F16_F32|D.f16 = flt32_to_flt16(S0.f).<br>0.5ULP accuracy, supports input modifiers and creates FP16 denormals<br>when appropriate.|
|11|V_CVT_F32_F16|D.f = flt16_to_flt32(S0.f16).<br>0ULP accuracy, FP16 denormal inputs are accepted.|



12.8. VOP1 Instructions

123 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|12|V_CVT_RPI_I32_F32|D.i = (int)floor(S0.f + 0.5).|
|||0.5ULP accuracy, denormals are supported.|
|13|V_CVT_FLR_I32_F32|D.i = (int)floor(S0.f).|
|||1ULP accuracy, denormals are supported.|
|14|V_CVT_OFF_F32_I4|4-bit signed int to 32-bit float. Used for interpolation in shader.<br>S0 Result<br>1000 -0.5f<br>1001 -0.4375f<br>1010 -0.375f<br>1011 -0.3125f<br>1100 -0.25f<br>1101 -0.1875f<br>1110 -0.125f<br>1111 -0.0625f<br>0000 0.0f<br>0001 0.0625f<br>0010 0.125f<br>0011 0.1875f<br>0100 0.25f<br>0101 0.3125f<br>0110 0.375f<br>0111 0.4375f|
|15|V_CVT_F32_F64|D.f = (float)S0.d.<br>0.5ULP accuracy, denormals are supported.|
|16|V_CVT_F64_F32|D.d = (double)S0.f.|
|||0ULP accuracy, denormals are supported.|
|17|V_CVT_F32_UBYTE0|D.f = (float)(S0.u[7:0]).|
|18|V_CVT_F32_UBYTE1|D.f = (float)(S0.u[15:8]).|
|19|V_CVT_F32_UBYTE2|D.f = (float)(S0.u[23:16]).|
|20|V_CVT_F32_UBYTE3|D.f = (float)(S0.u[31:24]).|
|21|V_CVT_U32_F64|D.u = (unsigned)S0.d.|
|||0.5ULP accuracy, out-of-range floating point values (including<br>infinity) saturate. NaN is converted to 0.<br>Generation of the INEXACT exception is controlled by the CLAMP bit.<br>INEXACT exceptions are enabled for this conversion iff CLAMP == 1.|
|22|V_CVT_F64_U32|D.d = (double)S0.u.|
|||0ULP accuracy.|
|23|V_TRUNC_F64|D.d = trunc(S0.d).<br>Return integer part of S0.d, round-to-zero semantics.|



12.8. VOP1 Instructions

124 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|24|V_CEIL_F64|D.d = trunc(S0.d);<br>if(S0.d > 0.0 && S0.d != D.d) then<br>D.d += 1.0;<br>endif.|
|||Round up to next whole integer.|
|25|V_RNDNE_F64|D.d = floor(S0.d + 0.5);<br>if(floor(S0.d) is even && fract(S0.d) == 0.5) then<br>D.d -= 1.0;<br>endif.|
|||Round-to-nearest-even semantics.|
|26|V_FLOOR_F64|D.d = trunc(S0.d);<br>if(S0.d < 0.0 && S0.d != D.d) then<br>D.d += -1.0;<br>endif.|
|||Round down to previous whole integer.|
|27|V_FRACT_F32|D.f = S0.f + -floor(S0.f).<br>Return fractional portion of a number. 0.5ULP accuracy, denormals are<br>accepted.|
|28|V_TRUNC_F32|D.f = trunc(S0.f).<br>Return integer part of S0.f, round-to-zero semantics.|
|29|V_CEIL_F32|D.f = trunc(S0.f);<br>if(S0.f > 0.0 && S0.f != D.f) then<br>D.f += 1.0;<br>endif.|
|||Round up to next whole integer.|
|30|V_RNDNE_F32|D.f = floor(S0.f + 0.5);<br>if(floor(S0.f) is even && fract(S0.f) == 0.5) then<br>D.f -= 1.0;<br>endif.|
|||Round-to-nearest-even semantics.|
|31|V_FLOOR_F32|D.f = trunc(S0.f);<br>if(S0.f < 0.0 && S0.f != D.f) then<br>D.f += -1.0;<br>endif.|
|||Round down to previous whole integer.|
|32|V_EXP_F32|D.f = pow(2.0, S0.f).|
|||Base 2 exponentiation. 1ULP accuracy, denormals are flushed.|
|||Examples:|
|||V_EXP_F32(0xff800000) => 0x00000000     // exp(-INF) = 0<br>V_EXP_F32(0x80000000) => 0x3f800000     // exp(-0.0) = 1<br>V_EXP_F32(0x7f800000) => 0x7f800000     // exp(+INF) = +INF|



12.8. VOP1 Instructions

125 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|33|V_LOG_F32|D.f = log2(S0.f).|
|||Base 2 logarithm. 1ULP accuracy, denormals are flushed.|
|||Examples:|
|||V_LOG_F32(0xff800000) => 0xffc00000     // log(-INF) = NAN|
|||V_LOG_F32(0xbf800000) => 0xffc00000     // log(-1.0) = NAN|
|||V_LOG_F32(0x80000000) => 0xff800000     // log(-0.0) = -INF|
|||V_LOG_F32(0x00000000) => 0xff800000     // log(+0.0) = -INF|
|||V_LOG_F32(0x3f800000) => 0x00000000     // log(+1.0) = 0|
|||V_LOG_F32(0x7f800000) => 0x7f800000     // log(+INF) = +INF|
|||You may safely ignore this paragraph. This paragraph is inserted to<br>ensure this specification fails legal scans, and for tracking<br>purposes. It has nothing to do with the V_LOG_F32 opcode.<br>TRACKJDS20151119, GLADIUS, MILOS, KRYPTOS, ANUBIS.|
|34|V_RCP_F32|D.f = 1.0 / S0.f.|
|||Reciprocal with IEEE rules and 1ULP accuracy. Accuracy converges to <<br>0.5ULP when using the Newton-Raphson method and 2 FMA operations.<br>Denormals are flushed.|
|||Examples:|
|||V_RCP_F32(0xff800000) => 0x80000000     // rcp(-INF) = -0|
|||V_RCP_F32(0xc0000000) => 0xbf000000     // rcp(-2.0) = -0.5|
|||V_RCP_F32(0x80000000) => 0xff800000     // rcp(-0.0) = -INF|
|||V_RCP_F32(0x00000000) => 0x7f800000     // rcp(+0.0) = +INF|
|||V_RCP_F32(0x7f800000) => 0x00000000     // rcp(+INF) = +0|
|35|V_RCP_IFLAG_F32|D.f = 1.0 / S0.f.|
|||Reciprocal intended for integer division, can raise integer<br>DIV_BY_ZERO exception but cannot raise floating-point exceptions. To<br>be used in an integer reciprocal macro by the compiler with one of the<br>following sequences:|
|||Unsigned:<br>CVT_F32_U32<br>RCP_IFLAG_F32<br>MUL_F32 (2**32 - 1)<br>CVT_U32_F32|
|||Signed:<br>CVT_F32_I32|
|||RCP_IFLAG_F32|
|||MUL_F32 (2**31 - 1)<br>CVT_I32_F32|



12.8. VOP1 Instructions

126 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|36|V_RSQ_F32|D.f = 1.0 / sqrt(S0.f).|
|||Reciprocal square root with IEEE rules. 1ULP accuracy, denormals are<br>flushed.|
|||Examples:|
|||V_RSQ_F32(0xff800000) => 0xffc00000     // rsq(-INF) = NAN|
|||V_RSQ_F32(0x80000000) => 0xff800000     // rsq(-0.0) = -INF|
|||V_RSQ_F32(0x00000000) => 0x7f800000     // rsq(+0.0) = +INF<br>|
|||V_RSQ_F32(0x40800000) => 0x3f000000     // rsq(+4.0) = +0.5<br>V_RSQ_F32(0x7f800000) => 0x00000000     // rsq(+INF) = +0|
|37|V_RCP_F64|D.d = 1.0 / S0.d.|
|||Reciprocal with IEEE rules. Precision is (2**29) ULP, and supports<br>denormals.|
|38|V_RSQ_F64|D.f16 = 1.0 / sqrt(S0.f16).|
|||Reciprocal square root with IEEE rules. Precision is (2**29) ULP, and<br>supports denormals.|
|39|V_SQRT_F32|D.f = sqrt(S0.f).|
|||Square root. 1ULP accuracy, denormals are flushed.|
|||Examples:|
|||V_SQRT_F32(0xff800000) => 0xffc00000     // sqrt(-INF) = NAN|
|||V_SQRT_F32(0x80000000) => 0x80000000     // sqrt(-0.0) = -0|
|||V_SQRT_F32(0x00000000) => 0x00000000     // sqrt(+0.0) = +0|
|||V_SQRT_F32(0x40800000) => 0x40000000     // sqrt(+4.0) = +2.0|
|||V_SQRT_F32(0x7f800000) => 0x7f800000     // sqrt(+INF) = +INF|
|40|V_SQRT_F64|D.d = sqrt(S0.d).|
|||Square root. Precision is (2**29) ULP, and supports denormals.|
|41|V_SIN_F32|D.f = sin(S0.f * 2 * PI).|
|||Trigonometric sine. Denormals are supported.|
|||Examples:|
|||V_SIN_F32(0xff800000) => 0xffc00000     // sin(-INF) = NAN|
|||V_SIN_F32(0xff7fffff) => 0x00000000     // -MaxFloat, finite|
|||V_SIN_F32(0x80000000) => 0x80000000     // sin(-0.0) = -0|
|||V_SIN_F32(0x3e800000) => 0x3f800000     // sin(0.25) = 1|
|||V_SIN_F32(0x7f800000) => 0xffc00000     // sin(+INF) = NAN|
|42|V_COS_F32|D.f = cos(S0.f * 2 * PI).|
|||Trigonometric cosine. Denormals are supported.|
|||Examples:|
|||V_COS_F32(0xff800000) => 0xffc00000     // cos(-INF) = NAN|
|||V_COS_F32(0xff7fffff) => 0x3f800000     // -MaxFloat, finite|
|||V_COS_F32(0x80000000) => 0x3f800000     // cos(-0.0) = 1|
|||V_COS_F32(0x3e800000) => 0x00000000     // cos(0.25) = 0|
|||<br>V_COS_F32(0x7f800000) => 0xffc00000     // cos(+INF) = NAN|



12.8. VOP1 Instructions

127 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|43|V_NOT_B32|D.u = ~S0.u.|
|||Bitwise negation. Input and output modifiers not supported.|
|44|V_BFREV_B32|D.u[31:0] = S0.u[0:31].<br>Bitfield reverse. Input and output modifiers not supported.|
|45|V_FFBH_U32|D.i = -1; // Set if no ones are found<br>for i in 0 ... 31 do<br>// Note: search is from the MSB<br>if S0.u[31 - i] == 1 then<br>D.i = i;<br>break for;<br>endif;<br>endfor.<br>Counts how many zeros before the first one starting from the MSB.<br>Returns -1 if there are no ones.<br>Examples:<br>V_FFBH_U32(0x00000000) => 0xffffffff<br>V_FFBH_U32(0x800000ff) => 0<br>V_FFBH_U32(0x100000ff) => 3<br>V_FFBH_U32(0x0000ffff) => 16<br>V_FFBH_U32(0x00000001) => 31|
|46|V_FFBL_B32|D.i = -1; // Set if no ones are found<br>for i in 0 ... 31 do // Search from LSB<br>if S0.u[i] == 1 then<br>D.i = i;<br>break for;<br>endif;<br>endfor.<br>Returns the bit position of the first one from the LSB, or -1 if there<br>are no ones.<br>Examples:<br>V_FFBL_B32(0x00000000) => 0xffffffff<br>V_FFBL_B32(0xff000001) => 0<br>V_FFBL_B32(0xff000008) => 3|
|||V_FFBL_B32(0xffff0000) => 16<br>V_FFBL_B32(0x80000000) => 31|



12.8. VOP1 Instructions

128 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|47|V_FFBH_I32|D.i = -1; // Set if all bits are the same<br>for i in 1 ... 31 do<br>// Note: search is from the MSB<br>if S0.i[31 - i] != S0.i[31] then<br>D.i = i;<br>break for;<br>endif;<br>endfor.<br>Counts how many bits in a row (from MSB to LSB) are the same as the<br>sign bit. Returns -1 if all bits are the same.<br>Examples:<br>V_FFBH_I32(0x00000000) => 0xffffffff<br>V_FFBH_I32(0x40000000) => 1<br>V_FFBH_I32(0x80000000) => 1<br>V_FFBH_I32(0x0fffffff) => 4<br>V_FFBH_I32(0xffff0000) => 16<br>V_FFBH_I32(0xfffffffe) => 31<br>V_FFBH_I32(0xffffffff) => 0xffffffff|
|48|V_FREXP_EXP_I32_F6<br>4|if(S0.d == +-INF || S0.d == NAN) then<br>D.i = 0;<br>else<br>D.i = TwosComplement(Exponent(S0.d) - 1023 + 1);<br>endif.<br>Returns exponent of single precision float input, such that S0.d =<br>significand * (2 ** exponent). See also V_FREXP_MANT_F64, which<br>returns the significand. See the C library function frexp() for more<br>information.|
|49|V_FREXP_MANT_F64|if(S0.d == +-INF || S0.d == NAN) then<br>D.d = S0.d;<br>else<br>D.d = Mantissa(S0.d);<br>endif.<br>Result range is in (-1.0,-0.5][0.5,1.0) in typical cases. Returns<br>binary significand of double precision float input, such that S0.d =<br>significand * (2 ** exponent). See also V_FREXP_EXP_I32_F64, which<br>returns integer exponent. See the C library function frexp() for more<br>information.|
|50|V_FRACT_F64|D.d = S0.d + -floor(S0.d).<br>Return fractional portion of a number. 0.5ULP accuracy, denormals are<br>accepted.|



12.8. VOP1 Instructions

129 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|51|V_FREXP_EXP_I32_F3<br>2|if(S0.f == +-INF || S0.f == NAN) then<br>D.i = 0;<br>else<br>D.i = TwosComplement(Exponent(S0.f) - 127 + 1);<br>endif.|
|||Returns exponent of single precision float input, such that S0.f =<br>significand * (2 ** exponent). See also V_FREXP_MANT_F32, which<br>returns the significand. See the C library function frexp() for more<br>information.|
|52|V_FREXP_MANT_F32|if(S0.f == +-INF || S0.f == NAN) then<br>D.f = S0.f;<br>else<br>D.f = Mantissa(S0.f);<br>endif.|
|||Result range is in (-1.0,-0.5][0.5,1.0) in typical cases. Returns<br>binary significand of single precision float input, such that S0.f =<br>significand * (2 ** exponent). See also V_FREXP_EXP_I32_F32, which<br>returns integer exponent. See the C library function frexp() for more<br>information.|
|53|V_CLREXCP|Clear wave's exception state in SIMD (SP).|



12.8. VOP1 Instructions

130 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|55|V_SCREEN_PARTITIO<br>N4SEB32|D.u = TABLE[S0.u[7:0]].|
||__||
|||TABLE:|
|||0x1, 0x3, 0x7, 0xf, 0x5, 0xf, 0xf, 0xf, 0x7, 0xf, 0xf, 0xf, 0xf,|
|||0xf, 0xf, 0xf,|
|||0xf, 0x2, 0x6, 0xe, 0xf, 0xa, 0xf, 0xf, 0xf, 0xb, 0xf, 0xf, 0xf,<br>|
|||0xf, 0xf, 0xf,|
|||0xd, 0xf, 0x4, 0xc, 0xf, 0xf, 0x5, 0xf, 0xf, 0xf, 0xd, 0xf, 0xf,|
|||0xf, 0xf, 0xf,|
|||<br>0x9, 0xb, 0xf, 0x8, 0xf, 0xf, 0xf, 0xa, 0xf, 0xf, 0xf, 0xe, 0xf,<br>0xf, 0xf, 0xf,|
|||0xf, 0xf, 0xf, 0xf, 0x4, 0xc, 0xd, 0xf, 0x6, 0xf, 0xf, 0xf, 0xe,<br>0xf, 0xf, 0xf,|
|||0xf, 0xf, 0xf, 0xf, 0xf, 0x8, 0x9, 0xb, 0xf, 0x9, 0x9, 0xf, 0xf,<br>0xd 0xf 0xf|
|||, , ,<br>0xf, 0xf, 0xf, 0xf, 0x7, 0xf, 0x1, 0x3, 0xf, 0xf, 0x9, 0xf, 0xf,<br>|
|||0xf, 0xb, 0xf,|
|||0xf, 0xf, 0xf, 0xf, 0x6, 0xe, 0xf, 0x2, 0x6, 0xf, 0xf, 0x6, 0xf,|
|||0xf, 0xf, 0x7,|
|||0xb, 0xf, 0xf, 0xf, 0xf, 0xf, 0xf, 0xf, 0x2, 0x3, 0xb, 0xf, 0xa,<br>0xf, 0xf, 0xf,|
|||0xf, 0x7, 0xf, 0xf, 0xf, 0xf, 0xf, 0xf, 0xf, 0x1, 0x9, 0xd, 0xf,<br>|
|||0x5, 0xf, 0xf,|
|||0xf, 0xf, 0xe, 0xf, 0xf, 0xf, 0xf, 0xf, 0xe, 0xf, 0x8, 0xc, 0xf,|
|||0xf 0xa 0xf|
|||, , ,<br>0xf, 0xf, 0xf, 0xd, 0xf, 0xf, 0xf, 0xf, 0x6, 0x7, 0xf, 0x4, 0xf,<br>0xf, 0xf, 0x5,|
|||0x9, 0xf, 0xf, 0xf, 0xd, 0xf, 0xf, 0xf, 0xf, 0xf, 0xf, 0xf, 0x8,|
|||0xc, 0xe, 0xf,|
|||0xf, 0x6, 0x6, 0xf, 0xf, 0xe, 0xf, 0xf, 0xf, 0xf, 0xf, 0xf, 0xf,<br>0x4 0x6 0x7|
|||, , ,<br>0xf, 0xf, 0x6, 0xf, 0xf, 0xf, 0x7, 0xf, 0xf, 0xf, 0xf, 0xf, 0xb,<br>|
|||0xf, 0x2, 0x3,<br>0x9, 0xf, 0xf, 0x9, 0xf, 0xf, 0xf, 0xb, 0xf, 0xf, 0xf, 0xf, 0x9,<br>0xd, 0xf, 0x1|
|||4SE version of LUT instruction for screen partitioning/filtering. This<br>opcode is intended to accelerate screen partitioning in the 4SE case<br>only. 2SE and 1SE cases use normal ALU instructions.|
|||This opcode returns a 4-bit bitmask indicating which SE backends are<br>covered by a rectangle from (x_min, y_min) to (x_max, y_max). With 32-<br>pixel tiles the SE for (x, y) is given by   { x[5] ^ y[6], y[5] ^ x[6]<br>}  . Using this formula we can determine which SEs are covered by a<br>larger rectangle.|
|||The primitive shader must perform the following operation before the<br>opcode is called.<br>1. Compute the bounding box of the primitive (x_min, y_min) (upper<br>left) and (x_max, y_max) (lower right), in pixels.|
|||2. Check for any extents that do not need to use the opcode --- if<br>((x_max/32 - x_min/32 >= 3)   OR   ((y_max/32 - y_min/32 >= 3)   (tile<br>size of 32) then all backends are covered.|
|||3. Call the opcode with this 8 bit select:   { x_min[6:5], y_min[6:5],<br>x_max[6:5], y_max[6:5] }  .|



~~12.8. VOP1 Instructions~~

~~131 of 267~~

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|57|V_CVT_F16_U16|D.f16 = uint16_to_flt16(S.u16).|
|||0.5ULP accuracy, supports denormals, rounding, exception flags and<br>saturation.|
|58|V_CVT_F16_I16|D.f16 = int16_to_flt16(S.i16).|
|||0.5ULP accuracy, supports denormals, rounding, exception flags and<br>saturation.|
|59|V_CVT_U16_F16|D.u16 = flt16_to_uint16(S.f16).|
|||1ULP accuracy, supports rounding, exception flags and saturation. FP16<br>denormals are accepted. Conversion is done with truncation.|
|||Generation of the INEXACT exception is controlled by the CLAMP bit.<br>INEXACT exceptions are enabled for this conversion iff CLAMP == 1.|
|60|V_CVT_I16_F16|D.i16 = flt16_to_int16(S.f16).|
|||1ULP accuracy, supports rounding, exception flags and saturation. FP16<br>denormals are accepted. Conversion is done with truncation.|
|||Generation of the INEXACT exception is controlled by the CLAMP bit.<br>INEXACT exceptions are enabled for this conversion iff CLAMP == 1.|
|61|V_RCP_F16|D.f16 = 1.0 / S0.f16.|
|||Reciprocal with IEEE rules and 0.51ULP accuracy.|
|||Examples:|
|||V_RCP_F16(0xfc00) => 0x8000     // rcp(-INF) = -0|
|||V_RCP_F16(0xc000) => 0xb800     // rcp(-2.0) = -0.5|
|||V_RCP_F16(0x8000) => 0xfc00     // rcp(-0.0) = -INF|
|||V_RCP_F16(0x0000) => 0x7c00     // rcp(+0.0) = +INF|
|||V_RCP_F16(0x7c00) => 0x0000     // rcp(+INF) = +0|
|62|V_SQRT_F16|D.f16 = sqrt(S0.f16).|
|||Square root. 0.51ULP accuracy, denormals are supported.|
|||Examples:|
|||V_SQRT_F16(0xfc00) => 0xfe00     // sqrt(-INF) = NAN|
|||V_SQRT_F16(0x8000) => 0x8000     // sqrt(-0.0) = -0|
|||V_SQRT_F16(0x0000) => 0x0000     // sqrt(+0.0) = +0|
|||V_SQRT_F16(0x4400) => 0x4000     // sqrt(+4.0) = +2.0|
|||<br>V_SQRT_F16(0x7c00) => 0x7c00     // sqrt(+INF) = +INF|
|63|V_RSQ_F16|D.f16 = 1.0 / sqrt(S0.f16).|
|||Reciprocal square root with IEEE rules. 0.51ULP accuracy, denormals<br>are supported.|
|||Examples:|
|||V_RSQ_F16(0xfc00) => 0xfe00     // rsq(-INF) = NAN|
|||V_RSQ_F16(0x8000) => 0xfc00     // rsq(-0.0) = -INF|
|||V_RSQ_F16(0x0000) => 0x7c00     // rsq(+0.0) = +INF|
|||V_RSQ_F16(0x4400) => 0x3800     // rsq(+4.0) = +0.5|
|||<br>V_RSQ_F16(0x7c00) => 0x0000     // rsq(+INF) = +0|



12.8. VOP1 Instructions

132 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|64|V_LOG_F16|D.f16 = log2(S0.f).|
|||Base 2 logarithm. 0.51ULP accuracy, denormals are supported.|
|||Examples:|
|||V_LOG_F16(0xfc00) => 0xfe00     // log(-INF) = NAN<br>|
|||V_LOG_F16(0xbc00) => 0xfe00     // log(-1.0) = NAN<br>|
|||V_LOG_F16(0x8000) => 0xfc00     // log(-0.0) = -INF|
|||V_LOG_F16(0x0000) => 0xfc00     // log(+0.0) = -INF<br>|
|||V_LOG_F16(0x3c00) => 0x0000     // log(+1.0) = 0<br>V_LOG_F16(0x7c00) => 0x7c00     // log(+INF) = +INF|
|65|V_EXP_F16|D.f16 = pow(2.0, S0.f16).|
|||Base 2 exponentiation. 0.51ULP accuracy, denormals are supported.|
|||Examples:|
|||V_EXP_F16(0xfc00) => 0x0000     // exp(-INF) = 0<br>V_EXP_F16(0x8000) => 0x3c00     // exp(-0.0) = 1<br>V_EXP_F16(0x7c00) => 0x7c00     // exp(+INF) = +INF|
|66|V_FREXP_MANT_F16|if(S0.f16 == +-INF || S0.f16 == NAN) then<br>D.f16 = S0.f16;<br>else<br>D.f16 = Mantissa(S0.f16);<br>endif.<br>Result range is in (-1.0,-0.5][0.5,1.0) in typical cases. Returns<br>binary significand of half precision float input, such that S0.f16 =<br>significand * (2 ** exponent). See also V_FREXP_EXP_I16_F16, which<br>returns integer exponent. See the C library function frexp() for more<br>information.|
|67|V_FREXP_EXP_I16_F1<br>6|if(S0.f16 == +-INF || S0.f16 == NAN) then<br>D.i = 0;<br>else<br>D.i = TwosComplement(Exponent(S0.f16) - 15 + 1);<br>endif.|
|||Returns exponent of half precision float input, such that S0.f16 =<br>significand * (2 ** exponent). See also V_FREXP_MANT_F16, which<br>returns the significand. See the C library function frexp() for more<br>information.|
|68|V_FLOOR_F16|D.f16 = trunc(S0.f16);<br>if(S0.f16 < 0.0f && S0.f16 != D.f16) then<br>D.f16 -= 1.0;<br>endif.|
|||Round down to previous whole integer.|
|69|V_CEIL_F16|D.f16 = trunc(S0.f16);<br>if(S0.f16 > 0.0f && S0.f16 != D.f16) then<br>D.f16 += 1.0;<br>endif.<br>Round up to next whole integer.|



12.8. VOP1 Instructions

133 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|70|V_TRUNC_F16|D.f16 = trunc(S0.f16).|
|||Return integer part of S0.f16, round-to-zero semantics.|
|71|V_RNDNE_F16|D.f16 = floor(S0.f16 + 0.5);<br>if(floor(S0.f16) is even && fract(S0.f16) == 0.5) then<br>D.f16 -= 1.0;<br>endif.|
|||Round-to-nearest-even semantics.|
|72|V_FRACT_F16|D.f16 = S0.f16 + -floor(S0.f16).|
|||Return fractional portion of a number. 0.5ULP accuracy, denormals are<br>accepted.|
|73|V_SIN_F16|D.f16 = sin(S0.f16 * 2 * PI).|
|||Trigonometric sine. Denormals are supported.|
|||Examples:|
|||V_SIN_F16(0xfc00) => 0xfe00     // sin(-INF) = NAN|
|||V_SIN_F16(0xfbff) => 0x0000     // Most negative finite FP16<br>|
|||V_SIN_F16(0x8000) => 0x8000     // sin(-0.0) = -0<br>V_SIN_F16(0x3400) => 0x3c00     // sin(0.25) = 1<br>V_SIN_F16(0x7bff) => 0x0000     // Most positive finite FP16<br>V_SIN_F16(0x7c00) => 0xfe00     // sin(+INF) = NAN|
|74|V_COS_F16|D.f16 = cos(S0.f16 * 2 * PI).|
|||Trigonometric cosine. Denormals are supported.|
|||Examples:|
|||V_COS_F16(0xfc00) => 0xfe00     // cos(-INF) = NAN|
|||V_COS_F16(0xfbff) => 0x3c00     // Most negative finite FP16|
|||V_COS_F16(0x8000) => 0x3c00     // cos(-0.0) = 1|
|||V_COS_F16(0x3400) => 0x0000     // cos(0.25) = 0|
|||V_COS_F16(0x7bff) => 0x3c00     // Most positive finite FP16<br>|
|||V_COS_F16(0x7c00) => 0xfe00     // cos(+INF) = NAN|
|75|V_EXP_LEGACY_F32|D.f = pow(2.0, S0.f).|
|||Power with legacy semantics.|
|76|V_LOG_LEGACY_F32|D.f = log2(S0.f).|
|||Base 2 logarithm with legacy semantics.|
|77|V_CVT_NORM_I16_F1<br>|D.i16 = flt16_to_snorm16(S.f16).|
||6|0.5ULP accuracy, supports rounding, exception flags and saturation,<br>denormals are supported.|
|78|V_CVT_NORM_U16_F<br>16|D.u16 = flt16_to_unorm16(S.f16).|
|||0.5ULP accuracy, supports rounding, exception flags and saturation,<br>denormals are supported.|
|79|V_SAT_PK_U8_I16|D.u32 = {16'b0, sat8(S.u[31:16]), sat8(S.u[15:0])}.|



12.8. VOP1 Instructions

134 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|81|V_SWAP_B32|tmp = D.u;<br>D.u = S0.u;<br>S0.u = tmp.|
|||Swap operands. Input and output modifiers not supported; this is an<br>untyped operation.|
|82|V_ACCVGPR_MOV_B3<br>2|Move one AccVGPR to another AccVGPR.|



### **12.8.1. VOP1 using VOP3 encoding**

Instructions in this format may also be encoded as VOP3. This allows access to the extra control bits (e.g. ABS, OMOD) in exchange for not being able to use a literal constant. The VOP3 opcode is: VOP2 opcode + 0x140.





## **12.9. VOPC Instructions**

The bitfield map for VOPC is:



where: SRC0  = First operand for instruction. VSRC1 = Second operand for instruction. OP    = Instructions. All VOPC instructions can alternatively be encoded in the VOP3A format.

Compare instructions perform the same compare operation on each lane (workItem or thread) using that lane’s private data, and producing a 1 bit result per lane into VCC or EXEC.

Instructions in this format may use a 32-bit literal constant which occurs immediately after the instruction.

Most compare instructions fall into one of two categories:

12.9. VOPC Instructions

135 of 267

"AMD Instinct MI200" Instruction Set Architecture



- Those which can use one of 16 compare operations (floating point types). "{COMPF}"

- Those which can use one of 8 compare operations (integer types). "{COMPI}"

The opcode number is such that for these the opcode number can be calculated from a base opcode number for the data type, plus an offset for the specific compare operation.

_Table 48. Instructions with Sixteen Compare Operations_

|**Compare Operation**|**Opcode Offset**|**Description**|
|---|---|---|
|F|0|D.u = 0|
|LT|1|D.u = (S0 < S1)|
|EQ|2|D.u = (S0 == S1)|
|LE|3|D.u = (S0 <= S1)|
|GT|4|D.u = (S0 > S1)|
|LG|5|D.u = (S0 <> S1)|
|GE|6|D.u = (S0 >= S1)|
|O|7|D.u = (!isNaN(S0) && !isNaN(S1))|
|U|8|D.u = (!isNaN(S0) || !isNaN(S1))|
|NGE|9|D.u = !(S0 >= S1)|
|NLG|10|D.u = !(S0 <> S1)|
|NGT|11|D.u = !(S0 > S1)|
|NLE|12|D.u = !(S0 <= S1)|
|NEQ|13|D.u = !(S0 == S1)|
|NLT|14|D.u = !(S0 < S1)|
|TRU|15|D.u = 1|



_Table 49. Instructions with Sixteen Compare Operations_

|**Instruction**|**Description**|**Hex Range**|
|---|---|---|
|V_CMP_{COMPF}_F16|16-bit float compare.|0x20 to 0x2F|
|V_CMPX_{COMPF}_F16|16-bit float compare. Also writes EXEC.|0x30 to 0x3F|
|V_CMP_{COMPF}_F32|32-bit float compare.|0x40 to 0x4F|
|V_CMPX_{COMPF}_F32|32-bit float compare. Also writes EXEC.|0x50 to 0x5F|
|V_CMPS_{COMPF}_F64|64-bit float compare.|0x60 to 0x6F|
|V_CMPSX_{COMPF}_F64|64-bit float compare. Also writes EXEC.|0x70 to 0x7F|



_Table 50. Instructions with Sixteen Compare Operations_

|**Compare Operation**|**Opcode Offset**|**Description**|
|---|---|---|
|F|0|D.u = 0|



12.9. VOPC Instructions

136 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Compare Operation**|**Opcode Offset**|**Description**|
|---|---|---|
|LT|1|D.u = (S0 < S1)|
|EQ|2|D.u = (S0 == S1)|
|LE|3|D.u = (S0 <= S1)|
|GT|4|D.u = (S0 > S1)|
|LG|5|D.u = (S0 <> S1)|
|GE|6|D.u = (S0 >= S1)|
|TRU|7|D.u = 1|



_Table 51. Instructions with Eight Compare Operations_

|**Instruction**|**Description**|**Hex Range**|
|---|---|---|
|V_CMP_{COMPI}_I16|16-bit signed integer compare.|0xA0 - 0xA7|
|V_CMP_{COMPI}_U16|16-bit signed integer compare. Also writes EXEC.|0xA8 - 0xAF|
|V_CMPX_{COMPI}_I16|16-bit unsigned integer compare.|0xB0 - 0xB7|
|V_CMPX_{COMPI}_U16|16-bit unsigned integer compare. Also writes EXEC.|0xB8 - 0xBF|
|V_CMP_{COMPI}_I32|32-bit signed integer compare.|0xC0 - 0xC7|
|V_CMP_{COMPI}_U32|32-bit signed integer compare. Also writes EXEC.|0xC8 - 0xCF|
|V_CMPX_{COMPI}_I32|32-bit unsigned integer compare.|0xD0 - 0xD7|
|V_CMPX_{COMPI}_U32|32-bit unsigned integer compare. Also writes EXEC.|0xD8 - 0xDF|
|V_CMP_{COMPI}_I64|64-bit signed integer compare.|0xE0 - 0xE7|
|V_CMP_{COMPI}_U64|64-bit signed integer compare. Also writes EXEC.|0xE8 - 0xEF|
|V_CMPX_{COMPI}_I64|64-bit unsigned integer compare.|0xF0 - 0xF7|
|V_CMPX_{COMPI}_U64|64-bit unsigned integer compare. Also writes EXEC.|0xF8 - 0xFF|



_Table 52. VOPC Compare Opcodes_

|**Opcode**|**Name**|**Description**|
|---|---|---|
|16|V_CMP_CLASS_F32|VCC = IEEE numeric class function specified in S1.u, performed on S0.f|
|||The function reports true if the floating point value is *any* of the<br>numeric types selected in S1.u according to the following list:|
|||S1.u[0] -- value is a signaling NaN.<br>S1.u[1] -- value is a quiet NaN.<br>S1.u[2] -- value is negative infinity.<br>S1.u[3] -- value is a negative normal value.<br>S1.u[4] -- value is a negative denormal value.<br>S1.u[5] -- value is negative zero.<br>S1.u[6] -- value is positive zero.|
|||S1.u[7] -- value is a positive denormal value.<br>S1.u[8] -- value is a positive normal value.<br>S1.u[9] -- value is positive infinity.|



12.9. VOPC Instructions

137 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|17|V_CMPX_CLASS_F32|EXEC = VCC = IEEE numeric class function specified in S1.u, performed<br>on S0.f|
|||The function reports true if the floating point value is *any* of the<br>numeric types selected in S1.u according to the following list:|
|||S1.u[0] -- value is a signaling NaN.<br>S1.u[1] -- value is a quiet NaN.<br>S1.u[2] -- value is negative infinity.<br>S1.u[3] -- value is a negative normal value.<br>S1.u[4] -- value is a negative denormal value.<br>S1.u[5] -- value is negative zero.<br>S1.u[6] -- value is positive zero.<br>S1.u[7] -- value is a positive denormal value.<br>S1.u[8] -- value is a positive normal value.<br>S1.u[9] -- value is positive infinity.|
|18|V_CMP_CLASS_F64|VCC = IEEE numeric class function specified in S1.u, performed on S0.d<br>The function reports true if the floating point value is *any* of the<br>numeric types selected in S1.u according to the following list:|
|||S1.u[0] -- value is a signaling NaN.<br>S1.u[1] -- value is a quiet NaN.<br>S1.u[2] -- value is negative infinity.<br>S1.u[3] -- value is a negative normal value.|
|||S1.u[4] -- value is a negative denormal value.<br>S1.u[5] -- value is negative zero.|
|||S1.u[6] -- value is positive zero.|
|||S1.u[7] -- value is a positive denormal value.<br>S1.u[8] -- value is a positive normal value.<br>S1.u[9] -- value is positive infinity.|
|19|V_CMPX_CLASS_F64|EXEC = VCC = IEEE numeric class function specified in S1.u, performed<br>on S0.d|
|||The function reports true if the floating point value is *any* of the<br>numeric types selected in S1.u according to the following list:|
|||S1.u[0] -- value is a signaling NaN.<br>S1.u[1] -- value is a quiet NaN.|
|||S1.u[2] -- value is negative infinity.|
|||S1.u[3] -- value is a negative normal value.|
|||S1.u[4] -- value is a negative denormal value.|
|||S1.u[5] -- value is negative zero.|
|||S1.u[6] -- value is positive zero.|
|||S1.u[7] -- value is a positive denormal value.|
|||S1.u[8] -- value is a positive normal value.<br>S1.u[9] -- value is positive infinity.|



12.9. VOPC Instructions

138 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|20|V_CMP_CLASS_F16|VCC = IEEE numeric class function specified in S1.u, performed on<br>S0.f16.<br>Note that the S1 has a format of f16 since floating point literal<br>constants are interpreted as 16 bit value for this opcode<br>The function reports true if the floating point value is *any* of the<br>numeric types selected in S1.u according to the following list:<br>S1.u[0] -- value is a signaling NaN.<br>S1.u[1] -- value is a quiet NaN.<br>S1.u[2] -- value is negative infinity.<br>S1.u[3] -- value is a negative normal value.<br>S1.u[4] -- value is a negative denormal value.<br>S1.u[5] -- value is negative zero.<br>S1.u[6] -- value is positive zero.<br>S1.u[7] -- value is a positive denormal value.<br>S1.u[8] -- value is a positive normal value.|
|||S1.u[9] -- value is positive infinity.|
|21|V_CMPX_CLASS_F16|EXEC = VCC = IEEE numeric class function specified in S1.u, performed<br>on S0.f16<br>Note that the S1 has a format of f16 since floating point literal<br>constants are interpreted as 16 bit value for this opcode|
|||The function reports true if the floating point value is *any* of the<br>numeric types selected in S1.u according to the following list:|
|||S1.u[0] -- value is a signaling NaN.<br>S1.u[1] -- value is a quiet NaN.<br>S1.u[2] -- value is negative infinity.<br>S1.u[3] -- value is a negative normal value.<br>S1.u[4] -- value is a negative denormal value.<br>S1.u[5] -- value is negative zero.<br>S1.u[6] -- value is positive zero.<br>S1.u[7] -- value is a positive denormal value.<br>S1.u[8] -- value is a positive normal value.<br>S1.u[9] -- value is positive infinity.|
|32|V_CMP_F_F16|D.u64[threadId] = 0.|
|33|V_CMP_LT_F16|D.u64[threadId] = (S0 < S1).|
|34|V_CMP_EQ_F16|D.u64[threadId] = (S0 == S1).|
|35|V_CMP_LE_F16|D.u64[threadId] = (S0 <= S1).|
|36|V_CMP_GT_F16|D.u64[threadId] = (S0 > S1).|
|37|V_CMP_LG_F16|D.u64[threadId] = (S0 <> S1).|
|38|V_CMP_GE_F16|D.u64[threadId] = (S0 >= S1).|
|39|V_CMP_O_F16|D.u64[threadId] = (!isNan(S0) && !isNan(S1)).|
|40|V_CMP_U_F16|D.u64[threadId] = (isNan(S0)  ||  isNan(S1)).|
|41|V_CMP_NGE_F16|D.u64[threadId] = !(S0 >= S1) // With NAN inputs this is not the<br>same operation as <.|
|42|V_CMP_NLG_F16|D.u64[threadId] = !(S0 <> S1) // With NAN inputs this is not the<br>same operation as ==.|



12.9. VOPC Instructions

139 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|43|V_CMP_NGT_F16|D.u64[threadId] = !(S0 > S1) // With NAN inputs this is not the same<br>operation as <=.|
|44|V_CMP_NLE_F16|D.u64[threadId] = !(S0 <= S1) // With NAN inputs this is not the<br>same operation as >.|
|45|V_CMP_NEQ_F16|D.u64[threadId] = !(S0 == S1) // With NAN inputs this is not the<br>same operation as !=.|
|46|V_CMP_NLT_F16|D.u64[threadId] = !(S0 < S1) // With NAN inputs this is not the same<br>operation as >=.|
|47|V_CMP_TRU_F16|D.u64[threadId] = 1.|
|48|V_CMPX_F_F16|EXEC[threadId] = D.u64[threadId] = 0.|
|49|V_CMPX_LT_F16|EXEC[threadId] = D.u64[threadId] = (S0 < S1).|
|50|V_CMPX_EQ_F16|EXEC[threadId] = D.u64[threadId] = (S0 == S1).|
|51|V_CMPX_LE_F16|EXEC[threadId] = D.u64[threadId] = (S0 <= S1).|
|52|V_CMPX_GT_F16|EXEC[threadId] = D.u64[threadId] = (S0 > S1).|
|53|V_CMPX_LG_F16|EXEC[threadId] = D.u64[threadId] = (S0 <> S1).|
|54|V_CMPX_GE_F16|EXEC[threadId] = D.u64[threadId] = (S0 >= S1).|
|55|V_CMPX_O_F16|EXEC[threadId] = D.u64[threadId] = (!isNan(S0) && !isNan(S1)).|
|56|V_CMPX_U_F16|EXEC[threadId] = D.u64[threadId] = (isNan(S0)  ||  isNan(S1)).|
|57|V_CMPX_NGE_F16|EXEC[threadId] = D.u64[threadId] = !(S0 >= S1) // With NAN inputs<br>this is not the same operation as <.|
|58|V_CMPX_NLG_F16|EXEC[threadId] = D.u64[threadId] = !(S0 <> S1) // With NAN inputs<br>this is not the same operation as ==.|
|59|V_CMPX_NGT_F16|EXEC[threadId] = D.u64[threadId] = !(S0 > S1) // With NAN inputs<br>this is not the same operation as <=.|
|60|V_CMPX_NLE_F16|EXEC[threadId] = D.u64[threadId] = !(S0 <= S1) // With NAN inputs<br>this is not the same operation as >.|
|61|V_CMPX_NEQ_F16|EXEC[threadId] = D.u64[threadId] = !(S0 == S1) // With NAN inputs<br>this is not the same operation as !=.|
|62|V_CMPX_NLT_F16|EXEC[threadId] = D.u64[threadId] = !(S0 < S1) // With NAN inputs<br>this is not the same operation as >=.|
|63|V_CMPX_TRU_F16|EXEC[threadId] = D.u64[threadId] = 1.|
|64|V_CMP_F_F32|D.u64[threadId] = 0.|
|65|V_CMP_LT_F32|D.u64[threadId] = (S0 < S1).|
|66|V_CMP_EQ_F32|D.u64[threadId] = (S0 == S1).|
|67|V_CMP_LE_F32|D.u64[threadId] = (S0 <= S1).|
|68|V_CMP_GT_F32|D.u64[threadId] = (S0 > S1).|
|69|V_CMP_LG_F32|D.u64[threadId] = (S0 <> S1).|
|70|V_CMP_GE_F32|D.u64[threadId] = (S0 >= S1).|
|71|V_CMP_O_F32|D.u64[threadId] = (!isNan(S0) && !isNan(S1)).|



12.9. VOPC Instructions

140 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|72|V_CMP_U_F32|D.u64[threadId] = (isNan(S0)  ||  isNan(S1)).|
|73|V_CMP_NGE_F32|D.u64[threadId] = !(S0 >= S1) // With NAN inputs this is not the<br>same operation as <.|
|74|V_CMP_NLG_F32|D.u64[threadId] = !(S0 <> S1) // With NAN inputs this is not the<br>same operation as ==.|
|75|V_CMP_NGT_F32|D.u64[threadId] = !(S0 > S1) // With NAN inputs this is not the same<br>operation as <=.|
|76|V_CMP_NLE_F32|D.u64[threadId] = !(S0 <= S1) // With NAN inputs this is not the<br>same operation as >.|
|77|V_CMP_NEQ_F32|D.u64[threadId] = !(S0 == S1) // With NAN inputs this is not the<br>same operation as !=.|
|78|V_CMP_NLT_F32|D.u64[threadId] = !(S0 < S1) // With NAN inputs this is not the same<br>operation as >=.|
|79|V_CMP_TRU_F32|D.u64[threadId] = 1.|
|80|V_CMPX_F_F32|EXEC[threadId] = D.u64[threadId] = 0.|
|81|V_CMPX_LT_F32|EXEC[threadId] = D.u64[threadId] = (S0 < S1).|
|82|V_CMPX_EQ_F32|EXEC[threadId] = D.u64[threadId] = (S0 == S1).|
|83|V_CMPX_LE_F32|EXEC[threadId] = D.u64[threadId] = (S0 <= S1).|
|84|V_CMPX_GT_F32|EXEC[threadId] = D.u64[threadId] = (S0 > S1).|
|85|V_CMPX_LG_F32|EXEC[threadId] = D.u64[threadId] = (S0 <> S1).|
|86|V_CMPX_GE_F32|EXEC[threadId] = D.u64[threadId] = (S0 >= S1).|
|87|V_CMPX_O_F32|EXEC[threadId] = D.u64[threadId] = (!isNan(S0) && !isNan(S1)).|
|88|V_CMPX_U_F32|EXEC[threadId] = D.u64[threadId] = (isNan(S0)  ||  isNan(S1)).|
|89|V_CMPX_NGE_F32|EXEC[threadId] = D.u64[threadId] = !(S0 >= S1) // With NAN inputs<br>this is not the same operation as <.|
|90|V_CMPX_NLG_F32|EXEC[threadId] = D.u64[threadId] = !(S0 <> S1) // With NAN inputs<br>this is not the same operation as ==.|
|91|V_CMPX_NGT_F32|EXEC[threadId] = D.u64[threadId] = !(S0 > S1) // With NAN inputs<br>this is not the same operation as <=.|
|92|V_CMPX_NLE_F32|EXEC[threadId] = D.u64[threadId] = !(S0 <= S1) // With NAN inputs<br>this is not the same operation as >.|
|93|V_CMPX_NEQ_F32|EXEC[threadId] = D.u64[threadId] = !(S0 == S1) // With NAN inputs<br>this is not the same operation as !=.|
|94|V_CMPX_NLT_F32|EXEC[threadId] = D.u64[threadId] = !(S0 < S1) // With NAN inputs<br>this is not the same operation as >=.|
|95|V_CMPX_TRU_F32|EXEC[threadId] = D.u64[threadId] = 1.|
|96|V_CMP_F_F64|D.u64[threadId] = 0.|
|97|V_CMP_LT_F64|D.u64[threadId] = (S0 < S1).|
|98|V_CMP_EQ_F64|D.u64[threadId] = (S0 == S1).|
|99|V_CMP_LE_F64|D.u64[threadId] = (S0 <= S1).|



12.9. VOPC Instructions

141 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|100|V_CMP_GT_F64|D.u64[threadId] = (S0 > S1).|
|101|V_CMP_LG_F64|D.u64[threadId] = (S0 <> S1).|
|102|V_CMP_GE_F64|D.u64[threadId] = (S0 >= S1).|
|103|V_CMP_O_F64|D.u64[threadId] = (!isNan(S0) && !isNan(S1)).|
|104|V_CMP_U_F64|D.u64[threadId] = (isNan(S0)  ||  isNan(S1)).|
|105|V_CMP_NGE_F64|D.u64[threadId] = !(S0 >= S1) // With NAN inputs this is not the<br>same operation as <.|
|106|V_CMP_NLG_F64|D.u64[threadId] = !(S0 <> S1) // With NAN inputs this is not the<br>same operation as ==.|
|107|V_CMP_NGT_F64|D.u64[threadId] = !(S0 > S1) // With NAN inputs this is not the same<br>operation as <=.|
|108|V_CMP_NLE_F64|D.u64[threadId] = !(S0 <= S1) // With NAN inputs this is not the<br>same operation as >.|
|109|V_CMP_NEQ_F64|D.u64[threadId] = !(S0 == S1) // With NAN inputs this is not the<br>same operation as !=.|
|110|V_CMP_NLT_F64|D.u64[threadId] = !(S0 < S1) // With NAN inputs this is not the same<br>operation as >=.|
|111|V_CMP_TRU_F64|D.u64[threadId] = 1.|
|112|V_CMPX_F_F64|EXEC[threadId] = D.u64[threadId] = 0.|
|113|V_CMPX_LT_F64|EXEC[threadId] = D.u64[threadId] = (S0 < S1).|
|114|V_CMPX_EQ_F64|EXEC[threadId] = D.u64[threadId] = (S0 == S1).|
|115|V_CMPX_LE_F64|EXEC[threadId] = D.u64[threadId] = (S0 <= S1).|
|116|V_CMPX_GT_F64|EXEC[threadId] = D.u64[threadId] = (S0 > S1).|
|117|V_CMPX_LG_F64|EXEC[threadId] = D.u64[threadId] = (S0 <> S1).|
|118|V_CMPX_GE_F64|EXEC[threadId] = D.u64[threadId] = (S0 >= S1).|
|119|V_CMPX_O_F64|EXEC[threadId] = D.u64[threadId] = (!isNan(S0) && !isNan(S1)).|
|120|V_CMPX_U_F64|EXEC[threadId] = D.u64[threadId] = (isNan(S0)  ||  isNan(S1)).|
|121|V_CMPX_NGE_F64|EXEC[threadId] = D.u64[threadId] = !(S0 >= S1) // With NAN inputs<br>this is not the same operation as <.|
|122|V_CMPX_NLG_F64|EXEC[threadId] = D.u64[threadId] = !(S0 <> S1) // With NAN inputs<br>this is not the same operation as ==.|
|123|V_CMPX_NGT_F64|EXEC[threadId] = D.u64[threadId] = !(S0 > S1) // With NAN inputs<br>this is not the same operation as <=.|
|124|V_CMPX_NLE_F64|EXEC[threadId] = D.u64[threadId] = !(S0 <= S1) // With NAN inputs<br>this is not the same operation as >.|
|125|V_CMPX_NEQ_F64|EXEC[threadId] = D.u64[threadId] = !(S0 == S1) // With NAN inputs<br>this is not the same operation as !=.|
|126|V_CMPX_NLT_F64|EXEC[threadId] = D.u64[threadId] = !(S0 < S1) // With NAN inputs<br>this is not the same operation as >=.|
|127|V_CMPX_TRU_F64|EXEC[threadId] = D.u64[threadId] = 1.|



12.9. VOPC Instructions

142 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|160|V_CMP_F_I16|D.u64[threadId] = 0.|
|161|V_CMP_LT_I16|D.u64[threadId] = (S0 < S1).|
|162|V_CMP_EQ_I16|D.u64[threadId] = (S0 == S1).|
|163|V_CMP_LE_I16|D.u64[threadId] = (S0 <= S1).|
|164|V_CMP_GT_I16|D.u64[threadId] = (S0 > S1).|
|165|V_CMP_NE_I16|D.u64[threadId] = (S0 <> S1).|
|166|V_CMP_GE_I16|D.u64[threadId] = (S0 >= S1).|
|167|V_CMP_T_I16|D.u64[threadId] = 1.|
|168|V_CMP_F_U16|D.u64[threadId] = 0.|
|169|V_CMP_LT_U16|D.u64[threadId] = (S0 < S1).|
|170|V_CMP_EQ_U16|D.u64[threadId] = (S0 == S1).|
|171|V_CMP_LE_U16|D.u64[threadId] = (S0 <= S1).|
|172|V_CMP_GT_U16|D.u64[threadId] = (S0 > S1).|
|173|V_CMP_NE_U16|D.u64[threadId] = (S0 <> S1).|
|174|V_CMP_GE_U16|D.u64[threadId] = (S0 >= S1).|
|175|V_CMP_T_U16|D.u64[threadId] = 1.|
|176|V_CMPX_F_I16|EXEC[threadId] = D.u64[threadId] = 0.|
|177|V_CMPX_LT_I16|EXEC[threadId] = D.u64[threadId] = (S0 < S1).|
|178|V_CMPX_EQ_I16|EXEC[threadId] = D.u64[threadId] = (S0 == S1).|
|179|V_CMPX_LE_I16|EXEC[threadId] = D.u64[threadId] = (S0 <= S1).|
|180|V_CMPX_GT_I16|EXEC[threadId] = D.u64[threadId] = (S0 > S1).|
|181|V_CMPX_NE_I16|EXEC[threadId] = D.u64[threadId] = (S0 <> S1).|
|182|V_CMPX_GE_I16|EXEC[threadId] = D.u64[threadId] = (S0 >= S1).|
|183|V_CMPX_T_I16|EXEC[threadId] = D.u64[threadId] = 1.|
|184|V_CMPX_F_U16|EXEC[threadId] = D.u64[threadId] = 0.|
|185|V_CMPX_LT_U16|EXEC[threadId] = D.u64[threadId] = (S0 < S1).|
|186|V_CMPX_EQ_U16|EXEC[threadId] = D.u64[threadId] = (S0 == S1).|
|187|V_CMPX_LE_U16|EXEC[threadId] = D.u64[threadId] = (S0 <= S1).|
|188|V_CMPX_GT_U16|EXEC[threadId] = D.u64[threadId] = (S0 > S1).|
|189|V_CMPX_NE_U16|EXEC[threadId] = D.u64[threadId] = (S0 <> S1).|
|190|V_CMPX_GE_U16|EXEC[threadId] = D.u64[threadId] = (S0 >= S1).|
|191|V_CMPX_T_U16|EXEC[threadId] = D.u64[threadId] = 1.|
|192|V_CMP_F_I32|D.u64[threadId] = 0.|
|193|V_CMP_LT_I32|D.u64[threadId] = (S0 < S1).|



12.9. VOPC Instructions

143 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|194|V_CMP_EQ_I32|D.u64[threadId] = (S0 == S1).|
|195|V_CMP_LE_I32|D.u64[threadId] = (S0 <= S1).|
|196|V_CMP_GT_I32|D.u64[threadId] = (S0 > S1).|
|197|V_CMP_NE_I32|D.u64[threadId] = (S0 <> S1).|
|198|V_CMP_GE_I32|D.u64[threadId] = (S0 >= S1).|
|199|V_CMP_T_I32|D.u64[threadId] = 1.|
|200|V_CMP_F_U32|D.u64[threadId] = 0.|
|201|V_CMP_LT_U32|D.u64[threadId] = (S0 < S1).|
|202|V_CMP_EQ_U32|D.u64[threadId] = (S0 == S1).|
|203|V_CMP_LE_U32|D.u64[threadId] = (S0 <= S1).|
|204|V_CMP_GT_U32|D.u64[threadId] = (S0 > S1).|
|205|V_CMP_NE_U32|D.u64[threadId] = (S0 <> S1).|
|206|V_CMP_GE_U32|D.u64[threadId] = (S0 >= S1).|
|207|V_CMP_T_U32|D.u64[threadId] = 1.|
|208|V_CMPX_F_I32|EXEC[threadId] = D.u64[threadId] = 0.|
|209|V_CMPX_LT_I32|EXEC[threadId] = D.u64[threadId] = (S0 < S1).|
|210|V_CMPX_EQ_I32|EXEC[threadId] = D.u64[threadId] = (S0 == S1).|
|211|V_CMPX_LE_I32|EXEC[threadId] = D.u64[threadId] = (S0 <= S1).|
|212|V_CMPX_GT_I32|EXEC[threadId] = D.u64[threadId] = (S0 > S1).|
|213|V_CMPX_NE_I32|EXEC[threadId] = D.u64[threadId] = (S0 <> S1).|
|214|V_CMPX_GE_I32|EXEC[threadId] = D.u64[threadId] = (S0 >= S1).|
|215|V_CMPX_T_I32|EXEC[threadId] = D.u64[threadId] = 1.|
|216|V_CMPX_F_U32|EXEC[threadId] = D.u64[threadId] = 0.|
|217|V_CMPX_LT_U32|EXEC[threadId] = D.u64[threadId] = (S0 < S1).|
|218|V_CMPX_EQ_U32|EXEC[threadId] = D.u64[threadId] = (S0 == S1).|
|219|V_CMPX_LE_U32|EXEC[threadId] = D.u64[threadId] = (S0 <= S1).|
|220|V_CMPX_GT_U32|EXEC[threadId] = D.u64[threadId] = (S0 > S1).|
|221|V_CMPX_NE_U32|EXEC[threadId] = D.u64[threadId] = (S0 <> S1).|
|222|V_CMPX_GE_U32|EXEC[threadId] = D.u64[threadId] = (S0 >= S1).|
|223|V_CMPX_T_U32|EXEC[threadId] = D.u64[threadId] = 1.|
|224|V_CMP_F_I64|D.u64[threadId] = 0.|
|225|V_CMP_LT_I64|D.u64[threadId] = (S0 < S1).|
|226|V_CMP_EQ_I64|D.u64[threadId] = (S0 == S1).|
|227|V_CMP_LE_I64|D.u64[threadId] = (S0 <= S1).|



12.9. VOPC Instructions

144 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|228|V_CMP_GT_I64|D.u64[threadId] = (S0 > S1).|
|229|V_CMP_NE_I64|D.u64[threadId] = (S0 <> S1).|
|230|V_CMP_GE_I64|D.u64[threadId] = (S0 >= S1).|
|231|V_CMP_T_I64|D.u64[threadId] = 1.|
|232|V_CMP_F_U64|D.u64[threadId] = 0.|
|233|V_CMP_LT_U64|D.u64[threadId] = (S0 < S1).|
|234|V_CMP_EQ_U64|D.u64[threadId] = (S0 == S1).|
|235|V_CMP_LE_U64|D.u64[threadId] = (S0 <= S1).|
|236|V_CMP_GT_U64|D.u64[threadId] = (S0 > S1).|
|237|V_CMP_NE_U64|D.u64[threadId] = (S0 <> S1).|
|238|V_CMP_GE_U64|D.u64[threadId] = (S0 >= S1).|
|239|V_CMP_T_U64|D.u64[threadId] = 1.|
|240|V_CMPX_F_I64|EXEC[threadId] = D.u64[threadId] = 0.|
|241|V_CMPX_LT_I64|EXEC[threadId] = D.u64[threadId] = (S0 < S1).|
|242|V_CMPX_EQ_I64|EXEC[threadId] = D.u64[threadId] = (S0 == S1).|
|243|V_CMPX_LE_I64|EXEC[threadId] = D.u64[threadId] = (S0 <= S1).|
|244|V_CMPX_GT_I64|EXEC[threadId] = D.u64[threadId] = (S0 > S1).|
|245|V_CMPX_NE_I64|EXEC[threadId] = D.u64[threadId] = (S0 <> S1).|
|246|V_CMPX_GE_I64|EXEC[threadId] = D.u64[threadId] = (S0 >= S1).|
|247|V_CMPX_T_I64|EXEC[threadId] = D.u64[threadId] = 1.|
|248|V_CMPX_F_U64|EXEC[threadId] = D.u64[threadId] = 0.|
|249|V_CMPX_LT_U64|EXEC[threadId] = D.u64[threadId] = (S0 < S1).|
|250|V_CMPX_EQ_U64|EXEC[threadId] = D.u64[threadId] = (S0 == S1).|
|251|V_CMPX_LE_U64|EXEC[threadId] = D.u64[threadId] = (S0 <= S1).|
|252|V_CMPX_GT_U64|EXEC[threadId] = D.u64[threadId] = (S0 > S1).|
|253|V_CMPX_NE_U64|EXEC[threadId] = D.u64[threadId] = (S0 <> S1).|
|254|V_CMPX_GE_U64|EXEC[threadId] = D.u64[threadId] = (S0 >= S1).|
|255|V_CMPX_T_U64|EXEC[threadId] = D.u64[threadId] = 1.|



### **12.9.1. VOPC using VOP3A encoding**

Instructions in this format may also be encoded as VOP3A. This allows access to the extra control bits (e.g. ABS, OMOD) in exchange for not being able to use a literal constant. The VOP3 opcode is: VOP2 opcode + 0x000.

12.9. VOPC Instructions

145 of 267

"AMD Instinct MI200" Instruction Set Architecture



When the CLAMP microcode bit is set to 1, these compare instructions signal an exception when either of the inputs is NaN. When CLAMP is set to zero, NaN does not signal an exception. The second eight VOPC instructions have {OP8} embedded in them. This refers to each of the compare operations listed below.



where:

VDST = Destination for instruction in the VGPR. ABS = Floating-point absolute value. CLMP = Clamp output. OP = Instructions. SRC0 = First operand for instruction. SRC1 = Second operand for instruction. SRC2 = Third operand for instruction. Unused in VOPC instructions. OMOD = Output modifier for instruction. Unused in VOPC instructions. NEG = Floating-point negation.

## **12.10. VOP3P Instructions**





|**Opcode**|**Name**|**Description**||
|---|---|---|---|
|0|V_PK_MAD_I16|D.i[31:16]<br>S0.i[15:0]|= S0.i[31:16] * S1.i[31:16] + S2.i[31:16] . D.i[15:0]  =<br>* S1.i[15:0]  + S2.i[15:0]  .|
|1|V_PK_MUL_LO_U16|D.u[31:16]<br>S1.u[15:0]|= S0.u[31:16] * S1.u[31:16] . D.u[15:0]  = S0.u[15:0]  *<br>.|
|2|V_PK_ADD_I16|D.i[31:16]<br>S1.i[15:0]|= S0.i[31:16] + S1.i[31:16] . D.i[15:0]  = S0.i[15:0]  +<br>.|
|3|V_PK_SUB_I16|D.i[31:16]<br>S1.i[15:0]|= S0.i[31:16] - S1.i[31:16] . D.i[15:0]  = S0.i[15:0]  -<br>.|
|4|V_PK_LSHLREV_B16|D.u[31:16]<br>S0.u[3:0]|= S1.u[31:16] << S0.u[19:16] . D.u[15:0]  = S1.u[15:0]  <<<br>.|
|5|V_PK_LSHRREV_B16|D.u[31:16]<br>S0.u[3:0]|= S1.u[31:16] >> S0.u[19:16] . D.u[15:0]  = S1.u[15:0]  >><br>.|
|6|V_PK_ASHRREV_I16|D.i[31:16]<br>S0.i[3:0]|= S1.i[31:16] >> S0.i[19:16] . D.i[15:0]  = S1.i[15:0]  >><br>.|



12.10. VOP3P Instructions

146 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|7|V_PK_MAX_I16|D.i[31:16] = (S0.i[31:16] >= S1.i[31:16]) ? S0.i[31:16] : S1.i[31:16]<br>. D.i[15:0]  = (S0.i[15:0]  >= S1.i[15:0])  ? S0.i[15:0]  : S1.i[15:0]<br>.|
|8|V_PK_MIN_I16|D.i[31:16] = (S0.i[31:16] < S1.i[31:16]) ? S0.i[31:16] : S1.i[31:16]<br>. D.i[15:0]  = (S0.i[15:0]  < S1.i[15:0])  ? S0.i[15:0]  : S1.i[15:0]|
|9|V_PK_MAD_U16|D.u[31:16] = S0.u[31:16] * S1.u[31:16] + S2.u[31:16] . D.u[15:0]  =<br>S0.u[15:0]  * S1.u[15:0]  + S2.u[15:0]  .|
|10|V_PK_ADD_U16|D.u[31:16] = S0.u[31:16] + S1.u[31:16] . D.u[15:0]  = S0.u[15:0]  +<br>S1.u[15:0]  .|
|11|V_PK_SUB_U16|D.u[31:16] = S0.u[31:16] - S1.u[31:16] . D.u[15:0]  = S0.u[15:0]  -<br>S1.u[15:0]  .|
|12|V_PK_MAX_U16|D.u[31:16] = (S0.u[31:16] >= S1.u[31:16]) ? S0.u[31:16] : S1.u[31:16]<br>. D.u[15:0]  = (S0.u[15:0]  >= S1.u[15:0])  ? S0.u[15:0]  : S1.u[15:0]<br>.|
|13|V_PK_MIN_U16|D.u[31:16] = (S0.u[31:16] < S1.u[31:16]) ? S0.u[31:16] : S1.u[31:16]<br>. D.u[15:0]  = (S0.u[15:0]  < S1.u[15:0])  ? S0.u[15:0]  : S1.u[15:0]<br>.|
|14|V_PK_FMA_F16|D.f[31:16] = S0.f[31:16] * S1.f[31:16] + S2.f[31:16] . D.f[15:0]  =<br>S0.f[15:0]  * S1.f[15:0]  + S2.f[15:0]  .<br>Fused half-precision multiply add.|
|15|V_PK_ADD_F16|D.f[31:16] = S0.f[31:16] + S1.f[31:16] . D.f[15:0]  = S0.f[15:0]  +<br>S1.f[15:0]  .|
|16|V_PK_MUL_F16|D.f[31:16] = S0.f[31:16] * S1.f[31:16] . D.f[15:0]  = S0.f[15:0]  *<br>S1.f[15:0]  .|
|17|V_PK_MIN_F16|D.f[31:16] = min(S0.f[31:16], S1.f[31:16]) . D.f[15:0]  =<br>min(S0.f[15:0], S1.u[15:0]) .|
|18|V_PK_MAX_F16|D.f[31:16] = max(S0.f[31:16], S1.f[31:16]) . D.f[15:0]  =<br>max(S0.f[15:0], S1.f[15:0]) .|
|32|V_MAD_MIX_F32|D.f[31:0] = S0.f * S1.f + S2.f.  Size and location of S0, S1 and S2<br>controlled by OPSEL: 0=src[31:0], 1=src[31:0], 2=src[15:0],<br>3=src[31:16]. Also, for MAD_MIX, the NEG_HI field acts instead as an<br>absolute-value modifier.|
|33|V_MAD_MIXLO_F16|D.f[15:0] = S0.f * S1.f + S2.f.  Size and location of S0, S1 and S2<br>controlled by OPSEL: 0=src[31:0], 1=src[31:0], 2=src[15:0],<br>3=src[31:16]. Also, for MAD_MIX, the NEG_HI field acts instead as an<br>absolute-value modifier.|
|34|V_MAD_MIXHI_F16|D.f[31:16] = S0.f * S1.f + S2.f.  Size and location of S0, S1 and S2<br>controlled by OPSEL: 0=src[31:0], 1=src[31:0], 2=src[15:0],<br>3=src[31:16]. Also, for MAD_MIX, the NEG_HI field acts instead as an<br>absolute-value modifier.|
|35|V_DOT2_F32_F16|D.f32 = S0.f16[0] * S1.f16[0] + S0.f16[1] * S1.f16[1] + S2.f32|
|38|V_DOT2_I32_I16|D.i32 = S0.i16[0] * S1.i16[0] + S0.i16[1] * S1.i16[1] + S2.i32|
|39|V_DOT2_U32_U16|D.u32 = S0.u16[0] * S1.u16[0] + S0.u16[1] * S1.u16[1] + S2.u32|
|40|V_DOT4_I32_I8|D.i32 = S0.i8[0] * S1.i8[0] + S0.i8[1] * S1.i8[1] + S0.i8[2] *<br>S1.i8[2] + S0.i8[3] * S1.i8[3] + S2.i32|



12.10. VOP3P Instructions

147 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|41|V_DOT4_U32_U8|D.u32 = S0.u8[0] * S1.u8[0] + S0.u8[1] * S1.u8[1] + S0.u8[2] *<br>S1.u8[2] + S0.u8[3] * S1.u8[3] + S2.u32|
|42|V_DOT8_I32_I4|D.i32 = S0.i4[0] * S1.i4[0] + S0.i4[1] * S1.i4[1] + S0.i4[2] *<br>S1.i4[2] + S0.i4[3] * S1.i4[3] + S0.i4[4] * S1.i4[4] + S0.i4[5] *<br>S1.i4[5] + S0.i4[6] * S1.i4[6] + S0.i4[7] * S1.i4[7] + S2.i32|
|43|V_DOT8_U32_U4|D.u32 = S0.u4[0] * S1.u4[0] + S0.u4[1] * S1.u4[1] + S0.u4[2] *<br>S1.u4[2] + S0.u4[3] * S1.u4[3] + S0.u4[4] * S1.u4[4] + S0.u4[5] *<br>S1.u4[5] + S0.u4[6] * S1.u4[6] + S0.u4[7] * S1.u4[7] + S2.u32|
|48|V_PK_FMA_F32|D.f[63:32] = S0.f[63:32] * S1.f[63:32] + S2.f[63:32] . D.f[31:0]  =<br>S0.f[31:0]  * S1.f[31:0]  + S2.f[31:0]  .|
|||Packed single precision FMA_F32 instruction.|
|49|V_PK_MUL_F32|D.f[63:32] = S0.f[63:32] * S1.f[63:32] . D.f[31:0]  = S0.f[31:0]  *<br>S1.f[31:0]  .<br>Packed single precision MUL_F32 instruction.|
|50|V_PK_ADD_F32|D.f[63:32] = S0.f[63:32] + S1.f[63:32] . D.f[31:0]  = S0.f[31:0]  +<br>S1.f[31:0]  .|
|||Packed single precision ADD_F32 instruction.|
|51|V_PK_MOV_B32|D.u[63:32] = S1.u[31:0]; D.u[31:0] = S0.u[31:0].<br>Packed single precision MOV_B32 instruction.|
|64|V_MFMA_F32_32X32X<br>1F32|D(32x32F32) = A(32x1F32) x B(1x32F32) + C(32x32F32), 2 Blocks, 16<br>pass, srcA/srcB one archVgpr, srcC/D 32 accVGPR|
|65|V_MFMA_F32_16X16X<br>1F32|D(16x16F32) = A(16x1F32) x B(1x16F32) + C(16x16F32), 4 Blocks, 8<br>pass, srcA/srcB one archVgpr, srcC/D 16 accVGPR|
|66|V_MFMA_F32_4X4X1F<br>32|D(4x4F32) = A(4x1F32) x B(1x4F32) + C(4x4F32), 16 Blocks, 2 pass,<br>srcA/srcB one archVgpr, srcC/D 4 accVGPR|
|68|V_MFMA_F32_32X32X<br>2F32|D(32x32F32) = A(32x2F32) x B(2x32F32) + C(32x32F32), 1 Blocks, 16<br>pass, srcA/srcB one archVgpr, srcC/D 16 accVGPR|
|69|V_MFMA_F32_16X16X<br>4F32|D(16x16F32) = A(16x4F32) x B(4x16F32) + C(16x16F32), 1 Blocks, 8<br>pass, srcA/srcB one archVgpr, srcC/D 4 accVGPR|
|72|V_MFMA_F32_32X32X<br>4F16|D(32x32F32) = A(32x1F16) x B(1x32F16) + C(32x32F32), 2 Blocks, 16<br>pass, srcA/srcB 2 archVgpr, srcC/D 32 accVGPR|
|73|V_MFMA_F32_16X16X<br>4F16|D(16x16F32) = A(16x4F16) x B(4x16F16) + C(16x16F32), 4 Blocks, 8<br>pass, srcA/srcB 2 archVgpr, srcC/D 16 accVGPR|
|74|V_MFMA_F32_4X4X4F<br>16|D(4x4F32) = A(4x4F16) x B(4x4F16) + C(4x4F32), 16 Blocks, 2 pass,<br>srcA/srcB 2 archVgpr, srcC/D 4 accVGPR|
|76|V_MFMA_F32_32X32X<br>8F16|D(32x32F32) = A(32x8F16) x B(8x32F16) + C(32x32F32), 1 Blocks, 16<br>pass, srcA/srcB 2 archVgpr, srcC/D 16 accVGPR|
|77|V_MFMA_F32_16X16X<br>16F16|D(16x16F32) = A(16x16F16) x B(16x16F16) + C(16x16F32), 1 Blocks, 8<br>pass, srcA/srcB 2 archVgpr, srcC/D 4 accVGPR|
|80|V_MFMA_I32_32X32X4<br>I8|D(32x32I32) = A(32x1I8) x B(1x32I8) + C(32x32I32), 2 Blocks, 16 pass,<br>srcA/srcB 1 archVgpr, srcC/D 32 accVGPR|



12.10. VOP3P Instructions

148 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|81|V_MFMA_I32_16X16X4<br>I8|D(16x16I32) = A(16x4I8) x B(4x16I8) + C(16x16I32), 4 Blocks, 8 pass,<br>srcA/srcB 1 archVgpr, srcC/D 16 accVGPR|
|82|V_MFMA_I32_4X4X4I8|D(4x4I32) = A(4x4I8) x B(4x4I8) + C(4x4I32), 16 Blocks, 2 pass,<br>srcA/srcB 1 archVgpr, srcC/D 4 accVGPR|
|84|V_MFMA_I32_32X32X8<br>I8|D(32x32I32) = A(32x8I8) x B(8x32I8) + C(32x32I32), 1 Blocks, 16 pass,<br>srcA/srcB 1 archVgpr, srcC/D 16 accVGPR|
|85|V_MFMA_I32_16X16X1<br>6I8|D(16x16I32) = A(16x16I8) x B(16x16I8) + C(16x16I32), 1 Blocks, 8<br>pass, srcA/srcB 1 archVgpr, srcC/D 4 accVGPR|
|88|V_ACCVGPR_READ|move one AccVGPR to ArchVGPR, one source operand|
|89|V_ACCVGPR_WRITE|move one ArchVGPR to AccVGPR, one source operand|
|99|V_MFMA_F32_32X32X<br>4BF16_1K|D(32x32F32) = A(32x4BF16) x B(4x32BF16) + C(32x32F32), 2 Blocks, 16<br>pass, srcA/srcB 2 Vgpr, srcC/D 32 VGPR|
|100|V_MFMA_F32_16X16X<br>4BF16_1K|D(16x16F32) = A(16x4BF16) x B(4x16BF16) + C(16x16F32), 4 Blocks, 8<br>pass, srcA/srcB 2 Vgpr, srcC/D 16 VGPR|
|101|V_MFMA_F32_4X4X4B<br>F16_1K|D(4x4F32) = A(4x4BF16) x B(4x4BF16) + C(4x4F32), 16 Blocks, 2 pass,<br>srcA/srcB 2 Vgpr, srcC/D 4 VGPR|
|102|V_MFMA_F32_32X32X<br>8BF16_1K|D(32x32F32) = A(32x8BF16) x B(8x32BF16) + C(32x32F32), 1 Blocks, 16<br>pass, srcA/srcB 2 Vgpr, srcC/D 16 VGPR|
|103|V_MFMA_F32_16X16X<br>16BF16_1K|D(16x16F32) = A(16x16BF16) x B(16x16BF16) + C(16x16F32), 1 Blocks, 8<br>pass, srcA/srcB 2 Vgpr, srcC/D 4 VGPR|
|104|V_MFMA_F32_32X32X<br>2BF16|D(32x32F32) = A(32x2BF16) x B(2x32BF16) + C(32x32F32), 2 Blocks, 16<br>pass, srcA/srcB one archVgpr, srcC/D 32 accVGPR|
|105|V_MFMA_F32_16X16X<br>2BF16|D(16x16F32) = A(16x2BF16) x B(2x16BF16) + C(16x16F32), 4 Blocks, 8<br>pass, srcA/srcB one archVgpr, srcC/D 16 accVGPR|
|107|V_MFMA_F32_4X4X2B<br>F16|D(4x4F32) = A(4x2BF16) x B(2x4BF16) + C(4x4F32), 16 Blocks, 2 pass,<br>srcA/srcB one archVgpr, srcC/D 4 accVGPR|
|108|V_MFMA_F32_32X32X<br>4BF16|D(32x32F32) = A(32x4BF16) x B(4x32BF16) + C(32x32F32), 1 Blocks, 16<br>pass, srcA/srcB one archVgpr, srcC/D 16 accVGPR|
|109|V_MFMA_F32_16X16X<br>8BF16|D(16x16F32) = A(16x8BF16) x B(8x16BF16) + C(16x16F32), 1 Blocks, 8<br>pass, srcA/srcB one archVgpr, srcC/D 4 accVGPR|
|110|V_MFMA_F64_16X16X<br>4F64|D(16x16F64) = A(16x4F64) x B(4x16F64) + C(16x16F64), 1 Blocks, 8<br>pass, srcA/srcB 2 VGPR, srcC/D 8 VGPR|
|111|V_MFMA_F64_4X4X4F<br>64|D(4x4F64) = A(4x4F64) x B(4x4F64) + C(4x4F64), 4 Blocks, 4 pass,<br>srcA/srcB 2 VGPR, srcC/D 2 VGPR|



## **12.11. VOP3A & VOP3B Instructions**

VOP3 instructions use one of two encodings:

12.11. VOP3A & VOP3B Instructions

149 of 267

"AMD Instinct MI200" Instruction Set Architecture







**VOP3B** this encoding allows specifying a unique scalar destination, and is used only for: V_ADD_CO_U32 V_SUB_CO_U32 V_SUBREV_CO_U32 V_ADDC_CO_U32 V_SUBB_CO_U32 V_SUBBREV_CO_U32 V_DIV_SCALE_F32 V_DIV_SCALE_F64 V_MAD_U64_U32 V_MAD_I64_I32

#### **VOP3A** all other VALU instructions use this encoding

|**Opcode**|**Name**|**Description**|
|---|---|---|
|448|V_MAD_LEGACY_F3<br>2|D.f = S0.f * S1.f + S2.f. // DX9 rules, 0.0 * x = 0.0|
|449|V_MAD_F32|D.f = S0.f * S1.f + S2.f.|
|||1ULP accuracy, denormals are flushed.|
|450|V_MAD_I32_I24|D.i = S0.i[23:0] * S1.i[23:0] + S2.i.|
|451|V_MAD_U32_U24|D.u = S0.u[23:0] * S1.u[23:0] + S2.u.|
|452|V_CUBEID_F32|D.f = cubemap face ID ({0.0, 1.0, ..., 5.0}). XYZ coordinate is given<br>in (S0.f, S1.f, S2.f).<br>Cubemap Face ID determination. Result is a floating point face ID.<br>S0.f = x<br>S1.f = y<br>S2.f = z<br>If (Abs(S2.f) >= Abs(S0.f) && Abs(S2.f) >= Abs(S1.f))<br>If (S2.f < 0) D.f = 5.0<br>Else D.f = 4.0<br>Else if (Abs(S1.f) >= Abs(S0.f))<br>If (S1.f < 0) D.f = 3.0<br>Else D.f = 2.0<br>Else<br>If (S0.f < 0) D.f = 1.0<br>Else D.f = 0.0|



12.11. VOP3A & VOP3B Instructions

150 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|453|V_CUBESC_F32|D.f = cubemap S coordinate. XYZ coordinate is given in (S0.f, S1.f,<br>S2.f).<br>S0.f = x<br>S1.f = y<br>S2.f = z<br>If (Abs(S2.f) >= Abs(S0.f) && Abs(S2.f) >= Abs(S1.f))<br>If (S2.f < 0) D.f = -S0.f<br>Else D.f = S0.f<br>Else if (Abs(S1.f) >= Abs(S0.f))<br>D.f = S0.f<br>Else<br>If (S0.f < 0) D.f = S2.f<br>Else D.f = -S2.f|
|454|V_CUBETC_F32|D.f = cubemap T coordinate. XYZ coordinate is given in (S0.f, S1.f,<br>S2.f).<br>S0.f = x<br>S1.f = y<br>S2.f = z<br>If (Abs(S2.f) >= Abs(S0.f) && Abs(S2.f) >= Abs(S1.f))<br>D.f = -S1.f<br>Else if (Abs(S1.f) >= Abs(S0.f))<br>If (S1.f < 0) D.f = -S2.f<br>Else D.f = S2.f<br>Else<br>D.f = -S1.f|
|455|V_CUBEMA_F32|D.f = 2.0 * cubemap major axis. XYZ coordinate is given in (S0.f,<br>S1.f, S2.f).<br>S0.f = x<br>S1.f = y<br>S2.f = z<br>If (Abs(S2.f) >= Abs(S0.f) && Abs(S2.f) >= Abs(S1.f))<br>D.f = 2.0*S2.f<br>Else if (Abs(S1.f) >= Abs(S0.f))<br>D.f = 2.0 * S1.f<br>Else<br>D.f = 2.0 * S0.f|
|456|V_BFE_U32|D.u = (S0.u >> S1.u[4:0]) & ((1 << S2.u[4:0]) - 1).<br>Bitfield extract with S0 = data, S1 = field_offset, S2 = field_width.|
|457|V_BFE_I32|D.i = (S0.i >> S1.u[4:0]) & ((1 << S2.u[4:0]) - 1).<br>Bitfield extract with S0 = data, S1 = field_offset, S2 = field_width.|
|458|V_BFI_B32|D.u = (S0.u & S1.u) | (~S0.u & S2.u).<br>Bitfield insert.|
|459|V_FMA_F32|D.f = S0.f * S1.f + S2.f.<br>Fused single precision multiply add. 0.5ULP accuracy, denormals are<br>supported.|
|460|V_FMA_F64|D.d = S0.d * S1.d + S2.d.<br>Fused double precision multiply add. 0.5ULP precision, denormals are<br>supported.|



12.11. VOP3A & VOP3B Instructions

151 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|461|V_LERP_U8|D.u = ((S0.u[31:24] + S1.u[31:24] + S2.u[24]) >> 1) << 24<br>D.u += ((S0.u[23:16] + S1.u[23:16] + S2.u[16]) >> 1) << 16;<br>D.u += ((S0.u[15:8] + S1.u[15:8] + S2.u[8]) >> 1) << 8;<br>D.u += ((S0.u[7:0] + S1.u[7:0] + S2.u[0]) >> 1).<br>Unsigned 8-bit pixel average on packed unsigned bytes (linear<br>interpolation). S2 acts as a round mode; if set, 0.5 rounds up,<br>otherwise 0.5 truncates.|
|462|V_ALIGNBIT_B32|D.u = ({S0,S1} >> S2.u[4:0]) & 0xffffffff.|
|463|V_ALIGNBYTE_B32|D.u = ({S0,S1} >> (8*S2.u[4:0])) & 0xffffffff.|
|464|V_MIN3_F32|D.f = V_MIN_F32(V_MIN_F32(S0.f, S1.f), S2.f).|
|465|V_MIN3_I32|D.i = V_MIN_I32(V_MIN_I32(S0.i, S1.i), S2.i).|
|466|V_MIN3_U32|D.u = V_MIN_U32(V_MIN_U32(S0.u, S1.u), S2.u).|
|467|V_MAX3_F32|D.f = V_MAX_F32(V_MAX_F32(S0.f, S1.f), S2.f).|
|468|V_MAX3_I32|D.i = V_MAX_I32(V_MAX_I32(S0.i, S1.i), S2.i).|
|469|V_MAX3_U32|D.u = V_MAX_U32(V_MAX_U32(S0.u, S1.u), S2.u).|
|470|V_MED3_F32|if (isNan(S0.f) || isNan(S1.f) || isNan(S2.f))<br>D.f = V_MIN3_F32(S0.f, S1.f, S2.f);<br>else if (V_MAX3_F32(S0.f, S1.f, S2.f) == S0.f)<br>D.f = V_MAX_F32(S1.f, S2.f);<br>else if (V_MAX3_F32(S0.f, S1.f, S2.f) == S1.f)<br>D.f = V_MAX_F32(S0.f, S2.f);<br>else<br>D.f = V_MAX_F32(S0.f, S1.f);<br>endif.|
|471|V_MED3_I32|if (V_MAX3_I32(S0.i, S1.i, S2.i) == S0.i)<br>D.i = V_MAX_I32(S1.i, S2.i);<br>else if (V_MAX3_I32(S0.i, S1.i, S2.i) == S1.i)<br>D.i = V_MAX_I32(S0.i, S2.i);<br>else<br>D.i = V_MAX_I32(S0.i, S1.i);<br>endif.|
|472|V_MED3_U32|if (V_MAX3_U32(S0.u, S1.u, S2.u) == S0.u)<br>D.u = V_MAX_U32(S1.u, S2.u);<br>else if (V_MAX3_U32(S0.u, S1.u, S2.u) == S1.u)<br>D.u = V_MAX_U32(S0.u, S2.u);<br>else<br>D.u = V_MAX_U32(S0.u, S1.u);<br>endif.|
|473|V_SAD_U8|ABSDIFF(x, y) := (x > y ? x - y : y - x) // UNSIGNED comparison<br>D.u = S2.u;<br>D.u += ABSDIFF(S0.u[31:24], S1.u[31:24]);<br>D.u += ABSDIFF(S0.u[23:16], S1.u[23:16]);<br>D.u += ABSDIFF(S0.u[15:8], S1.u[15:8]);<br>D.u += ABSDIFF(S0.u[7:0], S1.u[7:0]).<br>Sum of absolute differences with accumulation, overflow into upper bits<br>is allowed.|



12.11. VOP3A & VOP3B Instructions

152 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|474|V_SAD_HI_U8|D.u = (SAD_U8(S0, S1, 0) << 16) + S2.u.<br>Sum of absolute differences with accumulation, overflow is lost.|
|475|V_SAD_U16|ABSDIFF(x, y) := (x > y ? x - y : y - x) // UNSIGNED comparison<br>D.u = S2.u;<br>D.u += ABSDIFF(S0.u[31:16], S1.u[31:16]);<br>D.u += ABSDIFF(S0.u[15:0], S1.u[15:0]).|
|||Word SAD with accumulation.|
|476|V_SAD_U32|ABSDIFF(x, y) := (x > y ? x - y : y - x) // UNSIGNED comparison<br>D.u = ABSDIFF(S0.u, S1.u) + S2.u.<br>Dword SAD with accumulation.|
|477|V_CVT_PK_U8_F32|D.u = (S2.u & ~(0xff << (8 * S1.u[1:0])));<br>D.u = D.u | ((flt32_to_uint8(S0.f) & 0xff) << (8 * S1.u[1:0])).<br>Convert floating point value S0 to 8-bit unsigned integer and pack the<br>result into byte S1 of dword S2.|
|478|V_DIV_FIXUP_F32|sign_out = sign(S1.f)^sign(S2.f);<br>if (S2.f == NAN)<br>D.f = Quiet(S2.f);<br>else if (S1.f == NAN)<br>D.f = Quiet(S1.f);<br>else if (S1.f == S2.f == 0)<br>// 0/0<br>D.f = 0xffc0_0000;<br>else if (abs(S1.f) == abs(S2.f) == +-INF)<br>// inf/inf<br>D.f = 0xffc0_0000;<br>else if (S1.f == 0 || abs(S2.f) == +-INF)<br>// x/0, or inf/y<br>D.f = sign_out ? -INF : +INF;<br>else if (abs(S1.f) == +-INF || S2.f == 0)<br>// x/inf, 0/y<br>D.f = sign_out ? -0 : 0;<br>else if ((exponent(S2.f) - exponent(S1.f)) < -150)<br>D.f = sign_out ? -underflow : underflow;<br>else if (exponent(S1.f) == 255)<br>D.f = sign_out ? -overflow : overflow;<br>else<br>D.f = sign_out ? -abs(S0.f) : abs(S0.f);<br>endif.<br>Single precision division fixup. S0 = Quotient, S1 = Denominator, S2 =<br>Numerator.<br>Given a numerator, denominator, and quotient from a divide, this<br>opcode will detect and apply specific case numerics, touching up the<br>quotient if necessary. This opcode also generates invalid, denorm and<br>divide by zero exceptions caused by the division.|



12.11. VOP3A & VOP3B Instructions

153 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|479|V_DIV_FIXUP_F64|sign_out = sign(S1.d)^sign(S2.d);<br>if (S2.d == NAN)<br>D.d = Quiet(S2.d);<br>else if (S1.d == NAN)<br>D.d = Quiet(S1.d);<br>else if (S1.d == S2.d == 0)<br>// 0/0<br>D.d = 0xfff8_0000_0000_0000;<br>else if (abs(S1.d) == abs(S2.d) == +-INF)<br>// inf/inf<br>D.d = 0xfff8_0000_0000_0000;<br>else if (S1.d == 0 || abs(S2.d) == +-INF)<br>// x/0, or inf/y<br>D.d = sign_out ? -INF : +INF;<br>else if (abs(S1.d) == +-INF || S2.d == 0)<br>// x/inf, 0/y<br>D.d = sign_out ? -0 : 0;<br>else if ((exponent(S2.d) - exponent(S1.d)) < -1075)<br>D.d = sign_out ? -underflow : underflow;<br>else if (exponent(S1.d) == 2047)<br>D.d = sign_out ? -overflow : overflow;<br>else<br>D.d = sign_out ? -abs(S0.d) : abs(S0.d);<br>endif.<br>Double precision division fixup. S0 = Quotient, S1 = Denominator, S2 =<br>Numerator.<br>Given a numerator, denominator, and quotient from a divide, this<br>opcode will detect and apply specific case numerics, touching up the<br>quotient if necessary. This opcode also generates invalid, denorm and<br>divide by zero exceptions caused by the division.|



12.11. VOP3A & VOP3B Instructions

154 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|480|V_DIV_SCALE_F32|VCC = 0;<br>if (S2.f == 0 || S1.f == 0)<br>D.f = NAN<br>else if (exponent(S2.f) - exponent(S1.f) >= 96)<br>// N/D near MAX_FLOAT<br>VCC = 1;<br>if (S0.f == S1.f)<br>// Only scale the denominator<br>D.f = ldexp(S0.f, 64);<br>end if<br>else if (S1.f == DENORM)<br>D.f = ldexp(S0.f, 64);<br>else if (1 / S1.f == DENORM && S2.f / S1.f == DENORM)<br>VCC = 1;<br>if (S0.f == S1.f)<br>// Only scale the denominator<br>D.f = ldexp(S0.f, 64);<br>end if<br>else if (1 / S1.f == DENORM)<br>D.f = ldexp(S0.f, -64);<br>else if (S2.f / S1.f==DENORM)<br>VCC = 1;<br>if (S0.f == S2.f)<br>// Only scale the numerator<br>D.f = ldexp(S0.f, 64);<br>end if<br>else if (exponent(S2.f) <= 23)<br>// Numerator is tiny<br>D.f = ldexp(S0.f, 64);<br>end if.<br>Single precision division pre-scale. S0 = Input to scale (either<br>denominator or numerator), S1 = Denominator, S2 = Numerator.<br>Given a numerator and denominator, this opcode will appropriately<br>scale inputs for division to avoid subnormal terms during Newton-<br>Raphson correction method. S0 must be the same value as either S1 or<br>S2.<br>This opcode producses a VCC flag for post-scaling of the quotient<br>(using V_DIV_FMAS_F32).|



12.11. VOP3A & VOP3B Instructions

155 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|481|V_DIV_SCALE_F64|VCC = 0;<br>if (S2.d == 0 || S1.d == 0)<br>D.d = NAN<br>else if (exponent(S2.d) - exponent(S1.d) >= 768)<br>// N/D near MAX_FLOAT<br>VCC = 1;<br>if (S0.d == S1.d)<br>// Only scale the denominator<br>D.d = ldexp(S0.d, 128);<br>end if<br>else if (S1.d == DENORM)<br>D.d = ldexp(S0.d, 128);<br>else if (1 / S1.d == DENORM && S2.d / S1.d == DENORM)<br>VCC = 1;<br>if (S0.d == S1.d)<br>// Only scale the denominator<br>D.d = ldexp(S0.d, 128);<br>end if<br>else if (1 / S1.d == DENORM)<br>D.d = ldexp(S0.d, -128);<br>else if (S2.d / S1.d==DENORM)<br>VCC = 1;<br>if (S0.d == S2.d)<br>// Only scale the numerator<br>D.d = ldexp(S0.d, 128);<br>end if<br>else if (exponent(S2.d) <= 53)<br>// Numerator is tiny<br>D.d = ldexp(S0.d, 128);<br>end if.<br>Double precision division pre-scale. S0 = Input to scale (either<br>denominator or numerator), S1 = Denominator, S2 = Numerator.<br>Given a numerator and denominator, this opcode will appropriately<br>scale inputs for division to avoid subnormal terms during Newton-<br>Raphson correction method. S0 must be the same value as either S1 or<br>S2.<br>This opcode producses a VCC flag for post-scaling of the quotient<br>(using V_DIV_FMAS_F64).|
|482|V_DIV_FMAS_F32|if (VCC[threadId])<br>D.f = 2**32 * (S0.f * S1.f + S2.f);<br>else<br>D.f = S0.f * S1.f + S2.f;<br>end if.<br>Single precision FMA with fused scale.<br>This opcode performs a standard Fused Multiply-Add operation and will<br>conditionally scale the resulting exponent if VCC is set.<br>Input denormals are not flushed, but output flushing is allowed.|



12.11. VOP3A & VOP3B Instructions

156 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|483|V_DIV_FMAS_F64|if (VCC[threadId])<br>D.d = 2**64 * (S0.d * S1.d + S2.d);<br>else<br>D.d = S0.d * S1.d + S2.d;<br>end if.<br>Double precision FMA with fused scale.<br>This opcode performs a standard Fused Multiply-Add operation and will<br>conditionally scale the resulting exponent if VCC is set.<br>Input denormals are not flushed, but output flushing is allowed.|
|484|V_MSAD_U8|ABSDIFF(x, y) := (x > y ? x - y : y - x) // UNSIGNED comparison<br>D.u = S2.u;<br>D.u += S1.u[31:24] == 0 ? 0 : ABSDIFF(S0.u[31:24], S1.u[31:24]);<br>D.u += S1.u[23:16] == 0 ? 0 : ABSDIFF(S0.u[23:16], S1.u[23:16]);<br>D.u += S1.u[15:8] == 0 ? 0 : ABSDIFF(S0.u[15:8], S1.u[15:8]);<br>D.u += S1.u[7:0] == 0 ? 0 : ABSDIFF(S0.u[7:0], S1.u[7:0]).<br>Masked sum of absolute differences with accumulation, overflow into<br>upper bits is allowed. Components where the reference value in S1 is<br>zero are not included in the sum.|
|485|V_QSAD_PK_U16_U8|D[63:48] = SAD_U8(S0[55:24], S1[31:0], S2[63:48]);<br>D[47:32] = SAD_U8(S0[47:16], S1[31:0], S2[47:32]);<br>D[31:16] = SAD_U8(S0[39:8], S1[31:0], S2[31:16]);<br>D[15:0] = SAD_U8(S0[31:0], S1[31:0], S2[15:0]).<br>Quad-byte SAD with 16-bit packed accumulation.|
|486|V_MQSAD_PK_U16_<br>U8|D[63:48] = MSAD_U8(S0[55:24], S1[31:0], S2[63:48]);<br>D[47:32] = MSAD_U8(S0[47:16], S1[31:0], S2[47:32]);<br>D[31:16] = MSAD_U8(S0[39:8], S1[31:0], S2[31:16]);<br>D[15:0] = MSAD_U8(S0[31:0], S1[31:0], S2[15:0]).|
|||Quad-byte masked SAD with 16-bit packed accumulation.|
|487|V_MQSAD_U32_U8|D[127:96] = MSAD_U8(S0[55:24], S1[31:0], S2[127:96]);<br>D[95:64] = MSAD_U8(S0[47:16], S1[31:0], S2[95:64]);<br>D[63:32] = MSAD_U8(S0[39:8], S1[31:0], S2[63:32]);<br>D[31:0] = MSAD_U8(S0[31:0], S1[31:0], S2[31:0]).<br>Quad-byte masked SAD with 32-bit packed accumulation.|
|488|V_MAD_U64_U32|{vcc_out,D.u64} = S0.u32 * S1.u32 + S2.u64.|
|489|V_MAD_I64_I32|{vcc_out,D.i64} = S0.i32 * S1.i32 + S2.i64.|
|490|V_MAD_LEGACY_F1<br>6|D.f16 = S0.f16 * S1.f16 + S2.f16.<br>Supports round mode, exception flags, saturation.|
|||If op_sel[3] is 0 Result is written to 16 LSBs of destination VGPR and<br>hi 16 bits are written as 0 (this is different from V_MAD_F16).<br>If op_sel[3] is 1 Result is written to 16 MSBs of destination VGPR and<br>lo 16 bits are preserved.|



12.11. VOP3A & VOP3B Instructions

157 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|491|V_MAD_LEGACY_U1<br>6|D.u16 = S0.u16 * S1.u16 + S2.u16.<br>Supports saturation (unsigned 16-bit integer domain).<br>If op_sel[3] is 0 Result is written to 16 LSBs of destination VGPR and<br>hi 16 bits are written as 0 (this is different from V_MAD_U16).<br>If op_sel[3] is 1 Result is written to 16 MSBs of destination VGPR and<br>lo 16 bits are preserved.|
|492|V_MAD_LEGACY_I16|D.i16 = S0.i16 * S1.i16 + S2.i16.<br>Supports saturation (signed 16-bit integer domain).<br>If op_sel[3] is 0 Result is written to 16 LSBs of destination VGPR and<br>hi 16 bits are written as 0 (this is different from V_MAD_I16).<br>If op_sel[3] is 1 Result is written to 16 MSBs of destination VGPR and<br>lo 16 bits are preserved.|
|493|V_PERM_B32|D.u[31:24] = byte_permute({S0.u, S1.u}, S2.u[31:24]);<br>D.u[23:16] = byte_permute({S0.u, S1.u}, S2.u[23:16]);<br>D.u[15:8] = byte_permute({S0.u, S1.u}, S2.u[15:8]);<br>D.u[7:0] = byte_permute({S0.u, S1.u}, S2.u[7:0]);<br>byte permute(byte in[8], byte sel) {<br>if(sel>=13) then return 0xff;<br>elsif(sel==12) then return 0x00;<br>elsif(sel==11) then return in[7][7] * 0xff;<br>elsif(sel==10) then return in[5][7] * 0xff;<br>elsif(sel==9) then return in[3][7] * 0xff;<br>elsif(sel==8) then return in[1][7] * 0xff;<br>else return in[sel];<br>}<br>Byte permute.|
|494|V_FMA_LEGACY_F16|D.f16 = S0.f16 * S1.f16 + S2.f16.<br>Fused half precision multiply add.|



12.11. VOP3A & VOP3B Instructions

158 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|495|V_DIV_FIXUP_LEGA<br>CY_F16|sign_out = sign(S1.f16)^sign(S2.f16);<br>if (S2.f16 == NAN)<br>D.f16 = Quiet(S2.f16);<br>else if (S1.f16 == NAN)<br>D.f16 = Quiet(S1.f16);<br>else if (S1.f16 == S2.f16 == 0)<br>// 0/0<br>D.f16 = 0xfe00;<br>else if (abs(S1.f16) == abs(S2.f16) == +-INF)<br>// inf/inf<br>D.f16 = 0xfe00;<br>else if (S1.f16 ==0 || abs(S2.f16) == +-INF)<br>// x/0, or inf/y<br>D.f16 = sign_out ? -INF : +INF;<br>else if (abs(S1.f16) == +-INF || S2.f16 == 0)<br>// x/inf, 0/y<br>D.f16 = sign_out ? -0 : 0;<br>else<br>D.f16 = sign_out ? -abs(S0.f16) : abs(S0.f16);<br>end if.<br>Half precision division fixup. S0 = Quotient, S1 = Denominator, S2 =<br>Numerator.<br>Given a numerator, denominator, and quotient from a divide, this<br>opcode will detect and apply specific case numerics, touching up the<br>quotient if necessary. This opcode also generates invalid, denorm and<br>divide by zero exceptions caused by the division.|
|496|V_CVT_PKACCUM_U<br>8_F32|byte = S1.u[1:0];<br>bit = byte * 8;<br>D.u[bit+7:bit] = flt32_to_uint8(S0.f).|
|||Pack converted value of S0.f into byte S1 of the destination.  Note:<br>this opcode uses src_c to pass destination in as a source.|
|497|V_MAD_U32_U16|D.u32 = S0.u16 * S1.u16 + S2.u32.|
|498|V_MAD_I32_I16|D.i32 = S0.i16 * S1.i16 + S2.i32.|
|499|V_XAD_U32|D.u32 = (S0.u32 ^ S1.u32) + S2.u32.<br>No carryin/carryout and no saturation. This opcode exists to accelerate<br>the SHA256 hash algorithm.|
|500|V_MIN3_F16|D.f16 = V_MIN_F16(V_MIN_F16(S0.f16, S1.f16), S2.f16).|
|501|V_MIN3_I16|D.i16 = V_MIN_I16(V_MIN_I16(S0.i16, S1.i16), S2.i16).|
|502|V_MIN3_U16|D.u16 = V_MIN_U16(V_MIN_U16(S0.u16, S1.u16), S2.u16).|
|503|V_MAX3_F16|D.f16 = V_MAX_F16(V_MAX_F16(S0.f16, S1.f16), S2.f16).|
|504|V_MAX3_I16|D.i16 = V_MAX_I16(V_MAX_I16(S0.i16, S1.i16), S2.i16).|
|505|V_MAX3_U16|D.u16 = V_MAX_U16(V_MAX_U16(S0.u16, S1.u16), S2.u16).|



12.11. VOP3A & VOP3B Instructions

159 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|506|V_MED3_F16|if (isNan(S0.f16) || isNan(S1.f16) || isNan(S2.f16))<br>D.f16 = V_MIN3_F16(S0.f16, S1.f16, S2.f16);<br>else if (V_MAX3_F16(S0.f16, S1.f16, S2.f16) == S0.f16)<br>D.f16 = V_MAX_F16(S1.f16, S2.f16);<br>else if (V_MAX3_F16(S0.f16, S1.f16, S2.f16) == S1.f16)<br>D.f16 = V_MAX_F16(S0.f16, S2.f16);<br>else<br>D.f16 = V_MAX_F16(S0.f16, S1.f16);<br>endif.|
|507|V_MED3_I16|if (V_MAX3_I16(S0.i16, S1.i16, S2.i16) == S0.i16)<br>D.i16 = V_MAX_I16(S1.i16, S2.i16);<br>else if (V_MAX3_I16(S0.i16, S1.i16, S2.i16) == S1.i16)<br>D.i16 = V_MAX_I16(S0.i16, S2.i16);<br>else<br>D.i16 = V_MAX_I16(S0.i16, S1.i16);<br>endif.|
|508|V_MED3_U16|if (V_MAX3_U16(S0.u16, S1.u16, S2.u16) == S0.u16)<br>D.u16 = V_MAX_U16(S1.u16, S2.u16);<br>else if (V_MAX3_U16(S0.u16, S1.u16, S2.u16) == S1.u16)<br>D.u16 = V_MAX_U16(S0.u16, S2.u16);<br>else<br>D.u16 = V_MAX_U16(S0.u16, S1.u16);<br>endif.|
|509|V_LSHL_ADD_U32|D.u = (S0.u << S1.u[4:0]) + S2.u.|
|510|V_ADD_LSHL_U32|D.u = (S0.u + S1.u) << S2.u[4:0].|
|511|V_ADD3_U32|D.u = S0.u + S1.u + S2.u.|
|512|V_LSHL_OR_B32|D.u = (S0.u << S1.u[4:0]) | S2.u.|
|513|V_AND_OR_B32|D.u = (S0.u & S1.u) | S2.u.|
|514|V_OR3_B32|D.u = S0.u | S1.u | S2.u.|
|515|V_MAD_F16|D.f16 = S0.f16 * S1.f16 + S2.f16.<br>Supports round mode, exception flags, saturation. 1ULP accuracy,<br>denormals are flushed.<br>If op_sel[3] is 0 Result is written to 16 LSBs of destination VGPR and<br>hi 16 bits are preserved.<br>If op_sel[3] is 1 Result is written to 16 MSBs of destination VGPR and<br>lo 16 bits are preserved.|
|516|V_MAD_U16|D.u16 = S0.u16 * S1.u16 + S2.u16.<br>Supports saturation (unsigned 16-bit integer domain).<br>If op_sel[3] is 0 Result is written to 16 LSBs of destination VGPR and<br>hi 16 bits are preserved.<br>If op_sel[3] is 1 Result is written to 16 MSBs of destination VGPR and<br>lo 16 bits are preserved.|



12.11. VOP3A & VOP3B Instructions

160 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|517|V_MAD_I16|D.i16 = S0.i16 * S1.i16 + S2.i16.<br>Supports saturation (signed 16-bit integer domain).<br>If op_sel[3] is 0 Result is written to 16 LSBs of destination VGPR and<br>hi 16 bits are preserved.<br>If op_sel[3] is 1 Result is written to 16 MSBs of destination VGPR and<br>lo 16 bits are preserved.|
|518|V_FMA_F16|D.f16 = S0.f16 * S1.f16 + S2.f16.<br>Fused half precision multiply add. 0.5ULP accuracy, denormals are<br>supported.|
|||If op_sel[3] is 0 Result is written to 16 LSBs of destination VGPR and<br>hi 16 bits are preserved.<br>If op_sel[3] is 1 Result is written to 16 MSBs of destination VGPR and<br>lo 16 bits are preserved.|
|519|V_DIV_FIXUP_F16|sign_out = sign(S1.f16)^sign(S2.f16);<br>if (S2.f16 == NAN)<br>D.f16 = Quiet(S2.f16);<br>else if (S1.f16 == NAN)<br>D.f16 = Quiet(S1.f16);<br>else if (S1.f16 == S2.f16 == 0)<br>// 0/0<br>D.f16 = 0xfe00;<br>else if (abs(S1.f16) == abs(S2.f16) == +-INF)<br>// inf/inf<br>D.f16 = 0xfe00;<br>else if (S1.f16 ==0 || abs(S2.f16) == +-INF)<br>// x/0, or inf/y<br>D.f16 = sign_out ? -INF : +INF;<br>else if (abs(S1.f16) == +-INF || S2.f16 == 0)<br>// x/inf, 0/y<br>D.f16 = sign_out ? -0 : 0;<br>else<br>D.f16 = sign_out ? -abs(S0.f16) : abs(S0.f16);<br>end if.|
|||Half precision division fixup. S0 = Quotient, S1 = Denominator, S2 =<br>Numerator.<br>Given a numerator, denominator, and quotient from a divide, this<br>opcode will detect and apply specific case numerics, touching up the<br>quotient if necessary. This opcode also generates invalid, denorm and<br>divide by zero exceptions caused by the division.|
|||If op_sel[3] is 0 Result is written to 16 LSBs of destination VGPR and<br>hi 16 bits are preserved.<br>If op_sel[3] is 1 Result is written to 16 MSBs of destination VGPR and<br>lo 16 bits are preserved.|
|640|V_ADD_F64|D.d = S0.d + S1.d.<br>0.5ULP precision, denormals are supported.|



12.11. VOP3A & VOP3B Instructions

161 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|641|V_MUL_F64|D.d = S0.d * S1.d.|
|||0.5ULP precision, denormals are supported.|
|642|V_MIN_F64|if (IEEE_MODE && S0.d == sNaN)<br>D.d = Quiet(S0.d);<br>else if (IEEE_MODE && S1.d == sNaN)<br>D.d = Quiet(S1.d);<br>else if (S0.d == NaN)<br>D.d = S1.d;<br>else if (S1.d == NaN)<br>D.d = S0.d;<br>else if (S0.d == +0.0 && S1.d == -0.0)<br>D.d = S1.d;<br>else if (S0.d == -0.0 && S1.d == +0.0)<br>D.d = S0.d;<br>else<br>// Note: there's no IEEE special case here like there is for<br>V_MAX_F64.<br>D.d = (S0.d < S1.d ? S0.d : S1.d);<br>endif.|
|643|V_MAX_F64|if (IEEE_MODE && S0.d == sNaN)<br>D.d = Quiet(S0.d);<br>else if (IEEE_MODE && S1.d == sNaN)<br>D.d = Quiet(S1.d);<br>else if (S0.d == NaN)<br>D.d = S1.d;<br>else if (S1.d == NaN)<br>D.d = S0.d;<br>else if (S0.d == +0.0 && S1.d == -0.0)<br>D.d = S0.d;<br>else if (S0.d == -0.0 && S1.d == +0.0)<br>D.d = S1.d;<br>else if (IEEE_MODE)<br>D.d = (S0.d >= S1.d ? S0.d : S1.d);<br>else<br>D.d = (S0.d > S1.d ? S0.d : S1.d);<br>endif.|
|644|V_LDEXP_F64|D.d = S0.d * (2 ** S1.i).|
|645|V_MUL_LO_U32|D.u = S0.u * S1.u.|
|646|V_MUL_HI_U32|D.u = (S0.u * S1.u) >> 32.|
|647|V_MUL_HI_I32|D.i = (S0.i * S1.i) >> 32.|
|648|V_LDEXP_F32|D.f = S0.f * (2 ** S1.i).|
|649|V_READLANE_B32|Copy one VGPR value to one SGPR. D = SGPR-dest, S0 = Source Data<br>(VGPR# or M0(lds-direct)), S1 = Lane Select (SGPR or M0). Ignores exec<br>mask.<br>Input and output modifiers not supported; this is an untyped operation.|



12.11. VOP3A & VOP3B Instructions

162 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|650|V_WRITELANE_B32|Write value into one VGPR in one lane. D = VGPR-dest, S0 = Source Data<br>(sgpr, m0, exec or constants), S1 = Lane Select (SGPR or M0). Ignores<br>exec mask.|
|||Input and output modifiers not supported; this is an untyped operation.|
|651|V_BCNT_U32_B32|D.u = S1.u;<br>for i in 0 .. 31 do<br>D.u += S0.u[i]; // count i'th bit<br>endfor.|
|||Bit count.|
|652|V_MBCNT_LO_U32_B<br>32|ThreadMask = (1LL << ThreadPosition) - 1;<br>MaskedValue = (S0.u & ThreadMask[31:0]);<br>D.u = S1.u;<br>for i in 0 ... 31 do<br>D.u += (MaskedValue[i] == 1 ? 1 : 0);<br>endfor.<br>Masked bit count, ThreadPosition is the position of this thread in the<br>wavefront (in 0..63). See also V_MBCNT_HI_U32_B32.|
|653|V_MBCNT_HI_U32_B<br>32|ThreadMask = (1LL << ThreadPosition) - 1;<br>MaskedValue = (S0.u & ThreadMask[63:32]);<br>D.u = S1.u;<br>for i in 0 ... 31 do<br>D.u += (MaskedValue[i] == 1 ? 1 : 0);<br>endfor.|
|||Masked bit count, ThreadPosition is the position of this thread in the<br>wavefront (in 0..63). See also V_MBCNT_LO_U32_B32.<br>Example to compute each thread's position in 0..63:<br>v_mbcnt_lo_u32_b32 v0, -1, 0<br>v_mbcnt_hi_u32_b32 v0, -1, v0<br>// v0 now contains ThreadPosition|
|655|V_LSHLREV_B64|D.u64 = S1.u64 << S0.u[5:0].|
|656|V_LSHRREV_B64|D.u64 = S1.u64 >> S0.u[5:0].|
|657|V_ASHRREV_I64|D.u64 = signext(S1.u64) >> S0.u[5:0].|



12.11. VOP3A & VOP3B Instructions

163 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|658|V_TRIG_PREOP_F64|shift = S1.u * 53;<br>if exponent(S0.d) > 1077 then<br>shift += exponent(S0.d) - 1077;<br>endif<br>result = (double) ((2/PI[1200:0] << shift) & 0x1fffff_ffffffff);<br>scale = (-53 - shift);<br>if exponent(S0.d) >= 1968 then<br>scale += 128;<br>endif<br>D.d = ldexp(result, scale).<br>Look Up 2/PI (S0.d) with segment select S1.u[4:0]. This operation<br>returns an aligned, double precision segment of 2/PI needed to do range<br>reduction on S0.d (double-precision value). Multiple segments can be<br>specified through S1.u[4:0]. Rounding uses round-to-zero. Large inputs<br>(exp > 1968) are scaled to avoid loss of precision through<br>denormalization.|
|659|V_BFM_B32|D.u = ((1<<S0.u[4:0])-1) << S1.u[4:0].<br>Bitfield modify. S0 is the bitfield width and S1 is the bitfield<br>offset.|
|660|V_CVT_PKNORM_I16<br>_F32|D = {(snorm)S1.f, (snorm)S0.f}.|
|661|V_CVT_PKNORM_U1<br>6_F32|D = {(unorm)S1.f, (unorm)S0.f}.|
|662|V_CVT_PKRTZ_F16_<br>F32|D = {flt32_to_flt16(S1.f),flt32_to_flt16(S0.f)}.<br>// Round-toward-zero regardless of current round mode setting in<br>hardware.<br>This opcode is intended for use with 16-bit compressed exports. See<br>V_CVT_F16_F32 for a version that respects the current rounding mode.|
|663|V_CVT_PK_U16_U32|D = {uint32_to_uint16(S1.u), uint32_to_uint16(S0.u)}.|
|664|V_CVT_PK_I16_I32|D = {int32_to_int16(S1.i), int32_to_int16(S0.i)}.|
|665|V_CVT_PKNORM_I16<br>_F16|D = {(snorm)S1.f16, (snorm)S0.f16}.|
|666|V_CVT_PKNORM_U1<br>6_F16|D = {(unorm)S1.f16, (unorm)S0.f16}.|
|668|V_ADD_I32|D.i = S0.i + S1.i.|
|||Supports saturation (signed 32-bit integer domain).|
|669|V_SUB_I32|D.i = S0.i - S1.i.|
|||Supports saturation (signed 32-bit integer domain).|
|670|V_ADD_I16|D.i16 = S0.i16 + S1.i16.|
|||Supports saturation (signed 16-bit integer domain).|
|671|V_SUB_I16|D.i16 = S0.i16 - S1.i16.|
|||Supports saturation (signed 16-bit integer domain).|



12.11. VOP3A & VOP3B Instructions

164 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|672|V_PACK_B32_F16|D[31:16].f16 = S1.f16;|
|||D[15:0].f16 = S0.f16.|
|673|V_MUL_LEGACY_F32|D.f = S0.f * S1.f. // DX9 rules, 0.0*x = 0.0|



## **12.12. LDS & GDS Instructions**

This suite of instructions operates on data stored within the data share memory. The instructions transfer data between VGPRs and data share memory. The bitfield map for the LDS/GDS is:



where: OFFSET0 = Unsigned byte offset added to the address from the ADDR VGPR. OFFSET1 = Unsigned byte offset added to the address from the ADDR VGPR. GDS = Set if GDS, cleared if LDS. OP = DS instructions. ADDR = Source LDS address VGPR 0 - 255. DATA0 = Source data0 VGPR 0 - 255. DATA1 = Source data1 VGPR 0 - 255. VDST = Destination VGPR 0- 255.

 All instructions with RTN in the name return the value that was in memorybefore the operation was performed.

|**Opcode**|**Name**|**Description**|
|---|---|---|
|0|DS_ADD_U32|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] += DATA;<br>RETURN_DATA = tmp.|
|1|DS_SUB_U32|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] -= DATA;<br>RETURN_DATA = tmp.|
|2|DS_RSUB_U32|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = DATA - MEM[ADDR];<br>RETURN_DATA = tmp.|
|||Subtraction with reversed operands.|



12.12. LDS & GDS Instructions

165 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|3|DS_INC_U32|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (tmp >= DATA) ? 0 : tmp + 1; // unsigned compare<br>RETURN_DATA = tmp.|
|4|DS_DEC_U32|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (tmp == 0 || tmp > DATA) ? DATA : tmp - 1; // unsigned<br>compare<br>RETURN_DATA = tmp.|
|5|DS_MIN_I32|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (DATA < tmp) ? DATA : tmp; // signed compare<br>RETURN_DATA = tmp.|
|6|DS_MAX_I32|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (DATA > tmp) ? DATA : tmp; // signed compare<br>RETURN_DATA = tmp.|
|7|DS_MIN_U32|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (DATA < tmp) ? DATA : tmp; // unsigned compare<br>RETURN_DATA = tmp.|
|8|DS_MAX_U32|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (DATA > tmp) ? DATA : tmp; // unsigned compare<br>RETURN_DATA = tmp.|
|9|DS_AND_B32|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] &= DATA;<br>RETURN_DATA = tmp.|
|10|DS_OR_B32|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] |= DATA;<br>RETURN_DATA = tmp.|
|11|DS_XOR_B32|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] ^= DATA;<br>RETURN_DATA = tmp.|
|12|DS_MSKOR_B32|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (MEM[ADDR] & ~DATA) | DATA2;<br>RETURN_DATA = tmp.<br>Masked dword OR, D0 contains the mask and D1 contains the new<br>value.|
|13|DS_WRITE_B32|// 32bit<br>MEM[ADDR] = DATA.<br>Write dword.|



12.12. LDS & GDS Instructions

166 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|14|DS_WRITE2_B32|// 32bit<br>MEM[ADDR_BASE + OFFSET0 * 4] = DATA;<br>MEM[ADDR_BASE + OFFSET1 * 4] = DATA2.|
|||Write 2 dwords.|
|15|DS_WRITE2ST64_B32|// 32bit<br>MEM[ADDR_BASE + OFFSET0 * 4 * 64] = DATA;<br>MEM[ADDR_BASE + OFFSET1 * 4 * 64] = DATA2.|
|||Write 2 dwords.|
|16|DS_CMPST_B32|// 32bit<br>tmp = MEM[ADDR];<br>src = DATA2;<br>cmp = DATA;<br>MEM[ADDR] = (tmp == cmp) ? src : tmp;<br>RETURN_DATA[0] = tmp.<br>Compare and store. Caution, the order of src and cmp are the<br>*opposite* of the BUFFER_ATOMIC_CMPSWAP opcode.|
|17|DS_CMPST_F32|// 32bit<br>tmp = MEM[ADDR];<br>src = DATA2;<br>cmp = DATA;<br>MEM[ADDR] = (tmp == cmp) ? src : tmp;<br>RETURN_DATA[0] = tmp.<br>Floating point compare and store that handles NaN/INF/denormal<br>values.|
|18|DS_MIN_F32|// 32bit<br>tmp = MEM[ADDR];<br>src = DATA;<br>cmp = DATA2;<br>MEM[ADDR] = (cmp < tmp) ? src : tmp.<br>Floating point minimum that handles NaN/INF/denormal values.|
|19|DS_MAX_F32|// 32bit<br>tmp = MEM[ADDR];<br>src = DATA;<br>cmp = DATA2;<br>MEM[ADDR] = (tmp > cmp) ? src : tmp.<br>Floating point maximum that handles NaN/INF/denormal values.|
|20|DS_NOP|Do nothing.|
|21|DS_ADD_F32|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] += DATA;<br>RETURN_DATA = tmp.<br>Floating point add that handles NaN/INF/denormal values.|



12.12. LDS & GDS Instructions

167 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|29|DS_WRITE_ADDTID_B32|// 32bit<br>MEM[ADDR_BASE + OFFSET + M0.OFFSET + TID*4] = DATA.|
|||Write dword.|
|30|DS_WRITE_B8|MEM[ADDR] = DATA[7:0].|
|||Byte write.|
|31|DS_WRITE_B16|MEM[ADDR] = DATA[15:0].|
|||Short write.|
|32|DS_ADD_RTN_U32|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] += DATA;<br>RETURN_DATA = tmp.|
|33|DS_SUB_RTN_U32|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] -= DATA;<br>RETURN_DATA = tmp.|
|34|DS_RSUB_RTN_U32|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = DATA - MEM[ADDR];<br>RETURN_DATA = tmp.|
|||Subtraction with reversed operands.|
|35|DS_INC_RTN_U32|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (tmp >= DATA) ? 0 : tmp + 1; // unsigned compare<br>RETURN_DATA = tmp.|
|36|DS_DEC_RTN_U32|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (tmp == 0 || tmp > DATA) ? DATA : tmp - 1; // unsigned<br>compare<br>RETURN_DATA = tmp.|
|37|DS_MIN_RTN_I32|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (DATA < tmp) ? DATA : tmp; // signed compare<br>RETURN_DATA = tmp.|
|38|DS_MAX_RTN_I32|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (DATA > tmp) ? DATA : tmp; // signed compare<br>RETURN_DATA = tmp.|
|39|DS_MIN_RTN_U32|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (DATA < tmp) ? DATA : tmp; // unsigned compare<br>RETURN_DATA = tmp.|
|40|DS_MAX_RTN_U32|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (DATA > tmp) ? DATA : tmp; // unsigned compare<br>RETURN_DATA = tmp.|



12.12. LDS & GDS Instructions

168 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|41|DS_AND_RTN_B32|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] &= DATA;<br>RETURN_DATA = tmp.|
|42|DS_OR_RTN_B32|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] |= DATA;<br>RETURN_DATA = tmp.|
|43|DS_XOR_RTN_B32|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] ^= DATA;<br>RETURN_DATA = tmp.|
|44|DS_MSKOR_RTN_B32|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (MEM[ADDR] & ~DATA) | DATA2;<br>RETURN_DATA = tmp.<br>Masked dword OR, D0 contains the mask and D1 contains the new<br>value.|
|45|DS_WRXCHG_RTN_B32|tmp = MEM[ADDR];<br>MEM[ADDR] = DATA;<br>RETURN_DATA = tmp.<br>Write-exchange operation.|
|46|DS_WRXCHG2_RTN_B3<br>2|Write-exchange 2 separate dwords.|
|47|DS_WRXCHG2ST64_RT<br>N_B32|Write-exchange 2 separate dwords with a stride of 64 dwords.|
|48|DS_CMPST_RTN_B32|// 32bit<br>tmp = MEM[ADDR];<br>src = DATA2;<br>cmp = DATA;<br>MEM[ADDR] = (tmp == cmp) ? src : tmp;<br>RETURN_DATA[0] = tmp.<br>Compare and store. Caution, the order of src and cmp are the<br>*opposite* of the BUFFER_ATOMIC_CMPSWAP opcode.|
|49|DS_CMPST_RTN_F32|// 32bit<br>tmp = MEM[ADDR];<br>src = DATA2;<br>cmp = DATA;<br>MEM[ADDR] = (tmp == cmp) ? src : tmp;<br>RETURN_DATA[0] = tmp.<br>Floating point compare and store that handles NaN/INF/denormal<br>values.|



12.12. LDS & GDS Instructions

169 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|50|DS_MIN_RTN_F32|// 32bit<br>tmp = MEM[ADDR];<br>src = DATA;<br>cmp = DATA2;<br>MEM[ADDR] = (cmp < tmp) ? src : tmp.<br>Floating point minimum that handles NaN/INF/denormal values.|
|51|DS_MAX_RTN_F32|// 32bit<br>tmp = MEM[ADDR];<br>src = DATA;<br>cmp = DATA2;<br>MEM[ADDR] = (tmp > cmp) ? src : tmp.<br>Floating point maximum that handles NaN/INF/denormal values.|
|52|DS_WRAP_RTN_B32|tmp = MEM[ADDR];<br>MEM[ADDR] = (tmp >= DATA) ? tmp - DATA : tmp + DATA2;<br>RETURN_DATA = tmp.|
|53|DS_ADD_RTN_F32|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] += DATA;<br>RETURN_DATA = tmp.<br>Floating point add that handles NaN/INF/denormal values.|
|54|DS_READ_B32|RETURN_DATA = MEM[ADDR].<br>Dword read.|
|55|DS_READ2_B32|RETURN_DATA[0] = MEM[ADDR_BASE + OFFSET0 * 4];<br>RETURN_DATA[1] = MEM[ADDR_BASE + OFFSET1 * 4].<br>Read 2 dwords.|
|56|DS_READ2ST64_B32|RETURN_DATA[0] = MEM[ADDR_BASE + OFFSET0 * 4 * 64];<br>RETURN_DATA[1] = MEM[ADDR_BASE + OFFSET1 * 4 * 64].<br>Read 2 dwords.|
|57|DS_READ_I8|RETURN_DATA = signext(MEM[ADDR][7:0]).<br>Signed byte read.|
|58|DS_READ_U8|RETURN_DATA = {24'h0,MEM[ADDR][7:0]}.|
|||Unsigned byte read.|
|59|DS_READ_I16|RETURN_DATA = signext(MEM[ADDR][15:0]).|
|||Signed short read.|
|60|DS_READ_U16|RETURN_DATA = {16'h0,MEM[ADDR][15:0]}.<br>Unsigned short read.|
|61|DS_SWIZZLE_B32|Dword swizzle, no data is written to LDS memory. See next section<br>for details.|



12.12. LDS & GDS Instructions

170 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|62|DS_PERMUTE_B32|// VGPR[index][thread_id] is the VGPR RAM<br>// VDST, ADDR and DATA0 are from the microcode DS encoding<br>tmp[0..63] = 0<br>for i in 0..63 do<br>// If a source thread is disabled, it will not propagate data.<br>next if !EXEC[i]<br>// ADDR needs to be divided by 4.<br>// High-order bits are ignored.<br>dst_lane = floor((VGPR[ADDR][i] + OFFSET) / 4) mod 64<br>tmp[dst_lane] = VGPR[DATA0][i]<br>endfor<br>// Copy data into destination VGPRs. If multiple sources<br>// select the same destination thread, the highest-numbered<br>// source thread wins.<br>for i in 0..63 do<br>next if !EXEC[i]<br>VGPR[VDST][i] = tmp[i]<br>endfor|
|||Forward permute. This does not access LDS memory and may be called<br>even if no LDS memory is allocated to the wave. It uses LDS hardware<br>to implement an arbitrary swizzle across threads in a wavefront.<br>Note the address passed in is the thread ID multiplied by 4.|
|||If multiple sources map to the same destination lane, the final<br>value is not predictable but will be the value from one of the<br>writers.|
|||See also DS_BPERMUTE_B32.|
|||Examples (simplified 4-thread wavefronts):|
|||VGPR[SRC0] = { A, B, C, D }<br>VGPR[ADDR] = { 0, 0, 12, 4 }<br>EXEC = 0xF, OFFSET = 0<br>VGPR[VDST] := { B, D, 0, C }|
|||VGPR[SRC0] = { A, B, C, D }<br>VGPR[ADDR] = { 0, 0, 12, 4 }|
|||EXEC = 0xA, OFFSET = 0<br>VGPR[VDST] := { -, D, -, 0 }|



12.12. LDS & GDS Instructions

171 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|63|DS_BPERMUTE_B32|// VGPR[index][thread_id] is the VGPR RAM<br>// VDST, ADDR and DATA0 are from the microcode DS encoding<br>tmp[0..63] = 0<br>for i in 0..63 do<br>// ADDR needs to be divided by 4.<br>// High-order bits are ignored.<br>src_lane = floor((VGPR[ADDR][i] + OFFSET) / 4) mod 64<br>// EXEC is applied to the source VGPR reads.<br>next if !EXEC[src_lane]<br>tmp[i] = VGPR[DATA0][src_lane]<br>endfor<br>// Copy data into destination VGPRs. Some source<br>// data may be broadcast to multiple lanes.<br>for i in 0..63 do<br>next if !EXEC[i]<br>VGPR[VDST][i] = tmp[i]<br>endfor<br>Backward permute. This does not access LDS memory and may be called<br>even if no LDS memory is allocated to the wave. It uses LDS hardware<br>to implement an arbitrary swizzle across threads in a wavefront.<br>Note the address passed in is the thread ID multiplied by 4.<br>Note that EXEC mask is applied to both VGPR read and write. If<br>src_lane selects a disabled thread, zero will be returned.<br>See also DS_PERMUTE_B32.<br>Examples (simplified 4-thread wavefronts):<br>VGPR[SRC0] = { A, B, C, D }<br>VGPR[ADDR] = { 0, 0, 12, 4 }<br>EXEC = 0xF, OFFSET = 0<br>VGPR[VDST] := { A, A, D, B }|
|||VGPR[SRC0] = { A, B, C, D }<br>VGPR[ADDR] = { 0, 0, 12, 4 }<br>EXEC = 0xA, OFFSET = 0<br>VGPR[VDST] := { -, 0, -, B }|
|64|DS_ADD_U64|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] += DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|
|65|DS_SUB_U64|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] -= DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|
|66|DS_RSUB_U64|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = DATA - MEM[ADDR];<br>RETURN_DATA = tmp.<br>Subtraction with reversed operands.|



12.12. LDS & GDS Instructions

172 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|67|DS_INC_U64|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (tmp >= DATA[0:1]) ? 0 : tmp + 1; // unsigned compare<br>RETURN_DATA[0:1] = tmp.|
|68|DS_DEC_U64|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (tmp == 0 || tmp > DATA[0:1]) ? DATA[0:1] : tmp - 1; //<br>unsigned compare<br>RETURN_DATA[0:1] = tmp.|
|69|DS_MIN_I64|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] -= (DATA[0:1] < tmp) ? DATA[0:1] : tmp; // signed compare<br>RETURN_DATA[0:1] = tmp.|
|70|DS_MAX_I64|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] -= (DATA[0:1] > tmp) ? DATA[0:1] : tmp; // signed compare<br>RETURN_DATA[0:1] = tmp.|
|71|DS_MIN_U64|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] -= (DATA[0:1] < tmp) ? DATA[0:1] : tmp; // unsigned<br>compare<br>RETURN_DATA[0:1] = tmp.|
|72|DS_MAX_U64|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] -= (DATA[0:1] > tmp) ? DATA[0:1] : tmp; // unsigned<br>compare<br>RETURN_DATA[0:1] = tmp.|
|73|DS_AND_B64|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] &= DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|
|74|DS_OR_B64|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] |= DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|
|75|DS_XOR_B64|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] ^= DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|
|76|DS_MSKOR_B64|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (MEM[ADDR] & ~DATA) | DATA2;<br>RETURN_DATA = tmp.<br>Masked dword OR, D0 contains the mask and D1 contains the new<br>value.|
|77|DS_WRITE_B64|// 64bit<br>MEM[ADDR] = DATA.<br>Write qword.|



12.12. LDS & GDS Instructions

173 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|78|DS_WRITE2_B64|// 64bit<br>MEM[ADDR_BASE + OFFSET0 * 8] = DATA;<br>MEM[ADDR_BASE + OFFSET1 * 8] = DATA2.|
|||Write 2 qwords.|
|79|DS_WRITE2ST64_B64|// 64bit<br>MEM[ADDR_BASE + OFFSET0 * 8 * 64] = DATA;<br>MEM[ADDR_BASE + OFFSET1 * 8 * 64] = DATA2.|
|||Write 2 qwords.|
|80|DS_CMPST_B64|// 64bit<br>tmp = MEM[ADDR];<br>src = DATA2;<br>cmp = DATA;<br>MEM[ADDR] = (tmp == cmp) ? src : tmp;<br>RETURN_DATA[0] = tmp.<br>Compare and store. Caution, the order of src and cmp are the<br>*opposite* of the BUFFER_ATOMIC_CMPSWAP_X2 opcode.|
|81|DS_CMPST_F64|// 64bit<br>tmp = MEM[ADDR];<br>src = DATA2;<br>cmp = DATA;<br>MEM[ADDR] = (tmp == cmp) ? src : tmp;<br>RETURN_DATA[0] = tmp.<br>Floating point compare and store that handles NaN/INF/denormal<br>values.|
|82|DS_MIN_F64|// 64bit<br>tmp = MEM[ADDR];<br>src = DATA;<br>cmp = DATA2;<br>MEM[ADDR] = (cmp < tmp) ? src : tmp.<br>Floating point minimum that handles NaN/INF/denormal values. Note<br>that this opcode is slightly more general-purpose than<br>BUFFER_ATOMIC_FMIN_X2.|
|83|DS_MAX_F64|// 64bit<br>tmp = MEM[ADDR];<br>src = DATA;<br>cmp = DATA2;<br>MEM[ADDR] = (tmp > cmp) ? src : tmp.<br>Floating point maximum that handles NaN/INF/denormal values. Note<br>that this opcode is slightly more general-purpose than<br>BUFFER_ATOMIC_FMAX_X2.|
|84|DS_WRITE_B8_D16_HI|MEM[ADDR] = DATA[23:16].<br>Byte write in to high word.|
|85|DS_WRITE_B16_D16_HI|MEM[ADDR] = DATA[31:16].<br>Short write in to high word.|



12.12. LDS & GDS Instructions

174 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|86|DS_READ_U8_D16|RETURN_DATA[15:0] = {8'h0,MEM[ADDR][7:0]}.<br>Unsigned byte read with masked return to lower word.|
|87|DS_READ_U8_D16_HI|RETURN_DATA[31:16] = {8'h0,MEM[ADDR][7:0]}.<br>Unsigned byte read with masked return to upper word.|
|88|DS_READ_I8_D16|RETURN_DATA[15:0] = signext(MEM[ADDR][7:0]).<br>Signed byte read with masked return to lower word.|
|89|DS_READ_I8_D16_HI|RETURN_DATA[31:16] = signext(MEM[ADDR][7:0]).<br>Signed byte read with masked return to upper word.|
|90|DS_READ_U16_D16|RETURN_DATA[15:0] = MEM[ADDR][15:0].|
|||Unsigned short read with masked return to lower word.|
|91|DS_READ_U16_D16_HI|RETURN_DATA[31:0] = MEM[ADDR][15:0].<br>Unsigned short read with masked return to upper word.|
|92|DS_ADD_F64|// 64bit<br>tmp = MEM[ADDR];<br>D.f64 = tmp.f64 + DATA.f64;<br>MEM[ADDR] = D;<br>RETURN_DATA[0:1] = tmp.|
|96|DS_ADD_RTN_U64|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] += DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|
|97|DS_SUB_RTN_U64|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] -= DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|
|98|DS_RSUB_RTN_U64|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = DATA - MEM[ADDR];<br>RETURN_DATA = tmp.|
|||Subtraction with reversed operands.|
|99|DS_INC_RTN_U64|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (tmp >= DATA[0:1]) ? 0 : tmp + 1; // unsigned compare<br>RETURN_DATA[0:1] = tmp.|
|100|DS_DEC_RTN_U64|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (tmp == 0 || tmp > DATA[0:1]) ? DATA[0:1] : tmp - 1; //<br>unsigned compare<br>RETURN_DATA[0:1] = tmp.|
|101|DS_MIN_RTN_I64|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] -= (DATA[0:1] < tmp) ? DATA[0:1] : tmp; // signed compare<br>RETURN_DATA[0:1] = tmp.|



12.12. LDS & GDS Instructions

175 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|102|DS_MAX_RTN_I64|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] -= (DATA[0:1] > tmp) ? DATA[0:1] : tmp; // signed compare<br>RETURN_DATA[0:1] = tmp.|
|103|DS_MIN_RTN_U64|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] -= (DATA[0:1] < tmp) ? DATA[0:1] : tmp; // unsigned<br>compare<br>RETURN_DATA[0:1] = tmp.|
|104|DS_MAX_RTN_U64|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] -= (DATA[0:1] > tmp) ? DATA[0:1] : tmp; // unsigned<br>compare<br>RETURN_DATA[0:1] = tmp.|
|105|DS_AND_RTN_B64|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] &= DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|
|106|DS_OR_RTN_B64|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] |= DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|
|107|DS_XOR_RTN_B64|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] ^= DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|
|108|DS_MSKOR_RTN_B64|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (MEM[ADDR] & ~DATA) | DATA2;<br>RETURN_DATA = tmp.<br>Masked dword OR, D0 contains the mask and D1 contains the new<br>value.|
|109|DS_WRXCHG_RTN_B64|tmp = MEM[ADDR];<br>MEM[ADDR] = DATA;<br>RETURN_DATA = tmp.<br>Write-exchange operation.|
|110|DS_WRXCHG2_RTN_B6<br>4|Write-exchange 2 separate qwords.|
|111|DS_WRXCHG2ST64_RT<br>N_B64|Write-exchange 2 qwords with a stride of 64 qwords.|



12.12. LDS & GDS Instructions

176 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|112|DS_CMPST_RTN_B64|// 64bit<br>tmp = MEM[ADDR];<br>src = DATA2;<br>cmp = DATA;<br>MEM[ADDR] = (tmp == cmp) ? src : tmp;<br>RETURN_DATA[0] = tmp.<br>Compare and store. Caution, the order of src and cmp are the<br>*opposite* of the BUFFER_ATOMIC_CMPSWAP_X2 opcode.|
|113|DS_CMPST_RTN_F64|// 64bit<br>tmp = MEM[ADDR];<br>src = DATA2;<br>cmp = DATA;<br>MEM[ADDR] = (tmp == cmp) ? src : tmp;<br>RETURN_DATA[0] = tmp.<br>Floating point compare and store that handles NaN/INF/denormal<br>values.|
|114|DS_MIN_RTN_F64|// 64bit<br>tmp = MEM[ADDR];<br>src = DATA;<br>cmp = DATA2;<br>MEM[ADDR] = (cmp < tmp) ? src : tmp.<br>Floating point minimum that handles NaN/INF/denormal values. Note<br>that this opcode is slightly more general-purpose than<br>BUFFER_ATOMIC_FMIN_X2.|
|115|DS_MAX_RTN_F64|// 64bit<br>tmp = MEM[ADDR];<br>src = DATA;<br>cmp = DATA2;<br>MEM[ADDR] = (tmp > cmp) ? src : tmp.|
|||Floating point maximum that handles NaN/INF/denormal values. Note<br>that this opcode is slightly more general-purpose than<br>BUFFER_ATOMIC_FMAX_X2.|
|118|DS_READ_B64|RETURN_DATA = MEM[ADDR].<br>Read 1 qword.|
|119|DS_READ2_B64|RETURN_DATA[0] = MEM[ADDR_BASE + OFFSET0 * 8];<br>RETURN_DATA[1] = MEM[ADDR_BASE + OFFSET1 * 8].<br>Read 2 qwords.|
|120|DS_READ2ST64_B64|RETURN_DATA[0] = MEM[ADDR_BASE + OFFSET0 * 8 * 64];<br>RETURN_DATA[1] = MEM[ADDR_BASE + OFFSET1 * 8 * 64].|
|||Read 2 qwords.|
|124|DS_ADD_RTN_F64|// 64bit<br>tmp = MEM[ADDR];<br>D.f64 = tmp.f64 + DATA.f64;<br>MEM[ADDR] = D;<br>RETURN_DATA[0:1] = tmp.|



12.12. LDS & GDS Instructions

177 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|126|DS_CONDXCHG32_RTN<br>_B64|Conditional write exchange.|
|152|DS_GWS_SEMA_RELEA<br>SE_ALL|GDS Only: The GWS resource (rid) indicated will process this<br>opcode by updating the counter and labeling the specified resource<br>as a semaphore.<br>// Determine the GWS resource to work on<br>rid[5:0] = SH_SX_EXPCMD.gds_base[5:0] + offset0[5:0];<br>// Incr the state counter of the resource<br>state.counter[rid] = state.wave_in_queue;<br>state.type = SEMAPHORE;<br>return rd_done; //release calling wave<br>This action will release ALL queued waves; it Will have no effect<br>if no waves are present.|
|153|DS_GWS_INIT|GDS Only: Initialize a barrier or semaphore resource.<br>// Determine the GWS resource to work on<br>rid[5:0] = SH_SX_EXPCMD.gds_base[5:0] + offset0[5:0];<br>// Get the value to use in init<br>index = find_first_valid(vector mask)<br>value = DATA[thread: index]<br>// Set the state of the resource<br>state.counter[rid] = lsb(value); //limit #waves<br>state.flag[rid] = 0;<br>return rd_done; //release calling wave|
|154|DS_GWS_SEMA_V|GDS Only: The GWS resource indicated will process this opcode by<br>updating the counter and labeling the resource as a semaphore.<br>//Determine the GWS resource to work on<br>rid[5:0] = SH_SX_EXPCMD.gds_base[5:0] + offset0[5:0];<br>//Incr the state counter of the resource<br>state.counter[rid] += 1;<br>state.type = SEMAPHORE;<br>return rd_done; //release calling wave<br>This action will release one waved if any are queued in this<br>resource.|



12.12. LDS & GDS Instructions

178 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|155|DS_GWS_SEMA_BR|GDS Only: The GWS resource indicated will process this opcode by<br>updating the counter by the bulk release delivered count and<br>labeling the resource as a semaphore.<br>//Determine the GWS resource to work on<br>rid[5:0] = SH_SX_EXPCMD.gds_base[5:0] + offset0[5:0];<br>index = find first valid (vector mask)<br>count = DATA[thread: index];<br>//Add count to the resource state counter<br>state.counter[rid] += count;<br>state.type = SEMAPHORE;<br>return rd_done; //release calling wave<br>This action will release count number of waves, immediately if<br>queued, or as they arrive from the noted resource.|
|156|DS_GWS_SEMA_P|GDS Only: The GWS resource indicated will process this opcode by<br>queueing it until counter enables a release and then decrementing<br>the counter of the resource as a semaphore.<br>//Determine the GWS resource to work on<br>rid[5:0] = SH_SX_EXPCMD.gds_base[5:0] + offset0[5:0];<br>state.type = SEMAPHORE;<br>ENQUEUE until(state[rid].counter > 0)<br>state[rid].counter -= 1;<br>return rd_done;|



12.12. LDS & GDS Instructions

179 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|157|DS_GWS_BARRIER|GDS Only: The GWS resource indicated will process this opcode by<br>queueing it until barrier is satisfied. The number of waves needed<br>is passed in as DATA of first valid thread.<br>//Determine the GWS resource to work on<br>rid[5:0] = SH_SX_EXPCMD.gds_base[5:0] + OFFSET0[5:0];<br>index = find first valid (vector mask);<br>value = DATA[thread: index];<br>// Input Decision Machine<br>state.type[rid] = BARRIER;<br>if(state[rid].counter <= 0) then<br>thread[rid].flag = state[rid].flag;<br>ENQUEUE;<br>state[rid].flag = !state.flag;<br>state[rid].counter = value;<br>return rd_done;<br>else<br>state[rid].counter -= 1;<br>thread.flag = state[rid].flag;<br>ENQUEUE;<br>endif.<br>Since the waves deliver the count for the next barrier, this<br>function can have a different size barrier for each occurrence.<br>// Release Machine<br>if(state.type == BARRIER) then<br>if(state.flag != thread.flag) then<br>return rd_done;<br>endif;<br>endif.|
|182|DS_READ_ADDTID_B32|RETURN_DATA = MEM[ADDR_BASE + OFFSET + M0.OFFSET + TID*4].|
|||Dword read.|
|189|DS_CONSUME|LDS & GDS. Subtract (count_bits(exec_mask)) from the value stored<br>in DS memory at (M0.base + instr_offset). Return the pre-operation<br>value to VGPRs.|
|190|DS_APPEND|LDS & GDS. Add (count_bits(exec_mask)) to the value stored in DS<br>memory at (M0.base + instr_offset). Return the pre-operation value<br>to VGPRs.|
|222|DS_WRITE_B96|{MEM[ADDR + 8], MEM[ADDR + 4], MEM[ADDR]} = DATA[95:0].<br>Tri-dword write.|
|223|DS_WRITE_B128|{MEM[ADDR + 12], MEM[ADDR + 8], MEM[ADDR + 4], MEM[ADDR]} =<br>DATA[127:0].|
|||Quad-dword write.|
|254|DS_READ_B96|Tri-dword read.|
|255|DS_READ_B128|Quad-dword read.|



12.12. LDS & GDS Instructions

180 of 267

"AMD Instinct MI200" Instruction Set Architecture



### **12.12.1. DS_SWIZZLE_B32 Details**

Dword swizzle, no data is written to LDS memory. Swizzles input thread data based on offset mask and returns; note does not read or write the DS memory banks. Note that reading from an invalid thread results in 0x0. This opcode supports two specific modes, FFT and rotate, plus two basic modes which swizzle in groups of 4 or 32 consecutive threads. The FFT mode (offset >= 0xe000) swizzles the input based on offset[4:0] to support FFT calculation. Example swizzles using input {1, 2, ... 20} are: Offset[4:0]: Swizzle 0x00: {1,11,9,19,5,15,d,1d,3,13,b,1b,7,17,f,1f,2,12,a,1a,6,16,e,1e,4,14,c,1c,8,18,10,20} 0x10: {1,9,5,d,3,b,7,f,2,a,6,e,4,c,8,10,11,19,15,1d,13,1b,17,1f,12,1a,16,1e,14,1c,18,20} 0x1f: No swizzle The rotate mode (offset >= 0xc000 and offset < 0xe000) rotates the input either left (offset[10] == 0) or right (offset[10] == 1) a number of threads equal to offset[9:5]. The rotate mode also uses a mask value which can alter the rotate result. For example, mask == 1 will swap the odd threads across every other even thread (rotate left), or even threads across every other odd thread (rotate right). Offset[9:5]: Swizzle 0x01, mask=0, rotate left: {2,3,4,5,6,7,8,9,a,b,c,d,e,f,10,11,12,13,14,15,16,17,18,19,1a,1b,1c,1d,1e,1f,20,1} 0x01, mask=0, rotate right: {20,1,2,3,4,5,6,7,8,9,a,b,c,d,e,f,10,11,12,13,14,15,16,17,18,19,1a,1b,1c,1d,1e,1f} 0x01, mask=1, rotate left: {2,1,4,7,6,5,8,b,a,9,c,f,e,d,10,13,12,11,14,17,16,15,18,1b,1a,19,1c,1f,1e,1d,20,3} 0x01, mask=1, rotate right: {1e,1,4,3,2,5,8,7,6,9,c,b,a,d,10,f,e,11,14,13,12,15,18,17,16,19,1c,1b,1a,1d,20,1f} If offset < 0xc000, one of the basic swizzle modes is used based on offset[15]. If offset[15] == 1, groups of 4 consecutive threads are swizzled together. If offset[15] == 0, all 32 threads are swizzled together. The first basic swizzle mode (when offset[15] == 1) allows full data sharing between a group of 4 consecutive threads. Any thread within the group of 4 can get data from any other thread within the group of 4, specified by the corresponding offset bits --- [1:0] for the first thread, [3:2] for the second thread, [5:4] for the third thread, [7:6] for the fourth thread. Note that the offset bits apply to all groups of 4 within a wavefront; thus if offset[1:0] == 1, then thread0 will grab thread1, thread4 will grab thread5, etc. The second basic swizzle mode (when offset[15] == 0) allows limited data sharing between 32 consecutive threads. In this case, the offset is used to specify a 5-bit xor-mask, 5-bit or-mask, and 5-bit and-mask used to generate a thread mapping. Note that the offset bits apply to each group of 32 within a wavefront. The details of the thread mapping are listed below. Some example usages: SWAPX16 : xor_mask = 0x10, or_mask = 0x00, and_mask = 0x1f SWAPX8 : xor_mask = 0x08, or_mask = 0x00, and_mask = 0x1f SWAPX4 : xor_mask = 0x04, or_mask = 0x00, and_mask = 0x1f SWAPX2 : xor_mask = 0x02, or_mask = 0x00, and_mask = 0x1f SWAPX1 : xor_mask = 0x01, or_mask = 0x00, and_mask = 0x1f REVERSEX32 : xor_mask = 0x1f, or_mask = 0x00, and_mask = 0x1f REVERSEX16 : xor_mask = 0x0f, or_mask = 0x00, and_mask = 0x1f REVERSEX8 : xor_mask = 0x07, or_mask = 0x00, and_mask = 0x1f REVERSEX4 : xor_mask = 0x03, or_mask = 0x00, and_mask = 0x1f REVERSEX2 : xor_mask = 0x01 or_mask = 0x00, and_mask = 0x1f BCASTX32: xor_mask = 0x00, or_mask = thread, and_mask = 0x00 BCASTX16: xor_mask = 0x00, or_mask = thread, and_mask = 0x10 BCASTX8: xor_mask = 0x00, or_mask = thread, and_mask = 0x18 BCASTX4: xor_mask = 0x00, or_mask = thread, and_mask = 0x1c BCASTX2: xor_mask = 0x00, or_mask = thread, and_mask = 0x1e Pseudocode follows: offset = offset1:offset0;

12.12. LDS & GDS Instructions

181 of 267

"AMD Instinct MI200" Instruction Set Architecture



if (offset >= 0xe000) { // FFT decomposition mask = offset[4:0]; for (i = 0; i < 64; i++) { j = reverse_bits(i & 0x1f); j = (j >> count_ones(mask)); j \|= (i & mask); j \|= i & 0x20; thread_out[i] = thread_valid[j] ? thread_in[j] : 0; } } else if (offset >= 0xc000) { // rotate rotate = offset[9:5]; mask = offset[4:0]; if (offset[10]) { rotate = -rotate; } for (i = 0; i < 64; i++) { j = (i & mask) \| ((i + rotate) & ~mask); j \|= i & 0x20; thread_out[i] = thread_valid[j] ? thread_in[j] : 0; } } else if (offset[15]) { // full data sharing within 4 consecutive threads for (i = 0; i < 64; i+=4) { thread_out[i+0] = thread_valid[i+offset[1:0]]?thread_in[i+offset[1:0]]:0; thread_out[i+1] = thread_valid[i+offset[3:2]]?thread_in[i+offset[3:2]]:0; thread_out[i+2] = thread_valid[i+offset[5:4]]?thread_in[i+offset[5:4]]:0; thread_out[i+3] = thread_valid[i+offset[7:6]]?thread_in[i+offset[7:6]]:0; } } else { // offset[15] == 0 // limited data sharing within 32 consecutive threads xor_mask = offset[14:10]; or_mask = offset[9:5]; and_mask = offset[4:0]; for (i = 0; i < 64; i++) { j = (((i & 0x1f) & and_mask) \| or_mask) ^ xor_mask; j \|= (i & 0x20); // which group of 32 thread_out[i] = thread_valid[j] ? thread_in[j] : 0; } }

## **12.13. MUBUF Instructions**

The bitfield map of the MUBUF format is:



12.13. MUBUF Instructions

182 of 267

"AMD Instinct MI200" Instruction Set Architecture



where: OFFSET  = Unsigned immediate byte offset. OFFEN   = Send offset either as VADDR or as zero.. IDXEN   = Send index either as VADDR or as zero. GLC     = Global coherency. LDS     = Data read from/written to LDS or VGPR. OP      = Instruction Opcode. VADDR   = VGPR address source. VDATA   = Destination vector GPR. SRSRC   = Scalar GPR that specifies resource constant. SLC     = System level coherent. ACC     = Return to ACC VGPRs SOFFSET = Byte offset added to the memory address of an SGPR.

|**Opcode**|**Name**|**Description**|
|---|---|---|
|0|BUFFER_LOAD_FORMAT_X|Untyped buffer load 1 dword with format conversion.|
|1|BUFFER_LOAD_FORMAT_XY|Untyped buffer load 2 dwords with format conversion.|
|2|BUFFER_LOAD_FORMAT_XYZ|Untyped buffer load 3 dwords with format conversion.|
|3|BUFFER_LOAD_FORMAT_XYZW|Untyped buffer load 4 dwords with format conversion.|
|4|BUFFER_STORE_FORMAT_X|Untyped buffer store 1 dword with format conversion.|
|5|BUFFER_STORE_FORMAT_XY|Untyped buffer store 2 dwords with format conversion.|
|6|BUFFER_STORE_FORMAT_XYZ|Untyped buffer store 3 dwords with format conversion.|
|7|BUFFER_STORE_FORMAT_XYZW|Untyped buffer store 4 dwords with format conversion.|
|8|BUFFER_LOAD_FORMAT_D16_X|Untyped buffer load 1 dword with format conversion.<br>D0[15:0] = {8'h0, MEM[ADDR]}.|
|9|BUFFER_LOAD_FORMAT_D16_XY|Untyped buffer load 1 dword with format conversion.|
|10|BUFFER_LOAD_FORMAT_D16_XY<br>Z|Untyped buffer load 2 dwords with format conversion.|
|11|BUFFER_LOAD_FORMAT_D16_XY<br>ZW|Untyped buffer load 2 dwords with format conversion.|
|12|BUFFER_STORE_FORMAT_D16_X|Untyped buffer store 1 dword with format conversion.|
|13|BUFFER_STORE_FORMAT_D16_<br>XY|Untyped buffer store 1 dword with format conversion.|
|14|BUFFER_STORE_FORMAT_D16_<br>XYZ|Untyped buffer store 2 dwords with format conversion.|
|15|BUFFER_STORE_FORMAT_D16_<br>XYZW|Untyped buffer store 2 dwords with format conversion.|
|16|BUFFER_LOAD_UBYTE|Untyped buffer load unsigned byte (zero extend to VGPR<br>destination).|
|17|BUFFER_LOAD_SBYTE|Untyped buffer load signed byte (sign extend to VGPR<br>destination).|
|18|BUFFER_LOAD_USHORT|Untyped buffer load unsigned short (zero extend to VGPR<br>destination).|



12.13. MUBUF Instructions

183 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|19|BUFFER_LOAD_SSHORT|Untyped buffer load signed short (sign extend to VGPR<br>destination).|
|20|BUFFER_LOAD_DWORD|Untyped buffer load dword.|
|21|BUFFER_LOAD_DWORDX2|Untyped buffer load 2 dwords.|
|22|BUFFER_LOAD_DWORDX3|Untyped buffer load 3 dwords.|
|23|BUFFER_LOAD_DWORDX4|Untyped buffer load 4 dwords.|
|24|BUFFER_STORE_BYTE|Untyped buffer store byte. Stores S0[7:0].|
|25|BUFFER_STORE_BYTE_D16_HI|Untyped buffer store byte. Stores S0[23:16].|
|26|BUFFER_STORE_SHORT|Untyped buffer store short. Stores S0[15:0].|
|27|BUFFER_STORE_SHORT_D16_HI|Untyped buffer store short. Stores S0[31:16].|
|28|BUFFER_STORE_DWORD|Untyped buffer store dword.|
|29|BUFFER_STORE_DWORDX2|Untyped buffer store 2 dwords.|
|30|BUFFER_STORE_DWORDX3|Untyped buffer store 3 dwords.|
|31|BUFFER_STORE_DWORDX4|Untyped buffer store 4 dwords.|
|32|BUFFER_LOAD_UBYTE_D16|D0[15:0] = {8'h0, MEM[ADDR]}.|
|||Untyped buffer load unsigned byte.|
|33|BUFFER_LOAD_UBYTE_D16_HI|D0[31:16] = {8'h0, MEM[ADDR]}.<br>Untyped buffer load unsigned byte.|
|34|BUFFER_LOAD_SBYTE_D16|D0[15:0] = {8'h0, MEM[ADDR]}.|
|||Untyped buffer load signed byte.|
|35|BUFFER_LOAD_SBYTE_D16_HI|D0[31:16] = {8'h0, MEM[ADDR]}.|
|||Untyped buffer load signed byte.|
|36|BUFFER_LOAD_SHORT_D16|D0[15:0] = MEM[ADDR].<br>Untyped buffer load short.|
|37|BUFFER_LOAD_SHORT_D16_HI|D0[31:16] = MEM[ADDR].<br>Untyped buffer load short.|
|38|BUFFER_LOAD_FORMAT_D16_HI<br>_X|D0[31:16] = MEM[ADDR].<br>Untyped buffer load 1 dword with format conversion.|
|39|BUFFER_STORE_FORMAT_D16_<br>HI_X|Untyped buffer store 1 dword with format conversion.|
|40|BUFFER_WBL2|Write back L2, flush the whole L2 cache. Returns ACK to<br>shader.|
|41|BUFFER_INVL2|invalidate L2. Returns ACK to shader.|
|61|BUFFER_STORE_LDS_DWORD|Store one DWORD from LDS memory to system memory without<br>utilizing VGPRs.|



12.13. MUBUF Instructions

184 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|62|BUFFER_WBINVL1|Write back and invalidate the shader L1. Returns ACK to<br>shader.|
|63|BUFFER_WBINVL1_VOL|Write back and invalidate the shader L1 only for lines<br>that are marked volatile. Returns ACK to shader.|
|64|BUFFER_ATOMIC_SWAP|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = DATA;<br>RETURN_DATA = tmp.|
|65|BUFFER_ATOMIC_CMPSWAP|// 32bit<br>tmp = MEM[ADDR];<br>src = DATA[0];<br>cmp = DATA[1];<br>MEM[ADDR] = (tmp == cmp) ? src : tmp;<br>RETURN_DATA[0] = tmp.|
|66|BUFFER_ATOMIC_ADD|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] += DATA;<br>RETURN_DATA = tmp.|
|67|BUFFER_ATOMIC_SUB|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] -= DATA;<br>RETURN_DATA = tmp.|
|68|BUFFER_ATOMIC_SMIN|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (DATA < tmp) ? DATA : tmp; // signed compare<br>RETURN_DATA = tmp.|
|69|BUFFER_ATOMIC_UMIN|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (DATA < tmp) ? DATA : tmp; // unsigned compare<br>RETURN_DATA = tmp.|
|70|BUFFER_ATOMIC_SMAX|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (DATA > tmp) ? DATA : tmp; // signed compare<br>RETURN_DATA = tmp.|
|71|BUFFER_ATOMIC_UMAX|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (DATA > tmp) ? DATA : tmp; // unsigned compare<br>RETURN_DATA = tmp.|
|72|BUFFER_ATOMIC_AND|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] &= DATA;<br>RETURN_DATA = tmp.|
|73|BUFFER_ATOMIC_OR|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] |= DATA;<br>RETURN_DATA = tmp.|



12.13. MUBUF Instructions

185 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|74|BUFFER_ATOMIC_XOR|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] ^= DATA;<br>RETURN_DATA = tmp.|
|75|BUFFER_ATOMIC_INC|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (tmp >= DATA) ? 0 : tmp + 1; // unsigned<br>compare<br>RETURN_DATA = tmp.|
|76|BUFFER_ATOMIC_DEC|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (tmp == 0 || tmp > DATA) ? DATA : tmp - 1; //<br>unsigned compare<br>RETURN_DATA = tmp.|
|77|BUFFER_ATOMIC_ADD_F32|// 32bit<br>tmp = MEM[ADDR];<br>D.f = tmp.f + DATA.f;<br>MEM[ADDR] = D.|
|78|BUFFER_ATOMIC_PK_ADD_F16|// 32bit<br>tmp = MEM[ADDR];<br>D.f16[31:16] = tmp.f16[31:16] + DATA.f16[31:16];<br>D.f16[15:0] = tmp.f16[15:0] + DATA.f16[15:0];<br>MEM[ADDR] = D.|
|79|BUFFER_ATOMIC_ADD_F64|// 64bit<br>tmp = MEM[ADDR];<br>D.f64 = tmp.f64 + DATA.f64;<br>MEM[ADDR] = D;<br>RETURN_DATA[0:1] = tmp.|
|80|BUFFER_ATOMIC_MIN_F64|// 64bit<br>tmp = MEM[ADDR];<br>D.f64 = (DATA.f64 < tmp.f64) ? DATA.f64 : tmp.f64;<br>MEM[ADDR] = D;<br>RETURN_DATA[0:1] = tmp.|
|81|BUFFER_ATOMIC_MAX_F64|// 64bit<br>tmp = MEM[ADDR];<br>D.f64 = (DATA.f64 > tmp.f64) ? DATA.f64 : tmp.f64;<br>MEM[ADDR] = D;<br>RETURN_DATA[0:1] = tmp.|
|96|BUFFER_ATOMIC_SWAP_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|
|97|BUFFER_ATOMIC_CMPSWAP_X2|// 64bit<br>tmp = MEM[ADDR];<br>src = DATA[0:1];<br>cmp = DATA[2:3];<br>MEM[ADDR] = (tmp == cmp) ? src : tmp;<br>RETURN_DATA[0:1] = tmp.|



12.13. MUBUF Instructions

186 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|98|BUFFER_ATOMIC_ADD_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] += DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|
|99|BUFFER_ATOMIC_SUB_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|
|100|BUFFER_ATOMIC_SMIN_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (DATA[0:1] < tmp) ? DATA[0:1] : tmp; // signed<br>compare<br>RETURN_DATA[0:1] = tmp.|
|101|BUFFER_ATOMIC_UMIN_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (DATA[0:1] < tmp) ? DATA[0:1] : tmp; //<br>unsigned compare<br>RETURN_DATA[0:1] = tmp.|
|102|BUFFER_ATOMIC_SMAX_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (DATA[0:1] > tmp) ? DATA[0:1] : tmp; // signed<br>compare<br>RETURN_DATA[0:1] = tmp.|
|103|BUFFER_ATOMIC_UMAX_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (DATA[0:1] > tmp) ? DATA[0:1] : tmp; //<br>unsigned compare<br>RETURN_DATA[0:1] = tmp.|
|104|BUFFER_ATOMIC_AND_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] &= DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|
|105|BUFFER_ATOMIC_OR_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] |= DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|
|106|BUFFER_ATOMIC_XOR_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] ^= DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|
|107|BUFFER_ATOMIC_INC_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (tmp >= DATA[0:1]) ? 0 : tmp + 1; // unsigned<br>compare<br>RETURN_DATA[0:1] = tmp.|
|108|BUFFER_ATOMIC_DEC_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (tmp == 0 || tmp > DATA[0:1]) ? DATA[0:1] :<br>tmp - 1; // unsigned compare<br>RETURN_DATA[0:1] = tmp.|



12.13. MUBUF Instructions

187 of 267

"AMD Instinct MI200" Instruction Set Architecture



## **12.14. MTBUF Instructions**

The bitfield map of the MTBUF format is:



where: OFFSET  = Unsigned immediate byte offset. OFFEN   = Send offset either as VADDR or as zero. IDXEN   = Send index either as VADDR or as zero. GLC     = Global coherency. SLC     = System level coherent. LDS     = Data is transferred between LDS and Memory, not VGPRs. OP      = Instruction Opcode. DFMT    = Data format for typed buffer. NFMT    = Number format for typed buffer. VADDR   = VGPR address source. VDATA   = Vector GPR for read/write result.

SRSRC   = Scalar GPR that specifies resource constant. SOFFSET = Unsigned byte offset from an SGPR. ACC     = Return to ACC VGPRs

|**Opcode**|**Name**|**Description**|
|---|---|---|
|0|TBUFFER_LOAD_FORMAT_X|Typed buffer load 1 dword with format conversion.|
|1|TBUFFER_LOAD_FORMAT_XY|Typed buffer load 2 dwords with format conversion.|
|2|TBUFFER_LOAD_FORMAT_XYZ|Typed buffer load 3 dwords with format conversion.|
|3|TBUFFER_LOAD_FORMAT_XYZW|Typed buffer load 4 dwords with format conversion.|
|4|TBUFFER_STORE_FORMAT_X|Typed buffer store 1 dword with format conversion.|
|5|TBUFFER_STORE_FORMAT_XY|Typed buffer store 2 dwords with format conversion.|
|6|TBUFFER_STORE_FORMAT_XYZ|Typed buffer store 3 dwords with format conversion.|
|7|TBUFFER_STORE_FORMAT_XYZW|Typed buffer store 4 dwords with format conversion.|
|8|TBUFFER_LOAD_FORMAT_D16_X|Typed buffer load 1 dword with format conversion.|
|9|TBUFFER_LOAD_FORMAT_D16_XY|Typed buffer load 1 dword with format conversion.|
|10|TBUFFER_LOAD_FORMAT_D16_XY<br>Z|Typed buffer load 2 dwords with format conversion.|
|11|TBUFFER_LOAD_FORMAT_D16_XY<br>ZW|Typed buffer load 2 dwords with format conversion.|
|12|TBUFFER_STORE_FORMAT_D16_X|Typed buffer store 1 dword with format conversion.|
|13|TBUFFER_STORE_FORMAT_D16_X<br>Y|Typed buffer store 1 dword with format conversion.|



12.14. MTBUF Instructions

188 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|14|TBUFFER_STORE_FORMAT_D16_X<br>YZ|Typed buffer store 2 dwords with format conversion.|
|15|TBUFFER_STORE_FORMAT_D16_X<br>YZW|Typed buffer store 2 dwords with format conversion.|



## **12.15. MIMG Instructions**

The bitfield map of the MIMG format is:



where: DMASK = Enable mask for image read/write data components. UNRM  = Force address to be unnormalized. GLC   = Global coherency. DA    = Declare an array. A16   = Texture address component size. ACC   = Return to ACC VGPRs LWE   = LOD warning enable. OP    = Instruction Opcode. OPM   = Instruction Opcode most signifcant bit. SLC   = System level coherent. VADDR = VGPR address source. VDATA = Vector GPR for read/write result. SRSRC = Scalar GPR that specifies resource constant. SSAMP = Scalar GPR that specifies sampler constant. D16   = Data in VGPRs is 16 bits, not 32 bits.

|**Opcode**|**Name**|**Description**|
|---|---|---|
|0|IMAGE_LOAD|Image memory load with format conversion specified in T#. No<br>sampler.|
|1|IMAGE_LOAD_MIP|Image memory load with user-supplied mip level. No sampler.|
|||Only allowed for miplevel 0, this must be enforced by S/W.|
|2|IMAGE_LOAD_PCK|Image memory load with no format conversion. No sampler.|
|3|IMAGE_LOAD_PCK_SGN|Image memory load with with no format conversion and sign<br>extension. No sampler.|
|4|IMAGE_LOAD_MIP_PCK|Image memory load with user-supplied mip level, no format<br>conversion. No sampler.|
|||Only allowed for miplevel 0, this must be enforced by S/W.|



12.15. MIMG Instructions

189 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|5|IMAGE_LOAD_MIP_PCK_SGN|Image memory load with user-supplied mip level, no format<br>conversion and with sign extension. No sampler.|
|||Only allowed for miplevel 0, this must be enforced by S/W.|
|8|IMAGE_STORE|Image memory store with format conversion specified in T#. No<br>sampler.|
|9|IMAGE_STORE_MIP|Image memory store with format conversion specified in T# to<br>user specified mip level. No sampler.|
|||Only allowed for miplevel 0, this must be enforced by S/W.|
|10|IMAGE_STORE_PCK|Image memory store of packed data without format conversion .<br>No sampler.|
|11|IMAGE_STORE_MIP_PCK|Image memory store of packed data without format conversion<br>to user-supplied mip level. No sampler.<br>Only allowed for miplevel 0, this must be enforced by S/W.|
|14|IMAGE_GET_RESINFO|return resource info for a given mip level specified in the<br>address vgpr. No sampler. Returns 4 integer values into VGPRs<br>3-0: {num_mip_levels, depth, height, width}.|
|16|IMAGE_ATOMIC_SWAP|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = DATA;<br>RETURN_DATA = tmp.|
|17|IMAGE_ATOMIC_CMPSWAP|// 32bit<br>tmp = MEM[ADDR];<br>src = DATA[0];<br>cmp = DATA[1];<br>MEM[ADDR] = (tmp == cmp) ? src : tmp;<br>RETURN_DATA[0] = tmp.|
|18|IMAGE_ATOMIC_ADD|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] += DATA;<br>RETURN_DATA = tmp.|
|19|IMAGE_ATOMIC_SUB|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] -= DATA;<br>RETURN_DATA = tmp.|
|20|IMAGE_ATOMIC_SMIN|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (DATA < tmp) ? DATA : tmp; // signed compare<br>RETURN_DATA = tmp.|
|21|IMAGE_ATOMIC_UMIN|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (DATA < tmp) ? DATA : tmp; // unsigned compare<br>RETURN_DATA = tmp.|
|22|IMAGE_ATOMIC_SMAX|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (DATA > tmp) ? DATA : tmp; // signed compare<br>RETURN_DATA = tmp.|



12.15. MIMG Instructions

190 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|23|IMAGE_ATOMIC_UMAX|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (DATA > tmp) ? DATA : tmp; // unsigned compare<br>RETURN_DATA = tmp.|
|24|IMAGE_ATOMIC_AND|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] &= DATA;<br>RETURN_DATA = tmp.|
|25|IMAGE_ATOMIC_OR|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] |= DATA;<br>RETURN_DATA = tmp.|
|26|IMAGE_ATOMIC_XOR|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] ^= DATA;<br>RETURN_DATA = tmp.|
|27|IMAGE_ATOMIC_INC|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (tmp >= DATA) ? 0 : tmp + 1; // unsigned compare<br>RETURN_DATA = tmp.|
|28|IMAGE_ATOMIC_DEC|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (tmp == 0 || tmp > DATA) ? DATA : tmp - 1; //<br>unsigned compare<br>RETURN_DATA = tmp.|
|32|IMAGE_SAMPLE|Sample texture map. This is the only sample instruction<br>supported on this ASIC.|



## **12.16. FLAT, Scratch and Global Instructions**

The bitfield map of the FLAT format is:



12.16. FLAT, Scratch and Global Instructions

191 of 267

"AMD Instinct MI200" Instruction Set Architecture



where: GLC    = Global coherency. SLC    = System level coherency. OP     = Instruction Opcode. ADDR   = Source of flat address VGPR. DATA   = Source data. VDST   = Destination VGPR. NV     = Access to non-volatile memory. SADDR  = SGPR holding address or offset SEG    = Instruction type: Flat, Scratch, or Global LDS    = Data is transferred between LDS and Memory, not VGPRs. OFFSET = Immediate address byte-offset.

### **12.16.1. Flat Instructions**

Flat instructions look at the per-workitem address and determine for each work item if the target memory address is in global, private or scratch memory.

|**Opcode**|**Name**|**Description**|
|---|---|---|
|16|FLAT_LOAD_UBYTE|Untyped buffer load unsigned byte (zero extend to VGPR<br>destination).|
|17|FLAT_LOAD_SBYTE|Untyped buffer load signed byte (sign extend to VGPR<br>destination).|
|18|FLAT_LOAD_USHORT|Untyped buffer load unsigned short (zero extend to VGPR<br>destination).|
|19|FLAT_LOAD_SSHORT|Untyped buffer load signed short (sign extend to VGPR<br>destination).|
|20|FLAT_LOAD_DWORD|Untyped buffer load dword.|
|21|FLAT_LOAD_DWORDX2|Untyped buffer load 2 dwords.|
|22|FLAT_LOAD_DWORDX3|Untyped buffer load 3 dwords.|
|23|FLAT_LOAD_DWORDX4|Untyped buffer load 4 dwords.|
|24|FLAT_STORE_BYTE|Untyped buffer store byte. Stores S0[7:0].|
|25|FLAT_STORE_BYTE_D16_HI|Untyped buffer store byte. Stores S0[23:16].|
|26|FLAT_STORE_SHORT|Untyped buffer store short. Stores S0[15:0].|
|27|FLAT_STORE_SHORT_D16_HI|Untyped buffer store short. Stores S0[31:16].|
|28|FLAT_STORE_DWORD|Untyped buffer store dword.|
|29|FLAT_STORE_DWORDX2|Untyped buffer store 2 dwords.|
|30|FLAT_STORE_DWORDX3|Untyped buffer store 3 dwords.|
|31|FLAT_STORE_DWORDX4|Untyped buffer store 4 dwords.|
|32|FLAT_LOAD_UBYTE_D16|D0[15:0] = {8'h0, MEM[ADDR]}.|
|||Untyped buffer load unsigned byte.|



12.16. FLAT, Scratch and Global Instructions

192 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|33|FLAT_LOAD_UBYTE_D16_HI|D0[31:16] = {8'h0, MEM[ADDR]}.<br>Untyped buffer load unsigned byte.|
|34|FLAT_LOAD_SBYTE_D16|D0[15:0] = {8'h0, MEM[ADDR]}.<br>Untyped buffer load signed byte.|
|35|FLAT_LOAD_SBYTE_D16_HI|D0[31:16] = {8'h0, MEM[ADDR]}.|
|||Untyped buffer load signed byte.|
|36|FLAT_LOAD_SHORT_D16|D0[15:0] = MEM[ADDR].<br>Untyped buffer load short.|
|37|FLAT_LOAD_SHORT_D16_HI|D0[31:16] = MEM[ADDR].|
|||Untyped buffer load short.|
|64|FLAT_ATOMIC_SWAP|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = DATA;<br>RETURN_DATA = tmp.|
|65|FLAT_ATOMIC_CMPSWAP|// 32bit<br>tmp = MEM[ADDR];<br>src = DATA[0];<br>cmp = DATA[1];<br>MEM[ADDR] = (tmp == cmp) ? src : tmp;<br>RETURN_DATA[0] = tmp.|
|66|FLAT_ATOMIC_ADD|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] += DATA;<br>RETURN_DATA = tmp.|
|67|FLAT_ATOMIC_SUB|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] -= DATA;<br>RETURN_DATA = tmp.|
|68|FLAT_ATOMIC_SMIN|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (DATA < tmp) ? DATA : tmp; // signed compare<br>RETURN_DATA = tmp.|
|69|FLAT_ATOMIC_UMIN|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (DATA < tmp) ? DATA : tmp; // unsigned compare<br>RETURN_DATA = tmp.|
|70|FLAT_ATOMIC_SMAX|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (DATA > tmp) ? DATA : tmp; // signed compare<br>RETURN_DATA = tmp.|
|71|FLAT_ATOMIC_UMAX|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (DATA > tmp) ? DATA : tmp; // unsigned compare<br>RETURN_DATA = tmp.|



12.16. FLAT, Scratch and Global Instructions

193 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|72|FLAT_ATOMIC_AND|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] &= DATA;<br>RETURN_DATA = tmp.|
|73|FLAT_ATOMIC_OR|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] |= DATA;<br>RETURN_DATA = tmp.|
|74|FLAT_ATOMIC_XOR|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] ^= DATA;<br>RETURN_DATA = tmp.|
|75|FLAT_ATOMIC_INC|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (tmp >= DATA) ? 0 : tmp + 1; // unsigned compare<br>RETURN_DATA = tmp.|
|76|FLAT_ATOMIC_DEC|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (tmp == 0 || tmp > DATA) ? DATA : tmp - 1; //<br>unsigned compare<br>RETURN_DATA = tmp.|
|79|FLAT_ATOMIC_ADD_F64|// 64bit<br>tmp = MEM[ADDR];<br>D.f64 = tmp.f64 + DATA.f64;<br>MEM[ADDR] = D;<br>RETURN_DATA[0:1] = tmp.|
|80|FLAT_ATOMIC_MIN_F64|// 64bit<br>tmp = MEM[ADDR];<br>D.f64 = (DATA.f64 < tmp.f64) ? DATA.f64 : tmp.f64;<br>MEM[ADDR] = D;<br>RETURN_DATA[0:1] = tmp.|
|81|FLAT_ATOMIC_MAX_F64|// 64bit<br>tmp = MEM[ADDR];<br>D.f64 = (DATA.f64 < tmp.f64) ? DATA.f64 : tmp.f64;<br>MEM[ADDR] = D;<br>RETURN_DATA[0:1] = tmp.|
|96|FLAT_ATOMIC_SWAP_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|
|97|FLAT_ATOMIC_CMPSWAP_X2|// 64bit<br>tmp = MEM[ADDR];<br>src = DATA[0:1];<br>cmp = DATA[2:3];<br>MEM[ADDR] = (tmp == cmp) ? src : tmp;<br>RETURN_DATA[0:1] = tmp.|
|98|FLAT_ATOMIC_ADD_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] += DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|



12.16. FLAT, Scratch and Global Instructions

194 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|99|FLAT_ATOMIC_SUB_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] -= DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|
|100|FLAT_ATOMIC_SMIN_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] -= (DATA[0:1] < tmp) ? DATA[0:1] : tmp; // signed<br>compare<br>RETURN_DATA[0:1] = tmp.|
|101|FLAT_ATOMIC_UMIN_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] -= (DATA[0:1] < tmp) ? DATA[0:1] : tmp; // unsigned<br>compare<br>RETURN_DATA[0:1] = tmp.|
|102|FLAT_ATOMIC_SMAX_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] -= (DATA[0:1] > tmp) ? DATA[0:1] : tmp; // signed<br>compare<br>RETURN_DATA[0:1] = tmp.|
|103|FLAT_ATOMIC_UMAX_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] -= (DATA[0:1] > tmp) ? DATA[0:1] : tmp; // unsigned<br>compare<br>RETURN_DATA[0:1] = tmp.|
|104|FLAT_ATOMIC_AND_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] &= DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|
|105|FLAT_ATOMIC_OR_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] |= DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|
|106|FLAT_ATOMIC_XOR_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] ^= DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|
|107|FLAT_ATOMIC_INC_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (tmp >= DATA[0:1]) ? 0 : tmp + 1; // unsigned<br>compare<br>RETURN_DATA[0:1] = tmp.|
|108|FLAT_ATOMIC_DEC_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (tmp == 0 || tmp > DATA[0:1]) ? DATA[0:1] : tmp -<br>1; // unsigned compare<br>RETURN_DATA[0:1] = tmp.|



12.16. FLAT, Scratch and Global Instructions

195 of 267

"AMD Instinct MI200" Instruction Set Architecture



### **12.16.2. Scratch Instructions**

Scratch instructions are like Flat, but assume all workitem addresses fall in scratch (private) space.

|**Opcode**|**Name**|**Description**|
|---|---|---|
|16|SCRATCH_LOAD_UBYTE|Untyped buffer load unsigned byte (zero extend to VGPR<br>destination).|
|17|SCRATCH_LOAD_SBYTE|Untyped buffer load signed byte (sign extend to VGPR<br>destination).|
|18|SCRATCH_LOAD_USHORT|Untyped buffer load unsigned short (zero extend to VGPR<br>destination).|
|19|SCRATCH_LOAD_SSHORT|Untyped buffer load signed short (sign extend to VGPR<br>destination).|
|20|SCRATCH_LOAD_DWORD|Untyped buffer load dword.|
|21|SCRATCH_LOAD_DWORDX2|Untyped buffer load 2 dwords.|
|22|SCRATCH_LOAD_DWORDX3|Untyped buffer load 3 dwords.|
|23|SCRATCH_LOAD_DWORDX4|Untyped buffer load 4 dwords.|
|24|SCRATCH_STORE_BYTE|Untyped buffer store byte. Stores S0[7:0].|
|25|SCRATCH_STORE_BYTE_D16_<br>HI|Untyped buffer store byte. Stores S0[23:16].|
|26|SCRATCH_STORE_SHORT|Untyped buffer store short. Stores S0[15:0].|
|27|SCRATCH_STORE_SHORT_D16<br>_HI|Untyped buffer store short. Stores S0[31:16].|
|28|SCRATCH_STORE_DWORD|Untyped buffer store dword.|
|29|SCRATCH_STORE_DWORDX2|Untyped buffer store 2 dwords.|
|30|SCRATCH_STORE_DWORDX3|Untyped buffer store 3 dwords.|
|31|SCRATCH_STORE_DWORDX4|Untyped buffer store 4 dwords.|
|32|SCRATCH_LOAD_UBYTE_D16|D0[15:0] = {8'h0, MEM[ADDR]}.<br>Untyped buffer load unsigned byte.|
|33|SCRATCH_LOAD_UBYTE_D16_<br>HI|D0[31:16] = {8'h0, MEM[ADDR]}.<br>Untyped buffer load unsigned byte.|
|34|SCRATCH_LOAD_SBYTE_D16|D0[15:0] = {8'h0, MEM[ADDR]}.<br>Untyped buffer load signed byte.|
|35|SCRATCH_LOAD_SBYTE_D16_<br>HI|D0[31:16] = {8'h0, MEM[ADDR]}.<br>Untyped buffer load signed byte.|
|36|SCRATCH_LOAD_SHORT_D16|D0[15:0] = MEM[ADDR].<br>Untyped buffer load short.|



12.16. FLAT, Scratch and Global Instructions

196 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|37|SCRATCH_LOAD_SHORT_D16_<br>HI|D0[31:16] = MEM[ADDR].<br>Untyped buffer load short.|



### **12.16.3. Global Instructions**

Global instructions are like Flat, but assume all workitem addresses fall in global memory space.

|**Opcode**|**Name**|**Description**|
|---|---|---|
|16|GLOBAL_LOAD_UBYTE|Untyped buffer load unsigned byte (zero extend to VGPR<br>destination).|
|17|GLOBAL_LOAD_SBYTE|Untyped buffer load signed byte (sign extend to VGPR<br>destination).|
|18|GLOBAL_LOAD_USHORT|Untyped buffer load unsigned short (zero extend to VGPR<br>destination).|
|19|GLOBAL_LOAD_SSHORT|Untyped buffer load signed short (sign extend to VGPR<br>destination).|
|20|GLOBAL_LOAD_DWORD|Untyped buffer load dword.|
|21|GLOBAL_LOAD_DWORDX2|Untyped buffer load 2 dwords.|
|22|GLOBAL_LOAD_DWORDX3|Untyped buffer load 3 dwords.|
|23|GLOBAL_LOAD_DWORDX4|Untyped buffer load 4 dwords.|
|24|GLOBAL_STORE_BYTE|Untyped buffer store byte. Stores S0[7:0].|
|25|GLOBAL_STORE_BYTE_D16_HI|Untyped buffer store byte. Stores S0[23:16].|
|26|GLOBAL_STORE_SHORT|Untyped buffer store short. Stores S0[15:0].|
|27|GLOBAL_STORE_SHORT_D16_<br>HI|Untyped buffer store short. Stores S0[31:16].|
|28|GLOBAL_STORE_DWORD|Untyped buffer store dword.|
|29|GLOBAL_STORE_DWORDX2|Untyped buffer store 2 dwords.|
|30|GLOBAL_STORE_DWORDX3|Untyped buffer store 3 dwords.|
|31|GLOBAL_STORE_DWORDX4|Untyped buffer store 4 dwords.|
|32|GLOBAL_LOAD_UBYTE_D16|D0[15:0] = {8'h0, MEM[ADDR]}.<br>Untyped buffer load unsigned byte.|
|33|GLOBAL_LOAD_UBYTE_D16_HI|D0[31:16] = {8'h0, MEM[ADDR]}.<br>Untyped buffer load unsigned byte.|
|34|GLOBAL_LOAD_SBYTE_D16|D0[15:0] = {8'h0, MEM[ADDR]}.<br>Untyped buffer load signed byte.|
|35|GLOBAL_LOAD_SBYTE_D16_HI|D0[31:16] = {8'h0, MEM[ADDR]}.<br>Untyped buffer load signed byte.|



12.16. FLAT, Scratch and Global Instructions

197 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|36|GLOBAL_LOAD_SHORT_D16|D0[15:0] = MEM[ADDR].|
|||Untyped buffer load short.|
|37|GLOBAL_LOAD_SHORT_D16_HI|D0[31:16] = MEM[ADDR].|
|||Untyped buffer load short.|
|64|GLOBAL_ATOMIC_SWAP|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = DATA;<br>RETURN_DATA = tmp.|
|65|GLOBAL_ATOMIC_CMPSWAP|// 32bit<br>tmp = MEM[ADDR];<br>src = DATA[0];<br>cmp = DATA[1];<br>MEM[ADDR] = (tmp == cmp) ? src : tmp;<br>RETURN_DATA[0] = tmp.|
|66|GLOBAL_ATOMIC_ADD|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] += DATA;<br>RETURN_DATA = tmp.|
|67|GLOBAL_ATOMIC_SUB|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] -= DATA;<br>RETURN_DATA = tmp.|
|68|GLOBAL_ATOMIC_SMIN|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (DATA < tmp) ? DATA : tmp; // signed compare<br>RETURN_DATA = tmp.|
|69|GLOBAL_ATOMIC_UMIN|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (DATA < tmp) ? DATA : tmp; // unsigned compare<br>RETURN_DATA = tmp.|
|70|GLOBAL_ATOMIC_SMAX|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (DATA > tmp) ? DATA : tmp; // signed compare<br>RETURN_DATA = tmp.|
|71|GLOBAL_ATOMIC_UMAX|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (DATA > tmp) ? DATA : tmp; // unsigned compare<br>RETURN_DATA = tmp.|
|72|GLOBAL_ATOMIC_AND|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] &= DATA;<br>RETURN_DATA = tmp.|
|73|GLOBAL_ATOMIC_OR|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] |= DATA;<br>RETURN_DATA = tmp.|



12.16. FLAT, Scratch and Global Instructions

198 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|74|GLOBAL_ATOMIC_XOR|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] ^= DATA;<br>RETURN_DATA = tmp.|
|75|GLOBAL_ATOMIC_INC|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (tmp >= DATA) ? 0 : tmp + 1; // unsigned compare<br>RETURN_DATA = tmp.|
|76|GLOBAL_ATOMIC_DEC|// 32bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (tmp == 0 || tmp > DATA) ? DATA : tmp - 1; //<br>unsigned compare<br>RETURN_DATA = tmp.|
|77|GLOBAL_ATOMIC_ADD_F32|// 32bit<br>tmp = MEM[ADDR];<br>D.f = tmp.f + DATA.f;<br>MEM[ADDR] = D.|
|78|GLOBAL_ATOMIC_PK_ADD_F16|// 32bit<br>tmp = MEM[ADDR];<br>D.f16[31:16] = tmp.f16[31:16] + DATA.f16[31:16];<br>D.f16[15:0] = tmp.f16[15:0] + DATA.f16[15:0];<br>MEM[ADDR] = D.|
|79|GLOBAL_ATOMIC_ADD_F64|// 64bit<br>tmp = MEM[ADDR];<br>D.f64 = tmp.f64 + DATA.f64;<br>MEM[ADDR] = D;<br>RETURN_DATA[0:1] = tmp.|
|80|GLOBAL_ATOMIC_MIN_F64|// 64bit<br>tmp = MEM[ADDR];<br>D.f64 = (DATA.f64 < tmp.f64) ? DATA.f64 : tmp.f64;<br>MEM[ADDR] = D;<br>RETURN_DATA[0:1] = tmp.|
|81|GLOBAL_ATOMIC_MAX_F64|// 64bit<br>tmp = MEM[ADDR];<br>D.f64 = (DATA.f64 < tmp.f64) ? DATA.f64 : tmp.f64;<br>MEM[ADDR] = D;<br>RETURN_DATA[0:1] = tmp.|
|96|GLOBAL_ATOMIC_SWAP_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|
|97|GLOBAL_ATOMIC_CMPSWAP_<br>X2|// 64bit<br>tmp = MEM[ADDR];<br>src = DATA[0:1];<br>cmp = DATA[2:3];<br>MEM[ADDR] = (tmp == cmp) ? src : tmp;<br>RETURN_DATA[0:1] = tmp.|



12.16. FLAT, Scratch and Global Instructions

199 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode**|**Name**|**Description**|
|---|---|---|
|98|GLOBAL_ATOMIC_ADD_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] += DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|
|99|GLOBAL_ATOMIC_SUB_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] -= DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|
|100|GLOBAL_ATOMIC_SMIN_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] -= (DATA[0:1] < tmp) ? DATA[0:1] : tmp; // signed<br>compare<br>RETURN_DATA[0:1] = tmp.|
|101|GLOBAL_ATOMIC_UMIN_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] -= (DATA[0:1] < tmp) ? DATA[0:1] : tmp; // unsigned<br>compare<br>RETURN_DATA[0:1] = tmp.|
|102|GLOBAL_ATOMIC_SMAX_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] -= (DATA[0:1] > tmp) ? DATA[0:1] : tmp; // signed<br>compare<br>RETURN_DATA[0:1] = tmp.|
|103|GLOBAL_ATOMIC_UMAX_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] -= (DATA[0:1] > tmp) ? DATA[0:1] : tmp; // unsigned<br>compare<br>RETURN_DATA[0:1] = tmp.|
|104|GLOBAL_ATOMIC_AND_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] &= DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|
|105|GLOBAL_ATOMIC_OR_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] |= DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|
|106|GLOBAL_ATOMIC_XOR_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] ^= DATA[0:1];<br>RETURN_DATA[0:1] = tmp.|
|107|GLOBAL_ATOMIC_INC_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (tmp >= DATA[0:1]) ? 0 : tmp + 1; // unsigned<br>compare<br>RETURN_DATA[0:1] = tmp.|
|108|GLOBAL_ATOMIC_DEC_X2|// 64bit<br>tmp = MEM[ADDR];<br>MEM[ADDR] = (tmp == 0 || tmp > DATA[0:1]) ? DATA[0:1] : tmp -<br>1; // unsigned compare<br>RETURN_DATA[0:1] = tmp.|



12.16. FLAT, Scratch and Global Instructions

200 of 267

"AMD Instinct MI200" Instruction Set Architecture



## **12.17. Instruction Limitations**

### **12.17.1. DPP**

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

12.17. Instruction Limitations

201 of 267

"AMD Instinct MI200" Instruction Set Architecture



### **12.17.2. SDWA**

The following instructions cannot use SDWA:

- V_MAC_F32

- V_MADMK_F32

- V_MADAK_F32

- V_MAC_F16

- V_MADMK_F16

- V_MADAK_F16

- V_FMAC_F32

- V_READFIRSTLANE_B32

- V_CLREXCP

- V_SWAP_B32

12.17. Instruction Limitations

202 of 267
