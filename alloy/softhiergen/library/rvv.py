# Copyright 2026 ETH Zurich and the Alloy authors.
"""Tile nodes on the Spatz vector unit: a call of a ``dsh_rvv_*`` loop (``dsh_rvv.h``) on the compute core.

Tile operands are contiguous TCDM runs, read in place; a ``Scalar`` or ``Symbol`` operand is one value (the ``vf`` /
``vx`` forms). The tile is walked as ``prod(widths)`` elements.
"""

import math
from typing import ClassVar

import dace
from dace import library
from dace.codegen.cppunparse import pyexpr2cpp
from dace.libraries.tileops import TileBinop, TileFMA, TileReduce, TileUnop
from dace.libraries.tileops.kinds import SYMBOL, TILE
from dace.libraries.tileops.operands import Operand
from dace.sdfg import nodes
from dace.transformation.transformation import ExpandTransformation

from alloy.softhiergen.library.common import (
    COMPUTE_CORE,
    RVV_SUFFIX,
    LoweringError,
    edge_desc,
    guarded_tasklet,
    in_edges,
    out_edges,
    pointer_to,
    tcdm_tile_reason,
)

IMPLEMENTATION = "SoftHierRVV"

#: TileBinop ops with a Spatz loop, and whether they commute.
BINOPS = {"+": ("add", True), "-": ("sub", False), "*": ("mul", True), "/": ("div", False), "min": ("min", True),
          "max": ("max", True)}  # fmt: skip
#: TileUnop ops that are one RVV float instruction; the rest (exp, log, ...) have no Spatz loop.
UNOPS = ("neg", "abs", "sqrt")
#: TileReduce ops with a Spatz reduction.
REDUCTIONS = {"+": "sum", "max": "max", "min": "min"}


class Call:
    """The connectors and arguments of one call: tiles by pointer, single values by value or inline."""

    def __init__(self, node: nodes.LibraryNode, state: dace.SDFGState, sdfg: dace.SDFG, out_conn: str) -> None:
        self.node, self.state, self.sdfg = node, state, sdfg
        self.inputs: dict[str, dace.typeclass | None] = {}
        out = out_edges(state, node)[out_conn]
        self.check(tcdm_tile_reason(sdfg, out, f"{node.label}: output {out_conn}"))
        self.outputs = {out_conn: pointer_to(sdfg, out)}
        self.dtype = edge_desc(sdfg, out).dtype
        if self.dtype not in RVV_SUFFIX:
            raise LoweringError(f"{node.label}: Spatz takes float32, float16 or int32, not {self.dtype}")
        self.suffix = RVV_SUFFIX[self.dtype]
        self.count = math.prod(node.widths)  # pyright: ignore[reportAttributeAccessIssue] -- DaCe's annotation

    def check(self, reason: str | None) -> None:
        if reason is not None:
            raise LoweringError(reason)

    def tile(self, conn: str) -> str:
        edge = in_edges(self.state, self.node)[conn]
        self.check(tcdm_tile_reason(self.sdfg, edge, f"{self.node.label}: {conn}"))
        if edge_desc(self.sdfg, edge).dtype != self.dtype:
            raise LoweringError(f"{self.node.label}: {conn} is not {self.dtype}")
        self.inputs[conn] = pointer_to(self.sdfg, edge)
        return conn

    def value(self, operand: Operand) -> str:
        if operand.kind == SYMBOL:
            return f"({self.dtype.ctype})({pyexpr2cpp(operand.expr)})"
        self.inputs[operand.conn] = None
        return f"({self.dtype.ctype})({operand.conn})"

    def tasklet(self, body: str) -> nodes.Tasklet:
        # The fence completes the vector stores before the cluster barrier lets other cores read them
        return guarded_tasklet(
            f"{self.node.label}_rvv", self.inputs, self.outputs, COMPUTE_CORE, f"{body}\ndsh_vfence();"
        )


def no_mask(node: nodes.LibraryNode) -> None:
    if node.has_mask:  # pyright: ignore[reportAttributeAccessIssue] -- DaCe's annotation
        raise LoweringError(f"{node.label}: masked tiles have no Spatz lowering")


