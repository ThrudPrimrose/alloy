# Copyright 2026 ETH Zurich and the Alloy authors.
"""Split a dace program into regions: one per top-level nest or library node, each a standalone SDFG with a fixed C
ABI."""

import copy
import re
from dataclasses import dataclass

import dace
import sympy
from dace.libraries.standard.nodes import ArgReduce, Reduce, Scan, external_call
from dace.sdfg import nodes
from dace.sdfg.graph import MultiConnectorEdge
from dace.transformation import passes

CALL_PATTERN = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(")


@dataclass(slots=True, frozen=True)
class Region:
    """One outlined nest: the entry ``symbol``, its parameter order, and the SDFG that renders it."""

    symbol: str
    abi_order: tuple[str, ...]
    signature: str
    sdfg: dace.SDFG
    calls_libm: bool
    has_reduction: bool
    #: Terms summed into one output element (symbolic; 1 when nothing reduces): the ``l`` of the reassociation floor.
    accumulation_length: sympy.Expr


@dataclass(slots=True, frozen=True)
class Program:
    """The outlined program: ``sdfg`` calls every region through an ``ExternalCall`` node; ``original`` is the
    program before outlining."""

    sdfg: dace.SDFG
    original: dace.SDFG
    regions: tuple[Region, ...]


def called_names(sdfg: dace.SDFG) -> set[str]:
    """Every function name a tasklet of ``sdfg`` (nested SDFGs included) calls."""
    names: set[str] = set()
    for node, _ in sdfg.all_nodes_recursive():
        if isinstance(node, nodes.Tasklet):
            names |= set(CALL_PATTERN.findall(node.code.as_string))
    return names


def has_reduction(sdfg: dace.SDFG) -> bool:
    """Whether ``sdfg`` reduces: a write-conflict-resolution memlet or a reduce/scan library node."""
    for node, _ in sdfg.all_nodes_recursive():
        if isinstance(node, Reduce | Scan | ArgReduce):
            return True
    return any(
        edge.data.wcr is not None for edge, _ in sdfg.all_edges_recursive() if isinstance(edge.data, dace.Memlet)
    )


def reduced_extent(
    edge: MultiConnectorEdge[dace.Memlet], scope: dict[nodes.Node, nodes.EntryNode | None]
) -> sympy.Expr:
    """Product of the extents of the enclosing map parameters the WCR ``edge`` does NOT index its destination by:
    every iteration over those writes the same element."""
    subset = edge.data.subset
    assert subset is not None, "only non-empty WCR edges are measured"
    indexed = {str(s) for s in subset.free_symbols}
    extent: sympy.Expr = sympy.Integer(1)
    entry = scope[edge.src]
    while isinstance(entry, nodes.MapEntry):
        for param, rng in zip(entry.map.params, entry.map.range, strict=True):
            if param not in indexed:
                extent = extent * sympy.sympify(dace.subsets.Range([rng]).num_elements())
        entry = scope[entry]
    return extent


def volume(edge: MultiConnectorEdge[dace.Memlet]) -> sympy.Expr:
    subset = edge.data.subset
    assert subset is not None, "a library node's data edge names a subset"
    return sympy.Integer(1) * sympy.sympify(subset.num_elements())


def library_length(state: dace.SDFGState, node: Reduce | ArgReduce | Scan) -> sympy.Expr:
    """A reduce's input elements per output element; a scan's whole input (its longest prefix bounds the chain)."""
    total = volume(next(e for e in state.in_edges(node) if not e.data.is_empty()))
    if isinstance(node, Scan):
        return total
    return total / volume(next(e for e in state.out_edges(node) if not e.data.is_empty()))


def accumulation_length(sdfg: dace.SDFG) -> sympy.Expr:
    """The longest accumulation chain of ``sdfg``: the reduced map extent around each WCR edge (times a nested SDFG's
    own length), or a reduce/scan node's :func:`library_length`. A sequential loop into a scalar does not count."""
    lengths: list[sympy.Expr] = []
    for state in sdfg.states():
        scope = state.scope_dict()
        for edge in state.edges():
            if edge.data.is_empty() or edge.data.wcr is None:
                continue
            if isinstance(edge.src, nodes.Tasklet):
                lengths.append(reduced_extent(edge, scope))
            elif isinstance(edge.src, nodes.NestedSDFG):
                lengths.append(reduced_extent(edge, scope) * accumulation_length(edge.src.sdfg))
        lengths += [accumulation_length(n.sdfg) for n in state.nodes() if isinstance(n, nodes.NestedSDFG)]
        lengths += [library_length(state, n) for n in state.nodes() if isinstance(n, Reduce | ArgReduce | Scan)]
    known = [length for length in lengths if length != 1]
    if not known:
        return sympy.Integer(1)
    return known[0] if len(known) == 1 else sympy.Max(*known)


def standalone(call: external_call.ExternalCall) -> dace.SDFG:
    """The call's reference nest with containers renamed from connector names (``_in_a``/``_out_a``) back to the
    names ``abi_order`` uses; a container both read and written becomes one pointer."""
    if call.standalone_sdfg is None:
        raise ValueError(f"{call.symbol} has no reference nest")
    sdfg = call.standalone_sdfg
    sdfg.name = call.symbol  # pyright: ignore[reportAttributeAccessIssue] -- DaCe Property descriptor
    for name in call.abi_order:
        read, written = external_call.in_conn(name), external_call.out_conn(name)
        if read in sdfg.arrays and written in sdfg.arrays:
            sdfg.remove_data(read, validate=False)
            sdfg.replace(read, written)
        for conn in (read, written):
            if conn in sdfg.arrays:
                sdfg.replace(conn, name)
    return sdfg


def unchosen(node: nodes.LibraryNode) -> bool:
    """Whether no pipeline chose ``node``'s implementation (unset, or ``pure``): Alloy expands it and generates the
    nest. An explicit choice (canonicalize's ``CPU`` C++ reduction) is kept."""
    return node.implementation in (None, "pure")


def outline(sdfg: dace.SDFG, libm_calls: frozenset[str]) -> Program:
    """Outline each top-level nest and library node of a copy of ``sdfg`` into a region; ``libm_calls`` marks the
    regions a vector math library could serve."""
    sdfg = copy.deepcopy(sdfg)
    sdfg.simplify()
    original = copy.deepcopy(sdfg)
    # An unchosen library node expands into a nest Alloy generates; one whose implementation a pipeline chose is
    # outlined whole and rendered in its region with that implementation.
    sdfg.expand_library_nodes(recursive=True, predicate=unchosen)
    sdfg.simplify()
    regions = []
    for call in passes.outline_to_external_calls(sdfg, library_nodes=True):
        region_sdfg = standalone(call)
        regions.append(
            Region(
                symbol=call.symbol,
                abi_order=tuple(call.abi_order),
                signature=call.signature,
                sdfg=region_sdfg,
                calls_libm=bool(called_names(region_sdfg) & libm_calls),
                has_reduction=has_reduction(region_sdfg),
                accumulation_length=accumulation_length(region_sdfg),
            )
        )
    return Program(sdfg=sdfg, original=original, regions=tuple(regions))
