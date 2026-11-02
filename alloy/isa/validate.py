# Copyright 2026 ETH Zurich and the Alloy authors.
"""Numerical validation of table entries: the intrinsic or recipe of an x86 row the host runs is checked before a
lookup returns it, and every other row says unverified. Masked forms, mnemonics and notes are not checked.

An x86 entry the host can execute (AVX2+FMA, AVX-512F+DQ) runs fixed inputs, on buffers no vector boundary
aligns, through a small compiled C kernel calling the row in its signature's operand order, against a scalar reference and a per-op tolerance; :func:`unexercised` refuses a kernel that skips a
spelling. An approximation tier is re-measured in numpy against libm: the recorded ``error_ulp`` must reproduce within
a slack, which catches transcription errors in the coefficients. On a failure :func:`candidates_for` names a shortlist.

``Verdict.ok is None`` means not verifiable on this host (NEON/SVE, for which no kernels exist yet, AVX-512 FP16,
entries with no executable form, no C compiler): unverified is never reported as correct.
"""

import contextlib
import dataclasses
import functools
import math
import pathlib
import platform
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import numpy as np

from alloy.isa.ops import OPS
from alloy.isa.table import ALIASES, ALL_DTYPES, DTYPES, INT_DTYPES, LANE_BYTES, SPELLED, Entry, Hit, Table, load
from alloy.machine import cpu_flags

__all__ = ["Verdict", "candidates_for", "host_can_run", "validate", "validate_all", "validate_tier"]

#: Per-op relative-error tolerances for the compiled kernels. IEEE ops are exactly rounded, so their
#: tolerance is zero; order-sensitive ops (reductions, recipes) get a real band.
TOL: dict[str, float] = {"reduce_add": 1e-12, "mod": 1e-13}  # any other op is bit-exact
TOL_F16 = 4e-3  # the AVX2 f16 recipes compute in f32; a few f16 ulps of slack
TOL_LIBRARY = {"f64": 1e-13, "f32": 1e-6}  # vector math library entries vs double libm, by lane type
TIER_SLACK = 2.0  # a tier's re-measured error may exceed the recorded one by this factor
N_TIER = 2_000_000
COMPILE_TIMEOUT = 120  # seconds, per compile and per run

VERIFY_LINE = re.compile(r"^ALLOY-VERIFY rel=(\S+)", re.MULTILINE)
SIGNATURE = re.compile(r"^\(([^)]*)\)")
#: Ops whose row is one call on the kernel's operands, by the names a ``signature`` gives them.
CALLED = frozenset({"add", "sub", "mul", "div", "min", "max", "fma", "and", "or", "shl", "shr", "sqrt"})
CALLED |= {"load", "broadcast", "zero"}


@dataclasses.dataclass(slots=True, frozen=True)
class Verdict:
    """One validation outcome. ``ok`` None = not verifiable on this host (never reported as correct);
    ``candidates`` lists the potentially relevant spellings when the check failed."""

    ok: bool | None
    basis: str
    detail: str = ""
    candidates: tuple[Hit, ...] = ()


def host_flags() -> frozenset[str]:
    """The host's CPU feature flags, none when ``/proc/cpuinfo`` cannot say."""
    try:
        return cpu_flags()
    except (OSError, RuntimeError):
        return frozenset()


def host_can_run(isa: str, dtype: str) -> bool:
    """Whether this host compiles AND executes kernels for ``(isa, dtype)``."""
    flags, machine = host_flags(), platform.machine()
    isa = ALIASES.get(isa, isa)
    if machine == "x86_64":
        if isa == "avx2":
            return {"avx2", "fma", "f16c"} <= flags if dtype == "f16" else {"avx2", "fma"} <= flags
        if isa == "avx512":  # the kernels and the k-mask entries need DQ
            return dtype != "f16" and {"avx512f", "avx512dq"} <= flags  # no FP16 kernel exists
        return False
    if machine == "aarch64":
        return {"neon": "asimd", "sve": "sve"}.get(isa, "") in flags
    return False


#: dtype -> (scalar C type, letter of its vector type, intrinsic suffix).
X86_LANES = {
    "f64": ("double", "d", "pd"),
    "f32": ("float", "", "ps"),
    "i64": ("int64_t", "i", "epi64"),
    "i32": ("int32_t", "i", "epi32"),
}


def track_error(got: str, ref: str, indent: str = "    ") -> str:
    """The per-lane error update of a kernel: a NaN must stick, a plain ``>`` would drop it."""
    lines = (
        f"double d = fabs({got} - {ref});",
        f"double m = fabs({ref}) > 1 ? fabs({ref}) : 1;",
        "double e = d / m;",
        "if (isnan(e) || e > maxrel) maxrel = e;",
    )
    return f"\n{indent}".join(lines)


#: How a kernel ends: the worst error, in the line :data:`VERIFY_LINE` reads.
REPORT_ERROR = 'printf("ALLOY-VERIFY rel=%.6e\\n", maxrel);\n  return 0;\n}'


