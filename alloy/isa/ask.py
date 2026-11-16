# Copyright 2026 ETH Zurich and the Alloy authors.
"""One abstract machine ISA (alloy-workspace notes/isa-design.md): a :class:`Request` names a target, an operation, and
its operands (memory space, element type, shape, layout, swizzle); :func:`ask` answers :class:`Feasible`, possibly
several instructions, or :class:`Infeasible` with the reason and the nearest requests the target takes.

Step 1 of the design: the answer comes from today's surfaces (the vector table, the math kernels, the SIMT rows, the
Tensix rows, and the tile plans), wrapped, so every existing answer keeps its content and its check.

    python -m alloy.isa ask sm90 mma --a shared:f16:64x64 --b shared:f16:64x64 --c register:f32:64x64
"""

import dataclasses
from typing import Literal, get_args

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from alloy.isa import OPS, load, simt, tensix, tile
from alloy.isa.mathkernels import cheapest, functions, kernel, render, target_of

__all__ = ["TARGETS", "UNITS", "Answer", "Check", "Feasible", "Infeasible", "Operand", "Request", "Step", "ask"]

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
#: Per tile target, where an mma's inputs (a, b) and its accumulator (c) may live, and the swizzles the inputs take
#: ("none" on a GPU input leaves the swizzle to the kernel, which holds its shared tiles in the other one listed).
MMA_OPERANDS: dict[str, tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]] = {
    "cpu": (("global", "vector"), ("none",), ("global", "vector")),
    "sme": (("global", "vector", "tile_register"), ("none",), ("tile_register", "global")),
    "sm90": (("shared",), ("none", "b128"), ("register", "tile_register")),
    "gfx942": (("shared",), ("none", "xor:8"), ("register", "tile_register")),
    "tensix": (("tile_register", "shared"), ("none",), ("tile_register", "shared")),
}
#: What an mma kernel expects beyond the request's row-major operands.
MMA_NOTE = {
    "sm90": "the kernel reads B transposed: pass Bt, N x K row-major",
    "gfx942": "the kernel reads B transposed: pass Bt, N x K row-major",
}


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


@dataclass(config=STRICT)
class Infeasible:
    """No unit of the target carries the request out: the reason, and what the target does take (operands as
    ``name space:dtype:shape[:layout[:swizzle]]``, comma-separated, or ``unit <name>``)."""

    request: Request
    reason: str
    nearest: tuple[str, ...] = ()
    feasible: Literal[False] = False


Answer = Feasible | Infeasible


def no(request: Request, reason: str, *nearest: str) -> Infeasible:
    return Infeasible(request, reason, tuple(nearest))


def spell(**operands: Operand) -> str:
    """Operands as a nearest request names them: ``a shared:f16:64x64, b ...``."""
    return ", ".join(f"{name} {operand.spelled()}" for name, operand in operands.items())


def ask(request: Request, verify: bool = True) -> Answer:
    """The answer to ``request``; ``verify`` runs the check the surface has (on the host, ttsim's record, a compile).
    A pinned unit that does not run the operation is infeasible, with the unit that does."""
    answer = answered(request, verify)
    if isinstance(answer, Feasible) and request.unit and answer.unit != request.unit:
        reason = f"{request.target} {request.op} runs on {answer.unit}, not {request.unit}"
        return no(request, reason, f"unit {answer.unit}")
    return answer


