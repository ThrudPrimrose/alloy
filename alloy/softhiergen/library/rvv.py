# Copyright 2026 ETH Zurich and the Alloy authors.
"""Tile nodes on the Spatz vector unit: a call of a ``dsh_rvv_*`` loop (``dsh_rvv.h``) on the compute core.

Tile operands are contiguous TCDM runs, read in place; a ``Scalar`` or ``Symbol`` operand is one value (the ``vf`` /
``vx`` forms). The tile is walked as ``prod(widths)`` elements.
"""

import math
import re
from typing import ClassVar

import dace
from dace import library
from dace.codegen.cppunparse import pyexpr2cpp
from dace.libraries.tileops import TileBinop, TileFMA, TileGather, TileITE, TileReduce, TileUnop
from dace.libraries.tileops.kinds import SYMBOL, TILE
from dace.libraries.tileops.nodes.tile_scan import TileScan
from dace.libraries.tileops.operands import Operand
from dace.sdfg import nodes
from dace.transformation.transformation import ExpandTransformation

from alloy.isa.mathkernels import kernel, render
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
#: TileBinop comparisons: the Spatz loop, and the one that takes the operands swapped (``s < x`` is ``x > s``). The
#: result is a bool tile, one 0/1 byte per lane.
COMPARES = {"<": ("lt", "gt"), "<=": ("le", "ge"), ">": ("gt", "lt"), ">=": ("ge", "le"), "==": ("eq", "eq"),
            "!=": ("ne", "ne")}  # fmt: skip
#: TileUnop ops that are one RVV float instruction.
UNOPS = ("neg", "abs", "sqrt")
#: TileUnop ops with no RVV instruction: a scalar loop on the Spatz core over the ladder's float32 kernel
#: (alloy.isa.mathkernels) at :data:`LADDER_RUNG`, which keeps libm's results on every input. An agent may swap a
#: lower rung in from the lookup.
LADDER = ("exp", "log")
LADDER_RUNG = "strict"
#: TileReduce ops with a Spatz reduction.
REDUCTIONS = {"+": "sum", "max": "max", "min": "min"}


class Call:
    """The connectors and arguments of one call: tiles by pointer, single values by value or inline."""

    def __init__(
        self, node: nodes.LibraryNode, state: dace.SDFGState, sdfg: dace.SDFG, out_conn: str, lanes_of: str = ""
    ) -> None:
        """``lanes_of``: the input connector whose element type the loop takes, when the output's differs (a
        comparison writes bool)."""
        self.node, self.state, self.sdfg = node, state, sdfg
        self.inputs: dict[str, dace.typeclass | None] = {}
        out = out_edges(state, node)[out_conn]
        self.check(tcdm_tile_reason(sdfg, out, f"{node.label}: output {out_conn}"))
        self.outputs = {out_conn: pointer_to(sdfg, out)}
        self.dtype = edge_desc(sdfg, in_edges(state, node)[lanes_of] if lanes_of else out).dtype
        if self.dtype not in RVV_SUFFIX:
            raise LoweringError(f"{node.label}: Spatz takes float32, float16 or int32, not {self.dtype}")
        self.suffix = RVV_SUFFIX[self.dtype]
        self.count = math.prod(node.widths)  # pyright: ignore[reportAttributeAccessIssue] -- DaCe's annotation

    def check(self, reason: str | None) -> None:
        if reason is not None:
            raise LoweringError(reason)

    def tile(self, conn: str, dtype: dace.typeclass | None = None) -> str:
        """``conn`` read in place; its element type must be ``dtype``, the loop's by default."""
        edge = in_edges(self.state, self.node)[conn]
        self.check(tcdm_tile_reason(self.sdfg, edge, f"{self.node.label}: {conn}"))
        if edge_desc(self.sdfg, edge).dtype != (dtype or self.dtype):
            raise LoweringError(f"{self.node.label}: {conn} is not {dtype or self.dtype}")
        self.inputs[conn] = pointer_to(self.sdfg, edge)
        return conn

    def value(self, operand: Operand) -> str:
        if operand.kind == SYMBOL:
            return f"({self.dtype.ctype})({pyexpr2cpp(operand.expr)})"
        self.inputs[operand.conn] = None
        return f"({self.dtype.ctype})({operand.conn})"

    def tasklet(self, body: str) -> nodes.Tasklet:
        # rv32 newlib's int32_t is long, DaCe's int32 is int: one width, two C++ types, so int tiles pass by cast
        for conn, ptr in {**self.inputs, **self.outputs}.items():
            if ptr is not None and ptr.base_type == dace.int32:
                body = re.sub(rf"\b{conn}\b(?!\s*\[)", f"(int32_t*){conn}", body)  # not an indexed scalar
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
        if node.op in COMPARES:
            return compare(node, parent_state, parent_sdfg)
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
        if node.op in LADDER and call.suffix == "f32" and node.kind_a == TILE:
            return call.tasklet(f"dsh_scalar_{node.op}_f32(_c, {call.tile('_a')}, {call.count});")
        if node.op not in UNOPS or call.suffix == "i32" or node.kind_a != TILE:
            raise LoweringError(
                f"{node.label}: Spatz has {UNOPS} on float tiles and {LADDER} on float32 tiles, not {node.op!r}"
            )
        return call.tasklet(f"dsh_rvv_{node.op}_{call.suffix}(_c, {call.tile('_a')}, {call.count});")


