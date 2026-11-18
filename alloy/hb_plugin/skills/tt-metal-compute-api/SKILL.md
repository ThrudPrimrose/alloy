---
name: tt-metal-compute-api
description: "The tt-metal v0.63.0 compute kernel API headers (compute_kernel_api.h and compute_kernel_api/), verbatim with their doc comments."
when: before writing a Tensix compute kernel or calling a compute API function.
---

# tt-metal v0.63.0 compute kernel API

## tt_metal/include/compute_kernel_api.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "chlkc_list.h"
#include "ckernel.h"
#include "ckernel_globals.h"
#include "ckernel_include.h"
#include "ckernel_debug.h"
#include "hostdevcommon/kernel_structs.h"
#include "risc_attribs.h"

#define ALWI inline __attribute__((always_inline))

#ifdef TRISC_MATH
#include "llk_math_common_api.h"
#include "llk_math_matmul_api.h"
#include "llk_math_unary_datacopy_api.h"
#include "llk_math_binary_api.h"
#include "llk_math_unary_sfpu_api.h"
#include "llk_math_binary_sfpu_api.h"
#include "llk_math_reduce_api.h"
#define MATH(x) x
#define MAIN math_main()
#else
#define MATH(x)
#endif

#ifdef TRISC_PACK
#include "llk_pack_api.h"
#include "llk_io_pack.h"
#define PACK(x) x
#define MAIN pack_main()
#else
#define PACK(x)
#endif

#ifdef TRISC_UNPACK
#include "llk_unpack_common_api.h"
#include "llk_unpack_AB_matmul_api.h"
#include "llk_unpack_A_api.h"
#include "llk_unpack_AB_api.h"
#include "llk_unpack_reduce_api.h"
#include "llk_unpack_tilize_api.h"
#include "llk_unpack_untilize_api.h"
#include "llk_io_unpack.h"
#define UNPACK(x) x
#define MAIN unpack_main()
#else
#define UNPACK(x)
#endif

