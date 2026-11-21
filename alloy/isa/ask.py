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

:func:`ask_all` answers requests that run as one kernel (design section 2.4b): a copy into shared memory and the mma it
fills are checked as the one tile program that runs both.

    python -m alloy.isa ask-all sm90 'copy src=global:f16:64x64 dst=shared:f16:64x64:row_major:b128' \
        'mma a=shared:f16:64x64:row_major:b128 b=shared:f16:64x64:col_major:b128 c=register:f32:64x64'
"""

import dataclasses
import difflib
import enum
import math
from collections.abc import Sequence
from typing import Literal, get_args

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from alloy.isa import OPS, load, simt, softhier, tensix, tile
from alloy.isa.mathkernels import cheapest, functions, kernel, ladder, render, target_of
from alloy.isa.table import ALIASES, GATED, Entry, Table, gate
from alloy.isa.validate import HEADERS, c_flags

__all__ = [
    "TARGETS",
    "UNITS",
    "Answer",
    "Check",
    "Combined",
    "Feasible",
    "Infeasible",
    "Invalid",
    "Operand",
    "Request",
    "Step",
    "Why",
    "ask",
    "ask_all",
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
    "avx512_fp16": ("vector", "scalar"),
    "neon": ("vector", "scalar"),
    "sve": ("vector", "scalar"),
    "sme": ("streaming_vector", "za"),
    "sm90": ("thread", "warp", "warpgroup", "tma", "cp_async"),
    "gfx942": ("thread", "wave", "mfma", "lds_dma", "lds"),
    "gfx90a": ("thread", "wave", "mfma", "lds_dma", "lds"),
    "tensix": ("sfpu", "fpu", "noc"),
    "softhier": ("spatz", "idma", "redmule", "cluster"),
}
TARGETS = tuple(UNITS)
CPU = ("avx2", "avx512", "avx512_fp16", "neon", "sve")
#: The dialect of a GPU target's per-thread rows (simt.toml).
DIALECT = {"sm90": "cuda"} | dict.fromkeys(tile.CDNA, "hip")
#: Per tile target, what its mma kernel reads, exactly: the space of the inputs (a, b), their swizzle, the space of the
#: accumulator (c), and the layout of a, b, and c. A request that names anything else is infeasible, so an answer never
#: computes on a tile laid out differently from the one the caller holds. The GPU kernels read B with K contiguous
#: (col_major, that is Bt as N rows of K), and SME's outer products read A with K leading (col_major, At as K rows of M).
MMA_OPERANDS: dict[str, tuple[tuple[str, ...], str, tuple[str, ...], tuple[str, str, str]]] = {
    "cpu": (("global",), "none", ("global",), ("row_major", "row_major", "row_major")),
    "sme": (("global",), "none", ("tile_register", "global"), ("col_major", "row_major", "row_major")),
    "sm90": (("shared",), "b128", ("register", "tile_register"), ("row_major", "col_major", "row_major")),
    "gfx942": (("shared",), "xor:8", ("register", "tile_register"), ("row_major", "col_major", "row_major")),
    "gfx90a": (("shared",), "xor:8", ("register", "tile_register"), ("row_major", "col_major", "row_major")),
    "tensix": (("tile_register",), "none", ("tile_register",), ("row_major", "row_major", "row_major")),
}  # fmt: skip
#: What a layout of an mma operand means in memory, for the refusal's reason.
MMA_LAYOUT = {
    ("a", "row_major"): "M rows of K", ("a", "col_major"): "At, K rows of M",
    ("b", "row_major"): "K rows of N", ("b", "col_major"): "Bt, N rows of K",
    ("c", "row_major"): "M rows of N", ("c", "col_major"): "Ct, N rows of M",
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
    MIXED_TARGETS = "mixed_targets"

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
    COMBINE = "answers_do_not_combine"
    ORDER = "order"


#: The reasons of an invalid request; every other reason is an infeasible one.
INVALID = frozenset({Why.TARGET, Why.UNIT_NAME, Why.OPERATION, Why.OPERANDS, Why.MALFORMED, Why.CHAIN,
                     Why.MIXED_TYPES, Why.BOUND, Why.MIXED_TARGETS})  # fmt: skip


@dataclass(config=STRICT)
class Operand:
    """One operand: where it lives, its element type, its shape (``()`` a scalar, ``(lanes,)`` a vector, ``(rows,
    cols)`` a tile), its layout, and its swizzle. The alignment a tile needs is the answer's setup, not an operand's."""

    space: Space
    dtype: str
    shape: tuple[int, ...] = ()
    layout: Layout = "row_major"
    swizzle: Swizzle = "none"

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
    #: ``wait``: the completion token waited on; ``fence``: the fence's kind (``proxy``, ``operand``).
    on: str = ""
    kind: str = ""


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
class Completion:
    """How asynchronous work completes (design 2.9): the token its issue signals, the ``wait`` request that completes
    it, and the ``fence`` requests that must come before its issue. Reading the work's result before the wait is a
    race; issuing it without the fences reads stale data."""

    token: str
    wait: str
    fences: tuple[str, ...] = ()


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
    #: Set when the unit is asynchronous: how its work completes.
    completion: Completion | None = None
    feasible: Literal[True] = True
    status: Literal["feasible"] = "feasible"


@dataclass(config=STRICT)
class Infeasible:
    """A well-formed request that no unit of the target carries out: the reason's code, the reason, and what the
    target does take (operands as ``name space:dtype:shape[:layout[:swizzle]]``, comma-separated, or ``unit <name>``).
    ``fix`` says how the caller gets from what it has to a nearest request (a load that swizzles, a transposed
    store), where Alloy knows one. ``block`` is the extent one instruction of the lowering takes, per dimension (the
    lanes of a register; the rows and columns of a tile; M, N, and K of a product's kernel block): a shape the target
    takes is a whole multiple of it. It is set on every refusal for a shape."""

    request: Request
    why: Why
    reason: str
    nearest: tuple[str, ...] = ()
    fix: str = ""
    block: tuple[int, ...] = ()
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


@dataclass(config=STRICT)
class Combined:
    """The answers to several requests that run as one kernel, in the order asked: which copy fills which mma input,
    and the check of them together. A copy and the mma it fills carry the check of the one tile program that runs
    both; ``check`` is the weakest check of the answers."""

    answers: tuple[Feasible, ...]
    feeds: tuple[str, ...]
    check: Check
    #: The waits and fences the kernel needs, in order, when the list did not state them (design 2.9).
    order: tuple[str, ...] = ()
    feasible: Literal[True] = True
    status: Literal["feasible"] = "feasible"


def no(
    request: Request, why: Why, reason: str, *nearest: str, fix: str = "", block: tuple[int, ...] = ()
) -> Infeasible:
    assert why not in INVALID, why
    return Infeasible(request, why, reason, tuple(nearest), fix, block)


#: The primitives a request names on logical data (design 2.8): the reductions with the lane-wise row that combines two
#: blocks, and the scans with the row that carries a block's last element into the next.
REDUCTIONS = {"reduce_add": "add", "reduce_min": "min", "reduce_max": "max"}
SCANS = {"scan_add": "add"}
#: The last lane of a scanned register ``t``, broadcast to every lane: the carry of a scan into the next register.
LAST_LANE = {
    ("avx512", "f64"): "_mm512_permutexvar_pd(_mm512_set1_epi64(7), t)",
    ("avx512", "f32"): "_mm512_permutexvar_ps(_mm512_set1_epi32(15), t)",
    ("avx2", "f64"): "_mm256_permute4x64_pd(t, 0xFF)",
    ("avx2", "f32"): "_mm256_permutevar8x32_ps(t, _mm256_set1_epi32(7))",
    ("neon", "f64"): "vdupq_laneq_f64(t, 1)",
    ("neon", "f32"): "vdupq_laneq_f32(t, 3)",
    ("sve", "f64"): "svdup_n_f64(svlastb_f64(pg, t))",
    ("sve", "f32"): "svdup_n_f32(svlastb_f32(pg, t))",
}
#: Where a load ends and a store starts; every other space is memory.
REGISTERS = ("register", "vector", "tile_register")
#: How a caller finishes the elements past the last whole register on a CPU without masks.
REMAINDER = "finish them in a scalar remainder loop, or pad the data to the multiple above"
#: What a masked-off lane must hold so a reduction's lane-wise combine ignores it.
IDENTITY = {"reduce_add": "0", "reduce_min": "INFINITY", "reduce_max": "-INFINITY"}


def tail_fix(isa: str, op: str, dtype: str, table: Table) -> str:
    """How a caller finishes the elements past the last whole register for ``op``: a masked form where the row has
    one, else a masked load that fills the masked-off lanes so the whole-register op is right."""
    isa = ALIASES.get(isa, isa)  # avx512_fp16 masks like avx512
    if isa == "sve":
        return "run every block under the svwhilelt predicate (ask gen_mask); ask with the whole extent for the loop"
    if isa != "avx512":
        return REMAINDER
    rows = table.isa(isa).entries(dtype)
    entry, load, store = (rows.get(name, Entry()).masked for name in (op, "load", "store"))
    if op in REDUCTIONS:
        fill = rows.get("broadcast", Entry()).intrinsic
        filled = (
            load
            if op == "reduce_add"
            else load.replace("maskz_", "mask_").replace("(k, p)", f"({fill}({IDENTITY[op]}), k, p)")
        )
        return (
            f"ask gen_mask for the last block's mask k, load the block with {filled} so its masked-off lanes hold "
            f"{IDENTITY[op]}, combine it lane-wise like a whole register, and reduce once"
        )
    if op in ("load", "store"):
        return f"ask gen_mask for the last block's mask k, then {op} it with {entry}"
    compute = f"compute with {entry}" if entry else "compute as a whole register"
    return f"ask gen_mask for the last block's mask k, load with {load}, {compute}, store with {store}"


def uneven(request: Request, isa: str, dtype: str, n: int, lanes: int, *names: str, op: str = "") -> Infeasible:
    """The refusal of ``n`` elements that are no whole multiple of a register's ``lanes``: the block, the multiples
    below and above as nearest requests (``names`` are the operands a nearest request spells), and the tail's fix."""
    below = n - n % lanes
    full = n // lanes
    held = (
        f"{full} register{'s' if full > 1 else ''} hold{'' if full > 1 else 's'} {below}, {n % lanes} remain"
        if below
        else "less than one register"
    )
    article = "a" if isa == "neon" else "an"
    reason = f"{n} {dtype} elements are not a whole multiple of the {lanes} {dtype} lanes of {article} {isa} register: {held}"
    if request.op == "broadcast":
        reason += f"; a broadcast's scalar source is --x register:{dtype} (or register:{dtype}:1)"
    sizes = [size for size in (below, below + lanes) if size]
    if names == ("src", "dst"):
        memory = "src" if request.operands["dst"].space in REGISTERS else "dst"
        nearest = [
            spell(**{name: Operand("global" if name == memory else "vector", dtype, (size,)) for name in names})
            for size in sizes
        ]
    else:
        nearest = [spell(x=Operand("vector", dtype, (size,))) for size in sizes]
    fix = tail_fix(isa, op or request.op, dtype, load())
    return no(request, Why.SHAPE, reason, *nearest, fix=fix, block=(lanes,))


def repeated(answer: Answer, request: Request, count: int, table: Table, isa: str, dtype: str) -> Answer:
    """``answer`` for one register, as the answer for ``count`` of them: every step runs ``count`` times; a reduction
    combines the registers lane-wise and reduces once; a scan carries each register's last lane into the next."""
    if not isinstance(answer, Feasible) or count == 1:
        return answer
    if request.op in REDUCTIONS:
        combine = table.entry(isa, REDUCTIONS[request.op], dtype).intrinsic
        steps = (Step("vector", combine, count - 1), *answer.steps)
        note = (
            f"{count} registers: combine them lane-wise with {combine} into one accumulator register, then reduce "
            "it once; the lanes combine in another order than a scalar left fold"
        )
    elif request.op in SCANS:
        carry = (LAST_LANE[isa, dtype], table.entry(isa, SCANS[request.op], dtype).intrinsic)
        steps = (*(dataclasses.replace(s, count=count) for s in answer.steps),
                 *(Step("vector", c, count - 1) for c in carry))  # fmt: skip
        note = (
            f"{count} registers: scan each, then from the second on add the carry c, the last lane of the scanned "
            f"register before broadcast to every lane: c = {carry[0]} with t the register before, then "
            f"{carry[1]}(this register, c)"
        )
    else:
        steps = tuple(dataclasses.replace(s, count=s.count * count) for s in answer.steps)
        note = f"{count} registers: a loop of {count} iterations, one register each"
    return dataclasses.replace(answer, steps=steps, notes=(*answer.notes, note))


def bad(request: Request | None, why: Why, reason: str, *expected: str) -> Invalid:
    assert why in INVALID, why
    return Invalid(request, why, reason, tuple(expected))


def spell(**operands: Operand) -> str:
    """Operands as a nearest request names them: ``a shared:f16:64x64, b ...``."""
    return ", ".join(f"{name} {operand.spelled()}" for name, operand in operands.items())


def ask(request: Request, verify: bool = True) -> Answer:
    """The answer to ``request``; ``verify`` runs the check the surface has (on the host, ttsim's record, a compile).
    A pinned unit that does not run the operation is infeasible, with the unit that does; ``on`` and ``kind`` on an
    operation other than ``wait`` (``on``) and ``fence`` or ``barrier`` (``kind``) are invalid, so a flag is never silently dropped."""
    for flag, value, owners in (("on", request.on, ("wait",)), ("kind", request.kind, ("fence", "barrier"))):
        if value and request.op not in owners:
            return bad(
                request,
                Why.OPERANDS,
                f"--{flag} applies to {' and '.join(owners)} only; {request.op} has no {flag}",
                f"ask {request.target} {owners[0]} --{flag} ...",
                f"ask {request.target} {request.op} without --{flag}",
            )
    answer = answered(request, verify)
    if isinstance(answer, Feasible) and request.unit and answer.unit != request.unit:
        reason = f"{request.target} {request.op} runs on {answer.unit}, not {request.unit}"
        return no(request, Why.UNIT, reason, f"unit {answer.unit}")
    return answer


#: Per target and completion token: the wait's spelling and what it waits for (isa-research/tensor.md 1.5, 3.3, 3.4,
#: 7.4; tensix-primitives.md). The tile programs that run on the hardware issue the sm90 and Tensix ones.
WAITS: dict[str, dict[str, tuple[str, str]]] = {
    "sm90": {
        "mbarrier": ("alloy_mbar_wait(&bar, phase); phase ^= 1;  // mbarrier.try_wait.parity in a loop",
                     "a TMA load's bytes have arrived; the barrier's phase flips with each use"),
        "bulk_group": ('asm volatile("cp.async.bulk.commit_group;"); asm volatile("cp.async.bulk.wait_group.read 0;");',
                       ("a TMA store has read its shared tile, so the tile may be overwritten (without .read: the global "
                       "write is done)")),
        "cp_async_group": (('asm volatile("cp.async.commit_group;"); asm volatile("cp.async.wait_group 0;"); '
                           "__syncthreads();"), "the group's cp.async copies have landed in shared memory"),
        "wgmma_group": (('asm volatile("wgmma.commit_group.sync.aligned;"); asm volatile("wgmma.wait_group.sync.aligned '
                        '0;");'), "the group's wgmma have written their accumulators; reading them earlier is undefined"),
    },
    "tensix": {
        "noc": ("noc_async_read_barrier();", "the NoC reads issued so far have landed in L1"),
        "cb": ("cb_wait_front(cb, n);", "the producer has pushed n tiles into the circular buffer"),
    },
} | dict.fromkeys(tile.CDNA, {
    "vmcnt": ('asm volatile("s_waitcnt vmcnt(0)" ::: "memory");',
              "the wave's global loads (and LDS DMA) have returned"),
    "lgkmcnt": ('asm volatile("s_waitcnt lgkmcnt(0)" ::: "memory"); __syncthreads();',
                "the wave's LDS writes have landed, and the barrier lets every wave of the block read them"),
})  # fmt: skip
#: Per target and fence kind: the fence's spelling and what it orders. Only sm90 splits the generic and the async
#: proxy, and only wgmma reads registers asynchronously.
FENCES: dict[str, dict[str, tuple[str, str]]] = {
    "sm90": {
        "proxy": ('asm volatile("fence.proxy.async.shared::cta;" ::: "memory");',
                  ("generic-proxy writes to shared memory (thread stores, an mbarrier's init) become visible to the "
                  "async proxy (TMA, wgmma)")),
        "operand": ('asm volatile("wgmma.fence.sync.aligned;" ::: "memory");',
                    ("register accesses to a wgmma's accumulators or A fragment come before the next wgmma; none is "
                    "needed between back-to-back wgmma of one shape")),
    },
}  # fmt: skip
#: Why a target needs no fence of a kind.
NO_FENCE = {
    "proxy": "has one memory proxy: a barrier (__syncthreads) orders shared-memory writes before other threads' reads",
    "operand": "orders its matrix unit's operands in hardware: no fence comes before the next mma",
}
#: The completion of each asynchronous unit's work, per target.
COMPLETIONS = {
    ("sm90", "tma"): Completion("mbarrier", "wait on=mbarrier", ("fence kind=proxy",)),
    ("sm90", "warpgroup"): Completion("wgmma_group", "wait on=wgmma_group", ("fence kind=operand",)),
} | {(arch, "lds"): Completion("lgkmcnt", "wait on=lgkmcnt") for arch in tile.CDNA}


#: The waits and fences a tile program that ran on its hardware issues (alloy_tile_sm90.cuh, tensix_harness.py); every
#: other one is from the ISA manuals alone.
ISSUED = {("sm90", "mbarrier"), ("sm90", "wgmma_group"), ("sm90", "proxy"), ("sm90", "operand"), ("tensix", "noc"),
          ("tensix", "cb")}  # fmt: skip


def manual_check(target: str, name: str) -> Check:
    """The check of a wait or fence: unverified on its own, with whether a checked tile program issues it."""
    if (target, name) in ISSUED:
        return Check("unverified", f"from the ISA manuals; the {target} tile programs that ran issue it")
    return Check("unverified", "from the ISA manuals; no checked program issues it")


def gpu_build(target: str) -> str:
    """The line that compiles a GPU answer's code, saved as alloy.cu (sm90) or alloy.hip (CDNA), with no include path:
    the code carries every helper it calls."""
    if target == "sm90":
        return "nvcc -gencode arch=compute_90a,code=sm_90a -std=c++17 -O2 -c alloy.cu -o alloy.o"
    return f"hipcc --offload-arch={target} -O2 -c alloy.hip -o alloy.o"


def device_code(helpers: str, signature: str, body: str) -> str:
    """One self-contained block: the helpers ``body`` calls, then ``body`` as the device function ``signature``."""
    lines = "".join(f"  {line}\n" for line in body.splitlines())
    return f"{helpers}\n\n__device__ {signature} {{\n{lines}}}\n".lstrip("\n")


def gpu_helpers(target: str) -> str:
    """Alloy's tile helpers of ``target`` without the mma: the barriers, the TMA, the tensor map, the LDS chunk type."""
    if target in DIALECT:
        return tile.inlined(tile.GPU_HEADER[target], frozenset())
    return ""


def wait_answer(request: Request) -> Answer:
    """``wait on=<token>``: the instruction that completes the work a token names."""
    tokens = WAITS.get(request.target, {})
    if not request.on:
        return bad(request, Why.OPERANDS, "wait names the token it waits on", *(f"wait on={t}" for t in tokens))
    if request.on not in tokens:
        reason = (f"{request.target} has no {request.on!r} token" if tokens
                  else f"{request.target} issues no asynchronous work to wait on")  # fmt: skip
        return no(request, Why.NO_ROW, reason, *(f"wait on={t}" for t in tokens))
    spelling, what = tokens[request.on]
    code, setup = spelling, {}
    if request.target in DIALECT:
        mbarrier = "uint64_t& bar, uint32_t& phase" if "&bar" in spelling else ""
        code = device_code(gpu_helpers(request.target), f"void alloy_wait_{request.on}({mbarrier})", spelling)
        setup = {"build": gpu_build(request.target)}
    return Feasible(request, "thread", (Step("thread", spelling),), setup, code,
                    manual_check(request.target, request.on), (what,))  # fmt: skip


def fence_answer(request: Request) -> Answer:
    """``fence kind=<proxy|operand>``: the fence that orders a kind of access before asynchronous work."""
    if request.kind not in NO_FENCE:
        return bad(request, Why.OPERANDS, "fence names its kind", *(f"fence kind={k}" for k in NO_FENCE))
    fences = FENCES.get(request.target, {})
    if request.kind not in fences:
        return no(request, Why.NO_ROW, f"{request.target} {NO_FENCE[request.kind]}")
    spelling, what = fences[request.kind]
    code = device_code(gpu_helpers(request.target), f"void alloy_fence_{request.kind}()", spelling)
    return Feasible(request, "thread", (Step("thread", spelling),), {"build": gpu_build(request.target)}, code,
                    manual_check(request.target, request.kind), (what,))  # fmt: skip


def answered(request: Request, verify: bool) -> Answer:
    if request.target not in UNITS:
        return bad(request, Why.TARGET, f"no target {request.target!r}", *(f"target {t}" for t in TARGETS))
    if request.unit and request.unit not in UNITS[request.target]:
        units = (f"unit {u}" for u in UNITS[request.target])
        return bad(request, Why.UNIT_NAME, f"{request.target} has no unit {request.unit!r}", *units)
    if request.target == "softhier":
        return softhier_op(request)
    if request.op == "wait":
        return wait_answer(request)
    if request.op == "fence":
        return fence_answer(request)
    if request.op == "mma":
        return with_completion(mma(request, verify))
    if request.op == "copy":
        return with_completion(copy(request, verify))
    if request.op in ("load", "store") and {"src", "dst"} <= request.operands.keys():
        return moved(request, verify)
    if request.target in DIALECT:
        return thread_op(request)
    if request.op not in OPS and request.op not in functions():
        return bad(
            request, Why.OPERATION, f"no operation {request.op!r}", "an op of `python -m alloy.isa ops`, mma, or copy"
        )
    if request.max_ulp is not None and request.target == "tensix":
        return sfpi_rung(request)
    if request.max_ulp is not None and request.op not in functions():
        return bad(
            request,
            Why.BOUND,
            f"max_ulp selects a rung of a math kernel; {request.op} is exact",
            "the request without max_ulp",
        )
    if request.target in CPU:
        return vector_op(request, verify)
    if request.target == "tensix":
        return tile_call(request)
    nearest = mma_nearest("sme", 32, 32, 32)
    return no(request, Why.NOT_COVERED, "sme answers mma only so far (step 3 of the design)", *nearest)


def with_completion(answer: Answer) -> Answer:
    """``answer`` with the completion of its unit's asynchronous work, where the unit has one."""
    if not isinstance(answer, Feasible):
        return answer
    found = COMPLETIONS.get((answer.request.target, answer.unit))
    return dataclasses.replace(answer, completion=found) if found else answer


def moved(request: Request, verify: bool) -> Answer:
    """A ``load`` (memory to registers or a tile register) or a ``store`` (back), answered by the rows of ``copy``; a
    move between two memories is a copy, and so is one between two registers."""
    src, dst = request.operands["src"], request.operands["dst"]
    inner, outer = (dst, src) if request.op == "load" else (src, dst)
    if inner.space not in REGISTERS or outer.space in REGISTERS:
        ends = (
            "starts in memory and ends in registers"
            if request.op == "load"
            else "starts in registers and ends in memory"
        )
        reason = f"a {request.op} {ends} (register, vector, or tile_register), not {src.space} to {dst.space}"
        return bad(request, Why.MALFORMED, reason, "copy with the same operands, for a move between two memories")
    answer = copy(dataclasses.replace(request, op="copy"), verify)
    return dataclasses.replace(answer, request=request)


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


def untyped(request: Request, expected: Operand) -> Invalid | None:
    """The refusal of a request with no operand to name its element type, or with operands of mixed types; None."""
    if not request.operands:
        reason = f"{request.op} needs an operand: it names the element type"
        return bad(request, Why.OPERANDS, reason, spell(x=expected))
    if why := mixed(request):
        return bad(request, Why.MIXED_TYPES, why, spell(x=expected))
    return None


def unchained(request: Request, shapes: set[tuple[int, ...]], expected: Operand) -> Invalid | None:
    """The refusal of operands that do not share one shape, or None."""
    if len(shapes) <= 1:
        return None
    reason = f"the operands of {request.op} share one shape; got {', '.join(str(s) for s in sorted(shapes))}"
    return bad(request, Why.CHAIN, reason, spell(x=expected))


def vector_op(request: Request, verify: bool) -> Answer:
    """A CPU operation: the table's row, or the math kernel at the cheapest rung that holds ``max_ulp`` (the strict
    rung where the table has the function without an instruction)."""
    dtype, isa = dtype_of(request), request.target
    table = load()
    lanes = table.isa(isa).lanes.get(dtype, 0)
    register = Operand("vector", dtype, (lanes,) if lanes else ())
    if refusal := untyped(request, register):
        return refusal
    try:
        gate(isa, dtype)
    except KeyError as exc:
        return no(request, Why.ELEMENT_TYPE, str(exc.args[0]), f"target {GATED[isa, dtype]}")
    # a broadcast's source is one scalar: register:<dtype> or register:<dtype>:1
    scalar = request.op == "broadcast" and all(o.shape in ((), (1,)) for o in request.operands.values())
    shapes = set() if scalar else {operand.shape for operand in request.operands.values() if operand.shape}
    if refusal := unchained(request, shapes, register):
        return refusal
    for operand in request.operands.values():
        if operand.space not in ("vector", "register"):
            fix = f"load it first: ask load with src global and dst {register.spelled()}"
            return no(request, Why.SPACE, f"{isa} {request.op} computes on registers, not on {operand.space} memory",
                      spell(x=register), fix=fix)  # fmt: skip
        if operand.swizzle != "none":
            return no(request, Why.SWIZZLE, "a CPU has no swizzle", spell(x=register))
        if (
            len(operand.shape) >= 2 and lanes
        ):  # TODO(design): logical 2-D data on a CPU (owner's batch, isa-design.md 2.8)
            flat = Operand("vector", dtype, (math.prod(operand.shape),))
            near = flat if lanes and not flat.shape[0] % lanes else register
            shape = "x".join(map(str, operand.shape))
            return no(request, Why.SHAPE, f"{isa} {request.op} takes one-dimensional data, not {shape}; a tile is an "
                      "mma or copy operand", spell(x=near), fix="flatten the data into one run of elements",
                      block=(lanes,))  # fmt: skip
        if lanes and operand.shape and operand.shape[0] % lanes and not scalar:
            return uneven(request, isa, dtype, operand.shape[0], lanes)
    answer = one_register(request, isa, dtype, table, verify)
    if not lanes and shapes:  # SVE: the lane count is known at run time only
        return scalable(answer, request, math.prod(next(iter(shapes))), table, dtype)
    count = next(iter(shapes))[0] // lanes if shapes and lanes else 1
    return repeated(answer, request, count, table, isa, dtype)


#: Per SVE element type: the lanes of one register at run time, the vector and scalar C types, the predicate width.
SVE_TYPES = {
    "f64": ("svcntd()", "svfloat64_t", "double", "b64"),
    "f32": ("svcntw()", "svfloat32_t", "float", "b32"),
    "f16": ("svcnth()", "svfloat16_t", "float16_t", "b16"),
    "i64": ("svcntd()", "svint64_t", "int64_t", "b64"),
    "i32": ("svcntw()", "svint32_t", "int32_t", "b32"),
}


def scalable(answer: Answer, request: Request, n: int, table: Table, dtype: str) -> Answer:
    """``answer`` for one SVE register, as the loop over ``n`` elements: blocks of the run-time lane count under the
    svwhilelt predicate, no remainder. A reduction combines the blocks lane-wise into an accumulator (the _m form keeps
    its masked-off lanes) and reduces once; a scan adds the carry of the block before."""
    if not isinstance(answer, Feasible):
        return answer
    lanes, vector, scalar, bits = SVE_TYPES[dtype]
    mask = table.entry("sve", "gen_mask", dtype).intrinsic
    head = f"for (int64_t i = 0; i < {n}; i += {lanes}) {{\n  svbool_t pg = {mask}(i, {n});\n"
    each = f"each block of {lanes} lanes: "
    loop = (f"{n} elements: a loop over blocks of {lanes} lanes (the run-time vector length) under pg = {mask}(i, N); "
            "no remainder loop")  # fmt: skip
    if request.op in REDUCTIONS:
        load_, fill = (table.entry("sve", name, dtype).intrinsic for name in ("load", "broadcast"))
        combine = table.entry("sve", REDUCTIONS[request.op], dtype).intrinsic.replace("_x", "_m")
        reduce_ = table.entry("sve", request.op, dtype).intrinsic
        reduced = (Step("vector", f"{each}{mask}(i, N)"), Step("vector", f"{each}{load_}"),
                 Step("vector", f"{each}{combine} into the accumulator (_m: its masked-off lanes stay)"),
                 Step("vector", reduce_))  # fmt: skip
        code = (f"{vector} acc = {fill}({IDENTITY[request.op]});\n{head}  acc = {combine}(pg, acc, {load_}(pg, x + i));"
                f"\n}}\n{scalar} s = {reduce_}(svptrue_{bits}(), acc);")  # fmt: skip
        note = f"{loop}; the lanes combine in another order than a scalar left fold"
        return dataclasses.replace(answer, steps=reduced, code=code, notes=(*answer.notes, note))
    steps: tuple[Step, ...] = (
        Step("vector", f"{each}{mask}(i, N)"),
        *(Step("vector", each + s.spelling) for s in answer.steps),
    )
    body = "".join(f"  {line}\n" for line in answer.code.splitlines())
    before, after = "", ""
    if answer.notes and answer.notes[0].startswith("rung "):  # a math kernel: its function, then a call per block
        before, body = f"{answer.code}\n", f"  v = {answer.steps[0].spelling}(v);\n"
    if request.op in SCANS:
        carry = LAST_LANE["sve", dtype].replace(", t)", ", v)")
        add = table.entry("sve", SCANS[request.op], dtype).intrinsic
        steps += (Step("vector", f"{each}{add}(pg, v, c)"), Step("vector", f"{each}{carry}"))
        before = f"{vector} c = {table.entry('sve', 'broadcast', dtype).intrinsic}(0);\n"
        after = f"  v = {add}(pg, v, c);  // the carry of the blocks before\n  c = {carry};\n"
    code = f"{before}{head}  // the operands of block i, loaded under pg; then\n{body}{after}}}"
    return dataclasses.replace(answer, steps=steps, code=code, notes=(*answer.notes, loop))


def one_register(request: Request, isa: str, dtype: str, table: Table, verify: bool) -> Answer:
    """``request`` on one register of ``isa``: the table's row, or the math kernel."""
    if request.op in functions() and (request.op not in OPS or request.max_ulp is not None):
        return math_kernel(request, isa, dtype, verify)
    try:
        entry = table.entry(isa, request.op, dtype)
    except KeyError as exc:
        others = (Operand("vector", d, (n,) if n else ()) for d, n in table.isa(isa).lanes.items() if d != dtype)
        return no(request, Why.NO_ROW, str(exc.args[0]), *(spell(x=o) for o in others))
    if not entry.intrinsic and not entry.recipe:
        if request.op in functions():
            return math_kernel(request, isa, dtype, verify)
        return no(request, Why.NO_ROW, f"{isa} has no instruction or recipe for {request.op} on {dtype}")
    steps = (Step("vector", entry.intrinsic),) if entry.intrinsic else tuple(Step("vector", s) for s in entry.recipe)
    check = Check("unverified")
    if verify:
        from alloy.isa.validate import validate

        verdict = validate(isa, request.op, dtype, table)
        if verdict.ok is False:
            return no(request, Why.CHECK_FAILED, f"the row failed its check: {verdict.detail}")
        check = Check("run" if verdict.ok else "unverified", verdict.basis)
    notes = (entry.note,) if entry.note else ()
    return Feasible(request, "vector", steps, cpu_setup(isa, dtype, table, entry), statement(entry), check, notes)


def statement(entry: Entry) -> str:
    """The row as C on the operand names of its signature, ending in its result: ``v = _mm512_add_pd(a, b);``."""
    operands, _, result = entry.signature.partition("->")
    if not entry.code and not entry.intrinsic:
        return f"/* {' then '.join(entry.recipe)} on {entry.signature} */"
    *lines, last = entry.code or (f"{entry.intrinsic}{operands.strip()}",)
    done = last if result.strip() in ("", "void") else f"{result.strip()} = {last}"
    return "".join(f"{line};\n" for line in lines) + f"{done};"


def cpu_setup(isa: str, dtype: str, table: Table, entry: Entry | None = None) -> dict[str, str]:
    """What a CPU answer needs around its code: the header and the compiler flags, and on AVX-512 the row's masked
    form for the last block with the mask it takes."""
    flags = " ".join(c_flags(isa, dtype)) or f"none: {isa} is in the target's baseline"
    compiler = "aarch64-linux-gnu-gcc" if isa in ("neon", "sve") else "gcc"
    setup = {"header": f"#include <{HEADERS[isa]}>", "flags": flags,
             "build": " ".join([compiler, "-O2", *c_flags(isa, dtype), "-c", "alloy.c", "-o", "alloy.o"])}  # fmt: skip
    if isa in ("neon", "sve"):
        setup["tune"] = "-mcpu=neoverse-v2 for Grace (GH200), on a native compiler"
    mask = table.isa(isa).entries(dtype).get("gen_mask")
    if entry is not None and mask is not None and (entry.masked or entry is mask):
        if entry.masked:
            setup["masked"] = f"{entry.masked}: the last block, under the mask k"
        setup["mask"] = f"k = {mask.intrinsic}{mask.signature.partition('->')[0].strip()}: {mask.semantics}"
    return setup


def math_kernel(request: Request, isa: str, dtype: str, verify: bool) -> Answer:
    """The rung of the function with the fewest intrinsics within ``max_ulp`` (the strict rung without a bound);
    ``verify`` runs the kernel gate (``mathcheck.validate_kernel``) on it."""
    try:
        if request.max_ulp is None:
            spelled = render(kernel(request.op, dtype, "strict"), target_of(isa))
        else:
            spelled = cheapest(request.op, dtype, target_of(isa), max_ulp=request.max_ulp)
    except KeyError as exc:
        return no(request, Why.NO_RUNG, str(exc.args[0]))
    k = spelled.kernel
    others = [f"{r.level} {r.error_ulp:.4g} ulp" for r in ladder(k.fn, dtype) if r.level != k.level]
    notes = (
        f"rung {k.level}: {k.error_ulp:.4g} ulp, {spelled.intrinsics} intrinsics, contract: {k.contract}",
        # an agent whose own bound is tighter or looser sees the other rungs and asks again with --max-ulp
        (
            f"other rungs (a more accurate rung costs more instructions): {', '.join(others) or 'none'}; "
            "ask again with --max-ulp to get one"
        ),
    )
    check = Check("unverified", "not checked (verify off)")
    if verify:
        from alloy.isa.mathcheck import validate_kernel

        verdict = validate_kernel(k.fn, dtype, k.level, isa)
        if verdict.ok is False:
            return no(request, Why.CHECK_FAILED, f"the {k.level} kernel failed its check: {verdict.detail}")
        status: Literal["run", "compiled", "unverified"] = (
            "run" if verdict.ok else "compiled" if verdict.detail == "builds" else "unverified"
        )
        check = Check(status, f"{verdict.basis}: {verdict.detail}" if verdict.detail else verdict.basis)
    setup = cpu_setup(isa, dtype, load()) | {"header": f"#include <{HEADERS[isa]}> and <math.h>"}
    code = f"#include <{HEADERS[isa]}>\n#include <math.h>\n{spelled.source}"  # standalone with its build line
    return Feasible(request, "vector", (Step("vector", k.name),), setup, code, check, notes)


#: Bytes per element of the SIMT rows' element types.
SIMT_BYTES = {"f32": 4, "f16": 2, "bf16": 2}


def per_thread(row: simt.Row) -> int:
    """Elements one thread moves with a load or store row: 16 bytes for a wide row, two for a pair, else one."""
    if row.kind == "thread" and row.answers().endswith("_wide"):  # the f32 load_wide row reads one float
        return 16 // SIMT_BYTES[row.dtype]
    return 2 if row.answers().endswith("_x2") else 1


def moves(row: simt.Row) -> bool:
    return row.answers().split("_")[0] in ("load", "store")


def thread_op(request: Request) -> Answer:
    """A GPU operation of one thread or one warp: its SIMT row at the request's element type, with the recorded check.
    A load or store of N elements in global memory takes the widest row whose elements per thread divide N."""
    dialect = DIALECT[request.target]
    rows = simt.rows()
    named = [r for r in rows if request.op in (r.op, r.answers())]
    if request.op in ("load", "store"):  # the family: scalar, pair, and 16-byte rows
        named = [r for r in rows if moves(r) and r.answers().startswith(request.op)]
    if not named:
        names = list(dict.fromkeys(r.answers() for r in rows))
        related = [op for op in names if request.op in op] or difflib.get_close_matches(request.op, names, n=3)
        nearest = related or names  # the related rows, else every row
        tail = "a GPU loop tail is a per-thread bounds check (if (i < n)); ballot_count counts the lanes of a predicate"
        fix = tail if request.op == "gen_mask" else ""
        return no(request, Why.NO_ROW, f"no {dialect} row for {request.op}",
                  *(f"{request.target} {op}" for op in nearest), fix=fix)  # fmt: skip
    dtype = dtype_of(request) if request.operands else named[0].dtype
    typed = [r for r in named if r.dtype == dtype]
    space: Space = "global" if moves(named[0]) else "register"
    if not typed:
        dtypes = sorted({r.dtype for r in named})
        return no(request, Why.ELEMENT_TYPE, f"the {request.op} row computes in {', '.join(dtypes)}, not {dtype}",
                  *(spell(x=Operand(space, d)) for d in dtypes))  # fmt: skip
    if why := mixed(request):
        return bad(request, Why.MIXED_TYPES, why, spell(x=Operand(space, dtype)))
    row, count = typed[0], 1
    if moves(row):
        found = memory_row(request, typed, dtype)
        if not isinstance(found, tuple):
            return found
        row, count = found
    else:
        scalar = Operand("register", row.dtype)
        for operand in request.operands.values():
            if len(operand.shape) >= 2 or operand.swizzle != "none":
                return no(request, Why.SHAPE, f"{request.op} is a row of one thread on scalars; a tile is an mma or "
                          "copy operand", spell(x=scalar), block=(1,))  # fmt: skip
            if operand.space != "register":
                group = "wavefront" if dialect == "hip" else "warp"
                held = f"one register per lane of a {group}" if row.kind == "warp" else "one thread's registers"
                return no(request, Why.SPACE, f"the {request.op} row computes on {held}, not on {operand.space} "
                          "memory", spell(x=scalar), fix="load the value into a register first")  # fmt: skip
    if request.max_ulp is not None:
        return bad(request, Why.BOUND, "max_ulp selects a rung of a math kernel; a device row has one accuracy",
                  "the request without max_ulp")  # fmt: skip
    verdict = simt.verdicts().get((row.op, dialect))
    if verdict is not None and verdict.ok is False:
        return no(request, Why.CHECK_FAILED, f"the row failed its check: {verdict.error or verdict.basis}")
    spelling = row.spelled(dialect)
    check = Check("unverified") if verdict is None else Check("run" if verdict.ok else "compiled", verdict.basis)
    unit = ("wave" if dialect == "hip" else "warp") if row.kind == "warp" else "thread"  # a CDNA warp is a wavefront
    spread = (f"{count * per_thread(row)} elements: {count} threads, {per_thread(row)} each",) if count > 1 else ()
    notes = (*((row.note,) if row.note else ()), *spread, simt.bindings(dialect))
    setup = {"build": gpu_build(request.target)}
    return Feasible(request, unit, (Step(unit, spelling, count),), setup, row_code(row, dialect), check, notes)


def row_code(row: simt.Row, dialect: str) -> str:
    """A SIMT row as one device function that compiles on its own: the names its code uses are the parameters and the
    locals ``bindings`` describes, and it returns ``out``."""
    headers = [*(["hip/hip_runtime.h"] if dialect == "hip" else []), *simt.table()["target"][dialect]["headers"]]
    preamble = "\n".join(f"#include <{h}>" for h in headers) + f"\ntypedef {simt.ELEMENTS[dialect, row.dtype][0]} elem;"
    body = f"out = {row.spelled(dialect)};" if row.kind == "lane" else f"{row.spelled(dialect)}\n{row.read}".rstrip()
    signature = (f"float alloy_{row.op}(float v, float a, float b, float c, const elem* x, elem* y, const float* wide, "
                 "float* total)")  # fmt: skip
    locals_ = ("const int lanes = warpSize, lane = threadIdx.x % warpSize, i = blockIdx.x * blockDim.x + threadIdx.x;"
               "\nfloat out = 0.0f;")  # fmt: skip
    return device_code(preamble, signature, f"{locals_}\n{body}\nreturn out;")


def memory_row(request: Request, typed: list[simt.Row], dtype: str) -> tuple[simt.Row, int] | Answer:
    """The load or store row for the request's global data and how many threads run it: the widest row whose
    elements per thread divide the extent."""
    if not request.operands:  # the row itself: one thread's move
        return typed[0], 1
    shapes = {o.shape for o in request.operands.values()}
    for operand in request.operands.values():
        if operand.space != "global":
            return no(request, Why.SPACE, f"a {request.op} row moves {dtype} between global memory and registers; "
                      f"name the data in memory, not {operand.space}", spell(x=Operand("global", dtype, (1024,))))  # fmt: skip
        if len(operand.shape) >= 2 or operand.swizzle != "none":
            return no(request, Why.SHAPE, f"{request.op} moves a run of elements; a tile is a copy operand",
                      spell(x=Operand("global", dtype, (math.prod(operand.shape),))), block=(1,))  # fmt: skip
    if refusal := unchained(request, shapes, Operand("global", dtype, (1024,))):
        return refusal
    n = math.prod(next(iter(shapes), ()))
    widest = sorted(typed, key=per_thread, reverse=True)
    for row in widest:
        if n % per_thread(row) == 0:
            return row, n // per_thread(row)
    width = per_thread(widest[-1])
    sizes = [size for size in (n - n % width, n - n % width + width) if size]
    return no(request, Why.SHAPE, f"the {request.op} row moves {width} {dtype} per thread; {n} is no whole multiple",
              *(spell(x=Operand("global", dtype, (size,))) for size in sizes), block=(width,),
              fix="guard the last thread's elements with a bounds check (if (i < n)), or pad the data")  # fmt: skip


def ttsim_check(row: tensix.Row, dtype: str) -> Check | str:
    """A Tensix row's check from its current ttsim record, or why it is refused: a pending row, or one without a
    current record, is unverified (a stale failure never refuses it); a failed run refuses it."""
    verdict = None if row.pending else tensix.verdicts().get((row.op, dtype, row.unit))
    if verdict is None:
        return Check("unverified", "pending a ttsim run (the tensix CI job runs it)")
    if not verdict.ok:
        return f"the row failed its check on ttsim: {verdict.error or 'outside its error bound'}"
    return Check("run", "ttsim")


def tile_call(request: Request) -> Answer:
    """A Tensix operation on one 32 x 32 tile: its tile calls on the unit that has the operation, with ttsim's
    recorded check."""
    dtype = dtype_of(request)
    rows = [r for r in tensix.rows() if r.op == request.op]
    if not rows and request.op == "reduce_min":
        return no(request, Why.NO_ROW, "Tensix reduce_tile pools SUM, AVG, and MAX; it has no MIN", "tensix neg",
                  "tensix reduce_max", fix="negate the tiles (negative_tile), reduce_max, and negate the result")  # fmt: skip
    if not rows:
        return no(
            request, Why.NO_ROW, f"no Tensix row for {request.op}", *sorted({f"tensix {r.op}" for r in tensix.rows()})
        )
    found = [r for r in rows if not request.unit or r.unit.lower() == request.unit]
    if dtype == "f32":  # the SFPU keeps f32 in DST; the FPU reads its sources at TF32 (19 bits)
        found.sort(key=lambda r: r.unit.lower() != "sfpu")
    if not found:
        units = sorted({r.unit.lower() for r in rows})
        return no(
            request,
            Why.UNIT,
            f"tensix {request.op} runs on {', '.join(units)}, not {request.unit}",
            *(f"unit {u}" for u in units),
        )
    one = Operand("tile_register", dtype if dtype in tensix.dtypes() else "f32", (32, 32))
    if refusal := untyped(request, one):
        return refusal
    if dtype not in tensix.dtypes():
        return no(request, Why.ELEMENT_TYPE, f"Tensix computes {', '.join(tensix.dtypes())}, not {dtype}", spell(x=one))
    if any(o.space != "tile_register" for o in request.operands.values()):
        return no(request, Why.SPACE, "a Tensix tile call computes on the unit's tile registers", spell(x=one),
                  fix=INTO_SPACE["tensix"])  # fmt: skip
    shapes = {o.shape for o in request.operands.values() if o.shape}
    if refusal := unchained(request, shapes, one):
        return refusal
    shape = next(iter(shapes), (32, 32))
    if refused := untiled(request, shape, one.dtype):
        return refused
    tiles = (shape[0] // 32) * (shape[1] // 32)
    row = found[0]
    if row.kind == "scan" and shape[1] > 32:  # first = (i == 0) restarts the total only at the top of one column
        return no(request, Why.SHAPE, "the checked scan runs down one column of tiles (cumsum_tile with first set "
                  "on its top tile); a wider shape needs first set at the top of every column, which is not checked",
                  spell(x=Operand("tile_register", dtype, (shape[0], 32))), fix="ask one 32-wide column at a time",
                  block=(32, 32))  # fmt: skip
    check = ttsim_check(row, dtype)
    if isinstance(check, str):
        return no(request, Why.CHECK_FAILED, check)
    init, call = tensix.spelled(row.init, "v08"), tensix.spelled(row.call, "v08")
    unit = row.unit.lower()
    once = row.kind in ("scan", "reduction")  # one init: the state stays in the unit from tile to tile
    each = "one init, then one call per tile" if once else "the init before each tile's call, as the checked program"
    notes = (
        *((row.note,) if row.note else ()),
        *((card.strip(),) if (card := tensix.card_line(row, dtype)) else ()),
        *((f"{tiles} tiles: {each}",) if tiles > 1 else ()),
        *(("the FPU reads its sources at TF32 (19 bits): about 1e-3 relative error in f32; unit sfpu keeps f32",)
          if unit == "fpu" and dtype == "f32" else ()),
        *(f"{r.name}, an SFPI kernel of {r.op} at {r.error_ulp:.3g} ulp on the card: ask with --max-ulp "
          f"{math.ceil(r.error_ulp)}" for r in tensix.rungs(row.op, dtype)[:1]),
    )  # fmt: skip
    steps: tuple[Step, ...] = (Step(unit, init, 1 if once else tiles), Step(unit, call, tiles))
    if row.kind == "reduction":  # every tile into one DST tile, packed once; the harness runs it so
        steps += (Step(unit, "pack_tile(0, c16)"),)
    return Feasible(request, unit, steps, tensix_setup(row, dtype), f"{init};\n{call};", check, notes)


def untiled(request: Request, shape: tuple[int, ...], dtype: str) -> Infeasible | None:
    """The refusal of a Tensix ``shape`` that is no whole number of 32x32 tiles, with the sizes below and above;
    None."""
    if len(shape) == 2 and not shape[0] % 32 and not shape[1] % 32:
        return None
    sizes = {tuple(max(32, e - e % 32) for e in shape[:2]), tuple(-(-e // 32) * 32 for e in shape[:2])}
    near = (spell(x=Operand("tile_register", dtype, s)) for s in sorted(sizes) if len(s) == 2)
    reason = (
        f"a Tensix tile call computes one 32x32 tile at a time; {'x'.join(map(str, shape))} is no whole number of tiles"
    )
    return no(request, Why.SHAPE, reason, *near, fix="pad the data to whole 32x32 tiles", block=(32, 32))


def tensix_setup(row: tensix.Row, dtype: str) -> dict[str, str]:
    """What the host sets for Tensix ``row`` at ``dtype``: its header, the compute config, and a reduction's scaler."""
    setup = {"header": row.header}
    if dtype == "f32":  # without these, f32 data passes DST at bf16 precision (tensix.toml's target note)
        setup["compute config"] = "fp32_dest_acc_en = true, math_fidelity = HiFi4" + (
            "; unpack_to_dest_mode UnpackToDestFp32 for the CBs copied into DST" if row.unit.lower() == "sfpu" else ""
        )
    if row.kind == "reduction":
        setup |= {"compute config": "fp32_dest_acc_en = true, math_fidelity = HiFi4",
                  "scaler": "one tile in CB c1: 1 in the first row of each 16x16 face"}  # fmt: skip
    return setup


def sfpi_rung(request: Request) -> Answer:
    """The most accurate Tensix math kernel on SFPU lanes (tensix.toml's rungs) within ``max_ulp``, checked on a
    Blackhole: its full source, which the compute kernel inlines, and the calls that run it on DST tile 0."""
    dtype = dtype_of(request)
    found = tensix.rungs(request.op, dtype)
    if not found:
        reason = f"no SFPI rung for {request.op} on {dtype}; a Tensix tile call has one accuracy"
        return bad(request, Why.BOUND, reason, "the request without max_ulp")
    within = [r for r in found if request.max_ulp is not None and r.error_ulp <= request.max_ulp]
    if not within:
        best = found[0]
        return no(request, Why.NO_RUNG, f"the most accurate {request.op} rung, {best.name}, holds "
                  f"{best.error_ulp:.3g} ulp on the card", f"max_ulp {best.error_ulp:.3g}")  # fmt: skip
    rung = within[-1]  # the loosest within the bound: rungs are sorted most accurate first
    steps = (Step("sfpu", rung.init, 1), Step("sfpu", rung.call, 1))
    setup = {
        "header": "compute_kernel_api.h (under TRISC_MATH it brings sfpi and the llk SFPU helpers)",
        "compute config": "fp32_dest_acc_en = true, math_fidelity = HiFi4; unpack_to_dest_mode UnpackToDestFp32 "
        "for the CBs copied into DST",
    }
    notes = (f"rung {rung.name}: {rung.error_ulp:.3g} ulp, measured on the card ({rung.card})", rung.note)
    return Feasible(request, "sfpu", steps, setup, rung.code, Check("run", f"card: {rung.card}"), notes)


def mma_nearest(target: str, m: int, n: int, k: int, in_type: str = "f16") -> tuple[str, ...]:
    """The mma requests ``target`` takes that are closest to an ``m`` x ``n`` x ``k`` product: of ``in_type`` when the
    target takes it, else of every input type it takes."""
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
    types = [t for t in tile.TYPES[target] if t[0] == in_type] or list(tile.TYPES[target])
    return tuple(request(i, o, bm, bn, tile.k_block(i)) for i, o in types for bm, bn in tile.GPU_TILES[target])


#: How a caller moves an mma input into the space its target reads, by target.
INTO_SPACE = {
    "sm90": "load it into shared memory first: ask copy with src global and dst shared:<type>:<rows>x<128 bytes of "
    "the type: 64 f16 or bf16, 128 e4m3 or e5m2>:row_major:b128 (TMA)",
    "gfx942": "load it into LDS first: ask copy with src global and dst shared:<type>:<rows>x<128 bytes of the type: "
    "64 f16 or bf16, 128 e4m3 or e5m2>:row_major:xor:8",
    "cpu": "the fallback reads memory through pointers: pass the arrays as global",
    "sme": "FMOPA reads its vectors from memory: pass the arrays as global",
    "tensix": "the reader kernel sends each tile into a circular buffer: pass tiles as tile_register",
}
INTO_SPACE["gfx90a"] = INTO_SPACE["gfx942"]
#: How a caller gives an mma input the swizzle its target reads.
INTO_SWIZZLE = {
    "sm90": "the kernel's wgmma descriptor reads 128B-swizzled rows: fill the tile with the TMA copy (dst swizzle "
    "b128, tensor map SWIZZLE_128B), and ask the mma with that swizzle",
    "gfx942": "the kernel reads LDS chunk c of row r at slot c ^ (r % 8): fill the tile with the LDS copy (dst swizzle "
    "xor:8), and ask the mma with that swizzle",
}
INTO_SWIZZLE["gfx90a"] = INTO_SWIZZLE["gfx942"]
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
INTO_LAYOUT["gfx90a", "b"] = INTO_LAYOUT["gfx942", "b"]


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
        target = "cpu" if request.target in CPU else request.target
        return bad(request, Why.OPERANDS, "mma takes operands a (M x K), b (K x N), and c (M x N)",
                   *mma_nearest(target, 64, 64, 64, next(iter(ops.values())).dtype if ops else "f16"))  # fmt: skip
    a, b, c = ops["a"], ops["b"], ops["c"]
    target = "cpu" if request.target in CPU else request.target
    if len(a.shape) != 2 or len(b.shape) != 2 or a.shape[1] != b.shape[0] or c.shape != (a.shape[0], b.shape[1]):
        reason = f"shapes do not chain: a {a.shape}, b {b.shape}, c {c.shape}; a is M x K, b K x N, c M x N"
        return bad(request, Why.CHAIN, reason, *mma_nearest(target, 64, 64, 64, a.dtype))
    m, k, n = a.shape[0], a.shape[1], b.shape[1]
    nearest = mma_nearest(target, m, n, k, a.dtype)
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
        code = Why.SHAPE if (a.dtype, c.dtype) in tile.TYPES[target] else Why.ELEMENT_TYPE
        gpu_shape = code is Why.SHAPE and target in tile.GPU_TILES
        block = (*next(iter(tile.GPU_TILES[target])), tile.k_block(a.dtype)) if gpu_shape else ()
        return no(request, code, str(exc.args[0]), *nearest, block=block)
    if misplaced_ := misplaced(target, a, b, c):
        return no(request, *misplaced_[:2], *nearest, fix=misplaced_[2])
    if verify:
        found = tile.verify(found)
        if found.verified == "failed":
            return no(request, Why.CHECK_FAILED, f"the tile program failed its check: {found.detail}")
    unit = ({"cpu": "vector", "sme": "za", "sm90": "warpgroup"} | dict.fromkeys(tile.CDNA, "mfma"))[target]
    check = Check(found.verified, found.detail)  # type: ignore[arg-type]
    steps = tuple(Step(unit, s) for s in found.steps)
    return Feasible(request, unit, steps, dict(found.descriptors), found.program, check, (found.layout,))


def tensix_mma(request: Request, m: int, n: int, k: int, nearest: tuple[str, ...]) -> Answer:
    """A Tensix matrix product: ``matmul_tiles`` on the FPU, one call per K tile, accumulated in DST, for every
    32 x 32 output tile; f32 operands are read at TF32."""
    a, b, c = (request.operands[name] for name in "abc")
    if m % 32 or n % 32 or k % 32:
        return no(request, Why.SHAPE, f"Tensix multiplies 32x32 tiles; got {m}x{n}x{k}", *nearest, block=(32, 32, 32))
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
    check = ttsim_check(row, a.dtype)
    if isinstance(check, str):
        return no(request, Why.CHECK_FAILED, check)
    tiles = (m // 32) * (n // 32)
    steps = (Step("fpu", tensix.spelled(row.init, "v08")), Step("fpu", tensix.spelled(row.call, "v08"), tiles * (k // 32)),
             Step("fpu", "pack_tile(0, c16)", tiles))  # fmt: skip
    setup = {"header": row.header, "compute config": "fp32_dest_acc_en = true, math_fidelity = HiFi4",
             "reader": "per output tile (mt, nt), for kt: A tile mt*Kt+kt into CB 0, B tile kt*Nt+nt into CB 1"}  # fmt: skip
    code = f"{tensix.spelled(row.init, 'v08')};\n// per output tile: tile_regs_acquire(); for kt: {tensix.spelled(row.call, 'v08')}; ..."
    notes = (("f32 operands reach the FPU as TF32 (A 10 mantissa bits, B 9 at HiFi4); 0.6x spells "
             f"{tensix.spelled(row.init, 'v06')} and {tensix.spelled(row.call, 'v06')}"),)  # fmt: skip
    return Feasible(request, "fpu", steps, setup, code, check, notes)


def copy_check(target: str, verify: bool, dtype: str = "f16") -> Check | None:
    """The check of a GPU copy: the copy has no program of its own, so it is the check of the smallest tile program
    that runs it (None when that program failed)."""
    if not verify:
        return Check("unverified", f"runs inside the {target} tile program; not checked (verify off)")
    k = tile.k_block(dtype)
    found = tile.verify(tile.plan(target, 64, 64, k, dtype, "f32"))
    if found.verified == "failed":
        return None
    return Check(found.verified, f"the {target} 64x64x{k} {dtype} tile program that runs this copy: {found.detail}")  # type: ignore[arg-type]


def covering(src: Operand, box: tuple[int, ...], width: int, dtype: str) -> tuple[int, int]:
    """The global tile a nearest request names: ``src``'s extents grown to hold one box (rows) and one K block
    (columns, whole K blocks), so the request it names is itself feasible."""
    rows, cols = src.shape if len(src.shape) == 2 and src.dtype == dtype else (256, 256)
    return max(rows, box[0]), -(-max(cols, width) // width) * width


def copy(request: Request, verify: bool) -> Answer:
    """A copy between two spaces: a CPU's vector load or store, sm_90's TMA into a 128B-swizzled shared tile, or
    CDNA's XOR-swizzled LDS stores. A copy converts nothing, so both sides share one element type."""
    ops = request.operands
    if not {"src", "dst"} <= ops.keys():
        return bad(request, Why.OPERANDS, "copy takes operands src and dst")
    src, dst = ops["src"], ops["dst"]
    if request.target in CPU:
        return cpu_copy(request, src, dst)
    if request.target not in tile.GPU_TILES:  # sme, tensix: no copy row yet
        return no(request, Why.NOT_COVERED, f"no checked row covers a {request.target} copy from {src.space} to "
                  f"{dst.space}")  # fmt: skip
    taken = [i for i, _ in tile.TYPES[request.target]]
    dtype = dst.dtype if dst.dtype in taken else "f16"  # the type of the nearest requests
    width = tile.k_block(dtype)
    box = dst.shape if len(dst.shape) == 2 and dst.shape[0] in (64, 128) else (64, width)
    source = Operand("global", dtype, covering(src, box, width, dtype))
    if request.target == "sm90" and src.space == "global":
        return tma_copy(request, src, dst, source, verify)
    if request.target in tile.CDNA and (src.space, dst.space) == ("global", "shared"):
        return lds_copy(request, src, dst, Operand("shared", dtype, (box[0], width), "row_major", "xor:8"), source,
                        verify)  # fmt: skip
    return no(
        request,
        Why.NOT_COVERED,
        f"no checked row covers a {request.target} copy from {src.space} to {dst.space}",
        fix="write it as plain device code, each thread moving its own elements, and check it with score",
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
    op = "load" if dst is register else "store"
    moved_, held = math.prod(register.shape), math.prod(memory.shape)
    if register.shape and memory.shape and held < moved_:
        side = "src" if memory is src else "dst"
        return no(request, Why.SHAPE, f"{side} holds {held} elements, fewer than the {moved_} the {op} moves", *nearest)
    if lanes and register.shape and register.shape[-1] % lanes:  # rows of a tile are whole registers
        return uneven(request, request.target, register.dtype, register.shape[-1], lanes, "src", "dst", op=op)
    whole = Operand("vector", register.dtype, (moved_,) if register.shape else one.shape)
    answer = vector_op(Request(request.target, op, {"x": whole}), verify=False)
    if isinstance(answer, Feasible) and register.shape and memory.shape and held > moved_:
        block = f"a block of {moved_} of the {held} elements: offset the pointer by the block's start"
        answer = dataclasses.replace(answer, notes=(*answer.notes, block))
    return dataclasses.replace(answer, request=request)


def tma_copy(request: Request, src: Operand, dst: Operand, source: Operand, verify: bool) -> Answer:
    """sm_90's TMA: one box of a row-major global tile (f16, bf16, e4m3, or e5m2) into a 128B-swizzled shared tile."""
    taken = [i for i, _ in tile.TYPES["sm90"]]
    dtype = source.dtype
    width = tile.k_block(dtype)
    rows = dst.shape[0] if len(dst.shape) == 2 and dst.shape[0] in (64, 128) else 64
    nearest = spell(src=source, dst=Operand("shared", dtype, (rows, width), "row_major", "b128"))
    if dst.space != "shared":
        return no(request, Why.SPACE, f"TMA writes shared memory only, not {dst.space}", nearest)
    if dst.dtype not in taken:
        return no(request, Why.ELEMENT_TYPE, f"the checked TMA load fills {', '.join(taken)} tiles with the 128B "
                  f"swizzle, not {dst.dtype}", nearest)  # fmt: skip
    if dst.swizzle != "b128":
        return no(request, Why.SWIZZLE, f"the checked TMA load fills a {dtype} tile with the 128B swizzle", nearest)
    if dst.shape not in ((64, width), (128, width)):
        return no(request, Why.SHAPE, f"a TMA box here is 128 bytes wide ({width} {dtype}) and 64 or 128 rows",
                  nearest)  # fmt: skip
    if src.dtype != dst.dtype:
        return bad(request, Why.MIXED_TYPES, f"TMA converts nothing: src is {src.dtype}, dst is {dst.dtype}", nearest)
    if (
        len(src.shape) != 2
        or src.shape[0] < dst.shape[0]
        or src.shape[1] < dst.shape[1]
        or (
            src.shape[1] * tile.GPU_BYTES[dtype] % 16  # the tensor map's row stride is a multiple of 16 bytes
        )
    ):
        return no(
            request,
            Why.SHAPE,
            f"the tensor map describes a two-dimensional global tile at least the box {dst.shape}, whose rows are a "
            "whole multiple of 16 bytes",
            nearest,
        )
    if src.swizzle != "none":
        return no(request, Why.SWIZZLE, "TMA reads an unswizzled global tile", nearest)
    if src.layout != "row_major" or dst.layout != "row_major":
        return no(request, Why.LAYOUT, "the checked TMA load copies row-major tiles", nearest)
    map_type, size = {"f16": "FLOAT16", "bf16": "BFLOAT16"}.get(dtype, "UINT8"), tile.GPU_BYTES[dtype]
    setup = {"tensor map": f"alloy_make_tmap<{tile.ELEM[dtype]}>(&map, global, rows, K, {rows}): {map_type}, box "
             f"{{{width}, {rows}}}, SWIZZLE_128B; the global address 16-byte aligned, K * {size} a multiple of 16",
             "shared tile": f"__shared__ alignas(1024) uint8_t tile[{rows} * 128] (the 128B swizzle needs 1024-byte "
             "alignment)", "barrier": "__shared__ alignas(8) uint64_t bar, initialized by one thread, then "
             "fence.proxy.async.shared::cta"}  # fmt: skip
    if dtype in tile.FP8_NAMES["sm90"]:
        setup["type"] = tile.type_note("sm90", dtype)
    setup["launch"] = (
        f"as the tile program: grid dim3(N / BN, M / BM), {tile.GPU_THREADS['sm90', rows]} threads per block (one "
        f"warpgroup per 64 rows); one elected thread (threadIdx.x == 0) issues the TMA, and every thread then waits"
    )
    # the wait is the completion's own request (wait on=mbarrier): the copy only issues
    steps = (Step("tma", f"mbarrier.arrive.expect_tx with {rows * 128} bytes"),
             Step("tma", "cp.async.bulk.tensor.2d.shared::cluster.global.mbarrier::complete_tx::bytes"))  # fmt: skip
    issue = (f"if (threadIdx.x == 0) {{ alloy_mbar_arrive_expect_tx(bar, {rows * 128}); "
             "alloy_tma_load_2d(tile, map, bar, k0, row0); }")  # fmt: skip
    signature = "void alloy_copy_tma(void* tile, const CUtensorMap* map, uint64_t* bar, int k0, int row0)"
    code = device_code(gpu_helpers("sm90"), signature, issue)
    setup["build"] = gpu_build("sm90")
    if (check := copy_check("sm90", verify, dtype)) is None:
        return no(request, Why.CHECK_FAILED, "the sm90 tile program that runs this copy failed its check")
    return Feasible(request, "tma", steps, setup, code, check)


#: Check statuses from the weakest.
STRENGTH = {"unverified": 0, "compiled": 1, "run": 2}


def lds_copy(request: Request, src: Operand, dst: Operand, tile_: Operand, source: Operand, verify: bool) -> Answer:
    """CDNA's copy of one 64-row K block from global memory into an LDS tile, each 16-byte chunk at the XOR-swizzled
    slot the mma reads; ``tile_`` and ``source`` are the nearest request's operands."""
    taken = [i for i, _ in tile.TYPES[request.target]]
    dtype = tile_.dtype
    width = tile.k_block(dtype)
    nearest = spell(src=source, dst=tile_)
    if src.dtype != dst.dtype:
        return bad(request, Why.MIXED_TYPES, f"a copy converts nothing: src is {src.dtype}, dst is {dst.dtype}",
                   nearest)  # fmt: skip
    if dst.dtype not in taken:
        return no(request, Why.ELEMENT_TYPE, f"the checked LDS load copies {', '.join(taken)} tiles on "
                  f"{request.target}, not {dst.dtype}", nearest)  # fmt: skip
    if len(dst.shape) != 2 or dst.shape != (64, width):
        return no(request, Why.SHAPE, f"the checked LDS load fills a tile of 64 rows of 128 bytes ({width} "
                  f"{dtype}, 8 chunks of 16 bytes)", nearest)  # fmt: skip
    row_bytes = src.shape[1] * tile.GPU_BYTES[dtype] if len(src.shape) == 2 else 0
    if len(src.shape) != 2 or src.shape[0] < 64 or src.shape[1] < width or row_bytes % 16:
        return no(request, Why.SHAPE, f"the LDS load reads one 64 x {width} box of a row-major global tile whose "
                  "rows are whole 16-byte chunks: the source must hold the box", nearest)  # fmt: skip
    if dst.swizzle != "xor:8" or src.swizzle != "none":
        return no(request, Why.SWIZZLE, "the checked LDS load stores each chunk at slot chunk ^ (row % 8) (dst "
                  "swizzle xor:8) from an unswizzled global tile", nearest)  # fmt: skip
    if src.layout != "row_major" or dst.layout != "row_major":
        return no(request, Why.LAYOUT, "the checked LDS load copies row-major tiles", nearest)
    steps = (Step("lds", "global_load_dwordx4"), Step("lds", "ds_write_b128 at slot chunk ^ (row % 8)"))
    spelled = "sA[r * 8 + (c ^ (r & 7))] = *reinterpret_cast<const alloy_long2*>(a + r * row_bytes + 16 * c);"
    loop = ("for (int it = 0; it < 2; ++it) {  // 512 chunks of 16 bytes per 64-row tile, 256 threads\n"
            "  const int idx = threadIdx.x + 256 * it, r = idx / 8, c = idx % 8;\n"
            f"  {spelled}\n}}")  # fmt: skip
    signature = "void alloy_copy_lds(alloy_long2* sA, const char* a, long row_bytes)"
    code = device_code(gpu_helpers(request.target), signature, loop)
    if (check := copy_check(request.target, verify, dtype)) is None:
        return no(request, Why.CHECK_FAILED, f"the {request.target} tile program that runs this copy failed its check")
    notes = ("16 bytes per lane; a points at the block's first element (row 0, column k0)",)
    return Feasible(request, "lds", steps, {"build": gpu_build(request.target)}, code, check, notes)


def ask_all(requests: Sequence[Request], verify: bool = True) -> Combined | Infeasible | Invalid:
    """The answers to ``requests`` as one kernel on one target. On a GPU, a copy into shared memory must write one K
    block that the list's mma loads, from the global matrix it loads; the copy and the mma then carry the check of the
    tile program that runs both. The tile programs run one mma each, so a list holds at most one. A refused request
    is refused with its index."""
    if not requests:
        return bad(None, Why.OPERANDS, "a kernel names at least one request", "a list of requests")
    targets = sorted({r.target for r in requests})
    if len(targets) > 1:
        return bad(requests[0], Why.MIXED_TARGETS, f"one kernel runs on one target, not {', '.join(targets)}",
                   *(f"target {t}" for t in targets))  # fmt: skip
    mmas = [i for i, r in enumerate(requests) if r.op == "mma"]
    if len(mmas) > 1:
        return no(requests[mmas[1]], Why.COMBINE, f"requests {mmas[0]} and {mmas[1]} are both mma; a tile program "
                  "runs one mma, so no program checks them together", fix="ask each mma with its copies alone")  # fmt: skip
    answers: list[Feasible] = []
    for i, request in enumerate(requests):
        answer = ask(request, verify=False)
        if not isinstance(answer, Feasible):
            return dataclasses.replace(answer, reason=f"request {i} ({request.op}): {answer.reason}")
        answers.append(answer)
    fed = feeds(requests, mmas[0]) if mmas and requests[0].target in DIALECT else {}
    if isinstance(fed, Infeasible):
        return fed
    for i, request in enumerate(requests):
        if verify and i not in fed:
            answer = ask(request, verify=True)
            if not isinstance(answer, Feasible):
                return dataclasses.replace(answer, reason=f"request {i} ({request.op}): {answer.reason}")
            answers[i] = answer
    for i in fed:
        mma_check = answers[mmas[0]].check
        basis = f"the tile program of request {mmas[0]} (mma), which runs this copy" + (
            f": {mma_check.basis}" if mma_check.basis else ""
        )
        answers[i] = dataclasses.replace(answers[i], check=Check(mma_check.status, basis))
    order = ordering(requests, answers, fed, mmas)
    if isinstance(order, Infeasible):
        return order
    weakest = min((a.check for a in answers), key=lambda c: STRENGTH[c.status])
    basis = combined_basis(requests, answers, fed, mmas)
    return Combined(tuple(answers), tuple(f"copy {i} fills {name} of mma {mmas[0]}" for i, name in fed.items()),
                    Check(weakest.status, basis), order)  # fmt: skip


def combined_basis(requests: Sequence[Request], answers: list[Feasible], fed: dict[int, str], mmas: list[int]) -> str:
    """Which of the kernel's requests one program checks together (the mma, the copies it is fed by, the waits and
    fences), and which alone."""
    together = set(fed) | set(mmas[:1]) | {i for i, r in enumerate(requests) if r.op in ("wait", "fence")}
    if len(requests) == 1:
        return answers[0].check.basis
    if len(together) == len(requests):
        one = answers[mmas[0]].check.basis
        return f"one program runs all {len(requests)} requests" + (f": {one}" if one else "")
    alone = ", ".join(str(i) for i in range(len(requests)) if i not in together)
    return f"requests {alone} are checked alone, not in one program with the others"


def ordering(
    requests: Sequence[Request], answers: Sequence[Feasible], fed: dict[int, str], mmas: Sequence[int]
) -> tuple[str, ...] | Infeasible:
    """The waits and fences a kernel needs between its asynchronous work and the requests that read it (design 2.9).
    A list that states any ``wait`` or ``fence`` must state every one, in an order that reads nothing early: else it
    is refused with the missing request and where it goes. A list that states none gets them, in order, as the
    answer's ``order``."""
    explicit = any(r.op in ("wait", "fence") for r in requests)
    needed: list[str] = []
    for i, answer in enumerate(answers):
        readers = [mmas[0]] if i in fed else []
        if readers and readers[0] < i:
            return no(requests[readers[0]], Why.ORDER, f"request {readers[0]} (mma) comes before request {i} (copy), "
                      "which fills its input", fix=f"move request {i} before request {readers[0]}")  # fmt: skip
        done = answer.completion
        if done is None:
            continue
        for fence in done.fences:
            kind = fence.split("=", 1)[1]
            if explicit and not any(r.op == "fence" and r.kind == kind for r in requests[:i]):
                return no(requests[i], Why.ORDER, f"request {i} ({requests[i].op} on {answer.unit}) needs `{fence}` "
                          "before it", fence, fix=f"put `{fence}` before request {i}")  # fmt: skip
            needed.append(f"{fence} before request {i}")
        waits = [j for j in range(i + 1, len(requests)) if requests[j].op == "wait" and requests[j].on == done.token]
        if explicit and not waits:
            return no(requests[i], Why.ORDER, f"request {i} ({requests[i].op} on {answer.unit}) is never completed: "
                      f"`{done.wait}` must follow it", done.wait, fix=f"put `{done.wait}` after request {i}")  # fmt: skip
        early = [j for j in readers if explicit and j < waits[0]]
        if early:
            return no(requests[early[0]], Why.ORDER, f"request {early[0]} reads what request {i} ({requests[i].op}) "
                      f"writes before `{done.wait}`", done.wait,
                      fix=f"put `{done.wait}` between requests {i} and {early[0]}")  # fmt: skip
        needed.append(f"{done.wait} after request {i}" + (f", before request {readers[0]}" if readers else ""))
    return () if explicit else tuple(needed)


def feeds(requests: Sequence[Request], j: int) -> dict[int, str] | Infeasible:
    """Which mma input each copy into shared memory fills, by the copy's index: the tile program of mma ``j`` loads
    A as BM rows of 64 from the M x K matrix and Bt as BN rows of 64 from the N x K one. A copy that writes anything
    else is not in that program, so it is infeasible with the copies the program runs."""
    target, mma_ = requests[j].target, requests[j]
    a, b = mma_.operands["a"], mma_.operands["b"]
    m, k, n = a.shape[0], a.shape[1], b.shape[1]
    bm, bn = tile.gpu_block(target, m, n, k, a.dtype)
    kb = tile.k_block(a.dtype)
    blocks = {
        "a": (Operand("global", a.dtype, (m, k)), Operand("shared", a.dtype, (bm, kb), "row_major", a.swizzle)),
        "b": (Operand("global", b.dtype, (n, k)), Operand("shared", b.dtype, (bn, kb), "row_major", b.swizzle)),
    }
    nearest = tuple(dict.fromkeys(f"copy {spell(src=src, dst=dst)}" for src, dst in blocks.values()))
    fed: dict[int, str] = {}
    for i, request in enumerate(requests):
        src, dst = request.operands.get("src"), request.operands.get("dst")
        if request.op != "copy" or src is None or dst is None or dst.space != "shared":
            continue
        names = [name for name, (whole, block) in blocks.items() if dst == block and src.shape == whole.shape]
        if not names:
            reason = (f"request {i} copies {src.spelled()} into {dst.spelled()}, which the tile program of request {j} "
                      f"(mma) does not load: it loads A as {blocks['a'][1].spelled()} from {m}x{k} and Bt as "
                      f"{blocks['b'][1].spelled()} from {n}x{k}")  # fmt: skip
            fix = (f"copy one K block of {kb} per step: A from the {m} x {k} matrix, and B from Bt ({n} rows of {k}) "
                   "in global memory, since the mma reads B transposed")  # fmt: skip
            return no(request, Why.COMBINE, reason, *nearest, fix=fix)
        fed[i] = " or ".join(names)
    return fed


#: Bytes of an element a SoftHier copy moves.
SOFTHIER_BYTES = {"f64": 8, "f32": 4, "i32": 4, "f16": 2, "bf16": 2, "i16": 2, "i8": 1, "e4m3": 1, "e5m2": 1}
#: SoftHier's completion tokens: the wait row's name and what the wait completes.
SOFTHIER_WAITS = {"idma": ("wait_idma", "the iDMA transfers the cluster's DMA core issued have landed"),
                  "redmule": ("wait_redmule", "RedMulE has written the product into c")}  # fmt: skip
#: The operand names a Spatz row takes, per kind: one operand that names the type and length, or all of them.
SOFTHIER_OPERANDS = {"move": ({"x"}, {"src", "dst"}), "binary": ({"x"}, {"a", "b"}, {"x", "y"}),
                     "fma": ({"x"}, {"a", "b", "c"}), "reduction": ({"x"},)}  # fmt: skip
SOFTHIER_INTO_TCDM = ("copy it into the cluster's TCDM first: ask softhier copy --src global:<type>:<shape> --dst "
                      "shared:<type>:<shape> (iDMA), then wait on=idma")  # fmt: skip


def softhier_row(name: str) -> softhier.Row:
    return next(r for r in softhier.rows() if r.key() == name)


def softhier_check(row: softhier.Row, dtype: str) -> Check | str:
    """A SoftHier row's check from its current GVSoC record, or why it is refused: a failed run refuses it, a missing
    or stale record leaves it unverified."""
    verdict = softhier.verdict_of(row, dtype)
    if verdict is None:
        return Check("unverified", "no current GVSoC run recorded (python -m alloy.isa.softhier verify)")
    if not verdict.ok:
        return f"the row failed its check on GVSoC: {verdict.error or 'outside its error bound'}"
    inside = f" inside the {row.checked_by} program" if row.checked_by else ""
    error = f", max rel error {verdict.rel:.2g}" if verdict.rel else ""
    return Check("run", f"GVSoC {softhier.TARGET}, SoftHier v1{inside}{error}")


def softhier_setup() -> dict[str, str]:
    """What every SoftHier answer needs around its code: the v1 configuration, the headers, and the lines that build
    and run it."""
    return {
        "arch": f"{softhier.ARCH_HEADER}  (the SDK headers include flex_cluster_arch.h from their own folder, so the "
        "v1 header replaces the SDK's there)",
        "headers": "riscv_vector.h from the GCC 14 toolchain; flex_*.h from $SOFTHIER_SDK/runtime/runtime/include ("
        f"{softhier.pins()['sdk']})",
        "build": softhier.build_line(),
        "program": "the SDK headers define their functions (not static): put the code in the file with main (the SDK "
        f"frame: flex_barrier_xy_init(); flex_global_barrier_xy(); ...; flex_eoc(0)), then {softhier.link_line()}",
        "run": softhier.run_line(),
    }


def softhier_feasible(request: Request, row: softhier.Row, dtype: str, steps: tuple[Step, ...],
                      notes: tuple[str, ...] = (), completion: Completion | None = None) -> Answer:  # fmt: skip
    check = softhier_check(row, dtype)
    if isinstance(check, str):
        return no(request, Why.CHECK_FAILED, check)
    return Feasible(request, row.unit, steps, softhier_setup(), softhier.code(row, dtype), check,
                    (*notes, *((row.note,) if row.note else ())), completion)  # fmt: skip


def softhier_op(request: Request) -> Answer:
    """A SoftHier v1 request, answered from softhier.toml with the GVSoC record of the row."""
    if request.op == "wait":
        return softhier_wait(request)
    if request.op == "fence":
        if request.kind not in NO_FENCE:
            return bad(request, Why.OPERANDS, "fence names its kind", *(f"fence kind={k}" for k in NO_FENCE))
        return no(request, Why.NO_ROW, "softhier has no fence: flex_dma_async_wait_all and flex_redmule_wait complete "
                  "the work, and flex_intra_cluster_sync makes TCDM writes visible to the cluster's cores",
                  "wait on=idma", "wait on=redmule", "barrier kind=cluster")  # fmt: skip
    if request.op == "barrier":
        return softhier_barrier(request)
    if request.op == "mma":
        return softhier_mma(request)
    if request.op == "copy":
        return softhier_copy(request)
    return softhier_vector(request)


def softhier_wait(request: Request) -> Answer:
    if request.on not in SOFTHIER_WAITS:
        reason = f"softhier has no {request.on!r} token" if request.on else "wait names the token it waits on"
        nearest = tuple(f"wait on={t}" for t in SOFTHIER_WAITS)
        return no(request, Why.NO_ROW, reason, *nearest) if request.on else bad(request, Why.OPERANDS, reason, *nearest)
    name, what = SOFTHIER_WAITS[request.on]
    row = softhier_row(name)
    return softhier_feasible(request, row, row.dtypes[0], (Step(row.unit, row.call), Step("cluster",
                             "flex_intra_cluster_sync()")), (what,))  # fmt: skip


def softhier_barrier(request: Request) -> Answer:
    kinds = {"cluster": "barrier_cluster", "global": "barrier_global"}
    if request.kind not in kinds:
        return bad(request, Why.OPERANDS, "barrier names its kind: the cores of one cluster, or every cluster",
                   *(f"barrier kind={k}" for k in kinds))  # fmt: skip
    row = softhier_row(kinds[request.kind])
    return softhier_feasible(request, row, "none", (Step(row.unit, row.call),))


def softhier_vector(request: Request) -> Answer:
    """An elementwise operation, a reduction, a load, or a store on the Spatz unit: a strip-mined RVV loop over TCDM
    whose last strip is the tail (vsetvl gives min(n - i, VLMAX))."""
    spatz = [r for r in softhier.rows() if r.unit == "spatz"]
    rows = [r for r in spatz if r.op == request.op]
    if not rows:
        if request.op not in OPS and request.op not in functions():
            return bad(request, Why.OPERATION, f"no operation {request.op!r}",
                       "an op of `python -m alloy.isa ops`, mma, copy, wait, or barrier")  # fmt: skip
        related = [r.op for r in spatz if r.op.split("_")[0] == request.op.split("_")[0]]
        return no(request, Why.NO_ROW, f"no SoftHier row for {request.op}",
                  *(f"softhier {op}" for op in dict.fromkeys(related or [r.op for r in spatz])))  # fmt: skip
    row = rows[0]
    if request.max_ulp is not None:
        return bad(request, Why.BOUND, "max_ulp selects a rung of a math kernel; a SoftHier row has one accuracy",
                   "the request without max_ulp")  # fmt: skip
    one = Operand("shared", "f32", (1024,))
    if not request.operands:
        return bad(request, Why.OPERANDS, f"{request.op} needs an operand: it names the element type and the length",
                   spell(x=one))  # fmt: skip
    taken = SOFTHIER_OPERANDS[row.kind]
    if set(request.operands) not in taken:
        named = ", ".join(sorted(request.operands))
        return bad(request, Why.OPERANDS, f"softhier {request.op} takes operands {' or '.join(', '.join(sorted(t)) for t in taken)}, "
                   f"not {named}", spell(x=one))  # fmt: skip
    if why := mixed(request):
        return bad(request, Why.MIXED_TYPES, why, spell(x=one))
    dtype = dtype_of(request)
    if dtype not in row.dtypes:
        return no(request, Why.ELEMENT_TYPE, f"the SoftHier {request.op} row computes {', '.join(row.dtypes)}, not "
                  f"{dtype}", *(spell(x=Operand("shared", d, (1024,))) for d in row.dtypes))  # fmt: skip
    for operand in request.operands.values():
        if operand.space != "shared":
            fix = SOFTHIER_INTO_TCDM if operand.space == "global" else "name the data in TCDM: the row loops over it"
            return no(request, Why.SPACE, f"the Spatz row loads and stores the cluster's TCDM (shared), not "
                      f"{operand.space}", spell(x=Operand("shared", dtype, operand.shape or (1024,))), fix=fix)  # fmt: skip
    shapes = {o.shape for o in request.operands.values()}
    if refusal := unchained(request, shapes, Operand("shared", dtype, (1024,))):
        return refusal
    n = max(math.prod(s) for s in shapes)
    if n < 1:
        return bad(request, Why.MALFORMED, f"{request.op} needs at least one element", spell(x=one))
    size = int(dtype[1:]) // 8
    if n * size * (1 + len(request.operands)) > softhier.config()["cluster_tcdm_size"]:
        return no(request, Why.SHAPE, f"{n} {dtype} per operand do not fit the cluster's TCDM "
                  f"({softhier.config()['cluster_tcdm_size'] // 1024} KiB)", spell(x=Operand("shared", dtype, (16384,))),
                  fix="split the data into blocks that fit, and stream them in with iDMA")  # fmt: skip
    lanes = softhier.vlmax(dtype)
    strips = -(-n // lanes)
    setvl = f"__riscv_vsetvl_e{dtype[1:]}m8(n - i)"
    steps = (Step("spatz", setvl, strips), Step("spatz", softhier.spelled(row.call, dtype), strips))
    tail = (f"{n} elements: {strips} strips of vl = min(n - i, {lanes}) (VLMAX of e{dtype[1:]}m8 at VLEN 256); the "
            f"last strip, {n - (strips - 1) * lanes} elements, is the tail: no mask, no scalar epilogue")  # fmt: skip
    return softhier_feasible(request, row, dtype, steps, (tail,))


def softhier_copy(request: Request) -> Answer:
    """A copy between HBM (global) and the cluster's TCDM (shared) on the iDMA: one contiguous run (1D), or a block of
    rows of a larger row-major matrix (2D, a stride on each side). Asynchronous: wait on=idma completes it."""
    ops = request.operands
    if not {"src", "dst"} <= ops.keys():
        return bad(request, Why.OPERANDS, "copy takes operands src and dst")
    src, dst = ops["src"], ops["dst"]
    near = spell(src=Operand("global", src.dtype, (64, 64)), dst=Operand("shared", src.dtype, (32, 64)))
    if src.dtype != dst.dtype:
        return bad(request, Why.MIXED_TYPES, f"a copy converts nothing: src is {src.dtype}, dst is {dst.dtype}", near)
    if {src.space, dst.space} != {"global", "shared"}:
        return no(request, Why.SPACE, f"the checked iDMA rows copy between HBM (global) and TCDM (shared), not "
                  f"{src.space} to {dst.space}", near)  # fmt: skip
    if src.dtype not in SOFTHIER_BYTES:
        return no(request, Why.ELEMENT_TYPE, f"no element size for {src.dtype}", near)
    if src.swizzle != "none" or dst.swizzle != "none" or src.layout != dst.layout:
        return no(request, Why.SWIZZLE if src.swizzle != "none" or dst.swizzle != "none" else Why.LAYOUT,
                  "iDMA copies bytes in order: no swizzle, no transpose", near)  # fmt: skip
    size = SOFTHIER_BYTES[src.dtype]
    tcdm = dst if dst.space == "shared" else src
    if math.prod(tcdm.shape or (1,)) * size > softhier.config()["cluster_tcdm_size"]:
        return no(request, Why.SHAPE, f"{tcdm.spelled()} does not fit the cluster's TCDM "
                  f"({softhier.config()['cluster_tcdm_size'] // 1024} KiB)", near)  # fmt: skip
    hbm = "hbm_west(node, offset)"
    where = {"global": hbm, "shared": "local(offset)"}
    if math.prod(src.shape or (1,)) == math.prod(dst.shape or (1,)):  # the whole operand, packed on both sides: one run
        nbytes = math.prod(src.shape or (1,)) * size
        row = softhier_row("copy_1d")
        call = f"alloy_copy_1d({where[dst.space]}, {where[src.space]}, {nbytes})"
        notes: tuple[str, ...] = (f"{nbytes} bytes in one transfer",)
    else:
        small, large = sorted((src, dst), key=lambda o: math.prod(o.shape or (1,)))
        block, matrix = tuple(small.shape), tuple(large.shape)
        if len(block) != 2 or len(matrix) != 2 or block[0] > matrix[0] or block[1] > matrix[1]:
            return no(request, Why.SHAPE, f"a copy of a part moves a block of rows of a row-major matrix, both named "
                      f"rows x cols: {small.spelled()} is no block of {large.spelled()}", near)  # fmt: skip
        rows_, row_bytes, strided = block[0], block[1] * size, matrix[1] * size
        if block[1] == matrix[1]:  # whole rows: one run that starts at row row0
            row = softhier_row("copy_1d")
            start = f" + row0 * {strided}"
            src_at = where[src.space] + (start if src is large else "")
            dst_at = where[dst.space] + (start if dst is large else "")
            call = f"alloy_copy_1d({dst_at}, {src_at}, {rows_ * row_bytes})"
            notes = (f"{rows_} whole rows from row row0 of the {matrix[0]} x {matrix[1]} matrix: one run",)
        else:
            dst_stride, src_stride = (row_bytes, strided) if dst is small else (strided, row_bytes)
            row = softhier_row("copy_2d")
            corner = f" + (row0 * {matrix[1]} + col0) * {size}"
            src_at = where[src.space] + (corner if src is large else "")
            dst_at = where[dst.space] + (corner if dst is large else "")
            call = f"alloy_copy_2d({dst_at}, {src_at}, {row_bytes}, {dst_stride}, {src_stride}, {rows_})"
            notes = ((f"{rows_} rows of {row_bytes} bytes; the block's corner (row0, col0) in the {matrix[0]} x "
                     f"{matrix[1]} matrix"),)  # fmt: skip
    notes += ((f"HBM of v1: {hbm} or hbm_south(node, offset), node 0 or 1; every core calls the function, the DMA core "
              "(flex_is_dm_core(), the last) issues"),)  # fmt: skip
    steps = (Step("idma", call),)
    return softhier_feasible(request, row, "bytes", steps, notes, Completion("idma", "wait on=idma"))


def softhier_mma(request: Request) -> Answer:
    """c (M x N) += a (M x K) b (K x N) on RedMulE: f16, all three row-major in the cluster's TCDM. Asynchronous: wait
    on=redmule completes it."""
    ops = request.operands
    near = spell(a=Operand("shared", "f16", (64, 64)), b=Operand("shared", "f16", (64, 64)),
                 c=Operand("shared", "f16", (64, 64)))  # fmt: skip
    if not {"a", "b", "c"} <= ops.keys():
        return bad(request, Why.OPERANDS, "mma takes operands a (M x K), b (K x N), and c (M x N)", near)
    a, b, c = ops["a"], ops["b"], ops["c"]
    if len(a.shape) != 2 or len(b.shape) != 2 or a.shape[1] != b.shape[0] or c.shape != (a.shape[0], b.shape[1]):
        reason = f"shapes do not chain: a {a.shape}, b {b.shape}, c {c.shape}; a is M x K, b K x N, c M x N"
        return bad(request, Why.CHAIN, reason, near)
    if a.dtype != b.dtype:
        return bad(request, Why.MIXED_TYPES, f"a is {a.dtype} and b is {b.dtype}; an mma multiplies inputs of one "
                   "element type", near)  # fmt: skip
    m, k, n = a.shape[0], a.shape[1], b.shape[1]
    near = spell(
        a=Operand("shared", "f16", (m, k)), b=Operand("shared", "f16", (k, n)), c=Operand("shared", "f16", (m, n))
    )
    if (a.dtype, c.dtype) != ("f16", "f16"):
        return no(request, Why.ELEMENT_TYPE, f"the checked RedMulE row multiplies f16 into f16 (REDMULE_FP_16), not "
                  f"{a.dtype} into {c.dtype}", near)  # fmt: skip
    for name, operand in (("a", a), ("b", b), ("c", c)):
        if operand.space != "shared":
            return no(request, Why.SPACE, f"RedMulE reads and writes the cluster's TCDM, not {name} in {operand.space}",
                      near, fix=SOFTHIER_INTO_TCDM)  # fmt: skip
        if operand.layout != "row_major" or operand.swizzle != "none":
            return no(request, Why.LAYOUT, f"RedMulE takes {name} packed row-major, without a swizzle", near,
                      fix=f"hold {name} row_major; a 2D iDMA copy packs a block of a larger matrix")  # fmt: skip
    if 2 * (m * k + k * n + m * n) > softhier.config()["cluster_tcdm_size"] or max(m, n, k) > 0xFFFF:
        return no(request, Why.SHAPE, f"a, b, and c ({2 * (m * k + k * n + m * n)} bytes) must fit the cluster's TCDM "
                  f"({softhier.config()['cluster_tcdm_size'] // 1024} KiB)", spell(a=Operand("shared", "f16", (256, 256)),
                  b=Operand("shared", "f16", (256, 256)), c=Operand("shared", "f16", (256, 256))),
                  fix="tile the product and accumulate the tiles of K into one c")  # fmt: skip
    row = softhier_row("mma")
    steps = (Step("redmule", f"flex_redmule_config({m}, {k}, {n})"),
             Step("redmule", "flex_redmule_trigger(a_off, b_off, c_off, REDMULE_FP_16)"))  # fmt: skip
    notes = ((f"call alloy_mma_f16(a_off, b_off, c_off, {m}, {n}, {k}) on every core of the cluster; RedMulE names the "
             f"extents M, N (inner), K, so its config is ({m}, {k}, {n}); offsets are bytes into the TCDM"),
             "c is the accumulator and the result: load it (zero it for c = a b) before the call")  # fmt: skip
    return softhier_feasible(request, row, "f16", steps, notes, Completion("redmule", "wait on=redmule"))


def parsed_request(target: str, text: str) -> Request:
    """One request of ``ask-all``: ``op name=operand ... [unit=U] [max_ulp=X]``; a malformed one raises
    :class:`KeyError` with what is wrong."""
    if not text.split():
        raise KeyError("an empty request: op name=operand ...")
    op, *fields = text.split()
    operands: dict[str, Operand] = {}
    unit, max_ulp, on, kind = "", None, "", ""
    for field in fields:
        name, sep, value = field.partition("=")
        if not sep or not value:
            raise KeyError(f"{field!r} in {text!r}: a field is name=operand, unit=U, max_ulp=X, on=TOKEN, or kind=K")
        if name == "unit":
            unit = value.lower()
        elif name == "on":
            on = value.lower()
        elif name == "kind":
            kind = value.lower()
        elif name == "max_ulp":
            try:
                max_ulp = float(value)
            except ValueError:
                raise KeyError(f"{field!r} in {text!r}: max_ulp is a number") from None
        else:
            operands[name] = Operand.parse(value)
    return Request(target, op.lower(), operands, unit, max_ulp, on, kind)
