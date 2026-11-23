#include <stdint.h>
#include "dataflow_api.h"

void kernel_main() {
    const uint32_t num_tiles = get_arg_val<uint32_t>(0);
    const uint32_t c_addr = get_arg_val<uint32_t>(1);

    constexpr uint32_t cb_c = 16;
    constexpr auto c_args = TensorAccessorArgs<0>();
    const uint32_t c_bytes = get_tile_size(cb_c);
    const auto c = TensorAccessor(c_args, c_addr, c_bytes);

    for (uint32_t t = 0; t < num_tiles; ++t) {
        cb_wait_front(cb_c, 1);
        noc_async_write(get_read_ptr(cb_c), c.get_noc_addr(t), c_bytes);
        noc_async_writes_flushed();
        cb_pop_front(cb_c, 1);
    }
    noc_async_write_barrier();
}
