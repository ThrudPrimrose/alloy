// Writer (NCRISC): writes CB 16 tiles to DRAM, one tile at a time.
// Runtime args: [num_tiles, out_addr]
// Compile-time args: TensorAccessorArgs of the output (offset 0).

#include <cstdint>
#include "dataflow_api.h"
#include "tensor_accessor.h"  // unsure of exact header path in 0.63, see NOTES.md

void kernel_main() {
    const uint32_t num_tiles = get_arg_val<uint32_t>(0);
    const uint32_t out_addr = get_arg_val<uint32_t>(1);

    constexpr uint32_t cb_out = tt::CBIndex::c_16;
    constexpr auto out_args = TensorAccessorArgs<0>();
    const uint32_t tile_bytes = get_tile_size(cb_out);
    const auto out = TensorAccessor(out_args, out_addr, tile_bytes);

    for (uint32_t i = 0; i < num_tiles; ++i) {
        cb_wait_front(cb_out, 1);
        const uint32_t l1_addr = get_read_ptr(cb_out);
        noc_async_write_tile(i, out, l1_addr);
        noc_async_write_barrier();
        cb_pop_front(cb_out, 1);
    }
}
