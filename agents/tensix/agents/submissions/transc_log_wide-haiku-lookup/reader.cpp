// transc_log_wide: reader (BRISC). Streams one input tile at a time from DRAM into CB 0.
// NOT FROM TOOL: the Alloy lookup covers no data-movement calls; spellings below are from memory of tt-metal 0.6x.
#include "dataflow_api.h"  // NOT FROM TOOL
#include "tensor_accessor.h"  // NOT FROM TOOL (include path may differ in 0.63)

void kernel_main() {
    // Runtime args (SPEC): [num_tiles, in0_addr]
    const uint32_t num_tiles = get_arg_val<uint32_t>(0);
    const uint32_t in0_addr = get_arg_val<uint32_t>(1);

    constexpr uint32_t cb_in0 = tt::CBIndex::c_0;
    const uint32_t tile_bytes = get_tile_size(cb_in0);  // NOT FROM TOOL

    // Compile-time args: TensorAccessorArgs of input 0 only (one input in this kernel).
    constexpr auto in0_args = TensorAccessorArgs<0>();  // NOT FROM TOOL
    const auto in0 = TensorAccessor(in0_args, in0_addr, tile_bytes);  // NOT FROM TOOL

    for (uint32_t i = 0; i < num_tiles; ++i) {
        cb_reserve_back(cb_in0, 1);  // NOT FROM TOOL
        noc_async_read_tile(i, in0, get_write_ptr(cb_in0));  // NOT FROM TOOL
        noc_async_read_barrier();  // NOT FROM TOOL
        cb_push_back(cb_in0, 1);  // NOT FROM TOOL
    }
}
