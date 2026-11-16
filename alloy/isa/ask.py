# Copyright 2026 ETH Zurich and the Alloy authors.
"""One abstract machine ISA (alloy-workspace notes/isa-design.md): a :class:`Request` names a target, an operation, and
its operands (memory space, element type, shape, layout, swizzle); :func:`ask` answers :class:`Feasible`, possibly
several instructions, or :class:`Infeasible` with the reason and the nearest requests the target takes.

Step 1 of the design: the answer comes from today's surfaces (the vector table, the math kernels, the SIMT rows, the
Tensix rows, and the tile plans), wrapped, so every existing answer keeps its content and its check.

    python -m alloy.isa ask sm90 mma --a shared:f16:64x64 --b shared:f16:64x64 --c register:f32:64x64
"""

import dataclasses
from typing import Literal

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from alloy.isa import OPS, load, simt, tensix, tile
from alloy.isa.mathkernels import cheapest, functions, kernel, render, target_of

__all__ = ["TARGETS", "UNITS", "Answer", "Check", "Feasible", "Infeasible", "Operand", "Request", "Step", "ask"]

STRICT = ConfigDict(extra="forbid", strict=True, frozen=True)
Space = Literal["register", "vector", "tile_register", "shared", "global", "constant"]

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


@dataclass(config=STRICT)
class Operand:
    """One operand: where it lives, its element type, its shape (``()`` a scalar, ``(lanes,)`` a vector, ``(rows,
    cols)`` a tile), its layout, its swizzle, and its alignment in bytes (0: the element's own)."""

    space: Space
    dtype: str
    shape: tuple[int, ...] = ()
    layout: str = "row_major"
    swizzle: str = "none"
    align: int = 0

    @classmethod
    def parse(cls, text: str) -> "Operand":
        """``space:dtype[:RxC or N][:layout][:swizzle]``, as the CLI spells it (``shared:f16:64x64:row_major:b128``)."""
        parts = text.split(":")
        if len(parts) < 2:
            raise KeyError(f"{text!r}: an operand is space:dtype[:shape][:layout][:swizzle]")
        shape = tuple(int(n) for n in parts[2].split("x")) if len(parts) > 2 and parts[2] else ()
        layout = parts[3] if len(parts) > 3 else "row_major"
        swizzle = parts[4] if len(parts) > 4 else "none"
        return cls(parts[0], parts[1], shape, layout, swizzle)  # type: ignore[arg-type]


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
    """No unit of the target carries the request out: the reason, and requests the target does take."""

    request: Request
    reason: str
    nearest: tuple[str, ...] = ()
    feasible: Literal[False] = False


Answer = Feasible | Infeasible


def no(request: Request, reason: str, *nearest: str) -> Infeasible:
    return Infeasible(request, reason, tuple(nearest))


def ask(request: Request, verify: bool = True) -> Answer:
    """The answer to ``request``; ``verify`` runs the check the surface has (on the host, ttsim's record, a compile)."""
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
    if request.op not in OPS and request.op not in functions():
        return no(request, f"no operation {request.op!r}", "an op of `python -m alloy.isa ops`, mma, or copy")
    if request.target in CPU:
        return vector_op(request, verify)
    if request.target in DIALECT:
        return thread_op(request)
    if request.target == "tensix":
        return tile_call(request)
    return no(request, f"{request.target} answers mma and copy only so far (step 3 of the design)")


def dtype_of(request: Request) -> str:
    """The element type the request computes in: its first operand's, else f64."""
    return next((o.dtype for o in request.operands.values()), "f64")


