#include <stdint.h>
#include "dataflow_api.h"

void kernel_main() {
    uint32_t num_tiles = get_arg_val<uint32_t>(0);
    constexpr uint32_t cb = 16;
    constexpr auto args = TensorAccessorArgs<0>();
    const auto s = TensorAccessor(args, get_arg_val<uint32_t>(1), get_tile_size(cb));
    for (uint32_t i = 0; i < num_tiles; ++i) {
        cb_wait_front(cb, 1);
        noc_async_write_tile(i, s, get_read_ptr(cb));
        noc_async_write_barrier();
        cb_pop_front(cb, 1);
    }
}
