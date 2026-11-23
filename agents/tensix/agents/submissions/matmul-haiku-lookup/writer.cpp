// Writer (NCRISC): drains CB 16 (C, f32) to DRAM in tile order i*Nt+j.
#include <cstdint>
#include "dataflow_api.h"

void kernel_main() {
    const uint32_t num_out_tiles = get_arg_val<uint32_t>(0);
    const uint32_t c_addr = get_arg_val<uint32_t>(1);

    constexpr uint32_t cb_c = 16;
    constexpr auto c_args = TensorAccessorArgs<0>();

    const uint32_t c_tile_bytes = get_tile_size(cb_c);
    const auto c = TensorAccessor(c_args, c_addr, c_tile_bytes);

    for (uint32_t i = 0; i < num_out_tiles; ++i) {
        cb_wait_front(cb_c, 1);
        noc_async_write_tile(i, c, get_read_ptr(cb_c));
        noc_async_write_barrier();
        cb_pop_front(cb_c, 1);
    }
}
