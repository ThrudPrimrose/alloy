# Copyright 2026 ETH Zurich and the Alloy authors.
"""Copies inside a kernel as iDMA transfers (``flex_dma_async_1d`` / ``_2d``), issued by the DMA core.

The transfer is asynchronous: the ``DmaWait`` node that :mod:`alloy.softhiergen.passes` places after it completes it.
"""

from typing import ClassVar

import dace
from dace import data, library, symbolic
from dace.libraries.standard.nodes.copy import CopyLibraryNode
from dace.libraries.standard.nodes.copy.common import INPUT_CONNECTOR_NAME, OUTPUT_CONNECTOR_NAME
from dace.libraries.tileops import MaskedCopyLibraryNode
from dace.memlet import Memlet
from dace.sdfg.graph import MultiConnectorEdge
from dace.transformation.transformation import ExpandTransformation

from alloy.softhiergen.library.common import DMA_CORE, LoweringError, edge_desc, guarded_tasklet, pointer_to

IMPLEMENTATION = "SoftHierDMA"

#: One side of a transfer in elements: rows of ``row`` contiguous elements, ``stride`` apart.
Rows = tuple[int, int, int]


def rows_of(edge: MultiConnectorEdge[Memlet], desc: data.Data) -> Rows | None:
    """The rows one side of a copy moves, or ``None`` when it is not one run or one stack of equal rows."""
    if not isinstance(desc, data.Array):
        return None
    if edge.data.subset.is_contiguous_subset(desc):  # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess] -- DaCe's annotation
        return 1, int(edge.data.subset.num_elements_exact()), 0  # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess] -- DaCe's annotation
    subset = edge.data.subset
    if any(tile != 1 for tile in subset.tile_sizes):  # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess] -- DaCe's annotation
        return None
    # A step of a range multiplies its stride: X[0:16:2, :] is rows two strides apart; a step in the row is no run
    dims = [
        (
            int(size),
            int(symbolic.evaluate(stride * step, {})) if symbolic.issymbolic(stride * step) else int(stride * step),
        )
        for size, (_, _, step), stride in zip(subset.size_exact(), subset.ranges, desc.strides)  # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess] -- DaCe's annotation
        if size != 1
    ]
    if len(dims) == 2 and dims[1][1] == 1:
        return dims[0][0], dims[1][0], dims[0][1]
    return None


def dma_call(node: CopyLibraryNode, state: dace.SDFGState, sdfg: dace.SDFG) -> str:
    """The iDMA call of a copy node; raises when the copy is no 1D or 2D transfer."""
    if isinstance(node, MaskedCopyLibraryNode) and node.has_mask:
        raise LoweringError(f"{node.label}: a masked copy has no iDMA lowering")
    src = next(e for e in state.in_edges(node) if e.dst_conn == INPUT_CONNECTOR_NAME)
    dst = next(e for e in state.out_edges(node) if e.src_conn == OUTPUT_CONNECTOR_NAME)
    src_desc, dst_desc = edge_desc(sdfg, src), edge_desc(sdfg, dst)
    if src_desc.dtype != dst_desc.dtype:
        raise LoweringError(f"{node.label}: iDMA does not convert {src_desc.dtype} to {dst_desc.dtype}")
    src_rows, dst_rows = rows_of(src, src_desc), rows_of(dst, dst_desc)
    if src_rows is None or dst_rows is None:
        raise LoweringError(f"{node.label}: {src.data} -> {dst.data} is no 1D or 2D transfer")
    size = src_desc.dtype.bytes
    if src_rows[0] * src_rows[1] != dst_rows[0] * dst_rows[1]:
        raise LoweringError(f"{node.label}: the two sides move different element counts")
    addresses = f"dsh_addr({OUTPUT_CONNECTOR_NAME}), dsh_addr({INPUT_CONNECTOR_NAME})"
    if src_rows[0] == 1 and dst_rows[0] == 1:
        return f"dsh_dma_1d({addresses}, {src_rows[1] * size});"
    if src_rows[0] == 1:
        src_rows = dst_rows[0], dst_rows[1], dst_rows[1]
    if dst_rows[0] == 1:
        dst_rows = src_rows[0], src_rows[1], src_rows[1]
    if src_rows[:2] != dst_rows[:2]:
        raise LoweringError(f"{node.label}: the rows of the two sides differ, {src_rows} and {dst_rows}")
    rows, row, _ = src_rows
    return f"dsh_dma_2d({addresses}, {row * size}, {dst_rows[2] * size}, {src_rows[2] * size}, {rows});"


def expand(node: CopyLibraryNode, state: dace.SDFGState, sdfg: dace.SDFG) -> dace.nodes.Tasklet:
    src = next(e for e in state.in_edges(node) if e.dst_conn == INPUT_CONNECTOR_NAME)
    dst = next(e for e in state.out_edges(node) if e.src_conn == OUTPUT_CONNECTOR_NAME)
    return guarded_tasklet(
        f"{node.label}_dma",
        {INPUT_CONNECTOR_NAME: pointer_to(sdfg, src)},
        {OUTPUT_CONNECTOR_NAME: pointer_to(sdfg, dst)},
        DMA_CORE,
        dma_call(node, state, sdfg),
    )


@library.register_expansion(CopyLibraryNode, IMPLEMENTATION)  # pyright: ignore[reportArgumentType] -- DaCe's annotation
class ExpandCopyDMA(ExpandTransformation):
    environments: ClassVar[list[type]] = []

    @staticmethod
    def expansion(node: CopyLibraryNode, parent_state: dace.SDFGState, parent_sdfg: dace.SDFG) -> dace.nodes.Tasklet:
        return expand(node, parent_state, parent_sdfg)


@library.register_expansion(MaskedCopyLibraryNode, IMPLEMENTATION)  # pyright: ignore[reportArgumentType] -- DaCe's annotation
class ExpandMaskedCopyDMA(ExpandTransformation):
    environments: ClassVar[list[type]] = []

    @staticmethod
    def expansion(node: CopyLibraryNode, parent_state: dace.SDFGState, parent_sdfg: dace.SDFG) -> dace.nodes.Tasklet:
        return expand(node, parent_state, parent_sdfg)
