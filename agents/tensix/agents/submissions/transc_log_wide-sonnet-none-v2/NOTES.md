Design: reader streams 1024 fp32 tiles to CB0; compute copies each tile to DEST, applies log_tile (SFPU), packs to CB16; writer stores.
fp32 DEST + unpack_to_dest_fp32 on CB0 keep full fp32 input; math_approx_mode=false to get the accurate log path (abs tol 1e-5 near x=1).
Unsure spellings:
- Compute entry: kernel_main() vs `namespace NAMESPACE { void MAIN {} }` (0.63 should accept kernel_main).
- Include paths: compute_kernel_api/eltwise_unary/log.h vs compute_kernel_api.h vs api/compute/... (guarded with __has_include; new layout may need "api/compute/..." paths).
- log_tile_init() / log_tile(0); init_sfpu vs unary_op_init_common.
- copy_tile_init(cb_in) signature; with unpack_to_dest_fp32 some versions need it.
- tt::CBIndex::c_0 vs tt::CB::c_in0; TensorAccessor(args, addr, page_size) and noc_async_read_page(id, acc, addr).
- Accuracy of log_tile near x=1 is unverified; it may exceed 1e-5 abs there (possible fix: range-reduce manually).
