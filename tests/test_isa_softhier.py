# Copyright 2026 ETH Zurich and the Alloy authors.
"""The SoftHier v1 rows: each one recorded as run on GVSoC, the planted wrong rows recorded as failed, the lookup
answering from those records with code that builds alone, and the programs the harness runs."""

import dataclasses
import os
import pathlib
import re
import shutil

import pytest

from alloy.isa import softhier, softhier_harness
from alloy.isa.__main__ import main
from alloy.isa.ask import Check, Completion, Feasible, Infeasible, Invalid, Operand, Request, Why, ask


def shared(dtype: str, *shape: int) -> Operand:
    return Operand("shared", dtype, shape)


def test_every_row_at_every_dtype_has_a_passing_gvsoc_run_of_its_current_code():
    verdicts = softhier.verdicts()

    for row in softhier.rows():
        for dtype in row.dtypes:
            verdict = softhier.verdict_of(row, dtype)
            assert verdict is not None, (row.key(), dtype)
            assert verdict.ok, (row.key(), dtype, verdict.error)
    assert len(verdicts) == len(softhier.harness_rows(with_planted=False))
    assert softhier.recorded()["sdk"] == softhier.PINS["sdk"] and softhier.recorded()["gvsoc"] == softhier.PINS["gvsoc"]


def test_every_planted_wrong_row_was_run_and_failed_its_check():
    """The checks can fail: a vfsub spelled as add, and a 2D copy with its strides swapped, both ran and were caught."""
    planted = softhier.recorded()["planted"]

    assert {p["name"] for p in planted} == set(softhier.PLANTED)
    assert len(planted) == sum(len(r.dtypes) for r in softhier.planted())
    assert all(p["ok"] is False and p["error"] for p in planted), planted


def test_a_record_of_a_row_changed_since_its_run_is_stale_and_left_out(tmp_path: pathlib.Path):
    add = next(r for r in softhier.rows() if r.op == "add")
    current = softhier.Verdict("add", "f32", ok=True, rel=0.0, digest=softhier.digest(add, "f32"))
    changed = softhier.Verdict("add", "f16", ok=True, rel=0.0, digest="0123456789abcdef")
    path = tmp_path / "verified.toml"
    path.write_text(softhier.verdicts_text([current, changed], [], "2026-11-18"))

    sut = softhier.verdicts(path)

    assert sut == {("add", "f32"): current}


def test_a_wait_row_is_checked_by_the_program_of_the_row_that_issues_its_work():
    waits = [r for r in softhier.rows() if r.op == "wait"]

    assert {r.key() for r in waits} == {"wait_idma", "wait_redmule"}
    for wait in waits:
        issuer = next(r for r in softhier.rows() if r.key() == wait.checked_by)
        body = "\n".join(line for line in wait.code.strip().splitlines() if not line.startswith("#include"))
        assert body in issuer.code, wait.key()
    assert not {r["name"] for r in softhier.harness_rows()} & {w.key() for w in waits}


def test_each_planted_row_changes_exactly_one_call_of_a_real_row():
    by_key = {r.key(): r for r in softhier.rows()}

    for name, (real, right, wrong) in softhier.PLANTED.items():
        sut = next(r for r in softhier.planted() if r.key() == name)
        assert by_key[real].code.count(right) == 1
        assert sut.code == by_key[real].code.replace(right, wrong) and sut.kind == by_key[real].kind


def test_the_architecture_file_holds_every_configuration_value_as_the_sdk_config_script_reads_it():
    sut = softhier.arch()

    found = dict(re.findall(r"^\s*self\.(\w+)\s*=\s*(.+)$", sut, re.MULTILINE))
    assert set(found) == set(softhier.config())
    assert found["num_cluster_x"] == "2" and found["hbm_chan_placement"] == "[2, 0, 0, 2]"
    assert int(found["cluster_tcdm_size"], 16) == 1 << 20


def test_vlmax_at_lmul_8_is_vlen_times_8_over_the_element_bits():
    assert softhier.vlmax("f32") == 64 and softhier.vlmax("f16") == 128


