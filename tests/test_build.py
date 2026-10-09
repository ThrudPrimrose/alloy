# Copyright 2026 ETH Zurich and the Alloy authors.
import pathlib
import subprocess

import pytest
from helpers import MATRIX, outlined, region_with

from alloy.backend.build import build, parse_remarks
from alloy.backend.candidates import Candidate


def test_a_built_candidate_archives_an_entry_with_the_recorded_c_abi(tmp_path):
    region = region_with(outlined(), libm=True, reduction=False)

    sut = build(region, Candidate("c", "gcc"), MATRIX, tmp_path, {})

    assert sut.error == ""
    assert sut.archive is not None
    assert sut.archive.is_file()
    assert f"void {region.symbol}(" in sut.source.read_text()
    symbols = subprocess.run(["nm", "--defined-only", str(sut.archive)], capture_output=True, text=True, check=True)
    assert f" T {region.symbol}" in symbols.stdout


def test_a_candidate_whose_object_matches_an_earlier_one_is_marked_its_duplicate(tmp_path):
    region = region_with(outlined(), libm=True, reduction=False)
    seen: dict[str, str] = {}
    first = build(region, Candidate("c", "gcc"), MATRIX, tmp_path / "a", seen)

    sut = build(region, Candidate("cpp", "gcc"), MATRIX, tmp_path / "b", seen)

    assert first.duplicate_of == ""
    assert sut.object_hash == first.object_hash
    assert sut.duplicate_of == first.name


@pytest.mark.parametrize(
    ("line", "vectorized", "missed"),
    [
        ("k.c:29:21: optimized: loop vectorized using 64 byte vectors", 1, ()),
        ("k.c:29:21: missed: couldn't vectorize loop", 0, ("couldn't vectorize loop",)),
        (
            "k.c:30:23: remark: loop not vectorized: library call cannot be vectorized"
            " [-Rpass-analysis=loop-vectorize]",
            0,
            ("loop not vectorized: library call cannot be vectorized",),
        ),
        ("other.c:3:1: missed: couldn't vectorize loop", 0, ()),
    ],
)
def test_compiler_remarks_about_the_source_are_counted_and_their_tags_dropped(line, vectorized, missed):
    sut = parse_remarks(line, pathlib.Path("/x/k.c"))

    assert (sut.vectorized, sut.missed) == (vectorized, missed)
