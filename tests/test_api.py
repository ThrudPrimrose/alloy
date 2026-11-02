# Copyright 2026 ETH Zurich and the Alloy authors.
import dataclasses
import math
import pathlib

import dace
import numpy as np
import pytest

from alloy import api
from alloy.backend.build import Build
from alloy.backend.candidates import one_factor_at_a_time
from alloy.backend.sweep import ScopeReport
from alloy.evaluate import timing
from alloy.evaluate.timing import Measured, ProgramTiming, ScopeTiming, Timings
from alloy.evaluate.verify import Verdict
from alloy.frontend import inputs, scopes
from alloy.heuristics import predict
from alloy.report import Mode
from helpers import REDUCTIONS, SCALE_MANIFEST, gcc_and_clang, gcc_only, load_program, write_manifest

N = dace.symbol("N")


@dace.program
def roots(x: dace.float64[N], y: dace.float64[N], z: dace.float64[N]):
    for i in dace.map[0:N]:
        y[i] = np.sqrt(x[i])
    for i in dace.map[0:N]:
        z[i] = y[i] * 2.0


def test_profile_mode_needs_a_manifest_to_know_the_sizes_it_times_at(tmp_path):
    sdfg = load_program(f"{REDUCTIONS}:scale").to_sdfg()

    with pytest.raises(ValueError, match="profile mode times at declared sizes, so it needs a manifest"):
        api.generate(sdfg, tmp_path / "out", matrix=gcc_only(tmp_path))


def test_without_a_manifest_a_program_any_input_suits_is_verified_on_derived_draws_and_its_picks_linked(tmp_path):
    sdfg = load_program(f"{REDUCTIONS}:scale").to_sdfg()

    sut = api.generate(sdfg, tmp_path / "out", matrix=gcc_only(tmp_path), mode=Mode.SPECULATIVE)

    assert sut.verification is not None and sut.timings is None and sut.predictions is not None
    (rep,) = sut.scopes
    assert (
        sut.winners is not None and sut.verification.verdicts[rep.scope.symbol][sut.winners[rep.scope.symbol].name].ok
    )
    assert (tmp_path / "out" / "best" / "Makefile").is_file()


def test_without_a_manifest_a_program_whose_inputs_have_a_domain_links_every_scopes_default_build(tmp_path):
    sdfg = roots.to_sdfg()

    sut = api.generate(sdfg, tmp_path / "out", matrix=gcc_only(tmp_path), mode=Mode.SPECULATIVE)

    assert inputs.domain_gap(sut.program.original) == "calls sqrt"
    assert len(sut.scopes) == 2 and sut.verification is None
    assert sut.winners == {rep.scope.symbol: rep.builds[0] for rep in sut.scopes}
    assert sut.report.is_file()


def test_a_program_without_a_loop_nest_is_refused_by_name(tmp_path):
    sdfg = dace.SDFG("no_nest")
    sdfg.add_array("x", [1], dace.float64)
    state = sdfg.add_state()
    tasklet = state.add_tasklet("one", {}, {"o"}, "o = 1.0")
    state.add_edge(tasklet, "o", state.add_write("x"), None, dace.Memlet("x[0]"))

    with pytest.raises(ValueError, match="no_nest: no top-level loop nest"):
        api.generate(sdfg, tmp_path / "out", matrix=gcc_only(tmp_path))


def test_a_small_program_goes_through_the_whole_sweep_and_links_a_verified_winner(tmp_path):
    """``scale``: one scope, every single-factor variant of gcc and clang, each built, verified on fuzzed inputs and
    timed, and the winner linked into alloy_full."""
    matrix = gcc_and_clang(tmp_path)
    matrix = dataclasses.replace(
        matrix, timing=dataclasses.replace(matrix.timing, screen_reps=3, final_reps=5, max_program_cache_factor=1.0)
    )
    manifest = write_manifest(tmp_path, "scale", SCALE_MANIFEST)
    sdfg = load_program(f"{REDUCTIONS}:scale").to_sdfg()
    (scope,) = scopes.outline(sdfg, matrix.libm_calls).scopes
    swept = one_factor_at_a_time(matrix, scope)

    sut = api.generate(sdfg, tmp_path / "out", manifest=manifest, matrix=matrix)

    (report,) = sut.scopes
    assert {candidate.compiler for candidate in swept} == {"gcc", "clang"}
    assert {"", "contract", "noerrno"} <= {candidate.fp_level for candidate in swept}
    assert len(report.builds) + len(report.pruned) == len(swept)
    assert not [build.name for build in report.builds if build.error]
    assert sut.verification is not None and sut.timings is not None
    verdicts = sut.verification.verdicts[scope.symbol]
    assert all(verdicts[build.name].ok for build in report.builds if not build.duplicate_of)
    full = sut.timings.program.arms["alloy_full"]
    assert full.verdict.ok and math.isfinite(full.median)


