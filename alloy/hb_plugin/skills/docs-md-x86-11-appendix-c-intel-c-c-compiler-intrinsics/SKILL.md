---
name: docs-md-x86-11-appendix-c-intel-c-c-compiler-intrinsics
description: "Intel SDM Vol. 2: Appendix C Intel\u00ae C/C++ Compiler Intrinsics and Functional Equivalents (vendor documentation for x86 AVX2, AVX-512 and AVX-512 FP16)."
when: "when you need Intel SDM Vol. 2: Appendix C Intel\u00ae C/C++ Compiler Intrinsics and Functional Equivalents while writing a kernel for x86 AVX2, AVX-512 and AVX-512 FP16."
---

APPENDIX C

# INTEL® C/C++ COMPILER INTRINSICS AND FUNCTIONAL EQUIVALENTS

The two tables in this appendix itemize the Intel C/C ++ compiler intrinsics and functional equivalents for the Intel MMX technology, SSE, SSE2, SSE3, and SSSE3 instructions.

There may be additional intrinsics that do not have an instruction equivalent. It is strongly recommended that the reader reference the compiler documentation for the complete list of supported intrinsics. Please refer to http://www.intel.com/support/performancetools/.

Table C-1 presents simple intrinsics and Table C-2 presents composite intrinsics. Some intrinsics are “composites” because they require more than one instruction to implement them.

Intel C/C ++ Compiler intrinsic names reflect the following naming conventions:

_mm_<intrin_op>_<suffix>

where:

< intrin_op > Indicates the intrinsics basic operation; for example, add for addition and sub for subtraction < suffix > Denotes the type of data operated on by the instruction. The first one or two letters of each suffix denotes whether the data is packed (p), extended packed (ep), or scalar (s). The remaining letters denote the type: s single-precision floating-point d double precision floating-point i128 signed 128-bit integer i64 signed 64-bit integer u64 unsigned 64-bit integer i32 signed 32-bit integer u32 unsigned 32-bit integer i16 signed 16-bit integer u16 unsigned 16-bit integer i8 signed 8-bit integer u8 unsigned 8-bit integer

The remaining letters denote the type:

The variable r is generally used for the intrinsic's return value. A number appended to a variable name indicates the element of a packed object. For example, r0 is the lowest word of r.

The packed values are represented in right-to-left order, with the lowest value being used for scalar operations. Consider the following example operation:

double a[2] = {1.0, 2.0};

__m128d t = _mm_load_pd(a);

The result is the same as either of the following:

__m128d t = _mm_set_pd(2.0, 1.0);

__m128d t = _mm_setr_pd(1.0, 2.0);

In other words, the XMM register that holds the value t will look as follows:

||2.0||1.0|
|---|---|---|---|
|127||64 63|0|



Vol. 2D C-1

INTEL® C/C++ COMPILER INTRINSICS AND FUNCTIONAL EQUIVALENTS

The “scalar” element is 1.0. Due to the nature of the instruction, some intrinsics require their arguments to be immediates (constant integer literals).

To use an intrinsic in your code, insert a line with the following syntax:

data_type intrinsic_name (parameters)

Where:

data_type Is the return data type, which can be either void, int, __m64, __m128, __m128d, or __m128i. Only the _mm_empty intrinsic returns void.

intrinsic_name Is the name of the intrinsic, which behaves like a function that you can use in your C/C ++ code instead of in-lining the actual instruction. parameters Represents the parameters required by each intrinsic.

## C.1 SIMPLE INTRINSICS

### NOTE

For detailed descriptions of the intrinsics in Table C-1, see the corresponding mnemonic in Chapter 3, “Instruction Set Reference, A-L” of the _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 2A_ ; Chapter 4, “Instruction Set Reference, M-U” of the _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 2B_ ; Chapter 5, “Instruction Set Reference, V,” of the _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 2C_ ; or Chapter 6, “Instruction Set Reference, W-Z,” of the _Intel® 64 and IA-32 Architectures Software Developer’s Manual, Volume 2D_ .

Table C-1.  Simple Intrinsics

|Mnemonic|Intrinsic|
|---|---|
|ADDPD|__m128d _mm_add_pd(__m128d a, __m128d b)|
|ADDPS|__m128 _mm_add_ps(__m128 a, __m128 b)|
|ADDSD|__m128d _mm_add_sd(__m128d a, __m128d b)|
|ADDSS|__m128 _mm_add_ss(__m128 a, __m128 b)|
|ADDSUBPD|__m128d _mm_addsub_pd(__m128d a, __m128d b)|
|ADDSUBPS|__m128 _mm_addsub_ps(__m128 a, __m128 b)|
|AESDEC|__m128i _mm_aesdec (__m128i, __m128i)|
|AESDECLAST|__m128i _mm_aesdeclast (__m128i, __m128i)|
|AESENC|__m128i _mm_aesenc (__m128i, __m128i)|
|AESENCLAST|__m128i _mm_aesenclast (__m128i, __m128i)|
|AESIMC|__m128i _mm_aesimc (__m128i)|
|AESKEYGENASSIST|__m128i _mm_aesimc (__m128i, const int)|
|ANDNPD|__m128d _mm_andnot_pd(__m128d a, __m128d b)|
|ANDNPS|__m128 _mm_andnot_ps(__m128 a, __m128 b)|
|ANDPD|__m128d _mm_and_pd(__m128d a, __m128d b)|
|ANDPS|__m128 _mm_and_ps(__m128 a, __m128 b)|
|BLENDPD|__m128d _mm_blend_pd(__m128d v1, __m128d v2, const int mask)|
|BLENDPS|__m128 _mm_blend_ps(__m128 v1, __m128 v2, const int mask)|
|BLENDVPD|__m128d _mm_blendv_pd(__m128d v1, __m128d v2, __m128d v3)|
|BLENDVPS|__m128 _mm_blendv_ps(__m128 v1, __m128 v2, __m128 v3)|
|CLFLUSH|void _mm_clflush(void const *p)|



C-2 Vol. 2D

INTEL® C/C++ COMPILER INTRINSICS AND FUNCTIONAL EQUIVALENTS

Table C-1.  Simple Intrinsics (Contd.)

|Mnemonic||Intrinsic|
|---|---|---|
|CMPPD|__m128d _mm_cmpeq_pd(|__m128d a, __m128d b)|
||__m128d _mm_cmplt_pd(_|_m128d a, __m128d b)|
||__m128d _mm_cmple_pd(_|_m128d a, __m128d b)|
||__m128d _mm_cmpgt_pd(_|_m128d a, __m128d b)|
||__m128d _mm_cmpge_pd(|__m128d a, __m128d b)|
||__m128d _mm_cmpneq_pd|(__m128d a, __m128d b)|
||__m128d _mm_cmpnlt_pd(|__m128d a, __m128d b)|
||__m128d _mm_cmpngt_pd|(__m128d a, __m128d b)|
||__m128d _mm_cmpnge_pd|(__m128d a, __m128d b)|
||__m128d _mm_cmpord_pd|(__m128d a, __m128d b)|
||__m128d _mm_cmpunord_|pd(__m128d a, __m128d b)|
||__m128d _mm_cmpnle_pd(|__m128d a, __m128d b)|
|CMPPS|__m128 _mm_cmpeq_ps(_|_m128 a, __m128 b)|
||__m128 _mm_cmplt_ps(__|m128 a, __m128 b)|
||__m128 _mm_cmple_ps(__|m128 a, __m128 b)|
||__m128 _mm_cmpgt_ps(__|m128 a, __m128 b)|
||__m128 _mm_cmpge_ps(_|_m128 a, __m128 b)|
||__m128 _mm_cmpneq_ps(|__m128 a, __m128 b)|
||__m128 _mm_cmpnlt_ps(_|_m128 a, __m128 b)|
||__m128 _mm_cmpngt_ps(_|_m128 a, __m128 b)|
||__m128 _mm_cmpnge_ps(|__m128 a, __m128 b)|
||__m128 _mm_cmpord_ps(_|_m128 a, __m128 b)|
||__m128 _mm_cmpunord_p|s(__m128 a, __m128 b)|
||__m128 _mm_cmpnle_ps(_|_m128 a, __m128 b)|
|CMPSD|__m128d _mm_cmpeq_sd(|__m128d a, __m128d b)|
||__m128d _mm_cmplt_sd(_|_m128d a, __m128d b)|
||__m128d _mm_cmple_sd(_|_m128d a, __m128d b)|
||__m128d _mm_cmpgt_sd(_|_m128d a, __m128d b)|
||__m128d _mm_cmpge_sd(|__m128d a, __m128d b)|
||__m128 _mm_cmpneq_sd(|__m128d a, __m128d b)|
||__m128 _mm_cmpnlt_sd(_|_m128d a, __m128d b)|
||__m128d _mm_cmpnle_sd(|__m128d a, __m128d b)|
||__m128d _mm_cmpngt_sd|(__m128d a, __m128d b)|
||__m128d _mm_cmpnge_sd|(__m128d a, __m128d b)|
||__m128d _mm_cmpord_sd(|__m128d a, __m128d b)|
||__m128d _mm_cmpunord_|sd(__m128d a, __m128d b)|
|CMPSS|__m128 _mm_cmpeq_ss(__|m128 a, __m128 b)|
||__m128 _mm_cmplt_ss(__|m128 a, __m128 b)|
||__m128 _mm_cmple_ss(__|m128 a, __m128 b)|
||__m128 _mm_cmpgt_ss(__|m128 a, __m128 b)|
||__m128 _mm_cmpge_ss(__|m128 a, __m128 b)|



Vol. 2D C-3

INTEL® C/C++ COMPILER INTRINSICS AND FUNCTIONAL EQUIVALENTS

Table C-1.  Simple Intrinsics (Contd.)

|Mnemonic|Intrinsic|
|---|---|
||__m128 _mm_cmpneq_ss(__m128 a, __m128 b)|
||__m128 _mm_cmpnlt_ss(__m128 a, __m128 b)|
||__m128 _mm_cmpnle_ss(__m128 a, __m128 b)|
||__m128 _mm_cmpngt_ss(__m128 a, __m128 b)|
||__m128 _mm_cmpnge_ss(__m128 a, __m128 b)|
||__m128 _mm_cmpord_ss(__m128 a, __m128 b)|
||__m128 _mm_cmpunord_ss(__m128 a, __m128 b)|
|COMISD|int _mm_comieq_sd(__m128d a, __m128d b)|
||int _mm_comilt_sd(__m128d a, __m128d b)|
||int _mm_comile_sd(__m128d a, __m128d b)|
||int _mm_comigt_sd(__m128d a, __m128d b)|
||int _mm_comige_sd(__m128d a, __m128d b)|
||int _mm_comineq_sd(__m128d a, __m128d b)|
|COMISS|int _mm_comieq_ss(__m128 a, __m128 b)|
||int _mm_comilt_ss(__m128 a, __m128 b)|
||int _mm_comile_ss(__m128 a, __m128 b)|
||int _mm_comigt_ss(__m128 a, __m128 b)|
||int _mm_comige_ss(__m128 a, __m128 b)|
||int _mm_comineq_ss(__m128 a, __m128 b)|
|CRC32|unsigned int _mm_crc32_u8(unsigned int crc, unsigned char data)|
||unsigned int _mm_crc32_u16(unsigned int crc, unsigned short data)|
||unsigned int _mm_crc32_u32(unsigned int crc, unsigned int data)|
||unsigned __int64 _mm_crc32_u64(unsigned __int64 crc, unsigned __int64 data)|
|CVTDQ2PD|__m128d _mm_cvtepi32_pd(__m128i a)|
|CVTDQ2PS|__m128 _mm_cvtepi32_ps(__m128i a)|
|CVTPD2DQ|__m128i _mm_cvtpd_epi32(__m128d a)|
|CVTPD2PI|__m64 _mm_cvtpd_pi32(__m128d a)|
|CVTPD2PS|__m128 _mm_cvtpd_ps(__m128d a)|
|CVTPI2PD|__m128d _mm_cvtpi32_pd(__m64 a)|
|CVTPI2PS|__m128 _mm_cvt_pi2ps(__m128 a, __m64 b)<br>__m128 _mm_cvtpi32_ps(__m128 a, __m64 b)|
|CVTPS2DQ|__m128i _mm_cvtps_epi32(__m128 a)|
|CVTPS2PD|__m128d _mm_cvtps_pd(__m128 a)|
|CVTPS2PI|__m64 _mm_cvt_ps2pi(__m128 a)<br>__m64 _mm_cvtps_pi32(__m128 a)|
|CVTSD2SI|int _mm_cvtsd_si32(__m128d a)|
|CVTSD2SS|__m128 _mm_cvtsd_ss(__m128 a, __m128d b)|
|CVTSI2SD|__m128d _mm_cvtsi32_sd(__m128d a, int b)|
|CVTSI2SS|__m128 _mm_cvt_si2ss(__m128 a, int b)<br>__m128 _mm_cvtsi32_ss(__m128 a, int b)<br>__m128 _mm_cvtsi64_ss(__m128 a, __int64 b)|
|CVTSS2SD|__m128d _mm_cvtss_sd(__m128d a, __m128 b)|



C-4 Vol. 2D

INTEL® C/C++ COMPILER INTRINSICS AND FUNCTIONAL EQUIVALENTS

Table C-1.  Simple Intrinsics (Contd.)

|Mnemonic|Intrinsic|
|---|---|
|CVTSS2SI|int _mm_cvt_ss2si(__m128 a)<br>int _mm_cvtss_si32(__m128 a)|
|CVTTPD2DQ|__m128i _mm_cvttpd_epi32(__m128d a)|
|CVTTPD2PI|__m64 _mm_cvttpd_pi32(__m128d a)|
|CVTTPS2DQ|__m128i _mm_cvttps_epi32(__m128 a)|
|CVTTPS2PI|__m64 _mm_cvtt_ps2pi(__m128 a)<br>__m64 _mm_cvttps_pi32(__m128 a)|
|CVTTSD2SI|int _mm_cvttsd_si32(__m128d a)|
|CVTTSS2SI|int _mm_cvtt_ss2si(__m128 a)<br>int _mm_cvttss_si32(__m128 a)<br>__m64 _mm_cvtsi32_si64(int i)<br>int _mm_cvtsi64_si32(__m64 m)|
|DIVPD|__m128d _mm_div_pd(__m128d a, __m128d b)|
|DIVPS|__m128 _mm_div_ps(__m128 a, __m128 b)|
|DIVSD|__m128d _mm_div_sd(__m128d a, __m128d b)|
|DIVSS|__m128 _mm_div_ss(__m128 a, __m128 b)|
|DPPD|__m128d _mm_dp_pd(__m128d a, __m128d b, const int mask)|
|DPPS|__m128 _mm_dp_ps(__m128 a, __m128 b, const int mask)|
|EMMS|void _mm_empty()|
|EXTRACTPS|int _mm_extract_ps(__m128 src, const int ndx)|
|HADDPD|__m128d _mm_hadd_pd(__m128d a, __m128d b)|
|HADDPS|__m128 _mm_hadd_ps(__m128 a, __m128 b)|
|HSUBPD|__m128d _mm_hsub_pd(__m128d a, __m128d b)|
|HSUBPS|__m128 _mm_hsub_ps(__m128 a, __m128 b)|
|INSERTPS|__m128 _mm_insert_ps(__m128 dst, __m128 src, const int ndx)|
|LDDQU|__m128i _mm_lddqu_si128(__m128i const *p)|
|LDMXCSR|__mm_setcsr(unsigned int i)|
|LFENCE|void _mm_lfence(void)|
|MASKMOVDQU|void _mm_maskmoveu_si128(__m128i d, __m128i n, char *p)|
|MASKMOVQ|void _mm_maskmove_si64(__m64 d, __m64 n, char *p)|
|MAXPD|__m128d _mm_max_pd(__m128d a, __m128d b)|
|MAXPS|__m128 _mm_max_ps(__m128 a, __m128 b)|
|MAXSD|__m128d _mm_max_sd(__m128d a, __m128d b)|
|MAXSS|__m128 _mm_max_ss(__m128 a, __m128 b)|
|MFENCE|void _mm_mfence(void)|
|MINPD|__m128d _mm_min_pd(__m128d a, __m128d b)|
|MINPS|__m128 _mm_min_ps(__m128 a, __m128 b)|
|MINSD|__m128d _mm_min_sd(__m128d a, __m128d b)|
|MINSS|__m128 _mm_min_ss(__m128 a, __m128 b)|
|MONITOR|void _mm_monitor(void const *p, unsigned extensions, unsigned hints)|
|MOVAPD|__m128d _mm_load_pd(double * p)|
||void_mm_store_pd(double *p, __m128d a)|



