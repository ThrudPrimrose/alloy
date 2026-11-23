// Reader (BRISC): streams A and B tiles from DRAM into CB 0 (A, bf16) and CB 1 (B, bf16).
// Order: for each output tile (mt, nt), for kt: A tile mt*Kt+kt, then B tile kt*Nt+nt.
// The compute kernel consumes in the same order.
#include <cstdint>
#include "dataflow_api.h"

void kernel_main() {
    const uint32_t Mt = get_arg_val<uint32_t>(0);
    const uint32_t Kt = get_arg_val<uint32_t>(1);
    const uint32_t Nt = get_arg_val<uint32_t>(2);
    const uint32_t a_addr = get_arg_val<uint32_t>(3);
    const uint32_t b_addr = get_arg_val<uint32_t>(4);

    constexpr uint32_t cb_a = 0;
    constexpr uint32_t cb_b = 1;

    // Compile-time args: accessor args of A, then those of B.
    constexpr auto a_args = TensorAccessorArgs<0>();
    constexpr auto b_args = TensorAccessorArgs<a_args.next_compile_time_args_offset()>();

    const uint32_t a_tile_bytes = get_tile_size(cb_a);
    const uint32_t b_tile_bytes = get_tile_size(cb_b);
    const auto a = TensorAccessor(a_args, a_addr, a_tile_bytes);
    const auto b = TensorAccessor(b_args, b_addr, b_tile_bytes);

    for (uint32_t mt = 0; mt < Mt; ++mt) {
        for (uint32_t nt = 0; nt < Nt; ++nt) {
            for (uint32_t kt = 0; kt < Kt; ++kt) {
                cb_reserve_back(cb_a, 1);
                cb_reserve_back(cb_b, 1);
                noc_async_read_tile(mt * Kt + kt, a, get_write_ptr(cb_a));
                noc_async_read_tile(kt * Nt + nt, b, get_write_ptr(cb_b));
                noc_async_read_barrier();
                cb_push_back(cb_a, 1);
                cb_push_back(cb_b, 1);
            }
        }
    }
}
