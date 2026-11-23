// compute.cpp: fuse_diamond kernel implementation (f32)
// Computes out = (a*a + 1)*(a*a - 1) = a^4 - 1

#include "compute_kernel_api/common.h"
#include "compute_kernel_api/tile_move_copy.h"
#include "compute_kernel_api/eltwise_binary.h"   // for mul_binary_tile, add_binary_tile, sub_binary_tile
#include "compute_kernel_api/eltwise_unary.h"   // for exp_tile

constexpr uint32_t cb_in = 0;
constexpr uint32_t cb_out = 16;
constexpr uint32_t tile_size = 1; // number of tiles

void kernel_main() {
    // runtime args: [num_tiles]
    uint32_t num_tiles = get_arg_val<uint32_t>(0);

    // initialize required SFPU ops for f32 accuracy
    mul_binary_tile_init();
    sub_binary_tile_init();
    exp_tile_init();

    for (uint32_t i = 0; i < num_tiles; ++i) {
        // ----- read input tile -----
        cb_wait_front(cb_in, tile_size);
        uint32_t l1_addr = get_read_ptr(cb_in);
        copy_tile(l1_addr, 0);          // tile register 0 <- input
        cb_pop_front(cb_in, tile_size);

        // ----- compute t = a * a (reg1) -----
        mul_binary_tile(0, 0, 1);

        // ----- compute a^4 = t * t (reg2) -----
        mul_binary_tile(1, 1, 2);

        // ----- generate constant 1.0 tile (reg3) -----
        // zero tile by a - a
        sub_binary_tile(0, 0, 3);
        // exp(0) = 1.0 (SFPU exp is f32 accurate with HiFi4)
        exp_tile(3);

        // ----- compute out = a^4 - 1 (reg4) -----
        sub_binary_tile(2, 3, 4);

        // ----- write output tile -----
        cb_reserve_back(cb_out, tile_size);
        uint32_t out_l1 = get_write_ptr(cb_out);
        copy_tile(4, out_l1);
        cb_push_back(cb_out, tile_size);
    }
}
