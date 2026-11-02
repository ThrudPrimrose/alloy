# Copyright 2026 ETH Zurich and the Alloy authors.
"""The instruction lookup table: every abstract math op (:mod:`alloy.isa.ops`) spelled per ISA and dtype,
loaded from the checked-in ``intrinsics.toml`` and indexed in both directions — op -> intrinsic for
writing vector code, intrinsic or assembly mnemonic -> op for reading a build's source or disassembly
back into math."""

import dataclasses
import difflib
import functools
import math
import pathlib
import re
import tomllib
from collections.abc import Iterable

from pydantic import ConfigDict, TypeAdapter
from pydantic.dataclasses import dataclass

from alloy.isa.ops import OPS
from alloy.records import Strings

#: Parsed-table records: unknown keys refused, coercion allowed like configuration_matrix's STRICT; the stricter
#: invariants live in :func:`checked`.
TABLE = ConfigDict(extra="forbid")

__all__ = [
    "ALIASES",
    "ALL_DTYPES",
    "DTYPES",
    "F16",
    "INT_DTYPES",
    "INT_OPS",
    "DEFAULT_PATH",
    "Approx",
    "Assist",
    "AssistHit",
    "Entry",
    "ScheduleInfo",
    "Hit",
    "Isa",
    "SPELLED",
    "Table",
    "load",
    "lookup",
    "reverse",
]

#: The element types the table covers: the float lanes f64/f32 (full op coverage required), the
#: optional half-precision lane f16 (arithmetic subset, where the hardware has it), and the integer
#: lanes i64/i32 (the bitwise, shift and logical ops, and integer mod).
DTYPES = ("f64", "f32")
F16 = "f16"
INT_DTYPES = ("i64", "i32")
ALL_DTYPES = DTYPES + (F16,) + INT_DTYPES

#: The dtypes every ISA must fully cover.
REQUIRED_DTYPES = set(DTYPES) | set(INT_DTYPES)

#: Integer-lane ops: ``and``/``or``/``shl``/``shr``/``land``/``lor`` exist only under i64/i32; the rest of
#: INT_OPS also under the float dtypes, ``mod`` as fmod on f64/f32 only.
INT_ONLY_OPS = frozenset({"and", "or", "shl", "shr", "land", "lor"})
INT_OPS = INT_ONLY_OPS | {"mod", "add", "sub", "mul", "min", "max", "load", "store", "broadcast", "lt"}

#: The shipped table.
DEFAULT_PATH = pathlib.Path(__file__).parent / "intrinsics.toml"

#: Matrix ISA names that are another ISA under a compiler width knob: ``avx512_256`` is AVX-512 under
#: ``-mprefer-vector-width=256``, which steers only the autovectorizer (a sweep knob, not a target).
ALIASES = {"avx512_256": "avx512"}
#: Every ISA name a lookup error offers.
KNOWN_ISAS = "avx2, avx512, neon, sve (avx512_256 is a compiler width knob, not a target)"

#: An fma family form as the assembler prints it: ``vfnmadd231pd`` -> mnemonic ``vfnmadd``, dtype f64.
FMA_FORM = re.compile(r"^(vfn?m(?:add|sub))(?:132|213|231)?[ps]([dsh])$")
#: The last letter of an fma form -> its dtype.
FMA_DTYPE = {"d": "f64", "s": "f32", "h": "f16"}

#: A disassembler may suffix a mnemonic with flags (an EVEX ``vaddpd.z``); no mnemonic in the table
#: contains a dot, so the part before it is the mnemonic.
DOT_SUFFIX = re.compile(r"^([a-z0-9]+)\.[a-z]+$")

#: An intrinsic named anywhere in free text: a bare recipe step, or a prose step or masked note citing one.
SPELLED = re.compile(r"\b(?:_mm\d*_\w+|sv[a-z0-9]+(?:_[a-z0-9]+)+|v[a-z0-9]+(?:_[a-z0-9]+)+)\b")

