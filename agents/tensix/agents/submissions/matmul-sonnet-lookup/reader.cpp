#include <stdint.h>
#include "dataflow_api.h"

// A row block (Kt tiles of row mt) is read once per mt and reused for every nt; B column nt (Kt tiles) per nt.
// All reads of a block are issued, then one barrier.
void kernel_main() {
    uint32_t Mt = get_arg_val<uint32_t>(0);
    uint32_t Kt = get_arg_val<uint32_t>(1);
    uint32_t Nt = get_arg_val<uint32_t>(2);
    uint32_t a_addr = get_arg_val<uint32_t>(3);
    uint32_t b_addr = get_arg_val<uint32_t>(4);

    constexpr uint32_t cb_a = 0;
    constexpr uint32_t cb_b = 1;

    constexpr auto a_args = TensorAccessorArgs<0>();
    constexpr auto b_args = TensorAccessorArgs<a_args.next_compile_time_args_offset()>();  // NOT FROM TOOL
    const auto a = TensorAccessor(a_args, a_addr, get_tile_size(cb_a));
    const auto b = TensorAccessor(b_args, b_addr, get_tile_size(cb_b));
    const uint32_t a_tile_bytes = get_tile_size(cb_a);
    const uint32_t b_tile_bytes = get_tile_size(cb_b);

    for (uint32_t mt = 0; mt < Mt; ++mt) {
        cb_reserve_back(cb_a, Kt);
        uint32_t a_ptr = get_write_ptr(cb_a);
        for (uint32_t kt = 0; kt < Kt; ++kt) {
            noc_async_read_tile(mt * Kt + kt, a, a_ptr);
            a_ptr += a_tile_bytes;
        }
        noc_async_read_barrier();
        cb_push_back(cb_a, Kt);

        for (uint32_t nt = 0; nt < Nt; ++nt) {
            cb_reserve_back(cb_b, Kt);
            uint32_t b_ptr = get_write_ptr(cb_b);
            for (uint32_t kt = 0; kt < Kt; ++kt) {
                noc_async_read_tile(kt * Nt + nt, b, b_ptr);
                b_ptr += b_tile_bytes;
            }
            noc_async_read_barrier();
            cb_push_back(cb_b, Kt);
        }
    }
}
