#include "ttnn/tt_metal/kernels/compute_kernel.hpp"

// Compute kernel for fuse_diamond
// Runtime args: [num_tiles]
// CB 0: input a (float32)
// CB 16: output (float32)

constexpr uint32_t cb_id_in0 = tt::CB::c_in0;   // input
constexpr uint32_t cb_id_out = tt::CB::c_out0; // output (CB 16)
constexpr uint32_t TILE_ELEMENTS = 32 * 32;   // 1024 elements per tile

void kernel_main() {
    const uint32_t num_tiles = get_arg_val<uint32_t>(0);

    for (uint32_t t = 0; t < num_tiles; ++t) {
        // Reserve space for output tile
        cb_reserve_back(cb_id_out, 1);
        // Get pointers to input and output tiles in L1
        uint32_t l0 = get_read_ptr(cb_id_in0);
        uint32_t l1 = get_write_ptr(cb_id_out);
        // Treat as float pointers
        float* a = reinterpret_cast<float*>(l0);
        float* out = reinterpret_cast<float*>(l1);
        // Compute per‑element
        for (uint32_t i = 0; i < TILE_ELEMENTS; ++i) {
            float t_val = a[i] * a[i];          // t = a*a
            float u = t_val + 1.0f;              // u = t + 1
            float v = t_val - 1.0f;              // v = t - 1
            out[i] = u * v;                     // out = u * v
        }
        // Signal that we are done with the input tile
        cb_pop_front(cb_id_in0, 1);
        // Publish the output tile
        cb_push_back(cb_id_out, 1);
    }
}
