# Copyright 2026 ETH Zurich and the Alloy authors.
"""What the SoftHier expansions share: core roles, operand checks and the guarded tasklet."""

from collections.abc import Mapping

import dace
from dace import data, dtypes
from dace.memlet import Memlet
from dace.sdfg import nodes
from dace.sdfg.graph import MultiConnectorEdge

from alloy.softhiergen.storage import TCDM
from alloy.tilelower import Unsupported

#: The core that drives Spatz and RedMulE (core 0) and the one that issues iDMA (the last core).
COMPUTE_CORE = "dsh_is_compute_core()"
DMA_CORE = "dsh_is_dma_core()"

#: The RVV suffix of each element type the Spatz helpers take.
RVV_SUFFIX = {dtypes.float32: "f32", dtypes.float16: "f16", dtypes.int32: "i32"}


class LoweringError(Unsupported):
    """A node has no legal SoftHier lowering; the message says why."""


def edge_desc(sdfg: dace.SDFG, edge: MultiConnectorEdge[Memlet]) -> data.Data:
    return sdfg.arrays[edge.data.data]


def in_edges(state: dace.SDFGState, node: nodes.Node) -> dict[str, MultiConnectorEdge[Memlet]]:
    return {edge.dst_conn: edge for edge in state.in_edges(node) if edge.dst_conn is not None}  # pyright: ignore[reportUnnecessaryComparison] -- DaCe's annotation


def out_edges(state: dace.SDFGState, node: nodes.Node) -> dict[str, MultiConnectorEdge[Memlet]]:
    return {edge.src_conn: edge for edge in state.out_edges(node) if edge.src_conn is not None}  # pyright: ignore[reportUnnecessaryComparison] -- DaCe's annotation


def packed_run(edge: MultiConnectorEdge[Memlet], desc: data.Data) -> bool:
    """Whether the edge moves one contiguous run of its array."""
    return isinstance(desc, data.Array) and edge.data.subset.is_contiguous_subset(desc)  # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess] -- DaCe's annotation


def tcdm_tile_reason(sdfg: dace.SDFG, edge: MultiConnectorEdge[Memlet], what: str) -> str | None:
    """Why a tile operand cannot be read in place by a unit-stride vector loop, or ``None``."""
    desc = edge_desc(sdfg, edge)
    if desc.storage != TCDM:
        return f"{what} is in {desc.storage}, not in TCDM"
    if not packed_run(edge, desc):
        return f"{what} is not one contiguous run of {edge.data.data}"
    return None


def guarded_tasklet(
    label: str,
    inputs: Mapping[str, dtypes.typeclass | None],
    outputs: Mapping[str, dtypes.typeclass | None],
    role: str,
    body: str,
) -> nodes.Tasklet:
    """A tasklet whose ``body`` runs on the core of ``role`` only; every core still defines its connectors."""
    return nodes.Tasklet(
        label,
        inputs=dict(inputs),
        outputs=dict(outputs),
        code=f"if ({role}) {{\n{body}\n}}",
        language=dtypes.Language.CPP,
        side_effects=True,
    )


def side_effect_tasklet(state: dace.SDFGState, label: str, code: str) -> nodes.Tasklet:
    """A tasklet without connectors (a barrier or a wait). The expansion takes over the node's empty edges; without
    any, it would not add the tasklet to the state."""
    tasklet = nodes.Tasklet(label, code=code, language=dtypes.Language.CPP, side_effects=True)
    state.add_node(tasklet)
    return tasklet


def pointer_to(sdfg: dace.SDFG, edge: MultiConnectorEdge[Memlet]) -> dtypes.pointer:
    return dtypes.pointer(edge_desc(sdfg, edge).dtype)
