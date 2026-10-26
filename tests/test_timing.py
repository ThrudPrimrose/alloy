# Copyright 2026 ETH Zurich and the Alloy authors.
import dataclasses
import math

from alloy import machine
from alloy.backend.build import build
from alloy.backend.candidates import Candidate
from alloy.backend.sweep import ScopeReport
from alloy.evaluate import timing, verify
from alloy.evaluate.link import Linker
from alloy.frontend import inputs
from helpers import MATRIX, ROW_SUM_MANIFEST, SCALE_MANIFEST, handwritten_archive, program_and_cases, write_manifest

FEW_REPS = dataclasses.replace(MATRIX, timing=dataclasses.replace(MATRIX.timing, screen_reps=3, final_reps=5))


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
