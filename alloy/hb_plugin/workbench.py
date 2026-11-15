# Copyright 2026 ETH Zurich and the Alloy authors.
"""What the ``alloy_profile`` and ``alloy_speculative`` agent tools get back: Alloy on the episode's kernel after the
bench's canonical (CPF) pipeline, as plain C/C++ an agent can read, edit and rebuild without DaCe.

Under ``folder``: ``report.md``, and ``best/`` with one translation unit per scope, the program entry in the bench's C
ABI (``program.c``), a ``Makefile`` compiling each scope with its own compiler and flags, and the library it built.
On a GPU task (``language`` hip) ``best/`` holds the bench's HIP form with each device map at the threadblock its
compiler report ranks first, and the library the bench's own sandbox builds from it (:func:`gpu_codegen`)."""

import pathlib
import shlex
import shutil
import subprocess

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
from alloy.hb_plugin.adapter import device_submission, gpu_pipeline, manifest_of, nothing_to_generate, pipeline_sdfg
from alloy.report import Mode

__all__ = ["CodegenAnswer", "CodegenRequest", "codegen"]

#: The bench pipeline whose output Alloy renders: the canonical parallel form, on the CPU or the GPU.
PIPELINE = "canon_cpu"
GPU_PIPELINE = "canon_gpu"
#: Task languages whose submission is the bench's GPU form.
GPU_LANGUAGES = frozenset({"hip"})
#: The most of ``report.md`` an answer carries; the file holds all of it.
REPORT_CHARS = 20_000


class CodegenRequest(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid", frozen=True)

    kernel: str
    mode: Mode
    precision: Precision
    folder: str
    #: The sizes the judge grades the kernel at.
    running: dict[str, int]
    #: The episode's task language: ``hip`` takes the GPU path.
    language: str = "c"


class CodegenAnswer(pydantic.BaseModel):
    """The built library with the scratch it requests, where its sources are, how to rebuild it, and the report."""

    model_config = pydantic.ConfigDict(extra="forbid", frozen=True)

    mode: Mode
    library: str
    workspace_bytes: str
    folder: str
    make: str
    scopes: tuple[BestScope, ...]
    report: str
    #: Scope symbol -> why Alloy left it short and how to finish it by hand, with the target's intrinsics.
    advice: dict[str, str] = {}


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
    return form.workspace_bytes


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
    """The bench's HIP form of ``request.kernel`` with each device map at its ranked threadblock
    (:func:`alloy.gpu.speculate`, compile-only), built into a library by the bench's own sandbox, so it is the
    ``.so`` the judge would build from these sources."""
    spec = BenchSpec.load(request.kernel)
    task = Task(request.kernel, SourceMode.ANY, Language.HIP, request.precision)
    dialect = gpu.native_dialect()
    arch = gpu.native_arch(dialect)
    run = gpu_pipeline(task, spec, GPU_PIPELINE)
    program, picks = gpu.speculate(run, dialect, arch)
    if not picks:
        raise api.NothingToGenerate(f"{spec.short_name}: no device map to give a threadblock")
    submission = device_submission(task, spec, program)
    best = pathlib.Path(request.folder) / "best"
    best.mkdir(parents=True, exist_ok=True)
    (best / "program.hip").write_text(submission.source or "")
    (best / "device.hip").write_text(submission.device_source or "")
    with Sandbox(binding_from_spec(spec), source_mode=SourceMode.ANY) as sandbox:
        built = sandbox.build(submission)
        if not built.ok or built.lib is None:
            raise RuntimeError(f"the bench could not build the HIP form: {built.log[-1500:]}")
        library = best / built.lib.name
        shutil.copy(built.lib, library)
    report = gpu_report(picks, dialect, arch, request.mode)
    (pathlib.Path(request.folder) / "report.md").write_text(report)
    rebuild = "\n".join(built.commands) or "submit program.hip and device.hip as source and device_source"
    return CodegenAnswer(
        mode=request.mode,
        library=str(library),
        workspace_bytes=submission.workspace_bytes or "0",
        folder=str(best),
        make=rebuild,
        scopes=(),
        report=report,
    )


def codegen(request: CodegenRequest) -> CodegenAnswer:
    """Alloy on ``request.kernel`` in ``request.mode``: profile verifies and times every candidate here, speculative
    links the predicted pick of each scope (verified, never timed). A GPU task takes :func:`gpu_codegen`."""
    if request.language in GPU_LANGUAGES:
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
    result = api.generate(sdfg, out, manifest=manifest, matrix=matrix, mode=request.mode, running=request.running)
    if result.best is None or not result.winners:
        hints = "\n\n".join((result.advice or {}).values())
        raise api.NothingToGenerate(
            f"{spec.short_name}: Alloy picked no build for any scope (nothing was verified)\n\n{hints}"
        )
    linker, best = Linker(result.program, matrix, out), out / "best"
    workspace = bench_entry(linker, result.best, result.winners, spec, request.precision)
    made = subprocess.run(["make", "-C", str(best), "-B"], check=False, capture_output=True, text=True)
    if made.returncode != 0:
        raise RuntimeError(f"make in {best} failed:\n{made.stderr[-2000:]}")
    commands = linker.commands(result.best)
    report = result.report.read_text()
    return CodegenAnswer(
        mode=request.mode,
        library=str(best / commands.library),
        workspace_bytes=workspace,
        folder=str(best),
        make=shlex.join(["make", "-C", str(best)]),
        scopes=result.best.scopes,
        report=report[:REPORT_CHARS]
        + (f"\n[cut: the rest is in {result.report}]" if len(report) > REPORT_CHARS else ""),
        advice=result.advice or {},
    )
