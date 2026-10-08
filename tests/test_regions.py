# Copyright 2026 ETH Zurich and the Alloy authors.
import pytest
from helpers import MATRIX, REDUCTIONS, outlined

from alloy import regions
from alloy.cli import load_program


def test_the_libm_map_and_the_sum_become_separate_regions():
    sut = outlined()

    assert len(sut.regions) == len(sut.calls) == 3
    assert [r.calls_libm for r in sut.regions].count(True) == 1
    assert [r.has_reduction for r in sut.regions].count(True) == 1


@pytest.mark.parametrize(
    ("kernel", "lengths"),
    [
        ("square_free_matmul", ["K"]),
        ("square_matmul", ["N"]),  # the contracted k, though N also names both kept axes
        ("row_sum", ["1", "N"]),  # zero-initialization, then the sum over each row
        ("scale", ["1"]),
    ],
)
def test_the_accumulation_length_is_the_reduced_extent_of_each_region(kernel, lengths):
    sut = regions.outline(load_program(f"{REDUCTIONS}:{kernel}"), MATRIX.libm_calls)

    assert [str(r.accumulation_length) for r in sut.regions] == lengths
