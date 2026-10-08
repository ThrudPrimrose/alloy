# Copyright 2026 ETH Zurich and the Alloy authors.
from helpers import MATRIX, gcc_only, outlined, region_with

from alloy.candidates import one_factor_at_a_time


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
