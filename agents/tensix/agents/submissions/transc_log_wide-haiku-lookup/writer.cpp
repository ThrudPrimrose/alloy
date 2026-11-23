// transc_log_wide: writer (NCRISC). Drains CB 16 to the DRAM output, one tile at a time.
// NOT FROM TOOL: the Alloy lookup covers no data-movement calls; spellings below are from memory of tt-metal 0.6x.
#include "dataflow_api.h"  // NOT FROM TOOL
#include "tensor_accessor.h"  // NOT FROM TOOL (include path may differ in 0.63)

void kernel_main() {
    // Runtime args (SPEC): [num_tiles, out_addr]
    const uint32_t num_tiles = get_arg_val<uint32_t>(0);
    const uint32_t out_addr = get_arg_val<uint32_t>(1);

    constexpr uint32_t cb_out = tt::CBIndex::c_16;
    const uint32_t tile_bytes = get_tile_size(cb_out);  // NOT FROM TOOL

    // Compile-time args: TensorAccessorArgs of the output.
    constexpr auto out_args = TensorAccessorArgs<0>();  // NOT FROM TOOL
    const auto out = TensorAccessor(out_args, out_addr, tile_bytes);  // NOT FROM TOOL

    for (uint32_t i = 0; i < num_tiles; ++i) {
        cb_wait_front(cb_out, 1);  // NOT FROM TOOL
        noc_async_write_tile(i, out, get_read_ptr(cb_out));  // NOT FROM TOOL
        noc_async_write_barrier();  // NOT FROM TOOL
        cb_pop_front(cb_out, 1);  // NOT FROM TOOL
    }
}
