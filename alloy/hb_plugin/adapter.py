# Copyright 2026 ETH Zurich and the Alloy authors.
"""Alloy on HPCAgent-Bench: Alloy builds and verifies every scope's candidates, the judge times each as a
``/profile`` stub, and the chosen library is scored once with ``/score``."""

import atexit
import hashlib
import numbers
import os
import pathlib
import shutil
import sys
import tempfile
import time
from collections.abc import Callable, Sequence

import dace
from dace.config import set_temporary
from dace.frontend.python.parser import DaceProgram
from hpcagent_agent.tools.http_json import judge_rank, terminal_timeout
from hpcagent_bench import config, paths
from hpcagent_bench.categories import Language, Preset, SourceMode
from hpcagent_bench.cpf.bridge import RenderedForm, render_canonical
from hpcagent_bench.cpf.cache import DEFAULT_HINTS, Target
from hpcagent_bench.cpf.canonical import PARSE_SIMPLIFY
from hpcagent_bench.frameworks.benchmark import Benchmark
from hpcagent_bench.frameworks.dace_framework import (
    PIPELINES_BY_NAME,
    DaceFramework,
    apply_pipeline_config,
    enforce_gpu_residency,
    pipeline_canonicalize,
    pool_gpu_transients,
)
from hpcagent_bench.frameworks.framework import framework_class
from hpcagent_bench.harness.envelope import Submission
from hpcagent_bench.harness.judge_wire import ScorePreview
from hpcagent_bench.harness.pipeline import judge_endpoints
from hpcagent_bench.harness.profile_wire import DeviceTraceReport, LinuxperfReport, ProfileAnswer
from hpcagent_bench.harness.scoring import resolve_kernel_timeout
from hpcagent_bench.harness.task import Task
from hpcagent_bench.harness.tools import JudgeClient
from hpcagent_bench.precision import Precision, numpy_dtype
from hpcagent_bench.spec import RUNGS, BenchSpec, parse_preset

from alloy import api, configuration_matrix, gpu, gpu_build
from alloy.backend import intrinsics
from alloy.backend.build import Build
from alloy.backend.sweep import ScopeReport
from alloy.configuration_matrix import Matrix
from alloy.evaluate.link import Linker
from alloy.evaluate.verify import Verdict
from alloy.frontend import inputs, scopes
from alloy.hb_plugin.episode import PLAIN, EpisodeScope, EpisodeSeconds, Keep, episode, keep_episode, scope_record
from alloy.report import Mode

