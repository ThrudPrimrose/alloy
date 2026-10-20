# Copyright 2026 ETH Zurich and the Alloy authors.
"""Alloy on HPCAgent-Bench: Alloy builds and verifies every region's candidates, the judge times each as a
``/profile`` stub, and the chosen library is scored once with ``/score``."""

import pathlib
import sys
import tempfile
import time
from collections.abc import Callable, Sequence
from typing import Protocol

import dace
from dace.frontend.python.parser import DaceProgram
from hpcagent_agent.tools.http_json import judge_rank, judge_timeout
from hpcagent_bench import config, paths
from hpcagent_bench.categories import Language, Preset, SourceMode
from hpcagent_bench.cpf_bridge import render_canonical
from hpcagent_bench.cpf_cache import DEFAULT_HINTS, Target
from hpcagent_bench.frameworks.benchmark import Benchmark
from hpcagent_bench.frameworks.dace_framework import PIPELINES_BY_NAME, PipelineContext
from hpcagent_bench.frameworks.framework import framework_class
from hpcagent_bench.harness.envelope import Submission
from hpcagent_bench.harness.pipeline import judge_endpoints
from hpcagent_bench.harness.profile_wire import DeviceTraceReport, LinuxperfReport, ProfileAnswer
from hpcagent_bench.harness.scoring import resolve_kernel_timeout
from hpcagent_bench.harness.task import Task
from hpcagent_bench.harness.tools import JudgeClient
from hpcagent_bench.precision import Precision, numpy_dtype
from hpcagent_bench.spec import RUNGS, BenchSpec

from alloy import api, configuration_matrix
from alloy.backend.build import Build
from alloy.backend.sweep import RegionReport
from alloy.configuration_matrix import Matrix
from alloy.evaluate.link import Linker, execution_order
from alloy.evaluate.verify import Verdict
from alloy.frontend import inputs, regions

__all__ = [
    "DEVICES",
    "DIALECT",
    "FAST_SIZE",
    "PROFILE_REPS",
    "Deliver",
    "Named",
    "Profile",
    "arch_of",
    "fast_size",
    "verified",
    "generated",
    "library",
    "linked",
    "nothing_to_generate",
    "optimize",
    "pipeline_sdfg",
    "ranked",
    "rendered",
    "stub_time",
]

#: Repetitions the judge times a stub over (one input).
PROFILE_REPS = 5
#: The size a stub is timed at when the run's preset is larger.
FAST_SIZE = Preset.M
#: Task language -> the CPF dialect the library is rendered in.
DIALECT = {Language.C: "c", Language.CPP: "c++"}
#: A target -> the device its pipeline targets.
DEVICES = {Target.CPU: dace.dtypes.DeviceType.CPU, Target.GPU: dace.dtypes.DeviceType.GPU}

#: Builds a library submission from a rendered unit and what it links against.
Deliver = Callable[[str, Sequence[str]], Submission]
#: Times one library submission on the judge: ``/profile`` in production, a fake in tests.
Profile = Callable[[Submission], ProfileAnswer]


def pipeline_sdfg(spec: BenchSpec, pipeline: str, precision: Precision, target: Target = Target.CPU) -> dace.SDFG:
    """The kernel's SDFG at ``precision`` after the bench's DaCe pipeline ``pipeline`` for ``target``."""
    framework = framework_class(f"dace_{target.text}")(f"dace_{target.text}")
    framework.set_datatype(precision.value)
    program, _ = framework.implementations(Benchmark(spec.short_name))[0]
    if not isinstance(program, DaceProgram):
        raise TypeError(f"{spec.short_name}: the dace port is not a @dace.program")
    sdfg = program.to_sdfg(simplify=False)
    PIPELINES_BY_NAME[pipeline].transform(sdfg, PipelineContext(device=DEVICES[target]))
    return sdfg


def verified(rep: RegionReport, verdicts: dict[str, Verdict]) -> list[Build]:
    """``rep``'s builds other than its reference that verified, in Alloy's build order."""
    return [build for build in rep.builds[1:] if build.name in verdicts and verdicts[build.name].ok]


def fast_size(token: str) -> Preset | None:
    """The size a stub is timed at on a run of preset ``token``: :data:`FAST_SIZE` when the run is larger, else None."""
    preset = Preset.parse(token.partition("+")[0])
    return FAST_SIZE if preset.is_rung and RUNGS.index(FAST_SIZE) < RUNGS.index(preset) else None


def generated(sdfg: dace.SDFG, spec: BenchSpec, precision: Precision, matrix: Matrix, out: pathlib.Path) -> api.Result:
    """Alloy on ``sdfg`` under ``out``, every candidate verified at ``precision`` and timed by nobody here."""
    manifest = inputs.load(
        paths.BENCHMARKS / spec.relative_path / f"{spec.module_name}.yaml", datatype=numpy_dtype(precision).__name__
    )
    result = api.generate(sdfg, out, manifest=manifest, matrix=matrix, time_locally=False)
    if result.verification is None:
        raise RuntimeError(f"Alloy verified nothing for {spec.short_name}")
    return result


def nothing_to_generate(sdfg: dace.SDFG, matrix: Matrix) -> bool:
    """Whether ``sdfg`` outlines into no region (the program is the default codegen)."""
    return not regions.outline(sdfg, matrix.libm_calls).regions


def linked(linker: Linker, selection: dict[str, Build]) -> dace.SDFG:
    """The outlined program calling ``selection[symbol]``'s archive for every region."""
    archives = {symbol: build.archive for symbol, build in selection.items() if build.archive is not None}
    return linker.library_sdfg(archives, frozenset(build.candidate.compiler for build in selection.values()))


