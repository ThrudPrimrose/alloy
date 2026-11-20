# Copyright 2026 ETH Zurich and the Alloy authors.
"""Intrinsic tasklets: which innermost loops the lookup rows spell, the tasklets built from the rows, and the GPU
device tasklets compiled by the device compilers (no device needed)."""

import ctypes
import pathlib
import shutil
import subprocess

import dace
import numpy as np
import pytest
from dace.codegen import cpf
from dace.config import set_temporary
from dace.frontend.python.parser import DaceProgram

from alloy.backend import intrinsics
from alloy.backend.intrinsics import Leaf, Op, Plan, Spelling, Write
from alloy.frontend import scopes
from alloy.isa.table import load
from helpers import MATRIX

N = dace.symbol("N", dtype=dace.int64)
ROWS = MATRIX.intrinsic_tasklets.rows


@dace.program
def axpy(x: dace.float64[N], y: dace.float64[N], z: dace.float64[N]) -> None:
    for i in range(N):  # pyright: ignore[reportArgumentType] -- test double
        z[i] = 2.0 * x[i] + y[i]


@dace.program
def total(x: dace.float64[N], s: dace.float64[1]) -> None:
    for i in range(N):  # pyright: ignore[reportArgumentType] -- test double
        s[0] = s[0] + x[i]


@dace.program
def recurrence(a: dace.float64[N], b: dace.float64[N]) -> None:
    for i in range(1, N):  # pyright: ignore[reportArgumentType] -- test double
        a[i] = a[i - 1] + b[i]


@dace.program
def saxpy(x: dace.float32[N], y: dace.float32[N], z: dace.float32[N]) -> None:
    for i in dace.map[0:N]:
        z[i] = 2.0 * x[i] + y[i]


def scope_sdfg(program: DaceProgram) -> dace.SDFG:
    """The program's one scope, as the sweep outlines it."""
    (scope,) = scopes.outline(program.to_sdfg(simplify=False), MATRIX.libm_calls).scopes
    return scope.sdfg


def plan(write: Write, dtype: str = "f64") -> Plan:
    return Plan("loop", dace.nodes.MapEntry(dace.nodes.Map("m", ["i"], dace.subsets.Range([(0, 7, 1)]))), None, "i",
                0, 7, (write,), dtype)  # fmt: skip


X, Y, Z = (Leaf("load", name, ("i",)) for name in "xyz")


def test_an_elementwise_loop_is_admitted_with_the_rows_it_needs() -> None:
    (sut,) = intrinsics.admit(scope_sdfg(axpy), ROWS).plans

    assert (sut.dtype, sut.reduces) == ("f64", False)
    assert sut.rows(fused=False) == {"load", "store", "broadcast", "mul", "add"}
    assert sut.rows(fused=True) == {"load", "store", "broadcast", "fma"}


def test_a_scalar_updated_as_its_own_sum_is_a_reduction() -> None:
    (sut,) = intrinsics.admit(scope_sdfg(total), ROWS).plans

    assert [(w.data, w.reduce, w.value) for w in sut.writes] == [("s", "reduce_add", Leaf("load", "x", ("i",)))]


def test_a_loop_that_reads_what_an_earlier_iteration_wrote_is_refused_with_why() -> None:
    sut = intrinsics.admit(scope_sdfg(recurrence), ROWS)

    assert not sut.plans
    assert "an iteration reads what another writes" in sut.refused[0]


def test_a_tasklet_whose_op_the_matrix_leaves_out_is_refused() -> None:
    sut = intrinsics.admit(scope_sdfg(axpy), ("load", "store", "broadcast", "add"))

    assert not sut.plans and "mul" in sut.refused[0]


@pytest.mark.parametrize(
    ("lookup", "fma"),
    [("avx2", "_mm256_fmadd_pd(__v2, __v3, __v4)"), ("avx512", "_mm512_fmadd_pd(__v2, __v3, __v4)"),
     ("neon", "vfmaq_f64(__v4, __v2, __v3)"), ("sve", "svmla_f64_x(pg, __v4, __v2, __v3)")],
)  # fmt: skip
def test_a_fused_tasklet_binds_the_fma_rows_operands_by_its_semantics(lookup: str, fma: str) -> None:
    """x*y + z: the product's operands where the row's semantics multiply, the addend where it adds."""
    sut = intrinsics.tasklets(plan(Write("z", ("i",), Op("add", (Op("mul", (X, Y)), Z)))), Spelling(lookup, "f64",
                              load(), fused=True))  # fmt: skip

    assert fma in sut.main
    assert set(sut.loads.values()) == {("x", ("i",)), ("y", ("i",)), ("z", ("i",))}
    assert sut.stores == {"__out0": ("z", ("i",))}


def test_an_sve_tasklet_loops_over_the_block_under_the_gen_mask_predicate() -> None:
    sut = intrinsics.tasklets(plan(Write("z", ("i",), Op("add", (X, Y)))), Spelling("sve", "f64", load(), False))

    assert sut.main.startswith("for (int64_t __k = 0; __k < 32; __k += svcntd())")
    assert "svbool_t pg = svwhilelt_b64_s64(__k, (int64_t)32);" in sut.main
    assert "svld1_f64(pg, __in0 + __k)" in sut.main


