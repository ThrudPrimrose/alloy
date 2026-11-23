// transc_log_wide: compute (TRISC). out = log(x), one tile at a time, fp32 end to end.
#include <cstdint>
#include "api/compute/common.h"
#include "api/compute/tile_move_copy.h"
#include "api/compute/eltwise_unary/eltwise_unary.h"
#include "api/compute/eltwise_unary/log.h"

// Runtime args: [num_tiles]
void kernel_main() {
    const uint32_t num_tiles = get_arg_val<uint32_t>(0);

    constexpr uint32_t cb_in0 = tt::CBIndex::c_0;
    constexpr uint32_t cb_out = tt::CBIndex::c_16;

    init_sfpu(cb_in0, cb_out);

    for (uint32_t i = 0; i < num_tiles; ++i) {
        cb_wait_front(cb_in0, 1);
        cb_reserve_back(cb_out, 1);

        tile_regs_acquire();
        copy_tile_init(cb_in0);
        copy_tile(cb_in0, 0, 0);  // unpack CB 0 into DST[0] (unpack_to_dest_fp32 for CB 0)
        log_tile_init();
        log_tile(0);              // DST[0] = ln(DST[0]), SFPU, exact (no approx)
        tile_regs_commit();

        tile_regs_wait();
        pack_tile(0, cb_out);
        tile_regs_release();

        cb_push_back(cb_out, 1);
        cb_pop_front(cb_in0, 1);
    }
}