def arch_of(task: Task) -> Target:
    """The device a task's image runs: CPU, or GPU for the ``nvidia`` and ``amd`` images."""
    return Target.CPU if task.image == "cpu" else Target.GPU


def rendered(task: Task, spec: BenchSpec, sdfg: dace.SDFG, deliver: Deliver) -> Submission:
    """``sdfg`` rendered by CPF in the bench C ABI as a library submission."""
    form = render_canonical(
        spec,
        spec.short_name,
        sdfg,
        DIALECT[task.language],
        task.precision.value,
        arch_of(task),
        DEFAULT_HINTS,
    )
    return deliver(form.code, form.link)


def library(task: Task, spec: BenchSpec, linker: Linker, selection: dict[str, Build], deliver: Deliver) -> Submission:
    """The library calling ``selection[symbol]``'s archive for every region."""
    return rendered(task, spec, linked(linker, selection), deliver)


def stub_time(answer: ProfileAnswer) -> float:
    """A stub's time: device time per repetition from a trace, else the graded linuxperf configuration's elapsed."""
    report = answer.root
    if isinstance(report, DeviceTraceReport):
        return report.device_ns_per_rep
    if isinstance(report, LinuxperfReport) and report.configs:
        return float(max(report.configs, key=lambda c: c["threads"])["elapsed_ns"])
    raise ValueError(f"no stub time in a {type(report).__name__} profile")


class Named(Protocol):
    """A candidate build, as :func:`ranked` sees it."""

    @property
    def name(self) -> str: ...


def ranked[B: Named](
    order: Sequence[str],
    start: dict[str, B],
    candidates: dict[str, list[B]],
    time_stub: Callable[[dict[str, B], str], float],
    affordable: Callable[[], bool],
) -> dict[str, B]:
    """Region by region in execution ``order``, each candidate timed as a stub over the best of the regions before
    it, the fastest kept; stops when no longer ``affordable``."""
    chosen = dict(start)
    for symbol in order:
        times: dict[str, float] = {}
        for build in [chosen[symbol], *(b for b in candidates.get(symbol, []) if b is not chosen[symbol])]:
            if not affordable():
                return chosen
            try:
                times[build.name] = time_stub({**chosen, symbol: build}, symbol)
            except Exception as exc:  # noqa: BLE001 -- a failing stub drops out of the ranking
                print(f"alloy: stub {symbol}/{build.name} dropped: {exc}", file=sys.stderr, flush=True)
        pool = {b.name: b for b in [chosen[symbol], *candidates.get(symbol, [])]}
        print(f"alloy: {symbol}: {len(times)} stubs timed", file=sys.stderr, flush=True)
        if times:
            chosen[symbol] = pool[min(times, key=times.__getitem__)]
    return chosen


def optimize(task: Task, pipeline: str, deliver: Deliver, profile: Profile | None = None) -> Submission:
    """Alloy on ``task``'s kernel after ``pipeline``: the stub-timed selection if ``/score`` grades it correct, else
    every region's reference (CPF's default rendering with no region)."""
    started = time.monotonic()
    if task.language not in DIALECT or task.source_mode is SourceMode.RESTRICTED:
        raise NotImplementedError(f"Alloy submits a C/C++ library; got {task.language.text}/{task.source_mode.text}")
    spec = BenchSpec.load(task.kernel)
    deadline = started + resolve_kernel_timeout(spec)
    matrix = configuration_matrix.load()
    sdfg = pipeline_sdfg(spec, pipeline, task.precision, arch_of(task))
    if nothing_to_generate(sdfg, matrix):
        return rendered(task, spec, sdfg, deliver)
    out = pathlib.Path(tempfile.mkdtemp(prefix=f"alloy_{spec.short_name}_"))
    result = generated(sdfg, spec, task.precision, matrix, out)
    verification = result.verification
    if verification is None:
        raise RuntimeError(f"Alloy verified nothing for {spec.short_name}")
    linker, judge = (
        Linker(result.program, matrix, out),
        JudgeClient(judge_endpoints()[0], rank=judge_rank(), timeout=judge_timeout()),
    )
    size = fast_size(config.current().service.preset)
    measure = profile or (lambda submission: judge.profile(submission, task.kernel, reps=PROFILE_REPS, size=size))

    stub_costs: list[float] = []
    score_costs: list[float] = []

    def score_reserve() -> float:
        # the selection's final score plus the harness's own grade
        return 2 * max(score_costs, default=max(stub_costs, default=0.0))

    def affordable_stub() -> bool:
        return deadline - time.monotonic() > max(stub_costs, default=0.0) + score_reserve()

    def time_stub(selection: dict[str, Build], symbol: str) -> float:
        start = time.monotonic()
        try:
            return stub_time(measure(rendered(task, spec, linker.stub(selection, symbol), deliver)))
        finally:
            stub_costs.append(time.monotonic() - start)

    references = {rep.region.symbol: rep.builds[0] for rep in result.regions}
    candidates = {rep.region.symbol: verified(rep, verification.verdicts[rep.region.symbol]) for rep in result.regions}
    chosen = ranked(execution_order(result.program.sdfg), references, candidates, time_stub, affordable_stub)
    if chosen != references and deadline - time.monotonic() > score_reserve():
        start = time.monotonic()
        correct = judge.score(library(task, spec, linker, chosen, deliver), task.kernel).correct
        score_costs.append(time.monotonic() - start)
        if correct:
            # every deliver builds the same .so path, so the returned library is built last
            return library(task, spec, linker, chosen, deliver)
    return library(task, spec, linker, references, deliver)
