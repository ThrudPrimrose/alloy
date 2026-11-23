Design: log_tile on tt-metal 0.63 is a low-order approximation (abs err ~0.016), so the kernel uses the checked SFPI rung alloy_log_f32_sfpi (3.79 ulp on card), copied from the ask tool. One tile per iteration: copy to DST (fp32 via unpack_to_dest_fp32=[0], fp32_dest_acc_en), SFPU face loop, pack. Reader/writer are simple one-tile loops.

Unsure spellings:
- TensorAccessorArgs<0>() / TensorAccessor(args, addr, tile_bytes) and noc_async_read_tile(i, acc, l1) in 0.63.
- tt::CBIndex::c_0 vs tt::CB::c_in0 enum name.
- copy_tile_to_dst_init_short(cb) vs copy_tile_init(cb) in 0.63.
- init_sfpu(cb_in, cb_out) vs unary_op_init_common.
- Rung call placed after copy_tile without the extra llk_math_eltwise_unary_sfpu_start/done; the params helper is meant to handle that.
- Rung speed: 1.8 ms vs 0.7 ms for log_tile (from tool note); no faster accurate option known.
