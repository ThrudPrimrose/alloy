---
name: docs-md-gfx90a-07-chapter-4-program-flow-control
description: "AMD CDNA2 ISA: Chapter 4. Program Flow Control (vendor documentation for AMD gfx90a (CDNA2))."
when: "when you need AMD CDNA2 ISA: Chapter 4. Program Flow Control while writing a AMD gfx90a (CDNA2) kernel."
---

"AMD Instinct MI200" Instruction Set Architecture



# **Chapter 4. Program Flow Control**

All program flow control is programmed using scalar ALU instructions. This includes loops, branches, subroutine calls, and traps. The program uses SGPRs to store branch conditions and loop counters. Constants can be fetched from the scalar constant cache directly into SGPRs.

## **4.1. Program Control**

The instructions in the table below control the priority and termination of a shader program, as well as provide support for trap handlers.

_Table 7. Control Instructions_

|**Instructions**|**Description**|
|---|---|
|S_ENDPGM|Terminates the wavefront. It can appear anywhere in the kernel and can appear multiple<br>times.|
|S_ENDPGM_SAVED|Terminates the wavefront due to context save. It can appear anywhere in the kernel and can<br>appear multiple times.|
|S_NOP|Does nothing; it can be repeated in hardware up to eight times.|
|S_TRAP|Jumps to the trap handler.|
|S_RFE|Returns from the trap handler|
|S_SETPRIO|Modifies the priority of this wavefront: 0=lowest, 3 = highest.|
|S_SLEEP|Causes the wavefront to sleep for 64 - 8128 clock cycles.|
|S_SENDMSG|Sends a message (typically an interrupt) to the host CPU.|



## **4.2. Branching**

Branching is done using one of the following scalar ALU instructions.

_Table 8. Branch Instructions_

|**Instructions**|**Description**|
|---|---|
|S_BRANCH|Unconditional branch.|
|S_CBRANCH_<test>|Conditional branch. Branch only if <test> is true. Tests are VCCZ, VCCNZ,<br>EXECZ, EXECNZ, SCCZ, and SCCNZ.|
|S_CBRANCH_CDBGSYS|Conditional branch, taken if the COND_DBG_SYS status bit is set.|
|S_CBRANCH_CDBGUSER|Conditional branch, taken if the COND_DBG_USER status bit is set.|
|S_CBRANCH_CDBGSYS_AND_US<br>ER|Conditional branch, taken only if both COND_DBG_SYS and<br>COND_DBG_USER are set.|
|S_SETPC|Directly set the PC from an SGPR pair.|



4.1. Program Control

21 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Instructions**|**Description**|
|---|---|
|S_SWAPPC|Swap the current PC with an address in an SGPR pair.|
|S_GETPC|Retrieve the current PC value (does not cause a branch).|
|S_CBRANCH_FORK and<br>S_CBRANCH_JOIN|Conditional branch for complex branching.|
|S_SETVSKIP|Set a bit that causes all vector instructions to be ignored. Useful alternative<br>to branching.|
|S_CALL_B64|Jump to a subroutine, and save return address. SGPR_pair = PC+4; PC =<br>PC+4+SIMM16*4.|



For conditional branches, the branch condition can be determined by either scalar or vector operations. A scalar compare operation sets the Scalar Condition Code (SCC), which then can be used as a conditional branch condition. Vector compare operations set the VCC mask, and VCCZ or VCCNZ then can be used to determine branching.

## **4.3. Workgroups**

Work-groups are collections of wavefronts running on the same compute unit which can synchronize and share data. Up to 16 wavefronts (1024 work-items) can be combined into a work-group. When multiple wavefronts are in a workgroup, the S_BARRIER instruction can be used to force each wavefront to wait until all other wavefronts reach the same instruction; then, all wavefronts continue. Any wavefront can terminate early using S_ENDPGM, and the barrier is considered satisfied when the remaining live waves reach their barrier instruction.

## **4.4. Data Dependency Resolution**

Shader hardware resolves most data dependencies, but a few cases must be explicitly handled by the shader program. In these cases, the program must insert S_WAITCNT instructions to ensure that previous operations have completed before continuing.

The shader has three counters that track the progress of issued instructions. S_WAITCNT waits for the values of these counters to be at, or below, specified values before continuing.

These allow the shader writer to schedule long-latency instructions, execute unrelated work, and specify when results of long-latency operations are needed.

