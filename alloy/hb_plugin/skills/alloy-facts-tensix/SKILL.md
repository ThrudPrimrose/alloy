---
name: alloy-facts-tensix
description: "Alloy's checked facts for Tenstorrent Tensix (Blackhole): every compute-kernel tile call with its includes, init and call per tt-metal version, the platform each verdict ran on and its measured error, and the SFPU math kernels (SFPI) measured on a Blackhole card, with their code."
when: before writing a Tensix compute, reader or writer kernel, and before calling a tile operation or a math function on Tensix.
---

# Tenstorrent Tensix (Blackhole p150): Alloy's checked facts

Every row is a compute-kernel call on a 32x32 tile in DST. Each row lists its includes and its init and call per tt-metal version ([v06]: tt-metal 0.6x, [v08]: tt-metal 0.8x), the platform each verdict ran on with the measured error, and its note. An SFPU math kernel is a function written on SFPU lanes (SFPI) with its error measured on a Blackhole card.

## Target

Tenstorrent Tensix (Blackhole p150): tile calls, not intrinsics; dtypes f32, bf16.

```text
  note: No f64 on Tensix. A unary op copies the tile to DST (copy_tile) and runs <op>_tile_init(); <op>_tile(dst) on the SFPU. A binary op either runs <op>_tiles(cb_a, cb_b, i, j, dst) on the FPU, whose SrcA/SrcB registers hold TF32 (about 1e-3 relative on f32), or copies both tiles to DST and runs <op>_binary_tile(d0, d1, dst) on the SFPU, which keeps f32. Full f32 also needs fp32_dest_acc_en, and UnpackToDestFp32 for tiles copied to DST; without them f32 passes DST at bf16 precision (2^-9). Kernel scaffolding differs by version: 0.6x has namespace NAMESPACE { void MAIN }, init_sfpu and binary_op_init_common; 0.8x has kernel_main(), compute_kernel_hw_startup and copy_init.
```

## exp

```text
tensix/f32,bf16/exp: v[j] = exp(x[j]), applied to a 32x32 tile
  SFPU (unary): header eltwise_unary/exp.h
    includes [v06] compute: #include "compute_kernel_api/common.h" #include "compute_kernel_api/tile_move_copy.h" #include "compute_kernel_api/eltwise_unary/eltwise_unary.h" #include "compute_kernel_api/eltwise_binary.h" #include "compute_kernel_api/eltwise_unary/exp.h"; reader/writer: #include "dataflow_api.h"
    includes [v08] compute: #include "api/compute/common.h" #include "api/compute/tile_move_copy.h" #include "api/compute/eltwise_unary/eltwise_unary.h" #include "api/compute/eltwise_binary.h" #include "api/compute/eltwise_unary/exp.h"; reader/writer: #include "api/dataflow/dataflow_api.h"
    init: exp_tile_init()
    call: exp_tile(0)
    f32: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x: max rel error 6.5e-08
    bf16: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x: max rel error 0.0056
    f32: measured on a Blackhole card with tt-metal 0.63, the [v06] spelling, x in [-7, 7]: max rel error 0.00173, max abs error 1.77 (within the row's bound 0.01 rel; probe_exp-card, agents 8ec7b7d)
    note: On the Blackhole with tt-metal 0.63, exp_tile is accurate to bf16 only: max relative error 1.73e-3 over [-7, 7] in every sub-range, with fp32_dest_acc_en, UnpackToDestFp32 and HiFi4 (card probe of 2026-11-18). A log refined by Newton or Halley steps through it stops at an absolute error of 1.7e-3. The SFPI rung alloy_exp_f32_sfpi (rungs.exp below) holds f32 on the card. exp2_tile does not help on 0.63: mul_unary_tile(0, 0x3FB8AA3B) (x log2 e) then exp2_tile gave output identical to exp_tile on the card, rel 1.73e-3 (commit dd226b3), although the v0.63.0 tag's Blackhole ckernel_sfpu_exp2.h holds Moroz exp_21f: the container's exp2 goes through exp.
  SFPU math kernel alloy_exp_f32_sfpi: 1.66 ulp, measured on the card (tt-metal 0.63, Blackhole p150, 2026-11-18, alloy-tenstorrent agents commit 5cc4565: max rel error 9.87e-08, max abs error 7.10e-05 over x uniform in [-7, 7], worst x -6.99997)
    init: MATH((llk_math_eltwise_unary_sfpu_init<SfpuType::unused, APPROX>()))
    call: MATH((_llk_math_eltwise_unary_sfpu_params_<APPROX>(alloy_exp_f32_face, 0, (int)VectorMode::RC)))
    note: dev: built after the pilot's failures, when exp_tile on 0.63 held bf16 only (rel 1.73e-3: the metal layer runs Moroz exp_21f, as exp2_tile does). n = round(x / ln2) by the 1.5 * 2^23 shifter, r = x - n ln2 with the ln2 hi/lo split of the log rung, Taylor degree 7 on |r| <= ln2 / 2, and 2^n added to the result's exponent by setexp. On the card probe it took 1.5 ms. Checked on [-7, 7] only; no clamp, so |x| above about 87 overflows the exponent field instead of giving inf or 0. Same includes and compute config as the log rung.
    code:
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
```

