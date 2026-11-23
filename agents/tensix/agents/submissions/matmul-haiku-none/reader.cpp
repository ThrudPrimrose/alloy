// Reader (BRISC): streams A and B tiles from DRAM into CB 0 and CB 1.
// Tile order matches compute: for i in Mt, for j in Nt, for k in Kt.
// A tile (i, k) has index i*Kt + k; B tile (k, j) has index k*Nt + j.
#include "dataflow_api.h"
#include "tensor_accessor.h"

void kernel_main() {
    const uint32_t Mt = get_arg_val<uint32_t>(0);
    const uint32_t Kt = get_arg_val<uint32_t>(1);
    const uint32_t Nt = get_arg_val<uint32_t>(2);
    const uint32_t a_addr = get_arg_val<uint32_t>(3);
    const uint32_t b_addr = get_arg_val<uint32_t>(4);

    constexpr uint32_t cb_a = tt::CBIndex::c_0;
    constexpr uint32_t cb_b = tt::CBIndex::c_1;

    constexpr auto a_args = TensorAccessorArgs<0>();
    constexpr auto b_args = TensorAccessorArgs<a_args.next_compile_time_args_offset()>();
    const auto a = TensorAccessor(a_args, a_addr, get_tile_size(cb_a));
    const auto b = TensorAccessor(b_args, b_addr, get_tile_size(cb_b));

    for (uint32_t i = 0; i < Mt; ++i) {
        for (uint32_t j = 0; j < Nt; ++j) {
            for (uint32_t k = 0; k < Kt; ++k) {
                cb_reserve_back(cb_a, 1);
                cb_reserve_back(cb_b, 1);
                noc_async_read_tile(i * Kt + k, a, get_write_ptr(cb_a));
                noc_async_read_tile(k * Nt + j, b, get_write_ptr(cb_b));
                noc_async_read_barrier();
                cb_push_back(cb_a, 1);
                cb_push_back(cb_b, 1);
            }
        }
    }
}