Instructions of a given type return in order, but instructions of different types can complete outof-order. For example, both GDS and LDS instructions use LGKM_cnt, but they can return outof-order.

- VM_CNT: Vector memory count. Determines when memory reads have returned data to VGPRs, or memory writes have completed.

4.3. Workgroups

22 of 267

"AMD Instinct MI200" Instruction Set Architecture



   - ◦Incremented every time a vector-memory read or write (MIMG, MUBUF, or MTBUF format) instruction is issued.

   - ◦Decremented for reads when the data has been written back to the VGPRs, and for writes when the data has been written to the L2 cache. Ordering: Memory reads and writes return in the order they were issued, including mixing reads and writes.

- LGKM_CNT: (LDS, GDS, (K)constant, (M)essage) Determines when one of these lowlatency instructions have completed.

   - ◦Incremented by 1 for every LDS or GDS instruction issued, as well as by Dword-count for scalar-memory reads. For example, s_memtime counts the same as an s_load_dwordx2.

   - ◦Decremented by 1 for LDS/GDS reads or atomic-with-return when the data has been returned to VGPRs.

   - ◦Incremented by 1 for each S_SENDMSG issued. Decremented by 1 when message is sent out.

   - ◦Decremented by 1 for LDS/GDS writes when the data has been written to LDS/GDS.

   - ◦Decremented by 1 for each Dword returned from the data-cache (SMEM). **Ordering:**

      - ▪Instructions of different types are returned out-of-order.

      - ▪Instructions of the same type are returned in the order they were issued, except scalar-memory-reads, which can return out-of-order (in which case only S_WAITCNT 0 is the only legitimate value).

- EXP_CNT: VGPR-export count.

- Determines when data has been read out of the VGPR and sent to GDS, at which time it is safe to overwrite the contents of that VGPR.

   - ◦Incremented when an GDS instruction is issued from the wavefront buffer.

   - ◦Decremented for GDS when the last cycle of the GDS instruction is granted and executed (VGPRs read out).

## **4.5. Manually Inserted Wait States (NOPs)**

The hardware does not check for the following dependencies; they must be resolved by inserting NOPs or independent instructions.

_Table 9. Required Software-inserted Wait States_

|**First Instruction**|**Second Instruction**|**Wait**|**Notes**|
|---|---|---|---|
|S_SETREG <*>|S_GETREG <same reg>|2||
|S_SETREG <*>|S_SETREG <same reg>|2||
|SET_VSKIP|S_GETREG MODE|2|Reads VSKIP from MODE.|
|S_SETREG MODE.vskip|any vector op|2|Requires two nops or non-vector<br>instructions.|



4.5. Manually Inserted Wait States (NOPs)

23 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**First Instruction**|**Second Instruction**|**Wait**|**Notes**|
|---|---|---|---|
|VALU that sets VCC or EXEC|VALU that uses EXECZ or<br>VCCZ as a data source|5||
|VALU writes SGPR/VCC (readlane,<br>cmp, add/sub, div_scale)|V_{READ,WRITE}LANE using<br>that SGPR/VCC as the lane<br>select|4||
|VALU writes VCC (including<br>v_div_scale)|V_DIV_FMAS|4||
|FLAT_STORE_X3<br>FLAT_STORE_X4<br>FLAT_ATOMIC_{F}CMPSWAP_X2<br>BUFFER_STORE_DWORD_X3<br>BUFFER_STORE_DWORD_X4<br>BUFFER_STORE_FORMAT_XYZ<br>BUFFER_STORE_FORMAT_XYZW<br>BUFFER_ATOMIC_{F}CMPSWAP_X2<br>IMAGE_STORE_* > 64 bits<br>IMAGE_ATOMIC_{F}CMPSWAP > +<br>64bits|Write VGPRs holding writedata<br>from those instructions.|1|BUFFER_STORE_* operations<br>that use an SGPR for "offset" do<br>not require any wait states.<br>IMAGE_STORE_* and<br>IMAGE_{F}CMPSWAP* ops with<br>more than two DMASK bits set<br>require this one wait state. Ops<br>that use a 256-bit T# do not<br>need a wait state.|
|VALU writes SGPR|VMEM reads that SGPR|5|Hardware assumes that there is<br>no dependency here. If the<br>VALU writes the SGPR that is<br>used by a VMEM, the user must<br>add five wait states.|
|SALU writes M0|GDS, S_SENDMSG|1||
|VALU writes VGPR|VALU DPP reads that VGPR|2||
|VALU writes EXEC|VALU DPP op|5|ALU does not forward EXEC to<br>DPP.|
|Mixed use of VCC: alias vs<br>SGPR#<br>v_readlane, v_readfirstlane<br>v_cmp<br>v_add*_i/u_<br>_v_sub*_i/u_<br>_v_div_scale_* (writes vcc)|VALU which reads VCC as a<br>constant (not as a carry-in which<br>is 0 wait states).|1|VCC can be accessed by name<br>or by the logical SGPR which<br>holds VCC. The data<br>dependency check logic does<br>not understand that these are<br>the same register and do not<br>prevent races.|
|S_SETREG TRAPSTS|RFE, RFE_restore|1||
|SALU writes M0|LDS "add-TID" instruction,<br>buffer_store_LDS_dword,<br>scratch or global with LDS = 1 or<br>LDS_direct|1||
|SALU writes M0|S_MOVEREL|1||



