#include <cstdint>
#include "compute_kernel_api.h"
#include "compute_kernel_api/common.h"
#include "compute_kernel_api/tile_move_copy.h"
#include "compute_kernel_api/eltwise_unary/eltwise_unary.h"

#ifdef TRISC_MATH
#include "sfpi.h"
#include "ckernel_sfpu_recip.h"

namespace ckernel {
namespace sfpu {

// Accurate fp32 ln(x) for x > 0: x = 2^e * m, m folded into [sqrt(1/2), sqrt(2)),
// ln(m) = 2*atanh(s), s = (m-1)/(m+1), odd series up to s^9.
inline void accurate_log_body() {
    vFloat in = dst_reg[0];
    vFloat m = setexp(in, 127);
    vInt ex = exexp(in);
    v_if(ex < 0) { ex = setsgn(~ex + 1, 1); }
    v_endif;
    vFloat e = int32_to_float(ex, 0);
    v_if(m >= 1.41421356f) {
        m = setexp(m, 126);
        e = e + 1.0f;
    }
    v_endif;
    vFloat f = m - 1.0f;
    vFloat d = m + 1.0f;
    vFloat s = f * sfpu_reciprocal<false>(d);
    vFloat s2 = s * s;
    vFloat p = s2 * 0.111111111f + 0.142857143f;
    p = p * s2 + 0.2f;
    p = p * s2 + 0.333333333f;
    p = p * s2 + 1.0f;
    vFloat r = (s + s) * p;
    dst_reg[0] = e * 0.693147181f + r;
}

inline void accurate_log() {
#pragma GCC unroll 8
    for (int d = 0; d < 8; d++) {
        accurate_log_body();
        dst_reg++;
    }
}

inline void accurate_log_init() { recip_init<false>(); }

}  // namespace sfpu
}  // namespace ckernel
#endif

namespace NAMESPACE {
void MAIN {
    const uint32_t num_tiles = get_arg_val<uint32_t>(0);
    constexpr uint32_t cb_in = 0;
    constexpr uint32_t cb_out = 16;

    init_sfpu(cb_in, cb_out);
    MATH((llk_math_eltwise_unary_sfpu_init<SfpuType::log, false>(ckernel::sfpu::accurate_log_init)));

    for (uint32_t i = 0; i < num_tiles; i++) {
        cb_wait_front(cb_in, 1);
        cb_reserve_back(cb_out, 1);
        tile_regs_acquire();
        copy_tile(cb_in, 0, 0);
        MATH((_llk_math_eltwise_unary_sfpu_params_<false>(ckernel::sfpu::accurate_log, 0, (int)VectorMode::RC)));
        tile_regs_commit();
        tile_regs_wait();
        pack_tile(0, cb_out);
        tile_regs_release();
        cb_pop_front(cb_in, 1);
        cb_push_back(cb_out, 1);
    }
}
}  // namespace NAMESPACE
