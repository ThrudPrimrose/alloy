# fuse_diamond: design (tt-metal 0.63, Blackhole, one Tensix core)

Math: t = a*a; u = t + 1; v = t - 1; out = u*v. Tolerance 1e-5 + 1e-3|ref| needs full float32 on the SFPU.

- Reader (BRISC): one tile at a time from DRAM into CB 0 (2 tiles, double buffered by the host CB).
- Compute (TRISC): per tile, copy a into DST0, DST1, DST2 (copy_tile, UnpackToDestFp32 on CB 0).
  mul_binary_tile(0,1,0) gives t in DST0; mul_binary_tile(1,2,1) gives t in DST1 (recomputed, so no
  copy between DST registers is needed). add_unary_tile adds +1.0 to DST0 and -1.0 to DST1. A final
  mul_binary_tile(0,1,0) gives u*v in DST0, packed to CB 16.
- Writer (NCRISC): one tile at a time from CB 16 to DRAM.
- config.json: fp32_dest_acc_en true (DST and pack in f32), math_approx_mode false, math_fidelity HiFi4
  (no FPU op here, so it has no effect), unpack_to_dest_fp32 [0], no extra CBs.

## Tool-sourced spellings (Alloy, tensix, 0.6x form)
- mul_binary_tile_init(), mul_binary_tile(d0, d1, dst) (SFPU, keeps f32). Header eltwise_binary_sfpu.h.
- add_binary_tile is not used; the tool lists it as the add alternative.
- init_sfpu(icb, ocb) and NAMESPACE / MAIN scaffolding, as the tool states for 0.6x.
- No square row exists (the tool says so), so a*a is mul_binary_tile on two copies of a.

## NOT FROM TOOL (written from memory; check against the 0.63 headers)
- copy_tile_init(cb), copy_tile(cb, tile, dst): the tool names copy_tile only in a note. Header
  compute_kernel_api/tile_move_copy.h.
- binop_with_scalar_tile_init() and add_unary_tile(idst, uint32 float-bits). Header
  compute_kernel_api/eltwise_unary/binop_with_scalar.h. The tool has no add-scalar row (asked; see asks.log).
  Scalars are passed as the IEEE bit pattern: 0x3F800000 = 1.0f, 0xBF800000 = -1.0f.
- tile_regs_acquire/commit/wait/release, pack_tile, cb_* calls: the standard 0.6x compute API.
- Data movement: dataflow_api.h, tensor_accessor.h, TensorAccessorArgs<0>(), TensorAccessor(args, addr,
  page_bytes), get_tile_size, get_write_ptr / get_read_ptr, noc_async_read_tile / write_tile,
  noc_async_read_barrier / write_barrier. The tool covers no data movement (copy global->tile_register is
  "not_covered").

Unsure: the include directories (flat "dataflow_api.h" vs "api/dataflow/..." in 0.63), whether
copy_tile_init is required before each copy group (I call it once per tile, before the copies), and whether
DST holds 3 f32 tiles in half-sync mode (4 is expected).
