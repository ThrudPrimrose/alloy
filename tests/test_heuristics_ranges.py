# Copyright 2026 ETH Zurich and the Alloy authors.
"""A2: a rung above ``strict`` is built only where the declared input ranges prove each libm call's contract."""

import dace
import numpy as np
import pytest

from alloy.backend.candidates import Candidate
from alloy.frontend import scopes
from alloy.heuristics import prune, ranges
from alloy.heuristics.ranges import Interval
from alloy.isa import mathkernels
from helpers import MATRIX

N = dace.symbol("N")


@dace.program
def logs(a: dace.float64[N], out: dace.float64[N]) -> None:
    for i in dace.map[0:N]:
        out[i] = np.log(a[i])


@dace.program
def exp_of_difference(a: dace.float64[N], b: dace.float64[N], out: dace.float64[N]) -> None:
    for i in dace.map[0:N]:
        out[i] = np.exp(a[i] - b[i])


@dace.program
def exp_in_place(a: dace.float64[N]) -> None:
    for i in dace.map[0:N]:
        a[i] = np.exp(a[i])


def gap(program: dace.program, declared: dict[str, Interval]) -> str:  # pyright: ignore[reportGeneralTypeIssues] -- test double
    (scope,) = scopes.outline(program.to_sdfg(), MATRIX.libm_calls).scopes
    return dict(prune.facts(scope, declared).rung_gaps)["relaxed"]


def test_log_of_an_input_declared_in_one_to_two_takes_the_rung_and_one_reaching_zero_does_not() -> None:
    assert gap(logs, {"a": Interval(1.0, 2.0)}) == ""
    why = gap(logs, {"a": Interval(0.0, 2.0)})
    assert why.startswith("argument of log in ") and "spans [0, 2], outside relaxed (finite, positive, normal)" in why


def test_exp_of_a_difference_takes_the_rung_when_the_difference_of_the_ranges_is_in_the_contract() -> None:
    assert gap(exp_of_difference, {"a": Interval(-10.0, 10.0), "b": Interval(0.0, 5.0)}) == ""
    assert "spans [-1000, 1000]" in gap(exp_of_difference, {"a": Interval(0.0, 1000.0), "b": Interval(0.0, 1000.0)})


def test_an_undeclared_input_leaves_the_argument_unproven() -> None:
    assert "has no proven range" in gap(exp_of_difference, {"a": Interval(-1.0, 1.0)})


def test_a_call_on_an_array_the_scope_writes_is_unproven_whatever_its_declaration() -> None:
    assert "has no proven range" in gap(exp_in_place, {"a": Interval(-1.0, 1.0)})


def test_a_scope_with_only_finite_inputs_declared_builds_strict_and_never_relaxed() -> None:
    (scope,) = scopes.outline(logs.to_sdfg(), MATRIX.libm_calls).scopes
    relaxed, strict = Candidate("c", "gcc", approx="relaxed"), Candidate("c", "gcc", approx="strict")

    keep, pruned = prune.prune([strict, relaxed], MATRIX, prune.facts(scope), [], ())

    assert keep == [strict]
    assert [(p.candidate, p.reason.split(" in ")[0]) for p in pruned] == [(relaxed, "argument of log")]


def test_every_relaxed_contract_reads_as_a_range_or_as_a_two_argument_contract() -> None:
    """The proof reads the contract text the documentation prints, so the two cannot differ."""
    for (fn, dtype, level), k in mathkernels.load_kernels().items():
        if level == "relaxed":
            sut = ranges.contract(k.contract, dtype)
            assert (sut is None) == (len(k.args) == 2), (fn, dtype, k.contract)


@pytest.mark.parametrize(
    ("domain", "expected"),
    [("positive", ranges.SIGNS["positive"]), ([0.5, -1.5], Interval(-1.5, 0.5)), ("any", None), (None, None)],
)
def test_a_manifest_domain_becomes_a_declared_range(domain: object, expected: Interval | None) -> None:
    assert ranges.declared({"x": domain}).get("x") == expected
