# Copyright 2026 ETH Zurich and the Alloy authors.
"""Maintainer tool: fits the polynomials and writes ``mathkernels.toml`` (``python -m alloy.isa.mathfit``).

A program is written once per function family and parameterized by dtype and level. Coefficients are Chebyshev
interpolants in high precision, rounded to the lane type. Each kernel is then measured on this host and the worst
error across the x86 ISAs is recorded; the gate in tests/test_isa_kernels.py re-measures it."""

import concurrent.futures
import json
import math
import struct
import sys

import mpmath as mp

from alloy.isa.mathcheck import measure
from alloy.isa.mathkernels import KERNELS_PATH, LEVELS, Grid, Kernel

mp.mp.dps = 200

MANTISSA = {"f64": 52, "f32": 23}
BIAS = {"f64": 1023, "f32": 127}
SIGN_SHIFT = {"f64": 63, "f32": 31}
HUGE = {"f64": 1e300, "f32": 1e30}
TINY = {"f64": 1e-300, "f32": 1e-30}
#: Largest |x| the exp core holds, so its 2^q stays normal.
EXP_MAX = {"f64": 700.0, "f32": 87.0}
#: Largest |x| the trig reductions hold under their contract.
TRIG_MAX = {"f64": 1048576.0, "f32": 8192.0}
#: |y*log(x)| the double-word strict pow keeps accurate.
POW_MAX = {"f64": 64.0, "f32": 32.0}

DEGREES = {  # function -> dtype -> polynomial degree per level (strict, relaxed, fast)
    "sin": {"f64": (8, 7, 4), "f32": (4, 3, 2)},
    "tan": {"f64": (13, 12, 5), "f32": (6, 5, 2)},
    "exp": {"f64": (10, 9, 4), "f32": (5, 4, 2)},
    "exp2": {"f64": (11, 10, 5), "f32": (5, 4, 3)},
    "exp10": {"f64": (11, 10, 5), "f32": (5, 4, 3)},
    "expm1": {"f64": (10, 9, 5), "f32": (5, 4, 3)},
    "log": {"f64": (7, 6, 2), "f32": (3, 2, 1)},
    "atan": {"f64": (19, 18, 8), "f32": (8, 7, 3)},
    "asin": {"f64": (13, 12, 4), "f32": (5, 4, 2)},
    "sinh": {"f64": (6, 5, 3), "f32": (3, 2, 1)},
}
DEGREES["cos"] = DEGREES["sin"]


def fl(value, dtype: str) -> float:
    """``value`` rounded to the lane type, as a Python float."""
    return struct.unpack("f", struct.pack("f", float(value)))[0] if dtype == "f32" else float(value)


def fmt(value: float) -> str:
    return repr(float(value))


def split(value, dtype: str, parts: int = 3) -> list[float]:
    """``value`` as a sum of lane-precision terms."""
    terms, rest = [], mp.mpf(value)
    for _ in range(parts):
        terms.append(fl(rest, dtype))
        rest -= mp.mpf(terms[-1])
    return terms


def truncated(value, dtype: str) -> tuple[float, float]:
    """``value`` as (hi, lo), hi short enough that hi*n is exact for every exponent n."""
    bits = 42 if dtype == "f64" else 16
    scale = mp.mpf(2) ** bits
    hi = mp.floor(mp.mpf(value) * scale + mp.mpf(1) / 2) / scale
    return float(hi), fl(mp.mpf(value) - hi, dtype)


def fit(target, lo, hi, degree: int, dtype: str) -> list[float]:
    """The degree-``degree`` Chebyshev interpolant of ``target`` on [lo, hi], in monomials rounded to the lane."""
    n = degree + 1
    half, mid = (mp.mpf(hi) - lo) / 2, (mp.mpf(hi) + lo) / 2
    nodes = [mid + half * mp.cos(mp.pi * (2 * i + 1) / (2 * n)) for i in range(n)]
    nodes = [node if abs(node) > mp.mpf(10) ** -40 else mp.mpf(10) ** -40 for node in nodes]
    system = mp.matrix([[node**j for j in range(n)] for node in nodes])
    values = mp.matrix([target(node) for node in nodes])
    return [fl(c, dtype) for c in mp.lu_solve(system, values)]


def coefficients(values: list[float]) -> str:
    return ", ".join(fmt(v) for v in values)


def level_degree(family: str, dtype: str, level: str) -> int:
    return DEGREES[family][dtype][LEVELS.index(level)]


