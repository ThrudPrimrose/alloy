# fuse_diamond kernels (tt-metal 0.63, Blackhole, one Tensix core)

## Design
- Reader (BRISC) reads tile i of `a` into CB 0 (one tile at a time, barrier before push).
- Compute (TRISC) per tile, all in fp32 DST with SFPU ops:
  - copies `a` three times from CB 0 (CB 0 is popped once, at the end of the tile);
  - `t = a * a` in slot 0 and again in slot 1;
  - `u = t + 1` (slot 0) and `v = t - 1` (slot 1, written as `t + (-1.0f)`);
  - `out = u * v` in slot 0, packed to CB 16.
- Writer (NCRISC) writes tile i of CB 16 to DRAM.
- config: fp32 DST on, approx off, HiFi4 (irrelevant for SFPU ops), `unpack_to_dest_fp32: [0]` so the fp32 input
  reaches DST without a TF32-style truncation. No extra CBs.
- Math is the spec's literal form (t+1)(t-1), not a^4-1. Same value; rounding is fine for the tolerance.

## Performance notes (not tuned, no device)
- Reader and writer barrier per tile; with a 2-tile CB this serialises NoC latency. A later step could batch reads.

## API spellings I am unsure of
- Include paths: `api/dataflow/dataflow_api.h`, `api/tensor/tensor_accessor.h`, `api/compute/common.h`,
  `api/compute/tile_move_copy.h`, `api/compute/eltwise_binary_sfpu.h`, `api/compute/eltwise_unary/binop_with_scalar.h`
  (older trees use `dataflow_api.h` / `compute_kernel_api.h`).
- Compute entry: `void kernel_main()` (I used this) vs `namespace NAMESPACE { void MAIN() }`.
- `compute_kernel_hw_startup(cb_in, cb_out)` (2 args; some versions take 3, or use `init_sfpu(cb_in, cb_out)`).
- `mul_binary_tile(idst0, idst1, odst)` and `mul_binary_tile_init()`.
- `add_unary_tile(idst, float_bits)` and `add_unary_tile_init()`, with the scalar given as a bit pattern.
- `TensorAccessorArgs<0>()` as a constexpr value, `TensorAccessor(args, addr, page_size)`,
  `noc_async_read_tile` / `noc_async_write_tile`, `get_tile_size(cb)`.
- `pack_tile(dst_idx, cb)` without a format reconfig (all CBs are fp32).
