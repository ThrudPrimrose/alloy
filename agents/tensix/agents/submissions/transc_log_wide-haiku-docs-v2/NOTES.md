# transc_log_wide: design notes

## Design
- Three kernels, one tile per step, CB 0 and CB 16 each 2 tiles (host default).
- Reader (BRISC): `reader.cpp`. Runtime args `[n_tiles, in0_addr]`, accessor args `TensorAccessorArgs<0>`.
  Reads tile i with `noc_async_read_tile`, barriers, pushes CB 0.
- Compute (TRISC): `compute.cpp`. Runtime args `[n_tiles]`. Per tile: `copy_tile(cb0)` to DST[0], `log_tile<false>(0)`,
  pack DST[0] to CB 16.
- Writer (NCRISC): `writer.cpp`. Runtime args `[n_tiles, out_addr]`, accessor args `TensorAccessorArgs<0>`.
- config: `fp32_dest_acc_en` true so DST holds fp32 and the log result is not truncated. `unpack_to_dest_fp32` [0]
  so fp32 input tiles are unpacked into DST without a bf16-like truncation. No extra CBs.
- `math_fidelity` HiFi4 and `math_approx_mode` false. Neither affects the SFPU log path in the source I read.

## Accuracy (main risk)
- The Blackhole SFPU log (`tt_metal/hw/ckernels/blackhole/metal/llk_api/llk_sfpu/ckernel_sfpu_log.h`, `calculate_log_body`)
  is a 3rd-order polynomial on the mantissa in [1,2], plus `exp * ln2`. Its only `FAST_APPROX` difference is the
  negative-input NaN check. The tolerance is `1e-5 + 1e-3 |ref|`, so near x = 1 (ref about 0) the absolute error
  must be below 1e-5. A 3rd-order polynomial is unlikely to meet that. My estimate is an error of order 1e-3 to 1e-2
  there, which is not verified. Roughly 0.15 percent of log-uniform samples fall within 1 percent of x = 1.
- Not verified on a card. See QUESTIONS.md.

## API spellings I checked in the help tool (v0.63.0)
- `log_tile_init<bool>()` and `log_tile<bool>(uint32_t)` in `tt_metal/include/compute_kernel_api.h`, namespace ckernel.
  Default template argument is `fast_and_approx = true`. There is no `compute_kernel_api/eltwise_unary/log.h` header
  in 0.63 (checked with `docs ls`), so the include is the top-level `compute_kernel_api.h`.
- `init_sfpu(icb, ocb)`, `copy_tile_init(cb)`, `copy_tile(cb, offset, dst)`, `pack_tile(dst, cb)`,
  `tile_regs_acquire/commit/wait/release`: used in the `sfpu_eltwise_chain` and `eltwise_sfpu` examples.
- Dataflow: `TensorAccessorArgs<N>()`, `TensorAccessor(args, addr, page_bytes)`, `noc_async_read_tile`,
  `noc_async_write_tile`, `get_tile_size`, `get_write_ptr`, `get_read_ptr`: used in the `eltwise_sfpu` examples.
- `tt::CBIndex::c_0` and `c_16`: used in the examples.

## Not checked
- The `NAMESPACE`/`MAIN` macro form for the compute kernel: copied from the examples, not compiled.
- `unpack_to_dest_fp32` is given as a list of CB indices in config.json; the host side is assumed to map it to
  `UnpackToDestFp32` mode per CB.
- Per-tile barrier in the reader and writer: correct, but not tuned for throughput. Batching reads per several tiles
  would be the next step once the kernel is correct.