def sin_poly(dtype: str, level: str) -> str:
    u = (mp.pi / 2) ** 2
    return coefficients(
        fit(lambda t: (mp.sin(mp.sqrt(t)) / mp.sqrt(t) - 1) / t, 0, u, level_degree("sin", dtype, level), dtype)
    )


def reduce(q: str, x: str, unit, dtype: str, level: str) -> list[str]:
    """``r = x - q*unit``: double-word (``r`` + ``re``) when strict; else FMA steps, three unless fast."""
    a, b, c = split(unit, dtype)
    if level == "strict":
        return [
            f"p = mul({q}, {fmt(a)})",
            f"pe = fms({q}, {fmt(a)}, p)",
            f"h = sub({x}, p)",
            f"b = mul({q}, {fmt(b)})",
            f"be = fms({q}, {fmt(b)}, b)",
            "c = add(pe, b)",
            "ce = sub(b, sub(c, pe))",
            "r = sub(h, c)",
            f"re = sub(sub(sub(h, r), c), add(add(be, ce), mul({q}, {fmt(c)})))",
        ]
    lines = [f"r1 = fnma({q}, {fmt(a)}, {x})"]
    if level == "fast":
        return [*lines, f"r = fnma({q}, {fmt(b)}, r1)"]
    return [*lines, f"r2 = fnma({q}, {fmt(b)}, r1)", f"r = fnma({q}, {fmt(c)}, r2)"]


def strict_guard(cond: str) -> dict:
    return {"guard": "ok", "pre": [f"ok = {cond}"]}


def trig_grids(dtype: str, level: str) -> list[Grid]:
    top = TRIG_MAX[dtype]
    grids = [Grid(-1.6, 1.6, "lin"), Grid(-top, top, "lin"), Grid(1e-3, top, "near")]
    if level == "strict":
        grids += [Grid(TINY[dtype], HUGE[dtype], "log")]
    return grids


def trig_contract(dtype: str) -> str:
    return f"finite, |x| <= {TRIG_MAX[dtype]:g}"


def program_sin(dtype: str, level: str) -> dict:
    inv = fl(1 / mp.pi, dtype)
    body = [f"q = round(mul(x, {fmt(inv)}))", *reduce("q", "x", mp.pi, dtype, level), "t = mul(r, r)"]
    tail = "add(re, mul(mul(r, t), w))" if level == "strict" else "mul(mul(r, t), w)"
    body += [f"w = horner(t, {sin_poly(dtype, level)})", f"s = add(r, {tail})"]
    body += [f"f = frombits(ixor(bits(s), ishl(toint(q), {SIGN_SHIFT[dtype]})))"]
    out = {"args": ("x",), "grids": trig_grids(dtype, level), "contract": trig_contract(dtype)}
    if level == "strict":
        body += ["v = select(eq(x, 0.0), x, f)"]
        return {**out, **strict_guard(f"le(abs(x), {fmt(TRIG_MAX[dtype])})"), "body": body, "result": "v"}
    return {**out, "body": body, "result": "f"}


def program_cos(dtype: str, level: str) -> dict:
    inv = fl(1 / mp.pi, dtype)
    body = [f"q = add(mul(2.0, round(sub(mul(x, {fmt(inv)}), 0.5))), 1.0)"]
    body += [*reduce("q", "x", mp.pi / 2, dtype, level), "t = mul(r, r)"]
    tail = "add(re, mul(mul(r, t), w))" if level == "strict" else "mul(mul(r, t), w)"
    body += [f"w = horner(t, {sin_poly(dtype, level)})", f"s = add(r, {tail})"]
    body += [f"f = frombits(ixor(bits(neg(s)), ishl(ishr(toint(q), 1), {SIGN_SHIFT[dtype]})))"]
    out = {"args": ("x",), "grids": trig_grids(dtype, level), "contract": trig_contract(dtype)}
    if level == "strict":
        return {**out, **strict_guard(f"le(abs(x), {fmt(TRIG_MAX[dtype])})"), "body": body, "result": "f"}
    return {**out, "body": body, "result": "f"}


