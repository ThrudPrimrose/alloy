// Reference solution of transc_log_sincos_sum (out = sum(log(x) * cos(t) + sin(t))) under the eval contract:
// one tile of fp32 partial sums. log is Alloy's SFPI rung (log_tile on 0.63 misses f32 by 0.0165); the running
// partial sums stay in CB 24 between tiles, so every add happens in fp32 in DST.
#include <stdint.h>
#include "compute_kernel_api/common.h"
#include "compute_kernel_api/tile_move_copy.h"
#include "compute_kernel_api/eltwise_unary/eltwise_unary.h"
#include "compute_kernel_api/eltwise_unary/trigonometry.h"
#include "compute_kernel_api/eltwise_binary_sfpu.h"
#include "compute_kernel_api.h"

#ifdef TRISC_MATH
// f32 log on SFPU lanes: x = 2^n * m, m in [sqrt(1/2), sqrt(2)), f = m - 1,
// s = f / (2 + f), log x = n ln2 + 2s + s R(s^2) (Alloy rung alloy_log_f32_fast).
sfpi_inline sfpi::vFloat alloy_log_f32(sfpi::vFloat x) {
    sfpi::vInt e = sfpi::exexp(x);          // unbiased exponent
    sfpi::vFloat m = sfpi::setexp(x, 127);  // mantissa in [1, 2)
    v_if (m > 1.41421356f) {
        m = m * 0.5f;
        e = e + 1;
    }
    v_endif;
    // int32_to_float reads sign-magnitude, as in ckernel_sfpu_log.h
    v_if (e < 0) { e = sfpi::setsgn(~e + 1, 1); }
    v_endif;
    sfpi::vFloat n = sfpi::int32_to_float(e, 0);
    sfpi::vFloat f = m - 1.0f;
    sfpi::vFloat d = f + 2.0f;
    // 1/d: hardware estimate plus two Newton steps, d in [1.7, 2.5)
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

// one face: 8 rows of 32 lanes per iteration
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
    constexpr uint32_t cb_t = 0, cb_x = 1, cb_acc = 24, cb_out = 16;
    init_sfpu(cb_t, cb_out);
    for (uint32_t i = 0; i < num_tiles; ++i) {
        cb_wait_front(cb_t, 1);
        cb_wait_front(cb_x, 1);
        tile_regs_acquire();
        copy_tile_to_dst_init_short(cb_x);
        copy_tile(cb_x, 0, 0);
        copy_tile_to_dst_init_short(cb_t);
        copy_tile(cb_t, 0, 1);
        copy_tile(cb_t, 0, 2);
        MATH((llk_math_eltwise_unary_sfpu_init<SfpuType::unused, APPROX>()));
        MATH((_llk_math_eltwise_unary_sfpu_params_<APPROX>(alloy_log_f32_face, 0, (int)VectorMode::RC)));
        cos_tile_init();
        cos_tile(1);
        sin_tile_init();
        sin_tile(2);
        mul_binary_tile_init();
        mul_binary_tile(0, 1, 0);
        add_binary_tile_init();
        add_binary_tile(0, 2, 0);
        if (i > 0) {
            cb_wait_front(cb_acc, 1);
            copy_tile_to_dst_init_short(cb_acc);
            copy_tile(cb_acc, 0, 1);
            add_binary_tile_init();
            add_binary_tile(0, 1, 0);
            cb_pop_front(cb_acc, 1);
        }
        tile_regs_commit();
        cb_pop_front(cb_t, 1);
        cb_pop_front(cb_x, 1);
        uint32_t into = i + 1 < num_tiles ? cb_acc : cb_out;
        cb_reserve_back(into, 1);
        tile_regs_wait();
        pack_tile(0, into);
        tile_regs_release();
        cb_push_back(into, 1);
    }
}
}  // namespace NAMESPACE
