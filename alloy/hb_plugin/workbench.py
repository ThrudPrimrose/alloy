# Copyright 2026 ETH Zurich and the Alloy authors.
"""What the ``alloy_profile`` and ``alloy_speculative`` agent tools get back: Alloy on the episode's kernel after the
bench's canonical (CPF) pipeline, as plain C/C++ an agent can read, edit and rebuild without DaCe.

Under ``folder``: ``report.md``, and ``best/`` with one translation unit per scope, the program entry in the bench's C
ABI (``program.c``), a ``Makefile`` compiling each scope with its own compiler and flags, and ``advice/<symbol>.md``
for each scope Alloy left short. The answer names these files and does not build the library in the agent's folder:
the agent runs ``make`` and submits, or edits first (owner, 2026-11-17). The judge builds a scratch copy to check that
the folder builds and records that library's hash. On a GPU task (``language`` hip) ``best/`` holds the bench's HIP
form with each device map at the threadblock its compiler report ranks first (:func:`gpu_codegen`)."""

import pathlib
import shlex
import shutil
import subprocess
import tempfile

import pydantic
from hpcagent_bench.categories import Language, SourceMode
from hpcagent_bench.cpf.bridge import render_canonical
from hpcagent_bench.cpf.cache import DEFAULT_HINTS, Target
from hpcagent_bench.harness.sandbox import Sandbox
from hpcagent_bench.harness.task import Task
from hpcagent_bench.precision import Precision
from hpcagent_bench.spec import BenchSpec
from hpcagent_bench.support.bindings.contract import binding_from_spec

from alloy import api, configuration_matrix, gpu
from alloy.backend.build import Build
from alloy.evaluate.link import Best, BestScope, Linker
from alloy.hb_plugin.adapter import (
    built_library,
    gpu_form,
    gpu_pipeline,
    manifest_of,
    nothing_to_generate,
    pipeline_sdfg,
    source_pair,
)
from alloy.hb_plugin.episode import file_hash
from alloy.report import Mode

__all__ = ["CodegenAnswer", "CodegenRequest", "codegen"]

#: The bench pipeline whose output Alloy renders: the canonical parallel form, on the CPU or the GPU.
PIPELINE = "canon_cpu"
GPU_PIPELINE = "canon_gpu"
#: Task languages whose submission is the bench's GPU form.
GPU_LANGUAGES = frozenset({"hip", "cuda"})
#: The file suffix of a dialect's two GPU units.
DEVICE_SUFFIX = {"hip": "hip", "cuda": "cu"}


