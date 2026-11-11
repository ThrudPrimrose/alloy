# Copyright 2026 ETH Zurich and the Alloy authors.
"""Alloy's one entry point: an SDFG in, every scope's candidates built, verified, timed and reported."""

import importlib.util
import numbers
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

#: Fuzz draws candidates are verified on.
ITERATIONS = 2


class NothingToGenerate(ValueError):
    """The program has no scope Alloy can take."""


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


def test_cases(program: Program, manifest: Manifest | None) -> verify.Cases | None:
    """The draws candidates are verified on: the manifest's, or without one, draws derived from the SDFG when any
    value is a valid input (:func:`inputs.domain_gap`) and the bench's tolerance band is installed; else ``None``."""
    if manifest is not None:
        draws = [inputs.draw(manifest, i) for i in range(ITERATIONS)]
        return verify.Cases(draws, manifest.outputs, inputs.grading(manifest))
    original = program.original
    if inputs.domain_gap(original) or importlib.util.find_spec("hpcagent_bench") is None:
        return None
    return verify.Cases([inputs.derived_draw(original, i) for i in range(ITERATIONS)], inputs.derived_outputs(original))


def known_sizes(program: Program, running: dict[str, int] | None) -> dict[str, int] | None:
    """The sizes the program will run at: what the caller declares over the constants of its SDFG; ``None`` while a
    free symbol stays open (a manifest's presets say what may run, not what will)."""
    constants = {k: int(v) for k, v in program.original.constants.items() if isinstance(v, numbers.Integral)}
    sizes = {**constants, **(running or {})}
    return sizes if program.original.free_symbols <= sizes.keys() else None


def roofline_sizes(program: Program, manifest: Manifest | None, matrix: Matrix) -> dict[str, int] | None:
    """The sizes speculative mode weighs loops and memory at while the running ones are unknown: the manifest's largest
    preset, or without one every size symbol grown until the program fills the final timing stage's share of the
    largest cache."""
    if manifest is not None:
        presets = inputs.presets(manifest)  # the largest: at the smallest every array sits in cache
        return max(presets, key=lambda sizes: timing.footprint(program.original, sizes), default=None)
    base = dict.fromkeys(program.original.free_symbols, inputs.DERIVED_SIZES[0])
    if not base:
        return {}
    target = matrix.timing.final_cache_factor * machine.largest_cache_bytes()
    return timing.sized(program.original, program.original, {str(k): v for k, v in base.items()}, target, target)


def predicted_winners(
    reports: list[ScopeReport],
    verification: Verification | None,
    predicted: Predictions,
    matrix: Matrix,
    *,
    finite_inputs: bool,
) -> dict[str, Build]:
    """Each scope's predicted pick; with nothing to check a variant, its default build."""
    if verification is None:
        return {rep.scope.symbol: rep.builds[0] for rep in reports}
    verdicts = verification.verdicts
    return {
        rep.scope.symbol: predict.choose(
            rep, verdicts.get(rep.scope.symbol, {}), predicted, matrix, finite_inputs=finite_inputs
        )
        for rep in reports
    }


def timed_winners(reports: list[ScopeReport], timings: Timings) -> dict[str, Build]:
    """Each scope's fastest; every default build when the fastest together leave the band, as scopes each in it can."""
    if not timings.program.arms["alloy_full"].verdict.ok:
        return {rep.scope.symbol: rep.builds[0] for rep in reports}
    return {rep.scope.symbol: winning_build(rep, timings.scopes[rep.scope.symbol].winner) for rep in reports}


def generate(
    sdfg: dace.SDFG,
    out: pathlib.Path,
    *,
    manifest: Manifest | None = None,
    matrix: Matrix | None = None,
    finite_inputs: bool = False,
    time_locally: bool = True,
    mode: Mode = Mode.PROFILE,
    running: dict[str, int] | None = None,
) -> Result:
    """Outline ``sdfg`` into scopes and build every candidate under ``out``, then verify them on the manifest's
    fuzz draws (without a manifest, on draws derived from ``sdfg`` when any value is a valid input:
    :func:`test_cases`). In profile mode (a manifest is required), when ``time_locally``, time the survivors and link
    the fastest; a caller that times elsewhere (a benchmark's judge) passes ``time_locally=False``. In speculative mode
    link the ones :func:`predict.choose` picks, untimed, or each scope's default build when nothing was verified.
    ``finite_inputs`` declares no input is NaN or Inf, which opens the FP levels that need it. ``running`` declares
    the sizes the program will be called at: speculative mode then ranks every build, serial ones too, at those sizes."""
    matrix = matrix or configuration_matrix.load()
    program = scopes.outline(sdfg, matrix.libm_calls)
    if not program.scopes:
        raise NothingToGenerate(f"{sdfg.name}: no top-level loop nest to outline, so Alloy has nothing to generate")
    if manifest is None and mode == Mode.PROFILE:
        raise ValueError(f"{sdfg.name}: profile mode times at declared sizes, so it needs a manifest")
    out.mkdir(parents=True, exist_ok=True)
    reports = sweep.run(program, matrix, out, finite_inputs=finite_inputs)
    timings, best, commands, predicted, picked = None, None, None, None, None
    cases = test_cases(program, manifest)
    verification = verify.verify(program, matrix, reports, cases, out) if cases is not None else None
    linker = Linker(program, matrix, out)
    winners: dict[str, Build] = {}
    if mode == Mode.SPECULATIVE:
        known = known_sizes(program, running)
        sizes = known if known is not None else roofline_sizes(program, manifest, matrix)
        predicted = predict.predictions(reports, sizes, known is not None)
        winners = predicted_winners(reports, verification, predicted, matrix, finite_inputs=finite_inputs)
    elif verification is not None and manifest is not None and time_locally:
        timings = timing.time_program(linker, reports, verification, manifest)
        winners = timed_winners(reports, timings)
    if winners:
        picked = {symbol: b.name for symbol, b in winners.items()}
        best = linker.write_best(winners)
        commands = linker.commands(best)
    verdicts = verification.verdicts if verification else {}
    host_isas = matrix.host_isas(machine.cpu_flags())
    advice = guidance.guidance(reports, verdicts, winners, host_isas, finite_inputs=finite_inputs)
    report.write(program, reports, matrix, out, verification, timings, commands, predicted, picked, advice)
    return Result(program, reports, verification, timings, best, out / "report.md", predicted, winners, advice)
