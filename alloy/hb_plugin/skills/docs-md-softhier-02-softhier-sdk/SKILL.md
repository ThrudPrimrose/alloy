---
name: docs-md-softhier-02-softhier-sdk
description: "softhier-sdk's README.md and runtime headers, verbatim (vendor documentation for SoftHier v1)."
when: "before writing a SoftHier kernel or calling a flex_* runtime function."
---

# softhier-sdk

## README.md

```markdown
# 🌿 SoftHier SDK

The **SoftHier SDK** is a [PULP Platform](https://pulp-platform.org/index.html) software package developed by ETH Zurich and the University of Bologna as part of the [PULP project](https://pulp-platform.org/index.html).

This repository provides useful tools for programming and running software applications on **SoftHier**, a modeling and simulation framework for tile-based many-PE accelerators on the [GVSoC](https://github.com/gvsoc/gvsoc) event-based simulator. It is designed to be used together with a GVSoC source tree for benchmarking, debugging, and profiling software running on SoftHier architectures.

The SDK includes the SoftHier software runtime headers, startup and linker files, a default example application, configuration utilities, and Makefile integration targets for building and running SoftHier simulations.

For more background, see the [PULP Platform](https://pulp-platform.org/index.html) project page and the [GVSoC repository](https://github.com/gvsoc/gvsoc).

## 📍 Where This Fits

```text
gvsoc/
├── pulp/pulp/chips/soft_hier_old/     # Legacy SoftHier GVSoC models
├── soft_hier_sdk/                     # This SDK
│   ├── sourceme.sh                    # Environment + SDK-local toolchain setup
│   ├── softhier_old.mk                # Root make targets for SoftHier-old
│   ├── runtime/                       # Legacy runtime and linker scripts
│   ├── examples/SoftHier/             # Original example apps and arch configs
│   ├── implementation/                # Kernel-generation flows and LLM kernels
│   ├── utilities/                     # Arch/header/preload/perfetto utilities
└── Makefile                           # Includes soft_hier_sdk/softhier_old.mk
```

Run commands from the `gvsoc/` repository root unless a command explicitly uses
`make -C soft_hier_sdk/implementation`.

## ⚡ Quick Start

Navigate to the root of your GVSOC repository and add the following line to your `Makefile`:

```makefile
include soft_hier_sdk/softhier_old.mk
```

Initialize the SoftHier SDK environment:
```bash
source soft_hier_sdk/sourceme.sh
```

Then build and run the default SoftHier example:

```bash
make sh-old-hs
make sh-old-runv
```

The default target is:

```text
pulp.chips.soft_hier_old.flex_cluster
```

The default architecture config is:

```text
soft_hier_sdk/examples/SoftHier/config/arch_NoC512.py
```

The default application is:

```text
soft_hier_sdk/runtime/app_example
```

## 🏗️ Root Make Targets

The root `Makefile` includes `soft_hier_sdk/softhier_old.mk`, which provides the legacy SoftHier
flow with explicit `sh-old-*` targets.

| Target | Purpose |
| --- | --- |
| `make sh-old-config` | Copy the selected arch config into the model tree and generate runtime arch headers. |
| `make sh-old-hw` | Build the merged GVSoC SoftHier-old hardware target. |
| `make sh-old-sw` | Build the selected SoftHier software app into `soft_hier_sdk/sw_build/softhier.elf`. |
| `make sh-old-hs` | Build both hardware and software. |
| `make sh-old-run` | Run with a focused RedMule trace for cluster 0. |
| `make sh-old-runv` | Run with RedMule, iDMA, and cluster-register traces, saving `analyze_trace.txt`. |
| `make sh-old-pfto` | Convert `analyze_trace.txt` to Perfetto JSON. |
| `make sh-old-clean-sw` | Remove `soft_hier_sdk/sw_build`. |

Useful make variables:

| Variable | Default | Meaning |
| --- | --- | --- |
| `cfg=...` | `soft_hier_sdk/examples/SoftHier/config/arch_NoC512.py` | Architecture configuration. |
| `app=...` | `soft_hier_sdk/runtime/app_example` | Software application directory. |
| `core_model=fast` | `fast` | Core model selector: `fast` or `accurate`. |
| `pld=...` | empty | Optional HBM preload ELF. |

Example:

```bash
make sh-old-hs \
  cfg=soft_hier_sdk/examples/SoftHier/config/arch_NoC512.py \
  app=soft_hier_sdk/examples/SoftHier/software/gemm_systolic \
  core_model=fast

make sh-old-runv \
  cfg=soft_hier_sdk/examples/SoftHier/config/arch_NoC512.py \
  core_model=fast
```

## 🧠 Core Model Selection

SoftHier-old can run with either:

| Mode | Use |
| --- | --- |
| `core_model=fast` | Fast Snitch model. This is the default and the recommended mode for long legacy apps. |
| `core_model=accurate` | More detailed Snitch + FP subsystem path. Use for core-model debugging. |

The selector is passed to GVSoC as:

```text
--core-model=fast
```

or:

```text
--core-model=accurate
```

## ✅ Verified Applications

### 🏷️ Annotation API Test

The annotation test exercises the complete annotation lifecycle on every core,
including concurrent IDs, dynamic labels, invalid-label rejection, active
interval handling, ID `0`, `UINT32_MAX`, and per-cluster isolation.

Build the hardware model and test application:

```bash
source soft_hier_sdk/sourceme.sh

make sh-old-hs \
  cfg=soft_hier_sdk/examples/SoftHier/config/arch_NoC1024.py \
  app=soft_hier_sdk/examples/SoftHier/software/annotation_test \
  core_model=fast
```

Run with cluster-register tracing enabled:

```bash
make sh-old-runv \
  cfg=soft_hier_sdk/examples/SoftHier/config/arch_NoC1024.py \
  core_model=fast
```

Check the application result:

```bash
rg "ANNOTATION_TEST_(PASS|FAIL)" soft_hier_sdk/sw_build/analyze_trace.txt
```

A successful run prints:

```text
ANNOTATION_TEST_PASS
```

Convert the annotation intervals into cluster-scoped Perfetto tracks:

```bash
make sh-old-pfto
```

The verbose trace and converted output are written to:

```text
soft_hier_sdk/sw_build/analyze_trace.txt
soft_hier_sdk/sw_build/roi.json
soft_hier_sdk/sw_build/perfetto.json
```

### 🟥 GEMM Systolic, NoC512

```bash
source soft_hier_sdk/sourceme.sh

make sh-old-hs \
  cfg=soft_hier_sdk/examples/SoftHier/config/arch_NoC512.py \
  app=soft_hier_sdk/examples/SoftHier/software/gemm_systolic \
  core_model=fast

make sh-old-runv \
  cfg=soft_hier_sdk/examples/SoftHier/config/arch_NoC512.py \
  core_model=fast
```

RedMule checkpoint:

```bash
rg -c "GEMM id" soft_hier_sdk/sw_build/analyze_trace.txt
rg "GEMM id = 256|Performance Counter|Simulation stopped" soft_hier_sdk/sw_build/analyze_trace.txt
```

A healthy full run should frequently print lines like:

```text
[LightRedmule] Finished : ... | GEMM id = ... | M-N-K = 256-256-256
```

### 🟥 GEMM Systolic, NoC1024

```bash
source soft_hier_sdk/sourceme.sh

make sh-old-hs \
  cfg=soft_hier_sdk/examples/SoftHier/config/arch_NoC1024.py \
  app=soft_hier_sdk/examples/SoftHier/software/gemm_systolic \
  core_model=fast

make sh-old-runv \
  cfg=soft_hier_sdk/examples/SoftHier/config/arch_NoC1024.py \
  core_model=fast
```

Use the same RedMule checkpoint commands as NoC512.

### 🟦 RMSNorm

The RMSNorm flow lives under `soft_hier_sdk/implementation` because it generates kernel-specific
headers and preload data before building the old app.

```bash
source soft_hier_sdk/sourceme.sh
make -C soft_hier_sdk/implementation norm-runv
```

This uses:

```text
soft_hier_sdk/implementation/config/arch/arch.py
soft_hier_sdk/implementation/config/kernels/norm.py
soft_hier_sdk/implementation/sw/RMSNorm
```

Generated files:

```text
soft_hier_sdk/implementation/sw/RMSNorm/include/norm.h
soft_hier_sdk/implementation/sw/RMSNorm/include/preload.h
soft_hier_sdk/implementation/sw/RMSNorm/preload.elf
```

RMSNorm mainly exercises iDMA and vector instructions, not the RedMule GEMM datapath.

## 🧪 Trace And Perfetto Flow

Run a verbose trace:

```bash
make sh-old-runv \
  cfg=soft_hier_sdk/examples/SoftHier/config/arch_NoC512.py \
  core_model=fast
```

Trace output:

```text
soft_hier_sdk/sw_build/analyze_trace.txt
```

Convert to Perfetto:

```bash
make sh-old-pfto
```

Generated files:

```text
soft_hier_sdk/sw_build/roi.json
soft_hier_sdk/sw_build/perfetto.json
```

## 🧬 Architecture And Kernel Configuration

Architecture configs define cluster count, core count, TCDM, HBM layout, NoC width, Spatz attachment,
RedMule shape, and synchronization ranges.

Common configs:

```text
soft_hier_sdk/examples/SoftHier/config/arch_NoC512.py
soft_hier_sdk/examples/SoftHier/config/arch_NoC1024.py
soft_hier_sdk/implementation/config/arch/arch.py
```

Kernel configs for the implementation flow:

```text
soft_hier_sdk/implementation/config/kernels/attn.py
soft_hier_sdk/implementation/config/kernels/gemm.py
soft_hier_sdk/implementation/config/kernels/norm.py
soft_hier_sdk/implementation/config/kernels/acti.py
```

The implementation Makefile supports:

```bash
make -C soft_hier_sdk/implementation attn-run
make -C soft_hier_sdk/implementation gemm-run
make -C soft_hier_sdk/implementation norm-run
make -C soft_hier_sdk/implementation acti-run
```

Use `*-runv` for verbose traces.

## 🧹 Cleaning

Remove the root software build:

```bash
make sh-old-clean-sw
```

Remove generated implementation-kernel files:

```bash
make -C soft_hier_sdk/implementation norm-clean
make -C soft_hier_sdk/implementation gemm-clean
make -C soft_hier_sdk/implementation attn-clean
make -C soft_hier_sdk/implementation acti-clean
```

The SDK-local toolchain is intentionally not removed by these commands.

## 🛠️ Troubleshooting

### Compiler is not SDK-local

Check:

```bash
source soft_hier_sdk/sourceme.sh
which riscv32-unknown-elf-gcc
```

Expected:

```text
.../soft_hier_sdk/toolchain/install/bin/riscv32-unknown-elf-gcc
```

If the compiler is missing, check that the old-release archive exists:

```text
../soft_hier_release/third_party/toolchain/toolchain.tar.xz
```

### RedMule trace is silent

For GEMM, the correct run should frequently emit:

```text
[LightRedmule] Finished : ... GEMM id = ...
```

If not, verify:

1. The app is `soft_hier_sdk/examples/SoftHier/software/gemm_systolic`.
2. The command used `make sh-old-runv` or explicitly enabled a RedMule trace.
3. The architecture config was copied through `make sh-old-config` or any target depending on it.
4. The binary was rebuilt after changing `cfg` or `app`.

### Build uses stale software

Rebuild software explicitly:

```bash
make sh-old-sw \
  cfg=soft_hier_sdk/examples/SoftHier/config/arch_NoC512.py \
  app=soft_hier_sdk/examples/SoftHier/software/gemm_systolic
```

### RMSNorm headers are missing

Use the implementation Makefile; it generates `norm.h`, `preload.h`, and `preload.elf` before build:

```bash
make -C soft_hier_sdk/implementation norm-pre
```

## 📌 Notes For Maintainers

- Keep old application source code unchanged when validating the merge.
- Keep SoftHier-old hardware compatibility changes inside `pulp/pulp/chips/soft_hier_old`.
- `soft_hier_sdk/toolchain/` is generated by `sourceme.sh` and ignored by git.
- `soft_hier_sdk/sw_build/` is a generated software build directory.
- For regression checks, GEMM RedMule trace density is the strongest signal that the old custom
  instruction path, offload decoder, iDMA, RedMule, and synchronization path are all connected.
```

## runtime/runtime/include/flex_alloc.h

