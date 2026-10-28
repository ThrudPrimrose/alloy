# Copyright 2026 ETH Zurich and the Alloy authors.
"""Verify every built candidate inside the whole program: each scope links its archive from one fixed path, so a
candidate is one archive copy plus a replayed DaCe build (command cache + precompiled header). Every other scope
keeps its reference archive, and the outputs are compared against the all-reference program on the same inputs."""

import multiprocessing
import os
import pathlib
import queue
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Literal, Self

import numpy as np
import pydantic.dataclasses
import sympy
from dace.codegen.exceptions import CompilationError

from alloy import machine
from alloy.backend.sweep import ScopeReport
from alloy.configuration_matrix import Matrix
from alloy.evaluate.link import Linker, built
from alloy.frontend.inputs import Draw, require_bench
from alloy.frontend.scopes import Program
from alloy.records import RECORD


@dataclass(slots=True, frozen=True)
class Cases:
    """The fuzz draws every candidate runs on, and the program outputs compared."""

    draws: list[Draw]
    outputs: tuple[str, ...]


#: How a candidate's outputs compared: bit-identical (``exact``), inside the band (``pass``), outside the band or not
#: bit-identical (``fail``), the band's accumulation floor reaches its relative tolerance at this precision and
#: accumulation length (``ungradeable``), the program call died (``crashed``), or the program did not link
#: (``link_error``).
Status = Literal["exact", "pass", "fail", "ungradeable", "crashed", "link_error"]


@pydantic.dataclasses.dataclass(slots=True, frozen=True, config=RECORD)
class Verdict:
    """How a candidate's outputs compare with the reference's. ``error`` is the worst relative error seen."""

    status: Status
    error: float = 0.0
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.status in ("exact", "pass")


#: Seconds one program call may take before its child is killed and the candidate reported as crashed.
CALL_TIMEOUT_S = 600

#: One program call's outputs by name, or a string describing how its child died.
Outcome = dict[str, np.ndarray] | str


def openmp_env(cpus: tuple[int, ...]) -> dict[str, str]:
    # Places name the slot's CPUs: in a VM the runtime's own topology can merge two of them into one "core".
    places = ",".join(f"{{{cpu}}}" for cpu in cpus)
    return {"OMP_NUM_THREADS": str(len(cpus)), "OMP_PROC_BIND": "close", "OMP_PLACES": places}


def child_main(target: Callable[..., Any], args: tuple, cpus: tuple[int, ...], share: float, conn: Any) -> None:
    # The fork server froze the environment it started with and loads no OpenMP runtime, so the runtime the program
    # library brings in reads this child's settings.
    os.sched_setaffinity(0, cpus)
    os.environ.update(openmp_env(cpus))
    machine.limit_memory(share, len(cpus))
    conn.send(target(*args))


def call_program(folder: str, args: dict[str, Any], outputs: tuple[str, ...]) -> dict[str, np.ndarray]:
    from dace.codegen import compiler  # noqa: PLC0415 -- preloaded by the fork server

    # an array that crossed the process boundary may arrive as a view on the pickle buffer, which dace refuses
    args = {k: np.array(v, copy=True) if isinstance(v, np.ndarray) else v for k, v in args.items()}
    compiler.load_precompiled_sdfg(folder)(**args)
    return {name: np.asarray(args[name]).copy() for name in outputs}


def child_context() -> Any:
    """Children come from a fork server that imported dace once, never from this (threaded) process: a fork of a
    threaded parent can deadlock the child."""
    ctx = multiprocessing.get_context("forkserver")
    ctx.set_forkserver_preload(["dace", "numpy"])
    return ctx


def slot_share() -> float:
    """The memory share of one child when every core slot runs one at once."""
    return 1 / len(machine.core_slots())


def in_child(
    target: Callable[..., Any], args: tuple, cpus: tuple[int, ...], share: float, timeout: float = CALL_TIMEOUT_S
) -> Any:
    """``target(*args)`` in a fork-server child bound to ``cpus``, capped at ``share`` of the available memory and
    killed after ``timeout`` seconds, so a crash is a value: a string describing it."""
    ctx = child_context()
    receive, send = ctx.Pipe(duplex=False)
    child = ctx.Process(target=child_main, args=(target, args, cpus, share, send))
    child.start()
    send.close()
    result = None
    if receive.poll(timeout):
        try:
            result = receive.recv()
        except EOFError:  # the child died before sending: the exit code below says how
            result = None
    child.join(timeout=timeout)
    if child.is_alive():
        child.kill()
        child.join()
        return "timed out"
    if child.exitcode != 0 or result is None:
        return f"exit code {child.exitcode}"
    return result


