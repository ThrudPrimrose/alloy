// fuse_diamond reader (BRISC): streams input tiles of `a` from DRAM into CB 0.
#include "api/dataflow/dataflow_api.h"
#include "api/tensor/tensor_accessor.h"

void kernel_main() {
    const uint32_t num_tiles = get_arg_val<uint32_t>(0);
    const uint32_t in0_addr = get_arg_val<uint32_t>(1);

    constexpr uint32_t cb_in0 = 0;
    constexpr auto in0_args = TensorAccessorArgs<0>();
    const auto in0 = TensorAccessor(in0_args, in0_addr, get_tile_size(cb_in0));

    for (uint32_t i = 0; i < num_tiles; ++i) {
        cb_reserve_back(cb_in0, 1);
        const uint32_t l1_addr = get_write_ptr(cb_in0);
        noc_async_read_tile(i, in0, l1_addr);
        noc_async_read_barrier();
        cb_push_back(cb_in0, 1);
    }
}
