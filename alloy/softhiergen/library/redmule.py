# Copyright 2026 ETH Zurich and the Alloy authors.
"""``TileMMA`` on RedMulE: ``c (M x N) += a (M x K) b (K x N)``, float16, packed row-major in TCDM.

The compute core configures and triggers RedMulE; the ``RedmuleWait`` node after it completes the product. ``beta = 0``
zeroes ``c`` with Spatz first, on the same core.
"""

from typing import ClassVar

import dace
from dace import dtypes, library
from dace.libraries.tileops import TileMMA
from dace.sdfg import nodes
from dace.transformation.transformation import ExpandTransformation

from alloy.softhiergen.library.common import (
    COMPUTE_CORE,
    LoweringError,
    edge_desc,
    guarded_tasklet,
    in_edges,
    out_edges,
    pointer_to,
    tcdm_tile_reason,
)

IMPLEMENTATION = "SoftHierRedMulE"


@library.register_expansion(TileMMA, IMPLEMENTATION)  # pyright: ignore[reportArgumentType] -- DaCe's annotation
class ExpandMMARedMulE(ExpandTransformation):
    environments: ClassVar[list[type]] = []

    @staticmethod
    def expansion(node: TileMMA, parent_state: dace.SDFGState, parent_sdfg: dace.SDFG) -> nodes.Tasklet:
        node.validate(parent_sdfg, parent_state)
        if node.alpha != 1 or node.beta not in (0, 1):
            raise LoweringError(f"{node.label}: RedMulE computes c = a @ b (+ c), alpha 1 and beta 0 or 1")
        ins, out = in_edges(parent_state, node), out_edges(parent_state, node)["_c"]
        # validate() already requires one dtype for _a, _b and _c; _cin shares _c's container
        if edge_desc(parent_sdfg, out).dtype != dtypes.float16:
            raise LoweringError(f"{node.label}: RedMulE takes float16 operands")
        if "_cin" in ins and (ins["_cin"].data.data, ins["_cin"].data.subset) != (out.data.data, out.data.subset):
            raise LoweringError(f"{node.label}: RedMulE accumulates in place; _cin and _c must be the same container")
        operands = {conn: edge for conn, edge in ins.items() if conn in ("_a", "_b", "_cin")}
        for conn, edge in (*operands.items(), ("_c", out)):
            reason = tcdm_tile_reason(parent_sdfg, edge, f"{node.label}: {conn}")
            if reason is not None:
                raise LoweringError(reason)
        m, k, n = node.widths
        # RedMulE reads c through its own TCDM port: the fill's vector stores must have landed
        zero = f"dsh_rvv_fill_f16(_c, (dsh_f16)0, {m * n});\ndsh_vfence();\n" if node.beta == 0 else ""
        return guarded_tasklet(
            f"{node.label}_redmule",
            {conn: pointer_to(parent_sdfg, edge) for conn, edge in operands.items()},
            {"_c": pointer_to(parent_sdfg, out)},
            COMPUTE_CORE,
            f"{zero}dsh_redmule_mma(_a, _b, _c, {m}, {k}, {n});",
        )
