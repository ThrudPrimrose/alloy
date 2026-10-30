# Copyright 2026 ETH Zurich and the Alloy authors.
"""Do-it-yourself advice for the emission path: when Alloy cannot emit or validate vector code for a
scope, the agent gets a text response with three parts — the reason, a do-it-yourself instruction, and
hints computed from the scope's own tasklets: every Python tasklet is collected, classified by what it
computes, and mapped to the relevant intrinsics of the target ISA and dtype (with their validation
status and traps). The hints are never generic: they name the actual tasklets and the actual spellings.
"""

import ast
import dataclasses

from alloy.isa.ops import OPS
from alloy.isa.table import Table, load

__all__ = ["Hint", "OpUse", "Spelling", "advice", "tasklet_hints"]

#: Python binary operators -> abstract op names (only ops the table covers).
_OP_NAMES: dict[type, str] = {
    ast.Add: "add",
    ast.Sub: "sub",
    ast.Mult: "mul",
    ast.Div: "div",
    ast.Mod: "mod",
    ast.BitAnd: "and",
    ast.BitOr: "or",
    ast.LShift: "shl",
    ast.RShift: "shr",
}

#: Function calls a tasklet may make -> abstract op names (sqrt and the transcendentals the table tiers).
_CALL_NAMES: dict[str, str] = {
    "sqrt": "sqrt",
    "fabs": "abs",
    "abs": "abs",
    "fmod": "mod",
    "sin": "sin",
    "cos": "cos",
    "exp": "exp",
    "min": "min",
    "max": "max",
}

#: Ops a tasklet's arithmetic maps to, in a readable order.
_ORDER = (
    "reduce_add",
    "fma",
    "sin",
    "cos",
    "exp",
    "sqrt",
    "mod",
    "div",
    "mul",
    "add",
    "sub",
    "min",
    "max",
    "abs",
    "neg",
    "select",
    "and",
    "or",
    "shl",
    "shr",
    "land",
    "lor",
)


@dataclasses.dataclass(slots=True, frozen=True)
class OpUse:
    """What one tasklet computes: its label, the abstract ops (and calls) it makes, and whether it
    reduces (a summing write-conflict on an output edge)."""

    tasklet: str
    language: str
    ops: tuple[str, ...]
    calls: tuple[str, ...]
    reduces: bool


@dataclasses.dataclass(slots=True, frozen=True)
class Spelling:
    """The relevant spelling for one abstract op: intrinsic or recipe, the trap if one is recorded,
    and the validation verdict (None = not verifiable on this host)."""

    op: str
    spelling: str
    signature: str
    trap: str
    verified: bool | None


@dataclasses.dataclass(slots=True, frozen=True)
class Hint:
    """One tasklet's do-it-yourself hints."""

    use: OpUse
    kind: str
    spellings: tuple[Spelling, ...]


def _uses(sdfg) -> list[OpUse]:
    """Every tasklet of ``sdfg`` and what it computes, in SDFG order."""
    import dace  # noqa: PLC0415 -- the ISA table itself stays dace-free
    from dace.frontend.operations import detect_reduction_type  # noqa: PLC0415
    from dace.sdfg import nodes  # noqa: PLC0415

    uses = []
    for node, state in sdfg.all_nodes_recursive():
        if not isinstance(node, nodes.Tasklet):
            continue
        ops: set[str] = set()
        calls: tuple[str, ...] = ()
        if node.code.language == dace.Language.Python:
            tree = ast.parse(node.code.as_string)
            for child in ast.walk(tree):
                if isinstance(child, ast.BinOp) and type(child.op) in _OP_NAMES:
                    ops.add(_OP_NAMES[type(child.op)])
                elif isinstance(child, ast.UnaryOp) and isinstance(child.op, ast.USub):
                    ops.add("neg")
                elif isinstance(child, ast.BoolOp):
                    ops.add("land" if isinstance(child.op, ast.And) else "lor")
                elif isinstance(child, ast.IfExp):
                    ops.add("select")
                elif isinstance(child, ast.Call):
                    name = ast.unparse(child.func).rsplit(".", 1)[-1]
                    if name in _CALL_NAMES:
                        ops.add(_CALL_NAMES[name])
                    calls += (name,)
        reduces = False
        if isinstance(state, dace.SDFGState):
            for edge in state.out_edges(node):
                # the summing write-conflict may sit on this edge or anywhere up its memlet tree
                # (e.g. only on the enclosing map exit's edge); check the whole path
                tree = {id(e): e for e in [edge, *state.memlet_tree(edge)]}.values()
                if any(
                    e.data.wcr is not None and detect_reduction_type(e.data.wcr) == dace.dtypes.ReductionType.Sum
                    for e in tree
                ):
                    reduces = True
                    break
        if {"mul", "add"} <= ops or {"mul", "sub"} <= ops:
            ops.add("fma")  # contractable pair: name the fused form too
        ordered = tuple(op for op in _ORDER if op in ops)
        uses.append(OpUse(node.label, str(node.code.language).split(".")[-1], ordered, calls, reduces))
    return uses


