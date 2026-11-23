# tsvc_2_s451: design

- Reader (BRISC): per tile, reserves CB 0 (b) and CB 1 (c), issues two `noc_async_read_tile` calls through
  `TensorAccessor`, one read barrier, pushes both CBs. Accessor args: b at offset 0, c at `next_compile_time_args_offset()`.
- Compute (TRISC): per tile, copies b to dst0 and c to dst1 (`unpack_to_dest_fp32` for CB 0 and 1 keeps fp32),
  `sin_tile(0)`, `cos_tile(1)`, `add_binary_tile(0, 1, 0)`, packs dst0 to CB 16, pops inputs.
- Writer (NCRISC): per tile, waits on CB 16, `noc_async_write_tile`, barrier, pops.
- config: fp32 dest accumulation on, approx mode off (sin/cos accuracy matters near zero where the absolute 1e-5
  term applies), HiFi4 (no effect on SFPU ops, kept for safety), no extra CBs. Buffering is the host default of 2 tiles.

## API spellings I am unsure of (no tool to check)

- Include paths: `api/dataflow/dataflow_api.h`, `api/tensor/tensor_accessor.h`, `api/compute/common.h`,
  `api/compute/tile_move_copy.h`, `api/compute/eltwise_unary/sin.h`, `api/compute/eltwise_unary/cos.h`,
  `api/compute/eltwise_binary_sfpu.h`. Older trees use `dataflow_api.h` / `compute_kernel_api/...`.
- Compute entry: `namespace NAMESPACE { void MAIN {...} }`. Could be `void kernel_main()` in 0.63.
- `copy_tile_init(cb)` takes a CB argument; some versions have no argument or use `copy_tile_to_dst_init_short`.
- `init_sfpu(icb, ocb)` as the one-time init.
- `add_binary_tile_init()` / `add_binary_tile(idst0, idst1, odst)` for SFPU add.
- `pack_tile(dst_index, cb)` argument order.
- `get_tile_size(cb)`, `get_write_ptr`, `get_read_ptr`, `noc_async_read_tile`, `noc_async_write_tile` signatures.
- `TensorAccessorArgs<N>()` and `next_compile_time_args_offset()`.
- Writing the CB indices as plain `constexpr uint32_t` instead of `tt::CBIndex::c_0`.
