# Copyright 2026 ETH Zurich and the Alloy authors.
"""One abstract machine ISA (alloy-workspace notes/isa-design.md): a :class:`Request` names a target, an operation, and
its operands (memory space, element type, shape, layout, swizzle); :func:`ask` answers :class:`Feasible`, possibly
several instructions, :class:`Infeasible` (the target cannot: the reason and the nearest requests it takes), or
:class:`Invalid` (the request is wrong on every target: the reason and what a valid one has). Both carry a
:class:`Why` code.

Step 1 of the design: the answer comes from today's surfaces (the vector table, the math kernels, the SIMT rows, the
Tensix rows, and the tile plans), wrapped, so every existing answer keeps its content and its check.

    python -m alloy.isa ask sm90 mma --a shared:f16:64x64:row_major:b128 --b shared:f16:64x64:col_major:b128 \
        --c register:f32:64x64
"""

import dataclasses
import enum
from typing import Literal, get_args

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from alloy.isa import OPS, load, simt, tensix, tile
from alloy.isa.mathkernels import cheapest, functions, kernel, render, target_of

__all__ = [
    "TARGETS",
    "UNITS",
    "Answer",
    "Check",
    "Feasible",
    "Infeasible",
    "Invalid",
    "Operand",
    "Request",
    "Step",
    "Why",
    "ask",
]

STRICT = ConfigDict(extra="forbid", strict=True, frozen=True)
Space = Literal["register", "vector", "tile_register", "shared", "global", "constant"]
Layout = Literal["row_major", "col_major"]
Swizzle = Literal["none", "b32", "b64", "b128", "xor:8"]
SPACES, LAYOUTS, SWIZZLES = get_args(Space), get_args(Layout), get_args(Swizzle)

#: The targets and the units (implementations) each has.
UNITS: dict[str, tuple[str, ...]] = {
    "avx2": ("vector", "scalar"),
    "avx512": ("vector", "scalar"),
    "neon": ("vector", "scalar"),
    "sve": ("vector", "scalar"),
    "sme": ("streaming_vector", "za"),
    "sm90": ("thread", "warp", "warpgroup", "tma", "cp_async"),
    "gfx942": ("thread", "wave", "mfma", "lds_dma", "lds"),
    "tensix": ("sfpu", "fpu", "noc"),
}
TARGETS = tuple(UNITS)
CPU = ("avx2", "avx512", "neon", "sve")
#: The dialect of a GPU target's per-thread rows (simt.toml).
DIALECT = {"sm90": "cuda", "gfx942": "hip"}
#: The element type of a per-thread row that does not compute in f32.
SIMT_DTYPE = {"add_half2": "f16"}
#: Per tile target, what its mma kernel reads, exactly: the space of the inputs (a, b), their swizzle, the space of the
#: accumulator (c), and the layout of a, b, and c. A request that names anything else is infeasible, so an answer never
#: computes on a tile laid out differently from the one the caller holds. The GPU kernels read B with K contiguous
#: (col_major, that is Bt as N rows of K), and SME's outer products read A with K leading (col_major, At as K rows of M).
MMA_OPERANDS: dict[str, tuple[tuple[str, ...], str, tuple[str, ...], tuple[str, str, str]]] = {
    "cpu": (("global",), "none", ("global",), ("row_major", "row_major", "row_major")),
    "sme": (("global",), "none", ("tile_register", "global"), ("col_major", "row_major", "row_major")),
    "sm90": (("shared",), "b128", ("register", "tile_register"), ("row_major", "col_major", "row_major")),
    "gfx942": (("shared",), "xor:8", ("register", "tile_register"), ("row_major", "col_major", "row_major")),
    "tensix": (("tile_register",), "none", ("tile_register",), ("row_major", "row_major", "row_major")),
}  # fmt: skip
#: What a layout of an mma operand means in memory, for the refusal's reason.
MMA_LAYOUT = {
    ("a", "row_major"): "M rows of K", ("a", "col_major"): "At, K rows of M",
    ("b", "row_major"): "K rows of N", ("b", "col_major"): "Bt, N rows of K",
    ("c", "row_major"): "M rows of N", ("c", "col_major"): "Ct, N rows of M",
}  # fmt: skip
#: The (input, accumulator) element types each tile target's checked kernels take.
MMA_TYPES: dict[str, tuple[tuple[str, str], ...]] = {
    "cpu": tuple(tile.CPU_TYPES), "sme": (("f32", "f32"),), "sm90": (("f16", "f32"),), "gfx942": (("f16", "f32"),),
}  # fmt: skip


