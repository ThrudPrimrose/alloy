# Copyright 2026 ETH Zurich and the Alloy authors.
"""Whether every libm call of a scope provably stays inside a rung's contract, by interval arithmetic over the scope's
tasklets from the inputs' declared ranges.

A declared range is the caller's statement of an input's values (the bench manifest's ``domain`` of an argument). The
proof runs over Python tasklets: constants, the declared inputs, sums, differences, products, quotients by a range
that excludes zero, integer powers, and functions monotone on their range. A value has no proven range when it comes
from an undeclared input, a symbol, a container the scope both reads and writes outside its transients, an
accumulation (a write-conflict resolution), a tasklet in another language, or a value that does not settle in a few
rounds (an earlier iteration's). A rung's contract is read from its kernel's ``contract`` text (:func:`contract`), so
the documentation and the check cannot differ."""

import ast
import math
import re
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass

import dace
from dace.sdfg import nodes
from dace.sdfg import utils as sdutil

from alloy.frontend.scopes import Scope
from alloy.isa import approximation, mathkernels

__all__ = ["Interval", "contract", "declared", "proof_gap", "scope_ranges", "unread_calls"]

#: The largest finite double: a declared sign domain is finite but unbounded.
BIG = sys.float_info.max
#: Rounds a container's range may widen before it is given up as unproven.
ROUNDS = 8
#: The smallest positive normal per dtype.
NORMAL = {"f64": sys.float_info.min, "f32": 1.1754943508222875e-38}


@dataclass(slots=True, frozen=True)
class Interval:
    """The closed range ``[lo, hi]`` of a value; an infinite end means the value may be infinite."""

    lo: float
    hi: float

    def within(self, other: "Interval") -> bool:
        return other.lo <= self.lo and self.hi <= other.hi

    def join(self, other: "Interval") -> "Interval":
        return Interval(min(self.lo, other.lo), max(self.hi, other.hi))

    def text(self) -> str:
        return f"[{self.lo:.6g}, {self.hi:.6g}]"


EVERYTHING = Interval(-math.inf, math.inf)

#: A bench sign domain as a range (``positive`` admits only normals: the bench nudges a drawn zero to one).
SIGNS = {
    "positive": Interval(sys.float_info.min, BIG),
    "nonneg": Interval(0.0, BIG),
    "negative": Interval(-BIG, -sys.float_info.min),
    "nonpos": Interval(-BIG, 0.0),
}


def declared(domains: Mapping[str, object]) -> dict[str, Interval]:
    """Each input's range from a manifest's ``domain`` entries (a sign name or ``[low, high]``); ``any`` and
    ``None`` declare nothing."""
    out: dict[str, Interval] = {}
    for name, domain in domains.items():
        if isinstance(domain, str) and domain in SIGNS:
            out[name] = SIGNS[domain]
        elif isinstance(domain, list | tuple) and len(domain) == 2:
            lo, hi = (float(v) for v in domain)
            out[name] = Interval(min(lo, hi), max(lo, hi))
    return out


BOUND = re.compile(r"^\|x\| <= ([0-9.e+-]+)$")
SPAN = re.compile(r"^(-?[0-9.e+]+) <= x <= ([0-9.e+]+)$")
ABOVE = re.compile(r"^x > (-?[0-9.e+]+)$")


def contract(text: str, dtype: str) -> Interval | None:
    """The argument range a one-argument kernel's ``contract`` text admits; ``None`` for a contract over two
    arguments, which no range proves here."""
    if text in ("any input", "|x| <= 1 or NaN out"):  # outside [-1, 1] the kernel answers NaN, as libm does
        return EVERYTHING
    parts = [p.strip() for p in text.split(",")]
    if parts[0] != "finite":
        return None
    rest = ", ".join(parts[1:])
    if not rest:
        return Interval(-BIG, BIG)
    if rest == "positive, normal":
        return Interval(NORMAL[dtype], BIG)
    if (m := BOUND.match(rest)) is not None:
        return Interval(-float(m.group(1)), float(m.group(1)))
    if (m := SPAN.match(rest)) is not None:
        return Interval(float(m.group(1)), float(m.group(2)))
    if (m := ABOVE.match(rest)) is not None:
        return Interval(math.nextafter(float(m.group(1)), math.inf), BIG)
    raise ValueError(f"contract {text!r} is in no form the range proof reads")


def safe(f: Callable[[float], float], x: float) -> float:
    try:
        return f(x)
    except OverflowError:
        return math.inf
    except ValueError:
        return math.nan


def monotone(f: Callable[[float], float], x: Interval, low: float = -math.inf) -> Interval | None:
    """``f`` over ``x`` for an increasing ``f`` defined from ``low`` on."""
    if x.lo < low:
        return None
    return Interval(safe(f, x.lo), safe(f, x.hi))


