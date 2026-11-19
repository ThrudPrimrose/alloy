# Copyright 2026 ETH Zurich and the Alloy authors.
"""Tensix as one more backend of DaCe's tile nodes (``dace.libraries.tileops``): a ``tensix`` implementation of
``TileBinop``, ``TileUnop`` and ``TileReduce``, registered from Alloy, built from the checked rows of
``alloy/isa/tensix.toml``. A tile is one 32x32 Tensix tile in DST (1024 lanes, full tiles only, no lane masks).

An expansion is a C++ tasklet of two lines, the row's init and its call, whose DST tile arguments are the node's
connectors (``_a``, ``_b``, ``_c``; ``_src``, ``_dst``): the kernel split (:mod:`alloy.tensixgen.split`) assigns each
tile a DST index and substitutes it. A unary call works in place, on ``_c``. An SFPI rung's source goes in the
tasklet's ``code_global``."""

import re
from dataclasses import dataclass

import dace
from dace.libraries.tileops.nodes import TileBinop, TileReduce, TileUnop
from dace.library import register_implementation
from dace.sdfg import nodes
from dace.transformation.transformation import ExpandTransformation

from alloy.isa import tensix

__all__ = [
    "CONNECTORS",
    "EXPANSIONS",
    "IMPLEMENTATION",
    "Refused",
    "Rule",
    "code",
    "node_code",
    "op_of",
    "place",
    "rule",
    "use_tensix",
]

IMPLEMENTATION = "tensix"
#: The contract's relative tolerance: a row the card measured above it is replaced by its SFPI rung.
TASK_RTOL = 1e-3
#: The tile ops' names -> the Tensix row ops.
BINARY = {"+": "add", "-": "sub", "*": "mul", "/": "div", "max": "max"}
UNARY = {"neg": "neg", "abs": "abs", "exp": "exp", "log": "log", "sqrt": "sqrt", "sin": "sin", "cos": "cos",
         "tanh": "tanh"}  # fmt: skip
REDUCE = {"+": "add", "max": "max"}
#: A rung's call passes the DST tile as this argument of this function.
RUNG_FUNC, RUNG_DST = "_llk_math_eltwise_unary_sfpu_params_", 1
#: The positions of a row's DST tile arguments, per row kind.
DST_ARGS = {"unary": (0,), "binary_sfpu": (0, 1, 2), "fill": (0,)}


class Refused(ValueError):
    """A node or scope the Tensix backend does not compute; the message says why."""


@dataclass(frozen=True, slots=True)
class Rule:
    """How ``op`` runs on DST tiles for one tt-metal version: a row's or a rung's init and call, the function and
    argument positions of the DST tiles in the call, its header, its SFPI source, and where it comes from."""

    op: str
    init: str
    call: str
    func: str
    dst: tuple[int, ...]
    header: str
    code: str
    source: str


def rule(op: str, version: str = "v06") -> Rule:
    """The SFPU row of ``op`` (the FPU reads TF32, about 1e-3 relative) with a passing ttsim run at f32, spelled for
    ``version``; its most accurate SFPI rung instead where the platform that version runs on measured the row above
    :data:`TASK_RTOL`: the card (tt-metal 0.63) for ``v06``, ttsim (0.8x) for ``v08``, whose run every row passed."""
    rows = [r for r in tensix.rows() if r.op == op and r.unit == "SFPU" and r.kind in DST_ARGS]
    if not rows:
        raise Refused(f"no SFPU tile row for {op} in tensix.toml")
    row = rows[0]
    verdict = tensix.verdicts().get((op, "f32", row.unit))
    if row.pending or verdict is None or not verdict.ok or verdict.rel is None or verdict.rel > TASK_RTOL:
        raise Refused(f"the {op} row has no ttsim run at f32 within {TASK_RTOL:g}")
    card = tensix.card_verdicts().get((op, "f32", row.unit)) if version == "v06" else None
    rel = None if card is None else card.rel if card.ok and card.rel is not None else float("inf")
    if rel is not None and rel > TASK_RTOL:
        rungs = tensix.rungs(op, "f32")
        if not rungs:
            raise Refused(f"the {op} row is off by {rel:.3g} relative on the card and has no SFPI rung")
        r = rungs[0]
        source = f"rung {r.name} ({r.error_ulp:g} ulp on the card; the row's card rel {rel:.3g})"
        return Rule(op, r.init, r.call, RUNG_FUNC, (RUNG_DST,), row.header, r.code, source)
    call = tensix.spelled(row.call, version)
    func = re.match(r"\s*(\w+)", call)
    if func is None:
        raise ValueError(f"a row's call starts with its function: {call}")
    source = f"row {op} {row.unit} ({row.kind}), ttsim rel {verdict.rel:.3g}" + (
        f", card rel {rel:.3g}" if rel is not None else ""
    )
    init = tensix.spelled(row.init, version)
    return Rule(op, init, call, func.group(1), DST_ARGS[row.kind], row.header, "", source)


