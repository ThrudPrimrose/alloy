# Design
The stock log_tile (ckernel_sfpu_log.h, blackhole) is a 3rd-order polynomial (error ~1e-3 absolute), too coarse for 1e-5 + 1e-3|ref| near x=1. So compute.cpp carries its own SFPI log: split x = 2^e * m, fold m into [sqrt(.5), sqrt2) (e+1 if m>=1.41421), s=(m-1)/(m+1) with the library reciprocal (2 Newton steps), ln m = 2s(1 + s^2/3 + s^4/5 + s^6/7 + s^8/9) (truncation error ~1e-9), result = e*ln2 + ln m. Exponent handling copies the stock kernel (sign-magnitude trick before int32_to_float). e = 0 on both sides of x=1, so no cancellation there. Inputs are positive; no 0/negative handling.
One tile at a time: reader -> CB0 -> compute (fp32 dest, unpack_to_dest_fp32 on CB0) -> CB16 -> writer. Single core, no extra CBs.

# Unsure API spellings
- Defining a custom SFPU function under #ifdef TRISC_MATH in namespace ckernel::sfpu and passing it to `_llk_math_eltwise_unary_sfpu_params_<false>(fn, dst_idx, (int)VectorMode::RC)` (guessed from llk_math_eltwise_unary_sfpu_log.h; the stock call passes extra args).
- `llk_math_eltwise_unary_sfpu_init<SfpuType::log, false>(fn)` for my init; I reuse SfpuType::log.
- `#include "ckernel_sfpu_recip.h"` and `sfpu_reciprocal<false>` / `recip_init<false>()` (the _init_reciprocal_ template args may differ in this tt-llk commit).
- `setexp(m, 126)`, `exexp`, `setsgn`, `int32_to_float(ex, 0)`, `v_if(m >= 1.41421356f)` copied or extrapolated from the stock log kernel.
- No copy_tile_to_dst_init_short call: I follow the sfpu_eltwise_chain example (init_sfpu then copy_tile). With unpack_to_dest_fp32 a *_with_dt variant may be needed.
- `get_arg_val` in compute: spec says runtime args; if compute needs `get_arg_val<uint32_t>(0)` via different header, adjust.
- TensorAccessorArgs<0>() for reader and writer (single accessor, offset 0).
