---
name: docs-md-gfx90a-16-chapter-13-microcode-formats
description: "AMD CDNA2 ISA: Chapter 13. Microcode Formats (vendor documentation for AMD gfx90a (CDNA2))."
when: "when you need AMD CDNA2 ISA: Chapter 13. Microcode Formats while writing a AMD gfx90a (CDNA2) kernel."
---

"AMD Instinct MI200" Instruction Set Architecture



# **Chapter 13. Microcode Formats**

This section specifies the microcode formats. The definitions can be used to simplify compilation by providing standard templates and enumeration names for the various instruction formats.

Endian Order - The CDNA architecture addresses memory and registers using littleendian byteordering and bit-ordering. Multi-byte values are stored with their least-significant (low-order) byte (LSB) at the lowest byte address, and they are illustrated with their LSB at the right side. Byte values are stored with their least-significant (low-order) bit (lsb) at the lowest bit address, and they are illustrated with their lsb at the right side.

The table below summarizes the microcode formats and their widths. The sections that follow provide details

_Table 53. Summary of Microcode Formats_

|**Microcode Formats**|**Reference**|**Width (bits)**|
|---|---|---|
|**Scalar ALU and Control Formats**|||
|SOP2|SOP2|32|
|SOP1|SOP1||
|SOPK|SOPK||
|SOPP|SOPP||
|SOPC|SOPC||
|**Scalar Memory Format**|||
|SMEM|SMEM|64|
|**Vector ALU Format**|||
|VOP1|VOP1|32|
|VOP2|VOP2|32|
|VOPC|VOPC|32|
|VOP3A|VOP3A|64|
|VOP3B|VOP3B|64|
|VOP3P|VOP3P|64|
|VOP3P-MAI|VOP3P-MAI|64|
|DPP|DPP|32|
|SDWA|VOP2|32|
|**LDS/GDS Format**|||
|DS|DS|64|
|**Vector Memory Buffer Formats**|||
|MTBUF|MTBUF|64|



203 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Microcode Formats**|**Reference**|**Width (bits)**|
|---|---|---|
|MUBUF|MUBUF|64|
|**Vector Memory Image Format**|||
|MIMG|MIMG|64|
|**Flat Formats**|||
|FLAT|FLAT|64|
|GLOBAL|GLOBAL|64|
|SCRATCH|SCRATCH|64|



The field-definition tables that accompany the descriptions in the sections below use the following notation.

- int(2) - A two-bit field that specifies an unsigned integer value.

- enum(7) - A seven-bit field that specifies an enumerated set of values (in this case, a set of up to 27 values). The number of valid values can be less than the maximum.

The default value of all fields is zero. Any bitfield not identified is assumed to be reserved.

#### **Instruction Suffixes**

Most instructions include a suffix which indicates the data type the instruction handles. This suffix may also include a number which indicate the size of the data.

For example: "F32" indicates "32-bit floating point data", or "B16" is "16-bit binary data".

- B = binary

- F = floating point

- U = unsigned integer

- S = signed integer

When more than one data-type specifier occurs in an instruction, the last one is the result type and size, and the earlier one(s) is/are input data type and size.

## **13.1. Scalar ALU and Control Formats**

### **13.1.1. SOP2**

Scalar format with Two inputs, one output



13.1. Scalar ALU and Control Formats

204 of 267

"AMD Instinct MI200" Instruction Set Architecture



#### **Format**

#### SOP2

**Description** This is a scalar instruction with two inputs and one output. Can be followed by a 32-bit literal constant.

_Table 54. SOP2 Fields_

|**Field Name**|**Bits**|**Format or Description**|
|---|---|---|
|SSRC0|[7:0]|Source 0. First operand for the instruction.|
||0 - 101|SGPR0 to SGPR101: Scalar general-purpose registers.|
||102|FLAT_SCRATCH_LO.|
||103|FLAT_SCRATCH_HI.|
||104|XNACK_MASK_LO.|
||105|XNACK_MASK_HI.|
||106|VCC_LO: vcc[31:0].|
||107|VCC_HI: vcc[63:32].|
||108-123|TTMP0 - TTMP15: Trap handler temporary register.|
||124|M0. Memory register 0.|
||125|Reserved|
||126|EXEC_LO: exec[31:0].|
||127|EXEC_HI: exec[63:32].|
||128|0.|
||129-192|Signed integer 1 to 64.|
||193-208|Signed integer -1 to -16.|
||209-234|Reserved.|
||235|SHARED_BASE (Memory Aperture definition).|
||236|SHARED_LIMIT (Memory Aperture definition).|
||237|PRIVATE_BASE (Memory Aperture definition).|
||238|PRIVATE_LIMIT (Memory Aperture definition).|
||239|POPS_EXITING_WAVE_ID .|
||240|0.5.|
||241|-0.5.|
||242|1.0.|
||243|-1.0.|
||244|2.0.|
||245|-2.0.|
||246|4.0.|
||247|-4.0.|
||248|1/(2*PI).|
||249 - 250|Reserved.|
||251|VCCZ.|
||252|EXECZ.|
||253|SCC.|
||254|Reserved.|
||255|Literal constant.|
|SSRC1|[15:8]|Second scalar source operand.|
|||Same codes as SSRC0, above.|
|SDST|[22:16]|Scalar destination.|
|||Same codes as SSRC0, above except only codes 0-127 are valid.|
|OP|[29:23]|See Opcode table below.|



13.1. Scalar ALU and Control Formats

205 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Field Name**|**Bits**|**Format or Description**|
|---|---|---|
|ENCODING|[31:30]|Must be: 10|



_Table 55. SOP2 Opcodes_

|**Opcode**|**#**<br>**Name**|
|---|---|
|0|S_ADD_U32|
|1|S_SUB_U32|
|2|S_ADD_I32|
|3|S_SUB_I32|
|4|S_ADDC_U32|
|5|S_SUBB_U32|
|6|S_MIN_I32|
|7|S_MIN_U32|
|8|S_MAX_I32|
|9|S_MAX_U32|
|10|S_CSELECT_B32|
|11|S_CSELECT_B64|
|12|S_AND_B32|
|13|S_AND_B64|
|14|S_OR_B32|
|15|S_OR_B64|
|16|S_XOR_B32|
|17|S_XOR_B64|
|18|S_ANDN2_B32|
|19|S_ANDN2_B64|
|20|S_ORN2_B32|
|21|S_ORN2_B64|
|22|S_NAND_B32|
|23|S_NAND_B64|
|24|S_NOR_B32|
|25|S_NOR_B64|
|26|S_XNOR_B32|
|27|S_XNOR_B64|
|28|S_LSHL_B32|
|29|S_LSHL_B64|



13.1. Scalar ALU and Control Formats

206 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode #**|**Name**|
|---|---|
|30|S_LSHR_B32|
|31|S_LSHR_B64|
|32|S_ASHR_I32|
|33|S_ASHR_I64|
|34|S_BFM_B32|
|35|S_BFM_B64|
|36|S_MUL_I32|
|37|S_BFE_U32|
|38|S_BFE_I32|
|39|S_BFE_U64|
|40|S_BFE_I64|
|41|S_CBRANCH_G_FORK|
|42|S_ABSDIFF_I32|
|43|S_RFE_RESTORE_B64|
|44|S_MUL_HI_U32|
|45|S_MUL_HI_I32|
|46|S_LSHL1_ADD_U32|
|47|S_LSHL2_ADD_U32|
|48|S_LSHL3_ADD_U32|
|49|S_LSHL4_ADD_U32|
|50|S_PACK_LL_B32_B16|
|51|S_PACK_LH_B32_B16|
|52|S_PACK_HH_B32_B16|



### **13.1.2. SOPK**



**Format** SOPK

**Description** This is a scalar instruction with one 16-bit signed immediate (SIMM16) input and a single destination. Instructions which take 2 inputs use the destination as the second input.

_Table 56. SOPK Fields_

13.1. Scalar ALU and Control Formats

207 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Field Name**|**Bits**|**Format or Description**|
|---|---|---|
|SIMM16|[15:0]|Signed immediate 16-bit value.|
|SDST|[22:16]|Scalar destination, and can provide second source operand.|
||0 - 101|SGPR0 to SGPR101: Scalar general-purpose registers.|
||102|FLAT_SCRATCH_LO.|
||103|FLAT_SCRATCH_HI.|
||104|XNACK_MASK_LO.|
||105|XNACK_MASK_HI.|
||106|VCC_LO: vcc[31:0].|
||107|VCC_HI: vcc[63:32].|
||108-123|TTMP0 - TTMP15: Trap handler temporary register.|
||124|M0. Memory register 0.|
||125|Reserved|
||126|EXEC_LO: exec[31:0].|
||127|EXEC_HI: exec[63:32].|
|OP|[27:23]|See Opcode table below.|
|ENCODING|[31:28]|Must be: 1011|



_Table 57. SOPK Opcodes_

|**Opcode #**|**Name**|
|---|---|
|0|S_MOVK_I32|
|1|S_CMOVK_I32|
|2|S_CMPK_EQ_I32|
|3|S_CMPK_LG_I32|
|4|S_CMPK_GT_I32|
|5|S_CMPK_GE_I32|
|6|S_CMPK_LT_I32|
|7|S_CMPK_LE_I32|
|8|S_CMPK_EQ_U32|
|9|S_CMPK_LG_U32|
|10|S_CMPK_GT_U32|
|11|S_CMPK_GE_U32|
|12|S_CMPK_LT_U32|
|13|S_CMPK_LE_U32|
|14|S_ADDK_I32|
|15|S_MULK_I32|
|16|S_CBRANCH_I_FORK|
|17|S_GETREG_B32|
|18|S_SETREG_B32|
|20|S_SETREG_IMM32_B32|



13.1. Scalar ALU and Control Formats

208 of 267

"AMD Instinct MI200" Instruction Set Architecture





<!-- Start of picture text -->
Opcode # Name<br>21 S_CALL_B64<br><!-- End of picture text -->

### **13.1.3. SOP1**



**Format** SOP1

**Description** This is a scalar instruction with two inputs and one output. Can be followed by a 32-bit literal constant.

_Table 58. SOP1 Fields_

13.1. Scalar ALU and Control Formats

209 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Field Name**|**Bits**|**Format or Description**|
|---|---|---|
|SSRC0|[7:0]|Source 0. First operand for the instruction.|
||0 - 101|SGPR0 to SGPR101: Scalar general-purpose registers.|
||102|FLAT_SCRATCH_LO.|
||103|FLAT_SCRATCH_HI.|
||104|XNACK_MASK_LO.|
||105|XNACK_MASK_HI.|
||106|VCC_LO: vcc[31:0].|
||107|VCC_HI: vcc[63:32].|
||108-123|TTMP0 - TTMP15: Trap handler temporary register.|
||124|M0. Memory register 0.|
||125|Reserved|
||126|EXEC_LO: exec[31:0].|
||127|EXEC_HI: exec[63:32].|
||128|0.|
||129-192|Signed integer 1 to 64.|
||193-208|Signed integer -1 to -16.|
||209-234|Reserved.|
||235|SHARED_BASE (Memory Aperture definition).|
||236|SHARED_LIMIT (Memory Aperture definition).|
||237|PRIVATE_BASE (Memory Aperture definition).|
||238|PRIVATE_LIMIT (Memory Aperture definition).|
||239|POPS_EXITING_WAVE_ID .|
||240|0.5.|
||241|-0.5.|
||242|1.0.|
||243|-1.0.|
||244|2.0.|
||245|-2.0.|
||246|4.0.|
||247|-4.0.|
||248|1/(2*PI).|
||249 - 250|Reserved.|
||251|VCCZ.|
||252|EXECZ.|
||253|SCC.|
||254|Reserved.|
||255|Literal constant.|
|OP|[15:8]|See Opcode table below.|
|SDST|[22:16]|Scalar destination.|
|||Same codes as SSRC0, above except only codes 0-127 are valid.|
|ENCODING|[31:23]|Must be: 10_1111101|



##### _Table 59. SOP1 Opcodes_

|**Opcode #**|**Name**|
|---|---|
|0|S_MOV_B32|
|1|S_MOV_B64|
|2|S_CMOV_B32|
|3|S_CMOV_B64|



13.1. Scalar ALU and Control Formats

210 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode #**|**Name**|
|---|---|
|4|S_NOT_B32|
|5|S_NOT_B64|
|6|S_WQM_B32|
|7|S_WQM_B64|
|8|S_BREV_B32|
|9|S_BREV_B64|
|10|S_BCNT0_I32_B32|
|11|S_BCNT0_I32_B64|
|12|S_BCNT1_I32_B32|
|13|S_BCNT1_I32_B64|
|14|S_FF0_I32_B32|
|15|S_FF0_I32_B64|
|16|S_FF1_I32_B32|
|17|S_FF1_I32_B64|
|18|S_FLBIT_I32_B32|
|19|S_FLBIT_I32_B64|
|20|S_FLBIT_I32|
|21|S_FLBIT_I32_I64|
|22|S_SEXT_I32_I8|
|23|S_SEXT_I32_I16|
|24|S_BITSET0_B32|
|25|S_BITSET0_B64|
|26|S_BITSET1_B32|
|27|S_BITSET1_B64|
|28|S_GETPC_B64|
|29|S_SETPC_B64|
|30|S_SWAPPC_B64|
|31|S_RFE_B64|
|32|S_AND_SAVEEXEC_B64|
|33|S_OR_SAVEEXEC_B64|
|34|S_XOR_SAVEEXEC_B64|
|35|S_ANDN2_SAVEEXEC_B64|
|36|S_ORN2_SAVEEXEC_B64|
|37|S_NAND_SAVEEXEC_B64|



