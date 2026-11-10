# Copyright 2026 ETH Zurich and the Alloy authors.
"""Alloy on HPCAgent-Bench: Alloy builds and verifies every scope's candidates, the judge times each as a
``/profile`` stub, and the chosen library is scored once with ``/score``."""

import atexit
import numbers
import pathlib
import shutil
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
from hpcagent_bench.cpf.bridge import render_canonical
from hpcagent_bench.cpf.cache import DEFAULT_HINTS, Target
from hpcagent_bench.frameworks.benchmark import Benchmark
from hpcagent_bench.frameworks.dace_framework import PIPELINES_BY_NAME
from hpcagent_bench.frameworks.framework import framework_class
from hpcagent_bench.harness.envelope import Submission
from hpcagent_bench.harness.pipeline import judge_endpoints
from hpcagent_bench.harness.profile_wire import DeviceTraceReport, LinuxperfReport, ProfileAnswer
from hpcagent_bench.harness.scoring import resolve_kernel_timeout
from hpcagent_bench.harness.task import Task
from hpcagent_bench.harness.tools import JudgeClient
from hpcagent_bench.precision import Precision, numpy_dtype
from hpcagent_bench.spec import RUNGS, BenchSpec, parse_preset
from pydantic.dataclasses import dataclass

from alloy import api, configuration_matrix, gpu
from alloy.backend.build import Build
from alloy.backend.sweep import ScopeReport
from alloy.configuration_matrix import Matrix
from alloy.evaluate.link import Linker, execution_order
from alloy.evaluate.verify import Verdict
from alloy.frontend import inputs, scopes
from alloy.records import RECORD, dumped_json
from alloy.report import Mode

__all__ = [
    "DIALECT",
    "Deliver",
    "EPISODE_RECORD",
    "Episode",
    "EpisodeScope",
    "EpisodeSeconds",
    "FAST_SIZE",
    "Named",
    "PROFILE_REPS",
    "fast_size",
    "generated",
    "library",
    "linked",
    "nothing_to_generate",
    "optimize",
    "pipeline_sdfg",
    "ranked",
    "record_episode",
    "reference",
    "rendered",
    "running_sizes",
    "stub_time",
    "target_of",
    "verified",
]

#: Repetitions the judge times a stub over (one input).
PROFILE_REPS = 5
#: The size a stub is timed at when the run's preset is larger.
FAST_SIZE = Preset.M
#: Task language -> the CPF dialect the library is rendered in.
DIALECT = {Language.C: "c", Language.CPP: "c++"}

#: Builds a library submission from a rendered unit and what it links against.
Deliver = Callable[[str, Sequence[str]], Submission]
#: The episode's record, written into its working folder (the tuner runs each episode in its own).
EPISODE_RECORD = "alloy-episode.json"


@dataclass(slots=True, frozen=True, config=RECORD)
class EpisodeSeconds:
    """Wall seconds of an episode's stages: Alloy's generate, the stub timings, the final scoring, and the whole."""

    generate: float
    time_stubs: float
    score: float
    total: float


@dataclass(slots=True, frozen=True, config=RECORD)
class EpisodeScope:
    """A scope's reference build, the build delivered for it, and the delivered candidate's note."""

    symbol: str
    reference: str
    chosen: str
    note: str


@dataclass(slots=True, frozen=True, config=RECORD)
class Episode:
    """One episode of an Alloy flavor: its mode (``profile``, ``speculative`` or ``reference``), kernel, stage
    seconds and every scope's delivered build."""

    schema: int
    mode: str
    kernel: str
    seconds: EpisodeSeconds
    scopes: tuple[EpisodeScope, ...]


def record_episode(
    mode: str,
    task: Task,
    started: float,
    generate: float = 0.0,
    time_stubs: float = 0.0,
    score: float = 0.0,
    references: dict[str, Build] | None = None,
    delivered: dict[str, Build] | None = None,
) -> None:
    """Write the episode's :class:`Episode` to :data:`EPISODE_RECORD` in the working folder; ``started`` is the
    episode's ``time.monotonic()`` start, ``delivered`` the build delivered per scope of ``references``."""
    refs, picks = references or {}, delivered or {}
    scopes = tuple(
        EpisodeScope(symbol, build.name, picks[symbol].name, picks[symbol].candidate.note)
        for symbol, build in refs.items()
    )
    seconds = EpisodeSeconds(generate, time_stubs, score, time.monotonic() - started)
    episode = Episode(1, mode, task.kernel, seconds, scopes)
    (pathlib.Path.cwd() / EPISODE_RECORD).write_text(dumped_json(episode))