__all__ = [
    "DIALECT",
    "Deliver",
    "FAST_SIZE",
    "PROFILE_REPS",
    "fast_size",
    "generated",
    "library",
    "linked",
    "nothing_to_generate",
    "optimize",
    "pipeline_sdfg",
    "plain",
    "record_episode",
    "scope_records",
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


def record_episode(
    keep: Keep,
    mode: str,
    task: Task,
    started: float,
    generate: float = 0.0,
    time_stubs: float = 0.0,
    score: float = 0.0,
    stubs: int = 0,
    scopes: tuple[EpisodeScope, ...] = (),
) -> None:
    """Keep the episode's record (:mod:`alloy.hb_plugin.episode`) through ``keep``; ``started`` is the episode's
    ``time.monotonic()`` start, ``stubs`` the stub timings it took, ``scopes`` every scope's record."""
    seconds = EpisodeSeconds(generate, time_stubs, score, time.monotonic() - started)
    keep_episode(keep, episode(mode, task.kernel, seconds, stubs, scopes))


def scope_records(
    result: api.Result,
    matrix: Matrix,
    delivered: dict[str, Build] | None,
    timed: dict[str, dict[str, float]] | None = None,
) -> tuple[EpisodeScope, ...]:
    """Every scope's record of ``result``: ``delivered`` the build per scope (``None``: the plain program), ``timed``
    the stub ns per scope and build name."""
    verdicts = result.verification.verdicts if result.verification is not None else {}
    predicted = result.predictions or {}
    return tuple(
        scope_record(
            rep,
            matrix,
            None if delivered is None else delivered[rep.scope.symbol],
            verdicts.get(rep.scope.symbol, {}),
            (timed or {}).get(rep.scope.symbol, {}),
            predicted.get(rep.scope.symbol),
        )
        for rep in result.scopes
    )


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
    if not isinstance(framework, DaceFramework):
        raise TypeError(f"dace_{target.text} is not a DaCe framework")
    framework.set_datatype(precision.value)
    program, _ = framework.implementations(Benchmark(spec.short_name))[0]
    if not isinstance(program, DaceProgram):
        raise TypeError(f"{spec.short_name}: the dace port is not a @dace.program")
    pipe = PIPELINES_BY_NAME[pipeline]
    # as DaceFramework.build_sdfgs does: the pipeline's config, and canon parsed as the CPF cache parses it
    apply_pipeline_config(pipe)
    sdfg = program.to_sdfg(simplify=PARSE_SIMPLIFY if pipe.transform is pipeline_canonicalize else False)
    pipe.transform(sdfg, framework.build_context(spec, offloaded))
    if target is Target.GPU:  # the bench's residency contract, after every GPU pipeline
        enforce_gpu_residency(sdfg)
        pool_gpu_transients(sdfg)
    return sdfg


def verified(rep: ScopeReport, verdicts: dict[str, Verdict]) -> list[Build]:
    """``rep``'s builds other than its reference that verified, in Alloy's build order."""
    return [
        build
        for build in rep.builds[1:]
        if build.name in verdicts and verdicts[build.name].ok and not build.duplicate_of
    ]


def fast_size(token: str) -> Preset | None:
    """The size a stub is timed at on a run of preset ``token``: :data:`FAST_SIZE` when the run (a fuzzed one's
    anchor) is larger, else None."""
    return FAST_SIZE if RUNGS.index(FAST_SIZE) < RUNGS.index(parse_preset(token).anchor) else None


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
    *,
    time_locally: bool = False,
    deadline: float | None = None,
) -> api.Result:
    """Alloy on ``sdfg`` under ``out``, every candidate verified at ``precision``; in profile mode timed here when
    ``time_locally`` until ``deadline``, in speculative mode each scope's pick the prediction's at the ``running`` sizes."""
    manifest = manifest_of(spec, precision)
    result = api.generate(
        sdfg,
        out,
        manifest=manifest,
        matrix=matrix,
        mode=mode,
        time_locally=time_locally,
        deadline=deadline,
        running=running,
    )
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


def delivery(
    task: Task, spec: BenchSpec, pipeline: str, linker: Linker, delivered: dict[str, Build] | None, deliver: Deliver
) -> Submission:
    """The library of the ``delivered`` selection, or without one the plain program (:func:`plain`)."""
    return (
        plain(task, spec, pipeline, deliver) if delivered is None else library(task, spec, linker, delivered, deliver)
    )


def stub_time(answer: ProfileAnswer) -> float:
    """A stub's time: device time per repetition from a trace, else the graded linuxperf configuration's elapsed."""
    report = answer.root
    if isinstance(report, DeviceTraceReport):
        return float(report.device_ns_per_rep)
    if isinstance(report, LinuxperfReport) and report.configs:
        return float(max(report.configs, key=lambda c: c["threads"])["elapsed_ns"])
    raise ValueError(f"no stub time in a {type(report).__name__} profile")


#: Scales the kernel's agent-run budget for profile mode (E1b, the tuning-budget curve); 1 is the agent's budget.
BUDGET_SCALE_ENV = "ALLOY_BUDGET_SCALE"


def budget(spec: BenchSpec) -> float:
    """The seconds profile mode may spend on ``spec``: the kernel's agent-run budget times $ALLOY_BUDGET_SCALE."""
    scale = float(os.environ.get(BUDGET_SCALE_ENV, "1"))
    if not scale > 0:
        raise ValueError(f"{BUDGET_SCALE_ENV}={scale}: a positive factor")
    return scale * float(resolve_kernel_timeout(spec))


def judge_client() -> JudgeClient:
    """A client that waits for a grade as long as the router lets the judge take: given up early, a slow kernel's
    ``/score`` reads as no grade and the plain program is delivered in place of the pick."""
    # the rank is this worker's judge, $JUDGE_URL (as run_tuner pairs them); the endpoint list is for a bare call
    url = os.environ.get("JUDGE_URL") or judge_endpoints()[0]
    return JudgeClient(url, rank=judge_rank(), timeout=terminal_timeout())


