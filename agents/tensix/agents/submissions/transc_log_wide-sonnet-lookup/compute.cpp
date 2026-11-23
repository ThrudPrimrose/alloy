// log(x) = y0 + two Halley steps on exp: y <- y + 2 (x - e^y) / (x + e^y).
// y0 is the native log_tile (inaccurate near x = 1 on 0.63, enough as a start).
// DST (fp32): d0 = x, d1 = y, d2 = e^y then x + e^y, d3 = zero then x - e^y.
#include <cstdint>
#include "compute_kernel_api/common.h"
#include "compute_kernel_api/tile_move_copy.h"
#include "compute_kernel_api/eltwise_unary/eltwise_unary.h"
#include "compute_kernel_api/eltwise_unary/exp.h"
#include "compute_kernel_api/eltwise_binary_sfpu.h"
#include "compute_kernel_api.h"

namespace NAMESPACE {
void MAIN {
    uint32_t num_tiles = get_arg_val<uint32_t>(0);
    constexpr uint32_t cb_in = 0;
    constexpr uint32_t cb_out = 16;
    init_sfpu(cb_in, cb_out);
    for (uint32_t t = 0; t < num_tiles; ++t) {
        cb_wait_front(cb_in, 1);
        cb_reserve_back(cb_out, 1);
        tile_regs_acquire();
        copy_tile_to_dst_init_short(cb_in);
        copy_tile(cb_in, 0, 0);
        copy_tile(cb_in, 0, 1);
        cb_pop_front(cb_in, 1);
        log_tile_init();
        log_tile(1);
        sub_binary_tile_init();
        sub_binary_tile(0, 0, 3);  // d3 = 0
        for (int it = 0; it < 2; ++it) {
            add_binary_tile_init();
            add_binary_tile(1, 3, 2);  // d2 = y
            exp_tile_init();
            exp_tile(2);  // d2 = e^y
            sub_binary_tile_init();
            sub_binary_tile(0, 2, 3);  // d3 = x - e
            add_binary_tile_init();
            add_binary_tile(0, 2, 2);  // d2 = x + e
            div_binary_tile_init();
            div_binary_tile(3, 2, 3);  // d3 = r
            add_binary_tile_init();
            add_binary_tile(3, 3, 3);  // d3 = 2r
            add_binary_tile(1, 3, 1);  // d1 = y + 2r
            if (it == 0) {
                sub_binary_tile_init();
                sub_binary_tile(0, 0, 3);  // d3 = 0
            }
        }
        tile_regs_commit();
        tile_regs_wait();
        pack_tile(1, cb_out);
        tile_regs_release();
        cb_push_back(cb_out, 1);
    }
}
}  // namespace NAMESPACE
