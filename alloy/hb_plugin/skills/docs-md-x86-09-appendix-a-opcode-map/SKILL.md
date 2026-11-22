---
name: docs-md-x86-09-appendix-a-opcode-map
description: "Intel SDM Vol. 2: Appendix A Opcode Map (vendor documentation for x86 AVX2, AVX-512 and AVX-512 FP16)."
when: "when you need Intel SDM Vol. 2: Appendix A Opcode Map while writing a kernel for x86 AVX2, AVX-512 and AVX-512 FP16."
---

APPENDIX A OPCODE MAP

Use the opcode tables in this chapter to interpret IA-32 and Intel 64 architecture object code. Instructions are divided into encoding groups:

- 1-byte, 2-byte and 3-byte opcode encodings are used to encode integer, system, MMX technology, SSE/SSE2/SSE3/SSSE3/SSE4, and VMX instructions. Maps for these instructions are given in Table A-2 through Table A-6.

- Escape opcodes (in the format: ESC character, opcode, ModR/M byte) are used for floating-point instructions. The maps for these instructions are provided in Table A-7 through Table A-22.

#### NOTE

All blanks in opcode maps are reserved and must not be used. Do not depend on the operation of undefined or blank opcodes.

# A.1 USING OPCODE TABLES

Tables in this appendix list opcodes of instructions (including required instruction prefixes, opcode extensions in associated ModR/M byte). Blank cells in the tables indicate opcodes that are reserved or undefined. Cells marked “Reserved-NOP” are also reserved but may behave as NOP on certain processors. Software should not use opcodes corresponding blank cells or cells marked “Reserved-NOP” nor depend on the current behavior of those opcodes.

The opcode map tables are organized by hex values of the upper and lower 4 bits of an opcode byte. For 1-byte encodings (Table A-2), use the four high-order bits of an opcode to index a row of the opcode table; use the four low-order bits to index a column of the table. For 2-byte opcodes beginning with 0FH (Table A-3), skip any instruction prefixes, the 0FH byte (0FH may be preceded by 66H, F2H, or F3H) and use the upper and lower 4-bit values of the next opcode byte to index table rows and columns. Similarly, for 3-byte opcodes beginning with 0F38H or 0F3AH (Table A-4), skip any instruction prefixes, 0F38H or 0F3AH and use the upper and lower 4-bit values of the third opcode byte to index table rows and columns. See Section A.2.4, “Opcode Look-up Examples for One, Two, and Three-Byte Opcodes.”

When a ModR/M byte provides opcode extensions, this information qualifies opcode execution. For information on how an opcode extension in the ModR/M byte modifies the opcode map in Table A-2 and Table A-3, see Section A.4.

The escape (ESC) opcode tables for floating-point instructions identify the eight high order bits of opcodes at the top of each page. See Section A.5. If the accompanying ModR/M byte is in the range of 00H-BFH, bits 3-5 (the top row of the third table on each page) along with the reg bits of ModR/M determine the opcode. ModR/M bytes outside the range of 00H-BFH are mapped by the bottom two tables on each page of the section.

# A.2 KEY TO ABBREVIATIONS

Operands are identified by a two-character code of the form Zz. The first character, an uppercase letter, specifies the addressing method; the second character, a lowercase letter, specifies the type of operand.

## A.2.1 Codes for Addressing Method

The following abbreviations are used to document addressing methods:

- A Direct address: the instruction has no ModR/M byte; the address of the operand is encoded in the instruction. No base register, index register, or scaling factor can be applied (for example, far JMP (EA)).

- B The VEX.vvvv field of the VEX prefix selects a general purpose register.

Vol. 2D A-1

OPCODE MAP

- C The reg field of the ModR/M byte selects a control register (for example, MOV (0F20, 0F22)).

- D The reg field of the ModR/M byte selects a debug register (for example, MOV (0F21,0F23)).

- E A ModR/M byte follows the opcode and specifies the operand. The operand is either a general-purpose register or a memory address. If it is a memory address, the address is computed from a segment register and any of the following values: a base register, an index register, a scaling factor, a displacement.

- F EFLAGS/RFLAGS Register.

- G The reg field of the ModR/M byte selects a general register (for example, AX (000)).

- H The VEX.vvvv field of the VEX prefix selects a 128-bit XMM register or a 256-bit YMM register, determined by operand type. For legacy SSE encodings this operand does not exist, changing the instruction to destructive form.

- I Immediate data: the operand value is encoded in subsequent bytes of the instruction.

- J The instruction contains a relative offset to be added to the instruction pointer register (for example, JMP (0E9), LOOP).

- L The upper 4 bits of the 8-bit immediate selects a 128-bit XMM register or a 256-bit YMM register, determined by operand type. (the MSB is ignored in 32-bit mode)

- M The ModR/M byte may refer only to memory (for example, BOUND, LES, LDS, LSS, LFS, LGS, CMPXCHG8B).

- N The R/M field of the ModR/M byte selects a packed-quadword, MMX technology register.

- O The instruction has no ModR/M byte. The offset of the operand is coded as a word or double word (depending on address size attribute) in the instruction. No base register, index register, or scaling factor can be applied (for example, MOV (A0–A3)).

- P The reg field of the ModR/M byte selects a packed quadword MMX technology register.

- Q A ModR/M byte follows the opcode and specifies the operand. The operand is either an MMX technology register or a memory address. If it is a memory address, the address is computed from a segment register and any of the following values: a base register, an index register, a scaling factor, and a displacement.

- R The R/M field of the ModR/M byte may refer only to a general register (for example, MOV (0F20-0F23)).

- S The reg field of the ModR/M byte selects a segment register (for example, MOV (8C,8E)).

- U The R/M field of the ModR/M byte selects a 128-bit XMM register or a 256-bit YMM register, determined by operand type.

- V The reg field of the ModR/M byte selects a 128-bit XMM register or a 256-bit YMM register, determined by operand type.

- W A ModR/M byte follows the opcode and specifies the operand. The operand is either a 128-bit XMM register, a 256-bit YMM register (determined by operand type), or a memory address. If it is a memory address, the address is computed from a segment register and any of the following values: a base register, an index register, a scaling factor, and a displacement.

- X Memory addressed by the DS:rSI register pair (for example, MOVS, CMPS, OUTS, or LODS).

- Y Memory addressed by the ES:rDI register pair (for example, MOVS, CMPS, INS, STOS, or SCAS).

## A.2.2 Codes for Operand Type

The following abbreviations are used to document operand types:

- a Two one-word operands in memory or two double-word operands in memory, depending on operand-size attribute (used only by the BOUND instruction).

- b Byte, regardless of operand-size attribute.

- c Byte or word, depending on operand-size attribute.

- d Doubleword, regardless of operand-size attribute.

A-2 Vol. 2D

OPCODE MAP

- dq Double-quadword, regardless of operand-size attribute. p 32-bit, 48-bit, or 80-bit pointer, depending on operand-size attribute. pd 128-bit or 256-bit packed double precision floating-point data. pi Quadword MMX technology register (for example: mm0). ps 128-bit or 256-bit packed single-precision floating-point data. q Quadword, regardless of operand-size attribute. qq Quad-Quadword (256-bits), regardless of operand-size attribute. s 6-byte or 10-byte pseudo-descriptor. sd Scalar element of a 128-bit double precision floating data. ss Scalar element of a 128-bit single-precision floating data. si Doubleword integer register (for example: eax).

- v Word, doubleword or quadword (in 64-bit mode), depending on operand-size attribute.

- w Word, regardless of operand-size attribute.

- x dq or qq based on the operand-size attribute.

- y Doubleword or quadword (in 64-bit mode), depending on operand-size attribute. z Word for 16-bit operand-size or doubleword for 32 or 64-bit operand-size.

## A.2.3 Register Codes

When an opcode requires a specific register as an operand, the register is identified by name (for example, AX, CL, or ESI). The name indicates whether the register is 64, 32, 16, or 8 bits wide.

A register identifier of the form eXX or rXX is used when register width depends on the operand-size attribute. eXX is used when 16 or 32-bit sizes are possible; rXX is used when 16, 32, or 64-bit sizes are possible. For example: eAX indicates that the AX register is used when the operand-size attribute is 16 and the EAX register is used when the operand-size attribute is 32. rAX can indicate AX, EAX or RAX.

When the REX.B bit is used to modify the register specified in the reg field of the opcode, this fact is indicated by adding “/x” to the register name to indicate the additional possibility. For example, rCX/r9 is used to indicate that the register could either be rCX or r9. Note that the size of r9 in this case is determined by the operand size attribute (just as for rCX).

## A.2.4 Opcode Look-up Examples for One, Two, and Three-Byte Opcodes

This section provides examples that demonstrate how opcode maps are used.

### A.2.4.1 One-Byte Opcode Instructions

The opcode map for 1-byte opcodes is shown in Table A-2. The opcode map for 1-byte opcodes is arranged by row (the least-significant 4 bits of the hexadecimal value) and column (the most-significant 4 bits of the hexadecimal value). Each entry in the table lists one of the following types of opcodes:

- Instruction mnemonics and operand types using the notations listed in Section A.2

- Opcodes used as an instruction prefix

For each entry in the opcode map that corresponds to an instruction, the rules for interpreting the byte following the primary opcode fall into one of the following cases:

- A ModR/M byte is required and is interpreted according to the abbreviations listed in Section A.1 and Chapter 2, “Instruction Format,” of the _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 2A_ . Operand types are listed according to notations listed in Section A.2.

Vol. 2D A-3

OPCODE MAP

- A ModR/M byte is required and includes an opcode extension in the reg field in the ModR/M byte. Use Table A-6 when interpreting the ModR/M byte.

- Use of the ModR/M byte is reserved or undefined. This applies to entries that represent an instruction prefix or entries for instructions without operands that use ModR/M (for example: 60H, PUSHA; 06H, PUSH ES).

Example A-1.  Look-up Example for 1-Byte Opcodes

Opcode 030500000000H for an ADD instruction is interpreted using the 1-byte opcode map (Table A-2) as follows:

- The first digit (0) of the opcode indicates the table row and the second digit (3) indicates the table column. This locates an opcode for ADD with two operands.

- The first operand (type Gv) indicates a general register that is a word or doubleword depending on the operandsize attribute. The second operand (type Ev) indicates a ModR/M byte follows that specifies whether the operand is a word or doubleword general-purpose register or a memory address.

- The ModR/M byte for this instruction is 05H, indicating that a 32-bit displacement follows (00000000H). The reg/opcode portion of the ModR/M byte (bits 3-5) is 000, indicating the EAX register.

The instruction for this opcode is ADD EAX, mem_op, and the offset of mem_op is 00000000H.

Some 1- and 2-byte opcodes point to group numbers (shaded entries in the opcode map table). Group numbers indicate that the instruction uses the reg/opcode bits in the ModR/M byte as an opcode extension (refer to Section A.4).

### A.2.4.2 Two-Byte Opcode Instructions

The two-byte opcode map shown in Table A-3 includes primary opcodes that are either two bytes or three bytes in length. Primary opcodes that are 2 bytes in length begin with an escape opcode 0FH. The upper and lower four bits of the second opcode byte are used to index a particular row and column in Table A-3.

Two-byte opcodes that are 3 bytes in length begin with a mandatory prefix (66H, F2H, or F3H) and the escape opcode (0FH). The upper and lower four bits of the third byte are used to index a particular row and column in Table A-3 (except when the second opcode byte is the 3-byte escape opcodes 38H or 3AH; in this situation refer to Section A.2.4.3).

For each entry in the opcode map, the rules for interpreting the byte following the primary opcode fall into one of the following cases:

