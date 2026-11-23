## Design summary
- **reader.cpp**: simple loop reading `num_tiles` float32 tiles from DRAM address `in_addr` into circular buffer CB 0. Uses `cb_reserve_back(cb, 1)`, `noc_async_read`, `noc_async_read_barrier`, `cb_push_back(cb, 1)`.
- **compute.cpp** (`fuse_diamond`): implements `out = (a*a + 1)*(a*a - 1) = a^4 - 1`.
  1. Load input tile from CB 0 into tile register 0 with `copy_tile(l1_addr, 0)`.
  2. `t = a*a` → `mul_binary_tile(0,0,1)`.
  3. `a^4 = t*t` → `mul_binary_tile(1,1,2)`.
  4. Generate a tile of constant **1.0** by:
     - `sub_binary_tile(0,0,3)` gives a zero tile in register 3.
     - `exp_tile(3)` (SFPU exp on zero yields 1.0) – `exp_tile_init()` is called.
  5. `out = a^4 - 1` → `sub_binary_tile(2,3,4)`.
  6. Write result tile from register 4 to CB 16 with `copy_tile(4,out_l1)`.
  7. All required SFPU ops are initialized at the start (`mul_binary_tile_init()`, `sub_binary_tile_init()`, `exp_tile_init()`).
- **writer.cpp**: writes each output tile from CB 16 to DRAM address `out_addr` using the same pattern as the reader but with `noc_async_write`.
- **config.json** enables full‑precision accumulation (`fp32_dest_acc_en: true`) and HiFi4 math fidelity. `unpack_to_dest_fp32` lists CBs that need destination‑FP32 unpack (input and output). An extra CB 2 is declared but not used – it could be removed.

## API spellings we are unsure of
- `copy_tile(src_ptr, reg)` vs `copy_tile(reg, dst_ptr)`. The direction used for loading a tile from L1 to a tile register is guessed as `copy_tile(l1_addr, 0)`. Opposite direction for storing is guessed as `copy_tile(reg, out_l1)`.
- `cb_reserve_back(cb, 1)` and `cb_push_back(cb, 1)` accept a **tile count**, not bytes. The host created CBs with `tiles = 2`, so a count of `1` is correct.
- Signature of binary SFPU ops: `mul_binary_tile(src0, src1, dst)` and `sub_binary_tile(src0, src1, dst)`. Assumed order of arguments (src0, src1, dst).
- `exp_tile(reg)` – assumes the tile register containing the argument is overwritten with the result (SFPU unary API).
- Initialization calls: `mul_binary_tile_init()`, `sub_binary_tile_init()`, `exp_tile_init()`. Assumed they exist for the SFPU binary/unary ops (facts list `exp_tile_init()`).
- `cb_wait_front(cb, 1)` waits for **one tile**; the second argument is tile count, not bytes.

If any of the above signatures differ, the kernels will need adjustment.