class Why(enum.StrEnum):
    """Why a request has no answer. The first group makes a request :class:`Invalid` (wrong on every target); the
    second makes it :class:`Infeasible` (well formed, and this target or unit cannot carry it out)."""

    TARGET = "unknown_target"
    UNIT_NAME = "unknown_unit"
    OPERATION = "unknown_operation"
    OPERANDS = "missing_operand"
    MALFORMED = "malformed_operand"
    CHAIN = "shapes_do_not_chain"
    MIXED_TYPES = "mixed_element_types"
    BOUND = "bound_not_applicable"

    UNIT = "unit_does_not_run_it"
    NO_ROW = "no_row"
    ELEMENT_TYPE = "element_type"
    SHAPE = "shape"
    SPACE = "space"
    SWIZZLE = "swizzle"
    LAYOUT = "layout"
    NO_RUNG = "no_rung_within_bound"
    NOT_COVERED = "not_covered"
    CHECK_FAILED = "check_failed"


#: The reasons of an invalid request; every other reason is an infeasible one.
INVALID = frozenset({Why.TARGET, Why.UNIT_NAME, Why.OPERATION, Why.OPERANDS, Why.MALFORMED, Why.CHAIN,
                     Why.MIXED_TYPES, Why.BOUND})  # fmt: skip


@dataclass(config=STRICT)
class Operand:
    """One operand: where it lives, its element type, its shape (``()`` a scalar, ``(lanes,)`` a vector, ``(rows,
    cols)`` a tile), its layout, its swizzle, and its alignment in bytes (0: the element's own)."""

    space: Space
    dtype: str
    shape: tuple[int, ...] = ()
    layout: Layout = "row_major"
    swizzle: Swizzle = "none"
    align: int = 0

    @classmethod
    def parse(cls, text: str) -> "Operand":
        """``space:dtype[:RxC or N][:layout][:swizzle]``, as the CLI spells it (``shared:f16:64x64:row_major:b128``);
        a malformed operand raises :class:`KeyError` with what is wrong."""
        parts = text.lower().split(":")
        if len(parts) < 2 or not parts[1]:
            raise KeyError(f"{text!r}: an operand is space:dtype[:shape][:layout][:swizzle]")
        if parts[0] not in SPACES:
            raise KeyError(f"{text!r}: no space {parts[0]!r}; one of {', '.join(SPACES)}")
        try:
            shape = tuple(int(n) for n in parts[2].split("x")) if len(parts) > 2 and parts[2] else ()
        except ValueError:
            raise KeyError(f"{text!r}: a shape is N or RxC, got {parts[2]!r}") from None
        if len(shape) > 2 or any(n <= 0 for n in shape):
            raise KeyError(f"{text!r}: a shape is one or two positive extents, got {parts[2]!r}")
        layout = parts[3] if len(parts) > 3 and parts[3] else "row_major"
        if layout not in LAYOUTS:
            hint = f"; a swizzle follows the layout: ...:row_major:{layout}" if layout in SWIZZLES else ""
            raise KeyError(f"{text!r}: no layout {layout!r}; one of {', '.join(LAYOUTS)}{hint}")
        swizzle = ":".join(parts[4:]) or "none"
        if swizzle not in SWIZZLES:
            raise KeyError(f"{text!r}: no swizzle {swizzle!r}; one of {', '.join(SWIZZLES)}")
        return cls(parts[0], parts[1], shape, layout, swizzle)  # type: ignore[arg-type]

    def spelled(self) -> str:
        """The operand as :meth:`parse` reads it."""
        text = f"{self.space}:{self.dtype}"
        if self.shape:
            text += ":" + "x".join(str(n) for n in self.shape)
        if (self.layout, self.swizzle) != ("row_major", "none"):
            text += f"{'' if self.shape else ':'}:{self.layout}"
        return text if self.swizzle == "none" else f"{text}:{self.swizzle}"


@dataclass(config=STRICT)
class Request:
    """A target, an operation, its operands by name, the unit the caller pins ("" lets Alloy choose), and an error
    bound for an approximated function."""

    target: str
    op: str
    operands: dict[str, Operand] = dataclasses.field(default_factory=dict)
    unit: str = ""
    max_ulp: float | None = None


@dataclass(config=STRICT)
class Step:
    """One instruction or call of an answer: the unit that runs it, its spelling, and how often a request runs it."""

    unit: str
    spelling: str
    count: int = 1


@dataclass(config=STRICT)
class Check:
    """How the answer was checked: ``run`` (matched a reference here), ``compiled``, or ``unverified``."""

    status: Literal["run", "compiled", "unverified"]
    basis: str = ""


@dataclass(config=STRICT)
class Feasible:
    """An implementation of the request: the unit chosen, its steps in order, the host-side setup it needs, code to
    copy, its check, and notes."""

    request: Request
    unit: str
    steps: tuple[Step, ...]
    setup: dict[str, str]
    code: str
    check: Check
    notes: tuple[str, ...] = ()
    feasible: Literal[True] = True
    status: Literal["feasible"] = "feasible"


