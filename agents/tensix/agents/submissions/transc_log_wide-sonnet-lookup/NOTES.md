# transc_log_wide design
Native log_tile on 0.63 has rel error >0.3 near x=1 (tool note), so it is only the start y0. Two Halley steps
y <- y + 2(x - e^y)/(x + e^y) with the accurate exp_tile (6.5e-8 rel) give cubic convergence; the error near x=1 is
~1e-7 abs (tolerance 1e-5). One tile at a time, fp32 DST (4 tiles used: x, y, e, tmp), HiFi4, approx off, CB0 unpacked
to dest fp32. Reader/writer are the plain one-tile-at-a-time loops.

Unsure (from tool: log, exp, add/sub/mul/div_binary_tile, init_sfpu, copy_tile_to_dst_init_short, headers;
rest from memory):
- Include paths `compute_kernel_api/eltwise_unary/eltwise_unary.h` (init_sfpu), `.../eltwise_unary/exp.h`,
  `.../eltwise_binary_sfpu.h`, `common.h`, `tile_move_copy.h` in 0.63.
- Whether start log_tile is good enough everywhere (not only near 1); if it is garbage (NaN/inf) the iteration fails.
  The second step covers abs error up to roughly 0.5 in y.
- add_binary_tile(3,3,3) with all three operands equal (in-place) is assumed fine; likewise sub(0,0,3).
- Re-calling *_binary_tile_init / exp_tile_init each step is cheap, but may be redundant.
- DST capacity: fp32 DST used with 4 tiles (indices 0..3); assumed available.
- `copy_tile_to_dst_init_short` is called once per tile before the copy_tile calls.
Everything not in the tool answers is "NOT FROM TOOL": the Halley scheme and the in-DST zero trick (d0 - d0).
asks.log has the tool log; isa.sh is the logging wrapper.