Vol. 2D C-5

INTEL® C/C++ COMPILER INTRINSICS AND FUNCTIONAL EQUIVALENTS

Table C-1.  Simple Intrinsics (Contd.)

|Mnemonic|Intrinsic|
|---|---|
|MOVAPS|__m128 _mm_load_ps(float * p)|
||void_mm_store_ps(float *p, __m128 a)|
|MOVD|__m128i _mm_cvtsi32_si128(int a)|
||int _mm_cvtsi128_si32(__m128i a)|
||__m64 _mm_cvtsi32_si64(int a)|
||int _mm_cvtsi64_si32(__m64 a)|
|MOVDDUP|__m128d _mm_movedup_pd(__m128d a)|
||__m128d _mm_loaddup_pd(double const * dp)|
|MOVDQA|__m128i _mm_load_si128(__m128i * p)|
||void_mm_store_si128(__m128i *p, __m128i a)|
|MOVDQU|__m128i _mm_loadu_si128(__m128i * p)|
||void_mm_storeu_si128(__m128i *p, __m128i a)|
|MOVDQ2Q|__m64 _mm_movepi64_pi64(__m128i a)|
|MOVHLPS|__m128 _mm_movehl_ps(__m128 a, __m128 b)|
|MOVHPD|__m128d _mm_loadh_pd(__m128d a, double * p)|
||void _mm_storeh_pd(double * p, __m128d a)|
|MOVHPS|__m128 _mm_loadh_pi(__m128 a, __m64 * p)|
||void _mm_storeh_pi(__m64 * p, __m128 a)|
|MOVLPD|__m128d _mm_loadl_pd(__m128d a, double * p)|
||void _mm_storel_pd(double * p, __m128d a)|
|MOVLPS|__m128 _mm_loadl_pi(__m128 a, __m64 *p)|
||void_mm_storel_pi(__m64 * p, __m128 a)|
|MOVLHPS|__m128 _mm_movelh_ps(__m128 a, __m128 b)|
|MOVMSKPD|int _mm_movemask_pd(__m128d a)|
|MOVMSKPS|int _mm_movemask_ps(__m128 a)|
|MOVNTDQA|__m128i _mm_stream_load_si128(__m128i *p)|
|MOVNTDQ|void_mm_stream_si128(__m128i * p, __m128i a)|
|MOVNTPD|void_mm_stream_pd(double * p, __m128d a)|
|MOVNTPS|void_mm_stream_ps(float * p, __m128 a)|
|MOVNTI|void_mm_stream_si32(int * p, int a)|
|MOVNTQ|void_mm_stream_pi(__m64 * p, __m64 a)|
|MOVQ|__m128i _mm_loadl_epi64(__m128i * p)|
||void_mm_storel_epi64(_m128i * p, __m128i a)|
||__m128i _mm_move_epi64(__m128i a)|
|MOVQ2DQ|__m128i _mm_movpi64_epi64(__m64 a)|
|MOVSD|__m128d _mm_load_sd(double * p)|
||void_mm_store_sd(double * p, __m128d a)|
||__m128d _mm_move_sd(__m128d a, __m128d b)|
|MOVSHDUP|__m128 _mm_movehdup_ps(__m128 a)|
|MOVSLDUP|__m128 _mm_moveldup_ps(__m128 a)|
|MOVSS|__m128 _mm_load_ss(float * p)|



C-6 Vol. 2D

INTEL® C/C++ COMPILER INTRINSICS AND FUNCTIONAL EQUIVALENTS

Table C-1.  Simple Intrinsics (Contd.)

|Mnemonic|Intrinsic|
|---|---|
||void_mm_store_ss(float * p, __m128 a)|
||__m128 _mm_move_ss(__m128 a, __m128 b)|
|MOVUPD|__m128d _mm_loadu_pd(double * p)|
||void_mm_storeu_pd(double *p, __m128d a)|
|MOVUPS|__m128 _mm_loadu_ps(float * p)|
||void_mm_storeu_ps(float *p, __m128 a)|
|MPSADBW|__m128i _mm_mpsadbw_epu8(__m128i s1, __m128i s2, const int mask)|
|MULPD|__m128d _mm_mul_pd(__m128d a, __m128d b)|
|MULPS|__m128 _mm_mul_ss(__m128 a, __m128 b)|
|MULSD|__m128d _mm_mul_sd(__m128d a, __m128d b)|
|MULSS|__m128 _mm_mul_ss(__m128 a, __m128 b)|
|MWAIT|void _mm_mwait(unsigned extensions, unsigned hints)|
|ORPD|__m128d _mm_or_pd(__m128d a, __m128d b)|
|ORPS|__m128 _mm_or_ps(__m128 a, __m128 b)|
|PABSB|__m64 _mm_abs_pi8 (__m64 a)|
||__m128i _mm_abs_epi8 (__m128i a)|
|PABSD|__m64 _mm_abs_pi32 (__m64 a)|
||__m128i _mm_abs_epi32 (__m128i a)|
|PABSW|__m64 _mm_abs_pi16 (__m64 a)|
||__m128i _mm_abs_epi16 (__m128i a)|
|PACKSSWB|__m128i _mm_packs_epi16(__m128i m1, __m128i m2)|
|PACKSSWB|__m64 _mm_packs_pi16(__m64 m1, __m64 m2)|
|PACKSSDW|__m128i _mm_packs_epi32 (__m128i m1, __m128i m2)|
|PACKSSDW|__m64 _mm_packs_pi32 (__m64 m1, __m64 m2)|
|PACKUSDW|__m128i _mm_packus_epi32(__m128i m1, __m128i m2)|
|PACKUSWB|__m128i _mm_packus_epi16(__m128i m1, __m128i m2)|
|PACKUSWB|__m64 _mm_packs_pu16(__m64 m1, __m64 m2)|
|PADDB|__m128i _mm_add_epi8(__m128i m1, __m128i m2)|
|PADDB|__m64 _mm_add_pi8(__m64 m1, __m64 m2)|
|PADDW|__m128i _mm_add_epi16(__m128i m1, __m128i m2)|
|PADDW|__m64 _mm_add_pi16(__m64 m1, __m64 m2)|
|PADDD|__m128i _mm_add_epi32(__m128i m1, __m128i m2)|
|PADDD|__m64 _mm_add_pi32(__m64 m1, __m64 m2)|
|PADDQ|__m128i _mm_add_epi64(__m128i m1, __m128i m2)|
|PADDQ|__m64 _mm_add_si64(__m64 m1, __m64 m2)|
|PADDSB|__m128i _mm_adds_epi8(__m128i m1, __m128i m2)|
|PADDSB|__m64 _mm_adds_pi8(__m64 m1, __m64 m2)|
|PADDSW|__m128i _mm_adds_epi16(__m128i m1, __m128i m2)|
|PADDSW|__m64 _mm_adds_pi16(__m64 m1, __m64 m2)|
|PADDUSB|__m128i _mm_adds_epu8(__m128i m1, __m128i m2)|
|PADDUSB|__m64 _mm_adds_pu8(__m64 m1, __m64 m2)|



Vol. 2D C-7

INTEL® C/C++ COMPILER INTRINSICS AND FUNCTIONAL EQUIVALENTS

Table C-1.  Simple Intrinsics (Contd.)

|Mnemonic|Intrinsic|
|---|---|
|PADDUSW|__m128i _mm_adds_epu16(__m128i m1, __m128i m2)|
|PADDUSW|__m64 _mm_adds_pu16(__m64 m1, __m64 m2)|
|PALIGNR|__m64 _mm_alignr_pi8 (__m64 a, __m64 b, int n)|
||__m128i _mm_alignr_epi8 (__m128i a, __m128i b, int n)|
|PAND|__m128i _mm_and_si128(__m128i m1, __m128i m2)|
|PAND|__m64 _mm_and_si64(__m64 m1, __m64 m2)|
|PANDN|__m128i _mm_andnot_si128(__m128i m1, __m128i m2)|
|PANDN|__m64 _mm_andnot_si64(__m64 m1, __m64 m2)|
|PAUSE|void _mm_pause(void)|
|PAVGB|__m128i _mm_avg_epu8(__m128i a, __m128i b)|
|PAVGB|__m64 _mm_avg_pu8(__m64 a, __m64 b)|
|PAVGW|__m128i _mm_avg_epu16(__m128i a, __m128i b)|
|PAVGW|__m64 _mm_avg_pu16(__m64 a, __m64 b)|
|PBLENDVB|__m128i _mm_blendv_epi (__m128i v1, __m128i v2, __m128i mask)|
|PBLENDW|__m128i _mm_blend_epi16(__m128i v1, __m128i v2, const int mask)|
|PCLMULQDQ|__m128i _mm_clmulepi64_si128 (__m128i, __m128i, const int)|
|PCMPEQB|__m128i _mm_cmpeq_epi8(__m128i m1, __m128i m2)|
|PCMPEQB|__m64 _mm_cmpeq_pi8(__m64 m1, __m64 m2)|
|PCMPEQQ|__m128i _mm_cmpeq_epi64(__m128i a, __m128i b)|
|PCMPEQW|__m128i _mm_cmpeq_epi16 (__m128i m1, __m128i m2)|
|PCMPEQW|__m64 _mm_cmpeq_pi16 (__m64 m1, __m64 m2)|
|PCMPEQD|__m128i _mm_cmpeq_epi32(__m128i m1, __m128i m2)|
|PCMPEQD|__m64 _mm_cmpeq_pi32(__m64 m1, __m64 m2)|
|PCMPESTRI|int _mm_cmpestri (__m128i a, int la, __m128i b, int lb, const int mode)|
||int _mm_cmpestra (__m128i a, int la, __m128i b, int lb, const int mode)|
||int _mm_cmpestrc (__m128i a, int la, __m128i b, int lb, const int mode)|
||int _mm_cmpestro (__m128i a, int la, __m128i b, int lb, const int mode)|
||int _mm_cmpestrs (__m128i a, int la, __m128i b, int lb, const int mode)|
||int _mm_cmpestrz (__m128i a, int la, __m128i b, int lb, const int mode)|
|PCMPESTRM|__m128i _mm_cmpestrm (__m128i a, int la, __m128i b, int lb, const int mode)|
||int _mm_cmpestra (__m128i a, int la, __m128i b, int lb, const int mode)|
||int _mm_cmpestrc (__m128i a, int la, __m128i b, int lb, const int mode)|
||int _mm_cmpestro (__m128i a, int la, __m128i b, int lb, const int mode)|
||int _mm_cmpestrs (__m128i a, int la, __m128i b, int lb, const int mode)|
||int _mm_cmpestrz (__m128i a, int la, __m128i b, int lb, const int mode)|
|PCMPGTB|__m128i _mm_cmpgt_epi8 (__m128i m1, __m128i m2)|
|PCMPGTB|__m64 _mm_cmpgt_pi8 (__m64 m1, __m64 m2)|
|PCMPGTW|__m128i _mm_cmpgt_epi16(__m128i m1, __m128i m2)|
|PCMPGTW|__m64 _mm_cmpgt_pi16 (__m64 m1, __m64 m2)|
|PCMPGTD|__m128i _mm_cmpgt_epi32(__m128i m1, __m128i m2)|
|PCMPGTD|__m64 _mm_cmpgt_pi32(__m64 m1, __m64 m2)|



C-8 Vol. 2D

INTEL® C/C++ COMPILER INTRINSICS AND FUNCTIONAL EQUIVALENTS

Table C-1.  Simple Intrinsics (Contd.)

|Mnemonic|Intrinsic|
|---|---|
|PCMPISTRI|__m128i _mm_cmpestrm (__m128i a, int la, __m128i b, int lb, const int mode)|
||int _mm_cmpestra (__m128i a, int la, __m128i b, int lb, const int mode)|
||int _mm_cmpestrc (__m128i a, int la, __m128i b, int lb, const int mode)|
||int _mm_cmpestro (__m128i a, int la, __m128i b, int lb, const int mode)|
||int _mm_cmpestrs (__m128i a, int la, __m128i b, int lb, const int mode)|
||int _mm_cmpistrz (__m128i a, __m128i b, const int mode)|
|PCMPISTRM|__m128i _mm_cmpistrm (__m128i a, __m128i b, const int mode)|
||int _mm_cmpistra (__m128i a, __m128i b, const int mode)|
||int _mm_cmpistrc (__m128i a, __m128i b, const int mode)|
||int _mm_cmpistro (__m128i a, __m128i b, const int mode)|
||int _mm_cmpistrs (__m128i a, __m128i b, const int mode)|
||int _mm_cmpistrz (__m128i a, __m128i b, const int mode)|
|PCMPGTQ|__m128i _mm_cmpgt_epi64(__m128i a, __m128i b)|
|PEXTRB|int _mm_extract_epi8 (__m128i src, const int ndx)|
|PEXTRD|int _mm_extract_epi32 (__m128i src, const int ndx)|
|PEXTRQ|__int64 _mm_extract_epi64 (__m128i src, const int ndx)|
|PEXTRW|int _mm_extract_epi16(__m128i a, int n)|
|PEXTRW|int _mm_extract_pi16(__m64 a, int n)|
||int _mm_extract_epi16 (__m128i src, int ndx)|
|PHADDD|__m64 _mm_hadd_pi32 (__m64 a, __m64 b)|
||__m128i _mm_hadd_epi32 (__m128i a, __m128i b)|
|PHADDSW|__m64 _mm_hadds_pi16 (__m64 a, __m64 b)|
||__m128i _mm_hadds_epi16 (__m128i a, __m128i b)|
|PHADDW|__m64 _mm_hadd_pi16 (__m64 a, __m64 b)|
||__m128i _mm_hadd_epi16 (__m128i a, __m128i b)|
|PHMINPOSUW|__m128i _mm_minpos_epu16( __m128i packed_words)|
|PHSUBD|__m64 _mm_hsub_pi32 (__m64 a, __m64 b)|
||__m128i _mm_hsub_epi32 (__m128i a, __m128i b)|
|PHSUBSW|__m64 _mm_hsubs_pi16 (__m64 a, __m64 b)|
||__m128i _mm_hsubs_epi16 (__m128i a, __m128i b)|
|PHSUBW|__m64 _mm_hsub_pi16 (__m64 a, __m64 b)|
||__m128i _mm_hsub_epi16 (__m128i a, __m128i b)|
|PINSRB|__m128i _mm_insert_epi8(__m128i s1, int s2, const int ndx)|
|PINSRD|__m128i _mm_insert_epi32(__m128i s2, int s, const int ndx)|
|PINSRQ|__m128i _mm_insert_epi64(__m128i s2, __int64 s, const int ndx)|
|PINSRW|__m128i _mm_insert_epi16(__m128i a, int d, int n)|
|PINSRW|__m64 _mm_insert_pi16(__m64 a, int d, int n)|
|PMADDUBSW|__m64 _mm_maddubs_pi16 (__m64 a, __m64 b)|
||__m128i _mm_maddubs_epi16 (__m128i a, __m128i b)|
|PMADDWD|__m128i _mm_madd_epi16(__m128i m1 __m128i m2)|
|PMADDWD|__m64 _mm_madd_pi16(__m64 m1, __m64 m2)|



