# Copyright 2026 ETH Zurich and the Alloy authors.
"""Numerical validation of table entries: every spelling an agent gets from a lookup is checked before
it is returned. Two validators, one idea — never hand the agent an unverified mapping:

- x86 entries the host can execute (AVX2+FMA, AVX-512F+DQ) are checked by a small compiled C kernel:
  fixed inputs through the looked-up intrinsic (or its fallback recipe, hand-coded once per op and ISA
  family — :func:`unexercised` refuses a kernel that skips a spelling, so a wrong mapping is caught
  rather than propagated), a scalar reference, and a per-op tolerance.
- approximation tiers ([approx]) are re-measured in numpy against libm on their domain: the recorded
  ``error_ulp`` must reproduce within a slack, which catches transcription errors in the coefficients.

When validation fails, :func:`candidates_for` names the potentially relevant spellings — same op on
other dtypes and ISAs, the reverse-lookup family — so the caller returns a shortlist with an explicit
failure notice instead of a wrong answer.

``Verdict.ok is None`` means not verifiable on this host (NEON/SVE, for which no kernels exist yet,
AVX-512 FP16 without the hardware, entries with no executable form, no C compiler): unverified is never
reported as correct.
"""

import contextlib
import dataclasses
import pathlib
import platform
import re
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from alloy.isa.ops import OPS
from alloy.isa.table import ALIASES, ALL_DTYPES, DTYPES, INT_DTYPES, SPELLED, Entry, Hit, Table, load

__all__ = ["Verdict", "candidates_for", "host_can_run", "validate", "validate_all", "validate_tier"]

#: Per-op relative-error tolerances for the compiled kernels. IEEE ops are exactly rounded, so their
#: tolerance is zero; order-sensitive ops (reductions, recipes) get a real band.
TOL: dict[str, float] = {
    "add": 0.0,
    "sub": 0.0,
    "mul": 0.0,
    "div": 0.0,
    "min": 0.0,
    "max": 0.0,
    "and": 0.0,
    "or": 0.0,
    "shl": 0.0,
    "shr": 0.0,
    "select": 0.0,
    "abs": 0.0,
    "neg": 0.0,
    "sqrt": 0.0,
    "gather": 0.0,
    "scatter": 0.0,
    "load": 0.0,
    "store": 0.0,
    "broadcast": 0.0,
    "zero": 0.0,
    "gen_mask": 0.0,
    "fma": 1e-15,
    "reduce_add": 1e-12,
    "mod": 1e-13,
}
TOL_F16 = 4e-3  # the AVX2 f16 recipes compute in f32; a few f16 ulps of slack
TOL_LIBRARY = {"f64": 1e-13, "f32": 1e-6}  # vector math library entries vs double libm, by lane type
TIER_SLACK = 2.0  # a tier's re-measured error may exceed the recorded one by this factor
N_TIER = 2_000_000
COMPILE_TIMEOUT = 120  # seconds, per compile and per run

VERIFY_LINE = re.compile(r"^ALLOY-VERIFY rel=(\S+)", re.MULTILINE)


@dataclasses.dataclass(slots=True, frozen=True)
class Verdict:
    """One validation outcome. ``ok`` None = not verifiable on this host (never reported as correct);
    ``candidates`` lists the potentially relevant spellings when the check failed."""

    ok: bool | None
    basis: str
    detail: str = ""
    candidates: tuple[Hit, ...] = ()


# ---------------------------------------------------------------- host capabilities


def _flags() -> frozenset[str]:
    """The host's CPU feature flags — x86 ``flags`` or aarch64 ``Features`` lines."""
    try:
        lines = pathlib.Path("/proc/cpuinfo").read_text(errors="ignore").splitlines()
    except OSError:
        return frozenset()
    wanted = ("flags", "features")
    return frozenset(
        flag
        for line in lines
        for key, _, rest in (line.partition(":"),)
        if key.strip().lower() in wanted
        for flag in rest.split()
    )


def host_can_run(isa: str, dtype: str) -> bool:
    """Whether this host compiles AND executes kernels for ``(isa, dtype)``."""
    flags, machine = _flags(), platform.machine()
    isa = ALIASES.get(isa, isa)
    if machine == "x86_64":
        if isa == "avx2":
            return {"avx2", "fma", "f16c"} <= flags if dtype == "f16" else {"avx2", "fma"} <= flags
        if isa == "avx512":  # the kernels and the k-mask entries need DQ
            needed = {"avx512f", "avx512dq", "avx512fp16"} if dtype == "f16" else {"avx512f", "avx512dq"}
            return needed <= flags
        return False
    if machine == "aarch64":
        return {"neon": "asimd", "sve": "sve"}.get(isa, "") in flags
    return False


