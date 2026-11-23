// fuse_diamond reader (BRISC): streams the 1024 float32 tiles of input a from DRAM into CB 0.
// Runtime args: [num_tiles, a_addr]. Compile-time args: TensorAccessorArgs of a.
// NOT FROM TOOL: the Alloy tool covers only compute-side tile calls; data-movement spellings are from memory.
#include "dataflow_api.h"        // NOT FROM TOOL: may be "api/dataflow/dataflow_api.h" in 0.63
#include "tensor_accessor.h"     // NOT FROM TOOL: header name for TensorAccessor in 0.63

void kernel_main() {
    const uint32_t num_tiles = get_arg_val<uint32_t>(0);
    const uint32_t a_addr = get_arg_val<uint32_t>(1);

    constexpr uint32_t cb_a = tt::CBIndex::c_0;
    const uint32_t tile_bytes = get_tile_size(cb_a);

    constexpr auto a_args = TensorAccessorArgs<0>();
    const auto a = TensorAccessor(a_args, a_addr, tile_bytes);

    for (uint32_t i = 0; i < num_tiles; ++i) {
        cb_reserve_back(cb_a, 1);
        noc_async_read_tile(i, a, get_write_ptr(cb_a));
        noc_async_read_barrier();
        cb_push_back(cb_a, 1);
    }
}
