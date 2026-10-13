# Copyright 2026 ETH Zurich and the Alloy authors.
from alloy.backend.candidates import one_factor_at_a_time
from helpers import MATRIX, gcc_only, outlined, region_with


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


def test_a_level_that_does_not_need_finite_inputs_never_assumes_them():
    finite_only = ("-ffast-math", "-ffinite-math-only", "-fp-model=fast", "-fast")
    open_levels = {name for name, level in MATRIX.fp_levels.items() if level.needs != "finite_inputs"}
    spellings = [
        (compiler, level, flags)
        for compiler, comp in MATRIX.compilers.items()
        for level, flags in comp.fp.items()
        if level in open_levels
    ]
    spellings += [
        (compiler, lib, flags)
        for compiler, comp in MATRIX.compilers.items()
        for lib, flags in comp.veclib.items()
        if MATRIX.veclibs[lib].fp_level in open_levels
    ]

    assert [(c, o) for c, o, flags in spellings if any(f.startswith(finite_only) for f in flags)] == []


def test_gccs_vector_math_is_tried_only_when_inputs_are_declared_finite(tmp_path):
    matrix = gcc_only(tmp_path)
    region = region_with(outlined(), libm=True, reduction=False)

    undeclared = one_factor_at_a_time(matrix, region)
    declared = one_factor_at_a_time(matrix, region, finite_inputs=True)

    assert all(c.veclib == "none" for c in undeclared)
    assert any(c.veclib == "libmvec_fast" for c in declared)


def test_a_narrow_index_is_tried_only_where_every_array_fits_it(tmp_path):
    matrix = gcc_only(tmp_path)
    region = region_with(outlined(), libm=False, reduction=True)

    fits = one_factor_at_a_time(matrix, region, max_elements=2**20)
    overflows = one_factor_at_a_time(matrix, region, max_elements=2**31)

    assert "int32" in {c.resolved(matrix)[0] for c in fits}
    assert {c.resolved(matrix)[0] for c in overflows} == {"int64"}
