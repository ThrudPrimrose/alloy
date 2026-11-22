---
name: docs-md-arm-10-data-processing-intrinsics
description: "Arm ACLE: Data-processing intrinsics (vendor documentation for Arm NEON, SVE and SME)."
when: "when you need Arm ACLE: Data-processing intrinsics while writing a kernel for Arm NEON, SVE and SME."
---

# Data-processing intrinsics

The intrinsics in this section are provided for algorithm optimization.

The `<arm_acle.h>` header should be included before using these
intrinsics.

Implementations are not required to introduce precisely the instructions
whose names match the intrinsics. However, implementations should aim to
ensure that a computation expressed compactly with intrinsics will
generate a similarly compact sequence of machine code. In general, C's
as-if rule [[C99]](#C99) (5.1.2.3) applies, meaning that the compiled code must
behave *as if* the instruction had been generated.

In general, these intrinsics are aimed at DSP algorithm optimization on
M-profile and R-profile. Use on A-profile is deprecated. However, the
miscellaneous intrinsics and CRC32 intrinsics described in [Miscellaneous
data-processing intrinsics](#miscellaneous-data-processing-intrinsics)
and [CRC32 intrinsics](#crc32-intrinsics) respectively are suitable
for all profiles.

## Programmer's model of global state

### The Q (saturation) flag

The Q flag is a cumulative (sticky) saturation bit in the APSR
(Application Program Status Register) indicating that an operation
saturated, or in some cases, overflowed. It is set on saturation by most
intrinsics in the DSP and SIMD intrinsic sets, though some SIMD
intrinsics feature saturating operations which do not set the Q flag.

[[AAPCS]](#AAPCS) (5.1.1) states:

The N, Z, C, V and Q flags (bits 27-31) and the GE[3:0] bits (bits
16-19) are undefined on entry to or return from a public interface.

Note that this does not state that these bits (in particular the Q flag)
are undefined across any C/C++ function call boundary only across a
public interface. The Q and GE bits could be manipulated in
well-defined ways by local functions, for example when constructing
functions to be used in DSP algorithms.

Implementations must avoid introducing instructions (such as SSAT/USAT,
or SMLABB) which affect the Q flag, if the programmer is testing whether
the Q flag was set by explicit use of intrinsics and if the
implementation's introduction of an instruction may affect the value
seen. The implementation might choose to model the definition and use
(liveness) of the Q flag in the way that it models the liveness of any
visible variable, or it might suppress introduction of Q-affecting
instructions in any routine in which the Q flag is tested.

ACLE does not define how or whether the Q flag is preserved across
function call boundaries. (This is seen as an area for future
specification.)

In general, the Q flag should appear to C/C++ code in a similar way to
the standard floating-point cumulative exception flags, as global (or
thread-local) state that can be tested, set or reset through an API.

The following intrinsics are available when `__ARM_FEATURE_QBIT` is
defined:

int ```__saturation_occurred(void);```

Returns 1 if the Q flag is set, 0 if not.

void ```__set_saturation_occurred(int);```

Sets or resets the Q flag according to the LSB of the value.
`__set_saturation_occurred(0)` might be used before performing a
sequence of operations after which the Q flag is tested. (In general,
the Q flag cannot be assumed to be unset at the start of a function.)

void ```__ignore_saturation(void);```

This intrinsic is a hint and may be ignored. It indicates to the
compiler that the value of the Q flag is not live (needed) at or
subsequent to the program point at which the intrinsic occurs. It may
allow the compiler to remove preceding instructions, or to change the
instruction sequence in such a way as to result in a different value of
the Q flag. (A specific example is that it may recognize clipping idioms
in C code and implement them with an instruction such as SSAT that may
set the Q flag.)

### The GE flags

The GE (Greater than or Equal to) flags are four bits in the APSR. They
are used with the 32-bit SIMD intrinsics described in
[32-bit SIMD Operations](#32-bit-simd-operations).

There are four GE flags, one for each 8-bit lane of a 32-bit SIMD
operation. Certain non-saturating 32-bit SIMD intrinsics set the GE bits
to indicate overflow of addition or subtraction. For 4x8-bit operations
the GE bits are set one for each byte. For 2x16-bit operations the GE
bits are paired together, one for the high halfword and the other pair
for the low halfword. The only supported way to read or use the GE bits
(in this specification) is by using the `__sel` intrinsic, see
[Parallel selection](#parallel-selection).

### Floating-point environment

An implementation should implement the features of <fenv.h> for
accessing the floating-point runtime environment. Programmers should use
this rather than accessing the VFP FPSCR directly. For example, on a
target supporting VFP the cumulative exception flags (for example IXC, OFC) can
be read from the FPSCR by using the fetestexcept() function, and the
rounding mode (RMode) bits can be read using the fegetround() function.

ACLE does not support changing the DN, FZ or AHP bits at runtime.

VFP short vector mode (enabled by setting the Stride and Len bits) is
deprecated, and is unavailable on later VFP implementations. ACLE
provides no support for this mode.

## Miscellaneous data-processing intrinsics

The following intrinsics perform general data-processing operations.
They have no effect on global state.

\[Note: documentation of the `__nop` intrinsic has moved to [NOP](#nop)]

For completeness and to aid portability between LP64 and LLP64
models, ACLE also defines intrinsics with `l` suffix.

``` c
  uint32_t __ror(uint32_t x, uint32_t y);
  unsigned long __rorl(unsigned long x, uint32_t y);
  uint64_t __rorll(uint64_t x, uint32_t y);
```

Rotates the argument `x` right by `y` bits. `y` can take any value.
These intrinsics are available on all targets.

``` c
  unsigned int __clz(uint32_t x);
  unsigned int __clzl(unsigned long x);
  unsigned int __clzll(uint64_t x);
```

Returns the number of leading zero bits in `x`. When `x` is zero it
returns the argument width, that is, 32 or 64. These intrinsics are available
on all targets. On targets without the CLZ instruction it should be
implemented as an instruction sequence or a call to such a sequence. A
suitable sequence can be found in [Warren](#Warren) (fig. 5-7). Hardware support
for these intrinsics is indicated by `__ARM_FEATURE_CLZ`.

``` c
  unsigned int __cls(uint32_t x);
  unsigned int __clsl(unsigned long x);
  unsigned int __clsll(uint64_t x);
```

Returns the number of leading sign bits in `x`. When `x` is zero it
returns the argument width - 1, that is, 31 or 63. These intrinsics are
available on all targets. On targets without the CLZ instruction it
should be implemented as an instruction sequence or a call to such a
sequence. Fast hardware implementation (using a CLS instruction or a short code
sequence involving the CLZ instruction) is indicated by
`__ARM_FEATURE_CLZ`.

``` c
  uint32_t __rev(uint32_t);
  unsigned long __revl(unsigned long);
  uint64_t __revll(uint64_t);
```

Reverses the byte order within a word or doubleword. These intrinsics
are available on all targets and should be expanded to an efficient
straight-line code sequence on targets without byte reversal
instructions.

``` c
  uint32_t __rev16(uint32_t);
  unsigned long __rev16l(unsigned long);
  uint64_t __rev16ll(uint64_t);
```

Reverses the byte order within each halfword of a word. For example,
`0x12345678` becomes `0x34127856`. These intrinsics are available on
all targets and should be expanded to an efficient straight-line code
sequence on targets without byte reversal instructions.

``` c
  int16_t __revsh(int16_t);
```

Reverses the byte order in a 16-bit value and returns the signed 16-bit result.
For example, `0x0080` becomes `0x8000`. This intrinsic is available on
all targets and should be expanded to an efficient straight-line code
sequence on targets without byte reversal instructions.

``` c
  uint32_t __rbit(uint32_t x);
  unsigned long __rbitl(unsigned long x);
  uint64_t __rbitll(uint64_t x);
```

Reverses the bits in `x`. These intrinsics are only available on targets
with the RBIT instruction.

### Examples

``` c
  #ifdef __ARM_BIG_ENDIAN
  #define htonl(x) (uint32_t)(x)
  #define htons(x) (uint16_t)(x)
  #else /* little-endian */
  #define htonl(x) __rev(x)
  #define htons(x) (uint16_t)__revsh(x)
  #endif /* endianness */
  #define ntohl(x) htonl(x)
  #define ntohs(x) htons(x)

  /* Count leading sign bits */
  inline unsigned int count_sign(int32_t x) { return __clz(x ^ (x << 1)); }

  /* Count trailing zeroes */
  inline unsigned int count_trail(uint32_t x) {
  #if (__ARM_ARCH >= 6 && __ARM_ISA_THUMB >= 2) || __ARM_ARCH >= 7
  /* RBIT is available */
    return __clz(__rbit(x));
  #else
    unsigned int n = __clz(x & -x);   /* get the position of the last bit */
    return n == 32 ? n : (31-n);
  #endif
  }
```

## 16-bit multiplications

The intrinsics in this section provide direct access to the 16x16 and
16x32 bit multiplies introduced in Armv5E. Compilers are also
encouraged to exploit these instructions from C code. These intrinsics
are available when `__ARM_FEATURE_DSP` is defined, and are not
available on non-5E targets. These multiplies cannot overflow.

``` c
  int32_t __smulbb(int32_t, int32_t);
```

Multiplies two 16-bit signed integers, that is, the low halfwords of the
operands.

``` c
  int32_t __smulbt(int32_t, int32_t);
```

Multiplies the low halfword of the first operand and the high halfword
of the second operand.

``` c
  int32_t __smultb(int32_t, int32_t);
```

Multiplies the high halfword of the first operand and the low halfword
of the second operand.

``` c
  int32_t __smultt(int32_t, int32_t);
```

Multiplies the high halfwords of the operands.

``` c
  int32_t __smulwb(int32_t, int32_t);
```

Multiplies the 32-bit signed first operand with the low halfword (as a
16-bit signed integer) of the second operand. Return the top 32 bits of
the 48-bit product.

``` c
  int32_t __smulwt(int32_t, int32_t);
```

Multiplies the 32-bit signed first operand with the high halfword (as a
16-bit signed integer) of the second operand. Return the top 32 bits of
the 48-bit product.

## Saturating intrinsics

### Width-specified saturation intrinsics

These intrinsics are available when `__ARM_FEATURE_SAT` is defined.
They saturate a 32-bit value at a given bit position. The saturation
width must be an integral constant expression |--| see
[Constant arguments to intrinsics](#constant-arguments-to-intrinsics).

``` c
  int32_t __ssat(int32_t, /*constant*/ unsigned int);
```

Saturates a signed integer to the given bit width in the range 1 to 32.
For example, the result of saturation to 8-bit width will be in the
range -128 to 127. The Q flag is set if the operation saturates.

``` c
  uint32_t __usat(int32_t, /*constant*/ unsigned int);
```

Saturates a signed integer to an unsigned (non-negative) integer of a
bit width in the range 0 to 31. For example, the result of saturation to
8-bit width is in the range 0 to 255, with all negative inputs going to
zero. The Q flag is set if the operation saturates.

### Saturating addition and subtraction intrinsics

These intrinsics are available when `__ARM_FEATURE_DSP` is defined.

The saturating intrinsics operate on 32-bit signed integer data. There
are no special saturated or fixed point types.

``` c
  int32_t __qadd(int32_t, int32_t);
```

Adds two 32-bit signed integers, with saturation. Sets the Q flag if the
addition saturates.

``` c
  int32_t __qsub(int32_t, int32_t);
```

Subtracts two 32-bit signed integers, with saturation. Sets the Q flag
if the subtraction saturates.

``` c
  int32_t __qdbl(int32_t);
```

Doubles a signed 32-bit number, with saturation. `__qdbl(x)` is equal to
`__qadd(x,x)` except that the argument x is evaluated only once. Sets
the Q flag if the addition saturates.

### Accumulating multiplications

These intrinsics are available when `__ARM_FEATURE_DSP` is defined.

``` c
  int32_t __smlabb(int32_t, int32_t, int32_t);
```

Multiplies two 16-bit signed integers, the low halfwords of the first
two operands, and adds to the third operand. Sets the Q flag if the
addition overflows. (Note that the addition is the usual 32-bit modulo
addition which wraps on overflow, not a saturating addition. The
multiplication cannot overflow.)

``` c
  int32_t __smlabt(int32_t, int32_t, int32_t);
```

Multiplies the low halfword of the first operand and the high halfword
of the second operand, and adds to the third operand, as for `__smlabb`.

``` c
  int32_t __smlatb(int32_t, int32_t, int32_t);
```

Multiplies the high halfword of the first operand and the low halfword
of the second operand, and adds to the third operand, as for `__smlabb`.

``` c
  int32_t __smlatt(int32_t, int32_t, int32_t);
```

Multiplies the high halfwords of the first two operands and adds to the
third operand, as for `__smlabb`.

``` c
  int32_t __smlawb(int32_t, int32_t, int32_t);
```

Multiplies the 32-bit signed first operand with the low halfword (as a
16-bit signed integer) of the second operand. Adds the top 32 bits of
the 48-bit product to the third operand. Sets the Q flag if the addition
overflows. (See note for `__smlabb`).

``` c
  int32_t __smlawt(int32_t, int32_t, int32_t);
```

Multiplies the 32-bit signed first operand with the high halfword (as a
16-bit signed integer) of the second operand and adds the top 32 bits of
the 48-bit result to the third operand as for `__smlawb`.

### Examples

The ACLE DSP intrinsics can be used to define ETSI/ITU-T basic
operations [[G.191]](#G.191):

``` c
    #include <arm_acle.h>
    inline int32_t L_add(int32_t x, int32_t y) { return __qadd(x, y); }
    inline int32_t L_negate(int32_t x) { return __qsub(0, x); }
    inline int32_t L_mult(int16_t x, int16_t y) { return __qdbl(x*y); }
    inline int16_t add(int16_t x, int16_t y) { return (int16_t)(__qadd(x<<16, y<<16) >> 16); }
    inline int16_t norm_l(int32_t x) { return __clz(x ^ (x<<1)) & 31; }
    ...
```

This example assumes the implementation preserves the Q flag on return
from an inline function.

<span id="32-bit-simd-operations"></span>

## 32-bit SIMD Operations

### Availability

Armv6 introduced instructions to perform 32-bit SIMD operations (that is,
two 16-bit operations or four 8-bit operations) on the Arm
general-purpose registers. These instructions are not related to the
much more versatile Advanced SIMD (Neon) extension, whose support is
described in [Advanced SIMD (Neon) intrinsics](#advanced-simd-neon-intrinsics).

The 32-bit SIMD intrinsics are available on targets featuring Armv6 and
upwards, including the A and R profiles. In the M profile they are
available in the Armv7E-M architecture. Availability of the 32-bit SIMD
intrinsics implies availability of the saturating intrinsics.

Availability of the SIMD intrinsics is indicated by the
`__ARM_FEATURE_SIMD32` predefine.

To access the intrinsics, the `<arm_acle.h>` header should be included.

### Data types for 32-bit SIMD intrinsics

The header `<arm_acle.h>` should be included before using these
intrinsics.

The SIMD intrinsics generally operate on and return 32-bit words
consisting of two 16-bit or four 8-bit values. These are represented as
`int16x2_t` and `int8x4_t` below for illustration. Some intrinsics also
feature scalar accumulator operands and/or results.

When defining the intrinsics, implementations can define SIMD operands
using a 32-bit integral type (such as `unsigned int`).

The header `<arm_acle.h>` defines typedefs `int16x2_t`, `uint16x2_t`,
`int8x4_t`, and `uint8x4_t`. These should be defined as 32-bit integral
types of the appropriate sign. There are no intrinsics provided to pack
or unpack values of these types. This can be done with shifting and
masking operations.

### Use of the Q flag by 32-bit SIMD intrinsics

Some 32-bit SIMD instructions may set the Q flag described in
[The Q (saturation) flag](#the-q-saturation-flag). The behavior of the
intrinsics matches that of the instructions.

Generally, instructions that perform lane-by-lane saturating operations
do not set the Q flag. For example, `__qadd16` does not set the Q flag,
even if saturation occurs in one or more lanes.

The explicit saturation operations `__ssat` and `__usat` set the Q flag
if saturation occurs. Similarly, `__ssat16` and `__usat16` set the Q
flag if saturation occurs in either lane.

Some instructions, such as `__smlad`, set the Q flag if overflow occurs
on an accumulation, even though the accumulation is not a saturating
operation (that is, does not clip its result to the limits of the type).

### Parallel 16-bit saturation

These intrinsics are available when `__ARM_FEATURE_SIMD32` is defined.
They saturate two 16-bit values to a given bit width as for the `__ssat`
and `__usat` intrinsics defined in [Width-specified saturation
intrinsics](#width-specified-saturation-intrinsics).

``` c
  int16x2_t __ssat16(int16x2_t, /*constant*/ unsigned int);
```

Saturates two 16-bit signed values to a width in the range 1 to 16. The
Q flag is set if either operation saturates.

``` c
  int16x2_t __usat16(int16x2_t, /*constant */ unsigned int);
```

Saturates two 16-bit signed values to a bit width in the range 0 to 15.
The input values are signed and the output values are non-negative, with
all negative inputs going to zero. The Q flag is set if either operation
saturates.

### Packing and unpacking

These intrinsics are available when `__ARM_FEATURE_SIMD32` is defined.

``` c
  int16x2_t __sxtab16(int16x2_t, int8x4_t);
```

Two values (at bit positions 0..7 and 16..23) are extracted from the
second operand, sign-extended to 16 bits, and added to the first
operand.

``` c
  int16x2_t __sxtb16(int8x4_t);
```

Two values (at bit positions 0..7 and 16..23) are extracted from the
first operand, sign-extended to 16 bits, and returned as the result.

``` c
  uint16x2_t __uxtab16(uint16x2_t, uint8x4_t);
```

Two values (at bit positions 0..7 and 16..23) are extracted from the
second operand, zero-extended to 16 bits, and added to the first
operand.

``` c
  uint16x2_t __uxtb16(uint8x4_t);
```

Two values (at bit positions 0..7 and 16..23) are extracted from the
first operand, zero-extended to 16 bits, and returned as the result.

### Parallel selection

This intrinsic is available when `__ARM_FEATURE_SIMD32` is defined.

``` c
  uint8x4_t __sel(uint8x4_t, uint8x4_t);
```

Selects each byte of the result from either the first operand or the
second operand, according to the values of the GE bits. For each result
byte, if the corresponding GE bit is set then the byte from the first
operand is used, otherwise the byte from the second operand is used.
Because of the way that `int16x2_t` operations set two (duplicate) GE
bits per value, the `__sel` intrinsic works equally well on
`(u)int16x2_t` and `(u)int8x4_t` data.

### Parallel 8-bit addition and subtraction

These intrinsics are available when `__ARM_FEATURE_SIMD32` is defined.
Each intrinsic performs 8-bit parallel addition or subtraction. In some
cases the result may be halved or saturated.

``` c
  int8x4_t __qadd8(int8x4_t, int8x4_t);
```

4x8-bit addition, saturated to the range `-2**7` to `2**7-1`.

``` c
  int8x4_t __qsub8(int8x4_t, int8x4_t);
```

4x8-bit subtraction, with saturation.

``` c
  int8x4_t __sadd8(int8x4_t, int8x4_t);
```

4x8-bit signed addition. The GE bits are set according to the results.

``` c
  int8x4_t __shadd8(int8x4_t, int8x4_t);
```

4x8-bit signed addition, halving the results.

``` c
  int8x4_t __shsub8(int8x4_t, int8x4_t);
```

4x8-bit signed subtraction, halving the results.

``` c
  int8x4_t __ssub8(int8x4_t, int8x4_t);
```

4x8-bit signed subtraction. The GE bits are set according to the
results.

``` c
  uint8x4_t __uadd8(uint8x4_t, uint8x4_t);
```

4x8-bit unsigned addition. The GE bits are set according to the results.

``` c
  uint8x4_t __uhadd8(uint8x4_t, uint8x4_t);
```

4x8-bit unsigned addition, halving the results.

``` c
  uint8x4_t __uhsub8(uint8x4_t, uint8x4_t);
```

4x8-bit unsigned subtraction, halving the results.

``` c
  uint8x4_t __uqadd8(uint8x4_t, uint8x4_t);
```

4x8-bit unsigned addition, saturating to the range `0` to `2**8-1`.

``` c
  uint8x4_t __uqsub8(uint8x4_t, uint8x4_t);
```

4x8-bit unsigned subtraction, saturating to the range `0` to `2**8-1`.

``` c
  uint8x4_t __usub8(uint8x4_t, uint8x4_t);
```

4x8-bit unsigned subtraction. The GE bits are set according to the
results.

### Sum of 8-bit absolute differences

These intrinsics are available when `__ARM_FEATURE_SIMD32` is defined.
They perform an 8-bit sum-of-absolute differences operation, typically
used in motion estimation.

``` c
  uint32_t __usad8(uint8x4_t, uint8x4_t);
```

Performs 4x8-bit unsigned subtraction, and adds the absolute values of
the differences together, returning the result as a single unsigned
integer.

``` c
  uint32_t __usada8(uint8x4_t, uint8x4_t, uint32_t);
```

Performs 4x8-bit unsigned subtraction, adds the absolute values of the
differences together, and adds the result to the third operand.

### Parallel 16-bit addition and subtraction

These intrinsics are available when `__ARM_FEATURE_SIMD32` is defined.
Each intrinsic performs 16-bit parallel addition and/or subtraction. In
some cases the result may be halved or saturated.

``` c
  int16x2_t __qadd16(int16x2_t, int16x2_t);
```

2x16-bit addition, saturated to the range `-2**15` to `2**15-1`.

``` c
  int16x2_t __qasx(int16x2_t, int16x2_t);
```

Exchanges halfwords of second operand, adds high halfwords and subtracts
low halfwords, saturating in each case.

``` c
  int16x2_t __qsax(int16x2_t, int16x2_t);
```

Exchanges halfwords of second operand, subtracts high halfwords and adds
low halfwords, saturating in each case.

``` c
  int16x2_t __qsub16(int16x2_t, int16x2_t);
```

2x16-bit subtraction, with saturation.

``` c
  int16x2_t __sadd16(int16x2_t, int16x2_t);
```

2x16-bit signed addition. The GE bits are set according to the results.

``` c
  int16x2_t __sasx(int16x2_t, int16x2_t);
```

Exchanges halfwords of the second operand, adds high halfwords and
subtracts low halfwords. The GE bits are set according to the results.

``` c
  int16x2_t __shadd16(int16x2_t, int16x2_t);
```

2x16-bit signed addition, halving the results.

``` c
  int16x2_t __shasx(int16x2_t, int16x2_t);
```

Exchanges halfwords of the second operand, adds high halfwords and
subtract low halfwords, halving the results.

``` c
  int16x2_t __shsax(int16x2_t, int16x2_t);
```

Exchanges halfwords of the second operand, subtracts high halfwords and
add low halfwords, halving the results.

``` c
  int16x2_t __shsub16(int16x2_t, int16x2_t);
```

2x16-bit signed subtraction, halving the results.

``` c
  int16x2_t __ssax(int16x2_t, int16x2_t);
```

Exchanges halfwords of the second operand, subtracts high halfwords and
adds low halfwords. The GE bits are set according to the results.

``` c
  int16x2_t __ssub16(int16x2_t, int16x2_t);
```

2x16-bit signed subtraction. The GE bits are set according to the
results.

``` c
  uint16x2_t __uadd16(uint16x2_t, uint16x2_t);
```

2x16-bit unsigned addition. The GE bits are set according to the
results.

``` c
  uint16x2_t __uasx(uint16x2_t, uint16x2_t);
```

Exchanges halfwords of the second operand, adds high halfwords and
subtracts low halfwords. The GE bits are set according to the results of
unsigned addition.

``` c
  uint16x2_t __uhadd16(uint16x2_t, uint16x2_t);
```

2x16-bit unsigned addition, halving the results.

``` c
  uint16x2_t __uhasx(uint16x2_t, uint16x2_t);
```

Exchanges halfwords of the second operand, adds high halfwords and
subtracts low halfwords, halving the results.

``` c
  uint16x2_t __uhsax(uint16x2_t, uint16x2_t);
```

Exchanges halfwords of the second operand, subtracts high halfwords and
adds low halfwords, halving the results.

``` c
  uint16x2_t __uhsub16(uint16x2_t, uint16x2_t);
```

2x16-bit unsigned subtraction, halving the results.

``` c
  uint16x2_t __uqadd16(uint16x2_t, uint16x2_t);
```

2x16-bit unsigned addition, saturating to the range `0` to `2**16-1`.

``` c
  uint16x2_t __uqasx(uint16x2_t, uint16x2_t);
```

Exchanges halfwords of the second operand, and performs saturating
unsigned addition on the high halfwords and saturating unsigned
subtraction on the low halfwords.

``` c
  uint16x2_t __uqsax(uint16x2_t, uint16x2_t);
```

Exchanges halfwords of the second operand, and performs saturating
unsigned subtraction on the high halfwords and saturating unsigned
addition on the low halfwords.

``` c
  uint16x2_t __uqsub16(uint16x2_t, uint16x2_t);
```

2x16-bit unsigned subtraction, saturating to the range `0` to `2**16-1`.

``` c
  uint16x2_t __usax(uint16x2_t, uint16x2_t);
```

Exchanges the halfwords of the second operand, subtracts the high
halfwords and adds the low halfwords. Sets the GE bits according to the
results of unsigned addition.

``` c
  uint16x2_t __usub16(uint16x2_t, uint16x2_t);
```

2x16-bit unsigned subtraction. The GE bits are set according to the
results.

### Parallel 16-bit multiplication

These intrinsics are available when `__ARM_FEATURE_SIMD32` is defined.
Each intrinsic performs two 16-bit multiplications.

``` c
  int32_t __smlad(int16x2_t, int16x2_t, int32_t);
```

Performs 2x16-bit multiplication and adds both results to the third
operand. Sets the Q flag if the addition overflows. (Overflow cannot
occur during the multiplications.)

``` c
  int32_t __smladx(int16x2_t, int16x2_t, int32_t);
```

Exchanges the halfwords of the second operand, performs 2x16-bit
multiplication, and adds both results to the third operand. Sets the Q
flag if the addition overflows. (Overflow cannot occur during the
multiplications.)

``` c
  int64_t __smlald(int16x2_t, int16x2_t, int64_t);
```

Performs 2x16-bit multiplication and adds both results to the 64-bit
third operand. Overflow in the addition is not detected.

``` c
  int64_t __smlaldx(int16x2_t, int16x2_t, int64_t);
```

Exchanges the halfwords of the second operand, performs 2x16-bit
multiplication and adds both results to the 64-bit third operand.
Overflow in the addition is not detected.

``` c
  int32_t __smlsd(int16x2_t, int16x2_t, int32_t);
```

Performs two 16-bit signed multiplications. Takes the difference of the
products, subtracting the high-halfword product from the low-halfword
product, and adds the difference to the third operand. Sets the Q flag
if the addition overflows. (Overflow cannot occur during the
multiplications or the subtraction.)

``` c
  int32_t __smlsdx(int16x2_t, int16x2_t, int32_t);
```

Performs two 16-bit signed multiplications. The product of the high
halfword of the first operand and the low halfword of the second operand
is subtracted from the product of the low halfword of the first operand
and the high halfword of the second operand, and the difference is added
to the third operand. Sets the Q flag if the addition overflows.
(Overflow cannot occur during the multiplications or the subtraction.)

``` c
  int64_t __smlsld(int16x2_t, int16x2_t, int64_t);
```

Perform two 16-bit signed multiplications. Take the difference of the
products, subtracting the high-halfword product from the low-halfword
product, and add the difference to the third operand. Overflow in the
64-bit addition is not detected. (Overflow cannot occur during the
multiplications or the subtraction.)

``` c
  int64_t __smlsldx(int16x2_t, int16x2_t, int64_t);
```

Perform two 16-bit signed multiplications. The product of the high
halfword of the first operand and the low halfword of the second operand
is subtracted from the product of the low halfword of the first operand
and the high halfword of the second operand, and the difference is added
to the third operand. Overflow in the 64-bit addition is not detected.
(Overflow cannot occur during the multiplications or the subtraction.)

``` c
  int32_t __smuad(int16x2_t, int16x2_t);
```

Perform 2x16-bit signed multiplications, adding the products together.
Set the Q flag if the addition overflows.

``` c
  int32_t __smuadx(int16x2_t, int16x2_t);
```

Exchange the halfwords of the second operand (or equivalently, the first
operand), perform 2x16-bit signed multiplications, and add the products
together. Set the Q flag if the addition overflows.

``` c
  int32_t __smusd(int16x2_t, int16x2_t);
```

Perform two 16-bit signed multiplications. Take the difference of the
products, subtracting the high-halfword product from the low-halfword
product.

``` c
  int32_t __smusdx(int16x2_t, int16x2_t);
```

Perform two 16-bit signed multiplications. The product of the high
halfword of the first operand and the low halfword of the second operand
is subtracted from the product of the low halfword of the first operand
and the high halfword of the second operand.

### Examples

Taking the elementwise maximum of two SIMD values each of which consists
of four 8-bit signed numbers:

``` c
  int8x4_t max8x4(int8x4_t x, int8x4_t y) { __ssub8(x, y); return __sel(x, y); }
```

As described in :ref:sec-Parallel-selection, where SIMD values
consist of two 16-bit unsigned numbers:

``` c
  int16x2_t max16x2(int16x2_t x, int16x2_t y) { __usub16(x, y); return __sel(x, y); }
```

Note that even though the result of the subtraction is not used, the
compiler must still generate the instruction, because of its side-effect
on the GE bits which are tested by the `__sel()` intrinsic.

## Floating-point data-processing intrinsics

The intrinsics in this section provide direct access to selected
floating-point instructions. They are defined only if the appropriate
precision is available in hardware, as indicated by `__ARM_FP` (see
[Hardware floating point](#hardware-floating-point)).

``` c
  double __sqrt(double x);
  float __sqrtf(float x);
```

The `__sqrt` intrinsics compute the square root of their operand. They
have no effect on errno. Negative values produce a default NaN
result and possible floating-point exception as described in [ARMARM]
(A2.7.7).

``` c
  double __fma(double x, double y, double z);
  float __fmaf(float x, float y, float z);
```

The `__fma` intrinsics compute `(x*y)+z`, without intermediate rounding.
These intrinsics are available only if `__ARM_FEATURE_FMA` is defined.
On a Standard C implementation it should not normally be necessary to
use these intrinsics, because the fma functions defined in [C99] (7.12.13)
should expand directly to the instructions if available.

``` c
  float __rintnf (float);
  double __rintn (double);
```

The `__rintn` intrinsics perform a floating point round to integral, to
nearest with ties to even. The `__rintn` intrinsic is available when
`__ARM_FEATURE_DIRECTED_ROUNDING` is defined to 1. For other rounding
modes like |lsquo| to nearest with ties to away |rsquo| it is strongly recommended
that C99 standard functions be used. To achieve a floating point convert
to integer, rounding to |lsquo| nearest with ties to even |rsquo| operation, use these
rounding functions with a type-cast to integral values. For example:

``` c
  (int) __rintnf (a);
```

maps to a floating point convert to signed integer, rounding to nearest
with ties to even operation.

``` c
  int32_t __jcvt (double);
```

Converts a double-precision floating-point number to a 32-bit signed
integer following the Javascript Convert instruction semantics [[ARMARMv83]](#ARMARMv83).
The `__jcvt` intrinsic is available if `__ARM_FEATURE_JCVT` is defined.

``` c
  float __rint32zf (float);
  double __rint32z (double);
  float __rint64zf (float);
  double __rint64z (double);
  float __rint32xf (float);
  double __rint32x (double);
  float __rint64xf (float);
  double __rint64x (double);
```

These intrinsics round their floating-point argument to a floating-point value
that would be representable in a 32-bit or 64-bit signed integer type.
Out-of-Range values are forced to the Most Negative Integer representable in
the target size, and an Invalid Operation Floating-Point Exception is
generated.  The rounding mode can be either the ambient rounding mode
(for example `__rint32xf`) or toward zero (for example `__rint32zf`).

These instructions are introduced in the Armv8.5-A extensions
[[ARMARMv85]](#ARMARMv85) and are available only in the AArch64 execution state.
The intrinsics are available when `__ARM_FEATURE_FRINT` is defined.

## Random number generation intrinsics

The Random number generation intrinsics provide access to the Random Number
instructions introduced in Armv8.5-A.  These intrinsics are only defined for
the AArch64 execution state and are available when `__ARM_FEATURE_RNG`
is defined.

``` c
  int __rndr (uint64_t *);
```

Stores a 64-bit random number into the object pointed to by the argument and
returns zero.
If the implementation could not generate a random number  within a reasonable
period of time the object pointed to by the input is set to zero and a non-zero
value is returned.

``` c
  int __rndrrs (uint64_t *);
```

Reseeds the random number generator.  After that stores a 64-bit random number
into the object pointed to by the argument and returns zero.
If the implementation could not generate a random number within a reasonable
period of time the object pointed to by the input is set to zero and a
non-zero value is returned.

These intrinsics have side-effects on the system beyond their results.
Implementations must preserve them even if the results of the intrinsics are
unused.

To access these intrinsics, `<arm_acle.h>` should be included.

## CRC32 intrinsics

CRC32 intrinsics provide direct access to CRC32 instructions
CRC32{C}{B, H, W, X} in both Armv8 AArch32 and AArch64 execution states.
These intrinsics are available when `__ARM_FEATURE_CRC32` is defined.

``` c
  uint32_t __crc32b (uint32_t a, uint8_t b);
```

Performs CRC-32 checksum from bytes.

``` c
  uint32_t __crc32h (uint32_t a, uint16_t b);
```

Performs CRC-32 checksum from half-words.

``` c
  uint32_t __crc32w (uint32_t a, uint32_t b);
```

Performs CRC-32 checksum from words.

``` c
  uint32_t __crc32d (uint32_t a, uint64_t b);
```

Performs CRC-32 checksum from double words.

``` c
  uint32_t __crc32cb (uint32_t a, uint8_t b);
```

Performs CRC-32C checksum from bytes.

``` c
  uint32_t __crc32ch (uint32_t a, uint16_t b);
```

Performs CRC-32C checksum from half-words.

``` c
  uint32_t __crc32cw (uint32_t a, uint32_t b);
```

Performs CRC-32C checksum from words.

``` c
  uint32_t __crc32cd (uint32_t a, uint64_t b);
```

Performs CRC-32C checksum from double words.

To access these intrinsics, `<arm_acle.h>` should be included.

## Load/store 64 Byte intrinsics

These intrinsics provide direct access to the Armv8.7-A `LD64B`,
`ST64B`, `ST64BV` and `ST64BV0` instructions for atomic 64-byte
access to device memory.
These intrinsics are available when `__ARM_FEATURE_LS64` is defined.

The header `<arm_acle.h>` defines these intrinsics, and also the
data type `data512_t` that they use.

The type `data512_t` is a 64-byte structure type containing a single
member `val` which is an array of 8 `uint64_t`, as if declared
like this:

``` c
  typedef struct {
      uint64_t val[8];
  } data512_t;
```

The following intrinsics are defined on this data type. In all cases,
the address `addr` must be aligned to a multiple of 64 bytes.

``` c
  data512_t __arm_ld64b(const void *addr);
```

Loads 64 bytes of data atomically from the address `addr`. The
address must be in a memory region that supports 64-byte load/store
operations.

``` c
  void __arm_st64b(void *addr, data512_t value);
```

Stores the 64 bytes in `value` atomically to the address `addr`. The
address must be in a memory region that supports 64-byte load/store
operations.

``` c
  uint64_t __arm_st64bv(void *addr, data512_t value);
```

Attempts to store the 64 bytes in `value` atomically to the address
`addr`.  It returns a 64-bit value from the response of the device
written to.

``` c
  uint64_t __arm_st64bv0(void *addr, data512_t value);
```

Performs the same operation as `__arm_st64bv`, except that the data
stored to memory is modified by replacing the low 32 bits of
`value.val[0]` with the contents of the `ACCDATA_EL1` system register.
The returned value is the same as for `__arm_st64bv`.

## Atomic store with hints intrinsics

This intrinsic provides an atomic store together with a hint value.
The hint is a suggestion to the compiler and maps directly to a
specific hint instruction variant in the ISA. The compiler may use this hint
when selecting code sequences, but it is not required to emit a specific
hint instruction or a specific instruction sequence. This intrinsic is
type generic and supports scalar integral and floating-point types of 8, 16, 32, and 64 bits.

To access this intrinsic, `<arm_acle.h>` should be included.

``` c
  void __arm_atomic_store_with_hint(type *ptr,
                                    type data,
                                    int memory_order,
                                    int hint);
```

The first argument `ptr` is the location to store to. The second
argument `data` is the value to be stored. The third argument
`memory_order` can be one of the memory ordering values supported by
`atomic_store`: `__ATOMIC_RELAXED`, `__ATOMIC_SEQ_CST`, and
`__ATOMIC_RELEASE`.

The fourth argument `hint` selects the requested hint. The set of valid
hint values depends on the architectural features supported by the
target. The following hint values are defined:

| **Hint**         | **Value** | **Feature**                | **Summary**                                                                       |
| ---------------- | --------- | -------------------------- | --------------------------------------------------------------------------------- |
| HINT_STSHH_KEEP  | 0         | `__ARM_FEATURE_PCDPHINT`   | Requests retention of the updated location in the local cache of the updating PE. |
| HINT_STSHH_STRM  | 1         | `__ARM_FEATURE_PCDPHINT`   | Requests that the updated location not be retained in the local cache of the updating PE. |
| HINT_STCPH       | 2         | `__ARM_FEATURE_CMH`        | Ensures that the memory write effect of the next instruction occurs before any other effects from other threads.|
| HINT_SHUH        | 3         | `__ARM_FEATURE_CMH`        | Informs that the next instruction generates an effect in a location that one or more other threads of execution are likely to subsequently update. |
| HINT_SHUH_PH     | 4         | `__ARM_FEATURE_CMH`        | PH adds the effects of STCPH to SHUH. |

## Atomic fetch with hints intrinsics

These intrinsics provide some atomic fetch operations, which will
make use of hint instructions immediately followed by the
associated fetch instructions. These intrinsics are type generic and
support scalar integral types of 8, 16, 32, and 64 bits.

To access these intrinsics, `<arm_acle.h>` should be included.

``` c
  type __arm_atomic_fetch_add_with_hint(type *ptr, type data, int memory_order, int hint);
  type __arm_atomic_fetch_sub_with_hint(type *ptr, type data, int memory_order, int hint);
  type __arm_atomic_fetch_and_with_hint(type *ptr, type data, int memory_order, int hint);
  type __arm_atomic_fetch_xor_with_hint(type *ptr, type data, int memory_order, int hint);
  type __arm_atomic_fetch_or_with_hint(type *ptr, type data, int memory_order, int hint);
```

The first argument in these intrinsic is a pointer `ptr` which is the location for read-modify-write.
The second argument `data` is the data which is to be used in the RMW operation.
The third argument `mem` can be one of 6 memory ordering variables supported by atomic_fetch:
__ATOMIC_RELAXED, __ATOMIC_SEQ_CST, __ATOMIC_ACQUIRE, __ATOMIC_CONSUME, __ATOMIC_ACQ_REL and __ATOMIC_RELEASE.

The fourth argument `hint` selects the requested hint. The set of valid
hint values depends on the architectural features supported by the
target. The following hint values are defined:

| **Hint**         | **Value** | **Feature**                | **Summary**                                                                       |
| ---------------- | --------- | -------------------------- | --------------------------------------------------------------------------------- |
| HINT_SHUH        | 3         | `__ARM_FEATURE_CMH`        | Informs that the next instruction generates an effect in a location that one or more other threads of execution are likely to subsequently update. |
| HINT_SHUH_PH     | 4         | `__ARM_FEATURE_CMH`        | PH adds the effects of STCPH to SHUH. |
