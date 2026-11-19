---
name: alloy-facts-softhier
description: "Alloy's checked facts for SoftHier v1: the C code of every vector (Spatz RVV), copy (iDMA), matrix (RedMulE) and barrier row with its GVSoC verdict, and the build line."
when: before writing a SoftHier kernel.
---

# SoftHier v1 (GVSoC model pulp.chips.soft_hier_old.flex_cluster, simulated): Alloy's checked facts

Every row is C code for one operation on a SoftHier v1 cluster, with its GVSoC verdict and its note. A row that moves bytes or no data (a copy, its wait, a barrier) holds for any element type.

## Target

```text
build: riscv32-unknown-elf-gcc -mabi=ilp32d -mcmodel=medlow -march=rv32imafdv_zfh_zvfh -O3 -ffast-math -fno-builtin -fno-tree-vectorize -fno-common -ffunction-sections -I $SOFTHIER_SDK/runtime/runtime/include -c alloy.c -o alloy.o
note: Every core of every cluster runs the same ELF from _start. Per cluster: 3 Snitch cores; core 0 drives the Spatz vector unit (VLEN 256) and RedMulE, the last core (flex_is_dm_core()) issues iDMA. Data a kernel computes on sits in the cluster's 1 MiB TCDM (local(offset)); HBM and other clusters' TCDM are reached only through iDMA (hbm_west(node, offset), hbm_south(node, offset), remote_cid(cid, offset)): a core's own load or store there is out of bounds. Simulated, not hardware.
```

## load

```text
softhier/f32/load: load on spatz: __riscv_vle32_v_f32m8(x + i, vl)
  verified on GVSoC pulp.chips.soft_hier_old.flex_cluster
#include <riscv_vector.h>
// y[0:n] = x[0:n] through vector registers; x and y in TCDM; run on the Spatz core (core 0)
void alloy_load_f32(float* y, const float* x, size_t n) {
    for (size_t i = 0; i < n;) {
        size_t vl = __riscv_vsetvl_e32m8(n - i);
        vfloat32m8_t v = __riscv_vle32_v_f32m8(x + i, vl);
        __riscv_vse32_v_f32m8(y + i, v, vl);
        i += vl;
    }
}

softhier/f16/load: load on spatz: __riscv_vle16_v_f16m8(x + i, vl)
  verified on GVSoC pulp.chips.soft_hier_old.flex_cluster
#include <riscv_vector.h>
// y[0:n] = x[0:n] through vector registers; x and y in TCDM; run on the Spatz core (core 0)
void alloy_load_f16(_Float16* y, const _Float16* x, size_t n) {
    for (size_t i = 0; i < n;) {
        size_t vl = __riscv_vsetvl_e16m8(n - i);
        vfloat16m8_t v = __riscv_vle16_v_f16m8(x + i, vl);
        __riscv_vse16_v_f16m8(y + i, v, vl);
        i += vl;
    }
}

```

## store

```text
softhier/f32/store: store on spatz: __riscv_vse32_v_f32m8(y + i, v, vl)
  verified on GVSoC pulp.chips.soft_hier_old.flex_cluster
#include <riscv_vector.h>
// y[0:n] = x[0:n] through vector registers; x and y in TCDM; run on the Spatz core (core 0)
void alloy_store_f32(float* y, const float* x, size_t n) {
    for (size_t i = 0; i < n;) {
        size_t vl = __riscv_vsetvl_e32m8(n - i);
        vfloat32m8_t v = __riscv_vle32_v_f32m8(x + i, vl);
        __riscv_vse32_v_f32m8(y + i, v, vl);
        i += vl;
    }
}

softhier/f16/store: store on spatz: __riscv_vse16_v_f16m8(y + i, v, vl)
  verified on GVSoC pulp.chips.soft_hier_old.flex_cluster
#include <riscv_vector.h>
// y[0:n] = x[0:n] through vector registers; x and y in TCDM; run on the Spatz core (core 0)
void alloy_store_f16(_Float16* y, const _Float16* x, size_t n) {
    for (size_t i = 0; i < n;) {
        size_t vl = __riscv_vsetvl_e16m8(n - i);
        vfloat16m8_t v = __riscv_vle16_v_f16m8(x + i, vl);
        __riscv_vse16_v_f16m8(y + i, v, vl);
        i += vl;
    }
}

```

## add

