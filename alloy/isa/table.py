# Copyright 2026 ETH Zurich and the Alloy authors.
"""The instruction lookup table: every abstract math op (:mod:`alloy.isa.ops`) spelled per ISA and dtype,
loaded from the checked-in ``intrinsics.toml`` and indexed in both directions — op -> intrinsic for
writing vector code, intrinsic or assembly mnemonic -> op for reading a build's source or disassembly
back into math."""

import dataclasses
import pathlib
import re
import tomllib

from pydantic import ConfigDict, TypeAdapter
from pydantic.dataclasses import dataclass

from alloy.isa.ops import OPS
from alloy.records import Strings

#: An empty library-name map.
NO_LIBRARIES: dict[str, str] = {}

#: Parsed-table records: every key required and typed, coercion allowed like configuration_matrix's
#: STRICT; the stricter invariants live in :func:`_checked`.
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
    "Entry",
    "ScheduleInfo",
    "Hit",
    "Isa",
    "Table",
    "isas",
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

#: Integer-lane ops: ``and``/``or``/``shl``/``shr``/``land``/``lor`` exist only under i64/i32; ``mod``
#: exists under all float dtypes (fmod) and both integer ones (truncated remainder).
INT_ONLY_OPS = frozenset({"and", "or", "shl", "shr", "land", "lor"})
INT_OPS = INT_ONLY_OPS | {"mod"}

#: The shipped table.
DEFAULT_PATH = pathlib.Path(__file__).parent / "intrinsics.toml"

#: Matrix ISA names that are another ISA at a different width: ``avx512_256`` is AVX-512 under
#: ``-mprefer-vector-width=256`` — same intrinsics, half the lanes (a sweep knob, not a target).
ALIASES = {"avx512_256": "avx512"}

#: An fma family form as the assembler prints it: ``vfmadd231pd`` -> mnemonic ``vfmadd``, dtype f64.
FMA_FORM = re.compile(r"^vf(m(?:add|sub|nmadd|nmsub))(?:132|213|231)?(pd|ps)$")

#: A disassembler may suffix a mnemonic with flags (an EVEX ``vaddpd.z``); no mnemonic in the table
#: contains a dot, so the part before it is the mnemonic.
DOT_SUFFIX = re.compile(r"^([a-z0-9]+)\.[a-z]+$")


@dataclass(slots=True, frozen=True, config=TABLE)
class Entry:
    """One op spelling: the C intrinsic (when one instruction exists) or a composite ``recipe``, the
    assembly mnemonic for reading disassembly, the C ``signature``, the lane ``semantics``, an optional
    ``masked`` variant (mask/predication-capable ISAs), and a ``note`` for the traps (operand order).

    Transcendentals (no native instruction on the covered ISAs) carry no intrinsic and no recipe but a
    list of ``approximations`` — keys into :attr:`Table.approx`, polynomial tiers with measured ULP
    error — and ``libraries``, the vector math library call per veclib (libmvec/SVML/SLEEF/ArmPL)."""

    mnemonic: str = ""
    intrinsic: str = ""
    masked: str = ""
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


