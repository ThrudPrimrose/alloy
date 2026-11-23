#include <stdint.h>
#include "compute_kernel_api/common.h"
#include "compute_kernel_api/tile_move_copy.h"
#include "compute_kernel_api/eltwise_unary/eltwise_unary.h"
#include "compute_kernel_api/eltwise_binary.h"
#include "compute_kernel_api.h"

#ifdef TRISC_MATH
// f32 log on SFPU lanes: x = 2^n * m, m in [sqrt(1/2), sqrt(2)), f = m - 1,
// s = f / (2 + f), log x = n ln2 + 2s + s R(s^2).
sfpi_inline sfpi::vFloat alloy_log_f32(sfpi::vFloat x) {
    sfpi::vInt e = sfpi::exexp(x);
    sfpi::vFloat m = sfpi::setexp(x, 127);
    v_if (m > 1.41421356f) {
        m = m * 0.5f;
        e = e + 1;
    }
    v_endif;
    v_if (e < 0) { e = sfpi::setsgn(~e + 1, 1); }
    v_endif;
    sfpi::vFloat n = sfpi::int32_to_float(e, 0);
    sfpi::vFloat f = m - 1.0f;
    sfpi::vFloat d = f + 2.0f;
    sfpi::vFloat r = sfpi::approx_recip(d);
    sfpi::vFloat two = 2.0f;
    r = r * (two - d * r);
    r = r * (two - d * r);
    sfpi::vFloat s = f * r;
    sfpi::vFloat z = s * s;
    sfpi::vFloat c1 = 0.41215285658836365f;
    sfpi::vFloat c0 = 0.6665537357330322f;
    sfpi::vFloat big = z * (c1 * z + c0);
    sfpi::vFloat lo = s * (f - big);
    sfpi::vFloat ln2hi = 0.693145751953125f;
    sfpi::vFloat ln2lo = 1.428606765330187e-06f;
    sfpi::vFloat v = n * ln2hi + (f + (n * ln2lo - lo));
    v_if (x == 0.0f) { v = -std::numeric_limits<float>::infinity(); }
    v_endif;
    v_if (x < 0.0f) { v = std::numeric_limits<float>::quiet_NaN(); }
    v_endif;
    return v;
}

inline void alloy_log_f32_face() {
#pragma GCC unroll 0
    for (int d = 0; d < 8; d++) {
        sfpi::dst_reg[0] = alloy_log_f32(sfpi::dst_reg[0]);
        sfpi::dst_reg++;
    }
}
#endif

namespace NAMESPACE {
void MAIN {
    uint32_t num_tiles = get_arg_val<uint32_t>(0);
    constexpr auto cb_in = tt::CBIndex::c_0;
    constexpr auto cb_out = tt::CBIndex::c_16;
    init_sfpu(cb_in, cb_out);
    for (uint32_t i = 0; i < num_tiles; i++) {
        cb_wait_front(cb_in, 1);
        cb_reserve_back(cb_out, 1);
        tile_regs_acquire();
        copy_tile_to_dst_init_short(cb_in);
        copy_tile(cb_in, 0, 0);
        MATH((llk_math_eltwise_unary_sfpu_init<SfpuType::unused, APPROX>()));
        MATH((_llk_math_eltwise_unary_sfpu_params_<APPROX>(alloy_log_f32_face, 0, (int)VectorMode::RC)));
        tile_regs_commit();
        tile_regs_wait();
        pack_tile(0, cb_out);
        tile_regs_release();
        cb_pop_front(cb_in, 1);
        cb_push_back(cb_out, 1);
    }
}
}  // namespace NAMESPACE
