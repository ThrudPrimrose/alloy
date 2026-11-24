# Copyright 2026 ETH Zurich and the Alloy authors.
import pathlib

import pytest

from alloy import configuration_matrix
from helpers import MATRIX, variant


@pytest.mark.parametrize(
    ("old", "new", "refusal"),
    [
        ("schema = 1\n", "schema = 1\ntypo_key = 1\n", "typo_key\n  Unexpected keyword argument"),
        ('fast = ["-ffast-math"]\n', "", r"compilers\.gcc\.fp: missing \['fast'\]"),
        (
            "[compilers.gcc.isa]\n",
            '[compilers.gcc.isa]\navx10 = ["-mavx10.2"]\n',
            r"compilers\.gcc\.isa: missing \[\], unknown \['avx10'\]",
        ),
        (
            'isas = ["sve"]\nrender = "sve"',
            'isas = ["sme"]\nrender = "sve"',
            r"tails\.sve_intrinsics\.isas names undeclared ISAs \['sme'\]",
        ),
    ],
)
def test_a_broken_matrix_is_refused(tmp_path: pathlib.Path, old: str, new: str, refusal: str) -> None:
    with pytest.raises(ValueError, match=refusal):
        configuration_matrix.load(variant(tmp_path, old, new))


def test_a_compiler_not_on_path_is_skipped_with_its_reason(tmp_path: pathlib.Path) -> None:
    matrix = configuration_matrix.load(
        variant(tmp_path, 'c = "gcc"\ncpp = "g++"', 'c = "no-such-cc"\ncpp = "no-such-cxx"')
    )

    usable, skipped = matrix.usable_compilers()

    assert "gcc" not in usable
    assert skipped["gcc"] == "not on PATH: no-such-cc, no-such-cxx"


def test_only_the_isas_the_host_lists_are_offered() -> None:
    zen3_flags = frozenset({"sse2", "avx", "avx2", "fma"})
    grace_flags = frozenset({"fp", "asimd", "sve", "sve2"})

    assert MATRIX.host_isas(zen3_flags) == ("avx2",)
    assert MATRIX.host_isas(grace_flags) == ("neon", "sve")


def test_the_reference_fp_matrix_keeps_only_the_reference_levels_and_no_approximation() -> None:
    ref = configuration_matrix.at_reference_fp(MATRIX)

    assert set(MATRIX.fp_levels) - set(ref.fp_levels)  # the full matrix relaxes further (fast, reassoc)
    assert set(ref.fp_levels) == set(MATRIX.fp_levels) & set(configuration_matrix.REFERENCE_FP_LEVELS)
    assert ref.approximation is False
    assert ref.compilers == MATRIX.compilers
