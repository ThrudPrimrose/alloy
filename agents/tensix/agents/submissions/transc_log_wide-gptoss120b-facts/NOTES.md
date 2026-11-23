# Design Notes
- Reader reads tiles from DRAM into CB 0 using `noc_async_read` and pushes them.
- Compute kernel uses custom SFPU log implementation (`alloy_log_f32`) from FACTS.md because the built‑in `log_tile` on tt‑metal 0.63 is only bf16 accurate (abs error ~0.0165) which exceeds the required tolerance. The custom kernel runs on the TRISC SFPU lanes using the `MATH` macro and `llk_math_eltwise_unary_sfpu_params_` call.
- `log_tile_init<false>()` is NOT used; we rely on our own SFPU code.
- `fp32_dest_acc_en` is enabled and `unpack_to_dest_fp32` includes CB 0 so that tiles are unpacked to FP32 destination registers.
- Writer writes tiles from CB 16 back to DRAM.

## API spelling uncertainties (to verify on target)
- `get_write_ptr(cb)` / `get_read_ptr(cb)` – confirm correct function names for obtaining L1 buffer pointers.
- `noc_async_read_barrier()` – correct barrier for reads.
- `noc_async_write_barrier()` – correct barrier for writes.
- `cb_push_back(cb, n)` and `cb_pop_front(cb, n)` – argument order (cb index first).
- `MATH((_llk_math_eltwise_unary_sfpu_params_<APPROX>(...)))` – exact macro name and template parameters for invoking a custom SFPU face.
- Inclusion of `api/compute/compute_kernel_api.h` inside `#ifdef TRISC_MATH` – needed for `sfpi` definitions.
- Whether `VectorMode::RC` is the correct enum for row‑column vector mode.
- Whether `sfpi::vFloat` etc. are available after including `compute_kernel_api/eltwise_unary/eltwise_unary.h`.
