# Copyright 2026 ETH Zurich and the Alloy authors.
"""The gate both tile backends share (softhiergen on GVSoC, tensixgen on ttsim): a NumPy program with its inputs and
its NumPy reference, and the check of an output against that reference."""

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass

import dace
import numpy

#: Arrays a program takes, by name (a NumPy scalar for a scalar argument), as softhiergen.program takes them.
Inputs = Mapping[str, numpy.ndarray | numpy.generic]


@dataclass(frozen=True)
class Case:
    name: str
    sdfg: Callable[[], dace.SDFG]
    inputs: Inputs
    #: The arrays the program must leave, by name
    expected: dict[str, numpy.ndarray]
    #: per element, |out - ref| / (|ref| + max |ref|) (:func:`error`); integers and bools exact
    tolerance: float


def error(got: numpy.ndarray, want: numpy.ndarray) -> float:
    """Integers and bools exactly (0 or inf); floats per element, ``|got - want| / (|want| + max |want|)``: an
    allclose whose absolute part is the tolerance times the largest reference value, so a rounding of large operands
    that cancel to a small element (axpy's a x + y near 0) passes, and a wrong element of any size fails."""
    if want.dtype.kind in "biu":
        return 0.0 if numpy.array_equal(got, want) else math.inf
    got, want = got.astype(numpy.float64), want.astype(numpy.float64)
    scale = max(float(numpy.abs(want).max()), 1e-30)
    return float((numpy.abs(got - want) / (numpy.abs(want) + scale)).max())