```cpp
// Copyright 2025 ETH Zurich and University of Bologna.
// Licensed under the Apache License, Version 2.0, see LICENSE for details.
// SPDX-License-Identifier: Apache-2.0

// Authors: Bowen Wang    <bowwang@iis.ee.ethz.ch>
//          Gua Hao Khov, ETH Zurich

/*
Dynamic memory allocation based on linked list of free memory blocks
*/

#ifndef _FLEX_ALLOC_H_
#define _FLEX_ALLOC_H_

#include <stdint.h>
#include "flex_printf.h"
#include "flex_cluster_arch.h"

/*
Desc: Free-memory-block indicator
@var: (unit32_t)               size -- capacity of the free memory block (in bytes)
@var: (struct alloc_block_s *) next -- pointer to the next free memory block
*/
typedef struct alloc_block_s {
  uint32_t size;
  struct alloc_block_s *next;
} alloc_block_t;

/*
Desc: Allocator data structure
@var: (alloc_block_t *) first block -- pointer to the first free memory block
*/
typedef struct {
  alloc_block_t *first_block;
} alloc_t;


/********************
*  Initialization   *
********************/

// Initialize the first free-memory-block indicator, and set up the pointer in the allocator
void flex_cluster_alloc_init(alloc_t *alloc, void *base, const uint32_t size);

/***************
*  Allocation  *
***************/

// Memory alllocation with programmer-specified allocator
void *domain_malloc(alloc_t *alloc, const uint32_t size);

// Memory allocation with default l1 heap allocator
void *flex_l1_malloc(const uint32_t size);
void *flex_hbm_malloc(const uint32_t size);


/******************
*  De-allocation  *
******************/

// De-allocation with programmer-specified allocator
void domain_free(alloc_t *alloc, void *const ptr);

// De-allocation with default l1 heap allocator
void flex_l1_free(void *const ptr);
void flex_hbm_free(void *const ptr);

/*********************
*  Helper functions  *
*********************/

// Return the address of the default l1 heap allocator
alloc_t *flex_get_allocator_l1();
alloc_t *flex_get_allocator_hbm();

// [debug] print all free-memory-blocks in l1 heap
void flex_dump_heap();



/********************
*  Implementations  *
********************/

// Block Alignment
#define MIN_BLOCK_SIZE (uint32_t)sizeof(alloc_block_t)

// Alignment functions (size must be a power of 2)
#define ALIGN_UP(addr, size) ((addr + size - 1) & ~(size - 1))
#define ALIGN_DOWN(addr, size) (addr & ~(size - 1))

// Allocator
// TODO: currently placed at a selected address
// bowwang: we can also pass this info from config file
// #define ALLOC_L1 (0x00000000)

// volatile alloc_t * alloc_l1 = (alloc_t *) 0x00000008;
// volatile alloc_t * alloc_l1 = (alloc_t *) ALLOC_L1;
volatile alloc_t alloc_l1 __attribute__((section(".l1_prio")));

// bowwng: allocator for HBM
volatile alloc_t alloc_hbm __attribute__((section(".hbm_prio")));


/*
 Canary System based on LSBs of block pointer
 |     size     |  canary  |
 |    24-bit    |   8-bit  |
*/

typedef struct {
  uint32_t size;
  uint8_t canary;
} canary_and_size_t;

static inline uint8_t canary(const void *const ptr) {
  return (uint32_t)ptr & 0xFF;
}

static inline uint32_t canary_encode(const void *const ptr,
                                     const uint32_t size) {
  return (size << 8) | canary(ptr);
}

static inline canary_and_size_t canary_decode(const uint32_t value) {
  return (canary_and_size_t){.canary = value & 0xFF, .size = value >> 8};
}



/********************
*  Initialization   *
********************/

void flex_cluster_alloc_init(alloc_t *alloc, void *base, const uint32_t size) {
  // Create first block at base address aligned up
  uint32_t aligned_base = ALIGN_UP((uint32_t)base, MIN_BLOCK_SIZE);
  alloc_block_t *block_ptr = (alloc_block_t *)aligned_base;

  // Calculate block size aligned down
  uint32_t block_size = size - ((uint32_t)block_ptr - (uint32_t)base);
  block_size = ALIGN_DOWN(block_size, MIN_BLOCK_SIZE);

  // Setup allocator
  block_ptr->size = block_size;
  block_ptr->next = NULL;
  alloc->first_block = block_ptr;
  return;
}



/***********************
*  Memory Allocation   *
***********************/

static void *allocate_memory(alloc_t *alloc, const uint32_t size) {
  // Get first block of linked list of free blocks
  alloc_block_t *curr = alloc->first_block;
  alloc_block_t *prev = 0;

  // Search first block large enough in linked list
  while (curr && (curr->size < size)) {
    prev = curr;
    curr = curr->next;
  }

  if (curr) {
    // Update allocator
    if (curr->size == size) {
      // Special case: Whole block taken
      if (prev) {
        prev->next = curr->next;
      } else {
        alloc->first_block = curr->next;
      }
    } else {
      // Regular case: Split off block
      alloc_block_t *new_block = (alloc_block_t *)((char *)curr + size);
      new_block->size = curr->size - size;
      new_block->next = curr->next;
      if (prev) {
        prev->next = new_block;
      } else {
        alloc->first_block = new_block;
      }
    }

    // Return block pointer
    return (void *)curr;
  } else {
    // There is no free block large enough
    return NULL;
  }
}


void *domain_malloc(alloc_t *alloc, const uint32_t size) {
  // Calculate actually required block size
  uint32_t data_size = size + sizeof(uint32_t); // add size/metadata
  uint32_t block_size = ALIGN_UP(data_size, MIN_BLOCK_SIZE); // add alignment

  // 32-bit metadata = 8-bit canary + 24-bit size
  // i.e. max allowed block_size == (2^24 - 1) bytes
  if (block_size >= (1 << (sizeof(uint32_t) * 8 - sizeof(uint8_t) * 8))) {
    printf("Memory allocator: Requested memory exceeds max block size\n");
    return NULL;
  }

  // Allocate memory
  void *block_ptr = allocate_memory(alloc, block_size);
  if (!block_ptr) {
    printf("Memory allocator: No large enough block found (%d)\n", block_size);
    return NULL;
  }

  // Store canary and size into first four bytes
  *((uint32_t *)block_ptr) = canary_encode(block_ptr, block_size);

  // Return data pointer
  void *data_ptr = (void *)((uint32_t *)block_ptr + 1);
  return data_ptr;
}


void *flex_l1_malloc(const uint32_t size) {
  void *addr;
  addr = domain_malloc(&alloc_l1, size);
  return addr;
}

void *flex_hbm_malloc(const uint32_t size) {
  void *addr;
  addr = domain_malloc(&alloc_hbm, size);
  return addr;
}




/*******************
*  De-allocation   *
*******************/

static void free_memory(alloc_t *alloc, void *const ptr, const uint32_t size) {
  alloc_block_t *block_ptr = (alloc_block_t *)ptr;
  // Get first block of linked list of free blocks
  alloc_block_t *next = alloc->first_block;
  alloc_block_t *prev = 0;

  // Find position in linked list of free blocks
  while (next && next < block_ptr) {
    prev = next;
    next = next->next;
  }

  // Connect with next block
  if (((char *)block_ptr + size) == (char *)next) {
    // Special case: Coalesce with adjacent next block
    block_ptr->size = size + next->size;
    block_ptr->next = next->next;
  } else {
    // Regular case: Link to next block
    block_ptr->size = size;
    block_ptr->next = next;
  }

  if (prev) {
    // Connect with previous block
    if (((char *)prev + prev->size) == (char *)block_ptr) {
      // Special case: Coalesce with adjacent previous block
      prev->size += block_ptr->size;
      prev->next = block_ptr->next;
    } else {
      // Regular case: Link from previous block
      prev->next = block_ptr;
    }
  } else {
    alloc->first_block = block_ptr;
  }
}

void domain_free(alloc_t *alloc, void *const ptr) {
  // Get block pointer from data pointer
  void *block_ptr = (void *)((uint32_t *)ptr - 1);

  // Retrieve canary and size
  const canary_and_size_t canary_and_size =
      canary_decode(*(const uint32_t *)block_ptr);

  // Check for memory overflow
  if (canary_and_size.canary != canary(block_ptr)) {
    printf("Memory Overflow at %p\n", block_ptr);
    return;
  }

  // Free memory
  free_memory(alloc, block_ptr, canary_and_size.size);
}

void flex_l1_free(void *const ptr)  { domain_free(&alloc_l1, ptr); }
void flex_hbm_free(void *const ptr) { domain_free(&alloc_hbm, ptr); }


/**********************
*  Helper functions   *
**********************/

alloc_t *flex_get_allocator_l1() { return &alloc_l1; }
alloc_t *flex_get_allocator_hbm() { return &alloc_hbm; }


void flex_dump_heap(){
  // access the first free-memory-block indicator
  alloc_block_t *curr = (&alloc_l1)->first_block;
  uint32_t block_id = 0; // for printing

  printf("Memory allocator: Free-memory-block dump\n");
  while (curr) {
  	printf("[block_id %d] addr: 0x%08x, size (byte): %x\n", block_id, (uint32_t)curr, curr->size);
    curr = curr->next;
    block_id += 1;
  }
  printf("\n");
}

#endif
```

## runtime/runtime/include/flex_annotation.h

```cpp
//
// Copyright (C) 2026 ETH Zurich and University of Bologna
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//

#ifndef _FLEX_ANNOTATION_H_
#define _FLEX_ANNOTATION_H_

#include <stdint.h>

#include "flex_cluster_arch.h"

/*
 * Annotation register protocol.
 *
 * All registers are 32-bit and local to the calling core's cluster. String
 * bytes are packed little-endian into DATA, four bytes per MMIO access. LENGTH
 * excludes the terminating NUL.
 */
#define FLEX_ANNOTATION_COMMAND_OFFSET 0x000001c0u
#define FLEX_ANNOTATION_ID_OFFSET      0x000001c4u
#define FLEX_ANNOTATION_LENGTH_OFFSET  0x000001c8u
#define FLEX_ANNOTATION_DATA_OFFSET    0x000001ccu
#define FLEX_ANNOTATION_RESULT_OFFSET  0x000001d0u
#define FLEX_ANNOTATION_LOCK_OFFSET    0x000001d4u

#define FLEX_ANNOTATION_COMMAND_REGISTER_ID    1u
#define FLEX_ANNOTATION_COMMAND_REGISTER_WORDS 2u
#define FLEX_ANNOTATION_COMMAND_CLEAR          3u
#define FLEX_ANNOTATION_COMMAND_CLEAR_ALL      4u
#define FLEX_ANNOTATION_COMMAND_START          5u
#define FLEX_ANNOTATION_COMMAND_STOP           6u

static inline void annotation_mmio_fence(void)
{
    __asm__ volatile("fence iorw, iorw" ::: "memory");
}

static inline void annotation_mmio_write(uint32_t offset, uint32_t value)
{
    volatile uint32_t *reg =
        (volatile uint32_t *)(uintptr_t)(ARCH_CLUSTER_REG_BASE + offset);

    annotation_mmio_fence();
    *reg = value;
    annotation_mmio_fence();
}

static inline uint32_t annotation_mmio_read(uint32_t offset)
{
    volatile uint32_t *reg =
        (volatile uint32_t *)(uintptr_t)(ARCH_CLUSTER_REG_BASE + offset);

    annotation_mmio_fence();
    uint32_t value = *reg;
    annotation_mmio_fence();
    return value;
}

static inline void annotation_lock_acquire(void)
{
    while (!annotation_mmio_read(FLEX_ANNOTATION_LOCK_OFFSET))
    {
    }
}

static inline void annotation_lock_release(void)
{
    /* The model treats any write to LOCK as a release. */
    annotation_mmio_write(FLEX_ANNOTATION_LOCK_OFFSET, 0u);
}

/* Caller must hold the annotation lock for the complete transaction. */
static inline uint32_t annotation_command_with_id_locked(uint32_t command,
                                                         uint32_t id)
{
    annotation_mmio_write(FLEX_ANNOTATION_ID_OFFSET, id);
    annotation_mmio_write(FLEX_ANNOTATION_COMMAND_OFFSET, command);
    return annotation_mmio_read(FLEX_ANNOTATION_RESULT_OFFSET);
}

/*
 * Scan a valid C string without imposing an artificial annotation-size limit.
 * A UINT32_MAX-byte string is representable by the MMIO protocol; anything
 * longer is not. As with every strlen-like operation, the caller must provide
 * readable, stable, NUL-terminated storage. A general invalid non-NULL pointer
 * cannot be detected by C code before dereferencing it.
 */
static inline uint32_t annotation_string_length(const char *str,
                                                uint32_t *length)
{
    uint32_t current = 0;

    if (str == (const char *)0 || str[0] == '\0')
    {
        return 0;
    }

    while (str[current] != '\0')
    {
        if (current == UINT32_MAX)
        {
            return 0;
        }
        current++;
    }

    *length = current;
    return 1;
}

static inline uint32_t annotation_register_id(uint32_t id)
{
    uint32_t result;

    annotation_lock_acquire();
    result = annotation_command_with_id_locked(
        FLEX_ANNOTATION_COMMAND_REGISTER_ID, id);
    annotation_lock_release();
    return result;
}

static inline uint32_t annotation_register_words(uint32_t id, const char *str)
{
    uint32_t length;
    uint32_t position = 0;

    if (!annotation_string_length(str, &length))
    {
        return 0;
    }

    annotation_lock_acquire();
    annotation_mmio_write(FLEX_ANNOTATION_ID_OFFSET, id);
    annotation_mmio_write(FLEX_ANNOTATION_LENGTH_OFFSET, length);
    annotation_mmio_write(FLEX_ANNOTATION_COMMAND_OFFSET,
                          FLEX_ANNOTATION_COMMAND_REGISTER_WORDS);

    /*
     * The first result read is a preflight check. In particular, it avoids
     * streaming the string when the ID is not registered or is active.
     */
    if (!annotation_mmio_read(FLEX_ANNOTATION_RESULT_OFFSET))
    {
        annotation_lock_release();
        return 0;
    }

    while (position < length)
    {
        uint32_t remaining = length - position;
        uint32_t chunk_size = remaining < 4u ? remaining : 4u;
        uint32_t word = 0;

        for (uint32_t byte = 0; byte < chunk_size; byte++)
        {
            word |= ((uint32_t)(uint8_t)str[position + byte]) << (byte * 8u);
        }

        annotation_mmio_write(FLEX_ANNOTATION_DATA_OFFSET, word);
        position += chunk_size;
    }

    uint32_t result = annotation_mmio_read(FLEX_ANNOTATION_RESULT_OFFSET);
    annotation_lock_release();
    return result;
}

static inline uint32_t annotation_register_clear(uint32_t id)
{
    uint32_t result;

    annotation_lock_acquire();
    result = annotation_command_with_id_locked(FLEX_ANNOTATION_COMMAND_CLEAR,
                                               id);
    annotation_lock_release();
    return result;
}

static inline uint32_t annotation_register_clear_all(void)
{
    uint32_t result;

    annotation_lock_acquire();
    annotation_mmio_write(FLEX_ANNOTATION_COMMAND_OFFSET,
                          FLEX_ANNOTATION_COMMAND_CLEAR_ALL);
    result = annotation_mmio_read(FLEX_ANNOTATION_RESULT_OFFSET);
    annotation_lock_release();
    return result;
}

static inline uint32_t annotation_start(uint32_t id)
{
    uint32_t result;

    annotation_lock_acquire();
    result = annotation_command_with_id_locked(FLEX_ANNOTATION_COMMAND_START,
                                               id);
    annotation_lock_release();
    return result;
}

static inline uint32_t annotation_stop(uint32_t id)
{
    uint32_t result;

    annotation_lock_acquire();
    result = annotation_command_with_id_locked(FLEX_ANNOTATION_COMMAND_STOP,
                                               id);
    annotation_lock_release();
    return result;
}

#endif // _FLEX_ANNOTATION_H_
```

## runtime/runtime/include/flex_cluster_arch.h

```cpp
//
// Copyright (C) 2026 ETH Zurich and University of Bologna
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//

// Author: Chi Zhang <chizhang@ethz.ch>

#ifndef FLEXCLUSTERARCH_H
#define FLEXCLUSTERARCH_H

#define ARCH_NUM_CLUSTER_X 2
#define ARCH_NUM_CLUSTER_Y 2
#define ARCH_NUM_CORE_PER_CLUSTER 3
#define ARCH_CLUSTER_TCDM_BANK_WIDTH 64
#define ARCH_CLUSTER_TCDM_BANK_NB 64
#define ARCH_CLUSTER_TCDM_BASE 0x0
#define ARCH_CLUSTER_TCDM_SIZE 0x100000
#define ARCH_CLUSTER_TCDM_REMOTE 805306368
#define ARCH_CLUSTER_STACK_BASE 0x10000000
#define ARCH_CLUSTER_STACK_SIZE 0x20000
#define ARCH_CLUSTER_ZOMEM_BASE 0x18000000
#define ARCH_CLUSTER_ZOMEM_SIZE 0x20000
#define ARCH_CLUSTER_REG_BASE 0x20000000
#define ARCH_CLUSTER_REG_SIZE 0x200
#define ARCH_SPATZ_ATTACED_CORES 1
#define ARCH_SPATZ_ATTACED_CHECK_LIST {1, 0, 0}
#define ARCH_SPATZ_ATTACED_SID_LIST {0, 0, 0}
#define ARCH_SPATZ_ATTACED_CORE_LIST {0}
#define ARCH_SPATZ_NUM_VLSU_PORT 4
#define ARCH_SPATZ_NUM_FUNCTION_UNIT 4
#define ARCH_SPATZ_VLSU_PORT_WIDTH 64
#define ARCH_REDMULE_CE_HEIGHT 128
#define ARCH_REDMULE_CE_WIDTH 32
#define ARCH_REDMULE_CE_PIPE 3
#define ARCH_REDMULE_ELEM_SIZE 0x2
#define ARCH_REDMULE_QUEUE_DEPTH 1
#define ARCH_REDMULE_REG_BASE 0x20020000
#define ARCH_REDMULE_REG_SIZE 0x200
#define ARCH_IDMA_OUTSTAND_TXN 16
#define ARCH_IDMA_OUTSTAND_BURST 256
#define ARCH_HBM_START_BASE 0xc0000000
#define ARCH_HBM_NODE_ADDR_SPACE 0x4000000
#define ARCH_NUM_NODE_PER_CTRL 1
#define ARCH_HBM_CHAN_PLACEMENT [2, 0, 0, 2]
#define ARCH_NOC_OUTSTANDING 64
#define ARCH_NOC_LINK_WIDTH 512
#define ARCH_INSTRUCTION_MEM_BASE 0x80000000
#define ARCH_INSTRUCTION_MEM_SIZE 0x10000
#define ARCH_SOC_REGISTER_BASE 0x90000000
#define ARCH_SOC_REGISTER_SIZE 0x10000
#define ARCH_SOC_REGISTER_EOC 2415919104
#define ARCH_SOC_REGISTER_WAKEUP 2415919108
#define ARCH_SYNC_BASE 0x40000000
#define ARCH_SYNC_INTERLEAVE 128
#define ARCH_SYNC_SPECIAL_MEM 64

#endif // FLEXCLUSTERARCH_H
```

## runtime/runtime/include/flex_cluster_arch.inc

```cpp
#
# Copyright (C) 2026 ETH Zurich and University of Bologna
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

# Author: Chi Zhang <chizhang@ethz.ch>

#ifndef FLEXCLUSTERARCH_H
#define FLEXCLUSTERARCH_H

.set ARCH_NUM_CLUSTER_X, 2
.set ARCH_NUM_CLUSTER_Y, 2
.set ARCH_NUM_CORE_PER_CLUSTER, 3
.set ARCH_CLUSTER_TCDM_BANK_WIDTH, 64
.set ARCH_CLUSTER_TCDM_BANK_NB, 64
.set ARCH_CLUSTER_TCDM_BASE, 0x0
.set ARCH_CLUSTER_TCDM_SIZE, 0x100000
.set ARCH_CLUSTER_TCDM_REMOTE, 805306368
.set ARCH_CLUSTER_STACK_BASE, 0x10000000
.set ARCH_CLUSTER_STACK_OFFSET, 15
.set ARCH_CLUSTER_STACK_SIZE, 0x20000
.set ARCH_CLUSTER_ZOMEM_BASE, 0x18000000
.set ARCH_CLUSTER_ZOMEM_SIZE, 0x20000
.set ARCH_CLUSTER_REG_BASE, 0x20000000
.set ARCH_CLUSTER_REG_SIZE, 0x200
.set ARCH_SPATZ_NUM_VLSU_PORT, 4
.set ARCH_SPATZ_NUM_FUNCTION_UNIT, 4
.set ARCH_SPATZ_VLSU_PORT_WIDTH, 64
.set ARCH_REDMULE_CE_HEIGHT, 128
.set ARCH_REDMULE_CE_WIDTH, 32
.set ARCH_REDMULE_CE_PIPE, 3
.set ARCH_REDMULE_ELEM_SIZE, 0x2
.set ARCH_REDMULE_QUEUE_DEPTH, 1
.set ARCH_REDMULE_REG_BASE, 0x20020000
.set ARCH_REDMULE_REG_SIZE, 0x200
.set ARCH_IDMA_OUTSTAND_TXN, 16
.set ARCH_IDMA_OUTSTAND_BURST, 256
.set ARCH_HBM_START_BASE, 0xc0000000
.set ARCH_HBM_NODE_ADDR_SPACE, 0x4000000
.set ARCH_NUM_NODE_PER_CTRL, 1
.set ARCH_NOC_OUTSTANDING, 64
.set ARCH_NOC_LINK_WIDTH, 512
.set ARCH_INSTRUCTION_MEM_BASE, 0x80000000
.set ARCH_INSTRUCTION_MEM_SIZE, 0x10000
.set ARCH_SOC_REGISTER_BASE, 0x90000000
.set ARCH_SOC_REGISTER_SIZE, 0x10000
.set ARCH_SOC_REGISTER_EOC, 2415919104
.set ARCH_SOC_REGISTER_WAKEUP, 2415919108
.set ARCH_SYNC_BASE, 0x40000000
.set ARCH_SYNC_INTERLEAVE, 128
.set ARCH_SYNC_SPECIAL_MEM, 64

#endif // FLEXCLUSTERARCH_H
```