def lane_errors(got: str, ref: str) -> str:
    """The end of a kernel comparing every lane."""
    return f"""double maxrel = 0;
  for (int j = 0; j < VL; j++) {{
    {track_error(got, ref)}
  }}
  {REPORT_ERROR}"""


#: Why a kernel's buffers start one element past a 64-byte boundary, in the source a reader of a failure sees.
MISALIGNED = "one element past a boundary: an aligned spelling of an unaligned row always faults"


def c_flags(isa: str, dtype: str) -> list[str]:
    isa = ALIASES.get(isa, isa)
    if isa == "neon":
        return ["-march=armv8.2-a+fp16"] if dtype == "f16" else []
    if isa == "sve":
        return ["-march=armv8-a+sve"]
    if isa == "avx2":
        return ["-mavx2", "-mfma", "-mf16c"] if dtype == "f16" else ["-mavx2", "-mfma"]
    return ["-mavx512f", "-mavx512dq", "-mavx512fp16"] if dtype == "f16" else ["-mavx512f", "-mavx512dq"]


@dataclasses.dataclass(slots=True, frozen=True)
class Frame:
    """What every kernel of one x86 ``(isa, dtype)`` shares: its C spellings, the loads and the store."""

    wide: bool
    fp: bool
    dtype: str
    bits: int
    lanes: int
    scalar: str
    vector: str
    prefix: str
    suffix: str
    cast: str
    masked_load: str
    spill: str
    loads: str
    store: str

    def stored(self, compute: str) -> str:
        return f"{self.loads}\n  {compute}\n  {self.store}"


def frame(isa: str, dtype: str, table: Table) -> Frame:
    wide, fp = isa == "avx512", dtype in DTYPES
    bits = 512 if wide else 256
    scalar, letter, suffix = X86_LANES[dtype]
    vector, prefix = f"__m{bits}{letter}", f"_mm{bits}"
    load_row, store_row = table.entry(isa, "load", dtype), table.entry(isa, "store", dtype)
    cast = "" if fp else f"({vector}*)"
    loads = {name: called(load_row, {"p": f"{cast}{name}"}) for name in "abc"}
    out = f"({scalar}*)out" if fp else f"({vector}*)out"
    return Frame(
        wide,
        fp,
        dtype,
        bits,
        bits // (8 * LANE_BYTES[dtype]),
        scalar,
        vector,
        prefix,
        suffix,
        cast,
        load_row.masked.split("(", 1)[0],
        f"{called(store_row, {'p': 'buf', 'v': 'va'})};",
        f"{vector} va = {loads['a']};\n  {vector} vb = {loads['b']};\n  {vector} vc = {loads['c']};",
        f"{called(store_row, {'p': out, 'v': 'vr'})};",
    )


def lane_ref(expression: str) -> str:
    """The scalar reference of a kernel: ``expression`` for every lane."""
    return f"for (int j = 0; j < VL; j++) ref[j] = {expression};"


#: The constant an abs or neg recipe combines with, by lane type.
SIGN_MASKS = {
    ("abs", "f64"): "(long long)0x7fffffffffffffffULL",
    ("abs", "f32"): "(int)0x7fffffffU",
    ("neg", "f64"): "(long long)0x8000000000000000ULL",
    ("neg", "f32"): "(int)0x80000000U",
}


def sign_body(k: Frame, op: str, entry: Entry) -> tuple[str, str]:
    mask = SIGN_MASKS[op, k.dtype]
    if k.wide:
        set1 = f"{k.prefix}_set1_epi{8 * LANE_BYTES[k.dtype]}"
        bits_of = f"{k.prefix}_cast{k.suffix}_si512(va)"
        compute = f"{k.vector} vr = {k.prefix}_castsi512_{k.suffix}({entry.recipe[0]}({bits_of}, {set1}({mask})));"
    else:
        to_float, set1, bitop = entry.recipe
        compute = f"{k.vector} vr = {bitop}(va, {to_float}({set1}({mask})));"
    return k.stored(compute), lane_ref("a[j] < 0 ? -a[j] : a[j]" if op == "abs" else "-a[j]")


def select_body(k: Frame, op: str, entry: Entry) -> tuple[str, str]:
    pick = called(entry, {"a": "va", "b": "vb", "k": "k", "mask": "k"})
    test = (
        f"__mmask{k.lanes} k = {k.prefix}_cmp_{k.suffix}_mask"
        if k.wide
        else f"{k.vector} k = {k.prefix}_cmp_{k.suffix}"
    )
    return k.stored(f"{test}(va, vb, _CMP_LT_OQ);\n  {k.vector} vr = {pick};"), lane_ref("a[j] < b[j] ? b[j] : a[j]")


