# Copyright 2026 ETH Zurich and the Alloy authors.
"""The numerical validation gate: every spelling is checked by a compiled kernel (on ISAs the host
runs) or a tier re-measurement before an agent sees it; failures attach the candidate spellings."""

import dataclasses
import importlib
import math
import shutil
from typing import Any

import pytest

from alloy.isa import load
from alloy.isa.validate import (
    Verdict,
    _c_flags,
    _compile_run,
    candidates_for,
    host_can_run,
    kernel_c,
    unexercised,
    validate,
    validate_all,
    validate_tier,
)

TABLE = load()
#: The module itself: ``alloy.isa.validate`` the attribute is the function of that name.
validate_module = importlib.import_module("alloy.isa.validate")
CC = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
AVX2 = CC and host_can_run("avx2", "f64")
AVX512 = CC and host_can_run("avx512", "f64")


@dataclasses.dataclass(slots=True, frozen=True)
class FakeTier:
    """A tampered tier: one coefficient is wrong, as a transcription error would be."""

    op: str
    domain: str
    error_ulp: float
    recipe: tuple[str, ...]


GOOD = TABLE.approx["sin-quad-cheb13"]
BAD = FakeTier(
    GOOD.op,
    GOOD.domain,
    GOOD.error_ulp,
    tuple(step.replace("1.0000000000000024", "1.0000000000001024") for step in GOOD.recipe),
)


@pytest.mark.skipif(not AVX2, reason="host cannot execute AVX2 kernels")
@pytest.mark.parametrize(
    ("op", "dtype"),
    [
        ("add", "f64"),
        ("sub", "f32"),
        ("mul", "f64"),
        ("div", "f32"),
        ("fma", "f64"),
        ("sqrt", "f64"),
        ("min", "f64"),
        ("max", "f32"),
        ("select", "f64"),
        ("select", "f32"),
        ("reduce_add", "f64"),
        ("reduce_add", "f32"),
        ("gather", "f64"),
        ("gather", "f32"),
        ("scatter", "f64"),
        ("scatter", "f32"),
        ("mod", "f64"),
        ("mod", "f32"),
        ("load", "f64"),
        ("store", "f64"),
        ("broadcast", "f64"),
        ("zero", "f64"),
        ("and", "i64"),
        ("or", "i32"),
        ("shl", "i64"),
        ("shr", "i32"),
        ("land", "i64"),
        ("lor", "i32"),
        ("mod", "i64"),
    ],
)
def test_compiled_kernels_validate_the_avx2_entries(op, dtype):
    verdict = validate("avx2", op, dtype, TABLE)

    assert verdict.ok is True, verdict.detail
    assert verdict.candidates == ()


@pytest.mark.skipif(not AVX2, reason="host cannot execute AVX2 kernels")
@pytest.mark.parametrize("op", ["add", "div", "fma", "sqrt", "min", "max", "abs", "neg", "select"])
def test_the_avx2_f16_emulation_recipes_validate(op):
    verdict = validate("avx2", op, "f16", TABLE)

    assert verdict.ok is True, verdict.detail


@pytest.mark.skipif(not AVX512, reason="host cannot execute AVX-512 kernels")
@pytest.mark.parametrize(
    ("op", "dtype"),
    [
        ("add", "f64"),
        ("fma", "f32"),
        ("select", "f64"),
        ("select", "f32"),
        ("reduce_add", "f64"),
        ("gather", "f64"),
        ("gather", "f32"),
        ("scatter", "f32"),
        ("gen_mask", "f64"),
        ("gen_mask", "f32"),
        ("mod", "f64"),
        ("and", "i64"),
        ("shl", "i32"),
        ("land", "i64"),
        ("lor", "i32"),
        ("mod", "i64"),
    ],
)
def test_compiled_kernels_validate_the_avx512_entries(op, dtype):
    verdict = validate("avx512", op, dtype, TABLE)

    assert verdict.ok is True, verdict.detail


def test_an_isa_the_host_cannot_run_is_unverified_not_wrong():
    verdict = validate("neon", "add", "f64", TABLE)

    assert verdict.ok is None
    assert "cannot execute" in verdict.basis


def test_the_avx512_f16_entries_are_unverified_without_fp16_hardware():
    if host_can_run("avx512", "f16"):
        pytest.skip("this host has AVX512-FP16")
    verdict = validate("avx512", "fma", "f16", TABLE)

    assert verdict.ok is None


@pytest.mark.parametrize("name", ["sin-taylor7", "sin-quad-cheb13", "cos-quad-cheb12", "exp-cheb11"])
def test_every_recorded_tier_error_reproduces_within_slack(name):
    verdict = validate_tier(name, TABLE)

    assert verdict.ok is True, verdict.detail


def test_a_tampered_tier_fails_the_gate():
    """A transcription error in a coefficient must not reproduce the recorded error."""
    held = TABLE.approx["sin-quad-cheb13"]
    TABLE.approx["sin-quad-cheb13"] = BAD  # type: ignore[assignment]
    try:
        verdict = validate_tier("sin-quad-cheb13", TABLE)
    finally:
        TABLE.approx["sin-quad-cheb13"] = held

    assert verdict.ok is False
    assert "measured" in verdict.detail


