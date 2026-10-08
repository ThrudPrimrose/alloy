# Copyright 2026 ETH Zurich and the Alloy authors.
import pytest
from helpers import variant

from alloy import configuration_matrix


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
