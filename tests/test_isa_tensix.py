# Copyright 2026 ETH Zurich and the Alloy authors.
"""The Tensix rows: each one recorded as run on ttsim, the lookup answering from those records, and the kernel the
harness builds spelled for the tt-metal version it targets."""

import os
import pathlib
import shutil

import pytest

from alloy.isa import tensix, tensix_harness
from alloy.isa.__main__ import main


def test_every_row_at_each_of_its_dtypes_has_a_passing_run_on_the_pinned_image() -> None:
    verdicts = tensix.verdicts()

    for row in tensix.rows():
        for dtype in tensix.row_dtypes(row):
            if row.pending:  # run by the tensix CI job (below), recorded by the next `verify`
                assert (row.op, dtype, row.unit) not in verdicts
                continue
            verdict = verdicts[(row.op, dtype, row.unit)]
            assert verdict.ok, (row.op, dtype, row.unit, verdict.error)
    assert tensix.recorded()["image"] == tensix.IMAGE


def test_a_record_of_a_row_changed_since_its_run_is_stale_and_left_out(tmp_path: pathlib.Path) -> None:
    exp = next(r for r in tensix.rows() if r.op == "exp")
    current = tensix.Verdict("exp", "f32", exp.unit, ok=True, rel=1e-7, digest=tensix.digest(exp, "f32"))
    changed = tensix.Verdict("exp", "bf16", exp.unit, ok=False, rel=0.5, digest="0123456789abcdef")
    path = tmp_path / "verified.toml"
    library = tmp_path / "libttsim.so"
    library.write_bytes(b"sim")
    path.write_text(tensix.verdicts_text([current, changed], library, tensix.IMAGE))

    sut = tensix.verdicts(path)

    assert sut == {("exp", "f32", exp.unit): current}


def test_every_card_record_is_of_a_current_row_and_its_verdict_follows_the_rows_bound() -> None:
    recorded = tensix.recorded(tensix.CARD_PATH)["verdicts"]

    sut = tensix.card_verdicts()

    assert len(sut) == len(recorded)
    for verdict in sut.values():
        assert verdict.ok == (verdict.rel is not None and verdict.rel < tensix.TOLERANCE[verdict.dtype]), verdict


def test_the_lookup_prints_the_card_measurement_beside_the_ttsim_run(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["lookup", "tensix", "log", "f32"])

    out = capsys.readouterr().out
    assert code == 0
    assert "verified on ttsim" in out
    assert "measured on a Blackhole card with tt-metal 0.63, the [v06] spelling" in out
    assert "max abs error 0.0165 (OUTSIDE the row's bound" in out


def test_an_fpu_add_reads_tf32_operands_and_an_sfpu_add_keeps_f32() -> None:
    verdicts = tensix.verdicts()

    fpu, sfpu = verdicts[("add", "f32", "FPU")], verdicts[("add", "f32", "SFPU")]

    assert fpu.rel is not None and sfpu.rel is not None
    assert fpu.rel > 1e-5 > 1e-6 > sfpu.rel


def test_the_lookup_offers_both_units_of_an_op_with_their_recorded_errors(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["lookup", "tensix", "add", "f32"]) == 0

    printed = capsys.readouterr().out
    assert "FPU (binary)" in printed and "SFPU (binary_sfpu)" in printed
    assert "init: add_tiles_init(c0, c1)" in printed and "add_init(c0, c1)" not in printed  # the card's 0.63 only
    assert printed.count("verified on ttsim") == 2


