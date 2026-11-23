// Writer (NCRISC): writes C tiles from CB 16 to DRAM in tile order i*Nt + j.
#include "dataflow_api.h"
#include "tensor_accessor.h"

void kernel_main() {
    const uint32_t num_out_tiles = get_arg_val<uint32_t>(0);
    const uint32_t c_addr = get_arg_val<uint32_t>(1);

    constexpr uint32_t cb_c = tt::CBIndex::c_16;

    constexpr auto c_args = TensorAccessorArgs<0>();
    const auto c = TensorAccessor(c_args, c_addr, get_tile_size(cb_c));

    for (uint32_t t = 0; t < num_out_tiles; ++t) {
        cb_wait_front(cb_c, 1);
        noc_async_write_tile(t, c, get_read_ptr(cb_c));
        noc_async_write_barrier();
        cb_pop_front(cb_c, 1);
    }
}
