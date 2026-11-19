# Copyright 2026 ETH Zurich and the Alloy authors.
import json
import pathlib
import re
import types
from typing import Any

import dace
import numpy as np
import pytest

from alloy.frontend import cnumpy


def binding(kernel: str, *args: tuple[str, str, list[str]]) -> dict[str, Any]:
    return {"kernel": kernel, "args": [{"name": n, "kind": k, "shape": s} for n, k, s in args]}


def lifted(source: str, bound: dict[str, Any]) -> tuple[str, types.FunctionType]:
    """The NumPy module of ``source`` and its kernel, ready to call."""
    module = cnumpy.translate(source, bound)
    namespace: dict[str, Any] = {}
    exec(compile(module, "<lifted>", "exec"), namespace)
    return module, namespace["kernel"]


def test_a_flat_index_with_offsets_delinearizes_against_the_shape():
    source = """
    void k(double *restrict aa, const double *restrict bb, const int64_t N) {
      for (int64_t i = 1; i < N; ++i)
        for (int64_t j = 1; j < N; ++j)
          aa[(i)*(N) + (j)] = aa[((i - 1))*(N) + ((j - 1))] + bb[(i)*(N) + (j)];
    }"""
    bound = binding("k", ("aa", "ptr_double", ["N", "N"]), ("bb", "ptr_double", ["N", "N"]), ("N", "int64", []))
    module, kernel = lifted(source, bound)
    aa, bb = np.random.default_rng(0).random((2, 5, 5))
    expected = aa.copy()
    for i in range(1, 5):
        for j in range(1, 5):
            expected[i, j] = expected[i - 1, j - 1] + bb[i, j]

    kernel(aa, bb, 5)

    assert "aa[i - 1, j - 1]" in module
    np.testing.assert_array_equal(aa, expected)


