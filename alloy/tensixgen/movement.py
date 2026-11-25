# Copyright 2026 ETH Zurich and the Alloy authors.
"""Tensix data movement as copy, wait and sync nodes in the tile body, on the design of DaCe's ``InsertAsyncWaits``
(the asynchronous TMA loads of the GPU backend) and the model softhiergen uses for iDMA.

Every tile the body loads from or stores to an array in DRAM (or its L1 shard) moves through a ``CopyLibraryNode``
(the vectorizer's tile copies; a body that reads an array directly, a ``Reduce``, gets one). The copies are
asynchronous NoC transfers: :func:`insert` places
- after the loads, one :class:`NocWait` (``noc_async_read_barrier``) before the first reader of any loaded tile: a
  Tensix barrier completes every transfer issued before it, so the loads of the body are in flight together, as
  ``InsertAsyncWaits`` issues a state's copies before its waits; then one ``Sync`` per circular buffer, the handoff
  to the compute kernel (``cb_push_back``);
- around the store, a ``Sync`` that waits for the compute kernel's tiles (``cb_wait_front``), then the copy, its
  :class:`NocWait` (``noc_async_write_barrier``), and a ``Sync`` that frees the buffer (``cb_pop_front``).

The reader and writer kernels of :mod:`alloy.tensixgen.split` spell these nodes in their order (:func:`read_lines`,
:func:`write_lines`)."""

from dataclasses import dataclass
from typing import ClassVar

import dace
from dace import library, nodes, properties
from dace.libraries.standard.nodes.copy import CopyLibraryNode
from dace.libraries.standard.nodes.copy.common import INPUT_CONNECTOR_NAME, OUTPUT_CONNECTOR_NAME
from dace.libraries.standard.nodes.sync import Sync, SyncScope
from dace.libraries.tileops.nodes import MaskedCopyLibraryNode
from dace.memlet import Memlet
from dace.sdfg.graph import MultiConnectorEdge
from dace.transformation.transformation import ExpandTransformation

from alloy.tensixgen.backend import Refused

IMPLEMENTATION = "Tensix"
#: The circular buffer the compute kernel packs the output tiles into.
OUT_CB = 16
COPIES = (CopyLibraryNode, MaskedCopyLibraryNode)


@library.expansion
class ExpandNocWait(ExpandTransformation):
    environments: ClassVar[list[type]] = []

    @staticmethod
    def expansion(node: "NocWait", parent_state: dace.SDFGState, parent_sdfg: dace.SDFG) -> nodes.Tasklet:
        return nodes.Tasklet(node.label, {}, {}, node.call(), language=dace.Language.CPP, side_effects=True)


@library.node
class NocWait(nodes.LibraryNode):
    """The data-movement core waits until every NoC read (or write) it issued has completed."""

    implementations: ClassVar[dict[str, type]] = {IMPLEMENTATION: ExpandNocWait}
    default_implementation = IMPLEMENTATION
    direction = properties.Property(dtype=str, default="read", desc="read or write")

    def __init__(self, name: str, direction: str = "read") -> None:
        super().__init__(name)
        self.direction = direction

    def call(self) -> str:
        return f"noc_async_{self.direction}_barrier();"

    def has_side_effects(self, sdfg: dace.SDFG) -> bool:
        return True


@dataclass(frozen=True, slots=True)
class Load:
    """Input ``cb``'s tiles: its copies, and the sync that hands the filled buffer to the compute kernel."""

    cb: int
    array: str
    copies: tuple[nodes.LibraryNode, ...]
    push: Sync


@dataclass(frozen=True, slots=True)
class Movement:
    loads: tuple[Load, ...]
    read_wait: NocWait
    ready: Sync
    store: nodes.LibraryNode
    write_wait: NocWait
    pop: Sync


def source(state: dace.SDFGState, node: nodes.Node) -> str | None:
    (edge,) = [e for e in state.in_edges(node) if e.dst_conn == INPUT_CONNECTOR_NAME] or [None]
    return None if edge is None else state.memlet_path(edge)[0].src.data


def target(state: dace.SDFGState, node: nodes.Node) -> str | None:
    (edge,) = [e for e in state.out_edges(node) if e.src_conn == OUTPUT_CONNECTOR_NAME] or [None]
    return None if edge is None else state.memlet_path(edge)[-1].dst.data


def through_copy(state: dace.SDFGState, edge: MultiConnectorEdge[Memlet], name: str) -> CopyLibraryNode:
    """``edge`` (between the array ``name`` and the body) rerouted through a new copy and a transient of its subset."""
    sdfg = state.sdfg
    shape = edge.data.subset.size_exact()  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue] -- DaCe's annotation
    buffer, _ = sdfg.add_transient(f"{name}_cb", shape, sdfg.arrays[name].dtype, find_new_name=True)
    whole = ", ".join(f"0:{s}" for s in shape)
    load = isinstance(edge.src, nodes.AccessNode) and edge.src.data == name
    copy = CopyLibraryNode(f"{'load' if load else 'store'}_{name}")
    held = state.add_access(buffer)
    state.remove_edge(edge)
    if load:  # a load: array -> copy -> buffer -> body
        state.add_edge(edge.src, None, copy, INPUT_CONNECTOR_NAME, Memlet.from_memlet(edge.data))
        state.add_edge(copy, OUTPUT_CONNECTOR_NAME, held, None, Memlet(f"{buffer}[{whole}]"))
        state.add_edge(held, None, edge.dst, edge.dst_conn, Memlet(f"{buffer}[{whole}]"))
    else:  # a store: body -> buffer -> copy -> array
        state.add_edge(edge.src, edge.src_conn, held, None, Memlet(f"{buffer}[{whole}]"))
        state.add_edge(held, None, copy, INPUT_CONNECTOR_NAME, Memlet(f"{buffer}[{whole}]"))
        state.add_edge(copy, OUTPUT_CONNECTOR_NAME, edge.dst, None, Memlet.from_memlet(edge.data))
    return copy


