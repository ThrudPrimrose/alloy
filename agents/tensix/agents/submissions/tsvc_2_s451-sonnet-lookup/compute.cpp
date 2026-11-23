// out = sin(b) + cos(c), fp32 end to end: sin/cos/add on the SFPU, inputs unpacked straight to DST in fp32.
#include <stdint.h>
#include "compute_kernel_api/common.h"
#include "compute_kernel_api/tile_move_copy.h"            // NOT FROM TOOL
#include "compute_kernel_api/eltwise_unary/eltwise_unary.h"  // NOT FROM TOOL (init_sfpu)
#include "compute_kernel_api/eltwise_unary/trigonometry.h"   // from tool: eltwise_unary/trigonometry.h
#include "compute_kernel_api/eltwise_binary_sfpu.h"          // from tool: eltwise_binary_sfpu.h

namespace NAMESPACE {
void MAIN {
    uint32_t num_tiles = get_arg_val<uint32_t>(0);

    constexpr uint32_t cb_b = 0;
    constexpr uint32_t cb_c = 1;
    constexpr uint32_t cb_out = 16;

    init_sfpu(cb_b, cb_out);  // NOT FROM TOOL

    for (uint32_t i = 0; i < num_tiles; ++i) {
        cb_wait_front(cb_b, 1);
        cb_wait_front(cb_c, 1);

        tile_regs_acquire();  // NOT FROM TOOL

        copy_tile_to_dst_init_short(cb_b);  // NOT FROM TOOL
        copy_tile(cb_b, 0, 0);
        sin_tile_init();
        sin_tile(0);

        copy_tile_to_dst_init_short(cb_c);  // NOT FROM TOOL
        copy_tile(cb_c, 0, 1);
        cos_tile_init();
        cos_tile(1);

        add_binary_tile_init();
        add_binary_tile(0, 1, 0);

        tile_regs_commit();  // NOT FROM TOOL

        cb_pop_front(cb_b, 1);
        cb_pop_front(cb_c, 1);

        cb_reserve_back(cb_out, 1);
        tile_regs_wait();  // NOT FROM TOOL
        pack_tile(0, cb_out);  // NOT FROM TOOL
        tile_regs_release();   // NOT FROM TOOL
        cb_push_back(cb_out, 1);
    }
}
}  // namespace NAMESPACE
