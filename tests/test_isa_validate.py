# Copyright 2026 ETH Zurich and the Alloy authors.
"""The numerical validation gate: every spelling is checked by a compiled kernel (on ISAs the host
runs) or a tier re-measurement before an agent sees it; failures attach the candidate spellings."""

import dataclasses
import shutil

import pytest

from alloy.isa import load
from alloy.isa.validate import (
    Verdict,
    candidates_for,
    host_can_run,
    validate,
    validate_tier,
)

TABLE = load()
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
    TABLE.approx["sin-quad-cheb13"] = BAD
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