#: SVE activity suffixes and AVX-512 masked forms that spell the same op as the row's ``_x`` or ``_mask_`` form.
SVE_POLICY = re.compile(r"^(sv\w+)_[mz]$")
AVX512_MASKED = re.compile(r"^(_mm\d*)_(?:maskz|mask3)_(\w+)$")

#: Bytes per lane, the invariant between an ISA's width and its lane counts.
LANE_BYTES = {"f64": 8, "f32": 4, "f16": 2, "i64": 8, "i32": 4}


@dataclass(slots=True, frozen=True, config=TABLE)
class Entry:
    """One op spelling: the C intrinsic (when one instruction exists) or a composite ``recipe``, the
    assembly mnemonic for reading disassembly, the C ``signature``, the lane ``semantics``, an optional
    ``masked`` variant (mask/predication-capable ISAs), and a ``note`` for the traps (operand order).
    ``observed`` lists further mnemonics compilers print for the row, which reverse lookup reads back.

    Transcendentals (no native instruction on the covered ISAs) carry no intrinsic and no recipe but a
    list of ``approximations`` — keys into :attr:`Table.approx`, polynomial tiers with measured ULP
    error — and ``libraries``, the vector math library call per veclib (libmvec/SVML/SLEEF/ArmPL)."""

    mnemonic: str = ""
    intrinsic: str = ""
    masked: str = ""
    observed: Strings = ()
    signature: str = ""
    semantics: str = ""
    recipe: Strings = ()
    note: str = ""
    approximations: Strings = ()
    libraries: dict[str, str] = dataclasses.field(default_factory=dict)


@dataclass(slots=True, frozen=True, config=TABLE)
class Approx:
    """One polynomial tier of a transcendental: the ``domain`` it is valid on (after the range
    reduction it assumes), the measured ``error_ulp`` and ``error_abs``, and the Horner ``recipe`` in
    abstract-op steps (fma/mul with inline coefficients) — the copyable implementation."""

    op: str
    domain: str
    error_ulp: float
    recipe: Strings
    error_abs: float = 0.0
    note: str = ""


@dataclass(slots=True, frozen=True, config=TABLE)
class Assist:
    """A hardware assist the survey surfaced but that is not an abstract op: a single intrinsic that
    helps implement one (the `helps` op), with the
    assembly mnemonic for reading disassembly and a note on what it does. ``helps`` is an abstract op."""

    name: str
    mnemonic: str
    helps: str
    note: str


@dataclass(slots=True, frozen=True, config=TABLE)
class ScheduleInfo:
    """One loop schedule: what it is and how it handles the tail (the vectorizer knob it maps to in
    the matrix's ``[tails]``; ``scalar`` and ``scalar_remainder`` keep the remainder a scalar loop,
    ``masked_remainder`` masks only the epilogue, ``full_mask`` masks every iteration, and
    ``sve_intrinsics`` renders explicit predicated SVE loops)."""

    title: str
    description: str
    tail: str
    gcc: str = ""
    clang: str = ""


@dataclass(slots=True, frozen=True, config=TABLE)
class Isa:
    """One vector ISA: its machine model (vector width, lanes per dtype, mask capability, legal loop
    schedules, the ``gen_mask`` spelling) and the op table per dtype. ``vector_bytes`` 0 and ``lanes``
    0 mean length-agnostic (SVE: the runtime ``svcntd()``). f64/f32 and i64/i32 carry every op the
    abstract ISA defines; f16 is optional, holds the arithmetic subset, and records AVX2's convert-to-
    f32 emulation as recipes. ``embedded_broadcast`` marks ISAs (AVX-512 EVEX) where a scalar operand
    fuses into an arithmetic instruction as a broadcast memory operand."""

    title: str
    vector_bytes: int
    lanes: dict[str, int]
    mask: bool
    schedules: Strings
    f64: dict[str, Entry]
    f32: dict[str, Entry]
    gen_mask: str = ""
    note: str = ""
    i64: dict[str, Entry] = dataclasses.field(default_factory=dict)
    i32: dict[str, Entry] = dataclasses.field(default_factory=dict)
    f16: dict[str, Entry] = dataclasses.field(default_factory=dict)
    embedded_broadcast: bool = False
    assists: tuple[Assist, ...] = ()

    def entries(self, dtype: str) -> dict[str, Entry]:
        """The op table of ``dtype``."""
        return {"f64": self.f64, "f32": self.f32, "f16": self.f16, "i64": self.i64, "i32": self.i32}[dtype]


