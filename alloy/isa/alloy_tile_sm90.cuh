// Alloy's tile functions on sm_90 (GH200), alloy/isa/tile.py: TMA loads into 128B-swizzled shared memory completed
// through an mbarrier, and wgmma on f16, bf16, e4m3, or e5m2 tiles (OCP FP8) with an f32 accumulator. Build for sm_90a
// (-gencode arch=compute_90a,code=sm_90a): plain sm_90 rejects wgmma. A is M x K row-major; B is given as N x K
// row-major (each column of B contiguous, K-major, the layout wgmma reads without a transpose); C is M x N row-major
// f32, read and written: C = A x B + C. A K block is 128 bytes of a row for every input type (64 halves or 128 FP8
// values), so the swizzle, the descriptor, and the 32-byte step per wgmma are the same for all four. Facts and sources:
// alloy-workspace notes/isa-research/tensor.md, sections 1, 3, and 5.
#pragma once
// alloy-only: file
// Blocks between "// alloy-only: <tokens>" and "// alloy-end", and lines ending in that tag, belong to the named
// types and shapes only; tile.py inlines this file trimmed to what one answer uses.
// alloy-end
#include <cuda.h>
#include <cuda_fp16.h>
#include <cstdint>

constexpr int ALLOY_BM = 64, ALLOY_BN = 64, ALLOY_ROW = 128;  // a K block: 128 bytes of a row

// The input element types of the tile kernels, as their template argument.
enum alloy_elem { ALLOY_F16, ALLOY_BF16, ALLOY_E4M3, ALLOY_E5M2 };
template <int E> constexpr int alloy_bytes = E <= ALLOY_BF16 ? 2 : 1;

__device__ __forceinline__ uint32_t alloy_smem_u32(const void* p) {
  return static_cast<uint32_t>(__cvta_generic_to_shared(p));
}

// alloy-only: mma
// K-major, 128B-swizzled operand tile whose rows are 128 bytes, 1024B-aligned.
__device__ __forceinline__ uint64_t alloy_desc_kmajor_sw128(uint32_t saddr) {
  uint64_t d = 0;
  d |= uint64_t((saddr & 0x3FFFF) >> 4);   // [13:0]  start address >> 4
  d |= uint64_t(1) << 16;                    // [29:16] LBO (unused for swizzled K-major, "assumed 1")
  d |= uint64_t(1024 >> 4) << 32;            // [45:32] SBO = 8 rows * 128 B = 1024 B
  d |= uint64_t(1) << 62;                    // [63:62] 1 = 128B swizzle
  return d;
}
// alloy-end

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
// One box of shared memory into the global tile of the tensor map (TMA store), the reverse of alloy_tma_load_2d: the
// threads' writes to src reach the async proxy first (fence.proxy.async.shared::cta), and src is reused only after
// cp.async.bulk.commit_group and cp.async.bulk.wait_group.read 0. A box crossing the global edge writes its inside only.
__device__ __forceinline__ void alloy_tma_store_2d(const CUtensorMap* tm, const void* src, int c0, int c1) {
  asm volatile("cp.async.bulk.tensor.2d.global.shared::cta.bulk_group [%0, {%2, %3}], [%1];"
               :: "l"(reinterpret_cast<uint64_t>(tm)), "r"(alloy_smem_u32(src)), "r"(c0), "r"(c1) : "memory");
}

// alloy-only: mma
#define D8(i) "+f"(d[i]), "+f"(d[i+1]), "+f"(d[i+2]), "+f"(d[i+3]), "+f"(d[i+4]), "+f"(d[i+5]), "+f"(d[i+6]), "+f"(d[i+7])
#define R32 "{%0,%1,%2,%3,%4,%5,%6,%7,%8,%9,%10,%11,%12,%13,%14,%15,%16,%17,%18,%19,%20,%21,%22,%23,%24,%25,%26,%27,%28,%29,%30,%31}"
#define R64 "{%0,%1,%2,%3,%4,%5,%6,%7,%8,%9,%10,%11,%12,%13,%14,%15,%16,%17,%18,%19,%20,%21,%22,%23,%24,%25,%26,%27,%28,%29,%30,%31," \
            "%32,%33,%34,%35,%36,%37,%38,%39,%40,%41,%42,%43,%44,%45,%46,%47,%48,%49,%50,%51,%52,%53,%54,%55,%56,%57,%58,%59,%60,%61,%62,%63}"
