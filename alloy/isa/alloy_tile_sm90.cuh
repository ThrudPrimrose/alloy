// Alloy's tile functions on sm_90 (GH200), alloy/isa/tile.py: TMA loads into 128B-swizzled shared memory completed
// through an mbarrier, and wgmma on f16 tiles with an f32 accumulator. Build for sm_90a
// (-gencode arch=compute_90a,code=sm_90a): plain sm_90 rejects wgmma. A is M x K row-major; B is given as N x K
// row-major (each column of B contiguous, K-major, the layout wgmma reads without a transpose); C is M x N row-major
// f32. Facts and sources: alloy-workspace notes/isa-research/tensor.md, sections 1, 3, and 5.
#pragma once
#include <cuda.h>
#include <cuda_fp16.h>
#include <cstdint>

constexpr int ALLOY_BM = 64, ALLOY_BN = 64, ALLOY_BK = 64;

__device__ __forceinline__ uint32_t alloy_smem_u32(const void* p) {
  return static_cast<uint32_t>(__cvta_generic_to_shared(p));
}

// K-major, 128B-swizzled operand tile whose rows are 128 bytes (64 halves), 1024B-aligned.
__device__ __forceinline__ uint64_t alloy_desc_kmajor_sw128(uint32_t saddr) {
  uint64_t d = 0;
  d |= uint64_t((saddr & 0x3FFFF) >> 4);   // [13:0]  start address >> 4
  d |= uint64_t(1) << 16;                    // [29:16] LBO (unused for swizzled K-major, "assumed 1")
  d |= uint64_t(1024 >> 4) << 32;            // [45:32] SBO = 8 rows * 128 B = 1024 B
  d |= uint64_t(1) << 62;                    // [63:62] 1 = 128B swizzle
  return d;
}

__device__ __forceinline__ void alloy_mbar_init(uint64_t* bar, uint32_t count) {
  asm volatile("mbarrier.init.shared::cta.b64 [%0], %1;" :: "r"(alloy_smem_u32(bar)), "r"(count) : "memory");
}
__device__ __forceinline__ void alloy_mbar_arrive_expect_tx(uint64_t* bar, uint32_t bytes) {
  asm volatile("mbarrier.arrive.expect_tx.shared::cta.b64 _, [%0], %1;" :: "r"(alloy_smem_u32(bar)), "r"(bytes) : "memory");
}
__device__ __forceinline__ void alloy_mbar_wait(uint64_t* bar, uint32_t phase) {
  asm volatile(
      "{\n .reg .pred p;\n"
      "WAIT_%=:\n"
      " mbarrier.try_wait.parity.shared::cta.b64 p, [%0], %1;\n"
      " @!p bra WAIT_%=;\n}" :: "r"(alloy_smem_u32(bar)), "r"(phase) : "memory");
}
__device__ __forceinline__ void alloy_tma_load_2d(void* dst, const CUtensorMap* tm, uint64_t* bar, int c0, int c1) {
  asm volatile(
      "cp.async.bulk.tensor.2d.shared::cluster.global.mbarrier::complete_tx::bytes [%0], [%1, {%3, %4}], [%2];"
      :: "r"(alloy_smem_u32(dst)), "l"(reinterpret_cast<uint64_t>(tm)), "r"(alloy_smem_u32(bar)), "r"(c0), "r"(c1) : "memory");
}

#define D8(i) "+f"(d[i]), "+f"(d[i+1]), "+f"(d[i+2]), "+f"(d[i+3]), "+f"(d[i+4]), "+f"(d[i+5]), "+f"(d[i+6]), "+f"(d[i+7])
__device__ __forceinline__ void alloy_wgmma_m64n64k16_f32_f16(float (&d)[32], uint64_t da, uint64_t db) {
  asm volatile(
      "{\n .reg .pred p;\n setp.ne.b32 p, %34, 0;\n"
      "wgmma.mma_async.sync.aligned.m64n64k16.f32.f16.f16 "
      "{%0,%1,%2,%3,%4,%5,%6,%7,%8,%9,%10,%11,%12,%13,%14,%15,"
      "%16,%17,%18,%19,%20,%21,%22,%23,%24,%25,%26,%27,%28,%29,%30,%31},"
      " %32, %33, p, 1, 1, 0, 0;\n}"
      : D8(0), D8(8), D8(16), D8(24)
      : "l"(da), "l"(db), "r"(1));
}