@dataclasses.dataclass(slots=True, frozen=True)
class AssistHit:
    """One reverse-lookup match over the assists: ``name`` is ``assist`` on ``isa``."""

    isa: str
    assist: Assist


@dataclasses.dataclass(slots=True, frozen=True)
class Hit:
    """One reverse-lookup match: ``name`` spelled ``entry`` on ``isa``/``dtype`` as abstract ``op``, reached via the
    intrinsic, a recipe step, the mnemonic, or ``step``: one mnemonic of a composite, not the op's whole math."""

    isa: str
    dtype: str
    op: str
    entry: Entry
    via: str


@dataclasses.dataclass(slots=True, frozen=True)
class Table:
    """The parsed table and both indexes: ISAs, the shared approximation tiers, the schedule
    metadata, and the reverse maps."""

    isas: dict[str, Isa]
    approx: dict[str, Approx]
    schedule_info: dict[str, ScheduleInfo]
    by_intrinsic: dict[str, tuple[Hit, ...]]
    by_mnemonic: dict[str, tuple[Hit, ...]]
    by_part: dict[str, tuple[Hit, ...]]
    by_assist: dict[str, tuple[AssistHit, ...]]

    def isa(self, name: str) -> Isa:
        """``name``'s ISA (aliases resolved), or ``KeyError`` naming the known ISAs."""
        key = ALIASES.get(name, name)
        try:
            return self.isas[key]
        except KeyError:
            raise KeyError(f"{name!r}: unknown ISA{suggestion(name, self.isas)} (one of: {KNOWN_ISAS})") from None

    def entry(self, isa: str, op: str, dtype: str) -> Entry:
        """The ``(isa, op, dtype)`` entry, or ``KeyError`` naming what is unknown or unsupported."""
        target = self.isa(isa)
        if op not in OPS:
            raise KeyError(f"{op!r}: unknown op{suggestion(op, OPS)} (one of: {', '.join(OPS)})")
        if dtype not in ALL_DTYPES:
            raise KeyError(f"{dtype!r}: unknown dtype{suggestion(dtype, ALL_DTYPES)} (one of: {', '.join(ALL_DTYPES)})")
        if dtype in DTYPES and op in INT_ONLY_OPS:
            raise KeyError(f"{isa}/{dtype}/{op}: integer op (look under i64/i32)")
        entries = target.entries(dtype)
        if op not in entries:
            why = f"no predication on {isa}" if op == "gen_mask" and not target.mask else f"no {isa}/{dtype} row"
            raise KeyError(f"{isa}/{dtype}/{op}: unsupported ({why}); float rows are not valid for integer lanes")
        return entries[op]

    def reverse(self, name: str) -> tuple[Hit, ...]:
        """Every ``(isa, op, dtype)`` an intrinsic, mnemonic or library call spells, or an empty tuple.

        Accepts a C intrinsic (``_mm256_add_pd``), a composite recipe step, a vector math library call
        (``_ZGVdN4v_sin``, ``_mm512_exp_pd``), or a mnemonic as a disassembler prints it (``vaddpd``,
        ``vfmadd231pd``, ``fmla``, ``ld1d``, a ``.z``-suffixed EVEX form, any letter case). A mnemonic that
        is only one step of a composite (``vfnmadd231pd`` in fmod) matches the composite."""
        token = normalized(name)
        if hits := self.by_intrinsic.get(token) or self.by_intrinsic.get(masked_form(token)):
            return hits
        token = token.lower()
        if (m := FMA_FORM.match(token)) is not None:
            return tuple(h for h in self.mnemonic_hits(m.group(1)) if h.dtype == FMA_DTYPE[m.group(2)])
        return self.mnemonic_hits(token)

    def mnemonic_hits(self, token: str) -> tuple[Hit, ...]:
        """The rows a mnemonic spells whole, then those it is one step of."""
        whole = self.by_mnemonic.get(token, ())
        seen = {(h.isa, h.dtype, h.op) for h in whole}
        return whole + tuple(h for h in self.by_part.get(token, ()) if (h.isa, h.dtype, h.op) not in seen)

    def assist(self, name: str) -> tuple[AssistHit, ...]:
        """Every assist an intrinsic or mnemonic names (e.g. ``_mm512_scalef_pd``, ``svexpa_f64``,
        ``vreducepd``), or an empty tuple."""
        token = normalized(name)
        return self.by_assist.get(token) or self.by_assist.get(token.lower(), ())