def test_a_sum_starts_its_accumulator_at_zero_and_folds_it_into_the_target() -> None:
    sut = intrinsics.tasklets(plan(Write("s", ("0",), X, "reduce_add")), Spelling("avx512", "f64", load(), False))

    assert "_mm512_setzero_pd()" in sut.init
    assert "_mm512_add_pd(__v1, __v2)" in sut.main
    assert "_mm512_reduce_add_pd(__a)" in sut.final and "__s_out = __s + __t;" in sut.final


def test_a_max_starts_its_accumulator_at_the_target() -> None:
    sut = intrinsics.tasklets(plan(Write("s", ("0",), X, "reduce_max")), Spelling("avx2", "f64", load(), False))

    assert "_mm256_set1_pd(__s)" in sut.init
    assert "__s_out = __t;" in sut.final


def compiled(code: str, tmp_path: pathlib.Path, name: str) -> ctypes.CDLL:
    source = tmp_path / f"{name}.c"
    source.write_text(code)
    library = tmp_path / f"lib{name}.so"
    subprocess.run(
        ["gcc", "-std=gnu17", "-O2", "-march=native", "-shared", "-fPIC", str(source), "-o", str(library)], check=True
    )
    return ctypes.CDLL(str(library))


@pytest.mark.gcc
@pytest.mark.parametrize("program", [axpy, total])
def test_a_rendered_loop_with_a_remainder_computes_what_the_loop_does(
    program: DaceProgram, tmp_path: pathlib.Path
) -> None:
    """15 elements: whole AVX2 blocks of 4, then the remainder loop; a sum reassociates, so it is compared by band."""
    (scope,) = scopes.outline(program.to_sdfg(simplify=False), MATRIX.libm_calls).scopes
    rendered, header = intrinsics.rendered(scope.sdfg, "avx2", fused=False, rows=ROWS)
    code = header + "\n" + cpf.render(rendered, language="c", check_compiles=False, signature=cpf.EntrySignature(
        order=list(scope.abi_order))).code  # fmt: skip
    function = compiled(code, tmp_path, scope.symbol)[scope.symbol]
    rng = np.random.default_rng(0)
    arrays = {"x": rng.random(15), "y": rng.random(15), "z": np.zeros(15), "s": np.array([0.5])}
    expected = 2.0 * arrays["x"] + arrays["y"] if program is axpy else 0.5 + arrays["x"].sum()
    arguments = [ctypes.c_int64(15) if name == "N" else arrays[name].ctypes.data_as(ctypes.POINTER(ctypes.c_double))
                 for name in scope.abi_order]  # fmt: skip
    function(*arguments)
    if program is axpy:
        assert np.array_equal(arrays["z"], expected)
    else:
        assert arrays["s"][0] == pytest.approx(expected, rel=1e-14)


def test_a_device_tasklet_loads_a_float4_and_fuses_with_the_fma_row() -> None:
    rendered = intrinsics.device_rendered(gpu_program(), "cuda")

    (tasklet,) = [n for n, _ in rendered.all_nodes_recursive() if isinstance(n, dace.nodes.Tasklet)
                  and n.label.endswith("_intrinsic")]  # fmt: skip
    assert "float4 __w0 = reinterpret_cast<const float4*>(__in0)[0];" in tasklet.code.as_string
    assert "__out0[3] = fmaf((float)(2.0), __w0.w, __w1.w);" in tasklet.code.as_string


def gpu_program() -> dace.SDFG:
    sdfg = saxpy.to_sdfg()
    sdfg.apply_gpu_transformations()
    for node, _ in sdfg.all_nodes_recursive():
        if isinstance(node, dace.nodes.MapEntry):
            node.map.gpu_block_size = [128, 1, 1]
    return sdfg


@pytest.mark.parametrize(
    "dialect",
    [pytest.param("cuda", marks=pytest.mark.cuda), pytest.param("hip", marks=pytest.mark.hip)],
)
def test_a_device_tasklet_compiles_for_its_device(dialect: str, tmp_path: pathlib.Path) -> None:
    """Build only: the device unit of the rewritten program compiles for sm_89 or gfx90a."""
    driver = "nvcc" if dialect == "cuda" else "hipcc"
    if shutil.which(driver) is None:
        pytest.skip(f"{driver} is not on PATH")
    unit = tmp_path / ("unit.cu" if dialect == "cuda" else "unit.hip")
    with set_temporary("compiler", "cuda", "chiplet_number", value=1):  # no device here to count them on
        rendered = cpf.render(
            intrinsics.device_rendered(gpu_program(), dialect), language=dialect, check_compiles=False
        )
    unit.write_text(rendered.device_code)
    arch = [*cpf.CUDA_BUILD_FLAGS, "-arch=sm_89"] if dialect == "cuda" else ["-std=c++20", "--offload-arch=gfx90a"]
    done = subprocess.run([driver, *arch, "-c", str(unit), "-o", str(tmp_path / "unit.o")], capture_output=True,
                          text=True)  # fmt: skip
    assert done.returncode == 0, done.stderr[-2000:]