- A ModR/M byte is required and is interpreted according to the abbreviations listed in Section A.1 and Chapter 2, “Instruction Format,” of the _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 2A_ . The operand types are listed according to notations listed in Section A.2.

- A ModR/M byte is required and includes an opcode extension in the reg field in the ModR/M byte. Use Table A-6 when interpreting the ModR/M byte.

- Use of the ModR/M byte is reserved or undefined. This applies to entries that represent an instruction without operands that are encoded using ModR/M (for example: 0F77H, EMMS).

Example A-2.  Look-up Example for 2-Byte Opcodes

Look-up opcode 0FA4050000000003H for a SHLD instruction using Table A-3.

- The opcode is located in row A, column 4. The location indicates a SHLD instruction with operands Ev, Gv, and Ib. Interpret the operands as follows:

   - Ev: The ModR/M byte follows the opcode to specify a word or doubleword operand.

   - Gv: The reg field of the ModR/M byte selects a general-purpose register.

   - Ib: Immediate data is encoded in the subsequent byte of the instruction.

- The third byte is the ModR/M byte (05H). The mod and opcode/reg fields of ModR/M indicate that a 32-bit displacement is used to locate the first operand in memory and eAX as the second operand.

- The next part of the opcode is the 32-bit displacement for the destination memory operand (00000000H). The last byte stores immediate byte that provides the count of the shift (03H).

A-4 Vol. 2D

OPCODE MAP

- By this breakdown, it has been shown that this opcode represents the instruction: SHLD DS:00000000H, EAX, 3.

### A.2.4.3 Three-Byte Opcode Instructions

The three-byte opcode maps shown in Table A-4 and Table A-5 includes primary opcodes that are either 3 or 4 bytes in length. Primary opcodes that are 3 bytes in length begin with two escape bytes 0F38H or 0F3A. The upper and lower four bits of the third opcode byte are used to index a particular row and column in Table A-4 or Table A-5.

Three-byte opcodes that are 4 bytes in length begin with a mandatory prefix (66H, F2H, or F3H) and two escape bytes (0F38H or 0F3AH). The upper and lower four bits of the fourth byte are used to index a particular row and column in Table A-4 or Table A-5.

For each entry in the opcode map, the rules for interpreting the byte following the primary opcode fall into the following case:

- A ModR/M byte is required and is interpreted according to the abbreviations listed in A.1 and Chapter 2, “Instruction Format,” of the _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 2A_ . The operand types are listed according to notations listed in Section A.2.

##### Example A-3.  Look-up Example for 3-Byte Opcodes

Look-up opcode 660F3A0FC108H for a PALIGNR instruction using Table A-5.

- 66H is a prefix and 0F3AH indicate to use Table A-5. The opcode is located in row 0, column F indicating a PALIGNR instruction with operands Vdq, Wdq, and Ib. Interpret the operands as follows:

   - Vdq: The reg field of the ModR/M byte selects a 128-bit XMM register.

   - Wdq: The R/M field of the ModR/M byte selects either a 128-bit XMM register or memory location.

      - Ib: Immediate data is encoded in the subsequent byte of the instruction.

- The next byte is the ModR/M byte (C1H). The reg field indicates that the first operand is XMM0. The mod shows that the R/M field specifies a register and the R/M indicates that the second operand is XMM1.

- The last byte is the immediate byte (08H).

- By this breakdown, it has been shown that this opcode represents the instruction: PALIGNR XMM0, XMM1, 8.

### A.2.4.4 VEX Prefix Instructions

Instructions that include a VEX prefix are organized relative to the 2-byte and 3-byte opcode maps, based on the VEX.mmmmm field encoding of implied 0F, 0F38H, 0F3AH, respectively. Each entry in the opcode map of a VEXencoded instruction is based on the value of the opcode byte, similar to non-VEX-encoded instructions.

A VEX prefix includes several bit fields that encode implied 66H, F2H, F3H prefix functionality (VEX.pp) and operand size/opcode information (VEX.L). See chapter 4 for details.

Opcode tables A2-A6 include both instructions with a VEX prefix and instructions without a VEX prefix. Many entries are only made once, but represent both the VEX and non-VEX forms of the instruction. If the VEX prefix is present all the operands are valid and the mnemonic is usually prefixed with a “v”. If the VEX prefix is not present the VEX.vvvv operand is not available and the prefix “v” is dropped from the mnemonic.

A few instructions exist only in VEX form and these are marked with a superscript “v”.

Operand size of VEX prefix instructions can be determined by the operand type code. 128-bit vectors are indicated by 'dq', 256-bit vectors are indicated by 'qq', and instructions with operands supporting either 128 or 256-bit, determined by VEX.L, are indicated by 'x'. For example, the entry "VMOVUPD Vx,Wx" indicates both VEX.L=0 and VEX.L=1 are supported.

Vol. 2D A-5

OPCODE MAP

## A.2.5 Superscripts Utilized in Opcode Tables

Table A-1 contains notes on particular encodings. These notes are indicated in the following opcode maps by superscripts. Gray cells indicate instruction groupings.

Table A-1.  Superscripts Utilized in Opcode Tables

