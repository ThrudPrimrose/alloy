---
name: docs-md-gfx90a-13-chapter-10-flat-memory-instructions
description: "AMD CDNA2 ISA: Chapter 10. Flat Memory Instructions (vendor documentation for AMD gfx90a (CDNA2))."
when: "when you need AMD CDNA2 ISA: Chapter 10. Flat Memory Instructions while writing a kernel for AMD gfx90a (CDNA2)."
---

"AMD Instinct MI200" Instruction Set Architecture



# **Chapter 10. Flat Memory Instructions**

Flat Memory instructions read, or write, one piece of data into, or out of, VGPRs; they do this separately for each work-item in a wavefront. Unlike buffer or image instructions, Flat instructions do not use a resource constant to define the base address of a surface. Instead, Flat instructions use a single flat address from the VGPR; this addresses memory as a single flat memory space. This memory space includes video memory, system memory, LDS memory, and scratch (private) memory. Parts of the flat memory space may not map to any real memory, and accessing these regions generates a memory-violation error. The determination of the memory space to which an address maps is controlled by a set of "memory aperture" base and size registers.

## **10.1. Flat Memory Instruction**

Flat memory instructions let the kernel read or write data in memory, or perform atomic operations on data already in memory. These operations occur through the texture L2 cache. The instruction declares which VGPR holds the address (either 32- or 64-bit, depending on the memory configuration), the VGPR which sends and the VGPR which receives data. Flat instructions also use M0 as described in the table below:

_Table 44. Flat, Global and Scratch Microcode Formats_

|**Field**|**Bit Size**|**Description**|
|---|---|---|
|OP|7|Opcode. Can be Flat, Scratch or Global instruction. See next table.|
|ADDR|8|VGPR which holds the address. For 64-bit addresses, ADDR has the LSBs, and ADDR+1 has<br>the MSBs.|
|DATA|8|VGPR which holds the first Dword of data. Instructions can use 0-4 Dwords.|
|VDST|8|VGPR destination for data returned to the kernel, either from LOADs or Atomics with GLC=1<br>(return pre-op value).|
|SLC|1|System Level Coherent. Used in conjunction with GLC to determine cache policies.|
|GLC|1|Global Level Coherent. For Atomics, GLC: 1 means return pre-op value, 0 means do|
|ACC|1|VDATA is Accumulation VGPR|
|reserved|1|must be set to zero not return pre-op value.|
|SEG|2|Memory Segment: 0=FLAT, 1=SCRATCH, 2=GLOBAL, 3=reserved.|
|LDS|1|When set, data is moved between LDS and memory instead of VGPRs and memory. For Global<br>and Scratch only; must be zero for Flat.|
|NV|1|Non-volatile. When set, the read/write is operating on non-volatile memory.|
|OFFSET|13|Address offset.<br>Scratch, Global: 13-bit signed byte offset.<br>Flat: 12-bit unsigned offset (MSB is ignored).|



10.1. Flat Memory Instruction

80 of 267

"AMD Instinct MI200" Instruction Set Architecture



#### **Field Bit Size Description**

|SADDR|7|Scalar SGPR that provides an offset address. To disable, set this field to 0x7F. Meaning of this<br>field is different for Scratch and Global:<br>Flat: Unused.<br>Scratch: Use an SGPR (instead of VGPR) for the address.<br>Global: Use the SGPR to provide a base address; the VGPR provides a 32-bit offset.|
|---|---|---|
|M0|16|Implied use of M0 for SCRATCH and GLOBAL only when LDS=1. Provides the LDS address-<br>offset.|



_Table 45. Flat, Global and Scratch Opcodes_

