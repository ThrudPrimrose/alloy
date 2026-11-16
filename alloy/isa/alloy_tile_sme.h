/* Alloy's tile functions on SME (alloy/isa/tile.py): C (m x n, f32, row-major) += A x B with A given transposed
 * (at: k x m row-major, each column of A contiguous: streaming mode has no gather) and B k x n row-major. Each block of
 * SVL/32 x SVL/32 elements of C is loaded into the ZA tile za0.s, receives k outer products (FMOPA) of a column of A
 * and a row of B, and is stored back; predicates cover the edges. No evaluated CPU has SME (Grace is SVE2 without it):
 * the function is checked under qemu (-cpu max,sme=on). Build with -march=armv9-a+sme (clang 18 or later, gcc 14). */
#ifndef ALLOY_TILE_SME_H
#define ALLOY_TILE_SME_H
#include <arm_sme.h>
#include <stdint.h>

__arm_new("za") __arm_locally_streaming static void alloy_mma_sme_f32(int64_t m, int64_t n, int64_t k,
                                                                      const float *at, int64_t ldat, const float *b,
                                                                      int64_t ldb, float *c, int64_t ldc) {
  const int64_t vl = (int64_t)svcntw();
  for (int64_t i0 = 0; i0 < m; i0 += vl)
    for (int64_t j0 = 0; j0 < n; j0 += vl) {
      const svbool_t rows = svwhilelt_b32_s64(i0, m), cols = svwhilelt_b32_s64(j0, n);
      const int64_t count = m - i0 < vl ? m - i0 : vl;
      for (int64_t r = 0; r < count; ++r) svld1_hor_za32(0, (uint32_t)r, cols, c + (i0 + r) * ldc + j0);
      for (int64_t p = 0; p < k; ++p)
        svmopa_za32_f32_m(0, rows, cols, svld1(rows, at + p * ldat + i0), svld1(cols, b + p * ldb + j0));
      for (int64_t r = 0; r < count; ++r) svst1_hor_za32(0, (uint32_t)r, cols, c + (i0 + r) * ldc + j0);
    }
}

#endif
