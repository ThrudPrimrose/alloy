# Copyright 2026 ETH Zurich and the Alloy authors.
"""The outlined program's control flow as a tree of records, which ``report.json`` carries and ``report.md`` prints.
A slim port of NestForge's tree printer (same rows and connectors, no work and depth); duplicated on purpose, so
neither project imports the other for it."""

import enum
import functools
import heapq
from typing import Any

import dace
import sympy
from dace.libraries.standard.nodes import external_call
from dace.sdfg import nodes
from dace.sdfg.state import AbstractControlFlowRegion, ConditionalBlock, ControlFlowRegion, LoopRegion, SDFGState
from dace.transformation.passes.analysis import loop_analysis
from pydantic.dataclasses import dataclass

from alloy.records import RECORD

__all__ = ["CfgNode", "Kind", "cfg_tree", "render"]

TEE, ELBOW, PIPE, BLANK = "|- ", "`- ", "|  ", "   "


class Kind(enum.StrEnum):
    SDFG = "sdfg"
    STATE = "state"
    LOOP = "loop"
    CONDITIONAL = "conditional"
    BRANCH = "branch"
    MAP = "map"
    LIBRARY = "library"
    #: An outlined scope (an ``ExternalCall``); its label is the scope's entry symbol.
    SCOPE = "scope"


@dataclass(slots=True, frozen=True, config=RECORD)
class CfgNode:
    """One row: what it is, its label, what follows the label (domain, condition, reads and writes), its rows below."""

    kind: Kind
    label: str
    detail: str
    children: tuple["CfgNode", ...]


def in_order(graph: AbstractControlFlowRegion | SDFGState) -> list[Any]:
    """A graph's nodes in topological order, ties broken by insertion order, so the tree is deterministic."""
    all_nodes: list[Any] = list(graph.nodes())
    rank = {id(n): i for i, n in enumerate(all_nodes)}
    indegree = {id(n): 0 for n in all_nodes}
    for edge in graph.edges():
        indegree[id(edge.dst)] += 1
    ready = [rank[id(n)] for n in all_nodes if indegree[id(n)] == 0]
    heapq.heapify(ready)
    ordered: list[Any] = []
    while ready:
        node = all_nodes[heapq.heappop(ready)]
        ordered.append(node)
        for edge in graph.out_edges(node):
            indegree[id(edge.dst)] -= 1
            if indegree[id(edge.dst)] == 0:
                heapq.heappush(ready, rank[id(edge.dst)])
    return ordered


@functools.lru_cache(maxsize=4096, typed=True)
def exclusive_end(end_text: str, delta: int) -> str:
    """``end + delta``, simplified."""
    end = dace.symbolic.pystr_to_symbolic(end_text)
    assert isinstance(end, sympy.Expr), f"a range end is an expression, got {end_text!r}"
    return str(dace.symbolic.simplify(end + delta))


def render_range(begin: object, end: object, step: object) -> str:
    """``begin:end:step`` as ``range`` reads it: the end one past the last value, a unit step left off."""
    delta = -1 if dace.symbolic.pystr_to_symbolic(str(step)).is_negative is True else 1
    text = f"{begin}:{exclusive_end(str(end), delta)}"
    return text if str(step) == "1" else f"{text}:{step}"


def loop_detail(loop: LoopRegion) -> str:
    start, end = loop_analysis.get_init_assignment(loop), loop_analysis.get_loop_end(loop)
    stride = loop_analysis.get_loop_stride(loop)
    if loop.loop_variable and start is not None and end is not None:
        return f"{loop.loop_variable}={render_range(start, end, stride if stride is not None else 1)}"
    return loop.loop_condition.as_string if loop.loop_condition is not None else ""


def reads_writes(state: SDFGState, node: nodes.MapEntry | nodes.LibraryNode) -> str:
    last = state.exit_node(node) if isinstance(node, nodes.MapEntry) else node
    reads = sorted({e.data.data for e in state.in_edges(node) if e.data.data})
    writes = sorted({e.data.data for e in state.out_edges(last) if e.data.data})
    return f"reads={reads} writes={writes}"


def kernel_node(state: SDFGState, node: nodes.MapEntry | nodes.LibraryNode, children: dict[Any, list[Any]]) -> CfgNode:
    if isinstance(node, external_call.ExternalCall):
        return CfgNode(kind=Kind.SCOPE, label=node.symbol, detail=reads_writes(state, node), children=())
    if isinstance(node, nodes.LibraryNode):
        return CfgNode(kind=Kind.LIBRARY, label=node.label, detail=reads_writes(state, node), children=())
    domain = ", ".join(f"{p}={render_range(*r)}" for p, r in zip(node.map.params, node.map.range, strict=True))
    inner = tuple(kernel_node(state, child, children) for child in kernels(children[node]))
    return CfgNode(
        kind=Kind.MAP, label=node.map.label, detail=f"[{domain}]  {reads_writes(state, node)}", children=inner
    )


def kernels(scope_nodes: list[Any]) -> list[nodes.MapEntry | nodes.LibraryNode]:
    return [n for n in scope_nodes if isinstance(n, nodes.MapEntry | nodes.LibraryNode)]


def state_node(state: SDFGState) -> CfgNode:
    rank = {id(n): i for i, n in enumerate(in_order(state))}
    children = {scope: sorted(kids, key=lambda n: rank[id(n)]) for scope, kids in state.scope_children().items()}
    rows = tuple(kernel_node(state, node, children) for node in kernels(children[None]))
    return CfgNode(kind=Kind.STATE, label=state.label, detail="", children=rows)


def block_node(block: Any) -> CfgNode:
    if isinstance(block, SDFGState):
        return state_node(block)
    if isinstance(block, ConditionalBlock):
        branches = tuple(
            CfgNode(
                kind=Kind.BRANCH,
                label=branch.label,
                detail="else" if condition is None else f"when {condition.as_string}",
                children=region_rows(branch),
            )
            for condition, branch in block.branches
        )
        return CfgNode(kind=Kind.CONDITIONAL, label=block.label, detail="", children=branches)
    if isinstance(block, LoopRegion):
        return CfgNode(kind=Kind.LOOP, label=block.label, detail=loop_detail(block), children=region_rows(block))
    assert isinstance(block, ControlFlowRegion), f"unexpected control-flow block {type(block).__name__}"
    return CfgNode(kind=Kind.BRANCH, label=block.label, detail="", children=region_rows(block))


def region_rows(cfg: AbstractControlFlowRegion) -> tuple[CfgNode, ...]:
    return tuple(block_node(block) for block in in_order(cfg))


def cfg_tree(sdfg: dace.SDFG) -> CfgNode:
    """``sdfg``'s control flow: blocks in execution order, each state's top-level maps, library nodes and scopes."""
    return CfgNode(kind=Kind.SDFG, label=sdfg.label, detail="", children=region_rows(sdfg))


def render(tree: CfgNode) -> str:
    """The tree as text, one row per node, in NestForge's connectors."""
    lines = [f"SDFG '{tree.label}'"]

    def walk(node: CfgNode, prefix: str) -> None:
        for index, child in enumerate(node.children):
            last = index == len(node.children) - 1
            text = f"{child.label}  {child.detail}" if child.detail else child.label
            lines.append(prefix + (ELBOW if last else TEE) + text)
            walk(child, prefix + (BLANK if last else PIPE))

    walk(tree, "")
    return "\n".join(lines)