```text
softhier/f32/add: add on spatz: __riscv_vfadd_vv_f32m8(a, b, vl)
  verified on GVSoC pulp.chips.soft_hier_old.flex_cluster: max rel error 3.1e-08
#include <riscv_vector.h>
// z[i] = x[i] + y[i] for i < n; x, y, z in TCDM; run on the Spatz core (core 0)
void alloy_add_f32(float* z, const float* x, const float* y, size_t n) {
    for (size_t i = 0; i < n;) {
        size_t vl = __riscv_vsetvl_e32m8(n - i);
        vfloat32m8_t a = __riscv_vle32_v_f32m8(x + i, vl);
        vfloat32m8_t b = __riscv_vle32_v_f32m8(y + i, vl);
        __riscv_vse32_v_f32m8(z + i, __riscv_vfadd_vv_f32m8(a, b, vl), vl);
        i += vl;
    }
}

softhier/f16/add: add on spatz: __riscv_vfadd_vv_f16m8(a, b, vl)
  verified on GVSoC pulp.chips.soft_hier_old.flex_cluster: max rel error 0.00025
#include <riscv_vector.h>
// z[i] = x[i] + y[i] for i < n; x, y, z in TCDM; run on the Spatz core (core 0)
void alloy_add_f16(_Float16* z, const _Float16* x, const _Float16* y, size_t n) {
    for (size_t i = 0; i < n;) {
        size_t vl = __riscv_vsetvl_e16m8(n - i);
        vfloat16m8_t a = __riscv_vle16_v_f16m8(x + i, vl);
        vfloat16m8_t b = __riscv_vle16_v_f16m8(y + i, vl);
        __riscv_vse16_v_f16m8(z + i, __riscv_vfadd_vv_f16m8(a, b, vl), vl);
        i += vl;
    }
}

```

## mul

```text
softhier/f32/mul: mul on spatz: __riscv_vfmul_vv_f32m8(a, b, vl)
  verified on GVSoC pulp.chips.soft_hier_old.flex_cluster: max rel error 2.9e-08
#include <riscv_vector.h>
// z[i] = x[i] * y[i] for i < n; x, y, z in TCDM; run on the Spatz core (core 0)
void alloy_mul_f32(float* z, const float* x, const float* y, size_t n) {
    for (size_t i = 0; i < n;) {
        size_t vl = __riscv_vsetvl_e32m8(n - i);
        vfloat32m8_t a = __riscv_vle32_v_f32m8(x + i, vl);
        vfloat32m8_t b = __riscv_vle32_v_f32m8(y + i, vl);
        __riscv_vse32_v_f32m8(z + i, __riscv_vfmul_vv_f32m8(a, b, vl), vl);
        i += vl;
    }
}

softhier/f16/mul: mul on spatz: __riscv_vfmul_vv_f16m8(a, b, vl)
  verified on GVSoC pulp.chips.soft_hier_old.flex_cluster: max rel error 0.00025
#include <riscv_vector.h>
// z[i] = x[i] * y[i] for i < n; x, y, z in TCDM; run on the Spatz core (core 0)
void alloy_mul_f16(_Float16* z, const _Float16* x, const _Float16* y, size_t n) {
    for (size_t i = 0; i < n;) {
        size_t vl = __riscv_vsetvl_e16m8(n - i);
        vfloat16m8_t a = __riscv_vle16_v_f16m8(x + i, vl);
        vfloat16m8_t b = __riscv_vle16_v_f16m8(y + i, vl);
        __riscv_vse16_v_f16m8(z + i, __riscv_vfmul_vv_f16m8(a, b, vl), vl);
        i += vl;
    }
}

```

## fma

