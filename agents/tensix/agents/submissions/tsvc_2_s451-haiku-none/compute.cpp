// tsvc_2_s451 compute (TRISC): out = sin(b) + cos(c), one 32x32 fp32 tile at a time, SFPU path.
#include "api/compute/common.h"
#include "api/compute/tile_move_copy.h"
#include "api/compute/eltwise_unary/sin.h"
#include "api/compute/eltwise_unary/cos.h"
#include "api/compute/eltwise_binary_sfpu.h"

namespace NAMESPACE {
void MAIN {
    const uint32_t num_tiles = get_arg_val<uint32_t>(0);

    constexpr uint32_t cb_b = 0;
    constexpr uint32_t cb_c = 1;
    constexpr uint32_t cb_out = 16;

    init_sfpu(cb_b, cb_out);

    for (uint32_t i = 0; i < num_tiles; ++i) {
        cb_wait_front(cb_b, 1);
        cb_wait_front(cb_c, 1);
        cb_reserve_back(cb_out, 1);

        tile_regs_acquire();
        copy_tile_init(cb_b);
        copy_tile(cb_b, 0, 0);  // dst0 = b
        copy_tile_init(cb_c);
        copy_tile(cb_c, 0, 1);  // dst1 = c
        sin_tile_init();
        sin_tile(0);            // dst0 = sin(b)
        cos_tile_init();
        cos_tile(1);            // dst1 = cos(c)
        add_binary_tile_init();
        add_binary_tile(0, 1, 0);  // dst0 = sin(b) + cos(c)
        tile_regs_commit();

        tile_regs_wait();
        pack_tile(0, cb_out);
        tile_regs_release();

        cb_push_back(cb_out, 1);
        cb_pop_front(cb_b, 1);
        cb_pop_front(cb_c, 1);
    }
}
}  // namespace NAMESPACE
