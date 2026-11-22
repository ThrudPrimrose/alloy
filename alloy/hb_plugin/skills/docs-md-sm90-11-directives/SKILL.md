---
name: docs-md-sm90-11-directives
description: "PTX ISA 9.4: Directives (vendor documentation for NVIDIA sm90 (PTX))."
when: "when you need PTX ISA 9.4: Directives while writing a kernel for NVIDIA sm90 (PTX)."
---

# Chapter 11. Directives

## 11.1. PTX Module Directives

The following directives declare the PTX ISA version of the code in the module, the target architecture for which the code was generated, and the size of addresses within the PTX module.

- .version

- .target

- .address_size

### 11.1.1. PTX Module Directives: .version

**.version**

PTX ISA version number.

#### **Syntax**

.version major.minor ∕∕major, minor are integers

#### **Description**

Specifies the PTX language version number.

The _major_ number is incremented when there are incompatible changes to the PTX language, such as changes to the syntax or semantics. The version major number is used by the PTX compiler to ensure correct execution of legacy PTX code.

The _minor_ number is incremented when new features are added to PTX.

**911**

**PTX ISA, Release 9.4**

#### **Semantics**

Indicates that this module must be compiled with tools that support an equal or greater version number.

Each PTX module must begin with a .version directive, and no other .version directive is allowed anywhere else within the module.

#### **PTX ISA Notes**

Introduced in PTX ISA version 1.0.

#### **Target ISA Notes**

Supported on all target architectures.

#### **Examples**

.version 3.1 .version 3.0 .version 2.3

### 11.1.2. PTX Module Directives: .target

**.target**

Architecture and Platform target.

#### **Syntax**

.target stringlist ∕∕comma separated list of target specifiers string = { sm_120a, sm_120f, sm_120, ∕∕sm_12x target architectures sm_121a, sm_121f, sm_121, ∕∕sm_12x target architectures sm_110a, sm_110f, sm_110, ∕∕sm_11x target architectures sm_100a, sm_100f, sm_100, ∕∕sm_10x target architectures sm_101a, sm_101f, sm_101, ∕∕sm_10x target architectures sm_103a, sm_103f, sm_103 ∕∕sm_10x target architectures sm_107a, sm_107f, sm_107 ∕∕sm_10x target architectures sm_90a, sm_90, ∕∕sm_9x target architectures sm_80, sm_86, sm_87, sm_88, sm_89, ∕∕sm_8x target architectures sm_70, sm_72, sm_75, ∕∕sm_7x target architectures sm_60, sm_61, sm_62, ∕∕sm_6x target architectures sm_50, sm_52, sm_53, ∕∕sm_5x target architectures sm_30, sm_32, sm_35, sm_37, ∕∕sm_3x target architectures sm_20, ∕∕sm_2x target architectures sm_10, sm_11, sm_12, sm_13, ∕∕sm_1x target architectures texmode_unified, texmode_independent, ∕∕texturing mode debug, ∕∕platform option map_f64_to_f32 }; ∕∕platform option

**Chapter 11. Directives**

**912**

**PTX ISA, Release 9.4**

#### **Description**

Specifies the set of features in the target architecture for which the current PTX code was generated. In general, generations of SM architectures follow an _onion layer_ model, where each generation adds new features and retains all features of previous generations. The onion layer model allows the PTX code generated for a given target to be run on later generation devices.

Target architectures with suffix “ a ”, such as sm_90a , include architecture-specific features that are supported on the specified architecture only, hence such targets do not follow the onion layer model. Therefore, PTX code generated for such targets cannot be run on later generation devices. Architecture-specific features can only be used with targets that support these features.

Target architectures with suffix “ f ”, such as sm_100f , include family-specific features that are supported only within the same architecture family. Therefore, PTX code generated for such targets can run only on later generation devices in the same family. Family-specific features can be used with f-targets as well as a-targets of later generation devices in the same family.

Table 76 defines the architecture families.

Table 76: Architecture Families

|**Family**|**Target SM architectures included**|
|---|---|
|sm_10x family|sm_100f, sm_103f, sm_107f, future targets in sm_10x family|
|sm_11x family|sm_110f, sm_101f, future targets in sm_11x family|
|sm_12x family|sm_120f, sm_121f, future targets in sm_12x family|



#### **Semantics**

Each PTX module must begin with a .version directive, immediately followed by a .target directive containing a target architecture and optional platform options. A .target directive specifies a single target architecture, but subsequent .target directives can be used to change the set of target features allowed during parsing. A program with multiple .target directives will compile and run only on devices that support all features of the highest-numbered architecture listed in the program.

PTX features are checked against the specified target architecture, and an error is generated if an unsupported feature is used. The following table summarizes the features in PTX that vary according to target architecture.

|**Target**|**Description**|
|---|---|
|sm_120|Baseline feature set forsm_120architecture.|
|sm_120f|Adds support forsm_120ffamily specific features.|
|sm_120a|Adds support forsm_120aarchitecture-specific features.|
|sm_121|Baseline feature set forsm_121architecture.|
|sm_121f|Adds support forsm_121ffamily specific features.|
|sm_121a|Adds support forsm_121aarchitecture-specific features.|



**11.1. PTX Module Directives**

**913**

**PTX ISA, Release 9.4**

|**Target**|**Description**|
|---|---|
|sm_110|Baseline feature set forsm_110architecture.|
|sm_110f|Adds support forsm_110ffamily specific features.|
|sm_110a|Adds support forsm_110aarchitecture-specific features.|



|**Target**|**Description**|
|---|---|
|sm_100|Baseline feature set forsm_100architecture.|
|sm_100f|Adds support forsm_100ffamily specific features.|
|sm_100a|Adds support forsm_100aarchitecture-specific features.|
|sm_101|Baseline feature set forsm_101architecture. (Renamed tosm_110)|
|sm_101f|Adds support forsm_101ffamily specific features. (Renamed tosm_110f)|
|sm_101a|Adds support for sm_101a architecture-specific features.<br>(Renamed to<br>sm_110a)|
|sm_103|Baseline feature set forsm_103architecture.|
|sm_103f|Adds support forsm_103ffamily specific features.|
|sm_103a|Adds support forsm_103aarchitecture-specific features.|
|sm_107|Baseline feature set forsm_107architecture.|
|sm_107f|Adds support forsm_107ffamily specific features.|
|sm_107a|Adds support forsm_107aarchitecture-specific features.|



|**Target**|**Description**|
|---|---|
|sm_90|Baseline feature set forsm_90architecture.|
|sm_90a|Adds support forsm_90aarchitecture-specific features.|



|**Target**|**Description**|
|---|---|
|sm_80|Baseline feature set forsm_80architecture.|
|sm_86|Adds support for.xorsignmodifier onminandmaxinstructions.|
|sm_87|Baseline feature set forsm_87architecture.|
|sm_88|Baseline feature set forsm_88architecture.|
|sm_89|Baseline feature set forsm_89architecture.|



**Chapter 11. Directives**

**914**

**PTX ISA, Release 9.4**

|**Target**|**Description**|
|---|---|
|sm_70|Baseline feature set forsm_70architecture.|
|sm_72|Adds support for integer multiplicand and accumulator matrices in wmma in-<br>structions.<br>Adds support forcvt.packinstruction.|
|sm_75|Adds support for sub-byte integer and single-bit multiplicant matrices inwmma<br>instructions.<br>Adds support forldmatrixinstruction.<br>Adds support formovmatrixinstruction.<br>Adds support fortanhinstruction.|



|**Target**|**Description**|
|---|---|
|sm_60|Baseline feature set forsm_60architecture.|
|sm_61|Adds support fordp2aanddp4ainstructions.|
|sm_62|Baseline feature set forsm_61architecture.|



|**Target**|**Description**|
|---|---|
|sm_50|Baseline feature set forsm_50architecture.|
|sm_52|Baseline feature set forsm_50architecture.|
|sm_53|Adds support for arithmetic, comparison and texture instructions for.f16and<br>.f16x2types.|



