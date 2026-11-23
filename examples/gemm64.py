# Copyright 2026 ETH Zurich and the Alloy authors.
"""The paper's running example as a program: PolyBench gemm, C = alpha A B + beta C, at 64 x 64 x 64 (gemm64.yaml)."""

import dace

NI, NJ, NK = (dace.symbol(s, dace.int64) for s in ("NI", "NJ", "NK"))


@dace.program
def gemm64(
    alpha: dace.float32, beta: dace.float32, C: dace.float32[NI, NJ], A: dace.float32[NI, NK], B: dace.float32[NK, NJ]
) -> None:
    C[:] = alpha * A @ B + beta * C
