# Copyright 2026 ETH Zurich and the Alloy authors.
"""Do-it-yourself advice for the emission path: when Alloy cannot emit or validate vector code for a
scope, the agent gets a text response with three parts — the reason, a do-it-yourself instruction, and
hints computed from the scope's own tasklets: every Python tasklet is collected, classified by what it
computes, and mapped to the relevant intrinsics of the target ISA and dtype (with their validation
status and traps). The hints are never generic: they name the actual tasklets and the actual spellings.
"""

import ast
import dataclasses
from collections import Counter

from alloy.isa.mathcheck import HEADERS, validate_kernel
from alloy.isa.mathkernels import LEVELS, NEEDS_IEEE, functions, kernel, ladder, render, target_of
from alloy.isa.ops import OPS, called_name
from alloy.isa.table import DTYPES, Table, load
from alloy.isa.validate import host_can_run, validate

__all__ = ["Hint", "OpUse", "Spelling", "advice", "tasklet_hints"]

#: Python binary operators -> abstract op names (only ops the table covers).
OP_NAMES: dict[type, str] = {
    ast.Add: "add",
    ast.Sub: "sub",
    ast.Mult: "mul",
    ast.Div: "div",
    ast.Mod: "mod",
    ast.Pow: "pow",
    ast.BitAnd: "and",
    ast.BitOr: "or",
    ast.LShift: "shl",
    ast.RShift: "shr",
}

#: Function calls a tasklet may make -> abstract op names: the renamed ones, then those spelled like their op.
CALL_NAMES: dict[str, str] = {
    "fabs": "abs",
    "fmod": "mod",
    "py_mod": "mod",
    "PyMod": "mod",
    "ITE": "select",
    "ln": "log",
    **{
        name: name
        for name in (
            "sqrt abs sin cos tan exp exp2 exp10 expm1 min max log log2 log10 log1p atan asin acos sinh cosh tanh pow"
        ).split()
    },
}

#: Ops a tasklet's arithmetic maps to, in a readable order.
OP_ORDER = tuple(
    (
        "reduce_add fma sin cos tan exp exp2 exp10 expm1 log log2 log10 log1p pow atan asin acos sinh cosh tanh sqrt mod "
        "div mul add sub min max abs neg lt select and or shl shr land lor"
    ).split()
)


@dataclasses.dataclass(slots=True, frozen=True)
class OpUse:
    """What one tasklet or library node computes: its label, the abstract ops, what the table cannot spell
    (``skipped``), whether it reduces (a summing write-conflict) or under which other conflict (``conflict``), and
    the lane it computes in (``dtype``, empty for lanes the table has no spelling for, ``""`` also for complex)."""

    tasklet: str
    ops: tuple[str, ...]
    skipped: tuple[str, ...]
    reduces: bool
    conflict: str = ""
    dtype: str = ""


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


def expression_ops(code: str) -> tuple[set[str], set[str]]:
    """The abstract ops of a Python tasklet's expressions, and what the table has no op for."""
    ops: set[str] = set()
    skipped: set[str] = set()
    for child in ast.walk(ast.parse(code)):
        if isinstance(child, ast.BinOp | ast.AugAssign):
            name = OP_NAMES.get(type(child.op))
            ops.add(name) if name else skipped.add(type(child.op).__name__)
            if isinstance(child, ast.BinOp) and is_fused(child):
                ops.add("fma")
        elif isinstance(child, ast.UnaryOp) and isinstance(child.op, ast.USub):
            if not isinstance(child.operand, ast.Constant):
                ops.add("neg")
        elif isinstance(child, ast.BoolOp):
            ops.add("land" if isinstance(child.op, ast.And) else "lor")
        elif isinstance(child, ast.IfExp | ast.If):
            ops.add("select")
        elif isinstance(child, ast.Compare):
            ops.add("lt")
        elif isinstance(child, ast.Call):
            name = called_name(child)
            ops.add(CALL_NAMES[name]) if name in CALL_NAMES else skipped.add(name)
    return ops, skipped


def is_fused(node: ast.BinOp) -> bool:
    """A product summed in one expression, which an fma can fuse."""
    if not isinstance(node.op, ast.Add | ast.Sub):
        return False
    return any(isinstance(side, ast.BinOp) and isinstance(side.op, ast.Mult) for side in (node.left, node.right))


def is_copy(code: str) -> bool:
    """A tasklet that only forwards a value: ``out = in``."""
    body = ast.parse(code).body
    return len(body) == 1 and isinstance(body[0], ast.Assign) and isinstance(body[0].value, ast.Name)