def pipeline_sdfg(
    spec: BenchSpec,
    pipeline: str,
    precision: Precision,
    target: Target = Target.CPU,
    offloaded: Callable[[dace.SDFG], None] | None = None,
) -> dace.SDFG:
    """The kernel's SDFG at ``precision`` after the bench's DaCe pipeline ``pipeline`` for ``target``, run with the
    symbol facts the bench's own flavor passes it; ``offloaded`` runs on a GPU program between its offload and its
    tiling (``PipelineContext.offloaded``)."""
    framework = framework_class(f"dace_{target.text}")(f"dace_{target.text}")
    framework.set_datatype(precision.value)
    program, _ = framework.implementations(Benchmark(spec.short_name))[0]
    if not isinstance(program, DaceProgram):
        raise TypeError(f"{spec.short_name}: the dace port is not a @dace.program")
    sdfg = program.to_sdfg(simplify=False)
    PIPELINES_BY_NAME[pipeline].transform(sdfg, framework.build_context(spec, offloaded))
    return sdfg


def verified(rep: ScopeReport, verdicts: dict[str, Verdict]) -> list[Build]:
    """``rep``'s builds other than its reference that verified, in Alloy's build order."""
    return [build for build in rep.builds[1:] if build.name in verdicts and verdicts[build.name].ok]


def fast_size(token: str) -> Preset | None:
    """The size a stub is timed at on a run of preset ``token``: :data:`FAST_SIZE` when the run is larger, else None."""
    preset = Preset.parse(token.partition("+")[0])
    return FAST_SIZE if preset.is_rung and RUNGS.index(FAST_SIZE) < RUNGS.index(preset) else None


def running_sizes(spec: BenchSpec, token: str) -> dict[str, int]:
    """The sizes a run of preset ``token`` grades ``spec`` at: its rung's, or a fuzzed run's anchor rung's, which its
    timed draws stay within a quarter of."""
    rung = spec.parameters.get(parse_preset(token).anchor.text, {})
    return {name: int(value) for name, value in rung.items() if isinstance(value, numbers.Integral)}


def manifest_of(spec: BenchSpec, precision: Precision) -> inputs.Manifest:
    """``spec``'s manifest in the corpus, inputs drawn at ``precision``."""
    path = paths.BENCHMARKS / spec.relative_path / f"{spec.module_name}.yaml"
    return inputs.load(path, datatype=numpy_dtype(precision).__name__)


def generated(
    sdfg: dace.SDFG,
    spec: BenchSpec,
    precision: Precision,
    matrix: Matrix,
    out: pathlib.Path,
    mode: Mode = Mode.PROFILE,
    running: dict[str, int] | None = None,
) -> api.Result:
    """Alloy on ``sdfg`` under ``out``, every candidate verified at ``precision`` and timed by nobody here; in
    speculative mode each scope's pick is the prediction's at the ``running`` sizes."""
    manifest = manifest_of(spec, precision)
    result = api.generate(sdfg, out, manifest=manifest, matrix=matrix, mode=mode, time_locally=False, running=running)
    if result.verification is None:
        raise RuntimeError(f"Alloy verified nothing for {spec.short_name}")
    return result


def nothing_to_generate(sdfg: dace.SDFG, matrix: Matrix) -> bool:
    """Whether ``sdfg`` outlines into no scope (the program is the default codegen)."""
    return not scopes.outline(sdfg, matrix.libm_calls).scopes


def linked(linker: Linker, selection: dict[str, Build]) -> dace.SDFG:
    """The outlined program calling ``selection[symbol]``'s archive for every scope."""
    archives = {symbol: build.archive for symbol, build in selection.items() if build.archive is not None}
    return linker.library_sdfg(archives, frozenset(build.candidate for build in selection.values()))


def target_of(task: Task) -> Target:
    """The target a task's image runs: CPU, or GPU for the ``nvidia`` and ``amd`` images."""
    return Target.CPU if task.image == "cpu" else Target.GPU


def with_scratch(submission: Submission, workspace_bytes: str) -> Submission:
    """The entry carves its transients out of the judge's scratch; without the request they point past a null buffer."""
    if workspace_bytes != "0":
        submission.workspace_bytes = workspace_bytes
    return submission


def rendered(task: Task, spec: BenchSpec, sdfg: dace.SDFG, deliver: Deliver) -> Submission:
    """``sdfg`` rendered by CPF in the bench C ABI as a library submission."""
    form = render_canonical(
        spec,
        spec.short_name,
        sdfg,
        DIALECT[task.language],
        task.precision.value,
        target_of(task),
        DEFAULT_HINTS,
    )
    return with_scratch(deliver(form.code, form.link), form.workspace_bytes)


