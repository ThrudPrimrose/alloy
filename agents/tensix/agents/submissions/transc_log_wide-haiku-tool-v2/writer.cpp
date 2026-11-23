// transc_log_wide: writer (NCRISC). Drains output tiles from CB 16 to DRAM.
#include "dataflow_api.h"

void kernel_main() {
    // runtime args: [num_tiles, out_addr]
    uint32_t num_tiles = get_arg_val<uint32_t>(0);
    uint32_t out_addr = get_arg_val<uint32_t>(1);

    constexpr uint32_t cb_out = tt::CBIndex::c_16;

    // compile-time args: TensorAccessorArgs of the output (offset 0)
    constexpr auto out_args = TensorAccessorArgs<0>();
    const auto out = TensorAccessor(out_args, out_addr, get_tile_size(cb_out));

    for (uint32_t i = 0; i < num_tiles; i++) {
        cb_wait_front(cb_out, 1);
        uint32_t l1_addr = get_read_ptr(cb_out);
        noc_async_write_tile(i, out, l1_addr);
        noc_async_write_barrier();
        cb_pop_front(cb_out, 1);
    }
}
