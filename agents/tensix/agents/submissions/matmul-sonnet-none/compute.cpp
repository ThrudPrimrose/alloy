#include <stdint.h>
#include "compute_kernel_api/matmul.h"
#include "compute_kernel_api/tile_move_copy.h"

constexpr uint32_t BLK = 4;  // fp32 dest holds 4 tiles per half

static inline void matmul_body() {
    const uint32_t Mt = get_arg_val<uint32_t>(0);
    const uint32_t Kt = get_arg_val<uint32_t>(1);
    const uint32_t Nt = get_arg_val<uint32_t>(2);

    constexpr uint32_t cb_a = 0;
    constexpr uint32_t cb_b = 1;
    constexpr uint32_t cb_c = 16;

    mm_init(cb_a, cb_b, cb_c);

    cb_wait_front(cb_b, Kt * Nt);  // whole B resident
    for (uint32_t i = 0; i < Mt; ++i) {
        cb_wait_front(cb_a, Kt);
        for (uint32_t j0 = 0; j0 < Nt; j0 += BLK) {
            const uint32_t n = (Nt - j0 < BLK) ? (Nt - j0) : BLK;
            tile_regs_acquire();
            for (uint32_t k = 0; k < Kt; ++k) {
                for (uint32_t jj = 0; jj < n; ++jj) {
                    matmul_tiles(cb_a, cb_b, k, k * Nt + j0 + jj, jj);
                }
            }
            tile_regs_commit();
            cb_reserve_back(cb_c, n);
            tile_regs_wait();
            for (uint32_t jj = 0; jj < n; ++jj) {
                pack_tile(jj, cb_c);
            }
            tile_regs_release();
            cb_push_back(cb_c, n);
        }
        cb_pop_front(cb_a, Kt);
    }
}

#ifdef MAIN
namespace NAMESPACE {
void MAIN { matmul_body(); }
}  // namespace NAMESPACE
#else
void kernel_main() { matmul_body(); }
#endif
