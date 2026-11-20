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


def test_a_flat_index_with_offsets_delinearizes_against_the_shape() -> None:
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


def test_integer_division_truncates_as_c_does_unless_both_sides_are_non_negative() -> None:
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


def test_a_null_pointer_then_malloc_becomes_np_empty_and_the_nests_become_array_statements() -> None:
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


def test_a_matmul_nest_and_cblas_dgemm_both_become_matmul() -> None:
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


def test_reductions_become_np_sum_over_the_reduced_axes() -> None:
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


def test_memset_constants_float_scalars_and_nested_branches_keep_c_semantics() -> None:
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
        ("x[0] = twice(x[1]); x[1] = twice(x[0]);", "a helper function that computes its value in statements"),
        (
            "struct pair { double a; } p; x[0] = p.a;",
            "a type outside canonical C form (a struct, complex or library type)",
        ),
        ("x[0] = GLOBAL;", "a name that is no array, scalar or constant (a global or a macro)"),
        ("switch (N) { case 1: x[0] = 1.0; }", "switch"),
    ],
)
def test_constructs_outside_canonical_c_are_refused_with_their_reason(body: str, reason: str) -> None:
    source = f"static double twice(double v) {{ double w = 2.0 * v; return w; }}\nvoid k(double *restrict x, const int64_t N) {{ {body} }}"
    bound = binding("k", ("x", "ptr_double", ["N"]), ("N", "int64", []))

    with pytest.raises(cnumpy.Refused) as refused:
        cnumpy.translate(source, bound)

    assert refused.value.reason == reason


def test_the_command_line_writes_the_numpy_and_the_sdfg(tmp_path: pathlib.Path) -> None:
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


def test_every_refusal_reason_on_the_skill_page_is_one_the_lifter_prints() -> None:
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


def test_a_dereference_of_an_output_pointer_is_its_first_element_and_pragmas_are_dropped() -> None:
    source = """
    void k(const double *restrict x, double *restrict out, const int64_t N) {
      double s = 0.0;
      #pragma omp simd reduction(+:s)
      for (int64_t i = 0; i < N; i++) s += x[i];
      *out = s;
    }"""
    bound = binding("k", ("x", "ptr_double", ["N"]), ("out", "ptr_double", ["1"]), ("N", "int64", []))
    module, kernel = lifted(source, bound)
    out = np.zeros(1)

    kernel(np.arange(4.0), out, 4)

    assert "out[0] = s" in module and "pragma" not in module
    assert out[0] == 6.0


def test_a_constant_extent_stays_a_name_so_the_index_splits_against_it() -> None:
    source = """
    constexpr int64_t nb = 3;
    void k(double *restrict q, const int64_t batch) {
      for (int64_t b = 0; b < batch; ++b) for (int64_t i = 0; i < nb; ++i) q[(b)*(nb) + (i)] += 1.0 * b;
    }"""
    module, kernel = lifted(source, binding("k", ("q", "ptr_double", ["batch", "nb"]), ("batch", "int64", [])))
    q = np.zeros((2, 3))

    kernel(q, 2)

    assert "q[b, i]" in module
    np.testing.assert_array_equal(q, [[0.0] * 3, [1.0] * 3])


def test_a_horner_form_index_splits_against_extents_that_are_no_single_symbol() -> None:
    source = """
    void k(double *restrict t, const int64_t N) {
      for (int64_t i = 0; i < (N - 1); ++i)
        for (int64_t j = 0; j < (N - 2); ++j) t[(i)*((N - 2)) + (j)] = 10.0 * i + j;
    }"""
    module, kernel = lifted(source, binding("k", ("t", "ptr_double", ["N - 1", "N - 2"]), ("N", "int64", [])))
    t = np.zeros((3, 2))

    kernel(t, 4)

    assert "t[i, j]" in module
    np.testing.assert_array_equal(t, [[0.0, 1.0], [10.0, 11.0], [20.0, 21.0]])


