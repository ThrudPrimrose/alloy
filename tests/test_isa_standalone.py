# Copyright 2026 ETH Zurich and the Alloy authors.
"""Every answer's code is one self-contained block: it compiles with nothing but its setup's build line, no include
path and no Alloy header beside it."""

import dataclasses
import pathlib
import re
import shlex
import subprocess

import pytest

from alloy.isa import simt, tile
from alloy.isa.ask import Answer, Feasible, Operand, Request, Swizzle, ask
from helpers import sample

GPUS = ("sm90", "gfx942", "gfx90a")
TMA = {"src": Operand("global", "f16", (256, 256)), "dst": Operand("shared", "f16", (64, 64), "row_major", "b128")}
LDS = {"src": Operand("global", "f16", (256, 256)), "dst": Operand("shared", "f16", (64, 64), "row_major", "xor:8")}


def mma(target: str, in_type: str, rows: int = 64) -> Request:
    swizzle: Swizzle = "b128" if target == "sm90" else "xor:8"
    k = 128 if in_type in ("e4m3", "e5m2") else 64
    a = Operand("shared", in_type, (rows, k), "row_major", swizzle)
    b = Operand("shared", in_type, (k, rows), "col_major", swizzle)
    return Request(target, "mma", {"a": a, "b": b, "c": Operand("register", "f32", (rows, rows))})


def built(answer: Answer, tmp_path: pathlib.Path) -> subprocess.CompletedProcess[str]:
    """``answer``'s code saved under the file name its build line names, compiled with that line in an empty folder (a
    line that links builds an object instead: this machine may lack the GPU's runtime library)."""
    assert isinstance(answer, Feasible), answer
    argv = shlex.split(answer.setup["build"])
    argv = argv if "-c" in argv else tile.compile_only(argv)
    source = next(a for a in argv if re.fullmatch(r"\w+\.(c|cu|hip)", a))
    (tmp_path / source).write_text(answer.code)
    return subprocess.run(argv, cwd=tmp_path, capture_output=True, text=True, check=False, timeout=600)


def assert_builds(answer: Answer, tmp_path: pathlib.Path) -> None:
    done = built(answer, tmp_path)
    assert done.returncode == 0, done.stderr[-2000:]
    assert '#include "alloy' not in answer.code  # type: ignore[union-attr]


SIMT = [(target, row.op) for target in GPUS for row in simt.rows()]
CUDA_ROWS = [(t, op) for t, op in SIMT if t == "sm90"]
HIP_ROWS = [(t, op) for t, op in SIMT if t != "sm90"]


@pytest.mark.cuda
@pytest.mark.parametrize(("target", "op"), sample(CUDA_ROWS))
def test_a_cuda_device_row_compiles_on_its_own(target: str, op: str, tmp_path: pathlib.Path) -> None:
    assert_builds(ask(Request(target, op), verify=False), tmp_path)


@pytest.mark.hip
@pytest.mark.parametrize(("target", "op"), sample(HIP_ROWS))
def test_a_hip_device_row_compiles_on_its_own(target: str, op: str, tmp_path: pathlib.Path) -> None:
    assert_builds(ask(Request(target, op), verify=False), tmp_path)


@pytest.mark.cuda
@pytest.mark.parametrize("request_", [
    mma("sm90", "f16"), mma("sm90", "e4m3"), mma("sm90", "bf16", rows=128), Request("sm90", "copy", TMA),
    *(Request("sm90", "wait", on=on) for on in ("mbarrier", "bulk_group", "cp_async_group", "wgmma_group")),
    *(Request("sm90", "fence", kind=kind) for kind in ("proxy", "operand")),
], ids=str)  # fmt: skip
def test_an_sm90_answer_compiles_with_its_build_line_alone(request_: Request, tmp_path: pathlib.Path) -> None:
    assert_builds(ask(request_, verify=False), tmp_path)


@pytest.mark.hip
@pytest.mark.parametrize("request_", [
    mma("gfx942", "f16"), mma("gfx942", "e5m2"), mma("gfx90a", "bf16"), Request("gfx942", "copy", LDS),
    Request("gfx90a", "copy", LDS), *(Request(t, "wait", on=on) for t in ("gfx942", "gfx90a") for on in ("vmcnt", "lgkmcnt")),
], ids=str)  # fmt: skip
def test_a_cdna_answer_compiles_with_its_build_line_alone(request_: Request, tmp_path: pathlib.Path) -> None:
    assert_builds(ask(request_, verify=False), tmp_path)


def test_a_trimmed_gpu_answer_carries_only_its_own_type_and_shape() -> None:
    sut = ask(mma("sm90", "e4m3"), verify=False)

    assert isinstance(sut, Feasible)
    assert "alloy_wgmma_n64_e4m3" in sut.code and "alloy_wgmma_n64_f16" not in sut.code
    assert "alloy_gemm_128x128" not in sut.code and "alloy_gemm_64x64" in sut.code
    assert "alloy-only" not in sut.code and "alloy-end" not in sut.code


@pytest.mark.clang
def test_an_sme_mma_answer_compiles_with_its_build_line_alone(tmp_path: pathlib.Path) -> None:
    operands = {"a": Operand("global", "f32", (32, 32), "col_major"), "b": Operand("global", "f32", (32, 32)),
                "c": Operand("tile_register", "f32", (32, 32))}  # fmt: skip

    assert_builds(ask(Request("sme", "mma", operands), verify=False), tmp_path)


@pytest.mark.gcc
@pytest.mark.parametrize(("target", "dtype", "lanes"), [("avx512", "f64", 8), ("avx2", "f32", 8), ("neon", "f64", 2),
                                                        ("sve", "f32", 0)])  # fmt: skip
def test_a_cpu_math_kernel_compiles_with_its_build_line_alone(
    target: str, dtype: str, lanes: int, tmp_path: pathlib.Path
) -> None:
    x = Operand("vector", dtype, (lanes,) if lanes else ())

    assert_builds(ask(Request(target, "exp", {"x": x}), verify=False), tmp_path)


@pytest.mark.gcc
def test_a_cpu_mma_answer_compiles_with_its_build_line_alone(tmp_path: pathlib.Path) -> None:
    tile_ = Operand("global", "f64", (64, 64))

    assert_builds(ask(Request("avx512", "mma", {"a": tile_, "b": tile_, "c": tile_}), verify=False), tmp_path)


#: The C types of the operand names the AVX-512 f64 rows' signatures use.
DECLARED = (
    "__m512d a = _mm512_set1_pd(1), b = a, c = a, v = a, src = a; double s = 0, buffer[8] = {0}, *p = buffer; "
    "__mmask8 k = 0; __m512i iota = _mm512_setzero_si512(), n = iota;"
)


@pytest.mark.gcc
@pytest.mark.parametrize("op", ["add", "fma", "broadcast", "reduce_add", "scan_add", "gen_mask"])
def test_a_cpu_answer_is_one_statement_that_compiles_with_its_header_and_flags(op: str, tmp_path: pathlib.Path) -> None:
    sut = ask(Request("avx512", op, {"x": Operand("vector", "f64", (8,))}), verify=False)
    assert isinstance(sut, Feasible)
    unused = "(void)a; (void)b; (void)c; (void)v; (void)src; (void)s; (void)p; (void)k; (void)iota; (void)n;"
    wrapped = f"{sut.setup['header']}\nvoid f(void) {{\n  {DECLARED}\n  {sut.code}\n  {unused}\n}}\n"

    assert_builds(dataclasses.replace(sut, code=wrapped), tmp_path)
