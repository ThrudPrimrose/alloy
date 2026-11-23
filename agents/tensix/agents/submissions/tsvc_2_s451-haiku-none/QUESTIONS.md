# Questions for the owner

1. Which tt-metal 0.63 include layout is current: `api/...` paths or the older `dataflow_api.h` / `compute_kernel_api/...`?
   I used `api/...`.
2. Is the compute entry `namespace NAMESPACE { void MAIN }` or `void kernel_main()` in 0.63? I used `MAIN`.
3. Is it allowed to add `extra_cbs` for a deeper buffer on CB 0/1/16 (more tiles) to overlap reader and compute?
   I kept the host default of 2 tiles and listed no extra CBs.
4. Is sin_tile/cos_tile accurate enough in fp32 for the 1e-5 absolute term near zero? I could not check. If not, is
   a higher-accuracy path (for example a polynomial written by hand) acceptable?
