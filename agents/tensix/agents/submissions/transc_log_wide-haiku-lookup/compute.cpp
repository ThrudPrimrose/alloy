// transc_log_wide: compute (TRISC). out = log(x), per 32x32 tile, in fp32 DST.
//
// Design: the 0.6x SFPU log_tile is a low-order approximation whose relative error is large near x = 1
// (tool note), and the test tolerance is 1e-5 absolute there. So one Halley step corrects it:
//   y0 = log_tile(x)                      (approximate)
//   e  = exp(y0)
//   q  = (x - e) / (x + e)
//   log(x) = y0 + 2 q                     (Halley: cubic convergence in the error of y0)
// Every op is an SFPU op that works on fp32 in DST (verified rows in the Alloy lookup).
// DST slots: 0 = y0, 1 = x (later x + e), 2 = q, 3 = e. Four slots fit fp32 DST.
#include "compute_kernel_api.h"
#include "compute_kernel_api/common.h"  // NOT FROM TOOL (umbrella header may already cover it)
#include "compute_kernel_api/tile_move_copy.h"  // NOT FROM TOOL
#include "compute_kernel_api/eltwise_unary/exp.h"
#include "compute_kernel_api/eltwise_binary_sfpu.h"

namespace NAMESPACE {
void MAIN {
    // Compile-time / runtime args (SPEC): [num_tiles]
    const uint32_t num_tiles = get_arg_val<uint32_t>(0);

    constexpr auto cb_in = tt::CBIndex::c_0;
    constexpr auto cb_out = tt::CBIndex::c_16;

    init_sfpu(cb_in, cb_out);  // NOT FROM TOOL (0.6x init, per the tool's scaffolding note)

    for (uint32_t i = 0; i < num_tiles; ++i) {
        cb_wait_front(cb_in, 1);  // NOT FROM TOOL
        cb_reserve_back(cb_out, 1);  // NOT FROM TOOL

        tile_regs_acquire();  // NOT FROM TOOL

        // Load x into slots 0, 1 and 3 (the copy is the only way to get CB data into DST).
        copy_tile_init(cb_in);  // NOT FROM TOOL
        copy_tile(cb_in, 0, 0);  // NOT FROM TOOL
        copy_tile(cb_in, 0, 1);  // NOT FROM TOOL
        copy_tile(cb_in, 0, 3);  // NOT FROM TOOL

        // y0 = log(x) in slot 0; slot 3 becomes exp(y0) = e.
        log_tile_init<false>();
        log_tile<false>(0);
        log_tile<false>(3);
        exp_tile_init();
        exp_tile(3);

        // q = (x - e) / (x + e) in slot 2.
        sub_binary_tile_init();
        sub_binary_tile(1, 3, 2);  // slot 2 = x - e
        add_binary_tile_init();
        add_binary_tile(1, 3, 1);  // slot 1 = x + e
        div_binary_tile_init();
        div_binary_tile(2, 1, 2);  // slot 2 = q

        // result = y0 + 2 q.
        add_binary_tile_init();
        add_binary_tile(2, 2, 2);  // slot 2 = 2 q
        add_binary_tile(0, 2, 0);  // slot 0 = y0 + 2 q

        tile_regs_commit();  // NOT FROM TOOL
        tile_regs_wait();  // NOT FROM TOOL
        pack_tile(0, cb_out);  // NOT FROM TOOL
        tile_regs_release();  // NOT FROM TOOL

        cb_pop_front(cb_in, 1);  // NOT FROM TOOL
        cb_push_back(cb_out, 1);  // NOT FROM TOOL
    }
}
}  // namespace NAMESPACE