|**Flat Opcodes**|**Global Opcodes**|**Scratch Opcodes**|
|---|---|---|
|FLAT|GLOBAL|SCRATCH|
|FLAT_LOAD_UBYTE|GLOBAL_LOAD_UBYTE|SCRATCH_LOAD_UBYTE|
|FLAT_LOAD_UBYTE_D16|GLOBAL_LOAD_UBYTE_D16|SCRATCH_LOAD_UBYTE_D16|
|FLAT_LOAD_UBYTE_D16_HI|GLOBAL_LOAD_UBYTE_D16_HI|SCRATCH_LOAD_UBYTE_D16_HI|
|FLAT_LOAD_SBYTE|GLOBAL_LOAD_SBYTE|SCRATCH_LOAD_SBYTE|
|FLAT_LOAD_SBYTE_D16|GLOBAL_LOAD_SBYTE_D16|SCRATCH_LOAD_SBYTE_D16|
|FLAT_LOAD_SBYTE_D16_HI|GLOBAL_LOAD_SBYTE_D16_HI|SCRATCH_LOAD_SBYTE_D16_HI|
|FLAT_LOAD_USHORT|GLOBAL_LOAD_USHORT|SCRATCH_LOAD_USHORT|
|FLAT_LOAD_SSHORT|GLOBAL_LOAD_SSHORT|SCRATCH_LOAD_SSHORT|
|FLAT_LOAD_SHORT_D16|GLOBAL_LOAD_SHORT_D16|SCRATCH_LOAD_SHORT_D16|
|FLAT_LOAD_SHORT_D16_HI|GLOBAL_LOAD_SHORT_D16_HI|SCRATCH_LOAD_SHORT_D16_HI|
|FLAT_LOAD_DWORD|GLOBAL_LOAD_DWORD|SCRATCH_LOAD_DWORD|
|FLAT_LOAD_DWORDX2|GLOBAL_LOAD_DWORDX2|SCRATCH_LOAD_DWORDX2|
|FLAT_LOAD_DWORDX3|GLOBAL_LOAD_DWORDX3|SCRATCH_LOAD_DWORDX3|
|FLAT_LOAD_DWORDX4|GLOBAL_LOAD_DWORDX4|SCRATCH_LOAD_DWORDX4|
|FLAT_STORE_BYTE|GLOBAL_STORE_BYTE|SCRATCH_STORE_BYTE|
|FLAT_STORE_BYTE_D16_HI|GLOBAL_STORE_BYTE_D16_HI|SCRATCH_STORE_BYTE_D16_HI|
|FLAT_STORE_SHORT|GLOBAL_STORE_SHORT|SCRATCH_STORE_SHORT|
|FLAT_STORE_SHORT_D16_HI|GLOBAL_STORE_SHORT_D16_HI|SCRATCH_STORE_SHORT_D16_HI|
|FLAT_STORE_DWORD|GLOBAL_STORE_DWORD|SCRATCH_STORE_DWORD|
|FLAT_STORE_DWORDX2|GLOBAL_STORE_DWORDX2|SCRATCH_STORE_DWORDX2|
|FLAT_STORE_DWORDX3|GLOBAL_STORE_DWORDX3|SCRATCH_STORE_DWORDX3|
|FLAT_STORE_DWORDX4|GLOBAL_STORE_DWORDX4|SCRATCH_STORE_DWORDX4|
|FLAT_ATOMIC_SWAP|GLOBAL_ATOMIC_SWAP|none|
|FLAT_ATOMIC_CMPSWAP|GLOBAL_ATOMIC_CMPSWAP|none|
|FLAT_ATOMIC_ADD|GLOBAL_ATOMIC_ADD|none|



10.1. Flat Memory Instruction

81 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Flat Opcodes**|**Global Opcodes**|**Scratch Opcodes**|
|---|---|---|
|FLAT_ATOMIC_SUB|GLOBAL_ATOMIC_SUB|none|
|FLAT_ATOMIC_SMIN|GLOBAL_ATOMIC_SMIN|none|
|FLAT_ATOMIC_UMIN|GLOBAL_ATOMIC_UMIN|none|
|FLAT_ATOMIC_SMAX|GLOBAL_ATOMIC_SMAX|none|
|FLAT_ATOMIC_UMAX|GLOBAL_ATOMIC_UMAX|none|
|FLAT_ATOMIC_AND|GLOBAL_ATOMIC_AND|none|
|FLAT_ATOMIC_OR|GLOBAL_ATOMIC_OR|none|
|FLAT_ATOMIC_XOR|GLOBAL_ATOMIC_XOR|none|
|FLAT_ATOMIC_INC|GLOBAL_ATOMIC_INC|none|
|FLAT_ATOMIC_DEC|GLOBAL_ATOMIC_DEC|none|
|none|GLOBAL_ATOMIC_ADD_F32|none|
|none|GLOBAL_ATOMIC_PK_ADD_F16|none|



The atomic instructions above are also available in "_X2" versions (64-bit).

## **10.2. Instructions**

The FLAT instruction set is nearly identical to the Buffer instruction set, but without the FORMAT reads and writes. Unlike Buffer instructions, FLAT instructions cannot return data directly to LDS, but only to VGPRs.

