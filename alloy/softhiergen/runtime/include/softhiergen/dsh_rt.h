// softhiergen runtime: the calls generated code makes, implemented over the SoftHier SDK in dsh_rt.c.
// Pointers to TCDM are local addresses (the TCDM starts at 0), equal on every cluster for one object.
#ifndef DSH_RT_H
#define DSH_RT_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

// Element types and reductions of the collectives
enum { DSH_F32 = 0, DSH_F16 = 1, DSH_I32 = 2 };
enum { DSH_SUM = 0, DSH_PROD = 1, DSH_MAX = 2, DSH_MIN = 3 };

uint32_t dsh_cluster_id(void);
// Roles: core 0 drives Spatz and RedMulE, the last core issues iDMA
uint32_t dsh_is_dma_core(void);
uint32_t dsh_is_compute_core(void);

void dsh_cluster_sync(void);
void dsh_global_barrier(void);

// Address of a TCDM object in the TCDM of cluster cid
uint64_t dsh_remote(uint32_t cid, const void* local);
uint64_t dsh_addr(const void* p);

// iDMA, issued by the DMA core only; asynchronous until dsh_dma_wait
void dsh_dma_1d(uint64_t dst, uint64_t src, uint32_t bytes);
void dsh_dma_2d(uint64_t dst, uint64_t src, uint32_t row_bytes, uint32_t dst_stride, uint32_t src_stride,
                uint32_t rows);
void dsh_dma_wait(void);

// RedMulE: c (m x n) += a (m x k) b (k x n), f16, packed row-major in TCDM; asynchronous until dsh_redmule_wait
void dsh_redmule_mma(const void* a, const void* b, void* c, uint32_t m, uint32_t k, uint32_t n);
void dsh_redmule_wait(void);

// Collectives over every cluster of the mesh; every core of every cluster calls them. Buffers are TCDM objects.
// scratch holds num_clusters * count elements where a call takes one.
void dsh_bcast(void* out, const void* in, uint32_t bytes, uint32_t root);
void dsh_reduce(void* out, const void* in, void* scratch, uint32_t count, uint32_t dtype, uint32_t op,
                uint32_t root);
void dsh_allreduce(void* out, const void* in, void* scratch, uint32_t count, uint32_t dtype, uint32_t op);
void dsh_allgather(void* out, const void* in, uint32_t bytes);
void dsh_gather(void* out, const void* in, uint32_t bytes, uint32_t root);
void dsh_scatter(void* out, const void* in, uint32_t bytes, uint32_t root);
void dsh_reduce_scatter(void* out, const void* in, void* scratch, uint32_t count, uint32_t dtype, uint32_t op);
void dsh_alltoall(void* out, const void* in, uint32_t bytes);

#ifdef __cplusplus
}
#endif

#endif  // DSH_RT_H
