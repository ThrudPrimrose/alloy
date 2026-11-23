#include <stdint.h>
#if __has_include("api/dataflow/dataflow_api.h")
#include "api/dataflow/dataflow_api.h"
#else
#include "dataflow_api.h"
#endif

void kernel_main() {
    uint32_t num_tiles = get_arg_val<uint32_t>(0);
    uint32_t out_addr = get_arg_val<uint32_t>(1);

    constexpr uint32_t cb_out = 16;
    const uint32_t tile_bytes = get_tile_size(cb_out);

    constexpr auto args = TensorAccessorArgs<0>();
    const auto out = TensorAccessor(args, out_addr, tile_bytes);

    for (uint32_t i = 0; i < num_tiles; ++i) {
        cb_wait_front(cb_out, 1);
        uint32_t l1 = get_read_ptr(cb_out);
        noc_async_write(l1, out.get_noc_addr(i), tile_bytes);
        noc_async_write_barrier();
        cb_pop_front(cb_out, 1);
    }
}