def library(task: Task, spec: BenchSpec, linker: Linker, selection: dict[str, Build], deliver: Deliver) -> Submission:
    """The library calling ``selection[symbol]``'s archive for every scope."""
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
    """Scope by scope in execution ``order``, each candidate timed as a stub over the best of the scopes before
    it, the fastest kept; stops when no longer ``affordable``."""
    chosen = dict(start)
    for symbol in order:
        times: dict[str, float] = {}
        for build in [chosen[symbol], *(b for b in candidates.get(symbol, []) if b is not chosen[symbol])]:
            if not affordable():
                return chosen
            try:
                times[build.name] = time_stub({**chosen, symbol: build}, symbol)
            except Exception as exc:
                print(f"alloy: stub {symbol}/{build.name} dropped: {exc}", file=sys.stderr, flush=True)
        pool = {b.name: b for b in [chosen[symbol], *candidates.get(symbol, [])]}
        print(f"alloy: {symbol}: {len(times)} stubs timed", file=sys.stderr, flush=True)
        if times:
            chosen[symbol] = pool[min(times, key=times.__getitem__)]
    return chosen


def judge_client() -> JudgeClient:
    return JudgeClient(judge_endpoints()[0], rank=judge_rank(), timeout=judge_timeout())


def refuse_restricted(task: Task) -> None:
    if task.language not in DIALECT or task.source_mode is SourceMode.RESTRICTED:
        raise NotImplementedError(f"Alloy submits a C/C++ library; got {task.language.text}/{task.source_mode.text}")


def scratch_folder(spec: BenchSpec) -> pathlib.Path:
    """A folder that lasts as long as the process: the library links its archives statically."""
    out = pathlib.Path(tempfile.mkdtemp(prefix=f"alloy_{spec.short_name}_"))
    atexit.register(shutil.rmtree, out, ignore_errors=True)
    return out


def optimize(task: Task, pipeline: str, deliver: Deliver) -> Submission:
    """Alloy on ``task``'s kernel after ``pipeline``: the stub-timed selection if ``/score`` grades it correct, else
    every scope's reference (CPF's default rendering with no scope)."""
    started = time.monotonic()
    refuse_restricted(task)
    spec = BenchSpec.load(task.kernel)
    deadline = started + resolve_kernel_timeout(spec)
    matrix = configuration_matrix.load()
    sdfg = pipeline_sdfg(spec, pipeline, task.precision, target_of(task))
    if nothing_to_generate(sdfg, matrix):
        submission = rendered(task, spec, sdfg, deliver)
        record_episode(Mode.PROFILE.value, task, started)
        return submission
    out = scratch_folder(spec)
    generating = time.monotonic()
    result = generated(sdfg, spec, task.precision, matrix, out)
    generate = time.monotonic() - generating
    verification = result.verification
    assert verification is not None, "generated() refuses an unverified result"
    linker, judge = Linker(result.program, matrix, out), judge_client()
    size = fast_size(config.current().service.preset)

    stub_costs: list[float] = []

    def score_reserve() -> float:
        # the selection's final score plus the harness's own grade
        return 2 * max(stub_costs, default=0.0)

    def affordable_stub() -> bool:
        return deadline - time.monotonic() > max(stub_costs, default=0.0) + score_reserve()

    def time_stub(selection: dict[str, Build], symbol: str) -> float:
        start = time.monotonic()
        try:
            stub = rendered(task, spec, linker.stub(selection, symbol), deliver)
            return stub_time(judge.profile(stub, task.kernel, reps=PROFILE_REPS, size=size))
        finally:
            stub_costs.append(time.monotonic() - start)

    references = {rep.scope.symbol: rep.builds[0] for rep in result.scopes}
    candidates = {rep.scope.symbol: verified(rep, verification.verdicts[rep.scope.symbol]) for rep in result.scopes}
    ranking = time.monotonic()
    chosen = ranked(execution_order(result.program.sdfg), references, candidates, time_stub, affordable_stub)
    scoring = time.monotonic()
    correct = False
    if chosen != references and deadline - time.monotonic() > score_reserve():
        try:
            correct = judge.score(library(task, spec, linker, chosen, deliver), task.kernel).correct
        except (OSError, RuntimeError, ValueError):
            pass  # the references need no grade
    score = time.monotonic() - scoring
    delivered = chosen if correct else references
    # every deliver builds the same .so path, so the returned library is built last
    submission = library(task, spec, linker, delivered, deliver)
    record_episode(Mode.PROFILE.value, task, started, generate, scoring - ranking, score, references, delivered)
    return submission