__device__ __forceinline__ void alloy_wgmma_m64n128k16_f32_f16(float (&d)[64], uint64_t da, uint64_t db) {
  asm volatile(
      "{\n .reg .pred p;\n setp.ne.b32 p, %66, 0;\n"
      "wgmma.mma_async.sync.aligned.m64n128k16.f32.f16.f16 {%0,%1,%2,%3,%4,%5,%6,%7,%8,%9,%10,%11,%12,%13,%14,%15,%16,%17,%18,%19,%20,%21,%22,%23,%24,%25,%26,%27,%28,%29,%30,%31,%32,%33,%34,%35,%36,%37,%38,%39,%40,%41,%42,%43,%44,%45,%46,%47,%48,%49,%50,%51,%52,%53,%54,%55,%56,%57,%58,%59,%60,%61,%62,%63}, %64, %65, p, 1, 1, 0, 0;\n}"
      : "+f"(d[0]), "+f"(d[1]), "+f"(d[2]), "+f"(d[3]), "+f"(d[4]), "+f"(d[5]), "+f"(d[6]), "+f"(d[7]), "+f"(d[8]), "+f"(d[9]), "+f"(d[10]), "+f"(d[11]), "+f"(d[12]), "+f"(d[13]), "+f"(d[14]), "+f"(d[15]), "+f"(d[16]), "+f"(d[17]), "+f"(d[18]), "+f"(d[19]), "+f"(d[20]), "+f"(d[21]), "+f"(d[22]), "+f"(d[23]), "+f"(d[24]), "+f"(d[25]), "+f"(d[26]), "+f"(d[27]), "+f"(d[28]), "+f"(d[29]), "+f"(d[30]), "+f"(d[31]), "+f"(d[32]), "+f"(d[33]), "+f"(d[34]), "+f"(d[35]), "+f"(d[36]), "+f"(d[37]), "+f"(d[38]), "+f"(d[39]), "+f"(d[40]), "+f"(d[41]), "+f"(d[42]), "+f"(d[43]), "+f"(d[44]), "+f"(d[45]), "+f"(d[46]), "+f"(d[47]), "+f"(d[48]), "+f"(d[49]), "+f"(d[50]), "+f"(d[51]), "+f"(d[52]), "+f"(d[53]), "+f"(d[54]), "+f"(d[55]), "+f"(d[56]), "+f"(d[57]), "+f"(d[58]), "+f"(d[59]), "+f"(d[60]), "+f"(d[61]), "+f"(d[62]), "+f"(d[63])
      : "l"(da), "l"(db), "r"(1));
}

__global__ void __launch_bounds__(128) alloy_gemm_64x64x64(const __grid_constant__ CUtensorMap tmA,
                                                     const __grid_constant__ CUtensorMap tmB,
                                                     float* __restrict__ C, int N, int K) {
  __shared__ alignas(1024) __half sA[ALLOY_BM * ALLOY_BK];
  __shared__ alignas(1024) __half sB[ALLOY_BN * ALLOY_BK];
  __shared__ alignas(8) uint64_t bar;
  const int tid = threadIdx.x, m0 = blockIdx.y * ALLOY_BM, n0 = blockIdx.x * ALLOY_BN;
  float d[32];
#pragma unroll
  for (int i = 0; i < 32; ++i) d[i] = 0.f;
  if (tid == 0) {
    alloy_mbar_init(&bar, 1);
    asm volatile("fence.proxy.async.shared::cta;" ::: "memory");  // make init visible to the async proxy
  }
  __syncthreads();
  uint32_t phase = 0;
  for (int k0 = 0; k0 < K; k0 += ALLOY_BK) {
    if (tid == 0) {
      alloy_mbar_arrive_expect_tx(&bar, (ALLOY_BM + ALLOY_BN) * ALLOY_BK * sizeof(__half));
      alloy_tma_load_2d(sA, &tmA, &bar, k0, m0);   // coords innermost-first: {k, m}
      alloy_tma_load_2d(sB, &tmB, &bar, k0, n0);   // {k, n}
    }
    alloy_mbar_wait(&bar, phase);
    phase ^= 1;
    const uint64_t da = alloy_desc_kmajor_sw128(alloy_smem_u32(sA)), db = alloy_desc_kmajor_sw128(alloy_smem_u32(sB));
    asm volatile("wgmma.fence.sync.aligned;" ::: "memory");
#pragma unroll
    for (int kk = 0; kk < ALLOY_BK / 16; ++kk)             // 4 x m64n64k16 cover K = 64
      alloy_wgmma_m64n64k16_f32_f16(d, da + (kk * 32 >> 4), db + (kk * 32 >> 4));  // +32 B per k-step
    asm volatile("wgmma.commit_group.sync.aligned;" ::: "memory");
    asm volatile("wgmma.wait_group.sync.aligned 0;" ::: "memory");
    __syncthreads();  // single stage: all reads of sA/sB done before the next TMA overwrites them
  }
  const int warp = tid / 32, lane = tid % 32;
  const int r = m0 + 16 * warp + lane / 4;
#pragma unroll
  for (int i = 0; i < ALLOY_BN / 8; ++i) {
    const int c = n0 + 8 * i + 2 * (lane % 4);
    *reinterpret_cast<float2*>(&C[r * N + c]) = make_float2(d[4 * i + 0], d[4 * i + 1]);
    *reinterpret_cast<float2*>(&C[(r + 8) * N + c]) = make_float2(d[4 * i + 2], d[4 * i + 3]);
  }
}