```text
softhier/f32/fma: fma on spatz: __riscv_vfmacc_vv_f32m8(acc, a, b, vl)
  verified on GVSoC pulp.chips.soft_hier_old.flex_cluster: max rel error 5.1e-08
#include <riscv_vector.h>
// d[i] = a[i] * b[i] + c[i] for i < n, one rounding (vfmacc: acc += a * b); all in TCDM; run on the Spatz core (core 0)
void alloy_fma_f32(float* d, const float* a, const float* b, const float* c, size_t n) {
    for (size_t i = 0; i < n;) {
        size_t vl = __riscv_vsetvl_e32m8(n - i);
        vfloat32m8_t va = __riscv_vle32_v_f32m8(a + i, vl);
        vfloat32m8_t vb = __riscv_vle32_v_f32m8(b + i, vl);
        vfloat32m8_t acc = __riscv_vle32_v_f32m8(c + i, vl);
        __riscv_vse32_v_f32m8(d + i, __riscv_vfmacc_vv_f32m8(acc, va, vb, vl), vl);
        i += vl;
    }
}

softhier/f16/fma: fma on spatz: __riscv_vfmacc_vv_f16m8(acc, a, b, vl)
  verified on GVSoC pulp.chips.soft_hier_old.flex_cluster: max rel error 0.00034
#include <riscv_vector.h>
// d[i] = a[i] * b[i] + c[i] for i < n, one rounding (vfmacc: acc += a * b); all in TCDM; run on the Spatz core (core 0)
void alloy_fma_f16(_Float16* d, const _Float16* a, const _Float16* b, const _Float16* c, size_t n) {
    for (size_t i = 0; i < n;) {
        size_t vl = __riscv_vsetvl_e16m8(n - i);
        vfloat16m8_t va = __riscv_vle16_v_f16m8(a + i, vl);
        vfloat16m8_t vb = __riscv_vle16_v_f16m8(b + i, vl);
        vfloat16m8_t acc = __riscv_vle16_v_f16m8(c + i, vl);
        __riscv_vse16_v_f16m8(d + i, __riscv_vfmacc_vv_f16m8(acc, va, vb, vl), vl);
        i += vl;
    }
}

```

## reduce_add

```text
softhier/f32/reduce_add: reduce_add on spatz: __riscv_vfredusum_vs_f32m8_f32m1(v, acc, vl)
  verified on GVSoC pulp.chips.soft_hier_old.flex_cluster: max rel error 8e-08
  note: vfredusum adds in an unspecified order and accumulates in the element type: an f16 sum of many terms loses digits; sum f16 data in f32 with vfwredusum, or in blocks
#include <riscv_vector.h>
// the sum of x[0:n]; x in TCDM; run on the Spatz core (core 0)
float alloy_reduce_add_f32(const float* x, size_t n) {
    vfloat32m1_t acc = __riscv_vfmv_s_f_f32m1(0, 1);
    for (size_t i = 0; i < n;) {
        size_t vl = __riscv_vsetvl_e32m8(n - i);
        vfloat32m8_t v = __riscv_vle32_v_f32m8(x + i, vl);
        acc = __riscv_vfredusum_vs_f32m8_f32m1(v, acc, vl);
        i += vl;
    }
    return __riscv_vfmv_f_s_f32m1_f32(acc);
}

softhier/f16/reduce_add: reduce_add on spatz: __riscv_vfredusum_vs_f16m8_f16m1(v, acc, vl)
  verified on GVSoC pulp.chips.soft_hier_old.flex_cluster: max rel error 0.0005
  note: vfredusum adds in an unspecified order and accumulates in the element type: an f16 sum of many terms loses digits; sum f16 data in f32 with vfwredusum, or in blocks
#include <riscv_vector.h>
// the sum of x[0:n]; x in TCDM; run on the Spatz core (core 0)
_Float16 alloy_reduce_add_f16(const _Float16* x, size_t n) {
    vfloat16m1_t acc = __riscv_vfmv_s_f_f16m1(0, 1);
    for (size_t i = 0; i < n;) {
        size_t vl = __riscv_vsetvl_e16m8(n - i);
        vfloat16m8_t v = __riscv_vle16_v_f16m8(x + i, vl);
        acc = __riscv_vfredusum_vs_f16m8_f16m1(v, acc, vl);
        i += vl;
    }
    return __riscv_vfmv_f_s_f16m1_f16(acc);
}

```

## reduce_max

