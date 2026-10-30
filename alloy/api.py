# Copyright 2026 ETH Zurich and the Alloy authors.
"""Alloy's one entry point: an SDFG in, every scope's candidates built, verified, timed and reported."""

import importlib.util
import pathlib
from dataclasses import dataclass

import dace

from alloy import configuration_matrix, guidance, machine, report
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
    #: The build linked for each scope (empty when nothing was linked).
    winners: dict[str, Build] | None = None
    #: Do-it-yourself text for the scopes Alloy left short (:func:`guidance.guidance`).
    advice: dict[str, str] | None = None


def test_cases(program: Program, manifest: Manifest | None, iterations: int) -> verify.Cases | None:
    """The draws candidates are verified on: the manifest's, or without one, draws derived from the SDFG when any
    value is a valid input (:func:`inputs.domain_gap`) and the bench's tolerance band is installed; else ``None``."""
    if manifest is not None:
        return verify.Cases([inputs.draw(manifest, i) for i in range(iterations)], manifest.outputs)
    original = program.original
    if inputs.domain_gap(original) or importlib.util.find_spec("hpcagent_bench") is None:
        return None
    return verify.Cases([inputs.derived_draw(original, i) for i in range(iterations)], inputs.derived_outputs(original))


def roofline_sizes(program: Program, manifest: Manifest | None, matrix: Matrix) -> dict[str, int] | None:
    """The sizes speculative mode weighs loops and memory at: the manifest's first preset, or without one every size
    symbol grown until the program fills the final timing stage's share of the largest cache."""
    if manifest is not None:
        return next(iter(inputs.presets(manifest)), None)
    base = dict.fromkeys(program.original.free_symbols, inputs.DERIVED_SIZES[0])
    if not base:
        return None
    target = matrix.timing.final_cache_factor * machine.largest_cache_bytes()
    return timing.sized(program.original, program.original, {str(k): v for k, v in base.items()}, target, target)


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
    """Outline ``sdfg`` into scopes and build every candidate under ``out``, then verify them on the manifest's
    ``iterations`` fuzz draws (without a manifest, on draws derived from ``sdfg`` when any value is a valid input:
    :func:`test_cases`). In profile mode (a manifest is required), when ``time_locally``, time the survivors and link
    the fastest; a caller that times elsewhere (a benchmark's judge) passes ``time_locally=False``. In speculative mode
    link the ones :func:`predict.choose` picks, untimed, or each scope's default build when nothing was verified.
    ``finite_inputs`` declares no input is NaN or Inf, which opens the FP levels that need it."""
    matrix = matrix or configuration_matrix.load()
    program = scopes.outline(sdfg, matrix.libm_calls)
    if not program.scopes:
        raise ValueError(f"{sdfg.name}: no top-level loop nest to outline, so Alloy has nothing to generate")
    if manifest is None and mode == Mode.PROFILE:
        raise ValueError(f"{sdfg.name}: profile mode times at declared sizes, so it needs a manifest")
    out.mkdir(parents=True, exist_ok=True)
    max_elements = None if manifest is None else inputs.largest_array(manifest, program.original)
    reports = sweep.run(program, matrix, out, finite_inputs=finite_inputs, max_elements=max_elements)
    timings, best, commands, predicted, picked = None, None, None, None, None
    cases = test_cases(program, manifest, iterations)
    verification = verify.verify(program, matrix, reports, cases, out) if cases is not None else None
    winners: dict[str, Build] = {}
    if mode == Mode.SPECULATIVE:
        predicted = predict.predictions(reports, roofline_sizes(program, manifest, matrix))
        verdicts = verification.verdicts if verification else {}
        winners = {
            rep.scope.symbol: predict.choose(
                rep, verdicts.get(rep.scope.symbol, {}), predicted, matrix, finite_inputs=finite_inputs
            )
            if verification is not None
            else rep.builds[0]  # nothing checked a variant: the default build ships
            for rep in reports
        }
        picked = {symbol: b.name for symbol, b in winners.items()}
    elif verification is not None and manifest is not None and time_locally:
        timings = timing.time_program(Linker(program, matrix, out), reports, verification, manifest)
        winners = {rep.scope.symbol: winning_build(rep, timings.scopes[rep.scope.symbol].winner) for rep in reports}
    if winners:
        linker = Linker(program, matrix, out)
        best = linker.write_best(winners)
        commands = linker.commands(best)
    verdicts = verification.verdicts if verification else {}
    advice = guidance.guidance(reports, verdicts, winners, matrix.host_isas(machine.cpu_flags()))
    report.write(
        program,
        reports,
        matrix,
        out,
        verification,
        timings,
        commands,
        predicted=predicted,
        picked=picked,
        advice=advice,
    )
    return Result(program, reports, verification, timings, best, out / "report.md", predicted, winners, advice)
