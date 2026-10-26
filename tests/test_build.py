# Copyright 2026 ETH Zurich and the Alloy authors.
import pathlib
import subprocess

import dace
import pytest

from alloy import configuration_matrix
from alloy.backend import sweep
from alloy.backend.build import build, parse_remarks
from alloy.backend.candidates import Candidate
from alloy.frontend import scopes
from helpers import MATRIX, gcc_only, outlined, scope_with, variant

N = dace.symbol("N")


@dace.program
def scale(x: dace.float64[N], y: dace.float64[N], a: dace.float64):
    y[:] = a * x


def scale_scope() -> scopes.Scope:
    (scope,) = scopes.outline(scale.to_sdfg(), MATRIX.libm_calls).scopes
    return scope


def test_a_built_candidate_archives_an_entry_with_the_recorded_c_abi(tmp_path):
    scope = scope_with(outlined(), libm=True, reduction=False)

    sut = build(scope, Candidate("c", "gcc"), MATRIX, tmp_path, {})

    assert sut.error == ""
    assert sut.archive is not None
    assert sut.archive.is_file()
    assert f"void {scope.symbol}(" in sut.source.read_text()
    symbols = subprocess.run(["nm", "--defined-only", str(sut.archive)], capture_output=True, text=True, check=True)
    assert f" T {scope.symbol}" in symbols.stdout


def test_a_candidate_whose_object_matches_an_earlier_one_is_marked_its_duplicate(tmp_path):
    scope = scope_with(outlined(), libm=True, reduction=False)
    seen: dict[str, str] = {}
    first = build(scope, Candidate("c", "gcc"), MATRIX, tmp_path / "a", seen)

    sut = build(scope, Candidate("cpp", "gcc"), MATRIX, tmp_path / "b", seen)

    assert first.duplicate_of == ""
    assert sut.object_hash == first.object_hash
    assert sut.duplicate_of == first.name


def test_a_parallel_sweep_marks_each_duplicate_against_the_first_candidate_in_candidate_order(tmp_path):
    sut = sweep.run(outlined(), gcc_only(tmp_path), tmp_path / "out")

    duplicates = 0
    for report in sut:
        first: dict[str, str] = {}
        for built in report.builds:
            if built.archive is None:
                continue
            owner = first.setdefault(built.object_hash, built.name)
            assert built.duplicate_of == ("" if owner == built.name else owner), built.name
            duplicates += bool(built.duplicate_of)
    assert duplicates > 0, "the sweep built no duplicate, so its order went untested"


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


def avx512_matrix(tmp_path: pathlib.Path) -> configuration_matrix.Matrix:
    """The shipped matrix building for x86-64-v4 instead of the host, so AVX-512 code is emitted on any x86 box."""
    return configuration_matrix.load(variant(tmp_path, '"-march=native"', '"-march=x86-64-v4"'))


@pytest.mark.parametrize(
    "compiler", [pytest.param("gcc", marks=pytest.mark.gcc), pytest.param("clang", marks=pytest.mark.clang)]
)
def test_a_full_mask_tail_runs_its_loop_under_masks_and_a_scalar_remainder_does_not(tmp_path, compiler):
    matrix = avx512_matrix(tmp_path)
    scope = scale_scope()

    full = build(scope, Candidate("c", compiler, isa="avx512", tail="full_mask"), matrix, tmp_path / "full", {})
    scalar = build(scope, Candidate("c", compiler, isa="avx512", tail="scalar_remainder"), matrix, tmp_path / "s", {})

    assert full.error == "" and scalar.error == ""
    assert full.masked_ops > 0
    assert scalar.masked_ops == 0


def test_an_sve_tail_renders_the_scopes_maps_as_explicit_sve_loops(tmp_path):
    scope = scale_scope()

    sut = build(scope, Candidate("cpp", "gcc", isa="sve", tail="sve_intrinsics"), MATRIX, tmp_path, {})

    assert "svwhilele" in sut.source.read_text() and "#include <arm_sve.h>" in sut.source.read_text()


def test_a_scope_the_sve_loop_cannot_express_is_a_failed_build_naming_why(tmp_path):
    scope = scope_with(outlined(), libm=True, reduction=False)
    candidate = Candidate("cpp", "gcc", isa="sve", tail="sve_intrinsics", note="tail sve_intrinsics on sve")

    sut = build(scope, candidate, MATRIX, tmp_path, {})

    assert sut.archive is None
    assert "#error alloy: tail sve_intrinsics on sve cannot be rendered" in sut.source.read_text()
    assert "sin(" in sut.source.read_text()
