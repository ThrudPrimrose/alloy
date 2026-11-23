# transc_log_wide: design notes

Kernel: out = log(x) for 1024 fp32 tiles, one Tensix core, interleaved DRAM.

## Design
- Reader: one tile per iteration into CB 0 (2-tile CB from the host). Uses `noc_async_read_tile` and a barrier per tile.
- Compute: per tile, `copy_tile` CB 0 -> DEST[0] (fp32), `log_tile` in place, `pack_tile` DEST[0] -> CB 16.
- Writer: one tile per iteration from CB 16 with `noc_async_write_tile` and a barrier per tile.
- config.json: fp32 DEST accumulation on, `unpack_to_dest_fp32: [0]` so the fp32 input reaches DEST without a bf16 pass, `math_approx_mode: false` for the accurate log path. No extra CBs.
- Tolerance: absolute error 1e-5 is needed near x = 1 (ref about 0). Non-approx log is chosen for that reason.
- "Wide" is not exploited: batching 2 to 4 tiles per DEST acquire would need more CB slots than the host gives (2 tiles each), i.e. `extra_cbs`. Not done; the kernel is correct first.

## API spellings I am unsure of
- Compute include paths: `compute_kernel_api/common.h`, `compute_kernel_api/tile_move_copy.h`, `compute_kernel_api/eltwise_unary/eltwise_unary.h`, `compute_kernel_api/eltwise_unary/log.h`.
- Dataflow include: `dataflow_api.h`. The `tensor_accessor.h` include in reader and writer is a guess; in 0.63 it may live under `api/tensor/tensor_accessor.h` or be pulled in by dataflow_api.h.
- `TensorAccessorArgs<0>()` and `TensorAccessor(args, addr, page_size)` constructor order.
- `get_tile_size(cb)`, `get_write_ptr(cb)`, `get_read_ptr(cb)`, `noc_async_read_tile(i, accessor, l1)`, `noc_async_write_tile(i, accessor, l1)`.
- `tt::CBIndex::c_0` / `c_16` naming.
- Compute entry: `void kernel_main()`, as SPEC states. Older examples use `void MAIN`.
- `init_sfpu(icb, ocb)` signature.
- `copy_tile_to_dst_init_short(cb)` (may be `copy_tile_init(cb)` in 0.63).
- `log_tile_init()` / `log_tile(idst)`: I believe the default template is the accurate path, but the template parameter (`fast_and_approx`) is unverified.
- `tile_regs_acquire/commit/wait/release`, `pack_tile(idst, cb)`: standard, but verify the 0.63 names.

## Not verified
Nothing compiled or run. Accuracy of the SFPU log against the 1e-5 absolute bound is unverified.
