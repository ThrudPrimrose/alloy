# Copyright 2026 ETH Zurich and the Alloy authors.
"""Map fission: a map's body cut at a node set into up to three maps, ``before | set | after``, every value crossing a
cut widened to an array over the map's range. :func:`cuts` is the default work/depth heuristic that picks the set;
:func:`split` applies cuts to a copy of a scope with DaCe's own transformations (nest the body, fission its state at
the set, ``SubgraphFission`` after each piece)."""

import ast
import copy
import platform
from dataclasses import dataclass

import dace
from dace.sdfg import nodes
from dace.sdfg.graph import MultiConnectorEdge, SubgraphView
from dace.transformation import helpers
from dace.transformation.interstate import SubgraphFission

from alloy import machine

__all__ = ["Cut", "cuts", "fissioned", "split", "vector_registers"]


@dataclass(slots=True, frozen=True)
class Cut:
    """A node set of one top-level map's body, by position: the state's index in ``sdfg.states()``, the map entry's
    and the set's node ids in that state."""

    state: int
    entry: int
    nodes: tuple[int, ...]


def vector_registers() -> int:
    """The host's architectural vector registers: 32 on aarch64 and with AVX-512, 16 on other x86-64."""
    return 32 if platform.machine() in ("aarch64", "arm64") or "avx512f" in machine.cpu_flags() else 16


def work(node: nodes.Node) -> int:
    """Operations a code node performs: a Python tasklet's operators and calls, 1 for any other code node."""
    if not isinstance(node, nodes.Tasklet) or node.code.language != dace.Language.Python:
        return 1
    operations = (ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.Call)
    return max(1, sum(isinstance(n, operations) for n in ast.walk(ast.parse(node.code.as_string))))


@dataclass(slots=True, frozen=True)
class Body:
    """A flat map body as work/depth sees it: each code node's level (1 + its deepest producer's), each value's level
    (its producer's) and the levels that consume it."""

    levels: dict[nodes.Node, int]
    values: tuple[tuple[int, tuple[int, ...]], ...]

    @property
    def depth(self) -> int:
        return max(self.levels.values(), default=0)

    def crossing(self, d: int, lo: int, hi: int) -> int:
        """Values produced in levels ``[lo, d]`` and consumed in ``(d, hi]``: live across level ``d`` of that piece."""
        return sum(1 for made, used in self.values if lo <= made <= d and any(d < u <= hi for u in used))

    def pressure(self, lo: int, hi: int) -> int:
        """The most values live at once in the piece of levels ``[lo, hi]``. A value from an earlier piece is loaded
        where it is used, one for a later piece stored where it is made, so neither stays live."""
        return max((self.crossing(d, lo, hi) for d in range(lo, hi)), default=0)


def body(state: dace.SDFGState, entry: nodes.MapEntry) -> Body:
    inside = state.scope_subgraph(entry, include_entry=False, include_exit=False)
    members = set(inside.nodes())
    levels: dict[nodes.Node, int] = {}
    pending = {n: sum(1 for e in state.in_edges(n) if e.src in members) for n in members}
    ready = [n for n in inside.nodes() if pending[n] == 0]
    while ready:
        node = ready.pop()
        made = max((levels[e.src] for e in state.in_edges(node) if e.src in members), default=0)
        levels[node] = made + 1 if isinstance(node, nodes.CodeNode) else made
        for e in state.out_edges(node):
            if e.dst in members:
                pending[e.dst] -= 1
                if pending[e.dst] == 0:
                    ready.append(e.dst)
    values = tuple(
        (levels[n], tuple(levels[e.dst] for e in state.out_edges(n) if isinstance(e.dst, nodes.CodeNode)))
        for n in inside.nodes()
        if isinstance(n, nodes.AccessNode) and levels[n] > 0  # a value loaded from an array is reloaded, not held
    )
    return Body({n: lv for n, lv in levels.items() if isinstance(n, nodes.CodeNode)}, values)


def flat_maps(state: dace.SDFGState) -> list[nodes.MapEntry]:
    """Top-level maps whose body holds no other scope."""
    children = state.scope_children()
    return [
        n
        for n in children[None]
        if isinstance(n, nodes.MapEntry) and not any(isinstance(c, nodes.EntryNode) for c in children[n])
    ]


def cut_level(b: Body) -> int:
    """The level to cut after: the one leaving the least pressure in either piece, then the fewest values crossing
    (each a store and a load more per element), then the most even work."""
    total = sum(work(n) for n in b.levels)

    def key(d: int) -> tuple[int, int, int]:
        before = sum(work(n) for n, lv in b.levels.items() if lv <= d)
        return max(b.pressure(1, d), b.pressure(d + 1, b.depth)), b.crossing(d, 1, b.depth), abs(total - 2 * before)

    return min(range(1, b.depth), key=key)


def cuts(sdfg: dace.SDFG, registers: int) -> tuple[Cut, ...]:
    """The default work/depth cut of every flat top-level map whose body keeps more values live than ``registers``:
    the code nodes up to :func:`cut_level`. Splitting a map the vectorizer misses or whose loop spills, read from a
    build's feedback, is not done yet."""
    out = []
    for index, state in enumerate(sdfg.states()):
        for entry in flat_maps(state):
            b = body(state, entry)
            if b.depth < 2 or b.pressure(1, b.depth) <= registers:
                continue
            d = cut_level(b)
            chosen = tuple(sorted(state.node_id(n) for n, lv in b.levels.items() if lv <= d))
            out.append(Cut(index, state.node_id(entry), chosen))
    return tuple(out)