|**Target**|**Description**|
|---|---|
|sm_30|Baseline feature set forsm_30architecture.|
|sm_32|Adds 64-bit{atom,red}.{and,or,xor,min,max}instructions.<br>Addsshfinstruction.<br>Addsld.global.ncinstruction.|
|sm_35|Adds support for CUDA Dynamic Parallelism.|
|sm_37|Baseline feature set forsm_35architecture.|



|**Target**|**Description**|
|---|---|
|sm_20|Baseline feature set forsm_20architecture.|



**11.1. PTX Module Directives**

**915**

**PTX ISA, Release 9.4**

|**Target**|**Description**|
|---|---|
|sm_10|Baseline feature set forsm_10architecture.<br>Requiresmap_f64_to_f32if any.f64instructions used.|
|sm_11|Adds 64-bit{atom,red}.{and,or,xor,min,max}instructions.<br>Requiresmap_f64_to_f32if any.f64instructions used.|
|sm_12|Adds{atom,red}.shared, 64-bit{atom,red}.global,voteinstructions.<br>Requiresmap_f64_to_f32if any.f64instructions used.|
|sm_13|Adds double-precision support, including expanded rounding modifiers.<br>Disallows use ofmap_f64_to_f32.|



The texturing mode is specified for an entire module and cannot be changed within the module.

The .target debug option declares that the PTX file contains DWARF debug information, and subsequent compilation of PTX will retain information needed for source-level debugging. If the debug option is declared, an error message is generated if no DWARF information is found in the file. The debug option requires PTX ISA version 3.0 or later.

map_f64_to_f32 indicates that all double-precision instructions map to single-precision regardless of the target architecture. This enables high-level language compilers to compile programs containing type double to target device that do not support double-precision operations. Note that .f64 storage remains as 64-bits, with only half being used by instructions converted from .f64 to .f32 .

#### **Notes**

Targets of the form compute_xx are also accepted as synonyms for sm_xx targets.

Targets sm_{101,101f,101a} are renamed to targets sm_{110,110f,110a} from PTX ISA version 9.0.

#### **PTX ISA Notes**

Introduced in PTX ISA version 1.0.

Target strings sm_10 and sm_11 introduced in PTX ISA version 1.0.

Target strings sm_12 and sm_13 introduced in PTX ISA version 1.2.

Texturing mode introduced in PTX ISA version 1.5.

Target string sm_20 introduced in PTX ISA version 2.0. Target string sm_30 introduced in PTX ISA version 3.0.

Platform option debug introduced in PTX ISA version 3.0.

Target string sm_35 introduced in PTX ISA version 3.1.

Target strings sm_32 and sm_50 introduced in PTX ISA version 4.0.

Target strings sm_37 and sm_52 introduced in PTX ISA version 4.1. Target string sm_53 introduced in PTX ISA version 4.2.

Target string sm_60 , sm_61 , sm_62 introduced in PTX ISA version 5.0.

Target string sm_70 introduced in PTX ISA version 6.0.

**Chapter 11. Directives**

**916**

**PTX ISA, Release 9.4**

Target string sm_72 introduced in PTX ISA version 6.1. Target string sm_75 introduced in PTX ISA version 6.3. Target string sm_80 introduced in PTX ISA version 7.0. Target string sm_86 introduced in PTX ISA version 7.1. Target string sm_87 introduced in PTX ISA version 7.4. Target string sm_88 introduced in PTX ISA version 9.0. Target string sm_89 introduced in PTX ISA version 7.8. Target string sm_90 introduced in PTX ISA version 7.8. Target string sm_90a introduced in PTX ISA version 8.0. Target string sm_100 introduced in PTX ISA version 8.6. Target string sm_100f introduced in PTX ISA version 8.8. Target string sm_100a introduced in PTX ISA version 8.6. Target string sm_101 introduced in PTX ISA version 8.6. (Renamed to sm_110 ) Target string sm_101f introduced in PTX ISA version 8.8. (Renamed to sm_110f ) Target string sm_101a introduced in PTX ISA version 8.6. (Renamed to sm_110a ) Target string sm_103 introduced in PTX ISA version 8.8. Target string sm_103f introduced in PTX ISA version 8.8. Target string sm_103a introduced in PTX ISA version 8.8. Target string sm_107 introduced in PTX ISA version 9.4. Target string sm_107f introduced in PTX ISA version 9.4. Target string sm_107a introduced in PTX ISA version 9.4. Target string sm_110 introduced in PTX ISA version 9.0. Target string sm_110f introduced in PTX ISA version 9.0. Target string sm_110a introduced in PTX ISA version 9.0. Target string sm_120 introduced in PTX ISA version 8.7. Target string sm_120f introduced in PTX ISA version 8.8. Target string sm_120a introduced in PTX ISA version 8.7. Target string sm_121 introduced in PTX ISA version 8.8. Target string sm_121f introduced in PTX ISA version 8.8. Target string sm_121a introduced in PTX ISA version 8.8.

**11.1. PTX Module Directives**

**917**

**PTX ISA, Release 9.4**

#### **Target ISA Notes**

The .target directive is supported on all target architectures.

#### **Examples**

.target sm_10 ∕∕baseline target architecture .target sm_13 ∕∕supports double-precision .target sm_20, texmode_independent .target sm_90 ∕∕baseline target architecture .target sm_90a ∕∕PTX using architecture-specific features .target sm_100f ∕∕PTX using family-specific features

### 11.1.3. PTX Module Directives: .address_size

**.address_size**

Address size used throughout PTX module.

#### **Syntax**

.address_size address-size address-size = { 32, 64 };

#### **Description**

Specifies the address size assumed throughout the module by the PTX code and the binary DWARF information in PTX.

Redefinition of this directive within a module is not allowed. In the presence of separate compilation all modules must specify (or default to) the same address size.

The .address_size directive is optional, but it must immediately follow the .target directive if present within a module.

#### **Semantics**

If the .address_size directive is omitted, the address size defaults to 32.

**Chapter 11. Directives**

**918**

**PTX ISA, Release 9.4**

#### **PTX ISA Notes**

Introduced in PTX ISA version 2.3.

#### **Target ISA Notes**

Supported on all target architectures.

#### **Examples**

∕∕example directives .address_size 32 ∕∕addresses are 32 bit .address_size 64 ∕∕addresses are 64 bit ∕∕example of directive placement within a module .version 2.3 .target sm_20 .address_size 64 ... .entry foo () { ... }

## 11.2. Specifying Kernel Entry Points and Functions

The following directives specify kernel entry points and functions.

▶ .entry ▶ .func

11.2.1. Kernel and Function Directives: .entry

**.entry**

Kernel entry point and body, with optional parameters.

**11.2. Specifying Kernel Entry Points and Functions**

**919**

**PTX ISA, Release 9.4**

#### **Syntax**

.entry kernel-name ( param-list ) kernel-body .entry kernel-name kernel-body

#### **Description**

Defines a kernel entry point name, parameters, and body for the kernel function.

Parameters are passed via .param space memory and are listed within an optional parenthesized parameter list. Parameters may be referenced by name within the kernel body and loaded into registers using ld.param{::entry} instructions.

In addition to normal parameters, opaque .texref , .samplerref , and .surfref variables may be passed as parameters. These parameters can only be referenced by name within texture and surface load, store, and query instructions and cannot be accessed via ld.param instructions.

The shape and size of the CTA executing the kernel are available in special registers.

#### **Semantics**

Specify the entry point for a kernel program.

At kernel launch, the kernel dimensions and properties are established and made available via special registers, e.g., %ntid , %nctaid , etc.

#### **PTX ISA Notes**

For PTX ISA version 1.4 and later, parameter variables are declared in the kernel parameter list. For PTX ISA versions 1.0 through 1.3, parameter variables are declared in the kernel body.

The maximum memory size supported by PTX for normal (non-opaque type) parameters is 32764 bytes. Depending upon the PTX ISA version, the parameter size limit varies. The following table shows the allowed parameter size for a PTX ISA version:

|**PTX ISA Version**|**Maximum parameter size (In bytes)**|
|---|---|
|PTX ISA version 8.1 and above|32764|
|PTX ISA version 1.5 and above|4352|
|PTX ISA version 1.4 and above|256|



The CUDA and OpenCL drivers support the following limits for parameter memory:

|**Driver**|**Parameter memory size**|
|---|---|
|CUDA|256 bytes for sm_1x, 4096 bytes for sm_2x<br>and<br>higher, 32764 bytes fo sm_70 and<br>higher|
|OpenCL|32764 bytes forsm_70and higher, 4352 bytes onsm_6xand lower|



**Chapter 11. Directives**

**920**

**PTX ISA, Release 9.4**

#### **Target ISA Notes**

Supported on all target architectures.

#### **Examples**

.entry cta_fft .entry filter ( .param .b32 x, .param .b32 y, .param .b32 z ) { .reg .b32 %r<99>; ld.param.b32 %r1, [x]; ld.param.b32 %r2, [y]; ld.param.b32 %r3, [z]; ... } .entry prefix_sum ( .param .align 4 .s32 pitch[8000] ) { .reg .s32 %t; ld.param::entry.s32 %t, [pitch]; ... }

11.2.2. Kernel and Function Directives: .func

#### **.func**

Function definition.

#### **Syntax**

.func {.attribute(attr-list)} fname {.noreturn} {.abi_preserve N} {.abi_preserve �→_ control N} function-body .func {.attribute(attr-list)} fname (param-list) {.noreturn} {.abi_preserve N} {.abi �→_ preserve_control N} function-body .func {.attribute(attr-list)} (ret-param) fname (param-list) {.abi_preserve N} {.abi �→_ preserve_control N} function-body

#### **Description**

Defines a function, including input and return parameters and optional function body.

An optional .noreturn directive indicates that the function does not return to the caller function. .noreturn directive cannot be specified on functions which have return parameters. See the description of .noreturn directive in _Performance-Tuning Directives: .noreturn_ .

An optional .attribute directive specifies additional information associated with the function. See the description of _Variable and Function Attribute Directive: .attribute_ for allowed attributes.

**11.2. Specifying Kernel Entry Points and Functions**

**921**

**PTX ISA, Release 9.4**

Optional .abi_preserve and .abi_preserve_control directives are used to specify the number of general purpose registers and control registers. See description of _Performance-Tuning Directives: .abi_preserve_ and _Performance-Tuning Directives: .abi_preserve_control_ for more details.

Directives, if any specified, for a function, e.g. .noreturn , must be specified consistently between function declaration and definition.

A .func definition with no body provides a function prototype.

The parameter lists define locally-scoped variables in the function body. Parameters must be base types in either the register or parameter state space. Parameters in register state space may be referenced directly within instructions in the function body. Parameters in .param space are accessed using ld.param{::func} and st.param{::func} instructions in the body. Parameter passing is call-by-value.

The last parameter in the parameter list may be a .param array of type .b8 with no size specified. It is used to pass an arbitrary number of parameters to the function packed into a single array object.

When calling a function with such an unsized last argument, the last argument may be omitted from the call instruction if no parameter is passed through it. Accesses to this array parameter must be within the bounds of the array. The result of an access is undefined if no array was passed, or if the access was outside the bounds of the actual array being passed.

#### **Semantics**

The PTX syntax hides all details of the underlying calling convention and ABI.

The implementation of parameter passing is left to the optimizing translator, which may use a combination of registers and stack locations to pass parameters.

#### **Release Notes**

For PTX ISA version 1.x code, parameters must be in the register state space, there is no stack, and recursion is illegal.

PTX ISA versions 2.0 and later with target sm_20 or higher allow parameters in the .param state space, implements an ABI with stack, and supports recursion.

PTX ISA versions 2.0 and later with target sm_20 or higher support at most one return value.

#### **PTX ISA Notes**

Introduced in PTX ISA version 1.0.

Support for unsized array parameter introduced in PTX ISA version 6.0.

Support for .noreturn directive introduced in PTX ISA version 6.4.

Support for .attribute directive introduced in PTX ISA version 8.0.

Support for .abi_preserve and .abi_preserve_control directives introduced in PTX ISA version 9.0.

**Chapter 11. Directives**

**922**

**PTX ISA, Release 9.4**

#### **Target ISA Notes**

Functions without unsized array parameter supported on all target architectures.

Unsized array parameter requires sm_30 or higher.

.noreturn directive requires sm_30 or higher.

.attribute directive requires sm_90 or higher.

.abi_preserve and .abi_preserve_control directives require sm_80 or higher.

#### **Examples**

.func (.reg .b32 rval) foo (.reg .b32 N, .reg .f64 dbl) { .reg .b32 localVar; ... use N, dbl; other code; mov.b32 rval,result; ret; } ... call (fooval), foo, (val0, val1); ∕∕return value in fooval ... .func foo (.reg .b32 N, .reg .f64 dbl) .noreturn { .reg .b32 localVar; ... use N, dbl; other code; mov.b32 rval, result; ret; } ... call foo, (val0, val1); ... .func (.param .u32 rval) bar(.param .u32 N, .param .align 4 .b8 numbers[]) { .reg .b32 input0, input1; ld.param.b32 input0, [numbers + 0]; ld.param.b32 input1, [numbers + 4]; ... other code; ret; } ... .param .u32 N; .param .align 4 .b8 numbers[8]; st.param.u32 [N], 2; st.param.b32 [numbers + 0], 5; st.param.b32 [numbers + 4], 10;

(continues on next page)

**11.2. Specifying Kernel Entry Points and Functions**

**923**

**PTX ISA, Release 9.4**

(continued from previous page)

call (rval), bar, (N, numbers); ...

### 11.2.3. Kernel and Function Directives: .alias

**.alias**

Define an alias to existing function symbol.

#### **Syntax**

.alias fAlias, fAliasee;

#### **Description**

.alias is a module scope directive that defines identifier fAlias to be an alias to function specified by fAliasee .

Both fAlias and fAliasee are non-entry function symbols.

Identifier fAlias is a function declaration without body.

Identifier fAliasee is a function symbol which must be defined in the same module as .alias declaration. Function fAliasee cannot have .weak linkage.

Prototype of fAlias and fAliasee must match.

Program can use either fAlias or fAlisee identifiers to reference function defined with fAliasee .

#### **PTX ISA Notes**

.alias directive introduced in PTX ISA 6.3.

#### **Target ISA Notes**

.alias directive requires sm_30 or higher.

#### **Examples**

.visible .func foo(.param .u32 p) { ... } .visible .func bar(.param .u32 p); .alias bar, foo; .entry test() {

(continues on next page)

**Chapter 11. Directives**

**924**

**PTX ISA, Release 9.4**

(continued from previous page)

.param .u32 p; ... call foo, (p); ∕∕call foo directly ... .param .u32 p; call bar, (p); ∕∕call foo through alias } .entry filter ( .param .b32 x, .param .b32 y, .param .b32 z ) { .reg .b32 %r1, %r2, %r3; ld.param.b32 %r1, [x]; ld.param.b32 %r2, [y]; ld.param.b32 %r3, [z]; ... }

## 11.3. Control Flow Directives

PTX provides directives for specifying potential targets for brx.idx and call instructions. See the descriptions of brx.idx and call for more information.

- .branchtargets

- .calltargets

- .callprototype

### 11.3.1. Control Flow Directives: .branchtargets

#### **.branchtargets**

Declare a list of potential branch targets.

#### **Syntax**

Label: .branchtargets list-of-labels ;

#### **Description**

Declares a list of potential branch targets for a subsequent brx.idx , and associates the list with the label at the start of the line.

All control flow labels in the list must occur within the same function as the declaration.

The list of labels may use the compact, shorthand syntax for enumerating a range of labels having a common prefix, similar to the syntax described in _Parameterized Variable Names_ .