## log

```text
tensix/f32,bf16/log: log, applied to a 32x32 tile
  SFPU (unary): header compute_kernel_api.h
    includes [v06] compute: #include "compute_kernel_api/common.h" #include "compute_kernel_api/tile_move_copy.h" #include "compute_kernel_api/eltwise_unary/eltwise_unary.h" #include "compute_kernel_api/eltwise_binary.h" #include "compute_kernel_api.h"; reader/writer: #include "dataflow_api.h"
    includes [v08] compute: #include "api/compute/common.h" #include "api/compute/tile_move_copy.h" #include "api/compute/eltwise_unary/eltwise_unary.h" #include "api/compute/eltwise_binary.h" #include "api/compute/compute_kernel_api.h"; reader/writer: #include "api/dataflow/dataflow_api.h"
    init: log_tile_init<false>() [v06], log_tile_init() [v08]
    call: log_tile<false>(0) [v06], log_tile(0) [v08]
    f32: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x, the [v08] spelling only: max rel error 7.1e-08
    bf16: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x, the [v08] spelling only: max rel error 0.004
    f32: measured on a Blackhole card with tt-metal 0.63, the [v06] spelling, x in [0.001, 1000]: max rel error 3.35e+04, max abs error 0.0165 (OUTSIDE the row's bound 0.01 rel; probe_log-false, agents 8ec7b7d)
    note: tt-metal 0.6x log is a low-order approximation: on a Blackhole with tt-metal 0.63 its absolute error is 0.012 to 0.0165 over [1e-3, 1e3], so its relative error passes 1 near x = 1; both template arguments give the same output (card probes of 2026-11-16 and 2026-11-18). On 0.63 a log accurate to f32 must be built from the f32-accurate SFPU binary rows (div_binary_tile: max relative error 2.4e-7 on the card) with its own range reduction; the SFPI rung alloy_log_f32_sfpi (rungs.log below) does so on SFPU lanes and holds f32 on the card. 0.8x holds the table's bound on ttsim.
  SFPU math kernel alloy_log_f32_sfpi: 3.79 ulp, measured on the card (tt-metal 0.63, Blackhole p150, 2026-11-18, alloy-tenstorrent agents commit 7d69842: max abs error 3.05e-07, max rel error 2.26e-07 over x log-uniform in [1e-3, 1e3], worst x 0.99999958)
    init: MATH((llk_math_eltwise_unary_sfpu_init<SfpuType::unused, APPROX>()))
    call: MATH((_llk_math_eltwise_unary_sfpu_params_<APPROX>(alloy_log_f32_face, 0, (int)VectorMode::RC)))
    note: dev: built after the pilot's failures, when log_tile on 0.63 missed f32 by 0.0165. Alloy's CPU rung alloy_log_f32_fast on SFPU lanes, with one change: exexp and setexp split the exponent and mantissa (no integer add and shift of the bit pattern), and the division f / (2 + f) is approx_recip plus two Newton steps. The polynomial and the ln2 hi/lo split are the CPU rung's. On the card probe it took 1.8 ms where log_tile took 0.7 ms. The compute kernel includes compute_kernel_api.h, which under TRISC_MATH declares sfpi, SfpuType, VectorMode and the llk SFPU helpers; keep fp32_dest_acc_en and UnpackToDestFp32, or DST holds bf16. Contract: finite x; 0 gives -inf, negative x NaN.
    code:
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
```

