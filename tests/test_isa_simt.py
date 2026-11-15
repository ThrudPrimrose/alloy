# Copyright 2026 ETH Zurich and the Alloy authors.
"""The CUDA and HIP rows: recorded checks, the dialect differences the lookup must keep, and the device runs."""

import pytest

from alloy.isa import simt
from alloy.isa.__main__ import main


def test_every_row_is_recorded_correct_on_cuda_and_compiled_or_correct_on_hip():
    verdicts = simt.verdicts()

    for row in simt.rows():
        assert verdicts[(row.op, "cuda")].ok is True, verdicts[(row.op, "cuda")]
        assert verdicts[(row.op, "hip")].ok is not False, verdicts[(row.op, "hip")]


def test_a_warp_reduction_takes_a_mask_on_cuda_and_none_on_a_64_lane_hip_wavefront():
    row = next(r for r in simt.rows() if r.op == "reduce_add")

    cuda, hip = simt.program(row, "cuda"), simt.program(row, "hip")

    assert "__shfl_down_sync(0xffffffffu, out, d)" in cuda and "#define LANES 32" in cuda
    assert "__shfl_down(out, d)" in hip and "#define LANES 64" in hip
    assert "#include <hip/hip_runtime.h>" in hip and "hipMalloc" in hip


def test_the_lookup_prints_the_dialects_spelling_and_its_check(capsys: pytest.CaptureFixture[str]):
    assert main(["lookup", "hip", "gen_mask", "f32"]) == 0

    printed = capsys.readouterr().out
    assert "__popcll(__ballot(v > 0.0f))" in printed
    assert "compiled for gfx90a, gfx942" in printed


@pytest.mark.nvidia
@pytest.mark.parametrize("row", simt.rows(), ids=lambda r: r.op)
def test_each_row_runs_correct_on_an_nvidia_gpu(row: simt.Row):
    sut = simt.check(row, "cuda", runs=True)

    assert sut.ok is True, sut


@pytest.mark.hip
@pytest.mark.parametrize("row", simt.rows(), ids=lambda r: r.op)
def test_each_row_compiles_for_cdna(row: simt.Row):
    sut = simt.check(row, "hip", runs=False)

    assert sut.ok is None and "compiled" in sut.basis, sut
