# Copyright 2026 ETH Zurich and the Alloy authors.
from alloy import api
from helpers import EXAMPLE, gcc_only, load_program


def test_without_a_manifest_every_region_is_built_and_reported_but_not_verified(tmp_path):
    sdfg = load_program(f"{EXAMPLE}:two_regions").to_sdfg()

    sut = api.generate(sdfg, tmp_path / "out", matrix=gcc_only(tmp_path))

    assert len(sut.regions) == 3
    assert all(rep.builds for rep in sut.regions)
    assert (sut.verification, sut.timings) == (None, None)
    assert sut.report.is_file()