## sqrt

```text
tensix/f32,bf16/sqrt: v[j] = sqrt(x[j]), applied to a 32x32 tile
  SFPU (unary): header eltwise_unary/sqrt.h
    includes [v06] compute: #include "compute_kernel_api/common.h" #include "compute_kernel_api/tile_move_copy.h" #include "compute_kernel_api/eltwise_unary/eltwise_unary.h" #include "compute_kernel_api/eltwise_binary.h" #include "compute_kernel_api/eltwise_unary/sqrt.h"; reader/writer: #include "dataflow_api.h"
    includes [v08] compute: #include "api/compute/common.h" #include "api/compute/tile_move_copy.h" #include "api/compute/eltwise_unary/eltwise_unary.h" #include "api/compute/eltwise_binary.h" #include "api/compute/eltwise_unary/sqrt.h"; reader/writer: #include "api/dataflow/dataflow_api.h"
    init: sqrt_tile_init()
    call: sqrt_tile(0)
    f32: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x: max rel error 8.5e-08
    bf16: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x: max rel error 0.0039
    f32: measured on a Blackhole card with tt-metal 0.63, the [v06] spelling, x in [0.001, 1000]: max rel error 5.54e-06, max abs error 0.000171 (within the row's bound 0.01 rel; probe_sqrt-stock, agents 8ec7b7d)
    note: On a Blackhole with tt-metal 0.63, sqrt_tile() (legacy_compat = true, the default) has max relative error 5.5e-6 over x log-uniform in [1e-3, 1e3]; sqrt_tile_init<false>() and sqrt_tile<false>(0) give 9.3e-8, f32 accuracy, and run faster (0.77 ms against 0.98 ms on the probe; card run of 2026-11-18, alloy-tenstorrent agents commit dd226b3). 0.8x on ttsim: the table's bound.
```

## rsqrt

```text
tensix/f32,bf16/rsqrt: rsqrt, applied to a 32x32 tile
  SFPU (unary): header eltwise_unary/rsqrt.h
    includes [v06] compute: #include "compute_kernel_api/common.h" #include "compute_kernel_api/tile_move_copy.h" #include "compute_kernel_api/eltwise_unary/eltwise_unary.h" #include "compute_kernel_api/eltwise_binary.h" #include "compute_kernel_api/eltwise_unary/rsqrt.h"; reader/writer: #include "dataflow_api.h"
    includes [v08] compute: #include "api/compute/common.h" #include "api/compute/tile_move_copy.h" #include "api/compute/eltwise_unary/eltwise_unary.h" #include "api/compute/eltwise_binary.h" #include "api/compute/eltwise_unary/rsqrt.h"; reader/writer: #include "api/dataflow/dataflow_api.h"
    init: rsqrt_tile_init()
    call: rsqrt_tile(0)
    f32: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x: max rel error 7.3e-08
    bf16: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x: max rel error 0.0039
```

## recip

```text
tensix/f32,bf16/recip: recip, applied to a 32x32 tile
  SFPU (unary): header eltwise_unary/recip.h
    includes [v06] compute: #include "compute_kernel_api/common.h" #include "compute_kernel_api/tile_move_copy.h" #include "compute_kernel_api/eltwise_unary/eltwise_unary.h" #include "compute_kernel_api/eltwise_binary.h" #include "compute_kernel_api/eltwise_unary/recip.h"; reader/writer: #include "dataflow_api.h"
    includes [v08] compute: #include "api/compute/common.h" #include "api/compute/tile_move_copy.h" #include "api/compute/eltwise_unary/eltwise_unary.h" #include "api/compute/eltwise_binary.h" #include "api/compute/eltwise_unary/recip.h"; reader/writer: #include "api/dataflow/dataflow_api.h"
    init: recip_tile_init()
    call: recip_tile(0)
    f32: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x: max rel error 7.1e-08
    bf16: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x: max rel error 0.0039
```

## abs

