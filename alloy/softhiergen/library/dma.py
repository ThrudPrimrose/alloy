# Copyright 2026 ETH Zurich and the Alloy authors.
"""Copies inside a kernel as iDMA transfers (``flex_dma_async_1d`` / ``_2d``), issued by the DMA core.

The transfer is asynchronous: the ``DmaWait`` node that :mod:`alloy.softhiergen.passes` places after it completes it.
"""

import math
from typing import Any, ClassVar

import dace
import sympy
from dace import data, library, symbolic
from dace.codegen.targets.cpp import sym2cpp
from dace.libraries.standard.nodes.copy import CopyLibraryNode
from dace.libraries.standard.nodes.copy.common import INPUT_CONNECTOR_NAME, OUTPUT_CONNECTOR_NAME
from dace.libraries.tileops import MaskedCopyLibraryNode
from dace.memlet import Memlet
from dace.sdfg import nodes
from dace.sdfg.graph import MultiConnectorEdge
from dace.subsets import Range
from dace.transformation.transformation import ExpandTransformation

from alloy.softhiergen import hbm
from alloy.softhiergen.library.common import DMA_CORE, LoweringError, edge_desc, guarded_tasklet, pointer_to

IMPLEMENTATION = "SoftHierDMA"

#: One side of a transfer in elements: rows of ``row`` contiguous elements, ``stride`` apart.
Rows = tuple[int, int, int]


def rows_of(subset: Range, desc: data.Data) -> Rows | None:
    """The rows one side of a copy moves, or ``None`` when it is not one run or one stack of equal rows."""
    if not isinstance(desc, data.Array):
        return None
    if subset.is_contiguous_subset(desc):
        return 1, int(subset.num_elements_exact()), 0
    if any(tile != 1 for tile in subset.tile_sizes):
        return None
    # A step of a range multiplies its stride: X[0:16:2, :] is rows two strides apart; a step in the row is no run
    dims = [
        (
            int(size),
            int(symbolic.evaluate(stride * step, {})) if symbolic.issymbolic(stride * step) else int(stride * step),  # pyright: ignore[reportOperatorIssue] -- sympy's annotation
        )
        for size, (_, _, step), stride in zip(subset.size_exact(), subset.ranges, desc.strides)  # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess] -- DaCe's annotation
        if size != 1
    ]
    if len(dims) == 2 and dims[1][1] == 1:
        return dims[0][0], dims[1][0], dims[0][1]
    return None


def enclosing_ranges(state: dace.SDFGState, node: nodes.Node) -> dict[str, tuple[Any, Any]]:
    """The first value and the step of every map parameter around ``node``."""
    found = {}
    entry = state.entry_node(node)
    while entry is not None:
        for param, (begin, _, step) in zip(entry.map.params, entry.map.range.ranges, strict=True):  # pyright: ignore[reportAttributeAccessIssue] -- DaCe's annotation
            found[param] = (begin, step)
        entry = state.entry_node(entry)
    return found


def multiple_of(source: object, count: int, ranges: dict[str, tuple[Any, Any]]) -> bool:
    """Whether ``source`` is a multiple of ``count`` for every value the map parameters in it take."""
    expr = sympy.sympify(source)
    values = {}
    for symbol in expr.free_symbols:
        if symbol.name not in ranges:  # pyright: ignore[reportAttributeAccessIssue] -- sympy's annotation
            return False
        begin, step = ranges[symbol.name]  # pyright: ignore[reportAttributeAccessIssue] -- sympy's annotation
        values[symbol] = begin + step * sympy.Symbol(f"k_{symbol.name}", integer=True, nonnegative=True)  # pyright: ignore[reportAttributeAccessIssue] -- sympy's annotation
    terms = sympy.expand(expr.subs(values, simultaneous=True)).as_coefficients_dict()
    return all(coefficient.is_Integer and int(coefficient) % count == 0 for coefficient in terms.values())


def node_side(
    edge: MultiConnectorEdge[Memlet], desc: data.Array, state: dace.SDFGState, node: nodes.Node, sdfg: dace.SDFG
) -> tuple[str, Rows | None] | None:
    """The address and the rows of a copy's side on a placed array, if the copy provably stays in one block of every
    distributed dimension, so on one node, where it is a box of the node's share; ``None`` otherwise."""
    place, subset = desc.placement, edge.data.subset
    ranges = enclosing_ranges(state, node)
    for (begin, _, step), size, block in zip(subset.ranges, subset.size_exact(), hbm.blocks(place), strict=True):  # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess] -- DaCe's annotation
        if block is None or size == 1:
            continue
        block = int(hbm.value(block, sdfg.constants))
        if step != 1 or block % int(size) or not multiple_of(begin, int(size), ranges):
            return None
    local = [int(hbm.value(extent, sdfg.constants)) for extent in place.local_shape(desc.shape)]
    share = data.Array(desc.dtype, local[1:] if place.pages is not None else local)
    box = Range([(0, (size - 1) * step, step) for (_, _, step), size in zip(subset.ranges, subset.size_exact())])  # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess] -- DaCe's annotation
    start = [begin for begin, _, _ in subset.ranges]  # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess] -- DaCe's annotation
    node_of, offset_of = sym2cpp(place.node_of(start)), sym2cpp(place.offset_of(start, desc.shape))
    return f"dsh_addr({hbm.table_name(edge.data.data)}[{node_of}] + {offset_of})", rows_of(box, share)  # pyright: ignore[reportArgumentType] -- DaCe's annotation


