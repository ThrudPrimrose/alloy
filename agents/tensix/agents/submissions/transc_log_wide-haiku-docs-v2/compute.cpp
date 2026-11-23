// SPDX-License-Identifier: Apache-2.0
// transc_log_wide: compute (TRISC). out = log(x), one tile at a time.

#include <cstdint>
#include "compute_kernel_api.h"
#include "compute_kernel_api/common.h"
#include "compute_kernel_api/tile_move_copy.h"
#include "compute_kernel_api/eltwise_unary/eltwise_unary.h"

namespace NAMESPACE {
void MAIN {
    const uint32_t n_tiles = get_arg_val<uint32_t>(0);

    constexpr uint32_t cb_in0 = tt::CBIndex::c_0;
    constexpr uint32_t cb_out0 = tt::CBIndex::c_16;

    init_sfpu(cb_in0, cb_out0);
    copy_tile_init(cb_in0);
    // fast_and_approx = false selects the non-approx negative-input handling.
    // The polynomial itself is shared by both paths; see NOTES.md on accuracy.
    log_tile_init<false>();

    for (uint32_t i = 0; i < n_tiles; i++) {
        cb_wait_front(cb_in0, 1);
        cb_reserve_back(cb_out0, 1);

        tile_regs_acquire();
        copy_tile(cb_in0, 0, 0);
        log_tile<false>(0);
        tile_regs_commit();

        tile_regs_wait();
        pack_tile(0, cb_out0);
        tile_regs_release();

        cb_pop_front(cb_in0, 1);
        cb_push_back(cb_out0, 1);
    }
}
}  // namespace NAMESPACE