```text
tensix/f32,bf16/abs: v[j] = |x[j]|, applied to a 32x32 tile
  SFPU (unary): header compute_kernel_api.h
    includes [v06] compute: #include "compute_kernel_api/common.h" #include "compute_kernel_api/tile_move_copy.h" #include "compute_kernel_api/eltwise_unary/eltwise_unary.h" #include "compute_kernel_api/eltwise_binary.h" #include "compute_kernel_api.h"; reader/writer: #include "dataflow_api.h"
    includes [v08] compute: #include "api/compute/common.h" #include "api/compute/tile_move_copy.h" #include "api/compute/eltwise_unary/eltwise_unary.h" #include "api/compute/eltwise_binary.h" #include "api/compute/compute_kernel_api.h"; reader/writer: #include "api/dataflow/dataflow_api.h"
    init: abs_tile_init()
    call: abs_tile(0)
    f32: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x: max rel error 0
    bf16: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x: max rel error 0
```

## neg

```text
tensix/f32,bf16/neg: v[j] = -x[j], applied to a 32x32 tile
  SFPU (unary): header eltwise_unary/negative.h
    includes [v06] compute: #include "compute_kernel_api/common.h" #include "compute_kernel_api/tile_move_copy.h" #include "compute_kernel_api/eltwise_unary/eltwise_unary.h" #include "compute_kernel_api/eltwise_binary.h" #include "compute_kernel_api/eltwise_unary/negative.h"; reader/writer: #include "dataflow_api.h"
    includes [v08] compute: #include "api/compute/common.h" #include "api/compute/tile_move_copy.h" #include "api/compute/eltwise_unary/eltwise_unary.h" #include "api/compute/eltwise_binary.h" #include "api/compute/eltwise_unary/negative.h"; reader/writer: #include "api/dataflow/dataflow_api.h"
    init: negative_tile_init()
    call: negative_tile(0)
    f32: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x: max rel error 0
    bf16: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x: max rel error 0
```

## tanh

```text
tensix/f32,bf16/tanh: tanh, applied to a 32x32 tile
  SFPU (unary): header compute_kernel_api.h
    includes [v06] compute: #include "compute_kernel_api/common.h" #include "compute_kernel_api/tile_move_copy.h" #include "compute_kernel_api/eltwise_unary/eltwise_unary.h" #include "compute_kernel_api/eltwise_binary.h" #include "compute_kernel_api.h"; reader/writer: #include "dataflow_api.h"
    includes [v08] compute: #include "api/compute/common.h" #include "api/compute/tile_move_copy.h" #include "api/compute/eltwise_unary/eltwise_unary.h" #include "api/compute/eltwise_binary.h" #include "api/compute/compute_kernel_api.h"; reader/writer: #include "api/dataflow/dataflow_api.h"
    init: tanh_tile_init()
    call: tanh_tile(0)
    f32: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x: max rel error 1.2e-07
    bf16: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x: max rel error 0.0046
    note: tt-metal 0.6x computes tanh from a lookup table: relative error between 0.1 and 0.3 near tanh's zero on a Blackhole (runs of 2026-11-16, tt-metal 0.63). 0.8x holds the table's bound.
```

## sin

```text
tensix/f32,bf16/sin: v[j] = sin(x[j]), applied to a 32x32 tile
  SFPU (unary): header eltwise_unary/trigonometry.h
    includes [v06] compute: #include "compute_kernel_api/common.h" #include "compute_kernel_api/tile_move_copy.h" #include "compute_kernel_api/eltwise_unary/eltwise_unary.h" #include "compute_kernel_api/eltwise_binary.h" #include "compute_kernel_api/eltwise_unary/trigonometry.h"; reader/writer: #include "dataflow_api.h"
    includes [v08] compute: #include "api/compute/common.h" #include "api/compute/tile_move_copy.h" #include "api/compute/eltwise_unary/eltwise_unary.h" #include "api/compute/eltwise_binary.h" #include "api/compute/eltwise_unary/trigonometry.h"; reader/writer: #include "api/dataflow/dataflow_api.h"
    init: sin_tile_init()
    call: sin_tile(0)
    f32: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x: max rel error 1.1e-07
    bf16: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x: max rel error 0.0037
```

## cos