@dataclasses.dataclass(slots=True, frozen=True)
class Hit:
    """One reverse-lookup match: ``name`` spelled ``entry`` on ``isa``/``dtype`` as abstract ``op``,
    reached via the intrinsic, a recipe step, or the mnemonic."""

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

    def isa(self, name: str) -> Isa:
        """``name``'s ISA (aliases resolved), or ``KeyError`` naming the known ISAs."""
        key = ALIASES.get(name, name)
        try:
            return self.isas[key]
        except KeyError:
            raise KeyError(f"{name!r}: unknown ISA (one of: {', '.join(sorted(self.isas))})") from None

    def entry(self, isa: str, op: str, dtype: str) -> Entry:
        """The ``(isa, op, dtype)`` entry, or ``KeyError`` naming what is unknown or unsupported."""
        target = self.isa(isa)
        if op not in OPS:
            raise KeyError(f"{op!r}: unknown op (one of: {', '.join(OPS)})")
        if dtype not in ALL_DTYPES:
            raise KeyError(f"{dtype!r}: unknown dtype (one of: {', '.join(ALL_DTYPES)})")
        if dtype in INT_DTYPES and op not in INT_OPS:
            raise KeyError(f"{isa}/{dtype}/{op}: {op} is a float op (look under f64/f32)")
        if dtype in DTYPES and op in INT_ONLY_OPS:
            raise KeyError(f"{isa}/{dtype}/{op}: integer op (look under i64/i32)")
        entries = getattr(target, dtype)
        if op not in entries:
            why = f"no predication on {isa}" if op == "gen_mask" else f"not in the {isa}/{dtype} table"
            raise KeyError(f"{isa}/{dtype}/{op}: unsupported ({why}); legal schedules: {', '.join(target.schedules)}")
        return entries[op]

    def reverse(self, name: str) -> tuple[Hit, ...]:
        """Every ``(isa, op, dtype)`` an intrinsic, mnemonic or library call spells, or an empty tuple.

        Accepts a C intrinsic (``_mm256_add_pd``), a composite recipe step, a vector math library call
        (``_ZGVcN4v_sin``, ``_mm512_exp_pd``), or a mnemonic as a disassembler prints it (``vaddpd``,
        ``vfmadd231pd``, ``fmla``, ``ld1d``, a ``.z``-suffixed EVEX form)."""
        token = name.strip().split(maxsplit=1)[0].split(",", 1)[0]
        if hits := self.by_intrinsic.get(token, ()):
            return hits
        if (m := DOT_SUFFIX.match(token)) is not None:
            token = m.group(1)
        if (m := FMA_FORM.match(token)) is not None:
            mnemonic, dtype = "vf" + m.group(1), "f64" if m.group(2) == "pd" else "f32"
            return tuple(h for h in self.by_mnemonic.get(mnemonic, ()) if h.dtype == dtype)
        return self.by_mnemonic.get(token, ())


def _hits(isas: dict[str, Isa]) -> tuple[dict[str, tuple[Hit, ...]], dict[str, tuple[Hit, ...]]]:
    """The reverse indexes over every entry: by intrinsic (and recipe step) and by mnemonic."""
    by_intrinsic: dict[str, list[Hit]] = {}
    by_mnemonic: dict[str, list[Hit]] = {}
    for isa_name, isa in isas.items():
        for dtype in ALL_DTYPES:
            for op, entry in getattr(isa, dtype).items():
                if entry.intrinsic:
                    by_intrinsic.setdefault(entry.intrinsic, []).append(Hit(isa_name, dtype, op, entry, "intrinsic"))
                if entry.masked:
                    name = entry.masked.split("(", 1)[0]
                    by_intrinsic.setdefault(name, []).append(Hit(isa_name, dtype, op, entry, "masked"))
                for step in entry.recipe:
                    by_intrinsic.setdefault(step, []).append(Hit(isa_name, dtype, op, entry, "recipe"))
                for call in entry.libraries.values():
                    by_intrinsic.setdefault(call, []).append(Hit(isa_name, dtype, op, entry, "library"))
                if entry.mnemonic:
                    by_mnemonic.setdefault(entry.mnemonic, []).append(Hit(isa_name, dtype, op, entry, "mnemonic"))
    return (
        {key: tuple(hits) for key, hits in by_intrinsic.items()},
        {key: tuple(hits) for key, hits in by_mnemonic.items()},
    )