# ---------------------------------------------------------------- C kernels (x86)

_X86 = {  # dtype -> (scalar C type, vector type, intrinsic prefix, suffix)
    "f64": ("double", "__m256d", "_mm256", "pd"),
    "f32": ("float", "__m256", "_mm256", "ps"),
    "i64": ("int64_t", "__m256i", "_mm256", "epi64"),
    "i32": ("int32_t", "__m256i", "_mm256", "epi32"),
}
_X86_512 = {
    "f64": ("double", "__m512d", "_mm512", "pd"),
    "f32": ("float", "__m512", "_mm512", "ps"),
    "i64": ("int64_t", "__m512i", "_mm512", "epi64"),
    "i32": ("int32_t", "__m512i", "_mm512", "epi32"),
}

#: The per-lane error update every kernel ends with: a NaN must stick, a plain ``>`` would drop it.
TRACK_ERROR = "double e = d / m;\n    if (isnan(e) || e > maxrel) maxrel = e;"


def _c_flags(isa: str, dtype: str) -> list[str]:
    isa = ALIASES.get(isa, isa)
    if isa == "neon":
        return []
    if isa == "sve":
        return ["-march=armv8-a+sve"]
    if isa == "avx2":
        return ["-mavx2", "-mfma", "-mf16c"] if dtype == "f16" else ["-mavx2", "-mfma"]
    return ["-mavx512f", "-mavx512dq", "-mavx512fp16"] if dtype == "f16" else ["-mavx512f", "-mavx512dq"]