```text
tensix/f32,bf16/cos: v[j] = cos(x[j]), applied to a 32x32 tile
  SFPU (unary): header eltwise_unary/trigonometry.h
    includes [v06] compute: #include "compute_kernel_api/common.h" #include "compute_kernel_api/tile_move_copy.h" #include "compute_kernel_api/eltwise_unary/eltwise_unary.h" #include "compute_kernel_api/eltwise_binary.h" #include "compute_kernel_api/eltwise_unary/trigonometry.h"; reader/writer: #include "dataflow_api.h"
    includes [v08] compute: #include "api/compute/common.h" #include "api/compute/tile_move_copy.h" #include "api/compute/eltwise_unary/eltwise_unary.h" #include "api/compute/eltwise_binary.h" #include "api/compute/eltwise_unary/trigonometry.h"; reader/writer: #include "api/dataflow/dataflow_api.h"
    init: cos_tile_init()
    call: cos_tile(0)
    f32: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x: max rel error 1.1e-07
    bf16: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x: max rel error 0.0037
```

## add

```text
tensix/f32,bf16/add: v[j] = a[j] + b[j], applied to a 32x32 tile
  FPU (binary): header eltwise_binary.h
    includes [v06] compute: #include "compute_kernel_api/common.h" #include "compute_kernel_api/tile_move_copy.h" #include "compute_kernel_api/eltwise_unary/eltwise_unary.h" #include "compute_kernel_api/eltwise_binary.h"; reader/writer: #include "dataflow_api.h"
    includes [v08] compute: #include "api/compute/common.h" #include "api/compute/tile_move_copy.h" #include "api/compute/eltwise_unary/eltwise_unary.h" #include "api/compute/eltwise_binary.h"; reader/writer: #include "api/dataflow/dataflow_api.h"
    init: add_tiles_init(c0, c1) [v06], add_init(c0, c1) [v08]
    call: add_tiles(c0, c1, 0, 0, 0)
    f32: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x, the [v08] spelling only: max rel error 0.00049
    bf16: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x, the [v08] spelling only: max rel error 0.0036
  SFPU (binary_sfpu): header eltwise_binary_sfpu.h
    includes [v06] compute: #include "compute_kernel_api/common.h" #include "compute_kernel_api/tile_move_copy.h" #include "compute_kernel_api/eltwise_unary/eltwise_unary.h" #include "compute_kernel_api/eltwise_binary.h" #include "compute_kernel_api/eltwise_binary_sfpu.h"; reader/writer: #include "dataflow_api.h"
    includes [v08] compute: #include "api/compute/common.h" #include "api/compute/tile_move_copy.h" #include "api/compute/eltwise_unary/eltwise_unary.h" #include "api/compute/eltwise_binary.h" #include "api/compute/eltwise_binary_sfpu.h"; reader/writer: #include "api/dataflow/dataflow_api.h"
    init: add_binary_tile_init()
    call: add_binary_tile(0, 1, 0)
    f32: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x: max rel error 6e-08
    bf16: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x: max rel error 0.0058
```

## sub

```text
tensix/f32,bf16/sub: v[j] = a[j] - b[j], applied to a 32x32 tile
  FPU (binary): header eltwise_binary.h
    includes [v06] compute: #include "compute_kernel_api/common.h" #include "compute_kernel_api/tile_move_copy.h" #include "compute_kernel_api/eltwise_unary/eltwise_unary.h" #include "compute_kernel_api/eltwise_binary.h"; reader/writer: #include "dataflow_api.h"
    includes [v08] compute: #include "api/compute/common.h" #include "api/compute/tile_move_copy.h" #include "api/compute/eltwise_unary/eltwise_unary.h" #include "api/compute/eltwise_binary.h"; reader/writer: #include "api/dataflow/dataflow_api.h"
    init: sub_tiles_init(c0, c1) [v06], sub_init(c0, c1) [v08]
    call: sub_tiles(c0, c1, 0, 0, 0)
    f32: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x, the [v08] spelling only: max rel error 0.00049
    bf16: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x, the [v08] spelling only: max rel error 0.0021
  SFPU (binary_sfpu): header eltwise_binary_sfpu.h
    includes [v06] compute: #include "compute_kernel_api/common.h" #include "compute_kernel_api/tile_move_copy.h" #include "compute_kernel_api/eltwise_unary/eltwise_unary.h" #include "compute_kernel_api/eltwise_binary.h" #include "compute_kernel_api/eltwise_binary_sfpu.h"; reader/writer: #include "dataflow_api.h"
    includes [v08] compute: #include "api/compute/common.h" #include "api/compute/tile_move_copy.h" #include "api/compute/eltwise_unary/eltwise_unary.h" #include "api/compute/eltwise_binary.h" #include "api/compute/eltwise_binary_sfpu.h"; reader/writer: #include "api/dataflow/dataflow_api.h"
    init: sub_binary_tile_init()
    call: sub_binary_tile(0, 1, 0)
    f32: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x: max rel error 3.9e-08
    bf16: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x: max rel error 0.0021
```