## **4.6. Arbitrary Divergent Control Flow**

In the CDNA architecture, conditional branches are handled in one of the following ways.

4.6. Arbitrary Divergent Control Flow

24 of 267

"AMD Instinct MI200" Instruction Set Architecture



1. S_CBRANCH This case is used for simple control flow, where the decision to take a branch is based on a previous compare operation. This is the most common method for conditional branching.

2. S_CBRANCH_I/G_FORK and S_CBRANCH_JOIN This method, intended for complex, irreducible control flow graphs, is described in the rest of this section. The performance of this method is lower than that for S_CBRANCH on simple flow control; use it only when necessary.

Conditional Branch (CBR) graphs are grouped into self-contained code blocks, denoted by FORK at the entrance point, and JOIN and the exit point. The shader compiler must add these instructions into the code. This method uses a six-deep stack and requires three SGPRs for each fork/join block. Fork/Join blocks can be hierarchically nested to any depth (subject to SGPR requirements); they also can coexist with other conditional flow control or computed jumps.



_Figure 3. Example of Complex Control Flow Graph_

The register requirements per wavefront are:

- CSP [2:0] - control stack pointer.

- Six stack entries of 128-bits each, stored in SGPRS: { exec[63:0], PC[47:2] }

This method compares how many of the 64 threads go down the PASS path instead of the FAIL path; then, it selects the path with the fewer number of threads first. This means at most 50% of the threads are active, and this limits the necessary stack depth to Log264 = 6.

The following pseudo-code shows the details of CBRANCH Fork and Join operations.

4.6. Arbitrary Divergent Control Flow

25 of 267

"AMD Instinct MI200" Instruction Set Architecture



**S_CBRANCH_G_FORK** arg0, arg1 // arg1 is an sgpr-pair which holds 64bit (48bit) target address **S_CBRANCH_I_FORK** arg0, #target_addr_offset[17:2] // target_addr_offset: 16b signed immediate offset // PC: in this pseudo-code is pointing to the cbranch_*_fork instruction mask_pass = SGPR[arg0] & exec mask_fail = ~SGPR[arg0] & exec if (mask_pass == exec) I_FORK : PC += 4 + target_addr_offset G_FORK: PC = SGPR[arg1] else if (mask_fail == exec) PC += 4 else if (bitcount(mask_fail) < bitcount(mask_pass)) exec = mask_fail I_FORK : SGPR[CSP*4] = { (pc + 4 + target_addr_offset), mask_pass } G_FORK: SGPR[CSP*4] = { SGPR[arg1], mask_pass } CSP++ PC += 4 else exec = mask_pass SGPR[CSP*4] = { (pc+4), mask_fail } CSP++ I_FORK : PC += 4 + target_addr_offset G_FORK: PC = SGPR[arg1] **S_CBRANCH_JOIN arg0** if (CSP == SGPR[arg0]) // SGPR[arg0] holds the CSP value when the FORK started PC += 4 // this is the 2nd time to JOIN: continue with pgm else CSP -- // this is the 1st time to JOIN: jump to other FORK path {PC, EXEC} = SGPR[CSP*4] // read 128-bits from 4 consecutive SGPRs

4.6. Arbitrary Divergent Control Flow

26 of 267
