---
name: docs-md-x86-02-chapter-2-instruction-format
description: "Intel SDM Vol. 2: Chapter 2 Instruction Format (vendor documentation for x86 AVX2, AVX-512 and AVX-512 FP16)."
when: "when you need Intel SDM Vol. 2: Chapter 2 Instruction Format while writing a kernel for x86 AVX2, AVX-512 and AVX-512 FP16."
---

CHAPTER 2 INSTRUCTION FORMAT

This chapter describes the instruction format for all Intel 64 and IA-32 processors. The instruction format for protected mode, real-address mode and virtual-8086 mode is described in Section 2.1. Increments provided for IA32e mode and its sub-modes are described in Section 2.2.

# 2.1 INSTRUCTION FORMAT FOR PROTECTED MODE, REAL-ADDRESS MODE, AND VIRTUAL-8086 MODE

The Intel 64 and IA-32 architectures instruction encodings are subsets of the format shown in Figure 2-1. Instructions consist of optional instruction prefixes (in any order), primary opcode bytes (up to three bytes), an addressing-form specifier (if required) consisting of the ModR/M byte and sometimes the SIB (Scale-Index-Base) byte, a displacement (if required), and an immediate data field (if required).



<!-- Start of picture text -->
Instruction<br>Prefixes Opcode ModR/M SIB Displacement Immediate<br>Prefixes of 1-, 2-, or 3-byte 1 byte 1 byte Address Immediate<br>1 byte each opcode (if required) (if required) displacement data of<br>(optional) 1, 2 of 1, 2, or 4 1, 2, or 4<br>bytes or none 3 bytes or none 3<br>7 6 5 3 2 0 7 6 5 3 2 0<br>Mod Reg/ R/M Scale Index Base<br>Opcode<br>1. The REX prefix is optional, but if used must be immediately before the opcode; see Section<br>2.2.1, “REX Prefixes” for additional information.<br>2. For VEX encoding information, see Section 2.3, “Intel® Advanced Vector Extensions (Intel®<br>AVX)”.<br>3. Some rare instructions can take an 8B immediate or 8B displacement.<br><!-- End of picture text -->

Figure 2-1.  Intel 64 and IA-32 Architectures Instruction Format

## 2.1.1 Instruction Prefixes

Instruction prefixes are divided into four groups, each with a set of allowable prefix codes. For each instruction, it is only useful to include up to one prefix code from each of the four groups (Groups 1, 2, 3, 4). Groups 1 through 4 may be placed in any order relative to each other.

- Group 1

   - Lock and repeat prefixes:

      - LOCK prefix is encoded using F0H.

      - REPNE/REPNZ prefix is encoded using F2H. Repeat-Not-Zero prefix applies only to string and input/output instructions. (F2H is also used as a mandatory prefix for some instructions.)

      - REP or REPE/REPZ is encoded using F3H. The repeat prefix applies only to string and input/output instructions. (F3H is also used as a mandatory prefix for some instructions.)

Vol. 2A 2-1

INSTRUCTION FORMAT

   - BND prefix is encoded using F2H if the following conditions are true:

      - CPUID.(EAX=07H, ECX=0):EBX.MPX[bit 14] is set.

      - BNDCFGU.EN and/or IA32_BNDCFGS.EN is set.

      - When the F2 prefix precedes a near CALL, a near RET, a near JMP, a short Jcc, or a near Jcc instruction (see Appendix E, “Intel® Memory Protection Extensions,” of the _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ ).

- Group 2

   - Segment override prefixes:

      - 2EH—CS segment override (use with any branch instruction is reserved).

      - 36H—SS segment override prefix (use with any branch instruction is reserved).

      - 3EH—DS segment override prefix (use with any branch instruction is reserved).

      - 26H—ES segment override prefix (use with any branch instruction is reserved).

      - 64H—FS segment override prefix (use with any branch instruction is reserved).

      - 65H—GS segment override prefix (use with any branch instruction is reserved).

   - Branch hints<sup>1</sup> :

      - 2EH—Branch not taken (used only with J _cc_ instructions).

      - 3EH—Branch taken (used only with J _cc_ instructions).

- Group 3

      - Operand-size override prefix is encoded using 66H (66H is also used as a mandatory prefix for some instructions).

- Group 4

      - 67H—Address-size override prefix.

The LOCK prefix (F0H) forces an operation that ensures exclusive use of shared memory in a multiprocessor environment. See “LOCK—Assert LOCK# Signal Prefix” in Chapter 3, “Instruction Set Reference, A-L,” for a description of this prefix.

Repeat prefixes (F2H, F3H) cause an instruction to be repeated for each element of a string. Use these prefixes only with string and I/O instructions (MOVS, CMPS, SCAS, LODS, STOS, INS, and OUTS). Use of repeat prefixes and/or undefined opcodes with other Intel 64 or IA-32 instructions is reserved; such use may cause unpredictable behavior.

Some instructions may use F2H,F3H as a mandatory prefix to express distinct functionality.

Branch hint prefixes (2EH, 3EH) allow a program to give a hint to the processor about the most likely code path for a branch. Use these prefixes only with conditional branch instructions (J _cc_ ). Other use of branch hint prefixes and/or other undefined opcodes with Intel 64 or IA-32 instructions is reserved; such use may cause unpredictable behavior.

The operand-size override prefix allows a program to switch between 16- and 32-bit operand sizes. Either size can be the default; use of the prefix selects the non-default size.

Some SSE2/SSE3/SSSE3/SSE4 instructions and instructions using a three-byte sequence of primary opcode bytes may use 66H as a mandatory prefix to express distinct functionality.

Other use of the 66H prefix is reserved; such use may cause unpredictable behavior.

The address-size override prefix (67H) allows programs to switch between 16- and 32-bit addressing. Either size can be the default; the prefix selects the non-default size. Using this prefix and/or other undefined opcodes when operands for the instruction do not reside in memory is reserved; such use may cause unpredictable behavior.

1. Some earlier microarchitectures used these as branch hints, but recent generations have not and they are reserved for future hint usage.

2-2 Vol. 2A

INSTRUCTION FORMAT

## 2.1.2 Opcodes

A primary opcode can be 1, 2, or 3 bytes in length. An additional 3-bit opcode field is sometimes encoded in the ModR/M byte. Smaller fields can be defined within the primary opcode. Such fields define the direction of operation, size of displacements, register encoding, condition codes, or sign extension. Encoding fields used by an opcode vary depending on the class of operation.

Two-byte opcode formats for general-purpose and SIMD instructions consist of one of the following:

- An escape opcode byte 0FH as the primary opcode and a second opcode byte.

- A mandatory prefix (66H, F2H, or F3H), an escape opcode byte, and a second opcode byte (same as previous bullet).

For example, CVTDQ2PD consists of the following sequence: F3 0F E6. The first byte is a mandatory prefix (it is not considered as a repeat prefix).

Three-byte opcode formats for general-purpose and SIMD instructions consist of one of the following:

- An escape opcode byte 0FH as the primary opcode, plus two additional opcode bytes.

- A mandatory prefix (66H, F2H, or F3H), an escape opcode byte, plus two additional opcode bytes (same as previous bullet).

For example, PHADDW for XMM registers consists of the following sequence: 66 0F 38 01. The first byte is the mandatory prefix.

Valid opcode expressions are defined in Appendix A and Appendix B.

## 2.1.3 ModR/M and SIB Bytes

Many instructions that refer to an operand in memory have an addressing-form specifier byte (called the ModR/M byte) following the primary opcode. The ModR/M byte contains three fields of information:

- The _mod_ field combines with the r/m field to form 32 possible values: eight registers and 24 addressing modes.

- The _reg/opcode_ field specifies either a register number or three more bits of opcode information. The purpose of the reg/opcode field is specified in the primary opcode.

- The _r/m_ field can specify a register as an operand or it can be combined with the mod field to encode an addressing mode. Sometimes, certain combinations of the _mod_ field and the _r/m_ field are used to express opcode information for some instructions.

Certain encodings of the ModR/M byte require a second addressing byte (the SIB byte). The base-plus-index and scale-plus-index forms of 32-bit addressing require the SIB byte. The SIB byte includes the following fields:

- The _scale_ field specifies the scale factor.

- The _index_ field specifies the register number of the index register.

- The _base_ field specifies the register number of the base register.

See Section 2.1.5 for the encodings of the ModR/M and SIB bytes.

## 2.1.4 Displacement and Immediate Bytes

Some addressing forms include a displacement immediately following the ModR/M byte (or the SIB byte if one is present). If a displacement is required, it can be 1, 2, or 4 bytes.

If an instruction specifies an immediate operand, the operand always follows any displacement bytes. An immediate operand can be 1, 2 or 4 bytes.

Vol. 2A 2-3

INSTRUCTION FORMAT

## 2.1.5 Addressing-Mode Encoding of ModR/M and SIB Bytes

The values and corresponding addressing forms of the ModR/M and SIB bytes are shown in Table 2-1 through Table 2-3: 16-bit addressing forms specified by the ModR/M byte are in Table 2-1 and 32-bit addressing forms are in Table 2-2. Table 2-3 shows 32-bit addressing forms specified by the SIB byte. In cases where the reg/opcode field in the ModR/M byte represents an extended opcode, valid encodings are shown in Appendix B.

In Table 2-1 and Table 2-2, the Effective Address column lists 32 effective addresses that can be assigned to the first operand of an instruction by using the Mod and R/M fields of the ModR/M byte. The first 24 options provide ways of specifying a memory location; the last eight (Mod = 11B) provide ways of specifying general-purpose, MMX technology and XMM registers.

The Mod and R/M columns in Table 2-1 and Table 2-2 give the binary encodings of the Mod and R/M fields required to obtain the effective address listed in the first column. For example: see the row indicated by Mod = 11B, R/M = 000B. The row identifies the general-purpose registers EAX, AX or AL; MMX technology register MM0; or XMM register XMM0. The register used is determined by the opcode byte and the operand-size attribute.

Now look at the seventh row in either table (labeled “REG = ”). This row specifies the use of the 3-bit Reg/Opcode field when the field is used to give the location of a second operand. The second operand must be a generalpurpose, MMX technology, or XMM register. Rows one through five list the registers that may correspond to the value in the table. Again, the register used is determined by the opcode byte along with the operand-size attribute.

If the instruction does not require a second operand, then the Reg/Opcode field may be used as an opcode extension. This use is represented by the sixth row in the tables (labeled “/digit (Opcode)”). Note that values in row six are represented in decimal form.

The body of Table 2-1 and Table 2-2 (under the label “Value of ModR/M Byte (in Hexadecimal)”) contains a 32 by 8 array that presents all of 256 values of the ModR/M byte (in hexadecimal). Bits 3, 4, and 5 are specified by the column of the table in which a byte resides. The row specifies bits 0, 1, and 2; and bits 6 and 7. The figure below demonstrates interpretation of one table value.



<!-- Start of picture text -->
Mod 11<br>RM  000<br>/digit (Opcode); REG = 001<br>C8H 11 001 000<br><!-- End of picture text -->

Figure 2-2.  Table Interpretation of ModR/M Byte (C8H)

2-4 Vol. 2A

INSTRUCTION FORMAT

Table 2-1.  16-Bit Addressing Forms with the ModR/M Byte

|r8(/r)<br>r16(/r)<br>r32(/r)<br>mm(/r)<br>xmm(/r)<br>(In decimal) /digit (Opcode)<br>(In binary) REG =|||AL<br>AX<br>EAX<br>MM0<br>XMM0<br>0<br>000|CL<br>CX<br>ECX<br>MM1<br>XMM1<br>1<br>001|DL<br>DX<br>EDX<br>MM2<br>XMM2<br>2<br>010|BL<br>BX<br>EBX<br>MM3<br>XMM3<br>3<br>011|AH<br>SP<br>ESP<br>MM4<br>XMM4<br>4<br>100|CH<br>BP<sup>1</sup><br>EBP<br>MM5<br>XMM5<br>5<br>101|DH<br>SI<br>ESI<br>MM6<br>XMM6<br>6<br>110|BH<br>DI<br>EDI<br>MM7<br>XMM7<br>7<br>111|
|---|---|---|---|---|---|---|---|---|---|---|
|Effective Address|Mod|R/M|||Value of|ModR/M B|yte (in H|exadecim|al)||
|[BX+SI]<br>[BX+DI]<br>[BP+SI]<br>[BP+DI]<br>[SI]<br>[DI]<br>disp16<sup>2</sup><br>[BX]|00|000<br>001<br>010<br>011<br>100<br>101<br>110<br>111|00<br>01<br>02<br>03<br>04<br>05<br>06<br>07|08<br>09<br>0A<br>0B<br>0C<br>0D<br>0E<br>0F|10<br>11<br>12<br>13<br>14<br>15<br>16<br>17|18<br>19<br>1A<br>1B<br>1C<br>1D<br>1E<br>1F|20<br>21<br>22<br>23<br>24<br>25<br>26<br>27|28<br>29<br>2A<br>2B<br>2C<br>2D<br>2E<br>2F|30<br>31<br>32<br>33<br>34<br>35<br>36<br>37|38<br>39<br>3A<br>3B<br>3C<br>3D<br>3E<br>3F|
|[BX+SI]+disp8<sup>3</sup><br>[BX+DI]+disp8<br>[BP+SI]+disp8<br>[BP+DI]+disp8<br>[SI]+disp8<br>[DI]+disp8<br>[BP]+disp8<br>[BX]+disp8|01|000<br>001<br>010<br>011<br>100<br>101<br>110<br>111|40<br>41<br>42<br>43<br>44<br>45<br>46<br>47|48<br>49<br>4A<br>4B<br>4C<br>4D<br>4E<br>4F|50<br>51<br>52<br>53<br>54<br>55<br>56<br>57|58<br>59<br>5A<br>5B<br>5C<br>5D<br>5E<br>5F|60<br>61<br>62<br>63<br>64<br>65<br>66<br>67|68<br>69<br>6A<br>6B<br>6C<br>6D<br>6E<br>6F|70<br>71<br>72<br>73<br>74<br>75<br>76<br>77|78<br>79<br>7A<br>7B<br>7C<br>7D<br>7E<br>7F|
|[BX+SI]+disp16<br>[BX+DI]+disp16<br>[BP+SI]+disp16<br>[BP+DI]+disp16<br>[SI]+disp16<br>[DI]+disp16<br>[BP]+disp16<br>[BX]+disp16|10|000<br>001<br>010<br>011<br>100<br>101<br>110<br>111|80<br>81<br>82<br>83<br>84<br>85<br>86<br>87|88<br>89<br>8A<br>8B<br>8C<br>8D<br>8E<br>8F|90<br>91<br>92<br>93<br>94<br>95<br>96<br>97|98<br>99<br>9A<br>9B<br>9C<br>9D<br>9E<br>9F|A0<br>A1<br>A2<br>A3<br>A4<br>A5<br>A6<br>A7|A8<br>A9<br>AA<br>AB<br>AC<br>AD<br>AE<br>AF|B0<br>B1<br>B2<br>B3<br>B4<br>B5<br>B6<br>B7|B8<br>B9<br>BA<br>BB<br>BC<br>BD<br>BE<br>BF|
|EAX/AX/AL/MM0/XMM0<br>ECX/CX/CL/MM1/XMM1<br>EDX/DX/DL/MM2/XMM2<br>EBX/BX/BL/MM3/XMM3<br>ESP/SP/AHMM4/XMM4<br>EBP/BP/CH/MM5/XMM5<br>ESI/SI/DH/MM6/XMM6<br>EDI/DI/BH/MM7/XMM7|11|000<br>001<br>010<br>011<br>100<br>101<br>110<br>111|C0<br>C1<br>C2<br>C3<br>C4<br>C5<br>C6<br>C7|C8<br>C9<br>CA<br>CB<br>CC<br>CD<br>CE<br>CF|D0<br>D1<br>D2<br>D3<br>D4<br>D5<br>D6<br>D7|D8<br>D9<br>DA<br>DB<br>DC<br>DD<br>DE<br>DF|E0<br>E1<br>E2<br>E3<br>E4<br>E5<br>E6<br>E7|E8<br>E9<br>EA<br>EB<br>EC<br>ED<br>EE<br>EF|F0<br>F1<br>F2<br>F3<br>F4<br>F5<br>F6<br>F7|F8<br>F9<br>FA<br>FB<br>FC<br>FD<br>FE<br>FF|



#### NOTES:

1. The default segment register is SS for the effective addresses containing a BP index, DS for other effective addresses.

2. The disp16 nomenclature denotes a 16-bit displacement that follows the ModR/M byte and that is added to the index.

3. The disp8 nomenclature denotes an 8-bit displacement that follows the ModR/M byte and that is sign-extended and added to the index.

Vol. 2A 2-5

INSTRUCTION FORMAT

Table 2-2.  32-Bit Addressing Forms with the ModR/M Byte

|r8(/r)<br>r16(/r)<br>r32(/r)<br>mm(/r)<br>xmm(/r)<br>(In decimal) /digit (Opcode)<br>(In binary) REG =|||AL<br>AX<br>EAX<br>MM0<br>XMM0<br>0<br>000|CL<br>CX<br>ECX<br>MM1<br>XMM1<br>1<br>001|DL<br>DX<br>EDX<br>MM2<br>XMM2<br>2<br>010|BL<br>BX<br>EBX<br>MM3<br>XMM3<br>3<br>011|AH<br>SP<br>ESP<br>MM4<br>XMM4<br>4<br>100|CH<br>BP<br>EBP<br>MM5<br>XMM5<br>5<br>101|DH<br>SI<br>ESI<br>MM6<br>XMM6<br>6<br>110|BH<br>DI<br>EDI<br>MM7<br>XMM7<br>7<br>111|
|---|---|---|---|---|---|---|---|---|---|---|
|Effective Address|Mod|R/M|||Value of|ModR/M B|yte (in H|exadecim|al)||
|[EAX]<br>[ECX]<br>[EDX]<br>[EBX]<br>[--][--]<sup>1</sup><br>disp32<sup>2</sup><br>[ESI]<br>[EDI]|00|000<br>001<br>010<br>011<br>100<br>101<br>110<br>111|00<br>01<br>02<br>03<br>04<br>05<br>06<br>07|08<br>09<br>0A<br>0B<br>0C<br>0D<br>0E<br>0F|10<br>11<br>12<br>13<br>14<br>15<br>16<br>17|18<br>19<br>1A<br>1B<br>1C<br>1D<br>1E<br>1F|20<br>21<br>22<br>23<br>24<br>25<br>26<br>27|28<br>29<br>2A<br>2B<br>2C<br>2D<br>2E<br>2F|30<br>31<br>32<br>33<br>34<br>35<br>36<br>37|38<br>39<br>3A<br>3B<br>3C<br>3D<br>3E<br>3F|
|[EAX]+disp8<sup>3</sup><br>[ECX]+disp8<br>[EDX]+disp8<br>[EBX]+disp8<br>[--][--]+disp8<br>[EBP]+disp8<br>[ESI]+disp8<br>[EDI]+disp8|01|000<br>001<br>010<br>011<br>100<br>101<br>110<br>111|40<br>41<br>42<br>43<br>44<br>45<br>46<br>47|48<br>49<br>4A<br>4B<br>4C<br>4D<br>4E<br>4F|50<br>51<br>52<br>53<br>54<br>55<br>56<br>57|58<br>59<br>5A<br>5B<br>5C<br>5D<br>5E<br>5F|60<br>61<br>62<br>63<br>64<br>65<br>66<br>67|68<br>69<br>6A<br>6B<br>6C<br>6D<br>6E<br>6F|70<br>71<br>72<br>73<br>74<br>75<br>76<br>77|78<br>79<br>7A<br>7B<br>7C<br>7D<br>7E<br>7F|
|[EAX]+disp32<br>[ECX]+disp32<br>[EDX]+disp32<br>[EBX]+disp32<br>[--][--]+disp32<br>[EBP]+disp32<br>[ESI]+disp32<br>[EDI]+disp32|10|000<br>001<br>010<br>011<br>100<br>101<br>110<br>111|80<br>81<br>82<br>83<br>84<br>85<br>86<br>87|88<br>89<br>8A<br>8B<br>8C<br>8D<br>8E<br>8F|90<br>91<br>92<br>93<br>94<br>95<br>96<br>97|98<br>99<br>9A<br>9B<br>9C<br>9D<br>9E<br>9F|A0<br>A1<br>A2<br>A3<br>A4<br>A5<br>A6<br>A7|A8<br>A9<br>AA<br>AB<br>AC<br>AD<br>AE<br>AF|B0<br>B1<br>B2<br>B3<br>B4<br>B5<br>B6<br>B7|B8<br>B9<br>BA<br>BB<br>BC<br>BD<br>BE<br>BF|
|EAX/AX/AL/MM0/XMM0<br>ECX/CX/CL/MM/XMM1<br>EDX/DX/DL/MM2/XMM2<br>EBX/BX/BL/MM3/XMM3<br>ESP/SP/AH/MM4/XMM4<br>EBP/BP/CH/MM5/XMM5<br>ESI/SI/DH/MM6/XMM6<br>EDI/DI/BH/MM7/XMM7|11|000<br>001<br>010<br>011<br>100<br>101<br>110<br>111|C0<br>C1<br>C2<br>C3<br>C4<br>C5<br>C6<br>C7|C8<br>C9<br>CA<br>CB<br>CC<br>CD<br>CE<br>CF|D0<br>D1<br>D2<br>D3<br>D4<br>D5<br>D6<br>D7|D8<br>D9<br>DA<br>DB<br>DC<br>DD<br>DE<br>DF|E0<br>E1<br>E2<br>E3<br>E4<br>E5<br>E6<br>E7|E8<br>E9<br>EA<br>EB<br>EC<br>ED<br>EE<br>EF|F0<br>F1<br>F2<br>F3<br>F4<br>F5<br>F6<br>F7|F8<br>F9<br>FA<br>FB<br>FC<br>FD<br>FE<br>FF|



NOTES:

1. The [--][--] nomenclature means a SIB follows the ModR/M byte.

2. The disp32 nomenclature denotes a 32-bit displacement that follows the ModR/M byte (or the SIB byte if one is present) and that is added to the index.

3. The disp8 nomenclature denotes an 8-bit displacement that follows the ModR/M byte (or the SIB byte if one is present) and that is sign-extended and added to the index.

Table 2-3 is organized to give 256 possible values of the SIB byte (in hexadecimal). General purpose registers used as a base are indicated across the top of the table, along with corresponding values for the SIB byte’s base field. Table rows in the body of the table indicate the register used as the index (SIB byte bits 3, 4, and 5) and the scaling factor (determined by SIB byte bits 6 and 7).

2-6 Vol. 2A

INSTRUCTION FORMAT

Table 2-3.  32-Bit Addressing Forms with the SIB Byte