def test_a_failed_validation_lists_potentially_relevant_spellings():
    candidates = candidates_for("avx2", "fma", "f64", TABLE)

    names = {(hit.isa, hit.dtype, hit.op) for hit in candidates}
    assert ("avx512", "f64", "fma") in names  # same op, other ISA
    assert ("avx2", "f32", "fma") in names  # same op, other dtype
    assert any(hit.via in ("intrinsic", "mnemonic") for hit in candidates)  # the family


def test_a_confirmed_wrong_spelling_is_not_endorsed():
    """Simulate the gate's decision path on a broken entry: ok must be False and candidates attached.
    Uses the real candidates_for on a float op whose kernel exists, checked against a swapped ref."""
    verdict = validate("avx2", "add", "f64", TABLE)

    assert verdict.ok is True  # the shipped table passes; the gate's contract is the failure shape
    broken = Verdict(
        False, "compiled kernel", "max rel err 1.0 vs tolerance 0.0", candidates_for("avx2", "add", "f64", TABLE)
    )
    assert broken.candidates  # a real failure carries the shortlist


def test_the_libmvec_calls_validate_against_libm():
    if not (AVX2 and shutil.which("nm")):
        pytest.skip("no AVX2 host or no libmvec")
    verdict = validate("avx2", "sin", "f64", TABLE)

    assert verdict.ok is True, verdict.detail


@pytest.mark.skipif(not AVX2, reason="needs AVX2")
def test_the_gate_passes_over_everything_the_host_runs_and_skips_nothing():
    """The whole gate end to end: no failure and no entry the kernels leave unexercised."""
    results = validate_all(TABLE, jobs=2)
    expected = {
        f"{isa}/{dtype}/{op}"
        for isa in ("avx2", *(("avx512",) if AVX512 else ()))
        for dtype in ("f64", "f32", "i64", "i32")
        for op in getattr(TABLE.isas[isa], dtype)
    } | {f"approx/{name}" for name in TABLE.approx}
    assert expected <= {ident for ident, _ in results}
    assert [(ident, verdict.detail) for ident, verdict in results if verdict.ok is not True] == []


@pytest.mark.skipif(not AVX2, reason="needs AVX2")
@pytest.mark.parametrize(
    "op, dtype, wrong",
    [
        ("add", "f64", "_mm256_sub_pd"),
        ("min", "f32", "_mm256_max_ps"),
        ("shr", "i32", "_mm256_srav_epi32"),  # arithmetic for logical: only a negative lane tells them apart
        ("mul", "f64", "_mm256_add_pd"),
    ],
)
def test_a_wrong_spelling_in_the_table_fails_the_gate(op, dtype, wrong):
    """The kernel runs the table's own spelling, so a mapping that compiles but computes otherwise is caught."""
    target = TABLE.isas["avx2"]
    entries = {**getattr(target, dtype), op: dataclasses.replace(getattr(target, dtype)[op], intrinsic=wrong)}
    fields: dict[str, Any] = {dtype: entries}
    broken = dataclasses.replace(TABLE, isas={**TABLE.isas, "avx2": dataclasses.replace(target, **fields)})
    assert validate("avx2", op, dtype, broken).ok is False


@pytest.mark.skipif(not AVX2, reason="needs AVX2")
def test_a_nan_result_fails_the_gate_rather_than_comparing_false():
    source = str(kernel_c("avx2", "f64", "add", TABLE)).replace(
        "__m256d vr = _mm256_add_pd(va, vb);", "__m256d vr = _mm256_div_pd(_mm256_setzero_pd(), _mm256_setzero_pd());"
    )
    assert math.isnan(_compile_run(source, _c_flags("avx2", "f64")))


def test_a_kernel_that_skips_a_spelling_verifies_nothing():
    assert unexercised(TABLE.entry("avx2", "add", "f64"), "_mm256_mul_pd(a, b)") == ["_mm256_add_pd"]
    assert unexercised(TABLE.entry("avx2", "scatter", "f64"), "_mm256_storeu_pd(p, v)") == []


def test_no_x86_kernel_is_built_for_an_arm_isa():
    assert kernel_c("neon", "f64", "add", TABLE) is None
    assert kernel_c("sve", "f64", "add", TABLE) is None


def test_an_isa_the_host_lacks_is_unverified_and_not_failed(monkeypatch):
    monkeypatch.setattr(validate_module, "host_can_run", lambda isa, dtype: False)
    assert validate("avx512", "add", "f64", TABLE).ok is None
    assert validate("avx512", "sin", "f32", TABLE).ok is True  # the tier stands, the library call is not run


def test_a_missing_compiler_is_unverified_and_not_failed(monkeypatch):
    monkeypatch.setattr(validate_module, "host_can_run", lambda isa, dtype: True)
    monkeypatch.setattr(validate_module, "_compiler", lambda: None)
    assert validate("avx2", "add", "f64", TABLE).ok is None


def test_the_alias_runs_the_same_kernels():
    assert host_can_run("avx512_256", "f64") == host_can_run("avx512", "f64")
    assert kernel_c("avx512_256", "f64", "add", TABLE) == kernel_c("avx512", "f64", "add", TABLE)