## runtime/runtime/include/flex_dma_pattern.h

```cpp
//
// Copyright (C) 2026 ETH Zurich and University of Bologna
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// Author: Chi Zhang <chizhang@ethz.ch>

#ifndef _FLEX_DMA_PATTERN_H_
#define _FLEX_DMA_PATTERN_H_

#include "flex_runtime.h"
#include "flex_cluster_arch.h"
#include <stddef.h>

/********************************************
*  iDMA Trigger Fucntions (Customized ISA)  *
********************************************/

#define OP_CUSTOM1 0b0101011
#define XDMA_FUNCT3 0b000
#define DMSRC_FUNCT7 0b0000000
#define DMDST_FUNCT7 0b0000001
#define DMCPYI_FUNCT7 0b0000010
#define DMCPYC_FUNCT7 0b0000011
#define DMSTATI_FUNCT7 0b0000100
#define DMMASK_FUNCT7 0b0000101
#define DMSTR_FUNCT7 0b0000110
#define DMREP_FUNCT7 0b0000111

typedef enum {
    COLLECTIVE_REDADD_UINT_16,
    COLLECTIVE_REDADD_INT_16,
    COLLECTIVE_REDADD_FP_16,
    COLLECTIVE_REDMAX_UINT_16,
    COLLECTIVE_REDMAX_INT_16,
    COLLECTIVE_REDMAX_FP_16
} collective_compute_format_t;

#define R_TYPE_ENCODE(funct7, rs2, rs1, funct3, rd, opcode)                    \
    ((funct7 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | \
     (opcode))

inline uint32_t bare_dma_start_1d(uint64_t dst, uint64_t src,
                                          size_t size) {
    register uint32_t reg_dst_low asm("a0") = dst >> 0;    // 10
    register uint32_t reg_dst_high asm("a1") = dst >> 32;  // 11
    register uint32_t reg_src_low asm("a2") = src >> 0;    // 12
    register uint32_t reg_src_high asm("a3") = src >> 32;  // 13
    register uint32_t reg_size asm("a4") = size;           // 14

    // dmsrc a2, a3
    asm volatile(".word %0\n" ::"i"(R_TYPE_ENCODE(DMSRC_FUNCT7, 13, 12,
                                                  XDMA_FUNCT3, 0, OP_CUSTOM1)),
                 "r"(reg_src_high), "r"(reg_src_low));

    // dmdst a0, a1
    asm volatile(".word %0\n" ::"i"(R_TYPE_ENCODE(DMDST_FUNCT7, 11, 10,
                                                  XDMA_FUNCT3, 0, OP_CUSTOM1)),
                 "r"(reg_dst_high), "r"(reg_dst_low));

    // dmcpyi a0, a4, 0b00
    register uint32_t reg_txid asm("a0");  // 10
    asm volatile(".word %1\n"
                 : "=r"(reg_txid)
                 : "i"(R_TYPE_ENCODE(DMCPYI_FUNCT7, 0b00000, 14, XDMA_FUNCT3,
                                     10, OP_CUSTOM1)),
                   "r"(reg_size));

    return reg_txid;
}

inline uint32_t bare_dma_start_2d(uint64_t dst, uint64_t src,
                                                 size_t size, size_t dst_stride,
                                                 size_t src_stride,
                                                 size_t repeat) {
    register uint32_t reg_dst_low asm("a0") = dst >> 0;       // 10
    register uint32_t reg_dst_high asm("a1") = dst >> 32;     // 11
    register uint32_t reg_src_low asm("a2") = src >> 0;       // 12
    register uint32_t reg_src_high asm("a3") = src >> 32;     // 13
    register uint32_t reg_size asm("a4") = size;              // 14
    register uint32_t reg_dst_stride asm("a5") = dst_stride;  // 15
    register uint32_t reg_src_stride asm("a6") = src_stride;  // 16
    register uint32_t reg_repeat asm("a7") = repeat;          // 17

    // dmsrc a0, a1
    asm volatile(".word %0\n" ::"i"(R_TYPE_ENCODE(DMSRC_FUNCT7, 13, 12,
                                                  XDMA_FUNCT3, 0, OP_CUSTOM1)),
                 "r"(reg_src_high), "r"(reg_src_low));

    // dmdst a0, a1
    asm volatile(".word %0\n" ::"i"(R_TYPE_ENCODE(DMDST_FUNCT7, 11, 10,
                                                  XDMA_FUNCT3, 0, OP_CUSTOM1)),
                 "r"(reg_dst_high), "r"(reg_dst_low));

    // dmstr a5, a6
    asm volatile(".word %0\n" ::"i"(R_TYPE_ENCODE(DMSTR_FUNCT7, 15, 16,
                                                  XDMA_FUNCT3, 0, OP_CUSTOM1)),
                 "r"(reg_src_stride), "r"(reg_dst_stride));

    // dmrep a7
    asm volatile(".word %0\n" ::"i"(R_TYPE_ENCODE(DMREP_FUNCT7, 0, 17,
                                                  XDMA_FUNCT3, 0, OP_CUSTOM1)),
                 "r"(reg_repeat));

    // dmcpyi a0, a4, 0b10
    register uint32_t reg_txid asm("a0");  // 10
    asm volatile(".word %1\n"
                 : "=r"(reg_txid)
                 : "i"(R_TYPE_ENCODE(DMCPYI_FUNCT7, 0b00010, 14, XDMA_FUNCT3,
                                     10, OP_CUSTOM1)),
                   "r"(reg_size));

    return reg_txid;
}

inline void bare_dma_set_mask(uint16_t row_mask, uint16_t col_mask){
    uint32_t mask = col_mask;
    mask = (mask << 16) | row_mask;
    register uint32_t reg_mask asm("a5") = mask;           // 15
    //dmmask a5, a5
    asm volatile(".word %0\n" ::"i"(R_TYPE_ENCODE(DMMASK_FUNCT7, 15, 15,
                                                  XDMA_FUNCT3, 15, OP_CUSTOM1)),
                 "r"(reg_mask), "r"(reg_mask));
}

inline uint32_t bare_dma_start_1d_broadcast(uint64_t dst, uint64_t src,
                            size_t size, uint16_t row_mask, uint16_t col_mask) {
    register uint32_t reg_dst_low asm("a0") = dst >> 0;    // 10
    register uint32_t reg_dst_high asm("a1") = dst >> 32;  // 11
    register uint32_t reg_src_low asm("a2") = src >> 0;    // 12
    register uint32_t reg_src_high asm("a3") = src >> 32;  // 13
    register uint32_t reg_size asm("a4") = size;           // 14

    bare_dma_set_mask(row_mask, col_mask);

    // dmsrc a2, a3
    asm volatile(".word %0\n" ::"i"(R_TYPE_ENCODE(DMSRC_FUNCT7, 13, 12,
                                                  XDMA_FUNCT3, 0, OP_CUSTOM1)),
                 "r"(reg_src_high), "r"(reg_src_low));

    // dmdst a0, a1
    asm volatile(".word %0\n" ::"i"(R_TYPE_ENCODE(DMDST_FUNCT7, 11, 10,
                                                  XDMA_FUNCT3, 0, OP_CUSTOM1)),
                 "r"(reg_dst_high), "r"(reg_dst_low));

    // dmcpyi a0, a4, 0b00
    register uint32_t reg_txid asm("a0");  // 10
    asm volatile(".word %1\n"
                 : "=r"(reg_txid)
                 : "i"(R_TYPE_ENCODE(DMCPYC_FUNCT7, 0b00001, 14, XDMA_FUNCT3,
                                     10, OP_CUSTOM1)),
                   "r"(reg_size));

    return reg_txid;
}

inline uint32_t bare_dma_start_1d_reduction(uint64_t dst, uint64_t src,
        size_t size, collective_compute_format_t fmt, uint16_t row_mask, uint16_t col_mask) {
    register uint32_t reg_dst_low asm("a0") = dst >> 0;    // 10
    register uint32_t reg_dst_high asm("a1") = dst >> 32;  // 11
    register uint32_t reg_src_low asm("a2") = src >> 0;    // 12
    register uint32_t reg_src_high asm("a3") = src >> 32;  // 13
    register uint32_t reg_size asm("a4") = size;           // 14

    bare_dma_set_mask(row_mask, col_mask);

    // dmsrc a2, a3
    asm volatile(".word %0\n" ::"i"(R_TYPE_ENCODE(DMSRC_FUNCT7, 13, 12,
                                                  XDMA_FUNCT3, 0, OP_CUSTOM1)),
                 "r"(reg_src_high), "r"(reg_src_low));

    // dmdst a0, a1
    asm volatile(".word %0\n" ::"i"(R_TYPE_ENCODE(DMDST_FUNCT7, 11, 10,
                                                  XDMA_FUNCT3, 0, OP_CUSTOM1)),
                 "r"(reg_dst_high), "r"(reg_dst_low));

    // dmcpyi a0, a4, 0b00
    register uint32_t reg_txid asm("a0");  // 10
    if (fmt == COLLECTIVE_REDADD_UINT_16)
    {
        asm volatile(".word %1\n"
                     : "=r"(reg_txid)
                     : "i"(R_TYPE_ENCODE(DMCPYC_FUNCT7, 0b00010, 14, XDMA_FUNCT3,
                                         10, OP_CUSTOM1)),
                       "r"(reg_size));
    } else if (fmt == COLLECTIVE_REDADD_INT_16){
        asm volatile(".word %1\n"
                     : "=r"(reg_txid)
                     : "i"(R_TYPE_ENCODE(DMCPYC_FUNCT7, 0b00011, 14, XDMA_FUNCT3,
                                         10, OP_CUSTOM1)),
                       "r"(reg_size));
    } else if (fmt == COLLECTIVE_REDADD_FP_16){
        asm volatile(".word %1\n"
                     : "=r"(reg_txid)
                     : "i"(R_TYPE_ENCODE(DMCPYC_FUNCT7, 0b00100, 14, XDMA_FUNCT3,
                                         10, OP_CUSTOM1)),
                       "r"(reg_size));
    } else if (fmt == COLLECTIVE_REDMAX_UINT_16){
        asm volatile(".word %1\n"
                     : "=r"(reg_txid)
                     : "i"(R_TYPE_ENCODE(DMCPYC_FUNCT7, 0b00101, 14, XDMA_FUNCT3,
                                         10, OP_CUSTOM1)),
                       "r"(reg_size));
    } else if (fmt == COLLECTIVE_REDMAX_INT_16){
        asm volatile(".word %1\n"
                     : "=r"(reg_txid)
                     : "i"(R_TYPE_ENCODE(DMCPYC_FUNCT7, 0b00110, 14, XDMA_FUNCT3,
                                         10, OP_CUSTOM1)),
                       "r"(reg_size));
    } else if (fmt == COLLECTIVE_REDMAX_FP_16){
        asm volatile(".word %1\n"
                     : "=r"(reg_txid)
                     : "i"(R_TYPE_ENCODE(DMCPYC_FUNCT7, 0b00111, 14, XDMA_FUNCT3,
                                         10, OP_CUSTOM1)),
                       "r"(reg_size));
    }

    return reg_txid;
}

inline void bare_dma_wait_all() {
    // dmstati t0, 2  # 2=status.busy
    asm volatile(
        "1: \n"
        ".word %0\n"
        "bne t0, zero, 1b \n" ::"i"(
            R_TYPE_ENCODE(DMSTATI_FUNCT7, 0b10, 0, XDMA_FUNCT3, 5, OP_CUSTOM1))
        : "t0");
}


/*************************************
*  Basic Asynchronize DMA Interface  *
*************************************/

//Basic DMA 1d transfter
void flex_dma_async_1d(uint64_t dst_addr, uint64_t src_addr, size_t transfer_size){
    bare_dma_start_1d(dst_addr, src_addr, transfer_size); //Start iDMA
}

//Basic DMA 2d transfter
void flex_dma_async_2d(uint64_t dst_addr, uint64_t src_addr, size_t transfer_size, size_t dst_stride, size_t src_stride, size_t repeat){
    bare_dma_start_2d(dst_addr, src_addr, transfer_size, dst_stride, src_stride, repeat); //Start iDMA
}

//Basic collective primitives
void flex_dma_async_broadcast(uint64_t dst_offset, uint64_t src_offset, size_t transfer_size, uint16_t row_mask, uint16_t col_mask){
    FlexPosition pos = get_pos(flex_get_cluster_id());
    bare_dma_start_1d_broadcast(remote_pos(pos,dst_offset), local(src_offset), transfer_size, row_mask, col_mask); //Start iDMA
}

void flex_dma_async_reduction(uint64_t dst_offset, uint64_t src_offset, size_t transfer_size, collective_compute_format_t fmt, uint16_t row_mask, uint16_t col_mask){
    FlexPosition pos = get_pos(flex_get_cluster_id());
    bare_dma_start_1d_reduction(local(dst_offset), remote_pos(pos,src_offset), transfer_size, fmt, row_mask, col_mask); //Start iDMA
}

//wait for idma
void flex_dma_async_wait_all(){
    bare_dma_wait_all(); // Wait for iDMA Finishing
}

/*************************************
*  Basic Synchronize DMA Interface   *
*************************************/

//Basic DMA 2d transfter
void flex_dma_sync_2d(uint64_t dst_addr, uint64_t src_addr, size_t transfer_size, size_t dst_stride, size_t src_stride, size_t repeat){
    bare_dma_start_2d(dst_addr, src_addr, transfer_size, dst_stride, src_stride, repeat); //Start iDMA
    bare_dma_wait_all(); // Wait for iDMA Finishing
}

/****************************************
*  Versitle Asynchronize DMA Functions  *
****************************************/


void flex_dma_async_Load_HBM_1d(uint32_t local_offset, uint32_t hbm_offset, size_t transfer_size){
    bare_dma_start_1d(local(local_offset),hbm_addr(hbm_offset), transfer_size); //Start iDMA
}

//Basic DMA 1d transfter store to HBM
void flex_dma_async_Store_HBM_1d(uint32_t local_offset, uint32_t hbm_offset, size_t transfer_size){
    bare_dma_start_1d(hbm_addr(hbm_offset), local(local_offset), transfer_size); //Start iDMA
}

/*******************************************
*  Traffic Pattern: Asynchronize Interface *
*******************************************/

//Pattern: Round Shift Right
void flex_dma_async_pattern_round_shift_right(uint32_t local_offset, uint32_t remote_offset, size_t transfer_size){
    FlexPosition pos = get_pos(flex_get_cluster_id());
    bare_dma_start_1d(local(local_offset),remote_pos(left_pos(pos),remote_offset), transfer_size); //Start iDMA
}

//Pattern: Round Shift Left
void flex_dma_async_pattern_round_shift_left(uint32_t local_offset, uint32_t remote_offset, size_t transfer_size){
    FlexPosition pos = get_pos(flex_get_cluster_id());
    bare_dma_start_1d(local(local_offset),remote_pos(right_pos(pos),remote_offset), transfer_size); //Start iDMA
}

void flex_dma_async_pattern_round_shift_up(uint32_t local_offset, uint32_t remote_offset, size_t transfer_size){
    FlexPosition pos = get_pos(flex_get_cluster_id());
    bare_dma_start_1d(local(local_offset),remote_pos(bottom_pos(pos),remote_offset), transfer_size); //Start iDMA
}


//Pattern All-to-One
void flex_dma_async_pattern_all_to_one(uint32_t local_offset, uint32_t remote_offset, size_t transfer_size){
    FlexPosition pos = get_pos(flex_get_cluster_id());
    bare_dma_start_1d(local(local_offset),remote_xy(0,0,remote_offset), transfer_size); //Start iDMA
}

//Pattern Dialog-to-Dialog
void flex_dma_async_pattern_dialog_to_dialog(uint32_t local_offset, uint32_t remote_offset, size_t transfer_size){
    FlexPosition pos = get_pos(flex_get_cluster_id());
    bare_dma_start_1d(local(local_offset),remote_xy(pos.y,pos.x,remote_offset), transfer_size); //Start iDMA
}

//Pattern Access West HBM
void flex_dma_async_pattern_access_west_hbm(uint32_t local_offset, uint32_t remote_offset, size_t transfer_size){
    FlexPosition pos = get_pos(flex_get_cluster_id());
    bare_dma_start_1d(local(local_offset),hbm_west(pos.y,remote_offset), transfer_size); //Start iDMA
}

//Pattern Access South HBM
void flex_dma_async_pattern_access_south_hbm(uint32_t local_offset, uint32_t remote_offset, size_t transfer_size){
    FlexPosition pos = get_pos(flex_get_cluster_id());
    bare_dma_start_1d(local(local_offset),hbm_south(pos.x,remote_offset), transfer_size); //Start iDMA
}

/******************************************
*  Traffic Pattern: Synchronize Interface *
******************************************/

//Pattern: Round Shift Right
void flex_dma_pattern_round_shift_right(uint32_t local_offset, uint32_t remote_offset, size_t transfer_size){
    FlexPosition pos = get_pos(flex_get_cluster_id());
    bare_dma_start_1d(local(local_offset),remote_pos(left_pos(pos),remote_offset), transfer_size); //Start iDMA
    bare_dma_wait_all(); // Wait for iDMA Finishing
}

//Pattern: Round Shift Left
void flex_dma_pattern_round_shift_left(uint32_t local_offset, uint32_t remote_offset, size_t transfer_size){
    FlexPosition pos = get_pos(flex_get_cluster_id());
    bare_dma_start_1d(local(local_offset),remote_pos(right_pos(pos),remote_offset), transfer_size); //Start iDMA
    bare_dma_wait_all(); // Wait for iDMA Finishing
}

void flex_dma_pattern_round_shift_up(uint32_t local_offset, uint32_t remote_offset, size_t transfer_size){
    FlexPosition pos = get_pos(flex_get_cluster_id());
    bare_dma_start_1d(local(local_offset),remote_pos(bottom_pos(pos),remote_offset), transfer_size); //Start iDMA
    bare_dma_wait_all(); // Wait for iDMA Finishing
}


//Pattern All-to-One
void flex_dma_pattern_all_to_one(uint32_t local_offset, uint32_t remote_offset, size_t transfer_size){
    FlexPosition pos = get_pos(flex_get_cluster_id());
    bare_dma_start_1d(local(local_offset),remote_xy(0,0,remote_offset), transfer_size); //Start iDMA
    bare_dma_wait_all(); // Wait for iDMA Finishing
}

//Pattern Dialog-to-Dialog
void flex_dma_pattern_dialog_to_dialog(uint32_t local_offset, uint32_t remote_offset, size_t transfer_size){
    FlexPosition pos = get_pos(flex_get_cluster_id());
    bare_dma_start_1d(local(local_offset),remote_xy(pos.y,pos.x,remote_offset), transfer_size); //Start iDMA
    bare_dma_wait_all(); // Wait for iDMA Finishing
}

//Pattern Access West HBM
void flex_dma_pattern_access_west_hbm(uint32_t local_offset, uint32_t remote_offset, size_t transfer_size){
    FlexPosition pos = get_pos(flex_get_cluster_id());
    bare_dma_start_1d(local(local_offset),hbm_west(pos.y,remote_offset), transfer_size); //Start iDMA
    bare_dma_wait_all(); // Wait for iDMA Finishing
}


//Pattern Systolic-like Shifting
void flex_dma_pattern_systolic_shift_west_south(uint32_t local_offset, uint32_t remote_offset, size_t transfer_size){

    FlexPosition pos = get_pos(flex_get_cluster_id());

    if(pos.x == 0){
        /* clusters at west edge hbm transfer*/
        bare_dma_start_1d(local(local_offset),hbm_west(pos.y,remote_offset), transfer_size);
    } else {
        /* clusters on-chip transfer*/
        bare_dma_start_1d(local(local_offset),remote_pos(left_pos(pos),remote_offset), transfer_size);
    }

    if (pos.y == 0)
    {
        /* clusters at south edge hbm transfer*/
        bare_dma_start_1d(local(local_offset),hbm_south(pos.x,remote_offset), transfer_size);
    } else {
        /* clusters on-chip transfer*/
        bare_dma_start_1d(local(local_offset),remote_pos(bottom_pos(pos),remote_offset), transfer_size);
    }

    bare_dma_wait_all(); // Wait for iDMA Finishing
}

#endif
```

