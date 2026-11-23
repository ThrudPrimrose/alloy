# SoftHier v1 kernels: task spec

You write one C kernel for SoftHier v1, simulated by GVSoC (model `pulp.chips.soft_hier_old.flex_cluster`) and built
with the softhier-sdk runtime and the GCC 14 RISC-V toolchain. The host side is fixed and written by us (`host.py`):
it puts the task's inputs in HBM, calls your kernel on every core of every cluster, times the call, reads the output
back, and compares it with a float64 reference. The `run` tool runs exactly that judge on your folder.

## The machine

- 2 x 2 clusters (cluster id 0 to 3, `flex_get_cluster_id()`), 3 Snitch RISC-V cores each (`flex_get_core_id()` 0 to
  2). Core 0 drives the cluster's Spatz vector unit (RVV 1.0, VLEN 256; GCC 14's `riscv_vector.h`) and its RedMulE
  matrix unit; the last core (`flex_is_dm_core()`) issues iDMA transfers. Every core runs scalar C (built with
  `-march=rv32imafdv_zfh_zvfh -O3 -ffast-math`, linked with `-lm`).
- Each cluster has 1 MiB of TCDM at `local(offset)`, offset 0 to 0xFFFFF. A core loads and stores only its own
  cluster's TCDM; HBM and other clusters' TCDM are reached through iDMA alone (`flex_dma_async_1d(dst, src, bytes)` and
  the other `flex_dma_*` calls of the SDK headers, then `flex_dma_async_wait_all()` on the DM core). A core's own load or store to HBM is out
  of bounds.
- Synchronization: `flex_intra_cluster_sync()` (all 3 cores of one cluster), `flex_global_barrier_xy()` (every core
  of every cluster).

## Deliverables (in your folder)

- `kernel.c`: the kernel, with any includes and helpers it needs, defining

      void alloy_kernel(uint64_t in0, uint64_t in1, uint64_t in2, uint64_t out, uint32_t n);

  The host includes `flex_runtime.h`, `flex_printf.h` and `flex_dma_pattern.h` before your code, and pastes your code
  into its program (the SDK headers define their functions, so there is one translation unit). Do not define `main`,
  and do not print lines that start with `ALLOY ` (the host reads the output from them).
- `NOTES.md`: your design in a few lines.

## The fixed host contract

- Every core of every cluster calls `alloy_kernel` once, after a global barrier, with the same arguments. The host
  times from that barrier to the global barrier after every core returned. Return only when your cluster's part of
  the output is in HBM (wait for your iDMA transfers).
- `in0`, `in1`, `in2`: the HBM addresses of the task's inputs, in the order `tasks.json` lists them (0 for a missing
  one). `out`: the HBM address of the output. Pass them to iDMA as they are.
- A map task: every input is `n` = 65,536 float32 elements; the output is `n` float32 elements at `out`. When the
  output has the name of an input (for example `B = B + 2.0 * A`), `out` is that input's address: you overwrite it.
- A reduce task (`sum(e)`): `out` holds 4 float32 values, one per cluster: cluster c writes its partial sum to
  `out + 4 * c`; the host adds the four in float64. (Any split of the terms is fine, as long as the four values add
  up to the sum.)
- The GEMM task `gemm64`: `C += A x B` with A, B, C 64 x 64 row-major f16 (`_Float16`), `n` = 64; `in0` = A, `in1` =
  B, `out` = C, which holds C's initial values.
- Inputs: drawn uniformly from each input's range in `tasks.json` (seeded), float32 for map and reduce, f16 for the
  GEMM.
- Tolerance: map: |got - ref| <= 1e-5 + 1e-3 |ref| for every element, where ref is the float64 program on the float32
  inputs; reduce: the same bound on the sum plus 2^-23 sqrt(65,536) |ref| (fp32 reassociation); GEMM: max |got - ref|
  / max |ref| <= 1e-3.
- Time: the simulated time of the call (GVSoC's performance counter, ns), compared with our scalar reference
  (`python3 host.py reference TASK DIR` writes it): plain C loops on cores 0 and 1 of every cluster, the DM core
  moving each cluster's quarter of the data. A run is deterministic.

## Eval tasks (tasks.json)

Each task is one bench kernel as a program over whole arrays (`name = expression` lines; a name a line assigns and
the task does not output is a per-element temporary; `sum(e)` adds every element of `e` into one value), the same
tasks as the Tenstorrent study, plus `gemm64`, the paper's running example (the 64 x 64 x 64 tile, on RedMulE or
otherwise).
