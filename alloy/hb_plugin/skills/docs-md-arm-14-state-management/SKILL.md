---
name: docs-md-arm-14-state-management
description: "Arm ACLE: State management (vendor documentation for Arm NEON, SVE and SME)."
when: "when you need Arm ACLE: State management while writing a kernel for Arm NEON, SVE and SME."
---

# State management

The specification for SME is in
[**Beta** state](#support-levels) and might change or be
extended in the future.

## Introduction

ACLE often uses normal C and C++ objects to represent architectural state.
These objects are passed to intrinsics and returned from intrinsics in
the same way as they would be for a normal function.

For example, ACLE defines an `svbool_t` type to represent the
contents of an SVE predicate register. SVE intrinsics that read
a predicate register have an `svbool_t` argument for that register.
SVE intrinsics that write to a predicate register have an `svbool_t`
return type for that register.

SVE provides 16 predicate registers, but this number is not exposed to
C and C++ code. Instead, the program can have as many `svbool_t` objects
as it needs, and it is the compiler's responsibility to manage the
register allocation.

However, there are some pieces of architectural state for which this
approach is not suitable. For example, [SME's ZA](#za-storage) is a
single piece of storage: there are not multiple ZAs, and so it does
not make sense for a C or C++ function to have multiple ZA objects.
It would also be inefficient to copy state from one ZA object to another.

ACLE models this kind of architectural state using [keyword
attributes](#keyword-attributes) rather than types and objects.
The main purpose of these keyword attributes is to establish the following
binary choices for a given piece of architectural state S:

<span id="shares-state"></span><span id="uses-state"></span>

1.  A function with a given type either shares S with its caller,
    or it does not.

2.  A given function definition either uses S internally, or it does not.

A function definition that shares S with its caller also (implicitly) uses
S internally.

<span id="new-state-scope"></span>

A function definition that uses S internally but does not share S with
its caller is said to create a “new scope” for S.

ACLE uses strings to identify each piece of state that is managed in
this way. The strings are listed in the table below.

<span id="state-strings"></span>

| **String** | **State**          | **State macro**   | **Feature macro**    |
| ---------- | ------------------ | ----------------- | -------------------- |
| `"za"`     | SME's ZA storage   | `__ARM_STATE_ZA`  | `__ARM_FEATURE_SME`  |
| `"zt0"`    | SME2's ZT0         | `__ARM_STATE_ZT0` | `__ARM_FEATURE_SME2` |

For each string, there are two associated macros:

*   a so-called “state macro” that compilers predefine if they recognize
    the string

*   a so-called “feature macro” that compilers predefine if they can compile
    functions that use the state

A compiler that predefines the feature macro must also predefine the
state macro.

For example, `__ARM_STATE_ZA` allows declarations of functions that share ZA.
`__ARM_FEATURE_SME` allows function definitions to use ZA internally.

The strings are case-sensitive. For example, `"za"` cannot be written `"ZA"`.

## Ways of sharing state

ACLE identifies several different ways in which a callee can share
state with its caller. Each one has an associated [keyword
attribute](#keyword-attributes):

*   `__arm_in`: the callee takes the state as input and returns with
    the state unchanged. This is similar to a const reference in C++.

*   `__arm_out`: the callee ignores the incoming state and returns new state.
    This is similar to a function return value.

*   `__arm_inout`: the callee takes the state as input and returns new state.
    This is similar to a non-const reference in C++.

*   `__arm_preserves`: the callee does not read the incoming state and
    returns with the state unchanged.

Each keyword attribute takes a comma-separated list of state strings as
an argument. The list must be non-empty.

For example:

``` c
   void f() __arm_inout("za") __arm_preserves("zt0");
```

says that `f` uses ZA to receive data from callers and to pass data
back to callers. `f` also promises to preserve the contents of ZT0.

A program is [ill-formed](#ill-formed) if a function type has two
attributes that specify different behavior for the same piece of state.
For example, a program is ill-formed if a function type has both
`__arm_in("za")` and `__arm_out("za")`, or both `__arm_in("za")`
and `__arm_inout("za")`.

The same information may be specified multiple times. For example:

``` c
  void f() __arm_in("za", "za") __arm_in("za");
```

is well-formed.

Two function types are incompatible if they handle a piece of
architectural state differently. For example:

``` c
   void f1() __arm_in("za");
   void f2() __arm_out("za");
   void f3() __arm_inout("za");
   void f4() __arm_preserves("za");
   void f5();

   void (*ptr1)() __arm_in("za");
   void (*ptr2)() __arm_out("za");
   void (*ptr3)() __arm_inout("za");
   void (*ptr4)() __arm_preserves("za");
   void (*ptr5)();

   void test() {
     ptr1 = f1;    // OK
     ptr2 = f1;    // Invalid
     ptr3 = f1;    // Invalid
     ptr4 = f1;    // Invalid
     ptr5 = f1;    // Invalid

     ptr1 = f2;    // Invalid
     ptr2 = f2;    // OK
     ptr3 = f2;    // Invalid
     ptr4 = f2;    // Invalid
     ptr5 = f2;    // Invalid

     ptr1 = f3;    // Invalid
     ptr2 = f3;    // Invalid
     ptr3 = f3;    // OK
     ptr4 = f3;    // Invalid
     ptr5 = f3;    // Invalid

     ptr1 = f4;    // Invalid
     ptr2 = f4;    // Invalid
     ptr3 = f4;    // Invalid
     ptr4 = f4;    // OK
     ptr5 = f4;    // Invalid

     ptr1 = f5;    // Invalid
     ptr2 = f5;    // Invalid
     ptr3 = f5;    // Invalid
     ptr4 = f5;    // Invalid
     ptr5 = f5;    // OK
   }
```

`__arm_in` and `__arm_preserves` both guarantee that a function leaves
the contents of the state unchanged on return. Functions are not
[ill-formed](#ill-formed) if they write to such state, but they must ensure
that the cumulative effect of such writes is to leave the state unchanged.

A program is [ill-formed](#ill-formed) if a function that does not [use
state](#uses-state) S contains a call to a function that shares S with
its caller. This is conceptually similar to an undefined variable in
C. For example:

``` c
   void callee() __arm_inout("za");
   void caller() {
     callee(); // Ill-formed, caller does not use ZA
   }
```

If a C or C++ function F [uses state](#uses-state) S internally and calls
a function F2 that does not share S with its callers, the call to F2 has
no effect on F's S state. The compiler must ensure this by [restoring
the old contents of S](#za-implementation-notes) after the call to F2,
if such a restoration is necessary. For example:

``` c
   void za_callee() __arm_inout("za");
   void za_caller() __arm_inout("za") {
     za_callee();
     printf("Here\n"); // Does not change za_caller's ZA state
     za_callee();
   }
```

## `__arm_agnostic`

A function with the `__arm_agnostic` [keyword attribute](#keyword-attributes)
must preserve the architectural state that is specified by its arguments when
such state exists at runtime. The function is otherwise unconcerned with this
state.

The `__arm_agnostic` [keyword attribute](#keyword-attributes) applies to
**function types** and accepts the following arguments:

```"sme_za_state"```

*   This attribute affects the ABI of a function, which must implement an
    [agnostic-ZA interface](#agnostic-za). It is the responsibility of the compiler
    to ensure that the object code of the function honors the ABI requirements.

*   The use of `__arm_agnostic("sme_za_state")` allows writing functions that
    are compatible with ZA state without having to share ZA state with the
    caller, as required by `__arm_preserves`. The use of this attribute
    does not imply that SME is available.

*   It is not valid for a function declaration with
    `__arm_agnostic("sme_za_state")` to [share](#shares-state) PSTATE.ZA state
    with its caller.

## Mapping to the Procedure Call Standard

[[AAPCS64]](#AAPCS64) classifies functions as having one of the following
interfaces:

<span id="private-za"></span>

*   a “private-ZA” interface

*   a “shared-ZA” interface

<span id="agnostic-za"></span>

*   an "agnostic-ZA" interface

If a C or C++ function F forms part of ABI for the object code:

* the object code function has a shared-ZA interface only if at least
  one of the following is true:

  * F shares ZA with its caller

  * F shares ZT0 with its caller

* the object code function has an agnostic-ZA interface only if the type for F
  has an `__arm_agnostic("sme_za_state")` attribute.

All other functions have a private-ZA interface.

## Function definitions

<span id="arm_new"></span>

The [keyword attribute](#keyword-attributes) `__arm_new(...)`
applies to function definitions. It specifies that the function
creates a [new scope](#new-state-scope) for the given state. `...` is a
comma-separated list of [state strings](#state-strings). The list
must be non-empty.

Each piece of state specified by `__arm_new` is zero-initialized.

This attribute does not change a function's binary interface. If the
function forms part of the object code's ABI, that object code function
has the same interface as it would have had without `__arm_new`.

A program is [ill-formed](#ill-formed) if a function definition F
uses `__arm_new` for some state that F also [shares](#shares-state)
with its caller. For example:

``` c
  __arm_new("za") void f1() __arm_in("za") { ... }     // Invalid
  __arm_new("za") void f2() __arm_out("za") { ... }    // Invalid
  __arm_new("za") void f3() __arm_inout("za") { ... }  // Invalid
  __arm_new("za") void f4() __arm_inout("zt0") { ... } // OK
  __arm_new("zt0") void f5() __arm_inout("za") { ... } // OK
```

## Inline assembly

Some ACLE implementations might support the GNU inline asm extension.
For implementations that do, suppose that an inline asm occurs in a
function F that [uses state](#uses-state) S. There are then two
possibilities:

*   S is not an input to the asm and S is not an output from the asm.
    The contents of S immediately after executing the asm's instructions
    are the same as the contents of S immediately before executing the
    instructions. This is the default assumption.

*   S might be an input to the asm, might be an output from the asm,
    and might be changed by the asm's instructions. This is indicated by
    adding S's string to the asm's clobber list. For example, if an asm's
    clobber list includes `"za"`, ZA might be an input to the asm,
    an output from the asm, or something that the asm changes.

If instead the inline asm occurs in a function that does not [use
state](#uses-state) S, the two possibilities are:

*   S is not an input to the asm and S is not an output from the asm.
    The contents of S immediately after executing the asm's instructions
    are the same as the contents of S immediately before executing the
    instructions. This is the default assumption.

*   S is not an input to the asm and S is not an output from the asm.
    However, the contents of S after executing the asm's instructions might
    be different from the contents of S before executing the instructions.
    This is indicated by adding S's string to the asm's clobber list.

    If an asm takes this option for state that is controlled by PSTATE.ZA,
    the asm itself is responsible for handling the [[AAPCS64]](#AAPCS64)
    lazy save scheme.

[[AAPCS64]](#AAPCS64) defines three possible states for ZA:
“off”, “dormant” or “active”. These states describe the values
of two things:

*   the PSTATE.ZA bit

*   the TPIDR2_EL0 register

ZA is guaranteed to be active on entry to an inline asm A in a
function F if at least one of the following is true:

*   F [uses `"za"`](#uses-state) and A's clobber list includes `"za"`.

*   F [uses `"zt0"`](#uses-state) and A's clobber list includes `"zt0"`.

Otherwise, ZA can be in any state on entry to A if at least one of the
following is true:

*   F [uses](#uses-state) `"za"`.

*   F [uses](#uses-state) `"zt0"`.

*   F's type has an [`__arm_agnostic("sme_za_state")` attribute](#agnostic-za)
    and A's clobber-list includes neither `"za"` nor `"zt0"`.

Otherwise, ZA can be off or dormant on entry to A, in the same way as if F were
to call what the [[AAPCS64]](#AAPCS64) describes as a "private-ZA" function.

If ZA is active on entry to A then A's instructions must ensure that
ZA is also active when the asm finishes.

Similarly, if ZA is off on entry to A then A's instructions must ensure
that ZA is off when the asm finishes.

If ZA is dormant on entry to A and A's clobber list does not include `"za"`,
A's instructions must ensure that ZA is dormant when the asm finishes.

Otherwise, if ZA is dormant on entry to A and A's clobber list
includes `"za"`, A's instructions can leave ZA unchanged or in
the off state (A's choice).  In the latter case, A's instructions
must commit the lazy save that was pending on entry to A.

The table below summarizes the possible ZA states on entry to an
inline asm A in a function F. It also specifies what the state
is required to be when A finishes; it is the asm's responsibility
to ensure this. Since PSTATE.ZA controls both ZA and ZT0, the rules
depend on ZT0 as well as ZA.

| **ZA state before A** | **ZA state after A** | **Possible if…**                       |
| --------------------- | -------------------- | -------------------------------------- |
| off                   | off                  | F's uses and A's clobbers are disjoint |
| dormant               | dormant              | " " "                                  |
| dormant               | off                  | " " ", and A clobbers `"za"`           |
| active                | active               | F uses `"za"` and/or `"zt0"`, or       |
|                       |                      | F's type has an                        |
|                       |                      | `__arm_agnostic("sme_za_state")`       |
|                       |                      | attribute with A's clobber-list        |
|                       |                      | including neither `"za"` nor `"zt0"`   |

The [`__ARM_STATE` macros](#state-strings) indicate whether a compiler
is guaranteed to support a particular clobber string. For example,
the following code is a safe way to indicate that an asm might commit
a lazy ZA save:

``` c
  // Function foo doesn't use ZA or ZT0.
  void foo() {
    ...
    asm volatile("bl something"
                 ::: ...call-clobbered registers...
#ifdef __ARM_STATE_ZA
                     , "za"
#endif
                );
    ...
  }
```

## Implementation notes

<span id="za-implementation-notes"></span>

A piece of state S can be said to be “live” at a point P during the
execution of a function F if:

*   F [uses](#uses-state) S; and

*   a random, exogenous change to S at P could change the behavior
    of the program.

If S is live before a call from F to a function F2 that does not share S
with its caller, the compiler must arrange for S to be preserved around
the call to F2. One way to do this is to save S before the call and
restore it afterwards. However, if S is ZA and F2 is a private-ZA
function, the compiler can instead make use of the lazy-save scheme
described in [[AAPCS64]](#AAPCS64).

For example, the code below shows a function that uses ZA and ZT0
internally. The comments describe when ZA should be saved and restored:

``` c
  void f_shares_zt0() __arm_inout("zt0");
  void f_shares_za() __arm_inout("za");
  void f_private();

  void setup_za() __arm_out("za");
  void use_za() __arm_in("za");

  __arm_new("za", "zt0") void test() {
    f_private();     // ZA is not live, no save necessary

    setup_za();      // ZA is live after this call
    f_shares_zt0();  // The compiler should save and restore ZA
                     // around the call ("caller-save")
    f_shares_za();   // ZA is live before and after this call
    f_private();     // The compiler should preserve ZA across the call
                     // It can use the lazy-save mechanism
    use_za();        // ZA is no longer live after this call

    f_private();     // ZA is not live, no save necessary
  }
```

ZT0 cannot be saved lazily, so if ZT0 is live before a call to a
function that does not share ZT0, the compiler must save and restore
ZT0 around the call. For example:

``` c
  void setup_zt0() __arm_out("zt0");
  void use_zt0() __arm_in("zt0");
  void f_private();

  __arm_new("zt0") void test() {
    f_private();     // ZT0 is not live, no save necessary

    setup_zt0();     // ZT0 is live after this call
    f_private();     // The compiler should save and restore ZT0
                     // around the call ("caller-save")
    use_zt0();       // ZT0 is no longer live after this call

    f_private();     // ZT0 is not live, no save necessary
  }
```

# System register access

## Special register intrinsics

Intrinsics are provided to read and write system and coprocessor
registers, collectively referred to as special register.

``` c
  uint32_t __arm_rsr(const char *special_register);
```

Reads a 32-bit system register.

``` c
  uint64_t __arm_rsr64(const char *special_register);
```

Reads a 64-bit system register.

``` c
  __uint128_t __arm_rsr128(const char *special_register);
```

Reads a 128-bit system register. Only available if `__ARM_FEATURE_SYSREG128` is
defined to 1.

``` c
  void* __arm_rsrp(const char *special_register);
```

Reads a system register containing an address.

``` c
  float __arm_rsrf(const char *special_register);
```

Reads a 32-bit coprocessor register containing a floating point value.

``` c
  double __arm_rsrf64(const char *special_register);
```

Reads a 64-bit coprocessor register containing a floating point value.

``` c
  void __arm_wsr(const char *special_register, uint32_t value);
```

Writes a 32-bit system register.

``` c
  void __arm_wsr64(const char *special_register, uint64_t value);
```

Writes a 64-bit system register.

``` c
  void __arm_wsr128(const char *special_register, __uint128_t value);
```

Writes a 128-bit system register. Only available if `__ARM_FEATURE_SYSREG128` is
defined to 1.

``` c
  void __arm_wsrp(const char *special_register, const void *value);
```

Writes a system register containing an address.

``` c
  void __arm_wsrf(const char *special_register, float value);
```

Writes a floating point value to a 32-bit coprocessor register.

``` c
  void __arm_wsrf64(const char *special_register, double value);
```

Writes a floating point value to a 64-bit coprocessor register.

## Special register designations

The `special_register` parameter must be a compile time string literal.
This means that the implementation can determine the register being
accessed at compile-time and produce the correct instruction without
having to resort to self-modifying code. All register specifiers are
case-insensitive (so "apsr" is equivalent to "APSR"). The string literal
should have one of the forms described below.

### AArch32 32-bit coprocessor register

When specifying a 32-bit coprocessor register to `__arm_rsr`,
`__arm_rsrp`, `__arm_rsrf`, `__arm_wsr`, `__arm_wsrp`, or
`__arm_wsrf`:

``` c
  cp<coprocessor>:<opc1>:c<CRn>:c<CRm>:<opc2>
```

Or (equivalently):

``` c
  p<coprocessor>:<opc1>:c<CRn>:c<CRm>:<opc2>
```

Where:

* `<coprocessor>` is a decimal integer in the range `[0, 15]`
* `<opc1>`, `<opc2>` are decimal integers in the range `[0, 7]`
* `<CRn>`, `<CRm>` are decimal integers in the range `[0, 15]`.

The values of the register specifiers will be as described in [[ARMARM]](#ARMARM)
or the Technical Reference Manual (TRM) for the specific processor.

So to read MIDR:

``` c
  unsigned int midr = __arm_rsr("cp15:0:c0:c0:0");
```

ACLE does not specify predefined strings for the system coprocessor
register names documented in the Arm Architecture Reference Manual (for example “ MIDR ”).

### AArch32 32-bit system register

When specifying a 32-bit system register to `__arm_rsr`, `__arm_rsrp`,
`__arm_wsr`, or `__arm_wsrp`, one of:

* The values accepted in the `spec_reg` field of the MRS
  instruction [[ARMARM]](#ARMARM) (B6.1.5), for example CPSR.
* The values accepted in the  `spec_reg` field of the MSR
  (immediate) instruction [[ARMARM]](#ARMARM) (B6.1.6).
* The values accepted in the `spec_reg` field of the VMRS
  instruction [[ARMARM]](#ARMARM) (B6.1.14), for example FPSID.
* The values accepted in the `spec_reg` field of the VMSR
  instruction [[ARMARM]](#ARMARM) (B6.1.15), for example FPSCR.
* The values accepted in the `spec_reg` field of the MSR and MRS
  instructions with virtualization extensions [[ARMARM]](#ARMARM)  (B1.7), for example
  `ELR_Hyp`.
* The values specified in Special register encodings used in
  Armv7-M  system instructions. [[ARMv7M]](#ARMv7M) (B5.1.1), for example  PRIMASK.

### AArch32 64-bit coprocessor register

When specifying a 64-bit coprocessor register to `__arm_rsr64`,
`__arm_rsrf64`, `__arm_wsr64`, or `__arm_wsrf64`

``` c
  cp<coprocessor>:<opc1>:c<CRm>
```

Or (equivalently):

``` c
  p<coprocessor>:<opc1>:c<Rm>
```

Where:

* `<coprocessor>` is a decimal  integer in the range `[0, 15]`
* `<opc1>` is a decimal integer in  the range `[0, 7]`
* `<CRm>` is a decimal integer in the  range `[0, 15]`

### AArch64 system register

When specifying a system register to `__arm_rsr`, `__arm_rsr64`, `__arm_rsr128`,
`__arm_rsrp`, `__arm_wsr`, `__arm_wsr64`,`__arm_wsr128` or `__arm_wsrp`:

``` c
  "o0:op1:CRn:CRm:op2"
```

Where:

* `<o0>` is a decimal integer in the range `[0, 3]`
* `<op1>`, `<op2>` are decimal integers in the range `[0, 7]`
* `<CRm>`, `<CRn>` are decimal integers in the range `[0, 15]`

### AArch64 processor state field

When specifying a processor state field to `__arm_rsr`, `__arm_rsp`,
`__arm_wsr`, or `__arm_wsrp`, one of the values accepted in the
pstatefield of the MSR (immediate) instruction [[ARMARMv8]](#ARMARMv8) (C5.6.130).

## Coprocessor Intrinsics

### AArch32 coprocessor intrinsics

In the intrinsics below `coproc`, `opc1`, `opc2`, `CRn` and `CRd` are
all compile time integer constants with appropriate values as defined by the
coprocessor for the intended architecture.

The argument order for all intrinsics is the same as the operand order for the
instruction as described in the Arm Architecture Reference Manual, with the exception of `MRC`/
`MRC2`/ `MRRC`/`MRRC2` which omit the Arm register arguments and instead
returns a value and `MCRR`/`MCRR2` which accepts a single 64 bit unsigned
integer instead of two 32-bit unsigned integers.

### AArch32 Data-processing coprocessor intrinsics

Intrinsics are provided to create coprocessor data-processing
instructions as follows:

| **Intrinsics**                                        | **Equivalent Instruction**             |
| ----------------------------------------------------- | -------------------------------------- |
| void __arm_cdp(coproc, opc1, CRd, CRn, CRm, opc2)     | CDP coproc, opc1, CRd, CRn, CRm, opc2  |
| void __arm_cdp2(coproc, opc1, CRd, CRn, CRm, opc2)    | CDP2 coproc, opc1, CRd, CRn, CRm, opc2 |

#### AArch32 Memory coprocessor transfer intrinsics

Intrinsics are provided to create coprocessor memory transfer
instructions as follows:

| **Intrinsics**                                   | **Equivalent Instruction** |
| ------------------------------------------------ | -------------------------- |
| void __arm_ldc(coproc, CRd, const void* p)       | LDC coproc, CRd, [...]     |
| void __arm_ldcl(coproc, CRd, const void* p)      | LDCL coproc, CRd, [...]    |
| void __arm_ldc2(coproc, CRd, const void* p)      | LDC2 coproc, CRd, [...]    |
| void __arm_ldc2l(coproc, CRd, const void* p)     | LDC2L coproc, CRd, [...]   |
| void __arm_stc(coproc, CRd, void* p)             | STC coproc, CRd, [...]     |
| void __arm_stcl(coproc, CRd, void* p)            | STCL coproc, CRd, [...]    |
| void __arm_stc2(coproc, CRd, void* p)            | STC2 coproc, CRd, [...]    |
| void __arm_stc2l(coproc, CRd, void* p)           | STC2L coproc, CRd, [...]   |

### AArch32 Integer to coprocessor transfer intrinsics

Intrinsics are provided to map to coprocessor to core register transfer
instructions as follows:

| **Intrinsics**                                                    | **Equivalent Instruction**            |
| ----------------------------------------------------------------- | ------------------------------------- |
| void __arm_mcr(coproc, opc1, uint32_t value, CRn, CRm, opc2)      | MCR coproc, opc1, Rt, CRn, CRm, opc2  |
| void __arm_mcr2(coproc, opc1, uint32_t value, CRn, CRm, opc2)     | MCR2 coproc, opc1, Rt, CRn, CRm, opc2 |
| uint32_t __arm_mrc(coproc, opc1, CRn, CRm, opc2)                  | MRC coproc, opc1, Rt, CRn, CRm, opc2  |
| uint32_t __arm_mrc2(coproc, opc1, CRn, CRm, opc2)                 | MRC2 coproc, opc1, Rt, CRn, CRm, opc2 |
| void __arm_mcrr(coproc, opc1, uint64_t value, CRm)                | MCRR coproc, opc1, Rt, Rt2, CRm       |
| void __arm_mcrr2(coproc, opc1, uint64_t value, CRm)               | MCRR2 coproc, opc1, Rt, Rt2, CRm      |
| uint64_t __arm_mrrc(coproc, opc1, CRm)                            | MRRC coproc, opc1, Rt, Rt2, CRm       |
| uint64_t __arm_mrrc2(coproc, opc1, CRm)                           | MRRC2 coproc, opc1, Rt, Rt2, CRm      |

The intrinsics `__arm_mcrr`/`__arm_mcrr2` accept a single unsigned 64-bit
integer value instead of two 32-bit integers.  The low half of the value goes
in register `Rt` and the high half goes in `Rt2`.  Likewise for
`__arm_mrrc`/`__arm_mrrc2` which return an unsigned 64-bit integer.

## Unspecified behavior

ACLE does not specify how the implementation should behave in the
following cases:

* When merging multiple reads/writes of the same register.

* When writing to a read-only register, or a register that is
  undefined on the architecture being compiled for.

* When reading or writing to a register which the implementation
  models by some other means (this covers – but is not limited to –
  reading/writing cp10 and cp11 registers when VFP is enabled, and
  reading/writing the CPSR).

* When reading or writing a register using one of these
  intrinsics with an inappropriate type for the value being read or
  written to.

* When writing to a coprocessor register that carries out a
  "System operation".

* When using a register specifier which doesn't apply to the
  targeted architecture.

# Instruction generation

## Instruction generation, arranged by instruction

The following table indicates how instructions may be generated by
intrinsics, and/or C code. The table includes integer data processing
and certain system instructions.

Compilers are encouraged to use opportunities to combine instructions,
or to use shifted/rotated operands where available. In general,
intrinsics are not provided for accumulating variants of instructions in
cases where the accumulation is a simple addition (or subtraction)
following the instruction.

The table indicates which architectures the instruction is supported on,
as follows:

Architecture 8 means Armv8-A AArch32 and AArch64, 8-32
means Armv8-AArch32 only.  8-64 means Armv8-AArch64 only.

Architecture 7 means Armv7-A and Armv7-R.

In the sequence of Arm architectures { 5, 5TE, 6, 6T2, 7 }
each architecture includes its predecessor instruction set.

In the sequence of Thumb-only architectures { 6-M, 7-M, 7E-M }
each architecture includes its predecessor instruction set.

7MP are the Armv7 architectures that implement the Multiprocessing Extensions.

| **Instruction** | **Flags** | **Arch.**     | **Intrinsic or C code**                               |
| --------------- | --------- | ------------- | ----------------------------------------------------- |
| BKPT            |           | 5             | none                                                  |
| BFC             |           | 6T2, 7-M      | C                                                     |
| BFI             |           | 6T2, 7-M      | C                                                     |
| CLZ             |           | 5             | `__clz`, `__builtin_clz`                              |
| DBG             |           | 7, 7-M        | `__dbg`                                               |
| DMB             |           | 8,7, 6-M      | `__dmb`                                               |
| DSB             |           | 8, 7, 6-M     | `__dsb`                                               |
| FRINT32Z        |           | 8-64          | `__rint32zf`, `__rint32z`                             |
| FRINT64Z        |           | 8-64          | `__rint64zf`, `__rint64z`                             |
| FRINT32X        |           | 8-64          | `__rint32xf`, `__rint32x`                             |
| FRINT64X        |           | 8-64          | `__rint64xf`, `__rint64x`                             |
| ISB             |           | 8, 7, 6-M     | `__isb`                                               |
| LDREX           |           | 6, 7-M        | `__sync_xxx`                                          |
| LDRT            |           | all           | none                                                  |
| MCR/MRC         |           | all           | see [System register access](#system-register-access) |
| MSR/MRS         |           | 6-M           | see [System register access](#system-register-access) |
| MSRR/MRRS       |           | 8-64          | see [System register access](#system-register-access) |
| PKHBT           |           | 6             | C                                                     |
| PKHTB           |           | 6             | C                                                     |
| PLD             |           | 8-32,5TE, 7-M | `__pld`                                               |
| PLDW            |           | 7-MP          | `__pldx`                                              |
| PLI             |           | 8-32,7        | `__pli`                                               |
| QADD            | Q         | 5E, 7E-M      | `__qadd`                                              |
| QADD16          |           | 6, 7E-M       | `__qadd16`                                            |
| QADD8           |           | 6, 7E-M       | `__qadd8`                                             |
| QASX            |           | 6, 7E-M       | `__qasx`                                              |
| QDADD           | Q         | 5E, 7E-M      | `__qadd(__qdbl)`                                      |
| QDSUB           | Q         | 5E, 7E-M      | `__qsub(__qdbl)`                                      |
| QSAX            |           | 6, 7E-M       | `__qsax`                                              |
| QSUB            | Q         | 5E, 7E-M      | `__qsub`                                              |
| QSUB16          |           | 6, 7E-M       | `__qsub16`                                            |
| QSUB8           |           | 6, 7E-M       | `__qsub8`                                             |
| RBIT            |           | 8,6T2, 7-M    | `__rbit`, `__builtin_rbit`                            |
| REV             |           | 8,6, 6-M      | `__rev`, `__builtin_bswap32`                          |
| REV16           |           | 8,6, 6-M      | `__rev16`                                             |
| REVSH           |           | 6, 6-M        | `__revsh`                                             |
| ROR             |           | all           | `__ror`                                               |
| SADD16          | GE        | 6, 7E-M       | `__sadd16`                                            |
| SADD8           | GE        | 6, 7E-M       | `__sadd8`                                             |
| SASX            | GE        | 6, 7E-M       | `__sasx`                                              |
| SBFX            |           | 8,6T2, 7-M    | C                                                     |
| SDIV            |           | 7-M+          | C                                                     |
| SEL             | (GE)      | 6, 7E-M       | `__sel`                                               |
| SETEND          |           | 6             | n/a                                                   |
| SEV             |           | 8,6K,6-M,7-M  | `__sev`                                               |
| SHADD16         |           | 6, 7E-M       | `__shadd16`                                           |
| SHADD8          |           | 6, 7E-M       | `__shadd8`                                            |
| SHASX           |           | 6, 7E-M       | `__shasx`                                             |
| SHSAX           |           | 6, 7E-M       | `__shsax`                                             |
| SHSUB16         |           | 6, 7E-M       | `__shsub16`                                           |
| SHSUB8          |           | 6, 7E-M       | `__shsub8`                                            |
| SMC             |           | 8,6Z, T2      | none                                                  |
| SMI             |           | 6Z, T2        | none                                                  |
| SMLABB          | Q         | 5E, 7E-M      | `__smlabb`                                            |
| SMLABT          | Q         | 5E, 7E-M      | `__smlabt`                                            |
| SMLAD           | Q         | 6, 7E-M       | `__smlad`                                             |
| SMLADX          | Q         | 6, 7E-M       | `__smladx`                                            |
| SMLAL           |           | all, 7-M      | C                                                     |
| SMLALBB         |           | 5E, 7E-M      | `__smulbb` and C                                      |
| SMLALBT         |           | 5E, 7E-M      | `__smulbt` and C                                      |
| SMLALTB         |           | 5E, 7E-M      | `__smultb` and C                                      |
| SMLALTT         |           | 5E, 7E-M      | `__smultt` and C                                      |
| SMLALD          |           | 6, 7E-M       | `__smlald`                                            |
| SMLALDX         |           | 6, 7E-M       | `__smlaldx`                                           |
| SMLATB          | Q         | 5E, 7E-M      | `__smlatb`                                            |
| SMLATT          | Q         | 5E, 7E-M      | `__smlatt`                                            |
| SMLAWB          | Q         | 5E, 7E-M      | `__smlawb`                                            |
| SMLAWT          | Q         | 5E, 7E-M      | `__smlawt`                                            |
| SMLSD           | Q         | 6, 7E-M       | `__smlsd`                                             |
| SMLSDX          | Q         | 6, 7E-M       | `__smlsdx`                                            |
| SMLSLD          |           | 6, 7E-M       | `__smlsld`                                            |
| SMLSLDX         |           | 6, 7E-M       | `__smlsldx`                                           |
| SMMLA           |           | 6, 7E-M       | C                                                     |
| SMMLAR          |           | 6, 7E-M       | C                                                     |
| SMMLS           |           | 6, 7E-M       | C                                                     |
| SMMLSR          |           | 6, 7E-M       | C                                                     |
| SMMUL           |           | 6, 7E-M       | C                                                     |
| SMMULR          |           | 6, 7E-M       | C                                                     |
| SMUAD           | Q         | 6, 7E-M       | `__smuad`                                             |
| SMUADX          | Q         | 6, 7E-M       | `__smuadx`                                            |
| SMULBB          |           | 5E, 7E-M      | `__smulbb;` C                                         |
| SMULBT          |           | 5E, 7E-M      | `__smulbt` ; C                                        |
| SMULTB          |           | 5E, 7E-M      | `__smultb;` C                                         |
| SMULTT          |           | 5E, 7E-M      | `__smultt;` C                                         |
| SMULL           |           | all, 7-M      | C                                                     |
| SMULWB          |           | 5E, 7E-M      | `__smulwb;` C                                         |
| SMULWT          |           | 5E, 7E-M      | `__smulwt;` C                                         |
| SMUSD           |           | 6, 7E-M       | `__smusd`                                             |
| SMUSDX          |           | 6, 7E-M       | `__smusd`                                             |
| SSAT            | Q         | 6, 7-M        | `__ssat`                                              |
| SSAT16          | Q         | 6, 7E-M       | `__ssat16`                                            |
| SSAX            | GE        | 6, 7E-M       | `__ssax`                                              |
| SSUB16          | GE        | 6, 7E-M       | `__ssub16`                                            |
| SSUB8           | GE        | 6, 7E-M       | `__ssub8`                                             |
| STREX           |           | 6, 7-M        | `__sync_xxx`                                          |
| STRT            |           | all           | none                                                  |
| SVC             |           | all           | none                                                  |
| SWP             |           | A32 only      | `__swp` [deprecated; see [Swap](#swap)]               |
| SXTAB           |           | 6, 7E-M       | `(int8_t)x` + a                                       |
| SXTAB16         |           | 6, 7E-M       | `__sxtab16`                                           |
| SXTAH           |           | 6, 7E-M       | `(int16_t)x` + a                                      |
| SXTB            |           | 8,6, 6-M      | `(int8_t)x`                                           |
| SXTB16          |           | 6, 7E-M       | `__sxtb16`                                            |
| SXTH            |           | 8,6, 6-M      | `(int16_t)x`                                          |
| UADD16          | GE        | 6, 7E-M       | `__uadd16`                                            |
| UADD8           | GE        | 6, 7E-M       | `__uadd8`                                             |
| UASX            | GE        | 6, 7E-M       | `__uasx`                                              |
| UBFX            |           | 8,6T2, 7-M    | C                                                     |
| UDIV            |           | 7-M+          | C                                                     |
| UHADD16         |           | 6, 7E-M       | `__uhadd16`                                           |
| UHADD8          |           | 6, 7E-M       | `__uhadd8`                                            |
| UHASX           |           | 6, 7E-M       | `__uhasx`                                             |
| UHSAX           |           | 6, 7E-M       | `__uhsax`                                             |
| UHSUB16         |           | 6, 7E-M       | `__uhsub16`                                           |
| UHSUB8          |           | 6, 7E-M       | `__uhsub8`                                            |
| UMAAL           |           | 6, 7E-M       | C                                                     |
| UMLAL           |           | all, 7-M      | `acc += (uint64_t)x * y`                              |
| UMULL           |           | all, 7-M      | C                                                     |
| UQADD16         |           | 6, 7E-M       | `__uqadd16`                                           |
| UQADD8          |           | 6, 7E-M       | `__uqadd8`                                            |
| UQASX           |           | 6, 7E-M       | `__uqasx`                                             |
| UQSAX           |           | 6, 7E-M       | `__uqsax`                                             |
| UQSUB16         |           | 6, 7E-M       | `__uqsub16`                                           |
| UQSUB8          |           | 6, 7E-M       | `__uqsub8`                                            |
| USAD8           |           | 6, 7E-M       | `__usad8`                                             |
| USADA8          |           | 6, 7E-M       | `__usad8 + acc`                                       |
| USAT            | Q         | 6, 7-M        | `__usat`                                              |
| USAT16          | Q         | 6, 7E-M       | `__usat16`                                            |
| USAX            |           | 6, 7E-M       | `__usax`                                              |
| USUB16          |           | 6, 7E-M       | `__usub16`                                            |
| USUB8           |           | 6, 7E-M       | `__usub8`                                             |
| UXTAB           |           | 6, 7E-M       | `(uint8_t)x + i`                                      |
| UXTAB16         |           | 6, 7E-M       | `__uxtab16`                                           |
| UXTAH           |           | 6, 7E-M       | `(uint16_t)x + i`                                     |
| UXTB16          |           | 6, 7E-M       | `__uxtb16`                                            |
| UXTH            |           | 8,6, 6-M      | `(uint16_t)x`                                         |
| VFMA            |           | VFPv4         | `fma`, `__fma`                                        |
| VSQRT           |           | VFP           | `sqrt`, `__sqrt`                                      |
| WFE             |           | 8,6K, 6-M     | `__wfe`                                               |
| WFI             |           | 8,6K, 6-M     | `__wfi`                                               |
| YIELD           |           | 8,6K, 6-M     | `__yield`                                             |

# About FP8 intrinsics

The specification for FP8 intrinsics is in
[**Beta** state](#support-levels).

Each 8-bit floating point intrinsic call has a parameter to define the format
and scale of the operands, and the overflow behavior, as applicable to each
operation. This parameter is typically declared as `fpm_t fpm`.

```c
  typedef uint64_t fpm_t;
```

The bits of an argument to an `fpm` parameter are interpreted as follows:

| **Bit range** | **Name**       | **Meaning**                                                        |
| ------------- | -------------- | ------------------------------------------------------------------ |
| 0-2           | `src1_format`  | first source operand format:  0 - FP8 E5M2, 1 - FP8 E4M3           |
| 3-5           | `src2_format`  | second source operand format: 0 - FP8 E5M2, 1 - FP8 E4M3           |
| 6-8           | `dst_format`   | destination format: 0  - FP8 E5M2, 1 - FP8 E4M3                    |
| 9-13          |                | must be zero                                                       |
| 14            | `overflow_mul` | overflow behavior for multiplication instructions:                 |
|               |                |   0 - generate infinity, 1 - generate maximum normal number        |
| 15            | `overflow_cvt` | overflow behavior for conversion instructions:                     |
|               |                |   0 - generate infinity or NaN, 1 - generate maximum normal number |
| 16-22         | `lscale`       | downscaling value                                                  |
| 23            |                | must be zero                                                       |
| 24-31         | `nscale`       | scaling value for conversions                                      |
| 32-37         | `lscale2`      | downscaling value for conversions of the second input stream       |
| 38-63         |                | must be zero                                                       |

Bit patterns other than those described in this table are invalid. Passing an invalid value as an argument
to an FP8 intrinsic results in undefined behavior.

The ACLE declares several helper types and intrinsics to
facilitate construction of `fpm` arguments. The helper intrinsics do not have
side effects and their return values depend only on their parameters.

Passing an out of range argument to a helper intrinsic results in the intrinsic
returning an indeterminate value. Passing such an indeterminate value as
an argument to an FP8 intrinsic results in undefined behavior.

The helper types and intrinsics are available after including any of
[`<arm_neon.h>`](#arm_neon.h), [`<arm_sve.h>`](#arm_sve.h), or
[`<arm_sme.h>`](#arm_sme.h).

Note: where a helper intrinsic description refers to updating the FP8 mode it
means the intrinsic only modifies the bits of the input `fpm_t` parameter that
correspond to the new mode and returns the resulting value. No side effects, such
as changing processor state, occur.

Individual FP8 intrinsics are described in their respective
Advanced SIMD (Neon), SVE, and SME sections.

## Support enumerations

```c
enum __ARM_FPM_FORMAT {
  __ARM_FPM_E5M2,
  __ARM_FPM_E4M3,
};

enum __ARM_FPM_OVERFLOW {
  __ARM_FPM_INFNAN,
  __ARM_FPM_SATURATE,
};
```

## Helper intrinsics

```c
  fpm_t __arm_fpm_init();
```
Initializes a value, suitable for use as an `fpm` argument in FP8 mode.
The value corresponds to a mode of operation where:
  * The source and destination operands are interpreted as E5M2.
  * Overflow behavior is to yield infinity or NaN, depending on operation.
  * No scaling occurs.

```c
  fpm_t __arm_set_fpm_src1_format(fpm_t fpm, enum __ARM_FPM_FORMAT format);
  fpm_t __arm_set_fpm_src2_format(fpm_t fpm, enum __ARM_FPM_FORMAT format);
```
Updates the FP8 mode to set the first or the second source operand format,
respectively.

```c
  fpm_t __arm_set_fpm_dst_format(fpm_t fpm,  enum __ARM_FPM_FORMAT format);
```
Updates the FP8 mode to set the destination format.

```c
  fpm_t __arm_set_fpm_overflow_cvt(fpm_t fpm, enum __ARM_FPM_OVERFLOW behavior);
```
Updates the FP8 mode to set the overflow behavior for conversion operations.

``` c
  fpm_t __arm_set_fpm_overflow_mul(fpm_t fpm, enum __ARM_FPM_OVERFLOW behavior);
```
Updates the FP8 mode to set the overflow behavior for multiplicative
operations.

``` c
  fpm_t __arm_set_fpm_lscale(fpm_t fpm, uint64_t scale);
```
Updates the FP8 mode to set the downscaling value subtracted from:
* The product or the sum-of-products exponent, for multiplication instructions
  with FP8 operands.
* The result exponent, for instructions converting the first FP8
  input data stream to other floating-point formats.

The valid range for the `scale` parameter is [0, 127], inclusive.

``` c
  fpm_t __arm_set_fpm_lscale2(fpm_t fpm, uint64_t scale);
```
Updates the FP8 mode to set the downscaling value subtracted from the
result exponent for instructions converting the second FP8 input data
stream to other floating-point formats.

The valid range for the `scale` parameter is [0, 63], inclusive.

``` c
  fpm_t __arm_set_fpm_nscale(fpm_t fpm,  int64_t scale);
```
Updates the FP8 mode to set the scaling value added to the operand's
exponent for instructions converting other floating-point formats to an
FP8 format.

The valid range for the `scale` parameter is [-128, 127], inclusive.

# Advanced SIMD (Neon) intrinsics

## Introduction

The Advanced SIMD instructions provide packed Single Instruction
Multiple Data (SIMD) and single-element scalar operations on a range
of integer and floating-point types.

Neon is an implementation of the Advanced SIMD instructions which is
provided as an extension for some Cortex-A Series processors. Where this
document refers to Neon instructions, such instructions refer to the Advanced
SIMD instructions as described by the Arm Architecture Reference Manual
[[ARMARMv8]](#ARMARMv8).

The Advanced SIMD extension provides for arithmetic, logical and saturated
arithmetic operations on 8-bit, 16-bit and 32-bit integers (and sometimes
on 64-bit integers) and on 32-bit and 64-bit floating-point data, arranged
in 64-bit and 128-bit vectors.

The intrinsics in this section provide C and C++ programmers with a
simple programming model allowing easy access to code-generation of the
Advanced SIMD instructions for both AArch64 and AArch32 execution states.

<span id="neon-intrinsics-concepts"></span>

### Concepts

The Advanced SIMD instructions are designed to improve the performance of
multimedia and signal processing algorithms by operating on 64-bit or 128-bit
*vectors* of *elements* of the same *scalar* data type.

For example, `uint16x4_t` is a 64-bit vector type consisting of four
elements of the scalar `uint16_t` data type. Likewise, `uint16x8_t` is
a 128-bit vector type consisting of eight `uint16_t` elements.

In a vector programming model, operations are performed in parallel across
the elements of the vector. For example, `vmul_u16(a, b)` is a vector
intrinsic which takes two `uint16x4_t` vector arguments `a` and `b`,
and returns the result of multiplying corresponding elements from each vector
together.

The Advanced SIMD extension also provides support for *vector-by-lane*
and *vector-by-scalar* operations. In these operations, a scalar value
is extracted from one element of a vector input, or provided directly,
duplicated to create a new vector with the same number of elements as an
input vector, and an operation is performed in parallel between
this new vector and other input vectors.

For example, `vmul_lane_u16(a, b, 1)`, is a vector-by-lane intrinsic
which takes two `uint16x4_t` vector elements. From `b`, element
`1` is extracted, a new vector is formed which consists of four
copies of element `1` of `b`, and this new vector is multiplied by
`a`.

*Reduction*, *cross-lane*, and *pairwise* vector operations work on pairs
of elements within a vector, or across the whole of a single vector
performing the same operation between elements of that vector. For example,
`vaddv_u16(a)` is a reduction intrinsic which takes a `uint16x4_t`
vector, adds each of the four `uint16_t` elements together, and returns
a `uint16_t` result containing the sum.

### Vector data types

Vector data types are named as a lane type and a multiple. Lane type
names are based on the types defined in `<stdint.h>`. For example,
`int16x4_t` is a vector of four `int16_t` values. The base types are
`int8_t`, `uint8_t`, `int16_t`, `uint16_t`, `int32_t`, `uint32_t`,
`int64_t`, `uint64_t`, `float16_t`, `float32_t`, `poly8_t`, `poly16_t`,
`poly64_t`, `poly128_t`, and `bfloat16_t`. The multiples are such that the
resulting vector types are 64-bit and 128-bit. In AArch64, `float64_t`
and `mfloat8_t` are also base types.

Not all types can be used in all operations. Generally, the operations
available on a type correspond to the operations available on the
corresponding scalar type.

ACLE does not define whether `int64x1_t` is the same type as `int64_t`,
or whether `uint64x1_t` is the same type as `uint64_t`, or whether
`poly64x1_t` is the same as `poly64_t` for example for C++ overloading
purposes.

float16 types are only available when the `__fp16` type is defined, that is,
when supported by the hardware.

bfloat types are only available when the `__bf16` type is defined, that is,
when supported by the hardware. The bfloat types are all opaque types. That is,
they can only be used by intrinsics.

The FP8 types are all opaque types. That is, they can only be used by
intrinsics.

### Advanced SIMD Scalar data types

AArch64 supports Advanced SIMD scalar operations that work on standard
scalar data types viz. `int8_t`, `uint8_t`, `int16_t`, `uint16_t`,
`int32_t`, `uint32_t`, `int64_t`, `uint64_t`, `float32_t`,
`float64_t`.

### Vector array data types

Array types are defined for multiples of 2, 3 or 4 of all the vector
types, for use in load and store operations, in table-lookup operations,
and as the result type of operations that return a pair of vectors. For
a vector type `<type>_t` the corresponding array type is
`<type>x<length>_t`. Concretely, an array type is a structure containing
a single array element called val.

For example an array of two `int16x4_t` types is `int16x4x2_t`, and is
represented as

``` c
  struct int16x4x2_t { int16x4_t val[2]; };
```

Note that this array of two 64-bit vector types is distinct from the
128-bit vector type `int16x8_t`.

### Scalar data types

For consistency, `<arm_neon.h>` defines some additional scalar data types
to match the vector types.

`float32_t` is defined as an alias for `float`.

If the `__fp16` type is defined, `float16_t` is defined as an alias for
it.

If the `__bf16` type is defined, `bfloat16_t` is defined as an alias for it.

If the `__mfp8` type is defined, `mfloat8_t` is defined as an alias for it.

`poly8_t`, `poly16_t`, `poly64_t` and `poly128_t` are defined as
unsigned integer types. It is unspecified whether these are the same type as
`uint8_t`, `uint16_t`, `uint64_t` and `uint128_t` for overloading and
mangling purposes.

`float64_t` is defined as an alias for `double`.

<span id="16-bit-floating-point-arithmetic-scalar-intrinsics"></span>

### 16-bit floating-point arithmetic scalar intrinsics

The architecture extensions introduced by Armv8.2-A [[ARMARMv82]](#ARMARMv82) provide a set
of data processing instructions which operate on 16-bit floating-point
quantities. These instructions are available in both AArch64 and AArch32
execution states, for both Advanced SIMD and scalar floating-point values.

ACLE defines two sets of intrinsics which correspond to these data
processing instructions; a set of scalar intrinsics, and a set of
vector intrinsics.

The intrinsics introduced in this section use the data types defined
by ACLE. In particular, scalar intrinsics use the `float16_t` type
defined by ACLE as an alias for the `__fp16` type, and vector intrinsics
use the `float16x4_t` and `float16x8_t` vector types.

Where the scalar 16-bit floating point intrinsics are available,
an implementation is required to ensure that including
`<arm_neon.h>` has the effect of also including `<arm_fp16.h>`.

To only enable support for the scalar 16-bit floating-point intrinsics,
the header `<arm_fp16.h>` may be included directly.

<span id="16-bit-brain-floating-point-arithmetic-scalar-intrinsics"></span>

### 16-bit brain floating-point arithmetic scalar intrinsics

The architecture extensions introduced by Armv8.6-A [[Bfloat16]](#Bfloat16) provide a set
of data processing instructions which operate on brain 16-bit floating-point
quantities. These instructions are available in both AArch64 and AArch32
execution states, for both Advanced SIMD and scalar floating-point values.

The brain 16-bit floating-point format (bfloat) differs from the older 16-bit
floating-point format (float16) in that the former has an 8-bit exponent similar
to a single-precision floating-point format but has a 7-bit fraction.

ACLE defines two sets of intrinsics which correspond to these data
processing instructions; a set of scalar intrinsics, and a set of
vector intrinsics.

The intrinsics introduced in this section use the data types defined
by ACLE. In particular, scalar intrinsics use the `bfloat16_t` type
defined by ACLE as an alias for the `__bf16` type, and vector intrinsics
use the `bfloat16x4_t` and `bfloat16x8_t` vector types.

Where the 16-bit brain floating point intrinsics are available,
an implementation is required to ensure that including
`<arm_neon.h>` has the effect of also including `<arm_bf16.h>`.

To only enable support for the 16-bit brain floating-point intrinsics,
the header `<arm_bf16.h>` may be included directly.

When `__ARM_BF16_FORMAT_ALTERNATIVE` is defined to `1` then these types are
storage only and cannot be used with anything other than ACLE intrinsics.  The
underlying type for them is `uint16_t`.

### Operations on data types

ACLE does not define implicit conversion between different data types.
For example:

``` c
  int32x4_t x;
  uint32x4_t y = x; // No representation change
  float32x4_t z = x; // Conversion of integer to floating type
```

Is not portable. Use the `vreinterpret` intrinsics to convert from one
vector type to another without changing representation, and use the `vcvt`
intrinsics to convert between integer and floating types; for example:

``` c
  int32x4_t x;
  uint32x4_t y = vreinterpretq_u32_s32(x);
  float32x4_t z = vcvt_f32_s32(x);
```

ACLE does not define static construction of vector types. For instance:

``` c
  int32x4_t x = { 1, 2, 3, 4 };
```

Is not portable. Use the `vcreate` or `vdup` intrinsics to construct values
from scalars.

In C++, ACLE does not define whether Advanced SIMD data types are POD types
or whether they can be inherited from.

### Compatibility with other vector programming models

ACLE does not specify how the Advanced SIMD Intrinsics interoperate with
alternative vector programming models. Consequently, programmers should
take particular care when combining the Advanced SIMD Intrinsics
programming model with such programming models.

For example, the GCC vector extensions permit initializing a variable using
array syntax, as so

``` c
  #include "arm_neon.h"
  ...
  uint32x2_t x = {0, 1}; // GCC extension.
  uint32_t y = vget_lane_s32 (x, 0); // ACLE Neon Intrinsic.
```

But the definition of the GCC vector extensions is such that the value
stored in y will depend on both the target architecture (AArch32 or AArch64)
and whether the program is running in big- or little-endian mode.

It is recommended that Advanced SIMD Intrinsics be used consistently:

``` c
  #include "arm_neon.h"
  ...
  const int temp[2] = {0, 1};
  uint32x2_t x = vld1_s32 (temp);
  uint32_t y = vget_lane_s32 (x, 0);
```

## Availability of Advanced SIMD intrinsics and Extensions

### Availability of Advanced SIMD intrinsics

Advanced SIMD support is available if the `__ARM_NEON` macro is
predefined (see [Advanced SIMD architecture extension
(Neon)](#advanced-simd-architecture-extension-neon)). In order
to access the Advanced SIMD intrinsics, it is necessary to include
the `<arm_neon.h>` header.

``` c
  #if __ARM_NEON
  #include <arm_neon.h>
    /* Advanced SIMD intrinsics are now available to use.  */
  #endif
```

Some intrinsics are only available when compiling for the AArch64
execution state. This can be determined using the `__ARM_64BIT_STATE`
predefined macro (see [Instruction set
architecture (A32/T32/A64)](#instruction-set-architecture-a32t32a64)).

### Availability of 16-bit floating-point vector interchange types

When the 16-bit floating-point data type `__fp16` is available as an
interchange type for scalar values, it is also available in the vector
interchange types `float16x4_t` and `float16x8_t`. When the vector
interchange types are available, conversion intrinsics between
vector of `__fp16` and vector of `float` types are provided.

This is indicated by the setting of bit 1 in `__ARM_NEON_FP`
(see [Neon floating-point](#neon-floating-point)).

``` c
  #if __ARM_NEON_FP & 0x1
    /* 16-bit floating point vector types are available.  */
    float16x8_t storage;
  #endif
```

### Availability of fused multiply-accumulate intrinsics

Whenever fused multiply-accumulate is available for scalar operations, it is
also available as a vector operation in the Advanced SIMD extension. When
a vector fused multiply-accumulate is available, intrinsics are defined to
access it.

This is indicated by `__ARM_FEATURE_FMA` (see [Fused multiply-accumulate
(FMA)](#fused-multiply-accumulate-fma)).

``` c
  #if __ARM_FEATURE_FMA
    /* Fused multiply-accumulate intrinsics are available.  */
    float32x4_t a, b, c;
    vfma_f32 (a, b, c);
  #endif
```

### Availability of Armv8.1-A Advanced SIMD intrinsics

The Armv8.1-A [[ARMARMv81]](#ARMARMv81) architecture introduces two new instructions:
SQRDMLAH and SQRDMLSH. ACLE specifies vector and vector-by-lane intrinsics to
access these instructions where they are available in hardware.

This is indicated by `__ARM_FEATURE_QRDMX` (see [Rounding doubling
multiplies](#rounding-doubling-multiplies)). :

``` c
  #if __ARM_FEATURE_QRDMX
    /* Armv8.1-A RDMA extensions are available.  */
    int16x4_t a, b, c;
    vqrdmlah_s16 (a, b, c);
  #endif
```

### Availability of 16-bit floating-point arithmetic intrinsics

Armv8.2-A [[ARMARMv82]](#ARMARMv82) introduces new data processing instructions which
operate on 16-bit floating point data in the IEEE754-2008 [IEEE-FP]
format. ACLE specifies intrinsics which map to the vector forms of these
instructions where they are available in hardware.

This is indicated by `__ARM_FEATURE_FP16_VECTOR_ARITHMETIC`
(see [16-bit floating-point data processing
operations](#16-bit-floating-point-data-processing-operations)). :

``` c
  #if __ARM_FEATURE_FP16_VECTOR_ARITHMETIC
    float16x8_t a, b;
    vaddq_f16 (a, b);
  #endif
```

ACLE also specifies intrinsics which map to the scalar forms of these
instructions, see [16-bit floating-point arithmetic scalar
intrinsics](#16-bit-floating-point-arithmetic-scalar-intrinsics).
Availability of the scalar intrinsics is indicated by
`__ARM_FEATURE_FP16_SCALAR_ARITHMETIC`.

``` c
  #if __ARM_FEATURE_FP16_SCALAR_ARITHMETIC
    float16_t a, b;
    vaddh_f16 (a, b);
  #endif
```

### Availability of 16-bit brain floating-point arithmetic intrinsics

Armv8.2-A [[ARMARMv82]](#ARMARMv82) introduces new data processing instructions which
operate on 16-bit brain floating point data as described in the Arm
Architecture Reference Manual. ACLE specifies intrinsics which map to the vector
forms of these instructions where they are available in hardware.

This is indicated by `__ARM_FEATURE_BF16_VECTOR_ARITHMETIC`
(see [Brain 16-bit floating-point
support](#brain-16-bit-floating-point-support)).

``` c
  #if __ARM_FEATURE_BF16_VECTOR_ARITHMETIC
    float32x2_t res = {0};
    bfloat16x4_t a' = vld1_bf16 (a);
    bfloat16x4_t b' = vld1_bf16 (b);
    res = vdot_bf16 (res, a', b');
  #endif
```

ACLE also specifies intrinsics which map to the scalar forms of these
instructions, see [16-bit brain floating-point arithmetic scalar
intrinsics](#16-bit-brain-floating-point-arithmetic-scalar-intrinsics).
Availability of the scalar intrinsics is indicated by
`__ARM_FEATURE_BF16_SCALAR_ARITHMETIC`.

``` c
  #if __ARM_FEATURE_BF16_SCALAR_ARITHMETIC
    bfloat16_t a;
    float32_t b = ..;
    a = b<convert> (b);
  #endif
```

### Availability of Armv8.4-A Advanced SIMD intrinsics

New Crypto and FP16 Floating Point Multiplication Variant instructions in
Armv8.4-A:

* New SHA512 crypto instructions (available if `__ARM_FEATURE_SHA512`)
* New SHA3 crypto instructions (available if `__ARM_FEATURE_SHA3`)
* SM3 crypto instructions (available if `__ARM_FEATURE_SM3`)
* SM4 crypto instructions (available if `__ARM_FEATURE_SM4`)
* New FML[A\|S] instructions (available if `__ARM_FEATURE_FP16_FML`).

These instructions have been backported as optional instructions to Armv8.2-A
and Armv8.3-A.

### Availability of Dot Product intrinsics

The architecture extensions introduced by Armv8.2-A provide a set of dot product
instructions which operate on 8-bit sub-element quantities. These instructions
are available in both AArch64 and AArch32 execution states using
Advanced SIMD instructions. These intrinsics are available
when `__ARM_FEATURE_DOTPROD` is defined (see [Dot Product
extension](#dot-product-extension)). :

``` c
  #if __ARM_FEATURE_DOTPROD
    uint8x8_t a, b;
    vdot_u8 (a, b);
  #endif
```

### Availability of Armv8.5-A floating-point rounding intrinsics

The architecture extensions introduced by Armv8.5-A provide a set of
floating-point rounding instructions that round a floating-point number to an
to a floating-point value that would be representable in a 32-bit or 64-bit
signed integer type.
NaNs, Infinities and Out-of-Range values are forced to the
Most Negative Integer representable in the target size, and an
Invalid Operation Floating-Point Exception is generated.
These instructions are available only in the AArch64 execution state.
The intrinsics for these are available when `__ARM_FEATURE_FRINT` is defined.
The Advanced SIMD intrinsics are specified in the Arm Neon Intrinsics
Reference Architecture Specification [[Neon]](#Neon).

### Availability of Armv8.6-A Integer Matrix Multiply intrinsics

The architecture extensions introduced by Armv8.6-A provide a set of
integer matrix multiplication and mixed sign dot product instructions.
These instructions are optional from Armv8.2-A to Armv8.5-A.

These intrinsics are available when `__ARM_FEATURE_MATMUL_INT8` is defined
(see [Matrix Multiply Intrinsics](#matrix-multiply-intrinsics)).

## Specification of Advanced SIMD intrinsics

The Advanced SIMD intrinsics are specified in the Arm Neon Intrinsics
Reference Architecture Specification [[Neon]](#Neon).

The behavior of an intrinsic is specified to be equivalent to the
AArch64 instruction it is mapped to in [[Neon]](#Neon). Intrinsics are specified
as a mapping between their name, arguments and return values and the AArch64
instruction and assembler operands which they are equivalent to.

A compiler may make use of the as-if rule from C [[C99]](#C99) (5.1.2.3) to perform
optimizations which preserve the instruction semantics.

## Undefined behavior

Care should be taken by compiler implementers not to introduce the concept of
undefined behavior to the semantics of an intrinsic. For example, the
`vabsd_s64` intrinsic has well defined behavior for all input values,
while the C99 `llabs` has undefined behavior if the result would not
be representable in a `long long` type. It would thus be incorrect to
implement `vabsd_s64` as a wrapper function or macro around `llabs`.

## Alignment assertions

The AArch32 Neon load and store instructions provide for alignment
assertions, which may speed up access to aligned data (and will fault
access to unaligned data). The Advanced SIMD intrinsics do not directly
provide a means for asserting alignment.

# SVE language extensions and intrinsics

## SVE introduction

The Scalable Vector Extension (SVE) was introduced as an optional extension
to the Arm8.2-A architecture. Its associated feature flag is FEAT_SVE.
SVE has since been extended further by features such as Armv8.6-A's
matrix multiplication extensions and Armv9-A's SVE2.

For brevity, this document generally uses “SVE” to refer to the original
FEAT_SVE version of SVE and all subsequent extensions to it. For example,
references to “SVE” include “SVE2” except whether otherwise noted.

ACLE defines a set of C and C++ types and accessors for SVE vectors
and predicates. It also defines intrinsics for almost all SVE
instructions. [Mapping of SVE instructions to
intrinsics](#mapping-of-sve-instructions-to-intrinsics) lists each SVE
instruction and links to the corresponding ACLE intrinsic (if one exists).

However, the intrinsic interface is more general than the underlying
architecture, so not every intrinsic maps directly to an architectural
instruction. The intention is to provide a regular interface and leave
the ACLE implementation to pick the best mapping to SVE instructions.

## SVE types

### Overview of SVE types

SVE is a “vector-length agnostic” architecture. Instead of mandating a
particular vector length, it allows implementations to choose any
multiple of 128 bits up to the architectural maximum of 2048 bits. It
also allows higher exception levels to constrain the vector lengths of
lower exception levels. The effective vector length is therefore not a
compile-time constant and can in principle change during execution.

Although the architectural increment is 128 bits, it is often more
natural to think in terms of 64-bit quantities. The term “VG” (“vector
granules”) refers to the current number of 64-bit elements in an SVE
vector, so that the number of usable bits in a vector is VG×64.
Predicates have one bit for each vector byte, so the number of
usable bits in a predicate is VG×8.

Therefore, code that makes direct use of SVE instructions requires access
to vector types that have VG×64 bits and predicate types that have VG×8
bits, but without the value of VG being fixed. Ideally it should be
possible to pass and return these types by value, like it is for other
(fixed-length) vector extensions. However, standard C and C++ do not
provide variable-length types that are both self-contained (rather than
dependent on separate storage) and suitable for passing and returning by
value. (For example, C's variable-length arrays are self-contained but
are not valid return types. C++'s `std::string` can store variable-length
data and is suitable for passing and returning by value, but it relies
on separately-allocated storage.) This means that there is no existing
mechanism that maps directly to the concept of an SVE vector or predicate.

Any approach to defining the types would fall into one of three
categories:

1.  Limit the types in such a way that there is no concept of size.

2.  Define the size of the types to be variable.

3.  Define the size of the types to be constant, with the constant being
    large enough for all possible VG or with the types pointing to
    separate memory (as for classes like `std::string`).

ACLE takes the first approach and classifies SVE vectors and
predicates as belonging to a new category of type called “sizeless types”.
The next section describes these types in more detail.

### Sizeless types

For the reasons explained in the previous section, ACLE defines a
new category of type called “sizeless types”. They are less restrictive
than the standard “incomplete types” but more restrictive than ”complete
types”. SVE vectors and predicates have sizeless type.

#### Informal definition of sizeless types

Informally, sizeless types can be used in the following situations:

*   as the type of an object with automatic storage duration;

*   as a function parameter or return type;

*   as a type name in a `_Generic` association;

*   as the type in a `(type) {value}` compound literal;

*   as the type in a C++ `type()` expression;

*   as the target of a pointer or reference type; and

*   as a template type argument.

Sizeless types may not be used in the following situations:

*   as the type of a variable with static or thread-local storage
    duration (regardless of whether the variable is being defined or just
    declared);

*   as the type of an array element;

*   as the operand to a `new` expression; and

*   as the type of object being deleted by a `delete` expression.

In all other respects, sizeless types have the same restrictions as the
standard-defined “incomplete types”. This specifically includes (but is
not limited to) the following:

*   The argument to `sizeof` and `_Alignof` cannot be a sizeless
    type, or an object of sizeless type.

*   It is not possible to perform arithmetic on pointers to sizeless
    types. (This affects the `+`, `-`, `++` and `--` operators.)

*   Members of unions, structures and classes cannot have sizeless type.

*   `_Atomic` variables cannot have sizeless type.

*   It is not possible to throw or catch objects of sizeless type.

*   Lambda expressions cannot capture sizeless types by value, although
    they can capture them by reference. (This is a corollary of not
    allowing member variables to have sizeless type.)

*   Standard library containers like `std::vector` cannot have a
    sizeless `value_type`.

#### Formal definition of sizeless types

[Sizeless types in C](#sizeless-types-in-c) gives a more formal
definition of sizeless types for C, in the form of an edit to the
standard. [Sizeless types in C++](#sizeless-types-in-cxx) gives the
corresponding changes for C++. Implementations should correctly compile
any code that follows these rules, but they do not need to report a
diagnostic for invalid uses of sizeless types. Whether they report a
diagnostic or not is a quality of implementation issue.
(Note: future versions of ACLE might have stricter diagnostic
requirements.)

##### Sizeless types in C

This section specifies the behavior of sizeless types as an edit to the
N1570 version of the C standard.

**6.2.5 Types**

> In 6.2.5/1, replace:
>
> > At various points within a translation unit an object type may
> > be *incomplete* ...
>
> onwards with:
>
> > Object types are further partitioned into *sized* and *sizeless*;
> > all basic and derived types defined in this standard are sized,
> > but an implementation may provide additional sizeless types.
>
> and add two additional clauses:
>
> > *   At various points within a translation unit an object type
> >     may be *indefinite* (lacking sufficient information to
> >     construct an object of that type) or *definite* (having
> >     sufficient information). An object type is said to be
> >     *complete* if it is both sized and definite; all other object
> >     types are said to be *incomplete*. Complete types have
> >     sufficient information to determine the size of an object of
> >     that type while incomplete types do not.
> >
> > *   Arrays, structures, unions and enumerated types are always
> >     sized, so for them the term *incomplete* is equivalent to (and
> >     used interchangeably with) the term *indefinite*.
>
> Change 6.2.5/19 to:
>
> > The `void` type comprises an empty set of values; it is a
> > sized indefinite object type that cannot be completed (made
> > definite).
>
> Replace *incomplete* with *indefinite* and *complete* with *definite* in
> 6.2.5/37, which describes how a type's state can change throughout a
> translation unit.

**6.3.2.1 Lvalues, arrays, and function designators**

> Replace *incomplete* with *indefinite* in 6.3.2.1/1, so that sizeless
> definite types are modifiable lvalues.
>
> Make the same replacement in 6.3.2.1/2, to prevent undefined
> behavior when lvalues have sizeless definite type.

**6.5.1.1 Generic selection**

> Replace *complete object type* with *definite object type* in 6.5.1.1/2,
> so that the type name in a generic association can be a sizeless
> definite type.

**6.5.2.2 Function calls**

> Replace *complete object type* with *definite object type* in 6.5.2.2/1,
> so that functions can return sizeless definite types.
>
> Make the same change in 6.5.2.2/4, so that arguments can also have
> sizeless definite type.

**6.5.2.5 Compound literals**

> Replace *complete object type* with *definite object type* in 6.5.2.5/1,
> so that compound literals can have sizeless definite type.

**6.7 Declarations**

> Insert the following new clause after 6.7/4:
>
> > *   If an identifier for an object does not have automatic storage
> >     duration, its type must be sized rather than sizeless.
>
> Replace *complete* with *definite* in 6.7/7, which describes when the
> type of an object becomes definite.

**6.7.6.3 Function declarators (including prototypes)**

> Replace *incomplete type* with *indefinite type* in 6.7.6.3/4, so that
> parameters can also have sizeless definite type.
>
> Make the same change in 6.7.6.3/12, which allows even indefinite
> types to be function parameters if no function definition is
> present.

**6.7.9 Initialization**

> Replace *complete object type* with *definite object type* in 6.7.9/3,
> to allow initialization of identifiers with sizeless definite type.

**6.9.1 Function definitions**

> Replace *complete object type* with *definite object type* in 6.9.1/3,
> so that functions can return sizeless definite types.
>
> Make the same change in 6.9.1/7, so that adjusted parameter types
> can be sizeless definite types.

**J.2 Undefined behavior**

> Update the entries that refer to the clauses above.

<span id="sizeless-types-in-cxx"></span>

##### Sizeless types in C++

This section specifies the behavior of sizeless types as an edit to the
N3797 version of the C++ standard.

**3.1 Declarations and definitions [basic.def]**

> Replace *incomplete type* with *indefinite type* in 3.1/5, so that
> objects can have sizeless definite type in some situations. Add a
> new clause immediately afterwards:
>
> > *   A program is ill-formed if any declaration of an object gives
> >     it both a sizeless type and either static or thread-local
> >     storage duration.

**3.9 Types [basic.types]**

> Replace 3.9/5 with these clauses:
>
> > *   A class that has been declared but not defined, an
> >     enumeration type in certain contexts, or an array of unknown
> >     size or of indefinite element type, is an *indefinite object type*.
> >     Indefinite object types and the void types are *indefinite types*.
> >     Objects shall not be defined to have an indefinite type.
> >
> > *   Object and void types are further partitioned into *sized*
> >     and *sizeless*; all basic and derived types defined in this
> >     standard are sized, but an implementation may provide
> >     additional sizeless types.
> >
> > *   An object or void type is said to be *complete* if it is both
> >     sized and definite; all other object and void types are said
> >     to be *incomplete*. The term *completely-defined object type*
> >     is synonymous with *complete object type*.
> >
> > *   Arrays, class types and enumeration types are always sized,
> >     so for them the term *incomplete* is equivalent to (and used
> >     interchangeably with) the term *indefinite*.
>
> Replace *incomplete types* with *indefinite types* in 3.9/7, which is
> simply a cross-reference note.

**3.9.1 Fundamental Types [basic.fundamental]**

> Replace the second sentence of 3.9.1/9 with:
>
> > The `void` type is a sized indefinite type that cannot be
> > completed (made definite).

**3.9.2. Compound Types [basic.compound]**

> Add “(including indefinite types)” after “Pointers to incomplete
> types” in 3.9.2/3, to emphasize that pointers to incomplete types
> are more restricted than pointers to complete types, even if the
> types are definite.

**3.10 Lvalues and rvalues [basic.lval]**

> Replace *complete types* with *definite types* and *incomplete types*
> with *indefinite types* in 3.10/4, so that prvalues can be sizeless
> definite types.
>
> Replace *incomplete* with *indefinite* and *complete* with *definite*
> in 3.10/7, which describes the modifiability of a pointer and the
> object to which it points.

**4.1 Lvalue-to-rvalue conversion [conv.lval]**

> Replace *incomplete type* with *indefinite type* in 4.1/1, so that
> glvalues of sizeless definite type can be converted to prvalues.

**5.2.2 Function call [expr.call]**

> Replace *completely-defined object type* with *definite object type*
> and *incomplete class type* with *indefinite class type*,
> so that parameters can have sizeless definite type.
>
> Replace *incomplete* with *indefinite* and *complete* with *definite*
> in 5.2.2/11, so that functions can return sizeless definite types.

**5.2.3 Explicit type conversion (function notation) [expr.type.conv]**

> Replace *complete object type* with *definite object type* in 5.2.3/2,
> so that the `T()` notation extends to sizeless definite types.

**5.3.1 Unary operators [expr.unary.op]**

> Replace *incomplete type* with *indefinite type* in 5.3.1/1. This simply
> updates a cross-reference to the 4.1 change above.

**5.3.5 Delete [expr.delete]**

> Insert the following after the first sentence of 5.3.5/2 (which
> describes the implicit conversion of an object type to a pointer type):
>
> > The type of the operand must now be a pointer to a sized type,
> > otherwise the program is ill-formed.

**8.3.4 Arrays [dcl.array]**

> In 8.3.4/1, add *a sizeless type* to the list of types that the
> element type `T` cannot have.

**9.4.2 Static data members [class.static.data]**

> Replace *an incomplete type* with *a sized indefinite type* in 9.4.2/2,
> so that static data members cannot be declared with sizeless type.
>
> Add a new final clause:
>
> > * A static data member shall not have sizeless type.

**14.3.1 Template type parameters [temp.arg.type]**

> Add “(including an indefinite type)” after “an incomplete type” in
> the note describing template type arguments, to emphasize that the
> arguments can be sizeless.

**20.10.4.3 Type properties [meta.unary.prop]**

> Replace *complete* with *definite* in 20.10.4.3/3, so that the
> situations in which an implementation may implicitly instantiate
> template arguments remain the same as before.

**20.10.6 Relationships between types [meta.rel]**

> Replace *complete* with *definite* in 20.10.6/2, so that these
> metaprogramming facilities extend to sized definite types.

**20.10.7.5 Pointer modifications [meta.trans.ptr]**

> Likewise replace *complete* with *definite* in the initial table, so
> that these metaprogramming facilities also extend to sized definite types.

#### Interaction between sizeless types and other extensions

It is not feasible to reconcile the definition of sizeless types with
each individual current and future extension to C and C++. Therefore,
the default position is that extensions to C and C++ should treat sizeless
types as incomplete types unless otherwise specified.

### Scalar types defined by `<arm_sve.h>`

[`<arm_sve.h>`](#arm_sve.h) includes `<stdint.h>` and so provides
standard types such as `uint32_t`. When included from C code, the header
also includes `<stdbool.h>` and so provides the `bool` type.

In addition, the header file defines the following scalar data types:

| **Scalar type** | **Definition**         |
| --------------- | ---------------------- |
| `float16_t`     | equivalent to `__fp16` |
| `float32_t`     | equivalent to `float`  |
| `float64_t`     | equivalent to `double` |
| `mfloat8_t`     | equivalent to `__mfp8` |

If the feature macro `__ARM_FEATURE_BF16_SCALAR_ARITHMETIC` is
defined, [`<arm_sve.h>`](#arm_sve.h) also includes
[`<arm_bf16.h>`](#arm_bf16.h), which defines the scalar 16-bit brain
floating-point type `__bf16`. Then, under the control of the same feature
macro, `<arm_sve.h>` defines an alias of `__bf16` called `bfloat16_t`.

### SVE vector types

[`<arm_sve.h>`](#arm_sve.h) defines the following sizeless types for
single vectors:

| **Signed integer**   | **Unsigned integer** | **Floating-point**   |                      |
| -------------------- | -------------------- | -------------------- | -------------------- |
| `svint8_t`           | `svuint8_t`          |                      | `svmfloat8_t`        |
| `svint16_t`          | `svuint16_t`         | `svfloat16_t`        | `svbfloat16_t`       |
| `svint32_t`          | `svuint32_t`         | `svfloat32_t`        |                      |
| `svint64_t`          | `svuint64_t`         | `svfloat64_t`        |                      |

Each type `svBASE_t` is an opaque length-agnostic vector of `BASE_t`
elements. The types in each row have the same number of elements and
have twice as many elements as the types in the row below them.

`svbfloat16_t` is only available if the header file also provides a
definition of `bfloat16_t` (see [Scalar types defined by
`<arm_sve.h>`](#scalar-types-defined-by-arm_sve.h)). The other
types are available unconditionally.


[`<arm_sve.h>`](#arm_sve.h) also defines tuples of two, three, and four
vectors, as follows:

| **Signed integer**   | **Unsigned integer** | **Floating-point**    |                      |
| -------------------- | -------------------- | --------------------- | -------------------- |
| `svint8x2_t`         | `svuint8x2_t`        |                       | `svmfloat8x2_t`      |
| `svint16x2_t`        | `svuint16x2_t`       | `svfloat16x2_t`       | `svbfloat16x2_t`     |
| `svint32x2_t`        | `svuint32x2_t`       | `svfloat32x2_t`       |                      |
| `svint64x2_t`        | `svuint64x2_t`       | `svfloat64x2_t`       |                      |
|                      |                      |                       |                      |
| `svint8x3_t`         | `svuint8x3_t`        |                       | `svmfloat8x3_t`      |
| `svint16x3_t`        | `svuint16x3_t`       | `svfloat16x3_t`       | `svbfloat16x3_t`     |
| `svint32x3_t`        | `svuint32x3_t`       | `svfloat32x3_t`       |                      |
| `svint64x3_t`        | `svuint64x3_t`       | `svfloat64x3_t`       |                      |
|                      |                      |                       |                      |
| `svint8x4_t`         | `svuint8x4_t`        |                       | `svmfloat8x4_t`      |
| `svint16x4_t`        | `svuint16x4_t`       | `svfloat16x4_t`       | `svbfloat16x4_t`     |
| `svint32x4_t`        | `svuint32x4_t`       | `svfloat32x4_t`       |                      |
| `svint64x4_t`        | `svuint64x4_t`       | `svfloat64x4_t`       |                      |

Each `svBASExN_t` is an opaque sizeless type that conceptually
contains a sequence of N `svBASE_t`s, indexed starting at 0. It is
available whenever the corresponding single-vector type is.

ACLE provides the following intrinsics for creating and accessing
these tuple types:

<!-- Trailing whitespace is deliberate here -->
[`svcreate2(svBASE_t x0, svBASE_t x1)`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svcreate2)
[`svcreate3(svBASE_t x0, svBASE_t x1, svBASE_t x2)`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svcreate3)
[`svcreate4(svBASE_t x0, svBASE_t x1, svBASE_t x2, svBASE_t x3)`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svcreate4)

> `svcreateN` returns a `svBASExN_t` in which the vector at index M has the
> value given by `xM`.

<!-- Trailing whitespace is deliberate here -->
[`svset2(svBASEx2_t tuple, uint64_t imm_index, svBASE_t x)`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svset2)
[`svset3(svBASEx3_t tuple, uint64_t imm_index, svBASE_t x)`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svset3)
[`svset4(svBASEx4_t tuple, uint64_t imm_index, svBASE_t x)`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svset4)

> `svsetN` returns a copy of `tuple` in which the vector at index
> `imm_index` has the value given by `x`. `imm_index` must be an
> integer constant expression in the range [0, N-1].

<!-- Trailing whitespace is deliberate here -->
[`svget2(svBASEx2_t tuple, uint64_t imm_index)`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svget2)
[`svget3(svBASEx3_t tuple, uint64_t imm_index)`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svget3)
[`svget4(svBASEx4_t tuple, uint64_t imm_index)`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svget4)

> `svgetN` returns the value of vector `imm_index` in `tuple`. `imm_index`
> must be an integer constant expression in the range [0, N-1].

It is also possible to create completely-undefined vectors and tuples of
vectors using [`svundef`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svundef_),
[`svundef2`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svundef2),
[`svundef3`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svundef3) and
[`svundef4`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svundef4).

ACLE provides two sets of intrinsics for converting between vector types
and between vector tuple types:

*   The [`svreinterpret`](#sve-reinterpret-intrinsics) intrinsics simply
    reinterpret a vector (or vector tuple) of one type as a vector (or
    vector tuple) of another type, without changing any of the bits.

*   The [`svcvt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svcvt_)
    intrinsics instead perform numerical conversion from one type to another,
    such as converting integers to floating-point values.

To avoid any ambiguity between the two operations, ACLE does not allow
C-style casting from one vector type to another.

### SVE predicate types

[`<arm_sve.h>`](#arm_sve.h) defines a single sizeless predicate type
`svbool_t`, which has enough bits to control an operation on a vector
of bytes.

The main use of predicates is to select elements in a vector. When the
elements in the vector have *N* bytes, only the low bit in each sequence
of *N* predicate bits is significant. For example, with bits of a predicate
numbered from the least significant bit upwards, the elements selected by
each bit are as follows:

|                            | **bit 0** | **bit 1** | **bit 2** | **bit 3** | **bit 4** | **bit 5** | **bit 6** | **bit 7** | **bit 8** |
| -------------------------: | :-------: | :-------: | :-------: | :-------: | :-------: | :-------: | :-------: | :-------: | :-------: |
| **svuint8_t** element      | 0         | 1         | 2         | 3         | 4         | 5         | 6         | 7         | 8         |
| **svuint16_t** element     | 0         | -         | 1         | -         | 2         | -         | 3         | -         | 4         |
| **svuint32_t** element     | 0         | -         | -         | -         | 1         | -         | -         | -         | 2         |
| **svuint64_t** element     | 0         | -         | -         | -         | -         | -         | -         | -         | 1         |

### Fixed-length SVE types

#### Introduction to fixed-length SVE types

As described in [Overview of SVE types](#overview-of-sve-types),
SVE is a “length-agnostic” architecture that supports a range of
different vector register sizes. Some SVE ACLE code might be written
to work with all of these register sizes; such code is fully
“length-agnostic”. Other SVE ACLE code might instead require the
register size to belong to a restricted set. Possible restrictions
include imposing a minimum register size, a maximum register size, a
power-of-two register size, or a single exact register size. This is a
choice for the programmer to make. For example, the program snippet:

``` c
  svfloat32_t data = svld1(svptrue_pat_b32(SV_VL16), ptr);
```

loads no data when the vector registers are smaller than 512 bits, so in
practice the code is likely to require a register size of 512 bits or more.

Similarly, for any given piece of source code (whether it uses ACLE
or not), a code generator might produce SVE object code that only correctly
implements the source code for certain runtime register sizes. The code
is likely to abort or malfunction if the registers have a different
size. For example, if the code generator assumes that the vector register
size is exactly 256 bits, it might use:

``` asm
  ADD X1, X2, #32
```

instead of:

``` asm
  ADDVL X1, X2, #1
```

Let SourceVL be the set of vector register sizes supported by a piece of
SVE ACLE source code and ObjectVL be the set of vector register sizes
for which the object code correctly implements the source code. In both
cases, the set might be the set of all possible register sizes (referred
to as “unrestricted” below).

In general, object code created from SVE ACLE source code only works
correctly when the runtime register size belongs to the intersection of
SourceVL and ObjectVL. The behavior in other cases is undefined.

The compiler might impose a fixed ObjectVL set for all code or provide a
level of user control. It might also allow ObjectVL to vary within the
program, either within the same translation unit or between different
translation units. Whether and how this happens is currently outside the
scope of ACLE.

The combination of a singleton SourceVL and an unrestricted
ObjectVL makes sense: ACLE source code written for a single register
size can still be compiled correctly without knowing what that size is,
just like an assembler can assemble SVE code without knowing what
register sizes the assembly code supports. Similarly, the combination of
a singleton ObjectVL and an unrestricted SourceVL makes sense: ACLE
source code written for all register sizes can still be compiled for
only a single register size, perhaps to try to improve the performance
of surrounding code. Other combinations are also possible.

This section describes ACLE features related to singleton ObjectVLs.
They are intended to help cases in which SourceVL is the same singleton.

All the features are optional: a conforming ACLE implementation does not
need to provide them.

Note: the types defined in [SVE vector types](#sve-vector-types) and
[SVE predicate types](#sve-predicate-types) are always sizeless types and
are subject to the same restrictions for all SourceVL and for all ObjectVL.

#### The `__ARM_FEATURE_SVE_BITS` macro

As an optional extension, an ACLE implementation may set the
preprocessor macro:

``` c
  __ARM_FEATURE_SVE_BITS
```

to a nonzero value N provided that:

*   ObjectVL (see [Introduction to fixed-length SVE
    types](#introduction-to-fixed-length-sve-types)
    is a singleton vector register size of N bits; and

*   it is possible to apply the `arm_sve_vector_bits(N)` attribute to
    SVE vector types and SVE predicate types, as described in
    [The `arm_sve_vector_bits` attribute](#the-arm_sve_vector_bits-attribute).

If the implementation allows ObjectVL to be changed within a translation
unit, it must ensure that the value of the macro remains accurate after
each change. `__ARM_FEATURE_SVE_BITS` would then have different values
at different points in a translation unit.

Defining the macro to zero has the same meaning as not defining it all.

#### The `arm_sve_vector_bits` attribute

##### Syntax and requirements

An ACLE implementation can choose to provide the following GNU-style type
attribute:

``` c
  __attribute__((arm_sve_vector_bits(...arguments...)))
```

ACLE only defines the effect of the attribute if all of the
following are true:

1.  the attribute is attached to a single SVE vector type (such as
    `svint32_t`) or to the SVE predicate type `svbool_t`;

2.  the arguments consist of a single nonzero integer constant expression
    (referred to as N below); and

3.  `N==__ARM_FEATURE_SVE_BITS`.

In other cases the implementation must do one of the following:

*   Ignore the attribute; a warning would then be appropriate, but is not
    required.

*   Reject the program with a diagnostic.

*   Extend requirement (3) above to support other values of N besides
    `__ARM_FEATURE_SVE_BITS`.

*   Process the attribute in accordance with a later revision of ACLE.

##### General `arm_sve_vector_bits` behavior

Let VLST be a valid type:

``` c
  VLAT __attribute__((arm_sve_vector_bits(N)))
```

for some SVE vector type or SVE predicate type VLAT. VLST is then a
fixed-length version of VLAT that is specialized for an N-bit SVE
target. It is a normal sized (rather than sizeless) type, so unlike
VLAT, it can be used as the type of a global variable, class member,
`constexpr`, and so on. For example:

``` c
  #if __ARM_FEATURE_SVE_BITS==512
  typedef svint32_t vec __attribute__((arm_sve_vector_bits(512)));
  typedef svbool_t pred __attribute__((arm_sve_vector_bits(512)));
  #endif
```

creates a type called `vec` that acts a fixed-length version of
`svint32_t` and a type called `pred` that acts as a fixed-length
version of `svbool_t`. Both types are normal sized types; `vec`
contains exactly 512 bits (64 bytes) and `pred` contains exactly 64
bits (8 bytes):

``` c
  #if __ARM_FEATURE_SVE_BITS==512
  typedef svint32_t vec __attribute__((arm_sve_vector_bits(512)));
  typedef svbool_t pred __attribute__((arm_sve_vector_bits(512)));

  svint32_t g1;  // Invalid, svint32_t is sizeless
  vec g2;        // OK
  svbool_t g3;   // Invalid, svbool_t is sizeless
  pred g4;       // OK

  struct wrap1 { svint32_t x; };  // Invalid, svint32_t is sizeless
  struct wrap2 { vec x; };        // OK
  struct wrap3 { svbool_t x; };   // Invalid, svbool_t is sizeless
  struct wrap4 { pred x; };       // OK

  size_t size1 = sizeof(svint32_t);  // Invalid, svint32_t is sizeless
  size_t size2 = sizeof(vec);        // OK, equals 64
  size_t size3 = sizeof(svbool_t);   // Invalid, svbool_t is sizeless
  size_t size4 = sizeof(pred);       // OK, equals 8
  #endif
```

The following rules apply to both vector and predicate VLST types:

*   Whenever `__ARM_FEATURE_SVE_BITS==N`, VLST implicitly converts to
    VLAT and VLAT implicitly converts to VLST. In C++, these conversions
    have a rank just below derived-to-base conversion.

    This behavior makes it possible to use VLST with ACLE intrinsics that
    operate on VLAT. For example:

    ``` c
      #if __ARM_FEATURE_SVE_BITS==512
      typedef svbool_t pred __attribute__((arm_sve_vector_bits(512)));
      pred f(pred x, pred y) { return svbrka_z(x, y); }
      #endif
    ```

*   A conditional expression of the form `C ? E1 : E2` is ill-formed if:

    *   E1 has type VLAT or cv-qualified VLAT and E2 has type VLST or
        cv-qualified VLST; or

    *   E1 has type VLST or cv-qualified VLST and E2 has type VLAT or
        cv-qualified VLAT.

    However, the implementation does not need to diagnose these cases.

    This rule avoids any ambiguity about whether the result of the
    conditional expression is sized or sizeless. For example:

    ``` c
      #if __ARM_FEATURE_SVE_BITS==512
      typedef svint32_t vec __attribute__((arm_sve_vector_bits(512)));
      auto f(bool cond, vec x, svint32_t y) { return cond ? x : y; }
      #endif
    ```

    is ill-formed because it is not clear whether the type of the result
    should come from `x` or `y`.

*   VLST maps to the same AAPCS64 ABI type as VLAT. For example:

    ``` c
      svint32_t __attribute__((arm_sve_vector_bits(128)))
    ```

    maps to the same AAPCS64 type as `svint32_t`, rather than to the
    same AAPCS64 type as the `arm_neon.h` type `int32x4_t`.

*   An object type “requires size N” if:

    *   it is an SVE vector type or SVE predicate type that has the
        attribute `arm_sve_vector_bits(N)`;

    *   it is an array type whose element type requires size N; or

    *   it is a class or struct and:

        *   at least one non-static member has a type that requires size N; or

        *   a base type requires size N

    Note: this definition specifically excludes reference and pointer types.

*   A function type “requires size N” if the return type requires size N
    or if at least one parameter type requires size N.

*   A program is ill-formed if:

    *   any function type requires two different sizes N1 and N2.

    *   `__ARM_FEATURE_SVE_BITS!=N` when defining a function whose type
        requires size N.

    *   `__ARM_FEATURE_SVE_BITS!=N` when calling a function whose type
        requires size N. (Note that this explicitly excludes parameters
        passed through “`...`”.)

    *   an object whose type requires some size N is passed to an
        [unprototyped function](#unprototyped-function).

    However, the implementation does not need to diagnose these cases.

    These rules only have an effect if an implementation allows the
    register size to vary within a translation unit. The aim is to forbid
    function definitions and function calls that have no mapping to the
    AAPCS64 calling conventions. For example, if an implementation
    supports some form of pragma that changes `__ARM_FEATURE_SVE_BITS`
    within a translation unit:

    ``` c
      ...pragma that changes __ARM_FEATURE_SVE_BITS to 256...

      typedef svfloat32_t vec256 __attribute__((arm_sve_vector_bits(256)));

      ...pragma that changes __ARM_FEATURE_SVE_BITS to 512...

      typedef svbool_t bool512 __attribute__((arm_sve_vector_bits(512)));
      struct mix1 { bool512 a; vec256 b; };  // OK
      struct mix2 { bool512 a; vec256 *b; }; // OK
      union mix3 { bool512 a; vec256 b; };   // OK
      typedef bool512 (*callback)(vec256);   // Invalid, requires sizes 256, 512
      bool512 f1(vec256);                    // Invalid, requires sizes 256, 512
      vec256 f2();                           // OK, just a declaration
      vec256 f3() { ... }                    // Invalid, requires size 256
      void f4(struct mix1 m) { ... }         // Invalid, requires sizes 256, 512
      void f5(struct mix2 m) { ... }         // OK, just requires size 512
      void f6(union mix3 m) { ... }          // OK, no size requirements
      bool512 f7() { ... }                   // OK, just requires size 512
      void f8(bool512 *x, vec256 *y) { ... } // OK, no size requirements
    ```

See [`arm_sve_vector_bits` behavior specific to
vectors](#arm_sve_vector_bits-behavior-specific-to-vectors)
for additional rules that apply specifically to vectors and
[`arm_sve_vector_bits` behavior specific to
predicates](#arm_sve_vector_bits-behavior-specific-to-predicates)
for additional rules that apply specifically to predicates.

##### `arm_sve_vector_bits` behavior specific to vectors

If VLAT is an SVE vector type `svBASE_t` and VLST is a valid type:

``` c
  VLAT __attribute__((arm_sve_vector_bits(N)))
```

then VLST is a sized type that has the following properties:

``` c
  sizeof(VLST) == N/8
  alignof(VLST) == 16
```

If in addition the implementation defines the preprocessor macro

``` c
  __ARM_FEATURE_SVE_VECTOR_OPERATORS
```

and if VLAT is not `svbfloat16_t`, then:

*   The GNU `__attribute__((vector_size))` extension is available.

*   VLST supports the same forms of elementwise initialization as:

    ``` c
      BASE_t __attribute__((vector_size(N/8)))
    ```

    (referred to as GNUT below). For example:

    ``` c
      #if __ARM_FEATURE_SVE_BITS==256 && __ARM_FEATURE_SVE_VECTOR_OPERATORS
      svint64_t vec __attribute__((arm_sve_vector_bits(256))) = { 0, 1, 2, 3 };
      #endif
    ```

*   VLST supports the same built-in C and C++ operators as GNUT. Any
    result that has type GNUT for GNUT operators has type VLST for VLST
    operators. For example:

    ``` c
      #if __ARM_FEATURE_SVE_BITS==512 && __ARM_FEATURE_SVE_VECTOR_OPERATORS
      typedef svint32_t vec __attribute__((arm_sve_vector_bits(512)));
      auto f(vec x, vec y) { return x + y; }    // Returns a vec.
      #endif
    ```

*   Whenever `__ARM_FEATURE_SVE_BITS==N`, GNUT implicitly converts to
    VLAT and VLAT implicitly converts to GNUT. In C++, these conversions
    have a rank just below derived-to-base conversion.

    This behavior makes it possible to use GNUT with ACLE intrinsics that
    operate on VLAT. For example:

    ``` c
      typedef int8_t vec __attribute__((vector_size(32)));
      #if __ARM_FEATURE_SVE_BITS==256 && __ARM_FEATURE_SVE_VECTOR_OPERATORS
      vec f(vec x) { return svasrd_x(svptrue_b8(), x, 1); }
      #endif
    ```

*   Irrespective of `__ARM_FEATURE_SVE_BITS`, GNUT implicitly converts
    to VLST and VLST implicitly converts to GNUT. In C++, these
    conversions again have a rank just below derived-to-base conversion.

    This behavior makes it possible to use VLST with existing interfaces
    that operate on GNUT. For example:

    ``` c
      typedef int8_t vec1 __attribute__((vector_size(32)));
      void f(vec1);
      #if __ARM_FEATURE_SVE_BITS==256 && __ARM_FEATURE_SVE_VECTOR_OPERATORS
      typedef svint8_t vec2 __attribute__((arm_sve_vector_bits(256)));
      void g(vec2 x) { f(x); }    // OK
      #endif
    ```

    Also, if an implementation supports some form of pragma that changes
    `__ARM_FEATURE_SVE_BITS` within a translation unit:

    ``` c
      #ifdef __ARM_FEATURE_SVE_VECTOR_OPERATORS
      ...pragma that changes __ARM_FEATURE_SVE_BITS to 256...

      int8_t x __attribute__((vector_size(32)));
      svint8_t y __attribute__((arm_sve_vector_bits(256)));

      ...pragma that changes __ARM_FEATURE_SVE_BITS to 512...

      void f() { x = y; }    // OK
      #endif
    ```

*   A conditional expression of the form `C ? E1 : E2` is ill-formed if:

    *   E1 has type VLAT or cv-qualified VLAT and E2 has type GNUT or
        cv-qualified GNUT; or

    *   E1 has type GNUT or cv-qualified GNUT and E2 has type VLAT or
        cv-qualified VLAT.

    However, the implementation does not need to diagnose these cases.

    This rule avoids any ambiguity about whether the result of the
    conditional expression is sized or sizeless. For example:

    ``` c
      #if __ARM_FEATURE_SVE_BITS==512 && __ARM_FEATURE_SVE_VECTOR_OPERATORS
      typedef int32_t vec __attribute__((vector_size(64)));
      auto f(bool cond, vec x, svint32_t y) { return cond ? x : y; }
      #endif
    ```

    is ill-formed because it is not clear whether the type of the result
    should come from `x` or `y`. The choice would affect the ABI of
    the function.

*   A binary expression of the form `E1 op E2` or a conditional expression
    of the form `C ? E1 : E2` is ill-formed if:

    *   E1 has type VLST or cv-qualified VLST and E2 has type GNUT or
        cv-qualified GNUT; or

    *   E1 has type GNUT or cv-qualified GNUT and E2 has type VLST or
        cv-qualified VLST.

    However, the implementation does not need to diagnose these cases.

    This rule avoids any ambiguity about whether the result of the
    expression is a GNU or SVE type. For example:

    ``` c
      #if __ARM_FEATURE_SVE_BITS==512 && __ARM_FEATURE_SVE_VECTOR_OPERATORS
      typedef int32_t vec1 __attribute__((vector_size(64)));
      typedef svint32_t vec2 __attribute__((arm_sve_vector_bits(512)));
      auto f(vec1 x, vec2 y) { return x + y; }
      #endif
    ```

    is ill-formed because it is not clear whether the type of the result
    should come from `x` or `y`. The choice would affect the ABI of
    the function.

##### `arm_sve_vector_bits` behavior specific to predicates

Let VLST be a valid type:

``` c
  svbool_t __attribute__((arm_sve_vector_bits(N)))
```

VLST is then a sized type that has the following properties:

``` c
  sizeof(VLST) == N/64
  alignof(VLST) == 2
```

If in addition the implementation defines the preprocessor macro

``` c
  __ARM_FEATURE_SVE_PREDICATE_OPERATORS
```

then:

*   The GNU `__attribute__((vector_size))` extension is available.

*   VLST supports the same forms of elementwise initialization as the
    vector type:

    ``` c
      uint8_t __attribute__((vector_size(N/8)))
    ```

    except that the elements have type `bool` instead of `uint8_t`.

*   VLST supports the following operators, all of which take arguments of
    type VLST and return either a VLST or a reference to a VLST:

    *   unary `~`

    *   binary `&`, `|` and `^`

    *   assignments `&=`, `|=` and `^=`

    *   comparisons `<`, `<=`, `==`, `!=`, `>=` and `>`

    All operators behave analogously to GNU vectors. For example:

    ``` c
      #if __ARM_FEATURE_SVE_BITS==256 && __ARM_FEATURE_SVE_PREDICATE_OPERATORS
      typedef svbool_t pred __attribute__((arm_sve_vector_bits(256)));
      auto f(pred x, pred y) { return x & y; }    // Returns a pred
      #endif
    ```

*   VLST supports the array subscript operator `[]` in a way that
    behaves analogously to GNU vectors, except that it is not possible to
    take the address of the result. For example:

    ``` c
      #if __ARM_FEATURE_SVE_BITS==256 && __ARM_FEATURE_SVE_PREDICATE_OPERATORS
      typedef svbool_t pred __attribute__((arm_sve_vector_bits(256)));
      pred x;
      bool f() { x[1] = true; return x[0]; }
      #endif
    ```

*   Within a byte, subscripts count from the least significant bit. For
    example:

    ``` c
      #if __ARM_FEATURE_SVE_BITS==256 && __ARM_FEATURE_SVE_PREDICATE_OPERATORS
      svbool_t p __attribute__((arm_sve_vector_bits(256))) = { 0, 1 };
      #endif
    ```

    sets the first byte of `p` to 2 for both big- and little-endian targets.

An implementation can choose to provide other operators too, but it does not
need to do so.

Note that, at the time of writing, the GNU `vector_size` extension is
not defined for `bool` elements, nor for packed vectors of single bits.
The definition above is intended to be a conservative subset of what such
an extension might provide.

##### C++ mangling of fixed-length SVE types

Let VLST be a valid C++ type:

``` c
  VLAT __attribute__((arm_sve_vector_bits(N)))
```

for some SVE vector type or SVE predicate type VLAT. VLST is mangled in
the same way as a template:

``` c
  template<typename, unsigned> struct __SVE_VLS;
```

with the arguments:

``` c
  __SVE_VLS<VLAT, N>
```

For example:

``` c
  #if __ARM_FEATURE_SVE_BITS==512
  // Mangled as 9__SVE_VLSIu11__SVInt32_tLj512EE
  typedef svint32_t vec __attribute__((arm_sve_vector_bits(512)));
  // Mangled as 9__SVE_VLSIu10__SVBool_tLj512EE
  typedef svbool_t pred __attribute__((arm_sve_vector_bits(512)));
  #endif
```

## SVE enum declarations

The following enum enumerates all the possible patterns returned by a PTRUE:

``` c
  enum svpattern
  {
    SV_POW2 = 0,
    SV_VL1 = 1,
    SV_VL2 = 2,
    SV_VL3 = 3,
    SV_VL4 = 4,
    SV_VL5 = 5,
    SV_VL6 = 6,
    SV_VL7 = 7,
    SV_VL8 = 8,
    SV_VL16 = 9,
    SV_VL32 = 10,
    SV_VL64 = 11,
    SV_VL128 = 12,
    SV_VL256 = 13,
    SV_MUL4 = 29,
    SV_MUL3 = 30,
    SV_ALL = 31
  };
```

The following enum lists the possible prefetch types:

``` c
  enum svprfop
  {
    SV_PLDL1KEEP = 0,
    SV_PLDL1STRM = 1,
    SV_PLDL2KEEP = 2,
    SV_PLDL2STRM = 3,
    SV_PLDL3KEEP = 4,
    SV_PLDL3STRM = 5,
    SV_PSTL1KEEP = 8,
    SV_PSTL1STRM = 9,
    SV_PSTL2KEEP = 10,
    SV_PSTL2STRM = 11,
    SV_PSTL3KEEP = 12,
    SV_PSTL3STRM = 13
  };
```

Both enums are defined by [`<arm_sve.h>`](#arm_sve.h).

## SVE intrinsics

### SVE naming convention

The SVE ACLE intrinsics have the form:

``` c
  svbase[_disambiguator][_type0][_type1]...[_predication]
```

where the individual parts are as follows:

**base**

> For most intrinsics this is the lower-case name of an SVE
> instruction, but with some adjustments:
>
> *   The most common change is to drop `F`, `S` and `U` if they
>     stand for “floating-point”, “signed” and “unsigned” respectively,
>     in cases where this would duplicate information in the type
>     suffixes below.
>
> *   Simple non-extending loads and non-truncating stores drop the
>     size suffix (`B`, `H`, `W` or `D`), which would always duplicate
>     information in the suffixes.
>
> *   Conversely, extending loads always specify an explicit extension
>     type, since this information is not available in the suffixes.
>     A sign-extending load has the same base as the architectural
>     instruction (for instance, `ld1sb`) while a zero-extending load replaces
>     the `s` with a `u` (for instance, `ld1ub` for a zero-extending `LD1B`).
>     Thus [`svld1ub_u32`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svld1ub_u32)
>     zero-extends 8-bit data to a vector of
>     `uint32_t`s while [`svld1sb_u32`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svld1sb_u32)
>     sign-extends 8-bit data to a vector of `uint32_t`s.

**disambiguator**

> This field distinguishes between different forms of an intrinsic.
> There are several common uses:
>
> *   Load, store, prefetch, and ADR intrinsics use this field to
>     distinguish between different addressing modes. See
>     [SVE addressing modes](#sve-addressing-modes) for a detailed
>     description of these modes.
>
> *   Arithmetic operations use the disambiguator `_n` when the final
>     operand is a scalar rather than a vector. See [SVE operations involving
>     vectors and scalars](#sve-operations-involving-vectors-and-scalars)
>     for more information about these operations.
>
> *   Some predicate-based operations use the disambiguator `_pat` to
>     show that they operate on an explicit constant predicate pattern
>     like `MUL3` instead of either an all-true predicate or an `svbool_t`.

<!-- Trailing whitespace is deliberate here -->
**type0**
**type1**
...

> These fields list the types of vectors and predicates, starting with
> the return type and continuing with the argument types. They do not
> include the types of vector bases and displacements, which form part
> of the addressing mode disambiguator instead. They also do not
> include argument types that are uniquely determined by the previous
> argument types and return type.
>
> For vectors the field is a type category followed by an element size
> in bits:
>
> | **Type category**            | **8-bit** | **16-bit** | **32-bit** | **64-bit** |
> | ---------------------------- | --------- | ---------- | ---------- | ---------- |
> | signed integers              | `s8`      | `s16`      | `s32`      | `s64`      |
> | unsigned integers            | `u8`      | `u16`      | `u32`      | `u64`      |
> | floating-point numbers       |           | `f16`      | `f32`      | `f64`      |
> | brain floating-point numbers |           | `bf16`     |            |            |
>
> For predicates the suffix is `b` followed by the size of the
> associated data elements in bits, or simply `b` if the operation
> does not assume a particular element size. For example, the intrinsic
> for
>
> ``` asm
>   PTRUE Pd.B
> ```
>
> is [`svptrue_b8`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svptrue_b8)
> while the intrinsic for
>
> ``` asm
>   PTRUE Pd.H
> ```
>
> is [`svptrue_b16`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[16]&q=svptrue_b16)
> The intrinsic for:
>
> ``` asm
>   PFALSE Pd.B
> ```
>
> is [`svpfalse_b`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svpfalse_b)
> rather than `svpfalse_b8` since the result is suitable for all element sizes.

**predication**

> This suffix describes the inactive elements in the result of a
> predicated operation. It can be one of the following:
>
> **`z`**
>
> > Zero predication: set all inactive elements of the result to zero.
>
> **`m`**
>
> > Merge predication: copy all inactive elements from the first
> > vector argument.
> >
> > Unary operations have a separate vector argument that comes
> > before the general predicate; for example:
> >
> > ``` asm
> >   CLZ Zd.H, Pg/M, Zs.H
> > ```
> >
> > corresponds to:
> >
> > ``` c
> >   Zd = svclz_u16_m(Zd, Pg, Zs);
> > ```
> >
> > The argument does not need to be syntactically related to the result;
> > calls such as:
> >
> > ``` c
> >   Zd = svclz_u16_m(svadd_u16_z(...), Pg, Zs);
> > ```
> >
> > are also valid.
> >
> > Binary and ternary operations reuse the first argument to the
> > operation as the merge input; for example:
> >
> > ``` asm
> >   ADD Zd.S, Pg/M, Zd.S, Zs2.S
> > ```
> >
> > corresponds to:
> >
> > ``` c
> >   Zd = svadd_u32_m(Pg, Zd, Zs2);
> > ```
> >
> > where the `Zd` argument supplies both the values of inactive
> > elements and the first operand to the addition. Again, the merge
> > input does not need to be syntactically related to the result.
>
> **`x`**
>
> > “Don't-care” predication: set the inactive elements to
> > **unknown** values.
> >
> > Warning: these values could be arbitrary register contents left
> > around from a previous operation, so accidentally using the inactive
> > elements could lead to data leakage.
> >
> > This form of predication removes the need to choose between
> > zeroing and merging in cases where the inactive elements are
> > unimportant. The code generator can then pick whichever form of
> > instruction seems to give the best code. This includes using
> > unpredicated instructions, where available and suitable.
>
> Predicated loads, predicated comparisons and predicated string match
> operations are always zeroing operations, so for brevity, the
> corresponding intrinsics have no predication suffix.

### Overloaded aliases of SVE intrinsics

The intrinsic names that are described in [SVE naming
convention](#sve-naming-convention) often carry information that is
obvious from the types of the arguments. For example, `svclz_u16_z`
always takes a `svuint16_t` and no other form of `svclz_type_z` does.
ACLE therefore defines shorter, overloaded, aliases that are compatible
with both C++ overloading and C `_Generic` associations. At a
minimum, this means that all overloaded forms of an intrinsic have the
same number of arguments and that it is possible to select the correct
overload by considering each argument from left to right.

(Although the overloading scheme is compatible with `_Generic`, a C
implementation can use other implementation-specific ways of achieving
the same effect.)

The usual integer promotions mean that overloading based on scalar
integer types can be non-obvious. For example, in the C++ code:

``` c
  int f(unsigned char) { return 1; }
  int f(int) { return 2; }
  int g1(unsigned char c) { return f(c); }
  int g2(unsigned char c) { return f(c + 1); }
```

`g1` returns 1 but `g2` returns 2. A cast would be required to make
`g2` use the `unsigned char` version of `f` instead of the `int` version.
For this reason, ACLE does not use overloading of scalar arguments
alone to determine the type of a vector result. Intrinsics like `svdup`
and `svindex` (whose only arguments are scalar) always require a suffix
indicating the return type.

Overloaded aliases are always a full intrinsic name with parts of the
suffix removed. The rest of this document refers to both the full
intrinsic name and its overloaded alias by enclosing the elided suffix
characters in square brackets. For example:

``` c
  svclz[_u16]_m
```

says that the full name is `svclz_u16_m` and that its overloaded alias
is `svclz_m`.

### SVE addressing modes

Load, store, prefetch, and ADR intrinsics have different forms for
different addressing modes. The exact set of addressing modes depends on
the particular operation, but they always have a base component and may
also have a displacement component.

The base may be either a single C pointer or a vector of address values.
In the latter case, the address values may be 32 or 64 bits in size.
Addressing modes with vector bases use the disambiguator `[_xNNbase]`,
where `xNN` is the type of the address vector elements.

The displacement, if present, may be a 64-bit scalar or a vector of
32-bit or 64-bit elements. There are five forms in total, with the
following disambiguators:

**`_offset`**

> The displacement is a 64-bit scalar byte count.

**`_index`**

> The displacement is a 64-bit scalar element count. For example, if an
> intrinsic loads 16-bit elements from memory, an `_index` displacement
> of 1 is equivalent to an `_offset` displacement of 2.

**`_vnum`**

> The displacement is a 64-bit scalar that counts a single vector's
> worth of elements. For example, if an intrinsic loads one or more full
> vectors from memory, a `_vnum` displacement of 1 is equivalent to
> an `_offset` displacement of VG×8 (the number of bytes in an SVE
> vector). If an intrinsic loads 16-bit elements and extends them to
> 32 bits, a `_vnum` displacement of 1 is equivalent to an `_offset`
> displacement of VG×4 (half the number of bytes in an SVE vector).
>
> This form corresponds to the `MUL VL` addressing mode. However,
> the displacement argument can be any scalar value; it does not need
> to be a constant in a particular range.

**`_[xNN]offset`**

> The displacement is a vector of type `xNN` and each element specifies
> a separate byte count. In other words:
>
> *   `_[s32]offset` specifies a vector of signed 32-bit byte counts
>     and is equivalent to the `SXTW` addressing mode.
>
> *   `_[u32]offset` specifies a vector of unsigned 32-bit byte counts
>      and is equivalent to the `UXTW` addressing mode.
>
> *   `_[s64]offset` and `_[u64]offset` both specify vectors of 64-bit byte
>     counts; the sign is unimportant in this case.

**`_[xNN]index`**

> Similar to `_[xNN]offset`, but each element specifies an element
> count rather than a byte count, in the same way as for `_index`.

These displacements do not need to be constant and they do not need to
be within a specific range.

For example, the simplest load addressing mode is:

``` c
  svint16_t svld1[_s16](svbool_t pg, const int16_t *base)
```

which loads N elements from `base[0]` to `base[N-1]` inclusive.

It is possible to apply a displacement measured in whole vectors using:

``` c
  svint16_t svld1_vnum[_s16](svbool_t pg, const int16_t *base, int64_t vnum)
```

which loads N elements from `base[N*vnum]` to `base[N*vnum+N-1]` inclusive.

The following intrinsic instead takes a vector of offsets, measured in bytes:

``` c
  svuint32_t svld1_gather_[s32]offset[_u32](svbool_t pg, const uint32_t *base,
                                            svint32_t offsets)
```

In this case the address of element i is:

``` c
  (int32_t *)((uintptr_t)base + offsets[i])
```

For:

``` c
  svuint32_t svld1_gather_[s32]index[_u32](svbool_t pg, const uint32_t *base,
                                           svint32_t indices)
```

the address of element i is simply `&base[indices[i]]`.

The following intrinsic is an example of one that combines a vector base
with a scalar index:

``` c
  svint32_t svld1_gather[_u32base]_index_s32(svbool_t pg, svuint32_t bases,
                                             int64_t index)
```

The address of element i is:

``` c
  ((int32_t *)(uintptr_t)bases[i]) + index
```

### SVE operations involving vectors and scalars

Some of the SVE instructions have immediate forms; for example:

``` c
  ADD Zd.S, Zd.S, #1
```

adds 1 to every element of `Zd.S`. ACLE extends this approach to
all arithmetic operations and to all scalar inputs (not just immediates).
The implementation can then use immediate forms where possible or duplicate
the scalar into a vector otherwise.

For example:

``` c
  svint32_t x;
  ...
  x = svadd[_n_s32]_x(pg, x, 1);
```

adds 1 to every active element of `x` while:

``` c
  svfloat64_t x;
  double *ptr;
  ...
  x = svadd[_n_f64]_x(pg, x, *ptr);
```

adds `*ptr` to every active element of `x`. The first example is
likely to use the immediate form of ADD while the latter is likely to
use LD1RD.

In a vector operation, the disambiguator `_n` indicates that the final
operand is a scalar rather than a vector.

### Immediate arguments to SVE intrinsics

Some intrinsics take enumeration values as arguments. These enumerations
must always be integer constant expressions that specify a valid
enumeration value.

A few intrinsics take general integer immediates as arguments. In the
[intrinsics documentation](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiessimdisa=[sve,sve2]),
these arguments always start with the prefix `imm`. Immediate arguments
must be integer constant expressions within a certain range (which is
the same as the range of the underlying SVE instruction).

### Faults and exceptions in SVE intrinsics

Loads and stores can trigger faults in the same way as normal pointer
dereferences. Exactly what happens then depends on the host environment
and is out of scope for this document. However, these faults should be
symptoms of a program going wrong rather than something that the
programmer deliberately planted. The implementation can therefore remove
or reorder potentially faulting operations as long as:

*   doing so would not cause a previously non-faulting program to fault;
    and

*   faults do not move between C++ exception blocks, in cases where
    faults are reported as exceptions.

Also, many floating-point operations can raise IEEE exceptions. A
similar set of rules apply there: the implementation can remove or
reorder operations that might raise an IEEE exception if:

*   doing so would not cause a program to raise IEEE exceptions in cases
    where it would not previously;

*   IEEE exceptions do not move between C++ exception blocks, in cases
    where IEEE exceptions are reported as C++ exceptions; and

*   IEEE exceptions do not move across functions that manipulate the IEEE
    exception state.

For example, the compiler can remove a floating-point addition whose
result is not used. It can also reorder independent floating-point
operations, even if that would change the order that exceptions occur.
It cannot however move floating-point addition across a direct or
indirect call to `feclearexcept` unless it can prove that the addition
would not raise an exception.

Many code generators have a mode that ignores IEEE exceptions. The
floating-point restrictions above would not apply when such a mode is in
effect.

### First-faulting and non-faulting loads

SVE provides load instructions in which only the first active element
can fault, and others in which no elements can fault. A special register
called the first-fault register (FFR) records which elements were loaded
successfully. The FFR describes all loads that have executed since the
last write to the register.

If a first-faulting or non-faulting load does not load an active element
due to a potential fault, it clears the FFR from that element onwards.
Those elements of the returned vector then have an unknown value.
Elements also have an unknown value if the associated FFR element was
*already* clear before the instruction started.

For example, in:

``` asm
  SETFFR
  LDFF1D Z0.D, P0/Z, [X0]
  LDFF1D Z1.D, P1/Z, [X1]
  LDFF1D Z2.D, P2/Z, [X2]
  RDFFR P3.B
```

the load of `Z0.D` might suppress the load of `[X0, #16]` due to a
potential fault. It would then clear bit 16 onwards of the FFR and leave
elements 2 onwards of `Z0.D` in an unknown state. The same elements of
`Z1.D` and `Z2.D` would then also be unknown, regardless of whether
the loads based on `X1` or `X2` might fault. At the end of the
sequence, `P3.B` indicates which elements of `Z0.D`, `Z1.D` and
`Z2.D` are valid.

In this sequence, the leading inactive elements of `Z0.D` are
guaranteed to be zero and the first active element is guaranteed to be
valid (assuming that the first element did not trigger a fault). The
same guarantees apply to `Z1.D` only if the first active element of
`P1` is guaranteed to be earlier than the second active element of
`P0`. In this sense, the contents of `Z0.D`, `Z1.D` and `Z2.D`
do depend on the order of the instructions, since the guarantees would
be different if the loads had a different order. However, the point of
the loads is to try to access more than the first active element, so
these relationships are not useful in practice.

ACLE therefore divides first-faulting and non-faulting loads (but
not normal loads) into “FFR groups”. Each group begins and ends with an
intrinsic that explicitly reads from or writes to the FFR. More precisely,
ACLE introduces a global “first-fault register token” (FFRT) that identifies
the current FFR group. This FFRT is a purely conceptual construct and contains
three pieces of information:

| **Identifier** | **Contents**                                                   |
| -------------- | -------------------------------------------------------------- |
| *nwrite*       | the number of explicit writes to the FFR                       |
| *lastwrite*    | the last value written to the FFR                              |
| *nread*        | the number of explicit reads from the FFR since the last write |

There are only two possible ways of modifying this FFRT:

1.  Increment *nwrite* by one, set *lastwrite* to a given value, and set
    *nread* to zero.

2.  Increment *nread* by one.

Intrinsics that explicitly write to the FFR do the first operation.
Intrinsics that explicitly read from the FFR do the second operation.
First-faulting and non-faulting loads read from the FFRT and depend on
its value, but they do not write to it.

One consequence of this arrangement is that an intrinsic that writes to
the FFR is only dead if there are no further references to the FFRT in
the program. However, the normal “as if” rules apply, so the implementation
can produce an empty code sequence for the write if doing so would not
affect the behavior of the program. Similarly, if a first-faulting or
non-faulting load follows an intrinsic that explicitly reads from the FFR,
without an intervening write, the load keeps the read intrinsic alive
even if the result of that read is unused. Again, the normal “as if”
rules mean that the implementation can produce an empty code sequence
for the read if doing so would not affect the behavior of the program.

These FFRT dependencies are the only FFR-based ones that the implementation
needs to consider when optimizing first-faulting and non-faulting loads;
in all other respects the implementation can treat the loads like normal
loads. This includes removing loads whose results are not used,
suppressing loads of individual elements if their values do not matter,
or reordering loads within a group (subject to the usual rules for
normal loads). In practice the value of the FFR before a load does still
affect which elements of the load result are defined, and in practice
the loads do still write to the FFR, but the input program does not
control these effects directly.

Assuming `float64_t` data, the C version of the code above would be:

``` c
  svfloat64_t z0, z1, z2;
  svbool_t p0, p1, p2, p3;
  double *x0, *x1, *x2;
  ...
  svsetffr();
  z0 = svldff1[_f64](p0, x0);
  z1 = svldff1[_f64](p1, x1);
  z2 = svldff1[_f64](p2, x2);
  p3 = svrdffr();
```

### SVE reinterpret intrinsics

The `svreinterpret` intrinsics for vector types and vector tuple types take the form

``` c
svreinterpret_type0[_type1_xN]
```

where `N` refers to the number of elements in a tuple type (2, 3, or 4).

For example:
``` c
svuin16_t svreinterpret_u16_s32(svint32_t op);
svuin16_t svreinterpret_u16(svint32_t op);
svuin16x2_t svreinterpret_u16_s32_x2(svint32x2_t op);
svuin16x2_t svreinterpret_u16(svint32x2_t op);
```

A list of SVE reinterpret intrinsics can be found on [developer.arm.com](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svreinterpret).

### List of SVE intrinsics

The list of SVE intrinsics can be found on
[developer.arm.com](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiessimdisa=[sve,sve2]).
This list includes SVE2 and other SVE extensions (such as the 32-bit
matrix multiply extensions).

The tick boxes on the left can be used to narrow the displayed
intrinsics to particular data types and element sizes. Below that is an
instruction group hierarchy that groups the intrinsics based on the
operation that they perform.

### Mapping of SVE instructions to intrinsics

#### List of instructions

This section contains a list of all SVE instructions. For each one it
gives a reference to the associated ACLE intrinsic or explains why no
such intrinsic exists. The list includes SVE2 and other SVE extensions
(such as the 32-bit matrix multiply extensions).

| **Instruction**                      | **Intrinsic** |
| ------------------------------------ | ------------- |
| ABS                                  | [`svabs`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svabs) |
| ADCLB                                | [`svadclb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svadclb) |
| ADCLT                                | [`svadclt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svadclt) |
| ADD (immediate)                      | [`svadd`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint,int]&q=svadd[) |
| ADD (vectors, predicated)            | [`svadd`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint,int]&q=svadd[) |
| ADD (vectors, unpredicated)          | [`svadd`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint,int]&q=svadd[) |
| ADDHNB                               | [`svaddhnb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svaddhnb) |
| ADDHNT                               | [`svaddhnt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svaddhnt) |
| ADDP                                 | [`svaddp`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int,uint]&q=svaddp) |
| ADDPL                                | See [ADDPL, ADDVL, INC and DEC](#addpl-addvl-inc-and-dec) |
| ADDVL                                | See [ADDPL, ADDVL, INC and DEC](#addpl-addvl-inc-and-dec) |
| ADR                                  | [`svadrb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svadrb), [`svadrh`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svadrh), [`svadrw`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svadrw), [`svadrd`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svadrd) |
| AESD                                 | [`svaesd`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svaesd) |
| AESE                                 | [`svaese`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svaese) |
| AESIMC                               | [`svaesimc`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svaesimc) |
| AESMC                                | [`svaesmc`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svaesmc) |
| AND (immediate)                      | [`svand`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int,uint]&q=svand[) |
| AND (predicates)                     | [`svand`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[bool]&q=svand) |
| AND (vectors, predicated)            | [`svand`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int,uint]&q=svand[) |
| AND (vectors, unpredicated)          | [`svand`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int,uint]&q=svand[) |
| ANDS                                 | [`svand`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[bool]&q=svand) |
| ANDV                                 | [`svandv`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svandv) |
| ASR (immediate, predicated)          | [`svasr`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svasr[) |
| ASR (immediate, unpredicated)        | [`svasr`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svasr[) |
| ASR (vectors)                        | [`svasr`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svasr[) |
| ASR (wide elements, predicated)      | [`svasr_wide`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svasr_wide) |
| ASR (wide elements, unpredicated)    | [`svasr_wide`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svasr_wide) |
| ASRD                                 | [`svasrd`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svasrd) |
| ASRR                                 | [`svasr`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svasr) (optimization of `_x` forms) |
| BCAX                                 | [`svbcax`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svbcax) |
| BDEP                                 | [`svbdep`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svbdep) |
| BEXT                                 | [`svbext`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svbext) |
| BFCVT                                | [`svcvt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svcvt_bf16) |
| BFCVTNT                              | [`svcvtnt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svcvtnt_bf16) |
| BFDOT                                | [`svbfdot`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svbfdot) |
| BFMLALB                              | [`svbfmlalb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svbfmlalb) |
| BFMLALT                              | [`svbfmlalt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svbfmlalt) |
| BFMMLA                               | [`svbfmmla`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svbfmmla) |
| BGRP                                 | [`svbgrp`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svbgrp) |
| BIC (immediate)                      | [`svbic`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int,uint]&q=svbic[) |
| BIC (predicates)                     | [`svbic`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[bool]&q=svbic) |
| BIC (vectors, predicated)            | [`svbic`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int,uint]&q=svbic[) |
| BIC (vectors, unpredicated)          | [`svbic`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int,uint]&q=svbic[) |
| BICS                                 | [`svbic`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[bool]&q=svbic) |
| BRKA                                 | [`svbrka`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svbrka) |
| BRKAS                                | [`svbrka`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svbrka) |
| BRKB                                 | [`svbrkb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svbrkb) |
| BRKBS                                | [`svbrkb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svbrkb) |
| BRKN                                 | [`svbrkn`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svbrkn) |
| BRKNS                                | [`svbrkn`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svbrkn) |
| BRKPA                                | [`svbrkpa`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svbrkpa) |
| BRKPAS                               | [`svbrkpa`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svbrkpa) |
| BRKPB                                | [`svbrkpb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svbrkpb) |
| BRKPBS                               | [`svbrkpb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svbrkpb) |
| BSL                                  | [`svbsl`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svbsl[) |
| BSL1N                                | [`svbsl1n`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svbsl1n) |
| BSL2N                                | [`svbsl2n`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svbsl2n) |
| CADD                                 | [`svcadd`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svcadd) |
| CDOT (indexed)                       | [`svcdot_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svcdot_lane) |
| CDOT (vectors)                       | [`svcdot`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svcdot[) |
| CLASTA (SIMD & FP scalar)            | [`svclasta`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svclasta) |
| CLASTA (scalar)                      | [`svclasta`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svclasta) |
| CLASTA (vectors)                     | [`svclasta`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svclasta) |
| CLASTB (SIMD & FP scalar)            | [`svclastb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svclastb) |
| CLASTB (scalar)                      | [`svclastb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svclastb) |
| CLASTB (vectors)                     | [`svclastb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svclastb) |
| CLS                                  | [`svcls`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svcls) |
| CLZ                                  | [`svclz`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svclz) |
| CMLA (indexed)                       | [`svcmla_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int,uint]&q=svcmla_lane) |
| CMLA (vectors)                       | [`svcmla`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int,uint]&q=svcmla[) |
| CMPEQ (immediate)                    | [`svcmpeq`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint,int]&q=svcmpeq[) |
| CMPEQ (vectors)                      | [`svcmpeq`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint,int]&q=svcmpeq[) |
| CMPEQ (wide elements)                | [`svcmpeq_wide`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svcmpeq_wide) |
| CMPGE (immediate)                    | [`svcmpge`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svcmpge[) |
| CMPGE (vectors)                      | [`svcmpge`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svcmpge[) |
| CMPGE (wide elements)                | [`svcmpge_wide`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svcmpge_wide) |
| CMPGT (immediate)                    | [`svcmpgt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svcmpgt[) |
| CMPGT (vectors)                      | [`svcmpgt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svcmpgt[) |
| CMPGT (wide elements)                | [`svcmpgt_wide`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svcmpgt_wide) |
| CMPHI (immediate)                    | [`svcmpgt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svcmpgt[) |
| CMPHI (vectors)                      | [`svcmpgt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svcmpgt[) |
| CMPHI (wide elements)                | [`svcmpgt_wide`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svcmpgt_wide) |
| CMPHS (immediate)                    | [`svcmpge`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svcmpge[) |
| CMPHS (vectors)                      | [`svcmpge`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svcmpge[) |
| CMPHS (wide elements)                | [`svcmpge_wide`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svcmpge_wide) |
| CMPLE (immediate)                    | [`svcmple`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svcmple[) |
| CMPLE (vectors)                      | [`svcmple`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svcmple[) |
| CMPLE (wide elements)                | [`svcmple_wide`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svcmple_wide) |
| CMPLO (immediate)                    | [`svcmplt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svcmplt[) |
| CMPLO (vectors)                      | [`svcmplt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svcmplt[) |
| CMPLO (wide elements)                | [`svcmplt_wide`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svcmplt_wide) |
| CMPLS (immediate)                    | [`svcmple`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svcmple[) |
| CMPLS (vectors)                      | [`svcmple`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svcmple[) |
| CMPLS (wide elements)                | [`svcmple_wide`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svcmple_wide) |
| CMPLT (immediate)                    | [`svcmplt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svcmplt[) |
| CMPLT (vectors)                      | [`svcmplt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svcmplt[) |
| CMPLT (wide elements)                | [`svcmplt_wide`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svcmplt_wide) |
| CMPNE (immediate)                    | [`svcmpne`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint,int]&q=svcmpne[) |
| CMPNE (vectors)                      | [`svcmpne`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint,int]&q=svcmpne[) |
| CMPNE (wide elements)                | [`svcmpne_wide`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint,int]&q=svcmpne_wide) |
| CNOT                                 | [`svcnot`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svcnot) |
| CNT                                  | [`svcnt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svcnt[) |
| CNTB                                 | [`svcntb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svcntb) |
| CNTD                                 | [`svcntd`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svcntd) |
| CNTH                                 | [`svcnth`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svcnth) |
| CNTP                                 | [`svcntp`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svcntp) |
| CNTW                                 | [`svcntw`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svcntw) |
| COMPACT                              | [`svcompact`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svcompact) |
| CPY (SIMD & FP scalar)               | [`svdup`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svdup[_n]) (predicated forms) |
| CPY (immediate)                      | [`svdup`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svdup[_n]) (predicated forms) |
| CPY (scalar)                         | [`svdup`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svdup[_n]) (predicated forms) |
| CTERMEQ                              | See [CTERMEQ and CTERMNE](#ctermeq-and-ctermne) |
| CTERMNE                              | See [CTERMEQ and CTERMNE](#ctermeq-and-ctermne) |
| DECB                                 | See [ADDPL, ADDVL, INC and DEC](#addpl-addvl-inc-and-dec) |
| DECD (scalar)                        | See [ADDPL, ADDVL, INC and DEC](#addpl-addvl-inc-and-dec) |
| DECD (vector)                        | See [ADDPL, ADDVL, INC and DEC](#addpl-addvl-inc-and-dec) |
| DECH (scalar)                        | See [ADDPL, ADDVL, INC and DEC](#addpl-addvl-inc-and-dec) |
| DECH (vector)                        | See [ADDPL, ADDVL, INC and DEC](#addpl-addvl-inc-and-dec) |
| DECP (scalar)                        | See [ADDPL, ADDVL, INC and DEC](#addpl-addvl-inc-and-dec) |
| DECP (vector)                        | See [ADDPL, ADDVL, INC and DEC](#addpl-addvl-inc-and-dec) |
| DECW (scalar)                        | See [ADDPL, ADDVL, INC and DEC](#addpl-addvl-inc-and-dec) |
| DECW (vector)                        | See [ADDPL, ADDVL, INC and DEC](#addpl-addvl-inc-and-dec) |
| DUP (immediate)                      | [`svdup`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svdup[_n]), [`svdupq`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svdupq[_n]) |
| DUP (indexed)                        | [`svdup_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svdup_lane), [`svdupq_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svdupq_lane) |
| DUP (scalar)                         | [`svdup`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svdup[_n]), [`svdupq`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svdupq[_n]) |
| DUPM                                 | [`svdup`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svdup[_n]), [`svdupq`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svdupq[_n]) |
| EON                                  | [`sveor`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int,uint]&q=sveor[) |
| EOR (immediate)                      | [`sveor`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int,uint]&q=sveor[) |
| EOR (predicates)                     | [`sveor`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[bool]&q=sveor) |
| EOR (vectors, predicated)            | [`sveor`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int,uint]&q=sveor[) |
| EOR (vectors, unpredicated)          | [`sveor`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int,uint]&q=sveor[) |
| EOR3                                 | [`sveor3`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=sveor3) |
| EORBT                                | [`sveorbt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=sveorbt) |
| EORS                                 | [`sveor`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[bool]&q=sveor) |
| EORTB                                | [`sveortb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=sveortb) |
| EORV                                 | [`sveorv`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=sveorv) |
| EXT                                  | [`svext`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svext[) |
| FABD                                 | [`svabd`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svabd[) |
| FABS                                 | [`svabs`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svabs) |
| FACGE                                | [`svacge`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svacge) |
| FACGT                                | [`svacgt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svacgt) |
| FACLE                                | [`svacle`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svacle) |
| FACLT                                | [`svaclt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svaclt) |
| FADD (immediate)                     | [`svadd`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svadd[) |
| FADD (vectors, predicated)           | [`svadd`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svadd[) |
| FADD (vectors, unpredicated)         | [`svadd`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svadd[) |
| FADDA                                | [`svadda`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svadda) |
| FADDP                                | [`svaddp`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svaddp) |
| FADDV                                | [`svaddv`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svaddv) |
| FCADD                                | [`svcadd`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svcadd) |
| FCMEQ (vectors)                      | [`svcmpeq`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svcmpeq) |
| FCMEQ (zero)                         | [`svcmpeq`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svcmpeq) |
| FCMGE (vectors)                      | [`svcmpge`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svcmpge) |
| FCMGE (zero)                         | [`svcmpge`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svcmpge) |
| FCMGT (vectors)                      | [`svcmpgt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svcmpgt) |
| FCMGT (zero)                         | [`svcmpgt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svcmpgt) |
| FCMLA (indexed)                      | [`svcmla`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svcmla) |
| FCMLA (vectors)                      | [`svcmla`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svcmla) |
| FCMLE (vectors)                      | [`svcmple`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svcmple) |
| FCMLE (zero)                         | [`svcmple`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svcmple) |
| FCMLT (vectors)                      | [`svcmplt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svcmplt) |
| FCMLT (zero)                         | [`svcmplt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svcmplt) |
| FCMNE (vectors)                      | [`svcmpne`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svcmpne) |
| FCMNE (zero)                         | [`svcmpne`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svcmpne) |
| FCMUO                                | [`svcmpuo`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svcmpuo) |
| FCPY                                 | [`svdup`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svdup) (predicated forms) |
| FCVT                                 | [`svcvt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svcvt_) |
| FCVTLT                               | [`svcvtlt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svcvtlt) |
| FCVTNT                               | [`svcvtnt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svcvtnt_f) |
| FCVTX                                | [`svcvtx`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svcvtx_) |
| FCVTXNT                              | [`svcvtxnt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svcvtxnt) |
| FCVTZS                               | [`svcvt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svcvt_) |
| FCVTZU                               | [`svcvt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svcvt_) |
| FDIV                                 | [`svdiv`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svdiv[) |
| FDIVR                                | [`svdivr`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svdivr) |
| FDUP                                 | [`svdup`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svdup[_n]) |
| FEXPA                                | [`svexpa`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svexpa) |
| FLOGB                                | [`svlogb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svlogb) |
| FMAD                                 | [`svmad`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svmad) |
| FMAX (immediate)                     | [`svmax`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svmax[) |
| FMAX (vectors)                       | [`svmax`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svmax[) |
| FMAXNM (immediate)                   | [`svmaxnm`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svmaxnm[) |
| FMAXNM (vectors)                     | [`svmaxnm`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svmaxnm[) |
| FMAXNMP                              | [`svmaxnmp`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svmaxnmp) |
| FMAXNMV                              | [`svmaxnmv`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svmaxnmv) |
| FMAXP                                | [`svmaxp`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svmaxp) |
| FMAXV                                | [`svmaxv`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svmaxv) |
| FMIN (immediate)                     | [`svmin`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svmin[) |
| FMIN (vectors)                       | [`svmin`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svmin[) |
| FMINNM (immediate)                   | [`svminnm`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svminnm[) |
| FMINNM (vectors)                     | [`svminnm`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svminnm[) |
| FMINNMP                              | [`svminnmp`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svminnmp) |
| FMINNMV                              | [`svminnmv`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svminnmv) |
| FMINP                                | [`svminp`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svminp) |
| FMINV                                | [`svminv`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svminv) |
| FMLA (indexed)                       | [`svmla`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svmla[) |
| FMLA (vectors)                       | [`svmla`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svmla[) |
| FMLALB (indexed)                     | [`svmlalb_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svmlalb_lane) |
| FMLALB (vectors)                     | [`svmlalb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svmlalb[) |
| FMLALT (indexed)                     | [`svmlalt_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svmlalt_lane) |
| FMLALT (vectors)                     | [`svmlalt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svmlalt[) |
| FMLS (indexed)                       | [`svmls_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svmls_lane) |
| FMLS (vectors)                       | [`svmls`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svmls[) |
| FMLSLB (indexed)                     | [`svmlslb_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svmlslb_lane) |
| FMLSLB (vectors)                     | [`svmlslb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svmlslb[) |
| FMLSLT (indexed)                     | [`svmlslt_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svmlslt_lane) |
| FMLSLT (vectors)                     | [`svmlslt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svmlslt[) |
| FMMLA                                | [`svmmla`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svmmla) |
| FMOV (immediate, predicated)         | [`svdup`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svdup[_n]) |
| FMOV (immediate, unpredicated)       | [`svdup`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svdup[_n]) |
| FMOV (zero, predicated)              | [`svdup`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svdup[_n]) |
| FMOV (zero, unpredicated)            | [`svdup`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svdup[_n]) |
| FMSB                                 | [`svmsb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svmsb) |
| FMUL (immediate)                     | [`svmul`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svmul[) |
| FMUL (indexed)                       | [`svmul`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svmul[) |
| FMUL (vectors, predicated)           | [`svmul`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svmul[) |
| FMUL (vectors, unpredicated)         | [`svmul`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svmul[) |
| FMULX                                | [`svmulx`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svmulx) |
| FNEG                                 | [`svneg`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svneg) |
| FNMAD                                | [`svnmad`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svnmad) |
| FNMLA                                | [`svnmla`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svnmla) |
| FNMLS                                | [`svnmls`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svnmls) |
| FNMSB                                | [`svnmsb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svnmsb) |
| FRECPE                               | [`svrecpe`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svrecpe) |
| FRECPS                               | [`svrecps`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svrecps) |
| FRECPX                               | [`svrecpx`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svrecpx) |
| FRINTA                               | [`svrinta`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svrinta) |
| FRINTI                               | [`svrinti`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svrinti) |
| FRINTM                               | [`svrintm`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svrintm) |
| FRINTN                               | [`svrintn`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svrintn) |
| FRINTP                               | [`svrintp`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svrintp) |
| FRINTX                               | [`svrintx`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svrintx) |
| FRINTZ                               | [`svrintz`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svrintz) |
| FRSQRTE                              | [`svrsqrte`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svrsqrte) |
| FRSQRTS                              | [`svrsqrts`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svrsqrts) |
| FSCALE                               | [`svscale`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svscale) |
| FSQRT                                | [`svsqrt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svsqrt) |
| FSUB (immediate)                     | [`svsub`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svsub[) |
| FSUB (vectors, predicated)           | [`svsub`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svsub[) |
| FSUB (vectors, unpredicated)         | [`svsub`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svsub[) |
| FSUBR (immediate)                    | [`svsubr`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svsubr) |
| FSUBR (vectors)                      | [`svsubr`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svsubr) |
| FTMAD                                | [`svtmad`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svtmad) |
| FTSMUL                               | [`svtsmul`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svtsmul) |
| FTSSEL                               | [`svtssel`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[float]&q=svtssel) |
| HISTCNT                              | [`svhistcnt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svhistcnt) |
| HISTSEG                              | [`svhistseg`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svhistseg) |
| INCB                                 | See [ADDPL, ADDVL, INC and DEC](#addpl-addvl-inc-and-dec) |
| INCD (scalar)                        | See [ADDPL, ADDVL, INC and DEC](#addpl-addvl-inc-and-dec) |
| INCD (vector)                        | See [ADDPL, ADDVL, INC and DEC](#addpl-addvl-inc-and-dec) |
| INCH (scalar)                        | See [ADDPL, ADDVL, INC and DEC](#addpl-addvl-inc-and-dec) |
| INCH (vector)                        | See [ADDPL, ADDVL, INC and DEC](#addpl-addvl-inc-and-dec) |
| INCP (scalar)                        | See [ADDPL, ADDVL, INC and DEC](#addpl-addvl-inc-and-dec) |
| INCP (vector)                        | See [ADDPL, ADDVL, INC and DEC](#addpl-addvl-inc-and-dec) |
| INCW (scalar)                        | See [ADDPL, ADDVL, INC and DEC](#addpl-addvl-inc-and-dec) |
| INCW (vector)                        | See [ADDPL, ADDVL, INC and DEC](#addpl-addvl-inc-and-dec) |
| INDEX (immediate, scalar)            | [`svindex`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svindex) |
| INDEX (immediates)                   | [`svindex`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svindex) |
| INDEX (scalar, immediate)            | [`svindex`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svindex) |
| INDEX (scalars)                      | [`svindex`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svindex) |
| INSR (SIMD & FP scalar)              | [`svinsr`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svinsr) |
| INSR (scalar)                        | [`svinsr`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svinsr) |
| LASTA (SIMD & FP scalar)             | [`svlasta`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svlasta) |
| LASTA (scalar)                       | [`svlasta`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svlasta) |
| LASTB (SIMD & FP scalar)             | [`svlastb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svlastb) |
| LASTB (scalar)                       | [`svlastb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svlastb) |
| LD1B (scalar plus immediate)         | [`svld1_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[8]&q=svld1_vnum), [`svld1ub_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svld1ub_vnum) |
| LD1B (scalar plus scalar)            | [`svld1`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[8]&q=svld1[), [`svld1ub`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#&q=svld1ub) |
| LD1B (scalar plus vector)            | [`svld1ub_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svld1ub_gather_[) |
| LD1B (vector plus immediate)         | [`svld1ub_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svld1ub_gather[) |
| LD1D (scalar plus immediate)         | [`svld1_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[64]&q=svld1_vnum) |
| LD1D (scalar plus scalar)            | [`svld1`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[64]&q=svld1[) |
| LD1D (scalar plus vector)            | [`svld1_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[64]&q=svld1_gather_[) |
| LD1D (vector plus immediate)         | [`svld1_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[64]&q=svld1_gather[) |
| LD1H (scalar plus immediate)         | [`svld1_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[16]&q=svld1_vnum), [`svld1uh_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svld1uh_vnum) |
| LD1H (scalar plus scalar)            | [`svld1`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[16]&q=svld1[), [`svld1uh`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#&q=svld1uh) |
| LD1H (scalar plus vector)            | [`svld1uh_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svld1uh_gather_[) |
| LD1H (vector plus immediate)         | [`svld1uh_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svld1uh_gather[) |
| LD1RB                                | See [SVE LD1R instructions](#sve-ld1r-instructions) |
| LD1RD                                | See [SVE LD1R instructions](#sve-ld1r-instructions) |
| LD1RH                                | See [SVE LD1R instructions](#sve-ld1r-instructions) |
| LD1ROB (scalar plus immediate)       | [`svld1ro`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[8]&q=svld1ro) |
| LD1ROB (scalar plus scalar)          | [`svld1ro`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[8]&q=svld1ro) |
| LD1ROD (scalar plus immediate)       | [`svld1ro`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[64]&q=svld1ro) |
| LD1ROD (scalar plus scalar)          | [`svld1ro`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[64]&q=svld1ro) |
| LD1ROH (scalar plus immediate)       | [`svld1ro`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[16]&q=svld1ro) |
| LD1ROH (scalar plus scalar)          | [`svld1ro`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[16]&q=svld1ro) |
| LD1ROW (scalar plus immediate)       | [`svld1ro`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[32]&q=svld1ro) |
| LD1ROW (scalar plus scalar)          | [`svld1ro`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[32]&q=svld1ro) |
| LD1RQB (scalar plus immediate)       | [`svld1rq`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[8]&q=svld1rq), [`svdupq`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[8]&q=svdupq) |
| LD1RQB (scalar plus scalar)          | [`svld1rq`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[8]&q=svld1rq), [`svdupq`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[8]&q=svdupq) |
| LD1RQD (scalar plus immediate)       | [`svld1rq`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[64]&q=svld1rq), [`svdupq`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[64]&q=svdupq) |
| LD1RQD (scalar plus scalar)          | [`svld1rq`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[64]&q=svld1rq), [`svdupq`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[64]&q=svdupq) |
| LD1RQH (scalar plus immediate)       | [`svld1rq`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[16]&q=svld1rq), [`svdupq`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[16]&q=svdupq) |
| LD1RQH (scalar plus scalar)          | [`svld1rq`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[16]&q=svld1rq), [`svdupq`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[16]&q=svdupq) |
| LD1RQW (scalar plus immediate)       | [`svld1rq`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[32]&q=svld1rq), [`svdupq`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[32]&q=svdupq) |
| LD1RQW (scalar plus scalar)          | [`svld1rq`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[32]&q=svld1rq), [`svdupq`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[32]&q=svdupq) |
| LD1RSB                               | See [SVE LD1R instructions](#sve-ld1r-instructions) |
| LD1RSH                               | See [SVE LD1R instructions](#sve-ld1r-instructions) |
| LD1RSW                               | See [SVE LD1R instructions](#sve-ld1r-instructions) |
| LD1RW                                | See [SVE LD1R instructions](#sve-ld1r-instructions) |
| LD1SB (scalar plus immediate)        | [`svld1sb_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svld1sb_vnum) |
| LD1SB (scalar plus scalar)           | [`svld1sb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svld1sb) |
| LD1SB (scalar plus vector)           | [`svld1sb_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svld1sb_gather_[) |
| LD1SB (vector plus immediate)        | [`svld1sb_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svld1sb_gather[) |
| LD1SH (scalar plus immediate)        | [`svld1sh_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svld1sh_vnum) |
| LD1SH (scalar plus scalar)           | [`svld1sh`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svld1sh) |
| LD1SH (scalar plus vector)           | [`svld1sh_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svld1sh_gather_[) |
| LD1SH (vector plus immediate)        | [`svld1sh_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svld1sh_gather[) |
| LD1SW (scalar plus immediate)        | [`svld1sw_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svld1sw_vnum) |
| LD1SW (scalar plus scalar)           | [`svld1sw`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svld1sw) |
| LD1SW (scalar plus vector)           | [`svld1sw_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svld1sw_gather_[) |
| LD1SW (vector plus immediate)        | [`svld1sw_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svld1sw_gather[) |
| LD1W (scalar plus immediate)         | [`svld1_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[32]&q=svld1_vnum), [`svld1uw_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svld1uw_vnum) |
| LD1W (scalar plus scalar)            | [`svld1`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[32]&q=svld1[), [`svld1uw`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#&q=svld1uw) |
| LD1W (scalar plus vector)            | [`svld1_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[32]&q=svld1_gather_[), [`svld1uw_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svld1uw_gather_[) |
| LD1W (vector plus immediate)         | [`svld1_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[32]&q=svld1_gather[), [`svld1uw_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svld1uw_gather[) |
| LD2B (scalar plus immediate)         | [`svld2_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[8]&q=svld2_vnum) |
| LD2B (scalar plus scalar)            | [`svld2`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[8]&q=svld2[) |
| LD2D (scalar plus immediate)         | [`svld2_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[64]&q=svld2_vnum) |
| LD2D (scalar plus scalar)            | [`svld2`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[64]&q=svld2[) |
| LD2H (scalar plus immediate)         | [`svld2_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[16]&q=svld2_vnum) |
| LD2H (scalar plus scalar)            | [`svld2`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[16]&q=svld2[) |
| LD2W (scalar plus immediate)         | [`svld2_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[32]&q=svld2_vnum) |
| LD2W (scalar plus scalar)            | [`svld2`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[32]&q=svld2[) |
| LD3B (scalar plus immediate)         | [`svld3_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[8]&q=svld3_vnum) |
| LD3B (scalar plus scalar)            | [`svld3`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[8]&q=svld3[) |
| LD3D (scalar plus immediate)         | [`svld3_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[64]&q=svld3_vnum) |
| LD3D (scalar plus scalar)            | [`svld3`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[64]&q=svld3[) |
| LD3H (scalar plus immediate)         | [`svld3_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[16]&q=svld3_vnum) |
| LD3H (scalar plus scalar)            | [`svld3`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[16]&q=svld3[) |
| LD3W (scalar plus immediate)         | [`svld3_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[32]&q=svld3_vnum) |
| LD3W (scalar plus scalar)            | [`svld3`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[32]&q=svld3[) |
| LD4B (scalar plus immediate)         | [`svld4_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[8]&q=svld4_vnum) |
| LD4B (scalar plus scalar)            | [`svld4`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[8]&q=svld4[) |
| LD4D (scalar plus immediate)         | [`svld4_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[64]&q=svld4_vnum) |
| LD4D (scalar plus scalar)            | [`svld4`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[64]&q=svld4[) |
| LD4H (scalar plus immediate)         | [`svld4_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[16]&q=svld4_vnum) |
| LD4H (scalar plus scalar)            | [`svld4`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[16]&q=svld4[) |
| LD4W (scalar plus immediate)         | [`svld4_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[32]&q=svld4_vnum) |
| LD4W (scalar plus scalar)            | [`svld4`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[32]&q=svld4[) |
| LDFF1B (scalar plus scalar)          | [`svldff1`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[8]&q=svldff1[), [`svldff1ub`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svldff1ub) |
| LDFF1B (scalar plus vector)          | [`svldff1ub_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svldff1ub_gather_[) |
| LDFF1B (vector plus immediate)       | [`svldff1ub_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svldff1ub_gather[) |
| LDFF1D (scalar plus scalar)          | [`svldff1`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[64]&q=svldff1[) |
| LDFF1D (scalar plus vector)          | [`svldff1_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[64]&q=svldff1_gather_[) |
| LDFF1D (vector plus immediate)       | [`svldff1_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[64]&q=svldff1_gather[) |
| LDFF1H (scalar plus scalar)          | [`svldff1`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[16]&q=svldff1[), [`svldff1uh`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svldff1uh) |
| LDFF1H (scalar plus vector)          | [`svldff1uh_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svldff1uh_gather_[) |
| LDFF1H (vector plus immediate)       | [`svldff1uh_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svldff1uh_gather[) |
| LDFF1SB (scalar plus scalar)         | [`svldff1sb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svldff1sb) |
| LDFF1SB (scalar plus vector)         | [`svldff1sb_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svldff1sb_gather_[) |
| LDFF1SB (vector plus immediate)      | [`svldff1sb_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svldff1sb_gather[) |
| LDFF1SH (scalar plus scalar)         | [`svldff1sh`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svldff1sh) |
| LDFF1SH (scalar plus vector)         | [`svldff1sh_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svldff1sh_gather_[) |
| LDFF1SH (vector plus immediate)      | [`svldff1sh_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svldff1sh_gather[) |
| LDFF1SW (scalar plus scalar)         | [`svldff1sw`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svldff1sw) |
| LDFF1SW (scalar plus vector)         | [`svldff1sw_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svldff1sw_gather_[) |
| LDFF1SW (vector plus immediate)      | [`svldff1sw_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svldff1sw_gather[) |
| LDFF1W (scalar plus scalar)          | [`svldff1`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[32]&q=svldff1[), [`svldff1uw`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svldff1uw) |
| LDFF1W (scalar plus vector)          | [`svldff1_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[32]&q=svldff1_gather_[), [`svldff1uw_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svldff1uw_gather_[) |
| LDFF1W (vector plus immediate)       | [`svldff1_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[32]&q=svldff1_gather[), [`svldff1uw_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svldff1uw_gather[) |
| LDNF1B                               | [`svldnf1`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[8]&q=svldnf1[), [`svldnf1ub`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svldnf1ub) |
| LDNF1D                               | [`svldnf1`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[64]&q=svldnf1[) |
| LDNF1H                               | [`svldnf1`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[16]&q=svldnf1[), [`svldnf1uh`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svldnf1uh) |
| LDNF1SB                              | [`svldnf1sb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svldnf1sb) |
| LDNF1SH                              | [`svldnf1sh`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svldnf1sh) |
| LDNF1SW                              | [`svldnf1sw`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svldnf1sw) |
| LDNF1W                               | [`svldnf1`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[32]&q=svldnf1[), [`svldnf1uw`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svldnf1uw) |
| LDNT1B (scalar plus immediate)       | [`svldnt1_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[8]&q=svldnt1_vnum) |
| LDNT1B (scalar plus scalar)          | [`svldnt1`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[8]&q=svldnt1[) |
| LDNT1B (vector plus scalar)          | [`svldnt1`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svldnt1_gather), [`svldnt1ub`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svldnt1ub) |
| LDNT1D (scalar plus immediate)       | [`svldnt1_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[64]&q=svldnt1_vnum) |
| LDNT1D (scalar plus scalar)          | [`svldnt1`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[64]&q=svldnt1[) |
| LDNT1D (vector plus scalar)          | [`svldnt1`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svldnt1_gather) |
| LDNT1H (scalar plus immediate)       | [`svldnt1_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[16]&q=svldnt1_vnum) |
| LDNT1H (scalar plus scalar)          | [`svldnt1`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[16]&q=svldnt1[) |
| LDNT1H (vector plus scalar)          | [`svldnt1`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svldnt1_gather), [`svldnt1uh`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svldnt1uh) |
| LDNT1SB                              | [`svldnt1sb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svldnt1sb) |
| LDNT1SH                              | [`svldnt1sh`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svldnt1sh) |
| LDNT1SW                              | [`svldnt1sw`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svldnt1sw) |
| LDNT1W (scalar plus immediate)       | [`svldnt1_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[32]&q=svldnt1_vnum) |
| LDNT1W (scalar plus scalar)          | [`svldnt1`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[32]&q=svldnt1[) |
| LDNT1W (vector plus scalar)          | [`svldnt1`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svldnt1_gather), [`svldnt1uw`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svldnt1uw) |
| LDR (predicate)                      | See [SVE LDR and STR](#sve-ldr-and-str) |
| LDR (vector)                         | See [SVE LDR and STR](#sve-ldr-and-str) |
| LSL (immediate, predicated)          | [`svlsl`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svlsl[) |
| LSL (immediate, unpredicated)        | [`svlsl`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svlsl[) |
| LSL (vectors)                        | [`svlsl`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svlsl[) |
| LSL (wide elements, predicated)      | [`svlsl_wide`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svlsl_wide) |
| LSL (wide elements, unpredicated)    | [`svlsl_wide`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svlsl_wide) |
| LSLR                                 | [`svlsl`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svlsl[) (optimization of `_x` forms) |
| LSR (immediate, predicated)          | [`svlsr`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svlsr[) |
| LSR (immediate, unpredicated)        | [`svlsr`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svlsr[) |
| LSR (vectors)                        | [`svlsr`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svlsr[) |
| LSR (wide elements, predicated)      | [`svlsr_wide`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svlsr_wide) |
| LSR (wide elements, unpredicated)    | [`svlsr_wide`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svlsr_wide) |
| LSRR                                 | [`svlsr`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svlsr[) (optimization of `_x` forms) |
| MAD                                  | [`svmad`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint,int]&q=svmad) |
| MATCH                                | [`svmatch`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svmatch) |
| MLA (indexed)                        | [`svmla_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint,int]&q=svmla_lane) |
| MLA (vectors)                        | [`svmla`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint,int]&q=svmla[) |
| MLS (indexed)                        | [`svmls_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint,int]&q=svmls_lane) |
| MLS (vectors)                        | [`svmls`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint,int]&q=svmls[) |
| MOV (SIMD & FP scalar, predicated)   | [`svdup`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svdup[_n]) |
| MOV (SIMD & FP scalar, unpredicated) | [`svdup`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svdup[_n]) |
| MOV (bitmask immediate)              | [`svdup`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svdup[_n]) |
| MOV (immediate, predicated)          | [`svdup`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svdup[_n]) |
| MOV (immediate, unpredicated)        | [`svdup`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svdup[_n]) |
| MOV (predicate, predicated, merging) | [`svsel`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[bool]&q=svsel) |
| MOV (predicate, predicated, zeroing) | [`svmov`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svmov) |
| MOV (predicate, unpredicated)        | See [SVE MOV](#sve-mov) |
| MOV (scalar, predicated)             | [`svdup`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svdup[_n]) |
| MOV (scalar, unpredicated)           | [`svdup`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svdup[_n]) |
| MOV (vector, predicated)             | [`svsel`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint,int,float,bfloat]&q=svsel) |
| MOV (vector, unpredicated)           | See [SVE MOV](#sve-mov) |
| MOVPRFX (predicated)                 | See [MOVPRFX](#movprfx) |
| MOVPRFX (unpredicated)               | See [MOVPRFX](#movprfx) |
| MOVS (predicated)                    | [`svmov`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svmov) |
| MOVS (unpredicated)                  | See [SVE MOV](#sve-mov) |
| MSB                                  | [`svmsb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint,int]&q=svmsb) |
| MUL (immediate)                      | [`svmul`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint,int]&q=svmul[) |
| MUL (indexed)                        | [`svmul_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint,int]&q=svmul_lane) |
| MUL (vectors, predicated)            | [`svmul`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint,int]&q=svmul[) |
| MUL (vectors, unpredicated)          | [`svmul`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint,int]&q=svmul[) |
| NAND                                 | [`svnand`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svnand) |
| NANDS                                | [`svnand`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svnand) |
| NBSL                                 | [`svnbsl`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svnbsl) |
| NEG                                  | [`svneg`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint,int]&q=svneg) |
| NMATCH                               | [`svnmatch`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svnmatch) |
| NOR                                  | [`svnor`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svnor) |
| NORS                                 | [`svnor`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svnor) |
| NOT (predicate)                      | [`svnot`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[bool]&q=svnot) |
| NOT (vector)                         | [`svnot`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint,int]&q=svnot) |
| NOTS                                 | [`svnot`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[bool]&q=svnot) |
| ORN (immediate)                      | [`svorr`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int,uint]&q=svorr[) |
| ORN (predicates)                     | [`svorn`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svorn) |
| ORNS                                 | [`svorn`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svorn) |
| ORR (immediate)                      | [`svorr`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int,uint]&q=svorr[) |
| ORR (predicates)                     | [`svorr`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[bool]&q=svorr) |
| ORR (vectors, predicated)            | [`svorr`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int,uint]&q=svorr[) |
| ORR (vectors, unpredicated)          | [`svorr`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int,uint]&q=svorr[) |
| ORRS                                 | [`svorr`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[bool]&q=svorr) |
| ORV                                  | [`svorv`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svorv) |
| PFALSE                               | [`svpfalse`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svpfalse) |
| PFIRST                               | [`svpfirst`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svpfirst) |
| PMUL                                 | [`svpmul`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svpmul[) |
| PMULLB                               | [`svpmullb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svpmullb[), [`svpmullb_pair`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svpmullb_pair) |
| PMULLT                               | [`svpmullt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svpmullt[), [`svpmullt_pair`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svpmullt_pair) |
| PNEXT                                | [`svpnext`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svpnext) |
| PRFB (scalar plus immediate)         | [`svprfb_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svprfb_vnum) |
| PRFB (scalar plus scalar)            | [`svprfb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svprfb) |
| PRFB (scalar plus vector)            | [`svprfb_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svprfb_gather_[) |
| PRFB (vector plus immediate)         | [`svprfb_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svprfb_gather[) |
| PRFD (scalar plus immediate)         | [`svprfd_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svprfd_vnum) |
| PRFD (scalar plus scalar)            | [`svprfd`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svprfd) |
| PRFD (scalar plus vector)            | [`svprfd_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svprfd_gather_[) |
| PRFD (vector plus immediate)         | [`svprfd_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svprfd_gather[) |
| PRFH (scalar plus immediate)         | [`svprfh_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svprfh_vnum) |
| PRFH (scalar plus scalar)            | [`svprfh`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svprfh) |
| PRFH (scalar plus vector)            | [`svprfh_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svprfh_gather_[) |
| PRFH (vector plus immediate)         | [`svprfh_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svprfh_gather[) |
| PRFW (scalar plus immediate)         | [`svprfw_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svprfw_vnum) |
| PRFW (scalar plus scalar)            | [`svprfw`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svprfw) |
| PRFW (scalar plus vector)            | [`svprfw_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svprfw_gather_[) |
| PRFW (vector plus immediate)         | [`svprfw_gather`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svprfw_gather[) |
| PTEST                                | [`svptest`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svptest) |
| PTRUE                                | [`svptrue`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svptrue) |
| PTRUES                               | [`svptrue`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svptrue) |
| PUNPKHI                              | [`svunpkhi`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[bool]&q=svunpkhi) |
| PUNPKLO                              | [`svunpklo`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[bool]&q=svunpklo) |
| RADDHNB                              | [`svraddhnb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svraddhnb) |
| RADDHNT                              | [`svraddhnt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svraddhnt) |
| RAX1                                 | [`svrax1`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svrax1) |
| RBIT                                 | [`svrbit`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svrbit) |
| RDFFR (predicated)                   | [`svrdffr`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svrdffr) |
| RDFFR (unpredicated)                 | [`svrdffr`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svrdffr) |
| RDFFRS                               | [`svrdffr`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svrdffr) |
| RDVL                                 | See [RDVL](#rdvl) |
| REV (predicate)                      | [`svrev`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[bool]&q=svrev) |
| REV (vector)                         | [`svrev`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint,int,float,bfloat]&q=svrev) |
| REVB                                 | [`svrevb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svrevb) |
| REVH                                 | [`svrevh`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svrevh) |
| REVW                                 | [`svrevw`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svrevw) |
| RSHRNB                               | [`svrshrnb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svrshrnb) |
| RSHRNT                               | [`svrshrnt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svrshrnt) |
| RSUBHNB                              | [`svrsubhnb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svrsubhnb) |
| RSUBHNT                              | [`svrsubhnt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svrsubhnt) |
| SABA                                 | [`svaba`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svaba[) |
| SABALB                               | [`svabalb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svabalb) |
| SABALT                               | [`svabalt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svabalt) |
| SABD                                 | [`svabd`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svabd[) |
| SABDLB                               | [`svabdlb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svabdlb) |
| SABDLT                               | [`svabdlt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svabdlt) |
| SADALP                               | [`svadalp`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svadalp) |
| SADDLB                               | [`svaddlb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svaddlb[) |
| SADDLBT                              | [`svaddlbt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svaddlbt) |
| SADDLT                               | [`svaddlt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svaddlt) |
| SADDV                                | [`svaddv`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svaddv) |
| SADDWB                               | [`svaddwb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svaddwb) |
| SADDWT                               | [`svaddwt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svaddwt) |
| SBCLB                                | [`svsbclb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svsbclb) |
| SBCLT                                | [`svsbclt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svsbclt) |
| SCVTF                                | [`svcvt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svcvt_) |
| SDIV                                 | [`svdiv`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svdiv[) |
| SDIVR                                | [`svdivr`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svdivr) |
| SDOT (indexed)                       | [`svdot_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svdot_lane) |
| SDOT (vectors)                       | [`svdot`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svdot[) |
| SEL (predicates)                     | [`svsel`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[bool]&q=svsel) |
| SEL (vectors)                        | [`svsel`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint,int,float,bfloat]&q=svsel) |
| SETFFR                               | [`svsetffr`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svsetffr) |
| SHADD                                | [`svhadd`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svhadd) |
| SHRNB                                | [`svshrnb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svshrnb) |
| SHRNT                                | [`svshrnt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svshrnt) |
| SHSUB                                | [`svhsub`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svhsub[) |
| SHSUBR                               | [`svhsubr`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svhsubr) |
| SLI                                  | [`svsli`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svsli) |
| SM4E                                 | [`svsm4e`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svsm4e[) |
| SM4EKEY                              | [`svsm4ekey`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svsm4ekey) |
| SMAX (immediate)                     | [`svmax`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svmax[) |
| SMAX (vectors)                       | [`svmax`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svmax[) |
| SMAXP                                | [`svmaxp`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svmaxp) |
| SMAXV                                | [`svmaxv`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svmaxv) |
| SMIN (immediate)                     | [`svmin`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svmin[) |
| SMIN (vectors)                       | [`svmin`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svmin[) |
| SMINP                                | [`svminp`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svminp) |
| SMINV                                | [`svminv`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svminv) |
| SMLALB (indexed)                     | [`svmlalb_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svmlalb_lane) |
| SMLALB (vectors)                     | [`svmlalb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svmlalb[) |
| SMLALT (indexed)                     | [`svmlalt_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svmlalt_lane) |
| SMLALT (vectors)                     | [`svmlalt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svmlalt[) |
| SMLSLB (indexed)                     | [`svmlslb_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svmlslb_lane) |
| SMLSLB (vectors)                     | [`svmlslb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svmlslb[) |
| SMLSLT (indexed)                     | [`svmlslt_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svmlslt_lane) |
| SMLSLT (vectors)                     | [`svmlslt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svmlslt[) |
| SMMLA                                | [`svmmla`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svmmla) |
| SMULH (predicated)                   | [`svmulh`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svmulh) |
| SMULH (unpredicated)                 | [`svmulh`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svmulh) |
| SMULLB (indexed)                     | [`svmullb_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svmullb_lane) |
| SMULLB (vectors)                     | [`svmullb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svmullb[) |
| SMULLT (indexed)                     | [`svmullt_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svmullt_lane) |
| SMULLT (vectors)                     | [`svmullt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svmullt[) |
| SPLICE                               | [`svsplice`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svsplice) |
| SQABS                                | [`svqabs`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqabs) |
| SQADD (immediate)                    | [`svqadd`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqadd) |
| SQADD (vectors, predicated)          | [`svqadd`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqadd) |
| SQADD (vectors, unpredicated)        | [`svqadd`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqadd) |
| SQCADD                               | [`svqcadd`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqcadd) |
| SQDECB                               | [`svqdecb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqdecb) |
| SQDECD (scalar)                      | [`svqdecd`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqdecd) |
| SQDECD (vector)                      | [`svqdecd`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqdecd) |
| SQDECH (scalar)                      | [`svqdech`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqdech) |
| SQDECH (vector)                      | [`svqdech`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqdech) |
| SQDECP (scalar)                      | [`svqdecp`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqdecp) |
| SQDECP (vector)                      | [`svqdecp`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqdecp) |
| SQDECW (scalar)                      | [`svqdecw`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqdecw) |
| SQDECW (vector)                      | [`svqdecw`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqdecw) |
| SQDMLALB (indexed)                   | [`svqdmlalb_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqdmlalb_lane) |
| SQDMLALB (vectors)                   | [`svqdmlalb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqdmlalb[) |
| SQDMLALBT                            | [`svqdmlalbt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqdmlalbt) |
| SQDMLALT (indexed)                   | [`svqdmlalt_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqdmlalt_lane) |
| SQDMLALT (vectors)                   | [`svqdmlalt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqdmlalt[) |
| SQDMLSLB (indexed)                   | [`svqdmlslb_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqdmlslb_lane) |
| SQDMLSLB (vectors)                   | [`svqdmlslb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqdmlslb[) |
| SQDMLSLBT                            | [`svqdmlslbt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqdmlslbt) |
| SQDMLSLT (indexed)                   | [`svqdmlslt_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqdmlslt_lane) |
| SQDMLSLT (vectors)                   | [`svqdmlslt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqdmlslt[) |
| SQDMULH (indexed)                    | [`svqdmulh_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqdmulh_lane) |
| SQDMULH (vectors)                    | [`svqdmulh`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqdmulh[) |
| SQDMULLB (indexed)                   | [`svqdmullb_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqdmullb_lane) |
| SQDMULLB (vectors)                   | [`svqdmullb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqdmullb[) |
| SQDMULLT (indexed)                   | [`svqdmullt_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqdmullt_lane) |
| SQDMULLT (vectors)                   | [`svqdmullt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqdmullt[) |
| SQINCB                               | [`svqincb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqincb) |
| SQINCD (scalar)                      | [`svqincd`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqincd) |
| SQINCD (vector)                      | [`svqincd`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqincd) |
| SQINCH (scalar)                      | [`svqinch`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqinch) |
| SQINCH (vector)                      | [`svqinch`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqinch) |
| SQINCP (scalar)                      | [`svqincp`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqincp) |
| SQINCP (vector)                      | [`svqincp`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqincp) |
| SQINCW (scalar)                      | [`svqincw`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqincw) |
| SQINCW (vector)                      | [`svqincw`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqincw) |
| SQNEG                                | [`svqneg`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqneg) |
| SQRDCMLAH (indexed)                  | [`svqrdcmlah_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqrdcmlah_lane) |
| SQRDCMLAH (vectors)                  | [`svqrdcmlah`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqrdcmlah[) |
| SQRDMLAH (indexed)                   | [`svqrdmlah_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqrdmlah_lane) |
| SQRDMLAH (vectors)                   | [`svqrdmlah`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqrdmlah[) |
| SQRDMLSH (indexed)                   | [`svqrdmlsh_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqrdmlsh_lane) |
| SQRDMLSH (vectors)                   | [`svqrdmlsh`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqrdmlsh[) |
| SQRDMULH (indexed)                   | [`svqrdmulh_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqrdmulh_lane) |
| SQRDMULH (vectors)                   | [`svqrdmulh`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqrdmulh[) |
| SQRSHL                               | [`svqrshl`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqrshl[) |
| SQRSHLR                              | [`svqrshl`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqrshl[) |
| SQRSHRNB                             | [`svqrshrnb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqrshrnb) |
| SQRSHRNT                             | [`svqrshrnt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqrshrnt) |
| SQRSHRUNB                            | [`svqrshrunb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svqrshrunb) |
| SQRSHRUNT                            | [`svqrshrunt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svqrshrunt) |
| SQSHL (immediate)                    | [`svqshl`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqshl[) |
| SQSHL (vectors)                      | [`svqshl`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqshl[) |
| SQSHLR                               | [`svqshl`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqshl[) |
| SQSHLU                               | [`svqshlu`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#&q=svqshlu) |
| SQSHRNB                              | [`svqshrnb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqshrnb) |
| SQSHRNT                              | [`svqshrnt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqshrnt) |
| SQSHRUNB                             | [`svqshrunb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svqshrunb) |
| SQSHRUNT                             | [`svqshrunt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svqshrunt) |
| SQSUB (immediate)                    | [`svqsub`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqsub[) |
| SQSUB (vectors, predicated)          | [`svqsub`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqsub[) |
| SQSUB (vectors, unpredicated)        | [`svqsub`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqsub[) |
| SQSUBR                               | [`svqsubr`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqsubr) |
| SQXTNB                               | [`svqxtnb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqxtnb) |
| SQXTNT                               | [`svqxtnt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svqxtnt) |
| SQXTUNB                              | [`svqxtunb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svqxtunb) |
| SQXTUNT                              | [`svqxtunt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svqxtunt) |
| SRHADD                               | [`svrhadd`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svrhadd) |
| SRI                                  | [`svsri`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svsri) |
| SRSHL                                | [`svrshl`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svrshl) |
| SRSHLR                               | [`svrshl`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svrshl) |
| SRSHR                                | [`svrshr`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svrshr[) |
| SRSRA                                | [`svrsra`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svrsra) |
| SSHLLB                               | [`svshllb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svshllb), [`svmovlb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svmovlb) |
| SSHLLT                               | [`svshllt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svshllt), [`svmovlt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svmovlt) |
| SSRA                                 | [`svsra`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svsra) |
| SSUBLB                               | [`svsublb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svsublb[) |
| SSUBLBT                              | [`svsublbt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svsublbt) |
| SSUBLT                               | [`svsublt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svsublt[) |
| SSUBLTB                              | [`svsubltb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svsubltb) |
| SSUBWB                               | [`svsubwb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svsubwb) |
| SSUBWT                               | [`svsubwt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svsubwt) |
| ST1B (scalar plus immediate)         | [`svst1_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst1_vnum), [`svst1b_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst1b_vnum) |
| ST1B (scalar plus scalar)            | [`svst1`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst1[), [`svst1b`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst1b) |
| ST1B (scalar plus vector)            | [`svst1b_scatter`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst1b_scatter_[) |
| ST1B (vector plus immediate)         | [`svst1b_scatter`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst1b_scatter[) |
| ST1D (scalar plus immediate)         | [`svst1_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst1_vnum) |
| ST1D (scalar plus scalar)            | [`svst1`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst1[) |
| ST1D (scalar plus vector)            | [`svst1_scatter`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst1_scatter_[) |
| ST1D (vector plus immediate)         | [`svst1_scatter`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst1_scatter[) |
| ST1H (scalar plus immediate)         | [`svst1_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst1_vnum), [`svst1h_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst1h_vnum) |
| ST1H (scalar plus scalar)            | [`svst1`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst1[), [`svst1h`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst1h) |
| ST1H (scalar plus vector)            | [`svst1h_scatter`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst1h_scatter_[) |
| ST1H (vector plus immediate)         | [`svst1h_scatter`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst1h_scatter[) |
| ST1W (scalar plus immediate)         | [`svst1_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst1_vnum), [`svst1w_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst1w_vnum) |
| ST1W (scalar plus scalar)            | [`svst1`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst1[), [`svst1w`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst1w) |
| ST1W (scalar plus vector)            | [`svst1_scatter`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst1_scatter_[), [`svst1w_scatter`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst1w_scatter_[) |
| ST1W (vector plus immediate)         | [`svst1_scatter`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst1_scatter[), [`svst1w_scatter`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst1w_scatter[) |
| ST2B (scalar plus immediate)         | [`svst2_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst2_vnum) |
| ST2B (scalar plus scalar)            | [`svst2`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst2[) |
| ST2D (scalar plus immediate)         | [`svst2_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst2_vnum) |
| ST2D (scalar plus scalar)            | [`svst2`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst2[) |
| ST2H (scalar plus immediate)         | [`svst2_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst2_vnum) |
| ST2H (scalar plus scalar)            | [`svst2`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst2[) |
| ST2W (scalar plus immediate)         | [`svst2_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst2_vnum) |
| ST2W (scalar plus scalar)            | [`svst2`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst2[) |
| ST3B (scalar plus immediate)         | [`svst3_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst3_vnum) |
| ST3B (scalar plus scalar)            | [`svst3`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst3[) |
| ST3D (scalar plus immediate)         | [`svst3_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst3_vnum) |
| ST3D (scalar plus scalar)            | [`svst3`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst3[) |
| ST3H (scalar plus immediate)         | [`svst3_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst3_vnum) |
| ST3H (scalar plus scalar)            | [`svst3`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst3[) |
| ST3W (scalar plus immediate)         | [`svst3_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst3_vnum) |
| ST3W (scalar plus scalar)            | [`svst3`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst3[) |
| ST4B (scalar plus immediate)         | [`svst4_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst4_vnum) |
| ST4B (scalar plus scalar)            | [`svst4`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst4[) |
| ST4D (scalar plus immediate)         | [`svst4_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst4_vnum) |
| ST4D (scalar plus scalar)            | [`svst4`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst4[) |
| ST4H (scalar plus immediate)         | [`svst4_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst4_vnum) |
| ST4H (scalar plus scalar)            | [`svst4`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst4[) |
| ST4W (scalar plus immediate)         | [`svst4_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst4_vnum) |
| ST4W (scalar plus scalar)            | [`svst4`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst4[) |
| STNT1B (scalar plus immediate)       | [`svstnt1_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svstnt1_vnum) |
| STNT1B (scalar plus scalar)          | [`svstnt1`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svstnt1[) |
| STNT1B (vector plus scalar)          | [`svstnt1_scatter`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svstnt1_scatter), [`svstnt1b`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svstnt1b) |
| STNT1D (scalar plus immediate)       | [`svstnt1_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svstnt1_vnum) |
| STNT1D (scalar plus scalar)          | [`svstnt1`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svstnt1[) |
| STNT1D (vector plus scalar)          | [`svstnt1_scatter`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svstnt1_scatter) |
| STNT1H (scalar plus immediate)       | [`svstnt1_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svstnt1_vnum) |
| STNT1H (scalar plus scalar)          | [`svstnt1`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svstnt1[) |
| STNT1H (vector plus scalar)          | [`svstnt1_scatter`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svstnt1_scatter), [`svstnt1h`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svstnt1h) |
| STNT1W (scalar plus immediate)       | [`svstnt1_vnum`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svstnt1_vnum) |
| STNT1W (scalar plus scalar)          | [`svstnt1`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svstnt1[) |
| STNT1W (vector plus scalar)          | [`svstnt1_scatter`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svstnt1_scatter), [`svstnt1w`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svstnt1w) |
| STR (predicate)                      | See [SVE LDR and STR](#sve-ldr-and-str) |
| STR (vector)                         | See [SVE LDR and STR](#sve-ldr-and-str) |
| SUB (immediate)                      | [`svsub`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint,int]&q=svsub[) |
| SUB (vectors, predicated)            | [`svsub`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint,int]&q=svsub[) |
| SUB (vectors, unpredicated)          | [`svsub`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint,int]&q=svsub[) |
| SUBHNB                               | [`svsubhnb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svsubhnb) |
| SUBHNT                               | [`svsubhnt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svsubhnt) |
| SUBR (immediate)                     | [`svsubr`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint,int]&q=svsubr) |
| SUBR (vectors)                       | [`svsubr`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint,int]&q=svsubr) |
| SUDOT                                | [`svsudot_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svsudot_lane) |
| SUNPKHI                              | [`svunpkhi`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svunpkhi) |
| SUNPKLO                              | [`svunpklo`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svunpklo) |
| SUQADD                               | [`svuqadd`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svuqadd) |
| SXTB                                 | [`svextb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svextb) |
| SXTH                                 | [`svexth`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svexth) |
| SXTW                                 | [`svextw`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svextw) |
| TBL                                  | [`svtbl`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svtbl[), [`svdup_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svdup_lane) |
| TBX                                  | [`svtbx`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svtbx) |
| TRN1 (predicates)                    | [`svtrn1`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[bool]&q=svtrn1) |
| TRN1 (vectors)                       | [`svtrn1`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint,int,float,bfloat]&q=svtrn1) |
| TRN2 (predicates)                    | [`svtrn2`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[bool]&q=svtrn2) |
| TRN2 (vectors)                       | [`svtrn2`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint,int,float,bfloat]&q=svtrn2) |
| UABA                                 | [`svaba`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svaba[) |
| UABALB                               | [`svabalb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svabalb) |
| UABALT                               | [`svabalt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svabalt) |
| UABD                                 | [`svabd`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svabd[) |
| UABDLB                               | [`svabdlb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svabdlb) |
| UABDLT                               | [`svabdlt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svabdlt) |
| UADALP                               | [`svadalp`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svadalp) |
| UADDLB                               | [`svaddlb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svaddlb[) |
| UADDLT                               | [`svaddlt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svaddlt) |
| UADDV                                | [`svaddv`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint,int]&q=svaddv) |
| UADDWB                               | [`svaddwb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svaddwb) |
| UADDWT                               | [`svaddwt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svaddwt) |
| UCVTF                                | [`svcvt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svcvt_) |
| UDIV                                 | [`svdiv`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svdiv[) |
| UDIVR                                | [`svdivr`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svdivr) |
| UDOT (indexed)                       | [`svdot_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svdot_lane) |
| UDOT (vectors)                       | [`svdot`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svdot[) |
| UHADD                                | [`svhadd`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svhadd) |
| UHSUB                                | [`svhsub`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svhsub[) |
| UHSUBR                               | [`svhsubr`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svhsubr) |
| UMAX (immediate)                     | [`svmax`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svmax[) |
| UMAX (vectors)                       | [`svmax`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svmax[) |
| UMAXP                                | [`svmaxp`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svmaxp) |
| UMAXV                                | [`svmaxv`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svmaxv) |
| UMIN (immediate)                     | [`svmin`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svmin[) |
| UMIN (vectors)                       | [`svmin`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svmin[) |
| UMINP                                | [`svminp`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svminp) |
| UMINV                                | [`svminv`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svminv) |
| UMLALB (indexed)                     | [`svmlalb_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svmlalb_lane) |
| UMLALB (vectors)                     | [`svmlalb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svmlalb[) |
| UMLALT (indexed)                     | [`svmlalt_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svmlalt_lane) |
| UMLALT (vectors)                     | [`svmlalt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svmlalt[) |
| UMLSLB (indexed)                     | [`svmlslb_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svmlslb_lane) |
| UMLSLB (vectors)                     | [`svmlslb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svmlslb[) |
| UMLSLT (indexed)                     | [`svmlslt_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svmlslt_lane) |
| UMLSLT (vectors)                     | [`svmlslt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svmlslt[) |
| UMMLA                                | [`svmmla`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svmmla) |
| UMULH (predicated)                   | [`svmulh`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svmulh) |
| UMULH (unpredicated)                 | [`svmulh`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svmulh) |
| UMULLB (indexed)                     | [`svmullb_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svmullb_lane) |
| UMULLB (vectors)                     | [`svmullb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svmullb[) |
| UMULLT (indexed)                     | [`svmullt_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svmullt_lane) |
| UMULLT (vectors)                     | [`svmullt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svmullt[) |
| UQADD (immediate)                    | [`svqadd`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svqadd[) |
| UQADD (vectors, predicated)          | [`svqadd`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svqadd) |
| UQADD (vectors, unpredicated)        | [`svqadd`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svqadd[) |
| UQDECB                               | [`svqdecb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svqdecb) |
| UQDECD (scalar)                      | [`svqdecd`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svqdecd) |
| UQDECD (vector)                      | [`svqdecd`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svqdecd) |
| UQDECH (scalar)                      | [`svqdech`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svqdech) |
| UQDECH (vector)                      | [`svqdech`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svqdech) |
| UQDECP (scalar)                      | [`svqdecp`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svqdecp) |
| UQDECP (vector)                      | [`svqdecp`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svqdecp) |
| UQDECW (scalar)                      | [`svqdecw`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svqdecw) |
| UQDECW (vector)                      | [`svqdecw`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svqdecw) |
| UQINCB                               | [`svqincb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svqincb) |
| UQINCD (scalar)                      | [`svqincd`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svqincd) |
| UQINCD (vector)                      | [`svqincd`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svqincd) |
| UQINCH (scalar)                      | [`svqinch`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svqinch) |
| UQINCH (vector)                      | [`svqinch`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svqinch) |
| UQINCP (scalar)                      | [`svqincp`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svqincp) |
| UQINCP (vector)                      | [`svqincp`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svqincp) |
| UQINCW (scalar)                      | [`svqincw`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svqincw) |
| UQINCW (vector)                      | [`svqincw`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svqincw) |
| UQRSHL                               | [`svqrshl`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svqrshl[) |
| UQRSHLR                              | [`svqrshl`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svqrshl[) |
| UQRSHRNB                             | [`svqrshrnb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svqrshrnb) |
| UQRSHRNT                             | [`svqrshrnt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svqrshrnt) |
| UQSHL (immediate)                    | [`svqshl`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svqshl[) |
| UQSHL (vectors)                      | [`svqshl`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svqshl[) |
| UQSHLR                               | [`svqshl`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svqshl[) |
| UQSHRNB                              | [`svqshrnb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svqshrnb) |
| UQSHRNT                              | [`svqshrnt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svqshrnt) |
| UQSUB (immediate)                    | [`svqsub`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svqsub[) |
| UQSUB (vectors, predicated)          | [`svqsub`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svqsub[) |
| UQSUB (vectors, unpredicated)        | [`svqsub`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svqsub[) |
| UQSUBR                               | [`svqsubr`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svqsubr) |
| UQXTNB                               | [`svqxtnb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svqxtnb) |
| UQXTNT                               | [`svqxtnt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svqxtnt) |
| URECPE                               | [`svrecpe`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svrecpe) |
| URHADD                               | [`svrhadd`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svrhadd) |
| URSHL                                | [`svrshl`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svrshl) |
| URSHLR                               | [`svrshl`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svrshl) |
| URSHR                                | [`svrshr`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svrshr[) |
| URSQRTE                              | [`svrsqrte`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svrsqrte) |
| URSRA                                | [`svrsra`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svrsra) |
| USDOT (indexed)                      | [`svusdot_lane`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svusdot_lane) |
| USDOT (vectors)                      | [`svusdot`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svusdot[), [`svsudot`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svsudot[) |
| USHLLB                               | [`svshllb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svshllb), [`svmovlb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svmovlb) |
| USHLLT                               | [`svshllt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svshllt), [`svmovlt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svmovlt) |
| USMMLA                               | [`svusmmla`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svusmmla) |
| USQADD                               | [`svsqadd`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svsqadd) |
| USRA                                 | [`svsra`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svsra) |
| USUBLB                               | [`svsublb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svsublb[) |
| USUBLT                               | [`svsublt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svsublt[) |
| USUBWB                               | [`svsubwb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svsubwb) |
| USUBWT                               | [`svsubwt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svsubwt) |
| UUNPKHI                              | [`svunpkhi`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svunpkhi) |
| UUNPKLO                              | [`svunpklo`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svunpklo) |
| UXTB                                 | [`svextb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svextb) |
| UXTH                                 | [`svexth`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svexth) |
| UXTW                                 | [`svextw`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svextw) |
| UZP1 (predicates)                    | [`svuzp1`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[bool]&q=svuzp1) |
| UZP1 (vectors)                       | [`svuzp1`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint,int,float,bfloat]&q=svuzp1) |
| UZP2 (predicates)                    | [`svuzp2`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[bool]&q=svuzp2) |
| UZP2 (vectors)                       | [`svuzp2`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint,int,float,bfloat]&q=svuzp2) |
| WHILEGE                              | [`svwhilege`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svwhilege) |
| WHILEGT                              | [`svwhilegt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svwhilegt) |
| WHILEHI                              | [`svwhilegt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svwhilegt) |
| WHILEHS                              | [`svwhilege`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svwhilege) |
| WHILELE                              | [`svwhilele`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svwhilele) |
| WHILELO                              | [`svwhilelt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svwhilelt) |
| WHILELS                              | [`svwhilele`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint]&q=svwhilele) |
| WHILELT                              | [`svwhilelt`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[int]&q=svwhilelt) |
| WHILERW                              | [`svwhilerw`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svwhilerw) |
| WHILEWR                              | [`svwhilewr`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svwhilewr) |
| WRFFR                                | [`svwrffr`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svwrffr) |
| XAR                                  | [`svxar`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svxar) |
| ZIP1 (predicates)                    | [`svzip1`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[bool]&q=svzip1) |
| ZIP1 (vectors)                       | [`svzip1`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint,int,float,bfloat]&q=svzip1) |
| ZIP2 (predicates)                    | [`svzip2`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[bool]&q=svzip2) |
| ZIP2 (vectors)                       | [`svzip2`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchiesreturnbasetype=[uint,int,float,bfloat]&q=svzip2) |

#### ADDPL, ADDVL, INC and DEC

The architecture provides instructions for adding or subtracting an
element count, where the count might come from a pattern (such as
[`svcntb_pat`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svcntb_pat))
or from a predicate
([`svcntp`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svcntp)).
For example, INCH adds the number of halfwords in a pattern to a scalar
register or to every element of a vector register.

At the C and C++ level it is usually simpler to write the addition out
normally. Also, having intrinsics that map directly to architectural
instructions like INCH could cause confusion for pointers, since the
instructions would operate on the raw integer value of the pointer. For
example, applying INCH to a pointer to halfwords would effectively
convert the pointer to an integer, add the number of halfwords, and then
convert the result back to a pointer. The pointer would then only
advance by half a vector.

For these reasons there are no dedicated ACLE intrinsics for:

*   ADDPL and ADDVL

*   DECB, DECH, DECW, DECD, and DECP

*   INCB, INCH, INCW, INCD, and INCP

Instead the implementation should use these instructions to optimize things
like:

``` c
  svbool_t p1;
  ...
  x += svcntp_b16(p1, p1);
```

The same concerns do not apply to saturating scalar arithmetic, since
using saturating arithmetic only makes sense for displacements rather
than pointers. There is also no standard way of doing a saturating
addition or subtraction of arbitrary integers. ACLE does therefore
provide intrinsics for:

*   SQDECB, SQDECH, SQDECW, SQDECD, and SQDECP

*   SQINCB, SQINCH, SQINCW, SQINCD, and SQINCP

*   UQDECB, UQDECH, UQDECW, UQDECD, and UQDECP

*   UQINCB, UQINCH, UQINCW, UQINCD, and UQINCP

#### CTERMEQ and CTERMNE

CTERMEQ and CTERMNE provide a way of optimizing conditions such as:

``` c
  svbool_t p1, p2;
  uint64_t x, y;
  ...
  if (svptest_last(p1, p2) && x == y)
    ...stmts...
```

Here the implementation could use PTEST to test whether the last active
element of `p2` is active and follow it by CTERMNE to test whether
`x` is not equal to `y`. The code should then execute `stmts` if the
LT condition holds (that is, if the last element is active and the
“termination condition” `x != y` does not hold).

There are no ACLE intrinsics that perform a combined predicate and scalar
test since the separate tests should be more readable.

#### MOVPRFX

There are no separate ACLE intrinsics for MOVPRFX, but its use
is implicit in many of the zeroing intrinsics. For example,
[`svadd[_s32]_z`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svadd[_s32]_z)
uses a MOVPRFX before the ADD instruction.

The code generator can also use MOVPRFX to optimize calls
to many `_x` and `_m` intrinsics. For example,
[`svdiv[_s32]_x`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svdiv[_s32]_x)
can use DIV to tie the result to the first operand, DIVR to tie the
result to the second operand, or a combination of MOVPRFX and DIV
to store the result to a separate register.

#### RDVL

There is no separate ACLE intrinsic for RDVL, but the same functionality
is available though the [`svcntb`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svcntb),
[`svcnth`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svcnth),
[`svcntw`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svcntw), and
[`svcntd`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svcntd)
intrinsics.

#### SVE LD1R instructions

There are no separate ACLE intrinsics for LD1RB, LD1RH, LD1RW, LD1RD,
LD1RSB, LD1RSH, and LD1RSW. However, the code generator can use these
instructions to optimize calls to
[`svdup`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svdup[_n])
in which the scalar argument comes from memory.

#### SVE LDR and STR

There are no separate ACLE intrinsics for SVE LDR and STR instructions,
but the code generator can use these instructions to save and restore
SVE registers, or to optimize calls to intrinsics like
[`svld1`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#f:@navigationhierarchieselementbitsize=[8]&q=svld1[)
and
[`svst1`](https://developer.arm.com/architectures/instruction-sets/intrinsics/#q=svst1[).

#### SVE MOV

There are no ACLE intrinsics for the unpredicated SVE MOV instructions.
This is because the ACLE intrinsic calls do not imply a particular
register allocation and so the code generator must decide for itself
when move instructions are required.


### SVE2 BFloat16 data-processing instructions.

The specification for B16B16 is in
[**Beta** state](#support-levels) and might change or be
extended in the future.

The instructions in this section are available when `__ARM_FEATURE_SVE_B16B16`
is non-zero.

#### BFADD, BFSUB

BFloat16 floating-point add and sub (vectors)

``` c
  svbfloat16_t svadd[_bf16]_m (svbool_t pg, svbfloat16_t zdn, svbfloat16_t zm);
  svbfloat16_t svadd[_bf16]_x (svbool_t pg, svbfloat16_t zdn, svbfloat16_t zm);
  svbfloat16_t svadd[_bf16]_z (svbool_t pg, svbfloat16_t zdn, svbfloat16_t zm);
  svbfloat16_t svadd[_n_bf16]_m (svbool_t pg, svbfloat16_t zdn, bfloat16_t zm);
  svbfloat16_t svadd[_n_bf16]_x (svbool_t pg, svbfloat16_t zdn, bfloat16_t zm);
  svbfloat16_t svadd[_n_bf16]_z (svbool_t pg, svbfloat16_t zdn, bfloat16_t zm);

  svbfloat16_t svsub[_bf16]_m (svbool_t pg, svbfloat16_t zdn, svbfloat16_t zm);
  svbfloat16_t svsub[_bf16]_x (svbool_t pg, svbfloat16_t zdn, svbfloat16_t zm);
  svbfloat16_t svsub[_bf16]_z (svbool_t pg, svbfloat16_t zdn, svbfloat16_t zm);
  svbfloat16_t svsub[_n_bf16]_m (svbool_t pg, svbfloat16_t zdn, bfloat16_t zm);
  svbfloat16_t svsub[_n_bf16]_x (svbool_t pg, svbfloat16_t zdn, bfloat16_t zm);
  svbfloat16_t svsub[_n_bf16]_z (svbool_t pg, svbfloat16_t zdn, bfloat16_t zm);
  ```

#### BFCLAMP

BFloat16 Clamp to minimum/maximum vector.

``` c
  svbfloat16_t svclamp[_bf16](svbfloat16_t op, svbfloat16_t min, svbfloat16_t max);
  ```

#### BFMAX, BFMIN

BFloat16 floating-point maximum/minimum (predicated).

 ``` c
   svbfloat16_t svmax[_bf16]_m(svbool_t pg, svbfloat16_t zdn, svbfloat16_t zm);
   svbfloat16_t svmax[_bf16]_z(svbool_t pg, svbfloat16_t zdn, svbfloat16_t zm);
   svbfloat16_t svmax[_bf16]_x(svbool_t pg, svbfloat16_t zdn, svbfloat16_t zm);
   svbfloat16_t svmax[_n_bf16]_m(svbool_t pg, svbfloat16_t zdn, bfloat16_t zm);
   svbfloat16_t svmax[_n_bf16]_z(svbool_t pg, svbfloat16_t zdn, bfloat16_t zm);
   svbfloat16_t svmax[_n_bf16]_x(svbool_t pg, svbfloat16_t zdn, bfloat16_t zm);

   svbfloat16_t svmin[_bf16]_m(svbool_t pg, svbfloat16_t zdn, svbfloat16_t zm);
   svbfloat16_t svmin[_bf16]_z(svbool_t pg, svbfloat16_t zdn, svbfloat16_t zm);
   svbfloat16_t svmin[_bf16]_x(svbool_t pg, svbfloat16_t zdn, svbfloat16_t zm);
   svbfloat16_t svmin[_n_bf16]_m(svbool_t pg, svbfloat16_t zdn, bfloat16_t zm);
   svbfloat16_t svmin[_n_bf16]_z(svbool_t pg, svbfloat16_t zdn, bfloat16_t zm);
   svbfloat16_t svmin[_n_bf16]_x(svbool_t pg, svbfloat16_t zdn, bfloat16_t zm);
   ```

#### BFMAXNM, BFMINNM

BFloat16 floating-point maximum/minimum number (predicated).

 ``` c
   svbfloat16_t svmaxnm[_bf16]_m(svbool_t pg, svbfloat16_t zdn, svbfloat16_t zm);
   svbfloat16_t svmaxnm[_bf16]_z(svbool_t pg, svbfloat16_t zdn, svbfloat16_t zm);
   svbfloat16_t svmaxnm[_bf16]_x(svbool_t pg, svbfloat16_t zdn, svbfloat16_t zm);
   svbfloat16_t svmaxnm[_n_bf16]_m(svbool_t pg, svbfloat16_t zdn, bfloat16_t zm);
   svbfloat16_t svmaxnm[_n_bf16]_z(svbool_t pg, svbfloat16_t zdn, bfloat16_t zm);
   svbfloat16_t svmaxnm[_n_bf16]_x(svbool_t pg, svbfloat16_t zdn, bfloat16_t zm);

   svbfloat16_t svminnm[_bf16]_m(svbool_t pg, svbfloat16_t zdn, svbfloat16_t zm);
   svbfloat16_t svminnm[_bf16]_z(svbool_t pg, svbfloat16_t zdn, svbfloat16_t zm);
   svbfloat16_t svminnm[_bf16]_x(svbool_t pg, svbfloat16_t zdn, svbfloat16_t zm);
   svbfloat16_t svminnm[_n_bf16]_m(svbool_t pg, svbfloat16_t zdn, bfloat16_t zm);
   svbfloat16_t svminnm[_n_bf16]_z(svbool_t pg, svbfloat16_t zdn, bfloat16_t zm);
   svbfloat16_t svminnm[_n_bf16]_x(svbool_t pg, svbfloat16_t zdn, bfloat16_t zm);
   ```

#### BFMLA, BFMLS

BFloat16 floating-point fused multiply add or sub vectors.

 ``` c
   svbfloat16_t svmla[_bf16]_m(svbool_t pg, svbfloat16_t zda, svbfloat16_t zn,
                               svbfloat16_t zm);
   svbfloat16_t svmla[_bf16]_z(svbool_t pg, svbfloat16_t zda, svbfloat16_t zn,
                               svbfloat16_t zm);
   svbfloat16_t svmla[_bf16]_x(svbool_t pg, svbfloat16_t zda, svbfloat16_t zn,
                               svbfloat16_t zm);
   svbfloat16_t svmla[_n_bf16]_m(svbool_t pg, svbfloat16_t zda, svbfloat16_t zn,
                                 bfloat16_t zm);
   svbfloat16_t svmla[_n_bf16]_z(svbool_t pg, svbfloat16_t zda, svbfloat16_t zn,
                                 bfloat16_t zm);
   svbfloat16_t svmla[_n_bf16]_x(svbool_t pg, svbfloat16_t zda, svbfloat16_t zn,
                                 bfloat16_t zm);

   svbfloat16_t svmla_lane[_bf16](svbfloat16_t zda, svbfloat16_t zn,
                                  svbfloat16_t zm, uint64_t imm_idx);

   svbfloat16_t svmls[_bf16]_m(svbool_t pg, svbfloat16_t zda, svbfloat16_t zn,
                               svbfloat16_t zm);
   svbfloat16_t svmls[_bf16]_z(svbool_t pg, svbfloat16_t zda, svbfloat16_t zn,
                               svbfloat16_t zm);
   svbfloat16_t svmls[_bf16]_x(svbool_t pg, svbfloat16_t zda, svbfloat16_t zn,
                               svbfloat16_t zm);
   svbfloat16_t svmls[_n_bf16]_m(svbool_t pg, svbfloat16_t zda, svbfloat16_t zn,
                                 bfloat16_t zm);
   svbfloat16_t svmls[_n_bf16]_z(svbool_t pg, svbfloat16_t zda, svbfloat16_t zn,
                                 bfloat16_t zm);
   svbfloat16_t svmls[_n_bf16]_x(svbool_t pg, svbfloat16_t zda, svbfloat16_t zn,
                                 bfloat16_t zm);

   svbfloat16_t svmls_lane[_bf16](svbfloat16_t zda, svbfloat16_t zn,
                                  svbfloat16_t zm, uint64_t imm_idx);
   ```

#### BFMUL

BFloat16 floating-point multiply vectors.

 ``` c
   svbfloat16_t svmul[_bf16]_m(svbool_t pg, svbfloat16_t zdn, svbfloat16_t zm);
   svbfloat16_t svmul[_bf16]_x(svbool_t pg, svbfloat16_t zdn, svbfloat16_t zm);
   svbfloat16_t svmul[_bf16]_z(svbool_t pg, svbfloat16_t zdn, svbfloat16_t zm);
   svbfloat16_t svmul[_n_bf16]_m(svbool_t pg, svbfloat16_t zdn, bfloat16_t zm);
   svbfloat16_t svmul[_n_bf16]_x(svbool_t pg, svbfloat16_t zdn, bfloat16_t zm);
   svbfloat16_t svmul[_n_bf16]_z(svbool_t pg, svbfloat16_t zdn, bfloat16_t zm);

   svbfloat16_t svmul_lane[_bf16](svbfloat16_t zn, svbfloat16_t zm,
                                  uint64_t imm_idx);
   ```

### SVE BFloat16 floating-point adjust exponent vectors instructions.

The specification for SVE BFloat16 floating-point adjust exponent vectors instructions is in
[**Beta** state](#support-levels) and might change or be
extended in the future.

#### BFSCALE

BFloat16 floating-point adjust exponent vectors.

``` c
  // Only if __ARM_FEATURE_SVE_BFSCALE != 0
  svbfloat16_t svscale[_bf16]_m (svbool_t pg, svbfloat16_t zdn, svint16_t zm);
  svbfloat16_t svscale[_bf16]_x (svbool_t pg, svbfloat16_t zdn, svint16_t zm);
  svbfloat16_t svscale[_bf16]_z (svbool_t pg, svbfloat16_t zdn, svint16_t zm);
  svbfloat16_t svscale[_n_bf16]_m (svbool_t pg, svbfloat16_t zdn, int16_t zm);
  svbfloat16_t svscale[_n_bf16]_x (svbool_t pg, svbfloat16_t zdn, int16_t zm);
  svbfloat16_t svscale[_n_bf16]_z (svbool_t pg, svbfloat16_t zdn, int16_t zm);
  ```

### SVE2 floating-point matrix multiply-accumulate instructions.

#### BFMMLA, FMMLA (non-widening)

16-bit floating-point matrix multiply-accumulate.
```c
  // Only if __ARM_FEATURE_SVE_B16MM
  // Variant also available for _f16 if (__ARM_FEATURE_SVE2p2 && __ARM_FEATURE_F16MM).
  svbfloat16_t svmmla[_bf16](svbfloat16_t zda, svbfloat16_t zn, svbfloat16_t zm);
```

#### FMMLA (widening, FP8 to FP16)

Modal 8-bit floating-point matrix multiply-accumulate to half-precision.
```c
  // Only if (__ARM_FEATURE_SVE2 && __ARM_FEATURE_F8F16MM)
  svfloat16_t svmmla[_f16_mf8]_fpm(svfloat16_t zda, svmfloat8_t zn, svmfloat8_t zm, fpm_t fpm);
```

#### FMMLA (widening, FP8 to FP32)

Modal 8-bit floating-point matrix multiply-accumulate to single-precision.
```c
  // Only if (__ARM_FEATURE_SVE2 && __ARM_FEATURE_F8F32MM)
  svfloat32_t svmmla[_f32_mf8]_fpm(svfloat32_t zda, svmfloat8_t zn, svmfloat8_t zm, fpm_t fpm);
```
#### FMMLA (widening, FP16 to FP32)

16-bit floating-point matrix multiply-accumulate to single-precision.
```c
  // Only if __ARM_FEATURE_SVE_F16F32MM
  svfloat32_t svmmla[_f32_f16](svfloat32_t zda, svfloat16_t zn, svfloat16_t zm);
```

### SVE2.1 instruction intrinsics

The specification for SVE2.1 is in
[**Beta** state](#support-levels) and might change or be
extended in the future.

The functions in this section are available when `__ARM_FEATURE_SVE2p1`
is defined.

Some instructions overlap with the SME and SME2 architecture extensions and
are additionally available in Streaming SVE mode when __ARM_FEATURE_SME is
non-zero or __ARM_FEATURE_SME2 are non-zero.
For convenience, the intrinsics for these instructions  are listed in the
 following section.

#### Multi-vector predicates

When `__ARM_FEATURE_SVE2p1` is defined, the tuple types `svboolx2_t` and
`svboolx4_t` are available.

These are opaque tuple types that can be accessed using the SVE intrinsics
`svsetN`, `svgetN` and `svcreateN`. `svundef2` and `svundef4` are also extended
to work with `svboolx2_t` and `svboolx4_t`.  For example:

``` c
    svbool_t svget2[_b](svboolx2_t tuple, uint64_t imm_index);
    svboolx2_t svset2[_b](svboolx2_t tuple, uint64_t imm_index, svbool_t x);
    svboolx2_t svcreate2[_b](svbool_t x, svbool_t y);
    svboolx2_t svundef2_b();
```

#### ADDQV, FADDQV

Unsigned/FP add reduction of quadword vector segments.

``` c
  // Variants are also available for:
  // _s8, _s16, _u16, _s32, _u32, _s64, _u64,
  // _f16, _f32, _f64
  uint8x16_t svaddqv[_u8](svbool_t pg, svuint8_t zn);
  ```

#### ANDQV, EORQV, ORQV

Reduction of quadword vector segments.

``` c
  // Variants are also available for:
  // _s8, _u16, _s16, _u32, _s32, _u64, _s64
  uint8x16_t svandqv[_u8](svbool_t pg, svuint8_t zn);
  uint8x16_t sveorqv[_u8](svbool_t pg, svuint8_t zn);
  uint8x16_t svorqv[_u8](svbool_t pg, svuint8_t zn);
  ```

#### DUPQ

Broadcast indexed element within each quadword vector segment.

``` c
   // Variants are also available for:
   // _s8, _u16, _s16, _u32, _s32, _u64, _s64
   // _mf8, _bf16, _f16, _f32, _f64
   svuint8_t svdup_laneq[_u8](svuint8_t zn, uint64_t imm_idx);
   ```

#### EXTQ

Extract vector segment from each pair of quadword segments.

``` c
   // Variants are also available for:
   // _s8, _s16, _u16, _s32, _u32, _s64, _u64
   // _mf8, _bf16, _f16, _f32, _f64
   svuint8_t svextq[_u8](svuint8_t zdn, svuint8_t zm, uint64_t imm);
   ```
#### LD1D, LD1W

Contiguous zero-extending load to quadword (single vector).

``` c
   // Variants are also available for:
   // _u32, _s32
   svfloat32_t svld1uwq[_f32](svbool_t, const float32_t *ptr);
   svfloat32_t svld1uwq_vnum[_f32](svbool_t, const float32_t *ptr, int64_t vnum);


   // Variants are also available for:
   // _u64, _s64
   svfloat64_t svld1udq[_f64](svbool_t, const float64_t *ptr);
   svfloat64_t svld1udq_vnum[_f64](svbool_t, const float64_t *ptr, int64_t vnum);
   ```

#### LD1Q

Gather Load Quadword.

``` c
   // Variants are also available for:
   // _u8, _u16, _s16, _u32, _s32, _u64, _s64
   // _mf8, _bf16, _f16, _f32, _f64
   svint8_t svld1q_gather[_u64base]_s8(svbool_t pg, svuint64_t zn);
   svint8_t svld1q_gather[_u64base]_offset_s8(svbool_t pg, svuint64_t zn, int64_t offset);
   svint8_t svld1q_gather_[s64]offset[_s8](svbool_t pg, const int8_t *base, svint64_t offset);
   svint8_t svld1q_gather_[u64]offset[_s8](svbool_t pg, const int8_t *base, svuint64_t offset);

   // Variants are also available for:
   // _u16, _u32, _s32, _u64, _s64
   // _bf16, _f16, _f32, _f64
   svint16_t svld1q_gather_[s64]index[_s16](svbool_t pg, const int16_t *base, svint64_t index);
   svint16_t svld1q_gather_[u64]index[_s16](svbool_t pg, const int16_t *base, svuint64_t index);
   svint16_t svld1q_gather[_u64base]_index_s16(svbool_t pg, svuint64_t zn, int64_t index);
   ```

#### LD2Q, LD3Q, LD4Q

Contiguous load two, three, or four quadword structures.

``` c
   // Variants are also available for:
   // _u8, _u16, _s16, _u32, _s32, _u64, _s64
   // _mf8, _bf16, _f16, _f32, _f64
   svint8x2_t svld2q[_s8](svbool_t pg, const int8_t *rn);
   svint8x2_t svld2q_vnum[_s8](svbool_t pg, const int8_t *rn, uint64_t vnum);
   svint8x3_t svld3q[_s8](svbool_t pg, const int8_t *rn);
   svint8x3_t svld3q_vnum[_s8](svbool_t pg, const int8_t *rn, uint64_t vnum);
   svint8x4_t svld4q[_s8](svbool_t pg, const int8_t *rn);
   svint8x4_t svld4q_vnum[_s8](svbool_t pg, const int8_t *rn, uint64_t vnum);
   ```

#### UMAXQV, SMAXQV, FMAXQV, UMINQV, SMINQV, FMINQV

Max/Min reduction of quadword vector segments.

``` c
   // Variants are also available for:
   // _s8, _u16, _s16, _u32, _s32, _u64, _s64
   // _f16, _f32, _f64
   uint8x16_t svmaxqv[_u8](svbool_t pg, svuint8_t zn);
   uint8x16_t svminqv[_u8](svbool_t pg, svuint8_t zn);
   ```

#### FMAXNMQV, FMINNMQV

Max/Min recursive reduction of quadword vector segments.

``` c
   // Variants are also available for  _f32, _f64
   float16x8_t svmaxnmqv[_f16](svbool_t pg, svfloat16_t zn);
   float16x8_t svminnmqv[_f16](svbool_t pg, svfloat16_t zn);
   ```

#### PMOV

``` c
   // Variants are available for:
   // _s8, _u16, _s16, _s32, _u32, _s64, _u64
   svbool_t svpmov_lane[_u8](svuint8_t zn, uint64_t imm);

   // Variants are available for:
   // _s8, _s16, _u16, _s32, _u32, _s64, _u64
   svbool_t svpmov[_u8](svuint8_t zn);

   // Variants are available for:
   // _s16, _s32, _u32, _s64, _u64
   svuint16_t svpmov_lane[_u16]_m(svuint16_t zd, svbool_t pn, uint64_t imm);

   // Variants are also available for:
   // _s8, _u16, _s16, _u32, _s32, _u64, _s64
   svuint8_t svpmov_u8_z(svbool_t pn);
   ```

#### ST1D, ST1W

Contiguous store of single vector operand, truncating from quadword.

``` c
   // Variants are also available for:
   // _u32, _s32
   void svst1wq[_f32](svbool_t, float32_t *ptr, svfloat32_t data);
   void svst1wq_vnum[_f32](svbool_t, float32_t *ptr, int64_t vnum, svfloat32_t data);


   // Variants are also available for:
   // _u64, _s64
   void svst1dq[_f64](svbool_t, float64_t *ptr, svfloat64_t data);
   void svst1dq_vnum[_f64](svbool_t, float64_t *ptr, int64_t vnum, svfloat64_t data);
   ```

#### ST1Q

Scatter store quadwords.

``` c
   // Variants are also available for:
   // _u8, _u16, _s16, _u32, _s32, _u64, _s64
   // _mf8, _bf16, _f16, _f32, _f64
   void svst1q_scatter[_u64base][_s8](svbool_t pg, svuint64_t zn, svint8_t data);
   void svst1q_scatter[_u64base]_offset[_s8](svbool_t pg, svuint64_t zn, int64_t offset, svint8_t data);
   void svst1q_scatter_[s64]offset[_s8](svbool_t pg, uint8_t *base, svint64_t offset, svint8_t data);
   void svst1q_scatter_[u64]offset[_s8](svbool_t pg, uint8_t *base, svuint64_t offset, svint8_t data);

   // Variants are also available for:
   // _u16, _u32, _s32, _u64, _s64
   // _bf16, _f16, _f32, _f64
   void svst1q_scatter_[s64]index[_s16](svbool_t pg, int16_t *base, svint64_t index, svint16_t data);
   void svst1q_scatter_[u64]index[_s16](svbool_t pg, int16_t *base, svuint64_t index, svint16_t data);
   void svst1q_scatter[_u64base]_index[_s16](svbool_t pg, svuint64_t zn, int64_t index, svint16_t data);
```

#### ST2Q, ST3Q, ST4Q

Contiguous store.

``` c
   // Variants are also available for:
   // _s8 _u16, _s16, _u32, _s32, _u64, _s64
   // _mf8, _bf16, _f16, _f32, _f64
   void svst2q[_u8](svbool_t pg, uint8_t *rn, svuint8x2_t zt);
   void svst2q_vnum[_u8](svbool_t pg, uint8_t *rn, int64_t vnum, svuint8x2_t zt);
   void svst3q[_u8](svbool_t pg, uint8_t *rn, svuint8x3_t zt);
   void svst3q_vnum[_u8](svbool_t pg, uint8_t *rn, int64_t vnum, svuint8x3_t zt);
   void svst4q[_u8](svbool_t pg, uint8_t *rn, svuint8x4_t zt);
   void svst4q_vnum[_u8](svbool_t pg, uint8_t *rn, int64_t vnum, svuint8x4_t zt);
   ```

#### TBLQ

Programmable table lookup within each quadword vector segment (zeroing).

``` c
   // Variants are also available for:
   // _u8, _u16, _s16, _u32, _s32, _u64, _s64
   // _mf8, _bf16, _f16, _f32, _f64
   svint8_t svtblq[_s8](svint8_t zn, svuint8_t zm);
   ```

#### TBXQ

Programmable table lookup within each quadword vector segment (merging).

``` c
   // Variants are also available for:
   // _u8, _u16, _s16, _u32, _s32, _u64, _s64
   // _mf8, _bf16, _f16, _f32, _f64
   svint8_t svtbxq[_s8](svint8_t fallback, svint8_t zn, svuint8_t zm);
   ```

#### UZPQ1, UZPQ2

Concatenate elements within each pair of quadword vector segments.

``` c
   // Variants are also available for:
   // _s8, _u16, _s16, _u32, _s32, _u64, _s64
   // _mf8, _bf16, _f16, _f32, _f64
   svuint8_t svuzpq1[_u8](svuint8_t zn, svuint8_t zm);
   svuint8_t svuzpq2[_u8](svuint8_t zn, svuint8_t zm);
   ```

#### ZIPQ1, ZIPQ2

Interleave elements from halves of each pair of quadword vector segments.

``` c
   // Variants are also available for:
   // _s8, _u16, _s16, _u32, _s32, _u64, _s64
   // _mf8, _bf16, _f16, _f32, _f64
   svuint8_t svzipq1[_u8](svuint8_t zn, svuint8_t zm);
   svuint8_t svzipq2[_u8](svuint8_t zn, svuint8_t zm);
   ```

### SVE2 maximum and minimum absolute value

The intrinsics in this section are available when either
`__ARM_FEATURE_SVE2` or `__ARM_FEATURE_SME2` is defined to 1, and
`__ARM_FEATURE_FAMINMAX` is defined to 1.

#### FAMAX

Floating-point absolute maximum (predicated).
``` c
  // Variants are also available for: _f32 and _f64
  svfloat16_t svamax[_f16]_m(svbool_t pg, svfloat16_t zn, svfloat16_t zm);
  svfloat16_t svamax[_f16]_x(svbool_t pg, svfloat16_t zn, svfloat16_t zm);
  svfloat16_t svamax[_f16]_z(svbool_t pg, svfloat16_t zn, svfloat16_t zm);

  // Variants are also available for: _f32 and _f64
  svfloat16_t svamax[_n_f16]_m(svbool_t pg, svfloat16_t zn, float16_t zm);
  svfloat16_t svamax[_n_f16]_x(svbool_t pg, svfloat16_t zn, float16_t zm);
  svfloat16_t svamax[_n_f16]_z(svbool_t pg, svfloat16_t zn, float16_t zm);
```

#### FAMIN

Floating-point absolute minimum (predicated).
``` c
  // Variants are also available for: _f32 and _f64
  svfloat16_t svamin[_f16]_m(svbool_t pg, svfloat16_t zn, svfloat16_t zm);
  svfloat16_t svamin[_f16]_x(svbool_t pg, svfloat16_t zn, svfloat16_t zm);
  svfloat16_t svamin[_f16]_z(svbool_t pg, svfloat16_t zn, svfloat16_t zm);

  // Variants are also available for: _f32 and _f64
  svfloat16_t svamin[_n_f16]_m(svbool_t pg, svfloat16_t zn, float16_t zm);
  svfloat16_t svamin[_n_f16]_x(svbool_t pg, svfloat16_t zn, float16_t zm);
  svfloat16_t svamin[_n_f16]_z(svbool_t pg, svfloat16_t zn, float16_t zm);
```

### SVE2 lookup table

The intrinsics in this section are available when either
`__ARM_FEATURE_SVE2` or `__ARM_FEATURE_SME2` is defined to 1, and
`__ARM_FEATURE_LUT` is defined to 1.

#### LUTI2

Lookup table read with 2-bit indices.
```c
  // Variant is  also available for: _u8
  svint8_t svluti2_lane[_s8](svint8_t table, svuint8_t indices, uint64_t imm_idx);

  // Variants are also available for: _u16, _f16 and _bf16
  svint16_t svluti2_lane[_s16]( svint16_t table, svuint8_t indices, uint64_t imm_idx);
```

#### LUTI4

Lookup table read with 4-bit indices.
```c
  // Variant is also available for: _u8
  svint8_t svluti4_lane[_s8](svint8_t table, svuint8_t indices, uint64_t imm_idx);

  // Variants are also available for: _u16, _f16, _bf16
  svint16_t svluti4_lane[_s16](svint16_t table, svuint8_t indices, uint64_t imm_idx);
  svint16_t svluti4_lane[_s16_x2](svint16x2_t table, svuint8_t indices, uint64_t imm_idx);
```

### SVE2.3 lookup table

The intrinsics in this section are available when `__ARM_FEATURE_SVE2p3`
is defined to 1.

#### LUTI6

Lookup table read with 6-bit indices (8-bit).

Use of this intrinsic if `svcntb() * 8 < 256` results in undefined behavior.

```c
  // Variant is  also available for: _u8 _mf8
  svint8_t svluti6[_s8_x2](svint8x2_t table, svuint8_t indices);
```

### SVE2 Multi-vector AES and 128-bit polynomial multiply long instructions

The specification for SVE2 Multi-vector AES and 128-bit polynomial multiply long instructions is in
[**Beta** state](#support-levels) and might change or be
extended in the future.

#### AESE, AESD, AESEMC, AESDIMC

Multi-vector Advanced Encryption Standard instructions.

```c
  // Only if __ARM_FEATURE_SVE_AES2 != 0

  svuint8x2_t    svaese_lane[_u8_x2]     (svuint8x2_t zdn, svuint8_t zm, uint64_t index);
  svuint8x4_t    svaese_lane[_u8_x4]     (svuint8x4_t zdn, svuint8_t zm, uint64_t index);
  svuint8x2_t    svaesd_lane[_u8_x2]     (svuint8x2_t zdn, svuint8_t zm, uint64_t index);
  svuint8x4_t    svaesd_lane[_u8_x4]     (svuint8x4_t zdn, svuint8_t zm, uint64_t index);
  svuint8x2_t    svaesemc_lane[_u8_x2]   (svuint8x2_t zdn, svuint8_t zm, uint64_t index);
  svuint8x4_t    svaesemc_lane[_u8_x4]   (svuint8x4_t zdn, svuint8_t zm, uint64_t index);
  svuint8x2_t    svaesdimc_lane[_u8_x2]  (svuint8x2_t zdn, svuint8_t zm, uint64_t index);
  svuint8x4_t    svaesdimc_lane[_u8_x4]  (svuint8x4_t zdn, svuint8_t zm, uint64_t index);
```

#### PMULL, PMLAL

Multi-vector 128-bit polynomial multiply long instructions.

``` c
  // Only if __ARM_FEATURE_SVE_AES2 != 0

  svuint64x2_t svpmull_pair[_u64_x2](svuint64_t zn, svuint64_t zm);
  svuint64x2_t svpmull_pair[_n_u64_x2](svuint64_t zn, uint64_t zm);

  svuint64x2_t svpmlal_pair[_u64_x2](svuint64x2_t zda, svuint64_t zn, svuint64_t zm);
  svuint64x2_t svpmlal_pair[_n_u64_x2](svuint64x2_t zda, svuint64_t zn, uint64_t zm);
  ```

# SME language extensions and intrinsics

The specification for SME is in
[**Beta** state](#support-levels) and might change or be
extended in the future.

## Controlling the use of streaming mode

### Introduction to streaming and non-streaming mode

<span id="streaming-mode"></span>

The AArch64 architecture defines a concept called “streaming mode”,
controlled by a processor state bit called PSTATE.SM. At any given
point in time, the processor is either in streaming mode (PSTATE.SM==1)
or in non-streaming mode (PSTATE.SM==0). There is an instruction called
SMSTART to enter streaming mode and an instruction called SMSTOP to
return to non-streaming mode.

Streaming mode has three main effects on C and C++ code:

*   It can change the length of SVE vectors and predicates: the length
    of an SVE vector in streaming mode is called the “streaming vector
    length” (SVL), which might be different from the normal non-streaming
    vector length. See [Effect of streaming mode on VL](#effect-of-streaming-mode-on-vl)
    for more details.

*   <span id="streaming-intrinsic"></span>
    Some instructions can only be executed in streaming mode, which means
    that their associated ACLE intrinsics can only be used in streaming mode.
    These intrinsics are called “streaming intrinsics”.

*   <span id="non-streaming-intrinsic"></span>
    Some other instructions can only be executed in non-streaming mode,
    which means that their associated ACLE intrinsics can only be used
    in non-streaming mode. These intrinsics are called
    “non-streaming intrinsics”.

The C and C++ standards define the behavior of programs in terms of
an “abstract machine”. As an extension, the ACLE specification
applies the distinction between streaming mode and non-streaming mode
to this abstract machine: at any given point in time, the abstract
machine is either in streaming mode or in non-streaming mode.

This distinction between processor mode and abstract machine mode is
mostly just a dry specification detail. However, the usual “as if” rule
applies: the processor's actual mode at runtime can be different from
the abstract machine's mode, provided that this does not alter the
behavior of the program. One practical consequence of this is that
C and C++ code does not specify the exact placement of SMSTART and
SMSTOP instructions; the source code simply places limits on where such
instructions go. For example, when stepping through a program in a
debugger, the processor mode might sometimes be different from the one
implied by the source code.

<span id="non-streaming-statement"></span>
<span id="streaming-statement"></span>
<span id="streaming-compatible-statement"></span>

ACLE provides attributes that specify whether the abstract
machine executes statements:

*   in non-streaming mode, in which case they are called “non-streaming
    statements”

*   in streaming mode, in which case they are called “streaming statements”

*   in either mode, in which case they are called “streaming-compatible
    statements”

At present, the classification can only be controlled at function
granularity: the statements in a function are all non-streaming, all
streaming, or all streaming-compatible. When no attribute specifies
otherwise, all statements in a function are non-streaming.

As noted above, this classification affects which intrinsics
the statements can use. It also affects the length of SVE vectors
and predicates.

A program is [ill-formed](#ill-formed) if:

*   a [streaming statement](#streaming-statement) or a
    [streaming-compatible statement](#streaming-compatible-statement)
    contains an [evaluated call](#evaluated-call) to a
    [non-streaming intrinsic](#non-streaming-intrinsic).

*   a [non-streaming statement](#non-streaming-statement) or a
    [streaming-compatible statement](#streaming-compatible-statement)
    contains an [evaluated call](#evaluated-call) to a
    [streaming intrinsic](#streaming-intrinsic).

The current mode of the abstract machine can be queried using
[`__arm_in_streaming_mode`](#arm_in_streaming_mode).

### Changing streaming mode locally

Adding an [`__arm_locally_streaming`](#arm_locally_streaming)
[keyword attribute](#keyword-attributes) to a function specifies
that all the statements in the function are [streaming
statements](#streaming-statement). The program automatically puts
the [abstract machine](#abstract-machine) into streaming mode before
executing the statements and automatically restores the previous mode
afterwards.

This choice is internal to the function definition. It is not
visible to callers and so it can be changed without affecting the
function's binary interface. (In other words, it can be changed
without requiring all callers to be recompiled.)

For example:

``` c
  int nonstreaming_fn(void) {
    return __arm_in_streaming_mode();  // Returns 0
  }

  __arm_locally_streaming int streaming_fn(void)
  { // Function automatically switches into streaming mode on entry
    svsetffr();  // Ill-formed, calls a non-streaming intrinsic
    return __arm_in_streaming_mode();  // Returns 1
  } // Function automatically switches out of streaming mode on return

  int (*ptr1)(void) = nonstreaming_fn; // OK
  int (*ptr2)(void) = streaming_fn;    // OK
```

This approach can be useful when implementing existing APIs,
including when overriding virtual functions. It allows the
use of SME to be an internal implementation detail.

The [`__arm_locally_streaming`](#arm_locally_streaming) [keyword
attribute](#keyword-attributes) is an optional feature; it is only
guaranteed to be present if the implementation predefines the
`__ARM_FEATURE_LOCALLY_STREAMING` macro to a nonzero value.

### Managing streaming mode across function boundaries

In addition to [changing streaming mode locally](#changing-streaming-mode-locally),
ACLE provides [keyword attributes](#keyword-attributes) for managing
streaming mode across function boundaries. This can be useful in the
following example situations:

*   An SME operation is split across several cooperating subroutines
    (as is often the case). The SME operation as a whole is designed
    to execute exclusively in streaming mode, so mid-operation mode
    switches should be avoided for performance reasons.

*   A function provides a public API that is specific to SME.
    Again, callers to such functions would want to avoid the
    overhead of switching modes at function call boundaries.

*   Some functions are compatible with both streaming and
    non-streaming mode. Marking them as “streaming-compatible”
    allows them to be called in either mode, without changing
    the vector length. For example, this could be useful for
    “length agnostic” SVE math routines.

<span id="streaming-type"></span><span id="streaming-compatible-type"></span>

For this reason, the “streaming”, “non-streaming” and
“streaming-compatible” classification extends to function types:

*   By default, function types are “non-streaming types”.

*   Attaching an [`__arm_streaming`](#arm_streaming) [keyword
    attribute](#keyword-attributes) to a function type makes it a
    “streaming type”.

*   Attaching an [`__arm_streaming_compatible`](#arm_streaming_compatible)
    [keyword attribute](#keyword-attributes) to a function type makes it
    a “streaming-compatible type”.

The function type classification decides which mode the
[abstract machine](#abstract-machine) is in on entry to the function and
which mode the abstract machine is in on return from the function. The
program automatically switches mode as necessary before calling a
function and restores the previous mode on return; see
[Changes in streaming mode](#changes-in-streaming-mode) for details.

If the function forms part of the object code's ABI, the function type
classification also determines whether the function has a “non-streaming
interface”, a “streaming interface” or a “streaming-compatible
interface”; see [[AAPCS64]](#AAPCS64) for details.

By default, the classification of a function type carries over to
the classification of the statements in the function's definition,
if any. However, this can be overridden by the
[`__arm_locally_streaming`](#arm_locally_streaming) [keyword
attribute](#keyword-attributes); see [Changing streaming mode
locally](#changing-streaming-mode-locally) for details.

For example:

``` c
  // "n" stands for "non-streaming"
  // "s" stands for "streaming"
  // "sc" stands for "streaming-compatible"

  void n_callee(void);
  void s_callee(void) __arm_streaming;
  void sc_callee(void) __arm_streaming_compatible;

  void (*n_callback)(void);
  void (*s_callback)(void) __arm_streaming;
  void (*sc_callback)(void)  __arm_streaming_compatible;

  int n_caller(void)
  {
    n_callee();        // No mode switch
    (*n_callback)();   // No mode switch
    s_caller();        // Temporarily switches to streaming mode
    (*s_callback)();   // Temporarily switches to streaming mode
    sc_caller();       // No mode switch
    (*sc_callback)();  // No mode switch

    return __arm_in_streaming_mode();  // Returns 0
  }

  int s_caller(void) __arm_streaming
  {
    n_callee();        // Temporarily switches to non-streaming mode
    (*n_callback)();   // Temporarily switches to non-streaming mode
    s_caller();        // No mode switch
    (*s_callback)();   // No mode switch
    sc_caller();       // No mode switch
    (*sc_callback)();  // No mode switch

    return __arm_in_streaming_mode();  // Returns 1
  }

  int sc_caller(void) __arm_streaming_compatible
  {
    n_callee();        // Temporarily switches to non-streaming mode
    (*n_callback)();   // Temporarily switches to non-streaming mode
    s_caller();        // Temporarily switches to streaming mode
    (*s_callback)();   // Temporarily switches to streaming mode
    sc_caller();       // No mode switch
    (*sc_callback)();  // No mode switch

    return __arm_in_streaming_mode();  // Might return 0 or 1
  }
```

A function type in one category is incompatible with a function type in
another category, even if the types are otherwise identical. For example:

``` c
  // "n" stands for "non-streaming"
  // "s" stands for "streaming"
  // "sc" stands for "streaming-compatible"

  void n_callee(void);
  void s_callee(void) __arm_streaming;
  void sc_callee(void) __arm_streaming_compatible;

  void (*n_callback)(void);
  void (*s_callback)(void) __arm_streaming;
  void (*sc_callback)(void) __arm_streaming_compatible;

  void code() {
    n_callback = n_callee;    // OK
    n_callback = s_callee;    // Ill-formed
    n_callback = sc_callee;   // Ill-formed

    s_callback = n_callee;    // Ill-formed
    s_callback = s_callee;    // OK
    s_callback = sc_callee;   // Ill-formed

    sc_callback = n_callee;   // Ill-formed
    sc_callback = s_callee;   // Ill-formed
    sc_callback = sc_callee;  // OK
  }
```

A type that has both an [`__arm_streaming`](#arm_streaming)
[keyword attribute](#keyword-attributes) and an
[`__arm_streaming_compatible`](#arm_streaming_compatible)
[keyword attribute](#keyword-attributes) is [ill-formed](#ill-formed).

### Effect of streaming mode on VL

The value returned by an SVE intrinsic like `svcntb` depends on
whether or not the [abstract machine](#abstract-machine) is in streaming mode:
if the abstract machine is in streaming mode then the returned value
depends on the “streaming vector length” (SVL), otherwise the returned
value depends on the non-streaming vector length.

The runtime size of SVE vector and predicate types varies in the same way.
For example, an `svint8_t` object created while the abstract machine
is in streaming mode will have SVL bits, whereas an `svint8_t` object
created while the abstract machine is in non-streaming mode will have
the size specified by the non-streaming vector length.

The following definitions are useful when describing the consequences
of this behavior on the vector length:

*   <span id="vl-dependent"></span>
    A type T is said to be “VL-dependent” if an object of type T created
    while the [abstract machine](#abstract-machine) is in streaming mode
    has a different size from an object of type T created while the abstract
    machine is in non-streaming mode.

    Pointer and reference types are never VL-dependent. No types are
    VL-dependent if the streaming and non-streaming vector lengths are equal.

*   As a shorthand, an object or value is said to be VL-dependent if its
    type is VL-dependent.

    Like normal objects, a VL-dependent object never changes size after
    it has been created. The “VL-dependent” classification instead
    decides when it is valid to access the object, as described below.

*   <span id="streaming-object"></span>
    A VL-dependent object created while the abstract machine is in
    streaming mode is called a “streaming object”.

*   <span id="non-streaming-object"></span>
    A VL-dependent object created while the abstract machine is in
    non-streaming mode is called a “non-streaming object”.

If any of the following events occurs during the execution of a program,
then the behavior is undefined:

*   The program accesses a [non-streaming object](#non-streaming-object)
    while the [abstract machine](#abstract-machine) is in streaming mode.

*   The program accesses a [streaming object](#streaming-object) while the
    [abstract machine](#abstract-machine) is in non-streaming mode.

### Streaming callers and streaming callees

If, during the execution of a program, a function F1 calls a function F2, then:

*   <span id="streaming-caller"></span>
    <span id="non-streaming-caller"></span>
    F1 is said to be a “streaming caller” if:

    *   F1's statements are [streaming statements](#streaming-statement); or

    *   F1's statements are [streaming-compatible statements](#streaming-compatible-statement)
        and F1's caller is itself a streaming caller.

    Otherwise, F1 is said to be a “non-streaming caller”.

*   <span id="streaming-callee"></span>
    <span id="non-streaming-callee"></span>
    F2 is said to be a “streaming callee” if:

    *   F2 has a [streaming type](#streaming-type); or

    *   F2 has a [streaming-compatible type](#streaming-compatible-type)
        and F1 is a streaming caller.

    Otherwise, F2 is said to be a “non-streaming callee”.

See [Calling restrictions related to streaming mode](#calling-restrictions-related-to-streaming-mode)
for some examples.

### Changes in streaming mode

Calls from a [non-streaming caller](#non-streaming-caller) to a
[streaming callee](#streaming-callee) involve a temporary change
into streaming mode. The [abstract machine](#abstract-machine) enters
streaming mode for the duration of the call and returns to non-streaming
mode afterwards.

Similarly, calls from a [streaming caller](#streaming-caller) to a
[non-streaming callee](#non-streaming-callee) involve a temporary change
out of streaming mode. The [abstract machine](#abstract-machine) leaves
streaming mode for the duration of the call and reenters streaming mode
afterwards.

In both cases, these changes of mode are automatic and it is the compiler's
responsibility to insert the necessary instructions. There are no intrinsics
that map directly to SMSTART and SMSTOP.

Semantically, the sequencing of such calls is as follows:

1.  Evaluate the function arguments according to the normal C/C++ rules
    and create any temporary objects necessary for performing the call.

2.  Switch the abstract machine to the callee's mode.

3.  Call the callee function.

4.  Switch the abstract machine back to the original mode.

5.  Process the value returned by the call (if any).

The intention is that the change in mode binds as closely to the call as
possible.

### Calling restrictions related to streaming mode

If any of the following events occurs during the execution of a program,
then the behavior is undefined:

*   a [streaming caller](#streaming-caller) passes a
    [VL-dependent](#vl-dependent) argument to a
    [non-streaming callee](#non-streaming-callee)

*   a [non-streaming caller](#non-streaming-caller) passes a
    [VL-dependent](#vl-dependent) argument to a
    [streaming callee](#streaming-callee)

*   a [non-streaming callee](#non-streaming-callee) receives a
    [VL-dependent](#vl-dependent) argument and the callee has
    an [`__arm_locally_streaming`](#arm_locally_streaming) [keyword
    attribute](#keyword-attributes)

*   a [streaming callee](#streaming-callee) returns a
    [VL-dependent](#vl-dependent) value to a
    [non-streaming caller](#non-streaming-caller)

*   a [non-streaming callee](#non-streaming-callee) returns a
    [VL-dependent](#vl-dependent) value to a
    [streaming caller](#streaming-caller)

*   a [non-streaming callee](#non-streaming-callee) returns a
    [VL-dependent](#vl-dependent) value and the callee has an
    [`__arm_locally_streaming`](#arm_locally_streaming) [keyword
    attribute](#keyword-attributes)

The following code gives some examples. In each case, the assumption is
that the non-streaming vector length is different from the streaming
vector length:

``` c
  // "n" stands for "non-streaming"
  // "s" stands for "streaming"
  // "sc" stands for "streaming-compatible"
  // "ls" stands for "locally streaming"

  void n_callee(svint8_t);
  void s_callee(svbool_t) __arm_streaming;
  void sc_callee(svint8_t) __arm_streaming_compatible;

  __arm_locally_streaming void ls_callee(svbool_t pg) {
    // Invokes undefined behavior if called.
  }

  void n_caller(void)
  {
    svint8_t i = ...;
    svbool_t b = ...;

    n_callee(i);   // OK: non-streaming callee
    s_callee(b);   // Undefined behavior: streaming callee
    sc_callee(i);  // OK: non-streaming callee
    ls_callee(b);  // call is OK: non-streaming callee. However,
                   //   as noted above, the callee invokes undefined
                   //   behavior internally
  }

  void s_caller(void) __arm_streaming
  {
    svint8_t i = ...;
    svbool_t b = ...;

    n_callee(i);   // Undefined behavior: non-streaming callee
    s_callee(b);   // OK: streaming callee
    sc_callee(i);  // OK: streaming callee
    ls_callee(b);  // Undefined behavior: non-streaming callee
  }

  void sc_caller(void) __arm_streaming_compatible
  {
    svint8_t i = ...;
    svbool_t b = ...;

    n_callee(i);   // Undefined behavior if sc_caller was called
                   //   in streaming mode (but not otherwise)
    s_callee(b);   // Undefined behavior if sc_caller was called
                   //   in non-streaming mode (but not otherwise)
    sc_callee(i);  // OK: keeps current streaming/non-streaming mode
    ls_callee(b);  // Undefined behavior if sc_caller was called
                   //   in streaming mode, but the call itself is
                   //   OK otherwise. As noted above, the callee
                   //   invokes undefined behavior internally
  }
```

If the streaming and non-streaming vector lengths are equal then there
is no undefined behavior in the code above.

### `asm` restrictions related to streaming mode

Some ACLE implementations might support the GNU “inline asm” extension.
If so, the value of PSTATE.SM at the start of such inline asms is
guaranteed to match the mode of the [abstract machine](#abstract-machine).
For example, PSTATE.SM is guaranteed to be 1 at the start of inline asms
in [streaming statements](#streaming-statement) and 0 at the start of
inline asms in [non-streaming statements](#non-streaming-statement).

All inline asms must preserve the value of PSTATE.SM.  Therefore:

*   An asm entered in streaming mode must finish in streaming mode.

*   An asm entered in non-streaming mode must finish in non-streaming mode.

The behavior in other cases is undefined.

An inline asm can temporarily switch mode internally, such as using an
SMSTART/SMSTOP pair. However, such mode switches invalidate all Z and P
register state. The asm's “clobber list” must mention any registers
whose values might be changed by the asm.

## ZA storage

SME provides an area of storage called ZA, of size SVL.B×SVL.B bytes.
It also provides a processor state bit called PSTATE.ZA to control
whether ZA is enabled.

<span id="za-state"></span>

In C and C++ code, access to ZA is controlled at function granularity:
a function either [uses](#uses-state) ZA or it does not. Another way to
say this is that a function either “has ZA state” or it does not.

If a function does have ZA state, the function can either
[share](#shares-state) that ZA state with the function's caller or create
new ZA state “from scratch”. In the latter case, it is the compiler's
responsibility to free up ZA so that the function can use it; see the
description of the lazy saving scheme in [[AAPCS64]](#AAPCS64) for
details about how the compiler does this.

These possibilities give a one-out-of-three choice for how a function
handles ZA:

1.  The function has no [ZA state](#za-state). This is the default.

2.  The function has [ZA state](#za-state) that it shares with its caller.
    This is indicated by adding a [state-sharing
    attribute](#ways-of-sharing-state) to the function type,
    such as `__arm_inout("za")`.

3.  The function has [ZA state](#za-state) that it creates “from scratch” and
    that it does not share with its caller. This is indicated by adding
    [`__arm_new("za")`](#arm_new) to the function definition.

Functions that have ZA state can use the [SME instruction intrinsics](#sme-instruction-intrinsics)
to manipulate that state.

## ZT0 Lookup Table

When ZA storage is enabled, SME2 additionally provides access to a 64-byte large
lookup table called ZT0 which can be accessed through specialized instructions.
ZT0 is architecturally linked to ZA such that changing PSTATE.ZA enables or
disables both ZA and ZT0 simultaneously.

<span id="zt-state"></span>
This means that when the hardware supports SME2, a function that has
[ZA state](#za-state) also has ZT state.


## SME keyword attributes

ACLE adds several SME-related keyword attributes. See [Keyword
attributes](#keyword-attributes) for general remarks about these keywords.

Except where noted otherwise, function types that have an attribute are
incompatible with function types that do not. For example:

``` c
  // "n" stands for "non-streaming"
  // "s" stands for "streaming"

  typedef void (*n_callback_type)(void);
  n_callback_type n_callback_ptr;
  void n_extern_function(void);
  void n_local_function(void) { ... }

  typedef void (*s_callback_type)(void) __arm_streaming;
  s_callback_type s_callback_ptr;
  void s_extern_function(void) __arm_streaming;
  void s_local_function(void) __arm_streaming { ... }

  void foo() {
    n_callback_ptr = n_callback_ptr;     // OK
    n_callback_ptr = n_extern_function;  // OK
    n_callback_ptr = n_local_function;   // OK
    n_callback_ptr = s_callback_ptr;     // Ill-formed
    n_callback_ptr = s_extern_function;  // Ill-formed
    n_callback_ptr = s_local_function;   // Ill-formed

    s_callback_ptr = n_callback_ptr;     // Ill-formed
    s_callback_ptr = n_extern_function;  // Ill-formed
    s_callback_ptr = n_local_function;   // Ill-formed
    s_callback_ptr = s_callback_ptr;     // OK
    s_callback_ptr = s_extern_function;  // OK
    s_callback_ptr = s_local_function;   // OK
  }
```

The function type attributes cannot be used with K&R-style
[unprototyped function](#unprototyped-function) types. For example:

``` c
  #define ATTR __arm_streaming

  typedef int ft1() ATTR;      // Ill-formed in C, C18 and earlier, OK in
                               //   later versions of C and in C++
  int f1() ATTR { ... }        // Likewise
  typedef int ft2(void) ATTR;  // OK
  int f2(void) ATTR { ... }    // OK
```

Some implementations may, as an extension, accept code such as:

```c
void f(void) [[attr1, attr2, ..., attrN]];
void f(void);
```

where the second declaration inherits the type attributes from the
first, even if the declarations would otherwise be incompatible.

However, this specification considers such code invalid if the first
declaration is annotated with an SME keyword attribute which would make
the declarations incompatible (as above), due to its absence from the
second declaration.

Thus, e.g. all of the following (otherwise duplicate) declarations are
ill-formed:

```c
void f(void) __arm_streaming;
void f(void); // Ill-formed

void g(void) __arm_streaming_compatible;
void g(void) {} // Ill-formed

void h(void) __arm_streaming __arm_inout("za");
void h(void); // Ill-formed
```

### SME keyword attributes related to streaming mode

<span id="arm_streaming"></span>

#### `__arm_streaming`

This [keyword attribute](#keyword-attributes) applies to **function types**
and specifies the following:

*   If the function is defined, all statements in that definition are
    [streaming statements](#streaming-statement).

*   The program switches the [abstract machine](#abstract-machine) into
    streaming mode before calling the function and restores the previous
    mode after the function has returned.

*   If the function forms part of the object code's ABI, that object code
    function has a “streaming interface”; see [[AAPCS64]](#AAPCS64) for
    more details.

Using this attribute does not place any restriction on the function's
argument and return types. For example, an `__arm_streaming` function
can take arguments of type `int32x4_t` even though that type is
generally associated with non-streaming Advanced SIMD code.

See [Managing streaming mode across function boundaries](#managing-streaming-mode-across-function-boundaries)
for more information.

<span id="arm_streaming_compatible"></span>

#### `__arm_streaming_compatible`

This [keyword attribute](#keyword-attributes) applies to **function types**
and specifies the following:

*   If the function is defined, all statements in that definition are
    by default [streaming-compatible statements](#streaming-compatible-statement).
    This can be overridden by the [`__arm_locally_streaming`](#arm_locally_streaming)
    keyword attribute.

*   The [abstract machine](#abstract-machine) does not change into or out
    of streaming mode before calling the function and does not (need to)
    restore the previous mode after the function has returned.

*   If the function forms part of the object code's ABI, that object code
    function has a “streaming-compatible interface”; see [[AAPCS64]](#AAPCS64)
    for more details.

Using this attribute does not place any restriction on the function's
argument and return types. For example, an `__arm_streaming_compatible`
function can take arguments of type `int32x4_t` even though that type
is generally associated only with non-streaming Advanced SIMD code.

See [Managing streaming mode across function boundaries](#managing-streaming-mode-across-function-boundaries)
for more information.

<span id="arm_locally_streaming"></span>

#### `__arm_locally_streaming`

This [keyword attribute](#keyword-attributes) is only guaranteed to be
supported by ACLE implementations that predefine the macro
`__ARM_FEATURE_LOCALLY_STREAMING` to a nonzero value.

The attribute applies to **function definitions** and specifies that all
statements in the function definition are [streaming statements](#streaming-statement).
The attribute is redundant (but still valid) for functions that have
an [`__arm_streaming`](#arm_streaming) type.

See [Changing streaming mode locally](#changing-streaming-mode-locally)
for more information.

### C++ mangling of SME keywords

If the mangling would normally include the return type of the function, then
the SME keyword attributes that apply to function types must be included in the
name mangling of the type.

SME attributes are mangled in the same way as a template:

``` c
  template<typename, uint64_t> __SME_ATTRS;
```

with the arguments:

``` c
  __SME_ATTRS<normal_function_type, sme_state>;
```

where:

* normal_function_type is the function type without any SME attributes.

* sme_state is an unsigned 64-bit integer representing the streaming and ZA
  properties of the interface of the function.

The bits are defined as follows:

| **Bits** | **Value** | **Interface Type**             |
| -------- | --------- | ------------------------------ |
| 0        | 0b1       | __arm_streaming                |
| 1        | 0b1       | __arm_streaming_compatible     |
| 2        | 0b1       | __arm_agnostic("sme_za_state") |
| 3-5      | 0b000     | No ZA state (default)          |
|          | 0b001     | __arm_in("za")                 |
|          | 0b010     | __arm_out("za")                |
|          | 0b011     | __arm_inout("za")              |
|          | 0b100     | __arm_preserves("za")          |
| 6-8      | 0b000     | No ZT0 state (default)         |
|          | 0b001     | __arm_in("zt0")                |
|          | 0b010     | __arm_out("zt0")               |
|          | 0b011     | __arm_inout("zt0")             |
|          | 0b100     | __arm_preserves("zt0")         |

Bits 9-63 are defined to be zero by this revision of the ACLE and are reserved
for future type attributes.

For example:

``` c
  // Mangled as _Z1fP11__SME_ATTRSIFu10__SVInt8_tvELj1EE
  void f(svint8_t (*fn)() __arm_streaming) { fn(); }

  // Mangled as _Z1fP11__SME_ATTRSIFu10__SVInt8_tvELj26EE
  void f(svint8_t (*fn)() __arm_streaming_compatible __arm_inout("za")) { fn(); }

  // Mangled as _Z1fP11__SME_ATTRSIFu10__SVInt8_tvELj128EE
  void f(svint8_t (*fn)() __arm_out("zt0")) { fn(); }
```

## SME types

### Predicate-as-counter

SME2 adds a new kind of predicate, named *predicate-as-counter* which is used
for multi-vector predication. It describes a predicate mask that can span
multiple predicate registers with `K` `true` values followed by all `false`
values, or `K` `false` values followed by all `true` values, for a given element
type.

When `__ARM_FEATURE_SME2` is defined, a single sizeless
predicate-as-counter type named `svcount_t` is available.

`svcount_t` and `svbool_t` are both used to represent predicate masks, but
they cannot be used interchangeably.

The ACLE allows these types to be cast from one to another using the
`svcount_t svreinterpret_c(svbool_t)` and `svbool_t svreinterpret_b(svcount_t)`
intrinsics, although the reinterpreted values may not be sensible in the other
format. To safely extract a sensible mask from a `svcount_t`, the `svpext`
functions should be used.

### Multi-vector predicates

When `__ARM_FEATURE_SME2` is defined, the tuple types `svboolx2_t` and
`svboolx4_t` are available.

These are opaque tuple types that can be accessed using the SVE intrinsics
`svsetN`, `svgetN` and `svcreateN`. `svundef2` and `svundef4` are also extended
to work with `svboolx2_t` and `svboolx4_t`. For example:

``` c
    svbool_t svget2[_b](svboolx2_t tuple, uint64_t imm_index);
    svboolx2_t svset2[_b](svboolx2_t tuple, uint64_t imm_index, svbool_t x);
    svboolx2_t svcreate2[_b](svbool_t x, svbool_t y);
    svboolx2_t svundef2_b();
```

## SME functions and intrinsics

This section describes various support functions and intrinsics. The support
functions have
[external linkage](#external-linkage), like standard C functions such
as `memcpy` do. However, as noted in [Intrinsics](#intrinsics), it is
unspecified whether the intrinsics are functions and, if so, what
linkage they have.

There are many more intrinsics than support functions, so everything
described in this section is an intrinsic unless its individual
description says otherwise.

If an intrinsic is implemented as a macro rather than a function,
the macro must behave “as if” it had the prototype and attributes
specified in this section.

### SME PSTATE functions

#### Prototypes

``` c
  bool __arm_has_sme(void) __arm_streaming_compatible;

  bool __arm_in_streaming_mode(void) __arm_streaming_compatible;

  // Function with external linkage.
  void __arm_za_disable(void) __arm_streaming_compatible;
```

#### Semantics

**`__arm_has_sme()`**

> This call returns true if the current thread “has access to SME”;
> see [[AAPCS64]](#AAPCS64) for a more detailed definition of this term.
>
> One way of implementing this function is to call `__arm_sme_state`
> and then return the top bit of X0.  See [[AAPCS64]](#AAPCS64) for
> more details about `__arm_sme_state`.

<span id="arm_in_streaming_mode"></span>

**`__arm_in_streaming_mode()`**

> This call returns true if the [abstract machine](#abstract-machine) is
> in streaming mode. It always returns true when called from [streaming
> statements](#streaming-statement) and it always return false when
> called from [non-streaming statements](#non-streaming-statement).
> However, the call is not semantically a constant expression even in
> those cases.

<span id="arm_za_disable"></span>

**`__arm_za_disable()`**

> This call commits any pending lazy save and turns ZA off;
> see [[AAPCS64]](#AAPCS64) for details.
>
> Note: since this is a [private-ZA](#private-za) function,
> it is valid (though pointless) to call it from a function that has
> [ZA state](#za-state). The compiler would simply reenable ZA after the
> call and reload the saved ZA state.

### SME ZA state assertions

#### Prototypes

``` c
  void svundef_za() __arm_streaming_compatible;
```

#### Semantics

**`svundef_za()`**

> This call asserts that ZA does not currently have any useful data.
> Semantically, it fills ZA with unpredictable data, although from
> a quality of implementation perspective, it should not generate
> any object code.
>
> The call can be used as an optimization hint to the compiler, so that
> the compiler does not insert unnecessary code to save and restore the
> current ZA contents. The call might also be useful for static analysis.


### SME instruction intrinsics

The intrinsics in this section have the following properties in common:

*   Every argument named `tile` or `tile_mask` must be an integer constant
    expression in the range of the underlying instruction.

*   Some SME instructions identify a slice of ZA using the sum of a 32-bit
    general-purpose register and an immediate offset.  The intrinsics for
    these instructions have a 32-bit argument named `slice`, which is
    interpreted as follows:

    *   If the intrinsic also has a `vnum` argument, the ZA slice number
        is calculated by adding `vnum` to `slice`.  Both `slice` and `vnum`
        can be variable.

    *   Otherwise, `slice` specifies the ZA slice number directly; that is,
        it represents the sum of the 32-bit register and the immediate
        offset.  `slice` can be variable.

*   ZA loads and stores do not use typed pointers, since there is
    no C or C++ type information associated with the contents of ZA.

*   Intrinsics have a `_hor` suffix if they operate on horizontal slices
    of a given ZA tile and a `_ver` suffix if they operate on vertical
    slices of a given ZA tile.


SME2 adds operations that work on groups of SVE vectors, ZA tile slices or
ZA array vectors. The intrinsics model this in the following way:

*   Multi-vector operands are groups of SVE data vectors, that use the same
    tuple types as defined in the [SVE ACLE](#sve-vector-types), for example,
    `svint32x2_t` for a multi-vector operand of two 32-bit element vectors, or
    `svint64x4_t` for a multi-vector operand of four 64-bit element vectors.

*   The architecture distinguishes between multi-vector operands with
    consecutive registers and multi-vector operands with strided registers.
    This level of detail is not exposed to the C/C++ intrinsics or types. It is
    left up to the compiler to choose the most optimal form.

*   Intrinsic functions have a `_x2` or `_x4` suffix if the
    function\'s widest type is a vector tuple of 2 or 4 data vectors
    and the function operates purely on vectors, not on the matrix array or
    tile slices. The suffix is only present on overloaded names if it cannot
    be inferred from arguments.

*   Intrinsic functions have a `_vg2` or `_vg4` suffix if the function
    operates on groups of 2 or 4 ZA tile slices.  For example:

``` c
    // Reads 2 consecutive horizontal tile slices from ZA into multi-vector.
    svint8x2_t svread_hor_za8_s8_vg2(uint64_t tile, uint32_t slice)
      __arm_streaming __arm_in("za");
```

*   Intrinsic functions have a `_vg1x2`, `_vg1x4` suffix if the function
    operates on 2 or 4 single-vector groups within the ZA array.

*   Intrinsic functions have a `_vg2x1`, `_vg2x2`, `_vg2x4` suffix if
    the function operates on 1, 2 or 4 double-vector groups within the ZA array.

*   Intrinsic functions have a `_vg4x1`, `_vg4x2`, `_vg4x4` suffix if the
    function operates on 1, 2 or 4 quad-vector groups within the ZA array.
    For example:

``` c
    // SMLAL intrinsic for 2 quad-vector groups.
    void svmla_lane_za32[_s8]_vg4x2(uint32_t slice, svint8x2_t zn,
                                    svint8_t zm, uint64_t imm_idx)
      __arm_streaming __arm_inout("za");
```

*   Intrinsic functions that take a multi-vector operand may have additional
    suffixes to distinguish them from other forms for the same intrinsic:
    *   a `_single` suffix if they take one multi-vector operand and one
        (single) vector operand.
    *   a `_lane` suffix if they take one multi-vector operand and one
        indexed vector operand with an immediate to specify the indexed
        elements.

``` c
    void svmla_za32[_s8]_vg4x2(uint32_t slice, svint8x2_t zn, svint8x2_t zm)
      __arm_streaming __arm_inout("za");

    void svmla[_single]_za32[_s8]_vg4x2(uint32_t slice, svint8x2_t zn,
                                        svint8_t zm)
      __arm_streaming __arm_inout("za");

    void svmla_lane_za32[_s8]_vg4x2(uint32_t slice, svint8x2_t zn,
                                    svint8_t zm, uint64_t imm_idx)
      __arm_streaming __arm_inout("za");
```


#### LD1B, LD1H, LD1W, LD1D, LD1Q

``` c
  // Also for _za16, _za32, _za64 and _za128 (with the same prototype).
  void svld1_hor_za8(uint64_t tile, uint32_t slice, svbool_t pg,
                     const void *ptr)
    __arm_streaming __arm_inout("za");

  // Synthetic intrinsic: adds vnum to slice and vnum * svcntsb() to the
  // address given by ptr.
  //
  // Also for _za16, _za32, _za64 and _za128 (with the same prototype).
  void svld1_hor_vnum_za8(uint64_t tile, uint32_t slice, svbool_t pg,
                          const void *ptr, int64_t vnum)
    __arm_streaming __arm_inout("za");

  // Also for _za16, _za32, _za64 and _za128 (with the same prototype).
  void svld1_ver_za8(uint64_t tile, uint32_t slice, svbool_t pg,
                     const void *ptr)
    __arm_streaming __arm_inout("za");

  // Synthetic intrinsic: adds vnum to slice and vnum * svcntsb() to the
  // address given by ptr.
  //
  // Also for _za16, _za32, _za64 and _za128 (with the same prototype).
  void svld1_ver_vnum_za8(uint64_t tile, uint32_t slice, svbool_t pg,
                          const void *ptr, int64_t vnum)
    __arm_streaming __arm_inout("za");
```

#### LDR

``` c
  void svldr_za(uint32_t slice, const void *ptr)
    __arm_streaming_compatible __arm_inout("za");

  // Adds vnum to slice and vnum * svcntsb() to the address given by ptr.
  // This can be done in a single instruction if vnum is a constant in the
  // range [0, 15].  The intrinsic is synthetic for other vnum parameters.
  void svldr_vnum_za(uint32_t slice, const void *ptr, int64_t vnum)
     __arm_streaming_compatible __arm_inout("za");
```

#### ST1B, ST1H, ST1W, ST1D, ST1Q

``` c
  // Also for _za16, _za32, _za64 and _za128 (with the same prototype).
  void svst1_hor_za8(uint64_t tile, uint32_t slice, svbool_t pg,
                     void *ptr)
    __arm_streaming __arm_in("za");

  // Synthetic intrinsic: adds vnum to slice and vnum * svcntsb() to the
  // address given by ptr.
  //
  // Also for _za16, _za32, _za64 and _za128 (with the same prototype).
  void svst1_hor_vnum_za8(uint64_t tile, uint32_t slice, svbool_t pg,
                          void *ptr, int64_t vnum)
    __arm_streaming __arm_in("za");

  // Also for _za16, _za32, _za64 and _za128 (with the same prototype).
  void svst1_ver_za8(uint64_t tile, uint32_t slice, svbool_t pg,
                     void *ptr)
    __arm_streaming __arm_in("za");

  // Synthetic intrinsic: adds vnum to slice and vnum * svcntsb() to the
  // address given by ptr.
  //
  // Also for _za16, _za32, _za64 and _za128 (with the same prototype).
  void svst1_ver_vnum_za8(uint64_t tile, uint32_t slice, svbool_t pg,
                          void *ptr, int64_t vnum)
    __arm_streaming __arm_in("za");
```

#### STR

``` c
  void svstr_za(uint32_t slice, void *ptr)
    __arm_streaming_compatible __arm_in("za");

  // Adds vnum to slice and vnum * svcntsb() to the address given by ptr.
  // This can be done in a single instruction if vnum is a constant in the
  // range [0, 15].  The intrinsic is synthetic for other vnum parameters.
  void svstr_vnum_za(uint32_t slice, void *ptr, int64_t vnum)
     __arm_streaming_compatible __arm_in("za");
```

#### MOVA

The intrinsics below read horizontal ZA slices. In each case, the type
of the return value and the `zd` parameter vary with the type suffix.
For example, in the `_u8` intrinsic, the return value and the `zd`
parameter both have type `svuint8_t`.

``` c
  // And similarly for u8, mf8
  svint8_t svread_hor_za8[_s8]_m(svint8_t zd, svbool_t pg,
                                 uint64_t tile, uint32_t slice)
    __arm_streaming __arm_in("za");

  // And similarly for u16, bf16 and f16.
  svint16_t svread_hor_za16[_s16]_m(svint16_t zd, svbool_t pg,
                                    uint64_t tile, uint32_t slice)
    __arm_streaming __arm_in("za");

  // And similarly for u32 and f32.
  svint32_t svread_hor_za32[_s32]_m(svint32_t zd, svbool_t pg,
                                    uint64_t tile, uint32_t slice)
    __arm_streaming __arm_in("za");

  // And similarly for u64 and f64.
  svint64_t svread_hor_za64[_s64]_m(svint64_t zd, svbool_t pg,
                                    uint64_t tile, uint32_t slice)
    __arm_streaming __arm_in("za");

  // And similarly for s16, s32, s64, u8, u16, u32, u64, mf8, bf16, f16, f32, f64
  svint8_t svread_hor_za128[_s8]_m(svint8_t zd, svbool_t pg,
                                   uint64_t tile, uint32_t slice)
    __arm_streaming __arm_in("za");
```

Replacing `_hor` with `_ver` gives the associated vertical forms.

The intrinsics below write to horizontal ZA slices. In each case,
the type of the `zn` parameter varies with the type suffix. For example,
the `zn` parameter to the `_u8` intrinsic has type `svuint8_t`.

``` c
  // And similarly for u8, mf8.
  void svwrite_hor_za8[_s8]_m(uint64_t tile, uint32_t slice, svbool_t pg,
                              svint8_t zn)
    __arm_streaming __arm_inout("za");

  // And similarly for u16, bf16 and f16.
  void svwrite_hor_za16[_s16]_m(uint64_t tile, uint32_t slice, svbool_t pg,
                                svint16_t zn)
    __arm_streaming __arm_inout("za");

  // And similarly for u32 and f32.
  void svwrite_hor_za32[_s32]_m(uint64_t tile, uint32_t slice, svbool_t pg,
                                svint32_t zn)
    __arm_streaming __arm_inout("za");

  // And similarly for u64 and f64.
  void svwrite_hor_za64[_s64]_m(uint64_t tile, uint32_t slice, svbool_t pg,
                                svint64_t zn)
    __arm_streaming __arm_inout("za");

  // And similarly for s16, s32, s64, u8, u16, u32, u64, mf8, bf16, f16, f32, f64
  void svwrite_hor_za128[_s8]_m(uint64_t tile, uint32_t slice, svbool_t pg,
                                svint8_t zn)
    __arm_streaming __arm_inout("za");
```

Replacing `_hor` with `_ver` gives the associated vertical forms.

#### ADDHA

``` c
  void svaddha_za32[_s32]_m(uint64_t tile, svbool_t pn, svbool_t pm,
                            svint32_t zn)
    __arm_streaming __arm_inout("za");

  void svaddha_za32[_u32]_m(uint64_t tile, svbool_t pn, svbool_t pm,
                            svuint32_t zn)
    __arm_streaming __arm_inout("za");

  // Only if __ARM_FEATURE_SME_I16I64 != 0
  void svaddha_za64[_s64]_m(uint64_t tile, svbool_t pn, svbool_t pm,
                            svint64_t zn)
    __arm_streaming __arm_inout("za");

  // Only if __ARM_FEATURE_SME_I16I64 != 0
  void svaddha_za64[_u64]_m(uint64_t tile, svbool_t pn, svbool_t pm,
                            svuint64_t zn)
    __arm_streaming __arm_inout("za");
```

#### ADDVA

``` c
  void svaddva_za32[_s32]_m(uint64_t tile, svbool_t pn, svbool_t pm,
                            svint32_t zn)
    __arm_streaming __arm_inout("za");

  void svaddva_za32[_u32]_m(uint64_t tile, svbool_t pn, svbool_t pm,
                            svuint32_t zn)
    __arm_streaming __arm_inout("za");

  // Only if __ARM_FEATURE_SME_I16I64 != 0
  void svaddva_za64[_s64]_m(uint64_t tile, svbool_t pn, svbool_t pm,
                            svint64_t zn)
    __arm_streaming __arm_inout("za");

  // Only if __ARM_FEATURE_SME_I16I64 != 0
  void svaddva_za64[_u64]_m(uint64_t tile, svbool_t pn, svbool_t pm,
                            svuint64_t zn)
    __arm_streaming __arm_inout("za");
```

#### BFMOPA, FMOPA (widening), SMOPA, UMOPA

``` c
  void svmopa_za32[_bf16]_m(uint64_t tile, svbool_t pn, svbool_t pm,
                            svbfloat16_t zn, svbfloat16_t zm)
    __arm_streaming __arm_inout("za");

  void svmopa_za32[_f16]_m(uint64_t tile, svbool_t pn, svbool_t pm,
                           svfloat16_t zn, svfloat16_t zm)
    __arm_streaming __arm_inout("za");

  void svmopa_za32[_s8]_m(uint64_t tile, svbool_t pn, svbool_t pm,
                          svint8_t zn, svint8_t zm)
    __arm_streaming;

  void svmopa_za32[_u8]_m(uint64_t tile, svbool_t pn, svbool_t pm,
                          svuint8_t zn, svuint8_t zm)
    __arm_streaming __arm_inout("za");

  // Only if __ARM_FEATURE_SME_I16I64 != 0
  void svmopa_za64[_s16]_m(uint64_t tile, svbool_t pn, svbool_t pm,
                           svint16_t zn, svint16_t zm)
    __arm_streaming __arm_inout("za");

  // Only if __ARM_FEATURE_SME_I16I64 != 0
  void svmopa_za64[_u16]_m(uint64_t tile, svbool_t pn, svbool_t pm,
                           svuint16_t zn, svuint16_t zm)
    __arm_streaming __arm_inout("za");
```

#### BFMOPA, FMOPA (non-widening)

``` c
  // Variants are also available for:
  //   _za16[_bf16]_m (only if __ARM_FEATURE_SME_B16B16 != 0)
  //   _za16[_f16]_m (only if __ARM_FEATURE_SME_F16F16 != 0)
  //   _za64[_f64]_m (only if __ARM_FEATURE_SME_F64F64 != 0)
  void svmopa_za32[_f32]_m(uint64_t tile, svbool_t pn, svbool_t pm,
                           svfloat32_t zn, svfloat32_t zm)
    __arm_streaming __arm_inout("za");
```

#### BFMOPS, FMOPS (widening), SMOPS, UMOPS

``` c
  void svmops_za32[_bf16]_m(uint64_t tile, svbool_t pn, svbool_t pm,
                            svbfloat16_t zn, svbfloat16_t zm)
    __arm_streaming __arm_inout("za");

  void svmops_za32[_f16]_m(uint64_t tile, svbool_t pn, svbool_t pm,
                           svfloat16_t zn, svfloat16_t zm)
    __arm_streaming __arm_inout("za");

  void svmops_za32[_s8]_m(uint64_t tile, svbool_t pn, svbool_t pm,
                          svint8_t zn, svint8_t zm)
    __arm_streaming __arm_inout("za");

  void svmops_za32[_u8]_m(uint64_t tile, svbool_t pn, svbool_t pm,
                          svuint8_t zn, svuint8_t zm)
    __arm_streaming __arm_inout("za");

  // Only if __ARM_FEATURE_SME_I16I64 != 0
  void svmops_za64[_s16]_m(uint64_t tile, svbool_t pn, svbool_t pm,
                           svint16_t zn, svint16_t zm)
    __arm_streaming __arm_inout("za");

  // Only if __ARM_FEATURE_SME_I16I64 != 0
  void svmops_za64[_u16]_m(uint64_t tile, svbool_t pn, svbool_t pm,
                           svuint16_t zn, svuint16_t zm)
    __arm_streaming __arm_inout("za");
```

#### BFMOPS, FMOPS (non-widening)

``` c
  // Variants are also available for:
  //   _za16[_bf16]_m (only if __ARM_FEATURE_SME_B16B16 != 0)
  //   _za16[_f16]_m (only if __ARM_FEATURE_SME_F16F16 != 0)
  //   _za64[_f64]_m (only if __ARM_FEATURE_SME_F64F64 != 0)
  void svmops_za32[_f32]_m(uint64_t tile, svbool_t pn, svbool_t pm,
                           svfloat32_t zn, svfloat32_t zm)
    __arm_streaming __arm_inout("za");
```

#### BFTMOPA, FTMOPA, STMOPA, UTMOPA

``` c
  // Only if __ARM_FEATURE_SME_TMOP != 0
  // Variants are also available for:
  //   _za16[_f16_f16] (only if __ARM_FEATURE_SME_F16F16 != 0)
  //   _za16[_bf16_bf16] (only if __ARM_FEATURE_SME_B16B16 != 0)
  //   _za32[_bf16_bf16]
  //   _za32[_f16_f16]
  //   _za32[_s16_s16]
  //   _za32[_u16_u16]
  //   _za32[_s8_s8]
  //   _za32[_u8_u8]
  void svtmopa_lane_za32[_f32_f32](uint64_t tile, svfloat32x2_t zn, svfloat32_t zm,
                                   svuint8_t zk, uint64_t imm_idx)
    __arm_streaming __arm_inout("za");

  // Only if __ARM_FEATURE_SME_TMOP != 0 && __ARM_FEATURE_SME_F8F16 != 0
  void svtmopa_lane_za16[_mf8_mf8]_fpm(uint64_t tile, svmfloat8x2_t zn, svmfloat8_t zm,
                                       svuint8_t zk, uint64_t imm_idx, fpm_t fpm)
    __arm_streaming __arm_inout("za");

  // Only if __ARM_FEATURE_SME_TMOP != 0 && __ARM_FEATURE_SME_F8F32 != 0
  void svtmopa_lane_za32[_mf8_mf8]_fpm(uint64_t tile, svmfloat8x2_t zn, svmfloat8_t zm,
                                       svuint8_t zk, uint64_t imm_idx, fpm_t fpm)
    __arm_streaming __arm_inout("za");
```

#### SUTMOPA, USTMOPA

``` c
  // Only if __ARM_FEATURE_SME_TMOP != 0
  void svtmopa_lane_za32[_s8_u8](uint64_t tile, svint8x2_t zn, svuint8_t zm,
                                 svuint8_t zk, uint64_t imm_idx)
    __arm_streaming __arm_inout("za");

  // Only if __ARM_FEATURE_SME_TMOP != 0
  void svtmopa_lane_za32[_u8_s8](uint64_t tile, svuint8x2_t zn, svint8_t zm,
                                 svuint8_t zk, uint64_t imm_idx)
    __arm_streaming __arm_inout("za");
```

#### RDSVL

The following intrinsics read the length of a streaming vector:

``` c
  // Return the number of bytes in a streaming vector.
  // Equivalent to svcntb() when called in streaming mode.
  uint64_t svcntsb() __arm_streaming_compatible;

  // Return the number of halfwords in a streaming vector.
  // Equivalent to svcnth() when called in streaming mode.
  uint64_t svcntsh() __arm_streaming_compatible;

  // Return the number of words in a streaming vector.
  // Equivalent to svcntw() when called in streaming mode.
  uint64_t svcntsw() __arm_streaming_compatible;

  // Return the number of doublewords in a streaming vector.
  // Equivalent to svcntd() when called in streaming mode.
  uint64_t svcntsd() __arm_streaming_compatible;
```

`svcntsb()` is equivalent to an RDSVL instruction with an immediate
operand of 1. There are no intrinsics that map directly to other
immediate operands, or to the ADDSVL and ADDSPL instructions, but it is
possible to write these operations using normal C arithmetic. For example:

``` c
  x0 = svcntsb();           // corresponds to RDSVL x0, #1
  x0 = svcntsb() * 5;       // can be optimized to RDSVL x0, #5
  x0 = x1 + svcntsb();      // can be optimized to ADDSVL x0, x1, #1
  x0 = x1 - svcntsb() * 3;  // can be optimized to ADDSVL x0, x1, #-3
  x0 = x1 + svcntsd();      // can be optimized to ADDSPL x0, x1, #1
  x0 = x1 - svcntsw();      // can be optimized to ADDSPL x0, x1, #-2
```

#### SUMOPA

``` c
  void svsumopa_za32[_s8]_m(uint64_t tile, svbool_t pn, svbool_t pm,
                            svint8_t zn, svuint8_t zm)
    __arm_streaming __arm_inout("za");

  // Only if __ARM_FEATURE_SME_I16I64 != 0
  void svsumopa_za64[_s16]_m(uint64_t tile, svbool_t pn, svbool_t pm,
                             svint16_t zn, svuint16_t zm)
    __arm_streaming __arm_inout("za");
```

#### SUMOPS

``` c
  void svsumops_za32[_s8]_m(uint64_t tile, svbool_t pn, svbool_t pm,
                            svint8_t zn, svuint8_t zm)
    __arm_streaming __arm_inout("za");

  // Only if __ARM_FEATURE_SME_I16I64 != 0
  void svsumops_za64[_s16]_m(uint64_t tile, svbool_t pn, svbool_t pm,
                             svint16_t zn, svuint16_t zm)
    __arm_streaming __arm_inout("za");
```

#### USMOPA

``` c
  void svusmopa_za32[_u8]_m(uint64_t tile, svbool_t pn, svbool_t pm,
                            svuint8_t zn, svint8_t zm)
    __arm_streaming __arm_inout("za");

  // Only if __ARM_FEATURE_SME_I16I64 != 0
  void svusmopa_za64[_u16]_m(uint64_t tile, svbool_t pn, svbool_t pm,
                             svuint16_t zn, svint16_t zm)
    __arm_streaming __arm_inout("za");
```

#### USMOPS

``` c
  void svusmops_za32[_u8]_m(uint64_t tile, svbool_t pn, svbool_t pm,
                            svuint8_t zn, svint8_t zm)
    __arm_streaming __arm_inout("za");

  // Only if __ARM_FEATURE_SME_I16I64 != 0
  void svusmops_za64[_u16]_m(uint64_t tile, svbool_t pn, svbool_t pm,
                             svuint16_t zn, svint16_t zm)
    __arm_streaming __arm_inout("za");
```

#### ZERO

``` c
  void svzero_mask_za(uint64_t tile_mask)
    __arm_streaming_compatible __arm_inout("za");

  void svzero_za() __arm_streaming_compatible __arm_out("za");
```

### SME2 instruction intrinsics

The intrinsics in this section are available when `__ARM_FEATURE_SME2`
is defined.

#### ADD, SUB (store into ZA, single)

Multi-vector add/sub, storing into ZA

The additional '_write' suffix indicates that the operation is not accumulating;
the result is written directly into ZA.

``` c
  // Variants are available for:
  //   _za32[_s32]
  //   _za32[_u32]
  //   _za64[_s64] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u64] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svadd_write[_single]_za32[_s32]_vg1x2(uint32_t slice, svint32x2_t zn,
                                             svint32_t zm)
    __arm_streaming __arm_inout("za");


  // Variants are available for:
  //   _za32[_s32]
  //   _za32[_u32]
  //   _za64[_s64] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u64] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svadd_write[_single]_za32[_s32]_vg1x4(uint32_t slice, svint32x4_t zn,
                                             svint32_t zm)
    __arm_streaming __arm_inout("za");


  // Variants are available for:
  //   _za32[_s32]
  //   _za32[_u32]
  //   _za64[_s64] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u64] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svsub_write[_single]_za32[_u32]_vg1x2(uint32_t slice, svuint32x2_t zn,
                                             svuint32_t zm)
    __arm_streaming __arm_inout("za");


  // Variants are available for:
  //   _za32[_s32]
  //   _za32[_u32]
  //   _za64[_s64] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u64] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svsub_write[_single]_za32[_u32]_vg1x4(uint32_t slice, svuint32x4_t zn,
                                             svuint32_t zm)
    __arm_streaming __arm_inout("za");
  ```

#### ADD, SUB (store into ZA, multi)

Multi-vector add/sub, storing into ZA

The additional '_write' suffix indicates that the operation is not accumulating;
the result is written directly into ZA.

``` c
  // Variants are available for:
  //   _za32[_s32]
  //   _za32[_u32]
  //   _za64[_s64] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u64] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svadd_write_za32[_s32]_vg1x2(uint32_t slice,
                                    svint32x2_t zn, svint32x2_t zm)
    __arm_streaming __arm_inout("za");


  // Variants are available for:
  //   _za32[_s32]
  //   _za32[_u32]
  //   _za64[_s64] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u64] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svadd_write_za32[_s32]_vg1x4(uint32_t slice,
                                    svint32x4_t zn, svint32x4_t zm)
    __arm_streaming __arm_inout("za");


  // Variants are available for:
  //   _za32[_s32]
  //   _za32[_u32]
  //   _za64[_s64] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u64] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svsub_write_za32[_u32]_vg1x2(uint32_t slice,
                                    svuint32x2_t zn, svuint32x2_t zm)
    __arm_streaming __arm_inout("za");


  // Variants are available for:
  //   _za32[_s32]
  //   _za32[_u32]
  //   _za64[_s64] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u64] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svsub_write_za32[_u32]_vg1x4(uint32_t slice,
                                    svuint32x4_t zn, svuint32x4_t zm)
    __arm_streaming __arm_inout("za");
  ```

#### ADD (vectors)

Multi-vector add

``` c
  // Variants are also available for _single_u8_x2, _single_s16_x2,
  // _single_u16_x2, _single_s32_x2, _single_u32_x2, _single_s64_x2 and
  // _single_u64_x2
  svint8x2_t svadd[_single_s8_x2](svint8x2_t zdn, svint8_t zm) __arm_streaming;


  // Variants are also available for _single_u8_x4, _single_s16_x4,
  // _single_u16_x4, _single_s32_x4, _single_u32_x4, _single_s64_x4 and
  // _single_u64_x4
  svint8x4_t svadd[_single_s8_x4](svint8x4_t zdn, svint8_t zm) __arm_streaming;
  ```

#### ADD, SUB, BFADD, BFSUB, FADD, FSUB (accumulate into ZA)

Multi-vector add/sub and accumulate into ZA

``` c
  // Variants are available for:
  //   _za16[_bf16] (only if __ARM_FEATURE_SME_B16B16 != 0)
  //   _za16[_f16] (only if __ARM_FEATURE_SME_F16F16 != 0)
  //   _za32[_f32]
  //   _za32[_s32]
  //   _za32[_u32]
  //   _za64[_f64] (only if __ARM_FEATURE_SME_F64F64 != 0)
  //   _za64[_s64] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u64] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svadd_za32[_f32]_vg1x2(uint32_t slice, svfloat32x2_t zm)
    __arm_streaming __arm_inout("za");


  // Variants are available for:
  //   _za16[_bf16] (only if __ARM_FEATURE_SME_B16B16 != 0)
  //   _za16[_f16] (only if __ARM_FEATURE_SME_F16F16 != 0)
  //   _za32[_f32]
  //   _za32[_s32]
  //   _za32[_u32]
  //   _za64[_f64] (only if __ARM_FEATURE_SME_F64F64 != 0)
  //   _za64[_s64] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u64] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svadd_za32[_f32]_vg1x4(uint32_t slice, svfloat32x4_t zm)
    __arm_streaming __arm_inout("za");


  // Variants are available for:
  //   _za16[_bf16] (only if __ARM_FEATURE_SME_B16B16 != 0)
  //   _za16[_f16] (only if __ARM_FEATURE_SME_F16F16 != 0)
  //   _za32[_f32]
  //   _za32[_s32]
  //   _za32[_u32]
  //   _za64[_f64] (only if __ARM_FEATURE_SME_F64F64 != 0)
  //   _za64[_s64] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u64] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svsub_za32[_f32]_vg1x2(uint32_t slice, svfloat32x2_t zm)
    __arm_streaming __arm_inout("za");


  // Variants are available for:
  //   _za16[_bf16] (only if __ARM_FEATURE_SME_B16B16 != 0)
  //   _za16[_f16] (only if __ARM_FEATURE_SME_F16F16 != 0)
  //   _za32[_f32]
  //   _za32[_s32]
  //   _za32[_u32]
  //   _za64[_f64] (only if __ARM_FEATURE_SME_F64F64 != 0)
  //   _za64[_s64] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u64] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svsub_za32[_f32]_vg1x4(uint32_t slice, svfloat32x4_t zm)
    __arm_streaming __arm_inout("za");
  ```

#### BFCVTN, FCVTN

Multi-vector floating-point convert from single-precision to interleaved half-precision/BFloat16

``` c
  // Variants are also available for _f16[_f32_x2]
  svbfloat16_t svcvtn_bf16[_f32_x2](svfloat32x2_t zn) __arm_streaming;
  ```

#### FCVTL

Multi-vector floating-point convert from half-precision to deinterleaved
single-precision.

```
  // Only if __ARM_FEATURE_SME_F16F16 != 0
  svfloat32x2_t svcvtl_f32[_f16_x2](svfloat16_t zn) __arm_streaming;
```

#### FCVT, BFCVT, FCVTZS, FCVTZU, SCVTF, UCVTF

Multi-vector convert to/from floating-point.

``` c
  // Variants are also available for _f16[_f32_x2]
  svbfloat16_t svcvt_bf16[_f32_x2](svfloat32x2_t zn) __arm_streaming;


  // Variants are also available for _f32[_u32_x2], _s32[_f32_x2] and _u32[_f32_x2]
  svfloat32x2_t svcvt_f32[_s32_x2](svint32x2_t zn) __arm_streaming;


  // Variants are also available for _f32[_u32_x4], _s32[_f32_x4] and _u32[_f32_x4]
  svfloat32x4_t svcvt_f32[_s32_x4](svint32x4_t zn) __arm_streaming;

  // Only if __ARM_FEATURE_SME_F16F16 != 0
  svfloat32x2_t svcvt_f32[_f16_x2](svfloat16_t zn) __arm_streaming;
  ```

#### SQCVT, SQCVTU, UQCVT

Multi-vector saturating extract narrow

``` c
  // Variants are also available for _u16[_s32_x2] and _u16[_u32_x2]
  svint16_t svqcvt_s16[_s32_x2](svint32x2_t zn) __arm_streaming;


  // Variants are also available for _u8[_s32_x4], _u8[_u32_x4], _s16[_s64_x4],
  // _u16[_s64_x4] and _u16[_u64_x4]
  svint8_t svqcvt_s8[_s32_x4](svint32x4_t zn) __arm_streaming;
  ```

#### SQCVTN, SQCVTUN, UQCVTN

Multi-vector saturating extract narrow and interleave

``` c
  // Variants are also available for _u8[_s32_x4], _u8[_u32_x4], _s16[_s64_x4],
  // _u16[_s64_x4] and _u16[_u64_x4]
  svint8_t svqcvtn_s8[_s32_x4](svint32x4_t zn) __arm_streaming;
  ```

#### FDOT, BFDOT, SUDOT, USDOT, SDOT, UDOT (store into ZA, single)

Multi-vector dot-product (2-way and 4-way)

``` c
  // Variants are available for:
  //   _za32[_bf16]
  //   _za32[_f16]
  //   _za32[_s8]
  //   _za32[_s16]
  //   _za32[_u8]
  //   _za32[_u16]
  //   _za64[_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svdot[_single]_za32[_bf16]_vg1x2(uint32_t slice, svbfloat16x2_t zn,
                                        svbfloat16_t zm)
    __arm_streaming __arm_inout("za");


  // Variants are available for:
  //   _za32[_bf16]
  //   _za32[_f16]
  //   _za32[_s8]
  //   _za32[_s16]
  //   _za32[_u8]
  //   _za32[_u16]
  //   _za64[_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svdot[_single]_za32[_bf16]_vg1x4(uint32_t slice,
                                        svbfloat16x4_t zn, svbfloat16_t zm)
    __arm_streaming __arm_inout("za");


  void svsudot[_single]_za32[_s8]_vg1x2(uint32_t slice, svint8x2_t zn,
                                        svuint8_t zm)
    __arm_streaming __arm_inout("za");


  void svsudot[_single]_za32[_s8]_vg1x4(uint32_t slice, svint8x4_t zn,
                                        svuint8_t zm)
    __arm_streaming __arm_inout("za");


  void svusdot[_single]_za32[_u8]_vg1x2(uint32_t slice, svuint8x2_t zn,
                                        svint8_t zm)
    __arm_streaming __arm_inout("za");


  void svusdot[_single]_za32[_u8]_vg1x4(uint32_t slice, svuint8x4_t zn,
                                        svint8_t zm)
    __arm_streaming __arm_inout("za");
  ```

#### FDOT, BFDOT, SUDOT, USDOT, SDOT, UDOT (store into ZA, multi)

Multi-vector dot-product (2-way and 4-way)

``` c
  // Variants are available for:
  //   _za32[_bf16]
  //   _za32[_f16]
  //   _za32[_s8]
  //   _za32[_s16]
  //   _za32[_u8]
  //   _za32[_u16]
  //   _za64[_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svdot_za32[_bf16]_vg1x2(uint32_t slice, svbfloat16x2_t zn,
                               svbfloat16x2_t zm)
    __arm_streaming __arm_inout("za");


  // Variants are available for:
  //   _za32[_bf16]
  //   _za32[_f16]
  //   _za32[_s8]
  //   _za32[_s16]
  //   _za32[_u8]
  //   _za32[_u16]
  //   _za64[_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svdot_za32[_bf16]_vg1x4(uint32_t slice, svbfloat16x4_t zn,
                               svbfloat16x4_t zm)
    __arm_streaming __arm_inout("za");


  void svsudot_za32[_s8]_vg1x2(uint32_t slice, svint8x2_t zn, svuint8x2_t zm)
    __arm_streaming __arm_inout("za");


  void svsudot_za32[_s8]_vg1x4(uint32_t slice, svint8x4_t zn, svuint8x4_t zm)
    __arm_streaming __arm_inout("za");


  void svusdot_za32[_u8]_vg1x2(uint32_t slice, svuint8x2_t zn, svint8x2_t zm)
    __arm_streaming __arm_inout("za");


  void svusdot_za32[_u8]_vg1x4(uint32_t slice, svuint8x4_t zn, svint8x4_t zm)
    __arm_streaming __arm_inout("za");
  ```

#### FDOT, BFDOT, SUDOT, USDOT, SDOT, UDOT (store into ZA, indexed)

Multi-vector dot-product (2-way and 4-way)

``` c
  // Variants are available for:
  //   _za32[_bf16]
  //   _za32[_f16]
  //   _za32[_s8]
  //   _za32[_s16]
  //   _za32[_u8]
  //   _za32[_u16]
  //   _za64[_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svdot_lane_za32[_bf16]_vg1x2(uint32_t slice, svbfloat16x2_t zn,
                                    svbfloat16_t zm, uint64_t imm_idx)
    __arm_streaming __arm_inout("za");


  // Variants are available for:
  //   _za32[_bf16]
  //   _za32[_f16]
  //   _za32[_s8]
  //   _za32[_s16]
  //   _za32[_u8]
  //   _za32[_u16]
  //   _za64[_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svdot_lane_za32[_bf16]_vg1x4(uint32_t slice, svbfloat16x4_t zn,
                                    svbfloat16_t zm, uint64_t imm_idx)
    __arm_streaming __arm_inout("za");


  void svsudot_lane_za32[_s8]_vg1x2(uint32_t slice, svint8x2_t zn, svuint8_t zm,
                                    uint64_t imm_idx)
    __arm_streaming __arm_inout("za");


  void svsudot_lane_za32[_s8]_vg1x4(uint32_t slice, svint8x4_t zn, svuint8_t zm,
                                    uint64_t imm_idx)
    __arm_streaming __arm_inout("za");


  void svusdot_lane_za32[_u8]_vg1x2(uint32_t slice, svuint8x2_t zn, svint8_t zm,
                                    uint64_t imm_idx)
    __arm_streaming __arm_inout("za");


  void svusdot_lane_za32[_u8]_vg1x4(uint32_t slice, svuint8x4_t zn, svint8_t zm,
                                    uint64_t imm_idx)
    __arm_streaming __arm_inout("za");
  ```

#### FVDOT, BFVDOT, SUVDOT, USVDOT, SVDOT, UVDOT

Multi-vector vertical dot-product by indexed element.

``` c
  void svsuvdot_lane_za32[_s8]_vg1x4(uint32_t slice, svint8x4_t zn,
                                     svuint8_t zm, uint64_t imm_idx)
    __arm_streaming __arm_inout("za");


  void svusvdot_lane_za32[_u8]_vg1x4(uint32_t slice, svuint8x4_t zn,
                                     svint8_t zm, uint64_t imm_idx)
    __arm_streaming __arm_inout("za");


  // Variants are also available for _za32[_f16], _za32[_s16] and _za32[_u16]
  void svvdot_lane_za32[_bf16]_vg1x2(uint32_t slice, svbfloat16x2_t zn,
                                     svbfloat16_t zm, uint64_t imm_idx)
    __arm_streaming __arm_inout("za");


  // Variants are available for:
  //   _za32[_s8]
  //   _za32[_u8]
  //   _za64[_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svvdot_lane_za32[_s8]_vg1x4(uint32_t slice, svint8x4_t zn, svint8_t zm,
                                   uint64_t imm_idx)
    __arm_streaming __arm_inout("za");
  ```

#### UMOPA, SMOPA, UMOPS, SMOPS

Integer sum of outer products and accumulate/subtract (2-way)

``` c
  // Variants are also available for _za32[_u16]
  void svmopa_za32[_s16]_m(uint64_t tile, svbool_t pn, svbool_t pm, svint16_t zn,
                           svint16_t zm)
    __arm_streaming __arm_inout("za");


  // Variants are also available for _za32[_u16]
  void svmops_za32[_s16]_m(uint64_t tile, svbool_t pn, svbool_t pm, svint16_t zn,
                           svint16_t zm)
    __arm_streaming __arm_inout("za");
  ```

#### BMOPA, BMOPS

Bitwise exclusive NOR population count outer product and accumulate/subtract

``` c
  // Variants are also available for _za32[_s32]
  void svbmopa_za32[_u32]_m(uint64_t tile, svbool_t pn, svbool_t pm,
                            svuint32_t zn, svuint32_t zm)
    __arm_streaming __arm_inout("za");


  // Variants are also available for _za32[_s32]
  void svbmops_za32[_u32]_m(uint64_t tile, svbool_t pn, svbool_t pm,
                            svuint32_t zn, svuint32_t zm)
    __arm_streaming __arm_inout("za");
  ```

#### BFMLA, BFMLS, FMLA, FMLS (single)

Multi-vector floating-point fused multiply-add/subtract

``` c
  // Variants are available for:
  //   _za16[_bf16] (only if __ARM_FEATURE_SME_B16B16 != 0)
  //   _za16[_f16] (only if __ARM_FEATURE_SME_F16F16 != 0)
  //   _za32[_f32]
  //   _za64[_f64] (only if __ARM_FEATURE_SME_F64F64 != 0)
  void svmla[_single]_za32[_f32]_vg1x2(uint32_t slice, svfloat32x2_t zn,
                                       svfloat32_t zm)
    __arm_streaming __arm_inout("za");


  // Variants are available for:
  //   _za16[_bf16] (only if __ARM_FEATURE_SME_B16B16 != 0)
  //   _za16[_f16] (only if __ARM_FEATURE_SME_F16F16 != 0)
  //   _za32[_f32]
  //   _za64[_f64] (only if __ARM_FEATURE_SME_F64F64 != 0)
  void svmla[_single]_za32[_f32]_vg1x4(uint32_t slice, svfloat32x4_t zn,
                                       svfloat32_t zm)
    __arm_streaming __arm_inout("za");


  // Variants are available for:
  //   _za16[_bf16] (only if __ARM_FEATURE_SME_B16B16 != 0)
  //   _za16[_f16] (only if __ARM_FEATURE_SME_F16F16 != 0)
  //   _za32[_f32]
  //   _za64[_f64] (only if __ARM_FEATURE_SME_F64F64 != 0)
  void svmls[_single]_za32[_f32]_vg1x2(uint32_t slice, svfloat32x2_t zn,
                                       svfloat32_t zm)
    __arm_streaming __arm_inout("za");


  // Variants are available for:
  //   _za16[_bf16] (only if __ARM_FEATURE_SME_B16B16 != 0)
  //   _za16[_f16] (only if __ARM_FEATURE_SME_F16F16 != 0)
  //   _za32[_f32]
  //   _za64[_f64] (only if __ARM_FEATURE_SME_F64F64 != 0)
  void svmls[_single]_za32[_f32]_vg1x4(uint32_t slice, svfloat32x4_t zn,
                                       svfloat32_t zm)
    __arm_streaming __arm_inout("za");
  ```

#### BFMLA, BFMLS, FMLA, FMLS (multi)

Multi-vector floating-point fused multiply-add/subtract

``` c
  // Variants are available for:
  //   _za16[_bf16] (only if __ARM_FEATURE_SME_B16B16 != 0)
  //   _za16[_f16] (only if __ARM_FEATURE_SME_F16F16 != 0)
  //   _za32[_f32]
  //   _za64[_f64] (only if __ARM_FEATURE_SME_F64F64 != 0)
  void svmla_za32[_f32]_vg1x2(uint32_t slice, svfloat32x2_t zn,
                              svfloat32x2_t zm)
    __arm_streaming __arm_inout("za");


  // Variants are available for:
  //   _za16[_bf16] (only if __ARM_FEATURE_SME_B16B16 != 0)
  //   _za16[_f16] (only if __ARM_FEATURE_SME_F16F16 != 0)
  //   _za32[_f32]
  //   _za64[_f64] (only if __ARM_FEATURE_SME_F64F64 != 0)
  void svmla_za32[_f32]_vg1x4(uint32_t slice, svfloat32x4_t zn,
                              svfloat32x4_t zm)
    __arm_streaming __arm_inout("za");


  // Variants are available for:
  //   _za16[_bf16] (only if __ARM_FEATURE_SME_B16B16 != 0)
  //   _za16[_f16] (only if __ARM_FEATURE_SME_F16F16 != 0)
  //   _za32[_f32]
  //   _za64[_f64] (only if __ARM_FEATURE_SME_F64F64 != 0)
  void svmls_za32[_f32]_vg1x2(uint32_t slice, svfloat32x2_t zn,
                              svfloat32x2_t zm)
    __arm_streaming __arm_inout("za");


  // Variants are available for:
  //   _za16[_bf16] (only if __ARM_FEATURE_SME_B16B16 != 0)
  //   _za16[_f16] (only if __ARM_FEATURE_SME_F16F16 != 0)
  //   _za32[_f32]
  //   _za64[_f64] (only if __ARM_FEATURE_SME_F64F64 != 0)
  void svmls_za32[_f32]_vg1x4(uint32_t slice, svfloat32x4_t zn,
                              svfloat32x4_t zm)
    __arm_streaming __arm_inout("za");
  ```

#### BFMLA, BFMLS, FMLA, FMLS (indexed)

Multi-vector floating-point fused multiply-add/subtract

``` c
  // Variants are available for:
  //   _za16[_bf16] (only if __ARM_FEATURE_SME_B16B16 != 0)
  //   _za16[_f16] (only if __ARM_FEATURE_SME_F16F16 != 0)
  //   _za32[_f32]
  //   _za64[_f64] (only if __ARM_FEATURE_SME_F64F64 != 0)
  void svmla_lane_za32[_f32]_vg1x2(uint32_t slice, svfloat32x2_t zn,
                                   svfloat32_t zm, uint64_t imm_idx)
    __arm_streaming __arm_inout("za");


  // Variants are available for:
  //   _za16[_bf16] (only if __ARM_FEATURE_SME_B16B16 != 0)
  //   _za16[_f16] (only if __ARM_FEATURE_SME_F16F16 != 0)
  //   _za32[_f32]
  //   _za64[_f64] (only if __ARM_FEATURE_SME_F64F64 != 0)
  void svmla_lane_za32[_f32]_vg1x4(uint32_t slice, svfloat32x4_t zn,
                                   svfloat32_t zm, uint64_t imm_idx)
    __arm_streaming __arm_inout("za");


  // Variants are available for:
  //   _za16[_bf16] (only if __ARM_FEATURE_SME_B16B16 != 0)
  //   _za16[_f16] (only if __ARM_FEATURE_SME_F16F16 != 0)
  //   _za32[_f32]
  //   _za64[_f64] (only if __ARM_FEATURE_SME_F64F64 != 0)
  void svmls_lane_za32[_f32]_vg1x2(uint32_t slice, svfloat32x2_t zn,
                                   svfloat32_t zm, uint64_t imm_idx)
    __arm_streaming __arm_inout("za");


  // Variants are available for:
  //   _za16[_bf16] (only if __ARM_FEATURE_SME_B16B16 != 0)
  //   _za16[_f16] (only if __ARM_FEATURE_SME_F16F16 != 0)
  //   _za32[_f32]
  //   _za64[_f64] (only if __ARM_FEATURE_SME_F64F64 != 0)
  void svmls_lane_za32[_f32]_vg1x4(uint32_t slice, svfloat32x4_t zn,
                                   svfloat32_t zm, uint64_t imm_idx)
    __arm_streaming __arm_inout("za");
  ```

#### FMLAL, BFMLAL, SMLAL, UMLAL (single)

Multi-vector multiply-add long (widening)

``` c
  // Variants are also available for _za32[_f16], _za32[_s16] and _za32[_u16]
  void svmla_za32[_bf16]_vg2x1(uint32_t slice, svbfloat16_t zn,
                               svbfloat16_t zm)
    __arm_streaming __arm_inout("za");


  // Variants are also available for _za32[_f16], _za32[_s16] and _za32[_u16]
  void svmla[_single]_za32[_bf16]_vg2x2(uint32_t slice, svbfloat16x2_t zn,
                                        svbfloat16_t zm)
    __arm_streaming __arm_inout("za");


  // Variants are also available for _za32[_f16], _za32[_s16] and _za32[_u16]
  void svmla[_single]_za32[_bf16]_vg2x4(uint32_t slice, svbfloat16x4_t zn,
                                        svbfloat16_t zm)
    __arm_streaming __arm_inout("za");
  ```

#### FMLAL, BFMLAL, SMLAL, UMLAL (multi)

Multi-vector multiply-add long (widening)

``` c
  // Variants are also available for _za32[_f16], _za32[_s16] and _za32[_u16]
  void svmla_za32[_bf16]_vg2x2(uint32_t slice, svbfloat16x2_t zn,
                               svbfloat16x2_t zm)
    __arm_streaming __arm_inout("za");


  // Variants are also available for _za32[_f16], _za32[_s16] and _za32[_u16]
  void svmla_za32[_bf16]_vg2x4(uint32_t slice, svbfloat16x4_t zn,
                               svbfloat16x4_t zm)
    __arm_streaming __arm_inout("za");
  ```

#### FMLAL, BFMLAL, SMLAL, UMLAL (indexed)

Multi-vector multiply-add long (widening)

``` c
  // Variants are also available for _za32[_f16], _za32[_s16] and _za32[_u16]
  void svmla_lane_za32[_bf16]_vg2x1(uint32_t slice, svbfloat16_t zn,
                                    svbfloat16_t zm, uint64_t imm_idx)
    __arm_streaming __arm_inout("za");


  // Variants are also available for _za32[_f16], _za32[_s16] and _za32[_u16]
  void svmla_lane_za32[_bf16]_vg2x2(uint32_t slice, svbfloat16x2_t zn,
                                    svbfloat16_t zm, uint64_t imm_idx)
    __arm_streaming __arm_inout("za");


  // Variants are also available for _za32[_f16], _za32[_s16] and _za32[_u16]
  void svmla_lane_za32[_bf16]_vg2x4(uint32_t slice, svbfloat16x4_t zn,
                                    svbfloat16_t zm, uint64_t imm_idx)
    __arm_streaming __arm_inout("za");
  ```

#### BFMLSL, FMLSL, UMLSL, SMLSL (single)

Multi-vector multiply-subtract long (widening)

``` c
  // Variants are also available for _za32[_f16], _za32[_s16] and _za32[_u16]
  void svmls_za32[_bf16]_vg2x1(uint32_t slice, svbfloat16_t zn,
                               svbfloat16_t zm)
    __arm_streaming __arm_inout("za");


  // Variants are also available for _za32[_f16], _za32[_s16] and _za32[_u16]
  void svmls[_single]_za32[_bf16]_vg2x2(uint32_t slice, svbfloat16x2_t zn,
                                        svbfloat16_t zm)
    __arm_streaming __arm_inout("za");


  // Variants are also available for _za32[_f16], _za32[_s16] and _za32[_u16]
  void svmls[_single]_za32[_bf16]_vg2x4(uint32_t slice, svbfloat16x4_t zn,
                                        svbfloat16_t zm)
    __arm_streaming __arm_inout("za");
  ```

#### BFMLSL, FMLSL, UMLSL, SMLSL (multi)

Multi-vector multiply-subtract long (widening)

``` c
  // Variants are also available for _za32[_f16], _za32[_s16] and _za32[_u16]
  void svmls_za32[_bf16]_vg2x2(uint32_t slice, svbfloat16x2_t zn,
                               svbfloat16x2_t zm)
    __arm_streaming __arm_inout("za");


  // Variants are also available for _za32[_f16], _za32[_s16] and _za32[_u16]
  void svmls_za32[_bf16]_vg2x4(uint32_t slice, svbfloat16x4_t zn,
                               svbfloat16x4_t zm)
    __arm_streaming __arm_inout("za");
  ```

#### BFMLSL, FMLSL, UMLSL, SMLSL (indexed)

Multi-vector multiply-subtract long (widening)

``` c
  // Variants are also available for _za32[_f16], _za32[_s16] and _za32[_u16]
  void svmls_lane_za32[_bf16]_vg2x1(uint32_t slice, svbfloat16_t zn,
                                    svbfloat16_t zm, uint64_t imm_idx)
    __arm_streaming __arm_inout("za");


  // Variants are also available for _za32[_f16], _za32[_s16] and _za32[_u16]
  void svmls_lane_za32[_bf16]_vg2x2(uint32_t slice, svbfloat16x2_t zn,
                                    svbfloat16_t zm, uint64_t imm_idx)
    __arm_streaming __arm_inout("za");


  // Variants are also available for _za32[_f16], _za32[_s16] and _za32[_u16]
  void svmls_lane_za32[_bf16]_vg2x4(uint32_t slice, svbfloat16x4_t zn,
                                    svbfloat16_t zm, uint64_t imm_idx)
    __arm_streaming __arm_inout("za");
  ```

#### UMLALL, SMLALL, USMLALL, SUMLALL (single)

Multi-vector multiply-add long long (widening)

``` c
  // Variants are available for:
  //   _za32[_s8]
  //   _za32[_u8]
  //   _za64[_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmla_za32[_s8]_vg4x1(uint32_t slice, svint8_t zn, svint8_t zm)
    __arm_streaming __arm_inout("za");


  // Variants are available for:
  //   _za32[_s8]
  //   _za32[_u8]
  //   _za64[_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmla[_single]_za32[_s8]_vg4x2(uint32_t slice, svint8x2_t zn,
                                      svint8_t zm)
    __arm_streaming __arm_inout("za");


  // Variants are available for:
  //   _za32[_s8]
  //   _za32[_u8]
  //   _za64[_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmla[_single]_za32[_s8]_vg4x4(uint32_t slice, svint8x4_t zn,
                                      svint8_t zm)
    __arm_streaming __arm_inout("za");


  void svsumla_za32[_s8]_vg4x1(uint32_t slice, svint8_t zn, svuint8_t zm)
    __arm_streaming __arm_inout("za");


  void svsumla[_single]_za32[_s8]_vg4x2(uint32_t slice, svint8x2_t zn,
                                        svuint8_t zm)
    __arm_streaming __arm_inout("za");


  void svsumla[_single]_za32[_s8]_vg4x4(uint32_t slice, svint8x4_t zn,
                                        svuint8_t zm)
    __arm_streaming __arm_inout("za");


  void svusmla_za32[_u8]_vg4x1(uint32_t slice, svuint8_t zn, svint8_t zm)
    __arm_streaming __arm_inout("za");


  void svusmla[_single]_za32[_u8]_vg4x2(uint32_t slice, svuint8x2_t zn,
                                        svint8_t zm)
    __arm_streaming __arm_inout("za");


  void svusmla[_single]_za32[_u8]_vg4x4(uint32_t slice, svuint8x4_t zn,
                                        svint8_t zm)
    __arm_streaming __arm_inout("za");
  ```

#### UMLALL, SMLALL, USMLALL, SUMLALL (multi)

Multi-vector multiply-add long long (widening)

``` c
  // Variants are available for:
  //   _za32[_s8]
  //   _za32[_u8]
  //   _za64[_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmla_za32[_s8]_vg4x2(uint32_t slice, svint8x2_t zn, svint8x2_t zm)
    __arm_streaming __arm_inout("za");


  // Variants are available for:
  //   _za32[_s8]
  //   _za32[_u8]
  //   _za64[_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmla_za32[_s8]_vg4x4(uint32_t slice, svint8x4_t zn, svint8x4_t zm)
    __arm_streaming __arm_inout("za");


  void svsumla_za32[_s8]_vg4x2(uint32_t slice, svint8x2_t zn, svuint8x2_t zm)
    __arm_streaming __arm_inout("za");


  void svsumla_za32[_s8]_vg4x4(uint32_t slice, svint8x4_t zn, svuint8x4_t zm)
    __arm_streaming __arm_inout("za");


  void svusmla_za32[_u8]_vg4x2(uint32_t slice, svuint8x2_t zn, svint8x2_t zm)
    __arm_streaming __arm_inout("za");


  void svusmla_za32[_u8_vg4x4(uint32_t slice, svuint8x4_t zn, svint8x4_t zm)
    __arm_streaming __arm_inout("za");
  ```

#### UMLALL, SMLALL, USMLALL, SUMLALL (indexed)

Multi-vector multiply-add long long (widening)

``` c
  // Variants are available for:
  //   _za32[_s8]
  //   _za32[_u8]
  //   _za64[_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmla_lane_za32[_s8]_vg4x1(uint32_t slice, svint8_t zn, svint8_t zm,
                                  uint64_t imm_idx)
    __arm_streaming __arm_inout("za");


  // Variants are available for:
  //   _za32[_s8]
  //   _za32[_u8]
  //   _za64[_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmla_lane_za32[_s8]_vg4x2(uint32_t slice, svint8x2_t zn, svint8_t zm,
                                  uint64_t imm_idx)
    __arm_streaming __arm_inout("za");


  // Variants are available for:
  //   _za32[_s8]
  //   _za32[_u8]
  //   _za64[_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmla_lane_za32[_s8]_vg4x4(uint32_t slice, svint8x4_t zn, svint8_t zm,
                                  uint64_t imm_idx)
    __arm_streaming __arm_inout("za");


  void svsumla_lane_za32[_s8]_vg4x1(uint32_t slice, svint8_t zn,
                                    svuint8_t zm, uint64_t imm_idx)
    __arm_streaming __arm_inout("za");


  void svsumla_lane_za32[_s8]_vg4x2(uint32_t slice, svint8x2_t zn,
                                    svuint8_t zm, uint64_t imm_idx)
    __arm_streaming __arm_inout("za");


  void svsumla_lane_za32[_s8]_vg4x4(uint32_t slice, svint8x4_t zn,
                                    svuint8_t zm, uint64_t imm_idx)
    __arm_streaming __arm_inout("za");


  void svusmla_lane_za32[_u8]_vg4x1(uint32_t slice, svuint8_t zn,
                                    svint8_t zm, uint64_t imm_idx)
    __arm_streaming __arm_inout("za");


  void svusmla_lane_za32[_u8]_vg4x2(uint32_t slice, svuint8x2_t zn,
                                    svint8_t zm, uint64_t imm_idx)
    __arm_streaming __arm_inout("za");


  void svusmla_lane_za32[_u8]_vg4x4(uint32_t slice, svuint8x4_t zn,
                                    svint8_t zm, uint64_t imm_idx)
    __arm_streaming __arm_inout("za");
  ```

#### SMLSLL, UMLSLL (single)

Multi-vector multiply-subtract long long (widening)

``` c
  // Variants are available for:
  //   _za32[_s8]
  //   _za32[_u8]
  //   _za64[_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmls_za32[_s8]_vg4x1(uint32_t slice, svint8_t zn, svint8_t zm)
    __arm_streaming __arm_inout("za");


  // Variants are available for:
  //   _za32[_s8]
  //   _za32[_u8]
  //   _za64[_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmls[_single]_za32[_s8]_vg4x2(uint32_t slice, svint8x2_t zn,
                                      svint8_t zm)
    __arm_streaming __arm_inout("za");


  // Variants are available for:
  //   _za32[_s8]
  //   _za32[_u8]
  //   _za64[_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmls[_single]_za32[_s8]_vg4x4(uint32_t slice, svint8x4_t zn,
                                      svint8_t zm)
    __arm_streaming __arm_inout("za");
  ```

#### SMLSLL, UMLSLL (multi)

Multi-vector multiply-subtract long long (widening)

``` c
  // Variants are available for:
  //   _za32[_s8]
  //   _za32[_u8]
  //   _za64[_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmls_za32[_s8]_vg4x2(uint32_t slice, svint8x2_t zn, svint8x2_t zm)
    __arm_streaming __arm_inout("za");


  // Variants are available for:
  //   _za32[_s8]
  //   _za32[_u8]
  //   _za64[_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmls_za32[_s8]_vg4x4(uint32_t slice, svint8x4_t zn, svint8x4_t zm)
    __arm_streaming __arm_inout("za");
  ```

#### SMLSLL, UMLSLL (indexed)

Multi-vector multiply-subtract long long (widening)

``` c
  // Variants are available for:
  //   _za32[_s8]
  //   _za32[_u8]
  //   _za64[_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmls_lane_za32[_s8]_vg4x1(uint32_t slice, svint8_t zn, svint8_t zm,
                                  uint64_t imm_idx)
    __arm_streaming __arm_inout("za");


  // Variants are available for:
  //   _za32[_s8]
  //   _za32[_u8]
  //   _za64[_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmls_lane_za32[_s8]_vg4x2(uint32_t slice, svint8x2_t zn, svint8_t zm,
                                  uint64_t imm_idx)
    __arm_streaming __arm_inout("za");


  // Variants are available for:
  //   _za32[_s8]
  //   _za32[_u8]
  //   _za64[_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmls_lane_za32[_s8]_vg4x4(uint32_t slice, svint8x4_t zn, svint8_t zm,
                                  uint64_t imm_idx)
    __arm_streaming __arm_inout("za");
  ```

#### SMAX, SMIN, UMAX, UMIN, BFMAX, BFMIN, FMAX, FMIN (single)

Multi-vector min/max

``` c
  // Variants are also available for:
  //   _single_s8_x2
  //   _single_u8_x2,
  //   _single_bf16_x2 (only if __ARM_FEATURE_SVE_B16B16 != 0)
  //   _single_s16_x2
  //   _single_u16_x2
  //   _single_s32_x2
  //   _single_u32_x2,
  //   _single_f32_x2
  //   _single_s64_x2
  //   _single_u64_x2
  //   _single_f64_x2
  svfloat16x2_t svmax[_single_f16_x2](svfloat16x2_t zdn, svfloat16_t zm)
    __arm_streaming;


  // Variants are also available for:
  //   _single_s8_x4
  //   _single_u8_x4,
  //   _single_bf16_x4 (only if __ARM_FEATURE_SVE_B16B16 != 0)
  //   _single_s16_x4
  //   _single_u16_x4
  //   _single_s32_x4
  //   _single_u32_x4,
  //   _single_f32_x4
  //   _single_s64_x4
  //   _single_u64_x4
  //   _single_f64_x4
  svfloat16x4_t svmax[_single_f16_x4](svfloat16x4_t zdn, svfloat16_t zm)
    __arm_streaming;


  // Variants are also available for:
  //   _single_s8_x2
  //   _single_u8_x2,
  //   _single_bf16_x2 (only if __ARM_FEATURE_SVE_B16B16 != 0)
  //   _single_s16_x2
  //   _single_u16_x2
  //   _single_s32_x2
  //   _single_u32_x2,
  //   _single_f32_x2
  //   _single_s64_x2
  //   _single_u64_x2
  //   _single_f64_x2
  svfloat16x2_t svmin[_single_f16_x2](svfloat16x2_t zdn, svfloat16_t zm)
    __arm_streaming;


  // Variants are also available for:
  //   _single_s8_x4
  //   _single_u8_x4,
  //   _single_bf16_x4 (only if __ARM_FEATURE_SVE_B16B16 != 0)
  //   _single_s16_x4
  //   _single_u16_x4
  //   _single_s32_x4
  //   _single_u32_x4,
  //   _single_f32_x4
  //   _single_s64_x4
  //   _single_u64_x4
  //   _single_f64_x4
  svfloat16x4_t svmin[_single_f16_x4](svfloat16x4_t zdn, svfloat16_t zm)
    __arm_streaming;
  ```

#### SMAX, SMIN, UMAX, UMIN, BFMAX, BFMIN, FMAX, FMIN (multi)

Multi-vector min/max

``` c
  // Variants are also available for:
  //   _s8_x2
  //   _u8_x2
  //   _bf16_x2 (only if __ARM_FEATURE_SVE_B16B16 != 0)
  //   _s16_x2
  //   _u16_x2,
  //   _s32_x2
  //   _u32_x2
  //   _f32_x2
  //   _s64_x2
  //   _u64_x2
  //   _f64_x2
  svfloat16x2_t svmax[_f16_x2](svfloat16x2_t zdn, svfloat16x2_t zm)
    __arm_streaming;


  // Variants are also available for:
  //   _s8_x4
  //   _u8_x4
  //   _bf16_x4 (only if __ARM_FEATURE_SVE_B16B16 != 0)
  //   _s16_x4
  //   _u16_x4,
  //   _s32_x4
  //   _u32_x4
  //   _f32_x4
  //   _s64_x4
  //   _u64_x4
  //   _f64_x4
  svfloat16x4_t svmax[_f16_x4](svfloat16x4_t zdn, svfloat16x4_t zm)
    __arm_streaming;


  // Variants are also available for:
  //   _s8_x2
  //   _u8_x2
  //   _bf16_x2 (only if __ARM_FEATURE_SVE_B16B16 != 0)
  //   _s16_x2
  //   _u16_x2,
  //   _s32_x2
  //   _u32_x2
  //   _f32_x2
  //   _s64_x2
  //   _u64_x2
  //   _f64_x2
  svfloat16x2_t svmin[_f16_x2](svfloat16x2_t zdn, svfloat16x2_t zm)
    __arm_streaming;


  // Variants are also available for:
  //   _s8_x4
  //   _u8_x4
  //   _bf16_x4 (only if __ARM_FEATURE_SVE_B16B16 != 0)
  //   _s16_x4
  //   _u16_x4,
  //   _s32_x4
  //   _u32_x4
  //   _f32_x4
  //   _s64_x4
  //   _u64_x4
  //   _f64_x4
  svfloat16x4_t svmin[_f16_x4](svfloat16x4_t zdn, svfloat16x4_t zm)
    __arm_streaming;
  ```

#### BFMAXNM, BFMINNM, FMAXNM, FMINNM (single)

Multi-vector floating point min/max number

``` c
  // Variants are also available for:
  //   _single_bf16_x2 (only if __ARM_FEATURE_SVE_B16B16 != 0)
  //   _single_f32_x2
  //   _single_f64_x2
  svfloat16x2_t svmaxnm[_single_f16_x2](svfloat16x2_t zdn, svfloat16_t zm)
    __arm_streaming;


  // Variants are also available for:
  //   _single_bf16_x4 (only if __ARM_FEATURE_SVE_B16B16 != 0)
  //   _single_f32_x4
  //   _single_f64_x4
  svfloat16x4_t svmaxnm[_single_f16_x4](svfloat16x4_t zdn, svfloat16_t zm)
    __arm_streaming;


  // Variants are also available for:
  //   _single_bf16_x2 (only if __ARM_FEATURE_SVE_B16B16 != 0)
  //   _single_f32_x2
  //   _single_f64_x2
  svfloat16x2_t svminnm[_single_f16_x2](svfloat16x2_t zdn, svfloat16_t zm)
    __arm_streaming;


  // Variants are also available for:
  //   _single_bf16_x4 (only if __ARM_FEATURE_SVE_B16B16 != 0)
  //   _single_f32_x4
  //   _single_f64_x4
  svfloat16x4_t svminnm[_single_f16_x4](svfloat16x4_t zdn, svfloat16_t zm)
    __arm_streaming;
  ```

#### BFMAXNM, BFMINNM, FMAXNM, FMINNM (multi)

Multi-vector floating point min/max number

``` c
  // Variants are also available for:
  //   _bf16_x2 (only if __ARM_FEATURE_SVE_B16B16 != 0)
  //   _f32_x2
  //   _f64_x2
  svfloat16x2_t svmaxnm[_f16_x2](svfloat16x2_t zdn, svfloat16x2_t zm)
    __arm_streaming;


  // Variants are also available for:
  //   _bf16_x4 (only if __ARM_FEATURE_SVE_B16B16 != 0)
  //   _f32_x4
  //   _f64_x4
  svfloat16x4_t svmaxnm[_f16_x4](svfloat16x4_t zdn, svfloat16x4_t zm)
    __arm_streaming;


  // Variants are also available for:
  //   _bf16_x2 (only if __ARM_FEATURE_SVE_B16B16 != 0)
  //   _f32_x2
  //   _f64_x2
  svfloat16x2_t svminnm[_f16_x2](svfloat16x2_t zdn, svfloat16x2_t zm)
    __arm_streaming;


  // Variants are also available for:
  //   _bf16_x4 (only if __ARM_FEATURE_SVE_B16B16 != 0)
  //   _f32_x4
  //   _f64_x4
  svfloat16x4_t svminnm[_f16_x4](svfloat16x4_t zdn, svfloat16x4_t zm)
    __arm_streaming;
  ```

#### FRINTA, FRINTM, FRINTN, FRINTP

Multi-vector floating-point round to integral value

``` c
  svfloat32x2_t svrinta[_f32_x2](svfloat32x2_t zn) __arm_streaming;


  svfloat32x4_t svrinta[_f32_x4](svfloat32x4_t zn) __arm_streaming;


  svfloat32x2_t svrintm[_f32_x2](svfloat32x2_t zn) __arm_streaming;


  svfloat32x4_t svrintm[_f32_x4](svfloat32x4_t zn) __arm_streaming;


  svfloat32x2_t svrintn[_f32_x2](svfloat32x2_t zn) __arm_streaming;


  svfloat32x4_t svrintn[_f32_x4](svfloat32x4_t zn) __arm_streaming;


  svfloat32x2_t svrintp[_f32_x2](svfloat32x2_t zn) __arm_streaming;


  svfloat32x4_t svrintp[_f32_x4](svfloat32x4_t zn) __arm_streaming;
  ```

#### LDR, STR

Spill and fill of ZT0

``` c
  void svldr_zt(uint64_t zt, const void *rn)
    __arm_streaming_compatible __arm_inout("zt0");


  void svstr_zt(uint64_t zt, void *rn)
    __arm_streaming_compatible __arm_in("zt0");
  ```

#### ZERO

Zero ZT0

``` c
  void svzero_zt(uint64_t zt)
    __arm_streaming_compatible __arm_out("zt0");
  ```

#### LUTI2, LUTI4

Lookup table read with 2-bit and 4-bit indexes

``` c
  // Variants are also available for _zt_u8, _zt_mf8, _zt_s16, _zt_u16, _zt_f16,
  // _zt_bf16, _zt_s32, _zt_u32 and _zt_f32
  svint8_t svluti2_lane_zt_s8(uint64_t zt, svuint8_t zn, uint64_t imm_idx)
    __arm_streaming __arm_in("zt0");


  // Variants are also available for _zt_u8, _zt_mf8, _zt_s16, _zt_u16, _zt_f16,
  // _zt_bf16, _zt_s32, _zt_u32 and _zt_f32
  svint8x2_t svluti2_lane_zt_s8_x2(uint64_t zt, svuint8_t zn,
                                   uint64_t imm_idx)
    __arm_streaming __arm_in("zt0");


  // Variants are also available for _zt_u8, _zt_mf8, _zt_s16, _zt_u16, _zt_f16,
  // _zt_bf16, _zt_s32, _zt_u32 and _zt_f32
  svint8x4_t svluti2_lane_zt_s8_x4(uint64_t zt, svuint8_t zn,
                                   uint64_t imm_idx)
    __arm_streaming __arm_in("zt0");


  // Variants are also available for _zt_u8, _zt_mf8, _zt_s16, _zt_u16, _zt_f16,
  // _zt_bf16, _zt_s32, _zt_u32 and _zt_f32
  svint8_t svluti4_lane_zt_s8(uint64_t zt, svuint8_t zn, uint64_t imm_idx)
    __arm_streaming __arm_in("zt0");


  // Variants are also available for _zt_u8, _zt_mf8, _zt_s16, _zt_u16, _zt_f16,
  // _zt_bf16, _zt_s32, _zt_u32 and _zt_f32
  svint8x2_t svluti4_lane_zt_s8_x2(uint64_t zt, svuint8_t zn,
                                   uint64_t imm_idx)
    __arm_streaming __arm_in("zt0");


  // Variants are also available for _zt_u16, _zt_f16, _zt_bf16, _zt_s32,
  // _zt_u32 and _zt_f32
  svint16x4_t svluti4_lane_zt_s16_x4(uint64_t zt, svuint8_t zn,
                                     uint64_t imm_idx)
    __arm_streaming __arm_in("zt0");
  ```

#### MOVA

Move multi-vectors to/from ZA

``` c
  // Variants are also available for _za8_u8, _za8_mf8,
  // _za16_s16, _za16_u16, _za16_f16, _za16_bf16,
  // _za32_s32, _za32_u32, _za32_f32,
  // _za64_s64, _za64_u64 and _za64_f64
  svint8x2_t svread_hor_za8_s8_vg2(uint64_t tile, uint32_t slice)
    __arm_streaming __arm_in("za");


  // Variants are also available for _za8_u8, _za8_mf8,
  // _za16_s16, _za16_u16, _za16_f16, _za16_bf16,
  // _za32_s32, _za32_u32, _za32_f32,
  // _za64_s64, _za64_u64 and _za64_f64
  svint8x4_t svread_hor_za8_s8_vg4(uint64_t tile, uint32_t slice)
    __arm_streaming __arm_in("za");


  // Variants are also available for _za8_u8, _za8_mf8,
  // _za16_s16, _za16_u16, _za16_f16, _za16_bf16,
  // _za32_s32, _za32_u32, _za32_f32,
  // _za64_s64, _za64_u64 and _za64_f64
  svint8x2_t svread_ver_za8_s8_vg2(uint64_t tile, uint32_t slice)
    __arm_streaming __arm_in("za");


  // Variants are also available for _za8_u8, _za8_mf8,
  // _za16_s16, _za16_u16, _za16_f16, _za16_bf16,
  // _za32_s32, _za32_u32, _za32_f32,
  // _za64_s64, _za64_u64 and _za64_f64
  svint8x4_t svread_ver_za8_s8_vg4(uint64_t tile, uint32_t slice)
    __arm_streaming __arm_in("za");


  // Variants are also available for _za8_u8, _za8_mf8,
  // _za16_s16, _za16_u16, _za16_f16, _za16_bf16,
  // _za32_s32, _za32_u32, _za32_f32,
  // _za64_s64, _za64_u64 and _za64_f64
  svint8x2_t svread_za8_s8_vg1x2(uint32_t slice)
    __arm_streaming __arm_in("za");


  // Variants are also available for _za8_u8, _za8_mf8,
  // _za16_s16, _za16_u16, _za16_f16, _za16_bf16,
  // _za32_s32, _za32_u32, _za32_f32,
  // _za64_s64, _za64_u64 and _za64_f64
  svint8x4_t svread_za8_s8_vg1x4(uint32_t slice)
    __arm_streaming __arm_in("za");


  // Variants are also available for _za8[_u8], _za8[_mf8],
  // _za16[_s16], _za16[_u16], _za16[_f16], _za16[_bf16],
  // _za32[_s32], _za32[_u32], _za32[_f32],
  // _za64[_s64], _za64[_u64] and _za64[_f64]
  void svwrite_hor_za8[_s8]_vg2(uint64_t tile, uint32_t slice, svint8x2_t zn)
    __arm_streaming __arm_inout("za");


  // Variants are also available for _za8[_u8], _za8[_mf8],
  // _za16[_s16], _za16[_u16], _za16[_f16], _za16[_bf16],
  // _za32[_s32], _za32[_u32], _za32[_f32],
  // _za64[_s64], _za64[_u64] and _za64[_f64]
  void svwrite_hor_za8[_s8]_vg4(uint64_t tile, uint32_t slice, svint8x4_t zn)
    __arm_streaming __arm_inout("za");


  // Variants are also available for _za8[_u8], _za8[_mf8],
  // _za16[_s16], _za16[_u16], _za16[_f16], _za16[_bf16],
  // _za32[_s32], _za32[_u32], _za32[_f32],
  // _za64[_s64], _za64[_u64] and _za64[_f64]
  void svwrite_ver_za8[_s8]_vg2(uint64_t tile, uint32_t slice, svint8x2_t zn)
    __arm_streaming __arm_inout("za");


  // Variants are also available for _za8[_u8], _za8[_mf8],
  // _za16[_s16], _za16[_u16], _za16[_f16], _za16[_bf16],
  // _za32[_s32], _za32[_u32], _za32[_f32],
  // _za64[_s64], _za64[_u64] and _za64[_f64]
  void svwrite_ver_za8[_s8]_vg4(uint64_t tile, uint32_t slice, svint8x4_t zn)
    __arm_streaming __arm_inout("za");


  // Variants are also available for _za8[_u8], _za8[_mf8],
  // _za16[_s16], _za16[_u16], _za16[_f16], _za16[_bf16],
  // _za32[_s32], _za32[_u32], _za32[_f32],
  // _za64[_s64], _za64[_u64] and _za64[_f64]
  void svwrite_za8[_s8]_vg1x2(uint32_t slice, svint8x2_t zn)
    __arm_streaming __arm_inout("za");


  // Variants are also available for _za8[_u8], za8[_mf8],
  // _za16[_s16], _za16[_u16], _za16[_f16], _za16[_bf16],
  // _za32[_s32], _za32[_u32], _za32[_f32],
  // _za64[_s64], _za64[_u64] and _za64[_f64]
  void svwrite_za8[_s8]_vg1x4(uint32_t slice, svint8x4_t zn)
    __arm_streaming __arm_inout("za");
  ```

#### UCLAMP, SCLAMP, BFCLAMP, FCLAMP

Multi-vector clamp to minimum/maximum vector

``` c
  // Variants are also available for:
  //   _single_s8_x2
  //   _single_u8_x2,
  //   _single_bf16_x2 (only if __ARM_FEATURE_SVE_B16B16 != 0)
  //   _single_s16_x2
  //   _single_u16_x2
  //   _single_s32_x2
  //   _single_u32_x2,
  //   _single_f32_x2
  //   _single_s64_x2
  //   _single_u64_x2
  //   _single_f64_x2
  svfloat16x2_t svclamp[_single_f16_x2](svfloat16x2_t zd, svfloat16_t zn,
                                        svfloat16_t zm)
    __arm_streaming;


  // Variants are also available for:
  //   _single_s8_x4
  //   _single_u8_x4,
  //   _single_bf16_x4 (only if __ARM_FEATURE_SVE_B16B16 != 0)
  //   _single_s16_x4
  //   _single_u16_x4
  //   _single_s32_x4
  //   _single_u32_x4,
  //   _single_f32_x4
  //   _single_s64_x4
  //   _single_u64_x4
  //   _single_f64_x4
  svfloat16x4_t svclamp[_single_f16_x4](svfloat16x4_t zd, svfloat16_t zn,
                                        svfloat16_t zm)
    __arm_streaming;
  ```


#### SEL

Multi-vector conditionally select elements from two vectors

``` c
  // Variants are also available for _s8_x2, _mf8_x2, _u16_x2, _s16_x2, _f16_x2,
  // _bf16_x2, _u32_x2, _s32_x2, _f32_x2, _u64_x2, _s64_x2 and _f64_x2
  svuint8x2_t svsel[_u8_x2](svcount_t png, svuint8x2_t zn, svuint8x2_t zm)
    __arm_streaming;


  // Variants are also available for _s8_x4, _mf8_x4, _u16_x4, _s16_x4, _f16_x4,
  // _bf16_x4, _u32_x4, _s32_x4, _f32_x4, _u64_x4, _s64_x4 and _f64_x4
  svuint8x4_t svsel[_u8_x4](svcount_t png, svuint8x4_t zn, svuint8x4_t zm)
    __arm_streaming;
  ```

#### URSHL, SRSHL (single)

Multi-vector rounding shift left

``` c
  // Variants are also available for _single_u8_x2, _single_u16_x2,
  // _single_s16_x2, _single_u32_x2, _single_s32_x2, _single_u64_x2
  // and _single_s64_x2
  svint8x2_t svrshl[_single_s8_x2](svint8x2_t zdn, svint8_t zm) __arm_streaming;


  // Variants are also available for _single_u8_x4, _single_u16_x4,
  // _single_s16_x4, _single_u32_x4, _single_s32_x4, _single_u64_x4
  // and _single_s64_x4
  svint8x4_t svrshl[_single_s8_x4](svint8x4_t zdn, svint8_t zm) __arm_streaming;
  ```

#### URSHL, SRSHL (multi)

Multi-vector rounding shift left

``` c
  // Variants are also available for _u8_x2, _u16_x2, _s16_x2, _u32_x2, _s32_x2,
  // _u64_x2 and _s64_x2
  svint8x2_t svrshl[_s8_x2](svint8x2_t zdn, svint8x2_t zm) __arm_streaming;


  // Variants are also available for _u8_x4, _u16_x4, _s16_x4, _u32_x4, _s32_x4,
  // _u64_x4 and _s64_x4
  svint8x4_t svrshl[_s8_x4](svint8x4_t zdn, svint8x4_t zm) __arm_streaming;
  ```

#### SQRSHR, UQRSHR

Multi-vector saturating rounding shift right narrow

``` c
  // Variants are also available for _u8[_u32_x4]
  svint8_t svqrshr[_n]_s8[_s32_x4](svint32x4_t zn, uint64_t imm)
    __arm_streaming;


  // Variants are also available for _u16[_u32_x2]
  svint16_t svqrshr[_n]_s16[_s32_x2](svint32x2_t zn, uint64_t imm)
    __arm_streaming;


  // Variants are also available for _u16[_u64_x4]
  svint16_t svqrshr[_n]_s16[_s64_x4](svint64x4_t zn, uint64_t imm)
    __arm_streaming;
  ```

#### SQRSHRN, UQRSHRN

Multi-vector saturating rounding shift right narrow and interleave

``` c
  // Variants are also available for _u8[_u32_x4]
  svint8_t svqrshrn[_n]_s8[_s32_x4](svint32x4_t zn, uint64_t imm)
    __arm_streaming;


  // Variants are also available for _u16[_u64_x4]
  svint16_t svqrshrn[_n]_s16[_s64_x4](svint64x4_t zn, uint64_t imm)
    __arm_streaming;
  ```

#### SQRSHRU

Multi-vector saturating rounding shift right unsigned narrow

``` c
  svuint8_t svqrshru[_n]_u8[_s32_x4](svint32x4_t zn, uint64_t imm)
    __arm_streaming;


  svuint16_t svqrshru[_n]_u16[_s32_x2](svint32x2_t zn, uint64_t imm)
    __arm_streaming;


  svuint16_t svqrshru[_n]_u16[_s64_x4](svint64x4_t zn, uint64_t imm)
    __arm_streaming;
  ```

#### SQRSHRUN

Multi-vector saturating rounding shift right unsigned narrow and interleave

``` c
  // Variants are also available for _u16[_s64_x4]
  svuint8_t svqrshrun[_n]_u8[_s32_x4](svint32x4_t zn, uint64_t imm)
    __arm_streaming;
  ```

#### SQDMULH (single)

Multi-vector signed saturating doubling multiply high

``` c
  // Variants are also available for _single_s16_x2, _single_s32_x2
  // and _single_s64_x2
  svint8x2_t svqdmulh[_single_s8_x2](svint8x2_t zdn, svint8_t zm)
    __arm_streaming;


  // Variants are also available for _single_s16_x4, _single_s32_x4
  // and _single_s64_x4
  svint8x4_t svqdmulh[_single_s8_x4](svint8x4_t zdn, svint8_t zm)
    __arm_streaming;
  ```

#### SQDMULH (multi)

Multi-vector signed saturating doubling multiply high

``` c
  // Variants are also available for _s16_x2, _s32_x2 and _s64_x2
  svint8x2_t svqdmulh[_s8_x2](svint8x2_t zdn, svint8x2_t zm) __arm_streaming;


  // Variants are also available for _s16_x4, _s32_x4 and _s64_x4
  svint8x4_t svqdmulh[_s8_x4](svint8x4_t zdn, svint8x4_t zm) __arm_streaming;
  ```

#### SUNPK, UUNPK

Multi-vector pack/unpack

``` c
  // Variants are also available for _u16[_u8_x2], _u32[_u16_x2], _s32[_s16_x2],
  // _u64[_u32_x2] and _s64[_s32_x2]
  svint16x2_t svunpk_s16[_s8_x2](svint8_t zn) __arm_streaming;


  // Variants are also available for _u16[_u8_x4], _u32[_u16_x4], _s32[_s16_x4],
  // _u64[_u32_x4] and _s64[_s32_x4]
  svint16x4_t svunpk_s16[_s8_x4](svint8x2_t zn) __arm_streaming;
  ```

#### ZIP

Multi-vector zip.

``` c
  // Variants are also available for _u8_x2, _mf8_x2, _u16_x2, _s16_x2, _f16_x2,
  // _bf16_x2, _u32_x2, _s32_x2, _f32_x2, _u64_x2, _s64_x2 and _f64_x2
  svint8x2_t svzip[_s8_x2](svint8x2_t zn) __arm_streaming;


  // Variants are also available for _u8_x4, _mf8_x4, _u16_x4, _s16_x4, _f16_x4,
  // _bf16_x4, _u32_x4, _s32_x4, _f32_x4, _u64_x4, _s64_x4 and _f64_x4
  svint8x4_t svzip[_s8_x4](svint8x4_t zn) __arm_streaming;
  ```

The `svzipq` intrinsics operate on quad-words, but for convenience accept all
element types.


``` c
  // Variants are also available for _u8_x2, _mf8_x2, _u16_x2, _s16_x2, _f16_x2,
  // _bf16_x2, _u32_x2, _s32_x2, _f32_x2, _u64_x2, _s64_x2 and _f64_x2
  svint8x2_t svzipq[_s8_x2](svint8x2_t zn) __arm_streaming;


  // Variants are also available for _u8_x4, _mf8_x4, _u16_x4, _s16_x4, _f16_x4,
  // _bf16_x4, _u32_x4, _s32_x4, _f32_x4, _u64_x4, _s64_x4 and _f64_x4
  svint8x4_t svzipq[_s8_x4](svint8x4_t zn) __arm_streaming;
  ```

#### UZP

Multi-vector unzip.

``` c
  // Variants are also available for _u8_x2, _mf8_x2, _u16_x2, _s16_x2, _f16_x2,
  // _bf16_x2, _u32_x2, _s32_x2, _f32_x2, _u64_x2, _s64_x2 and _f64_x2
  svint8x2_t svuzp[_s8_x2](svint8x2_t zn) __arm_streaming;


  // Variants are also available for _u8_x4, _mf8_x4, _u16_x4, _s16_x4, _f16_x4,
  // _bf16_x4, _u32_x4, _s32_x4, _f32_x4, _u64_x4, _s64_x4 and _f64_x4
  svint8x4_t svuzp[_s8_x4](svint8x4_t zn) __arm_streaming;
  ```

The `svuzpq` intrinsics operate on quad-words, but for convenience accept all
element types.

``` c
  // Variants are also available for _u8_x2, _mf8_x2, _u16_x2, _s16_x2, _f16_x2,
  // _bf16_x2, _u32_x2, _s32_x2, _f32_x2, _u64_x2, _s64_x2 and _f64_x2
  svint8x2_t svuzpq[_s8_x2](svint8x2_t zn) __arm_streaming;


  // Variants are also available for _u8_x4, _mf8_x4, _u16_x4, _s16_x4, _f16_x4,
  // _bf16_x4, _u32_x4, _s32_x4, _f32_x4, _u64_x4, _s64_x4 and _f64_x4
  svint8x4_t svuzpq[_s8_x4](svint8x4_t zn) __arm_streaming;
  ```

#### BFMUL

BFloat16 Multi-vector floating-point multiply

``` c
  // Only if __ARM_FEATURE_SVE_BFSCALE != 0
   svbfloat16x2_t svmul[_bf16_x2](svbfloat16x2_t zd, svbfloat16x2_t zm) __arm_streaming;
   svbfloat16x2_t svmul[_single_bf16_x2](svbfloat16x2_t zd, svbfloat16_t zm) __arm_streaming;
   svbfloat16x4_t svmul[_bf16_x4](svbfloat16x4_t zd, svbfloat16x4_t zm) __arm_streaming;
   svbfloat16x4_t svmul[_single_bf16_x4](svbfloat16x4_t zd, svbfloat16_t zm) __arm_streaming;
   ```

#### BFSCALE

BFloat16 floating-point adjust exponent vectors.

``` c
  // Only if __ARM_FEATURE_SVE_BFSCALE != 0
   svbfloat16x2_t svscale[_bf16_x2](svbfloat16x2_t zdn, svint16x2_t zm)  __arm_streaming;
   svbfloat16x2_t svscale[_single_bf16_x2](svbfloat16x2_t zn, svint16_t zm)  __arm_streaming;
   svbfloat16x4_t svscale[_bf16_x4](svbfloat16x4_t zdn, svint16x4_t zm)  __arm_streaming;
   svbfloat16x4_t svscale[_single_bf16_x4](svbfloat16x4_t zn, svint16_t zm)  __arm_streaming;
   ```

### SME2.1 instruction intrinsics

The specification for SME2.1 is in
[**Beta** state](#support-levels) and might change or
be extended in the future.

The intrinsics in this section are available when `__ARM_FEATURE_SME2p1`
is defined.

#### MOVAZ (tile to vector, single)

Move and zero ZA tile slice to vector register.

```
  // And similarly for u8 and mf8.
  svint8_t svreadz_hor_za8_s8(uint64_t tile, uint32_t slice)
    __arm_streaming __arm_inout("za");

  // And similarly for u16, bf16 and f16.
  svint16_t svreadz_hor_za16_s16(uint64_t tile, uint32_t slice)
    __arm_streaming __arm_inout("za");

  // And similarly for u32 and f32.
  svint32_t svreadz_hor_za32_s32(uint64_t tile, uint32_t slice)
    __arm_streaming __arm_inout("za");

  // And similarly for u64 and f64.
  svint64_t svreadz_hor_za64_s64(uint64_t tile, uint32_t slice)
    __arm_streaming __arm_inout("za");

  // And similarly for s16, s32, s64, u8, u16, u32, u64,
  // mf8, bf16, f16, f32, f64
  svint8_t svreadz_hor_za128_s8(uint64_t tile, uint32_t slice)
    __arm_streaming __arm_inout("za");

  // And similarly for u8 and mf8.
  svint8_t svreadz_ver_za8_s8(uint64_t tile, uint32_t slice)
    __arm_streaming __arm_inout("za");

  // And similarly for u16, bf16 and f16.
  svint16_t svreadz_ver_za16_s16(uint64_t tile, uint32_t slice)
    __arm_streaming __arm_inout("za");

  // And similarly for u32 and f32.
  svint32_t svreadz_ver_za32_s32(uint64_t tile, uint32_t slice)
    __arm_streaming __arm_inout("za");

  // And similarly for u64 and f64.
  svint64_t svreadz_ver_za64_s64(uint64_t tile, uint32_t slice)
    __arm_streaming __arm_inout("za");

  // And similarly for s16, s32, s64, u8, u16, u32, u64,
  // mf8, bf16, f16, f32, f64
  svint8_t svreadz_ver_za128_s8(uint64_t tile, uint32_t slice)
    __arm_streaming __arm_inout("za");
```

#### MOVAZ (tile to vector, multiple)

Move and zero multiple ZA tile slices to vector registers

``` c
  // Variants are also available for _za8_u8, _za8_mf8,
  // _za16_s16, _za16_u16, _za16_f16, _za16_bf16,
  // _za32_s32, _za32_u32, _za32_f32,
  // _za64_s64, _za64_u64 and _za64_f64
  svint8x2_t svreadz_hor_za8_s8_vg2(uint64_t tile, uint32_t slice)
    __arm_streaming __arm_inout("za");


  // Variants are also available for _za8_u8, _za8_mf8,
  // _za16_s16, _za16_u16, _za16_f16, _za16_bf16,
  // _za32_s32, _za32_u32, _za32_f32,
  // _za64_s64, _za64_u64 and _za64_f64
  svint8x4_t svreadz_hor_za8_s8_vg4(uint64_t tile, uint32_t slice)
    __arm_streaming __arm_inout("za");


  // Variants are also available for _za8_u8, _za8_mf8,
  // _za16_s16, _za16_u16, _za16_f16, _za16_bf16,
  // _za32_s32, _za32_u32, _za32_f32,
  // _za64_s64, _za64_u64 and _za64_f64
  svint8x2_t svreadz_ver_za8_s8_vg2(uint64_t tile, uint32_t slice)
    __arm_streaming __arm_inout("za");


  // Variants are also available for _za8_u8, _za8_mf8,
  // _za16_s16, _za16_u16, _za16_f16, _za16_bf16,
  // _za32_s32, _za32_u32, _za32_f32,
  // _za64_s64, _za64_u64 and _za64_f64
  svint8x4_t svreadz_ver_za8_s8_vg4(uint64_t tile, uint32_t slice)
    __arm_streaming __arm_inout("za");
```

#### MOVAZ (array to vector)

Move and zero multiple ZA single-vector groups to vector registers

```
  // Variants are also available for _za8_u8, _za8_mf8,
  // _za16_s16, _za16_u16, _za16_f16, _za16_bf16,
  // _za32_s32, _za32_u32, _za32_f32,
  // _za64_s64, _za64_u64 and _za64_f64
  svint8x2_t svreadz_za8_s8_vg1x2(uint32_t slice)
    __arm_streaming __arm_inout("za");


  // Variants are also available for _za8_u8, _za8_mf8,
  // _za16_s16, _za16_u16, _za16_f16, _za16_bf16,
  // _za32_s32, _za32_u32, _za32_f32,
  // _za64_s64, _za64_u64 and _za64_f64
  svint8x4_t svreadz_za8_s8_vg1x4(uint32_t slice)
    __arm_streaming __arm_inout("za");
```

#### ZERO (vector groups)

Zero ZA vector groups

```
  void svzero_za64_vg1x2(uint32_t slice)
    __arm_streaming __arm_inout("za");

  void svzero_za64_vg1x4(uint32_t slice)
    __arm_streaming __arm_inout("za");

  void svzero_za64_vg2x1(uint32_t slice)
    __arm_streaming __arm_inout("za");

  void svzero_za64_vg2x2(uint32_t slice)
    __arm_streaming __arm_inout("za");

  void svzero_za64_vg2x4(uint32_t slice)
    __arm_streaming __arm_inout("za");

  void svzero_za64_vg4x1(uint32_t slice)
    __arm_streaming __arm_inout("za");

  void svzero_za64_vg4x2(uint32_t slice)
    __arm_streaming __arm_inout("za");

  void svzero_za64_vg4x4(uint32_t slice)
    __arm_streaming __arm_inout("za");
```

### SME2.2 instruction intrinsics

The specification for SME2.2 are in
[**Beta** state](#support-levels) and might change or be
extended in the future.

The intrinsics in this section are available when `__ARM_FEATURE_SME2p2`
is defined.

#### FMUL

Multi-vector floating-point multiply

``` c
  // Variants are also available for:
  // [_single_f32_x2]
  // [_single_f64_x2]
  svfloat16x2_t svmul[_single_f16_x2](svfloat16x2_t zd, svfloat16_t zm) __arm_streaming;

  // Variants are also available for:
  // [_single_f32_x4]
  // [_single_f64_x4]
  svfloat16x4_t svmul[_single_f16_x4](svfloat16x4_t zd, svfloat16_t zm) __arm_streaming;

  // Variants are also available for:
  // [_f32_x2]
  // [_f64_x2]
  svfloat16x2_t svmul[_f16_x2](svfloat16x2_t zd, svfloat16x2_t zm) __arm_streaming;

  // Variants are also available for:
  // [_f32_x4]
  // [_f64_x4]
  svfloat16x4_t svmul[_f16_x4](svfloat16x4_t zd, svfloat16x4_t zm) __arm_streaming;
```

### Streaming-compatible versions of standard routines

ACLE provides the following streaming-compatible functions,
with the same behavior as the standard C functions that they
are named after. All of the functions have external linkage.

``` c
  void *__arm_sc_memcpy(void *dest, const void *src, size_t n)
    __arm_streaming_compatible;

  void *__arm_sc_memmove(void *dest, const void *src, size_t n)
    __arm_streaming_compatible;

  void *__arm_sc_memset(void *s, int c, size_t n)
    __arm_streaming_compatible;

  void *__arm_sc_memchr(void *s, int c, size_t n)
    __arm_streaming_compatible;
```

### SVE2.1 and SME2 instruction intrinsics

The specification for SVE2.1 is in
[**Beta** state](#support-levels) and might change or be
extended in the future.

The functions in this section are available when `__ARM_FEATURE_SVE2p1`
or `__ARM_FEATURE_SME2` is defined.

These intrinsics can only be called from non-streaming code if
`__ARM_FEATURE_SVE2p1` is defined. They can only be called from streaming code
if the appropriate SME feature macro is defined (see previous paragraph).
They can only be called from streaming-compatible code if they could be called
from both non-streaming code and streaming code

Most functions in this section are SME2 or SVE2.1. However some are available in
SME. For convenience the ones available in SME will be tagged in the function
with `[SME]`.

#### UCLAMP, SCLAMP, FCLAMP

Clamp to minimum/maximum vector.

``` c
  // Variants are also available for:
  //  _s8, _u8, _s16, _u16, _s32, _u32  [SME]
  // _f32, _s64, _u64 and _f64
  svfloat16_t svclamp[_f16](svfloat16_t op, svfloat16_t min, svfloat16_t max);
  ```

#### CNTP

Set scalar to count from predicate-as-counter. ``vl`` is expected to be 2 or 4.

``` c
  // Variants are also available for _c16, _c32 and _c64
  uint64_t svcntp_c8(svcount_t pnn, uint64_t vl);
  ```

#### UDOT, SDOT, FDOT (vectors)

Multi-vector dot-product (2-way)

``` c
  // Variants are also available for _s32_s16, _u32_u16
  // and also for _s16_s8 and _u16_u8 if (__ARM_FEATURE_SVE2p3 || __ARM_FEATURE_SME2p3).
  svfloat32_t svdot[_f32_f16](svfloat32_t zda, svfloat16_t zn,
                              svfloat16_t zm);
  svfloat32_t svdot[_n_f32_f16](svfloat32_t zda, svfloat16_t zn,
                                float16_t zm);
  ```

#### UDOT, SDOT, FDOT (indexed)

Multi-vector dot-product (2-way)

``` c
  // Variants are also available for _s32_s16, _u32_u16
  // and also for _s16_s8 and _u16_u8  if (__ARM_FEATURE_SVE2p3 || __ARM_FEATURE_SME2p3).
  svfloat32_t svdot_lane[_f32_f16](svfloat32_t zda, svfloat16_t zn,
                                   svfloat16_t zm, uint64_t imm_idx);
  ```

#### LD1B, LD1D, LD1H, LD1W

Contiguous load to multi-vector

``` c
  // Variants are also available for _s8, _mf8
  svuint8x2_t svld1[_u8]_x2(svcount_t png, const uint8_t *rn);


  // Variants are also available for _s8, _mf8
  svuint8x4_t svld1[_u8]_x4(svcount_t png, const uint8_t *rn);


  // Variants are also available for _s8, _mf8
  svuint8x2_t svld1_vnum[_u8]_x2(svcount_t png, const uint8_t *rn,
                                 int64_t vnum);


  // Variants are also available for _s8, _mf8
  svuint8x4_t svld1_vnum[_u8]_x4(svcount_t png, const uint8_t *rn,
                                 int64_t vnum);


  // Variants are also available for _s16, _f16 and _bf16
  svuint16x2_t svld1[_u16]_x2(svcount_t png, const uint16_t *rn);


  // Variants are also available for _s16, _f16 and _bf16
  svuint16x4_t svld1[_u16]_x4(svcount_t png, const uint16_t *rn);


  // Variants are also available for _s16, _f16 and _bf16
  svuint16x2_t svld1_vnum[_u16]_x2(svcount_t png, const uint16_t *rn,
                                   int64_t vnum);


  // Variants are also available for _s16, _f16 and _bf16
  svuint16x4_t svld1_vnum[_u16]_x4(svcount_t png, const uint16_t *rn,
                                   int64_t vnum);


  // Variants are also available for _s32 and _f32
  svuint32x2_t svld1[_u32]_x2(svcount_t png, const uint32_t *rn);


  // Variants are also available for _s32 and _f32
  svuint32x4_t svld1[_u32]_x4(svcount_t png, const uint32_t *rn);


  // Variants are also available for _s32 and _f32
  svuint32x2_t svld1_vnum[_u32]_x2(svcount_t png, const uint32_t *rn,
                                   int64_t vnum);


  // Variants are also available for _s32 and _f32
  svuint32x4_t svld1_vnum[_u32]_x4(svcount_t png, const uint32_t *rn,
                                   int64_t vnum);


  // Variants are also available for _s64 and _f64
  svuint64x2_t svld1[_u64]_x2(svcount_t png, const uint64_t *rn);


  // Variants are also available for _s64 and _f64
  svuint64x4_t svld1[_u64]_x4(svcount_t png, const uint64_t *rn);


  // Variants are also available for _s64 and _f64
  svuint64x2_t svld1_vnum[_u64]_x2(svcount_t png, const uint64_t *rn,
                                   int64_t vnum);


  // Variants are also available for _s64 and _f64
  svuint64x4_t svld1_vnum[_u64]_x4(svcount_t png, const uint64_t *rn,
                                   int64_t vnum);
  ```

#### LDNT1B, LDNT1D, LDNT1H, LDNT1W

Contiguous non-temporal load to multi-vector

``` c
  // Variants are also available for _s8, _mf8
  svuint8x2_t svldnt1[_u8]_x2(svcount_t png, const uint8_t *rn);


  // Variants are also available for _s8, _mf8
  svuint8x4_t svldnt1[_u8]_x4(svcount_t png, const uint8_t *rn);


  // Variants are also available for _s8, _mf8
  svuint8x2_t svldnt1_vnum[_u8]_x2(svcount_t png, const uint8_t *rn,
                                   int64_t vnum);


  // Variants are also available for _s8, _mf8
  svuint8x4_t svldnt1_vnum[_u8]_x4(svcount_t png, const uint8_t *rn,
                                   int64_t vnum);


  // Variants are also available for _s16, _f16 and _bf16
  svuint16x2_t svldnt1[_u16]_x2(svcount_t png, const uint16_t *rn);


  // Variants are also available for _s16, _f16 and _bf16
  svuint16x4_t svldnt1[_u16]_x4(svcount_t png, const uint16_t *rn);


  // Variants are also available for _s16, _f16 and _bf16
  svuint16x2_t svldnt1_vnum[_u16]_x2(svcount_t png, const uint16_t *rn,
                                     int64_t vnum);


  // Variants are also available for _s16, _f16 and _bf16
  svuint16x4_t svldnt1_vnum[_u16]_x4(svcount_t png, const uint16_t *rn,
                                     int64_t vnum);


  // Variants are also available for _s32 and _f32
  svuint32x2_t svldnt1[_u32]_x2(svcount_t png, const uint32_t *rn);


  // Variants are also available for _s32 and _f32
  svuint32x4_t svldnt1[_u32]_x4(svcount_t png, const uint32_t *rn);


  // Variants are also available for _s32 and _f32
  svuint32x2_t svldnt1_vnum[_u32]_x2(svcount_t png, const uint32_t *rn,
                                     int64_t vnum);


  // Variants are also available for _s32 and _f32
  svuint32x4_t svldnt1_vnum[_u32]_x4(svcount_t png, const uint32_t *rn,
                                     int64_t vnum);


  // Variants are also available for _s64 and _f64
  svuint64x2_t svldnt1[_u64]_x2(svcount_t png, const uint64_t *rn);


  // Variants are also available for _s64 and _f64
  svuint64x4_t svldnt1[_u64]_x4(svcount_t png, const uint64_t *rn);


  // Variants are also available for _s64 and _f64
  svuint64x2_t svldnt1_vnum[_u64]_x2(svcount_t png, const uint64_t *rn,
                                     int64_t vnum);


  // Variants are also available for _s64 and _f64
  svuint64x4_t svldnt1_vnum[_u64]_x4(svcount_t png, const uint64_t *rn,
                                     int64_t vnum);
  ```

#### BFMLSLB, BFMLSLT

BFloat16 floating-point multiply-subtract long from single-precision (top/bottom)

``` c
  svfloat32_t svbfmlslb[_f32](svfloat32_t zda, svbfloat16_t zn, svbfloat16_t zm);


  svfloat32_t svbfmlslb_lane[_f32](svfloat32_t zda, svbfloat16_t zn,
                                   svbfloat16_t zm, uint64_t imm_idx);


  svfloat32_t svbfmlslt[_f32](svfloat32_t zda, svbfloat16_t zn, svbfloat16_t zm);


  svfloat32_t svbfmlslt_lane[_f32](svfloat32_t zda, svbfloat16_t zn,
                                   svbfloat16_t zm, uint64_t imm_idx);
  ```

#### PEXT

Transform a predicate-as-counter to a predicate (pair).

``` c
  // Variants are also available for _c16, _c32 and _c64
  svbool_t svpext_lane_c8(svcount_t pnn, uint64_t imm);


  // Variants are also available for _c16, _c32 and _c64
  svboolx2_t svpext_lane_c8_x2(svcount_t pnn, uint64_t imm);
  ```

#### PSEL

Predicate select between predicate value or all-false

``` c
   // Variants are also available for _b16, _b32 and _b64 [SME]
   svbool_t svpsel_lane_b8(svbool_t pn, svbool_t pm, uint32_t idx);


  // Variants are also available for _c16, _c32 and _c64
  svcount_t svpsel_lane_c8(svcount_t pn, svbool_t pm, uint32_t idx);
  ```

#### PTRUE, PFALSE

Initialize predicate-as-counter to all active or all inactive.

``` c
  // Variants are also available for _c16, _c32 and _c64
  svcount_t svptrue_c8();


  svcount_t svpfalse_c(void);
```

#### REVD

Reverse doublewords in elements.

``` c
  // All the intrinsics below are [SME]
  // Variants are available for:
  // _s8, _s16, _u16, _s32, _u32, _s64, _u64
  // _mf8, _bf16, _f16, _f32, _f64
  svuint8_t svrevd[_u8]_m(svuint8_t zd, svbool_t pg, svuint8_t zn);


  // Variants are available for:
  // _s8, _s16, _u16, _s32, _u32, _s64, _u64
  // _mf8, _bf16, _f16, _f32, _f64
  svuint8_t svrevd[_u8]_z(svbool_t pg, svuint8_t zn);


  // Variants are available for:
  // _s8, _s16, _u16, _s32, _u32, _s64, _u64
  // _mf8, _bf16, _f16, _f32, _f64
  svuint8_t svrevd[_u8]_x(svbool_t pg, svuint8_t zn);
  ```

#### SQCVTN, SQCVTUN, UQCVTN

Multi-vector saturating extract narrow and interleave

``` c
  // Variants are also available for _u16[_s32_x2] and _u16[_u32_x2]
  svint16_t svqcvtn_s16[_s32_x2](svint32x2_t zn);
  ```

#### SQRSHRN, UQRSHRN

Multi-vector saturating rounding shift right narrow and interleave

``` c
  // Variants are also available for _u16[_u32_x2]
  // and also _s8[_s16_x2] and _u8[_u16_x2] if __ARM_FEATURE_SVE2p3 || __ARM_FEATURE_SME2p3.
  svint16_t svqrshrn[_n]_s16[_s32_x2](svint32x2_t zn, uint64_t imm);
  ```

#### SQRSHRUN

Multi-vector saturating rounding shift right unsigned narrow and interleave

``` c
  // Variant for _u8[_s16_x2] is available if __ARM_FEATURE_SVE2p3 || __ARM_FEATURE_SME2p3.
  svuint16_t svqrshrun[_n]_u16[_s32_x2](svint32x2_t zn, uint64_t imm);
  ```

#### ST1B, ST1D, ST1H, ST1W

Contiguous store of multi-vector operand

``` c
  // Variants are also available for _s8_x2, _mf8_x2
  void svst1[_u8_x2](svcount_t png, uint8_t *rn, svuint8x2_t zt);


  // Variants are also available for _s8_x4, _mf8_x4
  void svst1[_u8_x4](svcount_t png, uint8_t *rn, svuint8x4_t zt);


  // Variants are also available for _s8_x2, _mf8_x2
  void svst1_vnum[_u8_x2](svcount_t png, uint8_t *rn, int64_t vnum,
                          svuint8x2_t zt);


  // Variants are also available for _s8_x4, _mf8_x4
  void svst1_vnum[_u8_x4](svcount_t png, uint8_t *rn, int64_t vnum,
                          svuint8x4_t zt);


  // Variants are also available for _s16_x2, _f16_x2 and _bf16_x2
  void svst1[_u16_x2](svcount_t png, uint16_t *rn, svuint16x2_t zt);


  // Variants are also available for _s16_x4, _f16_x4 and _bf16_x4
  void svst1[_u16_x4](svcount_t png, uint16_t *rn, svuint16x4_t zt);


  // Variants are also available for _s16_x2, _f16_x2 and _bf16_x2
  void svst1_vnum[_u16_x2](svcount_t png, uint16_t *rn, int64_t vnum,
                           svuint16x2_t zt);


  // Variants are also available for _s16_x4, _f16_x4 and _bf16_x4
  void svst1_vnum[_u16_x4](svcount_t png, uint16_t *rn, int64_t vnum,
                           svuint16x4_t zt);


  // Variants are also available for _s32_x2 and _f32_x2
  void svst1[_u32_x2](svcount_t png, uint32_t *rn, svuint32x2_t zt);


  // Variants are also available for _s32_x4 and _f32_x4
  void svst1[_u32_x4](svcount_t png, uint32_t *rn, svuint32x4_t zt);


  // Variants are also available for _s32_x2 and _f32_x2
  void svst1_vnum[_u32_x2](svcount_t png, uint32_t *rn, int64_t vnum,
                           svuint32x2_t zt);


  // Variants are also available for _s32_x4 and _f32_x4
  void svst1_vnum[_u32_x4](svcount_t png, uint32_t *rn, int64_t vnum,
                           svuint32x4_t zt);


 // Variants are also available for _s64_x2 and _f64_x2
  void svst1[_u64_x2](svcount_t png, uint64_t *rn, svuint64x2_t zt);


  // Variants are also available for _s64_x4 and _f64_x4
  void svst1[_u64_x4](svcount_t png, uint64_t *rn, svuint64x4_t zt);


  // Variants are also available for _s64_x2 and _f64_x2
  void svst1_vnum[_u64_x2](svcount_t png, uint64_t *rn, int64_t vnum,
                           svuint64x2_t zt);


  // Variants are also available for _s64_x4 and _f64_x4
  void svst1_vnum[_u64_x4](svcount_t png, uint64_t *rn, int64_t vnum,
                           svuint64x4_t zt);
  ```

#### STNT1B, STNT1D, STNT1H, STNT1W

Contiguous non-temporal store of multi-vector operand

``` c
  // Variants are also available for _s8_x2, _mf8_x2
  void svstnt1[_u8_x2](svcount_t png, uint8_t *rn, svuint8x2_t zt);


  // Variants are also available for _s8_x4, _mf8_x4
  void svstnt1[_u8_x4](svcount_t png, uint8_t *rn, svuint8x4_t zt);


  // Variants are also available for _s8_x2, _mf8_x2
  void svstnt1_vnum[_u8_x2](svcount_t png, uint8_t *rn, int64_t vnum,
                            svuint8x2_t zt);


  // Variants are also available for _s8_x4, _mf8_x4
  void svstnt1_vnum[_u8_x4](svcount_t png, uint8_t *rn, int64_t vnum,
                            svuint8x4_t zt);


  // Variants are also available for _s16_x2, _f16_x2 and _bf16_x2
  void svstnt1[_u16_x2](svcount_t png, uint16_t *rn, svuint16x2_t zt);


  // Variants are also available for _s16_x4, _f16_x4 and _bf16_x4
  void svstnt1[_u16_x4](svcount_t png, uint16_t *rn, svuint16x4_t zt);


  // Variants are also available for _s16_x2, _f16_x2 and _bf16_x2
  void svstnt1_vnum[_u16_x2](svcount_t png, uint16_t *rn, int64_t vnum,
                             svuint16x2_t zt);


  // Variants are also available for _s16_x4, _f16_x4 and _bf16_x4
  void svstnt1_vnum[_u16_x4](svcount_t png, uint16_t *rn, int64_t vnum,
                             svuint16x4_t zt);


  // Variants are also available for _s32_x2 and _f32_x2
  void svstnt1[_u32_x2](svcount_t png, uint32_t *rn, svuint32x2_t zt);


  // Variants are also available for _s32_x4 and _f32_x4
  void svstnt1[_u32_x4](svcount_t png, uint32_t *rn, svuint32x4_t zt);


  // Variants are also available for _s32_x2 and _f32_x2
  void svstnt1_vnum[_u32_x2](svcount_t png, uint32_t *rn, int64_t vnum,
                             svuint32x2_t zt);


  // Variants are also available for _s32_x4 and _f32_x4
  void svstnt1_vnum[_u32_x4](svcount_t png, uint32_t *rn, int64_t vnum,
                             svuint32x4_t zt);


  // Variants are also available for _s64_x2 and _f64_x2
  void svstnt1[_u64_x2](svcount_t png, uint64_t *rn, svuint64x2_t zt);


  // Variants are also available for _s64_x4 and _f64_x4
  void svstnt1[_u64_x4](svcount_t png, uint64_t *rn, svuint64x4_t zt);


  // Variants are also available for _s64_x2 and _f64_x2
  void svstnt1_vnum[_u64_x2](svcount_t png, uint64_t *rn, int64_t vnum,
                             svuint64x2_t zt);


  // Variants are also available for _s64_x4 and _f64_x4
  void svstnt1_vnum[_u64_x4](svcount_t png, uint64_t *rn, int64_t vnum,
                             svuint64x4_t zt);
  ```

#### WHILEGE, WHILEGT, WHILEHI, WHILEHS, WHILELE, WHILELO, WHILELS, WHILELT

While (resulting in predicate-as-counter). ``vl`` is expected to be 2 or 4.

``` c
  // Variants are also available for _c16[_s64], _c32[_s64] _c64[_s64],
  // _c8[_u64], _c16[_u64], _c32[_u64] and _c64[_u64]
  svcount_t svwhilege_c8[_s64](int64_t rn, int64_t rm, uint64_t vl);


  // Variants are also available for _c16[_s64], _c32[_s64] _c64[_s64],
  // _c8[_u64], _c16[_u64], _c32[_u64] and _c64[_u64]
  svcount_t svwhilegt_c8[_s64](int64_t rn, int64_t rm, uint64_t vl);


  // Variants are also available for _c16[_s64], _c32[_s64] _c64[_s64],
  // _c8[_u64], _c16[_u64], _c32[_u64] and _c64[_u64]
  svcount_t svwhilele_c8[_s64](int64_t rn, int64_t rm, uint64_t vl);


  // Variants are also available for _c16[_s64], _c32[_s64] _c64[_s64],
  // _c8[_u64], _c16[_u64], _c32[_u64] and _c64[_u64]
  svcount_t svwhilelt_c8[_s64](int64_t rn, int64_t rm, uint64_t vl);
  ```

While (resulting in predicate tuple)

``` c
  // Variants are also available for _b16[_s64]_x2, _b32[_s64]_x2,
  // _b64[_s64]_x2, _b8[_u64]_x2, _b16[_u64]_x2, _b32[_u64]_x2 and
  // _b64[_u64]_x2
  svboolx2_t svwhilege_b8[_s64]_x2(int64_t rn, int64_t rm);


  // Variants are also available for _b16[_s64]_x2, _b32[_s64]_x2,
  // _b64[_s64]_x2, _b8[_u64]_x2, _b16[_u64]_x2, _b32[_u64]_x2 and
  // _b64[_u64]_x2
  svboolx2_t svwhilegt_b8[_s64]_x2(int64_t rn, int64_t rm);


  // Variants are also available for _b16[_s64]_x2, _b32[_s64]_x2,
  // _b64[_s64]_x2, _b8[_u64]_x2, _b16[_u64]_x2, _b32[_u64]_x2 and
  // _b64[_u64]_x2
  svboolx2_t svwhilele_b8[_s64]_x2(int64_t rn, int64_t rm);


  // Variants are also available for _b16[_s64]_x2, _b32[_s64]_x2,
  // _b64[_s64]_x2, _b8[_u64]_x2, _b16[_u64]_x2, _b32[_u64]_x2 and
  // _b64[_u64]_x2
  svboolx2_t svwhilelt_b8[_s64]_x2(int64_t rn, int64_t rm);
```

### SVE2.2 and SME2.2 instruction intrinsics

The specification for SVE2.2 and SME2.2 are in
[**Beta** state](#support-levels) and might change or be
extended in the future.

The functions in this section are available when `__ARM_FEATURE_SVE2p2`
or `__ARM_FEATURE_SME2p2` is defined.

#### FCVTXNT, FCVTLT, FCVTNT, BFCVTNT

Zeroing forms of convert instructions.

```c

// Variant is available for _f64_f32
svfloat32_t	svcvtlt_f32[_f16]_z	(svbool_t pg, svfloat16_t op);

// Variants are available for:
// _f32_f64, _bf16_f32
svfloat16_t	svcvtnt_f16[_f32]_z	(svfloat16_t even, svbool_t pg, svfloat32_t op);

svfloat32_t	svcvtxnt_f32[_f64]_z (svfloat32_t even, svbool_t pg, svfloat64_t op);
```

#### FRINT32X, FRINT32Z, FRINT64X, FRINT64Z

Round to integral floating-point values.

```c

// Variant is available for _f64
svfloat32_t svrint32x[_f32]_z(svbool_t pg, svfloat32_t zn);
// Variant is available for _f64
svfloat32_t svrint32x[_f32]_x(svbool_t pg, svfloat32_t zn);
// Variant is available for _f64
svfloat32_t svrint32x[_f32]_m(svfloat32_t inactive, svbool_t pg, svfloat32_t zn);

// Variant is available for _f64
svfloat32_t svrint32z[_f32]_z(svbool_t pg, svfloat32_t zn);
// Variant is available for _f64
svfloat32_t svrint32z[_f32]_x(svbool_t pg, svfloat32_t zn);
// Variant is available for _f64
svfloat32_t svrint32z[_f32]_m(svfloat32_t inactive, svbool_t pg, svfloat32_t zn);

// Variant is available for _f64
svfloat32_t svrint64x[_f32]_z(svbool_t pg, svfloat32_t zn);
// Variant is available for _f64
svfloat32_t svrint64x[_f32]_x(svbool_t pg, svfloat32_t zn);
// Variant is available for _f64
svfloat32_t svrint64x[_f32]_m(svfloat32_t inactive, svbool_t pg, svfloat32_t zn);

// Variant is available for _f64
svfloat32_t svrint64z[_f32]_z(svbool_t pg, svfloat32_t zn);
// Variant is available for _f64
svfloat32_t svrint64z[_f32]_x(svbool_t pg, svfloat32_t zn);
// Variant is available for _f64
svfloat32_t svrint64z[_f32]_m(svfloat32_t inactive, svbool_t pg, svfloat32_t zn);
```

#### COMPACT, EXPAND

Copy active vector elements to/from lower-numbered elements.

``` c
  // Variants are available for:
  // _s8, _s16, _u16, _mf8, _bf16, _f16
  svuint8_t svcompact[_u8](svbool_t pg, svuint8_t zn);

  // Variants are available for:
  // _s8, _s16, _u16, _s32, _u32, _s64, _u64
  // _mf8, _bf16, _f16, _f32, _f64
  svuint8_t svexpand[_u8](svbool_t pg, svuint8_t zn);

  ```

#### FIRSTP, LASTP

Scalar index of first/last true predicate element (predicated).

``` c
  // Variants are available for:
  // _b16, _b32, _b64
  int64_t svfirstp_b8(svbool_t pg, svbool_t pn);

  // Variants are available for:
  // _b16, _b32, _b64
  int64_t svlastp_b8(svbool_t pg, svbool_t pn);

  ```

### SVE2.3 and SME2.3 instruction intrinsics

The specification for SVE2.3 and SME2.3 are in
[**Alpha** state](#support-levels) and might change or be
extended in the future.

The functions in this section are available when `__ARM_FEATURE_SVE2p3`
or `__ARM_FEATURE_SME2p3` is defined.

#### ADDQP

Add pairwise within quadword vector segments.

``` c
  // Variants are also available for _s16, _s32, _s64, _u8, _u16, _u32 and _u64.
  svint8_t svaddqp[_s8](svint8_t zn, svint8_t zm);
  ```

#### ADDSUBP

Add subtract pairwise.

``` c
  // Variants are also available for _s16, _s32, _s64, _u8, _u16, _u32 and _u64.
  svint8_t svaddsubp[_s8](svint8_t zn, svint8_t zm);
  ```

#### LUTI6

Lookup table read with 6-bit indices (16-bit).

Use of this intrinsic if `svcntb() * 8 < 512` results in undefined behavior.

``` c
  // Variants are also available for _u16_x2, _bf16_x2 and _f16_x2.
  svint16_t svluti6_lane[_s16_x2](svint16x2_t table, svuint8_t indices, uint64_t imm_idx);
  ```

#### FCVTZSN, FCVTZUN

Floating-point narrowing convert to interleaved integer, rounding toward zero.

``` c
  // Variants are also available for
  //               _s16[_f32_x2], _s32[_f64_x2],
  // _u8[_f16_x2], _u16[_f32_x2], _u32[_f64_x2].
  svint8_t svcvtn_s8[_f16_x2](svfloat16x2_t zn);
```

#### SABAL, UABAL

Two-way absolute difference sum and accumulate long.

``` c
  // Variants are also available for
  //       _s32, _s64,
  // _u16, _u32, _u64.
  svint16_t svabal[_s16](svint16_t zda, svint8_t zn, svint8_t zm);
  svint16_t svabal[_n_s16](svint16_t zda, svint8_t zn, int8_t zm);
```

#### SCVTF, SCVTFLT, UCVTF, UCVTFLT

Integer convert to floating-point (top and bottom).

``` c
  // Variants are also available for
  //            _f32[_s16], _f64[_s32],
  // _f16[_u8], _f32[_u16], _f64[_u32].
  svfloat16_t svcvtt_f16[_s8](svint8_t zn);
  svfloat16_t svcvtb_f16[_s8](svint8_t zn);
```

#### SQSHRN, UQSHRN

Multi-vector saturating shift right narrow and interleave.

``` c
  // Variants are also available for _s8[_s16_x2], _u16[_u32_x2] and _u8[_u16_x2].
  svint16_t svqshrn[_n]_s16[_s32_x2](svint32x2_t zn, uint64_t imm);
  ```

#### SQSHRUN

Signed saturating shift right narrow by immediate to interleaved unsigned integer.

``` c
  // Variant for _u8[_s16_x2] is also available.
  svuint16_t svqshrun[_n]_u16[_s32_x2](svint32x2_t zn, uint64_t imm);
  ```

#### SUBP

Subtract pairwise.

``` c
  // Variants are also available for _s16, _s32, _s64, _u8, _u16, _u32 and _u64.
  svint8_t svsubp[_s8]_m (svbool_t pg, svint8_t zdn, svint8_t zm);
  svint8_t svsubp[_s8]_x (svbool_t pg, svint8_t zdn, svint8_t zm);
  ```

### SME2 maximum and minimum absolute value

The intrinsics in this section are available when `__ARM_FEATURE_SME2`
and `__ARM_FEATURE_FAMINMAX` are both defined to 1.

#### FAMAX

Absolute maximum.
``` c
  // Variants are also available for:
  //  [_f32_x2], [_f64_x2],
  //  [_f16_x4], [_f32_x4] and [_f64_x4]
  svfloat16x2_t svamax[_f16_x2](svfloat16x2 zd, svfloat16x2_t zm) __arm_streaming;
```

#### FAMIN

Absolute minimum.
``` c
  // Variants are also available for:
  //  [_f32_x2], [_f64_x2],
  //  [_f16_x4], [_f32_x4] and [_f64_x4]
  svfloat16x2_t svamin[_f16_x2](svfloat16x2 zd, svfloat16x2_t zm) __arm_streaming;
```

### SME2 lookup table

The intrinsics in this section are available when
`__ARM_FEATURE_SME_LUTv2` is defined to 1.

#### MOVT

Move vector register to ZT0.
``` c
  // Variants are also available for:
  // [_s8], [_u16], [_s16], [_u32], [_s32], [_u64], [_s64]
  // [_bf16], [_f16], [_f32], [_f64]
  void svwrite_zt[_u8](uint64_t zt0, svuint8_t zt) __arm_streaming __arm_out("zt0");

  // Variants are also available for:
  // [_s8], [_u16], [_s16], [_u32], [_s32], [_u64], [_s64]
  // [_bf16], [_f16], [_f32], [_f64]
  void svwrite_lane_zt[_u8](uint64_t zt0, svuint8_t zt, uint64_t idx) __arm_streaming __arm_inout("zt0");
```

#### LUTI4

Lookup table read with 4-bit indexes and 8-bit elements.
``` c
  // Variants are also available for: _u8
  svint8x4_t svluti4_zt_s8_x4(uint64_t zt0, svuint8x2_t zn) __arm_streaming __arm_in("zt0");
```

### SVE2 and SME2 modal 8-bit floating-point intrinsics

The intrinsics in this section are available when `__ARM_FEATURE_FP8`
is defined, and `__ARM_FEATURE_SVE2` or `__ARM_FEATURE_SME2` is defined.
Individual intrinsics may have additional target feature requirements.

#### BF1CVT, BF2CVT, F1CVT, F2CVT

8-bit floating-point convert to half-precision and BFloat16.
``` c
  // Variants are also available for: _bf16
  svfloat16_t svcvt1_f16[_mf8]_fpm(svmfloat8_t zn, fpm_t fpm);
  svfloat16_t svcvt2_f16[_mf8]_fpm(svmfloat8_t zn, fpm_t fpm);
```

#### BF1CVTLT, BF2CVTLT, F1CVTLT, F2CVTLT

8-bit floating-point convert to half-precision and BFloat16 (top).
``` c
  // Variants are also available for: _bf16
  svfloat16_t svcvtlt1_f16[_mf8]_fpm(svmfloat8_t zn, fpm_t fpm);
  svfloat16_t svcvtlt2_f16[_mf8]_fpm(svmfloat8_t zn, fpm_t fpm);
```

#### BFCVTN, FCVTN

Half-precision and BFloat16 convert, narrow, and interleave to 8-bit
floating-point.
``` c
  // Variant is also available for: _bf16_x2
  svmfloat8_t svcvtn_mf8[_f16_x2]_fpm(svfloat16x2_t zn, fpm_t fpm);
```

#### FCVTNT, FCVTNB

Single-precision convert, narrow, and interleave to 8-bit floating-point (top and bottom).
``` c
  svmfloat8_t svcvtnt_mf8[_f32_x2]_fpm(svmfloat8_t zd, svfloat32x2_t zn, fpm_t fpm);
  svmfloat8_t svcvtnb_mf8[_f32_x2]_fpm(svfloat32x2_t zn, fpm_t fpm);
```

#### FDOT (4-way, vectors)

8-bit floating-point dot product to single-precision.
``` c
  // Only if (__ARM_FEATURE_SVE2  && __ARM_FEATURE_FP8DOT4) || __ARM_FEATURE_SSVE_FP8DOT4
  svfloat32_t svdot[_f32_mf8]_fpm(svfloat32_t zda, svmfloat8_t zn, svmfloat8_t zm, fpm_t fpm);
  svfloat32_t svdot[_n_f32_mf8]_fpm(svfloat32_t zda, svmfloat8_t zn, mfloat8_t zm, fpm_t fpm);
```

#### FDOT (4-way, indexed)

8-bit floating-point indexed dot product to single-precision.
``` c
  // Only if (__ARM_FEATURE_SVE2  && __ARM_FEATURE_FP8DOT4) || __ARM_FEATURE_SSVE_FP8DOT4
  svfloat32_t svdot_lane[_f32_mf8]_fpm(svfloat32_t zda, svmfloat8_t zn, svmfloat8_t zm,
                                       uint64_t imm0_3, fpm_t fpm);
```

#### FDOT (2-way, vectors, FP8 to FP16)

8-bit floating-point dot product to half-precision.
``` c
  // Only if (__ARM_FEATURE_SVE2  && __ARM_FEATURE_FP8DOT2) || __ARM_FEATURE_SSVE_FP8DOT2
  svfloat16_t svdot[_f16_mf8]_fpm(svfloat16_t zda, svmfloat8_t zn, svmfloat8_t zm, fpm_t fpm);
  svfloat16_t svdot[_n_f16_mf8]_fpm(svfloat16_t zda, svmfloat8_t zn, mfloat8_t zm, fpm_t fpm);
```

#### FDOT (2-way, indexed, FP8 to FP16)

8-bit floating-point dot product to half-precision.
``` c
  // Only if (__ARM_FEATURE_SVE2  && __ARM_FEATURE_FP8DOT2) || __ARM_FEATURE_SSVE_FP8DOT2
  svfloat16_t svdot_lane[_f16_mf8]_fpm(svfloat16_t zda, svmfloat8_t zn, svmfloat8_t zm,
                                       uint64_t imm0_7, fpm_t fpm);
```

#### FMLALB (vectors, FP8 to FP16)

8-bit floating-point multiply-add long to half-precision (bottom).
``` c
  // Only if (__ARM_FEATURE_SVE2  && __ARM_FEATURE_FP8FMA) || __ARM_FEATURE_SSVE_FP8FMA
  svfloat16_t svmlalb[_f16_mf8]_fpm(svfloat16_t zda, svmfloat8_t zn, svmfloat8_t zm, fpm_t fpm);
  svfloat16_t svmlalb[_n_f16_mf8]_fpm(svfloat16_t zda, svmfloat8_t zn, mfloat8_t zm, fpm_t fpm);
```

#### FMLALB (indexed, FP8 to FP16)

8-bit floating-point multiply-add long to half-precision (bottom, indexed).
``` c
  // Only if (__ARM_FEATURE_SVE2  && __ARM_FEATURE_FP8FMA) || __ARM_FEATURE_SSVE_FP8FMA
  svfloat16_t svmlalb_lane[_f16_mf8]_fpm(svfloat16_t zda, svmfloat8_t zn, svmfloat8_t zm,
                                         uint64_t imm0_15, fpm_t fpm);
```

#### FMLALLBB (vectors)

8-bit floating-point multiply-add long long to single-precision (bottom bottom).
``` c
  // Only if (__ARM_FEATURE_SVE2  && __ARM_FEATURE_FP8FMA) || __ARM_FEATURE_SSVE_FP8FMA
  svfloat32_t svmlallbb[_f32_mf8]_fpm(svfloat32_t zda, svmfloat8_t zn, svmfloat8_t zm, fpm_t fpm);
  svfloat32_t svmlallbb[_n_f32_mf8]_fpm(svfloat32_t zda, svmfloat8_t zn, mfloat8_t zm, fpm_t fpm);
```

#### FMLALLBB (indexed)

8-bit floating-point multiply-add long long to single-precision (bottom bottom, indexed).
``` c
  // Only if (__ARM_FEATURE_SVE2  && __ARM_FEATURE_FP8FMA) || __ARM_FEATURE_SSVE_FP8FMA
  svfloat32_t svmlallbb_lane[_f32_mf8]_fpm(svfloat32_t zda, svmfloat8_t zn, svmfloat8_t zm,
                                           uint64_t imm0_15, fpm_t fpm);
```

#### FMLALLBT (vectors)

8-bit floating-point multiply-add long long to single-precision (bottom top).
``` c
  // Only if (__ARM_FEATURE_SVE2  && __ARM_FEATURE_FP8FMA) || __ARM_FEATURE_SSVE_FP8FMA
  svfloat32_t svmlallbt[_f32_mf8]_fpm(svfloat32_t zda, svmfloat8_t zn, svmfloat8_t zm, fpm_t fpm);
  svfloat32_t svmlallbt[_n_f32_mf8]_fpm(svfloat32_t zda, svmfloat8_t zn, mfloat8_t zm, fpm_t fpm);
```

#### FMLALLBT (indexed)

8-bit floating-point multiply-add long long to single-precision (bottom top, indexed).
``` c
  // Only if (__ARM_FEATURE_SVE2  && __ARM_FEATURE_FP8FMA) || __ARM_FEATURE_SSVE_FP8FMA
  svfloat32_t svmlallbt_lane[_f32_mf8]_fpm(svfloat32_t zda, svmfloat8_t zn, svmfloat8_t zm,
                                           uint64_t imm0_15, fpm_t fpm);
```

#### FMLALLTB (vectors)

8-bit floating-point multiply-add long long to single-precision (top bottom).
``` c
  // Only if (__ARM_FEATURE_SVE2  && __ARM_FEATURE_FP8FMA) || __ARM_FEATURE_SSVE_FP8FMA
  svfloat32_t svmlalltb[_f32_mf8]_fpm(svfloat32_t zda, svmfloat8_t zn, svmfloat8_t zm, fpm_t fpm);
  svfloat32_t svmlalltb[_n_f32_mf8]_fpm(svfloat32_t zda, svmfloat8_t zn, mfloat8_t zm, fpm_t fpm);
```

#### FMLALLTB (indexed)

8-bit floating-point multiply-add long long to single-precision (top bottom, indexed).
``` c
  // Only if (__ARM_FEATURE_SVE2  && __ARM_FEATURE_FP8FMA) || __ARM_FEATURE_SSVE_FP8FMA
  svfloat32_t svmlalltb_lane[_f32_mf8]_fpm(svfloat32_t zda, svmfloat8_t zn, svmfloat8_t zm,
                                           uint64_t imm0_15, fpm_t fpm);
```

#### FMLALLTT (vectors)

8-bit floating-point multiply-add long long to single-precision (top top).
``` c
  // Only if (__ARM_FEATURE_SVE2  && __ARM_FEATURE_FP8FMA) || __ARM_FEATURE_SSVE_FP8FMA
  svfloat32_t svmlalltt[_f32_mf8]_fpm(svfloat32_t zda, svmfloat8_t zn, svmfloat8_t zm, fpm_t fpm);
  svfloat32_t svmlalltt[_n_f32_mf8]_fpm(svfloat32_t zda, svmfloat8_t zn, mfloat8_t zm, fpm_t fpm);
```

#### FMLALLTT (indexed)

8-bit floating-point multiply-add long long to single-precision (top top, indexed).
``` c
  // Only if (__ARM_FEATURE_SVE2  && __ARM_FEATURE_FP8FMA) || __ARM_FEATURE_SSVE_FP8FMA
  svfloat32_t svmlalltt_lane[_f32_mf8]_fpm(svfloat32_t zda, svmfloat8_t zn, svmfloat8_t zm,
                                           uint64_t imm0_15, fpm_t fpm);
```

#### FMLALT (vectors, FP8 to FP16)

8-bit floating-point multiply-add long to half-precision (top).
```c
  // Only if (__ARM_FEATURE_SVE2  && __ARM_FEATURE_FP8FMA) || __ARM_FEATURE_SSVE_FP8FMA
  svfloat16_t svmlalt[_f16_mf8]_fpm(svfloat16_t zda, svmfloat8_t zn, svmfloat8_t zm, fpm_t fpm);
  svfloat16_t svmlalt[_n_f16_mf8]_fpm(svfloat16_t zda, svmfloat8_t zn, mfloat8_t zm, fpm_t fpm);
```

#### FMLALT (indexed, FP8 to FP16)

8-bit floating-point multiply-add long to half-precision (top, indexed).
```c
  // Only if (__ARM_FEATURE_SVE2  && __ARM_FEATURE_FP8FMA) || __ARM_FEATURE_SSVE_FP8FMA
  svfloat16_t svmlalt_lane[_f16_mf8]_fpm(svfloat16_t zda, svmfloat8_t zn, svmfloat8_t zm,
                                         uint64_t imm0_15, fpm_t fpm);
```

### SME2 modal 8-bit floating-point intrinsics

The intrinsics in this section are available when `__ARM_FEATURE_SME2` and
`__ARM_FEATURE_FP8` are defined. Individual intrinsics may have
additional target feature requirements.

#### BF1CVT, BF2CVT, F1CVT, F2CVT

8-bit floating-point convert to half-precision or BFloat16.
``` c
  // Variant is also available for: _bf16[_mf8]_x2
  svfloat16x2_t svcvt1_f16[_mf8]_x2_fpm(svmfloat8_t zn, fpm_t fpm) __arm_streaming;
  svfloat16x2_t svcvt2_f16[_mf8]_x2_fpm(svmfloat8_t zn, fpm_t fpm) __arm_streaming;
```

#### BF1CVTL, BF2CVTL, F1CVTL, F2CVTL

8-bit floating-point convert to deinterleaved half-precision or BFloat16.
``` c
  // Variant is also available for: _bf16[_mf8]_x2
  svfloat16x2_t svcvtl1_f16[_mf8]_x2_fpm(svmfloat8_t zn, fpm_t fpm) __arm_streaming;
  svfloat16x2_t svcvtl2_f16[_mf8]_x2_fpm(svmfloat8_t zn, fpm_t fpm) __arm_streaming;
```

#### BFCVT, FCVT

Convert to packed 8-bit floating-point format.
``` c
  // Variants are also available for: _mf8[_bf16_x2] and _mf8[_f32_x4]
  svmfloat8_t svcvt_mf8[_f16_x2]_fpm(svfloat16x2_t zn, fpm_t fpm) __arm_streaming;
```

#### FCVTN

Convert to interleaved 8-bit floating-point format.
``` c
  svmfloat8_t svcvtn_mf8[_f32_x4]_fpm(svfloat32x4_t zn, fpm_t fpm) __arm_streaming;
```

#### FSCALE
``` c
  // Variants are also available for:
  // [_single_f32_x2], [_single_f64_x2],
  // [_single_f16_x4], [_single_f32_x4] and [_single_f64_x4]
  svfloat16x2_t svscale[_single_f16_x2](svfloat16x2_t zd, svint16_t zm) __arm_streaming;

  // Variants are also available for:
  //  [_f32_x2], [_f64_x2],
  //  [_f16_x4], [_f32_x4] and [_f64_x4]
  svfloat16x2_t svscale[_f16_x2](svfloat16x2_t zd, svint16x2_t zm) __arm_streaming;
```

#### FDOT

Multi-vector 8-bit floating-point dot-product.
``` c
  // Available variants are: _za16 if __ARM_FEATURE_SME_F8F16 != 0
  //                         _za32 if __ARM_FEATURE_SME_F8F32 != 0
  void svdot_lane_za16[_mf8]_vg1x2_fpm(uint32_t slice, svmfloat8x2_t zn,
                                       svmfloat8_t zm, uint64_t imm_idx,
                                       fpm_t fpm) __arm_streaming __arm_inout("za");

  void svdot_lane_za16[_mf8]_vg1x4_fpm(uint32_t slice, svmfloat8x4_t zn,
                                      svmfloat8_t zm, uint64_t imm_idx,
                                      fpm_t fpm) __arm_streaming __arm_inout("za");

  void svdot[_single]_za16[_mf8]_vg1x2_fpm(uint32_t slice, svmfloat8x2_t zn,
                                           svmfloat8_t zm, fpm_t fpm)
                                           __arm_streaming __arm_inout("za");

  void svdot[_single]_za16[_mf8]_vg1x4_fpm(uint32_t slice, svmfloat8x4_t zn,
                                           svmfloat8_t zm, fpm_t fpm)
                                           __arm_streaming __arm_inout("za");

  void svdot_za16[_mf8]_vg1x2_fpm(uint32_t slice, svmfloat8x2_t zn, svmfloat8x2_t zm,
                                  fpm_t fpm) __arm_streaming __arm_inout("za");

  void svdot_za16[_mf8]_vg1x4_fpm(uint32_t slice, svmfloat8x4_t zn, svmfloat8x4_t zm,
                                  fpm_t fpm)  __arm_streaming __arm_inout("za");
```

#### FVDOT

Multi-vector 8-bit floating-point vertical dot-product by indexed element to
half-precision.
``` c
  // Only if __ARM_FEATURE_SME_F8F16 != 0
  void svvdot_lane_za16[_mf8]_vg1x2_fpm(uint32_t slice, svmfloat8x2_t zn,
                                        svmfloat8_t zm, uint64_t imm_idx,
                                        fpm_t fpm)  __arm_streaming __arm_inout("za");
```

#### FVDOTB, FVDOTT

Multi-vector 8-bit floating-point vertical dot-product.
``` c
  // Only if __ARM_FEATURE_SME_F8F32 != 0
  void svvdott_lane_za32[_mf8]_vg1x4_fpm(uint32_t slice, svmfloat8x2_t zn,
                                         svmfloat8_t zm, uint64_t imm_idx,
                                         fpm_t fpm) __arm_streaming __arm_inout("za");

  void svvdotb_lane_za32[_mf8]_vg1x4_fpm(uint32_t slice, svmfloat8x2_t zn,
                                         svmfloat8_t zm, uint64_t imm_idx,
                                         fpm_t fpm) __arm_streaming __arm_inout("za");
```

#### FMLAL

Multi-vector 8-bit floating-point multiply-add long.
``` c
  // Only if __ARM_FEATURE_SME_F8F16 != 0
  void svmla_lane_za16[_mf8]_vg2x1_fpm(uint32_t slice, svmfloat8_t zn,
                                       svmfloat8_t zm, uint64_t imm_idx,
                                       fpm_t fpm)  __arm_streaming __arm_inout("za");

  void svmla_lane_za16[_mf8]_vg2x2_fpm(uint32_t slice, svmfloat8x2_t zn,
                                       svmfloat8_t zm, uint64_t imm_idx,
                                       fpm_t fpm)  __arm_streaming __arm_inout("za");

  void svmla_lane_za16[_mf8]_vg2x4_fpm(uint32_t slice, svmfloat8x4_t zn,
                                       svmfloat8_t zm, uint64_t imm_idx
                                       fpm_t fpm) __arm_streaming __arm_inout("za");

  void svmla_za16[_mf8]_vg2x1_fpm(uint32_t slice, svmfloat8_t zn,
                                           svmfloat8_t zm, fpm_t fpm)
                                           __arm_streaming __arm_inout("za");

  void svmla[_single]_za16[_mf8]_vg2x2_fpm(uint32_t slice, svmfloat8x2_t zn,
                                           svmfloat8_t zm, fpm_t fpm)
                                           __arm_streaming __arm_inout("za");

  void svmla[_single]_za16[_mf8]_vg2x4_fpm(uint32_t slice, svmfloat8x4_t zn,
                                           svmfloat8_t zm, fpm_t fpm)
                                           __arm_streaming __arm_inout("za");

  void svmla_za16[_mf8]_vg2x2_fpm(uint32_t slice, svmfloat8x2_t zn, svmfloat8x2_t zm,
                                  fpm_t fpm) __arm_streaming __arm_inout("za");

  void svmla_za16[_mf8]_vg2x4_fpm(uint32_t slice, svmfloat8x4_t zn, svmfloat8x4_t zm,
                                  fpm_t fpm) __arm_streaming __arm_inout("za");
```

#### FMLALL

Multi-vector 8-bit floating-point multiply-add long.
``` c
// Only if __ARM_FEATURE_SME_F8F32 != 0
  void svmla_lane_za32[_mf8]_vg4x1_fpm(uint32_t slice, svmfloat8_t zn,
                                       svmfloat8_t zm, uint64_t imm_idx,
                                       fpm_t fpm)__arm_streaming __arm_inout("za");

  void svmla_lane_za32[_mf8]_vg4x2_fpm(uint32_t slice, svmfloat8x2_t zn,
                                       svmfloat8_t zm, uint64_t imm_idx,
                                       fpm_t fpm)__arm_streaming __arm_inout("za");

  void svmla_lane_za32[_mf8]_vg4x4_fpm(uint32_t slice, svmfloat8x4_t zn,
                                       svmfloat8_t zm, uint64_t imm_idx,
                                       fpm_t fpm)__arm_streaming __arm_inout("za");

  void svmla_za32[_mf8]_vg4x1_fpm(uint32_t slice, svmfloat8_t zn,
                                           svmfloat8_t zm, fpm_t fpm)
                                           __arm_streaming __arm_inout("za");

  void svmla[_single]_za32[_mf8]_vg4x2_fpm(uint32_t slice, svmfloat8x2_t zn,
                                           svmfloat8_t zm, fpm_t fpm)
                                           __arm_streaming __arm_inout("za");

  void svmla[_single]_za32[_mf8]_vg4x4_fpm(uint32_t slice, svmfloat8x4_t zn,
                                           svmfloat8_t zm, fpm_t fpm)
                                           __arm_streaming __arm_inout("za");

  void svmla_za32[_mf8]_vg4x2_fpm(uint32_t slice, svmfloat8x2_t zn, svmfloat8x2_t zm,
                                  fpm_t fpm) __arm_streaming __arm_inout("za");

  void svmla_za32[_mf8]_vg4x4_fpm(uint32_t slice, svmfloat8x4_t zn, svmfloat8x4_t zm,
                                  fpm_t fpm) __arm_streaming __arm_inout("za");
```

#### FMOPA

8-bit floating-point sum of outer products and accumulate.
``` c
  // Only if __ARM_FEATURE_SME_F8F16 != 0
    void svmopa_za16[_mf8]_m_fpm(uint64_t tile, svbool_t pn, svbool_t pm,
                                 svmfloat8_t zn, svmfloat8_t zm, fpm_t fpm)
                                 __arm_streaming __arm_inout("za");

  // Only if __ARM_FEATURE_SME_F8F32 != 0
    void svmopa_za32[_mf8]_m_fpm(uint64_t tile, svbool_t pn, svbool_t pm,
                                 svmfloat8_t zn, svmfloat8_t zm, fpm_t fpm)
                                 __arm_streaming __arm_inout("za");
```

### SME2 mop4 intrinsics

The intrinsics in this section are available when `__ARM_FEATURE_SME2` and
`__ARM_FEATURE_SME_MOP4` are defined. Individual intrinsics may have
additional target feature requirements.

These intrinsics have an additional '_{1,2}x{1,2}' suffix in
non-overloaded names to indicate which vector argument is a vector register pair.

#### FMOP4A (non-FP8), BFMOP4A, SMOP4A, UMOP4A

``` c
  // Variants are also available for:
  //   _za16[_f16_f16] (only if __ARM_FEATURE_SME_F16F16 != 0)
  //   _za16[_bf16_bf16] (only if __ARM_FEATURE_SME_B16B16 != 0)
  //   _za32[_f16_f16]
  //   _za32[_bf16_bf16]
  //   _za32[_s16_s16]
  //   _za32[_u16_u16]
  //   _za32[_s8_s8]
  //   _za32[_u8_u8]
  //   _za64[_f64_f64] (only if __ARM_FEATURE_SME_F64F64 != 0)
  //   _za64[_s16_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u16_u16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmop4a[_1x1]_za32[_f32_f32](uint64_t tile, svfloat32_t zn,
                                    svfloat32_t zm)
    __arm_streaming __arm_inout("za");

  // Variants are also available for:
  //   _za16[_f16_f16] (only if __ARM_FEATURE_SME_F16F16 != 0)
  //   _za16[_bf16_bf16] (only if __ARM_FEATURE_SME_B16B16 != 0)
  //   _za32[_f16_f16]
  //   _za32[_bf16_bf16]
  //   _za32[_s16_s16]
  //   _za32[_u16_u16]
  //   _za32[_s8_s8]
  //   _za32[_u8_u8]
  //   _za64[_f64_f64] (only if __ARM_FEATURE_SME_F64F64 != 0)
  //   _za64[_s16_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u16_u16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmop4a[_2x2]_za32[_f32_f32](uint64_t tile, svfloat32x2_t zn,
                                    svfloat32x2_t zm)
    __arm_streaming __arm_inout("za");

  // Variants are also available for:
  //   _za16[_f16_f16] (only if __ARM_FEATURE_SME_F16F16 != 0)
  //   _za16[_bf16_bf16] (only if __ARM_FEATURE_SME_B16B16 != 0)
  //   _za32[_f16_f16]
  //   _za32[_bf16_bf16]
  //   _za32[_s16_s16]
  //   _za32[_u16_u16]
  //   _za32[_s8_s8]
  //   _za32[_u8_u8]
  //   _za64[_f64_f64] (only if __ARM_FEATURE_SME_F64F64 != 0)
  //   _za64[_s16_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u16_u16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmop4a[_2x1]_za32[_f32_f32](uint64_t tile, svfloat32x2_t zn,
                                    svfloat32_t zm)
    __arm_streaming __arm_inout("za");

  // Variants are also available for:
  //   _za16[_f16_f16] (only if __ARM_FEATURE_SME_F16F16 != 0)
  //   _za16[_bf16_bf16] (only if __ARM_FEATURE_SME_B16B16 != 0)
  //   _za32[_f16_f16]
  //   _za32[_bf16_bf16]
  //   _za32[_s16_s16]
  //   _za32[_u16_u16]
  //   _za32[_s8_s8]
  //   _za32[_u8_u8]
  //   _za64[_f64_f64] (only if __ARM_FEATURE_SME_F64F64 != 0)
  //   _za64[_s16_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u16_u16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmop4a[_1x2]_za32[_f32_f32](uint64_t tile, svfloat32_t zn,
                                    svfloat32x2_t zm)
    __arm_streaming __arm_inout("za");
  ```

#### FMOP4S (non-FP8), BFMOP4S, SMOP4S, UMOP4S

``` c
  // Variants are also available for:
  //   _za16[_f16_f16] (only if __ARM_FEATURE_SME_F16F16 != 0)
  //   _za16[_bf16_bf16] (only if __ARM_FEATURE_SME_B16B16 != 0)
  //   _za32[_f16_f16]
  //   _za32[_bf16_bf16]
  //   _za32[_s16_s16]
  //   _za32[_u16_u16]
  //   _za32[_s8_s8]
  //   _za32[_u8_u8]
  //   _za64[_f64_f64] (only if __ARM_FEATURE_SME_F64F64 != 0)
  //   _za64[_s16_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u16_u16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmop4s[_1x1]_za32[_f32_f32](uint64_t tile, svfloat32_t zn,
                                    svfloat32_t zm)
    __arm_streaming __arm_inout("za");

  // Variants are also available for:
  //   _za16[_f16_f16] (only if __ARM_FEATURE_SME_F16F16 != 0)
  //   _za16[_bf16_bf16] (only if __ARM_FEATURE_SME_B16B16 != 0)
  //   _za32[_f16_f16]
  //   _za32[_bf16_bf16]
  //   _za32[_s16_s16]
  //   _za32[_u16_u16]
  //   _za32[_s8_s8]
  //   _za32[_u8_u8]
  //   _za64[_f64_f64] (only if __ARM_FEATURE_SME_F64F64 != 0)
  //   _za64[_s16_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_s16_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmop4s[_2x2]_za32[_f32_f32](uint64_t tile, svfloat32x2_t zn,
                                    svfloat32x2_t zm)
    __arm_streaming __arm_inout("za");

  // Variants are also available for:
  //   _za16[_f16_f16] (only if __ARM_FEATURE_SME_F16F16 != 0)
  //   _za16[_bf16_bf16] (only if __ARM_FEATURE_SME_B16B16 != 0)
  //   _za32[_f16_f16]
  //   _za32[_bf16_bf16]
  //   _za32[_s16_s16]
  //   _za32[_u16_u16]
  //   _za32[_s8_s8]
  //   _za32[_u8_u8]
  //   _za64[_f64_f64] (only if __ARM_FEATURE_SME_F64F64 != 0)
  //   _za64[_s16_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u16_u16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmop4s[_2x1]_za32[_f32_f32](uint64_t tile, svfloat32x2_t zn,
                                    svfloat32_t zm)
    __arm_streaming __arm_inout("za");

  // Variants are also available for:
  //   _za16[_f16_f16] (only if __ARM_FEATURE_SME_F16F16 != 0)
  //   _za16[_bf16_bf16] (only if __ARM_FEATURE_SME_B16B16 != 0)
  //   _za32[_f16_f16]
  //   _za32[_bf16_bf16]
  //   _za32[_s16_s16]
  //   _za32[_u16_u16]
  //   _za32[_s8_s8]
  //   _za32[_u8_u8]
  //   _za64[_f64_f64] (only if __ARM_FEATURE_SME_F64F64 != 0)
  //   _za64[_s16_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  //   _za64[_u16_u16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmop4s[_1x2]_za32[_f32_f32](uint64_t tile, svfloat32_t zn,
                                    svfloat32x2_t zm)
    __arm_streaming __arm_inout("za");
```

#### SUMOP4A

``` c
  // Variants are also available for:
  //   _za64[_s16_u16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmop4a[_1x1]_za32[_s8_u8](uint64_t tile, svint8_t zn,
                                  svuint8_t zm)
    __arm_streaming __arm_inout("za");

  // Variants are also available for:
  //   _za64[_s16_u16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmop4a[_2x2]_za32[_s8_u8](uint64_t tile, svint8x2_t zn,
                                  svuint8x2_t zm)
    __arm_streaming __arm_inout("za");

  // Variants are also available for:
  //   _za64[_s16_u16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmop4a[_2x1]_za32[_s8_u8](uint64_t tile, svint8x2_t zn,
                                  svuint8_t zm)
    __arm_streaming __arm_inout("za");

  // Variants are also available for:
  //   _za64[_s16_u16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmop4a[_1x2]_za32[_s8_u8](uint64_t tile, svint8_t zn,
                                  svuint8x2_t zm)
    __arm_streaming __arm_inout("za");
```

#### SUMOP4S

``` c
  // Variants are also available for:
  //   _za64[_s16_u16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmop4s[_1x1]_za32[_s8_u8](uint64_t tile, svint8_t zn,
                                  svuint8_t zm)
    __arm_streaming __arm_inout("za");

  // Variants are also available for:
  //   _za64[_s16_u16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmop4s[_2x2]_za32[_s8_u8](uint64_t tile, svint8x2_t zn,
                                  svuint8x2_t zm)
    __arm_streaming __arm_inout("za");

  // Variants are also available for:
  //   _za64[_s16_u16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmop4s[_2x1]_za32[_s8_u8](uint64_t tile, svint8x2_t zn,
                                  svuint8_t zm)
    __arm_streaming __arm_inout("za");

  // Variants are also available for:
  //   _za64[_s16_u16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmop4s[_1x2]_za32[_s8_u8](uint64_t tile, svint8_t zn,
                                  svuint8x2_t zm)
    __arm_streaming __arm_inout("za");
```

#### USMOP4A

``` c
  // Variants are also available for:
  //   _za64[_u16_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmop4a[_1x1]_za32[_u8_s8](uint64_t tile, svuint8_t zn,
                                  svint8_t zm)
    __arm_streaming __arm_inout("za");

  // Variants are also available for:
  //   _za64[_u16_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmop4a[_2x2]_za32[_u8_s8](uint64_t tile, svuint8x2_t zn,
                                  svint8x2_t zm)
    __arm_streaming __arm_inout("za");

  // Variants are also available for:
  //   _za64[_u16_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmop4a[_2x1]_za32[_u8_s8](uint64_t tile, svuint8x2_t zn,
                                  svint8_t zm)
    __arm_streaming __arm_inout("za");

  // Variants are also available for:
  //   _za64[_u16_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmop4a[_1x2]_za32[_u8_s8](uint64_t tile, svuint8_t zn,
                                  svint8x2_t zm)
    __arm_streaming __arm_inout("za");
```

#### USMOP4S

``` c
  // Variants are also available for:
  //   _za64[_u16_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmop4s[_1x1]_za32[_u8_s8](uint64_t tile, svuint8_t zn,
                                  svint8_t zm)
    __arm_streaming __arm_inout("za");

  // Variants are also available for:
  //   _za64[_u16_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmop4s[_2x2]_za32[_u8_s8](uint64_t tile, svuint8x2_t zn,
                                  svint8x2_t zm)
    __arm_streaming __arm_inout("za");

  // Variants are also available for:
  //   _za64[_u16_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmop4s[_2x1]_za32[_u8_s8](uint64_t tile, svuint8x2_t zn,
                                  svint8_t zm)
    __arm_streaming __arm_inout("za");

  // Variants are also available for:
  //   _za64[_u16_s16] (only if __ARM_FEATURE_SME_I16I64 != 0)
  void svmop4s[_1x2]_za32[_u8_s8](uint64_t tile, svuint8_t zn,
                                  svint8x2_t zm)
    __arm_streaming __arm_inout("za");
```

#### FMOP4A (FP8)

``` c
    // Variants are also available for:
  //   _za16[_mf8_mf8] (only if __ARM_FEATURE_SME_F8F16 != 0)
  //   _za32[_mf8_mf8] (only if __ARM_FEATURE_SME_F8F32 != 0)
  void svmop4a[_1x1]_za32[_mf8_mf8]_fpm(uint64_t tile, svmfloat8_t zn,
                                        svmfloat8_t zm, fpm_t fpm)
    __arm_streaming __arm_inout("za");

  // Variants are also available for:
  //   _za16[_mf8_mf8] (only if __ARM_FEATURE_SME_F8F16 != 0)
  //   _za32[_mf8_mf8] (only if __ARM_FEATURE_SME_F8F32 != 0)
  void svmop4a[_2x2]_za32[_mf8_mf8]_fpm(uint64_t tile, svmfloat8x2_t zn,
                                        svmfloat8x2_t zm, fpm_t fpm)
    __arm_streaming __arm_inout("za");

  // Variants are also available for:
  //   _za16[_mf8_mf8] (only if __ARM_FEATURE_SME_F8F16 != 0)
  //   _za32[_mf8_mf8] (only if __ARM_FEATURE_SME_F8F32 != 0)
  void svmop4a[_2x1]_za32[_mf8_mf8]_fpm(uint64_t tile, svmfloat8x2_t zn,
                                        svmfloat8_t zm, fpm_t fpm)
    __arm_streaming __arm_inout("za");

  // Variants are also available for:
  //   _za16[_mf8_mf8] (only if __ARM_FEATURE_SME_F8F16 != 0)
  //   _za32[_mf8_mf8] (only if __ARM_FEATURE_SME_F8F32 != 0)
  void svmop4a[_1x2]_za32[_mf8_mf8]_fpm(uint64_t tile, svmfloat8_t zn,
                                        svmfloat8x2_t zm, fpm_t fpm)
    __arm_streaming __arm_inout("za");
```

### SME2.3 lookup table

The intrinsics in this section are available when `__ARM_FEATURE_SME2p3`
is defined to 1.

#### LUTI6

Lookup table read with 6-bit indices (16-bit).

Use of this intrinsic if `svcntb() * 8 < 512` results in undefined behavior.

```c
  // Variants are also available for:
  //   _u16_x2_u8_x2, _f16_x2_u8_x2, _bf16_x2_u8_x2
  //   _s16_x2_u8_x3, _u16_x2_u8_x3, _f16_x2_u8_x3, _bf16_x2_u8_x3
  svint16x4_t svluti6_lane_s16_x4[_s16_x2_u8_x2](svint16x2_t table,
                                                 svuint8x2_t indices,
                                                 uint64_t imm_idx) __arm_streaming;
```

Lookup table read with 6-bit indices (four registers, 8-bit).

``` c
  // Variants are also available for: _u8 and _mf8.
  svint8x4_t svluti6_zt_s8_x4(uint64_t zt0, svuint8x3_t zn) __arm_streaming __arm_in("zt0");
```

Lookup table read with 6-bit indices (table, single, 8-bit).

``` c
  // Variants are also available for: _u8 and _mf8.
  svint8_t svluti6_zt_s8(uint64_t zt0, svuint8_t zn) __arm_streaming __arm_in("zt0");
```

# M-profile Vector Extension (MVE) intrinsics

The M-profile Vector Extension (MVE) [[MVE-spec]](#MVE-spec) instructions provide packed Single
Instruction Multiple Data (SIMD) and single-element scalar operations on a range
of integer and floating-point types.  MVE can also be referred to as Helium.

The M-profile Vector Extension provides for arithmetic, logical and saturated
arithmetic operations on 8-bit, 16-bit and 32-bit integers (and sometimes
on 64-bit integers) and on 16-bit and 32-bit floating-point data, arranged
in 128-bit vectors.

The intrinsics in this section provide C and C++ programmers with a
simple programming model allowing easy access to the code generation of the
MVE instructions for the Armv8.1-M Mainline architecture.

## Concepts

The MVE instructions are designed to improve the performance of SIMD operations
by operating on 128-bit *vectors* of *elements* of the same *scalar* data type.

For example, `uint16x8_t` is a 128-bit vector type consisting of eight
elements of the scalar `uint16_t` data type. Likewise, `uint8x16_t` is
a 128-bit vector type consisting of sixteen `uint8_t` elements.

In a vector programming model, operations are performed in parallel across
the elements of the vector. For example, `vmulq_u16(a, b)` is a vector
intrinsic which takes two `uint16x8_t` vector arguments `a` and `b`,
and returns the result of multiplying corresponding elements from each vector
together.

The M-profile Vector Extension also provides support for *vector-by-scalar*
operations. In these operations, a scalar value is provided directly,
duplicated to create a new vector with the same number of elements as an
input vector, and an operation is performed in parallel between
this new vector and other input vectors.

For example, `vaddq_n_u16(a, s)`, is a vector-by-scalar intrinsic
which takes one `uint16x8_t` vector argument and one `uint16_t` scalar
argument. A new vector is formed which consists of eight copies of `s`,
and this new vector is multiplied by `a`.

*Reductions* work across the whole of a single vector performing the same
operation between elements of that vector. For example, `vaddvq_u16(a)` is a
reduction intrinsic which takes a `uint16x8_t` vector, adds each of the eight
`uint16_t` elements together, and returns a `uint32_t` result containing
the sum.  Note the difference in return types between MVE's `vaddvq_u16` and
Advanced SIMD's implementation of the same name intrinsic, MVE returns the
`uint32_t` type whereas Advanced SIMD returns the element type `uint16_t`.

*Cross-lane* and *pairwise* vector operations work on pairs of elements within
a vector, sometimes performing the same operation like in the case of the
vector saturating doubling multiply subtract dual returning high half with
exchange `vqdmlsdhxq_s8` or sometimes a different one as is the case with the
vector complex addition intrinsic `vcaddq_rot90_s8`.

Some intrinsics may only read part of the input vectors whereas others may only
write part of the results. For example, the vector multiply long intrinsics,
depending on whether you use `vmullbq_int_s32` or `vmulltq_int_s32`, will
read the even (bottom) or odd (top) elements of each `int16x8_t` input
vectors, multiply them and write to a double-width `int32x4_t` vector.
In contrast the vector shift right and narrow will read in a double-width input
vector and, depending on whether you pick the bottom or top variant, write to
the even or odd elements of the single-width result vector. For example,
`vshrnbq_n_s16(a, b, 2)` will take each eight elements of type `int16_t` of
argument `b`, shift them right by two, narrow them to eight bits and write
them to the even elements of the `int8x16_t` result vector, where the odd
elements are picked from the equally typed `int8x16_t` argument `a`.

*Predication*: the M-profile Vector Extension uses vector predication to allow
SIMD operations on selected lanes. The MVE intrinsics expose vector predication
by providing predicated intrinsic variants for instructions that support it.
These intrinsics can be recognized by one of the four suffixes:

* `_m` (merging) which indicates that false-predicated lanes are not written
  to and keep the same value as they had in the first argument of the
  intrinsic.
* `_p` (predicated) which indicates that false-predicated lanes are not used
  in the SIMD operation. For example `vaddvq_p_s8`, where the
  false-predicated lanes are not added to the resulting sum.
* `_z` (zero) which indicates that false-predicated lanes are filled with
  zeros. These are only used for load instructions.
* `_x` (dont-care) which indicates that the false-predicated lanes have
  undefined values. These are syntactic sugar for merge intrinsics with a
  `vuninitializedq` inactive parameter.

These predicated intrinsics can also be recognized by their last parameter
being of type `mve_pred16_t`.  This is an alias for the `uint16_t` type.
Some predicated intrinsics may have a dedicated first parameter to specify the
value in the result vector for the false-predicated lanes; this argument will
be of the same type as the result type.  For example,
`v = veorq_m_s8(inactive, a, b, p)`, will write to each of the sixteen lanes
of the result vector `v`, either the result of the exclusive or between the
corresponding lanes of vectors `a` and `b`, or the corresponding lane of
vector `inactive`, depending on whether that lane is true- or false-predicated
in `p`.  The types of `inactive`, `a`, `b` and  `v` are all
`int8x16_t` in this case and `p` has type `mve_pred16_t`.

When calling a predicated intrinsic, the predicate mask value should
contain the same value in all bits corresponding to the same element
of an input or output vector. For example, an instruction operating on
32-bit vector elements should have a predicate mask in which each
block of 4 bits is either all 0 or all 1.

``` c
  mve_pred16_t mask8 = vcmpeqq_u8 (a, b);
  uint8x16_t r8  = vaddq_m_u8  (inactive, a, b, mask8); // OK
  uint16x8_t r16 = vaddq_m_u16 (inactive, c, d, mask8); // UNDEFINED BEHAVIOR
  mve_pred16_t mask8 = 0x5555;        // Predicate every other byte.
  uint8x16_t r8  = vaddq_m_u8  (inactive, a, b, mask8); // OK
  uint16x8_t r16 = vaddq_m_u16 (inactive, c, d, mask8); // UNDEFINED BEHAVIOR
```

In cases where the input and output vectors have different sizes (a
widening or narrowing operation), the mask should be consistent with
the largest element size used by the intrinsic. For example,
`vcvtbq_m_f16_f32` and `vcvtbq_m_f32_f16` should *both* be passed
a predicate mask consistent with 32-bit vector lanes.

Users wishing to exploit the MVE architecture's predication behavior
in finer detail than this constraint permits are encouraged to use
inline assembly.

## Scalar shift intrinsics

The M-profile Vector Extension (MVE) also provides a set of scalar shift
instructions that operate on signed and unsigned double-words and single-words.
These shifts can perform additional saturation, rounding, or both. The ACLE for
MVE defines intrinsics for these instructions.

## Namespace

By default all M-profile Vector Extension intrinsics are available with and
without the `__arm_` prefix.  If the `__ARM_MVE_PRESERVE_USER_NAMESPACE`
macro is defined, the `__arm_` prefix is mandatory.  This is available to hide
the user-namespace-polluting variants of the intrinsics.

## Intrinsic polymorphism

The ACLE for the M-profile Vector Extension intrinsics was designed in such a
way that it supports a polymorphic implementation of most intrinsics.  The
polymorphic name of an intrinsic is indicated by leaving out the type suffix
enclosed in square brackets, for example the vector addition intrinsic
`vaddq[_s32]` can be called using the function name `vaddq`.  Note that the
polymorphism is only possible on input parameter types and intrinsics with the
same name must still have the same number of parameters.  This is expected to
aid implementation of the polymorphism using C11's `_Generic` selection.

## Vector data types

Vector data types are named as a lane type and a multiple. Lane type
names are based on the types defined in `<stdint.h>`. For example,.
`int16x8_t` is a vector of eight `int16_t` values. The base types are
`int8_t`, `uint8_t`, `int16_t`, `uint16_t`, `int32_t`,
`uint32_t`, `int64_t`, `uint64_t`, `float16_t` and `float32_t`.
The multiples are such that the resulting vector types are 128-bit.

## Vector array data types

Array types are defined for multiples of 2 and 4 of all the vector types, for
use in load and store operations. For a vector type `<type>_t` the
corresponding array type is `<type>x<length>_t`. Concretely, an array type is
a structure containing a single array element called `val`.

For example, an array of two `int16x8_t` types is `int16x4x8_t`, and is
represented as

``` c
  struct int16x8x2_t { int16x8_t val[2]; };
```

## Scalar data types

For consistency, `<arm_mve.h>` defines some additional scalar data types
to match the vector types.

`float32_t` is defined as an alias for `float`, `float16_t` is defined as
an alias for `__fp16` and `mve_pred16_t` is defined as an alias for
`uint16_t`.

## Operations on data types

ACLE does not define implicit conversion between different data types.
For example:

``` c
  int32x4_t x;
  uint32x4_t y = x; // No representation change
  float32x4_t z = x; // Conversion of integer to floating type
```

Is not portable. Use the `vreinterpretq` intrinsics to convert from one
vector type to another without changing representation, and use the `vcvtq`
intrinsics to convert between integer and floating types; for example:

``` c
  int32x4_t x;
  uint32x4_t y = vreinterpretq_u32_s32(x);
  float32x4_t z = vcvtq_f32_s32(x);
```

ACLE does not define static construction of vector types. For example:

``` c
  int32x4_t x = { 1, 2, 3, 4 };
```

Is not portable. Use the `vcreateq` or `vdupq` intrinsics to construct values
from scalars.

In C++, ACLE does not define whether MVE data types are POD types or whether
they can be inherited from.

## Compatibility with other vector programming models

ACLE does not specify how the MVE Intrinsics interoperate with alternative
vector programming models. Consequently, programmers should take particular
care when combining the MVE programming model with such programming models.

For example, the GCC vector extensions permit initializing a variable using
array syntax, as so

``` c
  #include "arm_mve.h"
  ...
  uint32x4_t x = {0, 1, 2, 3}; // GCC extension.
  uint32_t y = vgetq_lane_s32 (x, 0); // ACLE MVE Intrinsic.
```

But the definition of the GCC vector extensions is such that the value
stored in `y` will depend on whether the program is running in big- or
little-endian mode.

It is recommended that MVE Intrinsics be used consistently:

``` c
  #include "arm_mve.h"
  ...
  const int temp[4] = {0, 1, 2, 3};
  uint32x4_t x = vld1q_s32 (temp);
  uint32_t y = vgetq_lane_s32 (x, 0);
```

## Availability of M-profile Vector Extension intrinsics

M-profile Vector Extension support is available if the `__ARM_FEATURE_MVE`
macro has a value other than 0 (see [M-profile Vector
Extension](#m-profile-vector-extension)). The availability of the
MVE Floating Point data types and intrinsics are predicated on the value of
this macro having bit two set.  In order to access the MVE intrinsics, it is
necessary to include the `<arm_mve.h>` header.

``` c
  #if (__ARM_FEATURE_MVE & 3) == 3
  #include <arm_mve.h>
    /* MVE integer and floating point intrinsics are now available to use.  */
  #elif __ARM_FEATURE_MVE & 1
  #include <arm_mve.h>
    /* MVE integer intrinsics are now available to use.  */
  #endif
```

### Specification of M-profile Vector Extension intrinsics

The M-profile Vector Extension intrinsics are specified in the Arm MVE
Intrinsics Reference Architecture Specification [[MVE]](#MVE).

The behavior of an intrinsic is specified to be equivalent to the
MVE instruction it is mapped to in [[MVE]](#MVE). Intrinsics are specified
as a mapping between their name, arguments and return values and the MVE
instruction and assembler operands which they are equivalent to.

A compiler may make use of the as-if rule from C [[C99]](#C99) (5.1.2.3) to perform
optimizations which preserve the instruction semantics.

### Undefined behavior

Care should be taken by compiler implementers not to introduce the concept of
undefined behavior to the semantics of an intrinsic.

### Alignment assertions

The MVE load and store instructions provide for alignment assertions, which may
speed up access to aligned data (and will fault access to unaligned data).  The
MVE intrinsics do not directly provide a means for asserting alignment.

# memcpy family of operations intrinsics - MOPS

## Introduction

This section describes the intrinsic for the new instructions introduced in the
Armv8.8-A and Armv9.3-A architecture updates for the `memcpy`, `memmove` and `memset`
family of memory operations (MOPS).

These instructions are designed to enable the standardization of the software
implementation of those operations. Therefore, most of the use cases for
the new instructions are covered by the compiler's code generation or by library
implementations.

An exception to that is the set of instructions covering the `memset` operation
with memory tagging. An intrinsic is available to provide access to this
operation. See [Memory tagging](#memory-tagging) for more information on
memory tagging.

Note: the `<arm_acle.h>` header should be included before using this intrinsic.

This intrinsic is available when both `__ARM_FEATURE_MOPS` and
`__ARM_FEATURE_MEMORY_TAGGING` are defined.

``` c
  void* __arm_mops_memset_tag(void* tagged_address, int value, size_t size)
```

This intrinsic performs a `memset` operation with tag setting on a memory block.

The parameters of `__arm_mops_memset_tag` are as follows:

* `tagged_address`: destination address to be set, containing the allocation
  tag in its bits `[59:56]`. The address should be aligned with the tag granule
  size. (See the [SETG\* instructions specification](<https://developer.arm.com/documentation/ddi0596/2021-09/Base-Instructions/SETGP--SETGM--SETGE--Memory-Set-with-tag-setting-?lang=en#sa_xd)
  for more details)
* `value`: fill value.
* `size`: number of bytes to fill. This should be a multiple of the tag
  granule size.

Similarly to C's `memset`, this intrinsic returns the `tagged_address` pointer.

# Architectural Extension Bridges

## Neon-SVE Bridge

The NEON_SVE Bridge adds intrinsics that allow conversions between Neon and
SVE vectors.

The [`<arm_neon_sve_bridge.h>`](#arm_neon_sve_bridge.h) header should be
included before using these intrinsics.

### `svset_neonq`

These intrinsics set the first 128 bits of SVE vector `vec` to `subvec`.

That is, bit *i* of the result is equal to:
* bit *i* of `subvec` if *i* < 128
* bit *i* of `vec` otherwise

On big-endian targets, this leaves lanes in a different
order from the “native” SVE order.  For example, if `subvec` is
`int32x4_t`, then on big-endian targets, the first memory element
is in lane 3 of `subvec` and is therefore in lane 3 of the returned
SVE vector.  Using `svld1` to load elements would instead put the
first memory element in lane 0 of the returned SVE vector.

When `svundef` is passed as the `vec` parameter, compilers are able
to reuse the SVE register overlapping the Neon input without generating
additional instructions.

| **Instances**                                                            |
|--------------------------------------------------------------------------|
| `svint8_t svset_neonq[_s8](svint8_t vec, int8x16_t subvec)`              |
| `svint16_t svset_neonq[_s16](svint16_t vec, int16x8_t subvec)`           |
| `svint32_t svset_neonq[_s32](svint32_t vec, int32x4_t subvec)`           |
| `svint64_t svset_neonq[_s64](svint64_t vec, int64x2_t subvec)`           |
| `svuint8_t svset_neonq[_u8](svuint8_t vec, uint8x16_t subvec)`           |
| `svuint16_t svset_neonq[_u16](svuint16_t vec, uint16x8_t subvec)`        |
| `svuint32_t svset_neonq[_u32](svuint32_t vec, uint32x4_t subvec)`        |
| `svuint64_t svset_neonq[_u64](svuint64_t vec, uint64x2_t subvec)`        |
| `svfloat16_t svset_neonq[_f16](svfloat16_t vec, float16x8_t subvec)`     |
| `svfloat32_t svset_neonq[_f32](svfloat32_t vec, float32x4_t subvec)`     |
| `svfloat64_t svset_neonq[_f64](svfloat64_t vec, float64x2_t subvec)`     |
| `svbfloat16_t svset_neonq[_bf16](svbfloat16_t vec, bfloat16x8_t subvec)` |
| `svmfloat8_t svset_neonq[_mf8](svmfloat8_t vec, mfloat8x16_t subvec)`    |

### `svget_neonq`

These intrinsics get the first 128 bit subvector of SVE vector `vec` as a
Neon vector.

| **Instances**                                       |
|-----------------------------------------------------|
| `int8x16_t svget_neonq[_s8](svint8_t vec)`          |
| `int16x8_t svget_neonq[_s16](svint16_t vec)`        |
| `int32x4_t svget_neonq[_s32](svint32_t vec)`        |
| `int64x2_t svget_neonq[_s64](svint64_t vec)`        |
| `uint8x16_t svget_neonq[_u8](svuint8_t vec)`        |
| `uint16x8_t svget_neonq[_u16](svuint16_t vec)`      |
| `uint32x4_t svget_neonq[_u32](svuint32_t vec)`      |
| `uint64x2_t svget_neonq[_u64](svuint64_t vec)`      |
| `float16x8_t svget_neonq[_f16](svfloat16_t vec)`    |
| `float32x4_t svget_neonq[_f32](svfloat32_t vec)`    |
| `float64x2_t svget_neonq[_f64](svfloat64_t vec)`    |
| `bfloat16x8_t svget_neonq[_bf16](svbfloat16_t vec)` |
| `mfloat8x16_t svget_neonq[_mf8](svmfloat8_t vec)`   |

### `svdup_neonq`

These intrinsics return an SVE vector with all SVE subvectors containing the
duplicated Neon vector `vec`.

| **Instances**                                       |
|-----------------------------------------------------|
| `svint8_t svdup_neonq[_s8](int8x16_t vec)`          |
| `svint16_t svdup_neonq[_s16](int16x8_t vec)`        |
| `svint32_t svdup_neonq[_s32](int32x4_t vec)`        |
| `svint64_t svdup_neonq[_s64](int64x2_t vec)`        |
| `svuint8_t svdup_neonq[_u8](uint8x16_t vec)`        |
| `svuint16_t svdup_neonq[_u16](uint16x8_t vec)`      |
| `svuint32_t svdup_neonq[_u32](uint32x4_t vec)`      |
| `svuint64_t svdup_neonq[_u64](uint64x2_t vec)`      |
| `svfloat16_t svdup_neonq[_f16](float16x8_t vec)`    |
| `svfloat32_t svdup_neonq[_f32](float32x4_t vec)`    |
| `svfloat64_t svdup_neonq[_f64](float64x2_t vec)`    |
| `svbfloat16_t svdup_neonq[_bf16](bfloat16x8_t vec)` |
| `svmfloat8_t svdup_neonq[_mf8](mfloat8x16_t vec)`   |

# Future directions

## Extensions under consideration

### Procedure calls and the Q / GE bits

The Arm procedure call standard [[AAPCS]](#AAPCS) states that the Q and GE bits are
undefined across public interfaces, but in practice it is desirable to
return saturation status from functions. There are at least two common
use cases:

To define small (inline) functions (defined in terms of
expressions involving intrinsics, which provide abstractions or emulate
other intrinsic families), it is desirable for such functions to have the
same well-defined effects on the Q/GE bits as the corresponding
intrinsics.

### DSP library functions

Options being considered are to define an extension to the pcs
attribute to indicate that Q is meaningful on the return, and possibly
also to infer this in the case of functions marked as inline.

### Returning a value in registers

As a type attribute this would allow things like

``` c
  struct __attribute__((value_in_regs)) Point { int x[2]; };
```

This would indicate that the result registers should be used as if the
type had been passed as the first argument. The implementation should
not complain if the attribute is applied inappropriately (that is, where
insufficient registers are available) it might be a template instance.

### Custom calling conventions

Some interfaces may use calling conventions that depart from the AAPCS.
Examples include:

* Using additional argument registers, for example passing an argument
  in R5, R7, R12.
* Using additional result registers, for example R0 and R1 for a
  combined divide-and-remainder routine (note that some implementations
  may be able to support this by means of a value in registers structure
  return).
* Returning results in the condition flags.
* Preserving and possibly setting the Q (saturation) bit.

### Traps: system calls, breakpoints, ...

This release of ACLE does not define how to invoke a SVC (supervisor
call), BKPT (breakpoint) and other related functionality.

One option would be to mark a function prototype with an attribute, for example

``` c
  int __attribute__((svc(0xAB))) system_call(int code, void const *params);
```

When calling the function, arguments and results would be marshaled
according to the AAPCS, the only difference being that the call would be
invoked as a trap instruction rather than a branch-and-link.

One issue is that some calls may have non-standard calling conventions.
(For example, Arm Linux system calls expect the code number to be passed
in R7.)

Another issue is that the code may vary between A32 and T32 state.
This issue could be addressed by allowing two numeric parameters in the
attribute.

### Mixed-endian data

Extensions for accessing data in different endianness have been
considered. However, this is not an issue specific to the Arm
architecture, and it seems better to wait for a lead from language
standards.

### Memory access with non-temporal hints

Supporting memory access with cacheability hints through language
extensions is being investigated. For example:

``` c
  int *__attribute__((nontemporal)) p;
```

As a type attribute, will allow indirection of p with non-temporal
cacheability hint.

## Features not considered for support

### VFP vector mode

The short vector mode of the original VFP architecture is now
deprecated, and unsupported in recent implementations of the Arm
floating-point instructions set. There is no plan to support it through
C extensions.

### Bit-banded memory access

The bit-banded memory feature of certain Cortex-M cores is now regarded
as being outside the architecture, and there is no plan to standardize
its support.

<!-- Please add new extension chapters somewhere before the “Architectural
     Extension Bridges” chapter.  In particular, the “Future directions”
     chapter should be last.  -->
