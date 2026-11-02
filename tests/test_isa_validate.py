# Copyright 2026 ETH Zurich and the Alloy authors.
"""The numerical validation gate: every spelling is checked by a compiled kernel (on ISAs the host
runs) or a tier re-measurement before an agent sees it; failures attach the candidate spellings."""

import dataclasses
import importlib
import json
import math
import shutil
import subprocess
from typing import Any

import pytest

from alloy.isa import load
from alloy.isa.__main__ import main
from alloy.isa.table import Table
from alloy.isa.validate import (
    c_flags,
    candidates_for,
    compile_run,
    evaluate_tier,
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
    tuple(step.replace("p = fma(p, t, 1.0)", "p = fma(p, t, 1.0000000000001024)") for step in GOOD.recipe),
)


@pytest.mark.skipif(not AVX2, reason="host cannot execute AVX2 kernels")
@pytest.mark.parametrize(
    ("op", "dtype"),
    [("mul", "f64"), ("min", "f64"), ("max", "f32"), ("mod", "f64"), ("mod", "f32"), ("load", "f64")],
)
def test_a_float_row_of_an_op_with_integer_gaps_validates(op, dtype):
    """The whole-gate test lets these ops stay unchecked, for their integer rows; their float rows must run."""
    verdict = validate("avx2", op, dtype, TABLE)

    assert verdict.ok is True, verdict.detail
    assert verdict.candidates == ()


@pytest.mark.skipif(not AVX2, reason="host cannot execute AVX2 kernels")
@pytest.mark.parametrize("op", ["add", "div", "fma", "sqrt", "min", "max", "abs", "neg", "select"])
def test_the_avx2_f16_emulation_recipes_validate(op):
    verdict = validate("avx2", op, "f16", TABLE)

    assert verdict.ok is True, verdict.detail


@pytest.mark.skipif(not AVX512, reason="host cannot execute AVX-512 kernels")
def test_the_avx512_fmod_recipe_validates():
    verdict = validate("avx512", "mod", "f64", TABLE)

    assert verdict.ok is True, verdict.detail


@pytest.mark.parametrize("dtype", ["f64", "f32", "i64", "i32"])
def test_every_avx512_kernel_builds_whatever_the_host_can_run(dtype, tmp_path):
    """Every runner checks the spellings and their operand types; only an AVX-512 runner gets to execute them."""
    assert CC, "the gate needs a C compiler"
    kernels = {op: kernel_c("avx512", dtype, op, TABLE) for op in TABLE.isas["avx512"].entries(dtype)}
    sources = {op: source for op, source in kernels.items() if source is not None}
    assert {"add", "load", "store"} <= sources.keys()

    for op, source in sources.items():
        unit = tmp_path / f"{op}.c"
        unit.write_text(source)
        sut = subprocess.run(
            [CC, *c_flags("avx512", dtype), "-c", str(unit), "-o", str(unit.with_suffix(".o"))],
            capture_output=True,
            text=True,
            check=False,
        )
        assert sut.returncode == 0, f"{op}: {sut.stderr}"


def test_an_isa_the_host_cannot_run_is_unverified_not_wrong(monkeypatch):
    monkeypatch.setattr(validate_module, "emulated", lambda isa: None)

    verdict = validate("neon", "add", "f64", TABLE)

    assert verdict.ok is None
    assert "cannot execute" in verdict.basis


def test_the_avx512_f16_entries_are_unverified_without_fp16_hardware():
    if host_can_run("avx512", "f16"):
        pytest.skip("this host has AVX512-FP16")
    verdict = validate("avx512", "fma", "f16", TABLE)

    assert verdict.ok is None


def test_an_avx2_f16_recipe_composes_with_the_rows_full_width_load():
    """A half-width ``code`` would not take what the f16 ``load`` row returns."""
    sut = str(kernel_c("avx2", "f16", "add", TABLE))

    assert "_mm256_castsi256_si128(va)" in sut
    assert "_mm256_extracti128_si256(vb, 1)" in sut


