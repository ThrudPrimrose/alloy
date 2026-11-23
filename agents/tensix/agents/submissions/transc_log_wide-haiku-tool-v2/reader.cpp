// transc_log_wide: reader (BRISC). Streams input tiles from DRAM into CB 0.
#include "dataflow_api.h"

void kernel_main() {
    // runtime args: [num_tiles, in0_addr]
    uint32_t num_tiles = get_arg_val<uint32_t>(0);
    uint32_t in0_addr = get_arg_val<uint32_t>(1);

    constexpr uint32_t cb_in0 = tt::CBIndex::c_0;

    // compile-time args: TensorAccessorArgs of input 0 (offset 0)
    constexpr auto in0_args = TensorAccessorArgs<0>();
    const auto in0 = TensorAccessor(in0_args, in0_addr, get_tile_size(cb_in0));

    for (uint32_t i = 0; i < num_tiles; i++) {
        cb_reserve_back(cb_in0, 1);
        uint32_t l1_addr = get_write_ptr(cb_in0);
        noc_async_read_tile(i, in0, l1_addr);
        noc_async_read_barrier();
        cb_push_back(cb_in0, 1);
    }
}
