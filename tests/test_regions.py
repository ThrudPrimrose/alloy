# Copyright 2026 ETH Zurich and the Alloy authors.
import pytest
from dace.libraries.standard.nodes import Reduce, external_call

from alloy.frontend import regions
from helpers import MATRIX, REDUCTIONS, load_program, outlined


def test_the_libm_map_and_the_sum_become_separate_regions():
    sut = outlined()

    assert len(sut.regions) == len(external_call.external_calls(sut.sdfg)) == 3
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
    sut = regions.outline(load_program(f"{REDUCTIONS}:{kernel}").to_sdfg(), MATRIX.libm_calls)

    assert [str(r.accumulation_length) for r in sut.regions] == lengths


def test_a_library_node_a_pipeline_chose_stays_whole_as_its_own_region():
    sdfg = load_program(f"{REDUCTIONS}:row_sum").to_sdfg()
    (chosen,) = [n for n, parent in sdfg.all_nodes_recursive() if isinstance(n, Reduce)]
    chosen.implementation = "CPU"

    sut = regions.outline(sdfg, MATRIX.libm_calls)

    kept = [r for r in sut.regions if any(isinstance(n, Reduce) for n, parent in r.sdfg.all_nodes_recursive())]
    assert len(kept) == 1
    assert kept[0].has_reduction
    assert str(kept[0].accumulation_length) == "N"
