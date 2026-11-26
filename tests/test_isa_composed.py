# Copyright 2026 ETH Zurich and the Alloy authors.
"""The N-element reduction and scan programs an answer hands out (review R12): they run, and a wrong join fails."""

import dataclasses

import pytest

from alloy.isa import composed
from alloy.isa.ask import Feasible, Infeasible, Operand, Request, ask
from alloy.isa.table import Table, load
from helpers import by_isa

TABLE = load()
CASES = [("avx2", 24), ("avx512", 48), ("neon", 12), ("sve", 100), ("rvv", 100)]  # three registers, or a partial pass


def with_intrinsic(isa: str, op: str, intrinsic: str) -> Table:
    """The shipped table with one row's intrinsic changed, as a wrong edit of ``intrinsics.toml`` would."""
    target = TABLE.isas[isa]
    entries = {**target.f32, op: dataclasses.replace(target.f32[op], intrinsic=intrinsic)}
    return dataclasses.replace(TABLE, isas={**TABLE.isas, isa: dataclasses.replace(target, f32=entries)})


@pytest.mark.parametrize(("isa", "n"), by_isa(CASES))
@pytest.mark.parametrize("op", ["reduce_add", "reduce_min", "reduce_max", "scan_add"])
def test_the_program_over_several_registers_equals_the_scalar_operation(isa: str, n: int, op: str) -> None:

    ok, basis = composed.checked(isa, op, "f32", n, TABLE)

    assert ok is True, basis


@pytest.mark.parametrize(
    ("isa", "wrong"), by_isa([("avx2", "_mm256_set1_epi32(6)"), ("neon", "vdupq_laneq_f32(t, 2)")])
)
def test_a_scan_that_carries_the_wrong_lane_fails(isa: str, wrong: str, monkeypatch: pytest.MonkeyPatch) -> None:
    right = composed.LAST_LANE[isa, "f32"]
    carry = right.replace("_mm256_set1_epi32(7)", wrong) if isa == "avx2" else wrong
    monkeypatch.setitem(composed.LAST_LANE, (isa, "f32"), carry)

    ok, _ = composed.checked(isa, "scan_add", "f32", 24 if isa == "avx2" else 12, TABLE)

    assert ok is False


@pytest.mark.parametrize(("isa", "n", "wrong"), by_isa([("avx2", 24, "_mm256_max_ps"), ("sve", 100, "svmax_f32_x")]))
def test_a_reduction_that_combines_its_registers_wrongly_fails(isa: str, n: int, wrong: str) -> None:

    ok, _ = composed.checked(isa, "reduce_add", "f32", n, with_intrinsic(isa, "add", wrong))

    assert ok is False


@pytest.mark.avx2
def test_an_answer_over_three_registers_hands_out_and_runs_the_whole_program() -> None:
    sut = ask(Request("avx2", "scan_add", {"x": Operand("vector", "f32", (24,))}))

    assert isinstance(sut, Feasible) and sut.check.status == "run" and "24-element program" in sut.check.basis
    assert "for (int k = 0; k < 3; k++)" in sut.code and "_mm256_permutevar8x32_ps(t, _mm256_set1_epi32(7))" in sut.code


def test_an_sve_min_reduction_names_the_header_of_its_infinity() -> None:
    sut = ask(Request("sve", "reduce_min", {"x": Operand("vector", "f32", (100,))}), verify=False)

    assert isinstance(sut, Feasible) and "INFINITY" in sut.code
    assert sut.setup["header"].startswith("#include <math.h>")


@pytest.mark.avx2
def test_a_wrong_join_makes_the_answer_infeasible(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(composed.LAST_LANE, ("avx2", "f32"), "_mm256_permutevar8x32_ps(t, _mm256_set1_epi32(0))")

    sut = ask(Request("avx2", "scan_add", {"x": Operand("vector", "f32", (24,))}))

    assert isinstance(sut, Infeasible) and "differs from the scalar reference" in sut.reason


@pytest.mark.rvv
def test_an_rvv_scan_that_carries_the_wrong_element_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    right = composed.rvv_program
    monkeypatch.setattr(composed, "rvv_program", lambda *a: right(*a).replace("vl - 1, vl", "vl - 2, vl"))

    ok, _ = composed.checked("rvv", "scan_add", "f32", 100, TABLE)

    assert ok is False


def test_an_rvv_answer_over_n_elements_is_a_vsetvl_loop_without_a_remainder() -> None:
    sut = ask(Request("rvv", "add", {"a": Operand("vector", "f32", (100,)), "b": Operand("vector", "f32", (100,))}),
              verify=False)  # fmt: skip

    assert isinstance(sut, Feasible)
    assert "size_t vl = __riscv_vsetvl_e32m1((size_t)(100 - i));" in sut.code and "i += (int64_t)vl;" in sut.code
    assert sut.setup["build"].startswith("riscv64-linux-gnu-gcc")
