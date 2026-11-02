# Copyright 2026 ETH Zurich and the Alloy authors.
"""What one call of a scope does at known sizes: the OpenMP regions it enters and the elements it handles, read from
its SDFG. A loop variable a bound depends on stands at the middle of its range, exact for a triangular nest."""

import dataclasses
import math
from dataclasses import dataclass
from typing import Any, Self

import dace
import sympy
from dace.dtypes import ScheduleType
from dace.libraries.standard.nodes import ArgReduce, Reduce, Scan
from dace.sdfg import nodes
from dace.sdfg.state import ControlFlowRegion, LoopRegion
from dace.transformation.passes.analysis import loop_analysis
from dace.transformation.passes.iteration_domain import loop_trip_count

__all__ = ["Load", "load_of"]

#: Schedules that render a worksharing loop; ``Default`` resolves to one at the top of a scope.
WORKSHARING = frozenset({ScheduleType.Default, ScheduleType.CPU_Multicore})


@dataclass(slots=True, frozen=True)
class Load:
    """``regions`` entered (a parallel region or a worksharing loop inside one: either way a team joins), ``elements``
    handled, and ``span``: the elements of the busiest thread."""

    regions: float = 0.0
    elements: float = 0.0
    span: float = 0.0

    def __add__(self, other: Self) -> Self:
        return type(self)(self.regions + other.regions, self.elements + other.elements, self.span + other.span)

    def repeated(self, count: float) -> Self:
        """``count`` iterations of this body; an iteration holding no inner loop is one element."""
        elements, span = (self.elements, self.span) if self.elements != 0.0 else (1.0, 1.0)
        return type(self)(count * self.regions, count * elements, count * span)


UNKNOWN = Load(math.nan, math.nan, math.nan)


@dataclass(slots=True, frozen=True)
class Where:
    """A point of the walk: the value of every symbol, the team size, and whether a region here costs one. Inside a
    worksharing loop every nested map runs on its own thread."""

    values: dict[str, float]
    cores: int
    forks: bool = True


def at(expr: Any, values: dict[str, float]) -> float:
    """``expr`` at ``values``; NaN when it is not a number there, which spreads to the whole load."""
    if expr is None:
        return math.nan
    value = sympy.sympify(expr)
    value = value.subs({s: values[s.name] for s in value.free_symbols if s.name in values})
    return float(value) if value.is_number else math.nan


def of_map(entry: nodes.MapEntry, state: dace.SDFGState, children: dict[Any, list[nodes.Node]], where: Where) -> Load:
    count, values = 1.0, dict(where.values)
    for param, (begin, end, step) in zip(entry.map.params, entry.map.range, strict=True):
        low, high = at(begin, values), at(end, values)
        count *= (high - low) / at(step, values) + 1
        values[param] = (low + high) / 2
    shares = where.forks and entry.map.schedule in WORKSHARING
    inner = dataclasses.replace(where, values=values, forks=where.forks and not shares)
    body = of_scope(children[entry], state, children, inner)
    if entry.map.schedule == ScheduleType.CPU_Persistent:
        return Load(regions=float(where.forks)) + body
    whole = body.repeated(count)
    return Load(1.0, whole.elements, whole.elements / min(where.cores, count)) if shares else whole


def of_library(node: nodes.LibraryNode, state: dace.SDFGState, where: Where) -> Load:
    elements = at(
        sympy.Max(*[e.data.subset.num_elements() for e in state.in_edges(node) if e.data.subset is not None]),
        where.values,
    )
    return Load(1.0, elements, elements / where.cores) if where.forks else Load(0.0, elements, elements)


def of_node(node: nodes.Node, state: dace.SDFGState, children: dict[Any, list[nodes.Node]], where: Where) -> Load:
    if isinstance(node, nodes.MapEntry):
        return of_map(node, state, children, where)
    if isinstance(node, nodes.NestedSDFG):
        mapped = {name: at(value, where.values) for name, value in node.symbol_mapping.items()}
        return of_region(node.sdfg, dataclasses.replace(where, values={**where.values, **mapped}))
    if isinstance(node, Reduce | ArgReduce | Scan):
        return of_library(node, state, where)
    return UNKNOWN if isinstance(node, nodes.LibraryNode) else Load()


def of_scope(
    inside: list[nodes.Node], state: dace.SDFGState, children: dict[Any, list[nodes.Node]], where: Where
) -> Load:
    total = Load()
    for node in inside:
        total += of_node(node, state, children, where)
    return total


def of_loop(loop: LoopRegion, where: Where) -> Load:
    count = at(loop_trip_count(loop), where.values)
    first, stride = (
        at(loop_analysis.get_init_assignment(loop), where.values),
        at(loop_analysis.get_loop_stride(loop), where.values),
    )
    middle = first + stride * (count - 1) / 2
    inner = dataclasses.replace(where, values={**where.values, loop.loop_variable: middle})
    return of_region(loop, inner).repeated(count)


def of_region(region: ControlFlowRegion, where: Where) -> Load:
    total = Load()
    for block in region.nodes():
        if isinstance(block, LoopRegion):
            total += of_loop(block, where)
        elif isinstance(block, dace.SDFGState):
            children = block.scope_children()
            total += of_scope(children[None], block, children, where)
        else:  # a branch or a jump: what runs depends on the data
            return UNKNOWN
    return total


def load_of(sdfg: dace.SDFG, sizes: dict[str, int], cores: int) -> Load | None:
    """One call of ``sdfg`` at ``sizes`` on a team of ``cores``; ``None`` when ``sizes`` do not decide it."""
    load = of_region(sdfg, Where(dict(sizes), cores))
    return load if load.elements > 0 and math.isfinite(load.regions + load.span) else None
