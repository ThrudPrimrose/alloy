#include <cstdint>
#include "compute_kernel_api/common.h"
#include "compute_kernel_api/tile_move_copy.h"
#include "compute_kernel_api/matmul.h"

namespace NAMESPACE {
void MAIN {
    uint32_t Mt = get_arg_val<uint32_t>(0);
    uint32_t Kt = get_arg_val<uint32_t>(1);
    uint32_t Nt = get_arg_val<uint32_t>(2);

    constexpr auto cb_a = tt::CBIndex::c_0;
    constexpr auto cb_b = tt::CBIndex::c_1;
    constexpr auto cb_c = tt::CBIndex::c_16;

    mm_init(cb_a, cb_b, cb_c);  // 0.6x spelling, tool row v06

    for (uint32_t mt = 0; mt < Mt; ++mt) {
        cb_wait_front(cb_a, Kt);  // A row stays until all nt are done
        for (uint32_t nt = 0; nt < Nt; ++nt) {
            cb_wait_front(cb_b, Kt);
            cb_reserve_back(cb_c, 1);
            tile_regs_acquire();
            for (uint32_t kt = 0; kt < Kt; ++kt) {
                matmul_tiles(cb_a, cb_b, kt, kt, 0, false);
            }
            tile_regs_commit();
            tile_regs_wait();
            pack_tile(0, cb_c);
            tile_regs_release();
            cb_push_back(cb_c, 1);
            cb_pop_front(cb_b, Kt);
        }
        cb_pop_front(cb_a, Kt);
    }
}
}  // namespace NAMESPACE
