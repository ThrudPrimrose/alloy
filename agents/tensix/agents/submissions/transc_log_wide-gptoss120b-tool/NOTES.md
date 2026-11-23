# NOTES
- `get_arg_val<uint32_t>(i)` is used to fetch runtime arguments. If the API expects a different template usage (e.g., `get_arg_val(i)` returning `uint32_t` directly), adjust accordingly.
- CB indices: input is fixed to CB 0, output to CB 16 as per host contract. No compile‑time argument for CB index is needed.
- Tile size: a float32 tile is 32x32 = 1024 elements; each element is 4 bytes, so `tile_bytes = 1024 * sizeof(float)`.
- `noc_async_read_barrier()` and `noc_async_write_barrier()` are used after each async transfer. If the API provides a different barrier name (e.g., `noc_async_read_barrier()` is correct, but verify spelling), update.
- `cb_reserve_back`, `cb_push_back`, `cb_wait_front`, `cb_pop_front`, `get_write_ptr`, `get_read_ptr` are the usual circular buffer API calls for the BRISC/TRISC/NCRISC kernels. Verify their exact signatures (e.g., whether they take a uint32_t CB index and tile count). 
- The compute kernel uses `std::log` from `<cmath>` which maps to the hardware `log` instruction for float32. Ensure the compiler maps this correctly; otherwise use the Tensix `log` operation directly if required.
- `config.json` sets `fp32_dest_acc_en` to true to enable FP32 accumulation, though this kernel only does elementwise log.
- No extra CBs are needed for this kernel.