def lane_of(state, node) -> str:
    """The lane a node writes in, or ``""`` when the table has no spelling for it (complex, narrow integers)."""
    import dace

    names = {dace.float64: "f64", dace.float32: "f32", dace.float16: "f16", dace.int64: "i64", dace.int32: "i32"}
    for edge in state.out_edges(node):
        if edge.data.data is not None:
            return names.get(state.sdfg.arrays[edge.data.data].dtype, "")
    return ""


def conflict_of(state, node) -> str:
    """The write-conflict ``node``'s output meets, on its memlet tree or past a private access node, or ``""``."""
    from dace.frontend.operations import detect_reduction_type
    from dace.sdfg import nodes

    for edge in state.out_edges(node):
        forwarded = state.out_edges(edge.dst) if isinstance(edge.dst, nodes.AccessNode) else []
        walked = [edge, *state.memlet_tree(edge), *(e for f in forwarded for e in [f, *state.memlet_tree(f)])]
        for e in walked:
            if e.data.wcr is not None:
                return str(detect_reduction_type(e.data.wcr)).rsplit(".", 1)[-1]
    return ""


def library_use(state, node) -> OpUse:
    """A library node: its name in the advice, a reduce by its conflict, the rest as sum-of-products."""
    from dace.frontend.operations import detect_reduction_type
    from dace.libraries.standard.nodes import Reduce

    if isinstance(node, Reduce):
        kind = str(detect_reduction_type(node.wcr)).rsplit(".", 1)[-1]
        ops, conflict = ("reduce_add",) if kind == "Sum" else (), "" if kind == "Sum" else kind
        return OpUse(node.label, ops, (type(node).__name__,), kind == "Sum", conflict, lane_of(state, node))
    return OpUse(node.label, ("fma", "reduce_add"), (type(node).__name__,), False, "", lane_of(state, node))


def op_uses(sdfg) -> list[OpUse]:
    """Every computing tasklet and library node of ``sdfg`` and what it computes, in SDFG order."""
    import dace
    from dace.sdfg import nodes

    uses = []
    for node, state in sdfg.all_nodes_recursive():
        if isinstance(node, nodes.LibraryNode) and isinstance(state, dace.SDFGState):
            uses.append(library_use(state, node))
        if not isinstance(node, nodes.Tasklet):
            continue
        ops: set[str] = set()
        skipped: set[str] = set()
        kind = conflict_of(state, node) if isinstance(state, dace.SDFGState) else ""
        if node.code.language == dace.Language.Python:
            if is_copy(node.code.as_string) and not kind:
                continue
            ops, skipped = expression_ops(node.code.as_string)
        dtype = lane_of(state, node) if isinstance(state, dace.SDFGState) else ""
        ordered = tuple(op for op in OP_ORDER if op in ops)
        uses.append(
            OpUse(node.label, ordered, tuple(sorted(skipped)), kind == "Sum", kind if kind != "Sum" else "", dtype)
        )
    return uses


def use_kind(use: OpUse) -> str:
    if use.reduces or use.conflict:
        return "reduction"
    if any(op in functions() for op in use.ops):
        return "libm (no native instruction: inline a kernel or call the vector library)"
    return "elementwise"


def op_spelling(
    table: Table, isa: str, dtype: str, op: str, verdicts: dict[str, bool | None], recommended: str = ""
) -> Spelling | None:
    """The target spelling for one abstract op, with its trap and validation verdict, or None when the
    op is not in the table for (isa, dtype) (e.g. integer ops on a float dtype)."""
    if op not in OPS:
        return kernel_spelling(isa, dtype, op, recommended)
    try:
        entry = table.entry(isa, op, dtype)
    except KeyError:
        return None
    if op not in verdicts:
        verdicts[op] = validate(isa, op, dtype, table).ok if host_can_run(isa, dtype) else None
    if entry.intrinsic:
        spelling = entry.intrinsic
    elif entry.recipe:
        spelling = "recipe: " + "; ".join(entry.code)
    elif entry.approximations:
        libraries = ", ".join(f"{k} {v}" for k, v in entry.libraries.items()) or "a vector math library"
        spelling = f"{kernel_summary(isa, dtype, op, recommended)}; or call {libraries}"
    else:
        spelling = "(no spelling)"
    return Spelling(op, spelling, entry.signature, entry.note, verdicts[op])