#: Round to nearest even in one RV32F instruction: newlib's rintf, which ``__builtin_rintf`` calls on rv32, stops
#: GVSoC. Exact for the kernels' |q| < 2**31; past it the strict kernels' guard takes :data:`TAILS`.
RINT = (
    "static inline float dsh_rintf(float x) {",
    "    int32_t i;",
    '    __asm__("fcvt.w.s %0, %1, rne" : "=r"(i) : "f"(x));',
    "    return (float)i;",
    "}",
    "#define __builtin_rintf dsh_rintf",
)

#: The strict kernels' out-of-range values, in place of newlib's expf and logf (which stop GVSoC too): exp(x) as
#: exp(x/2)^2 (|x| <= 174; beyond, inf or 0), log(x) on x scaled by 2^-64 or 2^64 back into the kernel's range.
TAILS = (
    "static inline float alloy_exp_f32_strict(float x);",
    "static inline float alloy_log_f32_strict(float x);",
    "static float dsh_expf(float x) {",
    "    if (x != x) return x;",
    "    if (x > 174.0f) return __builtin_inff();",
    "    if (x < -174.0f) return 0.0f;",
    "    float h = alloy_exp_f32_strict(0.5f * x);",
    "    return h * h;",
    "}",
    "static float dsh_logf(float x) {",
    '    if (x != x || x < 0.0f) return __builtin_nanf("");',
    "    if (x == 0.0f) return -__builtin_inff();",
    "    if (x == __builtin_inff()) return x;",
    "    const float shift = 44.3614195558365f;  // 64 ln 2",
    "    if (x < 1.2e-38f) return alloy_log_f32_strict(x * 0x1p64f) - shift;",
    "    return alloy_log_f32_strict(x * 0x1p-64f) + shift;",
    "}",
    "#define expf dsh_expf",
    "#define logf dsh_logf",
)


def ladder_unit() -> str:
    """The C unit of the :data:`LADDER` loops (main.c includes it: the kernels are C, kernels.cpp declares the
    loops): each function's float32 kernel at :data:`LADDER_RUNG` and ``dsh_scalar_<fn>_f32(z, x, n)``."""
    lines = ["// Generated by alloy.softhiergen.library.rvv.ladder_unit: the ladder's float32 kernels as scalar loops",
             "#include <math.h>", "#include <stdint.h>", *RINT, *TAILS]  # fmt: skip
    for fn in LADDER:
        k = kernel(fn, "f32", LADDER_RUNG)
        lines += [render(k, "scalar").source,
                  f"void dsh_scalar_{fn}_f32(float *z, const float *x, int n) {{",
                  f"    for (int i = 0; i < n; ++i) z[i] = {k.name}(x[i]);", "}"]  # fmt: skip
    return "\n".join(lines) + "\n"


@library.register_expansion(TileGather, IMPLEMENTATION)  # pyright: ignore[reportArgumentType] -- DaCe's annotation
class ExpandGatherRVV(ExpandTransformation):
    """A constant over the tile (``numpy.full``): the Spatz fill loop. A gather from memory has no Spatz loop."""

    environments: ClassVar[list[type]] = []

    @staticmethod
    def expansion(node: TileGather, parent_state: dace.SDFGState, parent_sdfg: dace.SDFG) -> nodes.Tasklet:
        if node.src_kind != SYMBOL:
            raise LoweringError(f"{node.label}: only a constant fills a tile on Spatz, not a {node.src_kind} gather")
        call = Call(node, parent_state, parent_sdfg, "_dst")
        if call.suffix == "i32":
            raise LoweringError(f"{node.label}: Spatz fills float tiles only")
        value = f"({call.dtype.ctype})({pyexpr2cpp(node.src_expr)})"
        return call.tasklet(f"dsh_rvv_fill_{call.suffix}(_dst, {value}, {call.count});")


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


