// reader: this core's tiles start .. start + n - 1 of 1 input(s), input k into CB k, 2 per barrier
#include <stdint.h>
#include "dataflow_api.h"

void kernel_main() {
    uint32_t num_tiles = get_arg_val<uint32_t>(0);
    uint32_t start = get_arg_val<uint32_t>(1);
    constexpr auto args0 = TensorAccessorArgs<0>();
    const uint32_t bytes0 = get_tile_size(0);
    const auto s0 = TensorAccessor(args0, get_arg_val<uint32_t>(2), bytes0);
    for (uint32_t i = 0; i < num_tiles; i += 2) {
        uint32_t n = num_tiles - i < 2 ? num_tiles - i : 2;
        cb_reserve_back(0, n);
        uint32_t w0 = get_write_ptr(0);
        for (uint32_t t = 0; t < n; ++t) {
            noc_async_read_tile(start + i + t, s0, w0 + t * bytes0);
        }
        noc_async_read_barrier();
        cb_push_back(0, n);
    }
}
