# Copyright 2026 ETH Zurich and the Alloy authors.
"""Kernels with a known accumulation length: K for a matmul, N for a row sum, 1 for an elementwise map."""

import dace
import numpy as np

M = dace.symbol("M", dace.int64)
N = dace.symbol("N", dace.int64)
K = dace.symbol("K", dace.int64)


@dace.program
def square_free_matmul(a: dace.float64[M, K], b: dace.float64[K, N], c: dace.float64[M, N]):
    for i, j, k in dace.map[0:M, 0:N, 0:K]:
        c[i, j] += a[i, k] * b[k, j]


@dace.program
def square_matmul(a: dace.float64[N, N], b: dace.float64[N, N], c: dace.float64[N, N]):
    for i, j, k in dace.map[0:N, 0:N, 0:N]:
        c[i, j] += a[i, k] * b[k, j]


@dace.program
def row_sum(a: dace.float64[M, N], out: dace.float64[M]):
    out[:] = np.sum(a, axis=1)


@dace.program
def scale(a: dace.float64[N], out: dace.float64[N]):
    for i in dace.map[0:N]:
        out[i] = 2.0 * a[i]
