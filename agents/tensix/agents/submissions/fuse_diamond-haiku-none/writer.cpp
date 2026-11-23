// fuse_diamond writer (NCRISC): drains CB 16 to the output tensor in DRAM.
#include "api/dataflow/dataflow_api.h"
#include "api/tensor/tensor_accessor.h"

void kernel_main() {
    const uint32_t num_tiles = get_arg_val<uint32_t>(0);
    const uint32_t out_addr = get_arg_val<uint32_t>(1);

    constexpr uint32_t cb_out = 16;
    constexpr auto out_args = TensorAccessorArgs<0>();
    const auto out = TensorAccessor(out_args, out_addr, get_tile_size(cb_out));

    for (uint32_t i = 0; i < num_tiles; ++i) {
        cb_wait_front(cb_out, 1);
        const uint32_t l1_addr = get_read_ptr(cb_out);
        noc_async_write_tile(i, out, l1_addr);
        noc_async_write_barrier();
        cb_pop_front(cb_out, 1);
    }
}