@dataclass(config=STRICT)
class Infeasible:
    """A well-formed request that no unit of the target carries out: the reason's code, the reason, and what the
    target does take (operands as ``name space:dtype:shape[:layout[:swizzle]]``, comma-separated, or ``unit <name>``).
    ``fix`` says how the caller gets from what it has to a nearest request (a load that swizzles, a transposed
    store), where Alloy knows one."""

    request: Request
    why: Why
    reason: str
    nearest: tuple[str, ...] = ()
    fix: str = ""
    feasible: Literal[False] = False
    status: Literal["infeasible"] = "infeasible"


@dataclass(config=STRICT)
class Invalid:
    """A request that is wrong on every target (an unknown name, a missing or malformed operand, shapes that do not
    chain, mixed element types, a bound on an exact operation): the reason's code, the reason, and what a valid
    request has in its place. ``request`` is None when an operand did not parse."""

    request: Request | None
    why: Why
    reason: str
    expected: tuple[str, ...] = ()
    feasible: Literal[False] = False
    status: Literal["invalid"] = "invalid"


Answer = Feasible | Infeasible | Invalid


def no(request: Request, why: Why, reason: str, *nearest: str, fix: str = "") -> Infeasible:
    assert why not in INVALID, why
    return Infeasible(request, why, reason, tuple(nearest), fix)


def bad(request: Request | None, why: Why, reason: str, *expected: str) -> Invalid:
    assert why in INVALID, why
    return Invalid(request, why, reason, tuple(expected))


def spell(**operands: Operand) -> str:
    """Operands as a nearest request names them: ``a shared:f16:64x64, b ...``."""
    return ", ".join(f"{name} {operand.spelled()}" for name, operand in operands.items())


def ask(request: Request, verify: bool = True) -> Answer:
    """The answer to ``request``; ``verify`` runs the check the surface has (on the host, ttsim's record, a compile).
    A pinned unit that does not run the operation is infeasible, with the unit that does."""
    answer = answered(request, verify)
    if isinstance(answer, Feasible) and request.unit and answer.unit != request.unit:
        reason = f"{request.target} {request.op} runs on {answer.unit}, not {request.unit}"
        return no(request, Why.UNIT, reason, f"unit {answer.unit}")
    return answer


def answered(request: Request, verify: bool) -> Answer:
    if request.target not in UNITS:
        return bad(request, Why.TARGET, f"no target {request.target!r}", *(f"target {t}" for t in TARGETS))
    if request.unit and request.unit not in UNITS[request.target]:
        units = (f"unit {u}" for u in UNITS[request.target])
        return bad(request, Why.UNIT_NAME, f"{request.target} has no unit {request.unit!r}", *units)
    if request.op == "mma":
        return mma(request, verify)
    if request.op == "copy":
        return copy(request)
    if request.target in DIALECT:
        return thread_op(request)
    if request.op not in OPS and request.op not in functions():
        return bad(
            request, Why.OPERATION, f"no operation {request.op!r}", "an op of `python -m alloy.isa ops`, mma, or copy"
        )
    if request.max_ulp is not None and (request.op not in functions() or request.target == "tensix"):
        what = "a Tensix tile call has one accuracy" if request.target == "tensix" else f"{request.op} is exact"
        return bad(
            request, Why.BOUND, f"max_ulp selects a rung of a math kernel; {what}", "the request without max_ulp"
        )
    if request.target in CPU:
        return vector_op(request, verify)
    if request.target == "tensix":
        return tile_call(request)
    nearest = mma_nearest("sme", 32, 32, 32)
    return no(request, Why.NOT_COVERED, "sme answers mma only so far (step 3 of the design)", *nearest)


def dtype_of(request: Request) -> str:
    """The element type the request computes in: its first operand's, else f64."""
    return next((o.dtype for o in request.operands.values()), "f64")


def mixed(request: Request) -> str:
    """Why the operands of an elementwise request do not agree on one element type, or ""."""
    dtypes = sorted({o.dtype for o in request.operands.values()})
    return (
        f"the operands mix {', '.join(dtypes)}; an elementwise operation computes in one type"
        if len(dtypes) > 1
        else ""
    )


