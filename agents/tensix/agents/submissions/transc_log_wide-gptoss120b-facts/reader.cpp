#include "dataflow_api.h"

// Reader kernel: reads input tiles from DRAM into CB 0
// Runtime args: [num_tiles, in_addr]

void kernel_main() {
    // Get runtime arguments
    uint32_t num_tiles = get_arg_val<uint32_t>(0);
    uint64_t in_addr = get_arg_val<uint64_t>(1);

    // Tile size in bytes for a float32 tile (32x32)
    constexpr uint32_t tile_size_bytes = 32 * 32 * sizeof(float);

    // Loop over tiles
    for (uint32_t i = 0; i < num_tiles; ++i) {
        // Read a tile from DRAM into the CB buffer
        uint64_t tile_addr = in_addr + uint64_t(i) * tile_size_bytes;
        // Destination pointer obtained from CB 0
        uint32_t l1_write_addr = get_write_ptr(0);
        // Async read from DRAM
        noc_async_read(tile_addr, l1_write_addr, tile_size_bytes);
        // Ensure the read completes before using the data
        noc_async_read_barrier();
        // Push the tile into CB 0
        cb_push_back(0, 1);
    }
}
