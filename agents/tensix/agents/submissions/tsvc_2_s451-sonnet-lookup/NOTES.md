# tsvc_2_s451: out = sin(b) + cos(c)

Design: reader streams b (CB0) and c (CB1) tile by tile; compute copies b to DST[0] and c to DST[1] (fp32 via
UnpackToDestFp32 on CB 0 and 1), runs sin_tile(0), cos_tile(1), add_binary_tile(0,1,0) on the SFPU, packs DST[0] to
CB16; writer writes tiles. All fp32 (no FPU add, which has TF32 sources and ~5e-4 error; the 1e-5 abs tolerance
needs fp32). fp32_dest_acc_en=true, HiFi4, approx mode off. No extra CBs. Tool: sin/cos rel error 1.1e-7, SFPU add 6e-8.

From the tool: sin_tile_init/sin_tile, cos_tile_init/cos_tile, add_binary_tile_init/add_binary_tile, headers,
config, cb_wait_front, noc_async_read_barrier. Everything else is from memory (marked NOT FROM TOOL).

Unsure of (0.63 spelling):
- include paths: "compute_kernel_api/..." vs "api/compute/..." (0.63 should be the former); "dataflow_api.h".
- copy_tile_to_dst_init_short(cb) (alt: copy_tile_init(cb)); init_sfpu(cb_in, cb_out) placement.
- tile_regs_acquire/commit/wait/release and pack_tile spelling.
- TensorAccessorArgs<0>() / next_compile_time_args_offset(), TensorAccessor(args, addr, bytes), and
  noc_async_read_tile/noc_async_write_tile taking a TensorAccessor (alt: noc_async_read_page/write_page).
- Whether SFPU sin/cos init calls clobber each other's constants (I re-init before each op).
- Whether sin/cos are accurate over [-pi, pi] on hardware as on ttsim (abs tol 1e-5 near zero of the sum).
- DST holds 4 fp32 tiles in half-sync; I use 2.
