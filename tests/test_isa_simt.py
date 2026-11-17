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


def test_a_warp_scan_adds_the_lane_d_below_only_where_one_exists_and_checks_every_lane():
    row = next(r for r in simt.rows() if r.op == "scan_add")

    cuda, hip = simt.program(row, "cuda"), simt.program(row, "hip")

    assert "__shfl_up_sync(0xffffffffu, out, d); if (lane >= d) out += t;" in cuda
    assert "__shfl_up(out, d); if (lane >= d) out += t;" in hip
    assert "for (int k = 0; k < lanes; k++) {\n        double scale" in cuda


@pytest.mark.parametrize(("op", "pick"), [("reduce_min", "fminf"), ("reduce_max", "fmaxf")])
def test_a_warp_min_or_max_takes_the_c_function_and_is_exact_in_lane_0(op: str, pick: str):
    row = next(r for r in simt.rows() if r.op == op)

    sut = simt.program(row, "cuda")

    assert f"out = {pick}(out, __shfl_down_sync(0xffffffffu, out, d));" in sut and row.tol == 0.0
    assert row.check == "first"


def test_a_nan_on_any_lane_stays_the_programs_worst_error():
    row = next(r for r in simt.rows() if r.op == "rsqrt")

    sut = simt.program(row, "cuda")

    assert "if (rel != rel || rel > worst) worst = rel;" in sut


@pytest.mark.parametrize("op", ["reduce_add", "reduce_min", "reduce_max", "scan_add", "atomic_add", "gen_mask"])
def test_a_cross_lane_rows_inputs_tell_its_result_from_an_untouched_output(op: str):
    row = next(r for r in simt.rows() if r.op == op)
    lo, hi = row.domain

    for lanes in simt.LANES.values():
        values = [lo + (hi - lo) * (k + 0.5) / lanes for k in range(lanes)]
        positive = sum(v > 0 for v in values)
        assert sum(values) != 0.0
        assert positive != lanes - positive


@pytest.mark.parametrize(
    "argv",
    [
        ["kernel", "tensix", "sin", "f32", "--max-ulp", "2"],
        ["kernel", "avx2", "sin", "f64", "--level", "fast", "--max-ulp", "2"],
        ["kernel", "avx2", "foo", "f64"],
        ["lookup", "avx2", "foo", "f64", "--json", "--no-verify"],
    ],
)
def test_a_request_the_tool_cannot_answer_prints_nothing_to_stdout(argv: list[str], capsys: pytest.CaptureFixture[str]):
    assert main(argv) == 2

    printed = capsys.readouterr()
    assert printed.out == "" and printed.err.startswith("alloy.isa: ")


def test_the_lookup_prints_the_dialects_spelling_and_its_check(capsys: pytest.CaptureFixture[str]):
    assert main(["lookup", "hip", "gen_mask", "f32"]) == 0

    printed = capsys.readouterr().out
    assert "__popcll(__ballot(v > 0.0f))" in printed
    recorded = simt.verdicts()[("gen_mask", "hip")]
    assert f"verified: {recorded.basis}" in printed  # the recorded check, word for word
    assert "ran on gfx90a" in recorded.basis and "ran on gfx942" in recorded.basis


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


def test_a_row_run_on_a_second_gpu_keeps_the_first_gpus_run_and_the_worse_error():
    mi250x = simt.Verdict("fma", "hip", "ran on gfx90a", ok=True, rel=1e-7)
    mi300a = simt.Verdict("fma", "hip", "ran on gfx942", ok=True, rel=2e-7)

    sut = simt.merged(mi300a, mi250x)

    assert sut == simt.Verdict("fma", "hip", "ran on gfx942; ran on gfx90a", ok=True, rel=2e-7)
    assert simt.merged(sut, mi250x) == sut, "a rerun on one GPU does not repeat it"
    failed = simt.merged(mi300a, simt.Verdict("fma", "hip", "ran on gfx90a", ok=False, rel=0.5))
    assert (failed.ok, failed.rel) == (False, 0.5), "a row correct on one GPU and wrong on another is wrong"
    compiled = simt.Verdict("fma", "hip", "compiled for gfx90a, gfx942, not run (no such GPU here)")
    assert simt.merged(mi300a, compiled) == mi300a, "a compile-only record adds no run"
