// fuse_diamond compute (TRISC): out = (t + 1) * (t - 1), t = a * a, in fp32 DST.
// DST slots: 0 and 1 hold t and then u and v; slot 2 is scratch. Three slots fit fp32 half-sync DST.
#include "api/compute/common.h"
#include "api/compute/tile_move_copy.h"
#include "api/compute/eltwise_binary_sfpu.h"
#include "api/compute/eltwise_unary/binop_with_scalar.h"

constexpr uint32_t cb_in0 = 0;
constexpr uint32_t cb_out = 16;
constexpr uint32_t ONE_F32 = 0x3F800000u;      // bit pattern of  1.0f
constexpr uint32_t NEG_ONE_F32 = 0xBF800000u;  // bit pattern of -1.0f

void kernel_main() {
    const uint32_t num_tiles = get_arg_val<uint32_t>(0);

    compute_kernel_hw_startup(cb_in0, cb_out);

    for (uint32_t i = 0; i < num_tiles; ++i) {
        cb_wait_front(cb_in0, 1);
        cb_reserve_back(cb_out, 1);
        tile_regs_acquire();

        // dst0 = a, dst1 = a, then dst0 = a * a = t.
        copy_tile_init(cb_in0);
        copy_tile(cb_in0, 0, 0);
        copy_tile(cb_in0, 0, 1);
        mul_binary_tile_init();
        mul_binary_tile(0, 1, 0);

        // dst1 = a, dst2 = a, then dst1 = a * a = t (second copy of t).
        copy_tile_init(cb_in0);
        copy_tile(cb_in0, 0, 1);
        copy_tile(cb_in0, 0, 2);
        mul_binary_tile_init();
        mul_binary_tile(1, 2, 1);

        // u = t + 1 in dst0, v = t - 1 in dst1 (subtract via adding -1.0f).
        add_unary_tile_init();
        add_unary_tile(0, ONE_F32);
        add_unary_tile(1, NEG_ONE_F32);

        // out = u * v in dst0.
        mul_binary_tile_init();
        mul_binary_tile(0, 1, 0);

        tile_regs_commit();
        tile_regs_wait();
        pack_tile(0, cb_out);
        tile_regs_release();

        cb_push_back(cb_out, 1);
        cb_pop_front(cb_in0, 1);
    }
}