def suggestion(name: str, known: Iterable[str]) -> str:
    """`` (did you mean x?)`` for the closest of ``known``, or nothing."""
    close = difflib.get_close_matches(name, list(known), n=1)
    return f" (did you mean {close[0]}?)" if close else ""


def normalized(name: str) -> str:
    """The first word of a disassembly line or a name: operands, a comma and an EVEX ``.z`` suffix dropped."""
    words = name.strip().split(maxsplit=1)
    token = words[0].split(",", 1)[0] if words else ""
    m = DOT_SUFFIX.match(token.lower())
    return m.group(1) if m is not None else token


def masked_form(token: str) -> str:
    """The name the table indexes for a policy variant: ``svmla_f64_m`` -> ``svmla_f64_x``, ``_mm512_maskz_add_pd``
    -> ``_mm512_mask_add_pd``."""
    if (m := SVE_POLICY.match(token)) is not None:
        return f"{m.group(1)}_x"
    if (m := AVX512_MASKED.match(token)) is not None:
        return f"{m.group(1)}_mask_{m.group(2)}"
    return token


def assist_hits(isas: dict[str, Isa]) -> dict[str, tuple[AssistHit, ...]]:
    """The reverse index over the assists, by intrinsic name and by mnemonic."""
    index: dict[str, list[AssistHit]] = {}
    for isa_name, isa in isas.items():
        for assist in isa.assists:
            index.setdefault(assist.name, []).append(AssistHit(isa_name, assist))
            index.setdefault(assist.mnemonic, []).append(AssistHit(isa_name, assist))
    return {key: tuple(hits) for key, hits in index.items()}


def mnemonic_parts(mnemonic: str) -> list[str]:
    """The real mnemonics of a composite: ``vdivpd+vroundpd+vfnmadd`` splits, ``ld1d (gather)`` keeps its
    first word, the placeholders ``op`` and ``...`` are dropped."""
    words = [part.split(maxsplit=1)[0] for part in mnemonic.split("+") if part.strip()]
    return [word for word in words if word not in ("op", "...")]


def entry_hits(isas: dict[str, Isa]) -> tuple[dict[str, tuple[Hit, ...]], ...]:
    """The reverse indexes over every entry: by intrinsic (and recipe step), by mnemonic, and by the
    mnemonics inside a composite."""
    by_intrinsic: dict[str, list[Hit]] = {}
    by_mnemonic: dict[str, list[Hit]] = {}
    by_part: dict[str, list[Hit]] = {}
    for isa_name, isa in isas.items():
        for dtype in ALL_DTYPES:
            for op, entry in isa.entries(dtype).items():
                if entry.intrinsic:
                    by_intrinsic.setdefault(entry.intrinsic, []).append(Hit(isa_name, dtype, op, entry, "intrinsic"))
                for name in dict.fromkeys(SPELLED.findall(entry.masked)):
                    by_intrinsic.setdefault(name, []).append(Hit(isa_name, dtype, op, entry, "masked"))
                for name in dict.fromkeys(name for step in entry.recipe for name in SPELLED.findall(step)):
                    by_intrinsic.setdefault(name, []).append(Hit(isa_name, dtype, op, entry, "recipe"))
                for call in entry.libraries.values():
                    by_intrinsic.setdefault(call, []).append(Hit(isa_name, dtype, op, entry, "library"))
                if entry.mnemonic:
                    by_mnemonic.setdefault(entry.mnemonic, []).append(Hit(isa_name, dtype, op, entry, "mnemonic"))
                    for part in dict.fromkeys(mnemonic_parts(entry.mnemonic)):
                        by_part.setdefault(part, []).append(Hit(isa_name, dtype, op, entry, "step"))
                for name in entry.observed:
                    by_mnemonic.setdefault(name, []).append(Hit(isa_name, dtype, op, entry, "mnemonic"))
    return tuple({key: tuple(hits) for key, hits in index.items()} for index in (by_intrinsic, by_mnemonic, by_part))


