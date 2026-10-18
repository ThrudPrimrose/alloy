# Copyright 2026 ETH Zurich and the Alloy authors.
"""Alloy on HPCAgent-Bench (needs ``alloy[bench]``; the core never imports this module). A bench DaCe pipeline gives
the SDFG; Alloy builds, verifies and times every region candidate. The framework columns compile the program linking
each region's local winner (:func:`compiled_winners`). The optimizers start from those winners and, while the
kernel's time budget allows, let the judge's ``/score`` rank the :data:`TOP` screened candidates of each region, one
region at a time with the others at their best so far; the best library is submitted (:func:`optimize`)."""

import copy
import pathlib
import tempfile
import time
from collections.abc import Callable, Sequence

import dace
from dace.codegen.compiled_sdfg import CompiledSDFG
from dace.config import set_temporary
from dace.frontend.python.parser import DaceProgram
from hpcagent_bench import paths
from hpcagent_bench.cpf_bridge import render_canonical
from hpcagent_bench.cpf_cache import DEFAULT_HINTS
from hpcagent_bench.frameworks.benchmark import Benchmark
from hpcagent_bench.frameworks.dace_framework import PIPELINES_BY_NAME, PipelineContext
from hpcagent_bench.frameworks.framework import framework_class
from hpcagent_bench.harness.envelope import Submission
from hpcagent_bench.harness.pipeline import judge_endpoints
from hpcagent_bench.harness.scoring import resolve_kernel_timeout
from hpcagent_bench.harness.task import Task
from hpcagent_bench.harness.tools import JudgeClient
from hpcagent_bench.precision import Precision, numpy_dtype
from hpcagent_bench.spec import BenchSpec

from alloy import api, configuration_matrix
from alloy.backend.build import Build
from alloy.backend.sweep import RegionReport
from alloy.configuration_matrix import Matrix
from alloy.evaluate.link import Linker, cmake_args
from alloy.evaluate.timing import Measured, winning_build
from alloy.frontend import inputs, regions

#: Screened candidates per region the judge scores.
TOP = 5
#: Seconds one judge ``/score`` is assumed to take until one is timed: 200-240 s for argmax_value (fp64) on a 16-core
#: box, so only an L3 kernel's 600 s leaves room for a score beside the harness's own grade.
SCORE_GUESS_S = 240.0
#: Task language -> the CPF dialect the library is rendered in.
DIALECT = {"c": "c", "cpp": "c++"}

#: Builds a library submission from a rendered unit and what it links against (the bench's ``.so`` build).
Deliver = Callable[[str, Sequence[str]], Submission]


def pipeline_sdfg(spec: BenchSpec, pipeline: str, precision: Precision) -> dace.SDFG:
    """The kernel's SDFG at ``precision`` after the bench's DaCe pipeline ``pipeline``."""
    framework = framework_class("dace_cpu")("dace_cpu")
    framework.set_datatype(precision.value)
    program, _ = framework.implementations(Benchmark(spec.short_name))[0]
    if not isinstance(program, DaceProgram):
        raise TypeError(f"{spec.short_name}: the dace port is not a @dace.program")
    sdfg = program.to_sdfg(simplify=False)
    PIPELINES_BY_NAME[pipeline].transform(sdfg, PipelineContext(device=dace.dtypes.DeviceType.CPU))
    return sdfg


def screened(rep: RegionReport, screen: dict[str, Measured], top: int) -> list[Build]:
    """The ``top`` verified builds of ``rep`` other than its reference, fastest screened median first."""
    by_name = {build.name: build for build in rep.builds[1:]}
    ranked = sorted((n for n, m in screen.items() if n in by_name and m.verdict.ok), key=lambda n: screen[n].median)
    return [by_name[n] for n in ranked[:top]]


def generated(sdfg: dace.SDFG, spec: BenchSpec, precision: Precision, matrix: Matrix, out: pathlib.Path) -> api.Result:
    """Alloy on ``sdfg`` under ``out``, verified and timed on the kernel's bench manifest at ``precision``."""
    manifest = inputs.load(
        paths.BENCHMARKS / spec.relative_path / f"{spec.module_name}.yaml", datatype=numpy_dtype(precision).__name__
    )
    result = api.generate(sdfg, out, manifest=manifest, matrix=matrix)
    if result.timings is None:
        raise RuntimeError(f"Alloy timed nothing for {spec.short_name}")
    return result


def nothing_to_generate(sdfg: dace.SDFG, matrix: Matrix) -> bool:
    """Whether ``sdfg`` outlines into no region (a pipeline folded every loop away): Alloy has no candidate, so the
    program is the default codegen."""
    return not regions.outline(sdfg, matrix.libm_calls).regions


def local_winners(result: api.Result) -> dict[str, Build]:
    """Every region's locally timed winner, by region symbol."""
    if result.timings is None:
        raise ValueError("local winners need a timed result")
    winners = result.timings.regions
    return {rep.region.symbol: winning_build(rep, winners[rep.region.symbol].winner) for rep in result.regions}