## runtime/runtime/include/flex_dump.h

```cpp
//
// Copyright (C) 2026 ETH Zurich and University of Bologna
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// Author: Chi Zhang <chizhang@ethz.ch>

#ifndef _FLEX_DUMP_H_
#define _FLEX_DUMP_H_

#include "flex_runtime.h"
#include "flex_dma_pattern.h"
#include <stddef.h>

/************************
*      Dumping Data     *
************************/

void flex_dump_open(){
    volatile uint32_t * dump_reg = (volatile uint32_t *) (ARCH_CLUSTER_REG_BASE + ARCH_CLUSTER_REG_SIZE);
    *dump_reg = flex_get_enable_value();
}

void flex_dump_stamp(){
    volatile uint32_t * dump_reg = (volatile uint32_t *) (ARCH_CLUSTER_REG_BASE + ARCH_CLUSTER_REG_SIZE + 4);
    *dump_reg = flex_get_enable_value();
}

void flex_dump_close(){
    volatile uint32_t * dump_reg = (volatile uint32_t *) (ARCH_CLUSTER_REG_BASE + ARCH_CLUSTER_REG_SIZE + 8);
    *dump_reg = flex_get_enable_value();
}

void flex_dump_set_lower_base(uint32_t val){
    volatile uint32_t * dump_reg = (volatile uint32_t *) (ARCH_CLUSTER_REG_BASE + ARCH_CLUSTER_REG_SIZE + 12);
    *dump_reg = val;
}

void flex_dump_set_upper_base(uint32_t val){
    volatile uint32_t * dump_reg = (volatile uint32_t *) (ARCH_CLUSTER_REG_BASE + ARCH_CLUSTER_REG_SIZE + 16);
    *dump_reg = val;
}

void flex_dump_set_base(uint64_t val){
    uint32_t lower = val >> 0;
    uint32_t upper = val >> 32;
    flex_dump_set_lower_base(lower);
    flex_dump_set_upper_base(upper);
    flex_dump_stamp();
}

void flex_dump_hbm(uint64_t hbm_offset, size_t size){
	flex_dump_set_base(hbm_offset);
	flex_dma_async_1d((ARCH_CLUSTER_TCDM_BASE+ARCH_CLUSTER_TCDM_SIZE), hbm_addr(hbm_offset), size);
	flex_dma_async_wait_all();
}


#endif
```

## runtime/runtime/include/flex_group_barrier.h

```cpp
//
// Copyright (C) 2026 ETH Zurich and University of Bologna
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// Author: Chi Zhang <chizhang@ethz.ch>

#ifndef _FLEX_GROUP_BARRIER_H_
#define _FLEX_GROUP_BARRIER_H_

#include "flex_runtime.h"
#include "flex_cluster_arch.h"

/*****************************************
*  Grid Group Synchronization functions  *
*****************************************/

typedef struct GridSyncGroupInfo
{
    //General information
    uint32_t valid_grid;
    uint32_t grid_x_dim;
    uint32_t grid_y_dim;
    uint32_t grid_x_num;
    uint32_t grid_y_num;

    //Local information
    uint32_t this_grid_id;
    uint32_t this_grid_id_x;
    uint32_t this_grid_id_y;
    uint32_t this_grid_left_most;
    uint32_t this_grid_right_most;
    uint32_t this_grid_top_most;
    uint32_t this_grid_bottom_most;
    uint32_t this_grid_cluster_num;
    uint32_t this_grid_cluster_num_x;
    uint32_t this_grid_cluster_num_y;

    //Sync information
    uint8_t  wakeup_row_mask;
    uint8_t  wakeup_col_mask;
    uint32_t sync_x_cluster;
    uint32_t sync_y_cluster;
    volatile uint32_t * sync_x_point;
    volatile uint32_t * sync_x_piter;
    volatile uint32_t * sync_y_point;
    volatile uint32_t * sync_y_piter;
}GridSyncGroupInfo;

GridSyncGroupInfo grid_sync_group_init(uint32_t grid_x_dim, uint32_t grid_y_dim){
	GridSyncGroupInfo info;

	//Calculate information
	info.valid_grid = 1;
	info.grid_x_dim = grid_x_dim;
	info.grid_y_dim = grid_y_dim;

	if (grid_x_dim == 0 || grid_y_dim == 0)
	{
		info.valid_grid = 0;
		return info;
	}

    if (!(is_power_of_two(grid_x_dim) && is_power_of_two(grid_y_dim)))
    {
        info.valid_grid = 0;
        return info;
    }

	info.grid_x_num = (ARCH_NUM_CLUSTER_X + grid_x_dim - 1)/grid_x_dim;
	info.grid_y_num = (ARCH_NUM_CLUSTER_Y + grid_y_dim - 1)/grid_y_dim;

	FlexPosition pos = get_pos(flex_get_cluster_id());
	info.this_grid_id_x = pos.x/grid_x_dim;
	info.this_grid_id_y = pos.y/grid_y_dim;
	info.this_grid_id   = info.grid_x_num * info.this_grid_id_y + info.this_grid_id_x;
	info.this_grid_left_most = info.this_grid_id_x * grid_x_dim;
	info.this_grid_right_most = (info.this_grid_id_x + 1) * grid_x_dim - 1;
	info.this_grid_right_most = info.this_grid_right_most >= ARCH_NUM_CLUSTER_X? ARCH_NUM_CLUSTER_X - 1 : info.this_grid_right_most;
	info.this_grid_bottom_most = info.this_grid_id_y * grid_y_dim;
	info.this_grid_top_most = (info.this_grid_id_y + 1) * grid_y_dim - 1;
	info.this_grid_top_most = info.this_grid_top_most >= ARCH_NUM_CLUSTER_Y? ARCH_NUM_CLUSTER_Y - 1 : info.this_grid_top_most;
	info.this_grid_cluster_num_x = info.this_grid_right_most + 1 - info.this_grid_left_most;
	info.this_grid_cluster_num_y = info.this_grid_top_most + 1 - info.this_grid_bottom_most;
    info.this_grid_cluster_num   = info.this_grid_cluster_num_x * info.this_grid_cluster_num_y;

    info.wakeup_row_mask= ~(info.grid_x_dim - 1);
    info.wakeup_col_mask= ~(info.grid_y_dim - 1);
	info.sync_x_cluster = (info.this_grid_left_most + info.this_grid_right_most)/2;
	info.sync_y_cluster = (info.this_grid_bottom_most + info.this_grid_top_most)/2;
	info.sync_x_point   = (volatile uint32_t *) (ARCH_SYNC_BASE+(cluster_index(info.sync_x_cluster,pos.y              )*ARCH_SYNC_SIZE)+24);
    info.sync_x_piter   = (volatile uint32_t *) (ARCH_SYNC_BASE+(cluster_index(info.sync_x_cluster,pos.y              )*ARCH_SYNC_SIZE)+28);
    info.sync_y_point   = (volatile uint32_t *) (ARCH_SYNC_BASE+(cluster_index(info.sync_x_cluster,info.sync_y_cluster)*ARCH_SYNC_SIZE)+32);
    info.sync_y_piter   = (volatile uint32_t *) (ARCH_SYNC_BASE+(cluster_index(info.sync_x_cluster,info.sync_y_cluster)*ARCH_SYNC_SIZE)+36);

	if (flex_get_core_id() == 0)
	{
		//Reset synchronization point
		volatile uint32_t * local_sync_point_for_group_level1 = (volatile uint32_t *) (ARCH_SYNC_BASE+(flex_get_cluster_id()*ARCH_SYNC_SIZE)+24);
		volatile uint32_t * local_sync_point_for_group_level2 = (volatile uint32_t *) (ARCH_SYNC_BASE+(flex_get_cluster_id()*ARCH_SYNC_SIZE)+32);
		*local_sync_point_for_group_level1 = 0;
		*local_sync_point_for_group_level2 = 0;
	}

	return info;
}


void grid_sync_group_barrier_xy(GridSyncGroupInfo * info){

    flex_intra_cluster_sync();

    if (flex_is_dm_core()){
        flex_annotate_barrier(0);

    	volatile uint32_t * cluster_wfi_reg  = (volatile uint32_t *) ARCH_CLUSTER_REG_BASE;

        //First Barrier X
        if ((info->this_grid_cluster_num_x - flex_get_enable_value()) == flex_amo_fetch_add(info->sync_x_point)) {
            flex_reset_barrier(info->sync_x_point);

            //For cluster synced X, then sync Y
            if ((info->this_grid_cluster_num_y - flex_get_enable_value()) == flex_amo_fetch_add(info->sync_y_point))
            {
                flex_reset_barrier(info->sync_y_point);
                flex_wakeup_clusters(info->wakeup_row_mask,info->wakeup_col_mask);
            }
        }
        *cluster_wfi_reg = flex_get_enable_value();

        flex_annotate_barrier(0);
    }

    flex_intra_cluster_sync();
}

void grid_sync_group_barrier_xy_polling(GridSyncGroupInfo * info){

    flex_intra_cluster_sync();

    if (flex_is_dm_core()){
        flex_annotate_barrier(0);

        // Remember previous iteration
        uint32_t prev_barrier_iter_x     = *(info->sync_x_piter);
        uint32_t prev_barrier_iter_y     = *(info->sync_y_piter);

        //First Barrier X
        if ((info->this_grid_cluster_num_x - flex_get_enable_value()) == flex_amo_fetch_add(info->sync_x_point)) {
            flex_reset_barrier(info->sync_x_point);

            //For cluster synced X, then sync Y
            if ((info->this_grid_cluster_num_y - flex_get_enable_value()) == flex_amo_fetch_add(info->sync_y_point))
            {
                flex_reset_barrier(info->sync_y_point);
                flex_amo_fetch_add(info->sync_y_piter);
            } else {
                while((*(info->sync_y_piter)) == prev_barrier_iter_y);
            }

            flex_amo_fetch_add(info->sync_x_piter);
        } else {
            while((*(info->sync_x_piter)) == prev_barrier_iter_x);
        }
        flex_annotate_barrier(0);
    }

    flex_intra_cluster_sync();
}

#endif
```

## runtime/runtime/include/flex_libfp16.h

