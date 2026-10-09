# Copyright 2026 ETH Zurich and the Alloy authors.
"""Split a dace program into regions: one per top-level nest, each a standalone SDFG with a fixed C ABI."""

import copy
import re
from dataclasses import dataclass

import dace
import sympy
from dace.libraries.standard.nodes import external_call
from dace.sdfg import nodes
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
    calls: tuple[external_call.ExternalCall, ...]


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
        if isinstance(node, nodes.LibraryNode) and type(node).__name__ in ("Reduce", "Scan", "ArgReduce"):
            return True
    return any(
        edge.data.wcr is not None for edge, _ in sdfg.all_edges_recursive() if isinstance(edge.data, dace.Memlet)
    )


def reduced_extent(edge, scope: dict) -> sympy.Expr:
    """Product of the extents of the enclosing map parameters the WCR ``edge`` does NOT index its destination by:
    every iteration over those writes the same element."""
    indexed = {str(s) for s in edge.data.subset.free_symbols}
    extent: sympy.Expr = sympy.Integer(1)
    entry = scope[edge.src]
    while entry is not None:
        for param, rng in zip(entry.map.params, entry.map.range, strict=True):
            if param not in indexed:
                extent = extent * sympy.sympify(dace.subsets.Range([rng]).num_elements())
        entry = scope[entry]
    return extent


def accumulation_length(sdfg: dace.SDFG) -> sympy.Expr:
    """The longest accumulation chain of ``sdfg``: over every write-conflict-resolution (reduction) edge leaving a
    tasklet or a nested SDFG, the reduced map extent around it, times the nested SDFG's own length. Exact on the SDFG,
    so a square matmul's ``K`` is told apart from its kept ``N``; only WCR reductions count, not a sequential loop
    that accumulates into a scalar."""
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


def outline(program: dace.frontend.python.parser.DaceProgram, libm_calls: frozenset[str]) -> Program:
    """Parse ``program`` and outline each top-level nest into a region; ``libm_calls`` marks the regions a vector
    math library could serve."""
    sdfg = program.to_sdfg(simplify=True)
    original = copy.deepcopy(sdfg)
    # A top-level library node (np.sum -> Reduce) is no nest until expanded; expand so it becomes a region.
    sdfg.expand_library_nodes(recursive=True)
    sdfg.simplify()
    calls = tuple(passes.outline_to_external_calls(sdfg))
    regions = []
    for call in calls:
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
    return Program(sdfg=sdfg, original=original, regions=tuple(regions), calls=calls)
