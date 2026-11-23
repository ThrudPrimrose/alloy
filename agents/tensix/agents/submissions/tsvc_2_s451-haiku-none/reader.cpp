// tsvc_2_s451 reader (BRISC): streams tiles of b (CB 0) and c (CB 1) from DRAM.
#include "api/dataflow/dataflow_api.h"
#include "api/tensor/tensor_accessor.h"

void kernel_main() {
    const uint32_t num_tiles = get_arg_val<uint32_t>(0);
    const uint32_t b_addr = get_arg_val<uint32_t>(1);
    const uint32_t c_addr = get_arg_val<uint32_t>(2);

    constexpr uint32_t cb_b = 0;
    constexpr uint32_t cb_c = 1;

    constexpr auto b_args = TensorAccessorArgs<0>();
    constexpr auto c_args = TensorAccessorArgs<b_args.next_compile_time_args_offset()>();

    const uint32_t tile_bytes = get_tile_size(cb_b);
    const auto b_acc = TensorAccessor(b_args, b_addr, tile_bytes);
    const auto c_acc = TensorAccessor(c_args, c_addr, tile_bytes);

    for (uint32_t i = 0; i < num_tiles; ++i) {
        cb_reserve_back(cb_b, 1);
        cb_reserve_back(cb_c, 1);
        noc_async_read_tile(i, b_acc, get_write_ptr(cb_b));
        noc_async_read_tile(i, c_acc, get_write_ptr(cb_c));
        noc_async_read_barrier();
        cb_push_back(cb_b, 1);
        cb_push_back(cb_c, 1);
    }
}
