---
name: docs-md-x86-06-chapter-6-instruction-set-reference-w-z
description: "Intel SDM Vol. 2: Chapter 6 Instruction Set Reference, W-Z (vendor documentation for x86 AVX2, AVX-512 and AVX-512 FP16)."
when: "when you need Intel SDM Vol. 2: Chapter 6 Instruction Set Reference, W-Z while writing a kernel for x86 AVX2, AVX-512 and AVX-512 FP16."
---

CHAPTER 6 INSTRUCTION SET REFERENCE, W-Z

# 6.1 INSTRUCTIONS (W-Z)

Chapter 6 continues an alphabetical discussion of Intel<sup>_®_</sup> 64 and IA-32 instructions (W-Z). See also: Chapter 3, “Instruction Set Reference, A-L,” in the _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 2A_ ; Chapter 4, “Instruction Set Reference, M-U‚” in the _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 2B_ ; and Chapter 5, “Instruction Set Reference, V‚” in the _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 2D_ .

Vol. 2D 6-1

INSTRUCTION SET REFERENCE, W-Z

## WAIT/FWAIT—Wait

|Opcode|Instruction|Op/<br>En|64-Bit<br>Mode|Compat/<br>Leg Mode|Description|
|---|---|---|---|---|---|
|9B|WAIT|ZO|Valid|Valid|Check pending unmasked floating-point<br>|
||||||exceptions.|
|9B|FWAIT|ZO|Valid|Valid|Check pending unmasked floating-point<br>exceptions.|



#### Instruction Operand Encoding

|Op/En|Operand 1|Operand 2|Operand 3|Operand 4|
|---|---|---|---|---|
|ZO|N/A|N/A|N/A|N/A|



#### Description

Causes the processor to check for and handle pending, unmasked, floating-point exceptions before proceeding. (FWAIT is an alternate mnemonic for WAIT.)

This instruction is useful for synchronizing exceptions in critical sections of code. Coding a WAIT instruction after a floating-point instruction ensures that any unmasked floating-point exceptions the instruction may raise are handled before the processor can modify the instruction’s results. See the section titled “Floating-Point Exception Synchronization” in Chapter 8 of the _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ , for more information on using the WAIT/FWAIT instruction.

This instruction’s operation is the same in non-64-bit modes and 64-bit mode.

#### Operation

CheckForPendingUnmaskedFloatingPointExceptions;

#### FPU Flags Affected

The C0, C1, C2, and C3 flags are undefined.

#### Floating-Point Exceptions

None.

#### Protected Mode Exceptions

#NM If CR0.MP[bit 1] = 1 and CR0.TS[bit 3] = 1. #UD If the LOCK prefix is used.

#### Real-Address Mode Exceptions

Same exceptions as in protected mode.

#### Virtual-8086 Mode Exceptions

Same exceptions as in protected mode.

#### Compatibility Mode Exceptions

Same exceptions as in protected mode.

#### 64-Bit Mode Exceptions

Same exceptions as in protected mode.

WAIT/FWAIT—Wait

6-2 Vol. 2D

INSTRUCTION SET REFERENCE, W-Z

## WBINVD—Write Back and Invalidate Cache

|Opcode|Instruction|Op/<br>En|64-Bit<br>Mode|Compat/<br>Leg Mode|Description|
|---|---|---|---|---|---|
|0F 09|WBINVD|ZO|Valid|Valid|Write back and flush Internal caches; initiate<br>writing-back and flushing of external caches.|



#### Instruction Operand Encoding

|Op/En|Operand 1|Operand 2|Operand 3|Operand 4|
|---|---|---|---|---|
|ZO|N/A|N/A|N/A|N/A|



#### Description

Writes back all modified cache lines in the processor’s internal cache to main memory and invalidates (flushes) the internal caches. The instruction then issues a special-function bus cycle that directs external caches to also write back modified data and another bus cycle to indicate that the external caches should be invalidated.

After executing this instruction, the processor does not wait for the external caches to complete their write-back and flushing operations before proceeding with instruction execution. It is the responsibility of hardware to respond to the cache write-back and flush signals. The amount of time or cycles for WBINVD to complete will vary due to size and other factors of different cache hierarchies. As a consequence, the use of the WBINVD instruction can have an impact on logical processor interrupt/event response time. Additional information of WBINVD behavior in a cache hierarchy with hierarchical sharing topology can be found in Chapter 2 of the _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 3A_ .

The WBINVD instruction is a privileged instruction. When the processor is running in protected mode, the CPL of a program or procedure must be 0 to execute this instruction. This instruction is also a serializing instruction (see “Serializing Instructions” in Chapter 9 of the _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 3A_ ).

In situations where cache coherency with main memory is not a concern, software can use the INVD instruction. This instruction’s operation is the same in non-64-bit modes and 64-bit mode.

#### IA-32 Architecture Compatibility

The WBINVD instruction is implementation dependent, and its function may be implemented differently on future Intel 64 and IA-32 processors. The instruction is not supported on IA-32 processors earlier than the Intel486 processor.

#### Operation

WriteBack(InternalCaches); Flush(InternalCaches); SignalWriteBack(ExternalCaches); SignalFlush(ExternalCaches); Continue; (* Continue execution *)

Intel C/C++ Compiler Intrinsic Equivalent

WBINVD void _wbinvd(void);

#### Flags Affected

None.

#### Protected Mode Exceptions

#GP(0) If the current privilege level is not 0. #UD If the LOCK prefix is used.

WBINVD—Write Back and Invalidate Cache

Vol. 2D 6-3

INSTRUCTION SET REFERENCE, W-Z

Real-Address Mode Exceptions #UD If the LOCK prefix is used.

Virtual-8086 Mode Exceptions

#GP(0) WBINVD cannot be executed at the virtual-8086 mode.

Compatibility Mode Exceptions

Same exceptions as in protected mode.

#### 64-Bit Mode Exceptions

Same exceptions as in protected mode.

WBINVD—Write Back and Invalidate Cache

6-4 Vol. 2D

INSTRUCTION SET REFERENCE, W-Z

## WBNOINVD—Write Back and Do Not Invalidate Cache

|Opcode /<br>Instruction|Op/<br>En|64/32 bit<br>Mode<br>Support|CPUID<br>Feature<br>Flag|Description|
|---|---|---|---|---|
|F3 0F 09<br>WBNOINVD|ZO|V/V|WBNOINVD|Write back and do not flush internal caches;<br>initiate writing-back without flushing of external<br>caches.|



#### Instruction Operand Encoding

|Op/En|Tuple|Operand 1|Operand 2|Operand 3|Operand 4|
|---|---|---|---|---|---|
|ZO|N/A|N/A|N/A|N/A|N/A|



#### Description

The WBNOINVD instruction writes back all modified cache lines in the processor’s internal cache to main memory but does not invalidate (flush) the internal caches.

After executing this instruction, the processor does not wait for the external caches to complete their write-back operation before proceeding with instruction execution. It is the responsibility of hardware to respond to the cache write-back signal. The amount of time or cycles for WBNOINVD to complete will vary due to size and other factors of different cache hierarchies. As a consequence, the use of the WBNOINVD instruction can have an impact on logical processor interrupt/event response time.

The WBNOINVD instruction is a privileged instruction. When the processor is running in protected mode, the CPL of a program or procedure must be 0 to execute this instruction. This instruction is also a serializing instruction (see “Serializing Instructions” in Chapter 9 of the _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 3A_ ).

This instruction’s operation is the same in non-64-bit modes and 64-bit mode.

#### Operation

WriteBack(InternalCaches); Continue; (* Continue execution *)

Intel C/C++ Compiler Intrinsic Equivalent

WBNOINVD void _wbnoinvd(void);

#### Flags Affected

None.

#### Protected Mode Exceptions

#GP(0) If the current privilege level is not 0. #UD If the LOCK prefix is used. Real-Address Mode Exceptions #UD If the LOCK prefix is used.

#### Virtual-8086 Mode Exceptions

#GP(0) WBNOINVD cannot be executed at the virtual-8086 mode.

#### Compatibility Mode Exceptions

Same exceptions as in protected mode.

WBNOINVD—Write Back and Do Not Invalidate Cache

Vol. 2D 6-5

INSTRUCTION SET REFERENCE, W-Z

#### 64-Bit Mode Exceptions

Same exceptions as in protected mode.

WBNOINVD—Write Back and Do Not Invalidate Cache

6-6 Vol. 2D

INSTRUCTION SET REFERENCE, W-Z

## WRFSBASE/WRGSBASE—Write FS/GS Segment Base

|Opcode/<br>Instruction|Op/<br>En|64/32-<br>bit<br>Mode|CPUID Fea-<br>ture Flag|Description|
|---|---|---|---|---|
|F3 0F AE /2<br>WRFSBASE r32|M|V/I|FSGSBASE|Load the FS base address with the 32-bit value in the<br>source register.|
|F3 REX.W 0F AE /2<br>WRFSBASE r64|M|V/I|FSGSBASE|Load the FS base address with the 64-bit value in the<br>source register.|
|F3 0F AE /3<br>WRGSBASE r32|M|V/I|FSGSBASE|Load the GS base address with the 32-bit value in the<br>source register.|
|F3 REX.W 0F AE /3<br>WRGSBASE r64|M|V/I|FSGSBASE|Load the GS base address with the 64-bit value in the<br>source register.|



#### Instruction Operand Encoding

|Op/En|Operand 1|Operand 2|Operand 3|Operand 4|
|---|---|---|---|---|
|M|ModRM:r/m (r)|N/A|N/A|N/A|



#### Description

Loads the FS or GS segment base address with the general-purpose register indicated by the modR/M:r/m field.

The source operand may be either a 32-bit or a 64-bit general-purpose register. The REX.W prefix indicates the operand size is 64 bits. If no REX.W prefix is used, the operand size is 32 bits; the upper 32 bits of the source register are ignored and upper 32 bits of the base address (for FS or GS) are cleared.

This instruction is supported only in 64-bit mode.

#### Operation

FS/GS segment base address := SRC;

#### Flags Affected

None

C/C++ Compiler Intrinsic Equivalent

WRFSBASE: void _writefsbase_u32( unsigned int ); WRFSBASE: _writefsbase_u64( unsigned __int64 ); WRGSBASE: void _writegsbase_u32( unsigned int ); WRGSBASE: _writegsbase_u64( unsigned __int64 );

Protected Mode Exceptions #UD The WRFSBASE and WRGSBASE instructions are not recognized in protected mode. Real-Address Mode Exceptions #UD The WRFSBASE and WRGSBASE instructions are not recognized in real-address mode. Virtual-8086 Mode Exceptions #UD The WRFSBASE and WRGSBASE instructions are not recognized in virtual-8086 mode. Compatibility Mode Exceptions #UD The WRFSBASE and WRGSBASE instructions are not recognized in compatibility mode.

WRFSBASE/WRGSBASE—Write FS/GS Segment Base

Vol. 2D 6-7

INSTRUCTION SET REFERENCE, W-Z

64-Bit Mode Exceptions #UD If the LOCK prefix is used. If CR4.FSGSBASE[bit 16] = 0. If CPUID.07H.0H:EBX.FSGSBASE[bit 0] = 0 #GP(0) If the source register contains a non-canonical address.

WRFSBASE/WRGSBASE—Write FS/GS Segment Base

6-8 Vol. 2D

INSTRUCTION SET REFERENCE, W-Z

## WRMSR—Write to Model Specific Register

|Opcode|Instruction|Op/<br>En|64-Bit<br>Mode|Compat/<br>Leg Mode|Description|
|---|---|---|---|---|---|
|0F 30|WRMSR|ZO|Valid|Valid|Write the value in EDX:EAX to MSR specified<br>by ECX.|



#### Instruction Operand Encoding

|Op/En|Operand 1|Operand 2|Operand 3|Operand 4|
|---|---|---|---|---|
|ZO|N/A|N/A|N/A|N/A|



#### Description

Writes the contents of registers EDX:EAX into the 64-bit model specific register (MSR) specified in the ECX register. (On processors that support the Intel 64 architecture, the high-order 32 bits of RCX are ignored.) The contents of the EDX register are copied to high-order 32 bits of the selected MSR and the contents of the EAX register are copied to low-order 32 bits of the MSR. (On processors that support the Intel 64 architecture, the high-order 32 bits of each of RAX and RDX are ignored.) Undefined or reserved bits in an MSR should be set to values previously read.

This instruction must be executed at privilege level 0 or in real-address mode; otherwise, a general protection exception #GP(0) is generated. Specifying a reserved or unimplemented MSR address in ECX will also cause a general protection exception. The processor will also generate a general protection exception if software attempts to write to bits in a reserved MSR.

When the WRMSR instruction is used to write to an MTRR, the TLBs are invalidated. This includes global entries (see “Translation Lookaside Buffers (TLBs)” in Chapter 3 of the _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 3A_ ).

MSRs control functions for testability, execution tracing, performance-monitoring and machine check errors. Chapter 2, “Model-Specific Registers (MSRs),” of the _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 4_ , lists all MSRs that can be written with this instruction and their addresses. Note that each processor family has its own set of MSRs.

The WRMSR instruction is a serializing instruction (see “Serializing Instructions” in Chapter 9 of the _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 3A_ ). Note that WRMSR to the IA32_TSC_DEADLINE MSR (MSR index 6E0H) and the X2APIC MSRs (MSR indices 802H to 83FH) are not serializing.

The CPUID instruction should be used to determine whether MSRs are supported (CPUID.01H:EDX[5] = 1) before using this instruction.

#### IA-32 Architecture Compatibility

The MSRs and the ability to read them with the WRMSR instruction were introduced into the IA-32 architecture with the Pentium processor. Execution of this instruction by an IA-32 processor earlier than the Pentium processor results in an invalid opcode exception #UD.

#### Operation

MSR[ECX] := EDX:EAX;

#### Flags Affected

None.

WRMSR—Write to Model Specific Register

Vol. 2D 6-9

INSTRUCTION SET REFERENCE, W-Z

#### Protected Mode Exceptions

#GP(0) If the current privilege level is not 0.

If the value in ECX specifies a reserved or unimplemented MSR address.

If the value in EDX:EAX sets bits that are reserved in the MSR specified by ECX.

If the source register contains a non-canonical address and ECX specifies one of the following MSRs: IA32_DS_AREA, IA32_FS_BASE, IA32_GS_BASE, IA32_KERNEL_GS_BASE, IA32_LSTAR, IA32_SYSENTER_EIP, IA32_SYSENTER_ESP.

#UD If the LOCK prefix is used.

#### Real-Address Mode Exceptions

#GP If the value in ECX specifies a reserved or unimplemented MSR address.

If the value in EDX:EAX sets bits that are reserved in the MSR specified by ECX.

If the source register contains a non-canonical address and ECX specifies one of the following MSRs: IA32_DS_AREA, IA32_FS_BASE, IA32_GS_BASE, IA32_KERNEL_GS_BASE, IA32_LSTAR, IA32_SYSENTER_EIP, IA32_SYSENTER_ESP.

#UD If the LOCK prefix is used.

Virtual-8086 Mode Exceptions

#GP(0) The WRMSR instruction is not recognized in virtual-8086 mode.

#### Compatibility Mode Exceptions

Same exceptions as in protected mode.

#### 64-Bit Mode Exceptions

Same exceptions as in protected mode.

WRMSR—Write to Model Specific Register

6-10 Vol. 2D

INSTRUCTION SET REFERENCE, W-Z

## WRPKRU—Write Data to User Page Key Register

|Opcode/<br>Instruction|Op/<br>En|64/32bit<br>Mode<br>Support|CPUID<br>Feature<br>Flag|Description|
|---|---|---|---|---|
|NP 0F 01 EF|ZO|V/V|OSPKE|Writes EAX into PKRU.|
|WRPKRU|||||



#### Instruction Operand Encoding

|Op/En|Operand 1|Operand 2|Operand 3|Operand 4|
|---|---|---|---|---|
|ZO|N/A|N/A|N/A|N/A|



#### Description