def refuse_restricted(task: Task) -> None:
    if task.language not in DIALECT or task.source_mode is SourceMode.RESTRICTED:
        raise NotImplementedError(f"Alloy submits a C/C++ library; got {task.language.text}/{task.source_mode.text}")


def scratch_folder(spec: BenchSpec) -> pathlib.Path:
    """A folder that lasts as long as the process: the library links its archives statically."""
    out = pathlib.Path(tempfile.mkdtemp(prefix=f"alloy_{spec.short_name}_"))
    atexit.register(shutil.rmtree, out, ignore_errors=True)
    return out


def optimize(
    task: Task, pipeline: str, deliver: Deliver, keep: Keep, *, reference_fp: bool = False,
    folder: pathlib.Path | None = None,
) -> Submission:  # fmt: skip
    """Alloy on ``task``'s kernel after ``pipeline``: the selection Alloy's timer picks (the alloy_profile tool's) if
    ``/score`` grades it correct and no slower than the plain program (:func:`plain`, CPF's default rendering with no scope), else the plain program. A
    GPU task's device maps take profiled threadblock shapes instead (:func:`profile_gpu`). ``reference_fp`` searches
    only the reference's FP semantics (:func:`configuration_matrix.at_reference_fp`)."""
    if target_of(task) is Target.GPU:
        return profile_gpu(task, pipeline, keep, folder)
    started = time.monotonic()
    refuse_restricted(task)
    spec = BenchSpec.load(task.kernel)
    deadline = started + budget(spec)
    matrix = configuration_matrix.load()
    matrix = configuration_matrix.at_reference_fp(matrix) if reference_fp else matrix
    sdfg = pipeline_sdfg(spec, pipeline, task.precision, target_of(task))
    if nothing_to_generate(sdfg, matrix):
        submission = rendered(task, spec, sdfg, deliver)
        record_episode(keep, Mode.PROFILE.value, task, started)
        return submission
    out, judge = scratch_folder(spec), judge_client()
    # the plain program's grade first: the pick is compared to it, and its cost is what the pick's grade will take
    scoring = time.monotonic()
    plain_grade = public_grade(judge, plain(task, spec, pipeline, deliver), task.kernel)
    score_cost = time.monotonic() - scoring
    generating = time.monotonic()
    # Alloy's own timer, as the alloy_profile tool's, stopped in time to grade the pick
    result = generated(sdfg, spec, task.precision, matrix, out, time_locally=True, deadline=deadline - score_cost)
    generate = time.monotonic() - generating
    linker = Linker(result.program, matrix, out)
    references = {rep.scope.symbol: rep.builds[0] for rep in result.scopes}
    chosen = {**references, **(result.winners or {})}
    picking = time.monotonic()
    delivered = None
    if chosen != references and plain_grade is not None and deadline - time.monotonic() > score_cost:
        delivered = graded_pick(
            judge,
            chosen,
            references,
            lambda selection: library(task, spec, linker, selection, deliver),
            lambda: plain(task, spec, pipeline, deliver),
            task.kernel,
            baseline=plain_grade,
        )
    score = score_cost + time.monotonic() - picking
    # every deliver builds the same .so path, so the returned library is built last
    submission = delivery(task, spec, pipeline, linker, delivered, deliver)
    timed = {
        symbol: {arm: m.median * 1e9 for arm, m in scope.screen.items()}
        for symbol, scope in (result.timings.scopes.items() if result.timings is not None else ())
    }
    record_episode(
        keep,
        Mode.PROFILE.value,
        task,
        started,
        generate,
        0.0,
        score,
        sum(map(len, timed.values())),  # every arm the timer measured, the reference among them
        scope_records(result, matrix, delivered, timed),
    )
    return submission


def reference(task: Task, pipeline: str, deliver: Deliver, keep: Keep) -> Submission:
    """``pipeline``'s program as CPF renders it with no scope outlined: the column Alloy's modes are compared to,
    graded by the same judge on the same draws."""
    started = time.monotonic()
    refuse_restricted(task)
    submission = plain(task, BenchSpec.load(task.kernel), pipeline, deliver)
    record_episode(keep, "none", task, started)
    return submission


