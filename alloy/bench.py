# Copyright 2026 ETH Zurich and the Alloy authors.
"""Alloy as an HPCAgent-Bench optimizer (needs ``alloy[bench]``; the core never imports this module). A bench DaCe
pipeline gives the SDFG; Alloy builds, verifies and times every region candidate and starts from each region's local
winner; while the kernel's time budget allows, the judge's ``/score`` ranks the :data:`TOP` screened candidates of
each region, one region at a time with the others at their best so far; the best library is submitted."""

import pathlib
import tempfile
import time
from collections.abc import Callable, Sequence

import dace
from dace.frontend.python.parser import DaceProgram
from hpcagent_bench import paths
from hpcagent_bench.cpf_bridge import render_canonical
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
from alloy.evaluate.link import Linker
from alloy.evaluate.timing import Measured, winning_build
from alloy.frontend import inputs

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


def library(task: Task, spec: BenchSpec, linker: Linker, selection: dict[str, Build], deliver: Deliver) -> Submission:
    """The library calling ``selection[symbol]``'s archive for every region, rendered by CPF in the bench C ABI."""
    archives = {symbol: build.archive for symbol, build in selection.items() if build.archive is not None}
    compilers = frozenset(build.candidate.compiler for build in selection.values())
    sdfg = linker.library_sdfg(archives, compilers)
    form = render_canonical(spec, spec.short_name, sdfg, DIALECT[task.language], task.precision.value, "cpu")
    return deliver(form.code, form.link)


def optimize(task: Task, pipeline: str, deliver: Deliver) -> Submission:
    """Alloy on ``task``'s kernel after ``pipeline``: the best library the judge scored within the kernel's budget,
    else the library of every region's local winner."""
    started = time.monotonic()
    if task.image != "cpu" or task.language not in DIALECT or task.source_mode == "restricted":
        raise NotImplementedError(f"Alloy submits a CPU C/C++ library; got {task.image}/{task.language}")
    spec = BenchSpec.load(task.kernel)
    deadline = started + resolve_kernel_timeout(spec)
    out = pathlib.Path(tempfile.mkdtemp(prefix=f"alloy_{spec.short_name}_"))
    matrix = configuration_matrix.load()
    manifest = inputs.load(
        paths.BENCHMARKS / spec.relative_path / f"{spec.module_name}.yaml",
        datatype=numpy_dtype(task.precision).__name__,
    )
    result = api.generate(pipeline_sdfg(spec, pipeline, task.precision), out, manifest=manifest, matrix=matrix)
    timings = result.timings
    if timings is None:
        raise RuntimeError(f"Alloy timed nothing for {spec.short_name}")
    linker, judge = Linker(result.program, matrix, out), JudgeClient(judge_endpoints()[0])
    costs: list[float] = []

    def affordable() -> bool:
        # one more score, and the harness's own score of the library returned
        return deadline - time.monotonic() > 2 * max(costs, default=SCORE_GUESS_S)

    def scored(selection: dict[str, Build]) -> tuple[float, Submission]:
        submission = library(task, spec, linker, selection, deliver)
        start = time.monotonic()
        reply = judge.score(submission, task.kernel)
        costs.append(time.monotonic() - start)
        speedup = reply.get("speedup")
        if reply.get("correct") is not True or not isinstance(speedup, int | float):
            return -1.0, submission
        return float(speedup), submission

    chosen = {
        rep.region.symbol: winning_build(rep, timings.regions[rep.region.symbol].winner) for rep in result.regions
    }
    if not affordable():
        return library(task, spec, linker, chosen, deliver)
    best, submission = scored(chosen)
    if best < 0:  # the judge refused the local winners: fall back to every region's reference
        chosen = {rep.region.symbol: rep.builds[0] for rep in result.regions}
        submission = library(task, spec, linker, chosen, deliver)
    for rep in result.regions:
        for build in screened(rep, timings.regions[rep.region.symbol].screen, TOP):
            if build is chosen[rep.region.symbol]:
                continue
            if not affordable():
                return submission
            trial = {**chosen, rep.region.symbol: build}
            speedup, candidate = scored(trial)
            if speedup > best:
                best, submission, chosen = speedup, candidate, trial
    return submission
