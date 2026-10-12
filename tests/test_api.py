# Copyright 2026 ETH Zurich and the Alloy authors.
import dace
import pytest

from alloy import api
from helpers import EXAMPLE, gcc_only, load_program


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
