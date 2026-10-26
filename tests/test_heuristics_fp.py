# Copyright 2026 ETH Zurich and the Alloy authors.
"""The default FP level: contraction for a scope that reduces, the finite-math level only when the inputs are
declared finite, the level without errno otherwise."""

import pytest

from alloy.heuristics import fp
from helpers import MATRIX, outlined, scope_with


@pytest.mark.parametrize("finite_inputs", [False, True])
def test_a_reducing_scope_keeps_its_summation_order_whether_or_not_the_inputs_are_finite(finite_inputs):
    scope = scope_with(outlined(), libm=False, reduction=True)

    assert fp.default_level(MATRIX, scope, finite_inputs=finite_inputs) == "contract"


def test_a_non_reducing_scope_gets_fast_math_only_with_finite_inputs():
    scope = scope_with(outlined(), libm=True, reduction=False)

    assert fp.default_level(MATRIX, scope, finite_inputs=True) == "fast"
    assert fp.default_level(MATRIX, scope, finite_inputs=False) == "noerrno"
