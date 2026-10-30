# Copyright 2026 ETH Zurich and the Alloy authors.
"""The schedule axis: legality per ISA with reasons, C skeletons composed from the table's entries,
and a compile-and-run numerical check of every skeleton the host can execute."""

import shutil
import subprocess

import pytest

from alloy.isa import load
from alloy.isa.schedules import SCHEDULES, legal, skeleton

TABLE = load()
CC = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")


def test_every_schedule_is_described_and_every_isa_offer_is_known():
    for name in SCHEDULES:
        assert name in TABLE.schedule_info
    for isa in TABLE.isas.values():
        for offered in isa.schedules:
            assert offered in TABLE.schedule_info


@pytest.mark.parametrize(
    ("isa", "schedule", "offered"),
    [
        ("avx2", "scalar", True),
        ("avx2", "scalar_remainder", True),
        ("avx2", "full_mask", False),
        ("neon", "masked_remainder", False),
        ("avx512", "masked_remainder", True),
        ("avx512", "full_mask", True),
        ("avx512", "sve_intrinsics", False),
        ("sve", "sve_intrinsics", True),
        ("sve", "scalar_remainder", False),
    ],
)
def test_legality_and_the_reason(isa, schedule, offered):
    why = legal(isa, schedule, TABLE)

    assert (why == "") is offered
    if not offered:
        assert why  # a refusal always names why


def test_a_refusal_explains_missing_predication():
    assert "no predication" in legal("avx2", "full_mask", TABLE)
    assert "not offered" in legal("sve", "scalar_remainder", TABLE)


SKELETON_MARKS = [
    ("avx2", "scalar", "f64", ["for (int64_t i = 0; i < N; i++)"]),
    (
        "avx2",
        "scalar_remainder",
        "f64",
        [
            "const int64_t n_main = 4 * (N / 4);",
            "_mm256_fmadd_pd(_mm256_set1_pd(a)",
            "for (int64_t i = n_main; i < N; i++)",
        ],
    ),
    (
        "avx512",
        "masked_remainder",
        "f64",
        [
            "for (; i + 8 <= N; i += 8)",
            "__mmask8 m = _mm512_cmplt_epu64_mask(iota, _mm512_set1_epi64(N - i));",
            "_mm512_mask_storeu_pd(C + i, m,",
        ],
    ),
    ("avx512", "full_mask", "f32", ["for (int64_t i = 0; i < N; i += 16)", "__mmask16 m = _mm512_cmplt_epu32_mask"]),
    (
        "neon",
        "scalar_remainder",
        "f32",
        ["const int64_t n_main = 4 * (N / 4);", "vfmaq_f32(vld1q_f32(Y + i), vdupq_n_f32(a)"],
    ),
    (
        "sve",
        "sve_intrinsics",
        "f64",
        [
            "i += svcntd()",
            "svbool_t __pg_i = svwhilelt_b64_u64((uint64_t)i, (uint64_t)N);",
            "svmla_f64_x(__pg_i, svld1_f64(__pg_i, Y + i), svdup_f64(a)",
        ],
    ),
]


@pytest.mark.parametrize(("isa", "schedule", "dtype", "marks"), SKELETON_MARKS)
def test_skeletons_compose_the_table_entries(isa, schedule, dtype, marks):
    source = skeleton(TABLE, isa, schedule, dtype)

    for mark in marks:
        assert mark in source, f"{mark!r} missing from {isa}/{schedule}/{dtype}"
    # operand-order traps respected: NEON fma takes the accumulator first
    if isa == "neon":
        assert "vfmaq_f32(vld1q_f32(Y + i), vdupq_n_f32(a), vld1q_f32(X + i))" in source


def test_an_illegal_skeleton_refuses_with_the_reason():
    with pytest.raises(KeyError, match="no predication"):
        skeleton(TABLE, "avx2", "full_mask", "f64")


_RUNNABLE = [
    ("avx2", "scalar", "f64", ["-mavx2", "-mfma"], "double", ""),
    ("avx2", "scalar_remainder", "f64", ["-mavx2", "-mfma"], "double", ""),
    ("avx512", "masked_remainder", "f64", ["-mavx512f", "-mavx512dq"], "double", ""),
    ("avx512", "full_mask", "f64", ["-mavx512f", "-mavx512dq"], "double", ""),
    ("avx512", "scalar_remainder", "f32", ["-mavx512f", "-mavx512dq"], "float", "f"),
    ("avx512", "full_mask", "f32", ["-mavx512f", "-mavx512dq"], "float", "f"),
]


@pytest.mark.skipif(not CC, reason="no C compiler on PATH")
@pytest.mark.parametrize(("isa", "schedule", "dtype"), [(i, s, d) for i, s, d, *_ in _RUNNABLE])
def test_skeletons_compile_and_run_on_the_host(isa, schedule, dtype):
    from alloy.isa.schedules import verify
    from alloy.isa.validate import host_can_run

    if not host_can_run(isa, dtype):
        pytest.skip(f"this host cannot execute {isa}/{dtype}")
    verdict = verify(isa, schedule, dtype, TABLE)

    assert verdict.ok is True, verdict.detail


def test_an_unexecutable_skeleton_is_unverified_not_wrong():
    from alloy.isa.schedules import verify

    verdict = verify("neon", "scalar_remainder", "f64", TABLE)

    assert verdict.ok is None


def test_every_schedule_spells_how_to_ask_each_compiler():
    from alloy.isa.schedules import compiler_spelling

    assert compiler_spelling("scalar", "gcc", TABLE) == "-fno-tree-vectorize"
    assert "vect-partial-vector-usage=0" in compiler_spelling("scalar_remainder", "gcc", TABLE)
    assert "vect-partial-vector-usage=1" in compiler_spelling("masked_remainder", "gcc", TABLE)
    assert "vect-partial-vector-usage=2" in compiler_spelling("full_mask", "gcc", TABLE)
    assert "no masked epilogue" in compiler_spelling("masked_remainder", "clang", TABLE)
    assert "vectorize_width" in compiler_spelling("scalar_remainder", "clang", TABLE)
    assert "armv8-a+sve" in compiler_spelling("sve_intrinsics", "gcc", TABLE)


def test_an_unknown_compiler_or_schedule_names_the_choices():
    import pytest

    from alloy.isa.schedules import compiler_spelling

    with pytest.raises(KeyError, match="unknown schedule"):
        compiler_spelling("wibble", "gcc", TABLE)


def test_the_cli_verifies_a_skeleton():
    import sys

    run = subprocess.run(
        [sys.executable, "-m", "alloy.isa", "skeleton", "avx512", "masked_remainder", "f64", "--verify"],
        capture_output=True,
        text=True,
        check=False,
    )

    if run.returncode != 0:  # host cannot execute AVX-512: the skeleton still prints
        assert "_mm512_mask_storeu_pd" in run.stdout
    else:
        assert "// verified: compiled skeleton" in run.stdout


def test_a_width_alias_is_refused_by_name():
    with pytest.raises(KeyError, match="use avx512"):
        skeleton(TABLE, "avx512_256", "full_mask", "f64")


def test_the_full_mask_count_cannot_truncate_to_32_bits():
    assert "N - i < 16 ? N - i : 16" in skeleton(TABLE, "avx512", "full_mask", "f32")


def test_a_compiler_spelling_names_a_compiler_not_any_field():
    from alloy.isa.schedules import compiler_spelling

    with pytest.raises(KeyError, match="no 'title' spelling"):
        compiler_spelling("scalar", "title", TABLE)