def compare(node: TileBinop, state: dace.SDFGState, sdfg: dace.SDFG) -> nodes.Tasklet:
    """A comparison into a bool tile: ``x CMP y`` or ``x CMP s``; ``s CMP x`` is ``x`` compared the other way."""
    a, b = node.operands()
    if TILE not in (a.kind, b.kind):
        raise LoweringError(f"{node.label}: one side of {node.op!r} must be a tile")
    call = Call(node, state, sdfg, "_c", "_a" if a.kind == TILE else "_b")
    if edge_desc(sdfg, out_edges(state, node)["_c"]).dtype != dace.bool_:
        raise LoweringError(f"{node.label}: a comparison writes a bool tile")
    name, swapped = COMPARES[node.op]
    n, s = call.count, call.suffix
    if a.kind == TILE and b.kind == TILE:
        body = f"dsh_rvv_{name}_{s}(_c, {call.tile('_a')}, {call.tile('_b')}, {n});"
    elif a.kind == TILE:
        body = f"dsh_rvv_{name}_s_{s}(_c, {call.tile('_a')}, {call.value(b)}, {n});"
    else:
        body = f"dsh_rvv_{swapped}_s_{s}(_c, {call.tile('_b')}, {call.value(a)}, {n});"
    return call.tasklet(body)


@library.register_expansion(TileITE, IMPLEMENTATION)  # pyright: ignore[reportArgumentType] -- DaCe's annotation
class ExpandITERVV(ExpandTransformation):
    """``_o = _mask ? _t : _e`` with a bool tile as the condition: a scalar loop on the Spatz core (``dsh_rvv.h``:
    GVSoC's Spatz model stops on mask instructions)."""

    environments: ClassVar[list[type]] = []

    @staticmethod
    def expansion(node: TileITE, parent_state: dace.SDFGState, parent_sdfg: dace.SDFG) -> nodes.Tasklet:
        condition, then, otherwise = node.operands()
        if condition.kind != TILE:
            raise LoweringError(f"{node.label}: Spatz selects under a bool tile, not a {condition.kind} condition")
        call = Call(node, parent_state, parent_sdfg, "_o")
        mask, n, s = call.tile("_mask", dace.bool), call.count, call.suffix  # pyright: ignore[reportArgumentType] -- DaCe's annotation
        if then.kind == TILE and otherwise.kind == TILE:
            body = f"dsh_rvv_select_{s}(_o, {mask}, {call.tile('_t')}, {call.tile('_e')}, {n});"
        elif otherwise.kind == TILE:
            body = f"dsh_rvv_select_ts_{s}(_o, {mask}, {call.value(then)}, {call.tile('_e')}, {n});"
        elif then.kind == TILE:
            body = f"dsh_rvv_select_es_{s}(_o, {mask}, {call.tile('_t')}, {call.value(otherwise)}, {n});"
        else:
            raise LoweringError(f"{node.label}: one arm must be a tile")
        return call.tasklet(body)


#: TileScan combines as C on two values ``a`` and ``b``.
SCAN_COMBINE = {"+": "a + b", "*": "a * b", "min": "b < a ? b : a", "max": "b > a ? b : a"}


@library.register_expansion(TileScan, IMPLEMENTATION)  # pyright: ignore[reportArgumentType] -- DaCe's annotation
class ExpandScanRVV(ExpandTransformation):
    """An inclusive scan of a one-dim tile, a scalar loop on the compute core: RVV has no scan instruction, and the
    log-step slide-and-add costs more than the loop at Spatz's strip lengths.

    shortcut: scalar; a vslideup ladder per strip (alloy/isa intrinsics.toml rvv scan_add) once it runs on GVSoC."""

    environments: ClassVar[list[type]] = []

    @staticmethod
    def expansion(node: TileScan, parent_state: dace.SDFGState, parent_sdfg: dace.SDFG) -> nodes.Tasklet:
        call = Call(node, parent_state, parent_sdfg, "_dst")
        source, ctype = call.tile("_src"), call.dtype.ctype
        combine = SCAN_COMBINE[node.op].replace("a", "acc").replace("b", f"{source}[i]")
        body = (
            f"{ctype} acc = {source}[0];\n_dst[0] = acc;\n"
            f"for (size_t i = 1; i < {call.count}; ++i) {{\n    acc = {combine};\n    _dst[i] = acc;\n}}"
        )
        return call.tasklet(body)
