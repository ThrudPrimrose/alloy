---
name: docs-md-arm-12-memory-tagging-intrinsics
description: "Arm ACLE: Memory tagging intrinsics (vendor documentation for Arm NEON, SVE and SME)."
when: "when you need Arm ACLE: Memory tagging intrinsics while writing a kernel for Arm NEON, SVE and SME."
---

# Memory tagging intrinsics

The intrinsics in this section provide access to the
Memory Tagging Extension (MTE) introduced with the Armv8.5-A [[ARMARMv85]](#ARMARMv85) architecture.

The `<arm_acle.h>` header should be included before using these intrinsics.

These intrinsics are expected to be used in system code, including freestanding
environments.  As such, implementations must guarantee that no new linking
dependencies to runtime support libraries will occur when these
intrinsics are used.

## Memory tagging

Memory tagging is a lightweight, probabilistic version of a lock and key
system where one of a limited set of lock values can be associated with
the memory locations forming part of an allocation, and the equivalent key
is stored in unused high bits of addresses used as references
to that allocation. On each use of a reference the key is checked to make
sure that it matches with the lock before an access is made.

When allocating memory, programmers must assign a lock to that section of memory.
When freeing an allocation, programmers must change the lock value so that
further referencing using the previous key has a reasonable probability of
failure.

The intrinsics specified below support creation, storage,
and retrieval of the lock values, leaving software to select and set the values
on allocation and deallocation. The intrinsics are expected to help protect
heap allocations.

The lock is referred to in the text below as `allocation tag` and the key as
`logical address tag` (or in short `logical tag`).

## Terms and implementation details

The memory system is extended with a new physical address space containing
an allocation tag for each 16-byte granule of memory in the existing data
physical address space. All loads and stores to  memory must pass a
valid logical address tag as part of the reference. However, SP- and PC-relative
addresses are not checked. The logical tag is held in the upper bits of
the reference.  There are 16 available logical tags that can be used.

## MTE intrinsics

These intrinsics are available when `__ARM_FEATURE_MEMORY_TAGGING` is defined.
Type T below can be any type.
Where the function return type is specified as T, the return type is determined
from the input argument which must also be specified as of type T.
If the input argument T has qualifiers `const` or  `volatile`, the return
type T will also have the `const` or `volatile` qualifier.

``` c
  T* __arm_mte_create_random_tag(T* src, uint64_t mask);
```

This intrinsic returns a pointer containing a randomly created logical address tag.
The first argument is a pointer `src` containing  an address.
The second argument is a `mask`, where the lower 16 bits specify logical tags
which must be excluded from consideration.
The intrinsic returns a pointer which is a copy of the input address but also
contains a randomly created logical tag (in the upper bits), that excludes any
logical tags specified by the `mask`.
A `mask` of zero excludes no tags.

``` c
  T* __arm_mte_increment_tag(T* src, unsigned offset);
```

This intrinsic returns a pointer which is a copy of the input pointer `src`
but with the logical address tag part offset by a specified offset value.
The first argument is a pointer `src` containing  an address and a logical tag.
The second argument is an offset which must be a compile time constant value
in the range [0,15].
The intrinsic adds `offset` to the logical tag part of `src`
returning a pointer with the incremented logical tag.
If adding the offset increments the logical tag beyond the valid 16 tags,
the value is wrapped around.

``` c
  uint64_t __arm_mte_exclude_tag(T* src, uint64_t excluded);
```

This intrinsic adds a logical tag to the set of excluded logical tags.
The first argument is a pointer `src` containing  an address and a logical tag.
The second argument `excluded` is a mask where the lower 16 bits specify
logical tags which are in current excluded set.
The intrinsic adds the logical tag of `src` to the set specified by `excluded`
and returns the new excluded tag set.

``` c
  void __arm_mte_set_tag(T* tag_address);
```

This intrinsic stores an allocation tag, computed from the logical tag,
to the tag memory thereby setting the allocation tag for the 16-byte
granule of memory.
The argument is a pointer `tag_address` containing  a logical tag and an address.
The address must be 16-byte aligned.
The type of the pointer is ignored (that is, allocation tag is set only for a
single granule even if the pointer points  to a type that is greater than 16 bytes).
These intrinsics generate an unchecked access to memory.

``` c
  T* __arm_mte_get_tag(T* address);
```

This intrinsic loads the allocation tag from tag memory and returns the
corresponding logical tag as part of the returned pointer value.
The argument is a pointer `address` containing an address from which
allocation tag memory is read.
The pointer `address`  need not be 16-byte aligned as it applies
to the 16-byte naturally aligned granule containing the un-aligned pointer.
The return value is a pointer whose address part comes from `address`
and the logical tag value is the value computed from the allocation
tag that was read from tag memory.

``` c
  ptrdiff_t __arm_mte_ptrdiff(T* a, T* b);
```

The intrinsic calculates the difference between the address parts of the
two pointers, ignoring the tags.
The return value is the sign-extended result of the computation.
The tag bits in the input pointers are ignored for this operation.