13.1. Scalar ALU and Control Formats

211 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode #**|**Name**|
|---|---|
|38|S_NOR_SAVEEXEC_B64|
|39|S_XNOR_SAVEEXEC_B64|
|40|S_QUADMASK_B32|
|41|S_QUADMASK_B64|
|42|S_MOVRELS_B32|
|43|S_MOVRELS_B64|
|44|S_MOVRELD_B32|
|45|S_MOVRELD_B64|
|46|S_CBRANCH_JOIN|
|48|S_ABS_I32|
|50|S_SET_GPR_IDX_IDX|
|51|S_ANDN1_SAVEEXEC_B64|
|52|S_ORN1_SAVEEXEC_B64|
|53|S_ANDN1_WREXEC_B64|
|54|S_ANDN2_WREXEC_B64|
|55|S_BITREPLICATE_B64_B32|



### **13.1.4. SOPC**



**Format** SOPC **Description** This is a scalar instruction with two inputs which are compared and produces SCC as a result. Can be followed by a 32-bit literal constant.

_Table 60. SOPC Fields_

13.1. Scalar ALU and Control Formats

212 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Field Name**|**Bits**|**Format or Description**|
|---|---|---|
|SSRC0|[7:0]|Source 0. First operand for the instruction.|
||0 - 101|SGPR0 to SGPR101: Scalar general-purpose registers.|
||102|FLAT_SCRATCH_LO.|
||103|FLAT_SCRATCH_HI.|
||104|XNACK_MASK_LO.|
||105|XNACK_MASK_HI.|
||106|VCC_LO: vcc[31:0].|
||107|VCC_HI: vcc[63:32].|
||108-123|TTMP0 - TTMP15: Trap handler temporary register.|
||124|M0. Memory register 0.|
||125|Reserved|
||126|EXEC_LO: exec[31:0].|
||127|EXEC_HI: exec[63:32].|
||128|0.|
||129-192|Signed integer 1 to 64.|
||193-208|Signed integer -1 to -16.|
||209-234|Reserved.|
||235|SHARED_BASE (Memory Aperture definition).|
||236|SHARED_LIMIT (Memory Aperture definition).|
||237|PRIVATE_BASE (Memory Aperture definition).|
||238|PRIVATE_LIMIT (Memory Aperture definition).|
||239|POPS_EXITING_WAVE_ID .|
||240|0.5.|
||241|-0.5.|
||242|1.0.|
||243|-1.0.|
||244|2.0.|
||245|-2.0.|
||246|4.0.|
||247|-4.0.|
||248|1/(2*PI).|
||249 - 250|Reserved.|
||251|VCCZ.|
||252|EXECZ.|
||253|SCC.|
||254|Reserved.|
||255|Literal constant.|
|SSRC1|[15:8]|Second scalar source operand.|
|||Same codes as SSRC0, above.|
|OP|[22:16]|See Opcode table below.|
|ENCODING|[31:23]|Must be: 10_1111110|



##### _Table 61. SOPC Opcodes_

|**Opcode #**|**Name**|
|---|---|
|0|S_CMP_EQ_I32|
|1|S_CMP_LG_I32|
|2|S_CMP_GT_I32|
|3|S_CMP_GE_I32|



13.1. Scalar ALU and Control Formats

213 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode #**|**Name**|
|---|---|
|4|S_CMP_LT_I32|
|5|S_CMP_LE_I32|
|6|S_CMP_EQ_U32|
|7|S_CMP_LG_U32|
|8|S_CMP_GT_U32|
|9|S_CMP_GE_U32|
|10|S_CMP_LT_U32|
|11|S_CMP_LE_U32|
|12|S_BITCMP0_B32|
|13|S_BITCMP1_B32|
|14|S_BITCMP0_B64|
|15|S_BITCMP1_B64|
|16|S_SETVSKIP|
|17|S_SET_GPR_IDX_ON|
|18|S_CMP_EQ_U64|
|19|S_CMP_LG_U64|



### **13.1.5. SOPP**



**Format** SOPP

**Description** This is a scalar instruction with one 16-bit signed immediate (SIMM16) input.

_Table 62. SOPP Fields_

|**Field Name**|**Bits**|**Format or Description**|
|---|---|---|
|SIMM16|[15:0]|Signed immediate 16-bit value.|
|OP|[22:16]|See Opcode table below.|
|ENCODING|[31:23]|Must be: 10_1111111|



_Table 63. SOPP Opcodes_

13.1. Scalar ALU and Control Formats

214 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode #**|**Name**|
|---|---|
|0|S_NOP|
|1|S_ENDPGM|
|2|S_BRANCH|
|3|S_WAKEUP|
|4|S_CBRANCH_SCC0|
|5|S_CBRANCH_SCC1|
|6|S_CBRANCH_VCCZ|
|7|S_CBRANCH_VCCNZ|
|8|S_CBRANCH_EXECZ|
|9|S_CBRANCH_EXECNZ|
|10|S_BARRIER|
|11|S_SETKILL|
|12|S_WAITCNT|
|13|S_SETHALT|
|14|S_SLEEP|
|15|S_SETPRIO|
|16|S_SENDMSG|
|17|S_SENDMSGHALT|
|18|S_TRAP|
|19|S_ICACHE_INV|
|20|S_INCPERFLEVEL|
|21|S_DECPERFLEVEL|
|23|S_CBRANCH_CDBGSYS|
|24|S_CBRANCH_CDBGUSER|
|25|S_CBRANCH_CDBGSYS_OR_USER|
|26|S_CBRANCH_CDBGSYS_AND_USER|
|27|S_ENDPGM_SAVED|
|28|S_SET_GPR_IDX_OFF|
|29|S_SET_GPR_IDX_MODE|
|30|S_ENDPGM_ORDERED_PS_DONE|



## **13.2. Scalar Memory Format**

13.2. Scalar Memory Format

215 of 267

"AMD Instinct MI200" Instruction Set Architecture



### **13.2.1. SMEM**



#### **Format** SMEM

#### **Description** Scalar Memory data load/store

_Table 64. SMEM Fields_

|**Field Name**|**Bits**|**Format or Description**|
|---|---|---|
|SBASE|[5:0]|SGPR-pair which provides base address or SGPR-quad which provides V#.<br>(LSB of SGPR address is omitted).|
|SDATA|[12:6]|SGPR which provides write data or accepts return data.|
|SOE|[14]|Scalar offset enable.|
|NV|[15]|Non-volatile|
|GLC|[16]|Globally memory Coherent. Force bypass of L1 cache, or for atomics, cause<br>pre-op value to be returned.|
|IMM|[17]|Immediate enable.|
|OP|[25:18]|See Opcode table below.|
|ENCODING|[31:26]|Must be: 110000|
|OFFSET|[52:32]|An immediate signed byte offset, or the address of an SGPR holding the<br>unsigned byte offset. Signed offsets only work with S_LOAD/STORE.|
|SOFFSET|[63:57]|SGPR offset. Used only when SOFFSET_EN = 1 May only specify an SGPR<br>or M0.|



_Table 65. SMEM Opcodes_

|**Opcode #**|**Name**|
|---|---|
|0|S_LOAD_DWORD|
|1|S_LOAD_DWORDX2|
|2|S_LOAD_DWORDX4|
|3|S_LOAD_DWORDX8|
|4|S_LOAD_DWORDX16|
|5|S_SCRATCH_LOAD_DWORD|
|6|S_SCRATCH_LOAD_DWORDX2|
|7|S_SCRATCH_LOAD_DWORDX4|
|8|S_BUFFER_LOAD_DWORD|



13.2. Scalar Memory Format

216 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode #**|**Name**||
|---|---|---|
|9|S_BUFFER_|LOAD_DWORDX2|
|10|S_BUFFER_|LOAD_DWORDX4|
|11|S_BUFFER_|LOAD_DWORDX8|
|12|S_BUFFER_|LOAD_DWORDX16|
|16|S_STORE_D|WORD|
|17|S_STORE_D|WORDX2|
|18|S_STORE_D|WORDX4|
|21|S_SCRATC|H_STORE_DWORD|
|22|S_SCRATC|H_STORE_DWORDX2|
|23|S_SCRATC|H_STORE_DWORDX4|
|24|S_BUFFER_|STORE_DWORD|
|25|S_BUFFER_|STORE_DWORDX2|
|26|S_BUFFER_|STORE_DWORDX4|
|32|S_DCACHE|_INV|
|33|S_DCACHE|_WB|
|34|S_DCACHE|_INV_VOL|
|35|S_DCACHE|_WB_VOL|
|36|S_MEMTIM|E|
|37|S_MEMREA|LTIME|
|38|S_ATC_PRO|BE|
|39|S_ATC_PRO|BE_BUFFER|
|40|S_DCACHE|_DISCARD|
|41|S_DCACHE|_DISCARD_X2|
|64|S_BUFFER_|ATOMIC_SWAP|
|65|S_BUFFER_|ATOMIC_CMPSWAP|
|66|S_BUFFER_|ATOMIC_ADD|
|67|S_BUFFER_|ATOMIC_SUB|
|68|S_BUFFER_|ATOMIC_SMIN|
|69|S_BUFFER_|ATOMIC_UMIN|
|70|S_BUFFER_|ATOMIC_SMAX|
|71|S_BUFFER_|ATOMIC_UMAX|
|72|S_BUFFER_|ATOMIC_AND|
|73|S_BUFFER_|ATOMIC_OR|
|74|S_BUFFER_|ATOMIC_XOR|



13.2. Scalar Memory Format

217 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode #**|**Name**||
|---|---|---|
|75|S_BUFFER|_ATOMIC_INC|
|76|S_BUFFER|_ATOMIC_DEC|
|96|S_BUFFER|_ATOMIC_SWAP_X2|
|97|S_BUFFER|_ATOMIC_CMPSWAP_X2|
|98|S_BUFFER|_ATOMIC_ADD_X2|
|99|S_BUFFER|_ATOMIC_SUB_X2|
|100|S_BUFFER|_ATOMIC_SMIN_X2|
|101|S_BUFFER|_ATOMIC_UMIN_X2|
|102|S_BUFFER|_ATOMIC_SMAX_X2|
|103|S_BUFFER|_ATOMIC_UMAX_X2|
|104|S_BUFFER|_ATOMIC_AND_X2|
|105|S_BUFFER|_ATOMIC_OR_X2|
|106|S_BUFFER|_ATOMIC_XOR_X2|
|107|S_BUFFER|_ATOMIC_INC_X2|
|108|S_BUFFER|_ATOMIC_DEC_X2|
|128|S_ATOMIC_|SWAP|
|129|S_ATOMIC_|CMPSWAP|
|130|S_ATOMIC_|ADD|
|131|S_ATOMIC_|SUB|
|132|S_ATOMIC_|SMIN|
|133|S_ATOMIC_|UMIN|
|134|S_ATOMIC_|SMAX|
|135|S_ATOMIC_|UMAX|
|136|S_ATOMIC_|AND|
|137|S_ATOMIC_|OR|
|138|S_ATOMIC_|XOR|
|139|S_ATOMIC_|INC|
|140|S_ATOMIC_|DEC|
|160|S_ATOMIC_|SWAP_X2|
|161|S_ATOMIC_|CMPSWAP_X2|
|162|S_ATOMIC_|ADD_X2|
|163|S_ATOMIC_|SUB_X2|
|164|S_ATOMIC_|SMIN_X2|
|165|S_ATOMIC_|UMIN_X2|



13.2. Scalar Memory Format

218 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode #**|**Name**|
|---|---|
|166|S_ATOMIC_SMAX_X2|
|167|S_ATOMIC_UMAX_X2|
|168|S_ATOMIC_AND_X2|
|169|S_ATOMIC_OR_X2|
|170|S_ATOMIC_XOR_X2|
|171|S_ATOMIC_INC_X2|
|172|S_ATOMIC_DEC_X2|



## **13.3. Vector ALU Formats**

### **13.3.1. VOP2**



**Format** VOP2

**Description** Vector ALU format with two operands

_Table 66. VOP2 Fields_

219 of 267

13.3. Vector ALU Formats

"AMD Instinct MI200" Instruction Set Architecture



|**Field Name**|**Bits**|**Format or Description**|
|---|---|---|
|SRC0|[8:0]|Source 0. First operand for the instruction.|
||0 - 101|SGPR0 to SGPR101: Scalar general-purpose registers.|
||102|FLAT_SCRATCH_LO.|
||103|FLAT_SCRATCH_HI.|
||104|XNACK_MASK_LO.|
||105|XNACK_MASK_HI.|
||106|VCC_LO: vcc[31:0].|
||107|VCC_HI: vcc[63:32].|
||108-123|TTMP0 - TTMP15: Trap handler temporary register.|
||124|M0. Memory register 0.|
||125|Reserved|
||126|EXEC_LO: exec[31:0].|
||127|EXEC_HI: exec[63:32].|
||128|0.|
||129-192|Signed integer 1 to 64.|
||193-208|Signed integer -1 to -16.|
||209-234|Reserved.|
||235|SHARED_BASE (Memory Aperture definition).|
||236|SHARED_LIMIT (Memory Aperture definition).|
||237|PRIVATE_BASE (Memory Aperture definition).|
||238|PRIVATE_LIMIT (Memory Aperture definition).|
||239|POPS_EXITING_WAVE_ID .|
||240|0.5.|
||241|-0.5.|
||242|1.0.|
||243|-1.0.|
||244|2.0.|
||245|-2.0.|
||246|4.0.|
||247|-4.0.|
||248|1/(2*PI).|
||249|SDWA|
||250|DPP|
||251|VCCZ.|
||252|EXECZ.|
||253|SCC.|
||254|Reserved.|
||255|Literal constant.|
||256 - 511|VGPR 0 - 255|
|VSRC1|[16:9]|VGPR which provides the second operand.|
|VDST|[24:17]|Destination VGPR.|
|OP|[30:25]|See Opcode table below.|
|ENCODING|[31]|Must be: 0|