def plain(task: Task, spec: BenchSpec, pipeline: str, deliver: Deliver) -> Submission:
    """``pipeline``'s program rendered by CPF with no scope outlined: what alloy_none delivers, and what an Alloy
    mode delivers when its pick does not grade faster."""
    return rendered(task, spec, pipeline_sdfg(spec, pipeline, task.precision, target_of(task)), deliver)


def speculative(
    task: Task, pipeline: str, deliver: Deliver, keep: Keep, folder: pathlib.Path | None = None
) -> Submission:
    """Alloy's speculative mode on ``task``'s kernel after ``pipeline``: each scope's predicted pick, verified and
    never timed, if ``/score`` grades it correct and no slower than the plain program, else the plain program. A GPU
    task's device maps take their speculated threadblock shapes instead (:func:`speculative_gpu`)."""
    if target_of(task) is Target.GPU:
        return speculative_gpu(task, pipeline, keep, folder)
    started = time.monotonic()
    refuse_restricted(task)
    spec = BenchSpec.load(task.kernel)
    matrix = configuration_matrix.load()
    sdfg = pipeline_sdfg(spec, pipeline, task.precision, target_of(task))
    if nothing_to_generate(sdfg, matrix):
        submission = rendered(task, spec, sdfg, deliver)
        record_episode(keep, Mode.SPECULATIVE.value, task, started)
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
    delivered = graded_pick(
        judge,
        chosen,
        references,
        lambda selection: library(task, spec, linker, selection, deliver),
        lambda: plain(task, spec, pipeline, deliver),
        task.kernel,
    )
    score = time.monotonic() - scoring
    # every deliver builds the same .so path, so the returned library is built last
    submission = delivery(task, spec, pipeline, linker, delivered, deliver)
    records = scope_records(result, matrix, delivered)
    record_episode(keep, Mode.SPECULATIVE.value, task, started, generate, 0.0, score, 0, records)
    return submission


def graded_pick[B](
    judge: JudgeClient,
    chosen: dict[str, B],
    references: dict[str, B],
    build: Callable[[dict[str, B]], Submission],
    plain_program: Callable[[], Submission],
    kernel: str,
    baseline: ScorePreview | None = None,
) -> dict[str, B] | None:
    """``chosen`` if ``/score`` grades it correct and no slower than ``plain_program`` (graded here, or its grade
    ``baseline`` when given); else ``None``, the plain program (:func:`plain`). A pick of every reference is no
    pick."""
    if chosen == references:
        return None
    plain_grade = (lambda: baseline) if baseline is not None else (lambda: judge.score(plain_program(), kernel))
    return chosen if faster_correct(judge, lambda: build(chosen), plain_grade, kernel) else None


def public_grade(judge: JudgeClient, submission: Submission, kernel: str) -> ScorePreview | None:
    """``/score`` of ``submission``, or None when the judge does not answer."""
    try:
        return judge.score(submission, kernel)
    except (OSError, RuntimeError, ValueError):
        return None


def faster_correct(
    judge: JudgeClient, pick: Callable[[], Submission], baseline: Callable[[], ScorePreview] | None, kernel: str
) -> bool:
    """Whether ``pick`` grades correct and no slower than ``baseline``'s grade (if any); a judge that does not
    answer keeps the plain program, the library that is safe without a grade. The pick is graded first: the baseline
    may build into the .so they share."""
    try:
        graded = judge.score(pick(), kernel)
        reference = baseline() if baseline is not None else None
    except (OSError, RuntimeError, ValueError):
        return False
    return graded.correct and (reference is None or not reference.correct or graded.speedup >= reference.speedup)


#: A GPU image -> the dialect of its device: the bench's GPU form is rendered in it (``dace_emit.device_units``) and
#: the device maps' register use is read from its compiler's report (nvcc, hipcc).
ANALYSIS_DIALECT = {"nvidia": "cuda", "amd": "hip"}


def gpu_form(task: Task, spec: BenchSpec, sdfg: dace.SDFG, dialect: str) -> RenderedForm:
    """``sdfg`` rendered by CPF in the bench C ABI as the bench's GPU form in ``dialect``."""
    return render_canonical(spec, spec.short_name, sdfg, dialect, task.precision.value, Target.GPU, DEFAULT_HINTS)