def program_tan(dtype: str, level: str) -> dict:
    inv = fl(2 / mp.pi, dtype)
    u = (mp.pi / 4) ** 2
    poly = fit(lambda t: (mp.tan(mp.sqrt(t)) / mp.sqrt(t) - 1) / t, 0, u, level_degree("tan", dtype, level), dtype)
    body = [f"q = round(mul(x, {fmt(inv)}))", *reduce("q", "x", mp.pi / 2, dtype, level), "t = mul(r, r)"]
    tail = "add(re, mul(mul(r, t), w))" if level == "strict" else "mul(mul(r, t), w)"
    body += [f"w = horner(t, {coefficients(poly)})", f"s = add(r, {tail})"]
    body += ["even = eq(sub(q, mul(2.0, round(mul(q, 0.5)))), 0.0)", "f = select(even, s, div(-1.0, s))"]
    out = {"args": ("x",), "grids": trig_grids(dtype, level), "contract": trig_contract(dtype)}
    if level == "strict":
        body += ["v = select(eq(x, 0.0), x, f)"]
        return {**out, **strict_guard(f"le(abs(x), {fmt(TRIG_MAX[dtype])})"), "body": body, "result": "v"}
    return {**out, "body": body, "result": "f"}


def scale(value: str, q: str, dtype: str) -> str:
    """``value * 2^q`` for an integral-valued float q, while the exponent stays normal."""
    return f"frombits(iadd(bits({value}), ishl(toint({q}), {MANTISSA[dtype]})))"


def exp_core(arg: str, dtype: str, level: str, tag: str = "") -> tuple[list[str], str]:
    """Lines computing e^arg; the name of the result."""
    poly = fit(
        lambda r: (mp.exp(r) - 1 - r) / r**2,
        -mp.log(2) / 2 * 1.01,
        mp.log(2) / 2 * 1.01,
        level_degree("exp", dtype, level),
        dtype,
    )
    a, b, _ = split(mp.log(2), dtype)
    inv = fl(1 / mp.log(2), dtype)
    k, r, t = f"q{tag}", f"r{tag}", f"t{tag}"
    lines = [
        f"{k} = round(mul({arg}, {fmt(inv)}))",
        f"{r}h = fnma({k}, {fmt(a)}, {arg})",
        f"{r}l = mul({k}, {fmt(b)})",
        f"{r} = sub({r}h, {r}l)",
        f"{t} = mul({r}, {r})",
        f"p{tag} = horner({r}, {coefficients(poly)})",
        f"m{tag} = add(1.0, add({r}h, sub(mul({t}, p{tag}), {r}l)))",
        f"e{tag} = {scale(f'm{tag}', k, dtype)}",
    ]
    return lines, f"e{tag}"


def bounded(arg: str, dtype: str) -> str:
    return f"le(abs({arg}), {fmt(EXP_MAX[dtype])})"


def exp_grids(dtype: str, level: str, top: float) -> list[Grid]:
    grids = [Grid(-1.0, 1.0, "lin"), Grid(-top, top, "lin"), Grid(TINY[dtype], top, "log")]
    if level == "strict":
        grids += [Grid(-3 * top, 3 * top, "lin")]
    return grids


def program_exp(dtype: str, level: str) -> dict:
    lines, result = exp_core("x", dtype, level)
    out = {"args": ("x",), "grids": exp_grids(dtype, level, EXP_MAX[dtype])}
    out |= {"contract": f"finite, |x| <= {EXP_MAX[dtype]:g}", "body": lines, "result": result}
    return {**out, **strict_guard(bounded("x", dtype))} if level == "strict" else out


def exp_like(fn: str, base, dtype: str, level: str) -> dict:
    """2^x and 10^x: reduce on the base's log2, then 1 + r*Q(r)."""
    unit = mp.log(2) / mp.log(base)
    half = unit / 2 * mp.mpf("1.01")
    poly = fit(lambda r: (mp.power(base, r) - 1) / r, -half, half, level_degree(fn, dtype, level), dtype)
    a, b, _ = split(unit, dtype)
    inv = fl(1 / unit, dtype)
    top = EXP_MAX[dtype] / float(mp.log(base))
    body = [
        f"q = round(mul(x, {fmt(inv)}))",
        f"rh = fnma(q, {fmt(a)}, x)",
        f"r = fnma(q, {fmt(b)}, rh)",
        f"m = add(1.0, mul(r, horner(r, {coefficients(poly)})))",
        f"e = {scale('m', 'q', dtype)}",
    ]
    out = {"args": ("x",), "grids": exp_grids(dtype, level, top), "contract": f"finite, |x| <= {top:.5g}"}
    out |= {"body": body, "result": "e"}
    return {**out, **strict_guard(f"le(abs(x), {fmt(fl(top, dtype))})")} if level == "strict" else out


