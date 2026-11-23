# tsvc_2_s451 on Tensix (tt-metal 0.63)

Design: out = sin(b) + cos(c), 1024 tiles, one core.
- Reader: per tile, pushes one b tile to CB 0, then one c tile to CB 1 (each CB holds 2 tiles, so no deadlock).
- Compute: per tile, copy b -> DST[0] and c -> DST[1] (unpacked as f32 via unpack_to_dest_fp32 [0,1]),
  sin_tile(0), cos_tile(1), add_binary_tile(0,1,0) (SFPU, keeps f32), pack DST[0] -> CB 16.
- Writer: waits on CB 16 and writes tile i with noc_async_write_tile.
- Config: fp32_dest_acc_en true (needed for f32 DST), math_approx_mode false (sin/cos accuracy; abs tolerance
  1e-5 matters where the sum is near 0), HiFi4 (irrelevant for SFPU), no extra CBs.
- Why SFPU add, not FPU add_tiles: the tool says FPU sources are TF32 (about 1e-3 relative), which is at the
  edge of tolerance; SFPU keeps f32 (tool: max rel error 6e-8).

Tool-sourced spellings (Alloy tensix rows, verified on ttsim v1.16.0 per the tool):
- sin_tile_init(), sin_tile(d); cos_tile_init(), cos_tile(d)  (eltwise_unary/trigonometry.h)
- add_binary_tile_init(), add_binary_tile(d0, d1, o)  (eltwise_binary_sfpu.h)
- init_sfpu, binary_op_init_common, namespace NAMESPACE { void MAIN } (tool: 0.6x scaffolding)

NOT FROM TOOL (tool has no rows for these; written from tt-metal 0.6x knowledge):
- copy_tile_init(cb), copy_tile(cb, idx, dst), pack_tile(dst, cb)
- tile_regs_acquire/commit/wait/release, cb_wait_front/cb_pop_front/cb_reserve_back/cb_push_back
- all dataflow: TensorAccessorArgs<>, next_compile_time_args_offset(), TensorAccessor(args, addr, page_size),
  get_tile_size, get_write_ptr/get_read_ptr, noc_async_read_tile, noc_async_write_tile, noc barriers
- get_arg_val in the compute kernel (header not checked)

Spellings unsure of: see QUESTIONS.md.