##### _Table 67. VOP2 Opcodes_

|**Opcode #**|**Name**|
|---|---|
|0|V_CNDMASK_B32|
|1|V_ADD_F32|



220 of 267

13.3. Vector ALU Formats

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode #**<br>**N**|**ame**|
|---|---|
|2<br>V_|SUB_F32|
|3<br>V_|SUBREV_F32|
|4<br>V_|FMAC_F64|
|5<br>V_|MUL_F32|
|6<br>V_|MUL_I32_I24|
|7<br>V_|MUL_HI_I32_I24|
|8<br>V_|MUL_U32_U24|
|9<br>V_|MUL_HI_U32_U24|
|10<br>V_|MIN_F32|
|11<br>V_|MAX_F32|
|12<br>V_|MIN_I32|
|13<br>V_|MAX_I32|
|14<br>V_|MIN_U32|
|15<br>V_|MAX_U32|
|16<br>V_|LSHRREV_B32|
|17<br>V_|ASHRREV_I32|
|18<br>V_|LSHLREV_B32|
|19<br>V_|AND_B32|
|20<br>V_|OR_B32|
|21<br>V_|XOR_B32|
|22<br>V_|MAC_F32|
|23<br>V_|MADMK_F32|
|24<br>V_|MADAK_F32|
|25<br>V_|ADD_CO_U32|
|26<br>V_|SUB_CO_U32|
|27<br>V_|SUBREV_CO_U32|
|28<br>V_|ADDC_CO_U32|
|29<br>V_|SUBB_CO_U32|
|30<br>V_|SUBBREV_CO_U32|
|31<br>V_|ADD_F16|
|32<br>V_|SUB_F16|
|33<br>V_|SUBREV_F16|
|34<br>V_|MUL_F16|
|35<br>V_|MAC_F16|



221 of 267

13.3. Vector ALU Formats

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode #**|**Name**|
|---|---|
|36|V_MADMK_F16|
|37|V_MADAK_F16|
|38|V_ADD_U16|
|39|V_SUB_U16|
|40|V_SUBREV_U16|
|41|V_MUL_LO_U16|
|42|V_LSHLREV_B16|
|43|V_LSHRREV_B16|
|44|V_ASHRREV_I16|
|45|V_MAX_F16|
|46|V_MIN_F16|
|47|V_MAX_U16|
|48|V_MAX_I16|
|49|V_MIN_U16|
|50|V_MIN_I16|
|51|V_LDEXP_F16|
|52|V_ADD_U32|
|53|V_SUB_U32|
|54|V_SUBREV_U32|
|55|V_DOT2C_F32_F16|
|56|V_DOT2C_I32_I16|
|57|V_DOT4C_I32_I8|
|58|V_DOT8C_I32_I4|
|59|V_FMAC_F32|
|60|V_PK_FMAC_F16|
|61|V_XNOR_B32|



### **13.3.2. VOP1**



**Format** VOP1

222 of 267

13.3. Vector ALU Formats

"AMD Instinct MI200" Instruction Set Architecture



#### **Description** Vector ALU format with one operand

_Table 68. VOP1 Fields_

|**Field Name**|**Bits**|**Format or Description**|
|---|---|---|
|SRC0|[8:0]|Source 0. First operand for the instruction.|
||0 - 101|SGPR0 to SGPR101: Scalar general-purpose registers.|
||102|FLAT_SCRATCH_LO.|
||103|FLAT_SCRATCH_HI.|
||104|XNACK_MASK_LO.|
||105|XNACK_MASK_HI.|
||106|VCC_LO: vcc[31:0].|
||107|VCC_HI: vcc[63:32].|
||108-123|TTMP0 - TTMP15: Trap handler temporary register.|
||124|M0. Memory register 0.|
||125|Reserved|
||126|EXEC_LO: exec[31:0].|
||127|EXEC_HI: exec[63:32].|
||128|0.|
||129-192|Signed integer 1 to 64.|
||193-208|Signed integer -1 to -16.|
||209-234|Reserved.|
||235|SHARED_BASE (Memory Aperture definition).|
||236|SHARED_LIMIT (Memory Aperture definition).|
||237|PRIVATE_BASE (Memory Aperture definition).|
||238|PRIVATE_LIMIT (Memory Aperture definition).|
||239|POPS_EXITING_WAVE_ID .|
||240|0.5.|
||241|-0.5.|
||242|1.0.|
||243|-1.0.|
||244|2.0.|
||245|-2.0.|
||246|4.0.|
||247|-4.0.|
||248|1/(2*PI).|
||249|SDWA|
||250|DPP|
||251|VCCZ.|
||252|EXECZ.|
||253|SCC.|
||254|Reserved.|
||255|Literal constant.|
||256 - 511|VGPR 0 - 255|
|OP|[16:9]|See Opcode table below.|
|VDST|[24:17]|Destination VGPR.|
|ENCODING|[31:25]|Must be: 0_111111|



_Table 69. VOP1 Opcodes_

223 of 267

13.3. Vector ALU Formats

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode #**|**Name**|
|---|---|
|0|V_NOP|
|1|V_MOV_B32|
|2|V_READFIRSTLANE_B32|
|3|V_CVT_I32_F64|
|4|V_CVT_F64_I32|
|5|V_CVT_F32_I32|
|6|V_CVT_F32_U32|
|7|V_CVT_U32_F32|
|8|V_CVT_I32_F32|
|10|V_CVT_F16_F32|
|11|V_CVT_F32_F16|
|12|V_CVT_RPI_I32_F32|
|13|V_CVT_FLR_I32_F32|
|14|V_CVT_OFF_F32_I4|
|15|V_CVT_F32_F64|
|16|V_CVT_F64_F32|
|17|V_CVT_F32_UBYTE0|
|18|V_CVT_F32_UBYTE1|
|19|V_CVT_F32_UBYTE2|
|20|V_CVT_F32_UBYTE3|
|21|V_CVT_U32_F64|
|22|V_CVT_F64_U32|
|23|V_TRUNC_F64|
|24|V_CEIL_F64|
|25|V_RNDNE_F64|
|26|V_FLOOR_F64|
|27|V_FRACT_F32|
|28|V_TRUNC_F32|
|29|V_CEIL_F32|
|30|V_RNDNE_F32|
|31|V_FLOOR_F32|
|32|V_EXP_F32|
|33|V_LOG_F32|
|34|V_RCP_F32|



224 of 267

13.3. Vector ALU Formats

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode #**|**Name**|
|---|---|
|35|V_RCP_IFLAG_F32|
|36|V_RSQ_F32|
|37|V_RCP_F64|
|38|V_RSQ_F64|
|39|V_SQRT_F32|
|40|V_SQRT_F64|
|41|V_SIN_F32|
|42|V_COS_F32|
|43|V_NOT_B32|
|44|V_BFREV_B32|
|45|V_FFBH_U32|
|46|V_FFBL_B32|
|47|V_FFBH_I32|
|48|V_FREXP_EXP_I32_F64|
|49|V_FREXP_MANT_F64|
|50|V_FRACT_F64|
|51|V_FREXP_EXP_I32_F32|
|52|V_FREXP_MANT_F32|
|53|V_CLREXCP|
|55|V_SCREEN_PARTITION_4SE_B32|
|57|V_CVT_F16_U16|
|58|V_CVT_F16_I16|
|59|V_CVT_U16_F16|
|60|V_CVT_I16_F16|
|61|V_RCP_F16|
|62|V_SQRT_F16|
|63|V_RSQ_F16|
|64|V_LOG_F16|
|65|V_EXP_F16|
|66|V_FREXP_MANT_F16|
|67|V_FREXP_EXP_I16_F16|
|68|V_FLOOR_F16|
|69|V_CEIL_F16|
|70|V_TRUNC_F16|



225 of 267

13.3. Vector ALU Formats

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode #**|**Name**|
|---|---|
|71|V_RNDNE_F16|
|72|V_FRACT_F16|
|73|V_SIN_F16|
|74|V_COS_F16|
|75|V_EXP_LEGACY_F32|
|76|V_LOG_LEGACY_F32|
|77|V_CVT_NORM_I16_F16|
|78|V_CVT_NORM_U16_F16|
|79|V_SAT_PK_U8_I16|
|81|V_SWAP_B32|
|82|V_ACCVGPR_MOV_B32|



### **13.3.3. VOPC**



**Format** VOPC

- **Description** Vector instruction taking two inputs and producing a comparison result. Can be followed by a 32- bit literal constant. Vector Comparison operations are divided into three groups:

   - those which can use any one of 16 comparison operations,

   - those which can use any one of 8, and

   - those which have a single comparison operation.

The final opcode number is determined by adding the base for the opcode family plus the offset from the compare op. Every compare instruction writes a result to VCC (for VOPC) or an SGPR (for VOP3). Additionally, compare instruction have variants that also writes to the EXEC mask. The destination of the compare result is always VCC when encoded using the VOPC format, and can be an arbitrary SGPR when encoded in the VOP3 format.

#### **Comparison Operations**

_Table 70. Comparison Operations_

|**Compare Operation**|**Opcode**|**Description**|
|---|---|---|
||**Offset**||
|Sixteen Compare Oper|ations (OP16)||



226 of 267

13.3. Vector ALU Formats

"AMD Instinct MI200" Instruction Set Architecture



|**Compare Operation**|**Opcode**<br>**Offset**|**Description**|
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
|Eight Compare Operati|ons (OP8)||
|F|0|D.u = 0|
|LT|1|D.u = (S0 < S1)|
|EQ|2|D.u = (S0 == S1)|
|LE|3|D.u = (S0 <= S1)|
|GT|4|D.u = (S0 > S1)|
|LG|5|D.u = (S0 <> S1)|
|GE|6|D.u = (S0 >= S1)|
|TRU|7|D.u = 1|



_Table 71. VOPC Fields_

227 of 267

13.3. Vector ALU Formats

"AMD Instinct MI200" Instruction Set Architecture



|**Field Name**|**Bits**|**Format or Description**|
|---|---|---|
|SRC0|[8:0]|Source 0. First operand for the instruction.|
||0 - 101|SGPR0 to SGPR101: Scalar general-purpose registers.|
||102|FLAT_SCRATCH_LO.|
||103|FLAT_SCRATCH_HI.|
||104|XNACK_MASK_LO.|
||105|XNACK_MASK_HI.|
||106|VCC_LO: vcc[31:0].|
||107|VCC_HI: vcc[63:32].|
||108-123|TTMP0 - TTMP15: Trap handler temporary register.|
||124|M0. Memory register 0.|
||125|Reserved|
||126|EXEC_LO: exec[31:0].|
||127|EXEC_HI: exec[63:32].|
||128|0.|
||129-192|Signed integer 1 to 64.|
||193-208|Signed integer -1 to -16.|
||209-234|Reserved.|
||235|SHARED_BASE (Memory Aperture definition).|
||236|SHARED_LIMIT (Memory Aperture definition).|
||237|PRIVATE_BASE (Memory Aperture definition).|
||238|PRIVATE_LIMIT (Memory Aperture definition).|
||239|POPS_EXITING_WAVE_ID .|
||240|0.5.|
||241|-0.5.|
||242|1.0.|
||243|-1.0.|
||244|2.0.|
||245|-2.0.|
||246|4.0.|
||247|-4.0.|
||248|1/(2*PI).|
||249|SDWA|
||250|DPP|
||251|VCCZ.|
||252|EXECZ.|
||253|SCC.|
||254|Reserved.|
||255|Literal constant.|
||256 - 511|VGPR 0 - 255|
|VSRC1|[16:9]|VGPR which provides the second operand.|
|OP|[24:17]|See Opcode table below.|
|ENCODING|[31:25]|Must be: 0_111110|



##### _Table 72. VOPC Opcodes_

|**Opcode #**|**Name**|
|---|---|
|16|V_CMP_CLASS_F32|
|17|V_CMPX_CLASS_F32|
|18|V_CMP_CLASS_F64|



228 of 267

13.3. Vector ALU Formats

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode #**|**Name**|
|---|---|
|19|V_CMPX_CLASS_F64|
|20|V_CMP_CLASS_F16|
|21|V_CMPX_CLASS_F16|
|32|V_CMP_F_F16|
|33|V_CMP_LT_F16|
|34|V_CMP_EQ_F16|
|35|V_CMP_LE_F16|
|36|V_CMP_GT_F16|
|37|V_CMP_LG_F16|
|38|V_CMP_GE_F16|
|39|V_CMP_O_F16|
|40|V_CMP_U_F16|
|41|V_CMP_NGE_F16|
|42|V_CMP_NLG_F16|
|43|V_CMP_NGT_F16|
|44|V_CMP_NLE_F16|
|45|V_CMP_NEQ_F16|
|46|V_CMP_NLT_F16|
|47|V_CMP_TRU_F16|
|48|V_CMPX_F_F16|
|49|V_CMPX_LT_F16|
|50|V_CMPX_EQ_F16|
|51|V_CMPX_LE_F16|
|52|V_CMPX_GT_F16|
|53|V_CMPX_LG_F16|
|54|V_CMPX_GE_F16|
|55|V_CMPX_O_F16|
|56|V_CMPX_U_F16|
|57|V_CMPX_NGE_F16|
|58|V_CMPX_NLG_F16|
|59|V_CMPX_NGT_F16|
|60|V_CMPX_NLE_F16|
|61|V_CMPX_NEQ_F16|
|62|V_CMPX_NLT_F16|



