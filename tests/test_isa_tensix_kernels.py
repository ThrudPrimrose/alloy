# Copyright 2026 ETH Zurich and the Alloy authors.
"""A13: the Tensix case study takes a kernel that is elementwise over one-dimensional arrays and calls only operations
with a Tensix row; anything else is refused with its reason."""

import dace
import numpy as np

from alloy.isa import tensix
from alloy.isa.tensix_kernels import fit

N = dace.symbol("N")
ROWS = frozenset(row.op for row in tensix.rows())


@dace.program
def saxpy_exp(x: dace.float32[N], y: dace.float32[N]):
    for i in dace.map[0:N]:
        y[i] = np.exp(x[i]) * 2.0 + y[i]


@dace.program
def shifted(x: dace.float32[N], y: dace.float32[N]):
    for i in dace.map[1:N]:
        y[i] = x[i - 1]


@dace.program
def summed(x: dace.float32[N], s: dace.float32[1]):
    for i in dace.map[0:N]:
        s[0] += x[i]


@dace.program
def arctan(x: dace.float32[N], y: dace.float32[N]):
    for i in dace.map[0:N]:
        y[i] = np.arctan(x[i])


def test_an_elementwise_kernel_of_tensix_operations_fits_and_names_them():
    sut = fit("saxpy_exp", saxpy_exp.to_sdfg(simplify=True), ROWS)

    assert sut.refused == ""
    assert set(sut.ops) == {"exp", "mul", "add"}


def test_a_shifted_access_an_accumulation_and_an_operation_without_a_row_are_refused():
    assert "not indexed by the map's" in fit("shifted", shifted.to_sdfg(simplify=True), ROWS).refused
    assert "accumulation" in fit("summed", summed.to_sdfg(simplify=True), ROWS).refused
    assert "arctan" in fit("arctan", arctan.to_sdfg(simplify=True), ROWS).refused
