// writer.cpp: writes output tiles from CB 16 back to DRAM for transc_log_wide kernel
#include "tt_metal/tt_metal.hpp"
using namespace tt::tt_metal;

void kernel_main() {
    // Runtime args: [num_tiles, out_addr]
    const uint32_t num_tiles = get_arg_val<uint32_t>(0);
    const uint32_t out_addr  = get_arg_val<uint32_t>(1);

    constexpr uint32_t cb_out = 16; // CB 16 holds output tiles
    constexpr uint32_t TILE_BYTES = 32 * 32 * sizeof(float);

    for (uint32_t i = 0; i < num_tiles; ++i) {
        // Wait for an output tile to be ready
        cb_wait_front(cb_out, 1);
        // Source address in L1 (the CB buffer)
        uint32_t l1_src = get_read_ptr(cb_out);
        // Destination address in DRAM for the i‑th tile
        uint32_t dram_dst = out_addr + i * TILE_BYTES;
        // Issue async NOC write of one tile
        noc_async_write(l1_src, dram_dst, TILE_BYTES);
        // Ensure write completes before we release the CB entry
        noc_async_write_barrier();
        // Release the tile from the CB
        cb_pop_front(cb_out, 1);
    }
}
