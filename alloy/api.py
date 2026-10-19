# Copyright 2026 ETH Zurich and the Alloy authors.
"""Alloy's one entry point: an SDFG in, every region's candidates built, verified, timed and reported."""

import pathlib
from dataclasses import dataclass

import dace

from alloy import configuration_matrix, report
from alloy.backend import sweep
from alloy.backend.sweep import RegionReport
from alloy.configuration_matrix import Matrix
from alloy.evaluate import timing, verify
from alloy.evaluate.link import Best, Linker
from alloy.evaluate.timing import Timings, winning_build
from alloy.evaluate.verify import Verification
from alloy.frontend import inputs, regions
from alloy.frontend.inputs import Manifest
from alloy.frontend.regions import Program


@dataclass(slots=True, frozen=True)
class Result:
    """The outlined program, every region's builds, their verdicts and timings, the ``best/`` link plan (these three
    ``None`` without a manifest), and the report."""

    program: Program
    regions: list[RegionReport]
    verification: Verification | None
    timings: Timings | None
    best: Best | None
    report: pathlib.Path


def generate(
    sdfg: dace.SDFG,
    out: pathlib.Path,
    *,
    manifest: Manifest | None = None,
    matrix: Matrix | None = None,
    finite_inputs: bool = False,
    iterations: int = 2,
) -> Result:
    """Outline ``sdfg`` into regions and build every candidate under ``out``. With a ``manifest``, verify each
    candidate on ``iterations`` fuzz draws and time the survivors; without one, candidates are only built.
    ``finite_inputs`` declares no input is NaN or Inf, which opens the FP levels that need it."""
    matrix = matrix or configuration_matrix.load()
    program = regions.outline(sdfg, matrix.libm_calls)
    if not program.regions:
        raise ValueError(f"{sdfg.name}: no top-level loop nest to outline, so Alloy has nothing to generate")
    out.mkdir(parents=True, exist_ok=True)
    max_elements = None if manifest is None else inputs.largest_array(manifest, program.original)
    reports = sweep.run(program, matrix, out, finite_inputs=finite_inputs, max_elements=max_elements)
    verification, timings, best = None, None, None
    if manifest is not None:
        cases = verify.Cases([inputs.draw(manifest, i) for i in range(iterations)], manifest.outputs)
        verification = verify.verify(program, matrix, reports, cases, out)
        linker = Linker(program, matrix, out)
        timings = timing.time_program(linker, reports, verification, manifest)
        winners = {rep.region.symbol: winning_build(rep, timings.regions[rep.region.symbol].winner) for rep in reports}
        best = linker.write_best(winners)
    report.write(reports, matrix, out, verification, timings, best)
    return Result(program, reports, verification, timings, best, out / "report.md")
