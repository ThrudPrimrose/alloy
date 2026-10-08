# Copyright 2026 ETH Zurich and the Alloy authors.
import json
import pathlib
import subprocess

import pytest

from alloy import configuration_matrix, regions, report
from alloy.build import build, parse_remarks
from alloy.candidates import Candidate, one_factor_at_a_time
from alloy.cli import load_program

EXAMPLE = pathlib.Path(__file__).parent.parent / "examples" / "two_regions.py"
MATRIX = configuration_matrix.load()


def outlined() -> regions.Program:
    return regions.outline(load_program(f"{EXAMPLE}:two_regions"), MATRIX.libm_calls)


def region_with(program: regions.Program, *, libm: bool, reduction: bool) -> regions.Region:
    (match,) = [r for r in program.regions if r.calls_libm == libm and r.has_reduction == reduction]
    return match


def test_the_libm_map_and_the_sum_become_separate_regions():
    sut = outlined()

    assert len(sut.regions) == len(sut.calls) == 3
    assert [r.calls_libm for r in sut.regions].count(True) == 1
    assert [r.has_reduction for r in sut.regions].count(True) == 1


def test_a_vector_math_library_is_tried_only_where_libm_is_called():
    program = outlined()
    libm_region = region_with(program, libm=True, reduction=False)
    reduction_region = region_with(program, libm=False, reduction=True)

    assert any(c.veclib != "none" for c in one_factor_at_a_time(MATRIX, libm_region))
    assert all(c.veclib == "none" for c in one_factor_at_a_time(MATRIX, reduction_region))


def test_reassociation_is_tried_only_where_something_reduces():
    program = outlined()
    libm_region = region_with(program, libm=True, reduction=False)
    reduction_region = region_with(program, libm=False, reduction=True)

    assert any(c.fp_level == "reassoc" for c in one_factor_at_a_time(MATRIX, reduction_region))
    assert all(c.fp_level != "reassoc" for c in one_factor_at_a_time(MATRIX, libm_region))


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


def test_the_report_lists_every_candidate_of_every_region(tmp_path):
    program = outlined()
    reports = [
        report.RegionReport(r, (build(r, Candidate("c", "gcc"), MATRIX, tmp_path / r.symbol, {}),))
        for r in program.regions
    ]

    report.write(reports, MATRIX, tmp_path)

    data = json.loads((tmp_path / "report.json").read_text())
    assert [r["symbol"] for r in data] == [r.symbol for r in program.regions]
    assert all(len(r["candidates"]) == 1 and r["candidates"][0]["archive"] for r in data)
    assert (tmp_path / "report.md").read_text().count("## ") == len(program.regions)
    assert (tmp_path / "configuration_matrix.toml").read_bytes() == MATRIX.path.read_bytes()


def variant(tmp_path: pathlib.Path, old: str, new: str) -> pathlib.Path:
    """The shipped matrix with ``old`` replaced by ``new`` once."""
    text = MATRIX.path.read_text()
    assert old in text
    path = tmp_path / "matrix.toml"
    path.write_text(text.replace(old, new, 1))
    return path


def gcc_only(tmp_path: pathlib.Path) -> configuration_matrix.Matrix:
    text = MATRIX.path.read_text()
    first, last = text.index("# clang 22"), text.index("# Readable-codegen knobs")
    return configuration_matrix.load(variant(tmp_path, text[first:last], ""))


def test_the_candidates_are_exactly_what_the_matrix_lists(tmp_path):
    matrix = gcc_only(tmp_path)
    region = region_with(outlined(), libm=False, reduction=True)

    sut = one_factor_at_a_time(matrix, region)

    gcc = matrix.compilers["gcc"]
    per_language = (
        1 + sum(len(v) - 1 for v in matrix.knobs.values()) + 1 + (len(gcc.fp) - 2) + (len(gcc.cost_model) - 1)
    )
    assert {c.compiler for c in sut} == {"gcc"}
    assert {c.resolved(matrix)[1] for c in sut} == {"strict", "contract", "noerrno", "reassoc"}
    assert len(sut) == len(matrix.languages) * per_language


def test_fast_math_is_tried_only_when_inputs_are_declared_finite(tmp_path):
    matrix = gcc_only(tmp_path)
    region = region_with(outlined(), libm=False, reduction=True)

    sut = one_factor_at_a_time(matrix, region, finite_inputs=True)

    assert "fast" in {c.resolved(matrix)[1] for c in sut}


def test_a_matrix_with_an_unknown_key_is_refused(tmp_path):
    path = variant(tmp_path, "schema = 1\n", "schema = 1\ntypo_key = 1\n")

    with pytest.raises(ValueError, match="unknown"):
        configuration_matrix.load(path)


def test_a_compiler_that_does_not_spell_every_fp_level_is_refused(tmp_path):
    path = variant(tmp_path, 'fast = ["-ffast-math"]\n', "")

    with pytest.raises(ValueError, match=r"compilers\.gcc\.fp: missing \['fast'\]"):
        configuration_matrix.load(path)


def test_a_compiler_not_on_path_is_skipped_with_its_reason(tmp_path):
    matrix = configuration_matrix.load(
        variant(tmp_path, 'c = "gcc"\ncpp = "g++"', 'c = "no-such-cc"\ncpp = "no-such-cxx"')
    )

    usable, skipped = matrix.usable_compilers()

    assert "gcc" not in usable
    assert skipped["gcc"] == "not on PATH: no-such-cc, no-such-cxx"