// 128x128 tile, ALLOY_BK=64, two consumer warpgroups (256 threads); warpgroup g computes rows [64g, 64g+64).
__global__ void __launch_bounds__(256) alloy_gemm_128x128x64(const __grid_constant__ CUtensorMap tmA,
                                                       const __grid_constant__ CUtensorMap tmB,
                                                       float* __restrict__ C, int N, int K) {
  __shared__ alignas(1024) __half sA[128 * ALLOY_BK];
  __shared__ alignas(1024) __half sB[128 * ALLOY_BK];
  __shared__ alignas(8) uint64_t bar;
  const int tid = threadIdx.x, wg = tid / 128, m0 = blockIdx.y * 128, n0 = blockIdx.x * 128;
  float d[64];
#pragma unroll
  for (int i = 0; i < 64; ++i) d[i] = 0.f;
  if (tid == 0) { alloy_mbar_init(&bar, 1); asm volatile("fence.proxy.async.shared::cta;" ::: "memory"); }
  __syncthreads();
  uint32_t phase = 0;
  for (int k0 = 0; k0 < K; k0 += ALLOY_BK) {
    if (tid == 0) {
      alloy_mbar_arrive_expect_tx(&bar, (128 + 128) * ALLOY_BK * sizeof(__half));
      alloy_tma_load_2d(sA, &tmA, &bar, k0, m0);   // box {64, 128}
      alloy_tma_load_2d(sB, &tmB, &bar, k0, n0);
    }
    alloy_mbar_wait(&bar, phase);
    phase ^= 1;
    const uint64_t da = alloy_desc_kmajor_sw128(alloy_smem_u32(sA + wg * 64 * ALLOY_BK)), db = alloy_desc_kmajor_sw128(alloy_smem_u32(sB));
    asm volatile("wgmma.fence.sync.aligned;" ::: "memory");
#pragma unroll
    for (int kk = 0; kk < ALLOY_BK / 16; ++kk)
      alloy_wgmma_m64n128k16_f32_f16(d, da + (kk * 32 >> 4), db + (kk * 32 >> 4));
    asm volatile("wgmma.commit_group.sync.aligned;" ::: "memory");
    asm volatile("wgmma.wait_group.sync.aligned 0;" ::: "memory");
    __syncthreads();
  }
  const int warp = (tid % 128) / 32, lane = tid % 32;
  const int r = m0 + 64 * wg + 16 * warp + lane / 4;
#pragma unroll
  for (int i = 0; i < 128 / 8; ++i) {
    const int c = n0 + 8 * i + 2 * (lane % 4);
    *reinterpret_cast<float2*>(&C[r * N + c]) = make_float2(d[4 * i + 0], d[4 * i + 1]);
    *reinterpret_cast<float2*>(&C[(r + 8) * N + c]) = make_float2(d[4 * i + 2], d[4 * i + 3]);
  }
}

// Host: tensor map for a row-major R x K f16 matrix, box = ALLOY_BK (inner, 128 B) x box_rows, 128B swizzle.
inline CUresult alloy_make_tmap(CUtensorMap* tm, const void* gptr, uint64_t rows, uint64_t K, cuuint32_t box_rows) {
  cuuint64_t gdim[2] = {K, rows};
  cuuint64_t gstride[1] = {K * sizeof(__half)};   // bytes, multiple of 16
  cuuint32_t box[2] = {ALLOY_BK, box_rows};   // 64 for the 64x64 kernel, 128 for the 128x128 kernel
  cuuint32_t estride[2] = {1, 1};
  return cuTensorMapEncodeTiled(tm, CU_TENSOR_MAP_DATA_TYPE_FLOAT16, 2, const_cast<void*>(gptr), gdim, gstride, box,
                                estride, CU_TENSOR_MAP_INTERLEAVE_NONE, CU_TENSOR_MAP_SWIZZLE_128B,
                                CU_TENSOR_MAP_L2_PROMOTION_L2_128B, CU_TENSOR_MAP_FLOAT_OOB_FILL_NONE);
}