@pytest.mark.parametrize(
    ("ok", "code", "said"), [(None, 0, "unverified: no recorded run"), (False, 2, "FAILED on ttsim")]
)
def test_the_lookup_exits_2_only_for_a_failed_run_not_for_a_missing_one(
    ok: bool | None, code: int, said: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    row = next(r for r in tensix.rows() if r.op == "exp")
    found = {} if ok is None else {("exp", "f32", row.unit): tensix.Verdict("exp", "f32", row.unit, ok, 0.5, "off")}
    monkeypatch.setattr(tensix, "verdicts", lambda: found)

    assert main(["lookup", "tensix", "exp", "f32"]) == code

    assert said in capsys.readouterr().out


def test_the_lookup_refuses_f64_because_tensix_has_none(capsys: pytest.CaptureFixture[str]) -> None:
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
def test_the_compute_kernel_is_spelled_for_its_tt_metal_version(new: bool, spelled: list[str], absent: str) -> None:
    row = next(r for r in tensix.harness_rows() if (r["op"], r["unit"]) == ("add", "FPU"))

    sut = tensix_harness.compute(row, new)

    assert all(text in sut for text in spelled), sut
    assert absent not in sut


def test_the_root_header_of_tt_metal_06_is_not_under_compute_kernel_api() -> None:
    assert tensix_harness.compute_include("compute_kernel_api.h", new=False) == "compute_kernel_api.h"
    assert tensix_harness.compute_include("eltwise_unary/exp.h", new=False) == "compute_kernel_api/eltwise_unary/exp.h"


@pytest.mark.tensix
def test_every_row_runs_correct_on_ttsim(tmp_path_factory: pytest.TempPathFactory) -> None:
    if shutil.which("docker") is None:
        pytest.fail("the tensix mark needs docker")
    library = tensix.ttsim(tmp_path_factory.mktemp("ttsim"))

    found = tensix.run_harness(library, tensix.IMAGE)

    if out := os.environ.get("ALLOY_TENSIX_VERDICTS"):  # the CI job uploads it: the record `verify` would write
        pathlib.Path(out).write_text(tensix.verdicts_text(found, library, tensix.IMAGE))
    assert len(found) == sum(len(tensix.row_dtypes(row)) for row in tensix.rows())
    assert all(v.ok for v in found), [v for v in found if not v.ok]


@pytest.mark.parametrize(("new", "spelled"), [
    (True, ["compute_kernel_hw_startup<SrcOrder::Reverse>(c0, c1, c16); matmul_init(c0, c1);",
            "matmul_tiles(c0, c1, 0, 0, 0);", '#include "api/compute/src_order.h"']),
    (False, ["mm_init(c0, c1, c16);", "matmul_tiles(c0, c1, 0, 0, 0, false);"]),
])  # fmt: skip
def test_the_matmul_kernel_accumulates_every_k_tile_into_one_dst_tile(new: bool, spelled: list[str]) -> None:
    row = next(r for r in tensix.harness_rows() if r["op"] == "mma")

    sut = tensix_harness.compute(row, new)

    assert all(text in sut for text in spelled), sut
    assert sut.count("pack_tile(0, c16)") == 1 and "for (uint32_t kt = 0; kt < num_tiles; ++kt)" in sut


@pytest.mark.parametrize("op", ["add", "sub", "mul", "div"])
def test_the_reference_of_an_elementwise_row_takes_tiles_that_do_not_chain_as_a_product(op: str) -> None:
    import torch

    x, y = torch.full((64, 32), 6.0), torch.full((64, 32), 3.0)

    sut = tensix_harness.reference(op, [x, y])

    assert sut.shape == (64, 32)
    assert sut[0, 0].item() == {"add": 9.0, "sub": 3.0, "mul": 18.0, "div": 2.0}[op]


def test_the_reference_of_an_mma_row_is_the_matrix_product() -> None:
    import torch

    sut = tensix_harness.reference("mma", [torch.ones(32, 64), torch.ones(64, 32)])

    assert sut.shape == (32, 32) and sut[0, 0].item() == 64.0


@pytest.mark.parametrize(("row", "expected"), [
    ({"dtype": "bf16", "kind": "matmul"}, True),
    ({"dtype": "f32", "kind": "matmul"}, True),
    ({"dtype": "f32", "kind": "unary"}, True),
    ({"dtype": "bf16", "kind": "unary"}, False),
    ({"dtype": "bf16", "kind": "binary"}, False),
])  # fmt: skip
def test_a_matrix_product_accumulates_in_fp32_for_every_element_type_as_ask_tells_the_caller(
    row: dict[str, str], expected: bool
) -> None:
    from alloy.isa.ask import Feasible, Operand, Request, ask

    assert tensix_harness.dest_fp32(row) is expected

    tile = Operand("tile_register", row["dtype"], (32, 32))
    answer = ask(Request("tensix", "mma", {"a": tile, "b": tile, "c": tile}), verify=False)
    assert isinstance(answer, Feasible), answer
    assert "fp32_dest_acc_en = true" in answer.setup["compute config"]


@pytest.mark.parametrize(("new", "spelled"), [
    (True, ['#include "api/compute/reduce.h"', "void kernel_main()"]),
    (False, ['#include "compute_kernel_api/reduce.h"', "void MAIN"]),
])  # fmt: skip
def test_the_reduction_kernel_reduces_every_tile_into_one_dst_tile_against_one_scaler_tile(
    new: bool, spelled: list[str]
) -> None:
    row = next(r for r in tensix.harness_rows() if r["op"] == "reduce_add")

    sut = tensix_harness.compute(row, new)

    assert all(text in sut for text in spelled), sut
    assert "#define REDUCE_OP PoolType::SUM\n#define REDUCE_DIM ReduceDim::REDUCE_SCALAR" in sut
    assert sut.index("#define REDUCE_OP") < sut.index("reduce.h")  # 0.6x's template defaults name the macros
    assert sut.count("cb_wait_front(c1, 1)") == 1 and sut.count("pack_tile(0, c16)") == 1
    assert sut.index("reduce_tile<") < sut.index("pack_tile(0, c16)") < sut.index("reduce_uninit()")


def test_the_reader_of_a_reduction_reads_the_scaler_tile_once() -> None:
    sut = tensix_harness.reader([0, 3], new=True, once=1)

    assert sut.count("if (i == 0) {") == 1
    assert sut.index("if (i == 0) {") < sut.index("cb_reserve_back(1, 1)")
    assert sut.index("cb_reserve_back(0, 1)") < sut.index("if (i == 0) {")


def test_the_scan_kernel_inits_once_and_marks_only_the_first_tile_of_a_column() -> None:
    row = next(r for r in tensix.harness_rows() if r["op"] == "scan_add")

    sut = tensix_harness.compute(row, new=True)

    assert sut.count("cumsum_tile_init()") == 1
    assert sut.index("cumsum_tile_init()") < sut.index("for (uint32_t i = 0") < sut.index("cumsum_tile(0, i == 0)")
    assert sut.index("copy_tile(c0, 0, 0)") < sut.index("cumsum_tile(0, i == 0)")


def test_the_scaler_tile_holds_one_in_the_first_row_of_each_face() -> None:
    row = next(r for r in tensix.harness_rows() if r["op"] == "reduce_max")

    data, scaler = tensix_harness.inputs(row)

    assert data.shape == (tensix_harness.TILES * 32, 32) and scaler.shape == (32, 32)
    assert scaler.sum().item() == 64.0 and scaler[0].sum().item() == scaler[16].sum().item() == 32.0


@pytest.mark.parametrize(("op", "expected"), [("reduce_add", 2048.0), ("reduce_max", 1.0)])
def test_the_reference_of_a_reduction_is_one_value_over_every_tile(op: str, expected: float) -> None:
    import torch

    sut = tensix_harness.reference(op, [torch.ones(64, 32), torch.zeros(32, 32)])

    assert sut.numel() == 1 and sut.item() == expected


def test_the_reference_of_the_scan_runs_down_each_column_across_tiles() -> None:
    import torch

    sut = tensix_harness.reference("scan_add", [torch.ones(64, 32)])

    assert sut.shape == (64, 32)
    assert sut[31, 0].item() == 32.0 and sut[63, 5].item() == 64.0


@pytest.mark.parametrize("kind", ["reduction", "matmul"])
def test_a_reduction_accumulates_in_fp32_for_every_element_type_as_ask_tells_the_caller(kind: str) -> None:
    from alloy.isa.ask import Feasible, Operand, Request, ask

    assert tensix_harness.dest_fp32({"dtype": "bf16", "kind": kind}) is True

    data = Operand("tile_register", "bf16", (64, 32))
    answer = ask(Request("tensix", "reduce_add", {"x": data}), verify=False)
    assert isinstance(answer, Feasible), answer
    assert "fp32_dest_acc_en = true" in answer.setup["compute config"] and "scaler" in answer.setup


@pytest.mark.parametrize(("op", "shape", "tiles"), [("reduce_add", (64, 64), 4), ("reduce_max", (64, 64), 4),
                                                     ("scan_add", (64, 32), 2)])  # fmt: skip
def test_a_reduction_or_scan_row_is_offered_checked_on_ttsim_with_one_init_and_one_call_per_tile(
    op: str, shape: tuple[int, int], tiles: int
) -> None:
    from alloy.isa.ask import Check, Feasible, Operand, Request, ask

    answer = ask(Request("tensix", op, {"x": Operand("tile_register", "f32", shape)}), verify=False)

    assert isinstance(answer, Feasible), answer
    assert answer.check == Check("run", "ttsim")
    assert (answer.steps[0].count, answer.steps[1].count) == (1, tiles)
    assert [s.spelling for s in answer.steps].count("pack_tile(0, c16)") == (op != "scan_add")


def test_a_scan_over_more_than_one_column_of_tiles_is_refused_with_one_column_as_nearest() -> None:
    """cumsum_tile's first flag restarts the total at the top of one column; the check ran one column (reviewer C)."""
    from alloy.isa.ask import Infeasible, Operand, Request, Why, ask

    answer = ask(Request("tensix", "scan_add", {"x": Operand("tile_register", "f32", (64, 64))}), verify=False)

    assert isinstance(answer, Infeasible) and answer.why == Why.SHAPE
    assert answer.nearest == ("x tile_register:f32:64x32",)


def test_an_f32_tile_answer_carries_the_compute_config_its_check_ran_with_and_prefers_the_sfpu() -> None:
    from alloy.isa.ask import Feasible, Operand, Request, ask

    sfpu = ask(Request("tensix", "add", {"x": Operand("tile_register", "f32", (32, 32))}), verify=False)
    fpu = ask(Request("tensix", "add", {"x": Operand("tile_register", "f32", (32, 32))}, unit="fpu"), verify=False)

    assert isinstance(sfpu, Feasible) and sfpu.unit == "sfpu"
    assert (
        "fp32_dest_acc_en = true" in sfpu.setup["compute config"] and "UnpackToDestFp32" in sfpu.setup["compute config"]
    )
    assert isinstance(fpu, Feasible) and any("TF32" in note for note in fpu.notes)


def test_a_pending_row_is_offered_unverified_until_its_ttsim_run_is_recorded(monkeypatch: pytest.MonkeyPatch) -> None:
    import dataclasses

    from alloy.isa.ask import Feasible, Operand, Request, ask

    pending = tuple(dataclasses.replace(r, pending=True) if r.op == "scan_add" else r for r in tensix.rows())
    monkeypatch.setattr(tensix, "rows", lambda: pending)
    monkeypatch.setattr(tensix, "verdicts", dict)

    answer = ask(Request("tensix", "scan_add", {"x": Operand("tile_register", "f32", (32, 32))}), verify=False)

    assert isinstance(answer, Feasible), answer
    assert answer.check.status == "unverified" and "pending" in answer.check.basis


def test_a_tensix_minimum_is_refused_with_the_maximum_of_the_negation() -> None:
    from alloy.isa.ask import Infeasible, Operand, Request, Why, ask

    answer = ask(Request("tensix", "reduce_min", {"x": Operand("tile_register", "f32", (32, 32))}), verify=False)

    assert isinstance(answer, Infeasible) and answer.why is Why.NO_ROW
    assert answer.nearest == ("tensix neg", "tensix reduce_max") and "negative_tile" in answer.fix


def test_the_log_lookup_gives_the_card_checked_sfpi_kernel_beside_the_tile_call(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["lookup", "tensix", "log", "f32"]) == 0

    printed = capsys.readouterr().out
    assert "log_tile<false>(0)" in printed and "0.012 to 0.0165" in printed
    assert "SFPU math kernel alloy_log_f32_sfpi" in printed and "tt-metal 0.63, Blackhole p150" in printed
    kernel = printed.split("SFPU math kernel alloy_log_f32_sfpi", 1)[1]  # the rung's text pastes in: no includes
    assert "sfpi_inline sfpi::vFloat alloy_log_f32(sfpi::vFloat x)" in kernel and "#include" not in kernel


@pytest.mark.parametrize("op", ["log", "exp"])
def test_ask_with_a_bound_answers_the_sfpi_kernel_with_its_card_verdict_and_full_source(op: str) -> None:
    from alloy.isa.ask import Feasible, Operand, Request, ask

    answer = ask(Request("tensix", op, {"x": Operand("tile_register", "f32", (32, 32))}, max_ulp=8), verify=False)

    assert isinstance(answer, Feasible) and answer.unit == "sfpu"
    assert answer.check.status == "run" and answer.check.basis.startswith("card: tt-metal 0.63")
    assert f"inline void alloy_{op}_f32_face()" in answer.code and "#include" not in answer.code
    assert f"_llk_math_eltwise_unary_sfpu_params_<APPROX>(alloy_{op}_f32_face" in answer.steps[1].spelling
    assert any(note.startswith("dev: ") for note in answer.notes)


def test_ask_below_the_card_error_of_every_rung_is_refused_with_the_bound_that_holds() -> None:
    from alloy.isa import tensix
    from alloy.isa.ask import Infeasible, Operand, Request, Why, ask

    best = tensix.rungs("log", "f32")[0].error_ulp
    request = Request("tensix", "log", {"x": Operand("tile_register", "f32", (32, 32))}, max_ulp=best / 2)

    answer = ask(request, verify=False)

    assert isinstance(answer, Infeasible) and answer.why is Why.NO_RUNG
    assert answer.nearest == (f"max_ulp {best:.3g}",)


def test_the_plain_log_tile_answer_points_at_the_sfpi_rung() -> None:
    from alloy.isa.ask import Feasible, Operand, Request, ask

    answer = ask(Request("tensix", "log", {"x": Operand("tile_register", "f32", (32, 32))}), verify=False)

    assert isinstance(answer, Feasible) and any("alloy_log_f32_sfpi" in note for note in answer.notes)


def test_a_tensix_answer_prints_every_include_its_checked_kernels_use_at_the_cards_version(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["lookup", "tensix", "sin", "f32"]) == 0

    printed = capsys.readouterr().out
    assert (
        'includes compute: #include "compute_kernel_api/common.h"' in printed
        and '#include "compute_kernel_api/eltwise_unary/eltwise_unary.h"' in printed  # init_sfpu
        and 'reader/writer: #include "dataflow_api.h"' in printed
    )  # TensorAccessor at 0.6x, no tensor_accessor.h
    assert '"api/compute/' not in printed  # no tt-metal 0.8x spelling beside the card's (owner, 11-19)
    assert '#include "compute_kernel_api/eltwise_unary/trigonometry.h"' in printed  # the row's own header
