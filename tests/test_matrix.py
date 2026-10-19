# Copyright 2026 ETH Zurich and the Alloy authors.
import pytest

from alloy import configuration_matrix
from helpers import MATRIX, variant


def test_a_matrix_with_an_unknown_key_is_refused(tmp_path):
    path = variant(tmp_path, "schema = 1\n", "schema = 1\ntypo_key = 1\n")

    with pytest.raises(ValueError, match="typo_key\n  Unexpected keyword argument"):
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


def test_a_compiler_spelling_an_undeclared_isa_is_refused(tmp_path):
    path = variant(tmp_path, "[compilers.gcc.isa]\n", '[compilers.gcc.isa]\navx10 = ["-mavx10.2"]\n')

    with pytest.raises(ValueError, match=r"compilers\.gcc\.isa: missing \[\], unknown \['avx10'\]"):
        configuration_matrix.load(path)


def test_only_the_isas_the_host_lists_are_offered():
    zen3_flags = frozenset({"sse2", "avx", "avx2", "fma"})
    grace_flags = frozenset({"fp", "asimd", "sve", "sve2"})

    assert MATRIX.host_isas(zen3_flags) == ("avx2",)
    assert MATRIX.host_isas(grace_flags) == ("neon", "sve")
