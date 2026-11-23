/* Alloy's tile functions on SME (alloy/isa/tile.py): C (m x n, f32 or f64, row-major) += A x B with A given transposed
 * (at: k x m row-major, each column of A contiguous: streaming mode has no gather) and B k x n row-major. Each block of
 * SVL/32 x SVL/32 elements of C is loaded into the ZA tile za0.s (f32) or za0.d (f64, SME_F64F64), receives k outer products (FMOPA) of a column of A
 * and a row of B, and is stored back; predicates cover the edges. No evaluated CPU has SME (Grace is SVE2 without it):
 * the function is checked under qemu (-cpu max,sme=on). Build with -march=armv9-a+sme+sme-f64f64 (clang 18 or later, gcc 14). */
#ifndef ALLOY_TILE_SME_H
#define ALLOY_TILE_SME_H
#include <arm_sme.h>
#include <stdint.h>

#define ALLOY_MMA_SME(NAME, T, BITS, COUNT)                                                                    \
  __arm_new("za") __arm_locally_streaming static void NAME(int64_t m, int64_t n, int64_t k, const T *at,         \
                                                           int64_t ldat, const T *b, int64_t ldb, T *c, int64_t ldc) { \
    const int64_t vl = (int64_t)COUNT();                                                                           \
    for (int64_t i0 = 0; i0 < m; i0 += vl)                                                                         \
      for (int64_t j0 = 0; j0 < n; j0 += vl) {                                                                     \
        const svbool_t rows = svwhilelt_b##BITS##_s64(i0, m), cols = svwhilelt_b##BITS##_s64(j0, n);               \
        const int64_t count = m - i0 < vl ? m - i0 : vl;                                                           \
        for (int64_t r = 0; r < count; ++r) svld1_hor_za##BITS(0, (uint32_t)r, cols, c + (i0 + r) * ldc + j0);     \
        for (int64_t p = 0; p < k; ++p)                                                                            \
          svmopa_za##BITS##_f##BITS##_m(0, rows, cols, svld1(rows, at + p * ldat + i0), svld1(cols, b + p * ldb + j0)); \
        for (int64_t r = 0; r < count; ++r) svst1_hor_za##BITS(0, (uint32_t)r, cols, c + (i0 + r) * ldc + j0);     \
      }                                                                                                            \
  }

ALLOY_MMA_SME(alloy_mma_sme_f32, float, 32, svcntw)  // alloy-only: f32
ALLOY_MMA_SME(alloy_mma_sme_f64, double, 64, svcntd)  // alloy-only: f64

#endif