def linked(linker: Linker, selection: dict[str, Build]) -> dace.SDFG:
    """The outlined program calling ``selection[symbol]``'s archive for every region."""
    archives = {symbol: build.archive for symbol, build in selection.items() if build.archive is not None}
    return linker.library_sdfg(archives, frozenset(build.candidate.compiler for build in selection.values()))


def compiled_winners(
    sdfg: dace.SDFG, spec: BenchSpec, precision: Precision, matrix: Matrix | None = None
) -> tuple[dace.SDFG, CompiledSDFG]:
    """The framework columns' program: ``sdfg`` (a bench pipeline's output) outlined, each region linking its local
    winner, built by DaCe on the matrix's OpenMP runtime; with no region, ``sdfg`` itself. The archives link
    statically, so Alloy's folder goes once the program is built."""
    matrix = matrix or configuration_matrix.load()
    with tempfile.TemporaryDirectory(prefix=f"alloy_{spec.short_name}_") as tmp:
        if nothing_to_generate(sdfg, matrix):
            program = copy.deepcopy(sdfg)
        else:
            out = pathlib.Path(tmp)
            result = generated(sdfg, spec, precision, matrix, out)
            program = linked(Linker(result.program, matrix, out), local_winners(result))
        program.name = f"{sdfg.name}_alloy"  # pyright: ignore[reportAttributeAccessIssue]
        with set_temporary("compiler", "extra_cmake_args", value=cmake_args(matrix)):
            return program, program.compile()


def library(task: Task, spec: BenchSpec, linker: Linker, selection: dict[str, Build], deliver: Deliver) -> Submission:
    """The library calling ``selection[symbol]``'s archive for every region, rendered by CPF in the bench C ABI."""
    return rendered(task, spec, linked(linker, selection), deliver)


def rendered(task: Task, spec: BenchSpec, sdfg: dace.SDFG, deliver: Deliver) -> Submission:
    """``sdfg`` rendered by CPF in the bench C ABI as a library submission."""
    form = render_canonical(
        spec, spec.short_name, sdfg, DIALECT[task.language], task.precision.value, "cpu", DEFAULT_HINTS
    )
    return deliver(form.code, form.link)


def optimize(task: Task, pipeline: str, deliver: Deliver) -> Submission:
    """Alloy on ``task``'s kernel after ``pipeline``: the best library the judge scored within the kernel's budget,
    else the library of every region's local winner; with no region, CPF's default rendering of the program."""
    started = time.monotonic()
    if task.image != "cpu" or task.language not in DIALECT or task.source_mode == "restricted":
        raise NotImplementedError(f"Alloy submits a CPU C/C++ library; got {task.image}/{task.language}")
    spec = BenchSpec.load(task.kernel)
    deadline = started + resolve_kernel_timeout(spec)
    matrix = configuration_matrix.load()
    sdfg = pipeline_sdfg(spec, pipeline, task.precision)
    if nothing_to_generate(sdfg, matrix):
        return rendered(task, spec, sdfg, deliver)
    out = pathlib.Path(tempfile.mkdtemp(prefix=f"alloy_{spec.short_name}_"))
    result = generated(sdfg, spec, task.precision, matrix, out)
    timings = result.timings
    if timings is None:
        raise RuntimeError(f"Alloy timed nothing for {spec.short_name}")
    linker, judge = Linker(result.program, matrix, out), JudgeClient(judge_endpoints()[0])
    costs: list[float] = []

    def affordable() -> bool:
        # one more score, and the harness's own score of the library returned
        return deadline - time.monotonic() > 2 * max(costs, default=SCORE_GUESS_S)

    def scored(selection: dict[str, Build]) -> float:
        submission = library(task, spec, linker, selection, deliver)
        start = time.monotonic()
        reply = judge.score(submission, task.kernel)
        costs.append(time.monotonic() - start)
        return reply.speedup if reply.correct else -1.0

    references = {rep.region.symbol: rep.builds[0] for rep in result.regions}
    candidates = [
        (rep.region.symbol, screened(rep, timings.regions[rep.region.symbol].screen, TOP)) for rep in result.regions
    ]
    chosen = search(local_winners(result), references, candidates, scored, affordable)
    # every deliver builds the same .so path, so the chosen library is built last, after every trial
    return library(task, spec, linker, chosen, deliver)


def search[T](
    winners: dict[str, T],
    references: dict[str, T],
    candidates: list[tuple[str, list[T]]],
    score: Callable[[dict[str, T]], float],
    affordable: Callable[[], bool],
) -> dict[str, T]:
    """The selection to submit, by region symbol. Every region's local winner, unless the judge refuses that (a
    negative ``score``), then every region's reference; then, while ``affordable``, each region's ``candidates`` in
    turn with the others at their best, kept when the judge scores it faster than the best so far."""
    if not affordable():
        return winners
    best = score(winners)
    chosen = winners if best >= 0 else references
    for symbol, builds in candidates:
        for build in builds:
            if build is chosen[symbol]:
                continue
            if not affordable():
                return chosen
            trial = {**chosen, symbol: build}
            speedup = score(trial)
            if speedup > best:
                best, chosen = speedup, trial
    return chosen