## mul

```text
tensix/f32,bf16/mul: v[j] = a[j] * b[j], applied to a 32x32 tile
  FPU (binary): header eltwise_binary.h
    includes [v06] compute: #include "compute_kernel_api/common.h" #include "compute_kernel_api/tile_move_copy.h" #include "compute_kernel_api/eltwise_unary/eltwise_unary.h" #include "compute_kernel_api/eltwise_binary.h"; reader/writer: #include "dataflow_api.h"
    includes [v08] compute: #include "api/compute/common.h" #include "api/compute/tile_move_copy.h" #include "api/compute/eltwise_unary/eltwise_unary.h" #include "api/compute/eltwise_binary.h"; reader/writer: #include "api/dataflow/dataflow_api.h"
    init: mul_tiles_init(c0, c1) [v06], mul_init(c0, c1) [v08]
    call: mul_tiles(c0, c1, 0, 0, 0)
    f32: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x, the [v08] spelling only: max rel error 0.002
    bf16: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x, the [v08] spelling only: max rel error 0.009
  SFPU (binary_sfpu): header eltwise_binary_sfpu.h
    includes [v06] compute: #include "compute_kernel_api/common.h" #include "compute_kernel_api/tile_move_copy.h" #include "compute_kernel_api/eltwise_unary/eltwise_unary.h" #include "compute_kernel_api/eltwise_binary.h" #include "compute_kernel_api/eltwise_binary_sfpu.h"; reader/writer: #include "dataflow_api.h"
    includes [v08] compute: #include "api/compute/common.h" #include "api/compute/tile_move_copy.h" #include "api/compute/eltwise_unary/eltwise_unary.h" #include "api/compute/eltwise_binary.h" #include "api/compute/eltwise_binary_sfpu.h"; reader/writer: #include "api/dataflow/dataflow_api.h"
    init: mul_binary_tile_init()
    call: mul_binary_tile(0, 1, 0)
    f32: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x: max rel error 5.7e-08
    bf16: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x: max rel error 0.0038
```

## div

```text
tensix/f32,bf16/div: v[j] = a[j] / b[j], applied to a 32x32 tile
  SFPU (binary_sfpu): header eltwise_binary_sfpu.h
    includes [v06] compute: #include "compute_kernel_api/common.h" #include "compute_kernel_api/tile_move_copy.h" #include "compute_kernel_api/eltwise_unary/eltwise_unary.h" #include "compute_kernel_api/eltwise_binary.h" #include "compute_kernel_api/eltwise_binary_sfpu.h"; reader/writer: #include "dataflow_api.h"
    includes [v08] compute: #include "api/compute/common.h" #include "api/compute/tile_move_copy.h" #include "api/compute/eltwise_unary/eltwise_unary.h" #include "api/compute/eltwise_binary.h" #include "api/compute/eltwise_binary_sfpu.h"; reader/writer: #include "api/dataflow/dataflow_api.h"
    init: div_binary_tile_init()
    call: div_binary_tile(0, 1, 0)
    f32: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x: max rel error 6.7e-08
    bf16: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x: max rel error 0.0037
    f32: measured on a Blackhole card with tt-metal 0.63, the [v06] spelling, x in [0.001, 1000]: max rel error 2.43e-07, max abs error 0.132 (within the row's bound 0.01 rel; probe_div-binary, agents 8ec7b7d)
```

## mma

