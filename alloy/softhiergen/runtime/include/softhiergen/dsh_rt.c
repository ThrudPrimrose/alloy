// softhiergen runtime over the SoftHier SDK (C: the SDK headers define functions and are written as C).
// The collectives run on every cluster of the mesh. Data moves by iDMA pushes into the peers' TCDM (cores reach
// other clusters' TCDM only through iDMA); the Spatz core combines. Barriers order the pushes:
// a global barrier before them frees the destinations, one after them publishes the data.
#include <stddef.h>
#include <stdint.h>

#include "flex_runtime.h"
#include "flex_dma_pattern.h"
#include "flex_redmule.h"
#include "softhiergen/dsh_rt.h"
#include "softhiergen/dsh_rvv.h"

uint32_t dsh_cluster_id(void) { return flex_get_cluster_id(); }
uint32_t dsh_is_dma_core(void) { return flex_is_dm_core(); }
uint32_t dsh_is_compute_core(void) { return flex_is_first_core(); }

void dsh_cluster_sync(void) { flex_intra_cluster_sync(); }
void dsh_global_barrier(void) { flex_global_barrier_xy(); }

uint64_t dsh_addr(const void* p) { return (uint64_t)(uintptr_t)p; }
uint64_t dsh_remote(uint32_t cid, const void* p) {
    return (uint64_t)ARCH_CLUSTER_TCDM_REMOTE + (uint64_t)cid * ARCH_CLUSTER_TCDM_SIZE +
           ((uint64_t)(uintptr_t)p - ARCH_CLUSTER_TCDM_BASE);
}

void dsh_dma_1d(uint64_t dst, uint64_t src, uint32_t bytes) { flex_dma_async_1d(dst, src, bytes); }
void dsh_dma_2d(uint64_t dst, uint64_t src, uint32_t row_bytes, uint32_t dst_stride, uint32_t src_stride,
                uint32_t rows) {
    flex_dma_async_2d(dst, src, row_bytes, dst_stride, src_stride, rows);
}
void dsh_dma_wait(void) { flex_dma_async_wait_all(); }

// RedMulE names the extents M, N (the inner one), K: flex_redmule_config(m, k, n), then flex_redmule_trigger(a, b, c,
// REDMULE_FP_16) with TCDM offsets. The SDK loads t3/t4 and t0-t2 in asm statements apart from the custom instructions,
// which lets the compiler reuse those registers in between; here one asm statement holds the loads and both instructions.
void dsh_redmule_mma(const void* a, const void* b, void* c, uint32_t m, uint32_t k, uint32_t n) {
    uint32_t cfg0 = ((uint32_t)(uint16_t)n << 16) | (uint16_t)m, cfg1 = (uint16_t)k;
    __asm__ volatile(
        "mv t3, %0\n\tmv t4, %1\n\t"
        ".word (0b11101 << 20) | (0b11100 << 15) | 0b0001010\n\t"  // config: rs1 t3, rs2 t4
        "mv t0, %2\n\tmv t1, %3\n\tmv t2, %4\n\t"
        ".word (0b00111 << 27) | (0b00110 << 20) | (0b00101 << 15) | (0b011 << 7) | 0b0101010"  // trigger, FP16
        :
        : "r"(cfg0), "r"(cfg1), "r"((uint32_t)(uintptr_t)a), "r"((uint32_t)(uintptr_t)b), "r"((uint32_t)(uintptr_t)c)
        : "t0", "t1", "t2", "t3", "t4", "memory");
}
void dsh_redmule_wait(void) { flex_redmule_wait(); }

static uint32_t element_size(uint32_t dtype) { return dtype == DSH_F16 ? 2 : 4; }

// dst = dst OP src over n elements, on the Spatz core
static void combine(void* dst, const void* src, uint32_t n, uint32_t dtype, uint32_t op) {
    if (dtype == DSH_F32) {
        float* d = (float*)dst;
        const float* s = (const float*)src;
        if (op == DSH_SUM) dsh_rvv_add_f32(d, d, s, n);
        else if (op == DSH_PROD) dsh_rvv_mul_f32(d, d, s, n);
        else if (op == DSH_MAX) dsh_rvv_max_f32(d, d, s, n);
        else dsh_rvv_min_f32(d, d, s, n);
    } else if (dtype == DSH_F16) {
        dsh_f16* d = (dsh_f16*)dst;
        const dsh_f16* s = (const dsh_f16*)src;
        if (op == DSH_SUM) dsh_rvv_add_f16(d, d, s, n);
        else if (op == DSH_PROD) dsh_rvv_mul_f16(d, d, s, n);
        else if (op == DSH_MAX) dsh_rvv_max_f16(d, d, s, n);
        else dsh_rvv_min_f16(d, d, s, n);
    } else {
        int32_t* d = (int32_t*)dst;
        const int32_t* s = (const int32_t*)src;
        if (op == DSH_SUM) dsh_rvv_add_i32(d, d, s, n);
        else if (op == DSH_PROD) dsh_rvv_mul_i32(d, d, s, n);
        else if (op == DSH_MAX) dsh_rvv_max_i32(d, d, s, n);
        else dsh_rvv_min_i32(d, d, s, n);
    }
}

static void copy_bytes(void* dst, const void* src, uint32_t bytes) {
    if (dst != src) dsh_rvv_copy_u8((uint8_t*)dst, (const uint8_t*)src, bytes);
    dsh_vfence();
}

// out = slot 0 OP slot 1 OP ... in rank order, so that every cluster computes the same bits
static void fold_slots(void* out, const void* slots, uint32_t count, uint32_t dtype, uint32_t op) {
    uint32_t bytes = count * element_size(dtype);
    const uint8_t* s = (const uint8_t*)slots;
    copy_bytes(out, s, bytes);
    for (uint32_t p = 1; p < ARCH_NUM_CLUSTER; ++p) combine(out, s + p * bytes, count, dtype, op);
    dsh_vfence();
}

