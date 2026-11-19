// reader: this core's tiles start .. start + n - 1 of 3 input(s), input k into CB k, 2 per barrier
#include <stdint.h>
#include "dataflow_api.h"

void kernel_main() {
    uint32_t num_tiles = get_arg_val<uint32_t>(0);
    uint32_t start = get_arg_val<uint32_t>(1);
    constexpr auto args0 = TensorAccessorArgs<0>();
    const uint32_t bytes0 = get_tile_size(0);
    const auto s0 = TensorAccessor(args0, get_arg_val<uint32_t>(2), bytes0);
    constexpr auto args1 = TensorAccessorArgs<args0.next_compile_time_args_offset()>();
    const uint32_t bytes1 = get_tile_size(1);
    const auto s1 = TensorAccessor(args1, get_arg_val<uint32_t>(3), bytes1);
    constexpr auto args2 = TensorAccessorArgs<args1.next_compile_time_args_offset()>();
    const uint32_t bytes2 = get_tile_size(2);
    const auto s2 = TensorAccessor(args2, get_arg_val<uint32_t>(4), bytes2);
    for (uint32_t i = 0; i < num_tiles; i += 2) {
        uint32_t n = num_tiles - i < 2 ? num_tiles - i : 2;
        cb_reserve_back(0, n);
        cb_reserve_back(1, n);
        cb_reserve_back(2, n);
        uint32_t w0 = get_write_ptr(0);
        uint32_t w1 = get_write_ptr(1);
        uint32_t w2 = get_write_ptr(2);
        for (uint32_t t = 0; t < n; ++t) {
            noc_async_read_tile(start + i + t, s0, w0 + t * bytes0);
            noc_async_read_tile(start + i + t, s1, w1 + t * bytes1);
            noc_async_read_tile(start + i + t, s2, w2 + t * bytes2);
        }
        noc_async_read_barrier();
        cb_push_back(0, n);
        cb_push_back(1, n);
        cb_push_back(2, n);
    }
}