229 of 267

13.3. Vector ALU Formats

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode #**<br>**N**|**ame**|
|---|---|
|63<br>V_|CMPX_TRU_F16|
|64<br>V_|CMP_F_F32|
|65<br>V_|CMP_LT_F32|
|66<br>V_|CMP_EQ_F32|
|67<br>V_|CMP_LE_F32|
|68<br>V_|CMP_GT_F32|
|69<br>V_|CMP_LG_F32|
|70<br>V_|CMP_GE_F32|
|71<br>V_|CMP_O_F32|
|72<br>V_|CMP_U_F32|
|73<br>V_|CMP_NGE_F32|
|74<br>V_|CMP_NLG_F32|
|75<br>V_|CMP_NGT_F32|
|76<br>V_|CMP_NLE_F32|
|77<br>V_|CMP_NEQ_F32|
|78<br>V_|CMP_NLT_F32|
|79<br>V_|CMP_TRU_F32|
|80<br>V_|CMPX_F_F32|
|81<br>V_|CMPX_LT_F32|
|82<br>V_|CMPX_EQ_F32|
|83<br>V_|CMPX_LE_F32|
|84<br>V_|CMPX_GT_F32|
|85<br>V_|CMPX_LG_F32|
|86<br>V_|CMPX_GE_F32|
|87<br>V_|CMPX_O_F32|
|88<br>V_|CMPX_U_F32|
|89<br>V_|CMPX_NGE_F32|
|90<br>V_|CMPX_NLG_F32|
|91<br>V_|CMPX_NGT_F32|
|92<br>V_|CMPX_NLE_F32|
|93<br>V_|CMPX_NEQ_F32|
|94<br>V_|CMPX_NLT_F32|
|95<br>V_|CMPX_TRU_F32|
|96<br>V_|CMP_F_F64|



230 of 267

13.3. Vector ALU Formats

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode #**<br>**N**|**ame**||
|---|---|---|
|97<br>V|_CMP|_LT_F64|
|98<br>V|_CMP|_EQ_F64|
|99<br>V|_CMP|_LE_F64|
|100<br>V|_CMP|_GT_F64|
|101<br>V|_CMP|_LG_F64|
|102<br>V|_CMP|_GE_F64|
|103<br>V|_CMP|_O_F64|
|104<br>V|_CMP|_U_F64|
|105<br>V|_CMP|_NGE_F64|
|106<br>V|_CMP|_NLG_F64|
|107<br>V|_CMP|_NGT_F64|
|108<br>V|_CMP|_NLE_F64|
|109<br>V|_CMP|_NEQ_F64|
|110<br>V|_CMP|_NLT_F64|
|111<br>V|_CMP|_TRU_F64|
|112<br>V|_CMP|X_F_F64|
|113<br>V|_CMP|X_LT_F64|
|114<br>V|_CMP|X_EQ_F64|
|115<br>V|_CMP|X_LE_F64|
|116<br>V|_CMP|X_GT_F64|
|117<br>V|_CMP|X_LG_F64|
|118<br>V|_CMP|X_GE_F64|
|119<br>V|_CMP|X_O_F64|
|120<br>V|_CMP|X_U_F64|
|121<br>V|_CMP|X_NGE_F64|
|122<br>V|_CMP|X_NLG_F64|
|123<br>V|_CMP|X_NGT_F64|
|124<br>V|_CMP|X_NLE_F64|
|125<br>V|_CMP|X_NEQ_F64|
|126<br>V|_CMP|X_NLT_F64|
|127<br>V|_CMP|X_TRU_F64|
|160<br>V|_CMP|_F_I16|
|161<br>V|_CMP|_LT_I16|
|162<br>V|_CMP|_EQ_I16|



231 of 267

13.3. Vector ALU Formats

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode #**|**Name**||
|---|---|---|
|163|V_CMP|_LE_I16|
|164|V_CMP|_GT_I16|
|165|V_CMP|_NE_I16|
|166|V_CMP|_GE_I16|
|167|V_CMP|_T_I16|
|168|V_CMP|_F_U16|
|169|V_CMP|_LT_U16|
|170|V_CMP|_EQ_U16|
|171|V_CMP|_LE_U16|
|172|V_CMP|_GT_U16|
|173|V_CMP|_NE_U16|
|174|V_CMP|_GE_U16|
|175|V_CMP|_T_U16|
|176|V_CMP|X_F_I16|
|177|V_CMP|X_LT_I16|
|178|V_CMP|X_EQ_I16|
|179|V_CMP|X_LE_I16|
|180|V_CMP|X_GT_I16|
|181|V_CMP|X_NE_I16|
|182|V_CMP|X_GE_I16|
|183|V_CMP|X_T_I16|
|184|V_CMP|X_F_U16|
|185|V_CMP|X_LT_U16|
|186|V_CMP|X_EQ_U16|
|187|V_CMP|X_LE_U16|
|188|V_CMP|X_GT_U16|
|189|V_CMP|X_NE_U16|
|190|V_CMP|X_GE_U16|
|191|V_CMP|X_T_U16|
|192|V_CMP|_F_I32|
|193|V_CMP|_LT_I32|
|194|V_CMP|_EQ_I32|
|195|V_CMP|_LE_I32|
|196|V_CMP|_GT_I32|



232 of 267

13.3. Vector ALU Formats

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode #**|**Name**||
|---|---|---|
|197|V_CMP|_NE_I32|
|198|V_CMP|_GE_I32|
|199|V_CMP|_T_I32|
|200|V_CMP|_F_U32|
|201|V_CMP|_LT_U32|
|202|V_CMP|_EQ_U32|
|203|V_CMP|_LE_U32|
|204|V_CMP|_GT_U32|
|205|V_CMP|_NE_U32|
|206|V_CMP|_GE_U32|
|207|V_CMP|_T_U32|
|208|V_CMP|X_F_I32|
|209|V_CMP|X_LT_I32|
|210|V_CMP|X_EQ_I32|
|211|V_CMP|X_LE_I32|
|212|V_CMP|X_GT_I32|
|213|V_CMP|X_NE_I32|
|214|V_CMP|X_GE_I32|
|215|V_CMP|X_T_I32|
|216|V_CMP|X_F_U32|
|217|V_CMP|X_LT_U32|
|218|V_CMP|X_EQ_U32|
|219|V_CMP|X_LE_U32|
|220|V_CMP|X_GT_U32|
|221|V_CMP|X_NE_U32|
|222|V_CMP|X_GE_U32|
|223|V_CMP|X_T_U32|
|224|V_CMP|_F_I64|
|225|V_CMP|_LT_I64|
|226|V_CMP|_EQ_I64|
|227|V_CMP|_LE_I64|
|228|V_CMP|_GT_I64|
|229|V_CMP|_NE_I64|
|230|V_CMP|_GE_I64|



233 of 267

13.3. Vector ALU Formats

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode #**|**Name**|
|---|---|
|231|V_CMP_T_I64|
|232|V_CMP_F_U64|
|233|V_CMP_LT_U64|
|234|V_CMP_EQ_U64|
|235|V_CMP_LE_U64|
|236|V_CMP_GT_U64|
|237|V_CMP_NE_U64|
|238|V_CMP_GE_U64|
|239|V_CMP_T_U64|
|240|V_CMPX_F_I64|
|241|V_CMPX_LT_I64|
|242|V_CMPX_EQ_I64|
|243|V_CMPX_LE_I64|
|244|V_CMPX_GT_I64|
|245|V_CMPX_NE_I64|
|246|V_CMPX_GE_I64|
|247|V_CMPX_T_I64|
|248|V_CMPX_F_U64|
|249|V_CMPX_LT_U64|
|250|V_CMPX_EQ_U64|
|251|V_CMPX_LE_U64|
|252|V_CMPX_GT_U64|
|253|V_CMPX_NE_U64|
|254|V_CMPX_GE_U64|
|255|V_CMPX_T_U64|



### **13.3.4. VOP3A**



**Format** VOP3A

234 of 267

13.3. Vector ALU Formats

"AMD Instinct MI200" Instruction Set Architecture



#### **Description** Vector ALU format with three operands

_Table 73. VOP3A Fields_

|**Field Name**|**Bits**|**Format or Description**|
|---|---|---|
|VDST|[7:0]|Destination VGPR|
|ABS|[10:8]|Absolute value of input. [8] = src0, [9] = src1, [10] = src2|
|OPSEL|[14:11]|Operand select for 16-bit data. 0 = select low half, 1 = select high half. [11] =<br>src0, [12] = src1, [13] = src2, [14] = dest.|
|CLMP|[15]|Clamp output|
|OP|[25:16]|Opcode. See next table.|
|ENCODING|[31:26]|Must be: 110100|



235 of 267

13.3. Vector ALU Formats

"AMD Instinct MI200" Instruction Set Architecture



|**Field Name**|**Bits**|**Format or Description**|
|---|---|---|
|SRC0|[40:32]|Source 0. First operand for the instruction.|
||0 - 101|SGPR0 to SGPR101: Scalar general-purpose registers.|
||102|FLAT_SCRATCH_LO.|
||103|FLAT_SCRATCH_HI.|
||104|XNACK_MASK_LO.|
||105|XNACK_MASK_HI.|
||106|VCC_LO: vcc[31:0].|
||107|VCC_HI: vcc[63:32].|
||108-123|TTMP0 - TTMP15: Trap handler temporary register.|
||124|M0. Memory register 0.|
||125|Reserved|
||126|EXEC_LO: exec[31:0].|
||127|EXEC_HI: exec[63:32].|
||128|0.|
||129-192|Signed integer 1 to 64.|
||193-208|Signed integer -1 to -16.|
||209-234|Reserved.|
||235|SHARED_BASE (Memory Aperture definition).|
||236|SHARED_LIMIT (Memory Aperture definition).|
||237|PRIVATE_BASE (Memory Aperture definition).|
||238|PRIVATE_LIMIT (Memory Aperture definition).|
||239|POPS_EXITING_WAVE_ID .|
||240|0.5.|
||241|-0.5.|
||242|1.0.|
||243|-1.0.|
||244|2.0.|
||245|-2.0.|
||246|4.0.|
||247|-4.0.|
||248|1/(2*PI).|
||249|SDWA|
||250|DPP|
||251|VCCZ.|
||252|EXECZ.|
||253|SCC.|
||254|Reserved.|
||255|Literal constant.|
||256 - 511|VGPR 0 - 255|
|SRC1|[49:41]|Second input operand. Same options as SRC0.|
|SRC2|[58:50]|Third input operand. Same options as SRC0.|
|OMOD|[60:59]|Output Modifier: 0=none, 1=*2, 2=*4, 3=div-2|
|NEG|[63:61]|Negate input. [61] = src0, [62] = src1, [63] = src2|



##### _Table 74. VOP3A Opcodes_

|**Opcode #**|**Name**|
|---|---|
|448|V_MAD_LEGACY_F32|
|449|V_MAD_F32|



236 of 267

13.3. Vector ALU Formats

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode #**|**Name**|
|---|---|
|450|V_MAD_I32_I24|
|451|V_MAD_U32_U24|
|452|V_CUBEID_F32|
|453|V_CUBESC_F32|
|454|V_CUBETC_F32|
|455|V_CUBEMA_F32|
|456|V_BFE_U32|
|457|V_BFE_I32|
|458|V_BFI_B32|
|459|V_FMA_F32|
|460|V_FMA_F64|
|461|V_LERP_U8|
|462|V_ALIGNBIT_B32|
|463|V_ALIGNBYTE_B32|
|464|V_MIN3_F32|
|465|V_MIN3_I32|
|466|V_MIN3_U32|
|467|V_MAX3_F32|
|468|V_MAX3_I32|
|469|V_MAX3_U32|
|470|V_MED3_F32|
|471|V_MED3_I32|
|472|V_MED3_U32|
|473|V_SAD_U8|
|474|V_SAD_HI_U8|
|475|V_SAD_U16|
|476|V_SAD_U32|
|477|V_CVT_PK_U8_F32|
|478|V_DIV_FIXUP_F32|
|479|V_DIV_FIXUP_F64|
|482|V_DIV_FMAS_F32|
|483|V_DIV_FMAS_F64|
|484|V_MSAD_U8|
|485|V_QSAD_PK_U16_U8|



237 of 267

13.3. Vector ALU Formats

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode #**|**Name**|
|---|---|
|486|V_MQSAD_PK_U16_U8|
|487|V_MQSAD_U32_U8|
|490|V_MAD_LEGACY_F16|
|491|V_MAD_LEGACY_U16|
|492|V_MAD_LEGACY_I16|
|493|V_PERM_B32|
|494|V_FMA_LEGACY_F16|
|495|V_DIV_FIXUP_LEGACY_F16|
|496|V_CVT_PKACCUM_U8_F32|
|497|V_MAD_U32_U16|
|498|V_MAD_I32_I16|
|499|V_XAD_U32|
|500|V_MIN3_F16|
|501|V_MIN3_I16|
|502|V_MIN3_U16|
|503|V_MAX3_F16|
|504|V_MAX3_I16|
|505|V_MAX3_U16|
|506|V_MED3_F16|
|507|V_MED3_I16|
|508|V_MED3_U16|
|509|V_LSHL_ADD_U32|
|510|V_ADD_LSHL_U32|
|511|V_ADD3_U32|
|512|V_LSHL_OR_B32|
|513|V_AND_OR_B32|
|514|V_OR3_B32|
|515|V_MAD_F16|
|516|V_MAD_U16|
|517|V_MAD_I16|
|518|V_FMA_F16|
|519|V_DIV_FIXUP_F16|
|640|V_ADD_F64|
|641|V_MUL_F64|



