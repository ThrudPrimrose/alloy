#include <cstdint>
#include "compute_kernel_api/common.h"
#include "compute_kernel_api/tile_move_copy.h"
#include "compute_kernel_api/eltwise_unary/eltwise_unary.h"
#include "compute_kernel_api/eltwise_binary.h"
#include "compute_kernel_api/eltwise_binary_sfpu.h"
#include "compute_kernel_api/eltwise_unary/fill.h"  // NOT FROM TOOL

namespace NAMESPACE {
void MAIN {
    uint32_t num_tiles = get_arg_val<uint32_t>(0);
    constexpr auto c0 = tt::CBIndex::c_0;
    constexpr auto c16 = tt::CBIndex::c_16;
    init_sfpu(c0, c16);
    for (uint32_t i = 0; i < num_tiles; ++i) {
        cb_reserve_back(c16, 1);
        tile_regs_acquire();
        cb_wait_front(c0, 1);
        copy_tile_to_dst_init_short(c0);
        copy_tile(c0, 0, 0);          // DST0 = a
        mul_binary_tile_init();
        mul_binary_tile(0, 0, 0);     // DST0 = t = a*a
        fill_tile_init();             // NOT FROM TOOL
        fill_tile(1, 1.0f);           // NOT FROM TOOL: DST1 = 1
        add_binary_tile_init();
        add_binary_tile(0, 1, 2);     // DST2 = u = t + 1
        sub_binary_tile_init();
        sub_binary_tile(0, 1, 3);     // DST3 = v = t - 1
        mul_binary_tile_init();
        mul_binary_tile(2, 3, 2);     // DST2 = u * v
        tile_regs_commit();
        tile_regs_wait();
        pack_tile(2, c16);
        cb_pop_front(c0, 1);
        tile_regs_release();
        cb_push_back(c16, 1);
    }
}
}  // namespace NAMESPACE
