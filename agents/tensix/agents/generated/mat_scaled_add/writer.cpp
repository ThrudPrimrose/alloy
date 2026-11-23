// writer: n tiles from CB 16 to output tiles start .. start + n - 1 (2 per barrier); a reduction passes n = 1 and start = the core's index
#include <stdint.h>
#include "dataflow_api.h"

void kernel_main() {
    uint32_t num_tiles = get_arg_val<uint32_t>(0);
    uint32_t start = get_arg_val<uint32_t>(1);
    constexpr auto args = TensorAccessorArgs<0>();
    const uint32_t bytes = get_tile_size(16);
    const auto s = TensorAccessor(args, get_arg_val<uint32_t>(2), bytes);
    for (uint32_t i = 0; i < num_tiles; i += 2) {
        uint32_t n = num_tiles - i < 2 ? num_tiles - i : 2;
        cb_wait_front(16, n);
        uint32_t r = get_read_ptr(16);
        for (uint32_t t = 0; t < n; ++t) {
            noc_async_write_tile(start + i + t, s, r + t * bytes);
        }
        noc_async_write_barrier();
        cb_pop_front(16, n);
    }
}
