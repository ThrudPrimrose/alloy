/* DaCe AUTO-GENERATED FILE. DO NOT MODIFY */
#include <dace/dace.h>
#include "../../include/hash.h"

struct element_gather_all32_state_t {

};

static DACE_HDFI constexpr int32_t table_idx(int32_t __d0) { return __d0; }
static DACE_HDFI constexpr int32_t out_idx(int32_t __d0) { return __d0; }
inline void kernels_element_gather_1_0_2(element_gather_all32_state_t *__state, const int64_t* __restrict__ idx, const double* __restrict__ table, double* __restrict__ out, int64_t i) {
    int64_t idx_index;


    idx_index = idx[i];
    {
        double out_slice;

        out_slice = table[table_idx(idx_index)];  // copy_table_to_out_slice
        out[out_idx(i)] = out_slice;  // assign_25_12

    }
}

void __program_element_gather_all32_internal(element_gather_all32_state_t*__state, int64_t * __restrict__ idx, double * __restrict__ out, double * __restrict__ table, int64_t N, int64_t R, int64_t T)
{


    for (int32_t _ = 0; (_ < T); _ = (_ + 1)) {

        #pragma omp parallel for
        for (int32_t i = 0; i < N; i += 1) {
            kernels_element_gather_1_0_2(__state, &idx[0], &table[0], &out[0], i);
        }

    }

}

DACE_EXPORTED void __program_element_gather_all32(element_gather_all32_state_t *__state, int64_t * __restrict__ idx, double * __restrict__ out, double * __restrict__ table, int64_t N, int64_t R, int64_t T)
{
    __program_element_gather_all32_internal(__state, idx, out, table, N, R, T);
}

DACE_EXPORTED element_gather_all32_state_t *__dace_init_element_gather_all32(int64_t N, int64_t T)
{

    int __result = 0;
    element_gather_all32_state_t *__state = new element_gather_all32_state_t();

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

DACE_EXPORTED int __dace_exit_element_gather_all32(element_gather_all32_state_t *__state)
{

    int __err = 0;
    delete __state;
    return __err;
}
