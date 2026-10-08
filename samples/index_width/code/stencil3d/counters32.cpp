/* DaCe AUTO-GENERATED FILE. DO NOT MODIFY */
#include <dace/dace.h>
#include "../../include/hash.h"

struct stencil3d_counters32_state_t {

};

static DACE_HDFI constexpr int64_t a_idx(int64_t __d0, int64_t __d1, int64_t __d2, int64_t K, int64_t M) { return ((((K * M) * __d0) + (K * __d1)) + __d2); }
static DACE_HDFI constexpr int64_t out_idx(int64_t __d0, int64_t __d1, int64_t __d2, int64_t K, int64_t M) { return ((((K * M) * __d0) + (K * __d1)) + __d2); }
void __program_stencil3d_counters32_internal(stencil3d_counters32_state_t*__state, double * __restrict__ a, double * __restrict__ out, int64_t K, int64_t M, int64_t N, int64_t T)
{


    for (int32_t _ = 0; (_ < T); _ = (_ + 1)) {

        #pragma omp parallel for
        for (int32_t i = 1; i < (N - 1); i += 1) {
            for (int32_t j = 1; j < (M - 1); j += 1) {
                for (int32_t k = 1; k < (K - 1); k += 1) {
                    double a_index;
                    double a_index_0;
                    double a_slice_plus_a_slice;
                    double a_index_1;
                    double a_slice_a_slice_plus_a_slice;
                    double a_index_2;
                    double a_slice_a_slice_a_slice_plus_a_slice;
                    double a_index_3;
                    double a_slice_a_slice_a_slice_a_slice_plus_a_slice;
                    double a_index_4;
                    double a_slice_a_slice_a_slice_a_slice_a_slice_plus_a_slice;
                    double a_index_5;
                    double a_slice_a_slice_a_slice_a_slice_a_slice_a_slice_plus_a_slice;
                    double out_slice;
                    a_index = a[a_idx(i, j, k, K, M)];  // copy_a_to_a_index
                    a_index_0 = a[a_idx((i - 1), j, k, K, M)];  // copy_a_to_a_index_0
                    a_slice_plus_a_slice = (a_index + a_index_0);  // _Add_
                    a_index_1 = a[a_idx((i + 1), j, k, K, M)];  // copy_a_to_a_index_1
                    a_slice_a_slice_plus_a_slice = (a_slice_plus_a_slice + a_index_1);  // _Add_
                    a_index_2 = a[a_idx(i, (j - 1), k, K, M)];  // copy_a_to_a_index_2
                    a_slice_a_slice_a_slice_plus_a_slice = (a_slice_a_slice_plus_a_slice + a_index_2);  // _Add_
                    a_index_3 = a[a_idx(i, (j + 1), k, K, M)];  // copy_a_to_a_index_3
                    a_slice_a_slice_a_slice_a_slice_plus_a_slice = (a_slice_a_slice_a_slice_plus_a_slice + a_index_3);  // _Add_
                    a_index_4 = a[a_idx(i, j, (k - 1), K, M)];  // copy_a_to_a_index_4
                    a_slice_a_slice_a_slice_a_slice_a_slice_plus_a_slice = (a_slice_a_slice_a_slice_a_slice_plus_a_slice + a_index_4);  // _Add_
                    a_index_5 = a[a_idx(i, j, (k + 1), K, M)];  // copy_a_to_a_index_5
                    a_slice_a_slice_a_slice_a_slice_a_slice_a_slice_plus_a_slice = (a_slice_a_slice_a_slice_a_slice_a_slice_plus_a_slice + a_index_5);  // _Add_
                    out_slice = (0.14285714285714285 * a_slice_a_slice_a_slice_a_slice_a_slice_a_slice_plus_a_slice);  // _Mult_
                    out[out_idx(i, j, k, K, M)] = out_slice;  // assign_39_12
                }
            }
        }

    }

}

DACE_EXPORTED void __program_stencil3d_counters32(stencil3d_counters32_state_t *__state, double * __restrict__ a, double * __restrict__ out, int64_t K, int64_t M, int64_t N, int64_t T)
{
    __program_stencil3d_counters32_internal(__state, a, out, K, M, N, T);
}

DACE_EXPORTED stencil3d_counters32_state_t *__dace_init_stencil3d_counters32(int64_t K, int64_t M, int64_t N, int64_t T)
{

    int __result = 0;
    stencil3d_counters32_state_t *__state = new stencil3d_counters32_state_t();

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

DACE_EXPORTED int __dace_exit_stencil3d_counters32(stencil3d_counters32_state_t *__state)
{

    int __err = 0;
    delete __state;
    return __err;
}
