# Copyright 2026 ETH Zurich and the Alloy authors.
"""Build every candidate of every scope of an outlined program."""

import pathlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from alloy import machine
from alloy.backend.build import Build, compile_source, deduplicated, write_source
from alloy.backend.candidates import Candidate, RenderKey, one_factor_at_a_time
from alloy.configuration_matrix import Matrix
from alloy.frontend.scopes import Program, Scope
from alloy.heuristics import prune


@dataclass(slots=True, frozen=True)
class ScopeReport:
    """A scope's builds in candidate order, and the candidates pruned before building with their reasons."""

    scope: Scope
    builds: tuple[Build, ...]
    pruned: tuple[prune.Pruned, ...] = ()


def run(
    program: Program,
    matrix: Matrix,
    out: pathlib.Path,
    *,
    finite_inputs: bool = False,
    max_elements: int | None = None,
) -> list[ScopeReport]:
    """Build every candidate of every scope under ``out/scopes/<symbol>`` in two stages: each compiler's default
    first, then the rest minus what :func:`prune.prune` rules out given those builds. Rendered in turn (the codegen
    knobs are process-wide DaCe config), compiled in parallel (:func:`machine.compile_jobs`), duplicates marked in
    candidate order. ``max_elements`` bounds the index widths tried (:func:`candidates.index_widths`)."""
    reports = []
    host_isas = matrix.host_isas(machine.cpu_flags())
    with ThreadPoolExecutor(max_workers=machine.compile_jobs()) as pool:
        for scope in program.scopes:
            folder = out / "scopes" / scope.symbol
            renders: dict[RenderKey, pathlib.Path] = {}

            def built(cands: list[Candidate]) -> list[Build]:
                sources = [write_source(scope, cand, matrix, folder, renders) for cand in cands]  # noqa: B023 -- called in this iteration
                return list(pool.map(lambda s, c: compile_source(s, c, matrix), sources, cands))

            candidates = one_factor_at_a_time(matrix, scope, finite_inputs=finite_inputs, max_elements=max_elements)
            natives = [c for c in candidates if prune.is_native(c)]
            first = dict(zip(natives, built(natives), strict=True))
            rest, pruned = prune.prune(
                [c for c in candidates if c not in first], matrix, prune.facts(scope), list(first.values()), host_isas
            )
            later = dict(zip(rest, built(rest), strict=True))
            seen: dict[str, str] = {}
            ordered = [first.get(c) or later[c] for c in candidates if c in first or c in later]
            reports.append(ScopeReport(scope, tuple(deduplicated(b, seen) for b in ordered), tuple(pruned)))
    return reports