@pytest.mark.parametrize("name", ["sin-taylor7", "sin-quad-cheb13", "cos-quad-cheb12", "exp-cheb11"])
def test_every_recorded_tier_error_reproduces_within_slack(name):
    verdict = validate_tier(name, TABLE)

    assert verdict.ok is True, verdict.detail


@pytest.mark.parametrize(
    "name, bound",
    [("sin-quad-cheb13", 3e-16), ("cos-quad-cheb12", 3e-16), ("exp-cheb11", 5e-16), ("exp-cheb9", 2e-14)],
)
def test_a_chebyshev_tier_reaches_what_its_degree_allows(name, bound):
    """A degree n interpolant errs by about h^(n+1) / (n+1)! / 2^n on half-width h, plus Horner's rounding: the old
    coefficients sat 3 to 90 times above that."""
    assert TABLE.approx[name].error_abs < bound


@pytest.mark.parametrize(
    "step",
    [
        "s = x.__class__",
        "s = ().__class__.__bases__",
        "s = x.tofile('/dev/null')",
        "s = [p for p in x]",
        "s = (lambda: 0)()",
    ],
)
def test_a_tier_step_cannot_reach_past_the_table_s_names(step):
    """A blank ``__builtins__`` alone does not stop an attribute walk."""
    with pytest.raises(ValueError, match="only calls on names"):
        evaluate_tier(FakeTier(GOOD.op, GOOD.domain, GOOD.error_ulp, (step,)))


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
        for op in TABLE.isas[isa].entries(dtype)
    } | {f"approx/{name}" for name in TABLE.approx}
    assert expected <= {ident for ident, _ in results}
    assert [(ident, verdict.detail) for ident, verdict in results if verdict.ok is False] == []
    unchecked = {ident.split("/")[-1] for ident, verdict in results if verdict.ok is None and ident in expected}
    assert unchecked <= {"lt", "mod", "mul", "min", "max", "load"}, unchecked  # the rows with no kernel yet


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
    entries = {**target.entries(dtype), op: dataclasses.replace(target.entries(dtype)[op], intrinsic=wrong)}
    fields: dict[str, Any] = {dtype: entries}
    broken = dataclasses.replace(TABLE, isas={**TABLE.isas, "avx2": dataclasses.replace(target, **fields)})

    sut = validate("avx2", op, dtype, broken)

    assert sut.ok is False
    assert sut.candidates


def with_row(isa: str, dtype: str, op: str, **fields: str) -> Table:
    """The shipped table with one row changed, as a wrong edit of ``intrinsics.toml`` would."""
    target = TABLE.isas[isa]
    entries = {**getattr(target, dtype), op: dataclasses.replace(getattr(target, dtype)[op], **fields)}
    changed: dict[str, Any] = {dtype: entries}
    return dataclasses.replace(TABLE, isas={**TABLE.isas, isa: dataclasses.replace(target, **changed)})


@pytest.mark.skipif(not AVX2, reason="needs AVX2")
@pytest.mark.parametrize(
    "op, dtype, aligned",
    [
        ("load", "f64", "_mm256_load_pd"),
        ("load", "f32", "_mm256_load_ps"),
        ("load", "i64", "_mm256_load_si256"),
        ("load", "f16", "_mm256_load_si256"),
        ("store", "f64", "_mm256_store_pd"),
        ("store", "f32", "_mm256_store_ps"),
        ("store", "i32", "_mm256_store_si256"),
        ("store", "f16", "_mm256_store_si256"),
    ],
)
def test_an_aligned_spelling_of_an_unaligned_row_fails_on_any_stack(op, dtype, aligned):
    """Kernel buffers sit one element past a 64-byte boundary, so an aligned access always faults."""
    sut = validate("avx2", op, dtype, with_row("avx2", dtype, op, intrinsic=aligned))

    assert sut.ok is False, sut.basis