def answered(request: Request, verify: bool) -> Answer:
    if request.target not in UNITS:
        return no(request, f"no target {request.target!r}", *(f"target {t}" for t in TARGETS))
    if request.unit and request.unit not in UNITS[request.target]:
        return no(
            request, f"{request.target} has no unit {request.unit!r}", *(f"unit {u}" for u in UNITS[request.target])
        )
    if request.op == "mma":
        return mma(request, verify)
    if request.op == "copy":
        return copy(request)
    if request.target in DIALECT:
        return thread_op(request)
    if request.op not in OPS and request.op not in functions():
        return no(request, f"no operation {request.op!r}", "an op of `python -m alloy.isa ops`, mma, or copy")
    if request.max_ulp is not None and (request.op not in functions() or request.target == "tensix"):
        what = "a Tensix tile call has one accuracy" if request.target == "tensix" else f"{request.op} is exact"
        return no(request, f"max_ulp selects a rung of a math kernel; {what}", "the request without max_ulp")
    if request.target in CPU:
        return vector_op(request, verify)
    if request.target == "tensix":
        return tile_call(request)
    tile_ = Operand("tile_register", "f32", (32, 32))
    return no(request, "sme answers mma only so far (step 3 of the design)", spell(a=tile_, b=tile_, c=tile_))


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
    if why := mixed(request):
        return no(request, why, spell(x=register))
    for operand in request.operands.values():
        if operand.swizzle != "none":
            return no(request, "a CPU has no swizzle", spell(x=register))
        if len(operand.shape) == 2:
            return no(request, f"{request.op} is elementwise: one register per operand; a tile is an mma or copy operand",
                      spell(x=register))  # fmt: skip
        if lanes and operand.shape and operand.shape != (lanes,):
            return no(
                request, f"an {isa} register holds {lanes} {dtype} lanes, not {operand.shape[0]}", spell(x=register)
            )
    if request.op in functions() and (request.op not in OPS or request.max_ulp is not None):
        return math_kernel(request, isa, dtype)
    try:
        entry = table.entry(isa, request.op, dtype)
    except KeyError as exc:
        others = (Operand("vector", d, (n,) if n else ()) for d, n in table.isa(isa).lanes.items() if d != dtype)
        return no(request, str(exc.args[0]), *(spell(x=o) for o in others))
    if not entry.intrinsic and not entry.recipe:
        if request.op in functions():
            return math_kernel(request, isa, dtype)
        return no(request, f"{isa} has no instruction or recipe for {request.op} on {dtype}")
    steps = (Step("vector", entry.intrinsic),) if entry.intrinsic else tuple(Step("vector", s) for s in entry.recipe)
    check = Check("unverified")
    if verify:
        from alloy.isa.validate import validate

        verdict = validate(isa, request.op, dtype, table)
        if verdict.ok is False:
            return no(request, f"the row failed its check: {verdict.detail}")
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
        return no(request, str(exc.args[0]))
    k = spelled.kernel
    notes = (f"rung {k.level}: {k.error_ulp:.4g} ulp, {spelled.intrinsics} intrinsics, contract: {k.contract}",)
    return Feasible(request, "vector", (Step("vector", k.name),), {}, spelled.source,
                    Check("unverified", "math kernels are checked by `kernel` and `validate`"), notes)  # fmt: skip


