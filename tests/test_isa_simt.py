# Copyright 2026 ETH Zurich and the Alloy authors.
"""The CUDA and HIP rows: recorded checks, the dialect differences the lookup must keep, and the device runs."""

import dataclasses
from collections.abc import Callable

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


@pytest.mark.parametrize(("op", "pick"), [("reduce_min", min), ("reduce_max", max)])
def test_a_warp_min_or_max_finds_its_extreme_in_the_last_lane_so_it_crosses_the_whole_tree(
    op: str, pick: Callable[[list[float]], float]
):
    row = next(r for r in simt.rows() if r.op == op)
    lo, hi = row.domain

    for lanes in simt.LANES.values():
        values = [lo + (hi - lo) * (k + 0.5) / lanes for k in range(lanes)]
        assert values.index(pick(values)) == lanes - 1


def test_a_packed_half_addition_is_checked_in_both_halves():
    row = next(r for r in simt.rows() if r.op == "add_half2")

    for dialect in simt.DIALECTS:
        sut = row.spelled(dialect)
        assert "__low2float(h)" in sut and "__high2float(h)" in sut
    assert row.ref == "(a + c) + 2.0f * (b + a)", "the halves add different operands, so a swap shows"


def test_a_nan_on_any_lane_stays_the_programs_worst_error():
    row = next(r for r in simt.rows() if r.op == "rsqrt")

    sut = simt.program(row, "cuda")

    assert "if (rel != rel || rel > worst) worst = rel;" in sut


@pytest.mark.parametrize("op", ["reduce_add", "reduce_min", "reduce_max", "scan_add", "atomic_add", "ballot_count"])
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
    assert main(["lookup", "hip", "ballot_count", "f32"]) == 0

    printed = capsys.readouterr().out
    assert "__popcll(__ballot(v > 0.0f))" in printed
    recorded = simt.verdicts()[("ballot_count", "hip")]
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


def test_a_record_of_a_row_changed_since_its_check_is_stale_and_left_out(tmp_path):
    fma, rsqrt = (next(r for r in simt.rows() if r.op == op) for op in ("fma", "rsqrt"))
    current = simt.Verdict("fma", "cuda", "ran on a GPU", ok=True, rel=0.0, digest=simt.digest(fma, "cuda"))
    changed = simt.Verdict("rsqrt", "cuda", "ran on a GPU", ok=True, rel=0.0, digest="0123456789abcdef")
    path = tmp_path / "verified.toml"
    path.write_text(simt.verdicts_text([current, changed]))

    sut = simt.verdicts(path)

    assert sut == {("fma", "cuda"): current}
    assert simt.digest(rsqrt, "cuda") != changed.digest


def test_a_rows_digest_changes_with_its_spelling_and_its_check_but_not_its_note():
    row = next(r for r in simt.rows() if r.op == "reduce_add")
    respelled = dataclasses.replace(row, cuda=row.cuda.replace("+=", "-="))
    rechecked = dataclasses.replace(row, check="all")
    renoted = dataclasses.replace(row, note="another note")

    sut = simt.digest(row, "cuda")

    assert sut != simt.digest(respelled, "cuda") and sut != simt.digest(rechecked, "cuda")
    assert sut == simt.digest(renoted, "cuda")


@pytest.mark.parametrize("dtype", ["f16", "bf16"])
def test_each_half_type_has_a_scalar_a_pair_and_a_16_byte_load_and_store(dtype: str):
    sut = {row.answers() for row in simt.rows() if row.dtype == dtype}

    assert {"load", "store", "load_x2", "store_x2", "load_wide", "store_wide"} <= sut


@pytest.mark.parametrize(("op", "cuda", "hip"), [
    ("store_x2_bf16", "__floats2bfloat162_rn(a, b)", "__float22bfloat162_rn(make_float2(a, b))"),
    ("load_bf16", "__bfloat162float(x[i])", "__bfloat162float(x[i])"),
    ("store_f16", "__float2half_rn(a)", "__float2half_rn(a)"),
    ("load_x2_f16", "__half22float2(", "__half22float2("),
])  # fmt: skip
def test_a_half_row_spells_each_dialects_conversion(op: str, cuda: str, hip: str):
    row = next(r for r in simt.rows() if r.op == op)

    assert cuda in row.cuda and hip in row.hip


def test_a_half_rows_check_moves_the_rows_element_type_through_its_arrays():
    row = next(r for r in simt.rows() if r.op == "load_wide_bf16")

    sut = simt.program(row, "hip")

    assert "typedef __hip_bfloat16 elem;" in sut and "xs[k] = __float2bfloat16(A(k));" in sut
    assert "uint4 q = reinterpret_cast<const uint4*>(x)[i / 8]; out = __bfloat162float(" in sut


@pytest.mark.parametrize(("argv", "spelled"), [
    (["lookup", "cuda", "load_wide", "f16"], "uint4 q = reinterpret_cast<const uint4*>(x)[i / 8];"),
    (["lookup", "cuda", "add_half2", "f16"], "__hadd2("),
    (["lookup", "hip", "store", "bf16"], "y[i] = __float2bfloat16(a);"),
])  # fmt: skip
def test_the_lookup_answers_a_row_at_its_own_element_type(argv: list[str], spelled: str, capsys):
    assert main(argv) == 0

    assert spelled in capsys.readouterr().out


def test_the_lookup_names_the_element_types_a_row_has(capsys: pytest.CaptureFixture[str]):
    assert main(["lookup", "cuda", "fma", "f16"]) == 2

    assert "the fma rows are f32" in capsys.readouterr().err
