#include <stdint.h>
#if __has_include("api/compute/common.h")
#include "api/compute/common.h"
#include "api/compute/tile_move_copy.h"
#include "api/compute/eltwise_unary/eltwise_unary.h"
#include "api/compute/eltwise_unary/binop_with_scalar.h"
#include "api/compute/eltwise_binary_sfpu.h"
#else
#include "compute_kernel_api/common.h"
#include "compute_kernel_api/tile_move_copy.h"
#include "compute_kernel_api/eltwise_unary/eltwise_unary.h"
#include "compute_kernel_api/eltwise_unary/binop_with_scalar.h"
#include "compute_kernel_api/eltwise_binary_sfpu.h"
#endif

// NAMESPACE is defined by older tt-metal builds only.
#ifdef NAMESPACE
namespace NAMESPACE {
#endif

void kernel_main() {
    uint32_t num_tiles = get_arg_val<uint32_t>(0);

    constexpr uint32_t cb_in = 0;
    constexpr uint32_t cb_out = 16;
    constexpr uint32_t one_bits = 0x3f800000;  // 1.0f

    init_sfpu(cb_in, cb_out);

    for (uint32_t i = 0; i < num_tiles; ++i) {
        cb_wait_front(cb_in, 1);
        cb_reserve_back(cb_out, 1);

        tile_regs_acquire();
        copy_tile_to_dst_init_short(cb_in);
        // four copies of a: dst0*dst1 and dst2*dst3 both give t
        copy_tile(cb_in, 0, 0);
        copy_tile(cb_in, 0, 1);
        copy_tile(cb_in, 0, 2);
        copy_tile(cb_in, 0, 3);

        mul_binary_tile_init();
        mul_binary_tile(0, 1, 0);  // t
        mul_binary_tile(2, 3, 2);  // t

        binop_with_scalar_tile_init();
        add_unary_tile(0, one_bits);  // u = t + 1
        sub_unary_tile(2, one_bits);  // v = t - 1

        mul_binary_tile_init();
        mul_binary_tile(0, 2, 0);  // u * v
        tile_regs_commit();

        tile_regs_wait();
        pack_tile(0, cb_out);
        tile_regs_release();

        cb_pop_front(cb_in, 1);
        cb_push_back(cb_out, 1);
    }
}

#ifdef NAMESPACE
}
#endif