Vol. 2D C-9

INTEL® C/C++ COMPILER INTRINSICS AND FUNCTIONAL EQUIVALENTS

Table C-1.  Simple Intrinsics (Contd.)

|Mnemonic|Intrinsic|
|---|---|
|PMAXSB|__m128i _mm_max_epi8( __m128i a, __m128i b)|
|PMAXSD|__m128i _mm_max_epi32( __m128i a, __m128i b)|
|PMAXSW|__m128i _mm_max_epi16(__m128i a, __m128i b)|
|PMAXSW|__m64 _mm_max_pi16(__m64 a, __m64 b)|
|PMAXUB|__m128i _mm_max_epu8(__m128i a, __m128i b)|
|PMAXUB|__m64 _mm_max_pu8(__m64 a, __m64 b)|
|PMAXUD|__m128i _mm_max_epu32( __m128i a, __m128i b)|
|PMAXUW|__m128i _mm_max_epu16( __m128i a, __m128i b)|
|PMINSB|_m128i _mm_min_epi8( __m128i a, __m128i b)|
|PMINSD|__m128i _mm_min_epi32( __m128i a, __m128i b)|
|PMINSW|__m128i _mm_min_epi16(__m128i a, __m128i b)|
|PMINSW|__m64 _mm_min_pi16(__m64 a, __m64 b)|
|PMINUB|__m128i _mm_min_epu8(__m128i a, __m128i b)|
|PMINUB|__m64 _mm_min_pu8(__m64 a, __m64 b)|
|PMINUD|__m128i _mm_min_epu32 ( __m128i a, __m128i b)|
|PMINUW|__m128i _mm_min_epu16 ( __m128i a, __m128i b)|
|PMOVMSKB|int _mm_movemask_epi8(__m128i a)|
|PMOVMSKB|int _mm_movemask_pi8(__m64 a)|
|PMOVSXBW|__m128i _mm_ cvtepi8_epi16( __m128i a)|
|PMOVSXBD|__m128i _mm_ cvtepi8_epi32( __m128i a)|
|PMOVSXBQ|__m128i _mm_ cvtepi8_epi64( __m128i a)|
|PMOVSXWD|__m128i _mm_ cvtepi16_epi32( __m128i a)|
|PMOVSXWQ|__m128i _mm_ cvtepi16_epi64( __m128i a)|
|PMOVSXDQ|__m128i _mm_ cvtepi32_epi64( __m128i a)|
|PMOVZXBW|__m128i _mm_ cvtepu8_epi16( __m128i a)|
|PMOVZXBD|__m128i _mm_ cvtepu8_epi32( __m128i a)|
|PMOVZXBQ|__m128i _mm_ cvtepu8_epi64( __m128i a)|
|PMOVZXWD|__m128i _mm_ cvtepu16_epi32( __m128i a)|
|PMOVZXWQ|__m128i _mm_ cvtepu16_epi64( __m128i a)|
|PMOVZXDQ|__m128i _mm_ cvtepu32_epi64( __m128i a)|
|PMULDQ|__m128i _mm_mul_epi32( __m128i a, __m128i b)|
|PMULHRSW|__m64 _mm_mulhrs_pi16 (__m64 a, __m64 b)|
||__m128i _mm_mulhrs_epi16 (__m128i a, __m128i b)|
|PMULHUW|__m128i _mm_mulhi_epu16(__m128i a, __m128i b)|
|PMULHUW|<br>__m64 _mm_mulhi_pu16(__m64 a, __m64 b)|
|PMULHW|__m128i _mm_mulhi_epi16(__m128i m1, __m128i m2)|
|PMULHW|__m64 _mm_mulhi_pi16(__m64 m1, __m64 m2)|
|PMULLUD|__m128i _mm_mullo_epi32(__m128i a, __m128i b)|
|PMULLW|__m128i _mm_mullo_epi16(__m128i m1, __m128i m2)|
|PMULLW|__m64 _mm_mullo_pi16(__m64 m1, __m64 m2)|



C-10 Vol. 2D

INTEL® C/C++ COMPILER INTRINSICS AND FUNCTIONAL EQUIVALENTS

Table C-1.  Simple Intrinsics (Contd.)

|Mnemonic|Intrinsic|
|---|---|
|PMULUDQ|__m64 _mm_mul_su32(__m64 m1, __m64 m2)|
||__m128i _mm_mul_epu32(__m128i m1, __m128i m2)|
|POPCNT|int _mm_popcnt_u32(unsigned int a)|
||int64_t _mm_popcnt_u64(unsigned __int64 a)|
|POR|__m64 _mm_or_si64(__m64 m1, __m64 m2)|
|POR|__m128i _mm_or_si128(__m128i m1, __m128i m2)|
|PREFETCHh|void _mm_prefetch(char *a, int sel)|
|PSADBW|__m128i _mm_sad_epu8(__m128i a, __m128i b)|
|PSADBW|__m64 _mm_sad_pu8(__m64 a, __m64 b)|
|PSHUFB|__m64 _mm_shuffle_pi8 (__m64 a, __m64 b)|
||__m128i _mm_shuffle_epi8 (__m128i a, __m128i b)|
|PSHUFD|__m128i _mm_shuffle_epi32(__m128i a, int n)|
|PSHUFHW|__m128i _mm_shufflehi_epi16(__m128i a, int n)|
|PSHUFLW|__m128i _mm_shufflelo_epi16(__m128i a, int n)|
|PSHUFW|__m64 _mm_shuffle_pi16(__m64 a, int n)|
|PSIGNB|__m64 _mm_sign_pi8 (__m64 a, __m64 b)|
||__m128i _mm_sign_epi8 (__m128i a, __m128i b)|
|PSIGND|__m64 _mm_sign_pi32 (__m64 a, __m64 b)|
||__m128i _mm_sign_epi32 (__m128i a, __m128i b)|
|PSIGNW|__m64 _mm_sign_pi16 (__m64 a, __m64 b)|
||__m128i _mm_sign_epi16 (__m128i a, __m128i b)|
|PSLLW|__m128i _mm_sll_epi16(__m128i m, __m128i count)|
|PSLLW|__m128i _mm_slli_epi16(__m128i m, int count)|
|PSLLW|__m64 _mm_sll_pi16(__m64 m, __m64 count)|
||__m64 _mm_slli_pi16(__m64 m, int count)|
|PSLLD|__m128i _mm_slli_epi32(__m128i m, int count)|
||__m128i _mm_sll_epi32(__m128i m, __m128i count)|
|PSLLD|__m64 _mm_slli_pi32(__m64 m, int count)|
||__m64 _mm_sll_pi32(__m64 m, __m64 count)|
|PSLLQ|__m64 _mm_sll_si64(__m64 m, __m64 count)|
||__m64 _mm_slli_si64(__m64 m, int count)|
|PSLLQ|__m128i _mm_sll_epi64(__m128i m, __m128i count)|
||__m128i _mm_slli_epi64(__m128i m, int count)|
|PSLLDQ|__m128i _mm_slli_si128(__m128i m, int imm)|
|PSRAW|__m128i _mm_sra_epi16(__m128i m, __m128i count)|
||__m128i _mm_srai_epi16(__m128i m, int count)|
|PSRAW|__m64 _mm_sra_pi16(__m64 m, __m64 count)|
||__m64 _mm_srai_pi16(__m64 m, int count)|
|PSRAD|__m128i _mm_sra_epi32 (__m128i m, __m128i count)|
||__m128i _mm_srai_epi32 (__m128i m, int count)|
|PSRAD|__m64 _mm_sra_pi32 (__m64 m, __m64 count)|



Vol. 2D C-11

INTEL® C/C++ COMPILER INTRINSICS AND FUNCTIONAL EQUIVALENTS

Table C-1.  Simple Intrinsics (Contd.)

|Mnemonic|Intrinsic|
|---|---|
||__m64 _mm_srai_pi32 (__m64 m, int count)|
|PSRLW|_m128i _mm_srl_epi16 (__m128i m, __m128i count)|
||__m128i _mm_srli_epi16 (__m128i m, int count)|
||__m64 _mm_srl_pi16 (__m64 m, __m64 count)|
||__m64 _mm_srli_pi16(__m64 m, int count)|
|PSRLD|__m128i _mm_srl_epi32 (__m128i m, __m128i count)|
||__m128i _mm_srli_epi32 (__m128i m, int count)|
|PSRLD|__m64 _mm_srl_pi32 (__m64 m, __m64 count)|
||__m64 _mm_srli_pi32 (__m64 m, int count)|
|PSRLQ|__m128i _mm_srl_epi64 (__m128i m, __m128i count)|
||__m128i _mm_srli_epi64 (__m128i m, int count)|
|PSRLQ|__m64 _mm_srl_si64 (__m64 m, __m64 count)|
||__m64 _mm_srli_si64 (__m64 m, int count)|
|PSRLDQ|__m128i _mm_srli_si128(__m128i m, int imm)|
|PSUBB|__m128i _mm_sub_epi8(__m128i m1, __m128i m2)|
|PSUBB|__m64 _mm_sub_pi8(__m64 m1, __m64 m2)|
|PSUBW|__m128i _mm_sub_epi16(__m128i m1, __m128i m2)|
|PSUBW|__m64 _mm_sub_pi16(__m64 m1, __m64 m2)|
|PSUBD|__m128i _mm_sub_epi32(__m128i m1, __m128i m2)|
|PSUBD|__m64 _mm_sub_pi32(__m64 m1, __m64 m2)|
|PSUBQ|__m128i _mm_sub_epi64(__m128i m1, __m128i m2)|
|PSUBQ|__m64 _mm_sub_si64(__m64 m1, __m64 m2)|
|PSUBSB|__m128i _mm_subs_epi8(__m128i m1, __m128i m2)|
|PSUBSB|__m64 _mm_subs_pi8(__m64 m1, __m64 m2)|
|PSUBSW|__m128i _mm_subs_epi16(__m128i m1, __m128i m2)|
|PSUBSW|__m64 _mm_subs_pi16(__m64 m1, __m64 m2)|
|PSUBUSB|__m128i _mm_subs_epu8(__m128i m1, __m128i m2)|
|PSUBUSB|__m64 _mm_subs_pu8(__m64 m1, __m64 m2)|
|PSUBUSW|__m128i _mm_subs_epu16(__m128i m1, __m128i m2)|
|PSUBUSW|__m64 _mm_subs_pu16(__m64 m1, __m64 m2)|
|PTEST|int _mm_testz_si128(__m128i s1, __m128i s2)|
||int _mm_testc_si128(__m128i s1, __m128i s2)|
||int _mm_testnzc_si128(__m128i s1, __m128i s2)|
|PUNPCKHBW|__m64 _mm_unpackhi_pi8(__m64 m1, __m64 m2)|
|PUNPCKHBW|__m128i _mm_unpackhi_epi8(__m128i m1, __m128i m2)|
|PUNPCKHWD|__m64 _mm_unpackhi_pi16(__m64 m1,__m64 m2)|
|PUNPCKHWD|__m128i _mm_unpackhi_epi16(__m128i m1, __m128i m2)|
|PUNPCKHDQ|___m64 _mm_unpackhi_pi32(__m64 m1, __m64 m2)|
|PUNPCKHDQ|__m128i _mm_unpackhi_epi32(__m128i m1, __m128i m2)|
|PUNPCKHQDQ|__m128i _mm_unpackhi_epi64(__m128i m1, __m128i m2)|
|PUNPCKLBW|__m64 _mm_unpacklo_pi8 (__m64 m1, __m64 m2)|



C-12 Vol. 2D

INTEL® C/C++ COMPILER INTRINSICS AND FUNCTIONAL EQUIVALENTS

Table C-1.  Simple Intrinsics (Contd.)

|Mnemonic|Intrinsic|
|---|---|
|PUNPCKLBW|__m128i _mm_unpacklo_epi8 (__m128i m1, __m128i m2)|
|PUNPCKLWD|__m64 _mm_unpacklo_pi16(__m64 m1, __m64 m2)|
|PUNPCKLWD|__m128i _mm_unpacklo_epi16(__m128i m1, __m128i m2)|
|PUNPCKLDQ|__m64 _mm_unpacklo_pi32(__m64 m1, __m64 m2)|
|PUNPCKLDQ|__m128i _mm_unpacklo_epi32(__m128i m1, __m128i m2)|
|PUNPCKLQDQ|__m128i _mm_unpacklo_epi64(__m128i m1, __m128i m2)|
|PXOR|__m64 _mm_xor_si64(__m64 m1, __m64 m2)|
|PXOR|__m128i _mm_xor_si128(__m128i m1, __m128i m2)|
|RCPPS|__m128 _mm_rcp_ps(__m128 a)|
|RCPSS|__m128 _mm_rcp_ss(__m128 a)|
|ROUNDPD|__m128 mm_round_pd(__m128d s1, int iRoundMode)|
||__m128 mm_floor_pd(__m128d s1)|
||__m128 mm_ceil_pd(__m128d s1)|
|ROUNDPS|__m128 mm_round_ps(__m128 s1, int iRoundMode)|
||__m128 mm_floor_ps(__m128 s1)|
||__m128 mm_ceil_ps(__m128 s1)|
|ROUNDSD|__m128d mm_round_sd(__m128d dst, __m128d s1, int iRoundMode)|
||__m128d mm_floor_sd(__m128d dst, __m128d s1)|
||__m128d mm_ceil_sd(__m128d dst, __m128d s1)|
|ROUNDSS|__m128 mm_round_ss(__m128 dst, __m128 s1, int iRoundMode)|
||__m128 mm_floor_ss(__m128 dst, __m128 s1)|
||__m128 mm_ceil_ss(__m128 dst, __m128 s1)|
|RSQRTPS|__m128 _mm_rsqrt_ps(__m128 a)|
|RSQRTSS|__m128 _mm_rsqrt_ss(__m128 a)|
|SFENCE|void_mm_sfence(void)|
|SHUFPD|__m128d _mm_shuffle_pd(__m128d a, __m128d b, unsigned int imm8)|
|SHUFPS|__m128 _mm_shuffle_ps(__m128 a, __m128 b, unsigned int imm8)|
|SQRTPD|__m128d _mm_sqrt_pd(__m128d a)|
|SQRTPS|__m128 _mm_sqrt_ps(__m128 a)|
|SQRTSD|__m128d _mm_sqrt_sd(__m128d a)|
|SQRTSS|__m128 _mm_sqrt_ss(__m128 a)|
|STMXCSR|_mm_getcsr(void)|
|SUBPD|__m128d _mm_sub_pd(__m128d a, __m128d b)|
|SUBPS|__m128 _mm_sub_ps(__m128 a, __m128 b)|
|SUBSD|__m128d _mm_sub_sd(__m128d a, __m128d b)|
|SUBSS|__m128 _mm_sub_ss(__m128 a, __m128 b)|
|UCOMISD|int _mm_ucomieq_sd(__m128d a, __m128d b)|
||int _mm_ucomilt_sd(__m128d a, __m128d b)|
||int _mm_ucomile_sd(__m128d a, __m128d b)|
||int _mm_ucomigt_sd(__m128d a, __m128d b)|
||int _mm_ucomige_sd(__m128d a, __m128d b)|



