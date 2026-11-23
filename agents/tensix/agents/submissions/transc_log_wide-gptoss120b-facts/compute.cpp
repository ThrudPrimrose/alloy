#include "compute_kernel_api/common.h"
#include "compute_kernel_api/tile_move_copy.h"
#include "compute_kernel_api/eltwise_unary/eltwise_unary.h"
#include "compute_kernel_api/eltwise_binary.h"
#include "compute_kernel_api/eltwise_unary/log.h"
#include <limits>

// NOTE: This kernel uses the custom SFPU log implementation (alloy_log_f32_sfpi) from FACTS.md
// to achieve full FP32 accuracy on Blackhole with tt-metal 0.63.

#ifdef TRISC_MATH
// Inline SFPU log implementation (as in FACTS.md)
static inline sfpi::vFloat alloy_log_f32(sfpi::vFloat x) {
    sfpi::vInt e = sfpi::exexp(x);          // unbiased exponent
    sfpi::vFloat m = sfpi::setexp(x, 127);  // mantissa in [1, 2)
    v_if (m > 1.41421356f) {
        m = m * 0.5f;
        e = e + 1;
    }
    v_endif;
    // make exponent positive for conversion
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

static inline void alloy_log_f32_face() {
#pragma GCC unroll 0
    for (int d = 0; d < 8; ++d) {
        sfpi::dst_reg[0] = alloy_log_f32(sfpi::dst_reg[0]);
        sfpi::dst_reg++;
    }
}
#endif // TRISC_MATH

void kernel_main() {
    uint32_t num_tiles = get_arg_val<uint32_t>(0);

    // Ensure input tiles are present in CB 0
    cb_wait_front(0, num_tiles);

    for (uint32_t i = 0; i < num_tiles; ++i) {
        // Pop tile from CB 0 into DST register 0
        cb_pop_front(0, 1);
        // Apply custom SFPU log to the tile
        MATH((_llk_math_eltwise_unary_sfpu_params_<APPROX>(alloy_log_f32_face, 0, (int)VectorMode::RC)));
        // Push result into CB 16
        cb_push_back(16, 1);
    }
}
