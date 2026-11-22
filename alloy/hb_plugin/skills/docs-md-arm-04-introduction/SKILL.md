---
name: docs-md-arm-04-introduction
description: "Arm ACLE: Introduction (vendor documentation for Arm NEON, SVE and SME)."
when: "when you need Arm ACLE: Introduction while writing a kernel for Arm NEON, SVE and SME."
---

# Introduction

The Arm architecture includes features that go beyond the set of operations
available to C/C++ programmers. The intention of the Arm C Language
Extensions (ACLE) is to allow the creation of applications and middleware
code that is portable across compilers, and across Arm architecture
variants, while exploiting the advanced features of the Arm architecture.

The design principles for ACLE can be summarized as:

 * Be implementable in (or as an addition to) current C/C++
   implementations.

 * Build on and standardize existing practice where possible.

ACLE incorporates some language extensions introduced in the GCC C
compiler. Current GCC documentation [[GCC]](#GCC) can be found at
<http://gcc.gnu.org/onlinedocs/gcc>.
Formally it should be assumed that ACLE refers to the documentation for
GCC 4.5.1: <http://gcc.gnu.org/onlinedocs/gcc-4.5.1/gcc/>.

Some of the ACLE extensions are not specific to the Arm architecture but
have proven to be of particular benefit in low-level and systems
programming; examples include features for controlling the alignment and
packing of data, and some common operations such as word rotation and
reversal. As and when features become available in international
standards (and implementations), Arm recommends that you use these in
preference to ACLE. When implementations are widely available, any
ACLE-specific features can be expected to be deprecated.

## Portable binary objects

In AArch32, the *ABI for the Arm Architecture* defines a set of build
attributes [[BA]](#BA). These attributes are intended to facilitate generating
cross-platform portable binary object files by providing a mechanism to
determine the compatibility of object files. In AArch64, the ABI does
not define a standard set of build attributes and takes the approach
that binaries are, in general, not portable across platforms. References
to build attributes in this document should be interpreted as applying
only to AArch32.
