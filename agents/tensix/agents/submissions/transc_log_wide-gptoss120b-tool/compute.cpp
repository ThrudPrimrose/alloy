#include "tt_metal/tt_metal.hpp"
#include <cmath>
using namespace tt::tt_metal;

// Compute kernel for transc_log_wide: out = log(in)
// One input CB (0), one output CB (16). All tiles are float32 (1024 elements).

void kernel_main() {
    // Runtime argument: number of tiles to process
    const uint32_t num_tiles = get_arg_val<uint32_t>(0);
    constexpr uint32_t in_cb = 0;
    constexpr uint32_t out_cb = 16;
    constexpr uint32_t elems_per_tile = 1024; // 32x32

    for (uint32_t t = 0; t < num_tiles; ++t) {
        // Wait for an input tile to be available
        cb_wait_front(in_cb, 1);
        // Reserve space for an output tile
        cb_reserve_back(out_cb, 1);

        // Pointers to the input and output tile data in L1
        uint32_t in_l1_addr  = get_read_ptr(in_cb);
        uint32_t out_l1_addr = get_write_ptr(out_cb);

        // Compute log element‑wise
        float *in_ptr  = reinterpret_cast<float *>(in_l1_addr);
        float *out_ptr = reinterpret_cast<float *>(out_l1_addr);
        for (uint32_t i = 0; i < elems_per_tile; ++i) {
            // The reference uses double precision, but the kernel works in fp32 as required.
            out_ptr[i] = std::log(in_ptr[i]);
        }

        // Release the input tile and make the output tile available
        cb_pop_front(in_cb, 1);
        cb_push_back(out_cb, 1);
    }
}
