/* Alloy's tile functions on a CPU (alloy/isa/tile.py): C += A x B on row-major tiles, A m x k (leading dimension
 * lda), B k x n (ldb), C m x n (ldc). The evaluated CPUs have neither AMX nor SME, so this is the fallback: a step
 * updates four rows of C from one row of B, so each row of B is read once per four rows, and the compiler vectorizes
 * the n loop (-O3 -march=native). No swizzle. */
#ifndef ALLOY_TILE_CPU_H
#define ALLOY_TILE_CPU_H

#define ALLOY_MMA(NAME, TA, TC)                                                                            \
  static inline void NAME(int m, int n, int k, const TA *restrict a, int lda, const TA *restrict b, int ldb, \
                          TC *restrict c, int ldc) {                                                        \
    int i = 0;                                                                                              \
    for (; i + 4 <= m; i += 4) {                                                                            \
      for (int p = 0; p < k; ++p) {                                                                         \
        TC a0 = a[(i + 0) * lda + p], a1 = a[(i + 1) * lda + p];                                            \
        TC a2 = a[(i + 2) * lda + p], a3 = a[(i + 3) * lda + p];                                            \
        const TA *restrict row = b + p * ldb;                                                               \
        _Pragma("omp simd") for (int j = 0; j < n; ++j) {                                                   \
          TC bj = row[j];                                                                                   \
          c[(i + 0) * ldc + j] += a0 * bj;                                                                  \
          c[(i + 1) * ldc + j] += a1 * bj;                                                                  \
          c[(i + 2) * ldc + j] += a2 * bj;                                                                  \
          c[(i + 3) * ldc + j] += a3 * bj;                                                                  \
        }                                                                                                   \
      }                                                                                                     \
    }                                                                                                       \
    for (; i < m; ++i)                                                                                      \
      for (int p = 0; p < k; ++p) {                                                                         \
        TC ai = a[i * lda + p];                                                                             \
        _Pragma("omp simd") for (int j = 0; j < n; ++j) c[i * ldc + j] += ai * (TC)b[p * ldb + j];          \
      }                                                                                                     \
  }

ALLOY_MMA(alloy_mma_f32_f32, float, float)
ALLOY_MMA(alloy_mma_f64_f64, double, double)
ALLOY_MMA(alloy_mma_f32_f64, float, double)

#endif