def thread_op(request: Request) -> Answer:
    """A GPU operation of one thread or one warp: its SIMT row on scalars, with the recorded check."""
    dialect = DIALECT[request.target]
    rows = {r.op: r for r in simt.rows()}
    if request.op not in rows:
        return no(request, f"no {dialect} row for {request.op}", *(f"{request.target} {op}" for op in rows))
    row, verdict = rows[request.op], simt.verdicts().get((request.op, dialect))
    scalar = Operand("register", SIMT_DTYPE.get(request.op, "f32"))
    for operand in request.operands.values():
        if operand.dtype != scalar.dtype:
            return no(request, f"the {request.op} row computes in {scalar.dtype}, not {operand.dtype}", spell(x=scalar))
        if len(operand.shape) == 2 or operand.swizzle != "none":
            return no(request, f"{request.op} is a row of one thread on scalars; a tile is an mma or copy operand",
                      spell(x=scalar))  # fmt: skip
    if request.max_ulp is not None:
        return no(request, "max_ulp selects a rung of a math kernel; a device row has one accuracy",
                  "the request without max_ulp")  # fmt: skip
    if verdict is not None and verdict.ok is False:
        return no(request, f"the row failed its check: {verdict.error or verdict.basis}")
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
        return no(request, f"no Tensix row for {request.op}", *sorted({f"tensix {r.op}" for r in tensix.rows()}))
    found = [r for r in rows if not request.unit or r.unit.lower() == request.unit]
    if not found:
        units = sorted({r.unit.lower() for r in rows})
        return no(
            request,
            f"tensix {request.op} runs on {', '.join(units)}, not {request.unit}",
            *(f"unit {u}" for u in units),
        )
    one = Operand("tile_register", dtype if dtype in tensix.dtypes() else "f32", (32, 32))
    if why := mixed(request):
        return no(request, why, spell(x=one))
    if dtype not in tensix.dtypes():
        return no(request, f"Tensix computes {', '.join(tensix.dtypes())}, not {dtype}", spell(x=one))
    if any(o.shape not in ((), (32, 32)) for o in request.operands.values()):
        return no(request, "a Tensix tile call computes one 32x32 tile", spell(x=one))
    row = found[0]
    verdict = tensix.verdicts().get((request.op, dtype, row.unit))
    if verdict is not None and not verdict.ok:
        return no(request, f"the row failed its check on ttsim: {verdict.error or 'outside its error bound'}")
    init, call = tensix.spelled(row.init, "v08"), tensix.spelled(row.call, "v08")
    check = Check("unverified") if verdict is None else Check("run", "ttsim")
    unit = row.unit.lower()
    return Feasible(request, unit, (Step(unit, init), Step(unit, call)), {"header": row.header}, f"{init};\n{call};",
                    check, (row.note,) if row.note else ())  # fmt: skip