def source_pair(dialect: str, form: RenderedForm) -> Submission:
    """``form`` as the host and device sources the judge builds."""
    submission = Submission(language=Language.parse(dialect), source=form.code, device_source=form.device_code)
    return with_scratch(submission, form.workspace_bytes)


def built_library(dialect: str, form: RenderedForm, spec: BenchSpec, folder: pathlib.Path) -> Submission:
    """``form`` built in ``folder`` by the default candidate with the catalog libraries it calls linked, as a library
    submission."""
    compilers = gpu_build.load()
    default = gpu_build.candidates(compilers, dialect, "atomic" in form.device_code)[0]
    result = gpu_build.build(
        compilers, default, form.code, form.device_code, form_folder(folder, form), gpu_arch(dialect),
        tuple(form.libraries),
    )  # fmt: skip
    if result.library is None:
        why = result.error.splitlines()[-1] if result.error else "no library"
        raise RuntimeError(
            f"{spec.short_name}: the {dialect} form calling {', '.join(form.libraries)} did not build: {why}"
        )
    return with_scratch(Submission(language=Language.parse(dialect), library=str(result.library)), form.workspace_bytes)


def form_folder(folder: pathlib.Path, form: RenderedForm) -> pathlib.Path:
    """A folder of its own under ``folder`` for ``form``'s builds: two programs (two threadblock shapes) never share
    a library path the judge might have loaded."""
    digest = hashlib.sha256((form.code + "\0" + form.device_code).encode()).hexdigest()[:12]
    return folder / f"alloy-gpu-{digest}"


def device_submission(
    task: Task, spec: BenchSpec, sdfg: dace.SDFG, dialect: str, folder: pathlib.Path | None = None
) -> Submission:
    """``sdfg``'s GPU form as the submission the judge grades: the host and device sources, which it builds. A form
    that calls a catalog library (hipBLAS for a BLAS node) is built in ``folder`` with the library linked and
    submitted as that library, since the judge links a source pair's libraries only on a ``startup.load`` request,
    which Alloy's setups refuse; ``folder`` is the episode's, the only place a submitted path may live."""
    form = gpu_form(task, spec, sdfg, dialect)
    if form.libraries and folder is not None:
        return built_library(dialect, form, spec, folder)
    return source_pair(dialect, form)


def form_dialect(task: Task) -> str:
    """The dialect ``task``'s GPU form is rendered and submitted in: its language when that is a device one, else
    its image's."""
    return task.language.text if task.language.text in ANALYSIS_DIALECT.values() else gpu_dialect(task)


def gpu_dialect(task: Task) -> str:
    if task.image not in ANALYSIS_DIALECT:
        raise NotImplementedError(f"Alloy's GPU mode reads NVIDIA or AMD compiler reports; got image {task.image}")
    return ANALYSIS_DIALECT[task.image]


def gpu_pipeline(task: Task, spec: BenchSpec, pipeline: str) -> gpu.Pipeline:
    """``pipeline``'s GPU program with the given device maps' threadblock shapes; ``{}`` keeps its own blocks."""

    def run(shapes: dict[int, gpu.Shape]) -> dace.SDFG:
        return pipeline_sdfg(spec, pipeline, task.precision, Target.GPU, offloaded=gpu.blocks(shapes))

    return run


def gpu_scopes(shapes: dict[int, gpu.Shape], delivered: bool, note: str) -> tuple[EpisodeScope, ...]:
    """A GPU episode's record per device map: its threadblock shape when ``delivered``, else the pipeline's own
    blocks (``none``) with the reason in ``note``; one ``program`` entry when no map was identified."""
    if not shapes:
        return (EpisodeScope("program", "pipeline", PLAIN[0], note, {}, None),)
    blocks = {ordinal: ",".join(str(n) for n in shape) for ordinal, shape in sorted(shapes.items())}
    return tuple(
        EpisodeScope(
            f"map{o}", "pipeline", block if delivered else PLAIN[0], note, {"block": block} if delivered else {}, None
        )
        for o, block in blocks.items()
    )


