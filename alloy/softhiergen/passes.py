# Copyright 2026 ETH Zurich and the Alloy authors.
"""The SoftHier lowering of a NumPy program's SDFG, in place.

1. Global arrays go to HBM.
2. DaCe's vectorizer turns elementwise maps into tile maps of tile nodes (``VectorizeCPUMultiDim``).
3. Whole-array nodes (matrix product, reduction, copy, collective) expand to kernels (:mod:`.library.kernels`).
4. Top-level maps become ``SoftHier_Device`` kernels; their arrays go to TCDM.
5. Each node in a kernel gets its SoftHier implementation; the async engines get their waits and every role-guarded
   node a cluster barrier after it (``insert_sync``).
6. Library nodes expand.
"""

import math

from dace import data, dtypes, nodes, symbolic
from dace.libraries.comm.nodes.node import CommNode
from dace.libraries.standard.nodes.copy import CopyLibraryNode
from dace.libraries.standard.nodes.sync import Sync, SyncScope
from dace.libraries.tileops import TileBinop, TileFMA, TileGather, TileITE, TileMMA, TileReduce, TileUnop
from dace.libraries.tileops.nodes.tile_scan import TileScan
from dace.memlet import Memlet
from dace.sdfg import SDFG, SDFGState
from dace.sdfg.graph import MultiConnectorEdge
from dace.sdfg.utils import inline_sdfgs
from dace.subsets import Range
from dace.transformation.dataflow import (
    RedundantArray,
    RedundantSecondArray,
    TrivialTaskletElimination,
)

from alloy import tilelower
from alloy.softhiergen import hbm, storage
from alloy.softhiergen.arch import V1
from alloy.softhiergen.library import collectives, dma, kernels, redmule, rvv, sync
from alloy.softhiergen.library.common import LoweringError

#: The implementation of each node inside a kernel.
KERNEL_IMPLEMENTATIONS: tuple[tuple[type | tuple[type, ...], str], ...] = (
    (CopyLibraryNode, dma.IMPLEMENTATION),
    (TileMMA, redmule.IMPLEMENTATION),
    ((TileBinop, TileFMA, TileGather, TileITE, TileReduce, TileScan, TileUnop), rvv.IMPLEMENTATION),
    (CommNode, collectives.IMPLEMENTATION),
    (Sync, sync.IMPLEMENTATION),
)


#: The narrowest tile the lowering picks to fit a ragged extent; below it, a tile per few elements costs more than it
#: computes.
MIN_TILE = 16


def tile_width(sdfg: SDFG, widest: int) -> int:
    """The widest power-of-two tile up to ``widest`` (the vectorizer's rule) that divides the innermost extent of every
    top-level map, so no remainder tile, and no mask, is needed (4000 elements: 32). Maps narrower than ``MIN_TILE``
    (a loop over clusters, a single row) do not count; with no such width, ``widest`` stays and the vectorizer refuses
    an extent it does not divide.

    shortcut: a ragged extent gets narrow tiles, not a masked remainder; masked Spatz loops would keep 256."""
    extents = [
        int(symbolic.evaluate(node.map.range.size_exact()[-1], sdfg.constants))  # a specialized size is a constant
        for state in sdfg.states()
        for node in state.nodes()
        if isinstance(node, nodes.MapEntry) and state.entry_node(node) is None and len(node.map.range) > 0
    ]
    common = math.gcd(*(e for e in extents if e >= MIN_TILE))
    width = max((1 << k for k in range(widest.bit_length()) if 1 << k <= widest and common % (1 << k) == 0), default=1)
    return width if width >= MIN_TILE else widest


def lower(sdfg: SDFG, tile: int = 256) -> None:
    """Lowers ``sdfg`` (all symbols specialized) for SoftHier; ``tile`` is the widest tile the vectorizer may use."""
    tilelower.front(sdfg, tile_width(sdfg, tile), fuse_multiply_add=True)
    for name, desc in sdfg.arrays.items():
        if isinstance(desc, data.Array):
            desc.storage = storage.HBM
            if desc.placement is not None:  # pyright: ignore[reportUnnecessaryComparison] -- DaCe's annotation
                hbm.node_count(name, desc, sdfg.constants)
    expand_whole_array_nodes(sdfg)
    for state in sdfg.states():
        for node in state.nodes():
            if isinstance(node, nodes.MapEntry) and state.entry_node(node) is None:
                node.map.schedule = storage.DEVICE
                place_in_tcdm(state, node)
    check_top_level(sdfg)
    check_placed_access(sdfg)
    select_implementations(sdfg)
    insert_sync(sdfg)
    sdfg.expand_library_nodes(recursive=True)


