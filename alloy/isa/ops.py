# Copyright 2026 ETH Zurich and the Alloy authors.
"""The machine abstract math ISA: the small op vocabulary an agent reasons in when it reads or writes vector
code, independent of the target. Every entry maps to a concrete intrinsic per ISA and dtype in
:data:`alloy.isa.table`; the table, not this module, carries spellings and operand orders.

Two operand conventions hold across the elementwise and bitwise ops: a binary op accepts a scalar in
either operand position — the scalar is broadcast to all lanes (per ISA: an EVEX embedded broadcast on
AVX-512, an explicit ``set1``/``vdup``/``svdup`` elsewhere, see the ISA notes); and integer-lane ops
(``and`` … ``lor``, integer ``mod``) are looked up under the ``i64``/``i32`` dtypes, the float ones under
``f64``/``f32``."""

from pydantic.dataclasses import dataclass

from alloy.records import RECORD

__all__ = ["AbstractOp", "OPS"]


@dataclass(slots=True, frozen=True, config=RECORD)
class AbstractOp:
    """One abstract vector op: what it computes, in math, without any target spelling.

    ``kind`` is ``memory`` (moves elements), ``elementwise`` (lane-wise, one result lane per operand
    lane), ``bitwise`` (integer lane-wise), ``shift`` (integer lane counts), ``logical`` (per-lane
    zero tests combined), ``reduction`` (the whole vector to one scalar), ``mask`` (a lane predicate),
    ``transcendental`` (no native instruction) or ``constant`` (no data operand)."""

    name: str
    symbol: str
    kind: str
    operands: int
    result: str
    semantics: str


#: The abstract op set, keyed by name. This is the ISA an agent's plan is phrased in; the per-target
#: spelling is always a table lookup away, never memorized.
OPS: dict[str, AbstractOp] = {
    "load": AbstractOp("load", "v = p[]", "memory", 1, "vector", "v[j] = p[j] for every active lane j"),
    "store": AbstractOp("store", "p[] = v", "memory", 2, "none", "p[j] = v[j] for every active lane j"),
    "gather": AbstractOp("gather", "v = p[idx]", "memory", 2, "vector", "v[j] = base[idx[j]] (indirect load)"),
    "scatter": AbstractOp("scatter", "p[idx] = v", "memory", 3, "none", "base[idx[j]] = v[j] (indirect store)"),
    "broadcast": AbstractOp(
        "broadcast", "v = s", "elementwise", 1, "vector", "v[j] = s for every lane j (s is a scalar)"
    ),
    "add": AbstractOp("add", "+", "elementwise", 2, "vector", "v[j] = a[j] + b[j]"),
    "sub": AbstractOp("sub", "-", "elementwise", 2, "vector", "v[j] = a[j] - b[j]"),
    "mul": AbstractOp("mul", "*", "elementwise", 2, "vector", "v[j] = a[j] * b[j]"),
    "div": AbstractOp("div", "/", "elementwise", 2, "vector", "v[j] = a[j] / b[j]"),
    "mod": AbstractOp(
        "mod",
        "%",
        "elementwise",
        2,
        "vector",
        "v[j] = a[j] % b[j]: fmod for f64/f32 (sign of a), truncated remainder for i64/i32",
    ),
    "fma": AbstractOp("fma", "a*b + c", "elementwise", 3, "vector", "one rounding: v[j] = a[j]*b[j] + c[j]"),
    "sqrt": AbstractOp("sqrt", "sqrt", "elementwise", 1, "vector", "v[j] = sqrt(x[j])"),
    "min": AbstractOp("min", "min", "elementwise", 2, "vector", "v[j] = min(a[j], b[j])"),
    "max": AbstractOp("max", "max", "elementwise", 2, "vector", "v[j] = max(a[j], b[j])"),
    "abs": AbstractOp("abs", "|x|", "elementwise", 1, "vector", "v[j] = |x[j]|"),
    "neg": AbstractOp("neg", "-x", "elementwise", 1, "vector", "v[j] = -x[j]"),
    "select": AbstractOp(
        "select", "m ? a : b", "elementwise", 3, "vector", "v[j] = mask[j] ? t[j] : f[j] (per-lane blend)"
    ),
    "and": AbstractOp("and", "&", "bitwise", 2, "vector", "v[j] = a[j] & b[j] (integer lanes)"),
    "or": AbstractOp("or", "|", "bitwise", 2, "vector", "v[j] = a[j] | b[j] (integer lanes)"),
    "shl": AbstractOp("shl", "<<", "shift", 2, "vector", "v[j] = a[j] << b[j] (integer lanes)"),
    "shr": AbstractOp("shr", ">>", "shift", 2, "vector", "v[j] = a[j] >> b[j], logical (integer lanes)"),
    "land": AbstractOp(
        "land",
        "&&",
        "logical",
        2,
        "vector",
        "(a[j] != 0) && (b[j] != 0) as the ISA's lane truth: all-ones lanes, or a k/predicate bit",
    ),
    "lor": AbstractOp(
        "lor",
        "||",
        "logical",
        2,
        "vector",
        "(a[j] != 0) || (b[j] != 0) as the ISA's lane truth: all-ones lanes, or a k/predicate bit",
    ),
    "reduce_add": AbstractOp("reduce_add", "sum(v)", "reduction", 1, "scalar", "s = sum of every active lane of v"),
    "exp": AbstractOp("exp", "e^x", "transcendental", 1, "vector", "v[j] = exp(x[j])"),
    "sin": AbstractOp("sin", "sin x", "transcendental", 1, "vector", "v[j] = sin(x[j])"),
    "cos": AbstractOp("cos", "cos x", "transcendental", 1, "vector", "v[j] = cos(x[j])"),
    "gen_mask": AbstractOp(
        "gen_mask", "j < N - i", "mask", 2, "mask", "lane j active iff i + j < N (the loop tail predicate)"
    ),
    "zero": AbstractOp("zero", "0", "constant", 0, "vector", "v[j] = 0 for every lane j"),
}
