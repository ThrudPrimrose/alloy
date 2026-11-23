// Compute (TRISC): C tile (i, j) = sum over k of A(i, k) * B(k, j).
// The partial sums stay in DST (fp32, enabled by fp32_dest_acc_en) for the whole K loop.
#include "compute_kernel_api/common.h"
#include "compute_kernel_api/matmul.h"
#include "compute_kernel_api/pack.h"

void kernel_main() {
    const uint32_t Mt = get_arg_val<uint32_t>(0);
    const uint32_t Kt = get_arg_val<uint32_t>(1);
    const uint32_t Nt = get_arg_val<uint32_t>(2);

    constexpr uint32_t cb_a = tt::CBIndex::c_0;
    constexpr uint32_t cb_b = tt::CBIndex::c_1;
    constexpr uint32_t cb_c = tt::CBIndex::c_16;

    mm_init(cb_a, cb_b, cb_c);

    for (uint32_t i = 0; i < Mt; ++i) {
        for (uint32_t j = 0; j < Nt; ++j) {
            tile_regs_acquire();
            for (uint32_t k = 0; k < Kt; ++k) {
                cb_wait_front(cb_a, 1);
                cb_wait_front(cb_b, 1);
                matmul_tiles(cb_a, cb_b, 0, 0, 0);
                cb_pop_front(cb_a, 1);
                cb_pop_front(cb_b, 1);
            }
            tile_regs_commit();

            cb_reserve_back(cb_c, 1);
            tile_regs_wait();
            pack_tile(0, cb_c);
            tile_regs_release();
            cb_push_back(cb_c, 1);
        }
    }
}