#: AVX2 has no horizontal sum: the row's mnemonics spelled out by hand.
AVX2_SUM = {
    "f64": """__m128d lo = _mm256_castpd256_pd128(va), hi = _mm256_extractf128_pd(va, 1);
  __m128d s2 = _mm_add_pd(lo, hi);
  __m128d sh = _mm_unpackhi_pd(s2, s2);
  double r = _mm_cvtsd_f64(_mm_add_sd(s2, sh));
  out[0] = r;""",
    "f32": """__m128 lo = _mm256_castps256_ps128(va), hi = _mm256_extractf128_ps(va, 1);
  __m128 s2 = _mm_add_ps(lo, hi);
  __m128 sh = _mm_movehdup_ps(s2);
  s2 = _mm_add_ps(s2, sh);
  sh = _mm_movehl_ps(sh, s2);
  s2 = _mm_add_ss(s2, sh);
  float r = _mm_cvtss_f32(s2);
  out[0] = r;""",
}


def reduce_body(k: Frame, op: str, entry: Entry) -> tuple[str, str]:
    compute = f"{k.scalar} r = {called(entry, {'v': 'va'})};\n  out[0] = r;" if k.wide else AVX2_SUM[k.dtype]
    return f"{k.loads}\n  {compute}", "for (int j = 0; j < VL; j++) ref[0] += a[j];"


def indices(k: Frame) -> str:
    """The load of the index vector; f32 gathers index in 32-bit lanes."""
    index_type = f"__m{k.bits}i"
    source = "idx" if k.dtype == "f64" else "idx32"
    return f"{index_type} vi = {k.prefix}_loadu_si{k.bits}((const {index_type}*){source});"


def gather_body(k: Frame, op: str, entry: Entry) -> tuple[str, str]:
    pick = called(entry, {"base": "a", "idx": "vi", "scale": str(LANE_BYTES[k.dtype])})
    return k.stored(f"{indices(k)}\n  {k.vector} vr = {pick};"), lane_ref("a[idx[j]]")


def scatter_body(k: Frame, op: str, entry: Entry) -> tuple[str, str]:
    if k.wide:
        write = called(entry, {"base": "out", "idx": "vi", "v": "va", "scale": str(LANE_BYTES[k.dtype])})
        compute = f"{indices(k)}\n  {write};"
    else:  # AVX2 has no scatter: the documented fallback, hand-coded
        compute = f"{k.scalar} buf[VL];\n  {k.spill}\n  for (int j = 0; j < VL; j++) out[idx[j]] = buf[j];"
    ref = "for (int j = 0; j < VL; j++) ref[j] = 0;\nfor (int j = 0; j < VL; j++) ref[idx[j]] = a[j];"
    return f"{k.loads}\n  {compute}", ref


def gen_mask_body(k: Frame, op: str, entry: Entry) -> tuple[str, str]:
    width = 8 * LANE_BYTES[k.dtype]
    iota = ", ".join(str(j) for j in range(k.lanes))
    limit = f"{k.prefix}_set1_epi{width}(n)"
    compute = (
        f"__m512i iota = {k.prefix}_setr_epi{width}({iota});\n  int n = VL - 1;\n"
        f"  __mmask{k.lanes} k = {called(entry, {'iota': 'iota', 'n': limit})};\n"
        f"  {k.vector} vr = {k.masked_load}(k, a);"
    )
    return k.stored(compute), lane_ref("j < n ? a[j] : 0")


def mod_body(k: Frame, op: str, entry: Entry) -> tuple[str, str]:
    div, trunc, fnmadd = entry.recipe
    rounding = "0x0B" if k.wide else "_MM_FROUND_TO_ZERO | _MM_FROUND_NO_EXC"
    compute = f"{k.vector} q = {trunc}({div}(va, vb), {rounding});\n  {k.vector} vr = {fnmadd}(q, vb, va);"
    return k.stored(compute), lane_ref(f"fmod{'' if k.dtype == 'f64' else 'f'}(a[j], b[j])")


#: Ops whose kernel is more than a call, on float lanes; an integer lane has none (``mod`` there is prose).
FLOAT_BODIES: dict[str, Callable[[Frame, str, Entry], tuple[str, str]]] = {
    "abs": sign_body,
    "neg": sign_body,
    "select": select_body,
    "reduce_add": reduce_body,
    "gather": gather_body,
    "scatter": scatter_body,
    "gen_mask": gen_mask_body,
    "mod": mod_body,
}


def called(entry: Entry, operands: dict[str, str]) -> str:
    """``entry``'s intrinsic on ``operands`` in the order its ``signature`` states, so the gate runs the order a reader
    of the row copies."""
    match = SIGNATURE.match(entry.signature)
    names = [name.strip() for name in match.group(1).split(",") if name.strip()] if match else []
    if match is None or any(name not in operands for name in names):
        raise ValueError(f"{entry.intrinsic}: the signature {entry.signature!r} names no operands of this op")
    return f"{entry.intrinsic}({', '.join(operands[name] for name in names)})"


