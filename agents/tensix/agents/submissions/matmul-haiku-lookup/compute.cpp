// Compute (TRISC): C tile (mt, nt) = sum over kt of A tile (mt, kt) x B tile (kt, nt).
// FPU matmul_tiles on bf16 operands, accumulating in f32 DST (fp32_dest_acc_en in config.json).
// Spellings are the tt-metal 0.6x ones (Alloy tensix lookup, v06 rows).
#include <cstdint>
#include "compute_kernel_api/common.h"
#include "compute_kernel_api/matmul.h"

namespace NAMESPACE {
void MAIN {
    const uint32_t Mt = get_arg_val<uint32_t>(0);
    const uint32_t Kt = get_arg_val<uint32_t>(1);
    const uint32_t Nt = get_arg_val<uint32_t>(2);

    constexpr uint32_t cb_a = tt::CBIndex::c_0;
    constexpr uint32_t cb_b = tt::CBIndex::c_1;
    constexpr uint32_t cb_c = tt::CBIndex::c_16;

    mm_init(cb_a, cb_b, cb_c);

    for (uint32_t mt = 0; mt < Mt; ++mt) {
        for (uint32_t nt = 0; nt < Nt; ++nt) {
            tile_regs_acquire();
            for (uint32_t kt = 0; kt < Kt; ++kt) {
                cb_wait_front(cb_a, 1);
                cb_wait_front(cb_b, 1);
                matmul_tiles(cb_a, cb_b, 0, 0, 0, false);
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
}  // namespace NAMESPACE
