#include <stdint.h>
#include "dataflow_api.h"

void kernel_main() {
    uint32_t num_tiles = get_arg_val<uint32_t>(0);
    uint32_t in0_addr = get_arg_val<uint32_t>(1);
    constexpr uint32_t cb_in = tt::CBIndex::c_0;
    constexpr auto args = TensorAccessorArgs<0>();
    const uint32_t tile_bytes = get_tile_size(cb_in);
    const auto acc = TensorAccessor(args, in0_addr, tile_bytes);
    for (uint32_t i = 0; i < num_tiles; i++) {
        cb_reserve_back(cb_in, 1);
        uint32_t l1 = get_write_ptr(cb_in);
        noc_async_read_tile(i, acc, l1);
        noc_async_read_barrier();
        cb_push_back(cb_in, 1);
    }
}