@pytest.mark.skipif(not AVX512, reason="host cannot execute AVX-512 kernels")
@pytest.mark.parametrize(
    "op, dtype, aligned",
    [("load", "f64", "_mm512_load_pd"), ("store", "f32", "_mm512_store_ps"), ("store", "i64", "_mm512_store_si512")],
)
def test_an_aligned_avx512_spelling_of_an_unaligned_row_fails(op, dtype, aligned):
    sut = validate("avx512", op, dtype, with_row("avx512", dtype, op, intrinsic=aligned))

    assert sut.ok is False, sut.basis


@pytest.mark.skipif(not AVX2, reason="needs AVX2")
@pytest.mark.parametrize(
    "op, dtype, swapped",
    [
        ("sub", "f64", "(b, a) -> v"),
        ("div", "f32", "(b, a) -> v"),
        ("shl", "i64", "(counts, a) -> v"),
        ("fma", "f64", "(c, a, b) -> v"),  # the NEON trap: accumulator first
        ("fma", "f32", "(a, c, b) -> v"),
        ("select", "f64", "(b, a, mask) -> v"),
        ("select", "f32", "(b, a, mask) -> v"),
        ("gather", "f64", "(idx, base, scale) -> v"),
    ],
)
def test_a_signature_in_the_wrong_order_fails_the_gate(op, dtype, swapped):
    """The kernel calls the row's intrinsic in the order its signature states, not one written beside it."""
    sut = validate("avx2", op, dtype, with_row("avx2", dtype, op, signature=swapped))

    assert sut.ok is False, sut.basis


@pytest.mark.skipif(not AVX512, reason="host cannot execute AVX-512 kernels")
@pytest.mark.parametrize(
    "op, dtype, swapped",
    [
        ("select", "f64", "(k, b, a) -> v"),
        ("gather", "f32", "(base, idx, scale) -> v"),
        ("scatter", "f64", "(idx, base, v, scale) -> void"),
    ],
)
def test_an_avx512_signature_in_the_wrong_order_fails_the_gate(op, dtype, swapped):
    sut = validate("avx512", op, dtype, with_row("avx512", dtype, op, signature=swapped))

    assert sut.ok is False, sut.basis


@pytest.mark.skipif(not AVX2, reason="needs AVX2")
@pytest.mark.parametrize("dtype", ["f64", "f32", "i64", "i32"])
def test_an_avx2_compare_spells_less_than_in_the_order_of_its_signature(dtype):
    """The float rows hid their predicate in a note, the integer rows passed (a, b) to a greater-than."""
    sut = validate("avx2", "lt", dtype, TABLE)

    assert sut.ok is True, sut.detail


@pytest.mark.skipif(not AVX512, reason="host cannot execute AVX-512 kernels")
@pytest.mark.parametrize("dtype", ["f64", "f32", "i64", "i32"])
def test_an_avx512_compare_spells_less_than_in_the_order_of_its_signature(dtype):
    sut = validate("avx512", "lt", dtype, TABLE)

    assert sut.ok is True, sut.detail


@pytest.mark.skipif(not AVX2, reason="needs AVX2")
@pytest.mark.parametrize(
    "op, dtype, code",
    [
        ("mod", "f64", ("__m256d q = _mm256_round_pd(_mm256_div_pd(b, a), 3)", "_mm256_fnmadd_pd(q, b, a)")),
        ("mod", "f32", ("__m256 q = _mm256_round_ps(_mm256_div_ps(a, b), 3)", "_mm256_fnmadd_ps(q, a, b)")),
        ("min", "i64", ("_mm256_blendv_epi8(b, a, _mm256_cmpgt_epi64(a, b))",)),
        ("max", "i64", ("_mm256_blendv_epi8(a, b, _mm256_cmpgt_epi64(a, b))",)),
        ("select", "f16", ("_mm256_or_si256(_mm256_and_si256(f, mask), _mm256_andnot_si256(mask, t))",)),
        (
            "mul",
            "i64",
            (
                "__m256i cross = _mm256_mullo_epi32(a, b)",  # the halves of b must cross
                "__m256i high = _mm256_slli_epi64(_mm256_add_epi64(cross, _mm256_srli_epi64(cross, 32)), 32)",
                "_mm256_add_epi64(_mm256_mul_epu32(a, b), high)",
            ),
        ),
    ],
)
def test_a_recipe_written_in_the_wrong_order_fails_the_gate(op, dtype, code):
    """The kernel runs the row's ``code``, the text a reader copies, so its order is what is checked."""
    sut = validate("avx2", op, dtype, with_row("avx2", dtype, op, code=code))

    assert sut.ok is False, sut.basis


