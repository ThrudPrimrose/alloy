// reader: this core's n tiles from its L1 shard of 1 input(s), input k into CB k, 4 per barrier
#include <stdint.h>
#include "dataflow_api.h"

void kernel_main() {
    uint32_t num_tiles = get_arg_val<uint32_t>(0);
    const uint32_t bytes0 = get_tile_size(0);
    const uint64_t s0 = get_noc_addr(get_arg_val<uint32_t>(2));
    for (uint32_t i = 0; i < num_tiles; i += 4) {
        uint32_t n = num_tiles - i < 4 ? num_tiles - i : 4;
        cb_reserve_back(0, n);
        uint32_t w0 = get_write_ptr(0);
        for (uint32_t t = 0; t < n; ++t) {
            noc_async_read(s0 + (i + t) * bytes0, w0 + t * bytes0, bytes0);
        }
        noc_async_read_barrier();
        cb_push_back(0, n);
    }
}
