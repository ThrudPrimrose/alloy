---
name: docs-md-gfx90a-04-chapter-1-introduction
description: "AMD CDNA2 ISA: Chapter 1. Introduction (vendor documentation for AMD gfx90a (CDNA2))."
when: "when you need AMD CDNA2 ISA: Chapter 1. Introduction while writing a AMD gfx90a (CDNA2) kernel."
---

"AMD Instinct MI200" Instruction Set Architecture



# **Chapter 1. Introduction**

AMD CDNA processors implement a parallel micro-architecture that is designed to provide an excellent platform for general-purpose data parallel applications. Data-intensive applications that require high bandwidth or are computationally intensive are a candidate for running on an AMD CDNA processor.

The figure below shows a block diagram of the AMD CDNA Generation series processors



_Figure 1. AMD CDNA Generation Series Block Diagram_

The CDNA device includes a data-parallel processor (DPP) array, a command processor, a memory controller, and other logic (not shown). The CDNA command processor reads commands that the host has written to memory-mapped CDNA registers in the system-memory address space. The command processor sends hardware-generated interrupts to the host when the command is completed. The CDNA memory controller has direct access to all CDNA device memory and the host-specified areas of system memory. To satisfy read and write requests, the memory controller performs the functions of a direct-memory access (DMA) controller, including computing memory-address offsets based on the format of the requested data in memory. In the CDNA environment, a complete application includes two parts:

- a program running on the host processor, and

- programs, called kernels, running on the CDNA processor.

The CDNA programs are controlled by host commands that

4 of 267

"AMD Instinct MI200" Instruction Set Architecture



- set CDNA internal base-address and other configuration registers,

- specify the data domain on which the CDNA GPU is to operate,

- invalidate and flush caches on the CDNA GPU, and

- cause the CDNA GPU to begin execution of a program.

The CDNA driver program runs on the host.

The DPP array is the heart of the CDNA processor. The array is organized as a set of compute unit pipelines, each independent from the others, that are designed to operate in parallel on streams of floating-point or integer data. The compute unit pipelines can process data or, through the memory controller, transfer data to, or from, memory. Computation in a compute unit pipeline can be made conditional. Outputs written to memory can also be made conditional.

When it receives a request, the compute unit pipeline loads instructions and data from memory, begins execution, and continues until the end of the kernel. As kernels are running, the CDNA hardware automatically fetches instructions from memory into on-chip caches; CDNA software plays no role in this. CDNA kernels can load data from off-chip memory into on-chip generalpurpose registers (GPRs) and caches.

The AMD CDNA devices can detect floating point exceptions and can generate interrupts. In particular, they can detect IEEE floating-point exceptions in hardware; these can be recorded for post-execution analysis. The software interrupts shown in the previous figure from the command processor to the host represent hardware-generated interrupts for signaling commandcompletion and related management functions.

The CDNA processor is designed to hide memory latency by keeping track of potentially hundreds of work-items in different stages of execution, and by overlapping compute operations with memory-access operations.

## **1.1. Terminology**

_Table 1. Basic Terms_

|**Term**|**Description**|
|---|---|
|CDNA Processor|The Graphics Core Next shader processor is a scalar and vector ALU capable of running<br>complex programs on behalf of a wavefront.|
|Dispatch|A dispatch launches a 1D, 2D, or 3D grid of work to the CDNA processor array.|
|Workgroup|A workgroup is a collection of wavefronts that have the ability to synchronize with each other<br>quickly; they also can share data through the Local Data Share.|
|Wavefront|A collection of 64 work-items that execute in parallel on a single CDNA processor.|
|Work-item|A single element of work: one element from the dispatch grid, or in graphics a pixel or vertex.|
|Literal Constant|A 32-bit integer or float constant that is placed in the instruction stream.|
|Scalar ALU (SALU)|The scalar ALU operates on one value per wavefront and manages all control flow.|



1.1. Terminology

5 of 267

"AMD Instinct MI200" Instruction Set Architecture



|**Term**|**Description**|
|---|---|
|Vector ALU (VALU)|The vector ALU maintains Vector GPRs that are unique for each work item and execute<br>arithmetic operations uniquely on each work-item.|
|Microcode format|The microcode format describes the bit patterns used to encode instructions. Each<br>instruction is either 32 or 64 bits.|
|Instruction|An instruction is the basic unit of the kernel. Instructions include: vector ALU, scalar ALU,<br>memory transfer, and control flow operations.|
|Quad|A quad is a 2x2 group of screen-aligned pixels. This is relevant for sampling texture maps.|
|Texture Sampler (S#)|A texture sampler is a 128-bit entity that describes how the vector memory system reads and<br>samples (filters) a texture map.|
|Texture Resource<br>(T#)|A texture resource descriptor describes an image in memory: address, data format, stride,<br>etc.|
|Buffer Resource (V#)|A buffer resource descriptor describes a buffer in memory: address, data format, stride, etc.|



1.1. Terminology

6 of 267