def program_expm1(dtype: str, level: str) -> dict:
    poly = fit(
        lambda r: (mp.exp(r) - 1 - r) / r**2,
        -mp.log(2) / 2 * 1.01,
        mp.log(2) / 2 * 1.01,
        level_degree("expm1", dtype, level),
        dtype,
    )
    a, b, _ = split(mp.log(2), dtype)
    inv = fl(1 / mp.log(2), dtype)
    low = -40.0 if dtype == "f64" else -18.0
    body = [
        f"q = round(mul(x, {fmt(inv)}))",
        f"rh = fnma(q, {fmt(a)}, x)",
        f"rl = mul(q, {fmt(b)})",
        "r = sub(rh, rl)",
        "t = mul(r, r)",
        f"w = horner(r, {coefficients(poly)})",
        "p = add(rh, sub(mul(t, w), rl))",
        f"u = {scale('one', 'q', dtype)}",
        "f = add(sub(u, 1.0), mul(u, p))",
    ]
    body.insert(0, "one = set(1.0)")
    grids = [Grid(-1.0, 1.0, "lin"), Grid(low, EXP_MAX[dtype], "lin"), Grid(TINY[dtype], 1.0, "log")]
    out = {"args": ("x",), "grids": grids, "contract": f"finite, {low:g} <= x <= {EXP_MAX[dtype]:g}"}
    if level == "strict":
        body += ["v = select(eq(x, 0.0), x, f)"]
        guard = strict_guard(f"mand(le({fmt(low)}, x), le(x, {fmt(EXP_MAX[dtype])}))")
        return {**out, **guard, "body": body, "result": "v"}
    return {**out, "body": body, "result": "f"}


def log_core(arg: str, dtype: str, level: str) -> list[str]:
    """Lines giving ``n`` (the exponent) and log(mantissa) = ``f`` - ``lo``, for a positive normal arg."""
    mantissa, bias = MANTISSA[dtype], BIAS[dtype]
    half = int.from_bytes(struct.pack(">d" if dtype == "f64" else ">f", math.sqrt(0.5)), "big")
    one = bias << mantissa
    limit = ((mp.sqrt(2) - 1) / (mp.sqrt(2) + 1)) ** 2 * mp.mpf("1.01")
    poly = fit(
        lambda z: (mp.atanh(mp.sqrt(z)) / mp.sqrt(z) - 1) / z * 2, 0, limit, level_degree("log", dtype, level), dtype
    )
    return [
        f"ix = iadd(bits({arg}), {one - half})",
        f"n = tofloat(isub(ishr(ix, {mantissa}), {bias}))",
        f"m = frombits(iadd(iand(ix, {(1 << mantissa) - 1}), {half}))",
        "f = sub(m, 1.0)",
        "s = div(f, add(2.0, f))",
        "z = mul(s, s)",
        f"big = mul(z, horner(z, {coefficients(poly)}))",
        "lo = mul(s, sub(f, big))",
    ]


def positive(arg: str, dtype: str) -> str:
    return (
        f"mand(le({fmt(2.3e-308 if dtype == 'f64' else 1.2e-38)}, {arg}), lt({arg}, {fl(HUGE[dtype] * 1e7, dtype)!r}))"
    )


def log_grids(dtype: str) -> list[Grid]:
    return [Grid(0.5, 2.0, "lin"), Grid(TINY[dtype], HUGE[dtype], "logp"), Grid(0.99, 1.01, "lin")]


def program_log(dtype: str, level: str) -> dict:
    hi, lo = truncated(mp.log(2), dtype)
    body = log_core("x", dtype, level)
    body += [f"v = add(mul(n, {fmt(hi)}), add(f, sub(mul(n, {fmt(lo)}), lo)))"]
    out = {"args": ("x",), "grids": log_grids(dtype), "contract": "finite, positive, normal"}
    out |= {"body": body, "result": "v"}
    return {**out, **strict_guard(positive("x", dtype))} if level == "strict" else out


