# Copyright 2026 ETH Zurich and the Alloy authors.
"""Numerical validation of table entries: the intrinsic or recipe of a row is run before a lookup returns it where
that is possible, and every row that did not run says unverified. Masked forms, mnemonics and notes are not checked.

An entry runs natively (AVX2+FMA, AVX-512F+DQ, aarch64) or under qemu-aarch64 when that and the cross compiler are on
PATH: fixed inputs, on buffers no vector boundary aligns, through a small compiled C kernel that calls the row in its
signature's operand order, or runs its ``code`` as written, against a scalar reference and a per-op tolerance;
:func:`unexercised` refuses a kernel that skips a spelling. An approximation tier is re-measured in numpy against libm:
the recorded ``error_ulp`` must reproduce within a slack, which catches transcription errors in the coefficients. On a
failure :func:`candidates_for` names a shortlist.

``Verdict.ok is None`` means not run: the row can still fail by not compiling for its target, but compiling verifies
nothing, so unverified is never reported as correct.
"""

import ast
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
from alloy.isa.table import ALIASES, ALL_DTYPES, DTYPES, F16, INT_DTYPES, LANE_BYTES, SPELLED, Entry, Hit, Table, load
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
#: A signature's literal operand: ``(0.0) -> v``, ``(a, b, _CMP_LT_OQ) -> mask``.
LITERAL = re.compile(r"\d[\d.]*f?|_[A-Z_]+")
WORD = re.compile(r"\b[A-Za-z_]\w*\b")
#: The -march of each aarch64 target when another host builds it, by this compiler.
CROSS = {"neon": "armv8.2-a", "sve": "armv8.2-a+sve"}
CROSS_CC = "aarch64-linux-gnu-gcc"
HEADERS = {"avx2": "immintrin.h", "avx512": "immintrin.h", "neon": "arm_neon.h", "sve": "arm_sve.h"}
NEON_BYTES = 16
SVE_MAX_BYTES = 256  # the longest vector the architecture allows
SVE_BITS = 512  # the vector length emulated kernels run at


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
    """Whether this host compiles AND executes kernels for ``(isa, dtype)`` natively; see :func:`emulated`."""
    flags, machine = host_flags(), platform.machine()
    isa = ALIASES.get(isa, isa)
    if machine == "x86_64":
        if isa == "avx2":
            return {"avx2", "fma", "f16c"} <= flags if dtype == "f16" else {"avx2", "fma"} <= flags
        if isa == "avx512":  # the kernels and the k-mask entries need DQ
            return {"avx512f", "avx512dq", *(("avx512_fp16",) if dtype == "f16" else ())} <= flags
        return False
    if machine == "aarch64":
        return {"neon": "asimdhp" if dtype == "f16" else "asimd", "sve": "sve"}.get(isa, "") in flags
    return False