def vector_op(request: Request, verify: bool) -> Answer:
    """A CPU operation: the table's row, or the math kernel at the cheapest rung that holds ``max_ulp`` (the strict
    rung where the table has the function without an instruction)."""
    dtype, isa = dtype_of(request), request.target
    table = load()
    lanes = table.isa(isa).lanes.get(dtype, 0)
    register = Operand("vector", dtype, (lanes,) if lanes else ())
    if not request.operands:
        return bad(
            request, Why.OPERANDS, f"{request.op} needs an operand: it names the element type", spell(x=register)
        )
    if why := mixed(request):
        return bad(request, Why.MIXED_TYPES, why, spell(x=register))
    for operand in request.operands.values():
        if operand.space not in ("vector", "register"):
            fix = f"load it first: ask copy with src global and dst {register.spelled()}"
            return no(request, Why.SPACE, f"{isa} {request.op} computes on registers, not on {operand.space} memory",
                      spell(x=register), fix=fix)  # fmt: skip
        if operand.swizzle != "none":
            return no(request, Why.SWIZZLE, "a CPU has no swizzle", spell(x=register))
        if len(operand.shape) == 2:
            return no(request, Why.SHAPE, f"{request.op} is elementwise: one register per operand; a tile is an mma or copy operand",
                      spell(x=register))  # fmt: skip
        if lanes and operand.shape and operand.shape != (lanes,):
            return no(
                request,
                Why.SHAPE,
                f"an {isa} register holds {lanes} {dtype} lanes, not {operand.shape[0]}",
                spell(x=register),
            )
    if request.op in functions() and (request.op not in OPS or request.max_ulp is not None):
        return math_kernel(request, isa, dtype)
    try:
        entry = table.entry(isa, request.op, dtype)
    except KeyError as exc:
        others = (Operand("vector", d, (n,) if n else ()) for d, n in table.isa(isa).lanes.items() if d != dtype)
        return no(request, Why.NO_ROW, str(exc.args[0]), *(spell(x=o) for o in others))
    if not entry.intrinsic and not entry.recipe:
        if request.op in functions():
            return math_kernel(request, isa, dtype)
        return no(request, Why.NO_ROW, f"{isa} has no instruction or recipe for {request.op} on {dtype}")
    steps = (Step("vector", entry.intrinsic),) if entry.intrinsic else tuple(Step("vector", s) for s in entry.recipe)
    check = Check("unverified")
    if verify:
        from alloy.isa.validate import validate

        verdict = validate(isa, request.op, dtype, table)
        if verdict.ok is False:
            return no(request, Why.CHECK_FAILED, f"the row failed its check: {verdict.detail}")
        check = Check("run" if verdict.ok else "unverified", verdict.basis)
    code = "\n".join(entry.code) or f"{entry.intrinsic}  /* {entry.signature} */"
    return Feasible(request, "vector", steps, {}, code, check, (entry.note,) if entry.note else ())


def math_kernel(request: Request, isa: str, dtype: str) -> Answer:
    """The rung of the function with the fewest intrinsics within ``max_ulp`` (the strict rung without a bound)."""
    try:
        if request.max_ulp is None:
            spelled = render(kernel(request.op, dtype, "strict"), target_of(isa))
        else:
            spelled = cheapest(request.op, dtype, target_of(isa), max_ulp=request.max_ulp)
    except KeyError as exc:
        return no(request, Why.NO_RUNG, str(exc.args[0]))
    k = spelled.kernel
    notes = (f"rung {k.level}: {k.error_ulp:.4g} ulp, {spelled.intrinsics} intrinsics, contract: {k.contract}",)
    return Feasible(request, "vector", (Step("vector", k.name),), {}, spelled.source,
                    Check("unverified", "math kernels are checked by `kernel` and `validate`"), notes)  # fmt: skip


def thread_op(request: Request) -> Answer:
    """A GPU operation of one thread or one warp: its SIMT row on scalars, with the recorded check."""
    dialect = DIALECT[request.target]
    rows = {r.op: r for r in simt.rows()}
    if request.op not in rows:
        return no(request, Why.NO_ROW, f"no {dialect} row for {request.op}", *(f"{request.target} {op}" for op in rows))
    row, verdict = rows[request.op], simt.verdicts().get((request.op, dialect))
    scalar = Operand("register", SIMT_DTYPE.get(request.op, "f32"))
    for operand in request.operands.values():
        if operand.dtype != scalar.dtype:
            return no(
                request,
                Why.ELEMENT_TYPE,
                f"the {request.op} row computes in {scalar.dtype}, not {operand.dtype}",
                spell(x=scalar),
            )
        if len(operand.shape) == 2 or operand.swizzle != "none":
            return no(request, Why.SHAPE, f"{request.op} is a row of one thread on scalars; a tile is an mma or copy operand",
                      spell(x=scalar))  # fmt: skip
    if request.max_ulp is not None:
        return bad(request, Why.BOUND, "max_ulp selects a rung of a math kernel; a device row has one accuracy",
                  "the request without max_ulp")  # fmt: skip
    if verdict is not None and verdict.ok is False:
        return no(request, Why.CHECK_FAILED, f"the row failed its check: {verdict.error or verdict.basis}")
    spelling = row.spelled(dialect)
    check = Check("unverified") if verdict is None else Check("run" if verdict.ok else "compiled", verdict.basis)
    unit = "warp" if row.kind == "warp" else "thread"
    return Feasible(request, unit, (Step(unit, spelling),), {}, spelling, check, (row.note,) if row.note else ())