// Every cluster in turn pushes `bytes` from src (+ p * src_step for peer p) to dst + sender * bytes on each peer, a
// global barrier after each turn. All clusters pushing at once never finishes on the v1 model (seen 2026-11-19);
// one sender at a time is the pattern bcast and scatter run.
static void push_in_turns(void* dst, const void* src, uint32_t bytes, uint32_t src_step) {
    uint32_t me = flex_get_cluster_id();
    for (uint32_t sender = 0; sender < ARCH_NUM_CLUSTER; ++sender) {
        if (sender == me && flex_is_dm_core()) {
            for (uint32_t p = 0; p < ARCH_NUM_CLUSTER; ++p)
                if (p != me)
                    flex_dma_async_1d(dsh_remote(p, (uint8_t*)dst + me * bytes),
                                      dsh_addr((const uint8_t*)src + p * src_step), bytes);
            flex_dma_async_wait_all();
        }
        flex_global_barrier_xy();
    }
}

void dsh_bcast(void* out, const void* in, uint32_t bytes, uint32_t root) {
    uint32_t me = flex_get_cluster_id();
    flex_global_barrier_xy();
    if (me == root) {
        if (flex_is_dm_core()) {
            for (uint32_t p = 0; p < ARCH_NUM_CLUSTER; ++p)
                if (p != root) flex_dma_async_1d(dsh_remote(p, out), dsh_addr(in), bytes);
            flex_dma_async_wait_all();
        }
        if (flex_is_first_core()) copy_bytes(out, in, bytes);
    }
    flex_global_barrier_xy();
}

void dsh_reduce(void* out, const void* in, void* scratch, uint32_t count, uint32_t dtype, uint32_t op,
                uint32_t root) {
    uint32_t me = flex_get_cluster_id(), bytes = count * element_size(dtype);
    uint8_t* slots = (uint8_t*)scratch;
    flex_global_barrier_xy();
    if (me == root) {
        if (flex_is_first_core()) copy_bytes(slots + me * bytes, in, bytes);
    } else if (flex_is_dm_core()) {
        flex_dma_async_1d(dsh_remote(root, slots + me * bytes), dsh_addr(in), bytes);
        flex_dma_async_wait_all();
    }
    flex_global_barrier_xy();
    if (me == root && flex_is_first_core()) fold_slots(out, slots, count, dtype, op);
    flex_intra_cluster_sync();
}

void dsh_allreduce(void* out, const void* in, void* scratch, uint32_t count, uint32_t dtype, uint32_t op) {
    uint32_t me = flex_get_cluster_id(), bytes = count * element_size(dtype);
    uint8_t* slots = (uint8_t*)scratch;
    if (flex_is_first_core()) copy_bytes(slots + me * bytes, in, bytes);
    flex_global_barrier_xy();
    push_in_turns(slots, in, bytes, 0);
    if (flex_is_first_core()) fold_slots(out, slots, count, dtype, op);
    flex_intra_cluster_sync();
}

void dsh_allgather(void* out, const void* in, uint32_t bytes) {
    uint32_t me = flex_get_cluster_id();
    flex_global_barrier_xy();
    if (flex_is_first_core()) copy_bytes((uint8_t*)out + me * bytes, in, bytes);
    push_in_turns(out, in, bytes, 0);
}

void dsh_gather(void* out, const void* in, uint32_t bytes, uint32_t root) {
    uint32_t me = flex_get_cluster_id();
    uint8_t* o = (uint8_t*)out;
    flex_global_barrier_xy();
    if (me == root) {
        if (flex_is_first_core()) copy_bytes(o + me * bytes, in, bytes);
    } else if (flex_is_dm_core()) {
        flex_dma_async_1d(dsh_remote(root, o + me * bytes), dsh_addr(in), bytes);
        flex_dma_async_wait_all();
    }
    flex_global_barrier_xy();
}

void dsh_scatter(void* out, const void* in, uint32_t bytes, uint32_t root) {
    uint32_t me = flex_get_cluster_id();
    const uint8_t* i = (const uint8_t*)in;
    flex_global_barrier_xy();
    if (me == root) {
        if (flex_is_dm_core()) {
            for (uint32_t p = 0; p < ARCH_NUM_CLUSTER; ++p)
                if (p != root) flex_dma_async_1d(dsh_remote(p, out), dsh_addr(i + p * bytes), bytes);
            flex_dma_async_wait_all();
        }
        if (flex_is_first_core()) copy_bytes(out, i + me * bytes, bytes);
    }
    flex_global_barrier_xy();
}

void dsh_reduce_scatter(void* out, const void* in, void* scratch, uint32_t count, uint32_t dtype, uint32_t op) {
    uint32_t me = flex_get_cluster_id(), bytes = count * element_size(dtype);
    uint8_t* slots = (uint8_t*)scratch;
    if (flex_is_first_core()) copy_bytes(slots + me * bytes, (const uint8_t*)in + me * bytes, bytes);
    flex_global_barrier_xy();
    push_in_turns(slots, in, bytes, bytes);
    if (flex_is_first_core()) fold_slots(out, slots, count, dtype, op);
    flex_intra_cluster_sync();
}

void dsh_alltoall(void* out, const void* in, uint32_t bytes) {
    uint32_t me = flex_get_cluster_id();
    flex_global_barrier_xy();
    if (flex_is_first_core()) copy_bytes((uint8_t*)out + me * bytes, (const uint8_t*)in + me * bytes, bytes);
    push_in_turns(out, in, bytes, bytes);
}
