---
name: docs-md-arm-05-c-language-extensions
description: "Arm ACLE: C language extensions (vendor documentation for Arm NEON, SVE and SME)."
when: "when you need Arm ACLE: C language extensions while writing a kernel for Arm NEON, SVE and SME."
---

# C language extensions

## Data types

This section overlaps with the specification of the Arm Procedure Call
Standard, particularly [[AAPCS]](#AAPCS) (4.1). ACLE extends some of the guarantees
of C, allowing assumptions to be made in source code beyond those
permitted by Standard C.

* Plain char is unsigned, as specified in the ABI [[AAPCS]](#AAPCS) and
  [[AAPCS64]](#AAPCS64) (7.1.1).

* When pointers are 32 bits, the long type is 32 bits (ILP32 model).

* When pointers are 64 bits, the long type may be either 64 bits
  (LP64 model) or 32 bits (LLP64 model).

ACLE extends C by providing some types not present in Standard C and
defining how they are dealt with by the AAPCS. These types fall into
two groups:

* types that are defined by [header files](#header-files)

* types that are predefined by the implementation, so that
  no header file needs to be included to make use of them

The former group includes things like [vector data types](#vector-data-types),
which are defined by the header file [`<arm_neon.h>`](#arm_neon.h).

The predefined types are:

* The `__fp16` type for 16-bit floating-point values (see
 [Half-precision floating-point](#half-precision-floating-point)).

* The `__bf16` type for 16-bit brain floating-point values (see
 [Half-precision brain floating-point](#half-precision-brain-floating-point)).

* The `__mfp8` type for the modal 8-bit floating-point values (see
[Modal 8-bit floating point types](#modal-8-bit-floating-point)).

### Implementation-defined type properties

ACLE and the Arm ABI allow implementations some freedom in order to
conform to long-standing conventions in various environments. It is
suggested that implementations set suitable defaults for their
environment but allow the default to be overridden.

The signedness of a plain int bit-field is implementation-defined.

Whether the underlying type of an enumeration is minimal or at least
32-bit, is implementation-defined. The predefined macro
`__ARM_SIZEOF_MINIMAL_ENUM` should be defined as 1 or 4 according to
the size of a minimal enumeration type such as `enum { X=0 }`. An
implementation that conforms to the Arm ABI must reflect its choice in
the `Tag_ABI_enum_size build` attribute.

`wchar_t` may be 2 or 4 bytes. The predefined macro
`__ARM_SIZEOF_WCHAR_T` should be defined as the same number. An
implementation that conforms to the Arm ABI must reflect its choice in
the `Tag_ABI_PCS_wchar_t` build attribute.

## Predefined macros

Several predefined macros are defined. Generally these define features
of the Arm architecture being targeted, or how the C/C++ implementation
uses the architecture. These macros are detailed in
[Feature test macros](#feature-test-macros). All ACLE predefined macros
start with the prefix `__ARM`.

## Keyword attributes

This section is in
[**Beta** state](#support-levels) and might change or be
extended in the future.

ACLE adds several non-standard keywords to C and C++. These keywords
all start with the prefix `__arm_`. (However, not everything that
starts with `__arm_` is a keyword.)

The keywords are modeled after standard `[[…]]` attributes and
fulfill a similar role to them.  However, the C++ standard says that
“any [non-standard attribute] that is not recognized by the
implementation is ignored” `[dcl.attr.grammar]`. It is therefore not
appropriate to use standard attributes for properties that affect the
type system, that affect the binary interface of the generated code, or
that must be honored for other reasons. ACLE uses keywords for some of
these properties instead. The keywords are therefore known as
“keyword attributes”.

A keyword attribute can appear wherever a standard `[[…]]` attribute
can appear. Following the terminology of the C++ standard, a keyword
attribute “appertains” to whatever a standard attribute would appertain
to. For example, consider the placeholders A, B, C and D in the
following function declaration:

``` c
  /*A*/ void /*B*/ f /*C*/ (void) /*D*/;
```

Here:

*   Attributes in position A appertain to the function declaration `f`.

*   Attributes in position B appertain to the return type (`void`).

*   Attributes in position C appertain to the function declaration `f`,
    as for A.

*   Attributes in position D appertain to the type of `f` (`void ()(void)`).

Position A is preferred over position C for ACLE code. This is because
position A can also be used for GNU-style attributes, whereas position C
cannot.

The table below lists all the ACLE keyword attributes. The “Target” column
says what the keyword is allowed to appertain to. For example, a function
type keyword can appear in position D above, but it cannot appear in
positions A, B or C.

Keyword attributes are only guaranteed to be supported by compilers that
predefine the associated macro to a nonzero value.

<!-- Please keep this table sorted alphabetically. -->

| **Name**                                                    | **Target**            | **Predefined macro**              |
| ----------------------------------------------------------- | --------------------- | --------------------------------- |
| [`__arm_agnostic`](#arm_agnostic)                           | function type         | `__ARM_FEATURE_SME`               |
| [`__arm_locally_streaming`](#arm_locally_streaming)         | function declaration  | `__ARM_FEATURE_LOCALLY_STREAMING` |
| [`__arm_in`](#ways-of-sharing-state)                        | function type         | Argument-dependent                |
| [`__arm_inout`](#ways-of-sharing-state)                     | function type         | Argument-dependent                |
| [`__arm_new`](#arm_new)                                     | function declaration  | Argument-dependent                |
| [`__arm_out`](#ways-of-sharing-state)                       | function type         | Argument-dependent                |
| [`__arm_preserves`](#ways-of-sharing-state)                 | function type         | Argument-dependent                |
| [`__arm_streaming`](#arm_streaming)                         | function type         | `__ARM_FEATURE_SME`               |
| [`__arm_streaming_compatible`](#arm_streaming_compatible)   | function type         | `__ARM_FEATURE_SME`               |

Using a keyword attribute multiple times is equivalent to using it once.

## Intrinsics

ACLE standardizes intrinsics to access various features of the
Arm ® architecture. It also standardizes a set of [header
files](#header-files) that provide access to these intrinsics.

Whether intrinsics are macros, functions or built-in operators is
unspecified. For example:

* It is unspecified whether applying #undef to an intrinsic
  removes the name from visibility
* It is unspecified whether it is possible to take the address
  of an intrinsic

However, each argument must be evaluated at most once. So this
definition is acceptable:

``` c
  #define __rev(x) __builtin_bswap32(x)
```

but this is not:

``` c
  #define __rev(x) ((((x) & 0xff) << 24) | (((x) & 0xff00) << 8) | \
    (((x) & 0xff0000) >> 8) | ((x) >> 24))
```

### Constant arguments to intrinsics

Some intrinsics may require arguments that are constant at compile-time,
to supply data that is encoded into the immediate fields of an
instruction. Typically, these intrinsics require an
integral-constant-expression in a specified range, or sometimes a string
literal. An implementation should produce a diagnostic if the argument
does not meet the requirements.

## Header files

ACLE standardizes various header files that provide access to
[intrinsics](#intrinsics) and their associated data types.
It also standardizes [feature test macros](#feature-test-macros)
that indicate which header files are available.

Some architecture features have a dedicated header file;
for example, [`<arm_neon.h>`](#arm_neon.h) provides access to the
[Advanced SIMD (Neon) intrinsics](#advanced-simd-neon-intrinsics).
[`arm_acle.h`](#arm_acle.h) provides a catch-all for intrinsics that
do not belong to a more specific header file.

These headers behave as standard library headers; repeated inclusion has
no effect beyond the first include.

Except where noted otherwise, it is unspecified whether the ACLE headers
include the standard headers `<assert.h>`, `<stdint.h>` or
`<inttypes.h>`. However, the ACLE headers will not define the standard
type names (for example `uint32_t`) except by inclusion of the standard
headers. Arm recommends that you include the standard headers explicitly
if the associated types and macros are needed.

In C++, the following source code fragments are expected to work
correctly:

``` c
  #include <stdint.h>
  // UINT64_C not defined here since we did not set __STDC_FORMAT_MACROS
  ...
  #include <arm_neon.h>
```

and:

``` c
  #include <arm_neon.h>
  ...
  #define __STDC_FORMAT_MACROS
  #include <stdint.h>
  // ... UINT64_C is now defined
```

### `<arm_acle.h>`

`<arm_acle.h>` provides access to intrinsics that do not belong
to the more specific header files below. These intrinsics are in the
C implementation namespace and begin with double underscores. It is
unspecified whether they are available without the header being
included. When `__ARM_ACLE` is defined to `1`, the header file is
guaranteed to be available.

``` c
  #ifdef __ARM_ACLE
  #include <arm_acle.h>
  #endif /* __ARM_ACLE */
```

### `<arm_fp16.h>`

`<arm_fp16.h>` is provided to define the scalar 16-bit floating point
arithmetic intrinsics. As these intrinsics are in the user namespace,
an implementation would not normally define them until the header is
included. When `__ARM_FEATURE_FP16_SCALAR_ARITHMETIC` is defined to `1`,
the header file is available regardless of the context in which the macro
is evaluated.

``` c
  #ifdef __ARM_FEATURE_FP16_SCALAR_ARITHMETIC
  #include <arm_fp16.h>
  #endif /* __ARM_FEATURE_FP16_SCALAR_ARITHMETIC */
```

### `<arm_bf16.h>`

`<arm_bf16.h>` is provided to define the 16-bit brain floating point
arithmetic intrinsics. As these intrinsics are in the user namespace,
an implementation would not normally define them until the header is
included. When `__ARM_FEATURE_BF16` is defined to `1`, the header file is
guaranteed to be available regardless of the context in which the macro
is evaluated.

``` c
  #ifdef __ARM_FEATURE_BF16
  #include <arm_bf16.h>
  #endif /* __ARM_FEATURE_BF16 */
```

When `__ARM_BF16_FORMAT_ALTERNATIVE` is defined to `1` the only scalar
instructions available are conversion intrinsics between `bfloat16_t` and
`float32_t`.  These instructions are:

* `vcvth_bf16_f32` (convert float32_t to bfloat16_t)
* `vcvtah_f32_bf16` (convert bfloat16_t to float32_t)

### `<arm_neon.h>`

`<arm_neon.h>` is provided to define the [Advanced SIMD (Neon)
intrinsics](#advanced-simd-neon-intrinsics) and associated
[data types](#vector-data-types). As these intrinsics and data types are
in the user namespace, an implementation would not normally define them
until the header is included. When `__ARM_NEON` is defined to `1`,
the header file is available regardless of the context in which the macro is
evaluated.


``` c
  #ifdef __ARM_NEON
  #include <arm_neon.h>
  #endif /* __ARM_NEON */
```

Including `<arm_neon.h>` will also cause the following header files
to be included, if the header files are available:

* [`<arm_fp16.h>`](#arm_fp16.h)
* [`<arm_bf16.h>`](#arm_bf16.h)

<span id="arm_sve.h"></span>

### `<arm_sve.h>`

`<arm_sve.h>` defines data types and intrinsics for SVE and its
extensions; see [SVE language extensions and
intrinsics](#sve-language-extensions-and-intrinsics) for details.
It also defines intrinsics for SME features that do not access ZA or ZT0.

When `__ARM_FEATURE_SVE` is defined to `1`, the header file is available
regardless of the context in which the macro is evaluated.

``` c
  #ifdef __ARM_FEATURE_SVE
  #include <arm_sve.h>
  #endif /* __ARM_FEATURE_SVE */
```

Including `<arm_sve.h>` also includes the following header files:

* `<stdint.h>`
* `<stdbool.h>` (for C only)
* [`<arm_fp16.h>`](#arm_fp16.h)
* [`<arm_bf16.h>`](#arm_bf16.h) (if available)

### `<arm_neon_sve_bridge.h>`

`<arm_neon_sve_bridge.h>` defines intrinsics for moving data between
Neon and SVE vector types; see [Neon-SVE Bridge](#neon-sve-bridge)
for details. Before including the header, you should test the
`__ARM_NEON_SVE_BRIDGE` macro.
:

``` c
  #ifdef __ARM_NEON_SVE_BRIDGE
  #include <arm_neon_sve_bridge.h>
  #endif /* __ARM_NEON_SVE_BRIDGE */
```

Including `<arm_neon_sve_bridge.h>` will also include
[`<arm_neon.h>`](#arm_neon.h) and [`<arm_sve.h>`](#arm_sve.h).

### `<arm_mve.h>`

`<arm_mve.h>` is provided to define the [M-profile Vector Extension
(MVE) intrinsics](#m-profile-vector-extension-mve-intrinsics) and associated
data types. The data types occupy the user namespace. By default the
intrinsics occupy both the user namespace and the `__arm_` namespace;
defining `__ARM_MVE_PRESERVE_USER_NAMESPACE` will hide the definition of
the user namespace variants.

The `__ARM_FEATURE_MVE` macro should be tested before including the
header:

``` c
  #if (__ARM_FEATURE_MVE & 3) == 3
  #include <arm_mve.h>
  /* MVE integer and floating point intrinsics are now available to use.  */
  #elif __ARM_FEATURE_MVE & 1
  #include <arm_mve.h>
  /* MVE integer intrinsics are now available to use.  */
  #endif
```

### `<arm_sme.h>`

The specification for SME is in
[**Beta** state](#support-levels) and may
change or be extended in the future.

`<arm_sme.h>` defines SME intrinsics that access ZA or ZT0, and declares SME
support functions and streaming vector length intrinsics. Include it to use
these intrinsics and functions; see
[SME language extensions and intrinsics](#sme-language-extensions-and-intrinsics)
for details. When `__ARM_FEATURE_SME` is defined to `1`, the header file is
available regardless of the context in which the macro is evaluated.

``` c
  #ifdef __ARM_FEATURE_SME
  #include <arm_sme.h>
  #endif
```

Including `<arm_sme.h>` also includes [`<arm_sve.h>`](#arm_sve.h).
This means that including `<arm_sme.h>` makes the intrinsics defined
in either header file available.

### Predefined feature macros and header files

Evaluating a feature macro returns the availability of intrinsics and inline
assembly for that feature, but no assumptions should be made on the order or
context in which the preprocessor macros are evaluated. For example:

``` c
    __attribute__((target("+sve")))
    void foo() {
    #ifdef __ARM_FEATURE_SVE
      // The user should make no assumptions that the target attribute
      // enables the __ARM_FEATURE_SVE macro.
    #endif
}
```

The compiler might add additional restrictions to the intrinsics beyond what is
captured by the ACLE macros depending on the context in which the intrinsics
are used. For example:

``` c
    #include <arm_sme.h>
    void foo(svbool_t pg, void *ptr, uint32_t slice_base) {
    #ifdef __ARM_FEATURE_SME
      svst1_hor_za8(0, slice_base, pg, ptr);
    #endif
    }
```

If `__ARM_FEATURE_SME` evaluates to `true` the SME intrinsic `svst1_hor_za8`
is available, but `foo` might still fail to compile because the call does not
occur in a [streaming statement](#streaming-statement).

## Attributes

GCC-style attributes are provided to annotate types, objects and
functions with extra information, such as alignment. These attributes
are defined in [Attributes and pragmas](#attributes-and-pragmas).

## Implementation strategies

An implementation may choose to define all the ACLE non-Neon intrinsics
as true compiler intrinsics, that is, built-in functions. The `<arm_acle.h>`
header would then have no effect.

Alternatively, `<arm_acle.h>` could define the ACLE intrinsics in terms
of already supported features of the implementation, for example compiler
intrinsics with other names, or inline functions using inline assembler.

### Half-precision floating-point

ACLE defines the `__fp16` type, which can be used for half-precision
(16-bit) floating-point in one of two formats. The binary16 format defined
in [[IEEE-FP]](#IEEE-FP), and referred to as *IEEE* format, and an alternative format,
defined by Arm, which extends the range by removing support for
infinities and NaNs, referred to as *alternative* format. Both formats are
described in [[ARMARM]](#ARMARM) (A2.7.4), [[ARMARMv8]](#ARMARMv8) (A1.4.2).

Toolchains are not required to support the alternative format, and use
of the alternative format precludes use of the ISO/IEC TS 18661:3 [[CFP15]](#CFP15)
`_Float16` type and the Armv8.2-A 16-bit floating-point extensions. For
these reasons, Arm deprecates the use of the alternative format for
half precision in ACLE.

The format in use can be selected at runtime but ACLE assumes it
is fixed for the life of a program. If the `__fp16` type is available,
one of `__ARM_FP16_FORMAT_IEEE` and `__ARM_FP16_FORMAT_ALTERNATIVE` will
be defined to indicate the format in use. An implementation conforming to
the Arm ABI will set the `Tag_ABI_FP_16bit_format` build attribute.

The `__fp16` type can be used in two ways; using the intrinsics ACLE
defines when the Armv8.2-A 16-bit floating point extensions are available,
and using the standard C operators. When using standard C operators,
values of `__fp16` type promote to (at least) float when used in
arithmetic operations, in the same way that values of char or short types
promote to int. There is no support for arithmetic directly on `__fp16`
values using standard C operators.

``` c
  void add(__fp16 a, __fp16 b) {
    a + b; /* a and b are promoted to (at least) float.
              Operation takes place with (at least) 32-bit precision.  */
    vaddh_f16 (a, b); /* a and b are not promoted.
                         Operation takes place with 16-bit precision.  */
  }
```

Armv8 introduces floating point instructions to convert 64-bit to 16-bit,
that is, from double to `__fp16`. They are not available in earlier
architectures, therefore have to rely on emulation libraries or a
sequence of instructions to achieve the conversion.

Providing emulation libraries for half-precision floating point
conversions when not implemented in hardware is implementation-defined.

``` c
  double xd;
  __fp16 xs = (float)xd;
```

rather than:

``` c
  double xd;
  __fp16 xs = xd;
```

In some older implementations, `__fp16` cannot be used as an argument or
result type, though it can be used as a field in a structure passed as
an argument or result, or passed via a pointer. The predefined macro
`__ARM_FP16_ARGS` should be defined if `__fp16` can be used as an
argument and result. C++ name mangling is Dh as defined in [[cxxabi]](#cxxabi),
and is the same for both the IEEE and alternative formats.

In this example, the floating-point addition is done in single (32-bit)
precision:

``` c
  void add(__fp16 *z, __fp16 const *x, __fp16 const *y, int n) {
     int i;
     for (i = 0; i < n; ++i) z[i] = x[i] + y[i];
   }
```

### Relationship between `__fp16` and ISO/IEC TS 18661

ISO/IEC TS 18661-3 [[CFP15]](#CFP15) is a published extension to [[C11]](#C11) which
describes a language binding for the [[IEEE-FP]](#IEEE-FP) standard for floating
point arithmetic. This language binding introduces a mapping to an
unlimited number of interchange and extended floating-point types, on
which binary arithmetic is well defined. These types are of the
form `_FloatN`, where `N` gives size in bits of the type.

One instantiation of the interchange types introduced by [[CFP15]](#CFP15) is
the `_Float16` type. ACLE defines the `__fp16` type as a storage
and interchange only format, on which arithmetic operations are defined
to first promote to a type with at least the range and precision of
float.

This has implications for the result of operations which would result
in rounding had the operation taken place in a native 16-bit type. As
software may rely on this behavior for correctness, arithmetic
operations on `__fp16` are defined to promote even when the
Armv8.2-A fp16 extension is available.

Arm recommends that portable software is written to use the `_Float16`
type defined in [[CFP15]](#CFP15).

Type conversion between a value of type `__fp16` and a value of type
`_Float16` leaves the object representation of the converted value unchanged.

When `__ARM_FP16_FORMAT_IEEE == 1`, this has no effect on the value of
the object. However, as the representation of certain values has a different
meaning when using the Arm alternative format for 16-bit floating point
values [[ARMARM]](#ARMARM) (A2.7.4) [[ARMARMv8]](#ARMARMv8) (A1.4.2), when
`__ARM_FP16_FORMAT_ALTERNATIVE == 1` the type conversion may introduce
or remove infinity or NaN representations.

Arm recommends that software implementations warn on type conversions
between `__fp16` and `_Float16` if `__ARM_FP16_FORMAT_ALTERNATIVE == 1`.

In an arithmetic operation where one operand is of `__fp16` type and
the other is of `_Float16 type`, the `_Float16` type is first
converted to `__fp16` type following the rules above, and then the
operation is completed as if both operands were of `__fp16` type.

[[CFP15]](#CFP15) and [[C11]](#C11) do not define vector types, however many C
implementations do provide these extensions. Where they exist, type
conversion between a value of type vector of `__fp16` and a value of
type vector of `_Float16` leaves the object representation of the
converted value unchanged.

ACLE does not define vector of `_Float16` types.

### Half-precision brain floating-point

ACLE defines the `__bf16` type, which can be used for half-precision
(16-bit) brain floating-point in an alternative format,
defined by Arm, which closely resembles the IEEE 754 single-precision floating
point format.

The `__bf16` type is only available when the
`__ARM_BF16_FORMAT_ALTERNATIVE` feature macro is defined.
When it is available it can only be used by the ACLE intrinsics
; it cannot be used with standard C operators.
It is expected that arithmetic using standard C operators be used using a
single-precision floating point format and the value be converted to `__bf16`
when required using ACLE intrinsics.

Armv8.2-A introduces floating point instructions to convert 32-bit to brain
16-bit, that is, from float to `__bf16`. They are not available in earlier
architectures, therefore have to rely on emulation libraries or a
sequence of instructions to achieve the conversion.

Providing emulation libraries for half-precision floating point
conversions when not implemented in hardware is implementation-defined.

### Modal 8-bit floating-point

ACLE defines the `__mfp8` type, which can be used for the E5M2 and E4M3
8-bit floating-point formats ("FP8"). It is a storage and interchange
only type with no arithmetic operations other than intrinsic calls.