def kernel_body(isa: str, dtype: str, op: str, table: Table) -> tuple[str, str] | None:
    """The kernel body for ``(isa, dtype, op)``, spelled with the table's own entry so a wrong mapping fails:
    (compute C, scalar-reference C), or None when the entry has no executable form here."""
    entry = table.entry(isa, op, dtype)
    if dtype == "f16":
        return f16_body(op, entry) if isa == "avx2" else None
    k = frame(isa, dtype, table)
    if op in ("land", "lor"):
        return logical_body(k, op, entry)
    if op in FLOAT_BODIES:
        return FLOAT_BODIES[op](k, op, entry) if k.fp else None
    if not entry.intrinsic:  # a recipe with no kernel written for it: unverified
        return None
    if op == "store":
        return k.stored(f"{k.vector} vr = vb;"), scalar_ref(op, dtype)
    if op not in CALLED:
        return None
    operands = {"a": "va", "b": "vb", "c": "vc", "v": "va", "counts": "vb", "p": f"{k.cast}a", "s": "a[0]"}
    return k.stored(f"{k.vector} vr = {called(entry, operands)};"), scalar_ref(op, dtype)


def scalar_ref(op: str, dtype: str) -> str:
    if dtype in INT_DTYPES:
        s, u = ("int64_t", "uint64_t") if dtype == "i64" else ("int32_t", "uint32_t")
        refs = {
            "and": "a[j] & b[j]",
            "or": "a[j] | b[j]",
            "shl": f"({s})(({u})a[j] << b[j])",
            "shr": f"({s})(({u})a[j] >> b[j])",  # logical: a negative lane must not sign-fill
            "add": f"({s})(({u})a[j] + ({u})b[j])",
            "sub": f"({s})(({u})a[j] - ({u})b[j])",
            "mul": f"({s})(({u})a[j] * ({u})b[j])",
            "min": "a[j] < b[j] ? a[j] : b[j]",
            "max": "a[j] > b[j] ? a[j] : b[j]",
            "load": "a[j]",
            "store": "b[j]",
            "broadcast": "a[0]",
        }
    else:
        f = "" if dtype == "f64" else "f"  # a float lane is checked against the float libm
        refs = {
            "add": "a[j] + b[j]",
            "sub": "a[j] - b[j]",
            "mul": "a[j] * b[j]",
            "div": "a[j] / b[j]",
            "min": "a[j] < b[j] ? a[j] : b[j]",
            "max": "a[j] > b[j] ? a[j] : b[j]",
            "fma": f"fma{f}(a[j], b[j], c[j])",
            "sqrt": f"sqrt{f}(a[j])",
            "load": "a[j]",
            "store": "b[j]",
            "broadcast": "a[0]",
            "zero": "0",
        }
    return lane_ref(refs[op])


def logical_body(k: Frame, op: str, entry: Entry) -> tuple[str, str]:
    """land/lor, full kernel body: k-register ops on AVX-512, the andnot-of-compares recipe on AVX2."""
    sym = "&&" if op == "land" else "||"
    if k.wide:
        cmp = f"_mm512_cmpneq_{k.suffix}_mask"
        compute = (
            f"__mmask{k.lanes} ka = {cmp}(_mm512_loadu_si512((const __m512i*)a), _mm512_setzero_si512());\n"
            f"  __mmask{k.lanes} kb = {cmp}(_mm512_loadu_si512((const __m512i*)b), _mm512_setzero_si512());\n"
            f"  unsigned got = {called(entry, {'ka': 'ka', 'kb': 'kb'})}, expect = 0;\n"
            f"  for (int j = 0; j < VL; j++) expect |= ((unsigned)(a[j] != 0) {sym} (b[j] != 0)) << j;\n"
            "  out[0] = (got == expect) ? 1 : 0;"
        )
        ref = "for (int j = 0; j < VL; j++) ref[j] = 0;\n  ref[0] = 1;"
        return f"{k.loads}\n  {compute}", ref
    eq = f"_mm256_cmpeq_{k.suffix}"
    ones = "_mm256_set1_epi64x(-1)" if k.dtype == "i64" else "_mm256_set1_epi32(-1)"
    za, zb = f"{eq}(va, _mm256_setzero_si256())", f"{eq}(vb, _mm256_setzero_si256())"
    expr = (
        f"_mm256_and_si256(_mm256_andnot_si256({za}, {ones}), _mm256_andnot_si256({zb}, {ones}))"
        if op == "land"
        else f"_mm256_andnot_si256(_mm256_and_si256({za}, {zb}), {ones})"
    )
    return k.stored(f"__m256i vr = {expr};"), lane_ref(f"((a[j] != 0) {sym} (b[j] != 0)) ? -1 : 0")