```cpp
//
// Copyright (C) 2026 ETH Zurich and University of Bologna
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// Author: Chi Zhang <chizhang@ethz.ch>

#ifndef _FLEX_LIBFP16_H_
#define _FLEX_LIBFP16_H_

typedef union {
    float f;
    struct {
        uint32_t mantissa : 23;
        uint32_t exponent : 8;
        uint32_t sign : 1;
    } parts;
} FloatBits;

typedef uint16_t fp16;

// Convert float to FP16 (half-precision)
fp16 float_to_fp16(float value) {
    FloatBits floatBits;
    floatBits.f = value;

    uint16_t sign = floatBits.parts.sign << 15;
    int32_t exponent = floatBits.parts.exponent - 127 + 15; // adjust bias from 127 to 15
    uint32_t mantissa = floatBits.parts.mantissa >> 13;     // reduce to 10 bits

    if (exponent <= 0) {
        if (exponent < -10) return sign;   // too small
        mantissa = (floatBits.parts.mantissa | 0x800000) >> (1 - exponent);
        return sign | mantissa;
    } else if (exponent >= 0x1F) {
        return sign | 0x7C00;  // overflow to infinity
    }
    return sign | (exponent << 10) | mantissa;
}

// Convert FP16 to float
float fp16_to_float(fp16 value) {
    FloatBits floatBits;
    floatBits.parts.sign = (value >> 15) & 0x1;
    int32_t exponent = (value >> 10) & 0x1F;
    floatBits.parts.exponent = (exponent == 0) ? 0 : exponent + 127 - 15;
    floatBits.parts.mantissa = (value & 0x3FF) << 13;
    return floatBits.f;
}

// Fused multiply-add for FP16
fp16 fp16_fma(fp16 a, fp16 b, fp16 c) {
    float fa = fp16_to_float(a);
    float fb = fp16_to_float(b);
    float fc = fp16_to_float(c);
    float result = (fa * fb) + fc;
    return float_to_fp16(result);
}

void matmul_fp16(fp16 * z, fp16 * y, fp16 * x, fp16 * w, uint16_t m_size, uint16_t n_size, uint16_t k_size){
    for (int i = 0; i < m_size; ++i)
    {
        for (int j = 0; j < k_size; ++j)
        {
            z[i * k_size + j] = y[i * k_size + j];
            for (int k = 0; k < n_size; ++k)
            {
                z[i * k_size + j] = fp16_fma(x[i * n_size + k], w[k * k_size + j], z[i * k_size + j]);
            }
        }
    }
}


inline void asm_fp16_div(const fp16 *a, const fp16 *b, fp16 *c) {
    // Load the half-precision values from memory into local variables
    // Operation: cv = av / bv
    fp16 av = *a;
    fp16 bv = *b;
    fp16 cv;

    // Perform the division using RISC-V half-precision instructions
    asm volatile(
        "fmv.h.x ft0, %[av]\n"   // move half value 'av' into ft0
        "fmv.h.x ft1, %[bv]\n"   // move half value 'bv' into ft1
        "fdiv.h   ft2, ft0, ft1\n"   // ft2 = ft0 / ft1 (half-precision)
        "fmv.x.h  %[cv], ft2\n"  // move the result from ft2 to our local variable 'cv'
        : [cv] "=r"(cv)
        : [av] "r"(av), [bv] "r"(bv)
        : "ft0", "ft1", "ft2"    // clobbered registers
    );

    // Store the result back to memory
    *c = cv;
}


inline void asm_fp16_exp(const fp16 *inp, fp16 *oup)
{
    // We'll store the input and output in local half variables
    fp16 x = *inp;
    fp16 r; // Will hold the final result

    // Some half-precision constants for the series coefficients.
    // These are approximate but good enough for a small demonstration.
    //   1.0   = 0x3C00 in half
    //   0.5   = 0x3800
    //   1/6 ≈ 0.1667  -> ~ 0.166015625 in half (0x3555)
    //   1/24 ≈ 0.0417 -> ~ 0.0416564941 in half (0x2AAA)
    static const fp16 c1      = 0x3C00;     // 1
    static const fp16 cHalf   = 0x3800;     // 1/2
    static const fp16 cOneSix = 0x3555;  // 1/6
    static const fp16 cOne24  = 0x2AAA;  // 1/24

    //
    // We will do all arithmetic in half-precision registers
    // using inline assembly with RISC-V Zfh instructions:
    //   fmv.h.x   (move half bits from int register to FP register)
    //   fmul.h    (half-precision multiply)
    //   fadd.h    (half-precision add)
    //   fmv.x.h   (move half bits from FP register to int register)
    //
    // Register usage (ft0–ft3 are temporary floating registers):
    //   ft0 = x
    //   ft1 = accumulated sum
    //   ft2, ft3 = scratch for multiplications and constants
    //

    asm volatile(
        // --- Load x into ft0 ---
        "fmv.h.x   ft0, %[x]       \n"

        // --- Start with ft1 = 1.0 ---
        "fmv.h.x   ft1, %[c1]      \n"

        // ft1 = ft1 + x   => 1 + x
        "fadd.h    ft1, ft1, ft0   \n"

        // --- Compute x^2/2 ---
        // ft2 = x^2
        "fmul.h    ft2, ft0, ft0   \n"
        // ft3 = 0.5
        "fmv.h.x   ft3, %[cHalf]   \n"
        // ft2 = ft2 * ft3 => x^2/2
        "fmul.h    ft2, ft2, ft3   \n"
        // ft1 = ft1 + ft2 => (1 + x) + x^2/2
        "fadd.h    ft1, ft1, ft2   \n"

        // --- Compute x^3/6 ---
        // ft2 = (x^2/2) * x = x^3/2
        "fmul.h    ft2, ft2, ft0   \n"
        // ft3 = 1/6
        "fmv.h.x   ft3, %[cOneSix] \n"
        // ft2 = ft2 * (1/6) => x^3/6
        "fmul.h    ft2, ft2, ft3   \n"
        // ft1 += x^3/6
        "fadd.h    ft1, ft1, ft2   \n"

        // --- Compute x^4/24 ---
        // ft2 = (x^3/6) * x = x^4/6
        "fmul.h    ft2, ft2, ft0   \n"
        // ft3 = 1/24
        "fmv.h.x   ft3, %[cOne24]  \n"
        // ft2 = ft2 * (1/24) => x^4/24
        "fmul.h    ft2, ft2, ft3   \n"
        // ft1 += x^4/24
        "fadd.h    ft1, ft1, ft2   \n"

        // --- Move the final sum (ft1) to r ---
        "fmv.x.h   %[r], ft1       \n"

        : [r] "=r"(r)          // Output
        : [x] "r"(x),
          [c1] "r"(c1),
          [cHalf] "r"(cHalf),
          [cOneSix] "r"(cOneSix),
          [cOne24] "r"(cOne24)
        : "ft0", "ft1", "ft2", "ft3"
    );

    // Store result back to memory
    *oup = r;
}


inline void asm_fp16_sigmoid(const fp16 *inp, fp16 *out)
{
    // We'll need a few temporaries in half precision.
    fp16 x      = *inp;   // input
    fp16 negX;            // will hold -x
    fp16 eNegX;           // will hold exp(-x)
    fp16 sum;             // will hold (1 + eNegX)

    // A half-precision constant "1.0"
    static const fp16 ONE = 0x3C00;

    //----------------------------------------------------------------
    // 1) negX = -x
    //
    //   RISC-V Zfh does not always have a “fneg.h” mnemonic, but we
    //   can use fsgnjn.h  (sign-injection) to flip the sign of x:
    //----------------------------------------------------------------
    asm volatile(
        "fmv.h.x    ft0, %[x]          \n"  // ft0 = x
        "fsgnjn.h   ft0, ft0, ft0      \n"  // ft0 = -ft0
        "fmv.x.h    %[negX], ft0       \n"  // negX = -x
        : [negX] "=r" (negX)
        : [x] "r" (x)
        : "ft0"
    );

    //----------------------------------------------------------------
    // 2) eNegX = exp(negX)
    //    (Use your existing half-precision exponent routine)
    //----------------------------------------------------------------
    asm_fp16_exp(&negX, &eNegX);

    //----------------------------------------------------------------
    // 3) sum = 1 + eNegX
    //    We'll do half-precision addition via inline assembly.
    //----------------------------------------------------------------
    asm volatile(
        "fmv.h.x    ft1, %[one]       \n"  // ft1 = 1.0
        "fmv.h.x    ft2, %[eNegX]     \n"  // ft2 = eNegX
        "fadd.h     ft1, ft1, ft2     \n"  // ft1 = 1 + eNegX
        "fmv.x.h    %[sum], ft1       \n"  // sum = (1 + eNegX)
        : [sum] "=r" (sum)
        : [one] "r" (ONE),
          [eNegX] "r" (eNegX)
        : "ft1", "ft2"
    );

    //----------------------------------------------------------------
    // 4) *out = 1 / sum = 1 / (1 + e^{-x})
    //    Use your existing half-precision division function:
    //----------------------------------------------------------------
    asm_fp16_div(&ONE, &sum, out);

    // done:  *out is the sigmoid of *inp
}

/*
 * asm_fp16_compare:
 *   Returns -1 if (*a < *b), 0 if (*a == *b), +1 if (*a > *b).
 *   Purely uses half-precision RISC-V instructions for the compare.
 */
int asm_fp16_compare(const fp16 *a, const fp16 *b)
{
    // Copy inputs into local half-precision variables.
    fp16 av = *a;
    fp16 bv = *b;

    // We'll compute diff = (av - bv) in half precision.
    // Then move the bits of diff into a 16-bit integer.
    uint16_t diff_bits;

    asm volatile(
        // Move av, bv into FP registers
        "fmv.h.x    ft0, %[av]         \n"
        "fmv.h.x    ft1, %[bv]         \n"
        // diff = av - bv
        "fsub.h     ft2, ft0, ft1      \n"
        // Move bits of diff from ft2 into diff_bits
        "fmv.x.h    %[diff_bits], ft2  \n"
        : [diff_bits] "=r"(diff_bits)
        : [av] "r"(av), [bv] "r"(bv)
        : "ft0", "ft1", "ft2"
    );

    // Now interpret diff_bits as a 16-bit float:
    // Sign bit is bit 15: if set => negative => (av < bv)
    // If entire bits == 0 => exact zero => av == bv
    // Else => av > bv

    if (diff_bits == 0) {
        return 0;    // av == bv
    } else if (diff_bits & 0x8000) {
        return -1;   // negative sign => av < bv
    } else {
        return 1;    // positive => av > bv
    }
}

#define VFR_TYPE_ENCODE(funct6, m, vs2, vs1, funct3, vd, opcode)                    \
    ((funct6 << 26) | (m << 25) | (vs2 << 20) | (vs1 << 15) | (funct3 << 12) | (vd << 7) | \
     (opcode))

inline void asm_rvv_exp(uint32_t vs1_num, uint32_t vd_num){
    asm volatile(".word %0\n"::"i"(VFR_TYPE_ENCODE(0b001100, 0b1, 0b00000, vs1_num, 0b001, vd_num, 0b1010111)));
}
#endif
```

## runtime/runtime/include/flex_libfp8.h

```cpp
// Copyright 2025 ETH Zurich and University of Bologna.
//
// SPDX-License-Identifier: Apache-2.0
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//    http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

// Author: Bowen Wang, ETH Zurich

// SoftHier Generic FP8 runtime support

#ifndef _FLEX_LIBFP8_H_
#define _FLEX_LIBFP8_H_


union FloatBits {
    float f;
    uint32_t u;
};

/*
  Format transform
*/

// Decode fp8 E5M2 into float32
float fp8_e5m2_to_f32(uint8_t val) {
    if (val == 0x00) return 0.0f;

    uint8_t sign = (val >> 7) & 0x1;
    uint8_t exp  = (val >> 2) & 0x1F;  // 5-bit exponent
    uint8_t frac = val & 0x03;         // 2-bit mantissa

    // Bias = 15
    int exp_val = exp - 15;

    // mantissa = 1 + frac / 4.0
    float mant = 1.0f + (frac * 0.25f);

    // Compute 2^exp_val for small integers without math.h
    float scale = 1.0f;
    if (exp_val >= 0) {
        for (int i = 0; i < exp_val; i++) scale *= 2.0f;
    } else {
        for (int i = 0; i < -exp_val; i++) scale *= 0.5f;
    }

    float result = mant * scale;
    return sign ? -result : result;
}

// Decode fp16 (IEEE 754, E5M10) into float32
float fp16_to_f32(uint16_t val) {
    if (val == 0x0000) return 0.0f;

    uint16_t sign = (val >> 15) & 0x1;
    uint16_t exp  = (val >> 10) & 0x1F;    // 5-bit exponent
    uint16_t frac = val & 0x3FF;           // 10-bit mantissa

    if (exp == 0x1F) {
        // Handle Inf / NaN
        float inf_val = 65504.0f; // Max FP16 value
        return sign ? -inf_val : inf_val;
    }

    float mant;
    int exp_val;

    if (exp == 0) {
        // Subnormal number
        exp_val = 1 - 15;
        mant = frac / 1024.0f;
    } else {
        // Normalized number
        exp_val = exp - 15;
        mant = 1.0f + (frac / 1024.0f);
    }

    // Compute 2^exp_val without math.h
    float scale = 1.0f;
    if (exp_val >= 0) {
        for (int i = 0; i < exp_val; i++) scale *= 2.0f;
    } else {
        for (int i = 0; i < -exp_val; i++) scale *= 0.5f;
    }

    float result = mant * scale;
    return sign ? -result : result;
}

/*
  Numerical verification
*/

void spatz_verify(uint32_t avl, uint8_t* act_vec, const uint8_t* exp_vec, const float tol) {
    uint8_t exp_fp8, act_fp8;
    float exp_f32, act_f32;
    uint32_t tot_err = 0;

    for (uint32_t i = 0; i < avl; i++) {
        exp_fp8 = exp_vec[i];
        act_fp8 = act_vec[i];
        exp_f32 = fp8_e5m2_to_f32(exp_fp8);
        act_f32 = fp8_e5m2_to_f32(act_fp8);

        float err = exp_f32 - act_f32;
        // if (exp_fp8 != act_fp8) {
        //     printf("%3d | exp: 0x%02x (%.5f), act: 0x%02x (%.5f), err: %.5f\n",
        //            i, exp_fp8, exp_f32, act_fp8, act_f32, err);
        //     tot_err += 1;
        // }
        if (err > tol || err < -tol) {
            printf("%3d | exp: 0x%02x (%.5f), act: 0x%02x (%.5f), err: %.5f\n",
                   i, exp_fp8, exp_f32, act_fp8, act_f32, err);
            tot_err += 1;
        }
    }

    printf("Errors above threshold (E5M2: %.3ff): %d out of %d\n", tol, tot_err, avl);
}

// for widening instruction checks
void spatz_verify_16(uint32_t avl, uint16_t* act_vec, const uint16_t* exp_vec, const float tol) {
    uint16_t exp_fp16, act_fp16;
    float exp_f32, act_f32;
    uint32_t tot_err = 0;

    for (uint32_t i = 0; i < avl; i++) {
        exp_fp16 = exp_vec[i];
        act_fp16 = act_vec[i];
        exp_f32 = fp16_to_f32(exp_fp16);
        act_f32 = fp16_to_f32(act_fp16);

        float err = exp_f32 - act_f32;
        if (err > tol || err < -tol) {
            printf("%3d | exp: 0x%04x (%.5f), act: 0x%04x (%.5f), err: %.5f\n",
                   i, exp_fp16, exp_f32, act_fp16, act_f32, err);
            tot_err += 1;
        }
    }

    printf("Errors above threshold (E5M2: %.3ff): %d out of %d\n", tol, tot_err, avl);
}

#endif
```

## runtime/runtime/include/flex_printf.h