namespace ckernel {

/**
 * Please refer to documentation for any_init.
 */
// clang-format on
template <bool fast_and_approx = false>
ALWI void sigmoid_tile_init() {
    MATH((llk_math_eltwise_unary_sfpu_sigmoid_init<fast_and_approx>()));
}

// clang-format off
/**
 * Performs element-wise computation of sigmoid on each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
template <int vec_mode = VectorMode::RC, bool fast_and_approx = false>
ALWI void sigmoid_tile(uint32_t idst) {
    MATH((llk_math_eltwise_unary_sfpu_sigmoid<fast_and_approx>(idst, vec_mode)));
}

/**
 * Please refer to documentation for any_init.
 */
template <bool fast_and_approx = true>
ALWI void log_tile_init() {
    MATH((llk_math_eltwise_unary_sfpu_log_init<APPROX, fast_and_approx>()));  // TODO(AP): move out init
}

// clang-format off
/**
 * Performs element-wise computation of logarithm on each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
 // clang-format on
template <bool fast_and_approx = true>
ALWI void log_tile(uint32_t idst) {
    MATH((llk_math_eltwise_unary_sfpu_log<APPROX, fast_and_approx>(idst)));
}

/**
 * Please refer to documentation for any_init.
 */
template <bool fast_and_approx = true>
ALWI void log_with_base_tile_init() {
    MATH((llk_math_eltwise_unary_sfpu_log_with_base_init<APPROX, fast_and_approx>()));  // TODO(AP): move out init
}

// clang-format off
/**
 * Performs element-wise computation of logarithm with a specified base on each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | base_scale      | The log base                                                               | uint32_t | Postive integers                                      | True     |
 */
// clang-format on
template <bool fast_and_approx = true>
ALWI void log_with_base_tile(uint32_t idst, uint32_t base_scale) {
    MATH((llk_math_eltwise_unary_sfpu_log_with_base<APPROX, fast_and_approx>(idst, base_scale)));
}

// TODO: Move to trigonometry.h
/**
 * Please refer to documentation for any_init.
 */
ALWI void tanh_tile_init() {
    MATH((llk_math_eltwise_unary_sfpu_tanh_init<APPROX>()));  // TODO(AP): move out init
}


// TODO: Move to trigonometry.h
// clang-format off
/**
 * Performs element-wise computation of tanh on each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
 // clang-format on
ALWI void tanh_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_tanh<APPROX>(idst))); }

/**
 * Please refer to documentation for any_init.
 */
ALWI void signbit_tile_init() { MATH((llk_math_eltwise_unary_sfpu_signbit_init<APPROX>())); }

// clang-format off
/**
 * Sets the sign bit of each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to modify the sign bit of     | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
 // clang-format on
ALWI void signbit_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_signbit<APPROX>(idst))); }

// clang-format off
/**
 * Sets the sign bit of each element of a tile (int32 datatype)
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to modify the sign bit of     | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void signbit_tile_int32(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_signbit_int32<APPROX>(idst))); }

// clang-format off
/**
 * Performs element-wise computation of absolute value on each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
 // clang-format on
ALWI void abs_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_abs<APPROX>(idst))); }

/**
 * Please refer to documentation for any_init.
 */
ALWI void abs_tile_init() { MATH((llk_math_eltwise_unary_sfpu_abs_init<APPROX>())); }

// clang-format off
/**
 * Performs element-wise computation of absolute value on each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Note: This version of the function is for int32 datatype
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
 // clang-format on
ALWI void abs_tile_int32(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_abs_int32<APPROX>(idst))); }

// clang-format off
/**
 * Will store in the output of the compute core the signum of the tile.
 * The DST register buffer must be in acquired state via *acquire_dst* call.
 * This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst           | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
 // clang-format on
ALWI void sign_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_sign<APPROX>(idst))); }

/**
 * Please refer to documentation for any_init.
 */
ALWI void sign_tile_init() { MATH((llk_math_eltwise_unary_sfpu_sign_init<APPROX>())); }

// clang-format off
/**
 * Performs element-wise computation of square value on each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
 // clang-format on
ALWI void square_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_square<APPROX>(idst))); }

/**
 * Please refer to documentation for any_init.
 */
ALWI void square_tile_init() { MATH((llk_math_eltwise_unary_sfpu_square_init<APPROX>())); }

// clang-format off
/**
 * Performs element-wise multiplication on each row of a tile.
 * The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
 // clang-format on
ALWI void tiled_prod_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_tiled_prod<APPROX>(idst))); }

/**
 * Please refer to documentation for any_init.
 */
ALWI void tiled_prod_tile_init() { MATH((llk_math_eltwise_unary_sfpu_tiled_prod_init<APPROX>())); }

// POWER : y = x^(const param0)
// clang-format off
/**
 * Performs element-wise computation of power operation (x ^(const param0)) value on each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | param0          | The value of the exponent in the power operation                           | uint32_t |                                                       | True     |
 */
// clang-format on
ALWI void power_tile(uint32_t idst, uint32_t param0) {
    MATH((llk_math_eltwise_unary_sfpu_power<APPROX>(idst, param0)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void power_tile_init() { MATH((llk_math_eltwise_unary_sfpu_power_init<APPROX>())); }

// clang-format off
// MAX : y = max(idst0, idst1)
/**
 * Performs element-wise computation of max value on each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * TODO: fix idst1.
 * currently idst1 is not used and (idst0 + 1) is used for max.
 * because don't know how to use 2 dst register with sfpu.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst0           | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | idst1           | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | vector_mode     | Controls face tiles which are operated on. Default RC - all face tiles.    | int      | Valid members of VectorMode enum                      | False    |
 */
// clang-format on
ALWI void max_tile(uint32_t idst0, uint32_t idst1, int vector_mode = (int)VectorMode::RC) {
    MATH((llk_math_eltwise_unary_sfpu_max<APPROX>(idst0, vector_mode)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void max_tile_init() { MATH((llk_math_eltwise_unary_sfpu_max_init<APPROX>())); }

// clang-format off
// exp2 : y = 2 ^ x  ==> [y = exp(x * log(2))]
/**
 * Performs element-wise computation of 2^x value where x is each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
 // clang-format on
ALWI void exp2_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_exp2<true, DST_ACCUM_MODE>(idst))); }

/**
 * Please refer to documentation for any_init.
 */
ALWI void exp2_tile_init() { MATH((llk_math_eltwise_unary_sfpu_exp2_init<true>())); }

// heaviside : y = 0 if x < 0 , 1 if x > 0 , else value
// clang-format off
/**
 * Performs element-wise computation of:  y = 0 if x < 0 , 1 if x > 0 , y= value  where x is each element of a tile
 * in DST register at index tile_index. The value is provided as const param0 The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | param0          | The value the output is if the input is greater than 0                     | uint32_t |                                                       | True     |
 */
// clang-format on
ALWI void heaviside_tile(uint32_t idst, uint32_t param0) {
    MATH((llk_math_eltwise_unary_sfpu_heaviside<APPROX>(idst, param0)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void heaviside_tile_init() { MATH((llk_math_eltwise_unary_sfpu_heaviside_init<APPROX>())); }

// expm1 : (exp(x) - 1)
// clang-format off
/**
 * Performs element-wise computation of exp(x) - 1, v where x is each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
 // clang-format on
ALWI void expm1_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_expm1<true>(idst))); }

/**
 * Please refer to documentation for any_init.
 */
ALWI void expm1_tile_init() { MATH((llk_math_eltwise_unary_sfpu_expm1_init<true>())); }

// silu
// Function SILU (same as Swish)
// use activation Silu[x] = x*Sigmoid[x]
// Ref: https://pytorch.org/docs/stable/generated/torch.nn.SiLU.html?highlight=silu#torch.nn.SiLU
ALWI void silu_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_silu<APPROX>(idst))); }

ALWI void silu_tile_init() { MATH((llk_math_eltwise_unary_sfpu_silu_init<APPROX>())); }

// topK local sort
// clang-format off
/**
 * Performs local sort stage of TopK algorithm on the two data tiles and two
 * index tiles that are pre-loaded in DST register. The DST register buffer
 * must be in acquired state via *acquire_dst* call. This call is blocking
 * and is only available on the compute engine.
 *
 * The algorithm used to implement TopK is found here:
 * https://anilshanbhag.in/static/papers/gputopk_sigmod18.pdf
 *
 * The local sort stage sorts the data into length-K subsequences of
 * alternating directions, in place. If i_start_phase != i_end_phase, all
 * phases in the range i_start_phase to i_end_phase (inclusive) are computed.
 * If i_start_phase == i_end_phase, only that phase is computed, with
 * i_start_step and i_end_step defining how many steps are computed. This can
 * be used to extend the OP support for cases when K > 64.
 *
 * Note that the two data tiles need to be loaded into the DST register
 * before the invocation of this call. The corresponding index tiles should
 * also be loaded in with the data tiles, at a DST offset of 2 tiles.
 *
 * Note that local sort is done across columns on 64 values spanning across
 * 2 tiles.
 *
 * Note: idist should be set to 0
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | idir            | The sorting direction of the local sort (0 == decreasing, 1 == increasing) | int32    | 0 to 1                                                | True     |
 * | i_end_phase     | The end phase of the local sort (should be set to log(K)-1)                | int32    | 1 to 5                                                | True     |
 * | i_start_phase   | The start phase of the local sort (should be set to 0)                     | int32    | 0 to 5                                                | False    |
 * | i_end_step      | The end step to perform if i_start_phase == i_end_phase                    | int32    | 4 to 6                                                | False    |
 * | i_start_step    | The start step to perform if i_start_phase == i_end_phase                  | int32    | 4 to 6                                                | False    |
 */
// clang-format on
ALWI void topk_local_sort(
    uint32_t idst, int idir, int i_end_phase, int i_start_phase = 0, int i_end_step = 0, int i_start_step = 0) {
    MATH((llk_math_eltwise_unary_sfpu_topk_local_sort<true, DST_ACCUM_MODE>(
        idst, idir, i_end_phase, i_start_phase, i_end_step, i_start_step)));
}

// topK merge
// clang-format off
/**
 * Performs merge stage of TopK algorithm on the two data tiles and two
 * index tiles that are pre-loaded in DST register. The DST register buffer
 * must be in acquired state via *acquire_dst* call. This call is blocking
 * and is only available on the compute engine.
 *
 * The merge stage combines length-K subsequences that are 2^m_iter apart,
 * such that the first subsequence receives the top K values, and the
 * second subsequence receives the bottom K values.
 *
 * Note that the two data tiles need to be loaded into the DST register
 * before the invocation of this call. The corresponding index tiles should
 * also be loaded in with the data tiles, at a DST offset of 2 tiles.
 *
 * Note that merge is done across columns on values spanning across 2
 * tiles.
 *
 * Note: idist should be set to 0
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | m_iter          | The index of the merge & rebuild iteration of the algorithm                | int32    | 0 to 9                                                | True     |
 * | k               | The number of sorted values to return                                      | int32    | {4, 8, 16, 32, 64}                                    | True     |
 */
// clang-format on
template <bool idir = false>
ALWI void topk_merge(uint32_t idst, int m_iter, int k) {
    MATH((llk_math_eltwise_unary_sfpu_topk_merge<true, DST_ACCUM_MODE, idir>(idst, m_iter, k)));
}

// topK rebuild
// clang-format off
/**
 * Performs rebuild stage of TopK algorithm on the two data tiles and two
 * index tiles that are pre-loaded in DST register. The DST register buffer
 * must be in acquired state via *acquire_dst* call. This call is blocking
 * and is only available on the compute engine.
 *
 * The rebuild stage sorts the length-K subsequences that are 2^(m_iter+1)
 * apart, such that they alternate directions.
 *
 * Note that the two data tiles need to be loaded into the DST register
 * before the invocation of this call. The corresponding index tiles should
 * also be loaded in with the data tiles, at a DST offset of 2 tiles.
 *
 * Note that rebuild is done across columns on values spanning across 2
 * tiles.
 *
 * Note: idist should be set to 0
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | idir            | The sorting direction of the local sort (0 == decreasing, 1 == increasing) | bool     | 0 to 1                                                | True     |
 * | m_iter          | The index of the merge & rebuild iteration of the algorithm                | int32    | 0 to 9                                                | True     |
 * | k               | The number of sorted values to return                                      | int32    | {4, 8, 16, 32, 64}                                    | True     |
 * | logk            | The log of K                                                               | int32    | 2 to 6                                                | True     |
 * | skip_second     | Whether or not to skip second tile                                         | int32    | 0 to 1                                                | True     |
 */
// clang-format on
ALWI void topk_rebuild(uint32_t idst, bool idir, int m_iter, int k, int logk, int skip_second) {
    MATH((llk_math_eltwise_unary_sfpu_topk_rebuild<true, DST_ACCUM_MODE>(idst, idir, m_iter, k, logk, skip_second)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void topk_tile_init() { MATH((llk_math_eltwise_unary_sfpu_topk_init<true>())); }

// clang-format off
/**
 * Performs MaxPool with indices algorithm on the data tile and index tile
 * that are pre-loaded in DST register. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Only a reduction of 9 rows is supported at this time.
 *
 * | Argument        | Description                                                              | Type     | Valid Range                                           | Required |
 * |-----------------|--------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register containing the data to be reduced  | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | idst_idx        | The index of the tile in DST register containing the indices of the data | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | num_rows        | The number of rows to use for the MaxPool operation                      | uint32_t | {9}                                                   | True     |
 */
// clang-format on
template <int num_rows = 9>
ALWI void max_reduce_with_indices(uint32_t idst, uint32_t idst_idx) {
    // support for num_rows != 9 is tracked here: https://github.com/tenstorrent/tt-metal/issues/17202
    static_assert(num_rows == 9, "num_rows must be one of: {9}");
    MATH((llk_math_eltwise_binary_sfpu_max_pool_with_indices<true, DST_ACCUM_MODE, num_rows>(idst, idst_idx)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void max_reduce_with_indices_init() { MATH((llk_math_eltwise_binary_sfpu_max_pool_with_indices_init<true>())); }

/**
 * Pauses the cores so that the debug interface can be used to inspect the value of the registers.
 *
 * Return value: None
 */
ALWI void dbg_halt() {
    PACK(dbg_thread_halt<PackThreadId>());
    UNPACK(dbg_thread_halt<UnpackThreadId>());
    MATH(dbg_thread_halt<MathThreadId>());
}

/**
 * Resumes the execution of the cores after a debug halt.
 *
 * Return value: None
 */
ALWI void dbg_unhalt() {
    PACK(dbg_thread_unhalt<PackThreadId>());
    UNPACK(dbg_thread_unhalt<UnpackThreadId>());
    MATH(dbg_thread_unhalt<MathThreadId>());
}

// clang-format off
/**
 * Reads the contents of the specified row of the destination register. It reads 8 dwords at a time.
 *
 * | Argument        | Description                                             | Type      | Valid Range  | Required |
 * |-----------------|---------------------------------------------------------|-----------|--------------|----------|
 * | row_addr        | The row address in the destination register to read     | int       |              | True     |
 * | rd_data         | The array of 8 dwords to store the data                 | uint32_t* |              | True     |
 *
 * Return value: None
 */
 // clang-format on
ALWI void dbg_read_dest_acc_row(int row_addr, uint32_t* rd_data) {
    MATH((dbg_get_array_row(dbg_array_id::DEST, row_addr, rd_data)));
}

// unary_max : if x > value --> x, else value
// clang-format off
/**
 * Performs element-wise computation of:  result = x if x > value , where x is each element of a tile
 * in DST register at index tile_index. The value is provided as const param0 The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | param0          | The value to be compared with the input tensor                             | uint32_t |                                                       | True     |
 */
// clang-format on
ALWI void unary_max_int32_tile(uint32_t idst, uint32_t param0) {
    MATH((llk_math_eltwise_unary_sfpu_unary_max_int32<APPROX>(idst, param0)));
}

// unary_max : if x > value --> x, else value
// clang-format off
/**
 * Performs element-wise computation of:  result = x if x > value , where x is each element of a tile
 * in DST register at index tile_index. The value is provided as const param0 The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | param0          | The value to be compared with the input tensor                             | uint32_t |                                                       | True     |
 */
// clang-format on
ALWI void unary_max_tile(uint32_t idst, uint32_t param0) {
    MATH((llk_math_eltwise_unary_sfpu_unary_max<APPROX>(idst, param0)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void unary_max_tile_init() { MATH((llk_math_eltwise_unary_sfpu_unary_max_init<APPROX>())); }

// clang-format off
/**
 * Treats pairs of numbers as complex numbers and rotates them 90 degrees
 * in the complex plane. The operation is performed on a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void alt_complex_rotate90_tile(uint32_t idst) {
    MATH((llk_math_eltwise_unary_sfpu_alt_complex_rotate90<APPROX>(idst)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void alt_complex_rotate90_tile_init() { MATH((llk_math_eltwise_unary_sfpu_alt_complex_rotate90_init<APPROX>())); }

// unary_min : if x < value --> x, else value
// clang-format off
/**
 * Performs element-wise computation of:  result = x if x < value , where x is each element of a tile
 * in DST register at index tile_index. The value is provided as const param0 The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | param0          | The value to be compared with the input tensor                             | uint32_t |                                                       | True     |
 */
// clang-format on
ALWI void unary_min_int32_tile(uint32_t idst, uint32_t param0) {
    MATH((llk_math_eltwise_unary_sfpu_unary_min_int32<APPROX>(idst, param0)));
}

// unary_min : if x < value --> x, else value
// clang-format off
/**
 * Performs element-wise computation of:  result = x if x < value , where x is each element of a tile
 * in DST register at index tile_index. The value is provided as const param0 The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | param0          | The value to be compared with the input tensor                             | uint32_t |                                                       | True     |
 */
// clang-format on
ALWI void unary_min_tile(uint32_t idst, uint32_t param0) {
    MATH((llk_math_eltwise_unary_sfpu_unary_min<APPROX>(idst, param0)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void unary_min_tile_init() { MATH((llk_math_eltwise_unary_sfpu_unary_min_init<APPROX>())); }

ALWI uint32_t get_compute_special_value_flags() {
    uint32_t ret_val = 0;
    MATH((ret_val = llk_math_get_compute_special_value_flags()));
    return ret_val;
}

ALWI uint32_t get_compute_special_value_flags_fpu(uint32_t special_value_flags_reg) {
    uint32_t ret_val = 0;
    MATH((ret_val = llk_math_get_compute_special_value_flags_fpu(special_value_flags_reg)));
    return ret_val;
}

ALWI uint32_t get_compute_special_value_flags_sfpu(uint32_t special_value_flags_reg) {
    uint32_t ret_val = 0;
    MATH((ret_val = llk_math_get_compute_special_value_flags_sfpu(special_value_flags_reg)));
    return ret_val;
}

ALWI void clear_compute_special_value_flags() { MATH((llk_math_clear_compute_special_value_flags())); }

ALWI void store_compute_special_value_flags_to_l1(uint32_t l1_addr) {
    MATH((llk_math_store_compute_special_value_flags_to_l1(l1_addr)));
}

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/add_int_sfpu.h

```cpp
// SPDX-FileCopyrightText: © 2024 Tenstorrent AI ULC
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_binary_sfpu_add_int.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

// clang-format off
/**
 * Performs an elementwise add operation with the two integer inputs: y = add(x0,x1)
 * Output overwrites odst in DST.
 *
 * The DST register buffer must be in acquired state via *acquire_dst* call. This call is blocking and is only available
 * on the compute engine.
 * A maximum of 4 tiles from each operand can be loaded into DST at once, for a total of 8 tiles,
 * when using 16 bit formats. This gets reduced to 2 tiles from each operand for 32 bit formats.
 *
 * Return value: None
 *
 * | Argument | Description                                                           | Type     | Valid Range                                           | Required |
 * |----------|-----------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst0    | The index of the tile in DST register buffer to use as first operand  | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | idst1    | The index of the tile in DST register buffer to use as second operand | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | odst     | The index of the tile in DST register buffer to use as output         | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void add_int32_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_add_int<APPROX, 8, InstrModLoadStore::INT32, false>(idst0, idst1, odst)));
}

ALWI void add_uint16_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_add_int<APPROX, 8, InstrModLoadStore::LO16, false>(idst0, idst1, odst)));
}

ALWI void add_uint32_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_add_int<APPROX, 8, InstrModLoadStore::INT32, false>(idst0, idst1, odst)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void add_int_tile_init() { MATH((llk_math_eltwise_binary_sfpu_add_int_init<APPROX>())); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/bcast.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common.h"
#ifdef TRISC_MATH
#include "llk_math_binary_api.h"
#include "llk_math_matmul_api.h"
#include "llk_math_common.h"
#include "llk_math_unary_datacopy_api.h"
#endif
#ifdef TRISC_UNPACK
#include "llk_unpack_AB_api.h"
#include "llk_unpack_A_api.h"
#endif
#ifdef TRISC_PACK
#include "llk_pack.h"
#include "llk_pack_common.h"
#endif

namespace ckernel {

template <BroadcastType bcast_type>
ALWI void unary_bcast_init(uint32_t icb, uint32_t ocb) {
    // Pass through uses A2D and potentially direct unpack to dest.
    const auto data_copy_type = (bcast_type == BroadcastType::NONE) ? A2D : B2D;
    const bool enable_unpack_to_dest = data_copy_type == A2D;

    // Will configure A & B in similar way
    UNPACK((llk_unpack_A_hw_configure_disaggregated<DST_ACCUM_MODE>(icb)));
    UNPACK((llk_unpack_A_init<bcast_type, false, EltwiseBinaryReuseDestType::NONE, enable_unpack_to_dest>(
        false, false /*transpose within 16x16 face*/, icb)));

    MATH((llk_math_eltwise_unary_datacopy_init<data_copy_type, DST_ACCUM_MODE, bcast_type>(
        false /*transpose of faces*/, false /*transpose within 16x16 face*/, icb)));
    MATH((llk_math_pack_sync_init<DST_ACCUM_MODE>()));
    MATH((llk_math_hw_configure_disaggregated(icb, icb)));

    PACK((llk_pack_hw_configure_disaggregated<DST_ACCUM_MODE, false>(ocb)));
    PACK((llk_pack_init<false>(ocb)));
    PACK((llk_pack_dest_init<DST_ACCUM_MODE, false>()));
}

template <BroadcastType bcast_type>
ALWI void unary_bcast(uint32_t icb, uint32_t in_tile_index, uint32_t dst_tile_index) {
    // Pass through uses A2D and potentially direct unpack to dest.
    const auto data_copy_type = (bcast_type == BroadcastType::NONE) ? A2D : B2D;
    const bool enable_unpack_to_dest = data_copy_type == A2D;

    UNPACK(
        (llk_unpack_A<bcast_type, false, EltwiseBinaryReuseDestType::NONE, enable_unpack_to_dest>(icb, in_tile_index)));
    MATH((llk_math_eltwise_unary_datacopy<data_copy_type, DST_ACCUM_MODE, bcast_type, enable_unpack_to_dest>(
        dst_tile_index, icb)));
}

template <BroadcastType old_bcast_type, BroadcastType new_bcast_type>
void reconfigure_unary_bcast(uint32_t old_icb, uint32_t new_icb, uint32_t old_ocb, uint32_t new_ocb) {
#if defined(TRISC_MATH) || defined(TRISC_UNPACK)
    // Pass through uses A2D and potentially direct unpack to dest.
    const auto data_copy_type = (new_bcast_type == BroadcastType::NONE) ? A2D : B2D;
    const bool enable_unpack_to_dest = data_copy_type == A2D;
    const std::uint32_t new_operand_id = get_operand_id(new_icb);
    const std::uint32_t old_operand_id = get_operand_id(old_icb);
    bool unpacker_src_format_change = unpack_src_format[new_operand_id] != unpack_src_format[old_operand_id];
    bool unpacker_dst_format_change = unpack_dst_format[new_operand_id] != unpack_dst_format[old_operand_id];
    bool bcast_type_change = (old_bcast_type != new_bcast_type);

    if (unpacker_src_format_change || unpacker_dst_format_change) {
        // Will configure A & B in similar way
        UNPACK((llk_unpack_A_hw_configure_disaggregated<DST_ACCUM_MODE>(new_icb)));
    }

    if (unpacker_src_format_change || unpacker_dst_format_change || bcast_type_change) {
        UNPACK((llk_unpack_A_init<new_bcast_type, false, EltwiseBinaryReuseDestType::NONE, enable_unpack_to_dest>(
            false, false /*transpose within 16x16 face*/, new_icb)));
    }

    if (unpacker_dst_format_change) {
        MATH((llk_math_hw_configure_disaggregated(new_icb, new_icb)));
    }

    if (unpacker_dst_format_change || bcast_type_change) {
        MATH((llk_math_eltwise_unary_datacopy_init<data_copy_type, DST_ACCUM_MODE, new_bcast_type>(
            false /*transpose of faces*/, false /*transpose within 16x16 face*/, new_icb)));
    }
#endif

    PACK((llk_pack_reconfig_data_format<DST_ACCUM_MODE>(old_ocb, new_ocb)));
}

/**
 * Shorthand template instantiation of sub_tiles_bcast.
 */
ALWI void sub_tiles_bcast_cols(uint32_t icb0, uint32_t icb1, uint32_t itile0, uint32_t itile1, uint32_t idst) {
    MATH((llk_math_eltwise_binary<
          EltwiseBinaryType::ELWSUB,
          BroadcastType::COL,
          DST_ACCUM_MODE,
          MATH_FIDELITY,
          EltwiseBinaryReuseDestType::NONE>(icb0, icb1, idst, true)));
    UNPACK((llk_unpack_AB<BroadcastType::COL>(icb0, icb1, itile0, itile1)));
}

/**
 * Shorthand template instantiation of sub_tiles_bcast.
 */
ALWI void sub_tiles_bcast_scalar(uint32_t icb0, uint32_t icb1, uint32_t itile0, uint32_t itile1, uint32_t idst) {
    MATH((llk_math_eltwise_binary<
          EltwiseBinaryType::ELWSUB,
          BroadcastType::SCALAR,
          DST_ACCUM_MODE,
          MATH_FIDELITY,
          EltwiseBinaryReuseDestType::NONE>(icb0, icb1, idst, true)));
    UNPACK((llk_unpack_AB<BroadcastType::SCALAR>(icb0, icb1, itile0, itile1)));
}

/**
 * Shorthand template instantiation of mul_tiles_bcast.
 */
ALWI void mul_tiles_bcast_cols(uint32_t icb0, uint32_t icb1, uint32_t itile0, uint32_t itile1, uint32_t idst) {
    MATH((llk_math_eltwise_binary<
          EltwiseBinaryType::ELWMUL,
          BroadcastType::COL,
          DST_ACCUM_MODE,
          MATH_FIDELITY,
          EltwiseBinaryReuseDestType::NONE>(icb0, icb1, idst, true)));
    UNPACK((llk_unpack_AB<BroadcastType::COL>(icb0, icb1, itile0, itile1)));
}

/**
 * Shorthand template instantiation of mul_tiles_bcast.
 */
ALWI void mul_tiles_bcast_rows(uint32_t icb0, uint32_t icb1, uint32_t itile0, uint32_t itile1, uint32_t idst) {
    MATH((llk_math_eltwise_binary<
          EltwiseBinaryType::ELWMUL,
          BroadcastType::ROW,
          DST_ACCUM_MODE,
          MATH_FIDELITY,
          EltwiseBinaryReuseDestType::NONE>(icb0, icb1, idst, true)));
    UNPACK((llk_unpack_AB<BroadcastType::ROW>(icb0, icb1, itile0, itile1)));
}

/**
 * Please refer to documentation for sub_tiles_bcast
 */
ALWI void add_tiles_bcast_rows(uint32_t icb0, uint32_t icb1, uint32_t itile0, uint32_t itile1, uint32_t idst) {
    MATH((llk_math_eltwise_binary<
          EltwiseBinaryType::ELWADD,
          BroadcastType::ROW,
          DST_ACCUM_MODE,
          MATH_FIDELITY,
          EltwiseBinaryReuseDestType::NONE>(icb0, icb1, idst, true)));
    UNPACK((llk_unpack_AB<BroadcastType::ROW>(icb0, icb1, itile0, itile1)));
}

/**
 * Please refer to documentation for sub_tiles_bcast
 */
ALWI void add_tiles_bcast_cols(uint32_t icb0, uint32_t icb1, uint32_t itile0, uint32_t itile1, uint32_t idst) {
    MATH((llk_math_eltwise_binary<
          EltwiseBinaryType::ELWADD,
          BroadcastType::COL,
          DST_ACCUM_MODE,
          MATH_FIDELITY,
          EltwiseBinaryReuseDestType::NONE>(icb0, icb1, idst, true)));
    UNPACK((llk_unpack_AB<BroadcastType::COL>(icb0, icb1, itile0, itile1)));
}

/**
 * Please refer to documentation for add_tiles_bcast
 */
ALWI void add_tiles_bcast_scalar(uint32_t icb0, uint32_t icb1, uint32_t itile0, uint32_t itile1, uint32_t idst) {
    MATH((llk_math_eltwise_binary<
          EltwiseBinaryType::ELWADD,
          BroadcastType::SCALAR,
          DST_ACCUM_MODE,
          MATH_FIDELITY,
          EltwiseBinaryReuseDestType::NONE>(icb0, icb1, idst, true)));
    UNPACK((llk_unpack_AB<BroadcastType::SCALAR>(icb0, icb1, itile0, itile1)));
}

// clang-format off
/**
 * Associated init function that must be called before calling a bcast op.
 *
 * Return value: None
 *
 *
 * | Argument       | Description                                                   | Type          | Valid Range | Required |
 * |----------------|---------------------------------------------------------------|---------------|-------------|----------|
 * | icb0           | The identifier of the circular buffer (CB) containing A       | uint32_t      | 0 to 31     | True     |
 * | icb1           | The indentifier of the circular buffer (CB) containing B      | uint32_t      | 0 to 31     | True     |
 * | ocb            | The indentifier of the circular buffer (CB) containing output | uint32_t      | 0 to 31     | False    |
 */
 // clang-format on
template <EltwiseBinaryType tBcastOp, BroadcastType tBcastDim>
void init_bcast(uint32_t icb0, uint32_t icb1, uint32_t ocb) {
    if constexpr (tBcastOp == ELWMUL) {
        MATH((llk_math_eltwise_binary_init<tBcastOp, tBcastDim, MATH_FIDELITY>()));
    } else {
        MATH((llk_math_eltwise_binary_init<tBcastOp, tBcastDim>()));
    }

    UNPACK((llk_unpack_AB_hw_configure_disaggregated<DST_ACCUM_MODE>(icb0, icb1)));
    UNPACK((llk_unpack_AB_init<tBcastDim>(icb0, icb1)));
    // TODO(AP): running this specific init after common AB init causes a hang

    // clone of general init for AB TODO(AP): commonize
    // UNPACK(( llk_unpack_AB_init<BroadcastType::NONE>() ));
    // UNPACK(( llk_unpack_AB_hw_configure_disaggregated<DST_ACCUM_MODE>(icb0, icb1) ));

    PACK((llk_pack_hw_configure_disaggregated<DST_ACCUM_MODE, false>(ocb)));
    PACK((llk_pack_init(ocb)));
    PACK((llk_pack_dest_init<DST_ACCUM_MODE, false>()));

    MATH((llk_math_pack_sync_init<DST_ACCUM_MODE>()));
    MATH((llk_math_hw_configure_disaggregated(icb0, icb1)));
}

/*
Internal helper function for all broadcast ops
*/
template <EltwiseBinaryType tBcastOp, BroadcastType tBcastDim>
ALWI void any_tiles_bcast(uint32_t icb0, uint32_t icb1, uint32_t itile0, uint32_t itile1, uint32_t idst) {
    MATH((llk_math_eltwise_binary<tBcastOp, tBcastDim, DST_ACCUM_MODE, MATH_FIDELITY, EltwiseBinaryReuseDestType::NONE>(
        icb0, icb1, idst, true)));
    UNPACK((llk_unpack_AB<tBcastDim>(icb0, icb1, itile0, itile1)));
}

// clang-format off
/**
 * This documentation applies to either one of the 3 broadcast operation variants -
 * *add_tiles_bcast*, *sub_tiles_bcast* and *mul_tiles_bcast*.
 *
 * The description below describes *add_tiles_bcast*, the other 2 operations
 * use the same definition with the corresponding substitution of the math
 * operator.
 *
 * Performs a broadcast-operation *C=A+B* of tiles in two CBs at given indices
 * and writes the result to the DST register at index dst_tile_index. The DST
 * register buffer must be in acquired state via *acquire_dst* call. This call
 * is blocking and is only available on the compute engine.
 *
 * Broadcasting semantics are defined as follows:
 *
 * For *dim==BroadcastType::COL*, the input in *B* is expected to be a single tile with a
 * filled 0-column and zeros elsewhere.  The result is *C[h, w] = A[h,w] + B[w]*
 *
 * For *dim==Dim::C*, the input in *B* is expected to be a single tile with a
 * filled 0-row, and zeros elsewhere.  The result is *C[h, w] = A[h,w] + B[h]*
 *
 * For *dim==Dim::RC*, the input in *B* is expected to be a single tile with a
 * filled single value at location [0,0], and zeros elsewhere.  The result is
 * *C[h, w] = A[h,w] + B[0,0]*
 *
 * Return value: None
 *
 * DOX-TODO(AP): verify that the bcast tile is actually required to be filled
 * with zeros.
 *
 * | Argument       | Description                                              | Type          | Valid Range                                    | Required |
 * |----------------|----------------------------------------------------------|---------------|------------------------------------------------|----------|
 * | tBcastDim      | Broadcast dimension                                      | BroadcastType | One of Dim::R, Dim::C, Dim::RC.                | True     |
 * | in0_cb_id      | The identifier of the circular buffer (CB) containing A  | uint32_t      | 0 to 31                                        | True     |
 * | in1_cb_id      | The indentifier of the circular buffer (CB) containing B | uint32_t      | 0 to 31                                        | True     |
 * | in0_tile_index | The index of tile A within the first CB                  | uint32_t      | Must be less than the size of the CB           | True     |
 * | in1_tile_index | The index of tile B within the second CB                 | uint32_t      | Must be less than the size of the CB           | True     |
 * | dst_tile_index | The index of the tile in DST REG for the result C        | uint32_t      | Must be less than the acquired size of DST REG | True     |
 */
// clang-format on
template <BroadcastType tBcastDim>
ALWI void add_tiles_bcast(uint32_t icb0, uint32_t icb1, uint32_t itile0, uint32_t itile1, uint32_t idst) {
    any_tiles_bcast<EltwiseBinaryType::ELWADD, tBcastDim>(icb0, icb1, itile0, itile1, idst);
}

/**
 * Please refer to documentation for *add_tiles_bcast*.
 */
template <BroadcastType tBcastDim>
ALWI void sub_tiles_bcast(uint32_t icb0, uint32_t icb1, uint32_t itile0, uint32_t itile1, uint32_t idst) {
    any_tiles_bcast<EltwiseBinaryType::ELWSUB, tBcastDim>(icb0, icb1, itile0, itile1, idst);
}

/**
 * Please refer to documentation for *add_tiles_bcast*.
 */
template <BroadcastType tBcastDim>
ALWI void mul_tiles_bcast(uint32_t icb0, uint32_t icb1, uint32_t itile0, uint32_t itile1, uint32_t idst) {
    any_tiles_bcast<EltwiseBinaryType::ELWMUL, tBcastDim>(icb0, icb1, itile0, itile1, idst);
}

/**
 * Performs a first-call or switch-from-another-op tile hw reconfiguration step needed for add_bcast_rows to be executed
 * correctly. Required to be called before add_tiles_bcast if using column as broadcast type
 */
ALWI void add_bcast_rows_init_short(uint32_t icb0, uint32_t icb1) {
    MATH((llk_math_eltwise_binary_init_with_operands<ELWADD, BroadcastType::ROW, MATH_FIDELITY>(icb0, icb1)));
    UNPACK((llk_unpack_AB_init<BroadcastType::ROW>(icb0, icb1)));
}

/**
 * Performs a first-call or switch-from-another-op tile hw reconfiguration step needed for add_bcast_cols to be executed
 * correctly. Required to be called before add_tiles_bcast if using column as broadcast type
 */
ALWI void add_bcast_cols_init_short(uint32_t icb0, uint32_t icb1) {
    MATH((llk_math_eltwise_binary_init<ELWADD, BroadcastType::COL>()));
    // FIXME: API Update needed in compute kernel?
    UNPACK((llk_unpack_AB_init<BroadcastType::COL>(icb0, icb1)));
}

/**
 * Performs a first-call or switch-from-another-op tile hw reconfiguration step needed for add_bcast_scalar to be
 * executed correctly.
 */
ALWI void add_bcast_scalar_init_short(uint32_t icb0, uint32_t icb1) {
    MATH((llk_math_eltwise_binary_init<ELWADD, BroadcastType::SCALAR, MATH_FIDELITY>()));
    // FIXME: API Update needed in compute kernel?
    UNPACK((llk_unpack_AB_init<BroadcastType::SCALAR>(icb0, icb1)));
}

/**
 * Performs a first-call or switch-from-another-op tile hw reconfiguration step needed for mul_bcast_cols to be executed
 * correctly.
 */
ALWI void mul_tiles_bcast_scalar_init_short(uint32_t icb0, uint32_t icb1) {
    MATH((llk_math_eltwise_binary_init_with_operands<ELWMUL, BroadcastType::SCALAR, MATH_FIDELITY>(icb0, icb1)));
    // FIXME: API Update needed in compute kernel?
    UNPACK((llk_unpack_AB_init<BroadcastType::SCALAR>(icb0, icb1)));
}

/**
 * Performs a broadcast-multiply of a tile from icb0[itile0] with a scalar encoded as a tile from icb1[itile1].
 */
ALWI void mul_tiles_bcast_scalar(uint32_t icb0, uint32_t icb1, uint32_t itile0, uint32_t itile1, uint32_t idst) {
    MATH((llk_math_eltwise_binary<
          ELWMUL,
          BroadcastType::SCALAR,
          DST_ACCUM_MODE,
          MATH_FIDELITY,
          EltwiseBinaryReuseDestType::NONE>(icb0, icb1, idst, true)));
    UNPACK((llk_unpack_AB<BroadcastType::SCALAR>(icb0, icb1, itile0, itile1)));
}

/**
 * Performs a first-call or switch-from-another-op tile hw reconfiguration step needed for mul_bcast_cols to be executed
 * correctly.
 */
ALWI void mul_bcast_cols_init_short(uint32_t icb0, uint32_t icb1) {
    MATH((llk_math_eltwise_binary_init<ELWMUL, BroadcastType::COL, MATH_FIDELITY>()));
    // FIXME: API Update needed in compute kernel?
    UNPACK((llk_unpack_AB_init<BroadcastType::COL>(icb0, icb1)));
}

/**
 * Performs a switch-from-another-op tile hw reconfiguration step needed for mul_bcast_rows to be executed correctly.
 */
ALWI void mul_bcast_rows_init_short(uint32_t icb0, uint32_t icb1) {
    MATH((llk_math_eltwise_binary_init<ELWMUL, BroadcastType::ROW, MATH_FIDELITY>()));
    // FIXME: API Update needed in compute kernel?
    UNPACK((llk_unpack_AB_init<BroadcastType::ROW>(icb0, icb1)));
}

/**
 * Performs a first-call or switch-from-another-op tile hw reconfiguration step needed for sub_bcast_cols to be executed
 * correctly.
 */
ALWI void sub_bcast_cols_init_short(uint32_t icb0, uint32_t icb1) {
    MATH((llk_math_eltwise_binary_init_with_operands<ELWSUB, BroadcastType::COL, MATH_FIDELITY>(icb0, icb1)));
    // FIXME: API Update needed in compute kernel?
    UNPACK((llk_unpack_AB_init<BroadcastType::COL>(icb0, icb1)));
}

/**
 * Performs a first-call or switch-from-another-op tile hw reconfiguration step needed for sub_tiles_bcast_scalar to be
 * executed correctly.
 */
ALWI void sub_tiles_bcast_scalar_init_short(uint32_t icb0, uint32_t icb1) {
    MATH((llk_math_eltwise_binary_init<ELWSUB, BroadcastType::SCALAR, MATH_FIDELITY>()));
    // FIXME: API Update needed in compute kernel?
    UNPACK((llk_unpack_AB_init<BroadcastType::SCALAR>(icb0, icb1)));
}

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/binary_bitwise_sfpu.h

```cpp
// SPDX-FileCopyrightText: © 2024 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_binary_sfpu_bitwise.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

// clang-format off
/**
 * Performs an elementwise binary bitwise operation with the two inputs: y = bitwise(x0,x1)
 * Output overwrites odst in DST.
 *
 * The DST register buffer must be in acquired state via *acquire_dst* call. This call is blocking and is only available
 * on the compute engine.
 * A maximum of 4 tiles from each operand can be loaded into DST at once, for a total of 8 tiles,
 * when using 16 bit formats. This gets reduced to 2 tiles from each operand for 32 bit formats.
 *
 * Return value: None
 *
 * | Argument       | Description                                                           | Type     | Valid Range                                           | Required |
 * |----------------|-----------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst0          | The index of the tile in DST register buffer to use as first operand  | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | idst1          | The index of the tile in DST register buffer to use as second operand | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | odst           | The index of the tile in DST register buffer to use as output         | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void bitwise_and_binary_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_bitwise<APPROX, ckernel::sfpu::BinaryBitwiseOp::AND, InstrModLoadStore::INT32>(
        idst0, idst1, odst)));
}

ALWI void bitwise_and_uint32_binary_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_bitwise<APPROX, ckernel::sfpu::BinaryBitwiseOp::AND, InstrModLoadStore::INT32>(
        idst0, idst1, odst)));
}

ALWI void bitwise_and_uint16_binary_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_bitwise<APPROX, ckernel::sfpu::BinaryBitwiseOp::AND, InstrModLoadStore::LO16>(
        idst0, idst1, odst)));
}

ALWI void bitwise_or_binary_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_bitwise<APPROX, ckernel::sfpu::BinaryBitwiseOp::OR, InstrModLoadStore::INT32>(
        idst0, idst1, odst)));
}

ALWI void bitwise_or_uint32_binary_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_bitwise<APPROX, ckernel::sfpu::BinaryBitwiseOp::OR, InstrModLoadStore::INT32>(
        idst0, idst1, odst)));
}

ALWI void bitwise_or_uint16_binary_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_bitwise<APPROX, ckernel::sfpu::BinaryBitwiseOp::OR, InstrModLoadStore::LO16>(
        idst0, idst1, odst)));
}

ALWI void bitwise_xor_binary_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_bitwise<APPROX, ckernel::sfpu::BinaryBitwiseOp::XOR, InstrModLoadStore::INT32>(
        idst0, idst1, odst)));
}

ALWI void bitwise_xor_uint32_binary_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_bitwise<APPROX, ckernel::sfpu::BinaryBitwiseOp::XOR, InstrModLoadStore::INT32>(
        idst0, idst1, odst)));
}

ALWI void bitwise_xor_uint16_binary_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_bitwise<APPROX, ckernel::sfpu::BinaryBitwiseOp::XOR, InstrModLoadStore::LO16>(
        idst0, idst1, odst)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void binary_bitwise_tile_init() { MATH((llk_math_eltwise_binary_sfpu_bitwise_init<APPROX>())); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/binary_max_min.h

```cpp
// SPDX-FileCopyrightText: © 2025 Tenstorrent AI ULC
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_binary_sfpu_binary_max_min.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

// clang-format off
/**
 * Performs an elementwise maximum operation on inputs of int32 data type at idst0, idst1: y = max(x0, x1).
 * Output overwrites odst in DST.
 *
 * The DST register buffer must be in acquired state via *acquire_dst* call. This call is blocking and is only available
 * on the compute engine.
 * A maximum of 4 tiles from each operand can be loaded into DST at once, for a total of 8 tiles,
 * when using 16 bit formats. This gets reduced to 2 tiles from each operand for 32 bit formats.
 *
 * Return value: None
 *
 * | Argument       | Description                                                           | Type     | Valid Range                                           | Required |
 * |----------------|-----------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst0          | The index of the tile in DST register buffer to use as first operand  | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | idst1          | The index of the tile in DST register buffer to use as second operand | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | odst           | The index of the tile in DST register buffer to use as output         | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void binary_max_int32_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_binary_max<APPROX, InstrModLoadStore::INT32_2S_COMP>(idst0, idst1, odst)));
}

// clang-format off
/**
 * Performs an elementwise maximum operation on inputs at idst0, idst1: y = max(x0, x1).
 * Output overwrites odst in DST.
 *
 * The DST register buffer must be in acquired state via *acquire_dst* call. This call is blocking and is only available
 * on the compute engine.
 * A maximum of 4 tiles from each operand can be loaded into DST at once, for a total of 8 tiles,
 * when using 16 bit formats. This gets reduced to 2 tiles from each operand for 32 bit formats.
 *
 * Return value: None
 *
 * | Argument       | Description                                                           | Type     | Valid Range                                           | Required |
 * |----------------|-----------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst0          | The index of the tile in DST register buffer to use as first operand  | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | idst1          | The index of the tile in DST register buffer to use as second operand | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | odst           | The index of the tile in DST register buffer to use as output         | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void binary_max_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_binary_max<APPROX, InstrModLoadStore::DEFAULT>(idst0, idst1, odst)));
}

/**
 * Please refer to documentation.
 */
ALWI void binary_max_tile_init() { MATH((llk_math_eltwise_binary_sfpu_binary_max_init<APPROX>())); }

// clang-format off
/**
 * Performs an elementwise maximum operation on inputs of int32 data type at idst0, idst1: y = min(x0, x1).
 * Output overwrites odst in DST.
 *
 * The DST register buffer must be in acquired state via *acquire_dst* call. This call is blocking and is only available
 * on the compute engine.
 * A maximum of 4 tiles from each operand can be loaded into DST at once, for a total of 8 tiles,
 * when using 16 bit formats. This gets reduced to 2 tiles from each operand for 32 bit formats.
 *
 * Return value: None
 *
 * | Argument       | Description                                                           | Type     | Valid Range                                           | Required |
 * |----------------|-----------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst0          | The index of the tile in DST register buffer to use as first operand  | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | idst1          | The index of the tile in DST register buffer to use as second operand | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | odst           | The index of the tile in DST register buffer to use as output         | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void binary_min_int32_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_binary_min<APPROX, InstrModLoadStore::INT32_2S_COMP>(idst0, idst1, odst)));
}

// clang-format off
/**
 * Performs an elementwise minimum operation on inputs at idst0, idst1: y = min(x0, x1).
 * Output overwrites odst in DST.
 *
 * The DST register buffer must be in acquired state via *acquire_dst* call. This call is blocking and is only available
 * on the compute engine.
 * A maximum of 4 tiles from each operand can be loaded into DST at once, for a total of 8 tiles,
 * when using 16 bit formats. This gets reduced to 2 tiles from each operand for 32 bit formats.
 *
 * Return value: None
 *
 * | Argument       | Description                                                           | Type     | Valid Range                                           | Required |
 * |----------------|-----------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst0          | The index of the tile in DST register buffer to use as first operand  | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | idst1          | The index of the tile in DST register buffer to use as second operand | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | odst           | The index of the tile in DST register buffer to use as output         | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void binary_min_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_binary_min<APPROX, InstrModLoadStore::DEFAULT>(idst0, idst1, odst)));
}

/**
 * Please refer to documentation.
 */
ALWI void binary_min_tile_init() { MATH((llk_math_eltwise_binary_sfpu_binary_min_init<APPROX>())); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/binary_shift.h

```cpp
// SPDX-FileCopyrightText: © 2024 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_binary_sfpu_shift.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

// clang-format off
/**
 * Performs an elementwise shift operation to the left on the input at idst0, by input at idst1: y = x0 << x1
 * Both inputs must be of Int32 data type only. Output overwrites odst in DST.
 *
 * The DST register buffer must be in acquired state via *acquire_dst* call. This call is blocking and is only available
 * on the compute engine.
 * A maximum of 4 tiles from each operand can be loaded into DST at once, for a total of 8 tiles,
 * when using 16 bit formats. This gets reduced to 2 tiles from each operand for 32 bit formats.
 *
 * Return value: None
 *
 * | Argument       | Description                                                           | Type     | Valid Range                                           | Required |
 * |----------------|-----------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst0          | The index of the tile in DST register buffer to use as first operand  | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | idst1          | The index of the tile in DST register buffer to use as second operand | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | odst           | The index of the tile in DST register buffer to use as output         | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void binary_left_shift_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_left_shift<APPROX>(idst0, idst1, odst)));
}

template <bool sign_magnitude_format = false>
ALWI void binary_left_shift_uint32_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_left_shift<APPROX, InstrModLoadStore::INT32, sign_magnitude_format>(
        idst0, idst1, odst)));
}

ALWI void binary_left_shift_int32_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_left_shift<APPROX, InstrModLoadStore::INT32>(idst0, idst1, odst)));
}

// clang-format off
/**
 * Performs an elementwise shift operation to the right on the input at idst0, by input at idst1: y = x0 >> x1
 * Both inputs must be of Int32 data type only. Output overwrites odst in DST.
 *
 * The DST register buffer must be in acquired state via *acquire_dst* call. This call is blocking and is only available
 * on the compute engine.
 * A maximum of 4 tiles from each operand can be loaded into DST at once, for a total of 8 tiles,
 * when using 16 bit formats. This gets reduced to 2 tiles from each operand for 32 bit formats.
 *
 * Return value: None
 *
 * | Argument       | Description                                                           | Type     | Valid Range                                           | Required |
 * |----------------|-----------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst0          | The index of the tile in DST register buffer to use as first operand  | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | idst1          | The index of the tile in DST register buffer to use as second operand | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | odst           | The index of the tile in DST register buffer to use as output         | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void binary_right_shift_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_right_shift<APPROX>(idst0, idst1, odst)));
}

template <bool sign_magnitude_format = false>
ALWI void binary_right_shift_uint32_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_right_shift<APPROX, InstrModLoadStore::INT32, sign_magnitude_format>(
        idst0, idst1, odst)));
}

ALWI void binary_right_shift_int32_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_right_shift<APPROX, InstrModLoadStore::INT32>(idst0, idst1, odst)));
}

// clang-format off
/**
 * Performs an elementwise logical shift operation to the right on the input at idst0, by input at idst1: y = x0 >> x1
 * Both inputs must be of Int32 data type only. Output overwrites odst in DST.
 *
 * The DST register buffer must be in acquired state via *acquire_dst* call. This call is blocking and is only available
 * on the compute engine.
 * A maximum of 4 tiles from each operand can be loaded into DST at once, for a total of 8 tiles,
 * when using 16 bit formats. This gets reduced to 2 tiles from each operand for 32 bit formats.
 *
 * Return value: None
 *
 * | Argument       | Description                                                           | Type     | Valid Range                                           | Required |
 * |----------------|-----------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst0          | The index of the tile in DST register buffer to use as first operand  | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | idst1          | The index of the tile in DST register buffer to use as second operand | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | odst           | The index of the tile in DST register buffer to use as output         | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void binary_logical_right_shift_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_logical_right_shift<APPROX>(idst0, idst1, odst)));
}

template <bool sign_magnitude_format = false>
ALWI void binary_logical_right_shift_uint32_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_logical_right_shift<APPROX, InstrModLoadStore::INT32, sign_magnitude_format>(
        idst0, idst1, odst)));
}

ALWI void binary_logical_right_shift_int32_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_logical_right_shift<APPROX, InstrModLoadStore::INT32>(idst0, idst1, odst)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void binary_shift_tile_init() { MATH((llk_math_eltwise_binary_sfpu_shift_init<APPROX>())); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/blank.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#ifdef TRISC_MATH
#define MAIN math_main()
#endif

#ifdef TRISC_PACK
#define MAIN pack_main()
#endif

#ifdef TRISC_UNPACK
#define MAIN unpack_main()
#endif
```

## tt_metal/include/compute_kernel_api/cb_api.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_PACK
#include "llk_io_pack.h"
#endif
#ifdef TRISC_UNPACK
#include "llk_io_unpack.h"
#endif

namespace ckernel {

// clang-format off
/**
 * A blocking call that waits for the specified number of tiles to be available in the specified circular buffer (CB).
 * This call is used by the consumer of the CB to wait for the producer to fill the CB with at least the specfied number
 * of tiles. Important note: in case multiple calls of cb_wait_front(n) are issued without a paired cb_pop_front() call,
 * n is expected to be incremented by the user to be equal to a cumulative total of tiles. Example: 4 calls of
 * cb_wait_front(8) followed by a cb_pop_front(32) would produce incorrect behavior. Instead 4 calls of cb_wait_front()
 * waiting on 8, 16, 24, 32 tiles should be issued.
 *
 * Important note: number of tiles used in all cb_* calls must evenly divide the cb size and must be the same number in
 * all cb_wait_front calls in the same kernel. Example 1: cb_wait_front(32), cb_wait_front(40), cb_pop_front(32+8) tiles
 * on a CB of size 64 would produce incorrect behavior. Example 2: cb_wait_front(3) on a cb of size 32 would also
 * produce incorrect behavior. These limitations are due to performance optimizations in the CB implementation.
 *
 * Important note: CB total size must be an even multiple of the argument passed to this call.
 *
 * Return value: None
 *
 * | Argument  | Description                          | Type     | Valid Range                                                                                       | Required |
 * |-----------|--------------------------------------|----------|---------------------------------------------------------------------------------------------------|----------|
 * | cb_id     | The index of the cirular buffer (CB) | uint32_t | 0 to 31                                                                                           | True     |
 * | ntiles    | The number of tiles to wait for      | uint32_t | It must be less or equal than the size of the CB (the total number of tiles that fit into the CB) | True     |
 * */
 // clang-format on
ALWI void cb_wait_front(uint32_t cbid, uint32_t ntiles) { UNPACK((llk_wait_tiles(cbid, ntiles))); }

// clang-format off
/**
 * Pops a specified number of tiles from the front of the specified CB. This
 * also frees this number of tiles in the circular buffer. This call is used by
 * the consumer to free up the space in the CB.
 *
 * We use the convention that the producer pushes tiles into the “back” of the
 * CB queue and the consumer consumes tiles from the “front” of the CB queue.
 *
 * Note that the act of reading of the tile data from the CB does not free up
 * the space in the CB. Waiting on available tiles and popping them is
 * separated in order to allow the consumer to: 1) read the tile data from the
 * CB via multiple reads of sub-tiles 2) access the tiles (or their sub-tiles)
 * that are visible to the consumer by random access of the valid section of
 * the CB
 *
 * Important note: This operation updates the read pointer of the CB, the CB pointer
 * can only be updated from one thread at a time. Example: if compute kernel has cb_pop_front(input_id, 1)
 * and writer kernel also has cb_pop_front(input_id, 1), these calls will produce non-deterministic behavior because
 * cb pointers are not synchronized across threads. Per circular buffer index, only have one thread pop tiles
 * to update the read pointer
 *
 * Return value: None
 *
 * | Argument  | Description                          | Type     | Valid Range                                                                                       | Required |
 * |-----------|--------------------------------------|----------|---------------------------------------------------------------------------------------------------|----------|
 * | cb_id     | The index of the cirular buffer (CB) | uint32_t | 0 to 31                                                                                           | True     |
 * | ntiles    | The number of tiles to be popped     | uint32_t | It must be less or equal than the size of the CB (the total number of tiles that fit into the CB) | True     |
 */
 // clang-format on
ALWI void cb_pop_front(uint32_t cbid, uint32_t ntiles) { UNPACK((llk_pop_tiles(cbid, ntiles))); }

// clang-format off
/**
 * A blocking call that waits for the specified number of tiles to be free in the specified circular buffer. This call
 * is used by the producer to wait for the consumer to consume (ie. free up) the specified number of tiles.
 *
 * CB total size must be an even multiple of the argument passed to this call.
 *
 * Return value: None
 *
 * | Argument  | Description                          | Type     | Valid Range                                                                                       | Required |
 * |-----------|--------------------------------------|----------|---------------------------------------------------------------------------------------------------|----------|
 * | cb_id     | The index of the cirular buffer (CB) | uint32_t | 0 to 31                                                                                           | True     |
 * | ntiles    | The number of free tiles to wait for | uint32_t | It must be less or equal than the size of the CB (the total number of tiles that fit into the CB) | True     |
 */
 // clang-format on
ALWI void cb_reserve_back(uint32_t cbid, uint32_t ntiles) {
    PACK((llk_wait_for_free_tiles<false, false, false>(cbid, ntiles)));
}

// clang-format off
/**
 * Pushes a given number of tiles in the back of the specified CB’s queue.
 * Decreases the available space in the circular buffer by this number of
 * tiles. This call is used by the producer to make the tiles visible to the
 * consumer of the CB.
 *
 * We use the convention that the producer pushes tiles into the “back” of the
 * CB queue and the consumer consumes tiles from the “front” of the CB queue.
 *
 * Note that the act of writing the tile data into the CB does not make the
 * tiles visible to the consumer. Writing of the tiles and pushing is separated
 * to allow the producer to: 1) write the tile data to the CB via multiple
 * writes of sub-tiles 2) modify tiles (or sub-tiles) by random access of the
 * valid section of the CB
 *
 * Important note: This operation updates the write pointer of the CB, the CB pointer
 * can only be updated from one thread at a time. Example: if compute kernel has cb_push_back(output_id, 1)
 * and reader kernel also has cb_push_back(output_id, 1), these calls will produce non-deterministic behavior because
 * cb pointers are not synchronized across threads. Per circular buffer index, only have one thread push tiles
 * to update the write pointer
 *
 * Return value: None
 *
 * | Argument  | Description                          | Type     | Valid Range                                                                                       | Required |
 * |-----------|--------------------------------------|----------|---------------------------------------------------------------------------------------------------|----------|
 * | cb_id     | The index of the cirular buffer (CB) | uint32_t | 0 to 31                                                                                           | True     |
 * | ntiles    | The number of tiles to be pushed     | uint32_t | It must be less or equal than the size of the CB (the total number of tiles that fit into the CB) | True     |
 */
 // clang-format on
ALWI void cb_push_back(uint32_t cbid, uint32_t ntiles) { PACK((llk_push_tiles<false, false>(cbid, ntiles))); }

// clang-format off
/**
 * Sends the pointer to the given tile index of the specified CB from the UNPACK
 * thread to the MATH and PACK threads, using mailbox writes. Also posts UNPACK_OPERAND_SYNC
 * semaphore for each of these threads.
 *
 * Return value: None
 *
 * | Argument  | Description                          | Type     | Valid Range                                                                                       | Required |
 * |-----------|--------------------------------------|----------|---------------------------------------------------------------------------------------------------|----------|
 * | cb_id     | The index of the cirular buffer (CB) | uint32_t | 0 to 31                                                                                           | True     |
 * | index     | The tile index within the CB         | uint32_t | It must be less or equal than the size of the CB (the total number of tiles that fit into the CB) | True     |
 * | p_tile    | The pointer that will be populated   | void*    | N/A                                                                                               | True     |
 */
 // clang-format on
ALWI void cb_get_tile(uint32_t cb_id, uint32_t index, volatile void* p_tile) {
    UNPACK(llk_unpack_get_tile(cb_id, index, (uint32_t*)p_tile));

    MATH(llk_math_get_tile(cb_id, index, (uint32_t*)p_tile));

    PACK(llk_pack_get_tile(cb_id, index, (uint32_t*)p_tile));
}

// clang-format off
/**
 * Blocks UNPACK thread on UNPACK_OPERAND_SYNC semaphore being decremented by
 * MATH and PACK threads.
 *
 * Return value: None
 *
 * | Argument  | Description                          | Type     | Valid Range | Required |
 * |-----------|--------------------------------------|----------|-------------|----------|
 * | cb_id     | The index of the cirular buffer (CB) | uint32_t | 0 to 31     | True     |
 */
 // clang-format on
ALWI void cb_release_tile(uint32_t cb_id) {
    UNPACK(llk_unpack_release_tile(cb_id));

    MATH(llk_math_release_tile(cb_id));

    PACK(llk_pack_release_tile(cb_id));
}

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/common.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#include "compute_kernel_api/reg_api.h"
#include "compute_kernel_api/pack.h"
#include "compute_kernel_api/reconfig_data_format.h"
#include "compute_kernel_api/cb_api.h"
#include "compute_kernel_api/compute_kernel_hw_startup.h"

extern uint32_t tt_l1_ptr* rta_l1_base;
extern uint32_t tt_l1_ptr* crta_l1_base;

// clang-format off
/**
 * Returns the address in L1 for a given runtime argument index for unique (per core) runtime arguments set via
 * SetRuntimeArgs() API.
 *
 * Return value: Associated L1 address of given unique runtime argument index
 *
 * | Argument       | Description                                                             | Type     | Valid Range | Required |
 * |----------------|-------------------------------------------------------------------------|----------|-------------|----------|
 * | arg_idx        | Unique Runtime argument index                                           | uint32_t | 0 to 341    | True     |
 */
// clang-format on
static FORCE_INLINE uint32_t get_arg_addr(int arg_idx) { return (uint32_t)&rta_l1_base[arg_idx]; }

// clang-format off
/**
 * Returns the address in L1 for a given runtime argument index for common (all cores) runtime arguments set via
 * SetCommonRuntimeArgs() API.
 *
 * Return value: Associated L1 address of given common runtime argument index
 *
 * | Argument       | Description                                                             | Type     | Valid Range | Required |
 * |----------------|-------------------------------------------------------------------------|----------|-------------|----------|
 * | arg_idx        | Common Runtime argument index                                           | uint32_t | 0 to 341    | True     |
 */
// clang-format on
static FORCE_INLINE uint32_t get_common_arg_addr(int arg_idx) { return (uint32_t)&crta_l1_base[arg_idx]; }

// clang-format off
/**
 * Returns the value at a given runtime argument index for unique (per-core) runtime arguments set via SetRuntimeArgs()
 * API.
 *
 * Return value: The value associated with the unique runtime argument index
 *
 * | Argument              | Description                                    | Type                  | Valid Range | Required |
 * |-----------------------|------------------------------------------------|-----------------------|-------------|----------|
 * | arg_idx               | Unique Runtime argument index                  | uint32_t              | 0 to 341    | True     |
 * | T (template argument) | Data type of the returned argument             | Any 4-byte sized type | N/A         | True     |
 */
// clang-format on
template <typename T>
FORCE_INLINE T get_arg_val(int arg_idx) {
    // only 4B args are supported (eg int32, uint32)
    static_assert("Error: only 4B args are supported" && sizeof(T) == 4);
    return *((tt_l1_ptr T*)(get_arg_addr(arg_idx)));
}

// clang-format off
/**
 * Returns the value at a given runtime argument index for common (all cores) runtime arguments set via
 * SetCommonRuntimeArgs() API.
 *
 * Return value: The value associated with the common runtime argument index
 *
 * | Argument              | Description                                    | Type                  | Valid Range | Required |
 * |-----------------------|------------------------------------------------|-----------------------|-------------|----------|
 * | arg_idx               | Common Runtime argument index                  | uint32_t              | 0 to 341    | True     |
 * | T (template argument) | Data type of the returned argument             | Any 4-byte sized type | N/A         | True     |
 */
// clang-format on
template <typename T>
FORCE_INLINE T get_common_arg_val(int arg_idx) {
    // only 4B args are supported (eg int32, uint32)
    static_assert("Error: only 4B args are supported" && sizeof(T) == 4);
    return *((tt_l1_ptr T*)(get_common_arg_addr(arg_idx)));
}

// clang-format off
/**
 * Returns the absolute logical X coordinate value that this kernel is running on. The absolute coordinate
 * is the one relative to the origin of the physical grid.
 *
 * Return value: X coordinate value.
 */
// clang-format on
inline uint8_t get_absolute_logical_x() {
    extern uint8_t my_logical_x_;  // Set in FW
    return my_logical_x_;
}

// clang-format off
/**
 * Returns the absolute logical Y coordinate value that this kernel is running on. The absolute coordinate
 * is the one relative to the origin of the physical grid.
 *
 * Return value: Y coordinate value.
 */
// clang-format on
inline uint8_t get_absolute_logical_y() {
    extern uint8_t my_logical_y_;  // Set in FW
    return my_logical_y_;
}

// clang-format off
/**
 * Returns the relative logical X coordinate value that this kernel is running on. The relative coordinate
 * is with respect to the origin of the sub device for this core type.
 *
 * Return value: X coordinate value.
 */
// clang-format on
inline uint8_t get_relative_logical_x() {
    extern uint8_t my_relative_x_;  // Set in FW
    return my_relative_x_;
}

// clang-format off
/**
 * Returns the relative logical Y coordinate value that this kernel is running on. The relative coordinate
 * is with respect to the origin of the sub device for this core type.
 *
 * Return value: Y coordinate value.
 */
// clang-format on
inline uint8_t get_relative_logical_y() {
    extern uint8_t my_relative_y_;  // Set in FW
    return my_relative_y_;
}
```

## tt_metal/include/compute_kernel_api/common_globals.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#define ALWI inline __attribute__((always_inline))

#include "chlkc_list.h"
#include "ckernel.h"
#include "firmware_common.h"
#include "ckernel_include.h"
#include "hostdevcommon/kernel_structs.h"

#ifdef TRISC_MATH
#include "llk_math_common_api.h"
#define MATH(x) x
#define MAIN math_main()
#else
#define MATH(x)
#endif

#ifdef TRISC_PACK
#include "llk_pack_api.h"
#define PACK(x) x
#define MAIN pack_main()
#else
#define PACK(x)
#endif

#ifdef TRISC_UNPACK
#include "llk_unpack_common_api.h"
#define UNPACK(x) x
#define MAIN unpack_main()
#else
#define UNPACK(x)
#endif
```

## tt_metal/include/compute_kernel_api/compute_kernel_hw_startup.h

```cpp
// SPDX-FileCopyrightText: © 2025 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common.h"

#ifdef TRISC_UNPACK
#include "llk_unpack_AB_api.h"
#endif

namespace ckernel {

// clang-format off
/**
 * Performs the required hardware initialization for all subsequent operations in the compute kernel. This function should be
 * called exactly once at the very beginning of the kernel, before any operation-specific initialization functions (such as
 * reduce_init, tilize_init, etc.). The circular buffer (CB) IDs provided to this function must match those used in the next
 * operation-specific initialization function. If the operands for the next operation require a different data format than
 * what was configured here, you must call one of the reconfig_data_format functions before proceeding with the next
 * initialization. Similarly, if the next operation requires different properties (such as tile or face dimensions), you must
 * ensure that the same CB IDs are used as in this function.
 *
 * NOTE: This function performs MMIO writes, which are slow and almost exclusively require the idle state of the execution
 * units that should be configured (PACK, MATH, UNPACK, CFG, etc.). This is why it is unsafe to call this function in the
 * middle of a kernel execution. This function should be called only once at the beginning of the kernel, before any other
 * calls to Compute API are made (either init or other). Calling this function after other API calls may lead cause race
 * conditions and undefined behavior which can be hard to debug.
 *
 * Return value: None
 *
 * | Param Type | Name  | Description                                                     | Type     | Valid Range | Required |
 * |------------|-------|-----------------------------------------------------------------|----------|-------------|----------|
 * | Function   | icb0  | The identifier of the circular buffer (CB) containing operand A | uint32_t | 0 to 31     | True     |
 * | Function   | icb1  | The identifier of the circular buffer (CB) containing operand B | uint32_t | 0 to 31     | True     |
 * | Function   | ocb   | The identifier of the output circular buffer (CB)               | uint32_t | 0 to 31     | True     |
 */
// clang-format on
ALWI void compute_kernel_hw_startup(uint32_t icb0, uint32_t icb1, uint32_t ocb) {
    UNPACK((llk_unpack_AB_hw_configure_disaggregated<DST_ACCUM_MODE>(icb0, icb1)));

    MATH((llk_math_pack_sync_init<DST_ACCUM_MODE>()));
    MATH((llk_math_hw_configure_disaggregated<false /*untilize*/, false /*skip_inputs*/>(icb0, icb1)));

    PACK((llk_pack_init<false /*untilize*/, false /*zero_output*/, false /*tilize*/>(ocb)));
    PACK((llk_pack_hw_configure_disaggregated<
          DST_ACCUM_MODE,
          false /*untilize*/,
          ReluType::NO_RELU,
          0 /*relu_treshold*/,
          false /*tilize*/>(ocb)));
    PACK((llk_pack_dest_init<DST_ACCUM_MODE, false /*untilize*/>(ocb)));
}

// clang-format off
/**
 * Convenience overload for hardware initialization when only one input circular buffer is used.
 * Both input operands (srcA and srcB) will be programmed using the same circular buffer identifier (`icb0`).
 * Internally, this calls the three-parameter version with `icb0` passed for both input operands.
 *
 * | Param Type | Name  | Description                                                        | Type     | Valid Range | Required |
 * |------------|-------|--------------------------------------------------------------------|----------|-------------|----------|
 * | Function   | icb0  | The identifier of the circular buffer (CB) used for both input ops | uint32_t | 0 to 31     | True     |
 * | Function   | ocb   | The identifier of the output circular buffer (CB)                  | uint32_t | 0 to 31     | True     |
 */
// clang-format on
ALWI void compute_kernel_hw_startup(uint32_t icb0, uint32_t ocb) { compute_kernel_hw_startup(icb0, icb0, ocb); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/copy_dest_values.h

```cpp
// SPDX-FileCopyrightText: © 2025 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_binary_sfpu_copy_dest_values.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

// clang-format off
/**
 * Copies all values from the tile in idst1 to the tile in idst0 in the DST register buffer.
 *
 * The DST register buffer must be in acquired state via *tile_regs_acquire* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                           | Type     | Valid Range                                           | Required |
 * |----------------|-----------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst0          | The index of the tile in DST register buffer to copy values to        | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | idst1          | The index of the tile in DST register buffer to copy values from      | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void copy_dest_values(uint32_t idst0, uint32_t idst1) {
    MATH(llk_math_eltwise_binary_sfpu_copy_dest_values(idst0, idst1));
}

ALWI void copy_dest_values_init() { MATH(llk_math_eltwise_binary_sfpu_copy_dest_values_init()); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/cumsum.h

```cpp
// SPDX-FileCopyrightText: © 2024 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_cumsum.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

// clang-format off
// Cumulative sum
/**
 * Calculates the columnwise (top to bottom) cumulative sum.
 * For multi tile comulative sum, tiles must come in NWH order (for example using reader_unary_transpose_wh) and
 * *first* must be false for all tiles where H != 0.
 * Tiles are also output in NWH order so writer_unary_transpose_wh can be used to store them correctly in L1
 * The DST register buffer must be in acquired state via *acquire_dst* call.
 * This call is blocking and is only available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | first           | Set true for tiles in the first row                                        | bool     |                                                       | False    |
 */
 // clang-format on
ALWI void cumsum_tile(uint32_t idst, bool first = true) {
    MATH((llk_math_eltwise_unary_sfpu_cumsum<false>(idst, first)));  // There is only non APPROXIMATE implementation
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void cumsum_tile_init() {
    MATH((llk_math_eltwise_unary_sfpu_cumsum_init<false>()));  // There is only non APPROXIMATE implementation
}

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_binary.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common.h"
#ifdef TRISC_MATH
#include "llk_math_binary_api.h"
#endif
#ifdef TRISC_UNPACK
#include "llk_unpack_AB_api.h"
#include "llk_unpack_A_api.h"
#endif

namespace ckernel {

// clang-format off
/**
 * Init function for all binary ops
 * Followed by the specific init required with an opcode (binrary_op_specific_init)
 *
 * | Argument       | Description                                                   | Type     | Valid Range                | Required |
 * |----------------|---------------------------------------------------------------|----------|----------------------------|----------|
 * | icb0           | The identifier of the circular buffer (CB) containing A       | uint32_t | 0 to 31                    | True     |
 * | icb1           | The identifier of the circular buffer (CB) containing B       | uint32_t | 0 to 31                    | True     |
 * | ocb            | The identifier of the circular buffer (CB) containing output  | uint32_t | 0 to 31, defaults to CB 16 | True     |
 */
// clang-format on
ALWI void binary_op_init_common(uint32_t icb0, uint32_t icb1, uint32_t ocb) {
    UNPACK((llk_unpack_AB_hw_configure_disaggregated<DST_ACCUM_MODE>(icb0, icb1)));
    UNPACK((llk_unpack_AB_init<BroadcastType::NONE>(icb0, icb1)));

    MATH((llk_math_pack_sync_init<DST_ACCUM_MODE>()));
    MATH((llk_math_hw_configure_disaggregated(icb0, icb1)));

    PACK((llk_pack_hw_configure_disaggregated<DST_ACCUM_MODE, false>(ocb)));
    PACK((llk_pack_init(ocb)));
    PACK((llk_pack_dest_init<DST_ACCUM_MODE, false>()));
}

// clang-format off
 /**
 * Template for initializing element-wise binary operations.
 * Template parameters:
 * full_init: if true, the full init is performed (unpack+math), otherwise only math init is performed
 * eltwise_binary_type: the binary operation type
 *
 * Function
 * | Argument       | Description                                                   | Type     | Valid Range | Required |
 * |----------------|---------------------------------------------------------------|----------|-------------|----------|
 * | icb0           | The identifier of the circular buffer (CB) containing A       | uint32_t | 0 to 31     | True     |
 * | icb1           | The identifier of the circular buffer (CB) containing B       | uint32_t | 0 to 31     | True     |
 * | acc_to_dest    | If true, operation = A [+,-,x] B + dst_tile_idx of *_tiles, depending on the eltwise_binary_type | bool | 0,1  | False |
 */
// clang-format on
template <bool full_init, EltwiseBinaryType eltwise_binary_type>
ALWI void binary_tiles_init(uint32_t icb0, uint32_t icb1, bool acc_to_dest = false) {
    MATH((llk_math_eltwise_binary_init_with_operands<eltwise_binary_type, NONE, MATH_FIDELITY>(
        icb0, icb1, 0 /*transpose*/, acc_to_dest)));

    if constexpr (full_init) {
        UNPACK((llk_unpack_AB_init<BroadcastType::NONE>(icb0, icb1, 0 /*transpose*/, acc_to_dest)));
    }
}

// clang-format off
/**
 * Short init function
 *
 * | Argument       | Description                                                   | Type     | Valid Range | Required |
 * |----------------|---------------------------------------------------------------|----------|-------------|----------|
 * | icb0           | The identifier of the circular buffer (CB) containing A       | uint32_t | 0 to 31     | True     |
 * | icb1           | The identifier of the circular buffer (CB) containing B       | uint32_t | 0 to 31     | True     |
 */
// clang-format on
ALWI void mul_tiles_init(uint32_t icb0, uint32_t icb1) { binary_tiles_init<true, ELWMUL>(icb0, icb1); }

// clang-format off
/**
 * Short init function
 *
 * | Argument       | Description                                                   | Type     | Valid Range | Required |
 * |----------------|---------------------------------------------------------------|----------|-------------|----------|
 * | icb0           | The identifier of the circular buffer (CB) containing A       | uint32_t | 0 to 31     | True     |
 * | icb1           | The identifier of the circular buffer (CB) containing B       | uint32_t | 0 to 31     | True     |
 * | acc_to_dest    | If true, operation = A + B + dst_tile_idx of add_tiles | bool     | 0,1         | False |
 */
// clang-format on
ALWI void add_tiles_init(uint32_t icb0, uint32_t icb1, bool acc_to_dest = false) {
    binary_tiles_init<true, ELWADD>(icb0, icb1, acc_to_dest);
}

// clang-format off
/**
 * Short init function
 *
 * | Argument       | Description                                                   | Type     | Valid Range | Required |
 * |----------------|---------------------------------------------------------------|----------|-------------|----------|
 * | icb0           | The identifier of the circular buffer (CB) containing A       | uint32_t | 0 to 31     | True     |
 * | icb1           | The identifier of the circular buffer (CB) containing B       | uint32_t | 0 to 31     | True     |
 * | acc_to_dest    | If true, operation = A - B + dst_tile_idx of sub_tiles | bool     | 0,1         | False |
 */
// clang-format on
ALWI void sub_tiles_init(uint32_t icb0, uint32_t icb1, bool acc_to_dest = false) {
    binary_tiles_init<true, ELWSUB>(icb0, icb1, acc_to_dest);
}

// clang-format off
/**
 * Performs element-wise multiplication C=A*B of tiles in two CBs at given
 * indices and writes the result to the DST register at index dst_tile_index.
 * The DST register buffer must be in acquired state via *acquire_dst* call.
 * This call is blocking and is only available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                              | Type     | Valid Range                                    | Required |
 * |----------------|----------------------------------------------------------|----------|------------------------------------------------|----------|
 * | in0_cb_id      | The identifier of the circular buffer (CB) containing A  | uint32_t | 0 to 31                                        | True     |
 * | in1_cb_id      | The identifier of the circular buffer (CB) containing B  | uint32_t | 0 to 31                                        | True     |
 * | in0_tile_index | The index of tile A within the first CB                  | uint32_t | Must be less than the size of the CB           | True     |
 * | in1_tile_index | The index of tile B within the second CB                 | uint32_t | Must be less than the size of the CB           | True     |
 * | dst_tile_index | The index of the tile in DST REG for the result C        | uint32_t | Must be less than the acquired size of DST REG | True     |
 */
// clang-format on
ALWI void mul_tiles(uint32_t icb0, uint32_t icb1, uint32_t itile0, uint32_t itile1, uint32_t idst) {
    // static bool first = true; // TODO(AP): static initializer causes a hang, possibly investigate
    // if (first)
    //  one possible solution is to add a local context in the kernel, pass it around and store init flags in it
    //  this way the compiler should be able to perform loop hoisting optimization
    //  - might need to add __attribute__((pure)) to init calls for this to work
    //  Also pass -fmove-loop-invariants to g++
    // mul_tiles_initf();
    // first = false;

    UNPACK((llk_unpack_AB(icb0, icb1, itile0, itile1)));
    MATH((llk_math_eltwise_binary<ELWMUL, NONE, DST_ACCUM_MODE, MATH_FIDELITY, EltwiseBinaryReuseDestType::NONE>(
        icb0, icb1, idst, true)));
}

// clang-format off
/**
 * Performs element-wise addition C=A+B of tiles in two CBs at given indices
 * and writes the result to the DST register at index dst_tile_index. The DST
 * register buffer must be in acquired state via *acquire_dst* call. This call
 * is blocking and is only available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                              | Type     | Valid Range                                    | Required |
 * |----------------|----------------------------------------------------------|----------|------------------------------------------------|----------|
 * | in0_cb_id      | The identifier of the circular buffer (CB) containing A  | uint32_t | 0 to 31                                        | True     |
 * | in1_cb_id      | The identifier of the circular buffer (CB) containing B  | uint32_t | 0 to 31                                        | True     |
 * | in0_tile_index | The index of tile A within the first CB                  | uint32_t | Must be less than the size of the CB           | True     |
 * | in1_tile_index | The index of tile B within the second CB                 | uint32_t | Must be less than the size of the CB           | True     |
 * | dst_tile_index | The index of the tile in DST REG for the result C        | uint32_t | Must be less than the acquired size of DST REG | True     |
 */
// clang-format on
ALWI void add_tiles(uint32_t icb0, uint32_t icb1, uint32_t itile0, uint32_t itile1, uint32_t idst) {
    UNPACK((llk_unpack_AB(icb0, icb1, itile0, itile1)));
    MATH((llk_math_eltwise_binary<ELWADD, NONE, DST_ACCUM_MODE, MATH_FIDELITY, EltwiseBinaryReuseDestType::NONE>(
        icb0, icb1, idst, true)));
}

// clang-format off
/**
 * Performs element-wise subtraction C=A-B of tiles in two CBs at given indices
 * and writes the result to the DST register at index dst_tile_index. The DST
 * register buffer must be in acquired state via *acquire_dst* call. This call
 * is blocking and is only available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                              | Type     | Valid Range                                    | Required |
 * |----------------|----------------------------------------------------------|----------|------------------------------------------------|----------|
 * | in0_cb_id      | The identifier of the circular buffer (CB) containing A  | uint32_t | 0 to 31                                        | True     |
 * | in1_cb_id      | The identifier of the circular buffer (CB) containing B  | uint32_t | 0 to 31                                        | True     |
 * | in0_tile_index | The index of tile A within the first CB                  | uint32_t | Must be less than the size of the CB           | True     |
 * | in1_tile_index | The index of tile B within the second CB                 | uint32_t | Must be less than the size of the CB           | True     |
 * | dst_tile_index | The index of the tile in DST REG for the result C        | uint32_t | Must be less than the acquired size of DST REG | True     |
 */
// clang-format on
ALWI void sub_tiles(uint32_t icb0, uint32_t icb1, uint32_t itile0, uint32_t itile1, uint32_t idst) {
    UNPACK((llk_unpack_AB(icb0, icb1, itile0, itile1)));
    MATH((llk_math_eltwise_binary<ELWSUB, NONE, DST_ACCUM_MODE, MATH_FIDELITY, EltwiseBinaryReuseDestType::NONE>(
        icb0, icb1, idst, true)));
}

/**
 * Please refer to documentation for any_init.
 */
template <
    EltwiseBinaryType eltwise_binary_type = ELWADD,
    EltwiseBinaryReuseDestType binary_reuse_dest = EltwiseBinaryReuseDestType::NONE>
ALWI void binary_dest_reuse_tiles_init(uint32_t icb0) {
    UNPACK((llk_unpack_A_init<BroadcastType::NONE, true, binary_reuse_dest>(false, false, icb0)));
    MATH((llk_math_eltwise_binary_init<eltwise_binary_type, NONE, MATH_FIDELITY, binary_reuse_dest>(false, false)));
}

// clang-format off
/**
 * Performs element-wise binary operations, such as multiply, add, or sub of tiles.
 * If binary_reuse_dest = EltwiseBinaryReuseDestType::DST_TO_SRCA, then the tile specified by idst will be loaded from
 * the DST register buffer into SRCA. The binary operation will operate on SRCA & SRCB inputs, and the result will be
 * written back to the DST register buffer specified by idst. Similar to DST_TO_SRCA, if binary_reuse_dest =
 * EltwiseBinaryReuseDestType::DST_TO_SRCB, then tile specified by idst will be loaded from the DST into SRCB register
 * buffer.
 *
 * EltwiseBinaryReuseDestType::DST_TO_SRCA and EltwiseBinaryReuseDestType::DST_TO_SRCB assume that another operation has
 * populated the dest register, otherwise dest will contain zeroes.
 *
 * The DST register buffer must be in acquired state via *acquire_dst* call.
 * This call is blocking and is only available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                                               | Type     | Valid Range                                    | Required |
 * |----------------|-----------------------------------------------------------------------------------------------------------|----------|------------------------------------------------|----------|
 * | in_cb_id       | The identifier of the circular buffer (CB) containing A                                                   | uint32_t | 0 to 31                                        | True     |
 * | in_tile_index  | The index of tile A within the first CB                                                                   | uint32_t | Must be less than the size of the CB           | True     |
 * | dst_tile_index | The index of tile B that will be moved to Src reg, and the index of the tile in DST REG for the result C  | uint32_t | Must be less than the acquired size of DST REG | True     |
 */
// clang-format on
template <
    EltwiseBinaryType eltwise_binary_type = ELWADD,
    EltwiseBinaryReuseDestType binary_reuse_dest = EltwiseBinaryReuseDestType::NONE>
ALWI void binary_dest_reuse_tiles(uint32_t in_cb_id, uint32_t in_tile_index, uint32_t dst_tile_index) {
    UNPACK((llk_unpack_A<BroadcastType::NONE, true, binary_reuse_dest>(in_cb_id, in_tile_index)));
    MATH((llk_math_eltwise_binary<eltwise_binary_type, NONE, DST_ACCUM_MODE, MATH_FIDELITY, binary_reuse_dest>(
        in_tile_index, in_tile_index, dst_tile_index, true)));
}

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_binary_sfpu.h

```cpp
// SPDX-FileCopyrightText: © 2024 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_binary_sfpu_binop.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

// clang-format off
/**
 * Performs an elementwise binop operation with the two floating point inputs: y = binop(x0,x1)
 * Output overwrites odst in DST.
 *
 * The DST register buffer must be in acquired state via *acquire_dst* call. This call is blocking and is only available
 * on the compute engine.
 * A maximum of 4 tiles from each operand can be loaded into DST at once, for a total of 8 tiles,
 * when using 16 bit formats. This gets reduced to 2 tiles from each operand for 32 bit formats.
 *
 * Return value: None
 *
 * | Argument       | Description                                                           | Type     | Valid Range                                           | Required |
 * |----------------|-----------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst0          | The index of the tile in DST register buffer to use as first operand  | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | idst1          | The index of the tile in DST register buffer to use as second operand | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | odst           | The index of the tile in DST register buffer to use as output         | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void add_binary_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_binop<APPROX, ckernel::BinaryOp::ADD>(idst0, idst1, odst)));
}

ALWI void sub_binary_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_binop<APPROX, ckernel::BinaryOp::SUB>(idst0, idst1, odst)));
}

ALWI void mul_binary_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_binop<APPROX, ckernel::BinaryOp::MUL>(idst0, idst1, odst)));
}

ALWI void div_binary_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_binop<APPROX, ckernel::BinaryOp::DIV>(idst0, idst1, odst)));
}

ALWI void rsub_binary_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_binop<APPROX, ckernel::BinaryOp::RSUB>(idst0, idst1, odst)));
}

ALWI void power_binary_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_binop<APPROX, ckernel::BinaryOp::POW, DST_ACCUM_MODE>(idst0, idst1, odst)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void add_binary_tile_init() { MATH((llk_math_eltwise_binary_sfpu_binop_init<APPROX, ckernel::BinaryOp::ADD>())); }

ALWI void sub_binary_tile_init() { MATH((llk_math_eltwise_binary_sfpu_binop_init<APPROX, ckernel::BinaryOp::SUB>())); }

ALWI void mul_binary_tile_init() { MATH((llk_math_eltwise_binary_sfpu_binop_init<APPROX, ckernel::BinaryOp::MUL>())); }

ALWI void div_binary_tile_init() { MATH((llk_math_eltwise_binary_sfpu_binop_init<APPROX, ckernel::BinaryOp::DIV>())); }

ALWI void rsub_binary_tile_init() {
    MATH((llk_math_eltwise_binary_sfpu_binop_init<APPROX, ckernel::BinaryOp::RSUB>()));
}

ALWI void power_binary_tile_init() {
    MATH((llk_math_eltwise_binary_sfpu_binop_init<APPROX, ckernel::BinaryOp::POW>()));
}

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/activations.h

```cpp
// SPDX-FileCopyrightText: © 2025 Tenstorrent AI ULC
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_activations.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

// clang-format off
/**
* Performs element-wise hardsigmoid operation. The DST
* register buffer must be in acquired state via *acquire_dst* call. This call is blocking and is only available on the
* compute engine.
*
* Return value: None
*
* | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
* |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
* | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
*/
// clang-format on
ALWI void hardsigmoid_tile(uint32_t idst) {
    MATH((llk_math_eltwise_unary_sfpu_hardsigmoid<APPROX, ckernel::ActivationType::Hardsigmoid>(idst)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void hardsigmoid_tile_init() { MATH((llk_math_eltwise_unary_sfpu_hardsigmoid_init<APPROX>())); }

// clang-format off
/**
* Performs element-wise softsign operation. The DST
* register buffer must be in acquired state via *acquire_dst* call. This call is blocking and is only available on the
* compute engine.
*
* Return value: None
*
* | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
* |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
* | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
*/
// clang-format on
ALWI void softsign_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_softsign<APPROX>(idst))); }

/**
 * Please refer to documentation for any_init.
 */
ALWI void softsign_tile_init() { MATH((llk_math_eltwise_unary_sfpu_softsign_init<APPROX>())); }

// clang-format off
/**
* Performs element-wise celu operation. The DST
* register buffer must be in acquired state via *acquire_dst* call. This call is blocking and is only available on the
* compute engine.
*
* Return value: None
*
* | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
* |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
* | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
* | alpha           | The alpha parameter for the CELU function                                  | uint32_t |                                                       | True     |
* | alpha_recip     | The reciprocal of the alpha parameter for the CELU function                | uint32_t |                                                       | True     |
*/
// clang-format on
ALWI void celu_tile(uint32_t idst, uint32_t alpha, uint32_t alpha_recip) {
    MATH((llk_math_eltwise_unary_sfpu_celu<APPROX, ckernel::ActivationType::Celu>(idst, alpha, alpha_recip)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void celu_tile_init() { MATH((llk_math_eltwise_unary_sfpu_celu_init<APPROX>())); }

// clang-format off
 /**
 * Performs element-wise softshrink operation. The DST
 * register buffer must be in acquired state via *acquire_dst* call. This call is blocking and is only available on the
 * compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | param0          | The λ value for the Softshrink formulation                                 | uint32   |                                                       | True     |
 */
 // clang-format on
 ALWI void softshrink_tile(uint32_t idst, uint32_t param0) {
    MATH((llk_math_eltwise_unary_sfpu_softshrink<APPROX>(idst, param0)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void softshrink_tile_init() { MATH((llk_math_eltwise_unary_sfpu_softshrink_init<APPROX>())); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/binop_with_scalar.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_binop_with_scalar.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

// clang-format off
/**
 * Performs a simple elementwise binop with scalar operation on the input: y = binop(x,scalar)
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                                 | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------------|----------|
 * | tile_index     | The index of the tile in DST register buffer to perform requested operation| uint32_t | Must be less than the size of the DST register buffer       | True     |
 * | mode           | 0, 1, 2, 3, and 4                                                          | uint32_t | 0, 1, 2, 3, 4 corresponding to add, mul, sub, div, and rsub | True     |
 * | param1         | fp32 value scalar encoded as uint32                                        | uint32_t | Must be less than the size of the DST register buffer       | True     |
 */
 // clang-format on
enum { ADD_UNARY = 0, SUB_UNARY = 1, MUL_UNARY = 2, DIV_UNARY = 3, RSUB_UNARY = 4 };
ALWI void add_unary_tile(uint32_t idst, uint32_t param1) {
    MATH((llk_math_eltwise_unary_sfpu_binop_with_scalar<APPROX, ADD_UNARY>(idst, param1)));
}

ALWI void sub_unary_tile(uint32_t idst, uint32_t param1) {
    MATH((llk_math_eltwise_unary_sfpu_binop_with_scalar<APPROX, SUB_UNARY>(idst, param1)));
}

ALWI void mul_unary_tile(uint32_t idst, uint32_t param1) {
    MATH((llk_math_eltwise_unary_sfpu_binop_with_scalar<APPROX, MUL_UNARY>(idst, param1)));
}

ALWI void div_unary_tile(uint32_t idst, uint32_t param1) {
    MATH((llk_math_eltwise_unary_sfpu_binop_with_scalar<APPROX, DIV_UNARY>(idst, param1)));
}

ALWI void rsub_unary_tile(uint32_t idst, uint32_t param1) {
    MATH((llk_math_eltwise_unary_sfpu_binop_with_scalar<APPROX, RSUB_UNARY>(idst, param1)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void binop_with_scalar_tile_init() { MATH((llk_math_eltwise_unary_sfpu_binop_with_scalar_init<APPROX>())); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/bitwise_and.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_bitwise_and.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

// clang-format off
/**
 * Performs element-wise bitwise_and computation on input x by y bits , where x is each element of a tile
 * in DST register at index tile_index. The input must be of int data type only. The value is provided as const param0
 * The DST register buffer must be in acquired state via *acquire_dst* call. This call is blocking and is only available
 * on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | param0          | The value the output is if the input is greater than 0                     | uint32_t |                                                       | True     |
 */
 // clang-format on
ALWI void bitwise_and_tile(uint32_t idst, uint32_t param0) {
    MATH((llk_math_eltwise_unary_sfpu_bitwise_and<APPROX>(idst, param0)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void bitwise_and_tile_init() { MATH((llk_math_eltwise_unary_sfpu_bitwise_and_init<APPROX>())); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/bitwise_not.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_bitwise_not.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

// clang-format off
/**
 * Performs element-wise bitwise_not computation on input x , where x is each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to modify the computation of  | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
 // clang-format on
ALWI void bitwise_not_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_bitwise_not<APPROX>(idst))); }

/**
 * Please refer to documentation for any_init.
 */
ALWI void bitwise_not_tile_init() { MATH((llk_math_eltwise_unary_sfpu_bitwise_not_init<APPROX>())); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/bitwise_or.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_bitwise_or.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

// clang-format off
/**
 * Performs element-wise bitwise_or computation on input x by y bits , where x is each element of a tile
 * in DST register at index tile_index. The input must be of int data type only. The value is provided as const param0
 * The DST register buffer must be in acquired state via *acquire_dst* call. This call is blocking and is only available
 * on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | param0          | The value the output is if the input is greater than 0                     | uint32_t |                                                       | True     |
 */
 // clang-format on
ALWI void bitwise_or_tile(uint32_t idst, uint32_t param0) {
    MATH((llk_math_eltwise_unary_sfpu_bitwise_or<APPROX>(idst, param0)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void bitwise_or_tile_init() { MATH((llk_math_eltwise_unary_sfpu_bitwise_or_init<APPROX>())); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/bitwise_xor.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_bitwise_xor.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

// clang-format off
/**
 * Performs element-wise bitwise_xor computation on input x , where x is each element of a tile
 * in DST register at index tile_index. The value is provided as const param0 The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking xor is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | param0          | The value the output is if the input is greater than 0                     | uint32_t |                                                       | True     |
 */
 // clang-format on
ALWI void bitwise_xor_tile(uint32_t idst, uint32_t param0) {
    MATH((llk_math_eltwise_unary_sfpu_bitwise_xor<APPROX>(idst, param0)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void bitwise_xor_tile_init() { MATH((llk_math_eltwise_unary_sfpu_bitwise_xor_init<APPROX>())); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/clamp.h

```cpp
// SPDX-FileCopyrightText: © 2025 Tenstorrent AI ULC
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_clamp.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

// clang-format off
/**
 * Performs element-wise clamp operation for float. The DST
 * register buffer must be in acquired state via *acquire_dst* call. This call is blocking and is only available on the
 * compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | param0          | The min value for the clamp function                                       | uint32_t |                                                       | True     |
 * | param1          | The max value for the clamp function                                       | uint32_t |                                                       | True     |
*/
// clang-format on
ALWI void clamp_tile(uint32_t idst, uint32_t param0, uint32_t param1) {
    MATH((llk_math_eltwise_unary_sfpu_clamp<APPROX>(idst, param0, param1)));
}

// clang-format off
/**
 * Performs element-wise clamp operation for int32. The DST
 * register buffer must be in acquired state via *acquire_dst* call. This call is blocking and is only available on the
 * compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | param0          | The min value for the clamp function                                       | uint32_t |                                                       | True     |
 * | param1          | The max value for the clamp function                                       | uint32_t |                                                       | True     |
 */
// clang-format on
ALWI void clamp_tile_int32(uint32_t idst, uint32_t param0, uint32_t param1) {
    MATH((llk_math_eltwise_unary_sfpu_clamp_int32<APPROX>(idst, param0, param1)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void clamp_tile_init() { MATH((llk_math_eltwise_unary_sfpu_clamp_init<APPROX>())); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/comp.h

```cpp
// SPDX-FileCopyrightText: © 2025 Tenstorrent AI ULC
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_comp.h"
#include "llk_math_eltwise_unary_sfpu_unary_comp.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

// unary ne : if x != value --> 1.0, else 0.0
// clang-format off
/**
 * Performs element-wise computation of:  result = 1.0 if x!=value , where x is each element of a tile
 * in DST register at index tile_index. The value is provided as const param0 The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | param0          | The value to be compared with the input tensor                             | uint32_t |                                                       | True     |
 */
// clang-format on
ALWI void unary_ne_tile(uint32_t idst, uint32_t param0) {
    MATH((llk_math_eltwise_unary_sfpu_unary_ne<APPROX>(idst, param0)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void unary_ne_tile_init() { MATH((llk_math_eltwise_unary_sfpu_unary_ne_init<APPROX>())); }

// unary ne : if x != value --> 1, else 0
// clang-format off
/**
 * Performs element-wise computation of:  result = 1 if x!=value , where x is each element of a tile
 * in DST register at index tile_index. The value is provided as const param0 The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | param0          | The value to be compared with the input tensor                             | uint32_t |                                                       | True     |
 */
// clang-format on
ALWI void unary_ne_tile_int32(uint32_t idst, uint32_t param0) {
    MATH((llk_math_eltwise_unary_sfpu_unary_ne_int32<APPROX>(idst, param0)));
}

// unary eq : if x == value --> 1.0, else 0.0
// clang-format off
/**
 * Performs element-wise computation of:  result = 1.0 if x==value , where x is each element of a tile
 * in DST register at index tile_index. The value is provided as const param0 The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | param0          | The value to be compared with the input tensor                             | uint32_t |                                                       | True     |
 */
// clang-format on
ALWI void unary_eq_tile(uint32_t idst, uint32_t param0) {
    MATH((llk_math_eltwise_unary_sfpu_unary_eq<APPROX>(idst, param0)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void unary_eq_tile_init() { MATH((llk_math_eltwise_unary_sfpu_unary_eq_init<APPROX>())); }

// unary eq : if x == value --> 1, else 0
// clang-format off
/**
 * Performs element-wise computation of:  result = 1 if x==value , where x is each element of a tile
 * in DST register at index tile_index. The value is provided as const param0 The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | param0          | The value to be compared with the input tensor                             | uint32_t |                                                       | True     |
 */
// clang-format on
ALWI void unary_eq_tile_int32(uint32_t idst, uint32_t param0) {
    MATH((llk_math_eltwise_unary_sfpu_unary_eq_int32<APPROX>(idst, param0)));
}

// unary gt : if x > value --> 1.0, else 0.0
// clang-format off
/**
 * Performs element-wise computation of:  result = 1 if x > value , where x is each element of a tile
 * in DST register at index tile_index. The value is provided as const param0 The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | param0          | The value to be compared with the input tensor                             | uint32_t |                                                       | True     |
 */
// clang-format on
ALWI void unary_gt_tile(uint32_t idst, uint32_t param0) {
    MATH((llk_math_eltwise_unary_sfpu_unary_gt<APPROX>(idst, param0)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void unary_gt_tile_init() { MATH((llk_math_eltwise_unary_sfpu_unary_gt_init<APPROX>())); }

// unary gt : if x > value --> 1, else 0
// clang-format off
/**
 * Performs element-wise computation of:  result = 1 if x>value , where x is each element of a tile
 * in DST register at index tile_index. The value is provided as const param0 The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | param0          | The value to be compared with the input tensor                             | uint32_t |                                                       | True     |
 */
// clang-format on
ALWI void unary_gt_tile_int32(uint32_t idst, uint32_t param0) {
    MATH((llk_math_eltwise_unary_sfpu_unary_gt_int32<APPROX>(idst, param0)));
}

// unary ge : if x >= value --> 1.0, else 0.0
// clang-format off
/**
 * Performs element-wise computation of:  result = 1 if x >= value , where x is each element of a tile
 * in DST register at index tile_index. The value is provided as const param0 The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | param0          | The value to be compared with the input tensor                             | uint32_t |                                                       | True     |
 */
// clang-format on
ALWI void unary_ge_tile(uint32_t idst, uint32_t param0) {
    MATH((llk_math_eltwise_unary_sfpu_unary_ge<APPROX>(idst, param0)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void unary_ge_tile_init() { MATH((llk_math_eltwise_unary_sfpu_unary_ge_init<APPROX>())); }

// unary ge : if x >= value --> 1, else 0
// clang-format off
/**
 * Performs element-wise computation of:  result = 1 if x>value , where x is each element of a tile
 * in DST register at index tile_index. The value is provided as const param0 The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | param0          | The value to be compared with the input tensor                             | uint32_t |                                                       | True     |
 */
// clang-format on
ALWI void unary_ge_tile_int32(uint32_t idst, uint32_t param0) {
    MATH((llk_math_eltwise_unary_sfpu_unary_ge_int32<APPROX>(idst, param0)));
}

// unary lt : if x < value --> 1.0, else 0.0
// clang-format off
/**
 * Performs element-wise computation of:  result = 1 if x < value , where x is each element of a tile
 * in DST register at index tile_index. The value is provided as const param0 The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | param0          | The value to be compared with the input tensor                             | uint32_t |                                                       | True     |
 */
// clang-format on
ALWI void unary_lt_tile(uint32_t idst, uint32_t param0) {
    MATH((llk_math_eltwise_unary_sfpu_unary_lt<APPROX>(idst, param0)));
}

// unary lt : if x < value --> 1, else 0
// clang-format off
/**
 * Performs element-wise computation of:  result = 1 if x<value , where x is each element of a tile
 * in DST register at index tile_index. The value is provided as const param0 The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | param0          | The value to be compared with the input tensor                             | uint32_t |                                                       | True     |
 */
// clang-format on
ALWI void unary_lt_tile_int32(uint32_t idst, uint32_t param0) {
    MATH((llk_math_eltwise_unary_sfpu_unary_lt_int32<APPROX>(idst, param0)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void unary_lt_tile_init() { MATH((llk_math_eltwise_unary_sfpu_unary_lt_init<APPROX>())); }

// unary le : if x <= value --> 1.0, else 0.0
// clang-format off
/**
 * Performs element-wise computation of:  result = 1 if x <= value , where x is each element of a tile
 * in DST register at index tile_index. The value is provided as const param0 The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | param0          | The value to be compared with the input tensor                             | uint32_t |                                                       | True     |
 */
// clang-format on
ALWI void unary_le_tile(uint32_t idst, uint32_t param0) {
    MATH((llk_math_eltwise_unary_sfpu_unary_le<APPROX>(idst, param0)));
}

// unary le : if x <= value --> 1, else 0
// clang-format off
/**
 * Performs element-wise computation of:  result = 1 if x<value , where x is each element of a tile
 * in DST register at index tile_index. The value is provided as const param0 The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | param0          | The value to be compared with the input tensor                             | uint32_t |                                                       | True     |
 */
// clang-format on
ALWI void unary_le_tile_int32(uint32_t idst, uint32_t param0) {
    MATH((llk_math_eltwise_unary_sfpu_unary_le_int32<APPROX>(idst, param0)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void unary_le_tile_init() { MATH((llk_math_eltwise_unary_sfpu_unary_le_init<APPROX>())); }

// clang-format off
/**
 * Will store in the output of the compute core True if each element is greater than zero.
 * The DST register buffer must be in acquired state via *acquire_dst* call.
 * This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst           | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void gtz_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_gtz<APPROX>(idst))); }

// clang-format off
/**
 * Will store in the output of the compute core True if each element is greater than zero.
 * The DST register buffer must be in acquired state via *acquire_dst* call.
 * This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst           | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void gtz_tile_int32(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_gtz_int32<APPROX>(idst))); }

/**
 * Please refer to documentation for any_init.
 */
ALWI void gtz_tile_init() { MATH((llk_math_eltwise_unary_sfpu_gtz_init<APPROX>())); }

// clang-format off
/**
 * Will store in the output of the compute core True if each element is not equal to zero.
 * The DST register buffer must be in acquired state via *acquire_dst* call.
 * This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst           | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void nez_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_nez<APPROX>(idst))); }

// clang-format off
/**
 * Will store in the output of the compute core True if each element is not equal to zero.
 * The DST register buffer must be in acquired state via *acquire_dst* call.
 * This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst           | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void nez_tile_int32(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_nez_int32<APPROX>(idst))); }

/**
 * Please refer to documentation for any_init.
 */
ALWI void nez_tile_init() { MATH((llk_math_eltwise_unary_sfpu_nez_init<APPROX>())); }

// clang-format off
/**
 * Will store in the output of the compute core True if each element is greater than or equal to zero.
 * The DST register buffer must be in acquired state via *acquire_dst* call.
 * This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst           | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void gez_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_gez<APPROX>(idst))); }

// clang-format off
/**
 * Will store in the output of the compute core True if each element is greater than or equal to zero.
 * The DST register buffer must be in acquired state via *acquire_dst* call.
 * This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst           | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void gez_tile_int32(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_gez_int32<APPROX>(idst))); }

/**
 * Please refer to documentation for any_init.
 */
ALWI void gez_tile_init() { MATH((llk_math_eltwise_unary_sfpu_gez_init<APPROX>())); }

// clang-format off
/**
 * Will store in the output of the compute core True if each element of a tile is less than zero.
 * The DST register buffer must be in acquired state via *acquire_dst* call.
 * This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst           | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void ltz_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_ltz<APPROX>(idst))); }

// clang-format off
/**
 * Will store in the output of the compute core True if each element of a tile is less than zero.
 * The DST register buffer must be in acquired state via *acquire_dst* call.
 * This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst           | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void ltz_tile_int32(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_ltz_int32<APPROX>(idst))); }

/**
 * Please refer to documentation for any_init.
 */
ALWI void ltz_tile_init() { MATH((llk_math_eltwise_unary_sfpu_ltz_init<APPROX>())); }

// clang-format off
/**
 * Will store in the output of the compute core True if each element of a tile is equal to zero.
 * The DST register buffer must be in acquired state via *acquire_dst* call.
 * This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst           | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void eqz_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_eqz<APPROX>(idst))); }

// clang-format off
/**
 * Will store in the output of the compute core True if each element of a tile is equal to zero.
 * The DST register buffer must be in acquired state via *acquire_dst* call.
 * This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst           | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void eqz_tile_int32(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_eqz_int32<APPROX>(idst))); }

// clang-format off
/**
 * Will store in the output of the compute core True if each element of a tile is equal to zero.
 * The DST register buffer must be in acquired state via *acquire_dst* call.
 * This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst           | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void eqz_tile_uint16(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_eqz_uint16<APPROX>(idst))); }

// clang-format off

/**
 * Will store in the output of the compute core True if each element of a tile is equal to zero.
 * The DST register buffer must be in acquired state via *acquire_dst* call.
 * This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst           | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void eqz_tile_uint32(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_eqz_uint32<APPROX>(idst))); }

/**
 * Please refer to documentation for any_init.
 */
ALWI void eqz_tile_init() { MATH((llk_math_eltwise_unary_sfpu_eqz_init<APPROX>())); }

// clang-format off
/**
 * Will store in the output of the compute core True if each element is less than or equal to zero.
 * The DST register buffer must be in acquired state via *acquire_dst* call.
 * This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst           | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void lez_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_lez<APPROX>(idst))); }

// clang-format off
/**
 * Will store in the output of the compute core True if each element is less than or equal to zero.
 * The DST register buffer must be in acquired state via *acquire_dst* call.
 * This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst           | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void lez_tile_int32(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_lez_int32<APPROX>(idst))); }

// clang-format off
/**
 * Will store in the output of the compute core True if each element is not equal to zero.
 * The DST register buffer must be in acquired state via *acquire_dst* call.
 * This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst           | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void nez_tile_uint16(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_nez_uint16<APPROX>(idst))); }

// clang-format off
/**
 * Will store in the output of the compute core True if each element is not equal to zero.
 * The DST register buffer must be in acquired state via *acquire_dst* call.
 * This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst           | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void nez_tile_uint32(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_nez_uint32<APPROX>(idst))); }

/**
 * Please refer to documentation for any_init.
 */
ALWI void lez_tile_init() { MATH((llk_math_eltwise_unary_sfpu_lez_init<APPROX>())); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/dropout.h

```cpp
// SPDX-FileCopyrightText: © 2024 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_dropout.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

// clang-format off
/**
 * Performs element-wise dropout on each element of a of a tile in DST register at index tile_index.
 * That is each element may be zeroed out based on a given probability or it may be scaled by a given
 * scale factor. The DST register buffer must be in acquired state via *acquire_dst* call. This
 * call is blocking and is only available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | tile_index      | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | probability     | A non-negative integer value representing dropout probability              | uint32_t | 0 to INT_MAX (float_probability * (double) INT_MAX)   | True     |
 * | scale_factor    | uint bitwise representation of 32 bit floating point scale factor          | uint32_t |                                                       | True     |
 */
 // clang-format on
ALWI void dropout_tile(uint32_t idst, uint32_t probability, uint32_t scale_factor) {
    MATH((llk_math_eltwise_unary_sfpu_dropout<APPROX>(idst, probability, scale_factor)));
}

/**
 * This init should be called once in kernel
 */
ALWI void dropout_kernel_init(uint32_t seed) { MATH((llk_math_eltwise_unary_sfpu_dropout_init<APPROX>(seed))); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/eltwise_unary.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common.h"
#ifdef TRISC_MATH
#include "llk_math_unary_datacopy_api.h"
#endif
#ifdef TRISC_UNPACK
#include "llk_unpack_A_api.h"
#endif

namespace ckernel {

ALWI void unary_op_init_common(uint32_t icb, uint32_t ocb) {
    UNPACK((llk_unpack_A_hw_configure_disaggregated<DST_ACCUM_MODE, StochRndType::None, true>(icb)));
    UNPACK((llk_unpack_A_init<BroadcastType::NONE, false, EltwiseBinaryReuseDestType::NONE, UnpackToDestEn>(
        false /*transpose of faces*/, false /*transpose within 16x16 face*/, icb)));

    PACK((llk_pack_hw_configure_disaggregated<DST_ACCUM_MODE, false>(ocb)));
    PACK((llk_pack_init<false>(ocb)));
    PACK((llk_pack_dest_init<DST_ACCUM_MODE, false>()));

    MATH((llk_math_eltwise_unary_datacopy_init<A2D, DST_ACCUM_MODE, BroadcastType::NONE>(
        false /*transpose of faces*/, false /*transpose within 16x16 face*/, icb)));
    MATH((llk_math_pack_sync_init<DST_ACCUM_MODE>()));
    MATH((llk_math_hw_configure_disaggregated(icb, icb)));
}

// clang-format off
/**
 * no_pack variant of unary_op_init_common, to be used with tilize_*_no_pack variants.
 *
 * Note: This function does not configure PACK thread, use with caution.
 */
// clang-format on
ALWI void unary_op_init_common_no_pack(uint32_t icb) {
    UNPACK((llk_unpack_A_hw_configure_disaggregated<DST_ACCUM_MODE, StochRndType::None, true>(icb)));
    UNPACK((llk_unpack_A_init<BroadcastType::NONE, false, EltwiseBinaryReuseDestType::NONE, UnpackToDestEn>(
        false /*transpose of faces*/, false /*transpose within 16x16 face*/, icb)));

    MATH((llk_math_eltwise_unary_datacopy_init<A2D, DST_ACCUM_MODE, BroadcastType::NONE>(
        false /*transpose of faces*/, false /*transpose within 16x16 face*/, icb)));
    MATH((llk_math_hw_configure_disaggregated(icb, icb)));
}

ALWI void init_sfpu(uint32_t icb, uint32_t ocb) { unary_op_init_common(icb, ocb); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/elu.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_elu.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

// clang-format off
/**
 * Performs element-wise computation of elu (relu(x) + slope*(exp(x) - 1)*(x <= 0 )) on each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | tile_index     | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | slope          | slope used in elu calculation                                              | uint32_t | Greater than 0                                        | True     |
 */
 // clang-format on
ALWI void elu_tile(uint32_t idst, uint32_t param0) { MATH((llk_math_eltwise_unary_sfpu_elu<APPROX>(idst, param0))); }

/**
 * Please refer to documentation for any_init.
 */
ALWI void elu_tile_init() { MATH((llk_math_eltwise_unary_sfpu_elu_init<APPROX>())); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/erf_erfc.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_erf_erfc.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

/************** ERF *****************/
/**
 * Please refer to documentation for any_init.
 */
template <bool fast_and_approx = true>
ALWI void erf_tile_init() {
    MATH((llk_math_eltwise_unary_sfpu_erf_init<fast_and_approx>()));
}

// clang-format off
/**
 * Performs element-wise computation of error function on each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | tile_index     | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
 // clang-format on
template <bool fast_and_approx = true>
ALWI void erf_tile(uint32_t idst) {
    MATH((llk_math_eltwise_unary_sfpu_erf<fast_and_approx>(idst)));
}

/************** ERFC *****************/

/**
 * Please refer to documentation for any_init.
 */
template <bool fast_and_approx = true>
ALWI void erfc_tile_init() {
    MATH((llk_math_eltwise_unary_sfpu_erfc_init<fast_and_approx>()));
}

// clang-format off
/**
 * Performs element-wise computation of complimentary error function on each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | tile_index     | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
 // clang-format on
template <bool fast_and_approx = true>
ALWI void erfc_tile(uint32_t idst) {
    MATH((llk_math_eltwise_unary_sfpu_erfc<fast_and_approx>(idst)));
}

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/erfinv.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_erfinv.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {
// clang-format off
/**
 * Performs element-wise computation of the inverse of the error function on each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | tile_index     | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
 // clang-format on
ALWI void erfinv_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_erfinv_op<APPROX>(idst))); }

/**
 * Please refer to documentation for any_init.
 */
ALWI void erfinv_tile_init() { MATH((llk_math_eltwise_unary_sfpu_erfinv_init<APPROX>())); }
}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/exp.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_exp.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

/**
 * Please refer to documentation for any_init.
 *
 * Template scale parameter is used when aprox and fast_and_approx are true and exp_tile is called with scale_en set to
 * true.
 *
 */
template <bool approx = false, bool fast_and_approx = true, uint32_t scale = 0x3F800000>
ALWI void exp_tile_init() {
    MATH((llk_math_eltwise_unary_sfpu_exponential_init<approx, fast_and_approx, scale>()));
}

// clang-format off
/**
 * Performs element-wise computation of exponential on each element of a tile
 * in the DST register. The DST register buffer must be in an
 * acquired state via an *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Template Parameter      | Description                                                    | Type     | Valid Range      | Default |
 * |-------------------------|----------------------------------------------------------------|----------|------------------|---------|
 * | approx                  | Enable approximate mode.                                       | bool     | true, false      | false   |
 * | fast_and_approx         | If approx is true, enable fast approximation.                  | bool     | true, false      | true   |
 * | scale_en                | Enable input scaling by a constant factor in approximate or non-approximate mode | bool     | true, false      | false   |
 * | skip_positive_check     | Skip large-positive input check                                | bool     | true, false      | false   |
 * | iterations              | Number of iterations over 32-SFPU lanes to run                 | int      | Positive integer | 8       |
 *
 * | Argument    | Description                                                                | Type     | Valid Range                                           | Required |
 * |-------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst        | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | vector_mode | Specifies the vector mode for computation (default: VectorMode::RC)        | int      | Subject to specific hardware/kernel limits            | False    |
 * | scale       | Scale factor to apply in approximate or non-approximate mode if scale_en is true (default: 0x3F80, 1.0f in FP16b) | uint16_t | Valid FP16b representation                            | False    |
 */
// clang-format on
template <
    bool approx = false,
    bool fast_and_approx = true,
    bool scale_en = false,
    bool skip_positive_check = false,
    int iterations = 8>
ALWI void exp_tile(uint32_t idst, int vector_mode = (int)VectorMode::RC, uint16_t scale = p_sfpu::kCONST_1_FP16B) {
    MATH((llk_math_eltwise_unary_sfpu_exponential<
          approx,
          fast_and_approx,
          scale_en,
          skip_positive_check,
          iterations,
          DST_ACCUM_MODE>(idst, vector_mode, scale)));
}

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/fill.h

```cpp
// SPDX-FileCopyrightText: © 2025 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_fill.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

// clang-format off
/**
 * Performs element-wise fill operation. The value to be filled in the tile is provided as const param0. The DST
 * register buffer must be in acquired state via *acquire_dst* call. This call is blocking and is only available on the
 * compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | param0          | The value the output is if the input is greater than 0                     | float    |                                                       | True     |
 */
// clang-format on
ALWI void fill_tile(uint32_t idst, float param0) { MATH((llk_math_eltwise_unary_sfpu_fill<APPROX>(idst, param0))); }

ALWI void fill_tile_int(uint32_t idst, uint param0) {
    MATH((llk_math_eltwise_unary_sfpu_fill_int<APPROX>(idst, param0)));
}

// clang-format off
/**
 * Performs element-wise fill operation. The value to be filled in the tile is provided as const param0, which is
 * interpreted as a bit-cast representation of a floating-point value. The DST register buffer must be in acquired
 * state via *acquire_dst* call. This call is blocking and is only available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | param0          | The bit-cast representation of a floating-point value to be used as output | uint32_t | Must represent a valid bit-cast float value           | True     |
 */
// clang-format on
ALWI void fill_tile_bitcast(uint32_t idst, uint32_t param0) {
    MATH((llk_math_eltwise_unary_sfpu_fill_bitcast<APPROX>(idst, param0)));
}
/**
 * Please refer to documentation for any_init.
 */
ALWI void fill_tile_init() { MATH((llk_math_eltwise_unary_sfpu_fill_init<APPROX>())); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/fmod.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_fmod.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

// clang-format off
/**
 * Performs element-wise fmod computation on input x by y , where x is each element of a tile
 * in DST register at index tile_index. The input can be of float data type. The value is provided as const param0 The
 * DST register buffer must be in acquired state via *acquire_dst* call. This call is blocking and is only available on
 * the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                 | Type     | Valid Range                                           | Required |
 * |----------------|-----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst           | The index of the tile in DST register buffer to perform fmod operation      | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | param0         | Denominator value to perform fmod operation                                 | uint32_t |                                                       | True     |
 * | param1         | Reciprocal of param0, calculated on-host                                    | uint32_t |                                                       | False    |
 */
// clang-format on
ALWI void fmod_tile(uint32_t idst, uint32_t param0, uint32_t param1) {
    MATH((llk_math_eltwise_unary_sfpu_fmod<APPROX>(idst, param0, param1)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void fmod_tile_init(uint32_t param0, uint32_t param1) {
    MATH((llk_math_eltwise_unary_sfpu_fmod_init<APPROX>(param0, param1)));
}

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/gelu.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_gelu.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

/**
 * Please refer to documentation for any_init.
 */
template <bool fast_and_approx = true>
ALWI void gelu_tile_init() {
    MATH((llk_math_eltwise_unary_sfpu_gelu_init<fast_and_approx>()));
}

// clang-format off
/**
 * Performs element-wise computation of gelu  on each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument         | Description                                                                | Type     | Valid Range                                           | Required |
 * |------------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | tile_index       | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | fast_and_approx  | Computation to be done faster and approximate                              | bool     |                                                       | False    |
 */
 // clang-format on
template <bool fast_and_approx = true>
ALWI void gelu_tile(uint32_t idst) {
    MATH((llk_math_eltwise_unary_sfpu_gelu<fast_and_approx>(idst)));
}

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/hardtanh.h

```cpp
// SPDX-FileCopyrightText: © 2025 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_hardtanh.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

// clang-format off
 /**
 * Performs element-wise hardtanh operation. The DST
 * register buffer must be in acquired state via *acquire_dst* call. This call is blocking and is only available on the
 * compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | param0          | The minimum value of the linear region range                               | uint32_t |                                                       | True     |
 * | param1          | The maximum value of the linear region range                               | uint32_t |                                                       | True     |

 */
// clang-format on
ALWI void hardtanh_tile(uint32_t idst, uint32_t param0, uint32_t param1) {
    MATH((llk_math_eltwise_unary_sfpu_hardtanh<APPROX>(idst, param0, param1)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void hardtanh_tile_init() { MATH((llk_math_eltwise_unary_sfpu_hardtanh_init<APPROX>())); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/i0.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_i0.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {
// clang-format off
/**
 * Performs element-wise computation of the zeroth order modified Bessel function of the first kind on each element of a
 * tile in DST register at index tile_index. The DST register buffer must be in acquired state via *acquire_dst* call.
 * This call is blocking and is only available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | tile_index     | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
 // clang-format on
ALWI void i0_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_i0_op<APPROX>(idst))); }

/**
 * Please refer to documentation for any_init.
 */
ALWI void i0_tile_init() { MATH((llk_math_eltwise_unary_sfpu_i0_init<APPROX>())); }
}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/i1.h

```cpp
// SPDX-FileCopyrightText: © 2024 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_i1.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

// clang-format off
/**
 * Performs element-wise computation of the first order modified Bessel function of the first kind on each element of a
 * tile in DST register at index tile_index. The DST register buffer must be in acquired state via *acquire_dst* call.
 * This call is blocking and is only available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | tile_index     | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
 // clang-format on
ALWI void i1_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_i1_op<APPROX>(idst))); }

/**
 * Please refer to documentation for any_init.
 */
ALWI void i1_tile_init() { MATH((llk_math_eltwise_unary_sfpu_i1_init<APPROX>())); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/identity.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_identity.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

// clang-format off
/**
 * Performs a simple elementwise copy / identity operation on the input: y(x) = x
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | tile_index     | The index of the tile in DST register buffer to perform identity operation | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
 // clang-format on
ALWI void identity_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_identity<APPROX>(idst))); }

/**
 * Please refer to documentation for any_init.
 */
ALWI void identity_tile_init() { MATH((llk_math_eltwise_unary_sfpu_identity_init<APPROX>())); }

// clang-format off
/**
 * Performs a simple elementwise copy / identity operation on the input: y(x) = x
 * This function should be used with unsigned integer formats: uint32
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | tile_index     | The index of the tile in DST register buffer to perform identity operation | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
 // clang-format on
ALWI void identity_tile_uint32(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_identity_uint32<APPROX>(idst))); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/isinf_isnan.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_isinf_isnan.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {
// clang-format off
/**
 * Will store in the output of the compute core True if the input tile is infinity.
 * The DST register buffer must be in acquired state via *acquire_dst* call.
 * This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | tile_index     | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
 // clang-format on
ALWI void isinf_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_isinf<APPROX>(idst))); }

/**
 * Please refer to documentation for any_init.
 */
ALWI void isinf_tile_init() { MATH((llk_math_eltwise_unary_sfpu_isinf_init<APPROX>())); }

// clang-format off
/**
 * Will store in the output of the compute core True if the input tile is positive infinity.
 * The DST register buffer must be in acquired state via *acquire_dst* call.
 * This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | tile_index     | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
 // clang-format on
ALWI void isposinf_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_isposinf<APPROX>(idst))); }

/**
 * Please refer to documentation for any_init.
 */
ALWI void isposinf_tile_init() { MATH((llk_math_eltwise_unary_sfpu_isposinf_init<APPROX>())); }

// clang-format off
/**
 * Will store in the output of the compute core True if the input tile is negative infinity.
 * The DST register buffer must be in acquired state via *acquire_dst* call.
 * This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | tile_index     | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
 // clang-format on
ALWI void isneginf_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_isneginf<APPROX>(idst))); }

/**
 * Please refer to documentation for any_init.
 */
ALWI void isneginf_tile_init() { MATH((llk_math_eltwise_unary_sfpu_isneginf_init<APPROX>())); }

// clang-format off
/**
 * Will store in the output of the compute core True if the input tile is nan.
 * The DST register buffer must be in acquired state via *acquire_dst* call.
 * This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | tile_index     | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
 // clang-format on
ALWI void isnan_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_isnan<APPROX>(idst))); }

/**
 * Please refer to documentation for any_init.
 */
ALWI void isnan_tile_init() { MATH((llk_math_eltwise_unary_sfpu_isnan_init<APPROX>())); }

// clang-format off
/**
 * Will store in the output of the compute core True if the input tile is finite
 * The DST register buffer must be in acquired state via *acquire_dst* call.
 * This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | tile_index     | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
 // clang-format on
ALWI void isfinite_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_isfinite<APPROX>(idst))); }

/**
 * Please refer to documentation for any_init.
 */
ALWI void isfinite_tile_init() { MATH((llk_math_eltwise_unary_sfpu_isfinite_init<APPROX>())); }
}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/left_shift.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_left_shift.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

// clang-format off
/**
 * Performs element-wise left_shift computation on input x by y bits , where x is each element of a tile
 * in DST register at index tile_index. The input must be of int data type only. The value is provided as const param0
 * The DST register buffer must be in acquired state via *acquire_dst* call. This call is blocking and is only available
 * on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | param0          | The value the output is if the input is greater than 0                     | uint32_t |                                                       | True     |
 */
 // clang-format on
ALWI void left_shift_tile(uint32_t idst, uint32_t param0) {
    MATH((llk_math_eltwise_unary_sfpu_left_shift<APPROX>(idst, param0)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void left_shift_tile_init() { MATH((llk_math_eltwise_unary_sfpu_left_shift_init<APPROX>())); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/log1p.h

```cpp
// SPDX-FileCopyrightText: © 2025 Tenstorrent AI ULC
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_log1p.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

/**
 * Please refer to documentation for any_init.
 */
template <bool fast_and_approx = true>
ALWI void log1p_tile_init() {
    MATH((llk_math_eltwise_unary_sfpu_log1p_init<APPROX, fast_and_approx>()));
}

// clang-format off
/**
 * Performs element-wise computation of logarithm of (1+x) on each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
template <bool fast_and_approx = true>
ALWI void log1p_tile(uint32_t idst) {
    MATH((llk_math_eltwise_unary_sfpu_log1p<APPROX, fast_and_approx>(idst)));
}

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/logical_not_noti.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent AI ULC
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_logical_not_noti.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {
// clang-format off
/**
 * Performs element-wise computation of the logical not unary operation on each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | tile_index     | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
 // clang-format on
ALWI void logical_not_unary_tile(uint32_t idst) {
    MATH((llk_math_eltwise_unary_sfpu_logical_not_unary_op<APPROX, sfpi::vFloat, float>(idst)));
}

ALWI void logical_not_unary_tile_int32(uint32_t idst) {
    MATH((llk_math_eltwise_unary_sfpu_logical_not_unary_op<APPROX, sfpi::vInt, int16_t>(idst)));
}

ALWI void logical_not_unary_tile_uint32(uint32_t idst) {
    MATH((llk_math_eltwise_unary_sfpu_logical_not_unary_op<APPROX, sfpi::vUInt, uint16_t>(idst)));
}

ALWI void logical_not_unary_tile_uint16(uint32_t idst) {
    MATH((llk_math_eltwise_unary_sfpu_logical_not_unary_uint16<APPROX>(idst)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void logical_not_unary_tile_init() { MATH((llk_math_eltwise_unary_sfpu_logical_not_unary_init<APPROX>())); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/negative.h

```cpp
/*
 * SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_negative.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

ALWI void negative_tile_init() { MATH((llk_math_eltwise_unary_sfpu_negative_init<APPROX>())); }
// clang-format off
/**
 * Performs element-wise computation of the negative on each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | tile_index     | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
 // clang-format on
ALWI void negative_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_negative<APPROX>(idst))); }

ALWI void negative_tile_int32(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_negative_int<APPROX>(idst))); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/prelu.h

```cpp
// SPDX-FileCopyrightText: © 2024 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_prelu.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {
// clang-format off
/**
 * Performs element-wise prelu operation. The value to be prelued in the tile is provided as const param0. The DST
 * register buffer must be in acquired state via *acquire_dst* call. This call is blocking and is only available on the
 * compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | param0          | Constant value that is being multiplied if the input is lesser than 0      | uint32_t |                                                       | True     |
 */
 // clang-format on
ALWI void prelu_tile(uint32_t idst, uint32_t param0) {
    MATH((llk_math_eltwise_unary_sfpu_prelu<APPROX>(idst, param0)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void prelu_tile_init() { MATH((llk_math_eltwise_unary_sfpu_prelu_init<APPROX>())); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/rand.h

```cpp
// SPDX-FileCopyrightText: © 2024 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_rand.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {
// clang-format off
/**
 * Performs element-wise rand on each element of a of a tile in DST register at index tile_index.
 * That is each element is overwritten with a randomly generated float.
 * The DST register buffer must be in acquired state via *acquire_dst* call.
 * This call is blocking and is only available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required  |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|-----------|
 * | tile_index     | The index of the tile in DST register buffer to perform typecast operation | uint32_t | Must be less than the size of the DST register buffer | True      |
 * | from           | Random range lowerbound(inclusive)                                         | uint     | Any number                                            | True      |
 * | scale          | Random scale rand float in range [from, from + scale]                      | uint     | Must be greater than 0                                | True      |
 */
 // clang-format on
ALWI void rand_tile(uint32_t idst, uint32_t from, uint32_t scale) {
    MATH((llk_math_eltwise_unary_sfpu_rand<APPROX>(idst, from, scale)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void rand_tile_init(uint32_t seed) { MATH((llk_math_eltwise_unary_sfpu_rand_init<APPROX>(seed))); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/recip.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_recip.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

/**
 * Please refer to documentation for any_init.
 */
template <bool legacy_compat = true>
ALWI void recip_tile_init() {
    MATH((llk_math_eltwise_unary_sfpu_reciprocal_init<APPROX, legacy_compat>()));
}

// clang-format off
/**
 * Performs element-wise computation of the reciprocal on each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 * Only works for Float32, Float16_b, Bfp8_b data formats for full accuracy.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst           | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | vector_mode | Specifies the vector mode for computation (e.g., Row, Column). (default: VectorMode::RC) | int      | Subject to specific hardware/kernel limits          | False    |
 */
// clang-format on
template <bool legacy_compat = true>
ALWI void recip_tile(uint32_t idst, int vector_mode = (int)VectorMode::RC) {
    MATH((llk_math_eltwise_unary_sfpu_reciprocal<APPROX, DST_ACCUM_MODE, legacy_compat>(idst, vector_mode)));
}

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/relu.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_relu.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

// clang-format off
/**
 * Performs element-wise computation of relu max (relu(max(x, upper_limit))) on each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | tile_index     | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | upper_limit    | Upper limit of relu_min                                                    | uint32_t | Greater than 0                                        | True     |
 */
// clang-format on
ALWI void relu_max_tile(uint32_t idst, uint32_t param0) {
    MATH((llk_math_eltwise_unary_sfpu_relu_max<APPROX>(idst, param0)));
}

ALWI void relu_max_tile_int32(uint32_t idst, uint32_t param0) {
    MATH((llk_math_eltwise_unary_sfpu_relu_max_int32<APPROX>(idst, param0)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void relu_max_tile_init() { MATH((llk_math_eltwise_unary_sfpu_relu_max_init<APPROX>())); }

// clang-format off
/**
 * Performs element-wise computation of relu min (relu(min(x, lower_limit))) on each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | tile_index     | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | lower_limit    | Upper limit of relu_min                                                    | uint32_t | Greater than 0                                        | True     |
 */
// clang-format on
ALWI void relu_min_tile(uint32_t idst, uint32_t param0) {
    MATH((llk_math_eltwise_unary_sfpu_relu_min<APPROX>(idst, param0)));
}

ALWI void relu_min_tile_int32(uint32_t idst, uint32_t param0) {
    MATH((llk_math_eltwise_unary_sfpu_relu_min_int32<APPROX>(idst, param0)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void relu_min_tile_init() { MATH((llk_math_eltwise_unary_sfpu_relu_min_init<APPROX>())); }

// clang-format off
/**
 * Performs element-wise computation of relu(x) = (0 if x is negative else x) on each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | tile_index     | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
 // clang-format on
ALWI void relu_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_relu<APPROX>(idst))); }

ALWI void relu_tile_int32(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_relu_int32<APPROX>(idst))); }

/**
 * Please refer to documentation for any_init.
 */
ALWI void relu_tile_init() { MATH((llk_math_eltwise_unary_sfpu_relu_init<APPROX>())); }

// clang-format off
/**
 * Performs element-wise computation of leaky relu (relu(x) + slope*-relu(-x)) on each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | tile_index     | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | slope          | slope used in leaky relu - will reinterpret unsigned int to float          | uint32_t | Greater than 0                                        | True     |
 */
// clang-format on
ALWI void leaky_relu_tile(uint32_t idst, uint32_t slope) {
    MATH((llk_math_eltwise_unary_sfpu_lrelu<APPROX>(idst, slope)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void leaky_relu_tile_init() { MATH((llk_math_eltwise_unary_sfpu_lrelu_init<APPROX>())); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/remainder.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_remainder.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

// clang-format off
/**
 * Performs element-wise remainder computation on input x by y , where x is each element of a tile
 * in DST register at index tile_index. The input can be of float data type. The value is provided as const param0 The
 * DST register buffer must be in acquired state via *acquire_dst* call. This call is blocking and is only available on
 * the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                 | Type     | Valid Range                                           | Required |
 * |----------------|-----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst           | The index of the tile in DST register buffer to perform remainder operation | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | param0         | Denominator value to perform remainder operation                            | uint32_t |                                                       | True     |
 * | param1         | Reciprocal of param0, calculated on-host                                    | uint32_t |                                                       | False    |
 */
// clang-format on
ALWI void remainder_tile(uint32_t idst, uint32_t param0, uint32_t param1) {
    MATH((llk_math_eltwise_unary_sfpu_remainder<APPROX>(idst, param0, param1)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void remainder_tile_init(uint32_t param0, uint32_t param1) {
    MATH((llk_math_eltwise_unary_sfpu_remainder_init<APPROX>(param0, param1)));
}

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/reverseops.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_reverseops.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

// rpow: implemented as a composite operator
// rpow(a,k) = k**(a)

// RDIV : rdiv(x,y) = y/x
// implemented as tied multiply operator

// RSUB : rsub(x,y) = y-x

// clang-format off
/**
 * Performs element-wise computation of rsub ( rsub(x,y) = y -x) on each element of a tile and y is a constant param
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst           | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | param0         | Constant value that is being subtracted from                               | uint32_t |                                                       | True     |
 */
 // clang-format on
ALWI void rsub_tile(uint32_t idst, uint32_t param0) { MATH((llk_math_eltwise_unary_sfpu_rsub<APPROX>(idst, param0))); }

/**
 * Please refer to documentation for any_init.
 */
ALWI void rsub_tile_init() { MATH((llk_math_eltwise_unary_sfpu_rsub_init<APPROX>())); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/right_shift.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_right_shift.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

// clang-format off
/**
 * Performs element-wise right_shift computation on input x , where x is each element of a tile
 * in DST register at index tile_index. The value is provided as const param0 The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | param0          | The value the output is if the input is greater than 0                     | uint32_t |                                                       | True     |
 */
 // clang-format on
ALWI void right_shift_tile(uint32_t idst, uint32_t param0) {
    MATH((llk_math_eltwise_unary_sfpu_right_shift<APPROX>(idst, param0)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void right_shift_tile_init() { MATH((llk_math_eltwise_unary_sfpu_right_shift_init<APPROX>())); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/rounding.h

```cpp
// SPDX-FileCopyrightText: © 2025 Tenstorrent AI ULC
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_rounding_ops.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

/**
 * Please refer to documentation for any_init.
 */
ALWI void rounding_op_tile_init() { MATH((llk_math_eltwise_unary_sfpu_rounding_op_init<APPROX>())); }

// clang-format off
/**
 * Performs element-wise ceil computation on input x , where x is each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform ceil operation     | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void ceil_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_ceil<APPROX>(idst))); }

// clang-format off
/**
 * Performs element-wise ceil computation on input x , where x is each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform ceil operation     | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void ceil_tile_float32(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_ceil_float32<APPROX>(idst))); }

// clang-format off
/**
 * Performs element-wise floor computation on input x , where x is each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform floor operation    | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void floor_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_floor<APPROX>(idst))); }

// clang-format off
/**
 * Performs element-wise floor computation on input x , where x is each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform floor operation    | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void floor_tile_float32(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_floor_float32<APPROX>(idst))); }

// clang-format off
/**
 * Performs element-wise trunc computation on input x , where x is each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform trunc operation    | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void trunc_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_trunc<APPROX>(idst))); }

// clang-format off
/**
 * Performs element-wise trunc computation on input x , where x is each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform trunc operation    | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void trunc_tile_float32(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_trunc_float32<APPROX>(idst))); }

// clang-format off
/**
 * Performs element-wise computation of the round operation on each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | decimals        | The number of decimal places to round to.                                  | uint32_t |                                                       | True     |
 */
// clang-format on
ALWI void round_tile(uint32_t idst, int32_t decimals) {
    MATH((llk_math_eltwise_unary_sfpu_round<APPROX>(idst, decimals)));
}

// clang-format off
/**
 * Performs element-wise frac computation on input x , where x is each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform frac operation     | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void frac_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_frac<APPROX>(idst))); }

// clang-format off
/**
 * Performs element-wise frac computation on input x , where x is each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform frac operation     | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void frac_tile_float32(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_frac_float32<APPROX>(idst))); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/rsqrt.h

```cpp
// SPDX-FileCopyrightText: © 2025 Jason Davies <jason@jasondavies.com>
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_rsqrt.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

/**
 * Please refer to documentation for any_init.
 */
template <bool legacy_compat = false>
ALWI void rsqrt_tile_init() {
    MATH((llk_math_eltwise_unary_sfpu_rsqrt_init<APPROX, legacy_compat>()));
}

// clang-format off
/**
 * Performs element-wise computation of reciprocal sqrt on each element of a
 * tile in DST register at index idst. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst           | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
template <bool legacy_compat = false>
ALWI void rsqrt_tile(uint32_t idst) {
    MATH((llk_math_eltwise_unary_sfpu_rsqrt<APPROX, DST_ACCUM_MODE, legacy_compat>(idst)));
}

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/sfpu_int_sum.h

```cpp
// SPDX-FileCopyrightText: © 2024 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_int_sum.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

ALWI void sfpu_sum_int_init() { MATH((llk_math_eltwise_unary_sfpu_sum_int_init<APPROX>())); }

ALWI void sfpu_sum_int_col(uint32_t idst) {
    MATH((llk_math_eltwise_unary_sfpu_sum_int<APPROX>(idst, SumIntDim::SUM_COL)));
}

ALWI void sfpu_sum_int_row(uint32_t idst) {
    MATH((llk_math_eltwise_unary_sfpu_sum_int<APPROX>(idst, SumIntDim::SUM_ROW)));
}

ALWI void sfpu_add_int(uint32_t idst, uint32_t dst_offset = 2, int32_t iterations = 8) {
    MATH((llk_math_eltwise_unary_sfpu_add_int<APPROX>(idst, dst_offset, iterations)));
}

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/sfpu_split_includes.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent AI ULC
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#if SFPU_OP_ISINF_ISNAN_INCLUDE
#include "compute_kernel_api/eltwise_unary/isinf_isnan.h"
#endif

#if SFPU_OP_ERF_ERFC_INCLUDE
#include "compute_kernel_api/eltwise_unary/erf_erfc.h"
#endif

#if SFPU_OP_LOGICAL_NOT_NOTI_INCLUDE
#include "compute_kernel_api/eltwise_unary/logical_not_noti.h"
#endif

#if SFPU_OP_EXP_INCLUDE
#include "compute_kernel_api/eltwise_unary/exp.h"
#endif

#if SFPU_OP_GELU_INCLUDE
#include "compute_kernel_api/eltwise_unary/gelu.h"
#endif

#if SFPU_OP_SQRT_INCLUDE
#include "compute_kernel_api/eltwise_unary/sqrt.h"
#endif

#if SFPU_OP_RSQRT_INCLUDE
#include "compute_kernel_api/eltwise_unary/rsqrt.h"
#endif

#if SFPU_OP_RECIP_INCLUDE
#include "compute_kernel_api/eltwise_unary/recip.h"
#endif

#if SFPU_OP_RELU_FAMILY_INCLUDE
#include "compute_kernel_api/eltwise_unary/relu.h"
#endif

#if SFPU_OP_ELU_INCLUDE
#include "compute_kernel_api/eltwise_unary/elu.h"
#endif

#if SFPU_OP_I0_INCLUDE
#include "compute_kernel_api/eltwise_unary/i0.h"
#endif

#if SFPU_OP_I1_INCLUDE
#include "compute_kernel_api/eltwise_unary/i1.h"
#endif

#if SFPU_OP_ERFINV_INCLUDE
#include "compute_kernel_api/eltwise_unary/erfinv.h"
#endif

#if SFPU_OP_NEG_INCLUDE
#include "compute_kernel_api/eltwise_unary/negative.h"
#endif

#if SFPU_OP_TRIG_FAMILY_INCLUDE
#include "compute_kernel_api/eltwise_unary/trigonometry.h"
#endif

#if SFPU_OP_REVERSE_FAMILY_INCLUDE
#include "compute_kernel_api/eltwise_unary/reverseops.h"
#endif

#if SFPU_OP_IDENTITY_INCLUDE
#include "compute_kernel_api/eltwise_unary/identity.h"
#endif

#if SFPU_OP_TYPECAST_INCLUDE
#include "compute_kernel_api/eltwise_unary/typecast.h"
#endif

#if SFPU_OP_BITWISE_XOR_INCLUDE
#include "compute_kernel_api/eltwise_unary/bitwise_xor.h"
#endif

#if SFPU_OP_BITWISE_NOT_INCLUDE
#include "compute_kernel_api/eltwise_unary/bitwise_not.h"
#endif

#if SFPU_OP_RIGHT_SHIFT_INCLUDE
#include "compute_kernel_api/eltwise_unary/right_shift.h"
#endif

#if SFPU_OP_BITWISE_AND_INCLUDE
#include "compute_kernel_api/eltwise_unary/bitwise_and.h"
#endif

#if SFPU_OP_BITWISE_OR_INCLUDE
#include "compute_kernel_api/eltwise_unary/bitwise_or.h"
#endif

#if SFPU_OP_ROUND_FAMILY_INCLUDE
#include "compute_kernel_api/eltwise_unary/rounding.h"
#endif

#if SFPU_OP_LEFT_SHIFT_INCLUDE
#include "compute_kernel_api/eltwise_unary/left_shift.h"
#endif

#if SFPU_OP_REMAINDER_INCLUDE
#include "compute_kernel_api/eltwise_unary/remainder.h"
#endif

#if SFPU_OP_FMOD_INCLUDE
#include "compute_kernel_api/eltwise_unary/fmod.h"
#endif

#if SFPU_OP_BINOP_WITH_SCALAR_INCLUDE
#include "compute_kernel_api/eltwise_unary/binop_with_scalar.h"
#endif

#if SFPU_OP_SOFTPLUS_INCLUDE
#include "compute_kernel_api/eltwise_unary/softplus.h"
#endif

#if SFPU_OP_PRELU_INCLUDE
#include "compute_kernel_api/eltwise_unary/prelu.h"
#endif

#if SFPU_OP_DROPOUT_INCLUDE
#include "compute_kernel_api/eltwise_unary/dropout.h"
#endif

#if SFPU_OP_FILL_INCLUDE
#include "compute_kernel_api/eltwise_unary/fill.h"
#endif

#if SFPU_OP_LOG1P_INCLUDE
#include "compute_kernel_api/eltwise_unary/log1p.h"
#endif

#if SFPU_OP_UNARY_COMP_INCLUDE
#include "compute_kernel_api/eltwise_unary/comp.h"
#endif

#if SFPU_OP_ACTIVATIONS_INCLUDE
#include "compute_kernel_api/eltwise_unary/activations.h"
#endif

#if SFPU_OP_THRESHOLD_INCLUDE
#include "compute_kernel_api/eltwise_unary/threshold.h"
#endif

#if SFPU_OP_WHERE_INCLUDE
#include "compute_kernel_api/eltwise_unary/where.h"
#endif

#if SFPU_OP_CLAMP_INCLUDE
#include "compute_kernel_api/eltwise_unary/clamp.h"
#endif

#if SFPU_OP_HARDTANH_INCLUDE
#include "compute_kernel_api/eltwise_unary/hardtanh.h"
#endif

#if SFPU_OP_COMPUTE_KERNEL_API_INCLUDE
#include "compute_kernel_api.h"
#endif
```

## tt_metal/include/compute_kernel_api/eltwise_unary/softplus.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_softplus.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

// clang-format off
/**
 * Performs element-wise computation of softplus (`1/beta * log(1 + exp(beta * x))`) on each element
 * of a tile in DST register at index tile_index. Any input value greater than the provided threshold
 * with return itself. The DST register buffer must be in acquired state via *acquire_dst* call. This
 * call is blocking and is only available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | tile_index      | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | beta            | Beta used in softplus calculation                                          | uint32_t | Greater than 0                                        | True     |
 * | beta_reciprocal | Reciprocal of beta (1/beta) used in softplus calculation                   | uint32_t | Greater than 0                                        | True     |
 * | threshold       | Threshold used in softplus calculation                                     | uint32_t | Greater than 0                                        | True     |
 */
 // clang-format on
ALWI void softplus_tile(uint32_t idst, uint32_t beta, uint32_t beta_reciprocal, uint32_t threshold) {
    MATH((llk_math_eltwise_unary_sfpu_softplus<APPROX>(idst, beta, beta_reciprocal, threshold)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void softplus_tile_init() { MATH((llk_math_eltwise_unary_sfpu_softplus_init<APPROX>())); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/sqrt.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_sqrt.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

/**
 * Please refer to documentation for any_init.
 */
template <bool legacy_compat = true>
ALWI void sqrt_tile_init() {
    MATH((llk_math_eltwise_unary_sfpu_sqrt_init<APPROX, legacy_compat>()));
}

// clang-format off
/**
 * Performs element-wise computation of the square root on each element of a
 * tile in DST register at index idst. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst           | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
template <bool legacy_compat = true>
ALWI void sqrt_tile(uint32_t idst) {
    MATH((llk_math_eltwise_unary_sfpu_sqrt<APPROX, DST_ACCUM_MODE, legacy_compat>(idst)));
}

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/threshold.h

```cpp
// SPDX-FileCopyrightText: © 2025 Tenstorrent AI ULC
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_threshold.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

// clang-format off
/**
* Performs element-wise threshold operation. The DST
* register buffer must be in acquired state via *acquire_dst* call. This call is blocking and is only available on the
* compute engine.
*
* Return value: None
*
* | Argument        | Description                                                                         | Type     | Valid Range                                           | Required |
* |-----------------|-------------------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
* | idst            | The index of the tile in DST register buffer to perform the computation on          | uint32_t | Must be less than the size of the DST register buffer | True     |
* | param0          | The threshold value for the threshold function                                      | uint32_t |                                                       | True     |
* | param1          | The value to replace the input with if it is less than or equal to the threshold    | uint32_t |                                                       | True     |
*/
// clang-format on
ALWI void threshold_tile(uint32_t idst, uint32_t param0, uint32_t param1) {
    MATH((llk_math_eltwise_unary_sfpu_threshold<APPROX>(idst, param0, param1)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void threshold_tile_init() { MATH((llk_math_eltwise_unary_sfpu_threshold_init<APPROX>())); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/trigonometry.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_trigonometry.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

/**
 * Please refer to documentation for any_init.
 */
ALWI void sin_tile_init() { MATH((llk_math_eltwise_unary_sfpu_sine_init<APPROX>())); }

// clang-format off
/**
 * Performs element-wise computation of the trigonometric sine operation on each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | tile_index     | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void sin_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_sine_op<APPROX>(idst))); }

/**
 * Please refer to documentation for any_init.
 */
ALWI void cos_tile_init() { MATH((llk_math_eltwise_unary_sfpu_cosine_init<APPROX>())); }

// clang-format off
/**
 * Performs element-wise computation of the trigonometric cosine operation on each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | tile_index     | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void cos_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_cosine_op<APPROX>(idst))); }

/**
 * Please refer to documentation for any_init.
 */
ALWI void acosh_tile_init() { MATH((llk_math_eltwise_unary_sfpu_acosh_init<APPROX>())); }

// clang-format off
/**
 * Performs element-wise computation of the inverse hyperbolic cosine operation on each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | tile_index     | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void acosh_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_acosh<APPROX>(idst))); }

/**
 * Please refer to documentation for any_init.
 */
ALWI void tan_tile_init() { MATH((llk_math_eltwise_unary_sfpu_tan_init<APPROX>())); }

// clang-format off
/**
 * Performs element-wise computation of the trigonometric tan operation on each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | tile_index     | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void tan_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_tan_op<APPROX>(idst))); }

/**
 * Please refer to documentation for any_init.
 */
ALWI void asinh_tile_init() { MATH((llk_math_eltwise_unary_sfpu_asinh_init<APPROX>())); }

// clang-format off
/**
 * Performs element-wise computation of the inverse hyperbolic sine operation on each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | tile_index     | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void asinh_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_asinh<APPROX>(idst))); }

/**
 * Please refer to documentation for any_init.
 */
ALWI void atanh_tile_init() { MATH((llk_math_eltwise_unary_sfpu_atanh_init<APPROX>())); }

// clang-format off
 /**
  * Performs element-wise computation of the inverse hyperbolic tangent operation on each element of a tile
  * in DST register at index tile_index. The DST register buffer must be in
  * acquired state via *acquire_dst* call. This call is blocking and is only
  * available on the compute engine.
  *
  * Return value: None
  *
  * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
  * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
  * | tile_index     | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
  */
// clang-format on
ALWI void atanh_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_atanh<APPROX, DST_ACCUM_MODE>(idst))); }

// clang-format off
/**
 * Performs element-wise computation of arcsine on each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void asin_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_asin<true>(idst))); }

/**
 * Please refer to documentation for any_init.
 */
ALWI void asin_tile_init() { MATH((llk_math_eltwise_unary_sfpu_asin_init<true>())); }

// clang-format off
/**
 * Performs element-wise computation of arctan on each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void atan_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_atan<true>(idst))); }

/**
 * Please refer to documentation for any_init.
 */
ALWI void atan_tile_init() { MATH((llk_math_eltwise_unary_sfpu_atan_init<true>())); }

// clang-format off
/**
 * Performs element-wise computation of arcossine on each element of a tile
 * in DST register at index tile_index. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void acos_tile(uint32_t idst) { MATH((llk_math_eltwise_unary_sfpu_acos<true>(idst))); }

/**
 * Please refer to documentation for any_init.
 */
ALWI void acos_tile_init() { MATH((llk_math_eltwise_unary_sfpu_acos_init<true>())); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/typecast.h

```cpp
// SPDX-FileCopyrightText: © 2024 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_typecast.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

// clang-format off
/**
 * Performs an elementwise typecast operation on the input.
 * Supports following typecasts:
 *  Float16_b <-> Float32
 *  Float16_b <-> Int32
 *  Float16_b <-> UInt16
 *  Float16_b <-> UInt32
 *  Float32 <-> Int32
 *  Float32 <-> UInt16
 *  Float32 <-> UInt32
 *  Bfp8_b <-> Int32
 *  Bfp8_b <-> UInt16
 *  Bfp8_b <-> UInt32
 *  Bfp8_b <-> Float16_b
 *  Bfp8_b <-> Float32
 *  Bfp4_b <-> Int32
 *  Bfp4_b <-> UInt16
 *  Bfp4_b <-> UInt32
 *  Bfp4_b <-> Bfp8_b
 *  Bfp4_b <-> Float16_b
 *  Bfp4_b <-> Float32
 *  UInt16 <-> UInt32
 *  UInt16 <-> Int32
 *
 * For input/output to be UInt32, Int32, or Float32, Dest must be in 32 bit mode.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type     | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | tile_index     | The index of the tile in DST register buffer to perform typecast operation | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | IN_DTYPE       | Input data format                                                          | uint32_t | Must be valid tt::DataFormat                          | True     |
 * | OUT_DTYPE      | Desired output data format                                                 | uint32_t | Must be valid tt::DataFormat                          | True     |
 */
// clang-format on
template <uint32_t IN_DTYPE, uint32_t OUT_DTYPE>
ALWI void typecast_tile(uint32_t idst) {
    MATH((llk_math_eltwise_unary_sfpu_typecast<APPROX, IN_DTYPE, OUT_DTYPE>(idst)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void typecast_tile_init() { MATH((llk_math_eltwise_unary_sfpu_typecast_init<APPROX>())); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/eltwise_unary/where.h

```cpp
// SPDX-FileCopyrightText: © 2025 Tenstorrent AI ULC
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_ternary_sfpu_where.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

// clang-format off
/**
 * Performs an elementwise where operation with the three inputs: y = where(x0,x1,x2)
 * Output overwrites odst in DST.
 *
 * The DST register buffer must be in acquired state via *acquire_dst* call. This call is blocking and is only available
 * on the compute engine.
 *
 * | Argument              | Description                                                              | Type     | Valid Range                                           | Required |
 * |-----------------------|--------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst0                 | The index of the tile in DST register buffer to use as condition operand | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | idst1                 | The index of the tile in DST register buffer to use as first operand     | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | idst2                 | The index of the tile in DST register buffer to use as second operand    | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | odst                  | The index of the tile in DST register buffer to use as output            | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void where_tile(uint32_t idst0, uint32_t idst1, uint32_t idst2, uint32_t odst) {
    MATH((llk_math_eltwise_ternary_sfpu_where<APPROX>(idst0, idst1, idst2, odst)));
}

ALWI void where_fp32_tile(uint32_t idst0, uint32_t idst1, uint32_t idst2, uint32_t odst) {
    MATH((llk_math_eltwise_ternary_sfpu_where_fp32<APPROX>(idst0, idst1, idst2, odst)));
}

ALWI void where_int32_tile(uint32_t idst0, uint32_t idst1, uint32_t idst2, uint32_t odst) {
    MATH((llk_math_eltwise_ternary_sfpu_where_int32<APPROX>(idst0, idst1, idst2, odst)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void where_tile_init() { MATH((llk_math_eltwise_ternary_sfpu_where_init<APPROX>())); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/gcd.h

```cpp
// SPDX-FileCopyrightText: © 2025 Jason Davies <jason@jasondavies.com>
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_binary_sfpu_gcd.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

// clang-format off
/**
 * Performs an elementwise GCD operation on two inputs: y = gcd(x0, x1).
 * Both inputs must be int32.
 * Output overwrites odst in DST.
 *
 * The DST register buffer must be in acquired state via *acquire_dst* call. This call is blocking and is only available
 * on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                           | Type     | Valid Range                                           | Required |
 * |----------------|-----------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst0          | The index of the tile in DST register buffer to use as first operand  | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | idst1          | The index of the tile in DST register buffer to use as second operand | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | odst           | The index of the tile in DST register buffer to use as output         | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void gcd_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_gcd<APPROX>(idst0, idst1, odst)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void gcd_tile_init() { MATH((llk_math_eltwise_binary_sfpu_gcd_init<APPROX>())); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/layernorm.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api.h"
#include "compute_kernel_api/eltwise_unary/rsqrt.h"
```

## tt_metal/include/compute_kernel_api/lcm.h

```cpp
// SPDX-FileCopyrightText: © 2025 Jason Davies <jason@jasondavies.com>
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_binary_sfpu_lcm.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

// clang-format off
/**
 * Performs an elementwise LCM operation on two inputs: y = lcm(x0, x1).
 * Both inputs must be int32 with values constrained to |value| ≤ 2^15-1 (32,767).
 * Output overwrites odst in DST.
 *
 * The DST register buffer must be in acquired state via *acquire_dst* call. This call is blocking and is only available
 * on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                           | Type     | Valid Range                                           | Required |
 * |----------------|-----------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst0          | The index of the tile in DST register buffer to use as first operand  | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | idst1          | The index of the tile in DST register buffer to use as second operand | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | odst           | The index of the tile in DST register buffer to use as output         | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void lcm_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_lcm<APPROX>(idst0, idst1, odst)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void lcm_tile_init() { MATH((llk_math_eltwise_binary_sfpu_lcm_init<APPROX>())); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/mask.h

```cpp
/*
 * SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_mask.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

ALWI void mask_tile_init() {
    MATH((llk_math_eltwise_unary_sfpu_mask_init<true>()));  // TODO(AP): move out init
}

// clang-format off
/**
 * Performs element-wise computation of mask on each element of a tile
 * in data and mask DST register. *mask_tile* will mask each element with 0,
 * *mask_posinf_tile* will mask each element with *float(inf)*.
 * The DST register buffer must be in acquired state via *acquire_dst* call.
 * This call is blocking and is only available on the compute engine.
 *
 *
 * TODO: fix idst2_mask.
 * currently idst2_mask is not used and (idst_data + 1) is used for mask.
 * because don't know how to use 2 dst register with sfpu.
 *
 * Return value: None
 *
 * | Argument       | Description                                                                | Type       | Valid Range                                           | Required |
 * |----------------|----------------------------------------------------------------------------|------------|-------------------------------------------------------|----------|
 * | dst_data_index | The index of the tile in DST REG for the data and result                   | uint32_t   | Must be less than the acquired size of DST REG        | True     |
 * | dst_mask_index | The index of the tile in DST REG for the mask                              | uint32_t   | Must be less than the acquired size of DST REG        | True     |
 * | data_format    | The format of the data and mask (supports Float16, Float16_b, and Int32)   | DataFormat | Must be a valid data format                           | False    |
 */
 // clang-format on
ALWI void mask_tile(uint32_t idst_data, uint32_t idst2_mask, DataFormat data_format = DataFormat::Float16_b) {
    MATH((llk_math_eltwise_unary_sfpu_mask<true>(idst_data, data_format)));
}

ALWI void mask_posinf_tile(uint32_t idst_data, uint32_t idst2_mask) {
    MATH((llk_math_eltwise_unary_sfpu_mask_posinf<true>(idst_data)));
}

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/matmul.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common.h"
#ifdef TRISC_MATH
#include "llk_math_matmul_api.h"
#endif
#ifdef TRISC_UNPACK
#include "llk_unpack_AB_matmul_api.h"
#endif
#ifndef MM_THROTTLE
#define MM_THROTTLE 0
#endif
namespace ckernel {

// clang-format off
/**
 * Initialization for matmul_tiles operation. Must be called before matmul_tiles.
 *
 * Return value: None
 *
 * | Argument       | Description                                                   | Type     | Valid Range                                        | Required |
 * |----------------|---------------------------------------------------------------|----------|----------------------------------------------------|----------|
 * | in0_cb_id      | The identifier of the first input circular buffer (CB)        | uint32_t | 0 to 31                                            | False    |
 * | in1_cb_id      | The identifier of the second input circular buffer (CB)       | uint32_t | 0 to 31                                            | False    |
 * | out_cb_id      | The identifier of the output circular buffer (CB)             | uint32_t | 0 to 31                                            | False    |
 * | transpose      | The transpose flag for performing transpose operation on B    | uint32_t | Any positive value will indicate tranpose is set   | False    |
 */
// clang-format on
ALWI void mm_init(uint32_t in0_cb_id, uint32_t in1_cb_id, uint32_t out_cb_id, const uint32_t transpose = 0) {
    UNPACK((llk_unpack_AB_matmul_hw_configure_disaggregated<DST_ACCUM_MODE>(in0_cb_id, in1_cb_id)));
    UNPACK((llk_unpack_AB_matmul_init(in0_cb_id, in1_cb_id, transpose)));

    MATH((llk_math_matmul_init<MATH_FIDELITY, MM_THROTTLE>(in0_cb_id, in1_cb_id, transpose)));
    MATH((llk_math_pack_sync_init<DST_ACCUM_MODE>()));
    MATH((llk_math_hw_configure_disaggregated(in0_cb_id, in1_cb_id)));

    PACK((llk_pack_hw_configure_disaggregated<DST_ACCUM_MODE, false>(out_cb_id)));
    PACK((llk_pack_init(out_cb_id)));
    PACK((llk_pack_dest_init<DST_ACCUM_MODE, false>()));
}

// clang-format off
/**
 * Performs tile-sized matrix multiplication *C=A\*B* between the tiles in two
 * specified input CBs and writes the result to DST. The DST register buffer
 * must be in acquired state via *acquire_dst* call. This call is blocking and
 * is only available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                             | Type     | Valid Range                                    | Required |
 * |----------------|-------------------------------------------------------------------------|----------|------------------------------------------------|----------|
 * | in0_cb_id      | The identifier of the first input circular buffer (CB)                  | uint32_t | 0 to 31                                        | True     |
 * | in1_cb_id      | The identifier of the second input circular buffer (CB)                 | uint32_t | 0 to 31                                        | True     |
 * | in0_tile_index | The index of the tile A from the first input CB                         | uint32_t | Must be less than the size of the CB           | True     |
 * | in1_tile_index | The index of the tile B from the second input CB                        | uint32_t | Must be less than the size of the CB           | True     |
 * | dst_tile_index | The index of the tile in DST REG to which the result C will be written. | uint32_t | Must be less than the acquired size of DST REG | True     |
 */
// clang-format on
ALWI void matmul_tiles(
    uint32_t in0_cb_id,
    uint32_t in1_cb_id,
    uint32_t in0_tile_index,
    uint32_t in1_tile_index,
    uint32_t idst,
    const uint32_t transpose) {
    UNPACK((llk_unpack_AB_matmul(in0_cb_id, in1_cb_id, in0_tile_index, in1_tile_index)));
    MATH((llk_math_matmul<MATH_FIDELITY, MM_THROTTLE>(idst, transpose)));
}

// clang-format off
/**
 * Performs tile-sized matrix multiplication *C=A\*B* between the tiles
 * located in SRCA and SRCB and writes the result to DST. The DST register buffer
 * must be in acquired state via *acquire_dst* call. This call is blocking and
 * is only available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                             | Type     | Valid Range                                    | Required |
 * |----------------|-------------------------------------------------------------------------|----------|------------------------------------------------|----------|
 * | idst           | The index of the tile in DST REG to which the result C will be written. | uint32_t | Must be less than the acquired size of DST REG | True     |
 */
 // clang-format on
template <uint32_t num_faces = 4>
ALWI void matmul_tiles_math(uint32_t idst) {
    MATH((llk_math_matmul<MATH_FIDELITY, MM_THROTTLE, num_faces>(idst)));
}

// clang-format off
/**
 * A short version of matmul_tiles initialization.
 * Configure the unpacker and math engine to matmul mode.
 *
 * Return value: None
 *
 * | Argument       | Description                                                   | Type     | Valid Range                                       | Required |
 * |----------------|---------------------------------------------------------------|----------|---------------------------------------------------|----------|
 * | in0_cb_id      | The identifier of the first input circular buffer (CB)        | uint32_t | 0 to 31                                           | False    |
 * | in1_cb_id      | The identifier of the second input circular buffer (CB)       | uint32_t | 0 to 31                                           | False    |
 * | transpose      | The transpose flag for performing transpose operation on B    | uint32_t | Any positive value will indicate tranpose is set  | False    |
 */
// clang-format on
ALWI void mm_init_short(uint32_t in0_cb_id, uint32_t in1_cb_id, const uint32_t transpose = 0) {
    MATH((llk_math_matmul_init<MATH_FIDELITY, MM_THROTTLE>(in0_cb_id, in1_cb_id, transpose)));
    UNPACK((llk_unpack_AB_matmul_init(in0_cb_id, in1_cb_id, transpose)));
}

// clang-format off
/**
 * A short version of matmul_tiles initialization.
 * It is used to reconfigure srcA of the compute engine back to matmul mode.
 *
 * Return value: None
 *
 * | Argument       | Description                                                   | Type     | Valid Range                                       | Required |
 * |----------------|---------------------------------------------------------------|----------|---------------------------------------------------|----------|
 * | in0_cb_id      | The identifier of the first input circular buffer (CB)        | uint32_t | 0 to 31                                           | False    |
 * | in1_cb_id      | The identifier of the second input circular buffer (CB)       | uint32_t | 0 to 31                                           | False    |
 * | c_in_old_srca  | The identifier of the old input to src A circular buffer (CB) | uint32_t | 0 to 31                                           | False    |
 * | transpose      | The transpose flag for performing transpose operation on B    | uint32_t | Any positive value will indicate tranpose is set  | False    |
 */
 // clang-format on
ALWI void mm_init_short_with_dt(
    uint32_t in0_cb_id, uint32_t in1_cb_id, uint32_t c_in_old_srca, const uint32_t transpose = 0) {
    UNPACK((llk_unpack_reconfig_data_format_srca<DST_ACCUM_MODE>(c_in_old_srca, in1_cb_id)));
    MATH((llk_math_reconfig_data_format_srca<DST_ACCUM_MODE>(c_in_old_srca, in1_cb_id)));
    mm_init_short(in0_cb_id, in1_cb_id, transpose);
}

// clang-format off
/**
 * Initialization for matmul_block operation. Must be called before matmul_block.
 *
 * Return value: None
 *
 * | Argument       | Description                                                   | Type     | Valid Range                                         | Required |
 * |----------------|---------------------------------------------------------------|----------|-----------------------------------------------------|----------|
 * | in0_cb_id      | The identifier of the first input circular buffer (CB)        | uint32_t | 0 to 31                                             | False    |
 * | in1_cb_id      | The identifier of the second input circular buffer (CB)       | uint32_t | 0 to 31                                             | False    |
 * | out_cb_id      | The identifier of the output circular buffer (CB)             | uint32_t | 0 to 31                                             | False    |
 * | ct_dim         | The number of columns of the output matrix in tiles           | uint32_t | 1 to 8 in half-sync mode, 1 to 16 in full-sync mode | False    |
 * | rt_dim         | The number of rows of the output matrix in tiles              | uint32_t | 1 to 8 in half-sync mode, 1 to 16 in full-sync mode | False    |
 * | kt_dim         | The inner dim of the input matrices in tiles                  | uint32_t | 1 to 2^32-1                                         | False    |
 */
// clang-format on
ALWI void mm_block_init(
    uint32_t in0_cb_id,
    uint32_t in1_cb_id,
    uint32_t out_cb_id,
    const uint32_t transpose = 0,
    uint32_t ct_dim = 1,
    uint32_t rt_dim = 1,
    uint32_t kt_dim = 1) {
    UNPACK((llk_unpack_AB_matmul_hw_configure_disaggregated<DST_ACCUM_MODE>(in0_cb_id, in1_cb_id)));
    UNPACK((llk_unpack_AB_matmul_init(in0_cb_id, in1_cb_id, transpose, ct_dim, rt_dim, kt_dim)));

    MATH((llk_math_matmul_init<MATH_FIDELITY, MM_THROTTLE>(in0_cb_id, in1_cb_id, transpose, ct_dim, rt_dim, kt_dim)));
    MATH((llk_math_pack_sync_init<DST_ACCUM_MODE>()));
    MATH((llk_math_hw_configure_disaggregated(in0_cb_id, in1_cb_id)));

    PACK((llk_pack_hw_configure_disaggregated<DST_ACCUM_MODE, false>(out_cb_id)));
    PACK((llk_pack_init<false, false>(out_cb_id)));
    PACK((llk_pack_dest_init<DST_ACCUM_MODE, false>()));
}

// clang-format off
/**
 * Performs block-sized matrix multiplication *C=A\*B* between the blocks in two
 * different input CBs and writes the result to DST. The DST register buffer
 * must be in acquired state via *acquire_dst* call. This call is blocking and
 * is only available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                                             | Type     | Valid Range                                    | Required |
 * |----------------|-------------------------------------------------------------------------|----------|------------------------------------------------|----------|
 * | in0_cb_id      | The identifier of the first input circular buffer (CB)                  | uint32_t | 0 to 31                                        | True     |
 * | in1_cb_id      | The identifier of the second input circular buffer (CB)                 | uint32_t | 0 to 31                                        | True     |
 * | in0_tile_index | The index of the tile in block A from the first input CB                | uint32_t | Must be less than the size of the CB           | True     |
 * | in1_tile_index | The index of the tile in block B from the second input CB               | uint32_t | Must be less than the size of the CB           | True     |
 * | idst           | The index of the tile in DST REG to which the result C will be written. | uint32_t | Must be less than the acquired size of DST REG | True     |
 * | transpose      | The transpose flag for performing transpose operation on tiles in B.    | bool     | Must be true or false                          | True     |
 * | ct_dim         | The coloumn dimension for the output block.                             | uint32_t | Must be equal to block B column dimension      | True     |
 * | rt_dim         | The row dimension for the output block.                                 | uint32_t | Must be equal to block A row dimension         | True     |
 * | kt_dim         | The inner dimension.                                                    | uint32_t | Must be equal to block A column dimension      | True     |
 */
// clang-format on
ALWI void matmul_block(
    uint32_t in0_cb_id,
    uint32_t in1_cb_id,
    uint32_t in0_tile_index,
    uint32_t in1_tile_index,
    uint32_t idst,
    const uint32_t transpose,
    uint32_t ct_dim,
    uint32_t rt_dim,
    uint32_t kt_dim) {
    UNPACK((llk_unpack_AB_matmul(in0_cb_id, in1_cb_id, in0_tile_index, in1_tile_index, ct_dim, rt_dim, kt_dim)));
    MATH((llk_math_matmul<MATH_FIDELITY, MM_THROTTLE>(idst, transpose, ct_dim, rt_dim, kt_dim)));
}

// clang-format off
/**
 * A short version of matmul_block initialization.
 * Configure the unpacker and math engine to matmul mode.
 *
 * Return value: None
 *
 * | Argument       | Description                                                   | Type     | Valid Range                                         | Required |
 * |----------------|---------------------------------------------------------------|----------|-----------------------------------------------------|----------|
 * | in0_cb_id      | The identifier of the first input circular buffer (CB)        | uint32_t | 0 to 31                                             | False    |
 * | in1_cb_id      | The identifier of the second input circular buffer (CB)       | uint32_t | 0 to 31                                             | False    |
 * | transpose      | The transpose flag for performing transpose operation on B    | uint32_t | Any positive value will indicate tranpose is set    | False    |
 * | ct_dim         | The coloumn dimension for the output block.                   | uint32_t | Must be equal to block B column dimension           | False    |
 * | rt_dim         | The row dimension for the output block.                       | uint32_t | Must be equal to block A row dimension              | False    |
 * | kt_dim         | The inner dimension.                                          | uint32_t | Must be equal to block A column dimension           | False    |
 */
// clang-format on
ALWI void mm_block_init_short(
    uint32_t in0_cb_id,
    uint32_t in1_cb_id,
    const uint32_t transpose = 0,
    uint32_t ct_dim = 1,
    uint32_t rt_dim = 1,
    uint32_t kt_dim = 1) {
    UNPACK((llk_unpack_AB_matmul_init(in0_cb_id, in1_cb_id, transpose, ct_dim, rt_dim, kt_dim)));
    MATH((llk_math_matmul_init<MATH_FIDELITY, MM_THROTTLE>(in0_cb_id, in1_cb_id, transpose, ct_dim, rt_dim, kt_dim)));
}

// clang-format off
/**
 * A short version of matmul_block initialization.
 * It is used to reconfigure srcA of the compute engine back to matmul mode.
 *
 * Return value: None
 *
 * | Argument       | Description                                                | Type     | Valid Range                               | Required |
 * |----------------|------------------------------------------------------------|----------|-------------------------------------------|----------|
 * | in0_cb_id      | The identifier of the first input circular buffer (CB)     | uint32_t | 0 to 31                                   | False    |
 * | in1_cb_id      | The identifier of the second input circular buffer (CB)    | uint32_t | 0 to 31                                   | False    |
 * | old_in1_cb_id  | The identifier of the old in1_cb_id circular buffer (CB)   | uint32_t | 0 to 31                                   | False    |
 * | ct_dim         | The coloumn dimension for the output block.                | uint32_t | Must be equal to block B column dimension | False    |
 * | rt_dim         | The row dimension for the output block.                    | uint32_t | Must be equal to block A row dimension    | False    |
 * | kt_dim         | The inner dimension.                                       | uint32_t | Must be equal to block A column dimension | False    |
 */
// clang-format on
ALWI void mm_block_init_short_with_dt(
    uint32_t in0_cb_id,
    uint32_t in1_cb_id,
    uint32_t old_in1_cb_id,
    const uint32_t transpose = 0,
    uint32_t ct_dim = 1,
    uint32_t rt_dim = 1,
    uint32_t kt_dim = 1) {
    UNPACK((llk_unpack_reconfig_data_format_srca<DST_ACCUM_MODE>(old_in1_cb_id, in1_cb_id)));
    MATH((llk_math_reconfig_data_format_srca<DST_ACCUM_MODE>(old_in1_cb_id, in1_cb_id)));
    mm_block_init_short(in0_cb_id, in1_cb_id, transpose, ct_dim, rt_dim, kt_dim);
}

// clang-format off
/**
 * A short version of matmul_block initialization.
 * It is used to reconfigure srcA and srcB of the compute engine back to matmul mode.
 *
 * Return value: None
 *
 * | Argument       | Description                                                | Type     | Valid Range                               | Required |
 * |----------------|------------------------------------------------------------|----------|-------------------------------------------|----------|
 * | in0_cb_id      | The identifier of the first input circular buffer (CB)     | uint32_t | 0 to 31                                   | True     |
 * | in1_cb_id      | The identifier of the second input circular buffer (CB)    | uint32_t | 0 to 31                                   | True     |
 * | old_in0_cb_id  | The identifier of the old in0_cb_id circular buffer (CB)   | uint32_t | 0 to 31                                   | True     |
 * | old_in1_cb_id  | The identifier of the old in1_cb_id circular buffer (CB)   | uint32_t | 0 to 31                                   | True     |
 * | ct_dim         | The coloumn dimension for the output block.                | uint32_t | Must be equal to block B column dimension | False    |
 * | rt_dim         | The row dimension for the output block.                    | uint32_t | Must be equal to block A row dimension    | False    |
 * | kt_dim         | The inner dimension.                                       | uint32_t | Must be equal to block A column dimension | False    |
 */
// clang-format on
ALWI void mm_block_init_short_with_both_dt(
    uint32_t in0_cb_id,
    uint32_t in1_cb_id,
    uint32_t old_in0_cb_id,
    uint32_t old_in1_cb_id,
    const uint32_t transpose = 0,
    uint32_t ct_dim = 1,
    uint32_t rt_dim = 1,
    uint32_t kt_dim = 1) {
    UNPACK((llk_unpack_reconfig_data_format<DST_ACCUM_MODE>(old_in1_cb_id, in1_cb_id, old_in0_cb_id, in0_cb_id)));
    MATH((llk_math_reconfig_data_format<DST_ACCUM_MODE>(old_in1_cb_id, in1_cb_id, old_in0_cb_id, in0_cb_id)));
    mm_block_init_short(in0_cb_id, in1_cb_id, transpose, ct_dim, rt_dim, kt_dim);
}

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/mul_int32_sfpu.h

```cpp
// SPDX-FileCopyrightText: © 2025 Tenstorrent AI ULC
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_binary_sfpu_mul_int32.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

// clang-format off
/**
 * Performs an elementwise mul operation with the two int32 inputs: y = mul(x0,x1)
 * Output overwrites odst in DST.
 *
 * The DST register buffer must be in acquired state via *acquire_dst* call. This call is blocking and is only available
 * on the compute engine.
 * A maximum of 4 tiles from each operand can be loaded into DST at once, for a total of 8 tiles,
 * when using 16 bit formats. This gets reduced to 2 tiles from each operand for 32 bit formats.
 *
 * Return value: None
 *
 * | Argument              | Description                                                           | Type     | Valid Range                                           | Required |
 * |-----------------------|-----------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst0                 | The index of the tile in DST register buffer to use as first operand  | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | idst1                 | The index of the tile in DST register buffer to use as second operand | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | odst                  | The index of the tile in DST register buffer to use as output         | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void mul_int32_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_mul_int32<APPROX>(idst0, idst1, odst)));
}

/**
 * Please refer to documentation for mul_int32_tile_init.
 */
ALWI void mul_int32_tile_init() { MATH((llk_math_eltwise_binary_sfpu_mul_int32_init<APPROX>())); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/mul_int_sfpu.h

```cpp
// SPDX-FileCopyrightText: © 2025 Tenstorrent AI ULC
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_binary_sfpu_mul_int.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

// clang-format off
/**
 * Performs an elementwise mul operation with the two integer inputs: y = mul(x0,x1)
 * Output overwrites odst in DST.
 *
 * The DST register buffer must be in acquired state via *acquire_dst* call. This call is blocking and is only available
 * on the compute engine.
 * A maximum of 4 tiles from each operand can be loaded into DST at once, for a total of 8 tiles,
 * when using 16 bit formats. This gets reduced to 2 tiles from each operand for 32 bit formats.
 *
 * Return value: None
 *
 * | Argument              | Description                                                           | Type     | Valid Range                                           | Required |
 * |-----------------------|-----------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst0                 | The index of the tile in DST register buffer to use as first operand  | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | idst1                 | The index of the tile in DST register buffer to use as second operand | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | odst                  | The index of the tile in DST register buffer to use as output         | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void mul_uint16_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_mul_int<APPROX, 8>(idst0, idst1, odst)));
}

/**
 * Please refer to documentation for mul_uint16_tile_init.
 */
ALWI void mul_int_tile_init() { MATH((llk_math_eltwise_binary_sfpu_mul_int_init<APPROX>())); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/pack.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "common_globals.h"

namespace ckernel {

// clang-format off
/**
 * Copies a single tile from the DEST register buffer at a specified index to a
 * specified CB at a given index. For the out_tile_index to be valid for this
 * call, cb_reserve_back(n) has to be called first to reserve at least some
 * number n > 0 of tiles in the output CB. out_tile_index = 0 then references
 * the first tile in the reserved section of the CB, up to index n - 1, which will
 * then be visible to the consumer in the same order after a cb_push_back call.
 * The DEST register buffer must be in acquired state via *acquire_dst* call.
 * This call is blocking and is only available on the compute engine.
 *
 * Each subsequent pack call will increment the write pointer in the cb by single
 * tile size. The pointer is then again set to a valid position with space for n
 * reserved tiles by another cb_reserve_back call.
 *
 * Operates in tandem with functions cb_reserve_back and cb_push_back.
 *
 * A typical use case is first the producer ensures that there is a number of
 * tiles available in the buffer via cb_reserve_back, then the producer uses
 * the pack_tile call to copy a tile from one of DEST slots to a slot in
 * reserved space and finally cb_push_back is called to announce visibility of
 * the reserved section of the circular buffer to the consumer.
 *
 * When the `out_of_order_output` flag is set to true, `pack_tile` behaves like
 * other APIs in that it writes the output tile to the tile index specified by
 * the user in `output_tile_index` within the reserved region of the circular
 * buffer, but relative to the position that might have been previously updated
 * by `cb_push_back` function. If `out_of_order_output` is false (the default),
 * `pack_tile` always operates sequentially: it writes to the next tile index
 * starting from index 0, and the `output_tile_index` parameter is ignored. In
 * this mode, each call to `pack_tile` advances the internal write pointer for
 * the reserved region, which is reset after `cb_push_back` function.
 *
 * NOTE: pack_tile doesn't need explicit initialization function prior to its call. Other op-specific
 * initialization functions (such as `tilize_init`, `reduce_init`, etc.) ensure proper initialization
 * of the packer. The reason for this stems from the fact that MATH and PACK threads need to be explicitly
 * synchronized in the kernels. To ensure this synchronization, tile packing is implemented as a separate
 * API call.
 *
 * Return value: None
 *
 * | Param Type | Name             | Description                                       | Type     | Valid Range                                          | Required |
 * |------------|------------------|---------------------------------------------------|----------|------------------------------------------------------|----------|
 * | Template   | out_of_order_output | Whether to allow out-of-order output           | bool     | true/false                                           | False    |
 * | Function   | ifrom_dst        | The index of the tile in the DEST register        | uint32_t | Must be less than the size of the DEST register (16) | True     |
 * | Function   | icb              | The identifier of the output circular buffer (CB) | uint32_t | 0 to 31                                              | True     |
 * | Function   | output_tile_index| The index of the tile in the output CB to copy to | uint32_t | Must be less than the size of the CB                 | False    |
 */
// clang-format on
template <bool out_of_order_output = false>
ALWI void pack_tile(uint32_t ifrom_dst, uint32_t icb, std::uint32_t output_tile_index = 0) {
    PACK((llk_pack<DST_ACCUM_MODE, out_of_order_output, false>(ifrom_dst, icb, output_tile_index)));
}

// clang-format off
/**
 * Copies a block of tiles from the DEST register buffer starting at a specified index
 * to a specified circular buffer (CB). The DEST register buffer must be in acquired
 * state via *acquire_dst* call. This call is blocking and is only available on the
 * compute engine. Before calling this function, cb_reserve_back(n) must be called to
 * reserve at least n > 0 tiles in the output CB. Each call to `pack_tile_block` will
 * copy `ntiles` tiles from the DEST register to the reserved region of the CB, starting
 * from index 0. The internal write pointer in the CB is advanced by `ntiles` after each
 * call, and is reset by another cb_push_back call. Operates in tandem with functions
 * cb_reserve_back and cb_push_back.
 *
 * A typical use case is for the producer to ensure that there are enough tiles available
 * in the buffer via cb_reserve_back, then use pack_tile_block to copy a block of tiles
 * from the DEST slots to the reserved space in the CB, and finally call cb_push_back to
 * announce visibility of the reserved section of the circular buffer to the consumer.
 *
 * NOTE: pack_tile_block doesn't need explicit initialization function prior to its call. Other op-specific
 * initialization functions (such as `tilize_init`, `reduce_init`, etc.) ensure proper initialization
 * of the packer. The reason for this stems from the fact that MATH and PACK threads need to be explicitly
 * synchronized in the kernels. To ensure this synchronization, tile packing is implemented as a separate
 * API call.
 *
 * Return value: None
 *
 * | Param Type | Name      | Description                                       | Type     | Valid Range                                          | Required |
 * |------------|-----------|---------------------------------------------------|----------|------------------------------------------------------|----------|
 * | Function   | ifrom_dst | The index of the first tile in the DEST register  | uint32_t | Must be less than the size of the DEST register (16) | True     |
 * | Function   | icb       | The identifier of the output circular buffer (CB) | uint32_t | 0 to 31                                              | True     |
 * | Function   | ntiles    | The number of tiles to copy from DEST to CB       | uint32_t | Must be less than the size of the DEST register (16) | True     |
 */
// clang-format on
ALWI void pack_tile_block(uint32_t ifrom_dst, uint32_t icb, uint32_t ntiles) {
    PACK((llk_matmul_pack<DST_ACCUM_MODE, false, false>(ifrom_dst, icb, ntiles)));
}

// clang-format off
/**
 * Reconfigures the packer output data format by specifying the CB ID of the new operand. This function
 * call will always perform the reconfiguration, regardless of the data format of the old operand.
 * If the new CB ID is the same as the current one, reconfiguration will still occur.
 *
 * NOTE: Packer reconfiguration functions are used similarly to the initialization function, in a sense
 * that they are called before the call to the packer function that uses the new configuration. It is
 * recommended to call this function right after other op-specific initialization functions.
 *
 * Return value: None
 *
 * | Param Type | Name       | Description                        | Type     | Valid Range | Required |
 * |------------|------------|------------------------------------|----------|-------------|----------|
 * | Function   | new_cb_id  | New data format operand value      | uint32_t | Any         | True     |
 */
// clang-format on
ALWI void pack_reconfig_data_format(const uint32_t new_cb_id) {
    PACK((llk_pack_reconfig_data_format<DST_ACCUM_MODE>(new_cb_id)));
}

// clang-format off
/**
 * Reconfigures the packer output data format by specifying the CB IDs of the old and new operands.
 * This function internally calls the reconfiguration function with the new CB ID, but before it does so,
 * it checks if the old and new data formats are different. If they are the same, it does not perform
 * the reconfiguration. This function is useful when you want to ensure that the packer only reconfigures
 * when different data format is wanted, avoiding unnecessary reconfiguration overhead.
 *
 * NOTE: Packer reconfiguration functions are used similarly to the initialization function, in a sense
 * that they are called before the call to the packer function that uses the new configuration. It is
 * recommended to call this function right after other op-specific initialization functions.
 *
 * Return value: None
 *
 * | Param Type | Name       | Description                        | Type     | Valid Range | Required |
 * |------------|------------|------------------------------------|----------|-------------|----------|
 * | Function   | old_cb_id  | Previous data format operand value | uint32_t | Any         | True     |
 * | Function   | new_cb_id  | New data format operand value      | uint32_t | Any         | True     |
 */
// clang-format on
ALWI void pack_reconfig_data_format(const uint32_t old_cb_id, const uint32_t new_cb_id) {
    PACK((llk_pack_reconfig_data_format<DST_ACCUM_MODE>(old_cb_id, new_cb_id)));
}

// clang-format off
/**
 * Helper function to reconfigure the packer L1 accumulation flag. This function would ideally be called
 * after other initialization functions that initialize the packer for a specific operation.
 * This function configures the packer to accumulate the values it takes from DEST with the ones that
 * are already in L1 at a given CB ID and tile index.
 *
 * The `l1_acc_en` parameter must be set to either 0 (disable accumulation) or 1 (enable accumulation).
 * Other values are not valid.
 *
 * NOTE: Packer reconfiguration functions are used similarly to the initialization function, in a sense
 * that they are called before the call to the packer function that uses the new configuration. It is
 * recommended to call this function right after other op-specific initialization functions.
 *
 * Return value: None
 *
 * | Param Type | Name      | Description                        | Type     | Valid Range | Required |
 * |------------|-----------|------------------------------------|----------|-------------|----------|
 * | Function   | l1_acc_en | L1 accumulation enable flag        | uint32_t | 0 or 1      | True     |
 */
// clang-format on
ALWI void pack_reconfig_l1_acc(const uint32_t l1_acc_en) { PACK((llk_pack_reconfig_l1_acc(l1_acc_en))); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/pack_untilize.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common.h"
#ifdef TRISC_MATH
#include "llk_math_unary_datacopy_api.h"
#endif
#ifdef TRISC_UNPACK
#include "llk_unpack_A_api.h"
#endif

namespace ckernel {

// clang-format off
/**
 * Performs the necessary hardware and software initialization for the pack untilize operation. This initialization
 * function should be used when the desired PACK input is already in DEST register - therefore, it doesn't
 * configure UNPACK and MATH threads for transferring data from circular buffers to DEST register (this is done with
 * `pack_untilize_init` function). Matching pack untilize operation for this initialization function is
 * `pack_untilize_dest`. In order for this untilization to be performed correctly, some other function must
 * place the tiles in the DEST register, e.g. `reduce_tile`, `copy_tile`, etc. This initialization function
 * should, therefore, be called right after the op-specific initialization function (`reduce_init`, `copy_init`, etc.).
 *
 * Since pack untilize works on a block of tiles, the user should specify the width of a single block (block_ct_dim),
 * and the width of the full block (`full_ct_dim`). It is not needed to provide the height of the block during the
 * initialization, since `pack_untilize_block` will loop over the height of the block. Note that the maximum size
 * of the block is limited by the size of the DEST and synchronization mode used. These are maximum sizes:
 * - half-sync mode (16-bit mode): 8 tiles
 * - half-sync mode (32-bit mode): 4 tiles
 * - full-sync mode (16-bit mode): 16 tiles
 * - full-sync mode (32-bit mode): 8 tiles
 *
 * NOTE: This function allows the user to specify `face_r_dim` and `num_faces` through function parameters. Setting these
 * parameters results in an expensive MMIO write and cannot be avoided currently.
 * This should be addressed more systematically within the issue tt-metal#22820, since these two values can be inferred
 * from the circular buffer description, the same way as it is done in `llk_pack_hw_configure_disaggregated`. This
 * would remove the need for `llk_pack_untilize_hw_configure_disaggregated` altogether and we would pay the price
 * of the MMIO write only once, in `compute_kernel_hw_startup`.
 *
 * Return value: None
 *
 * | Param Type | Name         | Description                              | Type      | Valid Range     | Required |
 * |------------|--------------|------------------------------------------|-----------|-----------------|----------|
 * | Template   | block_ct_dim | Width of a single block in tiles         | uint32_t  | 1 to max (see note) | False (default = 8) |
 * | Template   | full_ct_dim  | Width of a full input in tiles           | uint32_t  | Divisible by block_ct_dim | False    |
 * | Template   | narrow_row   |  Whether the provided input is narrow    | bool      | true/false      | False    |
 * | Template   | row_num_datums | Number of datums per row               | uint32_t  | >= 1            | False    |
 * | Function   | ocb          | Output circular buffer identifier        | uint32_t  | 0 to 31         | True     |
 * | Function   | face_r_dim   | Face height in rows                      | uint32_t  | 1, 8 or 16      | False (default = 16) |
 * | Function   | num_faces    | Number of faces                          | uint32_t  | 1, 2 or 4       | False (default = 4) |
 */
// clang-format on
template <
    uint32_t block_ct_dim = 8,
    uint32_t full_ct_dim = block_ct_dim,
    bool narrow_row = false,
    std::uint32_t row_num_datums = TILE_C_DIM>
ALWI void pack_untilize_dest_init(uint32_t ocb, uint32_t face_r_dim = 16, uint32_t num_faces = 4) {
#ifdef ARCH_BLACKHOLE
    // Needed for setting swizzle_32b:
    MATH((llk_math_hw_configure_disaggregated<true, true>(0, 0)));
#endif
    // A workaround for tt-metal#17132. Should be addressed more systematically.
    PACK(
        (llk_pack_untilize_hw_configure_disaggregated<DST_ACCUM_MODE, false /*untilize*/>(ocb, face_r_dim, num_faces)));
    PACK((llk_pack_untilize_init<block_ct_dim, full_ct_dim, false, narrow_row, row_num_datums>(
        ocb, face_r_dim, num_faces)));
    PACK((llk_init_packer_dest_offset_registers<true, false>()));
}

// clang-format off
/**
 * Performs the necessary hardware and software initialization for the pack untilize operation. Initializes all three
 * threads: UNPACK, MATH, and PACK. This function should be used when the desired PACK input is not yet in DEST
 * register. Internally, this function calls `pack_untilize_dest_init` to initialize the PACK thread.
 *
 * Since pack untilize works on a block of tiles, the user should specify the width of a single block (block_ct_dim),
 * and the width of the full block (`full_ct_dim`). It is not needed to provide the height of the block during the
 * initialization, since `pack_untilize_block` will loop over the height of the block. Note that the maximum size
 * of the block is limited by the size of the DEST and synchronization mode used. These are maximum sizes:
 * - half-sync mode (16-bit mode): 8 tiles
 * - half-sync mode (32-bit mode): 4 tiles
 * - full-sync mode (16-bit mode): 16 tiles
 * - full-sync mode (32-bit mode): 8 tiles
 *
 * NOTE: This function uses default `face_r_dim` and `num_faces` values (16 and 4, respectively). Setting these
 * parameters results in an expensive MMIO write and cannot be avoided currently.
 * This should be addressed more systematically within the issue tt-metal#22820, since these two values can be inferred
 * from the circular buffer description, the same way as it is done in `llk_pack_hw_configure_disaggregated`. This
 * would remove the need for `llk_pack_untilize_hw_configure_disaggregated` altogether and we would pay the price
 * of the MMIO write only once, in `compute_kernel_hw_startup`.
 *
 * Return value: None
 *
 * | Param Type | Name         | Description                                | Type      | Valid Range     | Required |
 * |------------|--------------|--------------------------------------------|-----------|-----------------|----------|
 * | Template   | block_ct_dim | Width of a single block in tiles           | uint32_t  | 1 to max (see note) | False (default = 8) |
 * | Template   | full_ct_dim  | Width of a full input in tiles             | uint32_t  | Divisible by block_ct_dim | False    |
 * | Function   | icb          | Input circular buffer identifier           | uint32_t  | 0 to 31         | True     |
 * | Function   | ocb          | Output circular buffer identifier          | uint32_t  | 0 to 31         | True     |
 */
// clang-format on
template <uint32_t block_ct_dim = 8, uint32_t full_ct_dim = block_ct_dim>
ALWI void pack_untilize_init(uint32_t icb, uint32_t ocb) {
    UNPACK((llk_unpack_A_init<BroadcastType::NONE, false, EltwiseBinaryReuseDestType::NONE, UnpackToDestEn>(
        false, false, icb)));  // init must be after configure
    MATH((llk_math_eltwise_unary_datacopy_init<A2D, DST_ACCUM_MODE, BroadcastType::NONE>(
        false /*transpose of faces*/, false /*transpose within 16x16 face*/, icb)));
    pack_untilize_dest_init<block_ct_dim, full_ct_dim>(ocb);
}

// clang-format off
/**
 * Performs the untilize operation on a block of tiles. Loops over the provided block size. The block is characterized
 * by its width in tiles (block_ct_dim) and height in tiles (block_rt_dim). The width of the block has to be the same
 * as the one provided during the initialization of the pack untilize operation (`pack_untilize_init`). It is not
 * needed to provide the height of the block during the initialization, since `pack_untilize_block` will loop over the
 * height of the block. Note that the maximum size of the block is limited by the size of the DEST and synchronization
 * mode used. These are maximum sizes:
 * - half-sync mode (16-bit mode): 8 tiles
 * - half-sync mode (32-bit mode): 4 tiles
 * - full-sync mode (16-bit mode): 16 tiles
 * - full-sync mode (32-bit mode): 8 tiles
 *
 * Return value: None
 *
 * | Param Type | Name         | Description                                 | Type      | Valid Range     | Required |
 * |------------|--------------|---------------------------------------------|-----------|-----------------|----------|
 * | Template   | block_ct_dim | Width of a single block in tiles            | uint32_t  | 1 to max (see note) | False (default = 8) |
 * | Template   | full_ct_dim  | Width of a full input in tiles              | uint32_t  | Divisible by block_ct_dim | False    |
 * | Function   | icb          | Input circular buffer identifier            | uint32_t  | 0 to 31         | True     |
 * | Function   | block_rt_dim | Height of a single block in tiles           | uint32_t  | >= 1            | True     |
 * | Function   | ocb          | Output circular buffer identifier           | uint32_t  | 0 to 31         | True     |
 * | Function   | block_c_index | Index of the currently processed block     | uint32_t  | >= 0            | False    |
 */
// clang-format on
template <uint32_t block_ct_dim = 8, uint32_t full_ct_dim = block_ct_dim>
ALWI void pack_untilize_block(uint32_t icb, uint32_t block_rt_dim, uint32_t ocb, uint32_t block_c_index = 0) {
    for (uint32_t r = 0; r < block_rt_dim; ++r) {
        MATH((llk_math_wait_for_dest_available()));
        for (uint32_t c = 0; c < block_ct_dim; ++c) {
            UNPACK(
                (llk_unpack_A<BroadcastType::NONE, false, EltwiseBinaryReuseDestType::NONE, UnpackToDestEn>(icb, c)));
            MATH((llk_math_eltwise_unary_datacopy<A2D, DST_ACCUM_MODE, BroadcastType::NONE, UnpackToDestEn>(c)));
        }

        MATH((llk_math_dest_section_done<DST_ACCUM_MODE>()));

        PACK((llk_packer_wait_for_math_done()));
        PACK((llk_pack_untilize<block_ct_dim, full_ct_dim>(1 /*num_blocks*/, ocb, FACE_R_DIM, 4, block_c_index)));
        PACK((llk_pack_dest_section_done<DST_ACCUM_MODE>()));
    }
}

// clang-format off
/**
 * Performs the pack untilize operation when PACK input is already in DEST register. In order to properly initialize the operation,
 * a call to `pack_untilize_dest_init` must be made before this function. The width of the block has to be the same
 * as the one provided during the initialization of the pack untilize operation (`pack_untilize_dest_init`). In order for this
 * untilization to be performed correctly, some other function must place the tiles in the DEST register, e.g. `reduce_tile`,
 * `copy_tile`, etc. Similarly as `pack_untilize_block`, this function operates on a whole block that needs to be untilized.
 * Note that the maximum size of the block is limited by the size of the DEST
 * and synchronization mode used. These are maximum sizes:
 * - half-sync mode (16-bit mode): 8 tiles
 * - half-sync mode (32-bit mode): 4 tiles
 * - full-sync mode (16-bit mode): 16 tiles
 * - full-sync mode (32-bit mode): 8 tiles
 *
 * Return value: None
 *
 * | Param Type | Name               | Description                                                                  | Type      | Valid Range                             | Required            |
 * |------------|--------------------|------------------------------------------------------------------------------|-----------|-----------------------------------------|---------------------|
 * | Template   | block_ct_dim       | Width of a single block in tiles                                             | uint32_t  | 1 to max (see note)                     | False (default = 8) |
 * | Template   | full_ct_dim        | Width of a full input in tiles                                               | uint32_t  | Divisible by block_ct_dim               | False               |
 * | Template   | diagonal           | Whether to use diagonal packing                                              | bool      | true/false                              | False               |
 * | Template   | narrow_row         | Whether the provided input is narrow                                         | bool      | true/false                              | False               |
 * | Template   | row_num_datums     | Number of datums per row                                                     | uint32_t  | >= 1                                    | False               |
 * | Template   | tile_dst_ct_offset | Compile time offset for the index of the tile in the dest from which to pack | uint32_t  | 0 to 7 (0 to 3 if fp32 dest is enabled) | False (default=0)   |
 * | Function   | ocb                | Output circular buffer identifier                                            | uint32_t  | 0 to 31                                 | True                |
 * | Function   | block_rt_dim       | Height of a single block in tiles                                            | uint32_t  | >= 1                                    | False (default=1)   |
 * | Function   | block_c_index      | Block column index (used when full_ct_dim > block_ct_dim)                    | uint32_t  | >= 0                                    | False (default=0)   |
 * | Function   | face_r_dim         | Face height in rows                                                          | uint32_t  | 1, 8 or 16                              | False (default=16)  |
 * | Function   | num_faces          | Number of faces                                                              | uint32_t  | 1, 2 or 4                               | False (default=4)   |
 * | Function   | tile_dst_offset    | Runtime offset for the index of the tile in the dest from which to pack      | uint32_t  | 0 to 7 (0 to 3 if fp32 dest is enabled) | False (default=0)   |
 */
// clang-format on
template <
    uint32_t block_ct_dim = 8,
    uint32_t full_ct_dim = block_ct_dim,
    bool diagonal = false,
    bool narrow_row = false,
    std::uint32_t row_num_datums = TILE_C_DIM,
    uint32_t tile_dst_ct_offset = 0>
ALWI void pack_untilize_dest(
    uint32_t ocb,
    uint32_t block_rt_dim = 1,
    uint32_t block_c_index = 0 /* used when full_ct_dim > block_ct_dim*/,
    uint32_t face_r_dim = 16,
    uint32_t num_faces = 4,
    uint32_t tile_dst_rt_offset = 0) {
    PACK((llk_pack_untilize<block_ct_dim, full_ct_dim, diagonal, narrow_row, row_num_datums, tile_dst_ct_offset>(
        block_rt_dim, ocb, face_r_dim, num_faces, block_c_index, tile_dst_rt_offset)));
}

// clang-format off
/**
 * Uninitializes the pack untilize operation, allowing another operations to be initialized. Needs to be
 * called after the last call to `pack_untilize_dest` or `pack_untilize_block`, before initializing
 * another operation.
 *
 * NOTE: This function is not in line with our programming model, and will be removed by the end of 2025
 * as a part of tt-metal#22904.
 *
 * Return value: None
 *
 * | Param Type | Name | Description                        | Type     | Valid Range | Required |
 * |------------|------|------------------------------------|----------|-------------|----------|
 * | Function   | ocb  | Output circular buffer identifier  | uint32_t | 0 to 31     | True     |
 */
// clang-format on
ALWI void pack_untilize_uninit(uint32_t ocb) {
    PACK((llk_pack_init(ocb)));
    PACK((llk_init_packer_dest_offset_registers<false>()));

#ifdef ARCH_BLACKHOLE
    PACK((llk_pack_untilize_uninit(ocb)));
#endif
}

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/quantization.h

```cpp
// SPDX-FileCopyrightText: © 2025 Tenstorrent AI ULC
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_binary_sfpu_quant.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

// clang-format off
/**
 * Performs an elementwise per-tensor affine quantization operation on the first operand using the scaling factor in the second operand.
 * Output overwrites odst in DST.
 *
 * Return value: None
 *
 * | Argument       | Description                                                           | Type     | Valid Range                                           | Required |
 * |----------------|-----------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst0          | The index of the tile in DST register buffer to use as first operand  | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | idst1          | The index of the tile in DST register buffer to use as second operand | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | odst           | The index of the tile in DST register buffer to use as output         | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void quant_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_quant_int32<APPROX>(idst0, idst1, odst)));
}

// clang-format off
/**
 * Performs an elementwise per-tensor affine re-quantization operation on the first operand using the scaling factor in the second operand.
 * Output overwrites odst in DST.
 *
 * Return value: None
 *
 * | Argument       | Description                                                           | Type     | Valid Range                                           | Required |
 * |----------------|-----------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst0          | The index of the tile in DST register buffer to use as first operand  | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | idst1          | The index of the tile in DST register buffer to use as second operand | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | odst           | The index of the tile in DST register buffer to use as output         | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void requant_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_requant_int32<APPROX>(idst0, idst1, odst)));
}

// clang-format off
/**
 * Performs an elementwise per-tensor affine de-quantization operation on the first operand using the scaling factor in the second operand.
 * Output overwrites odst in DST.
 *
 * Return value: None
 *
 * | Argument       | Description                                                           | Type     | Valid Range                                           | Required |
 * |----------------|-----------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst0          | The index of the tile in DST register buffer to use as first operand  | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | idst1          | The index of the tile in DST register buffer to use as second operand | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | odst           | The index of the tile in DST register buffer to use as output         | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void dequant_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_dequant_int32<APPROX>(idst0, idst1, odst)));
}

// clang-format off
/**
 * Initialize the sfpu with the zero point argument of the quantization Op.
 * To be called once at beginning of a kernel.
 *
 * Return value: None
 *
 * | Argument   | Description                           | Data type | Valid range | Required |
 * |------------|---------------------------------------|-----------|-------------|----------|
 * | zero_point | The zero point of the quantization Op | uint32_t  | Any number  | Yes      |
 * */
// clang-format on
ALWI void quant_tile_init(const uint32_t zero_point) {
    MATH((llk_math_eltwise_binary_sfpu_quant_int32_init<APPROX>(zero_point)));
}

// clang-format off
/**
 * Initialize the sfpu with the zero point argument of the re-quantization Op.
 * To be called once at beginning of a kernel.
 *
 * Return value: None
 *
 * | Argument   | Description                              | Data type | Valid range | Required |
 * |------------|------------------------------------------|-----------|-------------|----------|
 * | zero_point | The zero point of the re-quantization Op | uint32_t  | Any number  | Yes      |
 * */
// clang-format on
ALWI void requant_tile_init(const uint32_t zero_point) {
    MATH((llk_math_eltwise_binary_sfpu_requant_int32_init<APPROX>(zero_point)));
}

// clang-format off
/**
 * Initialize the sfpu with the zero point argument of the de-quantization Op.
 * To be called once at beginning of a kernel.
 *
 * Return value: None
 *
 * | Argument   | Description                              | Data type | Valid range | Required |
 * |------------|------------------------------------------|-----------|-------------|----------|
 * | zero_point | The zero point of the de-quantization Op | uint32_t  | Any number  | Yes      |
 * */
// clang-format on
ALWI void dequant_tile_init(const uint32_t zero_point) {
    MATH((llk_math_eltwise_binary_sfpu_dequant_int32_init<APPROX>(zero_point)));
}

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/reconfig_data_format.h

```cpp
// SPDX-FileCopyrightText: © 2024 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "common_globals.h"

namespace ckernel {

/**
 * Helper function to reconfigure srca and srcb data formats.
 */
template <bool to_from_int8 = false>
ALWI void reconfig_data_format(const uint32_t srca_new_operand, const uint32_t srcb_new_operand) {
    UNPACK((llk_unpack_reconfig_data_format<DST_ACCUM_MODE, to_from_int8>(srca_new_operand, srcb_new_operand)));
    MATH((llk_math_reconfig_data_format<DST_ACCUM_MODE, to_from_int8>(srca_new_operand, srcb_new_operand)));
}

/**
 * Helper function to reconfigure srca/srcb data formats, only if they differ from existing formats.
 */
template <bool to_from_int8 = false>
ALWI void reconfig_data_format(
    const uint32_t srca_old_operand,
    const uint32_t srca_new_operand,
    const uint32_t srcb_old_operand,
    const uint32_t srcb_new_operand) {
    UNPACK((llk_unpack_reconfig_data_format<DST_ACCUM_MODE, to_from_int8>(
        srca_old_operand, srca_new_operand, srcb_old_operand, srcb_new_operand)));
    MATH((llk_math_reconfig_data_format<DST_ACCUM_MODE, to_from_int8>(
        srca_old_operand, srca_new_operand, srcb_old_operand, srcb_new_operand)));
}

/**
 * Helper function to reconfigure srca data format.
 */
template <bool to_from_int8 = false>
ALWI void reconfig_data_format_srca(const uint32_t srca_new_operand) {
    UNPACK((llk_unpack_reconfig_data_format_srca<DST_ACCUM_MODE, to_from_int8>(srca_new_operand)));
    MATH((llk_math_reconfig_data_format_srca<DST_ACCUM_MODE, to_from_int8>(srca_new_operand)));
}

/**
 * Helper function to reconfigure srca input data format, only if it differs from existing format.
 */
template <bool to_from_int8 = false>
ALWI void reconfig_data_format_srca(const uint32_t srca_old_operand, const uint32_t srca_new_operand) {
    UNPACK((llk_unpack_reconfig_data_format_srca<DST_ACCUM_MODE, to_from_int8>(srca_old_operand, srca_new_operand)));
    MATH((llk_math_reconfig_data_format_srca<DST_ACCUM_MODE, to_from_int8>(srca_old_operand, srca_new_operand)));
}

/**
 * Helper function to reconfigure srcb input data format.
 */
template <bool to_from_int8 = false>
ALWI void reconfig_data_format_srcb(const uint32_t srcb_new_operand) {
    UNPACK((llk_unpack_reconfig_data_format_srcb<DST_ACCUM_MODE, to_from_int8>(srcb_new_operand)));
    MATH((llk_math_reconfig_data_format_srcb<DST_ACCUM_MODE, to_from_int8>(srcb_new_operand)));
}

/**
 * Helper function to reconfigure srcb input data format, only if it differs from existing format.
 */
template <bool to_from_int8 = false>
ALWI void reconfig_data_format_srcb(const uint32_t srcb_old_operand, const uint32_t srcb_new_operand) {
    UNPACK((llk_unpack_reconfig_data_format_srcb<DST_ACCUM_MODE, to_from_int8>(srcb_old_operand, srcb_new_operand)));
    MATH((llk_math_reconfig_data_format_srcb<DST_ACCUM_MODE, to_from_int8>(srcb_old_operand, srcb_new_operand)));
}

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/reduce.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common.h"
#ifdef TRISC_MATH
#include "llk_math_reduce_api.h"
#endif

#ifdef TRISC_UNPACK
#include "llk_unpack_AB_api.h"
#endif

namespace ckernel {

// clang-format off
/**
 * Performs the necessary hardware and software initialization for reduce operation for provided circular buffer identifiers (CB IDs). In order for reduce
 * operation to be performed, this function call must be followed by a call to `reduce_tile` or `reduce_tile_math`.
 * If another reduce op is needed which uses different CB IDs, then another reduce_init needs to be called as a part of that reduce operation.
 *
 * The `icb_scaler` circular buffer must contain the scaling factors for the reduction. The most straightforward way of filling the `icb_scaler` with the scaling
 * factors is to populate first row of each face with the followin values:
 * - If `reduce_type = SUM`, all scaling factors should preferably be 1.
 * - If `reduce_type = AVG`, all scaling factors should preferably be 1/N (where N is the number of elements being averaged, except if the reduction dimension is scalar,
 * in which case the scaling factor should be 1/sqrt(N)).
 * - If `reduce_type = MAX`, all scaling factors should preferably be 1.
 *
 * NOTE: For SUM and AVG operations, the value in `icb_scaler` is a scaling factor of the final sum of values across rows/columns/both, so there is no real constraint in terms
 * of it's value. For MAX operation, maximum value will be obtained as expected, but it will be scaled by the values in `icb_scaler`. In any case, it is recommended to use the
 * above-mentioned scaling factors to ensure that operations function as intended. Refer to ISA documentation for more details.
 * NOTE: For other valid ways of populating the `icb_scaler`, refer to the ISA documentation.
 *
 * Return value: None
 *
 * | Param Type | Name                      | Description                                                                             | Type      | Valid Range                                    | Required |
 * |------------|---------------------------|-----------------------------------------------------------------------------------------|-----------|------------------------------------------------|----------|
 * | Template   | reduce_type               | The type of reduce op - sum, average or maximum                                         | PoolType  | {SUM, AVG, MAX}                                | True     |
 * | Template   | reduce_dim                | The dimension of reduce op - row, column or both                                        | ReduceDim | {REDUCE_ROW, REDUCE_COL, REDUCE_SCALAR}        | True     |
 * | Template   | enforce_fp32_accumulation | Enable accumulation of reduction in full FP32 precision (Requires DST_ACCUM_MODE==true) | bool      | {true, false}                                  | True     |
 * | Function   | icb                       | The identifier of the circular buffer (CB) containing operand A                         | uint32_t  | 0 to 31                                        | True     |
 * | Function   | icb_scaler                | CB holding scaling factors (see above)                                                  | uint32_t  | 0 to 31                                        | True     |
 * | Function   | ocb                       | The identifier of the output circular buffer (CB)                                       | uint32_t  | 0 to 31                                        | True     |
 */
// clang-format on
template <PoolType reduce_type = REDUCE_OP, ReduceDim reduce_dim = REDUCE_DIM, bool enforce_fp32_accumulation = false>
ALWI void reduce_init(uint32_t icb, uint32_t icb_scaler, uint32_t ocb) {
    UNPACK((llk_unpack_AB_reduce_init<reduce_dim, BroadcastType::NONE, enforce_fp32_accumulation>(icb, icb_scaler)));
    MATH((llk_math_reduce_init<reduce_type, reduce_dim, DST_ACCUM_MODE, MATH_FIDELITY, enforce_fp32_accumulation>()));
    PACK((llk_pack_reduce_mask_config<false /*untilize*/, reduce_dim>()));
}

// clang-format off
/**
 * Resets the packer edge mask configuration to its default state by clearing any previously set masks. Needs to be called after
 * reduce_tile if the next operation requires default packer state. In case that the next operation is reduce operation across the
 * same dimension, this call can be omitted. If this function is not called, the packer will continue to use the edge masks set
 * by the latest reduce_init call, which may lead to incorrect packing behavior in subsequent operations.
 *
 * NOTE: This function is not in line with our programming model, and will be removed by the end of 2025
 * as a part of tt-metal#22904.
 *
 * | Param Type | Name | Description                                      | Type | Valid Range | Required |
 * |------------|------|--------------------------------------------------|------|-------------|----------|
 * | Function   | —    | No parameters                                    |  —   |      —      |    —     |
 */
// clang-format on
ALWI void reduce_uninit() { PACK((llk_pack_reduce_mask_clear())); }

// clang-format off
/**
 * Performs a reduction operation *B = reduce(A)* using reduce_func for dimension reduction on a tile in the CB at a given index and writes the
 * result to the DST register at index *dst_tile_index*. Reduction can be of type *Reduce::R*, *Reduce::C*, or *Reduce::RC*, identifying the
 * dimension(s) to be reduced in size to 1. The DST register buffer must be in acquired state via *acquire_dst* call.
 *
 * The `icb_scaler` circular buffer must contain the scaling factors for the reduction. The most straightforward way of filling the `icb_scaler` with the scaling
 * factors is to populate first row of each face with the followin values:
 * - If `reduce_type = SUM`, all scaling factors should preferably be 1.
 * - If `reduce_type = AVG`, all scaling factors should preferably be 1/N (where N is the number of elements being averaged, except if the reduction dimension is scalar,
 * in which case the scaling factor should be 1/sqrt(N)).
 * - If `reduce_type = MAX`, all scaling factors should preferably be 1.
 *
 * The templates take `reduce_type` which can be `ReduceFunc::Sum`, `ReduceFunc::Avg`, or `ReduceFunc::Max` and `reduce_dim` which can be `Reduce::R`, `Reduce::C`, or
 * `Reduce::RC`. They can also be specified by defines REDUCE_OP and REDUCE_DIM.
 *
 * NOTE: Before the next operation is initialized, the `reduce_uninit` function must be called to reset the packer state to default.
 * NOTE: For SUM and AVG operations, the value in `icb_scaler` is a scaling factor of the final sum of values across rows/columns/both, so there is no real constraint in terms
 * of it's value. For MAX operation, maximum value will be obtained as expected, but it will be scaled by the values in `icb_scaler`. In any case, it is recommended to use the
 * above-mentioned scaling factors to ensure that operations function as intended. Refer to ISA documentation for more details.
 * NOTE: For other valid ways of populating the `icb_scaler`, refer to the ISA documentation.
 * Return value: None
 *
 * | Param Type | Name                      | Description                                                                             | Type      | Valid Range                                    | Required |
 * |------------|---------------------------|-----------------------------------------------------------------------------------------|-----------|------------------------------------------------|----------|
 * | Template   | reduce_type               | The type of reduce op - sum, average or maximum                                         | PoolType  | {SUM, AVG, MAX}                                | True     |
 * | Template   | reduce_dim                | The dimension of reduce op - row, column or both                                        | ReduceDim | {REDUCE_ROW, REDUCE_COL, REDUCE_SCALAR}        | True     |
 * | Template   | enforce_fp32_accumulation | Enable accumulation of reduction in full FP32 precision (Requires DST_ACCUM_MODE==true) | bool      | {true, false}                                  | True     |
 * | Function   | icb                       | The identifier of the circular buffer (CB) containing operand A                         | uint32_t  | 0 to 31                                        | True     |
 * | Function   | icb_scaler                | CB holding scaling factors (see above)                                                  | uint32_t  | 0 to 31                                        | True     |
 * | Function   | itile                     | The index of the tile within the first CB                                               | uint32_t  | Must be less than the size of the CB           | True     |
 * | Function   | itile_scaler              | The index of the tile within the scaling factor CB.                                     | uint32_t  | Must be less than the size of the CB           | True     |
 * | Function   | idst                      | The index of the tile in DST REG for the result                                         | uint32_t  | Must be less than the acquired size of DST REG | True     |
 */
// clang-format on
template <PoolType reduce_type = REDUCE_OP, ReduceDim reduce_dim = REDUCE_DIM, bool enforce_fp32_accumulation = false>
ALWI void reduce_tile(uint32_t icb, uint32_t icb_scaler, uint32_t itile, uint32_t itile_scaler, uint32_t idst) {
    MATH((llk_math_reduce<reduce_type, reduce_dim, DST_ACCUM_MODE, MATH_FIDELITY, false, enforce_fp32_accumulation>(
        icb, icb_scaler, idst)));
    UNPACK((llk_unpack_AB(icb, icb_scaler, itile, itile_scaler)));
}

// clang-format off
/**
 * Performs a math-only reduction operation on a tile in the DST register. Assumes that source tiles are already in source registers.
 *
 * | Param Type | Name                      | Description                                                                             | Type      | Valid Range                                    | Required |
 * |------------|---------------------------|-----------------------------------------------------------------------------------------|-----------|------------------------------------------------|----------|
 * | Template   | reduce_type               | The type of reduce op - sum, average or maximum                                         | PoolType  | {SUM, AVG, MAX}                                | True     |
 * | Template   | reduce_dim                | The dimension of reduce op - row, column or both                                        | ReduceDim | {REDUCE_ROW, REDUCE_COL, REDUCE_SCALAR}        | True     |
 * | Template   | enforce_fp32_accumulation | Enable accumulation of reduction in full FP32 precision (Requires DST_ACCUM_MODE==true) | bool      | {true, false}                                  | True     |
 * | Function   | idst                      | The index of the tile in DST REG for the result                                         | uint32_t  | Must be less than the acquired size of DST REG | True     |
 * | Function   | num_faces                 | Number of faces to reduce (optional, default 4)                                         | uint32_t  | 1 to 4                                         | False    |
 */
// clang-format on
template <PoolType reduce_type = REDUCE_OP, ReduceDim reduce_dim = REDUCE_DIM, bool enforce_fp32_accumulation = false>
ALWI void reduce_tile_math(uint32_t idst, uint32_t num_faces = 4) {
    MATH((llk_math_reduce<reduce_type, reduce_dim, DST_ACCUM_MODE, MATH_FIDELITY, false, enforce_fp32_accumulation>(
        idst, num_faces)));
}

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/reg_api.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"

namespace ckernel {

/**
 * @deprecated This function is deprecated, please use `tile_regs_acquire()` instead.
 * See https://github.com/tenstorrent/tt-metal/issues/5868#issuecomment-2101726935
 *
 * Acquires an exclusive lock on the internal DST register for the current
 * Tensix core.
 *
 * This register is an array of 16 tiles of 32x32 elements each.
 * This is a blocking function, i.e. this function will wait until the lock is acquired.
 *
 * This is only available on the compute engine.
 *
 * Return value: None
 *
 * How the destination register will be shared and synchronized between TRISC threads will depend on the compute kernel
 * configuration.
 */
[[deprecated("Use tile_regs_acquire() instead")]]
ALWI void acquire_dst() {
    MATH((llk_math_wait_for_dest_available()));

    PACK((llk_packer_wait_for_math_done()));
}

// new APIs, TODO: migrate all kernels to these

/**
 * Acquire an exclusive lock on the DST register for the MATH thread.
 * This register is an array of 16 tiles of 32x32 elements each.
 * This is a blocking function, i.e. this function will wait until the lock is acquired.
 */
ALWI void tile_regs_acquire() { MATH((llk_math_wait_for_dest_available())); }

/**
 * Acquire an exclusive lock on the DST register for the PACK thread.
 * It waits for the MATH thread to commit the DST register.
 * This is a blocking function, i.e. this function will wait until the lock is acquired.
 */
ALWI void tile_regs_wait() { PACK((llk_packer_wait_for_math_done())); }

/**
 * @deprecated This function is deprecated, please use `tile_regs_release()` instead.
 * See https://github.com/tenstorrent/tt-metal/issues/5868#issuecomment-2101726935
 *
 * Releases the exclusive lock on the internal DST register for the current
 * Tensix core. This lock had to be previously acquired with acquire_dst. This
 * call is blocking and is only available on the compute engine.
 *
 * Return value: None
 *
 * How the destination register will be shared and synchronized between TRISC threads will depend on the compute kernel
 * configuration.
 */
[[deprecated("Use tile_regs_release() instead")]]
ALWI void release_dst() {
    MATH((llk_math_dest_section_done<DST_ACCUM_MODE>()));
    PACK((llk_pack_dest_section_done<DST_ACCUM_MODE>()));
}

// new APIs, TODO: migrate all kernels to these

/**
 * Release lock on DST register by MATH thread. The lock had to be previously acquired with tile_regs_acquire.
 */
ALWI void tile_regs_commit() { MATH((llk_math_dest_section_done<DST_ACCUM_MODE>())); }

/**
 * Release lock on DST register by PACK thread. The lock had to be previously acquired with tile_regs_wait.
 */
ALWI void tile_regs_release() { PACK((llk_pack_dest_section_done<DST_ACCUM_MODE>())); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/reshuffle.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_unary_sfpu_reshuffle_rows.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

// clang-format off
// row reshuffle
/**
 * Reshuffles the rows of the input tile to locations given by indices stored
 * at L1 address provided in idx_addr. The DST register buffer must be in
 * acquired state via *acquire_dst* call. This call is blocking and is only
 * available on the compute engine.
 *
 * Return value: None
 *
 * | Argument        | Description                                                                | Type     | Valid Range                                           | Required |
 * |-----------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst            | The index of the tile in DST register buffer to perform the computation on | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | idx_addr        | Address at which array of output row indices is stored                     | uint32_t |                                                       | True     |
 */
 // clang-format on
ALWI void reshuffle_rows_tile(uint32_t idst, uint32_t idx_addr) {
    MATH((llk_math_eltwise_unary_sfpu_reshuffle_rows<APPROX>(idst, idx_addr)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void reshuffle_rows_tile_init() { MATH((llk_math_eltwise_unary_sfpu_reshuffle_rows_init<APPROX>())); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/softmax.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/eltwise_unary/exp.h"
#include "compute_kernel_api/eltwise_unary/recip.h"
```

## tt_metal/include/compute_kernel_api/sub_int_sfpu.h

```cpp
// SPDX-FileCopyrightText: © 2025 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_binary_sfpu_sub_int.h"
#include "llk_math_eltwise_binary_sfpu_rsub_int32.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

// clang-format off
/**
 * Performs an elementwise sub operation with the two integer inputs: y = sub(x0,x1)
 * Output overwrites odst in DST.
 *
 * The DST register buffer must be in acquired state via *acquire_dst* call. This call is blocking and is only available
 * on the compute engine.
 * A maximum of 4 tiles from each operand can be loaded into DST at once, for a total of 8 tiles,
 * when using 16 bit formats. This gets reduced to 2 tiles from each operand for 32 bit formats.
 *
 * Return value: None
 *
 * | Argument              | Description                                                           | Type     | Valid Range                                           | Required |
 * |-----------------------|-----------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst0                 | The index of the tile in DST register buffer to use as first operand  | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | idst1                 | The index of the tile in DST register buffer to use as second operand | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | odst                  | The index of the tile in DST register buffer to use as output         | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void sub_int32_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_sub_int<APPROX, 8, InstrModLoadStore::INT32, false>(idst0, idst1, odst)));
}

ALWI void sub_uint32_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_sub_int<APPROX, 8, InstrModLoadStore::INT32, false>(idst0, idst1, odst)));
}

ALWI void sub_uint16_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_sub_int<APPROX, 8, InstrModLoadStore::LO16, false>(idst0, idst1, odst)));
}

ALWI void rsub_int32_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_rsub_int32<APPROX>(idst0, idst1, odst)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void sub_int_tile_init() { MATH((llk_math_eltwise_binary_sfpu_sub_int_init<APPROX>())); }

ALWI void rsub_int32_tile_init() { MATH((llk_math_eltwise_binary_sfpu_rsub_int32_init<APPROX>())); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/tile_move_copy.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"

#ifdef TRISC_MATH
#include "llk_math_unary_datacopy_api.h"
#endif

#ifdef TRISC_UNPACK
#include "llk_unpack_A_api.h"
#endif
namespace ckernel {

// clang-format off
/**
 * Perform the init short for copy tile. This does not reconfigure the unpacker data types.
 * Return value: None
 *
 * | Argument    | Description                                       | Type     | Valid Range                                        | Required |
 * |-------------|---------------------------------------------------|----------|----------------------------------------------------|----------|
 * | cbid        | The identifier of the input circular buffer (CB)  | uint32_t | 0 to 31                                            | False    |
 * | transpose   | Flag to perform transpose on SrcA                 | uint32_t | Any positive value will indicate tranpose is set   | False    |
 */
// clang-format on
ALWI void copy_tile_to_dst_init_short(uint32_t cbid, uint32_t transpose = 0) {
    UNPACK((llk_unpack_A_init<BroadcastType::NONE, false, EltwiseBinaryReuseDestType::NONE, UnpackToDestEn>(
        transpose, false /*transpose within 16x16 face*/, cbid)));
    MATH((llk_math_eltwise_unary_datacopy_init<A2D, DST_ACCUM_MODE, BroadcastType::NONE>(
        false /*transpose of faces*/, false /*transpose within 16x16 face*/, cbid)));
}
/**
 * Perform a init for the copy tile operation. This calls the short init function and initializes packer dst offset
 * registers.
 */
ALWI void copy_tile_init(uint32_t cbid) { copy_tile_to_dst_init_short(cbid); }

// clang-format off
/**
 * Return value: None
 *
 * | Argument       | Description                                                       | Type     | Valid Range                                       | Required |
 * |----------------|-------------------------------------------------------------------|----------|---------------------------------------------------|----------|
 * | old_cbid       | The identifier of the previous input circular buffer (CB) to SrcA | uint32_t | 0 to 31                                           | True     |
 * | new_cbid       | The identifier of the new input circular buffer (CB) to SrcA      | uint32_t | 0 to 31                                           | True     |
 * | transpose      | Flag to perform transpose on SrcA                                 | uint32_t | Any positive value will indicate tranpose is set  | False    |
 */
 // clang-format on
ALWI void copy_tile_to_dst_init_short_with_dt(uint32_t old_cbid, uint32_t new_cbid, uint32_t transpose = 0) {
    // This reconfig call checks if old operand has different data format to
    // new operand idx, otherwise no reconfig call occurs
    UNPACK((llk_unpack_reconfig_data_format_srca<DST_ACCUM_MODE>(old_cbid, new_cbid)));
    MATH((llk_math_reconfig_data_format_srca<DST_ACCUM_MODE>(old_cbid, new_cbid)));
    copy_tile_to_dst_init_short(new_cbid, transpose);
}

// clang-format off
/**
 * Copies a single tile from the specified input CB and writes the result to
 * DST at a specified index. The function will employ unpacker to first unpack into SRC
 * registers and then perform move into DST registers, at a specified index.
 * For the in_tile_index to be valid for this call, cb_wait_front(n) had to be
 * previously called to ensure that at least some number n>0 of tiles are available
 * in the input CB. The CB index 0 then references the first tile in the received section of the CB,
 * up to index n-1 (in a FIFO order). The DST register buffer must be in acquired state via
 * acquire_dst call. This call is blocking and is only available on the compute
 * engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                       | Data type | Valid range                                         | required |
 * |----------------|---------------------------------------------------|-----------|-----------------------------------------------------|----------|
 * | in_cb_id       | The identifier of the source circular buffer (CB) | uint32_t  | 0 to 31                                             | True     |
 * | in_tile_index  | The index of the tile to copy from the input CB   | uint32_t  | Must be less than the size of the CB                | True     |
 * | dst_tile_index | The index of the tile in the DST register         | uint32_t  | Must be less than the size of the DST register (16) | True     |
 * */
// clang-format on
ALWI void copy_tile(uint32_t in_cb_id, uint32_t in_tile_index, uint32_t dst_tile_index) {
    UNPACK((llk_unpack_A<BroadcastType::NONE, false, EltwiseBinaryReuseDestType::NONE, UnpackToDestEn>(
        in_cb_id, in_tile_index)));
    MATH((llk_math_eltwise_unary_datacopy<A2D, DST_ACCUM_MODE, BroadcastType::NONE, UnpackToDestEn>(
        dst_tile_index, in_cb_id)));
}

ALWI void copy_block_matmul_partials(
    uint32_t in_cb_id, uint32_t start_in_tile_index, uint32_t start_dst_tile_index, uint32_t ntiles) {
    UNPACK((llk_unpack_A_block<BroadcastType::NONE, false, EltwiseBinaryReuseDestType::NONE, UnpackToDestEn>(
        in_cb_id, start_in_tile_index, ntiles, false)));
    MATH((llk_math_eltwise_unary_datacopy_block<A2D, DST_ACCUM_MODE, BroadcastType::NONE, UnpackToDestEn>(
        start_dst_tile_index, ntiles, in_cb_id)));
}

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/tilize.h

```cpp
// SPDX-FileCopyrightText: © 2024 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common.h"
#ifdef TRISC_MATH
#include "llk_math_unary_datacopy_api.h"
#include "llk_math_reduce_api.h"
#include "llk_math_matmul_api.h"
#endif
#ifdef TRISC_UNPACK
#include "llk_unpack_tilize_api.h"
#endif

namespace ckernel {

// clang-format off
/**
 * Initializes the tilize operation. Should be called once at the beginning of a kernel.
 *
 * Return value: None
 *
 * | Param Type | Name   | Description                                   | Type     | Valid Range | Required |
 * |----------- |--------|-----------------------------------------------|----------|-------------|----------|
 * | Function   | icb    | Input circular buffer identifier              | uint32_t | 0 to 31     | True     |
 * | Function   | block  | Size of tile block to work on                 | uint32_t | > 0         | True     |
 * | Function   | ocb    | Output circular buffer identifier             | uint32_t | 0 to 31     | True     |
 */
// clang-format on
ALWI void tilize_init(uint32_t icb, uint32_t block, uint32_t ocb) {
    UNPACK((llk_unpack_tilize_init(icb, block)));
    MATH((llk_math_eltwise_unary_datacopy_init<
          A2D,
          DST_ACCUM_MODE,
          BroadcastType::NONE,
          false /*is_int_en*/,
          true /*tilize en*/>(false /*transpose of faces*/, false /*transpose within 16x16 face*/, icb)));
#ifdef ARCH_BLACKHOLE
    PACK((llk_pack_init<false /*untilize*/, false /*skip_inputs*/, true /*tilize en*/>(ocb)));
#endif
}

// clang-format off
/**
 * The same as tilize_init, but skips the packer configuration on blackhole in preparation to leave the
 * tilized result in DST without packing to an out CB
 *
 * Note: Should only be used with *_no_pack variants. Skips Low-Level API layer to enhance perf but limits use case.
 *
 * Return value: None
 *
 * | Param Type | Name   | Description                                   | Type     | Valid Range | Required |
 * |----------- |--------|-----------------------------------------------|----------|-------------|----------|
 * | Function   | icb    | Input circular buffer identifier              | uint32_t | 0 to 31     | True     |
 * | Function   | block  | Size of tile block to work on                 | uint32_t | > 0         | True     |
 */
// clang-format on
ALWI void tilize_init_no_pack(uint32_t icb, uint32_t block) {
    UNPACK((llk_unpack_tilize_init(icb, block)));
    MATH((llk_math_eltwise_unary_datacopy_init<
          A2D,
          DST_ACCUM_MODE,
          BroadcastType::NONE,
          false /*is_int_en*/,
          true /*tilize en*/>(false /*transpose of faces*/, false /*transpose within 16x16 face*/, icb)));
}

#if (defined(REDUCE_OP) and defined(REDUCE_DIM)) or defined(__DOXYGEN__)

// clang-format off
/**
 * Initializes the tilize operation with reduction. Should be called once at the beginning of a kernel.
 *
 * Return value: None
 *
 * | Param Type | Name           | Description                              | Type     | Valid Range | Required |
 * |------------|----------------|------------------------------------------|----------|-------------|----------|
 * | Template   | neginf_srcA    | NegInf source A flag                     | bool     | true/false  | False    |
 * | Template   | zero_srcA_reduce| Zero source A for reduce flag           | bool     | true/false  | False    |
 * | Function   | icb0           | Input circular buffer A identifier       | uint32_t | 0 to 31     | True     |
 * | Function   | icb1_scaler    | Input circular buffer for scaler         | uint32_t | 0 to 31     | True     |
 * | Function   | block          | Size of tile block to work on            | uint32_t | > 0         | True     |
 * | Function   | ocb            | Output circular buffer identifier        | uint32_t | 0 to 31     | True     |
 * | Function   | num_faces      | Number of faces per tile                 | uint32_t | 1 to 4      | False    |
 * | Function   | face_r_dim     | Number of rows in each face              | uint32_t | 1 to 16     | False    |
 */
// clang-format on
template <bool neginf_srcA = true, bool zero_srcA_reduce = false>
ALWI void tilizeA_B_reduce_init(
    uint32_t icb0,
    uint32_t icb1_scaler,
    uint32_t block,
    uint32_t ocb,
    uint32_t num_faces = 4,
    uint32_t face_r_dim = 16) {
    UNPACK((llk_unpack_tilizeA_B_hw_configure_disaggregated<DST_ACCUM_MODE>(icb0, icb1_scaler)));
    UNPACK((llk_unpack_tilizeA_B_init<neginf_srcA, true, false, zero_srcA_reduce>(
        icb0, icb1_scaler, block, num_faces, face_r_dim, 1)));

    MATH((llk_math_reduce_init<REDUCE_OP, REDUCE_DIM, DST_ACCUM_MODE, MATH_FIDELITY>()));
    MATH((llk_math_pack_sync_init<DST_ACCUM_MODE>()));
    MATH((llk_math_hw_configure_disaggregated(icb0, icb1_scaler)));

    PACK((llk_pack_hw_configure_disaggregated<DST_ACCUM_MODE, false>(ocb)));
    PACK((llk_pack_init(ocb)));
    PACK((llk_pack_dest_init<DST_ACCUM_MODE, false>(ocb)));
}
#endif

// clang-format off
/**
 * Re-initializes the tilize operation and reconfigures the unpacker with CB data type.
 *
 * Return value: None
 *
 * | Param Type | Name     | Description                              | Type     | Valid Range | Required |
 * |----------- |----------|------------------------------------------|----------|-------------|----------|
 * | Function   | old_icb  | Previous input circular buffer identifier| uint32_t | 0 to 31     | True     |
 * | Function   | new_icb  | New input circular buffer identifier     | uint32_t | 0 to 31     | True     |
 * | Function   | block    | Size of tile block to work on            | uint32_t | > 0         | True     |
 * | Function   | ocb      | Output circular buffer identifier        | uint32_t | 0 to 31     | True     |
 */
// clang-format on
ALWI void tilize_init_short_with_dt(uint32_t old_icb, uint32_t new_icb, uint32_t block, uint32_t ocb) {
    MATH((llk_math_eltwise_unary_datacopy_init<
          A2D,
          DST_ACCUM_MODE,
          BroadcastType::NONE,
          false /*is_int_en*/,
          true /*tilize en*/>(false /*transpose of faces*/, false /*transpose within 16x16 face*/, new_icb)));
    // This reconfig call checks if old operand has different data format to
    // new operand idx, otherwise no reconfig call occurs
    UNPACK((llk_unpack_reconfig_data_format_srca<DST_ACCUM_MODE>(old_icb, new_icb)));
    MATH((llk_math_reconfig_data_format_srca<DST_ACCUM_MODE>(old_icb, new_icb)));
    UNPACK((llk_unpack_tilize_init(new_icb, block)));

#ifdef ARCH_BLACKHOLE
    PACK((llk_pack_init<false, false, true /*tilize en*/>(ocb)));
#endif
}

// clang-format off
/**
 * The same as tilize_init_short_with_dt, but skips part of the packer configuration on blackhole in
 * preparation to leave the tilized result in DST without packing to an out CB
 *
 * Note: Should only be used with *_no_pack variants. Skips Low-Level API layer to enhance perf but limits use case.
 *
 * Return value: None
 *
 * | Param Type | Name     | Description                              | Type     | Valid Range | Required |
 * |----------- |----------|------------------------------------------|----------|-------------|----------|
 * | Function   | old_icb  | Previous input circular buffer identifier| uint32_t | 0 to 31     | True     |
 * | Function   | new_icb  | New input circular buffer identifier     | uint32_t | 0 to 31     | True     |
 * | Function   | block    | Size of tile block to work on            | uint32_t | > 0         | True     |
 */
// clang-format on
ALWI void tilize_init_short_with_dt_no_pack(uint32_t old_icb, uint32_t new_icb, uint32_t block) {
    MATH((llk_math_eltwise_unary_datacopy_init<
          A2D,
          DST_ACCUM_MODE,
          BroadcastType::NONE,
          false /*is_int_en*/,
          true /*tilize en*/>(false /*transpose of faces*/, false /*transpose within 16x16 face*/, new_icb)));
    // This reconfig call checks if old operand has different data format to
    // new operand idx, otherwise no reconfig call occurs
    UNPACK((llk_unpack_reconfig_data_format_srca<DST_ACCUM_MODE>(old_icb, new_icb)));
    MATH((llk_math_reconfig_data_format_srca<DST_ACCUM_MODE>(old_icb, new_icb)));
    UNPACK((llk_unpack_tilize_init(new_icb, block)));

// while the *_no_pack variants do not configure the packer, testing has shown that this call is
// still necessary to ensure the data type is properly updated
#ifdef ARCH_BLACKHOLE
    PACK((_llk_pack_init_<false, false, DstTileFaceLayout::RowMajor, false, true>(
        pack_dst_format[new_icb],
        get_output_face_r_dim(new_icb),
        get_output_tile_c_dim(new_icb),
        get_output_num_faces(new_icb),
        get_output_partial_face(new_icb),
        get_output_narrow_tile(new_icb))));
#endif
}

// clang-format off
/**
 * Performs the tilize operation on a block.
 *
 * Return value: None
 *
 * | Param Type | Name             | Description                              | Type     | Valid Range | Required |
 * |----------- |------------------|------------------------------------------|----------|-------------|----------|
 * | Function   | icb              | Input circular buffer identifier         | uint32_t | 0 to 31     | True     |
 * | Function   | block            | Size of tile block to work on            | uint32_t | > 0         | True     |
 * | Function   | ocb              | Output circular buffer identifier        | uint32_t | 0 to 31     | True     |
 * | Function   | input_tile_index | Index of the input tile in the icb       | uint32_t | >= 0        | False    |
 * | Function   | output_tile_index| Index of the output tile in the ocb      | uint32_t | >= 0        | False    |
 */
// clang-format on
ALWI void tilize_block(
    uint32_t icb, uint32_t block, uint32_t ocb, uint32_t input_tile_index = 0, uint32_t output_tile_index = 0) {
    UNPACK((llk_unpack_tilize_block(icb, block, input_tile_index)));

    for (uint32_t t = 0; t < block; t++) {
        // Acquire dst
        MATH((llk_math_wait_for_dest_available()));
        PACK((llk_packer_wait_for_math_done()));

        // Datacopy
        MATH((llk_math_eltwise_unary_datacopy<A2D, DST_ACCUM_MODE, BroadcastType::NONE, UnpackToDestEn>(
            0 /*dst index*/)));
        PACK((llk_pack<DST_ACCUM_MODE, true, false>(0 /*tile index*/, ocb, t + output_tile_index)));

        // Release dest
        MATH((llk_math_dest_section_done<DST_ACCUM_MODE>()));
        PACK((llk_pack_dest_section_done<DST_ACCUM_MODE>()));
    }
}

// clang-format off
/**
 * The same as tilize_block, but skips the packing step and MATH/PACK synchronization to leave the
 * tilized result in DST without packing to an out CB
 *
 * Note: Should only be used with *_no_pack variants. Skips Low-Level API layer to enhance perf but limits use case.
 *
 * Return value: None
 *
 * | Param Type | Name             | Description                              | Type     | Valid Range   | Required |
 * |----------- |------------------|------------------------------------------|----------|---------------|----------|
 * | Function   | icb              | Input circular buffer identifier         | uint32_t | 0 to 31       | True     |
 * | Function   | block            | Size of tile block to work on            | uint32_t | > 0           | True     |
 * | Function   | dst_idx          | Index of the tile in DST to write to     | uint32_t | 0 to DST size | True     |
 * | Function   | input_tile_index | Index of the input tile in the icb       | uint32_t | >= 0          | False    |
 */
// clang-format on
ALWI void tilize_block_no_pack(uint32_t icb, uint32_t block, uint32_t dst_idx, uint32_t input_tile_index = 0) {
    UNPACK((llk_unpack_tilize_block(icb, block, input_tile_index)));

    for (uint32_t t = 0; t < block; t++) {
        // Datacopy
        MATH((llk_math_eltwise_unary_datacopy<A2D, DST_ACCUM_MODE, BroadcastType::NONE, UnpackToDestEn>(
            dst_idx /*dst index*/)));
    }
}

// clang-format off
/**
 * Unpacks and tilizes a block from two input CBs.
 *
 * Return value: None
 *
 * | Param Type | Name             | Description                              | Type         | Valid Range | Required |
 * |------------|------------------|------------------------------------------|--------------|-------------|----------|
 * | Template   | neginf_srcA      | NegInf source A flag                     | bool         | true/false  | False    |
 * | Template   | reload_srcB      | Reload source B flag                     | std::uint32_t| true/false  | False    |
 * | Template   | zero_srcA        | Zero source A flag                       | bool         | true/false  | False    |
 * | Template   | zero_srcA_reduce | Zero source A for reduce flag            | bool         | true/false  | False    |
 * | Function   | icb0             | Input circular buffer A identifier       | uint32_t     | 0 to 31     | True     |
 * | Function   | icb1             | Input circular buffer B identifier       | uint32_t     | 0 to 31     | True     |
 * | Function   | block            | Size of tile block to work on            | uint32_t     | > 0         | True     |
 * | Function   | tile_idx_b       | Tile index for source B                  | uint32_t     | >= 0        | True     |
 * | Function   | num_faces        | Number of faces per tile                 | uint32_t     | 1 to 4      | False    |
 * | Function   | srca_face_r_dim  | Number of rows in each face (A)          | uint32_t     | 1 to 16     | False    |
 */
// clang-format on
template <
    bool neginf_srcA = true,
    std::uint32_t reload_srcB = true,
    bool zero_srcA = false,
    bool zero_srcA_reduce = false>
ALWI void unpack_tilizeA_B_block(
    uint32_t icb0,
    uint32_t icb1,
    uint32_t block,

    uint32_t tile_idx_b,
    uint32_t num_faces = 4,
    uint32_t srca_face_r_dim = 16) {
    UNPACK((llk_unpack_tilizeA_B_block<neginf_srcA, reload_srcB, zero_srcA, zero_srcA_reduce>(
        icb0, icb1, block, tile_idx_b, num_faces, srca_face_r_dim)));
}

// clang-format off
/**
 * Uninitializes the tilize operation before re-initializing for another operation.
 *
 * NOTE: This function is not in line with our programming model, and will be removed by the end of 2025
 * as a part of tt-metal#22904.
 *
 * Return value: None
 *
 * | Param Type | Name   | Description                              | Type     | Valid Range | Required |
 * |----------- |--------|------------------------------------------|----------|-------------|----------|
 * | Function   | icb    | Input circular buffer identifier         | uint32_t | 0 to 31     | True     |
 * | Function   | ocb    | Output circular buffer identifier        | uint32_t | 0 to 31     | True     |
 */
// clang-format on
ALWI void tilize_uninit(uint32_t icb, uint32_t ocb) {
    UNPACK((llk_unpack_tilize_uninit(icb)));
#ifdef ARCH_BLACKHOLE
    PACK((llk_pack_init<false /*untilize*/, false /*skip_inputs*/, false /*tilize en*/>(ocb)));
#endif
}

// clang-format off
/**
 * The same as tilize_uninit, but skips the packer configuration on blackhole in preparation to leave
 * the tilized result in DST without packing to an out CB
 *
 * Note: Should only be used with *_no_pack variants. Skips Low-Level API layer to enhance perf but limits use case.
 *
 * NOTE: This function is not in line with our programming model, and will be removed by the end of 2025
 * as a part of tt-metal#22904.
 *
 * Return value: None
 *
 * | Param Type | Name   | Description                              | Type     | Valid Range | Required |
 * |----------- |--------|------------------------------------------|----------|-------------|----------|
 * | Function   | icb    | Input circular buffer identifier         | uint32_t | 0 to 31     | True     |
 */
// clang-format on
ALWI void tilize_uninit_no_pack(uint32_t icb) { UNPACK((llk_unpack_tilize_uninit(icb))); }

// clang-format off
/**
 * Uninitializes the tilize operation and reconfigures the unpacker with CB data types.
 *
 * NOTE: This function is not in line with our programming model, and will be removed by the end of 2025
 * as a part of tt-metal#22904.
 *
 * Return value: None
 *
 * | Param Type | Name     | Description                              | Type     | Valid Range | Required |
 * |----------- |----------|------------------------------------------|----------|-------------|----------|
 * | Function   | old_icb  | Previous input circular buffer identifier| uint32_t | 0 to 31     | True     |
 * | Function   | new_icb  | New input circular buffer identifier     | uint32_t | 0 to 31     | True     |
 * | Function   | ocb      | Output circular buffer identifier        | uint32_t | 0 to 31     | True     |
 */
// clang-format on
ALWI void tilize_uninit_with_dt(uint32_t old_icb, uint32_t new_icb, uint32_t ocb) {
    UNPACK((llk_unpack_tilize_uninit(old_icb)));
    UNPACK((llk_unpack_reconfig_data_format_srca<DST_ACCUM_MODE>(old_icb, new_icb)));
    MATH((llk_math_reconfig_data_format_srca<DST_ACCUM_MODE>(old_icb, new_icb)));
#ifdef ARCH_BLACKHOLE
    PACK((llk_pack_init(ocb)));
#endif
}

// clang-format off
/**
 * The same as tilize_uninit_with_dt, but skips the packer configuration on blackhole in preparation to
 * leave the tilized result in DST without packing to an out CB
 *
 * Note: Should only be used with *_no_pack variants. Skips Low-Level API layer to enhance perf but limits use case.
 *
 * NOTE: This function is not in line with our programming model, and will be removed by the end of 2025
 * as a part of tt-metal#22904.
 *
 * Return value: None
 *
 * | Param Type | Name     | Description                              | Type     | Valid Range | Required |
 * |----------- |----------|------------------------------------------|----------|-------------|----------|
 * | Function   | old_icb  | Previous input circular buffer identifier| uint32_t | 0 to 31     | True     |
 * | Function   | new_icb  | New input circular buffer identifier     | uint32_t | 0 to 31     | True     |
 */
// clang-format on
ALWI void tilize_uninit_with_dt_no_pack(uint32_t old_icb, uint32_t new_icb) {
    UNPACK((llk_unpack_tilize_uninit(old_icb)));
    UNPACK((llk_unpack_reconfig_data_format_srca<DST_ACCUM_MODE>(old_icb, new_icb)));
    MATH((llk_math_reconfig_data_format_srca<DST_ACCUM_MODE>(old_icb, new_icb)));
}

ALWI void fast_tilize_init(uint32_t icb, uint32_t full_dim, uint32_t ocb) {
#ifdef ARCH_BLACKHOLE
    // Blackhole fallback
    tilize_init(icb, full_dim, ocb);
#else
    UNPACK((llk_unpack_fast_tilize_init(icb, full_dim)));
    MATH((llk_math_fast_tilize_init(icb, full_dim == 1 ? 1 : 2)));
    PACK((llk_pack_fast_tilize_init(icb, ocb, full_dim == 1 ? 1 : 2)));
#endif
}

ALWI void fast_tilize_init_with_dt(uint32_t icb, uint32_t full_dim, uint32_t ocb) {
    UNPACK((llk_unpack_reconfig_data_format<DST_ACCUM_MODE>(icb, icb)));
    MATH((llk_math_reconfig_data_format<true, true>(icb, icb)));

    fast_tilize_init(icb, full_dim, ocb);
}

ALWI void fast_tilize_uninit(uint32_t icb, uint32_t ocb) {
#ifdef ARCH_BLACKHOLE
    // Blackhole fallback
    tilize_uninit(icb, ocb);
#else
    UNPACK((llk_unpack_fast_tilize_uninit<DST_ACCUM_MODE>()));
    MATH((llk_math_fast_tilize_uninit<DST_ACCUM_MODE>(icb)));
    PACK((llk_pack_fast_tilize_uninit<DST_ACCUM_MODE>(ocb)));
#endif
}

ALWI void fast_tilize_block(
    uint32_t icb, uint32_t block, uint32_t ocb, uint32_t input_tile_index = 0, uint32_t output_tile_index = 0) {
#ifdef ARCH_BLACKHOLE
    // Blackhole fallback
    tilize_block(icb, block, ocb, input_tile_index, output_tile_index);
#else
    uint32_t full_dim = block;

    // Not sure if input_tile_index can be arbitrary but it works for moving across rows of files,
    // i.e. input_tile_index % full_dim == 0
    input_tile_index = input_tile_index % full_dim + (input_tile_index / full_dim) * full_dim * TILE_R_DIM;

    uint32_t packed_tiles = 0;
    uint32_t remaining_tiles = block;
    uint32_t dest_size = DST_ACCUM_MODE ? 4 : 8;
    uint32_t unit_dim = full_dim == 1 ? 1 : 2;
    uint32_t num_units = dest_size / unit_dim;

    while (packed_tiles < block) {
        uint32_t read_tile_index = input_tile_index + packed_tiles;
        uint32_t write_tile_index = output_tile_index + packed_tiles;

        MATH((llk_math_wait_for_dest_available()));
        PACK((llk_packer_wait_for_math_done()));

        if (remaining_tiles > 2 * dest_size) {
            // Three or more dests
            UNPACK((llk_unpack_fast_tilize_block(icb, read_tile_index, unit_dim, num_units, full_dim)));
            MATH((llk_math_fast_tilize_block_(0, icb, unit_dim, num_units)));
            PACK((llk_pack_fast_tilize_block(0, ocb, write_tile_index, unit_dim, num_units)));
            packed_tiles += dest_size;
            remaining_tiles -= dest_size;
        } else if (remaining_tiles > dest_size) {
            // Two dests
            uint32_t even_remainder = remaining_tiles / 2 + ((remaining_tiles / 2) % 2);
            num_units = even_remainder / unit_dim;
            UNPACK((llk_unpack_fast_tilize_block(icb, read_tile_index, unit_dim, num_units, full_dim)));
            MATH((llk_math_fast_tilize_block_(0, icb, unit_dim, num_units)));
            PACK((llk_pack_fast_tilize_block(0, ocb, write_tile_index, unit_dim, num_units)));
            packed_tiles += even_remainder;
            remaining_tiles -= even_remainder;
        } else {
            // Last dest
            if (remaining_tiles % 2 == 0 || unit_dim == 1) {
                // Single sequence
                num_units = remaining_tiles / unit_dim;
                UNPACK((llk_unpack_fast_tilize_block(icb, read_tile_index, unit_dim, num_units, full_dim)));
                MATH((llk_math_fast_tilize_block_(0, icb, unit_dim, num_units)));
                PACK((llk_pack_fast_tilize_block(0, ocb, write_tile_index, unit_dim, num_units)));
            } else if (remaining_tiles == 3) {
                // only odd pack
                UNPACK((llk_unpack_fast_tilize_block(icb, read_tile_index, 3, 1, full_dim)));
                MATH((llk_math_fast_tilize_block_(0, icb, 3, 1)));
                PACK((llk_pack_fast_tilize_block(0, ocb, write_tile_index, 3, 1)));
            } else {
                // even packs plus odd pack
                num_units = (remaining_tiles - 3) / unit_dim;
                UNPACK((llk_unpack_fast_tilize_block(icb, read_tile_index, unit_dim, num_units, full_dim)));
                MATH((llk_math_fast_tilize_block_(0, icb, unit_dim, num_units)));
                PACK((llk_pack_fast_tilize_block(0, ocb, write_tile_index, unit_dim, num_units)));

                UNPACK((llk_unpack_fast_tilize_block(icb, read_tile_index + remaining_tiles - 3, 3, 1, full_dim)));
                MATH((llk_math_fast_tilize_block_(remaining_tiles - 3, icb, 3, 1)));
                PACK((llk_pack_fast_tilize_block(
                    remaining_tiles - 3, ocb, write_tile_index + remaining_tiles - 3, 3, 1)));
            }
            packed_tiles += remaining_tiles;
            remaining_tiles = 0;
        }

        MATH((llk_math_dest_section_done<DST_ACCUM_MODE>()));
        PACK((llk_pack_dest_section_done<DST_ACCUM_MODE>()));
    }
#endif
}

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/transpose_wh.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent AI ULC
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common.h"
#ifdef TRISC_MATH
#include "llk_math_common_api.h"
#include "llk_math_unary_datacopy_api.h"
#include "llk_math_transpose_dest_api.h"
#endif
#ifdef TRISC_UNPACK
#include "llk_unpack_common_api.h"
#include "llk_unpack_A_api.h"
#endif

namespace ckernel {

// clang-format off
/**
 * Paired Init function for transpose_wh. For general information on init functions refer to any_init.
 *
 * | Argument       | Description                                                 | Type     | Valid Range | Required |
 * |----------------|-------------------------------------------------------------|----------|-------------|----------|
 * | icb            | The identifier of the circular buffer (CB) containing input | uint32_t | 0 to 31     | True     |
 */
 // clang-format on
ALWI void transpose_wh_init(uint32_t icb, uint32_t ocb) {

#if defined(TRISC_MATH) || defined(TRISC_UNPACK)
    const std::uint32_t src_format = get_operand_src_format(icb);
    const bool is_int32 = (src_format & 0xf) == (std::uint32_t)DataFormat::Int32;

    if (is_int32) {
        UNPACK((llk_unpack_A_hw_configure_disaggregated<DST_ACCUM_MODE, StochRndType::None, true>(icb, false)));
        UNPACK((llk_unpack_A_init<BroadcastType::NONE, false, EltwiseBinaryReuseDestType::NONE, UnpackToDestEn>(
            true, false, icb)));
        MATH((llk_math_eltwise_unary_datacopy_init<A2D, DST_ACCUM_MODE, BroadcastType::NONE>(true, false, icb)));
        MATH((llk_math_transpose_dest_init<false, true>()));
    } else {
        UNPACK((llk_unpack_A_hw_configure_disaggregated<DST_ACCUM_MODE, StochRndType::None, false>(icb, true)));
        UNPACK((llk_unpack_A_init<BroadcastType::NONE, true, EltwiseBinaryReuseDestType::NONE>(true, true, icb)));
        MATH((llk_math_eltwise_unary_datacopy_init<A2D, DST_ACCUM_MODE, BroadcastType::NONE>(true, true, icb)));
    }
    MATH((llk_math_pack_sync_init<DST_ACCUM_MODE>()));
    MATH((llk_math_hw_configure_disaggregated(icb, icb)));
#endif

    PACK((llk_pack_hw_configure_disaggregated<DST_ACCUM_MODE, false>(ocb)));
    PACK((llk_pack_init(ocb)));
    PACK((llk_pack_dest_init<DST_ACCUM_MODE, false>()));
}

/**
 * Performs a first-call or switch-from-another-op tile hw reconfiguration step needed for transpose_wh to be executed
 * correctly.
 */
ALWI void transpose_wh_init_short(uint32_t icb) {
#if defined(TRISC_MATH) || defined(TRISC_UNPACK)
    const std::uint32_t src_format = get_operand_src_format(icb);
    const bool is_int32 = (src_format & 0xf) == (std::uint32_t)DataFormat::Int32;

    if (is_int32) {
        UNPACK((llk_unpack_A_init<BroadcastType::NONE, false, EltwiseBinaryReuseDestType::NONE, UnpackToDestEn>(
            true, false, icb)));
        MATH((llk_math_eltwise_unary_datacopy_init<A2D, DST_ACCUM_MODE, BroadcastType::NONE>(true, false, icb)));
        MATH((llk_math_transpose_dest_init<false, true>()));
    } else {
        UNPACK((llk_unpack_A_init<BroadcastType::NONE, true, EltwiseBinaryReuseDestType::NONE>(true, true, icb)));
        MATH((llk_math_eltwise_unary_datacopy_init<A2D, DST_ACCUM_MODE, BroadcastType::NONE>(true, true, icb)));
    }

#endif
}

// clang-format off
/**
 * Performs a 32x32 transpose operation *B[w,h] = A[h,w]* on a tile in the CB
 * at a given index and writes the result to the DST register at index
 * dst_tile_index. The DST register buffer must be in acquired state via
 * *acquire_dst* call.
 *
 * This call is blocking and is only available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                             | Type     | Valid Range                                    | Required |
 * |----------------|---------------------------------------------------------|----------|------------------------------------------------|----------|
 * | in_cb_id       | The identifier of the circular buffer (CB) containing A | uint32_t | 0 to 31                                        | True     |
 * | in_tile_index  | The index of tile A within the first CB                 | uint32_t | Must be less than the size of the CB           | True     |
 * | dst_tile_index | The index of the tile in DST REG for the result B       | uint32_t | Must be less than the acquired size of DST REG | True     |
 */
 // clang-format on
ALWI void transpose_wh_tile(uint32_t icb, uint32_t itile, uint32_t idst) {
#if defined(TRISC_MATH) || defined(TRISC_UNPACK)
    const std::uint32_t src_format = get_operand_src_format(icb);
    const bool is_int32 = (src_format & 0xf) == (std::uint32_t)DataFormat::Int32;

    if (is_int32) {
        UNPACK((llk_unpack_A<BroadcastType::NONE, false, EltwiseBinaryReuseDestType::NONE, UnpackToDestEn>(icb, itile, true)));
        UNPACK((llk_unpack_set_srcb_dummy_valid()));
        MATH((llk_math_eltwise_unary_datacopy<A2D, DST_ACCUM_MODE, BroadcastType::NONE, UnpackToDestEn>(idst, icb)));
        MATH((llk_math_transpose_dest<false, true>(idst)));
    } else {
        UNPACK((llk_unpack_A<BroadcastType::NONE, false>(icb, itile, true)));
        MATH((llk_math_eltwise_unary_datacopy<A2D, DST_ACCUM_MODE, BroadcastType::NONE>(idst, icb)));
    }
#endif
}

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/transpose_wh_dest.h

```cpp
// SPDX-FileCopyrightText: © 2024 Tenstorrent AI ULC
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common.h"
#ifdef TRISC_MATH
#include "llk_math_unary_datacopy_api.h"
#include "llk_math_transpose_dest_api.h"
#endif
#ifdef TRISC_UNPACK
#include "llk_unpack_A_api.h"
#endif

namespace ckernel {

/**
 * Performs a first-call or switch-from-another-op tile hw reconfiguration step needed for transpose_wh_dest to be
 * executed correctly.
 */
template <bool is_32bit = false>
ALWI void transpose_wh_dest_init_short() {
    MATH((llk_math_transpose_dest_init<true, is_32bit>()));
}

// clang-format off
/**
 * Performs a 32x32 in place transpose operation *B[w,h] = A[h,w]* on a tile in the DST register at idst.
 * The DST register buffer must be in acquired state via *acquire_dst* call.
 * This call is blocking and is only available on the compute engine.
 *
 * Return value: None
 *
 * | Argument       | Description                                             | Type     | Valid Range                                    | Required |
 * |----------------|---------------------------------------------------------|----------|------------------------------------------------|----------|
 * | idst           | The index of the tile in DST REG to transpose           | uint32_t | Must be less than the acquired size of DST REG | True     |
 */
 // clang-format on
template <bool is_32bit = false>
ALWI void transpose_wh_dest(uint32_t idst) {
    UNPACK((llk_unpack_set_srcb_dummy_valid()));
    MATH((llk_math_transpose_dest<true, is_32bit>(idst)));
}

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/untilize.h

```cpp
// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common.h"
#ifdef TRISC_MATH
#include "llk_math_unary_datacopy_api.h"
#endif
#ifdef TRISC_UNPACK
#include "llk_unpack_untilize_api.h"
#endif

namespace ckernel {

// clang-format off
/**
 * Initializes the hardware and internal state for the untilize operation. This function should be called before
 * performing any untilize operations in the compute kernel. The circular buffer (CB) ID provided must correspond
 * to the buffer containing the input data to be untilized. If the data format or properties of the input operand
 * differ from those previously configured, ensure that the appropriate reconfiguration functions are called before
 * this initialization.
 *
 * Return value: None
 *
 * | Param Type | Name | Description                                               | Type     | Valid Range | Required |
 * |------------|------|-----------------------------------------------------------|----------|-------------|----------|
 * | Function   | icb  | The identifier of the circular buffer (CB) for input data | uint32_t | 0 to 31     | True     |
 */
// clang-format on
ALWI void untilize_init(uint32_t icb) {
    MATH((llk_math_eltwise_unary_datacopy_init<A2D, DST_ACCUM_MODE, BroadcastType::NONE>(
        false /*transpose of faces*/, false /*transpose within 16x16 face*/, icb)));
    UNPACK((llk_unpack_untilize_init(icb)));
}

// clang-format off
/**
 * Copies a block of tiles from the DEST register buffer to the specified circular buffer (CB) for the untilize
 * operation. This function is used to transfer multiple tiles at once, with the number of tiles determined by the
 * template parameter `block_ct_dim`. The DEST register buffer must be in the acquired state before calling this function. The CB
 * ID provided must correspond to the buffer where the untilized data will be stored. Note that the maximum size
 * of the block is limited by the size of the DEST and synchronization mode used. These are maximum sizes:
 * - half-sync mode (16-bit mode): 8 tiles
 * - half-sync mode (32-bit mode): 4 tiles
 * - full-sync mode (16-bit mode): 16 tiles
 * - full-sync mode (32-bit mode): 8 tiles
 *
 * Return value: None
 *
 * | Param Type | Name         | Description                                          | Type     | Valid Range               | Required |
 * |------------|--------------|------------------------------------------------------|----------|---------------------------|----------|
 * | Template   | block_ct_dim | The number of tiles stored in DEST at one moment     | uint32_t | 1 to max (see comment)    | False    |
 * | Function   | icb          | The identifier of the circular buffer (CB) for input | uint32_t | 0 to 31                   | True     |
 * | Function   | full_ct_dim  | Width of a full input in tiles                       | uint32_t | Divisible by block_ct_dim | True     |
 * | Function   | ocb          | The identifier of the circular buffer (CB) for output| uint32_t | 0 to 31                   | True     |
 */
// clang-format on
template <uint32_t block_ct_dim = 1>
ALWI void untilize_block(uint32_t icb, uint32_t full_ct_dim, uint32_t ocb) {
    UNPACK((llk_unpack_untilize(icb, full_ct_dim)));

    for (uint32_t t = 0; t < full_ct_dim / block_ct_dim; t++) {
        MATH((llk_math_wait_for_dest_available()));

        // Datacopy
        for (uint32_t reg_id = 0; reg_id < block_ct_dim; reg_id++) {
            MATH((llk_math_eltwise_unary_datacopy<A2D, DST_ACCUM_MODE, BroadcastType::NONE>(reg_id)));
        }

        MATH((llk_math_dest_section_done<DST_ACCUM_MODE>()));

        PACK((llk_packer_wait_for_math_done()));

        // Datacopy
        for (uint32_t reg_id = 0; reg_id < block_ct_dim; reg_id++) {
            PACK((llk_pack<DST_ACCUM_MODE, false, false>(reg_id, ocb)));
        }

        // Release dest
        PACK((llk_pack_dest_section_done<DST_ACCUM_MODE>()));
    }
}

// clang-format off
/**
 * Restores hardware and internal state after the untilize operation is complete. This function should be called after
 * untilize_block operation is finished. The circular buffer (CB) ID provided must correspond to the buffer that was
 * used for the untilize operation and it's initialization.
 *
 * NOTE: This function is not in line with our programming model, and will be removed by the end of 2025
 * as a part of tt-metal#22904.
 *
 * Return value: None
 *
 * | Param Type | Name | Description                                               | Type     | Valid Range | Required |
 * |------------|------|-----------------------------------------------------------|----------|-------------|----------|
 * | Function   | icb  | The identifier of the circular buffer (CB) for input data | uint32_t | 0 to 31     | True     |
 */
// clang-format on
ALWI void untilize_uninit(uint32_t icb) { UNPACK((llk_unpack_untilize_uninit(icb))); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/welford.h

```cpp
// SPDX-FileCopyrightText: © 2025 Tenstorrent AI ULC
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_welfords_sfpu_entry.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {
/**
 * @brief Performs a Welford's online algorithm update for mean and m2 on a tile in the DST register.
 *
 * This operation computes the running mean and m2 for a stream of data, enabling numerically stable
 * calculation of statistics in a single pass. The DST register buffer must be in acquired state via @ref
 * tile_regs_acquire call. This call is blocking and is only available on the compute engine.
 *
 * @tparam input_dst_index   The index of the tile in DST register buffer containing the new input.
 *                           Must be less than the size of the DST register.
 * @tparam mean_dst_index    The index of the tile in DST register buffer containing the current running mean.
 *                           Must be less than the size of the DST register.
 *                           This tile can be left uninitialized when current_row is 0.
 * @tparam m2_dst_index     M2 is the short hand name for the sum of squares
 *                          The index of the tile in DST register buffer containing the running m2.
 *                           Must be less than the size of the DST register.
 *                           This tile can be left uninitialized when current_row is 0.
 * @tparam reformat_dst_to_col_on_end      True: if final_row-current_row <= 32 then LLK converts dst reg at tile offset
 * 1 and dst reg at tile offset 2 to column vectors
 *
 * @tparam convert_M2_to_var_on_end      True: if final_row-current_row <= 32 then LLK converts M2 (dst reg at tile
 * offset 2) to variance
 *
 * @param current_row     The current row index (starting from 0). Should follow 0 <= current_row <= 32 and current_row
 * <= final_row. When current_row is 0, the previous mean and m2 are ignored.
 * @param final_row       The final row index. This index is not included in the update. Should follow current_row <=
 * final_row.A2D This dictates the total number of rows to update, starting from current_row.
 * @param num_skip_rows   Number of initial rows to skip in the update. Must be >= 0. Default is 0.
 *                        Setting this to a value greater than 0 skips the first num_skip_rows rows of the update.
 *                        Should follow 0 <= num_skip_rows <= 32.
 * @param reciprocal_lut_ptr       The reciprocal lookup table pointer for optimized speed
 *
 * @note All 32 rows of the input tile are processed by this function.
 *
 * @return None. Mean and m2 tiles are updated in place.
 */

template <
    uint32_t input_dst_index,
    uint32_t mean_dst_index,
    uint32_t m2_dst_index,
    bool reformat_dst_to_col_on_end,
    bool convert_M2_to_var_on_end>
ALWI void welford_tile(uint32_t current_row, uint32_t final_row, uint32_t num_skip_rows, uint32_t reciprocal_lut_ptr) {
    MATH((llk_math_welfords_sfpu<
          input_dst_index,
          mean_dst_index,
          m2_dst_index,
          reformat_dst_to_col_on_end,
          convert_M2_to_var_on_end>(current_row, final_row, num_skip_rows, reciprocal_lut_ptr)));
}

// /**
//  * @brief Pack the final mean and m2 tiles generated by Welford's algorithm into the DST register as mean and
//  variance.
//  *
//  * This function should be called after all the rows of the input tile have been processed.
//  * The DST register buffer must be in acquired state via @ref tile_regs_acquire call.
//  * This call is blocking and is only available on the compute engine.
//  * This function converts m2 to variance and packs both mean and variance into the DST register.
//  *
//  * @param scale_factor The 1/scale factor is multiplied to the M2 value in dst reg at tile offset 2 to convert it to
//  var and then stored in dst reg at tile offset 2.
//  *
//  * @return None. Mean and variance tiles are updated in place. 32 values each are written to the DST register.
//  *         All 32 values are written to the first face of the DST register. Each valid value is followed by an
//  invalid
//  * value.
//  */
ALWI void welford_M2_to_var(uint32_t scale_factor) {
    welford_tile<0, 1, 2, false, true>(scale_factor, scale_factor, 0, 0, 0);
}

/**
 * Uses a copy of the ternery_sfpu_init
 * Programs the replay for fast LLK. Needed otherwise LLK wont work
 */
ALWI void welford_init() { MATH((llk_math_welfords_sfpu_init())); }

}  // namespace ckernel
```

## tt_metal/include/compute_kernel_api/xlogy.h

```cpp
// SPDX-FileCopyrightText: © 2025 Tenstorrent Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "compute_kernel_api/common_globals.h"
#ifdef TRISC_MATH
#include "llk_math_eltwise_binary_sfpu_xlogy.h"
#define MAIN math_main()
#define MATH(x) x
#else
#define MATH(x)
#endif

namespace ckernel {

// clang-format off
/**
 * Performs element-wise xlogy operation y = xlogy(x0, x1) with x0 as first operand and x1 as second operand.
 * Output overwrites first operand in DST.
 * The DST register buffer must be in acquired state via *acquire_dst* call. This call is blocking and is only available on the
 * compute engine.
 *
 * Return value: None
 *
 * | Argument              | Description                                                           | Type     | Valid Range                                           | Required |
 * |-----------------------|-----------------------------------------------------------------------|----------|-------------------------------------------------------|----------|
 * | idst0                 | The index of the tile in DST register buffer to use as first operand  | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | idst1                 | The index of the tile in DST register buffer to use as second operand | uint32_t | Must be less than the size of the DST register buffer | True     |
 * | odst                  | The index of the tile in DST register buffer to use as output         | uint32_t | Must be less than the size of the DST register buffer | True     |
 */
// clang-format on
ALWI void xlogy_binary_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((llk_math_eltwise_binary_sfpu_xlogy<APPROX>(idst0, idst1, odst)));
}

/**
 * Please refer to documentation for any_init.
 */
ALWI void xlogy_binary_tile_init() { MATH((llk_math_eltwise_binary_sfpu_xlogy_init<APPROX>())); }

}  // namespace ckernel
```
