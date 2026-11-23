# Design
Single core, output tile (mt, nt) = sum over kt of A(mt,kt) x B(kt,nt), accumulated in DST (fp32_dest_acc_en) by
matmul_tiles, packed once to the fp32 CB 16. Reader reads A's row block (Kt tiles) once per mt and keeps it in CB 0
for all nt; B's column (Kt tiles) per nt. CB 0 and CB 1 hold 32 tiles (2 x Kt=16) for double buffering; one barrier
per block. Compute indexes tiles inside the waited block (matmul_tiles(c0, c1, kt, kt, 0, false)). HiFi4 for safety.
Needs Kt <= 16 (CB size). Tool source: `ask tensix mma` (v06 spellings), writer/reader patterns from the tool harness.

# Unsure of (0.63 spellings)
- Includes: "compute_kernel_api/common.h", "tile_move_copy.h", "matmul.h" (tool harness paths for 0.6x); the tool never
  checked "dataflow_api.h" with get_tile_size on non-default CB sizes.
- mm_init(c0, c1, c16) and matmul_tiles(..., false): from tool row v06.
- `a_args.next_compile_time_args_offset()` for B's accessor offset: NOT FROM TOOL (own memory). Fallback: constexpr
  offset equal to A's arg count.
- tt::CBIndex::c_0 enum in 0.63: from tool harness.
- Lookup tool has no rows for cb_reserve_back/pack_tile/etc.; those follow the tool harness's generated kernels.
- Whether HiFi2 passes 1e-2 Frobenius: not tried (no device).