```text
tensix/f32,bf16/mma: mma, applied to a 32x32 tile
  FPU (matmul): header matmul.h
    includes [v06] compute: #include "compute_kernel_api/common.h" #include "compute_kernel_api/tile_move_copy.h" #include "compute_kernel_api/matmul.h"; reader/writer: #include "dataflow_api.h"
    includes [v08] compute: #include "api/compute/common.h" #include "api/compute/tile_move_copy.h" #include "api/compute/matmul.h" #include "api/compute/compute_kernel_hw_startup.h" #include "api/compute/src_order.h"; reader/writer: #include "api/dataflow/dataflow_api.h"
    init: mm_init(c0, c1, c16) [v06], compute_kernel_hw_startup<SrcOrder::Reverse>(c0, c1, c16); matmul_init(c0, c1) [v08]
    call: matmul_tiles(c0, c1, 0, 0, 0, false) [v06], matmul_tiles(c0, c1, 0, 0, 0) [v08]
    f32: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x, the [v08] spelling only: max rel error 0.001
    bf16: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x, the [v08] spelling only: max rel error 0.0029
```

## reduce_add

```text
tensix/f32,bf16/reduce_add: s = sum of every active lane of v, applied to a 32x32 tile
  FPU (reduction): header reduce.h
    includes [v06] compute: #include "compute_kernel_api/common.h" #include "compute_kernel_api/reduce.h"; reader/writer: #include "dataflow_api.h"
    includes [v08] compute: #include "api/compute/common.h" #include "api/compute/reduce.h"; reader/writer: #include "api/dataflow/dataflow_api.h"
    init: reduce_init<PoolType::SUM, ReduceDim::REDUCE_SCALAR>(c0, c1, c16)
    call: reduce_tile<PoolType::SUM, ReduceDim::REDUCE_SCALAR>(c0, c1, 0, 0, 0)
    f32: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x: max rel error 0.00083
    bf16: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x: max rel error 1.5e-06
    note: the scaler tile (CB c1) holds 1 in the first row of each face; every data tile reduces into DST tile 0, packed once after the last; the sum sits at [0, 0] of the packed tile; fp32_dest_acc_en keeps the sum in f32; reduce_uninit() restores the packer
```

## reduce_max

```text
tensix/f32,bf16/reduce_max: s = the largest active lane of v; NaN lanes differ per ISA, applied to a 32x32 tile
  FPU (reduction): header reduce.h
    includes [v06] compute: #include "compute_kernel_api/common.h" #include "compute_kernel_api/reduce.h"; reader/writer: #include "dataflow_api.h"
    includes [v08] compute: #include "api/compute/common.h" #include "api/compute/reduce.h"; reader/writer: #include "api/dataflow/dataflow_api.h"
    init: reduce_init<PoolType::MAX, ReduceDim::REDUCE_SCALAR>(c0, c1, c16)
    call: reduce_tile<PoolType::MAX, ReduceDim::REDUCE_SCALAR>(c0, c1, 0, 0, 0)
    f32: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x: max rel error 0
    bf16: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x: max rel error 0
    note: the scaler tile (CB c1) holds 1 in the first row of each face (the maximum is scaled by it); every data tile reduces into DST tile 0, packed once after the last; the maximum sits at [0, 0] of the packed tile; reduce_uninit() restores the packer
```

## scan_add

```text
tensix/f32,bf16/scan_add: v[j] = x[0] + ... + x[j], the inclusive prefix sum of a register, applied to a 32x32 tile
  SFPU (scan): header cumsum.h
    includes [v06] compute: #include "compute_kernel_api/common.h" #include "compute_kernel_api/tile_move_copy.h" #include "compute_kernel_api/eltwise_unary/eltwise_unary.h" #include "compute_kernel_api/eltwise_binary.h" #include "compute_kernel_api/cumsum.h"; reader/writer: #include "dataflow_api.h"
    includes [v08] compute: #include "api/compute/common.h" #include "api/compute/tile_move_copy.h" #include "api/compute/eltwise_unary/eltwise_unary.h" #include "api/compute/eltwise_binary.h" #include "api/compute/cumsum.h"; reader/writer: #include "api/dataflow/dataflow_api.h"
    init: cumsum_tile_init()
    call: cumsum_tile(0, i == 0)
    f32: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x: max rel error 5.7e-07
    bf16: verified on ttsim v1.16.0 (simulated Blackhole) with tt-metal 0.8x: max rel error 0.0075
    note: the inclusive prefix sum down each column; tiles of one column arrive top to bottom, first = true only for the top one (i == 0 here), and no other SFPU call runs between them; along rows: transpose_tile before and transpose_dest after
```
