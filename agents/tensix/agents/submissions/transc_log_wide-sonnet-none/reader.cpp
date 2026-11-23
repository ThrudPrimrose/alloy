#include <stdint.h>
#include "dataflow_api.h"

void kernel_main() {
    uint32_t num_tiles = get_arg_val<uint32_t>(0);
    uint32_t in_addr = get_arg_val<uint32_t>(1);

    constexpr uint32_t cb_in = 0;
    constexpr auto args = TensorAccessorArgs<0>();
    const uint32_t tile_bytes = get_tile_size(cb_in);
    const auto acc = TensorAccessor(args, in_addr, tile_bytes);

    for (uint32_t i = 0; i < num_tiles; ++i) {
        cb_reserve_back(cb_in, 1);
        noc_async_read(acc.get_noc_addr(i), get_write_ptr(cb_in), tile_bytes);
        noc_async_read_barrier();
        cb_push_back(cb_in, 1);
    }
}
