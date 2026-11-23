Design: all-SFPU in DST, fp32. FPU binary ops would round operands to TF32 (~1e-3), so they are avoided.
Per tile: copy_tile a -> DST0 (CB 0 unpacked to dest in fp32), t = mul_binary_tile(0,0,0), DST1 = fill 1.0,
u = add_binary_tile(0,1,2), v = sub_binary_tile(0,1,3), out = mul_binary_tile(2,3,2), pack DST2 -> CB 16.
Reader/writer follow the tool's harness (one tile per barrier, no batching; CB depth is 2 so it overlaps a little).
Spellings from the tool (v06): init_sfpu, copy_tile_to_dst_init_short, *_binary_tile(_init), includes under compute_kernel_api/.
Unsure (NOT FROM TOOL):
- fill_tile_init(); fill_tile(idst, float) and its include compute_kernel_api/eltwise_unary/fill.h in 0.63.
- Whether re-calling the binary-sfpu inits between ops each tile is needed or only costs time.
- pack_tile(2, c16) with DST index 2 and four fp32 DST tiles live: assumes fp32 half-sync DST holds 4 tiles.
- init_sfpu argument form (c0, c16) and use of tt::CBIndex enum in 0.63 (taken from the tool harness).
- Include path for eltwise_binary_sfpu.h (tool names header, 0.6x prefix compute_kernel_api/ assumed).
- Performance not tuned (no batching of tiles per DST acquire, no bigger CBs).
