#include <stdint.h>
#include "dataflow_api.h"

void kernel_main() {
    uint32_t num_tiles = get_arg_val<uint32_t>(0);
    uint32_t out_addr = get_arg_val<uint32_t>(1);

    constexpr uint32_t cb_out = tt::CBIndex::c_16;
    constexpr auto args = TensorAccessorArgs<0>();
    const uint32_t tile_bytes = get_tile_size(cb_out);
    const auto acc = TensorAccessor(args, out_addr, tile_bytes);

    for (uint32_t i = 0; i < num_tiles; ++i) {
        cb_wait_front(cb_out, 1);
        uint32_t rd = get_read_ptr(cb_out);
        noc_async_write_page(i, acc, rd);
        noc_async_write_barrier();
        cb_pop_front(cb_out, 1);
    }
}