def tile_call(request: Request) -> Answer:
    """A Tensix operation on one 32 x 32 tile: its tile calls on the unit that has the operation, with ttsim's
    recorded check."""
    dtype = dtype_of(request)
    rows = [r for r in tensix.rows() if r.op == request.op]
    if not rows:
        return no(
            request, Why.NO_ROW, f"no Tensix row for {request.op}", *sorted({f"tensix {r.op}" for r in tensix.rows()})
        )
    found = [r for r in rows if not request.unit or r.unit.lower() == request.unit]
    if not found:
        units = sorted({r.unit.lower() for r in rows})
        return no(
            request,
            Why.UNIT,
            f"tensix {request.op} runs on {', '.join(units)}, not {request.unit}",
            *(f"unit {u}" for u in units),
        )
    one = Operand("tile_register", dtype if dtype in tensix.dtypes() else "f32", (32, 32))
    if not request.operands:
        return bad(request, Why.OPERANDS, f"{request.op} needs an operand: it names the element type", spell(x=one))
    if why := mixed(request):
        return bad(request, Why.MIXED_TYPES, why, spell(x=one))
    if dtype not in tensix.dtypes():
        return no(request, Why.ELEMENT_TYPE, f"Tensix computes {', '.join(tensix.dtypes())}, not {dtype}", spell(x=one))
    if any(o.space != "tile_register" for o in request.operands.values()):
        return no(request, Why.SPACE, "a Tensix tile call computes on the unit's tile registers", spell(x=one),
                  fix=INTO_SPACE["tensix"])  # fmt: skip
    if any(o.shape not in ((), (32, 32)) for o in request.operands.values()):
        return no(request, Why.SHAPE, "a Tensix tile call computes one 32x32 tile", spell(x=one))
    row = found[0]
    verdict = tensix.verdicts().get((request.op, dtype, row.unit))
    if verdict is not None and not verdict.ok:
        return no(
            request,
            Why.CHECK_FAILED,
            f"the row failed its check on ttsim: {verdict.error or 'outside its error bound'}",
        )
    init, call = tensix.spelled(row.init, "v08"), tensix.spelled(row.call, "v08")
    check = Check("unverified") if verdict is None else Check("run", "ttsim")
    unit = row.unit.lower()
    return Feasible(request, unit, (Step(unit, init), Step(unit, call)), {"header": row.header}, f"{init};\n{call};",
                    check, (row.note,) if row.note else ())  # fmt: skip


