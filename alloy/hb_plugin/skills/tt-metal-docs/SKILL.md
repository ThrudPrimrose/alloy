---
name: tt-metal-docs
description: "The tt-metal v0.63.0 documentation on writing kernels: METALIUM_GUIDE.md and the tt-metalium pages on the programming model, tiles, memory, compute engines, the examples and the kernel APIs."
when: before writing any Tensix kernel, to learn the programming model and the kernel APIs.
---

# tt-metal v0.63.0 documentation on writing kernels

## Source: METALIUM_GUIDE.md

# TT Architecture and Metalium Guide

## Table of Contents

- [Table of Contents](#table-of-contents)
- [Executive Summary](#executive-summary)
- [Tenstorrent Architecture Overview](#tenstorrent-architecture-overview)
  - [SRAM, interleaved and shared buffers](#sram-interleaved-and-shared-buffers)
  - [Native tile based computing](#native-tile-based-computing)
  - [Where is the cache hierarchy](#where-is-the-cache-hierarchy)
  - [Tenstorrent hardware for GPU experts](#tenstorrent-hardware-for-gpu-experts)
  - [Tenstorrent hardware for CPU experts](#tenstorrent-hardware-for-cpu-experts)
  - [Scaling beyond one chip](#scaling-beyond-one-chip)
- [TT-Metalium](#tt-metalium)
  - [Running code on device](#running-code-on-device)
  - [Register control and Data Flow within the Compute Kernels](#register-control-and-data-flow-within-the-compute-kernels)
  - [Compute APIs](#compute-apis)
  - [Fast dispatch](#fast-dispatch)
  - [SPMD in Metalium](#spmd-in-metalium)

## Executive Summary

This guide introduces developers to Tenstorrent's AI accelerator (called the Tensix Processor) architecture and the TT-Metalium™ programming model. Unlike traditional GPUs that rely on massive thread parallelism, Tensix Processors use a grid of specialized compute nodes called Tensix cores. Each Tensix core contains five small RISC-V CPUs for control and instruction dispatch, dedicated hardware units for matrix operations (FPU) and vector operations (SFPU), data packing/unpacking units, and 1.5MB of local SRAM.

The typical data flow uses Network-on-Chip (NoC) interfaces to bring data into a Tensix core, where it gets unpacked, processed by the compute units, packed, and sent out via the NoC to DRAM or other Tensix cores. This design prioritizes efficient data movement and local SRAM usage, reducing frequent DRAM access.

Programming with Metalium typically requires three kernel types per Tensix core: a **reader kernel** for data input, a **compute kernel** for calculations, and a **writer kernel** for data output. These kernels coordinate through circular buffers in SRAM. The architecture natively operates on 32×32 tiles, optimized for deep learning operations. Metalium provides APIs and abstractions (including compute and data movement) to simplify development, manage hardware resources, and ensure kernel compatibility across hardware generations.

This document covers these concepts in detail to help you develop efficient applications on Tenstorrent hardware.

## Tenstorrent Architecture Overview

The architecture Tenstorrent proposed is a different kind of AI accelerator. Unlike GPUs where the processor provides a massive pool of threads and parallelize across them. Tenstorrent chips are a grid of different nodes. Most are compute nodes called a Tensix core sprinkled with some memory, chip management and Ethernet nodes to facilitate the computation. The overall chip is then called a Tensix processor. The following image shows the logical layout of a Tensix processor, with the different nodes and their functions.

The following sections focus on the individual compute units. For precision, 'Tensix' refers specifically to Tensix cores rather than the complete Tensix processor.

The following image shows the NoC grid of the Tenstorrent Wormhole™ processor (D = DRAM, T = Tensix, E = Ethernet, A = ARC/management, P = PCIe).


Each Tensix contains 5 "Baby" RISC-V CPUs (Data Movement 0, Data Movement 1, Unpack, Math and Pack), 2 NoC interfaces, a vector unit (SFPU), a matrix unit (FPU) and a pack and unpacker, as well as 1.5MB of SRAM (called L1 in the architecture) to hold transient data and facilitates data exchange between local components. The following image is a rough block diagram of a Tensix (blue arrow = instruction dispatch, brown arrow = data transfer)


It's a lot to take in. Let's start from the obvious - RISC-V cores and the SRAM. The SRAM stores data local to the Tensix and feeds the compute engines/peripherals. Unlike GPUs, where the Streaming Processors/Compute Units (CUDA/OpenCL terms) provide the majority of computation power, the Baby RISC-V cores in Tensix primarily handle instruction dispatch and control flow. They issue commands to the NoC/Matrix/Vector/{,Un}packer units, which in turn perform the actual computational work, rather than executing the computations directly. These cores are designated "Baby" cores to reflect their design - unlike modern superscalar, vector processors, they are deliberately minimal and share more architectural similarity with classic RISC processors like the MIPS R3000 than with the complex CPUs found in contemporary phones, desktops, and servers.

The intended data flow is as follows, resembling software pipelining but on a distributed and hardware scale:

* NoC 0 reads data from DRAM (or accept data from other Tensixes)
* Unpacker unpacks the data into a format that can be processed by the matrix/tensor unit
* Matrix/tensor unit performs the computation
* Packer packs the result back into a format for storage
* NoC 1 sends the result to DRAM (or other Tensixes)



The NoCs operate in a quasi-full-duplex configuration through a unidirectional, wraparound topology where NoC 0 and NoC 1 traverse the chip in opposite directions. This bidirectional capability allows both NoCs to simultaneously send and receive data, while the unidirectional design optimizes power consumption and silicon area utilization. The wraparound 2D torus topology ensures full connectivity, enabling any point on the chip to communicate with any other location. The opposing directional flow of the two NoCs naturally provides efficient return paths for data, regardless of the originating location.


It is important to understand that the flow described above is just one possible configuration. The RISC-V cores maintain full control of every part of the Tensix. For complex operations, they are fully capable and sometimes operators intentionally utilize both NoCs for the same data movement simultaneously, doubling the effective bandwidth at the cost of not being able to overlap reads and writes together. SRAM can be used as temporary storage for intermediate results within the operation itself.

Despite the chip's grid-like topology, the architecture maintains programming flexibility. Developers can implement [Single Program, Multiple Data (SPMD)][wiki_spmd] execution patterns across cores without architectural restrictions. SPMD serves as the primary programming model for most operations, with specialized implementations only required for algorithms that benefit from exploiting the physical chip topology for performance optimization, such as the [optimized Scaled Dot Product Attention implementation on Wormhole][spda_tt_report].

[wiki_spmd]: https://en.wikipedia.org/wiki/Single_program,_multiple_data


[spda_tt_report]: https://github.com/tenstorrent/tt-metal/blob/7c26a4706be6ba8b5faf2c3ccb0e127a784883f8/tech_reports/FlashAttention/FlashAttention.md

This architecture, with its five RISC-V cores per Tensix, might initially suggest that developers need to write five separate programs for each operation. In practice, developers typically write three types of kernels per Tensix: a **reader kernel** for data input (usually managing NoC0), a **compute kernel** for the actual computation using the matrix/vector units, and a **writer kernel** for data output (usually managing NoC1). The reader and writer kernels are often reusable across different operations since they handle standard data movement patterns. The three RISC-V cores within the compute section work cooperatively, with their coordination handled automatically by the compiler and Metalium programming model rather than requiring explicit multi-threaded programming.

The following diagram illustrates how these kernel types are distributed across the Tensix architecture:



The three kernels - reader, compute, and writer - coordinate their execution using circular buffers, which are implemented in SRAM and facilitated by hardware metadata synchronization. These circular buffers act as producer-consumer queues, enabling safe and efficient data exchange between kernels.

Each kernel interacts with the buffers as follows:

- **Reader kernel:** Writes data into the circular buffer and signals when new data is available.
- **Compute kernel:** Waits for data to become available in the buffer before processing it. After computation, it writes the results to another buffer and marks them as ready.
- **Writer kernel:** Waits for the computed results to appear in the buffer before writing them to the output location.

This mechanism ensures that each kernel only proceeds when the necessary data is ready, preventing race conditions and enabling asynchronous, pipelined execution across the hardware.

The vector addition operation demonstrates the three-kernel architecture clearly. The reader kernel accepts three parameters: the addresses of input buffers A and B, and the number of tiles to process. It fetches data from DRAM and places it into circular buffers. The compute kernel waits for data availability from the reader, performs the addition operation, and outputs results to another circular buffer. The writer kernel then retrieves the computed results and writes them to the designated output buffer. Since the NoC interfaces and compute engines operate as independent peripherals, all operations execute asynchronously, requiring explicit synchronization barriers to ensure correct data flow and prevent race conditions.

The following are the kernels, when run together, will perform vector addition on two input buffers A and B, each containing `n_tiles` tiles and write the result to an output buffer C.

```c++
// Data read kernel (data movement kernel 0)
#include <dataflow_api.h>

void kernel_main() {
    // Read parameters from the kernel run-time arguments
    const uint32_t a_addr = get_arg_val<uint32_t>(0);
    const uint32_t b_addr = get_arg_val<uint32_t>(1);
    const uint32_t n_tiles = get_arg_val<uint32_t>(2);

    constexpr auto cb_in0 = tt::CBIndex::c_0;
    constexpr auto cb_in1 = tt::CBIndex::c_1;

    const uint32_t tile_size_bytes = get_tile_size(cb_in0);

    constexpr auto args_a = TensorAccessorArgs<0>();
    const auto a = TensorAccessor(args_a, a_addr, tile_size_bytes);

    constexpr auto args_b = TensorAccessorArgs<args_a.next_compile_time_args_offset()>();
    const auto b = TensorAccessor(args_b, b_addr, tile_size_bytes);

    // Read inputs from DRAM into circular buffers
    for (uint32_t i = 0; i < n_tiles; i++) {
        cb_reserve_back(cb_in0, 1);
        cb_reserve_back(cb_in1, 1);

        const uint32_t cb_in0_addr = get_write_ptr(cb_in0);
        const uint32_t cb_in1_addr = get_write_ptr(cb_in1);
        noc_async_read_tile(i, a, cb_in0_addr);
        noc_async_read_tile(i, b, cb_in1_addr);

        noc_async_read_barrier();  // Wait until tile reads are done

        cb_push_back(cb_in0, 1);
        cb_push_back(cb_in1, 1);
    }
}
```

For the compute kernel, the same source code is used to create binaries for all three Unpack/Math/Pack baby RISC-V cores. The Metalium compute API is implemented with code sections that are each enabled only for a specific type of core. In the example below, the `add_tiles` call has Unpack core code that copies the input tiles into the FPU's source registers, as well as Math core code that performs the addition operation on the FPU and stores the result into the destination register. On the other hand, the `cb_reserve_back` call only contains code that will execute on the Pack core. During execution, the runtime will automatically compile the compute kernel code three times, each time for a different core. The generated binaries will only contain code dedicated for a single type of core and will then be submitted to the device for concurrent execution.

Synchronization with the reader and writer kernels, as well as between the three cores that are running the compute kernel, is done through the circular buffers and other synchronization primitives.

```c++
// Compute kernel
#include <compute_kernel_api.h>
#include <compute_kernel_api/common.h>
#include <compute_kernel_api/eltwise_binary.h>

namespace NAMESPACE {
void MAIN {
    const uint32_t n_tiles = get_arg_val<uint32_t>(0);
    constexpr auto cb_in0 = tt::CBIndex::c_0;
    constexpr auto cb_in1 = tt::CBIndex::c_1;
    constexpr auto cb_out = tt::CBIndex::c_16;
    constexpr uint32_t dst_reg = 0;

    // Metalium API Calls                              Involved Cores
    binary_op_init_common(cb_in0, cb_in1, cb_out);  // Unpack, Math, Pack
    add_tiles_init(cb_in0, cb_in1, false);          // Unpack, Math

    for (uint32_t i = 0; i < n_tiles; i++) {
        cb_wait_front(cb_in0, 1);                   // Unpack
        cb_wait_front(cb_in1, 1);                   // Unpack

        tile_regs_acquire();                        // Math
        add_tiles(cb_in0, cb_in1, 0, 0, dst_reg);   // Unpack, Math
        tile_regs_commit();                         // Math

        cb_pop_front(cb_in0, 1);                    // Unpack
        cb_pop_front(cb_in1, 1);                    // Unpack

        cb_reserve_back(cb_out, 1);                 // Pack

        tile_regs_wait();                           // Pack
        pack_tile(dst_reg, cb_out, 0);              // Pack
        tile_regs_release();                        // Pack

        cb_push_back(cb_out, 1);                    // Pack
    }
}
}
```

The writer is simple. Just waits for the output data from the compute kernel to be ready in the output circular buffer and writes it to the output DRAM buffer.

```c++
// Data write kernel (data movement kernel 1)
#include <dataflow_api.h>

void kernel_main() {
    const uint32_t c_addr = get_arg_val<uint32_t>(0);
    const uint32_t n_tiles = get_arg_val<uint32_t>(1);

    constexpr auto cb_out = tt::CBIndex::c_16;

    const uint32_t tile_size_bytes = get_tile_size(cb_out);

    constexpr auto args_c = TensorAccessorArgs<0>();
    const auto c = TensorAccessor(args_c, c_addr, tile_size_bytes);

    // Read outputs from circular buffers into DRAM
    for (uint32_t i = 0; i < n_tiles; i++) {
        cb_wait_front(cb_out, 1);

        const uint32_t cb_out_addr = get_read_ptr(cb_out);
        noc_async_write_tile(i, c, cb_out_addr);

        noc_async_write_barrier();

        cb_pop_front(cb_out, 1);
    }
}
```

### SRAM, interleaved and shared buffers

Each Tensix contains 1.5MB of SRAM, and with hundreds of Tensix cores per chip, this provides substantial on-chip memory capacity. Unlike pure SRAM architectures that require all data to fit in SRAM, Tenstorrent's hybrid approach allows data to reside in either SRAM or DRAM as needed. This flexibility reduces expensive DRAM accesses for intermediate results while avoiding the strict memory constraints of pure SRAM designs.

This approach reduces the need for aggressive operator fusion that CPUs and GPUs require to maintain performance. In traditional architectures, intermediate tensors that exceed cache capacity get evicted to DRAM, or context switches invalidate cache contents, creating performance bottlenecks. Tenstorrent's architecture allows intermediate data to persist in SRAM across multiple operations without eviction pressure. When operations can access data stored locally within the same Tensix, NoC bandwidth requirements are eliminated entirely, further improving performance.

The physical placement of DRAM controllers on the chip can be exploited to optimize memory access patterns. By default, memory operations use "interleaved" mode, which distributes data across all available DRAM controllers. This provides the most balanced performance characteristics and works well for general-purpose workloads.

For specific operations, data can instead be stored in "sharded" mode (see the [Tensor and Memory Layout report](https://github.com/tenstorrent/tt-metal/blob/main/tech_reports/tensor_layouts/tensor_layouts.md) for details), where tensors are distributed across multiple Tensix cores based on the physical topology of the chip. This approach reduces the physical distance data must travel and minimizes cross-chip communication overhead. Sharded memory placement is particularly beneficial for attention mechanisms and convolution operations where the computation pattern aligns well with the data distribution strategy.


### Native tile based computing
Tenstorrent hardware natively operates on 32×32 element tiles, which optimizes common deep learning operations like matrix multiplication and convolution. This design choice addresses a fundamental inefficiency in traditional linear memory layouts: when performing matrix operations, hardware must buffer entire rows (often thousands of elements) because accessing the next row requires skipping large memory offsets, or manual zigzag/tiled matrix multiplication must be implemented which adds complexity.


Tiled layouts solve this problem by organizing data so the next row element appears after only 32 elements, dramatically reducing the memory footprint needed for computation. This organization significantly improves the compute-to-SRAM ratio - instead of dedicating large amounts of SRAM to buffer full matrix rows, the hardware keeps more data actively involved in computation.

Tensors are stored in tiled format natively on Tenstorrent processors and converted back to linear format when returned to host systems. For example, a 48×1024 matrix becomes a 64×1024 matrix due to 32×32 tile alignment requirements, with the first dimension padded by 16 rows. Tilization and untilization operations can be performed on-device, reducing CPU overhead during model loading and inference.

The 32×32 tile size allows hardware to process data efficiently within a few clock cycles while maintaining computation pipelines. CPUs and GPUs must implement complex tiled access patterns in software to improve cache utilization and performance. Tenstorrent hardware provides this capability natively, eliminating the software overhead of tile management.


GPUs often struggle to efficiently supply data to their tensor cores because their architectures are primarily designed around vector operations. This can lead to less optimal memory access patterns for tensor workloads. In contrast, Tenstorrent hardware is built for tile-based computation from the start—both the vector and matrix units operate natively on 32×32 tiles. This approach leads to more predictable performance and a simpler programming model. For detailed performance numbers, see the [Matrix Multiplication performance report](https://github.com/tenstorrent/tt-metal/blob/main/tech_reports/GEMM_FLOPS/GEMM_FLOPS.md) as well as the [Convolution Networks on Tenstorrent Chips](https://github.com/tenstorrent/tt-metal/blob/main/tech_reports/CNNs/ttcnn.md) report.

### Where is the cache hierarchy

Tenstorrent chips deliberately omit cache hierarchies found in traditional CPU and GPU architectures. Instead of relying on automatic caching mechanisms to hide memory latency, the design provides direct access to SRAM throughout the chip. Any component can read from or write to SRAM located in other Tensix cores across the entire device.

This SRAM functions as addressable memory rather than transparent cache. Data movement requires explicit operations: either other cores write data to a target Tensix's SRAM, or the Tensix itself issues requests to fetch required data. This explicit model eliminates cache coherency protocols and provides predictable memory access latency, but places responsibility on developers to manage data placement and movement patterns effectively.

### Tenstorrent hardware for GPU experts

In contrast to modern GPU architectures that achieve high throughput through massive thread parallelism and latency-hiding techniques, Tenstorrent processors employ a fundamentally different architectural approach centered on asynchronous I/O operations and efficient resource utilization through software pipelining. The key architectural distinctions include:

* Each Baby RISC-V core within a Tensix implements single-threaded execution without hardware multithreading capabilities
* The architecture omits SIMT (Single Instruction, Multiple Thread) designs that abstract SIMD lanes as independent threads, as well as traditional latency-hiding mechanisms
* Tensix cores operate through cooperative processing models rather than conventional thread scheduling paradigms
* The deliberate absence of cache hierarchies provides deterministic and consistent memory access patterns
* DRAM access requires explicit DMA operations rather than transparent memory management
* The Network-on-Chip (NoC) interconnect facilitates efficient near-memory computation capabilities

### Tenstorrent hardware for CPU experts

Similar to the IBM CELL processor architecture, each Tensix contains dedicated SRAM that the Baby RISC-V cores and the peripherals on the Tensix access directly. Any data not stored in local SRAM must be explicitly transferred via DMA operations, either through writes from other cores or through explicit requests from the Tensix itself. Each Tensix includes dedicated vector and matrix processing units, similar to modern CPU architectures. However, the entire chip architecture omits cache hierarchies, providing deterministic and consistent memory access latency. When computational data fits within SRAM capacity, maximum performance is achieved without requiring specialized optimization techniques. Additionally, cores within each Tensix operate cooperatively rather than independently completing separate work portions.

The Baby RISC-V cores are implemented as straightforward RISC-V 32IM processors without task switching capabilities. Since explicit DMA operations are required for DRAM access (which exists outside the Tensix's address space), memory consistency and latency management is unnecessary. Inter-core data communication within the Tensix uses hardware mutex mechanisms and circular buffer structures.

### Scaling beyond one chip

As models grow larger, multi-chip co-processing becomes essential for serving state-of-the-art models. The machine learning community has traditionally relied on CPUs and PCIe buses for inter-device data transfers. However, the scale requirements of modern workloads necessitated specialized solutions like NVLink and Infiniband. While these proprietary interconnects are effective, they require expensive cabling and switching infrastructure.

Tenstorrent takes a different approach by using standard Ethernet connectivity. While NVIDIA's NVLink 5.0 provides 400G (G = Gbps) connectivity, Tenstorrent chips support standard Ethernet up to 800G - infrastructure already present in modern data centers. This eliminates the need for proprietary interconnects and specialized switches. The chips have sufficient NoC bandwidth and processing capability to function as network switches themselves, enabling converged computing without affecting computational performance.

The Wormhole n300 card illustrates this design with two Wormhole chips connected via Ethernet. The chip with direct PCIe host connectivity (L chip - Local) communicates with the secondary chip (R chip - Remote) through this Ethernet link. The SDK abstracts this topology, allowing developers to program both chips uniformly for memory allocation, kernel execution, and data transfer operations.


This architecture scales efficiently beyond two chips. The QuietBox configuration contains 8 Wormhole or 4 Blackhole™ processors connected in a mesh topology. Data can be transferred between processors using specialized code called EDM (Ethernet Data Movers) that handles traffic routing over the Ethernet interconnects.


While 8 chips provides substantial computational capacity, larger configurations are required for training the most demanding models. The same interconnect architecture scales to configurations of up to 32 chips connected on a single host system.


Multiple 32-chip boxes can be connected together to form a mesh spanning several hosts. These meshes can then be linked, with traffic routed between them using the tt-Fabric firmware. This approach allows scaling to data center configurations while keeping the same programming model, API, and development concerns as a single machine.


Please refer to the [tt-Fabric technical report](tech_reports/TT-Fabric/TT-Fabric-Architecture.md) for more details on the interconnect architecture and how it enables efficient scaling across multiple chips and hosts. And [Basic Ethernet Multichip](https://github.com/tenstorrent/tt-metal/blob/main/tech_reports/EthernetMultichip/BasicEthernetGuide.md) for a guide on Ethernet performance on Wormhole processors.

## TT-Metalium

Metalium is Tenstorrent's SDK for developing applications on the Tensix Processor. The full product name is TT-Metalium™, also abbreviated as tt-Metal or Metal. The API design resembles OpenCL, providing C++ interfaces for both high-level operations and direct hardware control. The kernels shown in previous sections are written using Metalium.

Metalium functions as the base layer for Tenstorrent's software stack. Higher-level tools like TTNN, tt-MLIR, and tt-Forge are built on top of Metalium. Applications can range from simple single-kernel programs running on one core to complex distributed computations spanning multiple chips.

### Running code on device

Metalium follows a similar design philosophy to OpenCL, which is reflected in its API structure. The process of executing code on a Tenstorrent device involves the following steps:

* Initialize and open a device connection
* Allocate memory buffers for input and output data
* Transfer input data to device buffers
* Compile data movement and compute kernels
* Allocate circular buffers for inter-kernel data communication
* Configure runtime parameters for kernel execution
* Enqueue kernels for execution
* Synchronize and wait for kernel completion
* Retrieve computational results from output buffers

The following example demonstrates vector addition implementation using the Metalium API. This code shows the complete workflow: device initialization, buffer allocation, kernel compilation, circular buffer configuration, program execution, and result retrieval.

First, we initialize the device connection and allocate the necessary buffers:

```c++
IDevice* device = CreateDevice(/*device_id=*/0);
CommandQueue& cq = dev->command_queue(/*cq_id=*/0);
Program program = tt::tt_metal::CreateProgram();

constexpr uint32_t n_tiles = 64;
constexpr uint32_t elements_per_tile = tt::constants::TILE_WIDTH * tt::constants::TILE_HEIGHT;
constexpr size_t tile_size_bytes = elements_per_tile * sizeof(bfloat16);
constexpr size_t buffer_size_bytes = n_tiles * tile_size_bytes;
constexpr size_t page_size_bytes = tile_size_bytes; // We choose to use one tile per page

InterleavedBufferConfig dram_buffer_config{
    .device = device,
    .size = buffer_size_bytes,
    .page_size = page_size_bytes,
    .buffer_type = BufferType::DRAM};
auto a = CreateBuffer(dram_buffer_config);
auto b = CreateBuffer(dram_buffer_config);
auto c = CreateBuffer(dram_buffer_config);

std::vector<uint32_t> a_data = create_random_vector_of_bfloat16(buffer_size_bytes, 2, 42, -1.0f);
std::vector<bfloat16> b_data(n_tiles * elements_per_tile, 3.14159f);

EnqueueWriteBuffer(cq, a, a_data, /*blocking=*/false);
EnqueueWriteBuffer(cq, b, b_data, /*blocking=*/false);
```

Next, we allocate the circular buffers required for inter-kernel communication. Each circular buffer is configured to hold two or more tiles worth of data, enabling the reader kernel to fetch new data while the compute kernel processes the previous tile. This overlapping of data movement and computation significantly improves overall throughput. While increasing the number of tiles per circular buffer can further enhance performance, developers should carefully evaluate memory usage constraints and recognize the diminishing returns associated with larger buffer sizes. The circular buffer configuration utilizes buffers 0, 1, and 16 for inter-kernel communication. These specific buffer IDs are arbitrary selections - any unique identifiers would function equivalently. The key requirement is that each circular buffer must have a distinct ID to prevent conflicts during execution.

```c++
// This example executes on a single Tensix core
constexpr CoreCoord core {0, 0};
constexpr uint32_t tiles_per_cb = 2;

// Configure source buffer A (input 0)
constexpr auto cb_in0_index = tt::CBIndex::c_0;
CBHandle cb_in0 = CreateCircularBuffer(
    program, core,
    CircularBufferConfig(
        /*total_size=*/tiles_per_cb * tile_size_bytes,
        /*data_format_spec=*/{{cb_in0_index, tt::DataFormat::Float16_b}})
        .set_page_size(cb_in0_index, tile_size_bytes));

// Configure source buffer B (input 1)
constexpr auto cb_in1_index = tt::CBIndex::c_1;
CBHandle cb_in1 = CreateCircularBuffer(
    program, core,
    CircularBufferConfig(
        /*total_size=*/tiles_per_cb * tile_size_bytes,
        /*data_format_spec=*/{{cb_in1_index, tt::DataFormat::Float16_b}})
        .set_page_size(cb_in1_index, tile_size_bytes));

// Configure destination buffer (output)
constexpr auto cb_out_index = tt::CBIndex::c_16;
CBHandle cb_out = CreateCircularBuffer(
    program, core,
    CircularBufferConfig(
        /*total_size=*/tiles_per_cb * tile_size_bytes,
        /*data_format_spec=*/{{cb_out_index, tt::DataFormat::Float16_b}})
        .set_page_size(cb_out_index, tile_size_bytes));
```

Then, we compile the kernels for data movement and computation. For simplicity, this example targets a single Tensix at coordinates (0, 0). Runtime arguments are then configured for each kernel to specify their operational parameters.

```c++
std::vector<uint32_t> reader_args;
TensorAccessorArgs(*a).append_to(reader_args);
TensorAccessorArgs(*b).append_to(reader_args);
auto reader = CreateKernel(
    program,
    "path/to/reader_kernel.cpp",
    core,
    DataMovementConfig{.processor = DataMovementProcessor::RISCV_0, .noc = NOC::RISCV_0_default, .compile_args = reader_args});
std::vector<uint32_t> writer_args;
TensorAccessorArgs(*c).append_to(writer_args);
auto writer = CreateKernel(
    program,
    "path/to/writer_kernel.cpp",
    core,
    DataMovementConfig{.processor = DataMovementProcessor::RISCV_1, .noc = NOC::RISCV_1_default, .compile_args = writer_args});
auto compute = CreateKernel(
    program,
    "path/to/compute_kernel.cpp",
    core,
    ComputeConfig{.math_approx_mode = false, .compile_args = {}, .defines = {}});
SetRuntimeArgs(program, reader, core, {a->address(), b->address(), n_tiles});
SetRuntimeArgs(program, writer, core, {c->address(), n_tiles});
SetRuntimeArgs(program, compute, core, {n_tiles});
```

Following setting the arguments, the program is enqueued for execution, synchronized for completion, and the computational results are retrieved.

```c++
EnqueueProgram(cq, program, /*blocking=*/true);
std::vector<bfloat16> c_data(n_tiles * elements_per_tile, 0.0f);
EnqueueReadBuffer(cq, c, c_data, /*blocking=*/true);
```

### Register control and Data Flow within the Compute Kernels

As described earlier, the RISC-V cores in each Tensix are mainly responsible for dispatching instructions to the hardware engines, not for performing the computations themselves. The unpack core moves data from L1 SRAM into registers, the math core issues instructions to the SFPU and FPU, and the pack core writes data back to L1. These engines are peripherals and do not share registers with the RISC-V cores or with each other. Instead, they use dedicated registers:

- **SrcA** and **SrcB**: Hold the source data for the matrix engine
- **Dst**: Holds the result for matrix and vector engine operations, also serves as input for the vector engine
- **LReg**: Holds the internal state of the vector engine

The diagram below shows the register layout and data flow for the SFPU and FPU units:


Some APIs, such as the `add_tiles` function shown earlier, operate directly on circular buffers and handle register management automatically. For other operations - like trigonometric or more complex elementwise functions - you need to explicitly move data between buffers and registers. The exact approach depends on the operation and the API you are using.

For instance, adding two tiles together using the FPU requires the following steps:

```c++
// Dst register index for the result
constexpr uint32_t dst_reg = 0;
// Add two tiles together using the FPU and store in Dst register
add_tiles(tt::CBIndex::c_0, tt::CBIndex::c_1, 0, 0, dst_reg);
// Pack the result into the result circular buffer
pack_tile(dst_reg, tt::CBIndex::c_16, /*output_tile_index=*/0);
```

For functions such as sine or cosine, you must explicitly load the input tile into the Dst register, call the relevant SFPU function, and then write the result back to the circular buffer.

```c++
// Dst register index for the result
constexpr uint32_t dst_reg = 0;
// Load the input tile into the `dst_reg`-th register.
copy_tile(tt::CBIndex::c_0, 0, dst_reg);
// Call the SFPU sine function. It overwrites original value in register
sin_tile(dst_reg);
// Write the result back to the circular buffer
pack_tile(dst_reg, tt::CBIndex::c_16, /*output_tile_index=*/0);
```

In general, FPU operations can work directly on circular buffers, while SFPU operations require data to be moved into into the Dst register before invoking the SFPU. But almost always `pack_tile` is needed to write the result back to the circular buffer, which is then pushed and the writer kernel can proceed to write the result to the output buffer.

#### Compute APIs

A natural question when encountering a new abstraction layer is, "Why is this needed?" For Metalium kernels, the Compute API abstraction layer addresses a fundamental problem: **maintaining kernel code compatibility and performance across different hardware generations.**

Tenstorrent hardware evolves between generations with significant architectural changes. Vector units, instruction sets, and data path characteristics differ - Grayskull's vector unit processes 64 elements with 19-bit floating point precision, while Wormhole and Blackhole generations use 32-element vectors with 32-bit floating point operations.

Without an abstraction like compute API, developers would need to write kernels directly for specific hardware generations. This creates several problems:
*   **Code Brittleness:** Kernels written for Grayskull (using 64-wide vector operations) won't work on Wormhole or Blackhole.
*   **Maintenance Overhead:** Each new hardware generation requires rewriting and re-validating kernels, slowing development and adoption.

Compute APIs solve this by providing a stable programming interface. When invoked from a compute kernel (e.g., `sin_tile`), the Metalium compiler automatically selects the correct implementation optimized for the target hardware's vector width, instruction set, and other capabilities. This preserves the kernel's functionality while ensuring optimal performance across hardware generations.

This abstraction ensures kernel code remains functional and efficient across hardware generations. For example, when a compute kernel invokes `sin_tile`, the compiler automatically selects the appropriate implementation optimized for the target hardware's specific vector width and computational capabilities.

```c++
sin_tile(0); // Different implementation for sin is called when compiled for
             // different generations of Tenstorrent processors.
```
When a compute kernel calls `sin_tile`, Metalium automatically selects the correct hardware-specific implementation for the target processor. For Grayskull processors, the implementation performs a phase shift transformation from the [0, 2π] range to [-π, π] and employs a MacLaurin series expansion to compute the sine function. This selection and dispatch are handled by Metalium, ensuring that the appropriate version of the sine operation is invoked for each hardware generation.

```c++
// tt_metal/hw/ckernels/grayskull/metal/llk_api/llk_sfpu/ckernel_sfpu_trigonometry.h
template <bool APPROXIMATION_MODE, int ITERATIONS>
inline void calculate_sine() {
    // SFPU microcode
    for (int d = 0; d < ITERATIONS; d++) {
        vFloat v = dst_reg[0];

        // Assume v is bound [0:2pi]
        // phase shift [0:2pi] to [-pi:pi] and multiply result by -1
        v = v - 3.14159264f;
        v = sfpu_sine_maclaurin_series<APPROXIMATION_MODE>(v);

        // Use symmetrical properties of trig
        v *= -1;

        // Write Output
        dst_reg[0] = v;
        dst_reg++;
    }
}
```

For Blackhole (and Wormhole) processors, the availability of `float_to_int16` instruction enables reliable value shifting to the [-π, π] range. The implementation then applies a MacLaurin series calculation for sine computation (utilizing the same mathematical approach but with processor-specific function naming). Additionally, the ITERATIONS parameter differs between processor generations (not shown in code here, it is set by an outside source): Grayskull requires 4 iterations, while Wormhole and Blackhole require 8 iterations to accommodate their reduced vector width of 32 elements compared to Grayskull's 64-element vectors.

```c++
// tt_metal/hw/ckernels/blackhole/metal/llk_api/llk_sfpu/ckernel_sfpu_trigonometry.h
template <bool APPROXIMATION_MODE, int ITERATIONS>
inline void calculate_sine() {
    // SFPU microcode
    for (int d = 0; d < ITERATIONS; d++) {
        vFloat v = dst_reg[0] * FRAC_1_PI;
        vInt whole_v = float_to_int16(v, 0);
        v -= int32_to_float(whole_v, 0);
        v = sfpu_sinpi<APPROXIMATION_MODE>(v);

        v_if(whole_v & 1) { v = -v; }
        v_endif;
        dst_reg[0] = v;
        dst_reg++;
    }
}
```

While Metalium supports custom vectorized computation implementations, developers should note that vector width and hardware-specific details vary between processor generations. And working implementation must be provide for the target processor. For most applications, use the provided compute APIs from the kernel library since Tenstorrent maintains these implementations for compatibility with future hardware generations. For custom vectorized computation guidance, see the [Low Level Kernels][tt_llk_doc] section in the Metalium documentation.

[tt_llk_doc]: https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/apis/kernel_apis/sfpu/llk.html

### Fast dispatch

Fast dispatch implements asynchronous command queuing by dedicating one RISC-V core per queue on the device to process queued operations. Unlike GPUs that use specialized on-chip schedulers built into the GPU-host runtime, Tenstorrent assigns one RISC-V core per command queue for command processing. This core is typically placed on an unused Ethernet tile, which minimizes impact on computational performance while taking advantage of the architecture's ability for any core to access any other core.

When fast dispatch is disabled (by setting the `TT_METAL_SLOW_DISPATCH_MODE` environment variable to `1`), the asynchronous dispatch mechanism is bypassed. This disables command queue functionality and prevents asynchronous I/O operations between the host and device. In slow dispatch mode, the CPU must wait for each operation to complete before proceeding to the next instruction. Synchronous API calls such as `ReadFromBuffer` must be used instead of their asynchronous counterparts like `EnqueueReadBuffer`.

Fast dispatch is much faster - Slow dispatch forces the host CPU to actively manage all operations, including data transfers to and from the device. This creates significant CPU overhead and prevents the host from performing other tasks while waiting for device operations. Fast dispatch stores command sequences in host memory and allows the device to fetch and execute them independently. Freeing the CPU to handle other work (or simply idle and reduce power) while the device processes commands, resulting in better overall system utilization.

**Use fast dispatch for production workloads.** Slow dispatch should only be used for debugging when you suspect the dispatch mechanism itself is malfunctioning or when you need to determine whether issues originate from the command queuing system or kernel execution.


```c++
// Fast dispatch. Can be async or the process waits until completion
EnqueueReadBuffer(queue, buffer, host_ptr, /*blocking=*/false);

// Slow dispatch. No queue. But also CPU has to do all the job
ReadFromBuffer(buffer, host_ptr);
```

Unlike OpenCL's command queue which optionally supports out-of-order execution, Tenstorrent's command queue architecture enforces strict in-order execution due to the performance characteristics of the Baby RISC-V cores. To enable overlapping computation and data transfer operations, each device provides two dedicated command queues: By convention, queue 0 handles computational workloads while Queue 1 manages data transfer operations. Synchronization between queues is achieved through an event-based mechanism, where an event obtained from one queue can signal completion to the other queue, ensuring proper coordination and preventing race conditions such as reading from buffers that are currently being modified by concurrent operations.

```c++
// Wait for the current tail operation on queue 0 to complete
// before proceeding on command queue 1
auto event = EnqueueRecordEvent(device->command_queue(0));
EnqueueWaitForEvent(device->command_queue(1), event);
```

### SPMD in Metalium

Single Program, Multiple Data (SPMD) execution is a common parallel computing model used in frameworks like OpenMP, CUDA, and OpenCL. In SPMD, multiple processing units execute the same program but operate on different portions of data. While Metalium supports SPMD and provides the necessary infrastructure, the architecture does not enforce its use - developers can choose alternative approaches when beneficial.

For complex operations requiring specialized behavior, Metalium also supports Multiple Program, Multiple Data (MPMD) execution, where different Tensix cores run entirely different programs. An example is the data-reused matrix multiplication implementation, which places specialized kernels on specific Tensix cores to broadcast data to other cores, reducing NoC bandwidth consumption.

Unlike OpenCL's `get_global_id()`, CUDA's `threadIdx`, or OpenMP's `omp_get_thread_num()`, Metalium does not provide built-in thread and global work size identification mechanisms. Instead, developers explicitly specify the data range each Tensix core processes by passing different runtime arguments to each core before kernel execution. For example:

```c++
CoreRange core_range = {{0, 0}, {4, 4}}; // Processors from (0,0) to (4,4)
// set up the program and kernels
...

// Calculate work per core based on the range and number of tiles
uint32_t work_per_core = calculate_work_per_core(...);
for(uint32_t y = core_range.start.y; y < core_range.end.y; y++) {
    for(uint32_t x = core_range.start.x; x < core_range.end.x; x++) {
        auto core = {x, y};
        uint32_t id = y * core_range.end.x + x; // Unique ID for each core
        SetRuntimeArgs(program, reader_kernel, core, {
            a->address(),
            b->address(),
            work_per_core,
            id // Pass unique ID to each core
        });
        // In most cases, the compute kernel doesn't care about the core ID, but if needed, it can be passed as well
        SetRuntimeArgs(program, compute_kernel, core, {
            work_per_core
        });
        // Set runtime arguments for the writer kernel
        SetRuntimeArgs(program, writer_kernel, core, {
            c->address(),
            work_per_core,
            id // Pass unique ID to each core
        });
    }
}
```

Metalium provides the `tt::tt_metal::split_work_to_cores` utility function to distribute work across available cores for SPMD execution. The function takes the total number of tiles and available cores, then calculates how to divide the work when it cannot be evenly distributed. The function returns two groups of cores: a primary group that handles more tiles per core, and a secondary group that handles fewer, along with the tile count for each group. Minimizing workload imbalance between cores (if work can be evenly distributed, the secondary group will be empty.)

```c++
auto core_grid = device->compute_with_storage_grid_size();
auto [num_cores, // number of cores utilized
    all_cores, // set of all cores used
    core_group_1, // Primary core group
    core_group_2, // Secondary core group
    num_tiles_per_core_group_1, // Number of tiles each core in the primary group processes
    num_tiles_per_core_group_2 // Number of tiles each core in the secondary group processes
    ] = tt::tt_metal::split_work_to_cores(grid_size, work_size);
```

Only create kernels on cores that have been assigned work (i.e., those in `all_cores` or `core_group_*`). Avoid creating kernels on unused cores, as this can cause undefined behavior or crashes if kernels are created but runtime arguments are not set on the core. If there is not enough work, some cores may remain idle—do not assign kernels to them.

```c++
// `all_cores` is guaranteed to be the union of `core_group_1` and `core_group_2`.
for (const auto& core : all_cores) {
    // Good
    CreateKernel(program, "/path/to/reader.cpp", all_cores, DataMovementConfig{...});
    CreateKernel(program, "/path/to/compute.cpp", all_cores, ComputeConfig{...});
    CreateKernel(program, "/path/to/writer.cpp", all_cores, DataMovementConfig{...});

    // Bad - all_cores may be smaller than core_grid
    //                                               vvvvvvv
    // CreateKernel(program, "/path/to/reader.cpp", core_grid, DataMovementConfig{...});
    // CreateKernel(program, "/path/to/compute.cpp", core_grid, ComputeConfig{...});
    // CreateKernel(program, "/path/to/writer.cpp", core_grid, DataMovementConfig{...});
}
```

Developers should iterate over all cores and set the runtime arguments for each kernel according to the assigned core group and tile count. The sum of tiles processed by all cores must match the original workload. If a core is not part of either group (can happen due to not enough work or other reasons), its runtime arguments MUST be set such the kernel does nothing (a no-op). Leaving runtime arguments uninitialized will lead to undefined behavior and issues during execution.

```c++
auto work_groups = {std::make_pair(core_group_1, num_tiles_per_core_group_1),
                    std::make_pair(core_group_2, num_tiles_per_core_group_2)};
uint32_t id = 0; // Offset for the next core in the group
for(const auto& [group, work_per_core] : work_groups) {
    for (const auto& range : group) {
        for(const auto& core : range) {
            // Set runtime arguments for each kernel based on the core and tile count
            SetRuntimeArgs(program, reader, core, {/*reader parameters*/a->address(), b->address(), work_per_core, id});
            SetRuntimeArgs(program, writer, core, {/*writer parameters*/c->address(), work_per_core});
            SetRuntimeArgs(program, compute, core, {/*compute parameters*/work_per_core, id});
            id += work_per_core;
        }
    }
}

// at this point id == work_size as all cores have been assigned work
```

## Source: docs/source/tt-metalium/tt_metal/programming_model/index.rst

# Programming Model

Please find our architecture and programming model guide [here](https://github.com/tenstorrent/tt-metal/blob/main/METALIUM_GUIDE.md).

## Source: docs/source/tt-metalium/tt_metal/advanced_topics/compute_engines_and_dataflow_within_tensix.rst

# Compute Engines and Data Flow within Tensix

The matrix and vector engines (FPU and SFPU) are integral to Tensix's compute capabilities. They are designed to efficiently handle a wide range of mathematical operations, particularly those common in machine learning. However, they are highly specialized and do not operate like traditional CPU-attached vector and matrix units. Instead of having direct access to CPU registers and memory, these engines use their own registers and rely on the unpacker and packer to move data between SRAM and the compute engines.

Understanding the data flow between the register sets, the unpacker and packer, and the engines is critical for achieving optimal performance and resource utilization. Please refer to the relevant hardware and ISA documentation for more details.

- [SFPU on Wormhole](https://github.com/tenstorrent/tt-isa-documentation/blob/main/WormholeB0/TensixTile/TensixCoprocessor/VectorUnit.md)
- [FPU on Wormhole](https://github.com/tenstorrent/tt-isa-documentation/blob/main/WormholeB0/TensixTile/TensixCoprocessor/MatrixUnit.md)

## Component introduction

A critical design aspect to understand is that **all registers have a fixed element count**. Each vector register holds exactly N elements, where N depends on the kernel configuration and the specific register set. This differs from x86 SSE/AVX or ARM NEON and is more similar to some GPU warp/wavefront designs. The size of the registers may also change between hardware generations. Thus, a program that depends on a specific register dimension must be rewritten to work across generations. Compute APIs provided by the Metalium kernel library, like `matmul_tiles` and `sin_tiles`, abstract away these details, allowing you to focus on the algorithm rather than the underlying hardware specifics.

For example, the SFPU `LReg` (the SFPU's internal vector register) on Wormhole is 32 elements wide, with each element being 32 bits. A conventional SIMD register design would imply a capacity of 1024 bits per register, which could hold 128 elements of int8 data. However, the SFPU treats the register as holding 32 elements of at most 32 bits each, regardless of the actual data type.

Several key components work together to perform computations within Tensix:

- **Unpacker**: Reads data from L1 memory and converts it into the format required by the compute engines, placing it into the `SrcA`, `SrcB`, or `Dst` registers.
- **Packer**: Takes results from the compute engines (from the `Dst` registers), formats them, and moves them back into L1.
- **Vector engine (SFPU)**: Executes complex vector operations, handling data in parallel for efficient computation.
- **Matrix engine (FPU)**: Specializes in large-scale matrix operations, optimized for high throughput.

The compute engines rely on four main register sets:

1.  **SrcA**: The first source register set for the matrix engine.
2.  **SrcB**: The second source register set for the matrix engine.
3.  **Dst**: The destination register set for the matrix engine, also used by the vector engine. This register set is exposed in the higher-level API.
4.  **LReg**: Internal registers within the SFPU for holding vector data during computation.

The following image illustrates the connection between the different components and the registers they can access.

> [!NOTE]
> Although a compute kernel is written as a single piece of code, it is compiled into three separate binaries, each running on a different RISC-V core (T0-2) within the Tensix. Synchronization is required to ensure correct data flow and avoid race conditions between these components.
>
> Furthermore, the unpacker, packer, SFPU, and FPU are not processing cores and cannot make control flow decisions on their own. The RISC-V cores issue commands to the compute engines and manage data flow between them. Explicit synchronization may be needed to ensure the engines have finished their work before the RISC-V cores proceed.

*Figure: The connection between the unpacker, packer, SFPU, FPU, and the various registers is crucial for efficient data processing within the Tensix architecture.*

The data format within the compute registers can differ from the format used for storage in SRAM. The unpacker and packer are responsible for converting between these formats in hardware. This allows compute kernels to work with standard data types, like floating-point or integers, while data in SRAM can remain in a more compact representation, such as a block floating-point format.

This hardware-accelerated type conversion is more efficient than performing it in software. For example, instead of using the compute engines to decompress quantized data, the unpacker can perform this conversion directly. This design makes compute kernels independent of the storage data format and reduces execution time and power consumption.

The separation of data movement (unpacker/packer) and computation (FPU/SFPU) requires an initialization step. Before invoking a compute operation, the unpacker and packer must be configured to handle the correct input and output data formats. This is critical for ensuring correct results and enabling hardware performance optimizations.

## Dst register

The `Dst` register set is the primary workspace for compute kernels and the only register set directly exposed through the compute APIs. It serves as the destination for the matrix engine and as both a source and destination for the vector engine.

The unpacker and packer handle data movement between L1 memory and the `Dst` registers. The kernel library provides functions for these operations:

``` c++
// copy_tile: Unpacks a tile from a circular buffer into a Dst register.
// Before calling, ensure the source circular buffer has data (e.g., using cb_wait_front).
copy_tile(CBIndex::c_0, /*tile_offset_in_cb*/0, /*dst_idx*/0);

// pack_tile: Packs a tile from a Dst register into a circular buffer.
// Before calling, ensure the destination circular buffer has space (e.g., using cb_reserve_back).
pack_tile(/*dst_idx*/0, CBIndex::c_16, /*tile_offset_in_cb*/0);
```

Since the unpacker, packer, and compute engines operate concurrently on different RISC-V cores, access to the `Dst` registers must be synchronized. The kernel library provides a set of functions to manage this, ensuring that different hardware components do not access the registers simultaneously.

A typical compute loop follows this synchronization pattern:

``` c++
// 0. Wait for input data to be available in the input circular buffers.
// e.g. cb_wait_front(...)

// 1. Acquire Dst registers for the unpacker and math core.
//    This must happen after waiting for input data.
tile_regs_acquire();

// Unpack data and perform math operations.
// e.g., copy_tile(...), matmul_tiles(...), add_tiles(...)

// 2. Commit the results, transferring ownership of Dst registers to the packer.
tile_regs_commit();

// At this point, the kernel can pop from input CBs and reserve space in output CBs.
// This overlaps communication with the packer's work.
// e.g. cb_pop_front(...), cb_reserve_back(...)

// 3. Wait for the packer to be ready to access the Dst registers.
tile_regs_wait();

// Pack results from Dst registers to output circular buffers.
// e.g., pack_tile(...)

// 4. Release the Dst registers, making them available for the next iteration's acquire step.
tile_regs_release();

// Announce that data has been written to the output CBs.
// e.g., cb_push_back(...)
```

> [!NOTE]
> The ordering of circular buffer operations (`cb_wait_front`, `cb_pop_front`, `cb_reserve_back`, `cb_push_back`) is flexible but constrained by data dependencies. The pattern shown in the example minimizes stalls by overlapping communication with the packer's work. Unpacking into `Dst` registers requires first acquiring them, and packing can only begin after waiting for the packer to be ready. However, by no means it is the only correct ordering.
>
> The `acquire_dst` and `release_dst` functions are deprecated. The `tile_regs_*` family of functions provides more explicit control and should be used instead.

> [!WARNING]
> Even if a kernel does not pack any data, `tile_regs_commit` and `tile_regs_release` must still be called in sequence after computation to correctly manage the register state. Failure to do so results in undefined behavior.

The capacity and behavior of the `Dst` register set are configured on the host through the `ComputeKernelConfig` struct when creating a kernel. Two key parameters control its operation. Assuming using the standard 32x32 tiles:

- `fp32_dest_acc_en`: Configures the data width of the `Dst` registers.
  - `false` (default): `Dst` holds 16 tiles of 16-bit data.
  - `true`: `Dst` holds 8 tiles of 32-bit data.
- `dst_full_sync_en`: Controls a double-buffering mechanism for the `Dst` registers.
  - `false` (default): Enables double-buffering. Only half of the `Dst` registers are available to the kernel at a time. This allows the packer to work on one half while the math core and unpacker work on the other, overlapping computation and packing to improve performance.
  - `true`: Disables double-buffering. The entire `Dst` register set is available to the kernel. This serializes computation and packing, which may be simpler but can reduce throughput.

The number of available tiles is determined by the combination of these two settings:

|  | `dst_full_sync_en = false` (Double-Buffering ON) | `dst_full_sync_en = true` (Double-Buffering OFF) |
|----|----|----|
| `fp32_dest_acc_en = false` (16-bit) | 8 | 16 |
| `fp32_dest_acc_en = true` (32-bit) | 4 | 8 |

Number of Dst Tiles Available

``` c++
// Example host-side kernel configuration
auto kernel_id = tt::tt_metal::CreateKernel(
    program,
    "path/to/your/compute/kernel.cpp",
    core,
    tt::tt_metal::ComputeConfig{
        .fp32_dest_acc_en = true, // Use 32-bit Dst registers
        .dst_full_sync_en = false  // Enable double-buffering
    }
);

// Number of Dst registers can be checked using ttnn::get_dest_reg_count(const ComputeKernelConfig&)
```

> [!WARNING]
> Setting `fp32_dest_acc_en = true` only allocates 32-bit per-element storage space in the `Dst` registers; it does not guarantee that computations are performed in 32-bit precision. For example, the matrix engine might still compute in bfloat16 and store the result in a 32-bit container. Also, the matrix engine's maximum accuracy is TF32 (19 active bits), which is less than the full 32-bit precision. On the other hand, the vector engine does support the full 32-bit precision (with some limitations as it does not strictly follow IEEE 754 rounding).
>
> Accessing `Dst` register tiles beyond the number available for the current configuration results in undefined behavior.

## Matrix engine/FPU

The matrix engine, or FPU, performs the bulk of computation for most AI and machine learning workloads. FPU operations take data from `SrcA` and `SrcB` (if needed) and write or accumulate results into `Dst`. The FPU also supports common matrix operations such as element-wise multiplication, addition, subtraction, and pooling.

FPU operations require initialization before execution. This setup configures the unpacker, packer, and FPU for the specific operation (e.g., matrix multiplication). Re-initialization is not required for repeated operations with the same source, destination, and data type parameters.

The FPU uses dedicated registers for each operand, and the unpacker can directly write to these registers. The API requires specifying the circular buffer and tile index for each operand. Because the FPU writes results to the `Dst` registers, the output tile index must also be specified. FPU compute functions often takes the following parameters, depending on the number of operands:

- Index of the circular buffer for the first operand, and the offset of the tile from the buffer's read head.
- (If applicable) Index of the circular buffer for the second operand, and the offset of the tile from the buffer's read head.
- Offset, in number of tiles, within the `Dst` registers to write the result.

For example, to perform matrix multiplication:

``` c++
// Configure (un)packer and FPU for matmul mode.
// The unpacker is configured based on cb_in0 and cb_in1.
// The packer is configured based on cb_out.
mm_init(CBIndex::c_0, CBIndex::c_1, CBIndex::c_16);

// Repeated computation can be performed without re-initialization.
for(int i=0; i < 8; i++) {
    // Wait for data to be available in the input circular buffers.
    cb_wait_front(CBIndex::c_0, 1); cb_wait_front(CBIndex::c_1, 1);

    // Acquire Dst registers for the math core.
    tile_regs_acquire();

    // Perform matrix multiplication:
    // - Take tile 0 from CB 0 and tile 0 from CB 1.
    // - Place the result into Dst tile 0.
    //              cb_in0     cb_in1        in0_offset  in1_offset  dst_idx   transp
    matmul_tiles(CBIndex::c_0, CBIndex::c_1, 0         , 0         , 0      , false);

    // Commit the results, transferring ownership of Dst registers to the packer.
    tile_regs_commit();

    // Pop tiles from input CBs and reserve space in the output CB.
    cb_pop_front(CBIndex::c_0, 1); cb_pop_front(CBIndex::c_1, 1);
    cb_reserve_back(CBIndex::c_16, 1);

    // Wait for the packer to be ready.
    tile_regs_wait();

    // Pack the result from Dst tile 0 into the output CB.
    pack_tile(/*src_dst_idx*/0, CBIndex::c_16, /*tile_offset_in_cb*/0);

    // Announce that data has been written to the output CB.
    cb_push_back(CBIndex::c_16, 1);

    // Release Dst registers for the next iteration.
    tile_regs_release();
}
```

> [!WARNING]
> The same input circular buffers (e.g., `cb_in0` and `cb_in1`) must be specified in both `mm_init` and `matmul_tiles`. Using different circular buffers between these calls results in undefined behavior, as the unpacker may interpret the data incorrectly or read from invalid memory.

The configuration information for the unpacker and packer is derived from the circular buffer metadata. In the example above, circular buffers 0 and 1 are used to configure the unpacker to place their data into `SrcA` and `SrcB`, respectively. The packer is configured to pack data into the format expected by circular buffer 16.

## Vector engine/SFPU

The vector engine, or SFPU, is designed for high-throughput processing of vector data. Unlike matrix engine APIs, SFPU APIs require the user to explicitly unpack data into the `Dst` registers before performing computations and then pack the results back into L1 memory. This design enables easier chaining of operations.

The vector engine APIs also require an initialization phase. The `init_sfpu` function configures the unpacker and packer to handle the data types of the input and output circular buffers. Unlike the matrix engine, the unpacker cannot be configured for a second operand; it assumes that all input circular buffers contain the same underlying data type. As with the matrix engine, ensure that parameters are consistent between initialization and computation calls to avoid undefined behavior.

For example, to compute the element-wise sum of two tiles:

``` c++
// Configure the (un)packer based on the data formats of the CBs.
init_sfpu(tt::CBIndex::c_0, tt::CBIndex::c_16);

for(int i=0; i < 8; i++) {
    cb_wait_front(CBIndex::c_0, 1); cb_wait_front(CBIndex::c_1, 1);
    tile_regs_acquire();

    // Unpack the first tile from CB 0 into Dst tile 0.
    copy_tile(CBIndex::c_0, /*tile_offset_in_cb*/0, /*dst_idx*/0);
    // Unpack the first tile from CB 1 into Dst tile 1.
    copy_tile(CBIndex::c_1, /*tile_offset_in_cb*/0, /*dst_idx*/1);

    // Add Dst tiles 0 and 1 together. Store the result back into Dst tile 0.
    // Pseudocode: dst_tile[0] = dst_tile[0] + dst_tile[1]
    add_binary_tile(/*dst_idx_a*/0, /*dst_idx_b*/1, /*dst_idx_out*/0);
    // More operations can be chained here, e.g., applying sigmoid.
    // sigmoid_tile(0);

    tile_regs_commit();
    cb_pop_front(CBIndex::c_0, 1); cb_pop_front(CBIndex::c_1, 1);
    cb_reserve_back(CBIndex::c_16, 1);
    tile_regs_wait();
    pack_tile(/*dst_idx*/0, CBIndex::c_16, /*tile_offset_in_cb*/0);
    cb_push_back(CBIndex::c_16, 1);
    tile_regs_release();
}
```

> [!NOTE]
> `copy_tile_init` can be used to re-configure the unpacker to consume different data formats from circular buffers. If `CBIndex::c_0` and `CBIndex::c_1` contain different data types, the unpacking part of the above example can be rewritten as follows:
>
> ``` c++
> copy_tile_init(CBIndex::c_0);
> copy_tile(CBIndex::c_0, /*tile_offset_in_cb*/0, /*dst_offset_tiles*/0);
> copy_tile_init(CBIndex::c_1);
> copy_tile(CBIndex::c_1, /*tile_offset_in_cb*/0, /*dst_offset_tiles*/1);
> ```
>
> Note that `copy_tile_init` is always needed when unpacking FP32 values into 32-bit `Dst` registers. `init_sfpu` assumes a 16-bit storage size and sets up the unpacker for bfloat16, which would cause a loss of precision if an explicit initialization is not performed.
>
> Similarly, the `pack_reconfig_data_format` function and its variants can be used to change the packer's output data format. This is necessary when a computation produces multiple tiles that must be written to circular buffers with different data formats. For example, to pack two tiles into two separate circular buffers, each with a unique data format:
>
> ``` c++
> pack_reconfig_data_format(CBIndex::c_16);
> pack_tile(/*src_idx*/0, CBIndex::c_16, /*tile_offset_in_cb*/0);
> pack_reconfig_data_format(CBIndex::c_17);
> pack_tile(/*src_idx*/1, CBIndex::c_17, /*tile_offset_in_cb*/0);
> ```

After data is unpacked into the `Dst` registers, the vector engine can load data from `Dst` into its internal `LReg` registers directly, without involving other hardware blocks. For more details on programming the SFPU, see the `Low Level Kernels programming guide <llk>`. The `dst_reg` variable provides an `LReg`-sized view into the `Dst` registers. For example, on Wormhole and Blackhole, `LReg` is 32 elements wide, so the first `Dst` tile corresponds to `dst_reg[0:31]`. To illustrate:

``` c++
void sfpu_example_function() {
    // Load the first 32 elements of the 1st tile into an LReg.
    vFloat vec1 = dst_reg[0];
    // Load the first 32 elements of the 2nd tile into another LReg.
    vFloat vec2 = dst_reg[32];

    // Store the results back into the Dst registers.
    dst_reg[0] = vec1;
    dst_reg[32] = vec2;
}
```

Due to the `internal structure of tiles<internal_structure_of_a_tile>`, `dst_reg[0:3]` typically contains the first face of the tile, `dst_reg[4:7]` contains the second face, and so on.

## Source: docs/source/tt-metalium/tt_metal/advanced_topics/index.rst

# Advanced Topics

This section provides an overview of the details of the Tensix architecture and how Metalium integrates with it. The documents here are intended for developers looking to understand the underlying hardware and software interactions.

## Hardware implications and the effects

## Source: docs/source/tt-metalium/tt_metal/advanced_topics/memory_for_kernel_developers.rst

# Memory from a kernel developer's perspective

Memory on Tenstorrent processors works differently than on traditional CPUs and GPUs. Instead of a single address space shared by all cores, memory is addressed by an (`x`, `y`, `local_address`) tuple. This is due to the mesh-based design, where each node on the NoC has its own local resources. This design has important implications for writing compute kernels. Which core uses which memory can significantly affect performance, so understanding how memory works is essential for writing efficient kernels.

This document is intended for kernel developers who want to understand memory on Tenstorrent processors beyond just using the APIs. It assumes you are familiar with the first five programming examples (from DRAM loopback to multi-core matrix multiplication). Review the [Metalium Programming Model Guide](https://github.com/tenstorrent/tt-metal/blob/main/METALIUM_GUIDE.md) for foundational understanding of the hardware architecture and programming model.

## Data addressing on Tenstorrent processors

### RISC-V Address Space

For a kernel running on data-movement core 0 of Tensix core (0, 0), the binary is placed in that core's shared SRAM (historically "L1"). At runtime, instructions stream from shared SRAM into a small per-core instruction cache (0.5-2 KiB, about 128-512 instructions) to cut repeated SRAM fetches. Each RISC-V core also has a small private memory region for its stack and locals; this region and the shared SRAM are mapped at identical addresses on every core. The shared SRAM is always accessible to all cores; only the private region is isolated. Because many on-core agents contend for shared SRAM, RISC-V loads and stores to it have limited bandwidth and a latency of several cycles.

Refer to the [Baby RISC-V](https://github.com/tenstorrent/tt-isa-documentation/blob/main/WormholeB0/TensixTile/BabyRISCV/README.md) documentation for the RISC-V address space. The [L1 page](https://github.com/tenstorrent/tt-isa-documentation/blob/main/WormholeB0/TensixTile/L1.md) documents the shared SRAM (L1) organization, its clients and performance characteristics.

``` cpp
// the function (machine code) lives on L1. When executed, a 0.5~2KiB
// instruction cache (depending on which core is selected) reduces
// SRAM access pressure
void kernel_main() {
    int a = 0; // lives on per-core private memory
    // Because of this, passing the address of this variable to another core
    // will not work, as the other core does not have access to the private memory
    // it lives on. And has the core has its own private memory mapped at the same address

    // Variable `cb_idx` lives in per-core memory but points to a circular buffer in shared SRAM
    // Because shared SRAM is mapped in the core's address space, you can cast it to a pointer
    // and access it as if it were a regular memory.
    // However note that the RISC-V cores itself have low bandwidth to SRAM, the bulk of compute
    // is done via peripherals which have much higher bandwidth to SRAM.
    cb_wait_front(tt::CBIndex::c_16, 1);
    uint32_t cb_addr = get_write_ptr(tt::CBIndex::c_16);
    // Treating it as address because the address is in shared SRAM
    // DPRINT << ((uint32_t*)cb_addr)[0] << std::endl;

    // `dram_addr` is a DRAM address, however the address is not mapped in the RISC-V address space
    // and the content must be explicitly fetched from DRAM using NoC APIs and requesting a transfer
    uint32_t dram_addr = get_arg_val<uint32_t>(0);
}
```

The memory blocks and related peripherals within the Tensix core can be visualized with the following diagram. Compute-related blocks are not shown as they are consumers of the memory system rather than part of the memory hierarchy discussed here.

### DRAM tiles

Tensix tiles are one type of tile on the NoC. Each Tensix tile contains 1.5MB of SRAM. DRAM tiles, in contrast, connect to memory controllers that interface with off-chip GDDR memory. This provides significantly more storage capacity but with higher latency and lower bandwidth compared to SRAM.

For example, Wormhole has 6 DRAM controllers, each connected to 2GB of GDDR6 memory (2 channels, 1GB per channel). The following image shows Wormhole's NoC grid with DRAM tiles labeled D1 to D6, corresponding to controllers 1-6. Multiple DRAM tiles can connect to the same controller to improve NoC connectivity. The DRAM tile placement is optimized for physical routing constraints rather than uniform distribution.

*Figure: The NoC grid of the Tenstorrent Wormhole processor (D = DRAM, T = Tensix, E = Ethernet, A = ARC/management, P = PCIe).*

For Wormhole, within each DRAM tile, the 1st channel is mapped to address 0 and the 2nd channel is mapped from address 1GB.

*Figure: The DRAM tile connection to GDDR memory. Each DRAM tile has 2 channels, each with 1GB of memory.*

### Memory access via the NoC

RISC-V cores can only access their private memory and the local shared SRAM directly. Accessing SRAM on other Tensix cores or DRAM requires sending DMA requests through the NoC. These requests specify the target tile's (x, y) coordinates and the address within that tile.

``` cpp
uint64_t noc_addr = get_noc_addr(x, y, addr_on_target_tile);
noc_async_read(noc_addr, ptr_l1_buffer, dram_buffer_size);

// for writing
noc_async_write(ptr_l1_buffer, noc_addr, dram_buffer_size);
```

> [!WARNING]
> Private memory (including the stack) is only accessible by the core that owns it. NoC requests can only access shared SRAM addresses:
>
> - Stack variables cannot be used as DMA source or destination
> - L1 buffers (allocated in the host program) and circular buffers are accessible via NoC
>
> e.g. The following **will not** work.
>
> ``` c++
> // This WILL NOT work as arr lives on the stack which is private to the core
> int arr[8];
> noc_async_read(noc_addr, uint32_t(&arr), sizeof(arr));
> ```

The same scheme works for all tiles on the NoC (as long as the address maps to valid memory). If the NoC request goes to a Tensix or Ethernet tile, it accesses their SRAM; if to a DRAM tile, it accesses DRAM; to the PCIe controller, it accesses the peripheral. Thus making the real address a tuple of (`x`, `y`, `local_addr`).

Accessing raw DRAM is straightforward. The following creates a read request of size 0x100 to DRAM tile D1 at address 0x1000:

``` cpp
uint64_t noc_addr = get_noc_addr_from_bank_id<true>(0, 0x1000);
noc_async_read(noc_addr, ptr_l1_buffer, 0x100);
```

From the information above, the following is true on Wormhole (and analogous for other generation of processors):

- All 3 D1 tiles are connected to the same DRAM controller
- Reading from different D1 tiles at the same address returns the same data
- Address 0x1000 is within the first 1GB, so the 1st channel of the GDDR chip is used
- Using all 6 DRAM controllers simultaneously provides the full 12GB capacity

As the `async` naming in `noc_async_read/write` indicates. NoC requests are asynchronous, *may* complete out of order, and may or may not return immediately due to various factors. A barrier is needed to ensure that all read or write operations are complete before proceeding.

``` cpp
noc_async_read_barrier(); // Wait for all read operations to complete
noc_async_write_barrier(); // Wait for all write operations to complete
```

## Tensor Layout

Tensors are the primary data structure that Metalium is designed to work with, though they are not strictly the only supported data structure. Tensors are multi-dimensional arrays used to represent various types of data, from images to text. As the fundamental data structure in modern machine learning frameworks, tensors provide flexibility and power for diverse computational tasks. Metalium is designed to facilitate efficient tensor operations.

Multiple tensor memory layouts exist, with traditional systems using either C-style row-major or Fortran-style column-major ordering. Metalium supports C-style row-major ordering but uses a custom tiled layout for optimal computation performance on the Tensix core. This tiled layout reduces silicon area, power consumption, and memory bandwidth by matching the Tensix core's compute units and memory architecture.

Due to the lack of a linear, flat address space, data placement (onto each memory resource) requires explicit decisions about distribution and chunk size. Distribution will be discussed in a future section. The chunk size, or the amount of data stored before switching to the next storage location, is referred to as the **page size**.

In row-major layout, a single row of the tensor occupies one page, enabling simpler programming and lower logic overhead for common patterns of data access.

*Figure: The row-major memory layout of a tensor. The data is stored in a single contiguous block of memory, with the last dimension varying the fastest.*

In contrast, the tiled layout provides optimal performance for computations on the Tensix core. It divides the tensor into smaller tiles, typically 2D tiles of size 32x32 (padded as needed). Each tile is stored in a separate page, enabling efficient access patterns that align with the Tensix core's internal compute units. See `Tile documentation<Tiles>` for details on the tile layout and its implications.

*Figure: The tiled memory layout of a tensor.*

## Memory placement

Due to the lack of a single linear address space, data placement requires explicit decisions about location and distribution across available resources. The following factors determine optimal data placement:

- **Target tile selection**: Which specific tile should store each piece of data
- **Memory type**: Whether data should reside in DRAM or SRAM based on access patterns and capacity requirements
- **Access pattern optimization**: Minimizing NoC traffic by placing frequently accessed data close to consuming cores
- **Compatibility across generations**: Ensuring kernels can run on different Tenstorrent generations with varying memory configurations, without code changes

There is no one-size-fits-all solution for data placement. The optimal strategy depends on the specific kernel, its access patterns and the underlying hardware architecture.

### Lock step allocation

Each generation of Tenstorrent processors has a different memory configuration. For example, Wormhole has 6 DRAM controllers with 2 GB each, while Blackhole has 8 controllers with 4 GB each. Passing in a separate address for each DRAM controller to a kernel is not practical nor scalable. Similarly, providing 64 addresses for each Tensix core (as on a Wormhole n150) for data residing on SRAM is not feasible.

Lock-step allocation solves this problem. For DRAM allocation, the buffer size is divided and rounded up by the number of DRAM tiles. Allocation assumes the processor has only 1/N of the total memory. The resulting address is then shared across all DRAM tiles, effectively multiplying the available space and restoring the allocated area to the requested amount. This approach ensures that a single pointer (plus the memory type, which is known before kernel execution) can uniquely identify an object, regardless of the underlying memory configuration. The same applies to SRAM allocation, where the address is shared across all Tensix cores.

*Figure: The lock-step where single address can be used across multiple DRAM tiles. At the cost of some memory waste.*

Lock step allocation has inherent trade-offs. When allocating X bytes on one DRAM controller, all other controllers must reserve the same amount. Additionally, if the allocation size is not evenly divisible by the number of controllers, some banks will contain unused space. Despite these limitations, the programming model simplification justifies the overhead - kernels receive a single address parameter instead of N hardware-dependent pointers, at the cost of some memory waste and explicit specification of the storage pattern.

### Interleaved memory

Interleaved is the simplest memory placement scheme. Data is round‑robined across all available memory resources at `page_size` granularity. This approach is the most generic and works well for most kernels. It ensures that data is evenly distributed across all memory banks and not hot-spotted on any single one. At the cost of less efficient memory access patterns for certain operations such as matrix multiplication and convolution, where locality is paramount.

The following example is a typical interleaved memory allocation for a DRAM buffer. It allocates a buffer of size `tile_size_bytes * n_tiles` bytes. The `page_size` is set to the size of a tile, which 2KiB for bfloat16 tiles - each DRAM controller will hold a tile of data, and the next tile will be stored on the next DRAM controller, and so on.

``` cpp
constexpr uint32_t n_tiles = 64;
constexpr uint32_t elements_per_tile = tt::constants::TILE_WIDTH * tt::constants::TILE_HEIGHT;
constexpr uint32_t tile_size_bytes = sizeof(bfloat16) * elements_per_tile;

tt_metal::InterleavedBufferConfig dram_config{
    .device = device,
    .size = tile_size_bytes * n_tiles,
    .page_size = tile_size_bytes,
    .buffer_type = tt_metal::BufferType::DRAM};

auto src0_dram_buffer = CreateBuffer(dram_config);
auto in0_addr = src0_dram_buffer->address();

// Tell the kernel how to access the memory
std::vector<uint32_t> compile_time_args; // passed to kernel during kernel setup
TensorAccessorArgs(*src0_dram_buffer).append_to(compile_time_args);
```

The above code allocates 64 tiles of size 2KiB each, for a total of 128KiB. Across DRAM controllers. We can visualize the allocation (as a 1D array) as follows:

*Figure: Allocation of 64 tiles of bfloat16 in interleaved memory on Wormhole (6 DRAM controllers). Each tile is 1024 elements of bfloat16, or 2KiB. The allocation round-robins across the 6 DRAM controllers.*

As interleaved memory is the most common allocation scheme. Instead of manually calculating the address and tile coordinates, utilities are provided to enable easy access. `TensorAccessor` enables efficient, random access to interleaved memory. Allowing tile/page sized granularity for read and writes.

``` cpp
// access parameters are passed in compile time, starting from parameter 0
constexpr auto in0_args = TensorAccessorArgs<0>();
const auto in0 = TensorAccessor(in0_args, in0_addr, tile_size_bytes);
...

for (uint32_t i = 0; i < n_tiles; i++) {
    cb_reserve_back(cb_in0, 1);
    uint32_t cb_in0_addr = get_write_ptr(cb_in0);
    noc_async_read_tile(i, in0, cb_in0_addr); // read the i-th tile from the interleaved buffer

    noc_async_read_barrier();
    cb_push_back(cb_in0, 1);
}
```

### SRAM buffers

It is also possible to allocate buffers in SRAM. This is useful for small buffers that need to be accessed with high bandwidth, low latency and high locality. SRAM provides much higher bandwidth and lower latency than DRAM, making it ideal for intermediate data that needs to be accessed frequently during computation. However, SRAM is a very limited resource, so it is important to use it wisely and deallocate as soon as it is no longer needed.

Allocating on SRAM is exactly the same as allocating on DRAM, except that the buffer type is set to `BufferType::L1`. The following example allocates the same buffer as above, but in SRAM instead of DRAM. In this case, the round-robin allocation is done across all Tensix cores instead of DRAM controllers.

``` cpp
tt_metal::InterleavedBufferConfig sram_config{
    .device = device,
    .size = tile_size_bytes * n_tiles,
    .page_size = tile_size_bytes,
    .buffer_type = tt_metal::BufferType::L1}; // change here

auto src0_sram_buffer = CreateBuffer(sram_config);
auto in0_addr = src0_sram_buffer->address();

std::vector<uint32_t> compile_time_args;
// The knowledge that the buffer lives on SRAM is captured
TensorAccessorArgs(*src0_sram_buffer).append_to(compile_time_args);
```

As allocation type and scheme is known at compile time. The same `TensorAccessor` helper can be used to access the SRAM buffer with 0 change to the kernel.

``` cpp
// Nothing changes compared to reading from DRAM as allocation on DRAM or SRAM is known before
// kernel compilation.
// Whether accessing DRAM or SRAM is stored in TensorAccessorArgs.
constexpr auto in0_args = TensorAccessorArgs<0>();
const auto in0 = TensorAccessor(in0_args, in0_addr, tile_size_bytes);
...

for (uint32_t i = 0; i < n_tiles; i++) {
    cb_reserve_back(cb_in0, 1);
    uint32_t cb_in0_addr = get_write_ptr(cb_in0);
    noc_async_read_tile(i, in0, cb_in0_addr);

    noc_async_read_barrier();
    cb_push_back(cb_in0, 1);
}
```

### Sharded tensor

Interleaved memory, while simple and generic, does not always provide optimal performance for all kernels. It can lead to NoC contention since each link can only carry one packet at a time. When multiple packets attempt to traverse the same link, one must wait, causing delays and reduced throughput. The problem is true for both Interleaved DRAM and SRAM buffers. This is particularly problematic for high-bandwidth kernels with predictable access patterns, such as matrix multiplication or convolution. In these cases, more advanced memory allocation schemes that reduce contention and improve data locality often provide better performance.

*Figure: It is possible to have contention on the NoC when multiple packets try to traverse the same link.*

Sharded memory is a more advanced allocation scheme that allows for, but not necessarily makes, a more efficient memory access pattern. It is used for kernels that require more control over data placement and access patterns. Sharded memory allows you to specify which tiles should store which data, and how the data should be partitioned across those tiles.

Metalium supports several sharding schemes:

- **Height sharding**: Data is partitioned across tiles based on the height dimension
- **Width sharding**: Data is partitioned across tiles based on the width dimension
- **Block sharding**: Data is partitioned across tiles on both width and height dimensions

Sharding is usually only done for SRAM buffers.

``` cpp
using namespace tt::constants;
ShardSpecBuffer shard_spec(
    cores,                                            // The core grid on which data is distributed on
    { uint32_t(tiles_per_core_width * TILE_HEIGHT),   // Width and height in bytes
      uint32_t(tiles_per_core_height * TILE_WIDTH) },
    ShardOrientation::ROW_MAJOR,                      // direction (across cores) to distribute shards
    { TILE_HEIGHT, TILE_WIDTH },                      // Page size in elements
    { height_tiles, width_tiles });                   // shape of the overall matrix/tensor in shards

// Allocate a sharded buffer in L1
auto buf = CreateBuffer(ShardedBufferConfig{
    .device = device,
    .size = n_tiles * tile_size_bytes,
    .page_size = tile_size_bytes,
    .buffer_layout = TensorMemoryLayout::HEIGHT_SHARDED,
    .shard_parameters = shard_spec});

// Describe access pattern for kernel (compile-time args packing helper).
std::vector<uint32_t> compile_time_args;
TensorAccessorArgs(*buf).append_to(compile_time_args);
```

Accessing of sharded memory is done exactly like accessing interleaved memory. `TensorAccessor` enables efficient, random access to sharded memory. Allowing tile/page sized granularity for read and writes.

> [!NOTE]
> Note the concepts (DRAM vs SRAM, interleaved vs sharded) are mostly independent of each other. You can have interleaved DRAM buffers (most common), interleaved SRAM buffers (often used for temporary data), sharded SRAM buffers (for specific use cases where they benefit from the bandwidth) and sharded DRAM buffers (rarely used due to limited DRAM vs NoC bandwidth thus not described above). The best approach depends on the specific kernel and its access patterns.

## Source: docs/source/tt-metalium/tt_metal/advanced_topics/tiles.rst

# Tiles

Most compute and data movement on the Tensix processor use a tile as the fundamental unit. This page describes the tile structure, the memory layout of a tile and conversion between tiles and row major data (as used by most applications).

A tile is a 32x32 grid of values. Other tile sizes exist but currently have limited support. All elements in a tile share the same data type (integer, floating point, or block floating point).

A tile's memory footprint depends on the underlying element's data type. For 32-bit floating point elements, a tile occupies 4KB (32 x 32 x 4 bytes = 4096 bytes). For bfloat16 elements, a tile occupies 2KB (32 x 32 x 2 bytes = 2048 bytes). The size of each tile can be looked up programmatically by calling `tt::tile_size(DataFormat)`.

Tiles are fixed-size data structures, so matrices and tensors must be aligned to tile boundaries. When data dimensions don't align naturally, they must be padded to the nearest tile boundary. As tiles are 2D structures, padding is only needed in the last two dimensions. Higher-dimensional tensors (3D or more) only require padding in their final two dimensions. Most operations do not care about the specific value of padding as eventually they are disregarded when converted back into row-major. However, some, including matrix multiplication do. Thus it is advised to pad with zeros.

*Figure: A 1024x48 matrix would be padded to 1024x64 to ensure that each row of 32 elements is aligned to a tile boundary.*

> [!WARNING]
> The Tensix Processor is a little-endian architecture. Though all officially host architectures supported by Metalium are all little-endian, extra care must be taken when the host system may be big-endian.

## Internal structure of a Tile

Most tiles are not stored as a simple flat array. Instead, a 32x32 tile is subdivided into four 16x16 faces, where each face is stored as a contiguous block in memory. The faces are arranged sequentially in memory, creating a hierarchical structure that enables efficient access patterns for the matrix and vector engines in each Tensix core.

*Figure: A 32x32 tile is organized into four 16x16 faces.*

For example, consider a bfloat16 tile starting at address `0x1000` with a size of `0x800` (2KB). The tile occupies memory from `0x1000` to `0x17FF`, with the four 16x16 faces located at addresses `0x1000`, `0x1200`, `0x1400`, and `0x1600` respectively.

*Figure: Memory layout of a 32x32 tile with 16x16 faces with address of each face annotated.*

> [!NOTE]
> Other face sizes, orientation and count are possible but with limited support. The 32x32 tile with four 16x16 faces stored in a 2D array format is the most common and well supported configuration of tiles.

The following C function demonstrates the conversion from a 32x32 row-major matrix to the tile format with 16x16 faces:

``` c++
void convert_to_tile(float* out, const float* input) {
    // input must be a 32x32 tile
    for (int i = 0; i < 32; i++) {
        for (int j = 0; j < 32; j++) {
            int face_row = i / 16;
            int face_col = j / 16;
            int face_index = face_row * 2 + face_col;
            int element_row = i % 16;
            int element_col = j % 16;
            int offset = face_index * 16 * 16 + element_row * 16 + element_col;
            out[offset] = input[i * 32 + j];
        }
    }
}
```

The following Python implementation achieves the same conversion using NumPy's array operations:

``` python
import numpy as np

def convert_to_tile(arr: np.ndarray) -> np.ndarray:
    if arr.shape != (32, 32):
        raise ValueError("Input must have shape (32, 32)")
    faces = arr.reshape(2, 16, 2, 16).transpose(0, 2, 1, 3).reshape(4, 16, 16)
    return faces.reshape(32, 32) # Now the data is ordered in the tile format
```

To convert from tile format back to row-major format, the process is reversed by swapping the source and destination arrays in the indexing calculation:

``` c
void convert_from_tile(float* out, const float* input) {
    // input must be a 32x32 tile
    for (int i = 0; i < 32; i++) {
        for (int j = 0; j < 32; j++) {
            int face_row = i / 16;
            int face_col = j / 16;
            int face_index = face_row * 2 + face_col;
            int element_row = i % 16;
            int element_col = j % 16;
            int offset = face_index * 16 * 16 + element_row * 16 + element_col;
            out[i * 32 + j] = input[offset];
        }
    }
}
```

A Python/NumPy implementation of the same reversal is as follows:

``` python
import numpy as np

def convert_from_tile(arr: np.ndarray) -> np.ndarray:
    # arr must be a 32x32 matrix in the tile data format
    if arr.shape != (32, 32):
        raise ValueError("Input must have shape (32, 32)")
    faces = arr.reshape(4, 16, 16)
    rm = faces.reshape(2, 2, 16, 16).transpose(0, 2, 1, 3).reshape(32, 32)
    return rm # Now the data is ordered row major
```

## Conversion between tiles and row-major format

Metalium provides `convert_layout` to convert matrices and tensors into tile format that resides in host memory. This function handles data beyond single tiles, provided the input is aligned and padded to tile boundaries, and supports all CPU-handled element types (standard integer types, FP32, bfloat16, etc.) - most formats except block floating point variants.

`convert_layout` requires four parameters:

- Input data
- Input data shape
- Source layout type
- Target layout type

The following example shows matrix conversion to tile format. `NFACES` in `TILED_NFACES` refers to the number of faces within each tile. The function supports different tile and face configurations. By default, it uses 32x32 tiles with four 16x16 faces as described above:

``` c++
// matrix of shape 2x64x64
std::vector<float> input_matrix(2*64*64);
// Do something with input_matrix
...
// convert to tiles
auto tiled_matrix = tt::tt_metal::convert_layout(input_matrix,
    {2, 64, 64},
    tt::tt_metal::TensorLayoutType::LIN_ROW_MAJOR,
    tt::tt_metal::TensorLayoutType::TILED_NFACES);
```

And the reverse:

``` c++
// convert back to original layout
auto original_matrix = tt::tt_metal::convert_layout(tiled_matrix,
    {2, 64, 64},
    tt::tt_metal::TensorLayoutType::TILED_NFACES,
    tt::tt_metal::TensorLayoutType::LIN_ROW_MAJOR);
```

> [!NOTE]
> For TTNN users: `convert_layout` executes on the CPU in a single thread and does not use the Tensix Processor. Use `ttnn::tilize()` and `ttnn::untilize()` for layout conversion, or `ttnn::tilize_with_zero_padding()` and `ttnn::tilize_with_val_padding()` to handle non tile aligned data automatically. In most cases these on-device functions are much faster then the CPU counterpart as they can take advantage of the higher DRAM bandwidth and higher core count of the device. Please refer to the TTNN documentation for detail.
>
> For example:
>
> ``` c++
> auto t = ttnn::ones(ttnn::Shape({1024, 48})).to(device);
> // Conversion happens on device
> auto tiled = ttnn::tilize_with_zero_padding(t);
> auto untiled = ttnn::untilize(tiled);
> ```

## Source: docs/source/tt-metalium/tt_metal/examples/dram_loopback.rst

# DRAM Loopback

This is the simplest example of using the TT-Metal API. A data movement core in the Tensix copies data from DRAM into its L1(SRAM) buffer and back out to DRAM. Hence "loopback".

We'll go through this code section by section. The full source code for this example is available under the `tt_metal/programming_examples/loopback` directory.

Building the example can be done by adding a `--build-programming-examples` flag to the build script or adding the `-DBUILD_PROGRAMMING_EXAMPLES=ON` flag to the cmake command and results in the `loopback` executable in the `build/programming_examples` directory. For example:

``` bash
export TT_METAL_HOME=</path/to/tt-metal>
./build_metal.sh --build-programming-examples
# To run the example
./build/programming_examples/loopback
```

## Device initialization

``` cpp
constexpr int device_id = 0;
auto device = CreateDevice(device_id);
```

First we open a device. This is our gateway to all operations on the accelerator. The device ID is simply an index into the list of available devices (from 0 to N-1). Thus device 0 is the first device and always available if one is installed.

## Program setup

``` cpp
CommandQueue& cq = device->command_queue();
Program program = CreateProgram();
```

Operations in Metalium are almost always capable to be run asynchronously and the ordering of operations is managed by a command queue. The command queue, like the name suggests, is a FIFO queue of commands that are executed in order. And commands are operations that are run on the device, including but not limited to upload/download of data and program execution.

Next, we create a `Program` object that we will fill in later. A program is a set of kernels that are executed on the device. If you are familiar with OpenCL, the program in Metalium is different from OpenCL in that All Tensix cores need to to run the exact same kernel at the same time. However in this example, we are only going to use one of all the cores in the device.

## Create buffers in DRAM and L1 (SRAM)

Next, we need to declare buffers that will hold the actual data and an intermediate buffer on chip,

There's in total 3 buffers to be created:

- An L1 (SRAM) buffer within the core itself that will act as temporary storage
- A DRAM buffer that will house input data
- A DRAM buffer that will be written to with output data

There are two types of buffers in the Tensix: L1 and DRAM. L1 is a misnomer as it can be mistaken as similar to L1 cache in a CPU. In fact, the L1 is a SRAM scratchpad on the Tensix. Each generation of Tenstorrent processors has a different amount of L1 memory per Tensix. Grayskull had 1MB and Wormhole/Blackhole has 1.5MB.

Note that almost all operations on the Tensix are aligned with tiles. And a tile is a 32x32 grid of values. The data type used in this example is bfloat16 as it is what the math engine uses internally (though we won't touch the math engine in this example). Making each tile 32 x 32 x 2 bytes = 2048 bytes. And we wish to allocate 50 tiles in for each (input and output) DRAM buffer. Thus the total size of each DRAM buffer is 50 \* 2048 = 102400 bytes. And a single tile worth of buffer on the L1 is 2048 bytes as well. So that we can copy a single tile at a time.

Note the `page_size` argument in the buffer config and the `Interleaved` in the buffer type. Both L1 and DRAM are split into banks. Each bank is a physical memory unit that can be accessed independently. However, managing banks separately is tricky and not scalable. Interleaved buffers simply round-robin the data across all banks every `page_size` bytes. This allows the programmer to treat the buffer as a single unit, while taking advantage of the parallelism of the banks for higher bandwidth. Usually the page size is set to the tile size, which is 2048 bytes in this case. This enabels easy programming while still maintaining high performance. Other values are also supported, but the programmer is then responsible for the performance implications and programming complexity.

The L1 buffer is created with a size equal to the size of a single tile, which will act as a buffer for old temporary data. Then be written back to DRAM.

``` cpp
constexpr uint32_t num_tiles = 50;
constexpr uint32_t tile_size = TILE_WIDTH * TILE_HEIGHT;
constexpr uint32_t single_tile_size = sizeof(bfloat16) * tile_size;
constexpr uint32_t dram_buffer_size = single_tile_size * num_tiles;
tt_metal::InterleavedBufferConfig l1_config{
    .device=device,
    .size = single_tile_size,
    .page_size = single_tile_size,
    .buffer_type = tt_metal::BufferType::L1
};

Buffer l1_buffer = CreateBuffer(l1_config);
```

The only difference between the L1 and DRAM buffer is the `BufferType`. The L1 buffer is created with a `BufferType::L1` and the DRAM buffer is created with a `BufferType::DRAM`.

``` cpp
tt_metal::InterleavedBufferConfig dram_config{
    .device=device,
    .size = dram_buffer_size,
    .page_size = single_tile_size,
    .buffer_type = tt_metal::BufferType::DRAM
};

Buffer input_dram_buffer = CreateBuffer(dram_config);
const uint32_t input_dram_buffer_addr = input_dram_buffer.address();

Buffer output_dram_buffer = CreateBuffer(dram_config);
const uint32_t output_dram_buffer_addr = output_dram_buffer.address();
```

## Sending real data into DRAM

``` cpp
std::vector<bfloat16> input_vec(num_tiles * tile_size);
std::mt19937 rng(std::random_device{}());
std::uniform_real_distribution<float> distribution(0.0f, 100.0f);
for (auto& val : input_vec) {
    val = bfloat16(distribution(rng));
}
EnqueueWriteBuffer(cq, input_dram_buffer, input_vec, false);
```

Send in a randomly-generated BFP16 (Brain 16bit floating point) vector that will act as our input data tensor.

Note the final `false` argument. This indicates to tt-Metalium that the upload is non-blocking. The function may return as soon as possible while data transfer is still in progress. This is useful for performance, but the program is responsible for ensuring that the the source buffer is not freed before the transfer is complete. In this case, there are future blocking calls/calls to `Finish` that will ensure commands are completed before the program exits, which is also when the source buffer is freed.

## Creating a data movement kernel

Create a kernel that will copy data from DRAM to L1 and back. Since we are only using one Tensix core, `{0, 0}` is the only core (core on the most top left) we use. And as we are moving data from DRAM to L1, This is a data movement kernel using the movement processor 0, and the default NoC interface.

``` cpp
constexpr CoreCoord core = {0, 0};
std::vector<uint32_t> compile_args;
TensorAccessorArgs(*input_dram_buffer).append_to(compile_args);
TensorAccessorArgs(*output_dram_buffer).append_to(compile_args);

KernelHandle dram_copy_kernel_id = CreateKernel(
    program,
    "tt_metal/programming_examples/loopback/kernels/loopback_dram_copy.cpp",
    core,
    DataMovementConfig{.processor = DataMovementProcessor::RISCV_0, .noc = NOC::RISCV_0_default, .compile_args = compile_args}
);
```

> [!NOTE]
> The path to the kernel source file can either be
>
> - Relative to the `TT_METAL_KERNEL_PATH` environment variable (or `TT_METAL_HOME` if the former is not set), or
> - Absolute path to the file, or
> - Relative to the current working directory
>
> Metalium will search for the kernel source file in order of the above. In this case the kernel will be found relative to `TT_METAL_HOME`. If the file is not found, an error will be thrown.

The kernel itself is simple. It takes the address and bank indices we just created. Copies data from the input DRAM buffer to the L1 buffer and then back out to the output DRAM buffer. You might notice that the kernel is using `uint32_t` instead of pointers for addresses. This is intended design as the DRAM is not directly addressable by the kernels. Instead, access requests are sent to the NoC (Network on Chip) and be brought to the L1 before the kernel can access it in a meaningful way. However, letting the RISC-V core directly access the L1 is not the most efficient way to move data around. Thus the L1 address is also an integer.

The `TensorAccessor` object handles bank addressing and page size automatically, simplifying interleaved or sharded buffer access. Data transfers are asynchronous, allowing the kernel to issue multiple requests while transfers are in progress. This improves performance by utilizing on-core resources more efficiently. In this example, we use `noc_async_read_barrier()` and `noc_async_write_barrier()` after each operation to ensure data integrity before proceeding to the next loop iteration.

``` cpp
// tt_metal/programming_examples/loopback/kernels/loopback_dram_copy.cpp
void kernel_main() {
    std::uint32_t l1_buffer_addr        = get_arg_val<uint32_t>(0);
    std::uint32_t dram_buffer_src_addr  = get_arg_val<uint32_t>(1);
    std::uint32_t dram_buffer_dst_addr  = get_arg_val<uint32_t>(2);
    std::uint32_t num_tiles             = get_arg_val<uint32_t>(3);

    const uint32_t tile_size_bytes = 32 * 32 * 2; // same tile size as in the host code

    constexpr auto in0_args = TensorAccessorArgs<0>();
    const auto in0 = TensorAccessor(in0_args, dram_buffer_src_addr, tile_size_bytes);

    constexpr auto out0_args = TensorAccessorArgs<in0_args.next_compile_time_args_offset()>();
    const auto out0 = TensorAccessor(out0_args, dram_buffer_dst_addr, tile_size_bytes);

    for(uint32_t i=0;i<num_tiles;i++) {
        noc_async_read_tile(i, in0, l1_buffer_addr);
        noc_async_read_barrier();

        noc_async_write_tile(i, out0, l1_buffer_addr);
        noc_async_write_barrier();
    }
}
```

> [!NOTE]
> `TensorAccessor` handles address generation for all kinds of buffers automatically. Without the helper, the kernel implementation would be:
>
> ``` cpp
> constexpr std::uint32_t num_dram_banks = 6; // Number of DRAM banks on Wormhole
> for (uint32_t i = 0; i < num_tiles; i++) {
>     // Round-robin bank selection
>     uint32_t bank_id = i % num_dram_banks;
>     // Offset within the bank for the current tile
>     uint32_t offset_within_bank = i / num_dram_banks * tile_size_bytes;
>     std::uint64_t dram_buffer_src_noc_addr =
>         get_noc_addr_from_bank_id</*dram=*/true>(bank_id, dram_buffer_src_addr + offset_within_bank);
>     std::uint64_t dram_buffer_dst_noc_addr =
>         get_noc_addr_from_bank_id</*dram=*/true>(bank_id, dram_buffer_dst_addr + offset_within_bank);
>
>     noc_async_read(dram_buffer_src_noc_addr, l1_buffer_addr, tile_size_bytes);
>     noc_async_read_barrier();
>     noc_async_write(l1_buffer_addr, dram_buffer_dst_noc_addr, tile_size_bytes);
>     noc_async_write_barrier();
> }
> ```

## Setting runtime arguments for the data movement kernel

``` cpp
const std::vector<uint32_t> runtime_args = {
    l1_buffer.address(),
    input_dram_buffer.address(),
    output_dram_buffer.address(),
    num_tiles
};

SetRuntimeArgs(
    program,
    dram_copy_kernel_id,
    core,
    runtime_args
);
```

We now set runtime arguments for our data movement kernel. The kernel can then access these arguments at runtime. For this specific kernel, we need to pass in the following arguments:

- Where the L1 buffer starts (memory address)
- Where the input DRAM buffer starts (memory address)
- Where the output DRAM buffer starts (memory address)
- How many tiles we are copying (this is used to determine how many times to copy data)

## Running the program

``` cpp
EnqueueProgram(cq, program, false);
Finish(cq);
// Equivalently, we could have done:
// EnqueueProgram(cq, program, true);
```

Finally, we launch our program. The `Finish` call waits for the the host program only continues execution after everything in the command queue has been completed. The final argument in `EnqueueProgram` indicates that the program is non-blocking. Setting it to `true` would cause the program to block until the program is finished. Efficiently, this is the same as calling `Finish` after the program is enqueued.

## Download the result and verify output

Then we can finally read back the data from the output buffer and assert that it matches what we sent. Again the final `true` argument causes the data transfer to be blocking. Thus we know that the data is fully available when the function returns.

``` cpp
std::vector<bfloat16> result_vec;
EnqueueReadBuffer(cq,output_dram_buffer, result_vec, true);

for (int i = 0; i < input_vec.size(); i++) {
  if (input_vec[i] != result_vec[i]) {
      pass = false;
      break;
  }
}
```

## Validation and teardown

``` cpp
pass &= CloseDevice(device);
```

We now use `CloseDevice` to teardown our device. This releases resources associated with the device.

Now we can start adding some compute to our program. Please refer to the `Eltwise binary example<Eltwise binary example>`.

## Source: docs/source/tt-metalium/tt_metal/examples/eltwise_binary.rst

# Eltwise binary

We now build a program that performs elementwise binary operations on a pair of equal-sized tensors using the FPU (matrix engine). The FPU can perform a variety of complex operations efficiently, including matrix multiplication and reduction. It can also perform common elementwise operations like addition. This example will add two tensors together using the FPU.

Although looking trivial, this example introduces essential concepts that are used in more complicated programs. Namely the compute kernel and the use of circular buffers. Tenstorrent devices are designed with explicit data movement in mind. Leading to a separate compute kernel. And for circular buffers is the primary way to move data between kernels.

We'll go through any new code section by section. This builds on top of previous examples. Note that we have this exact, full example program is located under `tt_metal/programming_examples/eltwise_binary`, so you can follow along.

To build and execute, you may use the following commands. Note that we include the necessary environment variables here, but you may possibly need more depending on the most up-to-date installation methods.

``` bash
export TT_METAL_HOME=</path/to/tt-metal>
./build_metal.sh --build-programming-examples
# To run the example
./build/programming_examples/eltwise_binary
```

## Program setup

Initializing Metalium is almost the same as before. To recap, we need to

1.  Open a device (again we are using device 0)
2.  Obtain the command queue to issue down/uploads and program execution
3.  Create a program object to hold our kernels
4.  Define the core we are going to use (in this case, only one at {0, 0})
5.  Some basic constants for tile and total buffer sizes

``` cpp
constexpr int device_id = 0;
IDevice* device = CreateDevice(device_id);

CommandQueue& cq = device->command_queue();

Program program = CreateProgram();

constexpr CoreCoord core = {0, 0};
constexpr uint32_t n_tiles = 64;
constexpr uint32_t elements_per_tile = TILE_WIDTH * TILE_HEIGHT;
constexpr uint32_t tile_size_bytes = sizeof(bfloat16) * elements_per_tile;
```

This time, instead of 2 DRAM buffers to copy data out and back, we will create 3 buffers. 2 as data sources and 1 as the output. Page size is set to one tile. This is the most common setting for buffers in Metalium as the compute engines expect to operate on tiles of data.

``` cpp
InterleavedBufferConfig config{
    .device = device,                       // The device to create the buffer on
    .size = n_tiles * tile_size_bytes,      // The size of the buffer in bytes
    .page_size = tile_size_bytes,           // The page size of the buffer in bytes. In this case, will be
                                            // one tile per page.
    .buffer_type = BufferType::DRAM};       // This is a DRAM buffer.
auto src0_dram_buffer = CreateBuffer(config);
auto src1_dram_buffer = CreateBuffer(config);
auto dst_dram_buffer = CreateBuffer(config);
```

Data preparation and upload is the same as before. For this example, buffer 0 will be filled with random values, and buffer 1 will be filled with a constant of -1 just for demonstration purposes. The data is then uploaded to the device asynchronously like before.

``` cpp
constexpr float val_to_add = -1.0f;
std::mt19937 rng(std::random_device{}());
std::uniform_real_distribution<float> distribution(0.0f, 1.0f);
std::vector<bfloat16> src0_data(elements_per_tile * n_tiles);
std::vector<bfloat16> src1_data(elements_per_tile * n_tiles, bfloat16(val_to_add));
for(auto& val : a_data) {
    val = bfloat16(distribution(rng));
}
// Upload the data from host to the device.
EnqueueWriteBuffer(cq, src0_dram_buffer, a_data, false);
EnqueueWriteBuffer(cq, src1_dram_buffer, b_data, false);
```

## Circular buffers

Here we introduce a new concept: circular buffers. They are communication channels between the different kernel on a Tensix. Conceptually they act as pipes between different kernels. There are in total 32 circular buffers supported on a Tensix. To utilize them, the host program must allocate the circular buffers and utilize the appropriate circular buffer index in the kernel.

``` cpp
constexpr uint32_t tiles_per_cb = 2;
tt::CBIndex src0_cb_index = tt::CBIndex::c_0;
CircularBufferConfig c0_cfg = CircularBufferConfig(
    /*total_size=*/tiles_per_cb * tile_size_bytes,
    /*data_format_spec=*/{{src0_cb_index, tt::DataFormat::Float16_b}})
    .set_page_size(src0_cb_index, tile_size_bytes);
CBHandle cb_src0 = CreateCircularBuffer(program, core, c0_cfg);

tt::CBIndex src1_cb_index = tt::CBIndex::c_1;
CBHandle cb_src1 = CreateCircularBuffer(program, core, CircularBufferConfig(
    /*total_size=*/tiles_per_cb * tile_size_bytes,
    /*data_format_spec=*/{{src1_cb_index, tt::DataFormat::Float16_b}})
    .set_page_size(src1_cb_index, tile_size_bytes));
tt::CBIndex dst_cb_index = tt::CBIndex::c_16;
CBHandle cb_dst = CreateCircularBuffer(program, core, CircularBufferConfig(
    /*total_size=*/tiles_per_cb * tile_size_bytes,
    /*data_format_spec=*/{{dst_cb_index, tt::DataFormat::Float16_b}})
    .set_page_size(dst_cb_index, tile_size_bytes));
```

The API to create a circular buffer is more complicated than for a buffer, providing finer grained control for advanced use cases. At the core, there are a few critical parameters:

- The index of the circular buffer
- The total size of the circular buffer in bytes (and thus the number of pages within)
- The data format of the circular buffer (bfloat16, block float4, etc..)
- How large each pages is
  - For most cases, this should be the same as the size of a tile of the underlying data format

For instance, to create a circular buffer of 2 tiles of bfloat16 data, we need to set the total size to `2 * tile_size_bytes`. The page size set to `tile_size_bytes` and the data format is set to bfloat16.

## Data movement and compute kernels

In the previous example (DRAM loopback), we used a single kernel to perform the entire operation; to read data from DRAM and write it back out. The Tensix core in fact contains 5 RISC-V cores. 2 of them are the data movement cores, which connects to the NoC and can issue commands to access other on chip resources (including DRAM). The other 3 are compute cores, which operates cooperatively and runs a single compute kernel. They have access to the matrix and vector engines, which performs the majority of the compute work on a Tensix.

> [!NOTE]
> Unlike traditional multi core processors. Where a problem is broken down into subtasks as assigned to the cores while each core runs the same code (SPMD, single program multiple data). The compute cores on a Tensix are designed to run different code. The compute kernel is compiled 3 times. Once for each of the 3 compute cores and generating 3 different binaries. They work collaboratively to perform a single task. The 3 compute cores are the Unpack, Math and Pack cores. They are responsible for moving data from L1 into the matrix or vector engines, issue commands for computation and moving the results back out to L1. Which can be done at the same time for high throughput.

``` cpp
std::vector<uint32_t> reader_args;
TensorAccessorArgs(*src0_dram_buffer).append_to(reader_args);
TensorAccessorArgs(*src1_dram_buffer).append_to(reader_args);
auto reader = CreateKernel(
    program,
    "tt_metal/programming_examples/eltwise_binary/kernels/dataflow/read_tiles.cpp",
    core,
    DataMovementConfig{.processor = DataMovementProcessor::RISCV_0, .noc = NOC::RISCV_0_default, .compile_args = reader_args});
std::vector<uint32_t> writer_args;
TensorAccessorArgs(*dst_dram_buffer).append_to(writer_args);
auto writer = CreateKernel(
    program,
    "tt_metal/programming_examples/eltwise_binary/kernels/dataflow/write_tile.cpp",
    core,
    DataMovementConfig{.processor = DataMovementProcessor::RISCV_1, .noc = NOC::RISCV_1_default, .compile_args = writer_args});
auto compute = CreateKernel(
    program,
    "tt_metal/programming_examples/eltwise_binary/kernels/compute/tiles_add.cpp",
    core,
    ComputeConfig{.math_fidelity = MathFidelity::HiFi4});
```

Notice the `ComputeConfig` object. This indicates to the framework that a compute kernel should be created. There's a plethora of settings that can be set here. The most important one is the `math_fidelity` setting. This controls how accurate certain floating point operations are on the FPU specifically. Other operations (like the ones in the vector engine) are not\_ affected by this setting.

Now let's look at the kernels. First the reader kernel. This kernel reads both input buffers from DRAM and pushes them into the circular buffers (will discuss in the following section) for the compute kernel to consume. For now, consider the circular buffers as a pipe. Data can be pushed into the pipe and read out of it. And both ends must ensure there is space to do so.

To do so, the reader creates 2 interleaved address generators. Unlike on most processors, the Tensix doesn't just see raw bytes. The address generator contains metadata about the data it is associated to enable the data be read out of the DRAM in the correct format. Then in a loop, the program waits for space to be available in the circular buffers. Once there is, it reads a tile from DRAM and pushes it into the circular buffer. The `noc_async_read_barrier()` call ensures waits for the read to finish before committing the data to the circular buffer. This is important as the read is asynchronous and data is not guaranteed to be there when the program continues.

``` cpp
// tt_metal/programming_examples/eltwise_binary/kernels/dataflow/read_tiles.cpp
void kernel_main() {
    uint32_t in0_addr = get_arg_val<uint32_t>(0);
    uint32_t in1_addr = get_arg_val<uint32_t>(1);
    uint32_t n_tiles = get_arg_val<uint32_t>(2);

    // The circular buffers to read the tiles into (same as the ones in the host program)
    constexpr uint32_t cb_in0 = tt::CBIndex::c_0;
    constexpr uint32_t cb_in1 = tt::CBIndex::c_1;

    const uint32_t tile_size_bytes = get_tile_size(cb_in0);

    constexpr auto in0_args = TensorAccessorArgs<0>();
    const auto in0 = TensorAccessor(in0_args, in0_addr, tile_size_bytes);

    constexpr auto in1_args = TensorAccessorArgs<in0_args.next_compile_time_args_offset()>();
    const auto in1 = TensorAccessor(in1_args, in1_addr, tile_size_bytes);

    for (uint32_t i = 0; i < n_tiles; i++) {
        cb_reserve_back(cb_in0, 1);
        cb_reserve_back(cb_in1, 1);

        noc_async_read_tile(i, in0, get_write_ptr(cb_in0));
        noc_async_read_tile(i, in1, get_write_ptr(cb_in1));

        // Wait until tile reads are done
        noc_async_read_barrier();
        cb_push_back(cb_in0, 1);
        cb_push_back(cb_in1, 1);
    }
}
```

The compute kernel performs the actual elementwise addition. It initializes the matrix engine for addition, then enters a loop. Inside the loop, it waits for data to be available in the input circular buffers, and for the destination registers to be free. The destination registers (16 in total, with 8 usable at a time) are used to transfer data to and from the computation engines. The kernel adds the input tiles, writes the result to destination register 0, waits to be sure the result is ready, and waits for the output circular buffer to have space, and pushes the computed tile into it. Finally, it marks the input tiles as consumed, the output tile as produced, and releases the registers.

``` cpp
// tt_metal/programming_examples/eltwise_binary/kernels/compute/tiles_add.cpp
namespace NAMESPACE {
void MAIN {
    uint32_t n_tiles = get_arg_val<uint32_t>(0);

    constexpr auto cb_in0 = tt::CBIndex::c_0;
    constexpr auto cb_in1 = tt::CBIndex::c_1;
    constexpr auto cb_out0 = tt::CBIndex::c_16;

    constexpr uint32_t dst_reg_id = 0;

    binary_op_init_common(cb_in0, cb_in1, cb_out0);
    add_tiles_init(cb_in0, cb_in1);

    // Loop over all the tiles and perform the computation
    for (uint32_t i = 0; i < n_tiles; i++) {
        cb_wait_front(cb_in0, 1);
        cb_wait_front(cb_in1, 1);

        tile_regs_acquire();

        add_tiles(cb_in0, cb_in1, /*offset_0*/0, /*offset_1*/0, dst_reg_id);

        tile_regs_commit();
        tile_regs_wait();

        cb_reserve_back(cb_out0, 1);
        pack_tile(dst_reg, cb_out0); // copy result to out0
        tile_regs_release();

        cb_push_back(cb_out0, 1);
        cb_pop_front(cb_in0, 1);
        cb_pop_front(cb_in1, 1);
    }
}
}
```

The writer kernel looks similar to the reader kernel. Instead of reading, it writes data back into DRAM and uses the appropriate API to do so.

``` cpp
// tt_metal/programming_examples/eltwise_binary/kernels/dataflow/write_tile.cpp
void kernel_main() {
    uint32_t out_addr = get_arg_val<uint32_t>(0);
    uint32_t n_tiles = get_arg_val<uint32_t>(1);

    // same as the one in the host program
    constexpr uint32_t cb_out0 = tt::CBIndex::c_16;

    const uint32_t tile_size_bytes = get_tile_size(cb_out0);

    constexpr auto out_args = TensorAccessorArgs<0>();
    const auto out = TensorAccessor(out_args, out_addr, tile_size_bytes);

    for (uint32_t i = 0; i < n_tiles; i++) {
        cb_wait_front(cb_out0, 1);
        noc_async_write_tile(i, out, get_read_ptr(cb_out0));
        noc_async_write_barrier();
        cb_pop_front(cb_out0, 1);
    }
```

Then the host program sets the kernel arguments and launches the program. There is no difference in setting the arguments for the compute kernel.

> [!NOTE]
> Unlike OpenCL/CUDA. Each kernel (reader, compute and writer) can have it's own set of arguments. Furthermore, on a multi cored program (i.e. using more then 1 Tensix core), kernels within each core can have different arguments. This enables Metalium to exploit the grid like nature of the Tenstorrent processors to achieve high performance.

``` cpp
SetRuntimeArgs(program, reader, core, {src0_dram_buffer->address(), src1_dram_buffer->address(), n_tiles});
SetRuntimeArgs(program, writer, core, {dst_dram_buffer->address(), n_tiles});
SetRuntimeArgs(program, compute, core, {n_tiles});

EnqueueProgram(cq, program, false);
Finish(cq);
```

## Download the result and verify output

Finally, we download the result and verify the output. Again we read the data into a vector and wait for the transfer to finish. The result is then compared to the expected output. Note that we use a loose tolerance for the comparison because of the nature of bfloat16.

``` cpp
std::vector<bfloat16> result_vec;
EnqueueReadBuffer(cq, dst_dram_buffer, result_vec, /*blocking=*/true);

constexpr float eps = 1e-2f; // loose tolerance because of the nature of bfloat16
TT_FATAL(result_vec.size() == a_data.size(), "Result vector size mismatch");
for (size_t i = 0; i < result_vec.size(); ++i) {
    const float expected = a_data[i].to_float() + val_to_add;
    const float actual = result_vec[i].to_float();

    if (std::abs(expected - actual) > eps) {
        pass = false;
        tt::log_error(tt::LogTest, "Result mismatch at index {}: expected {}, got {}", i, expected, actual);
    }
}
```

## Validation and teardown

``` cpp
pass &= CloseDevice(device);
```

We now use `CloseDevice` to teardown our device. This releases resources associated with the device.

Next we will explore the use of the vector engine (SFPU) to perform the same operation. `Eltwise sfpu example<Eltwise sfpu example>`.

## Source: docs/source/tt-metalium/tt_metal/examples/eltwise_sfpu.rst

# Eltwise SFPU

We now build a program that will perform operations using the SFPU (vector engine/Special Function Processing Unit). Though not packing as much punch as the FPU (Matrix Engine), the SFPU is a powerful unit that can perform complex element-wise operations. This example will show how to use the SFPU to perform `exp(x)` on the input data.

This example is similar to the previous example of adding two vectors using the FPU. But instead of using the FPU, we will use the SFPU. And only 1 input buffer is used instead of 2. The SFPU can perform a variety of operations not just exponential, such as square root, sine, cosine, ReLU and more.

We'll go through this code section by section. The fully source code for this example is available under the `tt_metal/programming_examples/eltwise_sfpu` directory.

Building the example can be done by adding a `--build-programming-examples` flag to the build script or adding the `-DBUILD_PROGRAMMING_EXAMPLES=ON` flag to the cmake command and results in the `eltwise_sfpu` executable in the `build/programming_examples` directory. For example:

``` bash
export TT_METAL_HOME=</path/to/tt-metal>
./build_metal.sh
./build/programming_examples/eltwise_sfpu
```

## Program setup

Like the previous examples, setting up programs running on the accelerator is similar

- Allocate buffers for both input and output data
- Allocate circular buffers for communication between kernels
- Setup both data movement and compute kernels

First, allocate the buffers using the interleaved config with page size set to the tile size (in bytes). This is the most common buffer type and configuration used in Metalium as it fits how the compute engine expects data to be sent in. Then data is generated and written to the source buffer. The destination buffer is not initialized as it will be filled with the results later.

``` cpp
tt_metal::InterleavedBufferConfig dram_config{
    .device = device,
    .size = tile_size_bytes * n_tiles,
    .page_size = tile_size_bytes,
    .buffer_type = tt_metal::BufferType::DRAM};

std::shared_ptr<tt::tt_metal::Buffer> src0_dram_buffer = CreateBuffer(dram_config);
std::shared_ptr<tt::tt_metal::Buffer> dst_dram_buffer = CreateBuffer(dram_config);

// Fill a host buffer with random data and upload to the device.
std::mt19937 rng(std::random_device{}());
std::uniform_real_distribution<float> dist(0.f, 1.0f);
std::vector<bfloat16> src0_vec(n_tiles * elements_per_tile);
for (bfloat16& v : src0_vec) {
    v = bfloat16(dist(rng));
}

EnqueueWriteBuffer(cq, src0_dram_buffer, src0_vec, /*blocking=*/false);
```

Then we allocate the circular buffers. Again page size is set to tile size. There is 2 pages in each circular buffer to allow overlapping of data movement and compute operations. (data movement kernels will send/consume 1 tile at a time in this example).

``` cpp
// Allocate 2 circular buffers for input and output.
constexpr uint32_t src0_cb_index = tt::CBIndex::c_0;
constexpr uint32_t num_input_tiles = 2;
CircularBufferConfig cb_src0_config =
    CircularBufferConfig(num_input_tiles * tile_size_bytes, {{src0_cb_index, tt::DataFormat::Float16_b}})
        .set_page_size(src0_cb_index, tile_size_bytes);
CBHandle cb_src0 = tt_metal::CreateCircularBuffer(program, core, cb_src0_config);

constexpr uint32_t output_cb_index = tt::CBIndex::c_16;
constexpr uint32_t num_output_tiles = 2;
CircularBufferConfig cb_output_config =
    CircularBufferConfig(num_input_tiles * tile_size_bytes, {{output_cb_index, tt::DataFormat::Float16_b}})
        .set_page_size(output_cb_index, tile_size_bytes);
CBHandle cb_output = tt_metal::CreateCircularBuffer(program, core, cb_output_config);
```

Next, create the kernels. Nothing different from the previous examples besides being different kernels.

``` cpp
std::vector<uint32_t> reader_args;
TensorAccessorArgs(*src0_dram_buffer).append_to(reader_args);
KernelHandle unary_reader_kernel_id = CreateKernel(
    program,
    "tt_metal/programming_examples/eltwise_sfpu/kernels/dataflow/read_tile.cpp",
    core,
    DataMovementConfig{.processor = DataMovementProcessor::RISCV_1, .noc = NOC::RISCV_1_default, .compile_args = reader_args});

std::vector<uint32_t> writer_args;
TensorAccessorArgs(*dst_dram_buffer).append_to(writer_args);
KernelHandle unary_writer_kernel_id = CreateKernel(
    program,
    "tt_metal/programming_examples/eltwise_sfpu/kernels/dataflow/write_tile.cpp",
    core,
    DataMovementConfig{.processor = DataMovementProcessor::RISCV_0, .noc = NOC::RISCV_0_default, .compile_args = writer_args});
KernelHandle eltwise_sfpu_kernel_id = CreateKernel(
    program,
    "tt_metal/programming_examples/eltwise_sfpu/kernels/compute/eltwise_sfpu.cpp",
    core,
    ComputeConfig{
        .math_approx_mode = false,
    });
```

## The kernels

The reader kernel takes in the address of the source buffer and the number of tiles to read. Then read each tile from the source buffer and write it to the circular buffer. The structure should be familiar by now, as it is similar to the previous example but with one less buffer to read from.

``` cpp
// tt_metal/programming_examples/eltwise_sfpu/kernels/dataflow/read_tile.cpp
#include <cstdint>

void kernel_main() {
    uint32_t in0_addr = get_arg_val<uint32_t>(0);
    uint32_t n_tiles = get_arg_val<uint32_t>(1);

    constexpr uint32_t cb_in0 = tt::CBIndex::c_0;

    const uint32_t tile_size_bytes = get_tile_size(cb_in0);
    constexpr auto in0_args = TensorAccessorArgs<0>();
    const auto in0 = TensorAccessor(in0_args, in0_addr, tile_size_bytes);

    // Read in the data from the source buffer and write to the circular buffer
    // in a loop.
    for (uint32_t i = 0; i < n_tiles; i++) {
        cb_reserve_back(cb_in0, 1);
        uint32_t cb_in0_addr = get_write_ptr(cb_in0);
        noc_async_read_tile(i, in0, cb_in0_addr);

        noc_async_read_barrier();
        cb_push_back(cb_in0, 1);
    }
}
```

The writer kernel is the exact same as the previous example.

``` cpp
// tt_metal/programming_examples/eltwise_sfpu/kernels/dataflow/write_tile.cpp
#include <cstdint>

void kernel_main() {
    uint32_t c_addr = get_arg_val<uint32_t>(0);
    uint32_t n_tiles = get_arg_val<uint32_t>(1);

    // The circular buffer that we are going to read from and write to DRAM
    constexpr uint32_t cb_out0 = tt::CBIndex::c_16;
    const uint32_t tile_size_bytes = get_tile_size(cb_out0);

    // Address of the output buffer
    constexpr auto out0_args = TensorAccessorArgs<0>();
    const auto out0 = TensorAccessor(out0_args, c_addr, tile_size_bytes);

    // Loop over all the tiles and write them to the output buffer
    for (uint32_t i = 0; i < n_tiles; i++) {
        cb_wait_front(cb_out0, 1);
        uint32_t cb_out0_addr = get_read_ptr(cb_out0);
        // write the tile to DRAM
        noc_async_write_tile(i, out0, cb_out0_addr);
        noc_async_write_barrier();
        // Mark the tile as consumed
        cb_pop_front(cb_out0, 1);
    }
}
```

The compute kernel is the most interesting and different one. The flow is generally the same, but instead of calling functions that interact with the FPU (Matrix Engine), we use ones that invoke the SFPU. Note that some functions are postfixed with `_sfpu` to indicate that they are using the SFPU specifically, or they are implied by the fact that they do complex element-wise operations that are not supported by the FPU. The general flow of using the SFPU is as follows:

- Initialize the SFPU with the `init_sfpu` function
- Call the specific SFPU operation initialization function, such as `exp_tile_init` for exponential
- Wait for data to be available in the circular buffer using `cb_wait_front` (same as the FPU)
- Acquire tile registers using `tile_regs_acquire`
- Copy the tile from the circular buffer to the registers using `copy_tile`
- Perform the SFPU operation using `exp_tile` (or other SFPU operations)
- Wait for the result to be written back using `tile_regs_commit` and `tile_regs_wait`
- Reserve space in the circular buffer for the result using `cb_reserve_back` (same as the FPU)
- Pack the result tile from the registers to the circular buffer using `pack_tile`
- Mark the input tile as consumed using `cb_pop_front` (same as the FPU)
- Release the tile registers using `tile_regs_release`

``` cpp
// tt_metal/programming_examples/eltwise_sfpu/kernels/compute/eltwise_sfpu.cpp
#include <cstdint>
#include "compute_kernel_api/common.h"
#include "compute_kernel_api/tile_move_copy.h"
#include "compute_kernel_api/eltwise_unary/eltwise_unary.h"
#include "compute_kernel_api/eltwise_unary/exp.h"

namespace NAMESPACE {
void MAIN {
    uint32_t n_tiles = get_arg_val<uint32_t>(0);

    // Initialize the SFPU
    init_sfpu(tt::CBIndex::c_0, tt::CBIndex::c_16);
    // Setup the SFPU for exponential operation
    exp_tile_init();
    for (uint32_t i = 0; i < n_tiles; i++) {
        cb_wait_front(tt::CBIndex::c_0, 1);
        // Make sure and acquire data before running the SFPU operation
        tile_regs_acquire();
        // Copy the tile from the circular buffer offset 0 to the tile registers 0
        copy_tile(tt::CBIndex::c_0, /*offset*/ 0, /*register_offset*/ 0);

        // Invoke the SFPU exponential operation on tile 0
        exp_tile(0);
        tile_regs_commit();
        tile_regs_wait();

        // Clean up and prepare for the next iteration
        cb_reserve_back(tt::CBIndex::c_16, 1);
        pack_tile(0, tt::CBIndex::c_16);  // copy tile 0 from the registers to the CB
        cb_pop_front(tt::CBIndex::c_0, 1);
        tile_regs_release();
        cb_push_back(tt::CBIndex::c_16, 1);
    }
}
}
```

## Set up runtime arguments

For this program, the runtime arguments are similar to the previous examples. The reader gets the source address and size of the data to read. The writer gets the destination address and size of the data to write. The compute kernel simply know how much data to expect from the reader and how much data to write to the writer.

``` cpp
SetRuntimeArgs(program, eltwise_sfpu_kernel_id, core, {n_tiles});
SetRuntimeArgs(program, unary_reader_kernel_id, core, {src0_dram_buffer->address(), n_tiles});
SetRuntimeArgs(program, unary_writer_kernel_id, core, {dst_dram_buffer->address(), n_tiles});
```

## Program execution and final check

Finally we can run the program. The program is enqueued to the command queue and the results are read back from the device. Then compared against the expected results.

``` cpp
EnqueueProgram(cq, program, false);
Finish(cq);

std::vector<bfloat16> result_vec;
EnqueueReadBuffer(cq, dst_dram_buffer, result_vec, true);

for(uint32_t i = 0; i < result_vec.size(); ++i) {
    float expected = bfloat16(std::exp(src0_vec[i].to_float())).to_float();
    float result = result_vec[i].to_float();
    if (std::abs(expected - result) > eps) {
        pass = false;
        tt::log_error(tt::LogTest, "Result mismatch at index {}: {} != {}", i, expected, result);
    }
}
pass &= CloseDevice(device);
```

## Conclusion

This is the step to execute computation on the SFPU. Next we will introduce more complex data movement and running matrix multiplication using the matrix engine. See `MatMul Single Core example<MatMul_Single_Core example>`.

## Source: docs/source/tt-metalium/tt_metal/examples/index.rst

# Programming Examples

## Source: docs/source/tt-metalium/tt_metal/examples/matmul_multi_core.rst

# Matmul (Multi Core)

We'll build a program that will perform matmul operations on two tensors with equal-size inner dimension on as many cores as possible on the accelerator. This example builds on top of the previous single core matmul example.

In terms of API usage, there isn't much change. We will discuss the specific changes to:

- Distribute the work across multiple cores.
- Set up each core to process a subset of the tiles.
- What changes (and what doesn't change) in the API usage to achieve this.

It is important to note that this example builds on top of the previous single core matmul example, so it is recommended to understand the single core matmul example first. The single core matmul example is available under the `tt_metal/programming_examples/matmul_single_core/` directory.

The full source code for this example is available under the `tt_metal/programming_examples/matmul/matmul_multi_core/` directory.

Building the example can be done by adding a `--build-programming-examples` flag to the build script or adding the `-DBUILD_PROGRAMMING_EXAMPLES=ON` flag to the cmake command and results in the `matmul_multi_core` executable in the `build/programming_examples` directory. For example:

``` bash
export TT_METAL_HOME=</path/to/tt-metal>
./build_metal.sh --build-programming-examples
./build/programming_examples/matmul_multi_core
```

> [!NOTE]
> Efficiently parallelizing matrix multiplication across multiple cores—using SPMD (Single Program, Multiple Data) or other parallelization strategies - is a broad and advanced topic, often covered in depth in advanced computer science courses. While this tutorial demonstrates how to use our API to distribute work across cores, it does not attempt to teach the fundamentals of parallel programming or SPMD concepts themselves.
>
> If you are new to these topics, we recommend consulting external resources or textbooks on parallel computing for a deeper understanding. This will help you make the most of our platform and adapt these examples to your own use cases.
>
> For further reading on parallel programming and SPMD, see the References section at the end of this document.

## Device Initialization & Program Setup

Device initialization and parameter setup are the same as in the single core example. You create a device, initialize the program with the required parameters, and compute the reference result on the CPU. This section is unchanged from the single core example; see `Device Initialization & Program Setup in the single core matrix multiplication<mm_single_core_device_initialization>` in the single core matrix multiplication example for details on device setup and program initialization.

``` cpp
// Open device (use device 0)
constexpr int device_id = 0;
IDevice* device = CreateDevice(device_id);

// Matrix dimensions (must be divisible by tile dimensions)
constexpr uint32_t M = 640;  // Matrix A height
constexpr uint32_t N = 640;  // Matrix B width
constexpr uint32_t K = 640;  // Shared dimension

// Calculate number of tiles in each dimension
uint32_t Mt = M / TILE_HEIGHT;  // Each tile is 32x32
uint32_t Kt = K / TILE_WIDTH;
uint32_t Nt = N / TILE_WIDTH;

std::mt19937 rng(std::random_device{}());
std::uniform_real_distribution<float> dist(-0.5f, 0.5f);

std::vector<bfloat16> src0_vec(M * K, 0);  // Matrix A (MxK)
std::vector<bfloat16> src1_vec(K * N, 0);  // Matrix B (KxN)
// Fill with random bfloat16 values
for (bfloat16& v : src0_vec) {
    v = bfloat16(dist(rng));
}
for (bfloat16& v : src1_vec) {
    v = bfloat16(dist(rng));
}

std::vector<bfloat16> golden_vec(M * N, 0);
golden_matmul(src0_vec, src1_vec, golden_vec, M, N, K);
```

Next, convert the source matrices to tiled format before preparing for execution on the device.

``` cpp
src0_vec = tilize_nfaces(src0_vec, M, K);
src1_vec = tilize_nfaces(src1_vec, K, N);
```

## Calculating Work Distribution

Tenstorrent's AI processors support multiple parallelization strategies. The grid structure of the AI processors enables various approaches to distributing work. In this example, we use a simple SPMD (Single Program, Multiple Data) strategy similar to GPU programming. Each core runs the same program but processes a different subset of the data to compute the full result. We parallelize across the output tiles of the result matrix, with each core responsible for producing `1/num_cores` of the output tiles, where `num_cores` is the number of available cores.

> [!NOTE]
> The SPMD strategy is a standard approach in parallel computing and works well for many workloads. However, for matrix multiplication, the most efficient method on Tenstorrent's AI processors is to use a systolic array pattern, and use a subset of cores to read in and reuse the read data. This example does not cover that approach. See `MatMul_Multi_Core_example` for further optimizations, at the cost of genericity. SPMD remains a flexible and general-purpose strategy, making it suitable for a variety of tasks in Metalium.

For a matrix of size `288 x 288` (9 tiles along each dimension, with each tile being 32x32), and 11 cores available, the work is divided as evenly as possible. In the example case, 10 cores are assigned 8 output tiles each, and the 11th core processes the remaining tile. The diagram below shows how the output tiles are distributed among the cores. Each color corresponds to a different core, and each tile is handled by only one core:

Metalium includes utilities to simplify work distribution across cores. The `tt::tt_metal::split_work_to_cores(core_grid, num_work)` function calculates how many tiles each core should process, based on the total amount of work and the number of available cores. It distributes the work as evenly as possible, even if the number of tiles does not divide evenly among the cores. The function returns several values:

- `num_cores`: Number of cores used for the operation.
- `all_cores`: Set of all cores assigned to the operation.
- `core_group_1`: Primary group of cores, each handling more work.
- `core_group_2`: Secondary group of cores, each handling less work (empty if the work divides evenly).
- `work_per_core1`: Number of output tiles each core in the primary group processes.
- `work_per_core2`: Number of output tiles each core in the secondary group processes (0 if the work divides evenly).

For example, if you need to split 81 output tiles across 11 cores, `split_work_to_cores` may distribute the work as follows:

- `num_cores` = 11 (all 11 cores are used)
- `all_cores` = all 11 cores
- `core_group_1` = first 10 cores (each processes 8 tiles)
- `core_group_2` = last core (processes 1 tile)
- `work_per_core1` = 8 (tiles per core in the primary group)
- `work_per_core2` = 1 (tiles for the secondary group core)

``` cpp
auto core_grid = device->compute_with_storage_grid_size();
uint32_t num_output_tiles = (M * N) / TILE_HW; // number of output tiles

auto [num_cores, all_cores, core_group_1, core_group_2, work_per_core1, work_per_core2] =
    tt::tt_metal::split_work_to_cores(core_grid, num_output_tiles);
```

> [!NOTE]
> The following properties describe the output of `tt::tt_metal::split_work_to_cores`:
>
> - `all_cores` is the set of cores assigned work for this operation.
> - If there is not enough work, `all_cores` may be smaller than the total number of cores in `core_grid`.
> - `all_cores` contains exactly `num_cores` cores.
> - `all_cores` is always the union of `core_group_1` and `core_group_2`.
> - The total amount of work (`num_work`) is always fully assigned: `work_per_core1 * num_cores_in_core_group_1 + work_per_core2 * num_cores_in_core_group_2 == num_work`.
> - The function automatically handles uneven work distribution; you do not need to manage edge cases manually.

> [!NOTE]
> **How Metalium Parallelism Differs from OpenCL/CUDA**
>
> In frameworks like OpenCL and CUDA, you typically launch many more work groups (or thread blocks) than there are physical compute units. The hardware scheduler dynamically assigns these work groups to available compute units. If a group of threads (warp/wavefront) stalls - such as waiting for memory - the scheduler can quickly switch to another ready group, keeping the hardware busy and improving overall throughput. This dynamic scheduling and oversubscription allow for automatic load balancing and efficient handling of workloads with unpredictable execution times.
>
> In contrast, Metalium's parallelism model is static. The number of parallel tasks you can launch is limited to the number of available Tensix cores on the device. Each core is assigned a specific portion of the work at launch, and there is no dynamic scheduling or oversubscription: once a core finishes its assigned work, it remains idle until the next task is launched. This is similar to static scheduling in OpenMP, where work is divided as evenly as possible among available threads at the start.
>
> As a result, when using Metalium, it is important to:
>
> > - Carefully partition your workload so that all cores are kept busy.
> > - Be aware that you cannot launch more tasks than there are cores.
> > - Understand that dynamic load balancing (as in CUDA/OpenCL) is not available.
>
> This model offers predictable performance and is well-suited for workloads that can be evenly distributed, but it requires more attention to work distribution for optimal efficiency.

## Buffer and Circular Buffer Allocation

Creating buffers and circular buffers in Metalium is similar to the single core example. For circular buffers, instead of creating them on a single core, you create them on all cores that will be used in the operation.

``` cpp
// Allocate DRAM buffers (shared resources on the device). Nothing changes here.
constexpr uint32_t single_tile_size = sizeof(bfloat16) * TILE_HEIGHT * TILE_WIDTH;
auto src0_dram_buffer = CreateBuffer({
    .device = device,
    .size = single_tile_size * Mt * Kt,
    .page_size = single_tile_size,
    .buffer_type = tt_metal::BufferType::DRAM
});
auto src1_dram_buffer = CreateBuffer({
    .device = device,
    .size = single_tile_size * Nt * Kt,
    .page_size = single_tile_size,
    .buffer_type = tt_metal::BufferType::DRAM
});
auto dst_dram_buffer = CreateBuffer({
    .device = device,
    .size = single_tile_size,
    .page_size = single_tile_size,
    .buffer_type = tt_metal::BufferType::DRAM
});

// Create circular buffers on all participating cores
const auto cb_data_format = tt::DataFormat::Float16_b;
uint32_t num_input_tiles = 2;
auto cb_src0 = tt_metal::CreateCircularBuffer(
    program, all_cores, // create on all cores
    CircularBufferConfig(num_input_tiles * single_tile_size, {{CBIndex::c_0, cb_data_format}})
        .set_page_size(CBIndex::c_0, single_tile_size)
);

auto cb_src1 = tt_metal::CreateCircularBuffer(
    program, all_cores, // create on all cores
    CircularBufferConfig(num_input_tiles * single_tile_size, {{CBIndex::c_1, cb_data_format}})
        .set_page_size(CBIndex::c_1, single_tile_size)
);

auto cb_output = tt_metal::CreateCircularBuffer(
    program, all_cores, // create on all cores
    CircularBufferConfig(num_input_tiles * single_tile_size, {{CBIndex::c_16, cb_data_format}})
        .set_page_size(CBIndex::c_16, single_tile_size)
);
```

## Partitioning Work in Kernels

To support work distribution, the kernel is updated so that each core processes only its assigned portion of the output. Instead of having one core handle the entire matrix, we add parameters to the kernel that specify how many tiles each core should process and the starting tile index. This way, each core computes a subset of the output tiles. Below is the writer kernel, which writes the output tiles to the DRAM buffer:

``` cpp
void kernel_main() {
    uint32_t dst_addr = get_arg_val<uint32_t>(0);
    uint32_t num_tiles = get_arg_val<uint32_t>(1); // Number of tiles to write
    uint32_t start_id = get_arg_val<uint32_t>(2);  // Starting tile ID for this core

    constexpr uint32_t cb_id_out = tt::CBIndex::c_16;

    const uint32_t tile_bytes = get_tile_size(cb_id_out);

    constexpr auto c_args = TensorAccessorArgs<0>();
    const auto c = TensorAccessor(c_args, dst_addr, tile_bytes);

    // Each core writes only its assigned tiles
    for (uint32_t i = 0; i < num_tiles; ++i) {
        cb_wait_front(cb_id_out, 1);
        uint32_t l1_read_addr = get_read_ptr(cb_id_out);
        // Write to the correct offset based on start_id
        noc_async_write_tile(i + start_id, c, l1_read_addr);
        noc_async_write_barrier();
        cb_pop_front(cb_id_out, 1);
    }
}
```

The compute kernel does not handle IO directly and is not concerned with how work is distributed among the cores. It only needs to know how many tiles to compute and the size of the inner dimension. The kernel is almost identical to the single core version, except that the number of tiles to process is passed as a parameter:

``` cpp
namespace NAMESPACE {
void MAIN {
    uint32_t num_output_tiles = get_arg_val<uint32_t>(0); // Number of output tiles to produce
    uint32_t Kt = get_arg_val<uint32_t>(1); // Size of the inner dimension (K)

    constexpr tt::CBIndex cb_in0 = tt::CBIndex::c_0;
    constexpr tt::CBIndex cb_in1 = tt::CBIndex::c_1;
    constexpr tt::CBIndex cb_out = tt::CBIndex::c_16;

    mm_init(cb_in0, cb_in1, cb_out);

    // Instead of processing all tiles, we process only the assigned amount of tiles.
    for (uint32_t i = 0; i < num_output_tiles; ++i) {
        tile_regs_acquire();
        // Same inner loop as in the single core example, only the outer loop is adjusted
        // to produce the assigned number of tiles.
        for (uint32_t kt = 0; kt < Kt; kt++) {
            cb_wait_front(cb_in0, 1);
            cb_wait_front(cb_in1, 1);

            matmul_tiles(cb_in0, cb_in1, 0, 0, 0, false);

            cb_pop_front(cb_in0, 1);
            cb_pop_front(cb_in1, 1);
        }

        tile_regs_commit();
        tile_regs_wait();

        cb_reserve_back(cb_out, 1);
        pack_tile(0, cb_out);
        cb_push_back(cb_out, 1);

        tile_regs_release();
    }
}
```

The reader kernel is responsible for reading the input data from the DRAM buffers and pushing it into the circular buffers. It also needs to know how many tiles to read and the starting tile index for each core. Due to needing to calculate where to start reading from the DRAM buffer, it also needs to know the exact dimensions of the input matrices (Mt, Kt, Nt). Again the reader is almost identical to the single core version, except that it reads only the assigned number of tiles and uses the starting tile index to calculate the correct offset in the DRAM buffer:

``` cpp
void kernel_main() {
    uint32_t src0_addr = get_arg_val<uint32_t>(0);
    uint32_t src1_addr = get_arg_val<uint32_t>(1);
    uint32_t Mt = get_arg_val<uint32_t>(2);
    uint32_t Kt = get_arg_val<uint32_t>(3);
    uint32_t Nt = get_arg_val<uint32_t>(4);
    uint32_t output_tile_start_id = get_arg_val<uint32_t>(5); // Starting tile ID for this core
    uint32_t num_output_tiles = get_arg_val<uint32_t>(6); // Number of output tiles to read

    constexpr uint32_t cb_id_in0 = tt::CBIndex::c_0;
    constexpr uint32_t cb_id_in1 = tt::CBIndex::c_1;

    const uint32_t in0_tile_bytes = get_tile_size(cb_id_in0);
    const uint32_t in1_tile_bytes = get_tile_size(cb_id_in1);

    constexpr auto a_args = TensorAccessorArgs<0>();
    const auto a = TensorAccessor(a_args, src0_addr, in0_tile_bytes);

    constexpr auto b_args = TensorAccessorArgs<a_args.next_compile_time_args_offset()>();
    const auto b = TensorAccessor(b_args, src1_addr, in1_tile_bytes);

    // Loop through the output tiles assigned to this core
    for (uint32_t output_tile = 0; output_tile < num_output_tiles; output_tile++) {
        uint32_t current_tile_id = output_tile_start_id + output_tile;

        // Calculate the output tile position in the grid
        uint32_t out_row = current_tile_id / Nt;
        uint32_t out_col = current_tile_id % Nt;

        // Read all K tiles for this output position. Same inner loop as in the single core example.
        for (uint32_t k = 0; k < Kt; k++) {
            uint32_t tile_A = out_row * Kt + k;
            {
                cb_reserve_back(cb_id_in0, 1);
                uint32_t l1_write_addr_in0     = get_write_ptr(cb_id_in0);
                noc_async_read_tile(tile_A, a, l1_write_addr_in0);
                noc_async_read_barrier();
                cb_push_back(cb_id_in0, 1);
            }

            uint32_t tile_B = k * Nt + out_col;
            {
                cb_reserve_back(cb_id_in1, 1);
                uint32_t l1_write_addr_in1 = get_write_ptr(cb_id_in1);
                noc_async_read_tile(tile_B, b, l1_write_addr_in1);
                noc_async_read_barrier();
                cb_push_back(cb_id_in1, 1);
            }
        }
    }
}
```

## Kernel Creation and Parameter Setup

With the work distribution calculated, you can now create the kernels and set up their parameters. Since not all cores may be used, make sure to create kernels only on the cores listed in `all_cores`. This avoids having idle kernels on unused cores.

> [!WARNING]
> If a kernel is created on a core but runtime arguments are not set for that core, the program may crash or hang as a result of undefined behavior. Always ensure that kernels are created only on the intended cores, or that runtime arguments are set for every core where a kernel is created.

``` cpp
MathFidelity math_fidelity = MathFidelity::HiFi4;  // High fidelity math for accurate results
std::vector<uint32_t> reader_args;
TensorAccessorArgs(*src0_dram_buffer).append_to(reader_args);
TensorAccessorArgs(*src1_dram_buffer).append_to(reader_args);
auto reader_id = tt_metal::CreateKernel(
    program,
    "tt_metal/programming_examples/matmul_multi_core/kernels/dataflow/reader_mm_output_tiles_partitioned.cpp",
    all_cores,
    tt_metal::DataMovementConfig{
        .processor = DataMovementProcessor::RISCV_1, .noc = NOC::RISCV_1_default, .compile_args = reader_args});

std::vector<uint32_t> writer_args;
TensorAccessorArgs(*dst_dram_buffer).append_to(writer_args);
auto writer_id = tt_metal::CreateKernel(
    program,
    "tt_metal/programming_examples/matmul_multi_core/kernels/dataflow/writer_unary_interleaved_start_id.cpp",
    all_cores,
    tt_metal::DataMovementConfig{
        .processor = DataMovementProcessor::RISCV_0, .noc = NOC::RISCV_0_default, .compile_args = writer_args});

auto compute_kernel_id = tt_metal::CreateKernel(
    program,
    "tt_metal/programming_examples/matmul_multi_core/kernels/compute/mm.cpp",
    all_cores,
    tt_metal::ComputeConfig{.math_fidelity = math_fidelity, .compile_args = {}});
```

Unlike OpenCL or CUDA, Metalium does not provide built-in parameters for work distribution on the device. You need to manually set the runtime arguments for each core. This is done by iterating through the work groups and assigning the correct arguments for each core, including buffer addresses, tile counts, and the amount of work assigned.

``` cpp
uint32_t work_offset = 0;
auto work_groups = {
    std::make_pair(core_group_1, work_per_core1), std::make_pair(core_group_2, work_per_core2)};

// Iterate through each work group and assign work to cores
for (const auto& [ranges, work_per_core] : work_groups) {
    // Each core group may be formed of multiple ranges, so we iterate
    // through each range (splitting up 2D grid may result in fragmented ranges)
    for (const auto& range : ranges.ranges()) {
        // For each core in the range, set the runtime arguments for the
        // reader, writer, and compute kernels
        for (const auto& core : range) {
            // Set arguments for the reader kernel (data input)
            tt_metal::SetRuntimeArgs(
                program,
                reader_id,
                core,
                {src0_dram_buffer->address(),
                 src1_dram_buffer->address(),
                 Mt,
                 Kt,
                 Nt,
                 work_offset,                  // Starting offset for this core's work
                 work_per_core});              // Amount of work for this core

            // Set arguments for the writer kernel (data output)
            tt_metal::SetRuntimeArgs(
                program, writer_id, core, {dst_dram_buffer->address(),
                work_per_core,                 // Amount of work for this core
                work_offset});                 // Starting offset for this core's work

            // Set arguments for the compute kernel
            tt_metal::SetRuntimeArgs(
                program,
                compute_kernel_id,
                core,
                {work_per_core,            // Amount of work for this core
                 Kt});
            work_offset += work_per_core;  // Update offset for next core
        }
    }
}
```

## Program Execution, Receiving Results and Cleanup

This part is the same as in the single core example. You execute the program, wait for it to finish, and then download the results from the DRAM buffer. The cleanup process is also unchanged.

See `Kernel execution and result verification in the single core matrix multiplication<mm_single_core_kernel_execution>` in the single core matrix multiplication example for details on how program execution, downloading results, untilize, verification, and cleanup are performed. There is no change in the API usage for these steps compared to the single core example.

``` cpp
EnqueueWriteBuffer(cq, src0_dram_buffer, a.data(), false);
EnqueueWriteBuffer(cq, src1_dram_buffer, b.data(), false);
EnqueueProgram(cq, program, false);
EnqueueReadBuffer(cq, dst_dram_buffer, output.data(), true);

// outside of the fcunction, `output` is returned as `result_vec`
result_vec = untilize_nfaces(result_vec, M, N);

float pearson = check_bfloat16_vector_pcc(golden_vec, result_vec);
log_info(tt::LogVerif, "Metalium vs Golden -- PCC = {}", pearson);
TT_FATAL(pearson > 0.97, "PCC not high enough. Result PCC: {}, Expected PCC: 0.97", pearson);
```

## Conclusion

This concludes the multi-core matmul example and the basic usage of the Metalium API to distribute work across multiple cores. The key changes compared to the single core example are:

- Work distribution calculations using the `tt::tt_metal::split_work_to_cores` function
- Allocate circular buffers across all cores that will be used in the operation
- Set runtime arguments for each core to specify how many tiles to process and the starting tile index
- Adjust the kernels to process only the assigned number of tiles and use the starting tile index for reading/writing data
- Create kernels on the cores that will be used in the operation and handle edge cases like uneven work distribution or fewer cores than work

Explore `MatMul_Multi_Core_example` for further optimizations, including data reuse and data multicast to truly harness the power of the Tenstorrent architecture.

## References

For those interested in learning more about parallel programming concepts, we recommend the following resources:

- [Intel OpenMP Tutorial](https://www.youtube.com/playlist?list=PLLbPZJxtMs4ZHSamRRYCtvowRS0qIwC-I) — A comprehensive YouTube series covering OpenMP as well as fundamental parallel programming concepts.
- [A "Hands-On" Introduction to OpenMP](https://www.openmp.org/wp-content/uploads/omp-hands-on-SC08.pdf) — A detailed PDF guide that provides a practical introduction to OpenMP, which is a widely used API for parallel programming in C/C++ and Fortran.

## Source: docs/source/tt-metalium/tt_metal/examples/matmul_multi_core_optimizations/data_mcast.rst

# Data Multicasting in `matmul_multicore_reuse_mcast`

**Note**: This example only works on Grayskull.

Let's level up our code and show how you can leverage and fully customize METALIUM's core-to-core communication through a data broadcasting scheme. METALIUM offers you customizability for creating your very own compute fabric, allowing precise control over which cores disseminate, collect, or process segments of work. This example builds off of the data_reuse one, so we employ the same intemediate (partial) results handling scheme on-core. However, rather than map tile-work statically to your coregrid, we map in0's rows and in1's columns to the coregrid's edges, and cascade work core-to-core dynamically. A fun tidbit: "torrent" in Tenstorrent pays homage to this concept of tensor computation flowing like an ultra fast stream of water.

## Additional Compile-Time Argument

We introduced an out_block_num_tiles parameter in our reuse example, yet in our mcast example, we leverage it at compile time to navigate the complexity of multicasting partial results alongside fused operations -- namely the bias and activation functions -- which we will demonstrate further below. Let's pass it as follows:

``` cpp
vector<uint32_t> compute_kernel_args = {
...
out_block_tiles // out_block_num_tiles
};
log_info(tt::LogVerif, " -- out_block_tiles= {} --", out_block_tiles);
```

## Configuring Core Ranges for Tile Distribution

We can define our coregrid from any upper-left corner and define its range with any height and width that our problem calls for. The cores that make up the grid can be relegated specific broadcast roles (sender or receiver cores) and compute workloads (only certain tiles of in0 and in1). We start with the following initializations for the grid itself, upper-left corner, and grid edge vectors:

``` cpp
CoreCoord start_core = {0, 0};
CoreCoord core_range = bmm_op_utils::get_core_range(num_blocks_y, num_blocks_x, num_cores_y, num_cores_x);
```

``` cpp
uint32_t start_core_x = start_core.x;
uint32_t start_core_y = start_core.y;
uint32_t num_cores_c = core_range.x;  // Core count along x-axis
uint32_t num_cores_r = core_range.y;  // Core count along y-axis
```

Next, we define the mcast role of the entire coregrid, the uppermost edge, and the leftmost edge vectors of cores like so:

- **\`\`all_cores\`\`**: Outlines the boundary of all inclusive cores for the matmul kernel.

  > ``` cpp
  > CoreRange all_cores(
  >     {(std::size_t)start_core_x, (std::size_t)start_core_y},
  >     {(std::size_t)start_core_x + num_cores_c - 1, (std::size_t)start_core_y + num_cores_r - 1});
  > ```

- **\`\`left_column\`\`**: Isolates the left column of cores for specialized tasks; in this case, multicasting in0 tiles.

  > ``` cpp
  > CoreRange left_column(
  >     {(std::size_t)start_core_x, (std::size_t)start_core_y},
  >     {(std::size_t)start_core_x, (std::size_t)start_core_y + num_cores_r - 1});
  > ```

- **\`\`all_except_left_column\`\`**: Designates which cores will peform their share of in0 and in1 tile work, and calculate their partial results.

  > ``` cpp
  > CoreRange all_except_left_column(
  >     {(std::size_t)start_core_x + 1, (std::size_t)start_core_y},
  >     {(std::size_t)start_core_x + num_cores_c - 1, (std::size_t)start_core_y + num_cores_r - 1});
  > ```

Then, we define the data flow framework. The basic idea is that we initiate in0 row and in1 column data flow from the upper-left core of the coregrid (0,0) and designate this as our master sender core.

``` cpp
CoreRange in0_sender_in1_sender(
    {(std::size_t)start_core_x, (std::size_t)start_core_y}, {(std::size_t)start_core_x, (std::size_t)start_core_y});
```

Then we mcast send in0 rows of work vertically down the coregrid's left_column (from DRAM into each of these core's L1). These left_column cores are responsible for disseminating the **same** in0 row tile data to each core, thereby leveraging the data reuse scheme as we mentioned in the last section. We also ensure they are desginated as receiver cores because they will also take on in1 column work.

``` cpp
CoreRange in0_sender_in1_receiver(
    {(std::size_t)start_core_x, (std::size_t)start_core_y + 1},
    {(std::size_t)start_core_x, (std::size_t)start_core_y + num_cores_r - 1});
```

We also mcast send in1 columns of work horizontally across the coregrid (left to right) into left_column and all_except_left_column ranges of cores. You can imagine the top row of our coregrid (minus the master sender core) will be responsible for disseminating all the **different** in1 columns of work.

``` cpp
CoreRange in0_receiver_in1_sender(
    {(std::size_t)start_core_x + 1, (std::size_t)start_core_y},
    {(std::size_t)start_core_x + num_cores_c - 1, (std::size_t)start_core_y});
```

The remining tiles act as receivers for both in0 and in1 tile data. Essentially we are computing output_tile work (partial results of our output matrix) on each core, wherein each core has been simultaneously mcasted a unique chunk of in0 and in1 tile data to compute on.

``` cpp
CoreRange in0_receiver_in1_receiver(
    {(std::size_t)start_core_x + 1, (std::size_t)start_core_y + 1},
    {(std::size_t)start_core_x + num_cores_c - 1, (std::size_t)start_core_y + num_cores_r - 1});
```

This leaves each core with exactly the work it needs to compute its partial results of the output matrix. We will end up using 4 dataflow kernels:

    in0 sender
    in0 receiver
    in1 sender+writer
    in1 receiver+writer

## Circular Buffer Creation for CoreGrid

Recall in our data reuse example, we created our L1 circular buffers for all the cores like so:

``` cpp
auto cb_output = tt_metal::CreateCircularBuffer(program, all_cores, cb_output_config);
```

METALIUM also allows us to pass all of our CoreRanges defined above through a `CoreRangeSet(...)` function call as the 2nd argument. Let's do so with the following:

``` cpp
auto cb_output = tt_metal::CreateCircularBuffer(program, CoreRangeSet({all_cores}), cb_output_config);
```

In fact, you can instantiate circular buffers on any one of these three options: `const std::variant<CoreCoord, CoreRange, CoreRangeSet>`. Please refer to the CircularBuffers page for further details.

## Multicast Reader/Writer Kernel Setup

In datareuse, we spawned reader and writer kernels per core. In mcast, we have desginated core ranges (or more generally speaking, "groups"), and METALIUM gives us functionality to relegate a certain type of reader/writer kernel to a group.

Below, let's set some core ID's associated with a specific sender-receiver kernel. Take note that each ID is designated as one of two data movement processors, NCRISC (loading data from DRAM to L1) or BRISC (storing data from L1 to DRAM), as defined in the `$TT_METAL_HOME/tt_metal/impl/kernels/data_types.hpp` file.

``` cpp
// Create reader and writer kernels per core group

auto mm_reader_kernel_in0_sender_in1_sender_id = tt_metal::CreateKernel(
    program,
    "tt_metal/programming_examples/matmul_common/kernels/dataflow/reader_bmm_tile_layout_in0_sender_in1_sender.cpp",
    in0_sender_in1_sender,
    tt_metal::DataMovementConfig{.processor = tt_metal::DataMovementProcessor::RISCV_1, .noc = tt_metal::NOC::RISCV_0_default, .compile_args = reader_compile_time_args});

auto mm_reader_kernel_in0_sender_in1_receiver_id = tt_metal::CreateKernel(
    program,
    "tt_metal/programming_examples/matmul_common/kernels/dataflow/reader_bmm_tile_layout_in0_sender_in1_receiver.cpp",
    in0_sender_in1_receiver,
    tt_metal::DataMovementConfig{.processor = tt_metal::DataMovementProcessor::RISCV_1, .noc = tt_metal::NOC::RISCV_0_default, .compile_args = reader_compile_time_args});

auto mm_reader_kernel_in0_receiver_in1_sender_id = tt_metal::CreateKernel(
    program,
    "tt_metal/programming_examples/matmul_common/kernels/dataflow/reader_bmm_tile_layout_in0_receiver_in1_sender.cpp",
    in0_receiver_in1_sender,
    tt_metal::DataMovementConfig{.processor = tt_metal::DataMovementProcessor::RISCV_1, .noc = tt_metal::NOC::RISCV_1_default, .compile_args = reader_compile_time_args});

auto mm_reader_kernel_in0_receiver_in1_receiver_id = tt_metal::CreateKernel(
    program,
    "tt_metal/programming_examples/matmul_common/kernels/dataflow/reader_bmm_tile_layout_in0_receiver_in1_receiver.cpp",
    in0_receiver_in1_receiver,
    tt_metal::DataMovementConfig{.processor = tt_metal::DataMovementProcessor::RISCV_1, .noc = tt_metal::NOC::RISCV_1_default, .compile_args = reader_compile_time_args});

auto unary_writer_kernel_noc0_id = tt_metal::CreateKernel(
    program,
    "tt_metal/programming_examples/matmul_common/kernels/dataflow/writer_bmm_tile_layout.cpp",
    all_except_left_column,
    tt_metal::DataMovementConfig{.processor = tt_metal::DataMovementProcessor::RISCV_0, .noc = tt_metal::NOC::RISCV_0_default, .compile_args = writer_compile_time_args});

auto unary_writer_kernel_noc1_id = tt_metal::CreateKernel(
    program,
    "tt_metal/programming_examples/matmul_common/kernels/dataflow/writer_bmm_tile_layout.cpp",
    left_column,
    tt_metal::DataMovementConfig{.processor = tt_metal::DataMovementProcessor::RISCV_0, .noc = tt_metal::NOC::RISCV_1_default, .compile_args = writer_compile_time_args});
```

If you are interested in further details on how these work, we implore you to check out the exact dataflow kernels located in the `$TT_METAL_HOME/tt_metal/programming_examples/matmul_common/kernels/dataflow` file. You can see there are many arguments with which to experiment with, such as mcast destination nocs. You can imagine defining your own mcast scheme.

    in0_mcast_dest_noc_start_x
    in0_mcast_dest_noc_start_y
    in0_mcast_dest_noc_end_x
    in0_mcast_dest_noc_end_y

## New Compute Kernel: Fused Bias Addition and Activation Functions

Like all the examples preceeding, we call our compute kernel as usual, except here we introduce a new one called "bmm_large_block_zm_fused_bias_activation".

``` cpp
auto mm_kernel_id = tt_metal::CreateKernel(
    program,
    "tt_metal/programming_examples/matmul_common/kernels/compute/bmm_large_block_zm_fused_bias_activation.cpp",
    all_cores,
    tt_metal::ComputeConfig{.math_fidelity = math_fidelity, .compile_args = compute_kernel_args}
);
```

1.  **Flow Control through Conditionals**

    > - When bias fusion is enabled (`FUSE_BIAS`), intermediate results are directly packed and may not require reloading for subsequent operations within the same batch, indicated by `enable_reload = false`. We can employ this as a means of minimizing mem-to-mem operations.
    > - For kernels without bias fusion or when the `PACKER_L1_ACC` is not defined, we determine whether intermediate results need to be reloaded based on the computation phase (ie. our `spill` condition and the current `block`). This ensures that for operations that accumulate results over multiple blocks, intermediate data is correctly managed across iterations.

2.  **Bias Broadcasting Mechanism**

    > ``` cpp
    > add_bcast_rows_init_short();
    > for (uint32_t i = 0, j = 0; j < out_subblock_h; j++) {
    >     uint32_t bcast_tile_idx = in1_index_subblock_offset;
    >     for (uint32_t k = 0; k < out_subblock_w; k++, i++) {
    >         add_tiles_bcast_rows(mm_partials_cb_id, bias_cb_id, i, bcast_tile_idx, i);
    >         bcast_tile_idx++;
    >     }
    > }
    > ```

3.  **In-place Activation Function**

    > ``` cpp
    > #ifdef SFPU_OP_INIT_ACTIVATION
    > for (uint32_t i = 0; i < out_subblock_num_tiles; i++) {
    >     SFPU_OP_FUNC_ACTIVATION
    > }
    > #endif
    > ```

4.  **Handling Partial Results**

    > ``` cpp
    > if (enable_reload) {
    >     reload_from_cb_to_dst(in0_cb_id, in1_cb_id, mm_partials_cb_id, out_subblock_num_tiles, out_subblock_w, out_subblock_h, in0_block_w);
    > }
    > ```

## Semaphores

To cleanly coordinate the distribution and processing of in0 and in1 tiles in our mcast strategy, we should introduce semaphores. Without these, we run the risk of mcast sending data from one Tensix core to another too early (before the first Tensix core's CB stream is fully populated), or mcast receiving too few packets of data and thus computing prematurely (before the second Tensix core's CB stream is fully populated). METALIUM makes this very simple, by allowing you to call the CreateSemaphore function and simply passing the entire CoreGrid number of cores. Therefore, we define our sender and receiver core semaphores as follows, to maintain synchronization of compute across the device.

``` cpp
auto in0_mcast_sender_semaphore = tt_metal::CreateSemaphore(program, all_cores, INVALID);
auto in0_mcast_receiver_semaphore = tt_metal::CreateSemaphore(program, all_cores, INVALID);
auto in1_mcast_sender_semaphore = tt_metal::CreateSemaphore(program, all_cores, INVALID);
auto in1_mcast_receiver_semaphore = tt_metal::CreateSemaphore(program, all_cores, INVALID);
```

## Kernel Runtime Arguments

Recall that we just desginated NCRISCs to handle our DRAM-\>CoreGrid L1 data movement. METALIUM lets us pass in a buffer of tensors and dereference them with a stride by multiples of core coordintates.

``` cpp
std::vector<uint32_t> mm_reader_args = {
    (std::uint32_t)  src0_dram_buffer->address(), // in0_buffer_addr
    (std::uint32_t)  Kt * per_core_M * core_idx_y, // in0_buffer_start_tile_id
    (std::uint32_t)  1, // in0_buffer_stride_w
    (std::uint32_t)  Kt, // in0_buffer_stride_h
    (std::uint32_t)  in0_block_w, // in0_buffer_next_block_stride

    (std::uint32_t)  in0_block_w, // in0_block_w
    (std::uint32_t)  per_core_M, // in0_block_h
    (std::uint32_t)  in0_block_w * per_core_M, // in0_block_num_tiles

    (std::uint32_t)  src1_dram_buffer->address(), // in1_buffer_addr
    (std::uint32_t)  per_core_N * core_idx_x, //in1_buffer_start_tile_id
    (std::uint32_t)  1, // in1_buffer_stride_w
    (std::uint32_t)  Nt, // in1_buffer_stride_h
    (std::uint32_t)  in0_block_w * Nt, //in1_buffer_next_block_stride
    ...
```

For runtime, we need to set a few more IDs on corner cores of our CoreGrid, that will act solely as worker cores.

``` cpp
std::vector<KernelHandle> reader_kernel_ids;
std::vector<KernelHandle> writer_kernel_ids;
for(int core_idx_y = 0; core_idx_y < num_cores_r; core_idx_y++) {
    for(int core_idx_x = 0; core_idx_x < num_cores_c; core_idx_x++) {
        CoreCoord core = {(std::size_t) start_core_x + core_idx_x, (std::size_t) start_core_y + core_idx_y};

        CoreCoord left_core    = {(std::size_t) start_core_x, (std::size_t) core.y};
        CoreCoord left_core_plus_one    = {(std::size_t) start_core_x + 1, (std::size_t) core.y};
        CoreCoord right_core   = {(std::size_t) start_core_x + num_cores_c - 1, (std::size_t) core.y};
        CoreCoord top_core     = {(std::size_t) core.x, (std::size_t) start_core_y};
        CoreCoord top_core_plus_one     = {(std::size_t) core.x, (std::size_t) start_core_y + 1};
        CoreCoord bottom_core  = {(std::size_t) core.x, (std::size_t) start_core_y + num_cores_r - 1};

        auto left_core_physical = device->worker_core_from_logical_core(left_core);
        auto left_core_plus_one_physical = device->worker_core_from_logical_core(left_core_plus_one);
        auto right_core_physical = device->worker_core_from_logical_core(right_core);
        auto top_core_physical = device->worker_core_from_logical_core(top_core);
        auto top_core_plus_one_physical = device->worker_core_from_logical_core(top_core_plus_one);
        auto bottom_core_physical = device->worker_core_from_logical_core(bottom_core);
```

At this point we can specificy exactly which worker core plays which role for mcasting in0 and in1 data. Here we can map the physical core on device with:

``` cpp
(std::uint32_t)  right_core_physical.x, // in0_mcast_dest_noc_start_x
(std::uint32_t)  right_core_physical.y, // in0_mcast_dest_noc_start_y
(std::uint32_t)  left_core_plus_one_physical.x, // in0_mcast_dest_noc_end_x
(std::uint32_t)  left_core_plus_one_physical.y, // in0_mcast_dest_noc_end_y
(std::uint32_t)  (num_cores_c - 1), // in0_mcast_num_dests
(std::uint32_t)  left_core_physical.x, // in0_mcast_sender_noc_x
(std::uint32_t)  left_core_physical.y, // in0_mcast_sender_noc_y
(std::uint32_t)  in0_mcast_sender_semaphore,
(std::uint32_t)  in0_mcast_receiver_semaphore,

(std::uint32_t)  bottom_core_physical.x, // in0_mcast_dest_noc_start_x
(std::uint32_t)  bottom_core_physical.y, // in0_mcast_dest_noc_start_y
(std::uint32_t)  top_core_plus_one_physical.x, // in0_mcast_dest_noc_end_x
(std::uint32_t)  top_core_plus_one_physical.y, // in0_mcast_dest_noc_end_y
(std::uint32_t)  (num_cores_r - 1), // in0_mcast_num_dests
(std::uint32_t)  top_core_physical.x, // in0_mcast_sender_noc_x
(std::uint32_t)  top_core_physical.y, // in0_mcast_sender_noc_y
(std::uint32_t)  in1_mcast_sender_semaphore,
(std::uint32_t)  in1_mcast_receiver_semaphore,
...
```

Finally, we push our IDs into our reader and writer kernel handler vectors, and targets our NCRISC (RISCV_0) and BRISC (RISCV_1) processors. For our master send core (0,0), which initiates data movement for both matrices in0 and in1:

``` cpp
if(core_idx_x == 0 and core_idx_y == 0) {
    tt_metal::SetRuntimeArgs(program, mm_reader_kernel_in0_sender_in1_sender_id, core, mm_reader_args); // RISCV_0_default
    tt_metal::SetRuntimeArgs(program, unary_writer_kernel_noc1_id, core, writer_args); // RISCV_1_default
    reader_kernel_ids.push_back(mm_reader_kernel_in0_sender_in1_sender_id);
    writer_kernel_ids.push_back(unary_writer_kernel_noc1_id);
}
```

For the left_column cores, we task them with receiving in1 columns from the top and sending in0 rows to the right:

``` cpp
else if (core_idx_x == 0 and core_idx_y != 0) {
    tt_metal::SetRuntimeArgs(program, mm_reader_kernel_in0_sender_in1_receiver_id, core, mm_reader_args); // RISCV_0_default
    tt_metal::SetRuntimeArgs(program, unary_writer_kernel_noc1_id, core, writer_args); // RISCV_1_default
    reader_kernel_ids.push_back(mm_reader_kernel_in0_sender_in1_receiver_id);
    writer_kernel_ids.push_back(unary_writer_kernel_noc1_id);
}
```

For the upper_row cores (minus the upper-left master send core), we task them with receiving matrix in0 rows from the left, and sending in1 columns upwards.

``` cpp
else if (core_idx_x != 0 and core_idx_y == 0) {
    tt_metal::SetRuntimeArgs(program, mm_reader_kernel_in0_receiver_in1_sender_id, core, mm_reader_args); // RISCV_1_default
    tt_metal::SetRuntimeArgs(program, unary_writer_kernel_noc0_id, core, writer_args); // RISCV_0_default
    reader_kernel_ids.push_back(mm_reader_kernel_in0_receiver_in1_sender_id);
    writer_kernel_ids.push_back(unary_writer_kernel_noc0_id);
}
```

For all other cores (between the left_column and upper_row cores, minus the master send core), we task these with receiving in0 rows from the left and in1 columns from the top, thereby dividing work appropriately and commencing the partial results computation process.

``` cpp
else {
    tt_metal::SetRuntimeArgs(program, mm_reader_kernel_in0_receiver_in1_receiver_id, core, mm_reader_args); // RISCV_1_default
    tt_metal::SetRuntimeArgs(program, unary_writer_kernel_noc0_id, core, writer_args); // RISCV_0_default
    reader_kernel_ids.push_back(mm_reader_kernel_in0_receiver_in1_receiver_id);
    writer_kernel_ids.push_back(unary_writer_kernel_noc0_id);
}
```

## Source: docs/source/tt-metalium/tt_metal/examples/matmul_multi_core_optimizations/data_reuse.rst

# Data Reuse in `matmul_multicore_reuse`

## Fine-Grained Block Size Control

Advanced matrix dimension controls are found in the Programming Example's matmul_common directory, namely Block Matrix Multiply Ops (bmm_op.hpp). Including this header allows us advanced dynamic means of defining and retrieving matrix parameters. Our matmul kernels that work out-of-the-box perform on row-major and tile-major layouts, so you have the power to define your own outer-dimensional tile sizes, desired core grid dimensions, as well as your own input block width, all depending on your problem at hand.

In our reuse example, we can employ the `get_large_matmul_params(...)` function and pass our inputs as described above. By doing so, we let METALIUM's bmm op utility functions do the heavy lifting for us mathematically, and calculate our matmul's exact work-per-core size and work output size seamlessly. (You can consult the header for the prime factorization method used, plus many other details).

``` cpp
auto matmul_params = bmm_op_utils::get_large_matmul_params(Mt, Nt, num_cores_y, num_cores_x, in0_block_w);
uint32_t per_core_M = std::get<0>(matmul_params);
uint32_t per_core_N = std::get<1>(matmul_params);
uint32_t out_subblock_h = std::get<2>(matmul_params);
uint32_t out_subblock_w = std::get<3>(matmul_params);
```

Take note of the example's use of "subblocks" above. Recall that until now, we have optimized matmul by dividing matrices into blocks and subdivided those into tiles, which are laid out neatly on our compute cores. A key optimization here in `matmul_multicore_reuse` is the introduction of an intermediate subdivision of blocks, called subblocks. Below are some optimal subblock layouts already provided for you in the header, which run efficiently on our hardware.

``` cpp
constexpr std::array<std::tuple<uint32_t, uint32_t>, 20> SUBBLOCK_HW_CHOICES = {{
    {4, 2}, {2, 4}, {8, 1}, {1, 8},
    {7, 1}, {1, 7},
    {3, 2}, {2, 3}, {6, 1}, {1, 6},
    {5, 1}, {1, 5},
    {2, 2}, {4, 1}, {1, 4},
    {3, 1}, {1, 3},
    {2, 1}, {1, 2},
    {1, 1},
}};
```

## Intermediate Circular Buffer Configuration

In addition to our double-buffer config, we introduce a third circular buffer denoted as `interm0_cb_index`. Out of the 32 possible circular buffers provided by the API (which you can view in the `$TT_METAL_HOME/tt_metal/hostdevcommon/kernel_structs.h` file), this one belongs to a subset of intermediate CBs. This buffer acts as a temporary storage for the intermediate results of matrix multiplication before they are combined into the final output.

``` cpp
uint32_t output_cb_index = CBIndex::c_16;
uint32_t interm0_cb_index = CBIndex::c_24; // Index for the intermediate circular buffer
std::map<uint8_t, tt::DataFormat> output_cb_data_format_spec {
    {output_cb_index, cb_data_format}, // Output buffer configuration
    {interm0_cb_index, cb_data_format} // Intermediate buffer configuration
};
CircularBufferConfig cb_output_config = CircularBufferConfig(out_CB_size, output_cb_data_format_spec)
    .set_page_size(output_cb_index, single_tile_size)
    .set_page_size(interm0_cb_index, single_tile_size);
auto cb_output = tt_metal::CreateCircularBuffer(program, all_cores, cb_output_config);
```

## Stride Kernel Arguments

The runtime arguments for the read, write, and compute kernels are set up in a certain way to employ data reuse through the intermediate circular buffer. This setup aligns with the execution model of the `bmm_tile_layout.cpp` reader and writer kernels, and `bmm_large_block_zm.cpp` compute kernel.

``` cpp
/*
* Create Kernels (Reader, Writer, Compute)
*/
// Create reader and writer kernels per core
auto reader_id = tt_metal::CreateKernel(
    program,
    "tt_metal/programming_examples/matmul_common/kernels/dataflow/reader_bmm_tile_layout.cpp",
    all_cores,
    tt_metal::DataMovementConfig{.processor = DataMovementProcessor::RISCV_1, .noc = NOC::RISCV_1_default, .compile_args = reader_compile_time_args});

auto writer_id = tt_metal::CreateKernel(
    program,
    "tt_metal/programming_examples/matmul_common/kernels/dataflow/writer_bmm_tile_layout.cpp",
    all_cores,
    tt_metal::DataMovementConfig{.processor = DataMovementProcessor::RISCV_0, .noc = NOC::RISCV_0_default, .compile_args = writer_compile_time_args});

// Create compute kernel
auto mm_kernel_id = tt_metal::CreateKernel(
    program,
    "tt_metal/programming_examples/matmul_common/kernels/compute/bmm_large_block_zm.cpp",
    all_cores,
    tt_metal::ComputeConfig{.math_fidelity = math_fidelity, .compile_args = compute_kernel_args}
);
```

Recall our compile-time kernel compute args:

``` cpp
vector<uint32_t> compute_kernel_args = {
    in0_block_w, // in0_block_w
    in0_num_subblocks, // in0_num_subblocks
    in0_block_num_tiles, // in0_block_num_tiles
    in0_subblock_num_tiles, // in0_subblock_num_tiles

    in1_num_subblocks, // in1_num_subblocks
    in1_block_num_tiles, // in1_block_num_tiles
    in1_per_core_w, // in1_per_core_w

    num_blocks, // num_blocks

    out_subblock_h, // out_subblock_h
    out_subblock_w, // out_subblock_w
    out_subblock_num_tiles, // out_subblock_num_tiles
    B // batch
};
```

To properly run the reader and writer kernels, we must set up the runtime arguments with this information. For each block of in0 and in1 matrices, we read the tiles pertaining to a certain subblock from DRAM into that core's L1, and we perform the bmm_large_block_zm on tiles therein using stride arguments. Recall each tile is a member of a certain subblock, and subblocks are distributed across different cores in the core grid (specifically, in each core's L1). The writer kernel then stores the partial matmul results into its corresponding output subblock.

Reader:

``` cpp
std::vector<uint32_t> mm_reader_args = {
    (std::uint32_t)  src0_dram_buffer->address(), // in0_tensor_addr
    (std::uint32_t)  Kt * per_core_M * output_idx_y, // in0_tensor_start_tile_id
    (std::uint32_t)  1, // in0_tensor_stride_w
    (std::uint32_t)  Kt, // in0_tensor_stride_h
    (std::uint32_t)  in0_block_w, // in0_tensor_next_block_stride

    (std::uint32_t)  in0_block_w, // in0_block_w
    (std::uint32_t)  per_core_M, // in0_block_h
    (std::uint32_t)  in0_block_w * per_core_M, //in0_block_num_tiles

    (std::uint32_t)  src1_dram_buffer->address(), // in1_tensor_addr
    (std::uint32_t)  per_core_N * output_idx_x, //in1_tensor_start_tile_id
    (std::uint32_t)  1, // in1_tensor_stride_w
    (std::uint32_t)  Nt, // in1_tensor_stride_h
    (std::uint32_t)  in0_block_w * Nt, //in1_tensor_next_block_stride

    (std::uint32_t)  per_core_N, // in1_block_w
    (std::uint32_t)  in0_block_w, //in1_block_h
    (std::uint32_t)  per_core_N * in0_block_w, // in1_block_num_tiles

    (std::uint32_t)  Kt / in0_block_w, // num_blocks

    (std::uint32_t)  Mt * Kt, // MtKt
    (std::uint32_t)  Kt * Nt, // KtNt
    (std::uint32_t)  B, // batch
    (std::uint32_t)  bcast_batch // bcast_B
};
```

Writer:

``` cpp
std::vector<uint32_t> writer_args = {
    (std::uint32_t) dst_dram_buffer->address(), // out_buffer_addr
    (std::uint32_t) output_idx_x * per_core_N + output_idx_y * per_core_M * Nt, // out_tensor_start_tile_id
    (std::uint32_t) 1, // out_tensor_stride_w
    (std::uint32_t) Nt,  // out_tensor_stride_h
    (std::uint32_t) out_subblock_w, // out_tensor_next_subblock_stride_w
    (std::uint32_t) out_subblock_h * Nt, // out_tensor_next_subblock_stride_h

    (std::uint32_t) out_subblock_w, // out_subblock_w
    (std::uint32_t) out_subblock_h, // out_subblock_h
    (std::uint32_t) out_subblock_w * out_subblock_h, // out_subblocks_w * out_subblocks_h
    (std::uint32_t) per_core_N / out_subblock_w, // out_num_subblocks_w
    (std::uint32_t) per_core_M / out_subblock_h, // out_num_subblocks_h

    (std::uint32_t) Mt * Nt, // MtNt
    (std::uint32_t) B // batch
};
```

## Intermediate Results Handling

In `bmm_large_block_zm.cpp`,

1.  **Preparing the Intermediate Buffer**:

    > - **Reserving Partial Results Space**: For a given block (excluding the last block), we reserve space for intermediate (ie. partial) results in the rear of the intermediate circular buffer with `cb_reserve_back(...)`. Each consecutive subblock within this block will access this space, and contribute their partial results.
    >
    > ``` cpp
    > cb_reserve_back(tt::CBIndex::c_24, out_subblock_num_tiles);
    > ```
    >
    > - **Storing Partial Results**: Partial results are stored via a packing mechanism with `pack_tile(...)` into the above reserved space.
    >
    > ``` cpp
    > for (uint32_t i = 0; i < out_subblock_num_tiles; i++) {
    >     pack_tile(i, tt::CBIndex::c_24);
    > }
    > cb_push_back(tt::CBIndex::c_24, out_subblock_num_tiles);
    > ```

2.  **Computing with Partial Results**:

    > - **Result Retrieval**: During block computations after the first block, we retrieve the stored results `cb_wait_front(...)` for further computation. This retrieval, also known as "reloading" data, is the heart of our data reuse concept. It is leveraged only when our flag `enable_reload` is set to true. Recall from our understanding of circular buffers that there needs be synchronization that all tile work thus far be finished before contributing more partial results.
    >
    > ``` cpp
    > if (enable_reload) {
    >     cb_wait_front(tt::CBIndex::c_24, out_subblock_num_tiles);
    >     for (uint32_t i = 0; i < out_subblock_num_tiles; i++) {
    >         copy_tile(tt::CBIndex::c_24, i, i);
    >     }
    >     cb_pop_front(tt::CBIndex::c_24, out_subblock_num_tiles);
    > }
    > ```
    >
    > - **Execution with \`matmul_tiles\`**: Now we are ready to compute partial results and integrate them back into the computation stream (or for the last block of computation, culminate our data reuse to produce the final output tensor). We call the `matmul_tiles(...)` function to execute our matmul on the core's subblocks of tiles.
    >
    > ``` cpp
    > // Compute output sub-block from in0_subblock x in1_subblock
    > int dst_index = 0;
    > int in0_index_h_offset = 0;
    > for (uint32_t h = 0; h < out_subblock_h; h++) {
    >     for (uint32_t w = 0; w < out_subblock_w; w++) {
    >         int in1_index_inner_dim_offset = 0;
    >         for (uint32_t inner_dim = 0; inner_dim < in0_block_w; inner_dim++) {
    >             int in0_index = in0_index_subblock_offset + in0_index_h_offset + inner_dim;
    >             int in1_index = in1_index_subblock_offset + in1_index_inner_dim_offset + w;
    >             matmul_tiles(tt::CBIndex::c_0, tt::CBIndex::c_1, in0_index, in1_index, dst_index, false /* transpose */);
    >             in1_index_inner_dim_offset += in1_per_core_w;
    >         }
    >         dst_index++;
    >     }
    >     in0_index_h_offset += in0_block_w;
    > }
    > ```

3.  **Wrapping Up the Intermediate Buffer**:

    > - **Freeing Up Space**: After all partial results have been computed and stored in our output subblock, we have completed the cycle of reuse, so now we free up the space in the intermediate circular buffer with `cb_pop_front(...)`.

## Conclusion

Those are the additional steps for getting `matmul_multicore_data_reuse` operations up and running on the compute engine. To see a more complicated example using core-to-core data movement, please refer to the `Matmul multi-core data mcast example<MatMul_Multi_Core_Optimized_Data_Mcast_example>`.

## Source: docs/source/tt-metalium/tt_metal/examples/matmul_multi_core_optimized.rst

# Matmul (Multi Core Optimized)

The Tensix core architecture's secret weapon is its full user control over memory workload spread, core communication style, novel block matmul kernels, and compute patterns. In this section, we will harness real power through 3 shiny optimizations, each building off one another: data reuse, data multicast, and multidimensional systolic arrays (coming soon).

    export ARCH_NAME=<arch name>
    export TT_METAL_HOME=<this repo dir>
    ./build_metal.sh
    ./build/programming_examples/matmul_multi_core_reuse
    ./build/programming_examples/matmul_multi_core_reuse_mcast

## Source: docs/source/tt-metalium/tt_metal/examples/matmul_single_core.rst

# Matmul (Single Core)

Now that we have a basic understanding of how to use the TT Metal API and building data movement and compute kernels, we can look at a more complex example of matrix multiplication. This will be the first non-trivial example of a program that involves complex data movement and compute operations working together. The matrix multiplication will be performed on a single Tensix core using the FPU (Matrix Engine).

This example introduces the concept of using separate data movement and compute kernels that communicate through circular buffers. The compute kernel uses the powerful matrix engine to perform efficient tile-wise matrix multiplication, while data movement kernels handle reading input data from DRAM and writing results back.

We'll go through this code section by section. The full source code for this example is available under the `tt_metal/programming_examples/matmul/matmul_single_core/` directory.

Building the example can be done by adding a `--build-programming-examples` flag to the build script or adding the `-DBUILD_PROGRAMMING_EXAMPLES=ON` flag to the cmake command and results in the `matmul_single_core` executable in the `build/programming_examples` directory. For example:

``` bash
export TT_METAL_HOME=</path/to/tt-metal>
./build_metal.sh --build-programming-examples
./build/programming_examples/matmul_single_core
```

## Device Initialization & Program Setup

After standard device and command queue initialization, the matrix dimensions M, K, and N are translated into tile-based dimensions `Mt`, `Kt`, and `Nt`. This is essential as the hardware operates on 32×32 tiles. For this example, all operations are mapped to a single Tensix core at physical coordinates `{0, 0}`.

``` cpp
// Open device (we use device 0, the first available device)
constexpr int device_id = 0;
IDevice* device = CreateDevice(device_id);

// Matrix dimensions (must be divisible by tile dimensions)
constexpr uint32_t M = 640;  // Matrix A height
constexpr uint32_t N = 640;  // Matrix B width
constexpr uint32_t K = 640;  // Shared dimension

// Calculate number of tiles in each dimension
uint32_t Mt = M / TILE_HEIGHT;  // Each tile is 32x32
uint32_t Kt = K / TILE_WIDTH;
uint32_t Nt = N / TILE_WIDTH;
```

``` cpp
CommandQueue& cq = device->command_queue();
Program program{};
CoreCoord core({0, 0});  // Single core at position {0, 0}
```

## Data Preparation and Golden Reference

Before touching the matrix multiplication on the device, the host program performs several important steps:

1.  **Input Data Generation**: Two input vectors, `src0_vec` (for matrix A) and `src1_vec` (for matrix B), are populated with random `bfloat16` values

    ``` cpp
    std::mt19937 rng(std::random_device{}());
    std::uniform_real_distribution<float> dist(0.f, 1.0f);
    std::vector<bfloat16> src0_vec(M * K);
    std::vector<bfloat16> src1_vec(K * N);

    for (bfloat16& v : src0_vec) {
        v = bfloat16(dist(rng));
    }
    for (bfloat16& v : src1_vec) {
        v = bfloat16(dist(rng));
    }
    ```

2.  **Golden Reference Calculation**: A reference implementation of matrix multiplication, `golden_matmul`, is executed on the CPU. This produces a `golden_vec` which serves as the ground truth for verifying the correctness of the accelerator's output.

    ``` cpp
    std::vector<bfloat16> golden_vec(M * N, 0);
    golden_matmul(src0_vec, src1_vec, golden_vec, M, N, K);
    ```

3.  **Data Tilization**: The input vectors, which are initially in a row-major format, are converted into a tiled layout using the `tilize_nfaces` function. This is a necessary step because the Tenstorrent hardware operates on data in 32x32 tiles.

    ``` cpp
    src0_vec = tilize_nfaces(src0_vec, M, K);
    src1_vec = tilize_nfaces(src1_vec, K, N);
    ```

After the device computation, the output data needs to be converted back to a standard format for verification:

## DRAM Buffer Allocation

Three DRAM buffers are allocated: `src0_dram_buffer` for the M×K input matrix A, `src1_dram_buffer` for the K×N input matrix B, and `dst_dram_buffer` for the M×N output matrix C. The configuration for these buffers sets `page_size` to `single_tile_size` (the size of one 32x32 bfloat16 tile), a common practice for tile-based processing.

``` cpp
uint32_t single_tile_size = sizeof(bfloat16) * TILE_HEIGHT * TILE_WIDTH;

// Buffer for matrix A (M×K)
tt_metal::InterleavedBufferConfig dram_config_A{
    .device = device,
    .size = sizeof(bfloat16) * a.size(),
    .page_size = single_tile_size,
    .buffer_type = tt_metal::BufferType::DRAM};

// Buffer for matrix B (K×N)
tt_metal::InterleavedBufferConfig dram_config_B{
    .device = device,
    .size = sizeof(bfloat16) * b.size(),
    .page_size = single_tile_size,
    .buffer_type = tt_metal::BufferType::DRAM};

// Buffer for output matrix C (M×N)
tt_metal::InterleavedBufferConfig dram_config_C{
    .device = device,
    .size = sizeof(bfloat16) * output.size(),
    .page_size = single_tile_size,
    .buffer_type = tt_metal::BufferType::DRAM};

std::shared_ptr<tt::tt_metal::Buffer> src0_dram_buffer = CreateBuffer(dram_config_A);
std::shared_ptr<tt::tt_metal::Buffer> src1_dram_buffer = CreateBuffer(dram_config_B);
std::shared_ptr<tt::tt_metal::Buffer> dst_dram_buffer = CreateBuffer(dram_config_C);
```

## Circular Buffer Orchestration for Pipelined MatMul

Three circular buffers (CBs) are established to manage the data pipeline between kernels:

- `cb_src0` (CB index 0): Holds tiles of matrix A, produced by the reader kernel and consumed by the compute kernel.
- `cb_src1` (CB index 1): Holds tiles of matrix B, also produced by the reader and consumed by the compute kernel.
- `cb_output` (CB index 16): Holds resulting tiles of matrix C, produced by the compute kernel and consumed by the writer kernel.

Each CB is configured with `num_input_tiles = 2` or `num_output_tiles = 2`. This implements double buffering, allowing data movement (e.g., the reader kernel fetching the next set of A and B tiles) to overlap with computation (the compute kernel processing the current set). A higher number of tiles can be used for more complex scenarios, reducing bottlenecks in complex data movement patterns. At the cost of increased memory usage and diminishing returns, this can be used to increase performance.

``` cpp
tt::DataFormat cb_data_format = tt::DataFormat::Float16_b;
uint32_t num_input_tiles = 2;   // Double buffering for performance
uint32_t num_output_tiles = 2;

// Circular buffer for matrix A tiles
uint32_t src0_cb_index = CBIndex::c_0;
CircularBufferConfig cb_src0_config =
    CircularBufferConfig(num_input_tiles * single_tile_size, {{src0_cb_index, cb_data_format}})
        .set_page_size(src0_cb_index, single_tile_size);
auto cb_src0 = tt_metal::CreateCircularBuffer(program, core, cb_src0_config);

// Circular buffer for matrix B tiles
uint32_t src1_cb_index = CBIndex::c_1;
CircularBufferConfig cb_src1_config =
    CircularBufferConfig(num_input_tiles * single_tile_size, {{src1_cb_index, cb_data_format}})
        .set_page_size(src1_cb_index, single_tile_size);
auto cb_src1 = tt_metal::CreateCircularBuffer(program, core, cb_src1_config);

// Circular buffer for output tiles
uint32_t output_cb_index = tt::CBIndex::c_16;
CircularBufferConfig cb_output_config =
    CircularBufferConfig(num_output_tiles * single_tile_size, {{output_cb_index, cb_data_format}})
        .set_page_size(output_cb_index, single_tile_size);
auto cb_output = tt_metal::CreateCircularBuffer(program, core, cb_output_config);
```

## Matmul Kernel Pipeline Breakdown

The matrix multiplication is performed by a pipeline of three specialized kernels:

``` cpp
// Reader kernel - reads tiles from DRAM into circular buffers
std::vector<uint32_t> reader_args;
TensorAccessorArgs(*src0_dram_buffer).append_to(reader_args);
TensorAccessorArgs(*src1_dram_buffer).append_to(reader_args);
auto reader_id = tt_metal::CreateKernel(
    program,
    "tt_metal/programming_examples/matmul_single_core/kernels/dataflow/reader_single_core_mm.cpp",
    core,
    tt_metal::DataMovementConfig{.processor = DataMovementProcessor::RISCV_1, .noc = NOC::RISCV_1_default, .compile_args = reader_args});

// Writer kernel - writes result tiles from circular buffer to DRAM
std::vector<uint32_t> writer_args;
TensorAccessorArgs(*dst_dram_buffer).append_to(writer_args);
auto writer_id = tt_metal::CreateKernel(
    program,
    "tt_metal/programming_examples/matmul_single_core/kernels/dataflow/writer_single_core_mm.cpp",
    core,
    tt_metal::DataMovementConfig{.processor = DataMovementProcessor::RISCV_0, .noc = NOC::RISCV_0_default, .compile_args = writer_args});

// Compute kernel - performs matrix multiplication using the matrix engine
MathFidelity math_fidelity = MathFidelity::HiFi4;
std::vector<uint32_t> compute_compile_time_args = {Mt, Kt, Nt};
auto matmul_single_core_kernel_id = tt_metal::CreateKernel(
    program,
    "tt_metal/programming_examples/matmul_single_core/kernels/compute/mm.cpp",
    core,
    tt_metal::ComputeConfig{.math_fidelity = math_fidelity, .compile_args = compute_compile_time_args});
```

### The reader kernel

The reader kernel is responsible for fetching tiles from the DRAM buffers for matrices A and B and pushing them into `cb_src0` and `cb_src1`, respectively. The crucial aspect of this kernel is the *order* in which tiles are read. The nested loop structure (`for mt, for nt, for kt`) ensures that tiles are provided to the compute kernel in the sequence required by the matrix multiplication algorithm implemented in the compute kernel.

The tile indexing logic:

- For matrix A (M×K, or Mt×Kt tiles): `a_tile_index = mt * Kt + kt`
- For matrix B (K×N, or Kt×Nt tiles): `b_tile_index = kt * Nt + nt`

maps tiles in the row-major order of the matrices in DRAM to read into the circular buffers. This ensures that the compute kernel receives tiles in the correct order for multiplication.

``` cpp
// tt_metal/programming_examples/matmul_single_core/kernels/dataflow/reader_single_core_mm.cpp
void kernel_main() {
    // same arg indices as in reader_binary_diff_lenghts for compat
    uint32_t src0_addr = get_arg_val<uint32_t>(0);
    uint32_t src1_addr = get_arg_val<uint32_t>(1);
    uint32_t Mt = get_arg_val<uint32_t>(2);
    uint32_t Kt = get_arg_val<uint32_t>(3);
    uint32_t Nt = get_arg_val<uint32_t>(4);

    constexpr uint32_t cb_id_in0 = 0;
    constexpr uint32_t cb_id_in1 = 1;

    // Declare address in which we stored the source matrices. We have set the exact same format between CBs and DRAM
    // buffers in the host code, so we can use the same address for both DRAM and CBs.
    constexpr auto s0_args = TensorAccessorArgs<0>();
    const auto s0 = TensorAccessor(s0_args, src0_addr, get_tile_size(cb_id_in0));
    constexpr auto s1_args = TensorAccessorArgs<s0_args.next_compile_time_args_offset()>();
    const auto s1 = TensorAccessor(s1_args, src1_addr, get_tile_size(cb_id_in1));

    // Loop through the dimensions of the matrices. Read them and push to the circular buffers.
    // Dimension names are called M, N and K. `t` in `mt` means tile.
    for (uint32_t mt = 0; mt < Mt; mt++) {
        uint32_t itileB = 0;
        for (uint32_t nt = 0; nt < Nt; nt++) {
            for (uint32_t kt = 0; kt < Kt; kt++) {
                {                                          // Read A's tile at (mt, kt)
                    uint32_t a_tile_index = mt * Kt + kt;  // A is MK, so we stride by Kt
                    cb_reserve_back(cb_id_in0, 1);
                    uint32_t l1_write_addr_in0 = get_write_ptr(cb_id_in0);
                    noc_async_read_tile(a_tile_index, s0, l1_write_addr_in0);
                    noc_async_read_barrier();
                    cb_push_back(cb_id_in0, 1);
                }

                {                                          // Read B's tile at (kt, nt)
                    uint32_t b_tile_index = kt * Nt + nt;  // B is KN, so we stride by Nt
                    cb_reserve_back(cb_id_in1, 1);
                    uint32_t l1_write_addr_in1 = get_write_ptr(cb_id_in1);
                    noc_async_read_tile(b_tile_index, s1, l1_write_addr_in1);
                    noc_async_read_barrier();
                    cb_push_back(cb_id_in1, 1);
                }
            }  // Kt loop
        }  // Nt loop
    }  // Mt loop
}
```

### The compute kernel

This kernel performs the tile-by-tile matrix multiplication `C_tile += A_tile @ B_tile`. Key operations include:

- `mm_init(cb_in0, cb_in1, cb_out)`: Initializes the FPU for matrix multiplication, specifying the input CBs (`cb_in0` for A, `cb_in1` for B) and the output CB (`cb_out`).
- The outer loops iterate `Mt` times (for rows of C) and `Nt` times (for columns of C) to compute each output tile.
- `tile_regs_acquire()`: Called before the inner accumulation loop (over `Kt`). This prepares the FPU's destination/accumulator registers, typically by zeroing them, for the upcoming sum of products.
- The inner loop iterates `Kt` times, performing the dot-product-like accumulation for a single output tile.
- `matmul_tiles(cb_in0, cb_in1, 0, 0, 0, false)`: Executes the core FPU instruction: multiplies a tile from `cb_in0` with a tile from `cb_in1` and adds the result to the accumulator.
- `tile_regs_commit()` and `tile_regs_wait()`: After the inner loop, these functions ensure that the FPU has finished computation and result available in the destination registers.
- `cb_pop_front(cb_in0, 1); cb_pop_front(cb_in1, 1);`: After the tiles are used by `matmul_tiles`, they are marked as consumed by popping them from the input CBs.
- `pack_tile(0, cb_out); cb_push_back(cb_out, 1);`: Once the `Kt` loop completes for an output tile, the accumulated result in the FPU registers is packed and pushed to the output circular buffer `cb_out`.

The dimensions `Mt`, `Kt`, `Nt` are passed as compile-time arguments, enabling the compiler to optimize the kernel structure for these specific dimensions.

``` cpp
// tt_metal/programming_examples/matmul_single_core/kernels/compute/mm.cpp
namespace NAMESPACE {
void MAIN {
    const uint32_t Mt = get_compile_time_arg_val(0);
    const uint32_t Kt = get_compile_time_arg_val(1);
    const uint32_t Nt = get_compile_time_arg_val(2);
    constexpr tt::CBIndex cb_in0 = tt::CBIndex::c_0;
    constexpr tt::CBIndex cb_in1 = tt::CBIndex::c_1;
    constexpr tt::CBIndex cb_out = tt::CBIndex::c_16;

    // Setup the FPU (matrix engine) for the matmul operation
    mm_init(cb_in0, cb_in1, cb_out);
    for (uint32_t mt = 0; mt < Mt; ++mt) {
        for (uint32_t nt = 0; nt < Nt; ++nt) {
            // Make sure registers can be used for the output tile. This also sets the registers to zero.
            tile_regs_acquire();
            for (uint32_t kt = 0; kt < Kt; kt++) {
                // Wait for the input tiles to be available in the input circular buffers.
                cb_wait_front(cb_in0, 1);
                cb_wait_front(cb_in1, 1);

                // Perform the matrix multiplication for the current tile.
                // NOTE: This function also accumulates the result into the destination tile.
                matmul_tiles(cb_in0, cb_in1, 0, 0, 0, false);
                cb_pop_front(cb_in0,1);
                cb_pop_front(cb_in1,1);
            }

            tile_regs_commit();
            tile_regs_wait();

            // store the result tile in the output circular buffer.
            cb_reserve_back(cb_out, 1);
            pack_tile(0, cb_out);
            cb_push_back(cb_out, 1);

            tile_regs_release();
        }
    }
}
}
```

### The writer kernel

The writer kernel consumes tiles from the output circular buffer `cb_id_out0` (which is `cb_output`, index 16) and writes them to the designated DRAM buffer for matrix C. The nested loops iterate `Mt` and `Nt` times, and the tile index `m * Nt + n` ensures that the output tiles are written in row-major order, correctly forming the M×N output matrix in DRAM.

``` cpp
// tt_metal/programming_examples/matmul_single_core/kernels/dataflow/writer_single_core_mm.cpp

void kernel_main() {
    // Runtime arguments to write data back into the output buffer.
    uint32_t dst_addr = get_arg_val<uint32_t>(0);
    uint32_t Mt = get_arg_val<uint32_t>(1);
    uint32_t Nt = get_arg_val<uint32_t>(2);

    constexpr uint32_t cb_id_out0 = 16;

    constexpr auto s_args = TensorAccessorArgs<0>();
    const auto s = TensorAccessor(s_args, dst_addr, get_tile_size(cb_id_out0));

    for (uint32_t mt = 0; mt < Mt; ++mt) {
        for (uint32_t nt = 0; nt < Nt; ++nt) {
            // Wait for the matrix multiplication kernel to produce an output
            cb_wait_front(cb_id_out0, 1);
            // Write the output tile to DRAM.
            uint32_t l1_read_addr = get_read_ptr(cb_id_out0);
            noc_async_write_tile(mt * Nt + nt, s, l1_read_addr);
            noc_async_write_barrier();
            cb_pop_front(cb_id_out0, 1);
        }
    }
}
```

## Kernel execution and result verification

On the host side, runtime arguments are configured for each kernel. These typically include DRAM buffer addresses (for A, B, and C) and tile counts (`Mt`, `Kt`, `Nt`) that define the scope of the operation for the current invocation. The overall execution flow is managed by enqueuing commands:

1.  `EnqueueWriteBuffer`: Transfers input matrices A and B from host memory to their respective DRAM buffers on the device.
2.  `EnqueueProgram`: Launches the compiled program (reader, compute, and writer kernels) on the designated core.
3.  `EnqueueReadBuffer`: Transfers the resulting matrix C from its DRAM buffer on the device back to host memory.

``` cpp
// Set runtime arguments for kernels
uint32_t src0_addr = src0_dram_buffer->address();
uint32_t src1_addr = src1_dram_buffer->address();
uint32_t dst_addr = dst_dram_buffer->address();

tt_metal::SetRuntimeArgs(program, reader_id, core, {src0_addr, src1_addr, Mt, Kt, Nt});
tt_metal::SetRuntimeArgs(program, writer_id, core, {dst_addr, Mt, Nt}); // Note: Writer kernel uses Mt, Nt for output C
// Don't need to set runtime args for compute kernel, as everything is passed as compile-time args

// Upload input data, execute program, and read results
EnqueueWriteBuffer(cq, src0_dram_buffer, a.data(), false);
EnqueueWriteBuffer(cq, src1_dram_buffer, b.data(), false);
EnqueueProgram(cq, program, false);
EnqueueReadBuffer(cq, dst_dram_buffer, output.data(), true);
```

After the program execution, the `output.data()` (which is `result_vec` in the `main` function of the C++ example) contains the result matrix C from the device's DRAM. However, this data is still in the tiled format used by the Tenstorrent hardware. To verify its correctness against the `golden_vec` (which is in a standard row-major format), two steps are necessary:

1.  **Data Untilization**: The `untilize_nfaces` function is used to convert the tiled output data back into a row-major format. This is the inverse operation of `tilize_nfaces` performed on the input data.

    ``` cpp
    // Reverse the tilization to get the result in the row-major format
    result_vec = untilize_nfaces(result_vec, M, N);
    ```

2.  **Verification against Golden Reference**: The untilized `result_vec` is then compared against the `golden_vec` computed by the CPU. A common method for comparing floating-point vectors is to calculate the Pearson correlation coefficient (PCC). A PCC value close to 1.0 indicates a high degree of similarity between the two vectors, confirming the correctness of the accelerator's computation.

    ``` cpp
    float pearson = check_bfloat16_vector_pcc(golden_vec, result_vec);
    log_info(tt::LogVerif, "Metalium vs Golden -- PCC = {}", pearson);
    TT_FATAL(pearson > 0.97, "PCC not high enough. Result PCC: {}, Expected PCC: 0.97", pearson);
    ```

## Conclusion

This single-core matrix multiplication example highlights several key architectural patterns for programming Tenstorrent devices:

- **Separation of data movement and compute**: By using dedicated RISC-V processors for data movement (reader/writer kernels) and the matrix engine for computation, complex data orchestration patterns do not sacrifice compute throughput. The data movement processors can handle complex access patterns while the compute units remain fully utilized.
- **Tiled operations**: The hardware is optimized for tiled operations, making tile-based algorithms essential for achieving peak performance. All matrices are processed in tile units, matching the natural granularity of the underlying hardware accelerators.
- **Pipelined data movement**: The circular buffer architecture with double buffering enables overlapped execution - while the compute kernel processes current tiles, the data movement kernels can simultaneously fetch the next set of tiles. This pipelining ensures efficient utilization of compute resources by minimizing idle time.

Next we will explore the `MatMul_Multi_Core example <MatMul_Multi_Core example>`, which extends these concepts to a multi-core setup, demonstrating how to scale matrix multiplication across multiple Tensix cores for even greater performance.

## Source: docs/source/tt-metalium/tt_metal/apis/kernel_apis/circular_buffers/circular_buffers.rst

# Circular Buffer APIs

Circular buffers are used for communication between threads of the Tensix core. They act as limited capacity double-ended queues with producers pushing tiles to the back of the queue and consumers popping tiles off the front of the queue.

## Source: docs/source/tt-metalium/tt_metal/apis/kernel_apis/compute/compute.rst

# Compute APIs

This page lists the APIs available in the compute kernels. These APIs cover:

- Synchronization between the three cores running the compute kernel cooperatively
- Copying data between SRAM and the registers used by the compute engines
- Performing computations

For details on function parameters and their meanings, see the `Compute Engines and Data Flow within Tensix<compute_engines_and_dataflow_within_tensix>` documentation.

## Synchronization

## Compute

### Initialization

### Compute (FPU/matrix engine)

### Compute (SFPU/vector engine)

#### Basic arithmetic operations

#### Integer operations

#### Exponential and logarithmic functions

#### Comparison and logical operations

#### Bitwise operations

#### Rounding and ceiling functions

#### Hyperbolic functions

#### Special mathematical functions

#### Initialization and utilities

#### Trigonometric functions

#### Activation functions

#### Data manipulation and processing

#### Quantization operations

## Source: docs/source/tt-metalium/tt_metal/apis/kernel_apis/compute/init_functions.rst

# any_init

Most compute API calls have an `*_init` paired API call (for example `exp_tile_init` and `exp_tile`). Invoking this `*_init` API configures the compute unit for execution of the subsequent paired call.

## Source: docs/source/tt-metalium/tt_metal/apis/kernel_apis/data_movement/data_movement.rst

# Data Movement APIs

## Source: docs/source/tt-metalium/tt_metal/apis/kernel_apis/data_movement/ordering.rst

# Ordering (NOC, CMD_BUF, VC)

NoC requests/responses are usually asynchronous, but they can have an implicit ordering, or you could enforce an explicit ordering. In this section, we will go over command buffers (`CMD_BUF`), virtual channels (`VC`), and allocation of virtual channels.

There are two NoCs (NoC-0 and NoC-1) that are completely phyiscally replicated and separated. The only communication between these NoCs is through software or L1 memory. For each NoC, we have 4 command buffers: `RD_CMD_BUF`, `WR_CMD_BUF`, `WR_REG_CMD_BUF`, `AT_CMD_BUF`. We usually use the `WR_CMD_BUF` for all writes, except for the atomic ones where we use `AT_CMD_BUF`, e.g. `noc_semaphore_inc` uses `AT_CMD_BUF`.

For each NoC, we have 6 `VC` (numbered 0-5). Each `VC` is usually used for a different purpose. For example, all unicast writes go on `NOC_UNICAST_WRITE_VC`, which is `VC` 1, and all multicast writes go on `NOC_MULTICAST_WRITE_VC`, which is `VC` 4.

We can allocate `VC` either statically or dynamically. We can allocate `VC` statically using `NOC_CMD_STATIC_VC`, which is usually the case for noc writes. For noc reads, the read requests can use a statically allocated `VC`, as for read responses, we always use dynamically allocated `VC`. So there's really no way to control ordering for data reads.

As for ordering of the NoC writes:

- If writes are on different NoCs, there is no ordering guarantees.
- If writes are on the same NoC but different VCs, there's also no ordering guarantees. You might as well use different CMD_BUFs to avoid serialization.
- If writes are on the same NoC and same VC, they will be ordered based on program order, regardless whether you use the same CMD_BUF or different ones.

## Source: docs/source/tt-metalium/tt_metal/apis/kernel_apis/kernel_args/kernel_args.rst

# Kernel Argument APIs

## Source: docs/source/tt-metalium/tt_metal/apis/kernel_apis/pack_unpack/packing_apis.rst

# Packing APIs

Packing and Unpacking APIs allow reinterpreting or construct/reading of buffers as specific integer or floating point data types.

## Source: docs/source/tt-metalium/tt_metal/apis/kernel_apis/sfpu/llk.rst

# Low Level Kernels

## Overview

SFPI is the programming interface to the SFPU. It consists of a C++ wrapper around a RISCV GCC compiler base which has been extended with vector data types and \_\_builtin intrinsics to generate SFPU instructions. The wrapper provides a C++ like interface for programming.

SFPI is supported on Grayskull and Wormhole.

## Compiler Options/Flags

The following flags must be specified to compile SFPI kernels:

``` c++
-m<arch> -fno-exceptions
```

where `arch` is one of:

> - grayskull
> - wormhole

Note that the arch specification above overrides any `-march=<xyz>` to either `-march=rv32iy` for grayskull or `-march=rv32iw` for wormhole.

Further, the following options disable parts of the SFPI enabled compiler:

> - `-fno-rvtt-sfpu-warn`: disable sfpu specific warnings/errors
> - `-fno-rvtt-sfpu-combine`: disable sfpu instruction combining
> - `-fno-rvtt-sfpu-cc`: disable sfpu CC optimizations
> - `-fno-rvtt-sfpu-replay`: disable sfpu REPLAY optimizations (wormhole only)

### Example

Before going into details, below is a simple example of SFPI code:

``` c++
void silly(bool take_abs)
{
    // dst_reg[n] loads into a temporary LREG
    vFloat a = dst_reg[0] + 2.0F;

    // This emits a load, move, mad (on GS uses the "+/0 .5" feature of MAD)
    dst_reg[3] = a * -dst_reg[1] + vConst0p6929 + 0.5F;

    // This emits a load, loadi, mad (a * dst_reg[] goes down the mad path)
    dst_reg[4] = a * dst_reg[1] + 1.2F;

    // This emits two loadis and a mad
    dst_reg[4] = a * 1.5F + 1.2F;

    // This emits a loadi (into tmp), loadi (as a temp for 1.2F) and a mad
    vFloat tmp = s2vFloat16a(value);
    dst_reg[5] = a * tmp + 1.2F;

    v_if ((a >= 4.0F && a < 8.0F) || (a >= 12.0F && a < 16.0F)) {
        vInt b = exexp_nodebias(a);
        b &= 0xAA;
        v_if (b >= 130) {
            dst_reg[6] = setexp(a, 127);
        }
        v_endif;
    } v_elseif (a == s2vFloat16a(3.0F)) {
        // RISCV branch
        if (take_abs) {
            dst_reg[7] = abs(a);
        } else {
            dst_reg[7] = a;
        }
    } v_else {
        vInt exp = lz(a) - 19;
        exp = ~exp;
        dst_reg[8] = -setexp(a, exp);
    }
    v_endif;
}
```

The main things to note from the example are:

> - Constants are expressed as scalars but are expanded to the width of the vector
> - `v_if` (and related) predicate execution of vector operations such that only enabled vector elements are written
> - The compiler views `v_if` and `v_elseif` as straight-line code, ie, both sides of the conditionals are executed
> - RISCV conditional and looping instructions work as expected (only one side executed)
> - Math expressions for vectors work across all enabled vector elements
> - Presently, `v_endif` is required to close out all `v_if`/`v_elseif`/`v_else` chains

## Details

### Namespace

All the data types/objects/etc. listed below fall within the `sfpi` namespace.

### User Visible Data Types

The following data types are visible to the programmer:

> - `vFloat`
> - `vInt`
> - `vUInt`
> - enum `LRegs`

Each of the `v` types is a strongly typed wrapper around the weakly typed compiler data type `__rvtt_vec_t`. On Grayskull this is a vector of 64 19 bit values while on Wormhole this is a vector of 32 32 bit values.

LRegs are the SFPU's general purpose vector registers. `LRegs` enumerates these registers.

#### User Visible Constants

Constant registers are implemented as objects which can be referenced wherever a vector can be used.

> - Grayskull:
>   - `vConst0`
>   - `vConst0p6929`
>   - `vConstNeg1p0068`
>   - `vConst1p4424`
>   - `vConst0p8369`
>   - `vConstNeg0p5`
>   - `vConst1`
>   - `vConstNeg1`
>   - `vConst0p0020`
>   - `vConstNeg0p6748`
>   - `vConstNeg0p3447`
>   - `vConstTileId`, enumerates the vector elements: \[0..63\]

- Wormhole:
  - `vConst0`
  - `vConst1`
  - `vConst0p8373`
  - `vConstNeg1`
  - `vConstTileId`, counts by two through the vector elements: \[0, 2, 4..62\]
  - `vConstFloatPrgm0`, `vConstIntPrgm0`
  - `vConstFloatPrgm1`, `vConstIntPrgm1`
  - `vConstFloatPrgm2`, `vConstIntPrgm2`

#### User Visible Objects

> - `dst_reg[]` is an array used to access the destination register
> - `l_reg[]` is an array used to load/store to specific SFPU registers

#### Macros

The only macros used within the wrapper implement the predicated conditional processing mechanism. These (of course) do not fall within the SFPI namespace and for brevity run some chance of a namespace collision. They are:

> - `v_if()`
> - `v_elseif()`
> - `v_else`
> - `v_endif`
> - `v_block`
> - `v_endblock`
> - `v_and()`

The conditionals work mostly as expected but note the required `v_endif` at the end of an if/else chain. Forgetting this results in compilation errors as the `v_if` macro contains a `{` which is matched by the `v_endif`.

`v_block` and `v_and` allow for the following code to progressively "narrow" the CC state:

``` c++
v_block {
    for (int x = 0; x < n; x++) {
        v1 = v1 - 1;
        v_and (v1 >= 0);
        v2 *= 2;
    }
}
v_endblock;
```

`v_and` can be used inside any predicated conditional block (i.e., a `v_block` or a `v_if`).

### Data Type Details

#### vFloat

> - Assignment: from float, dst_reg\[n\]
> - Conversion: `reinterpret<AnotherVecType>()` converts, in place, between vInt and vUInt and vFloat
> - Immediate loads: see section **Immediate Floating Point Values** below
> - Operators: `+`/`-`/`*` should work as expected with dst_reg\[n\], vFloat and vConst
> - Conditionals: all 6 (`<`, `<=`, `==`, `!=`, `>=`, `>`) are supported. Note that `<=` and `>` pay a performance penalty relative to the others

#### vInt

> - Assignment: from integer, dst_reg\[n\]
> - Conversion: `reinterpret<AnotherVecType>()` converts, in place, between vFloat and vUInt
> - Operators: `&`, `&=`, `|`, `|=`, `~`, `^`, `^=`, `<<` and `+`, `-`, `+=`, `-=`, `++`, `--`. (there is no signed right shift on Grayskull or Wormhole)
> - Conditionals: all 6 (`<`, `<=`, `==`, `!=`, `>=`, `>`) are supported. Note that `<=` and `>` pay a performance penalty relative to the others

#### vUInt

> - Assignment: from unsigned integer, dst_reg\[n\]
> - Conversion: `reinterpret<AnotherVecType>()` converts, in place, between vFloat and vInt
> - Operators: `&`, `&=`, `|`, `|=`, `~`, `^`, `^=`, `<<`, `>>` and `+`, `-`, `+=`, `-=`, `++`, `--`
> - Conditionals: all 6 (`<`, `<=`, `==`, `!=`, `>=`, `>`) are supported. Note that `<=` and `>` pay a performance penalty relative to the others

Note that on Wormhole, the destination register format is always determined by the run time. So, for example, reading a vInt when the format is set to float32 gives unexpected results.

### Library

Below `Vec` means any vector type.

Below is a list of library calls, further documentation is below.

#### Grayskull and Wormhole

``` c++
vInt exexp(const vFloat v)
vInt exexp_nodebias(const vFloat v)
```

Extracts, optionally debiases and then returns the 8-bit exponent in ''v'' in bits 7:0.

``` c++
vInt exman8(const vFloat v)
vInt exman9(const vFloat v)
```

Extracts and returns the mantissa of v. ''exman8'' adds the hidden bit and pads the left side with 8 zeros while ''exman9' does not include the hidden bit and pads the left side with 9 zeros.

``` c++
vFloat setexp(const vFloat v, const uint32_t exp)
vFloat setexp(const vFloat v, const Vec[U]Short exp)
```

Replaces the exponent of ''v'' with the exponent in bits 7:0 of ''exp'' and returns the result (preserving the sign and mantissa of ''v'').

``` c++
vFloat setman(const vFloat v, const uint32_t man)
vFloat setman(const vFloat v, const Vec[U]Short man) // This does not work on GS due to a HW bug
```

Replaces the mantissa of ''v'' with the mantissa in the low bits of ''man'' and returns the result (preserving the sign and exponent of ''v'').

``` c++
vFloat setsgn(const vFloat v, const int32_t sgn)
vFloat setsgn(const vFloat v, const vFloat sgn)
vFloat setsgn(const vFloat v, const vInt sgn)
```

Replaces the sign bit of ''v'' with the sign in ''sgn'' and returns the result (preserving the exponent and mantissa of ''v''). Note that the ''int32_t'' version takes the sign from bit 0 while the ''vFloat'' and ''vInt'' versions take the sign from the sign bit location (bit 19 on GS and bit 32 on WH).

``` c++
vFloat addexp(const vFloat v, const int32_t exp)
```

Adds the 8-bit value in ''exp'' to the exponent of ''v'' and returns the result (preserving the sign and mantissa of ''v'').

``` c++
vFloat lut(const vFloat v, const vUInt l0, const vUInt l1, const vUInt l2, const int offset)
vFloat lut_sign(const vFloat v, const vUInt l0, const vUInt l1, const vUInt l2, const int offset)
```

''l0'', ''l1'', ''l2'' each contain 2 8-bit floating point values ''A'' and ''B'' with ''A'' in bits 15:8 and ''B'' in bits 7:0. The 8-bit format is:
- 0xFF represents the value 0, otherwise
- bit\[7\] is the sign bit, bit\[6:4\] is the unsigned exponent_extender and bit\[3:0\] is the mantissa

Floating point representations of ''A'' and ''B'' (19-bit on GS and 32-bit on WH) are constructed by:
- Using the sign bit
- Generating an 8-bit exponent as (127 – exponent_extender)
- Generating a mantissa by padding the right of the specified 4 bit mantissa with 0s

''A'' and ''B'' are selected from one of ''l0'', ''l1'' or ''l2'' based on the value in ''v'' as follows:
- ''l0'' when ''v'' \< 0
- ''l1'' when ''v'' == 0
- ''l2'' when ''v'' \> 0

XXXX is this backwards? Returns the result of the computation ''A \* ABS(v) + B''. The ''lut_sgn'' variation discards the calculated sign bit and instead uses the sign of ''v''.

``` c++
vInt lz(Vec v)
```

Returns the count of leading (left-most) zeros of ''v''.

``` c++
vFloat abs(vFloat v)
vInt abs(vInt v)
```

Returns the absolute value of ''v''.

``` c++
vUInt shft(const vUInt v, const vInt amt)
```

Performs a left shift (when ''amt'' is positive) or right shift (when ''amt'' is negative) of ''v'' by ''amt'' bits.

#### Wormhole only

``` c++
void vec_swap(Vec& A, Vec& B)
```

Swaps the (integer or floating point) vectors in ''A'' and ''B''.

``` c++
void vec_min_max(Vec& min, Vec& max)
```

Compares and swaps each element of the two vectors such that on return ''min'' contains all of the minimum values and ''max'' contains all of the maximum values.

``` c++
Vec subvec_shflror1(Vec& v)
Vec subvec_shflshr1(Vec& v)
```

``` c++
void subvec_transp(Vec& A, Vec& B, Vec& C, Vec& D)
```

``` c++
vInt lz_nosgn(const Vec v)
```

Returns the count of leading (left-most) zeros of ''v'' ignoring the sign bit.

``` c++
vFloat int_to_float(vInt in, int round_mode = 1)
vUInt float_to_fp16a(vFloat in, int round_mode = 1)
vUInt float_to_fp16b(vFloat in, int round_mode = 1)
vUInt float_to_uint8(vFloat in, int round_mode = 1)
vUInt float_to_int8(vFloat in, int round_mode = 1)
vUInt int32_to_uint8(vInt in, vUInt descale, int round_mode = 1)
vUInt int32_to_uint8(vInt in, unsigned int descale, int round_mode = 1)
vUInt int32_to_int8(vInt in, vUInt descale, int round_mode = 1)
vUInt int32_to_int8(vInt in, unsigned int descale, int round_mode = 1)
vUInt float_to_uint16(vFloat in, int round_mode = 1)
vUInt float_to_int16(vFloat in, int round_mode = 1)
```

Returns the rounded value performing round-to-even when ''round_mode'' is 0 and stochastic rounding when ''round_mode'' is 1.

### Immediate Floating Point Values

Assigning a float to a vFloat behaves slightly different on Grayskull vs Wormhole. On Grayskull, the value is interpreted as an fp16b; use the conversion routines below to explicitly specify the format. On Wormhole, the floating point value is converted to an fp16a, fp16b, or fp32 by first looking to see if the range fits in fp16b and if not using fp16a (or fp32). If the value is not known at compile time, then it is loaded as an fp32. Note that on Wormhole fp32 loads take 2 cycles.

For more explicit conversions, use one of the classes `s2vFloat16a` and `s2vFloat16b`. Each takes either an integer or floating point value. Floating point immediate values are converted at compilation time and incur no overhead. Floating point variables that are not known at compilation time are converted at run time. An integer value loaded into floating point vector (via one of the conversion routines) is treated as a bit pattern and incurs no overhead, see examples below.

Note: fp16a conversions do not presently handle denorms/nans, etc. properly.

Example uses:

``` c++
vFloat x = 1.0f;               // Load fb16b value
vFloat x = 500000.0f;          // GS load fp16b value, WH fp32 value
vFloat x = s2vFloat16a(3.0F);  // Load fp16a value, no overhead
unsigned int ui = 0x3c00;
vFloat x = s2vFloat16a(ui);    // Load fp16a value (1.0F), no overhead
float f = 1.0F;
vFloat x = s2vFloat16a(f);     // Load fp16a value, overhead if value cannot be determined at compile time
```

#### Boolean Operators

All conditionals operating on base types can be combined with any of `&&`, `||`, `!`.

#### vBool

`vBool` doesn't exist yet, but the functionality can be obtained by executing conditional instructions outside of a `v_if` and assigning the result to a `vInt`. This can be useful to, e.g., use RISCV code to conditionally generate an SFPU predicate. For example, the following function evaluates different predicated conditionals based on the value of a function parameter:

``` c++
sfpi_inline vInt sfpu_is_fp16_zero(const vFloat& v, uint exponent_size_8)
{
    if (exponent_size_8) {
        return v == 0.0F;
    } else {
        vInt tmp = 0x3800; // loads {0, 8'd112, 10'b0}
        tmp += reinterpret<vInt>(v);
        return tmp == 0;
    }
}
```

which may be called by:

``` c++
v_if (sfpu_is_fp16_zero(v, exponent_size_8)) {
    ...
}
v_endif;
```

If exponent_size_8 is known at compile time, this has no overhead. If not, the predication is determined at runtime.

#### Assigning and Using Constant Registers

Programmable constant registers (Wormhole only) are accessed and assigned just like any other variables, for example:

``` c++
vConstFloatPrgm0 = 3.14159265;
vFloat two_pi = 2.0f * vConstFloatPrgm0;
```

Writing to a constant register first loads the constant into a temporary LReg then assigns the LReg to the constant register and so takes 1 cycle longer than just loading an LReg. Accessing a constant register is just as fast as accessing an LReg. Loading a constant register loads the same value into all vector elements.

#### Assigning LRegs

Some highly optimized code may call a function prior to the kernel to pre-load values into specific LRegs and then access those values in the kernel. Note that if the register's value must be preserved when the kernel exits, you must restore the value explicitly by assigning back into the LReg.

For example:

``` c++
vFloat x = l_reg[LRegs::LReg1];  // x is now LReg1
vFloat y = x + 2.0f;
l_reg[LRegs::LReg1] = x;         // this is necessary at the end of the function
                                 // to preserve the value in LReg1 (if desired)
```

## Miscellaneous

### Register Pressure Management

Note that the wrapper introduces temporaries in a number of places. For example:

``` c++
dst_reg[0] = dst_reg[0] + dst_reg[1];
```

loads dst_reg\[0\] and dst_reg\[1\] into temporary LREGs (as expected).

The compiler will not spill registers. Exceeding the number of registers available will result in the cryptic: `error: cannot store SFPU register (reigster spill?) - exiting!` without a line number.

The compiler does a reasonable job with lifetime analysis when assigning variables to registers. Reloading or recalculating results helps the compiler free up and re-use registers and is a good way to correct a spilling error.

Grayskull has 4 general purpose LRegs, Wormhole has 8.

### Optimizer

There is a basic optimizer in place. The optimization philosophy to date is to enable the programmer to write optimal code. This is different from mainstream compilers which may generate optimal code given non-optimal source. For example, common sub-expression elimination and the like are not implemented. The optimizer will handle the following items:

> - MAD generation (from MUL/ADD)
> - MULI, ADDI generation (from MUL + const, or ADD + const)
> - Adding a 0.5f to the end of ADD/MULL/MAD/MULI/ADDI (Grayskull only)
> - Swapping the order of arguments to instructions that use the destination-as-source, e.g., SFPOR to minimize the need for register moves
> - CC enables (PUSHC, POPC, etc.)
> - Instruction combining for comparison operations. For example, a subtract of 5 followed by a compare against 0 gets combined into one operation
> - Wormhole only: NOP insertion for instructions which must be followed by an independent instruction or NOP. Note that this pass (presently) does not move instructions to fill the slot but will skip adding a NOP if the next instruction is independent. In other words, reordering your code to reduce dependent chains of instructions may improve performance

There is a potential pitfall in the above in that the MAD generator could change code which would not run out of registers with, say, a MULI followed by an ADDI into code that runs out of registers with a MAD. (future todo to fix this).

### SFPREPLAY

The `SFPREPLAY` instruction available on Wormhole allows the RISCV processor to submit up to 32 SFP instructions at once. The compiler looks for sequences of instructions that repeat, stores these and then "replays" them later.

The current implementation of this is very much first cut: it does not handle kernels with rolled up loops very well. Best performance is typically attained by unrolling the top level loop and then letting the compiler find the repetitions and replace them with `SFPREPLAY`. This works well when the main loop contains \< 32 instructions, but performance starts to degrade again as the number of instructions grows (future work).

The other issue that can arise with `SFPREPLAY` is that sometimes the last unrolled loop of instructions uses different registers than the prior loops resulting in imperfect utilization of the replay.

### Emulation

There is an emulator for the SFPU that works at the \_\_builtin level. Compilation and runtime are extremely fast (sub 1 second) so this may be useful during development.

Look in the file main.cc in the `sfpi` submodule under `src/ckernels`, there is an example kernel there to lead the way.

The main difference between compilation and running on HW is that the emulator has an infinite number of registers and so code that runs there may fail on the HW due to spilling. The `Makefile` builds for both rv32 (generating a `.S` file) and x86 (to run through emulation) and so an "out of registers" message for rv32 tells you you have work to do.

The emulator for WH is not fully implemented (missing some of the new WH specific instructions)

### Tools

The sfpi submodule contains a `tools` directory. `cd` into that directory and type `make` to build `fp16c` which is a converter that converts floating point values to fp16a, fp16b and the LUT instruction's fp8 as well as the other way (integer to float/fp16a/fp16b/fp8). This is useful for writing optimal code or looking through assembly dumps.

## Pitfalls/Oddities/Limitations

### Arrays/Storing to Memory

The SFPU can only read/write vectors to/from the destination register, it cannot read/write them to memory. Therefore, SFPI does not support arrays of vectors. Using arrays may work if the optimizer is able to optimize out the loads/stores, however, this is brittle and so is not recommended. Storing a vector to memory will result in an error similar to the following:

``` c++
tt-metal/tt_metal/hw/ckernels/sfpi/include/sfpi.h:792:7: error: cannot write sfpu vector to memory
  792 |     v = (initialized) ? __builtin_rvtt_sfpassign_lv(v, in) : in;
      |       ^
/tt-metal/tt_metal/hw/ckernels/sfpi/include/sfpi.h:792:7: error: cannot write sfpu vector to memory
```

### Function Calls

There is no ABI and none of the vector types can be passed on the stack. Therefore, all function calls must be inlined. To ensure this use `sfpi_inline`, which is defined to `__attribute__((always_inline))` on GCC.

### Register Spilling

The compiler does not implement register spilling. Since Grayskull only has 4 LRegs, running out of registers is a common occurrence. If you see the following: `error: cannot store SFPU register (reigster spill?) - exiting!` you have most likely run out of registers.

### Error Messages

Unfortunately, many errors are attributed to the code in the wrapper rather than in the code being written. For example, using an uninitialized variable would show an error at a macro called by a wrapper function before showing the line number in the user's code.

### Limitations

> - Forgetting a `v_endif` results in mismatched {} error which can be confusing (however, catches the case where a `v_endif` is missing!)
> - In general, incorrect use of vector operations (e.g., accidentally using a scalar argument instead of a vector) results in warnings/errors within the wrapper rather than in the calling code
> - Keeping too many variables alive at once (4 on GS) requires register spilling which is not implemented and causes a compiler abort
> - The gcc compiler occasionally moves a value from one register to another for no apparent reason. At this point it appears there is nothing that can be done about this besides hoping that the issue is fixed in a future version of gcc.
