/* DaCe AUTO-GENERATED FILE. DO NOT MODIFY */
#include <dace/dace.h>
#include "../../include/hash.h"

struct row_gather_counters32_state_t {

};

static DACE_HDFI constexpr int64_t table_idx(int64_t __d0, int64_t __d1, int64_t M) { return ((M * __d0) + __d1); }
static DACE_HDFI constexpr int64_t out_idx(int64_t __d0, int64_t __d1, int64_t M) { return ((M * __d0) + __d1); }
inline void kernels_row_gather_1_0_2(row_gather_counters32_state_t *__state, const int64_t* __restrict__ idx, const double* __restrict__ table, double* __restrict__ out, int64_t M, int64_t i, int64_t j) {
    int64_t idx_index;


    idx_index = idx[i];
    {
        double out_slice;

        out_slice = table[table_idx(idx_index, j, M)];  // copy_table_to_out_slice
        out[out_idx(i, j, M)] = out_slice;  // assign_18_12

    }
}

void __program_row_gather_counters32_internal(row_gather_counters32_state_t*__state, int64_t * __restrict__ idx, double * __restrict__ out, double * __restrict__ table, int64_t M, int64_t N, int64_t R, int64_t T)
{


    for (int32_t _ = 0; (_ < T); _ = (_ + 1)) {

        #pragma omp parallel for
        for (int32_t i = 0; i < N; i += 1) {
            for (int32_t j = 0; j < M; j += 1) {
                kernels_row_gather_1_0_2(__state, &idx[0], &table[0], &out[0], M, i, j);
            }
        }

    }

}

DACE_EXPORTED void __program_row_gather_counters32(row_gather_counters32_state_t *__state, int64_t * __restrict__ idx, double * __restrict__ out, double * __restrict__ table, int64_t M, int64_t N, int64_t R, int64_t T)
{
    __program_row_gather_counters32_internal(__state, idx, out, table, M, N, R, T);
}

DACE_EXPORTED row_gather_counters32_state_t *__dace_init_row_gather_counters32(int64_t M, int64_t N, int64_t T)
{

    int __result = 0;
    row_gather_counters32_state_t *__state = new row_gather_counters32_state_t();

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

DACE_EXPORTED int __dace_exit_row_gather_counters32(row_gather_counters32_state_t *__state)
{

    int __err = 0;
    delete __state;
    return __err;
}