```cpp
///////////////////////////////////////////////////////////////////////////////
// \author (c) Marco Paland (info@paland.com)
//             2014-2018, PALANDesign Hannover, Germany
//
// \license The MIT License (MIT)
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in
// all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
// THE SOFTWARE.
//
// \brief Tiny printf, sprintf and snprintf implementation, optimized for speed
//        on embedded systems with a very limited resources. Use this instead
//        of bloated standard/newlib printf. These routines are thread safe and
//        reentrant.
//
///////////////////////////////////////////////////////////////////////////////

#ifndef _PRINTF_H_
#define _PRINTF_H_

#include <stdarg.h>
#include <stddef.h>
#include <stdbool.h>
#include <stdint.h>
#include "flex_cluster_arch.h"

// #define PRINTF_DISABLE_SUPPORT_FLOAT
// #define PRINTF_DISABLE_SUPPORT_LONG_LONG

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Output a character to a custom device like UART, used by the printf()
 * function This function is declared here only. You have to write your custom
 * implementation somewhere \param character Character to output
 */
void _putchar(char character){
    volatile uint32_t * uart_reg = (volatile uint32_t *)(ARCH_SOC_REGISTER_EOC + 16);
    * uart_reg = character;
};

/**
 * Tiny printf implementation
 * You have to implement _putchar if you use printf()
 * To avoid conflicts with the regular printf() API it is overridden by macro
 * defines and internal underscore-appended functions like printf_() are used
 * \param format A string that specifies the format of the output
 * \return The number of characters that are written into the array, not
 * counting the terminating null character
 */
#define printf printf_
int printf_(const char *format, ...);

/**
 * Tiny sprintf implementation
 * Due to security reasons (buffer overflow) YOU SHOULD CONSIDER USING
 * (V)SNPRINTF INSTEAD! \param buffer A pointer to the buffer where to store the
 * formatted string. MUST be big enough to store the output! \param format A
 * string that specifies the format of the output \return The number of
 * characters that are WRITTEN into the buffer, not counting the terminating
 * null character
 */
#define sprintf sprintf_
int sprintf_(char *buffer, const char *format, ...);

/**
 * Tiny snprintf/vsnprintf implementation
 * \param buffer A pointer to the buffer where to store the formatted string
 * \param count The maximum number of characters to store in the buffer,
 * including a terminating null character \param format A string that specifies
 * the format of the output \return The number of characters that are WRITTEN
 * into the buffer, not counting the terminating null character If the formatted
 * string is truncated the buffer size (count) is returned
 */
#define snprintf snprintf_
#define vsnprintf vsnprintf_
int snprintf_(char *buffer, size_t count, const char *format, ...);
int vsnprintf_(char *buffer, size_t count, const char *format, va_list va);

/**
 * printf with output function
 * You may use this as dynamic alternative to printf() with its fixed _putchar()
 * output \param out An output function which takes one character and an
 * argument pointer \param arg An argument pointer for user data passed to
 * output function \param format A string that specifies the format of the
 * output \return The number of characters that are sent to the output function,
 * not counting the terminating null character
 */
int fctprintf(void (*out)(char character, void *arg), void *arg,
              const char *format, ...);

#ifdef __cplusplus
}
#endif

// 'ntoa' conversion buffer size, this must be big enough to hold one converted
// numeric number including padded zeros (dynamically created on stack)
// default: 32 byte
#ifndef PRINTF_NTOA_BUFFER_SIZE
#define PRINTF_NTOA_BUFFER_SIZE 32U
#endif

// 'ftoa' conversion buffer size, this must be big enough to hold one converted
// float number including padded zeros (dynamically created on stack)
// default: 32 byte
#ifndef PRINTF_FTOA_BUFFER_SIZE
#define PRINTF_FTOA_BUFFER_SIZE 32U
#endif

// support for the floating point type (%f)
// default: activated
#ifndef PRINTF_DISABLE_SUPPORT_FLOAT
#define PRINTF_SUPPORT_FLOAT
#endif

// support for the long long types (%llu or %p)
// default: activated
#ifndef PRINTF_DISABLE_SUPPORT_LONG_LONG
#define PRINTF_SUPPORT_LONG_LONG
#endif

// support for the ptrdiff_t type (%t)
// ptrdiff_t is normally defined in <stddef.h> as long or long long type
// default: activated
#ifndef PRINTF_DISABLE_SUPPORT_PTRDIFF_T
#define PRINTF_SUPPORT_PTRDIFF_T
#endif

///////////////////////////////////////////////////////////////////////////////

// internal flag definitions
#define FLAGS_ZEROPAD (1U << 0U)
#define FLAGS_LEFT (1U << 1U)
#define FLAGS_PLUS (1U << 2U)
#define FLAGS_SPACE (1U << 3U)
#define FLAGS_HASH (1U << 4U)
#define FLAGS_UPPERCASE (1U << 5U)
#define FLAGS_CHAR (1U << 6U)
#define FLAGS_SHORT (1U << 7U)
#define FLAGS_LONG (1U << 8U)
#define FLAGS_LONG_LONG (1U << 9U)
#define FLAGS_PRECISION (1U << 10U)

// output function type
typedef void (*out_fct_type)(char character, void *buffer, size_t idx,
                             size_t maxlen);

// wrapper (used as buffer) for output function type
typedef struct {
  void (*fct)(char character, void *arg);
  void *arg;
} out_fct_wrap_type;

// internal buffer output
static inline void _out_buffer(char character, void *buffer, size_t idx,
                               size_t maxlen) {
  if (idx < maxlen) {
    ((char *)buffer)[idx] = character;
  }
}

// internal null output
static inline void _out_null(char character, void *buffer, size_t idx,
                             size_t maxlen) {
  (void)character;
  (void)buffer;
  (void)idx;
  (void)maxlen;
}

// internal _putchar wrapper
static inline void _out_char(char character, void *buffer, size_t idx,
                             size_t maxlen) {
  (void)buffer;
  (void)idx;
  (void)maxlen;
  if (character) {
    _putchar(character);
  }
}

// internal output function wrapper
static inline void _out_fct(char character, void *buffer, size_t idx,
                            size_t maxlen) {
  (void)idx;
  (void)maxlen;
  if (character) {
    // buffer is the output fct pointer
    ((out_fct_wrap_type *)buffer)
        ->fct(character, ((out_fct_wrap_type *)buffer)->arg);
  }
}

// internal secure strlen
// \return The length of the string (excluding the terminating 0) limited by
// 'maxsize'
static inline unsigned int _strnlen_s(const char *str, size_t maxsize) {
  const char *s;
  for (s = str; *s && maxsize--; ++s)
    ;
  return (unsigned int)(s - str);
}

// internal test if char is a digit (0-9)
// \return true if char is a digit
static inline bool _is_digit(char ch) { return (ch >= '0') && (ch <= '9'); }

// internal ASCII string to unsigned int conversion
static unsigned int _atoi(const char **str) {
  unsigned int i = 0U;
  while (_is_digit(**str)) {
    i = i * 10U + (unsigned int)(*((*str)++) - '0');
  }
  return i;
}

// internal itoa format
static size_t _ntoa_format(out_fct_type out, char *buffer, size_t idx,
                           size_t maxlen, char *buf, size_t len, bool negative,
                           unsigned int base, unsigned int prec,
                           unsigned int width, unsigned int flags) {
  const size_t start_idx = idx;

  // pad leading zeros
  if (!(flags & FLAGS_LEFT)) {
    if (width && (flags & FLAGS_ZEROPAD) &&
        (negative || (flags & (FLAGS_PLUS | FLAGS_SPACE)))) {
      width--;
    }
    while ((len < prec) && (len < PRINTF_NTOA_BUFFER_SIZE)) {
      buf[len++] = '0';
    }
    while ((flags & FLAGS_ZEROPAD) && (len < width) &&
           (len < PRINTF_NTOA_BUFFER_SIZE)) {
      buf[len++] = '0';
    }
  }

  // handle hash
  if (flags & FLAGS_HASH) {
    if (!(flags & FLAGS_PRECISION) && len &&
        ((len == prec) || (len == width))) {
      len--;
      if (len && (base == 16U)) {
        len--;
      }
    }
    if ((base == 16U) && !(flags & FLAGS_UPPERCASE) &&
        (len < PRINTF_NTOA_BUFFER_SIZE)) {
      buf[len++] = 'x';
    } else if ((base == 16U) && (flags & FLAGS_UPPERCASE) &&
               (len < PRINTF_NTOA_BUFFER_SIZE)) {
      buf[len++] = 'X';
    } else if ((base == 2U) && (len < PRINTF_NTOA_BUFFER_SIZE)) {
      buf[len++] = 'b';
    }
    if (len < PRINTF_NTOA_BUFFER_SIZE) {
      buf[len++] = '0';
    }
  }

  if (len < PRINTF_NTOA_BUFFER_SIZE) {
    if (negative) {
      buf[len++] = '-';
    } else if (flags & FLAGS_PLUS) {
      buf[len++] = '+'; // ignore the space if the '+' exists
    } else if (flags & FLAGS_SPACE) {
      buf[len++] = ' ';
    }
  }

  // pad spaces up to given width
  if (!(flags & FLAGS_LEFT) && !(flags & FLAGS_ZEROPAD)) {
    for (size_t i = len; i < width; i++) {
      out(' ', buffer, idx++, maxlen);
    }
  }

  // reverse string
  for (size_t i = 0U; i < len; i++) {
    out(buf[len - i - 1U], buffer, idx++, maxlen);
  }

  // append pad spaces up to given width
  if (flags & FLAGS_LEFT) {
    while (idx - start_idx < width) {
      out(' ', buffer, idx++, maxlen);
    }
  }

  return idx;
}

// internal itoa for 'long' type
static size_t _ntoa_long(out_fct_type out, char *buffer, size_t idx,
                         size_t maxlen, unsigned long value, bool negative,
                         unsigned long base, unsigned int prec,
                         unsigned int width, unsigned int flags) {
  char buf[PRINTF_NTOA_BUFFER_SIZE];
  size_t len = 0U;

  // no hash for 0 values
  if (!value) {
    flags &= ~FLAGS_HASH;
  }

  // write if precision != 0 and value is != 0
  if (!(flags & FLAGS_PRECISION) || value) {
    do {
      const char digit = (char)(value % base);
      buf[len++] = (char)(digit < 10 ? '0' + digit
                                     : (flags & FLAGS_UPPERCASE ? 'A' : 'a') +
                                           digit - 10);
      value /= base;
    } while (value && (len < PRINTF_NTOA_BUFFER_SIZE));
  }

  return _ntoa_format(out, buffer, idx, maxlen, buf, len, negative,
                      (unsigned int)base, prec, width, flags);
}

// internal itoa for 'long long' type
#if defined(PRINTF_SUPPORT_LONG_LONG)
static size_t _ntoa_long_long(out_fct_type out, char *buffer, size_t idx,
                              size_t maxlen, unsigned long long value,
                              bool negative, unsigned long long base,
                              unsigned int prec, unsigned int width,
                              unsigned int flags) {
  char buf[PRINTF_NTOA_BUFFER_SIZE];
  size_t len = 0U;

  // no hash for 0 values
  if (!value) {
    flags &= ~FLAGS_HASH;
  }

  // write if precision != 0 and value is != 0
  if (!(flags & FLAGS_PRECISION) || value) {
    do {
      const char digit = (char)(value % base);
      buf[len++] = (char)(digit < 10 ? '0' + digit
                                     : (flags & FLAGS_UPPERCASE ? 'A' : 'a') +
                                           digit - 10);
      value /= base;
    } while (value && (len < PRINTF_NTOA_BUFFER_SIZE));
  }

  return _ntoa_format(out, buffer, idx, maxlen, buf, len, negative,
                      (unsigned int)base, prec, width, flags);
}
#endif // PRINTF_SUPPORT_LONG_LONG

#if defined(PRINTF_SUPPORT_FLOAT)
static size_t _ftoa(out_fct_type out, char *buffer, size_t idx, size_t maxlen,
                    double value, unsigned int prec, unsigned int width,
                    unsigned int flags) {
  const size_t start_idx = idx;

  char buf[PRINTF_FTOA_BUFFER_SIZE];
  size_t len = 0U;
  double diff = 0.0;

  // if input is larger than thres_max, revert to exponential
  const double thres_max = (double)0x7FFFFFFF;

  // powers of 10
  static const double pow10[] = {1,         10,        100,     1000,
                                 10000,     100000,    1000000, 10000000,
                                 100000000, 1000000000};

  // test for NaN
  if (value != value) {
    out('n', buffer, idx++, maxlen);
    out('a', buffer, idx++, maxlen);
    out('n', buffer, idx++, maxlen);
    return idx;
  }

  // test for negative
  bool negative = false;
  if (value < 0) {
    negative = true;
    value = 0 - value;
  }

  // set default precision to 6, if not set explicitly
  if (!(flags & FLAGS_PRECISION)) {
    prec = 6U;
  }
  // limit precision to 9, cause a prec >= 10 can lead to overflow errors
  while ((len < PRINTF_FTOA_BUFFER_SIZE) && (prec > 9U)) {
    buf[len++] = '0';
    prec--;
  }

  int whole = (int)value;
  double tmp = (value - whole) * pow10[prec];
  unsigned long frac = (unsigned long)tmp;
  diff = tmp - frac;

  if (diff > 0.5) {
    ++frac;
    // handle rollover, e.g. case 0.99 with prec 1 is 1.0
    if (frac >= pow10[prec]) {
      frac = 0;
      ++whole;
    }
  } else if (diff < 0.5) {
  } else if ((frac == 0U) || (frac & 1U)) {
    // if halfway, round up if odd OR if last digit is 0
    ++frac;
  }

  // TBD: for very large numbers switch back to native sprintf for exponentials.
  // Anyone want to write code to replace this? Normal printf behavior is to
  // print EVERY whole number digit which can be 100s of characters overflowing
  // your buffers == bad
  if (value > thres_max) {
    return 0U;
  }

  if (prec == 0U) {
    diff = value - (double)whole;
    if ((!(diff < 0.5) || (diff > 0.5)) && (whole & 1)) {
      // exactly 0.5 and ODD, then round up
      // 1.5 -> 2, but 2.5 -> 2
      ++whole;
    }
  } else {
    unsigned int count = prec;
    // now do fractional part, as an unsigned number
    while (len < PRINTF_FTOA_BUFFER_SIZE) {
      --count;
      buf[len++] = (char)(48U + (frac % 10U));
      if (!(frac /= 10U)) {
        break;
      }
    }
    // add extra 0s
    while ((len < PRINTF_FTOA_BUFFER_SIZE) && (count-- > 0U)) {
      buf[len++] = '0';
    }
    if (len < PRINTF_FTOA_BUFFER_SIZE) {
      // add decimal
      buf[len++] = '.';
    }
  }

  // do whole part, number is reversed
  while (len < PRINTF_FTOA_BUFFER_SIZE) {
    buf[len++] = (char)(48 + (whole % 10));
    if (!(whole /= 10)) {
      break;
    }
  }

  // pad leading zeros
  if (!(flags & FLAGS_LEFT) && (flags & FLAGS_ZEROPAD)) {
    if (width && (negative || (flags & (FLAGS_PLUS | FLAGS_SPACE)))) {
      width--;
    }
    while ((len < width) && (len < PRINTF_FTOA_BUFFER_SIZE)) {
      buf[len++] = '0';
    }
  }

  if (len < PRINTF_FTOA_BUFFER_SIZE) {
    if (negative) {
      buf[len++] = '-';
    } else if (flags & FLAGS_PLUS) {
      buf[len++] = '+'; // ignore the space if the '+' exists
    } else if (flags & FLAGS_SPACE) {
      buf[len++] = ' ';
    }
  }

  // pad spaces up to given width
  if (!(flags & FLAGS_LEFT) && !(flags & FLAGS_ZEROPAD)) {
    for (size_t i = len; i < width; i++) {
      out(' ', buffer, idx++, maxlen);
    }
  }

  // reverse string
  for (size_t i = 0U; i < len; i++) {
    out(buf[len - i - 1U], buffer, idx++, maxlen);
  }

  // append pad spaces up to given width
  if (flags & FLAGS_LEFT) {
    while (idx - start_idx < width) {
      out(' ', buffer, idx++, maxlen);
    }
  }

  return idx;
}
#endif // PRINTF_SUPPORT_FLOAT

// internal vsnprintf
static int _vsnprintf(out_fct_type out, char *buffer, const size_t maxlen,
                      const char *format, va_list va) {
  unsigned int flags, width, precision, n;
  size_t idx = 0U;

  if (!buffer) {
    // use null output function
    out = _out_null;
  }

  while (*format) {
    // format specifier?  %[flags][width][.precision][length]
    if (*format != '%') {
      // no
      out(*format, buffer, idx++, maxlen);
      format++;
      continue;
    } else {
      // yes, evaluate it
      format++;
    }

    // evaluate flags
    flags = 0U;
    do {
      switch (*format) {
      case '0':
        flags |= FLAGS_ZEROPAD;
        format++;
        n = 1U;
        break;
      case '-':
        flags |= FLAGS_LEFT;
        format++;
        n = 1U;
        break;
      case '+':
        flags |= FLAGS_PLUS;
        format++;
        n = 1U;
        break;
      case ' ':
        flags |= FLAGS_SPACE;
        format++;
        n = 1U;
        break;
      case '#':
        flags |= FLAGS_HASH;
        format++;
        n = 1U;
        break;
      default:
        n = 0U;
        break;
      }
    } while (n);

    // evaluate width field
    width = 0U;
    if (_is_digit(*format)) {
      width = _atoi(&format);
    } else if (*format == '*') {
      const int w = va_arg(va, int);
      if (w < 0) {
        flags |= FLAGS_LEFT; // reverse padding
        width = (unsigned int)-w;
      } else {
        width = (unsigned int)w;
      }
      format++;
    }

    // evaluate precision field
    precision = 0U;
    if (*format == '.') {
      flags |= FLAGS_PRECISION;
      format++;
      if (_is_digit(*format)) {
        precision = _atoi(&format);
      } else if (*format == '*') {
        const int prec = (int)va_arg(va, int);
        precision = prec > 0 ? (unsigned int)prec : 0U;
        format++;
      }
    }

    // evaluate length field
    switch (*format) {
    case 'l':
      flags |= FLAGS_LONG;
      format++;
      if (*format == 'l') {
        flags |= FLAGS_LONG_LONG;
        format++;
      }
      break;
    case 'h':
      flags |= FLAGS_SHORT;
      format++;
      if (*format == 'h') {
        flags |= FLAGS_CHAR;
        format++;
      }
      break;
#if defined(PRINTF_SUPPORT_PTRDIFF_T)
    case 't':
      flags |=
          (sizeof(ptrdiff_t) == sizeof(long) ? FLAGS_LONG : FLAGS_LONG_LONG);
      format++;
      break;
#endif
    case 'j':
      flags |=
          (sizeof(intmax_t) == sizeof(long) ? FLAGS_LONG : FLAGS_LONG_LONG);
      format++;
      break;
    case 'z':
      flags |= (sizeof(size_t) == sizeof(long) ? FLAGS_LONG : FLAGS_LONG_LONG);
      format++;
      break;
    default:
      break;
    }

    // evaluate specifier
    switch (*format) {
    case 'd':
    case 'i':
    case 'u':
    case 'x':
    case 'X':
    case 'o':
    case 'b': {
      // set the base
      unsigned int base;
      if (*format == 'x' || *format == 'X') {
        base = 16U;
      } else if (*format == 'o') {
        base = 8U;
      } else if (*format == 'b') {
        base = 2U;
      } else {
        base = 10U;
        flags &= ~FLAGS_HASH; // no hash for dec format
      }
      // uppercase
      if (*format == 'X') {
        flags |= FLAGS_UPPERCASE;
      }

      // no plus or space flag for u, x, X, o, b
      if ((*format != 'i') && (*format != 'd')) {
        flags &= ~(FLAGS_PLUS | FLAGS_SPACE);
      }

      // ignore '0' flag when precision is given
      if (flags & FLAGS_PRECISION) {
        flags &= ~FLAGS_ZEROPAD;
      }

      // convert the integer
      if ((*format == 'i') || (*format == 'd')) {
        // signed
        if (flags & FLAGS_LONG_LONG) {
#if defined(PRINTF_SUPPORT_LONG_LONG)
          const long long value = va_arg(va, long long);
          idx = _ntoa_long_long(
              out, buffer, idx, maxlen,
              (unsigned long long)(value > 0 ? value : 0 - value), value < 0,
              base, precision, width, flags);
#endif
        } else if (flags & FLAGS_LONG) {
          const long value = va_arg(va, long);
          idx = _ntoa_long(out, buffer, idx, maxlen,
                           (unsigned long)(value > 0 ? value : 0 - value),
                           value < 0, base, precision, width, flags);
        } else {
          const int value = (flags & FLAGS_CHAR)    ? (char)va_arg(va, int)
                            : (flags & FLAGS_SHORT) ? (short int)va_arg(va, int)
                                                    : va_arg(va, int);
          idx = _ntoa_long(out, buffer, idx, maxlen,
                           (unsigned int)(value > 0 ? value : 0 - value),
                           value < 0, base, precision, width, flags);
        }
      } else {
        // unsigned
        if (flags & FLAGS_LONG_LONG) {
#if defined(PRINTF_SUPPORT_LONG_LONG)
          idx = _ntoa_long_long(out, buffer, idx, maxlen,
                                va_arg(va, unsigned long long), false, base,
                                precision, width, flags);
#endif
        } else if (flags & FLAGS_LONG) {
          idx = _ntoa_long(out, buffer, idx, maxlen, va_arg(va, unsigned long),
                           false, base, precision, width, flags);
        } else {
          const unsigned int value =
              (flags & FLAGS_CHAR) ? (unsigned char)va_arg(va, unsigned int)
              : (flags & FLAGS_SHORT)
                  ? (unsigned short int)va_arg(va, unsigned int)
                  : va_arg(va, unsigned int);
          idx = _ntoa_long(out, buffer, idx, maxlen, value, false, base,
                           precision, width, flags);
        }
      }
      format++;
      break;
    }
#if defined(PRINTF_SUPPORT_FLOAT)
    case 'f':
    case 'F':
      idx = _ftoa(out, buffer, idx, maxlen, va_arg(va, double), precision,
                  width, flags);
      format++;
      break;
#endif // PRINTF_SUPPORT_FLOAT
    case 'c': {
      unsigned int l = 1U;
      // pre padding
      if (!(flags & FLAGS_LEFT)) {
        while (l++ < width) {
          out(' ', buffer, idx++, maxlen);
        }
      }
      // char output
      out((char)va_arg(va, int), buffer, idx++, maxlen);
      // post padding
      if (flags & FLAGS_LEFT) {
        while (l++ < width) {
          out(' ', buffer, idx++, maxlen);
        }
      }
      format++;
      break;
    }

    case 's': {
      const char *p = va_arg(va, char *);
      unsigned int l = _strnlen_s(p, precision ? precision : (size_t)-1);
      // pre padding
      if (flags & FLAGS_PRECISION) {
        l = (l < precision ? l : precision);
      }
      if (!(flags & FLAGS_LEFT)) {
        while (l++ < width) {
          out(' ', buffer, idx++, maxlen);
        }
      }
      // string output
      while ((*p != 0) && (!(flags & FLAGS_PRECISION) || precision--)) {
        out(*(p++), buffer, idx++, maxlen);
      }
      // post padding
      if (flags & FLAGS_LEFT) {
        while (l++ < width) {
          out(' ', buffer, idx++, maxlen);
        }
      }
      format++;
      break;
    }

    case 'p': {
      width = sizeof(void *) * 2U;
      flags |= FLAGS_ZEROPAD | FLAGS_UPPERCASE;
#if defined(PRINTF_SUPPORT_LONG_LONG)
      const bool is_ll = sizeof(uintptr_t) == sizeof(long long);
      if (is_ll) {
        idx = _ntoa_long_long(out, buffer, idx, maxlen,
                              (uintptr_t)va_arg(va, void *), false, 16U,
                              precision, width, flags);
      } else {
#endif
        idx = _ntoa_long(out, buffer, idx, maxlen,
                         (unsigned long)((uintptr_t)va_arg(va, void *)), false,
                         16U, precision, width, flags);
#if defined(PRINTF_SUPPORT_LONG_LONG)
      }
#endif
      format++;
      break;
    }

    case '%':
      out('%', buffer, idx++, maxlen);
      format++;
      break;

    default:
      out(*format, buffer, idx++, maxlen);
      format++;
      break;
    }
  }

  // termination
  out((char)0, buffer, idx < maxlen ? idx : maxlen - 1U, maxlen);

  // return written chars without terminating \0
  return (int)idx;
}

///////////////////////////////////////////////////////////////////////////////

int printf_(const char *format, ...) {
  va_list va;
  va_start(va, format);
  char buffer[1];
  const int ret = _vsnprintf(_out_char, buffer, (size_t)-1, format, va);
  va_end(va);
  return ret;
}

int sprintf_(char *buffer, const char *format, ...) {
  va_list va;
  va_start(va, format);
  const int ret = _vsnprintf(_out_buffer, buffer, (size_t)-1, format, va);
  va_end(va);
  return ret;
}

int snprintf_(char *buffer, size_t count, const char *format, ...) {
  va_list va;
  va_start(va, format);
  const int ret = _vsnprintf(_out_buffer, buffer, count, format, va);
  va_end(va);
  return ret;
}

int vsnprintf_(char *buffer, size_t count, const char *format, va_list va) {
  return _vsnprintf(_out_buffer, buffer, count, format, va);
}

int fctprintf(void (*out)(char character, void *arg), void *arg,
              const char *format, ...) {
  va_list va;
  va_start(va, format);
  const out_fct_wrap_type out_fct_wrap = {out, arg};
  const int ret = _vsnprintf(_out_fct, (char *)(uintptr_t)&out_fct_wrap,
                             (size_t)-1, format, va);
  va_end(va);
  return ret;
}


#endif // _PRINTF_H_
```