def test_an_index_whose_stride_is_not_the_temporaries_extent_reads_the_flat_view() -> None:
    source = """
    void k(double *restrict out, const int64_t N, const int64_t W) {
      double *t = (double *)malloc((size_t)((N) * ((N + 1))) * sizeof(double));
      for (int64_t i = 0; i < N; ++i) for (int64_t j = 0; j < W; ++j) t[(i)*(W) + (j)] = 10.0 * i + j;
      for (int64_t i = 0; i < N * W; ++i) out[i] = t[i];
      free(t);
    }"""
    bound = binding("k", ("out", "ptr_double", ["N * W"]), ("N", "int64", []), ("W", "int64", []))
    module, kernel = lifted(source, bound)
    out = np.zeros(4)

    kernel(out, 2, 2)

    assert "t.reshape(-1)[i * W + j]" in module
    np.testing.assert_array_equal(out, [0.0, 1.0, 10.0, 11.0])


def test_a_const_index_local_delinearizes_through_its_value() -> None:
    source = """
    void k(double *restrict aa, const int64_t LEN) {
      const int64_t n = LEN;
      for (int64_t i = 1; i < n; ++i)
        for (int64_t j = 1; j < n; ++j) {
          const int64_t ij = i * n + j;
          aa[ij] = aa[(i - 1) * n + (j - 1)] + 1.0;
        }
    }"""
    module, kernel = lifted(source, binding("k", ("aa", "ptr_double", ["LEN", "LEN"]), ("LEN", "int64", [])))
    aa = np.zeros((3, 3))

    kernel(aa, 3)

    assert "aa[i, j] = aa[i - 1, j - 1] + 1.0" in module
    np.testing.assert_array_equal(aa, [[0, 0, 0], [0, 1, 1], [0, 1, 2]])


def test_the_binding_s_c_symbol_names_the_function_when_it_differs_from_the_kernel_name() -> None:
    bound = {**binding("K_fp64", ("x", "ptr_double", ["N"]), ("N", "int64", [])), "symbols": {"c": "k_fp64"}}

    module = cnumpy.translate("void k_fp64(double *restrict x, const int64_t N) { x[0] = 1.0; }", bound)

    assert "x[0] = 1.0" in module


def test_helpers_of_the_file_are_inlined_a_value_into_its_expression_a_void_one_into_the_caller() -> None:
    source = """
    static int64_t idx(int64_t i, int64_t j, int64_t n) { return i * n + j; }
    static void bump(double *restrict a, const double *restrict b, const int64_t n) {
      for (int64_t k = 0; k < n; ++k) a[k] += b[k];
    }
    void k(double *restrict aa, double *restrict x, const double *restrict y, const int64_t N) {
      for (int64_t i = 1; i < N; ++i)
        for (int64_t j = 0; j < N; ++j) aa[idx(i, j, N)] = aa[idx(i - 1, j, N)] + 1.0;
      bump(x, y, N);
    }"""
    bound = binding(
        "k",
        ("aa", "ptr_double", ["N", "N"]),
        ("x", "ptr_double", ["N"]),
        ("y", "ptr_double", ["N"]),
        ("N", "int64", []),
    )
    module, kernel = lifted(source, bound)
    aa, x = np.zeros((2, 2)), np.ones(2)

    kernel(aa, x, np.arange(2.0), 2)

    assert "aa[i, j] = aa[i - 1, j] + 1.0" in module and "x[:] += y" in module
    np.testing.assert_array_equal(aa, [[0.0, 0.0], [1.0, 1.0]])
    np.testing.assert_array_equal(x, [1.0, 2.0])


@pytest.mark.parametrize(
    ("helpers", "call", "reason"),
    [
        (
            "static double f(double v) { return v < 1.0 ? v : f(v - 1.0); }",
            "x[0] = f(x[1]);",
            "a recursive helper function",
        ),
        (
            "static void g(double *a) { a[0] = 1.0; }",
            "g(x + 1);",
            "a helper call on part of an array (pointer arithmetic)",
        ),
        (
            "static void g(double *a, int64_t m) { m += 1; a[0] = m; }",
            "g(x, N);",
            "a helper that stores to a scalar parameter",
        ),
    ],
)
def test_helpers_outside_the_inlinable_form_are_refused(helpers: str, call: str, reason: str) -> None:
    source = f"{helpers}\nvoid k(double *restrict x, const int64_t N) {{ {call} }}"

    with pytest.raises(cnumpy.Refused) as refused:
        cnumpy.translate(source, binding("k", ("x", "ptr_double", ["N"]), ("N", "int64", [])))

    assert refused.value.reason == reason