def speculative(task: Task, pipeline: str, deliver: Deliver) -> Submission:
    """Alloy's speculative mode on ``task``'s kernel after ``pipeline``: each scope's predicted pick, verified and
    never timed, if ``/score`` grades it correct, else every scope's reference. A GPU task's device maps take their
    speculated threadblock shapes instead (:func:`speculative_gpu`)."""
    if target_of(task) is Target.GPU:
        return speculative_gpu(task, pipeline)
    started = time.monotonic()
    refuse_restricted(task)
    spec = BenchSpec.load(task.kernel)
    matrix = configuration_matrix.load()
    sdfg = pipeline_sdfg(spec, pipeline, task.precision, target_of(task))
    if nothing_to_generate(sdfg, matrix):
        submission = rendered(task, spec, sdfg, deliver)
        record_episode(Mode.SPECULATIVE.value, task, started)
        return submission
    out = scratch_folder(spec)
    running = running_sizes(spec, config.current().service.preset)
    generating = time.monotonic()
    result = generated(sdfg, spec, task.precision, matrix, out, Mode.SPECULATIVE, running)
    generate = time.monotonic() - generating
    linker = Linker(result.program, matrix, out)
    references = {rep.scope.symbol: rep.builds[0] for rep in result.scopes}
    chosen = {**references, **(result.winners or {})}
    judge = judge_client()
    scoring = time.monotonic()
    pick = library(task, spec, linker, chosen, deliver)
    baseline = library(task, spec, linker, references, deliver)
    better = chosen != references and faster_correct(judge, pick, baseline, task.kernel)
    score = time.monotonic() - scoring
    delivered = chosen if better else references
    # every deliver builds the same .so path, so the returned library is built last
    submission = library(task, spec, linker, delivered, deliver)
    record_episode(Mode.SPECULATIVE.value, task, started, generate, 0.0, score, references, delivered)
    return submission


def reference(task: Task, pipeline: str, deliver: Deliver) -> Submission:
    """The plain arm: ``task``'s kernel after ``pipeline`` rendered by CPF with no search, graded as the Alloy arms
    are (a GPU task as the bench's GPU form)."""
    started = time.monotonic()
    spec = BenchSpec.load(task.kernel)
    if target_of(task) is Target.GPU:
        submission = device_submission(task, spec, pipeline_sdfg(spec, pipeline, task.precision, Target.GPU))
    else:
        refuse_restricted(task)
        submission = rendered(task, spec, pipeline_sdfg(spec, pipeline, task.precision, target_of(task)), deliver)
    record_episode("reference", task, started)
    return submission


def faster_correct(judge: JudgeClient, pick: Submission, baseline: Submission, kernel: str) -> bool:
    """Whether ``pick`` grades correct and no slower than ``baseline``; a judge that does not answer keeps the
    references, the library that is safe without a grade."""
    try:
        graded, reference = judge.score(pick, kernel), judge.score(baseline, kernel)
    except (OSError, RuntimeError, ValueError):
        return False
    return graded.correct and (not reference.correct or graded.speedup >= reference.speedup)


#: A GPU image -> the dialect its device maps' register use is read in: nvcc's report on an NVIDIA device, hipcc's
#: on an AMD one. The submission itself is the bench's GPU form, HIP on either (``bridge.DEVICE_LANGUAGE``).
ANALYSIS_DIALECT = {"nvidia": "cuda", "amd": "hip"}


def device_submission(task: Task, spec: BenchSpec, sdfg: dace.SDFG) -> Submission:
    """``sdfg`` rendered by CPF in the bench C ABI as the bench's GPU form: a HIP host and device source."""
    form = render_canonical(spec, spec.short_name, sdfg, "hip", task.precision.value, Target.GPU, DEFAULT_HINTS)
    submission = Submission(language=Language.HIP, source=form.code, device_source=form.device_code)
    return with_scratch(submission, form.workspace_bytes)


def speculative_gpu(task: Task, pipeline: str) -> Submission:
    """Every device map of ``task``'s kernel after ``pipeline`` at its speculated threadblock shape
    (:func:`alloy.gpu.speculate`, for this machine's device), if ``/score`` grades it correct, else the pipeline's
    own blocks."""
    if task.image not in ANALYSIS_DIALECT:
        raise NotImplementedError(f"Alloy's GPU mode reads NVIDIA or AMD compiler reports; got image {task.image}")
    spec = BenchSpec.load(task.kernel)
    dialect = ANALYSIS_DIALECT[task.image]

    def run(shapes: dict[int, gpu.Shape]) -> dace.SDFG:
        return pipeline_sdfg(spec, pipeline, task.precision, Target.GPU, offloaded=gpu.blocks(shapes))

    program, picks = gpu.speculate(run, dialect, gpu.native_arch(dialect))
    blocks = {ordinal: pick.shape for ordinal, pick in picks.items()}
    print(f"alloy: {spec.short_name}: threadblocks {blocks}", file=sys.stderr, flush=True)
    chosen = device_submission(task, spec, program)
    if judge_client().score(chosen, task.kernel).correct:
        return chosen
    return device_submission(task, spec, run({}))
