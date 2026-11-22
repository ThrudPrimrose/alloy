---
name: docs-md-gfx90a-12-chapter-9-vector-memory-operations
description: "AMD CDNA2 ISA: Chapter 9. Vector Memory Operations (vendor documentation for AMD gfx90a (CDNA2))."
when: "when you need AMD CDNA2 ISA: Chapter 9. Vector Memory Operations while writing a AMD gfx90a (CDNA2) kernel."
---

"AMD Instinct MI200" Instruction Set Architecture



# **Chapter 9. Vector Memory Operations**

Vector Memory (VMEM) instructions read or write one piece of data separately for each workitem in a wavefront into, or out of, VGPRs. This is in contrast to Scalar Memory instructions, which move a single piece of data that is shared by all threads in the wavefront. All Vector Memory (VM) operations are processed by the texture cache system (level 1 and level 2 caches).

Software initiates a load, store or atomic operation through the texture cache through one of three types of VMEM instructions:

- MTBUF: Memory typed-buffer operations.

- MUBUF: Memory untyped-buffer operations.

- MIMG: Memory image operations.

The instruction defines which VGPR(s) supply the addresses for the operation, which VGPRs supply or receive data from the operation, and a series of SGPRs that contain the memory buffer descriptor (V# or T#). Also, MIMG operations supply a texture sampler from a series of four SGPRs; this sampler defines texel filtering operations to be performed on data read from the image.

## **9.1. Vector Memory Buffer Instructions**

Vector-memory (VM) operations transfer data between the VGPRs and buffer objects in memory through the texture cache (TC). **Vector** means that one or more piece of data is transferred uniquely for every thread in the wavefront, in contrast to scalar memory reads, which transfer only one value that is shared by all threads in the wavefront.

Buffer reads have the option of returning data to VGPRs or directly into LDS.

Examples of buffer objects are vertex buffers, raw buffers, stream-out buffers, and structured buffers.

Buffer objects support both homogeneous and heterogeneous data, but no filtering of read-data (no samplers). Buffer instructions are divided into two groups:

- MUBUF: Untyped buffer objects.

   - ◦Data format is specified in the resource constant.

   - ◦Load, store, atomic operations, with or without data format conversion.

- MTBUF: Typed buffer objects.

   - ◦Data format is specified in the instruction.

   - ◦The only operations are Load and Store, both with data format conversion.

Atomic operations take data from VGPRs and combine them arithmetically with data already in

9.1. Vector Memory Buffer Instructions

55 of 267

"AMD Instinct MI200" Instruction Set Architecture



memory. Optionally, the value that was in memory before the operation took place can be returned to the shader.

All VM operations use a buffer resource constant (V#) which is a 128-bit value in SGPRs. This constant is sent to the texture cache when the instruction is executed. This constant defines the address and characteristics of the buffer in memory. Typically, these constants are fetched from memory using scalar memory reads prior to executing VM instructions, but these constants also can be generated within the shader.

### **9.1.1. Simplified Buffer Addressing**

The equation below shows how the hardware calculates the memory address for a buffer access.



### **9.1.2. Buffer Instructions**

Buffer instructions (MTBUF and MUBUF) allow the shader program to read from, and write to, linear buffers in memory. These operations can operate on data as small as one byte, and up to four Dwords per work-item. Atomic arithmetic operations are provided that can operate on the data values in memory and, optionally, return the value that was in memory before the arithmetic operation was performed.

The D16 instruction variants convert the results to packed 16-bit values. For example, BUFFER_LOAD_FORMAT_D16_XYZW will write two VGPRs.

_Table 28. Buffer Instructions_

|**Instruction**|**Description**|
|---|---|
|MTBUF Instructions||
|TBUFFER_LOAD_FORMAT_{x,xy,xyz,xyzw}<br>TBUFFER_STORE_FORMAT_{x,xy,xyz,xyzw}|Read from, or write to, a typed buffer object. Also used for a vertex<br>fetch.|
|MUBUF Instructions||
|BUFFER_LOAD_FORMAT_{x,xy,xyz,xyzw}|Read to, or write from, an untyped buffer object.|
|BUFFER_STORE_FORMAT_{x,xy,xyz,xyzw}|<size> = byte, ubyte, short, ushort, Dword, Dwordx2, Dwordx3,|
|BUFFER_LOAD_<size>|Dwordx4 BUFFER_ATOMIC_<op>|
|BUFFER_STORE_<size>|BUFFER_ATOMIC_<op>_ x2|



_Table 29. Microcode Formats_

9.1. Vector Memory Buffer Instructions

56 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Field**|**Bit Si**|**ze**<br>**Description**|
|---|---|---|
|OP|4<br>7|MTBUF: Opcode for Typed buffer instructions.<br>MUBUF: Opcode for Untyped buffer instructions.|
|VADDR|8|Address of VGPR to supply first component of address (offset or index). When both index and<br>offset are used, index is in the first VGPR, offset in the second.|
|VDATA|8|Address of VGPR to supply first component of write data or receive first component of read-<br>data.|
|SOFFSET|8|SGPR to supply unsigned byte offset. Must be an SGPR, M0, or inline constant.|
|SRSRC|5|Specifies which SGPR supplies T# (resource constant) in four or eight consecutive SGPRs.<br>This field is missing the two LSBs of the SGPR address, since this address must be aligned to<br>a multiple of four SGPRs.|
|DFMT|4|Data Format of data in memory buffer:<br>0 invalid<br>1 8<br>2 16<br>3 8_8<br>4 32<br>5 16_16<br>6 10_11_11<br>7 11_11_10<br>8 10_10_10_2<br>9 2_10_10_10<br>10 8_8_8_8<br>11 32_32<br>12 16_16_16_16<br>13 32_32_32<br>14 32_32_32_32<br>15 reserved|
|NFMT|3|Numeric format of data in memory:<br>0 unorm<br>1 snorm<br>2 uscaled<br>3 sscaled<br>4 uint<br>5 sint<br>6 reserved<br>7 float|
|OFFSET|12|Unsigned byte offset.|
|OFFEN|1|1 = Supply an offset from VGPR (VADDR). 0 = Do not (offset = 0).|
|IDXEN|1|1 = Supply an index from VGPR (VADDR). 0 = Do not (index = 0).|



9.1. Vector Memory Buffer Instructions

57 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Field**|**Bit Size**|**Description**|
|---|---|---|
|GLC|1|Globally Coherent. Controls how reads and writes are handled by the L1 texture cache.<br>**READ**<br>GLC = 0 Reads can hit on the L1 and persist across wavefronts<br>GLC = 1 Reads miss the L1 and force fetch to L2. No L1 persistence across waves.<br>**WRITE**<br>GLC = 0 Writes miss the L1, write through to L2, and persist in L1 across wavefronts.<br>GLC = 1 Writes miss the L1, write through to L2. No persistence across wavefronts.<br>**ATOMIC**<br>GLC = 0 Previous data value is not returned. No L1 persistence across wavefronts.<br>GLC = 1 Previous data value is returned. No L1 persistence across wavefronts.<br>Note: GLC means "return pre-op value" for atomics.|
|SLC|1|System Level Coherent. When set, sets "streaming" mode in the L2 cache which should be<br>used for non-temoporal accesses.|
|ACC|1|VDATA is Accumulation VGPR|
|reserved|1|must set to zero can return a NACK that causes a VGPR write into DST+1 (first GPR after all<br>fetch-dest GPRs).|
|LDS|1|MUBUF-ONLY: 0 = Return read-data to VGPRs. 1 = Return read-data to LDS instead of<br>VGPRs.|



### **9.1.3. VGPR Usage**

VGPRs supply address and write-data; also, they can be the destination for return data (the other option is LDS).

#### **Address**

Zero, one or two VGPRs are used, depending of the offset-enable (OFFEN) and indexenable (IDXEN) in the instruction word, as shown in the table below:

_Table 30. Address VGPRs_

|**IDXEN**|**OFFEN**|**VGPRn**|**VGPRn+1**|
|---|---|---|---|
|0|0|nothing||
|0|1|uint offset||
|1|0|uint index||
|1|1|uint index|uint offset|



**Write Data** : N consecutive VGPRs, starting at VDATA. The data format specified in the instruction word (NFMT, DFMT for MTBUF, or encoded in the opcode field for MUBUF) determines how many Dwords to write.

**Read Data** : Same as writes. Data is returned to consecutive GPRs.

**Read Data Format** : Read data is 32 bits, based on the data format in the instruction or resource. Float or normalized data is returned as floats; integer formats are returned as integers

9.1. Vector Memory Buffer Instructions

58 of 267

"AMD Instinct MI200" Instruction Set Architecture



(signed or unsigned, same type as the memory storage format). Memory reads of data in memory that is 32 or 64 bits do not undergo any format conversion.

**Atomics with Return** : Data is read out of the VGPR(s) starting at VDATA to supply to the atomic operation. If the atomic returns a value to VGPRs, that data is returned to those same VGPRs starting at VDATA.

### **9.1.4. Buffer Data**

The amount and type of data that is read or written is controlled by the following: data-format (dfmt), numeric-format (nfmt), destination-component-selects (dst_sel), and the opcode. Dfmt and nfmt can come from the resource, instruction fields, or the opcode itself. Dst_sel comes from the resource, but is ignored for many operations.

_Table 31. Buffer Instructions_

|**Instruction**|**Data Format**|**Num Format**|**DST SEL**|
|---|---|---|---|
|TBUFFER_LOAD_FORMAT_*|instruction|instruction|identity|
|TBUFFER_STORE_FORMAT_*|instruction|instruction|identity|
|BUFFER_LOAD_<type>|derived|derived|identity|
|BUFFER_STORE_<type>|derived|derived|identity|
|BUFFER_LOAD_FORMAT_*|resource|resource|resource|
|BUFFER_STORE_FORMAT_*|resource|resource|resource|
|BUFFER_ATOMIC_*|derived|derived|identity|



**Instruction** : The instruction’s dfmt and nfmt fields are used instead of the resource’s fields.

**Data format derived** : The data format is derived from the opcode and ignores the resource definition. For example, buffer_load_ubyte sets the data-format to 8 and number-format to uint.

The resource’s data format must not be INVALID; that format has specific meaning (unbound resource), and for that case the data format is not  replaced by the instruction’s implied data format.

**DST_SEL identity** : Depending on the number of components in the data-format, this is: X000, XY00, XYZ0, or XYZW.

The MTBUF derives the data format from the instruction. The MUBUF BUFFER_LOAD_FORMAT and BUFFER_STORE_FORMAT instructions use dst_sel from the resource; other MUBUF instructions derive data-format from the instruction itself.

**D16 Instructions** : Load-format and store-format instructions also come in a "d16" variant. For stores, each 32-bit VGPR holds two 16-bit data elements that are passed to the texture unit.

9.1. Vector Memory Buffer Instructions

59 of 267

"AMD Instinct MI200" Instruction Set Architecture



This texture unit converts them to the texture format before writing to memory. For loads, data returned from the texture unit is converted to 16 bits, and a pair of data are stored in each 32-bit VGPR (LSBs first, then MSBs). Control over int vs. float is controlled by NFMT.

### **9.1.5. Buffer Addressing**

A **buffer** is a data structure in memory that is addressed with an **index** and an **offset** . The index points to a particular record of size **stride** bytes, and the offset is the byte-offset within the record. The **stride** comes from the resource, the index from a VGPR (or zero), and the offset from an SGPR or VGPR and also from the instruction itself.

_Table 32. BUFFER Instruction Fields for Addressing_

|**Field**|**Size**|**Description**|
|---|---|---|
|inst_offset|12|Literal byte offset from the instruction.|
|inst_idxen|1|Boolean: get index from VGPR when true, or no index when false.|
|inst_offen|1|Boolean: get offset from VGPR when true, or no offset when false. Note that inst_offset is<br>present, regardless of this bit.|



The "element size" for a buffer instruction is the amount of data the instruction transfers. It is determined by the DFMT field for MTBUF instructions, or from the opcode for MUBUF instructions. It can be 1, 2, 4, 8, or 16 bytes.

_Table 33. V# Buffer Resource Constant Fields for Addressing_

|**Field**|**Size**|**Description**|
|---|---|---|
|const_base|48|Base address, in bytes, of the buffer resource.|
|const_stride|14<br>or<br>18|Stride of the record in bytes (0 to 16,383 bytes, or 0 to 262,143<br>bytes). Normally 14 bits, but is extended to 18-bits when:<br>const_add_tid_enable = true used with MUBUF instructions which<br>are not**format**types (or cache invalidate/WB).<br>This is extension intended for use with scratch (private) buffers.|
|||If (const_add_tid_enable && MUBUF-non-format instr.)<br>const_stride [17:0] = { V#.DFMT[3:0],<br>V#.const_stride[13:0] }<br>else<br>const_stride is 14 bits: {4'b0, V#.const_stride[13:0]}|
|const_num_records|32|Number of records in the buffer.<br>In units of Bytes for raw buffers, units of Stride for structured buffers,<br>and ignored for private (scratch) buffers.<br>In units of: (inst_idxen == 1) ? Bytes : Stride|



9.1. Vector Memory Buffer Instructions

60 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Field**|**Size**|**Description**|
|---|---|---|
|const_add_tid_enab<br>le|1|Boolean. Add thread_ID within the wavefront to the index when true.|
|const_swizzle_enab<br>le|1|Boolean. Indicates that the surface is swizzled when true.|
|const_element_size|2|Used only when const_swizzle_en = true. Number of contiguous<br>bytes of a record for a given index (2, 4, 8, or 16 bytes).<br>Must be >= the maximum element size in the structure. const_stride<br>must be an integer multiple of const_element_size.|
|const_index_stride|2|Used only when const_swizzle_en = true. Number of contiguous<br>indices for a single element (of const_element_size) before switching<br>to the next element. There are 8, 16, 32, or 64 indices.|



_Table 34. Address Components from GPRs_

|**Field**|**Size**|**Description**|
|---|---|---|
|SGPR_offset|32|An unsigned byte-offset to the address. Comes from an SGPR or M0.|
|VGPR_offset|32|An optional unsigned byte-offset. It is per-thread, and comes from a VGPR.|
|VGPR_index|32|An optional index value. It is per-thread and comes from a VGPR.|



The final buffer memory address is composed of three parts:

- the base address from the buffer resource (V#),

- the offset from the SGPR, and

- a buffer-offset that is calculated differently, depending on whether the buffer is linearly addressed (a simple Array-of-Structures calculation) or is swizzled.



_Figure 4. Address Calculation for a Linear Buffer_

9.1. Vector Memory Buffer Instructions

61 of 267

"AMD Instinct MI200" Instruction Set Architecture



#### **9.1.5.1. Range Checking**

Addresses can be checked to see if they are in or out of range. When an address is out of range, reads will return zero, and writes and atomics will be dropped. The address range check method depends on the buffer type.

#### **Private (Scratch) Buffer**

Used when: AddTID==1 && IdxEn==0

For this buffer, there is no range checking.

#### **Raw Buffer**

Used when: AddTID==0 && SWizzleEn==0 && IdxEn==0 Out of Range if: (InstOffset + (OffEN ? vgpr_offset : 0)) >= NumRecords

#### **Structured Buffer**

Used when: AddTID==0 && Stride!=0 && IdxEn==1 Out of Range if: Index(vgpr) >= NumRecords

#### **Notes:**

1. Reads that go out-of-range return zero (except for components with V#.dst_sel = SEL_1 that return 1).

2. Writes that are out-of-range do not write anything.

3. Load/store-format-* instruction and atomics are range-checked "all or nothing" - either entirely in or out.

4. Load/store-Dword-x{2,3,4} and range-check per component.

#### **9.1.5.2. Swizzled Buffer Addressing**

Swizzled addressing rearranges the data in the buffer to help provide improved cache locality for arrays of structures. Swizzled addressing also requires Dword-aligned accesses. A single fetch instruction cannot attempt to fetch a unit larger than const-element-size. The buffer’s STRIDE must be a multiple of element_size.

9.1. Vector Memory Buffer Instructions

62 of 267

"AMD Instinct MI200" Instruction Set Architecture



Index = (inst_idxen ? vgpr_index : 0) + (const_add_tid_enable ? thread_id[5:0] : 0) Offset = (inst_offen ? vgpr_offset : 0) + inst_offset index_msb = index / const_index_stride index_lsb = index % const_index_stride offset_msb = offset / const_element_size offset_lsb = offset % const_element_size buffer_offset = (index_msb * const_stride + offset_msb * const_element_size) * const_index_stride + index_lsb * const_element_size + offset_lsb Final Address = const_base + sgpr_offset + buffer_offset

Remember that the "sgpr_offset" is not a part of the "offset" term in the above equations.

9.1. Vector Memory Buffer Instructions

63 of 267

"AMD Instinct MI200" Instruction Set Architecture





_Figure 5. Example of Buffer Swizzling_

#### **9.1.5.3. Proposed Use Cases for Swizzled Addressing**

Here are few proposed uses of swizzled addressing in common graphics buffers.

9.1. Vector Memory Buffer Instructions

64 of 267

"AMD Instinct MI200" Instruction Set Architecture



_Table 35. Swizzled Buffer Use Cases_

||**DX11 Raw**<br>**Uav OpenCL**<br>**Buffer Object**|**Dx11 Structured**<br>**(literal offset)**|**Dx11 Structured**<br>**(gpr offset)**|**Scratch**|**Ring /**<br>**stream-out**|**Const**<br>**Buffer**|
|---|---|---|---|---|---|---|
|inst_vgpr_offset_<br>en|T|F|T|T|T|T|
|inst_vgpr_index_<br>en|F|T|T|F|F|F|
|const_stride|na|<api>|<api>|scratchSize|na|na|
|const_add_tid_en<br>able|F|F|F|T|T|F|
|const_buffer_swiz<br>zle|F|T|T|T|F|F|
|const_elem_size|na|4|4|4 or 16|na|4|
|const_index_strid<br>e|na|16|16|64|||



### **9.1.6. 16-bit Memory Operations**

The D16 buffer instructions allow a kernel to load or store just 16 bits per work item between VGPRs and memory. There are two variants of these instructions:

- D16 loads data into or stores data from the lower 16 bits of a VGPR.

- D16_HI loads data into or stores data from the upper 16 bits of a VGPR.

For example, BUFFER_LOAD_UBYTE_D16 reads a byte per work-item from memory, converts it to a 16-bit integer, then loads it into the lower 16 bits of the data VGPR.

When ECC is enabled 16-bit memory loads write the full 32-bit VGPR. Unused bits are set to zero.

### **9.1.7. Alignment**

For Dword or larger reads or writes, the two LSBs of the byte-address are ignored, thus forcing Dword alignment.

### **9.1.8. Buffer Resource**

The buffer resource describes the location of a buffer in memory and the format of the data in the buffer. It is specified in four consecutive SGPRs (four aligned SGPRs) and sent to the texture cache with each buffer instruction.

9.1. Vector Memory Buffer Instructions

65 of 267

"AMD Instinct MI200" Instruction Set Architecture



The table below details the fields that make up the buffer resource descriptor.

_Table 36. Buffer Resource Descriptor_

|**Bits**|**Size**|**Name**|**Description**|
|---|---|---|---|
|47:0|48|Base address|Byte address.|
|61:48|14|Stride|Bytes 0 to 16383|
|62|1|Cache swizzle|Buffer access. Optionally, swizzle texture cache TC L1 cache banks.|
|63|1|Swizzle enable|Swizzle AOS according to stride, index_stride, and element_size,<br>else linear (stride * index + offset).|
|95:64|32|Num_records|In units of stride or bytes.|
|98:96|3|Dst_sel_x|Destination channel select:|
|101:99|3|Dst_sel_y|0=0, 1=1, 4=R, 5=G, 6=B, 7=A|
|104:102|3|Dst_sel_z||
|107:105|3|Dst_sel_w||
|110:108|3|Num format|Numeric data type (float, int, …). See instruction encoding for values.|
|114:111|4|Data format|Number of fields and size of each field. See instruction encoding for<br>values. For MUBUF instructions with ADD_TID_EN = 1. This field<br>holds Stride [17:14].|
|115|1|User VM Enable|Resource is mapped via tiled pool / heap.|
|116|1|User VM mode|Unmapped behavior: 0: null (return 0 / drop write); 1:invalid (results in<br>error)|
|118:117|2|Index stride|8, 16, 32, or 64. Used for swizzled buffer addressing.|
|119|1|Add tid enable|Add thread ID to the index for to calculate the address.|
|122:120|3|RSVD|Reserved. Must be set to zero.|
|123|1|NV|Non-volatile (0=volatile)|
|125:124|2|RSVD|Reserved. Must be set to zero.|
|127:126|2|Type|Value == 0 for buffer. Overlaps upper two bits of four-bit TYPE field in<br>128-bit T# resource.|



A resource set to all zeros acts as an unbound texture or buffer (return 0,0,0,0).

### **9.1.9. Memory Buffer Load to LDS**

The MUBUF instruction format allows reading data from a memory buffer directly into LDS without passing through VGPRs. This is supported for the following subset of MUBUF instructions.

- BUFFER_LOAD_{ubyte, sbyte, ushort, sshort, dword, format_x}.

9.1. Vector Memory Buffer Instructions

66 of 267

"AMD Instinct MI200" Instruction Set Architecture



LDS_offset = 16-bit unsigned byte offset from M0[15:0]. Mem_offset = 32-bit unsigned byte offset from an SGPR (the SOFFSET SGPR). idx_vgpr = index value from a VGPR (located at VADDR). (Zero if idxen=0.) off_vgpr = offset value from a VGPR (located at VADDR or VADDR+1). (Zero if offen=0.)

The figure below shows the components of the LDS and memory address calculation:



TIDinWave is only added if the resource (T#) has the ADD_TID_ENABLE field set to 1, whereas LDS adds it. The MEM_ADDR M0 is in the VDATA field; it specifies M0.

#### **9.1.9.1. Clamping Rules**

Memory address clamping follows the same rules as any other buffer fetch. LDS address clamping: the return data must not be written outside the LDS space allocated to this wave.

- Set the active-mask to limit buffer reads to those threads that return data to a legal LDS location.

- The LDSbase (alloc) is in units of 32 Dwords, as is LDSsize.

- M0[15:0] is in bytes.

### **9.1.10. GLC Bit Explained**

The GLC bit means different things for loads, stores, and atomic ops.

#### **GLC Meaning for Loads**

- For GLC==0

   - ◦The load can read data from the GPU L1.

   - ◦Typically, all loads (except load-acquire) use GLC==0.

- For GLC==1

   - ◦The load intentionally misses the GPU L1 and reads from L2. If there was a line in the GPU L1 that matched, it is invalidated; L2 is reread.

9.1. Vector Memory Buffer Instructions

67 of 267

"AMD Instinct MI200" Instruction Set Architecture



- ◦NOTE: L2 is not re-read for every work-item in the same wave-front for a single load instruction. For example: b=uav[N+tid] // assume this is a byte read w/ glc==1 and N is aligned to 64B In the above op, the first Tid of the wavefront brings in the line from L2 or beyond, and all 63 of the other Tids read from same 64 B cache line in the L1.

#### **GLC Meaning for Stores**

- For GLC==0 This causes a write-combine across work-items of the wavefront store op; dirtied lines are written to the L2 automatically.

   - ◦If the store operation dirtied all bytes of the 64 B line, it is left clean and valid in the L1; subsequent accesses to the cache are allowed to hit on this cache line.

   - ◦Else do not leave write-combined lines in L1.

- For GLC==1 Same as GLC==0, except the write-combined lines are not left in the line, even if all bytes are dirtied.

#### **Atomics**

- For GLC == 0 No return data (this is "write-only" atomic op).

- For GLC == 1 Returns previous value in memory (before the atomic operation).

## **9.2. Vector Memory (VM) Image Instructions**

Vector Memory (VM) operations transfer data between the VGPRs and memory through the texture cache (TC). Vector means the transfer of one or more pieces of data uniquely for every work-item in the wavefront. This is in contrast to scalar memory reads, which transfer only one value that is shared by all work-items in the wavefront.

Examples of image objects are texture maps and typed surfaces.

Image objects are accessed using from one to four dimensional addresses; they are composed of homogeneous data of one to four elements. These image objects are read from, or written to, using IMAGE_* or SAMPLE_* instructions, all of which use the MIMG instruction format. IMAGE_LOAD instructions read an element from the image buffer directly into VGPRS, and SAMPLE instructions use sampler constants (S#) and apply filtering to the data after it is read. IMAGE_ATOMIC instructions combine data from VGPRs with data already in memory, and optionally return the value that was in memory before the operation.

All VM operations use an image resource constant (T#) that is a 256-bit value in SGPRs. This constant is sent to the texture cache when the instruction is executed. This constant defines the address, data format, and characteristics of the surface in memory. Some image instructions also use a sampler constant that is a 128-bit constant in SGPRs. Typically, these constants are fetched from memory using scalar memory reads prior to executing VM instructions, but these constants can also be generated within the shader.

Texture fetch instructions have a data mask (DMASK) field. DMASK specifies how many data

9.2. Vector Memory (VM) Image Instructions

68 of 267

"AMD Instinct MI200" Instruction Set Architecture



components it receives. If DMASK is less than the number of components in the texture, the texture unit only sends DMASK components, starting with R, then G, B, and A. if DMASK specifies more than the texture format specifies, the shader receives zero for the missing components.

### **9.2.1. Image Instructions**

This section describes the image instruction set, and the microcode fields available to those instructions.

_Table 37. Image Instructions_

|**MIMG**|**Description**|
|---|---|
|SAMPLE_*|Read and filter data from a image object.|
|IMAGE_LOAD_<op>|Read data from an image object using one of the following: image_load,<br>image_load_mip, image_load_{pck, pck_sgn, mip_pck, mip_pck_sgn}.|
|IMAGE_STORE<br>IMAGE_STORE_MIP|Store data to an image object. Store data to a specific mipmap level.|
|IMAGE_ATOMIC_<op>|Image atomic operation, which is one of the following: swap, cmpswap, add, sub,<br>rsub, {u,s}{min,max}, and, or, xor, inc, dec|



_Table 38. Instruction Fields_

|**Field**|**Bit Size**|**Description**|
|---|---|---|
|OP|7|Opcode.|
|VADDR|8|Address of VGPR to supply first component of address.|
|VDATA|8|Address of VGPR to supply first component of write data or receive first component of read-<br>data.|
|SSAMP|5|SGPR to supply S# (sampler constant) in four consecutive SGPRs. Missing two LSBs of SGPR-<br>address since must be aligned to a multiple of four SGPRs.|
|SRSRC|5|SGPR to supply T# (resource constant) in four or eight consecutive SGPRs. Missing two LSBs<br>of SGPR-address since must be aligned to a multiple of four SGPRs.|
|UNRM|1|Force address to be un-normalized regardless of T#. Must be set to 1 for image stores and<br>atomics.|
|DA|1|Shader declared an array resource to be used with this fetch.<br>When 1, the shader provides an array-index with the instruction.<br>When 0, no array index is provided.|
|DMASK|4|Data VGPR enable mask: one to four consecutive VGPRs. Reads: defines which components<br>are returned.<br>0 = red, 1 = green, 2 = blue, 3 = alpha<br>Writes: defines which components are written with data from VGPRs (missing components get<br>0). Enabled components come from consecutive VGPRs.<br>For example: DMASK=1001: Red is in VGPRn and alpha in VGPRn+1. For D16 writes, DMASK<br>is used only as a word count: each bit represents 16 bits of data to be written, starting at the<br>LSBs of VADDR, the MSBs, VADDR+1, etc. Bit position is ignored.|



9.2. Vector Memory (VM) Image Instructions

69 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Field**|**Bit Size**|**Description**|
|---|---|---|
|GLC|1|Globally Coherent. Controls how reads and writes are handled by the L1 texture cache.<br>**READ:**<br>GLC = 0 Reads can hit on the L1 and persist across waves.<br>GLC = 1 Reads miss the L1 and force fetch to L2. No L1 persistence across waves.<br>**WRITE:**<br>GLC = 0 Writes miss the L1, write through to L2, and persist in L1 across wavefronts.<br>GLC = 1 Writes miss the L1, write through to L2. No persistence across wavefronts.<br>**ATOMIC:**<br>GLC = 0 Previous data value is not returned. No L1 persistence across wavefronts.<br>GLC = 1 Previous data value is returned. No L1 persistence across wavefronts.|
|SLC|1|System Level Coherent. When set, sets "streaming" mode in the L2 cache which should be<br>used for non-temopora|
|ACC|1|VDATA is Accumulation VGPR|
|reserved|1|must be set to zero a NACK, which causes a VGPR write into DST+1 (first GPR after all fetch-<br>dest GPRs).|
|LWE|1|LOD Warning Enable. When set to 1, a texture fetch may return "LOD_CLAMPED=1".|
|A16|1|Address components are 16-bits (instead of the usual 32 bits). When set, all address<br>components are 16 bits (packed into two per Dword), except:<br>Texel offsets (three 6-bit uint packed into one Dword).<br>PCF reference (for _C instructions).<br>Address components are 16-bit uint for image ops without sampler; 16-bit float with sampler.|
|D16|1|VGPR-Data-16bit. On loads, convert data in memory to 16-bit format before storing it in VGPRs.<br>For stores, convert 16-bit data in VGPRs to 32 bits before going to memory. Whether the data is<br>treated as float or int is decided by NFMT. Allowed only with these opcodes:<br>IMAGE_SAMPLE<br>IMAGE_LOAD<br>IMAGE_LOAD_MIP<br>IMAGE_STORE<br>IMAGE_STORE_MIP|



## **9.3. Image Opcodes with No Sampler**

For image opcodes with no sampler, all VGPR address values are taken as uint. For cubemaps, face_id = slice * 6 + face.

The table below shows the contents of address VGPRs for the various image opcodes.

_Table 39. Image Opcodes with No Sampler_

|**Image Opcode**|**Acnt**|**dim**|**VGPRn**|**VGPRn+1**|**VGPRn+2**|**VGPRn+3**|
|---|---|---|---|---|---|---|
|**(Resource w/o Sampler)**|||||||
|get_resinfo|0|Any|mipid||||



9.3. Image Opcodes with No Sampler

70 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Image Opcode**<br>**(Resource w/o Sampler)**|**Acnt**|**dim**|**VGPRn**|**VGPRn+1**|**VGPRn+2**|**VGPRn+3**|
|---|---|---|---|---|---|---|
|load / store / atomics|0|1D|x||||
||1|1D Array|x|slice|||
||1|2D|x|y|||
||2|2D MSAA|x|y|fragid||
||2|2D Array|x|y|slice||
||3|2D Array MSAA|x|y|slice|fragid|
||2|3D|x|y|z||
||2|Cube|x|y|face_id||
|load_mip / store_mip|1|1D|x|mipid|||
||2|1D Array|x|slice|mipid||
||2|2D|x|y|mipid||
||3|2D Array|x|y|slice|mipid|
||3|3D|x|y|z|mipid|
||3|Cube|x|y|face_id|mipid|



## **9.4. Image Opcodes with a Sampler**

For image opcodes with a sampler, all VGPR address values are taken as float. For cubemaps, face_id = slice * 8 + face.

_Table 40. Image Opcodes with Sampler_

|**Image Opcode**<br>**(w/ Sampler)**|**Acnt**|**dim**|**VGPRn**|**VGPRn+1**|**VGPRn+2**|**VGPRn+3**|
|---|---|---|---|---|---|---|
|sample|0|1D|x||||
||1|1D Array|x|slice|||
||1|2D|x|y|||
||2|2D interlaced|x|y|field||
||2|2D Array|x|y|slice||
||2|3D|x|y|z||
||2|Cube|x|y|face_id||



### **9.4.1. VGPR Usage**

Address: The address consists of up to four parts:

9.4. Image Opcodes with a Sampler

71 of 267

"AMD Instinct MI200" Instruction Set Architecture



These are all packed into consecutive VGPRs.

|**Image Dim**|**Vgpr N**|**N+1**|**N+2**|**N+3**|**N+4**|**N+5**|
|---|---|---|---|---|---|---|
|1D|DX/DH|DX/DV|-|-|-|-|
|2D|DX/DH|DY/DH|DX/DV|DY/DV|-|-|
|3D|DX/DH|DY/DH|DZ/DH|DX/DV|DY/DV|DZ/DV|



- Body: One to four Dwords, as defined by the table: Image Opcodes with a Sampler Address components are X,Y,Z,W with X in VGPR_M, Y in VGPR_M+1, etc. The number of components in "body" is the value of the ACNT field in the table, plus one.

- Data: Written from, or returned to, one to four consecutive VGPRs. The amount of data read or written is determined by the DMASK field of the instruction.

- Reads: DMASK specifies which elements of the resource are returned to consecutive VGPRs. The texture system reads data from memory and based on the data format expands it to a canonical RGBA form, filling in zero or one for missing components. Then, DMASK is applied, and only those components selected are returned to the shader.

- Writes: When writing an image object, it is only possible to write an entire element (all components), not just individual components. The components come from consecutive VGPRs, and the texture system fills in the value zero for any missing components of the image’s data format; it ignores any values that are not part of the stored data format. For example, if the DMASK=1001, the shader sends Red from VGPR_N, and Alpha from VGPR_N+1, to the texture unit. If the image object is RGB, the texel is overwritten with Red from the VGPR_N, Green and Blue set to zero, and Alpha from the shader ignored.

- Atomics: Image atomic operations are supported only on 32- and 64-bit-per pixel surfaces. The surface data format is specified in the resource constant. Atomic operations treat the element as a single component of 32- or 64-bits. For atomic operations, DMASK is set to the number of VGPRs (Dwords) to send to the texture unit. DMASK legal values for atomic image operations: no other values of DMASK are legal.

- 0x1 = 32-bit atomics except cmpswap. 0x3 = 32-bit atomic cmpswap. 0x3 = 64-bit atomics except cmpswap.

- 0xf = 64-bit atomic cmpswap.

- Atomics with Return: Data is read out of the VGPR(s), starting at VDATA, to supply to the atomic operation. If the atomic returns a value to VGPRs, that data is returned to those same VGPRs starting at VDATA.

- D16 Instructions: Load-format and store-format instructions also come in a "d16" variant. For stores, each 32-bit VGPR holds two 16-bit data elements that are passed to the texture unit. The texture unit converts them to the texture format before writing to memory. For loads, data returned from the texture unit is converted to 16 bits, and a pair of data are stored in each 32- bit VGPR (LSBs first, then MSBs). The DMASK bit represents individual 16- bit elements; so, when DMASK=0011 for an image-load, two 16-bit components are loaded into a single 32-bit VGPR.

9.4. Image Opcodes with a Sampler

72 of 267

"AMD Instinct MI200" Instruction Set Architecture



### **9.4.2. Image Resource**

The image resource (also referred to as T#) defines the location of the image buffer in memory, its dimensions, tiling, and data format. These resources are stored in four or eight consecutive SGPRs and are read by MIMG instructions.

_Table 41. Image Resource Definition_

|**Bits**|**Size**|**Name**|**Comments**|
|---|---|---|---|
|**128-bit Re**|**source: 1D**|**-tex, 2d-tex, 2d-msaa (**|**multi-sample auto-aliasing)**|
|39:0|40|base address|256-byte aligned. Also used for fmask-ptr.|
|51:40|12|min lod|4.8 (four uint bits, eight fraction bits) format.|
|57:52|6|data format|Number of comps, number of bits/comp.|
|61:58|4|num format|Numeric format.|
|62|1|NV|Non-volatile (0=volatile)|
|77:64|14|width|width-1 of mip0 in texels|
|91:78|14|height|height-1 of mip0 in texels|
|94:92|3|perf modulation|Scales sampler’s perf_z, perf_mip, aniso_bias, lod_bias_sec.|
|98:96|3|dst_sel_x|0 = 0, 1 = 1, 4 = R, 5 = G, 6 = B, 7 = A.|
|101:99|3|dst_sel_y||
|104:102|3|dst_sel_z||
|107:105|3|dst_sel_w||
|111:108|4|base level|largest mip level in the resource view. For msaa, set to zero.|
|115:112|4|last level|For msaa, holds number of samples|
|120:116|5|Tiling index|Lookuptable: 32 x 16<br>bank_width[2], bank_height[2], num_banks[2], tile_split[2],<br>macro_tile_aspect[2], micro_tile_mode[2], array_mode[4].|
|127:124<br>**256-bit Re**|4<br>**source: 1d**|type<br>**-array, 2d-array, 3d, cu**|0 = buf, 8 = 1d, 9 = 2d, 10 = 3d, 11 = cube, 12 = 1d-array, 13 = 2d-<br>array, 14 = 2d-msaa, 15 = 2d-msaa-array. 1-7 are reserved.<br>**bemap, MSAA**|
|140:128|13|depth|depth-1 of mip0 for 3d map|
|156:141|16|pitch|In texel units.|
|159:157|3|border color swizzle|Specifies the channel ordering for border color independent of the T#<br>dst_sel fields. 0=xyzw, 1=xwyz, 2=wqyx, 3=wxyz, 4=zyxw, 5=yxwz|
|176:173|4|Array Pitch|array pitch for quilts, encoded as: trunc(log2(array_pitch))+1|
|184:177|8|meta data address|bits[47:40]|
|185|1|meta_linear|forces metadata surface to be linear|
|186|1|meta_pipe_aligned|maintain pipe alignment in metadata addressing|
|187|1|meta_rb_aligned|maintain RB alignment in metadata addressing|



9.4. Image Opcodes with a Sampler

73 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Bits**|**Size**|**Name**|**Comments**|
|---|---|---|---|
|191:188|4|Max Mip|Resource mipLevel-1. Describes the resource, as opposed to<br>base_level and last_level, which describes the resouce view. For<br>MSAA, holds log2(number of samples).|
|203:192|12|min LOD warn|Feedback trigger for LOD, in U4.8 format.|
|211:204|8|counter bank ID|PRT counter ID|
|212|1|LOD hardware<br>count enable|PRT hardware counter enable|
|213|1|Compression<br>Enable|enable delta color compression|
|214|1|Alpha is on MSB|Set to 1 if the surface’s component swap is not reversed (DCC)|
|215|1|Color Transform|Auto=0, none=1 (DCC)|
|255:216|40|Meta Data Address|Upper bits of meta-data address (DCC) [47:8]|



All image resource view descriptors (T#'s) are written by the driver as 256 bits.

The MIMG-format instructions have a DeclareArray (DA) bit that reflects whether the shader was expecting an array-texture or simple texture to be bound. When DA is zero, the hardware does not send an array index to the texture cache. If the texture map was indexed, the hardware supplies an index value of zero. Indices sent for non-indexed texture maps are ignored.

### **9.4.3. Image Sampler**

The sampler resource (also referred to as S#) defines what operations to perform on texture map data read by **sample** instructions. These are primarily address clamping and filter options. Sampler resources are defined in four consecutive SGPRs and are supplied to the texture cache with every sample instruction.

_Table 42. Image Sampler Definition_

|**Bits**|**Size**|**Name**|**Description**|
|---|---|---|---|
|2:0|3|clamp x|Clamp/wrap mode.|
|5:3|3|clamp y||
|8:6|3|clamp z||
|11:9|3|max aniso ratio||
|14:12|3|depth compare func||
|15|1|force unnormalized|Force address cords to be unorm.|
|18:16|3|aniso threshold||
|19|1|mc coord trunc||
|20|1|force degamma||



9.4. Image Opcodes with a Sampler

74 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Bits**|**Size**|**Name**|**Description**|
|---|---|---|---|
|26:21|6|aniso bias|u1.5.|
|27|1|trunc coord||
|28|1|disable cube wrap||
|30:29|2|filter_mode|Normal lerp, min, or max filter.|
|31|1|compat_mode|1 = new mode; 0 = legacy|
|43:32|12|min lod|u4.8.|
|55:44|12|max lod|u4.8.|
|59:56|4|perf_mip||
|63:60|4|perf z||
|77:64|14|lod bias|s5.8.|
|83:78|6|lod bias sec|s1.4.|
|85:84|2|xy mag filter|Magnification filter.|
|87:86|2|xy min filter|Minification filter.|
|89:88|2|z filter||
|91:90|2|mip filter||
|92|1|mip_point_preclamp|When mipfilter = point, add 0.5 before clamping.|
|93|1|disable_lsb_ceil|Disable ceiling logic in filter (rounds up).|
|94|1|Filter_Prec_Fix||
|95|1|Aniso_override|Disable Aniso filtering if base_level = last_level|
|107:96|12|border color ptr||
|125:108|18|unused||
|127:126|2|border color type|Opaque-black, transparent-black, white, use border color ptr.|



### **9.4.4. Data Formats**

The table below shows the image and buffer data formats:

9.4. Image Opcodes with a Sampler

75 of 267

"AMD Instinct MI200" Instruction Set Architecture





### **9.4.5. Vector Memory Instruction Data Dependencies**

When a VM instruction is issued, the address is immediately read out of VGPRs and sent to the texture cache. Any texture or buffer resources and samplers are also sent immediately. However, write-data is not immediately sent to the texture cache.

The shader developer’s responsibility to avoid data hazards associated with VMEM instructions include waiting for VMEM read instruction completion before reading data fetched from the TC (VMCNT).

This is explained in the section: Data Dependency Resolution

9.4. Image Opcodes with a Sampler

76 of 267

"AMD Instinct MI200" Instruction Set Architecture



## **9.5. Float Memory Atomics**

Floating point memory atomics are executed in LDS and in the L2 cache. They can be issued as LDS, GDS, Buffer, Flat, Global, and Scratch instructions.

This chapter explains the rules for rounding, denormals and NaN for floating point atomics.

### **9.5.1. Rounding of Float Atomics**

All float atomic ADD opcodes use "Round to Nearest-Even" rounding.

### **9.5.2. Denormal (Subnormal) Handling**

When atomics operate on floating point data, there is the possibility of the data continaing denormal numbers, or the operation producing a denormal.

Denormals: The floating point atomic instructions have the option of passing denormal values through, or flushing them to zero. This is controlled with the MODE.denorm bits which also control VALU denormal behavior. As with VALU ops, “denorm_single” affects F32 ops and “denorm_double” affects F64 and F16. Some atomics have fixed denormal handling behavior.

_LDS instructions allows denormals to be passed through or flushed to zero based on the MODE.denormal wave-state register._

- Float 16 and 32 bit Adder uses both input and output denorm flush controls from MODE

- Float 64 bit adder never flushes denorms lds_tcc_atomic_adder_f64.inf_nan_clamp=0

- Float CMP, MIN and MAX use only the “input denormal” flushing control

   - ◦Each input to the comparisons will flush the mantissa of both operands to zero before the compare if the exponent is zero and the flush denorm control is active. For Min and Max the actual result returned is the selected non-flushed input.

   - ◦CompareStore (“compare swap”) flushes the result when input denormal flushing occurs.

_Table 43. Denorm Handling Rules for Memory Ops_

|**Atomic type**|**LDS Handling**|**L2 Cache Handling**|
|---|---|---|
|PK_ADD_F16|N/A|Never Flush Denorms|
|ADD_F32|Mode|Always Flush Denorms|
|Min/MAX_F32|Mode|N/A|
|CMPST_F32|Mode|N/A|
|MIN/MAX_F64|Mode|Never Flush Denorms|
|CMPST_F64|Mode|N/A|
|ADD_F64|Never Flush Denorms|Never Flush Denorms|



9.5. Float Memory Atomics

77 of 267

"AMD Instinct MI200" Instruction Set Architecture



- “Always Flush” = flush all input denorm

- “Never Flush” = don’t flush input denorm

- “Mode” = denormal flush controlled by bit from shader’s “MODE . fp_denorm” register

- “Mode + reg” = “Mode” from above, but there exists an override register to flush output or not.

Note that MIN and MAX when flushing denormals only do it for the comparison, but the result is an unmodified copy of one of the sources. CompareStore (“compare swap”) flushes the result when input denormal flushing occurs.

### **9.5.3. NaN Handling**

Not A Number (“NaN”) is a IEEE-754 value representing a result which cannot be computed.

_There two types of NaN: quiet and signaling_

- Quiet NaN Exponent=0xFF, Mantissa MSB=1

- Singaling NaN Exponent=0xFF, Mantissa MSB=0 and at least one other mantissa bit ==1

The LDS does not produce any exception or “signal” due to a signaling NaN.

DS_ADD_F32 can create a quiet NaN, or propagate NaN from its inputs: if either input is a NaN, the output will be that same NaN, and if both inputs are NaN, the NaN from the first input is selected as the output. Signaling NaN is converted to Quiet NaN.

Floating point atomics (CMPSWAP, MIN, MAX) flush input denormals only when MODE (allow_input_denorm)=0, otherwise values are passed through without modification. When flushing, denorms will be flushed before the operation (i.e. before the comparison).

_FP Max Selection Rules:_

if (src0 == SNaN) result = QNaN (src0) else if (src1 == SNaN) result = QNaN (src1) else result = larger of (src0, src1)

“Larger” order from smallest to largest: QNaN, -inf, -float, -denorm, -0, +0, +denorm, +float, +inf

_FP Min Selection Rules:_

if (src0 == SNaN) result = QNaN (src0) else if (src1 == SNaN) result = QNaN (src1) else result = smaller of (src0, src1)

“Smaller” order from smallest to largest: -inf, -float, -denorm, -0, +0, +denorm, +float, +inf, QNaN

9.5. Float Memory Atomics

78 of 267

"AMD Instinct MI200" Instruction Set Architecture



- _FP Compare Swap: only swap if the compare condition (==) is true, treating +0 and -0 as equal_ doSwap = (src0 != NaN) && (src1 != NaN) && (src0 == src1) // allow +0 == -0

_Float Add rules:_

1. -INF + INF = QNAN (mantissa is all zeros except MSB)

2. -+/-INF + NAN = QNAN (NAN input is copied to output but made quiet NAN)

3. -0 + 0 = +0

4. INF + (float, +0, -0) = INF, with infinity sign preserved

5. NaN + NaN = SRC0’s NaN, converted to QNaN

9.5. Float Memory Atomics

79 of 267
