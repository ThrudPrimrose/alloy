#include <stdint.h>
#include "dataflow_api.h"

void kernel_main() {
    const uint32_t Mt = get_arg_val<uint32_t>(0);
    const uint32_t Kt = get_arg_val<uint32_t>(1);
    const uint32_t Nt = get_arg_val<uint32_t>(2);
    const uint32_t a_addr = get_arg_val<uint32_t>(3);
    const uint32_t b_addr = get_arg_val<uint32_t>(4);

    constexpr uint32_t cb_a = 0;
    constexpr uint32_t cb_b = 1;

    constexpr auto a_args = TensorAccessorArgs<0>();
    constexpr auto b_args = TensorAccessorArgs<a_args.next_compile_time_args_offset()>();

    const uint32_t a_bytes = get_tile_size(cb_a);
    const uint32_t b_bytes = get_tile_size(cb_b);
    const auto a = TensorAccessor(a_args, a_addr, a_bytes);
    const auto b = TensorAccessor(b_args, b_addr, b_bytes);

    // All of B stays resident in CB 1 (Kt*Nt tiles); compute never pops it.
    const uint32_t b_tiles = Kt * Nt;
    cb_reserve_back(cb_b, b_tiles);
    uint32_t b_l1 = get_write_ptr(cb_b);
    for (uint32_t t = 0; t < b_tiles; ++t) {
        noc_async_read(b.get_noc_addr(t), b_l1, b_bytes);
        b_l1 += b_bytes;
    }
    noc_async_read_barrier();
    cb_push_back(cb_b, b_tiles);

    // One row of A (Kt tiles) per block row of C.
    for (uint32_t i = 0; i < Mt; ++i) {
        cb_reserve_back(cb_a, Kt);
        uint32_t a_l1 = get_write_ptr(cb_a);
        for (uint32_t k = 0; k < Kt; ++k) {
            noc_async_read(a.get_noc_addr(i * Kt + k), a_l1, a_bytes);
            a_l1 += a_bytes;
        }
        noc_async_read_barrier();
        cb_push_back(cb_a, Kt);
    }
}