def run(folder: pathlib.Path, draw: Draw, outputs: tuple[str, ...], cpus: tuple[int, ...] | None = None) -> Outcome:
    """The outputs of one call of the program built in ``folder`` on a fresh copy of ``draw`` (the child unpickles
    its own), in a child bound to ``cpus`` (default: the first core slot)."""
    args = {**draw.values, **draw.sizes}
    slot = machine.core_slots()[0] if cpus is None else cpus
    return in_child(call_program, (str(folder), args, outputs), slot, slot_share())


class Children:
    """Program calls in parallel: one child per core slot at a time, each bound to its slot's cores, so no two
    children share a core."""

    __slots__ = ("free", "pool")

    def __init__(self) -> None:
        slots = machine.core_slots()
        self.free: queue.SimpleQueue[tuple[int, ...]] = queue.SimpleQueue()
        for slot in slots:
            self.free.put(slot)
        self.pool = ThreadPoolExecutor(max_workers=len(slots))

    def call(self, folder: pathlib.Path, draw: Draw, outputs: tuple[str, ...]) -> Outcome:
        cpus = self.free.get()
        try:
            return run(folder, draw, outputs, cpus)
        finally:
            self.free.put(cpus)

    def submit(self, folder: pathlib.Path, draw: Draw, outputs: tuple[str, ...]) -> Future[Outcome]:
        return self.pool.submit(self.call, folder, draw, outputs)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.pool.shutdown(wait=True)


def accumulation_length(program: Program, sizes: dict[str, int]) -> int:
    """The longest accumulation chain of the program at ``sizes``: a candidate's reordering can reach an output
    through every scope after it, so the program-wide maximum bounds it."""
    subs = {sympy.Symbol(k): v for k, v in sizes.items()}
    lengths = []
    for r in program.scopes:
        length = sympy.sympify(r.accumulation_length).subs(list(subs.items()))
        if length.free_symbols:
            raise ValueError(f"{r.symbol}: accumulation length {r.accumulation_length} needs {length.free_symbols}")
        lengths.append(int(length))
    return max(lengths)


def compare(tolerance: str, ref: np.ndarray, val: np.ndarray, length: int, datatype: str) -> Verdict:
    """``exact``: bit-identical. ``band``: HPCAgent-Bench's per-precision band with its eps_acc*sqrt(l) floor, at the
    kernel's ``datatype``, else (an integer kernel's float output) at the output's own; an integer or boolean output
    has no rounding, so it is always compared bit-identical."""
    if tolerance == "exact" or not np.issubdtype(ref.dtype, np.inexact):
        same = np.array_equal(ref, val, equal_nan=np.issubdtype(ref.dtype, np.inexact))
        return Verdict("exact") if same else Verdict("fail", detail="not bit-identical to the reference")
    require_bench()
    from hpcagent_bench.frameworks.utilities import compare_arrays  # noqa: PLC0415
    from hpcagent_bench.precision import (  # noqa: PLC0415
        UngradeableTolerance,
        accumulation_eps,
        precision_from_datatype,
        tolerance_band,
    )

    try:
        precision = precision_from_datatype(datatype)
    except ValueError:
        precision = precision_from_datatype(ref.dtype.name)
    band = tolerance_band(precision)
    try:
        ok, err, detail = compare_arrays(
            ref, val, band.rtol, band.atol, accum_length=length, eps_precision=accumulation_eps(precision)
        )
    except UngradeableTolerance as exc:
        return Verdict("ungradeable", detail=str(exc))
    return Verdict("pass" if ok else "fail", float(err), detail)


#: Reference runs per draw. An output that differs between them is nondeterministic -- a parallel reduction that
#: combines its partial sums in whatever order the threads finish -- and is compared under ``band`` at every level.
REFERENCE_RUNS = 3


@dataclass(slots=True, frozen=True)
class Reference:
    outputs: list[dict[str, np.ndarray]]
    nondeterministic: frozenset[str]


@dataclass(slots=True, frozen=True)
class Verification:
    """``verdicts[scope symbol][candidate name]``, the outputs the reference does not reproduce, and the program
    built for every candidate (``programs[scope symbol, candidate name]``) and for the reference."""

    verdicts: dict[str, dict[str, Verdict]]
    nondeterministic: frozenset[str]
    programs: dict[tuple[str, str], pathlib.Path]
    reference: pathlib.Path


def reference_outputs(compiled: pathlib.Path, cases: Cases) -> Reference:
    """The reference's outputs per draw, and which outputs change between repeated runs of the same draw."""
    with Children() as children:
        return reference_from(
            cases, [[f.result() for f in runs] for runs in submit_reference(children, compiled, cases)]
        )


