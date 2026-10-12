# Copyright 2026 ETH Zurich and the Alloy authors.
"""Build every candidate of every region of an outlined program."""

import pathlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from alloy import machine
from alloy.backend.build import Build, RenderKey, compile_source, deduplicated, write_source
from alloy.backend.candidates import one_factor_at_a_time
from alloy.configuration_matrix import Matrix
from alloy.frontend.regions import Program, Region


@dataclass(slots=True, frozen=True)
class RegionReport:
    region: Region
    builds: tuple[Build, ...]


def run(program: Program, matrix: Matrix, out: pathlib.Path, *, finite_inputs: bool = False) -> list[RegionReport]:
    """Build every candidate of every region under ``out/regions/<symbol>``: rendered in turn (the codegen knobs are
    process-wide DaCe config), compiled one per physical core, duplicates marked in candidate order."""
    reports = []
    with ThreadPoolExecutor(max_workers=len(machine.physical_cores())) as pool:
        for region in program.regions:
            folder = out / "regions" / region.symbol
            renders: dict[RenderKey, str] = {}
            candidates = one_factor_at_a_time(matrix, region, finite_inputs=finite_inputs)
            sources = [write_source(region, cand, matrix, folder, renders) for cand in candidates]
            built = list(pool.map(lambda s, c: compile_source(s, c, matrix), sources, candidates))
            seen: dict[str, str] = {}
            reports.append(RegionReport(region, tuple(deduplicated(b, seen) for b in built)))
    return reports