def f16_body(op: str, entry: Entry) -> tuple[str, str]:
    """AVX2's f16 entries, hand-coded over all 16 lanes: memory ops and the bitwise recipes work on the
    storage, arithmetic converts each 8-lane half to f32 and back. The reference is native _Float16
    arithmetic (gcc >= 12, clang >= 15)."""
    load, store = "_mm256_loadu_si256((const __m256i*)h)", "_mm256_storeu_si256((__m256i*)out16, vr);"
    plain = lane_ref("(double)(_Float16)h[j]")
    if op == "load":
        return f"__m256i vr = {entry.intrinsic}((const __m256i*)h);\n  {store}", plain
    if op == "store":
        return f"__m256i vr = {load};\n  {entry.intrinsic}((__m256i*)out16, vr);", plain
    if op == "broadcast":
        body = f"short bits;\n  memcpy(&bits, h, 2);\n  __m256i vr = {entry.intrinsic}(bits);\n  {store}"
        return body, lane_ref("(double)(_Float16)h[0]")
    if op == "select":
        and_, andnot, or_ = entry.recipe
        body = (
            f"__m256i m = _mm256_loadu_si256((const __m256i*)mk), hb = _mm256_loadu_si256((const __m256i*)k);\n"
            f"  __m256i vr = {or_}({and_}({load}, m), {andnot}(m, hb));\n  {store}"
        )
        return body, lane_ref("mk[j] ? (double)(_Float16)h[j] : (double)(_Float16)k[j]")
    if op in ("abs", "neg"):
        set1, bitop = entry.recipe
        mask = "0x7fff" if op == "abs" else "(short)0x8000"
        expr = "(_Float16)h[j] < 0 ? -(_Float16)h[j] : (_Float16)h[j]" if op == "abs" else "-(_Float16)h[j]"
        return f"__m256i vr = {bitop}({load}, {set1}({mask}));\n  {store}", lane_ref(f"(double)({expr})")
    to_f32, f32op, to_f16 = entry.recipe
    if op == "fma":
        compute = f"__m256 vr = {f32op}(fa, fb, fa);"
        ref = lane_ref("(_Float16)h[j] * (_Float16)k[j] + (_Float16)h[j]")
    elif op == "sqrt":
        compute = f"__m256 vr = {f32op}(fa);"
        ref = lane_ref("sqrtf((float)(_Float16)h[j])")
    else:
        compute = f"__m256 vr = {f32op}(fa, fb);"
        ref = lane_ref(f"(double)({F16_ARITHMETIC[op]})")
    body = (
        f"for (int o = 0; o < VL; o += 8) {{\n"
        f"    __m128i ha = _mm_loadu_si128((const __m128i*)(h + o)), hb = _mm_loadu_si128((const __m128i*)(k + o));\n"
        f"    __m256 fa = {to_f32}(ha), fb = {to_f32}(hb);\n    {compute}\n"
        f"    __m128i hr = {to_f16}(vr, _MM_FROUND_TO_NEAREST_INT | _MM_FROUND_NO_EXC);\n"
        f"    _mm_storeu_si128((__m128i*)(out16 + o), hr);\n  }}"
    )
    return body, ref


#: The reference of each two-operand f16 op.
F16_ARITHMETIC = {
    "add": "(_Float16)h[j] + (_Float16)k[j]",
    "sub": "(_Float16)h[j] - (_Float16)k[j]",
    "mul": "(_Float16)h[j] * (_Float16)k[j]",
    "div": "(_Float16)h[j] / (_Float16)k[j]",
    "min": "((_Float16)h[j] < (_Float16)k[j]) ? (_Float16)h[j] : (_Float16)k[j]",
    "max": "((_Float16)h[j] > (_Float16)k[j]) ? (_Float16)h[j] : (_Float16)k[j]",
}
#: Sixteen exact f16 values per operand, no zero divisor; ``F16_POSITIVE`` feeds sqrt.
F16_A = (1.0, 0.5, 2.0, 1.5, -0.25, 3.5, -1.25, 0.75, 2.5, -3.0, 0.125, 4.0, -0.5, 1.75, 0.625, -2.25)
F16_B = (0.25, 3.0, 0.75, 2.5, 1.5, -0.5, 2.0, -1.0, 0.5, 1.25, -2.0, 0.375, 3.5, -0.75, 1.0, 2.25)


def integer_inputs(op: str, dtype: str, lanes: int) -> tuple[list[int], list[int], list[int]]:
    """Signs alternate, so an arithmetic shift cannot pass for a logical one; land/lor get every zero / non-zero
    combination; the operands differ on every lane, so no order of a three-operand op passes for another."""
    logical = op in ("land", "lor")
    high = 1 << 40 if dtype == "i64" and op in ("and", "or", "shl", "shr") else 0  # a bit past lane 32's reach
    a = [0 if logical and j % 2 == 0 else (7 + 3 * j) * (-1 if j % 2 else 1) + high for j in range(lanes)]
    return a, [0 if logical and j % 4 < 2 else 1 + j for j in range(lanes)], [2 + 5 * j for j in range(lanes)]


def float_inputs(op: str, lanes: int) -> tuple[list[float], list[float], list[float]]:
    """Not dyadic, so rounding is exercised; signs alternate except for sqrt; the operands differ on every lane, so no
    order of fma passes for another."""
    # every third lane is larger than b, so a compare goes both ways and a quotient passes 1
    scale = [10.0 if j % 3 == 2 else 1.0 for j in range(lanes)]
    a = [(0.5371 + 0.3 * j) * scale[j] * (-1 if j % 2 and op != "sqrt" else 1) for j in range(lanes)]
    return a, [1.25 + 0.7 * j for j in range(lanes)], [0.3171 + 0.9 * j for j in range(lanes)]


