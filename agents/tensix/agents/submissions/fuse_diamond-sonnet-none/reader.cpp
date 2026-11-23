#include <stdint.h>
#if __has_include("api/dataflow/dataflow_api.h")
#include "api/dataflow/dataflow_api.h"
#else
#include "dataflow_api.h"
#endif

void kernel_main() {
    uint32_t num_tiles = get_arg_val<uint32_t>(0);
    uint32_t in0_addr = get_arg_val<uint32_t>(1);

    constexpr uint32_t cb_in0 = 0;
    const uint32_t tile_bytes = get_tile_size(cb_in0);

    constexpr auto args = TensorAccessorArgs<0>();
    const auto in0 = TensorAccessor(args, in0_addr, tile_bytes);

    for (uint32_t i = 0; i < num_tiles; ++i) {
        cb_reserve_back(cb_in0, 1);
        uint32_t l1 = get_write_ptr(cb_in0);
        noc_async_read(in0.get_noc_addr(i), l1, tile_bytes);
        noc_async_read_barrier();
        cb_push_back(cb_in0, 1);
    }
}