@pytest.mark.skipif(not AVX2, reason="needs AVX2")
@pytest.mark.parametrize(
    "op, dtype", [("mul", "i64"), ("min", "i64"), ("max", "i64"), ("mod", "i64"), ("mod", "i32"), ("land", "i32")]
)
def test_a_recipe_with_no_hand_written_kernel_runs_all_the_same(op, dtype):
    """These rows had no kernel, so they stayed unverified: their ``code`` is the kernel now."""
    sut = validate("avx2", op, dtype, TABLE)

    assert sut.ok is True, sut.detail


def test_a_kernel_runs_the_recipe_as_the_table_writes_it():
    sut = str(kernel_c("avx2", "f64", "mod", TABLE))

    assert "_mm256_fnmadd_pd(q, vb, va);" in sut


@pytest.mark.skipif(not AVX2, reason="needs AVX2")
def test_a_signature_naming_an_operand_the_op_does_not_have_fails_the_gate():
    sut = validate("avx2", "add", "f64", with_row("avx2", "f64", "add", signature="(x, y) -> v"))

    assert sut.ok is False


def test_the_fma_kernel_tells_all_three_operands_apart():
    sut = str(kernel_c("avx2", "f64", "fma", TABLE))

    assert "_mm256_fmadd_pd(va, vb, vc)" in sut
    assert "ref[j] = fma(a[j], b[j], c[j])" in sut


@pytest.mark.skipif(not AVX2, reason="needs AVX2")
def test_a_nan_result_fails_the_gate_rather_than_comparing_false():
    source = str(kernel_c("avx2", "f64", "add", TABLE)).replace(
        "__m256d vr = _mm256_add_pd(va, vb);", "__m256d vr = _mm256_div_pd(_mm256_setzero_pd(), _mm256_setzero_pd());"
    )
    assert math.isnan(compile_run(source, c_flags("avx2", "f64")))


def test_a_kernel_that_skips_a_spelling_verifies_nothing():
    assert unexercised(TABLE.entry("avx2", "add", "f64"), "_mm256_mul_pd(a, b)") == ["_mm256_add_pd"]
    assert unexercised(TABLE.entry("avx2", "scatter", "f64"), "_mm256_storeu_pd(p, v)") == []


def test_no_x86_kernel_is_built_for_an_arm_isa():
    assert "#include <arm_neon.h>" in str(kernel_c("neon", "f64", "add", TABLE))
    assert "#include <arm_sve.h>" in str(kernel_c("sve", "f64", "add", TABLE))
    assert "immintrin" not in str(kernel_c("neon", "f64", "add", TABLE))


@pytest.mark.parametrize("isa", ["neon", "sve"])
@pytest.mark.parametrize("dtype", ["f64", "f32", "f16", "i64", "i32"])
def test_every_arm_row_holds_under_qemu_or_at_least_compiles(isa, dtype):
    """A cross compile catches a wrong name or operand type; only a run under qemu earns a verified row."""
    verdicts = {op: validate(isa, op, dtype, TABLE) for op in TABLE.isas[isa].entries(dtype)}

    assert {op: verdict.detail for op, verdict in verdicts.items() if verdict.ok is False} == {}


def test_an_arm_row_that_only_compiled_is_not_verified(monkeypatch):
    monkeypatch.setattr(validate_module, "emulated", lambda isa: None)

    sut = validate("sve", "add", "f64", TABLE)

    assert sut.ok is None


