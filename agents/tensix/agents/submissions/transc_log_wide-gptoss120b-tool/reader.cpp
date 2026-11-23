#include "tt_metal/tt_metal.hpp"
using namespace tt::tt_metal;

// Reader kernel for transc_log_wide
// Reads input float32 tiles from DRAM into CB 0.

void kernel_main() {
    // Runtime arguments
    const uint32_t num_tiles = get_arg_val<uint32_t>(0);
    const uint32_t src_addr  = get_arg_val<uint32_t>(1);

    // Tile size for a float32 tile (32x32 elements)
    constexpr uint32_t tile_bytes = 1024 * sizeof(float);

    for (uint32_t i = 0; i < num_tiles; ++i) {
        // Reserve space for one tile in CB 0
        cb_reserve_back(0, 1);
        // Destination pointer in L1 (CB) memory
        uint32_t l1_write_addr = get_write_ptr(0);
        // Source address of this tile in DRAM
        uint32_t dram_addr = src_addr + i * tile_bytes;
        // Async read from DRAM to L1
        noc_async_read(dram_addr, l1_write_addr, tile_bytes);
        noc_async_read_barrier();
        // Mark tile as ready for compute
        cb_push_back(0, 1);
    }
}
