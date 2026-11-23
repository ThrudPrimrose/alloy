# Questions for the owner

1. Does the non-approx `log_tile` in tt-metal 0.63 meet |got - ref| <= 1e-5 + 1e-3 |ref| near x = 1, where ref is near 0 and the bound is essentially absolute? If not, is there a preferred fallback (e.g. log via exponent split and a higher-order polynomial in compute)?
2. Compute entry point: is `void kernel_main()` correct for compute kernels in 0.63, or should it be `void MAIN`?
3. Is `tensor_accessor.h` the right include for the reader and writer, or is it already in `dataflow_api.h`?
4. May I add `extra_cbs` to batch 2 to 4 tiles per DEST acquire for the "wide" variant, or is the 2-tile CB layout fixed for this task?
