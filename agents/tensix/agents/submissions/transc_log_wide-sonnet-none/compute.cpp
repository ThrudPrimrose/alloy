#include <stdint.h>
#if __has_include("api/compute/common.h")
#include "api/compute/common.h"
#include "api/compute/tile_move_copy.h"
#include "api/compute/eltwise_unary/eltwise_unary.h"
#include "api/compute/compute_kernel_api.h"
#else
#include "compute_kernel_api/common.h"
#include "compute_kernel_api/tile_move_copy.h"
#include "compute_kernel_api/eltwise_unary/eltwise_unary.h"
#include "compute_kernel_api.h"
#endif

namespace NAMESPACE {
void MAIN {
    uint32_t num_tiles = get_arg_val<uint32_t>(0);
    constexpr uint32_t cb_in = 0;
    constexpr uint32_t cb_out = 16;

    init_sfpu(cb_in, cb_out);
    log_tile_init();

    for (uint32_t i = 0; i < num_tiles; ++i) {
        cb_wait_front(cb_in, 1);
        cb_reserve_back(cb_out, 1);
        tile_regs_acquire();
        copy_tile(cb_in, 0, 0);
        log_tile(0);
        tile_regs_commit();
        tile_regs_wait();
        pack_tile(0, cb_out);
        tile_regs_release();
        cb_pop_front(cb_in, 1);
        cb_push_back(cb_out, 1);
    }
}
}  // namespace NAMESPACE