def _body(isa: str, dtype: str, op: str, table: Table) -> tuple[str, str, float] | None:
    """The kernel body for ``(isa, dtype, op)``, spelled with the table's own entry so a wrong mapping fails:
    (compute C, scalar-reference C, tolerance), or None when the entry has no executable form here."""
    entry = table.entry(isa, op, dtype)
    if dtype == "f16":
        return _f16_body(op, entry) if isa == "avx2" else None
    wide = isa == "avx512"
    lanes = (8 if wide else 4) if dtype in ("f64", "i64") else (16 if wide else 8)
    s, v, p, sfx = (_X86_512 if wide else _X86)[dtype]
    fp = dtype in DTYPES
    bits = 512 if wide else 256
    load = table.entry(isa, "load", dtype).intrinsic if fp else f"{p}_loadu_si{bits}"
    iload = f"{p}_loadu_si{bits}"  # index vectors and integer lanes
    store_fn = table.entry(isa, "store", dtype).intrinsic if fp else f"{p}_storeu_si{bits}"
    cast = "" if fp else f"({v}*)"
    decl = f"{v} va = {load}({cast}a);\n  {v} vb = {load}({cast}b);"
    out_ptr = f"({s}*)out" if fp else f"({v}*)out"
    store = f"{store_fn}({out_ptr}, vr);"
    lanes_s = str(lanes)

    if op in ("land", "lor"):
        if dtype not in INT_DTYPES:
            return None
        return _logical(isa, dtype, op, decl, store, entry)
    if op == "mod" and dtype in INT_DTYPES:
        # the documented recipe (no vector remainder, r = a - q*b per lane) against libm
        compute = "for (int j = 0; j < VL; j++) out[j] = a[j] - (a[j] / b[j]) * b[j];"
        return compute, "for (int j = 0; j < VL; j++) ref[j] = fmod((double)a[j], (double)b[j]);", 0.0

    if op == "abs" or op == "neg":
        if not fp:
            return None  # integer abs/neg are not tabled
        mask = {
            "abs": "(long long)0x7fffffffffffffffULL" if dtype == "f64" else "(int)0x7fffffffU",
            "neg": "(long long)0x8000000000000000ULL" if dtype == "f64" else "(int)0x80000000U",
        }[op]
        if wide:
            set1 = f"{p}_set1_{'epi64' if dtype == 'f64' else 'epi32'}"
            compute = f"{v} vr = {p}_castsi512_{sfx}({entry.recipe[0]}({p}_cast{sfx}_si512(va), {set1}({mask})));"
        else:
            to_float, set1, bitop = entry.recipe
            compute = f"{v} vr = {bitop}(va, {to_float}({set1}({mask})));"
        ref = (
            "for (int j = 0; j < VL; j++) ref[j] = a[j] < 0 ? -a[j] : a[j];"
            if op == "abs"
            else "for (int j = 0; j < VL; j++) ref[j] = -a[j];"
        )
        return f"{decl}\n  {compute}\n  {store}", ref, 0.0

    if op == "select":
        if not fp:
            return None
        if wide:
            compute = f"__mmask{lanes_s} k = {p}_cmp_{sfx}_mask(va, vb, _CMP_LT_OQ);\n  {v} vr = {entry.intrinsic}(k, vb, va);"
        else:
            compute = f"{v} k = {p}_cmp_{sfx}(va, vb, _CMP_LT_OQ);\n  {v} vr = {entry.intrinsic}(vb, va, k);"
        ref = "for (int j = 0; j < VL; j++) ref[j] = a[j] < b[j] ? a[j] : b[j];"
        return f"{decl}\n  {compute}\n  {store}", ref, 0.0

    if op == "reduce_add":
        if not fp:
            return None
        if wide:
            compute = f"{s} r = {entry.intrinsic}(va);\n  out[0] = r;"
        elif dtype == "f64":
            compute = (
                "__m128d lo = _mm256_castpd256_pd128(va), hi = _mm256_extractf128_pd(va, 1);\n"
                "  __m128d s2 = _mm_add_pd(lo, hi);\n"
                "  __m128d sh = _mm_unpackhi_pd(s2, s2);\n"
                "  double r = _mm_cvtsd_f64(_mm_add_sd(s2, sh));\n  out[0] = r;"
            )
        else:
            compute = (
                "__m128 lo = _mm256_castps256_ps128(va), hi = _mm256_extractf128_ps(va, 1);\n"
                "  __m128 s2 = _mm_add_ps(lo, hi);\n"
                "  __m128 sh = _mm_movehdup_ps(s2);\n"
                "  s2 = _mm_add_ps(s2, sh);\n  sh = _mm_movehl_ps(sh, s2);\n"
                "  s2 = _mm_add_ss(s2, sh);\n"
                "  float r = _mm_cvtss_f32(s2);\n  out[0] = r;"
            )
        ref = "for (int j = 0; j < VL; j++) ref[0] += a[j];"
        return f"{decl}\n  {compute}", ref, TOL["reduce_add"]

    if op in ("gather", "scatter"):
        if not fp:
            return None
        vi_t = f"__m{bits}i"
        scale = "8" if dtype == "f64" else "4"
        idx_arr = "idx" if dtype == "f64" else "idx32"  # f32 gathers index in 32-bit lanes
        idx_ld = f"{vi_t} vi = {iload}((const {vi_t}*){idx_arr});"
        if op == "gather":
            args = f"vi, a, {scale}" if wide else f"a, vi, {scale}"
            g = f"{idx_ld}\n  {v} vr = {entry.intrinsic}({args});"
            return f"{decl}\n  {g}\n  {store}", "for (int j = 0; j < VL; j++) ref[j] = a[idx[j]];", 0.0
        if wide:
            compute = f"{idx_ld}\n  {entry.intrinsic}(out, vi, va, {scale});"
        else:  # AVX2 has no scatter: the documented fallback, hand-coded
            compute = f"{s} buf[VL];\n  {store_fn}(buf, va);\n  for (int j = 0; j < VL; j++) out[idx[j]] = buf[j];"
        ref = "for (int j = 0; j < VL; j++) ref[j] = 0;\nfor (int j = 0; j < VL; j++) ref[idx[j]] = a[j];"
        return f"{decl}\n  {compute}", ref, 0.0

    if op == "gen_mask":
        if not wide or not fp:
            return None
        width = "64" if dtype == "f64" else "32"
        iota = ", ".join(str(j) for j in range(lanes))
        masked_load = table.entry(isa, "load", dtype).masked.split("(", 1)[0]
        compute = (
            f"__m512i iota = {p}_setr_epi{width}({iota});\n  int n = VL - 1;\n"
            f"  __mmask{lanes_s} k = {entry.intrinsic}(iota, {p}_set1_epi{width}(n));\n"
            f"  {v} vr = {masked_load}(k, a);"
        )
        ref = "for (int j = 0; j < VL; j++) ref[j] = j < n ? a[j] : 0;"
        return f"{decl}\n  {compute}\n  {store}", ref, 0.0

    if op == "mod":
        if not fp:
            return None
        div, trunc, fnmadd = entry.recipe
        rounding = "0x0B" if wide else "_MM_FROUND_TO_ZERO | _MM_FROUND_NO_EXC"
        compute = f"{v} q = {trunc}({div}(va, vb), {rounding});\n  {v} vr = {fnmadd}(q, vb, va);"
        ref = f"for (int j = 0; j < VL; j++) ref[j] = fmod{'' if dtype == 'f64' else 'f'}(a[j], b[j]);"
        return f"{decl}\n  {compute}\n  {store}", ref, TOL["mod"]

    name = entry.intrinsic
    exprs = {
        "add": f"{name}(va, vb)",
        "sub": f"{name}(va, vb)",
        "mul": f"{name}(va, vb)",
        "div": f"{name}(va, vb)",
        "min": f"{name}(va, vb)",
        "max": f"{name}(va, vb)",
        "fma": f"{name}(va, vb, va)",
        "and": f"{name}(va, vb)",
        "or": f"{name}(va, vb)",
        "shl": f"{name}(va, vb)",
        "shr": f"{name}(va, vb)",
        "sqrt": f"{name}(va)",
        "load": f"{name}(a)",
        "store": "vb",
        "broadcast": f"{name}(a[0])",
        "zero": f"{name}()",
    }
    if op not in exprs:
        return None
    compute = f"{v} vr = {exprs[op]};"
    ref = _scalar_ref(op, dtype)
    return f"{decl}\n  {compute}\n  {store}", ref, TOL.get(op, 0.0)


