#include <stdint.h>
#include "compute_kernel_api/common.h"
#include "compute_kernel_api/tile_move_copy.h"
#include "compute_kernel_api/eltwise_unary/eltwise_unary.h"
#include "compute_kernel_api/eltwise_unary/exp.h"
#include "compute_kernel_api/eltwise_binary_sfpu.h"
#include "compute_kernel_api.h"

namespace NAMESPACE {
void MAIN {
    uint32_t num_tiles = get_arg_val<uint32_t>(0);
    init_sfpu(0, 16);
    for (uint32_t i = 0; i < num_tiles; ++i) {
        cb_wait_front(0, 1);
        tile_regs_acquire();
        copy_tile_to_dst_init_short(0);
        copy_tile(0, 0, 0);
        log_tile_init<false>();
        log_tile<false>(0);
        tile_regs_commit();
        cb_pop_front(0, 1);
        cb_reserve_back(16, 1);
        tile_regs_wait();
        pack_tile(0, 16);
        tile_regs_release();
        cb_push_back(16, 1);
    }
}
}  // namespace NAMESPACE