def _kind(use: OpUse) -> str:
    if use.reduces:
        return "reduction"
    if any(OPS[op].kind == "transcendental" for op in use.ops if op in OPS):
        return "libm (no native instruction: use a tier or call the vector library)"
    return "elementwise"


def _spelling(table: Table, isa: str, dtype: str, op: str, verdicts: dict[str, bool | None]) -> Spelling | None:
    """The target spelling for one abstract op, with its trap and validation verdict, or None when the
    op is not in the table for (isa, dtype) (e.g. integer ops on a float dtype)."""
    from alloy.isa.validate import host_can_run, validate  # noqa: PLC0415

    try:
        entry = table.entry(isa, op, dtype)
    except KeyError:
        return None
    if op not in verdicts:
        verdicts[op] = validate(isa, op, dtype, table).ok if host_can_run(isa, dtype) else None
    trap = entry.note if "trap" in entry.note else ""
    if entry.intrinsic:
        spelling = entry.intrinsic
    elif entry.recipe:
        spelling = "recipe: " + " -> ".join(entry.recipe[:3]) + (" -> ..." if len(entry.recipe) > 3 else "")
    elif entry.approximations:
        best = table.approx[entry.approximations[-1]]
        libraries = ", ".join(f"{k} {v}" for k, v in entry.libraries.items()) or "a vector math library"
        spelling = (
            f"no native instruction: tier '{entry.approximations[-1]}' ({best.error_ulp:.4g} ulp) or call {libraries}"
        )
    else:
        spelling = "(no spelling)"
    return Spelling(op, spelling, entry.signature, trap, verdicts[op])


def tasklet_hints(sdfg, isa: str, dtype: str, table: Table | None = None) -> list[Hint]:
    """Every tasklet's do-it-yourself hints for ``(isa, dtype)`` — relevant spellings, traps, and how
    each was validated on this host."""
    table = table or load()
    verdicts: dict[str, bool | None] = {}
    hints = []
    for use in _uses(sdfg):
        ops = ("reduce_add",) + use.ops if use.reduces and "reduce_add" not in use.ops else use.ops
        spellings = tuple(
            spelling for op in ops if (spelling := _spelling(table, isa, dtype, op, verdicts)) is not None
        )
        hints.append(Hint(use, _kind(use), spellings))
    return hints


_VERDICT_WORDS = {
    True: "verified on this host",
    False: "FAILED validation — check before use",
    None: "not verifiable on this host",
}


def advice(reason: str, sdfg, isa: str, dtype: str, table: Table | None = None) -> str:
    """The full do-it-yourself response body: the reason, the instruction, and the tasklet-derived
    hints. This is what the emission path returns when it cannot emit or validation fails."""
    table = table or load()
    lines = [
        f"Reason: {reason}",
        "",
        "Do it yourself: hand-write the loop in C with intrinsics — read the alloy skill's isa/ "
        "pages for the machine model and traps, `python -m alloy.isa lookup` for spellings, and "
        "verify each op with `python -m alloy.isa validate`.",
        "",
        f"Relevant hints from your tasklets ({isa}/{dtype}):",
        "",
    ]
    for hint in tasklet_hints(sdfg, isa, dtype, table):
        use = hint.use
        ops = ", ".join(use.ops) if use.ops else "(no recognized ops)"
        suffix = "; reduces via summing write-conflict" if use.reduces else ""
        lines.append(f"- tasklet '{use.tasklet}' [{hint.kind}]: {ops}{suffix}")
        for spelling in hint.spellings:
            sig = f" {spelling.signature}" if spelling.signature else ""
            lines.append(f"    {spelling.op}: {spelling.spelling}{sig}  [{_VERDICT_WORDS[spelling.verified]}]")
            if spelling.trap:
                lines.append(f"      trap: {spelling.trap}")
    return "\n".join(lines)
