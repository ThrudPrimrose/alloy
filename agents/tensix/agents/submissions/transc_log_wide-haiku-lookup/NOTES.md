# transc_log_wide: design notes

## Design
- Reader streams one tile per iteration into CB 0. Writer drains CB 16 one tile at a time.
- Compute, per tile, computes out = log(x) in fp32 DST:
  1. `y0 = log_tile(x)` (approximate, tool note: 0.6x log is low-order, relative error large near x = 1).
  2. `e = exp(y0)`, `q = (x - e) / (x + e)`.
  3. `out = y0 + 2q` (one Halley step: cubic convergence of the error in y0; exact to f32 rounding near x = 1).
- DST slots 0..3 (fp32 DST holds 4 tiles). x is copied three times because a copy is the only way into DST.
- config: fp32_dest_acc_en on, unpack_to_dest_fp32 [0] (required for the CB 0 copy in full fp32), approx off, HiFi4 (no effect on SFPU).
- No extra CBs.

## Tool-verified spellings (Alloy, tensix, f32, rows of 2026-11-18)
- `log_tile_init<false>()`, `log_tile<false>(0)` (v06). Note from the tool: rel. error above 0.3 near x = 1 on 0.6x.
- `exp_tile_init()`, `exp_tile(0)`.
- `sub_binary_tile_init()`, `sub_binary_tile(d0, d1, odst)`; `add_binary_tile_init()`, `add_binary_tile(d0, d1, odst)`; `div_binary_tile_init()`, `div_binary_tile(d0, d1, odst)`. SFPU binary rows keep f32.
- `init_sfpu`, `binary_op_init_common`, `namespace NAMESPACE { void MAIN }`: 0.6x scaffolding (tool note). I use `init_sfpu` and omit `binary_op_init_common`.

## Not from the tool (marked `// NOT FROM TOOL` in the sources)
- All data movement: `dataflow_api.h`, `tensor_accessor.h`, `TensorAccessorArgs<N>()`, `TensorAccessor`, `noc_async_read_tile`, `noc_async_write_tile`, `get_tile_size`, `get_read_ptr`, `get_write_ptr`, `noc_async_*_barrier`.
- CB calls: `cb_wait_front`, `cb_reserve_back`, `cb_push_back`, `cb_pop_front`.
- DST sync and pack: `tile_regs_acquire/commit/wait/release`, `pack_tile`.
- `copy_tile_init`, `copy_tile`. The tool gives no copy row ("no checked row covers a tensix copy" for global-to-shared, and no unary copy row).
- Header paths: `compute_kernel_api.h`, `compute_kernel_api/eltwise_unary/exp.h`, `compute_kernel_api/eltwise_binary_sfpu.h`, `compute_kernel_api/tile_move_copy.h`, `compute_kernel_api/common.h`.

## Unsure
- Exact `tensor_accessor.h` include path and whether `TensorAccessorArgs` is spelled this way in 0.63.
- Whether `log_tile` takes `<false>` in 0.63 (tool says yes for v06).
- Whether `div_binary_tile` accuracy holds in approx-off mode (tool gives 6.7e-8 rel error on simulator).
- Whether the 0.63 DST capacity with fp32 acc is 4 tiles (I assume it is, per tt-metal half-sync).
- Performance: per tile, 3 copies, 2 log, 1 exp, 1 div, 4 add/sub. Likely not optimal; correctness first.
- The tool's simulator check for `log_tile` (7.1e-8 rel) disagrees with its own note (rel err > 0.3 near 1). I trust the note and built the correction for it.
- Nothing has been compiled or run.
