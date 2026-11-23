// reader.cpp: reads input tiles from DRAM into CB 0 (float32)
#include "dataflow_api.h"

constexpr uint32_t cb_id = 0; // input CB index
constexpr uint32_t tile_size_bytes = 32 * 32 * 4; // one float32 tile (32x32)

void kernel_main() {
    // runtime args: [num_tiles, in_addr]
    uint32_t num_tiles = get_arg_val<uint32_t>(0);
    uint32_t in_addr   = get_arg_val<uint32_t>(1);

    for (uint32_t i = 0; i < num_tiles; ++i) {
        // reserve one slot in the circular buffer
        cb_reserve_back(cb_id, 1);
        uint32_t l1_write_addr = get_write_ptr(cb_id);
        // issue async read of one tile from DRAM
        noc_async_read(in_addr + i * tile_size_bytes, l1_write_addr, tile_size_bytes);
        noc_async_read_barrier();
        // make the tile available to the compute kernel
        cb_push_back(cb_id, 1);
    }
}