def expand_whole_array_nodes(sdfg: SDFG) -> None:
    """Expands the top-level library nodes and array-to-array copies to kernels and inlines them."""
    # A result assigned through a temporary (``s[:] = numpy.sum(x)``) becomes the node's own output
    sdfg.apply_transformations_repeated([TrivialTaskletElimination, RedundantArray, RedundantSecondArray])
    for state in sdfg.states():
        for edge in list(state.edges()):
            if isinstance(edge.src, nodes.AccessNode) and isinstance(edge.dst, nodes.AccessNode):
                if relay_into(state, edge):
                    continue
                # The copy kernel moves whole arrays and refuses any other subset
                copy = CopyLibraryNode(f"copy_{edge.src.data}_{edge.dst.data}")
                src = edge.data.get_src_subset(edge, state) or Range.from_array(edge.src.desc(sdfg))
                dst = edge.data.get_dst_subset(edge, state) or Range.from_array(edge.dst.desc(sdfg))
                state.add_edge(edge.src, None, copy, "_cpy_in", Memlet(data=edge.src.data, subset=src))
                state.add_edge(copy, "_cpy_out", edge.dst, None, Memlet(data=edge.dst.data, subset=dst))
                state.remove_edge(edge)
        for node in state.nodes():
            if isinstance(node, nodes.LibraryNode) and state.entry_node(node) is None:
                node.implementation = kernels.IMPLEMENTATION
                node.expand(state)
    inline_sdfgs(sdfg)


def relay_into(state: SDFGState, edge: MultiConnectorEdge[Memlet]) -> bool:
    """Writes the library node whose transient output only relays to ``edge.dst`` straight into ``edge.dst``."""
    relay = edge.src
    if not relay.desc(state.sdfg).transient or state.in_degree(relay) != 1 or state.out_degree(relay) != 1:
        return False
    produced = state.in_edges(relay)[0]
    if not isinstance(produced.src, nodes.LibraryNode):
        return False
    subset = edge.data.get_dst_subset(edge, state)
    state.add_edge(produced.src, produced.src_conn, edge.dst, None, Memlet(data=edge.dst.data, subset=subset))
    state.remove_node(relay)
    return True


def place_in_tcdm(state: SDFGState, entry: nodes.MapEntry) -> None:
    """Every transient a kernel holds, in its scope or its nested SDFGs: an array lives in TCDM, a scalar in each
    core's registers (every core computes it)."""
    found = [
        node.desc(state.sdfg) for node in state.scope_subgraph(entry).nodes() if isinstance(node, nodes.AccessNode)
    ]
    for node in state.scope_subgraph(entry).nodes():
        if isinstance(node, nodes.NestedSDFG):
            found.extend(desc for inner in node.sdfg.all_sdfgs_recursive() for desc in inner.arrays.values())
    for desc in found:
        if desc.transient:
            desc.storage = storage.TCDM if isinstance(desc, data.Array) else dtypes.StorageType.Register


def check_top_level(sdfg: SDFG) -> None:
    """Outside kernels, a SoftHier program holds only arrays and kernels, in a straight sequence of states."""
    for block in sdfg.nodes():
        if not isinstance(block, SDFGState):
            raise LoweringError(f"{block.label}: control flow around kernels is not supported; put it in a kernel")
    for state in sdfg.states():
        for node in state.nodes():
            if state.entry_node(node) is None and not isinstance(
                node, (nodes.AccessNode, nodes.MapEntry, nodes.MapExit)
            ):
                raise LoweringError(f"{node.label} ({type(node).__name__}) is outside every kernel")


