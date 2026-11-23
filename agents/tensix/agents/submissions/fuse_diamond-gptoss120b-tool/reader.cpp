#include "ttnn/tt_metal/kernels/dataflow.hpp"

// Reader kernel for fuse_diamond
// Runtime args: [num_tiles, in0_addr]
// Compile-time args: TensorAccessorArgs for input (not used directly here)

void kernel_main() {
    // Get runtime arguments
    const uint32_t num_tiles = get_arg_val<uint32_t>(0);
    const uint32_t src_addr = get_arg_val<uint32_t>(1); // base DRAM address of input tensor
    // Constants
    constexpr uint32_t cb_id_in0 = tt::CB::c_in0; // CB 0
    constexpr uint32_t tile_size_bytes = 1024 * sizeof(float); // 32x32 float32 tile

    // Loop over tiles
    for (uint32_t i = 0; i < num_tiles; ++i) {
        // Reserve space in CB for one tile
        cb_reserve_back(cb_id_in0, 1);
        // Get write pointer in L1 for the tile
        uint32_t l1_write_addr = get_write_ptr(cb_id_in0);
        // Compute DRAM address of current tile
        uint32_t dram_tile_addr = src_addr + i * tile_size_bytes;
        // Async read from DRAM to L1
        noc_async_read(dram_tile_addr, l1_write_addr, tile_size_bytes);
        // Wait for the transfer to complete before making the data visible
        noc_async_read_barrier();
        // Publish the tile to the CB
        cb_push_back(cb_id_in0, 1);
    }
}