238 of 267

13.3. Vector ALU Formats

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode #**|**Name**|
|---|---|
|642|V_MIN_F64|
|643|V_MAX_F64|
|644|V_LDEXP_F64|
|645|V_MUL_LO_U32|
|646|V_MUL_HI_U32|
|647|V_MUL_HI_I32|
|648|V_LDEXP_F32|
|649|V_READLANE_B32|
|650|V_WRITELANE_B32|
|651|V_BCNT_U32_B32|
|652|V_MBCNT_LO_U32_B32|
|653|V_MBCNT_HI_U32_B32|
|655|V_LSHLREV_B64|
|656|V_LSHRREV_B64|
|657|V_ASHRREV_I64|
|658|V_TRIG_PREOP_F64|
|659|V_BFM_B32|
|660|V_CVT_PKNORM_I16_F32|
|661|V_CVT_PKNORM_U16_F32|
|662|V_CVT_PKRTZ_F16_F32|
|663|V_CVT_PK_U16_U32|
|664|V_CVT_PK_I16_I32|
|665|V_CVT_PKNORM_I16_F16|
|666|V_CVT_PKNORM_U16_F16|
|668|V_ADD_I32|
|669|V_SUB_I32|
|670|V_ADD_I16|
|671|V_SUB_I16|
|672|V_PACK_B32_F16|
|673|V_MUL_LEGACY_F32|



### **13.3.5. VOP3B**

239 of 267

13.3. Vector ALU Formats

"AMD Instinct MI200" Instruction Set Architecture





#### **Format**

VOP3B

**Description** Vector ALU format with three operands and a scalar result. This encoding is used only for a few opcodes.

This encoding allows specifying a unique scalar destination, and is used only for the opcodes listed below. All other opcodes use VOP3A.

- V_ADD_CO_U32

- V_SUB_CO_U32

- V_SUBREV_CO_U32

- V_ADDC_CO_U32

- V_SUBB_CO_U32

- V_SUBBREV_CO_U32

- V_DIV_SCALE_F32

- V_DIV_SCALE_F64

- V_MAD_U64_U32

- V_MAD_I64_I32

_Table 75. VOP3B Fields_

|**Field Name**|**Bits**|**Format or Description**|
|---|---|---|
|VDST|[7:0]|Destination VGPR|
|SDST|[14:8]|Scalar destination|
|CLMP|[15]|Clamp result|
|OP|[25:16]|Opcode. see next table.|
|ENCODING|[31:26]|Must be: 110100|



240 of 267

13.3. Vector ALU Formats

"AMD Instinct MI200" Instruction Set Architecture



|**Field Name**|**Bits**|**Format or Description**|
|---|---|---|
|SRC0|[40:32]|Source 0. First operand for the instruction.|
||0 - 101|SGPR0 to SGPR101: Scalar general-purpose registers.|
||102|FLAT_SCRATCH_LO.|
||103|FLAT_SCRATCH_HI.|
||104|XNACK_MASK_LO.|
||105|XNACK_MASK_HI.|
||106|VCC_LO: vcc[31:0].|
||107|VCC_HI: vcc[63:32].|
||108-123|TTMP0 - TTMP15: Trap handler temporary register.|
||124|M0. Memory register 0.|
||125|Reserved|
||126|EXEC_LO: exec[31:0].|
||127|EXEC_HI: exec[63:32].|
||128|0.|
||129-192|Signed integer 1 to 64.|
||193-208|Signed integer -1 to -16.|
||209-234|Reserved.|
||235|SHARED_BASE (Memory Aperture definition).|
||236|SHARED_LIMIT (Memory Aperture definition).|
||237|PRIVATE_BASE (Memory Aperture definition).|
||238|PRIVATE_LIMIT (Memory Aperture definition).|
||239|POPS_EXITING_WAVE_ID .|
||240|0.5.|
||241|-0.5.|
||242|1.0.|
||243|-1.0.|
||244|2.0.|
||245|-2.0.|
||246|4.0.|
||247|-4.0.|
||248|1/(2*PI).|
||249|SDWA|
||250|DPP|
||251|VCCZ.|
||252|EXECZ.|
||253|SCC.|
||254|Reserved.|
||255|Literal constant.|
||256 - 511|VGPR 0 - 255|
|SRC1|[49:41]|Second input operand. Same options as SRC0.|
|SRC2|[58:50]|Third input operand. Same options as SRC0.|
|OMOD|[60:59]|Output Modifier: 0=none, 1=*2, 2=*4, 3=div-2|
|NEG|[63:61]|Negate input. [61] = src0, [62] = src1, [63] = src2|



##### _Table 76. VOP3B Opcodes_

|**Opcode #**|**Name**|
|---|---|
|480|V_DIV_SCALE_F32|
|481|V_DIV_SCALE_F64|



241 of 267

13.3. Vector ALU Formats

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode #**|**Name**||
|---|---|---|
|488|V_MAD|_U64_U32|
|489|V_MAD|_I64_I32|



### **13.3.6. VOP3P**



#### **Format**

#### VOP3P

**Description** Vector ALU format taking one, two or three pairs of 16 bit inputs and producing two 16-bit outputs (packed into 1 dword).

_Table 77. VOP3P Fields_

|**Field Name**|**Bits**|**Format or Description**|
|---|---|---|
|VDST|[7:0]|Destination VGPR|
|NEG_HI|[10:8]|Negate sources 0,1,2 of the high 16-bits.|
|OPSEL|[13:11]|Select low or high for low sources 0=[11], 1=[12], 2=[13].|
|OPSEL_HI2|[14]|Select low or high for high sources 0=[14], 1=[60], 2=[59].|
|CLMP|[15]|1 = clamp result.|
|OP|[22:16]|Opcode. see next table.|
|ENCODING|[31:24]|Must be: 110100111|



242 of 267

13.3. Vector ALU Formats

"AMD Instinct MI200" Instruction Set Architecture



|**Field Name**|**Bits**|**Format or Description**|
|---|---|---|
|SRC0|[40:32]|Source 0. First operand for the instruction.|
||0 - 101|SGPR0 to SGPR101: Scalar general-purpose registers.|
||102|FLAT_SCRATCH_LO.|
||103|FLAT_SCRATCH_HI.|
||104|XNACK_MASK_LO.|
||105|XNACK_MASK_HI.|
||106|VCC_LO: vcc[31:0].|
||107|VCC_HI: vcc[63:32].|
||108-123|TTMP0 - TTMP15: Trap handler temporary register.|
||124|M0. Memory register 0.|
||125|Reserved|
||126|EXEC_LO: exec[31:0].|
||127|EXEC_HI: exec[63:32].|
||128|0.|
||129-192|Signed integer 1 to 64.|
||193-208|Signed integer -1 to -16.|
||209-234|Reserved.|
||235|SHARED_BASE (Memory Aperture definition).|
||236|SHARED_LIMIT (Memory Aperture definition).|
||237|PRIVATE_BASE (Memory Aperture definition).|
||238|PRIVATE_LIMIT (Memory Aperture definition).|
||239|POPS_EXITING_WAVE_ID .|
||240|0.5.|
||241|-0.5.|
||242|1.0.|
||243|-1.0.|
||244|2.0.|
||245|-2.0.|
||246|4.0.|
||247|-4.0.|
||248|1/(2*PI).|
||249|SDWA|
||250|DPP|
||251|VCCZ.|
||252|EXECZ.|
||253|SCC.|
||254|Reserved.|
||255|Literal constant.|
||256 - 511|VGPR 0 - 255|
|SRC1|[49:41]|Second input operand. Same options as SRC0.|
|SRC2|[58:50]|Third input operand. Same options as SRC0.|
|OPSEL_HI|[60:59]|See OP_SEL_HI2.|
|NEG|[63:61]|Negate input for low 16-bits of sources. [61] = src0, [62] = src1, [63] = src2|



#### **13.3.6.1. VOP3P-MAI**



243 of 267

13.3. Vector ALU Formats

"AMD Instinct MI200" Instruction Set Architecture



_Table 78. VOP3P-MAI Fields_

|**Field Name**|**Bits**|**Format or Description**|
|---|---|---|
|VDST|[7:0]|Destination VGPR|
|CBSZ|[10:8]|Defines the number of blocks that can do a broadcast within a group. Legal<br>values = 0-4. The block ID of this group comes from ABID.|
|ABID|[14:11]|Block ID of block to broadcast during matrix multiply (MFMA ops).|
|ACC_CD|[15]|Indicats that SRC-C and VDST use ACC VGPRs|
|OP|[22:16]|Opcode. see next table.|
|ENCODING|[31:24]|Must be: 110100111|
|SRC0|[40:32]<br>0 - 107<br>128|Source 0. First operand for the instruction.<br>Reserved.<br>0.|
||129-192|Signed integer 1 to 64.|
||193-208|Signed integer -1 to -16.|
||209-239|Reserved.|
||240|0.5. (float32)|
||241|-0.5.(float32)|
||242|1.0. (float32)|
||243|-1.0. (float32)|
||244|2.0. (float32)|
||245|-2.0. (float32)|
||246|4.0. (float32)|
||247|-4.0. (float32)|
||248|1/(2*PI). (float32)|
||249 - 255|Reserved|
||256 - 511|VGPR 0 - 255|
|SRC1|[49:41]|Second input operand. Same options as SRC0.|
|SRC2|[58:50]|Third input operand. Same options as SRC0.|
|ACC|[60:59]|ACC[0] : 0 = read SRC-A from Arch VGPR; 1 = read SRC-A from Acc VGPR.<br>ACC[1] : 0 = read SRC-B from Arch VGPR; 1 = read SRC-B from Acc VGPR.|
|BLGP|[63:61]|“B”-Matrix Lane-Group Pattern. Controls how to swizzle the matrix lane groups<br>(LG) in VGPRs when doing matrix multiplication by controlling the swizzle<br>muxes.|



##### _Table 79. VOP3P Opcodes_

|**Opcode #**|**Name**||
|---|---|---|
|0|V_PK_|MAD_I16|
|1|V_PK_|MUL_LO_U16|
|2|V_PK_|ADD_I16|
|3|V_PK_|SUB_I16|
|4|V_PK_|LSHLREV_B16|
|5|V_PK_|LSHRREV_B16|
|6|V_PK_|ASHRREV_I16|



244 of 267

13.3. Vector ALU Formats

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode #**|**Name**|
|---|---|
|7|V_PK_MAX_I16|
|8|V_PK_MIN_I16|
|9|V_PK_MAD_U16|
|10|V_PK_ADD_U16|
|11|V_PK_SUB_U16|
|12|V_PK_MAX_U16|
|13|V_PK_MIN_U16|
|14|V_PK_FMA_F16|
|15|V_PK_ADD_F16|
|16|V_PK_MUL_F16|
|17|V_PK_MIN_F16|
|18|V_PK_MAX_F16|
|32|V_MAD_MIX_F32|
|33|V_MAD_MIXLO_F16|
|34|V_MAD_MIXHI_F16|
|35|V_DOT2_F32_F16|
|38|V_DOT2_I32_I16|
|39|V_DOT2_U32_U16|
|40|V_DOT4_I32_I8|
|41|V_DOT4_U32_U8|
|42|V_DOT8_I32_I4|
|43|V_DOT8_U32_U4|
|48|V_PK_FMA_F32|
|49|V_PK_MUL_F32|
|50|V_PK_ADD_F32|
|51|V_PK_MOV_B32|
|64|V_MFMA_F32_32X32X1F32|
|65|V_MFMA_F32_16X16X1F32|
|66|V_MFMA_F32_4X4X1F32|
|68|V_MFMA_F32_32X32X2F32|
|69|V_MFMA_F32_16X16X4F32|
|72|V_MFMA_F32_32X32X4F16|
|73|V_MFMA_F32_16X16X4F16|
|74|V_MFMA_F32_4X4X4F16|



245 of 267

13.3. Vector ALU Formats

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode #**|**Name**||
|---|---|---|
|76|V_MFMA_F32|_32X32X8F16|
|77|V_MFMA_F32|_16X16X16F16|
|80|V_MFMA_I32_|32X32X4I8|
|81|V_MFMA_I32_|16X16X4I8|
|82|V_MFMA_I32_|4X4X4I8|
|84|V_MFMA_I32_|32X32X8I8|
|85|V_MFMA_I32_|16X16X16I8|
|88|V_ACCVGPR_|READ|
|89|V_ACCVGPR_|WRITE|
|99|V_MFMA_F32|_32X32X4BF16_1K|
|100|V_MFMA_F32|_16X16X4BF16_1K|
|101|V_MFMA_F32|_4X4X4BF16_1K|
|102|V_MFMA_F32|_32X32X8BF16_1K|
|103|V_MFMA_F32|_16X16X16BF16_1K|
|104|V_MFMA_F32|_32X32X2BF16|
|105|V_MFMA_F32|_16X16X2BF16|
|107|V_MFMA_F32|_4X4X2BF16|
|108|V_MFMA_F32|_32X32X4BF16|
|109|V_MFMA_F32|_16X16X8BF16|
|110|V_MFMA_F64|_16X16X4F64|
|111|V_MFMA_F64|_4X4X4F64|



