# Copyright 2026 ETH Zurich and the Alloy authors.
import dataclasses
import math

import dace
import pytest

from alloy import api
from alloy.backend.candidates import one_factor_at_a_time
from alloy.frontend import inputs, regions
from helpers import EXAMPLE, REDUCTIONS, SCALE_MANIFEST, gcc_and_clang, gcc_only, load_program, write_manifest


def test_without_a_manifest_every_region_is_built_and_reported_but_not_verified(tmp_path):
    sdfg = load_program(f"{EXAMPLE}:two_regions").to_sdfg()

    sut = api.generate(sdfg, tmp_path / "out", matrix=gcc_only(tmp_path))

    assert len(sut.regions) == 3
    assert all(rep.builds for rep in sut.regions)
    assert (sut.verification, sut.timings) == (None, None)
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
    """``scale``: one region, every single-factor variant of gcc and clang (54 on an x86-64 host), each built,
    verified on fuzzed inputs and timed, and the winner linked into alloy_full."""
    matrix = gcc_and_clang(tmp_path)
    matrix = dataclasses.replace(
        matrix, timing=dataclasses.replace(matrix.timing, screen_reps=3, final_reps=5, max_program_cache_factor=1.0)
    )
    manifest = write_manifest(tmp_path, "scale", SCALE_MANIFEST)
    sdfg = load_program(f"{REDUCTIONS}:scale").to_sdfg()
    (region,) = regions.outline(sdfg, matrix.libm_calls).regions
    swept = one_factor_at_a_time(matrix, region, max_elements=inputs.largest_array(manifest, sdfg))

    sut = api.generate(sdfg, tmp_path / "out", manifest=manifest, matrix=matrix)

    (report,) = sut.regions
    assert len(swept) >= 40 and len(report.builds) == len(swept)
    assert not [build.name for build in report.builds if build.error]
    assert sut.verification is not None and sut.timings is not None
    verdicts = sut.verification.verdicts[region.symbol]
    assert all(verdicts[build.name].ok for build in report.builds if not build.duplicate_of)
    full = sut.timings.program.arms["alloy_full"]
    assert full.verdict.ok and math.isfinite(full.median)
