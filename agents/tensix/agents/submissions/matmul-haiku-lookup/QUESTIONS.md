# Questions for the owner

1. HiFi4 is the safe choice for bf16 operands. HiFi2 or LoFi would need fewer FPU passes, and the 1e-2 Frobenius tolerance
   probably allows them. Do you want me to switch for speed? I kept HiFi4.
2. Should the kernels use the 0.8x scaffolding (`kernel_main` for compute, `compute_kernel_hw_startup`, `matmul_init`) or
   the 0.6x one? The brief says 0.63, and the Alloy tool gives 0.6x spellings, so I used 0.6x. Please confirm the image
   really is 0.63 and not a 0.8x build.
3. Does `dataflow_api.h` bring in `TensorAccessor` and `TensorAccessorArgs` in 0.63, or must I include
   `api/tensor/tensor_accessor.h` explicitly? I could not check.
4. Does the host accept `extra_cbs` entries for indices 0 and 1 that override the default CBs, or should it reject them?
   The spec says it does; I followed the spec.
5. Is a blocked schedule (an A row kept resident in L1) in scope for this pass, or should I keep the simple version?