def split_call(
    edge: MultiConnectorEdge[Memlet], desc: data.Array, other: str, other_rows: Rows, to_node: bool, sdfg: dace.SDFG
) -> str:
    """A copy between a placed array and the connector ``other`` as one 1D transfer per run: each row of the placed
    side is cut where a block of its last dimension ends.

    shortcut: one 1D transfer per run, issued in a loop on the DMA core; merge runs into 2D transfers when copies
    across blocks show in the cycle counts.
    """
    place, subset = desc.placement, edge.data.subset
    sizes = [int(size) for size in subset.size_exact()]  # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess] -- DaCe's annotation
    begins, steps = [begin for begin, _, _ in subset.ranges], [step for _, _, step in subset.ranges]  # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess] -- DaCe's annotation
    if steps[-1] != 1:
        raise LoweringError(f"{edge.data.data}: a step inside the row has no iDMA transfer")
    rows, row, stride = other_rows
    if rows != 1 and row != sizes[-1]:
        raise LoweringError(f"{edge.data.data}: the rows of the two sides differ ({sizes[-1]} and {row})")
    last = len(sizes) - 1
    index = [sympy.Symbol(f"__p{dim}", integer=True, nonnegative=True) for dim in range(len(sizes))]
    lines = [f"for (int __r = 0; __r < {math.prod(sizes[:-1])}; ++__r) {{"]
    inner = 1
    for dim in reversed(range(last)):
        lines.append(
            f"const int __p{dim} = {sym2cpp(begins[dim])} + (__r / {inner} % {sizes[dim]}) * {sym2cpp(steps[dim])};"
        )
        inner *= sizes[dim]
    lines += [
        f"for (int __j = 0; __j < {sizes[-1]};) {{",
        f"const int __p{last} = {sym2cpp(begins[-1])} + __j;",
        f"int __len = {sizes[-1]} - __j;",
    ]
    block = hbm.blocks(place)[-1]
    if block is not None:
        block = sym2cpp(hbm.value(block, sdfg.constants))
        lines += [f"const int __room = {block} - __p{last} % {block};", "if (__room < __len) __len = __room;"]
    node_of, offset_of = sym2cpp(place.node_of(index)), sym2cpp(place.offset_of(index, desc.shape))
    placed_address = f"dsh_addr({hbm.table_name(edge.data.data)}[{node_of}] + {offset_of})"  # pyright: ignore[reportArgumentType] -- DaCe's annotation
    other_address = f"dsh_addr({other} + __r * {stride if rows != 1 else sizes[-1]} + __j)"
    dst, src = (placed_address, other_address) if to_node else (other_address, placed_address)
    lines += [f"dsh_dma_1d({dst}, {src}, __len * {desc.dtype.bytes});", "__j += __len;", "}", "}"]
    return "\n".join(lines)


def dma_call(node: CopyLibraryNode, state: dace.SDFGState, sdfg: dace.SDFG) -> str:
    """The iDMA call of a copy node; raises when the copy is no 1D or 2D transfer."""
    if isinstance(node, MaskedCopyLibraryNode) and node.has_mask:
        raise LoweringError(f"{node.label}: a masked copy has no iDMA lowering")
    src = next(e for e in state.in_edges(node) if e.dst_conn == INPUT_CONNECTOR_NAME)
    dst = next(e for e in state.out_edges(node) if e.src_conn == OUTPUT_CONNECTOR_NAME)
    src_desc, dst_desc = edge_desc(sdfg, src), edge_desc(sdfg, dst)
    if src_desc.dtype != dst_desc.dtype:
        raise LoweringError(f"{node.label}: iDMA does not convert {src_desc.dtype} to {dst_desc.dtype}")
    if hbm.placed(src_desc) is not None and hbm.placed(dst_desc) is not None:
        raise LoweringError(f"{node.label}: {src.data} -> {dst.data} copies between two placed arrays")
    sides: list[tuple[str | None, Rows | None]] = []
    for edge, desc, conn in ((src, src_desc, INPUT_CONNECTOR_NAME), (dst, dst_desc, OUTPUT_CONNECTOR_NAME)):
        if hbm.placed(desc) is None:
            sides.append((f"dsh_addr({conn})", rows_of(edge.data.subset, desc)))  # pyright: ignore[reportArgumentType] -- DaCe's annotation
        else:
            sides.append(node_side(edge, desc, state, node, sdfg) or (None, None))  # pyright: ignore[reportArgumentType] -- DaCe's annotation
    (src_address, src_rows), (dst_address, dst_rows) = sides
    if src_address is None and dst_rows is not None:
        return split_call(src, src_desc, OUTPUT_CONNECTOR_NAME, dst_rows, False, sdfg)  # pyright: ignore[reportArgumentType] -- DaCe's annotation
    if dst_address is None and src_rows is not None:
        return split_call(dst, dst_desc, INPUT_CONNECTOR_NAME, src_rows, True, sdfg)  # pyright: ignore[reportArgumentType] -- DaCe's annotation
    if src_rows is None or dst_rows is None:
        raise LoweringError(f"{node.label}: {src.data} -> {dst.data} is no 1D or 2D transfer")
    size = src_desc.dtype.bytes
    if src_rows[0] * src_rows[1] != dst_rows[0] * dst_rows[1]:
        raise LoweringError(f"{node.label}: the two sides move different element counts")
    addresses = f"{dst_address}, {src_address}"
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