FLAT instructions do not use a resource constant (V#) or sampler (S#); however, they do require a specific SGPR-pair to hold scratch-space information in case any threads' address resolves to scratch space. See the Scratch section for details.

Internally, FLAT instruction are executed as both an LDS and a Buffer instruction; so, they increment both VM_CNT and LGKM_CNT and are not considered done until both have been decremented. There is no way beforehand to determine whether a FLAT instruction uses only LDS or TA memory space.

### **10.2.1. Ordering**

Flat instructions can complete out of order with each other. If one flat instruction finds all of its data in Texture cache, and the next finds all of its data in LDS, the second instruction might complete first. If the two fetches return data to the same VGPR, the result are unknown.

### **10.2.2. Important Timing Consideration**

Since the data for a FLAT load can come from either LDS or the texture cache, and because

10.2. Instructions

82 of 267

"AMD Instinct MI200" Instruction Set Architecture



these units have different latencies, there is a potential race condition with respect to the VM_CNT and LGKM_CNT counters. Because of this, the only sensible S_WAITCNT value to use after FLAT instructions is zero.

## **10.3. Addressing**

FLAT instructions support both 64- and 32-bit addressing. The address size is set using a mode register (PTR32), and a local copy of the value is stored per wave.

The addresses for the aperture check differ in 32- and 64-bit mode; however, this is not covered here.

64-bit addresses are stored with the LSBs in the VGPR at ADDR, and the MSBs in the VGPR at ADDR+1.

For scratch space, the texture unit takes the address from the VGPR and does the following.

Address = VGPR[addr] + TID_in_wave * Size - private aperture base (in SH_MEM_BASES) + offset (from flat_scratch)

### **10.3.1. Atomics**

Float atomics must set GLC=0 (no return value).

Memory atomics are performed in the last level texture cache so they are not known to be atomic with host memory access. Memory atomics which attempt to access host memory that is non-cacheable will be silently dropped.

FP32 atomic operations flush denormals to zero, and both FP64 and FP16 atomic never flush denormals. The rounding mode is fixed and "round to nearest even".

## **10.4. Global**

Global instructions are similar to Flat instructions, but the programmer must ensure that no threads access LDS space; thus, no LDS bandwidth is used by global instructions.

Global instructions offer two types of addressing:

- Memory_addr = VGPR-address + instruction offset.

- Memory_addr = SGPR-address + VGPR-offset + instruction offset.

The size of the address component is dependent on ADDRESS_MODE: 32-bits or 64-bit

10.3. Addressing

83 of 267

"AMD Instinct MI200" Instruction Set Architecture



pointers. The VGPR-offset is 32 bits.

These instructions also allow direct data movement between LDS and memory without going through VGPRs.

Since these instructions do not access LDS, only VM_CNT is used, not LGKM_CNT. If a global instruction does attempt to access LDS, the instruction returns MEM_VIOL.

## **10.5. Scratch**

Scratch instructions are similar to Flat, but the programmer must ensure that no threads access LDS space, and the memory space is swizzled. Thus, no LDS bandwidth is used by scratch instructions.

Scratch instructions also support multi-Dword access and mis-aligned access (although misaligned is slower).

Scratch instructions use the following addressing:

- Memory_addr = flat_scratch.addr + swizzle(V/SGPR_offset + inst_offset, threadID)

- The offset can come from either an SGPR or a VGPR, and is a 32- bit unsigned byte.

The size of the address component is dependent on the ADDRESS_MODE: 32-bits or 64-bit pointers. The VGPR-offset is 32 bits.

These instructions also allow direct data movement between LDS and memory without going through VGPRs.

Since these instructions do not access LDS, only VM_CNT is used, not LGKM_CNT. It is not possible for a Scratch instruction to access LDS; thus, no error or aperture checking is done.

## **10.6. Memory Error Checking**

Both TA and LDS can report that an error occurred due to a bad address. This can occur in the following cases:

- invalid address (outside any aperture)

- write to read-only surface

- misaligned data

- out-of-range address:

   - ◦LDS access with an address outside the range: [ 0, MIN(M0, LDS_SIZE)-1 ]

   - ◦Scratch access with an address outside the range: [0, scratch-size -1 ]

The policy for threads with bad addresses is: writes outside this range do not write a value, and

10.5. Scratch

84 of 267

"AMD Instinct MI200" Instruction Set Architecture



reads return zero.

Addressing errors from either LDS or TA are returned on their respective "instruction done" busses as MEM_VIOL. This sets the wave’s MEM_VIOL TrapStatus bit and causes an exception (trap) if the corresponding EXCPEN bit is set.

## **10.7. Data**

FLAT instructions can use zero to four consecutive Dwords of data in VGPRs and/or memory. The DATA field determines which VGPR(s) supply source data (if any), and the VDST VGPRs hold return data (if any). No data-format conversion is done.

## **10.8. Scratch Space (Private)**

Scratch (thread-private memory) is an area of memory defined by the aperture registers. When an address falls in scratch space, additional address computation is automatically performed by the hardware. The kernel must provide additional information for this computation to occur in the form of the FLAT_SCRATCH register.

The FLAT_SCRATCH address is automatically sent with every FLAT request.

FLAT_SCRATCH is a 64-bit, byte address. The shader composes the value by adding together two separate values: the base address, which can be passed in via an initialized SGPR, or perhaps through a constant buffer, and the per-wave allocation offset (also initialized in an SGPR).

85 of 267

10.7. Data
