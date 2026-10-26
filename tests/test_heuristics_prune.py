# Copyright 2026 ETH Zurich and the Alloy authors.
"""Sweep pruning: a scope's static facts and each compiler's default build rule out the cells that cannot change
the code (vector cells when nothing vectorizes, tails when the vector length divides every trip count, FP levels
with nothing to rewrite), and the sweep reports every pruned cell with its reason."""

import pathlib

import dace
import numpy as np
import pytest

from alloy.backend import sweep
from alloy.backend.build import Build, Remarks
from alloy.backend.candidates import Candidate, flips
from alloy.frontend import scopes
from alloy.heuristics import prune
from helpers import MATRIX, gcc_only

N = dace.symbol("N")
HOST_ISAS = ("avx2", "avx512_256", "avx512", "sve")


@dace.program
def axpy(x: dace.float64[N], y: dace.float64[N], a: dace.float64):
    for i in dace.map[0:N]:
        y[i] = a * x[i] + y[i]


@dace.program
def scale64(x: dace.float64[64], y: dace.float64[64], a: dace.float64):
    for i in dace.map[0:64]:
        y[i] = a * x[i]


@dace.program
def roots(x: dace.float64[N], y: dace.float64[N]):
    for i in dace.map[0:N]:
        y[i] = np.sqrt(x[i]) / x[i]


def only_scope(program: dace.program) -> scopes.Scope:
    (scope,) = scopes.outline(program.to_sdfg(), MATRIX.libm_calls).scopes
    return scope


def native(compiler: str, vectorized: int) -> Build:
    c = Candidate("c", compiler)
    remarks = Remarks(vectorized, ())
    return Build(c, c.name(MATRIX), {}, pathlib.Path("v0.c"), pathlib.Path("lib.a"), (), "0f", remarks)


def pruned_reasons(
    scope: scopes.Scope, *, vectorized: int, finite_inputs: bool = False, host: tuple[str, ...] = HOST_ISAS
) -> dict[str, str]:
    candidates = flips(MATRIX, scope, "c", "gcc", finite_inputs=finite_inputs, max_elements=None, isas=host)
    _, pruned = prune.prune(candidates, MATRIX, prune.facts(scope), [native("gcc", vectorized)], host)
    return {p.candidate.note: p.reason for p in pruned}


def test_a_multiply_feeding_an_add_is_contractible_and_a_lone_multiply_is_not():
    assert prune.facts(only_scope(axpy)).contracts
    assert not prune.facts(only_scope(scale64)).contracts


def test_sqrt_sets_errno_and_a_division_is_a_fast_math_approximation():
    sut = prune.facts(only_scope(roots))

    assert sut.sets_errno and sut.approximates
    assert not sut.reduces


def test_a_constant_innermost_extent_is_a_known_trip_count_and_a_symbolic_one_is_not():
    assert prune.facts(only_scope(scale64)).trip_counts == (64,)
    assert prune.facts(only_scope(axpy)).trip_counts == (None,)


def test_when_no_compiler_vectorizes_every_vector_cell_but_explicit_sve_loops_is_pruned():
    sut = pruned_reasons(only_scope(axpy), vectorized=0)

    assert sut["isa avx512"] == "nothing vectorizes"
    assert sut["tail full_mask on avx512"] == "nothing vectorizes"
    assert "tail sve_intrinsics on sve" not in sut


def test_tails_are_pruned_only_where_the_vector_length_divides_every_trip_count():
    exact = pruned_reasons(only_scope(scale64), vectorized=1)
    exact_x86 = pruned_reasons(only_scope(scale64), vectorized=1, host=("avx2", "avx512_256", "avx512"))
    symbolic = pruned_reasons(only_scope(axpy), vectorized=1)

    assert exact["tail full_mask on avx512"] == "every trip count divides the vector length"
    assert "tail full_mask on sve" not in exact, "SVE's length is not known at compile time"
    assert "tail scalar_remainder" not in exact, "a tail of any ISA stays while one ISA's length is unknown"
    assert exact_x86["tail scalar_remainder"] == "every trip count divides the vector length"
    assert not any(note.startswith("tail") for note in symbolic)


def test_fp_levels_are_pruned_where_they_have_nothing_to_rewrite():
    lone_multiply = pruned_reasons(only_scope(scale64), vectorized=1, finite_inputs=True)
    multiply_add = pruned_reasons(only_scope(axpy), vectorized=1, finite_inputs=True)

    assert lone_multiply["fp contract"] == "no multiply feeds an add"
    assert lone_multiply["fp noerrno"] == "no libm or sqrt call"
    assert lone_multiply["fp fast"] == "nothing fast-math rewrites"
    assert "fp contract" not in multiply_add and "fp fast" not in multiply_add


def test_a_compilers_default_build_is_never_pruned():
    candidates = flips(MATRIX, only_scope(axpy), "c", "gcc", finite_inputs=False, max_elements=None, isas=HOST_ISAS)

    keep, _ = prune.prune(candidates, MATRIX, prune.facts(only_scope(axpy)), [native("gcc", 0)], HOST_ISAS)

    assert keep[0] == Candidate("c", "gcc")


@pytest.mark.gcc
def test_the_sweep_builds_the_defaults_first_and_skips_the_pruned_cells(tmp_path):
    matrix = gcc_only(tmp_path)
    program = scopes.outline(scale64.to_sdfg(), matrix.libm_calls)

    (sut,) = sweep.run(program, matrix, tmp_path / "out")

    built = {b.name for b in sut.builds}
    assert sut.builds[0].candidate == Candidate("c", "gcc")
    assert sut.pruned, "a lone multiply prunes at least the contract level"
    assert not built & {p.candidate.name(matrix) for p in sut.pruned}
