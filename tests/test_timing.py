# Copyright 2026 ETH Zurich and the Alloy authors.
import dataclasses
import math

from alloy import machine
from alloy.backend.candidates import Candidate
from alloy.backend.sweep import ScopeReport
from alloy.evaluate import timing, verify
from alloy.evaluate.link import Linker
from alloy.frontend import inputs
from helpers import (
    MATRIX,
    ROW_SUM_MANIFEST,
    SCALE_MANIFEST,
    build,
    handwritten_archive,
    program_and_cases,
    write_manifest,
)

# fewer reps, and programs capped at 4x the largest cache (production: 16x), so a scope that touches one vector of
# row_sum does not grow its matrix past what three parallel test workers leave each child
FEW_REPS = dataclasses.replace(
    MATRIX, timing=dataclasses.replace(MATRIX.timing, screen_reps=3, final_reps=5, max_program_cache_factor=4.0)
)


def test_the_median_ci_takes_the_order_statistics_of_hoefler_and_belli():
    sut = timing.median_ci([float(x) for x in range(31, 0, -1)])

    assert sut == (16.0, 10.0, 22.0)


def test_a_sized_scope_touches_the_target_bytes_and_not_much_more(tmp_path):
    program, _ = program_and_cases(tmp_path, "row_sum", ROW_SUM_MANIFEST)
    scope = program.scopes[-1]
    target = 48 * 2**20

    sut = timing.footprint(scope.sdfg, timing.sized(scope.sdfg, program.original, {"M": 64, "N": 512}, target, 1e12))

    assert target <= sut < 1.01 * target


def test_a_scope_touching_one_vector_stops_growing_at_the_program_cap(tmp_path):
    program, _ = program_and_cases(tmp_path, "row_sum", ROW_SUM_MANIFEST)
    init = program.scopes[0]  # writes out(M) only; growing M alone also grows a(M, N)
    cap = 256 * 2**20

    sut = timing.sized(init.sdfg, program.original, {"M": 64, "N": 512}, 48 * 2**20, cap)

    assert timing.footprint(program.original, sut) < 1.01 * cap
    assert timing.footprint(init.sdfg, sut) < 48 * 2**20


def test_a_timing_size_never_outgrows_the_memory_the_machine_has(tmp_path, monkeypatch):
    # A cache-only cap picked a 2 GiB-per-array preset on a CI runner with a large L3 and the reference ran out of
    # memory; the memory cap must bind when it is the smaller one.
    program, _ = program_and_cases(tmp_path, "row_sum", ROW_SUM_MANIFEST)
    manifest = write_manifest(tmp_path, "row_sum", ROW_SUM_MANIFEST)
    available = 64 * 2**20
    monkeypatch.setattr(machine, "largest_cache_bytes", lambda: 2**30)
    monkeypatch.setattr(machine, "available_memory", lambda: available)

    sut = timing.stage_sizes(program.original, program.original, manifest, 2.0, 16.0, grow_only=False)

    assert timing.footprint(program.original, sut) <= 1.01 * available / machine.TIMING_COPIES


def test_the_scope_timer_reads_nothing_for_an_empty_scope_and_time_for_a_real_one(tmp_path):
    program, cases = program_and_cases(tmp_path, "scale", SCALE_MANIFEST)
    (scope,) = program.scopes
    linker = Linker(program, MATRIX, tmp_path / "out")
    real = build(scope, Candidate("c", "gcc"), MATRIX, tmp_path / "ref", {})
    assert real.archive is not None
    folders = [
        str(linker.compile({scope.symbol: handwritten_archive(tmp_path, scope, "")}, "empty")),
        str(linker.compile({scope.symbol: real.archive}, "real")),
    ]
    draw = inputs.at(write_manifest(tmp_path, "scale", SCALE_MANIFEST), {"N": 4 * 2**20})

    sut = verify.in_child(
        timing.time_arms, (folders, scope.symbol, {**draw.values, **draw.sizes}, 3), machine.physical_cores()[:4], 1.0
    )

    empty, real_times = sut
    assert max(empty) < 1e-5
    assert min(real_times) > 10 * max(empty)


