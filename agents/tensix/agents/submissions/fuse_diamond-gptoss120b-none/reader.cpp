#include "tt_metal/kernels/dataflow_api.h"

// Reader kernel for fuse_diamond elementwise operation.
// Runtime arguments:
//   arg[0] : uint32_t num_tiles - number of tiles to read
//   arg[1] : uint32_t in0_addr - DRAM address of the first input tensor
// Note: Only one input tensor for this kernel.

void kernel_main() {
    // Get runtime arguments
    uint32_t num_tiles = get_arg_val<uint32_t>(0);
    uint32_t in0_addr = get_arg_val<uint32_t>(1);

    // Constants
    constexpr uint32_t cb_id_in0 = 0; // input CB index
    constexpr uint32_t tile_size_bytes = 32 * 32 * 4; // float32 tile (1024 elements)

    // Loop over tiles and read them from DRAM into CB 0
    for (uint32_t i = 0; i < num_tiles; ++i) {
        // Destination address in L1 (CB 0)
        uint32_t l1_write_addr = get_write_ptr(cb_id_in0);
        // Source address in DRAM for this tile
        uint32_t src_addr = in0_addr + i * tile_size_bytes;
        // Issue async read from DRAM to L1
        noc_async_read(src_addr, l1_write_addr, tile_size_bytes);
        // Wait for the read to complete before making the tile visible
        noc_async_read_barrier();
        // Mark one tile as available in the circular buffer
        cb_push_back(cb_id_in0, 1);
    }
}
