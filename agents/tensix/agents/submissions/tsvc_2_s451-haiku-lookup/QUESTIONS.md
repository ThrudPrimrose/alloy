# Questions for the owner

1. Compute header and scaffolding: I assume `compute_kernel_api/...` include paths and `namespace NAMESPACE { void MAIN }`
   with `init_sfpu(cb_in, cb_out)` and `binary_op_init_common(...)` for 0.63. Confirm this is the 0.63 form, not the
   `kernel_main()` form the tool gives for 0.8x.
2. `copy_tile_init(cb)` takes the CB id in 0.63 (I believe so); confirm, and whether `copy_tile_to_dst_init_short` is needed.
3. Dataflow API in 0.63: `TensorAccessorArgs<N>()`, `next_compile_time_args_offset()`, and the
   `TensorAccessor(args, addr, page_size)` constructor. Alloy has no dataflow rows; please confirm against the image.
4. Do the two `noc_async_read_tile` calls per iteration need to be batched for speed? I chose simplicity (one read and
   one barrier per tile). Score is device time, so a batched version may be faster; not done here.
5. Is `unpack_to_dest_fp32` indexed by CB index ([0, 1]) as the SPEC implies? I assume yes.