def mma_nearest(target: str, m: int, n: int, k: int) -> tuple[str, ...]:
    """The mma requests ``target`` takes that are closest to an ``m`` x ``n`` x ``k`` product."""
    inputs, swizzles, outputs = MMA_OPERANDS[target]

    def tile_(space: str, dtype: str, rows: int, cols: int, swizzle: str = "none") -> Operand:
        return Operand(space, dtype, (rows, cols), "row_major", swizzle)  # type: ignore[arg-type]

    def request(in_type: str, acc_type: str, m_: int, n_: int, k_: int) -> str:
        a = tile_(inputs[0], in_type, m_, k_, swizzles[-1])
        return spell(a=a, b=tile_(inputs[0], in_type, k_, n_, swizzles[-1]), c=tile_(outputs[0], acc_type, m_, n_))

    if target == "cpu":
        return tuple(request(i, o, m, n, k) for i, o in tile.CPU_TYPES)
    if target == "sme":
        return (request("f32", "f32", m, n, k),)
    if target == "tensix":
        up = [max(32, -(-extent // 32) * 32) for extent in (m, n, k)]
        return tuple(request(d, d, *up) for d in tensix.dtypes())
    return tuple(request("f16", "f32", bm, bn, 64) for bm, bn in tile.GPU_TILES[target])


def misplaced(target: str, a: Operand, b: Operand, c: Operand) -> str:
    """Why the target's mma cannot take its operands where and how the request has them, or ""."""
    inputs, swizzles, outputs = MMA_OPERANDS[target]
    for name, operand in (("a", a), ("b", b)):
        if operand.space not in inputs:
            return f"{target} mma reads {name} from {' or '.join(inputs)}, not {operand.space}"
        if operand.swizzle not in swizzles:
            legal = "no swizzle" if swizzles == ("none",) else f"swizzle {swizzles[-1]}"
            return f"{target} mma reads {name} with {legal}, not {operand.swizzle}"
    if c.space not in outputs:
        return f"{target} mma accumulates c in {' or '.join(outputs)}, not {c.space}"
    if c.swizzle != "none":
        return f"{target} mma accumulates c without a swizzle, not {c.swizzle}"
    if any(o.layout != "row_major" for o in (a, b, c)):
        return f"{target} mma takes row-major operands"
    return ""


def mma(request: Request, verify: bool) -> Answer:
    """D = A x B + C on tiles, from the tile plans: the CPU fallback, SME's FMOPA, sm_90's wgmma, gfx942's MFMA, or
    Tensix's matmul_tiles. The inputs share one element type and sit where the target's instruction reads them."""
    ops = request.operands
    if not {"a", "b", "c"} <= ops.keys():
        return no(request, "mma takes operands a (M x K), b (K x N), and c (M x N)")
    a, b, c = ops["a"], ops["b"], ops["c"]
    if len(a.shape) != 2 or len(b.shape) != 2 or a.shape[1] != b.shape[0] or c.shape != (a.shape[0], b.shape[1]):
        return no(request, f"shapes do not chain: a {a.shape}, b {b.shape}, c {c.shape}")
    m, k, n = a.shape[0], a.shape[1], b.shape[1]
    target = "cpu" if request.target in CPU else request.target
    nearest = mma_nearest(target, m, n, k)
    if a.dtype != b.dtype:
        return no(request, f"a is {a.dtype} and b is {b.dtype}; an mma multiplies inputs of one element type", *nearest)
    if target == "tensix":
        return tensix_mma(request, m, n, k, nearest)
    try:
        found = tile.plan(target, m, n, k, a.dtype, c.dtype)
    except KeyError as exc:
        return no(request, str(exc.args[0]), *nearest)
    if why := misplaced(target, a, b, c):
        return no(request, why, *nearest)
    if verify:
        found = tile.verify(found)
        if found.verified == "failed":
            return no(request, f"the tile program failed its check: {found.detail}")
    unit = {"cpu": "vector", "sme": "za", "sm90": "warpgroup", "gfx942": "mfma"}[target]
    check = Check(found.verified, found.detail)  # type: ignore[arg-type]
    steps = tuple(Step(unit, s) for s in found.steps)
    notes = (found.layout, *((MMA_NOTE[target],) if target in MMA_NOTE else ()))
    return Feasible(request, unit, steps, dict(found.descriptors), found.program, check, notes)


def tensix_mma(request: Request, m: int, n: int, k: int, nearest: tuple[str, ...]) -> Answer:
    """A Tensix matrix product: ``matmul_tiles`` on the FPU, one call per K tile, accumulated in DST, for every
    32 x 32 output tile; f32 operands are read at TF32."""
    a, b, c = (request.operands[name] for name in "abc")
    if m % 32 or n % 32 or k % 32:
        return no(request, f"Tensix multiplies 32x32 tiles; got {m}x{n}x{k}", *nearest)
    if a.dtype not in tensix.dtypes() or c.dtype not in tensix.dtypes():
        return no(request, f"Tensix computes {', '.join(tensix.dtypes())}, not {a.dtype} into {c.dtype}", *nearest)
    if why := misplaced("tensix", a, b, c):
        return no(request, why, *nearest)
    row = next(r for r in tensix.rows() if r.op == "mma")
    verdict = tensix.verdicts().get(("mma", a.dtype, row.unit))
    if verdict is not None and not verdict.ok and not row.pending:
        return no(request, f"the row failed its check on ttsim: {verdict.error or 'outside its error bound'}")
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
        return no(request, "copy takes operands src and dst")
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
            return no(request, f"the checked LDS load copies f16 halves, not {src.dtype} to {dst.dtype}", nearest)
        if len(dst.shape) != 2 or dst.shape[1] != 64 or dst.swizzle != "xor:8" or src.swizzle != "none":
            return no(request, "the checked LDS load fills rows of 64 halves at slot chunk ^ (row % 8) (swizzle xor:8) "
                      "from an unswizzled global tile", nearest)  # fmt: skip
        steps = (Step("lds", "global_load_dwordx4"), Step("lds", "ds_write_b128 at slot chunk ^ (row % 8)"))
        code = "sA[r * 8 + (c ^ (r & 7))] = *reinterpret_cast<const alloy_half8*>(A + r * K + 8 * c);"
        return Feasible(
            request, "lds", steps, {}, code, Check("compiled", "alloy_tile_gfx942.hip.h"), ("16 bytes per lane",)
        )
    return no(request, f"{request.target} copy from {src.space} to {dst.space} comes with step 3 of the design")


def cpu_copy(request: Request, src: Operand, dst: Operand) -> Answer:
    """A CPU copy is a vector load (memory to a register) or a store (a register to memory) of one register."""
    in_register = {"vector", "register"}
    memory, register = (src, dst) if dst.space in in_register else (dst, src)
    lanes = load().isa(request.target).lanes.get(register.dtype, 0)
    one = Operand("vector", register.dtype, (lanes,) if lanes else ())
    nearest = (spell(src=Operand("global", one.dtype, one.shape), dst=one),
               spell(src=one, dst=Operand("global", one.dtype, one.shape)))  # fmt: skip
    if src.swizzle != "none" or dst.swizzle != "none":
        return no(request, "a CPU has no swizzle", *nearest)
    if register.space not in in_register or memory.space != "global":
        return no(request, f"a CPU copy loads global memory into a register or stores it back, not {src.space} to "
                  f"{dst.space}", *nearest)  # fmt: skip
    if src.dtype != dst.dtype:
        return no(request, f"a copy converts nothing: src is {src.dtype}, dst is {dst.dtype}", *nearest)
    if lanes and register.shape not in ((), (lanes,)):
        return no(request, f"an {request.target} register holds {lanes} {register.dtype} lanes; a larger copy is a "
                  "loop of this one", *nearest)  # fmt: skip
    op = "load" if dst is register else "store"
    answer = vector_op(Request(request.target, op, {"x": one}), verify=False)
    return dataclasses.replace(answer, request=request)


def tma_copy(request: Request, src: Operand, dst: Operand, source: Operand) -> Answer:
    """sm_90's TMA: one box of a row-major f16 global tile into a 128B-swizzled shared tile."""
    rows = dst.shape[0] if len(dst.shape) == 2 and dst.shape[0] in (64, 128) else 64
    nearest = spell(src=source, dst=Operand("shared", "f16", (rows, 64), "row_major", "b128"))
    if dst.space != "shared":
        return no(request, f"TMA writes shared memory only, not {dst.space}", nearest)
    if dst.swizzle != "b128" or dst.dtype != "f16":
        return no(request, "the checked TMA load fills an f16 tile with the 128B swizzle", nearest)
    if dst.shape not in ((64, 64), (128, 64)):
        return no(request, "a TMA box here is 64 f16 wide (128 bytes) and 64 or 128 rows", nearest)
    if src.dtype != dst.dtype:
        return no(request, f"TMA converts nothing: src is {src.dtype}, dst is {dst.dtype}", nearest)
    if len(src.shape) != 2 or src.shape[0] < dst.shape[0] or src.shape[1] < dst.shape[1]:
        return no(
            request, f"the tensor map describes a two-dimensional global tile at least the box {dst.shape}", nearest
        )
    if src.swizzle != "none" or src.layout != "row_major" or dst.layout != "row_major":
        return no(request, "TMA reads an unswizzled row-major global tile", nearest)
    setup = {"tensor map": f"alloy_make_tmap(&map, global, rows, K, {rows}): FLOAT16, box {{64, {rows}}}, SWIZZLE_128B"}
    steps = (Step("tma", "mbarrier.arrive.expect_tx"), Step("tma", "cp.async.bulk.tensor.2d.shared::cluster.global.mbarrier::complete_tx::bytes"),
             Step("thread", "mbarrier.try_wait.parity"))  # fmt: skip
    code = "alloy_mbar_arrive_expect_tx(&bar, bytes); alloy_tma_load_2d(tile, &map, &bar, k0, row0); alloy_mbar_wait(&bar, phase);"
    return Feasible(request, "tma", steps, setup, code, Check("compiled", "alloy_tile_sm90.cuh"))
