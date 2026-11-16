// Alloy's tile functions on gfx942 (MI300A), alloy/isa/tile.py: row-major f16 tiles loaded into LDS with an XOR
// swizzle (chunk c of row r at slot c ^ (r % 8), no padding), read with ds_read_b128, and multiplied with
// v_mfma_f32_32x32x8_f16 into f32 accumulators. A is M x K row-major; B is given as N x K row-major (B transposed,
// K contiguous); C is M x N row-major f32. Facts and sources: alloy-workspace notes/isa-research/tensor.md, sections
// 6 to 8.
#pragma once
#include <hip/hip_runtime.h>

typedef _Float16 alloy_half4 __attribute__((ext_vector_type(4)));
typedef _Float16 alloy_half8 __attribute__((ext_vector_type(8)));
typedef float alloy_floatx16 __attribute__((ext_vector_type(16)));

__global__ __launch_bounds__(256) void alloy_gemm_64x64x64(const _Float16* __restrict__ A, const _Float16* __restrict__ Bt,
                                                float* __restrict__ C, int N, int K) {
  // 64 rows x 8 chunks of 16 B; chunk c of row r is stored at slot c ^ (r % 8) (XOR swizzle, no padding).
  __shared__ alloy_half8 sA[64 * 8];
  __shared__ alloy_half8 sB[64 * 8];
  const int tid = threadIdx.x, wave = tid / 64, lane = tid % 64;
  const int wm = wave / 2, wn = wave % 2, m0 = blockIdx.y * 64, n0 = blockIdx.x * 64;
  alloy_floatx16 acc = {};
  for (int k0 = 0; k0 < K; k0 += 64) {
#pragma unroll
    for (int it = 0; it < 2; ++it) {          // 512 chunks per operand / 256 threads
      const int idx = tid + 256 * it, r = idx / 8, c = idx % 8;
      sA[r * 8 + (c ^ (r & 7))] = *reinterpret_cast<const alloy_half8*>(A + (m0 + r) * K + k0 + 8 * c);   // global_load_dwordx4
      sB[r * 8 + (c ^ (r & 7))] = *reinterpret_cast<const alloy_half8*>(Bt + (n0 + r) * K + k0 + 8 * c);  // ds_write_b128
    }
    __syncthreads();
    const int i = lane % 32, h = lane / 32, ra = 32 * wm + i, rb = 32 * wn + i;
#pragma unroll
    for (int p = 0; p < 4; ++p) {             // 4 x ds_read_b128 per operand, 8 MFMAs cover K = 64
      const int ch = 2 * p + h;
      const alloy_half8 a = sA[ra * 8 + (ch ^ (ra & 7))];
      const alloy_half8 b = sB[rb * 8 + (ch ^ (rb & 7))];
      // Same K permutation for A and B: lane half h feeds k = 16p + 8h + {0..3} (lo) then {4..7} (hi).
      acc = __builtin_amdgcn_mfma_f32_32x32x8f16(a.lo, b.lo, acc, 0, 0, 0);
      acc = __builtin_amdgcn_mfma_f32_32x32x8f16(a.hi, b.hi, acc, 0, 0, 0);
    }
    __syncthreads();
  }
  // D layout of v_mfma_f32_32x32x8_f16: acc[g] = D[8*(g/4) + 4*(lane/32) + g%4][lane%32].
#pragma unroll
  for (int g = 0; g < 16; ++g) {
    const int row = m0 + 32 * wm + 8 * (g / 4) + 4 * (lane / 32) + g % 4;
    const int col = n0 + 32 * wn + lane % 32;
    C[row * N + col] = acc[g];
  }
}