def program_log_scaled(base, dtype: str, level: str) -> dict:
    inv = fl(1 / mp.log(base), dtype)
    body = log_core("x", dtype, level)
    body += [f"h = mul(f, {fmt(inv)})", f"he = fms(f, {fmt(inv)}, h)", f"lg = fnma(lo, {fmt(inv)}, he)"]
    if base == 2:
        body += ["v = add(n, add(h, lg))"]
    else:
        high, low = truncated(mp.log(2) / mp.log(base), dtype)
        body += [f"v = add(mul(n, {fmt(high)}), add(h, add(lg, mul(n, {fmt(low)}))))"]
    out = {"args": ("x",), "grids": log_grids(dtype), "contract": "finite, positive, normal"}
    out |= {"body": body, "result": "v"}
    return {**out, **strict_guard(positive("x", dtype))} if level == "strict" else out


def program_log1p(dtype: str, level: str) -> dict:
    hi, lo = truncated(mp.log(2), dtype)
    body = ["y = add(1.0, x)", "c = div(sub(x, sub(y, 1.0)), y)", *log_core("y", dtype, level)]
    body += [f"f1 = add(mul(n, {fmt(hi)}), add(f, add(c, sub(mul(n, {fmt(lo)}), lo))))"]
    grids = [Grid(-0.9, 2.0, "lin"), Grid(TINY[dtype], 0.5, "log"), Grid(TINY[dtype], HUGE[dtype], "logp")]
    out = {"args": ("x",), "grids": grids, "contract": "finite, x > -1"}
    if level == "strict":
        body += ["v = select(eq(x, 0.0), x, f1)"]
        guard = strict_guard(f"mand(lt(-1.0, x), lt(x, {fl(HUGE[dtype], dtype)!r}))")
        return {**out, **guard, "body": body, "result": "v"}
    return {**out, "body": body, "result": "f1"}


def with_sign(value: str, source: str) -> str:
    return f"frombits(ior(bits({value}), iand(bits({source}), bits(-0.0))))"


def inverse_grids(dtype: str, unit: bool) -> list[Grid]:
    if unit:
        return [Grid(-1.0, 1.0, "lin"), Grid(TINY[dtype], 1.0, "log")]
    return [Grid(-2.0, 2.0, "lin"), Grid(TINY[dtype], HUGE[dtype], "log")]


def program_atan(dtype: str, level: str) -> dict:
    poly = fit(lambda t: (mp.atan(mp.sqrt(t)) / mp.sqrt(t) - 1) / t, 0, 1, level_degree("atan", dtype, level), dtype)
    hi, lo = split(mp.pi / 2, dtype, 2)
    body = [
        "a = abs(x)",
        "far = lt(1.0, a)",
        "u = select(far, div(-1.0, a), a)",
        f"off = select(far, set({fmt(hi)}), set(0.0))",
        f"ofl = select(far, set({fmt(lo)}), set(0.0))",
        "t = mul(u, u)",
        f"w = horner(t, {coefficients(poly)})",
        "s = add(off, add(u, add(ofl, mul(mul(u, t), w))))",
        f"v = {with_sign('s', 'x')}",
    ]
    return {"args": ("x",), "grids": inverse_grids(dtype, False), "contract": "any input", "body": body, "result": "v"}


def asin_core(x: str, dtype: str, level: str) -> list[str]:
    poly = fit(lambda t: (mp.asin(mp.sqrt(t)) / mp.sqrt(t) - 1) / t, 0, 0.25, level_degree("asin", dtype, level), dtype)
    return [
        f"a = abs({x})",
        "far = lt(0.5, a)",
        "z = select(far, mul(0.5, sub(1.0, a)), mul(a, a))",
        "s = select(far, sqrt(z), a)",
        f"w = add(s, mul(mul(s, z), horner(z, {coefficients(poly)})))",
    ]


def program_asin(dtype: str, level: str) -> dict:
    hi, lo = split(mp.pi / 2, dtype, 2)
    body = asin_core("x", dtype, level)
    body += [f"g = select(far, sub({fmt(hi)}, sub(add(w, w), {fmt(lo)})), w)", f"v = {with_sign('g', 'x')}"]
    return {
        "args": ("x",),
        "grids": inverse_grids(dtype, True),
        "contract": "|x| <= 1 or NaN out",
        "body": body,
        "result": "v",
    }


def program_acos(dtype: str, level: str) -> dict:
    half_hi, half_lo = split(mp.pi / 2, dtype, 2)
    pi_hi, pi_lo = split(mp.pi, dtype, 2)
    body = asin_core("x", dtype, level)
    body += [
        f"w2 = {with_sign('w', 'x')}",
        f"mid = sub({fmt(half_hi)}, sub(w2, {fmt(half_lo)}))",
        f"low = sub({fmt(pi_hi)}, sub(add(w, w), {fmt(pi_lo)}))",
        "v = select(far, select(lt(x, 0.0), low, add(w, w)), mid)",
    ]
    return {
        "args": ("x",),
        "grids": inverse_grids(dtype, True),
        "contract": "|x| <= 1 or NaN out",
        "body": body,
        "result": "v",
    }