def gpu_arch(dialect: str) -> str:
    """This device's target as a compiler spells it: ``sm_89`` for CUDA, the ``gfx`` name for HIP."""
    arch = gpu.native_arch(dialect)
    return f"sm_{arch.replace('.', '')}" if dialect == "cuda" else arch


def gpu_libraries(
    task: Task, spec: BenchSpec, program: dace.SDFG, folder: pathlib.Path | None = None
) -> list[tuple[gpu_build.GpuBuild, Submission]]:
    """The device candidates of ``program`` (A10: compiler, floating-point level, and where scalars are declared,
    :mod:`alloy.gpu_build`), each built into a library, the default first; a build this machine refuses or a
    duplicate device object drops out."""
    dialect = form_dialect(task)

    def rendered_form(scalar_decl: str, intrinsic: bool = False) -> RenderedForm:
        source = intrinsics.device_rendered(program, dialect) if intrinsic else program
        with set_temporary("compiler", "cpu", "codegen_params", "scalar_decl", value=scalar_decl or "eager"):
            return render_canonical(
                spec, spec.short_name, source, dialect, task.precision.value, Target.GPU, DEFAULT_HINTS
            )

    forms = {("", False): rendered_form("")}
    # the episode's folder when there is one: the judge takes a submitted library only from there
    compilers, folder, arch = gpu_build.load(), folder or scratch_folder(spec), gpu_arch(dialect)
    folder = form_folder(folder, forms["", False])
    seen: set[str] = set()
    built: list[tuple[gpu_build.GpuBuild, Submission]] = []
    for candidate in gpu_build.candidates(compilers, dialect, "atomic" in forms["", False].device_code):
        key = (candidate.scalar_decl, candidate.intrinsic)
        try:
            form = forms[key] if key in forms else forms.setdefault(key, rendered_form(*key))
        except intrinsics.Refused as refused:
            print(f"alloy: {spec.short_name}: no intrinsic tasklets: {refused}", file=sys.stderr, flush=True)
            continue
        result = gpu_build.build(compilers, candidate, form.code, form.device_code, folder, arch, tuple(form.libraries))
        if result.library is None or result.device_hash in seen:
            why = result.error.splitlines()[-1] if result.error else "a duplicate device object"
            print(
                f"alloy: {spec.short_name}: device build {candidate.name} dropped: {why}", file=sys.stderr, flush=True
            )
            continue
        seen.add(result.device_hash)
        submission = Submission(language=Language.parse(dialect), library=str(result.library))
        built.append((result, with_scratch(submission, form.workspace_bytes)))
    return built