def _scalar_ref(op: str, dtype: str) -> str:
    if dtype in INT_DTYPES:
        s, u = ("int64_t", "uint64_t") if dtype == "i64" else ("int32_t", "uint32_t")
        refs = {
            "and": "a[j] & b[j]",
            "or": "a[j] | b[j]",
            "shl": f"({s})(({u})a[j] << b[j])",
            "shr": f"({s})(({u})a[j] >> b[j])",  # logical: a negative lane must not sign-fill
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
            "fma": f"fma{f}(a[j], b[j], a[j])",
            "sqrt": f"sqrt{f}(a[j])",
            "load": "a[j]",
            "store": "b[j]",
            "broadcast": "a[0]",
            "zero": "0",
        }
    return f"for (int j = 0; j < VL; j++) ref[j] = {refs[op]};"


def _logical(isa: str, dtype: str, op: str, decl: str, store: str, entry: Entry) -> tuple[str, str, float]:
    """land/lor, full kernel body: k-register ops on AVX-512, the andnot-of-compares recipe on AVX2."""
    wide = isa == "avx512"
    sym = "&&" if op == "land" else "||"
    if wide:
        bits = "8" if dtype == "i64" else "16"
        cmp = f"_mm512_cmpneq_{'epi64' if dtype == 'i64' else 'epi32'}_mask"
        compute = (
            f"__mmask{bits} ka = {cmp}(_mm512_loadu_si512((const __m512i*)a), _mm512_setzero_si512());\n"
            f"  __mmask{bits} kb = {cmp}(_mm512_loadu_si512((const __m512i*)b), _mm512_setzero_si512());\n"
            f"  unsigned got = {entry.intrinsic}(ka, kb), expect = 0;\n"
            f"  for (int j = 0; j < VL; j++) expect |= ((unsigned)(a[j] != 0) {sym} (b[j] != 0)) << j;\n"
            "  out[0] = (got == expect) ? 1 : 0;"
        )
        ref = "for (int j = 0; j < VL; j++) ref[j] = 0;\n  ref[0] = 1;"
        return f"{decl}\n  {compute}", ref, 0.0
    eq = f"_mm256_cmpeq_{'epi64' if dtype == 'i64' else 'epi32'}"
    ones = "_mm256_set1_epi64x(-1)" if dtype == "i64" else "_mm256_set1_epi32(-1)"
    za, zb = f"{eq}(va, _mm256_setzero_si256())", f"{eq}(vb, _mm256_setzero_si256())"
    expr = (
        f"_mm256_and_si256(_mm256_andnot_si256({za}, {ones}), _mm256_andnot_si256({zb}, {ones}))"
        if op == "land"
        else f"_mm256_andnot_si256(_mm256_and_si256({za}, {zb}), {ones})"
    )
    ref = f"for (int j = 0; j < VL; j++) ref[j] = ((a[j] != 0) {sym} (b[j] != 0)) ? -1 : 0;"
    return f"{decl}\n  __m256i vr = {expr};\n  {store}", ref, 0.0


