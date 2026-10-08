/* DaCe AUTO-GENERATED FILE. DO NOT MODIFY */
#include <dace/dace.h>
#include "../../include/hash.h"

struct stencil2d_all32_state_t {

};

static DACE_HDFI constexpr int32_t a_idx(int32_t __d0, int32_t __d1, int32_t M) { return ((M * __d0) + __d1); }
static DACE_HDFI constexpr int32_t out_idx(int32_t __d0, int32_t __d1, int32_t M) { return ((M * __d0) + __d1); }
void __program_stencil2d_all32_internal(stencil2d_all32_state_t*__state, double * __restrict__ a, double * __restrict__ out, int64_t M, int64_t N, int64_t T)
{


    for (int32_t _ = 0; (_ < T); _ = (_ + 1)) {

        #pragma omp parallel for
        for (int32_t i = 1; i < (N - 1); i += 1) {
            for (int32_t j = 1; j < (M - 1); j += 1) {
                double a_index;
                double a_index_0;
                double a_slice_plus_a_slice;
                double a_index_1;
                double a_slice_a_slice_plus_a_slice;
                double a_index_2;
                double a_slice_a_slice_a_slice_plus_a_slice;
                double a_index_3;
                double a_slice_a_slice_a_slice_a_slice_plus_a_slice;
                double out_slice;
                a_index = a[a_idx(i, j, M)];  // copy_a_to_a_index
                a_index_0 = a[a_idx((i - 1), j, M)];  // copy_a_to_a_index_0
                a_slice_plus_a_slice = (a_index + a_index_0);  // _Add_
                a_index_1 = a[a_idx((i + 1), j, M)];  // copy_a_to_a_index_1
                a_slice_a_slice_plus_a_slice = (a_slice_plus_a_slice + a_index_1);  // _Add_
                a_index_2 = a[a_idx(i, (j - 1), M)];  // copy_a_to_a_index_2
                a_slice_a_slice_a_slice_plus_a_slice = (a_slice_a_slice_plus_a_slice + a_index_2);  // _Add_
                a_index_3 = a[a_idx(i, (j + 1), M)];  // copy_a_to_a_index_3
                a_slice_a_slice_a_slice_a_slice_plus_a_slice = (a_slice_a_slice_a_slice_plus_a_slice + a_index_3);  // _Add_
                out_slice = (0.2 * a_slice_a_slice_a_slice_a_slice_plus_a_slice);  // _Mult_
                out[out_idx(i, j, M)] = out_slice;  // assign_32_12
            }
        }

    }

}

DACE_EXPORTED void __program_stencil2d_all32(stencil2d_all32_state_t *__state, double * __restrict__ a, double * __restrict__ out, int64_t M, int64_t N, int64_t T)
{
    __program_stencil2d_all32_internal(__state, a, out, M, N, T);
}

DACE_EXPORTED stencil2d_all32_state_t *__dace_init_stencil2d_all32(int64_t M, int64_t N, int64_t T)
{

    int __result = 0;
    stencil2d_all32_state_t *__state = new stencil2d_all32_state_t();

    if (__result) {
        delete __state;
        return nullptr;
    }

    if (__result) {
        delete __state;
        return nullptr;
    }

    return __state;
}

DACE_EXPORTED int __dace_exit_stencil2d_all32(stencil2d_all32_state_t *__state)
{

    int __err = 0;
    delete __state;
    return __err;
}
