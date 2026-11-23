# Brief (identical for every configuration; only the "Help" section differs: fairness audit F5)

You write one Tenstorrent kernel for the task in SPEC.md, section "{KERNEL}". Read SPEC.md first: it fixes the
deliverables, the host contract, the inputs and the tolerance. Write the files into this folder.

There is no card and no tt-metal installation here: you cannot compile or run. Write carefully. Put every API
spelling you are unsure of in NOTES.md, and anything you would ask the owner in QUESTIONS.md instead of guessing.

Limits: {LIMITS} (the same for every configuration and model; a run that reaches a limit ends there).

## tt-metal 0.63 primer (the card's version; the same for every configuration)

A skeleton that builds and runs on the card. Paths are tt-metal 0.63's: there is no `api/compute/...`,
`tt_metal/tt_metal.hpp` or `tensor_accessor.h` include in a kernel.

    // reader.cpp / writer.cpp (data movement)
    #include <stdint.h>
    #include "dataflow_api.h"
    void kernel_main() {
        uint32_t n = get_arg_val<uint32_t>(0), start = get_arg_val<uint32_t>(1);
        constexpr auto args = TensorAccessorArgs<0>();   // next array: TensorAccessorArgs<args.next_compile_time_args_offset()>()
        const auto a = TensorAccessor(args, get_arg_val<uint32_t>(2), get_tile_size(0));
        for (uint32_t i = 0; i < n; ++i) {               // reader; the writer mirrors it with CB 16,
            cb_reserve_back(0, 1);                       // cb_wait_front / noc_async_write_tile(start + i, s,
            noc_async_read_tile(start + i, a, get_write_ptr(0));   // get_read_ptr(16)) / noc_async_write_barrier /
            noc_async_read_barrier();                    // cb_pop_front
            cb_push_back(0, 1);
        }
    }

    // compute.cpp
    #include <stdint.h>
    #include "compute_kernel_api/common.h"
    #include "compute_kernel_api/tile_move_copy.h"
    #include "compute_kernel_api/eltwise_unary/eltwise_unary.h"   // init_sfpu; each op has its own header too
    namespace NAMESPACE {
    void MAIN {
        uint32_t n = get_arg_val<uint32_t>(0);
        init_sfpu(0, 16);                                 // input CB, output CB
        for (uint32_t i = 0; i < n; ++i) {
            cb_wait_front(0, 1);
            tile_regs_acquire();
            copy_tile_to_dst_init_short(0);
            copy_tile(0, 0, 0);                           // CB 0, tile 0 -> DST 0
            /* the op's init and call on DST 0 */
            tile_regs_commit();
            cb_pop_front(0, 1);
            cb_reserve_back(16, 1);
            tile_regs_wait();
            pack_tile(0, 16);                             // DST 0 -> CB 16
            tile_regs_release();
            cb_push_back(16, 1);
        }
    }
    }  // namespace NAMESPACE

## Help

{HELP}
