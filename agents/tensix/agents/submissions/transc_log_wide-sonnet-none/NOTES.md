Design: reader streams tiles of x into CB0; compute does copy_tile -> log_tile (SFPU, non-approx) -> pack to CB16; writer drains CB16.
fp32 end to end: fp32_dest_acc_en and unpack_to_dest_fp32=[0] so the unpacker does not truncate to tf32; approx mode off for the accurate log.

Unsure about:
- Compute entry: I used namespace NAMESPACE { void MAIN } (older form); 0.63 may want plain void kernel_main().
- Include paths: __has_include picks "api/compute/..." or "compute_kernel_api/...".
- log_tile_init() / log_tile(idst) signatures (newer versions may template on fast_and_approx).
- init_sfpu(cb_in, cb_out) name (newer: unary_op_init_common).
- TensorAccessor(args, addr, page_size) and acc.get_noc_addr(i); older code used noc_async_read_tile with InterleavedAddrGenFast.
- Accuracy of hardware log near x=1 (ref ~ 0): tolerance there is about 1e-5 absolute. Untested.