```text
softhier/f32/reduce_max: reduce_max on spatz: __riscv_vfredmax_vs_f32m8_f32m1(v, acc, vl)
  verified on GVSoC pulp.chips.soft_hier_old.flex_cluster
  note: starts from x[0], so n >= 1; -ffast-math (in the build line) assumes no NaN or infinity
#include <riscv_vector.h>
// the maximum of x[0:n], n >= 1; x in TCDM; run on the Spatz core (core 0)
float alloy_reduce_max_f32(const float* x, size_t n) {
    vfloat32m1_t acc = __riscv_vfmv_s_f_f32m1(x[0], 1);
    for (size_t i = 0; i < n;) {
        size_t vl = __riscv_vsetvl_e32m8(n - i);
        vfloat32m8_t v = __riscv_vle32_v_f32m8(x + i, vl);
        acc = __riscv_vfredmax_vs_f32m8_f32m1(v, acc, vl);
        i += vl;
    }
    return __riscv_vfmv_f_s_f32m1_f32(acc);
}

softhier/f16/reduce_max: reduce_max on spatz: __riscv_vfredmax_vs_f16m8_f16m1(v, acc, vl)
  verified on GVSoC pulp.chips.soft_hier_old.flex_cluster
  note: starts from x[0], so n >= 1; -ffast-math (in the build line) assumes no NaN or infinity
#include <riscv_vector.h>
// the maximum of x[0:n], n >= 1; x in TCDM; run on the Spatz core (core 0)
_Float16 alloy_reduce_max_f16(const _Float16* x, size_t n) {
    vfloat16m1_t acc = __riscv_vfmv_s_f_f16m1(x[0], 1);
    for (size_t i = 0; i < n;) {
        size_t vl = __riscv_vsetvl_e16m8(n - i);
        vfloat16m8_t v = __riscv_vle16_v_f16m8(x + i, vl);
        acc = __riscv_vfredmax_vs_f16m8_f16m1(v, acc, vl);
        i += vl;
    }
    return __riscv_vfmv_f_s_f16m1_f16(acc);
}

```

## copy

```text
softhier/any/copy: copy_1d on idma: flex_dma_async_1d(dst, src, bytes)
  verified on GVSoC pulp.chips.soft_hier_old.flex_cluster
#include "flex_dma_pattern.h"
// issue a copy of `bytes` contiguous bytes from src to dst; every core of the cluster calls it, the DMA core issues
void alloy_copy_1d(uint64_t dst, uint64_t src, size_t bytes) {
    if (flex_is_dm_core()) flex_dma_async_1d(dst, src, bytes);
}
// wait on=idma: every core calls it; the DMA core waits for its transfers, then the cluster's cores meet
void alloy_wait_idma(void) {
    if (flex_is_dm_core()) flex_dma_async_wait_all();
    flex_intra_cluster_sync();
}

softhier/any/copy: copy_2d on idma: flex_dma_async_2d(dst, src, row_bytes, dst_stride, src_stride, rows)
  verified on GVSoC pulp.chips.soft_hier_old.flex_cluster
  note: row_bytes is one row's bytes, not the total; the strides are bytes from one row's start to the next on each side
#include "flex_dma_pattern.h"
// issue a copy of `rows` rows of `row_bytes` bytes, row r from src + r * src_stride to dst + r * dst_stride (bytes);
// every core of the cluster calls it, the DMA core issues
void alloy_copy_2d(uint64_t dst, uint64_t src, size_t row_bytes, size_t dst_stride, size_t src_stride, size_t rows) {
    if (flex_is_dm_core()) flex_dma_async_2d(dst, src, row_bytes, dst_stride, src_stride, rows);
}
// issue a copy of `bytes` contiguous bytes; the 2D copy's check also runs it
void alloy_copy_1d(uint64_t dst, uint64_t src, size_t bytes) {
    if (flex_is_dm_core()) flex_dma_async_1d(dst, src, bytes);
}
// wait on=idma: every core calls it; the DMA core waits for its transfers, then the cluster's cores meet
void alloy_wait_idma(void) {
    if (flex_is_dm_core()) flex_dma_async_wait_all();
    flex_intra_cluster_sync();
}

```

## wait

```text
softhier/any/wait: wait_idma on idma: flex_dma_async_wait_all()
  verified on GVSoC pulp.chips.soft_hier_old.flex_cluster (inside the copy_1d program)
#include "flex_dma_pattern.h"
// wait on=idma: every core calls it; the DMA core waits for its transfers, then the cluster's cores meet
void alloy_wait_idma(void) {
    if (flex_is_dm_core()) flex_dma_async_wait_all();
    flex_intra_cluster_sync();
}

softhier/f16/wait: wait_redmule on redmule: flex_redmule_wait()
  verified on GVSoC pulp.chips.soft_hier_old.flex_cluster (inside the mma program): max rel error 0.00022
#include "flex_runtime.h"
#include "flex_redmule.h"
// wait on=redmule: every core calls it; core 0 waits for the product, then the cluster's cores meet
void alloy_wait_redmule(void) {
    if (flex_is_first_core()) flex_redmule_wait();
    flex_intra_cluster_sync();
}

```

## mma