@library.register_expansion(TileBinop, IMPLEMENTATION)  # pyright: ignore[reportArgumentType] -- DaCe's annotation
class ExpandBinopRVV(ExpandTransformation):
    environments: ClassVar[list[type]] = []

    @staticmethod
    def expansion(node: TileBinop, parent_state: dace.SDFGState, parent_sdfg: dace.SDFG) -> nodes.Tasklet:
        no_mask(node)
        if node.op not in BINOPS:
            raise LoweringError(f"{node.label}: no Spatz loop for {node.op!r}")
        name, commutes = BINOPS[node.op]
        call = Call(node, parent_state, parent_sdfg, "_c")
        if name == "div" and call.suffix == "i32":
            raise LoweringError(f"{node.label}: RVV integer division is not among the Spatz loops")
        a, b = node.operands()
        n, s = call.count, call.suffix
        if a.kind == TILE and b.kind == TILE:
            body = f"dsh_rvv_{name}_{s}(_c, {call.tile('_a')}, {call.tile('_b')}, {n});"
        elif a.kind == TILE:
            body = f"dsh_rvv_{name}_s_{s}(_c, {call.tile('_a')}, {call.value(b)}, {n});"
        elif b.kind == TILE and commutes:
            body = f"dsh_rvv_{name}_s_{s}(_c, {call.tile('_b')}, {call.value(a)}, {n});"
        elif b.kind == TILE and name in ("sub", "div") and s != "i32":
            body = f"dsh_rvv_{name}_r_{s}(_c, {call.value(a)}, {call.tile('_b')}, {n});"
        else:
            raise LoweringError(f"{node.label}: no Spatz loop for operands {a.kind}, {b.kind} of {node.op!r}")
        return call.tasklet(body)


@library.register_expansion(TileUnop, IMPLEMENTATION)  # pyright: ignore[reportArgumentType] -- DaCe's annotation
class ExpandUnopRVV(ExpandTransformation):
    environments: ClassVar[list[type]] = []

    @staticmethod
    def expansion(node: TileUnop, parent_state: dace.SDFGState, parent_sdfg: dace.SDFG) -> nodes.Tasklet:
        no_mask(node)
        call = Call(node, parent_state, parent_sdfg, "_c")
        if node.op not in UNOPS or call.suffix == "i32" or node.kind_a != TILE:
            raise LoweringError(f"{node.label}: Spatz has {UNOPS} on float tiles only, not {node.op!r}")
        return call.tasklet(f"dsh_rvv_{node.op}_{call.suffix}(_c, {call.tile('_a')}, {call.count});")


@library.register_expansion(TileFMA, IMPLEMENTATION)  # pyright: ignore[reportArgumentType] -- DaCe's annotation
class ExpandFMARVV(ExpandTransformation):
    environments: ClassVar[list[type]] = []

    @staticmethod
    def expansion(node: TileFMA, parent_state: dace.SDFGState, parent_sdfg: dace.SDFG) -> nodes.Tasklet:
        no_mask(node)
        call = Call(node, parent_state, parent_sdfg, "_o")
        a, b, c = node.operands()
        n, s = call.count, call.suffix
        if c.kind != TILE:
            raise LoweringError(f"{node.label}: the addend must be a tile")
        if a.kind == TILE and b.kind == TILE:
            body = f"dsh_rvv_fma_{s}(_o, {call.tile('_a')}, {call.tile('_b')}, {call.tile('_c')}, {n});"
        elif b.kind == TILE:
            body = f"dsh_rvv_fma_s_{s}(_o, {call.value(a)}, {call.tile('_b')}, {call.tile('_c')}, {n});"
        elif a.kind == TILE:
            body = f"dsh_rvv_fma_s_{s}(_o, {call.value(b)}, {call.tile('_a')}, {call.tile('_c')}, {n});"
        else:
            raise LoweringError(f"{node.label}: one factor must be a tile")
        return call.tasklet(body)


@library.register_expansion(TileReduce, IMPLEMENTATION)  # pyright: ignore[reportArgumentType] -- DaCe's annotation
class ExpandReduceRVV(ExpandTransformation):
    environments: ClassVar[list[type]] = []

    @staticmethod
    def expansion(node: TileReduce, parent_state: dace.SDFGState, parent_sdfg: dace.SDFG) -> nodes.Tasklet:
        no_mask(node)
        if node.axis is not None or node.op not in REDUCTIONS:
            raise LoweringError(f"{node.label}: Spatz reduces a whole tile with +, max or min")
        call = Call(node, parent_state, parent_sdfg, "_dst")
        # The Spatz model has no widening reduction (vfwredusum); a float16 sum would accumulate in float16
        if node.op == "+" and call.suffix == "f16":
            raise LoweringError(f"{node.label}: a float16 sum would accumulate in float16")
        source = call.tile("_src")
        return call.tasklet(f"_dst[0] = dsh_rvv_red{REDUCTIONS[node.op]}_{call.suffix}({source}, {call.count});")
