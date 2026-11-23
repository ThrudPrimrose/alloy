# Tile matmul, Blackhole, tt-metal 0.63: design notes

## Design
- Output tiles in row-major order (mt, nt). For each, the reader streams kt = 0..Kt-1:
  A tile `mt*Kt+kt` into CB 0 and B tile `kt*Nt+nt` into CB 1, one barrier per pair.
- Compute accumulates the Kt products in one DST tile (f32, `fp32_dest_acc_en`), then packs once into CB 16.
- Writer drains CB 16 in tile order `i*Nt+j`, which matches the host's output index.
- FPU `matmul_tiles` reads bf16 operands directly. Inputs are bf16, so no TF32 rounding on the operands.
- CB 0 and CB 1 are resized to 4 tiles (bf16) so the reader can run one tile pair ahead of the FPU. CB 16 stays at 2 f32 tiles.
- `math_fidelity` HiFi4 (correctness first). `math_approx_mode` false: no SFPU ops.
- `unpack_to_dest_fp32` is empty: the operands never go through DST.

## Performance (not tuned)
- Each A tile is read Nt times and each B tile Mt times (about 16 MB of DRAM reads for 512^3 bf16). A blocked
  schedule that keeps an A row in L1 would cut this; not done, since correctness is the first score.
- Barriers are per tile, so reads and writes do not overlap.

## API spellings I am unsure of (0.63)
- `mm_init(c0, c1, c16)` and `matmul_tiles(c0, c1, 0, 0, 0, false)`: 0.6x spellings from the Alloy tensix `mma` row (v06).
  The 0.8x spelling (`compute_kernel_hw_startup`, `matmul_init`, 5-argument `matmul_tiles`) is not used.
- Kernel scaffolding `namespace NAMESPACE { void MAIN { ... } }` for the compute kernel: from the Alloy tensix note (0.6x).
- Includes: `compute_kernel_api/common.h`, `compute_kernel_api/matmul.h` (compute); `dataflow_api.h` (both data movers).
  I did not include `api/tensor/tensor_accessor.h` explicitly; I assume `dataflow_api.h` pulls in `TensorAccessor`
  and `TensorAccessorArgs`. NOT FROM TOOL.
- `TensorAccessorArgs<a_args.next_compile_time_args_offset()>()` for B's offset. NOT FROM TOOL (chaining method name).
- `get_tile_size(cb)`, `get_read_ptr`, `get_write_ptr`, `noc_async_read_tile`, `noc_async_write_tile`,
  `noc_async_*_barrier`, `TensorAccessor(args, addr, page_size)`: NOT FROM TOOL. Standard dataflow API names as I know them.
- `tile_regs_acquire/commit/wait/release`, `pack_tile(0, cb)`, `tt::CBIndex::c_0`: NOT FROM TOOL, standard 0.6x names.
- `get_arg_val<uint32_t>(i)` in compute kernels: NOT FROM TOOL.