def program_sinh(dtype: str, level: str) -> dict:
    poly = fit(lambda t: (mp.sinh(mp.sqrt(t)) / mp.sqrt(t) - 1) / t, 0, 1, level_degree("sinh", dtype, level), dtype)
    lines, e = exp_core("a", dtype, level)
    body = ["a = abs(x)", *lines]
    body += [
        f"i = div(1.0, {e})",
        "h = sub(mul(0.5, " + e + "), mul(0.5, i))",
        "b = mul(a, a)",
        f"sm = add(a, mul(mul(a, b), horner(b, {coefficients(poly)})))",
        "g = select(lt(1.0, a), h, sm)",
        f"v = {with_sign('g', 'x')}",
    ]
    grids = [Grid(-2.0, 2.0, "lin"), Grid(-EXP_MAX[dtype], EXP_MAX[dtype], "lin"), Grid(TINY[dtype], 1.0, "log")]
    out = {
        "args": ("x",),
        "grids": grids,
        "contract": f"finite, |x| <= {EXP_MAX[dtype]:g}",
        "body": body,
        "result": "v",
    }
    return {**out, **strict_guard(bounded("x", dtype))} if level == "strict" else out


def program_cosh(dtype: str, level: str) -> dict:
    lines, e = exp_core("a", dtype, level)
    body = ["a = abs(x)", *lines, f"v = add(mul(0.5, {e}), div(0.5, {e}))"]
    grids = [Grid(-2.0, 2.0, "lin"), Grid(-EXP_MAX[dtype], EXP_MAX[dtype], "lin")]
    out = {
        "args": ("x",),
        "grids": grids,
        "contract": f"finite, |x| <= {EXP_MAX[dtype]:g}",
        "body": body,
        "result": "v",
    }
    return {**out, **strict_guard(bounded("x", dtype))} if level == "strict" else out


def program_tanh(dtype: str, level: str) -> dict:
    expm1 = program_expm1(dtype, level)
    body = ["a = abs(x)", "d = add(a, a)"]
    body += [
        line.replace("(x,", "(d,").replace(", x)", ", d)") for line in expm1["body"] if not line.startswith("v = ")
    ]
    top = 20.0 if dtype == "f64" else 10.0
    body += ["g = div(f, add(f, 2.0))", f"h = select(le({top}, a), set(1.0), g)", f"v = {with_sign('h', 'x')}"]
    grids = [Grid(-2.0, 2.0, "lin"), Grid(-40.0, 40.0, "lin"), Grid(TINY[dtype], 1.0, "log")]
    out = {"args": ("x",), "grids": grids, "contract": "finite", "body": body, "result": "v"}
    return out


def program_pow(dtype: str, level: str) -> dict:
    hi, lo = truncated(mp.log(2), dtype)
    core = log_core("x", dtype, level)
    tail, e = exp_core("big2", dtype, level, "E")
    limit = POW_MAX[dtype]
    grids = [Grid(0.1, 10.0, "lin", -8.0, 8.0), Grid(TINY[dtype], HUGE[dtype], "logp", -1.0, 1.0)]
    out = {"args": ("x", "y"), "grids": grids, "contract": "x positive normal, finite y, |y*log(x)| in exp range"}
    if level == "strict":
        double_log = [
            "two = add(2.0, f)",
            "sl = div(fnma(s, two, f), two)",
            "nh = mul(n, " + fmt(hi) + ")",
            "lh = add(s, s)",
            "sum = add(nh, lh)",
            "bb = sub(sum, nh)",
            "er = add(sub(nh, sub(sum, bb)), sub(lh, bb))",
            f"tl = add(er, add(mul(n, {fmt(lo)}), add(add(sl, sl), mul(s, big))))",
            "ph = add(sum, tl)",
            "pl = sub(tl, sub(ph, sum))",
            "big2 = mul(y, ph)",
            "ee = fms(y, ph, big2)",
            "cor = add(ee, mul(y, pl))",
        ]
        body = [*core[:-1], *double_log, *tail, f"v = fma({e}, cor, {e})"]
        guard = f"mand({positive('x', dtype)}, le(abs(big2), {fmt(limit)}))"
        return {**out, **strict_guard(guard), "body": body, "result": "v"}
    body = [*core, f"lg = add(mul(n, {fmt(hi)}), add(f, sub(mul(n, {fmt(lo)}), lo)))", "big2 = mul(y, lg)", *tail]
    return {**out, "body": body, "result": e}


