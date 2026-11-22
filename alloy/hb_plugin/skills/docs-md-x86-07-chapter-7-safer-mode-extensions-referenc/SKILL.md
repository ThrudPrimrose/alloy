---
name: docs-md-x86-07-chapter-7-safer-mode-extensions-referenc
description: "Intel SDM Vol. 2: Chapter 7 Safer Mode Extensions Reference (vendor documentation for x86 AVX2, AVX-512 and AVX-512 FP16)."
when: "when you need Intel SDM Vol. 2: Chapter 7 Safer Mode Extensions Reference while writing a kernel for x86 AVX2, AVX-512 and AVX-512 FP16."
---

CHAPTER 7 SAFER MODE EXTENSIONS REFERENCE

# 7.1 OVERVIEW

This chapter describes the Safer Mode Extensions (SMX) for the Intel 64 and IA-32 architectures. Safer Mode Extensions (SMX) provide a programming interface for system software to establish a measured environment within the platform to support trust decisions by end users. The measured environment includes:

- Measured launch of a system executive, referred to as a Measured Launched Environment (MLE)<sup>1</sup> . The system executive may be based on a Virtual Machine Monitor (VMM), a measured VMM is referred to as MVMM<sup>2</sup> .

- Mechanisms to ensure the above measurement is protected and stored in a secure location in the platform.

- Protection mechanisms that allow the VMM to control attempts to modify the VMM.

The measurement and protection mechanisms used by a measured environment are supported by the capabilities of an Intel<sup>®</sup> Trusted Execution Technology (Intel<sup>®</sup> TXT) platform:

- The SMX are the processor’s programming interface in an Intel TXT platform.

- The chipset in an Intel TXT platform provides enforcement of the protection mechanisms.

- Trusted Platform Module (TPM) 1.2 in the platform provides platform configuration registers (PCRs) to store software measurement values.

# 7.2 SMX FUNCTIONALITY

SMX functionality is provided in an Intel 64 processor through the GETSEC instruction via leaf functions. The GETSEC instruction supports multiple leaf functions. Leaf functions are selected by the value in EAX at the time GETSEC is executed. Each GETSEC leaf function is documented separately in the reference pages with a unique mnemonic (even though these mnemonics share the same opcode, 0F 37).

## 7.2.1 Detecting and Enabling SMX

Software can detect support for SMX operation using the CPUID instruction. If software executes CPUID with 1 in EAX, a value of 1 in bit 6 of ECX indicates support for SMX operation (GETSEC is available), see CPUID instruction for the layout of feature flags of reported by CPUID.01H:ECX.

