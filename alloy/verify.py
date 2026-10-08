# Copyright 2026 ETH Zurich and the Alloy authors.
"""Verify every built candidate inside the whole program: each region links its archive from one fixed path, so a
candidate is one archive copy plus a replayed DaCe build (command cache + precompiled header). Every other region
keeps its reference archive, and the outputs are compared against the all-reference program on the same inputs."""

import copy
import hashlib
import multiprocessing
import pathlib
import shutil
from contextlib import ExitStack
from dataclasses import dataclass
from typing import Any

import numpy as np
import sympy
from dace.codegen.exceptions import CompilationError
from dace.config import set_temporary
from dace.libraries.standard.nodes import external_call

from alloy import runtime
from alloy.build import Build, runtime_library
from alloy.configuration_matrix import Matrix
from alloy.inputs import Draw
from alloy.regions import Program
from alloy.sweep import RegionReport


@dataclass(slots=True, frozen=True)
class Cases:
    """The fuzz draws every candidate runs on, and the program outputs compared."""

    draws: list[Draw]
    outputs: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class Verdict:
    """``exact``, ``pass``, ``fail``, ``ungradeable`` or ``crashed``; ``error`` is the worst relative error seen."""

    status: str
    error: float = 0.0
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.status in ("exact", "pass")


@dataclass(slots=True)
class Linker:
    """Builds the program with a chosen archive per region, every region's archive at ``link/lib<symbol>.a``."""

    program: Program
    matrix: Matrix
    out: pathlib.Path

    def link_flags(self) -> list[str]:
        library = runtime_library(self.matrix)
        return runtime.link_flags(library, self.matrix.openmp_runtimes[self.matrix.defaults.openmp_runtime])

    def cmake_args(self) -> str:
        """Make DaCe's own OpenMP the matrix runtime: its CMake would otherwise find the compiler's default one and
        load a second runtime next to the regions'."""
        soname = self.matrix.openmp_runtimes[self.matrix.defaults.openmp_runtime]
        extra = [f"-DOpenMP_CXX_LIB_NAMES={soname}", f"-DOpenMP_{soname}_LIBRARY={runtime_library(self.matrix)}"]
        return " ".join(extra)

    def support_flags(self, compilers: frozenset[str]) -> list[str]:
        """Link flags for the support libraries of every compiler that built one of the linked archives."""
        flags: list[str] = []
        for name in sorted(compilers):
            comp = self.matrix.compilers[name]
            executables = list(comp.executables.values())
            for soname in comp.support_libraries:
                flags += runtime.link_flags(runtime.resolve(soname, executables), soname)
        return flags

    def compile(
        self, archives: dict[str, pathlib.Path], tag: str, compilers: frozenset[str] = frozenset()
    ) -> pathlib.Path:
        """The program with ``archives[symbol]`` linked for each region, built under a name of its own so no cache
        or loaded library of another candidate can stand in for it."""
        link = self.out / "link"
        link.mkdir(parents=True, exist_ok=True)
        sdfg = copy.deepcopy(self.program.sdfg)
        safe = f"p{hashlib.sha256(tag.encode()).hexdigest()[:12]}"  # candidate names carry '-', SDFG names may not
        sdfg.name = f"{self.program.sdfg.name}_{safe}"  # pyright: ignore[reportAttributeAccessIssue]
        sdfg.build_folder = str(self.out / "programs" / safe)
        flags = self.link_flags() + self.support_flags(compilers)
        for call in external_call.external_calls(sdfg):
            fixed = link / f"lib{call.symbol}.a"
            shutil.copyfile(archives[call.symbol], fixed)
            call.implementation, call.lib_path, call.link_flags = "ExternCall", str(fixed), flags
        with ExitStack() as stack:
            for path, value in (
                (("compiler", "command_cache"), True),
                (("compiler", "precompiled_header"), True),
                (("compiler", "extra_cmake_args"), self.cmake_args()),
            ):
                stack.enter_context(set_temporary(*path, value=value))
            sdfg.compile()
        return pathlib.Path(sdfg.build_folder)


#: Seconds one program call may take before its child is killed and the candidate reported as crashed.
CALL_TIMEOUT_S = 600


def run_child(folder: str, args: dict[str, Any], outputs: tuple[str, ...], conn: Any) -> None:
    from dace.codegen import compiler  # noqa: PLC0415 -- preloaded by the fork server

    # an array that crossed the process boundary may arrive as a view on the pickle buffer, which dace refuses
    args = {k: np.array(v, copy=True) if isinstance(v, np.ndarray) else v for k, v in args.items()}
    compiler.load_precompiled_sdfg(folder)(**args)
    conn.send({name: np.asarray(args[name]).copy() for name in outputs})


def child_context() -> Any:
    """Children come from a fork server that imported dace once, never from this (threaded) process: a fork of a
    threaded parent can deadlock the child."""
    ctx = multiprocessing.get_context("forkserver")
    ctx.set_forkserver_preload(["dace", "numpy"])
    return ctx


def run(folder: pathlib.Path, draw: Draw, outputs: tuple[str, ...]) -> dict[str, np.ndarray] | str:
    """The outputs of one call of the program built in ``folder`` on a fresh copy of ``draw``, in a child process so a
    crash is a verdict; a string describes the crash."""
    args = {**{k: copy.deepcopy(v) for k, v in draw.values.items()}, **draw.sizes}
    ctx = child_context()
    receive, send = ctx.Pipe(duplex=False)
    child = ctx.Process(target=run_child, args=(str(folder), args, outputs, send))
    child.start()
    send.close()
    result = None
    if receive.poll(CALL_TIMEOUT_S):
        try:
            result = receive.recv()
        except EOFError:  # the child died before sending: the exit code below says how
            result = None
    child.join(timeout=CALL_TIMEOUT_S)
    if child.is_alive():
        child.kill()
        child.join()
        return "timed out"
    if child.exitcode != 0 or result is None:
        return f"exit code {child.exitcode}"
    return result


