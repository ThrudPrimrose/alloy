#include "dataflow_api.h"

// Writer kernel: writes output tiles from CB 16 to DRAM
// Runtime args: [num_tiles, out_addr]

void kernel_main() {
    uint32_t num_tiles = get_arg_val<uint32_t>(0);
    uint64_t out_addr = get_arg_val<uint64_t>(1);

    constexpr uint32_t tile_size_bytes = 32 * 32 * sizeof(float);

    for (uint32_t i = 0; i < num_tiles; ++i) {
        // Wait for a tile to be ready in CB 16
        cb_wait_front(16, 1);
        // Get L1 address of the tile
        uint32_t l1_read_addr = get_read_ptr(16);
        // Destination DRAM address
        uint64_t dst = out_addr + uint64_t(i) * tile_size_bytes;
        // Async write to DRAM
        noc_async_write(l1_read_addr, dst, tile_size_bytes);
        // Ensure write completes
        noc_async_write_barrier();
        // Pop the tile from CB 16
        cb_pop_front(16, 1);
    }
}