def last_distinct_build(rep: ScopeReport) -> str:
    """A candidate the sweep has no other reason to pick: never the reference every default falls back to."""
    name = next(b.name for b in reversed(rep.builds) if not b.duplicate_of and not b.error and b.archive)
    assert name != rep.builds[0].name, "the matrix must give the scope a second distinct build"
    return name


def picked(reports: list[ScopeReport], arm: Verdict) -> Timings:
    """Timings naming each scope's last distinct build, with ``arm`` as alloy-full's verdict."""
    measured = Measured(1e-3, 1e-3, 1e-3, arm)
    named = {r.scope.symbol: last_distinct_build(r) for r in reports}
    scoped = {
        symbol: ScopeTiming(
            {timing.REFERENCE: measured, name: measured}, {timing.REFERENCE: measured}, name, {"N": 64}, {"N": 64}
        )
        for symbol, name in named.items()
    }
    return Timings(scoped, ProgramTiming({"alloy_full": measured, "dace_default": measured}, {"N": 64}))


def assert_best_is(sut: api.Result, names: dict[str, str]) -> None:
    assert sut.winners is not None and sut.best is not None
    assert {symbol: build.name for symbol, build in sut.winners.items()} == names
    assert {scope.symbol: scope.candidate for scope in sut.best.scopes} == names
    folder = sut.report.parent / "best"
    for scope in sut.best.scopes:
        winner = sut.winners[scope.symbol]
        assert (folder / scope.source).read_bytes() == winner.source.read_bytes()
        assert scope.flags == winner.flags


def test_what_best_links_is_the_build_the_speculative_pick_names(tmp_path, monkeypatch):
    sdfg = load_program(f"{REDUCTIONS}:scale").to_sdfg()
    names: dict[str, str] = {}

    def choose(rep: ScopeReport, *_: object, **__: object) -> Build:
        names[rep.scope.symbol] = last_distinct_build(rep)
        return next(b for b in rep.builds if b.name == names[rep.scope.symbol])

    monkeypatch.setattr(predict, "choose", choose)
    monkeypatch.setattr(predict, "predictions", lambda *_: {})  # measures the machine, and the pick is stubbed

    sut = api.generate(sdfg, tmp_path / "out", matrix=gcc_only(tmp_path), mode=Mode.SPECULATIVE)

    assert_best_is(sut, names)


def profile_run(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, arm: Verdict) -> tuple[api.Result, list]:
    """A profile run of ``scale`` whose timing names a winner without timing anything."""
    manifest = write_manifest(tmp_path, "scale", SCALE_MANIFEST)
    seen: list[ScopeReport] = []

    def time_program(_: object, reports: list[ScopeReport], *__: object) -> Timings:
        seen.extend(reports)
        return picked(reports, arm)

    monkeypatch.setattr(timing, "time_program", time_program)
    sdfg = load_program(f"{REDUCTIONS}:scale").to_sdfg()
    return api.generate(sdfg, tmp_path / "out", manifest=manifest, matrix=gcc_only(tmp_path)), seen


def test_what_best_links_is_the_build_the_timing_names(tmp_path, monkeypatch):
    sut, (rep,) = profile_run(tmp_path, monkeypatch, Verdict("pass"))

    assert_best_is(sut, {rep.scope.symbol: last_distinct_build(rep)})


def test_winners_the_whole_program_refuses_give_way_to_the_reference(tmp_path, monkeypatch):
    """Two scopes each inside the band can compound past it: their combination is what the verdict is about."""
    sut, (rep,) = profile_run(tmp_path, monkeypatch, Verdict("fail"))

    assert_best_is(sut, {rep.scope.symbol: rep.builds[0].name})
