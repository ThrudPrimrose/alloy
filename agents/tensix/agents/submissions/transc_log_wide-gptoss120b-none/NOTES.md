## Design
- Simple three‑kernel pipeline: reader moves tiles from DRAM to CB 0, compute reads from CB 0, writes to CB 16, writer moves tiles from CB 16 back to DRAM.
- Tile size for float32 is 32x32 elements = 1024 floats = 4096 bytes.
- All loops iterate over `num_tiles` runtime argument.

## API spelling uncertainties
- Namespace/enum for circular‑buffer IDs: used `tt::CB::c_in0` and `tt::CB::c_out0`. Actual names may be `tt::CB::c_in0` / `tt::CB::c_out0` or simply numeric literals (`0` and `16`).
- Functions to copy a whole tile between DRAM and L1: `noc_async_read_tile` and `noc_async_write_tile`. The real API could be `noc_async_read` / `noc_async_write` with a size argument, or there may be a helper like `l1_buffer_to_dram`.
- Barrier functions after async NOC: used `noc_async_read_barrier()` and `noc_async_write_barrier()`. The actual names might be `noc_async_read_barrier` (no parentheses) or `noc_async_write_barrier()`.
- Getting pointers: used `get_write_ptr(cb_id)` and `get_read_ptr(cb_id)`. These are likely correct, but could be `get_write_ptr(cb_id)` returning `uint32_t*` or a different helper.
- `cb_reserve_back`, `cb_push_back`, `cb_wait_front`, `cb_pop_front` are assumed to be the correct TT‑Metal APIs for circular‑buffer management.
- The include path `#include "tt_metal/tt_metal.hpp"` is the typical header, but could be `#include "tt_metal/tt_metal.h"`.
