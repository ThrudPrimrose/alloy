// reader: this core's n tiles from its L1 shard of 3 input(s), input k into CB k, 2 per barrier
#include <stdint.h>
#include "dataflow_api.h"

void kernel_main() {
    uint32_t num_tiles = get_arg_val<uint32_t>(0);
    const uint32_t bytes0 = get_tile_size(0);
    const uint64_t s0 = get_noc_addr(get_arg_val<uint32_t>(2));
    const uint32_t bytes1 = get_tile_size(1);
    const uint64_t s1 = get_noc_addr(get_arg_val<uint32_t>(3));
    const uint32_t bytes2 = get_tile_size(2);
    const uint64_t s2 = get_noc_addr(get_arg_val<uint32_t>(4));
    for (uint32_t i = 0; i < num_tiles; i += 2) {
        uint32_t n = num_tiles - i < 2 ? num_tiles - i : 2;
        cb_reserve_back(0, n);
        cb_reserve_back(1, n);
        cb_reserve_back(2, n);
        uint32_t w0 = get_write_ptr(0);
        uint32_t w1 = get_write_ptr(1);
        uint32_t w2 = get_write_ptr(2);
        for (uint32_t t = 0; t < n; ++t) {
            noc_async_read(s0 + (i + t) * bytes0, w0 + t * bytes0, bytes0);
            noc_async_read(s1 + (i + t) * bytes1, w1 + t * bytes1, bytes1);
            noc_async_read(s2 + (i + t) * bytes2, w2 + t * bytes2, bytes2);
        }
        noc_async_read_barrier();
        cb_push_back(0, n);
        cb_push_back(1, n);
        cb_push_back(2, n);
    }
}
