---
name: docs-md-arm-09-synchronization-barrier-and-hint-intrins
description: "Arm ACLE: Synchronization, barrier, and hint intrinsics (vendor documentation for Arm NEON, SVE and SME)."
when: "when you need Arm ACLE: Synchronization, barrier, and hint intrinsics while writing a kernel for Arm NEON, SVE and SME."
---

# Synchronization, barrier, and hint intrinsics

## Introduction

This section provides intrinsics for managing data that may be accessed
concurrently between processors, or between a processor and a device.
Some intrinsics atomically update data, while others place barriers
around accesses to data to ensure that accesses are visible in the
correct order.

Memory prefetch intrinsics are also described in this section.

## Atomic update primitives

### C/C++ standard atomic primitives

The new C and C++ standards [[C11]](#C11) (7.17), [[CPP11]](#CPP11) (clause 29) provide a
comprehensive library of atomic operations and barriers, including
operations to read and write data with particular ordering requirements.
Programmers are recommended to use this where available.

### IA-64/GCC atomic update primitives

The `__sync` family of intrinsics (introduced in [[IA-64]](#IA-64) (section 7.4),
and as documented in the GCC documentation) may be provided, especially
if the C/C++ atomics are not available, and are recommended as being
portable and widely understood. These may be expanded inline, or call
library functions. Note that, unusually, these intrinsics are
polymorphic they will specialize to instructions suitable for the size
of their arguments.

## Memory barriers

Memory barriers ensure specific ordering properties between memory
accesses. For more details on memory barriers, see [ARMARM] (A3.8.3).
The intrinsics in this section are available for all targets.
They may be no-ops (that is, generate no code, but possibly act as a code
motion barrier in compilers) on targets where the relevant instructions
do not exist, but only if the property they guarantee would have held
anyway. On targets where the relevant instructions exist but are
implemented as no-ops, these intrinsics generate the instructions.

The memory barrier intrinsics take a numeric argument indicating the
scope and access type of the barrier, as shown in the following table.
(The assembler mnemonics for these numbers, as shown in the table, are
not available in the intrinsics.) The argument should be an integral
constant expression within the required range see
[Constant arguments to intrinsics](#constant-arguments-to-intrinsics).

| **Argument** | **Mnemonic** | **Domain**      | **Ordered Accesses (before-after)** |
| ------------ | ------------ | --------------- | ----------------------------------- |
| 15           | SY           | Full system     | Any-Any                             |
| 14           | ST           | Full system     | Store-Store                         |
| 13           | LD           | Full system     | Load-Load, Load-Store               |
| 11           | ISH          | Inner shareable | Any-Any                             |
| 10           | ISHST        | Inner shareable | Store-Store                         |
| 9            | ISHLD        | Inner shareable | Load-Load, Load-Store               |
| 7            | NSH or UN    | Non-shareable   | Any-Any                             |
| 6            | NSHST        | Non-shareable   | Store-Store                         |
| 5            | NSHLD        | Non-shareable   | Load-Load, Load-Store               |
| 3            | OSH          | Outer shareable | Any-Any                             |
| 2            | OSHST        | Outer shareable | Store-Store                         |
| 1            | OSHLD        | Outer shareable | Load-Load, Load-Store               |

The following memory barrier intrinsics are available:

``` c
    void __dmb(/*constant*/ unsigned int);
```

Generates a DMB (data memory barrier) instruction or equivalent CP15
instruction. DMB ensures the observed ordering of memory accesses.
Memory accesses of the specified type issued before the DMB are
guaranteed to be observed (in the specified scope) before memory
accesses issued after the DMB. For example, DMB should be used between
storing data, and updating a flag variable that makes that data
available to another core.

The `__dmb()` intrinsic also acts as a compiler memory barrier of the
appropriate type.

``` c
  void __dsb(/*constant*/ unsigned int);
```

Generates a DSB (data synchronization barrier) instruction or equivalent
CP15 instruction. DSB ensures the completion of memory accesses. A DSB
behaves as the equivalent DMB and has additional properties. After a DSB
instruction completes, all memory accesses of the specified type issued
before the DSB are guaranteed to have completed.

The `__dsb()` intrinsic also acts as a compiler memory barrier of the
appropriate type.

``` c
  void __isb(/*constant*/ unsigned int);
```

Generates an ISB (instruction synchronization barrier) instruction or
equivalent CP15 instruction. This instruction flushes the processor
pipeline fetch buffers, so that following instructions are fetched from
cache or memory. An ISB is needed after some system maintenance
operations.

An ISB is also needed before transferring control to code that has been
loaded or modified in memory, for example by an overlay mechanism or
just-in-time code generator. (Note that if instruction and data caches
are separate, privileged cache maintenance operations would be needed in
order to unify the caches.)

The only supported argument for the `__isb()` intrinsic is 15,
corresponding to the SY (full system) scope of the ISB instruction.

### Examples

In this example, process `P1` makes some data available to process `P2`
and sets a flag to indicate this.

``` c
  P1:

    value = x;
    /* issue full-system memory barrier for previous store:
       setting of flag is guaranteed not to be observed before
       write to value */
    __dmb(14);
    flag = true;

  P2:

    /* busy-wait until the data is available */
    while (!flag) {}
    /* issue full-system memory barrier: read of value is guaranteed
       not to be observed by memory system before read of flag */
    __dmb(15);
    /* use value */;
```

In this example, process `P1` makes data available to `P2` by putting
it on a queue.

``` c
  P1:

    work = new WorkItem;
    work->payload = x;
    /* issue full-system memory barrier for previous store:
       consumer cannot observe work item on queue before write to
       work item's payload */
    __dmb(14);
    queue_head = work;

  P2:

    /* busy-wait until work item appears */
    while (!(work = queue_head)) {}
    /* no barrier needed: load of payload is data-dependent */
    /* use work->payload */
```

## Hints

The intrinsics in this section are available for all targets. They may
be no-ops (that is, generate no code, but possibly act as a code motion
barrier in compilers) on targets where the relevant instructions do not
exist. On targets where the relevant instructions exist but are
implemented as no-ops, these intrinsics generate the instructions.

``` c
  void __wfi(void);
```

Generates a WFI (wait for interrupt) hint instruction, or nothing. The
WFI instruction allows (but does not require) the processor to enter a
low-power state until one of a number of asynchronous events occurs.

``` c
  void __wfe(void);
```

Generates a WFE (wait for event) hint instruction, or nothing. The WFE
instruction allows (but does not require) the processor to enter a
low-power state until some event occurs such as a SEV being issued by
another processor.

``` c
  void __sev(void);
```

Generates a SEV (send a global event) hint instruction. This causes an
event to be signaled to all processors in a multiprocessor system. It is
a NOP on a uniprocessor system.

``` c
  void __sevl(void);
```

Generates a send a local event hint instruction. This causes an event
to be signaled to only the processor executing this instruction. In a
multiprocessor system, it is not required to affect the other
processors.

``` c
  void __yield(void);
```

Generates a YIELD hint instruction. This enables multithreading software
to indicate to the hardware that it is performing a task, for example a
spin-lock, that could be swapped out to improve overall system
performance.

``` c
  void __dbg(/*constant*/ unsigned int);
```

Generates a DBG instruction. This provides a hint to debugging and
related systems. The argument must be a constant integer from 0 to 15
inclusive. See implementation documentation for the effect (if any) of
this instruction and the meaning of the argument. This is available only
when compiling for AArch32.

``` c
  uint64_t __chkfeat(uint64_t);
```

Checks for hardware features at runtime using the CHKFEAT hint instruction.
`__chkfeat` returns a bitmask where a bit is set if the same bit in the
input argument is set and the corresponding feature is enabled. It can be
used with predefined macros:

| **Macro name**           | **Value**           | **Meaning**                                        |
| ``_CHKFEAT_GCS``         | 1                   | Guarded Control Stack (GCS) protection is enabled. |

Note: for usability reasons the return value differs from how the CHKFEAT
instruction sets X16.

## Swap

`__swp` is available for all targets. This intrinsic expands to a
sequence equivalent to the deprecated (and possibly unavailable) SWP
instruction.

``` c
  uint32_t __swp(uint32_t, volatile void *);
```

Unconditionally stores a new value at the given address, and returns the
old value.

As with the IA-64/GCC primitives described in 0, the `__swp` intrinsic
is polymorphic. The second argument must provide the address of a
byte-sized object or an aligned word-sized object and it must be
possible to determine the size of this object from the argument
expression.

This intrinsic is implemented by LDREX/STREX (or LDREXB/STREXB) where
available, as if by

``` c
  uint32_t __swp(uint32_t x, volatile uint32_t *p) {
    uint32_t v;
    /* use LDREX/STREX intrinsics not specified by ACLE */
    do v = __ldrex(p); while (__strex(x, p));
    return v;
  }
```

or alternatively,

``` c
  uint32_t __swp(uint32_t x, uint32_t *p) {
    uint32_t v;
    /* use IA-64/GCC atomic builtins */
    do v = *p; while (!__sync_bool_compare_and_swap(p, v, x));
    return v;
  }
```

It is recommended that compilers should produce a
downgradeable/upgradeable warning on encountering the `__swp` intrinsic.

Only if load-store exclusive instructions are not available will the
intrinsic use the SWP/SWPB instructions.

It is strongly recommended to use standard and flexible atomic
primitives such as those available in the C++ <atomic> header. `__swp`
is provided solely to allow straightforward (and possibly automated)
replacement of explicit use of SWP in inline assembler. SWP is obsolete
in the Arm architecture, and in recent versions of the architecture, may
be configured to be unavailable in user-mode. (Aside: unconditional
atomic swap is also less powerful as a synchronization primitive than
load-exclusive/store-conditional.)

## Memory prefetch intrinsics

Intrinsics are provided to prefetch data or instructions. The size of
the data or function is ignored. Note that the intrinsics may be
implemented as no-ops (that is, not generate a prefetch instruction, if none
is available). Also, even where the architecture does provide a prefetch
instruction, a particular implementation may implement the instruction
as a no-op (that is, the instruction has no effect).

### Data prefetch

``` c
  void __pld(void const volatile *addr);
```

Generates a data prefetch instruction, if available. The argument should
be any expression that may designate a data address. The data is
prefetched to the innermost level of cache, for reading.

``` c
  void __pldx(/*constant*/ unsigned int /*access_kind*/,
              /*constant*/ unsigned int /*cache_level*/,
              /*constant*/ unsigned int /*retention_policy*/,
              void const volatile *addr);
```

Generates a data prefetch instruction. This intrinsic allows the
specification of the expected access kind (read or write), the cache
level to load the data, the data retention policy (temporal or
streaming), The relevant arguments can only be one of the following
values.

| **Access Kind** | **Value** | **Summary**                              |
| --------------- | --------- | ---------------------------------------- |
| PLD             | 0         | Fetch the addressed location for reading |
| PST             | 1         | Fetch the addressed location for writing |

| Cache Level | Value | Summary                                                |
| ----------- | ----- | ------------------------------------------------------ |
| L1          | 0     | Fetch the addressed location to L1 cache               |
| L2          | 1     | Fetch the addressed location to L2 cache               |
| L3          | 2     | Fetch the addressed location to L3 cache               |
| SLC         | 3     | Fetch the addressed location to the System-Level Cache |

| **Retention Policy** | **Value** | **Summary**                                                                |
| -------------------- | --------- | -------------------------------------------------------------------------- |
| KEEP                 | 0         | Temporal fetch of the addressed location (that is, allocate in cache normally) |
| STRM                 | 1         | Streaming fetch of the addressed location (that is, memory used only once)     |

The `__ARM_PREFETCH_RANGE` macro can be used to test for the presence of the
following range prefetch intrinsics:

``` c
  void __pldx_range(/*constant*/ unsigned int /*access_kind*/,
                    /*constant*/ unsigned int /*retention_policy*/,
                    /*constant*/ signed int   /*length*/,
                    /*constant*/ unsigned int /*count*/,
                    /*constant*/ signed int   /*stride*/,
                    /*constant*/ size_t       /*reuse distance*/,
                    void const volatile *addr);
```

Generates a data prefetch instruction for a range of addresses starting from a
given base address. Locations within the specified address ranges are prefetched
into one or more caches. This intrinsic allows the specification of the
expected access kind (read or write), the data retention policy (temporal or
streaming) and the length, count, stride and reuse distance metadata values.

The access kind and data retention policy arguments can only be one of the
following values.

| **Access Kind** | **Value** | **Summary**                              |
| --------------- | --------- | ---------------------------------------- |
| PLD             | 0         | Fetch the addressed location for reading |
| PST             | 1         | Fetch the addressed location for writing |

| **Retention Policy** | **Value** | **Summary**                                                                |
| -------------------- | --------- | -------------------------------------------------------------------------- |
| KEEP                 | 0         | Temporal fetch of the addressed location (that is, allocate in cache normally) |
| STRM                 | 1         | Streaming fetch of the addressed location (that is, memory used only once)     |

The table below describes the ranges of the length, count, stride and reuse distance arguments.

| **Metadata**   | **Range**           | **Summary**                                                          |
| -------------- | ------------------- | -------------------------------------------------------------------- |
| Length         | [-2MiB, +2MiB)      | Number of contiguous bytes to be accessed.                           |
| Count          | [1, 65536]          | Number of blocks to be accessed.                                     |
| Stride         | [-2MiB, +2MiB)      | Number of bytes to advance the block address by after `Length`       |
|                |                     | bytes have been accessed. Note: This value is ignored if Count is 1. |
| Reuse Distance |                     | Maximum number of bytes to be accessed before executing the next     |
|                |                     | RPRFM instruction that specifies the same range. All values are      |
|                |                     | rounded up to the nearest power of 2 in the range 32KiB to 512MiB.   |
|                |                     | Values exceeding the maximum of 512MiB will be represented by 0,     |
|                |                     | indicating distance not known.                                       |
|                |                     | Note: This value is ignored if a streaming prefetch is specified.    |

``` c
  void __pld_range(/*constant*/ unsigned int /*access_kind*/,
                   /*constant*/ unsigned int /*retention_policy*/,
                   uint64_t /*metadata*/,
                   void const volatile *addr);
```

Generates a data prefetch instruction for a range of addresses starting from a
given base address. Locations within the specified address ranges are prefetched
into one or more caches. The access kind and retention policy arguments can
have the same values as in `__pldx_range`. The bits of the metadata argument
are interpreted as follows:

| **Metadata**   | **Bits** | **Range**       | **Summary**                                                  |
| -------------- | -------- | --------------- | ------------------------------------------------------------ |
| Length         | 0-21     | [-2MiB, +2MiB)  | Signed integer representing the number of contiguous         |
|                |          |                 | bytes to be accessed.                                        |
| Count          | 37-22    | [0, 65535]      | Unsigned integer representing number of blocks of data       |
|                |          |                 | to be accessed, minus 1.                                     |
| Stride         | 59-38    | [-2MiB, +2MiB)  | Signed integer representing the number of bytes to advance   |
|                |          |                 | the block address by after `Length` bytes have been          |
|                |          |                 | accessed. This value is ignored if Count is 0.               |
| Reuse Distance | 63-60    | [0, 15]         | Indicates the maximum number of bytes to be accessed before  |
|                |          |                 | executing the next RPRFM instruction that specifies the same |
|                |          |                 | range. Bits encode decreasing powers of two in the range     |
|                |          |                 | 1 (512MiB) to 15 (32KiB). 0 indicates distance not known.    |

### Instruction prefetch

``` c
  void __pli(T addr);
```

Generates a code prefetch instruction, if available. If a specific code
prefetch instruction is not available, this intrinsic may generate a
data-prefetch instruction to fetch the addressed code to the innermost
level of unified cache. It will not fetch code to data-cache in a split
cache level.

``` c
  void __plix(/*constant*/ unsigned int /*cache_level*/,
              /*constant*/ unsigned int /*retention_policy*/,
              T addr);
```

Generates a code prefetch instruction. This intrinsic allows the
specification of the cache level to load the code, the retention policy
(temporal or streaming). The relevant arguments can have the same values
as in `__pldx`.

`__pldx` and `__plix` arguments cache level and retention policy
are ignored on unsupported targets.

### Intent to read prefetch

``` c
  void __pldir(void const volatile *addr);
```
Generates an intent to read on update prefetch instruction. The argument should
be any expression that may designate a data address. This intrinsic does
not require specification of cache level or retention policy. Support for this
intrinsic is indicated by `__ARM_FEATURE_PCDPHINT`.

## NOP

``` c
  void __nop(void);
```

Generates an unspecified no-op instruction. Note that not all
architectures provide a distinguished NOP instruction. On those that do,
it is unspecified whether this intrinsic generates it or another
instruction. It is not guaranteed that inserting this instruction will
increase execution time.
