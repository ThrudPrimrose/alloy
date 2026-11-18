# Copyright 2026 ETH Zurich and the Alloy authors.
"""Build every candidate of every scope of an outlined program."""

import pathlib
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace

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
    sources: Mapping[str, pathlib.Path] | None = None,
    reference_only: bool = False,
) -> list[ScopeReport]:
    """Build every candidate of every scope under ``out/scopes/<symbol>`` in three stages: each compiler's default,
    then every cell that sets no vector width or tail, then the vector cells; each stage minus what :func:`prune.prune`
    rules out given the builds before it. Rendered in turn (the codegen
    knobs are process-wide DaCe config), compiled in parallel (:func:`machine.compile_jobs`), duplicates marked in
    candidate order.

    ``sources`` maps a scope symbol to a translation unit that replaces its rendering (an agent's edit of
    ``best/scopes/<symbol>.c``): the scope's reference stays its rendered default, the one build every other is
    verified against, and every candidate of the unit's language compiles the unit as ``agent_<candidate>``.
    ``reference_only`` builds each compiler's default and keeps the reference alone."""
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
            if reference_only:
                reports.append(ScopeReport(scope, (reference_first(list(first.values()))[0],)))
                continue
            if sources and scope.symbol in sources:
                reference = reference_first(list(first.values()))[0]
                unit = sources[scope.symbol]
                once: dict[str, str] = {}
                builds = edited(reference, candidates, unit, matrix, folder, pool)
                reports.append(ScopeReport(scope, tuple(deduplicated(b, once) for b in builds)))
                continue
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


def edited(
    reference: Build,
    candidates: list[Candidate],
    unit: pathlib.Path,
    matrix: Matrix,
    folder: pathlib.Path,
    pool: ThreadPoolExecutor,
) -> list[Build]:
    """``reference``, then ``unit`` compiled by every candidate of its language (by suffix), named ``agent_<name>``."""
    language = next((n for n, lang in matrix.languages.items() if f".{lang.suffix}" == unit.suffix), None)
    if language is None:
        raise ValueError(f"{unit.name}: no language of the matrix has the suffix {unit.suffix!r}")
    source = folder / "agent" / "variants" / unit.name
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(unit.read_bytes())
    own = [c for c in candidates if c.language == language]
    builds = pool.map(lambda c: compile_source(source, c, matrix), own)
    return [reference, *(replace(b, name=f"agent_{b.name}") for b in builds)]
