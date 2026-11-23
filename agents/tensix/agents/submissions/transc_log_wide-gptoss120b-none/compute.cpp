// compute.cpp: compute kernel for transc_log_wide (log per element)
#include "tt_metal/tt_metal.hpp"
#include <cmath>
using namespace tt::tt_metal;

void kernel_main() {
    // Runtime args: [num_tiles]
    const uint32_t num_tiles = get_arg_val<uint32_t>(0);

    constexpr uint32_t cb_in  = 0;   // CB 0 holds input tiles
    constexpr uint32_t cb_out = 16;  // CB 16 holds output tiles
    constexpr uint32_t TILE_ELEMS = 32 * 32; // 1024 elements per tile

    for (uint32_t t = 0; t < num_tiles; ++t) {
        // Wait for an input tile to be ready
        cb_wait_front(cb_in, 1);
        // Reserve space for an output tile
        cb_reserve_back(cb_out, 1);

        // Pointers to the tile data in L1
        uint32_t l1_in  = get_read_ptr(cb_in);
        uint32_t l1_out = get_write_ptr(cb_out);

        // Compute log element‑wise
        for (uint32_t i = 0; i < TILE_ELEMS; ++i) {
            ((float*)l1_out)[i] = logf(((float*)l1_in)[i]);
        }

        // Commit output tile and release input tile
        cb_push_back(cb_out, 1);
        cb_pop_front(cb_in, 1);
    }
}