PROGRAMS = {
    "sin": program_sin,
    "cos": program_cos,
    "tan": program_tan,
    "exp": program_exp,
    "exp2": lambda d, l: exp_like("exp2", 2, d, l),
    "exp10": lambda d, l: exp_like("exp10", 10, d, l),
    "expm1": program_expm1,
    "log": program_log,
    "log2": lambda d, l: program_log_scaled(2, d, l),
    "log10": lambda d, l: program_log_scaled(10, d, l),
    "log1p": program_log1p,
    "pow": program_pow,
    "atan": program_atan,
    "asin": program_asin,
    "acos": program_acos,
    "sinh": program_sinh,
    "cosh": program_cosh,
    "tanh": program_tanh,
}

SPECIALS = (float("nan"), float("inf"), float("-inf"), 0.0, -0.0, 1.0, -1.0, 0.5, 2.0)


def build(fn: str, dtype: str, level: str) -> Kernel:
    """The kernel, with unmeasured errors."""
    p = PROGRAMS[fn](dtype, level)
    pre = p.get("pre", [])
    body = (*p["body"], *pre)
    tiny = 1e-320 if dtype == "f64" else 1e-44
    specials = (*SPECIALS, tiny, -tiny, HUGE[dtype], -HUGE[dtype]) if level == "strict" else ()
    return Kernel(
        fn,
        dtype,
        level,
        p["args"],
        body,
        p["result"],
        p.get("guard", ""),
        p["contract"],
        tuple(p["grids"]),
        specials,
        0.0,
        0.0,
    )


def measured(k: Kernel) -> tuple[Kernel, float, float, int]:
    results = [m for isa in ("avx2", "avx512") if (m := measure(k, isa)) is not None]
    if not results:
        raise RuntimeError("this host runs neither AVX2 nor AVX-512")
    return k, max(m.ulp for m in results), max(m.abs for m in results), max(m.special for m in results)


def toml_entry(k: Kernel, ulp: float, abs_err: float) -> str:
    lines = [f"[{k.fn}.{k.dtype}.{k.level}]"]
    lines += [f"args = {json.dumps(list(k.args))}", f"result = {json.dumps(k.result)}"]
    if k.guard:
        lines.append(f"guard = {json.dumps(k.guard)}")
    lines += [f"contract = {json.dumps(k.contract)}", f"error_ulp = {ulp:.4g}"]
    lines.append(f"error_abs = {abs_err:.4g}")
    if k.specials:
        lines.append("specials = [" + ", ".join(toml_float(v) for v in k.specials) + "]")
    lines.append("grids = [")
    for g in k.grids:
        lines.append(
            f'  {{ lo = {toml_float(g.lo)}, hi = {toml_float(g.hi)}, kind = "{g.kind}", '
            f"ylo = {toml_float(g.ylo)}, yhi = {toml_float(g.yhi)} }},"
        )
    lines += ["]", "body = ["]
    lines += [f"  {json.dumps(line)}," for line in k.body]
    return "\n".join([*lines, "]"])


def toml_float(value: float) -> str:
    if math.isnan(value):
        return "nan"
    if math.isinf(value):
        return "inf" if value > 0 else "-inf"
    return repr(float(value)) if "." in repr(float(value)) or "e" in repr(float(value)) else f"{value}.0"


def main(argv: list[str]) -> int:
    only = argv or list(PROGRAMS)
    kernels = [build(fn, dtype, level) for fn in only for dtype in ("f64", "f32") for level in LEVELS]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(measured, kernels))
    for k, ulp, abs_err, special in results:
        print(f"{k.fn:6} {k.dtype} {k.level:8} {ulp:11.4g} ulp  abs {abs_err:9.3g}  special-bad {special}")
    if not argv:
        header = "# Generated by `python -m alloy.isa.mathfit`; do not edit.\n\n"
        text = "\n\n".join(toml_entry(k, ulp, abs_err) for k, ulp, abs_err, _ in results)
        KERNELS_PATH.write_text(header + text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
