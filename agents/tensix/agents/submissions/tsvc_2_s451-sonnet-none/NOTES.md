Design: reader pushes one b tile and one c tile per iteration; compute copies b to DST0 and c to DST1, runs the SFPU
sin on DST0 and cos on DST1, adds them with the SFPU binary add into DST0, packs to CB 16; writer drains CB 16.
fp32_dest_acc_en and unpack_to_dest_fp32 on CB 0/1 keep full fp32 (no tf32 truncation). Approx mode off.

Unsure of:
- Include paths: I used compute_kernel_api/... (older layout). 0.63 may use api/compute/... instead.
- Entry point: namespace NAMESPACE { void MAIN } form; 0.63 may want plain void kernel_main().
- add_binary_tile(idst0, idst1, odst) three-argument form (older: two-argument, result in idst0), and add_binary_tile_init().
- copy_tile_to_dst_init_short(cb) name; copy_tile_init(cb) in some versions. With unpack_to_dest_fp32 it may need the _with_dt variant.
- unary_op_init_common(icb, ocb) name; may be init_sfpu.
- TensorAccessor::get_noc_addr(page) and noc_async_read/write by byte address (alternative: noc_async_read_page).
- sin/cos SFPU accuracy over [-pi, pi] against 1e-3 relative: the sum can be near zero, where the 1e-5 absolute floor is tight.
