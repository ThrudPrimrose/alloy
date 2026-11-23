#include "tt_metal/kernels/dataflow_api.h"

// Writer kernel for fuse_diamond elementwise operation.
// Runtime arguments:
//   arg[0] : uint32_t num_tiles - number of tiles to write
//   arg[1] : uint32_t out_addr - DRAM address of output tensor

void kernel_main() {
    uint32_t num_tiles = get_arg_val<uint32_t>(0);
    uint32_t out_addr = get_arg_val<uint32_t>(1);

    constexpr uint32_t cb_id_out = 16; // output CB
    constexpr uint32_t tile_size_bytes = 32 * 32 * 4; // float32 tile

    for (uint32_t i = 0; i < num_tiles; ++i) {
        // Wait for output tile to be ready in CB 16
        cb_wait_front(cb_id_out, tile_size_bytes);
        // Get L1 address of tile
        uint32_t l1_addr = get_read_ptr(cb_id_out);
        // Destination DRAM address
        uint32_t dst_addr = out_addr + i * tile_size_bytes;
        // Async write to DRAM
        noc_async_write(l1_addr, dst_addr, tile_size_bytes);
        noc_async_write_barrier();
        // Release tile from CB
        cb_pop_front(cb_id_out, tile_size_bytes);
    }
}
