// Writer (NCRISC): drains CB 16 to the interleaved output buffer, one tile at a time.
// Dataflow calls are NOT FROM TOOL.
#include <cstdint>
#include "dataflow_api.h"

void kernel_main() {
    const uint32_t num_tiles = get_arg_val<uint32_t>(0);  // NOT FROM TOOL
    const uint32_t out_addr = get_arg_val<uint32_t>(1);

    constexpr uint32_t cb_out = tt::CBIndex::c_16;
    constexpr auto out_args = TensorAccessorArgs<0>();

    const uint32_t tile_bytes = get_tile_size(cb_out);  // NOT FROM TOOL
    const auto out_acc = TensorAccessor(out_args, out_addr, tile_bytes);  // NOT FROM TOOL

    for (uint32_t i = 0; i < num_tiles; ++i) {
        cb_wait_front(cb_out, 1);
        noc_async_write_tile(i, out_acc, get_read_ptr(cb_out));
        noc_async_write_barrier();
        cb_pop_front(cb_out, 1);
    }
}