def _f16_body(op: str, entry: Entry) -> tuple[str, str, float]:
    """AVX2's f16 entries, hand-coded over all 16 lanes: memory ops and the bitwise recipes work on the
    storage, arithmetic converts each 8-lane half to f32 and back. The reference is native _Float16
    arithmetic (gcc >= 12, clang >= 15)."""
    load, store = "_mm256_loadu_si256((const __m256i*)h)", "_mm256_storeu_si256((__m256i*)out16, vr);"
    plain = "for (int j = 0; j < VL; j++) ref[j] = (double)(_Float16)h[j];"
    if op == "load":
        return f"__m256i vr = {entry.intrinsic}((const __m256i*)h);\n  {store}", plain, 0.0
    if op == "store":
        return f"__m256i vr = {load};\n  {entry.intrinsic}((__m256i*)out16, vr);", plain, 0.0
    if op == "broadcast":
        ref = "for (int j = 0; j < VL; j++) ref[j] = (double)(_Float16)h[0];"
        return f"short bits;\n  memcpy(&bits, h, 2);\n  __m256i vr = {entry.intrinsic}(bits);\n  {store}", ref, 0.0
    if op == "select":
        and_, andnot, or_ = entry.recipe
        body = (
            f"__m256i m = _mm256_loadu_si256((const __m256i*)mk), hb = _mm256_loadu_si256((const __m256i*)k);\n"
            f"  __m256i vr = {or_}({and_}({load}, m), {andnot}(m, hb));\n  {store}"
        )
        ref = "for (int j = 0; j < VL; j++) ref[j] = mk[j] ? (double)(_Float16)h[j] : (double)(_Float16)k[j];"
        return body, ref, 0.0
    if op in ("abs", "neg"):
        set1, bitop = entry.recipe
        mask = "0x7fff" if op == "abs" else "(short)0x8000"
        expr = "(_Float16)h[j] < 0 ? -(_Float16)h[j] : (_Float16)h[j]" if op == "abs" else "-(_Float16)h[j]"
        ref = f"for (int j = 0; j < VL; j++) ref[j] = (double)({expr});"
        return f"__m256i vr = {bitop}({load}, {set1}({mask}));\n  {store}", ref, 0.0
    to_f32, f32op, to_f16 = entry.recipe
    if op == "fma":
        compute = f"__m256 vr = {f32op}(fa, fb, fa);"
        ref = "for (int j = 0; j < VL; j++) ref[j] = (_Float16)h[j] * (_Float16)k[j] + (_Float16)h[j];"
    elif op == "sqrt":
        compute = f"__m256 vr = {f32op}(fa);"
        ref = "for (int j = 0; j < VL; j++) ref[j] = sqrtf((float)(_Float16)h[j]);"
    else:
        compute = f"__m256 vr = {f32op}(fa, fb);"
        expr = {
            "add": "(_Float16)h[j] + (_Float16)k[j]",
            "sub": "(_Float16)h[j] - (_Float16)k[j]",
            "mul": "(_Float16)h[j] * (_Float16)k[j]",
            "div": "(_Float16)h[j] / (_Float16)k[j]",
            "min": "((_Float16)h[j] < (_Float16)k[j]) ? (_Float16)h[j] : (_Float16)k[j]",
            "max": "((_Float16)h[j] > (_Float16)k[j]) ? (_Float16)h[j] : (_Float16)k[j]",
        }[op]
        ref = f"for (int j = 0; j < VL; j++) ref[j] = (double)({expr});"
    body = (
        f"for (int o = 0; o < VL; o += 8) {{\n"
        f"    __m128i ha = _mm_loadu_si128((const __m128i*)(h + o)), hb = _mm_loadu_si128((const __m128i*)(k + o));\n"
        f"    __m256 fa = {to_f32}(ha), fb = {to_f32}(hb);\n    {compute}\n"
        f"    __m128i hr = {to_f16}(vr, _MM_FROUND_TO_NEAREST_INT | _MM_FROUND_NO_EXC);\n"
        f"    _mm_storeu_si128((__m128i*)(out16 + o), hr);\n  }}"
    )
    return body, ref, TOL_F16


