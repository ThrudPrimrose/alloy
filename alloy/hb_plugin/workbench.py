# Copyright 2026 ETH Zurich and the Alloy authors.
"""What the ``alloy_profile`` and ``alloy_speculative`` agent tools get back: Alloy on the episode's kernel after the
bench's canonical (CPF) pipeline, as plain C/C++ an agent can read, edit and rebuild without DaCe.

Under ``folder``: ``report.md`` (every scope's candidates, the top ones ranked by time or prediction), and ``best/``
with one translation unit per scope (``scopes/<symbol>.<ext>``, the chosen candidate's source), the program entry in
the bench's C ABI (``program.c``, CPF calling the scopes) and a ``Makefile`` that compiles each scope with its own
compiler and flags and links ``lib<program>.so``. The library is built here, so it can be submitted as it is."""

import pathlib
import shlex
import subprocess

import pydantic
from hpcagent_bench.cpf.bridge import render_canonical
from hpcagent_bench.cpf.cache import DEFAULT_HINTS, Target
from hpcagent_bench.precision import Precision
from hpcagent_bench.spec import BenchSpec

from alloy import api, configuration_matrix
from alloy.backend.build import Build
from alloy.evaluate.link import Best, BestScope, Linker
from alloy.hb_plugin.adapter import manifest_of, nothing_to_generate, pipeline_sdfg
from alloy.report import Mode

__all__ = ["CodegenAnswer", "CodegenRequest", "codegen"]

#: The bench pipeline whose output Alloy renders: the canonical parallel form.
PIPELINE = "canon_cpu"
#: The most of ``report.md`` an answer carries; the file holds all of it.
REPORT_CHARS = 20_000


class CodegenRequest(pydantic.BaseModel):
    """One tool call: the kernel, the mode, the graded precision and the folder the answer is written into."""

    model_config = pydantic.ConfigDict(extra="forbid", frozen=True)

    kernel: str
    mode: Mode
    precision: Precision
    folder: str


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


def codegen(request: CodegenRequest) -> CodegenAnswer:
    """Alloy on ``request.kernel`` in ``request.mode``: profile verifies and times every candidate here, speculative
    links the predicted pick of each scope (verified, never timed)."""
    spec = BenchSpec.load(request.kernel)
    matrix = configuration_matrix.load()
    sdfg = pipeline_sdfg(spec, PIPELINE, request.precision, Target.CPU)
    if nothing_to_generate(sdfg, matrix):
        raise api.NothingToGenerate(
            f"{spec.short_name}: no loop nest outlines into a scope, so Alloy has nothing to generate"
        )
    manifest = manifest_of(spec, request.precision)
    out = pathlib.Path(request.folder)
    result = api.generate(sdfg, out, manifest=manifest, matrix=matrix, mode=request.mode)
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