## runtime/runtime/include/flex_redmule.h

```cpp
//
// Copyright (C) 2026 ETH Zurich and University of Bologna
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// Author: Chi Zhang <chizhang@ethz.ch>

#ifndef _FLEX_REDMULE_H_
#define _FLEX_REDMULE_H_
#include "flex_cluster_arch.h"

typedef enum {
    REDMULE_NONE_16,
    REDMULE_UINT_16,
    REDMULE_INT_16,
    REDMULE_FP_16,
    REDMULE_UINT_8,
    REDMULE_INT_8,
    REDMULE_FP_8
} redmule_compute_format_t;


void flex_redmule_config(uint16_t m_size, uint16_t n_size, uint16_t k_size){
    uint32_t cfg_reg0 = ((k_size << 16) | (m_size << 0));
    uint32_t cfg_reg1 = (n_size << 0);

    asm volatile ("addi t3, %0, 0" :: "r"(cfg_reg0):"t3");
    asm volatile ("addi t4, %0, 0" :: "r"(cfg_reg1):"t4");

    /* mcnfig instruction */
    // asm volatile(
    //      ".word (0x0       << 25) | \     /* Empty         */
    //             (0b11101   << 20) | \     /* Rs2 (t4 here) */
    //             (0b11100   << 15) | \     /* Rs1 (t3 here) */
    //             (0x00      <<  7) | \     /* Empty         */
    //             (0b0001010 <<  0)   \n"); /* OpCode        */

    asm volatile(
         ".word (0x0       << 25) | \
                (0b11101   << 20) | \
                (0b11100   << 15) | \
                (0x00      <<  7) | \
                (0b0001010 <<  0)   \n");
}

void flex_redmule_trigger(uint32_t x_addr, uint32_t w_addr, uint32_t y_addr, redmule_compute_format_t format){

    asm volatile ("addi t0, %0, 0" :: "r"(x_addr):"t0");
    asm volatile ("addi t1, %0, 0" :: "r"(w_addr):"t1");
    asm volatile ("addi t2, %0, 0" :: "r"(y_addr):"t2");

    /* arith instruction */
    // sm volatile(
    //     ".word (0b00111   << 27) | \     /* Rs3 (t2 here)                */
    //            (0b00      << 25) | \     /* Empty                        */
    //            (0b00110   << 20) | \     /* Rs2 (t1 here)                */
    //            (0b00101   << 15) | \     /* Rs1 (t0 here)                */
    //            (0b0       << 14) | \     /* Custom format enable/disable */
    //            (0b0       << 13) | \     /* Widening enable/disable      */
    //            (0b001     << 10) | \     /* Operation selection          */
    //            (0b001     <<  7) | \     /* Data format                  */
    //            (0b0101010 <<  0)   \n"); /* OpCode                       */

    switch (format) {
        case REDMULE_NONE_16:
            asm volatile(
                 ".word (0b00111   << 27) | \
                        (0b00      << 25) | \
                        (0b00110   << 20) | \
                        (0b00101   << 15) | \
                        (0b0       << 14) | \
                        (0b0       << 13) | \
                        (0b000     << 10) | \
                        (0b000     <<  7) | \
                        (0b0101010 <<  0)   \n");
            break;
        case REDMULE_UINT_16:
            asm volatile(
                 ".word (0b00111   << 27) | \
                        (0b00      << 25) | \
                        (0b00110   << 20) | \
                        (0b00101   << 15) | \
                        (0b0       << 14) | \
                        (0b0       << 13) | \
                        (0b000     << 10) | \
                        (0b001     <<  7) | \
                        (0b0101010 <<  0)   \n");
            break;
        case REDMULE_INT_16:
            asm volatile(
                 ".word (0b00111   << 27) | \
                        (0b00      << 25) | \
                        (0b00110   << 20) | \
                        (0b00101   << 15) | \
                        (0b0       << 14) | \
                        (0b0       << 13) | \
                        (0b000     << 10) | \
                        (0b010     <<  7) | \
                        (0b0101010 <<  0)   \n");
            break;
        case REDMULE_FP_16:
            asm volatile(
                 ".word (0b00111   << 27) | \
                        (0b00      << 25) | \
                        (0b00110   << 20) | \
                        (0b00101   << 15) | \
                        (0b0       << 14) | \
                        (0b0       << 13) | \
                        (0b000     << 10) | \
                        (0b011     <<  7) | \
                        (0b0101010 <<  0)   \n");
            break;
        case REDMULE_UINT_8:
            asm volatile(
                 ".word (0b00111   << 27) | \
                        (0b00      << 25) | \
                        (0b00110   << 20) | \
                        (0b00101   << 15) | \
                        (0b0       << 14) | \
                        (0b0       << 13) | \
                        (0b000     << 10) | \
                        (0b101     <<  7) | \
                        (0b0101010 <<  0)   \n");
            break;
        case REDMULE_INT_8:
            asm volatile(
                 ".word (0b00111   << 27) | \
                        (0b00      << 25) | \
                        (0b00110   << 20) | \
                        (0b00101   << 15) | \
                        (0b0       << 14) | \
                        (0b0       << 13) | \
                        (0b000     << 10) | \
                        (0b110     <<  7) | \
                        (0b0101010 <<  0)   \n");
            break;
        case REDMULE_FP_8:
            asm volatile(
                 ".word (0b00111   << 27) | \
                        (0b00      << 25) | \
                        (0b00110   << 20) | \
                        (0b00101   << 15) | \
                        (0b0       << 14) | \
                        (0b0       << 13) | \
                        (0b000     << 10) | \
                        (0b111     <<  7) | \
                        (0b0101010 <<  0)   \n");
            break;
    }
}

uint32_t flex_redmule_wait(){
    volatile uint32_t * redmule_reg  = (volatile uint32_t *) (ARCH_REDMULE_REG_BASE + 40);
    return (*redmule_reg);
}

#endif
```

## runtime/runtime/include/flex_runtime.h