// The 16-bit forms take the transpose immediates (0: K-major); the FP8 forms have none and are K-major only.
#define ALLOY_WGMMA64(NAME, SHAPE, TAIL)                                                              \
  __device__ __forceinline__ void NAME(float (&d)[32], uint64_t da, uint64_t db) {                    \
    asm volatile("{\n .reg .pred p;\n setp.ne.b32 p, %34, 0;\n"                                       \
                 "wgmma.mma_async.sync.aligned." SHAPE " " R32 ", %32, %33, p, 1, 1" TAIL ";\n}"      \
                 : D8(0), D8(8), D8(16), D8(24)                                                       \
                 : "l"(da), "l"(db), "r"(1));                                                         \
  }
#define ALLOY_WGMMA128(NAME, SHAPE, TAIL)                                                             \
  __device__ __forceinline__ void NAME(float (&d)[64], uint64_t da, uint64_t db) {                    \
    asm volatile("{\n .reg .pred p;\n setp.ne.b32 p, %66, 0;\n"                                       \
                 "wgmma.mma_async.sync.aligned." SHAPE " " R64 ", %64, %65, p, 1, 1" TAIL ";\n}"      \
                 : D8(0), D8(8), D8(16), D8(24), D8(32), D8(40), D8(48), D8(56)                       \
                 : "l"(da), "l"(db), "r"(1));                                                         \
  }
ALLOY_WGMMA64(alloy_wgmma_n64_f16, "m64n64k16.f32.f16.f16", ", 0, 0")  // alloy-only: n64 f16
ALLOY_WGMMA64(alloy_wgmma_n64_bf16, "m64n64k16.f32.bf16.bf16", ", 0, 0")  // alloy-only: n64 bf16
ALLOY_WGMMA64(alloy_wgmma_n64_e4m3, "m64n64k32.f32.e4m3.e4m3", "")  // alloy-only: n64 e4m3
ALLOY_WGMMA64(alloy_wgmma_n64_e5m2, "m64n64k32.f32.e5m2.e5m2", "")  // alloy-only: n64 e5m2
ALLOY_WGMMA128(alloy_wgmma_n128_f16, "m64n128k16.f32.f16.f16", ", 0, 0")  // alloy-only: n128 f16
ALLOY_WGMMA128(alloy_wgmma_n128_bf16, "m64n128k16.f32.bf16.bf16", ", 0, 0")  // alloy-only: n128 bf16
ALLOY_WGMMA128(alloy_wgmma_n128_e4m3, "m64n128k32.f32.e4m3.e4m3", "")  // alloy-only: n128 e4m3
ALLOY_WGMMA128(alloy_wgmma_n128_e5m2, "m64n128k32.f32.e5m2.e5m2", "")  // alloy-only: n128 e5m2
// alloy-end

// One wgmma of K = 32 bytes per row (16 halves or 32 FP8 values) for the element type E.
// alloy-only: mma n64
template <int E> __device__ __forceinline__ void alloy_wgmma(float (&d)[32], uint64_t da, uint64_t db) {
  if constexpr (E == ALLOY_F16) alloy_wgmma_n64_f16(d, da, db);  // alloy-only: f16
  if constexpr (E == ALLOY_BF16) alloy_wgmma_n64_bf16(d, da, db);  // alloy-only: bf16
  if constexpr (E == ALLOY_E4M3) alloy_wgmma_n64_e4m3(d, da, db);  // alloy-only: e4m3
  if constexpr (E == ALLOY_E5M2) alloy_wgmma_n64_e5m2(d, da, db);  // alloy-only: e5m2
}
// alloy-end
// alloy-only: mma n128
template <int E> __device__ __forceinline__ void alloy_wgmma(float (&d)[64], uint64_t da, uint64_t db) {
  if constexpr (E == ALLOY_F16) alloy_wgmma_n128_f16(d, da, db);  // alloy-only: f16
  if constexpr (E == ALLOY_BF16) alloy_wgmma_n128_bf16(d, da, db);  // alloy-only: bf16
  if constexpr (E == ALLOY_E4M3) alloy_wgmma_n128_e4m3(d, da, db);  // alloy-only: e4m3
  if constexpr (E == ALLOY_E5M2) alloy_wgmma_n128_e5m2(d, da, db);  // alloy-only: e5m2
}
// alloy-end

