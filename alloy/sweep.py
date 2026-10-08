# Copyright 2026 ETH Zurich and the Alloy authors.
"""Build every candidate of every region of an outlined program."""

import pathlib
from dataclasses import dataclass

from alloy.build import Build, build
from alloy.candidates import one_factor_at_a_time
from alloy.configuration_matrix import Matrix
from alloy.regions import Program, Region


@dataclass(slots=True, frozen=True)
class RegionReport:
    region: Region
    builds: tuple[Build, ...]


def run(program: Program, matrix: Matrix, out: pathlib.Path, *, finite_inputs: bool = False) -> list[RegionReport]:
    """Build every candidate of every region under ``out/regions/<symbol>``."""
    reports = []
    for region in program.regions:
        seen: dict[str, str] = {}
        folder = out / "regions" / region.symbol
        candidates = one_factor_at_a_time(matrix, region, finite_inputs=finite_inputs)
        builds = tuple(build(region, cand, matrix, folder, seen) for cand in candidates)
        reports.append(RegionReport(region, builds))
    return reports