```cpp
//
// Copyright (C) 2026 ETH Zurich and University of Bologna
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// Author: Chi Zhang <chizhang@ethz.ch>

#ifndef _FLEX_RUNTIME_H_
#define _FLEX_RUNTIME_H_
#include <stdint.h>
#include "flex_cluster_arch.h"
#include "flex_alloc.h"

#define ARCH_NUM_CLUSTER            (ARCH_NUM_CLUSTER_X*ARCH_NUM_CLUSTER_Y)
#define ARCH_SYNC_SIZE              (ARCH_SYNC_INTERLEAVE + ARCH_SYNC_SPECIAL_MEM)
#define cluster_index(x,y)          ((y)*ARCH_NUM_CLUSTER_X+(x))
#define local(offset)               (ARCH_CLUSTER_TCDM_BASE+offset)
#define zomem(offset)               (ARCH_CLUSTER_ZOMEM_BASE+offset)
#define remote_cid(cid,offset)      (ARCH_CLUSTER_TCDM_REMOTE+cid*ARCH_CLUSTER_TCDM_SIZE+offset)
#define remote_xy(x,y,offset)       (ARCH_CLUSTER_TCDM_REMOTE+cluster_index(x,y)*ARCH_CLUSTER_TCDM_SIZE+offset)
#define remote_pos(pos,offset)      (ARCH_CLUSTER_TCDM_REMOTE+cluster_index(pos.x,pos.y)*ARCH_CLUSTER_TCDM_SIZE+offset)
#define hbm_addr(offset)            ((uint64_t)ARCH_HBM_START_BASE+(uint64_t)offset)
#define hbm_west(nid,offset)        ((uint64_t)ARCH_HBM_START_BASE+((uint64_t)nid)*(uint64_t)ARCH_HBM_NODE_ADDR_SPACE+(uint64_t)offset)
#define hbm_north(nid,offset)       ((uint64_t)ARCH_HBM_START_BASE+((uint64_t)nid)*(uint64_t)ARCH_HBM_NODE_ADDR_SPACE+(uint64_t)ARCH_HBM_NODE_ADDR_SPACE*(uint64_t)ARCH_NUM_CLUSTER_Y+(uint64_t)offset)
#define hbm_east(nid,offset)        ((uint64_t)ARCH_HBM_START_BASE+((uint64_t)nid)*(uint64_t)ARCH_HBM_NODE_ADDR_SPACE+(uint64_t)ARCH_HBM_NODE_ADDR_SPACE*((uint64_t)ARCH_NUM_CLUSTER_Y+(uint64_t)ARCH_NUM_CLUSTER_X)+(uint64_t)offset)
#define hbm_south(nid,offset)       ((uint64_t)ARCH_HBM_START_BASE+((uint64_t)nid)*(uint64_t)ARCH_HBM_NODE_ADDR_SPACE+(uint64_t)ARCH_HBM_NODE_ADDR_SPACE*2*(uint64_t)ARCH_NUM_CLUSTER_Y+(uint64_t)ARCH_HBM_NODE_ADDR_SPACE*ARCH_NUM_CLUSTER_X+(uint64_t)offset)
#define is_hbm_region(addr)         (addr >= ARCH_HBM_START_BASE)
#define is_power_of_two(value)      (((value) & ((value) - 1)) == 0)

/*******************
* Cluster Position *
*******************/

typedef struct FlexPosition
{
    uint32_t x;
    uint32_t y;
}FlexPosition;

FlexPosition get_pos(uint32_t cluster_id) {
    FlexPosition pos;
    pos.x = cluster_id % ARCH_NUM_CLUSTER_X;
    pos.y = cluster_id / ARCH_NUM_CLUSTER_X;
    return pos;
}

//Methods
FlexPosition right_pos(FlexPosition pos) {
    uint32_t new_x = (pos.x + 1) % ARCH_NUM_CLUSTER_X;
    uint32_t new_y = pos.y;
    FlexPosition new_pos;
    new_pos.x = new_x;
    new_pos.y = new_y;
    return new_pos;
}

FlexPosition left_pos(FlexPosition pos) {
    uint32_t new_x = (pos.x + ARCH_NUM_CLUSTER_X - 1) % ARCH_NUM_CLUSTER_X;
    uint32_t new_y = pos.y;
    FlexPosition new_pos;
    new_pos.x = new_x;
    new_pos.y = new_y;
    return new_pos;
}

FlexPosition top_pos(FlexPosition pos) {
    uint32_t new_x = pos.x;
    uint32_t new_y = (pos.y + 1) % ARCH_NUM_CLUSTER_Y;
    FlexPosition new_pos;
    new_pos.x = new_x;
    new_pos.y = new_y;
    return new_pos;
}

FlexPosition bottom_pos(FlexPosition pos) {
    uint32_t new_x = pos.x;
    uint32_t new_y = (pos.y + ARCH_NUM_CLUSTER_Y - 1) % ARCH_NUM_CLUSTER_Y;
    FlexPosition new_pos;
    new_pos.x = new_x;
    new_pos.y = new_y;
    return new_pos;
}

uint32_t flex_get_cluster_id(){
    volatile uint32_t * cluster_reg      = (volatile uint32_t *) ARCH_CLUSTER_REG_BASE;
    return *cluster_reg;
}

/*******************
*  Core Position   *
*******************/

uint32_t flex_get_core_id(){
    uint32_t hartid;
    asm volatile("csrr %0, mhartid" : "=r"(hartid));
    return hartid;
}

uint32_t flex_is_dm_core(){
    uint32_t hartid;
    asm volatile("csrr %0, mhartid" : "=r"(hartid));
    return (hartid == ARCH_NUM_CORE_PER_CLUSTER-1);
}

uint32_t flex_is_first_core(){
    uint32_t hartid;
    asm volatile("csrr %0, mhartid" : "=r"(hartid));
    return (hartid == 0);
}

/********************
*  Data Allocation  *
********************/

// Back-adaptation for other config fills to pass CI
#ifndef ARCH_CLUSTER_HEAP_BASE
#define ARCH_CLUSTER_HEAP_BASE (0x00000000)
#define ARCH_CLUSTER_HEAP_END  (0x00000000)
#endif

/*
 * Desc: cluster-private heap allocator initialization
 */

extern char __l1_heap_start[];
extern char __hbm_heap_start[];

static inline void flex_alloc_init(){
    uint32_t CID = flex_get_cluster_id();
    // volatile uint32_t * heap_start      = (volatile uint32_t *) (ARCH_CLUSTER_HEAP_BASE + 0x1000);
    volatile uint32_t * heap_start      = (volatile uint32_t *) __l1_heap_start;
    volatile uint32_t * heap_end        = (volatile uint32_t *) ARCH_CLUSTER_HEAP_END;
    volatile uint32_t   heap_size       = (uint32_t)heap_end - (uint32_t)heap_start;
    if (flex_is_first_core()){
        flex_cluster_alloc_init(flex_get_allocator_l1(), (void *)heap_start, heap_size);
    }

    // HBM allocator
    uint32_t hbm_nodes = 4; // bowwang: hardcoded for now
    volatile uint32_t * hbm_heap_start      = (volatile uint32_t *) __hbm_heap_start;
    volatile uint32_t * hbm_heap_end        = (volatile uint32_t *) (ARCH_HBM_START_BASE + (ARCH_HBM_NODE_ADDR_SPACE * hbm_nodes));
    volatile uint32_t   hbm_heap_size       = (uint32_t)hbm_heap_end - (uint32_t)hbm_heap_start;
    if (flex_is_first_core()){
        flex_cluster_alloc_init(flex_get_allocator_hbm(), (void *)hbm_heap_start, hbm_heap_size);
    }

    // allocation init summary
    if (CID==0 && flex_is_first_core()){
        printf("[Alloc] >>> L1  allocator:    0x%p\n", &alloc_l1);
        printf("[Alloc] >>> L1  first block:  0x%p\n", (&alloc_l1)->first_block);
        printf("[Alloc] >>> L1  heap start:   0x%p, size: 0x%x\n\n", heap_start, heap_size);
        printf("[Alloc] >>> HBM allocator:    0x%p\n", &alloc_hbm);
        printf("[Alloc] >>> HBM first block:  0x%p\n", (&alloc_hbm)->first_block);
        printf("[Alloc] >>> HBM heap start:   0x%p, size: 0x%x\n\n", hbm_heap_start, hbm_heap_size);
    }

    return;
}


/*******************
*  Global Barrier  *
*******************/

uint32_t flex_get_enable_value(){
    volatile uint32_t * amo_reg      = (volatile uint32_t *) (ARCH_CLUSTER_REG_BASE+4);
    return *amo_reg;
}

uint32_t flex_get_disable_value(){
    volatile uint32_t * amo_reg      = (volatile uint32_t *) (ARCH_CLUSTER_REG_BASE+24);
    return *amo_reg;
}

uint32_t flex_get_barrier_num_cluster(){
    volatile uint32_t * info_reg      = (volatile uint32_t *) (ARCH_CLUSTER_REG_BASE+8);
    return *info_reg;
}

uint32_t flex_get_barrier_num_cluster_x(){
    volatile uint32_t * info_reg      = (volatile uint32_t *) (ARCH_CLUSTER_REG_BASE+12);
    return *info_reg;
}

uint32_t flex_get_barrier_num_cluster_y(){
    volatile uint32_t * info_reg      = (volatile uint32_t *) (ARCH_CLUSTER_REG_BASE+16);
    return *info_reg;
}

void flex_annotate_barrier(uint32_t type){
    volatile uint32_t * info_reg      = (volatile uint32_t *) (ARCH_CLUSTER_REG_BASE+20);
    *info_reg = type;
}

void flex_reset_barrier(uint32_t* barrier){
    *barrier = flex_get_disable_value();
}

uint32_t flex_amo_fetch_add(uint32_t* barrier){
    return __atomic_fetch_add(barrier, flex_get_enable_value(), __ATOMIC_RELAXED);
}

void flex_intra_cluster_sync(){
    asm volatile("csrr x0, 0x7C2" ::: "memory");
}

inline void flex_wakeup_clusters(uint8_t row_mask, uint8_t col_mask)
{
    volatile uint32_t * wakeup_reg   = (volatile uint32_t *) (ARCH_CLUSTER_REG_BASE+28);
    uint32_t value = (((uint32_t)col_mask) << 16) | row_mask;
    *wakeup_reg = value;
}

inline void flex_wakeup_all_clusters()
{
    volatile uint32_t * wakeup_reg   = (volatile uint32_t *) (ARCH_CLUSTER_REG_BASE+28);
    uint32_t value = flex_get_disable_value();
    *wakeup_reg = value;
}

void flex_barrier_init(){
    volatile uint32_t * barrier      = (volatile uint32_t *) ARCH_SYNC_BASE;
    volatile uint32_t * cluster_reg  = (volatile uint32_t *) ARCH_CLUSTER_REG_BASE;

    if (flex_is_dm_core()){
        if (flex_get_cluster_id() == 0)
        {
            // __atomic_store_n(barrier, 0, __ATOMIC_RELAXED);
            flex_reset_barrier(barrier);
            flex_wakeup_all_clusters();
        }
        *cluster_reg = flex_get_enable_value();
    }

    flex_intra_cluster_sync();
}

void flex_global_barrier(){
    volatile uint32_t * barrier      = (volatile uint32_t *) ARCH_SYNC_BASE;
    volatile uint32_t * cluster_reg  = (volatile uint32_t *) ARCH_CLUSTER_REG_BASE;

    flex_intra_cluster_sync();

    if (flex_is_dm_core()){
        flex_annotate_barrier(0);
        if ((flex_get_barrier_num_cluster() - flex_get_enable_value()) == flex_amo_fetch_add(barrier)) {
            flex_reset_barrier(barrier);
            flex_wakeup_all_clusters();
        }
        *cluster_reg = flex_get_enable_value();
        flex_annotate_barrier(0);
    }

    flex_intra_cluster_sync();
}

void flex_global_barrier_polling(){
    volatile uint32_t * barrier      = (volatile uint32_t *) ARCH_SYNC_BASE;
    volatile uint32_t * barrier_iter = (volatile uint32_t *) (ARCH_SYNC_BASE + 4);

    flex_intra_cluster_sync();

    if (flex_is_dm_core()){
        flex_annotate_barrier(0);
        // Remember previous iteration
        uint32_t prev_barrier_iteration = *barrier_iter;

        if ((flex_get_barrier_num_cluster() - flex_get_enable_value()) == flex_amo_fetch_add(barrier)) {
            flex_reset_barrier(barrier);
            flex_amo_fetch_add(barrier_iter);
        } else {
            while((*barrier_iter) == prev_barrier_iteration);
        }
        flex_annotate_barrier(0);
    }

    flex_intra_cluster_sync();
}

void flex_barrier_xy_init(){
    FlexPosition        pos          = get_pos(flex_get_cluster_id());
    uint32_t            pos_x_middel = (ARCH_NUM_CLUSTER_X)/2;
    uint32_t            pos_y_middel = (ARCH_NUM_CLUSTER_Y)/2;
    volatile uint32_t * barrier_y    = (volatile uint32_t *) (ARCH_SYNC_BASE+(cluster_index(pos_x_middel,pos_y_middel)*ARCH_SYNC_SIZE)+16);
    volatile uint32_t * cluster_reg  = (volatile uint32_t *) ARCH_CLUSTER_REG_BASE;

    if (flex_is_dm_core()){
        if (flex_get_cluster_id() == 0)
        {
            flex_reset_barrier(barrier_y);
            for (int i = 0; i < ARCH_NUM_CLUSTER_Y; ++i)
            {
                volatile uint32_t * barrier_x = (volatile uint32_t *) (ARCH_SYNC_BASE+(cluster_index(pos_x_middel,i)*ARCH_SYNC_SIZE)+8);
                flex_reset_barrier(barrier_x);
            }
            flex_wakeup_all_clusters();
        }
        *cluster_reg = flex_get_enable_value();
    }

    flex_intra_cluster_sync();
}

void flex_global_barrier_xy(){

    flex_intra_cluster_sync();

    if (flex_is_dm_core()){
        flex_annotate_barrier(0);

        FlexPosition        pos          = get_pos(flex_get_cluster_id());
        uint32_t            pos_x_middel = (flex_get_barrier_num_cluster_x())/2;
        uint32_t            pos_y_middel = (flex_get_barrier_num_cluster_y())/2;
        volatile uint32_t * barrier_x    = (volatile uint32_t *) (ARCH_SYNC_BASE+(cluster_index(pos_x_middel,pos.y       )*ARCH_SYNC_SIZE)+8);
        volatile uint32_t * barrier_y    = (volatile uint32_t *) (ARCH_SYNC_BASE+(cluster_index(pos_x_middel,pos_y_middel)*ARCH_SYNC_SIZE)+16);
        volatile uint32_t * cluster_reg  = (volatile uint32_t *) ARCH_CLUSTER_REG_BASE;

        //First Barrier X
        if ((flex_get_barrier_num_cluster_x() - flex_get_enable_value()) == flex_amo_fetch_add(barrier_x)) {
            flex_reset_barrier(barrier_x);

            //For cluster synced X, then sync Y
            if ((flex_get_barrier_num_cluster_y() - flex_get_enable_value()) == flex_amo_fetch_add(barrier_y))
            {
                flex_reset_barrier(barrier_y);
                flex_wakeup_all_clusters();
            }
        }
        *cluster_reg = flex_get_enable_value();

        flex_annotate_barrier(0);
    }

    flex_intra_cluster_sync();
}

void flex_global_barrier_xy_polling(){

    flex_intra_cluster_sync();

    if (flex_is_dm_core()){
        flex_annotate_barrier(0);

        FlexPosition        pos          = get_pos(flex_get_cluster_id());
        uint32_t            pos_x_middel = (flex_get_barrier_num_cluster_x())/2;
        uint32_t            pos_y_middel = (flex_get_barrier_num_cluster_y())/2;
        volatile uint32_t * barrier_x    = (volatile uint32_t *) (ARCH_SYNC_BASE+(cluster_index(pos_x_middel,pos.y       )*ARCH_SYNC_SIZE)+8);
        volatile uint32_t * barrier_ix   = (volatile uint32_t *) (ARCH_SYNC_BASE+(cluster_index(pos_x_middel,pos.y       )*ARCH_SYNC_SIZE)+12);
        volatile uint32_t * barrier_y    = (volatile uint32_t *) (ARCH_SYNC_BASE+(cluster_index(pos_x_middel,pos_y_middel)*ARCH_SYNC_SIZE)+16);
        volatile uint32_t * barrier_iy   = (volatile uint32_t *) (ARCH_SYNC_BASE+(cluster_index(pos_x_middel,pos_y_middel)*ARCH_SYNC_SIZE)+20);

        // Remember previous iteration
        uint32_t prev_barrier_iter_x     = *barrier_ix;
        uint32_t prev_barrier_iter_y     = *barrier_iy;

        //First Barrier X
        if ((flex_get_barrier_num_cluster_x() - flex_get_enable_value()) == flex_amo_fetch_add(barrier_x)) {
            flex_reset_barrier(barrier_x);

            //For cluster synced X, then sync Y
            if ((flex_get_barrier_num_cluster_y() - flex_get_enable_value()) == flex_amo_fetch_add(barrier_y))
            {
                flex_reset_barrier(barrier_y);
                flex_amo_fetch_add(barrier_iy);
            } else {
                while((*barrier_iy) == prev_barrier_iter_y);
            }

            flex_amo_fetch_add(barrier_ix);
        } else {
            while((*barrier_ix) == prev_barrier_iter_x);
        }

        flex_annotate_barrier(0);
    }

    flex_intra_cluster_sync();
}

/*******************
*        EoC       *
*******************/

void flex_eoc(uint32_t val){
    volatile uint32_t * eoc_reg = (volatile uint32_t *) ARCH_SOC_REGISTER_EOC;
    *eoc_reg = val;
}

/*******************
*   Perf Counter   *
*******************/

void flex_timer_start(){
    volatile uint32_t * start_reg    = (volatile uint32_t *) (ARCH_SOC_REGISTER_EOC + 8);
    *start_reg = flex_get_enable_value();
}

void flex_timer_end(){
    volatile uint32_t * end_reg = (volatile uint32_t *) (ARCH_SOC_REGISTER_EOC + 12);
    *end_reg = flex_get_enable_value();
}

/*******************
*      Logging     *
*******************/

void flex_log_char(char c){
    uint32_t data = (uint32_t) c;
    volatile uint32_t * log_reg = (volatile uint32_t *)(ARCH_SOC_REGISTER_EOC + 16);
    *log_reg = data;
}

void flex_print(char * str){
    for (int i = 0; str[i] != '\0'; i++) {
        flex_log_char(str[i]);
    }
}

void flex_print_int(uint32_t data){
    volatile uint32_t * log_reg = (volatile uint32_t *)(ARCH_SOC_REGISTER_EOC + 20);
    *log_reg = data;
}

/************************
*      Stop at Time     *
************************/

void flex_sat(uint32_t val){
    volatile uint32_t * sat_reg = (volatile uint32_t *) (ARCH_SOC_REGISTER_EOC + 40);
    *sat_reg = val;
}

#endif
```

## runtime/runtime/include/flex_transpose_engine.h

```cpp
//
// Copyright (C) 2026 ETH Zurich and University of Bologna
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// Author: Chi Zhang <chizhang@ethz.ch>

#ifndef _FLEX_TRANSPOSE_ENGINE_H_
#define _FLEX_TRANSPOSE_ENGINE_H_

#include "flex_runtime.h"
#define TRANSPOSE_ENGINE_REG (ARCH_CLUSTER_REG_BASE + ARCH_CLUSTER_REG_SIZE + 64)

void flex_transpose_engine_config(uint32_t M, uint32_t N, uint32_t src_addr, uint32_t dst_addr, uint32_t elem_size)
{
	volatile uint32_t * m_reg = (volatile uint32_t *) (TRANSPOSE_ENGINE_REG + 0);
	volatile uint32_t * n_reg = (volatile uint32_t *) (TRANSPOSE_ENGINE_REG + 4);
	volatile uint32_t * x_reg = (volatile uint32_t *) (TRANSPOSE_ENGINE_REG + 8);
	volatile uint32_t * y_reg = (volatile uint32_t *) (TRANSPOSE_ENGINE_REG + 12);
	volatile uint32_t * e_reg = (volatile uint32_t *) (TRANSPOSE_ENGINE_REG + 16);

	*m_reg = M;
	*n_reg = N;
	*x_reg = src_addr;
	*y_reg = dst_addr;
	*e_reg = elem_size;
}

uint32_t flex_transpose_engine_trigger(){
	volatile uint32_t * start_reg = (volatile uint32_t *) (TRANSPOSE_ENGINE_REG + 20);
	return *start_reg;
}

uint32_t flex_transpose_engine_wait(){
	volatile uint32_t * wait_reg = (volatile uint32_t *) (TRANSPOSE_ENGINE_REG + 24);
	return *wait_reg;
}

#endif
```
