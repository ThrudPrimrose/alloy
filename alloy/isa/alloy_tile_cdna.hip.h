// Alloy's tile functions on CDNA (gfx90a: MI250X, gfx942: MI300A), alloy/isa/tile.py: row-major tiles loaded into LDS
// with an XOR swizzle (16-byte chunk c of row r at slot c ^ (r % 8), no padding), read with ds_read_b128, and
// multiplied with a 32x32 MFMA into f32 accumulators. A is M x K row-major; B is given as N x K row-major (B
// transposed, K contiguous); C is M x N row-major f32, read and written: C = A x B + C. A K block is 128 bytes of a row
// for every input type: 64 halves (f16, bf16) or 128 bytes (e4m3, e5m2: the FNUZ formats of gfx942, which gfx90a
// lacks). Facts and sources: alloy-workspace notes/isa-research/tensor.md, sections 6 to 8.
#pragma once
// alloy-only: file
// Blocks between "// alloy-only: <tokens>" and "// alloy-end" belong to the named types only; tile.py inlines this
// file trimmed to what one answer uses.
// alloy-end
#include <hip/hip_runtime.h>

typedef _Float16 alloy_half4 __attribute__((ext_vector_type(4)));
typedef _Float16 alloy_half8 __attribute__((ext_vector_type(8)));
typedef short alloy_short4 __attribute__((ext_vector_type(4)));
typedef long alloy_long2 __attribute__((ext_vector_type(2)));  // one 16-byte chunk: 8 bytes lo, 8 bytes hi
typedef float alloy_floatx16 __attribute__((ext_vector_type(16)));
typedef double alloy_doublex4 __attribute__((ext_vector_type(4)));

// The input element types of the tile kernels, as their template argument.
enum alloy_elem { ALLOY_F16, ALLOY_BF16, ALLOY_E4M3, ALLOY_E5M2 };

// One 32x32 MFMA on 8 bytes of A and of B per lane: K = 8 for the 2-byte types, K = 16 for the 1-byte types.
// alloy-only: mma
template <int E>
__device__ __forceinline__ alloy_floatx16 alloy_mfma(long a, long b, alloy_floatx16 acc) {
// alloy-only: f16
  if constexpr (E == ALLOY_F16)
    return __builtin_amdgcn_mfma_f32_32x32x8f16(__builtin_bit_cast(alloy_half4, a), __builtin_bit_cast(alloy_half4, b),
                                                acc, 0, 0, 0);
// alloy-end
// alloy-only: bf16
  if constexpr (E == ALLOY_BF16)
    return __builtin_amdgcn_mfma_f32_32x32x8bf16_1k(__builtin_bit_cast(alloy_short4, a),
                                                    __builtin_bit_cast(alloy_short4, b), acc, 0, 0, 0);
// alloy-end
#if !defined(__gfx90a__)  // gfx90a has no FP8 MFMA; tile.py never builds an FP8 kernel for it
// alloy-only: e4m3
  if constexpr (E == ALLOY_E4M3) return __builtin_amdgcn_mfma_f32_32x32x16_fp8_fp8(a, b, acc, 0, 0, 0);
// alloy-end
// alloy-only: e5m2
  if constexpr (E == ALLOY_E5M2) return __builtin_amdgcn_mfma_f32_32x32x16_bf8_bf8(a, b, acc, 0, 0, 0);
// alloy-end
#endif
  return acc;
}
// alloy-end

// alloy-only: mma
// One 64 x 64 block of C per 256 threads (four wave64, each a 32 x 32 sub-tile); K in elements, a multiple of the
// K block (128 bytes of a row).
template <int E>
__global__ __launch_bounds__(256) void alloy_gemm_64x64(const void* __restrict__ A, const void* __restrict__ Bt,
                                                       float* __restrict__ C, int N, int K) {
  constexpr int bytes = E <= ALLOY_BF16 ? 2 : 1;
  constexpr int block = 128 / bytes;  // elements of K per block of 128 bytes
  // 64 rows x 8 chunks of 16 B; chunk c of row r is stored at slot c ^ (r % 8) (XOR swizzle, no padding).
  __shared__ alloy_long2 sA[64 * 8];
  __shared__ alloy_long2 sB[64 * 8];
  const char* a = static_cast<const char*>(A);
  const char* b = static_cast<const char*>(Bt);
  const long row_bytes = static_cast<long>(K) * bytes;
  const int tid = threadIdx.x, wave = tid / 64, lane = tid % 64;
  const int wm = wave / 2, wn = wave % 2, m0 = blockIdx.y * 64, n0 = blockIdx.x * 64;
  alloy_floatx16 acc;
#pragma unroll
  for (int g = 0; g < 16; ++g)  // the accumulators start as C: D = A x B + C
    acc[g] = C[(m0 + 32 * wm + 8 * (g / 4) + 4 * (lane / 32) + g % 4) * N + n0 + 32 * wn + lane % 32];
  for (int k0 = 0; k0 < K; k0 += block) {
#pragma unroll
    for (int it = 0; it < 2; ++it) {  // 512 chunks per operand / 256 threads
      const int idx = tid + 256 * it, r = idx / 8, c = idx % 8;
      const long at = static_cast<long>(k0) * bytes + 16 * c;
      sA[r * 8 + (c ^ (r & 7))] = *reinterpret_cast<const alloy_long2*>(a + (m0 + r) * row_bytes + at);  // global_load_dwordx4
      sB[r * 8 + (c ^ (r & 7))] = *reinterpret_cast<const alloy_long2*>(b + (n0 + r) * row_bytes + at);  // ds_write_b128
    }
    __syncthreads();
    const int i = lane % 32, h = lane / 32, ra = 32 * wm + i, rb = 32 * wn + i;
#pragma unroll
    for (int p = 0; p < 4; ++p) {  // 4 x ds_read_b128 per operand, 8 MFMAs cover the K block
      const int ch = 2 * p + h;
      const alloy_long2 ca = sA[ra * 8 + (ch ^ (ra & 7))];
      const alloy_long2 cb = sB[rb * 8 + (ch ^ (rb & 7))];
      // Same K permutation for A and B: lane half h feeds the first 8 bytes of chunk 2p + h, then the last 8.
      acc = alloy_mfma<E>(ca.x, cb.x, acc);
      acc = alloy_mfma<E>(ca.y, cb.y, acc);
    }
    __syncthreads();
  }
  // D layout of a 32x32 MFMA with f32 accumulators: acc[g] = D[8*(g/4) + 4*(lane/32) + g%4][lane%32].
#pragma unroll
  for (int g = 0; g < 16; ++g) {
    const int row = m0 + 32 * wm + 8 * (g / 4) + 4 * (lane / 32) + g % 4;
    const int col = n0 + 32 * wn + lane % 32;
    C[row * N + col] = acc[g];
  }
}
// alloy-end