def f16_source(op: str, compute: str, ref: str) -> str:
    """The C source of an f16 kernel."""
    h_init = ", ".join(repr(abs(v) if op == "sqrt" else v) for v in (0.0, *F16_A))
    k_init = ", ".join(map(repr, (0.0, *F16_B)))
    mk_init = ", ".join("0xffff" if j % 2 == 0 else "0" for j in range(16))
    return f"""#include <immintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#ifndef __FLT16_MAX__
#error "_Float16 is required for f16 reference values"
#endif
#define VL 16
int main(void) {{
  _Alignas(64) _Float16 h_lanes[VL + 1] = {{{h_init}}};
  _Alignas(64) _Float16 k_lanes[VL + 1] = {{{k_init}}};
  _Float16 *h = h_lanes + 1, *k = k_lanes + 1;  // {MISALIGNED}
  uint16_t mk[VL] = {{{mk_init}}};
  double ref[VL] = {{0}};
  _Alignas(64) uint16_t out_lanes[VL + 1] = {{0}};
  uint16_t *out16 = out_lanes + 1;
  {compute}
  {ref}
  {lane_errors("(double)*((_Float16*)&out16[j])", "ref[j]")}"""


def kernel_c(isa: str, dtype: str, op: str, table: Table | None = None) -> str | None:
    """The full C source for a validation kernel, or None when the entry has no executable form."""
    isa = ALIASES.get(isa, isa)
    body = kernel_body(isa, dtype, op, table or load()) if isa in ("avx2", "avx512") else None
    if body is None:
        return None
    compute, ref = body
    if dtype == "f16":
        return f16_source(op, compute, ref)
    lanes = (512 if isa == "avx512" else 256) // (8 * LANE_BYTES[dtype])
    a, b, c = integer_inputs(op, dtype, lanes) if dtype in INT_DTYPES else float_inputs(op, lanes)
    idx_init = ", ".join(str((3 * j + 1) % lanes) for j in range(lanes))
    s = X86_LANES[dtype][0]
    return f"""#include <immintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <math.h>
#define VL {lanes}
int main(void) {{
  _Alignas(64) {s} a_lanes[VL + 1] = {{0, {", ".join(map(repr, a))}}};
  _Alignas(64) {s} b_lanes[VL + 1] = {{0, {", ".join(map(repr, b))}}};
  _Alignas(64) {s} c_lanes[VL + 1] = {{0, {", ".join(map(repr, c))}}};
  _Alignas(64) {s} out_lanes[VL + 1] = {{0}};
  {s} *a = a_lanes + 1, *b = b_lanes + 1, *c = c_lanes + 1, *out = out_lanes + 1;  // {MISALIGNED}
  int64_t idx[VL] = {{{idx_init}}};
  int32_t idx32[VL] = {{{idx_init}}};
  double ref[VL] = {{0}};
  {compute}
  {ref}
  {lane_errors("(double)out[j]", "ref[j]")}"""


def c_compiler() -> str | None:
    return shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")


class HostCannotRun(RuntimeError):
    """The toolchain or the host, not the row, stopped the kernel."""


@functools.lru_cache(maxsize=None, typed=True)
def toolchain_builds(flags: tuple[str, ...], libs: tuple[str, ...]) -> bool:
    """Whether a trivial kernel builds and runs with ``flags`` and ``libs``: a failure past it is the row's."""
    try:
        return (
            compile_run('#include <stdio.h>\nint main(void) { printf("ALLOY-VERIFY rel=0\\n"); }', list(flags), libs)
            == 0
        )
    except RuntimeError:
        return False


def compile_run(source: str, flags: list[str], libs: tuple[str, ...] = ()) -> float:
    """Compile and run a kernel; the rel error it prints. Raises RuntimeError on build/run failure."""
    cc = c_compiler()
    if cc is None:
        raise RuntimeError("no C compiler on PATH")
    with tempfile.TemporaryDirectory(prefix="alloy_verify_") as tmp:
        c_file, exe = pathlib.Path(tmp) / "kernel.c", pathlib.Path(tmp) / "kernel"
        c_file.write_text(source)
        try:
            build = subprocess.run(
                [cc, "-O0", *flags, str(c_file), *libs, "-lm", "-o", str(exe)],  # -O0: nothing folds the intrinsic away
                capture_output=True,
                text=True,
                check=False,
                timeout=COMPILE_TIMEOUT,
            )
            if build.returncode != 0:
                raise RuntimeError(f"build failed: {build.stderr.strip()[:400]}")
            run = subprocess.run([str(exe)], capture_output=True, text=True, check=False, timeout=COMPILE_TIMEOUT)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"timed out after {COMPILE_TIMEOUT} s: {exc.cmd[0]}") from None
        except OSError as exc:  # a noexec temporary folder
            raise HostCannotRun(f"cannot execute a kernel here: {exc}") from None
        if run.returncode != 0:
            raise RuntimeError(f"kernel exited {run.returncode}: {run.stderr.strip()[:200]}")
    match = VERIFY_LINE.search(run.stdout)
    if match is None:
        raise RuntimeError(f"kernel printed no verify line: {run.stdout[:200]!r}")
    return float(match.group(1))