def kernel_states(sdfg: SDFG) -> list[tuple[SDFGState, list[nodes.Node], nodes.MapEntry]]:
    """Each state with nodes inside a kernel, and the kernel's map entry: top-level kernel scopes, and every state of a
    nested SDFG in one."""
    found = []
    for state in sdfg.states():
        for node in state.nodes():
            if isinstance(node, nodes.MapEntry) and node.map.schedule == storage.DEVICE:
                inside = state.scope_subgraph(node, include_entry=False, include_exit=False).nodes()
                found.append((state, inside, node))
                for nested in inside:
                    if isinstance(nested, nodes.NestedSDFG):
                        for inner in nested.sdfg.all_sdfgs_recursive():
                            found.extend((s, s.nodes(), node) for s in inner.states())
    return found


def check_placed_access(sdfg: SDFG) -> None:
    """Only copy nodes reach a placed array: the iDMA expansion is what computes its element addresses."""
    for state, inside, _ in kernel_states(sdfg):
        for node in inside:
            if isinstance(node, (nodes.AccessNode, nodes.EntryNode, nodes.ExitNode, CopyLibraryNode)):
                continue
            for edge in state.all_edges(node):
                if not edge.data.is_empty() and hbm.placed(state.sdfg.arrays[edge.data.data]) is not None:
                    raise LoweringError(
                        f"{node.label}: reads or writes the placed array {edge.data.data}; only a copy may"
                    )


def select_implementations(sdfg: SDFG) -> None:
    for _, inside, entry in kernel_states(sdfg):
        for node in inside:
            if not isinstance(node, nodes.LibraryNode) or isinstance(node, (sync.DmaWait, sync.RedmuleWait)):
                continue
            # Collectives and grid barriers meet in global barriers: every cluster must reach each one exactly once
            meets = isinstance(node, CommNode) or (isinstance(node, Sync) and node.scope == SyncScope.GRID)
            if meets and entry.map.range.num_elements_exact() != V1.num_clusters:
                raise LoweringError(
                    f"{node.label}: a collective or grid barrier needs a kernel map of one iteration per cluster "
                    f"({V1.num_clusters}), "
                    f"{entry.map.label} has {entry.map.range.num_elements_exact()}"
                )
            implementation = next((impl for kind, impl in KERNEL_IMPLEMENTATIONS if isinstance(node, kind)), None)
            if implementation is None:
                raise LoweringError(f"{node.label}: {type(node).__name__} has no SoftHier lowering")
            node.implementation = implementation


def insert_sync(sdfg: SDFG) -> None:
    """After each role-guarded node: the wait for its engine (iDMA, RedMulE), then a cluster barrier, ordered before
    every reader of its outputs. Collectives synchronize themselves. A copy with ``sync = False`` gets neither: the
    pass that cleared it places the wait and the barrier.

    shortcut: one barrier per node, also where a later one would cover it; merge them when barriers show in the
    cycle counts.
    """
    waits = {dma.IMPLEMENTATION: sync.DmaWait, redmule.IMPLEMENTATION: sync.RedmuleWait}
    guarded = (dma.IMPLEMENTATION, redmule.IMPLEMENTATION, rvv.IMPLEMENTATION)
    for state, inside, _ in kernel_states(sdfg):
        for node in list(inside):
            if not isinstance(node, nodes.LibraryNode) or node.implementation not in guarded:
                continue
            if isinstance(node, CopyLibraryNode) and not node.sync:
                continue
            readers: list[nodes.Node] = []
            for edge in state.out_edges(node):
                if isinstance(edge.dst, nodes.AccessNode):
                    readers.extend(e.dst for e in state.out_edges(edge.dst))
                else:
                    readers.append(edge.dst)
            last: nodes.Node = node
            if node.implementation in waits:
                wait = waits[node.implementation](f"wait_{node.label}")
                state.add_nedge(last, wait, Memlet())
                last = wait
            barrier = Sync(f"sync_{node.label}", scope=SyncScope.BLOCK)
            barrier.implementation = sync.IMPLEMENTATION
            state.add_nedge(last, barrier, Memlet())
            for reader in dict.fromkeys(readers):
                state.add_nedge(barrier, reader, Memlet())
