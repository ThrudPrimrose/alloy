# Alloy report: hpcagent_bench_benchmarks_loop_level_reasoning_tsvc_2_vpv_tsvc_2_vpv_dace_vpv (profile)

```
SDFG 'hpcagent_bench_benchmarks_loop_level_reasoning_tsvc_2_vpv_tsvc_2_vpv_dace_vpv'
|- _assume_nonneg_syms
`- single_state_body
   `- hpcagent_bench_benchmarks_loop_level_reasoning_tsvc_2_vpv_tsvc_2_vpv_dace_vpv_nest_0  reads=['a', 'b'] writes=['a']
```

OpenMP runtime: libomp

## Vectorization options

| isa | scalar_remainder | masked_remainder | full_mask | sve_intrinsics |
|---|---|---|---|---|
| avx2 | gcc, clang | avx2 has no masks | avx2 has no masks | avx2 has no masks |
| avx512_256 | gcc, clang | gcc | gcc, clang | avx512_256 has no masks |
| avx512 | gcc, clang | gcc | gcc, clang | avx512 has no masks |
| neon | host lacks asimd | neon has no masks | neon has no masks | neon has no masks |
| sve | host lacks sve | host lacks sve | host lacks sve | host lacks sve |

## hpcagent_bench_benchmarks_loop_level_reasoning_tsvc_2_vpv_tsvc_2_vpv_dace_vpv_nest_0

`const double* __restrict__ b, double* __restrict__ a, int64_t LEN_1D`

libm calls: False; reduction: False; accumulation length: 1; 80 candidates, dropped: duplicate 50. Baseline (matrix default): 1.606 [1.525, 1.663] ms.

Pruned (no multiply feeds an add): c_gcc_contract_default_none, c_clang_contract_default_none, c_icx_contract_default_none, c_nvhpc_contract_default_none, cpp_gcc_contract_default_none, cpp_clang_contract_default_none, cpp_icx_contract_default_none, cpp_nvhpc_contract_default_none
Pruned (no division): c_gcc_reciprocal_default_none, c_gcc_reciprocal_default_none_serial, c_clang_reciprocal_default_none, c_clang_reciprocal_default_none_serial, c_icx_reciprocal_default_none, c_icx_reciprocal_default_none_serial, c_nvhpc_reciprocal_default_none, c_nvhpc_reciprocal_default_none_serial, cpp_gcc_reciprocal_default_none, cpp_gcc_reciprocal_default_none_serial, cpp_clang_reciprocal_default_none, cpp_clang_reciprocal_default_none_serial, cpp_icx_reciprocal_default_none, cpp_icx_reciprocal_default_none_serial, cpp_nvhpc_reciprocal_default_none, cpp_nvhpc_reciprocal_default_none_serial
Pruned (no libm or sqrt call): c_gcc_noerrno_default_none, c_clang_noerrno_default_none, c_icx_noerrno_default_none, c_nvhpc_noerrno_default_none, cpp_gcc_noerrno_default_none, cpp_clang_noerrno_default_none, cpp_icx_noerrno_default_none, cpp_nvhpc_noerrno_default_none

```
SDFG 'hpcagent_bench_benchmarks_loop_level_reasoning_tsvc_2_vpv_tsvc_2_vpv_dace_vpv_nest_0'
`- block
   `- single_state_body_map  [_loop_it_0=0:LEN_1D]  reads=['a', 'b'] writes=['a']
```

| rank | candidate | config | verified | screen ms | final ms | speedup | predicted cycles/elem | vectorized | masked ops | first missed |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | c_gcc_strict_default_none_avx512_256 | gcc_strict_default_none_avx512_256 | exact | 1.552 [1.516, 2.055] | 1.064 [1.036, 1.217] | 1.03x | - | 1 | 0 |  |
| 2 | c_gcc_strict_default_none_avx512_full_mask | gcc_strict_default_none_avx512_full_mask | exact | 1.556 [1.490, 1.750] | 1.067 [1.033, 1.148] | 1.03x | - | 1 | 4 | not vectorized: vectorization is not profitable. |
| 3 | c_clang_strict_default_none_avx512_256_full_mask | clang_strict_default_none_avx512_256_full_mask | exact | 1.558 [1.528, 1.656] | 1.082 [1.045, 1.112] | 1.03x | - | 1 | 3 |  |
| 4 | c_gcc_strict_default_none_avx512_256_masked_remainder | gcc_strict_default_none_avx512_256_masked_remainder | exact | 1.560 [1.477, 1.808] | - | 1.03x | - | 1 | 4 |  |
| 5 | c_clang_strict_default_none_avx2 | clang_strict_default_none_avx2 | exact | 1.560 [1.514, 1.708] | - | 1.03x | - | 1 | 0 |  |

