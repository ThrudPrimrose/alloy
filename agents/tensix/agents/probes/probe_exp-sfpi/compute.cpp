#include <stdint.h>
#include "compute_kernel_api/common.h"
#include "compute_kernel_api/tile_move_copy.h"
#include "compute_kernel_api/eltwise_unary/eltwise_unary.h"
#include "compute_kernel_api.h"

#ifdef TRISC_MATH
// f32 exp on SFPU lanes for |x| < 87: n = round(x / ln2) by the 1.5 * 2^23 shifter,
// r = x - n ln2 (hi/lo split), p = Taylor degree 7 on |r| <= ln2 / 2, exp x = p * 2^n.
sfpi_inline sfpi::vFloat alloy_exp_f32(sfpi::vFloat x) {
    sfpi::vFloat shifter = 12582912.0f;  // 1.5 * 2^23: t's low mantissa bits hold n
    sfpi::vFloat inv_ln2 = 1.4426950408889634f;
    sfpi::vFloat t = x * inv_ln2 + shifter;
    sfpi::vFloat nf = t - shifter;
    sfpi::vInt n = sfpi::reinterpret<sfpi::vInt>(t) - 0x4B400000;
    sfpi::vFloat ln2hi = 0.693145751953125f;
    sfpi::vFloat ln2lo = 1.428606765330187e-06f;
    sfpi::vFloat r = x - nf * ln2hi;
    r = r - nf * ln2lo;
    sfpi::vFloat p = 1.9841269841269841e-04f;  // 1/7!
    p = p * r + 1.3888888888888889e-03f;
    p = p * r + 8.3333333333333332e-03f;
    p = p * r + 4.1666666666666664e-02f;
    p = p * r + 1.6666666666666666e-01f;
    p = p * r + 0.5f;
    p = p * r + 1.0f;
    p = p * r + 1.0f;
    // p in [0.7, 1.42]: add n to its biased exponent
    return sfpi::setexp(p, sfpi::exexp_nodebias(p) + n);
}

inline void alloy_exp_f32_face() {
#pragma GCC unroll 0
    for (int d = 0; d < 8; d++) {
        sfpi::dst_reg[0] = alloy_exp_f32(sfpi::dst_reg[0]);
        sfpi::dst_reg++;
    }
}
#endif

namespace NAMESPACE {
void MAIN {
    uint32_t num_tiles = get_arg_val<uint32_t>(0);
    init_sfpu(0, 16);
    for (uint32_t i = 0; i < num_tiles; ++i) {
        cb_wait_front(0, 1);
        tile_regs_acquire();
        copy_tile_to_dst_init_short(0);
        copy_tile(0, 0, 0);
        MATH((llk_math_eltwise_unary_sfpu_init<SfpuType::unused, APPROX>()));
        MATH((_llk_math_eltwise_unary_sfpu_params_<APPROX>(alloy_exp_f32_face, 0, (int)VectorMode::RC)));
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