|Superscript<br>Symbol|Meaning of Symbol|
|---|---|
|1A|Bits 5, 4, and 3 of ModR/M byte used as an opcode extension (refer to Section A.4, “Opcode Extensions For One-Byte<br>And Two-byte Opcodes”).|
|1B|Use the 0F0B opcode (UD2 instruction), the 0FB9H opcode (UD1 instruction), or the 0FFFH opcode (UD0 instruction)<br>when deliberately trying to generate an invalid opcode exception (#UD).|
|1C|Some instructions use the same two-byte opcode. If the instruction has variations, or the opcode represents<br>different instructions, the ModR/M byte will be used to differentiate the instruction. For the value of the ModR/M<br>byte needed to decode the instruction, see Table A-6.|
|i64|The instruction is invalid or not encodable in 64-bit mode. 40 through 4F (single-byte INC and DEC) are REX prefix<br>combinations when in 64-bit mode (use FE/FF Grp 4 and 5 for INC and DEC).|
|o64|Instruction is only available when in 64-bit mode.|
|d64|When in 64-bit mode, instruction defaults to 64-bit operand size and cannot encode 32-bit operand size.|
|f64|The operand size is forced to a 64-bit operand size when in 64-bit mode (prefixes that change operand size are<br>ignored for this instruction in 64-bit mode).|
|v|VEX form only exists. There is no legacy SSE form of the instruction. For Integer GPR instructions it means VEX<br>prefix required.|
|v1|VEX128 & SSE forms only exist (no VEX256), when can’t be inferred from the data size.|



# A.3 ONE, TWO, AND THREE-BYTE OPCODE MAPS

See Table A-2 through Table A-5 below. The tables are multiple page presentations. Rows and columns with sequential relationships are placed on facing pages to make look-up tasks easier. Note that table footnotes are not presented on each page. Table footnotes for each table are presented on the last page of the table.

A-6 Vol. 2D

OPCODE MAP

Table A-2.  One-byte Opcode Map: (00H — F7H) *

|0|1|2|3|4|5|6|7|
|---|---|---|---|---|---|---|---|
|0||A|DD|||PUSH<br>|POP<br>|
|Eb, Gb|Ev, Gv|Gb, Eb|Gv, Ev|AL, Ib|rAX, Iz|ES<sup>i64</sup>|ES<sup>i64</sup>|
|1<br>Eb, Gb|Ev, Gv|A<br>Gb, Eb|DC<br>Gv, Ev|AL, Ib|rAX, Iz|PUSH<br>SS<sup>i64</sup>|POP<br>SS<sup>i64</sup>|
|2<br>Eb, Gb|Ev, Gv|A<br>Gb, Eb|ND<br>Gv, Ev|AL, Ib|rAX, Iz|SEG=ES<br>(Prefix)|DAA<sup>i64</sup>|
|3<br>Eb, Gb|Ev, Gv|X<br>Gb, Eb|OR<br>Gv, Ev|AL, Ib|rAX, Iz|SEG=SS<br>(Prefix)|AAA<sup>i64</sup>|
|4|||INC<sup>i64</sup>general regis|ter / REX<sup>o64</sup>Prefixe|s|||
|eAX<br>|eCX<br>|eDX<br>|eBX<br>|eSP<br>|eBP<br>|eSI<br>|eDI<br>|
|REX|REX.B|REX.X|REX.XB|REX.R|REX.RB|REX.RX|REX.RXB|
|5|||PUSH<sup>d64</sup>ge|neral register||||
|rAX/r8|rCX/r9|rDX/r10|rBX/r11|rSP/r12|rBP/r13|rSI/r14|rDI/r15|
|6<br>PUSHA<sup>i64</sup>/<br>PUSHAD<sup>i64</sup>|POPA<sup>i64</sup>/<br>POPAD<sup>i64</sup>|BOUND<sup>i64</sup><br>Gv, Ma|ARPL<sup>i64</sup><br>Ew, Gw<br>MOVSXD<sup>o64</sup>|SEG=FS<br>(Prefix)|SEG=GS<br>(Prefix)|Operand<br>Size<br>(Prefix)|Address<br>Size<br>(Prefix)|
|7||Jc|Gv, Ev<br>c<sup>f64</sup>, Jb - Short-displa|cement jump on con|dition|||
|O|NO|B/NAE/C|NB/AE/NC|Z/E|NZ/NE|BE/NA|NBE/A|
|8|Immed|iate Grp 1<sup>1A</sup>||TE|ST|X|CHG|
|Eb, Ib|Ev, Iz|Eb, Ib<sup>i64</sup>|Ev, Ib|Eb, Gb|Ev, Gv|Eb, Gb|Ev, Gv|
|9<br>NOP<br>PAUSE(F3)|||XCHG word, doub|le-word or quad-wo|rd register with rAX|||
|XCHG r8, rAX|rCX/r9|rDX/r10|rBX/r11|rSP/r12|rBP/r13|rSI/r14|rDI/r15|
|A||MOV||MOVS/B<br>Yb Xb|MOVS/W/D/Q<br>Y X|CMPS/B<br>Xb Yb|CMPS/W/D<br>X Y|
|AL, Ob|rAX, Ov|Ob, AL|Ov, rAX|,|v, v|,|v, v|
|B|||MOV immediate b|yte into byte register||||
|AL/R8B, Ib|CL/R9B, Ib|DL/R10B, Ib|BL/R11B, Ib|AH/R12B, Ib|CH/R13B, Ib|DH/R14B, Ib|BH/R15B, Ib|
|C<br>Shift G|rp 2<sup>1A</sup>|near RET<sup>f64</sup><br>|near RET<sup>f64</sup>|LES<sup>i64</sup><br>|LDS<sup>i64</sup><br>|Grp 1|1<sup>1A</sup>- MOV|
|Eb, Ib|Ev, Ib|Iw||Gz, Mp<br>VEX+2byte|Gz, Mp<br>VEX+1byte|Eb, Ib|Ev, Iz|
|D|Shif|t Grp 2<sup>1A</sup>||AAM<sup>i64</sup><br>|AAD<sup>i64</sup><br>||XLAT/<br>|
|Eb, 1|Ev, 1|Eb, CL|Ev, CL|Ib|Ib||XLATB|
|E<br>LOOPNE<sup>f64</sup>/<br>LOOPNZ<sup>f64</sup><br>Jb|LOOPE<sup>f64</sup>/<br>LOOPZ<sup>f64</sup><br>Jb|LOOP<sup>f64</sup><br>Jb|JrCXZ<sup>f64</sup>/<br>Jb|IN<br>AL, Ib|eAX, Ib|Ib, AL|OUT<br>Ib, eAX|
|F<br>LOCK<br>(Prefix)|INT1|REPNE<br>XACQUIRE<br>(Prefix)|REP/REPE<br>XRELEASE<br>(Prefix)|HLT|CMC|Unar<br>Eb|y Grp 3<sup>1A</sup><br>Ev|



Vol. 2D A-7

OPCODE MAP

Table A-2. One-byte Opcode Map: (08H — FFH) *

||8|9|A|B|C|D|E|F|
|---|---|---|---|---|---|---|---|---|
|0||||OR|||PUSH<br>|2-byte|
||Eb, Gb|Ev, Gv|Gb, Eb|Gv, Ev|AL, Ib|rAX, Iz|CS<sup>i64</sup>|escape<br>(Table A-3)|
|1|Eb, Gb|Ev, Gv|S<br>Gb, Eb|BB<br>Gv, Ev|AL, Ib|rAX, Iz|PUSH<br>DS<sup>i64</sup>|POP<br>DS<sup>i64</sup>|
|2|Eb, Gb|Ev, Gv|S<br>Gb, Eb|UB<br>Gv, Ev|AL, Ib|rAX, Iz|SEG=CS<br>(Prefix)|DAS<sup>i64</sup>|
|3|Eb, Gb|Ev, Gv|C<br>Gb, Eb|MP<br>Gv, Ev|AL, Ib|rAX, Iz|SEG=DS<br>(Prefix)|AAS<sup>i64</sup>|
|4||||DEC<sup>i64</sup>general regis<br>|ter / REX<sup>o64</sup>Prefixe<br>|s<br>|||
||eAX<br>REX.W|eCX<br>REX.WB|eDX<br>REX.WX|eBX<br>REX.WXB|eSP<br>REX.WR|eBP<br>REX.WRB|eSI<br>REX.WRX|eDI<br>REX.WRXB|
|5||||POP<sup>d64</sup>into g<br>|eneral register<br>||||
||rAX/r8|rCX/r9|rDX/r10|rBX/r11|rSP/r12|rBP/r13|rSI/r14|rDI/r15|
|6|PUSH<sup>d64</sup><br>Iz|IMUL<br>Gv, Ev, Iz|PUSH<sup>d64</sup><br>Ib|IMUL<br>Gv, Ev, Ib|INS/<br>INSB<br>Yb, DX|INS/<br>INSW/<br>INSD|OUTS/<br>OUTSB<br>DX, Xb|OUTS/<br>OUTSW/<br>OUTSD|
|||||||Yz, DX||DX, Xz|
|7|||Jcc|<sup>f64</sup>, Jb- Short displac|ement jump on cond|ition|||
||S|NS|P/PE|NP/PO|L/NGE|NL/GE|LE/NG|NLE/G|
|8|Eb, Gb|M<br>Ev, Gv|OV<br>Gb, Eb|Gv, Ev|MOV<br>Ev, Sw|LEA<br>Gv, M|MOV<br>Sw, Ew|Grp 1A<sup>1A</sup>POP<sup>d64</sup><br>Ev|
|9|CBW/<br>CWDE/<br>CDQE|CWD/<br>CDQ/<br>CQO|far CALL<sup>i64</sup><br>Ap|FWAIT/<br>WAIT|PUSHF/D/Q<sup>d64</sup>/<br>Fv|POPF/D/Q<sup>d64</sup>/<br>Fv|SAHF|LAHF|
|A|TES|T|STOS/B<br>|STOS/W/D/Q<br>|LODS/B<br>|LODS/W/D/Q<br>|SCAS/B<br>|SCAS/W/D/Q<br>|
||AL, Ib|rAX, Iz|Yb, AL|Yv, rAX|AL, Xb|rAX, Xv|AL, Yb|rAX, Yv|
|B|||MOV immed<br>|iate word or double i<br>|nto word, double, or<br>|quad register<br>|||
||rAX/r8, Iv|rCX/r9, Iv|rDX/r10, Iv|rBX/r11, Iv|rSP/r12, Iv|rBP/r13, Iv|rSI/r14, Iv|rDI/r15 , Iv|
|C|ENTER|LEAVE<sup>d64</sup>|far RET|far RET|INT3|INT|INTO<sup>i64</sup>|IRET/D/Q|
||Iw, Ib||Iw|||Ib|||
|D|||E|SC (Escape to copro|cessor instruction se|t)|||
|E|near CALL<sup>f64</sup>||JMP||I|N|O|UT|
||Jz|near<sup>f64</sup>|far<sup>i64</sup>|short<sup>f64</sup>|AL, DX|eAX, DX|DX, AL|DX, eAX|
|||Jz|Ap|Jb|||||
|F|CLC|STC|CLI|STI|CLD|STD|INC/DEC|INC/DEC|
||||||||Grp 4<sup>1A</sup>|Grp 5<sup>1A</sup>|



**NOTES:**

* All blanks in all opcode maps are reserved and must not be used. Do not depend on the operation of undefined or reserved locations.

A-8 Vol. 2D

OPCODE MAP

Table A-3.  Two-byte Opcode Map: 00H — 77H (First Byte is 0FH) *

|pfx|0<br>|1<br>|2|3|4|5<br>|6|7<br>|
|---|---|---|---|---|---|---|---|---|
|0|Grp 6<sup>1A</sup>|Grp 7<sup>1A</sup>|LAR<br>Gv, Ew|LSL<br>Gv, Ew||SYSCALL<sup>o64</sup>|CLTS|SYSRET<sup>o64</sup>|
||vmovups<br>Vps, Wps|vmovups<br>Wps, Vps|vmovlps<br>Vq, Hq, Mq<br>vmovhlps<br>Vq, Hq, Uq|vmovlps<br>Mq, Vq|vunpcklps<br>Vx, Hx, Wx|vunpckhps<br>Vx, Hx, Wx|vmovhps<sup>v1</sup><br>Vdq, Hq, Mq<br>vmovlhps<br>Vdq, Hq, Uq|vmovhps<sup>v1</sup><br>Mq, Vq|
|1<br>66|vmovupd<br>Vpd, Wpd|vmovupd<br>Wpd,Vpd|vmovlpd<br>Vq, Hq, Mq|vmovlpd<br>Mq, Vq|vunpcklpd<br>Vx,Hx,Wx|vunpckhpd<br>Vx,Hx,Wx|vmovhpd<sup>v1</sup><br>Vdq, Hq, Mq|vmovhpd<sup>v1</sup><br>Mq, Vq|
|F3|vmovss<br>Vx, Hx, Wss|vmovss<br>Wss, Hx, Vss|vmovsldup<br>Vx, Wx||||vmovshdup<br>Vx, Wx||
|F2|vmovsd<br>Vx, Hx, Wsd|vmovsd<br>Wsd, Hx, Vsd|vmovddup<br>Vx, Wx||||||
|2|MOV<br>Rd, Cd|MOV<br>Rd, Dd|MOV<br>Cd, Rd|MOV<br>Dd, Rd|||||
|3|WRMSR|RDTSC|RDMSR|RDPMC|SYSENTER|SYSEXIT||GETSEC|
|||||CMOVcc, (Gv, Ev|) - Conditional Move||||
|4|O|NO|B/C/NAE|AE/NB/NC|E/Z|NE/NZ|BE/NA|A/NBE|
||vmovmskps<br>Gy, Ups|vsqrtps<br>Vps, Wps|vrsqrtps<br>Vps, Wps|vrcpps<br>Vps, Wps|vandps<br>Vps, Hps, Wps|vandnps<br>Vps, Hps, Wps|vorps<br>Vps, Hps, Wps|vxorps<br>Vps, Hps, Wps|
|5<br>66|vmovmskpd<br>Gy,Upd|vsqrtpd<br>Vpd, Wpd|||vandpd<br>Vpd, Hpd, Wpd|vandnpd<br>Vpd, Hpd, Wpd|vorpd<br>Vpd, Hpd, Wpd|vxorpd<br>Vpd, Hpd, Wpd|
|F3||vsqrtss<br>Vss, Hss, Wss|vrsqrtss<br>Vss, Hss, Wss|vrcpss<br>Vss, Hss, Wss|||||
|F2||vsqrtsd<br>Vsd, Hsd, Wsd|||||||
||punpcklbw<br>Pq, Qd|punpcklwd<br>Pq, Qd|punpckldq<br>Pq, Qd|packsswb<br>Pq, Qq|pcmpgtb<br>Pq, Qq|pcmpgtw<br>Pq, Qq|pcmpgtd<br>Pq, Qq|packuswb<br>Pq, Qq|
|6<br>66|vpunpcklbw<br>Vx, Hx, Wx|vpunpcklwd<br>Vx, Hx, Wx|vpunpckldq<br>Vx, Hx, Wx|vpacksswb<br>Vx, Hx, Wx|vpcmpgtb<br>Vx, Hx, Wx|vpcmpgtw<br>Vx, Hx, Wx|vpcmpgtd<br>Vx, Hx, Wx|vpackuswb<br>Vx, Hx, Wx|
|F3|||||||||
||pshufw<br>Pq, Qq, Ib|(Grp 12<sup>1A</sup>)|(Grp 13<sup>1A</sup>)|(Grp 14<sup>1A</sup>)|pcmpeqb<br>Pq, Qq|pcmpeqw<br>Pq, Qq|pcmpeqd<br>Pq, Qq|emms<br>vzeroupper<sup>v</sup><br>vzeroall<sup>v</sup>|
|7<br>66|vpshufd<br>Vx, Wx, Ib||||vpcmpeqb<br>Vx, Hx, Wx|vpcmpeqw<br>Vx, Hx, Wx|vpcmpeqd<br>Vx, Hx, Wx||
|F3|vpshufhw<br>Vx, Wx, Ib||||||||
|F2|vpshuflw<br>Vx, Wx, Ib||||||||



Vol. 2D A-9

OPCODE MAP

Table A-3. Two-byte Opcode Map: 08H — 7FH (First Byte is 0FH) *

|pfx|8|9|A|B|C|D|E|F|
|---|---|---|---|---|---|---|---|---|
|0|INVD|WBINVD||2-byte Illegal<br>Opcodes<br>UD2<sup>1B</sup>||prefetchw(/1)<br>Ev|||
||Prefetch<sup>1C</sup><br> <sup>1A</sup>|Reserved-NOP|bndldx|bndstx||Reserved-NOP||NOP /0 Ev|
|66|(Grp 16)||bndmov|bndmov|||||
|1<br>F3|||bndcl|bndmk|||||
|F2|||bndcu|bndcn|||||
||vmovaps|vmovaps|cvtpi2ps<br>|vmovntps|cvttps2pi|cvtps2pi|vucomiss|vcomiss|
||Vps, Wps|Wps, Vps|Vps, Qpi|Mps, Vps|Ppi, Wps|Ppi, Wps|Vss, Wss|Vss, Wss|
|2<br>66|vmovapd<br>Vpd, Wpd|vmovapd<br>Wpd,Vpd|cvtpi2pd<br>Vpd, Qpi|vmovntpd<br>Mpd, Vpd|cvttpd2pi<br>Ppi, Wpd|cvtpd2pi<br>Qpi, Wpd|vucomisd<br>Vsd, Wsd|vcomisd<br>Vsd, Wsd|
|<br>F3|||vcvtsi2ss<br>Vss, Hss, Ey||vcvttss2si<br>Gy, Wss|vcvtss2si<br>Gy, Wss|||
|F2|||vcvtsi2sd<br>Vsd, Hsd, Ey||vcvttsd2si<br>Gy, Wsd|vcvtsd2si<br>Gy, Wsd|||
|3|3-byte escape<br>(Table A-4)||3-byte escape<br>(Table A-5)||||||
|||||CMOVcc(Gv, Ev)<br>|- Conditional Move<br>||||
|4|S|NS|P/PE|NP/PO|L/NGE|NL/GE|LE/NG|NLE/G|
||vaddps<br>Vps, Hps, Wps|vmulps<br>Vps, Hps, Wps|vcvtps2pd<br>Vpd, Wps|vcvtdq2ps<br>Vps, Wdq|vsubps<br>Vps, Hps, Wps|vminps<br>Vps, Hps, Wps|vdivps<br>Vps, Hps, Wps|vmaxps<br>Vps, Hps, Wps|
|5<br>66|vaddpd<br>Vpd, Hpd, Wpd|vmulpd<br>Vpd, Hpd, Wpd|vcvtpd2ps<br>Vps, Wpd|vcvtps2dq<br>Vdq, Wps|vsubpd<br>Vpd, Hpd, Wpd|vminpd<br>Vpd, Hpd, Wpd|vdivpd<br>Vpd, Hpd, Wpd|vmaxpd<br>Vpd, Hpd, Wpd|
|F3|vaddss<br>Vss, Hss, Wss|vmulss<br>Vss, Hss, Wss|vcvtss2sd<br>Vsd, Hx, Wss|vcvttps2dq<br>Vdq, Wps|vsubss<br>Vss, Hss, Wss|vminss<br>Vss, Hss, Wss|vdivss<br>Vss, Hss, Wss|vmaxss<br>Vss, Hss, Wss|
|F2|vaddsd<br>Vsd, Hsd, Wsd|vmulsd<br>Vsd, Hsd, Wsd|vcvtsd2ss<br>Vss, Hx, Wsd||vsubsd<br>Vsd, Hsd, Wsd|vminsd<br>Vsd, Hsd, Wsd|vdivsd<br>Vsd, Hsd, Wsd|vmaxsd<br>Vsd, Hsd, Wsd|
||punpckhbw<br>Pq, Qd|punpckhwd<br>Pq, Qd|punpckhdq<br>Pq, Qd|packssdw<br>Pq, Qd|||movd/q<br>Pd, Ey|movq<br>Pq, Qq|
|6<br>66|vpunpckhbw<br>Vx, Hx, Wx|vpunpckhwd<br>Vx, Hx, Wx|vpunpckhdq<br>Vx, Hx, Wx|vpackssdw<br>Vx, Hx, Wx|vpunpcklqdq<br>Vx, Hx, Wx|vpunpckhqdq<br>Vx, Hx, Wx|vmovd/q<br>Vy, Ey|vmovdqa<br>Vx, Wx|
|F3||||||||vmovdqu<br>Vx, Wx|
||VMREAD<br>Ey, Gy|VMWRITE<br>Gy, Ey|||||movd/q<br>Ey, Pd|movq<br>Qq, Pq|
|66|||||vhaddpd<br>Vpd, Hpd, Wpd|vhsubpd<br>Vpd, Hpd, Wpd|vmovd/q<br>Ey, Vy|vmovdqa<br>Wx,Vx|
|7<br>F3|||||||vmovq<br>Vq, Wq|vmovdqu<br>Wx,Vx|
|F2|||||vhaddps<br>Vps, Hps, Wps|vhsubps<br>Vps, Hps, Wps|||



A-10 Vol. 2D

OPCODE MAP

Table A-3. Two-byte Opcode Map: 80H — F7H (First Byte is 0FH) *

|pfx|0|1|2<br><sup>f6</sup>|3<br>|4<br>|5<br>|6|7|
|---|---|---|---|---|---|---|---|---|
||||Jcc|, Jz - Long-displac|ement jump on conditio|n|||
|8||||<br>|<br>|<br>|||
||O|NO|B/CNAE|AE/NB/NC|E/Z|NE/NZ|BE/NA|A/NBE|
|||||SETcc, Eb - Byte<br>|Set on condition<br>||||
|9|O|NO|B/C/NAE|AE/NB/NC|E/Z|NE/NZ|BE/NA|A/NBE|
|A|PUSH<sup>d64</sup><br>FS|POP<sup>d64</sup><br>FS|CPUID|BT<br>Ev, Gv|SHLD<br>Ev, Gv, Ib|SHLD<br>Ev, Gv, CL|||
||CMPX|CHG|LSS<br>G M|BTR<br>E G|LFS<br>G M|LGS<br>G M|MO|VZX|
|B|Eb, Gb|Ev, Gv|v, p|v, v|v, p|v, p|Gv, Eb|Gv, Ew|
||XADD<br>Eb, Gb|XADD<br>Ev, Gv|vcmpps<br>Vps,Hps,Wps,Ib|movnti<br>My, Gy|pinsrw<br>Pq,Ry/Mw,Ib|pextrw<br>Gd, Nq, Ib|vshufps<br>Vps,Hps,Wps,Ib|Grp 9<sup>1A</sup>|
|C<br>66|||vcmppd<br>Vpd,Hpd,Wpd,Ib||vpinsrw<br>Vdq,Hdq,Ry/Mw,Ib|vpextrw<br>Gd, Udq, Ib|vshufpd<br>Vpd,Hpd,Wpd,Ib||
|F3|||vcmpss<br>Vss,Hss,Wss,Ib||||||
|F2|||vcmpsd<br>Vsd,Hsd,Wsd,Ib||||||
|||psrlw<br>Pq, Qq|psrld<br>Pq, Qq|psrlq<br>Pq, Qq|paddq<br>Pq, Qq|pmullw<br>Pq, Qq||pmovmskb<br>Gd, Nq|
|D<br>66|vaddsubpd<br>Vpd, Hpd, Wpd|vpsrlw<br>Vx, Hx, Wx|vpsrld<br>Vx, Hx, Wx|vpsrlq<br>Vx, Hx, Wx|vpaddq<br>Vx, Hx, Wx|vpmullw<br>Vx, Hx, Wx|vmovq<br>Wq, Vq|vpmovmskb<br>Gd, Ux|
|F3|||||||movq2dq<br>Vdq, Nq||
|F2|vaddsubps<br>Vps, Hps, Wps||||||movdq2q<br>Pq, Uq||
||pavgb<br>Pq, Qq|psraw<br>Pq, Qq|psrad<br>Pq, Qq|pavgw<br>Pq, Qq|pmulhuw<br>Pq, Qq|pmulhw<br>Pq, Qq||movntq<br>Mq, Pq|
|E<br>66|vpavgb<br>Vx, Hx, Wx|vpsraw<br>Vx, Hx, Wx|vpsrad<br>Vx, Hx, Wx|vpavgw<br>Vx, Hx, Wx|vpmulhuw<br>Vx, Hx, Wx|vpmulhw<br>Vx, Hx, Wx|vcvttpd2dq<br>Vx, Wpd|vmovntdq<br>Mx, Vx|
|F3|||||||vcvtdq2pd<br>Vx, Wpd||
|F2|||||||vcvtpd2dq<br>Vx, Wpd||
|||psllw<br>Pq, Qq|pslld<br>Pq, Qq|psllq<br>Pq, Qq|pmuludq<br>Pq, Qq|pmaddwd<br>Pq, Qq|psadbw<br>Pq, Qq|maskmovq<br>Pq, Nq|
|F<br>66||vpsllw<br>Vx, Hx, Wx|vpslld<br>Vx, Hx, Wx|vpsllq<br>Vx, Hx, Wx|vpmuludq<br>Vx, Hx, Wx|vpmaddwd<br>Vx, Hx, Wx|vpsadbw<br>Vx, Hx, Wx|vmaskmovdqu<br>Vdq, Udq|
|F2|vlddqu<br>Vx, Mx||||||||



Vol. 2D A-11

OPCODE MAP

Table A-3. Two-byte Opcode Map: 88H — FFH (First Byte is 0FH) *

|pfx<br>8|8|9|A<br>Jcc<sup>f</sup>|B<br><sup>64</sup>, Jz - Long-displac|C<br>ement jump on cond|D<br>ition|E|F|
|---|---|---|---|---|---|---|---|---|
||S|NS|P/PE|NP/PO|L/NGE|NL/GE|LE/NG|NLE/G|
|||||SETcc, Eb - Byte|Set on condition||||
|9|S|NS|P/PE|NP/PO|L/NGE|NL/GE|LE/NG|NLE/G|
|A|PUSH<sup>d64</sup><br>GS|POP<sup>d64</sup><br>GS|RSM|BTS<br>Ev, Gv|SHRD<br>Ev, Gv, Ib|SHRD<br>Ev, Gv, CL|(Grp 15<sup>1A</sup>)<sup>1C</sup>|IMUL<br>Gv, Ev|
|B|_JMPE_<br>(reserved for<br>emulator on IPF)|Grp 10<sup>1A</sup><br>Invalid Opcode<sup>1B</sup>|Grp 8<sup>1A</sup><br>Ev, Ib|BTC<br>Ev, Gv|BSF<br>Gv, Ev|BSR<br>Gv, Ev|MO<br>Gv, Eb|VSX<br>Gv, Ew|
|F3|POPCNT||||TZCNT|LZCNT|||
||Gv, Ev||||Gv, Ev|Gv, Ev|||
|||||BS<br>|WAP<br>||||
|C|RAX/EAX/<br>R8/R8D|RCX/ECX/<br>R9/R9D|RDX/EDX/<br>R10/R10D|RBX/EBX/<br>R11/R11D|RSP/ESP/<br>R12/R12D|RBP/EBP/<br>R13/R13D|RSI/ESI/<br>R14/R14D|RDI/EDI/<br>R15/R15D|
||psubusb<br>Pq, Qq|psubusw<br>Pq, Qq|pminub<br>Pq, Qq|pand<br>Pq, Qq|paddusb<br>Pq, Qq|paddusw<br>Pq, Qq|pmaxub<br>Pq, Qq|pandn<br>Pq, Qq|
|D<br>66|vpsubusb<br>Vx, Hx, Wx|vpsubusw<br>Vx, Hx, Wx|vpminub<br>Vx, Hx, Wx|vpand<br>Vx, Hx, Wx|vpaddusb<br>Vx, Hx, Wx|vpaddusw<br>Vx, Hx, Wx|vpmaxub<br>Vx, Hx, Wx|vpandn<br>Vx, Hx, Wx|
|F3|||||||||
|F2|||||||||
||psubsb<br>Pq, Qq|psubsw<br>Pq, Qq|pminsw<br>Pq, Qq|por<br>Pq, Qq|paddsb<br>Pq, Qq|paddsw<br>Pq, Qq|pmaxsw<br>Pq, Qq|pxor<br>Pq, Qq|
|E<br>66|vpsubsb<br>Vx, Hx, Wx|vpsubsw<br>Vx, Hx, Wx|vpminsw<br>Vx, Hx, Wx|vpor<br>Vx, Hx, Wx|vpaddsb<br>Vx, Hx, Wx|vpaddsw<br>Vx, Hx, Wx|vpmaxsw<br>Vx, Hx, Wx|vpxor<br>Vx, Hx, Wx|
|F3|||||||||
|F2|||||||||
||psubb<br>Pq, Qq|psubw<br>Pq, Qq|psubd<br>Pq, Qq|psubq<br>Pq, Qq|paddb<br>Pq, Qq|paddw<br>Pq, Qq|paddd<br>Pq, Qq|UD0|
|F<br>66|vpsubb<br>Vx, Hx, Wx|vpsubw<br>Vx, Hx, Wx|vpsubd<br>Vx, Hx, Wx|vpsubq<br>Vx, Hx, Wx|vpaddb<br>Vx, Hx, Wx|vpaddw<br>Vx, Hx, Wx|vpaddd<br>Vx, Hx, Wx||
|F2|||||||||



**NOTES:**

* All blanks in all opcode maps are reserved and must not be used. Do not depend on the operation of undefined or reserved locations.

A-12 Vol. 2D

OPCODE MAP

Table A-4.  Three-byte Opcode Map: 00H — F7H (First Two Bytes are 0F 38H) *

|pfx|0|1|2|3|4|5|6|7|
|---|---|---|---|---|---|---|---|---|
|0|pshufb<br>Pq, Qq|phaddw<br>Pq, Qq|phaddd<br>Pq, Qq|phaddsw<br>Pq, Qq|pmaddubsw<br>Pq, Qq|phsubw<br>Pq, Qq|phsubd<br>Pq, Qq|phsubsw<br>Pq, Qq|
|66|vpshufb<br>Vx,Hx,Wx|vphaddw<br>Vx,Hx,Wx|vphaddd<br>Vx,Hx,Wx|vphaddsw<br>Vx,Hx,Wx|vpmaddubsw<br>Vx,Hx,Wx|vphsubw<br>Vx,Hx,Wx|vphsubd<br>Vx,Hx,Wx|vphsubsw<br>Vx,Hx,Wx|
|1<br>66|pblendvb<br>Vdq, Wdq|||vcvtph2ps<sup>v</sup><br>Vx, Wx, Ib|blendvps<br>Vdq, Wdq|blendvpd<br>Vdq, Wdq|vpermps<sup>v</sup><br>Vqq, Hqq, Wqq|vptest<br>Vx, Wx|
|2<br>66|vpmovsxbw<br>Vx,Ux/Mq|vpmovsxbd<br>Vx,Ux/Md|vpmovsxbq<br>Vx,Ux/Mw|vpmovsxwd<br>Vx,Ux/Mq|vpmovsxwq<br>Vx,Ux/Md|vpmovsxdq<br>Vx,Ux/Mq|||
|3<br>66|vpmovzxbw<br>Vx,Ux/Mq|vpmovzxbd<br>Vx,Ux/Md|vpmovzxbq<br>Vx,Ux/Mw|vpmovzxwd<br>Vx,Ux/Mq|vpmovzxwq<br>Vx,Ux/Md|vpmovzxdq<br>Vx,Ux/Mq|vpermd<sup>v</sup><br>Vqq,Hqq,Wqq|vpcmpgtq<br>Vx,Hx,Wx|
|4<br>66|vpmulld<br>Vx,Hx,Wx|vphminposuw<br>Vdq,Wdq||||vpsrlvd/q<sup>v</sup><br>Vx,Hx,Wx|vpsravd<sup>v</sup><br>Vx,Hx,Wx|vpsllvd/q<sup>v</sup><br>Vx,Hx,Wx|
|5|||||||||
|6<br>7|||||||||
|8<br>66|INVEPT<br>Gy, Mdq|INVVPID<br>Gy, Mdq|INVPCID<br>Gy, Mdq||||||
|9<br>66|vgatherdd/q<sup>v</sup><br>Vx,Hx,Wx|vgatherqd/q<sup>v</sup><br>Vx,Hx,Wx|vgatherdps/d<sup>v</sup><br>Vx,Hx,Wx|vgatherqps/d<sup>v</sup><br>Vx,Hx,Wx|||vfmaddsub132ps/d<sup>v</sup><br>Vx,Hx,Wx|vfmsubadd132ps/d<sup>v</sup><br>Vx,Hx,Wx|
|A<br>66|||||||vfmaddsub213ps/d<sup>v</sup><br>Vx,Hx,Wx|vfmsubadd213ps/d<sup>v</sup><br>Vx,Hx,Wx|
|B<br>66<br>C|||||||vfmaddsub231ps/d<sup>v</sup><br>Vx,Hx,Wx|vfmsubadd231ps/d<sup>v</sup><br>Vx,Hx,Wx|
|D<br>|||||||||
|E|MOVBE<br>Gy,My|MOVBE<br>My,Gy|ANDN<sup>v</sup><br>Gy,By,Ey|||BZHI<sup>v</sup><br>Gy,Ey,By||BEXTR<sup>v</sup><br>Gy,Ey,By|
|66|MOVBE<br>Gw,Mw|MOVBE<br>Mw,Gw|||||ADCX<br>Gy,Ey|SHLX<sup>v</sup><br>Gy,Ey,By|
|F<br>F3||||Grp 17<sup>1A</sup>||PEXT<sup>v</sup><br>Gy,By,Ey|ADOX<br>Gy,Ey|SARX<sup>v</sup><br>Gy,Ey,By|
|F2|CRC32<br>Gd,Eb|CRC32<br>Gd,Ey||||PDEP<sup>v</sup><br>Gy,By,Ey|MULX<sup>v</sup><br>By,Gy,rDX,Ey|SHRX<sup>v</sup><br>Gy,Ey,By|
|66 &<br>F2|CRC32<br>Gd,Eb|CRC32<br>Gd,Ew|||||||



Vol. 2D A-13

OPCODE MAP

Table A-4. Three-byte Opcode Map: 08H — FFH (First Two Bytes are 0F 38H) *

||pfx|8|9|A|B|C|D|E|F|
|---|---|---|---|---|---|---|---|---|---|
|||psignb<br>Pq,Qq|psignw<br>Pq,Qq|psignd<br>Pq,Qq|pmulhrsw<br>Pq,Qq|||||
|0|66|vpsignb<br>Vx, Hx, Wx|vpsignw<br>Vx, Hx, Wx|vpsignd<br>Vx, Hx, Wx|vpmulhrsw<br>Vx, Hx, Wx|vpermilps<sup>v</sup><br>Vx,Hx,Wx|vpermilpd<sup>v</sup><br>Vx,Hx,Wx|vtestps<sup>v</sup><br>Vx, Wx|vtestpd<sup>v</sup><br>Vx, Wx|
|1||||||pabsb<br>Pq,Qq|pabsw<br>Pq,Qq|pabsd<br>Pq,Qq||
||66|vbroadcastss<sup>v</sup><br>Vx,Wd|vbroadcastsd<sup>v</sup>Vqq,<br>Wq<br>|vbroadcastf128<sup>v</sup>Vqq,<br>Mdq||vpabsb<br>Vx,Wx|vpabsw<br>Vx,Wx|vpabsd<br>Vx,Wx||
|2|66|vpmuldq<br>Vx,Hx,Wx|vpcmpeqq<br>Vx,Hx,Wx|vmovntdqa<br>Vx, Mx|vpackusdw<br>Vx,Hx,Wx|vmaskmovps<sup>v</sup><br>Vx,Hx,Mx|vmaskmovpd<sup>v</sup><br>Vx,Hx,Mx|vmaskmovps<sup>v</sup><br>Mx,Hx,Vx|vmaskmovpd<sup>v</sup><br>Mx,Hx,Vx|
|3|66|vpminsb<br>Vx,Hx,Wx|vpminsd<br>Vx,Hx,Wx|vpminuw<br>Vx, Hx, Wx|vpminud<br>Vx,Hx,Wx|vpmaxsb<br>Vx,Hx,Wx|vpmaxsd<br>Vx,Hx,Wx|vpmaxuw<br>Vx,Hx,Wx|vpmaxud<br>Vx,Hx,Wx|
|4||||||||||
|5<br>|66|vpbroadcastd<sup>v</sup><br>Vx,Wx|vpbroadcastq<sup>v</sup><br>Vx,Wx|vbroadcasti128<sup>v</sup><br>Vqq, Mdq||||||
|6<br>7|66|vpbroadcastb<sup>v</sup><br>Vx,Wx|vpbroadcastw<sup>v</sup><br>Vx,Wx|||||||
|8|66|||||vpmaskmovd/q<sup>v</sup><br>Vx,Hx,Mx||vpmaskmovd/q<sup>v</sup><br>Mx,Vx,Hx||
|9|66|vfmadd132ps/d<sup>v</sup><br>Vx,Hx,Wx|vfmadd132ss/d<sup>v</sup><br>Vx,Hx,Wx|vfmsub132ps/d<sup>v</sup><br>Vx,Hx,Wx|vfmsub132ss/d<sup>v</sup><br>Vx,Hx,Wx|vfnmadd132ps/d<sup>v</sup><br>Vx,Hx,Wx|vfnmadd132ss/d<sup>v</sup><br>Vx,Hx,Wx|vfnmsub132ps/d<sup>v</sup><br>Vx,Hx,Wx|vfnmsub132ss/d<sup>v</sup><br>Vx,Hx,Wx|
|A|66|vfmadd213ps/d<sup>v</sup><br>Vx,Hx,Wx|vfmadd213ss/d<sup>v</sup><br>Vx,Hx,Wx|vfmsub213ps/d<sup>v</sup><br>Vx,Hx,Wx|vfmsub213ss/d<sup>v</sup><br>Vx,Hx,Wx|vfnmadd213ps/d<sup>v</sup><br>Vx,Hx,Wx|vfnmadd213ss/d<sup>v</sup><br>Vx,Hx,Wx|vfnmsub213ps/d<sup>v</sup><br>Vx,Hx,Wx|vfnmsub213ss/d<sup>v</sup><br>Vx,Hx,Wx|
|B|66|vfmadd231ps/d<sup>v</sup><br>Vx,Hx,Wx|vfmadd231ss/d<sup>v</sup><br>Vx,Hx,Wx|vfmsub231ps/d<sup>v</sup><br>Vx,Hx,Wx|vfmsub231ss/d<sup>v</sup><br>Vx,Hx,Wx|vfnmadd231ps/d<sup>v</sup><br>Vx,Hx,Wx|vfnmadd231ss/d<sup>v</sup><br>Vx,Hx,Wx|vfnmsub231ps/d<sup>v</sup><br>Vx,Hx,Wx|vfnmsub231ss/d<sup>v</sup><br>Vx,Hx,Wx|
|C||sha1nexte<br>Vdq,Wdq|sha1msg1<br>Vdq,Wdq|sha1msg2<br>Vdq,Wdq|sha256rnds2<br>Vdq,Wdq|sha256msg1<br>Vdq,Wdq|sha256msg2<br>Vdq,Wdq|||
||66|||||||||
|D<br>E|66||||VAESIMC<br>Vdq,Wdq|VAESENC<br>Vdq,Hdq,Wdq|VAESENCLAST<br>Vdq,Hdq,Wdq|VAESDEC<br>Vdq,Hdq,Wdq|VAESDECLAST<br>Vdq,Hdq,Wdq|
||66|||||||||
|F|F3|||||||||
||F2<br>66 & F2|||||||||



NOTES:

* All blanks in all opcode maps are reserved and must not be used. Do not depend on the operation of undefined or reserved locations.

A-14 Vol. 2D

OPCODE MAP

Table A-5.  Three-byte Opcode Map: 00H — F7H (First two bytes are 0F 3AH) *

|pfx|0|1|2|3|4|5|6|7|
|---|---|---|---|---|---|---|---|---|
|0<br>66|vpermq<sup>v</sup><br>Vqq, Wqq, Ib|vpermpd<sup>v</sup><br>Vqq, Wqq, Ib|vpblendd<sup>v</sup><br>Vx,Hx,Wx,Ib||vpermilps<sup>v</sup><br>Vx, Wx, Ib|vpermilpd<sup>v</sup><br>Vx, Wx, Ib|vperm2f128<sup>v</sup><br>Vqq,Hqq,Wqq,Ib||
|1<br>66|||||vpextrb<br>Rd/Mb,Vdq,Ib|vpextrw<br>Rd/Mw,Vdq,Ib|vpextrd/q<br>Ey,Vdq,Ib|vextractps<br>Ed,Vdq,Ib|
|2<br>66|vpinsrb<br>Vdq,Hdq,Ry/Mb,Ib|vinsertps<br>Vdq,Hdq,Udq/Md,Ib|vpinsrd/q<br>Vdq,Hdq,Ey,Ib||||||
|3|||||||||
|4<br>66|vdpps<br>Vx,Hx,Wx,Ib|vdppd<br>Vdq,Hdq,Wdq,Ib|vmpsadbw<br>Vx,Hx,Wx,Ib||vpclmulqdq<br>Vdq,Hdq,Wdq,Ib||vperm2i128<sup>v</sup><br>Vqq,Hqq,Wqq,Ib||
|5|||||||||
|6<br>66|vpcmpestrm<br>Vdq,Wdq,Ib|vpcmpestri<br>Vdq,Wdq,Ib|vpcmpistrm<br>Vdq,Wdq,Ib|vpcmpistri<br>Vdq,Wdq,Ib|||||
|7|||||||||
|8|||||||||
|9|||||||||
|A|||||||||
|B|||||||||
|C|||||||||
|D|||||||||
|E|||||||||
|F<br>F2|RORX<sup>v</sup><br>Gy,Ey,Ib||||||||



Vol. 2D A-15

OPCODE MAP

Table A-5. Three-byte Opcode Map: 08H — FFH (First Two Bytes are 0F 3AH) *

|pfx|8|9|A|B|C|D|E|F|
|---|---|---|---|---|---|---|---|---|
|0||||||||palignr<br>Pq,Qq,Ib|
|66|vroundps<br>Vx,Wx,Ib|vroundpd<br>Vx,Wx,Ib|vroundss<br>Vss,Wss,Ib|vroundsd<br>Vsd,Wsd,Ib|vblendps<br>Vx,Hx,Wx,Ib|vblendpd<br>Vx,Hx,Wx,Ib|vpblendw<br>Vx,Hx,Wx,Ib|vpalignr<br>Vx,Hx,Wx,Ib|
|1<br>66|vinsertf128<sup>v</sup><br>Vqq,Hqq,Wqq,Ib|vextractf128<sup>v</sup><br>Wdq,Vqq,Ib||||vcvtps2ph<sup>v</sup><br>Wx, Vx, Ib|||
|2|||||||||
|3<br>66|vinserti128<sup>v</sup><br>Vqq,Hqq,Wqq,Ib|vextracti128<sup>v</sup><br>Wdq,Vqq,Ib|||||||
|4<br>66|||vblendvps<sup>v</sup><br>Vx,Hx,Wx,Lx|vblendvpd<sup>v</sup><br>Vx,Hx,Wx,Lx|vpblendvb<sup>v</sup><br>Vx,Hx,Wx,Lx||||
|5|||||||||
|6|||||||||
|7|||||||||
|8|||||||||
|9|||||||||
|A|||||||||
|B|||||||||
|C|||||sha1rnds4<br>Vdq,Wdq,Ib||||
|D<br>66<br>E<br>F||||||||VAESKEYGEN<br>Vdq,Wdq,Ib|



NOTES:

* All blanks in all opcode maps are reserved and must not be used. Do not depend on the operation of undefined or reserved locations.

A-16 Vol. 2D

OPCODE MAP

# A.4 OPCODE EXTENSIONS FOR ONE-BYTE AND TWO-BYTE OPCODES

Some 1-byte and 2-byte opcodes use bits 3-5 of the ModR/M byte (the nnn field in Figure A-1) as an extension of the opcode.

|mod||nnn||R/M|
|---|---|---|---|---|
||Figure|A-1.  ModR/M Byte nnn Field (Bits 5, 4|, and 3)||



Opcodes that have opcode extensions are indicated in Table A-6 and organized by group number. Group numbers (from 1 to 16, second column) provide a table entry point. The encoding for the r/m field for each instruction can be established using the third column of the table.

## A.4.1 Opcode Look-up Examples Using Opcode Extensions

An Example is provided below.

Example A-4.  Interpreting an ADD Instruction

An ADD instruction with a 1-byte opcode of 80H is a Group 1 instruction:

- Table A-6 indicates that the opcode extension field encoded in the ModR/M byte for this instruction is 000B.

- • The r/m field can be encoded to access a register (11B) or a memory address using a specified addressing mode (for example: mem = 00B, 01B, 10B).

##### Example A-5.  Looking Up 0F01C3H

Look up opcode 0F01C3 for a VMRESUME instruction by using Table A-2, Table A-3, and Table A-6:

- 0F indicates that this instruction is in the 2-byte opcode map.

- 01 (row 0, column 1 in Table A-3) reveals that this opcode is in Group 7 of Table A-6.

- C3 is the ModR/M byte. The first two bits of C3 are 11B. This tells us to look at the second of the Group 7 rows in Table A-6.

- The Op/Reg bits [5,4,3] are 000B. This tells us to look in the 000 column for Group 7.

- Finally, the R/M bits [2,1,0] are 011B. This identifies the opcode as the VMRESUME instruction.

## A.4.2 Opcode Extension Tables

See Table A-6 below.

Vol. 2D A-17

OPCODE MAP

Table A-6.  Opcode Extensions for One- and Two-byte Opcodes by Group Number *

||||||Encoding of|Bits 5,4,3 o|f the ModR/|M Byte (bit|s 2,1,0 in|parenthes|is)|
|---|---|---|---|---|---|---|---|---|---|---|---|
|Opcode|Group|Mod 7,6|pfx|000|001|010|011|100|101|110|111|
|80-83|1|mem, 11B||ADD|OR|ADC|SBB|AND|SUB|XOR|CMP|
|8F|1A|mem, 11B||POP||||||||
|C0,C1 reg, imm<br>D0, D1 reg, 1<br>D2, D3 reg, CL|2|mem, 11B||ROL|ROR|RCL|RCR|SHL/SAL|SHR||SAR|
|F6, F7|3|mem, 11B||TEST<br>Ib/Iz||NOT|NEG|MUL<br>AL/rAX|IMUL<br>AL/rAX|DIV<br>AL/rAX|IDIV<br>AL/rAX|
|FE|4|mem, 11B||INC<br>Eb|DEC<br>Eb|||||||
|FF|5|mem, 11B||INC<br>Ev|DEC<br>Ev|near CALL<sup>f64</sup><br>Ev|far CALL<br>Ep|near JMP<sup>f64</sup><br>Ev|far JMP<br>Mp|PUSH<sup>d64</sup><br>Ev||
|0F 00|6|mem, 11B||SLDT<br>Rv/Mw|STR<br>Rv/Mw|LLDT<br>Ew|LTR<br>Ew|VERR<br>Ew|VERW<br>Ew|||
|||mem||SGDT<br>Ms|SIDT<br>Ms|LGDT<br>Ms|LIDT<br>Ms|SMSW<br>Mw/Rv||LMSW<br>Ew|INVLPG<br>Mb|
|0F 01|7|11B||VMCALL (001)<br>VMLAUNCH<br>(010)<br>VMRESUME<br>(011) VMXOFF<br>(100)|<br> <br>MONITOR<br>(000)<br>MWAIT (001)<br>CLAC (010)<br>STAC (011)<br>ENCLS (111)|XGETBV (000)<br>XSETBV (001)<br>VMFUNC<br>(100)<br>XEND (101)<br>XTEST (110)<br>ENCLU(111)|||||SWAPGS<br>o64(000)<br>RDTSCP (001)|
|0F BA|8|mem, 11B||||||BT|BTS|BTR|BTC|
||||||CMPXCH8B Mq<br>CMPXCHG16B<br>Mdq|||||VMPTRLD<br>Mq|VMPTRST<br>Mq|
|||mem|66|||||||VMCLEAR<br>Mq||
|0F C7|9||F3|||||||VMXON<br>Mq||
|||11B||||||||RDRAND<br>Rv|RDSEED<br>Rv|
||||F3||||||||RDPID<br>Rd/q|
|0F B9|10|mem<br>11B|||||UD1|||||
|||mem||MOV||||||||
|C6|11|11B||Eb, Ib|||||||XABORT (000) Ib|
|C7||mem<br>11B||MOV<br>Ev, Iz|||||||XBEGIN (000) Jz|
|||mem||||||||||
|0F 71|12|11B||||psrlw<br>Nq, Ib||psraw<br>Nq, Ib||psllw<br>Nq, Ib||
||||66|||vpsrlw<br>Hx,Ux,Ib||vpsraw<br>Hx,Ux,Ib||vpsllw<br>Hx,Ux,Ib||
|||mem||||||||||
|0F 72|13|||||psrld<br>Nq, Ib||psrad<br>Nq, Ib||pslld<br>Nq, Ib||
|||11B|66|||vpsrld<br>Hx,Ux,Ib||vpsrad<br>Hx,Ux,Ib||vpslld<br>Hx,Ux,Ib||
|||mem||||||||||
|0F 73|14|11B||||psrlq<br>Nq, Ib||||psllq<br>Nq, Ib||
||||66|||vpsrlq<br>Hx,Ux,Ib|vpsrldq<br>Hx,Ux,Ib|||vpsllq<br>Hx,Ux,Ib|vpslldq<br>Hx,Ux,Ib|



A-18 Vol. 2D

OPCODE MAP

Table A-6.  Opcode Extensions for One- and Two-byte Opcodes by Group Number * (Contd.)

|Opcode|Group|Mod 7,6|pfx|<br>000|Encoding of<br>001|Bits 5,4,3<br>010|of the ModR/M<br>011|Byte (bit<br>100|s 2,1,0 in<br>101|parenthesis<br>110|)<br>111|
|---|---|---|---|---|---|---|---|---|---|---|---|
|||mem||fxsave|fxrstor|ldmxcsr|stmxcsr|XSAVE|XRSTOR|XSAVEOPT|clflush|
|0F AE|15||||||||lfence|mfence|sfence|
|||11B|F3|RDFSBASE<br>Ry|RDGSBASE<br>Ry|WRFSBASE<br>Ry|WRGSBASE<br>Ry|||||
|0F 18|16|mem||prefetch<br>NTA|prefetch<br>T0|prefetch<br>T1|prefetch<br>T2||Rese|rved NOP||
|VEX0F38 F3|17|11B<br>mem|||BLSR<sup>v</sup><br>|BLSMSK<sup>v</sup><br>|Reserved<br>BLSI<sup>v</sup><br>|NOP||||
|.||11B|||By, Ey|By, Ey|By, Ey|||||



NOTES:

* All blanks in all opcode maps are reserved and must not be used. Do not depend on the operation of undefined or reserved locations.

Vol. 2D A-19

OPCODE MAP

# A.5 ESCAPE OPCODE INSTRUCTIONS

Opcode maps for coprocessor escape instruction opcodes (x87 floating-point instruction opcodes) are in Table A-7 through Table A-22. These maps are grouped by the first byte of the opcode, from D8-DF. Each of these opcodes has a ModR/M byte. If the ModR/M byte is within the range of 00H-BFH, bits 3-5 of the ModR/M byte are used as an opcode extension, similar to the technique used for 1-and 2-byte opcodes (see A.4). If the ModR/M byte is outside the range of 00H through BFH, the entire ModR/M byte is used as an opcode extension.

## A.5.1 Opcode Look-up Examples for Escape Instruction Opcodes

Examples are provided below.

Example A-6.  Opcode with ModR/M Byte in the 00H through BFH Range

DD0504000000H can be interpreted as follows:

- The instruction encoded with this opcode can be located in Section . Since the ModR/M byte (05H) is within the 00H through BFH range, bits 3 through 5 (000) of this byte indicate the opcode for an FLD double-real instruction (see Table A-9).

- The double-real value to be loaded is at 00000004H (the 32-bit displacement that follows and belongs to this opcode).

Example A-7.  Opcode with ModR/M Byte outside the 00H through BFH Range

D8C1H can be interpreted as follows:

- This example illustrates an opcode with a ModR/M byte outside the range of 00H through BFH. The instruction can be located in Section A.4.

- In Table A-8, the ModR/M byte C1H indicates row C, column 1 (the FADD instruction using ST(0), ST(1) as operands).

## A.5.2 Escape Opcode Instruction Tables

Tables are listed below.

### A.5.2.1 Escape Opcodes with D8 as First Byte

Table A-7 and A-8 contain maps for the escape instruction opcodes that begin with D8H. Table A-7 shows the map if the ModR/M byte is in the range of 00H-BFH. Here, the value of bits 3-5 (the nnn field in Figure A-1) selects the instruction.

Table A-7.  D8 Opcode Map When ModR/M Byte is Within 00H to BFH *

|||nnn|Field of ModR/M By|te (refer to Figure|A.4)|||
|---|---|---|---|---|---|---|---|
|000B|001B|010B|011B|100B|101B|110B|111B|
|FADD|FMUL|FCOM|FCOMP|FSUB|FSUBR|FDIV|FDIVR|
|single-real|single-real|single-real|single-real|single-real|single-real|single-real|single-real|



NOTES:

* All blanks in all opcode maps are reserved and must not be used. Do not depend on the operation of undefined or reserved locations.

A-20 Vol. 2D

OPCODE MAP

Table A-8 shows the map if the ModR/M byte is outside the range of 00H-BFH. Here, the first digit of the ModR/M byte selects the table row and the second digit selects the column.

Table A-8.  D8 Opcode Map When ModR/M Byte is Outside 00H to BFH *

|0|1|2|3|4|5|6|7|
|---|---|---|---|---|---|---|---|
|C|||FA|DD||||
|ST(0),ST(0)|ST(0),ST(1)|ST(0),ST(2)|ST(0),ST(3)|ST(0),ST(4)|ST(0),ST(5)|ST(0),ST(6)|ST(0),ST(7)|
|D|||FC|OM||||
|ST(0),ST(0)|ST(0),ST(1)|ST(0),T(2)|ST(0),ST(3)|ST(0),ST(4)|ST(0),ST(5)|ST(0),ST(6)|ST(0),ST(7)|
|E|||FS|UB||||
|ST(0),ST(0)|ST(0),ST(1)|ST(0),ST(2)|ST(0),ST(3)|ST(0),ST(4)|ST(0),ST(5)|ST(0),ST(6)|ST(0),ST(7)|
|F|||FD|IV||||
|ST(0),ST(0)|ST(0),ST(1)|ST(0),ST(2)|ST(0),ST(3)|ST(0),ST(4)|ST(0),ST(5)|ST(0),ST(6)|ST(0),ST(7)|



|8|9|A|B|C|D|E|F|
|---|---|---|---|---|---|---|---|
|C|||FM|UL||||
|ST(0),ST(0)|ST(0),ST(1)|ST(0),ST(2)|ST(0),ST(3)|ST(0),ST(4)|ST(0),ST(5)|ST(0),ST(6)|ST(0),ST(7)|
|D|||FCO|MP||||
|ST(0),ST(0)|ST(0),ST(1)|ST(0),T(2)|ST(0),ST(3)|ST(0),ST(4)|ST(0),ST(5)|ST(0),ST(6)|ST(0),ST(7)|
|E|||FSU|BR||||
|ST(0),ST(0)|ST(0),ST(1)|ST(0),ST(2)|ST(0),ST(3)|ST(0),ST(4)|ST(0),ST(5)|ST(0),ST(6)|ST(0),ST(7)|
|F|||FDI|VR||||
|ST(0),ST(0)|ST(0),ST(1)|ST(0),ST(2)|ST(0),ST(3)|ST(0),ST(4)|ST(0),ST(5)|ST(0),ST(6)|ST(0),ST(7)|



NOTES:

* All blanks in all opcode maps are reserved and must not be used. Do not depend on the operation of undefined or reserved locations.

### A.5.2.2 Escape Opcodes with D9 as First Byte

Table A-9 and A-10 contain maps for escape instruction opcodes that begin with D9H. Table A-9 shows the map if the ModR/M byte is in the range of 00H-BFH. Here, the value of bits 3-5 (the nnn field in Figure A-1) selects the instruction.

Table A-9.  D9 Opcode Map When ModR/M Byte is Within 00H to BFH *

||||nnn Field of|ModR/M Byte||||
|---|---|---|---|---|---|---|---|
|000B|001B|010B|011B|100B|101B|110B|111B|
|FLD||FST|FSTP|FLDENV|FLDCW|FSTENV|FSTCW|
|single-real||single-real|single-real|14/28 bytes|2 bytes|14/28 bytes|2 bytes|



NOTES:

* All blanks in all opcode maps are reserved and must not be used. Do not depend on the operation of undefined or reserved locations.

Vol. 2D A-21

OPCODE MAP

Table A-10 shows the map if the ModR/M byte is outside the range of 00H-BFH. Here, the first digit of the ModR/M byte selects the table row and the second digit selects the column.

Table A-10.  D9 Opcode Map When ModR/M Byte is Outside 00H to BFH *

|0|1|2|3|4|5|6|7|
|---|---|---|---|---|---|---|---|
|C|||FL|D||||
|ST(0),ST(0)|ST(0),ST(1)|ST(0),ST(2)|ST(0),ST(3)|ST(0),ST(4)|ST(0),ST(5)|ST(0),ST(6)|ST(0),ST(7)|
|D<br>FNOP||||||||
|E<br>FCHS|FABS|||FTST|FXAM|||
|F<br>F2XM1|FYL2X|FPTAN|FPATAN|FXTRACT|FPREM1|FDECSTP|FINCSTP|
|8|9|A|B|C|D|E|F|
|C|||FXC|H||||
|ST(0),ST(0)|ST(0),ST(1)|ST(0),ST(2)|ST(0),ST(3)|ST(0),ST(4)|ST(0),ST(5)|ST(0),ST(6)|ST(0),ST(7)|
|D||||||||
|E<br>FLD1|FLDL2T|FLDL2E|FLDPI|FLDLG2|FLDLN2|FLDZ||
|F<br>FPREM|FYL2XP1|FSQRT|FSINCOS|FRNDINT|FSCALE|FSIN|FCOS|



NOTES:

* All blanks in all opcode maps are reserved and must not be used. Do not depend on the operation of undefined or reserved locations.

### A.5.2.3 Escape Opcodes with DA as First Byte

Table A-11 and A-12 contain maps for escape instruction opcodes that begin with DAH. Table A-11 shows the map if the ModR/M byte is in the range of 00H-BFH. Here, the value of bits 3-5 (the nnn field in Figure A-1) selects the instruction.

Table A-11.  DA Opcode Map When ModR/M Byte is Within 00H to BFH *

||||nnn Field of|ModR/M Byte||||
|---|---|---|---|---|---|---|---|
|000B|001B|010B|011B|100B|101B|110B|111B|
|FIADD|FIMUL|FICOM|FICOMP|FISUB|FISUBR|FIDIV|FIDIVR|
|dword-integer|dword-integer|dword-integer|dword-integer|dword-integer|dword-integer|dword-integer|dword-integer|



**NOTES:**

* All blanks in all opcode maps are reserved and must not be used. Do not depend on the operation of undefined or reserved locations.

A-22 Vol. 2D

OPCODE MAP

Table A-12 shows the map if the ModR/M byte is outside the range of 00H-BFH. Here, the first digit of the ModR/M byte selects the table row and the second digit selects the column.

Table A-12.  DA Opcode Map When ModR/M Byte is Outside 00H to BFH *

|0|1|2|3|4|5|6|7|
|---|---|---|---|---|---|---|---|
|C|||FCM|OVB||||
|ST(0),ST(0)|ST(0),ST(1)|ST(0),ST(2)|ST(0),ST(3)|ST(0),ST(4)|ST(0),ST(5)|ST(0),ST(6)|ST(0),ST(7)|
|D|||FCMO|VBE||||
|ST(0),ST(0)|ST(0),ST(1)|ST(0),ST(2)|ST(0),ST(3)|ST(0),ST(4)|ST(0),ST(5)|ST(0),ST(6)|ST(0),ST(7)|
|E||||||||
|F||||||||



|8|9|A|B|C|D|E|F|
|---|---|---|---|---|---|---|---|
|C|||FCM|OVE||||
|ST(0),ST(0)|ST(0),ST(1)|ST(0),ST(2)|ST(0),ST(3)|ST(0),ST(4)|ST(0),ST(5)|ST(0),ST(6)|ST(0),ST(7)|
|D|||FCM|OVU||||
|ST(0),ST(0)|ST(0),ST(1)|ST(0),ST(2)|ST(0),ST(3)|ST(0),ST(4)|ST(0),ST(5)|ST(0),ST(6)|ST(0),ST(7)|
|E|FUCOMPP|||||||
|F||||||||



NOTES:

* All blanks in all opcode maps are reserved and must not be used. Do not depend on the operation of undefined or reserved locations.

### A.5.2.4 Escape Opcodes with DB as First Byte

Table A-13 and A-14 contain maps for escape instruction opcodes that begin with DBH. Table A-13 shows the map if the ModR/M byte is in the range of 00H-BFH. Here, the value of bits 3-5 (the nnn field in Figure A-1) selects the instruction.

Table A-13.  DB Opcode Map When ModR/M Byte is Within 00H to BFH *

||||nnn Field of M|odR/M Byte||||
|---|---|---|---|---|---|---|---|
|000B|001B|010B|011B|100B|101B|110B|111B|
|FILD|FISTTP|FIST|FISTP||FLD||FSTP|
|dword-integer|dword-integer|dword-integer|dword-integer||extended-real||extended-real|



NOTES:

* All blanks in all opcode maps are reserved and must not be used. Do not depend on the operation of undefined or reserved locations.

Vol. 2D A-23

OPCODE MAP

Table A-14 shows the map if the ModR/M byte is outside the range of 00H-BFH. Here, the first digit of the ModR/M byte selects the table row and the second digit selects the column.

Table A-14.  DB Opcode Map When ModR/M Byte is Outside 00H to BFH *

|0<br>C<br>|1<br>|2<br>|3<br>FCM<br>|4<br>OVNB<br>|5<br>|6<br>|7<br>|
|---|---|---|---|---|---|---|---|
|ST(0),ST(0)|ST(0),ST(1)|ST(0),ST(2)|ST(0),ST(3)|ST(0),ST(4)|ST(0),ST(5)|ST(0),ST(6)|ST(0),ST(7)|
|D<br>|||FCMO<br>|VNBE<br>||||
|ST(0),ST(0)|ST(0),ST(1)|ST(0),ST(2)|ST(0),ST(3)|ST(0),ST(4)|ST(0),ST(5)|ST(0),ST(6)|ST(0),ST(7)|
|E<br>F<br>||FCLEX<br>|FINIT<br>FC<br>|OMI<br>||||
|ST(0),ST(0)|ST(0),ST(1)|ST(0),ST(2)|ST(0),ST(3)|ST(0),ST(4)|ST(0),ST(5)|ST(0),ST(6)|ST(0),ST(7)|
|8|9|A|B|C|D|E|F|
|C<br>|||FCM<br>|OVNE<br>||||
|ST(0),ST(0)|ST(0),ST(1)|ST(0),ST(2)|ST(0),ST(3)|ST(0),ST(4)|ST(0),ST(5)|ST(0),ST(6)|ST(0),ST(7)|
|D<br>|||FCM<br>|OVNU<br>||||
|ST(0),ST(0)|ST(0),ST(1)|ST(0),ST(2)|ST(0),ST(3)|ST(0),ST(4)|ST(0),ST(5)|ST(0),ST(6)|ST(0),ST(7)|
|E<br>|||FUC<br>|OMI<br>||||
|ST(0),ST(0)<br>F|ST(0),ST(1)|ST(0),ST(2)|ST(0),ST(3)|ST(0),ST(4)|ST(0),ST(5)|ST(0),ST(6)|ST(0),ST(7)|



NOTES:

* All blanks in all opcode maps are reserved and must not be used. Do not depend on the operation of undefined or reserved locations.

### A.5.2.5 Escape Opcodes with DC as First Byte

Table A-15 and A-16 contain maps for escape instruction opcodes that begin with DCH. Table A-15 shows the map if the ModR/M byte is in the range of 00H-BFH. Here, the value of bits 3-5 (the nnn field in Figure A-1) selects the instruction.

Table A-15.  DC Opcode Map When ModR/M Byte is Within 00H to BFH *

|||nnn F|ield of ModR/M B|yte (refer to Figure|A-1)|||
|---|---|---|---|---|---|---|---|
|000B|001B|010B|011B|100B|101B|110B|111B|
|FADD|FMUL|FCOM|FCOMP|FSUB|FSUBR|FDIV|FDIVR|
|double-real|double-real|double-real|double-real|double-real|double-real|double-real|double-real|



NOTES:

* All blanks in all opcode maps are reserved and must not be used. Do not depend on the operation of undefined or reserved locations.

A-24 Vol. 2D

OPCODE MAP

Table A-16 shows the map if the ModR/M byte is outside the range of 00H-BFH. In this case the first digit of the ModR/M byte selects the table row and the second digit selects the column.

Table A-16.  DC Opcode Map When ModR/M Byte is Outside 00H to BFH *

|0|1|2|3|4|5|6|7|
|---|---|---|---|---|---|---|---|
|C|||FA|DD||||
|ST(0),ST(0)|ST(1),ST(0)|ST(2),ST(0)|ST(3),ST(0)|ST(4),ST(0)|ST(5),ST(0)|ST(6),ST(0)|ST(7),ST(0)|
|D||||||||
|E|||FS|UBR||||
|ST(0),ST(0)|ST(1),ST(0)|ST(2),ST(0)|ST(3),ST(0)|ST(4),ST(0)|ST(5),ST(0)|ST(6),ST(0)|ST(7),ST(0)|
|F|||FD|IVR||||
|ST(0),ST(0)|ST(1),ST(0)|ST(2),ST(0)|ST(3),ST(0)|ST(4),ST(0)|ST(5),ST(0)|ST(6),ST(0)|ST(7),ST(0)|
|8|9|A|B|C|D|E|F|
|C|||FM|UL||||
|ST(0),ST(0)|ST(1),ST(0)|ST(2),ST(0)|ST(3),ST(0)|ST(4),ST(0)|ST(5),ST(0)|ST(6),ST(0)|ST(7),ST(0)|
|D||||||||
|E|||FS|UB||||
|ST(0),ST(0)|ST(1),ST(0)|ST(2),ST(0)|ST(3),ST(0)|ST(4),ST(0)|ST(5),ST(0)|ST(6),ST(0)|ST(7),ST(0)|
|F|||F|DIV||||
|ST(0),ST(0)|ST(1),ST(0)|ST(2),ST(0)|ST(3),ST(0)|ST(4),ST(0)|ST(5),ST(0)|ST(6),ST(0)|ST(7),ST(0)|



NOTES:

***** All blanks in all opcode maps are reserved and must not be used. Do not depend on the operation of undefined or reserved locations.

### A.5.2.6 Escape Opcodes with DD as First Byte

Table A-17 and A-18 contain maps for escape instruction opcodes that begin with DDH. Table A-17 shows the map if the ModR/M byte is in the range of 00H-BFH. Here, the value of bits 3-5 (the nnn field in Figure A-1) selects the instruction.

Table A-17.  DD Opcode Map When ModR/M Byte is Within 00H to BFH<sup>*</sup>

||||nnn Field of|ModR/M Byte||||
|---|---|---|---|---|---|---|---|
|000B|001B|010B|011B|100B|101B|110B|111B|
|FLD|FISTTP|FST|FSTP|FRSTOR||FSAVE|FSTSW|
|double-real|integer64|double-real|double-real|98/108bytes||98/108bytes|2 bytes|



NOTES:

* All blanks in all opcode maps are reserved and must not be used. Do not depend on the operation of undefined or reserved locations.

Vol. 2D A-25

OPCODE MAP

Table A-18 shows the map if the ModR/M byte is outside the range of 00H-BFH. The first digit of the ModR/M byte selects the table row and the second digit selects the column.

Table A-18.  DD Opcode Map When ModR/M Byte is Outside 00H to BFH *

|0<br>C|1|2|3<br>FF|4<br>REE|5|6|7|
|---|---|---|---|---|---|---|---|
|ST(0)|ST(1)|ST(2)|ST(3)|ST(4)|ST(5)|ST(6)|ST(7)|
|D|||F|ST||||
|ST(0)|ST(1)|ST(2)|ST(3)|ST(4)|ST(5)|ST(6)|ST(7)|
|E|||FUC|OM||||
|ST(0),ST(0)|ST(1),ST(0)|ST(2),ST(0)|ST(3),ST(0)|ST(4),ST(0)|ST(5),ST(0)|ST(6),ST(0)|ST(7),ST(0)|
|F||||||||
|8|9|A|B|C|D|E|F|
|C||||||||
|D|||FS|TP||||
|ST(0)|ST(1)|ST(2)|ST(3)|ST(4)|ST(5)|ST(6)|ST(7)|
|E<br>|||FUC<br>|OMP<br>||||
|ST(0)<br>F|ST(1)|ST(2)|ST(3)|ST(4)|ST(5)|ST(6)|ST(7)|



NOTES:

* All blanks in all opcode maps are reserved and must not be used. Do not depend on the operation of undefined or reserved locations.

### A.5.2.7 Escape Opcodes with DE as First Byte

Table A-19 and A-20 contain opcode maps for escape instruction opcodes that begin with DEH. Table A-19 shows the opcode map if the ModR/M byte is in the range of 00H-BFH. In this case, the value of bits 3-5 (the nnn field in Figure A-1) selects the instruction.

Table A-19.  DE Opcode Map When ModR/M Byte is Within 00H to BFH *

||||nnn Field of|ModR/M Byte||||
|---|---|---|---|---|---|---|---|
|000B|001B|010B|011B|100B|101B|110B|111B|
|FIADD|FIMUL|FICOM|FICOMP|FISUB|FISUBR|FIDIV|FIDIVR|
|word-integer|word-integer|word-integer|word-integer|word-integer|word-integer|word-integer|word-integer|



NOTES:

* All blanks in all opcode maps are reserved and must not be used. Do not depend on the operation of undefined or reserved locations.

A-26 Vol. 2D

OPCODE MAP

Table A-20 shows the opcode map if the ModR/M byte is outside the range of 00H-BFH. The first digit of the ModR/M byte selects the table row and the second digit selects the column.

Table A-20.  DE Opcode Map When ModR/M Byte is Outside 00H to BFH *

|0|1|2|3|4|5|6|7|
|---|---|---|---|---|---|---|---|
|C|||FA|DDP||||
|ST(0),ST(0)|ST(1),ST(0)|ST(2),ST(0)|ST(3),ST(0)|ST(4),ST(0)|ST(5),ST(0)|ST(6),ST(0)|ST(7),ST(0)|
|D<br>E|||FSU|BRP||||
|ST(0),ST(0)|ST(1),ST(0)|ST(2),ST(0)|ST(3),ST(0)|ST(4),ST(0)|ST(5),ST(0)|ST(6),ST(0)|ST(7),ST(0)|
|F|||FDI|VRP||||
|ST(0),ST(0)|ST(1),ST(0)|ST(2),ST(0)|ST(3),ST(0)|ST(4),ST(0)|ST(5),ST(0)|ST(6),ST(0)|ST(7),ST(0)|
|8|9|A|B|C|D|E|F|
|C|||FM|ULP||||
|ST(0),ST(0)|ST(1),ST(0)|ST(2),ST(0)|ST(3),ST(0)|ST(4),ST(0)|ST(5),ST(0)|ST(6),ST(0)|ST(7),ST(0)|
|D|FCOMPP|||||||
|E|||FS|UBP||||
|ST(0),ST(0)|ST(1),ST(0)|ST(2),ST(0)|ST(3),ST(0)|ST(4),ST(0)|ST(5),ST(0)|ST(6),ST(0)|ST(7),ST(0)|
|F|||FD|IVP||||
|ST(0),ST(0)|ST(1),ST(0)|ST(2),ST(0).|ST(3),ST(0)|ST(4),ST(0)|ST(5),ST(0)|ST(6),ST(0)|ST(7),ST(0)|



NOTES:

* All blanks in all opcode maps are reserved and must not be used. Do not depend on the operation of undefined or reserved locations.

### A.5.2.8 Escape Opcodes with DF As First Byte

Table A-21 and A-22 contain the opcode maps for escape instruction opcodes that begin with DFH. Table A-21 shows the opcode map if the ModR/M byte is in the range of 00H-BFH. Here, the value of bits 3-5 (the nnn field in Figure A-1) selects the instruction.

Table A-21.  DF Opcode Map When ModR/M Byte is Within 00H to BFH *

||||nnn Field of|ModR/M Byte||||
|---|---|---|---|---|---|---|---|
|000B|001B|010B|011B|100B|101B|110B|111B|
|FILD|FISTTP|FIST|FISTP|FBLD|FILD|FBSTP|FISTP|
|word-integer|word-integer|word-integer|word-integer|packed-BCD|qword-integer|packed-BCD|qword-integer|



NOTES:

* All blanks in all opcode maps are reserved and must not be used. Do not depend on the operation of undefined or reserved locations.

Vol. 2D A-27

OPCODE MAP

Table A-22 shows the opcode map if the ModR/M byte is outside the range of 00H-BFH. The first digit of the ModR/M byte selects the table row and the second digit selects the column.

Table A-22.  DF Opcode Map When ModR/M Byte is Outside 00H to BFH<sup>*</sup>

|C<br>D|0|1|2|3|4|5|6|7|
|---|---|---|---|---|---|---|---|---|
|E<br>F|FSTSW<br>AX<br>|||FCO<br>|MIP<br>||||
||ST(0),ST(0)|ST(0),ST(1)|ST(0),ST(2)|ST(0),ST(3)|ST(0),ST(4)|ST(0),ST(5)|ST(0),ST(6)|ST(0),ST(7)|
||8|9|A|B|C|D|E|F|
|C|||||||||
|D<br>E||||FUCO<br>|MIP<br>||||
|F|ST(0),ST(0)|ST(0),ST(1)|ST(0),ST(2)|ST(0),ST(3)|ST(0),ST(4)|ST(0),ST(5)|ST(0),ST(6)|ST(0),ST(7)|



NOTES:

* All blanks in all opcode maps are reserved and must not be used. Do not depend on the operation of undefined or reserved locations.

A-28 Vol. 2D

OPCODE MAP

Vol. 2D A-29

OPCODE MAP

A-30 Vol. 2D
