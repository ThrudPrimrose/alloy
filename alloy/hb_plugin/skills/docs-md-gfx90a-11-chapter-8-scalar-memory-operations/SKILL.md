---
name: docs-md-gfx90a-11-chapter-8-scalar-memory-operations
description: "AMD CDNA2 ISA: Chapter 8. Scalar Memory Operations (vendor documentation for AMD gfx90a (CDNA2))."
when: "when you need AMD CDNA2 ISA: Chapter 8. Scalar Memory Operations while writing a AMD gfx90a (CDNA2) kernel."
---

"AMD Instinct MI200" Instruction Set Architecture



# **Chapter 8. Scalar Memory Operations**

Scalar Memory Read (SMEM) instructions allow a shader program to load data from memory into SGPRs through the Scalar Data Cache, or write data from SGPRs to memory through the Scalar Data Cache. Instructions can read from 1 to 16 Dwords, or write 1 to 4 Dwords at a time. Data is read directly into SGPRs without any format conversion.

The scalar unit reads and writes consecutive Dwords between memory and the SGPRs. This is intended primarily for loading ALU constants and for indirect T#/S# lookup. No data formatting is supported, nor is byte or short data.

## **8.1. Microcode Encoding**

Scalar memory read, write and atomic instructions are encoded using the SMEM microcode format.



The fields are described in the table below:

_Table 27. SMEM Encoding Field Descriptions_

|**Field**|**Size**|**Description**|
|---|---|---|
|OP|8|Opcode.|
|IMM|1|Determines how the OFFSET field is interpreted.<br>IMM=1 : Offset is a 20-bit unsigned byte offset to the address.<br>IMM=0 : Offset[6:0] specifies an SGPR or M0 which provides an unsigned byte offset (for stores,<br>must be M0). STORE and ATOMIC instructions cannot use an SGPR: only imm or M0.|
|GLC|1|Globally Coherent.<br>For loads, controls L1 cache policy: 0=hit_lru, 1=miss_evict.<br>For stores, controls L1 cache bypass: 0=write-combine, 1=write-thru.<br>For atomics, "1" indicates that the atomic returns the pre-op value.|
|SDATA|7|SGPRs to return read data to, or to source write-data from.<br>Reads of two Dwords must have an even SDST-sgpr.<br>Reads of four or more Dwords must have their DST-gpr aligned to a multiple of 4.<br>SDATA must be: SGPR or VCC. Not: exec or m0.|
|SBASE|6|SGPR-pair (SBASE has an implied LSB of zero) which provides a base address, or for BUFFER<br>instructions, a set of 4 SGPRs (4-sgpr aligned) which hold the resource constant. For BUFFER<br>instructions, the only resource fields used are: base, stride, num_records.|
|OFFSET|20|An unsigned byte offset, or the address of an SGPR holding the offset. Writes and atomics: M0 or<br>immediate only, not SGPR.|
|NV|1|Non-volatile.|



8.1. Microcode Encoding

50 of 267

"AMD Instinct MI200" Instruction Set Architecture



**Field Size Description** SOE 1 Scalar Offset Enable.

## **8.2. Operations**

### **8.2.1. S_LOAD_DWORD, S_STORE_DWORD**

These instructions load 1-16 Dwords or store 1-4 Dwords between SGPRs and memory. The data in SGPRs is specified in SDATA, and the address is composed of the SBASE, OFFSET, and SOFFSET fields.

#### **8.2.1.1. Scalar Memory Addressing**

S_LOAD / S_STORE / S_DACHE_DISCARD:

ADDR = SGPR[base] + inst_offset + { M0 or SGPR[offset] or zero }

S_SCRATCH_LOAD / S_SCRATCH_STORE:

ADDR = SGPR[base] + inst_offset + { M0 or SGPR[offset] or zero } * 64

Use of offset fields:

|**IMM**|**SOFFSET_EN (SOE)**|**Address**|
|---|---|---|
|0|0|SGPR[base] + (SGPR[offset] or M0)|
|0|1|SGPR[base] + (SGPR[soffset] or M0)|
|1|0|SGPR[base] + inst_offset|
|1|1|SGPR[base] + inst_offset + (SGPR[soffset] or M0)|



All components of the address (base, offset, inst_offset, M0) are in bytes, but the two LSBs are ignored and treated as if they were zero. S_DCACHE_DISCARD ignores the six LSBs to make the address 64-byte-aligned.

It is illegal and undefined if the inst_offset is negative and the resulting (inst_offset + (M0 or SGPR[offset])) is negative.

