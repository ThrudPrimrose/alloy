# Design Notes for `fuse_diamond`

## Overview
- **Reader** (`reader.cpp`)
  - Reads `num_tiles` float‑32 input tiles from DRAM into CB 0.
  - Uses `noc_async_read` / `noc_async_read_barrier`.
  - After the read completes we make the tile visible with `cb_push_back(cb_id, 1)` (the API takes a *tile count*, not byte size).

- **Compute** (`compute.cpp`)
  - For each tile we wait for one input tile with `cb_wait_front(cb_id_in0, 1)`.
  - Reads the L1 address via `get_read_ptr` for the input and `get_write_ptr` for the output.
  - Performs the element‑wise operation `out = (a*a + 1)*(a*a - 1)` (equivalent to `a^4 - 1`).
  - Pops the input tile (`cb_pop_front(cb_id_in0, 1)`) and pushes the output tile (`cb_push_back(cb_id_out, 1)`).

- **Writer** (`writer.cpp`)
  - Writes `num_tiles` output tiles from CB 16 back to DRAM.
  - Waits for a tile to be ready with `cb_wait_front(cb_id_out, 1)`, then issues `noc_async_write` followed by a barrier.
  - Pops the tile from the CB after the write.

## API Calls Used
- `get_arg_val<T>(idx)` – retrieve a runtime argument.
- `get_write_ptr(cb_id)` / `get_read_ptr(cb_id)` – obtain L1 address for the next write/read slot.
- `noc_async_read(src, dst, size_bytes)` and `noc_async_write(src, dst, size_bytes)`.
- `noc_async_read_barrier()` / `noc_async_write_barrier()` – ensure the DMA completes before the tile is used.
- `cb_push_back(cb_id, num_tiles)` – make `num_tiles` tiles available in the circular buffer.
- `cb_pop_front(cb_id, num_tiles)` – release tiles that have been consumed.
- `cb_wait_front(cb_id, num_tiles)` – block until at least `num_tiles` are available.

## Uncertainties (to be verified against tt‑metal 0.63 headers)
- Whether `cb_push_back(cb_id, 1)` expects a *tile count* or a *byte count*. The spec for data‑movement kernels usually uses tile count.
- The exact signature of `get_arg_val<T>(idx)`. Some kernels use `get_arg_val<uint32_t>(idx)`; others use `get_arg_val<uint32_t>(0)`. Assumed correct.
- Whether a read/write barrier is required after each tile or only after the whole batch. Using per‑tile barriers for simplicity.
- Inclusion of `tt_metal/kernels/dataflow_api.h` in the compute kernel: the compute kernel also needs `get_read_ptr`/`get_write_ptr`, which are defined in `dataflow_api.h`; we included it.
- The naming of `noc_async_read_barrier` / `noc_async_write_barrier`. In some versions the function is `noc_async_read_barrier()` and `noc_async_write_barrier()`. Assumed correct.

If any of the above are incorrect, the kernel will need minor adjustments.