def product(a: Interval, b: Interval) -> Interval:
    ends = [p for x in (a.lo, a.hi) for y in (b.lo, b.hi) if not math.isnan(p := x * y)]
    return Interval(min(ends), max(ends)) if len(ends) == 4 else EVERYTHING


#: Calls the proof evaluates: monotone increasing ones from where they are defined, and bounded ones.
INCREASING: dict[str, tuple[Callable[[float], float], float]] = {
    "exp": (math.exp, -math.inf),
    "exp2": (lambda v: 2.0**v, -math.inf),
    "expm1": (math.expm1, -math.inf),
    "log": (math.log, 0.0),
    "log2": (math.log2, 0.0),
    "log10": (math.log10, 0.0),
    "log1p": (math.log1p, -1.0),
    "sqrt": (math.sqrt, 0.0),
    "cbrt": (lambda v: math.copysign(abs(v) ** (1 / 3), v), -math.inf),
    "tanh": (math.tanh, -math.inf),
    "atan": (math.atan, -math.inf),
    "sinh": (math.sinh, -math.inf),
}
BOUNDED = {"sin": Interval(-1.0, 1.0), "cos": Interval(-1.0, 1.0)}
IDENTITY = frozenset({"float", "double", "float64", "float32"})


def call_name(func: ast.expr) -> str:
    name = func.attr if isinstance(func, ast.Attribute) else func.id if isinstance(func, ast.Name) else ""
    return name[:-1] if name.endswith("f") and name[:-1] in INCREASING.keys() | BOUNDED.keys() else name


@dataclass(slots=True)
class Evaluation:
    """One tasklet's evaluation: the range of every name it binds, and each libm call's argument ranges."""

    names: dict[str, Interval | None]
    calls: list[tuple[str, tuple[Interval | None, ...]]]


def expression(e: ast.expr, ev: Evaluation) -> Interval | None:
    """``e``'s range, ``None`` when unproven."""
    if isinstance(e, ast.Constant) and isinstance(e.value, int | float) and not isinstance(e.value, bool):
        return Interval(float(e.value), float(e.value))
    if isinstance(e, ast.Name):
        return ev.names.get(e.id)
    if isinstance(e, ast.Subscript):
        return expression(e.value, ev)
    if isinstance(e, ast.UnaryOp) and isinstance(e.op, ast.USub | ast.UAdd):
        x = expression(e.operand, ev)
        return None if x is None else x if isinstance(e.op, ast.UAdd) else Interval(-x.hi, -x.lo)
    if isinstance(e, ast.BinOp):
        return binary(e, ev)
    if isinstance(e, ast.Call):
        return called(e, ev)
    return None


def binary(e: ast.BinOp, ev: Evaluation) -> Interval | None:
    a = expression(e.left, ev)
    if isinstance(e.op, ast.Pow) and isinstance(e.right, ast.Constant) and isinstance(e.right.value, int):
        if a is None or e.right.value < 0:
            return None
        result = Interval(1.0, 1.0)
        for _ in range(e.right.value):
            result = product(result, a)
        return Interval(0.0, result.hi) if e.right.value % 2 == 0 and a.lo < 0 < a.hi else result
    b = expression(e.right, ev)
    if isinstance(e.op, ast.Pow):  # a non-integer power renders as a pow call
        ev.calls.append(("pow", (a, b)))
        return None
    if a is None or b is None:
        return None
    if isinstance(e.op, ast.Add):
        return Interval(a.lo + b.lo, a.hi + b.hi)
    if isinstance(e.op, ast.Sub):
        return Interval(a.lo - b.hi, a.hi - b.lo)
    if isinstance(e.op, ast.Mult):
        return product(a, b)
    if isinstance(e.op, ast.Div) and (b.lo > 0 or b.hi < 0):
        return product(a, Interval(1.0 / b.hi, 1.0 / b.lo))
    return None


def called(e: ast.Call, ev: Evaluation) -> Interval | None:
    name = call_name(e.func)
    args = tuple(expression(a, ev) for a in e.args)
    if name in mathkernels.functions():
        ev.calls.append((name, args))
    if len(args) != 1 and name not in ("min", "max", "fmin", "fmax"):
        return None
    if None in args:
        return None
    known = [a for a in args if a is not None]
    if name in ("min", "fmin", "max", "fmax"):
        pick = min if "min" in name else max
        return Interval(pick(a.lo for a in known), pick(a.hi for a in known))
    (x,) = known
    if name in IDENTITY:
        return x
    if name in ("abs", "fabs"):
        return Interval(0.0 if x.lo <= 0 <= x.hi else min(abs(x.lo), abs(x.hi)), max(abs(x.lo), abs(x.hi)))
    if name in BOUNDED:
        return BOUNDED[name]
    if name in INCREASING:
        f, low = INCREASING[name]
        return monotone(f, x, low)
    return None