def reach(state: dace.SDFGState, start: set[nodes.Node], members: set[nodes.Node], *, up: bool) -> set[nodes.Node]:
    """Nodes of ``members`` upstream (or downstream) of ``start``, ``start`` excluded."""
    seen: set[nodes.Node] = set()
    frontier = list(start)
    while frontier:
        node = frontier.pop()
        edges = state.in_edges(node) if up else state.out_edges(node)
        for e in edges:
            nxt = e.src if up else e.dst
            if nxt in members and nxt not in seen:
                seen.add(nxt)
                frontier.append(nxt)
    return seen - start


def cut_after(sdfg: dace.SDFG, block: dace.SDFGState) -> None:
    """``SubgraphFission`` on the map whose nested body holds ``block``, cut after it."""
    for state in sdfg.states():
        for node in state.nodes():
            if isinstance(node, nodes.NestedSDFG) and block in node.sdfg.nodes():
                entry = state.entry_node(node)
                where = {"map_entry": entry, "nested_sdfg": node}
                if not SubgraphFission.can_be_applied_to(sdfg, options={"cut": block.label}, **where):
                    raise NotImplementedError(f"SubgraphFission refuses to cut {node.label}'s map after {block.label}")
                SubgraphFission.apply_to(sdfg, options={"cut": block.label}, verify=False, **where)
                return
    raise ValueError(f"no map body holds {block.label}")


def forward(
    sdfg: dace.SDFG, state: dace.SDFGState, value: nodes.AccessNode, later: list[MultiConnectorEdge]
) -> nodes.AccessNode:
    """Route the ``later`` reads of ``value`` through a copy of it, returned: the copy, made in ``value``'s piece,
    alone crosses the cut, so that piece reads ``value`` locally and inlines back into a flat map (``InlineSDFG``
    refuses a nested body that reads an output it writes)."""
    name = sdfg.add_datadesc(value.data, copy.deepcopy(sdfg.arrays[value.data]), find_new_name=True)
    whole = dace.subsets.Range.from_array(sdfg.arrays[name])
    copied = state.add_access(name)
    state.add_edge(value, None, copied, None, dace.Memlet(data=value.data, subset=whole, other_subset=whole))
    for e in later:
        memlet = copy.deepcopy(e.data)
        memlet.data = name
        state.add_edge(copied, e.src_conn, e.dst, e.dst_conn, memlet)
        state.remove_edge(e)
    return copied


def cut_map(sdfg: dace.SDFG, state: dace.SDFGState, entry: nodes.MapEntry, chosen: set[nodes.Node]) -> None:
    """Cut ``entry``'s map into ``before | chosen | after``; a node between two chosen ones is chosen too."""
    inside = state.scope_subgraph(entry, include_entry=False, include_exit=False)
    members = set(inside.nodes())
    chosen = chosen | (reach(state, chosen, members, up=True) & reach(state, chosen, members, up=False))
    upstream = reach(state, chosen, members, up=True)
    before: list[nodes.Node] = [n for n in inside.nodes() if n in upstream and isinstance(n, nodes.CodeNode)]
    the_set = [n for n in inside.nodes() if n in chosen]  # graph order
    after: list[nodes.Node] = []
    piece = {n: 0 if n in upstream else 1 if n in chosen else 2 for n in members if isinstance(n, nodes.CodeNode)}
    for value in [n for n in inside.nodes() if isinstance(n, nodes.AccessNode)]:
        made = max((piece[e.src] for e in state.in_edges(value) if e.src in piece), default=None)
        reads = [e for e in state.out_edges(value) if e.dst in piece]
        later = [e for e in reads if made is not None and piece[e.dst] > made]
        if made is not None and later and len(later) < len(reads):
            (before, the_set, after)[made].append(forward(sdfg, state, value, later))
    inside = state.scope_subgraph(entry, include_entry=False, include_exit=False)
    nested = helpers.nest_state_subgraph(sdfg, state, inside)
    (inner,) = nested.sdfg.states()
    pieces = [helpers.state_fission(SubgraphView(inner, group)) for group in (before, the_set) if group]
    if not any(isinstance(n, nodes.CodeNode) for n in inner.nodes()):
        pieces.pop()  # nothing after the set: its piece is the map's last
    for piece in pieces:
        cut_after(sdfg, piece)


def owner(sdfg: dace.SDFG, node: nodes.Node) -> dace.SDFGState:
    return next(s for s in sdfg.states() if node in s.nodes())


def split(sdfg: dace.SDFG, cut_list: tuple[Cut, ...]) -> dace.SDFG:
    """A copy of ``sdfg`` with every cut applied, simplified so each piece is a flat map again. Raises
    ``NotImplementedError`` when DaCe refuses a cut."""
    out = copy.deepcopy(sdfg)
    states = list(out.states())
    targets = [(states[c.state].node(c.entry), {states[c.state].node(n) for n in c.nodes}) for c in cut_list]
    for entry, chosen in targets:
        assert isinstance(entry, nodes.MapEntry), "a cut names a map entry"
        cut_map(out, owner(out, entry), entry, chosen)
    out.simplify()
    return out


def fissioned(sdfg: dace.SDFG) -> dace.SDFG:
    """``sdfg`` split at its default cuts for the host's registers: what a fission candidate renders."""
    return split(sdfg, cuts(sdfg, vector_registers()))
