# Copyright 2026 ETH Zurich and the Alloy authors.
"""The unified ISA (notes/isa-design.md, step 1): every target answers Feasible, with its unit, steps, and check, or
Infeasible, with a reason and the nearest requests it takes, from the surfaces it wraps."""

import json

import pytest

from alloy.isa.__main__ import main
from alloy.isa.ask import Feasible, Infeasible, Operand, Request, ask

TILE = {"a": Operand("shared", "f16", (64, 64)), "b": Operand("shared", "f16", (64, 64)),
        "c": Operand("register", "f32", (64, 64))}  # fmt: skip


@pytest.mark.parametrize(("request_", "unit"), [
    (Request("avx2", "add", {"a": Operand("vector", "f64", (4,))}), "vector"),
    (Request("avx2", "exp", {"x": Operand("vector", "f32", (8,))}, max_ulp=4.0), "vector"),
    (Request("sm90", "mma", TILE), "warpgroup"),
    (Request("gfx942", "mma", TILE), "mfma"),
    (Request("sm90", "fma", {"a": Operand("register", "f32")}), "thread"),
    (Request("tensix", "exp", {"x": Operand("tile_register", "f32", (32, 32))}), "sfpu"),
    (Request("sm90", "copy", {"src": Operand("global", "f16", (256, 256)),
                              "dst": Operand("shared", "f16", (64, 64), "row_major", "b128")}, unit="tma"), "tma"),
])  # fmt: skip
def test_each_target_answers_a_request_it_can_carry_out_with_its_unit_and_steps(request_, unit):
    sut = ask(request_, verify=False)

    assert isinstance(sut, Feasible), sut
    assert sut.unit == unit and sut.steps and sut.code


def test_a_gpu_mma_needing_four_instructions_per_k_block_is_one_feasible_answer():
    sut = ask(Request("sm90", "mma", TILE), verify=False)

    assert isinstance(sut, Feasible)
    assert any("4 x wgmma.mma_async.m64n64k16" in step.spelling for step in sut.steps)
    assert "SWIZZLE_128B" in sut.setup["tensor map"]


@pytest.mark.parametrize(("request_", "reason"), [
    (Request("gfx942", "mma", TILE | {"a": Operand("shared", "f32", (64, 64))}), "--in f16 --acc f32"),
    (Request("avx2", "copy", {"src": Operand("global", "f32", (8,)),
                              "dst": Operand("vector", "f32", (8,), "row_major", "b128")}), "no swizzle"),
    (Request("sm90", "mma", TILE, unit="za"), "no unit"),
    (Request("riscv", "add"), "no target"),
    (Request("tensix", "mma", {"a": Operand("tile_register", "f32", (32, 48)), "b": Operand("tile_register", "f32", (48, 32)),
                               "c": Operand("tile_register", "f32", (32, 32))}), "32x32 tiles"),
    (Request("sme", "mma", TILE), "--in f32 --acc f32"),
])  # fmt: skip
def test_a_request_no_unit_carries_out_is_infeasible_with_its_reason(request_, reason):
    sut = ask(request_, verify=False)

    assert isinstance(sut, Infeasible)
    assert reason in sut.reason


def test_the_nearest_request_of_an_infeasible_tile_is_feasible():
    refused = ask(Request("gfx942", "mma", TILE | {"a": Operand("shared", "f32", (64, 64))}), verify=False)
    assert isinstance(refused, Infeasible) and refused.nearest
    a, b, c = (Operand.parse(part.split(" ", 1)[1]) for part in refused.nearest[0].split(", "))

    sut = ask(Request("gfx942", "mma", {"a": a, "b": b, "c": c}), verify=False)

    assert isinstance(sut, Feasible)


def test_a_cpu_mma_is_the_checked_fma_fallback():
    tile = {"a": Operand("vector", "f32", (16, 8)), "b": Operand("vector", "f32", (8, 16)),
            "c": Operand("vector", "f32", (16, 16))}  # fmt: skip

    sut = ask(Request("avx2", "mma", tile))

    assert isinstance(sut, Feasible) and sut.check.status == "run", sut


def test_the_cli_prints_the_answer_as_json_and_exits_2_when_infeasible(capsys):
    code = main(["ask", "gfx942", "mma", "--a", "shared:f32:64x64", "--b", "shared:f32:64x64", "--c",
                 "register:f32:64x64", "--json"])  # fmt: skip

    sut = json.loads(capsys.readouterr().out)
    assert code == 2 and sut["feasible"] is False and sut["nearest"]
    assert sut["request"]["target"] == "gfx942" and sut["request"]["operands"]["a"]["shape"] == [64, 64]


def test_a_tensix_mma_is_one_matmul_tiles_call_per_k_tile_and_output_tile():
    tile = {"a": Operand("tile_register", "f32", (64, 96)), "b": Operand("tile_register", "f32", (96, 32)),
            "c": Operand("tile_register", "f32", (64, 32))}  # fmt: skip

    sut = ask(Request("tensix", "mma", tile), verify=False)

    assert isinstance(sut, Feasible) and sut.unit == "fpu"
    assert [(step.spelling, step.count) for step in sut.steps][1:] == [
        ("matmul_tiles(c0, c1, 0, 0, 0)", 6), ("pack_tile(0, c16)", 2)
    ]  # fmt: skip