|r32<br>(In decimal) Base=<br>(In binary) Base=|||EAX<br>0<br>000|ECX<br>1<br>001|EDX<br>2<br>010|EBX<br>3<br>011|ESP<br>4<br>100|[*]<br>5<br>101|ESI<br>6<br>110|EDI<br>7<br>111|
|---|---|---|---|---|---|---|---|---|---|---|
|Scaled Index|SS|Index|||Valu|e of SIB By|te (in Hex|adecimal)|||
|[EAX]<br>[ECX]<br>[EDX]<br>[EBX]<br>none<br>[EBP]<br>[ESI]<br>[EDI]|00|000<br>001<br>010<br>011<br>100<br>101<br>110<br>111|00<br>08<br>10<br>18<br>20<br>28<br>30<br>38|01<br>09<br>11<br>19<br>21<br>29<br>31<br>39|02<br>0A<br>12<br>1A<br>22<br>2A<br>32<br>3A|03<br>0B<br>13<br>1B<br>23<br>2B<br>33<br>3B|04<br>0C<br>14<br>1C<br>24<br>2C<br>34<br>3C|05<br>0D<br>15<br>1D<br>25<br>2D<br>35<br>3D|06<br>0E<br>16<br>1E<br>26<br>2E<br>36<br>3E|07<br>0F<br>17<br>1F<br>27<br>2F<br>37<br>3F|
|[EAX*2]<br>[ECX*2]<br>[EDX*2]<br>[EBX*2]<br>none<br>[EBP*2]<br>[ESI*2]<br>[EDI*2]|01|000<br>001<br>010<br>011<br>100<br>101<br>110<br>111|40<br>48<br>50<br>58<br>60<br>68<br>70<br>78|41<br>49<br>51<br>59<br>61<br>69<br>71<br>79|42<br>4A<br>52<br>5A<br>62<br>6A<br>72<br>7A|43<br>4B<br>53<br>5B<br>63<br>6B<br>73<br>7B|44<br>4C<br>54<br>5C<br>64<br>6C<br>74<br>7C|45<br>4D<br>55<br>5D<br>65<br>6D<br>75<br>7D|46<br>4E<br>56<br>5E<br>66<br>6E<br>76<br>7E|47<br>4F<br>57<br>5F<br>67<br>6F<br>77<br>7F|
|[EAX*4]<br>[ECX*4]<br>[EDX*4]<br>[EBX*4]<br>none<br>[EBP*4]<br>[ESI*4]<br>[EDI*4]|10|000<br>001<br>010<br>011<br>100<br>101<br>110<br>111|80<br>88<br>90<br>98<br>A0<br>A8<br>B0<br>B8|81<br>89<br>91<br>99<br>A1<br>A9<br>B1<br>B9|82<br>8A<br>92<br>9A<br>A2<br>AA<br>B2<br>BA|83<br>8B<br>93<br>9B<br>A3<br>AB<br>B3<br>BB|84<br>8C<br>94<br>9C<br>A4<br>AC<br>B4<br>BC|85<br>8D<br>95<br>9D<br>A5<br>AD<br>B5<br>BD|86<br>8E<br>96<br>9E<br>A6<br>AE<br>B6<br>BE|87<br>8F<br>97<br>9F<br>A7<br>AF<br>B7<br>BF|
|[EAX*8]<br>[ECX*8]<br>[EDX*8]<br>[EBX*8]<br>none<br>[EBP*8]|11|000<br>001<br>010<br>011<br>100<br>101|C0<br>C8<br>D0<br>D8<br>E0<br>E8|C1<br>C9<br>D1<br>D9<br>E1<br>E9|C2<br>CA<br>D2<br>DA<br>E2<br>EA|C3<br>CB<br>D3<br>DB<br>E3<br>EB|C4<br>CC<br>D4<br>DC<br>E4<br>EC|C5<br>CD<br>D5<br>DD<br>E5<br>ED|C6<br>CE<br>D6<br>DE<br>E6<br>EE|C7<br>CF<br>D7<br>DF<br>E7<br>EF|
|[ESI*8]<br>||110<br>|F0<br>|F1<br>|F2<br>|F3<br>|F4<br>|F5<br>|F6<br>|F7<br>|
|[EDI*8]||111|F8|F9|FA|FB|FC|FD|FE|FF|



NOTES:

1. The [*] nomenclature means a disp32 with no base if the MOD is 00B. Otherwise, [*] means disp8 or disp32 + [EBP]. This provides the following address modes:

<u>MOD bits Effective Address</u>

00 [scaled index] + disp32

- 01 [scaled index] + disp8 + [EBP]

10 [scaled index] + disp32 + [EBP]

# 2.2 IA-32E MODE

IA-32e mode has two sub-modes. These are:

- **Compatibility Mode.** Enables a 64-bit operating system to run most legacy protected mode software unmodified.

- **64-Bit Mode.** Enables a 64-bit operating system to run applications written to access 64-bit address space.

## 2.2.1 REX Prefixes

REX prefixes are instruction-prefix bytes used in 64-bit mode. They do the following:

- Specify GPRs and SSE registers.

Vol. 2A 2-7

INSTRUCTION FORMAT

- Specify 64-bit operand size.

- Specify extended control registers.

Not all instructions require a REX prefix in 64-bit mode. A prefix is necessary only if an instruction references one of the extended registers or uses a 64-bit operand. If a REX prefix is used when it has no meaning, it is ignored. Only one REX prefix is allowed per instruction. If used, the REX prefix byte must immediately precede the opcode byte or the escape opcode byte (0FH). When a REX prefix is used in conjunction with an instruction containing a mandatory prefix, the mandatory prefix must come before the REX so the REX prefix can be immediately preceding the opcode or the escape byte. For example, CVTDQ2PD with a REX prefix should have REX placed between F3 and 0F E6. Other placements are ignored. The instruction-size limit of 15 bytes still applies to instructions with a REX prefix. See Figure 2-3.



<!-- Start of picture text -->
LegacyPrefixes PrefixREX Opcode ModR/M SIB Displacement Immediate<br>Grp 1, Grp  (optional) 1-, 2-, or  1 byte 1 byte Address  Immediate data<br>2, Grp 3,  3-byte  (if required) (if required) displacement of  of 1, 2, or 4<br>Grp 4 opcode 1, 2, or 4 bytes  bytes or none<br>(optional)<br><!-- End of picture text -->

Figure 2-3.  Prefix Ordering in 64-bit Mode

### 2.2.1.1 Encoding

Intel 64 and IA-32 instruction formats specify up to three registers by using 3-bit fields in the encoding, depending on the format:

- ModR/M: the reg and r/m fields of the ModR/M byte.

- ModR/M with SIB: the reg field of the ModR/M byte, the base and index fields of the SIB (scale, index, base) byte.

- Instructions without ModR/M: the reg field of the opcode.

In 64-bit mode, these formats do not change. Bits needed to define fields in the 64-bit context are provided by the addition of REX prefixes.

### 2.2.1.2 More on REX Prefix Fields

REX prefixes are a set of 16 opcodes that span one row of the opcode map and occupy entries 40H to 4FH. These opcodes represent valid instructions (INC or DEC) in IA-32 operating modes and in compatibility mode. In 64-bit mode, the same opcodes represent the instruction prefix REX and are not treated as individual instructions.

The single-byte-opcode forms of the INC/DEC instructions are not available in 64-bit mode. INC/DEC functionality is still available using ModR/M forms of the same instructions (opcodes FF/0 and FF/1).

See Table 2-4 for a summary of the REX prefix format. Figure 2-4 though Figure 2-7 show examples of REX prefix fields in use. Some combinations of REX prefix fields are invalid. In such cases, the prefix is ignored. Some additional information follows:

- Setting REX.W can be used to determine the operand size but does not solely determine operand width. Like the 66H size prefix, 64-bit operand size override has no effect on byte-specific operations.

- For non-byte operations: if a 66H prefix is used with prefix (REX.W = 1), 66H is ignored.

- If a 66H override is used with REX and REX.W = 0, the operand size is 16 bits.

- REX.R modifies the ModR/M reg field when that field encodes a GPR, SSE, control or debug register. REX.R is ignored when ModR/M specifies other registers or defines an extended opcode.

- REX.X bit modifies the SIB index field.

2-8 Vol. 2A

INSTRUCTION FORMAT

- REX.B either modifies the base in the ModR/M r/m field or SIB base field; or it modifies the opcode reg field used for accessing GPRs.

Table 2-4.  REX Prefix Fields [BITS: 0100WRXB]

|Field Name|Bit Position|Definition||
|---|---|---|---|
|-|7:4|0100||
|W|3|0 = Operand|size determined by CS.D|
|||1 = 64 Bit Op|erand Size|
|R|2|Extension of|the ModR/M reg field|
|X|1|Extension of|the SIB index field|
|B|0|Extension of|the ModR/M r/m field, SIB base field, or Opcode reg field|
||||ModRM Byte|
||REX PREFIX<br>0100WR0B|Opcode|mod<br>≠11<br>reg<br>r/m<br>rrr<br>bbb|
||||Rrrr<br>Bbbb<br>OM17Xfig1-3|



Figure 2-4.  Memory Addressing Without an SIB Byte; REX.X Not Used



<!-- Start of picture text -->
ModRM Byte<br>REX PREFIX   Opcode mod reg r/m<br>0100WR0B 11 rrr bbb<br>Rrrr Bbbb<br>OM17Xfig1-4<br><!-- End of picture text -->

Figure 2-5.  Register-Register Addressing (No Memory Operand); REX.X Not Used

Vol. 2A 2-9

INSTRUCTION FORMAT



<!-- Start of picture text -->
ModRM Byte SIB Byte<br>REX PREFIX   Opcode mod reg r/m scale index base<br>0100WRXB ≠ 11 rrr 100 ss xxx bbb<br>Rrrr Xxxx Bbbb<br>OM17Xfig1-5<br><!-- End of picture text -->

Figure 2-6.  Memory Addressing With a SIB Byte



<!-- Start of picture text -->
REX PREFIX   Opcode reg<br>0100W00B bbb<br>Bbbb<br>OM17Xfig1-6<br><!-- End of picture text -->

Figure 2-7.  Register Operand Coded in Opcode Byte; REX.X & REX.R Not Used

In the IA-32 architecture, byte registers (AH, AL, BH, BL, CH, CL, DH, and DL) are encoded in the ModR/M byte’s reg field, the r/m field or the opcode reg field as registers 0 through 7. REX prefixes provide an additional addressing capability for byte-registers that makes the least-significant byte of GPRs available for byte operations. Certain combinations of the fields of the ModR/M byte and the SIB byte have special meaning for register encodings. For some combinations, fields expanded by the REX prefix are not decoded. Table 2-5 describes how each case behaves.

2-10 Vol. 2A

INSTRUCTION FORMAT

Table 2-5.  Special Cases of REX Encodings

