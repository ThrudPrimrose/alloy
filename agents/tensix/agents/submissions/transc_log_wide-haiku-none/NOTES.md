# transc_log_wide: design notes (no device, not compiled)

Design: standard three-stage elementwise pipeline on one Tensix core, 1024 tiles.

- reader.cpp (BRISC): for each tile, reserve 1 slot in CB 0, read the tile with `noc_async_read_tile` through a
  `TensorAccessor`, barrier, push. The 2-tile CB gives reader/compute overlap.
- compute.cpp (TRISC): per tile, `copy_tile` CB 0 -> DST[0] (fp32 via `unpack_to_dest_fp32` on CB 0), then
  `log_tile(0)` on DST[0], pack to CB 16.
- writer.cpp (NCRISC): for each tile, wait on CB 16, `noc_async_write_tile` through a `TensorAccessor`, barrier, pop.
- config.json: `fp32_dest_acc_en=true`, `math_approx_mode=false` (the accurate SFPU log, needed for the 1e-5 absolute
  term near x = 1), `HiFi4`, `unpack_to_dest_fp32=[0]`, no extra CBs.

Performance choices: per-tile read and write barriers (simple, latency-bound, about 2 tiles in flight). No
extra CBs, because the host contract sizes CB 0 and CB 16 at 2 tiles.

API spellings I am not sure of (from memory of tt-metal 0.63):
- Include paths: `api/dataflow/dataflow_api.h`, `api/tensor/tensor_accessor.h`, `api/compute/common.h`,
  `api/compute/tile_move_copy.h`, `api/compute/eltwise_unary/eltwise_unary.h`, `api/compute/eltwise_unary/log.h`.
  Older trees use `dataflow_api.h` and `compute_kernel_api/...`.
- Kernel entry: `void kernel_main()` for compute too. Older trees use `void MAIN`.
- `log_tile_init()` / `log_tile(idst)`: exact signature and whether a template flag selects the approx path.
- `init_sfpu(icb, ocb)` argument list.
- `TensorAccessor(args, base_addr, page_size)` constructor and `TensorAccessorArgs<offset>()` spelling.
- `noc_async_read_tile` / `noc_async_write_tile` argument order `(id, accessor, l1_addr)`.
- `get_tile_size(cb)`, `get_write_ptr(cb)`, `get_read_ptr(cb)`.
