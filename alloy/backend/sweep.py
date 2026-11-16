# Copyright 2026 ETH Zurich and the Alloy authors.
"""Build every candidate of every scope of an outlined program."""

import pathlib
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from alloy import machine
from alloy.backend.build import Build, compile_source, deduplicated, write_source
from alloy.backend.candidates import Candidate, RenderKey, one_factor_at_a_time
from alloy.configuration_matrix import Matrix
from alloy.frontend.scopes import Program, Scope
from alloy.heuristics import prune
from alloy.heuristics.ranges import Interval


@dataclass(slots=True, frozen=True)
class ScopeReport:
    """A scope's builds in candidate order, and the candidates pruned before building with their reasons."""

    scope: Scope
    builds: tuple[Build, ...]
    pruned: tuple[prune.Pruned, ...] = ()


def reference_first(builds: list[Build]) -> list[Build]:
    """``builds`` with the first that compiled in front: it is the reference every other candidate is judged against
    (a C++ tasklet cannot render in the C default, and the C++ builds then carry the scope)."""
    index = next((i for i, b in enumerate(builds) if b.archive is not None), None)
    if index is None:
        raise RuntimeError(f"no candidate built: {builds[0].error if builds else 'empty sweep'}")
    return [builds[index], *builds[:index], *builds[index + 1 :]]


def run(
    program: Program,
    matrix: Matrix,
    out: pathlib.Path,
    *,
    finite_inputs: bool = False,
    ranges: Mapping[str, Interval] | None = None,
) -> list[ScopeReport]:
    """Build every candidate of every scope under ``out/scopes/<symbol>`` in three stages: each compiler's default,
    then every cell that sets no vector width or tail, then the vector cells; each stage minus what :func:`prune.prune`
    rules out given the builds before it. Rendered in turn (the codegen
    knobs are process-wide DaCe config), compiled in parallel (:func:`machine.compile_jobs`), duplicates marked in
    candidate order."""
    reports = []
    host_isas = matrix.host_isas(machine.cpu_flags())
    with ThreadPoolExecutor(max_workers=machine.compile_jobs()) as pool:
        for scope in program.scopes:
            folder = out / "scopes" / scope.symbol
            renders: dict[RenderKey, pathlib.Path] = {}

            def built(cands: list[Candidate]) -> list[Build]:
                sources = [write_source(scope, cand, matrix, folder, renders) for cand in cands]
                return list(pool.map(lambda s, c: compile_source(s, c, matrix), sources, cands))

            candidates = one_factor_at_a_time(matrix, scope, finite_inputs=finite_inputs)
            facts = prune.facts(scope, ranges)
            natives = [c for c in candidates if prune.is_native(c)]
            first = dict(zip(natives, built(natives), strict=True))
            # the cells that may make a loop vectorize (an emission form, an FP level, a rung) are built before the
            # vector cells are pruned, so "nothing vectorizes" reads every one of them
            plain = [c for c in candidates if c not in first and not prune.is_vector_cell(c)]
            kept, pruned = prune.prune(plain, matrix, facts, list(first.values()), host_isas)
            second = dict(zip(kept, built(kept), strict=True))
            vector = [c for c in candidates if c not in first and prune.is_vector_cell(c)]
            kept, pruned_vector = prune.prune(vector, matrix, facts, [*first.values(), *second.values()], host_isas)
            later = second | dict(zip(kept, built(kept), strict=True))
            pruned = pruned + pruned_vector
            seen: dict[str, str] = {}
            ordered = [first.get(c) or later[c] for c in candidates if c in first or c in later]
            reports.append(
                ScopeReport(scope, tuple(deduplicated(b, seen) for b in reference_first(ordered)), tuple(pruned))
            )
    return reports