#: Sixteen exact f16 values per operand, no zero divisor; ``F16_POSITIVE`` feeds sqrt.
F16_A = (1.0, 0.5, 2.0, 1.5, -0.25, 3.5, -1.25, 0.75, 2.5, -3.0, 0.125, 4.0, -0.5, 1.75, 0.625, -2.25)
F16_B = (0.25, 3.0, 0.75, 2.5, 1.5, -0.5, 2.0, -1.0, 0.5, 1.25, -2.0, 0.375, 3.5, -0.75, 1.0, 2.25)


def _inputs(op: str, dtype: str, lanes: int) -> tuple[str, str]:
    """Kernel inputs. Floats are not dyadic, so rounding is exercised, and alternate in sign except for
    sqrt. Integers alternate in sign, so an arithmetic shift cannot pass for a logical one, and land/lor
    get every zero / non-zero combination."""
    a: list[int] | list[float]
    b: list[int] | list[float]
    if dtype in INT_DTYPES:
        logical = op in ("land", "lor")
        a = [0 if logical and j % 2 == 0 else (7 + 3 * j) * (-1 if j % 2 else 1) for j in range(lanes)]
        b = [0 if logical and j % 4 < 2 else 1 + j for j in range(lanes)]
    else:
        a = [(0.5371 + 0.3 * j) * (-1 if j % 2 and op != "sqrt" else 1) for j in range(lanes)]
        b = [1.25 + 0.7 * j for j in range(lanes)]
    return ", ".join(map(repr, a)), ", ".join(map(repr, b))


def kernel_c(isa: str, dtype: str, op: str, table: Table | None = None) -> str | None:
    """The full C source for a validation kernel, or None when the entry has no executable form."""
    isa = ALIASES.get(isa, isa)
    body = _body(isa, dtype, op, table or load()) if isa in ("avx2", "avx512") else None
    if body is None:
        return None
    compute, ref, _tol = body
    wide = isa == "avx512"
    lanes = (16 if wide else 8) if dtype in ("f32", "i32") else (8 if wide else 4)
    s = {"f64": "double", "f32": "float", "i64": "int64_t", "i32": "int32_t", "f16": "uint16_t"}[dtype]
    if dtype == "f16":
        h_init = ", ".join(repr(abs(v) if op == "sqrt" else v) for v in F16_A)
        k_init = ", ".join(map(repr, F16_B))
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
  _Float16 h[VL] = {{{h_init}}};
  _Float16 k[VL] = {{{k_init}}};
  uint16_t mk[VL] = {{{mk_init}}};
  double ref[VL] = {{0}};
  uint16_t out16[VL] = {{0}};
  {compute}
  {ref}
  double maxrel = 0;
  for (int j = 0; j < VL; j++) {{
    double got = (double)*((_Float16*)&out16[j]);
    double d = fabs(got - ref[j]);
    double m = fabs(ref[j]) > 1 ? fabs(ref[j]) : 1;
    {TRACK_ERROR}
  }}
  printf("ALLOY-VERIFY rel=%.6e\\n", maxrel);
  return 0;
}}"""
    a_init, b_init = _inputs(op, dtype, lanes)
    idx_init = ", ".join(str((3 * j + 1) % lanes) for j in range(lanes))
    return f"""#include <immintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <math.h>