#: dtype -> (scalar C type, letter of its x86 vector type, intrinsic suffix).
X86_LANES = {
    "f64": ("double", "d", "pd"),
    "f32": ("float", "", "ps"),
    "f16": ("_Float16", "h", "ph"),
    "i64": ("int64_t", "i", "epi64"),
    "i32": ("int32_t", "i", "epi32"),
}
#: dtype -> (scalar C type, element of its vector types, intrinsic suffix, the SVE lane count).
ARM_LANES = {
    "f64": ("double", "float64", "f64", "svcntd()"),
    "f32": ("float", "float32", "f32", "svcntw()"),
    "f16": ("float16_t", "float16", "f16", "svcnth()"),
    "i64": ("int64_t", "int64", "s64", "svcntd()"),
    "i32": ("int32_t", "int32", "s32", "svcntw()"),
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
    """What every kernel of one ``(isa, dtype)`` shares: its C types, the loads and the store, and two rows it leans
    on: ``below`` is ``a < b`` as a mask, ``masked_load`` reads ``a`` under the mask ``k``."""

    isa: str
    dtype: str
    scalar: str
    vector: str
    mask: str
    suffix: str
    lanes: int
    cast: str = ""
    loads: str = ""
    store: str = ""
    below: str = ""
    masked_load: str = ""
    one: str = ""
    zero: str = ""

    def stored(self, compute: str) -> str:
        return f"{self.loads}\n  {compute}\n  {self.store}"

    @property
    def wide(self) -> bool:
        return self.isa == "avx512"

    @property
    def fp(self) -> bool:
        return self.dtype in DTYPES

    @property
    def lane_bits(self) -> int:
        return 8 * LANE_BYTES[self.dtype]


def x86_frame(isa: str, dtype: str) -> Frame:
    scalar, letter, suffix = X86_LANES[dtype]
    bits = 512 if isa == "avx512" else 256
    letter = "i" if dtype == F16 and bits == 256 else letter
    vector, lanes = f"__m{bits}{letter}", bits // (8 * LANE_BYTES[dtype])
    return Frame(
        isa,
        dtype,
        scalar,
        vector,
        f"__mmask{lanes}" if bits == 512 else vector,
        suffix,
        lanes,
        f"({vector}*)" if letter == "i" else "",
    )


def arm_frame(isa: str, dtype: str) -> Frame:
    """Buffers hold the longest SVE vector; a kernel touches ``VL`` lanes, read at run time on SVE."""
    scalar, element, suffix, _ = ARM_LANES[dtype]
    width = 8 * LANE_BYTES[dtype]
    if isa == "sve":
        return Frame(isa, dtype, scalar, f"sv{element}_t", "svbool_t", suffix, SVE_MAX_BYTES // LANE_BYTES[dtype])
    lanes = NEON_BYTES // LANE_BYTES[dtype]
    return Frame(isa, dtype, scalar, f"{element}x{lanes}_t", f"uint{width}x{lanes}_t", suffix, lanes)


def frame(isa: str, dtype: str, table: Table) -> Frame:
    """The frame of ``(isa, dtype)``, spelled with the table's own load, store, compare and broadcast."""
    k = arm_frame(isa, dtype) if isa in CROSS else x86_frame(isa, dtype)
    load_row, store_row, set1 = (table.entry(isa, op, dtype) for op in ("load", "store", "broadcast"))
    names = {"a": "va", "b": "vb", "pg": "pg"}
    below = BELOW_F16[isa] if dtype == F16 else called(table.entry(isa, "lt", dtype), names)
    masked = f"{load_row.masked.split('(', 1)[0]}(k, a)" if k.wide else called(load_row, {"pg": "k", "p": "a"})
    loads = {name: called(load_row, {"pg": "pg", "p": f"{k.cast}{name}"}) for name in "abc"}
    predicate = f"svbool_t pg = svptrue_b{k.lane_bits}();\n  " if isa == "sve" else ""
    return dataclasses.replace(
        k,
        loads=predicate + "\n  ".join(f"{k.vector} v{name} = {load};" for name, load in loads.items()),
        store=f"{called(store_row, {'pg': 'pg', 'p': f'{k.cast}out', 'v': 'vr'})};",
        below=below,
        masked_load=masked,
        one=called(set1, {"s": "1"}),
        zero=called(set1, {"s": "0"}),
    )


#: ``a < b`` on f16 lanes, which have no ``lt`` row. AVX2 has no f16 compare: ``mk`` holds the answer, as a mask.
BELOW_F16 = {
    "avx2": "_mm256_loadu_si256((const __m256i*)mk)",
    "avx512": "_mm512_cmp_ph_mask(va, vb, _CMP_LT_OQ)",
    "neon": "vcltq_f16(va, vb)",
    "sve": "svcmplt_f16(pg, va, vb)",
}


def operands(k: Frame) -> dict[str, str]:
    """What the names of a signature are in a kernel. AVX2 broadcasts an f16 from its raw bits; SVE's fma has names."""
    s = "*(short*)a" if (k.isa, k.dtype) == ("avx2", F16) else "a[0]"
    names = {"a": "va", "b": "vb", "c": "vc", "v": "va", "counts": "vb", "s": s, "pg": "pg"}
    return names | {"p": f"{k.cast}a", "add": "va", "m1": "vb", "m2": "vc"}


def operand_names(entry: Entry, names: dict[str, str]) -> dict[str, str]:
    """The operands of ``entry`` in its ``signature``'s order, as ``names`` spells them; a literal stands for itself."""
    match = SIGNATURE.match(entry.signature)
    written = [name.strip() for name in match.group(1).split(",") if name.strip()] if match else []
    if match is None or any(name not in names and LITERAL.fullmatch(name) is None for name in written):
        raise ValueError(f"{entry.intrinsic}: the signature {entry.signature!r} names no operands of this op")
    return {name: names.get(name, name) for name in written}


def called(entry: Entry, names: dict[str, str]) -> str:
    """``entry``'s intrinsic on ``names`` in the order its ``signature`` states, so the gate runs the order a reader
    of the row copies."""
    return f"{entry.intrinsic}({', '.join(operand_names(entry, names).values())})"


def assigned(target: str, entry: Entry, names: dict[str, str]) -> str:
    """C leaving the row's result in ``target``, which holds ``= `` if any: its intrinsic in signature order, or its
    ``code`` as written, with the operands renamed. The gate runs what a reader of the row copies."""
    if not entry.code:
        return f"{target}{called(entry, names)};"
    renames = operand_names(entry, names)
    *statements, last = [WORD.sub(lambda word: renames.get(word[0], word[0]), line) for line in entry.code]
    return "".join(f"{line};\n  " for line in statements) + f"{target}{last};"


def lane_ref(expression: str) -> str:
    """The scalar reference of a kernel: ``expression`` for every lane."""
    return f"for (int j = 0; j < VL; j++) ref[j] = {expression};"


def blended(k: Frame, mask: str) -> str:
    """A vector of ones where ``mask`` holds and zeros elsewhere: how a kernel reads a mask, whatever its type."""
    return {
        "avx2": f"_mm256_blendv_{k.suffix if k.fp else 'epi8'}({k.zero}, {k.one}, {mask})",
        "avx512": f"_mm512_mask_blend_{k.suffix}({mask}, {k.zero}, {k.one})",
        "neon": f"vbslq_{k.suffix}({mask}, {k.one}, {k.zero})",
        "sve": f"svsel_{k.suffix}({mask}, {k.one}, {k.zero})",
    }[k.isa]


def call_body(k: Frame, op: str, entry: Entry) -> tuple[str, str]:
    return k.stored(assigned(f"{k.vector} vr = ", entry, operands(k))), scalar_ref(k, op)


def store_body(k: Frame, op: str, entry: Entry) -> tuple[str, str]:
    return k.stored(f"{k.vector} vr = vb;"), scalar_ref(k, op)


def lt_body(k: Frame, op: str, entry: Entry) -> tuple[str, str]:
    compute = f"{k.mask} m = {k.below};\n  {k.vector} vr = {blended(k, 'm')};"
    return k.stored(compute), lane_ref("a[j] < b[j] ? 1 : 0")


def select_body(k: Frame, op: str, entry: Entry) -> tuple[str, str]:
    names = {"a": "va", "b": "vb", "t": "vb", "f": "va", "k": "k", "mask": "k", "pg": "k"}
    pick = assigned(f"{k.vector} vr = ", entry, names)
    return k.stored(f"{k.mask} k = {k.below};\n  {pick}"), lane_ref("a[j] < b[j] ? b[j] : a[j]")


def reduce_body(k: Frame, op: str, entry: Entry) -> tuple[str, str]:
    compute = assigned(f"{k.scalar} r = ", entry, operands(k))
    return f"{k.loads}\n  {compute}\n  out[0] = r;", "for (int j = 0; j < VL; j++) ref[0] += a[j];"


def indices(k: Frame, entry: Entry) -> tuple[str, str]:
    """How a gather or scatter takes its indices: the statements that load them, and their operand. A row built from
    per-lane steps indexes the array; f32 gathers index in 32-bit lanes."""
    if entry.code or k.isa == "neon":
        return "", "idx"
    source = "idx" if k.lane_bits == 64 else "idx32"
    if k.isa == "sve":
        return f"svint{k.lane_bits}_t vi = svld1_s{k.lane_bits}(pg, {source});\n  ", "vi"
    bits = 512 if k.wide else 256
    return f"__m{bits}i vi = _mm{bits}_loadu_si{bits}((const __m{bits}i*){source});\n  ", "vi"


def gather_body(k: Frame, op: str, entry: Entry) -> tuple[str, str]:
    load, index = indices(k, entry)
    names = {"base": "a", "idx": index, "scale": str(LANE_BYTES[k.dtype]), "pg": "pg"}
    return k.stored(f"{load}{assigned(f'{k.vector} vr = ', entry, names)}"), lane_ref("a[idx[j]]")


def scatter_body(k: Frame, op: str, entry: Entry) -> tuple[str, str]:
    load, index = indices(k, entry)
    names = {"base": "out", "idx": index, "v": "va", "scale": str(LANE_BYTES[k.dtype]), "pg": "pg"}
    ref = "for (int j = 0; j < VL; j++) ref[j] = 0;\nfor (int j = 0; j < VL; j++) ref[idx[j]] = a[j];"
    return f"{k.loads}\n  {load}{assigned('', entry, names)}", ref


def gen_mask_body(k: Frame, op: str, entry: Entry) -> tuple[str, str]:
    if k.wide:
        iota = ", ".join(str(j) for j in range(k.lanes))
        setup = f"__m512i iota = _mm512_setr_epi{k.lane_bits}({iota});\n  "
        names = {"iota": "iota", "n": f"_mm512_set1_epi{k.lane_bits}(n)"}
    else:
        setup, names = "", {"i": "0", "N": "n"}
    compute = f"int n = VL - 1;\n  {setup}{k.mask} k = {called(entry, names)};\n  {k.vector} vr = {k.masked_load};"
    return k.stored(compute), lane_ref("j < n ? a[j] : 0")


def logical_body(k: Frame, op: str, entry: Entry) -> tuple[str, str]:
    """land/lor: all-ones lanes on AVX2 and NEON, a mask on AVX-512 and SVE, which a kernel reads as ones."""
    truth = f"(a[j] != 0) {'&&' if op == 'land' else '||'} (b[j] != 0)"
    if k.isa in ("avx2", "neon"):
        vector = assigned(f"{k.vector} vr = ", entry, operands(k))
        return k.stored(vector), lane_ref(f"({truth}) ? -1 : 0")
    tests = ""
    if k.wide:
        cmp, zero = f"_mm512_cmpneq_{k.suffix}_mask", "_mm512_setzero_si512()"
        tests = f"{k.mask} ka = {cmp}(va, {zero}), kb = {cmp}(vb, {zero});\n  "
    mask = assigned(f"{k.mask} m = ", entry, operands(k) | {"ka": "ka", "kb": "kb"})
    return k.stored(f"{tests}{mask}\n  {k.vector} vr = {blended(k, 'm')};"), lane_ref(f"({truth}) ? 1 : 0")


#: Ops whose kernel is more than one row on the frame's operands.
BODIES: dict[str, Callable[[Frame, str, Entry], tuple[str, str]]] = {
    "store": store_body,
    "lt": lt_body,
    "select": select_body,
    "reduce_add": reduce_body,
    "gather": gather_body,
    "scatter": scatter_body,
    "gen_mask": gen_mask_body,
    "land": logical_body,
    "lor": logical_body,
}


def scalar_ref(k: Frame, op: str) -> str:
    if k.dtype in INT_DTYPES:
        s, u = ("int64_t", "uint64_t") if k.dtype == "i64" else ("int32_t", "uint32_t")
        refs = {
            "and": "a[j] & b[j]",
            "or": "a[j] | b[j]",
            "shl": f"({s})(({u})a[j] << b[j])",
            "shr": f"({s})(({u})a[j] >> b[j])",  # logical: a negative lane must not sign-fill
            "add": f"({s})(({u})a[j] + ({u})b[j])",
            "sub": f"({s})(({u})a[j] - ({u})b[j])",
            "mul": f"({s})(({u})a[j] * ({u})b[j])",
            "mod": "a[j] % b[j]",
            "min": "a[j] < b[j] ? a[j] : b[j]",
            "max": "a[j] > b[j] ? a[j] : b[j]",
            "load": "a[j]",
            "store": "b[j]",
            "broadcast": "a[0]",
        }
        return lane_ref(refs[op])
    f = "f" if k.dtype == "f32" else ""  # a float lane is checked against the float libm, f16 against a wider one
    refs = {
        "add": "a[j] + b[j]",
        "sub": "a[j] - b[j]",
        "mul": "a[j] * b[j]",
        "div": "a[j] / b[j]",
        "min": "a[j] < b[j] ? a[j] : b[j]",
        "max": "a[j] > b[j] ? a[j] : b[j]",
        "fma": f"fma{f}(b[j], c[j], a[j])" if k.isa in CROSS else f"fma{f}(a[j], b[j], c[j])",
        "sqrt": f"sqrt{f}(a[j])",
        "abs": "a[j] < 0 ? -a[j] : a[j]",
        "neg": "-a[j]",
        "mod": f"fmod{f}(a[j], b[j])",
        "load": "a[j]",
        "store": "b[j]",
        "broadcast": "a[0]",
        "zero": "0",
    }
    return lane_ref(f"({k.scalar})({refs[op]})" if k.dtype == F16 else refs[op])


#: Sixteen exact f16 values per operand, no zero divisor; a longer vector repeats them, and sqrt takes their size.
F16_A = (1.0, 0.5, 2.0, 1.5, -0.25, 3.5, -1.25, 0.75, 2.5, -3.0, 0.125, 4.0, -0.5, 1.75, 0.625, -2.25)
F16_B = (0.25, 3.0, 0.75, 2.5, 1.5, -0.5, 2.0, -1.0, 0.5, 1.25, -2.0, 0.375, 3.5, -0.75, 1.0, 2.25)
F16_C = (0.75, -1.5, 2.25, 0.5, 3.0, 1.25, -0.125, 2.0, -0.75, 1.5, 0.25, -3.5, 1.0, 0.375, -2.0, 0.5)


def integer_inputs(op: str, dtype: str, lanes: int) -> tuple[list[int], list[int], list[int]]:
    """Signs alternate, so an arithmetic shift cannot pass for a logical one; land/lor get every zero / non-zero
    combination; the operands differ on every lane, so no order of a three-operand op passes for another; ``b`` stays
    a legal shift count at any vector length."""
    logical = op in ("land", "lor")
    high = 1 << 40 if dtype == "i64" and op in ("and", "or", "shl", "shr") else 0  # a bit past lane 32's reach
    a = [0 if logical and j % 2 == 0 else (7 + 3 * j) * (-1 if j % 2 else 1) + high for j in range(lanes)]
    return a, [0 if logical and j % 4 < 2 else 1 + j % 29 for j in range(lanes)], [2 + 5 * j for j in range(lanes)]


def float_inputs(op: str, lanes: int) -> tuple[list[float], list[float], list[float]]:
    """Not dyadic, so rounding is exercised; signs alternate except for sqrt; the operands differ on every lane, so no
    order of fma passes for another."""
    # every third lane is larger than b, so a compare goes both ways and a quotient passes 1
    scale = [10.0 if j % 3 == 2 else 1.0 for j in range(lanes)]
    a = [(0.5371 + 0.3 * j) * scale[j] * (-1 if j % 2 and op != "sqrt" else 1) for j in range(lanes)]
    return a, [1.25 + 0.7 * j for j in range(lanes)], [0.3171 + 0.9 * j for j in range(lanes)]


def f16_inputs(op: str, lanes: int) -> tuple[list[float], list[float], list[float]]:
    a = [abs(F16_A[j % 16]) if op == "sqrt" else F16_A[j % 16] for j in range(lanes)]
    return a, [F16_B[j % 16] for j in range(lanes)], [F16_C[j % 16] for j in range(lanes)]


def lane_count(k: Frame) -> str:
    """Lanes of a vector in C: a run-time query on SVE, whose buffers only bound it."""
    return f"((int){ARM_LANES[k.dtype][3]})" if k.isa == "sve" else str(k.lanes)


def kernel_inputs(op: str, dtype: str, lanes: int) -> tuple[list[Any], list[Any], list[Any]]:
    if dtype == F16:
        return f16_inputs(op, lanes)
    return integer_inputs(op, dtype, lanes) if dtype in INT_DTYPES else float_inputs(op, lanes)


def kernel_c(isa: str, dtype: str, op: str, table: Table | None = None) -> str | None:
    """The full C source for a validation kernel, or None for a row with no spelling to run (a transcendental)."""
    isa = ALIASES.get(isa, isa)
    table = table or load()
    entry = table.entry(isa, op, dtype)
    if entry.approximations:
        return None
    k = frame(isa, dtype, table)
    compute, ref = BODIES.get(op, call_body)(k, op, entry)
    a, b, c = kernel_inputs(op, dtype, k.lanes)
    mask = "uint16_t mk[LANES];\n  for (int j = 0; j < VL; j++) mk[j] = a[j] < b[j] ? 0xffff : 0;"
    s = k.scalar
    return f"""#include <{HEADERS[isa]}>
#include <stdint.h>
#include <stdio.h>
#include <math.h>
#define LANES {k.lanes}
#define VL {lane_count(k)}
int main(void) {{
  _Alignas(64) {s} a_lanes[LANES + 1] = {{0, {", ".join(map(repr, a))}}};
  _Alignas(64) {s} b_lanes[LANES + 1] = {{0, {", ".join(map(repr, b))}}};
  _Alignas(64) {s} c_lanes[LANES + 1] = {{0, {", ".join(map(repr, c))}}};
  _Alignas(64) {s} out_lanes[LANES + 1] = {{0}};
  {s} *a = a_lanes + 1, *b = b_lanes + 1, *c = c_lanes + 1, *out = out_lanes + 1;  // {MISALIGNED}
  int64_t idx[LANES];
  int32_t idx32[LANES];
  for (int j = 0; j < VL; j++) idx[j] = idx32[j] = (3 * j + 1) % VL;
  double ref[LANES] = {{0}};
  {mask if dtype == F16 else ""}
  {compute}
  {ref}
  {lane_errors("(double)out[j]", "ref[j]")}"""


def c_compiler() -> str | None:
    return shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")


#: How a host runs an aarch64 target it is not: (cross compiler, build flags, launcher).
Emulator = tuple[str, tuple[str, ...], tuple[str, ...]]


def emulated(isa: str) -> Emulator | None:
    """How this host runs an aarch64 ``isa`` under qemu, or None. A kernel run this way earns a real verdict."""
    cc, qemu = shutil.which(CROSS_CC), shutil.which("qemu-aarch64") or shutil.which("qemu-aarch64-static")
    if isa not in CROSS or platform.machine() == "aarch64" or cc is None or qemu is None:
        return None
    return cc, (f"-march={CROSS[isa]}", "-static"), (qemu, "-cpu", f"max,sve{SVE_BITS}=on")


def target_compiler(isa: str) -> str | None:
    """What builds ``isa`` here, whether or not the result can run."""
    return shutil.which(CROSS_CC) if isa in CROSS and platform.machine() != "aarch64" else c_compiler()


class HostCannotRun(RuntimeError):
    """The toolchain or the host, not the row, stopped the kernel."""


@functools.lru_cache(maxsize=None, typed=True)
def toolchain_builds(flags: tuple[str, ...], libs: tuple[str, ...], emulator: Emulator | None = None) -> bool:
    """Whether a trivial kernel builds and runs with ``flags`` and ``libs``: a failure past it is the row's."""
    source = '#include <stdio.h>\nint main(void) { printf("ALLOY-VERIFY rel=0\\n"); }'
    try:
        return compile_run(source, list(flags), libs, emulator) == 0
    except RuntimeError:
        return False


def compile_unit(source: str, cc: str, flags: list[str]) -> None:
    """Compile ``source`` to an object and no further. Raises RuntimeError when it does not build."""
    with tempfile.TemporaryDirectory(prefix="alloy_verify_") as tmp:
        c_file = pathlib.Path(tmp) / "kernel.c"
        c_file.write_text(source)
        command = [cc, "-O1", "-Werror=implicit-function-declaration", *flags, "-c", str(c_file)]
        try:
            build = subprocess.run(
                [*command, "-o", str(c_file.with_suffix(".o"))],
                capture_output=True,
                text=True,
                check=False,
                timeout=COMPILE_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"timed out after {COMPILE_TIMEOUT} s: {cc}") from None
    if build.returncode != 0:
        raise RuntimeError(f"build failed: {build.stderr.strip()[:400]}")


def compile_run(source: str, flags: list[str], libs: tuple[str, ...] = (), emulator: Emulator | None = None) -> float:
    """Compile and run a kernel, under ``emulator`` if given; the rel error it prints. Raises RuntimeError on build or
    run failure."""
    cc, launcher = (emulator[0], emulator[2]) if emulator else (c_compiler(), ())
    if cc is None:
        raise RuntimeError("no C compiler on PATH")
    static = ["-static"] if emulator else []
    with tempfile.TemporaryDirectory(prefix="alloy_verify_") as tmp:
        c_file, exe = pathlib.Path(tmp) / "kernel.c", pathlib.Path(tmp) / "kernel"
        c_file.write_text(source)
        try:
            build = subprocess.run(
                [cc, "-O0", *flags, *static, str(c_file), *libs, "-lm", "-o", str(exe)],  # -O0: nothing folds it away
                capture_output=True,
                text=True,
                check=False,
                timeout=COMPILE_TIMEOUT,
            )
            if build.returncode != 0:
                raise RuntimeError(f"build failed: {build.stderr.strip()[:400]}")
            run = subprocess.run(
                [*launcher, str(exe)], capture_output=True, text=True, check=False, timeout=COMPILE_TIMEOUT
            )
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
TIER_SPANS = {"pi/4": math.pi / 4, "pi/2": math.pi / 2, "ln(2)/2": math.log(2) / 2, "3-2*sqrt(2)": 3 - 2 * math.sqrt(2)}
#: The only syntax a tier step may hold: calls and names, no attribute, so ``eval`` reaches nothing past its names.
TIER_SYNTAX = (ast.Expression, ast.Call, ast.Name, ast.Load, ast.Constant, ast.UnaryOp, ast.USub)
#: What a tier's recipe steps call; ``eval`` sees only these, the recipe's own names and no builtins.
TIER_STEPS: dict[str, Any] = {
    "mul": np.multiply,
    "add": np.add,
    "sub": np.subtract,
    "div": np.divide,
    "fma": lambda p, q, r: p * q + r,
}


def tier_step(expression: str) -> Any:
    """A tier step compiled, or ``ValueError`` when it is more than calls on names."""
    tree = ast.parse(expression, mode="eval")
    if not all(isinstance(node, TIER_SYNTAX) for node in ast.walk(tree)):
        raise ValueError(f"tier step {expression!r}: only calls on names")
    return compile(tree, "<tier>", "eval")


def run_tier(tier: Any, x: np.ndarray) -> Any:
    """A tier's Horner recipe (abstract-op steps) at ``x``."""
    names: dict[str, Any] = {**TIER_STEPS, "x": x}
    value: Any = x
    for step in tier.recipe:
        name, _, expression = step.strip().partition(" = ")
        value = names[name.strip()] = eval(tier_step(expression), {"__builtins__": {}}, names)
    return value


def evaluate_tier(tier: Any) -> tuple[np.ndarray, Any]:
    """A tier on its domain: (grid, approx)."""
    half = next((half for key, half in TIER_SPANS.items() if key in tier.domain), None)
    if half is None:
        raise ValueError(f"{tier}: cannot parse the domain")
    x = np.linspace(-half, half, N_TIER)
    return x, run_tier(tier, x)


#: What a tier approximates on its grid; a log tier's x is (m-1)/(m+1), so it computes 2*atanh(x) = log(m).
TIER_REFERENCES: dict[str, Callable[[np.ndarray], np.ndarray]] = {
    "sin": np.sin,
    "cos": np.cos,
    "exp": np.exp,
    "log": lambda x: 2 * np.arctanh(x),
}


def tier_error(tier: Any) -> tuple[float, float]:
    """A tier's worst error against libm: in units of 2^-52 at function scale, and absolute."""
    x, approx = evaluate_tier(tier)
    reference = TIER_REFERENCES[tier.op](x)
    magnitude = np.maximum(np.abs(reference), 1.0)
    spacing = np.nextafter(magnitude, np.inf) - magnitude
    return float(np.max(np.abs(approx - reference) / spacing)), float(np.max(np.abs(approx - reference)))


def validate_tier(name: str, table: Table | None = None) -> Verdict:
    """Re-measure a tier's error against libm; ok when the recorded error_ulp reproduces within slack."""
    table = table or load()
    tier = table.approx[name]
    ulp, abs_err = tier_error(tier)
    ok = ulp <= tier.error_ulp * TIER_SLACK
    detail = f"measured {ulp:.4g} ulp (recorded {tier.error_ulp:.4g}, abs {abs_err:.3e})"
    return Verdict(ok, "tier re-measured vs libm", detail)


def library_kernel(call: str, isa: str, op: str, dtype: str, table: Table) -> str:
    """The vector ABI passes the vector in a register and returns it in one; SVE's masked form adds the predicate. The
    types come from ``isa``, not from ``call``, so a variant of another width cannot pass for the row."""
    k = frame(isa, dtype, table)
    suffix = "" if dtype == "f64" else "f"
    values = ", ".join(f"{0.5 + 0.25 * j}{suffix}" for j in range(k.lanes))
    predicate = (", svbool_t", ", pg") if isa == "sve" else ("", "")
    convention = "__attribute__((aarch64_vector_pcs)) " if isa == "neon" else ""
    return f"""#include <{HEADERS[isa]}>
#include <math.h>
#include <stdio.h>
#define VL {lane_count(k)}
extern {convention}{k.vector} {call}({k.vector}{predicate[0]});
int main(void) {{
  {k.scalar} a_lanes[{k.lanes}] = {{{values}}}, out_lanes[{k.lanes}];
  {k.scalar} *a = a_lanes, *b = a_lanes, *c = a_lanes, *out = out_lanes;
  {k.stored(f"{k.vector} vr = {call}(va{predicate[1]});")}
  {lane_errors("(double)out[j]", f"{op}((double)a[j])")}"""


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


def library_verdict(isa: str, op: str, dtype: str, table: Table, call: str, emulator: Emulator | None) -> Verdict:
    """The row's libmvec call, run against libm."""
    flags = c_flags(isa, dtype)
    try:
        rel = compile_run(library_kernel(call, isa, op, dtype, table), flags, ("-lmvec",), emulator)
    except RuntimeError as exc:
        if not toolchain_builds(tuple(flags), ("-lmvec",), emulator):
            return Verdict(None, f"this toolchain has no libmvec (unverified, not wrong): {exc}")
        return Verdict(False, "libmvec kernel", str(exc), candidates_for(isa, op, dtype, table))
    return within(rel, TOL_LIBRARY[dtype], f"libmvec kernel vs libm{emulator_note(emulator)}", isa, op, dtype, table)


def validate_transcendental(isa: str, op: str, dtype: str, table: Table, entry: Entry) -> Verdict:
    """The library call is checked against libm when it can run here; every cited tier is re-measured."""
    isa = ALIASES.get(isa, isa)
    tiers = [validate_tier(key, table) for key in entry.approximations]
    best = next((tier for tier in tiers if tier.ok is False), tiers[-1])
    if best.ok is False:
        return Verdict(False, best.basis, best.detail, candidates_for(isa, op, dtype, table))
    native, emulator = host_can_run(isa, dtype), emulated(isa)
    if (call := entry.libraries.get("libmvec")) and dtype in DTYPES and ((native and c_compiler()) or emulator):
        return library_verdict(isa, op, dtype, table, call, None if native else emulator)
    if not native:
        return Verdict(
            None, f"{isa}/{dtype}: tier re-measured in Python, the row's library calls never ran", best.detail
        )
    return Verdict(True, best.basis, best.detail)


def unexercised(entry: Entry, source: str) -> list[str]:
    """The spellings of ``entry`` the kernel ``source`` never calls: a check of those proves nothing."""
    names = [entry.intrinsic] if entry.intrinsic else []
    names += [name for step in entry.recipe for name in SPELLED.findall(step)]
    return [name for name in names if name not in source]


def emulator_note(emulator: Emulator | None) -> str:
    return " under qemu" if emulator else ""


def run_verdict(source: str, isa: str, op: str, dtype: str, table: Table, emulator: Emulator | None) -> Verdict:
    """The kernel ``source`` run here or under ``emulator``: the only way a row earns ok True."""
    flags = c_flags(isa, dtype)
    try:
        rel = compile_run(source, flags, (), emulator)
    except HostCannotRun as exc:
        return Verdict(None, str(exc))
    except RuntimeError as exc:
        if not toolchain_builds(tuple(flags), (), emulator):
            return Verdict(None, f"this toolchain cannot build {isa}/{dtype} kernels (unverified, not wrong): {exc}")
        return Verdict(False, "compiled kernel", str(exc), candidates_for(isa, op, dtype, table))
    tol = TOL_F16 if (isa, dtype) == ("avx2", F16) else TOL.get(op, 0.0)
    if dtype == "f32" and op in ("mod", "reduce_add"):
        tol = max(tol, 1e-5)  # single-precision arithmetic vs the double reference
    return within(rel, tol, f"compiled kernel{emulator_note(emulator)}", isa, op, dtype, table)


def build_verdict(source: str, isa: str, op: str, dtype: str, table: Table) -> Verdict:
    """A target this host cannot run: the row's spelling and operand types can still fail to compile, but compiling
    verifies nothing, so the best verdict here is None."""
    basis = f"host cannot execute {isa}/{dtype} kernels (unverified, not wrong)"
    cc = target_compiler(isa)
    if cc is None:
        return Verdict(None, basis, "no compiler for this target")
    try:
        compile_unit(source, cc, c_flags(isa, dtype))
    except RuntimeError as exc:
        try:
            compile_unit("int main(void) { return 0; }", cc, c_flags(isa, dtype))
        except RuntimeError:
            return Verdict(None, basis, f"this toolchain cannot build {isa}/{dtype}: {exc}")
        return Verdict(False, "cross-compiled kernel", str(exc), candidates_for(isa, op, dtype, table))
    return Verdict(None, basis, "compiled for the target, never run")


def validate(isa: str, op: str, dtype: str, table: Table | None = None) -> Verdict:
    """Validate one entry: compile-and-run on the host or under qemu where possible, cross-compile where not, re-measure
    tiers, and on failure attach the candidate spellings. ``ok is None``: not verified (never reported as correct)."""
    table = table or load()
    entry = table.entry(isa, op, dtype)
    isa = ALIASES.get(isa, isa)
    if OPS[op].kind == "transcendental":
        return validate_transcendental(isa, op, dtype, table, entry)
    native, emulator = host_can_run(isa, dtype), emulated(isa)
    if native and c_compiler() is None:
        return Verdict(None, "no C compiler on PATH (unverified, not wrong)")
    try:
        source = kernel_c(isa, dtype, op, table)
    except ValueError as exc:  # a signature naming what the op does not have
        return Verdict(False, "compiled kernel", str(exc), candidates_for(isa, op, dtype, table))
    missing = unexercised(entry, source or "")
    if source is None or missing:
        return Verdict(None, f"the validator kernel does not run {', '.join(missing) or 'this row'}")
    if native or emulator:
        return run_verdict(source, isa, op, dtype, table, None if native else emulator)
    return build_verdict(source, isa, op, dtype, table)


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