**11.3. Control Flow Directives**

**925**

**PTX ISA, Release 9.4**

**PTX ISA Notes**

Introduced in PTX ISA version 2.1.

**Target ISA Notes**

Requires sm_20 or higher.

**Examples**

.function foo () { .reg .u32 %r0; ... L1: ... L2: ... L3: ... ts: .branchtargets L1, L2, L3; @p brx.idx %r0, ts; ... .function bar() { .reg .u32 %r0; ... N0: ... N1: ... N2: ... N3: ... N4: ... ts: .branchtargets N<5>; @p brx.idx %r0, ts; ...

11.3.2. Control Flow Directives: .calltargets

**.calltargets**

Declare a list of potential call targets.

**Chapter 11. Directives**

**926**

**PTX ISA, Release 9.4**

#### **Syntax**

Label: .calltargets list-of-functions ;

#### **Description**

Declares a list of potential call targets for a subsequent indirect call, and associates the list with the label at the start of the line.

All functions named in the list must be declared prior to the .calltargets directive, and all functions must have the same type signature.

#### **PTX ISA Notes**

Introduced in PTX ISA version 2.1.

#### **Target ISA Notes**

Requires sm_20 or higher.

#### **Examples**

calltgt: .calltargets fastsin, fastcos; ... @p call (%f1), %r0, (%x), calltgt; ...

### 11.3.3. Control Flow Directives: .callprototype

#### **.callprototype**

Declare a prototype for use in an indirect call.

#### **Syntax**

∕∕no input or return parameters label: .callprototype _ .noreturn {.abi_preserve N} {.abi_preserve_control N}; ∕∕input params, no return params label: .callprototype _ (param-list) .noreturn {.abi_preserve N} {.abi_preserve �→_ control N}; ∕∕no input params, ∕∕return params label: .callprototype (ret-param) _ {.abi_preserve N} {.abi_preserve_control N}; ∕∕input, return parameters label: .callprototype (ret-param) _ (param-list) {.abi_preserve N} {.abi_preserve �→_ control N};

**11.3. Control Flow Directives**

**927**

**PTX ISA, Release 9.4**

#### **Description**

Defines a prototype with no specific function name, and associates the prototype with a label. The prototype may then be used in indirect call instructions where there is incomplete knowledge of the possible call targets.

Parameters may have either base types in the register or parameter state spaces, or array types in parameter state space. The sink symbol '_' may be used to avoid dummy parameter names.

An optional .noreturn directive indicates that the function does not return to the caller function. .noreturn directive cannot be specified on functions which have return parameters. See the description of .noreturn directive in _Performance-Tuning Directives: .noreturn_ .

Optional .abi_preserve and .abi_preserve_control directives are used to specify the number of general purpose registers and control registers. See description of _Performance-Tuning Directives: .abi_preserve_ and _Performance-Tuning Directives: .abi_preserve_control_ for more details.

#### **PTX ISA Notes**

Introduced in PTX ISA version 2.1.

Support for .noreturn directive introduced in PTX ISA version 6.4.

Support for .abi_preserve and .abi_preserve_control directives introduced in PTX ISA version 9.0.

#### **Target ISA Notes**

Requires sm_20 or higher.

.noreturn directive requires sm_30 or higher.

.abi_preserve and .abi_preserve_control directives require sm_80 or higher.

#### **Examples**

Fproto1: .callprototype _ ; Fproto2: .callprototype _ (.param .f32 _); Fproto3: .callprototype (.param .u32 _) _ ; Fproto4: .callprototype (.param .u32 _) _ (.param .f32 _); ... @p call (%val), %r0, (%f1), Fproto4; ... ∕∕example of array parameter Fproto5: .callprototype _ (.param .b8 _[12]); Fproto6: .callprototype _ (.param .f32 _) .noreturn; ... @p call %r0, (%f1), Fproto6; ... ∕∕example of .abi_preserve Fproto7: .callprototype _ (.param .b32 _) .abi_preserve 10; ...

(continues on next page)

**Chapter 11. Directives**

**928**

**PTX ISA, Release 9.4**

(continued from previous page)

@p call %r0, (%r1), Fproto7; ...

## 11.4. Performance-Tuning Directives

To provide a mechanism for low-level performance tuning, PTX supports the following directives, which pass information to the optimizing backend compiler.

- .maxnreg

- .maxntid

- .reqntid

- .minnctapersm

- .maxnctapersm (deprecated)

- .pragma

- .abi_preserve

- .abi_preserve_control

- .minperctamemory

The .maxnreg directive specifies the maximum number of registers to be allocated to a single thread; the .maxntid directive specifies the maximum number of threads in a thread block (CTA); the .reqntid directive specifies the required number of threads in a thread block (CTA); and the . minnctapersm directive specifies a minimum number of thread blocks to be scheduled on a single multiprocessor (SM). These can be used, for example, to throttle the resource requirements (e.g., registers) to increase total thread count and provide a greater opportunity to hide memory latency. The .minnctapersm directive can be used together with either the .maxntid or .reqntid directive to trade-off registers-per-thread against multiprocessor utilization without needed to directly specify a maximum number of registers. This may achieve better performance when compiling PTX for multiple devices having different numbers of registers per SM.

Device function directives .abi_preserve and .abi_preserve_control specify number of data and control registers from callee save registers that a function must preserve for its caller. This can be considered to be the number of general purpose and control registers live in the caller when function is called. Control registers refer to the number of divergent program points that happen in the calltree leading to current function call.

Currently, the .maxnreg , .maxntid , .reqntid , and .minnctapersm directives may be applied perentry and must appear between an .entry directive and its body. The directives take precedence over any module-level constraints passed to the optimizing backend. A warning message is generated if the directives’ constraints are inconsistent or cannot be met for the specified target device.

A general .pragma directive is supported for passing information to the PTX backend. The directive passes a list of strings to the backend, and the strings have no semantics within the PTX virtual machine model. The interpretation of .pragma values is determined by the backend implementation and is beyond the scope of the PTX ISA. Note that .pragma directives may appear at module (file) scope, at entry-scope, or as statements within a kernel or device function body.

**11.4. Performance-Tuning Directives**

**929**

**PTX ISA, Release 9.4**

### 11.4.1. Performance-Tuning Directives: .maxnreg

**.maxnreg**

Maximum number of registers that can be allocated per thread.

#### **Syntax**

.maxnreg n

#### **Description**

Declare the maximum number of registers per thread in a CTA.

#### **Semantics**

The compiler guarantees that this limit will not be exceeded. The actual number of registers used may be less; for example, the backend may be able to compile to fewer registers, or the maximum number of registers may be further constrained by .maxntid and .maxctapersm .

#### **PTX ISA Notes**

Introduced in PTX ISA version 1.3.

#### **Target ISA Notes**

Supported on all target architectures.

#### **Examples**

.entry foo .maxnreg 16 { ... } ∕∕max regs per thread = 16

### 11.4.2. Performance-Tuning Directives: .maxntid

**.maxntid**

Maximum number of threads in the thread block (CTA).

**Chapter 11. Directives**

**930**

**PTX ISA, Release 9.4**

#### **Syntax**

.maxntid nx .maxntid nx, ny .maxntid nx, ny, nz

#### **Description**

Declare the maximum number of threads in the thread block (CTA). This maximum is specified by giving the maximum extent of each dimension of the 1D, 2D, or 3D CTA. The maximum number of threads is the product of the maximum extent in each dimension.

#### **Semantics**

The maximum number of threads in the thread block, computed as the product of the maximum extent specified for each dimension, is guaranteed not to be exceeded in any invocation of the kernel in which this directive appears. Exceeding the maximum number of threads results in a runtime error or kernel launch failure.

Note that this directive guarantees that the _total_ number of threads does not exceed the maximum, but does not guarantee that the limit in any particular dimension is not exceeded.

#### **PTX ISA Notes**

Introduced in PTX ISA version 1.3.

#### **Target ISA Notes**

Supported on all target architectures.

#### **Examples**

.entry foo .maxntid 256 { ... } ∕∕max threads = 256 .entry bar .maxntid 16,16,4 { ... } ∕∕max threads = 1024

### 11.4.3. Performance-Tuning Directives: .reqntid

**.reqntid**

Number of threads in the thread block (CTA).

**11.4. Performance-Tuning Directives**

**931**

**PTX ISA, Release 9.4**

#### **Syntax**

.reqntid nx .reqntid nx, ny .reqntid nx, ny, nz

#### **Description**

Declare the number of threads in the thread block (CTA) by specifying the extent of each dimension of the 1D, 2D, or 3D CTA. The total number of threads is the product of the number of threads in each dimension.

#### **Semantics**

The size of each CTA dimension specified in any invocation of the kernel is required to be equal to that specified in this directive. Specifying a different CTA dimension at launch will result in a runtime error or kernel launch failure.

#### **Notes**

The .reqntid directive cannot be used in conjunction with the .maxntid directive.

#### **PTX ISA Notes**

Introduced in PTX ISA version 2.1.

#### **Target ISA Notes**

Supported on all target architectures.

#### **Examples**

.entry foo .reqntid 256 { ... } ∕∕num threads = 256 .entry bar .reqntid 16,16,4 { ... } ∕∕num threads = 1024

11.4.4. Performance-Tuning Directives: .minnctapersm

#### **.minnctapersm**

Minimum number of CTAs per SM.

**Chapter 11. Directives**

**932**

**PTX ISA, Release 9.4**

#### **Syntax**

.minnctapersm ncta

#### **Description**

Declare the minimum number of CTAs from the kernel’s grid to be mapped to a single multiprocessor (SM).

#### **Notes**

Optimizations based on .minnctapersm need either .maxntid or .reqntid to be specified as well.

If the total number of threads on a single SM resulting from .minnctapersm and .maxntid / . reqntid exceed maximum number of threads supported by an SM then directive .minnctapersm will be ignored.

In PTX ISA version 2.1 or higher, a warning is generated if .minnctapersm is specified without specifying either .maxntid or .reqntid .

#### **PTX ISA Notes**

Introduced in PTX ISA version 2.0 as a replacement for .maxnctapersm .

#### **Target ISA Notes**

Supported on all target architectures.

#### **Examples**

.entry foo .maxntid 256 .minnctapersm 4 { ... }

11.4.5. Performance-Tuning Directives: .maxnctapersm (deprecated)

#### **.maxnctapersm**

Maximum number of CTAs per SM.

**11.4. Performance-Tuning Directives**

**933**

**PTX ISA, Release 9.4**

#### **Syntax**

.maxnctapersm ncta

#### **Description**

Declare the maximum number of CTAs from the kernel’s grid that may be mapped to a single multiprocessor (SM).

#### **Notes**

Optimizations based on .maxnctapersm generally need .maxntid to be specified as well. The optimizing backend compiler uses .maxntid and .maxnctapersm to compute an upper-bound on per-thread register usage so that the specified number of CTAs can be mapped to a single multiprocessor. However, if the number of registers used by the backend is sufficiently lower than this bound, additional CTAs may be mapped to a single multiprocessor. For this reason, .maxnctapersm has been renamed to .minnctapersm in PTX ISA version 2.0.

#### **PTX ISA Notes**

Introduced in PTX ISA version 1.3. Deprecated in PTX ISA version 2.0.

#### **Target ISA Notes**

Supported on all target architectures.

#### **Examples**

.entry foo .maxntid 256 .maxnctapersm 4 { ... }

### 11.4.6. Performance-Tuning Directives: .noreturn

**.noreturn**

Indicate that the function does not return to its caller function.

**Chapter 11. Directives**

**934**

**PTX ISA, Release 9.4**

#### **Syntax**

.noreturn

#### **Description**

Indicate that the function does not return to its caller function.

#### **Semantics**

An optional .noreturn directive indicates that the function does not return to caller function. . noreturn directive can only be specified on device functions and must appear between a .func directive and its body.

The directive cannot be specified on functions which have return parameters.

If a function with .noreturn directive returns to the caller function at runtime, then the behavior is undefined.

#### **PTX ISA Notes**

Introduced in PTX ISA version 6.4.

#### **Target ISA Notes**

Requires sm_30 or higher.

#### **Examples**

.func foo .noreturn { ... }

### 11.4.7. Performance-Tuning Directives: .pragma

#### **.pragma**

Pass directives to PTX backend compiler.

**11.4. Performance-Tuning Directives**

**935**

**PTX ISA, Release 9.4**

#### **Syntax**

.pragma list-of-strings ;

#### **Description**

Pass module-scoped, entry-scoped, or statement-level directives to the PTX backend compiler.

The .pragma directive may occur at module-scope, at entry-scope, or at statement-level.

#### **Semantics**

The interpretation of .pragma directive strings is implementation-specific and has no impact on PTX semantics. See _Descriptions of .pragma Strings_ for descriptions of the pragma strings defined in ptxas .

#### **PTX ISA Notes**

Introduced in PTX ISA version 2.0.

#### **Target ISA Notes**

Supported on all target architectures.

#### **Examples**

.pragma "nounroll"; ∕∕disable unrolling in backend ∕∕disable unrolling for current kernel .entry foo .pragma "nounroll"; { ... }

11.4.8. Performance-Tuning Directives: .abi_preserve

**.abi_preserve**

Specify number of general purpose registers that should be preserved by the callers of this function.

**Chapter 11. Directives**

**936**

**PTX ISA, Release 9.4**

#### **Syntax**

.abi_preserve N

#### **Description**

It is an architecture agnostic value specifying actual number of general purpose registers. Internally ABI defines some general purpose registers as preserved (callee save) registers. Integer N specifies the actual number of general purpose registers that should be preserved by the function.

.abi_preserve directive can only be specified on device functions and must appear between a .func directive and its body.

#### **Semantics**

When this directive is specified compiler backend modifies low level ABI components to ensure that number of live data variables in the callers of this function that are stored in the callee save registers are less than specified value.

#### **PTX ISA Notes**

Introduced in PTX ISA version 9.0.

#### **Target ISA Notes**

Requires sm_80 or higher.

#### **Examples**

.func bar() .abi_preserve 8 ∕∕Indirect call via call prototype .func (.param .b32 out[30]) foo (.param .b32 in[30]) .abi_preserve 10 { ... } ... mov.b64 lpfoo, foo; prot: .callprototype (.param .b32 out[30]) _ (.param .b32 in[30]) .abi_preserve 10; call (out), lpfoo, (in), prot;

11.4.9. Performance-Tuning Directives: .abi_preserve_control

**.abi_preserve_control**

Specify number of control registers that should be preserved by the callers of this function.

**11.4. Performance-Tuning Directives**

**937**

**PTX ISA, Release 9.4**

#### **Syntax**

.abi_preserve_control N

#### **Description**

It is an architecture agnostic value specifying the number of divergent program points that happen in the calltree leading to current function call. Internally ABI defines some control registers as preserved (callee save) registers. Integer N specifies the actual number of control registers that should be preserved by the function.

.abi_preserve_control directive can only be specified on device functions and must appear between a .func directive and its body.

#### **Semantics**

When this directive is specified compiler backend modifies low level ABI components to ensure that number of live control variables in the callers of this function that are stored in the callee save control registers are less than specified value.

#### **PTX ISA Notes**

Introduced in PTX ISA version 9.0.

#### **Target ISA Notes**

Requires sm_80 or higher.

#### **Examples**

.func foo() .abi_preserve_control 14 ∕∕Indirect call via call prototype .func (.param .b32 out[30]) bar (.param .b32 in[30]) .abi_preserve_control 10 { ... } ... mov.b64 lpbar, bar; prot: .callprototype (.param .b32 out[30]) _ (.param .b32 in[30]) .abi_preserve �→_ control 10; call (out), lpbar, (in), prot;

**Chapter 11. Directives**

**938**

**PTX ISA, Release 9.4**

### 11.4.10. Performance-Tuning Directives: .minperctamemory

**.minperctamemory**

Declare minimum per-CTA global memory required by a kernel.

#### **Syntax**

.minperctamemory size; size = 32-bit unsigned integer (bytes)

#### **Description**

The .minperctamemory directive specifies the minimum number of bytes of per-CTA global memory that must be available when this kernel is launched.

The directive is only allowed on .entry functions and must appear between an .entry directive and its body.

Only entry functions specifying this directive are allowed to use special registers %perctamemoryoffset or %perctamemorysize .

#### **PTX ISA Notes**

Introduced in PTX ISA version 9.4.

#### **Target ISA Notes**

Requires sm_80 or higher.

#### **Examples**

.entry foo .minperctamemory 2048 { ... }

**11.4. Performance-Tuning Directives**

**939**

**PTX ISA, Release 9.4**

## 11.5. Debugging Directives

DWARF-format debug information is passed through PTX modules using the following directives:

- @@DWARF

- .section

- .file

- .loc

- .loc_intermediate

- .nv_intermediate_source_section

The .section directive was introduced in PTX ISA version 2.0 and replaces the @@DWARF syntax. The @@DWARF syntax was deprecated in PTX ISA version 2.0 but is supported for legacy PTX ISA version 1.x code.

Beginning with PTX ISA version 3.0, PTX files containing DWARF debug information should include the .target debug platform option. This forward declaration directs PTX compilation to retain mappings for source-level debugging.

### 11.5.1. Debugging Directives: @@dwarf

#### **@@dwarf**

DWARF-format information.

#### **Syntax**

@@DWARF dwarf-string dwarf-string may have one of the .byte byte-list ∕∕comma-separated hexadecimal byte values .4byte int32-list ∕∕comma-separated hexadecimal integers in range [0..2^32-1] .quad int64-list ∕∕comma-separated hexadecimal integers in range [0..2^64-1] .4byte label .quad label

#### **PTX ISA Notes**

Introduced in PTX ISA version 1.2. Deprecated as of PTX ISA version 2.0, replaced by .section directive.

**Chapter 11. Directives**

**940**

**PTX ISA, Release 9.4**

#### **Target ISA Notes**

Supported on all target architectures.

#### **Examples**

@@DWARF .section .debug_pubnames, "", @progbits @@DWARF .byte 0x2b, 0x00, 0x00, 0x00, 0x02, 0x00 @@DWARF .4byte .debug_info @@DWARF .4byte 0x000006b5, 0x00000364, 0x61395a5f, 0x5f736f63 @@DWARF .4byte 0x6e69616d, 0x63613031, 0x6150736f, 0x736d6172 @@DWARF .byte 0x00, 0x00, 0x00, 0x00, 0x00

### 11.5.2. Debugging Directives: .section

**.section**

PTX section definition.

#### **Syntax**

|.section|section_name {|dwarf-lines }|
|---|---|---|
|dwarf-li|nes have the fo|llowing formats:|
|.b8|byte-list|∕∕comma-separated list of integers<br>∕∕in range [-128..255]|
|.b16|int16-list|∕∕comma-separated list of integers|
|||∕∕in range [-2^15..2^16-1]|
|.b32|int32-list|∕∕comma-separated list of integers<br>∕∕in range [-2^31..2^32-1]|
|label:||∕∕Define label inside the debug section|
|.b64|int64-list|∕∕comma-separated list of integers<br>∕∕in range [-2^63..2^64-1]|
|.b32|label||
|.b64|label||
|.b32|label+imm|∕∕a sum of label address plus a constant integer byte<br>∕∕offset(signed, 32bit)|
|.b64|label+imm|∕∕a sum of label address plus a constant integer byte<br>∕∕offset(signed, 64bit)|
|.b32|label1-label2|∕∕a difference in label addresses between labels in<br>∕∕the same dwarf section (32bit)|
|.b64|label3-label4|∕∕a difference in label addresses between labels in<br>∕∕the same dwarf section (64bit)|



**11.5. Debugging Directives**

**941**

**PTX ISA, Release 9.4**

#### **PTX ISA Notes**

Introduced in PTX ISA version 2.0, replaces @@DWARF syntax.

label+imm expression introduced in PTX ISA version 3.2. Support for .b16 integers in dwarf-lines introduced in PTX ISA version 6.0. Support for defining label inside the DWARF section is introduced in PTX ISA version 7.2. label1-label2 expression introduced in PTX ISA version 7.5. Negative numbers in dwarf lines introduced in PTX ISA version 7.5.

#### **Target ISA Notes**

Supported on all target architectures.

#### **Examples**

.section .debug_pubnames { .b32 LpubNames_end0-LpubNames_begin0 LpubNames_begin0: .b8 0x2b, 0x00, 0x00, 0x00, 0x02, 0x00 .b32 .debug_info info_label1: .b32 0x000006b5, 0x00000364, 0x61395a5f, 0x5f736f63 .b32 0x6e69616d, 0x63613031, 0x6150736f, 0x736d6172 .b8 0x00, 0x00, 0x00, 0x00, 0x00 LpubNames_end0: } .section .debug_info { .b32 11430 .b8 2, 0 .b32 .debug_abbrev .b8 8, 1, 108, 103, 101, 110, 102, 101, 58, 32, 69, 68, 71, 32, 52, 46, 49 .b8 0 .b32 3, 37, 176, -99 .b32 info_label1 .b32 .debug_loc+0x4 .b8 -11, 11, 112, 97 .b32 info_label1+12 .b64 -1 .b16 -5, -65535 }

**Chapter 11. Directives**

**942**

**PTX ISA, Release 9.4**

### 11.5.3. Debugging Directives: .file

**.file**

Source file name.

#### **Syntax**

.file file_index "filename" {, timestamp, file_size}

#### **Description**

Associates a source filename with an integer index. .loc directives reference source files by index.

.file directive allows optionally specifying an unsigned number representing time of last modification and an unsigned integer representing size in bytes of source file. timestamp and file_size value can be 0 to indicate this information is not available.

timestamp value is in format of C and C++ data type time_t .

file_size is an unsigned 64-bit integer.

The .file directive is allowed only in the outermost scope, i.e., at the same level as kernel and device function declarations.

#### **Semantics**

If timestamp and file size are not specified, they default to 0.

#### **PTX ISA Notes**

Introduced in PTX ISA version 1.0.

Timestamp and file size introduced in PTX ISA version 3.2.

#### **Target ISA Notes**

Supported on all target architectures.

#### **Examples**

.file 1 "example.cu" .file 2 "kernel.cu" .file 1 "kernel.cu", 1339013327, 64118

**11.5. Debugging Directives**

**943**

**PTX ISA, Release 9.4**

### 11.5.4. Debugging Directives: .loc

**.loc**

Source file location.

#### **Syntax**

.loc file_index line_number column_position .loc file_index line_number column_position,function_name label {+ immediate }, _�→_ inlined_at file_index2 line_number2 column_position2

#### **Description**

Declares the source file location (source file, line number, and column position) to be associated with lexically subsequent PTX instructions. .loc refers to file_index which is defined by a .file directive.

To indicate PTX instructions that are generated from a function that got inlined, additional attribute .inlined_at can be specified as part of the .loc directive. .inlined_at attribute specifies source location at which the specified function is inlined. file_index2 , line_number2 , and column_position2 specify the location at which function is inlined. Source location specified as part of .inlined_at directive must lexically precede as source location in .loc directive.

The function_name attribute specifies an offset in the DWARF section named .debug_str . Offset is specified as label expression or label + immediate expression where label is defined in . debug_str section. DWARF section .debug_str contains ASCII null-terminated strings that specify the name of the function that is inlined.

Note that a PTX instruction may have a single associated source location, determined by the nearest lexically preceding .loc directive, or no associated source location if there is no preceding .loc directive. Labels in PTX inherit the location of the closest lexically following instruction. A label with no following PTX instruction has no associated source location.

#### **PTX ISA Notes**

Introduced in PTX ISA version 1.0.

function_name and inlined_at attributes are introduced in PTX ISA version 7.2.

#### **Target ISA Notes**

Supported on all target architectures.

**Chapter 11. Directives**

**944**

**PTX ISA, Release 9.4**

#### **Examples**

.loc 2 4237 0 L1: ∕∕line 4237, col 0 of file #2, ∕∕inherited from mov mov.u32 %r1,%r2; ∕∕line 4237, col 0 of file #2 add.u32 %r2,%r1,%r3; ∕∕line 4237, col 0 of file #2 ... L2: ∕∕line 4239, col 5 of file #2, ∕∕inherited from sub .loc 2 4239 5 sub.u32 %r2,%r1,%r3; ∕∕line 4239, col 5 of file #2 .loc 1 21 3 .loc 1 9 3, function_name info_string0, inlined_at 1 21 3 ld.global.u32 %r1, [gg]; ∕∕Function at line 9 setp.lt.s32 %p1, %r1, 8; ∕∕inlined at line 21 .loc 1 27 3 .loc 1 10 5, function_name info_string1, inlined_at 1 27 3 .loc 1 15 3, function_name .debug_str+16, inlined_at 1 10 5 setp.ne.s32 %p2, %r1, 18; @%p2 bra BB2_3; .section .debug_str { info_string0: .b8 95 ∕∕_ .b8 90 ∕∕z .b8 51 ∕∕3 .b8 102 ∕∕f .b8 111 ∕∕o .b8 111 ∕∕o .b8 118 ∕∕v .b8 0 info_string1: .b8 95 ∕∕_ .b8 90 ∕∕z .b8 51 ∕∕3 .b8 98 ∕∕b .b8 97 ∕∕a .b8 114 ∕∕r .b8 118 ∕∕v .b8 0 .b8 95 ∕∕_ .b8 90 ∕∕z .b8 51 ∕∕3 .b8 99 ∕∕c .b8 97 ∕∕a .b8 114 ∕∕r .b8 118 ∕∕v .b8 0 }

**11.5. Debugging Directives**

**945**

**PTX ISA, Release 9.4**

### 11.5.5. Debugging Directives: .loc_intermediate

**.loc_intermediate**

Intermediate language source file location.

#### **Syntax**

.loc_intermediate file_index line_number column_position

#### **Description**

Declares the intermediate-language source location (source file, line number, and column position) to be associated with the immediately following PTX instruction. .loc_intermediate refers to file_index which must be defined by a .file directive that names an intermediate IR source file.

A .loc_intermediate directive must be immediately preceded, in program order, by a .loc directive for the same instruction. Only one .loc_intermediate may appear per instruction. Unlike .loc , the .loc_intermediate directive does not support the inlined_at attribute.

The intermediate source location is recorded in the secondary debug line table which is based on ir-name in .nv_intermediate_source_section and is not merged into the primary DWARF . debug_line or .nv_debug_line_ptx sections. The .loc_intermediate directive is allowed only inside kernel or device function bodies.

#### **PTX ISA Notes**

Introduced in PTX ISA version 9.4.

#### **Target ISA Notes**

Supported on all target architectures.

#### **Examples**

.func (.param .b32 func_retval0) _Z17noinline_multiplyii( .param .b32 _Z17noinline_multiplyii_param_0, .param .b32 _Z17noinline_multiplyii_param_1 ) { .reg .b32 %r<4>; .loc 1 71 0 ld.param.b32 %r1, [_Z17noinline_multiplyii_param_0]; ld.param.b32 %r2, [_Z17noinline_multiplyii_param_1]; .loc 1 72 5 .loc_intermediate 2 23 6 ∕∕tileIR_source.ir:23:6 mul.lo.s32 %r3, %r2, %r1; .loc 1 73 5 .loc_intermediate 2 24 0 ∕∕tileIR_source.ir:24:0

(continues on next page)

**Chapter 11. Directives**

**946**

**PTX ISA, Release 9.4**

(continued from previous page)

add.lo.s32 %r3, %r3, %r1; } .file 1 "∕path∕to∕vectorAdd.cu" .file 2 ".∕tileIR_source.ir"

### 11.5.6. Debugging Directives: .nv_intermediate_source_section

**.nv_intermediate_source_section**

Embed intermediate IR source code in the PTX module.

#### **Syntax**

.nv_intermediate_source_section { .code_block { .ir_name: ir-name-string .sourceFileName: file-index .source_begin source-text .source_end } [ .code_block { ... } ]* } ir-name-string = quoted string identifier (e.g., "TileIR") file-index = unsigned integer matching a .file directive source-text = raw text of the intermediate IR source (heredoc)

#### **Description**

The .nv_intermediate_source_section construct embeds the source code of one or more intermediate IR compilation units directly into the PTX module. Each .code_block entry associates an ir_name string (identifying the intermediate language, e.g., "TileIR" ) with a .file index and the raw text of that source file.

The .sourceFileName field must reference a file_index already declared by a .file directive in the same PTX module. The .source_begin and .source_end constructs indicate the start and end of the source text and may contain arbitrary text including newlines.

Each .code_block produces a separate ELF section with name based on the specified ir_name . Currently only "TileIR" is supported for ir-name . The .nv_intermediate_source_section is allowed only at module scope. Multiple .nv_intermediate_source_section blocks may appear in a single PTX module; their .code_block entries are concatenated in order.

**11.5. Debugging Directives**

**947**

**PTX ISA, Release 9.4**

#### **PTX ISA Notes**

Introduced in PTX ISA version 9.4.

#### **Target ISA Notes**

Supported on all target architectures.

#### **Examples**

.visible .entry _Z9vectorAddPf( .param .u64 .ptr .align 1 _Z9vectorAddPf_param_0 ) { .loc 1 11 15 .loc_intermediate 2 137 23 ld.b64 %rd2, [%SP]; .loc 1 12 15 .loc_intermediate 3 24 23 ld.b64 %rd3, [%SP]; } .file 1 ".∕vectorAdd.cu" .file 2 ".∕tileIR_source_A.ir" .file 3 ".∕tileIR_source_B.ir" .nv_intermediate_source_section { .code_block { .ir_name: "TileIR" .sourceFileName: 2 .source_begin __global__ void vectorAdd(float *v) { float a, b; *v = a + b; } .source_end } .code_block { .ir_name: "TileIR" .sourceFileName: 3 .source_begin __global__ void vectorSub(float *v) { float a, b; *v = a - b; } .source_end } }

## 11.6. Linking Directives

▶ .extern

▶ .visible

▶ .weak

**Chapter 11. Directives**

**948**

**PTX ISA, Release 9.4**

### 11.6.1. Linking Directives: .extern

**.extern**

External symbol declaration.

#### **Syntax**

.extern identifier

#### **Description**

Declares identifier to be defined external to the current module. The module defining such identifier must define it as .weak or .visible only once in a single object file. Extern declaration of symbol may appear multiple times and references to that get resolved against the single definition of that symbol.

#### **PTX ISA Notes**

Introduced in PTX ISA version 1.0.

#### **Target ISA Notes**

Supported on all target architectures.

#### **Examples**

.extern .global .b32 foo; ∕∕foo is defined in another module

### 11.6.2. Linking Directives: .visible

**.visible**

Visible (externally) symbol declaration.

**11.6. Linking Directives**

**949**

**PTX ISA, Release 9.4**

#### **Syntax**

.visible identifier

#### **Description**

Declares identifier to be globally visible. Unlike C, where identifiers are globally visible unless declared static, PTX identifiers are visible only within the current module unless declared .visible outside the current.

#### **PTX ISA Notes**

Introduced in PTX ISA version 1.0.

#### **Target ISA Notes**

Supported on all target architectures.

#### **Examples**

.visible .global .b32 foo; ∕∕foo will be externally visible

### 11.6.3. Linking Directives: .weak

**.weak**

Visible (externally) symbol declaration.

#### **Syntax**

.weak identifier

#### **Description**

Declares identifier to be globally visible but _weak_ . Weak symbols are similar to globally visible symbols, except during linking, weak symbols are only chosen after globally visible symbols during symbol resolution. Unlike globally visible symbols, multiple object files may declare the same weak symbol, and references to a symbol get resolved against a weak symbol only if no global symbols have the same name.

**Chapter 11. Directives**

**950**

**PTX ISA, Release 9.4**

#### **PTX ISA Notes**

Introduced in PTX ISA version 3.1.

#### **Target ISA Notes**

Supported on all target architectures.

#### **Examples**

.weak .func (.reg .b32 val) foo; ∕∕foo will be externally visible

### 11.6.4. Linking Directives: .common

**.common**

Visible (externally) symbol declaration.

#### **Syntax**

.common identifier

#### **Description**

Declares identifier to be globally visible but “common”.

Common symbols are similar to globally visible symbols. However multiple object files may declare the same common symbol and they may have different types and sizes and references to a symbol get resolved against a common symbol with the largest size.

Only one object file can initialize a common symbol and that must have the largest size among all other definitions of that common symbol from different object files.

.common linking directive can be used only on variables with .global storage. It cannot be used on function symbols or on symbols with opaque type.

#### **PTX ISA Notes**

Introduced in PTX ISA version 5.0.

**11.6. Linking Directives**

**951**

**PTX ISA, Release 9.4**

#### **Target ISA Notes**

.common directive requires sm_20 or higher.

#### **Examples**

.common .global .u32 gbl;

## 11.7. Cluster Dimension Directives

The following directives specify information about clusters:

- .reqnctapercluster

- .explicitcluster

- .maxclusterrank

The .reqnctapercluster directive specifies the number of CTAs in the cluster. The . explicitcluster directive specifies that the kernel should be launched with explicit cluster details. The .maxclusterrank directive specifies the maximum number of CTAs in the cluster.

The cluster dimension directives can be applied only on kernel functions.

### 11.7.1. Cluster Dimension Directives: .reqnctapercluster

**.reqnctapercluster**

Declare the number of CTAs in the cluster.

#### **Syntax**

.reqnctapercluster nx .reqnctapercluster nx, ny .reqnctapercluster nx, ny, nz

**Chapter 11. Directives**

**952**

**PTX ISA, Release 9.4**

#### **Description**

Set the number of thread blocks (CTAs) in the cluster by specifying the extent of each dimension of the 1D, 2D, or 3D cluster. The total number of CTAs is the product of the number of CTAs in each dimension. For kernels with .reqnctapercluster directive specified, runtime will use the specified values for configuring the launch if the same are not specified at launch time.

#### **Semantics**

If cluster dimension is explicitly specified at launch time, it should be equal to the values specified in this directive. Specifying a different cluster dimension at launch will result in a runtime error or kernel launch failure.

#### **PTX ISA Notes**

Introduced in PTX ISA version 7.8.

#### **Target ISA Notes**

Requires sm_90 or higher.

#### **Examples**

.entry foo .reqnctapercluster 2 { . . . } .entry bar .reqnctapercluster 2, 2, 1 { . . . } .entry ker .reqnctapercluster 3, 2 { . . . }

11.7.2. Cluster Dimension Directives: .explicitcluster

**.explicitcluster**

Declare that Kernel must be launched with cluster dimensions explicitly specified.

#### **Syntax**

.explicitcluster

**11.7. Cluster Dimension Directives**

**953**

**PTX ISA, Release 9.4**

#### **Description**

Declares that this Kernel should be launched with cluster dimension explicitly specified.

#### **Semantics**

Kernels with .explicitcluster directive must be launched with cluster dimension explicitly specified (either at launch time or via .reqnctapercluster ), otherwise program will fail with runtime error or kernel launch failure.

#### **PTX ISA Notes**

Introduced in PTX ISA version 7.8.

#### **Target ISA Notes**

Requires sm_90 or higher.

#### **Examples**

.entry foo .explicitcluster { . . . }

11.7.3. Cluster Dimension Directives: .maxclusterrank

**.maxclusterrank**

Declare the maximum number of CTAs that can be part of the cluster.

#### **Syntax**

.maxclusterrank n

#### **Description**

Declare the maximum number of thread blocks (CTAs) allowed to be part of the cluster.

**Chapter 11. Directives**

**954**

**PTX ISA, Release 9.4**

#### **Semantics**

Product of the number of CTAs in each cluster dimension specified in any invocation of the kernel is required to be less or equal to that specified in this directive. Otherwise invocation will result in a runtime error or kernel launch failure.

The .maxclusterrank directive cannot be used in conjunction with the .reqnctapercluster directive.

#### **PTX ISA Notes**

Introduced in PTX ISA version 7.8.

#### **Target ISA Notes**

Requires sm_90 or higher.

#### **Examples**

.entry foo ..maxclusterrank 8 { . . . }

## 11.8. Miscellaneous Directives

PTX provides the following miscellaneous directives:

▶ .blocksareclusters

▶ .language

### 11.8.1. Miscellaneous Directives: .blocksareclusters

#### **.blocksareclusters**

Specify that CUDA thread blocks are mapped to clusters.

#### **Syntax**

.blocksareclusters

**11.8. Miscellaneous Directives**

**955**

**PTX ISA, Release 9.4**

#### **Description**

Default behavior of CUDA API is to specify the grid launch configuration by specifying the number of thread blocks and the number of threads per block.

When .blocksareclusters directive is specified, it implies that the grid launch configuration for the corresponding .entry function is specifying the number of clusters, i.e. the launch configuration is specifying number of clusters instead of the number of thread blocks. In this case, the number of thread blocks per cluster is specified by .reqnctapercluster directive and the thread block size is specified with the .reqntid directive.

.blocksareclusters directive is only allowed for .entry functions and also needs .reqntid and .reqnctapercluster directives to be specified.

Refer to _CUDA Programming Guide_ for more details.

#### **PTX ISA Notes**

Introduced in PTX ISA version 9.0.

#### **Target ISA Notes**

Requires sm_90 or higher.

#### **Examples**

.entry foo .reqntid 32, 32, 1 .reqnctapercluster 32, 32, 1 .blocksareclusters { ... }

### 11.8.2. Miscellaneous Directives: .language

**.language**

Specify the source language(s) used to generate the kernel or function.

#### **Syntax**

.language lang-list ∕∕comma separated list of strings or integers

**Chapter 11. Directives**

**956**

**PTX ISA, Release 9.4**

#### **Description**

The .language directive declares the source language(s) from which the code for the corresponding .entry or .func function was generated. The directive accepts a comma-separated list of language codes, specified as either quoted string names or unsigned integer values.

The .language directive is allowed for both .entry and .func functions and must appear between the function directive and its body.

If the .language directive is not specified, the language defaults to "ptx" .

Multiple languages may be specified for a single function, indicating mixed-language origins. Language names are case-insensitive.

Language codes specified as unsigned integers must be in the range [0..10] . The mapping between string names and integer codes is:

|**Code**|**String**|
|---|---|
|0|“unknown”|
|1|Reserved|
|2|Reserved|
|3|“ptx”|
|4|“nvvm”|
|5|“cuda c++”|
|6|“cuda c++ tile”|
|7|“tile ir”|
|8|“python-cutile”|
|9|“fortran”|
|10|“optix”|



#### **PTX ISA Notes**

Introduced in PTX ISA version 9.3.

#### **Target ISA Notes**

Supported on all target architectures.

**11.8. Miscellaneous Directives**

**957**

**PTX ISA, Release 9.4**

#### **Examples**

.entry foo () .language "ptx" { ... } .func bar () .language "nvvm", "ptx" { ... } .entry baz () .language "ptx", "cuda c++", 0x7 { ... }

**Chapter 11. Directives**

**958**