### **13.3.7. SDWA**



#### **Format** SDWA

|**Description**|Sub-Dword Addressing. This is a second dword which can follow VOP1 or|
|---|---|
||VOP2 instructions (in place of a literal constant) to control selection of sub-|
||dword (16-bit) operands. Use of SDWA is indicated by assigning the SRC0|
||field to SDWA, and then the actual VGPR used as source-zero is|
||determined in SDWA instruction word.|



_Table 80. SDWA Fields_

246 of 267

13.3. Vector ALU Formats

"AMD Instinct MI200" Instruction Set Architecture



|**Field Name**|**Bits**|**Format or Description**|
|---|---|---|
|SRC0|[39:32]|Real SRC0 operand (VGPR).|
|DST_SEL|[42:40]|Select the data destination:<br>0-3 = reserved<br>4 = data[15:0]<br>5 = data[31:16]<br>6 = data[31:0]<br>7 = reserved|
|DST_U|[44:43]|Destination format: what do with the bits in the VGPR that are not selected by<br>DST_SEL:<br>0 = pad with zeros + 1 = sign extend upper / zero lower<br>2 = preserve (don’t modify)<br>3 = reserved|
|CLMP|[45]|1 = clamp result|
|OMOD|[47:46]|Output modifiers (see VOP3). [46] = low half, [47] = high half|
|SRC0_SEL|[50:48]|Source 0 select. Same options as DST_SEL.|
|SRC0_SEXT|[51]|Sign extend modifier for source 0.|
|SRC0_NEG|[52]|1 = negate source 0.|
|SRC0_ABS|[53]|1 = Absolute value of source 0.|
|S0|[55]|0 = source 0 is VGPR, 1 = is SGPR.|
|SRC1_SEL|[58:56]|Same options as SRC0_SEL.|
|SRC1_SEXT|[59]|Sign extend modifier for source 1.|
|SRC1_NEG|[60]|1 = negate source 1.|
|SRC1_ABS|[61]|1 = Absolute value of source 1.|
|S1|[63]|0 = source 1 is VGPR, 1 = is SGPR.|



### **13.3.8. SDWAB**



#### **Format** SDWAB

**Description** Sub-Dword Addressing. This is a second dword which can follow VOPC instructions (in place of a literal constant) to control selection of sub-dword (16-bit) operands. Use of SDWA is indicated by assigning the SRC0 field to SDWA, and then the actual VGPR used as source-zero is determined in SDWA instruction word. This version has a scalar destination.

_Table 81. SDWAB Fields_

247 of 267

13.3. Vector ALU Formats

"AMD Instinct MI200" Instruction Set Architecture



|**Field Name**|**Bits**|**Format or Description**|
|---|---|---|
|SRC0|[39:32]|Real SRC0 operand (VGPR).|
|SDST|[46:40]|Scalar GPR destination.|
|SD|[47]|Scalar destination type: 0 = VCC, 1 = normal SGPR.|
|SRC0_SEL|[50:48]|Source 0 select. Same options as DST_SEL.|
|SRC0_SEXT|[51]|Sign extend modifier for source 0.|
|SRC0_NEG|[52]|1 = negate source 0.|
|SRC0_ABS|[53]|1 = Absolute value of source 0.|
|S0|[55]|0 = source 0 is VGPR, 1 = is SGPR.|
|SRC1_SEL|[58:56]|Same options as SRC0_SEL.|
|SRC1_SEXT|[59]|Sign extend modifier for source 1.|
|SRC1_NEG|[60]|1 = negate source 1.|
|SRC1_ABS|[61]|1 = Absolute value of source 1.|
|S1|[63]|0 = source 1 is VGPR, 1 = is SGPR.|



### **13.3.9. DPP**



**Format** DPP

**Description** Data Parallel Primitives. This is a second dword which can follow VOP1, VOP2 or VOPC instructions (in place of a literal constant) to control selection of data from other lanes.

_Table 82. DPP Fields_

|**Field Name**|**Bits**|**Format or Description**|
|---|---|---|
|SRC0|[39:32]|Real SRC0 operand (VGPR).|
|DPP_CTRL|[48:40]|See next table: "DPP_CTRL Enumeration"|
|BC|[51]|Bounds Control: 0 = do not write when source is out of range, 1 = write.|
|SRC0_NEG|[52]|1 = negate source 0.|
|SRC0_ABS|[53]|1 = Absolute value of source 0.|
|SRC1_NEG|[54]|1 = negate source 1.|
|SRC1_ABS|[55]|1 = Absolute value of source 1.|



248 of 267

13.3. Vector ALU Formats

"AMD Instinct MI200" Instruction Set Architecture



|**Field Name**|**Bits**|**Format or Description**|
|---|---|---|
|BANK_MASK|[59:56]|Bank Mask Applies to the VGPR destination write only, does not impact the<br>thread mask when fetching source VGPR data.<br>27==0: lanes[12:15, 28:31, 44:47, 60:63] are disabled<br>26==0: lanes[8:11, 24:27, 40:43, 56:59] are disabled<br>25==0: lanes[4:7, 20:23, 36:39, 52:55] are disabled<br>24==0: lanes[0:3, 16:19, 32:35, 48:51] are disabled<br>Notice: the term "bank" here is not the same as we used for the VGPR bank.|
|ROW_MASK|[63:60]|Row Mask Applies to the VGPR destination write only, does not impact the<br>thread mask when fetching source VGPR data.<br>31==0: lanes[63:48] are disabled (wave 64 only)<br>30==0: lanes[47:32] are disabled (wave 64 only)<br>29==0: lanes[31:16] are disabled<br>28==0: lanes[15:0] are disabled|



_Table 83. DPP_CTRL Enumeration_

|**DPP_Cntl**<br>**Enumeration**|**Hex**<br>**Value**|**Function**|**Description**|
|---|---|---|---|
|DPP_QUAD_PE<br>RM*|000-<br>0FF|pix[n].srca = pix[(n&0x3c)+ dpp_cntl[n%4*2+1 :<br>n%4*2]].srca|Full permute of four threads.|
|DPP_UNUSED|100|Undefined|Reserved.|
|DPP_ROW_SL*|101-<br>10F|if ((n & 0xf) < (16-cntl[3:0])) pix[n].srca = pix[n +<br>cntl[3:0]].srca else use bound_cntl|Row shift left by 1-15 threads.|
|DPP_ROW_SR*|111-<br>11F|if \((n&0xf) >= cntl[3:0]) pix[n].srca = pix[n -<br>cntl[3:0]].srca else use bound_cntl|Row shift right by 1-15<br>threads.|
|DPP_ROW_RR*|121-<br>12F|if \((n&0xf) >= cnt[3:0]) pix[n].srca = pix[n -<br>cntl[3:0]].srca else pix[n].srca = pix[n + 16 -<br>cntl[3:0]].srca|Row rotate right by 1-15<br>threads.|
|DPP_WF_SL1*|130|if (n<63) pix[n].srca = pix[n+1].srca else use bound_cntl|Wavefront left shift by 1<br>thread.|
|DPP_WF_RL1*|134|if (n<63) pix[n].srca = pix[n+1].srca else pix[n].srca =<br>pix[0].srca|Wavefront left rotate by 1<br>thread.|
|DPP_WF_SR1*|138|if (n>0) pix[n].srca = pix[n-1].srca else use bound_cntl|Wavefront right shift by 1<br>thread.|
|DPP_WF_RR1*|13C|if (n>0) pix[n].srca = pix[n-1].srca else pix[n].srca =<br>pix[63].srca|Wavefront right rotate by 1<br>thread.|
|DPP_ROW_MIR<br>ROR*|140|pix[n].srca = pix[15-(n&f)].srca|Mirror threads within row.|
|DPP_ROW_HAL<br>F_MIRROR*|141|pix[n].srca = pix[7-(n&7)].srca|Mirror threads within row (8<br>threads).|
|DPP_ROW_BCA<br>ST15*|142|if (n>15) pix[n].srca = pix[n & 0x30 - 1].srca|Broadcast 15th thread of each<br>row to next row.|
|DPP_ROW_BCA<br>ST31*|143|if (n>31) pix[n].srca = pix[n & 0x20 - 1].srca|Broadcast thread 31 to rows 2<br>and 3.|



249 of 267

13.3. Vector ALU Formats

"AMD Instinct MI200" Instruction Set Architecture



|**DPP_Cntl**|**Hex**|**Function**|**Description**|
|---|---|---|---|
|**Enumeration**|**Value**|||
|DPP_ROW*|150 -|pix[n].srca = pix[(n & 0xfffffff0)+count].srca;|Broadcast thread 0-15 within a|
||165||row to the whole row.|



## **13.4. LDS and GDS format**

### **13.4.1. DS**



**Format** LDS and GDS

**Description** Local and Global Data Sharing instructions

_Table 84. DS Fields_

|**Field Name**|**Bits**|**Format or Description**|
|---|---|---|
|OFFSET0|[7:0]|First address offset|
|OFFSET1|[15:8]|Second address offset. For some opcodes this is concatenated with OFFSET0.|
|GDS|[16]|1=GDS, 0=LDS operation.|
|OP|[24:17]|See Opcode table below.|
|ACC|[25]|VDST is Accumulation VGPR|
|ENCODING|[31:26]|Must be: 110110|
|ADDR|[39:32]|VGPR which supplies the address.|
|DATA0|[47:40]|First data VGPR.|
|DATA1|[55:48]|Second data VGPR.|
|VDST|[63:56]|Destination VGPR when results returned to VGPRs.|



_Table 85. DS Opcodes_

|**Opcode #**|**Name**|
|---|---|
|0|DS_ADD_U32|
|1|DS_SUB_U32|
|2|DS_RSUB_U32|
|3|DS_INC_U32|
|4|DS_DEC_U32|



13.4. LDS and GDS format

250 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode #**|**Na**|**me**|
|---|---|---|
|5|DS|_MIN_I32|
|6|DS|_MAX_I32|
|7|DS|_MIN_U32|
|8|DS|_MAX_U32|
|9|DS|_AND_B32|
|10|DS|_OR_B32|
|11|DS|_XOR_B32|
|12|DS|_MSKOR_B32|
|13|DS|_WRITE_B32|
|14|DS|_WRITE2_B32|
|15|DS|_WRITE2ST64_B32|
|16|DS|_CMPST_B32|
|17|DS|_CMPST_F32|
|18|DS|_MIN_F32|
|19|DS|_MAX_F32|
|20|DS|_NOP|
|21|DS|_ADD_F32|
|29|DS|_WRITE_ADDTID_B32|
|30|DS|_WRITE_B8|
|31|DS|_WRITE_B16|
|32|DS|_ADD_RTN_U32|
|33|DS|_SUB_RTN_U32|
|34|DS|_RSUB_RTN_U32|
|35|DS|_INC_RTN_U32|
|36|DS|_DEC_RTN_U32|
|37|DS|_MIN_RTN_I32|
|38|DS|_MAX_RTN_I32|
|39|DS|_MIN_RTN_U32|
|40|DS|_MAX_RTN_U32|
|41|DS|_AND_RTN_B32|
|42|DS|_OR_RTN_B32|
|43|DS|_XOR_RTN_B32|
|44|DS|_MSKOR_RTN_B32|
|45|DS|_WRXCHG_RTN_B32|



13.4. LDS and GDS format

251 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode #**|**Na**|**me**|
|---|---|---|
|46|DS_|WRXCHG2_RTN_B32|
|47|DS_|WRXCHG2ST64_RTN_B32|
|48|DS_|CMPST_RTN_B32|
|49|DS_|CMPST_RTN_F32|
|50|DS_|MIN_RTN_F32|
|51|DS_|MAX_RTN_F32|
|52|DS_|WRAP_RTN_B32|
|53|DS_|ADD_RTN_F32|
|54|DS_|READ_B32|
|55|DS_|READ2_B32|
|56|DS_|READ2ST64_B32|
|57|DS_|READ_I8|
|58|DS_|READ_U8|
|59|DS_|READ_I16|
|60|DS_|READ_U16|
|61|DS_|SWIZZLE_B32|
|62|DS_|PERMUTE_B32|
|63|DS_|BPERMUTE_B32|
|64|DS_|ADD_U64|
|65|DS_|SUB_U64|
|66|DS_|RSUB_U64|
|67|DS_|INC_U64|
|68|DS_|DEC_U64|
|69|DS_|MIN_I64|
|70|DS_|MAX_I64|
|71|DS_|MIN_U64|
|72|DS_|MAX_U64|
|73|DS_|AND_B64|
|74|DS_|OR_B64|
|75|DS_|XOR_B64|
|76|DS_|MSKOR_B64|
|77|DS_|WRITE_B64|
|78|DS_|WRITE2_B64|
|79|DS_|WRITE2ST64_B64|



13.4. LDS and GDS format