def submit_reference(children: Children, compiled: pathlib.Path, cases: Cases) -> list[list[Future[Outcome]]]:
    return [[children.submit(compiled, d, cases.outputs) for _ in range(REFERENCE_RUNS)] for d in cases.draws]


def reference_from(cases: Cases, per_draw: list[list[Outcome]]) -> Reference:
    outputs, unstable = [], set()
    for runs in per_draw:
        failed = [r for r in runs if isinstance(r, str)]
        if failed:
            raise RuntimeError(f"the reference program crashed: {failed[0]}")
        first, *rest = (r for r in runs if not isinstance(r, str))
        unstable |= {n for n in cases.outputs for r in rest if not np.array_equal(first[n], r[n], equal_nan=True)}
        outputs.append(first)
    return Reference(outputs, frozenset(unstable))


def judge(tolerance: str, ref: Reference, vals: list[Outcome], lengths: list[int]) -> Verdict:
    """The worst verdict over every iteration and output; nondeterministic outputs always use ``band``."""
    worst = Verdict("exact")
    for expected_outputs, val, length in zip(ref.outputs, vals, lengths, strict=True):
        if isinstance(val, str):
            return Verdict("crashed", detail=val)
        for name, expected in expected_outputs.items():
            level = "band" if name in ref.nondeterministic else tolerance
            verdict = compare(level, expected, val[name], length, str(np.real(expected).dtype))
            if not verdict.ok:
                return Verdict(verdict.status, verdict.error, f"{name}: {verdict.detail}")
            if verdict.status == "pass" and verdict.error >= worst.error:
                worst = verdict
    return worst


def verify(
    program: Program, matrix: Matrix, reports: list[ScopeReport], cases: Cases, out: pathlib.Path
) -> Verification:
    """A verdict for every built candidate. Program calls run in parallel children while the next candidate
    compiles; a duplicate object is judged on its original's outputs at its own FP level."""
    linker = Linker(program, matrix, out)
    reference = {rep.scope.symbol: reference_archive(rep) for rep in reports}
    ref_candidates = frozenset(rep.builds[0].candidate for rep in reports)
    ref_program = linker.compile(reference, "reference", ref_candidates)
    lengths = [accumulation_length(program, d.sizes) for d in cases.draws]
    with Children() as children:
        ref_runs = submit_reference(children, ref_program, cases)
        pending: dict[tuple[str, str], list[Future[Outcome]] | Verdict] = {}
        programs = {(rep.scope.symbol, rep.builds[0].name): ref_program for rep in reports}
        for rep in reports:
            for b in rep.builds[1:]:  # the first build is the reference, already running
                if b.error or b.archive is None or b.duplicate_of:
                    continue
                selection = {**reference, rep.scope.symbol: b.archive}
                try:
                    compiled = linker.compile(selection, f"{rep.scope.symbol}_{b.name}", ref_candidates | {b.candidate})
                except (CompilationError, RuntimeError, OSError) as exc:  # link failure, or a library that won't load
                    pending[rep.scope.symbol, b.name] = Verdict("link_error", detail=str(exc)[-2000:])
                    continue
                programs[rep.scope.symbol, b.name] = compiled
                pending[rep.scope.symbol, b.name] = [children.submit(compiled, d, cases.outputs) for d in cases.draws]
        refs = reference_from(cases, [[f.result() for f in runs] for runs in ref_runs])
        ran = {k: v if isinstance(v, Verdict) else [f.result() for f in v] for k, v in pending.items()}
    reference_runs: list[Outcome] = [*refs.outputs]
    for rep in reports:
        ran[rep.scope.symbol, rep.builds[0].name] = reference_runs
    verdicts = {rep.scope.symbol: judge_scope(rep, matrix, refs, ran, lengths) for rep in reports}
    return Verification(verdicts, refs.nondeterministic, programs, ref_program)


def judge_scope(
    rep: ScopeReport,
    matrix: Matrix,
    refs: Reference,
    ran: dict[tuple[str, str], list[Outcome] | Verdict],
    lengths: list[int],
) -> dict[str, Verdict]:
    """A verdict for every built candidate of ``rep``; a duplicate is judged on its original's outputs."""
    mine: dict[str, Verdict] = {}
    for b in rep.builds:
        if b.error or b.archive is None:
            continue
        outputs = ran[rep.scope.symbol, b.duplicate_of or b.name]
        verdict = (
            outputs if isinstance(outputs, Verdict) else judge(b.candidate.tolerance(matrix), refs, outputs, lengths)
        )
        mine[b.name] = verdict
    return mine


def reference_archive(rep: ScopeReport) -> pathlib.Path:
    """The scope's first built candidate: the matrix default (first language, first compiler, every default)."""
    return built(rep.builds[0])