def checked_float_entry(where: str, op: str, entry: Entry, approx: dict[str, Approx]) -> None:
    """A float row's shape: a transcendental cites tiers, every other op spells itself."""
    if OPS[op].kind != "transcendental":
        checked_spelling(where, entry)
        return
    if entry.intrinsic or entry.recipe:
        raise ValueError(f"{where} is a transcendental: no intrinsic/recipe")
    if not entry.approximations:
        raise ValueError(f"{where} lists no approximations")
    for key in entry.approximations:
        if key not in approx:
            raise ValueError(f"{where} cites unknown [approx.{key}]")
        if approx[key].op != op:
            raise ValueError(f"{where}: [approx.{key}].op is {approx[key].op!r}, not {op!r}")


def checked_spelling(where: str, entry: Entry) -> None:
    """A spelled row has exactly one of intrinsic and recipe, and a mnemonic."""
    if bool(entry.intrinsic) == bool(entry.recipe):
        raise ValueError(f"{where} sets exactly one of intrinsic, recipe")
    if not entry.mnemonic:
        raise ValueError(f"{where} has no mnemonic")


def checked_entry(where: str, op: str, entry: Entry, integer: bool, isa: Isa, approx: dict[str, Approx]) -> None:
    """One row against its op and its ISA."""
    if op not in OPS:
        raise ValueError(f"{where} is not an abstract op")
    if entry.approximations and OPS[op].kind != "transcendental":
        raise ValueError(f"{where} cites tiers but is no transcendental")
    if integer:
        if entry.approximations or entry.libraries:
            raise ValueError(f"{where} carries float-only fields")
        checked_spelling(where, entry)
    else:
        checked_float_entry(where, op, entry, approx)
    if entry.masked and not isa.mask:
        raise ValueError(f"{where}.masked on a maskless ISA")


def checked_tiers(approx: dict[str, Approx], path: pathlib.Path) -> None:
    """Every tier names an abstract op and carries a recipe, a domain and finite positive errors."""
    for name, tier in approx.items():
        if tier.op not in OPS:
            raise ValueError(f"{path}: [approx.{name}].op {tier.op!r} is not an abstract op")
        if not tier.recipe:
            raise ValueError(f"{path}: [approx.{name}] has an empty recipe")
        if not tier.domain or not (math.isfinite(tier.error_ulp) and tier.error_ulp > 0):
            raise ValueError(f"{path}: [approx.{name}] needs a domain and a positive error_ulp")
        if not (math.isfinite(tier.error_abs) and tier.error_abs >= 0):
            raise ValueError(f"{path}: [approx.{name}] needs a finite error_abs")


