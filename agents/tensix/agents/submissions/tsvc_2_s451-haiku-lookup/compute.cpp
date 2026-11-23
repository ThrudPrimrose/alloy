// Compute (TRISC): out = sin(b) + cos(c), all on the SFPU so f32 is kept.
// Per tile: copy b to DST[0] and c to DST[1] (both unpacked as f32), sin on DST[0], cos on DST[1],
// add_binary_tile into DST[0], pack DST[0] to CB 16.
#include <cstdint>
#include "compute_kernel_api/common.h"
#include "compute_kernel_api/tile_move_copy.h"
#include "compute_kernel_api/eltwise_unary/trigonometry.h"
#include "compute_kernel_api/eltwise_binary_sfpu.h"

namespace NAMESPACE {
void MAIN {
    const uint32_t num_tiles = get_arg_val<uint32_t>(0);  // NOT FROM TOOL

    constexpr auto cb_b = tt::CBIndex::c_0;
    constexpr auto cb_c = tt::CBIndex::c_1;
    constexpr auto cb_out = tt::CBIndex::c_16;

    init_sfpu(cb_b, cb_out);  // 0.6x scaffolding, NOT FROM TOOL (tool notes it)
    binary_op_init_common(cb_b, cb_c, cb_out);

    for (uint32_t i = 0; i < num_tiles; ++i) {
        cb_wait_front(cb_b, 1);
        cb_wait_front(cb_c, 1);
        cb_reserve_back(cb_out, 1);

        tile_regs_acquire();

        copy_tile_init(cb_b);  // NOT FROM TOOL: copy_tile_init takes the CB
        copy_tile(cb_b, 0, 0);
        copy_tile_init(cb_c);
        copy_tile(cb_c, 0, 1);

        sin_tile_init();
        sin_tile(0);
        cos_tile_init();
        cos_tile(1);

        add_binary_tile_init();
        add_binary_tile(0, 1, 0);

        tile_regs_commit();
        tile_regs_wait();
        pack_tile(0, cb_out);  // NOT FROM TOOL: pack_tile(dst_index, cb)
        tile_regs_release();

        cb_pop_front(cb_b, 1);
        cb_pop_front(cb_c, 1);
        cb_push_back(cb_out, 1);
    }
}
}  // namespace NAMESPACE
