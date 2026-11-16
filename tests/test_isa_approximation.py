# Copyright 2026 ETH Zurich and the Alloy authors.
"""The approximation axis: a C scope's libm calls answered by an inline ladder rung, rendered as scalar C."""

import subprocess

import pytest

from alloy.backend.candidates import Candidate, flips
from alloy.isa import approximation
from alloy.isa.mathcheck import judged, measure
from alloy.isa.mathkernels import functions, kernel
from helpers import MATRIX, build, outlined, scope_with


@pytest.mark.parametrize("fn", functions())
@pytest.mark.parametrize("dtype", ["f64", "f32"])
@pytest.mark.parametrize("level", approximation.LEVELS)
def test_every_scalar_rung_holds_the_error_its_vector_kernel_recorded(fn: str, dtype: str, level: str):
    k = kernel(fn, dtype, level)

    seen = measure(k, "scalar", samples=1 << 12)

    assert seen is not None
    assert judged(k, seen, "scalar").ok, (k.name, seen, k.error_ulp)


@pytest.mark.parametrize("finite", [False, True])
def test_a_c_scope_that_calls_libm_tries_every_rung_and_the_proof_prunes_relaxed(finite: bool):
    """Declaring finite inputs no longer opens ``relaxed``: the range proof prunes it (tests/test_heuristics_ranges)."""
    scope = scope_with(outlined(), libm=True, reduction=False)

    sut = [c for c in flips(MATRIX, scope, "c", "gcc", finite_inputs=finite) if c.approx]

    assert tuple(c.approx for c in sut) == approximation.LEVELS
    assert all(c.tolerance(MATRIX) == "band" for c in sut)


@pytest.mark.parametrize(("language", "libm"), [("cpp", True), ("c", False)])
def test_no_rung_is_tried_for_cpp_or_for_a_scope_without_libm_calls(language: str, libm: bool):
    scope = scope_with(outlined(), libm=libm, reduction=not libm)

    sut = flips(MATRIX, scope, language, "gcc", finite_inputs=True)

    assert not [c for c in sut if c.approx]


def test_a_rung_build_calls_its_kernel_and_a_relaxed_one_calls_no_libm(tmp_path):
    scope = scope_with(outlined(), libm=True, reduction=False)

    strict = build(scope, Candidate("c", "gcc", approx="strict"), MATRIX, tmp_path / "s", {})
    relaxed = build(scope, Candidate("c", "gcc", approx="relaxed"), MATRIX, tmp_path / "r", {})

    assert strict.error == "" and relaxed.error == "", (strict.error, relaxed.error)
    assert "#define sin(...) alloy_sin_f64_strict(__VA_ARGS__)" in strict.source.read_text()
    assert strict.name != relaxed.name
    assert strict.candidate.config_name(MATRIX) != relaxed.candidate.config_name(MATRIX)
    undefined = subprocess.run(["nm", "-u", str(relaxed.archive)], capture_output=True, text=True, check=True).stdout
    assert "sin" not in undefined.split(), undefined


def test_only_the_ladder_functions_a_unit_calls_get_a_kernel():
    sut = approximation.prelude("strict", approximation.called_functions("y[i] = sinf(x[i]) + atan2(x[i], 1.0);"))

    assert "alloy_sin_f32_strict" in sut and "alloy_sin_f64_strict" in sut
    assert "atan2" not in sut