def checked_machine(isa_name: str, isa: Isa, schedules: dict[str, ScheduleInfo], path: pathlib.Path) -> None:
    """The ISA's machine model: schedules, masks, widths and lanes agree."""
    where = f"{path}: [isa.{isa_name}]"
    unknown = [s for s in isa.schedules if s not in schedules]
    if unknown:
        raise ValueError(f"{where}.schedules cites unknown [schedules] {unknown}")
    if "scalar" not in isa.schedules or len(set(isa.schedules)) != len(isa.schedules):
        raise ValueError(f"{where}.schedules must list scalar and no duplicates")
    if not isa.mask and ({"masked_remainder", "full_mask", "sve_intrinsics"} & set(isa.schedules) or isa.gen_mask):
        raise ValueError(f"{where} has no mask, so no masked schedule and no gen_mask")
    if isa.mask and not isa.gen_mask:
        raise ValueError(f"{where} has masks but no gen_mask spelling")
    lanes = set(REQUIRED_DTYPES) | ({F16} if isa.f16 else set())
    if set(isa.lanes) != lanes:
        raise ValueError(f"{where}.lanes must cover {sorted(lanes)}")
    if isa.vector_bytes < 0 or any(isa.lanes[d] * LANE_BYTES[d] != isa.vector_bytes for d in lanes):
        raise ValueError(f"{where}.lanes disagree with vector_bytes {isa.vector_bytes}")
    for assist in isa.assists:
        if not assist.name or assist.helps not in OPS:
            raise ValueError(f"{path}: assist {assist.name!r} helps {assist.helps!r}, not an abstract op")


def checked_coverage(isa_name: str, isa: Isa, dtype: str, path: pathlib.Path) -> None:
    """The ops ``dtype``'s table must hold; f16 is optional and holds a subset."""
    entries = isa.entries(dtype)
    where = f"{path}: [isa.{isa_name}.{dtype}]"
    if not entries and dtype in REQUIRED_DTYPES:
        raise ValueError(f"{where} is empty")
    if dtype in DTYPES:
        missing = [
            op for op in OPS if op not in INT_ONLY_OPS and op not in entries and not (op == "gen_mask" and not isa.mask)
        ]
        if missing:
            raise ValueError(f"{where} lacks ops {missing}")
    elif dtype in INT_DTYPES and (missing := sorted(INT_OPS - set(entries))):
        raise ValueError(f"{where} lacks ops {missing}")


def checked(
    parsed: dict[str, Isa], approx: dict[str, Approx], schedules: dict[str, ScheduleInfo], path: pathlib.Path
) -> dict[str, Isa]:
    """The invariants every ISA table must hold, or ``ValueError`` naming the broken one."""
    checked_tiers(approx, path)
    for isa_name, isa in parsed.items():
        checked_machine(isa_name, isa, schedules, path)
        for dtype in ALL_DTYPES:
            checked_coverage(isa_name, isa, dtype, path)
            for op, entry in isa.entries(dtype).items():
                where = f"{path}: [isa.{isa_name}.{dtype}.{op}]"
                checked_entry(where, op, entry, dtype in INT_DTYPES, isa, approx)
    return parsed


@functools.lru_cache(maxsize=1, typed=True)
def load(path: pathlib.Path = DEFAULT_PATH) -> Table:
    """The table of ``path`` (the shipped ``intrinsics.toml`` by default), validated and indexed."""
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    parsed = TypeAdapter(dict[str, Isa]).validate_python(data.get("isa", {}))
    approx = TypeAdapter(dict[str, Approx]).validate_python(data.get("approx", {}))
    schedules = TypeAdapter(dict[str, ScheduleInfo]).validate_python(data.get("schedules", {}))
    isas_map = checked(parsed, approx, schedules, path)
    by_intrinsic, by_mnemonic, by_part = entry_hits(isas_map)
    return Table(isas_map, approx, schedules, by_intrinsic, by_mnemonic, by_part, assist_hits(isas_map))


def lookup(isa: str, op: str, dtype: str, table: Table | None = None) -> Entry:
    """The ``(isa, op, dtype)`` entry: the spelling, signature, semantics and traps."""
    return (table or load()).entry(isa, op, dtype)


def reverse(name: str, table: Table | None = None) -> tuple[Hit, ...]:
    """Every ``(isa, op, dtype)`` the intrinsic or mnemonic ``name`` spells."""
    return (table or load()).reverse(name)
