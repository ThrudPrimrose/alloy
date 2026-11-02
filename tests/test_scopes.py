# Copyright 2026 ETH Zurich and the Alloy authors.
import dace
import pytest
from dace.libraries.standard.nodes import Reduce, external_call
from dace.sdfg import nodes

from alloy.frontend import scopes
from helpers import MATRIX, REDUCTIONS, load_program, outlined


def test_the_libm_map_and_the_sum_become_separate_scopes():
    sut = outlined()

    assert len(sut.scopes) == len(external_call.external_calls(sut.sdfg)) == 3
    assert [r.calls_libm for r in sut.scopes].count(True) == 1
    assert [r.has_reduction for r in sut.scopes].count(True) == 1


@pytest.mark.parametrize(
    ("kernel", "lengths"),
    [
        ("square_free_matmul", ["K"]),
        ("square_matmul", ["N"]),  # the contracted k, though N also names both kept axes
        ("row_sum", ["1", "N"]),  # zero-initialization, then the sum over each row
        ("scale", ["1"]),
    ],
)
def test_the_accumulation_length_is_the_reduced_extent_of_each_scope(kernel, lengths):
    sut = scopes.outline(load_program(f"{REDUCTIONS}:{kernel}").to_sdfg(), MATRIX.libm_calls)

    assert [str(r.accumulation_length) for r in sut.scopes] == lengths


M = dace.symbol("M", dace.int64)
N = dace.symbol("N", dace.int64)


@dace.program
def two_increments(a: dace.float64[M, N], b: dace.float64[M, N], c: dace.float64[M, N], d: dace.float64[M, N]):
    for i in dace.map[0:M]:
        for j in dace.map[0:N]:
            b[i, j] = a[i, j] + 1.0
        for k in dace.map[0:N]:
            d[i, k] = c[i, k] + 1.0


def tasklet_labels(sdfg: dace.SDFG) -> list[str]:
    return [n.label for n, _ in sdfg.all_nodes_recursive() if isinstance(n, nodes.Tasklet)]


def test_tasklets_that_share_a_frontend_label_each_get_their_own_in_a_scope():
    sdfg = two_increments.to_sdfg()
    assert tasklet_labels(sdfg).count("_Add_") == 2

    (sut,) = scopes.outline(sdfg, MATRIX.libm_calls).scopes

    labels = tasklet_labels(sut.sdfg)
    assert len(labels) == len(set(labels))


def test_a_library_node_a_pipeline_chose_stays_whole_as_its_own_scope():
    sdfg = load_program(f"{REDUCTIONS}:row_sum").to_sdfg()
    (chosen,) = [n for n, parent in sdfg.all_nodes_recursive() if isinstance(n, Reduce)]
    chosen.implementation = "CPU"

    sut = scopes.outline(sdfg, MATRIX.libm_calls)

    kept = [r for r in sut.scopes if any(isinstance(n, Reduce) for n, parent in r.sdfg.all_nodes_recursive())]
    assert len(kept) == 1
    assert kept[0].has_reduction
    assert str(kept[0].accumulation_length) == "N"