def mma_nearest(target: str, m: int, n: int, k: int) -> tuple[str, ...]:
    """The mma requests ``target`` takes that are closest to an ``m`` x ``n`` x ``k`` product."""
    inputs, swizzle, outputs, layouts = MMA_OPERANDS[target]

    def tile_(space: str, dtype: str, rows: int, cols: int, layout: str, swizzle: str = "none") -> Operand:
        return Operand(space, dtype, (rows, cols), layout, swizzle)  # type: ignore[arg-type]

    def request(in_type: str, acc_type: str, m_: int, n_: int, k_: int) -> str:
        a = tile_(inputs[0], in_type, m_, k_, layouts[0], swizzle)
        b = tile_(inputs[0], in_type, k_, n_, layouts[1], swizzle)
        return spell(a=a, b=b, c=tile_(outputs[0], acc_type, m_, n_, layouts[2]))

    if target == "cpu":
        return tuple(request(i, o, m, n, k) for i, o in tile.CPU_TYPES)
    if target == "sme":
        return (request("f32", "f32", m, n, k),)
    if target == "tensix":
        up = [max(32, -(-extent // 32) * 32) for extent in (m, n, k)]
        return tuple(request(d, d, *up) for d in tensix.dtypes())
    return tuple(request("f16", "f32", bm, bn, 64) for bm, bn in tile.GPU_TILES[target])


#: How a caller moves an mma input into the space its target reads, by target.
INTO_SPACE = {
    "sm90": "load it into shared memory first: ask copy with src global and dst shared:f16:<rows>x64:row_major:b128 (TMA)",
    "gfx942": "load it into LDS first: ask copy with src global and dst shared:f16:<rows>x64:row_major:xor:8",
    "cpu": "the fallback reads memory through pointers: pass the arrays as global",
    "sme": "FMOPA reads its vectors from memory: pass the arrays as global",
    "tensix": "the reader kernel sends each tile into a circular buffer: pass tiles as tile_register",
}
#: How a caller gives an mma input the swizzle its target reads.
INTO_SWIZZLE = {
    "sm90": "the kernel's wgmma descriptor reads 128B-swizzled rows: fill the tile with the TMA copy (dst swizzle "
    "b128, tensor map SWIZZLE_128B), and ask the mma with that swizzle",
    "gfx942": "the kernel reads LDS chunk c of row r at slot c ^ (r % 8): fill the tile with the LDS copy (dst swizzle "
    "xor:8), and ask the mma with that swizzle",
}
#: How a caller gives an mma operand the layout its target reads.
INTO_LAYOUT = {
    ("sm90", "b"): "wgmma reads both inputs K-contiguous, so B is held transposed. Keep Bt (N rows of K) in global "
    "memory and load it with the same TMA copy as A (tensor map over Bt), or transpose once on the host before the "
    "launch. TMA cannot transpose.",
    ("gfx942", "b"): "MFMA reads both inputs K-contiguous, so B is held transposed. Keep Bt (N rows of K) in global "
    "memory and load it with the same LDS copy as A, or change the load to write element (k, n) of B to row n, "
    "column k of the tile.",
    ("sme", "a"): "FMOPA takes one column of A per outer product, so A is held transposed. Keep At (K rows of M) in "
    "memory, or copy A into At once before the loop. Streaming mode has no gather to read a column in place.",
}


def misplaced(target: str, a: Operand, b: Operand, c: Operand) -> tuple[Why, str, str] | None:
    """Why the target's mma cannot take its operands where and how the request has them: the reason's code, the
    reason, and the fix."""
    inputs, swizzle, outputs, layouts = MMA_OPERANDS[target]
    for name, operand in (("a", a), ("b", b)):
        if operand.space not in inputs:
            reason = f"{target} mma reads {name} from {' or '.join(inputs)}, not {operand.space}"
            return Why.SPACE, reason, INTO_SPACE[target]
        if operand.swizzle != swizzle:
            legal = "no swizzle" if swizzle == "none" else f"swizzle {swizzle}"
            fix = INTO_SWIZZLE.get(target, f"{target} has no swizzle: ask with swizzle none")
            return Why.SWIZZLE, f"{target} mma reads {name} with {legal}, not {operand.swizzle}", fix
    if c.space not in outputs:
        fix = f"accumulate in {outputs[0]} and store the result to {c.space} after the last K block"
        return Why.SPACE, f"{target} mma accumulates c in {' or '.join(outputs)}, not {c.space}", fix
    if c.swizzle != "none":
        return Why.SWIZZLE, f"{target} mma accumulates c without a swizzle, not {c.swizzle}", "ask c with swizzle none"
    for name, operand, layout in zip("abc", (a, b, c), layouts, strict=True):
        if operand.layout != layout:
            reason = f"{target} mma takes {name} {layout} ({MMA_LAYOUT[name, layout]}), not {operand.layout}"
            return Why.LAYOUT, reason, INTO_LAYOUT.get((target, name), f"hold {name} {layout}")
    return None


def mma(request: Request, verify: bool) -> Answer:
    """D = A x B + C on tiles, from the tile plans: the CPU fallback, SME's FMOPA, sm_90's wgmma, gfx942's MFMA, or
    Tensix's matmul_tiles. The inputs share one element type and sit where the target's instruction reads them."""
    ops = request.operands
    if not {"a", "b", "c"} <= ops.keys():
        return bad(request, Why.OPERANDS, "mma takes operands a (M x K), b (K x N), and c (M x N)")
    a, b, c = ops["a"], ops["b"], ops["c"]
    if len(a.shape) != 2 or len(b.shape) != 2 or a.shape[1] != b.shape[0] or c.shape != (a.shape[0], b.shape[1]):
        return bad(request, Why.CHAIN, f"shapes do not chain: a {a.shape}, b {b.shape}, c {c.shape}")
    m, k, n = a.shape[0], a.shape[1], b.shape[1]
    target = "cpu" if request.target in CPU else request.target
    nearest = mma_nearest(target, m, n, k)
    if a.dtype != b.dtype:
        return bad(
            request,
            Why.MIXED_TYPES,
            f"a is {a.dtype} and b is {b.dtype}; an mma multiplies inputs of one element type",
            *nearest,
        )
    if target == "tensix":
        return tensix_mma(request, m, n, k, nearest)
    try:
        found = tile.plan(target, m, n, k, a.dtype, c.dtype)
    except KeyError as exc:
        code = Why.SHAPE if (a.dtype, c.dtype) in MMA_TYPES[target] else Why.ELEMENT_TYPE
        return no(request, code, str(exc.args[0]), *nearest)
    if misplaced_ := misplaced(target, a, b, c):
        return no(request, *misplaced_[:2], *nearest, fix=misplaced_[2])
    if verify:
        found = tile.verify(found)
        if found.verified == "failed":
            return no(request, Why.CHECK_FAILED, f"the tile program failed its check: {found.detail}")
    unit = {"cpu": "vector", "sme": "za", "sm90": "warpgroup", "gfx942": "mfma"}[target]
    check = Check(found.verified, found.detail)  # type: ignore[arg-type]
    steps = tuple(Step(unit, s) for s in found.steps)
    return Feasible(request, unit, steps, dict(found.descriptors), found.program, check, (found.layout,))


def tensix_mma(request: Request, m: int, n: int, k: int, nearest: tuple[str, ...]) -> Answer:
    """A Tensix matrix product: ``matmul_tiles`` on the FPU, one call per K tile, accumulated in DST, for every
    32 x 32 output tile; f32 operands are read at TF32."""
    a, b, c = (request.operands[name] for name in "abc")
    if m % 32 or n % 32 or k % 32:
        return no(request, Why.SHAPE, f"Tensix multiplies 32x32 tiles; got {m}x{n}x{k}", *nearest)
    if a.dtype not in tensix.dtypes() or c.dtype not in tensix.dtypes():
        return no(
            request,
            Why.ELEMENT_TYPE,
            f"Tensix computes {', '.join(tensix.dtypes())}, not {a.dtype} into {c.dtype}",
            *nearest,
        )
    if misplaced_ := misplaced("tensix", a, b, c):
        return no(request, *misplaced_[:2], *nearest, fix=misplaced_[2])
    row = next(r for r in tensix.rows() if r.op == "mma")
    verdict = tensix.verdicts().get(("mma", a.dtype, row.unit))
    if verdict is not None and not verdict.ok and not row.pending:
        return no(
            request,
            Why.CHECK_FAILED,
            f"the row failed its check on ttsim: {verdict.error or 'outside its error bound'}",
        )
    if row.pending or verdict is None:
        check = Check("unverified", "pending a ttsim run (the tensix CI job runs it)")
    else:
        check = Check("run", "ttsim")
    tiles = (m // 32) * (n // 32)
    steps = (Step("fpu", tensix.spelled(row.init, "v08")), Step("fpu", tensix.spelled(row.call, "v08"), tiles * (k // 32)),
             Step("fpu", "pack_tile(0, c16)", tiles))  # fmt: skip
    setup = {"header": row.header, "compute config": "fp32_dest_acc_en = true, math_fidelity = HiFi4",
             "reader": "per output tile (mt, nt), for kt: A tile mt*Kt+kt into CB 0, B tile kt*Nt+nt into CB 1"}  # fmt: skip
    code = f"{tensix.spelled(row.init, 'v08')};\n// per output tile: tile_regs_acquire(); for kt: {tensix.spelled(row.call, 'v08')}; ..."
    notes = ("f32 operands reach the FPU as TF32 (A 10 mantissa bits, B 9 at HiFi4); 0.6x spells "
             f"{tensix.spelled(row.init, 'v06')} and {tensix.spelled(row.call, 'v06')}",)  # fmt: skip
    return Feasible(request, "fpu", steps, setup, code, check, notes)


def copy(request: Request) -> Answer:
    """A copy between two spaces: a CPU's vector load or store, sm_90's TMA into a 128B-swizzled shared tile, or
    gfx942's XOR-swizzled LDS stores. A copy converts nothing, so both sides share one element type."""
    ops = request.operands
    if not {"src", "dst"} <= ops.keys():
        return bad(request, Why.OPERANDS, "copy takes operands src and dst")
    src, dst = ops["src"], ops["dst"]
    if request.target in CPU:
        return cpu_copy(request, src, dst)
    box = dst.shape if len(dst.shape) == 2 else (64, 64)
    source = Operand("global", "f16", src.shape if len(src.shape) == 2 and src.dtype == "f16" else (256, 256))
    if request.target == "sm90" and src.space == "global":
        return tma_copy(request, src, dst, source)
    if request.target == "gfx942" and (src.space, dst.space) == ("global", "shared"):
        tile_ = Operand("shared", "f16", (box[0], 64), "row_major", "xor:8")
        nearest = spell(src=source, dst=tile_)
        if (src.dtype, dst.dtype) != ("f16", "f16"):
            return no(
                request,
                Why.ELEMENT_TYPE,
                f"the checked LDS load copies f16 halves, not {src.dtype} to {dst.dtype}",
                nearest,
            )
        if len(dst.shape) != 2 or dst.shape[1] != 64:
            return no(
                request, Why.SHAPE, "the checked LDS load fills rows of 64 halves (8 chunks of 16 bytes)", nearest
            )
        if dst.swizzle != "xor:8" or src.swizzle != "none":
            return no(request, Why.SWIZZLE, "the checked LDS load stores each chunk at slot chunk ^ (row % 8) (dst "
                      "swizzle xor:8) from an unswizzled global tile", nearest)  # fmt: skip
        if src.layout != "row_major" or dst.layout != "row_major":
            return no(request, Why.LAYOUT, "the checked LDS load copies row-major tiles", nearest)
        steps = (Step("lds", "global_load_dwordx4"), Step("lds", "ds_write_b128 at slot chunk ^ (row % 8)"))
        code = "sA[r * 8 + (c ^ (r & 7))] = *reinterpret_cast<const alloy_half8*>(A + r * K + 8 * c);"
        return Feasible(
            request, "lds", steps, {}, code, Check("compiled", "alloy_tile_gfx942.hip.h"), ("16 bytes per lane",)
        )
    return no(
        request,
        Why.NOT_COVERED,
        f"{request.target} copy from {src.space} to {dst.space} comes with step 3 of the design",
    )


def cpu_copy(request: Request, src: Operand, dst: Operand) -> Answer:
    """A CPU copy is a vector load (memory to a register) or a store (a register to memory) of one register."""
    in_register = {"vector", "register"}
    memory, register = (src, dst) if dst.space in in_register else (dst, src)
    lanes = load().isa(request.target).lanes.get(register.dtype, 0)
    one = Operand("vector", register.dtype, (lanes,) if lanes else ())
    nearest = (spell(src=Operand("global", one.dtype, one.shape), dst=one),
               spell(src=one, dst=Operand("global", one.dtype, one.shape)))  # fmt: skip
    if src.swizzle != "none" or dst.swizzle != "none":
        return no(request, Why.SWIZZLE, "a CPU has no swizzle", *nearest)
    if register.space not in in_register or memory.space != "global":
        return no(request, Why.SPACE, f"a CPU copy loads global memory into a register or stores it back, not {src.space} to "
                  f"{dst.space}", *nearest)  # fmt: skip
    if src.dtype != dst.dtype:
        return bad(
            request, Why.MIXED_TYPES, f"a copy converts nothing: src is {src.dtype}, dst is {dst.dtype}", *nearest
        )
    if lanes and register.shape not in ((), (lanes,)):
        return no(request, Why.SHAPE, f"an {request.target} register holds {lanes} {register.dtype} lanes; a larger copy is a "
                  "loop of this one", *nearest)  # fmt: skip
    op = "load" if dst is register else "store"
    answer = vector_op(Request(request.target, op, {"x": one}), verify=False)
    return dataclasses.replace(answer, request=request)


def tma_copy(request: Request, src: Operand, dst: Operand, source: Operand) -> Answer:
    """sm_90's TMA: one box of a row-major f16 global tile into a 128B-swizzled shared tile."""
    rows = dst.shape[0] if len(dst.shape) == 2 and dst.shape[0] in (64, 128) else 64
    nearest = spell(src=source, dst=Operand("shared", "f16", (rows, 64), "row_major", "b128"))
    if dst.space != "shared":
        return no(request, Why.SPACE, f"TMA writes shared memory only, not {dst.space}", nearest)
    if dst.dtype != "f16":
        return no(request, Why.ELEMENT_TYPE, "the checked TMA load fills an f16 tile with the 128B swizzle", nearest)
    if dst.swizzle != "b128":
        return no(request, Why.SWIZZLE, "the checked TMA load fills an f16 tile with the 128B swizzle", nearest)
    if dst.shape not in ((64, 64), (128, 64)):
        return no(request, Why.SHAPE, "a TMA box here is 64 f16 wide (128 bytes) and 64 or 128 rows", nearest)
    if src.dtype != dst.dtype:
        return bad(request, Why.MIXED_TYPES, f"TMA converts nothing: src is {src.dtype}, dst is {dst.dtype}", nearest)
    if len(src.shape) != 2 or src.shape[0] < dst.shape[0] or src.shape[1] < dst.shape[1]:
        return no(
            request,
            Why.SHAPE,
            f"the tensor map describes a two-dimensional global tile at least the box {dst.shape}",
            nearest,
        )
    if src.swizzle != "none":
        return no(request, Why.SWIZZLE, "TMA reads an unswizzled global tile", nearest)
    if src.layout != "row_major" or dst.layout != "row_major":
        return no(request, Why.LAYOUT, "the checked TMA load copies row-major tiles", nearest)
    setup = {"tensor map": f"alloy_make_tmap(&map, global, rows, K, {rows}): FLOAT16, box {{64, {rows}}}, SWIZZLE_128B"}
    steps = (Step("tma", "mbarrier.arrive.expect_tx"), Step("tma", "cp.async.bulk.tensor.2d.shared::cluster.global.mbarrier::complete_tx::bytes"),
             Step("thread", "mbarrier.try_wait.parity"))  # fmt: skip
    code = "alloy_mbar_arrive_expect_tx(&bar, bytes); alloy_tma_load_2d(tile, &map, &bar, k0, row0); alloy_mbar_wait(&bar, phase);"
    return Feasible(request, "tma", steps, setup, code, Check("compiled", "alloy_tile_sm90.cuh"))
