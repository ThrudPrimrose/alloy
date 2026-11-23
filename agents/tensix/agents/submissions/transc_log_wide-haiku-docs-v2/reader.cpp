// SPDX-License-Identifier: Apache-2.0
// transc_log_wide: reader (BRISC). Reads input tiles of x from DRAM into CB 0.

#include <cstdint>

void kernel_main() {
    const uint32_t n_tiles = get_arg_val<uint32_t>(0);
    const uint32_t in0_addr = get_arg_val<uint32_t>(1);

    constexpr uint32_t cb_in0 = tt::CBIndex::c_0;
    const uint32_t tile_size_bytes = get_tile_size(cb_in0);

    constexpr auto in0_args = TensorAccessorArgs<0>();
    const auto in0 = TensorAccessor(in0_args, in0_addr, tile_size_bytes);

    for (uint32_t i = 0; i < n_tiles; i++) {
        cb_reserve_back(cb_in0, 1);
        const uint32_t l1_addr = get_write_ptr(cb_in0);
        noc_async_read_tile(i, in0, l1_addr);
        noc_async_read_barrier();
        cb_push_back(cb_in0, 1);
    }
}
