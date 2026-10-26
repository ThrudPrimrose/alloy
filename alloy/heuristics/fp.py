# Copyright 2026 ETH Zurich and the Alloy authors.
"""The FP level a scope gets by default, when nothing is timed to choose one."""

from alloy.configuration_matrix import Matrix
from alloy.frontend.scopes import Scope

__all__ = ["default_level"]

#: Contraction only: a reduction or scan keeps its summation order, so it stays inside the reference band.
REDUCING = "contract"
#: Every rewrite but the finite-math ones; -ffast-math also assumes no NaN or Inf (folding NaN checks and
#: fmax/fmin), so it needs the caller's declaration even in a scope without a reduction or a libm call.
NON_FINITE = "noerrno"
FINITE = "fast"


def default_level(matrix: Matrix, scope: Scope, *, finite_inputs: bool) -> str:
    """``contract`` for a scope that reduces or scans, else ``fast`` when no input is NaN or Inf, else ``noerrno``."""
    level = REDUCING if scope.has_reduction else FINITE if finite_inputs else NON_FINITE
    if level not in matrix.fp_levels:
        raise ValueError(f"{matrix.path}: the FP default {level!r} is not a declared FP level")
    return level
