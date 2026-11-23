# transc_log_wide: design notes

## Design
- Reader (BRISC): reads tile i of input 0 from DRAM into CB 0, one tile at a time, with a barrier per tile. Args `[num_tiles, in0_addr]`, compile args `TensorAccessorArgs<0>`.
- Compute (TRISC): per tile, copies CB 0 to DST[0] in f32, runs a custom SFPU log, packs DST[0] to CB 16. Args `[num_tiles]`.
- Writer (NCRISC): drains CB 16 to DRAM tile i. Args `[num_tiles, out_addr]`, compile args `TensorAccessorArgs<0>`.
- Config: fp32_dest_acc_en true (f32 DST), unpack_to_dest_fp32 [0] (CB 0 copied to DST without bf16 truncation), math_approx_mode false, no extra CBs. CB 16 is f32 from the host, so no unpack flag is needed for it.

## Why not log_tile
The help tool reports that stock `log_tile` on tt-metal 0.63 has absolute error 0.012 to 0.0165 over [1e-3, 1e3]. The tolerance is 1e-5 + 1e-3 |ref|, so the stock call fails near x = 1 (ref near 0). The compute kernel therefore uses the SFPI rung `alloy_log_f32_sfpi` (help tool, measured on the card: max abs error 3.05e-07, max rel error 2.26e-07 on [1e-3, 1e3]). The function body is copied verbatim from the help output.

## API spellings I am unsure of (not verified by compiling)
- Scaffolding: `#include "compute_kernel_api/..."` paths and `namespace NAMESPACE { void MAIN }` are the 0.6x spellings given by the help tool. Reader and writer use `#include "dataflow_api.h"` (0.6x form); I did not confirm that this header also brings in `TensorAccessor` and `TensorAccessorArgs`.
- `TensorAccessor(args, addr, page_size)` with `get_tile_size(cb)` as the page size: 3-argument form assumed.
- `get_arg_val<uint32_t>(i)` in the compute kernel: assumed to work the same as in the dataflow kernels.
- `init_sfpu(cb_in, cb_out)`: argument form assumed.
- `copy_tile_init(cb_in)`: I pass the CB index. In some 0.6x revisions `copy_tile_init()` takes no argument; check this first.
- `copy_tile(cb, tile_idx, dst_idx)`, `pack_tile(dst_idx, cb)`, `tile_regs_acquire/commit/wait/release`, `cb_wait_front`, `cb_reserve_back`, `cb_push_back`, `cb_pop_front`, `get_write_ptr`, `get_read_ptr`, `noc_async_read_tile`, `noc_async_write_tile`, `noc_async_read_barrier`, `noc_async_write_barrier`: standard names from memory, not checked with the help tool.
- `tt::CBIndex::c_0` and `tt::CBIndex::c_16`: assumed to be the constants for CB indices.
- The custom SFPU call relies on macros the help tool uses: `APPROX` (set by the build from `math_approx_mode`), `MATH(...)`, `TRISC_MATH`, and the llk helpers `llk_math_eltwise_unary_sfpu_init`, `_llk_math_eltwise_unary_sfpu_params_`, `VectorMode::RC`, `SfpuType::unused`. These come from the help tool's rung text, not from a checked source file.
- `sfpi_inline`, `sfpi::vFloat`, `v_if` / `v_endif`, `sfpi::dst_reg` and the `sfpi::` helpers (`exexp`, `setexp`, `setsgn`, `int32_to_float`, `approx_recip`): taken from the help tool text.
- `#include <limits>` added for `std::numeric_limits`.
- `math_fidelity` HiFi4 has no effect on the SFPU path; set for completeness.