def place(call: str, func: str, values: dict[int, str]) -> str:
    """``call`` with the arguments of ``func`` at the positions of ``values`` replaced; each replaced argument must be
    an integer literal (the DST tile the row was checked on)."""
    at = call.find(func)
    if at < 0:
        raise ValueError(f"{func} is not called in {call}")
    start = call.index("(", at + len(func))
    depth, parts, begin, end = 0, [], start + 1, -1
    for k in range(start, len(call)):
        if call[k] == "(":
            depth += 1
        elif call[k] == ")":
            depth -= 1
            if depth == 0:
                parts.append(call[begin:k])
                end = k
                break
        elif call[k] == "," and depth == 1:
            parts.append(call[begin:k])
            begin = k + 1
    if end < 0:
        raise ValueError(f"unbalanced call {call}")
    for position, value in values.items():
        if not parts[position].strip().isdigit():
            raise ValueError(f"argument {position} of {func} in {call} is no DST tile: {parts[position]!r}")
        parts[position] = (" " if position else "") + value
    return call[: start + 1] + ",".join(parts) + call[end:]


def op_of(node: nodes.LibraryNode) -> str:
    """The Tensix row op a tile node runs; :class:`Refused` when none does."""
    if masked(node):
        raise Refused(f"{node.label}: a masked tile")
    if isinstance(node, TileBinop) and node.op in BINARY:
        return BINARY[node.op]
    if isinstance(node, TileUnop) and node.kind_a == "Symbol":  # a constant cast to the tile's type: a filled tile
        return "broadcast"
    if isinstance(node, TileUnop) and node.op in UNARY:
        return UNARY[node.op]
    if isinstance(node, TileReduce) and node.op in REDUCE and node.axis is None:
        return REDUCE[node.op]
    raise Refused(f"{node.label}: no Tensix row for this {type(node).__name__}")


def masked(node: nodes.LibraryNode) -> bool:
    return isinstance(node, TileBinop | TileUnop | TileReduce) and bool(node.has_mask)


def code(op: str, connectors: tuple[str, ...], value: float = 0.0, version: str = "v06") -> tuple[str, str, str]:
    """The init and the call of ``op`` on DST tiles named ``connectors`` for tt-metal ``version``, and its SFPI source
    ("" for a row); a fill writes ``value``."""
    r = rule(op, version)
    call = place(r.call, r.func, dict(zip(r.dst, connectors, strict=True)))
    if op == "broadcast":
        found = re.search(r",\s*[-+0-9.eE]+f?\s*\)", call)
        if found is None:
            raise ValueError(f"a fill call names its value: {r.call}")
        call = f"{call[: found.start()]}, {float(value)!r}f{call[found.end() - 1 :]}"
    return f"{r.init};", f"{call};", r.code


#: The DST tile connectors of each node's call.
CONNECTORS = {TileBinop: ("_a", "_b", "_c"), TileUnop: ("_c",), TileReduce: ("_dst", "_src", "_dst")}


def node_code(node: nodes.LibraryNode, version: str = "v06") -> tuple[str, str, str]:
    """``node``'s init and call on DST tiles named by its connectors, and its SFPI source, for tt-metal ``version``."""
    op = op_of(node)
    value = 0.0
    if op == "broadcast" and isinstance(node, TileUnop):
        try:
            value = float(str(node.expr_a))
        except ValueError as err:
            raise Refused(f"{node.label}: the symbol {node.expr_a} has no value at generation") from err
    return code(op, CONNECTORS[type(node)], value, version)


class ExpandTileTensix(ExpandTransformation):
    """A tile node as the init and call of its Tensix row (the card's tt-metal 0.63 spelling), on DST tiles named by
    its connectors."""

    environments: list = []

    @staticmethod
    def expansion(node: nodes.LibraryNode, parent_state: dace.SDFGState, parent_sdfg: dace.SDFG) -> nodes.Tasklet:
        init, call, source = node_code(node)
        return nodes.Tasklet(f"{node.label}_tensix", inputs=set(node.in_connectors), outputs=set(node.out_connectors),
                             code=f"{init}\n{call}", language=dace.Language.CPP, code_global=source)  # fmt: skip


class ExpandTileBinopTensix(ExpandTileTensix):
    pass


class ExpandTileUnopTensix(ExpandTileTensix):
    pass


class ExpandTileReduceTensix(ExpandTileTensix):
    """A full reduction folds ``_src`` into the core's partial tile ``_dst``; the host folds the partial tiles."""


EXPANSIONS: dict[type[TileBinop | TileUnop | TileReduce], type[ExpandTransformation]] = {
    TileBinop: ExpandTileBinopTensix,
    TileUnop: ExpandTileUnopTensix,
    TileReduce: ExpandTileReduceTensix,
}
for node_type, expansion in EXPANSIONS.items():
    if IMPLEMENTATION not in node_type.implementations:
        register_implementation(IMPLEMENTATION, expansion, node_type)


def use_tensix(sdfg: dace.SDFG) -> list[tuple[nodes.LibraryNode, dace.SDFGState]]:
    """The dispatch hook: every compute tile node of ``sdfg`` set to the ``tensix`` implementation; the nodes, with
    their states. :class:`Refused` names the first tile node without a Tensix expansion (admission)."""
    from dace.libraries.tileops.nodes import MaskedCopyLibraryNode

    found = []
    for node, state in sdfg.all_nodes_recursive():
        if isinstance(node, MaskedCopyLibraryNode) or not isinstance(node, nodes.LibraryNode):
            continue  # a copy is the reader's or the writer's: the kernel split moves it
        if type(node) not in EXPANSIONS:
            if type(node).__module__.startswith("dace.libraries.tileops"):
                raise Refused(f"{node.label}: no Tensix expansion of {type(node).__name__}")
            continue
        if not isinstance(state, dace.SDFGState):
            raise Refused(f"{node.label}: outside a state")
        node.implementation = IMPLEMENTATION
        found.append((node, state))
    return found