## Verdict

| scope | chosen | gcc_strict_default_none_native | gcc_strict_default_none_avx2 | gcc_strict_default_none_avx512_256 | gcc_strict_default_none_avx512 | gcc_strict_default_none_native_scalar_remainder | gcc_strict_default_none_avx512_256_masked_remainder | gcc_strict_default_none_avx512_masked_remainder | gcc_strict_default_none_avx512_256_full_mask | gcc_strict_default_none_avx512_full_mask | gcc_strict_default_none_native_serial | clang_strict_default_none_native | clang_strict_default_none_avx2 | clang_strict_default_none_avx512_256 | clang_strict_default_none_avx512 | clang_strict_default_none_native_scalar_remainder | clang_strict_default_none_avx512_256_full_mask | clang_strict_default_none_avx512_full_mask | clang_strict_default_none_native_serial | icx_strict_default_none_native | icx_strict_default_none_avx2 | icx_strict_default_none_avx512_256 | icx_strict_default_none_avx512 | icx_strict_no_vec_none_native | icx_strict_default_none_native_serial | nvhpc_strict_default_none_native | nvhpc_strict_default_none_avx2 | nvhpc_strict_no_vec_none_native | nvhpc_strict_default_none_native_serial | gcc_contract_default_none_native | gcc_reciprocal_default_none_native | gcc_noerrno_default_none_native | gcc_reciprocal_default_none_native_serial | clang_contract_default_none_native | clang_reciprocal_default_none_native | clang_noerrno_default_none_native | clang_reciprocal_default_none_native_serial | icx_contract_default_none_native | icx_reciprocal_default_none_native | icx_noerrno_default_none_native | icx_reciprocal_default_none_native_serial | nvhpc_contract_default_none_native | nvhpc_reciprocal_default_none_native | nvhpc_noerrno_default_none_native | nvhpc_reciprocal_default_none_native_serial |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hpcagent_bench_benchmarks_loop_level_reasoning_tsvc_2_vpv_tsvc_2_vpv_dace_vpv_nest_0 | c_gcc_strict_default_none | 1.606 (1.00x) | 1.568 (1.02x) | 1.552 (1.03x) | duplicate | 1.563 (1.03x) | 1.560 (1.03x) | 1.561 (1.03x) | 1.564 (1.03x) | 1.556 (1.03x) | 1.940 (0.83x) | 1.568 (1.02x) | 1.560 (1.03x) | duplicate | duplicate | duplicate | 1.558 (1.03x) | 1.568 (1.02x) | 1.894 (0.85x) | 1.578 (1.02x) | 1.577 (1.02x) | duplicate | duplicate | 1.612 (1.00x) | 1.862 (0.86x) | 1.564 (1.03x) | 1.592 (1.01x) | 1.633 (0.98x) | 1.848 (0.87x) | pruned: no multiply feeds an add | pruned: no division | pruned: no libm or sqrt call | pruned: no division | pruned: no multiply feeds an add | pruned: no division | pruned: no libm or sqrt call | pruned: no division | pruned: no multiply feeds an add | pruned: no division | pruned: no libm or sqrt call | pruned: no division | pruned: no multiply feeds an add | pruned: no division | pruned: no libm or sqrt call | pruned: no division |

Program at {'LEN_1D': 2097152}: DaCe default 2.824 [2.479, 3.071] ms, Alloy 2.753 [2.118, 3.106] ms (pass), speedup 1.03x.

Build (`best/`, `make` runs these):

```
gcc -std=c23 -O3 -march=native -fPIC -fopenmp -ffp-contract=off -fexcess-precision=standard -g1 -c scopes/hpcagent_bench_benchmarks_loop_level_reasoning_tsvc_2_vpv_tsvc_2_vpv_dace_vpv_nest_0.c -o hpcagent_bench_benchmarks_loop_level_reasoning_tsvc_2_vpv_tsvc_2_vpv_dace_vpv_nest_0.o
gcc -std=c23 -O3 -fPIC -shared program.c -o libhpcagent_bench_benchmarks_loop_level_reasoning_tsvc_2_vpv_tsvc_2_vpv_dace_vpv.so libhpcagent_bench_benchmarks_loop_level_reasoning_tsvc_2_vpv_tsvc_2_vpv_dace_vpv_nest_0.a -L/usr/lib/gcc/x86_64-linux-gnu/15 -lgomp -Wl,-rpath,/usr/lib/gcc/x86_64-linux-gnu/15 -Wl,--enable-new-dtags
```