// alloy-only: f64
// f64 on CDNA (gfx90a, gfx942): one 64 x 64 block of C per 256 threads, each wave64 a 32 x 32 sub-tile of 2 x 2
// v_mfma_f64_16x16x4f64 tiles accumulating in f64. A K block is 16 doubles (128 bytes of a row), staged in LDS with the
// XOR swizzle of the other types. In a 16x16x4 MFMA, lane l feeds A[l % 16][k + l / 16] and B[k + l / 16][l % 16], and
// holds D[4 * (l / 16) + i][l % 16] in accumulator i.
__global__ __launch_bounds__(256) void alloy_gemm_64x64_f64(const double* __restrict__ A,
                                                           const double* __restrict__ Bt, double* __restrict__ C,
                                                           int N, int K) {
  __shared__ alloy_long2 sA[64 * 8];
  __shared__ alloy_long2 sB[64 * 8];
  const char* a = reinterpret_cast<const char*>(A);
  const char* b = reinterpret_cast<const char*>(Bt);
  const long row_bytes = static_cast<long>(K) * 8;
  const int tid = threadIdx.x, wave = tid / 64, lane = tid % 64, r16 = lane % 16, q = lane / 16;
  const int wm = wave / 2, wn = wave % 2, m0 = blockIdx.y * 64, n0 = blockIdx.x * 64;
  alloy_doublex4 acc[2][2];
#pragma unroll
  for (int ti = 0; ti < 2; ++ti)
#pragma unroll
    for (int tj = 0; tj < 2; ++tj)
#pragma unroll
      for (int i = 0; i < 4; ++i)  // the accumulators start as C: D = A x B + C
        acc[ti][tj][i] = C[(m0 + 32 * wm + 16 * ti + 4 * q + i) * N + n0 + 32 * wn + 16 * tj + r16];
  for (int k0 = 0; k0 < K; k0 += 16) {
#pragma unroll
    for (int it = 0; it < 2; ++it) {  // 512 chunks of 16 bytes per operand / 256 threads
      const int idx = tid + 256 * it, r = idx / 8, c = idx % 8;
      const long at = static_cast<long>(k0) * 8 + 16 * c;
      sA[r * 8 + (c ^ (r & 7))] = *reinterpret_cast<const alloy_long2*>(a + (m0 + r) * row_bytes + at);
      sB[r * 8 + (c ^ (r & 7))] = *reinterpret_cast<const alloy_long2*>(b + (n0 + r) * row_bytes + at);
    }
    __syncthreads();
#pragma unroll
    for (int kk = 0; kk < 16; kk += 4) {  // 4 steps of K = 4 cover the block
      const int k = kk + q, c = k / 2, half = k % 2;
      double av[2], bv[2];
#pragma unroll
      for (int t = 0; t < 2; ++t) {
        const int ra = 32 * wm + 16 * t + r16, rb = 32 * wn + 16 * t + r16;
        av[t] = __builtin_bit_cast(double, sA[ra * 8 + (c ^ (ra & 7))][half]);
        bv[t] = __builtin_bit_cast(double, sB[rb * 8 + (c ^ (rb & 7))][half]);
      }
#pragma unroll
      for (int ti = 0; ti < 2; ++ti)
#pragma unroll
        for (int tj = 0; tj < 2; ++tj)
          acc[ti][tj] = __builtin_amdgcn_mfma_f64_16x16x4f64(av[ti], bv[tj], acc[ti][tj], 0, 0, 0);
    }
    __syncthreads();
  }
#pragma unroll
  for (int ti = 0; ti < 2; ++ti)
#pragma unroll
    for (int tj = 0; tj < 2; ++tj)
#pragma unroll
      for (int i = 0; i < 4; ++i)
        C[(m0 + 32 * wm + 16 * ti + 4 * q + i) * N + n0 + 32 * wn + 16 * tj + r16] = acc[ti][tj][i];
}
// alloy-end
