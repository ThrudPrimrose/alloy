---
name: docs-md-sm90-01-introduction
description: "PTX ISA 9.4: Introduction (vendor documentation for NVIDIA sm90 (PTX))."
when: "when you need PTX ISA 9.4: Introduction while writing a kernel for NVIDIA sm90 (PTX)."
---

# Chapter 1. Introduction

This document describes PTX, a low-level _parallel thread execution_ virtual machine and instruction set architecture (ISA). PTX exposes the GPU as a data-parallel computing _device_ .

## 1.1. Scalable Data-Parallel Computing using GPUs

Driven by the insatiable market demand for real-time, high-definition 3D graphics, the programmable GPU has evolved into a highly parallel, multithreaded, many-core processor with tremendous computational horsepower and very high memory bandwidth. The GPU is especially well-suited to address problems that can be expressed as data-parallel computations - the same program is executed on many data elements in parallel - with high arithmetic intensity - the ratio of arithmetic operations to memory operations. Because the same program is executed for each data element, there is a lower requirement for sophisticated flow control; and because it is executed on many data elements and has high arithmetic intensity, the memory access latency can be hidden with calculations instead of big data caches.

Data-parallel processing maps data elements to parallel processing threads. Many applications that process large data sets can use a data-parallel programming model to speed up the computations. In 3D rendering large sets of pixels and vertices are mapped to parallel threads. Similarly, image and media processing applications such as post-processing of rendered images, video encoding and decoding, image scaling, stereo vision, and pattern recognition can map image blocks and pixels to parallel processing threads. In fact, many algorithms outside the field of image rendering and processing are accelerated by data-parallel processing, from general signal processing or physics simulation to computational finance or computational biology.

_PTX_ defines a virtual machine and ISA for general purpose parallel thread execution. PTX programs are translated at install time to the target hardware instruction set. The PTX-to-GPU translator and driver enable NVIDIA GPUs to be used as programmable parallel computers.

**9**

**PTX ISA, Release 9.4**

## 1.2. Goals of PTX

_PTX_ provides a stable programming model and instruction set for general purpose parallel programming. It is designed to be efficient on NVIDIA GPUs supporting the computation features defined by the NVIDIA Tesla architecture. High level language compilers for languages such as CUDA and C/C++ generate PTX instructions, which are optimized for and translated to native target-architecture instructions.

The goals for PTX include the following:

- Provide a stable ISA that spans multiple GPU generations.

- Achieve performance in compiled applications comparable to native GPU performance.

- Provide a machine-independent ISA for C/C++ and other compilers to target.

- Provide a code distribution ISA for application and middleware developers.

- Provide a common source-level ISA for optimizing code generators and translators, which map PTX to specific target machines.

- Facilitate hand-coding of libraries, performance kernels, and architecture tests.

- Provide a scalable programming model that spans GPU sizes from a single unit to many parallel units.

## 1.3. PTX ISA Version 9.4

PTX ISA version 9.4 introduces the following new features:

- Adds support for sm_107 target architecture.

- Adds support for target sm_107f that supports family-specific features.

- Adds support for target sm_107a that supports architecture-specific features.

- Adds support for instruction types .u8x4 , .s8x4 , .u16x2 , .s16x2 for set instruction.

- Adds support for .pzo qualifier for cvt instruction.

- Adds support for .rz rounding mode for cvt instruction with .e4m3x2 , .e5m2x2 , .e2m3x2 , . e3m2x2 , .e2m1x2 destination types.

- Adds support for .multicast::cluster::32b qualifier for mbarrier.expect_tx , mbarrier.complete_tx , mbarrier.arrive , mbarrier.arrive_drop , cp.async.bulk , cp.async.bulk.tensor and tcgen05.commit instructions.

- Adds support for .sync_restrict::shared::read::mma::a qualifier for tcgen05.commit instruction.

- Adds support for .level::eviction_priority qualifier for cp.async.bulk.prefetch and cp.async.bulk.prefetch.tensor instructions.

- Adds support for applypriority.async.bulk and applypriority.async.bulk.tensor instructions.

- Adds support for .override::global_address and .override_attribute qualifiers for cp.async.bulk.tensor , cp.reduce.async.bulk.tensor , cp.async.bulk.prefetch. tensor instructions.

**Chapter 1. Introduction**

**10**

**PTX ISA, Release 9.4**

- Adds support for .im2col_no_offs::w qualifier for cp.async.bulk.tensor and cp. reduce.async.bulk.tensor instructions.

