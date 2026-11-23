# Copyright 2026 ETH Zurich and the Alloy authors.
"""The unified ISA (notes/isa-design.md, step 1): every target answers Feasible, with its unit, steps, and check, or
Infeasible, with a reason and the nearest requests it takes, from the surfaces it wraps."""

import dataclasses
import json
import math
import pathlib
import subprocess

import pytest

from alloy.isa import ask as ask_module
from alloy.isa import simt, tensix, tile
from alloy.isa.__main__ import main
from alloy.isa.ask import (
    INVALID,
    UNITS,
    Check,
    Combined,
    Completion,
    Feasible,
    Infeasible,
    Invalid,
    Operand,
    Request,
    Space,
    Swizzle,
    Why,
    ask,
    ask_all,
)

TILE = {"a": Operand("shared", "f16", (64, 64), "row_major", "b128"),
        "b": Operand("shared", "f16", (64, 64), "col_major", "b128"), "c": Operand("register", "f32", (64, 64))}  # fmt: skip
MFMA_TILE = {"a": Operand("shared", "f16", (64, 64), "row_major", "xor:8"),
             "b": Operand("shared", "f16", (64, 64), "col_major", "xor:8"), "c": Operand("register", "f32", (64, 64))}  # fmt: skip


@pytest.mark.parametrize(("request_", "unit"), [
    (Request("avx2", "add", {"a": Operand("vector", "f64", (4,))}), "vector"),
    (Request("avx2", "exp", {"x": Operand("vector", "f32", (8,))}, max_ulp=4.0), "vector"),
    (Request("sm90", "mma", TILE), "warpgroup"),
    (Request("gfx942", "mma", MFMA_TILE), "mfma"),
    (Request("gfx90a", "mma", MFMA_TILE), "mfma"),
    (Request("sm90", "fma", {"a": Operand("register", "f32")}), "thread"),
    (Request("tensix", "exp", {"x": Operand("tile_register", "f32", (32, 32))}), "sfpu"),
    (Request("sm90", "copy", {"src": Operand("global", "f16", (256, 256)),
                              "dst": Operand("shared", "f16", (64, 64), "row_major", "b128")}, unit="tma"), "tma"),
])  # fmt: skip
def test_each_target_answers_a_request_it_can_carry_out_with_its_unit_and_steps(request_: Request, unit: str) -> None:
    sut = ask(request_, verify=False)

    assert isinstance(sut, Feasible), sut
    assert sut.unit == unit and sut.steps and sut.code


def test_a_gpu_mma_needing_four_instructions_per_k_block_is_one_feasible_answer() -> None:
    sut = ask(Request("sm90", "mma", TILE), verify=False)

    assert isinstance(sut, Feasible)
    assert any("4 x wgmma.mma_async.m64n64k16" in step.spelling for step in sut.steps)
    assert "SWIZZLE_128B" in sut.setup["tensor map"]


@pytest.mark.parametrize(("request_", "reason"), [
    (Request("gfx942", "mma", MFMA_TILE | {"a": Operand("shared", "f32", (64, 64)), "b": Operand("shared", "f32", (64, 64), "col_major")}), "--in f16 --acc f32"),
    (Request("avx2", "copy", {"src": Operand("global", "f32", (8,)),
                              "dst": Operand("vector", "f32", (8,), "row_major", "b128")}), "no swizzle"),
    (Request("sm90", "mma", TILE, unit="za"), "no unit"),
    (Request("riscv", "add"), "no target"),
    (Request("tensix", "mma", {"a": Operand("tile_register", "f32", (32, 48)), "b": Operand("tile_register", "f32", (48, 32)),
                               "c": Operand("tile_register", "f32", (32, 32))}), "32x32 tiles"),
    (Request("sme", "mma", TILE), "--in f32 --acc f32"),
])  # fmt: skip
def test_a_request_no_unit_carries_out_is_infeasible_with_its_reason(request_: Request, reason: str) -> None:
    sut = ask(request_, verify=False)

    assert isinstance(sut, Infeasible | Invalid)
    assert reason in sut.reason


def test_the_nearest_request_of_an_infeasible_tile_is_feasible() -> None:
    refused = ask(
        Request(
            "gfx942",
            "mma",
            TILE | {"a": Operand("shared", "f32", (64, 64)), "b": Operand("shared", "f32", (64, 64), "col_major")},
        ),
        verify=False,
    )
    assert isinstance(refused, Infeasible) and refused.nearest
    a, b, c = (Operand.parse(part.split(" ", 1)[1]) for part in refused.nearest[0].split(", "))

    sut = ask(Request("gfx942", "mma", {"a": a, "b": b, "c": c}), verify=False)

    assert isinstance(sut, Feasible)


def test_a_cpu_mma_is_the_checked_fma_fallback() -> None:
    tile = {"a": Operand("global", "f32", (16, 8)), "b": Operand("global", "f32", (8, 16)),
            "c": Operand("global", "f32", (16, 16))}  # fmt: skip

    sut = ask(Request("avx2", "mma", tile))

    assert isinstance(sut, Feasible) and sut.check.status == "run", sut


def test_the_cli_prints_the_answer_as_json_and_exits_2_when_infeasible(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["ask", "gfx942", "mma", "--a", "shared:f32:64x64:row_major:xor:8", "--b",
                 "shared:f32:64x64:col_major:xor:8", "--c", "register:f32:64x64", "--json"])  # fmt: skip

    sut = json.loads(capsys.readouterr().out)
    assert code == 2 and sut["feasible"] is False and sut["nearest"]
    assert sut["request"]["target"] == "gfx942" and sut["request"]["operands"]["a"]["shape"] == [64, 64]


def test_a_tensix_mma_is_one_matmul_tiles_call_per_k_tile_and_output_tile() -> None:
    tile = {"a": Operand("tile_register", "f32", (64, 96)), "b": Operand("tile_register", "f32", (96, 32)),
            "c": Operand("tile_register", "f32", (64, 32))}  # fmt: skip

    sut = ask(Request("tensix", "mma", tile), verify=False)

    assert isinstance(sut, Feasible) and sut.unit == "fpu"
    assert [(step.spelling, step.count) for step in sut.steps][1:] == [
        ("matmul_tiles(c0, c1, 0, 0, 0)", 6), ("pack_tile(0, c16)", 2)
    ]  # fmt: skip


def answered(request_: Request) -> Feasible | Infeasible | Invalid:
    return ask(request_, verify=False)


LDS = Operand("shared", "f16", (64, 64), "row_major", "xor:8")
B128 = Operand("shared", "f16", (64, 64), "row_major", "b128")
GLOBAL = Operand("global", "f16", (256, 256))


@pytest.mark.parametrize(("request_", "reason"), [
    (Request("sm90", "mma", TILE | {"b": Operand("shared", "bf16", (64, 64))}), "one element type"),
    (Request("avx2", "mma", {"a": Operand("global", "f32", (16, 8)), "b": Operand("global", "f64", (8, 16)),
                             "c": Operand("global", "f64", (16, 16))}), "one element type"),
    (Request("sm90", "mma", TILE | {"c": Operand("shared", "f32", (64, 64))}), "accumulates c in register"),
    (Request("sm90", "mma", TILE | {"b": Operand("register", "f16", (64, 64))}), "reads b from shared"),
    (Request("sm90", "mma", TILE | {"a": Operand("shared", "f16", (64, 64), "row_major", "b32")}), "swizzle b128"),
    (Request("gfx942", "mma", MFMA_TILE | {"a": B128}), "swizzle xor:8"),
    (Request("sm90", "mma", TILE | {"a": Operand("shared", "f16", (64, 64), "col_major", "b128")}), "takes a row_major"),
    (Request("sm90", "mma", TILE | {"b": B128}), "takes b col_major (Bt, N rows of K)"),
    (Request("gfx942", "mma", MFMA_TILE | {"b": LDS}), "takes b col_major (Bt, N rows of K)"),
    (Request("avx2", "mma", {"a": Operand("global", "f32", (16, 8), "row_major", "b128"),
                             "b": Operand("global", "f32", (8, 16)), "c": Operand("global", "f32", (16, 16))}),
     "no swizzle"),
    (Request("tensix", "mma", {"a": Operand("tile_register", "bf16", (32, 32)),
                               "b": Operand("tile_register", "f32", (32, 32)),
                               "c": Operand("tile_register", "bf16", (32, 32))}), "one element type"),
])  # fmt: skip
def test_an_mma_whose_operands_the_instruction_cannot_read_is_infeasible(request_: Request, reason: str) -> None:
    sut = answered(request_)

    assert isinstance(sut, Infeasible | Invalid), sut
    assert reason in sut.reason


@pytest.mark.parametrize(("request_", "runs_on"), [
    (Request("sm90", "mma", TILE, unit="warp"), "warpgroup"),
    (Request("sm90", "mma", TILE, unit="tma"), "warpgroup"),
    (Request("tensix", "mma", {name: Operand("tile_register", "f32", (32, 32)) for name in "abc"}, unit="sfpu"), "fpu"),
    (Request("avx2", "add", {"a": Operand("vector", "f64", (4,))}, unit="scalar"), "vector"),
    (Request("gfx942", "copy", {"src": GLOBAL, "dst": LDS}, unit="mfma"), "lds"),
    (Request("sm90", "reduce_add", {"x": Operand("register", "f32")}, unit="thread"), "warp"),
    (Request("tensix", "exp", {"x": Operand("tile_register", "f32", (32, 32))}, unit="fpu"), "sfpu"),
])  # fmt: skip
def test_a_pinned_unit_that_does_not_run_the_operation_is_infeasible_and_names_the_unit_that_does(
    request_: Request, runs_on: str
) -> None:
    sut = answered(request_)

    assert isinstance(sut, Infeasible), sut
    assert f"runs on {runs_on}" in sut.reason and sut.nearest == (f"unit {runs_on}",)