Vol. 2D C-13

INTEL® C/C++ COMPILER INTRINSICS AND FUNCTIONAL EQUIVALENTS

Table C-1.  Simple Intrinsics (Contd.)

|Mnemonic|Intrinsic|
|---|---|
||int _mm_ucomineq_sd(__m128d a, __m128d b)|
|UCOMISS|int _mm_ucomieq_ss(__m128 a, __m128 b)|
||int _mm_ucomilt_ss(__m128 a, __m128 b)|
||int _mm_ucomile_ss(__m128 a, __m128 b)|
||int _mm_ucomigt_ss(__m128 a, __m128 b)|
||int _mm_ucomige_ss(__m128 a, __m128 b)|
||int _mm_ucomineq_ss(__m128 a, __m128 b)|
|UNPCKHPD|__m128d _mm_unpackhi_pd(__m128d a, __m128d b)|
|UNPCKHPS|__m128 _mm_unpackhi_ps(__m128 a, __m128 b)|
|UNPCKLPD|__m128d _mm_unpacklo_pd(__m128d a, __m128d b)|
|UNPCKLPS|__m128 _mm_unpacklo_ps(__m128 a, __m128 b)|
|XORPD|__m128d _mm_xor_pd(__m128d a, __m128d b)|
|XORPS|__m128 _mm_xor_ps(__m128 a, __m128 b)|



## C.2 COMPOSITE INTRINSICS

Table C-2.  Composite Intrinsics

|Mnemonic|Intrinsic|
|---|---|
|(composite)|__m128i _mm_set_epi64(__m64 q1, __m64 q0)|
|(composite)|__m128i _mm_set_epi32(int i3, int i2, int i1, int i0)|
|(composite)|__m128i _mm_set_epi16(short w7,short w6, short w5, short w4, short w3, short w2,<br>short w1,short w0)|
|(composite)|__m128i _mm_set_epi8(char w15,char w14, char w13, char w12, char w11, char w10,<br>char w9, char w8, char w7,char w6, char w5, char w4, char w3, char w2,char w1, char w0)|
|(composite)|__m128i _mm_set1_epi64(__m64 q)|
|(composite)|__m128i _mm_set1_epi32(int a)|
|(composite)|__m128i _mm_set1_epi16(short a)|
|(composite)|__m128i _mm_set1_epi8(char a)|
|(composite)|__m128i _mm_setr_epi64(__m64 q1, __m64 q0)|
|(composite)|__m128i _mm_setr_epi32(int i3, int i2, int i1, int i0)|
|(composite)|__m128i _mm_setr_epi16(short w7,short w6, short w5, short w4, short w3, short w2, short w,<br>short w0)|
|(composite)|__m128i _mm_setr_epi8(char w15,char w14, char w13, char w12, char w11, char w10,<br>char w9, char w8,char w7, char w6,char w5, char w4, char w3, char w2,char w1,char w0)|
|(composite)|__m128i _mm_setzero_si128()|
|(composite)|__m128 _mm_set_ps1(float w)<br>__m128 _mm_set1_ps(float w)|
|(composite)|__m128cmm_set1_pd(double w)|
|(composite)|__m128d _mm_set_sd(double w)|
|(composite)|__m128d _mm_set_pd(double z, double y)|
|(composite)|__m128 _mm_set_ps(float z, float y, float x, float w)|
|(composite)|__m128d _mm_setr_pd(double z, double y)|
|(composite)|__m128 _mm_setr_ps(float z, float y, float x, float w)|



C-14 Vol. 2D

INTEL® C/C++ COMPILER INTRINSICS AND FUNCTIONAL EQUIVALENTS

Table C-2.  Composite Intrinsics (Contd.)

|Mnemonic||Intrinsic|
|---|---|---|
|(composite)|__m128d _mm_setzero_pd(void)||
|(composite)|__m128 _mm_setzero_ps(void)||
|MOVSD+shuffle|__m128d _mm_load_pd(double * p)<br>__m128d _mm_load1_pd(double *p)||
|MOVSS+shuffle|__m128 _mm_load_ps1(float * p)<br>__m128 _mm_load1_ps(float *p)||
|MOVAPD+shuffle|__m128d _mm_loadr_pd(double * p)||
|MOVAPS+shuffle|__m128 _mm_loadr_ps(float * p)||
|MOVSD+shuffle|void _mm_store1_pd(double *p, __m128d a)||
|MOVSS+shuffle|void _mm_store_ps1(float * p, __m128 a)<br>void _mm_store1_ps(float *p, __m128 a)||
|MOVAPD+shuffle|_mm_storer_pd(double * p, __m128d a)||
|MOVAPS+shuffle|_mm_storer_ps(float * p, __m128 a)||



Vol. 2D C-15

INTEL® C/C++ COMPILER INTRINSICS AND FUNCTIONAL EQUIVALENTS

C-16 Vol. 2D

**INDEX**

Symbols VF 5-200, 5-215, 5-246, 5-261 Numerics 0000 B-41 MADD 5-200, 5-215 MSUB 5-246, 5-261 64-bit mode control and debug registers 2-12 default operand size 2-12 direct memory-offset MOVs 2-11 general purpose encodings B-18 immediates 2-11 introduction 2-7 machine instructions B-1 reg (reg) field B-4 REX prefixes 2-7, B-2 RIP-relative addressing 2-12 SIMD encodings B-37 special instruction encodings B-61 summary table notation 3-8 A AAA instruction 3-19, 3-21 AAD instruction 3-21 AAM instruction 3-23 AAS instruction 3-25 ADC instruction 3-27, 3-609 ADD instruction 3-19, 3-32, 3-315, 3-609 ADDPD instruction 3-34 ADDPS- Add Packed Single-Precision Floating-Point Values 3-37 Addressing methods RIP-relative 2-12 Addressing, segments 1-7 ADDSD- Add Scalar Double-Precision Floating-Point Values 3-40 ADDSD instruction 3-40 ADDSS- Add Scalar Single-Precision Floating-Point Values 3-42 ADDSUBPD instruction 3-44 ADDSUBPS instruction 3-46 ADOX — Unsigned Integer Addition of Two Operands with Overflow Flag 3-49 AESDEC128KL—Perform Ten Rounds of AES Decryption Flow Using 128-Bit Key 3-53 AESDEC256KL—Perform 14 Rounds of AES Decryption Flow Using 256-Bit Key 3-55 AESDECLAST—Perform Last Round of an AES Decryption Flow 3-57

AESDEC—Perform One Round of an AES Decryption Flow 3-51 AESDECWIDE128KL—Perform Ten Rounds of AES Decryption Flow on 8 Blocks with 128-Bit Key 3-59 AESDECWIDE256KL—Perform 14 Rounds of AES Decryption Flow on 8 Blocks with 256-Bit Key 3-61 AESENC128KL—Perform Ten Rounds of AES Encryption Flow Using 128-Bit Key 3-65 AESENC256KL—Perform 14 Rounds of AES Encryption Flow Using 256-Bit Key 3-67 AESENCLAST—Perform Last Round of an AES Encryption Flow 3-69

AESENC—Perform One Round of an AES Encryption Flow 3-63 AESENCWIDE128KL—Perform Ten Rounds of AES Encryption Flow on 8 Blocks with 128-Bit Key 3-71

