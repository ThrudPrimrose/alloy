#include "tt_metal/kernels/compute_api.h"
#include "tt_metal/kernels/dataflow_api.h"

// Compute kernel for fuse_diamond elementwise operation.
// Runtime arguments:
//   arg[0] : uint32_t num_tiles - number of tiles to process

void kernel_main() {
    // Runtime arguments
    uint32_t num_tiles = get_arg_val<uint32_t>(0);

    // CB indices
    constexpr uint32_t cb_id_in0 = 0;   // input CB
    constexpr uint32_t cb_id_out = 16;  // output CB

    // Tile dimensions
    constexpr uint32_t tile_w = 32;
    constexpr uint32_t tile_h = 32;
    constexpr uint32_t tile_elements = tile_w * tile_h; // 1024 elements per tile
    constexpr uint32_t tile_size_bytes = tile_elements * 4; // float32

    for (uint32_t t = 0; t < num_tiles; ++t) {
        // Wait until an input tile is available (1 tile)
        cb_wait_front(cb_id_in0, 1);

        // Get pointers to the tile data in L1
        uint32_t l1_in_addr = get_read_ptr(cb_id_in0);
        uint32_t l1_out_addr = get_write_ptr(cb_id_out);

        // Compute per‑element
        for (uint32_t i = 0; i < tile_elements; ++i) {
            float a = *((volatile float*)(l1_in_addr + i * 4));
            float t_val = a * a;           // t = a * a
            float u = t_val + 1.0f;        // u = t + 1
            float v = t_val - 1.0f;        // v = t - 1
            float out = u * v;            // out = u * v  ( = a^4 - 1 )
            *((volatile float*)(l1_out_addr + i * 4)) = out;
        }

        // Release the input tile and make the output tile visible
        cb_pop_front(cb_id_in0, 1);
        cb_push_back(cb_id_out, 1);
    }
}
