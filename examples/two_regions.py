# Copyright 2026 ETH Zurich and the Alloy authors.
"""Two regions: a libm-bound elementwise map, then a sum reduction."""

import numpy as np

import dace

N = dace.symbol("N", dace.int64)


@dace.program
def two_regions(a: dace.float64[N], b: dace.float64[N], total: dace.float64[1]):
    for i in dace.map[0:N]:
        b[i] = np.sin(a[i]) * 2.0
    total[0] = np.sum(b)
