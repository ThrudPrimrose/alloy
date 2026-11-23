#include <stdint.h>
#include "dataflow_api.h"

void kernel_main() {
    uint32_t num_tiles = get_arg_val<uint32_t>(0);
    constexpr uint32_t cb = 0;
    constexpr auto args0 = TensorAccessorArgs<0>();
    const auto s0 = TensorAccessor(args0, get_arg_val<uint32_t>(1), get_tile_size(cb));
    for (uint32_t i = 0; i < num_tiles; ++i) {
        cb_reserve_back(cb, 1);
        noc_async_read_tile(i, s0, get_write_ptr(cb));
        noc_async_read_barrier();
        cb_push_back(cb, 1);
    }
}
