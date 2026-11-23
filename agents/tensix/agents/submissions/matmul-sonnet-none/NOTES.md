# Design
Single core. Reader loads all of B (256 bf16 tiles, 512 KB) into CB1 once, then streams A one tile-row (Kt tiles) at a
time into CB0 (32 tiles, double buffered). Compute waits for B once, never pops it; per A row it computes C in blocks of
4 output tiles (fp32 dest holds 4 tiles per half), loop k outer, jj inner, matmul_tiles(cb0, cb1, k, k*Nt+j0+jj, jj).
Packs to CB16 (8 fp32 tiles) in row-major order; writer writes tile t at index t. Each tile is read from DRAM once.
Config: fp32 dest acc, HiFi2 (bf16 inputs; fidelity error should be well below 1e-2; HiFi4 is the safe fallback).
L1: 512 KB + 64 KB + 32 KB, well under 1.5 MB.

# Unsure API spellings
- Compute entry: I emit `namespace NAMESPACE { void MAIN {...} }` if MAIN is defined, else `void kernel_main()`.
- Includes: `compute_kernel_api/matmul.h` (newer trees use `api/compute/matmul.h`); `dataflow_api.h` assumed to pull in
  TensorAccessor / TensorAccessorArgs.
- `mm_init(cb_a, cb_b, cb_c)` and 5-argument `matmul_tiles(cb_a, cb_b, ia, ib, dst)` (no transpose flag).
- `noc_async_read(accessor.get_noc_addr(id), l1, bytes)` used in place of noc_async_read_tile.
- Newer trees may require `compute_kernel_hw_startup(...)` before mm_init; not used here.
- `get_tile_size(cb)` in kernels, assuming host sets tile size per CB format.
