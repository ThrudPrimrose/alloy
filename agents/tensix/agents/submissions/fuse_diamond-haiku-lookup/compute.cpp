// fuse_diamond compute (TRISC): out = u * v with t = a*a, u = t + 1, v = t - 1.
// Full float32 path: copy_tile unpacks a into DST as f32 (UnpackToDestFp32 on CB 0), SFPU binary ops keep f32,
// fp32_dest_acc_en makes DST and the pack to CB 16 f32.
// DST layout per tile:
//   DST0 = a, DST1 = a, DST2 = a
//   DST0 = a*a = t,  DST1 = a*a = t   (mul_binary_tile(1, 2, 1) uses DST1 = a, DST2 = a)
//   DST0 = t + 1 = u,  DST1 = t + (-1) = v   (add_unary_tile with scalar bit patterns)
//   DST0 = u * v
// Runtime args: [num_tiles]. Scaffolding follows the tt-metal 0.6x form (NAMESPACE / MAIN, init_sfpu).
#include "compute_kernel_api.h"
#include "compute_kernel_api/common.h"                         // NOT FROM TOOL: may be redundant
#include "compute_kernel_api/tile_move_copy.h"                 // NOT FROM TOOL: copy_tile_init, copy_tile
#include "compute_kernel_api/eltwise_binary_sfpu.h"            // mul_binary_tile (tool: eltwise_binary_sfpu.h)
#include "compute_kernel_api/eltwise_unary/binop_with_scalar.h"  // NOT FROM TOOL: add_unary_tile

namespace NAMESPACE {
void MAIN {
    const uint32_t num_tiles = get_arg_val<uint32_t>(0);

    constexpr auto cb_a = tt::CBIndex::c_0;
    constexpr auto cb_out = tt::CBIndex::c_16;

    constexpr uint32_t ONE_F32 = 0x3F800000u;      // bit pattern of +1.0f (scalar operand of add_unary_tile)
    constexpr uint32_t MINUS_ONE_F32 = 0xBF800000u;  // bit pattern of -1.0f

    init_sfpu(cb_a, cb_out);
    binop_with_scalar_tile_init();                 // NOT FROM TOOL: init for add_unary_tile

    for (uint32_t i = 0; i < num_tiles; ++i) {
        cb_wait_front(cb_a, 1);
        cb_reserve_back(cb_out, 1);

        tile_regs_acquire();

        copy_tile_init(cb_a);                      // NOT FROM TOOL
        copy_tile(cb_a, 0, 0);                     // DST0 = a
        copy_tile(cb_a, 0, 1);                     // DST1 = a
        copy_tile(cb_a, 0, 2);                     // DST2 = a

        mul_binary_tile_init();
        mul_binary_tile(0, 1, 0);                  // DST0 = t
        mul_binary_tile(1, 2, 1);                  // DST1 = t

        binop_with_scalar_tile_init();
        add_unary_tile(0, ONE_F32);                // DST0 = u = t + 1
        add_unary_tile(1, MINUS_ONE_F32);          // DST1 = v = t - 1

        mul_binary_tile_init();
        mul_binary_tile(0, 1, 0);                  // DST0 = u * v

        tile_regs_commit();
        tile_regs_wait();
        pack_tile(0, cb_out);
        tile_regs_release();

        cb_push_back(cb_out, 1);
        cb_pop_front(cb_a, 1);
    }
}
}  // namespace NAMESPACE
