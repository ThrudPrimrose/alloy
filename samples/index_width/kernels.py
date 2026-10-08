# Copyright 2026 ETH Zurich and the Alloy authors.
"""Kernels whose flat offsets run through the generated ``<array>_idx`` helpers. ``T`` repeats the body
inside the program so a cache-resident size is not drowned by the Python call."""

import dace

N = dace.symbol("N", dace.int64)
M = dace.symbol("M", dace.int64)
K = dace.symbol("K", dace.int64)
R = dace.symbol("R", dace.int64)
T = dace.symbol("T", dace.int64)


@dace.program
def row_gather(table: dace.float64[R, M], idx: dace.int64[N], out: dace.float64[N, M]):
    for _ in range(T):
        for i, j in dace.map[0:N, 0:M]:
            out[i, j] = table[idx[i], j]


@dace.program
def element_gather(table: dace.float64[R], idx: dace.int64[N], out: dace.float64[N]):
    for _ in range(T):
        for i in dace.map[0:N]:
            out[i] = table[idx[i]]


@dace.program
def stencil2d(a: dace.float64[N, M], out: dace.float64[N, M]):
    for _ in range(T):
        for i, j in dace.map[1 : N - 1, 1 : M - 1]:
            out[i, j] = 0.2 * (a[i, j] + a[i - 1, j] + a[i + 1, j] + a[i, j - 1] + a[i, j + 1])


@dace.program
def stencil3d(a: dace.float64[N, M, K], out: dace.float64[N, M, K]):
    for _ in range(T):
        for i, j, k in dace.map[1 : N - 1, 1 : M - 1, 1 : K - 1]:
            out[i, j, k] = (1.0 / 7.0) * (
                a[i, j, k]
                + a[i - 1, j, k]
                + a[i + 1, j, k]
                + a[i, j - 1, k]
                + a[i, j + 1, k]
                + a[i, j, k - 1]
                + a[i, j, k + 1]
            )
