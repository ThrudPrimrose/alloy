// NOT FROM TOOL: dataflow scaffolding (tool has no copy/load row for tensix)
#include <stdint.h>
#include "dataflow_api.h"

void kernel_main() {
    uint32_t num_tiles = get_arg_val<uint32_t>(0);
    uint32_t b_addr = get_arg_val<uint32_t>(1);
    uint32_t c_addr = get_arg_val<uint32_t>(2);

    constexpr uint32_t cb_b = 0;
    constexpr uint32_t cb_c = 1;

    constexpr auto b_args = TensorAccessorArgs<0>();
    constexpr auto c_args = TensorAccessorArgs<b_args.next_compile_time_args_offset()>();

    const uint32_t b_bytes = get_tile_size(cb_b);
    const uint32_t c_bytes = get_tile_size(cb_c);
    const auto b = TensorAccessor(b_args, b_addr, b_bytes);
    const auto c = TensorAccessor(c_args, c_addr, c_bytes);

    for (uint32_t i = 0; i < num_tiles; ++i) {
        cb_reserve_back(cb_b, 1);
        cb_reserve_back(cb_c, 1);
        noc_async_read_tile(i, b, get_write_ptr(cb_b));
        noc_async_read_tile(i, c, get_write_ptr(cb_c));
        noc_async_read_barrier();
        cb_push_back(cb_b, 1);
        cb_push_back(cb_c, 1);
    }
}