```text
softhier/f16/mma: mma on redmule: flex_redmule_config(m, k, n); flex_redmule_trigger(a_off, b_off, c_off, REDMULE_FP_16)
  verified on GVSoC pulp.chips.soft_hier_old.flex_cluster: max rel error 0.00022
#include "flex_runtime.h"
#include "flex_redmule.h"
// issue c (m x n) += a (m x k) * b (k x n), f16, row-major, at TCDM offsets a_off, b_off, c_off; every core of the
// cluster calls it, core 0 (the first core) drives RedMulE
void alloy_mma_f16(uint32_t a_off, uint32_t b_off, uint32_t c_off, uint16_t m, uint16_t n, uint16_t k) {
    if (flex_is_first_core()) {
        flex_redmule_config(m, k, n);
        flex_redmule_trigger(a_off, b_off, c_off, REDMULE_FP_16);
    }
}
// wait on=redmule: every core calls it; core 0 waits for the product, then the cluster's cores meet
void alloy_wait_redmule(void) {
    if (flex_is_first_core()) flex_redmule_wait();
    flex_intra_cluster_sync();
}

```

## barrier

```text
softhier/any/barrier: barrier_cluster on cluster: flex_intra_cluster_sync()
  verified on GVSoC pulp.chips.soft_hier_old.flex_cluster
#include "flex_runtime.h"
// the cores of one cluster meet: TCDM writes before it are seen by every core of the cluster after it
void alloy_barrier_cluster(void) {
    flex_intra_cluster_sync();
}

softhier/any/barrier: barrier_global on cluster: flex_global_barrier_xy()
  verified on GVSoC pulp.chips.soft_hier_old.flex_cluster
  note: flex_barrier_xy_init() runs once at the start of main, before the first global barrier (the SDK's program frame)
#include "flex_runtime.h"
// every core of every cluster meets: TCDM writes before it, in any cluster, are seen after it (other clusters'
// TCDM through iDMA from remote_cid(cid, offset))
void alloy_barrier_global(void) {
    flex_global_barrier_xy();
}

```

## Asked

What `ask` answers beyond the rows: the waits, the barriers, and a gemm tile plan.