def evaluate(tasklet: nodes.Tasklet, inputs: dict[str, Interval | None]) -> Evaluation | None:
    """The tasklet's statements in order from its inputs' ranges; ``None`` for a tasklet the proof cannot read."""
    if tasklet.language != dace.Language.Python:
        return None
    ev = Evaluation(dict(inputs), [])
    for statement in ast.parse(tasklet.code.as_string).body:
        if isinstance(statement, ast.Assign):
            value = expression(statement.value, ev)
            for target in statement.targets:
                name = target.value if isinstance(target, ast.Subscript) else target
                if isinstance(name, ast.Name):
                    ev.names[name.id] = value
        elif isinstance(statement, ast.Expr):
            expression(statement.value, ev)
        else:
            return None
    return ev


def unread_calls(tasklet: nodes.Tasklet) -> list[tuple[nodes.Tasklet, str, tuple[Interval | None, ...]]]:
    """Every ladder call of a tasklet the proof cannot read, each with an unproven argument."""
    return [(tasklet, fn, (None,)) for fn in approximation.called_functions(tasklet.code.as_string)]


def scope_ranges(
    sdfg: dace.SDFG, ranges: Mapping[str, Interval]
) -> tuple[dict[str, Interval | None], list[tuple[nodes.Tasklet, str, tuple[Interval | None, ...]]]]:
    """Every container's proven range in ``sdfg`` (``None``: unproven) from the declared ``ranges`` of its inputs,
    and every libm call with its arguments' ranges."""
    states = [b for b in sdfg.all_control_flow_blocks() if isinstance(b, dace.SDFGState)]
    writes = [
        (s, e) for s in states for e in s.edges() if isinstance(e.dst, nodes.AccessNode) and e.data.data is not None
    ]
    written = {e.dst.data for _, e in writes}
    unproven = {e.dst.data for _, e in writes if e.data.wcr is not None}
    unproven |= {name for name in written if not sdfg.arrays[name].transient}
    known: dict[str, Interval | None] = {
        name: ranges.get(name) for name, desc in sdfg.arrays.items() if not desc.transient and name not in written
    }
    known |= dict.fromkeys(unproven)

    def put(target: str, value: Interval | None) -> None:
        held = known.get(target, value)
        known[target] = None if value is None or held is None else held.join(value)

    calls: list[tuple[nodes.Tasklet, str, tuple[Interval | None, ...]]] = []
    skipped: list[nodes.Tasklet] = []
    before: dict[str, Interval | None] = {}
    for _ in range(ROUNDS):
        calls, skipped, before = [], [], dict(known)
        for state in states:
            for node in sdutil.dfs_topological_sort(state):
                if isinstance(node, nodes.AccessNode):  # a copy (through any scope): it holds what its source holds
                    for e in state.in_edges(node):
                        source = state.memlet_path(e)[0].src
                        if isinstance(source, nodes.AccessNode) and source.data in known:
                            put(node.data, known[source.data])
                if not isinstance(node, nodes.Tasklet):
                    continue
                reads = [(e.dst_conn, e.data.data) for e in state.in_edges(node) if e.dst_conn and e.data.data]
                if any(name not in known for _, name in reads):
                    skipped.append(node)  # a transient nothing has written yet: next round
                    continue
                ev = evaluate(node, {conn: known[name] for conn, name in reads})
                if ev is None:
                    calls += unread_calls(node)
                    continue
                calls += [(node, fn, args) for fn, args in ev.calls]
                for e in state.out_edges(node):
                    if (target := state.memlet_path(e)[-1].data.data) is not None:
                        put(target, None if e.src_conn is None else ev.names.get(e.src_conn))
        if known == before:
            return known, calls + [c for t in skipped for c in unread_calls(t)]
    unsettled = {name: None for name, value in known.items() if before.get(name, value) != value}
    return known | unsettled, calls + [c for t in skipped for c in unread_calls(t)]


def proof_gap(scope: Scope, ranges: Mapping[str, Interval], level: str, dtypes: tuple[str, ...]) -> str:
    """Why rung ``level`` is not proven for ``scope``'s calls at every one of ``dtypes``, or ``""`` when it is."""
    if any(isinstance(n, nodes.NestedSDFG) for n, _ in scope.sdfg.all_nodes_recursive()):
        return "a nested SDFG's values have no proven range"
    _, calls = scope_ranges(scope.sdfg, ranges)
    if not calls:
        return "no libm call the proof can read"
    for tasklet, fn, args in calls:
        for dtype in dtypes:
            k = mathkernels.kernel(fn, dtype, level)
            allowed = contract(k.contract, dtype)
            if allowed is None or len(args) != 1:
                return f"{fn} in {tasklet.label}: the {level} contract ({k.contract}) spans two arguments"
            (x,) = args
            if x is None:
                return f"argument of {fn} in {tasklet.label} has no proven range"
            if not x.within(allowed):
                return f"argument of {fn} in {tasklet.label} spans {x.text()}, outside {level} ({k.contract})"
    return ""
