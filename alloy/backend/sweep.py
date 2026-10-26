# Copyright 2026 ETH Zurich and the Alloy authors.
"""Build every candidate of every scope of an outlined program."""

import pathlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from alloy import machine
from alloy.backend.build import Build, compile_source, deduplicated, write_source
from alloy.backend.candidates import RenderKey, one_factor_at_a_time
from alloy.configuration_matrix import Matrix
from alloy.frontend.scopes import Program, Scope


@dataclass(slots=True, frozen=True)
class ScopeReport:
    scope: Scope
    builds: tuple[Build, ...]


def run(
    program: Program,
    matrix: Matrix,
    out: pathlib.Path,
    *,
    finite_inputs: bool = False,
    max_elements: int | None = None,
) -> list[ScopeReport]:
    """Build every candidate of every scope under ``out/scopes/<symbol>``: rendered in turn (the codegen knobs are
    process-wide DaCe config), compiled in parallel (:func:`machine.compile_jobs`), duplicates marked in candidate
    order. ``max_elements`` bounds the index widths tried (:func:`candidates.index_widths`)."""
    reports = []
    with ThreadPoolExecutor(max_workers=machine.compile_jobs()) as pool:
        for scope in program.scopes:
            folder = out / "scopes" / scope.symbol
            renders: dict[RenderKey, pathlib.Path] = {}
            candidates = one_factor_at_a_time(matrix, scope, finite_inputs=finite_inputs, max_elements=max_elements)
            sources = [write_source(scope, cand, matrix, folder, renders) for cand in candidates]
            built = list(pool.map(lambda s, c: compile_source(s, c, matrix), sources, candidates))
            seen: dict[str, str] = {}
            reports.append(ScopeReport(scope, tuple(deduplicated(b, seen) for b in built)))
    return reports