@pytest.mark.parametrize(("request_", "reason"), [
    (Request("gfx942", "copy", {"src": Operand("global", "f32", (3, 5)), "dst": Operand("shared", "f32", (7,))}),
     "copies f16, bf16, e4m3, e5m2 tiles on gfx942, not f32"),
    (Request("gfx942", "copy", {"src": GLOBAL, "dst": B128}), "xor:8"),
    (Request("gfx942", "copy", {"src": GLOBAL, "dst": Operand("shared", "f16", (64, 64))}), "xor:8"),
    (Request("avx2", "copy", {"src": Operand("global", "f32", (8,)), "dst": Operand("vector", "f64", (4,))}),
     "converts nothing"),
    (Request("avx2", "copy", {"src": Operand("shared", "f32", (8,)), "dst": Operand("shared", "f32", (8,))}),
     "loads global memory into a register"),
    (Request("avx2", "copy", {"src": Operand("global", "f32", (3,)), "dst": Operand("vector", "f32", (3,))}),
     "8 f32 lanes"),
    (Request("avx512", "copy", {"src": Operand("global", "f32", (64, 60)), "dst": Operand("vector", "f32", (64, 60))}),
     "16 f32 lanes"),
    (Request("sm90", "copy", {"src": GLOBAL, "dst": Operand("register", "f16", (64, 64))}), "shared memory only"),
    (Request("sm90", "copy", {"src": Operand("global", "f32", (256, 256)), "dst": B128}), "converts nothing"),
    (Request("sm90", "copy", {"src": Operand("global", "f16", (8, 8)), "dst": B128}), "at least the box"),
    (Request("sm90", "copy", {"src": Operand("global", "f16", (256,)), "dst": B128}), "two-dimensional"),
    (Request("sm90", "copy", {"src": Operand("global", "f16", (256, 256), "col_major"), "dst": B128}), "row-major"),
])  # fmt: skip
def test_a_copy_the_unit_cannot_carry_out_is_infeasible(request_: Request, reason: str) -> None:
    sut = answered(request_)

    assert isinstance(sut, Infeasible | Invalid), sut
    assert reason in sut.reason


def test_a_cpu_copy_from_a_register_to_memory_is_a_store_and_from_memory_a_load() -> None:
    register, memory = Operand("vector", "f32", (8,)), Operand("global", "f32", (8,))

    store = answered(Request("avx2", "copy", {"src": register, "dst": memory}))
    loaded = answered(Request("avx2", "copy", {"src": memory, "dst": register}))

    assert isinstance(store, Feasible) and isinstance(loaded, Feasible)
    assert "store" in store.steps[0].spelling and "load" in loaded.steps[0].spelling
    assert store.request.op == "copy"


@pytest.mark.parametrize("op", [row.op for row in simt.rows()])
@pytest.mark.parametrize("target", ["sm90", "gfx942", "gfx90a"])
def test_a_device_row_answers_on_a_unit_its_target_lists_and_pinning_that_unit_is_feasible(
    target: str, op: str
) -> None:
    sut = answered(Request(target, op))

    assert isinstance(sut, Feasible), sut
    assert sut.unit in UNITS[target] and all(step.unit == sut.unit for step in sut.steps)
    assert isinstance(answered(Request(target, op, unit=sut.unit)), Feasible)


@pytest.mark.parametrize("op", [row.op for row in simt.rows()])
def test_every_device_row_is_reachable_on_every_gpu_target(op: str) -> None:
    for target in ("sm90", "gfx942", "gfx90a"):
        sut = answered(Request(target, op))

        assert isinstance(sut, Feasible), sut
        assert sut.steps[0].spelling


@pytest.mark.parametrize(("request_", "reason"), [
    (Request("sm90", "fma", {"x": Operand("register", "f64")}), "computes in f32"),
    (Request("sm90", "fma", {"x": Operand("shared", "f32", (64, 64))}), "one thread on scalars"),
    (Request("avx2", "add", {"x": Operand("vector", "f64", (6,))}), "4 f64 lanes"),
    (Request("avx2", "add", {"a": Operand("vector", "f64", (4,)), "b": Operand("vector", "f32", (8,))}), "mix"),
    (Request("avx2", "add", {"a": Operand("vector", "f64", (4,))}, max_ulp=1.0), "add is exact"),
    (Request("tensix", "exp", {"x": Operand("tile_register", "f32", (7, 3))}), "one 32x32 tile"),
    (Request("tensix", "sqrt", {"x": Operand("tile_register", "f32", (32, 32))}, max_ulp=1.0), "one accuracy"),
    (Request("sme", "add"), "mma only"),
])  # fmt: skip
def test_an_elementwise_request_with_operands_the_row_does_not_compute_is_infeasible(
    request_: Request, reason: str
) -> None:
    sut = answered(request_)

    assert isinstance(sut, Infeasible | Invalid), sut
    assert reason in sut.reason


def test_a_math_function_without_a_bound_answers_its_strict_rung_with_code() -> None:
    sut = answered(Request("avx2", "exp", {"x": Operand("vector", "f32", (8,))}))

    assert isinstance(sut, Feasible)
    assert sut.steps[0].spelling == "alloy_exp_f32_strict" and "_mm256_" in sut.code
    assert "rung strict" in sut.notes[0]


@pytest.mark.parametrize("refused", [
    Request("avx2", "mma", {"a": Operand("global", "f16", (16, 8)), "b": Operand("global", "f16", (8, 16)),
                            "c": Operand("global", "f32", (16, 16))}),
    Request("sme", "mma", TILE),
    Request("sm90", "mma", TILE | {"c": Operand("shared", "f32", (64, 64))}),
    Request("gfx942", "mma", MFMA_TILE | {"a": B128}),
    Request("tensix", "mma", {"a": Operand("tile_register", "f32", (32, 48)),
                              "b": Operand("tile_register", "f32", (48, 32)),
                              "c": Operand("tile_register", "f32", (32, 32))}),
    Request("sm90", "copy", {"src": GLOBAL, "dst": Operand("register", "f16", (64, 64))}),
    Request("gfx942", "copy", {"src": GLOBAL, "dst": B128}),
    Request("gfx942", "copy", {"src": Operand("global", "f16", (128, 64)),
                               "dst": Operand("shared", "f16", (128, 64), "row_major", "xor:8")}),
    Request("sm90", "reduce_add", {"x": Operand("register", "f32", (1000,))}),
    Request("avx2", "copy", {"src": Operand("global", "f32", (3,)), "dst": Operand("vector", "f32", (3,))}),
    Request("avx2", "add", {"x": Operand("vector", "f64", (6,))}),
    Request("sm90", "fma", {"x": Operand("register", "f64")}),
    Request("tensix", "exp", {"x": Operand("tile_register", "f32", (7, 3))}),
    Request("sme", "add"),
])  # fmt: skip
def test_every_nearest_request_of_a_refusal_is_itself_feasible(refused: Request) -> None:
    sut = answered(refused)
    assert isinstance(sut, Infeasible) and sut.nearest

    for near in sut.nearest:
        operands = {name: Operand.parse(text) for name, text in (part.split(" ", 1) for part in near.split(", "))}
        op = "mma" if refused.target == "sme" else refused.op
        assert isinstance(answered(Request(refused.target, op, operands)), Feasible), near


def test_a_tile_program_that_fails_its_check_is_infeasible(monkeypatch: pytest.MonkeyPatch) -> None:
    def failing(plan_: tile.TilePlan) -> tile.TilePlan:
        return tile.replace_check(plan_, "failed", "relative error 0.5 against the f64 reference")

    monkeypatch.setattr(tile, "verify", failing)
    operands = {"a": Operand("global", "f32", (16, 8)), "b": Operand("global", "f32", (8, 16)),
                "c": Operand("global", "f32", (16, 16))}  # fmt: skip

    sut = ask(Request("avx2", "mma", operands))

    assert isinstance(sut, Infeasible) and "failed its check" in sut.reason


def test_a_device_row_whose_recorded_check_failed_is_infeasible(monkeypatch: pytest.MonkeyPatch) -> None:
    failed = {("fma", "cuda"): simt.Verdict("fma", "cuda", "an sm_90 device", ok=False, error="relative error 0.5")}
    monkeypatch.setattr(simt, "verdicts", lambda: failed)

    sut = answered(Request("sm90", "fma", {"x": Operand("register", "f32")}))

    assert isinstance(sut, Infeasible) and "relative error 0.5" in sut.reason


@pytest.mark.parametrize("operand", [
    "shared:f16:64y64", "smem:f16:64x64", "shared:f16:64x64:b128", "shared:f16:64x64:row_major:b128:extra",
    "shared:f16:0x64", "shared",
])  # fmt: skip
def test_the_cli_rejects_a_malformed_operand_as_a_usage_error_apart_from_infeasible(
    operand: str, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["ask", "sm90", "mma", "--a", operand, "--b", "shared:f16:64x64", "--c", "register:f32:64x64"])

    printed = capsys.readouterr()
    assert code == 64 and "invalid (malformed_operand)" in printed.out and operand in printed.out