def profile_gpu(task: Task, pipeline: str, keep: Keep, folder: pathlib.Path | None = None) -> Submission:
    """Every device map of ``task``'s kernel after ``pipeline`` at its profiled threadblock shape: the speculated
    shapes (:func:`alloy.gpu.speculate`), then each map's next ranked ones timed by the judge (:func:`alloy.gpu.descend`)
    while the kernel's time allows; delivered if ``/score`` grades it correct and no slower than the pipeline's own
    blocks, else those."""
    started = time.monotonic()
    spec = BenchSpec.load(task.kernel)
    deadline = started + budget(spec)
    dialect, run = gpu_dialect(task), gpu_pipeline(task, spec, pipeline)
    judge, size = judge_client(), fast_size(config.current().service.preset)
    default = device_submission(task, spec, run({}), form_dialect(task), folder)
    try:
        _, picks = gpu.speculate(run, dialect, gpu.native_arch(dialect))
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"alloy: {spec.short_name}: no speculated threadblocks, default kept: {exc}", file=sys.stderr, flush=True)
        record_episode(keep, "gpu-profile", task, started, scopes=gpu_scopes({}, False, f"no speculated blocks: {exc}"))
        return default
    costs: list[float] = []

    def timed(program: dace.SDFG) -> float | None:
        start = time.monotonic()
        try:
            shaped = device_submission(task, spec, program, form_dialect(task), folder)
            return stub_time(judge.profile(shaped, task.kernel, reps=PROFILE_REPS, size=size))
        except (OSError, RuntimeError, ValueError) as exc:
            # a shape the device cannot launch, a refused profile, or no time in the report: not a candidate
            print(f"alloy: {spec.short_name}: profile dropped: {exc}", file=sys.stderr, flush=True)
            return None
        finally:
            costs.append(time.monotonic() - start)

    def affordable() -> bool:
        # one more profile, then the pick's and the default's grades and the harness's own
        return bool(deadline - time.monotonic() > 4 * max(costs, default=0.0))

    shapes = gpu.descend(run, picks, timed, affordable)
    print(f"alloy: {spec.short_name}: threadblocks {shapes} after {len(costs)} profiles", file=sys.stderr, flush=True)
    program = run(shapes)
    chosen, build_name = device_submission(task, spec, program, form_dialect(task), folder), "default"
    best: float | None = None
    for result, library in gpu_libraries(task, spec, program, folder)[1:]:  # the default build is the source's own
        if not affordable():
            break
        start = time.monotonic()
        try:
            seconds = stub_time(judge.profile(library, task.kernel, reps=PROFILE_REPS, size=size))
        except (OSError, RuntimeError, ValueError) as exc:
            print(f"alloy: {spec.short_name}: {result.candidate.name} not timed: {exc}", file=sys.stderr, flush=True)
            continue
        finally:
            costs.append(time.monotonic() - start)
        best = best if best is not None else timed(program)
        if best is not None and seconds < best:
            best, chosen, build_name = seconds, library, result.candidate.name
    kept = faster_correct(judge, lambda: chosen, lambda: judge.score(default, task.kernel), task.kernel)
    note = f"profiled, device build {build_name}" if kept else "graded slower or wrong: the pipeline's blocks"
    record_episode(keep, "gpu-profile", task, started, stubs=len(costs), scopes=gpu_scopes(shapes, kept, note))
    return chosen if kept else default


def speculated_library(
    task: Task, spec: BenchSpec, program: dace.SDFG, folder: pathlib.Path | None = None
) -> tuple[Submission, str]:
    """The device build the compilers' resource reports rank first (:func:`alloy.gpu_build.resource_key`), or the
    source when no candidate ranks strictly ahead of the default build."""
    dialect = form_dialect(task)
    builds = gpu_libraries(task, spec, program, folder)
    keys = [gpu_build.resource_key(gpu_build.usage(result, dialect)) for result, _ in builds]
    if len(builds) > 1 and (best := min(range(len(builds)), key=keys.__getitem__)) > 0 and keys[best] < keys[0]:
        return builds[best][1], builds[best][0].candidate.name
    return device_submission(task, spec, program, dialect, folder), "default"


def speculative_gpu(task: Task, pipeline: str, keep: Keep, folder: pathlib.Path | None = None) -> Submission:
    """Every device map of ``task``'s kernel after ``pipeline`` at its speculated threadblock shape
    (:func:`alloy.gpu.speculate`, for this machine's device), if ``/score`` grades it correct, else the pipeline's
    own blocks."""
    started = time.monotonic()
    spec = BenchSpec.load(task.kernel)
    dialect, run = gpu_dialect(task), gpu_pipeline(task, spec, pipeline)
    blocks: dict[int, gpu.Shape] = {}
    try:
        program, picks = gpu.speculate(run, dialect, gpu.native_arch(dialect))
        blocks = {ordinal: pick.shape for ordinal, pick in picks.items()}
        print(f"alloy: {spec.short_name}: threadblocks {blocks}", file=sys.stderr, flush=True)
        chosen, build_name = speculated_library(task, spec, program, folder)
        if judge_client().score(chosen, task.kernel).correct:
            note = f"speculated, device build {build_name}"
            record_episode(keep, "gpu-speculative", task, started, scopes=gpu_scopes(blocks, True, note))
            return chosen
        reason = "graded wrong"
    except (OSError, RuntimeError, ValueError) as exc:  # no compiler report, or a judge that does not answer
        print(f"alloy: {spec.short_name}: speculated threadblocks dropped: {exc}", file=sys.stderr, flush=True)
        reason = f"dropped: {exc}"
    record_episode(keep, "gpu-speculative", task, started, scopes=gpu_scopes(blocks, False, reason))
    return device_submission(task, spec, run({}), form_dialect(task), folder)
