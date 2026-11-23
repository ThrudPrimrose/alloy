1. Is `void kernel_main()` the right compute entry point in 0.63, or must compute use `namespace NAMESPACE { void MAIN() }`?
2. Which include paths does 0.63 use (`api/...` prefix or the older flat names)?
3. Is the 2-arg `compute_kernel_hw_startup(cb_in, cb_out)` valid for SFPU-only kernels, or should I use `init_sfpu`?
4. Does `add_unary_tile` take the scalar as a float bit pattern (as I assumed)?
5. Is the literal (t+1)(t-1) form acceptable, or should I simplify to a^4 - 1? I kept the literal form.