```text
ask softhier wait on=idma: feasible on idma; check: run GVSoC pulp.chips.soft_hier_old.flex_cluster, SoftHier v1 inside the copy_1d program
  idma: flex_dma_async_wait_all()
  cluster: flex_intra_cluster_sync()
  setup arch: python -m alloy.isa.softhier arch > alloy_v1.py; python $SOFTHIER_SDK/utilities/config.py alloy_v1.py --output-dir $SOFTHIER_SDK/runtime/runtime/include  (the SDK headers include flex_cluster_arch.h from their own folder, so the v1 header replaces the SDK's there)
  setup headers: riscv_vector.h from the GCC 14 toolchain; flex_*.h from $SOFTHIER_SDK/runtime/runtime/include (https://github.com/pulp-platform/softhier-sdk.git c32f3eba212e5f44e9a65610836991729c0c58ce)
  setup build: riscv32-unknown-elf-gcc -mabi=ilp32d -mcmodel=medlow -march=rv32imafdv_zfh_zvfh -O3 -ffast-math -fno-builtin -fno-tree-vectorize -fno-common -ffunction-sections -I $SOFTHIER_SDK/runtime/runtime/include -c alloy.c -o alloy.o
  setup program: the SDK headers define their functions (not static): put the code in the file with main (the SDK frame: flex_barrier_xy_init(); flex_global_barrier_xy(); ...; flex_eoc(0)), then riscv32-unknown-elf-gcc -I $SOFTHIER_SDK/runtime/runtime/include -T $SOFTHIER_SDK/runtime/runtime/flex_memory.ld -nostartfiles -mabi=ilp32d -mcmodel=medlow -march=rv32imafdv_zfh_zvfh -O3 -ffast-math -fno-builtin -fno-tree-vectorize -fno-common -ffunction-sections -Wl,--gc-sections -o softhier.elf $SOFTHIER_SDK/runtime/runtime/flex_start.s program.c
  setup run: SOFTHIER_ARCH_FILE=alloy_v1.py gvsoc --target=pulp.chips.soft_hier_old.flex_cluster --binary softhier.elf run
  note: the iDMA transfers the cluster's DMA core issued have landed
#include "flex_dma_pattern.h"
// wait on=idma: every core calls it; the DMA core waits for its transfers, then the cluster's cores meet
void alloy_wait_idma(void) {
    if (flex_is_dm_core()) flex_dma_async_wait_all();
    flex_intra_cluster_sync();
}


ask softhier wait on=redmule: feasible on redmule; check: run GVSoC pulp.chips.soft_hier_old.flex_cluster, SoftHier v1 inside the mma program, max rel error 0.00022
  redmule: flex_redmule_wait()
  cluster: flex_intra_cluster_sync()
  note: RedMulE has written the product into c
#include "flex_runtime.h"
#include "flex_redmule.h"
// wait on=redmule: every core calls it; core 0 waits for the product, then the cluster's cores meet
void alloy_wait_redmule(void) {
    if (flex_is_first_core()) flex_redmule_wait();
    flex_intra_cluster_sync();
}


ask softhier barrier kind=cluster: feasible on cluster; check: run GVSoC pulp.chips.soft_hier_old.flex_cluster, SoftHier v1
  cluster: flex_intra_cluster_sync()
#include "flex_runtime.h"
// the cores of one cluster meet: TCDM writes before it are seen by every core of the cluster after it
void alloy_barrier_cluster(void) {
    flex_intra_cluster_sync();
}


ask softhier barrier kind=global: feasible on cluster; check: run GVSoC pulp.chips.soft_hier_old.flex_cluster, SoftHier v1
  cluster: flex_global_barrier_xy()
  note: flex_barrier_xy_init() runs once at the start of main, before the first global barrier (the SDK's program frame)
#include "flex_runtime.h"
// every core of every cluster meets: TCDM writes before it, in any cluster, are seen after it (other clusters'
// TCDM through iDMA from remote_cid(cid, offset))
void alloy_barrier_global(void) {
    flex_global_barrier_xy();
}


ask softhier copy src=global:f16:64x64 dst=shared:f16:64x64: feasible on idma; check: run GVSoC pulp.chips.soft_hier_old.flex_cluster, SoftHier v1
  idma: alloy_copy_1d(local(offset), hbm_west(node, offset), 8192)
  note: 8192 bytes in one transfer
  note: HBM of v1: hbm_west(node, offset) or hbm_south(node, offset), node 0 or 1; every core calls the function, the DMA core (flex_is_dm_core(), the last) issues
  async: completes on idma: wait on=idma
#include "flex_dma_pattern.h"
// issue a copy of `bytes` contiguous bytes from src to dst; every core of the cluster calls it, the DMA core issues
void alloy_copy_1d(uint64_t dst, uint64_t src, size_t bytes) {
    if (flex_is_dm_core()) flex_dma_async_1d(dst, src, bytes);
}
// wait on=idma: every core calls it; the DMA core waits for its transfers, then the cluster's cores meet
void alloy_wait_idma(void) {
    if (flex_is_dm_core()) flex_dma_async_wait_all();
    flex_intra_cluster_sync();
}


ask softhier mma a=shared:f16:32x64 b=shared:f16:64x32 c=shared:f16:32x32: feasible on redmule; check: run GVSoC pulp.chips.soft_hier_old.flex_cluster, SoftHier v1, max rel error 0.00022
  redmule: flex_redmule_config(32, 64, 32)
  redmule: flex_redmule_trigger(a_off, b_off, c_off, REDMULE_FP_16)
  note: call alloy_mma_f16(a_off, b_off, c_off, 32, 32, 64) on every core of the cluster; RedMulE names the extents M, N (inner), K, so its config is (32, 64, 32); offsets are bytes into the TCDM
  note: c is the accumulator and the result: load it (zero it for c = a b) before the call
  async: completes on redmule: wait on=redmule
#include "flex_runtime.h"
#include "flex_redmule.h"
// issue c (m x n) += a (m x k) * b (k x n), f16, row-major, at TCDM offsets a_off, b_off, c_off; every core of the
// cluster calls it, core 0 (the first core) drives RedMulE
void alloy_mma_f16(uint32_t a_off, uint32_t b_off, uint32_t c_off, uint16_t m, uint16_t n, uint16_t k) {
    if (flex_is_first_core()) {
        flex_redmule_config(m, k, n);
        flex_redmule_trigger(a_off, b_off, c_off, REDMULE_FP_16);
    }
}
// wait on=redmule: every core calls it; core 0 waits for the product, then the cluster's cores meet
void alloy_wait_redmule(void) {
    if (flex_is_first_core()) flex_redmule_wait();
    flex_intra_cluster_sync();
}

```