252 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode #**|**Na**|**me**|
|---|---|---|
|80|DS_|CMPST_B64|
|81|DS_|CMPST_F64|
|82|DS_|MIN_F64|
|83|DS_|MAX_F64|
|84|DS_|WRITE_B8_D16_HI|
|85|DS_|WRITE_B16_D16_HI|
|86|DS_|READ_U8_D16|
|87|DS_|READ_U8_D16_HI|
|88|DS_|READ_I8_D16|
|89|DS_|READ_I8_D16_HI|
|90|DS_|READ_U16_D16|
|91|DS_|READ_U16_D16_HI|
|92|DS_|ADD_F64|
|96|DS_|ADD_RTN_U64|
|97|DS_|SUB_RTN_U64|
|98|DS_|RSUB_RTN_U64|
|99|DS_|INC_RTN_U64|
|100|DS_|DEC_RTN_U64|
|101|DS_|MIN_RTN_I64|
|102|DS_|MAX_RTN_I64|
|103|DS_|MIN_RTN_U64|
|104|DS_|MAX_RTN_U64|
|105|DS_|AND_RTN_B64|
|106|DS_|OR_RTN_B64|
|107|DS_|XOR_RTN_B64|
|108|DS_|MSKOR_RTN_B64|
|109|DS_|WRXCHG_RTN_B64|
|110|DS_|WRXCHG2_RTN_B64|
|111|DS_|WRXCHG2ST64_RTN_B64|
|112|DS_|CMPST_RTN_B64|
|113|DS_|CMPST_RTN_F64|
|114|DS_|MIN_RTN_F64|
|115|DS_|MAX_RTN_F64|
|118|DS_|READ_B64|



13.4. LDS and GDS format

253 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode #**|**Name**|
|---|---|
|119|DS_READ2_B64|
|120|DS_READ2ST64_B64|
|124|DS_ADD_RTN_F64|
|126|DS_CONDXCHG32_RTN_B64|
|152|DS_GWS_SEMA_RELEASE_ALL|
|153|DS_GWS_INIT|
|154|DS_GWS_SEMA_V|
|155|DS_GWS_SEMA_BR|
|156|DS_GWS_SEMA_P|
|157|DS_GWS_BARRIER|
|182|DS_READ_ADDTID_B32|
|189|DS_CONSUME|
|190|DS_APPEND|
|222|DS_WRITE_B96|
|223|DS_WRITE_B128|
|254|DS_READ_B96|
|255|DS_READ_B128|



## **13.5. Vector Memory Buffer Formats**

There are two memory buffer instruction formats:

#### **MTBUF**

typed buffer access (data type is defined by the instruction)

#### **MUBUF**

untyped buffer access (data type is defined by the buffer / resource-constant)

### **13.5.1. MTBUF**



**Format** MTBUF

13.5. Vector Memory Buffer Formats

254 of 267

"AMD Instinct MI200" Instruction Set Architecture



#### **Description** Memory Typed-Buffer Instructions

_Table 86. MTBUF Fields_

|**Field Name**|**Bits**|**Format or Description**|
|---|---|---|
|OFFSET|[11:0]|Address offset, unsigned byte.|
|OFFEN|[12]|1 = enable offset VGPR, 0 = use zero for address offset|
|IDXEN|[13]|1 = enable index VGPR, 0 = use zero for address index|
|GLC|[14]|0 = normal, 1 = globally coherent (bypass L0 cache) or for atomics, return pre-<br>op value to VGPR.|
|OP|[18:15]|Opcode. See table below.|
|DFMT|22:19|Data Format of data in memory buffer:<br>0 invalid<br>1 8<br>2 16<br>3 8_8<br>4 32<br>5 16_16<br>6 10_11_11<br>8 10_10_10_2<br>9 2_10_10_10<br>10 8_8_8_8<br>11 32_32<br>12 16_16_16_16<br>13 32_32_32<br>14 32_32_32_32|
|NFMT|25:23|Numeric format of data in memory:<br>0 unorm<br>1 snorm<br>2 uscaled<br>3 sscaled<br>4 uint<br>5 sint<br>6 reserved<br>7 float|
|ENCODING|[31:26]|Must be: 111010|
|VADDR|[39:32]|Address of VGPR to supply first component of address (offset or index). When<br>both index and offset are used, index is in the first VGPR and offset in the<br>second.|
|VDATA|[47:40]|Address of VGPR to supply first component of write data or receive first<br>component of read-data.|
|SRSRC|[52:48]|SGPR to supply V# (resource constant) in 4 or 8 consecutive SGPRs. It is<br>missing 2 LSB’s of SGPR-address since must be aligned to 4.|
|reserved|[53]|must be set to zero|
|SLC|[54]|System level coherent: bypass L2 cache.|
|ACC|[55]|VDATA is Accumulation VGPR|



13.5. Vector Memory Buffer Formats

255 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Field Name**|**Bits**|**Format or Description**|
|---|---|---|
|SOFFSET|[63:56]|Address offset, unsigned byte.|



_Table 87. MTBUF Opcodes_

|**Opcode #**|**Name**|
|---|---|
|0|TBUFFER_LOAD_FORMAT_X|
|1|TBUFFER_LOAD_FORMAT_XY|
|2|TBUFFER_LOAD_FORMAT_XYZ|
|3|TBUFFER_LOAD_FORMAT_XYZW|
|4|TBUFFER_STORE_FORMAT_X|
|5|TBUFFER_STORE_FORMAT_XY|
|6|TBUFFER_STORE_FORMAT_XYZ|
|7|TBUFFER_STORE_FORMAT_XYZW|
|8|TBUFFER_LOAD_FORMAT_D16_X|
|9|TBUFFER_LOAD_FORMAT_D16_XY|
|10|TBUFFER_LOAD_FORMAT_D16_XYZ|
|11|TBUFFER_LOAD_FORMAT_D16_XYZW|
|12|TBUFFER_STORE_FORMAT_D16_X|
|13|TBUFFER_STORE_FORMAT_D16_XY|
|14|TBUFFER_STORE_FORMAT_D16_XYZ|
|15|TBUFFER_STORE_FORMAT_D16_XYZW|



### **13.5.2. MUBUF**



#### **Format** MUBUF

#### **Description** Memory Untyped-Buffer Instructions

_Table 88. MUBUF Fields_

|**Field Name**|**Bits**|**Format or Description**|
|---|---|---|
|OFFSET|[11:0]|Address offset, unsigned byte.|
|OFFEN|[12]|1 = enable offset VGPR, 0 = use zero for address offset|



13.5. Vector Memory Buffer Formats

256 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Field Name**|**Bits**|**Format or Description**|
|---|---|---|
|IDXEN|[13]|1 = enable index VGPR, 0 = use zero for address index|
|GLC|[14]|0 = normal, 1 = globally coherent (bypass L0 cache) or for atomics, return pre-<br>op value to VGPR.|
|reserved|[15]|must be set to zero|
|LDS|[16]|0 = normal, 1 = transfer data between LDS and memory instead of VGPRs and<br>memory.|
|SLC|[17]|System level coherent: bypass L2 cache.|
|OP|[24:18]|Opcode. See table below.|
|ENCODING|[31:26]|Must be: 111000|
|VADDR|[39:32]|Address of VGPR to supply first component of address (offset or index). When<br>both index and offset are used, index is in the first VGPR and offset in the<br>second.|
|VDATA|[47:40]|Address of VGPR to supply first component of write data or receive first<br>component of read-data.|
|SRSRC|[52:48]|SGPR to supply V# (resource constant) in 4 or 8 consecutive SGPRs. It is<br>missing 2 LSB’s of SGPR-address since must be aligned to 4.|
|ACC|[55]|VDATA is Accumulation VGPR|
|SOFFSET|[63:56]|Address offset, unsigned byte.|



_Table 89. MUBUF Opcodes_

|**Opcode #**|**Name**|
|---|---|
|0|BUFFER_LOAD_FORMAT_X|
|1|BUFFER_LOAD_FORMAT_XY|
|2|BUFFER_LOAD_FORMAT_XYZ|
|3|BUFFER_LOAD_FORMAT_XYZW|
|4|BUFFER_STORE_FORMAT_X|
|5|BUFFER_STORE_FORMAT_XY|
|6|BUFFER_STORE_FORMAT_XYZ|
|7|BUFFER_STORE_FORMAT_XYZW|
|8|BUFFER_LOAD_FORMAT_D16_X|
|9|BUFFER_LOAD_FORMAT_D16_XY|
|10|BUFFER_LOAD_FORMAT_D16_XYZ|
|11|BUFFER_LOAD_FORMAT_D16_XYZW|
|12|BUFFER_STORE_FORMAT_D16_X|
|13|BUFFER_STORE_FORMAT_D16_XY|
|14|BUFFER_STORE_FORMAT_D16_XYZ|



13.5. Vector Memory Buffer Formats

257 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode #**|**Name**|
|---|---|
|15|BUFFER_STORE_FORMAT_D16_XYZW|
|16|BUFFER_LOAD_UBYTE|
|17|BUFFER_LOAD_SBYTE|
|18|BUFFER_LOAD_USHORT|
|19|BUFFER_LOAD_SSHORT|
|20|BUFFER_LOAD_DWORD|
|21|BUFFER_LOAD_DWORDX2|
|22|BUFFER_LOAD_DWORDX3|
|23|BUFFER_LOAD_DWORDX4|
|24|BUFFER_STORE_BYTE|
|25|BUFFER_STORE_BYTE_D16_HI|
|26|BUFFER_STORE_SHORT|
|27|BUFFER_STORE_SHORT_D16_HI|
|28|BUFFER_STORE_DWORD|
|29|BUFFER_STORE_DWORDX2|
|30|BUFFER_STORE_DWORDX3|
|31|BUFFER_STORE_DWORDX4|
|32|BUFFER_LOAD_UBYTE_D16|
|33|BUFFER_LOAD_UBYTE_D16_HI|
|34|BUFFER_LOAD_SBYTE_D16|
|35|BUFFER_LOAD_SBYTE_D16_HI|
|36|BUFFER_LOAD_SHORT_D16|
|37|BUFFER_LOAD_SHORT_D16_HI|
|38|BUFFER_LOAD_FORMAT_D16_HI_X|
|39|BUFFER_STORE_FORMAT_D16_HI_X|
|40|BUFFER_WBL2|
|41|BUFFER_INVL2|
|61|BUFFER_STORE_LDS_DWORD|
|62|BUFFER_WBINVL1|
|63|BUFFER_WBINVL1_VOL|
|64|BUFFER_ATOMIC_SWAP|
|65|BUFFER_ATOMIC_CMPSWAP|
|66|BUFFER_ATOMIC_ADD|
|67|BUFFER_ATOMIC_SUB|



13.5. Vector Memory Buffer Formats

258 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode #**|**Name**||
|---|---|---|
|68|BUFFER_|ATOMIC_SMIN|
|69|BUFFER_|ATOMIC_UMIN|
|70|BUFFER_|ATOMIC_SMAX|
|71|BUFFER_|ATOMIC_UMAX|
|72|BUFFER_|ATOMIC_AND|
|73|BUFFER_|ATOMIC_OR|
|74|BUFFER_|ATOMIC_XOR|
|75|BUFFER_|ATOMIC_INC|
|76|BUFFER_|ATOMIC_DEC|
|77|BUFFER_|ATOMIC_ADD_F32|
|78|BUFFER_|ATOMIC_PK_ADD_F16|
|79|BUFFER_|ATOMIC_ADD_F64|
|80|BUFFER_|ATOMIC_MIN_F64|
|81|BUFFER_|ATOMIC_MAX_F64|
|96|BUFFER_|ATOMIC_SWAP_X2|
|97|BUFFER_|ATOMIC_CMPSWAP_X2|
|98|BUFFER_|ATOMIC_ADD_X2|
|99|BUFFER_|ATOMIC_SUB_X2|
|100|BUFFER_|ATOMIC_SMIN_X2|
|101|BUFFER_|ATOMIC_UMIN_X2|
|102|BUFFER_|ATOMIC_SMAX_X2|
|103|BUFFER_|ATOMIC_UMAX_X2|
|104|BUFFER_|ATOMIC_AND_X2|
|105|BUFFER_|ATOMIC_OR_X2|
|106|BUFFER_|ATOMIC_XOR_X2|
|107|BUFFER_|ATOMIC_INC_X2|
|108|BUFFER_|ATOMIC_DEC_X2|



## **13.6. Vector Memory Image Format**

**13.6.1. MIMG**

259 of 267

13.6. Vector Memory Image Format

"AMD Instinct MI200" Instruction Set Architecture





#### **Format** MIMG

#### **Description** Memory Image Instructions

_Table 90. MIMG Fields_

|**Field Name**|**Bits**|**Format or Description**|
|---|---|---|
|reserved|[7]|must be set to zero|
|DMASK|[11:8]|Data VGPR enable mask: 1 .. 4 consecutive VGPRs<br>Reads: defines which components are returned:<br>0=red,1=green,2=blue,3=alpha<br>Writes: defines which components are written with data from VGPRs (missing<br>components get 0).<br>Enabled components come from consecutive VGPRs.<br>E.G. dmask=1001 : Red is in VGPRn and alpha in VGPRn+1.<br>For D16 writes, DMASK is only used as a word count: each bit represents 16<br>bits of data to be written starting at the LSB’s of VDATA, then MSBs, then<br>VDATA+1 etc. Bit position is ignored.|
|UNRM|[12]|Force address to be un-normalized. Must be set to 1 for Image stores &<br>atomics.|
|GLC|[13]|0 = normal, 1 = globally coherent (bypass L0 cache) or for atomics, return pre-<br>op value to VGPR.|
|DA|[14]|Declare an Array.<br>1 Kernel has declared this resource to be an array of texture maps.<br>0 Kernel has declared this resource to be a single texture map.|
|A16|[15]|Address components are 16-bits (instead of the usual 32 bits).<br>When set, all address components are 16 bits (packed into 2 per dword),<br>except:<br>Texel offsets (3 6bit UINT packed into 1 dword)<br>PCF reference (for "_C" instructions)<br>Address components are 16b uint for image ops without sampler; 16b float with<br>sampler.|
|ACC|[16]|VDATA is Accumulation VGPR|
|LWE|[17]|LOD Warning Enable. When set to 1, a texture fetch may return<br>"LOD_CLAMPED = 1".|
|OP|[0],[24:18]|Opcode. See table below. (combine bits zero and 18-24 to form opcode).|
|SLC|[25]|System level coherent: bypass L2 cache.|
|ENCODING|[31:26]|Must be: 111100|
|VADDR|[39:32]|Address of VGPR to supply first component of address (offset or index). When<br>both index and offset are used, index is in the first VGPR and offset in the<br>second.|