def accumulation_length(program: Program, sizes: dict[str, int]) -> int:
    """The longest accumulation chain of the program at ``sizes``: a candidate's reordering can reach an output
    through every region after it, so the program-wide maximum bounds it."""
    subs = {sympy.Symbol(k): v for k, v in sizes.items()}
    return max(int(sympy.sympify(r.accumulation_length).subs(list(subs.items()))) for r in program.regions)


def compare(tolerance: str, ref: np.ndarray, val: np.ndarray, length: int, datatype: str) -> Verdict:
    """``exact``: bit-identical. ``band``: HPCAgent-Bench's per-precision band with its eps_acc*sqrt(l) floor."""
    if tolerance == "exact":
        same = np.array_equal(ref, val, equal_nan=np.issubdtype(ref.dtype, np.inexact))
        return Verdict("exact") if same else Verdict("fail", detail="not bit-identical to the reference")
    from hpcagent_bench.frameworks.utilities import compare_arrays  # noqa: PLC0415
    from hpcagent_bench.precision import (  # noqa: PLC0415
        UngradeableTolerance,
        accumulation_eps,
        precision_from_datatype,
        tolerance_band,
    )

    precision = precision_from_datatype(datatype)
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
    """``verdicts[region symbol][candidate name]``, and the outputs the reference does not reproduce."""

    verdicts: dict[str, dict[str, "Verdict"]]
    nondeterministic: frozenset[str]


def reference_outputs(compiled: pathlib.Path, cases: Cases) -> Reference:
    """The reference's outputs per draw, and which outputs change between repeated runs of the same draw."""
    outputs, unstable = [], set()
    for draw in cases.draws:
        runs = [run(compiled, draw, cases.outputs) for _ in range(REFERENCE_RUNS)]
        failed = [r for r in runs if isinstance(r, str)]
        if failed:
            raise RuntimeError(f"the reference program crashed: {failed[0]}")
        first, *rest = (r for r in runs if not isinstance(r, str))
        unstable |= {n for n in cases.outputs for r in rest if not np.array_equal(first[n], r[n], equal_nan=True)}
        outputs.append(first)
    return Reference(outputs, frozenset(unstable))


def judge(tolerance: str, ref: Reference, vals: list[dict[str, np.ndarray] | str], lengths: list[int]) -> Verdict:
    """The worst verdict over every iteration and output; nondeterministic outputs always use ``band``."""
    worst = Verdict("exact")
    for expected_outputs, val, length in zip(ref.outputs, vals, lengths, strict=True):
        if isinstance(val, str):
            return Verdict("crashed", detail=val)
        for name, expected in expected_outputs.items():
            level = "band" if name in ref.nondeterministic else tolerance
            verdict = compare(level, expected, val[name], length, str(expected.dtype))
            if not verdict.ok:
                return Verdict(verdict.status, verdict.error, f"{name}: {verdict.detail}")
            if verdict.status == "pass" and verdict.error >= worst.error:
                worst = verdict
    return worst


def verify(
    program: Program, matrix: Matrix, reports: list[RegionReport], cases: Cases, out: pathlib.Path
) -> Verification:
    """A verdict for every built candidate. A duplicate object inherits its original's verdict."""
    linker = Linker(program, matrix, out)
    reference = {rep.region.symbol: reference_archive(rep) for rep in reports}
    ref_compilers = frozenset(rep.builds[0].candidate.compiler for rep in reports)
    ref_program = linker.compile(reference, "reference", ref_compilers)
    draws, outputs = cases.draws, cases.outputs
    refs = reference_outputs(ref_program, cases)
    lengths = [accumulation_length(program, d.sizes) for d in draws]
    verdicts: dict[str, dict[str, Verdict]] = {}
    for rep in reports:
        mine = verdicts.setdefault(rep.region.symbol, {})
        ran: dict[str, list[dict[str, np.ndarray] | str]] = {}
        for b in rep.builds:
            if b.error or b.archive is None:
                continue
            tolerance = matrix.fp_levels[b.candidate.resolved(matrix)[1]].tolerance
            if b.duplicate_of:  # same object, but possibly a looser FP level: judge its outputs under its own test
                original = ran.get(b.duplicate_of)
                mine[b.name] = mine[b.duplicate_of] if original is None else judge(tolerance, refs, original, lengths)
                continue
            selection = {**reference, rep.region.symbol: b.archive}
            try:
                compiled = linker.compile(
                    selection, f"{rep.region.symbol}_{b.name}", ref_compilers | {b.candidate.compiler}
                )
            except (CompilationError, RuntimeError, OSError) as exc:  # link failure, or a library that does not load
                mine[b.name] = Verdict("link_error", detail=str(exc)[-2000:])
                continue
            ran[b.name] = [run(compiled, d, outputs) for d in draws]
            mine[b.name] = judge(tolerance, refs, ran[b.name], lengths)
    return Verification(verdicts, refs.nondeterministic)


def reference_archive(rep: RegionReport) -> pathlib.Path:
    """The region's first built candidate: the matrix default (first language, first compiler, every default)."""
    first: Build = rep.builds[0]
    if first.error or first.archive is None:
        raise RuntimeError(f"{rep.region.symbol}: the reference candidate {first.name} did not build: {first.error}")
    return first.archive