def test_the_cli_reads_a_target_in_any_case_and_an_lds_swizzle_with_its_colon(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = main(["ask", "GFX942", "copy", "--src", "global:f16:256x256", "--dst", "shared:f16:64x64:row_major:xor:8",
                 "--json"])  # fmt: skip

    sut = json.loads(capsys.readouterr().out)
    assert code == 0 and sut["unit"] == "lds" and sut["request"]["operands"]["dst"]["swizzle"] == "xor:8"


def test_an_operand_spells_back_to_what_parses_to_it() -> None:
    for text in ("register:f32", "vector:f64:4", "shared:f16:64x64:row_major:b128", "shared:f16:64x64:col_major",
                 "shared:f16:64x64:row_major:xor:8"):  # fmt: skip
        assert Operand.parse(text).spelled() == text


SME = {"a": Operand("global", "f32", (70, 9), "col_major"), "b": Operand("global", "f32", (9, 33)),
       "c": Operand("tile_register", "f32", (70, 33))}  # fmt: skip
REGISTER = Operand("vector", "f64", (4,))


@pytest.mark.parametrize(("request_", "why"), [
    (Request("riscv", "add"), Why.TARGET),
    (Request("sm90", "mma", TILE, unit="za"), Why.UNIT_NAME),
    (Request("avx2", "frobnicate"), Why.OPERATION),
    (Request("avx2", "add"), Why.OPERANDS),
    (Request("tensix", "exp"), Why.OPERANDS),
    (Request("avx2", "add", {"x": Operand("shared", "f64", (4,))}), Why.SPACE),
    (Request("tensix", "exp", {"x": Operand("global", "f32", (32, 32))}), Why.SPACE),
    (Request("tensix", "mma", {name: Operand("shared", "f32", (32, 32)) for name in "abc"}), Why.SPACE),
    (Request("sm90", "mma", {"a": TILE["a"]}), Why.OPERANDS),
    (Request("sm90", "copy", {"src": GLOBAL}), Why.OPERANDS),
    (Request("sm90", "mma", TILE | {"c": Operand("register", "f32", (64, 32))}), Why.CHAIN),
    (Request("sm90", "mma", TILE | {"a": Operand("shared", "bf16", (64, 64))}), Why.MIXED_TYPES),
    (Request("avx2", "add", {"a": REGISTER, "b": Operand("vector", "f32", (8,))}), Why.MIXED_TYPES),
    (Request("sm90", "copy", {"src": Operand("global", "f32", (256, 256)), "dst": B128}), Why.MIXED_TYPES),
    (Request("avx2", "add", {"a": REGISTER}, max_ulp=1.0), Why.BOUND),
    (Request("sm90", "fma", {"x": Operand("register", "f32")}, max_ulp=1.0), Why.BOUND),
    (Request("sm90", "mma", TILE, unit="warp"), Why.UNIT),
    (Request("sm90", "frobnicate"), Why.NO_ROW),
    (Request("tensix", "frobnicate"), Why.OPERATION),
    (Request("sm90", "mma", TILE | {"a": Operand("shared", "f32", (64, 64)),
                                    "b": Operand("shared", "f32", (64, 64), "col_major")}), Why.ELEMENT_TYPE),
    (Request("sm90", "fma", {"x": Operand("register", "f64")}), Why.ELEMENT_TYPE),
    (Request("sm90", "mma", {"a": Operand("shared", "f16", (64, 100), "row_major", "b128"),
                             "b": Operand("shared", "f16", (100, 64), "col_major", "b128"),
                             "c": Operand("register", "f32", (64, 64))}), Why.SHAPE),
    (Request("avx2", "add", {"x": Operand("vector", "f64", (6,))}), Why.SHAPE),
    (Request("sm90", "mma", TILE | {"c": Operand("shared", "f32", (64, 64))}), Why.SPACE),
    (Request("sm90", "copy", {"src": GLOBAL, "dst": Operand("register", "f16", (64, 64))}), Why.SPACE),
    (Request("sm90", "mma", TILE | {"a": Operand("shared", "f16", (64, 64), "row_major", "b32")}), Why.SWIZZLE),
    (Request("gfx942", "copy", {"src": GLOBAL, "dst": B128}), Why.SWIZZLE),
    (Request("avx2", "add", {"x": Operand("vector", "f64", (4,), "row_major", "b128")}), Why.SWIZZLE),
    (Request("sm90", "mma", TILE | {"b": B128}), Why.LAYOUT),
    (Request("sme", "mma", SME | {"a": Operand("global", "f32", (70, 9))}), Why.LAYOUT),
    (Request("avx2", "mma", {"a": Operand("global", "f32", (16, 8), "col_major"),
                             "b": Operand("global", "f32", (8, 16)), "c": Operand("global", "f32", (16, 16))}), Why.LAYOUT),
    (Request("sm90", "copy", {"src": Operand("global", "f16", (256, 256), "col_major"), "dst": B128}), Why.LAYOUT),
    (Request("avx2", "exp", {"x": Operand("vector", "f32", (8,))}, max_ulp=1e-9), Why.NO_RUNG),
    (Request("sme", "add"), Why.NOT_COVERED),
    (Request("gfx942", "copy", {"src": LDS, "dst": GLOBAL}), Why.NOT_COVERED),
])  # fmt: skip
def test_every_refusal_carries_its_reason_code_and_the_class_the_code_belongs_to(request_: Request, why: Why) -> None:
    sut = answered(request_)

    assert not isinstance(sut, Feasible), sut
    assert sut.why is why, sut.reason
    assert isinstance(sut, Invalid if why in INVALID else Infeasible)
    assert sut.status == ("invalid" if why in INVALID else "infeasible") and sut.feasible is False


def test_the_reason_codes_split_into_invalid_and_infeasible_without_overlap() -> None:
    infeasible = set(Why) - INVALID

    assert INVALID and infeasible and Why.MALFORMED in INVALID
    assert {Why.UNIT, Why.NO_ROW, Why.ELEMENT_TYPE, Why.SHAPE, Why.SPACE, Why.SWIZZLE, Why.LAYOUT, Why.NO_RUNG,
            Why.NOT_COVERED, Why.CHECK_FAILED, Why.COMBINE, Why.ORDER} == infeasible  # fmt: skip


def test_an_sme_mma_takes_a_transposed_and_answers_fmopa_into_za() -> None:
    sut = answered(Request("sme", "mma", SME))

    assert isinstance(sut, Feasible) and sut.unit == "za"
    assert any("svmopa_za32_f32_m" in step.spelling for step in sut.steps)


@pytest.mark.parametrize(("argv", "code", "status"), [
    (["sm90", "mma", "--a", "shared:f16:64x64:row_major:b128", "--b", "shared:f16:64x64:col_major:b128", "--c",
      "register:f32:64x64"], 0, "feasible"),
    (["sm90", "mma", "--a", "shared:f16:64x64:row_major:b128", "--b", "shared:f16:64x64:row_major:b128", "--c",
      "register:f32:64x64"], 2, "infeasible"),
    (["sm90", "mma", "--a", "shared:f16:64x64"], 64, "invalid"),
    (["sm90", "mma", "--a", "shared:f16:64y64"], 64, "invalid"),
])  # fmt: skip
def test_the_cli_exit_code_and_json_status_tell_feasible_infeasible_and_invalid_apart(
    argv: list[str], code: int, status: str, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(["ask", *argv, "--json", "--no-verify"])

    sut = json.loads(capsys.readouterr().out)
    assert exit_code == code and sut["status"] == status
    assert ("why" in sut) == (status != "feasible")


@pytest.mark.parametrize(("request_", "why", "fix"), [
    (Request("sm90", "mma", TILE | {"b": B128}), Why.LAYOUT, "Keep Bt (N rows of K) in global memory"),
    (Request("gfx942", "mma", MFMA_TILE | {"b": LDS}), Why.LAYOUT, "write element (k, n) of B to row n"),
    (Request("sme", "mma", SME | {"a": Operand("global", "f32", (70, 9))}), Why.LAYOUT, "Keep At (K rows of M)"),
    (Request("sm90", "mma", TILE | {"a": Operand("shared", "f16", (64, 64))}), Why.SWIZZLE, "TMA copy (dst swizzle b128"),
    (Request("gfx942", "mma", MFMA_TILE | {"a": Operand("shared", "f16", (64, 64))}), Why.SWIZZLE,
     "LDS copy (dst swizzle xor:8)"),
    (Request("sm90", "mma", TILE | {"a": Operand("global", "f16", (64, 64))}), Why.SPACE, "ask copy with src global"),
    (Request("sm90", "mma", TILE | {"c": Operand("shared", "f32", (64, 64))}), Why.SPACE, "store the result to shared"),
    (Request("avx2", "mma", {"a": Operand("vector", "f32", (16, 8)), "b": Operand("global", "f32", (8, 16)),
                             "c": Operand("global", "f32", (16, 16))}), Why.SPACE, "pass the arrays as global"),
])  # fmt: skip
def test_an_mma_on_a_tile_the_kernel_would_misread_is_infeasible_and_says_how_to_get_the_tile_it_reads(
    request_: Request, why: Why, fix: str
) -> None:
    """A swizzle, a layout, or a space the kernel does not read never answers with the kernel: its code would compute
    on the wrong bytes."""
    sut = answered(request_)

    assert isinstance(sut, Infeasible), sut
    assert sut.why is why and fix in sut.fix
    assert sut.nearest and all("swizzle" not in near for near in sut.nearest)


@pytest.mark.parametrize(("request_", "header"), [
    (Request("sm90", "copy", {"src": GLOBAL, "dst": B128}), "sm90"),
    (Request("gfx942", "copy", {"src": GLOBAL, "dst": LDS}), "gfx942"),
    (Request("gfx90a", "copy", {"src": GLOBAL, "dst": LDS}), "gfx90a"),
])  # fmt: skip
def test_a_gpu_copy_is_checked_by_the_tile_program_that_runs_it(
    request_: Request, header: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[tuple[str, int, int, int]] = []

    def verified(plan_: tile.TilePlan) -> tile.TilePlan:
        seen.append((plan_.target, plan_.m, plan_.n, plan_.k))
        return tile.replace_check(plan_, "compiled", "compiled here")

    monkeypatch.setattr(tile, "verify", verified)
    checked, unchecked = ask(request_), ask(request_, verify=False)

    assert isinstance(checked, Feasible) and isinstance(unchecked, Feasible)
    assert seen == [(header, 64, 64, 64)]
    assert checked.check.status == "compiled" and "tile program" in checked.check.basis
    assert unchecked.check.status == "unverified" and "verify off" in unchecked.check.basis


def test_a_gpu_copy_whose_tile_program_fails_is_infeasible(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tile, "verify", lambda plan_: tile.replace_check(plan_, "failed", "did not compile"))

    sut = ask(Request("sm90", "copy", {"src": GLOBAL, "dst": B128}))

    assert isinstance(sut, Infeasible)
    assert sut.why is Why.CHECK_FAILED


def test_a_tma_answer_states_the_shared_alignment_the_swizzle_needs() -> None:
    sut = answered(Request("sm90", "copy", {"src": GLOBAL, "dst": B128}))

    assert isinstance(sut, Feasible)
    assert "alignas(1024)" in sut.setup["shared tile"] and "barrier" in sut.setup


def test_a_per_thread_row_refuses_an_operand_in_memory_and_says_to_load_it() -> None:
    sut = answered(Request("sm90", "fma", {"x": Operand("global", "f32")}))

    assert isinstance(sut, Infeasible)
    assert sut.why is Why.SPACE and "register" in sut.fix
    assert sut.nearest == ("x register:f32",)


def test_a_per_thread_row_computes_in_its_table_element_type() -> None:
    half2 = next(row for row in simt.rows() if row.op == "add_half2")

    assert half2.dtype == "f16"
    assert {row.dtype for row in simt.rows() if row.op != "add_half2" and not ask_module.moves(row)} == {"f32"}
    assert isinstance(answered(Request("sm90", "add_half2", {"x": Operand("register", "f16")})), Feasible)
    assert answered(Request("sm90", "add_half2", {"x": Operand("register", "f32")})).status == "infeasible"


@pytest.mark.parametrize("target", sorted(tile.TYPES))
def test_every_tile_target_plans_exactly_the_type_pairs_it_declares(target: str) -> None:
    for in_type, acc_type in tile.TYPES[target]:
        k = tile.k_block(in_type) if in_type in tile.GPU_BYTES else 64
        assert tile.plan(target, 64, 64, k, in_type, acc_type).in_type == in_type
    with pytest.raises(KeyError):
        tile.plan(target, 64, 64, 64, "f64", "f32")


@pytest.mark.parametrize(("ok", "detail", "status"), [(True, "0.9 ulp", "run"), (None, "builds", "compiled"),
                                                      (None, "", "unverified")])  # fmt: skip
def test_a_math_kernel_answer_carries_the_kernel_gate_verdict(
    ok: bool | None, detail: str, status: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from alloy.isa import mathcheck
    from alloy.isa.validate import Verdict

    seen: list[tuple[str, str, str, str]] = []

    def gate(fn: str, dtype: str, level: str, isa: str) -> Verdict:
        seen.append((fn, dtype, level, isa))
        return Verdict(ok, "kernel vs wider libm", detail)

    monkeypatch.setattr(mathcheck, "validate_kernel", gate)
    sut = ask(Request("avx2", "exp", {"x": Operand("vector", "f32", (8,))}, max_ulp=4.0))

    assert isinstance(sut, Feasible)
    assert sut.check.status == status
    assert [(fn, dtype, isa) for fn, dtype, _, isa in seen] == [("exp", "f32", "avx2")]


def test_a_math_kernel_that_fails_its_gate_is_infeasible(monkeypatch: pytest.MonkeyPatch) -> None:
    from alloy.isa import mathcheck
    from alloy.isa.validate import Verdict

    monkeypatch.setattr(mathcheck, "validate_kernel", lambda *args: Verdict(False, "kernel vs wider libm", "9 ulp"))

    sut = ask(Request("avx2", "exp", {"x": Operand("vector", "f32", (8,))}, max_ulp=4.0))

    assert isinstance(sut, Infeasible)
    assert sut.why is Why.CHECK_FAILED and "9 ulp" in sut.reason


# A 256 x 256 x 128 product on sm90 runs the 128 x 128 kernel: A blocks of 128 x 64 from the 256 x 128 matrix, and
# Bt blocks of 128 x 64 from the 256 x 128 transposed B.
WIDE_MMA = Request("sm90", "mma", {"a": Operand("shared", "f16", (256, 128), "row_major", "b128"),
                                   "b": Operand("shared", "f16", (128, 256), "col_major", "b128"),
                                   "c": Operand("register", "f32", (256, 256))})  # fmt: skip
BLOCK = Operand("shared", "f16", (128, 64), "row_major", "b128")
COPY_A = Request("sm90", "copy", {"src": Operand("global", "f16", (256, 128)), "dst": BLOCK})
COPY_BT = Request("sm90", "copy", {"src": Operand("global", "f16", (256, 128)), "dst": BLOCK})
LDS_MMA = Request("gfx942", "mma", MFMA_TILE)
LDS_COPY = Request("gfx942", "copy", {"src": Operand("global", "f16", (64, 64)), "dst": LDS})


def recording(monkeypatch: pytest.MonkeyPatch, verified: str = "compiled") -> list[tuple[str, int, int, int]]:
    seen: list[tuple[str, int, int, int]] = []

    def verify(plan_: tile.TilePlan) -> tile.TilePlan:
        seen.append((plan_.target, plan_.m, plan_.n, plan_.k))
        return tile.replace_check(plan_, verified, "the program's check")

    monkeypatch.setattr(tile, "verify", verify)
    return seen


@pytest.mark.parametrize(("requests", "program"), [
    ([COPY_A, COPY_BT, WIDE_MMA], ("sm90", 256, 256, 128)),
    ([LDS_COPY, LDS_COPY, LDS_MMA], ("gfx942", 64, 64, 64)),
])  # fmt: skip
def test_copies_and_the_mma_they_fill_carry_the_check_of_the_one_tile_program_that_runs_them(
    requests: list[Request], program: tuple[str, int, int, int], monkeypatch: pytest.MonkeyPatch
) -> None:
    seen = recording(monkeypatch)

    sut = ask_all(requests)

    assert isinstance(sut, Combined), sut
    assert seen == [program]
    assert sut.check.status == "compiled" and "one program runs all 3 requests" in sut.check.basis
    assert all(a.check.status == "compiled" for a in sut.answers)
    assert all("tile program of request 2" in a.check.basis for a in sut.answers[:2])
    assert len(sut.feeds) == 2


def copy_request(target: str, text: str) -> Request:
    """A nearest copy as ``ask_all`` spells it: ``copy src <operand>, dst <operand>``."""
    fields = (field.split(" ") for field in text.removeprefix("copy ").split(", "))
    return Request(target, "copy", {name: Operand.parse(operand) for name, operand in fields})


def test_a_copy_of_b_as_k_rows_of_n_does_not_combine_and_the_nearest_copies_do() -> None:
    copy_b = Request("sm90", "copy", {"src": Operand("global", "f16", (128, 256)), "dst": BLOCK})

    sut = ask_all([COPY_A, copy_b, WIDE_MMA], verify=False)

    assert isinstance(sut, Infeasible) and sut.why is Why.COMBINE, sut
    assert sut.request == copy_b and "Bt" in sut.fix
    nearest = [copy_request("sm90", text) for text in sut.nearest]
    assert nearest and isinstance(ask_all([*nearest, WIDE_MMA], verify=False), Combined)


def test_a_copy_into_a_block_the_mma_does_not_load_does_not_combine() -> None:
    narrow = Request("sm90", "copy", {"src": Operand("global", "f16", (256, 128)), "dst": B128})

    sut = ask_all([narrow, WIDE_MMA], verify=False)

    assert isinstance(sut, Infeasible) and sut.why is Why.COMBINE
    assert "shared:f16:128x64:row_major:b128" in sut.reason


def test_two_mmas_do_not_combine_because_no_tile_program_runs_both() -> None:
    sut = ask_all([WIDE_MMA, WIDE_MMA], verify=False)

    assert isinstance(sut, Infeasible) and sut.why is Why.COMBINE


def test_requests_on_two_targets_are_invalid_as_one_kernel() -> None:
    sut = ask_all([COPY_A, LDS_MMA], verify=False)

    assert isinstance(sut, Invalid) and sut.why is Why.MIXED_TARGETS


def test_a_refused_request_in_a_list_is_refused_with_its_index() -> None:
    sut = ask_all([COPY_A, Request("sm90", "mma", TILE | {"b": B128})], verify=False)

    assert isinstance(sut, Infeasible) and sut.why is Why.LAYOUT
    assert sut.reason.startswith("request 1 (mma): ")


def test_a_kernel_whose_tile_program_fails_is_infeasible(monkeypatch: pytest.MonkeyPatch) -> None:
    recording(monkeypatch, "failed")

    sut = ask_all([COPY_A, COPY_BT, WIDE_MMA])

    assert isinstance(sut, Infeasible) and sut.why is Why.CHECK_FAILED
    assert sut.reason.startswith("request 2 (mma): ")


def test_requests_no_program_runs_together_say_each_is_checked_alone() -> None:
    load = Request("avx2", "copy", {"src": Operand("global", "f64", (4,)), "dst": REGISTER})

    sut = ask_all([load, Request("avx2", "add", {"a": REGISTER})], verify=False)

    assert isinstance(sut, Combined) and not sut.feeds
    assert "requests 0, 1 are checked alone" in sut.check.basis


@pytest.mark.parametrize(("argv", "code", "status"), [
    (["sm90", "copy src=global:f16:256x128 dst=shared:f16:128x64:row_major:b128",
      "mma a=shared:f16:256x128:row_major:b128 b=shared:f16:128x256:col_major:b128 c=register:f32:256x256"], 0, "feasible"),
    (["sm90", "copy src=global:f16:128x256 dst=shared:f16:128x64:row_major:b128",
      "mma a=shared:f16:256x128:row_major:b128 b=shared:f16:128x256:col_major:b128 c=register:f32:256x256"], 2, "infeasible"),
    (["sm90", "copy src"], 64, "invalid"),
    (["sm90", ""], 64, "invalid"),
])  # fmt: skip
def test_the_ask_all_cli_exit_code_and_json_status_tell_the_three_classes_apart(
    argv: list[str], code: int, status: str, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(["ask-all", *argv, "--json", "--no-verify"])

    sut = json.loads(capsys.readouterr().out)
    assert exit_code == code and sut["status"] == status


# The six primitives on logical data (notes/isa-design.md, 2.8): blocks, the whole-multiple rule, load and store.


def test_a_whole_multiple_of_the_register_is_feasible_and_each_step_carries_its_count() -> None:
    sut = answered(
        Request("avx512", "add", {"a": Operand("vector", "f32", (96,)), "b": Operand("vector", "f32", (96,))})
    )

    assert isinstance(sut, Feasible)
    assert [(s.spelling, s.count) for s in sut.steps] == [("_mm512_add_ps", 6)]
    assert "6 registers" in sut.notes[-1]


@pytest.mark.parametrize(("target", "extent", "block", "nearest", "fix"), [
    ("avx512", 100, (16,), ("x vector:f32:96", "x vector:f32:112"), "gen_mask"),
    ("avx2", 100, (8,), ("x vector:f32:96", "x vector:f32:104"), "scalar remainder"),
    ("avx2", 3, (8,), ("x vector:f32:8",), "scalar remainder"),
])  # fmt: skip
def test_an_extent_that_is_no_whole_multiple_is_refused_with_the_block_the_multiples_and_the_tail(
    target: str, extent: int, block: tuple[int], nearest: tuple[str, str] | tuple[str], fix: str
) -> None:
    sut = answered(Request(target, "mul", {"a": Operand("vector", "f32", (extent,))}))

    assert isinstance(sut, Infeasible) and sut.why is Why.SHAPE
    assert (sut.block, sut.nearest) == (block, nearest)
    assert fix in sut.fix and f"{extent % block[0]} remain" in sut.reason or "less than one register" in sut.reason


def test_operands_of_two_extents_are_invalid_on_every_target() -> None:
    request = Request("avx512", "add", {"a": Operand("vector", "f32", (16,)), "b": Operand("vector", "f32", (32,))})

    sut = answered(request)

    assert isinstance(sut, Invalid) and sut.why is Why.CHAIN


def test_a_reduction_over_several_registers_combines_them_lane_wise_and_reduces_once() -> None:
    sut = answered(Request("avx512", "reduce_max", {"x": Operand("vector", "f64", (32,))}))

    assert isinstance(sut, Feasible)
    assert [(s.spelling, s.count) for s in sut.steps] == [("_mm512_max_pd", 3), ("_mm512_reduce_max_pd", 1)]
    assert "accumulator" in sut.notes[-1]


def test_a_scan_over_several_registers_carries_the_last_lane_into_the_next() -> None:
    one = answered(Request("neon", "scan_add", {"x": Operand("vector", "f32", (4,))}))
    sut = answered(Request("neon", "scan_add", {"x": Operand("vector", "f32", (12,))}))

    assert isinstance(one, Feasible) and isinstance(sut, Feasible)
    assert all(s.count == 1 for s in one.steps)
    carry = [(s.spelling, s.count) for s in sut.steps[len(one.steps) :]]
    assert [s.count for s in sut.steps[: len(one.steps)]] == [3] * len(one.steps)
    assert carry == [("vdupq_laneq_f32(t, 3)", 2), ("vaddq_f32", 2)]


@pytest.mark.parametrize(("op", "src", "dst", "spelling"), [
    ("load", Operand("global", "f32", (48,)), Operand("vector", "f32", (48,)), "_mm512_loadu_ps"),
    ("store", Operand("vector", "f32", (48,)), Operand("global", "f32", (48,)), "_mm512_storeu_ps"),
])  # fmt: skip
def test_load_and_store_are_request_names_over_the_rows_of_copy(
    op: str, src: Operand, dst: Operand, spelling: str
) -> None:
    sut = answered(Request("avx512", op, {"src": src, "dst": dst}))
    as_copy = answered(Request("avx512", "copy", {"src": src, "dst": dst}))

    assert isinstance(sut, Feasible) and isinstance(as_copy, Feasible)
    assert sut.request.op == op and sut.steps == as_copy.steps
    assert [(s.spelling, s.count) for s in sut.steps] == [(spelling, 3)]


@pytest.mark.parametrize(("op", "src", "dst"), [
    ("load", "global", "global"),
    ("load", "vector", "global"),
    ("store", "global", "vector"),
    ("load", "global", "shared"),
])  # fmt: skip
def test_a_load_that_ends_in_memory_or_a_store_that_starts_there_is_invalid_and_names_copy(
    op: str, src: Space, dst: Space
) -> None:
    operands = {"src": Operand(src, "f32", (16,)), "dst": Operand(dst, "f32", (16,))}

    sut = answered(Request("avx512", op, operands))

    assert isinstance(sut, Invalid) and sut.why is Why.MALFORMED
    assert sut.expected and sut.expected[0].startswith("copy")


def test_a_refused_load_names_the_block_and_load_requests_that_are_feasible() -> None:
    refused = Request("avx2", "load", {"src": Operand("global", "f32", (50,)), "dst": Operand("vector", "f32", (50,))})

    sut = answered(refused)

    assert isinstance(sut, Infeasible) and sut.block == (8,)
    assert sut.nearest == ("src global:f32:48, dst vector:f32:48", "src global:f32:56, dst vector:f32:56")
    for near in sut.nearest:
        operands = {name: Operand.parse(text) for name, text in (part.split(" ", 1) for part in near.split(", "))}
        assert isinstance(answered(Request("avx2", "load", operands)), Feasible), near


def test_whole_tensix_tiles_are_one_call_each_and_a_partial_tile_names_the_tile() -> None:
    whole = answered(Request("tensix", "exp", {"x": Operand("tile_register", "f32", (64, 96))}))
    partial = answered(Request("tensix", "exp", {"x": Operand("tile_register", "f32", (48, 32))}))

    assert isinstance(whole, Feasible) and [s.count for s in whole.steps] == [
        6,
        6,
    ]  # an init before each call, as checked
    assert isinstance(partial, Infeasible) and partial.why is Why.SHAPE
    assert partial.block == (32, 32) and "pad" in partial.fix
    assert partial.nearest == ("x tile_register:f32:32x32", "x tile_register:f32:64x32")


@pytest.mark.parametrize(("refused", "block"), [
    (Request("sm90", "mma", {"a": Operand("shared", "f16", (100, 64), "row_major", "b128"),
                             "b": Operand("shared", "f16", (64, 64), "col_major", "b128"),
                             "c": Operand("register", "f32", (100, 64))}), (64, 64, 64)),
    (Request("tensix", "mma", {"a": Operand("tile_register", "f32", (32, 48)),
                               "b": Operand("tile_register", "f32", (48, 32)),
                               "c": Operand("tile_register", "f32", (32, 32))}), (32, 32, 32)),
    (Request("avx2", "copy", {"src": Operand("global", "f32", (3,)), "dst": Operand("vector", "f32", (3,))}), (8,)),
])  # fmt: skip
def test_a_refusal_for_a_shape_tells_the_block_the_target_needs(
    refused: Request, block: tuple[int, int, int] | tuple[int]
) -> None:
    sut = answered(refused)

    assert isinstance(sut, Infeasible) and sut.why is Why.SHAPE
    assert sut.block == block


def test_the_cli_prints_the_block_of_a_shape_refusal(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["ask", "avx512", "add", "--a", "vector:f32:100", "--no-verify"])

    out = capsys.readouterr().out
    assert code == 2
    assert "block: 16" in out and "nearest: x vector:f32:96" in out


@pytest.mark.parametrize("shape", [(32, 32), (64, 64, 64)])
def test_a_cpu_refuses_data_of_two_or_more_dimensions_with_the_block_and_the_flattened_run(
    shape: tuple[int, ...],
) -> None:
    sut = ask(Request("avx2", "reduce_add", {"x": Operand("vector", "f32", shape)}), verify=False)

    assert isinstance(sut, Infeasible) and sut.why is Why.SHAPE, sut
    assert sut.block == (8,) and "one-dimensional" in sut.reason and "elementwise" not in sut.reason
    assert sut.nearest == (f"x vector:f32:{math.prod(shape)}",) and "flatten" in sut.fix


def test_a_gpu_thread_row_refuses_a_three_dimensional_operand() -> None:
    sut = ask(Request("sm90", "fma", {"x": Operand("register", "f32", (4, 4, 4))}), verify=False)

    assert isinstance(sut, Infeasible) and sut.why is Why.SHAPE and sut.block == (1,), sut


def test_an_uneven_neon_request_names_a_neon_register() -> None:
    sut = ask(Request("neon", "add", {"x": Operand("vector", "f32", (6,))}), verify=False)

    assert isinstance(sut, Infeasible) and "lanes of a neon register: 1 register holds 4, 2 remain" in sut.reason, sut


def test_a_two_dimensional_request_in_a_type_the_isa_lacks_is_refused_for_the_type() -> None:
    sut = ask(Request("avx2", "add", {"x": Operand("vector", "bf16", (3, 5))}), verify=False)

    assert isinstance(sut, Infeasible) and sut.why is Why.NO_ROW, sut


def test_the_cli_states_a_device_rows_check_once(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["ask", "gfx942", "scan_add", "--x", "register:f32"]) == 0

    first = capsys.readouterr().out.splitlines()[0]
    basis = simt.verdicts()[("scan_add", "hip")].basis
    assert first.endswith(f"check: {basis}")  # a basis that starts with its status ("ran on ...") is printed once
    assert "run ran" not in first and "compiled compiled" not in first


# MI200 (gfx90a) answers an agent met in smoke S4: each refusal names where the answer is.
@pytest.mark.parametrize(
    "argv, expected",
    [
        (["lookup", "gfx90a", "mfma", "f64"], "lookup takes its dialect (hip"),
        (["lookup", "sm90", "add", "f32"], "lookup takes its dialect (cuda"),
        (["lookup", "hip", "mfma", "f32"], "mfma is a matrix instruction: tile"),
        (["lookup", "avx2", "wgmma", "f32"], "wgmma is a matrix instruction: tile"),
        (["lookup", "hip", "ds_read_b128", "f32"], "lookup <dialect> load_wide"),
        (["lookup", "hip", "s_waitcnt", "f32"], "ask <target> wait --on"),
        (["lookup", "cuda", "ldmatrix", "f16"], "tile sm90 gemm"),
        (["reverse", "global_load_dword"], "an AMD GPU (CDNA) instruction"),
        (["reverse", "v_mfma_f32_32x32x8f16"], "gives a checked v_mfma kernel"),
    ],
)
def test_a_gpu_name_in_a_cpu_command_is_refused_with_where_it_is_answered(
    argv: list[str], expected: str, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(argv)

    printed = capsys.readouterr()
    assert code == 2
    assert expected in printed.err
    assert "did you mean fma" not in printed.err


def test_a_missing_device_row_offers_the_related_rows_as_nearest() -> None:
    sut = ask(Request("gfx90a", "exp", {"x": Operand("register", "f32")}))

    assert isinstance(sut, Infeasible)
    assert sut.why == Why.NO_ROW
    assert sut.nearest == ("gfx90a exp_fast",)


def test_a_wavefront_row_on_memory_is_refused_as_a_wavefront_row() -> None:
    sut = ask(Request("gfx90a", "reduce_add", {"x": Operand("global", "f32", (4096,))}))

    assert isinstance(sut, Infeasible)
    assert sut.why == Why.SPACE
    assert "one register per lane of a wavefront" in sut.reason
    assert sut.fix == "load the value into a register first"


def test_an_uncovered_gpu_copy_says_how_to_write_it_without_naming_the_design() -> None:
    sut = ask(
        Request("gfx90a", "copy", {"src": Operand("global", "f32", (256,)), "dst": Operand("register", "f32", (256,))})
    )

    assert isinstance(sut, Infeasible)
    assert sut.why == Why.NOT_COVERED
    assert "design" not in sut.reason
    assert "plain device code" in sut.fix


def test_a_bf16_mma_on_gfx90a_is_feasible_and_its_nearest_requests_keep_its_type() -> None:
    sut = ask(Request("gfx90a", "mma", {"a": Operand("shared", "bf16", (64, 64), "row_major", "xor:8"),
                                        "b": Operand("shared", "bf16", (64, 64), "col_major", "xor:8"),
                                        "c": Operand("register", "f32", (64, 64))}), verify=False)  # fmt: skip

    assert isinstance(sut, Feasible)
    assert sut.unit == "mfma"
    assert sut.setup["tile"].startswith("alloy_gemm_64x64<ALLOY_BF16>")
    odd = ask(Request("gfx90a", "mma", {"a": Operand("shared", "bf16", (64, 100)), "b": Operand("shared", "bf16", (100, 64)),
                                        "c": Operand("register", "f32", (64, 64))}), verify=False)  # fmt: skip
    assert isinstance(odd, Infeasible) and odd.why == Why.SHAPE
    assert odd.block == (64, 64, 64)
    assert all("bf16" in nearest for nearest in odd.nearest)


@pytest.mark.parametrize(("target", "swizzle"), [("gfx942", "xor:8"), ("sm90", "b128")])
def test_an_fp8_copy_fills_rows_of_128_bytes(target: str, swizzle: Swizzle) -> None:
    good = ask(Request(target, "copy", {"src": Operand("global", "e4m3", (256, 256)),
                                       "dst": Operand("shared", "e4m3", (64, 128), "row_major", swizzle)}), verify=False)  # fmt: skip
    narrow = ask(Request(target, "copy", {"src": Operand("global", "e4m3", (256, 256)),
                                         "dst": Operand("shared", "e4m3", (64, 64), "row_major", swizzle)}), verify=False)  # fmt: skip

    assert isinstance(good, Feasible)
    assert isinstance(narrow, Infeasible) and narrow.why == Why.SHAPE
    assert narrow.nearest == (f"src global:e4m3:256x256, dst shared:e4m3:64x128:row_major:{swizzle}",)


def test_gfx90a_refuses_an_fp8_copy_with_the_types_it_takes() -> None:
    sut = ask(Request("gfx90a", "copy", {"src": Operand("global", "e4m3", (256, 256)),
                                         "dst": Operand("shared", "e4m3", (64, 128), "row_major", "xor:8")}), verify=False)  # fmt: skip

    assert isinstance(sut, Infeasible) and sut.why == Why.ELEMENT_TYPE
    assert "copies f16, bf16 tiles on gfx90a, not e4m3" in sut.reason


# Design 2.9: wait and fence.
TMA_COPY = "copy src=global:f16:64x256 dst=shared:f16:64x64:row_major:b128"
WGMMA = "mma a=shared:f16:64x256:row_major:b128 b=shared:f16:256x64:col_major:b128 c=register:f32:64x64"


def requests(target: str, *texts: str) -> list[Request]:
    from alloy.isa.ask import parsed_request

    return [parsed_request(target, text) for text in texts]


@pytest.mark.parametrize(("target", "on", "spelled"), [
    ("sm90", "mbarrier", "mbarrier.try_wait.parity"), ("sm90", "wgmma_group", "wgmma.wait_group.sync.aligned 0"),
    ("sm90", "bulk_group", "cp.async.bulk.wait_group.read 0"), ("sm90", "cp_async_group", "cp.async.wait_group 0"),
    ("gfx90a", "vmcnt", "s_waitcnt vmcnt(0)"), ("gfx942", "lgkmcnt", "s_waitcnt lgkmcnt(0)"),
    ("tensix", "noc", "noc_async_read_barrier()"), ("tensix", "cb", "cb_wait_front"),
])  # fmt: skip
def test_a_wait_answers_the_instruction_that_completes_its_token(target: str, on: str, spelled: str) -> None:
    sut = ask(Request(target, "wait", on=on))

    assert isinstance(sut, Feasible) and spelled in sut.code


def test_a_wait_on_a_token_the_target_lacks_offers_the_ones_it_has_and_a_cpu_has_none() -> None:
    on_gpu = ask(Request("sm90", "wait", on="vmcnt"))
    on_cpu = ask(Request("avx2", "wait", on="mbarrier"))

    assert isinstance(on_gpu, Infeasible) and "wait on=mbarrier" in on_gpu.nearest
    assert isinstance(on_cpu, Infeasible) and "no asynchronous work" in on_cpu.reason


@pytest.mark.parametrize(("request_",), [
    (Request("gfx942", "mma", kind="16x16x16"),), (Request("sme", "mma", kind="f16"),),
    (Request("sm90", "copy", on="mbarrier"),), (Request("sm90", "fence", kind="proxy", depth=1),),
    (Request("sm90", "mma", stage=1),),
])  # fmt: skip
def test_on_or_kind_on_an_op_other_than_wait_or_fence_is_invalid_instead_of_dropped(request_: Request) -> None:
    sut = ask(request_)

    assert isinstance(sut, Invalid) and sut.why is Why.FLAG
    assert "applies to" in sut.reason


@pytest.mark.parametrize(("target", "kind", "feasible"), [
    ("sm90", "proxy", True), ("sm90", "operand", True), ("gfx942", "proxy", False), ("gfx90a", "operand", False),
])  # fmt: skip
def test_only_sm90_has_a_proxy_and_an_operand_fence(target: str, kind: str, feasible: bool) -> None:
    sut = ask(Request(target, "fence", kind=kind))

    assert isinstance(sut, Feasible) is feasible
    if not feasible:
        assert isinstance(sut, Infeasible) and sut.why == Why.NO_ROW


@pytest.mark.parametrize(("target", "text", "token", "fences"), [
    ("sm90", TMA_COPY, "mbarrier", ("fence kind=proxy",)), ("sm90", WGMMA, "wgmma_group", ("fence kind=operand",)),
    ("gfx942", "copy src=global:f16:256x256 dst=shared:f16:64x64:row_major:xor:8", "lgkmcnt", ()),
])  # fmt: skip
def test_an_asynchronous_unit_answers_how_its_work_completes(
    target: str, text: str, token: str, fences: tuple[()] | tuple[str]
) -> None:
    (request,) = requests(target, text)

    sut = ask(request, verify=False)

    assert isinstance(sut, Feasible) and sut.completion is not None
    assert (sut.completion.token, sut.completion.wait, sut.completion.fences) == (token, f"wait on={token}", fences)


def test_a_synchronous_unit_has_no_completion() -> None:
    (request,) = requests("gfx942", "mma a=shared:f16:64x64:row_major:xor:8 b=shared:f16:64x64:col_major:xor:8 "
                                     "c=register:f32:64x64")  # fmt: skip

    sut = ask(request, verify=False)

    assert isinstance(sut, Feasible) and sut.completion is None


def test_a_kernel_that_states_no_waits_gets_them_in_order() -> None:
    sut = ask_all(requests("sm90", TMA_COPY, WGMMA), verify=False)

    assert isinstance(sut, Combined)
    assert sut.order == ("fence kind=proxy before request 0", "wait on=mbarrier after request 0, before request 1",
                         "fence kind=operand before request 1", "wait on=wgmma_group after request 1")  # fmt: skip


def test_a_kernel_that_states_its_waits_in_order_is_feasible() -> None:
    sut = ask_all(requests("sm90", "fence kind=proxy", TMA_COPY, "wait on=mbarrier", "fence kind=operand", WGMMA,
                           "wait on=wgmma_group"), verify=False)  # fmt: skip

    assert isinstance(sut, Combined) and sut.order == ()


@pytest.mark.parametrize(("texts", "refused", "missing"), [
    (("fence kind=proxy", TMA_COPY, "fence kind=operand", WGMMA, "wait on=wgmma_group"), 1, "wait on=mbarrier"),
    (("fence kind=proxy", TMA_COPY, "fence kind=operand", WGMMA, "wait on=mbarrier", "wait on=wgmma_group"), 3,
     "wait on=mbarrier"),
    (("fence kind=proxy", TMA_COPY, "wait on=mbarrier", WGMMA, "wait on=wgmma_group"), 3, "fence kind=operand"),
    ((TMA_COPY, "wait on=mbarrier", "fence kind=operand", WGMMA, "wait on=wgmma_group"), 0, "fence kind=proxy"),
    ((WGMMA, TMA_COPY), 0, ""),
])  # fmt: skip
def test_a_kernel_that_reads_early_or_skips_a_fence_is_refused_naming_the_missing_request(
    texts: tuple[str, ...], refused: int, missing: str
) -> None:
    sut = ask_all(requests("sm90", *texts), verify=False)

    assert isinstance(sut, Infeasible) and sut.why == Why.ORDER
    assert sut.request == requests("sm90", texts[refused])[0]
    if missing:
        assert sut.nearest == (missing,)


# Review of 2026-11-17 (reviewers A and C): each fix with its case.
def test_a_device_row_answer_binds_the_names_its_code_uses() -> None:
    sut = ask(Request("gfx90a", "scan_add", {"x": Operand("register", "f32")}))

    assert isinstance(sut, Feasible)
    assert any("lane = threadIdx.x % warpSize" in note and "64 on hip" in note for note in sut.notes)


@pytest.mark.parametrize("request_", [
    Request("sm90", "copy", {"src": Operand("global", "f16", (64, 100)),
                             "dst": Operand("shared", "f16", (64, 64), "row_major", "b128")}),
    Request("sm90", "copy", {"src": Operand("global", "f16", (32, 32)),
                             "dst": Operand("shared", "f16", (64, 64), "row_major", "b128")}),
    Request("gfx942", "copy", {"src": Operand("global", "f16", (8, 8)),
                               "dst": Operand("shared", "f16", (7, 64), "row_major", "xor:8")}),
    Request("gfx942", "copy", {"src": Operand("global", "f16", (8, 8)),
                               "dst": Operand("shared", "f16", (64, 64), "row_major", "xor:8")}),
])  # fmt: skip
def test_a_gpu_copy_from_a_source_too_small_or_misaligned_is_refused_with_a_feasible_nearest(request_: Request) -> None:
    sut = ask(request_, verify=False)

    assert isinstance(sut, Infeasible) and sut.why == Why.SHAPE
    (nearest,) = sut.nearest
    src, dst = (Operand.parse(part.split(" ", 1)[1]) for part in nearest.split(", "))
    assert isinstance(ask(Request(request_.target, "copy", {"src": src, "dst": dst}), verify=False), Feasible)


def test_a_copy_on_a_target_without_copy_rows_is_refused_not_crashed() -> None:
    sut = ask(Request("sme", "copy", {"src": Operand("global", "f32", (8,)), "dst": Operand("vector", "f32", (8,))}))

    assert isinstance(sut, Infeasible) and sut.why == Why.NOT_COVERED


@pytest.mark.parametrize(("target", "on", "issued"), [("sm90", "mbarrier", True), ("sm90", "bulk_group", False),
                                                       ("gfx942", "vmcnt", False), ("tensix", "cb", True)])  # fmt: skip
def test_a_wait_says_whether_a_checked_program_issues_it(target: str, on: str, issued: bool) -> None:
    sut = ask(Request(target, "wait", on=on))

    assert isinstance(sut, Feasible) and sut.check.status == "unverified"
    assert ("tile programs that ran issue it" in sut.check.basis) is issued


def test_a_malformed_command_line_exits_as_invalid_not_as_infeasible(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exited:
        main(["ask", "tensix", "exp", "--y", "bad"])

    assert exited.value.code == 64
    capsys.readouterr()


def test_a_gpu_tail_mask_request_says_a_gpu_tail_is_a_bounds_check_and_offers_the_ballot_count() -> None:
    answer = answered(Request("sm90", "gen_mask", {"x": Operand("register", "f32")}))

    assert isinstance(answer, Infeasible) and answer.why is Why.NO_ROW
    assert "bounds check" in answer.fix and "ballot_count" in answer.fix


def test_a_tma_copy_issues_the_load_and_leaves_the_wait_to_its_completion() -> None:
    copy_ = Request("sm90", "copy", {"src": GLOBAL, "dst": B128})

    sut = answered(copy_)

    assert isinstance(sut, Feasible) and sut.completion is not None
    assert sut.completion.wait == "wait on=mbarrier"
    issued = sut.code.split("void alloy_copy_tma(")[1]  # the copy's own function, after the helpers it may call
    assert not any("try_wait" in step.spelling for step in sut.steps) and "alloy_mbar_wait" not in issued
    assert "  if (threadIdx.x == 0) { alloy_mbar_arrive_expect_tx(bar, 8192);" in sut.code


def test_a_tma_copy_states_the_launch_of_the_tile_program_that_runs_it() -> None:
    sut = answered(Request("sm90", "copy", {"src": GLOBAL, "dst": Operand("shared", "f16", (128, 64), "row_major",
                                                                          "b128")}))  # fmt: skip

    assert isinstance(sut, Feasible)
    assert "256 threads per block" in sut.setup["launch"] and "threadIdx.x == 0" in sut.setup["launch"]
    assert tile.GPU_THREADS["sm90", 128] == 256


def test_a_cpu_load_of_one_register_from_a_larger_array_is_a_block_of_it() -> None:
    sut = answered(Request("avx512", "load", {"src": Operand("global", "f64", (64,)), "dst": Operand("vector", "f64",
                                                                                                    (8,))}))  # fmt: skip

    assert isinstance(sut, Feasible)
    assert [(s.spelling, s.count) for s in sut.steps] == [("_mm512_loadu_pd", 1)]
    assert "a block of 8 of the 64 elements" in sut.notes[-1]


def test_a_cpu_load_from_an_array_smaller_than_the_registers_is_refused() -> None:
    sut = answered(Request("avx512", "load", {"src": Operand("global", "f64", (8,)), "dst": Operand("vector", "f64",
                                                                                                   (16,))}))  # fmt: skip

    assert isinstance(sut, Infeasible) and sut.why is Why.SHAPE
    assert "src holds 8 elements, fewer than the 16" in sut.reason


@pytest.mark.parametrize(("op", "combine", "reduce_"), [("reduce_add", "svadd_f64_m", "svaddv_f64"),
                                                        ("reduce_max", "svmax_f64_m", "svmaxv_f64")])  # fmt: skip
def test_an_sve_reduction_over_n_elements_is_a_predicated_loop_that_reduces_once(
    op: str, combine: str, reduce_: str
) -> None:
    sut = answered(Request("sve", op, {"x": Operand("vector", "f64", (64,))}))

    assert isinstance(sut, Feasible)
    assert [s.spelling for s in sut.steps] == [
        "each block of svcntd() lanes: svwhilelt_b64_s64(i, N)",
        "each block of svcntd() lanes: svld1_f64",
        f"each block of svcntd() lanes: {combine} into the accumulator (_m: its masked-off lanes stay)",
        reduce_,
    ]
    assert "for (int64_t i = 0; i < 64; i += svcntd())" in sut.code
    assert f"acc = {combine}(pg, acc, svld1_f64(pg, x + i));" in sut.code
    assert sut.code.endswith(f"double s = {reduce_}(svptrue_b64(), acc);")


@pytest.mark.parametrize(("op", "fix"), [
    ("reduce_add", "_mm512_maskz_loadu_pd(k, p) so its masked-off lanes hold 0"),
    ("reduce_min", "_mm512_mask_loadu_pd(_mm512_set1_pd(INFINITY), k, p) so its masked-off lanes hold INFINITY"),
    ("add", "compute with _mm512_mask_add_pd(src, k, a, b), store with _mm512_mask_storeu_pd(p, k, v)"),
])  # fmt: skip
def test_an_avx512_tail_fix_names_the_masked_spelling_each_op_needs(op: str, fix: str) -> None:
    sut = answered(Request("avx512", op, {"x": Operand("vector", "f64", (100,))}))

    assert isinstance(sut, Infeasible) and sut.why is Why.SHAPE
    assert fix in sut.fix and "masked form" not in sut.fix


@pytest.mark.parametrize(("request_", "header", "flags", "code"), [
    (Request("avx512", "add", {"x": Operand("vector", "f64", (8,))}), "#include <immintrin.h>", "-mavx512f -mavx512dq",
     "v = _mm512_add_pd(a, b);"),
    (Request("neon", "fma", {"x": Operand("vector", "f64", (2,))}), "#include <arm_neon.h>", "none",
     "v = vfmaq_f64(a, b, c);"),
    (Request("avx2", "reduce_add", {"x": Operand("vector", "f64", (4,))}), "#include <immintrin.h>", "-mavx2 -mfma",
     "__m128d s2 = _mm_add_pd(_mm256_castpd256_pd128(v), _mm256_extractf128_pd(v, 1));\ns = _mm_cvtsd_f64("),
    (Request("avx512", "exp", {"x": Operand("vector", "f64", (8,))}), "#include <immintrin.h> and <math.h>",
     "-mavx512f", "alloy_exp_f64_strict"),
])  # fmt: skip
def test_a_cpu_answer_carries_its_header_its_flags_and_a_statement_to_copy(
    request_: Request, header: str, flags: str, code: str
) -> None:
    sut = answered(request_)

    assert isinstance(sut, Feasible)
    assert sut.setup["header"] == header and sut.setup["flags"].startswith(flags)
    assert code in sut.code


@pytest.mark.parametrize(("op", "masked"), [("load", "_mm512_maskz_loadu_pd(k, p)"),
                                            ("store", "_mm512_mask_storeu_pd(p, k, v)")])  # fmt: skip
def test_an_avx512_load_or_store_answer_shows_its_masked_form_and_the_mask_it_takes(op: str, masked: str) -> None:
    vector, memory = Operand("vector", "f64", (8,)), Operand("global", "f64", (8,))
    operands = {"src": memory, "dst": vector} if op == "load" else {"src": vector, "dst": memory}

    sut = answered(Request("avx512", op, operands))

    assert isinstance(sut, Feasible)
    assert sut.setup["masked"].startswith(masked)
    assert (
        sut.setup["mask"].startswith("k = _mm512_cmplt_epu64_mask(iota, n): ")
        and "clamp(N - i, 0, 8)" in sut.setup["mask"]
    )


def test_an_avx512_mask_answer_says_how_to_build_iota_and_n() -> None:
    sut = answered(Request("avx512", "gen_mask", {"x": Operand("vector", "f64", (8,))}))

    assert isinstance(sut, Feasible) and sut.code == "k = _mm512_cmplt_epu64_mask(iota, n);"
    assert "iota = _mm512_setr_epi64(0..7)" in sut.setup["mask"]


@pytest.mark.parametrize("source", [Operand("register", "f64"), Operand("register", "f64", (1,))])
def test_a_broadcast_takes_its_scalar_source_with_or_without_a_shape_of_one(source: Operand) -> None:
    sut = answered(Request("avx512", "broadcast", {"x": source}))

    assert isinstance(sut, Feasible) and sut.code == "v = _mm512_set1_pd(s);"


def test_a_broadcast_from_a_partial_register_names_the_scalar_form() -> None:
    sut = answered(Request("avx512", "broadcast", {"x": Operand("register", "f64", (3,))}))

    assert isinstance(sut, Infeasible) and "--x register:f64 (or register:f64:1)" in sut.reason


def test_an_mma_whose_shapes_do_not_chain_names_valid_requests_that_are_feasible() -> None:
    vector = Operand("vector", "f64", (8,))

    sut = answered(Request("avx512", "mma", {"a": vector, "b": vector, "c": vector}))

    assert isinstance(sut, Invalid) and sut.why is Why.CHAIN
    assert "a global:f64:64x64, b global:f64:64x64, c global:f64:64x64" in sut.expected
    for near in sut.expected:
        operands = {name: Operand.parse(text) for name, text in (part.split(" ", 1) for part in near.split(", "))}
        assert isinstance(answered(Request("avx512", "mma", operands)), Feasible), near


@pytest.mark.parametrize(("target", "dtype", "lanes"), [("avx512", "f64", 8), ("avx512", "f32", 16),
                                                        ("avx2", "f64", 4), ("avx2", "f32", 8)])  # fmt: skip
@pytest.mark.avx512
def test_the_carry_of_a_scan_broadcasts_the_last_lane_of_the_register_before(
    target: str, dtype: str, lanes: int, tmp_path: pathlib.Path
) -> None:
    scalar, vector = ("double", "__m512d" if target == "avx512" else "__m256d") if dtype == "f64" else (
        "float", "__m512" if target == "avx512" else "__m256")  # fmt: skip
    width = "512" if target == "avx512" else "256"
    suffix = "pd" if dtype == "f64" else "ps"
    source = tmp_path / "carry.c"
    source.write_text(f"""#include <immintrin.h>
#include <stdio.h>
int main(void) {{
  {scalar} in[{lanes}], out[{lanes}];
  for (int j = 0; j < {lanes}; ++j) in[j] = j + 1;
  {vector} t = _mm{width}_loadu_{suffix}(in);
  _mm{width}_storeu_{suffix}(out, {ask_module.LAST_LANE[target, dtype]});
  for (int j = 0; j < {lanes}; ++j) printf("%g ", (double)out[j]);
  return 0;
}}
""")
    binary = tmp_path / "carry"
    subprocess.run(["cc", "-O2", "-mavx512f", "-mavx2", "-mfma", str(source), "-o", str(binary)], check=True)

    printed = subprocess.run([str(binary)], capture_output=True, text=True, check=True).stdout

    assert printed.split() == [str(lanes)] * lanes


def test_a_pending_tensix_row_with_a_stale_failure_is_unverified_for_an_elementwise_call_and_an_mma(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = tuple(dataclasses.replace(r, pending=True) if r.op in ("add", "mma") else r for r in tensix.rows())
    failed = {(r.op, d, r.unit): tensix.Verdict(r.op, d, r.unit, ok=False, rel=0.5) for r in rows for d in ("f32",)}
    monkeypatch.setattr(tensix, "rows", lambda: rows)
    monkeypatch.setattr(tensix, "verdicts", lambda: failed)
    tiles = Operand("tile_register", "f32", (32, 32))

    add = answered(Request("tensix", "add", {"x": tiles}))
    mma = answered(Request("tensix", "mma", {"a": tiles, "b": tiles, "c": tiles}))
    exp = answered(Request("tensix", "exp", {"x": tiles}))

    assert isinstance(add, Feasible) and isinstance(mma, Feasible)
    assert add.check == mma.check == Check("unverified", "pending a ttsim run (the tensix CI job runs it)")
    assert isinstance(exp, Infeasible) and exp.why is Why.CHECK_FAILED, "a row that is not pending is refused"


def test_an_sve_math_function_over_n_elements_defines_its_kernel_once_and_calls_it_per_block() -> None:
    sut = answered(Request("sve", "exp", {"x": Operand("vector", "f64", (64,))}))

    assert isinstance(sut, Feasible)
    kernel, loop = sut.code.split("for (int64_t i = 0; i < 64; i += svcntd()) {")
    assert "static inline svfloat64_t alloy_exp_f64_strict(svfloat64_t x)" in kernel
    assert "static inline" not in loop and "v = alloy_exp_f64_strict(v);" in loop


@pytest.mark.parametrize(("target", "request_", "spelled", "count"), [
    ("sm90", Operand("global", "f16", (4096,)), "uint4 q = reinterpret_cast<const uint4*>(x)[i / 8];", 512),
    ("gfx942", Operand("global", "bf16", (6,)), "__float22bfloat162_rn(make_float2(a, b))", 3),
    ("gfx90a", Operand("global", "f16", (3,)), "__half2float(x[i])", 3),
])  # fmt: skip
def test_a_gpu_load_or_store_of_global_data_takes_the_widest_row_that_divides_it(
    target: str, request_: Operand, spelled: str, count: int
) -> None:
    op = "store" if "make_float2" in spelled else "load"

    sut = answered(Request(target, op, {"x": request_}))

    assert isinstance(sut, Feasible), sut
    assert spelled in sut.steps[0].spelling and sut.steps[0].count == count


def test_a_gpu_load_from_registers_names_the_global_form() -> None:
    sut = answered(Request("sm90", "load", {"x": Operand("register", "f16")}))

    assert isinstance(sut, Infeasible) and sut.why is Why.SPACE
    assert sut.nearest == ("x global:f16:1024",)


def test_a_wide_gpu_load_of_an_extent_it_does_not_divide_is_refused_with_the_block() -> None:
    sut = answered(Request("sm90", "load_wide", {"x": Operand("global", "f16", (100,))}))

    assert isinstance(sut, Infeasible) and sut.block == (8,)
    assert sut.nearest == ("x global:f16:96", "x global:f16:104")


@pytest.mark.parametrize("op", ["add", "fma", "load"])
def test_plain_avx512_refuses_f16_and_names_the_fp16_target(op: str) -> None:
    """Zen 4 runs AVX-512 without AVX512-FP16: an f16 answer for plain avx512 would not run there."""
    sut = ask(Request("avx512", op, {"x": Operand("vector", "f16", (32,))}), verify=False)

    assert isinstance(sut, Infeasible) and sut.why is Why.ELEMENT_TYPE
    assert sut.nearest == ("target avx512_fp16",)


def test_the_fp16_target_answers_f16_with_the_fp16_flag() -> None:
    sut = ask(Request("avx512_fp16", "add", {"x": Operand("vector", "f16", (32,))}), verify=False)

    assert isinstance(sut, Feasible)
    assert "-mavx512fp16" in sut.setup["build"]


def test_a_math_answer_names_the_other_rungs_so_a_tighter_bound_can_ask_for_one() -> None:
    sut = ask(Request("avx2", "log", {"x": Operand("register", "f32", (8,))}, max_ulp=4), verify=False)

    assert isinstance(sut, Feasible)
    assert sut.notes[0].startswith("rung fast")
    assert "other rungs" in sut.notes[1] and "relaxed 0.9108 ulp" in sut.notes[1] and "--max-ulp" in sut.notes[1]


@pytest.mark.parametrize(("target", "lanes"), [("sm90", 32), ("gfx942", 64)])
def test_a_warp_reduction_takes_one_value_per_lane_and_refuses_a_longer_one_with_the_block_recipe(
    target: str, lanes: int
) -> None:
    one = ask(Request(target, "reduce_add", {"x": Operand("register", "f32", (lanes,))}), verify=False)
    longer = ask(Request(target, "reduce_add", {"x": Operand("register", "f32", (1000,))}), verify=False)

    assert isinstance(one, Feasible), one
    assert isinstance(longer, Infeasible) and longer.why is Why.SHAPE and "shared memory" in longer.fix
    assert f"x register:f32:{lanes}" in longer.nearest


def test_an_instruction_name_points_at_its_operation_and_an_unknown_name_at_no_unrelated_row() -> None:
    wgmma = ask(Request("sm90", "wgmma"))
    unknown = ask(Request("sm90", "frobnicate"))

    assert isinstance(wgmma, Infeasible) and wgmma.nearest == ("sm90 mma",)
    assert isinstance(unknown, Infeasible) and unknown.nearest == ()


def test_a_refused_cdna_copy_names_a_nearest_request_other_than_itself() -> None:
    dst = Operand("shared", "f16", (128, 64), "row_major", "xor:8")

    sut = ask(Request("gfx942", "copy", {"src": Operand("global", "f16", (128, 64)), "dst": dst}), verify=False)

    assert isinstance(sut, Infeasible) and "dst shared:f16:64x64:row_major:xor:8" in sut.nearest[0]


def test_an_mma_larger_than_one_block_says_first_that_it_is_a_grid_of_blocks() -> None:
    sut = ask(Request("sm90", "mma", {"a": Operand("shared", "f16", (64, 64), "row_major", "b128"),
                                      "b": Operand("shared", "f16", (64, 256), "col_major", "b128"),
                                      "c": Operand("register", "f32", (64, 256))}), verify=False)  # fmt: skip

    assert isinstance(sut, Feasible)
    assert sut.steps[0].spelling.startswith("C 64x256 is a grid of 1 x 4 thread blocks")


def test_a_kernel_fences_each_kind_once_and_refuses_a_third_copy_into_an_mma() -> None:
    two = ask_all(requests("sm90", TMA_COPY, TMA_COPY, WGMMA), verify=False)
    three = ask_all(requests("sm90", TMA_COPY, TMA_COPY, TMA_COPY, WGMMA), verify=False)

    assert isinstance(two, Combined) and sum(o.startswith("fence kind=proxy") for o in two.order) == 1
    assert isinstance(three, Infeasible) and three.why is Why.COMBINE and "second copy" in three.reason


def test_an_mma_off_its_blocks_is_refused_with_the_zero_padding_fix() -> None:
    sut = ask(Request("sm90", "mma", {"a": Operand("shared", "f16", (64, 100), "row_major", "b128"),
                                      "b": Operand("shared", "f16", (100, 64), "col_major", "b128"),
                                      "c": Operand("register", "f32", (64, 64))}), verify=False)  # fmt: skip

    assert isinstance(sut, Infeasible) and sut.why is Why.SHAPE and "pad A and B with zeros" in sut.fix


def test_a_cpu_proxy_fence_refusal_speaks_of_the_cpu_not_of_gpu_shared_memory() -> None:
    sut = ask(Request("sme", "fence", kind="proxy"))

    assert isinstance(sut, Infeasible) and "program order" in sut.reason and "__syncthreads" not in sut.reason


def test_an_f16_load_on_plain_avx512_points_at_the_converting_load_first() -> None:
    sut = ask(Request("avx512", "load", {"x": Operand("vector", "f16", (32,))}), verify=False)

    assert isinstance(sut, Infeasible) and sut.nearest == ("avx512 load_f16 --x vector:f32:16", "target avx512_fp16")
    assert "_mm512_cvtph_ps" in sut.reason


def test_an_sm90_tma_store_completes_on_its_bulk_group_after_a_proxy_fence() -> None:
    sut = ask(Request("sm90", "copy", {"src": Operand("shared", "f16", (64, 64), "row_major", "b128"),
                                       "dst": Operand("global", "f16", (100, 72))}), verify=False)  # fmt: skip

    assert isinstance(sut, Feasible) and sut.unit == "tma_store", sut
    assert "alloy_tma_store_2d" in sut.code and "cp.async.bulk.tensor.2d.global.shared::cta" in sut.code
    assert sut.completion == Completion("bulk_group", "wait on=bulk_group", ("fence kind=proxy",))


def test_an_sm90_mma_of_a_partial_tile_is_feasible_and_a_k_off_16_bytes_is_refused() -> None:
    partial = ask(Request("sm90", "mma", {"a": Operand("shared", "f16", (100, 40), "row_major", "b128"),
                                          "b": Operand("shared", "f16", (40, 72), "col_major", "b128"),
                                          "c": Operand("register", "f32", (100, 72))}), verify=False)  # fmt: skip
    odd = ask(Request("sm90", "mma", {"a": Operand("shared", "f16", (64, 100), "row_major", "b128"),
                                      "b": Operand("shared", "f16", (100, 64), "col_major", "b128"),
                                      "c": Operand("register", "f32", (64, 64))}), verify=False)  # fmt: skip

    assert isinstance(partial, Feasible) and any("partial tiles" in s.spelling for s in partial.steps)
    assert partial.steps[0].spelling.startswith("C 100x72 is a grid of 2 x 2 thread blocks")
    assert isinstance(odd, Infeasible) and "multiple of 16" in odd.reason


@pytest.mark.parametrize(("target", "on", "depth", "spelled"), [
    ("sm90", "wgmma_group", 1, "wgmma.wait_group.sync.aligned 1;"), ("sm90", "bulk_group", 2, "wait_group.read 2;"),
    ("gfx942", "vmcnt", 3, "vmcnt(3)"),
])  # fmt: skip
def test_a_wait_with_a_depth_leaves_that_many_groups_in_flight(target: str, on: str, depth: int, spelled: str) -> None:
    sut = ask(Request(target, "wait", on=on, depth=depth))

    assert isinstance(sut, Feasible) and spelled in sut.code, sut


def test_a_wait_on_an_mbarrier_has_no_depth() -> None:
    sut = ask(Request("sm90", "wait", on="mbarrier", depth=1))

    assert isinstance(sut, Infeasible) and sut.why is Why.NO_ROW and "own" in sut.reason


@pytest.mark.parametrize(("target", "copy", "mma"), [
    ("sm90", TMA_COPY, WGMMA),
    ("gfx942", "copy src=global:f16:64x256 dst=shared:f16:64x64:row_major:xor:8",
     "mma a=shared:f16:64x256:row_major:xor:8 b=shared:f16:256x64:col_major:xor:8 c=register:f32:64x64"),
])  # fmt: skip
def test_copies_into_two_stages_run_the_double_buffered_tile_kernel(target: str, copy: str, mma: str) -> None:
    sut = ask_all(requests(target, copy, copy, f"{copy} stage=1", f"{copy} stage=1", mma), verify=False)

    assert isinstance(sut, Combined), sut
    assert "alloy_gemm_64x64_2stage<ALLOY_F16><<<" in sut.answers[4].code
    assert sut.feeds[2:] == ("copy 2 fills a (stage 1) of mma 4", "copy 3 fills b (stage 1) of mma 4")
    assert any(o.endswith("after request 3") for o in sut.order)  # stage 1 is read by the next K block, not this mma


def test_a_one_stage_tile_program_leaves_the_two_stage_kernel_out() -> None:
    sut = ask_all(requests("sm90", TMA_COPY, TMA_COPY, WGMMA), verify=False)

    assert isinstance(sut, Combined) and "2stage" not in sut.answers[2].code


def test_a_two_stage_list_missing_a_stage_copy_is_refused_with_the_missing_input() -> None:
    sut = ask_all(requests("sm90", TMA_COPY, TMA_COPY, f"{TMA_COPY} stage=1", WGMMA), verify=False)

    assert isinstance(sut, Infeasible) and sut.why is Why.COMBINE and "b (stage 1) has no copy" in sut.reason


def test_an_explicit_two_stage_list_waits_on_stage_1_after_the_mma() -> None:
    texts = ("fence kind=proxy", TMA_COPY, TMA_COPY, "wait on=mbarrier", f"{TMA_COPY} stage=1", f"{TMA_COPY} stage=1",
             "fence kind=operand", WGMMA, "wait on=wgmma_group", "wait on=mbarrier")  # fmt: skip

    sut = ask_all(requests("sm90", *texts), verify=False)
    unfinished = ask_all(requests("sm90", *texts[:-1]), verify=False)

    assert isinstance(sut, Combined), sut
    assert isinstance(unfinished, Infeasible) and unfinished.why is Why.ORDER and "request 4" in unfinished.reason


def test_an_sm90_mma_answer_ranks_both_kernels_and_says_the_rank_is_derived() -> None:
    sut = ask(Request("sm90", "mma", {"a": Operand("shared", "f16", (64, 64), "row_major", "b128"),
                                      "b": Operand("shared", "f16", (64, 64), "col_major", "b128"),
                                      "c": Operand("register", "f32", (64, 64))}), verify=False)  # fmt: skip

    assert isinstance(sut, Feasible)
    rank = next(note for note in sut.notes if note.startswith("ranked"))
    assert "not measured" in rank and rank.index("1. 64x64") < rank.index("2. 128x128")
