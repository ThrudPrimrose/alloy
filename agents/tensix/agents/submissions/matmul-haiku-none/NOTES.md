# Tile matmul (512x512x512, bf16 in, fp32 out), tt-metal 0.63, one Tensix core

## Design
- Output tile (i, j) is computed in one DST accumulation: `tile_regs_acquire`, then `matmul_tiles` for each k,
  then one `pack_tile` to CB 16. Partial sums never leave DST, so there is no intermediate CB or reload.
- Order i, j, k. The reader pushes A(i,k) and B(k,j) together per k; compute pops them in the same order.
- Reader: per k, reserve both CBs, issue both NOC reads, one barrier, push both.
- Writer: waits per output tile, writes, barriers, pops.
- config.json: `fp32_dest_acc_en` true (fp32 output and accumulation), HiFi4 (keeps bf16 products exact enough for
  the 1e-2 Frobenius tolerance), approx off, no unpack-to-dest.
- extra_cbs: CB 0 and CB 1 grown to 8 bf16 tiles each so the reader can run ahead of compute. CB 16 stays at 2 tiles.
- Cost: A is re-read Nt times and B is re-read Mt times (8192 tile reads in total). Accepted for simplicity.

## API spellings I am unsure of (none compiled or run)
- Include paths: `dataflow_api.h` / `tensor_accessor.h` (data movement) and `compute_kernel_api/{common,matmul,pack}.h`
  (compute). Newer trees may want `api/dataflow/dataflow_api.h`, `api/tensor/tensor_accessor.h`, `api/compute/...`.
- Compute entry: `void kernel_main()` used. Older kernels use `void MAIN`.
- `mm_init(cb_a, cb_b, cb_c)` as the init call. Newer trees may use `compute_kernel_hw_startup(...)`.
- `TensorAccessorArgs<0>()`, `.next_compile_time_args_offset()`, `TensorAccessor(args, addr, page_size)`.
- `noc_async_read_tile(id, accessor, l1_addr)`, `noc_async_write_tile(id, accessor, l1_addr)`.
- `get_tile_size(cb)`, `get_write_ptr(cb)`, `get_read_ptr(cb)`, `tt::CBIndex::c_0/c_1/c_16`.
- `matmul_tiles(cb0, cb1, idx0, idx1, dst)` accumulates into DST when called repeatedly without a release.