def test_integer_division_truncates_as_c_does_unless_both_sides_are_non_negative():
    source = """
    void k(int64_t *restrict out, const int64_t a, const int64_t N) {
      for (int64_t i = 0; i < N; ++i) out[i] = (a / 2) + (i / 2) + (a % 3);
    }"""
    bound = binding("k", ("out", "ptr_int64", ["N"]), ("a", "int64", []), ("N", "int64", []))
    module, kernel = lifted(source, bound)
    out = np.zeros(4, dtype=np.int64)

    kernel(out, -7, 4)

    assert "c_div(a, 2)" in module and "i // 2" in module
    np.testing.assert_array_equal(out, [-3 + i // 2 - 1 for i in range(4)])


def test_a_null_pointer_then_malloc_becomes_np_empty_and_the_nests_become_array_statements():
    source = """
    void k(const double *restrict x, double *restrict y, const int64_t N) {
      double *t = NULL;
      free(t);
      t = (double *)malloc((size_t)((N)) * sizeof(double));
      __npb_alloc_check(t, (size_t)((N)) * sizeof(double), "t");
      for (int64_t i = 0; i < N; ++i) { t[i] = x[i] * 2.0; }
      for (int64_t i = 0; i < N; ++i) { y[i] = (t[i] + x[i]); }
      free(t);
    }"""
    bound = binding("k", ("x", "ptr_double", ["N"]), ("y", "ptr_double", ["N"]), ("N", "int64", []))
    module, kernel = lifted(source, bound)
    x, y = np.arange(4.0), np.zeros(4)

    kernel(x, y, 4)

    assert "t = np.empty((N,), dtype=np.float64)" in module
    assert "y[:] = t + x" in module and "for" not in module
    np.testing.assert_array_equal(y, 3 * x)


def test_a_matmul_nest_and_cblas_dgemm_both_become_matmul():
    nest = """
    void k(const double *restrict A, const double *restrict B, double *restrict C, const int64_t M, const int64_t N,
           const int64_t K) {
      for (int64_t i = 0; i < M; ++i)
        for (int64_t j = 0; j < N; ++j) {
          C[(i)*(N) + (j)] = 0.0;
          for (int64_t l = 0; l < K; ++l) C[(i)*(N) + (j)] += A[(i)*(K) + (l)] * B[(l)*(N) + (j)];
        }
    }"""
    blas = """
    void k(const double *restrict A, const double *restrict B, double *restrict C, const int64_t M, const int64_t N,
           const int64_t K) {
      cblas_dgemm(CblasRowMajor, CblasNoTrans, CblasNoTrans, (blasint)(M), (blasint)(N), (blasint)(K), 1.0, A,
                  (blasint)(K), B, (blasint)(N), 0.0, C, (blasint)(N));
    }"""
    shapes = (("A", "ptr_double", ["M", "K"]), ("B", "ptr_double", ["K", "N"]), ("C", "ptr_double", ["M", "N"]))
    bound = binding("k", *shapes, ("M", "int64", []), ("N", "int64", []), ("K", "int64", []))
    rng = np.random.default_rng(1)
    a, b = rng.random((3, 4)), rng.random((4, 5))
    for source in (nest, blas):
        module, kernel = lifted(source, bound)
        c = np.zeros((3, 5))

        kernel(a, b, c, 3, 5, 4)

        assert "C[:, :] = A @ B" in module
        np.testing.assert_allclose(c, a @ b)


def test_reductions_become_np_sum_over_the_reduced_axes():
    source = """
    void k(const double *restrict x, double *restrict rows, double *restrict total, const int64_t M,
           const int64_t N) {
      double s = 0.0;
      for (int64_t i = 0; i < M; ++i) {
        rows[i] = 0.0;
        for (int64_t j = 0; j < N; ++j) rows[i] = (rows[i] + x[(i)*(N) + (j)]);
      }
      for (int64_t i = 0; i < M; ++i) for (int64_t j = 0; j < N; ++j) s += x[(i)*(N) + (j)];
      total[0] = s;
    }"""
    bound = binding(
        "k",
        ("x", "ptr_double", ["M", "N"]),
        ("rows", "ptr_double", ["M"]),
        ("total", "ptr_double", ["1"]),
        ("M", "int64", []),
        ("N", "int64", []),
    )
    module, kernel = lifted(source, bound)
    x, rows, total = np.arange(6.0).reshape(2, 3), np.zeros(2), np.zeros(1)

    kernel(x, rows, total, 2, 3)

    assert "rows[:] = np.sum(x, axis=1)" in module and "s += np.sum(x)" in module
    np.testing.assert_array_equal(rows, x.sum(axis=1))
    assert total[0] == x.sum()


def test_memset_constants_float_scalars_and_nested_branches_keep_c_semantics():
    source = """
    constexpr int64_t K = 2;
    #define SCALE 0.5
    void k(float *restrict y, const float *restrict x, const int64_t N) {
      memset(y, 0, (size_t)(N) * sizeof(float));
      float acc = 0.0f;
      for (int64_t i = 0; i < N; ++i) {
        if (x[i] > 0.0f) { acc += x[i]; } else { if (x[0] > 1.0f) { y[i] = 1.0f; } else { y[i] = K * SCALE; } }
      }
      y[0] += acc;
    }"""
    bound = binding("k", ("y", "ptr_float", ["N"]), ("x", "ptr_float", ["N"]), ("N", "int64", []))
    module, kernel = lifted(source, bound)
    x, y = np.array([0.5, -1.0, 3.0], dtype=np.float32), np.full(3, 7.0, dtype=np.float32)

    kernel(y, x, 3)

    assert "y[:] = 0" in module and "acc = np.float32(acc + x[i])" in module
    np.testing.assert_array_equal(y, np.array([3.5, 1.0, 0.0], dtype=np.float32))


@pytest.mark.parametrize(
    ("body", "reason"),
    [
        ('__asm__ volatile("nop");', "inline asm"),
        ("x[0] = 1.0; goto done; done: x[1] = 2.0;", "goto"),
        ("const double *p = x + 1; x[0] = p[0];", "a pointer into an array (pointer arithmetic)"),
        ("x[0] = foo(x[1]);", "a call to a function outside math.h and BLAS"),
        ("x[0] = twice(x[1]);", "a call to a helper function of the file (inline it into the kernel)"),
        (
            "struct pair { double a; } p; x[0] = p.a;",
            "a type outside canonical C form (a struct, complex or library type)",
        ),
        ("x[0] = GLOBAL;", "a name that is no array, scalar or constant (a global or a macro)"),
        ("switch (N) { case 1: x[0] = 1.0; }", "switch"),
    ],
)
def test_constructs_outside_canonical_c_are_refused_with_their_reason(body: str, reason: str):
    source = (
        f"static double twice(double v) {{ return 2.0 * v; }}\nvoid k(double *restrict x, const int64_t N) {{ {body} }}"
    )
    bound = binding("k", ("x", "ptr_double", ["N"]), ("N", "int64", []))

    with pytest.raises(cnumpy.Refused) as refused:
        cnumpy.translate(source, bound)

    assert refused.value.reason == reason


def test_the_command_line_writes_the_numpy_and_the_sdfg(tmp_path):
    source = tmp_path / "k.c"
    source.write_text(
        "void k(double *restrict y, const double *restrict x, const int64_t N) {\n"
        "  for (int64_t i = 0; i < N; ++i) y[i] = sqrt(x[i]);\n}\n"
    )
    bound = tmp_path / "k_binding.json"
    bound.write_text(
        json.dumps(binding("k", ("y", "ptr_double", ["N"]), ("x", "ptr_double", ["N"]), ("N", "int64", [])))
    )

    assert (
        cnumpy.main([str(source), str(bound), "--out", str(tmp_path / "k.py"), "--sdfg", str(tmp_path / "k.sdfg")]) == 0
    )

    assert "y[:] = np.sqrt(x)" in (tmp_path / "k.py").read_text()
    sdfg = dace.SDFG.from_file(str(tmp_path / "k.sdfg"))
    assert {"x", "y"} <= set(sdfg.arrays) and "N" in sdfg.free_symbols


def test_every_refusal_reason_on_the_skill_page_is_one_the_lifter_prints():
    page = pathlib.Path(cnumpy.__file__).parent.parent / "hb_plugin" / "skills" / "alloy-c" / "SKILL.md"
    table = page.read_text().split("## Refused, with the reason printed")[1]
    reasons = {
        r
        for line in table.splitlines()
        if line.startswith("| `")
        for r in re.findall(r"`([^`]+)`", line.split(" | ")[0])
    }
    code = pathlib.Path(cnumpy.__file__).read_text()

    assert len(reasons) > 20
    assert [r for r in reasons if f'"{r}"' not in code] == []
