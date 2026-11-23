// reader.cpp: reads input tiles from DRAM into CB 0 for transc_log_wide kernel
#include "tt_metal/tt_metal.hpp"
using namespace tt::tt_metal;

// Kernel entry point for a BRISC (RISC-V) reader
void kernel_main() {
    // Runtime args: [num_tiles, in0_addr]
    const uint32_t num_tiles = get_arg_val<uint32_t>(0);
    const uint32_t in0_addr  = get_arg_val<uint32_t>(1);

    constexpr uint32_t cb_id_in0 = 0; // CB 0 holds input tiles
    constexpr uint32_t TILE_BYTES = 32 * 32 * sizeof(float);

    for (uint32_t i = 0; i < num_tiles; ++i) {
        // Reserve space for one tile in the CB
        cb_reserve_back(cb_id_in0, 1);
        // Destination address in L1 (the CB buffer we just reserved)
        uint32_t l1_dst = get_write_ptr(cb_id_in0);
        // Source address in DRAM for the i‑th tile
        uint32_t dram_src = in0_addr + i * TILE_BYTES;
        // Issue async NOC read of one tile
        noc_async_read(dram_src, l1_dst, TILE_BYTES);
        // Ensure the read is complete before the tile is used
        noc_async_read_barrier();
        // Commit the tile to the CB so the compute core can consume it
        cb_push_back(cb_id_in0, 1);
    }
}