def vector_op(request: Request, verify: bool) -> Answer:
    """A CPU operation: the table's row, or the math kernel at the cheapest rung that holds ``max_ulp``."""
    dtype, isa = dtype_of(request), request.target
    if request.op in functions() and (request.op not in OPS or request.max_ulp is not None):
        return math_kernel(request, isa, dtype)
    table = load()
    try:
        entry = table.entry(isa, request.op, dtype)
    except KeyError as exc:
        return no(request, str(exc.args[0]), f"{isa} {request.op} f64", f"{isa} {request.op} f32")
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
    """A GPU operation of one thread or one warp: its SIMT row, with the recorded check."""
    dialect = DIALECT[request.target]
    rows = {r.op: r for r in simt.rows()}
    if request.op not in rows:
        return no(request, f"no {dialect} row for {request.op}", *(f"{request.target} {op}" for op in rows))
    row, verdict = rows[request.op], simt.verdicts().get((request.op, dialect))
    spelling = row.cuda if dialect == "cuda" else row.hip
    check = Check("unverified") if verdict is None else Check("run" if verdict.ok else "compiled", verdict.basis)
    unit = "warp" if row.kind == "warp" else "thread"
    return Feasible(request, unit, (Step(unit, spelling),), {}, spelling, check, (row.note,) if row.note else ())


def tile_call(request: Request) -> Answer:
    """A Tensix operation: its tile calls (one per unit that has the operation), with ttsim's recorded check."""
    dtype = dtype_of(request)
    found = [r for r in tensix.rows() if r.op == request.op and (not request.unit or r.unit.lower() == request.unit)]
    if not found:
        return no(request, f"no Tensix row for {request.op}", *sorted({f"tensix {r.op}" for r in tensix.rows()}))
    if dtype not in tensix.dtypes():
        return no(request, f"Tensix computes {', '.join(tensix.dtypes())}, not {dtype}", "--dtype f32")
    row = found[0]
    verdict = tensix.verdicts().get((request.op, dtype, row.unit))
    init, call = tensix.spelled(row.init, "v08"), tensix.spelled(row.call, "v08")
    check = Check("unverified") if verdict is None else Check("run" if verdict.ok else "unverified", "ttsim")
    unit = row.unit.lower()
    return Feasible(request, unit, (Step(unit, init), Step(unit, call)), {"header": row.header}, f"{init};\n{call};",
                    check, (row.note,) if row.note else ())  # fmt: skip


def mma(request: Request, verify: bool) -> Answer:
    """D = A x B + C on tiles, from the tile plans: the CPU fallback, sm_90's wgmma, or gfx942's MFMA."""
    ops = request.operands
    if not {"a", "b", "c"} <= ops.keys():
        return no(request, "mma takes operands a (M x K), b (K x N), and c (M x N)")
    a, b, c = ops["a"], ops["b"], ops["c"]
    if len(a.shape) != 2 or len(b.shape) != 2 or a.shape[1] != b.shape[0] or c.shape != (a.shape[0], b.shape[1]):
        return no(request, f"shapes do not chain: a {a.shape}, b {b.shape}, c {c.shape}")
    m, k, n = a.shape[0], a.shape[1], b.shape[1]
    target = "cpu" if request.target in CPU else request.target
    if target == "tensix":
        return tensix_mma(request, m, n, k, a.dtype)
    try:
        found = tile.plan(target, m, n, k, a.dtype, c.dtype)
    except KeyError as exc:
        if target == "cpu":
            nearest = tuple(f"a vector:{i}:{m}x{k}, c vector:{o}:{m}x{n}" for i, o in tile.CPU_TYPES)
        elif target == "sme":
            nearest = (f"a tile_register:f32:{m}x{k}, b tile_register:f32:{k}x{n}, c tile_register:f32:{m}x{n}",)
        else:
            nearest = tuple(
                f"a shared:f16:{bm}x64, b shared:f16:64x{bn}, c register:f32:{bm}x{bn}"
                for bm, bn in tile.GPU_TILES[target]
            )
        return no(request, str(exc.args[0]), *nearest)
    if verify:
        found = tile.verify(found)
    unit = {"cpu": "vector", "sme": "za", "sm90": "warpgroup", "gfx942": "mfma"}[target]
    check = Check(found.verified, found.detail)  # type: ignore[arg-type]
    steps = tuple(Step(unit, s) for s in found.steps)
    return Feasible(request, unit, steps, dict(found.descriptors), found.program, check, (found.layout,))