- Adds support for .spcompress qualifier for tcgen05.ld and tcgen05.ld.red instructions.

- Adds support for spcompress and spdecompress instructions.

- Adds support for .ue5m3x2 instruction type for cvt instruction.

- Adds support for .scaled::n1::ue8m0 qualifier for cvt instruction.

- Adds UE5M3 as scale type for tcgen05.mma and tcgen05.mma.sp instructions.

- Adds support for .kind::ti16 qualifier for tcgen05.mma , tcgen05.mma.sp , tcgen05.mma. ws , tcgen05.mma.ws.sp instructions.

- Adds support for add , sub , mul and fma instructions with .f16x2 / .bf16x2 / .f32x2 types.

- Adds support for add , sub , mul and fma instructions with FP8/FP6/FP4 x4 packed types.

- Adds support for .exclusive qualifier for tcgen05.alloc and tcgen05.dealloc instructions.

- Adds support for .phase_type::* qualifier for mbarrier.test_wait and mbarrier. try_wait instructions.

- Adds support for reportPredicate and reportValue operands for mbarrier.test_wait and mbarrier.try_wait instructions.

- Adds support for .layout qualifier for mbarrier instructions and support for mbarrier. check_layout instruction.

- Adds support for .report_mechanism qualifier for cp.async.bulk and cp.async.bulk. tensor instructions.

- Adds support for .decompress::lut::b qualifier for tcgen05.mma instruction.

- Adds support for .collector::b::* qualifier for tcgen05.mma instruction.

- Adds support for .loc_intermediate directive and .nv_intermediate_source_section construct for intermediate IR source location mapping.

- Adds support for .valid_addr and .L1::32B qualifiers for prefetch instruction.

- Adds support for .noftz qualifier with .f32 type for atom , red , cp.reduce.async.bulk , and multimem.cp.reduce.async.bulk instructions.

- Adds support for .proxy::readonly qualifier for ld instruction.

- Adds support for .minperctamemory directive and %perctamemoryoffset , %perctamemorysize special registers for per-CTA global memory.

- Adds support for .s8.s4 types for ldmatrix instruction for .m8n16 shape.

- Adds support for .sync_restrict::shared::cluster::read qualifier for fence.proxy. async::generic instruction.

- Adds support for .acquire and .release qualifiers with .alias qualifier for fence.proxy instruction.

- Adds support for fabric.try_get.async.tensor , fabric.try_put.async.tensor , and fabric.try_red.async.tensor instructions.

- Adds support for fabric.try_atom instruction.

- Adds support for createpolicy.range.fabric instruction.

**1.3. PTX ISA Version 9.4**

**11**

**PTX ISA, Release 9.4**

- Adds support for .level::cache_hint qualifier for fabric.try_get , fabric.try_put , and fabric.try_red instructions.

## 1.4. Document Structure

The information in this document is organized into the following Chapters:

- _Programming Model_ outlines the programming model.

- _PTX Machine Model_ gives an overview of the PTX virtual machine model.

- _Syntax_ describes the basic syntax of the PTX language.

- _State Spaces, Types, and Variables_ describes state spaces, types, and variable declarations.

- _Instruction Operands_ describes instruction operands.

- _Abstracting the ABI_ describes the function and call syntax, calling convention, and PTX support for abstracting the _Application Binary Interface (ABI)_ .

- _Instruction Set_ describes the instruction set.

- _Special Registers_ lists special registers.

- _Directives_ lists the assembly directives supported in PTX.

- _Release Notes_ provides release notes for PTX ISA versions 2.x and beyond.

### **References**

- 754-2008 IEEE Standard for Floating-Point Arithmetic. ISBN 978-0-7381-5752-8, 2008. http://ieeexplore.ieee.org/servlet/opac?punumber=4610933

- The OpenCL Specification, Version: 1.1, Document Revision: 44, June 1, 2011. http://www.khronos.org/registry/cl/specs/opencl-1.1.pdf

- CUDA Programming Guide.

https://docs.nvidia.com/cuda/cuda-programming-guide/index.html

- CUDA Dynamic Parallelism Programming Guide.

https://docs.nvidia.com/cuda/cuda-programming-guide/04-special-topics/dynamic-parallelism. html

- CUDA Atomicity Requirements.

https://nvidia.github.io/cccl/libcudacxx/extended_api/memory_model.html#atomicity

- PTX Writers Guide to Interoperability.

https://docs.nvidia.com/cuda/ptx-writers-guide-to-interoperability/index.html

**Chapter 1. Introduction**

**12**