Scalar access to private space must either use a buffer constant or manually convert the address:

8.2. Operations

51 of 267

"AMD Instinct MI200" Instruction Set Architecture



Addr = Addr - private_base + private_base_addr + scratch_baseOffset_for_this_wave

"Hidden private base" is not available to the shader through hardware: It must be preloaded into an SGPR or made available through a constant buffer. This is equivalent to what the driver must do to calculate the base address from scratch for buffer constants.

A scalar instruction must not overwrite its own source registers because the possibility of the instruction being replayed due to an ATC XNACK. Similarly, instructions in scalar memory clauses must not overwrite the sources of any of the instructions in the clause. A clause is defined as a string of memory instructions of the same type. A clause is broken by any nonmemory instruction.

Atomics are unusual because they are naturally aligned and they must be in a single-instruction clause. By definition, an atomic that returns the pre-op value overwrites its data source, which is acceptable.

##### **Reads/Writes/Atomics using Buffer Constant**

Buffer constant fields used: base_address, stride, num_records, NV. Other fields are ignored.

Scalar memory read/write does not support "swizzled" buffers. Stride is used only for memory address bounds checking, not for computing the address to access.

The SMEM supplies only a SBASE address (byte) and an offset (byte or Dword). Any "index * stride" must be calculated manually in shader code and added to the offset prior to the SMEM.

The two LSBs of V#.base and of the final address are ignored to force Dword alignment.

"m_*" components come from the buffer constant (V#): offset     = IMM ? OFFSET : SGPR[OFFSET] m_base     = { SGPR[SBASE * 2 +1][15:0], SGPR[SBASE] } m_stride   = SGPR[SBASE * 2 +1][31:16] m_num_records = SGPR[SBASE * 2 + 2] m_size     = (m_stride == 0) ? 1 : m_num_records m_addr     = (SGPR[SBASE * 2] + offset) & ~0x3 SGPR[SDST] = read_Dword_from_dcache(m_base, offset, m_size)

If more than 1 dword is being read, it is returned to SDST+1, SDST+2, etc, and the offset is incremented by 4 bytes per DWORD.

### **8.2.2. Scalar Atomic Operations**

The scalar memory unit supports the same set of memory atomics as the vector memory unit. Addressing is the same as for scalar memory loads and stores. Like the vector memory atomics, scalar atomic operations can return the "pre-operation value" to the SDATA SGPRs.

8.2. Operations

52 of 267

"AMD Instinct MI200" Instruction Set Architecture



This is enabled by setting the microcode GLC bit to 1.

### **8.2.3. S_DCACHE_INV, S_DCACHE_WB**

This instruction invalidates, or does a "write back" of dirty data, for the entire data cache. It does not return anything to SDST.

### **8.2.4. S_MEMTIME**

This instruction reads a 64-bit clock counter into a pair of SGPRs: SDST and SDST+1.

### **8.2.5. S_MEMREALTIME**

This instruction reads a 64-bit "real time-counter" and returns the value into a pair of SGPRS: SDST and SDST+1. The time value is from a constant 25MHz clock (not affected by power modes or core clock frequency changes).

## **8.3. Dependency Checking**

Scalar memory reads and writes can return data out-of-order from how they were issued; they can return partial results at different times when the read crosses two cache lines. The shader program uses the LGKM_CNT counter to determine when the data has been returned to the SDST SGPRs. This is done as follows.

- LGKM_CNT is incremented by 1 for every fetch of a single Dword.

- LGKM_CNT is incremented by 2 for every fetch of two or more Dwords.

- LGKM_CNT is decremented by an equal amount when each instruction completes.

Because the instructions can return out-of-order, the only sensible way to use this counter is to implement S_WAITCNT 0; this imposes a wait for all data to return from previous SMEMs before continuing.

## **8.4. Alignment and Bounds Checking**

#### **SDST**

The value of SDST must be even for fetches of two Dwords (including S_MEMTIME), or a multiple of four for larger fetches. If this rule is not followed, invalid data can result. If SDST is out-of-range, the instruction is not executed.

8.3. Dependency Checking

53 of 267

"AMD Instinct MI200" Instruction Set Architecture



#### **SBASE**

The value of SBASE must be even for S_BUFFER_LOAD (specifying the address of an SGPR which is a multiple of four). If SBASE is out-of-range, the value from SGPR0 is used.

#### **OFFSET**

The value of OFFSET has no alignment restrictions.

**Memory Address** : If the memory address is out-of-range (clamped), the operation is not performed for any Dwords that are out-of-range.

8.4. Alignment and Bounds Checking

54 of 267
