#include "tt_metal/tt_metal.hpp"
using namespace tt::tt_metal;

// Writer kernel for transc_log_wide
// Writes output float32 tiles from CB 16 to DRAM.

void kernel_main() {
    // Runtime arguments
    const uint32_t num_tiles = get_arg_val<uint32_t>(0);
    const uint32_t dst_addr  = get_arg_val<uint32_t>(1);

    constexpr uint32_t out_cb = 16;
    constexpr uint32_t tile_bytes = 1024 * sizeof(float);

    for (uint32_t i = 0; i < num_tiles; ++i) {
        // Wait for output tile to be ready
        cb_wait_front(out_cb, 1);
        uint32_t l1_read_addr = get_read_ptr(out_cb);
        uint32_t dram_addr = dst_addr + i * tile_bytes;
        noc_async_write(l1_read_addr, dram_addr, tile_bytes);
        noc_async_write_barrier();
        // Release the tile from CB
        cb_pop_front(out_cb, 1);
    }
}