def tensix_mma(request: Request, m: int, n: int, k: int, dtype: str) -> Answer:
    """A Tensix matrix product: ``matmul_tiles`` on the FPU, one call per K tile, accumulated in DST, for every
    32 x 32 output tile; f32 operands are read at TF32."""
    if m % 32 or n % 32 or k % 32:
        return no(request, f"Tensix multiplies 32x32 tiles; got {m}x{n}x{k}", "a, b, c with extents multiples of 32")
    if dtype not in tensix.dtypes():
        return no(request, f"Tensix computes {', '.join(tensix.dtypes())}, not {dtype}", "a and b in f32 or bf16")
    row = next(r for r in tensix.rows() if r.op == "mma")
    verdict = tensix.verdicts().get(("mma", dtype, row.unit))
    if row.pending or verdict is None:
        check = Check("unverified", "pending a ttsim run (the tensix CI job runs it)")
    else:
        check = Check("run" if verdict.ok else "unverified", "ttsim")
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
    """A copy between two spaces: sm_90's TMA into a 128B-swizzled shared tile, gfx942's swizzled LDS stores, or a
    CPU's vector load; anything else waits for step 3 of the design."""
    ops = request.operands
    if not {"src", "dst"} <= ops.keys():
        return no(request, "copy takes operands src and dst")
    src, dst = ops["src"], ops["dst"]
    if request.target in CPU:
        if src.swizzle != "none" or dst.swizzle != "none":
            return no(request, "a CPU has no swizzle", f"{request.target} copy with swizzle none")
        return vector_op(Request(request.target, "load", {"x": dst}), verify=False)
    if request.target == "sm90" and (src.space, dst.space) == ("global", "shared") and request.unit in ("", "tma"):
        if dst.swizzle != "b128" or dst.dtype != "f16":
            return no(
                request,
                "the checked TMA load fills an f16 tile with the 128B swizzle",
                "dst shared:f16:RxC:row_major:b128",
            )
        rows, cols = dst.shape if len(dst.shape) == 2 else (0, 0)
        if cols != 64 or rows not in (64, 128):
            return no(
                request, "a TMA box here is 64 f16 wide (128 bytes) and 64 or 128 rows", "dst shape 64x64 or 128x64"
            )
        setup = {
            "tensor map": f"alloy_make_tmap(&map, global, rows, K, {rows}): FLOAT16, box {{64, {rows}}}, SWIZZLE_128B"
        }
        steps: tuple[Step, ...] = (Step("tma", "mbarrier.arrive.expect_tx"), Step("tma", "cp.async.bulk.tensor.2d.shared::cluster.global.mbarrier::complete_tx::bytes"),
                 Step("thread", "mbarrier.try_wait.parity"))  # fmt: skip
        code = "alloy_mbar_arrive_expect_tx(&bar, bytes); alloy_tma_load_2d(tile, &map, &bar, k0, row0); alloy_mbar_wait(&bar, phase);"
        return Feasible(request, "tma", steps, setup, code, Check("compiled", "alloy_tile_sm90.cuh"))
    if request.target == "gfx942" and (src.space, dst.space) == ("global", "shared"):
        steps = (Step("lds", "global_load_dwordx4"), Step("lds", "ds_write_b128 at slot chunk ^ (row % 8)"))
        code = "sA[r * 8 + (c ^ (r & 7))] = *reinterpret_cast<const alloy_half8*>(A + r * K + 8 * c);"
        return Feasible(
            request, "lds", steps, {}, code, Check("compiled", "alloy_tile_gfx942.hip.h"), ("16 bytes per lane",)
        )
    return no(request, f"{request.target} copy from {src.space} to {dst.space} comes with step 3 of the design")