#: The half-width of a tier's domain, by how the domain's text names it.
TIER_SPANS = {"pi/4": math.pi / 4, "pi/2": math.pi / 2, "ln(2)/2": math.log(2) / 2}
#: What a tier's recipe steps call; ``eval`` sees only these, the recipe's own names and no builtins.
TIER_STEPS: dict[str, Any] = {
    "mul": np.multiply,
    "add": np.add,
    "sub": np.subtract,
    "div": np.divide,
    "fma": lambda p, q, r: p * q + r,
}


def evaluate_tier(tier: Any) -> tuple[np.ndarray, Any]:
    """Evaluate a tier's Horner recipe (abstract-op steps) on its domain; returns (grid, approx)."""
    half = next((half for key, half in TIER_SPANS.items() if key in tier.domain), None)
    if half is None:
        raise ValueError(f"{tier}: cannot parse the domain")
    x = np.linspace(-half, half, N_TIER)
    names: dict[str, Any] = {**TIER_STEPS, "x": x}
    value: Any = x
    for step in tier.recipe:
        name, _, expression = step.strip().partition(" = ")
        value = names[name.strip()] = eval(expression, {"__builtins__": {}}, names)
    return x, value


def validate_tier(name: str, table: Table | None = None) -> Verdict:
    """Re-measure a tier's error against libm; ok when the recorded error_ulp reproduces within slack."""
    table = table or load()
    tier = table.approx[name]
    x, approx = evaluate_tier(tier)
    reference = {"sin": np.sin, "cos": np.cos, "exp": np.exp}[tier.op](x)
    magnitude = np.maximum(np.abs(reference), 1.0)
    spacing = np.nextafter(magnitude, np.inf) - magnitude
    ulp = float(np.max(np.abs(approx - reference) / spacing))
    abs_err = float(np.max(np.abs(approx - reference)))
    ok = ulp <= tier.error_ulp * TIER_SLACK
    detail = f"measured {ulp:.4g} ulp (recorded {tier.error_ulp:.4g}, abs {abs_err:.3e})"
    return Verdict(ok, "tier re-measured vs libm", detail)


def library_kernel(call: str, op: str, dtype: str) -> str:
    """The glibc vector ABI passes the vector BY VALUE in a register and returns it in a register —
    the N<n> in ``_ZGV?N<n>v_`` names the lane count and picks the vector type."""
    s, letter, _ = X86_LANES[dtype]
    suffix = "" if dtype == "f64" else "f"
    width = re.search(r"N(\d+)v_", call)
    if width is None:
        raise ValueError(f"{call}: not a vector ABI name")
    lanes = int(width.group(1))
    vec = f"__m{lanes * 8 * LANE_BYTES[dtype]}{letter}"
    values = ", ".join(f"{0.5 + 0.25 * j}{suffix}" for j in range(lanes))
    return f"""#include <immintrin.h>
#include <math.h>
#include <stdio.h>
#define VL {lanes}
extern {vec} {call}({vec});
int main(void) {{
  _Alignas(64) {s} a[VL] = {{{values}}};
  _Alignas(64) {s} r[VL];
  *({vec}*)r = {call}(*({vec}*)a);
  {lane_errors("(double)r[j]", f"{op}((double)a[j])")}"""


def candidates_for(isa: str, op: str, dtype: str, table: Table | None = None) -> tuple[Hit, ...]:
    """The potentially relevant spellings for a failed (isa, op, dtype): the same op on the ISA's other
    dtypes and on the other ISAs, plus the reverse-lookup family of the committed intrinsic/mnemonic."""
    table = table or load()
    entry = table.entry(isa, op, dtype)
    hits: list[Hit] = []
    for other in ALL_DTYPES:
        if other != dtype:
            with contextlib.suppress(KeyError):
                hits.append(Hit(isa, other, op, table.entry(isa, op, other), "same op, other dtype"))
    for name in (name for name in table.isas if name != ALIASES.get(isa, isa)):
        with contextlib.suppress(KeyError):
            hits.append(Hit(name, dtype, op, table.entry(name, op, dtype), "same op, other ISA"))
    for name in (entry.intrinsic, entry.mnemonic):
        if name:
            hits.extend(table.reverse(name))
    seen, out = set(), []
    for hit in hits:
        key = (hit.isa, hit.dtype, hit.op)
        if key not in seen:
            seen.add(key)
            out.append(hit)
    return tuple(out)