#define VL {lanes}
int main(void) {{
  {s} a[VL] = {{{a_init}}};
  {s} b[VL] = {{{b_init}}};
  int64_t idx[VL] = {{{idx_init}}};
  int32_t idx32[VL] = {{{idx_init}}};
  double ref[VL] = {{0}};
  {s} out[VL] = {{0}};
  {compute}
  {ref}
  double maxrel = 0;
  for (int j = 0; j < VL; j++) {{
    double d = fabs((double)out[j] - ref[j]);
    double m = fabs(ref[j]) > 1 ? fabs(ref[j]) : 1;
    {TRACK_ERROR}
  }}
  printf("ALLOY-VERIFY rel=%.6e\\n", maxrel);
  return 0;
}}"""


def _compiler() -> str | None:
    return shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")


def _compile_run(source: str, flags: list[str], libs: tuple[str, ...] = ()) -> float:
    """Compile and run a kernel; the rel error it prints. Raises RuntimeError on build/run failure."""
    cc = _compiler()
    if cc is None:
        raise RuntimeError("no C compiler on PATH")
    with tempfile.TemporaryDirectory(prefix="alloy_verify_") as tmp:
        c_file, exe = pathlib.Path(tmp) / "kernel.c", pathlib.Path(tmp) / "kernel"
        c_file.write_text(source)
        try:
            build = subprocess.run(
                [cc, "-O1", *flags, str(c_file), *libs, "-lm", "-o", str(exe)],
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
        if run.returncode != 0:
            raise RuntimeError(f"kernel exited {run.returncode}: {run.stderr.strip()[:200]}")
    match = VERIFY_LINE.search(run.stdout)
    if match is None:
        raise RuntimeError(f"kernel printed no verify line: {run.stdout[:200]!r}")
    return float(match.group(1))


# ---------------------------------------------------------------- tier validation


def evaluate_tier(tier, n: int = N_TIER):
    """Evaluate a tier's Horner recipe (abstract-op steps) on its domain; returns (grid, approx)."""
    import numpy as np

    domains = [
        ("pi/4", (-0.7853981633974483, 0.7853981633974483)),
        ("pi/2", (-1.5707963267948966, 1.5707963267948966)),
        ("ln(2)/2", (-0.34657359027997264, 0.34657359027997264)),
    ]
    span = next((span for key, span in domains if key in tier.domain), None)
    if span is None:
        raise ValueError(f"{tier}: cannot parse the domain")
    x = np.linspace(span[0], span[1], n)
    env: dict[str, object] = {"x": x}
    name = "x"
    for step in tier.recipe:
        name, _, rhs = step.strip().partition(" = ")
        env[name.strip()] = _eval_expr(rhs, env)
    return x, env[name.strip()]


def _eval_expr(expr: str, env: dict[str, object]):
    """One recipe expression: a number, a variable, or fn(arg, ...) with arbitrary nesting."""
    import numpy as np

    expr = expr.strip()
    if _is_number(expr):
        return float(expr)
    if expr in env:
        return env[expr]
    fn, _, rest = expr.partition("(")
    if not rest.endswith(")"):
        raise ValueError(f"unparseable expression {expr!r}")
    depth, parts, cur = 0, [], ""
    for ch in rest[:-1]:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    values: list[Any] = [_eval_expr(part, env) for part in parts]
    steps: dict[str, Any] = {
        "mul": np.multiply,
        "add": np.add,
        "sub": np.subtract,
        "div": np.divide,
        "fma": lambda p, q, r: p * q + r,
    }
    return steps[fn.strip()](*values)


def _is_number(text: str) -> bool:
    try:
        float(text)
    except ValueError:
        return False
    return True


def validate_tier(name: str, table: Table | None = None, slack: float = TIER_SLACK) -> Verdict:
    """Re-measure a tier's error against libm; ok when the recorded error_ulp reproduces within slack."""
    import numpy as np

    table = table or load()
    tier = table.approx[name]
    x, approx = evaluate_tier(tier)
    reference = {"sin": np.sin, "cos": np.cos, "exp": np.exp}[tier.op](x)
    magnitude = np.maximum(np.abs(reference), 1.0)
    spacing = np.nextafter(magnitude, np.inf) - magnitude
    ulp = float(np.max(np.abs(approx - reference) / spacing))
    abs_err = float(np.max(np.abs(approx - reference)))
    ok = ulp <= tier.error_ulp * slack
    detail = f"measured {ulp:.4g} ulp (recorded {tier.error_ulp:.4g}, abs {abs_err:.3e})"
    return Verdict(ok, "tier re-measured vs libm", detail)


# ---------------------------------------------------------------- library validation


