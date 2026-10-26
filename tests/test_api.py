# Copyright 2026 ETH Zurich and the Alloy authors.
import dataclasses
import math

import dace
import numpy as np
import pytest

from alloy import api
from alloy.backend.candidates import one_factor_at_a_time
from alloy.frontend import inputs, scopes
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
    """``scale``: one scope, every single-factor variant of gcc and clang (54 on an x86-64 host), each built,
    verified on fuzzed inputs and timed, and the winner linked into alloy_full."""
    matrix = gcc_and_clang(tmp_path)
    matrix = dataclasses.replace(
        matrix, timing=dataclasses.replace(matrix.timing, screen_reps=3, final_reps=5, max_program_cache_factor=1.0)
    )
    manifest = write_manifest(tmp_path, "scale", SCALE_MANIFEST)
    sdfg = load_program(f"{REDUCTIONS}:scale").to_sdfg()
    (scope,) = scopes.outline(sdfg, matrix.libm_calls).scopes
    swept = one_factor_at_a_time(matrix, scope, max_elements=inputs.largest_array(manifest, sdfg))

    sut = api.generate(sdfg, tmp_path / "out", manifest=manifest, matrix=matrix)

    (report,) = sut.scopes
    assert len(swept) >= 40 and len(report.builds) + len(report.pruned) == len(swept)
    assert not [build.name for build in report.builds if build.error]
    assert sut.verification is not None and sut.timings is not None
    verdicts = sut.verification.verdicts[scope.symbol]
    assert all(verdicts[build.name].ok for build in report.builds if not build.duplicate_of)
    full = sut.timings.program.arms["alloy_full"]
    assert full.verdict.ok and math.isfinite(full.median)
