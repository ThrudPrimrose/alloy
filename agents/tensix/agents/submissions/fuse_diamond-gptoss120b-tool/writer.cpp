#include "ttnn/tt_metal/kernels/dataflow.hpp"

// Writer kernel for fuse_diamond
// Runtime args: [num_tiles, out_addr]
// Compile-time args: TensorAccessorArgs for output (not used directly here)

void kernel_main() {
    const uint32_t num_tiles = get_arg_val<uint32_t>(0);
    const uint32_t out_addr  = get_arg_val<uint32_t>(1);
    constexpr uint32_t cb_id_out = tt::CB::c_out0; // CB 16
    constexpr uint32_t tile_size_bytes = 1024 * sizeof(float); // 32x32 float32 tile

    for (uint32_t i = 0; i < num_tiles; ++i) {
        // Pointer to the tile in L1 (already produced by compute kernel)
        uint32_t l1 = get_read_ptr(cb_id_out);
        uint32_t dram_tile_addr = out_addr + i * tile_size_bytes;
        // Async write from L1 to DRAM
        noc_async_write(l1, dram_tile_addr, tile_size_bytes);
        // Ensure the write completes before we recycle the CB slot
        noc_async_write_barrier();
        // Release the tile from the CB
        cb_pop_front(cb_id_out, 1);
    }
}