def copies_of(state: dace.SDFGState, name: str, load: bool) -> list[nodes.LibraryNode]:
    """The copies that load tiles of ``name`` (or store them); a body that reads (writes) it directly gets one."""
    found: list[nodes.LibraryNode] = [
        n for n in state.nodes() if isinstance(n, COPIES) and (source if load else target)(state, n) == name
    ]
    if found:
        return found
    arrays = [n for n in state.data_nodes() if n.data == name]
    edges = [e for a in arrays for e in (state.out_edges(a) if load else state.in_edges(a))]
    if len(edges) != 1:
        raise Refused(f"{name}: {len(edges)} {'readers' if load else 'writers'} and no tile copy; the split moves one")
    return [through_copy(state, edges[0], name)]


def readers(state: dace.SDFGState, copy: nodes.Node) -> list[nodes.Node]:
    return [e.dst for edge in state.out_edges(copy) if isinstance(edge.dst, nodes.AccessNode)
            for e in state.out_edges(edge.dst)]  # fmt: skip


def sync(state: dace.SDFGState, label: str) -> Sync:
    node = Sync(label, scope=SyncScope.BLOCK)
    node.implementation = IMPLEMENTATION
    state.add_node(node)
    return node


def store_of(
    state: dace.SDFGState, output: str, body: list[nodes.Node] | None
) -> tuple[nodes.LibraryNode, list[nodes.Node]]:
    """The output's store copy and the nodes that produce what it stores; for a reduction (``body``, the body's
    sinks) a copy without data edges, the contract's partial tile."""
    if body is not None:
        partial = CopyLibraryNode("store_partial_tile")
        state.add_node(partial)
        return partial, body
    stores = copies_of(state, output, load=False)
    if len(stores) != 1:
        raise Refused(f"{output}: {len(stores)} tile stores; the writer moves one")
    (store,) = stores
    held = [e.src for e in state.in_edges(store) if isinstance(e.src, nodes.AccessNode)]
    return store, list(dict.fromkeys(e.src for a in held for e in state.in_edges(a)))


def insert(state: dace.SDFGState, inputs: list[str], output: str, reduce: bool = False) -> Movement:
    """The copy, wait and sync nodes of the body in ``state``: input ``k`` (in ``inputs``' order) through CB ``k``,
    the output through CB 16. A reduction (``reduce``) stores the contract's partial tile, which the SDFG does not
    hold: its store is a copy without data edges, ordered after the body."""
    body = state.sink_nodes() if reduce else []
    wait = NocWait("noc_read_wait", "read")
    state.add_node(wait)
    loads = []
    for cb, name in enumerate(inputs):
        copies = copies_of(state, name, load=True)
        push = sync(state, f"cb_push_{cb}")
        state.add_nedge(wait, push, Memlet())
        for copy in copies:
            copy.implementation = IMPLEMENTATION
            state.add_nedge(copy, wait, Memlet())
            for reader in dict.fromkeys(readers(state, copy)):
                state.add_nedge(push, reader, Memlet())
        loads.append(Load(cb, name, tuple(copies), push))
    store, before = store_of(state, output, body if reduce else None)
    store.implementation = IMPLEMENTATION
    ready, done = sync(state, f"cb_wait_{OUT_CB}"), sync(state, f"cb_pop_{OUT_CB}")
    write_wait = NocWait("noc_write_wait", "write")
    for node in before:
        state.add_nedge(node, ready, Memlet())
    state.add_nedge(ready, store, Memlet())
    state.add_nedge(store, write_wait, Memlet())
    state.add_nedge(write_wait, done, Memlet())
    return Movement(tuple(loads), wait, ready, store, write_wait, done)


def read_line(load: Load, sharded: bool) -> str:
    """The NoC read of tile ``t`` of the block ``i`` of ``load``'s array into its buffer."""
    k = load.cb
    if sharded:
        return f"noc_async_read(s{k} + (i + t) * bytes{k}, w{k} + t * bytes{k}, bytes{k});"
    return f"noc_async_read_tile(start + i + t, s{k}, w{k} + t * bytes{k});"


def write_line(sharded: bool) -> str:
    if sharded:
        return "noc_async_write(r + t * bytes, s + (i + t) * bytes, bytes);"
    return "noc_async_write_tile(start + i + t, s, r + t * bytes);"


def push_call(load: Load) -> str:
    return f"cb_push_back({load.cb}, n);"