|ModR/M or<br>SIB|Sub-field<br>Encodings|Compatibility Mode<br>Operation|Compatibility Mode<br>Implications|Additional Implications|
|---|---|---|---|---|
|ModR/M Byte|mod?11<br>r/m =<br>b*100(ESP)|SIB byte present.|SIB byte required for<br>ESP-based addressing.|REX prefix adds a fourth bit (b) which is not decoded<br>(don't care).<br>SIB byte also required for R12-based addressing.|
|ModR/M Byte|mod = 0<br>r/m =<br>b*101(EBP)|Base register not<br>used.|EBP without a<br>displacement must be<br>done using<br>mod = 01 with<br>displacement of 0.|REX prefix adds a fourth bit (b) which is not decoded<br>(don't care).<br>Using RBP or R13 without displacement must be done<br>using mod = 01 with a displacement of 0.|
|SIB Byte|index =<br>0100(ESP)|Index register not<br>used.|ESP cannot be used as<br>an index register.|REX prefix adds a fourth bit (b) which is decoded.<br>There are no additional implications. The expanded<br>index field allows distinguishing RSP from R12,<br>therefore R12 can be used as an index.|
|SIB Byte|base =<br>0101(EBP)|Base register is<br>unused if mod = 0.|Base register depends<br>on mod encoding.|REX prefix adds a fourth bit (b) which is not decoded.<br>This requires explicit displacement to be used with<br>EBP/RBP or R13.|



NOTES:

* Don’t care about value of REX.B

### 2.2.1.3 Displacement

Addressing in 64-bit mode uses existing 32-bit ModR/M and SIB encodings. The ModR/M and SIB displacement sizes do not change. They remain 8 bits or 32 bits and are sign-extended to 64 bits.

### 2.2.1.4 Direct Memory-Offset MOVs

In 64-bit mode, direct memory-offset forms of the MOV instruction are extended to specify a 64-bit immediate absolute address. This address is called a moffset. No prefix is needed to specify this 64-bit memory offset. For these MOV instructions, the size of the memory offset follows the address-size default (64 bits in 64-bit mode). See Table 2-6.

Table 2-6.  Direct Memory Offset Form of MOV

|Opcode|Instruction|
|---|---|
|A0|MOV AL, moffset|
|A1|MOV EAX, moffset|
|A2|MOV moffset, AL|
|A3|MOV moffset, EAX|



### 2.2.1.5 Immediates

In 64-bit mode, the typical size of immediate operands remains 32 bits. When the operand size is 64 bits, the processor sign-extends all immediates to 64 bits prior to their use.

Support for 64-bit immediate operands is accomplished by expanding the semantics of the existing move (MOV reg, imm16/32) instructions. These instructions (opcodes B8H – BFH) move 16-bits or 32-bits of immediate data (depending on the effective operand size) into a GPR. When the effective operand size is 64 bits, these instructions can be used to load an immediate into a GPR. A REX prefix is needed to override the 32-bit default operand size to a 64-bit operand size.

For example:

48 B8 8877665544332211 MOV RAX,1122334455667788H

Vol. 2A 2-11

INSTRUCTION FORMAT

### 2.2.1.6 RIP-Relative Addressing

A new addressing form, RIP-relative (relative instruction-pointer) addressing, is implemented in 64-bit mode. An effective address is formed by adding displacement to the 64-bit RIP of the next instruction.

In IA-32 architecture and compatibility mode, addressing relative to the instruction pointer is available only with control-transfer instructions. In 64-bit mode, instructions that use ModR/M addressing can use RIP-relative addressing. Without RIP-relative addressing, all ModR/M modes address memory relative to zero.

RIP-relative addressing allows specific ModR/M modes to address memory relative to the 64-bit RIP using a signed 32-bit displacement. This provides an offset range of ±2GB from the RIP. Table 2-7 shows the ModR/M and SIB encodings for RIP-relative addressing. Redundant forms of 32-bit displacement-addressing exist in the current ModR/M and SIB encodings. There is one ModR/M encoding and there are several SIB encodings. RIP-relative addressing is encoded using a redundant form.

In 64-bit mode, the ModR/M Disp32 (32-bit displacement) encoding is re-defined to be RIP+Disp32 rather than displacement-only. See Table 2-7.

Table 2-7.  RIP-Relative Addressing

|ModR/M and S|IB Sub-field Encodings|Compatibility Mode<br>Operation|64-bit Mode<br>Operation|Additional Implications in 64-bit mode|
|---|---|---|---|---|
|ModR/M Byte|mod = 00<br>r/m = 101 (none)|Disp32|RIP + Disp32|In 64-bit mode, if one wants to use a Disp32<br>without specifying a base register, one can use a<br>SIB byte encoding (indicated by ModR/M.r/m=100)<br>as described in the next row.|
|SIB Byte|base = 101 (none)<br>index = 100 (none)<br>scale = 0, 1, 2, 4|If mod = 00, Disp32|Same as legacy|None|



The ModR/M encoding for RIP-relative addressing does not depend on using a prefix. Specifically, the r/m bit field encoding of 101B (used to select RIP-relative addressing) is not affected by the REX prefix. For example, selecting R13 (REX.B = 1, r/m = 101B) with mod = 00B still results in RIP-relative addressing. The 4-bit r/m field of REX.B combined with ModR/M is not fully decoded. In order to address R13 with no displacement, software must encode R13 + 0 using a 1-byte displacement of zero.

RIP-relative addressing is enabled by 64-bit mode, not by a 64-bit address-size. The use of the address-size prefix does not disable RIP-relative addressing. The effect of the address-size prefix is to truncate and zero-extend the computed effective address to 32 bits.

### 2.2.1.7 Default 64-Bit Operand Size

In 64-bit mode, two groups of instructions have a default operand size of 64 bits (do not need a REX prefix for this operand size). These are:

- Near branches.

- All instructions, except far branches, that implicitly reference the RSP.

## 2.2.2 Additional Encodings for Control and Debug Registers

In 64-bit mode, more encodings for control and debug registers are available. The REX.R bit is used to modify the ModR/M reg field when that field encodes a control or debug register (see Table 2-4). These encodings enable the processor to address CR8-CR15 and DR8- DR15. An additional control register (CR8) is defined in 64-bit mode. CR8 becomes the Task Priority Register (TPR).

In the first implementation of IA-32e mode, CR9-CR15 and DR8-DR15 are not implemented. Any attempt to access unimplemented registers results in an invalid-opcode exception (#UD).

2-12 Vol. 2A

INSTRUCTION FORMAT

# 2.3 INTEL® ADVANCED VECTOR EXTENSIONS (INTEL® AVX)

Intel AVX instructions are encoded using an encoding scheme that combines prefix bytes, opcode extension field, operand encoding fields, and vector length encoding capability into a new prefix, referred to as VEX. In the VEX encoding scheme, the VEX prefix may be two or three bytes long, depending on the instruction semantics. Despite the two-byte or three-byte length of the VEX prefix, the VEX encoding format provides a more compact representation/packing of the components of encoding an instruction in Intel 64 architecture. The VEX encoding scheme also allows more headroom for future growth of Intel 64 architecture.

## 2.3.1 Instruction Format

Instruction encoding using VEX prefix provides several advantages:

- Instruction syntax support for three operands and up-to four operands when necessary. For example, the third source register used by VBLENDVPD is encoded using bits 7:4 of the immediate byte.

- Encoding support for vector length of 128 bits (using XMM registers) and 256 bits (using YMM registers).

- Encoding support for instruction syntax of non-destructive source operands.

- Elimination of escape opcode byte (0FH), SIMD prefix byte (66H, F2H, F3H) via a compact bit field representation within the VEX prefix.

- Elimination of the need to use REX prefix to encode the extended half of general-purpose register sets (R8R15) for direct register access, memory addressing, or accessing XMM8-XMM15 (including YMM8-YMM15).

- Flexible and more compact bit fields are provided in the VEX prefix to retain the full functionality provided by REX prefix. REX.W, REX.X, REX.B functionalities are provided in the three-byte VEX prefix only because only a subset of SIMD instructions need them.

- Extensibility for future instruction extensions without significant instruction length increase.

Figure 2-8 shows the Intel 64 instruction encoding format with VEX prefix support. Legacy instruction without a VEX prefix is fully supported and unchanged. The use of VEX prefix in an Intel 64 instruction is optional, but a VEX prefix is required for Intel 64 instructions that operate on YMM registers or support three and four operand syntax. VEX prefix is not a constant-valued, “single-purpose” byte like 0FH, 66H, F2H, F3H in legacy SSE instructions. VEX prefix provides substantially richer capability than the REX prefix.



<!-- Start of picture text -->
# Bytes 2,3 1 1 0,1 0,1,2,4 0,1<br>[Prefixes] [VEX] OPCODE ModR/M [SIB] [DISP] [IMM]<br><!-- End of picture text -->

Figure 2-8.  Instruction Encoding Format with VEX Prefix

## 2.3.2 VEX and the LOCK prefix

Any VEX-encoded instruction with a LOCK prefix preceding VEX will #UD.

## 2.3.3 VEX and the 66H, F2H, and F3H prefixes

Any VEX-encoded instruction with a 66H, F2H, or F3H prefix preceding VEX will #UD.

## 2.3.4 VEX and the REX prefix

Any VEX-encoded instruction with a REX prefix proceeding VEX will #UD.

Vol. 2A 2-13

INSTRUCTION FORMAT

## 2.3.5 The VEX Prefix

The VEX prefix is encoded in either the two-byte form (the first byte must be C5H) or in the three-byte form (the first byte must be C4H). The two-byte VEX is used mainly for 128-bit, scalar, and the most common 256-bit AVX instructions; while the three-byte VEX provides a compact replacement of REX and 3-byte opcode instructions (including AVX and FMA instructions). Beyond the first byte of the VEX prefix, it consists of a number of bit fields providing specific capability, they are shown in Figure 2-9.

The bit fields of the VEX prefix can be summarized by its functional purposes:

- Non-destructive source register encoding (applicable to three and four operand syntax): This is the first source operand in the instruction syntax. It is represented by the notation, VEX.vvvv. This field is encoded using 1’s complement form (inverted form), i.e., XMM0/YMM0/R0 is encoded as 1111B, XMM15/YMM15/R15 is encoded as 0000B.

- Vector length encoding: This 1-bit field represented by the notation VEX.L. L= 0 means vector length is 128 bits wide, L=1 means 256 bit vector. The value of this field is written as VEX.128 or VEX.256 in this document to distinguish encoded values of other VEX bit fields.

- REX prefix functionality: Full REX prefix functionality is provided in the three-byte form of VEX prefix. However the VEX bit fields providing REX functionality are encoded using 1’s complement form, i.e., XMM0/YMM0/R0 is encoded as 1111B, XMM15/YMM15/R15 is encoded as 0000B.

   - Two-byte form of the VEX prefix only provides the equivalent functionality of REX.R, using 1’s complement encoding. This is represented as VEX.R.

   - Three-byte form of the VEX prefix provides REX.R, REX.X, REX.B functionality using 1’s complement encoding and three dedicated bit fields represented as VEX.R, VEX.X, VEX.B.

   - Three-byte form of the VEX prefix provides the functionality of REX.W only to specific instructions that need to override default 32-bit operand size for a general purpose register to 64-bit size in 64-bit mode. For those applicable instructions, VEX.W field provides the same functionality as REX.W. VEX.W field can provide completely different functionality for other instructions.

Consequently, the use of REX prefix with VEX encoded instructions is not allowed. However, the intent of the REX prefix for expanding register set is reserved for future instruction set extensions using VEX prefix encoding format.

- Compaction of SIMD prefix: Legacy SSE instructions effectively use SIMD prefixes (66H, F2H, F3H) as an opcode extension field. VEX prefix encoding allows the functional capability of such legacy SSE instructions (operating on XMM registers, bits 255:128 of corresponding YMM unmodified) to be encoded using the VEX.pp field without the presence of any SIMD prefix. The VEX-encoded 128-bit instruction will zero-out bits 255:128 of the destination register. VEX-encoded instruction may have 128 bit vector length or 256 bits length.

- Compaction of two-byte and three-byte opcode: More recently introduced legacy SSE instructions employ two and three-byte opcode. The one or two leading bytes are: 0FH, and 0FH 3AH/0FH 38H. The one-byte escape (0FH) and two-byte escape (0FH 3AH, 0FH 38H) can also be interpreted as an opcode extension field. The VEX.mmmmm field provides compaction to allow many legacy instruction to be encoded without the constant byte sequence, 0FH, 0FH 3AH, 0FH 38H. These VEX-encoded instruction may have 128 bit vector length or 256 bits length.

The VEX prefix is required to be the last prefix and immediately precedes the opcode bytes. It must follow any other prefixes. If VEX prefix is present a REX prefix is not supported.

The 3-byte VEX leaves room for future expansion with 3 reserved bits. REX and the 66h/F2h/F3h prefixes are reclaimed for future use.

VEX prefix has a two-byte form and a three byte form. If an instruction syntax can be encoded using the two-byte form, it can also be encoded using the three byte form of VEX. The latter increases the length of the instruction by one byte. This may be helpful in some situations for code alignment.

The VEX prefix supports 256-bit versions of floating-point SSE, SSE2, SSE3, and SSE4 instructions. Note, certain new instruction functionality can only be encoded with the VEX prefix.

The VEX prefix will #UD on any instruction containing MMX register sources or destinations.

2-14 Vol. 2A

INSTRUCTION FORMAT



<!-- Start of picture text -->
Byte 0 Byte 1 Byte 2<br>(Bit Position) 7 0 7 6 5 4 0 7 6 3 2 1 0<br>3-byte VEX 11000100 R X B m-mmmm W vvvv1 L  pp<br>7 0 7 6 3 2 1 0<br>2-byte VEX 11000101 R vvvv1 L  pp<br><!-- End of picture text -->

R: REX.R in 1’s complement (inverted) form 1: Same as REX.R=0 (must be 1 in 32-bit mode) 0: Same as REX.R=1 (64-bit mode only)

X: REX.X in 1’s complement (inverted) form 1: Same as REX.X=0 (must be 1 in 32-bit mode) 0: Same as REX.X=1 (64-bit mode only) B: REX.B in 1’s complement (inverted) form 1: Same as REX.B=0 (Ignored in 32-bit mode). 0: Same as REX.B=1 (64-bit mode only) W: opcode specific (use like REX.W, or used for opcode extension, or ignored, depending on the opcode byte) m-mmmm: 00000: Reserved for future use (will #UD) 00001: implied 0F leading opcode byte 00010: implied 0F 38 leading opcode bytes 00011: implied 0F 3A leading opcode bytes 00100-11111: Reserved for future use (will #UD) vvvv: a register specifier (in 1’s complement form) or 1111 if unused. L: Vector Length 0: scalar or 128-bit vector 1: 256-bit vector pp: opcode extension providing equivalent functionality of a SIMD prefix 00: None 01: 66 10: F3 11: F2

Figure 2-9.  VEX bit fields

The following subsections describe the various fields in two or three-byte VEX prefix.

### 2.3.5.1 VEX Byte 0, bits[7:0]

VEX Byte 0, bits [7:0] must contain the value 11000101b (C5h) or 11000100b (C4h). The 3-byte VEX uses the C4h first byte, while the 2-byte VEX uses the C5h first byte.

### 2.3.5.2 VEX Byte 1, bit [7] - ‘R’

VEX Byte 1, bit [7] contains a bit analogous to a bit inverted REX.R. In protected and compatibility modes the bit must be set to ‘1’ otherwise the instruction is LES or LDS.

Vol. 2A 2-15

INSTRUCTION FORMAT

This bit is present in both 2- and 3-byte VEX prefixes.

The usage of WRXB bits for legacy instructions is explained in detail section 2.2.1.2 of Intel 64 and IA-32 Architectures Software developer’s manual, Volume 2A.

This bit is stored in bit inverted format.

### 2.3.5.3 3-byte VEX byte 1, bit[6] - ‘X’

Bit[6] of the 3-byte VEX byte 1 encodes a bit analogous to a bit inverted REX.X. It is an extension of the SIB Index field in 64-bit modes. In 32-bit modes, this bit must be set to ‘1’ otherwise the instruction is LES or LDS. This bit is available only in the 3-byte VEX prefix.

This bit is stored in bit inverted format.

### 2.3.5.4 3-byte VEX byte 1, bit[5] - ‘B’

Bit[5] of the 3-byte VEX byte 1 encodes a bit analogous to a bit inverted REX.B. In 64-bit modes, it is an extension of the ModR/M r/m field, or the SIB base field. In 32-bit modes, this bit is ignored. This bit is available only in the 3-byte VEX prefix.

This bit is stored in bit inverted format.

### 2.3.5.5 3-byte VEX byte 2, bit[7] - ‘W’

Bit[7] of the 3-byte VEX byte 2 is represented by the notation VEX.W. It can provide following functions, depending on the specific opcode.

- For AVX instructions that have equivalent legacy SSE instructions (typically these SSE instructions have a general-purpose register operand with its operand size attribute promotable by REX.W), if REX.W promotes the operand size attribute of the general-purpose register operand in legacy SSE instruction, VEX.W has same meaning in the corresponding AVX equivalent form. In 32-bit modes for these instructions, VEX.W is silently ignored.

- For AVX instructions that have equivalent legacy SSE instructions (typically these SSE instructions have operands with their operand size attribute fixed and not promotable by REX.W), if REX.W is don’t care in legacy SSE instruction, VEX.W is ignored in the corresponding AVX equivalent form irrespective of mode.

- For new AVX instructions where VEX.W has no defined function (typically these meant the combination of the opcode byte and VEX.mmmmm did not have any equivalent SSE functions), VEX.W is reserved as zero and setting to other than zero will cause instruction to #UD.

### 2.3.5.6 2-byte VEX Byte 1, bits[6:3] and 3-byte VEX Byte 2, bits [6:3]- ‘vvvv’ the Source or Dest Register Specifier

In 32-bit mode the VEX first byte C4 and C5 alias onto the LES and LDS instructions. To maintain compatibility with existing programs the VEX 2nd byte, bits [7:6] must be 11b. To achieve this, the VEX payload bits are selected to place only inverted, 64-bit valid fields (extended register selectors) in these upper bits.

The 2-byte VEX Byte 1, bits [6:3] and the 3-byte VEX, Byte 2, bits [6:3] encode a field (shorthand VEX.vvvv) that for instructions with 2 or more source registers and an XMM or YMM or memory destination encodes the first source register specifier stored in inverted (1’s complement) form.

VEX.vvvv is not used by the instructions with one source (except certain shifts, see below) or on instructions with no XMM or YMM or memory destination. If an instruction does not use VEX.vvvv then it should be set to 1111b otherwise instruction will #UD.

In 64-bit mode all 4 bits may be used. See Table 2-8 for the encoding of the XMM or YMM registers. In 32-bit and 16-bit modes bit 6 must be 1 (if bit 6 is not 1, the 2-byte VEX version will generate LDS instruction and the 3-byte VEX version will ignore this bit).

2-16 Vol. 2A

INSTRUCTION FORMAT

Table 2-8.  VEX.vvvv to register name mapping

|VEX.vvvv|Dest Register|General-Purpose Register<br>(If Applicable)<sup>1</sup>|Valid in Legacy/Compatibility<br>32-bit modes?<sup>2</sup>|
|---|---|---|---|
|1111B|XMM0/YMM0|RAX/EAX|Valid|
|1110B|XMM1/YMM1|RCX/ECX|Valid|
|1101B|XMM2/YMM2|RDX/EDX|Valid|
|1100B|XMM3/YMM3|RBX/EBX|Valid|
|1011B|XMM4/YMM4|RSP/ESP|Valid|
|1010B|XMM5/YMM5|RBP/EBP|Valid|
|1001B|XMM6/YMM6|RSI/ESI|Valid|
|1000B|XMM7/YMM7|RDI/EDI|Valid|
|0111B|XMM8/YMM8|R8/R8D|Invalid|
|0110B|XMM9/YMM9|R9/R9D|Invalid|
|0101B|XMM10/YMM10|R10/R10D|Invalid|
|0100B|XMM11/YMM11|R11/R11D|Invalid|
|0011B|XMM12/YMM12|R12/R12D|Invalid|
|0010B|XMM13/YMM13|R13/R13D|Invalid|
|0001B|XMM14/YMM14|R14/R14D|Invalid|
|0000B|XMM15/YMM15|R15/R15D|Invalid|



NOTES:

1. See Section 2.6, “VEX Encoding Support for GPR Instructions” for additional details.

2. Only the first eight General-Purpose Registers are accessible/encodable in 16/32b modes.

The VEX.vvvv field is encoded in bit inverted format for accessing a register operand.

## 2.3.6 Instruction Operand Encoding and VEX.vvvv, ModR/M

VEX-encoded instructions support three-operand and four-operand instruction syntax. Some VEX-encoded instructions have syntax with less than three operands, e.g., VEX-encoded pack shift instructions support one source operand and one destination operand).

The roles of VEX.vvvv, reg field of ModR/M byte (ModR/M.reg), r/m field of ModR/M byte (ModR/M.r/m) with respect to encoding destination and source operands vary with different type of instruction syntax.

The role of VEX.vvvv can be summarized to three situations:

- VEX.vvvv encodes the first source register operand, specified in inverted (1’s complement) form and is valid for instructions with 2 or more source operands.

- VEX.vvvv encodes the destination register operand, specified in 1’s complement form for certain vector shifts. The instructions where VEX.vvvv is used as a destination are listed in Table 2-9. The notation in the “Opcode” column in Table 2-9 is described in detail in section 3.1.1.

- VEX.vvvv does not encode any operand, the field is reserved and should contain 1111b.

Table 2-9.  Instructions with a VEX.vvvv destination

|Opcode|Instruction mnemonic|
|---|---|
|VEX.128.66.0F 73 /7 ib|VPSLLDQ xmm1, xmm2, imm8|
|VEX.128.66.0F 73 /3 ib|VPSRLDQ xmm1, xmm2, imm8|
|VEX.128.66.0F 71 /2 ib|VPSRLW xmm1, xmm2, imm8|
|VEX.128.66.0F 72 /2 ib|VPSRLD xmm1, xmm2, imm8|
|VEX.128.66.0F 73 /2 ib|VPSRLQ xmm1, xmm2, imm8|
|VEX.128.66.0F 71 /4 ib|VPSRAW xmm1, xmm2, imm8|



Vol. 2A 2-17

INSTRUCTION FORMAT

|Opcode|Instruction mnemonic|
|---|---|
|VEX.128.66.0F 72 /4 ib|VPSRAD xmm1, xmm2, imm8|
|VEX.128.66.0F 71 /6 ib|VPSLLW xmm1, xmm2, imm8|
|VEX.128.66.0F 72 /6 ib|VPSLLD xmm1, xmm2, imm8|
|VEX.128.66.0F 73 /6 ib|VPSLLQ xmm1, xmm2, imm8|



The role of ModR/M.r/m field can be summarized to two situations:

- ModR/M.r/m encodes the instruction operand that references a memory address.

- For some instructions that do not support memory addressing semantics, ModR/M.r/m encodes either the destination register operand or a source register operand.

The role of ModR/M.reg field can be summarized to two situations:

- ModR/M.reg encodes either the destination register operand or a source register operand.

- For some instructions, ModR/M.reg is treated as an opcode extension and not used to encode any instruction operand.

For instruction syntax that support four operands, VEX.vvvv, ModR/M.r/m, ModR/M.reg encodes three of the four operands. The role of bits 7:4 of the immediate byte serves the following situation:

- Imm8[7:4] encodes the third source register operand.

### 2.3.6.1 3-byte VEX byte 1, bits[4:0] - “m-mmmm”

Bits[4:0] of the 3-byte VEX byte 1 encode an implied leading opcode byte (0F, 0F 38, or 0F 3A). Several bits are reserved for future use and will #UD unless 0.

Table 2-10.   VEX.m-mmmm interpretation

|VEX.m-mmmm|Implied Leading Opcode Bytes|
|---|---|
|00000B|Reserved|
|00001B|0F|
|00010B|0F 38|
|00011B|0F 3A|
|00100-11111B|Reserved|
|(2-byte VEX)|0F|



VEX.m-mmmm is only available on the 3-byte VEX. The 2-byte VEX implies a leading 0Fh opcode byte.

### 2.3.6.2 2-byte VEX byte 1, bit[2], and 3-byte VEX byte 2, bit [2]- “L”

The vector length field, VEX.L, is encoded in bit[2] of either the second byte of 2-byte VEX, or the third byte of 3- byte VEX. If “VEX.L = 1”, it indicates 256-bit vector operation. “VEX.L = 0” indicates scalar and 128-bit vector operations.

The instruction VZEROUPPER is a special case that is encoded with VEX.L = 0, although its operation zero’s bits 255:128 of all YMM registers accessible in the current operating mode. See the following table.

2-18 Vol. 2A

INSTRUCTION FORMAT

Table 2-11.  VEX.L interpretation

|VEX.L|Vector Length|
|---|---|
|0|128-bit (or 32/64-bit scalar)|
|1|256-bit|



### 2.3.6.3 2-byte VEX byte 1, bits[1:0], and 3-byte VEX byte 2, bits [1:0]- “pp”

Up to one implied prefix is encoded by bits[1:0] of either the 2-byte VEX byte 1 or the 3-byte VEX byte 2. The prefix behaves as if it was encoded prior to VEX, but after all other encoded prefixes. See the following table.

Table 2-12.  VEX.pp interpretation

|pp|Implies this prefix after other prefixes but before VEX|
|---|---|
|00B|None|
|01B|66|
|10B|F3|
|11B|F2|



## 2.3.7 The Opcode Byte

One (and only one) opcode byte follows the 2 or 3 byte VEX. Legal opcodes are specified in Appendix B, in color. Any instruction that uses illegal opcode will #UD.

## 2.3.8 The ModR/M, SIB, and Displacement Bytes

The encodings are unchanged but the interpretation of reg_field or rm_field differs (see above).

## 2.3.9 The Third Source Operand (Immediate Byte)

VEX-encoded instructions can support instruction with a four operand syntax. VBLENDVPD, VBLENDVPS, and PBLENDVB use imm8[7:4] to encode one of the source registers.

## 2.3.10 Intel® AVX Instructions and the Upper 128-bits of YMM registers

If an instruction with a destination XMM register is encoded with a VEX prefix, the processor zeroes the upper bits (above bit 128) of the equivalent YMM register. Legacy SSE instructions without VEX preserve the upper bits.

### 2.3.10.1  Vector Length Transition and Programming Considerations

An instruction encoded with a VEX.128 prefix that loads a YMM register operand operates as follows:

- Data is loaded into bits 127:0 of the register

- Bits above bit 127 in the register are cleared.

Thus, such an instruction clears bits 255:128 of a destination YMM register on processors with a maximum vectorregister width of 256 bits. In the event that future processors extend the vector registers to greater widths, an instruction encoded with a VEX.128 or VEX.256 prefix will also clear any bits beyond bit 255. (This is in contrast with legacy SSE instructions, which have no VEX prefix; these modify only bits 127:0 of any destination register operand.)

Programmers should bear in mind that instructions encoded with VEX.128 and VEX.256 prefixes will clear any future extensions to the vector registers. A calling function that uses such extensions should save their state before calling legacy functions. This is not possible for involuntary calls (e.g., into an interrupt-service routine). It is recommended that software handling involuntary calls accommodate this by not executing instructions encoded

Vol. 2A 2-19

INSTRUCTION FORMAT

with VEX.128 and VEX.256 prefixes. In the event that it is not possible or desirable to restrict these instructions, then software must take special care to avoid actions that would, on future processors, zero the upper bits of vector registers.

Processors that support further vector-register extensions (defining bits beyond bit 255) will also extend the XSAVE and XRSTOR instructions to save and restore these extensions. To ensure forward compatibility, software that handles involuntary calls and that uses instructions encoded with VEX.128 and VEX.256 prefixes should first save and then restore the vector registers (with any extensions) using the XSAVE and XRSTOR instructions with save/restore masks that set bits that correspond to all vector-register extensions. Ideally, software should rely on a mechanism that is cognizant of which bits to set. (E.g., an OS mechanism that sets the save/restore mask bits for all vector-register extensions that are enabled in XCR0.) Saving and restoring state with instructions other than XSAVE and XRSTOR will, on future processors with wider vector registers, corrupt the extended state of the vector registers - even if doing so functions correctly on processors supporting 256-bit vector registers. (The same is true if XSAVE and XRSTOR are used with a save/restore mask that does not set bits corresponding to all supported extensions to the vector registers.)

## 2.3.11 Intel® AVX Instruction Length

The Intel AVX instructions described in this document (including VEX and ignoring other prefixes) do not exceed 11 bytes in length, but may increase in the future. The maximum length of an Intel 64 and IA-32 instruction remains 15 bytes.

## 2.3.12 Vector SIB (VSIB) Memory Addressing

In Intel<sup>®</sup> Advanced Vector Extensions 2 (Intel<sup>®</sup> AVX2), an SIB byte that follows the ModR/M byte can support VSIB memory addressing to an array of linear addresses. VSIB addressing is only supported in a subset of Intel AVX2 instructions. VSIB memory addressing requires 32-bit or 64-bit effective address. In 32-bit mode, VSIB addressing is not supported when address size attribute is overridden to 16 bits. In 16-bit protected mode, VSIB memory addressing is permitted if address size attribute is overridden to 32 bits. Additionally, VSIB memory addressing is supported only with VEX prefix.

In VSIB memory addressing, the SIB byte consists of:

- The scale field (bit 7:6) specifies the scale factor.

- The index field (bits 5:3) specifies the register number of the vector index register, each element in the vector register specifies an index.

- The base field (bits 2:0) specifies the register number of the base register.

Table 2-3 shows the 32-bit VSIB addressing form. It is organized to give 256 possible values of the SIB byte (in hexadecimal). General purpose registers used as a base are indicated across the top of the table, along with corresponding values for the SIB byte’s base field. The register names also include R8D-R15D applicable only in 64-bit mode (when address size override prefix is used, but the value of VEX.B is not shown in Table 2-3). In 32-bit mode, R8D-R15D does not apply.

Table rows in the body of the table indicate the vector index register used as the index field and each supported scaling factor shown separately. Vector registers used in the index field can be XMM or YMM registers. The leftmost column includes vector registers VR8-VR15 (i.e., XMM8/YMM8-XMM15/YMM15), which are only available in 64-bit mode and does not apply if encoding in 32-bit mode.

2-20 Vol. 2A

INSTRUCTION FORMAT

Table 2-13.  32-Bit VSIB Addressing Forms of the SIB Byte

|r32<br>(In decimal) Base=<br>(In binary) Base=||||EAX/<br>R8D<br>0<br>000|ECX/<br>R9D<br>1<br>001|EDX/<br>R10D<br>2<br>010|EBX/<br>R11D<br>3<br>011|ESP/<br>R12D<br>4<br>100|EBP/<br>R13D<sup>1</sup><br>5<br>101|ESI/<br>R14D<br>6<br>110|EDI/<br>R15D<br>7<br>111|
|---|---|---|---|---|---|---|---|---|---|---|---|
|Scaled Index||SS|Index|||Value|of SIB By|te (in Hexa|decimal)|||
|VR0/VR8<br>VR1/VR9<br>VR2/VR10<br>VR3/VR11<br>VR4/VR12<br>VR5/VR13<br>VR6/VR14<br>VR7/VR15|*1|00|000<br>001<br>010<br>011<br>100<br>101<br>110<br>111|00<br>08<br>10<br>18<br>20<br>28<br>30<br>38|01<br>09<br>11<br>19<br>21<br>29<br>31<br>39|02<br>0A<br>12<br>1A<br>22<br>2A<br>32<br>3A|03<br>0B<br>13<br>1B<br>23<br>2B<br>33<br>3B|04<br>0C<br>14<br>1C<br>24<br>2C<br>34<br>3C|05<br>0D<br>15<br>1D<br>25<br>2D<br>35<br>3D|06<br>0E<br>16<br>1E<br>26<br>2E<br>36<br>3E|07<br>0F<br>17<br>1F<br>27<br>2F<br>37<br>3F|
|VR0/VR8<br>VR1/VR9<br>VR2/VR10<br>VR3/VR11<br>VR4/VR12<br>VR5/VR13<br>VR6/VR14<br>VR7/VR15|*2|01|000<br>001<br>010<br>011<br>100<br>101<br>110<br>111|40<br>48<br>50<br>58<br>60<br>68<br>70<br>78|41<br>49<br>51<br>59<br>61<br>69<br>71<br>79|42<br>4A<br>52<br>5A<br>62<br>6A<br>72<br>7A|43<br>4B<br>53<br>5B<br>63<br>6B<br>73<br>7B|44<br>4C<br>54<br>5C<br>64<br>6C<br>74<br>7C|45<br>4D<br>55<br>5D<br>65<br>6D<br>75<br>7D|46<br>4E<br>56<br>5E<br>66<br>6E<br>76<br>7E|47<br>4F<br>57<br>5F<br>67<br>6F<br>77<br>7F|
|VR0/VR8<br>VR1/VR9<br>VR2/VR10<br>VR3/VR11<br>VR4/VR12<br>VR5/VR13<br>VR6/VR14<br>VR7/VR15|*4|10|000<br>001<br>010<br>011<br>100<br>101<br>110<br>111|80<br>88<br>90<br>98<br>A0<br>A8<br>B0<br>B8|81<br>89<br>91<br>89<br>A1<br>A9<br>B1<br>B9|82<br>8A<br>92<br>9A<br>A2<br>AA<br>B2<br>BA|83<br>8B<br>93<br>9B<br>A3<br>AB<br>B3<br>BB|84<br>8C<br>94<br>9C<br>A4<br>AC<br>B4<br>BC|85<br>8D<br>95<br>9D<br>A5<br>AD<br>B5<br>BD|86<br>8E<br>96<br>9E<br>A6<br>AE<br>B6<br>BE|87<br>8F<br>97<br>9F<br>A7<br>AF<br>B7<br>BF|
|VR0/VR8<br>VR1/VR9<br>VR2/VR10<br>VR3/VR11<br>VR4/VR12<br>VR5/VR13|*8|11|000<br>001<br>010<br>011<br>100<br>101|C0<br>C8<br>D0<br>D8<br>E0<br>E8|C1<br>C9<br>D1<br>D9<br>E1<br>E9|C2<br>CA<br>D2<br>DA<br>E2<br>EA|C3<br>CB<br>D3<br>DB<br>E3<br>EB|C4<br>CC<br>D4<br>DC<br>E4<br>EC|C5<br>CD<br>D5<br>DD<br>E5<br>ED|C6<br>CE<br>D6<br>DE<br>E6<br>EE|C7<br>CF<br>D7<br>DF<br>E7<br>EF|
|VR6/VR14|||110|F0|F1|F2|F3|F4|F5|F6|F7|
|VR7/VR15|||111|F8|F9|FA|FB|FC|FD|FE|FF|



NOTES:

1. If ModR/M.mod = 00b, the base address is zero, then effective address is computed as [scaled vector index] + disp32. Otherwise the base address is computed as [EBP/R13]+ disp, the displacement is either 8 bit or 32 bit depending on the value of ModR/M.mod: MOD Effective Address 00b [Scaled Vector Register] + Disp32 01b [Scaled Vector Register] + Disp8 + [EBP/R13] 10b [Scaled Vector Register] + Disp32 + [EBP/R13]

### 2.3.12.1  64-bit Mode VSIB Memory Addressing

In 64-bit mode VSIB memory addressing uses the VEX.B field and the base field of the SIB byte to encode one of the 16 general-purpose register as the base register. The VEX.X field and the index field of the SIB byte encode one of the 16 vector registers as the vector index register.

In 64-bit mode the top row of Table 2-13 base register should be interpreted as the full 64-bit of each register.

# 2.4 INTEL® ADVANCED MATRIX EXTENSIONS (INTEL® AMX)

Intel<sup>®</sup> AMX instructions follow the general documentation convention established in previous sections. Additionally, Intel<sup>®</sup> Advanced Matrix Extensions use notation conventions as described below.

In the instruction encoding boxes, **sibmem** is used to denote an encoding where a ModR/M byte and SIB byte are used to indicate a memory operation where the base and displacement are used to point to memory, and the index

Vol. 2A 2-21

INSTRUCTION FORMAT

register (if present) is used to denote a stride between memory rows. The index register is scaled by the sib.scale field as usual. The base register is added to the displacement, if present.

In the instruction encoding, the ModR/M byte is represented several ways depending on the role it plays. The ModR/M byte has 3 fields: 2-bit ModR/M.mod field, a 3-bit ModR/M.reg field and a 3-bit ModR/M.r/m field. When all bits of the ModR/M byte have fixed values for an instruction, the 2-hex nibble value of that byte is presented after the opcode in the encoding boxes on the instruction description pages. When only some fields of the ModR/M byte must contain fixed values, those values are specified as follows:

- If only the ModR/M.mod must be 0b11, and ModR/M.reg and ModR/M.r/m fields are unrestricted, this is denoted as **11:rrr:bbb** . The **rrr** correspond to the 3-bits of the ModR/M.reg field and the **bbb** correspond to the 3-bits of the ModR/M.r/m field.

- If the ModR/M.mod field is constrained to be a value other than 0b11, i.e., it must be one of 0b00, 0b01, or 0b10, then the notation !(11) is used.

- If the ModR/M.reg field had a specific required value, e.g., 0b101, that would be denoted as mm:101:bbb.

### NOTE

Historically this document only specified the ModR/M.reg field restrictions with the notation /0 ... /7 and did not specify restrictions on the ModR/M.mod and ModR/M.r/m fields in the encoding boxes.

# 2.5 INTEL® AVX AND INTEL® SSE INSTRUCTION EXCEPTION SPECIFICATION

To look up the exceptions of legacy 128-bit SIMD instruction, 128-bit VEX-encoded instructions, and 256-bit VEXencoded instruction, Table 2-14 summarizes the exception behavior into separate classes, with detailed exception conditions defined in sub-sections 2.5.1 through 2.6.1. For example, ADDPS contains the entry: “See Exceptions Type 2”

In this entry, _“Type2”_ can be looked up in Table 2-14.

The instruction’s corresponding CPUID feature flag can be identified in the fourth column of the Instruction summary table.

Note: #UD on CPUID feature flags=0 is not guaranteed in a virtualized environment if the hardware supports the feature flag.

### NOTE

Instructions that operate only with MMX, X87, or general-purpose registers are not covered by the exception classes defined in this section. For instructions that operate on MMX registers, see Section 23.25.3, “Exception Conditions of Legacy SIMD Instructions Operating on MMX Registers” in the _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 3B_ .

2-22 Vol. 2A

INSTRUCTION FORMAT

Table 2-14.  Exception Class Description

|Exception Class|Instruction set|Mem arg|Floating-Point<br>Exceptions (#XM)|
|---|---|---|---|
|Type 1|AVX,<br>Legacy SSE|16/32 byte explicitly<br>aligned|None|
|Type 2|AVX,<br>Legacy SSE|16/32 byte not explicitly<br>aligned|Yes|
|Type 3|AVX,<br>Legacy SSE|< 16 byte|Yes|
|Type 4|AVX,<br>Legacy SSE|16/32 byte not explicitly<br>aligned|No|
|Type 5|AVX,<br>Legacy SSE|< 16 byte|No|
|Type 6|AVX (no Legacy SSE)|Varies|(At present, none do)|
|Type 7|AVX,<br>Legacy SSE|None|None|
|Type 8|AVX|None|None|
|Type 11|F16C|8 or 16 byte, Not explicitly<br>aligned, no AC#|Yes|
|Type 12|AVX2 Gathers|Not explicitly aligned, no<br>AC#|No|



See Table 2-15 for lists of instructions in each exception class.

Vol. 2A 2-23

INSTRUCTION FORMAT

Table 2-15.  Instructions in each Exception Class

|Exception Class|Instruction|
|---|---|
|Type 1|(V)MOVAPD, (V)MOVAPS, (V)MOVDQA, (V)MOVNTDQ, (V)MOVNTDQA, (V)MOVNTPD, (V)MOVNTPS|
|Type 2|(V)ADDPD, (V)ADDPS, (V)ADDSUBPD, (V)ADDSUBPS, (V)CMPPD, (V)CMPPS, (V)CVTDQ2PS, (V)CVTPD2DQ,<br>(V)CVTPD2PS, (V)CVTPS2DQ, (V)CVTTPD2DQ, (V)CVTTPS2DQ, (V)DIVPD, (V)DIVPS, (V)DPPD*, (V)DPPS*,<br>VFMADD132PD, VFMADD213PD, VFMADD231PD, VFMADD132PS, VFMADD213PS, VFMADD231PS,<br>VFMADDSUB132PD, VFMADDSUB213PD, VFMADDSUB231PD, VFMADDSUB132PS, VFMADDSUB213PS,<br>VFMADDSUB231PS, VFMSUBADD132PD, VFMSUBADD213PD, VFMSUBADD231PD, VFMSUBADD132PS,<br>VFMSUBADD213PS, VFMSUBADD231PS, VFMSUB132PD, VFMSUB213PD, VFMSUB231PD, VFMSUB132PS,<br>VFMSUB213PS, VFMSUB231PS, VFNMADD132PD, VFNMADD213PD, VFNMADD231PD, VFNMADD132PS,<br>VFNMADD213PS, VFNMADD231PS, VFNMSUB132PD, VFNMSUB213PD, VFNMSUB231PD, VFNMSUB132PS,<br>VFNMSUB213PS, VFNMSUB231PS, (V)HADDPD, (V)HADDPS, (V)HSUBPD, (V)HSUBPS, (V)MAXPD, (V)MAXPS,<br>(V)MINPD, (V)MINPS, (V)MULPD, (V)MULPS, (V)ROUNDPD, (V)ROUNDPS, (V)SQRTPD, (V)SQRTPS, (V)SUBPD,<br>(V)SUBPS|
|Type 3|(V)ADDSD, (V)ADDSS, (V)CMPSD, (V)CMPSS, (V)COMISD, (V)COMISS, (V)CVTPS2PD, (V)CVTSD2SI, (V)CVTSD2SS,<br>(V)CVTSI2SD, (V)CVTSI2SS, (V)CVTSS2SD, (V)CVTSS2SI, (V)CVTTSD2SI, (V)CVTTSS2SI, (V)DIVSD, (V)DIVSS,<br>VFMADD132SD, VFMADD213SD, VFMADD231SD, VFMADD132SS, VFMADD213SS, VFMADD231SS,<br>VFMSUB132SD, VFMSUB213SD, VFMSUB231SD, VFMSUB132SS, VFMSUB213SS, VFMSUB231SS,<br>VFNMADD132SD, VFNMADD213SD, VFNMADD231SD, VFNMADD132SS, VFNMADD213SS, VFNMADD231SS,<br>VFNMSUB132SD, VFNMSUB213SD, VFNMSUB231SD, VFNMSUB132SS, VFNMSUB213SS, VFNMSUB231SS,<br>(V)MAXSD, (V)MAXSS, (V)MINSD, (V)MINSS, (V)MULSD, (V)MULSS, (V)ROUNDSD, (V)ROUNDSS, (V)SQRTSD,<br>(V)SQRTSS, (V)SUBSD, (V)SUBSS, (V)UCOMISD, (V)UCOMISS|
|Type 4|(V)AESDEC, (V)AESDECLAST, (V)AESENC, (V)AESENCLAST, (V)AESIMC, (V)AESKEYGENASSIST, (V)ANDPD,<br>(V)ANDPS, (V)ANDNPD, (V)ANDNPS, (V)BLENDPD, (V)BLENDPS, VBLENDVPD, VBLENDVPS, (V)LDDQU***,<br>(V)MASKMOVDQU, (V)PTEST, VTESTPS, VTESTPD, (V)MOVDQU*, (V)MOVSHDUP, (V)MOVSLDUP, (V)MOVUPD*,<br>(V)MOVUPS*, (V)MPSADBW, (V)ORPD, (V)ORPS, (V)PABSB, (V)PABSW, (V)PABSD, (V)PACKSSWB, (V)PACKSSDW,<br>(V)PACKUSWB, (V)PACKUSDW, (V)PADDB, (V)PADDW, (V)PADDD, (V)PADDQ, (V)PADDSB, (V)PADDSW,<br>(V)PADDUSB, (V)PADDUSW, (V)PALIGNR, (V)PAND, (V)PANDN, (V)PAVGB, (V)PAVGW, (V)PBLENDVB,<br>(V)PBLENDW, (V)PCMP(E/I)STRI/M***, (V)PCMPEQB, (V)PCMPEQW, (V)PCMPEQD, (V)PCMPEQQ, (V)PCMPGTB,<br>(V)PCMPGTW, (V)PCMPGTD, (V)PCMPGTQ, (V)PCLMULQDQ, (V)PHADDW, (V)PHADDD, (V)PHADDSW,<br>(V)PHMINPOSUW, (V)PHSUBD, (V)PHSUBW, (V)PHSUBSW, (V)PMADDWD, (V)PMADDUBSW, (V)PMAXSB,<br>(V)PMAXSW, (V)PMAXSD, (V)PMAXUB, (V)PMAXUW, (V)PMAXUD, (V)PMINSB, (V)PMINSW, (V)PMINSD,<br>(V)PMINUB, (V)PMINUW, (V)PMINUD, (V)PMULHUW, (V)PMULHRSW, (V)PMULHW, (V)PMULLW, (V)PMULLD,<br>(V)PMULUDQ, (V)PMULDQ, (V)POR, (V)PSADBW, (V)PSHUFB, (V)PSHUFD, (V)PSHUFHW, (V)PSHUFLW, (V)PSIGNB,<br>(V)PSIGNW, (V)PSIGND, (V)PSLLW, (V)PSLLD, (V)PSLLQ, (V)PSRAW, (V)PSRAD, (V)PSRLW, (V)PSRLD, (V)PSRLQ,<br>(V)PSUBB, (V)PSUBW, (V)PSUBD, (V)PSUBQ, (V)PSUBSB, (V)PSUBSW, (V)PSUBUSB, (V)PSUBUSW,<br>(V)PUNPCKHBW, (V)PUNPCKHWD, (V)PUNPCKHDQ, (V)PUNPCKHQDQ, (V)PUNPCKLBW, (V)PUNPCKLWD,<br>(V)PUNPCKLDQ, (V)PUNPCKLQDQ, (V)PXOR, (V)RCPPS, (V)RSQRTPS, (V)SHUFPD, (V)SHUFPS, (V)UNPCKHPD,<br>(V)UNPCKHPS, (V)UNPCKLPD, (V)UNPCKLPS, (V)XORPD, (V)XORPS, VPBLENDD, VPERMD, VPERMPS, VPERMPD,<br>VPERMQ, VPSLLVD, VPSLLVQ, VPSRAVD, VPSRLVD, VPSRLVQ, VPERMILPD, VPERMILPS, VPERM2F128|
|Type 5|(V)CVTDQ2PD, (V)EXTRACTPS, (V)INSERTPS, (V)MOVD, (V)MOVQ, (V)MOVDDUP, (V)MOVLPD, (V)MOVLPS,<br>(V)MOVHPD, (V)MOVHPS, (V)MOVSD, (V)MOVSS, (V)PEXTRB, (V)PEXTRD, (V)PEXTRW, (V)PEXTRQ, (V)PINSRB,<br>(V)PINSRD, (V)PINSRW, (V)PINSRQ, PMOVSXBW, (V)RCPSS, (V)RSQRTSS, (V)PMOVSX/ZX, VLDMXCSR*,<br>VSTMXCSR|
|Type 6|VEXTRACTF128/VEXTRACTFxxxx, VBROADCASTSS, VBROADCASTSD, VBROADCASTF128, VINSERTF128,<br>VMASKMOVPS**, VMASKMOVPD**, VPMASKMOVD, VPMASKMOVQ, VBROADCASTI128, VPBROADCASTB,<br>VPBROADCASTD, VPBROADCASTW, VPBROADCASTQ, VEXTRACTI128, VINSERTI128, VPERM2I128|
|Type 7|(V)MOVLHPS, (V)MOVHLPS, (V)MOVMSKPD, (V)MOVMSKPS, (V)PMOVMSKB, (V)PSLLDQ, (V)PSRLDQ, (V)PSLLW,<br>(V)PSLLD, (V)PSLLQ, (V)PSRAW, (V)PSRAD, (V)PSRLW, (V)PSRLD, (V)PSRLQ|
|Type 8|VZEROALL, VZEROUPPER|
|Type 11|VCVTPH2PS, VCVTPS2PH|
|Type 12|VGATHERDPS, VGATHERDPD, VGATHERQPS, VGATHERQPD, VPGATHERDD, VPGATHERDQ, VPGATHERQD,<br>VPGATHERQQ|



(*) - Additional exception restrictions are present - see the Instruction description for details

2-24 Vol. 2A

INSTRUCTION FORMAT

- (**) - Instruction behavior on alignment check reporting with mask bits of less than all 1s are the same as with mask bits of all 1s, i.e., no alignment checks are performed.

- (***) - PCMPESTRI, PCMPESTRM, PCMPISTRI, PCMPISTRM, and LDDQU instructions do not cause #GP if the memory operand is not aligned to 16-Byte boundary.

Table 2-15 classifies exception behaviors for AVX instructions. Within each class of exception conditions that are listed in Table 2-18 through Table 2-27, certain subsets of AVX instructions may be subject to #UD exception depending on the encoded value of the VEX.L field. Table 2-17 provides supplemental information of AVX instructions that may be subject to #UD exception if encoded with incorrect values in the VEX.W or VEX.L field.

Table 2-16.  #UD Exception and VEX.W=1 Encoding

|Exception Class|#UD If VEX.W = 1 in all modes|#UD If VEX.W = 1 in<br>non-64-bit modes|
|---|---|---|
|Type 1|||
|Type 2|||
|Type 3|||
|Type 4|VBLENDVPD, VBLENDVPS, VPBLENDVB, VTESTPD, VTESTPS, VPBLENDD, VPERMD,<br>VPERMPS, VPERM2I128, VPSRAVD, VPERMILPD, VPERMILPS, VPERM2F128||
|Type 5|||
|Type 6|VEXTRACTF128, VBROADCASTSS, VBROADCASTSD, VBROADCASTF128,<br>VINSERTF128, VMASKMOVPS, VMASKMOVPD, VBROADCASTI128,<br>VPBROADCASTB/W/D, VEXTRACTI128, VINSERTI128||
|Type 7|||
|Type 8|||
|Type 11|VCVTPH2PS, VCVTPS2PH||
|Type 12|||



Vol. 2A 2-25

INSTRUCTION FORMAT

Table 2-17.  #UD Exception and VEX.L Field Encoding

|Exception<br>Class|#UD If VEX.L = 0|#UD If (VEX.L = 1 && AVX2 not present && AVX<br>present)|#UD If (VEX.L = 1 && AVX2<br>present)|
|---|---|---|---|
|Type 1||VMOVNTDQA||
|Type 2||VDPPD|VDPPD|
|Type 3||||
|Type 4||VMASKMOVDQU, VMPSADBW, VPABSB/W/D,<br>VPACKSSWB/DW, VPACKUSWB/DW, VPADDB/W/D,<br>VPADDQ, VPADDSB/W, VPADDUSB/W, VPALIGNR, VPAND,<br>VPANDN, VPAVGB/W, VPBLENDVB, VPBLENDW,<br>VPCMP(E/I)STRI/M, VPCMPEQB/W/D/Q, VPCMPGTB/W/D/Q,<br>VPHADDW/D, VPHADDSW, VPHMINPOSUW, VPHSUBD/W,<br>VPHSUBSW, VPMADDWD, VPMADDUBSW, VPMAXSB/W/D,<br>VPMAXUB/W/D, VPMINSB/W/D, VPMINUB/W/D,<br>VPMULHUW, VPMULHRSW, VPMULHW/LW, VPMULLD,<br>VPMULUDQ, VPMULDQ, VPOR, VPSADBW, VPSHUFB/D,<br>VPSHUFHW/LW, VPSIGNB/W/D, VPSLLW/D/Q, VPSRAW/D,<br>VPSRLW/D/Q, VPSUBB/W/D/Q, VPSUBSB/W,<br>VPUNPCKHBW/WD/DQ, VPUNPCKHQDQ,<br>VPUNPCKLBW/WD/DQ, VPUNPCKLQDQ, VPXOR|VPCMP(E/I)STRI/M,<br>PHMINPOSUW|
|Type 5||VEXTRACTPS, VINSERTPS, VMOVD, VMOVQ, VMOVLPD,<br>VMOVLPS, VMOVHPD, VMOVHPS, VPEXTRB, VPEXTRD,<br>VPEXTRW, VPEXTRQ, VPINSRB, VPINSRD, VPINSRW,<br>VPINSRQ, VPMOVSX/ZX, VLDMXCSR, VSTMXCSR|Same as column 3|
|Type 6|VEXTRACTF128,<br>VPERM2F128,<br>VBROADCASTSD,<br>VBROADCASTF128,<br>VINSERTF128,|||
|Type 7||VMOVLHPS, VMOVHLPS, VPMOVMSKB, VPSLLDQ,<br>VPSRLDQ, VPSLLW, VPSLLD, VPSLLQ, VPSRAW, VPSRAD,<br>VPSRLW, VPSRLD, VPSRLQ|VMOVLHPS, VMOVHLPS|
|Type 8||||
|Type 11||||
|Type 12||||



2-26 Vol. 2A

INSTRUCTION FORMAT

## 2.5.1 Exceptions Type 1 (Aligned Memory Reference)

Table 2-18.  Type 1 Class Exception Conditions

|Exception|Real|Virtual-8086|Protected and<br>Compatibility|64-bit|Cause of Exception|
|---|---|---|---|---|---|
||X|X|||VEX prefix.|
||||X|X|VEX prefix:<br>If XCR0[2:1]?‘11b’.<br>If CR4.OSXSAVE[bit 18]=0.|
|Invalid Opcode,<br>#UD|X|X|X|X|Legacy SSE instruction:<br>If CR0.EM[bit 2] = 1.<br>If CR4.OSFXSR[bit 9] = 0.|
||X|X|X|X|If preceded by a LOCK prefix (F0H).|
||||X|X|If any REX, F2, F3, or 66 prefixes precede a VEX prefix.|
||X|X|X|X|If any corresponding CPUID feature flag is ‘0’.|
|Device Not Avail-<br>able, #NM|X|X|X|X|If CR0.TS[bit 3]=1.|
|Sk #SS0|||X||For an illegal address in the SS segment.|
|tac, ()||||X|If a memory address referencing the SS segment is in a non-canonical form.|
||||X|X|VEX.256: Memory operand is not 32-byte aligned.<br>VEX.128: Memory operand is not 16-byte aligned.|
||X|X|X|X|Legacy SSE: Memory operand is not 16-byte aligned.|
|General Protec-<br>tion, #GP(0)|||X||For an illegal memory operand effective address in the CS, DS, ES, FS or GS seg-<br>ments.|
|||||X|If the memory address is in a non-canonical form.|
||X|X|||If any part of the operand lies outside the effective address space from 0 to FFFFH.|
|Page Fault<br>#PF(fault-code)||X|X|X|For a page fault.|



Vol. 2A 2-27

INSTRUCTION FORMAT

## 2.5.2 Exceptions Type 2 (>=16 Byte Memory Reference, Unaligned)

Table 2-19.  Type 2 Class Exception Conditions

|Exception|Real|Virtual 8086|Protected and<br>Compatibility|64-bit|Cause of Exception|
|---|---|---|---|---|---|
||X|X|||VEX prefix.|
||X|X|X|X|If an unmasked SIMD floating-point exception and CR4.OSXMMEXCPT[bit 10] = 0.|
|Ilid Od|||X|X|VEX prefix:<br>If XCR0[2:1]?‘11b’.<br>If CR4.OSXSAVE[bit 18]=0.|
|nva pcoe,<br>#UD|X|X|X|X|Legacy SSE instruction:<br>If CR0.EM[bit 2] = 1.<br>If CR4.OSFXSR[bit 9] = 0.|
||X|X|X|X|If preceded by a LOCK prefix (F0H).|
||||X|X|If any REX, F2, F3, or 66 prefixes precede a VEX prefix.|
||X|X|X|X|If any corresponding CPUID feature flag is ‘0’.|
|Device Not Avail-<br>able, #NM|X|X|X|X|If CR0.TS[bit 3]=1.|
|Sk #SS0|||X||For an illegal address in the SS segment.|
|tac, ()||||X|If a memory address referencing the SS segment is in a non-canonical form.|
||X|X|X|X|Legacy SSE: Memory operand is not 16-byte aligned.|
|General Protec-|||X||For an illegal memory operand effective address in the CS, DS, ES, FS or GS segments.|
|tion, #GP(0)||||X|If the memory address is in a non-canonical form.|
||X|X|||If any part of the operand lies outside the effective address space from 0 to FFFFH.|
|Page Fault<br>#PF(fault-code)||X|X|X|For a page fault.|
|SIMD Floating-<br>point Exception,<br>#XM|X|X|X|X|If an unmasked SIMD floating-point exception and CR4.OSXMMEXCPT[bit 10] = 1.|



2-28 Vol. 2A

INSTRUCTION FORMAT

## 2.5.3 Exceptions Type 3 (<16 Byte Memory Argument)

Table 2-20.  Type 3 Class Exception Conditions

|Exception|Real|Virtual-8086|Protected and<br>Compatibility|64-bit|Cause of Exception|
|---|---|---|---|---|---|
||X|X|||VEX prefix.|
||X|X|X|X|If an unmasked SIMD floating-point exception and CR4.OSXMMEXCPT[bit 10] = 0.|
||||X|X|VEX prefix:<br>If XCR0[2:1]?‘11b’.<br>If CR4.OSXSAVE[bit 18]=0.|
|Invalid Opcode, #UD|X|X|X|X|Legacy SSE instruction:<br>If CR0.EM[bit 2] = 1.<br>If CR4.OSFXSR[bit 9] = 0.|
||X|X|X|X|If preceded by a LOCK prefix (F0H).|
||||X|X|If any REX, F2, F3, or 66 prefixes precede a VEX prefix.|
||X|X|X|X|If any corresponding CPUID feature flag is ‘0’.|
|Device Not Available,<br>#NM|X|X|X|X|If CR0.TS[bit 3]=1.|
|Stk #SS0|||X||For an illegal address in the SS segment.|
|ac, ()||||X|If a memory address referencing the SS segment is in a non-canonical form.|
||||X||For an illegal memory operand effective address in the CS, DS, ES, FS or GS seg-<br>ments.|
|General Protection,<br>#GP(0)||||X|If the memory address is in a non-canonical form.|
||X|X|||If any part of the operand lies outside the effective address space from 0 to<br>FFFFH.|
|Page Fault<br>#PF(fault-code)||X|X|X|For a page fault.|
|Alignment Check<br>#AC(0)||X|X|X|For 2, 4, or 8 byte memory access if alignment checking is enabled and an<br>unaligned memory access is made while the current privilege level is 3.|
|SIMD Floating-point<br>Exception, #XM|X|X|X|X|If an unmasked SIMD floating-point exception and CR4.OSXMMEXCPT[bit 10] = 1.|



Vol. 2A 2-29

INSTRUCTION FORMAT

## 2.5.4 Exceptions Type 4 (>=16 Byte Mem Arg, No Alignment, No Floating-point Exceptions)

Table 2-21.  Type 4 Class Exception Conditions

|Exception|Real|Virtual-8086|Protected and<br>Compatibility|64-bit|Cause of Exception|
|---|---|---|---|---|---|
||X|X|||VEX prefix.|
||||X|X|VEX prefix:<br>If XCR0[2:1]?‘11b’.<br>If CR4.OSXSAVE[bit 18]=0.|
|Invalid Opcode, #UD|X|X|X|X|Legacy SSE instruction:<br>If CR0.EM[bit 2] = 1.<br>If CR4.OSFXSR[bit 9] = 0.|
||X|X|X|X|If preceded by a LOCK prefix (F0H).|
||||X|X|If any REX, F2, F3, or 66 prefixes precede a VEX prefix.|
||X|X|X|X|If any corresponding CPUID feature flag is ‘0’.|
|Device Not Available,<br>#NM|X|X|X|X|If CR0.TS[bit 3]=1.|
|Stack #SS0|||X||For an illegal address in the SS segment.|
|, ()||||X|If a memory address referencing the SS segment is in a non-canonical form.|
||X|X|X|X|Legacy SSE: Memory operand is not 16-byte aligned.<sup>1</sup>|
|General Protection,|||X||For an illegal memory operand effective address in the CS, DS, ES, FS or GS seg-<br>ments.|
|#GP(0)||||X|If the memory address is in a non-canonical form.|
||X|X|||If any part of the operand lies outside the effective address space from 0 to<br>FFFFH.|
|Page Fault<br>#PF(fault-code)||X|X|X|For a page fault.|



NOTES:

1. LDDQU, MOVUPD, MOVUPS, PCMPESTRI, PCMPESTRM, PCMPISTRI, and PCMPISTRM instructions do not cause #GP if the memory operand is not aligned to 16-Byte boundary.

2-30 Vol. 2A

INSTRUCTION FORMAT

## 2.5.5 Exceptions Type 5 (<16 Byte Mem Arg and No FP Exceptions)

Table 2-22.  Type 5 Class Exception Conditions

|Exception|Real|Virtual-8086|Protected and<br>Compatibility|64-bit|Cause of Exception|
|---|---|---|---|---|---|
||X|X|||VEX prefix.|
||||X|X|VEX prefix:<br>If XCR0[2:1]?‘11b’.<br>If CR4.OSXSAVE[bit 18]=0.|
|Invalid Opcode, #UD|X|X|X|X|Legacy SSE instruction:<br>If CR0.EM[bit 2] = 1.<br>If CR4.OSFXSR[bit 9] = 0.|
||X|X|X|X|If preceded by a LOCK prefix (F0H).|
||||X|X|If any REX, F2, F3, or 66 prefixes precede a VEX prefix.|
||X|X|X|X|If any corresponding CPUID feature flag is ‘0’.|
|Device Not Available,<br>#NM|X|X|X|X|If CR0.TS[bit 3]=1.|
|Stk #SS0|||X||For an illegal address in the SS segment.|
|ac, ()||||X|If a memory address referencing the SS segment is in a non-canonical form.|
||||X||For an illegal memory operand effective address in the CS, DS, ES, FS or GS seg-<br>ments.|
|General Protection,<br>#GP(0)||||X|If the memory address is in a non-canonical form.|
||X|X|||If any part of the operand lies outside the effective address space from 0 to<br>FFFFH.|
|Page Fault<br>#PF(fault-code)||X|X|X|For a page fault.|
|Alignment Check<br>#AC(0)||X|X|X|For 2, 4, or 8 byte memory access if alignment checking is enabled and an<br>unaligned memory access is made while the current privilege level is 3.|



Vol. 2A 2-31

INSTRUCTION FORMAT

## 2.5.6 Exceptions Type 6 (VEX-Encoded Instructions without Legacy SSE Analogues) Note: At present, the AVX instructions in this category do not generate floating-point exceptions.

Table 2-23.  Type 6 Class Exception Conditions

|Exception|Real|Virtual-8086|Protected and<br>Compatibility|64-bit|Cause of Exception|
|---|---|---|---|---|---|
||X|X|||VEX prefix.|
||||X|X|If XCR0[2:1]?‘11b’.<br>If CR4.OSXSAVE[bit 18]=0.|
|Invalid Opcode, #UD|||X|X|If preceded by a LOCK prefix (F0H).|
||||X|X|If any REX, F2, F3, or 66 prefixes precede a VEX prefix.|
||||X|X|If any corresponding CPUID feature flag is ‘0’.|
|Device Not Available,<br>#NM|||X|X|If CR0.TS[bit 3]=1.|
|Sk #SS0|||X||For an illegal address in the SS segment.|
|tac, ()||||X|If a memory address referencing the SS segment is in a non-canonical form.|
|General Protection,<br>#GP0|||X||For an illegal memory operand effective address in the CS, DS, ES, FS or GS seg-<br>ments.|
|()||||X|If the memory address is in a non-canonical form.|
|Page Fault<br>#PF(fault-code)|||X|X|For a page fault.|
|Alignment Check<br>#AC(0)|||X|X|For 2, 4, or 8 byte memory access if alignment checking is enabled and an<br>unaligned memory access is made while the current privilege level is 3.|



2-32 Vol. 2A

INSTRUCTION FORMAT

## 2.5.7 Exceptions Type 7 (No FP Exceptions, No Memory Arg)

Table 2-24.  Type 7 Class Exception Conditions

|Exception|Real|Virtual-8086|Protected and<br>Compatibility|64-bit|Cause of Exception|
|---|---|---|---|---|---|
||X|X|||VEX prefix.|
||||X|X|VEX prefix:<br>If XCR0[2:1]?‘11b’.<br>If CR4.OSXSAVE[bit 18]=0.|
|Invalid Opcode, #UD|X|X|X|X|Legacy SSE instruction:<br>If CR0.EM[bit 2] = 1.<br>If CR4.OSFXSR[bit 9] = 0.|
||X|X|X|X|If preceded by a LOCK prefix (F0H).|
||||X|X|If any REX, F2, F3, or 66 prefixes precede a VEX prefix.|
||X|X|X|X|If any corresponding CPUID feature flag is ‘0’.|
|Device Not Available,<br>#NM|||X|X|If CR0.TS[bit 3]=1.|
|.5.8<br>Except<br>Exception|ions<br>Real|Type<br>Virtual-8086|8 (AV<br>Tabl<br>Protected and<br>Compatibility|X a<br>e 2-<br>64-bit|nd No Memory Argument)<br>25.  Type 8 Class Exception Conditions<br>Cause of Exception|
|Invalid Opcode, #UD|X|X|||Always in Real or Virtual-8086 mode.|
||||X|X|If XCR0[2:1]?‘11b’.<br>If CR4.OSXSAVE[bit 18]=0.<br>If CPUID.01H.ECX.AVX[bit 28]=0.<br>If VEX.vvvv?1111B.|
||X|X|X|X|If proceeded by a LOCK prefix (F0H).|
|Device Not Available,<br>#NM|||X|X|If CR0.TS[bit 3]=1.|



## 2.5.8 Exceptions Type 8 (AVX and No Memory Argument)

Vol. 2A 2-33

INSTRUCTION FORMAT

## 2.5.9 Exceptions Type 11 (VEX-only, Mem Arg, No AC, Floating-point Exceptions)

Table 2-26.  Type 11 Class Exception Conditions

|Exception|Real|Virtual-8086|Protected and<br>Compatibility|64-bit|Cause of Exception|
|---|---|---|---|---|---|
|Invalid Opcode, #UD|X|X|||VEX prefix.|
||||X|X|VEX prefix:<br>If XCR0[2:1]?‘11b’.<br>If CR4.OSXSAVE[bit 18]=0.|
||X|X|X|X|If preceded by a LOCK prefix (F0H).|
||||X|X|If any REX, F2, F3, or 66 prefixes precede a VEX prefix.|
||X|X|X|X|If any corresponding CPUID feature flag is ‘0’.|
|Device Not Avail-<br>able, #NM|X|X|X|X|If CR0.TS[bit 3]=1.|
|Stack, #SS(0)|||X||For an illegal address in the SS segment.|
|||||X|If a memory address referencing the SS segment is in a non-canonical form.|
|General Protection,<br>#GP(0)|||X||For an illegal memory operand effective address in the CS, DS, ES, FS or GS seg-<br>ments.|
|||||X|If the memory address is in a non-canonical form.|
||X|X|||If any part of the operand lies outside the effective address space from 0 to<br>FFFFH.|
|Page Fault #PF<br>(fault-code)||X|X|X|For a page fault.|
|SIMD Floating-Point<br>Exception, #XM|X|X|X|X|If an unmasked SIMD floating-point exception and CR4.OSXMMEXCPT[bit 10] = 1.|



2-34 Vol. 2A

INSTRUCTION FORMAT

## 2.5.10 Exceptions Type 12 (VEX-only, VSIB Mem Arg, No AC, No Floating-point Exceptions)

Table 2-27.  Type 12 Class Exception Conditions

|Exception|Real|Virtual-8086|Protected and<br>Compatibility|64-bit|Cause of Exception|
|---|---|---|---|---|---|
|Invalid Opcode, #UD|X|X|||VEX prefix.|
||||X|X|VEX prefix:<br>If XCR0[2:1]?‘11b’.<br>If CR4.OSXSAVE[bit 18]=0.|
||X|X|X|X|If preceded by a LOCK prefix (F0H).|
||||X|X|If any REX, F2, F3, or 66 prefixes precede a VEX prefix.|
||X|X|X|NA|If address size attribute is 16 bit.|
||X|X|X|X|If ModR/M.mod = ‘11b’.|
||X|X|X|X|If ModR/M.rm?‘100b’.|
||X|X|X|X|If any corresponding CPUID feature flag is ‘0’.|
||X|X|X|X|If any vector register is used more than once between the destination register,<br>mask register and the index register in VSIB addressing.|
|Device Not Available,<br>#NM|X|X|X|X|If CR0.TS[bit 3]=1.|
|Stack, #SS(0)|||X||For an illegal address in the SS segment.|
|||||X|If a memory address referencing the SS segment is in a non-canonical form.|
|General Protection,<br>#GP(0)|||X||For an illegal memory operand effective address in the CS, DS, ES, FS or GS seg-<br>ments.|
|||||X|If the memory address is in a non-canonical form.|
||X|X|||If any part of the operand lies outside the effective address space from 0 to<br>FFFFH.|
|Page Fault #PF (fault-<br>code)||X|X|X|For a page fault.|



# 2.6 VEX ENCODING SUPPORT FOR GPR INSTRUCTIONS

VEX prefix may be used to encode instructions that operate on neither YMM nor XMM registers. VEX-encoded general-purpose-register instructions have the following properties:

- Instruction syntax support for three encodable operands.

- Encoding support for instruction syntax of non-destructive source operand, destination operand encoded via VEX.vvvv, and destructive three-operand syntax.

- Elimination of escape opcode byte (0FH), two-byte escape via a compact bit field representation within the VEX prefix.

- Elimination of the need to use REX prefix to encode the extended half of general-purpose register sets (R8R15) for direct register access or memory addressing.

- Flexible and more compact bit fields are provided in the VEX prefix to retain the full functionality provided by REX prefix. REX.W, REX.X, REX.B functionalities are provided in the three-byte VEX prefix only.

- VEX-encoded GPR instructions are encoded with VEX.L=0.

Vol. 2A 2-35

INSTRUCTION FORMAT

Any VEX-encoded GPR instruction with a 66H, F2H, or F3H prefix preceding VEX will #UD. Any VEX-encoded GPR instruction with a REX prefix proceeding VEX will #UD. VEX-encoded GPR instructions are not supported in real and virtual 8086 modes.

## 2.6.1 Exceptions Type 13 (VEX-Encoded GPR Instructions)

The exception conditions applicable to VEX-encoded GPR instruction differs from those of legacy GPR instructions. Table 2-28 lists VEX-encoded GPR instructions. The exception conditions for VEX-encoded GRP instructions are found in Table 2-29 for those instructions which have a default operand size of 32 bits and 16-bit operand size is not encodable.

Table 2-28.  VEX-Encoded GPR Instructions

|Exception Class|Instruction|
|---|---|
|Type 13|ANDN, BEXTR, BLSI, BLSMSK, BLSR, BZHI, MULX, PDEP, PEXT, RORX, SARX, SHLX, SHRX|



- (*) - Additional exception restrictions are present - see the Instruction description for details.

Table 2-29.  Type 13 Class Exception Conditions

|Exception|Real|Virtual-8086|Protected and<br>Compatibility|64-bit|Cause of Exception|
|---|---|---|---|---|---|
|Invalid Opcode, #UD|X|X|X|X|If BMI1/BMI2 CPUID feature flag is ‘0’.|
||X|X|||If a VEX prefix is present.|
||X|X|X|X|If VEX.L = 1.|
||X|X|X|X|If preceded by a LOCK prefix (F0H).|
||||X|X|If any REX, F2, F3, or 66 prefixes precede a VEX prefix.|
|Stack, #SS(0)|X|X|X||For an illegal address in the SS segment.|
|||||X|If a memory address referencing the SS segment is in a non-canonical form.|
|General Protection,<br>#GP(0)|||X||For an illegal memory operand effective address in the CS, DS, ES, FS or GS seg-<br>ments.<br>If the DS, ES, FS, or GS register is used to access memory and it contains a null<br>segment selector.|
|||||X|If the memory address is in a non-canonical form.|
||X|X|||If any part of the operand lies outside the effective address space from 0 to<br>FFFFH.|
|Page Fault #PF(fault-<br>code)||X|X|X|For a page fault.|
|Alignment Check<br>#AC(0)||X|X|X|For 2, 4, or 8 byte memory access if alignment checking is enabled and an<br>unaligned memory access is made while the current privilege level is 3.|



# 2.7 INTEL® AVX-512 ENCODING

The majority of the Intel AVX-512 family of instructions (operating on 512/256/128-bit vector register operands) are encoded using a new prefix (called EVEX). Opmask instructions (operating on opmask register operands) are encoded using the VEX prefix. The EVEX prefix has some parts resembling the instruction encoding scheme using the VEX prefix, and many other capabilities not available with the VEX prefix.

2-36 Vol. 2A

INSTRUCTION FORMAT

The significant feature differences between EVEX and VEX are summarized below.

- EVEX is a 4-Byte prefix (the first byte must be 62H); VEX is either a 2-Byte (C5H is the first byte) or 3-Byte (C4H is the first byte) prefix.

- EVEX prefix can encode 32 vector registers (XMM/YMM/ZMM) in 64-bit mode.

- EVEX prefix can encode an opmask register for conditional processing or selection control in EVEX-encoded vector instructions. Opmask instructions, whose source/destination operands are opmask registers and treat the content of an opmask register as a single value, are encoded using the VEX prefix.

- EVEX memory addressing with disp8 form uses a compressed disp8 encoding scheme to improve the encoding density of the instruction byte stream.

- EVEX prefix can encode functionality that are specific to instruction classes (e.g., packed instruction with “load+op” semantic can support embedded broadcast functionality, floating-point instruction with rounding semantic can support static rounding functionality, floating-point instruction with non-rounding arithmetic semantic can support “suppress all exceptions” functionality).

## 2.7.1 Instruction Format and EVEX

The placement of the EVEX prefix in an IA instruction is represented in Figure 2-10. Note that the values contained within brackets are optional.



<!-- Start of picture text -->
# of bytes: 4 1 1 1 2, 4 1<br>[Prefixes] EVEX Opcode ModR/M [SIB] [Disp16,32] [Immediate]<br>1<br>[Disp8*N]<br><!-- End of picture text -->

Figure 2-10.  AVX-512 Instruction Format and the EVEX Prefix

The EVEX prefix is a 4-byte prefix, with the first two bytes derived from unused encoding form of the 32-bit-modeonly BOUND instruction. The layout of the EVEX prefix is shown in Figure 2-11. The first byte must be 62H, followed by three payload bytes, denoted as P0, P1, and P2 individually or collectively as P[23:0] (see Figure 2-11).



<!-- Start of picture text -->
EVEX 62H P0 P1 P2<br>7 6 5 4 3 2 1 0<br>P0 R X B R’ 0 0 m m P[7:0]<br>7 6 5 4 3 2 1 0<br>P1 W v v v v 1 p p P[15:8]<br>7 6 5 4 3 2 1 0<br>P2 z L’ L b V’ a a a P[23:16]<br><!-- End of picture text -->

Figure 2-11.  Bit Field Layout of the EVEX Prefix<sup>1</sup>

NOTES:

1. See Table 2-30 for additional details on bit fields.

Vol. 2A 2-37

INSTRUCTION FORMAT

Table 2-30.  EVEX Prefix Bit Field Functional Grouping

|Notation|Bit field Group|Position|Comment|
|---|---|---|---|
|--|Reserved|P[3 : 2]|Must be 0.|
|--|Fixed Value|P[10]|Must be 1.|
|EVEX.mm|Compressed legacy escape|P[1: 0]|Identical to low two bits of VEX.mmmmm.|
|EVEX.pp|Compressed legacy prefix|P[9 : 8]|Identical to VEX.pp.|
|EVEX.RXB|Next-8 register specifier modifier|P[7 : 5]|Combine with ModR/M.reg, ModR/M.rm (base, index/vidx). This<br>field is encoded in bit inverted format.|
|EVEX.R’|High-16 register specifier modifier|P[4]|Combine with EVEX.R and ModR/M.reg. This bit is stored in<br>inverted format.|
|EVEX.X|High-16 register specifier modifier|P[6]|Combine with EVEX.B and ModR/M.rm, when SIB/VSIB absent.|
|EVEX.vvvv|VVVV register specifier|P[14 : 11]|Same as VEX.vvvv. This field is encoded in bit inverted format.|
|EVEX.V’|High-16 VVVV/VIDX register specifier|P[19]|Combine with EVEX.vvvv or when VSIB present. This bit is<br>stored in inverted format.|
|EVEX.aaa|Embedded opmask register specifier|P[18 : 16]||
|EVEX.W|Osize promotion/Opcode extension|P[15]||
|EVEX.z|Zeroing/Merging|P[23]||
|EVEX.b|Broadcast/RC/SAE Context|P[20]||
|EVEX.L’L|Vector length/RC|P[22 : 21]||



The bit fields in P[23:0] are divided into the following functional groups (Table 2-30 provides a tabular summary):

- Reserved bits: P[3:2] must be 0, otherwise #UD.

- Fixed-value bit: P[10] must be 1, otherwise #UD.

- Compressed legacy prefix/escape bytes: P[1:0] is identical to the lowest 2 bits of VEX.mmmmm; P[9:8] is identical to VEX.pp.

- Operand specifier modifier bits for vector register, general purpose register, memory addressing: P[7:5] allows access to the next set of 8 registers beyond the low 8 registers when combined with ModR/M register specifiers.

- Operand specifier modifier bit for vector register: P[4] (or EVEX.R’) allows access to the high 16 vector register set when combined with P[7] and ModR/M.reg specifier; P[6] can also provide access to a high 16 vector register when SIB or VSIB addressing are not needed.

- Non-destructive source /vector index operand specifier: P[19] and P[14:11] encode the second source vector register operand in a non-destructive source syntax, vector index register operand can access an upper 16 vector register using P[19].

- Op-mask register specifiers: P[18:16] encodes op-mask register set k0-k7 in instructions operating on vector registers.

- EVEX.W: P[15] is similar to VEX.W which serves either as opcode extension bit or operand size promotion to 64-bit in 64-bit mode.

- Vector destination merging/zeroing: P[23] encodes the destination result behavior which either zeroes the masked elements or leave masked element unchanged.

- Broadcast/Static-rounding/SAE context bit: P[20] encodes multiple functionality, which differs across different classes of instructions and can affect the meaning of the remaining field (EVEX.L’L). The functionality for the following instruction classes are:

   - Broadcasting a single element across the destination vector register: this applies to the instruction class with Load+Op semantic where one of the source operand is from memory.

   - Redirect L’L field (P[22:21]) as static rounding control for floating-point instructions with rounding semantic. Static rounding control overrides MXCSR.RC field and implies “Suppress all exceptions” (SAE).

2-38 Vol. 2A

INSTRUCTION FORMAT

   - Enable SAE for floating -point instructions with arithmetic semantic that is not rounding.

   - For instruction classes outside of the afore-mentioned three classes, setting EVEX.b will cause #UD.

- Vector length/rounding control specifier: P[22:21] can serve one of three options.

   - Vector length information for packed vector instructions.

   - Ignored for instructions operating on vector register content as a single data element.

   - Rounding control for floating-point instructions that have a rounding semantic and whose source and destination operands are all vector registers.

## 2.7.2 Register Specifier Encoding and EVEX

EVEX-encoded instruction can access 8 opmask registers, 16 general-purpose registers and 32 vector registers in 64-bit mode (8 general-purpose registers and 8 vector registers in non-64-bit modes). EVEX-encoding can support instruction syntax that access up to 4 instruction operands. Normal memory addressing modes and VSIB memory addressing are supported with EVEX prefix encoding. The mapping of register operands used by various instruction syntax and memory addressing in 64-bit mode are shown in Table 2-31. Opmask register encoding is described in Section 2.7.3.

Table 2-31.  32-Register Support in 64-bit Mode Using EVEX with Embedded REX Bits

||4<sup>1</sup>|3|[2:0]|Reg. Type|Common Usages|
|---|---|---|---|---|---|
|REG|EVEX.R’|REX.R|modrm.reg|GPR, Vector|Destination or Source|
|VVVV|EVEX.V’|EVE|X.vvvv|GPR, Vector|2ndSource or Destination|
|RM|EVEX.X|EVEX.B|modrm.r/m|GPR, Vector|1st Source or Destination|
|BASE|0|EVEX.B|modrm.r/m|GPR|memory addressing|
|INDEX|0|EVEX.X|sib.index|GPR|memory addressing|
|VIDX|EVEX.V’|EVEX.X|sib.index|Vector|VSIB memory addressing|



NOTES:

1. Not applicable for accessing general purpose registers.

The mapping of register operands used by various instruction syntax and memory addressing in 32-bit modes are shown in Table 2-32.

Table 2-32.  EVEX Encoding Register Specifiers in 32-bit Mode

||[2:0]|Reg. Type|Common Usages|
|---|---|---|---|
|REG|modrm.reg|GPR, Vector|Destination or Source|
|VVVV|EVEX.vvv|GPR, Vector|2nd Source or Destination|
|RM|modrm.r/m|GPR, Vector|1st Source or Destination|
|BASE|modrm.r/m|GPR|Memory Addressing|
|INDEX|sib.index|GPR|Memory Addressing|
|VIDX|sib.index|Vector|VSIB Memory Addressing|



## 2.7.3 Opmask Register Encoding

There are eight opmask registers, k0-k7. Opmask register encoding falls into two categories:

- Opmask registers that are the source or destination operands of an instruction treating the content of opmask register as a scalar value, are encoded using the VEX prefix scheme. It can support up to three operands using

Vol. 2A 2-39

INSTRUCTION FORMAT

standard modR/M byte’s reg field and rm field and VEX.vvvv. Such a scalar opmask instruction does not support conditional update of the destination operand.

- An opmask register providing conditional processing and/or conditional update of the destination register of a vector instruction is encoded using EVEX.aaa field (see Section 2.7.4).

- An opmask register serving as the destination or source operand of a vector instruction is encoded using standard modR/M byte’s reg field and rm fields.

Table 2-33.  Opmask Register Specifier Encoding

||[2:0]|Register Access|Common Usages|
|---|---|---|---|
|REG|modrm.reg|k0-k7|Source|
|VVVV|VEX.vvvv|k0-k7|2nd Source|
|RM|modrm.r/m|k0-7|1st Source|
|{k1}|EVEX.aaa|k0<sup>1</sup>-k7|Opmask|



NOTES:

1. Instructions that overwrite the conditional mask in opmask do not permit using k0 as the embedded mask.

## 2.7.4 Masking Support in EVEX

EVEX can encode an opmask register to conditionally control per-element computational operation and updating of result of an instruction to the destination operand. The predicate operand is known as the opmask register. The EVEX.aaa field, P[18:16] of the EVEX prefix, is used to encode one out of a set of eight 64-bit architectural registers. Note that from this set of 8 architectural registers, only k1 through k7 can be addressed as predicate operands. k0 can be used as a regular source or destination but cannot be encoded as a predicate operand. AVX-512 instructions support two types of masking with EVEX.z bit (P[23]) controlling the type of masking:

- Merging-masking, which is the default type of masking for EVEX-encoded vector instructions, preserves the old value of each element of the destination where the corresponding mask bit has a 0. It corresponds to the case of EVEX.z = 0.

- Zeroing-masking, is enabled by having the EVEX.z bit set to 1. In this case, an element of the destination is set to 0 when the corresponding mask bit has a 0 value.

AVX-512 Foundation instructions can be divided into the following groups:

- Instructions which support “zeroing-masking”.

   - Also allow merging-masking.

- Instructions which require aaa = 000.

   - Do not allow any form of masking.

- Instructions which allow merging-masking but do not allow zeroing-masking.

   - Require EVEX.z to be set to 0.

   - This group is mostly composed of instructions that write to memory.

- Instructions which require aaa <> 000 do not allow EVEX.z to be set to 1.

   - Allow merging-masking and do not allow zeroing-masking, e.g., gather instructions.

## 2.7.5 Compressed Displacement (disp8*N) Support in EVEX

For memory addressing using disp8 form, EVEX-encoded instructions always use a compressed displacement scheme by multiplying disp8 in conjunction with a scaling factor N that is determined based on the vector length, the value of EVEX.b bit (embedded broadcast) and the input element size of the instruction. In general, the factor N corresponds to the number of bytes characterizing the internal memory operation of the input operand (e.g., 64 when the accessing a full 512-bit memory vector). The scale factor N is listed in Table 2-34 and Table 2-35 below,

2-40 Vol. 2A

INSTRUCTION FORMAT

where EVEX encoded instructions are classified using the **tupletype** attribute. The scale factor N of each tupletype is listed based on the vector length (VL) and other factors affecting it.

Table 2-34 covers EVEX-encoded instructions which has a load semantic in conjunction with additional computational or data element movement operation, operating either on the full vector or half vector (due to conversion of numerical precision from a wider format to narrower format). EVEX.b is supported for such instructions for data element sizes which are either dword or qword (see Section 2.7.11).

EVEX-encoded instruction that are pure load/store, and “Load+op” instruction semantic that operate on data element size less then dword do not support broadcasting using EVEX.b. These are listed in Table 2-35. Table 2-35 also includes many broadcast instructions which perform broadcast using a subset of data elements without using EVEX.b. These instructions and a few data element size conversion instruction are covered in Table 2-35. Instruction classified in Table 2-35 do not use EVEX.b and EVEX.b must be 0, otherwise #UD will occur.

The tupletype will be referenced in the instruction operand encoding table in the reference page of each instruction, providing the cross reference for the scaling factor N to encoding memory addressing operand.

Note that the disp8*N rules still apply when using 16b addressing.

Table 2-34.  Compressed Displacement (DISP8*N) Affected by Embedded Broadcast

|TupleType|EVEX.b|InputSize|EVEX.W|Broadcast|N (VL=128)|N (VL=256)|N (VL= 512)|Comment|
|---|---|---|---|---|---|---|---|---|
||0|32bit|0|none|16|32|64||
|Fll|1|32bit|0|{1tox}|4|4|4|Load+Op (Full Vector|
|u|0|64bit|1|none|16|32|64|Dword/Qword)|
||1|64bit|1|{1tox}|8|8|8||
|Hlf|0|32bit|0|none|8|16|32|Ld+O Hlf V|
|a|1|32bit|0|{1tox}|4|4|4|oap (a ector)|



Table 2-35.  EVEX DISP8*N for Instructions Not Affected by Embedded Broadcast

|TupleType|InputSize|EVEX.W|N(VL= 128)|N(VL= 256)|N(VL= 512)|Comment|
|---|---|---|---|---|---|---|
|Full Mem|N/A|N/A|16|32|64|Load/store or subDword full vector|
||8bit|N/A|1|1|1||
|Tl1 Sl|16bit|N/A|2|2|2|1Tl|
|upe caar|32bit|0|4|4|4|upe|
||64bit|1|8|8|8||
|Tl1 Fid|32bit|N/A|4|4|4|1 Tuple, memsize not affected by|
|upe xe|64bit|N/A|8|8|8|EVEX.W|
|Tl2|32bit|0|8|8|8|Bdt 2 lt|
|upe|64bit|1|NA|16|16|roacas ( eemens)|
|Tl4|32bit|0|NA|16|16|Bd 4 l|
|upe|64bit|1|NA|NA|32|roacast ( eements)|
|Tuple8|32bit|0|NA|NA|32|Broadcast (8 elements)|
|Half Mem|N/A|N/A|8|16|32|SubQword Conversion|
|Quarter Mem|N/A|N/A|4|8|16|SubDword Conversion|
|Eighth Mem|N/A|N/A|2|4|8|SubWord Conversion|
|Mem128|N/A|N/A|16|16|16|Shift count from memory|
|MOVDDUP|N/A|N/A|8|32|64|VMOVDDUP|



Vol. 2A 2-41

INSTRUCTION FORMAT

## 2.7.6 EVEX Encoding of Broadcast/Rounding/SAE Support

EVEX.b can provide three types of encoding context, depending on the instruction classes:

- Embedded broadcasting of one data element from a source memory operand to the destination for vector instructions with “load+op” semantic.

- Static rounding control overriding MXCSR.RC for floating-point instructions with rounding semantic.

- “Suppress All exceptions” (SAE) overriding MXCSR mask control for floating-point arithmetic instructions that do not have rounding semantic.

## 2.7.7 Embedded Broadcast Support in EVEX

EVEX encodes an embedded broadcast functionality that is supported on many vector instructions with 32-bit (double word or single precision floating-point) and 64-bit data elements, and when the source operand is from memory. EVEX.b (P[20]) bit is used to enable broadcast on load-op instructions. When enabled, only one element is loaded from memory and broadcasted to all other elements instead of loading the full memory size. The following instruction classes do not support embedded broadcasting:

- Instructions with only one scalar result is written to the vector destination.

- Instructions with explicit broadcast functionality provided by its opcode.

- Instruction semantic is a pure load or a pure store operation.

## 2.7.8 Static Rounding Support in EVEX

Static rounding control embedded in the EVEX encoding system applies only to register-to-register flavor of floating-point instructions with rounding semantic at two distinct vector lengths: (i) scalar, (ii) 512-bit. In both cases, the field EVEX.L’L expresses rounding mode control overriding MXCSR.RC if EVEX.b is set. When EVEX.b is set, “suppress all exceptions” is implied. The processor behaves as if all MXCSR masking controls are set.

## 2.7.9 SAE Support in EVEX

The EVEX encoding system allows arithmetic floating-point instructions without rounding semantic to be encoded with the SAE attribute. This capability applies to scalar and 512-bit vector lengths, register-to-register only, by setting EVEX.b. When EVEX.b is set, “suppress all exceptions” is implied. The processor behaves as if all MXCSR masking controls are set.

## 2.7.10 Vector Length Orthogonality

The architecture of EVEX encoding scheme can support SIMD instructions operating at multiple vector lengths. Many AVX-512 Foundation instructions operate at 512-bit vector length. The vector length of EVEX encoded vector instructions are generally determined using the L’L field in EVEX prefix, except for 512-bit floating-point, reg-reg instructions with rounding semantic. The table below shows the vector length corresponding to various values of the L’L bits. When EVEX is used to encode scalar instructions, L’L is generally ignored.

When EVEX.b bit is set for a register-register instructions with floating-point rounding semantic, the same two bits P2[6:5] specifies rounding mode for the instruction, with implied SAE behavior. The mapping of different instruction classes relative to the embedded broadcast/rounding/SAE control and the EVEX.L’L fields are summarized in Table 2-36.

2-42 Vol. 2A

INSTRUCTION FORMAT

Table 2-36.  EVEX Embedded Broadcast/Rounding/SAE and Vector Length on Vector Instructions

|Position|P2[4]|P2[6:5]|P2[6:5]|
|---|---|---|---|
|Broadcast/Rounding/SAE Context|EVEX.b|EVEX.L’L|EVEX.RC|
|Reg-reg, FP Instructions w/ rounding semantic or SAE|Enable static rounding<br>control (SAE implied)|Vector length Implied<br>(512 bit or scalar)|00b: SAE + RNE<br>01b: SAE + RD<br>10b: SAE + RU<br>11b: SAE + RZ|
|Load+op Instructions w/ memory source|Broadcast Control|00b: 128-bit<br>|NA|
|Other Instructions (<br>Explicit Load/Store/Broadcast/Gather/Scatter)|Must be 0 (otherwise<br>#UD)|01b: 256-bit<br>10b: 512-bit<br>11b: Reserved (#UD)|NA|



## 2.7.11 #UD Equations for EVEX

Instructions encoded using EVEX can face three types of UD conditions: state dependent, opcode independent and opcode dependent.

### 2.7.11.1 State Dependent #UD

In general, attempts of execute an instruction, which required OS support for incremental extended state component, will #UD if required state components were not enabled by OS. Table 2-37 lists instruction categories with respect to required processor state components. Attempts to execute a given category of instructions while enabled states were less than the required bit vector in XCR0 shown in Table 2-37 will cause #UD.

Table 2-37.  OS XSAVE Enabling Requirements of Instruction Categories

|**Instruction Categories**|Vector Register State Access|Required XCR0 Bit Vector [7:0]|
|---|---|---|
|Legacy SIMD prefix encoded Instructions (e.g SSE)|XMM|xxxxxx11b|
|VEX-encoded instructions operating on YMM|YMM|xxxxx111b|
|EVEX-encoded 128-bit instructions|ZMM|111xx111b|
|EVEX-encoded 256-bit instructions|ZMM|111xx111b|
|EVEX-encoded 512-bit instructions|ZMM|111xx111b|
|VEX-encoded instructions operating on opmask|k-reg|111xxx11b|



### 2.7.11.2 Opcode Independent #UD

A number of bit fields in EVEX encoded instruction must obey mode-specific but opcode-independent patterns listed in Table 2-38.

Table 2-38.  Opcode Independent, State Dependent EVEX Bit Fields

|Position|Notation|64-bit #UD|Non-64-bit #UD|
|---|---|---|---|
|P[3 : 2]|--|if > 0|if > 0|
|P[10]|--|if 0|if 0|
|P[1: 0]|EVEX.mm|if 00b|if 00b|
|P[7 : 6]|EVEX.RX|None (valid)|None (BOUND if EVEX.RX != 11b)|



Vol. 2A 2-43

INSTRUCTION FORMAT

### 2.7.11.3 Opcode Dependent #UD

This section describes legal values for the rest of the EVEX bit fields. Table 2-39 lists the #UD conditions of EVEX prefix bit fields which encodes or modifies register operands.

Table 2-39.  #UD Conditions of Operand-Encoding EVEX Prefix Bit Fields

|Notation|Position|Operand Encoding|64-bit #UD|Non-64-bit #UD|
|---|---|---|---|---|
|EVEX.R|P[7]|ModRM.reg encodes k-reg|If EVEX.R = 0|None (BOUND if<br>|
|||ModRM.reg is opcode extension|None (ignored)|EVEX.RX != 11b)|
|||ModRM.reg encodes all other registers|None (valid)||
|EVEX.X|P[6]|ModRM.r/m encodes ZMM/YMM/XMM|None (valid)||
|||ModRM.r/m encodes k-reg or GPR|None (ignored)||
|||ModRM.r/m without SIB/VSIB|None (ignored)||
|||ModRM.r/m with SIB/VSIB|None (valid)||
|EVEX.B|P[5]|ModRM.r/m encodes k-reg|None (ignored)|None (ignored)|
|||ModRM.r/m encodes other registers|None (valid)||
|||ModRM.r/m base present|None (valid)||
|||ModRM.r/m base not present|None (ignored)||
|EVEX.R’|P[4]|ModRM.reg encodes k-reg or GPR|If 0|None (ignored)|
|||ModRM.reg is opcode extension|None (ignored)||
|||ModRM.reg encodes ZMM/YMM/XMM|None (valid)||
|EVEX.vvvv|P[14 : 11]|vvvv encodes ZMM/YMM/XMM|None (valid)|None (valid)<br>P[14] ignored|
|||Otherwise|If != 1111b|If != 1111b|
|EVEX.V’|P[19]|Encodes ZMM/YMM/XMM|None (valid)|If 0|
|||Otherwise|If 0|If 0|



Table 2-40 lists the #UD conditions of instruction encoding of opmask register using EVEX.aaa and EVEX.z

Table 2-40.  #UD Conditions of Opmask Related Encoding Field

|Notation|Position|Operand Encoding|64-bit #UD|Non-64-bit #UD|
|---|---|---|---|---|
|EVEX.aaa|P[18 : 16]|Instructions do not use opmask for conditional processing<sup>1</sup>.|If aaa != 000b|If aaa != 000b|
|||Opmask used as conditional processing mask and updated<br>at completion<sup>2</sup>.|If aaa = 000b|If aaa = 000b;|
|||Opmask used as conditional processing.|None (valid<sup>3</sup>)|None (valid<sup>1</sup>)|
|EVEX.z|P[23]|Vector instruction using opmask as source or destination<sup>4</sup>.|If EVEX.z != 0|If EVEX.z != 0|
|||Store instructions or gather/scatter instructions.|If EVEX.z != 0|If EVEX.z != 0|
|||Instructions with EVEX.aaa = 000b.|If EVEX.z != 0|If EVEX.z != 0|
|VEX.vvvv|Varies|K-regs are instruction operands not mask control.|If vvvv = 0xxxb|None|



NOTES:

1. E.g., VPBROADCASTMxxx, VPMOVM2x, VPMOVx2M.

2. E.g., Gather/Scatter family.

3. aaa can take any value. A value of 000 indicates that there is no masking on the instruction; in this case, all elements will be processed as if there was a mask of ‘all ones’ regardless of the actual value in K0.

4. E.g., VFPCLASSPD/PS, VCMPB/D/Q/W family, VPMOVM2x, VPMOVx2M.

2-44 Vol. 2A

INSTRUCTION FORMAT

Table 2-41 lists the #UD conditions of EVEX bit fields that depends on the context of EVEX.b.

Table 2-41.  #UD Conditions Dependent on EVEX.b Context

|Notation|Position|Operand Encoding|64-bit #UD|Non-64-bit #UD|
|---|---|---|---|---|
|EVEX.L’Lb|P[22 : 20]|Reg-reg, FP instructions with rounding semantic.|None (valid<sup>1</sup>)|None (valid<sup>1</sup>)|
|||Other reg-reg, FP instructions that can cause #XM.|None (valid<sup>2</sup>)|None (valid<sup>2</sup>)|
|||Other reg-mem instructions in Table 2-34.|None (valid<sup>3</sup>)|None (valid<sup>3</sup>)|
|||Other instruction classes<sup>4</sup>in Table 2-35.|If EVEX.b = 1|If EVEX.b = 1|



NOTES:

1. L’L specifies rounding control, see Table 2-36, supports {er} syntax.

2. L’L is ignored.

3. L’L specifies vector length, see Table 2-36, supports embedded broadcast syntax

4. L’L specifies either vector length or ignored.

## 2.7.12 Device Not Available

EVEX-encoded instructions follow the same rules when it comes to generating #NM (Device Not Available) exception. In particular, it is generated when CR0.TS[bit 3]= 1.

## 2.7.13 Scalar Instructions

EVEX-encoded scalar SIMD instructions can access up to 32 registers in 64-bit mode. Scalar instructions support masking (using the least significant bit of the opmask register), but broadcasting is not supported.

# 2.8 EXCEPTION CLASSIFICATIONS OF EVEX-ENCODED INSTRUCTIONS

The exception behavior of EVEX-encoded instructions can be classified into the classes shown in the rest of this section. The classification of EVEX-encoded instructions follow a similar framework as those of AVX and AVX2 instructions using the VEX prefix. Exception types for EVEX-encoded instructions are named in the style of “E##” or with a suffix “E##XX”. The “##” designation generally follows that of AVX/AVX2 instructions. The majority of EVEX encoded instruction with “Load+op” semantic supports memory fault suppression, which is represented by E##. The instructions with “Load+op” semantic but do not support fault suppression are named “E##NF”. A summary table of exception classes by class names are shown below.

Table 2-42.  EVEX-Encoded Instruction Exception Class Summary

|Exception Class|Instruction set|Mem arg|(#XM)|
|---|---|---|---|
|Type E1|Vector Moves/Load/Stores|Explicitly aligned, w/ fault suppression|None|
|Type E1NF|Vector Non-temporal Stores|Explicitly aligned, no fault suppression|None|
|Type E2|FP Vector Load+op|Support fault suppression|Yes|
|Type E2NF|FP Vector Load+op|No fault suppression|Yes|
|Type E3|FP Scalar/Partial Vector, Load+Op|Support fault suppression|Yes|
|Type E3NF|FP Scalar/Partial Vector, Load+Op|No fault suppression|Yes|
|Type E4|Integer Vector Load+op|Support fault suppression|No|
|Type E4NF|Integer Vector Load+op|No fault suppression|No|
|Type E5|Legacy-like Promotion|Varies, Support fault suppression|No|
|Type E5NF|Legacy-like Promotion|Varies, No fault suppression|No|



Vol. 2A 2-45

INSTRUCTION FORMAT

Table 2-42.  EVEX-Encoded Instruction Exception Class Summary

|Exception Class|Instruction set|Mem arg|(#XM)|
|---|---|---|---|
|Type E6|Post AVX Promotion|Varies, w/ fault suppression|No|
|Type E6NF|Post AVX Promotion|Varies, no fault suppression|No|
|Type E7NM|Register-to-register op|None|None|
|Type E9NF|Miscellaneous 128-bit|Vector-length Specific, no fault suppression|None|
|Type E10|Non-XF Scalar|Vector Length ignored, w/ fault suppression|None|
|Type E10NF|Non-XF Scalar|Vector Length ignored, no fault suppression|None|
|Type E11|VCVTPH2PS, VCVTPS2PH|Half Vector Length, w/ fault suppression|Yes|
|Type E12|Gather and Scatter Family|VSIB addressing, w/ fault suppression|None|
|Type E12NP|Gather and Scatter Prefetch Family|VSIB addressing, w/o page fault|None|



Table 2-43 lists EVEX-encoded instruction mnemonic by exception classes.

Table 2-43.  EVEX Instructions in Each Exception Class

|Exception Class|Instruction|
|---|---|
|Type E1|VMOVAPD, VMOVAPS, VMOVDQA32, VMOVDQA64|
|Type E1NF|VMOVNTDQ, VMOVNTDQA, VMOVNTPD, VMOVNTPS|
|Type E2|VADDPD, VADDPH, VADDPS, VCMPPD, VCMPPH, VCMPPS, VCVTDQ2PH, VCVTDQ2PS, VCVTPD2DQ, VCVTPD2PH,<br>VCVTPD2PS, VCVTPD2QQ, VCVTPD2UQQ, VCVTPD2UDQ, VCVTPH2DQ, VCVTPH2PD, VCVTPH2QQ, VCVTPH2UDQ,<br>VCVTPH2UQQ, VCVTPH2UW, VCVTPH2W, VCVTPS2DQ, VCVTPS2UDQS, VCVTQQ2PD, VCVTQQ2PH, VCVTQQ2PS,<br>VCVTTPD2DQ, VCVTTPD2QQ, VCVTTPD2UDQ, VCVTTPD2UQQ, VCVTTPH2DQ, VCVTTPH2QQ, VCVTTPH2UDQ,<br>VCVTTPH2UQQ, VCVTTPH2UW, VCVTTPH2W, VCVTTPS2DQ, VCVTTPS2UDQ, VCVTUDQ2PH, VCVTUDQ2PS,<br>VCVTUQQ2PD, VCVTUQQ2PH, VCVTUQQ2PS, VCVTUW2PH, VCVTW2PH, VDIVPD, VDIVPH, VDIVPS, VEXP2PD,<br>VEXP2PS, VFIXUPIMMPD, VFIXUPIMMPS, VFMADDxxxPD, VFMADDxxxPH, VFMADDxxxPS, VFMADDSUBxxxPD,<br>VFMADDSUBxxxPH, VFMADDSUBxxxPS, VFMSUBADDxxxPD, VFMSUBADDxxxPH, VFMSUBADDxxxPS,<br>VFMSUBxxxPD, VFMSUBxxxPH, VFMSUBxxxPS, VFNMADDxxxPD, VFNMADDxxxPH, VFNMADDxxxPS,<br>VFNMSUBxxxPD, VFNMSUBxxxPH, VFNMSUBxxxPS, VGETEXPPD, VGETEXPPH, VGETEXPPS, VGETMANTPD,<br>VGETMANTPH, VGETMANTPS, VGETMANTSH, VMAXPD, VMAXPH, VMAXPS, VMINPD, VMINPH, VMINPS, VMULPD,<br>VMULPH, VMULPS, VRANGEPD, VRANGEPS, VREDUCEPD, VREDUCEPH, VREDUCEPS, VRNDSCALEPD,<br>VRNDSCALEPH, VRNDSCALEPS, VRCP28PD, VRCP28PS, VRSQRT28PD, VRSQRT28PS, VSCALEFPD, VSCALEFPS,<br>VSQRTPD, VSQRTPH, VSQRTPS, VSUBPD,VSUBPH,VSUBPS|
|Type E3|VADDSD, VADDSH, VADDSS, VCMPSD, VCMPSH, VCMPSS, VCVTPS2QQ, VCVTPS2UQQ, VCVTPS2PD, VCVTSD2SH,<br>VCVTSD2SS, VCVTSH2SD, VCVTSH2SS, VCVTSS2SD, VCVTSS2SH, VCVTTPS2QQ, VCVTTPS2UQQ, VDIVSD, VDIVSH,<br>VDIVSS, VFMADDxxxSD, VFMADDxxxSH, VFMADDxxxSS, VFMSUBxxxSD, VFMSUBxxxSH, VFMSUBxxxSS,<br>VFNMADDxxxSD, VFNMADDxxxSH, VFNMADDxxxSS, VFNMSUBxxxSD, VFNMSUBxxxSH, VFNMSUBxxxSS,<br>VFIXUPIMMSD, VFIXUPIMMSS, VGETEXPSD, VGETEXPSH, VGETEXPSS, VGETMANTSD, VGETMANTSH,<br>VGETMANTSS, VMAXSD, VMAXSH, VMAXSS, VMINSD, VMINSH, VMINSS, VMULSD, VMULSH, VMULSS, VRANGESD,<br>VRANGESS, VREDUCESD, VREDUCESH, VREDUCESS, VRNDSCALESD, VRNDSCALESH, VRNDSCALESS, VSCALEFSD,<br>VSCALEFSH, VSCALEFSS, VRCP28SD, VRCP28SS, VRSQRT28SD, VRSQRT28SS, VSQRTSD, VSQRTSH, VSQRTSS,<br>VSUBSD, VSUBSH, VSUBSS|
|Type E3NF|VCOMISD, VCOMISH, VCOMISS, VCVTSD2SI, VCVTSD2USI, VCVTSH2SI, VCVTSH2USI, VCVTSI2SD, VCVTSI2SH,<br>VCVTSI2SS, VCVTSS2SI, VCVTSS2USI, VCVTTSD2SI, VCVTTSD2USI, VCVTTSH2SI, VCVTTSH2USI, VCVTTSS2SI,<br>VCVTTSS2USI, VCVTUSI2SD, VCVTUSI2SH, VCVTUSI2SS, VUCOMISD, VUCOMISH, VUCOMISS|



2-46 Vol. 2A

INSTRUCTION FORMAT

Table 2-43.  EVEX Instructions in Each Exception Class (Contd.)

|Exception Class|Instruction|
|---|---|
|Type E4|VANDPD, VANDPS, VANDNPD, VANDNPS, VBLENDMPD, VBLENDMPS, VFCMADDCPH, VFCMULCPH, VFMADDCPH,<br>VFMULCPH, VFPCLASSPD, VFPCLASSPH, VFPCLASSPS, VORPD, VORPS, VPABSD, VPABSQ, VPADDD, VPADDQ,<br>VPANDD, VPANDQ, VPANDND, VPANDNQ, VPBLENDMB, VPBLENDMD, VPBLENDMQ, VPBLENDMW, VPCMPD,<br>VPCMPEQD, VPCMPEQQ, VPCMPGTD, VPCMPGTQ, VPCMPQ, VPCMPUD, VPCMPUQ, VPLZCNTD, VPLZCNTQ,<br>VPMADD52LUQ, VPMADD52HUQ, VPMAXSD, VPMAXSQ, VPMAXUD, VPMAXUQ, VPMINSD, VPMINSQ, VPMINUD,<br>VPMINUQ, VPMULLD, VPMULLQ, VPMULUDQ, VPMULDQ, VPORD, VPORQ, VPROLD, VPROLQ, VPROLVD, VPROLVQ,<br>VPRORD, VPRORQ, VPRORVD, VPRORVQ, (VPSLLD, VPSLLQ, VPSRAD, VPSRAQ, VPSRAVW, VPSRAVD, VPSRAVW,<br>VPSRAVQ, VPSRLD, VPSRLQ)<sup>1</sup>, VPSUBD, VPSUBQ, VPSUBUSB, VPSUBUSW, VPTERNLOGD, VPTERNLOGQ,<br>VPTESTMD, VPTESTMQ, VPTESTNMD, VPTESTNMQ, VPXORD, VPXORQ, VPSLLVD, VPSLLVQ, VRCP14PD,<br>VRCP14PS, VRCPPH, VRSQRT14PD, VRSQRT14PS, VRSQRTPH, VXORPD, VXORPS|
|E4.nb<sup>2</sup>|VCOMPRESSPD, VCOMPRESSPS, VEXPANDPD, VEXPANDPS, VMOVDQU8, VMOVDQU16, VMOVDQU32,<br>VMOVDQU64, VMOVUPD, VMOVUPS, VPABSB, VPABSW, VPADDB, VPADDW, VPADDSB, VPADDSW, VPADDUSB,<br>VPADDUSW, VPAVGB, VPAVGW, VPCMPB, VPCMPEQB, VPCMPEQW, VPCMPGTB, VPCMPGTW, VPCMPW, VPCMPUB,<br>VPCMPUW, VPCOMPRESSD, VPCOMPRESSQ, VPEXPANDD, VPEXPANDQ, VPMAXSB, VPMAXSW, VPMAXUB,<br>VPMAXUW, VPMINSB, VPMINSW, VPMINUB, VPMINUW, VPMULHRSW, VPMULHUW, VPMULHW, VPMULLW,<br>VPSLLVW, VPSLLW, VPSRAW, VPSRLVW, VPSRLW, VPSUBB, VPSUBW, VPSUBSB, VPSUBSW, VPTESTMB,<br>VPTESTMW, VPTESTNMB, VPTESTNMW|
|Type E4NF|VALIGND, VALIGNQ, VPACKSSDW, VPACKUSDW, VPCONFLICTD, VPCONFLICTQ, VPERMD, VPERMI2D, VPERMI2PS,<br>VPERMI2PD, VPERMI2Q, VPERMPD, VPERMPS, VPERMQ, VPERMT2D, VPERMT2PS, VPERMT2Q, VPERMT2PD,<br>VPERMILPD, VPERMILPS, VPMULTISHIFTQB, VPSHUFD, VPUNPCKHDQ, VPUNPCKHQDQ, VPUNPCKLDQ,<br>VPUNPCKLQDQ, VSHUFF32X4, VSHUFF64X2, VSHUFI32X4, VSHUFI64X2, VSHUFPD, VSHUFPS, VUNPCKHPD,<br>VUNPCKHPS, VUNPCKLPD, VUNPCKLPS|
|E4NF.nb<sup>2</sup>|VDBPSADBW, VPACKSSWB, VPACKUSWB, VPALIGNR, VPMADDWD, VPMADDUBSW, VMOVSHDUP, VMOVSLDUP,<br>VPSADBW, VPSHUFB, VPSHUFHW, VPSHUFLW, VPSLLDQ, VPSRLDQ, VPSLLW, VPSRAW, VPSRLW, (VPSLLD,<br>VPSLLQ, VPSRAD, VPSRAQ, VPSRLD, VPSRLQ)<sup>3</sup>, VPUNPCKHBW, VPUNPCKHWD, VPUNPCKLBW, VPUNPCKLWD,<br>VPERMW, VPERMI2W, VPERMT2W|
|Type E5|PMOVSXBW, PMOVSXBW, PMOVSXBD, PMOVSXBQ, PMOVSXWD, PMOVSXWQ, PMOVSXDQ, PMOVZXBW,<br>PMOVZXBD, PMOVZXBQ, PMOVZXWD, PMOVZXWQ, PMOVZXDQ, VCVTDQ2PD, VCVTUDQ2PD, VMOVSH,<br>VPMOVSXxx, VPMOVZXxx,|
|Type E5NF|VMOVDDUP|
|Type E6|VBROADCASTF32X2, VBROADCASTF32X4, VBROADCASTF64X2, VBROADCASTF32X8, VBROADCASTF64X4,<br>VBROADCASTI32X2, VBROADCASTI32X4, VBROADCASTI64X2, VBROADCASTI32X8, VBROADCASTI64X4,<br>VBROADCASTSD, VBROADCASTSS, VFPCLASSSD, VFPCLASSSS, VPBROADCASTB, VPBROADCASTD,<br>VPBROADCASTW, VPBROADCASTQ, VPMOVQB, VPMOVSQB, VPMOVUSQB, VPMOVQW, VPMOVSQW, VPMOVUSQW,<br>VPMOVQD, VPMOVSQD, VPMOVUSQD, VPMOVDB, VPMOVSDB, VPMOVUSDB, VPMOVDW, VPMOVSDW,<br>VPMOVUSDW, VPMOVWB, VPMOVSWB, VPMOVUSWB|
|Type E6NF|VEXTRACTF32X4, VEXTRACTF32X8, VEXTRACTF64X2, VEXTRACTF64X4, VEXTRACTI32X4, VEXTRACTI32X8,<br>VEXTRACTI64X2, VEXTRACTI64X4, VINSERTF32X4, VINSERTF32X8, VINSERTF64X2, VINSERTF64X4,<br>VINSERTI32X4, VINSERTI32X8, VINSERTI64X2, VINSERTI64X4, VPBROADCASTMB2Q, VPBROADCASTMW2D|
|Type<br>E7NM.128<sup>4</sup>|VMOVHLPS, VMOVLHPS|
|Type E7NM.|(VPBROADCASTD, VPBROADCASTQ, VPBROADCASTB, VPBROADCASTW)<sup>5</sup>, VPMOVB2M, VPMOVD2M, VPMOVM2B,<br>VPMOVM2D, VPMOVM2Q, VPMOVM2W, VPMOVQ2M, VPMOVW2M|
|Type E9NF|VEXTRACTPS, VINSERTPS, VMOVHPD, VMOVHPS, VMOVLPD, VMOVLPS, VMOVD, VMOVQ, VMOVW, VPEXTRB,<br>VPEXTRD, VPEXTRW, VPEXTRQ, VPINSRB, VPINSRD, VPINSRW, VPINSRQ|
|Type E10|VFCMADDCSH, VFMADDCSH, VFCMULCSH, VFMULCSH, VFPCLASSSH, VMOVSD, VMOVSS, VRCP14SD, VRCP14SS,<br>VRCPSH, VRSQRT14SD, VRSQRT14SS, VRSQRTSH|
|Type E10NF|(VCVTSI2SD, VCVTUSI2SD)<sup>6</sup>|
|Type E11|VCVTPH2PS, VCVTPS2PH|



Vol. 2A 2-47

INSTRUCTION FORMAT

Table 2-43.  EVEX Instructions in Each Exception Class (Contd.)

|Exception Class|Instruction|
|---|---|
|Type E12|VGATHERDPS, VGATHERDPD, VGATHERQPS, VGATHERQPD, VPGATHERDD, VPGATHERDQ, VPGATHERQD,<br>VPGATHERQQ, VPSCATTERDD, VPSCATTERDQ, VPSCATTERQD, VPSCATTERQQ, VSCATTERDPD, VSCATTERDPS,<br>VSCATTERQPD, VSCATTERQPS|
||VGATHERPF0DPD, VGATHERPF0DPS, VGATHERPF0QPD, VGATHERPF0QPS, VGATHERPF1DPD, VGATHERPF1DPS,|
|Type E12NP|VGATHERPF1QPD, VGATHERPF1QPS, VSCATTERPF0DPD, VSCATTERPF0DPS, VSCATTERPF0QPD,<br>VSCATTERPF0QPS, VSCATTERPF1DPD, VSCATTERPF1DPS, VSCATTERPF1QPD, VSCATTERPF1QPS|



NOTES:

1. Operand encoding Full tupletype with immediate.

2. Embedded broadcast is not supported with the “.nb” suffix.

3. Operand encoding Mem128 tupletype.

4. #UD raised if EVEX.L’L !=00b (VL=128).

5. The source operand is a general purpose register.

6. W0 encoding only.

## 2.8.1 Exceptions Type E1 and E1NF of EVEX-Encoded Instructions

EVEX-encoded instructions with memory alignment restrictions, and supporting memory fault suppression follow exception class E1.

Table 2-44.  Type E1 Class Exception Conditions

|Exception|Real|Virtual 80x86|Protected and<br>Compatibility|64-bit|Cause of Exception|
|---|---|---|---|---|---|
||X|X|||If EVEX prefix present.|
|Invalid Opcode,<br>#UD|||X|X|If CR4.OSXSAVE[bit 18]=0.<br>If any one of following conditions applies:<br>•<br>State requirement, Table 2-37 not met.<br>•<br>Opcode independent #UD condition in Table 2-38.<br>•<br>Operand encoding #UD conditions in Table 2-39.<br>•<br>Opmask encoding #UD condition of Table 2-40.<br>•<br>EVEX.b encoding #UD condition of Table 2-41.<br>•<br>Instruction specific EVEX.L'L restriction not met.|
||X|X|X|X|If preceded by a LOCK prefix (F0H).|
||||X|X|If any REX, F2, F3, or 66 prefixes precede a EVEX prefix.|
||X|X|X|X|If any corresponding CPUID feature flag is ‘0’.|



2-48 Vol. 2A

INSTRUCTION FORMAT

Table 2-44.  Type E1 Class Exception Conditions (Contd.)

|Exception|Real|Virtual 80x86|Protected and<br>Compatibility|64-bit|Cause of Exception|
|---|---|---|---|---|---|
|Device Not Avail-<br>able, #NM|X|X|X|X|If CR0.TS[bit 3]=1.|
||||X||If fault suppression not set, and an illegal address in the SS segment.|
|Stack, #SS(0)||||X|If fault suppression not set, and a memory address referencing the SS segment is in<br>a non-canonical form.|
||||X|X|EVEX.512: Memory operand is not 64-byte aligned.<br>EVEX.256: Memory operand is not 32-byte aligned.<br>EVEX.128: Memory operand is not 16-byte aligned.|
|General Protection,<br>#GP(0)|||X||If fault suppression not set, and an illegal memory operand effective address in the<br>CS, DS, ES, FS or GS segments.|
|||||X|If fault suppression not set, and the memory address is in a non-canonical form.|
||X|X|||If fault suppression not set, and any part of the operand lies outside the effective<br>address space from 0 to FFFFH.|
|Page Fault<br>#PF(fault-code)||X|X|X|If fault suppression not set, and a page fault.|



Vol. 2A 2-49

INSTRUCTION FORMAT

EVEX-encoded instructions with memory alignment restrictions, but do not support memory fault suppression follow exception class E1NF.

Table 2-45.  Type E1NF Class Exception Conditions

|Exception|Real|Virtual 80x86|Protected and<br>Compatibility|64-bit|Cause of Exception|
|---|---|---|---|---|---|
||X|X|||If EVEX prefix present.|
|Invalid Opcode,<br>#UD|||X|X|If CR4.OSXSAVE[bit 18]=0.<br>If any one of following conditions applies:<br>•<br>State requirement, Table 2-37 not met.<br>•<br>Opcode independent #UD condition in Table 2-38.<br>•<br>Operand encoding #UD conditions in Table 2-39.<br>•<br>Opmask encoding #UD condition of Table 2-40.<br>•<br>EVEX.b encoding #UD condition of Table 2-41.<br>•<br>Instruction specific EVEX.L'L restriction not met.|
||X|X|X|X|If preceded by a LOCK prefix (F0H).|
||||X|X|If any REX, F2, F3, or 66 prefixes precede a EVEX prefix.|
||X|X|X|X|If any corresponding CPUID feature flag is ‘0’.|
|Device Not Avail-<br>able, #NM|X|X|X|X|If CR0.TS[bit 3]=1.|
||||X||For an illegal address in the SS segment.|
|Stack, #SS(0)||||X|If a memory address referencing the SS segment is in a non-canonical form.|
||||X|X|EVEX.512: Memory operand is not 64-byte aligned.<br>EVEX.256: Memory operand is not 32-byte aligned.<br>EVEX.128: Memory operand is not 16-byte aligned.|
|General Protection,<br>#GP(0)|||X||For an illegal memory operand effective address in the CS, DS, ES, FS or GS seg-<br>ments.|
|||||X|If the memory address is in a non-canonical form.|
||X|X|||If any part of the operand lies outside the effective address space from 0 to FFFFH.|
|Page Fault<br>#PF(fault-code)||X|X|X|For a page fault.|



2-50 Vol. 2A

INSTRUCTION FORMAT

## 2.8.2 Exceptions Type E2 of EVEX-Encoded Instructions

EVEX-encoded vector instructions with arithmetic semantic follow exception class E2.

Table 2-46.  Type E2 Class Exception Conditions

|Exception|Real|Virtual 8086|Protected and<br>Compatibility|64-bit|Cause of Exception|
|---|---|---|---|---|---|
||X|X|||If EVEX prefix present.|
||X|X|X|X|If an unmasked SIMD floating-point exception and CR4.OSXMMEXCPT[bit 10] = 0.|
|Invalid Opcode,<br>#UD|||X|X|If CR4.OSXSAVE[bit 18]=0.<br>If any one of following conditions applies:<br>•<br>State requirement, Table 2-37 not met.<br>•<br>Opcode independent #UD condition in Table 2-38.<br>•<br>Operand encoding #UD conditions in Table 2-39.<br>•<br>Opmask encoding #UD condition of Table 2-40.<br>•<br>Instruction specific EVEX.L'L restriction not met.|
||X|X|X|X|If preceded by a LOCK prefix (F0H).|
||||X|X|If any REX, F2, F3, or 66 prefixes precede a EVEX prefix.|
||X|X|X|X|If any corresponding CPUID feature flag is ‘0’.|
|Device Not Avail-<br>able, #NM|X|X|X|X|If CR0.TS[bit 3]=1.|
||||X||If fault suppression not set, and an illegal address in the SS segment.|
|Stack, #SS(0)||||X|If fault suppression not set, and a memory address referencing the SS segment is in a<br>non-canonical form.|
||||X||If fault suppression not set, and an illegal memory operand effective address in the CS,<br>DS, ES, FS or GS segments.|
|General Protec-<br>tion, #GP(0)||||X|If fault suppression not set, and the memory address is in a non-canonical form.|
||X|X|||If fault suppression not set, and any part of the operand lies outside the effective<br>address space from 0 to FFFFH.|
|Page Fault<br>#PF(fault-code)||X|X|X|If fault suppression not set, and a page fault.|
|Alignment Check<br>#AC(0)||X|X|X|For 2, 4, or 8 byte memory access if alignment checking is enabled and an unaligned<br>memory access is made while the current privilege level is 3.|
|SIMD Floating-<br>point Exception,<br>#XM|X|X|X|X|If an unmasked SIMD floating-point exception, {sae} or {er} not set, and CR4.OSXMMEX-<br>CPT[bit 10] = 1.|



Vol. 2A 2-51

INSTRUCTION FORMAT

## 2.8.3 Exceptions Type E3 and E3NF of EVEX-Encoded Instructions

EVEX-encoded scalar instructions with arithmetic semantic that support memory fault suppression follow exception class E3.

Table 2-47.  Type E3 Class Exception Conditions

|Exception|Real|Virtual 80x86|Protected and<br>Compatibility|64-bit|Cause of Exception|
|---|---|---|---|---|---|
||X|X|||If EVEX prefix present.|
||X|X|X|X|If an unmasked SIMD floating-point exception and CR4.OSXMMEXCPT[bit 10] = 0.|
|Invalid Opcode, #UD|||X|X|If CR4.OSXSAVE[bit 18]=0.<br>If any one of following conditions applies:<br>•<br>State requirement, Table 2-37 not met.<br>•<br>Opcode independent #UD condition in Table 2-38.<br>•<br>Operand encoding #UD conditions in Table 2-39.<br>•<br>Opmask encoding #UD condition of Table 2-40.<br>•<br>EVEX.b encoding #UD condition of Table 2-41.|
||X|X|X|X|If preceded by a LOCK prefix (F0H).|
||||X|X|If any REX, F2, F3, or 66 prefixes precede a EVEX prefix.|
||X|X|X|X|If any corresponding CPUID feature flag is ‘0’.|
|Device Not Available,<br>#NM|X|X|X|X|If CR0.TS[bit 3]=1.|
||||X||If fault suppression not set, and an illegal address in the SS segment.|
|Stack, #SS(0)||||X|If fault suppression not set, and a memory address referencing the SS segment is<br>in a non-canonical form.|
||||X||If fault suppression not set, and an illegal memory operand effective address in<br>the CS, DS, ES, FS or GS segments.|
|General Protection,<br>#GP(0)||||X|If fault suppression not set, and the memory address is in a non-canonical form.|
||X|X|||If fault suppression not set, and any part of the operand lies outside the effective<br>address space from 0 to FFFFH.|
|Page Fault #PF(fault-<br>code)||X|X|X|If fault suppression not set, and a page fault.|
|Alignment Check<br>#AC(0)||X|X|X|For 2, 4, or 8 byte memory access if alignment checking is enabled and an<br>unaligned memory access is made while the current privilege level is 3.|
|SIMD Floating-point<br>Exception, #XM|X|X|X|X|If an unmasked SIMD floating-point exception, {sae} or {er} not set, and CR4.OSX-<br>MMEXCPT[bit 10] = 1.|



2-52 Vol. 2A

INSTRUCTION FORMAT

EVEX-encoded scalar instructions with arithmetic semantic that do not support memory fault suppression follow exception class E3NF.

Table 2-48.  Type E3NF Class Exception Conditions

|Exception|Real|Virtual 80x86|Protected and<br>Compatibility|64-bit|Cause of Exception|
|---|---|---|---|---|---|
||X|X|||EVEX prefix.|
||X|X|X|X|If an unmasked SIMD floating-point exception and CR4.OSXMMEXCPT[bit 10] = 0.|
|Invalid Opcode, #UD|||X|X|If CR4.OSXSAVE[bit 18]=0.<br>If any one of following conditions applies:<br>•<br>State requirement, Table 2-37 not met.<br>•<br>Opcode independent #UD condition in Table 2-38.<br>•<br>Operand encoding #UD conditions in Table 2-39.<br>•<br>Opmask encoding #UD condition of Table 2-40.<br>•<br>EVEX.b encoding #UD condition of Table 2-41.|
||X|X|X|X|If preceded by a LOCK prefix (F0H).|
||||X|X|If any REX, F2, F3, or 66 prefixes precede a EVEX prefix.|
||X|X|X|X|If any corresponding CPUID feature flag is ‘0’.|
|Device Not Available,<br>#NM|X|X|X|X|If CR0.TS[bit 3]=1.|
|k|||X||For an illegal address in the SS segment.|
|Stac, #SS(0)||||X|If a memory address referencing the SS segment is in a non-canonical form.|
||||X||For an illegal memory operand effective address in the CS, DS, ES, FS or GS seg-<br>ments.|
|General Protection,<br>#GP(0)||||X|If the memory address is in a non-canonical form.|
||X|X|||If any part of the operand lies outside the effective address space from 0 to<br>FFFFH.|
|Page Fault #PF(fault-<br>code)||X|X|X|For a page fault.|
|Alignment Check<br>#AC(0)||X|X|X|For 2, 4, or 8 byte memory access if alignment checking is enabled and an<br>unaligned memory access is made while the current privilege level is 3.|
|SIMD Floating-point<br>Exception, #XM|X|X|X|X|If an unmasked SIMD floating-point exception, {sae} or {er} not set, and CR4.OSX-<br>MMEXCPT[bit 10] = 1.|



Vol. 2A 2-53

INSTRUCTION FORMAT

## 2.8.4 Exceptions Type E4 and E4NF of EVEX-Encoded Instructions

EVEX-encoded vector instructions that cause no SIMD FP exception and support memory fault suppression follow exception class E4.

Table 2-49.  Type E4 Class Exception Conditions

|Exception|Real|Virtual 80x86|Protected and<br>Compatibility|64-bit|Cause of Exception|
|---|---|---|---|---|---|
||X|X|||If EVEX prefix present.|
|Invalid Opcode, #UD|||X|X|If CR4.OSXSAVE[bit 18]=0.<br>If any one of following conditions applies:<br>•<br>State requirement, Table 2-37 not met.<br>•<br>Opcode independent #UD condition in Table 2-38.<br>•<br>Operand encoding #UD conditions in Table 2-39.<br>•<br>Opmask encoding #UD condition of Table 2-40.<br>•<br>EVEX.b encoding #UD condition of Table 2-41 and in E4.nb subclass (see E4.nb<br>entries in Table 2-43).<br>•<br>Instruction specific EVEX.L'L restriction not met.|
||X|X|X|X|If preceded by a LOCK prefix (F0H).|
||||X|X|If any REX, F2, F3, or 66 prefixes precede a EVEX prefix.|
||X|X|X|X|If any corresponding CPUID feature flag is ‘0’.|
|Device Not Available,<br>#NM|X|X|X|X|If CR0.TS[bit 3]=1.|
||||X||If fault suppression not set, and an illegal address in the SS segment.|
|Stack, #SS(0)||||X|If fault suppression not set, and a memory address referencing the SS segment is<br>in a non-canonical form.|
|General Protection,|||X||If fault suppression not set, and an illegal memory operand effective address in<br>the CS, DS, ES, FS or GS segments.|
|<br>#GP(0)||||X|If fault suppression not set, and the memory address is in a non-canonical form.|
||X|X|||If fault suppression not set, and any part of the operand lies outside the effective<br>address space from 0 to FFFFH.|
|Page Fault #PF(fault-<br>code)||X|X|X|If fault suppression not set, and a page fault.|
|Alignment Check<br>#AC(0)||X|X|X|For 2, 4, or 8 byte memory access if alignment checking is enabled and an<br>unaligned memory access is made while the current privilege level is 3.|



2-54 Vol. 2A

INSTRUCTION FORMAT

EVEX-encoded vector instructions that do not cause SIMD FP exception nor support memory fault suppression follow exception class E4NF.

Table 2-50.  Type E4NF Class Exception Conditions

|Exception|Real|Virtual 80x86|Protected and<br>Compatibility|64-bit|Cause of Exception|
|---|---|---|---|---|---|
||X|X|||If EVEX prefix present.|
|Invalid Opcode, #UD|||X|X|If CR4.OSXSAVE[bit 18]=0.<br>If any one of following conditions applies:<br>•<br>State requirement, Table 2-37 not met.<br>•<br>Opcode independent #UD condition in Table 2-38.<br>•<br>Operand encoding #UD conditions in Table 2-39.<br>•<br>Opmask encoding #UD condition of Table 2-40.<br>•<br>EVEX.b encoding #UD condition of Table 2-41 and in E4NF.nb subclass (see<br>E4NF.nb entries in Table 2-43).<br>•<br>Instruction specific EVEX.L'L restriction not met.|
||X|X|X|X|If preceded by a LOCK prefix (F0H).|
||||X|X|If any REX, F2, F3, or 66 prefixes precede a EVEX prefix.|
||X|X|X|X|If any corresponding CPUID feature flag is ‘0’.|
|Device Not Available,<br>#NM|X|X|X|X|If CR0.TS[bit 3]=1.|
|Sk #SS0|||X||For an illegal address in the SS segment.|
|tac, ()||||X|If a memory address referencing the SS segment is in a non-canonical form.|
|General Protection,|||X||For an illegal memory operand effective address in the CS, DS, ES, FS or GS seg-<br>ments.|
|<br>#GP(0)||||X|If the memory address is in a non-canonical form.|
||X|X|||If any part of the operand lies outside the effective address space from 0 to<br>FFFFH.|
|Page Fault #PF(fault-<br>code)||X|X|X|For a page fault.|



Vol. 2A 2-55

INSTRUCTION FORMAT

## 2.8.5 Exceptions Type E5 and E5NF

EVEX-encoded scalar/partial-vector instructions that cause no SIMD FP exception and support memory fault suppression follow exception class E5.

Table 2-51.  Type E5 Class Exception Conditions

|Exception|Real|Virtual 80x86|Protected and<br>Compatibility|64-bit|Cause of Exception|
|---|---|---|---|---|---|
||X|X|||If EVEX prefix present.|
|Invalid Opcode, #UD|||X|X|If CR4.OSXSAVE[bit 18]=0.<br>If any one of following conditions applies:<br>•<br>State requirement, Table 2-37 not met.<br>•<br>Opcode independent #UD condition in Table 2-38.<br>•<br>Operand encoding #UD conditions in Table 2-39.<br>•<br>Opmask encoding #UD condition of Table 2-40.<br>•<br>EVEX.b encoding #UD condition of Table 2-41.<br>•<br>Instruction specific EVEX.L'L restriction not met.|
||X|X|X|X|If preceded by a LOCK prefix (F0H).|
||||X|X|If any REX, F2, F3, or 66 prefixes precede a EVEX prefix.|
||X|X|X|X|If any corresponding CPUID feature flag is ‘0’.|
|Device Not Available,<br>#NM|X|X|X|X|If CR0.TS[bit 3]=1.|
||||X||If fault suppression not set, and an illegal address in the SS segment.|
|Stack, #SS(0)||||X|If fault suppression not set, and a memory address referencing the SS segment is<br>in a non-canonical form.|
||||X||If fault suppression not set, and an illegal memory operand effective address in the<br>CS, DS, ES, FS or GS segments.|
|General Protection,<br>#GP(0)||||X|If fault suppression not set, and the memory address is in a non-canonical form.|
||X|X|||If fault suppression not set, and any part of the operand lies outside the effective<br>address space from 0 to FFFFH.|
|Page Fault #PF(fault-<br>code)||X|X|X|If fault suppression not set, and a page fault.|
|Alignment Check<br>#AC(0)||X|X|X|For 2, 4, or 8 byte memory access if alignment checking is enabled and an<br>unaligned memory access is made while the current privilege level is 3.|



EVEX-encoded scalar/partial vector instructions that do not cause SIMD FP exception nor support memory fault suppression follow exception class E5NF.

2-56 Vol. 2A

INSTRUCTION FORMAT

Table 2-52.  Type E5NF Class Exception Conditions

|Exception|Real|Virtual 80x86|Protected and<br>Compatibility|64-bit|Cause of Exception|
|---|---|---|---|---|---|
||X|X|||If EVEX prefix present.|
|Invalid Opcode, #UD|||X|X|If CR4.OSXSAVE[bit 18]=0.<br>If any one of following conditions applies:<br>•<br>State requirement, Table 2-37 not met.<br>•<br>Opcode independent #UD condition in Table 2-38.<br>•<br>Operand encoding #UD conditions in Table 2-39.<br>•<br>Opmask encoding #UD condition of Table 2-40.<br>•<br>EVEX.b encoding #UD condition of Table 2-41.<br>•<br>Instruction specific EVEX.L'L restriction not met.|
||X|X|X|X|If preceded by a LOCK prefix (F0H).|
||||X|X|If any REX, F2, F3, or 66 prefixes precede a EVEX prefix.|
||X|X|X|X|If any corresponding CPUID feature flag is ‘0’.|
|Device Not Available,<br>#NM|X|X|X|X|If CR0.TS[bit 3]=1.|
||||X||If an illegal address in the SS segment.|
|Stack, #SS(0)||||X|If a memory address referencing the SS segment is in a non-canonical form.|
||||X||If an illegal memory operand effective address in the CS, DS, ES, FS or GS segments.|
|General Protection,||||X|If the memory address is in a non-canonical form.|
|#GP(0)|X|X|||If any part of the operand lies outside the effective address space from 0 to<br>FFFFH.|
|Page Fault #PF(fault-<br>code)||X|X|X|For a page fault.|
|Alignment Check<br>#AC(0)||X|X|X|For 2, 4, or 8 byte memory access if alignment checking is enabled and an<br>unaligned memory access is made while the current privilege level is 3.|



Vol. 2A 2-57

INSTRUCTION FORMAT

## 2.8.6 Exceptions Type E6 and E6NF

Table 2-53.  Type E6 Class Exception Conditions

|Exception|Real|Virtual 80x86|Protected and<br>Compatibility|64-bit|Cause of Exception|
|---|---|---|---|---|---|
||X|X|||If EVEX prefix present.|
|Invalid Opcode, #UD|||X|X|If CR4.OSXSAVE[bit 18]=0.<br>If any one of following conditions applies:<br>•<br>State requirement, Table 2-37 not met.<br>•<br>Opcode independent #UD condition in Table 2-38.<br>•<br>Operand encoding #UD conditions in Table 2-39.<br>•<br>Opmask encoding #UD condition of Table 2-40.<br>•<br>EVEX.b encoding #UD condition of Table 2-41.<br>•<br>Instruction specific EVEX.L'L restriction not met.|
||||X|X|If preceded by a LOCK prefix (F0H).|
||||X|X|If any REX, F2, F3, or 66 prefixes precede a EVEX prefix.|
||||X|X|If any corresponding CPUID feature flag is ‘0’.|
|Device Not Available,<br>#NM|||X|X|If CR0.TS[bit 3]=1.|
||||X||If fault suppression not set, and an illegal address in the SS segment.|
|Stack, #SS(0)||||X|If fault suppression not set, and a memory address referencing the SS segment is<br>in a non-canonical form.|
|General Protection,<br>|||X||If fault suppression not set, and an illegal memory operand effective address in the<br>CS, DS, ES, FS or GS segments.|
|#GP(0)||||X|If fault suppression not set, and the memory address is in a non-canonical form.|
|Page Fault #PF(fault-<br>code)|||X|X|If fault suppression not set, and a page fault.|
|Alignment Check<br>#AC(0)|||X|X|For 2, 4, or 8 byte memory access if alignment checking is enabled and an<br>unaligned memory access is made while the current privilege level is 3.|



2-58 Vol. 2A

INSTRUCTION FORMAT

EVEX-encoded instructions that do not cause SIMD FP exception nor support memory fault suppression follow exception class E6NF.

Table 2-54.  Type E6NF Class Exception Conditions

|Exception|Real|Virtual 80x86|Protected and<br>Compatibility|64-bit|Cause of Exception|
|---|---|---|---|---|---|
|Invalid Opcode, #UD|X|X|||If EVEX prefix present.|
||||X|X|If CR4.OSXSAVE[bit 18]=0.<br>If any one of following conditions applies:<br>•<br>State requirement, Table 2-37 not met.<br>•<br>Opcode independent #UD condition in Table 2-38.<br>•<br>Operand encoding #UD conditions in Table 2-39.<br>•<br>Opmask encoding #UD condition of Table 2-40.<br>•<br>EVEX.b encoding #UD condition of Table 2-41.<br>•<br>Instruction specific EVEX.L'L restriction not met.|
||||X|X|If preceded by a LOCK prefix (F0H).|
||||X|X|If any REX, F2, F3, or 66 prefixes precede a EVEX prefix.|
||||X|X|If any corresponding CPUID feature flag is ‘0’.|
|Device Not Available,<br>#NM|||X|X|If CR0.TS[bit 3]=1.|
|Sk #SS0|||X||For an illegal address in the SS segment.|
|tac, ()||||X|If a memory address referencing the SS segment is in a non-canonical form.|
|General Protection,<br>|||X||For an illegal memory operand effective address in the CS, DS, ES, FS or GS seg-<br>ments.|
|#GP(0)||||X|If the memory address is in a non-canonical form.|
|Page Fault #PF(fault-<br>code)|||X|X|For a page fault.|
|Alignment Check<br>#AC(0)|||X|X|For 2, 4, or 8 byte memory access if alignment checking is enabled and an<br>unaligned memory access is made while the current privilege level is 3.|



Vol. 2A 2-59

INSTRUCTION FORMAT

## 2.8.7 Exceptions Type E7NM

EVEX-encoded instructions that cause no SIMD FP exception and do not reference memory follow exception class E7NM.

Table 2-55.  Type E7NM Class Exception Conditions

|Exception|Real|Virtual 80x86|Protected and<br>Compatibility|64-bit|Cause of Exception|
|---|---|---|---|---|---|
||X|X|||If EVEX prefix present.|
|Invalid Opcode, #UD|||X|X|If CR4.OSXSAVE[bit 18]=0.<br>If any one of following conditions applies:<br>•<br>State requirement, Table 2-37 not met.<br>•<br>Opcode independent #UD condition in Table 2-38.<br>•<br>Operand encoding #UD conditions in Table 2-39.<br>•<br>Opmask encoding #UD condition of Table 2-40.<br>•<br>EVEX.b encoding #UD condition of Table 2-41.<br>•<br>Instruction specific EVEX.L’L restriction not met.|
||X|X|X|X|If preceded by a LOCK prefix (F0H).|
||||X|X|If any REX, F2, F3, or 66 prefixes precede a EVEX prefix.|
||X|X|X|X|If any corresponding CPUID feature flag is ‘0’.|
|Device Not Available,<br>#NM|||X|X|If CR0.TS[bit 3]=1.|



2-60 Vol. 2A

INSTRUCTION FORMAT

## 2.8.8 Exceptions Type E9 and E9NF

EVEX-encoded vector or partial-vector instructions that do not cause no SIMD FP exception and support memory fault suppression follow exception class E9.

Table 2-56.  Type E9 Class Exception Conditions

|Exception|Real|Virtual 80x86|Protected and<br>Compatibility|64-bit|Cause of Exception|
|---|---|---|---|---|---|
||X|X|||If EVEX prefix present.|
|Invalid Opcode, #UD|||X|X|If CR4.OSXSAVE[bit 18]=0.<br>If any one of following conditions applies:<br>•<br>State requirement, Table 2-37 not met.<br>•<br>Opcode independent #UD condition in Table 2-38.<br>•<br>Operand encoding #UD conditions in Table 2-39.<br>•<br>Opmask encoding #UD condition of Table 2-40.<br>•<br>EVEX.b encoding #UD condition of Table 2-41.<br>•<br>Instruction specific EVEX.L'L restriction not met.|
||X|X|X|X|If preceded by a LOCK prefix (F0H).|
||||X|X|If any REX, F2, F3, or 66 prefixes precede a EVEX prefix.|
||X|X|X|X|If any corresponding CPUID feature flag is ‘0’.|
|Device Not Available,<br>#NM|X|X|X|X|If CR0.TS[bit 3]=1.|
||||X||If fault suppression not set, and an illegal address in the SS segment.|
|Stack, #SS(0)||||X|If fault suppression not set, and a memory address referencing the SS segment is<br>in a non-canonical form.|
||||X||If fault suppression not set, and an illegal memory operand effective address in the<br>CS, DS, ES, FS or GS segments.|
|General Protection,<br>#GP(0)||||X|If fault suppression not set, and the memory address is in a non-canonical form.|
||X|X|||If fault suppression not set, and any part of the operand lies outside the effective<br>address space from 0 to FFFFH.|
|Page Fault #PF(fault-<br>code)||X|X|X|If fault suppression not set, and a page fault.|
|Alignment Check<br>#AC(0)||X|X|X|For 2, 4, or 8 byte memory access if alignment checking is enabled and an<br>unaligned memory access is made while the current privilege level is 3.|



Vol. 2A 2-61

INSTRUCTION FORMAT

EVEX-encoded vector or partial-vector instructions that must be encoded with VEX.L’L = 0, do not cause SIMD FP exception nor support memory fault suppression follow exception class E9NF.

Table 2-57.  Type E9NF Class Exception Conditions

|Exception|Real|Virtual 80x86|Protected and<br>Compatibility|64-bit|Cause of Exception|
|---|---|---|---|---|---|
||X|X|||If EVEX prefix present.|
|Invalid Opcode, #UD|||X|X|If CR4.OSXSAVE[bit 18]=0.<br>If any one of following conditions applies:<br>•<br>State requirement, Table 2-37 not met.<br>•<br>Opcode independent #UD condition in Table 2-38.<br>•<br>Operand encoding #UD conditions in Table 2-39.<br>•<br>Opmask encoding #UD condition of Table 2-40.<br>•<br>EVEX.b encoding #UD condition of Table 2-41.<br>•<br>Instruction specific EVEX.L'L restriction not met.|
||X|X|X|X|If preceded by a LOCK prefix (F0H).|
||||X|X|If any REX, F2, F3, or 66 prefixes precede a EVEX prefix.|
||X|X|X|X|If any corresponding CPUID feature flag is ‘0’.|
|Device Not Available,<br>#NM|X|X|X|X|If CR0.TS[bit 3]=1.|
||||X||If an illegal address in the SS segment.|
|Stack, #SS(0)||||X|If a memory address referencing the SS segment is in a non-canonical form.|
||||X||If an illegal memory operand effective address in the CS, DS, ES, FS or GS segments.|
|General Protection,||||X|If the memory address is in a non-canonical form.|
|#GP(0)|X|X|||If any part of the operand lies outside the effective address space from 0 to<br>FFFFH.|
|Page Fault #PF(fault-<br>code)||X|X|X|For a page fault.|
|Alignment Check<br>#AC(0)||X|X|X|For 2, 4, or 8 byte memory access if alignment checking is enabled and an<br>unaligned memory access is made while the current privilege level is 3.|



2-62 Vol. 2A

INSTRUCTION FORMAT

## 2.8.9 Exceptions Type E10 and E10NF

EVEX-encoded scalar instructions that ignore EVEX.L’L vector length encoding, do not cause a SIMD FP exception, and support memory fault suppression follow exception class E10.

Table 2-58.  Type E10 Class Exception Conditions

|Exception|Real|Virtual 80x86|Protected and<br>Compatibility|64-bit|Cause of Exception|
|---|---|---|---|---|---|
||X|X|||If EVEX prefix present.|
|Invalid Opcode, #UD|||X|X|If CR4.OSXSAVE[bit 18]=0.<br>If any one of following conditions applies:<br>•<br>State requirement, Table 2-37 not met.<br>•<br>Opcode independent #UD condition in Table 2-38.<br>•<br>Operand encoding #UD conditions in Table 2-39.<br>•<br>Opmask encoding #UD condition of Table 2-40.<br>•<br>EVEX.b encoding #UD condition of Table 2-41.|
||X|X|X|X|If preceded by a LOCK prefix (F0H).|
||||X|X|If any REX, F2, F3, or 66 prefixes precede a EVEX prefix.|
||X|X|X|X|If any corresponding CPUID feature flag is ‘0’.|
|Device Not Available,<br>#NM|X|X|X|X|If CR0.TS[bit 3]=1.|
||||X||If fault suppression not set, and an illegal address in the SS segment.|
|Stack, #SS(0)||||X|If fault suppression not set, and a memory address referencing the SS segment is<br>in a non-canonical form.|
||||X||If fault suppression not set, and an illegal memory operand effective address in the<br>CS, DS, ES, FS or GS segments.|
|General Protection,<br>#GP(0)||||X|If fault suppression not set, and the memory address is in a non-canonical form.|
||X|X|||If fault suppression not set, and any part of the operand lies outside the effective<br>address space from 0 to FFFFH.|
|Page Fault #PF(fault-<br>code)||X|X|X|If fault suppression not set, and a page fault.|
|Alignment Check<br>#AC(0)||X|X|X|For 2, 4, or 8 byte memory access if alignment checking is enabled and an<br>unaligned memory access is made while the current privilege level is 3.|



Vol. 2A 2-63

INSTRUCTION FORMAT

EVEX-encoded scalar instructions that ignore EVEX.L’L vector length encoding, do not cause a SIMD FP exception, and do not support memory fault suppression follow exception class E10NF.

Table 2-59.  Type E10NF Class Exception Conditions

|Exception|Real|Virtual 80x86|Protected and<br>Compatibility|64-bit|Cause of Exception|
|---|---|---|---|---|---|
||X|X|||If EVEX prefix present.|
|Invalid Opcode, #UD|||X|X|If CR4.OSXSAVE[bit 18]=0.<br>If any one of following conditions applies:<br>•<br>State requirement, Table 2-37 not met.<br>•<br>Opcode independent #UD condition in Table 2-38.<br>•<br>Operand encoding #UD conditions in Table 2-39.<br>•<br>Opmask encoding #UD condition of Table 2-40.<br>•<br>EVEX.b encoding #UD condition of Table 2-41.|
||X|X|X|X|If preceded by a LOCK prefix (F0H).|
||||X|X|If any REX, F2, F3, or 66 prefixes precede a EVEX prefix.|
||X|X|X|X|If any corresponding CPUID feature flag is ‘0’.|
|Device Not Available,<br>#NM|X|X|X|X|If CR0.TS[bit 3]=1.|
||||X||If fault suppression not set, and an illegal address in the SS segment.|
|Stack, #SS(0)||||X|If fault suppression not set, and a memory address referencing the SS segment is<br>in a non-canonical form.|
||||X||If fault suppression not set, and an illegal memory operand effective address in the<br>CS, DS, ES, FS or GS segments.|
|General Protection,<br>#GP(0)||||X|If fault suppression not set, and the memory address is in a non-canonical form.|
||X|X|||If fault suppression not set, and any part of the operand lies outside the effective<br>address space from 0 to FFFFH.|
|Page Fault #PF(fault-<br>code)||X|X|X|If fault suppression not set, and a page fault.|
|Alignment Check<br>#AC(0)||X|X|X|For 2, 4, or 8 byte memory access if alignment checking is enabled and an<br>unaligned memory access is made while the current privilege level is 3.|



2-64 Vol. 2A

INSTRUCTION FORMAT

## 2.8.10 Exception Type E11 (EVEX-only, Mem Arg, No AC, Floating-point Exceptions)

EVEX-encoded instructions that can cause SIMD FP exception, memory operand support fault suppression but do not cause #AC follow exception class E11.

Table 2-60.  Type E11 Class Exception Conditions

|Exception|Real|Virtual 80x86|Protected and<br>Compatibility|64-bit|Cause of Exception|
|---|---|---|---|---|---|
|Invalid Opcode, #UD|X|X|||If EVEX prefix present.|
||||X|X|If CR4.OSXSAVE[bit 18]=0.<br>If any one of following conditions applies:<br>•<br>State requirement, Table 2-37 not met.<br>•<br>Opcode independent #UD condition in Table 2-38.<br>•<br>Operand encoding #UD conditions in Table 2-39.<br>•<br>Opmask encoding #UD condition of Table 2-40.<br>•<br>EVEX.b encoding #UD condition of Table 2-41.<br>•<br>Instruction specific EVEX.L'L restriction not met.|
||X|X|X|X|If preceded by a LOCK prefix (F0H).|
||||X|X|If any REX, F2, F3, or 66 prefixes precede a EVEX prefix.|
||X|X|X|X|If any corresponding CPUID feature flag is ‘0’.|
|Device Not Available,<br>#NM|X|X|X|X|If CR0.TS[bit 3]=1.|
|Stack, #SS(0)|||X||If fault suppression not set, and an illegal address in the SS segment.|
|||||X|If fault suppression not set, and a memory address referencing the SS segment is<br>in a non-canonical form.|
|General Protection,<br>#GP(0)|||X||If fault suppression not set, and an illegal memory operand effective address in the<br>CS, DS, ES, FS or GS segments.|
|||||X|If fault suppression not set, and the memory address is in a non-canonical form.|
||X|X|||If fault suppression not set, and any part of the operand lies outside the effective<br>address space from 0 to FFFFH.|
|Page Fault #PF (fault-<br>code)||X|X|X|If fault suppression not set, and a page fault.|
|SIMD Floating-Point<br>Exception, #XM|X|X|X|X|If an unmasked SIMD floating-point exception, {sae} not set, and CR4.OSXMMEX-<br>CPT[bit 10] = 1.|



Vol. 2A 2-65

INSTRUCTION FORMAT

## 2.8.11 Exception Type E12 and E12NP (VSIB Mem Arg, No AC, No Floating-point Exceptions)

Table 2-61.  Type E12 Class Exception Conditions

|Exception|Real|Virtual 80x86|Protected and<br>Compatibility|64-bit|Cause of Exception|
|---|---|---|---|---|---|
|Invalid Opcode, #UD|X|X|||If EVEX prefix present.|
||||X|X|If CR4.OSXSAVE[bit 18]=0.<br>If any one of following conditions applies:<br>•<br>State requirement, Table 2-37 not met.<br>•<br>Opcode independent #UD condition in Table 2-38.<br>•<br>Operand encoding #UD conditions in Table 2-39.<br>•<br>Opmask encoding #UD condition of Table 2-40.<br>•<br>EVEX.b encoding #UD condition of Table 2-41.<br>•<br>Instruction specific EVEX.L'L restriction not met.<br>•<br>If vvvv != 1111b.|
||X|X|X|X|If preceded by a LOCK prefix (F0H).|
||||X|X|If any REX, F2, F3, or 66 prefixes precede a VEX prefix.|
||X|X|X|NA|If address size attribute is 16 bit.|
||X|X|X|X|If ModR/M.mod = ‘11b’.|
||X|X|X|X|If ModR/M.rm != ‘100b’.|
||X|X|X|X|If any corresponding CPUID feature flag is ‘0’.|
||X|X|X|X|If k0 is used (gather or scatter operation).|
||X|X|X|X|If index = destination register (gather operation).|
|Device Not Available,<br>#NM|X|X|X|X|If CR0.TS[bit 3]=1.|
|Stack, #SS(0)|||X||For an illegal address in the SS segment.|
|||||X|If a memory address referencing the SS segment is in a non-canonical form.|
|General Protection,<br>#GP(0)|||X||For an illegal memory operand effective address in the CS, DS, ES, FS or GS seg-<br>ments.|
|||||X|If the memory address is in a non-canonical form.|
||X|X|||If any part of the operand lies outside the effective address space from 0 to<br>FFFFH.|
|Page Fault #PF (fault-<br>code)||X|X|X|For a page fault.|



2-66 Vol. 2A

INSTRUCTION FORMAT

EVEX-encoded prefetch instructions that do not cause #PF follow exception class E12NP.

Table 2-62.  Type E12NP Class Exception Conditions

|Exception|Real|Virtual 80x86|Protected and<br>Compatibility|64-bit|Cause of Exception|
|---|---|---|---|---|---|
|Invalid Opcode, #UD|X|X|||If EVEX prefix present.|
||||X|X|If CR4.OSXSAVE[bit 18]=0.<br>If any one of following conditions applies:<br>•<br>State requirement, Table 2-37 not met.<br>•<br>Opcode independent #UD condition in Table 2-38.<br>•<br>Operand encoding #UD conditions in Table 2-39.<br>•<br>Opmask encoding #UD condition of Table 2-40.<br>•<br>EVEX.b encoding #UD condition of Table 2-41.<br>•<br>Instruction specific EVEX.L'L restriction not met.|
||X|X|X|X|If preceded by a LOCK prefix (F0H).|
||||X|X|If any REX, F2, F3, or 66 prefixes precede a VEX prefix.|
||X|X|X|NA|If address size attribute is 16 bit.|
||X|X|X|X|If ModR/M.mod = ‘11b’.|
||X|X|X|X|If ModR/M.rm != ‘100b’.|
||X|X|X|X|If any corresponding CPUID feature flag is ‘0’.|
||X|X|X|X|If k0 is used (gather or scatter operation).|
|Device Not Available,<br>#NM|X|X|X|X|If CR0.TS[bit 3]=1.|



Vol. 2A 2-67

INSTRUCTION FORMAT

# 2.9 EXCEPTION CLASSIFICATIONS OF OPMASK INSTRUCTIONS

The exception behavior of VEX-encoded opmask instructions are listed below.

Exception conditions of Opmask instructions that do not address memory are listed as Type K20.

Table 2-63.  TYPE K20 Exception Definition (VEX-Encoded OpMask Instructions w/o Memory Arg)

|Exception|Real|Virtual 80x86|Protected and<br>Compatibility|64-bit|Cause of Exception|
|---|---|---|---|---|---|
|Invalid Opcode, #UD|X|X|X|X|If relevant CPUID feature flag is ‘0’.|
||X|X|||If a VEX prefix is present.|
||||X|X|If CR4.OSXSAVE[bit 18]=0.<br>If any one of following conditions applies:<br>•<br>State requirement, Table 2-37 not met.<br>•<br>Opcode independent #UD condition in Table 2-38.<br>•<br>Operand encoding #UD conditions in Table 2-39.|
||||X|X|If any REX, F2, F3, or 66 prefixes precede a VEX prefix.|
||||X|X|If ModRM:[7:6] != 11b.|
|Device Not Available,<br>#NM|X|X|X|X|If CR0.TS[bit 3]=1.|



2-68 Vol. 2A

INSTRUCTION FORMAT

Exception conditions of Opmask instructions that address memory are listed as Type K21.

Table 2-64.  TYPE K21 Exception Definition (VEX-Encoded OpMask Instructions Addressing Memory)

|Exception|Real|Virtual 80x86|Protected and<br>Compatibility|64-bit|Cause of Exception|
|---|---|---|---|---|---|
|Invalid Opcode, #UD|X|X|X|X|If relevant CPUID feature flag is ‘0’.|
||X|X|||If a VEX prefix is present.|
||||X|X|If CR4.OSXSAVE[bit 18]=0.<br>If any one of following conditions applies:<br>•<br>State requirement, Table 2-37 not met.<br>•<br>Opcode independent #UD condition in Table 2-38.<br>•<br>Operand encoding #UD conditions in Table 2-39.|
|Device Not Available,<br>#NM|X|X|X|X|If CR0.TS[bit 3]=1.|
||||X|X|If any REX, F2, F3, or 66 prefixes precede a VEX prefix.|
|Stack, #SS(0)|X|X|X||For an illegal address in the SS segment.|
|||||X|If a memory address referencing the SS segment is in a non-canonical form.|
|General Protection,<br>#GP(0)|||X||For an illegal memory operand effective address in the CS, DS, ES, FS or GS seg-<br>ments.<br>If the DS, ES, FS, or GS register is used to access memory and it contains a null<br>segment selector.|
|||||X|If the memory address is in a non-canonical form.|
||X|X|||If any part of the operand lies outside the effective address space from 0 to<br>FFFFH.|
|Page Fault #PF(fault-<br>code)||X|X|X|For a page fault.|
|Alignment Check<br>#AC(0)||X|X|X|For 2, 4, or 8 byte memory access if alignment checking is enabled and an<br>unaligned memory access is made while the current privilege level is 3.|



Vol. 2A 2-69

INSTRUCTION FORMAT

# 2.10 INTEL® AMX INSTRUCTION EXCEPTION CLASSES

Alignment exceptions: The Intel AMX instructions that access memory will never generate #AC exceptions.

Table 2-65.  Intel® AMX Exception Classes

|**Class**|**Description**|
|---|---|
|AMX-E1|• #UD if preceded by LOCK, 66H, F2H, F3H or REX prefixes.<br>• #UD if CR4.OSXSAVE≠1.<br>• #UD if XCR0[18:17]≠0b11.<br>• #UD if IA32_EFER.LMA≠1 OR CS.L≠1.<br>• #UD if VVVV≠0b1111.|
||• #GP based on palette and configuration checks (see pseudocode).<br>• #GP if the memory address is in a non-canonical form.|
||• #SS(0) if the memory address referencing the SS segment is in a non-canonical form.|
||• #PF if a page fault occurs.|
|AMX-E2|• #UD if preceded by LOCK, 66H, F2H, F3H or REX prefixes.<br>• #UD if CR4.OSXSAVE≠1.<br>• #UD if XCR0[18:17]≠0b11.<br>• #UD if IA32_EFER.LMA≠1 OR CS.L≠1.<br>• #UD if VVVV≠0b1111.|
||• #GP if the memory address is in a non-canonical form.|
||• #SS(0) if the memory address referencing the SS segment is in a non-canonical form.|
||• #PF if a page fault occurs.|
|AMX-E3|• #UD if preceded by LOCK, 66H, F2H, F3H or REX prefixes.<br>• #UD if CR4.OSXSAVE≠1.<br>• #UD if XCR0[18:17]≠0b11.<br>• #UD if IA32_EFER.LMA≠1 OR CS.L≠1.<br>• #UD if VVVV≠0b1111.<br>• #UD if not using SIB addressing.<br>• #UD if TILES_CONFIGURED == 0.<br>• #UD if tsrc or tdest are not valid tiles.<br>• #UD if tsrc/tdest are≥palette_table[tilecfg.palette_id].max_names.<br>• #UD if tsrc.colbytes mod 4≠0 OR tdest.colbytes mod 4≠0.<br>• #UD if tilecfg.start_row≥ tsrc.rows OR tilecfg.start_row≥tdest.rows.|
||• #GP if the memory address is in a non-canonical form.|
||• #SS(0) if the memory address referencing the SS segment is in a non-canonical form.|
||• #PF if any memory operand causes a page fault.|
||• #NM if XFD[18] == 1.|



2-70 Vol. 2A

INSTRUCTION FORMAT

Table 2-65.  Intel® AMX Exception Classes  (Contd.)

|**Class**|**Description**|
|---|---|
|AMX-E4|• #UD if preceded by LOCK, 66H, F2H, F3H or REX prefixes.<br>• #UD if CR4.OSXSAVE≠1.<br>• #UD if XCR0[18:17]≠0b11.<br>• #UD if IA32_EFER.LMA≠1 OR CS.L≠1.<br>• #UD if srcdest == src1 OR src1 == src2 OR srcdest == src2.<br>• #UD if TILES_CONFIGURED == 0.<br>• #UD if srcdest.colbytes mod 4≠0.<br>• #UD if src1.colbytes mod 4≠0.<br>• #UD if src2.colbytes mod 4≠0.<br>• #UD if srcdest/src1/src2 are not valid tiles.<br>• #UD if srcdest/src1/src2 are≥palette_table[tilecfg.palette_id].max_names.<br>• #UD if srcdest.colbytes≠src2.colbytes.<br>• #UD if srcdest.rows≠src1.rows.<br>• #UD if src1.colbytes / 4≠src2.rows.<br>• #UD if srcdest.colbytes > tmul_maxn.<br>• #UD if src2.colbytes > tmul_maxn.<br>• #UD if src1.colbytes/4 > tmul_maxk.<br>• #UD if src2.rows > tmul_maxk.|
||• #NM if XFD[18] == 1.|
|AMX-E5|• #UD if preceded by LOCK, 66H, F2H, F3H or REX prefixes.<br>• #UD if CR4.OSXSAVE≠1.<br>• #UD if XCR0[18:17]≠0b11.<br>• #UD if IA32_EFER.LMA≠1 OR CS.L≠1.<br>• #UD if VVVV≠0b1111.<br>• #UD if TILES_CONFIGURED == 0.<br>• #UD if tdest is not a valid tile.<br>• #UD if tdest is≥palette_table[tilecfg.palette_id].max_names.|
||• #NM if XFD[18] == 1.|
|AMX-E6|• #UD if preceded by LOCK, 66H, F2H, F3H or REX prefixes.<br>• #UD if CR4.OSXSAVE≠1.<br>• #UD if XCR0[18:17]≠0b11.<br>• #UD if IA32_EFER.LMA≠1 OR CS.L≠1.<br>• #UD if VVVV≠0b1111.|



Vol. 2A 2-71

INSTRUCTION FORMAT

2-72 Vol. 2A