Writes the value of EAX into PKRU. ECX and EDX must be 0 when WRPKRU is executed; otherwise, a generalprotection exception (#GP) occurs.

WRPKRU can be executed only if CR4.PKE = 1; otherwise, an invalid-opcode exception (#UD) occurs. Software can discover the value of CR4.PKE by examining CPUID.(EAX=07H,ECX=0H):ECX.OSPKE [bit 4].

On processors that support the Intel 64 Architecture, the high-order 32-bits of RCX, RDX, and RAX are ignored.

WRPKRU will never execute speculatively. Memory accesses affected by PKRU register will not execute (even speculatively) until all prior executions of WRPKRU have completed execution and updated the PKRU register.

#### Operation

IF (ECX = 0 AND EDX = 0) THEN PKRU := EAX; ELSE #GP(0);

FI;

Flags Affected

None.

C/C++ Compiler Intrinsic Equivalent

WRPKRU: void _wrpkru(uint32_t);

Protected Mode Exceptions

#GP(0) If ECX ≠ 0. If EDX ≠ 0. #UD If the LOCK prefix is used. If CR4.PKE = 0.

#### Real-Address Mode Exceptions

Same exceptions as in protected mode.

#### Virtual-8086 Mode Exceptions

Same exceptions as in protected mode.

#### Compatibility Mode Exceptions

Same exceptions as in protected mode.

WRPKRU—Write Data to User Page Key Register

Vol. 2D 6-11

INSTRUCTION SET REFERENCE, W-Z

#### 64-Bit Mode Exceptions

Same exceptions as in protected mode.

WRPKRU—Write Data to User Page Key Register

6-12 Vol. 2D

INSTRUCTION SET REFERENCE, W-Z

## WRSSD/WRSSQ—Write to Shadow Stack

|Opcode/<br>Instruction|Op/<br>En|64/32<br>bit Mode<br>Support|CPUID<br>Feature<br>Flag|Description|
|---|---|---|---|---|
|0F 38 F6 !(11):rrr:bbb<br>WRSSD m32, r32|MR|V/V|CET_SS|Write 4 bytes to shadow stack.|
|REX.W 0F 38 F6 !(11):rrr:bbb<br>WRSSQ m64, r64|MR|V/N.E.|CET_SS|Write 8 bytes to shadow stack.|



Instruction Operand Encoding

|Op/En|Operand 1|Operand 2|Operand 3|Operand 4|
|---|---|---|---|---|
|MR|ModRM:r/m (w)|ModRM:reg (r)|N/A|N/A|



#### Description

Writes bytes in register source to the shadow stack.

#### Operation

IF CPL = 3 IF (CR4.CET & IA32_U_CET.SH_STK_EN) = 0 THEN #UD; FI; IF (IA32_U_CET.WR_SHSTK_EN) = 0 THEN #UD; FI;

ELSE IF (CR4.CET & IA32_S_CET.SH_STK_EN) = 0 THEN #UD; FI; IF (IA32_S_CET.WR_SHSTK_EN) = 0 THEN #UD; FI; FI; DEST_LA = Linear_Address(mem operand) IF (operand size is 64 bit) THEN (* Destination not 8B aligned *) IF DEST_LA[2:0] THEN GP(0); FI; Shadow_stack_store 8 bytes of SRC to DEST_LA;

ELSE (* Destination not 4B aligned *) IF DEST_LA[1:0] THEN GP(0); FI; Shadow_stack_store 4 bytes of SRC[31:0] to DEST_LA; FI;

#### Flags Affected

None.

C/C++ Compiler Intrinsic Equivalent WRSSD void _wrssd(__int32, void *); WRSSQ void _wrssq(__int64, void *);

WRSSD/WRSSQ—Write to Shadow Stack

Vol. 2D 6-13

INSTRUCTION SET REFERENCE, W-Z

#### Protected Mode Exceptions

#UD If the LOCK prefix is used. If CR4.CET = 0. If CPL = 3 and IA32_U_CET.SH_STK_EN = 0. If CPL < 3 and IA32_S_CET.SH_STK_EN = 0. If CPL = 3 and IA32_U_CET.WR_SHSTK_EN = 0. If CPL < 3 and IA32_S_CET.WR_SHSTK_EN = 0. #GP(0) If a memory operand effective address is outside the CS, DS, ES, FS, or GS segment limit. If destination is located in a non-writeable segment.

If the DS, ES, FS, or GS register is used to access memory and it contains a NULL segment selector.

If linear address of destination is not 4 byte aligned.

#SS(0) If a memory operand effective address is outside the SS segment limit. #PF(fault-code) If a page fault occurs if destination is not a user shadow stack when CPL3 and not a supervisor shadow stack when CPL < 3. Other terminal and non-terminal faults.

Real-Address Mode Exceptions

#UD The WRSS instruction is not recognized in real-address mode.

Virtual-8086 Mode Exceptions #UD The WRSS instruction is not recognized in virtual-8086 mode.

Compatibility Mode Exceptions

#UD If the LOCK prefix is used. If CR4.CET = 0. If CPL = 3 and IA32_U_CET.SH_STK_EN = 0. If CPL < 3 and IA32_S_CET.SH_STK_EN = 0. If CPL = 3 and IA32_U_CET.WR_SHSTK_EN = 0. If CPL < 3 and IA32_S_CET.WR_SHSTK_EN = 0. #PF(fault-code) If a page fault occurs if destination is not a user shadow stack when CPL3 and not a supervisor shadow stack when CPL < 3. Other terminal and non-terminal faults.

64-Bit Mode Exceptions

#UD If the LOCK prefix is used. If CR4.CET = 0. If CPL = 3 and IA32_U_CET.SH_STK_EN = 0. If CPL < 3 and IA32_S_CET.SH_STK_EN = 0. If CPL = 3 and IA32_U_CET.WR_SHSTK_EN = 0. If CPL < 3 and IA32_S_CET.WR_SHSTK_EN = 0. #GP(0) If a memory address is in a non-canonical form. If linear address of destination is not 4 byte aligned. #PF(fault-code) If a page fault occurs if destination is not a user shadow stack when CPL3 and not a supervisor shadow stack when CPL < 3. Other terminal and non-terminal faults.

WRSSD/WRSSQ—Write to Shadow Stack

6-14 Vol. 2D

INSTRUCTION SET REFERENCE, W-Z

## WRUSSD/WRUSSQ—Write to User Shadow Stack

|Opcode/<br>Instruction|Op/<br>En|64/32<br>bit Mode<br>Support|CPUID<br>Feature<br>Flag|Description|
|---|---|---|---|---|
|66 0F 38 F5 !(11):rrr:bbb<br>WRUSSD m32, r32|MR|V/V|CET_SS|Write 4 bytes to shadow stack.|
|66 REX.W 0F 38 F5 !(11):rrr:bbb<br>WRUSSQ m64, r64|MR|V/N.E.|CET_SS|Write 8 bytes to shadow stack.|



|||Instruction Operand En|coding||
|---|---|---|---|---|
|Op/En|Operand 1|Operand 2|Operand 3|Operand 4|
|MR|ModRM:r/m (w)|ModRM:reg (r)|N/A|N/A|



#### Description

Writes bytes in register source to a user shadow stack page. The WRUSS instruction can be executed only if CPL = 0, however the processor treats its shadow-stack accesses as user accesses.

#### Operation

IF CR4.CET = 0 THEN #UD; FI; IF CPL > 0 THEN #GP(0); FI; DEST_LA = Linear_Address(mem operand) IF (operand size is 64 bit)

THEN

- (* Destination not 8B aligned *) IF DEST_LA[2:0]

THEN GP(0); FI;

Shadow_stack_store 8 bytes of SRC to DEST_LA as user-mode access;

##### ELSE

- (* Destination not 4B aligned *) IF DEST_LA[1:0]

THEN GP(0); FI;

Shadow_stack_store 4 bytes of SRC[31:0] to DEST_LA as user-mode access;

FI;

#### Flags Affected

None.

C/C++ Compiler Intrinsic Equivalent

WRUSSD void _wrussd(__int32, void *); WRUSSQ void _wrussq(__int64, void *);

WRUSSD/WRUSSQ—Write to User Shadow Stack

Vol. 2D 6-15

INSTRUCTION SET REFERENCE, W-Z

#### Protected Mode Exceptions

#UD If the LOCK prefix is used. If CR4.CET = 0. #GP(0) If a memory operand effective address is outside the CS, DS, ES, FS, or GS segment limit. If destination is located in a non-writeable segment. If the DS, ES, FS, or GS register is used to access memory and it contains a NULL segment selector.

If linear address of destination is not 4 byte aligned. If CPL is not 0.

#SS(0) If a memory operand effective address is outside the SS segment limit. #PF(fault-code) If destination is not a user shadow stack. Other terminal and non-terminal faults.

#### Real-Address Mode Exceptions

#UD The WRUSS instruction is not recognized in real-address mode.

#### Virtual-8086 Mode Exceptions

#UD The WRUSS instruction is not recognized in virtual-8086 mode.

#### Compatibility Mode Exceptions

#UD If the LOCK prefix is used. If CR4.CET = 0. #GP(0) If a memory address is in a non-canonical form. If linear address of destination is not 4 byte aligned. If CPL is not 0. #SS(0) If a memory address referencing the SS segment is in a non-canonical form. #PF(fault-code) If destination is not a user shadow stack. Other terminal and non-terminal faults.

#### 64-Bit Mode Exceptions

#UD If the LOCK prefix is used. If CR4.CET = 0. #GP(0) If a memory address is in a non-canonical form. If linear address of destination is not 4 byte aligned. If CPL is not 0. #PF(fault-code) If destination is not a user shadow stack. Other terminal and non-terminal faults.

WRUSSD/WRUSSQ—Write to User Shadow Stack

6-16 Vol. 2D

INSTRUCTION SET REFERENCE, W-Z

## XABORT—Transactional Abort

|Opcode/Instruction|Op/<br>En|64/32bit<br>Mode<br>Support|CPUID<br>Feature<br>Flag|Description|
|---|---|---|---|---|
|C6 F8 ib|A|V/V|RTM|Causes an RTM abort if in RTM execution.|
|XABORT imm8|||||



#### Instruction Operand Encoding

|Op/En|Operand 1|Operand2|Operand3|Operand4|
|---|---|---|---|---|
|A|imm8|N/A|N/A|N/A|



#### Description

XABORT forces an RTM abort. Following an RTM abort, the logical processor resumes execution at the fallback address computed through the outermost XBEGIN instruction. The EAX register is updated to reflect an XABORT instruction caused the abort, and the imm8 argument will be provided in bits 31:24 of EAX.

Operation XABORT IF RTM_ACTIVE = 0 THEN Treat as NOP; ELSE

GOTO RTM_ABORT_PROCESSING;

FI;

(* For any RTM abort condition encountered during RTM execution *) RTM_ABORT_PROCESSING: Restore architectural register state; Discard memory updates performed in transaction; Update EAX with status and XABORT argument; RTM_NEST_COUNT:= 0; RTM_ACTIVE:= 0; SUSLDTRK_ACTIVE := 0; IF 64-bit Mode THEN RIP:= fallbackRIP; ELSE EIP := fallbackEIP; FI; END Flags Affected None

Intel C/C++ Compiler Intrinsic Equivalent XABORT: void _xabort( unsigned int);

SIMD Floating-Point Exceptions None

XABORT—Transactional Abort

Vol. 2D 6-17

INSTRUCTION SET REFERENCE, W-Z

Other Exceptions #UD CPUID.(EAX=7, ECX=0):EBX.RTM[bit 11] = 0. If LOCK prefix is used.

XABORT—Transactional Abort

6-18 Vol. 2D

INSTRUCTION SET REFERENCE, W-Z

XACQUIRE/XRELEASE—Hardware Lock Elision Prefix Hints

|Opcode/Instruction|64/32bit<br>Mode<br>Support|CPUID<br>Feature<br>Flag<br>|Description|
|---|---|---|---|
|F2|V/V|HLE<sup>1</sup>|A hint used with an “XACQUIRE-enabled“ instruction to start lock|
|XACQUIRE|||elision on the instruction memoryoperand address.|
|F3|V/V|HLE|A hint used with an “XRELEASE-enabled“ instruction to end lock|
|XRELEASE|||elision on the instruction memoryoperand address.|



NOTES:

1. Software is not required to check the HLE feature flag to use XACQUIRE or XRELEASE, as they are treated as regular prefix if HLE feature flag reports 0.

#### Description

The XACQUIRE prefix is a hint to start lock elision on the memory address specified by the instruction and the XRELEASE prefix is a hint to end lock elision on the memory address specified by the instruction.

The XACQUIRE prefix hint can only be used with the following instructions (these instructions are also referred to as XACQUIRE-enabled when used with the XACQUIRE prefix):

- Instructions with an explicit LOCK prefix (F0H) prepended to forms of the instruction where the destination operand is a memory operand: ADD, ADC, AND, BTC, BTR, BTS, CMPXCHG, CMPXCHG8B, DEC, INC, NEG, NOT, OR, SBB, SUB, XOR, XADD, and XCHG.

- The XCHG instruction either with or without the presence of the LOCK prefix.

The XRELEASE prefix hint can only be used with the following instructions (also referred to as XRELEASE-enabled when used with the XRELEASE prefix):

- Instructions with an explicit LOCK prefix (F0H) prepended to forms of the instruction where the destination operand is a memory operand: ADD, ADC, AND, BTC, BTR, BTS, CMPXCHG, CMPXCHG8B, DEC, INC, NEG, NOT, OR, SBB, SUB, XOR, XADD, and XCHG.

- The XCHG instruction either with or without the presence of the LOCK prefix.

- The “MOV mem, reg” (Opcode 88H/89H) and “MOV mem, imm” (Opcode C6H/C7H) instructions. In these cases, the XRELEASE is recognized without the presence of the LOCK prefix.

The lock variables must satisfy the guidelines described in _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ , Section 16.3.3, for elision to be successful, otherwise an HLE abort may be signaled.

If an encoded byte sequence that meets XACQUIRE/XRELEASE requirements includes both prefixes, then the HLE semantic is determined by the prefix byte that is placed closest to the instruction opcode. For example, an F3F2C6 will not be treated as a XRELEASE-enabled instruction since the F2H (XACQUIRE) is closest to the instruction opcode C6. Similarly, an F2F3F0 prefixed instruction will be treated as a XRELEASE-enabled instruction since F3H (XRELEASE) is closest to the instruction opcode.

XACQUIRE/XRELEASE—Hardware Lock Elision Prefix Hints

Vol. 2D 6-19

INSTRUCTION SET REFERENCE, W-Z

##### **Intel 64 and IA-32 Compatibility**

The effect of the XACQUIRE/XRELEASE prefix hint is the same in non-64-bit modes and in 64-bit mode.

For instructions that do not support the XACQUIRE hint, the presence of the F2H  prefix behaves the same way as prior hardware, according to

- REPNE/REPNZ semantics for string instructions,

- Serve as SIMD prefix for legacy SIMD instructions operating on XMM register

- Cause #UD if prepending the VEX prefix.

- Undefined for non-string instructions or other situations.

For instructions that do not support the XRELEASE hint, the presence of the F3H prefix behaves the same way as in prior hardware, according to

- REP/REPE/REPZ semantics for string instructions,

- Serve as SIMD prefix for legacy SIMD instructions operating on XMM register

- Cause #UD if prepending the VEX prefix.

- Undefined for non-string instructions or other situations.

#### Operation

##### XACQUIRE

IF XACQUIRE-enabled instruction THEN IF (HLE_NEST_COUNT < MAX_HLE_NEST_COUNT) THEN HLE_NEST_COUNT++ IF (HLE_NEST_COUNT = 1) THEN HLE_ACTIVE := 1 IF 64-bit mode THEN restartRIP := instruction pointer of the XACQUIRE-enabled instruction ELSE restartEIP := instruction pointer of the XACQUIRE-enabled instruction FI; Enter HLE Execution (* record register state, start tracking memory state *) FI; (* HLE_NEST_COUNT = 1*) IF ElisionBufferAvailable THEN Allocate elision buffer Record address and data for forwarding and commit checking Perform elision ELSE Perform lock acquire operation transactionally but without elision FI; ELSE (* HLE_NEST_COUNT = MAX_HLE_NEST_COUNT*) GOTO HLE_ABORT_PROCESSING FI; ELSE

Treat instruction as non-XACQUIRE F2H prefixed legacy instruction

FI;

XACQUIRE/XRELEASE—Hardware Lock Elision Prefix Hints

6-20 Vol. 2D

INSTRUCTION SET REFERENCE, W-Z

##### XRELEASE

IF XRELEASE-enabled instruction THEN IF (HLE_NEST_COUNT > 0) THEN HLE_NEST_COUNT-IF lock address matches in elision buffer THEN IF lock satisfies address and value requirements THEN Deallocate elision buffer ELSE GOTO HLE_ABORT_PROCESSING FI; FI; IF (HLE_NEST_COUNT = 0) THEN IF NoAllocatedElisionBuffer THEN Try to commit transactional execution IF fail to commit transactional execution THEN GOTO HLE_ABORT_PROCESSING; ELSE (* commit success *) HLE_ACTIVE := 0 FI; ELSE GOTO HLE_ABORT_PROCESSING FI; FI; FI; (* HLE_NEST_COUNT > 0 *) ELSE Treat instruction as non-XRELEASE F3H prefixed legacy instruction

FI;

(* For any HLE abort condition encountered during HLE execution *) HLE_ABORT_PROCESSING: HLE_ACTIVE := 0 HLE_NEST_COUNT := 0 Restore architectural register state Discard memory updates performed in transaction Free any allocated lock elision buffers IF 64-bit mode THEN RIP := restartRIP ELSE EIP := restartEIP FI; Execute and retire instruction at RIP (or EIP) and ignore any HLE hint END

XACQUIRE/XRELEASE—Hardware Lock Elision Prefix Hints

Vol. 2D 6-21

INSTRUCTION SET REFERENCE, W-Z

SIMD Floating-Point Exceptions None Other Exceptions #GP(0) If the use of prefix causes instruction length to exceed 15 bytes.

XACQUIRE/XRELEASE—Hardware Lock Elision Prefix Hints

6-22 Vol. 2D

INSTRUCTION SET REFERENCE, W-Z

## XADD—Exchange and Add

|Opcode|Instruction|Op/<br>En|64-Bit<br>Mode|Compat/<br>Leg Mode|Description|
|---|---|---|---|---|---|
|0F C0 /_r_|XADD_r/m8, r8_|MR|Valid|Valid|Exchange_r8_and_r/m8_; load sum into_r/m8_.|
|REX + 0F C0 /_r_|XADD_r/m8*, r8*_|MR|Valid|N.E.|Exchange_r8_and_r/m8_; load sum into_r/m8_.|
|0F C1 /_r_|XADD_r/m16, r16_|MR|Valid|Valid|Exchange_r16_and_r/m16_; load sum into_r/m16_.|
|0F C1 /_r_|XADD_r/m32, r32_|MR|Valid|Valid|Exchange_r32_and_r/m32_; load sum into_r/m32_.|
|REX.W + 0F C1 /_r_|XADD_r/m64, r64_|MR|Valid|N.E.|Exchange_r64_and_r/m64_; load sum into_r/m64_.|



NOTES:

* In 64-bit mode, r/m8 can not be encoded to access the following byte registers if a REX prefix is used: AH, BH, CH, DH.

|||Instruction Operan|d Encoding||
|---|---|---|---|---|
|Op/En|Operand 1|Operand 2|Operand 3|Operand 4|
|MR|ModRM:r/m (r, w)|ModRM:reg (r, w)|N/A|N/A|



#### Description

Exchanges the first operand (destination operand) with the second operand (source operand), then loads the sum of the two values into the destination operand. The destination operand can be a register or a memory location; the source operand is a register.

In 64-bit mode, the instruction’s default operation size is 32 bits. Using a REX prefix in the form of REX.R permits access to additional registers (R8-R15). Using a REX prefix in the form of REX.W promotes operation to 64 bits. See the summary chart at the beginning of this section for encoding data and limits.

This instruction can be used with a LOCK prefix to allow the instruction to be executed atomically.

#### IA-32 Architecture Compatibility

IA-32 processors earlier than the Intel486 processor do not recognize this instruction. If this instruction is used, you should provide an equivalent code sequence that runs on earlier processors.

#### Operation

TEMP := SRC + DEST; SRC := DEST; DEST := TEMP;

#### Flags Affected

The CF, PF, AF, SF, ZF, and OF flags are set according to the result of the addition, which is stored in the destination operand.

#### Protected Mode Exceptions

|#GP(0)|If the destination is located in a non-writable segment.|
|---|---|
||If a memory operand effective address is outside the CS, DS, ES, FS, or GS segment limit.<br>If the DS, ES, FS, or GS register contains a NULL segment selector.|
|#SS(0)|If a memory operand effective address is outside the SS segment limit.|
|#PF(fault-code)|If a page fault occurs.|
|#AC(0)|If alignment checking is enabled and an unaligned memory reference is made while the<br>current privilege level is 3.|
|#UD|If the LOCK prefix is used but the destination is not a memory operand.|



XADD—Exchange and Add

Vol. 2D 6-23

INSTRUCTION SET REFERENCE, W-Z

#### Real-Address Mode Exceptions

#GP If a memory operand effective address is outside the CS, DS, ES, FS, or GS segment limit. #SS If a memory operand effective address is outside the SS segment limit. #UD If the LOCK prefix is used but the destination is not a memory operand.

#### Virtual-8086 Mode Exceptions

#GP(0) If a memory operand effective address is outside the CS, DS, ES, FS, or GS segment limit. #SS(0) If a memory operand effective address is outside the SS segment limit. #PF(fault-code) If a page fault occurs. #AC(0) If alignment checking is enabled and an unaligned memory reference is made. #UD If the LOCK prefix is used but the destination is not a memory operand.

#### Compatibility Mode Exceptions

Same exceptions as in protected mode.

#### 64-Bit Mode Exceptions

#SS(0) If a memory address referencing the SS segment is in a non-canonical form. #GP(0) If the memory address is in a non-canonical form. #PF(fault-code) If a page fault occurs. #AC(0) If alignment checking is enabled and an unaligned memory reference is made while the current privilege level is 3. #UD If the LOCK prefix is used but the destination is not a memory operand.

6-24 Vol. 2D

XADD—Exchange and Add

INSTRUCTION SET REFERENCE, W-Z

## XBEGIN—Transactional Begin

|Opcode/Instruction|Op/<br>En|64/32bit<br>Mode<br>Support|CPUID<br>Feature<br>Flag|Description|
|---|---|---|---|---|
|C7 F8<br>XBEGIN rel16|A|V/V|RTM|Specifies the start of an RTM region. Provides a 16-bit relative<br>offset to compute the address of the fallback instruction address at<br>which execution resumes followingan RTM abort.|
|C7 F8<br>XBEGIN rel32|A|V/V|RTM|Specifies the start of an RTM region. Provides a 32-bit relative<br>offset to compute the address of the fallback instruction address at<br>which execution resumes following an RTM abort.|



#### Instruction Operand Encoding

|Op/En|Operand 1|Operand2|Operand3|Operand4|
|---|---|---|---|---|
|A|Offset|N/A|N/A|N/A|



#### Description

The XBEGIN instruction specifies the start of an RTM code region. If the logical processor was not already in transactional execution, then the XBEGIN instruction causes the logical processor to transition into transactional execution. The XBEGIN instruction that transitions the logical processor into transactional execution is referred to as the outermost XBEGIN instruction. The instruction also specifies a relative offset to compute the address of the fallback code path following a transactional abort. (Use of the 16-bit operand size does not cause this address to be truncated to 16 bits, unlike a near jump to a relative offset.)

On an RTM abort, the logical processor discards all architectural register and memory updates performed during the RTM execution and restores architectural state to that corresponding to the outermost XBEGIN instruction. The fallback address following an abort is computed from the outermost XBEGIN instruction.

Execution of XBEGIN while in a suspend read address tracking region causes a transactional abort.

#### Operation

##### XBEGIN

IF RTM_NEST_COUNT < MAX_RTM_NEST_COUNT AND SUSLDTRK_ACTIVE = 0

THEN RTM_NEST_COUNT++ IF RTM_NEST_COUNT = 1 THEN IF 64-bit Mode THEN IF OperandSize = 16 THEN fallbackRIP := RIP + SignExtend64(rel16); ELSE fallbackRIP := RIP + SignExtend64(rel32); FI; IF fallbackRIP is not canonical THEN #GP(0); FI; ELSE IF OperandSize = 16 THEN fallbackEIP := EIP + SignExtend32(rel16); ELSE fallbackEIP := EIP + rel32; FI; IF fallbackEIP outside code segment limit THEN #GP(0); FI; FI; RTM_ACTIVE := 1

XBEGIN—Transactional Begin

Vol. 2D 6-25

INSTRUCTION SET REFERENCE, W-Z

Enter RTM Execution (* record register state, start tracking memory state*) FI; (* RTM_NEST_COUNT = 1 *) ELSE (* RTM_NEST_COUNT = MAX_RTM_NEST_COUNT OR SUSLDTRK_ACTIVE = 1 *) GOTO RTM_ABORT_PROCESSING FI; (* For any RTM abort condition encountered during RTM execution *) RTM_ABORT_PROCESSING: Restore architectural register state Discard memory updates performed in transaction Update EAX with status RTM_NEST_COUNT := 0 RTM_ACTIVE := 0 SUSLDTRK_ACTIVE := 0 IF 64-bit mode THEN RIP := fallbackRIP ELSE EIP := fallbackEIP FI; END Flags Affected None Intel C/C++ Compiler Intrinsic Equivalent XBEGIN: unsigned int _xbegin( void );

SIMD Floating-Point Exceptions None Protected Mode Exceptions #UD CPUID.(EAX=7, ECX=0):EBX.RTM[bit 11]=0. If LOCK prefix is used. #GP(0) If the fallback address is outside the CS segment. Real-Address Mode Exceptions #GP(0) If the fallback address is outside the address space 0000H and FFFFH. #UD CPUID.(EAX=7, ECX=0):EBX.RTM[bit 11]=0. If LOCK prefix is used. Virtual-8086 Mode Exceptions #GP(0) If the fallback address is outside the address space 0000H and FFFFH. #UD CPUID.(EAX=7, ECX=0):EBX.RTM[bit 11]=0. If LOCK prefix is used.

Compatibility Mode Exceptions

Same exceptions as in protected mode.

XBEGIN—Transactional Begin

6-26 Vol. 2D

INSTRUCTION SET REFERENCE, W-Z

64-bit Mode Exceptions #UD CPUID.(EAX=7, ECX=0):EBX.RTM[bit 11] = 0. If LOCK prefix is used. #GP(0) If the fallback address is non-canonical.

XBEGIN—Transactional Begin

Vol. 2D 6-27

INSTRUCTION SET REFERENCE, W-Z

## XCHG—Exchange Register/Memory With Register

|Opcode|Instruction|Op/<br>En|64-Bit<br>Mode|Compat/<br>Leg Mode|Description|
|---|---|---|---|---|---|
|90+rw|XCHG AX, r16|O|Valid|Valid|Exchange r16 with AX.|
|90+rw|XCHG r16, AX|O|Valid|Valid|Exchange AX with r16.|
|90+rd|XCHG EAX, r32|O|Valid|Valid|Exchange r32 with EAX.|
|REX.W + 90+rd|XCHG RAX, r64|O|Valid|N.E.|Exchange r64 with RAX.|
|90+rd|XCHG r32, EAX|O|Valid|Valid|Exchange EAX with r32.|
|REX.W + 90+rd|XCHG r64, RAX|O|Valid|N.E.|Exchange RAX with r64.|
|86 /r|XCHG r/m8, r8|MR|Valid|Valid|Exchange r8 (byte register) with byte from<br>r/m8.|
|REX + 86 /r|XCHG r/m8*, r8*|MR|Valid|N.E.|Exchange r8 (byte register) with byte from<br>r/m8.|
|86 /r|XCHG r8, r/m8|RM|Valid|Valid|Exchange byte from r/m8 with r8 (byte<br>register).|
|REX + 86 /r|XCHG r8*, r/m8*|RM|Valid|N.E.|Exchange byte from r/m8 with r8 (byte<br>register).|
|87 /r|XCHG r/m16, r16|MR|Valid|Valid|Exchange r16 with word from r/m16.|
|87 /r|XCHG r16, r/m16|RM|Valid|Valid|Exchange word from r/m16 with r16.|
|87 /r|XCHG r/m32, r32|MR|Valid|Valid|Exchange r32 with doubleword from r/m32.|
|REX.W + 87 /r|XCHG r/m64, r64|MR|Valid|N.E.|Exchange r64 with quadword from r/m64.|
|87 /r|XCHG r32, r/m32|RM|Valid|Valid|Exchange doubleword from r/m32 with r32.|
|REX.W + 87 /r|XCHG r64, r/m64|RM|Valid|N.E.|Exchange quadword from r/m64 with r64.|



NOTES:

* In 64-bit mode, r/m8 can not be encoded to access the following byte registers if a REX prefix is used: AH, BH, CH, DH.

Instruction Operand Encoding

|Op/En|Operand 1|Operand 2|Operand 3|Operand 4|
|---|---|---|---|---|
|O|AX/EAX/RAX (r, w)|opcode + rd (r, w)|N/A|N/A|
|O|opcode + rd (r, w)|AX/EAX/RAX (r, w)|N/A|N/A|
|MR|ModRM:r/m (r, w)|ModRM:reg (r)|N/A|N/A|
|RM|ModRM:reg (w)|ModRM:r/m (r)|N/A|N/A|



#### Description

Exchanges the contents of the destination (first) and source (second) operands. The operands can be two generalpurpose registers or a register and a memory location. If a memory operand is referenced, the processor’s locking protocol is automatically implemented for the duration of the exchange operation, regardless of the presence or absence of the LOCK prefix or of the value of the IOPL. (See the LOCK prefix description in this chapter for more information on the locking protocol.)

This instruction is useful for implementing semaphores or similar data structures for process synchronization. (See “Bus Locking” in Chapter 9 of the _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 3A_ , for more information on bus locking.)

The XCHG instruction can also be used instead of the BSWAP instruction for 16-bit operands.

In 64-bit mode, the instruction’s default operation size is 32 bits. Using a REX prefix in the form of REX.R permits access to additional registers (R8-R15). Using a REX prefix in the form of REX.W promotes operation to 64 bits. See the summary chart at the beginning of this section for encoding data and limits.

XCHG—Exchange Register/Memory With Register

6-28 Vol. 2D

INSTRUCTION SET REFERENCE, W-Z

### NOTE

XCHG (E)AX, (E)AX (encoded instruction byte is 90H) is an alias for NOP regardless of data size prefixes, including REX.W.

#### Operation

TEMP := DEST; DEST := SRC; SRC := TEMP;

#### Flags Affected

None.

#### Protected Mode Exceptions

#GP(0) If either operand is in a non-writable segment. If a memory operand effective address is outside the CS, DS, ES, FS, or GS segment limit. If the DS, ES, FS, or GS register contains a NULL segment selector. #SS(0) If a memory operand effective address is outside the SS segment limit. #PF(fault-code) If a page fault occurs. #AC(0) If alignment checking is enabled and an unaligned memory reference is made while the current privilege level is 3. #UD If the LOCK prefix is used but the destination is not a memory operand.

#### Real-Address Mode Exceptions

#GP If a memory operand effective address is outside the CS, DS, ES, FS, or GS segment limit. #SS If a memory operand effective address is outside the SS segment limit. #UD If the LOCK prefix is used but the destination is not a memory operand.

#### Virtual-8086 Mode Exceptions

#GP(0) If a memory operand effective address is outside the CS, DS, ES, FS, or GS segment limit. #SS(0) If a memory operand effective address is outside the SS segment limit. #PF(fault-code) If a page fault occurs. #AC(0) If alignment checking is enabled and an unaligned memory reference is made. #UD If the LOCK prefix is used but the destination is not a memory operand.

#### Compatibility Mode Exceptions

Same exceptions as in protected mode.

#### 64-Bit Mode Exceptions

#SS(0) If a memory address referencing the SS segment is in a non-canonical form. #GP(0) If the memory address is in a non-canonical form. #PF(fault-code) If a page fault occurs. #AC(0) If alignment checking is enabled and an unaligned memory reference is made while the current privilege level is 3. #UD If the LOCK prefix is used but the destination is not a memory operand.

XCHG—Exchange Register/Memory With Register

Vol. 2D 6-29

INSTRUCTION SET REFERENCE, W-Z

## XEND—Transactional End

|Opcode/Instruction|Op/<br>En|64/32bit<br>Mode<br>Support|CPUID<br>Feature<br>Flag|Description|
|---|---|---|---|---|
|NP 0F 01 D5<br>XEND|A|V/V|RTM|Specifies the end of an RTM code region.|



#### Instruction Operand Encoding

|Op/En|Operand 1|Operand2|Operand3|Operand4|
|---|---|---|---|---|
|A|N/A|N/A|N/A|N/A|



#### Description

The instruction marks the end of an RTM code region. If this corresponds to the outermost scope (that is, including this XEND instruction, the number of XBEGIN instructions is the same as number of XEND instructions), the logical processor will attempt to commit the logical processor state atomically. If the commit fails, the logical processor will rollback all architectural register and memory updates performed during the RTM execution. The logical processor will resume execution at the fallback address computed from the outermost XBEGIN instruction. The EAX register is updated to reflect RTM abort information.

Execution of XEND outside a transactional region causes a general-protection exception (#GP). Execution of XEND while in a suspend read address tracking region causes a transactional abort.

#### Operation

##### XEND

IF (RTM_ACTIVE = 0) THEN SIGNAL #GP

ELSE IF SUSLDTRK_ACTIVE = 1 THEN GOTO RTM_ABORT_PROCESSING; FI; RTM_NEST_COUNT-IF (RTM_NEST_COUNT = 0) THEN Try to commit transaction IF fail to commit transactional execution THEN GOTO RTM_ABORT_PROCESSING; ELSE (* commit success *) RTM_ACTIVE := 0 FI; FI; FI; (* For any RTM abort condition encountered during RTM execution *) RTM_ABORT_PROCESSING: Restore architectural register state Discard memory updates performed in transaction Update EAX with status RTM_NEST_COUNT := 0 RTM_ACTIVE := 0 SUSLDTRK_ACTIVE := 0 IF 64-bit Mode THEN RIP := fallbackRIP

6-30 Vol. 2D

XEND—Transactional End

INSTRUCTION SET REFERENCE, W-Z

##### ELSE

EIP := fallbackEIP FI; END Flags Affected None Intel C/C++ Compiler Intrinsic Equivalent XEND: void _xend( void ); SIMD Floating-Point Exceptions None Other Exceptions #UD CPUID.(EAX=7, ECX=0):EBX.RTM[bit 11] = 0. If LOCK prefix is used. #GP(0) If RTM_ACTIVE = 0.

XEND—Transactional End

Vol. 2D 6-31

INSTRUCTION SET REFERENCE, W-Z

## XGETBV—Get Value of Extended Control Register

|Opcode|Instruction|Op/<br>En|64-Bit<br>Mode|Compat/<br>Leg Mode|Description|
|---|---|---|---|---|---|
|NP 0F 01 D0|XGETBV|ZO|Valid|Valid|Reads an XCR specified by ECX into EDX:EAX.|



#### Instruction Operand Encoding

|Op/En|Operand 1|Operand 2|Operand 3|Operand 4|
|---|---|---|---|---|
|ZO|N/A|N/A|N/A|N/A|



#### Description

Reads the contents of the extended control register (XCR) specified in the ECX register into registers EDX:EAX. (On processors that support the Intel 64 architecture, the high-order 32 bits of RCX are ignored.) The EDX register is loaded with the high-order 32 bits of the XCR and the EAX register is loaded with the low-order 32 bits. (On processors that support the Intel 64 architecture, the high-order 32 bits of each of RAX and RDX are cleared.) If fewer than 64 bits are implemented in the XCR being read, the values returned to EDX:EAX in unimplemented bit locations are undefined.

XCR0 is supported on any processor that supports the XGETBV instruction. If CPUID.(EAX=0DH,ECX=1):EAX.XG1[bit 2] = 1, executing XGETBV with ECX = 1 returns in EDX:EAX the logicalAND of XCR0 and the current value of the XINUSE state-component bitmap. This allows software to discover the state of the init optimization used by XSAVEOPT and XSAVES. See Chapter 13, “Managing State Using the XSAVE Feature Set‚” in _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ .

Use of any other value for ECX results in a general-protection (#GP) exception.

#### Operation

EDX:EAX := XCR[ECX];

#### Flags Affected

None.

#### Intel C/C++ Compiler Intrinsic Equivalent

XGETBV: unsigned __int64 _xgetbv( unsigned int);

#### Protected Mode Exceptions

#GP(0) If an invalid XCR is specified in ECX (includes ECX = 1 if CPUID.(EAX=0DH,ECX=1):EAX.XG1[bit 2] = 0). #UD If CPUID.01H:ECX.XSAVE[bit 26] = 0. If CR4.OSXSAVE[bit 18] = 0. If the LOCK prefix is used.

#### Real-Address Mode Exceptions

#GP(0) If an invalid XCR is specified in ECX (includes ECX = 1 if CPUID.(EAX=0DH,ECX=1):EAX.XG1[bit 2] = 0). #UD If CPUID.01H:ECX.XSAVE[bit 26] = 0. If CR4.OSXSAVE[bit 18] = 0. If the LOCK prefix is used.

#### Virtual-8086 Mode Exceptions

Same exceptions as in protected mode.

XGETBV—Get Value of Extended Control Register

6-32 Vol. 2D

INSTRUCTION SET REFERENCE, W-Z

Compatibility Mode Exceptions

Same exceptions as in protected mode.

64-Bit Mode Exceptions

Same exceptions as in protected mode.

XGETBV—Get Value of Extended Control Register

Vol. 2D 6-33

INSTRUCTION SET REFERENCE, W-Z

## XLAT/XLATB—Table Look-up Translation

|Opcode|Instruction|Op/<br>En|64-Bit<br>Mode|Compat/<br>Leg Mode|Description|
|---|---|---|---|---|---|
|D7|XLAT m8|ZO|Valid|Valid|Set AL to memory byte DS:[(E)BX + unsigned<br>AL].|
|D7|XLATB|ZO|Valid|Valid|Set AL to memory byte DS:[(E)BX + unsigned<br>AL].|
|REX.W + D7|XLATB|ZO|Valid|N.E.|Set AL to memory byte [RBX + unsigned AL].|



#### Instruction Operand Encoding

|Op/En|Operand 1|Operand 2|Operand 3|Operand 4|
|---|---|---|---|---|
|ZO|N/A|N/A|N/A|N/A|



#### Description

Locates a byte entry in a table in memory, using the contents of the AL register as a table index, then copies the contents of the table entry back into the AL register. The index in the AL register is treated as an unsigned integer. The XLAT and XLATB instructions get the base address of the table in memory from either the DS:EBX or the DS:BX registers (depending on the address-size attribute of the instruction, 32 or 16, respectively). (The DS segment may be overridden with a segment override prefix.)

At the assembly-code level, two forms of this instruction are allowed: the “explicit-operand” form and the “nooperand” form. The explicit-operand form (specified with the XLAT mnemonic) allows the base address of the table to be specified explicitly with a symbol. This explicit-operands form is provided to allow documentation; however, note that the documentation provided by this form can be misleading. That is, the symbol does not have to specify the correct base address. The base address is always specified by the DS:(E)BX registers, which must be loaded correctly before the XLAT instruction is executed.

The no-operands form (XLATB) provides a “short form” of the XLAT instructions. Here also the processor assumes that the DS:(E)BX registers contain the base address of the table.

In 64-bit mode, operation is similar to that in legacy or compatibility mode. AL is used to specify the table index (the operand size is fixed at 8 bits). RBX, however, is used to specify the table’s base address. See the summary chart at the beginning of this section for encoding data and limits.

#### Operation

IF AddressSize = 16 THEN AL := (DS:BX + ZeroExtend(AL)); ELSE IF (AddressSize = 32) AL := (DS:EBX + ZeroExtend(AL)); FI; ELSE (AddressSize = 64) AL := (RBX + ZeroExtend(AL));

FI;

#### Flags Affected

None.

#### Protected Mode Exceptions

#GP(0) If a memory operand effective address is outside the CS, DS, ES, FS, or GS segment limit. If the DS, ES, FS, or GS register contains a NULL segment selector.

#SS(0) If a memory operand effective address is outside the SS segment limit. #PF(fault-code) If a page fault occurs.

XLAT/XLATB—Table Look-up Translation

6-34 Vol. 2D

INSTRUCTION SET REFERENCE, W-Z

#UD If the LOCK prefix is used.

#### Real-Address Mode Exceptions

#GP If a memory operand effective address is outside the CS, DS, ES, FS, or GS segment limit. #SS If a memory operand effective address is outside the SS segment limit. #UD If the LOCK prefix is used.

#### Virtual-8086 Mode Exceptions

#GP(0) If a memory operand effective address is outside the CS, DS, ES, FS, or GS segment limit. #SS(0) If a memory operand effective address is outside the SS segment limit. #PF(fault-code) If a page fault occurs. #UD If the LOCK prefix is used.

#### Compatibility Mode Exceptions

Same exceptions as in protected mode.

#### 64-Bit Mode Exceptions

#SS(0) If a memory address referencing the SS segment is in a non-canonical form. #GP(0) If the memory address is in a non-canonical form. #PF(fault-code) If a page fault occurs. #UD If the LOCK prefix is used.

XLAT/XLATB—Table Look-up Translation

Vol. 2D 6-35

INSTRUCTION SET REFERENCE, W-Z

## XOR—Logical Exclusive OR

|Opcode|Instruction|Op/<br>En|64-Bit<br>Mode|Compat/<br>Leg Mode|Description|
|---|---|---|---|---|---|
|34 ib|XOR AL, imm8|I|Valid|Valid|AL XOR imm8.|
|35 iw|XOR AX, imm16|I|Valid|Valid|AX XOR imm16.|
|35 id|XOR EAX, imm32|I|Valid|Valid|EAX XOR imm32.|
|REX.W + 35 id|XOR RAX, imm32|I|Valid|N.E.|RAX XOR imm32 (sign-extended).|
|80 /6 ib|XOR r/m8, imm8|MI|Valid|Valid|r/m8 XOR imm8.|
|REX + 80 /6 ib|XOR r/m8*, imm8|MI|Valid|N.E.|r/m8 XOR imm8.|
|81 /6 iw|XOR r/m16, imm16|MI|Valid|Valid|r/m16 XOR imm16.|
|81 /6 id|XOR r/m32, imm32|MI|Valid|Valid|r/m32 XOR imm32.|
|REX.W + 81 /6 id|XOR r/m64, imm32|MI|Valid|N.E.|r/m64 XOR imm32 (sign-extended).|
|83 /6 ib|XOR r/m16, imm8|MI|Valid|Valid|r/m16 XOR imm8 (sign-extended).|
|83 /6 ib|XOR r/m32, imm8|MI|Valid|Valid|r/m32 XOR imm8 (sign-extended).|
|REX.W + 83 /6 ib|XOR r/m64, imm8|MI|Valid|N.E.|r/m64 XOR imm8 (sign-extended).|
|30 /r|XOR r/m8, r8|MR|Valid|Valid|r/m8 XOR r8.|
|REX + 30 /r|XOR r/m8*, r8*|MR|Valid|N.E.|r/m8 XOR r8.|
|31 /r|XOR r/m16, r16|MR|Valid|Valid|r/m16 XOR r16.|
|31 /r|XOR r/m32, r32|MR|Valid|Valid|r/m32 XOR r32.|
|REX.W + 31 /r|XOR r/m64, r64|MR|Valid|N.E.|r/m64 XOR r64.|
|32 /r|XOR r8, r/m8|RM|Valid|Valid|r8 XOR r/m8.|
|REX + 32 /r|XOR r8*, r/m8*|RM|Valid|N.E.|r8 XOR r/m8.|
|33 /r|XOR r16, r/m16|RM|Valid|Valid|r16 XOR r/m16.|
|33 /r|XOR r32, r/m32|RM|Valid|Valid|r32 XOR r/m32.|
|REX.W + 33 /r|XOR r64, r/m64|RM|Valid|N.E.|r64 XOR r/m64.|



NOTES:

* In 64-bit mode, r/m8 can not be encoded to access the following byte registers if a REX prefix is used: AH, BH, CH, DH.

#### Instruction Operand Encoding

|Op/En|Operand 1|Operand 2|Operand 3|Operand 4|
|---|---|---|---|---|
|I|AL/AX/EAX/RAX|imm8/16/32|N/A|N/A|
|MI|ModRM:r/m (r, w)|imm8/16/32|N/A|N/A|
|MR|ModRM:r/m (r, w)|ModRM:reg (r)|N/A|N/A|
|RM|ModRM:reg (r, w)|ModRM:r/m (r)|N/A|N/A|



#### Description

Performs a bitwise exclusive OR (XOR) operation on the destination (first) and source (second) operands and stores the result in the destination operand location. The source operand can be an immediate, a register, or a memory location; the destination operand can be a register or a memory location. (However, two memory operands cannot be used in one instruction.) Each bit of the result is 1 if the corresponding bits of the operands are different; each bit is 0 if the corresponding bits are the same.

This instruction can be used with a LOCK prefix to allow the instruction to be executed atomically.

XOR—Logical Exclusive OR

6-36 Vol. 2D

INSTRUCTION SET REFERENCE, W-Z

In 64-bit mode, using a REX prefix in the form of REX.R permits access to additional registers (R8-R15). Using a REX prefix in the form of REX.W promotes operation to 64 bits. See the summary chart at the beginning of this section for encoding data and limits.

#### Operation

DEST := DEST XOR SRC;

#### Flags Affected

The OF and CF flags are cleared; the SF, ZF, and PF flags are set according to the result. The state of the AF flag is undefined.

#### Protected Mode Exceptions

#GP(0) If the destination operand points to a non-writable segment. If a memory operand effective address is outside the CS, DS, ES, FS, or GS segment limit. If the DS, ES, FS, or GS register contains a NULL segment selector. #SS(0) If a memory operand effective address is outside the SS segment limit. #PF(fault-code) If a page fault occurs. #AC(0) If alignment checking is enabled and an unaligned memory reference is made while the current privilege level is 3.

#UD If the LOCK prefix is used but the destination is not a memory operand.

#### Real-Address Mode Exceptions

#GP If a memory operand effective address is outside the CS, DS, ES, FS, or GS segment limit. #SS If a memory operand effective address is outside the SS segment limit. #UD If the LOCK prefix is used but the destination is not a memory operand.

#### Virtual-8086 Mode Exceptions

#GP(0) If a memory operand effective address is outside the CS, DS, ES, FS, or GS segment limit. #SS(0) If a memory operand effective address is outside the SS segment limit. #PF(fault-code) If a page fault occurs. #AC(0) If alignment checking is enabled and an unaligned memory reference is made. #UD If the LOCK prefix is used but the destination is not a memory operand.

#### Compatibility Mode Exceptions

Same exceptions as in protected mode.

#### 64-Bit Mode Exceptions

#SS(0) If a memory address referencing the SS segment is in a non-canonical form. #GP(0) If the memory address is in a non-canonical form. #PF(fault-code) If a page fault occurs. #AC(0) If alignment checking is enabled and an unaligned memory reference is made while the current privilege level is 3.

#UD If the LOCK prefix is used but the destination is not a memory operand.

XOR—Logical Exclusive OR

Vol. 2D 6-37

INSTRUCTION SET REFERENCE, W-Z

XORPD—Bitwise Logical XOR of Packed Double Precision Floating-Point Values

|Opcode/<br>Instruction|Op /<br>En|64/32<br>bit Mode<br>Support|CPUID<br>Feature<br>Flag|Description|
|---|---|---|---|---|
|66 0F 57/r<br>XORPD xmm1, xmm2/m128|A|V/V|SSE2|Return the bitwise logical XOR of packed double<br>precision floating-point values in xmm1 and xmm2/mem.|
|VEX.128.66.0F.WIG 57 /r<br>VXORPD xmm1,xmm2,<br>xmm3/m128|B|V/V|AVX|Return the bitwise logical XOR of packed double<br>precision floating-point values in xmm2 and xmm3/mem.|
|VEX.256.66.0F.WIG 57 /r<br>VXORPD ymm1, ymm2,<br>ymm3/m256|B|V/V|AVX|Return the bitwise logical XOR of packed double<br>precision floating-point values in ymm2 and ymm3/mem.|
|EVEX.128.66.0F.W1 57 /r<br>VXORPD xmm1 {k1}{z}, xmm2,<br>xmm3/m128/m64bcst|C|V/V|AVX512VL<br>AVX512DQ|Return the bitwise logical XOR of packed double<br>precision floating-point values in xmm2 and<br>xmm3/m128/m64bcst subject to writemask k1.|
|EVEX.256.66.0F.W1 57 /r<br>VXORPD ymm1 {k1}{z}, ymm2,<br>ymm3/m256/m64bcst|C|V/V|AVX512VL<br>AVX512DQ|Return the bitwise logical XOR of packed double<br>precision floating-point values in ymm2 and<br>ymm3/m256/m64bcst subject to writemask k1.|
|EVEX.512.66.0F.W1 57 /r<br>VXORPD zmm1 {k1}{z}, zmm2,<br>zmm3/m512/m64bcst|C|V/V|AVX512DQ|Return the bitwise logical XOR of packed double<br>precision floating-point values in zmm2 and<br>zmm3/m512/m64bcst subject to writemask k1.|



#### Instruction Operand Encoding

|Op/En|Tuple Type|Operand 1|Operand 2|Operand 3|Operand 4|
|---|---|---|---|---|---|
|A|N/A|ModRM:reg (r, w)|ModRM:r/m (r)|N/A|N/A|
|B|N/A|ModRM:reg (w)|VEX.vvvv (r)|ModRM:r/m (r)|N/A|
|C|Full|ModRM:reg (w)|EVEX.vvvv (r)|ModRM:r/m (r)|N/A|



##### Description

Performs a bitwise logical XOR of the two, four or eight packed double precision floating-point values from the first source operand and the second source operand, and stores the result in the destination operand.

EVEX.512 encoded version: The first source operand is a ZMM register. The second source operand can be a ZMM register or a vector memory location. The destination operand is a ZMM register conditionally updated with writemask k1.

VEX.256 and EVEX.256 encoded versions: The first source operand is a YMM register. The second source operand is a YMM register or a 256-bit memory location. The destination operand is a YMM register (conditionally updated with writemask k1 in case of EVEX). The upper bits (MAXVL-1:256) of the corresponding ZMM register destination are zeroed.

VEX.128 and EVEX.128 encoded versions: The first source operand is an XMM register. The second source operand is an XMM register or 128-bit memory location. The destination operand is an XMM register (conditionally updated with writemask k1 in case of EVEX). The upper bits (MAXVL-1:128) of the corresponding ZMM register destination are zeroed.

128-bit Legacy SSE version: The second source can be an XMM register or an 128-bit memory location. The destination is not distinct from the first source XMM register and the upper bits (MAXVL-1:128) of the corresponding register destination are unmodified.

XORPD—Bitwise Logical XOR of Packed Double Precision Floating-Point Values

6-38 Vol. 2D

INSTRUCTION SET REFERENCE, W-Z

##### Operation

VXORPD (EVEX encoded versions) (KL, VL) = (2, 128), (4, 256), (8, 512) FOR j := 0 TO KL-1 i := j * 64 IF k1[j] OR *no writemask* THEN IF (EVEX.b == 1) AND (SRC2 *is memory*) THEN DEST[i+63:i] := SRC1[i+63:i] BITWISE XOR SRC2[63:0]; ELSE DEST[i+63:i] := SRC1[i+63:i] BITWISE XOR SRC2[i+63:i]; FI; ELSE IF *merging-masking* ; merging-masking THEN *DEST[i+63:i] remains unchanged* ELSE *zeroing-masking* ; zeroing-masking DEST[i+63:i] = 0 FI

FI; ENDFOR DEST[MAXVL-1:VL] := 0

VXORPD (VEX.256 encoded version) DEST[63:0] := SRC1[63:0] BITWISE XOR SRC2[63:0] DEST[127:64] := SRC1[127:64] BITWISE XOR SRC2[127:64] DEST[191:128] := SRC1[191:128] BITWISE XOR SRC2[191:128] DEST[255:192] := SRC1[255:192] BITWISE XOR SRC2[255:192] DEST[MAXVL-1:256] := 0

VXORPD (VEX.128 encoded version) DEST[63:0] := SRC1[63:0] BITWISE XOR SRC2[63:0] DEST[127:64] := SRC1[127:64] BITWISE XOR SRC2[127:64] DEST[MAXVL-1:128] := 0

XORPD (128-bit Legacy SSE version) DEST[63:0] := DEST[63:0] BITWISE XOR SRC[63:0] DEST[127:64] := DEST[127:64] BITWISE XOR SRC[127:64] DEST[MAXVL-1:128] (Unmodified)

Intel C/C++ Compiler Intrinsic Equivalent

VXORPD __m512d _mm512_xor_pd (__m512d a, __m512d b); VXORPD __m512d _mm512_mask_xor_pd (__m512d a, __mmask8 m, __m512d b); VXORPD __m512d _mm512_maskz_xor_pd (__mmask8 m, __m512d a); VXORPD __m256d _mm256_xor_pd (__m256d a, __m256d b); VXORPD __m256d _mm256_mask_xor_pd (__m256d a, __mmask8 m, __m256d b); VXORPD __m256d _mm256_maskz_xor_pd (__mmask8 m, __m256d a); XORPD __m128d _mm_xor_pd (__m128d a, __m128d b); VXORPD __m128d _mm_mask_xor_pd (__m128d a, __mmask8 m, __m128d b); VXORPD __m128d _mm_maskz_xor_pd (__mmask8 m, __m128d a);

SIMD Floating-Point Exceptions None

XORPD—Bitwise Logical XOR of Packed Double Precision Floating-Point Values

Vol. 2D 6-39

INSTRUCTION SET REFERENCE, W-Z

##### Other Exceptions

Non-EVEX-encoded instructions, see Table 2-21, “Type 4 Class Exception Conditions”. EVEX-encoded instructions, see Table 2-49, “Type E4 Class Exception Conditions”.

XORPD—Bitwise Logical XOR of Packed Double Precision Floating-Point Values

6-40 Vol. 2D

INSTRUCTION SET REFERENCE, W-Z

XORPS—Bitwise Logical XOR of Packed Single Precision Floating-Point Values

|Opcode/<br>Instruction|Op /<br>En|64/32<br>bit Mode<br>Support|CPUID<br>Feature<br>Flag|Description|
|---|---|---|---|---|
|NP 0F 57 /r<br>XORPS xmm1, xmm2/m128|A|V/V|SSE|Return the bitwise logical XOR of packed single-<br>precision floating-point values in xmm1 and<br>xmm2/mem.|
|VEX.128.0F.WIG 57 /r<br>VXORPS xmm1,xmm2, xmm3/m128|B|V/V|AVX|Return the bitwise logical XOR of packed single-<br>precision floating-point values in xmm2 and<br>xmm3/mem.|
|VEX.256.0F.WIG 57 /r<br>VXORPS ymm1, ymm2, ymm3/m256|B|V/V|AVX|Return the bitwise logical XOR of packed single-<br>precision floating-point values in ymm2 and<br>ymm3/mem.|
|EVEX.128.0F.W0 57 /r<br>VXORPS xmm1 {k1}{z}, xmm2,<br>xmm3/m128/m32bcst|C|V/V|AVX512VL<br>AVX512DQ|Return the bitwise logical XOR of packed single-<br>precision floating-point values in xmm2 and<br>xmm3/m128/m32bcst subject to writemask k1.|
|EVEX.256.0F.W0 57 /r<br>VXORPS ymm1 {k1}{z}, ymm2,<br>ymm3/m256/m32bcst|C|V/V|AVX512VL<br>AVX512DQ|Return the bitwise logical XOR of packed single-<br>precision floating-point values in ymm2 and<br>ymm3/m256/m32bcst subject to writemask k1.|
|EVEX.512.0F.W0 57 /r<br>VXORPS zmm1 {k1}{z}, zmm2,<br>zmm3/m512/m32bcst|C|V/V|AVX512DQ|Return the bitwise logical XOR of packed single-<br>precision floating-point values in zmm2 and<br>zmm3/m512/m32bcst subject to writemask k1.|



#### Instruction Operand Encoding

|Op/En|Tuple Type|Operand 1|Operand 2|Operand 3|Operand 4|
|---|---|---|---|---|---|
|A|N/A|ModRM:reg (r, w)|ModRM:r/m (r)|N/A|N/A|
|B|N/A|ModRM:reg (w)|VEX.vvvv (r)|ModRM:r/m (r)|N/A|
|C|Full|ModRM:reg (w)|EVEX.vvvv (r)|ModRM:r/m (r)|N/A|



##### Description

Performs a bitwise logical XOR of the four, eight or sixteen packed single-precision floating-point values from the first source operand and the second source operand, and stores the result in the destination operand EVEX.512 encoded version: The first source operand is a ZMM register. The second source operand can be a ZMM register or a vector memory location. The destination operand is a ZMM register conditionally updated with writemask k1.

VEX.256 and EVEX.256 encoded versions: The first source operand is a YMM register. The second source operand is a YMM register or a 256-bit memory location. The destination operand is a YMM register (conditionally updated with writemask k1 in case of EVEX). The upper bits (MAXVL-1:256) of the corresponding ZMM register destination are zeroed.

VEX.128 and EVEX.128 encoded versions: The first source operand is an XMM register. The second source operand is an XMM register or 128-bit memory location. The destination operand is an XMM register (conditionally updated with writemask k1 in case of EVEX). The upper bits (MAXVL-1:128) of the corresponding ZMM register destination are zeroed.

128-bit Legacy SSE version: The second source can be an XMM register or an 128-bit memory location. The destination is not distinct from the first source XMM register and the upper bits (MAXVL-1:128) of the corresponding register destination are unmodified.

XORPS—Bitwise Logical XOR of Packed Single Precision Floating-Point Values

Vol. 2D 6-41

INSTRUCTION SET REFERENCE, W-Z

##### Operation

VXORPS (EVEX encoded versions) (KL, VL) = (4, 128), (8, 256), (16, 512) FOR j := 0 TO KL-1

i := j * 32 IF k1[j] OR *no writemask* THEN IF (EVEX.b == 1) AND (SRC2 *is memory*) THEN DEST[i+31:i] := SRC1[i+31:i] BITWISE XOR SRC2[31:0]; ELSE DEST[i+31:i] := SRC1[i+31:i] BITWISE XOR SRC2[i+31:i]; FI; ELSE

IF *merging-masking* ; merging-masking THEN *DEST[i+31:i] remains unchanged* ELSE *zeroing-masking* ; zeroing-masking DEST[i+31:i] = 0 FI

FI; ENDFOR DEST[MAXVL-1:VL] := 0

VXORPS (VEX.256 encoded version)

DEST[31:0] := SRC1[31:0] BITWISE XOR SRC2[31:0] DEST[63:32] := SRC1[63:32] BITWISE XOR SRC2[63:32] DEST[95:64] := SRC1[95:64] BITWISE XOR SRC2[95:64] DEST[127:96] := SRC1[127:96] BITWISE XOR SRC2[127:96] DEST[159:128] := SRC1[159:128] BITWISE XOR SRC2[159:128] DEST[191:160] := SRC1[191:160] BITWISE XOR SRC2[191:160] DEST[223:192] := SRC1[223:192] BITWISE XOR SRC2[223:192] DEST[255:224] := SRC1[255:224] BITWISE XOR SRC2[255:224]. DEST[MAXVL-1:256] := 0

##### VXORPS (VEX.128 encoded version)

DEST[31:0] := SRC1[31:0] BITWISE XOR SRC2[31:0] DEST[63:32] := SRC1[63:32] BITWISE XOR SRC2[63:32] DEST[95:64] := SRC1[95:64] BITWISE XOR SRC2[95:64] DEST[127:96] := SRC1[127:96] BITWISE XOR SRC2[127:96] DEST[MAXVL-1:128] := 0

XORPS (128-bit Legacy SSE version) DEST[31:0] := SRC1[31:0] BITWISE XOR SRC2[31:0] DEST[63:32] := SRC1[63:32] BITWISE XOR SRC2[63:32] DEST[95:64] := SRC1[95:64] BITWISE XOR SRC2[95:64] DEST[127:96] := SRC1[127:96] BITWISE XOR SRC2[127:96] DEST[MAXVL-1:128] (Unmodified)

Intel C/C++ Compiler Intrinsic Equivalent

VXORPS __m512 _mm512_xor_ps (__m512 a, __m512 b); VXORPS __m512 _mm512_mask_xor_ps (__m512 a, __mmask16 m, __m512 b); VXORPS __m512 _mm512_maskz_xor_ps (__mmask16 m, __m512 a); VXORPS __m256 _mm256_xor_ps (__m256 a, __m256 b); VXORPS __m256 _mm256_mask_xor_ps (__m256 a, __mmask8 m, __m256 b); VXORPS __m256 _mm256_maskz_xor_ps (__mmask8 m, __m256 a); XORPS __m128 _mm_xor_ps (__m128 a, __m128 b); VXORPS __m128 _mm_mask_xor_ps (__m128 a, __mmask8 m, __m128 b);

XORPS—Bitwise Logical XOR of Packed Single Precision Floating-Point Values

6-42 Vol. 2D

INSTRUCTION SET REFERENCE, W-Z

VXORPS __m128 _mm_maskz_xor_ps (__mmask8 m, __m128 a);

SIMD Floating-Point Exceptions None

##### Other Exceptions

Non-EVEX-encoded instructions, see Table 2-21, “Type 4 Class Exception Conditions”. EVEX-encoded instructions, see Table 2-49, “Type E4 Class Exception Conditions”.

XORPS—Bitwise Logical XOR of Packed Single Precision Floating-Point Values

Vol. 2D 6-43

INSTRUCTION SET REFERENCE, W-Z

XRESLDTRK—Resume Tracking Load Addresses

|Opcode/<br>Instruction|Op/<br>En|64/32<br>bit Mode<br>Support|CPUID Feature<br>Flag|Description|
|---|---|---|---|---|
|F2 0F 01 E9|ZO|V/V|TSXLDTRK|Specifies the end of an Intel TSX suspend read|
|XRESLDTRK||||address tracking region.|



Instruction Operand Encoding

|Op/En|Tuple|Operand 1|Operand 2|Operand 3|Operand 4|
|---|---|---|---|---|---|
|ZO|N/A|N/A|N/A|N/A|N/A|



##### Description

The instruction marks the end of an Intel TSX (RTM) suspend load address tracking region. If the instruction is used inside a suspend load address tracking region it will end the suspend region and all following load addresses will be added to the transaction read set. If this instruction is used inside an active transaction but not in a suspend region it will cause transaction abort.

If the instruction is used outside of a transactional region it behaves like a NOP.

Chapter 16, “Programming with Intel® Transactional Synchronization Extensions” in the _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ provides additional information on Intel<sup>®</sup> TSX Suspend Load Address Tracking.

##### Operation

##### XRESLDTRK

IF RTM_ACTIVE = 1: IF SUSLDTRK_ACTIVE = 1: SUSLDTRK_ACTIVE := 0 ELSE: RTM_ABORT ELSE: NOP

Flags Affected

None.

Intel C/C++ Compiler Intrinsic Equivalent

XRESLDTRK void _xresldtrk(void);

SIMD Floating-Point Exceptions

None.

Other Exceptions #UD If CPUID.(EAX=7, ECX=0):EDX.TSXLDTRK[bit 16] = 0. If the LOCK prefix is used.

XRESLDTRK—Resume Tracking Load Addresses

6-44 Vol. 2D

INSTRUCTION SET REFERENCE, W-Z

## XRSTOR—Restore Processor Extended States

|Opcode /<br>Instruction|Op/<br>En|64/32 bit<br>Mode<br>Support|CPUID<br>Feature<br>Flag|Description|
|---|---|---|---|---|
|NP 0F AE /5|M|V/V|XSAVE|Restore state components specified by EDX:EAX from|
|XRSTOR mem||||mem.|
|NP REX.W + 0F AE /5|M|V/N.E.|XSAVE|Restore state components specified by EDX:EAX from|
|XRSTOR64 mem||||mem.|



#### Instruction Operand Encoding

|Op/En|Operand 1|Operand 2|Operand 3|Operand 4|
|---|---|---|---|---|
|M|ModRM:r/m (r)|N/A|N/A|N/A|



#### Description

Performs a full or partial restore of processor state components from the XSAVE area located at the memory address specified by the source operand. The implicit EDX:EAX register pair specifies a 64-bit instruction mask. The specific state components restored correspond to the bits set in the requested-feature bitmap (RFBM), which is the logical-AND of EDX:EAX and XCR0.

The format of the XSAVE area is detailed in Section 13.4, “XSAVE Area,” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ . Like FXRSTOR and FXSAVE, the memory format used for x87 state depends on a REX.W prefix; see Section 13.5.1, “x87 State” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ .

Section 13.8, “Operation of XRSTOR,” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ provides a detailed description of the operation of the XRSTOR instruction. The following items provide a highlevel outline:

- Execution of XRSTOR may take one of two forms: standard and compacted. Bit 63 of the XCOMP_BV field in the XSAVE header determines which form is used: value 0 specifies the standard form, while value 1 specifies the compacted form.

- If RFBM[ _i_ ] = 0, XRSTOR does not update state component _i_ .<sup>1</sup>

- If RFBM[ _i_ ] = 1 and bit _i_ is clear in the XSTATE_BV field in the XSAVE header, XRSTOR initializes state component _i_ .

- If RFBM[ _i_ ] = 1 and XSTATE_BV[ _i_ ] = 1, XRSTOR loads state component _i_ from the XSAVE area.

- The standard form of XRSTOR treats MXCSR (which is part of state component 1 — SSE) differently from the XMM registers. If either form attempts to load MXCSR with an illegal value, a general-protection exception (#GP) occurs.

- XRSTOR loads the internal value XRSTOR_INFO, which may be used to optimize a subsequent execution of XSAVEOPT or XSAVES.

- Immediately following an execution of XRSTOR, the processor tracks as in-use (not in initial configuration) any state component _i_ for which RFBM[ _i_ ] = 1 and XSTATE_BV[ _i_ ] = 1; it tracks as modified any state component _i_ for which RFBM[ _i_ ] = 0.

Use of a source operand not aligned to 64-byte boundary (for 64-bit and 32-bit modes) results in a general-protection (#GP) exception. In 64-bit mode, the upper 32 bits of RDX and RAX are ignored.

See Section 13.6, “Processor Tracking of XSAVE-Managed State,” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ for discussion of the bitmaps XINUSE and XMODIFIED and of the quantity XRSTOR_INFO.

1. There is an exception if RFBM[1] = 0 and RFBM[2] = 1. In this case, the standard form of XRSTOR will load MXCSR from memory, even though MXCSR is part of state component 1 — SSE. The compacted form of XRSTOR does not make this exception.

XRSTOR—Restore Processor Extended States

Vol. 2D 6-45

INSTRUCTION SET REFERENCE, W-Z

#### Operation

RFBM := XCR0 AND EDX:EAX; /* bitwise logical AND */ COMPMASK := XCOMP_BV field from XSAVE header; RSTORMASK := XSTATE_BV field from XSAVE header;

IF COMPMASK[63] = 0

THEN

/* Standard form of XRSTOR */ TO_BE_RESTORED := RFBM AND RSTORMASK; TO_BE_INITIALIZED := RFBM AND NOT RSTORMASK;

IF TO_BE_RESTORED[0] = 1 THEN

XINUSE[0] := 1;

load x87 state from legacy region of XSAVE area; ELSIF TO_BE_INITIALIZED[0] = 1

##### THEN

XINUSE[0] := 0; initialize x87 state;

FI;

IF RFBM[1] = 1 OR RFBM[2] = 1

THEN load MXCSR from legacy region of XSAVE area;

FI;

IF TO_BE_RESTORED[1] = 1 THEN

XINUSE[1] := 1;

load XMM registers from legacy region of XSAVE area; // this step does not load MXCSR ELSIF TO_BE_INITIALIZED[1] = 1

THEN

XINUSE[1] := 0;

set all XMM registers to 0; // this step does not initialize MXCSR

FI;

FOR i := 2 TO 62

IF TO_BE_RESTORED[i] = 1 THEN

XINUSE[i] := 1;

load XSAVE state component i at offset n from base of XSAVE area; // n enumerated by CPUID(EAX=0DH,ECX=i):EBX) ELSIF TO_BE_INITIALIZED[i] = 1 THEN

XINUSE[i] := 0; initialize XSAVE state component i;

FI; ENDFOR;

ELSE

/* Compacted form of XRSTOR */ IF CPUID.(EAX=0DH,ECX=1):EAX.XSAVEC[bit 1] = 0 THEN /* compacted form not supported */ #GP(0);

6-46 Vol. 2D

XRSTOR—Restore Processor Extended States

INSTRUCTION SET REFERENCE, W-Z

##### FI;

FORMAT = COMPMASK AND 7FFFFFFF_FFFFFFFFH; RESTORE_FEATURES = FORMAT AND RFBM; TO_BE_RESTORED := RESTORE_FEATURES AND RSTORMASK; FORCE_INIT := RFBM AND NOT FORMAT; TO_BE_INITIALIZED = (RFBM AND NOT RSTORMASK) OR FORCE_INIT;

IF TO_BE_RESTORED[0] = 1 THEN

XINUSE[0] := 1; load x87 state from legacy region of XSAVE area; ELSIF TO_BE_INITIALIZED[0] = 1 THEN XINUSE[0] := 0; initialize x87 state;

FI;

IF TO_BE_RESTORED[1] = 1 THEN XINUSE[1] := 1; load SSE state from legacy region of XSAVE area; // this step loads the XMM registers and MXCSR ELSIF TO_BE_INITIALIZED[1] = 1 THEN set all XMM registers to 0; XINUSE[1] := 0; MXCSR := 1F80H; FI;

NEXT_FEATURE_OFFSET = 576; // Legacy area and XSAVE header consume 576 bytes FOR i := 2 TO 62 IF FORMAT[i] = 1 THEN IF TO_BE_RESTORED[i] = 1 THEN XINUSE[i] := 1; load XSAVE state component i at offset NEXT_FEATURE_OFFSET from base of XSAVE area; FI; NEXT_FEATURE_OFFSET = NEXT_FEATURE_OFFSET + n (n enumerated by CPUID(EAX=0DH,ECX=i):EAX); FI; IF TO_BE_INITIALIZED[i] = 1 THEN XINUSE[i] := 0; initialize XSAVE state component i; FI; ENDFOR;

FI;

XMODIFIED := NOT RFBM;

IF in VMX non-root operation THEN VMXNR := 1; ELSE VMXNR := 0; FI;

XRSTOR—Restore Processor Extended States

Vol. 2D 6-47

INSTRUCTION SET REFERENCE, W-Z

LAXA := linear address of XSAVE area; XRSTOR_INFO :=  CPL,VMXNR,LAXA,COMPMASK  ;

#### Flags Affected

None.

Intel C/C++ Compiler Intrinsic Equivalent

XRSTOR: void _xrstor( void * , unsigned __int64); XRSTOR: void _xrstor64( void * , unsigned __int64);

#### Protected Mode Exceptions

#GP(0) If a memory operand effective address is outside the CS, DS, ES, FS, or GS segment limit. If a memory operand is not aligned on a 64-byte boundary, regardless of segment. If bit 63 of the XCOMP_BV field of the XSAVE header is 1 and CPUID.(EAX=0DH,ECX=1):EAX.XSAVEC[bit 1] = 0.

If the standard form is executed and a bit in XCR0 is 0 and the corresponding bit in the XSTATE_BV field of the XSAVE header is 1.

If the standard form is executed and bytes 23:8 of the XSAVE header are not all zero. If the compacted form is executed and a bit in XCR0 is 0 and the corresponding bit in the XCOMP_BV field of the XSAVE header is 1.

If the compacted form is executed and a bit in the XCOMP_BV field in the XSAVE header is 0 and the corresponding bit in the XSTATE_BV field is 1.

If the compacted form is executed and bytes 63:16 of the XSAVE header are not all zero. If attempting to write any reserved bits of the MXCSR register with 1. #SS(0) If a memory operand effective address is outside the SS segment limit. #PF(fault-code) If a page fault occurs. #NM If CR0.TS[bit 3] = 1. #UD If CPUID.01H:ECX.XSAVE[bit 26] = 0. If CR4.OSXSAVE[bit 18] = 0. If the LOCK prefix is used.

#AC If this exception is disabled a general protection exception (#GP) is signaled if the memory operand is not aligned on a 64-byte boundary, as described above. If the alignment check exception (#AC) is enabled (and the CPL is 3), signaling of #AC is not guaranteed and may vary with implementation, as follows. In all implementations where #AC is not signaled, a general protection exception is signaled in its place. In addition, the width of the alignment check may also vary with implementation. For instance, for a given implementation, an alignment check exception might be signaled for a 2-byte misalignment, whereas a general protection exception might be signaled for all other misalignments (4-, 8-, or 16-byte misalignments).

#### Real-Address Mode Exceptions

#GP If a memory operand is not aligned on a 64-byte boundary, regardless of segment. If any part of the operand lies outside the effective address space from 0 to FFFFH. If bit 63 of the XCOMP_BV field of the XSAVE header is 1 and CPUID.(EAX=0DH,ECX=1):EAX.XSAVEC[bit 1] = 0.

If the standard form is executed and a bit in XCR0 is 0 and the corresponding bit in the XSTATE_BV field of the XSAVE header is 1. If the standard form is executed and bytes 23:8 of the XSAVE header are not all zero. If the compacted form is executed and a bit in XCR0 is 0 and the corresponding bit in the XCOMP_BV field of the XSAVE header is 1.

6-48 Vol. 2D

XRSTOR—Restore Processor Extended States

INSTRUCTION SET REFERENCE, W-Z

If the compacted form is executed and a bit in the XCOMP_BV field in the XSAVE header is 0 and the corresponding bit in the XSTATE_BV field is 1.

If the compacted form is executed and bytes 63:16 of the XSAVE header are not all zero.

If attempting to write any reserved bits of the MXCSR register with 1.

#NM

#UD

If CR0.TS[bit 3] = 1. If CPUID.01H:ECX.XSAVE[bit 26] = 0. If CR4.OSXSAVE[bit 18] = 0. If the LOCK prefix is used.

Virtual-8086 Mode Exceptions

Same exceptions as in protected mode

#### Compatibility Mode Exceptions

Same exceptions as in protected mode.

64-Bit Mode Exceptions

#GP(0)

If a memory address is in a non-canonical form.

If a memory operand is not aligned on a 64-byte boundary, regardless of segment. If bit 63 of the XCOMP_BV field of the XSAVE header is 1 and

CPUID.(EAX=0DH,ECX=1):EAX.XSAVEC[bit 1] = 0.

If the standard form is executed and a bit in XCR0 is 0 and the corresponding bit in the XSTATE_BV field of the XSAVE header is 1.

If the standard form is executed and bytes 23:8 of the XSAVE header are not all zero. If the compacted form is executed and a bit in XCR0 is 0 and the corresponding bit in the XCOMP_BV field of the XSAVE header is 1.

If the compacted form is executed and a bit in the XCOMP_BV field in the XSAVE header is 0 and the corresponding bit in the XSTATE_BV field is 1.

If the compacted form is executed and bytes 63:16 of the XSAVE header are not all zero. If attempting to write any reserved bits of the MXCSR register with 1.

#SS(0) If a memory address referencing the SS segment is in a non-canonical form.

#PF(fault-code) If a page fault occurs. #NM If CR0.TS[bit 3] = 1. #UD If CPUID.01H:ECX.XSAVE[bit 26] = 0. If CR4.OSXSAVE[bit 18] = 0. If the LOCK prefix is used.

#AC

If this exception is disabled a general protection exception (#GP) is signaled if the memory operand is not aligned on a 64-byte boundary, as described above. If the alignment check exception (#AC) is enabled (and the CPL is 3), signaling of #AC is not guaranteed and may vary with implementation, as follows. In all implementations where #AC is not signaled, a general protection exception is signaled in its place. In addition, the width of the alignment check may also vary with implementation. For instance, for a given implementation, an alignment check exception might be signaled for a 2-byte misalignment, whereas a general protection exception might be signaled for all other misalignments (4-, 8-, or 16-byte misalignments).

XRSTOR—Restore Processor Extended States

Vol. 2D 6-49

INSTRUCTION SET REFERENCE, W-Z

## XRSTORS—Restore Processor Extended States Supervisor

|Opcode /<br>Instruction|Op/<br>En|64/32 bit<br>Mode<br>Support|CPUID<br>Feature<br>Flag|Description|
|---|---|---|---|---|
|NP 0F C7 /3|M|V/V|XSS|Restore state components specified by EDX:EAX from|
|XRSTORS mem||||mem.|
|NP REX.W + 0F C7 /3|M|V/N.E.|XSS|Restore state components specified by EDX:EAX from|
|XRSTORS64 mem||||mem.|



#### Instruction Operand Encoding

|Op/En|Operand 1|Operand 2|Operand 3|Operand 4|
|---|---|---|---|---|
|M|ModRM:r/m (r)|N/A|N/A|N/A|



#### Description

Performs a full or partial restore of processor state components from the XSAVE area located at the memory address specified by the source operand. The implicit EDX:EAX register pair specifies a 64-bit instruction mask. The specific state components restored correspond to the bits set in the requested-feature bitmap (RFBM), which is the logical-AND of EDX:EAX and the logical-OR of XCR0 with the IA32_XSS MSR. XRSTORS may be executed only if CPL = 0.

The format of the XSAVE area is detailed in Section 13.4, “XSAVE Area,” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ . Like FXRSTOR and FXSAVE, the memory format used for x87 state depends on a REX.W prefix; see Section 13.5.1, “x87 State” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ .

Section 13.12, “Operation of XRSTORS,” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ provides a detailed description of the operation of the XRSTOR instruction. The following items provide a high-level outline:

- Execution of XRSTORS is similar to that of the compacted form of XRSTOR; XRSTORS cannot restore from an XSAVE area in which the extended region is in the standard format (see Section 13.4.3, “Extended Region of an XSAVE Area” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ ).

- XRSTORS differs from XRSTOR in that it can restore state components corresponding to bits set in the IA32_XSS MSR.

- If RFBM[ _i_ ] = 0, XRSTORS does not update state component _i_ .

- If RFBM[ _i_ ] = 1 and bit _i_ is clear in the XSTATE_BV field in the XSAVE header, XRSTORS initializes state component _i_ .

- If RFBM[ _i_ ] = 1 and XSTATE_BV[ _i_ ] = 1, XRSTORS loads state component _i_ from the XSAVE area.

- If XRSTORS attempts to load MXCSR with an illegal value, a general-protection exception (#GP) occurs.

- XRSTORS loads the internal value XRSTOR_INFO, which may be used to optimize a subsequent execution of XSAVEOPT or XSAVES.

- Immediately following an execution of XRSTORS, the processor tracks as in-use (not in initial configuration) any state component _i_ for which RFBM[ _i_ ] = 1 and XSTATE_BV[ _i_ ] = 1; it tracks as modified any state component _i_ for which RFBM[ _i_ ] = 0.

Use of a source operand not aligned to 64-byte boundary (for 64-bit and 32-bit modes) results in a general-protection (#GP) exception. In 64-bit mode, the upper 32 bits of RDX and RAX are ignored.

See Section 13.6, “Processor Tracking of XSAVE-Managed State,” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ for discussion of the bitmaps XINUSE and XMODIFIED and of the quantity XRSTOR_INFO.

XRSTORS—Restore Processor Extended States Supervisor

6-50 Vol. 2D

INSTRUCTION SET REFERENCE, W-Z

Operation

RFBM := (XCR0 OR IA32_XSS) AND EDX:EAX; /* bitwise logical OR and AND */ COMPMASK := XCOMP_BV field from XSAVE header; RSTORMASK := XSTATE_BV field from XSAVE header;

FORMAT = COMPMASK AND 7FFFFFFF_FFFFFFFFH; RESTORE_FEATURES = FORMAT AND RFBM; TO_BE_RESTORED := RESTORE_FEATURES AND RSTORMASK; FORCE_INIT := RFBM AND NOT FORMAT; TO_BE_INITIALIZED = (RFBM AND NOT RSTORMASK) OR FORCE_INIT;

IF TO_BE_RESTORED[0] = 1 THEN XINUSE[0] := 1; load x87 state from legacy region of XSAVE area; ELSIF TO_BE_INITIALIZED[0] = 1

##### THEN

XINUSE[0] := 0; initialize x87 state;

FI;

IF TO_BE_RESTORED[1] = 1 THEN XINUSE[1] := 1; load SSE state from legacy region of XSAVE area; // this step loads the XMM registers and MXCSR ELSIF TO_BE_INITIALIZED[1] = 1 THEN set all XMM registers to 0; XINUSE[1] := 0; MXCSR := 1F80H; FI; NEXT_FEATURE_OFFSET = 576; // Legacy area and XSAVE header consume 576 bytes FOR i := 2 TO 62 IF FORMAT[i] = 1 THEN IF TO_BE_RESTORED[i] = 1 THEN XINUSE[i] := 1; load XSAVE state component i at offset NEXT_FEATURE_OFFSET from base of XSAVE area; FI; NEXT_FEATURE_OFFSET = NEXT_FEATURE_OFFSET + n (n enumerated by CPUID(EAX=0DH,ECX=i):EAX); FI; IF TO_BE_INITIALIZED[i] = 1 THEN XINUSE[i] := 0; initialize XSAVE state component i;

FI; ENDFOR;

XMODIFIED := NOT RFBM;

IF in VMX non-root operation

XRSTORS—Restore Processor Extended States Supervisor

Vol. 2D 6-51

INSTRUCTION SET REFERENCE, W-Z

THEN VMXNR := 1; ELSE VMXNR := 0; FI; LAXA := linear address of XSAVE area; XRSTOR_INFO :=  CPL,VMXNR,LAXA,COMPMASK  ;

Flags Affected

None.

Intel C/C++ Compiler Intrinsic Equivalent XRSTORS: void _xrstors( void * , unsigned __int64); XRSTORS64: void _xrstors64( void * , unsigned __int64);

Protected Mode Exceptions

#GP(0) If CPL > 0.

If a memory operand effective address is outside the CS, DS, ES, FS, or GS segment limit. If a memory operand is not aligned on a 64-byte boundary, regardless of segment. If bit 63 of the XCOMP_BV field of the XSAVE header is 0.

If a bit in XCR0 is 0 and the corresponding bit in the XCOMP_BV field of the XSAVE header is 1. If a bit in the XCOMP_BV field in the XSAVE header is 0 and the corresponding bit in the XSTATE_BV field is 1.

If bytes 63:16 of the XSAVE header are not all zero. If attempting to write any reserved bits of the MXCSR register with 1. #SS(0) If a memory operand effective address is outside the SS segment limit. #PF(fault-code) If a page fault occurs. #NM If CR0.TS[bit 3] = 1. #UD If CPUID.01H:ECX.XSAVE[bit 26] = 0 or CPUID.(EAX=0DH,ECX=1):EAX.XSS[bit 3] = 0. If CR4.OSXSAVE[bit 18] = 0. If the LOCK prefix is used.

#### Real-Address Mode Exceptions

#GP If a memory operand is not aligned on a 64-byte boundary, regardless of segment. If any part of the operand lies outside the effective address space from 0 to FFFFH. If bit 63 of the XCOMP_BV field of the XSAVE header is 0.

If a bit in XCR0 is 0 and the corresponding bit in the XCOMP_BV field of the XSAVE header is 1. If a bit in the XCOMP_BV field in the XSAVE header is 0 and the corresponding bit in the XSTATE_BV field is 1.

If bytes 63:16 of the XSAVE header are not all zero. If attempting to write any reserved bits of the MXCSR register with 1. #NM If CR0.TS[bit 3] = 1. #UD If CPUID.01H:ECX.XSAVE[bit 26] = 0 or CPUID.(EAX=0DH,ECX=1):EAX.XSS[bit 3] = 0. If CR4.OSXSAVE[bit 18] = 0. If the LOCK prefix is used.

#### Virtual-8086 Mode Exceptions

Same exceptions as in protected mode.

XRSTORS—Restore Processor Extended States Supervisor

6-52 Vol. 2D

INSTRUCTION SET REFERENCE, W-Z

#### Compatibility Mode Exceptions

Same exceptions as in protected mode.

#### 64-Bit Mode Exceptions

#GP(0) If CPL > 0. If a memory address is in a non-canonical form. If a memory operand is not aligned on a 64-byte boundary, regardless of segment. If bit 63 of the XCOMP_BV field of the XSAVE header is 0. If a bit in XCR0 is 0 and the corresponding bit in the XCOMP_BV field of the XSAVE header is 1. If a bit in the XCOMP_BV field in the XSAVE header is 0 and the corresponding bit in the XSTATE_BV field is 1. If bytes 63:16 of the XSAVE header are not all zero. If attempting to write any reserved bits of the MXCSR register with 1. #SS(0) If a memory address referencing the SS segment is in a non-canonical form. #PF(fault-code) If a page fault occurs. #NM If CR0.TS[bit 3] = 1. #UD If CPUID.01H:ECX.XSAVE[bit 26] = 0 or CPUID.(EAX=0DH,ECX=1):EAX.XSS[bit 3] = 0. If CR4.OSXSAVE[bit 18] = 0. If the LOCK prefix is used.

XRSTORS—Restore Processor Extended States Supervisor

Vol. 2D 6-53

INSTRUCTION SET REFERENCE, W-Z

## XSAVE—Save Processor Extended States

|Opcode /<br>Instruction|Op/<br>En|64/32 bit<br>Mode<br>Support|CPUID<br>Feature<br>Flag|Description|
|---|---|---|---|---|
|NP 0F AE /4|M|V/V|XSAVE|Save state components specified by EDX:EAX to mem.|
|XSAVE mem|||||
|NP REX.W + 0F AE /4|M|V/N.E.|XSAVE|Save state components specified by EDX:EAX to mem.|
|XSAVE64 mem|||||



#### Instruction Operand Encoding

|Op/En|Operand 1|Operand 2|Operand 3|Operand 4|
|---|---|---|---|---|
|M|ModRM:r/m (r, w)|N/A|N/A|N/A|



#### Description

Performs a full or partial save of processor state components to the XSAVE area located at the memory address specified by the destination operand. The implicit EDX:EAX register pair specifies a 64-bit instruction mask. The specific state components saved correspond to the bits set in the requested-feature bitmap (RFBM), which is the logical-AND of EDX:EAX and XCR0.

The format of the XSAVE area is detailed in Section 13.4, “XSAVE Area,” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ . Like FXRSTOR and FXSAVE, the memory format used for x87 state depends on a REX.W prefix; see Section 13.5.1, “x87 State” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ .

Section 13.7, “Operation of XSAVE,” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ provides a detailed description of the operation of the XSAVE instruction. The following items provide a high-level outline:

- XSAVE saves state component _i_ if and only if RFBM[ _i_ ] = 1.<sup>1</sup>

- XSAVE does not modify bytes 511:464 of the legacy region of the XSAVE area (see Section 13.4.1, “Legacy Region of an XSAVE Area” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ ).

- XSAVE reads the XSTATE_BV field of the XSAVE header (see Section 13.4.2, “XSAVE Header” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ ) and writes a modified value back to memory as follows. If RFBM[ _i_ ] = 1, XSAVE writes XSTATE_BV[ _i_ ] with the value of XINUSE[ _i_ ]. (XINUSE is a bitmap by which the processor tracks the status of various state components. See Section 13.6, “Processor Tracking of XSAVEManaged State” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ .) If RFBM[ _i_ ] = 0, XSAVE writes XSTATE_BV[ _i_ ] with the value that it read from memory (it does not modify the bit). XSAVE does not write to any part of the XSAVE header other than the XSTATE_BV field.

- XSAVE always uses the standard format of the extended region of the XSAVE area (see Section 13.4.3, “Extended Region of an XSAVE Area” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ ).

Use of a destination operand not aligned to 64-byte boundary (in either 64-bit or 32-bit modes) results in a general-protection (#GP) exception. In 64-bit mode, the upper 32 bits of RDX and RAX are ignored.

1. An exception is made for MXCSR and MXCSR_MASK, which belong to state component 1 — SSE. XSAVE saves these values to memory if either RFBM[1] or RFBM[2] is 1.

6-54 Vol. 2D

XSAVE—Save Processor Extended States

INSTRUCTION SET REFERENCE, W-Z

#### Operation

RFBM := XCR0 AND EDX:EAX; /* bitwise logical AND */ OLD_BV := XSTATE_BV field from XSAVE header;

IF RFBM[0] = 1

THEN store x87 state into legacy region of XSAVE area;

FI;

IF RFBM[1] = 1

THEN store XMM registers into legacy region of XSAVE area; // this step does not save MXCSR or MXCSR_MASK

FI;

IF RFBM[1] = 1 OR RFBM[2] = 1

THEN store MXCSR and MXCSR_MASK into legacy region of XSAVE area;

FI;

FOR i := 2 TO 62

IF RFBM[i] = 1

THEN save XSAVE state component i at offset n from base of XSAVE area (n enumerated by CPUID(EAX=0DH,ECX=i):EBX); FI;

ENDFOR;

XSTATE_BV field in XSAVE header := (OLD_BV AND NOT RFBM) OR (XINUSE AND RFBM);

#### Flags Affected

None.

#### Intel C/C++ Compiler Intrinsic Equivalent

XSAVE: void _xsave( void * , unsigned __int64); XSAVE: void _xsave64( void * , unsigned __int64);

#### Protected Mode Exceptions

#GP(0) If a memory operand effective address is outside the CS, DS, ES, FS, or GS segment limit. If a memory operand is not aligned on a 64-byte boundary, regardless of segment. #SS(0) If a memory operand effective address is outside the SS segment limit. #PF(fault-code) If a page fault occurs. #NM If CR0.TS[bit 3] = 1. #UD If CPUID.01H:ECX.XSAVE[bit 26] = 0. If CR4.OSXSAVE[bit 18] = 0. If the LOCK prefix is used.

#AC If this exception is disabled a general protection exception (#GP) is signaled if the memory operand is not aligned on a 64-byte boundary, as described above. If the alignment check exception (#AC) is enabled (and the CPL is 3), signaling of #AC is not guaranteed and may vary with implementation, as follows. In all implementations where #AC is not signaled, a general protection exception is signaled in its place. In addition, the width of the alignment check may also vary with implementation. For instance, for a given implementation, an alignment check exception might be signaled for a 2-byte misalignment, whereas a general protection exception might be signaled for all other misalignments (4-, 8-, or 16-byte misalignments).

XSAVE—Save Processor Extended States

Vol. 2D 6-55

INSTRUCTION SET REFERENCE, W-Z

#### Real-Address Mode Exceptions

#GP If a memory operand is not aligned on a 64-byte boundary, regardless of segment. If any part of the operand lies outside the effective address space from 0 to FFFFH. #NM If CR0.TS[bit 3] = 1.

#UD If CPUID.01H:ECX.XSAVE[bit 26] = 0. If CR4.OSXSAVE[bit 18] = 0. If the LOCK prefix is used.

#### Virtual-8086 Mode Exceptions

Same exceptions as in protected mode.

#### Compatibility Mode Exceptions

Same exceptions as in protected mode.

#### 64-Bit Mode Exceptions

#GP(0) If the memory address is in a non-canonical form.

If a memory operand is not aligned on a 64-byte boundary, regardless of segment. #SS(0) If a memory address referencing the SS segment is in a non-canonical form. #PF(fault-code) If a page fault occurs. #NM If CR0.TS[bit 3] = 1. #UD If CPUID.01H:ECX.XSAVE[bit 26] = 0. If CR4.OSXSAVE[bit 18] = 0.

If the LOCK prefix is used.

#AC If this exception is disabled a general protection exception (#GP) is signaled if the memory operand is not aligned on a 64-byte boundary, as described above. If the alignment check exception (#AC) is enabled (and the CPL is 3), signaling of #AC is not guaranteed and may vary with implementation, as follows. In all implementations where #AC is not signaled, a general protection exception is signaled in its place. In addition, the width of the alignment check may also vary with implementation. For instance, for a given implementation, an alignment check exception might be signaled for a 2-byte misalignment, whereas a general protection exception might be signaled for all other misalignments (4-, 8-, or 16-byte misalignments).

6-56 Vol. 2D

XSAVE—Save Processor Extended States

INSTRUCTION SET REFERENCE, W-Z

## XSAVEC—Save Processor Extended States With Compaction

|Opcode /<br>Instruction|Op/<br>En|64/32 bit<br>Mode<br>Support|CPUID<br>Feature<br>Flag|Description|
|---|---|---|---|---|
|NP 0F C7 /4|M|V/V|XSAVEC|Save state components specified by EDX:EAX to mem with|
|XSAVEC mem||||compaction.|
|NP REX.W + 0F C7 /4|M|V/N.E.|XSAVEC|Save state components specified by EDX:EAX to mem with|
|XSAVEC64 mem||||compaction.|



#### Instruction Operand Encoding

|Op/En|Operand 1|Operand 2|Operand 3|Operand 4|
|---|---|---|---|---|
|M|ModRM:r/m (w)|N/A|N/A|N/A|



#### Description

Performs a full or partial save of processor state components to the XSAVE area located at the memory address specified by the destination operand. The implicit EDX:EAX register pair specifies a 64-bit instruction mask. The specific state components saved correspond to the bits set in the requested-feature bitmap (RFBM), which is the logical-AND of EDX:EAX and XCR0.

The format of the XSAVE area is detailed in Section 13.4, “XSAVE Area,” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ . Like FXRSTOR and FXSAVE, the memory format used for x87 state depends on a REX.W prefix; see Section 13.5.1, “x87 State” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ .

Section 13.10, “Operation of XSAVEC,” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ provides a detailed description of the operation of the XSAVEC instruction. The following items provide a highlevel outline:

- Execution of XSAVEC is similar to that of XSAVE. XSAVEC differs from XSAVE in that it uses compaction and that it may use the init optimization.

- XSAVEC saves state component _i_ if and only if RFBM[ _i_ ] = 1 and XINUSE[ _i_ ] = 1.<sup>1</sup> (XINUSE is a bitmap by which the processor tracks the status of various state components. See Section 13.6, “Processor Tracking of XSAVEManaged State” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ .)

- XSAVEC does not modify bytes 511:464 of the legacy region of the XSAVE area (see Section 13.4.1, “Legacy Region of an XSAVE Area” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ ).

- XSAVEC writes the logical AND of RFBM and XINUSE to the XSTATE_BV field of the XSAVE header.<sup>2,3</sup> (See Section 13.4.2, “XSAVE Header” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ .) XSAVEC sets bit 63 of the XCOMP_BV field and sets bits 62:0 of that field to RFBM[62:0]. XSAVEC does not write to any parts of the XSAVE header other than the XSTATE_BV and XCOMP_BV fields.

- XSAVEC always uses the compacted format of the extended region of the XSAVE area (see Section 13.4.3, “Extended Region of an XSAVE Area” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ ).

Use of a destination operand not aligned to 64-byte boundary (in either 64-bit or 32-bit modes) results in a general-protection (#GP) exception. In 64-bit mode, the upper 32 bits of RDX and RAX are ignored.

1. There is an exception for state component 1 (SSE). MXCSR is part of SSE state, but XINUSE[1] may be 0 even if MXCSR does not have its initial value of 1F80H. In this case, XSAVEC saves SSE state as long as RFBM[1] = 1.

2. Unlike XSAVE and XSAVEOPT, XSAVEC clears bits in the XSTATE_BV field that correspond to bits that are clear in RFBM.

3. There is an exception for state component 1 (SSE). MXCSR is part of SSE state, but XINUSE[1] may be 0 even if MXCSR does not have its initial value of 1F80H. In this case, XSAVEC sets XSTATE_BV[1] to 1 as long as RFBM[1] = 1.

XSAVEC—Save Processor Extended States With Compaction

Vol. 2D 6-57

INSTRUCTION SET REFERENCE, W-Z

#### Operation

RFBM := XCR0 AND EDX:EAX; /* bitwise logical AND */ TO_BE_SAVED := RFBM AND XINUSE; /* bitwise logical AND */ If MXCSR ≠ 1F80H AND RFBM[1] TO_BE_SAVED[1] = 1;

FI;

IF TO_BE_SAVED[0] = 1 THEN store x87 state into legacy region of XSAVE area;

FI;

IF TO_BE_SAVED[1] = 1

THEN store SSE state into legacy region of XSAVE area; // this step saves the XMM registers, MXCSR, and MXCSR_MASK

FI;

NEXT_FEATURE_OFFSET = 576; // Legacy area and XSAVE header consume 576 bytes FOR i := 2 TO 62

IF RFBM[i] = 1

THEN

IF TO_BE_SAVED[i]

THEN save XSAVE state component i at offset NEXT_FEATURE_OFFSET from base of XSAVE area; FI; NEXT_FEATURE_OFFSET = NEXT_FEATURE_OFFSET + n (n enumerated by CPUID(EAX=0DH,ECX=i):EAX); FI; ENDFOR;

XSTATE_BV field in XSAVE header := TO_BE_SAVED; XCOMP_BV field in XSAVE header := RFBM OR 80000000_00000000H;

Flags Affected

None.

Intel C/C++ Compiler Intrinsic Equivalent

XSAVEC: void _xsavec( void * , unsigned __int64); XSAVEC64: void _xsavec64( void * , unsigned __int64);

#### Protected Mode Exceptions

#GP(0) If a memory operand effective address is outside the CS, DS, ES, FS, or GS segment limit. If a memory operand is not aligned on a 64-byte boundary, regardless of segment. #SS(0) If a memory operand effective address is outside the SS segment limit. #PF(fault-code) If a page fault occurs. #NM If CR0.TS[bit 3] = 1. #UD If CPUID.01H:ECX.XSAVE[bit 26] = 0 or CPUID.(EAX=0DH,ECX=1):EAX.XSAVEC[bit 1] = 0. If CR4.OSXSAVE[bit 18] = 0. If the LOCK prefix is used.

XSAVEC—Save Processor Extended States With Compaction

6-58 Vol. 2D

INSTRUCTION SET REFERENCE, W-Z

#AC

If this exception is disabled a general protection exception (#GP) is signaled if the memory operand is not aligned on a 64-byte boundary, as described above. If the alignment check exception (#AC) is enabled (and the CPL is 3), signaling of #AC is not guaranteed and may vary with implementation, as follows. In all implementations where #AC is not signaled, a general protection exception is signaled in its place. In addition, the width of the alignment check may also vary with implementation. For instance, for a given implementation, an alignment check exception might be signaled for a 2-byte misalignment, whereas a general protection exception might be signaled for all other misalignments (4-, 8-, or 16-byte misalignments).

#### Real-Address Mode Exceptions

#GP If a memory operand is not aligned on a 64-byte boundary, regardless of segment. If any part of the operand lies outside the effective address space from 0 to FFFFH. #NM If CR0.TS[bit 3] = 1.

#UD If CPUID.01H:ECX.XSAVE[bit 26] = 0 or CPUID.(EAX=0DH,ECX=1):EAX.XSAVEC[bit 1] = 0. If CR4.OSXSAVE[bit 18] = 0.

If the LOCK prefix is used.

#### Virtual-8086 Mode Exceptions

Same exceptions as in protected mode.

#### Compatibility Mode Exceptions

Same exceptions as in protected mode.

#### 64-Bit Mode Exceptions

#GP(0) If the memory address is in a non-canonical form.

If a memory operand is not aligned on a 64-byte boundary, regardless of segment. #SS(0) If a memory address referencing the SS segment is in a non-canonical form. #PF(fault-code) If a page fault occurs. #NM If CR0.TS[bit 3] = 1. #UD If CPUID.01H:ECX.XSAVE[bit 26] = 0 or CPUID.(EAX=0DH,ECX=1):EAX.XSAVEC[bit 1] = 0. If CR4.OSXSAVE[bit 18] = 0.

If the LOCK prefix is used.

#AC If this exception is disabled a general protection exception (#GP) is signaled if the memory operand is not aligned on a 64-byte boundary, as described above. If the alignment check exception (#AC) is enabled (and the CPL is 3), signaling of #AC is not guaranteed and may vary with implementation, as follows. In all implementations where #AC is not signaled, a general protection exception is signaled in its place. In addition, the width of the alignment check may also vary with implementation. For instance, for a given implementation, an alignment check exception might be signaled for a 2-byte misalignment, whereas a general protection exception might be signaled for all other misalignments (4-, 8-, or 16-byte misalignments).

XSAVEC—Save Processor Extended States With Compaction

Vol. 2D 6-59

INSTRUCTION SET REFERENCE, W-Z

## XSAVEOPT—Save Processor Extended States Optimized

|Opcode/<br>Instruction|Op/<br>En|64/32 bit<br>Mode<br>Support|CPUID<br>Feature<br>Flag|Description|
|---|---|---|---|---|
|NP 0F AE /6|M|V/V|XSAVEOPT|Save state components specified by EDX:EAX|
|XSAVEOPT mem||||to mem, optimizing if possible.|
|NP REX.W + 0F AE /6<br>XSAVEOPT64 mem|M|V/V|XSAVEOPT|Save state components specified by EDX:EAX<br>to mem, optimizing if possible.|



#### Instruction Operand Encoding

|Op/En|Operand 1|Operand 2|Operand 3|Operand 4|
|---|---|---|---|---|
|M|ModRM:r/m (r, w)|N/A|N/A|N/A|



#### Description

Performs a full or partial save of processor state components to the XSAVE area located at the memory address specified by the destination operand. The implicit EDX:EAX register pair specifies a 64-bit instruction mask. The specific state components saved correspond to the bits set in the requested-feature bitmap (RFBM), which is the logical-AND of EDX:EAX and XCR0.

The format of the XSAVE area is detailed in Section 13.4, “XSAVE Area,” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ . Like FXRSTOR and FXSAVE, the memory format used for x87 state depends on a REX.W prefix; see Section 13.5.1, “x87 State” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ .

Section 13.9, “Operation of XSAVEOPT,” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ provides a detailed description of the operation of the XSAVEOPT instruction. The following items provide a high-level outline:

- Execution of XSAVEOPT is similar to that of XSAVE. XSAVEOPT differs from XSAVE in that it may use the init and modified optimizations. The performance of XSAVEOPT will be equal to or better than that of XSAVE.

- XSAVEOPT saves state component _i_ only if RFBM[ _i_ ] = 1 and XINUSE[ _i_ ] = 1.<sup>1</sup> (XINUSE is a bitmap by which the processor tracks the status of various state components. See Section 13.6, “Processor Tracking of XSAVEManaged State”of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ .) Even if both bits are 1, XSAVEOPT may optimize and not save state component _i_ if (1) state component _i_ has not been modified since the last execution of XRSTOR or XRSTORS; and (2) this execution of XSAVES corresponds to that last execution of XRSTOR or XRSTORS as determined by the internal value XRSTOR_INFO (see the Operation section below).

- XSAVEOPT does not modify bytes 511:464 of the legacy region of the XSAVE area (see Section 13.4.1, “Legacy Region of an XSAVE Area” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ ).

- XSAVEOPT reads the XSTATE_BV field of the XSAVE header (see Section 13.4.2, “XSAVE Header” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ ) and writes a modified value back to memory as follows. If RFBM[ _i_ ] = 1, XSAVEOPT writes XSTATE_BV[ _i_ ] with the value of XINUSE[ _i_ ]. If RFBM[ _i_ ] = 0, XSAVEOPT writes XSTATE_BV[ _i_ ] with the value that it read from memory (it does not modify the bit). XSAVEOPT does not write to any part of the XSAVE header other than the XSTATE_BV field.

- XSAVEOPT always uses the standard format of the extended region of the XSAVE area (see Section 13.4.3, “Extended Region of an XSAVE Area” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ ).

Use of a destination operand not aligned to 64-byte boundary (in either 64-bit or 32-bit modes) will result in a general-protection (#GP) exception. In 64-bit mode, the upper 32 bits of RDX and RAX are ignored.

1. There is an exception made for MXCSR and MXCSR_MASK, which belong to state component 1 — SSE. XSAVEOPT always saves these to memory if RFBM[1] = 1 or RFBM[2] = 1, regardless of the value of XINUSE.

XSAVEOPT—Save Processor Extended States Optimized

6-60 Vol. 2D

INSTRUCTION SET REFERENCE, W-Z

See Section 13.6, “Processor Tracking of XSAVE-Managed State,” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ for discussion of the bitmap XMODIFIED and of the quantity XRSTOR_INFO.

#### Operation

RFBM := XCR0 AND EDX:EAX; /* bitwise logical AND */ OLD_BV := XSTATE_BV field from XSAVE header; TO_BE_SAVED := RFBM AND XINUSE;

IF in VMX non-root operation THEN VMXNR := 1; ELSE VMXNR := 0; FI;

LAXA := linear address of XSAVE area; IF XRSTOR_INFO =  CPL,VMXNR,LAXA,00000000_00000000H  THEN TO_BE_SAVED := TO_BE_SAVED AND XMODIFIED;

FI;

IF TO_BE_SAVED[0] = 1

THEN store x87 state into legacy region of XSAVE area;

FI;

IF TO_BE_SAVED[1]

THEN store XMM registers into legacy region of XSAVE area; // this step does not save MXCSR or MXCSR_MASK

FI;

IF RFBM[1] = 1 or RFBM[2] = 1

THEN store MXCSR and MXCSR_MASK into legacy region of XSAVE area;

FI;

FOR i := 2 TO 62

IF TO_BE_SAVED[i] = 1

THEN save XSAVE state component i at offset n from base of XSAVE area (n enumerated by CPUID(EAX=0DH,ECX=i):EBX); FI;

ENDFOR;

XSTATE_BV field in XSAVE header := (OLD_BV AND NOT RFBM) OR (XINUSE AND RFBM);

Flags Affected

None.

#### Intel C/C++ Compiler Intrinsic Equivalent

XSAVEOPT: void _xsaveopt( void * , unsigned __int64); XSAVEOPT: void _xsaveopt64( void * , unsigned __int64);

#### Protected Mode Exceptions

#GP(0) If a memory operand effective address is outside the CS, DS, ES, FS, or GS segment limit. If a memory operand is not aligned on a 64-byte boundary, regardless of segment. #SS(0) If a memory operand effective address is outside the SS segment limit. #PF(fault-code) If a page fault occurs. #NM If CR0.TS[bit 3] = 1.

XSAVEOPT—Save Processor Extended States Optimized

Vol. 2D 6-61

INSTRUCTION SET REFERENCE, W-Z

#UD If CPUID.01H:ECX.XSAVE[bit 26] = 0 or CPUID.(EAX=0DH,ECX=1):EAX.XSAVEOPT[bit 0] = 0.

If CR4.OSXSAVE[bit 18] = 0.

If the LOCK prefix is used.

#AC If this exception is disabled a general protection exception (#GP) is signaled if the memory operand is not aligned on a 64-byte boundary, as described above. If the alignment check exception (#AC) is enabled (and the CPL is 3), signaling of #AC is not guaranteed and may vary with implementation, as follows. In all implementations where #AC is not signaled, a general protection exception is signaled in its place. In addition, the width of the alignment check may also vary with implementation. For instance, for a given implementation, an alignment check exception might be signaled for a 2-byte misalignment, whereas a general protection exception might be signaled for all other misalignments (4-, 8-, or 16-byte misalignments).

#### Real-Address Mode Exceptions

#GP If a memory operand is not aligned on a 64-byte boundary, regardless of segment. If any part of the operand lies outside the effective address space from 0 to FFFFH. #NM If CR0.TS[bit 3] = 1.

#UD If CPUID.01H:ECX.XSAVE[bit 26] = 0 or CPUID.(EAX=0DH,ECX=1):EAX.XSAVEOPT[bit 0] = 0.

If CR4.OSXSAVE[bit 18] = 0. If the LOCK prefix is used.

#### Virtual-8086 Mode Exceptions

Same exceptions as in protected mode.

#### Compatibility Mode Exceptions

Same exceptions as in protected mode.

#### 64-Bit Mode Exceptions

#SS(0) If a memory address referencing the SS segment is in a non-canonical form. #GP(0) If the memory address is in a non-canonical form. If a memory operand is not aligned on a 64-byte boundary, regardless of segment. #PF(fault-code) If a page fault occurs. #NM If CR0.TS[bit 3] = 1. #UD If CPUID.01H:ECX.XSAVE[bit 26] = 0 or CPUID.(EAX=0DH,ECX=1):EAX.XSAVEOPT[bit 0] = 0. If CR4.OSXSAVE[bit 18] = 0. If the LOCK prefix is used.

#AC If this exception is disabled a general protection exception (#GP) is signaled if the memory operand is not aligned on a 64-byte boundary, as described above. If the alignment check exception (#AC) is enabled (and the CPL is 3), signaling of #AC is not guaranteed and may vary with implementation, as follows. In all implementations where #AC is not signaled, a general protection exception is signaled in its place. In addition, the width of the alignment check may also vary with implementation. For instance, for a given implementation, an alignment check exception might be signaled for a 2-byte misalignment, whereas a general protection exception might be signaled for all other misalignments (4-, 8-, or 16-byte misalignments).

XSAVEOPT—Save Processor Extended States Optimized

6-62 Vol. 2D

INSTRUCTION SET REFERENCE, W-Z

## XSAVES—Save Processor Extended States Supervisor

|Opcode /<br>Instruction|Op/<br>En|64/32 bit<br>Mode<br>Support|CPUID<br>Feature<br>Flag|Description|
|---|---|---|---|---|
|NP 0F C7 /5|M|V/V|XSS|Save state components specified by EDX:EAX to|
|XSAVES mem||||mem with compaction, optimizing if possible.|
|NP REX.W + 0F C7 /5<br>XSAVES64 mem|M|V/N.E.|XSS|Save state components specified by EDX:EAX to<br>mem with compaction, optimizing if possible.|



#### Instruction Operand Encoding

|Op/En|Operand 1|Operand 2|Operand 3|Operand 4|
|---|---|---|---|---|
|M|ModRM:r/m (w)|N/A|N/A|N/A|



#### Description

Performs a full or partial save of processor state components to the XSAVE area located at the memory address specified by the destination operand. The implicit EDX:EAX register pair specifies a 64-bit instruction mask. The specific state components saved correspond to the bits set in the requested-feature bitmap (RFBM), the logicalAND of EDX:EAX and the logical-OR of XCR0 with the IA32_XSS MSR. XSAVES may be executed only if CPL = 0.

The format of the XSAVE area is detailed in Section 13.4, “XSAVE Area,” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ . Like FXRSTOR and FXSAVE, the memory format used for x87 state depends on a REX.W prefix; see Section 13.5.1, “x87 State” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ .

Section 13.11, “Operation of XSAVES,” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ provides a detailed description of the operation of the XSAVES instruction. The following items provide a highlevel outline:

- Execution of XSAVES is similar to that of XSAVEC. XSAVES differs from XSAVEC in that it can save state components corresponding to bits set in the IA32_XSS MSR and that it may use the modified optimization.

- XSAVES saves state component _i_ only if RFBM[ _i_ ] = 1 and XINUSE[ _i_ ] = 1.<sup>1</sup> (XINUSE is a bitmap by which the processor tracks the status of various state components. See Section 13.6, “Processor Tracking of XSAVEManaged State” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ .) Even if both bits are 1, XSAVES may optimize and not save state component _i_ if (1) state component _i_ has not been modified since the last execution of XRSTOR or XRSTORS; and (2) this execution of XSAVES correspond to that last execution of XRSTOR or XRSTORS as determined by XRSTOR_INFO (see the Operation section below).

- XSAVES does not modify bytes 511:464 of the legacy region of the XSAVE area (see Section 13.4.1, “Legacy Region of an XSAVE Area” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ ).

- XSAVES writes the logical AND of RFBM and XINUSE to the XSTATE_BV field of the XSAVE header.<sup>2</sup> (See Section 13.4.2, “XSAVE Header” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ .) XSAVES sets bit 63 of the XCOMP_BV field and sets bits 62:0 of that field to RFBM[62:0]. XSAVES does not write to any parts of the XSAVE header other than the XSTATE_BV and XCOMP_BV fields.

- XSAVES always uses the compacted format of the extended region of the XSAVE area (see Section 13.4.3, “Extended Region of an XSAVE Area” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ ).

Use of a destination operand not aligned to 64-byte boundary (in either 64-bit or 32-bit modes) results in a general-protection (#GP) exception. In 64-bit mode, the upper 32 bits of RDX and RAX are ignored.

1. There is an exception for state component 1 (SSE). MXCSR is part of SSE state, but XINUSE[1] may be 0 even if MXCSR does not have its initial value of 1F80H. In this case, the init optimization does not apply and XSAVEC will save SSE state as long as RFBM[1] = 1 and the modified optimization is not being applied.

2. There is an exception for state component 1 (SSE). MXCSR is part of SSE state, but XINUSE[1] may be 0 even if MXCSR does not have its initial value of 1F80H. In this case, XSAVES sets XSTATE_BV[1] to 1 as long as RFBM[1] = 1.

XSAVES—Save Processor Extended States Supervisor

Vol. 2D 6-63

INSTRUCTION SET REFERENCE, W-Z

See Section 13.6, “Processor Tracking of XSAVE-Managed State,” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ for discussion of the bitmap XMODIFIED and of the quantity XRSTOR_INFO.

#### Operation

RFBM := (XCR0 OR IA32_XSS) AND EDX:EAX; /* bitwise logical OR and AND */ IF in VMX non-root operation THEN VMXNR := 1; ELSE VMXNR := 0; FI; LAXA := linear address of XSAVE area; COMPMASK := RFBM OR 80000000_00000000H; TO_BE_SAVED := RFBM AND XINUSE; IF XRSTOR_INFO =  CPL,VMXNR,LAXA,COMPMASK  THEN TO_BE_SAVED := TO_BE_SAVED AND XMODIFIED; FI; IF MXCSR ≠ 1F80H AND RFBM[1] THEN TO_BE_SAVED[1] = 1; FI; IF TO_BE_SAVED[0] = 1 THEN store x87 state into legacy region of XSAVE area; FI;

IF TO_BE_SAVED[1] = 1

THEN store SSE state into legacy region of XSAVE area; // this step saves the XMM registers, MXCSR, and MXCSR_MASK FI;

NEXT_FEATURE_OFFSET = 576; // Legacy area and XSAVE header consume 576 bytes FOR i := 2 TO 62 IF RFBM[i] = 1 THEN IF TO_BE_SAVED[i] THEN save XSAVE state component i at offset NEXT_FEATURE_OFFSET from base of XSAVE area; IF i = 8 // state component 8 is for PT state THEN IA32_RTIT_CTL.TraceEn[bit 0] := 0; FI; FI;

NEXT_FEATURE_OFFSET = NEXT_FEATURE_OFFSET + n (n enumerated by CPUID(EAX=0DH,ECX=i):EAX); FI; ENDFOR;

NEW_HEADER := RFBM AND XINUSE; IF MXCSR ≠ 1F80H AND RFBM[1] THEN NEW_HEADER[1] = 1; FI; XSTATE_BV field in XSAVE header := NEW_HEADER; XCOMP_BV field in XSAVE header := COMPMASK;

Flags Affected

None.

XSAVES—Save Processor Extended States Supervisor

6-64 Vol. 2D

INSTRUCTION SET REFERENCE, W-Z

#### Intel C/C++ Compiler Intrinsic Equivalent

XSAVES: void _xsaves( void * , unsigned __int64); XSAVES64: void _xsaves64( void * , unsigned __int64);

#### Protected Mode Exceptions

#GP(0) If CPL > 0.

If a memory operand effective address is outside the CS, DS, ES, FS, or GS segment limit. If a memory operand is not aligned on a 64-byte boundary, regardless of segment. #SS(0) If a memory operand effective address is outside the SS segment limit. #PF(fault-code) If a page fault occurs. #NM If CR0.TS[bit 3] = 1. #UD If CPUID.01H:ECX.XSAVE[bit 26] = 0 or CPUID.(EAX=0DH,ECX=1):EAX.XSS[bit 3] = 0. If CR4.OSXSAVE[bit 18] = 0. If the LOCK prefix is used.

#### Real-Address Mode Exceptions

#GP If a memory operand is not aligned on a 64-byte boundary, regardless of segment. If any part of the operand lies outside the effective address space from 0 to FFFFH. #NM If CR0.TS[bit 3] = 1. #UD If CPUID.01H:ECX.XSAVE[bit 26] = 0 or CPUID.(EAX=0DH,ECX=1):EAX.XSS[bit 3] = 0. If CR4.OSXSAVE[bit 18] = 0. If the LOCK prefix is used.

#### Virtual-8086 Mode Exceptions

Same exceptions as in protected mode.

#### Compatibility Mode Exceptions

Same exceptions as in protected mode.

#### 64-Bit Mode Exceptions

#GP(0) If CPL > 0.

If the memory address is in a non-canonical form. If a memory operand is not aligned on a 64-byte boundary, regardless of segment. #SS(0) If a memory address referencing the SS segment is in a non-canonical form. #PF(fault-code) If a page fault occurs. #NM If CR0.TS[bit 3] = 1. #UD If CPUID.01H:ECX.XSAVE[bit 26] = 0 or CPUID.(EAX=0DH,ECX=1):EAX.XSS[bit 3] = 0. If CR4.OSXSAVE[bit 18] = 0. If the LOCK prefix is used.

XSAVES—Save Processor Extended States Supervisor

Vol. 2D 6-65

INSTRUCTION SET REFERENCE, W-Z

## XSETBV—Set Extended Control Register

|Opcode|Instruction|Op/<br>En|64-Bit<br>Mode|Compat/<br>Leg Mode|Description|
|---|---|---|---|---|---|
|NP 0F 01 D1|XSETBV|ZO|Valid|Valid|Write the value in EDX:EAX to the XCR<br>specified by ECX.|



#### Instruction Operand Encoding

|Op/En|Operand 1|Operand 2|Operand 3|Operand 4|
|---|---|---|---|---|
|ZO|N/A|N/A|N/A|N/A|



#### Description

Writes the contents of registers EDX:EAX into the 64-bit extended control register (XCR) specified in the ECX register. (On processors that support the Intel 64 architecture, the high-order 32 bits of RCX are ignored.) The contents of the EDX register are copied to high-order 32 bits of the selected XCR and the contents of the EAX register are copied to low-order 32 bits of the XCR. (On processors that support the Intel 64 architecture, the highorder 32 bits of each of RAX and RDX are ignored.) Undefined or reserved bits in an XCR should be set to values previously read.

This instruction must be executed at privilege level 0 or in real-address mode; otherwise, a general protection exception #GP(0) is generated. Specifying a reserved or unimplemented XCR in ECX will also cause a general protection exception. The processor will also generate a general protection exception if software attempts to write to reserved bits in an XCR.

Currently, only XCR0 is supported. Thus, all other values of ECX are reserved and will cause a #GP(0). Note that bit 0 of XCR0 (corresponding to x87 state) must be set to 1; the instruction will cause a #GP(0) if an attempt is made to clear this bit. In addition, the instruction causes a #GP(0) if an attempt is made to set XCR0[2] (AVX state) while clearing XCR0[1] (SSE state); it is necessary to set both bits to use AVX instructions; Section 13.3, “Enabling the XSAVE Feature Set and XSAVE-Enabled Features,” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ .

#### Operation

XCR[ECX] := EDX:EAX;

Flags Affected

None.

#### Intel C/C++ Compiler Intrinsic Equivalent

XSETBV: void _xsetbv( unsigned int, unsigned __int64);

#### Protected Mode Exceptions

#GP(0) If the current privilege level is not 0. If an invalid XCR is specified in ECX. If the value in EDX:EAX sets bits that are reserved in the XCR specified by ECX. If an attempt is made to clear bit 0 of XCR0. If an attempt is made to set XCR0[2:1] to 10b. #UD If CPUID.01H:ECX.XSAVE[bit 26] = 0. If CR4.OSXSAVE[bit 18] = 0. If the LOCK prefix is used.

XSETBV—Set Extended Control Register

6-66 Vol. 2D

INSTRUCTION SET REFERENCE, W-Z

#### Real-Address Mode Exceptions

#GP If an invalid XCR is specified in ECX. If the value in EDX:EAX sets bits that are reserved in the XCR specified by ECX. If an attempt is made to clear bit 0 of XCR0. If an attempt is made to set XCR0[2:1] to 10b. #UD If CPUID.01H:ECX.XSAVE[bit 26] = 0. If CR4.OSXSAVE[bit 18] = 0. If the LOCK prefix is used.

Virtual-8086 Mode Exceptions

#GP(0) The XSETBV instruction is not recognized in virtual-8086 mode.

#### Compatibility Mode Exceptions

Same exceptions as in protected mode.

#### 64-Bit Mode Exceptions

Same exceptions as in protected mode.

XSETBV—Set Extended Control Register

Vol. 2D 6-67

INSTRUCTION SET REFERENCE, W-Z

## XSUSLDTRK—Suspend Tracking Load Addresses

|Opcode/<br>Instruction|Op/<br>En|64/32<br>bit Mode<br>Support|CPUID Feature<br>Flag|Description|
|---|---|---|---|---|
|F2 0F 01 E8<br>XSUSLDTRK|ZO|V/V|TSXLDTRK|Specifies the start of an Intel TSX suspend<br>read address tracking region.|



Instruction Operand Encoding

|Op/En|Tuple|Operand 1|Operand 2|Operand 3|Operand 4|
|---|---|---|---|---|---|
|ZO|N/A|N/A|N/A|N/A|N/A|



##### Description

The instruction marks the start of an Intel TSX (RTM) suspend load address tracking region. If the instruction is used inside a transactional region, subsequent loads are not added to the read set of the transaction. If the instruction is used inside a suspend load address tracking region it will cause transaction abort.

If the instruction is used outside of a transactional region it behaves like a NOP.

Chapter 16, “Programming with Intel® Transactional Synchronization Extensions” in the _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 1_ provides additional information on Intel<sup>®</sup> TSX Suspend Load Address Tracking.

##### Operation

##### XSUSLDTRK

IF RTM_ACTIVE = 1: IF SUSLDTRK_ACTIVE = 0: SUSLDTRK_ACTIVE := 1 ELSE: RTM_ABORT ELSE: NOP

Flags Affected

None.

Intel C/C++ Compiler Intrinsic Equivalent

XSUSLDTRK void _xsusldtrk(void);

SIMD Floating-Point Exceptions

None.

Other Exceptions #UD If CPUID.(EAX=7, ECX=0):EDX.TSXLDTRK[bit 16] = 0. If the LOCK prefix is used.

XSUSLDTRK—Suspend Tracking Load Addresses

6-68 Vol. 2D

INSTRUCTION SET REFERENCE, W-Z

## XTEST—Test if in Transactional Execution

|Opcode/Instruction|Op/<br>En|64/32bit<br>Mode<br>Support|CPUID<br>Feature<br>Flag|Description|
|---|---|---|---|---|
|NP 0F 01 D6<br>XTEST|ZO|V/V|HLE or<br>RTM|Test if executing in a transactional region.|



#### Instruction Operand Encoding

|Op/En|Operand 1|Operand2|Operand3|Operand4|
|---|---|---|---|---|
|ZO|N/A|N/A|N/A|N/A|



#### Description

The XTEST instruction queries the transactional execution status. If the instruction executes inside a transactionally executing RTM region or a transactionally executing HLE region, then the ZF flag is cleared, else it is set.

#### Operation

##### XTEST

IF (RTM_ACTIVE = 1 OR HLE_ACTIVE = 1) THEN ZF := 0 ELSE ZF := 1

FI;

#### Flags Affected

The ZF flag is cleared if the instruction is executed transactionally; otherwise it is set to 1. The CF, OF, SF, PF, and AF, flags are cleared.

Intel C/C++ Compiler Intrinsic Equivalent

XTEST: int _xtest( void );

#### SIMD Floating-Point Exceptions

None

#### Other Exceptions

#UD CPUID.(EAX=7, ECX=0):EBX.HLE[bit 4] = 0 and CPUID.(EAX=7, ECX=0):EBX.RTM[bit 11] = 0.

If LOCK prefix is used.

XTEST—Test if in Transactional Execution

Vol. 2D 6-69

INSTRUCTION SET REFERENCE, W-Z

XTEST—Test if in Transactional Execution

6-70 Vol. 2D
