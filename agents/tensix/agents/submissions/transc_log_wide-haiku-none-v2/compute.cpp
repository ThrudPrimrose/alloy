// Compute (TRISC): out = log(x), one tile per iteration.
// Runtime args: [num_tiles]
// CB 0 (fp32, unpacked straight into DEST as fp32) -> DEST[0] -> log_tile -> CB 16 (fp32).

#include <cstdint>
#include "compute_kernel_api/common.h"
#include "compute_kernel_api/tile_move_copy.h"
#include "compute_kernel_api/eltwise_unary/eltwise_unary.h"
#include "compute_kernel_api/eltwise_unary/log.h"  // unsure of exact header name, see NOTES.md

void kernel_main() {
    const uint32_t num_tiles = get_arg_val<uint32_t>(0);

    constexpr uint32_t cb_in0 = tt::CBIndex::c_0;
    constexpr uint32_t cb_out = tt::CBIndex::c_16;

    init_sfpu(cb_in0, cb_out);

    for (uint32_t i = 0; i < num_tiles; ++i) {
        cb_wait_front(cb_in0, 1);
        cb_reserve_back(cb_out, 1);

        tile_regs_acquire();
        copy_tile_to_dst_init_short(cb_in0);
        copy_tile(cb_in0, 0, 0);
        log_tile_init();
        log_tile(0);
        tile_regs_commit();

        tile_regs_wait();
        pack_tile(0, cb_out);
        tile_regs_release();

        cb_pop_front(cb_in0, 1);
        cb_push_back(cb_out, 1);
    }
}