// alloy-only: mma
// C inside the M x N matrix: a partial tile at the edge reads zeros past it and writes nothing there, while TMA
// zero-fills the A and B boxes that cross the edge (OOB_FILL_NONE) and still counts their bytes on the mbarrier.
__device__ __forceinline__ float alloy_c_at(const float* C, int M, int N, int r, int c) {
  return r < M && c < N ? C[r * N + c] : 0.0f;
}
__device__ __forceinline__ void alloy_c_put(float* C, int M, int N, int r, int c, float v) {
  if (r < M && c < N) C[r * N + c] = v;
}
// alloy-end

// alloy-only: mma n64 64x64
template <int E>
__global__ void __launch_bounds__(128) alloy_gemm_64x64(const __grid_constant__ CUtensorMap tmA,
                                                     const __grid_constant__ CUtensorMap tmB,
                                                     float* __restrict__ C, int M, int N, int K) {
  __shared__ alignas(1024) uint8_t sA[ALLOY_BM * ALLOY_ROW];
  __shared__ alignas(1024) uint8_t sB[ALLOY_BN * ALLOY_ROW];
  __shared__ alignas(8) uint64_t bar;
  const int tid = threadIdx.x, m0 = blockIdx.y * ALLOY_BM, n0 = blockIdx.x * ALLOY_BN;
  const int warp = tid / 32, lane = tid % 32;
  const int r = m0 + 16 * warp + lane / 4;
  float d[32];
#pragma unroll
  for (int i = 0; i < ALLOY_BN / 8; ++i) {  // the accumulators start as C: D = A x B + C
    const int c = n0 + 8 * i + 2 * (lane % 4);
    d[4 * i + 0] = alloy_c_at(C, M, N, r, c), d[4 * i + 1] = alloy_c_at(C, M, N, r, c + 1);
    d[4 * i + 2] = alloy_c_at(C, M, N, r + 8, c), d[4 * i + 3] = alloy_c_at(C, M, N, r + 8, c + 1);
  }
  if (tid == 0) {
    alloy_mbar_init(&bar, 1);
    asm volatile("fence.proxy.async.shared::cta;" ::: "memory");  // make init visible to the async proxy
  }
  __syncthreads();
  uint32_t phase = 0;
  constexpr int block = ALLOY_ROW / alloy_bytes<E>;  // elements of K per block
  for (int k0 = 0; k0 < K; k0 += block) {
    if (tid == 0) {
      alloy_mbar_arrive_expect_tx(&bar, (ALLOY_BM + ALLOY_BN) * ALLOY_ROW);
      alloy_tma_load_2d(sA, &tmA, &bar, k0, m0);   // coords innermost-first: {k, m}
      alloy_tma_load_2d(sB, &tmB, &bar, k0, n0);   // {k, n}
    }
    alloy_mbar_wait(&bar, phase);
    phase ^= 1;
    const uint64_t da = alloy_desc_kmajor_sw128(alloy_smem_u32(sA)), db = alloy_desc_kmajor_sw128(alloy_smem_u32(sB));
    asm volatile("wgmma.fence.sync.aligned;" ::: "memory");
#pragma unroll
    for (int kk = 0; kk < ALLOY_ROW / 32; ++kk)              // 4 wgmma of 32 bytes per row cover the block
      alloy_wgmma<E>(d, da + (kk * 32 >> 4), db + (kk * 32 >> 4));  // +32 B per k-step
    asm volatile("wgmma.commit_group.sync.aligned;" ::: "memory");
    asm volatile("wgmma.wait_group.sync.aligned 0;" ::: "memory");
    __syncthreads();  // single stage: all reads of sA/sB done before the next TMA overwrites them
  }
#pragma unroll
  for (int i = 0; i < ALLOY_BN / 8; ++i) {
    const int c = n0 + 8 * i + 2 * (lane % 4);
    alloy_c_put(C, M, N, r, c, d[4 * i + 0]), alloy_c_put(C, M, N, r, c + 1, d[4 * i + 1]);
    alloy_c_put(C, M, N, r + 8, c, d[4 * i + 2]), alloy_c_put(C, M, N, r + 8, c + 1, d[4 * i + 3]);
  }
}

// alloy-end