def test_alloy_full_links_every_scope_winner_and_matches_dace_default(tmp_path):
    program, cases = program_and_cases(tmp_path, "row_sum", ROW_SUM_MANIFEST)
    reports = [
        ScopeReport(
            r,
            (
                build(r, Candidate("c", "gcc"), FEW_REPS, tmp_path / r.symbol, {}),
                build(r, Candidate("c", "gcc", fp_level="contract"), FEW_REPS, tmp_path / f"{r.symbol}2", {}),
            ),
        )
        for r in program.scopes
    ]
    verification = verify.verify(program, FEW_REPS, reports, cases, tmp_path / "out")
    linker = Linker(program, FEW_REPS, tmp_path / "out")

    timings = timing.time_program(linker, reports, verification, write_manifest(tmp_path, "row_sum", ROW_SUM_MANIFEST))
    sut = timings.program

    assert set(sut.arms) == {"dace_default", "alloy_full"}
    assert all(m.verdict.ok and math.isfinite(m.median) for m in sut.arms.values())
    assert timing.footprint(program.original, sut.sizes) >= 2 * machine.largest_cache_bytes()
    assert all(r.winner in r.final for r in timings.scopes.values())


def test_alloy_full_runs_the_build_each_scope_timing_named(tmp_path, monkeypatch):
    """The named winner is wrong on purpose: only a program that really links it can fail."""
    program, cases = program_and_cases(tmp_path, "scale", SCALE_MANIFEST)
    (scope,) = program.scopes
    good = build(scope, Candidate("c", "gcc"), FEW_REPS, tmp_path / "good", {})
    wrong = handwritten_archive(tmp_path, scope, "for (int64_t i = 0; i < N; ++i) out[i] = 3.0 * a[i];")
    report = ScopeReport(scope, (good, dataclasses.replace(good, name="wrong", archive=wrong, object_hash="wrong")))
    verification = verify.verify(program, FEW_REPS, [report], cases, tmp_path / "out")
    winner = timing.ScopeTiming({}, {}, "wrong", {"N": 64}, {"N": 64})
    monkeypatch.setattr(timing, "time_scope", lambda *_: winner)
    manifest = write_manifest(tmp_path, "scale", SCALE_MANIFEST)

    sut = timing.time_program(Linker(program, FEW_REPS, tmp_path / "out"), [report], verification, manifest)

    assert sut.program.arms["alloy_full"].verdict.status == "fail"


def test_a_sum_that_rounded_alike_on_every_draw_stays_a_candidate_at_the_larger_timing_size(tmp_path):
    """Reversing a sum rounds differently once the rows are long; the small draws called the output reproducible."""
    program, cases = program_and_cases(tmp_path, "row_sum", ROW_SUM_MANIFEST)
    init, summing = program.scopes
    good = build(summing, Candidate("c", "gcc"), FEW_REPS, tmp_path / "good", {})
    body = (
        "for (int i = 0; i < M; ++i) { double s = 0; for (int j = N - 1; j >= 0; --j) s += a[i * N + j]; out[i] = s; }"
    )
    reversed_sum = handwritten_archive(tmp_path, summing, body)
    reversed_build = dataclasses.replace(good, name="reversed", archive=reversed_sum, object_hash="reversed")
    reports = [
        ScopeReport(init, (build(init, Candidate("c", "gcc"), FEW_REPS, tmp_path / "init", {}),)),
        ScopeReport(summing, (good, reversed_build)),
    ]
    verified = verify.verify(program, FEW_REPS, reports, cases, tmp_path / "out")
    verdicts = {
        **verified.verdicts,
        summing.symbol: {good.name: verify.Verdict("exact"), "reversed": verify.Verdict("exact")},
    }
    alike = dataclasses.replace(verified, verdicts=verdicts, nondeterministic=frozenset())
    manifest = write_manifest(tmp_path, "row_sum", ROW_SUM_MANIFEST)

    sut = timing.time_scope(Linker(program, FEW_REPS, tmp_path / "out"), reports[1], alike, manifest)

    assert sut.screen["reversed"].verdict.status == "pass", sut.screen["reversed"].verdict.detail
    assert sut.final["reversed"].verdict.status == "pass", sut.final["reversed"].verdict.detail


def measured(median: float, spread: float = 0.1, status: str = "pass") -> timing.Measured:
    return timing.Measured(median, median - spread, median + spread, verify.Verdict(status))  # type: ignore[arg-type]


def test_a_candidate_whose_interval_overlaps_the_reference_does_not_win():
    final = {timing.REFERENCE: measured(1.0), "close": measured(0.95)}

    assert timing.winner_of(final, ["close"]) == timing.REFERENCE


def test_the_fastest_clear_candidate_wins_past_a_wide_faster_one():
    final = {timing.REFERENCE: measured(1.0), "wide": measured(0.5, 0.6), "clear": measured(0.7)}

    assert timing.winner_of(final, ["wide", "clear"]) == "clear"


def test_a_failed_candidate_never_wins():
    final = {timing.REFERENCE: measured(1.0), "wrong": measured(0.1, status="fail")}

    assert timing.winner_of(final, ["wrong"]) == timing.REFERENCE
