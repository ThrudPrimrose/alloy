# Copyright 2026 ETH Zurich and the Alloy authors.
"""The Tensix rows: each one recorded as run on ttsim, the lookup answering from those records, and the kernel the
harness builds spelled for the tt-metal version it targets."""

import shutil

import pytest

from alloy.isa import tensix, tensix_harness
from alloy.isa.__main__ import main


def test_every_row_at_every_dtype_has_a_passing_run_on_the_pinned_image():
    verdicts = tensix.verdicts()

    for row in tensix.rows():
        for dtype in tensix.dtypes():
            if row.pending:  # run by the tensix CI job (below), recorded by the next `verify`
                assert (row.op, dtype, row.unit) not in verdicts
                continue
            verdict = verdicts[(row.op, dtype, row.unit)]
            assert verdict.ok, (row.op, dtype, row.unit, verdict.error)
    assert tensix.recorded()["image"] == tensix.IMAGE


def test_an_fpu_add_reads_tf32_operands_and_an_sfpu_add_keeps_f32():
    verdicts = tensix.verdicts()

    fpu, sfpu = verdicts[("add", "f32", "FPU")], verdicts[("add", "f32", "SFPU")]

    assert fpu.rel is not None and sfpu.rel is not None
    assert fpu.rel > 1e-5 > 1e-6 > sfpu.rel


def test_the_lookup_offers_both_units_of_an_op_with_their_recorded_errors(capsys: pytest.CaptureFixture[str]):
    assert main(["lookup", "tensix", "add", "f32"]) == 0

    printed = capsys.readouterr().out
    assert "FPU (binary)" in printed and "SFPU (binary_sfpu)" in printed
    assert "add_tiles_init(c0, c1) [v06], add_init(c0, c1) [v08]" in printed
    assert printed.count("verified on ttsim") == 2


def test_the_lookup_refuses_f64_because_tensix_has_none(capsys: pytest.CaptureFixture[str]):
    assert main(["lookup", "tensix", "exp", "f64"]) != 0

    assert "no f64" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("new", "spelled", "absent"),
    [
        (
            True,
            ['#include "api/compute/eltwise_binary.h"', "void kernel_main()", "add_init(c0, c1);"],
            "add_tiles_init",
        ),
        (
            False,
            ['#include "compute_kernel_api/eltwise_binary.h"', "void MAIN", "add_tiles_init(c0, c1);"],
            "add_init(",
        ),
    ],
)
def test_the_compute_kernel_is_spelled_for_its_tt_metal_version(new: bool, spelled: list[str], absent: str):
    row = next(r for r in tensix.harness_rows() if (r["op"], r["unit"]) == ("add", "FPU"))

    sut = tensix_harness.compute(row, new)

    assert all(text in sut for text in spelled), sut
    assert absent not in sut


def test_the_root_header_of_tt_metal_06_is_not_under_compute_kernel_api():
    assert tensix_harness.compute_include("compute_kernel_api.h", new=False) == "compute_kernel_api.h"
    assert tensix_harness.compute_include("eltwise_unary/exp.h", new=False) == "compute_kernel_api/eltwise_unary/exp.h"


@pytest.mark.tensix
def test_every_row_runs_correct_on_ttsim(tmp_path_factory: pytest.TempPathFactory):
    if shutil.which("docker") is None:
        pytest.fail("the tensix mark needs docker")
    library = tensix.ttsim(tmp_path_factory.mktemp("ttsim"))

    found = tensix.run_harness(library, tensix.IMAGE)

    assert len(found) == len(tensix.rows()) * len(tensix.dtypes())
    assert all(v.ok for v in found), [v for v in found if not v.ok]


@pytest.mark.parametrize(("new", "spelled"), [
    (True, ["compute_kernel_hw_startup<SrcOrder::Reverse>(c0, c1, c16); matmul_init(c0, c1);",
            "matmul_tiles(c0, c1, 0, 0, 0);", '#include "api/compute/src_order.h"']),
    (False, ["mm_init(c0, c1, c16);", "matmul_tiles(c0, c1, 0, 0, 0, false);"]),
])  # fmt: skip
def test_the_matmul_kernel_accumulates_every_k_tile_into_one_dst_tile(new: bool, spelled: list[str]):
    row = next(r for r in tensix.harness_rows() if r["op"] == "mma")

    sut = tensix_harness.compute(row, new)

    assert all(text in sut for text in spelled), sut
    assert sut.count("pack_tile(0, c16)") == 1 and "for (uint32_t kt = 0; kt < num_tiles; ++kt)" in sut