def _library_kernel(call: str, op: str, dtype: str) -> str:
    """The glibc vector ABI passes the vector BY VALUE in a register and returns it in a register —
    the N<n> in ``_ZGV?N<n>v_`` names the lane count and picks the vector type."""
    s = "double" if dtype == "f64" else "float"
    fn = {"sin": "sin", "cos": "cos", "exp": "exp"}[op]
    suffix = "" if dtype == "f64" else "f"
    width = re.search(r"N(\d+)v_", call)
    if width is None:
        raise ValueError(f"{call}: not a vector ABI name")
    lanes = int(width.group(1))
    vec = {
        ("f64", 2): "__m128d",
        ("f64", 4): "__m256d",
        ("f64", 8): "__m512d",
        ("f32", 4): "__m128",
        ("f32", 8): "__m256",
        ("f32", 16): "__m512",
    }[(dtype, lanes)]
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
  double maxrel = 0;
  for (int j = 0; j < VL; j++) {{
    double d = fabs((double)r[j] - {fn}((double)a[j]));
    double m = fabs({fn}((double)a[j])) > 1 ? fabs({fn}((double)a[j])) : 1;
    {TRACK_ERROR}
  }}
  printf("ALLOY-VERIFY rel=%.6e\\n", maxrel);
  return 0;
}}"""


# ---------------------------------------------------------------- candidates and entry validation


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


def _validate_transcendental(isa: str, op: str, dtype: str, table: Table, entry) -> Verdict:
    """The library call is checked against libm when it is built here; the best tier is always re-measured."""
    best = validate_tier(entry.approximations[-1], table)
    if best.ok is False:
        return Verdict(False, best.basis, best.detail, candidates_for(isa, op, dtype, table))
    if (
        ALIASES.get(isa, isa) in ("avx2", "avx512")
        and dtype in DTYPES
        and host_can_run(isa, dtype)
        and (call := entry.libraries.get("libmvec"))
        and _compiler()
    ):
        try:
            rel = _compile_run(_library_kernel(call, op, dtype), _c_flags(isa, dtype), ("-lmvec",))
        except RuntimeError as exc:
            return Verdict(False, "libmvec kernel", str(exc), candidates_for(isa, op, dtype, table))
        tol = TOL_LIBRARY[dtype]
        ok = rel <= tol
        return Verdict(
            ok,
            "libmvec kernel vs libm",
            f"max rel err {rel:.3e} vs tolerance {tol:.3e}",
            candidates_for(isa, op, dtype, table) if not ok else (),
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
        return _validate_transcendental(isa, op, dtype, table, entry)
    if not host_can_run(isa, dtype):
        return Verdict(None, f"host cannot execute {isa}/{dtype} kernels (unverified, not wrong)")
    if _compiler() is None:
        return Verdict(None, "no C compiler on PATH (unverified, not wrong)")
    source = kernel_c(isa, dtype, op, table)
    if source is None:
        return Verdict(None, "no compiled validator for this entry yet (the table spelling is still in force)")
    if missing := unexercised(entry, source):
        return Verdict(None, f"the validator kernel does not run {', '.join(missing)} (unverified, not wrong)")
    try:
        rel = _compile_run(source, _c_flags(isa, dtype))
    except RuntimeError as exc:
        return Verdict(False, "compiled kernel", str(exc), candidates_for(isa, op, dtype, table))
    tol = TOL_F16 if dtype == "f16" else TOL.get(op, 0.0)
    if dtype == "f32" and op in ("mod", "reduce_add"):
        tol = max(tol, 1e-5)  # single-precision arithmetic vs the double reference
    ok = rel <= tol
    detail = f"max rel err {rel:.3e} vs tolerance {tol:.3e}"
    return Verdict(ok, "compiled kernel", detail, candidates_for(isa, op, dtype, table) if not ok else ())


def validate_all(table: Table | None = None, jobs: int = 8) -> list[tuple[str, Verdict]]:
    """Every entry this host can execute plus every tier, in parallel; (id, verdict) pairs."""
    table = table or load()
    ids = [
        f"{isa}/{dtype}/{op}"
        for isa, target in table.isas.items()
        for dtype in ALL_DTYPES
        for op in getattr(target, dtype)
        if host_can_run(isa, dtype)
    ]

    def one(ident: str) -> Verdict:
        isa, dtype, op = ident.split("/")
        return validate(isa, op, dtype, table)

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        verdicts = list(pool.map(one, ids))
    tier_ids = [f"approx/{name}" for name in table.approx]
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        tier_verdicts = list(pool.map(lambda n: validate_tier(n.split("/", 1)[1], table), tier_ids))
    return list(zip([*ids, *tier_ids], [*verdicts, *tier_verdicts], strict=True))