def kernel_summary(isa: str, dtype: str, fn: str, recommended: str = "") -> str:
    """One line naming ``fn``'s kernels and the one this build should take; the C is one CLI call away."""
    target = target_of(isa)
    if target not in HEADERS or dtype not in DTYPES:
        return f"no kernel for {isa}/{dtype}"
    levels = ", ".join(
        f"{k.level} {k.error_ulp:.3g} ulp ({render(k, target).intrinsics} intrinsics)" for k in ladder(fn, dtype)
    )
    contract = kernel(fn, dtype, recommended).contract if recommended else ""
    pick = f"; take {recommended} where the inputs hold its contract ({contract})" if recommended else ""
    if fn in NEEDS_IEEE:
        pick += "; under reassociation no level compiles: call the library"
    return f"inline intrinsics: {levels}{pick}; ask `kernel {isa} {fn} {dtype}` for the C"


def kernel_spelling(isa: str, dtype: str, fn: str, recommended: str = "") -> Spelling | None:
    """The hint of a math function outside the abstract ops, with the gate's verdict on its recommended kernel."""
    if dtype not in DTYPES:
        return None
    level = recommended or LEVELS[0]
    arguments = ", ".join(kernel(fn, dtype, level).args)
    verdict = validate_kernel(fn, dtype, level, target_of(isa)).ok
    return Spelling(fn, kernel_summary(isa, dtype, fn, recommended), f"({arguments}) -> v", "", verdict)


def tasklet_hints(sdfg, isa: str, dtype: str, table: Table | None = None, recommended: str = "") -> list[Hint]:
    """Every tasklet's do-it-yourself hints for ``isa`` in the tasklet's own lane (``dtype`` when it has none) --
    relevant spellings, traps, and how each was validated on this host. ``recommended`` names the kernel level the
    build should take."""
    table = table or load()
    verdicts: dict[tuple[str, str], dict[str, bool | None]] = {}
    hints = []
    for use in op_uses(sdfg):
        lane = use.dtype or dtype
        ops = ("reduce_add",) + use.ops if use.reduces and "reduce_add" not in use.ops else use.ops
        known = verdicts.setdefault((isa, lane), {})
        spellings = tuple(
            spelling for op in ops if (spelling := op_spelling(table, isa, lane, op, known, recommended)) is not None
        )
        hints.append(Hint(use, use_kind(use), spellings))
    return hints


VERDICT_WORDS = {
    True: "verified on this host",
    False: "FAILED validation — check before use",
    None: "not verifiable on this host",
}


def advice(reason: str, sdfg, isa: str, dtype: str, table: Table | None = None, recommended: str = "") -> str:
    """The full do-it-yourself response body: the reason, the instruction, and the tasklet-derived
    hints. This is what the emission path returns when it cannot emit or validation fails."""
    table = table or load()
    lines = [
        f"Reason: {reason}",
        "",
        "Do it yourself: hand-write the loop in C with intrinsics. Spellings come from `lookup`, math functions from "
        "`kernel`, loop shapes from `skeleton`: the `alloy_isa` tool in a benchmark, `python -m alloy.isa` elsewhere.",
        "",
        f"Relevant hints from your tasklets ({isa}/{dtype}):",
        "",
    ]
    hints = tasklet_hints(sdfg, isa, dtype, table, recommended)
    repeats = Counter((hint.use.ops, hint.use.skipped, hint.kind) for hint in hints)
    shown: set[tuple[tuple[str, ...], tuple[str, ...], str]] = set()
    for hint in hints:
        key = (hint.use.ops, hint.use.skipped, hint.kind)
        if key in shown:
            continue
        shown.add(key)
        lines += hint_lines(hint, repeats[key])
    if not hints:
        lines.append("- no tasklet or library node computes here")
    return "\n".join(lines)


def hint_lines(hint: Hint, repeats: int) -> list[str]:
    """One hint's lines; ``repeats`` tasklets share it."""
    use = hint.use
    ops = ", ".join(use.ops) if use.ops else "(no recognized ops)"
    times = f" and {repeats - 1} more like it" if repeats > 1 else ""
    suffix = "; reduces via summing write-conflict" if use.reduces else ""
    if use.conflict:
        suffix = f"; reduces via a {use.conflict} write-conflict, which the table has no reduction for"
    if use.skipped:
        suffix += f"; no table row for {', '.join(use.skipped)}"
    if not use.dtype and not use.reduces:
        suffix += "; check the lane type: the table has no complex or narrow integer rows"
    lines = [f"- tasklet '{use.tasklet}'{times} [{hint.kind}]: {ops}{suffix}"]
    for spelling in hint.spellings:
        sig = f" {spelling.signature}" if spelling.signature else ""
        lines.append(f"    {spelling.op}: {spelling.spelling}{sig}  [{VERDICT_WORDS[spelling.verified]}]")
        if spelling.trap:
            lines.append(f"      note: {spelling.trap}")
    return lines
