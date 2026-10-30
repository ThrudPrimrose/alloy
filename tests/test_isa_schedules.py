# Copyright 2026 ETH Zurich and the Alloy authors.
"""The schedule axis: legality per ISA with reasons, C skeletons composed from the table's entries,
and a compile-and-run numerical check of every skeleton the host can execute."""

import pathlib
import shutil
import subprocess
import tempfile

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
@pytest.mark.parametrize(("isa", "schedule", "dtype", "flags", "ctype", "fsuffix"), _RUNNABLE)
def test_skeletons_compile_and_run_on_the_host(isa, schedule, dtype, flags, ctype, fsuffix):
    from alloy.isa.validate import host_can_run

    if not host_can_run(isa, dtype):
        pytest.skip(f"this host cannot execute {isa}/{dtype}")
    source = (
        skeleton(TABLE, isa, schedule, dtype)
        + f"""
#include <stdio.h>
#include <math.h>
int main(void) {{
  int N = 19; {ctype} a = 1.5{fsuffix};
  {ctype} X[19], Y[19], C[19];
  for (int i = 0; i < N; i++) {{ X[i] = ({ctype})(0.5 + 0.1 * i); Y[i] = ({ctype})(1.0 + 0.25 * i); C[i] = 0; }}
  axpy(N, a, X, Y, C);
  double maxrel = 0;
  for (int i = 0; i < N; i++) {{
    double ref = (double)a * (double)X[i] + (double)Y[i];
    double d = fabs((double)C[i] - ref);
    double m = fabs(ref) > 1 ? fabs(ref) : 1;
    if (d / m > maxrel) maxrel = d / m;
  }}
  printf("rel=%.6e\\n", maxrel);
  return 0;
}}"""
    )
    with tempfile.TemporaryDirectory() as tmp:
        c_file = pathlib.Path(tmp) / "s.c"
        exe = pathlib.Path(tmp) / "s"
        c_file.write_text(source)
        build = subprocess.run(
            [CC, "-O1", *flags, str(c_file), "-lm", "-o", str(exe)], capture_output=True, text=True, check=False
        )
        assert build.returncode == 0, build.stderr[-400:]
        run = subprocess.run([str(exe)], capture_output=True, text=True, check=True)
    rel = float(run.stdout.strip().removeprefix("rel="))
    assert rel <= 1e-5, f"{isa}/{schedule}/{dtype} rel err {rel}"  # fma vs mul+add differs by ~1 ulp


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