260 of 267

13.6. Vector Memory Image Format

"AMD Instinct MI200" Instruction Set Architecture



|**Field Name**|**Bits**|**Format or Description**|
|---|---|---|
|VDATA|[47:40]|Address of VGPR to supply first component of write data or receive first<br>component of read-data.|
|SRSRC|[52:48]|SGPR to supply V# (resource constant) in 4 or 8 consecutive SGPRs. It is<br>missing 2 LSB’s of SGPR-address since must be aligned to 4.|
|SSAMP|[57:53]|SGPR to supply V# (resource constant) in 4 or 8 consecutive SGPRs. It is<br>missing 2 LSB’s of SGPR-address since must be aligned to 4.|
|D16|[63]|Address offset, unsigned byte.|



_Table 91. MIMG Opcodes_

|**Opcode #**|**Name**||
|---|---|---|
|0|IMAGE|_LOAD|
|1|IMAGE|_LOAD_MIP|
|2|IMAGE|_LOAD_PCK|
|3|IMAGE|_LOAD_PCK_SGN|
|4|IMAGE|_LOAD_MIP_PCK|
|5|IMAGE|_LOAD_MIP_PCK_SGN|
|8|IMAGE|_STORE|
|9|IMAGE|_STORE_MIP|
|10|IMAGE|_STORE_PCK|
|11|IMAGE|_STORE_MIP_PCK|
|14|IMAGE|_GET_RESINFO|
|16|IMAGE|_ATOMIC_SWAP|
|17|IMAGE|_ATOMIC_CMPSWAP|
|18|IMAGE|_ATOMIC_ADD|
|19|IMAGE|_ATOMIC_SUB|
|20|IMAGE|_ATOMIC_SMIN|
|21|IMAGE|_ATOMIC_UMIN|
|22|IMAGE|_ATOMIC_SMAX|
|23|IMAGE|_ATOMIC_UMAX|
|24|IMAGE|_ATOMIC_AND|
|25|IMAGE|_ATOMIC_OR|
|26|IMAGE|_ATOMIC_XOR|
|27|IMAGE|_ATOMIC_INC|
|28|IMAGE|_ATOMIC_DEC|
|32|IMAGE|_SAMPLE|



261 of 267

13.6. Vector Memory Image Format

"AMD Instinct MI200" Instruction Set Architecture



## **13.7. Flat Formats**

Flat memory instructions come in three versions: FLAT:: memory address (per work-item) may be in global memory, scratch (private) memory or shared memory (LDS) GLOBAL:: same as FLAT, but assumes all memory addresses are global memory. SCRATCH:: same as FLAT, but assumes all memory addresses are scratch (private) memory.

The microcode format is identical for each, and only the value of the SEG (segment) field differs.

### **13.7.1. FLAT**



**Format** FLAT

**Description** FLAT Memory Access

_Table 92. FLAT Fields_

|**Field Name**|**Bits**|**Format or Description**|
|---|---|---|
|OFFSET|[12:0]|Address offset<br>Scratch, Global: 13-bit signed byte offset<br>FLAT: 12-bit unsigned offset (MSB is ignored)|
|LDS|[13]|0 = normal, 1 = transfer data between LDS and memory instead of VGPRs and<br>memory.|
|SEG|[15:14]|Memory Segment (instruction type): 0 = flat, 1 = scratch, 2 = global.|
|GLC|[16]|0 = normal, 1 = globally coherent (bypass L0 cache) or for atomics, return pre-<br>op value to VGPR.|
|SLC|[17]|System level coherent: bypass L2 cache.|
|OP|[24:18]|Opcode. See tables below for FLAT, SCRATCH and GLOBAL opcodes.|
|reserved|[25]|must be set to zero|
|ENCODING|[31:26]|Must be: 110111|
|ADDR|[39:32]|VGPR which holds address or offset. For 64-bit addresses, ADDR has the<br>LSB’s and ADDR+1 has the MSBs. For offset a single VGPR has a 32 bit<br>unsigned offset.<br>For FLAT_*: always specifies an address.<br>For GLOBAL_* and SCRATCH_* when SADDR is 0x7f: specifies an address.<br>For GLOBAL_* and SCRATCH_* when SADDR is not 0x7f: specifies an offset.|
|DATA|[47:40]|VGPR which supplies data.|



13.7. Flat Formats

262 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Field Name**|**Bits**|**Format or Description**|
|---|---|---|
|SADDR|[54:48]|Scalar SGPR which provides an address of offset (unsigned). Set this field to<br>0x7f to disable use.|
|||Meaning of this field is different for Scratch and Global:<br>FLAT: Unused<br>Scratch: use an SGPR for the address instead of a VGPR<br>Global: use the SGPR to provide a base address and the VGPR provides a 32-<br>bit byte offset.|
|ACC|[55]|VDATA is Accumulation VGPR|
|VDST|[63:56]|Destination VGPR for data returned from memory to VGPRs.|



_Table 93. FLAT Opcodes_

|**Opcode #**|**Name**|
|---|---|
|16|FLAT_LOAD_UBYTE|
|17|FLAT_LOAD_SBYTE|
|18|FLAT_LOAD_USHORT|
|19|FLAT_LOAD_SSHORT|
|20|FLAT_LOAD_DWORD|
|21|FLAT_LOAD_DWORDX2|
|22|FLAT_LOAD_DWORDX3|
|23|FLAT_LOAD_DWORDX4|
|24|FLAT_STORE_BYTE|
|25|FLAT_STORE_BYTE_D16_HI|
|26|FLAT_STORE_SHORT|
|27|FLAT_STORE_SHORT_D16_HI|
|28|FLAT_STORE_DWORD|
|29|FLAT_STORE_DWORDX2|
|30|FLAT_STORE_DWORDX3|
|31|FLAT_STORE_DWORDX4|
|32|FLAT_LOAD_UBYTE_D16|
|33|FLAT_LOAD_UBYTE_D16_HI|
|34|FLAT_LOAD_SBYTE_D16|
|35|FLAT_LOAD_SBYTE_D16_HI|
|36|FLAT_LOAD_SHORT_D16|
|37|FLAT_LOAD_SHORT_D16_HI|
|64|FLAT_ATOMIC_SWAP|
|65|FLAT_ATOMIC_CMPSWAP|



13.7. Flat Formats

263 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode #**|**Name**||
|---|---|---|
|66|FLAT_ATOMIC|_ADD|
|67|FLAT_ATOMIC|_SUB|
|68|FLAT_ATOMIC|_SMIN|
|69|FLAT_ATOMIC|_UMIN|
|70|FLAT_ATOMIC|_SMAX|
|71|FLAT_ATOMIC|_UMAX|
|72|FLAT_ATOMIC|_AND|
|73|FLAT_ATOMIC|_OR|
|74|FLAT_ATOMIC|_XOR|
|75|FLAT_ATOMIC|_INC|
|76|FLAT_ATOMIC|_DEC|
|79|FLAT_ATOMIC|_ADD_F64|
|80|FLAT_ATOMIC|_MIN_F64|
|81|FLAT_ATOMIC|_MAX_F64|
|96|FLAT_ATOMIC|_SWAP_X2|
|97|FLAT_ATOMIC|_CMPSWAP_X2|
|98|FLAT_ATOMIC|_ADD_X2|
|99|FLAT_ATOMIC|_SUB_X2|
|100|FLAT_ATOMIC|_SMIN_X2|
|101|FLAT_ATOMIC|_UMIN_X2|
|102|FLAT_ATOMIC|_SMAX_X2|
|103|FLAT_ATOMIC|_UMAX_X2|
|104|FLAT_ATOMIC|_AND_X2|
|105|FLAT_ATOMIC|_OR_X2|
|106|FLAT_ATOMIC|_XOR_X2|
|107|FLAT_ATOMIC|_INC_X2|
|108|FLAT_ATOMIC|_DEC_X2|



### **13.7.2. GLOBAL**

_Table 94. GLOBAL Opcodes_

|**Opcode #**|**Name**||
|---|---|---|
|16|GLOBAL|_LOAD_UBYTE|
|17|GLOBAL|_LOAD_SBYTE|



13.7. Flat Formats

264 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode #**|**Name**||
|---|---|---|
|18|GLOBAL|_LOAD_USHORT|
|19|GLOBAL|_LOAD_SSHORT|
|20|GLOBAL|_LOAD_DWORD|
|21|GLOBAL|_LOAD_DWORDX2|
|22|GLOBAL|_LOAD_DWORDX3|
|23|GLOBAL|_LOAD_DWORDX4|
|24|GLOBAL|_STORE_BYTE|
|25|GLOBAL|_STORE_BYTE_D16_HI|
|26|GLOBAL|_STORE_SHORT|
|27|GLOBAL|_STORE_SHORT_D16_HI|
|28|GLOBAL|_STORE_DWORD|
|29|GLOBAL|_STORE_DWORDX2|
|30|GLOBAL|_STORE_DWORDX3|
|31|GLOBAL|_STORE_DWORDX4|
|32|GLOBAL|_LOAD_UBYTE_D16|
|33|GLOBAL|_LOAD_UBYTE_D16_HI|
|34|GLOBAL|_LOAD_SBYTE_D16|
|35|GLOBAL|_LOAD_SBYTE_D16_HI|
|36|GLOBAL|_LOAD_SHORT_D16|
|37|GLOBAL|_LOAD_SHORT_D16_HI|
|64|GLOBAL|_ATOMIC_SWAP|
|65|GLOBAL|_ATOMIC_CMPSWAP|
|66|GLOBAL|_ATOMIC_ADD|
|67|GLOBAL|_ATOMIC_SUB|
|68|GLOBAL|_ATOMIC_SMIN|
|69|GLOBAL|_ATOMIC_UMIN|
|70|GLOBAL|_ATOMIC_SMAX|
|71|GLOBAL|_ATOMIC_UMAX|
|72|GLOBAL|_ATOMIC_AND|
|73|GLOBAL|_ATOMIC_OR|
|74|GLOBAL|_ATOMIC_XOR|
|75|GLOBAL|_ATOMIC_INC|
|76|GLOBAL|_ATOMIC_DEC|
|77|GLOBAL|_ATOMIC_ADD_F32|



13.7. Flat Formats

265 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode #**|**Name**||
|---|---|---|
|78|GLOBAL|_ATOMIC_PK_ADD_F16|
|79|GLOBAL|_ATOMIC_ADD_F64|
|80|GLOBAL|_ATOMIC_MIN_F64|
|81|GLOBAL|_ATOMIC_MAX_F64|
|96|GLOBAL|_ATOMIC_SWAP_X2|
|97|GLOBAL|_ATOMIC_CMPSWAP_X2|
|98|GLOBAL|_ATOMIC_ADD_X2|
|99|GLOBAL|_ATOMIC_SUB_X2|
|100|GLOBAL|_ATOMIC_SMIN_X2|
|101|GLOBAL|_ATOMIC_UMIN_X2|
|102|GLOBAL|_ATOMIC_SMAX_X2|
|103|GLOBAL|_ATOMIC_UMAX_X2|
|104|GLOBAL|_ATOMIC_AND_X2|
|105|GLOBAL|_ATOMIC_OR_X2|
|106|GLOBAL|_ATOMIC_XOR_X2|
|107|GLOBAL|_ATOMIC_INC_X2|
|108|GLOBAL|_ATOMIC_DEC_X2|



### **13.7.3. SCRATCH**

_Table 95. SCRATCH Opcodes_

|**Opcode #**|**Name**|
|---|---|
|16|SCRATCH_LOAD_UBYTE|
|17|SCRATCH_LOAD_SBYTE|
|18|SCRATCH_LOAD_USHORT|
|19|SCRATCH_LOAD_SSHORT|
|20|SCRATCH_LOAD_DWORD|
|21|SCRATCH_LOAD_DWORDX2|
|22|SCRATCH_LOAD_DWORDX3|
|23|SCRATCH_LOAD_DWORDX4|
|24|SCRATCH_STORE_BYTE|
|25|SCRATCH_STORE_BYTE_D16_HI|
|26|SCRATCH_STORE_SHORT|
|27|SCRATCH_STORE_SHORT_D16_HI|



13.7. Flat Formats

266 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Opcode #**|**Name**|
|---|---|
|28|SCRATCH_STORE_DWORD|
|29|SCRATCH_STORE_DWORDX2|
|30|SCRATCH_STORE_DWORDX3|
|31|SCRATCH_STORE_DWORDX4|
|32|SCRATCH_LOAD_UBYTE_D16|
|33|SCRATCH_LOAD_UBYTE_D16_HI|
|34|SCRATCH_LOAD_SBYTE_D16|
|35|SCRATCH_LOAD_SBYTE_D16_HI|
|36|SCRATCH_LOAD_SHORT_D16|
|37|SCRATCH_LOAD_SHORT_D16_HI|



13.7. Flat Formats

267 of 267
