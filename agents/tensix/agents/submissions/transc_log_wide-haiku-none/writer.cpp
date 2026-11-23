// transc_log_wide: writer (NCRISC). Drains float32 result tiles from CB 16 to DRAM.
#include <cstdint>
#include "api/dataflow/dataflow_api.h"
#include "api/tensor/tensor_accessor.h"

// Runtime args: [num_tiles, out_addr]
// Compile-time args: TensorAccessorArgs of the output (offset 0).
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
