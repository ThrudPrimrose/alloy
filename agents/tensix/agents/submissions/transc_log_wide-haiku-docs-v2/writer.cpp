// SPDX-License-Identifier: Apache-2.0
// transc_log_wide: writer (NCRISC). Writes result tiles from CB 16 to DRAM.

#include <cstdint>

void kernel_main() {
    const uint32_t n_tiles = get_arg_val<uint32_t>(0);
    const uint32_t out_addr = get_arg_val<uint32_t>(1);

    constexpr uint32_t cb_out0 = tt::CBIndex::c_16;
    const uint32_t tile_size_bytes = get_tile_size(cb_out0);

    constexpr auto out0_args = TensorAccessorArgs<0>();
    const auto out0 = TensorAccessor(out0_args, out_addr, tile_size_bytes);

    for (uint32_t i = 0; i < n_tiles; i++) {
        cb_wait_front(cb_out0, 1);
        const uint32_t l1_addr = get_read_ptr(cb_out0);
        noc_async_write_tile(i, out0, l1_addr);
        noc_async_write_barrier();
        cb_pop_front(cb_out0, 1);
    }
}
