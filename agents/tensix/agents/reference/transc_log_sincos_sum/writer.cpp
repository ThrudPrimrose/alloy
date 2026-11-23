#include <stdint.h>
#include "dataflow_api.h"

void kernel_main() {
    uint32_t num_tiles = get_arg_val<uint32_t>(0);  // 1: this core's partial-sum tile
    uint32_t start = get_arg_val<uint32_t>(1);      // its index in the output: the core's index
    constexpr auto args = TensorAccessorArgs<0>();
    const auto s = TensorAccessor(args, get_arg_val<uint32_t>(2), get_tile_size(16));
    for (uint32_t i = 0; i < num_tiles; ++i) {
        cb_wait_front(16, 1);
        noc_async_write_tile(start + i, s, get_read_ptr(16));
        noc_async_write_barrier();
        cb_pop_front(16, 1);
    }
}
