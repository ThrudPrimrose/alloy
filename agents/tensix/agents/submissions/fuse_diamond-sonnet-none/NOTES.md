# fuse_diamond design
Single input, 1024 tiles, float32 end to end. Reader: one tile at a time DRAM -> CB0 via TensorAccessor.
Compute: copy the tile into 4 dest registers (CB0 unpacked straight to dest in fp32, fp32 dest acc on),
SFPU t = a*a twice (dst0, dst2), u = t+1, v = t-1, out = u*v, pack to CB16. SFPU (not FPU) binary ops are used
so products keep full fp32; FPU mul truncates mantissa and the t-1 cancellation near |a|=1 would miss the tolerance.
Writer: CB16 -> DRAM one tile at a time.

# Unsure API spellings
- Header paths: I use __has_include to choose "api/compute/..." / "api/dataflow/dataflow_api.h" (newer) or "compute_kernel_api/..." / "dataflow_api.h" (older).
- Compute entry: `void kernel_main()`, wrapped in `namespace NAMESPACE` only if NAMESPACE is defined (old builds use `void MAIN`).
- mul_binary_tile(idst0, idst1, odst) is the 3-arg form; older releases have 2-arg in-place (idst0, idst1). If compile fails, drop the third arg.
- add_unary_tile / sub_unary_tile(idst, uint32 float bits) and binop_with_scalar_tile_init(); the init may be named differently.
- init_sfpu(cb_in, cb_out) (older: unary_op_init_common).
- noc_async_read/write with accessor.get_noc_addr(i) instead of noc_async_read_tile.
- Dest holds 4 fp32 tiles in half-sync mode; I use exactly 4.
- Throughput is not tuned: CBs hold only 2 tiles and the reader/writer barrier per tile.
