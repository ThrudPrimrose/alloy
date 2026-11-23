# Questions for the owner

1. Include paths in 0.63: is it `dataflow_api.h` / `tensor_accessor.h`, or `api/dataflow/dataflow_api.h` and
   `api/tensor/tensor_accessor.h`? I did not guess a third form.
2. Scalar add: is `binop_with_scalar_tile_init()` plus `add_unary_tile(idst, bits)` the 0.63 spelling, or is it
   `add_unary_tile_init()`? The Alloy tool has no scalar row, so this is from memory (`// NOT FROM TOOL`).
3. Is `copy_tile_init(cb)` the 0.63 name, with `copy_tile(cb, tile, dst)` as its pair? I used the same names
   from memory.
4. Is the design (recompute t instead of copying DST registers) acceptable, or does the host prefer a 3-tile
   DST budget check? I assume DST holds at least 3 f32 tiles in half-sync mode.