@pytest.mark.parametrize("dtype", ["f32", "f16"])
def test_a_vector_answer_strip_mines_with_vsetvl_and_answers_the_tail_without_a_mask(dtype: str):
    answer = ask(Request("softhier", "add", {"x": shared(dtype, 300), "y": shared(dtype, 300)}), verify=False)

    assert isinstance(answer, Feasible), answer
    lanes = softhier.vlmax(dtype)
    strips = -(-300 // lanes)
    assert answer.unit == "spatz"
    assert answer.steps[0].spelling == f"__riscv_vsetvl_e{dtype[1:]}m8(n - i)" and answer.steps[0].count == strips
    assert f"__riscv_vfadd_vv_{dtype}m8" in answer.steps[1].spelling
    assert any(f"{300 - (strips - 1) * lanes} elements, is the tail" in note for note in answer.notes)


def test_an_answer_includes_only_toolchain_and_sdk_headers_that_its_setup_names():
    """The code compiles alone with the build line: no Alloy header it does not show."""
    requests = [Request("softhier", "fma", {"x": shared("f16", 64)}),
                Request("softhier", "copy", {"src": Operand("global", "f32", (64, 64)), "dst": shared("f32", 32, 64)}),
                Request("softhier", "mma", {"a": shared("f16", 32, 64), "b": shared("f16", 64, 32),
                                            "c": shared("f16", 32, 32)})]  # fmt: skip

    for request in requests:
        answer = ask(request, verify=False)
        assert isinstance(answer, Feasible), answer
        includes = re.findall(r'#include [<"]([^>"]+)[>"]', answer.code)
        assert includes and all(h == "riscv_vector.h" or h.startswith("flex_") for h in includes), includes
        assert answer.setup["build"] == softhier.build_line() and "-c alloy.c" in answer.setup["build"]
        assert "config.py alloy_v1.py --output-dir $SOFTHIER_SDK/runtime/runtime/include" in answer.setup["arch"]
        assert answer.setup["run"].startswith("SOFTHIER_ARCH_FILE=alloy_v1.py gvsoc --target=")


def test_the_v1_header_replaces_the_sdks_own_because_the_sdk_headers_include_it_beside_themselves():
    """A -I folder ahead of the SDK's does not win over a quoted include; a stale header broke the global barrier."""
    assert softhier.ARCH_HEADER.endswith("--output-dir $SOFTHIER_SDK/runtime/runtime/include")
    for line in (softhier.build_line(), softhier.link_line()):
        assert re.findall(r"-I (\S+)", line) == ["$SOFTHIER_SDK/runtime/runtime/include"]


def test_a_copy_of_a_block_of_hbm_into_tcdm_is_a_2d_idma_copy_that_completes_on_its_wait():
    request = Request("softhier", "copy", {"src": Operand("global", "f32", (64, 256)), "dst": shared("f32", 32, 16)})

    answer = ask(request, verify=False)

    assert isinstance(answer, Feasible), answer
    assert answer.unit == "idma" and answer.completion == Completion("idma", "wait on=idma")
    call = answer.steps[0].spelling
    assert call.startswith("alloy_copy_2d(local(offset), hbm_west(node, offset) + (row0 * 256 + col0) * 4,")
    assert call.endswith(", 64, 64, 1024, 32)")  # row bytes, dst stride (packed), src stride (the matrix row), rows


def test_a_store_of_a_tcdm_block_into_an_hbm_matrix_strides_the_destination():
    request = Request("softhier", "copy", {"src": shared("f16", 8, 32), "dst": Operand("global", "f16", (128, 128))})

    answer = ask(request, verify=False)

    assert isinstance(answer, Feasible), answer
    assert answer.steps[0].spelling.endswith(", 64, 256, 64, 8)")


def test_a_contiguous_copy_is_one_1d_transfer_of_its_bytes():
    request = Request("softhier", "copy", {"src": shared("f32", 300), "dst": Operand("global", "f32", (300,))})

    answer = ask(request, verify=False)

    assert isinstance(answer, Feasible), answer
    assert answer.steps[0].spelling == "alloy_copy_1d(hbm_west(node, offset), local(offset), 1200)"


def test_a_copy_between_two_tcdm_tiles_is_not_covered_by_the_checked_rows():
    request = Request("softhier", "copy", {"src": shared("f32", 64), "dst": shared("f32", 64)})

    answer = ask(request, verify=False)

    assert isinstance(answer, Infeasible) and answer.why is Why.SPACE


def test_an_mma_runs_on_redmule_with_its_extents_in_redmule_order_and_completes_on_its_wait():
    request = Request("softhier", "mma", {"a": shared("f16", 24, 40), "b": shared("f16", 40, 72),
                                          "c": shared("f16", 24, 72)})  # fmt: skip

    answer = ask(request, verify=False)

    assert isinstance(answer, Feasible), answer
    assert answer.unit == "redmule" and answer.completion == Completion("redmule", "wait on=redmule")
    assert answer.steps[0].spelling == "flex_redmule_config(24, 40, 72)"
    assert "flex_redmule_config(m, k, n);" in answer.code


def test_an_f32_mma_is_refused_with_the_f16_product_of_the_same_shape():
    request = Request("softhier", "mma", {"a": shared("f32", 32, 32), "b": shared("f32", 32, 32),
                                          "c": shared("f32", 32, 32)})  # fmt: skip

    answer = ask(request, verify=False)

    assert isinstance(answer, Infeasible) and answer.why is Why.ELEMENT_TYPE
    assert answer.nearest == ("a shared:f16:32x32, b shared:f16:32x32, c shared:f16:32x32",)


def test_vector_data_in_hbm_is_refused_with_the_idma_copy_into_tcdm_as_the_fix():
    answer = ask(Request("softhier", "mul", {"x": Operand("global", "f32", (512,))}), verify=False)

    assert isinstance(answer, Infeasible) and answer.why is Why.SPACE
    assert answer.nearest == ("x shared:f32:512",) and "ask softhier copy" in answer.fix


@pytest.mark.parametrize(("on", "call"), [("idma", "flex_dma_async_wait_all()"), ("redmule", "flex_redmule_wait()")])
def test_each_completion_token_has_a_wait_and_softhier_needs_no_fence(on: str, call: str):
    wait = ask(Request("softhier", "wait", on=on), verify=False)
    fence = ask(Request("softhier", "fence", kind="proxy"), verify=False)

    assert isinstance(wait, Feasible) and wait.steps[0].spelling == call
    assert isinstance(fence, Infeasible) and fence.why is Why.NO_ROW and "wait on=idma" in fence.nearest


def test_a_barrier_names_its_scope():
    cluster = ask(Request("softhier", "barrier", kind="cluster"), verify=False)
    nameless = ask(Request("softhier", "barrier"), verify=False)

    assert isinstance(cluster, Feasible) and cluster.steps[0].spelling == "flex_intra_cluster_sync()"
    assert isinstance(nameless, Invalid) and nameless.expected == ("barrier kind=cluster", "barrier kind=global")


def test_a_double_buffered_copy_and_mma_list_is_refused_without_the_waits_it_needs():
    from alloy.isa.ask import ask_all

    copy = Request("softhier", "copy", {"src": Operand("global", "f16", (64, 64)), "dst": shared("f16", 64, 64)})
    mma = Request(
        "softhier", "mma", {"a": shared("f16", 64, 64), "b": shared("f16", 64, 64), "c": shared("f16", 64, 64)}
    )
    wait = Request("softhier", "wait", on="redmule")

    answer = ask_all([copy, mma, wait], verify=False)

    assert isinstance(answer, Infeasible) and answer.why is Why.ORDER and "wait on=idma" in answer.reason


def test_a_failed_record_refuses_the_row_and_a_missing_one_leaves_it_unverified(monkeypatch: pytest.MonkeyPatch):
    add = next(r for r in softhier.rows() if r.op == "add")
    request = Request("softhier", "add", {"x": shared("f32", 64)})
    monkeypatch.setattr(softhier, "verdict_of", lambda row, dtype: None)
    missing = ask(request, verify=False)
    failed = softhier.Verdict("add", "f32", ok=False, rel=1.0, error="max error 1 over max |reference| > 1e-06")
    monkeypatch.setattr(softhier, "verdict_of", lambda row, dtype: failed if row == add else None)

    refused = ask(request, verify=False)

    assert isinstance(missing, Feasible) and missing.check.status == "unverified"
    assert isinstance(refused, Infeasible) and refused.why is Why.CHECK_FAILED and "1e-06" in refused.reason


def test_a_recorded_run_is_the_answers_check(monkeypatch: pytest.MonkeyPatch):
    ran = softhier.Verdict("reduce_add", "f32", ok=True, rel=3e-7)
    monkeypatch.setattr(softhier, "verdict_of", lambda row, dtype: ran)

    answer = ask(Request("softhier", "reduce_add", {"x": shared("f32", 300)}), verify=False)

    assert isinstance(answer, Feasible)
    assert answer.check == Check("run", f"GVSoC {softhier.TARGET}, SoftHier v1, max rel error 3e-07")


def test_the_lookup_prints_a_rows_code_and_build_line_and_refuses_an_element_type_without_a_row(
    capsys: pytest.CaptureFixture[str],
):
    assert main(["lookup", "softhier", "reduce_max", "f16"]) == 0
    printed = capsys.readouterr().out
    assert "_Float16 alloy_reduce_max_f16(const _Float16* x, size_t n)" in printed
    assert f"build: {softhier.build_line()}" in printed

    assert main(["lookup", "softhier", "add", "f64"]) == 2
    assert "the add rows are f16, f32" in capsys.readouterr().err


@pytest.mark.parametrize(("op", "dtype", "taken"), [("mma", "f32", "f16"), ("wait", "f32", None)])
def test_only_a_row_of_untyped_data_answers_any_element_type(op: str, dtype: str, taken: str | None,
                                                          capsys: pytest.CaptureFixture[str]):  # fmt: skip
    """RedMulE multiplies f16: an f32 lookup is refused with the type it takes; a wait moves no data."""
    code = main(["lookup", "softhier", op, dtype])

    if taken is None:
        assert code == 0 and "wait_idma on idma" in capsys.readouterr().out
    else:
        assert code == 2 and f"the {op} rows are {taken}" in capsys.readouterr().err


def test_the_harness_program_runs_the_rows_code_verbatim_inside_the_sdk_frame():
    for row in softhier.harness_rows():
        source, _ = softhier_harness.program(row)
        assert row["code"].strip() in source, row["name"]
        assert source.index("flex_barrier_xy_init();") < source.index("flex_eoc(0);")
        if row["kind"] in ("binary", "fma", "move", "reduction", "sync_cluster", "barrier_global"):
            assert f"{row['fn']}(" in source.split("int main()")[1], row["name"]


def test_the_2d_check_gathers_the_block_and_scatters_it_back_into_zeros():
    row = next(r for r in softhier.harness_rows() if r["name"] == "copy_2d")

    source, expected = softhier_harness.program(row)

    rows, cols = softhier_harness.BLOCK
    block, scattered = expected[: rows * cols], expected[rows * cols :]
    assert len(scattered) == softhier_harness.ROWS * softhier_harness.COLS
    assert sum(1 for w in scattered if w) <= rows * cols and set(block) <= set(scattered)
    assert source.count("alloy_copy_2d(") == 2 + 1  # the definition and two calls


def test_the_reference_of_the_product_accumulates_a_times_b_into_c():
    row = next(r for r in softhier.harness_rows() if r["name"] == "mma")
    m, n, k = softhier_harness.MMA

    sut = softhier_harness.reference(row)

    a, b, c = (softhier_harness.draw("mma", "f16", count, seed) for seed, count in enumerate((m * k, k * n, m * n)))
    assert len(sut) == m * n
    assert sut[n + 1] == pytest.approx(c[n + 1] + sum(a[k + p] * b[p * n + 1] for p in range(k)))


def test_a_result_off_by_one_f32_ulp_passes_the_add_bound_and_one_off_by_a_thousandth_does_not():
    row = next(r for r in softhier.harness_rows() if (r["name"], r["dtype"]) == ("add", "f32"))
    want = softhier_harness.reference(row)
    exact = [softhier_harness.bits(x, "f32") for x in want]
    nudged = [*exact[:-1], exact[-1] + 1]
    wrong = [*exact[:-1], softhier_harness.bits(want[-1] + 0.001 * max(map(abs, want)), "f32")]

    assert softhier_harness.compare(row, nudged, [])[0] is True
    assert softhier_harness.compare(row, wrong, [])[0] is False


@pytest.mark.softhier
def test_every_row_runs_correct_on_gvsoc_and_every_planted_row_fails():
    """In the SoftHier v1 image (SOFTHIER_IMAGE, helpers/build_softhier_image.sh), or on a GVSoC installed here."""
    image = os.environ.get("SOFTHIER_IMAGE")
    if image and shutil.which("singularity") is None:
        pytest.skip("SOFTHIER_IMAGE is set but singularity is not on PATH")
    if not image and not (os.environ.get("SOFTHIER_GVSOC") and os.environ.get("SOFTHIER_SDK")):
        pytest.skip("GVSoC is absent: set SOFTHIER_IMAGE, or SOFTHIER_GVSOC and SOFTHIER_SDK (alloy/isa/softhier.py)")

    found, wrong = softhier.parsed(softhier.run_harness(image=pathlib.Path(image) if image else None))

    assert len(found) == len(softhier.harness_rows(with_planted=False))
    assert all(v.ok for v in found), [dataclasses.asdict(v) for v in found if not v.ok]
    assert wrong and not any(v.ok for v in wrong), wrong


def vector_row(op: str, dtype: str) -> dict:
    return next(r for r in softhier.harness_rows() if (r["name"], r["dtype"]) == (op, dtype))


def words_of(values: list[float], dtype: str) -> list[int]:
    return [softhier_harness.bits(softhier_harness.rounded(x, dtype), dtype) for x in values]


@pytest.mark.parametrize("dtype", ["f32", "f16"])
def test_a_reduction_that_drops_the_tail_strip_or_five_terms_fails_its_check(dtype: str):
    """The tail strip holds the largest terms: a sum or maximum without it, or a sum short of five terms, is caught."""
    xs = softhier_harness.vector_inputs("reduce_add", dtype, 1)[0]
    tail = softhier_harness.TAIL
    total, maximum = vector_row("reduce_add", dtype), vector_row("reduce_max", dtype)

    assert softhier_harness.compare(total, words_of([sum(xs)], dtype), [])[0] is True
    assert softhier_harness.compare(total, words_of([sum(xs[:-tail])], dtype), [])[0] is False
    assert softhier_harness.compare(total, words_of([sum(xs[5:])], dtype), [])[0] is False
    assert softhier_harness.compare(maximum, words_of([max(xs[:-tail])], dtype), [])[0] is False
    assert maximum["tol"] == 0.0


@pytest.mark.parametrize("dtype", ["f32", "f16"])
def test_an_fma_that_rounds_the_product_first_fails_its_check(dtype: str):
    """The row claims one rounding: its probes are a power of two fused and 0 unfused."""
    row = vector_row("fma", dtype)
    a, b, c = softhier_harness.vector_inputs("fma", dtype, 3)
    fused = [a_ * b_ + c_ for a_, b_, c_ in zip(a, b, c, strict=True)]
    unfused = [softhier_harness.rounded(a_ * b_, dtype) + c_ for a_, b_, c_ in zip(a, b, c, strict=True)]

    assert softhier_harness.compare(row, words_of(fused, dtype), [])[0] is True
    assert softhier_harness.compare(row, words_of(unfused, dtype), [])[0] is False


def test_the_product_bound_is_a_few_times_the_error_measured_on_gvsoc():
    measured = 2.2130849714876254e-4  # the mma run of 2026-11-18, before this bound

    assert measured < vector_row("mma", "f16")["tol"] <= 5 * measured


def test_each_planted_row_without_its_tail_strip_loops_only_over_whole_strips():
    for name in ("planted_reduce_add_without_tail", "planted_reduce_max_without_tail"):
        sut = next(r for r in softhier.planted() if r.key() == name)
        assert "i + __riscv_vsetvlmax_e32m8() <= n;" in softhier.code(sut, "f32")


@pytest.mark.parametrize(("src", "dst"), [((300,), (16, 16)), ((300,), (200,)), ((16, 16), (64,))])
def test_a_copy_between_a_vector_and_a_matrix_or_runs_of_unequal_length_is_refused(src, dst):
    """No block of rows to take: the copy is refused for its shape, never an IndexError."""
    request = Request("softhier", "copy", {"src": Operand("global", "f32", src), "dst": shared("f32", *dst)})

    answer = ask(request, verify=False)

    assert isinstance(answer, Infeasible) and answer.why is Why.SHAPE


def test_a_packed_tile_of_as_many_elements_as_a_run_is_one_run():
    request = Request("softhier", "copy", {"src": Operand("global", "f32", (256,)), "dst": shared("f32", 16, 16)})

    answer = ask(request, verify=False)

    assert isinstance(answer, Feasible) and answer.steps[0].spelling.endswith(", 1024)")


def test_whole_rows_of_a_matrix_are_one_run_that_starts_at_their_first_row():
    request = Request("softhier", "copy", {"src": Operand("global", "f32", (64, 32)), "dst": shared("f32", 8, 32)})

    answer = ask(request, verify=False)

    assert isinstance(answer, Feasible), answer
    assert answer.steps[0].spelling == "alloy_copy_1d(local(offset), hbm_west(node, offset) + row0 * 128, 1024)"


@pytest.mark.parametrize(("op", "names"), [("reduce_add", ("x", "y")), ("add", ("a", "b", "c")), ("fma", ("x", "y"))])
def test_a_vector_request_with_operands_its_row_does_not_take_is_invalid(op: str, names: tuple[str, ...]):
    answer = ask(Request("softhier", op, {name: shared("f32", 64) for name in names}), verify=False)

    assert isinstance(answer, Invalid) and answer.why is Why.OPERANDS


def test_a_reduction_of_no_elements_is_invalid():
    answer = ask(Request("softhier", "reduce_max", {"x": shared("f32", 0)}), verify=False)

    assert isinstance(answer, Invalid) and answer.why is Why.MALFORMED
