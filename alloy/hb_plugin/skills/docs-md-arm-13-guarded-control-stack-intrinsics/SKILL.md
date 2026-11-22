---
name: docs-md-arm-13-guarded-control-stack-intrinsics
description: "Arm ACLE: Guarded Control Stack intrinsics (vendor documentation for Arm NEON, SVE and SME)."
when: "when you need Arm ACLE: Guarded Control Stack intrinsics while writing a kernel for Arm NEON, SVE and SME."
---

# Guarded Control Stack intrinsics

This section describes the intrinsics for the instructions of the
Guarded Control Stack (GCS) extension. The GCS instructions are present
in the AArch64 execution state only.

The specification for Guarded Control Stack is at Beta level.

When GCS protection is enabled, then function calls also save the return
address to a separate stack, the GCS, that is checked against the actual
return address when the function returns. At runtime, GCS protection can
be disabled and then calls and returns do not access the GCS. The GCS
grows down and a GCS pointer points to the last entry of the GCS.
Each thread has a separate GCS and GCS pointer.

To use the intrinsics, `arm_acle.h` must be included.

These intrinsics are available when GCS instructions are supported.
The `__chkfeat` intrinsics with `_CHKFEAT_GCS` can be used to check
if GCS protection is enabled at runtime. GCS protection is only
enabled at runtime if the code is GCS compatible and the GCS
instructions are supported.

## Intrinsics


``` c
  void *__gcspr(void);
```

Returns the GCS pointer of the current thread. The GCS pointer is represented
with the `void *` type. While normal stores do not work on GCS memory, this
pointer might be writable through the `GCSSS` operation or the `GCSSTR`
instruction when enabled.

``` c
  uint64_t __gcspopm(void);
```

Reads and returns the last entry on the GCS of the current thread and
updates the GCS pointer to point to the previous entry. If GCS
protection is disabled then it has no side effect and returns `0`.

An entry on the GCS is represented with the `uint64_t` because it has fixed
size and can be a token rather than a pointer.

``` c
  void *__gcsss(void *);
```

Switches the GCS of the current thread, where the argument is the new
GCS pointer, and returns the old GCS pointer. If GCS protection is
disabled then it has no side effect and returns `NULL`.
