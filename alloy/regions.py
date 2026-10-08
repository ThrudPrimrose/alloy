# Copyright 2026 ETH Zurich and the Alloy authors.
"""Split a dace program into regions: one per top-level nest, each a standalone SDFG with a fixed C ABI."""

import re
from dataclasses import dataclass

import dace
from dace.libraries.standard.nodes import external_call
from dace.sdfg import nodes
from dace.transformation import passes

#: libm calls a vector math library can replace. sqrt/fabs/fma are single instructions and need none.
LIBM_CALLS = frozenset(
    "sin cos tan asin acos atan atan2 sinh cosh tanh asinh acosh atanh exp exp2 expm1 log log2 log10 log1p "
    "pow cbrt erf erfc".split()
)
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


@dataclass(slots=True, frozen=True)
class Program:
    """The outlined program: ``sdfg`` calls every region through an ``ExternalCall`` node."""

    sdfg: dace.SDFG
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


def standalone(call: external_call.ExternalCall) -> dace.SDFG:
    """The call's reference nest with containers renamed from connector names (``_in_a``/``_out_a``) back to the
    names ``abi_order`` uses; a container both read and written becomes one pointer."""
    assert call.standalone_sdfg is not None, f"{call.symbol} has no reference nest"
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


def outline(program: dace.frontend.python.parser.DaceProgram) -> Program:
    """Parse ``program`` and outline each top-level nest into a region."""
    sdfg = program.to_sdfg(simplify=True)
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
                calls_libm=bool(called_names(region_sdfg) & LIBM_CALLS),
                has_reduction=has_reduction(region_sdfg),
            )
        )
    return Program(sdfg=sdfg, regions=tuple(regions), calls=calls)