class CodegenRequest(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid", frozen=True)

    kernel: str
    mode: Mode
    precision: Precision
    folder: str
    #: The sizes the judge grades the kernel at.
    running: dict[str, int]
    #: The episode's task language: ``hip`` and ``cuda`` take the GPU path.
    language: str = "c"
    #: Scope symbol -> an edited translation unit that replaces its rendering (``alloy_sweep``).
    sources: dict[str, str] = {}


class CodegenAnswer(pydantic.BaseModel):
    """Where the sources are, how to build and submit them, each scope's build, and the paths of the report and the
    advice; never the built library, which the agent makes itself."""

    model_config = pydantic.ConfigDict(extra="forbid", frozen=True)

    mode: Mode
    folder: str
    #: How to build and submit: the command, and on a GPU task which files to submit as which field.
    make: str
    #: The file ``make`` writes in ``folder`` (empty on a GPU source pair, which the judge builds).
    builds: str
    workspace_bytes: str
    scopes: tuple[BestScope, ...]
    #: The path of ``report.md``: every scope's candidates, ranked.
    report: str
    #: Scope symbol -> the path of the note on why Alloy left it short and the target's intrinsics it needs.
    advice: dict[str, str] = {}
    #: SHA-256 of the library the judge built from a scratch copy of ``folder`` (empty when nothing was built).
    checked_sha256: str = ""


def checked_build(best: pathlib.Path, library: str) -> str:
    """Build a scratch copy of ``best`` with its Makefile and return the library's SHA-256, so the folder handed to
    the agent is known to build and stays unbuilt."""
    with tempfile.TemporaryDirectory(prefix="alloy-check") as scratch:
        copy = pathlib.Path(scratch) / "best"
        shutil.copytree(best, copy)
        made = subprocess.run(["make", "-C", str(copy), "-B"], check=False, capture_output=True, text=True)
        if made.returncode != 0:
            raise RuntimeError(f"make in a copy of {best} failed:\n{made.stderr[-2000:]}")
        return file_hash(copy / library)


def advice_files(best: pathlib.Path, advice: dict[str, str]) -> dict[str, str]:
    """Write each scope's advice to ``best/advice/<symbol>.md`` and return the paths."""
    if not advice:
        return {}
    folder = best / "advice"
    folder.mkdir(exist_ok=True)
    paths: dict[str, str] = {}
    for symbol, text in advice.items():
        path = folder / f"{symbol}.md"
        path.write_text(text)
        paths[symbol] = str(path)
    return paths


def bench_entry(linker: Linker, plan: Best, winners: dict[str, Build], spec: BenchSpec, precision: Precision) -> str:
    """Write ``best/program.c`` in the bench's C ABI calling every scope's ``lib<symbol>.a``, and the Makefile that
    builds it; returns the scratch bytes the entry requests."""
    best = linker.out / "best"
    archives = {scope.symbol: best / f"lib{scope.symbol}.a" for scope in plan.scopes}
    sdfg = linker.library_sdfg(archives, frozenset(b.candidate for b in winners.values()))
    form = render_canonical(spec, spec.short_name, sdfg, "c", precision.value, Target.CPU, DEFAULT_HINTS)
    (best / "program.c").write_text(form.code)
    link = tuple(token.removeprefix(f"{best}/") for token in form.link)  # make runs in best/
    (best / "Makefile").write_text(linker.makefile(Best(plan.scopes, plan.arguments, link)))
    workspace: str = form.workspace_bytes
    return workspace


def gpu_report(picks: dict[int, gpu.Pick], dialect: str, arch: str, mode: Mode) -> str:
    """Each device map's picked threadblock and the shapes its compiler report ranked, best first."""
    lines = [
        f"# Alloy on the GPU ({dialect}, {arch})",
        "",
        "Each device map takes the threadblock its compiler report ranks first: no spills, then occupancy (counted up "
        "to 0.5), then an innermost dimension of at least a warp, then fewer registers. Nothing was timed"
        + (
            ": profile mode times shapes only in the tuner, so this call answers with the ranked picks."
            if mode is Mode.PROFILE
            else "."
        ),
        "",
        "| Map | Picked | Registers | Spill bytes | Occupancy | Ranked (shape, registers, occupancy) |",
        "|---|---|---|---|---|---|",
    ]
    for ordinal, pick in sorted(picks.items()):
        ranked = "; ".join(
            f"{'x'.join(map(str, shape))} {usage.registers} {occ:.2f}" for shape, usage, occ in pick.ranked[:4]
        )
        shape = "x".join(map(str, pick.shape))
        lines.append(
            f"| {ordinal} | {shape} | {pick.usage.registers} | {pick.usage.spill_bytes} | {pick.occupancy:.2f} | {ranked} |"
        )
    return "\n".join(lines) + "\n"


def gpu_codegen(request: CodegenRequest) -> CodegenAnswer:
    """The bench's GPU form of ``request.kernel`` in the task's dialect with each device map at its ranked
    threadblock (:func:`alloy.gpu.speculate`, compile-only), built into a library by the bench's own sandbox, so it
    is the ``.so`` the judge would build from these sources."""
    spec = BenchSpec.load(request.kernel)
    # the form in the task's language; the register report from the compiler of the device that is here
    task = Task(request.kernel, SourceMode.ANY, Language.parse(request.language), request.precision)
    dialect = gpu.native_dialect()
    arch = gpu.native_arch(dialect)
    run = gpu_pipeline(task, spec, GPU_PIPELINE)
    program, picks = gpu.speculate(run, dialect, arch)
    if not picks:
        raise api.NothingToGenerate(f"{spec.short_name}: no device map to give a threadblock")
    form = gpu_form(task, spec, program, request.language)
    submission = source_pair(request.language, form)
    best = pathlib.Path(request.folder) / "best"
    best.mkdir(parents=True, exist_ok=True)
    suffix = DEVICE_SUFFIX[request.language]
    (best / f"program.{suffix}").write_text(submission.source or "")
    (best / f"device.{suffix}").write_text(submission.device_source or "")
    if form.libraries:  # the bench's sandbox links a pair's libraries only on a request the setup refuses
        library = pathlib.Path(built_library(request.language, form, spec, best).library or "")
        builds, checked = library.name, file_hash(library)
    else:
        with Sandbox(binding_from_spec(spec), source_mode=SourceMode.ANY) as sandbox:
            built = sandbox.build(submission)
            if not built.ok or built.lib is None:
                raise RuntimeError(f"the bench could not build the {request.language} form: {built.log[-1500:]}")
            builds, checked = "", file_hash(built.lib)  # the judge builds the pair: nothing to make here
    report = pathlib.Path(request.folder) / "report.md"
    report.write_text(gpu_report(picks, dialect, arch, request.mode))
    # the sandbox's own commands name its temporary folder, gone by now: the judge rebuilds from the pair
    rebuild = (
        f"submit the library: the form calls {', '.join(form.libraries)}, which the judge links into a source pair "
        f"only on a library request; after editing program.{suffix} or device.{suffix}, rebuild with the "
        f"{', '.join(form.libraries)} link flags (-l{' -l'.join(form.libraries)})"
        if form.libraries
        else f"submit program.{suffix} as source and device.{suffix} as device_source; the judge builds them"
    )
    return CodegenAnswer(
        mode=request.mode,
        folder=str(best),
        make=rebuild,
        builds=builds,
        workspace_bytes=submission.workspace_bytes or "0",
        scopes=(),
        report=str(report),
        checked_sha256=checked,
    )


def codegen(request: CodegenRequest) -> CodegenAnswer:
    """Alloy on ``request.kernel`` in ``request.mode``: profile verifies and times every candidate here, speculative
    links the predicted pick of each scope (verified, never timed). A GPU task takes :func:`gpu_codegen`."""
    if request.language in GPU_LANGUAGES:
        if request.sources or request.mode is Mode.REFERENCE:
            raise api.NothingToGenerate("alloy_sweep and alloy_reference take CPU tasks; this task is GPU code")
        return gpu_codegen(request)
    spec = BenchSpec.load(request.kernel)
    matrix = configuration_matrix.load()
    sdfg = pipeline_sdfg(spec, PIPELINE, request.precision, Target.CPU)
    if nothing_to_generate(sdfg, matrix):
        raise api.NothingToGenerate(
            f"{spec.short_name}: no loop nest outlines into a scope, so Alloy has nothing to generate"
        )
    manifest = manifest_of(spec, request.precision)
    out = pathlib.Path(request.folder)
    sources = {symbol: pathlib.Path(path) for symbol, path in request.sources.items()}
    result = api.generate(
        sdfg, out, manifest=manifest, matrix=matrix, mode=request.mode, running=request.running, sources=sources
    )
    if result.best is None or not result.winners:
        hints = "\n\n".join((result.advice or {}).values())
        raise api.NothingToGenerate(
            f"{spec.short_name}: Alloy picked no build for any scope (nothing was verified)\n\n{hints}"
        )
    linker, best = Linker(result.program, matrix, out), out / "best"
    workspace = bench_entry(linker, result.best, result.winners, spec, request.precision)
    commands = linker.commands(result.best)
    checked = checked_build(best, commands.library)
    make = shlex.join(["make", "-C", str(best)])
    return CodegenAnswer(
        mode=request.mode,
        folder=str(best),
        make=f"{make} builds {best / commands.library}; submit it as the library with workspace_bytes={workspace}",
        builds=commands.library,
        workspace_bytes=workspace,
        scopes=result.best.scopes,
        report=str(result.report),
        advice=advice_files(best, result.advice or {}),
        checked_sha256=checked,
    )