def _checked(
    parsed: dict[str, Isa], approx: dict[str, Approx], schedules: dict[str, ScheduleInfo], path: pathlib.Path
) -> dict[str, Isa]:
    """The invariants every ISA table must hold, or ``ValueError`` naming the broken one.

    f64/f32 and i64/i32 must cover the full op set; f16 is optional and carries the arithmetic
    subset on ISAs that have it (AVX2 emulates through f32 conversions — its f16 entries are
    recipes, which is the table's fallback story)."""

    def entry_ok(isa_name: str, dtype: str, op: str, entry: Entry, integer: bool) -> None:
        if op not in OPS:
            raise ValueError(f"{path}: [isa.{isa_name}.{dtype}.{op}] is not an abstract op")
        if integer:
            if op not in INT_OPS:
                raise ValueError(f"{path}: [isa.{isa_name}.{dtype}.{op}] is not an integer op ({sorted(INT_OPS)})")
            if entry.masked or entry.approximations or entry.libraries:
                raise ValueError(f"{path}: [isa.{isa_name}.{dtype}.{op}] carries float-only fields")
        elif OPS[op].kind == "transcendental":
            if entry.intrinsic or entry.recipe:
                raise ValueError(f"{path}: [isa.{isa_name}.{dtype}.{op}] is a transcendental: no intrinsic/recipe")
            if not entry.approximations:
                raise ValueError(f"{path}: [isa.{isa_name}.{dtype}.{op}] lists no approximations")
            for key in entry.approximations:
                if key not in approx:
                    raise ValueError(f"{path}: [isa.{isa_name}.{dtype}.{op}] cites unknown [approx.{key}]")
                if approx[key].op != op:
                    raise ValueError(f"{path}: [approx.{key}].op is {approx[key].op!r}, not {op!r}")
        else:
            if bool(entry.intrinsic) == bool(entry.recipe):
                raise ValueError(f"{path}: [isa.{isa_name}.{dtype}.{op}] sets exactly one of intrinsic, recipe")
            if not entry.mnemonic:
                raise ValueError(f"{path}: [isa.{isa_name}.{dtype}.{op}] has no mnemonic")
        if entry.masked and not isa.mask:
            raise ValueError(f"{path}: [isa.{isa_name}.{dtype}.{op}].masked on a maskless ISA")

    for name, tier in approx.items():
        if not tier.recipe:
            raise ValueError(f"{path}: [approx.{name}] has an empty recipe")
        if not tier.domain or tier.error_ulp <= 0:
            raise ValueError(f"{path}: [approx.{name}] needs a domain and a positive error_ulp")
    for isa_name, isa in parsed.items():
        unknown = [s for s in isa.schedules if s not in schedules]
        if unknown:
            raise ValueError(f"{path}: [isa.{isa_name}].schedules cites unknown [schedules] {unknown}")
        lanes = set(REQUIRED_DTYPES) | ({F16} if isa.f16 else set())
        if set(isa.lanes) != lanes:
            raise ValueError(f"{path}: [isa.{isa_name}].lanes must cover {sorted(lanes)}")
        for dtype in ALL_DTYPES:
            entries = getattr(isa, dtype)
            integer = dtype in INT_DTYPES
            if not entries:
                if dtype in REQUIRED_DTYPES:
                    raise ValueError(f"{path}: [isa.{isa_name}.{dtype}] is empty")
                continue  # optional dtype tables (f16) may be absent
            if dtype in DTYPES:  # full float coverage with the gen_mask exemption
                missing = [
                    op
                    for op in OPS
                    if op not in INT_ONLY_OPS and op not in entries and not (op == "gen_mask" and not isa.mask)
                ]
                if missing:
                    raise ValueError(f"{path}: [isa.{isa_name}.{dtype}] lacks ops {missing}")
                if isa.mask and "gen_mask" not in entries:
                    raise ValueError(f"{path}: [isa.{isa_name}.{dtype}] has masks but no gen_mask entry")
            for op, entry in entries.items():
                entry_ok(isa_name, dtype, op, entry, integer)
        if isa.mask and not isa.gen_mask:
            raise ValueError(f"{path}: [isa.{isa_name}] has masks but no gen_mask spelling")
    return parsed


def load(path: pathlib.Path = DEFAULT_PATH) -> Table:
    """The table of ``path`` (the shipped ``intrinsics.toml`` by default), validated and indexed."""
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    parsed = TypeAdapter(dict[str, Isa]).validate_python(data["isa"])
    approx = TypeAdapter(dict[str, Approx]).validate_python(data.get("approx", {}))
    schedules = TypeAdapter(dict[str, ScheduleInfo]).validate_python(data.get("schedules", {}))
    isas_map = _checked(parsed, approx, schedules, path)
    by_intrinsic, by_intrinsic_m = _hits(isas_map)
    return Table(isas_map, approx, schedules, by_intrinsic, by_intrinsic_m)


def isas(table: Table | None = None) -> tuple[str, ...]:
    """The ISA names the table covers (aliases not included)."""
    return tuple((table or load()).isas)


def lookup(isa: str, op: str, dtype: str, table: Table | None = None) -> Entry:
    """The ``(isa, op, dtype)`` entry: the spelling, signature, semantics and traps."""
    return (table or load()).entry(isa, op, dtype)


def reverse(name: str, table: Table | None = None) -> tuple[Hit, ...]:
    """Every ``(isa, op, dtype)`` the intrinsic or mnemonic ``name`` spells."""
    return (table or load()).reverse(name)
