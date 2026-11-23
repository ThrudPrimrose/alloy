#include <stdint.h>
#include "compute_kernel_api/common.h"
#include "compute_kernel_api/tile_move_copy.h"
#include "compute_kernel_api/eltwise_unary/eltwise_unary.h"
#include "compute_kernel_api/eltwise_unary/trigonometry.h"
#include "compute_kernel_api/eltwise_binary_sfpu.h"

namespace NAMESPACE {
void MAIN {
    uint32_t num_tiles = get_arg_val<uint32_t>(0);

    constexpr uint32_t cb_b = 0;
    constexpr uint32_t cb_c = 1;
    constexpr uint32_t cb_out = 16;

    unary_op_init_common(cb_b, cb_out);

    for (uint32_t i = 0; i < num_tiles; ++i) {
        cb_wait_front(cb_b, 1);
        cb_wait_front(cb_c, 1);
        tile_regs_acquire();

        copy_tile_to_dst_init_short(cb_b);
        copy_tile(cb_b, 0, 0);
        sin_tile_init();
        sin_tile(0);

        copy_tile_to_dst_init_short(cb_c);
        copy_tile(cb_c, 0, 1);
        cos_tile_init();
        cos_tile(1);

        add_binary_tile_init();
        add_binary_tile(0, 1, 0);

        tile_regs_commit();
        cb_pop_front(cb_b, 1);
        cb_pop_front(cb_c, 1);

        cb_reserve_back(cb_out, 1);
        tile_regs_wait();
        pack_tile(0, cb_out);
        tile_regs_release();
        cb_push_back(cb_out, 1);
    }
}
}  // namespace NAMESPACE
