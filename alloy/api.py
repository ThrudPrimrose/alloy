# Copyright 2026 ETH Zurich and the Alloy authors.
"""Alloy's one entry point: an SDFG in, every scope's candidates built, verified, timed and reported."""

import pathlib
from dataclasses import dataclass

import dace

from alloy import configuration_matrix, report
from alloy.backend import sweep
from alloy.backend.build import Build
from alloy.backend.sweep import ScopeReport
from alloy.configuration_matrix import Matrix
from alloy.evaluate import timing, verify
from alloy.evaluate.link import Best, Linker
from alloy.evaluate.timing import Timings, winning_build
from alloy.evaluate.verify import Verification
from alloy.frontend import inputs, scopes
from alloy.frontend.inputs import Manifest
from alloy.frontend.scopes import Program
from alloy.heuristics import predict
from alloy.heuristics.predict import Predictions
from alloy.report import Mode


@dataclass(slots=True, frozen=True)
class Result:
    """The outlined program, every scope's builds, their verdicts and timings, the ``best/`` link plan (these three
    ``None`` without a manifest), the speculative predictions (``None`` in profile mode), and the report."""

    program: Program
    scopes: list[ScopeReport]
    verification: Verification | None
    timings: Timings | None
    best: Best | None
    report: pathlib.Path
    predictions: Predictions | None = None


def generate(
    sdfg: dace.SDFG,
    out: pathlib.Path,
    *,
    manifest: Manifest | None = None,
    matrix: Matrix | None = None,
    finite_inputs: bool = False,
    iterations: int = 2,
    time_locally: bool = True,
    mode: Mode = Mode.PROFILE,
) -> Result:
    """Outline ``sdfg`` into scopes and build every candidate under ``out``. With a ``manifest``, verify each
    candidate on ``iterations`` fuzz draws; then in profile mode, when ``time_locally``, time the survivors and link
    the fastest, in speculative mode link the ones :func:`predict.choose` picks, untimed. Without a manifest,
    candidates are only built (and predicted). A caller that times elsewhere (a benchmark's judge) passes
    ``time_locally=False``. ``finite_inputs`` declares no input is NaN or Inf, which opens the FP levels that need
    it."""
    matrix = matrix or configuration_matrix.load()
    program = scopes.outline(sdfg, matrix.libm_calls)
    if not program.scopes:
        raise ValueError(f"{sdfg.name}: no top-level loop nest to outline, so Alloy has nothing to generate")
    out.mkdir(parents=True, exist_ok=True)
    max_elements = None if manifest is None else inputs.largest_array(manifest, program.original)
    reports = sweep.run(program, matrix, out, finite_inputs=finite_inputs, max_elements=max_elements)
    verification, timings, best, commands, predicted, picked = None, None, None, None, None, None
    winners: dict[str, Build] = {}
    if manifest is not None:
        cases = verify.Cases([inputs.draw(manifest, i) for i in range(iterations)], manifest.outputs)
        verification = verify.verify(program, matrix, reports, cases, out)
    if mode == Mode.SPECULATIVE:
        sizes = inputs.presets(manifest)[0] if manifest is not None and inputs.presets(manifest) else None
        predicted = predict.predictions(reports, sizes)
        verdicts = verification.verdicts if verification else {}
        winners = {
            rep.scope.symbol: predict.choose(
                rep, verdicts.get(rep.scope.symbol, {}), predicted, matrix, finite_inputs=finite_inputs
            )
            for rep in reports
        }
        picked = {symbol: b.name for symbol, b in winners.items()}
    elif verification is not None and manifest is not None and time_locally:
        timings = timing.time_program(Linker(program, matrix, out), reports, verification, manifest)
        winners = {rep.scope.symbol: winning_build(rep, timings.scopes[rep.scope.symbol].winner) for rep in reports}
    if verification is not None and winners:
        linker = Linker(program, matrix, out)
        best = linker.write_best(winners)
        commands = linker.commands(best)
    report.write(program, reports, matrix, out, verification, timings, commands, predicted=predicted, picked=picked)
    return Result(program, reports, verification, timings, best, out / "report.md", predicted)