def within(rel: float, tol: float, basis: str, isa: str, op: str, dtype: str, table: Table) -> Verdict:
    """A kernel's measured error against its tolerance; a miss carries the candidates."""
    ok = rel <= tol
    detail = f"max rel err {rel:.3e} vs tolerance {tol:.3e}"
    return Verdict(ok, basis, detail, candidates_for(isa, op, dtype, table) if not ok else ())


def validate_transcendental(isa: str, op: str, dtype: str, table: Table, entry: Entry) -> Verdict:
    """The library call is checked against libm when it is built here; every cited tier is re-measured."""
    tiers = [validate_tier(key, table) for key in entry.approximations]
    best = next((tier for tier in tiers if tier.ok is False), tiers[-1])
    if best.ok is False:
        return Verdict(False, best.basis, best.detail, candidates_for(isa, op, dtype, table))
    if (
        ALIASES.get(isa, isa) in ("avx2", "avx512")
        and dtype in DTYPES
        and host_can_run(isa, dtype)
        and (call := entry.libraries.get("libmvec"))
        and c_compiler()
    ):
        try:
            rel = compile_run(library_kernel(call, op, dtype), c_flags(isa, dtype), ("-lmvec",))
        except (RuntimeError, ValueError) as exc:
            if not toolchain_builds(tuple(c_flags(isa, dtype)), ("-lmvec",)):
                return Verdict(None, f"this toolchain has no libmvec (unverified, not wrong): {exc}")
            return Verdict(False, "libmvec kernel", str(exc), candidates_for(isa, op, dtype, table))
        return within(rel, TOL_LIBRARY[dtype], "libmvec kernel vs libm", isa, op, dtype, table)
    if not host_can_run(isa, dtype):
        return Verdict(
            None, f"{isa}/{dtype}: tier re-measured in Python, the row's library calls never ran", best.detail
        )
    return Verdict(True, best.basis, best.detail)


def unexercised(entry: Entry, source: str) -> list[str]:
    """The spellings of ``entry`` the kernel ``source`` never calls: a check of those proves nothing."""
    names = [entry.intrinsic] if entry.intrinsic else []
    names += [name for step in entry.recipe for name in SPELLED.findall(step)]
    return [name for name in names if name not in source]


def validate(isa: str, op: str, dtype: str, table: Table | None = None) -> Verdict:
    """Validate one entry: compile-and-run on the host where possible, re-measure tiers, and on failure
    attach the candidate spellings. ``ok is None``: not verifiable here (never reported as correct)."""
    table = table or load()
    entry = table.entry(isa, op, dtype)
    if OPS[op].kind == "transcendental":
        return validate_transcendental(isa, op, dtype, table, entry)
    if not host_can_run(isa, dtype):
        return Verdict(None, f"host cannot execute {isa}/{dtype} kernels (unverified, not wrong)")
    if c_compiler() is None:
        return Verdict(None, "no C compiler on PATH (unverified, not wrong)")
    try:
        source = kernel_c(isa, dtype, op, table)
    except ValueError as exc:  # a recipe of the wrong shape
        return Verdict(False, "compiled kernel", str(exc), candidates_for(isa, op, dtype, table))
    if source is None:
        return Verdict(None, "no compiled validator for this entry yet (the table spelling is still in force)")
    if missing := unexercised(entry, source):
        return Verdict(None, f"the validator kernel does not run {', '.join(missing)}")
    try:
        rel = compile_run(source, c_flags(isa, dtype))
    except HostCannotRun as exc:
        return Verdict(None, str(exc))
    except (RuntimeError, ValueError) as exc:
        if not toolchain_builds(tuple(c_flags(isa, dtype)), ()):
            return Verdict(None, f"this toolchain cannot build {isa}/{dtype} kernels (unverified, not wrong): {exc}")
        return Verdict(False, "compiled kernel", str(exc), candidates_for(isa, op, dtype, table))
    tol = TOL_F16 if dtype == "f16" else TOL.get(op, 0.0)
    if dtype == "f32" and op in ("mod", "reduce_add"):
        tol = max(tol, 1e-5)  # single-precision arithmetic vs the double reference
    return within(rel, tol, "compiled kernel", isa, op, dtype, table)


def validate_all(table: Table | None = None, jobs: int = 8) -> list[tuple[str, Verdict]]:
    """Every entry plus every tier, in parallel, ``ok is None`` for what this host cannot execute; (id, verdict)."""
    table = table or load()
    ids = [
        f"{isa}/{dtype}/{op}"
        for isa, target in table.isas.items()
        for dtype in ALL_DTYPES
        for op in target.entries(dtype)
    ]

    def one(ident: str) -> Verdict:
        isa, dtype, op = ident.split("/")
        return validate(isa, op, dtype, table)

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        verdicts = list(pool.map(one, ids))
        tiers = list(pool.map(lambda name: validate_tier(name, table), table.approx))
    return [*zip(ids, verdicts, strict=True), *zip((f"approx/{n}" for n in table.approx), tiers, strict=True)]
