# Notes
- Include paths: using `#include "ttnn/tt_metal/kernels/dataflow.hpp"` for data movement kernels and `#include "ttnn/tt_metal/kernels/compute_kernel.hpp"` for compute kernels. If the actual header names differ (e.g., `kernel_dataflow.hpp`), this will need to be corrected.
- Runtime argument access: `get_arg_val<uint32_t>(index)` is assumed to retrieve a scalar argument. Verify the correct template type and indexing.
- Circular buffer API:
  - `cb_reserve_back(cb_id, num_tiles)` reserves space for `num_tiles` in the back of the CB.
  - `cb_push_back(cb_id, num_tiles)` makes the reserved tiles available to downstream kernels.
  - `cb_pop_front(cb_id, num_tiles)` releases tiles after consumption.
  - `get_write_ptr(cb_id)` returns a pointer (address) in L1 for the reserved back tile.
  - `get_read_ptr(cb_id)` returns a pointer to the front tile for reading.
  If any of these signatures differ (e.g., extra arguments for tile size), they must be adjusted.
- NOC async transfers:
  - `noc_async_read(src_addr, dst_addr, size_bytes)` reads from DRAM (src) into L1 (dst).
  - `noc_async_write(src_addr, dst_addr, size_bytes)` writes from L1 to DRAM.
  - `noc_async_read_barrier()` and `noc_async_write_barrier()` ensure completion.
  Verify that the ordering of src/dst matches the TT documentation.
- Tile size: For float32 tiles, 32x32 elements = 1024 elements, each 4 bytes → 4096 bytes. Used `1024 * sizeof(float)`. If the hardware expects 4096 bytes per tile, this is correct.
- CB IDs: Using `tt::CB::c_in0` for CB 0 and `tt::CB::c_out0` for CB 16. Confirm that `c_out0` maps to CB 16.
- Compute kernel locals: Using `reinterpret_cast<float*>` on L1 pointers; ensure proper alignment.
- No explicit synchronization (e.g., `wait_for_tile`) is used; barriers after async transfers should suffice.
- The `config.json` fields set to default values; may need `unpack_to_dest_fp32` to include CB 16 if required by host.
