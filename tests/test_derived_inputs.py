# Copyright 2026 ETH Zurich and the Alloy authors.
"""Inputs without a manifest: the outputs are the arguments the SDFG writes, any value is valid unless a call is
defined on part of the reals or an integer argument may index, and a draw sizes every symbol odd."""

import dace
import numpy as np

from alloy.frontend import inputs

N = dace.symbol("N")


@dace.program
def axpy(x: dace.float64[N], y: dace.float64[N], a: dace.float64):
    for i in dace.map[0:N]:
        y[i] = a * x[i] + y[i]


@dace.program
def roots(x: dace.float64[N], y: dace.float64[N]):
    for i in dace.map[0:N]:
        y[i] = np.sqrt(x[i])


@dace.program
def gather(x: dace.float64[N], idx: dace.int64[N], y: dace.float64[N]):
    for i in dace.map[0:N]:
        y[i] = x[idx[i]]


def test_the_outputs_are_the_arguments_the_program_writes():
    assert inputs.derived_outputs(axpy.to_sdfg()) == ("y",)


def test_any_value_is_valid_unless_a_call_or_an_integer_argument_restricts_it():
    assert inputs.domain_gap(axpy.to_sdfg()) == ""
    assert inputs.domain_gap(roots.to_sdfg()) == "calls sqrt"
    assert inputs.domain_gap(gather.to_sdfg()) == "integer argument idx"


def test_a_draw_sizes_every_symbol_odd_and_fills_every_argument_at_its_dtype():
    sdfg = axpy.to_sdfg()

    sut = [inputs.derived_draw(sdfg, i) for i in range(2)]

    assert [d.sizes for d in sut] == [{"N": 37}, {"N": 61}]
    assert sut[0].values["x"].shape == (37,) and sut[0].values["x"].dtype == np.float64
    assert isinstance(sut[0].values["a"], np.float64)
    assert not np.array_equal(sut[0].values["x"], inputs.derived_draw(sdfg, 2).values["x"]), "seeded per draw"