AESENCWIDE256KL—Perform 14 Rounds of AES Encryption Flow on 8 Blocks with 256-Bit Key 3-73 AESIMC—Perform the AES InvMixColumn Transformation 3-75 AESKEYGENASSIST - AES Round Key Generation Assist 3-76 AND instruction 3-78, 3-609 ANDNPS- Bitwise Logical AND NOT of Packed Single Precision Floating-Point Values 3-90 ANDPD- Bitwise Logical AND of Packed Double Precision Floating-Point Values 3-81 ANDPD instruction 3-80 ANDPS- Bitwise Logical AND of Packed Single Precision Floating-Point Values 3-84 Arctangent, x87 FPU operation 3-413 ARPL instruction 3-93 authenticated code execution mode 7-3 B Base (operand addressing) 2-3 BCD integers packed 3-315, 3-317, 3-363, 3-365 unpacked 3-19, 3-21, 3-23, 3-25 BEXTR—Bit Field Extract 3-95 Binary numbers 1-6 Bit order 1-5 BLENDPD — Blend Packed Double Precision Floating-Point Values 3-96 BLENDPS — Blend Packed Single Precision Floating-Point Values 3-98 BLSI-Extract Lowest Set Isolated Bit 3-105 BLSMSK - Get Mask Up to Lowest Set Bit 3-106 BLSR —Reset Lowest Set Bit 3-107 BNDCL—Check Lower Bound 3-108 BNDCU/BNDCN—Check Upper Bound 3-110 BNDLDX—Load Extended Bounds Using Address Translation 3-112 BNDMK—Make Bounds 3-115 BNDMOV—Move Bounds 3-117 BNDSTX—Store Extended Bounds Using Address Translation 3-120 bootstrap processor 7-16, 7-21, 7-29, 7-30 BOUND instruction 3-123 BOUND range exceeded exception (#BR) 3-123 BOUND—Check Array Index Against Bounds 3-123 Branch hints 2-2 Brand information 3-252 processor brand index 3-254 processor brand string 3-252 BSF instruction 3-125 BSR instruction 3-127 BSWAP instruction 3-129 BT instruction 3-130 BTC instruction 3-132, 3-609 BTR instruction 3-134, 3-609 BTS instruction 3-136, 3-609 Byte order 1-5 BZHI —Zero High Bits Starting with Specified Bit Position 3-138 C C/C++ compiler intrinsics compiler functional equivalents C-1 composite C-14

Vol. 2D INDEX-1

**INDEX**

description of 3-12 Control registers, moving values to and from 4-40 lists of C-1 Cosine, x87 FPU operation 3-379, 3-431 simple C-2 CPL 3-166, 5-155 Cache and TLB information 3-245 CPUID instruction 3-216, 3-244 Cache Inclusiveness 3-218 36-bit page size extension 3-244 Caches, invalidating (flushing) 3-531, 6-3 APIC on-chip 3-244 CALL instruction 3-139 basic CPUID information 3-217 GETSEC 7-3 cache and TLB characteristics 3-217 CBW instruction 3-156 CLFLUSH flag 3-244 CDQ instruction 3-314 CLFLUSH instruction cache line size 3-240 CDQE instruction 3-156 CMPXCHG16B flag 3-242 CF (carry) flag, EFLAGS register 3-32, 3-130, 3-132, 3-134, 3-136, CMPXCHG8B flag 3-244 3-158, 3-174, 3-319, 3-501, 3-506, 4-150, 4-534, 4-609, 4-635, CPL qualified debug store 3-241 4-638, 4-682 debug extensions, CR4.DE 3-244 CLC instruction 3-158 debug store supported 3-245 CLD instruction 3-159 deterministic cache parameters leaf 3-217, 3-220, 3-222, CLFLUSH instruction 3-162, 3-164 3-223, 3-224, 3-225, 3-226, 3-227, 3-228, 3-229, CPUID flag 3-244 3-230, 3-235 CLI instruction 3-166 extended function information 3-236 CLTS instruction 3-170 feature information 3-243 CMC instruction 3-174 FPU on-chip 3-244 CMOVcc flag 3-244 FSAVE flag 3-245 CMOVcc instructions 3-175 FXRSTOR flag 3-245 CPUID flag 3-244 IA-32e mode available 3-237 CMP instruction 3-179 input limits for EAX 3-238 CMPPD- Compare Packed Double-Precision Floating-Point Values L1 Context ID 3-242 3-181 local APIC physical ID 3-240 CMPPS- Compare Packed Single-Precision Floating-Point Values machine check architecture 3-244 3-188 machine check exception 3-244 CMPS instruction 3-195, 4-561 memory type range registers 3-244 CMPSB instruction 3-195 MONITOR feature information 3-249 CMPSD- Compare Scalar Double-Precision Floating-Point Values MONITOR/MWAIT flag 3-241 3-199 MONITOR/MWAIT leaf 3-218, 3-219, 3-223, 3-224, 3-230, CMPSD instruction 3-195 3-235, 3-236 CMPSQ instruction 3-195 MWAIT feature information 3-249 CMPSS- Compare Scalar Single-Precision Floating-Point Values page attribute table 3-244 3-203 page size extension 3-244 CMPSW instruction 3-195 performance monitoring features 3-250 CMPXCHG instruction 3-207, 3-609 physical address bits 3-238 CMPXCHG16B instruction 3-209 physical address extension 3-244 CPUID bit 3-242 power management 3-249, 3-250, 3-251, 3-252 CMPXCHG8B instruction 3-209 processor brand index 3-240, 3-252 CPUID flag 3-244 processor brand string 3-237, 3-252 COMISD- Compare Scalar Ordered Double-Precision Floating-Point processor serial number 3-217, 3-244 Values and Set EFLAGS 3-212 processor type field 3-239 COMISS- Compare Scalar Ordered Single-Precision Floating-Point RDMSR flag 3-244 Values and Set EFLAGS 3-214 returned in EBX 3-240 Compatibility mode returned in ECX & EDX 3-240 introduction 2-7 self snoop 3-245 see 64-bit mode SpeedStep technology 3-241 summary table notation 3-9 SS2 extensions flag 3-245 Compatibility, software 1-6 SSE extensions flag 3-245 Condition code flags, EFLAGS register 3-175 SSE3 extensions flag 3-241 Condition code flags, x87 FPU status word SSSE3 extensions flag 3-241 flags affected by instructions 3-14 SYSENTER flag 3-244 setting 3-449, 3-451, 3-454 SYSEXIT flag 3-244 Conditional jump 3-547 thermal management 3-249, 3-250, 3-251, 3-252 Conforming code segment 3-581 thermal monitor 3-241, 3-245 Constants (floating point), loading 3-403 time stamp counter 3-244

INDEX-2 Vol. 2D

**INDEX**

using CPUID 3-216 vendor ID string 3-238 version information 3-217, 3-249 virtual 8086 Mode flag 3-244 virtual address bits 3-238 WRMSR flag 3-244 CQO instruction 3-314 CR0 control register 4-654 CS register 3-140, 3-516, 3-538, 3-553, 4-36, 4-399 CVTDQ2PD- Convert Packed Doubleword Integers to Packed Double-Precision Floating-Point Values 3-264 CVTDQ2PD instruction 3-261 CVTDQ2PS- Convert Packed Doubleword Integers to Packed Single-Precision Floating-Point Values 3-268 CVTPD2DQ- Convert Packed Double-Precision Floating-Point Values to Packed Doubleword Integers 3-271 CVTPD2PI instruction 3-275

using CPUID 3-216 DIVPD- Divide Packed Double-Precision Floating-Point Values vendor ID string 3-238 3-324 version information 3-217, 3-249 DIVPS- Divide Packed Single-Precision Floating-Point Values virtual 8086 Mode flag 3-244 3-327 virtual address bits 3-238 DIVSD- Divide Scalar Double-Precision Floating-Point Values 3-330 WRMSR flag 3-244 DIVSS- Divide Scalar Single-Precision Floating-Point Values 3-332 CQO instruction 3-314 DS register 3-195, 3-587, 3-611, 4-113, 4-182 CR0 control register 4-654 E CS register 3-140, 3-516, 3-538, 3-553, 4-36, 4-399 EDI register 4-611, 4-668, 4-672 CVTDQ2PD- Convert Packed Doubleword Integers to Packed DouEffective address 3-594 ble-Precision Floating-Point Values 3-264 EFLAGS register CVTDQ2PD instruction 3-261 condition codes 3-177, 3-371, 3-376 CVTDQ2PS- Convert Packed Doubleword Integers to Packed Sinflags affected by instructions 3-14 gle-Precision Floating-Point Values 3-268 popping 4-407 CVTPD2DQ- Convert Packed Double-Precision Floating-Point Valpopping on return from interrupt 3-538 ues to Packed Doubleword Integers 3-271 pushing 4-526 CVTPD2PI instruction 3-275 pushing on interrupts 3-516 CVTPD2PS- Convert Packed Double-Precision Floating-Point Valsaving 4-597 ues to Packed Single-Precision Floating-Point Values 3-276 status flags 3-179, 3-550, 4-619, 4-711 CVTPI2PD instruction 3-280 EIP register 3-140, 3-516, 3-538, 3-553 CVTPI2PS instruction 3-281 EMMS instruction 3-339 CVTPS2DQ- Convert Packed Single Precision Floating-Point Values ENCODEKEY128—Encode 128-Bit Key 3-340 to Packed Signed Doubleword Integer Values 3-282 ENCODEKEY256—Encode 256-Bit Key 3-342 CVTPS2PI instruction 3-288 Encodings CVTSD2SI- Convert Scalar Double Precision Floating-Point Value See machine instructions, opcodes to Doubleword Integer 3-289 ENDBR32—Terminate an Indirect Branch in 32-bit and CompatibilCVTSI2SS- Convert Doubleword Integer to Scalar Single-Precision ity Mode 3-344 Floating-Point Value 3-295 ENTER instruction 3-346 CVTSS2SD- Convert Scalar Single-Precision Floating-Point Value GETSEC 7-3, 7-10 to Scalar Double-Precision Floating-Point Value 3-297 ES register 3-587, 4-182, 4-611, 4-672 CVTSS2SI- Convert Scalar Single-Precision Floating-Point Value to ESI register 3-195, 3-611, 4-113, 4-182, 4-668 Doubleword Integer 3-299 ESP register 3-140 CVTTPD2DQ- Convert with Truncation Packed Double-Precision EVEX.R 3-5 Floating-Point Values to Packed Doubleword Integers 3-301 Exceptions CVTTPD2PI instruction 3-305 BOUND range exceeded (#BR) 3-123 CVTTPS2DQ- Convert with Truncation Packed Single-Precision notation 1-7 Floating-Point Values to Packed Signed Doubleword Integer Valoverflow exception (#OF) 3-516 ues 3-306 returning from 3-538 CVTTPS2PI instruction 3-309 GETSEC 7-3, 7-5 CVTTSD2SI- Convert with Truncation Scalar Double-Precision Exponent, extracting from floating-point number 3-469 Floating-Point Value to Signed Integer 3-310 Extract exponent and significand, x87 FPU operation 3-469 CVTTSS2SI- Convert with Truncation Scalar Single-Precision FloatEXTRACTPS- Extract packed floating-point values 3-355 ing-Point Value to Integer 3-312 F CWD instruction 3-314 F2XM1 instruction 3-357, 3-469 CWDE instruction 3-156 FABS instruction 3-359 D FADD instruction 3-360 D (default operation size) flag, segment descriptor 4-403 FADDP instruction 3-360 DAA instruction 3-315 Far pointer, loading 3-587 DAS instruction 3-317 Far return, RET instruction 4-564 Debug registers, moving value to and from 4-43 FBLD instruction 3-363 DEC instruction 3-319, 3-609 FBSTP instruction 3-365 Denormalized finite number 3-454 FCHS instruction 3-367 Detecting and Enabling SMX FCLEX instruction 3-369 level 2 7-1 FCMOVcc instructions 3-371 DF (direction) flag, EFLAGS register 3-159, 3-196, 3-510, 3-611, FCOM instruction 3-373 4-113, 4-182, 4-611, 4-668 FCOMI instruction 3-376 Displacement (operand addressing) 2-3 FCOMIP instruction 3-376 DIV instruction 3-321 FCOMP instruction 3-373 Divide error exception (#DE) 3-321 FCOMPP instruction 3-373

Vol. 2D INDEX-3

**INDEX**

FCOS instruction 3-379 FDECSTP instruction 3-381 FDIV instruction 3-382 FDIVP instruction 3-382 FDIVR instruction 3-385 FDIVRP instruction 3-385 Feature information, processor 3-216 FFREE instruction 3-388 FIADD instruction 3-360 FICOM instruction 3-389 FICOMP instruction 3-389 FIDIV instruction 3-382 FIDIVR instruction 3-385 FILD instruction 3-391 FIMUL instruction 3-409 FINCSTP instruction 3-393 FINIT instruction 3-394 FINIT/FNINIT instructions 3-424 FIST instruction 3-396 FISTP instruction 3-396 FISTTP instruction 3-399 FISUB instruction 3-443 FISUBR instruction 3-446 FLD instruction 3-401 FLD1 instruction 3-403 FLDCW instruction 3-405 FLDENV instruction 3-407 FLDL2E instruction 3-403 FLDL2T instruction 3-403 FLDLG2 instruction 3-403 FLDLN2 instruction 3-403 FLDPI instruction 3-403 FLDZ instruction 3-403 Floating point instructions machine encodings B-61 Floating-point exceptions SSE and SSE2 SIMD 3-16 x87 FPU 3-16 Flushing caches 3-531, 6-3 TLB entry 3-533 FMUL instruction 3-409 FMULP instruction 3-409 FNCLEX instruction 3-369 FNINIT instruction 3-394 FNOP instruction 3-412 FNSAVE instruction 3-424 FNSTCW instruction 3-437 FNSTENV instruction 3-407, 3-439 FNSTSW instruction 3-441 FPATAN instruction 3-413 FPREM instruction 3-415 FPREM1 instruction 3-417 FPTAN instruction 3-419 FRNDINT instruction 3-421 FRSTOR instruction 3-422 FS register 3-587 FSAVE instruction 3-424 FSAVE/FNSAVE instructions 3-422

FSCALE instruction 3-427 FSIN instruction 3-429 FSINCOS instruction 3-431 FSQRT instruction 3-433 FST instruction 3-435 FSTCW instruction 3-437 FSTENV instruction 3-439 FSTP instruction 3-435 FSTSW instruction 3-441 FSUB instruction 3-443 FSUBP instruction 3-443 FSUBR instruction 3-446 FSUBRP instruction 3-446 FTST instruction 3-449 FUCOM instruction 3-451 FUCOMI instruction 3-376 FUCOMIP instruction 3-376 FUCOMP instruction 3-451 FUCOMPP instruction 3-451 FXAM instruction 3-454 FXCH instruction 3-456 FXRSTOR instruction 3-458 CPUID flag 3-245 FXSAVE instruction 3-461, 5-715, 5-716, 6-32, 6-45, 6-50, 6-54, 6-57, 6-60, 6-63, 6-66 CPUID flag 3-245 FXTRACT instruction 3-427, 3-469 FYL2X instruction 3-471 FYL2XP1 instruction 3-473 G GDT (global descriptor table) 3-599, 3-602 GDTR (global descriptor table register) 3-599, 4-624 General-purpose instructions 64-bit encodings B-18 non-64-bit encodings B-7 General-purpose registers moving value to and from 4-36 popping all 4-403 pushing all 4-524 GETSEC 7-1, 7-2, 7-5 GS register 3-587 H HADDPD instruction 3-482, 3-483 HADDPS instruction 3-485 Hexadecimal numbers 1-6 HLT instruction 3-488 HSUBPD instruction 3-491 HSUBPS instruction 3-494 I IA-32e mode CPUID flag 3-237 introduction 2-7, 2-13, 2-21, 2-36 see 64-bit mode see compatibility mode IDIV instruction 3-497 IDT (interrupt descriptor table) 3-517, 3-599 IDTR (interrupt descriptor table register) 3-599, 4-650 IF (interrupt enable) flag, EFLAGS register 3-166, 4-669 Immediate operands 2-3

INDEX-4 Vol. 2D

**INDEX**

IMUL instruction 3-500 IRETD instruction 3-538 IN instruction 3-504 J INC instruction 3-506, 3-609 Jcc instructions 3-547 Index (operand addressing) 2-3 JMP instruction 3-552 Initialization x87 FPU 3-394 Jump operation 3-552 initiating logical processor 7-4, 7-5, 7-10, 7-21, 7-22 L INS instruction 3-510, 4-561 L1 Context ID 3-242 INSB instruction 3-510 LAHF instruction 3-580 INSD instruction 3-510 LAR instruction 3-581 INSERTPS- Insert Scalar Single-Precision Floating-Point Value Last branch 3-513 interrupt & exception recording instruction encodings B-58, B-64, B-70 description of 4-579 Instruction format LDDQU instruction 3-584 base field 2-3 LDMXCSR instruction 3-586, 4-541, 6-7 description of reference information 3-1 LDS instruction 3-587 displacement 2-3 LDT (local descriptor table) 3-602 immediate 2-3 LDTR (local descriptor table register) 3-602, 4-652 index field 2-3 LEA instruction 3-594 Mod field 2-3 LEAVE instruction 3-596 ModR/M byte 2-3 LES instruction 3-587 opcode 2-3 LFENCE instruction 3-598 operands 1-6 LFS instruction 3-587 prefixes 2-1 LGDT instruction 3-599 r/m field 2-3 LGS instruction 3-587 reg/opcode field 2-3 LIDT instruction 3-599 scale field 2-3 LLDT instruction 3-602 SIB byte 2-3 LMSW instruction 3-604 See also: machine instructions, opcodes Load effective address operation 3-594 Instruction reference, nomenclature 3-1 LOADIWKEY—Load Internal Wrapping Key 3-606 Instruction set, reference 3-1 LOCK prefix 3-28, 3-33, 3-78, 3-132, 3-134, 3-136, 3-207, 3-319, INSW instruction 3-510 3-506, 3-609, 4-167, 4-170, 4-172, 4-609, 4-682, 6-23, 6-28, INT 3 instruction 3-516 6-36 Integer, storing, x87 FPU data type 3-396 Locking operation 3-609 Intel 64 architecture LODS instruction 3-611, 4-561 instruction format 2-1 LODSB instruction 3-611 Intel NetBurst microarchitecture 1-3 LODSD instruction 3-611 Intel software network link 1-9 LODSQ instruction 3-611 Intel VTune Performance Analyzer LODSW instruction 3-611 related information 1-9 Log (base 2), x87 FPU operation 3-473 Intel Xeon processor 1-1 Log epsilon, x87 FPU operation 3-471 Intel® Trusted Execution Technology 7-3 LOOP instructions 3-614 Inter-privilege level LOOPcc instructions 3-614 call, CALL instruction 3-139 LSL instruction 3-617 return, RET instruction 4-564 LSS instruction 3-587 Interrupts LTR instruction 3-620 returning from 3-538 LZCNT - Count the Number of Leading Zero Bits 3-622 software 3-516 M INTn instruction 3-516 Machine check architecture INTO instruction 3-516 CPUID flag 3-244 Intrinsics description 3-244 compiler functional equivalents C-1 Machine instructions composite C-14 64-bit mode B-1 description of 3-12 condition test (tttn) field B-6 list of C-1 direction bit (d) field B-6 simple C-2 floating-point instruction encodings B-61 INVD instruction 3-531 general description B-1 INVLPG instruction 3-533 general-purpose encodings B-7–B-37 IOPL (I/O privilege level) field, EFLAGS register 3-166 legacy prefixes B-1 IRET instruction 3-538 MMX encodings B-38–B-41

Vol. 2D INDEX-5

**INDEX**

opcode fields B-2 MOVD instruction 4-53 operand size (w) bit B-4 MOVDDUP- Replicate Double FP Values 4-60 P6 family encodings B-41 MOVDQ2Q instruction 4-80 Pentium processor family encodings B-37 MOVDQA- Move Aligned Packed Integer Values 4-67 reg (reg) field B-3, B-4 MOVDQU- Move Unaligned Packed Integer Values 4-72 REX prefixes B-2 MOVHLPS - Move Packed Single-Precision Floating-Point Values segment register (sreg) field B-5 High to Low 4-81 sign-extend (s) bit B-5 MOVHPD- Move High Packed Double-Precision Floating-Point ValSIMD 64-bit encodings B-37 ues 4-83 special 64-bit encodings B-61 MOVHPS- Move High Packed Single-Precision Floating-Point Valspecial fields B-2 ues 4-85 special-purpose register (eee) field B-5 MOVLPD- Move Low Packed Double-Precision Floating-Point ValSSE encodings B-42–B-47 ues 4-89 SSE2 encodings B-47–B-56 MOVLPS- Move Low Packed Single-Precision Floating-Point Values SSE3 encodings B-57–B-58 4-91 SSSE3 encodings B-58–B-60 MOVMSKPD instruction 4-93 VMX encodings B-112, B-113 MOVMSKPS instruction 4-95 See also: opcodes MOVNTDQ instruction 4-112 Machine status word, CR0 register 3-604, 4-654 MOVNTDQ- Store Packed Integers Using Non-Temporal Hint 4-99 MASKMOVDQU instruction 4-43 MOVNTI instruction 4-112 MAXPD- Maximum of Packed Double-Precision Floating-Point ValMOVNTPD- Store Packed Double-Precision Floating-Point Values ues 4-12 Using Non-Temporal Hint 4-103 MAXPS- Maximum of Packed Single-Precision Floating-Point ValMOVNTPS- Store Packed Single-Precision Floating-Point Values ues 4-15 Using Non-Temporal Hint 4-105 MAXSD- Return Maximum Scalar Double-Precision Floating-Point MOVNTQ instruction 4-107 Value 4-18 MOVQ instruction 4-53, 4-108 MAXSS- Return Maximum Scalar Single-Precision Floating-Point MOVQ2DQ instruction 4-111 Value 4-20 MOVS instruction 4-113, 4-561 measured environment 7-1 MOVSB instruction 4-113 Measured Launched Environment 7-1, 7-25 MOVSD instruction 4-113 MFENCE instruction 4-22 MOVSD- Move or Merge Scalar Double-Precision Floating-Point MINPD- Minimum of Packed Double-Precision Floating-Point ValValue 4-117 ues 4-23 MOVSHDUP- Replicate Single FP Values 4-120 MINPS- Minimum of Packed Single-Precision Floating-Point Values MOVSLDUP- Replicate Single FP Values 4-123 4-26 MOVSQ instruction 4-113 MINSD- Return Minimum Scalar Double-Precision Floating-Point MOVSS- Move or Merge Scalar Single-Precision Floating-Point ValValue 4-29 ue 4-126 MINSS- Return Minimum Scalar Single-Precision Floating-Point ValMOVSW instruction 4-113 ue 4-31 MOVSX instruction 4-130 MLE 7-1 MOVSXD instruction 4-130 MMX instructions MOVUPD- Move Unaligned Packed Double-Precision Floating-Point CPUID flag for technology 3-245 Values 4-132 encodings B-38 MOVUPS- Move Unaligned Packed Single-Precision Floating-Point Mod field, instruction format 2-3 Values 4-136 Model & family information 3-249 MOVZX instruction 4-140 ModR/M byte 2-3 MSRs (model specific registers) 16-bit addressing forms 2-5 reading 4-543 32-bit addressing forms of 2-6 MUL instruction 3-23, 4-150 description of 2-3 MULPD- Multiply Packed Double-Precision Floating-Point Values MONITOR instruction 4-33 4-152 CPUID flag 3-241 MULPS- Multiply Packed Single-Precision Floating-Point Values feature data 3-249 4-155 MOV instruction 4-35 MULSD- Multiply Scalar Double-Precision Floating-Point Values MOV instruction (control registers) 4-40, 4-63, 4-65 4-158 MOV instruction (debug registers) 4-43, 4-53 MULSS- Multiply Scalar Single-Precision Floating-Point Values MOVAPD- Move Aligned Packed Double-Precision Floating-Point 4-160 Values 4-45 Multi-byte no operation 4-167, 4-169, B-13 MOVAPS- Move Aligned Packed Single-Precision Floating-Point MULX - Unsigned Multiply Without Affecting Flags 4-162 Values 4-49 MVMM 7-1, 7-5, 7-37

INDEX-6 Vol. 2D

**INDEX**

MWAIT instruction 4-164 machine encodings B-41 CPUID flag 3-241 PABSB instruction 4-186, 4-200, 5-143, 5-534, 5-545, 5-560 feature data 3-249 PABSD instruction 4-186, 4-200, 5-143, 5-534, 5-545, 5-560 N PABSW instruction 4-186, 4-200, 5-143, 5-534, 5-545, 5-560 NaN. testing for 3-449 PACKSSDW instruction 4-192 Near PACKSSWB instruction 4-192 return, RET instruction 4-564 PACKUSWB instruction 4-205 NEG instruction 3-609, 4-167 PADDB/PADDW/PADDD/PADDQ - Add Packed Integers 4-210 NetBurst microarchitecture (see Intel NetBurst microarchitecture) PADDSB instruction 4-217 No operation 4-167, 4-169, B-12 PADDSW instruction 4-217 Nomenclature, used in instruction reference pages 3-1 PADDUSB instruction 4-221 NOP instruction 4-169 PADDUSW instruction 4-221 NOT instruction 3-609, 4-170 PALIGNR instruction 4-225 Notation PAND instruction 4-229 bit and byte order 1-5 PANDN instruction 4-232 exceptions 1-7 GETSEC 7-4 hexadecimal and binary numbers 1-6 PAUSE instruction 4-235 instruction operands 1-6 PAVGB instruction 4-236 reserved bits 1-6 PAVGW instruction 4-236 segmented addressing 1-7 PCE flag, CR4 register 4-548 Notational conventions 1-5 PCMPEQB instruction 4-251 NT (nested task) flag, EFLAGS register 3-538 PCMPEQD instruction 4-251 O PCMPEQW instruction 4-251 OF (carry) flag, EFLAGS register 3-501 PCMPGTB instruction 4-264 OF (overflow) flag, EFLAGS register 3-32, 3-516, 4-150, 4-609, PCMPGTD instruction 4-264 4-635, 4-638, 4-682 PCMPGTW instruction 4-264 Opcode format 2-3 PDEP - Parallel Bits Deposit 4-284 Opcodes PE (protection enable) flag, CR0 register 3-604 addressing method codes for A-1 Pending break enable 3-245 extensions A-17 Pentium 4 processor 1-1 extensions tables A-18 Pentium II processor 1-3 group numbers A-17 Pentium III processor 1-3 integers Pentium Pro processor 1-3 one-byte opcodes A-7 Pentium processor 1-1 two-byte opcodes A-7 Pentium processor family processors key to abbreviations A-1 machine encodings B-37 look-up examples A-3, A-17, A-20 Performance-monitoring counters ModR/M byte A-17 CPUID inquiry for 3-250 one-byte opcodes A-3, A-7 PEXT - Parallel Bits Extract 4-286 opcode maps A-1 PEXTRW instruction 4-291 operand type codes for A-2 PHADDD instruction 4-294 register codes for A-3 PHADDSW instruction 4-298 superscripts in tables A-6 PHADDW instruction 4-294 two-byte opcodes A-4, A-5, A-7 PH—Fused Multiply-Add of Packed FP16 Values 5-200 VMX instructions B-112, B-113 PH—Fused Multiply-Subtract of Packed FP16 Values 5-246 x87 ESC instruction opcodes A-20 PHSUBD instruction 4-302 Operands 1-6 PHSUBSW instruction 4-305 OR instruction 3-609, 4-172 PHSUBW instruction 4-302 ORPS- Bitwise Logical OR of Packed Single Precision Floating-Point Pi 3-403 Values 4-177 PINSRW instruction 4-310, 4-437 OUT instruction 4-180 PMADDUBSW instruction 4-312 OUTS instruction 4-182, 4-561 PMADDUDSW instruction 4-312 OUTSB instruction 4-182 PMADDWD instruction 4-315 OUTSD instruction 4-182 PMULHRSW instruction 4-375 OUTSW instruction 4-182 PMULHUW instruction 4-379 Overflow exception (#OF) 3-516 PMULHW instruction 4-383 P PMULLW instruction 4-391 P6 family processors PMULUDQ instruction 4-395 description of 1-1 POP instruction 4-398

Vol. 2D INDEX-7

**INDEX**

POPA instruction 4-403 PUSHA instruction 4-524 POPAD instruction 4-403 PUSHAD instruction 4-524 POPF instruction 4-407 PUSHF instruction 4-526 POPFD instruction 4-407 PUSHFD instruction 4-526 POPFQ instruction 4-407 PXOR instruction 4-529 POR instruction 4-411 R PREFETCHh instruction 4-414 R/m field, instruction format 2-3 PREFETCHWT1—Prefetch Vector Data Into Caches with Intent to RC (rounding control) field, x87 FPU control word 3-396, 3-403, Write and T1 Hint 4-418 3-435 Prefixes RCL instruction 4-532 Address-size override prefix 2-2 RCPPS instruction 4-537 Branch hints 2-2 RCPSS instruction 4-539 branch hints 2-2 RCR instruction 4-532 instruction, description of 2-1 RDMSR instruction 4-543, 4-556 legacy prefix encodings B-1 CPUID flag 3-244 LOCK 2-1, 3-609 RDPMC instruction 4-546, 4-548, 6-11 Operand-size override prefix 2-2 RDTSC instruction 4-550, 4-556, 4-558 REP or REPE/REPZ 2-1 Reg/opcode field, instruction format 2-3 REP/REPE/REPZ/REPNE/REPNZ 4-560 Related literature 1-8 REPNE/REPNZ 2-1 Remainder, x87 FPU operation 3-417 REX prefix encodings B-2 REP/REPE/REPZ/REPNE/REPNZ prefixes 3-196, 3-511, 4-183, Segment override prefixes 2-2 4-560 PSADBW instruction 4-418 Reserved PSHUFB instruction 4-422 use of reserved bits 1-6 PSHUFD instruction 4-426 Responding logical processor 7-4 PSHUFHW instruction 4-430 responding logical processor 7-4, 7-5 PSHUFLW instruction 4-433 RET instruction 4-564 PSHUFW instruction 4-436 REX prefixes PSIGNB instruction 4-437 addressing modes 2-9 PSIGND instruction 4-437 and INC/DEC 2-8 PSIGNW instruction 4-437 encodings 2-8, B-2 PSLLD instruction 4-443 field names 2-9 PSLLDQ instruction 4-441 ModR/M byte 2-8 PSLLQ instruction 4-443 overview 2-7 PSLLW instruction 4-443 REX.B 2-8 PSRAD instruction 4-455 REX.R 2-8 PSRAW instruction 4-455 REX.W 2-8 PSRLD instruction 4-467 special encodings 2-11 PSRLDQ instruction 4-465 RIP-relative addressing 2-12 PSRLQ instruction 4-467 ROL instruction 4-532 PSRLW instruction 4-467 ROR instruction 4-532 PSUBB instruction 4-479 RORX - Rotate Right Logical Without Affecting Flags 4-577 PSUBD instruction 4-479 Rounding PSUBQ instruction 4-486 modes, floating-point operations 4-579 PSUBSB instruction 4-489 Rounding control (RC) field PSUBSW instruction 4-489 MXCSR register 4-579 PSUBUSB instruction 4-493 x87 FPU control word 4-579 PSUBUSW instruction 4-493 Rounding, round to integer, x87 FPU operation 3-421 PSUBW instruction 4-479 ROUNDPD- Round Packed Double-Precision Floating-Point Values PTEST- Packed Bit Test 3-575 4-683 PUNPCKHBW instruction 4-501 RPL field 3-93 PUNPCKHDQ instruction 4-501 RSM instruction 4-588 PUNPCKHQDQ instruction 4-501 RSQRTPS instruction 4-590 PUNPCKHWD instruction 4-501 RSQRTSS instruction 4-592 PUNPCKLBW instruction 4-511 S PUNPCKLDQ instruction 4-511 Safer Mode Extensions 7-1 PUNPCKLQDQ instruction 4-511 SAHF instruction 4-597 PUNPCKLWD instruction 4-511 SAL instruction 4-599 PUSH instruction 4-521 SAR instruction 4-599

INDEX-8 Vol. 2D

**INDEX**

SBB instruction 3-609, 4-608 SSE extensions Scale (operand addressing) 2-3 cacheability instruction encodings B-47 Scale, x87 FPU operation 3-427 CPUID flag 3-245 Scan string instructions 4-611 floating-point encodings B-42 SCAS instruction 4-561, 4-611 instruction encodings B-42 SCASB instruction 4-611 integer instruction encodings B-46 SCASD instruction 4-611 memory ordering encodings B-47 SCASW instruction 4-611 SSE2 extensions Segment cacheability instruction encodings B-56 descriptor, segment limit 3-617 CPUID flag 3-245 limit 3-617 floating-point encodings B-48 registers, moving values to and from 4-36 integer instruction encodings B-52 selector, RPL field 3-93 SSE3 Segmented addressing 1-7 CPUID flag 3-241 Self Snoop 3-245 SSE3 extensions GETSEC 7-2, 7-4, 7-5 CPUID flag 3-241 SENTER sleep state 7-10 event mgmt instruction encodings B-57 SETcc instructions 4-618 floating-point instruction encodings B-57 GETSEC 7-4 integer instruction encodings B-57, B-58 SF (sign) flag, EFLAGS register 3-32 SSSE3 extensions B-58, B-64, B-70 SFENCE instruction 4-623 CPUID flag 3-241 SGDT instruction 4-624 Stack, pushing values on 4-521 SHAF instruction 4-597 Status flags, EFLAGS register 3-177, 3-179, 3-371, 3-376, 3-550, SH—Fused Multiply-Add of Scalar FP16 Values 5-215 4-619, 4-711 SH—Fused Multiply-Subtract of Scalar FP16 Values 5-261 STC instruction 4-667 Shift instructions 4-599 STD instruction 4-668 SHL instruction 4-599 Stepping information 3-249 SHLD instruction 4-635 STI instruction 4-669 SHR instruction 4-599 STMXCSR instruction 4-671 SHRD instruction 4-638 STOS instruction 4-561, 4-672 SHUFPD - Shuffle Packed Double Precision Floating-Point Values STOSB instruction 4-672 4-641, 4-683 STOSD instruction 4-672 SHUFPS - Shuffle Packed Single Precision Floating-Point Values STOSQ instruction 4-672 4-646 STOSW instruction 4-672 SIB byte 2-3 STR instruction 4-676 32-bit addressing forms of 2-7, 2-21 String instructions 3-195, 3-510, 3-611, 4-113, 4-182, 4-611, description of 2-3 4-672 SIDT instruction 4-624, 4-650 SUB instruction 3-25, 3-317, 3-609, 4-681 Significand, extracting from floating-point number 3-469 SUBPD- Subtract Packed Double Precision Floating-Point Values SIMD floating-point exceptions, unmasking, effects of 3-586, 4-683 4-541, 6-7 SUBPD- Subtract Packed Double-Precision Floating-Point Values Sine, x87 FPU operation 3-429, 3-431 4-683 SINIT 7-4 SUBPS- Subtract Packed Single-Precision Floating-Point Values SLDT instruction 4-652 4-686 GETSEC 7-4 SUBSD- Subtract Scalar Double-Precision Floating-Point Values SMSW instruction 4-654 4-689 SpeedStep technology 3-241 SUBSS- Subtract Scalar Single-Precision Floating-Point Values SQRTPD- Square Root of Double-Precision Floating-Point Values 4-691 4-683 SWAPGS instruction 4-693 SQRTPD—Square Root of Double-Precision Floating-Point Values SYSCALL instruction 4-695 4-656 SYSENTER instruction 4-698 SQRTPS- Square Root of Single-Precision Floating-Point Values CPUID flag 3-244 4-659 SYSEXIT instruction 4-701 SQRTSD - Compute Square Root of Scalar Double-Precision FloatCPUID flag 3-244 ing-Point Value 4-662, 4-683 SYSRET instruction 4-704 SQRTSS - Compute Square Root of Scalar Single-Precision FloatT ing-Point Value 4-664 Tangent, x87 FPU operation 3-419 Square root, Fx87 PU operation 3-433 Task register SS register 3-587, 4-36, 4-399 loading 3-620

Vol. 2D INDEX-9

**INDEX**

storing 4-676 Task switch CALL instruction 3-139 return from nested task, IRET instruction 3-538 TEST instruction 4-711, 5-711 Thermal Monitor CPUID flag 3-245 Thermal Monitor 2 3-241 CPUID flag 3-241 Time Stamp Counter 3-244 Time-stamp counter, reading 4-556, 4-558 TLB entry, invalidating (flushing) 3-533 Trusted Platform Module 7-5 TS (task switched) flag, CR0 register 3-170 TSS, relationship to task register 4-676 TZCNT - Count the Number of Trailing Zero Bits 4-721 U UCOMISD - Unordered Compare Scalar Double-Precision Floating-Point Values and Set EFLAGS 4-723 UCOMISD instruction 4-721 UCOMISS - Unordered Compare Scalar Single-Precision Floating-Point Values and Set EFLAGS 4-725 UD2 instruction 4-727 Undefined, format opcodes 3-449 Unordered values 3-373, 3-449, 3-451 UNPCKHPD- Unpack and Interleave High Packed Double-Precision Floating-Point Values 4-734 UNPCKHPS- Unpack and Interleave High Packed Single-Precision Floating-Point Values 4-738 UNPCKLPD- Unpack and Interleave Low Packed Double-Precision Floating-Point Values 4-742 UNPCKLPS- Unpack and Interleave Low Packed Single-Precision Floating-Point Values 4-746 V

VADDPH—Add Packed FP16 Values 5-5 VADDSH—Add Scalar FP16 Values 5-7 VALIGND/VALIGNQ—Align Doubleword/Quadword Vectors 5-8 VBLENDMPD/VBLENDMPS—Blend Float64/Float32 Vectors Using an OpMask Control 5-11 VBROADCAST—Load with Broadcast Floating-Point Data 5-13 VCMPPH—Compare Packed FP16 Values 5-21 VCMPSH—Compare Scalar FP16 Values 5-23 VCOMISH—Compare Scalar Ordered FP16 Values and Set EFLAGS 5-25

VCOMPRESSPD—Store Sparse Packed Double Precision Floating-Point Values Into Dense Memory 5-27 VCOMPRESSPS—Store Sparse Packed Single Precision Floating-Point Values Into Dense Memory 5-29 VCVTDQ2PH—Convert Packed Signed Doubleword Integers to Packed FP16 Values 5-31

VCVTNE2PS2BF16—Convert Two Packed Single Data to One Packed BF16 Data 5-33

VCVTNEPS2BF16—Convert Packed Single Data to Packed BF16 Data 5-35

VCVTPD2PH—Convert Packed Double Precision FP Values to Packed FP16 Values 5-37 VCVTPD2QQ—Convert Packed Double Precision Floating-Point Values to Packed Quadword Integers 5-39 VCVTPD2UDQ—Convert Packed Double-Precision Floating-Point

Values to Packed Unsigned Doubleword Integers 5-41 VCVTPD2UQQ—Convert Packed Double Precision Floating-Point Values to Packed Unsigned Quadword Integers 5-43 VCVTPH2DQ—Convert Packed FP16 Values to Signed Doubleword Integers 5-45 VCVTPH2PD—Convert Packed FP16 Values to FP64 Values 5-47 VCVTPH2QQ—Convert Packed FP16 Values to Signed Quadword Integer Values 5-53 VCVTPH2UDQ—Convert Packed FP16 Values to Unsigned Doubleword Integers 5-55 VCVTPH2UQQ—Convert Packed FP16 Values to Unsigned Quadword Integers 5-57 VCVTPH2UW—Convert Packed FP16 Values to Unsigned Word Integers 5-59 VCVTPH2W—Convert Packed FP16 Values to Signed Word Integers 5-61 VCVTPS2PH—Convert Single-Precision FP Value to 16-bit FP Value 5-63 VCVTPS2PHX—Convert Packed Single Precision Floating-Point Values to Packed FP16 Values 5-67 VCVTPS2UDQ—Convert Packed Single Precision Floating-Point Values to Packed Unsigned Doubleword Integer Values 5-69 VCVTPS2UQQ—Convert Packed Single Precision Floating-Point Values to Packed Unsigned Quadword Integer Values 5-74 VCVTQQ2PD—Convert Packed Quadword Integers to Packed Double Precision Floating-Point Values 5-76 VCVTQQ2PH—Convert Packed Signed Quadword Integers to Packed FP16 Values 5-78 VCVTQQ2PS—Convert Packed Quadword Integers to Packed Single Precision Floating-Point Values 5-80 VCVTSD2SH—Convert Low FP64 Value to an FP16 Value 5-82 VCVTSD2USI—Convert Scalar Double Precision Floating-Point Value to Unsigned Doubleword Integer 5-83 VCVTSH2SD—Convert Low FP16 Value to an FP64 Value 5-84 VCVTSH2SI—Convert Low FP16 Value to Signed Integer 5-85 VCVTSH2SS—Convert Low FP16 Value to FP32 Value 5-86 VCVTSH2USI—Convert Low FP16 Value to Unsigned Integer 5-87 VCVTSI2SH—Convert a Signed Doubleword/Quadword Integer to an FP16 Value 5-88

VCVTSS2SH—Convert Low FP32 Value to an FP16 Value 5-90 VCVTSS2USI—Convert Scalar Single Precision Floating-Point Value to Unsigned Doubleword Integer 5-91 VCVTTPD2QQ—Convert With Truncation Packed Double Precision Floating-Point Values to Packed Quadword Integers 5-93 VCVTTPD2UDQ—Convert With Truncation Packed Double Precision Floating-Point Values to Packed Unsigned Doubleword Integers 5-95

VCVTTPD2UQQ—Convert With Truncation Packed Double Precision Floating-Point Values to Packed Unsigned Quadword Integers 5-97

VCVTTPH2DQ—Convert with Truncation Packed FP16 Values to Signed Doubleword Integers 5-99 VCVTTPH2QQ—Convert with Truncation Packed FP16 Values to Signed Quadword Integers 5-101 VCVTTPH2UDQ—Convert with Truncation Packed FP16 Values to Unsigned Doubleword Integers 5-103 VCVTTPH2UQQ—Convert with Truncation Packed FP16 Values to Unsigned Quadword Integers 5-105 VCVTTPH2UW—Convert Packed FP16 Values to Unsigned Word

INDEX-10 Vol. 2D

**INDEX**

Integers 5-107 VCVTTPH2W—Convert Packed FP16 Values to Signed Word Integers 5-109 VCVTTPS2QQ—Convert With Truncation Packed Single Precision Floating-Point Values to Packed Signed Quadword Integer Values 5-113

VCVTTPS2UDQ—Convert With Truncation Packed Single Precision Floating-Point Values to Packed Unsigned Doubleword Integer Values 5-111 VCVTTPS2UQQ—Convert With Truncation Packed Single Precision Floating-Point Values to Packed Unsigned Quadword Integer Values 5-115 VCVTTSD2USI—Convert With Truncation Scalar Double Precision Floating-Point Value to Unsigned Integer 5-117 VCVTTSH2SI—Convert with Truncation Low FP16 Value to a Signed Integer 5-118 VCVTTSH2USI—Convert with Truncation Low FP16 Value to an Unsigned Integer 5-119 VCVTTSS2USI—Convert With Truncation Scalar Single Precision Floating-Point Value to Unsigned Integer 5-120 VCVTUDQ2PD—Convert Packed Unsigned Doubleword Integers to Packed Double Precision Floating-Point Values 5-121 VCVTUDQ2PH—Convert Packed Unsigned Doubleword Integers to Packed FP16 Values 5-123 VCVTUDQ2PS—Convert Packed Unsigned Doubleword Integers to Packed Single Precision Floating-Point Values 5-125 VCVTUQQ2PD—Convert Packed Unsigned Quadword Integers to Packed Double Precision Floating-Point Values 5-127 VCVTUQQ2PH—Convert Packed Unsigned Quadword Integers to Packed FP16 Values 5-129 VCVTUQQ2PS—Convert Packed Unsigned Quadword Integers to Packed Single Precision Floating-Point Values 5-133 VCVTUSI2SD—Convert Unsigned Integer to Scalar Double Precision Floating-Point Value 5-135

VCVTUSI2SH—Convert Unsigned Doubleword Integer to an FP16 Value 5-131 VCVTUSI2SS—Convert Unsigned Integer to Scalar Single Precision Floating-Point Value 5-137 VCVTUW2PH—Convert Packed Unsigned Word Integers to FP16 Values 5-139 VCVTW2PH—Convert Packed Signed Word Integers to FP16 Values 5-141 VDBPSADBW—Double Block Packed Sum-Absolute-Differences (SAD) on Unsigned Bytes 5-143 VDIVPH—Divide Packed FP16 Values 5-146 VDIVSH—Divide Scalar FP16 Values 5-148 VDPBF16PS—Dot Product of BF16 Pairs Accumulated Into Packed Single Precision 5-149 VERR instruction 5-155 VERR/VERW—Verify a Segment for Reading or Writing 5-155 Version information, processor 3-216 VERW instruction 5-155 VEX 3-3 VEX.B 3-3 VEX.L 3-3, 3-4 VEX.mmmmm 3-3 VEX.pp 3-3, 3-4 VEX.R 3-4 VEX.W 3-3

VEX.X 3-3

VEXP2PS—Approximation to the Exponential 2^x of Packed Single-Precision Floating-Point Values with Less Than 2^-23 Relative Error 8-10

VEXPANDPD—Load Sparse Packed Double Precision Floating-Point Values From Dense Memory 5-151 VEXPANDPS—Load Sparse Packed Single Precision Floating-Point Values From Dense Memory 5-153

VEXTRACTF128/VEXTRACTF32x4/VEXTRACTF64x2/VEXTRACT F32x8/VEXTRACTF64x4— Extract Packed Floating-Point Values 5-157

VEXTRACTI128/VEXTRACTI32x4/VEXTRACTI64x2/VEXTRACTI3 2x8/VEXTRACTI64x4—Extract Packed Integer Values 5-163 VFCMADDCPH/VFMADDCPH—Complex Multiply and Accumulate FP16 Values 5-169

VFCMADDCSH/VFMADDCSH—Complex Multiply and Accumulate Scalar FP16 Values 5-172

VFCMULCPH/VFMULCPH—Complex Multiply FP16 Values 5-174 VFCMULCSH/VFMULCSH—Complex Multiply Scalar FP16 Values 5-177

VFIXUPIMMPD—Fix Up Special Packed Float64 Values 5-179 VFIXUPIMMPS—Fix Up Special Packed Float32 Values 5-183 VFIXUPIMMSD—Fix Up Special Scalar Float64 Value 5-187 VFIXUPIMMSS—Fix Up Special Scalar Float32 Value 5-190 VFMADD132PD/VFMADD213PD/VFMADD231PD—Fused Multiply-Add of Packed Double Precision Floating-Point Values 5-193 VFMADD132PS/VFMADD213PS/VFMADD231PS—Fused Multiply-Add of Packed Single Precision Floating-Point Values 5-206 VFMADD132SD/VFMADD213SD/VFMADD231SD—Fused Multiply-Add of Scalar Double Precision Floating-Point Values 5-212 VFMADD132SS/VFMADD213SS/VFMADD231SS—Fused Multiply-Add of Scalar Single Precision Floating-Point Values 5-218 VFMADDSUB132PD/VFMADDSUB213PD/VFMADDSUB231PD—F used Multiply-Alternating Add/Subtract of Packed Double Precision Floating-Point Values 5-221

VFMADDSUB132PH/VFMADDSUB213PH/VFMADDSUB231PH—F used Multiply-Alternating Add/Subtract of Packed FP16 Values 5-228

VFMADDSUB132PS/VFMADDSUB213PS/VFMADDSUB231PS—Fu sed Multiply-Alternating Add/Subtract of Packed Single-Precision Floating-Point Values 5-233

VFMSUB132PD/VFMSUB213PD/VFMSUB231PD—Fused Multiply-Subtract of Packed Double Precision Floating-Point Values 5-240

VFMSUB132PS/VFMSUB213PS/VFMSUB231PS— Fused Multiply-Subtract of Packed Single-Precision Floating-Point Values 5-252

VFMSUB132SD/VFMSUB213SD/VFMSUB231SD— Fused Multiply-Subtract of Scalar Double-Precision Floating-Point Values 5-258

VFMSUB132SS/VFMSUB213SS/VFMSUB231SS—Fused Multiply-Subtract of Scalar Single-Precision Floating-Point Values 5-264

VFMSUBADD132PD/VFMSUBADD213PD/VFMSUBADD231PD—F used Multiply-Alternating Subtract/Add of Packed Double-Precision Floating-Point Values 5-267

VFMSUBADD132PH/VFMSUBADD213PH/VFMSUBADD231PH—F used Multiply-Alternating Subtract/Add of Packed FP16 Values 5-274

Vol. 2D INDEX-11

**INDEX**

VFMSUBADD132PS/VFMSUBADD213PS/VFMSUBADD231PS—Fu sed Multiply-Alternating Subtract/Add of Packed Single Precision Floating-Point Values 5-279 VFNMADD132PD/VFMADD213PD/VFMADD231PD —Fused Negative Multiply-Add of Packed Double-Precision Floating-Point Values 5-286 VFNMADD132PS/VFNMADD213PS/VFNMADD231PS—Fused Negative Multiply-Add of Packed Single-Precision Floating-Point Values 5-292 VFNMADD132SD/VFNMADD213SD/VFNMADD231SD—Fused Negative Multiply-Add of Scalar Double-Precision Floating-Point Values 5-298 VFNMADD132SS/VFNMADD213SS/VFNMADD231SS—Fused Negative Multiply-Add of Scalar Single Precision Floating-Point Values 5-301 VFNMSUB132PD/VFNMSUB213PD/VFNMSUB231PD—Fused Negative Multiply-Subtract of Packed Double Precision Floating-Point Values 5-304 VFNMSUB132PS/VFNMSUB213PS/VFNMSUB231PS—Fused Negative Multiply-Subtract of Packed Single Precision Floating-Point Values 5-310

VFNMSUB132SD/VFNMSUB213SD/VFNMSUB231SD—Fused Negative Multiply-Subtract of Scalar Double-Precision Floating-Point Values 5-316 VFNMSUB132SS/VFNMSUB213SS/VFNMSUB231SS—Fused Negative Multiply-Subtract of Scalar Single Precision Floating-Point Values 5-319

VFPCLASSPD—Tests Types of Packed Float64 Values 5-322 VFPCLASSPH—Test Types of Packed FP16 Values 5-325 VFPCLASSPS—Tests Types of Packed Float32 Values 5-328 VFPCLASSSD—Tests Type of a Scalar Float64 Value 5-330 VFPCLASSSH—Test Types of Scalar FP16 Values 5-332 VFPCLASSSS—Tests Type of a Scalar Float32 Value 5-333

VGATHERDPD/VGATHERQPD—Gather Packed Double Precision Floating-Point Values Using Signed Dword/Qword Indices 5-335 VGATHERDPS/VGATHERDPD—Gather Packed Single, Packed Double with Signed Dword 5-343

VGATHERDPS/VGATHERQPS—Gather Packed SP FP values Using Signed Dword/Qword Indices 5-339

VGATHERPF1DPS/VGATHERPF1QPS/VGATHERPF1DPD/VGATHE RPF1QPD - Sparse Prefetch Packed SP/DP Data Values with Signed Dword, Signed Qword Indices Using T1 Hint 8-14 VGATHERQPS/VGATHERQPD—Gather Packed Single, Packed Double with Signed Qword Indices 5-346

VGETEXPPD—Convert Exponents of Packed Double Precision Floating-Point Values to Double Precision Floating-Point Values 5-349

VGETEXPPH—Convert Exponents of Packed FP16 Values to FP16 Values 5-352

VGETEXPPS—Convert Exponents of Packed Single Precision Floating-Point Values to Single Precision Floating-Point Values 5-355 VGETEXPSD—Convert Exponents of Scalar Double Precision Floating-Point Value to Double Precision Floating-Point Value 5-359 VGETEXPSH—Convert Exponents of Scalar FP16 Values to FP16 Values 5-361

VGETEXPSS—Convert Exponents of Scalar Single Precision Floating-Point Value to Single Precision Floating-Point Value 5-363 VGETMANTPD—Extract Float64 Vector of Normalized Mantissas From Float64 Vector 5-365

VGETMANTPH—Extract FP16 Vector of Normalized Mantissas from FP16 Vector 5-369 VGETMANTPS—Extract Float32 Vector of Normalized Mantissas From Float32 Vector 5-373 VGETMANTSD—Extract Float64 of Normalized Mantissas From Float64 Scalar 5-376 VGETMANTSH—Extract FP16 of Normalized Mantissa from FP16 Scalar 5-378 VGETMANTSS—Extract Float32 Vector of Normalized Mantissa From Float32 Vector 5-380 VINSERTF128/VINSERTF32x4/VINSERTF64x2/VINSERTF32x8/ VINSERTF64x4—Insert Packed Floating-Point Values 5-382 VINSERTI128/VINSERTI32x4/VINSERTI64x2/VINSERTI32x8/VIN SERTI64x4—Insert Packed Integer Values 5-386 Virtual Machine Monitor 7-1 VM (virtual 8086 mode) flag, EFLAGS register 3-538 VMASKMOV—Conditional SIMD Packed Loads and Stores 5-390 VMAXPH—Return Maximum of Packed FP16 Values 5-393 VMAXSH—Return Maximum of Scalar FP16 Values 5-395 VMINPH—Return Minimum of Packed FP16 Values 5-397 VMINSH—Return Minimum Scalar FP16 Value 5-399 VMM 7-1 VMOVSH—Move Scalar FP16 Value 5-401 VMOVW—Move Word 5-403 VMULPH—Multiply Packed FP16 Values 5-404 VMULSH—Multiply Scalar FP16 Values 5-406 VP2INTERSECTD/VP2INTERSECTQ—Compute Intersection Between DWORDS/QUADWORDS to a Pair of Mask Registers 5-407 VPBLENDD—Blend Packed Dwords 5-409

VPBLENDMB/VPBLENDMW—Blend Byte/Word Vectors Using an Opmask Control 5-411 VPBLENDMD/VPBLENDMQ—Blend Int32/Int64 Vectors Using an OpMask Control 5-413

VPBROADCASTB/W/D/Q—Load With Broadcast Integer Data From General Purpose Register 5-416 VPBROADCAST—Load Integer and Broadcast 5-419 VPBROADCASTM—Broadcast Mask to Vector Register 5-428

VPCMPB/VPCMPUB—Compare Packed Byte Values Into Mask 5-430 VPCMPD/VPCMPUD—Compare Packed Integer Values Into Mask 5-433

VPCMPQ/VPCMPUQ—Compare Packed Integer Values into Mask 5-436

VPCMPW/VPCMPUW—Compare Packed Word Values Into Mask 5-439

VPCOMPRESSB/VCOMPRESSW—Store Sparse Packed Byte/Word Integer Values Into Dense Memory/Register 5-442 VPCOMPRESSD—Store Sparse Packed Doubleword Integer Values Into Dense Memory/Register 5-445

VPCOMPRESSQ—Store Sparse Packed Quadword Integer Values Into Dense Memory/Registe 5-447

VPCONFLICTD/Q—Detect Conflicts Within a Vector of Packed Dword/Qword Values Into Dense Memory/ Register 5-449

VPDPBUSD—Multiply and Add Unsigned and Signed Bytes 5-452 VPDPBUSDS—Multiply and Add Unsigned and Signed Bytes With Saturation 5-454

VPDPWSSD—Multiply and Add Signed Word Integers 5-456 VPDPWSSDS—Multiply and Add Signed Word Integers With Saturation 5-458

INDEX-12 Vol. 2D

**INDEX**

VPERM2F128—Permute Floating-Point Values 5-460 VPERM2I128—Permute Integer Values 5-462 VPERMB—Permute Packed Bytes Elements 5-464 VPERMD/VPERMW—Permute Packed Doubleword/Word Elements 5-466 VPERMI2B - Full Permute of Bytes from Two Tables Overwriting the Index 8-6 VPERMI2B—Full Permute of Bytes From Two Tables Overwriting the Index 5-469 VPERMI2W/D/Q/PS/PD—Full Permute From Two Tables Overwriting the Index 5-471 VPERMILPD—Permute In-Lane of Pairs of Double Precision Floating-Point Values 5-477 VPERMILPS—Permute In-Lane of Quadruples of Single Precision Floating-Point Values 5-482 VPERMPD—Permute Double Precision Floating-Point Elements 5-487 VPERMPS—Permute Single Precision Floating-Point Elements 5-490 VPERMQ—Qwords Element Permutation 5-493

VPERMT2B—Full Permute of Bytes From Two Tables Overwriting a Table 5-496 VPERMT2W/D/Q/PS/PD—Full Permute From Two Tables Overwriting One Table 5-498

VPEXPANDB/VPEXPANDW—Expand Byte/Word Values 5-503 VPEXPANDD—Load Sparse Packed Doubleword Integer Values From Dense Memory/Register 5-506

VPEXPANDQ—Load Sparse Packed Quadword Integer Values From Dense Memory/Register 5-508

VPGATHERDD/VPGATHERDQ—Gather Packed Dword, Packed Qword With Signed Dword Indices 5-514 VPGATHERDD/VPGATHERQD—Gather Packed Dword Values Using Signed Dword/Qword Indices 5-510 VPGATHERDQ/VPGATHERQQ—Gather Packed Qword values Using Signed Dword/Qword Indices 5-517 VPGATHERQD/VPGATHERQQ—Gather Packed Dword, Packed Qword with Signed Qword Indices 5-521 VPLZCNTD/Q—Count the Number of Leading Zero Bits for Packed Dword, Packed Qword Values 5-524 VPMADD52HUQ—Packed Multiply of Unsigned 52-Bit Unsigned Integers and Add High 52-Bit Products to 64-Bit Accumulators 5-527

VPMADD52LUQ—Packed Multiply of Unsigned 52-Bit Integers and Add the Low 52-Bit Products to Qword Accumulators 5-529 VPMASKMOV—Conditional SIMD Integer Packed Loads and Stores 5-531

VPMOVB2M/VPMOVW2M/VPMOVD2M/VPMOVQ2M—Convert a Vector Register to a Mask 5-534 VPMOVDB/VPMOVSDB/VPMOVUSDB - Down Convert DWord to Byte 5-537 VPMOVDB/VPMOVSDB/VPMOVUSDB—Down Convert DWord to Byte 5-537 VPMOVDW/VPMOVSDW/VPMOVUSDW - Down Convert DWord to Word 5-541 VPMOVDW/VPMOVSDW/VPMOVUSDW—Down Convert DWord to Word 5-541 VPMOVM2B/VPMOVM2W/VPMOVM2D/VPMOVM2Q—Convert a Mask Register to a Vector Register 5-545 VPMOVQB/VPMOVSQB/VPMOVUSQB - Down Convert QWord to

Byte 5-548 VPMOVQB/VPMOVSQB/VPMOVUSQB—Down Convert QWord to Byte 5-548

VPMOVQD/VPMOVSQD/VPMOVUSQD - Down Convert QWord to DWord 5-552

VPMOVQD/VPMOVSQD/VPMOVUSQD—Down Convert QWord to DWord 5-552 VPMOVQW/VPMOVSQW/VPMOVUSQW - Down Convert QWord to Word 5-556 VPMOVQW/VPMOVSQW/VPMOVUSQW—Down Convert QWord to Word 5-556 VPMOVWB/VPMOVSWB/VPMOVUSWB—Down Convert Word to Byte 5-560 VPMULTISHIFTQB – Select Packed Unaligned Bytes from Quadword Source 5-408 VPMULTISHIFTQB—Select Packed Unaligned Bytes From Quadword Sources 5-564

VPOPCNT—Return the Count of Number of Bits Set to 1 in BYTE/WORD/DWORD/QWORD 5-566 VPROLD/VPROLVD/VPROLQ/VPROLVQ—Bit Rotate Left 5-569 VPRORD/VPRORVD/VPRORQ/VPRORVQ—Bit Rotate Right 5-573 VPSCATTERDD/VPSCATTERDQ/VPSCATTERQD/VPSCATTERQQ—Scatter Packed Dword, Packed Qword with Signed Dword, Signed Qword Indices 5-577

VPSHLD—Concatenate and Shift Packed Data Left Logical 5-581 VPSHLDV—Concatenate and Variable Shift Packed Data Left Logical 5-584

VPSHRD—Concatenate and Shift Packed Data Right Logical 5-587 VPSHRDV—Concatenate and Variable Shift Packed Data Right Logical 5-590

VPSHUFBITQMB—Shuffle Bits From Quadword Elements Using Byte Indexes Into Mask 5-593

VPSLLVW/VPSLLVD/VPSLLVQ—Variable Bit Shift Left Logical 5-594

VPSRAVW/VPSRAVD/VPSRAVQ—Variable Bit Shift Right Arithmetic 5-599 VPSRLVW/VPSRLVD/VPSRLVQ—Variable Bit Shift Right Logical 5-604

VPTERNLOGD/VPTERNLOGQ—Bitwise Ternary Logic 5-609 VPTESTMB/VPTESTMW/VPTESTMD/VPTESTMQ—Logical AND and Set Mask 5-612

VPTESTNMB/W/D/Q—Logical NAND and Set 5-615

VRANGEPD—Range Restriction Calculation for Packed Pairs of Float64 Values 5-618

VRANGESD—Range Restriction Calculation From a Pair of Scalar Float64 Values 5-625

VRANGESS—Range Restriction Calculation From a Pair of Scalar Float32 Values 5-628

VRCP14PD—Compute Approximate Reciprocals of Packed Float64 Values 5-631

VRCP14PS—Compute Approximate Reciprocals of Packed Float32 Values 5-635

VRCP14SD—Compute Approximate Reciprocal of Scalar Float64 Value 5-633

VRCP14SS—Compute Approximate Reciprocal of Scalar Float32 Value 5-637

VRCP28SD—Approximation to the Reciprocal of Scalar Double-Precision Floating-Point Value with Less Than 2^-28 Relative Error 8-22

Vol. 2D INDEX-13

**INDEX**

VRCP28SS—Approximation to the Reciprocal of Scalar Single-Precision Floating-Point Value with Less Than 2^-28 Relative Error

8-26

VRCPPH—Compute Reciprocals of Packed FP16 Values 5-639 VRCPSH—Compute Reciprocal of Scalar FP16 Value 5-641 VREDUCEPD—Perform Reduction Transformation on Packed Float64 Values 5-642 VREDUCEPH—Perform Reduction Transformation on Packed FP16 Values 5-645 VREDUCEPS—Perform Reduction Transformation on Packed Float32 Values 5-652 VREDUCESD—Perform a Reduction Transformation on a Scalar Float64 Value 5-648 VREDUCESH—Perform Reduction Transformation on Scalar FP16 Value 5-650 VREDUCESS—Perform a Reduction Transformation on a Scalar Float32 Value 5-654 VRNDSCALEPD—Round Packed Float64 Values to Include a Given Number of Fraction Bits 5-656 VRNDSCALEPH—Round Packed FP16 Values to Include a Given Number of Fraction Bits 5-659 VRNDSCALEPS—Round Packed Float32 Values to Include a Given Number of Fraction Bits 5-662 VRNDSCALESD—Round Scalar Float64 Value to Include a Given Number of Fraction Bits 5-665 VRNDSCALESH—Round Scalar FP16 Value to Include a Given Number of Fraction Bits 5-667 VRNDSCALESS—Round Scalar Float32 Value to Include a Given Number of Fraction Bits 5-669 VRSQRT14PD—Compute Approximate Reciprocals of Square Roots of Packed Float64 Values 5-671

VRSQRT14PS—Compute Approximate Reciprocals of Square Roots of Packed Float32 Values 5-675 VRSQRT14SD—Compute Approximate Reciprocal of Square Root of Scalar Float64 Value 5-673 VRSQRT14SS—Compute Approximate Reciprocal of Square Root of Scalar Float32 Value 5-677

VRSQRT28PS—Approximation to the Reciprocal Square Root of Packed Single-Precision Floating-Point Values with Less Than 2^-28 Relative Error 8-32

VRSQRT28SD—Approximation to the Reciprocal Square Root of Scalar Double-Precision Floating-Point Value with Less Than 2^-28 Relative Error 8-30

VRSQRT28SS—Approximation to the Reciprocal Square Root of Scalar Single-Precision Floating-Point Value with Less Than 2^-28 Relative Error 8-34

VRSQRTPH—Compute Reciprocals of Square Roots of Packed FP16 Values 5-679

VRSQRTSH—Compute Approximate Reciprocal of Square Root of Scalar FP16 Value 5-681

VSCALEFPD—Scale Packed Float64 Values With Float64 Values 5-682

VSCALEFPH—Scale Packed FP16 Values with FP16 Values 5-685 VSCALEFPS—Scale Packed Float32 Values With Float32 Values 5-687 VSCALEFSD—Scale Scalar Float64 Values With Float64 Values 5-690

VSCALEFSH—Scale Scalar FP16 Values with FP16 Values 5-692 VSCALEFSS—Scale Scalar Float32 Value With Float32 Value

5-694 VSCATTERDPS/VSCATTERDPD/VSCATTERQPS/VSCATTERQPD—Scatter Packed Single, Packed Double with Signed Dword and Qword Indices 5-696 VSCATTERPF1DPS/VSCATTERPF1QPS/VSCATTERPF1DPD/VSCA TTERPF1QPD—Sparse Prefetch Packed SP/DP Data Values with Signed Dword, Signed Qword Indices Using T1 Hint with Intent to Write 8-38 VSHUFF32x4/VSHUFF64x2/VSHUFI32x4/VSHUFI64x2—Shuffle Packed Values at 128-Bit Granularity 5-700 VSQRTPH—Compute Square Root of Packed FP16 Values 5-705 VSQRTSH—Compute Square Root of Scalar FP16 Value 5-707 VSUBPH—Subtract Packed FP16 Values 5-708 VSUBSH—Subtract Scalar FP16 Value 5-710 VTESTPD/VTESTPS—Packed Bit Test 5-711 VUCOMISH—Unordered Compare Scalar FP16 Values and Set EFLAGS 5-714 VZEROALL—Zero XMM, YMM, and ZMM Registers 5-715 VZEROUPPER—Zero Upper Bits of YMM and ZMM Registers 5-716 W

WAIT/FWAIT instructions 6-2 GETSEC 7-4 WBINVD instruction 6-3, 6-5 WBINVD/INVD bit 3-218 Write-back and invalidate caches 6-3 WRMSR instruction 6-9 CPUID flag 3-244 X

x87 FPU checking for pending x87 FPU exceptions 6-2 constants 3-403 initialization 3-394 instruction opcodes A-20 x87 FPU control word loading 3-405, 3-407 RC field 3-396, 3-403, 3-435 restoring 3-422 saving 3-424, 3-439 storing 3-437 x87 FPU data pointer 3-407, 3-422, 3-424, 3-439 x87 FPU instruction pointer 3-407, 3-422, 3-424, 3-439 x87 FPU last opcode 3-407, 3-422, 3-424, 3-439 x87 FPU status word condition code flags 3-373, 3-389, 3-449, 3-451, 3-454 loading 3-407 restoring 3-422 saving 3-424, 3-439, 3-441 TOP field 3-393 x87 FPU flags affected by instructions 3-14 x87 FPU tag word 3-407, 3-422, 3-424, 3-439 XABORT - Transaction Abort 6-17 XADD instruction 3-609, 6-23 XCHG instruction 3-609, 6-28 XCR0 6-66, 6-67 XEND - Transaction End 6-30 XGETBV 6-32, 6-45, 6-50, B-41 XLAB instruction 6-34 XLAT instruction 6-34 XOR instruction 3-609, 6-36

INDEX-14 Vol. 2D

**INDEX**

XORPD- Bitwise Logical XOR of Packed Double Precision Floating-Point Values 6-38 XORPS- Bitwise Logical XOR of Packed Single Precision Floating-Point Values 5-716, 6-41 XRSTOR B-41 XSAVE 6-32, 6-48, 6-49, 6-52, 6-53, 6-54, 6-55, 6-56, 6-57, 6-58, 6-59, 6-60, 6-62, 6-63, 6-65, 6-66, 6-67, B-41 XSETBV 6-60, 6-66, B-41 XTEST - Test If In Transactional Execution 6-69 Z ZF (zero) flag, EFLAGS register 3-207, 3-581, 3-614, 3-617, 4-561, 5-155

Vol. 2D INDEX-15

**INDEX**

Vol. 2D

INDEX-16
