// writer.cpp: writes output tiles from CB 16 to DRAM
#include "dataflow_api.h"

constexpr uint32_t cb_out = 16;
constexpr uint32_t tile_size_bytes = 32 * 32 * 4; // float32 tile size

void kernel_main() {
    // runtime args: [num_tiles, out_addr]
    uint32_t num_tiles = get_arg_val<uint32_t>(0);
    uint32_t out_addr  = get_arg_val<uint32_t>(1);

    for (uint32_t i = 0; i < num_tiles; ++i) {
        // wait for one tile in output CB
        cb_wait_front(cb_out, 1);
        uint32_t l1_read_addr = get_read_ptr(cb_out);
        // async write to DRAM
        noc_async_write(l1_read_addr, out_addr + i * tile_size_bytes, tile_size_bytes);
        noc_async_write_barrier();
        // release tile from CB
        cb_pop_front(cb_out, 1);
    }
}