// alloy-only: mma n128 128x128
// 128x128 tile, rows of 128 bytes, two consumer warpgroups (256 threads); warpgroup g computes rows [64g, 64g+64).
template <int E>
__global__ void __launch_bounds__(256) alloy_gemm_128x128(const __grid_constant__ CUtensorMap tmA,
                                                       const __grid_constant__ CUtensorMap tmB,
                                                       float* __restrict__ C, int M, int N, int K) {
  __shared__ alignas(1024) uint8_t sA[128 * ALLOY_ROW];
  __shared__ alignas(1024) uint8_t sB[128 * ALLOY_ROW];
  __shared__ alignas(8) uint64_t bar;
  const int tid = threadIdx.x, wg = tid / 128, m0 = blockIdx.y * 128, n0 = blockIdx.x * 128;
  const int warp = (tid % 128) / 32, lane = tid % 32;
  const int r = m0 + 64 * wg + 16 * warp + lane / 4;
  float d[64];
#pragma unroll
  for (int i = 0; i < 128 / 8; ++i) {  // the accumulators start as C: D = A x B + C
    const int c = n0 + 8 * i + 2 * (lane % 4);
    d[4 * i + 0] = alloy_c_at(C, M, N, r, c), d[4 * i + 1] = alloy_c_at(C, M, N, r, c + 1);
    d[4 * i + 2] = alloy_c_at(C, M, N, r + 8, c), d[4 * i + 3] = alloy_c_at(C, M, N, r + 8, c + 1);
  }
  if (tid == 0) { alloy_mbar_init(&bar, 1); asm volatile("fence.proxy.async.shared::cta;" ::: "memory"); }
  __syncthreads();
  uint32_t phase = 0;
  constexpr int block = ALLOY_ROW / alloy_bytes<E>;
  for (int k0 = 0; k0 < K; k0 += block) {
    if (tid == 0) {
      alloy_mbar_arrive_expect_tx(&bar, (128 + 128) * ALLOY_ROW);
      alloy_tma_load_2d(sA, &tmA, &bar, k0, m0);   // box {64, 128}
      alloy_tma_load_2d(sB, &tmB, &bar, k0, n0);
    }
    alloy_mbar_wait(&bar, phase);
    phase ^= 1;
    const uint64_t da = alloy_desc_kmajor_sw128(alloy_smem_u32(sA + wg * 64 * ALLOY_ROW)), db = alloy_desc_kmajor_sw128(alloy_smem_u32(sB));
    asm volatile("wgmma.fence.sync.aligned;" ::: "memory");
#pragma unroll
    for (int kk = 0; kk < ALLOY_ROW / 32; ++kk)
      alloy_wgmma<E>(d, da + (kk * 32 >> 4), db + (kk * 32 >> 4));
    asm volatile("wgmma.commit_group.sync.aligned;" ::: "memory");
    asm volatile("wgmma.wait_group.sync.aligned 0;" ::: "memory");
    __syncthreads();
  }
#pragma unroll
  for (int i = 0; i < 128 / 8; ++i) {
    const int c = n0 + 8 * i + 2 * (lane % 4);
    alloy_c_put(C, M, N, r, c, d[4 * i + 0]), alloy_c_put(C, M, N, r, c + 1, d[4 * i + 1]);
    alloy_c_put(C, M, N, r + 8, c, d[4 * i + 2]), alloy_c_put(C, M, N, r + 8, c + 1, d[4 * i + 3]);
  }
}
// alloy-end

// Host: tensor map for a row-major R x K matrix of element type E, box = one K block (128 bytes) x box_rows, 128B
// swizzle. FP8 has no tensor-map type of its own on CUDA 12: it moves as bytes (UINT8).
template <int E>
inline CUresult alloy_make_tmap(CUtensorMap* tm, const void* gptr, uint64_t rows, uint64_t K, cuuint32_t box_rows) {
  constexpr CUtensorMapDataType type = E == ALLOY_F16    ? CU_TENSOR_MAP_DATA_TYPE_FLOAT16
                                       : E == ALLOY_BF16 ? CU_TENSOR_MAP_DATA_TYPE_BFLOAT16
                                                         : CU_TENSOR_MAP_DATA_TYPE_UINT8;
  cuuint64_t gdim[2] = {K, rows};
  cuuint64_t gstride[1] = {K * alloy_bytes<E>};   // bytes, multiple of 16
  cuuint32_t box[2] = {ALLOY_ROW / alloy_bytes<E>, box_rows};   // 64 for the 64x64 kernel, 128 for the 128x128 kernel
  cuuint32_t estride[2] = {1, 1};
  return cuTensorMapEncodeTiled(tm, type, 2, const_cast<void*>(gptr), gdim, gstride, box, estride,
                                CU_TENSOR_MAP_INTERLEAVE_NONE, CU_TENSOR_MAP_SWIZZLE_128B,
                                CU_TENSOR_MAP_L2_PROMOTION_L2_128B, CU_TENSOR_MAP_FLOAT_OOB_FILL_NONE);
}