System software enables SMX operation by setting CR4.SMXE[Bit 14] = 1 before attempting to execute GETSEC. Otherwise, execution of GETSEC results in the processor signaling an invalid opcode exception (#UD).

If the CPUID SMX feature flag is clear (CPUID.01H.ECX[Bit 6] = 0), attempting to set CR4.SMXE[Bit 14] results in a general protection exception.

The IA32_FEATURE_CONTROL MSR (at address 03AH) provides feature control bits that configure operation of VMX and SMX. These bits are documented in Table 7-1.

1. See _Intel® Trusted Execution Technology Measured Launched Environment Programming Guide_ .

2. An MVMM is sometimes referred to as a measured launched environment (MLE). See Intel® Trusted Execution Technology Measured Launched Environment Programming Guide

Vol. 2D 7-1

SAFER MODE EXTENSIONS REFERENCE

Table 7-1.  Layout of IA32_FEATURE_CONTROL

|Bit Position|Description|
|---|---|
|0|Lock bit (0 = unlocked, 1 = locked). When set to '1' further writes to this MSR are blocked.|
|1|Enable VMX in SMX operation.|
|2|Enable VMX outside SMX operation.|
|7:3|Reserved|
|14:8|SENTER Local Function Enables: When set, each bit in the field represents an enable control for a corresponding<br>SENTER function.|
|15|SENTER Global Enable: Must be set to ‘1’ to enable operation of GETSEC[SENTER].|
|16|Reserved|
|17|SGX Launch Control Enable: Must be set to ‘1’ to enable runtime re-configuration of SGX Launch Control via the<br>IA32_SGXLEPUBKEYHASHn MSR.|
|18|SGX Global Enable: Must be set to ‘1’ to enable Intel SGX leaf functions.|
|19|Reserved|
|20|LMCE On: When set, system software can program the MSRs associated with LMCE to configure delivery of some<br>machine check exceptions to a single logical processor.|
|63:21|Reserved|



- Bit 0 is a lock bit. If the lock bit is clear, an attempt to execute VMXON will cause a general-protection exception. Attempting to execute GETSEC[SENTER] when the lock bit is clear will also cause a general-protection exception. If the lock bit is set, WRMSR to the IA32_FEATURE_CONTROL MSR will cause a general-protection exception. Once the lock bit is set, the MSR cannot be modified until a power-on reset. System BIOS can use this bit to provide a setup option for BIOS to disable support for VMX, SMX or both VMX and SMX.

- Bit 1 enables VMX in SMX operation (between executing the SENTER and SEXIT leaves of GETSEC). If this bit is clear, an attempt to execute VMXON in SMX will cause a general-protection exception if executed in SMX operation. Attempts to set this bit on logical processors that do not support both VMX operation (Chapter 7, “Safer Mode Extensions Reference”) and SMX operation cause general-protection exceptions.

- Bit 2 enables VMX outside SMX operation. If this bit is clear, an attempt to execute VMXON will cause a generalprotection exception if executed outside SMX operation. Attempts to set this bit on logical processors that do not support VMX operation cause general-protection exceptions.

- Bits 8 through 14 specify enabled functionality of the SENTER leaf function. Each bit in the field represents an enable control for a corresponding SENTER function. Only enabled SENTER leaf functionality can be used when executing SENTER.

- Bits 15 specify global enable of all SENTER functionalities.

## 7.2.2 SMX Instruction Summary

System software must first query for available GETSEC leaf functions by executing GETSEC[CAPABILITIES]. The CAPABILITIES leaf function returns a bit map of available GETSEC leaves. An attempt to execute an unsupported leaf index results in an undefined opcode (#UD) exception.

7-2 Vol. 2D

SAFER MODE EXTENSIONS REFERENCE

### 7.2.2.1 GETSEC[CAPABILITIES]

The SMX functionality provides an architectural interface for newer processor generations to extend SMX capabilities. Specifically, the GETSEC instruction provides a capability leaf function for system software to discover the available GETSEC leaf functions that are supported in a processor. Table 7-2 lists the currently available GETSEC leaf functions.

> . Table 7-2.  GETSEC Leaf Functions

|Index (EAX)|Leaf function|Description|
|---|---|---|
|0|CAPABILITIES|Returns the available leaf functions of the GETSEC instruction.|
|1|Undefined|Reserved|
|2|ENTERACCS|Enter|
|3|EXITAC|Exit|
|4|SENTER|Launch an MLE.|
|5|SEXIT|Exit the MLE.|
|6|PARAMETERS|Return SMX related parameter information.|
|7|SMCTRL|SMX mode control.|
|8|WAKEUP|Wake up sleeping processors in safer mode.|
|9 - (4G-1)|Undefined|Reserved|



### 7.2.2.2 GETSEC[ENTERACCS]

The GETSEC[ENTERACCS] leaf enables authenticated code execution mode. The ENTERACCS leaf function performs an authenticated code module load using the chipset public key as the signature verification. ENTERACCS requires the existence of an Intel® Trusted Execution Technology capable chipset since it unlocks the chipset private configuration register space after successful authentication of the loaded module. The physical base address and size of the authenticated code module are specified as input register values in EBX and ECX, respectively.

While in the authenticated code execution mode, certain processor state properties change. For this reason, the time in which the processor operates in authenticated code execution mode should be limited to minimize impact on external system events.

Upon entry into , the previous paging context is disabled (since the authenticated code module image is specified with physical addresses and can no longer rely upon external memory-based page-table structures).

Prior to executing the GETSEC[ENTERACCS] leaf, system software must ensure the logical processor issuing GETSEC[ENTERACCS] is the boot-strap processor (BSP), as indicated by IA32_APIC_BASE.BSP = 1. System software must ensure other logical processors are in a suitable idle state and not marked as BSP.

The GETSEC[ENTERACCS] leaf may be used by different agents to load different authenticated code modules to perform functions related to different aspects of a measured environment, for example system software and Intel® TXT enabled BIOS may use more than one authenticated code modules.

### 7.2.2.3 GETSEC[EXITAC]

GETSEC[EXITAC] takes the processor out of . When this instruction leaf is executed, the contents of the authenticated code execution area are scrubbed and control is transferred to the non-authenticated context defined by a near pointer passed with the GETSEC[EXITAC] instruction.

The authenticated code execution area is no longer accessible after completion of GETSEC[EXITAC]. RBX (or EBX) holds the address of the near absolute indirect target to be taken.

Vol. 2D 7-3

SAFER MODE EXTENSIONS REFERENCE

### 7.2.2.4 GETSEC[SENTER]

The GETSEC[SENTER] leaf function is used by the initiating logical processor (ILP) to launch an MLE. GETSEC[SENTER] can be considered a superset of the ENTERACCS leaf, because it enters as part of the measured environment launch.

Measured environment startup consists of the following steps:

- the ILP rendezvous the responding logical processors (RLPs) in the platform into a controlled state (At the completion of this handshake, all the RLPs except for the ILP initiating the measured environment launch are placed in a newly defined SENTER sleep state).

- Load and authenticate the authenticated code module required by the measured environment, and enter authenticated code execution mode.

- Verify and lock certain system configuration parameters.

- Measure the dynamic root of trust and store into the PCRs in TPM.

- Transfer control to the MLE with interrupts disabled.

Prior to executing the GETSEC[SENTER] leaf, system software must ensure the platform’s TPM is ready for access and the ILP is the boot-strap processor (BSP), as indicated by IA32_APIC_BASE.BSP. System software must ensure other logical processors (RLPs) are in a suitable idle state and not marked as BSP.

System software launching a measurement environment is responsible for providing a proper authenticate code module address when executing GETSEC[SENTER]. The AC module responsible for the launch of a measured environment and loaded by GETSEC[SENTER] is referred to as SINIT. See _Intel® Trusted Execution Technology Measured Launched Environment Programming Guide_ for additional information on system software requirements prior to executing GETSEC[SENTER].

### 7.2.2.5 GETSEC[SEXIT]

System software exits the measured environment by executing the instruction GETSEC[SEXIT] on the ILP. This instruction rendezvous the responding logical processors in the platform for exiting from the measured environment. External events (if left masked) are unmasked and Intel® TXT-capable chipset’s private configuration space is re-locked.

### 7.2.2.6 GETSEC[PARAMETERS]

The GETSEC[PARAMETERS] leaf function is used to report attributes, options, and limitations of SMX operation. Software uses this leaf to identify operating limits or additional options.

The information reported by GETSEC[PARAMETERS] may require executing the leaf multiple times using EBX as an index. If the GETSEC[PARAMETERS] instruction leaf or if a specific parameter field is not available, then SMX operation should be interpreted to use the default limits of respective GETSEC leaves or parameter fields defined in the GETSEC[PARAMETERS] leaf.

### 7.2.2.7 GETSEC[SMCTRL]

The GETSEC[SMCTRL] leaf function is used for providing additional control over specific conditions associated with the SMX architecture. An input register is supported for selecting the control operation to be performed. See the specific leaf description for details on the type of control provided.

### 7.2.2.8 GETSEC[WAKEUP]

Responding logical processors (RLPs) are placed in the SENTER sleep state after the initiating logical processor executes GETSEC[SENTER]. The ILP can wake up RLPs to join the measured environment by using GETSEC[WAKEUP]. When the RLPs in SENTER sleep state wake up, these logical processors begin execution at the entry point defined in a data structure held in system memory (pointed to by an chipset register LT.MLE.JOIN) in TXT configuration space.

7-4 Vol. 2D

SAFER MODE EXTENSIONS REFERENCE

## 7.2.3 Measured Environment and SMX

This section gives a simplified view of a representative life cycle of a measured environment that is launched by a system executive using SMX leaf functions. _Intel® Trusted Execution Technology Measured Launched Environment Programming Guide_ provides more detailed examples of using SMX and chipset resources (including chipset registers, Trusted Platform Module) to launch an MVMM.

The life cycle starts with the system executive (an OS, an OS loader, and so forth) loading the MLE and SINIT AC module into available system memory. The system executive must validate and prepare the platform for the measured launch. When the platform is properly configured, the system executive executes GETSEC[SENTER] on the initiating logical processor (ILP) to rendezvous the responding logical processors into an SENTER sleep state, the ILP then enters into using the SINIT AC module. In a multi-threaded or multi-processing environment, the system executive must ensure that other logical processors are already in an idle loop, or asleep (such as after executing HLT) before executing GETSEC[SENTER].

After the GETSEC[SENTER] rendezvous handshake is performed between all logical processors in the platform, the ILP loads the chipset authenticated code module (SINIT) and performs an authentication check. If the check passes, the processor hashes the SINIT AC module and stores the result into TPM PCR 17. It then switches execution context to the SINIT AC module. The SINIT AC module will perform a number of platform operations, including: verifying the system configuration, protecting the system memory used by the MLE from I/O devices capable of DMA, producing a hash of the MLE, storing the hash value in TPM PCR 18, and various other operations. When SINIT completes execution, it executes the GETSEC[EXITAC] instruction and transfers control the MLE at the designated entry point.

Upon receiving control from the SINIT AC module, the MLE must establish its protection and isolation controls before enabling DMA and interrupts and transferring control to other software modules. It must also wake up the RLPs from their SENTER sleep state using the GETSEC[WAKEUP] instruction and bring them into its protection and isolation environment.

While executing in a measured environment, the MVMM can access the Trusted Platform Module (TPM) in locality 2. The MVMM has complete access to all TPM commands and may use the TPM to report current measurement values or use the measurement values to protect information such that only when the platform configuration registers (PCRs) contain the same value is the information released from the TPM. This protection mechanism is known as sealing.

A measured environment shutdown is ultimately completed by executing GETSEC[SEXIT]. Prior to this step system software is responsible for scrubbing sensitive information left in the processor caches, system memory.

# 7.3 GETSEC LEAF FUNCTIONS

This section provides detailed descriptions of each leaf function of the GETSEC instruction. GETSEC is available only if CPUID.01H:ECX[Bit 6] = 1. This indicates the availability of SMX and the GETSEC instruction. Before GETSEC can be executed, SMX must be enabled by setting CR4.SMXE[Bit 14] = 1.

A GETSEC leaf can only be used if it is shown to be available as reported by the GETSEC[CAPABILITIES] function. Attempts to access a GETSEC leaf index not supported by the processor, or if CR4.SMXE is 0, results in the signaling of an undefined opcode exception.

All GETSEC leaf functions are available in protected mode, including the compatibility sub-mode of IA-32e mode and the 64-bit sub-mode of IA-32e mode. Unless otherwise noted, the behavior of all GETSEC functions and interactions related to the measured environment are independent of IA-32e mode. This also applies to the interpretation of register widths<sup>1</sup> passed as input parameters to GETSEC functions and to register results returned as output parameters.

1. This chapter uses the 64-bit notation RAX, RIP, RSP, RFLAGS, etc. for processor registers because processors that support SMX also support Intel 64 Architecture. The MVMM can be launched in IA-32e mode or outside IA-32e mode. The 64-bit notation of processor registers also refer to its 32-bit forms if SMX is used in 32-bit environment. In some places, notation such as EAX is used to refer specifically to lower 32 bits of the indicated register

Vol. 2D 7-5

SAFER MODE EXTENSIONS REFERENCE

The GETSEC functions ENTERACCS, SENTER, SEXIT, and WAKEUP require a Intel<sup>®</sup> TXT capable-chipset to be present in the platform. The GETSEC[CAPABILITIES] returned bit vector in position 0 indicates an Intel<sup>®</sup> TXTcapable chipset has been sampled present<sup>1</sup> by the processor.

The processor's operating mode also affects the execution of the following GETSEC leaf functions: SMCTRL, ENTERACCS, EXITAC, SENTER, SEXIT, and WAKEUP. These functions are only allowed in protected mode at CPL = 0. They are not allowed while in SMM in order to prevent potential intra-mode conflicts. Further execution qualifications exist to prevent potential architectural conflicts (for example: nesting of the measured environment or authenticated code execution mode). See the definitions of the GETSEC leaf functions for specific requirements.

For the purpose of performance monitor counting, the execution of GETSEC functions is counted as a single instruction with respect to retired instructions. The response by a responding logical processor (RLP) to messages associated with GETSEC[SENTER] or GTSEC[SEXIT] is transparent to the retired instruction count on the ILP.

> 1. Sampled present means that the processor sent a message to the chipset and the chipset responded that it (a) knows about the message and (b) is capable of executing SENTER. This means that the chipset CAN support Intel® TXT, and is configured and WILLING to support it.

7-6 Vol. 2D

SAFER MODE EXTENSIONS REFERENCE

## GETSEC[CAPABILITIES] - Report the SMX Capabilities

|Opcode|Instruction|Description|
|---|---|---|
|NP 0F 37|GETSEC[CAPABILITIES]|Report the SMX capabilities.|
|(EAX = 0)||The capabilities index is input in EBX with the result returned in EAX.|



#### Description

The GETSEC[CAPABILITIES] function returns a bit vector of supported GETSEC leaf functions. The CAPABILITIES leaf of GETSEC is selected with EAX set to 0 at entry. EBX is used as the selector for returning the bit vector field in EAX. GETSEC[CAPABILITIES] may be executed at all privilege levels, but the CR4.SMXE bit must be set or an undefined opcode exception (#UD) is returned.

With EBX = 0 upon execution of GETSEC[CAPABILITIES], EAX returns the a bit vector representing status on the presence of a Intel<sup>®</sup> TXT-capable chipset and the first 30 available GETSEC leaf functions. The format of the returned bit vector is provided in Table 7-3.

If bit 0 is set to 1, then an Intel<sup>®</sup> TXT-capable chipset has been sampled present by the processor. If bits in the range of 1-30 are set, then the corresponding GETSEC leaf function is available. If the bit value at a given bit index is 0, then the GETSEC leaf function corresponding to that index is unsupported and attempted execution results in a #UD.

Bit 31 of EAX indicates if further leaf indexes are supported. If the Extended Leafs bit 31 is set, then additional leaf functions are accessed by repeating GETSEC[CAPABILITIES] with EBX incremented by one. When the most significant bit of EAX is not set, then additional GETSEC leaf functions are not supported; indexing EBX to a higher value results in EAX returning zero.

Table 7-3.  GETSEC Capability Result Encoding (EBX = 0)

|Field|Bit position|Description|
|---|---|---|
|Chipset Present|0|Intel® TXT-capable chipset is present.|
|Undefined|1|Reserved|
|ENTERACCS|2|GETSEC[ENTERACCS] is available.|
|EXITAC|3|GETSEC[EXITAC] is available.|
|SENTER|4|GETSEC[SENTER] is available.|
|SEXIT|5|GETSEC[SEXIT] is available.|
|PARAMETERS|6|GETSEC[PARAMETERS] is available.|
|SMCTRL|7|GETSEC[SMCTRL] is available.|
|WAKEUP|8|GETSEC[WAKEUP] is available.|
|Undefined|30:9|Reserved|
|Extended Leafs|31|Reserved for extended information reporting of GETSEC capabilities.|



GETSEC[CAPABILITIES] - Report the SMX Capabilities

Vol. 2D 7-7

SAFER MODE EXTENSIONS REFERENCE

Operation IF (CR4.SMXE=0) THEN #UD; ELSIF (in VMX non-root operation) THEN VM Exit (reason=”GETSEC instruction”); IF (EBX=0) THEN BitVector := 0; IF (TXT chipset present) BitVector[Chipset present] := 1; IF (ENTERACCS Available) THEN BitVector[ENTERACCS] := 1; IF (EXITAC Available) THEN BitVector[EXITAC] := 1; IF (SENTER Available) THEN BitVector[SENTER] := 1; IF (SEXIT Available) THEN BitVector[SEXIT] := 1; IF (PARAMETERS Available) THEN BitVector[PARAMETERS] := 1; IF (SMCTRL Available) THEN BitVector[SMCTRL] := 1; IF (WAKEUP Available) THEN BitVector[WAKEUP] := 1; EAX := BitVector; ELSE EAX := 0; END;; Flags Affected None Use of Prefixes LOCK Causes #UD. REP* Cause #UD (includes REPNE/REPNZ and REP/REPE/REPZ). Operand size Causes #UD. NP 66/F2/F3 prefixes are not allowed. Segment overrides Ignored. Address size Ignored. REX Ignored. Protected Mode Exceptions #UD IF CR4.SMXE = 0. Real-Address Mode Exceptions #UD IF CR4.SMXE = 0. Virtual-8086 Mode Exceptions #UD IF CR4.SMXE = 0. Compatibility Mode Exceptions #UD IF CR4.SMXE = 0.

7-8 Vol. 2D

GETSEC[CAPABILITIES] - Report the SMX Capabilities

SAFER MODE EXTENSIONS REFERENCE

64-Bit Mode Exceptions #UD IF CR4.SMXE = 0. VM-exit Condition Reason (GETSEC) IF in VMX non-root operation.

GETSEC[CAPABILITIES] - Report the SMX Capabilities

Vol. 2D 7-9

SAFER MODE EXTENSIONS REFERENCE

## GETSEC[ENTERACCS] — Execute Authenticated Chipset Code

|Opcode|Instruction|Description|
|---|---|---|
|NP 0F 37|GETSEC[ENTERACCS]|Enter authenticated code execution mode.|
|(EAX = 2)||EBX holds the authenticated code module physical base address. ECX holds the authenticated<br>code module size (bytes).|



#### Description

The GETSEC[ENTERACCS] function loads, authenticates, and executes an authenticated code module using an Intel<sup>®</sup> TXT platform chipset's public key. The ENTERACCS leaf of GETSEC is selected with EAX set to 2 at entry.

There are certain restrictions enforced by the processor for the execution of the GETSEC[ENTERACCS] instruction:

- Execution is not allowed unless the processor is in protected mode or IA-32e mode with CPL = 0 and EFLAGS.VM = 0.

- Processor cache must be available and not disabled, that is, CR0.CD and CR0.NW bits must be 0.

- For processor packages containing more than one logical processor, CR0.CD is checked to ensure consistency between enabled logical processors.

- For enforcing consistency of operation with numeric exception reporting using Interrupt 16, CR0.NE must be set.

- An Intel TXT-capable chipset must be present as communicated to the processor by sampling of the power-on configuration capability field after reset.

- The processor can not already be in authenticated code execution mode as launched by a previous GETSEC[ENTERACCS] or GETSEC[SENTER] instruction without a subsequent exiting using GETSEC[EXITAC]).

- To avoid potential operability conflicts between modes, the processor is not allowed to execute this instruction if it currently is in SMM or VMX operation.

- To ensure consistent handling of SIPI messages, the processor executing the GETSEC[ENTERACCS] instruction must also be designated the BSP (boot-strap processor) as defined by IA32_APIC_BASE.BSP (Bit 8).

Failure to conform to the above conditions results in the processor signaling a general protection exception.

Prior to execution of the ENTERACCS leaf, other logical processors, i.e., RLPs, in the platform must be:

- Idle in a wait-for-SIPI state (as initiated by an INIT assertion or through reset for non-BSP designated processors), or

- In the SENTER sleep state as initiated by a GETSEC[SENTER] from the initiating logical processor (ILP).

If other logical processor(s) in the same package are not idle in one of these states, execution of ENTERACCS signals a general protection exception. The same requirement and action applies if the other logical processor(s) of the same package do not have CR0.CD = 0.

A successful execution of ENTERACCS results in the ILP entering an authenticated code execution mode. Prior to reaching this point, the processor performs several checks. These include:

- Establish and check the location and size of the specified authenticated code module to be executed by the processor.

- Inhibit the ILP’s response to the external events: INIT, A20M, NMI, and SMI.

- Broadcast a message to enable protection of memory and I/O from other processor agents.

- Load the designated code module into an authenticated code execution area.

- Isolate the contents of the authenticated code execution area from further state modification by external agents.

- Authenticate the authenticated code module.

- Initialize the initiating logical processor state based on information contained in the authenticated code module header.

- Unlock the Intel<sup>®</sup> TXT-capable chipset private configuration space and TPM locality 3 space.

GETSEC[ENTERACCS] — Execute Authenticated Chipset Code

7-10 Vol. 2D

SAFER MODE EXTENSIONS REFERENCE

• Begin execution in the authenticated code module at the defined entry point.

The GETSEC[ENTERACCS] function requires two additional input parameters in the general purpose registers EBX and ECX. EBX holds the authenticated code (AC) module physical base address (the AC module must reside below 4 GBytes in physical address space) and ECX holds the AC module size (in bytes). The physical base address and size are used to retrieve the code module from system memory and load it into the internal authenticated code execution area. The base physical address is checked to verify it is on a modulo-4096 byte boundary. The size is verified to be a multiple of 64, that it does not exceed the internal authenticated code execution area capacity (as reported by GETSEC[CAPABILITIES]), and that the top address of the AC module does not exceed 32 bits. An error condition results in an abort of the authenticated code execution launch and the signaling of a general protection exception.

As an integrity check for proper processor hardware operation, execution of GETSEC[ENTERACCS] will also check the contents of all the machine check status registers (as reported by the MSRs IA32_MCi_STATUS) for any valid uncorrectable error condition. In addition, the global machine check status register IA32_MCG_STATUS MCIP bit must be cleared and the IERR processor package pin (or its equivalent) must not be asserted, indicating that no machine check exception processing is currently in progress. These checks are performed prior to initiating the load of the authenticated code module. Any outstanding valid uncorrectable machine check error condition present in these status registers at this point will result in the processor signaling a general protection violation.

The ILP masks the response to the assertion of the external signals INIT#, A20M, NMI#, and SMI#. This masking remains active until optionally unmasked by GETSEC[EXITAC] (this defined unmasking behavior assumes GETSEC[ENTERACCS] was not executed by a prior GETSEC[SENTER]). The purpose of this masking control is to prevent exposure to existing external event handlers that may not be under the control of the authenticated code module.

The ILP sets an internal flag to indicate it has entered authenticated code execution mode. The state of the A20M pin is likewise masked and forced internally to a de-asserted state so that any external assertion is not recognized during authenticated code execution mode.

To prevent other (logical) processors from interfering with the ILP operating in authenticated code execution mode, memory (excluding implicit write-back transactions) access and I/O originating from other processor agents are blocked. This protection starts when the ILP enters into authenticated code execution mode. Only memory and I/O transactions initiated from the ILP are allowed to proceed. Exiting authenticated code execution mode is done by executing GETSEC[EXITAC]. The protection of memory and I/O activities remains in effect until the ILP executes GETSEC[EXITAC].

Prior to launching the authenticated execution module using GETSEC[ENTERACCS] or GETSEC[SENTER], the processor’s MTRRs (Memory Type Range Registers) must first be initialized to map out the authenticated RAM addresses as WB (writeback). Failure to do so may affect the ability for the processor to maintain isolation of the loaded authenticated code module. If the processor detected this requirement is not met, it will signal an Intel® TXT reset condition with an error code during the loading of the authenticated code module.

While physical addresses within the load module must be mapped as WB, the memory type for locations outside of the module boundaries must be mapped to one of the supported memory types as returned by GETSEC[PARAMETERS] (or UC as default).

To conform to the minimum granularity of MTRR MSRs for specifying the memory type, authenticated code RAM (ACRAM) is allocated to the processor in 4096 byte granular blocks. If an AC module size as specified in ECX is not a multiple of 4096 then the processor will allocate up to the next 4096 byte boundary for mapping as ACRAM with indeterminate data. This pad area will not be visible to the authenticated code module as external memory nor can it depend on the value of the data used to fill the pad area.

At the successful completion of GETSEC[ENTERACCS], the architectural state of the processor is partially initialized from contents held in the header of the authenticated code module. The processor GDTR, CS, and DS selectors are initialized from fields within the authenticated code module. Since the authenticated code module must be relocatable, all address references must be relative to the authenticated code module base address in EBX. The processor GDTR base value is initialized to the AC module header field GDTBasePtr + module base address held in EBX and the GDTR limit is set to the value in the GDTLimit field. The CS selector is initialized to the AC module header SegSel field, while the DS selector is initialized to CS + 8. The segment descriptor fields are implicitly initialized to BASE=0, LIMIT=FFFFFh, G=1, D=1, P=1, S=1, read/write access for DS, and execute/read access for CS. The processor begins the authenticated code module execution with the EIP set to the AC module header EntryPoint field + module base address (EBX). The AC module based fields used for initializing the processor state are checked for consistency and any failure results in a shutdown condition.

GETSEC[ENTERACCS] — Execute Authenticated Chipset Code

Vol. 2D 7-11

SAFER MODE EXTENSIONS REFERENCE

A summary of the register state initialization after successful completion of GETSEC[ENTERACCS] is given for the processor in Table 7-4. The paging is disabled upon entry into authenticated code execution mode. The authenticated code module is loaded and initially executed using physical addresses. It is up to the system software after execution of GETSEC[ENTERACCS] to establish a new (or restore its previous) paging environment with an appropriate mapping to meet new protection requirements. EBP is initialized to the authenticated code module base physical address for initial execution in the authenticated environment. As a result, the authenticated code can reference EBP for relative address based references, given that the authenticated code module must be position independent.

Table 7-4.  Register State Initialization after GETSEC[ENTERACCS]

|Register State|Initialization Status|Comment|
|---|---|---|
|CR0|PG←0, AM←0, WP←0: Others unchanged|Paging, Alignment Check, Write-protection are<br>disabled.|
|CR4|MCE←0, CET←0,PCIDE←0: Others unchanged|Machine Check Exceptions, Control-flow<br>Enforcement Technology, and Process-context<br>Identifiers disabled.|
|EFLAGS|00000002H||
|IA32_EFER|0H|IA-32e mode disabled.|
|EIP|AC.base + EntryPoint|AC.base is in EBX as input to GETSEC[ENTERACCS].|
|[E|R]BX|Pre-ENTERACCS state: Next [E|R]IP prior to<br>GETSEC[ENTERACCS]|Carry forward 64-bit processor state across<br>GETSEC[ENTERACCS].|
|ECX|Pre-ENTERACCS state: [31:16]=GDTR.limit;<br>[15:0]=CS.sel|Carry forward processor state across<br>GETSEC[ENTERACCS].|
|[E|R]DX|Pre-ENTERACCS state:<br>GDTR base|Carry forward 64-bit processor state across<br>GETSEC[ENTERACCS].|
|EBP|AC.base||
|CS|Sel=[SegSel], base=0, limit=FFFFFh, G=1, D=1,<br>AR=9BH||
|DS|Sel=[SegSel] +8, base=0, limit=FFFFFh, G=1, D=1,<br>AR=93H||
|GDTR|Base= AC.base (EBX) + [GDTBasePtr],<br>Limit=[GDTLimit]||
|DR7|00000400H||
|IA32_DEBUGCTL|0H||
|IA32_MISC_ENABLE|See Table 7-5 for example.|The number of initialized fields may change due to<br>processor implementation.|
|Performance<br>counters and<br>counter control<br>registers|0H||



The segmentation related processor state that has not been initialized by GETSEC[ENTERACCS] requires appropriate initialization before use. Since a new GDT context has been established, the previous state of the segment selector values held in ES, SS, FS, GS, TR, and LDTR might not be valid.

GETSEC[ENTERACCS] — Execute Authenticated Chipset Code

7-12 Vol. 2D

SAFER MODE EXTENSIONS REFERENCE

The MSR IA32_EFER is also unconditionally cleared as part of the processor state initialized by ENTERACCS. Since paging is disabled upon entering authenticated code execution mode, a new paging environment will have to be reestablished in order to establish IA-32e mode while operating in authenticated code execution mode.

Debug exception and trap related signaling is also disabled as part of GETSEC[ENTERACCS]. This is achieved by resetting DR7, TF in EFLAGs, and the MSR IA32_DEBUGCTL. These debug functions are free to be re-enabled once supporting exception handler(s), descriptor tables, and debug registers have been properly initialized following entry into authenticated code execution mode. Also, any pending single-step trap condition will have been cleared upon entry into this mode.

Performance related counters and counter control registers are cleared as part of execution of ENTERACCS. This implies any active performance counters at any time of ENTERACCS execution will be disabled. To reactive the processor performance counters, this state must be re-initialized and re-enabled.

The IA32_MISC_ENABLE MSR is initialized upon entry into authenticated execution mode. Certain bits of this MSR are preserved because preserving these bits may be important to maintain previously established platform settings (See the footnote for Table 7-5.). The remaining bits are cleared for the purpose of establishing a more consistent environment for the execution of authenticated code modules. One of the impacts of initializing this MSR is any previous condition established by the MONITOR instruction will be cleared.

To support the possible return to the processor architectural state prior to execution of GETSEC[ENTERACCS], certain critical processor state is captured and stored in the general- purpose registers at instruction completion. [E|R]BX holds effective address ([E|R]IP) of the instruction that would execute next after GETSEC[ENTERACCS], ECX[15:0] holds the CS selector value, ECX[31:16] holds the GDTR limit field, and [E|R]DX holds the GDTR base field. The subsequent authenticated code can preserve the contents of these registers so that this state can be manually restored if needed, prior to exiting authenticated code execution mode with GETSEC[EXITAC]. For the processor state after exiting authenticated code execution mode, see the description of GETSEC[SEXIT].

Table 7-5.  IA32_MISC_ENABLE MSR Initialization<sup>1</sup> by ENTERACCS and SENTER

|Field|Bit position|Description|
|---|---|---|
|Fast strings enable|0|Clear to 0.|
|FOPCODE compatibility mode<br>enable|2|Clear to 0.|
|Thermal monitor enable|3|Set to 1 if other thermal monitor capability is not enabled.<sup>2</sup>|
|Split-lock disable|4|Clear to 0.|
|Bus lock on cache line splits<br>disable|8|Clear to 0.|
|Hardware prefetch disable|9|Clear to 0.|
|GV1/2 legacy enable|15|Clear to 0.|
|MONITOR/MWAIT s/m enable|18|Clear to 0.|
|Adjacent sector prefetch disable|19|Clear to 0.|



NOTES:

1. The number of IA32_MISC_ENABLE fields that are initialized may vary due to processor implementations.

2. ENTERACCS (and SENTER) initialize the state of processor thermal throttling such that at least a minimum level is enabled. If thermal throttling is already enabled when executing one of these GETSEC leaves, then no change in the thermal throttling control settings will occur. If thermal throttling is disabled, then it will be enabled via setting of the thermal throttle control bit 3 as a result of executing these GETSEC leaves.

The IDTR will also require reloading with a new IDT context after entering authenticated code execution mode, before any exceptions or the external interrupts INTR and NMI can be handled. Since external interrupts are reenabled at the completion of authenticated code execution mode (as terminated with EXITAC), it is recommended

GETSEC[ENTERACCS] — Execute Authenticated Chipset Code

Vol. 2D 7-13

SAFER MODE EXTENSIONS REFERENCE

that a new IDT context be established before this point. Until such a new IDT context is established, the programmer must take care in not executing an INT n instruction or any other operation that would result in an exception or trap signaling.

Prior to completion of the GETSEC[ENTERACCS] instruction and after successful authentication of the AC module, the private configuration space of the Intel TXT chipset is unlocked. The authenticated code module alone can gain access to this normally restricted chipset state for the purpose of securing the platform.

Once the authenticated code module is launched at the completion of GETSEC[ENTERACCS], it is free to enable interrupts by setting EFLAGS.IF and enable NMI by execution of IRET. This presumes that it has re-established interrupt handling support through initialization of the IDT, GDT, and corresponding interrupt handling code.

Operation in a Uni-Processor Platform (* The state of the internal flag ACMODEFLAG persists across instruction boundary *) IF (CR4.SMXE=0) THEN #UD; ELSIF (in VMX non-root operation) THEN VM Exit (reason=”GETSEC instruction”); ELSIF (GETSEC leaf unsupported) THEN #UD; ELSIF ((in VMX operation) or (CR0.PE=0) or (CR0.CD=1) or (CR0.NW=1) or (CR0.NE=0) or (CPL>0) or (EFLAGS.VM=1) or (IA32_APIC_BASE.BSP=0) or (TXT chipset not present) or (ACMODEFLAG=1) or (IN_SMM=1)) THEN #GP(0); IF (GETSEC[PARAMETERS].Parameter_Type = 5, MCA_Handling (bit 6) = 0) FOR I = 0 to IA32_MCG_CAP.COUNT-1 DO IF (IA32_MC[I]_STATUS = uncorrectable error) THEN #GP(0); OD; FI; IF (IA32_MCG_STATUS.MCIP=1) or (IERR pin is asserted) THEN #GP(0); ACBASE := EBX; ACSIZE := ECX; IF (((ACBASE MOD 4096) ≠ 0) or ((ACSIZE MOD 64 ) ≠ 0 ) or (ACSIZE < minimum module size) OR (ACSIZE > authenticated RAM capacity)) or ((ACBASE+ACSIZE) > (2^32 -1))) THEN #GP(0); IF (secondary thread(s) CR0.CD = 1) or ((secondary thread(s) NOT(wait-for-SIPI)) and (secondary thread(s) not in SENTER sleep state) THEN #GP(0); Mask SMI, INIT, A20M, and NMI external pin events; IA32_MISC_ENABLE := (IA32_MISC_ENABLE & MASK_CONST*) (* The hexadecimal value of MASK_CONST may vary due to processor implementations *) A20M := 0; IA32_DEBUGCTL := 0; Invalidate processor TLB(s); Drain Outgoing Transactions; ACMODEFLAG := 1; SignalTXTMessage(ProcessorHold); Load the internal ACRAM based on the AC module size; (* Ensure that all ACRAM loads hit Write Back memory space *) IF (ACRAM memory type ≠ WB) THEN TXT-SHUTDOWN(#BadACMMType);

GETSEC[ENTERACCS] — Execute Authenticated Chipset Code

7-14 Vol. 2D

SAFER MODE EXTENSIONS REFERENCE

IF (AC module header version isnot supported) OR (ACRAM[ModuleType] ≠ 2) THEN TXT-SHUTDOWN(#UnsupportedACM); (* Authenticate the AC Module and shutdown with an error if it fails *) KEY := GETKEY(ACRAM, ACBASE); KEYHASH := HASH(KEY); CSKEYHASH := READ(TXT.PUBLIC.KEY); IF (KEYHASH ≠ CSKEYHASH) THEN TXT-SHUTDOWN(#AuthenticateFail); SIGNATURE := DECRYPT(ACRAM, ACBASE, KEY); (* The value of SIGNATURE_LEN_CONST is implementation-specific*) FOR I=0 to SIGNATURE_LEN_CONST - 1 DO ACRAM[SCRATCH.I] := SIGNATURE[I]; COMPUTEDSIGNATURE := HASH(ACRAM, ACBASE, ACSIZE); FOR I=0 to SIGNATURE_LEN_CONST - 1 DO ACRAM[SCRATCH.SIGNATURE_LEN_CONST+I] := COMPUTEDSIGNATURE[I]; IF (SIGNATURE ≠ COMPUTEDSIGNATURE) THEN TXT-SHUTDOWN(#AuthenticateFail); ACMCONTROL := ACRAM[CodeControl]; IF ((ACMCONTROL.0 = 0) and (ACMCONTROL.1 = 1) and (snoop hit to modified line detected on ACRAM load)) THEN TXT-SHUTDOWN(#UnexpectedHITM); IF (ACMCONTROL reserved bits are set) THEN TXT-SHUTDOWN(#BadACMFormat); IF ((ACRAM[GDTBasePtr] < (ACRAM[HeaderLen] * 4 + Scratch_size)) OR ((ACRAM[GDTBasePtr] + ACRAM[GDTLimit]) >= ACSIZE)) THEN TXT-SHUTDOWN(#BadACMFormat); IF ((ACMCONTROL.0 = 1) and (ACMCONTROL.1 = 1) and (snoop hit to modified line detected on ACRAM load)) THEN ACEntryPoint := ACBASE+ACRAM[ErrorEntryPoint]; ELSE ACEntryPoint := ACBASE+ACRAM[EntryPoint];

IF ((ACEntryPoint >= ACSIZE) OR (ACEntryPoint < (ACRAM[HeaderLen] * 4 + Scratch_size)))THEN TXT-SHUTDOWN(#BadACMFormat); IF (ACRAM[GDTLimit] & FFFF0000h) THEN TXT-SHUTDOWN(#BadACMFormat); IF ((ACRAM[SegSel] > (ACRAM[GDTLimit] - 15)) OR (ACRAM[SegSel] < 8)) THEN TXT-SHUTDOWN(#BadACMFormat); IF ((ACRAM[SegSel].TI=1) OR (ACRAM[SegSel].RPL ≠ 0)) THEN TXT-SHUTDOWN(#BadACMFormat); CR0.[PG.AM.WP] := 0; CR4.MCE := 0; EFLAGS := 00000002h; IA32_EFER := 0h; [E|R]BX := [E|R]IP of the instruction after GETSEC[ENTERACCS]; ECX := Pre-GETSEC[ENTERACCS] GDT.limit:CS.sel; [E|R]DX := Pre-GETSEC[ENTERACCS] GDT.base; EBP := ACBASE; GDTR.BASE := ACBASE+ACRAM[GDTBasePtr]; GDTR.LIMIT := ACRAM[GDTLimit]; CS.SEL := ACRAM[SegSel]; CS.BASE := 0; CS.LIMIT := FFFFFh; CS.G := 1; CS.D := 1; CS.AR := 9Bh; DS.SEL := ACRAM[SegSel]+8; DS.BASE := 0;

GETSEC[ENTERACCS] — Execute Authenticated Chipset Code

Vol. 2D 7-15

SAFER MODE EXTENSIONS REFERENCE

DS.LIMIT := FFFFFh; DS.G := 1; DS.D := 1; DS.AR := 93h; DR7 := 00000400h; IA32_DEBUGCTL := 0; SignalTXTMsg(OpenPrivate); SignalTXTMsg(OpenLocality3); EIP := ACEntryPoint; END;

Flags Affected All flags are cleared.

Use of Prefixes LOCK Causes #UD. REP* Cause #UD (includes REPNE/REPNZ and REP/REPE/REPZ). Operand size Causes #UD. NP 66/F2/F3 prefixes are not allowed. Segment overrides Ignored. Address size Ignored. REX Ignored.

#### Protected Mode Exceptions

#UD If CR4.SMXE = 0. If GETSEC[ENTERACCS] is not reported as supported by GETSEC[CAPABILITIES]. #GP(0) If CR0.CD = 1 or CR0.NW = 1 or CR0.NE = 0 or CR0.PE = 0 or CPL > 0 or EFLAGS.VM = 1. If a Intel® TXT-capable chipset is not present. If in VMX root operation.

If the initiating processor is not designated as the bootstrap processor via the MSR bit IA32_APIC_BASE.BSP.

If the processor is already in authenticated code execution mode. If the processor is in SMM.

If a valid uncorrectable machine check error is logged in IA32_MC[I]_STATUS. If the authenticated code base is not on a 4096 byte boundary.

If the authenticated code size > processor internal authenticated code area capacity. If the authenticated code size is not modulo 64.

If other enabled logical processor(s) of the same package CR0.CD = 1.

If other enabled logical processor(s) of the same package are not in the wait-for-SIPI or SENTER sleep state.

#### Real-Address Mode Exceptions

#UD If CR4.SMXE = 0. If GETSEC[ENTERACCS] is not reported as supported by GETSEC[CAPABILITIES]. #GP(0) GETSEC[ENTERACCS] is not recognized in real-address mode.

GETSEC[ENTERACCS] — Execute Authenticated Chipset Code

7-16 Vol. 2D

SAFER MODE EXTENSIONS REFERENCE

#### Virtual-8086 Mode Exceptions

#UD If CR4.SMXE = 0.

If GETSEC[ENTERACCS] is not reported as supported by GETSEC[CAPABILITIES]. #GP(0) GETSEC[ENTERACCS] is not recognized in virtual-8086 mode.

#### Compatibility Mode Exceptions

All protected mode exceptions apply.

#GP IF AC code module does not reside in physical address below 2^32 -1.

#### 64-Bit Mode Exceptions

All protected mode exceptions apply. #GP IF AC code module does not reside in physical address below 2^32 -1.

VM-exit Condition

Reason (GETSEC) IF in VMX non-root operation.

GETSEC[ENTERACCS] — Execute Authenticated Chipset Code

Vol. 2D 7-17

SAFER MODE EXTENSIONS REFERENCE

## GETSEC[EXITAC]—Exit Authenticated Code Execution Mode

|Opcode|Instruction|Description|
|---|---|---|
|NP 0F 37|GETSEC[EXITAC]|Exit authenticated code execution mode.|
|(EAX=3)||RBX holds the Near Absolute Indirect jump target and EDX hold the exit parameter flags.|



#### Description

The GETSEC[EXITAC] leaf function exits the ILP out of authenticated code execution mode established by GETSEC[ENTERACCS] or GETSEC[SENTER]. The EXITAC leaf of GETSEC is selected with EAX set to 3 at entry. EBX (or RBX, if in 64-bit mode) holds the near jump target offset for where the processor execution resumes upon exiting authenticated code execution mode. EDX contains additional parameter control information. Currently only an input value of 0 in EDX is supported. All other EDX settings are considered reserved and result in a general protection violation.

GETSEC[EXITAC] can only be executed if the processor is in protected mode with CPL = 0 and EFLAGS.VM = 0. The processor must also be in authenticated code execution mode. To avoid potential operability conflicts between modes, the processor is not allowed to execute this instruction if it is in SMM or in VMX operation. A violation of these conditions results in a general protection violation.

Upon completion of the GETSEC[EXITAC] operation, the processor unmasks responses to external event signals INIT#, NMI#, and SMI#. This unmasking is performed conditionally, based on whether the authenticated code execution mode was entered via execution of GETSEC[SENTER] or GETSEC[ENTERACCS]. If the processor is in authenticated code execution mode due to the execution of GETSEC[SENTER], then these external event signals will remain masked. In this case, A20M is kept disabled in the measured environment until the measured environment executes GETSEC[SEXIT]. INIT# is unconditionally unmasked by EXITAC. Note that any events that are pending, but have been blocked while in authenticated code execution mode, will be recognized at the completion of the GETSEC[EXITAC] instruction if the pin event is unmasked.

The intent of providing the ability to optionally leave the pin events SMI#, and NMI# masked is to support the completion of a measured environment bring-up that makes use of VMX. In this envisioned security usage scenario, these events will remain masked until an appropriate virtual machine has been established in order to field servicing of these events in a safer manner. Details on when and how events are masked and unmasked in VMX operation are described in _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 3C_ . It should be cautioned that if no VMX environment is to be activated following GETSEC[EXITAC], that these events will remain masked until the measured environment is exited with GETSEC[SEXIT]. If this is not desired then the GETSEC function SMCTRL(0) can be used for unmasking SMI# in this context. NMI# can be correspondingly unmasked by execution of IRET.

A successful exit of the authenticated code execution mode requires the ILP to perform additional steps as outlined below:

- Invalidate the contents of the internal authenticated code execution area.

- Invalidate processor TLBs.

- Clear the internal processor AC Mode indicator flag.

- Re-lock the TPM locality 3 space.

- Unlock the Intel<sup>®</sup> TXT-capable chipset memory and I/O protections to allow memory and I/O activity by other processor agents.

- Perform a near absolute indirect jump to the designated instruction location.

The content of the authenticated code execution area is invalidated by hardware in order to protect it from further use or visibility. This internal processor storage area can no longer be used or relied upon after GETSEC[EXITAC]. Data structures need to be re-established outside of the authenticated code execution area if they are to be referenced after EXITAC. Since addressed memory content formerly mapped to the authenticated code execution area may no longer be coherent with external system memory after EXITAC, processor TLBs in support of linear to physical address translation are also invalidated.

GETSEC[EXITAC]—Exit Authenticated Code Execution Mode

7-18 Vol. 2D

SAFER MODE EXTENSIONS REFERENCE

Upon completion of GETSEC[EXITAC] a near absolute indirect transfer is performed with EIP loaded with the contents of EBX (based on the current operating mode size). In 64-bit mode, all 64 bits of RBX are loaded into RIP if REX.W precedes GETSEC[EXITAC]. Otherwise RBX is treated as 32 bits even while in 64-bit mode. Conventional CS limit checking is performed as part of this control transfer. Any exception conditions generated as part of this control transfer will be directed to the existing IDT; thus it is recommended that an IDTR should also be established prior to execution of the EXITAC function if there is a need for fault handling. In addition, any segmentation related (and paging) data structures to be used after EXITAC should be re-established or validated by the authenticated code prior to EXITAC.

In addition, any segmentation related (and paging) data structures to be used after EXITAC need to be re-established and mapped outside of the authenticated RAM designated area by the authenticated code prior to EXITAC. Any data structure held within the authenticated RAM allocated area will no longer be accessible after completion by EXITAC.

Operation (* The state of the internal flag ACMODEFLAG and SENTERFLAG persist across instruction boundary *) IF (CR4.SMXE=0) THEN #UD; ELSIF ( in VMX non-root operation) THEN VM Exit (reason=”GETSEC instruction”); ELSIF (GETSEC leaf unsupported) THEN #UD; ELSIF ((in VMX operation) or ( (in 64-bit mode) and ( RBX is non-canonical) ) (CR0.PE=0) or (CPL>0) or (EFLAGS.VM=1) or (ACMODEFLAG=0) or (IN_SMM=1)) or (EDX ≠ 0)) THEN #GP(0); IF (OperandSize = 32) THEN tempEIP := EBX; ELSIF (OperandSize = 64) THEN tempEIP := RBX; ELSE tempEIP := EBX AND 0000FFFFH; IF (tempEIP > code segment limit) THEN #GP(0); Invalidate ACRAM contents; Invalidate processor TLB(s); Drain outgoing messages; SignalTXTMsg(CloseLocality3); SignalTXTMsg(LockSMRAM); SignalTXTMsg(ProcessorRelease); Unmask INIT; IF (SENTERFLAG=0) THEN Unmask SMI, INIT, NMI, and A20M pin event; ELSEIF (IA32_SMM_MONITOR_CTL[0] = 0) THEN Unmask SMI pin event; ACMODEFLAG := 0; IF IA32_EFER.LMA == 1 THEN CR3 := R8; EIP := tempEIP; END; Flags Affected None.

GETSEC[EXITAC]—Exit Authenticated Code Execution Mode

Vol. 2D 7-19

SAFER MODE EXTENSIONS REFERENCE

Use of Prefixes LOCK Causes #UD. REP* Cause #UD (includes REPNE/REPNZ and REP/REPE/REPZ). Operand size Causes #UD. NP 66/F2/F3 prefixes are not allowed. Segment overrides Ignored. Address size Ignored. REX.W Sets 64-bit mode Operand size attribute.

#### Protected Mode Exceptions

#UD If CR4.SMXE = 0. If GETSEC[EXITAC] is not reported as supported by GETSEC[CAPABILITIES]. #GP(0) If CR0.PE = 0 or CPL>0 or EFLAGS.VM =1. If in VMX root operation. If the processor is not currently in authenticated code execution mode. If the processor is in SMM. If any reserved bit position is set in the EDX parameter register.

#### Real-Address Mode Exceptions

#UD If CR4.SMXE = 0. If GETSEC[EXITAC] is not reported as supported by GETSEC[CAPABILITIES]. #GP(0) GETSEC[EXITAC] is not recognized in real-address mode.

Virtual-8086 Mode Exceptions

#UD If CR4.SMXE = 0. If GETSEC[EXITAC] is not reported as supported by GETSEC[CAPABILITIES]. #GP(0) GETSEC[EXITAC] is not recognized in virtual-8086 mode.

#### Compatibility Mode Exceptions

All protected mode exceptions apply.

#### 64-Bit Mode Exceptions

All protected mode exceptions apply.

#GP(0) If the target address in RBX is not in a canonical form.

VM-Exit Condition

Reason (GETSEC) IF in VMX non-root operation.

GETSEC[EXITAC]—Exit Authenticated Code Execution Mode

7-20 Vol. 2D

SAFER MODE EXTENSIONS REFERENCE

## GETSEC[SENTER]—Enter a Measured Environment

|Opcode|Instruction|Description|
|---|---|---|
|NP 0F 37|GETSEC[SENTER]|Launch a measured environment.|
|(EAX=4)||EBX holds the SINIT authenticated code module physical base address.|
|||ECX holds the SINIT authenticated code module size (bytes).|
|||EDX controls the level of functionality supported by the measured environment launch.|



#### Description

The GETSEC[SENTER] instruction initiates the launch of a measured environment and places the initiating logical processor (ILP) into the authenticated code execution mode. The SENTER leaf of GETSEC is selected with EAX set to 4 at execution. The physical base address of the AC module to be loaded and authenticated is specified in EBX. The size of the module in bytes is specified in ECX. EDX controls the level of functionality supported by the measured environment launch. To enable the full functionality of the protected environment launch, EDX must be initialized to zero.

The authenticated code base address and size parameters (in bytes) are passed to the GETSEC[SENTER] instruction using EBX and ECX respectively. The ILP evaluates the contents of these registers according to the rules for the AC module address in GETSEC[ENTERACCS]. AC module execution follows the same rules, as set by GETSEC[ENTERACCS].

The launching software must ensure that the TPM.ACCESS_0.activeLocality bit is clear before executing the GETSEC[SENTER] instruction.

There are restrictions enforced by the processor for execution of the GETSEC[SENTER] instruction:

- Execution is not allowed unless the processor is in protected mode or IA-32e mode with CPL = 0 and EFLAGS.VM = 0.

- Processor cache must be available and not disabled using the CR0.CD and NW bits.

- For enforcing consistency of operation with numeric exception reporting using Interrupt 16, CR0.NE must be set.

- An Intel TXT-capable chipset must be present as communicated to the processor by sampling of the power-on configuration capability field after reset.

- The processor can not be in authenticated code execution mode or already in a measured environment (as launched by a previous GETSEC[ENTERACCS] or GETSEC[SENTER] instruction).

- To avoid potential operability conflicts between modes, the processor is not allowed to execute this instruction if it currently is in SMM or VMX operation.

- To ensure consistent handling of SIPI messages, the processor executing the GETSEC[SENTER] instruction must also be designated the BSP (boot-strap processor) as defined by IA32_APIC_BASE.BSP (Bit 8).

- EDX must be initialized to a setting supportable by the processor. Unless enumeration by the GETSEC[PARAMETERS] leaf reports otherwise, only a value of zero is supported.

Failure to abide by the above conditions results in the processor signaling a general protection violation.

This instruction leaf starts the launch of a measured environment by initiating a rendezvous sequence for all logical processors in the platform. The rendezvous sequence involves the initiating logical processor sending a message (by executing GETSEC[SENTER]) and other responding logical processors (RLPs) acknowledging the message, thus synchronizing the RLP(s) with the ILP.

In response to a message signaling the completion of rendezvous, RLPs clear the bootstrap processor indicator flag (IA32_APIC_BASE.BSP) and enter an SENTER sleep state. In this sleep state, RLPs enter an idle processor condition while waiting to be activated after a measured environment has been established by the system executive. RLPs in the SENTER sleep state can only be activated by the GETSEC leaf function WAKEUP in a measured environment.

GETSEC[SENTER]—Enter a Measured Environment

Vol. 2D 7-21

SAFER MODE EXTENSIONS REFERENCE

A successful launch of the measured environment results in the initiating logical processor entering the authenticated code execution mode. Prior to reaching this point, the ILP performs the following steps internally:

- Inhibit processor response to the external events: INIT, A20M, NMI, and SMI.

- Establish and check the location and size of the authenticated code module to be executed by the ILP.

- Check for the existence of an Intel<sup>®</sup> TXT-capable chipset.

- Verify the current power management configuration is acceptable.

- Broadcast a message to enable protection of memory and I/O from activities from other processor agents.

- Load the designated AC module into authenticated code execution area.

- Isolate the content of authenticated code execution area from further state modification by external agents.

- Authenticate the AC module.

- Updated the Trusted Platform Module (TPM) with the authenticated code module's hash.

- Initialize processor state based on the authenticated code module header information.

- Unlock the Intel<sup>®</sup> TXT-capable chipset private configuration register space and TPM locality 3 space.

- Begin execution in the authenticated code module at the defined entry point.

As an integrity check for proper processor hardware operation, execution of GETSEC[SENTER] will also check the contents of all the machine check status registers (as reported by the MSRs IA32_MCi_STATUS) for any valid uncorrectable error condition. In addition, the global machine check status register IA32_MCG_STATUS MCIP bit must be cleared and the IERR processor package pin (or its equivalent) must be not asserted, indicating that no machine check exception processing is currently in-progress. These checks are performed twice: once by the ILP prior to the broadcast of the rendezvous message to RLPs, and later in response to RLPs acknowledging the rendezvous message. Any outstanding valid uncorrectable machine check error condition present in the machine check status registers at the first check point will result in the ILP signaling a general protection violation. If an outstanding valid uncorrectable machine check error condition is present at the second check point, then this will result in the corresponding logical processor signaling the more severe TXT-shutdown condition with an error code of 12.

Before loading and authentication of the target code module is performed, the processor also checks that the current voltage and bus ratio encodings correspond to known good values supportable by the processor. The MSR IA32_PERF_STATUS values are compared against either the processor supported maximum operating target setting, system reset setting, or the thermal monitor operating target. If the current settings do not meet any of these criteria then the SENTER function will attempt to change the voltage and bus ratio select controls in a processor-specific manner. This adjustment may be to the thermal monitor, minimum (if different), or maximum operating target depending on the processor.

This implies that some thermal operating target parameters configured by BIOS may be overridden by SENTER. The measured environment software may need to take responsibility for restoring such settings that are deemed to be safe, but not necessarily recognized by SENTER. If an adjustment is not possible when an out of range setting is discovered, then the processor will abort the measured launch. This may be the case for chipset controlled settings of these values or if the controllability is not enabled on the processor. In this case it is the responsibility of the external software to program the chipset voltage ID and/or bus ratio select settings to known good values recognized by the processor, prior to executing SENTER.

### NOTE

For a mobile processor, an adjustment can be made according to the thermal monitor operating target. For a quad-core processor the SENTER adjustment mechanism may result in a more conservative but non-uniform voltage setting, depending on the pre-SENTER settings per core.

The ILP and RLPs mask the response to the assertion of the external signals INIT#, A20M, NMI#, and SMI#. The purpose of this masking control is to prevent exposure to existing external event handlers until a protected handler has been put in place to directly handle these events. Masked external pin events may be unmasked conditionally or unconditionally via the GETSEC[EXITAC], GETSEC[SEXIT], GETSEC[SMCTRL] or for specific VMX related operations such as a VM entry or the VMXOFF instruction (see respective GETSEC leaves and _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 3C_ for more details). The state of the A20M pin is masked and forced internally to a de-asserted state so that external assertion is not recognized. A20M masking as set by

GETSEC[SENTER]—Enter a Measured Environment

7-22 Vol. 2D

SAFER MODE EXTENSIONS REFERENCE

GETSEC[SENTER] is undone only after taking down the measured environment with the GETSEC[SEXIT] instruction or processor reset. INTR is masked by simply clearing the EFLAGS.IF bit. It is the responsibility of system software to control the processor response to INTR through appropriate management of EFLAGS.

To prevent other (logical) processors from interfering with the ILP operating in authenticated code execution mode, memory (excluding implicit write-back transactions) and I/O activities originating from other processor agents are blocked. This protection starts when the ILP enters into authenticated code execution mode. Only memory and I/O transactions initiated from the ILP are allowed to proceed. Exiting authenticated code execution mode is done by executing GETSEC[EXITAC]. The protection of memory and I/O activities remains in effect until the ILP executes GETSEC[EXITAC].

Once the authenticated code module has been loaded into the authenticated code execution area, it is protected against further modification from external bus snoops. There is also a requirement that the memory type for the authenticated code module address range be WB (via initialization of the MTRRs prior to execution of this instruction). If this condition is not satisfied, it is a violation of security and the processor will force a TXT system reset (after writing an error code to the chipset LT.ERRORCODE register). This action is referred to as a Intel® TXT reset condition. It is performed when it is considered unreliable to signal an error through the conventional exception reporting mechanism.

To conform to the minimum granularity of MTRR MSRs for specifying the memory type, authenticated code RAM (ACRAM) is allocated to the processor in 4096 byte granular blocks. If an AC module size as specified in ECX is not a multiple of 4096 then the processor will allocate up to the next 4096 byte boundary for mapping as ACRAM with indeterminate data. This pad area will not be visible to the authenticated code module as external memory nor can it depend on the value of the data used to fill the pad area.

Once successful authentication has been completed by the ILP, the computed hash is stored in a trusted storage facility in the platform. The following trusted storage facility are supported:

- If the platform register FTM_INTERFACE_ID.[bits 3:0] = 0, the computed hash is stored to the platform’s TPM at PCR17 after this register is implicitly reset. PCR17 is a dedicated register for holding the computed hash of the authenticated code module loaded and subsequently executed by the GETSEC[SENTER]. As part of this process, the dynamic PCRs 18-22 are reset so they can be utilized by subsequently software for registration of code and data modules.

- If the platform register FTM_INTERFACE_ID.[bits 3:0] = 1, the computed hash is stored in a firmware trusted module (FTM) using a modified protocol similar to the protocol used to write to TPM’s PCR17.

After successful execution of SENTER, either PCR17 (if FTM is not enabled) or the FTM (if enabled) contains the measurement of AC code and the SENTER launching parameters.

After authentication is completed successfully, the private configuration space of the Intel<sup>®</sup> TXT-capable chipset is unlocked so that the authenticated code module and measured environment software can gain access to this normally restricted chipset state. The Intel® TXT-capable chipset private configuration space can be locked later by software writing to the chipset LT.CMD.CLOSE-PRIVATE register or unconditionally using the GETSEC[SEXIT] instruction.

The SENTER leaf function also initializes some processor architecture state for the ILP from contents held in the header of the authenticated code module. Since the authenticated code module is relocatable, all address references are relative to the base address passed in via EBX. The ILP GDTR base value is initialized to EBX + [GDTBasePtr] and GDTR limit set to [GDTLimit]. The CS selector is initialized to the value held in the AC module header field SegSel, while the DS, SS, and ES selectors are initialized to CS+8. The segment descriptor fields are initialized implicitly with BASE=0, LIMIT=FFFFFh, G=1, D=1, P=1, S=1, read/write/accessed for DS, SS, and ES, while execute/read/accessed for CS. Execution in the authenticated code module for the ILP begins with the EIP set to EBX + [EntryPoint]. AC module defined fields used for initializing processor state are consistency checked with a failure resulting in an TXT-shutdown condition.

Table 7-6 provides a summary of processor state initialization for the ILP and RLP(s) after successful completion of GETSEC[SENTER]. For both ILP and RLP(s), paging is disabled upon entry to the measured environment. It is up to the ILP to establish a trusted paging environment, with appropriate mappings, to meet protection requirements established during the launch of the measured environment. RLP state initialization is not completed until a subsequent wake-up has been signaled by execution of the GETSEC[WAKEUP] function by the ILP.

GETSEC[SENTER]—Enter a Measured Environment

Vol. 2D 7-23

SAFER MODE EXTENSIONS REFERENCE

Table 7-6.  Register State Initialization after GETSEC[SENTER] and GETSEC[WAKEUP]

|Register State|ILP after GETSEC[SENTER]|RLP after GETSEC[WAKEUP]|
|---|---|---|
|CR0|PG←0, AM←0, WP←0; Others unchanged|PG←0, CD←0, NW←0, AM←0, WP←0; PE←1,NE←1|
|CR4|00004000H|00004000H|
|EFLAGS|00000002H|00000002H|
|IA32_EFER|0H|0|
|EIP|[EntryPoint from MLE header<sup>1</sup>]|[LT.MLE.JOIN + 12]|
|EBX|Unchanged [SINIT.BASE]|Unchanged|
|EDX|SENTER control flags|Unchanged|
|EBP|SINIT.BASE|Unchanged|
|CS|Sel=[SINIT SegSel], base=0, limit=FFFFFh, G=1,<br>D=1, AR=9BH|Sel = [LT.MLE.JOIN + 8], base = 0, limit = FFFFFH, G =<br>1, D = 1, AR = 9BH|
|DS, ES, SS|Sel=[SINIT SegSel] +8, base=0, limit=FFFFFh, G=1,<br>D=1, AR=93H|Sel = [LT.MLE.JOIN + 8] +8, base = 0, limit = FFFFFH,<br>G = 1, D = 1, AR = 93H|
|GDTR|Base= SINIT.base (EBX) + [SINIT.GDTBasePtr],<br>Limit=[SINIT.GDTLimit]|Base = [LT.MLE.JOIN + 4], Limit = [LT.MLE.JOIN]|
|DR7|00000400H|00000400H|
|IA32_DEBUGCTL|0H|0H|
|Performance<br>counters and counter<br>control registers|0H|0H|
|IA32_MISC_ENABLE|See Table 7-5|See Table 7-5|
|IA32_SMM_MONITOR<br>_CTL|Bit 2←0|Bit 2←0|



##### NOTES:

1. See _Intel® Trusted Execution Technology Measured Launched Environment Programming Guide_ for MLE header format.

Segmentation related processor state that has not been initialized by GETSEC[SENTER] requires appropriate initialization before use. Since a new GDT context has been established, the previous state of the segment selector values held in FS, GS, TR, and LDTR may no longer be valid. The IDTR will also require reloading with a new IDT context after launching the measured environment before exceptions or the external interrupts INTR and NMI can be handled. In the meantime, the programmer must take care in not executing an INT n instruction or any other condition that would result in an exception or trap signaling.

Debug exception and trap related signaling is also disabled as part of execution of GETSEC[SENTER]. This is achieved by clearing DR7, TF in EFLAGs, and the MSR IA32_DEBUGCTL as defined in Table 7-6. These can be reenabled once supporting exception handler(s), descriptor tables, and debug registers have been properly re-initialized following SENTER. Also, any pending single-step trap condition will be cleared at the completion of SENTER for both the ILP and RLP(s).

Performance related counters and counter control registers are cleared as part of execution of SENTER on both the ILP and RLP. This implies any active performance counters at the time of SENTER execution will be disabled. To reactive the processor performance counters, this state must be re-initialized and re-enabled.

Since MCE along with all other state bits (with the exception of SMXE) are cleared in CR4 upon execution of SENTER processing, any enabled machine check error condition that occurs will result in the processor performing the TXT-

GETSEC[SENTER]—Enter a Measured Environment

7-24 Vol. 2D

SAFER MODE EXTENSIONS REFERENCE

shutdown action. This also applies to an RLP while in the SENTER sleep state. For each logical processor CR4.MCE must be reestablished with a valid machine check exception handler to otherwise avoid an TXT-shutdown under such conditions.

The MSR IA32_EFER is also unconditionally cleared as part of the processor state initialized by SENTER for both the ILP and RLP. Since paging is disabled upon entering authenticated code execution mode, a new paging environment will have to be re-established if it is desired to enable IA-32e mode while operating in authenticated code execution mode.

The miscellaneous feature control MSR, IA32_MISC_ENABLE, is initialized as part of the measured environment launch. Certain bits of this MSR are preserved because preserving these bits may be important to maintain previously established platform settings. See the footnote for Table 7-5 The remaining bits are cleared for the purpose of establishing a more consistent environment for the execution of authenticated code modules. Among the impact of initializing this MSR, any previous condition established by the MONITOR instruction will be cleared.

##### Effect of MSR IA32_FEATURE_CONTROL MSR

Bits 15:8 of the IA32_FEATURE_CONTROL MSR affect the execution of GETSEC[SENTER]. These bits consist of two fields:

- Bit 15: a global enable control for execution of SENTER.

- Bits 14:8: a parameter control field providing the ability to qualify SENTER execution based on the level of functionality specified with corresponding EDX parameter bits 6:0.

The layout of these fields in the IA32_FEATURE_CONTROL MSR is shown in Table 7-1.

Prior to the execution of GETSEC[SENTER], the lock bit of IA32_FEATURE_CONTROL MSR must be bit set to affirm the settings to be used. Once the lock bit is set, only a power-up reset condition will clear this MSR. The IA32_FEATURE_CONTROL MSR must be configured in accordance to the intended usage at platform initialization. Note that this MSR is only available on SMX or VMX enabled processors. Otherwise, IA32_FEATURE_CONTROL is treated as reserved.

The _Intel® Trusted Execution Technology Measured Launched Environment Programming Guide_ provides additional details and requirements for programming measured environment software to launch in an Intel TXT platform.

#### Operation in a Uni-Processor Platform

(* The state of the internal flag ACMODEFLAG and SENTERFLAG persist across instruction boundary *) GETSEC[SENTER] (ILP only): IF (CR4.SMXE=0) THEN #UD; ELSE IF (in VMX non-root operation) THEN VM Exit (reason=”GETSEC instruction”); ELSE IF (GETSEC leaf unsupported) THEN #UD; ELSE IF ((in VMX root operation) or (CR0.PE=0) or (CR0.CD=1) or (CR0.NW=1) or (CR0.NE=0) or (CPL>0) or (EFLAGS.VM=1) or (IA32_APIC_BASE.BSP=0) or (TXT chipset not present) or (SENTERFLAG=1) or (ACMODEFLAG=1) or (IN_SMM=1) or (TPM interface is not present) or (EDX ≠ (SENTER_EDX_support_mask & EDX)) or (IA32_FEATURE_CONTROL[0]=0) or (IA32_FEATURE_CONTROL[15]=0) or ((IA32_FEATURE_CONTROL[14:8] & EDX[6:0]) ≠ EDX[6:0])) THEN #GP(0); IF (GETSEC[PARAMETERS].Parameter_Type = 5, MCA_Handling (bit 6) = 0) FOR I = 0 to IA32_MCG_CAP.COUNT-1 DO IF IA32_MC[I]_STATUS = uncorrectable error THEN #GP(0); FI; OD;

GETSEC[SENTER]—Enter a Measured Environment

Vol. 2D 7-25

SAFER MODE EXTENSIONS REFERENCE

FI; IF (IA32_MCG_STATUS.MCIP=1) or (IERR pin is asserted) THEN #GP(0); ACBASE := EBX; ACSIZE := ECX; IF (((ACBASE MOD 4096) ≠ 0) or ((ACSIZE MOD 64) ≠ 0 ) or (ACSIZE < minimum module size) or (ACSIZE > AC RAM capacity) or ((ACBASE+ACSIZE) > (2^32 -1))) THEN #GP(0); Mask SMI, INIT, A20M, and NMI external pin events; SignalTXTMsg(SENTER); DO WHILE (no SignalSENTER message); TXT_SENTER__MSG_EVENT (ILP & RLP): Mask and clear SignalSENTER event; Unmask SignalSEXIT event; IF (in VMX operation) THEN TXT-SHUTDOWN(#IllegalEvent); FOR I = 0 to IA32_MCG_CAP.COUNT-1 DO IF IA32_MC[I]_STATUS = uncorrectable error THEN TXT-SHUTDOWN(#UnrecovMCError); FI; OD; IF (IA32_MCG_STATUS.MCIP=1) or (IERR pin is asserted) THEN TXT-SHUTDOWN(#UnrecovMCError); IF (Voltage or bus ratio status are NOT at a known good state) THEN IF (Voltage select and bus ratio are internally adjustable) THEN Make product-specific adjustment on operating parameters; ELSE TXT-SHUTDOWN(#IIlegalVIDBRatio); FI; IA32_MISC_ENABLE := (IA32_MISC_ENABLE & MASK_CONST*) (* The hexadecimal value of MASK_CONST may vary due to processor implementations *) A20M := 0; IA32_DEBUGCTL := 0; Invalidate processor TLB(s); Drain outgoing transactions; Clear performance monitor counters and control; SENTERFLAG := 1; SignalTXTMsg(SENTERAck); IF (logical processor is not ILP) THEN GOTO RLP_SENTER_ROUTINE; (* ILP waits for all logical processors to ACK *) DO DONE := TXT.READ(LT.STS); WHILE (not DONE); SignalTXTMsg(SENTERContinue); SignalTXTMsg(ProcessorHold); FOR I=ACBASE to ACBASE+ACSIZE-1 DO ACRAM[I-ACBASE].ADDR := I; ACRAM[I-ACBASE].DATA := LOAD(I); OD;

7-26 Vol. 2D

GETSEC[SENTER]—Enter a Measured Environment

SAFER MODE EXTENSIONS REFERENCE

IF (ACRAM memory type ≠ WB) THEN TXT-SHUTDOWN(#BadACMMType); IF (AC module header version is not supported) OR (ACRAM[ModuleType] ≠ 2) THEN TXT-SHUTDOWN(#UnsupportedACM); KEY := GETKEY(ACRAM, ACBASE); KEYHASH := HASH(KEY); CSKEYHASH := LT.READ(LT.PUBLIC.KEY); IF (KEYHASH ≠ CSKEYHASH) THEN TXT-SHUTDOWN(#AuthenticateFail); SIGNATURE := DECRYPT(ACRAM, ACBASE, KEY); (* The value of SIGNATURE_LEN_CONST is implementation-specific*) FOR I=0 to SIGNATURE_LEN_CONST - 1 DO ACRAM[SCRATCH.I] := SIGNATURE[I]; COMPUTEDSIGNATURE := HASH(ACRAM, ACBASE, ACSIZE); FOR I=0 to SIGNATURE_LEN_CONST - 1 DO ACRAM[SCRATCH.SIGNATURE_LEN_CONST+I] := COMPUTEDSIGNATURE[I]; IF (SIGNATURE ≠ COMPUTEDSIGNATURE) THEN TXT-SHUTDOWN(#AuthenticateFail); ACMCONTROL := ACRAM[CodeControl]; IF ((ACMCONTROL.0 = 0) and (ACMCONTROL.1 = 1) and (snoop hit to modified line detected on ACRAM load)) THEN TXT-SHUTDOWN(#UnexpectedHITM); IF (ACMCONTROL reserved bits are set) THEN TXT-SHUTDOWN(#BadACMFormat); IF ((ACRAM[GDTBasePtr] < (ACRAM[HeaderLen] * 4 + Scratch_size)) OR ((ACRAM[GDTBasePtr] + ACRAM[GDTLimit]) >= ACSIZE)) THEN TXT-SHUTDOWN(#BadACMFormat); IF ((ACMCONTROL.0 = 1) and (ACMCONTROL.1 = 1) and (snoop hit to modified line detected on ACRAM load)) THEN ACEntryPoint := ACBASE+ACRAM[ErrorEntryPoint]; ELSE ACEntryPoint := ACBASE+ACRAM[EntryPoint]; IF ((ACEntryPoint >= ACSIZE) or (ACEntryPoint < (ACRAM[HeaderLen] * 4 + Scratch_size))) THEN TXT-SHUTDOWN(#BadACMFormat); IF ((ACRAM[SegSel] > (ACRAM[GDTLimit] - 15)) or (ACRAM[SegSel] < 8)) THEN TXT-SHUTDOWN(#BadACMFormat); IF ((ACRAM[SegSel].TI=1) or (ACRAM[SegSel].RPL ≠ 0)) THEN TXT-SHUTDOWN(#BadACMFormat);

IF (FTM_INTERFACE_ID.[3:0] = 1 ) (* Alternate FTM Interface has been enabled *) THEN (* TPM_LOC_CTRL_4 is located at 0FED44008H, TMP_DATA_BUFFER_4 is located at 0FED44080H *) WRITE(TPM_LOC_CTRL_4) := 01H; (* Modified HASH.START protocol *) (* Write to firmware storage *) WRITE(TPM_DATA_BUFFER_4) := SIGNATURE_LEN_CONST + 4; FOR I=0 to SIGNATURE_LEN_CONST - 1 DO WRITE(TPM_DATA_BUFFER_4 + 2 + I ) := ACRAM[SCRATCH.I]; WRITE(TPM_DATA_BUFFER_4 + 2 + SIGNATURE_LEN_CONST) := EDX; WRITE(FTM.LOC_CTRL) := 06H; (* Modified protocol combining HASH.DATA and HASH.END *) ELSE IF (FTM_INTERFACE_ID.[3:0] = 0 ) (* Use standard TPM Interface *) ACRAM[SCRATCH.SIGNATURE_LEN_CONST] := EDX; WRITE(TPM.HASH.START) := 0; FOR I=0 to SIGNATURE_LEN_CONST + 3 DO WRITE(TPM.HASH.DATA) := ACRAM[SCRATCH.I]; WRITE(TPM.HASH.END) := 0;

FI;

GETSEC[SENTER]—Enter a Measured Environment

Vol. 2D 7-27

SAFER MODE EXTENSIONS REFERENCE

ACMODEFLAG := 1; CR0.[PG.AM.WP] := 0; CR4 := 00004000h; EFLAGS := 00000002h; IA32_EFER := 0; EBP := ACBASE; GDTR.BASE := ACBASE+ACRAM[GDTBasePtr]; GDTR.LIMIT := ACRAM[GDTLimit]; CS.SEL := ACRAM[SegSel]; CS.BASE := 0; CS.LIMIT := FFFFFh; CS.G := 1; CS.D := 1; CS.AR := 9Bh; DS.SEL := ACRAM[SegSel]+8; DS.BASE := 0; DS.LIMIT := FFFFFh; DS.G := 1; DS.D := 1; DS.AR := 93h; SS := DS; ES := DS; DR7 := 00000400h; IA32_DEBUGCTL := 0; SignalTXTMsg(UnlockSMRAM); SignalTXTMsg(OpenPrivate); SignalTXTMsg(OpenLocality3); EIP := ACEntryPoint; END;

RLP_SENTER_ROUTINE: (RLP only) Mask SMI, INIT, A20M, and NMI external pin events Unmask SignalWAKEUP event; Wait for SignalSENTERContinue message; IA32_APIC_BASE.BSP := 0; GOTO SENTER sleep state; END;

Flags Affected All flags are cleared.

Use of Prefixes

LOCK Causes #UD. REP* Cause #UD (includes REPNE/REPNZ and REP/REPE/REPZ). Operand size Causes #UD. NP 66/F2/F3 prefixes are not allowed. Segment overrides Ignored. Address size Ignored. REX Ignored.

GETSEC[SENTER]—Enter a Measured Environment

7-28 Vol. 2D

SAFER MODE EXTENSIONS REFERENCE

#### Protected Mode Exceptions

#UD If CR4.SMXE = 0. If GETSEC[SENTER] is not reported as supported by GETSEC[CAPABILITIES]. #GP(0) If CR0.CD = 1 or CR0.NW = 1 or CR0.NE = 0 or CR0.PE = 0 or CPL > 0 or EFLAGS.VM = 1. If in VMX root operation.

- If the initiating processor is not designated as the bootstrap processor via the MSR bit IA32_APIC_BASE.BSP.

If an Intel<sup>®</sup> TXT-capable chipset is not present.

If an Intel<sup>®</sup> TXT-capable chipset interface to TPM is not detected as present.

- If a protected partition is already active or the processor is already in authenticated code mode.

If the processor is in SMM.

If a valid uncorrectable machine check error is logged in IA32_MC[I]_STATUS.

If the authenticated code base is not on a 4096 byte boundary.

If the authenticated code size > processor's authenticated code execution area storage capacity.

If the authenticated code size is not modulo 64.

#### Real-Address Mode Exceptions

#UD If CR4.SMXE = 0.

If GETSEC[SENTER] is not reported as supported by GETSEC[CAPABILITIES]. #GP(0) GETSEC[SENTER] is not recognized in real-address mode.

#### Virtual-8086 Mode Exceptions

#UD If CR4.SMXE = 0.

If GETSEC[SENTER] is not reported as supported by GETSEC[CAPABILITIES]. #GP(0) GETSEC[SENTER] is not recognized in virtual-8086 mode.

#### Compatibility Mode Exceptions

All protected mode exceptions apply.

#GP IF AC code module does not reside in physical address below 2^32 -1.

#### 64-Bit Mode Exceptions

All protected mode exceptions apply.

#GP IF AC code module does not reside in physical address below 2^32 -1.

VM-Exit Condition

Reason (GETSEC) IF in VMX non-root operation.

GETSEC[SENTER]—Enter a Measured Environment

Vol. 2D 7-29

SAFER MODE EXTENSIONS REFERENCE

## GETSEC[SEXIT]—Exit Measured Environment

|Opcode|Instruction|Description|
|---|---|---|
|NP 0F 37|GETSEC[SEXIT]|Exit measured environment.|
|(EAX=5)|||



#### Description

The GETSEC[SEXIT] instruction initiates an exit of a measured environment established by GETSEC[SENTER]. The SEXIT leaf of GETSEC is selected with EAX set to 5 at execution. This instruction leaf sends a message to all logical processors in the platform to signal the measured environment exit.

There are restrictions enforced by the processor for the execution of the GETSEC[SEXIT] instruction:

- Execution is not allowed unless the processor is in protected mode (CR0.PE = 1) with CPL = 0 and EFLAGS.VM = 0.

- The processor must be in a measured environment as launched by a previous GETSEC[SENTER] instruction, but not still in authenticated code execution mode.

- To avoid potential inter-operability conflicts between modes, the processor is not allowed to execute this instruction if it currently is in SMM or in VMX operation.

- To ensure consistent handling of SIPI messages, the processor executing the GETSEC[SEXIT] instruction must also be designated the BSP (bootstrap processor) as defined by the register bit IA32_APIC_BASE.BSP (bit 8).

Failure to abide by the above conditions results in the processor signaling a general protection violation.

This instruction initiates a sequence to rendezvous the RLPs with the ILP. It then clears the internal processor flag indicating the processor is operating in a measured environment.

In response to a message signaling the completion of rendezvous, all RLPs restart execution with the instruction that was to be executed at the time GETSEC[SEXIT] was recognized. This applies to all processor conditions, with the following exceptions:

- If an RLP executed HLT and was in this halt state at the time of the message initiated by GETSEC[SEXIT], then execution resumes in the halt state.

- If an RLP was executing MWAIT, then a message initiated by GETSEC[SEXIT] causes an exit of the MWAIT state, falling through to the next instruction.

- If an RLP was executing an intermediate iteration of a string instruction, then the processor resumes execution of the string instruction at the point which the message initiated by GETSEC[SEXIT] was recognized.

- If an RLP is still in the SENTER sleep state (never awakened with GETSEC[WAKEUP]), it will be sent to the waitfor-SIPI state after first clearing the bootstrap processor indicator flag (IA32_APIC_BASE.BSP) and any pending SIPI state. In this case, such RLPs are initialized to an architectural state consistent with having taken a soft reset using the INIT# pin.

Prior to completion of the GETSEC[SEXIT] operation, both the ILP and any active RLPs unmask the response of the external event signals INIT#, A20M, NMI#, and SMI#. This unmasking is performed unconditionally to recognize pin events which are masked after a GETSEC[SENTER]. The state of A20M is unmasked, as the A20M pin is not recognized while the measured environment is active.

On a successful exit of the measured environment, the ILP re-locks the Intel® TXT-capable chipset private configuration space. GETSEC[SEXIT] does not affect the content of any PCR.

At completion of GETSEC[SEXIT] by the ILP, execution proceeds to the next instruction. Since EFLAGS and the debug register state are not modified by this instruction, a pending trap condition is free to be signaled if previously enabled.

GETSEC[SEXIT]—Exit Measured Environment

7-30 Vol. 2D

SAFER MODE EXTENSIONS REFERENCE

Operation in a Uni-Processor Platform

(* The state of the internal flag ACMODEFLAG and SENTERFLAG persist across instruction boundary *)

GETSEC[SEXIT] (ILP only): IF (CR4.SMXE=0) THEN #UD; ELSE IF (in VMX non-root operation) THEN VM Exit (reason=”GETSEC instruction”); ELSE IF (GETSEC leaf unsupported) THEN #UD; ELSE IF ((in VMX root operation) or (CR0.PE=0) or (CPL>0) or (EFLAGS.VM=1) or (IA32_APIC_BASE.BSP=0) or (TXT chipset not present) or (SENTERFLAG=0) or (ACMODEFLAG=1) or (IN_SMM=1)) THEN #GP(0); SignalTXTMsg(SEXIT); DO WHILE (no SignalSEXIT message);

TXT_SEXIT_MSG_EVENT (ILP & RLP): Mask and clear SignalSEXIT event; Clear MONITOR FSM; Unmask SignalSENTER event; IF (in VMX operation) THEN TXT-SHUTDOWN(#IllegalEvent); SignalTXTMsg(SEXITAck); IF (logical processor is not ILP) THEN GOTO RLP_SEXIT_ROUTINE; (* ILP waits for all logical processors to ACK *) DO DONE := READ(LT.STS); WHILE (NOT DONE); SignalTXTMsg(SEXITContinue); SignalTXTMsg(ClosePrivate); SENTERFLAG := 0; Unmask SMI, INIT, A20M, and NMI external pin events; END;

RLP_SEXIT_ROUTINE (RLPs only): Wait for SignalSEXITContinue message; Unmask SMI, INIT, A20M, and NMI external pin events; IF (prior execution state = HLT) THEN reenter HLT state; IF (prior execution state = SENTER sleep) THEN IA32_APIC_BASE.BSP := 0; Clear pending SIPI state; Call INIT_PROCESSOR_STATE; Unmask SIPI event; GOTO WAIT-FOR-SIPI; FI; END;

GETSEC[SEXIT]—Exit Measured Environment

Vol. 2D 7-31

SAFER MODE EXTENSIONS REFERENCE

#### Flags Affected

ILP: None.

RLPs: all flags are modified for an RLP. returning to wait-for-SIPI state, none otherwise.

Use of Prefixes LOCK Causes #UD. REP* Cause #UD (includes REPNE/REPNZ and REP/REPE/REPZ). Operand size Causes #UD. NP 66/F2/F3 prefixes are not allowed. Segment overrides Ignored. Address size Ignored. REX Ignored.

Protected Mode Exceptions #UD If CR4.SMXE = 0. If GETSEC[SEXIT] is not reported as supported by GETSEC[CAPABILITIES]. #GP(0) If CR0.PE = 0 or CPL > 0 or EFLAGS.VM = 1. If in VMX root operation. If the initiating processor is not designated via the MSR bit IA32_APIC_BASE.BSP. If an Intel<sup>®</sup> TXT-capable chipset is not present. If a protected partition is not already active or the processor is already in authenticated code mode. If the processor is in SMM.

#### Real-Address Mode Exceptions

#UD If CR4.SMXE = 0. If GETSEC[SEXIT] is not reported as supported by GETSEC[CAPABILITIES]. #GP(0) GETSEC[SEXIT] is not recognized in real-address mode. Virtual-8086 Mode Exceptions #UD If CR4.SMXE = 0. If GETSEC[SEXIT] is not reported as supported by GETSEC[CAPABILITIES]. #GP(0) GETSEC[SEXIT] is not recognized in virtual-8086 mode.

#### Compatibility Mode Exceptions

All protected mode exceptions apply.

#### 64-Bit Mode Exceptions

All protected mode exceptions apply.

VM-Exit Condition

Reason (GETSEC) IF in VMX non-root operation.

GETSEC[SEXIT]—Exit Measured Environment

7-32 Vol. 2D

SAFER MODE EXTENSIONS REFERENCE

## GETSEC[PARAMETERS]—Report the SMX Parameters

|Opcode|Instruction|Description|
|---|---|---|
|NP 0F 37|GETSEC[PARAMETERS]|Report the SMX parameters.|
|(EAX=6)||The parameters index is input in EBX with the result returned in EAX, EBX, and ECX.|



#### Description

The GETSEC[PARAMETERS] instruction returns specific parameter information for SMX features supported by the processor. Parameter information is returned in EAX, EBX, and ECX, with the input parameter selected using EBX.

Software retrieves parameter information by searching with an input index for EBX starting at 0, and then reading the returned results in EAX, EBX, and ECX. EAX[4:0] is designated to return a parameter type field indicating if a parameter is available and what type it is. If EAX[4:0] is returned with 0, this designates a null parameter and indicates no more parameters are available.

Table 7-7 defines the parameter types supported in current and future implementations.

Table 7-7.  SMX Reporting Parameters Format

|Parameter<br>Type EAX[4:0]|Parameter Description|EAX[31:5]|EBX[31:0]|ECX[31:0]|
|---|---|---|---|---|
|0|NULL|Reserved (0 returned)|Reserved (unmodified)|Reserved (unmodified)|
|1|Supported AC module<br>versions|Reserved (0 returned)|Version comparison mask|Version numbers<br>supported|
|2|Max size of authenticated<br>code execution area|Multiply by 32 for size in<br>bytes|Reserved (unmodified)|Reserved (unmodified)|
|3|External memory types<br>supported during AC mode|Memory type bit mask|Reserved (unmodified)|Reserved (unmodified)|
|4|Selective SENTER<br>functionality control|EAX[14:8] correspond to<br>available SENTER function<br>disable controls|Reserved (unmodified)|Reserved (unmodified)|
|5|TXT extensions support|TXT Feature Extensions<br>Flags (see Table 7-8)|Reserved|Reserved|
|6-31|Undefined|Reserved (unmodified)|Reserved (unmodified)|Reserved (unmodified)|



GETSEC[PARAMETERS]—Report the SMX Parameters

Vol. 2D 7-33

SAFER MODE EXTENSIONS REFERENCE

Table 7-8.  TXT Feature Extensions Flags

|Bit|Definition|Description|
|---|---|---|
|5|Processor based<br>S-CRTM support|Returns 1 if this processor implements a processor-rooted S-CRTM capability and 0 if not (S-<br>CRTM is rooted in BIOS).<br>This flag cannot be used to infer whether the chipset supports TXT or whether the<br>processor support SMX.|
|6|Machine Check<br>Handling|Returns 1 if it machine check status registers can be preserved through ENTERACCS and<br>SENTER. If this bit is 1, the caller of ENTERACCS and SENTER is not required to clear machine<br>check error status bits before invoking these GETSEC leaves.<br>If this bit returns 0, the caller of ENTERACCS and SENTER must clear all machine check error<br>status bits before invoking these GETSEC leaves.|
|31:7|Reserved|Reserved for future use. Will return 0.|



Supported AC module versions (as defined by the AC module HeaderVersion field) can be determined for a particular SMX capable processor by the type 1 parameter. Using EBX to index through the available parameters reported by GETSEC[PARAMETERS] for each unique parameter set returned for type 1, software can determine the complete list of AC module version(s) supported.

For each parameter set, EBX returns the comparison mask and ECX returns the available HeaderVersion field values supported, after AND'ing the target HeaderVersion with the comparison mask. Software can then determine if a particular AC module version is supported by following the pseudo-code search routine given below:

parameter_search_index= 0

do {

EBX= parameter_search_index++ EAX= 6 GETSEC if (EAX[4:0] = 1) { if ((version_query & EBX) = ECX) { version_is_supported= 1 break } }

} while (EAX[4:0] ≠ 0)

If only AC modules with a HeaderVersion of 0 are supported by the processor, then only one parameter set of type 1 will be returned, as follows: EAX = 00000001H,

EBX = FFFFFFFFH and ECX = 00000000H.

The maximum capacity for an authenticated code execution area supported by the processor is reported with the parameter type of 2. The maximum supported size in bytes is determined by multiplying the returned size in EAX[31:5] by 32. Thus, for a maximum supported authenticated RAM size of 32KBytes, EAX returns with 00008002H.

Supportable memory types for memory mapped outside of the authenticated code execution area are reported with the parameter type of 3. While is active, as initiated by the GETSEC functions SENTER and ENTERACCS and terminated by EXITAC, there are restrictions on what memory types are allowed for the rest of system memory. It is the responsibility of the system software to initialize the memory type range register (MTRR) MSRs and/or the page attribute table (PAT) to only map memory types consistent with the reporting of this parameter. The reporting of supportable memory types of external memory is indicated using a bit map returned in EAX[31:8]. These bit positions correspond to the memory type encodings defined for the MTRR MSR and PAT programming. See Table 7-9.

The parameter type of 4 is used for enumerating the availability of selective GETSEC[SENTER] function disable controls. If a 1 is reported in bits 14:8 of the returned parameter EAX, then this indicates a disable control capa-

7-34 Vol. 2D

GETSEC[PARAMETERS]—Report the SMX Parameters

SAFER MODE EXTENSIONS REFERENCE

bility exists with SENTER for a particular function. The enumerated field in bits 14:8 corresponds to use of the EDX input parameter bits 6:0 for SENTER. If an enumerated field bit is set to 1, then the corresponding EDX input parameter bit of EDX may be set to 1 to disable that designated function. If the enumerated field bit is 0 or this parameter is not reported, then no disable capability exists with the corresponding EDX input parameter for SENTER, and EDX bit(s) must be cleared to 0 to enable execution of SENTER. If no selective disable capability for SENTER exists as enumerated, then the corresponding bits in the IA32_FEATURE_CONTROL MSR bits 14:8 must also be programmed to 1 if the SENTER global enable bit 15 of the MSR is set. This is required to enable future extensibility of SENTER selective disable capability with respect to potentially separate software initialization of the MSR.

Table 7-9.  External Memory Types Using Parameter 3

|EAX Bit Position|Parameter Description|
|---|---|
|8|Uncacheable (UC)|
|9|Write Combining (WC)|
|11:10|Reserved|
|12|Write-through (WT)|
|13|Write-protected (WP)|
|14|Write-back (WB)|
|31:15|Reserved|



If the GETSEC[PARAMETERS] leaf or specific parameter is not present for a given SMX capable processor, then default parameter values should be assumed. These are defined in Table 7-10.

Table 7-10.  Default Parameter Values

|Parameter Type EAX[4:0]|Default Setting|Parameter Description|
|---|---|---|
|1|0.0 only|Supported AC module versions.|
|2|32 KBytes|Authenticated code execution area size.|
|3|UC only|External memory types supported during AC execution mode.|
|4|None|Available SENTER selective disable controls.|



#### Operation

(* example of a processor supporting only a 0.0 HeaderVersion, 32K ACRAM size, memory types UC and WC *) IF (CR4.SMXE=0)

THEN #UD;

ELSE IF (in VMX non-root operation)

THEN VM Exit (reason=”GETSEC instruction”);

ELSE IF (GETSEC leaf unsupported) THEN #UD;

(* example of a processor supporting a 0.0 HeaderVersion *)

IF (EBX=0) THEN EAX := 00000001h; EBX := FFFFFFFFh; ECX := 00000000h;

ELSE IF (EBX=1)

(* example of a processor supporting a 32K ACRAM size *)

GETSEC[PARAMETERS]—Report the SMX Parameters

Vol. 2D 7-35

SAFER MODE EXTENSIONS REFERENCE

THEN EAX := 00008002h; ESE IF (EBX= 2) (* example of a processor supporting external memory types of UC and WC *) THEN EAX := 00000303h; ESE IF (EBX= other value(s) less than unsupported index value) (* EAX value varies. Consult Table 7-7 and Table 7-8*) ELSE (* unsupported index*) EAX := 00000000h; END;

Flags Affected

None.

Use of Prefixes LOCK Causes #UD. REP* Cause #UD (includes REPNE/REPNZ and REP/REPE/REPZ). Operand size Causes #UD. NP 66/F2/F3 prefixes are not allowed. Segment overrides Ignored. Address size Ignored. REX Ignored.

Protected Mode Exceptions #UD If CR4.SMXE = 0. If GETSEC[PARAMETERS] is not reported as supported by GETSEC[CAPABILITIES].

Real-Address Mode Exceptions

#UD If CR4.SMXE = 0. If GETSEC[PARAMETERS] is not reported as supported by GETSEC[CAPABILITIES].

Virtual-8086 Mode Exceptions

#UD If CR4.SMXE = 0. If GETSEC[PARAMETERS] is not reported as supported by GETSEC[CAPABILITIES].

Compatibility Mode Exceptions

All protected mode exceptions apply.

#### 64-Bit Mode Exceptions

All protected mode exceptions apply.

VM-Exit Condition Reason (GETSEC) IF in VMX non-root operation.

7-36 Vol. 2D

GETSEC[PARAMETERS]—Report the SMX Parameters

SAFER MODE EXTENSIONS REFERENCE

## GETSEC[SMCTRL]—SMX Mode Control

|Opcode|Instruction|Description|
|---|---|---|
|NP 0F 37 (EAX = 7)|GETSEC[SMCTRL]|Perform specified SMX mode control as selected with the input EBX.|



#### Description

The GETSEC[SMCTRL] instruction is available for performing certain SMX specific mode control operations. The operation to be performed is selected through the input register EBX. Currently only an input value in EBX of 0 is supported. All other EBX settings will result in the signaling of a general protection violation.

If EBX is set to 0, then the SMCTRL leaf is used to re-enable SMI events. SMI is masked by the ILP executing the GETSEC[SENTER] instruction (SMI is also masked in the responding logical processors in response to SENTER rendezvous messages.). The determination of when this instruction is allowed and the events that are unmasked is dependent on the processor context (See Table 7-11). For brevity, the usage of SMCTRL where EBX=0 will be referred to as GETSEC[SMCTRL(0)].

As part of support for launching a measured environment, the SMI, NMI, and INIT events are masked after GETSEC[SENTER], and remain masked after exiting authenticated execution mode. Unmasking these events should be accompanied by securely enabling these event handlers. These security concerns can be addressed in VMX operation by a MVMM.

The VM monitor can choose two approaches:

- In a dual monitor approach, the executive software will set up an SMM monitor in parallel to the executive VMM (i.e., the MVMM), see Chapter 32, “System Management Mode” of _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 3C_ . The SMM monitor is dedicated to handling SMI events without compromising the security of the MVMM. This usage model of handling SMI while a measured environment is active does not require the use of GETSEC[SMCTRL(0)] as event re-enabling after the VMX environment launch is handled implicitly and through separate VMX based controls.

- If a dedicated SMM monitor will not be established and SMIs are to be handled within the measured environment, then GETSEC[SMCTRL(0)] can be used by the executive software to re-enable SMI that has been masked as a result of SENTER.

Table 7-11 defines the processor context in which GETSEC[SMCTRL(0)] can be used and which events will be unmasked. Note that the events that are unmasked are dependent upon the currently operating processor context.

Table 7-11.  Supported Actions for GETSEC[SMCTRL(0)]

|ILP Mode of Operation|SMCTRL execution action|
|---|---|
|In VMX non-root operation|VM exit|
|SENTERFLAG = 0|#GP(0), illegal context|
|In authenticated code execution mode<br>(ACMODEFLAG = 1)|#GP(0), illegal context|
|SENTERFLAG = 1, not in VMX operation, not in<br>SMM|Unmask SMI|
|SENTERFLAG = 1, in VMX root operation, not in<br>SMM|Unmask SMI if SMM monitor is not configured, otherwise #GP(0)|
|SENTERFLAG = 1, In VMX root operation, in SMM|#GP(0), illegal context|



GETSEC[SMCTRL]—SMX Mode Control

Vol. 2D 7-37

SAFER MODE EXTENSIONS REFERENCE

#### Operation

(* The state of the internal flag ACMODEFLAG and SENTERFLAG persist across instruction boundary *) IF (CR4.SMXE=0) THEN #UD; ELSE IF (in VMX non-root operation) THEN VM Exit (reason=”GETSEC instruction”); ELSE IF (GETSEC leaf unsupported) THEN #UD; ELSE IF ((CR0.PE=0) or (CPL>0) OR (EFLAGS.VM=1)) THEN #GP(0); ELSE IF((EBX=0) and (SENTERFLAG=1) and (ACMODEFLAG=0) and (IN_SMM=0) and (((in VMX root operation) and (SMM monitor not configured)) or (not in VMX operation)) ) THEN unmask SMI; ELSE #GP(0); END Flags Affected None.

Use of Prefixes LOCK Causes #UD. REP* Cause #UD (includes REPNE/REPNZ and REP/REPE/REPZ). Operand size Causes #UD. NP 66/F2/F3 prefixes are not allowed. Segment overrides Ignored. Address size Ignored. REX Ignored. Protected Mode Exceptions #UD If CR4.SMXE = 0. If GETSEC[SMCTRL] is not reported as supported by GETSEC[CAPABILITIES]. #GP(0) If CR0.PE = 0 or CPL > 0 or EFLAGS.VM = 1. If in VMX root operation. If a protected partition is not already active or the processor is currently in authenticated code mode. If the processor is in SMM. If the SMM monitor is not configured.

Real-Address Mode Exceptions #UD If CR4.SMXE = 0. If GETSEC[SMCTRL] is not reported as supported by GETSEC[CAPABILITIES]. #GP(0) GETSEC[SMCTRL] is not recognized in real-address mode. Virtual-8086 Mode Exceptions #UD If CR4.SMXE = 0. If GETSEC[SMCTRL] is not reported as supported by GETSEC[CAPABILITIES]. #GP(0) GETSEC[SMCTRL] is not recognized in virtual-8086 mode.

7-38 Vol. 2D

GETSEC[SMCTRL]—SMX Mode Control

SAFER MODE EXTENSIONS REFERENCE

Compatibility Mode Exceptions All protected mode exceptions apply.

64-Bit Mode Exceptions All protected mode exceptions apply.

VM-exit Condition Reason (GETSEC) IF in VMX non-root operation.

GETSEC[SMCTRL]—SMX Mode Control

Vol. 2D 7-39

SAFER MODE EXTENSIONS REFERENCE

## GETSEC[WAKEUP]—Wake up sleeping processors in measured environment

|Opcode|Instruction|Description|
|---|---|---|
|NP 0F 37<br>(EAX=8)|GETSEC[WAKEUP]|Wake up the responding logical processors from the SENTER sleep state.|



#### Description

The GETSEC[WAKEUP] leaf function broadcasts a wake-up message to all logical processors currently in the SENTER sleep state. This GETSEC leaf must be executed only by the ILP, in order to wake-up the RLPs. Responding logical processors (RLPs) enter the SENTER sleep state after completion of the SENTER rendezvous sequence.

The GETSEC[WAKEUP] instruction may only be executed:

- In a measured environment as initiated by execution of GETSEC[SENTER].

- Outside of authenticated code execution mode.

- Execution is not allowed unless the processor is in protected mode with CPL = 0 and EFLAGS.VM = 0.

- In addition, the logical processor must be designated as the boot-strap processor as configured by setting IA32_APIC_BASE.BSP = 1.

If these conditions are not met, attempts to execute GETSEC[WAKEUP] result in a general protection violation.

An RLP exits the SENTER sleep state and start execution in response to a WAKEUP signal initiated by ILP’s execution of GETSEC[WAKEUP]. The RLP retrieves a pointer to a data structure that contains information to enable execution from a defined entry point. This data structure is located using a physical address held in the Intel<sup>®</sup> TXT-capable chipset configuration register LT.MLE.JOIN. The register is publicly writable in the chipset by all processors and is not restricted by the Intel<sup>®</sup> TXT-capable chipset configuration register lock status. The format of this data structure is defined in Table 7-12.

Table 7-12.  RLP MVMM JOIN Data Structure

|Offset|Field|
|---|---|
|0|GDT limit|
|4|GDT base pointer|
|8|Segment selector initializer|
|12|EIP|



The MLE JOIN data structure contains the information necessary to initialize RLP processor state and permit the processor to join the measured environment. The GDTR, LIP, and CS, DS, SS, and ES selector values are initialized using this data structure. The CS selector index is derived directly from the segment selector initializer field; DS, SS, and ES selectors are initialized to CS+8. The segment descriptor fields are initialized implicitly with BASE = 0, LIMIT = FFFFFH, G = 1, D = 1, P = 1, S = 1; read/write/access for DS, SS, and ES; and execute/read/access for CS. It is the responsibility of external software to establish a GDT pointed to by the MLE JOIN data structure that contains descriptor entries consistent with the implicit settings initialized by the processor (see Table 7-6). Certain states from the content of Table 7-12 are checked for consistency by the processor prior to execution. A failure of any consistency check results in the RLP aborting entry into the protected environment and signaling an Intel® TXT shutdown condition. The specific checks performed are documented later in this section. After successful completion of processor consistency checks and subsequent initialization, RLP execution in the measured environment begins from the entry point at offset 12 (as indicated in Table 7-12).

GETSEC[WAKEUP]—Wake up sleeping processors in measured environment

7-40 Vol. 2D

SAFER MODE EXTENSIONS REFERENCE

Operation (* The state of the internal flag ACMODEFLAG and SENTERFLAG persist across instruction boundary *) IF (CR4.SMXE=0) THEN #UD; ELSE IF (in VMX non-root operation) THEN VM Exit (reason=”GETSEC instruction”); ELSE IF (GETSEC leaf unsupported) THEN #UD; ELSE IF ((CR0.PE=0) or (CPL>0) or (EFLAGS.VM=1) or (SENTERFLAG=0) or (ACMODEFLAG=1) or (IN_SMM=0) or (in VMX operation) or (IA32_APIC_BASE.BSP=0) or (TXT chipset not present)) THEN #GP(0); ELSE SignalTXTMsg(WAKEUP); END;

RLP_SIPI_WAKEUP_FROM_SENTER_ROUTINE: (RLP only) WHILE (no SignalWAKEUP event); IF (IA32_SMM_MONITOR_CTL[0] ≠ ILP.IA32_SMM_MONITOR_CTL[0]) THEN TXT-SHUTDOWN(#IllegalEvent) IF (IA32_SMM_MONITOR_CTL[0] = 0) THEN Unmask SMI pin event; ELSE Mask SMI pin event; Mask A20M, and NMI external pin events (unmask INIT); Mask SignalWAKEUP event; Invalidate processor TLB(s); Drain outgoing transactions; TempGDTRLIMIT := LOAD(LT.MLE.JOIN); TempGDTRBASE := LOAD(LT.MLE.JOIN+4); TempSegSel := LOAD(LT.MLE.JOIN+8); TempEIP := LOAD(LT.MLE.JOIN+12); IF (TempGDTLimit & FFFF0000h) THEN TXT-SHUTDOWN(#BadJOINFormat); IF ((TempSegSel > TempGDTRLIMIT-15) or (TempSegSel < 8)) THEN TXT-SHUTDOWN(#BadJOINFormat); IF ((TempSegSel.TI=1) or (TempSegSel.RPL ≠ 0)) THEN TXT-SHUTDOWN(#BadJOINFormat); CR0.[PG,CD,NW,AM,WP] := 0; CR0.[NE,PE] := 1; CR4 := 00004000h; EFLAGS := 00000002h; IA32_EFER := 0; GDTR.BASE := TempGDTRBASE; GDTR.LIMIT := TempGDTRLIMIT; CS.SEL := TempSegSel; CS.BASE := 0; CS.LIMIT := FFFFFh; CS.G := 1; CS.D := 1; CS.AR := 9Bh; DS.SEL := TempSegSel+8; DS.BASE := 0; DS.LIMIT := FFFFFh; DS.G := 1;

GETSEC[WAKEUP]—Wake up sleeping processors in measured environment

Vol. 2D 7-41

SAFER MODE EXTENSIONS REFERENCE

DS.D := 1; DS.AR := 93h; SS := DS; ES := DS; DR7 := 00000400h; IA32_DEBUGCTL := 0; EIP := TempEIP; END; Flags Affected None. Use of Prefixes LOCK Causes #UD. REP* Cause #UD (includes REPNE/REPNZ and REP/REPE/REPZ). Operand size Causes #UD. NP 66/F2/F3 prefixes are not allowed. Segment overrides Ignored. Address size Ignored. REX Ignored. Protected Mode Exceptions #UD If CR4.SMXE = 0. If GETSEC[WAKEUP] is not reported as supported by GETSEC[CAPABILITIES]. #GP(0) If CR0.PE = 0 or CPL > 0 or EFLAGS.VM = 1. If in VMX operation. If a protected partition is not already active or the processor is currently in authenticated code mode. If the processor is in SMM. #UD If CR4.SMXE = 0. If GETSEC[WAKEUP] is not reported as supported by GETSEC[CAPABILITIES]. #GP(0) GETSEC[WAKEUP] is not recognized in real-address mode. Virtual-8086 Mode Exceptions #UD If CR4.SMXE = 0. If GETSEC[WAKEUP] is not reported as supported by GETSEC[CAPABILITIES]. #GP(0) GETSEC[WAKEUP] is not recognized in virtual-8086 mode. Compatibility Mode Exceptions All protected mode exceptions apply.

64-Bit Mode Exceptions All protected mode exceptions apply.

VM-exit Condition Reason (GETSEC) IF in VMX non-root operation.

GETSEC[WAKEUP]—Wake up sleeping processors in measured environment

7-42 Vol. 2D