@pytest.mark.skipif(shutil.which("aarch64-linux-gnu-gcc") is None, reason="needs the aarch64 cross compiler")
@pytest.mark.parametrize(
    "isa, dtype, op, wrong",
    [
        ("neon", "i64", "and", "vandq_u64"),  # the row's lanes load as int64x2_t
        ("sve", "i32", "or", "svorr_u32_x"),
        ("neon", "f64", "add", "vadd_not_an_intrinsic"),
    ],
)
def test_a_row_that_does_not_compile_for_its_target_is_wrong(monkeypatch, isa, dtype, op, wrong):
    monkeypatch.setattr(validate_module, "emulated", lambda isa: None)

    sut = validate(isa, op, dtype, with_row(isa, dtype, op, intrinsic=wrong))

    assert sut.ok is False, sut.basis


@pytest.mark.skipif(validate_module.emulated("sve") is None, reason="needs qemu-aarch64 and the cross compiler")
@pytest.mark.parametrize(
    "isa, dtype, op, fields",
    [
        ("neon", "f64", "fma", {"signature": "(c, a, b) -> v"}),
        ("sve", "f64", "fma", {"signature": "(pg, m1, m2, add) -> v"}),
        ("neon", "f32", "select", {"signature": "(mask, f, t) -> v"}),
        ("sve", "f32", "select", {"signature": "(pg, f, t) -> v"}),
        ("sve", "f64", "add", {"intrinsic": "svsub_f64_x"}),
        (
            "sve",
            "f32",
            "mod",
            {"code": ("svfloat32_t q = svrintz_f32_x(pg, svdiv_f32_x(pg, a, b))", "svmls_f32_x(pg, b, q, a)")},
        ),
    ],
)
def test_a_wrong_arm_row_fails_under_qemu(isa, dtype, op, fields):
    sut = validate(isa, op, dtype, with_row(isa, dtype, op, **fields))

    assert sut.ok is False, sut.basis


@pytest.mark.skipif(validate_module.emulated("neon") is None, reason="needs qemu-aarch64 and the cross compiler")
@pytest.mark.parametrize("isa", ["neon", "sve"])
@pytest.mark.parametrize("op", ["sin", "cos", "exp"])
def test_the_arm_libmvec_calls_validate_under_qemu(isa, op):
    sut = validate(isa, op, "f64", TABLE)

    assert sut.ok is True, sut.basis
    assert "qemu" in sut.basis


def test_an_isa_the_host_lacks_is_unverified_and_not_failed(monkeypatch):
    monkeypatch.setattr(validate_module, "host_can_run", lambda isa, dtype: False)
    assert validate("avx512", "add", "f64", TABLE).ok is None
    assert validate("avx512", "sin", "f32", TABLE).ok is None  # the tier stands, the library call did not run


def test_a_missing_compiler_is_unverified_and_not_failed(monkeypatch):
    monkeypatch.setattr(validate_module, "host_can_run", lambda isa, dtype: True)
    monkeypatch.setattr(validate_module, "c_compiler", lambda: None)
    assert validate("avx2", "add", "f64", TABLE).ok is None


def test_the_alias_runs_the_same_kernels():
    assert host_can_run("avx512_256", "f64") == host_can_run("avx512", "f64")
    assert kernel_c("avx512_256", "f64", "add", TABLE) == kernel_c("avx512", "f64", "add", TABLE)


def test_a_lookup_prints_a_recipes_operand_order(capsys):
    assert main(["lookup", "avx2", "mod", "f64", "--no-verify"]) == 0

    sut = capsys.readouterr().out
    assert "operands:  (a, b) -> v" in sut
    assert "_mm256_fnmadd_pd(q, b, a)" in sut


def test_a_lookup_as_json_carries_a_recipes_code(capsys):
    assert main(["lookup", "neon", "mod", "f64", "--no-verify", "--json"]) == 0

    sut = json.loads(capsys.readouterr().out)
    assert sut["code"] == ["float64x2_t q = vrndq_f64(vdivq_f64(a, b))", "vfmsq_f64(a, q, b)"]
    assert sut["signature"] == "(a, b) -> v"
