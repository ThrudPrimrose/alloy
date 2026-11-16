# Copyright 2026 ETH Zurich and the Alloy authors.
"""The unified ISA (notes/isa-design.md, step 1): every target answers Feasible, with its unit, steps, and check, or
Infeasible, with a reason and the nearest requests it takes, from the surfaces it wraps."""

import json

import pytest

from alloy.isa import simt, tile
from alloy.isa.__main__ import main
from alloy.isa.ask import INVALID, UNITS, Combined, Feasible, Infeasible, Invalid, Operand, Request, Why, ask, ask_all

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
    (Request("gfx942", "mma", MFMA_TILE | {"a": Operand("shared", "f32", (64, 64)), "b": Operand("shared", "f32", (64, 64), "col_major")}), "--in f16 --acc f32"),
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

    assert isinstance(sut, Infeasible | Invalid)
    assert reason in sut.reason


def test_the_nearest_request_of_an_infeasible_tile_is_feasible():
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


def test_a_cpu_mma_is_the_checked_fma_fallback():
    tile = {"a": Operand("global", "f32", (16, 8)), "b": Operand("global", "f32", (8, 16)),
            "c": Operand("global", "f32", (16, 16))}  # fmt: skip

    sut = ask(Request("avx2", "mma", tile))

    assert isinstance(sut, Feasible) and sut.check.status == "run", sut


def test_the_cli_prints_the_answer_as_json_and_exits_2_when_infeasible(capsys):
    code = main(["ask", "gfx942", "mma", "--a", "shared:f32:64x64:row_major:xor:8", "--b",
                 "shared:f32:64x64:col_major:xor:8", "--c", "register:f32:64x64", "--json"])  # fmt: skip

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
def test_an_mma_whose_operands_the_instruction_cannot_read_is_infeasible(request_, reason):
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
def test_a_pinned_unit_that_does_not_run_the_operation_is_infeasible_and_names_the_unit_that_does(request_, runs_on):
    sut = answered(request_)

    assert isinstance(sut, Infeasible), sut
    assert f"runs on {runs_on}" in sut.reason and sut.nearest == (f"unit {runs_on}",)


@pytest.mark.parametrize(("request_", "reason"), [
    (Request("gfx942", "copy", {"src": Operand("global", "f32", (3, 5)), "dst": Operand("shared", "f64", (7,))}),
     "f16 halves"),
    (Request("gfx942", "copy", {"src": GLOBAL, "dst": B128}), "xor:8"),
    (Request("gfx942", "copy", {"src": GLOBAL, "dst": Operand("shared", "f16", (64, 64))}), "xor:8"),
    (Request("avx2", "copy", {"src": Operand("global", "f32", (8,)), "dst": Operand("vector", "f64", (4,))}),
     "converts nothing"),
    (Request("avx2", "copy", {"src": Operand("shared", "f32", (8,)), "dst": Operand("shared", "f32", (8,))}),
     "loads global memory into a register"),
    (Request("avx2", "copy", {"src": Operand("global", "f32", (3,)), "dst": Operand("vector", "f32", (3,))}),
     "8 f32 lanes"),
    (Request("avx512", "copy", {"src": Operand("global", "f32", (64, 64)), "dst": Operand("vector", "f32", (64, 64))}),
     "16 f32 lanes"),
    (Request("sm90", "copy", {"src": GLOBAL, "dst": Operand("register", "f16", (64, 64))}), "shared memory only"),
    (Request("sm90", "copy", {"src": Operand("global", "f32", (256, 256)), "dst": B128}), "converts nothing"),
    (Request("sm90", "copy", {"src": Operand("global", "f16", (8, 8)), "dst": B128}), "at least the box"),
    (Request("sm90", "copy", {"src": Operand("global", "f16", (256,)), "dst": B128}), "two-dimensional"),
    (Request("sm90", "copy", {"src": Operand("global", "f16", (256, 256), "col_major"), "dst": B128}), "row-major"),
])  # fmt: skip
def test_a_copy_the_unit_cannot_carry_out_is_infeasible(request_, reason):
    sut = answered(request_)

    assert isinstance(sut, Infeasible | Invalid), sut
    assert reason in sut.reason


def test_a_cpu_copy_from_a_register_to_memory_is_a_store_and_from_memory_a_load():
    register, memory = Operand("vector", "f32", (8,)), Operand("global", "f32", (8,))

    store = answered(Request("avx2", "copy", {"src": register, "dst": memory}))
    loaded = answered(Request("avx2", "copy", {"src": memory, "dst": register}))

    assert isinstance(store, Feasible) and isinstance(loaded, Feasible)
    assert "store" in store.steps[0].spelling and "load" in loaded.steps[0].spelling
    assert store.request.op == "copy"


@pytest.mark.parametrize("op", [row.op for row in simt.rows()])
@pytest.mark.parametrize("target", ["sm90", "gfx942", "gfx90a"])
def test_a_device_row_answers_on_a_unit_its_target_lists_and_pinning_that_unit_is_feasible(target: str, op: str):
    sut = answered(Request(target, op))

    assert isinstance(sut, Feasible), sut
    assert sut.unit in UNITS[target] and all(step.unit == sut.unit for step in sut.steps)
    assert isinstance(answered(Request(target, op, unit=sut.unit)), Feasible)


@pytest.mark.parametrize("op", [row.op for row in simt.rows()])
def test_every_device_row_is_reachable_on_every_gpu_target(op: str):
    for target in ("sm90", "gfx942", "gfx90a"):
        sut = answered(Request(target, op))

        assert isinstance(sut, Feasible), sut
        assert sut.steps[0].spelling


@pytest.mark.parametrize(("request_", "reason"), [
    (Request("sm90", "fma", {"x": Operand("register", "f64")}), "computes in f32"),
    (Request("sm90", "fma", {"x": Operand("shared", "f32", (64, 64))}), "one thread on scalars"),
    (Request("avx2", "add", {"x": Operand("vector", "f64", (8,))}), "4 f64 lanes"),
    (Request("avx2", "add", {"a": Operand("vector", "f64", (4,)), "b": Operand("vector", "f32", (8,))}), "mix"),
    (Request("avx2", "add", {"a": Operand("vector", "f64", (4,))}, max_ulp=1.0), "add is exact"),
    (Request("tensix", "exp", {"x": Operand("tile_register", "f32", (7, 3))}), "one 32x32 tile"),
    (Request("tensix", "exp", {"x": Operand("tile_register", "f32", (32, 32))}, max_ulp=1.0), "one accuracy"),
    (Request("sme", "add"), "mma only"),
])  # fmt: skip
def test_an_elementwise_request_with_operands_the_row_does_not_compute_is_infeasible(request_, reason):
    sut = answered(request_)

    assert isinstance(sut, Infeasible | Invalid), sut
    assert reason in sut.reason


def test_a_math_function_without_a_bound_answers_its_strict_rung_with_code():
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
    Request("avx2", "copy", {"src": Operand("global", "f32", (3,)), "dst": Operand("vector", "f32", (3,))}),
    Request("avx2", "add", {"x": Operand("vector", "f64", (8,))}),
    Request("sm90", "fma", {"x": Operand("register", "f64")}),
    Request("tensix", "exp", {"x": Operand("tile_register", "f32", (7, 3))}),
    Request("sme", "add"),
])  # fmt: skip
def test_every_nearest_request_of_a_refusal_is_itself_feasible(refused: Request):
    sut = answered(refused)
    assert isinstance(sut, Infeasible) and sut.nearest

    for near in sut.nearest:
        operands = {name: Operand.parse(text) for name, text in (part.split(" ", 1) for part in near.split(", "))}
        op = "mma" if refused.target == "sme" else refused.op
        assert isinstance(answered(Request(refused.target, op, operands)), Feasible), near


def test_a_tile_program_that_fails_its_check_is_infeasible(monkeypatch: pytest.MonkeyPatch):
    def failing(plan_: tile.TilePlan) -> tile.TilePlan:
        return tile.replace_check(plan_, "failed", "relative error 0.5 against the f64 reference")

    monkeypatch.setattr(tile, "verify", failing)
    operands = {"a": Operand("global", "f32", (16, 8)), "b": Operand("global", "f32", (8, 16)),
                "c": Operand("global", "f32", (16, 16))}  # fmt: skip

    sut = ask(Request("avx2", "mma", operands))

    assert isinstance(sut, Infeasible) and "failed its check" in sut.reason


def test_a_device_row_whose_recorded_check_failed_is_infeasible(monkeypatch: pytest.MonkeyPatch):
    failed = {("fma", "cuda"): simt.Verdict("fma", "cuda", "an sm_90 device", ok=False, error="relative error 0.5")}
    monkeypatch.setattr(simt, "verdicts", lambda: failed)

    sut = answered(Request("sm90", "fma", {"x": Operand("register", "f32")}))

    assert isinstance(sut, Infeasible) and "relative error 0.5" in sut.reason


@pytest.mark.parametrize("operand", [
    "shared:f16:64y64", "smem:f16:64x64", "shared:f16:64x64:b128", "shared:f16:64x64:row_major:b128:extra",
    "shared:f16:0x64", "shared",
])  # fmt: skip
def test_the_cli_rejects_a_malformed_operand_as_a_usage_error_apart_from_infeasible(operand: str, capsys):
    code = main(["ask", "sm90", "mma", "--a", operand, "--b", "shared:f16:64x64", "--c", "register:f32:64x64"])

    printed = capsys.readouterr()
    assert code == 64 and "invalid (malformed_operand)" in printed.out and operand in printed.out


def test_the_cli_reads_a_target_in_any_case_and_an_lds_swizzle_with_its_colon(capsys):
    code = main(["ask", "GFX942", "copy", "--src", "global:f16:256x256", "--dst", "shared:f16:64x64:row_major:xor:8",
                 "--json"])  # fmt: skip

    sut = json.loads(capsys.readouterr().out)
    assert code == 0 and sut["unit"] == "lds" and sut["request"]["operands"]["dst"]["swizzle"] == "xor:8"


def test_an_operand_spells_back_to_what_parses_to_it():
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
    (Request("sm90", "mma", {"a": Operand("shared", "f16", (48, 64), "row_major", "b128"), "b": TILE["b"],
                             "c": Operand("register", "f32", (48, 64))}), Why.SHAPE),
    (Request("avx2", "add", {"x": Operand("vector", "f64", (8,))}), Why.SHAPE),
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
def test_every_refusal_carries_its_reason_code_and_the_class_the_code_belongs_to(request_: Request, why: Why):
    sut = answered(request_)

    assert not isinstance(sut, Feasible), sut
    assert sut.why is why, sut.reason
    assert isinstance(sut, Invalid if why in INVALID else Infeasible)
    assert sut.status == ("invalid" if why in INVALID else "infeasible") and sut.feasible is False


def test_the_reason_codes_split_into_invalid_and_infeasible_without_overlap():
    infeasible = set(Why) - INVALID

    assert INVALID and infeasible and Why.MALFORMED in INVALID
    assert {Why.UNIT, Why.NO_ROW, Why.ELEMENT_TYPE, Why.SHAPE, Why.SPACE, Why.SWIZZLE, Why.LAYOUT, Why.NO_RUNG,
            Why.NOT_COVERED, Why.CHECK_FAILED, Why.COMBINE} == infeasible  # fmt: skip


def test_an_sme_mma_takes_a_transposed_and_answers_fmopa_into_za():
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
def test_the_cli_exit_code_and_json_status_tell_feasible_infeasible_and_invalid_apart(argv, code, status, capsys):
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
):
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
def test_a_gpu_copy_is_checked_by_the_tile_program_that_runs_it(request_, header, monkeypatch):
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


def test_a_gpu_copy_whose_tile_program_fails_is_infeasible(monkeypatch):
    monkeypatch.setattr(tile, "verify", lambda plan_: tile.replace_check(plan_, "failed", "did not compile"))

    sut = ask(Request("sm90", "copy", {"src": GLOBAL, "dst": B128}))

    assert isinstance(sut, Infeasible)
    assert sut.why is Why.CHECK_FAILED


def test_a_tma_answer_states_the_shared_alignment_the_swizzle_needs():
    sut = answered(Request("sm90", "copy", {"src": GLOBAL, "dst": B128}))

    assert isinstance(sut, Feasible)
    assert "alignas(1024)" in sut.setup["shared tile"] and "barrier" in sut.setup


def test_a_per_thread_row_refuses_an_operand_in_memory_and_says_to_load_it():
    sut = answered(Request("sm90", "fma", {"x": Operand("global", "f32")}))

    assert isinstance(sut, Infeasible)
    assert sut.why is Why.SPACE and "register" in sut.fix
    assert sut.nearest == ("x register:f32",)


def test_a_per_thread_row_computes_in_its_table_element_type():
    half2 = next(row for row in simt.rows() if row.op == "add_half2")

    assert half2.dtype == "f16"
    assert {row.dtype for row in simt.rows() if row.op != "add_half2"} == {"f32"}
    assert isinstance(answered(Request("sm90", "add_half2", {"x": Operand("register", "f16")})), Feasible)
    assert answered(Request("sm90", "add_half2", {"x": Operand("register", "f32")})).status == "infeasible"


@pytest.mark.parametrize("target", sorted(tile.TYPES))
def test_every_tile_target_plans_exactly_the_type_pairs_it_declares(target):
    for in_type, acc_type in tile.TYPES[target]:
        assert tile.plan(target, 64, 64, 64, in_type, acc_type).in_type == in_type
    with pytest.raises(KeyError):
        tile.plan(target, 64, 64, 64, "bf16", "f32")


@pytest.mark.parametrize(("ok", "detail", "status"), [(True, "0.9 ulp", "run"), (None, "builds", "compiled"),
                                                      (None, "", "unverified")])  # fmt: skip
def test_a_math_kernel_answer_carries_the_kernel_gate_verdict(ok, detail, status, monkeypatch):
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


def test_a_math_kernel_that_fails_its_gate_is_infeasible(monkeypatch):
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


def recording(monkeypatch, verified: str = "compiled") -> list[tuple[str, int, int, int]]:
    seen: list[tuple[str, int, int, int]] = []

    def verify(plan_: tile.TilePlan) -> tile.TilePlan:
        seen.append((plan_.target, plan_.m, plan_.n, plan_.k))
        return tile.replace_check(plan_, verified, "the program's check")  # type: ignore[arg-type]

    monkeypatch.setattr(tile, "verify", verify)
    return seen


@pytest.mark.parametrize(("requests", "program"), [
    ([COPY_A, COPY_BT, WIDE_MMA], ("sm90", 256, 256, 128)),
    ([LDS_COPY, LDS_COPY, LDS_MMA], ("gfx942", 64, 64, 64)),
])  # fmt: skip
def test_copies_and_the_mma_they_fill_carry_the_check_of_the_one_tile_program_that_runs_them(
    requests, program, monkeypatch
):
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


def test_a_copy_of_b_as_k_rows_of_n_does_not_combine_and_the_nearest_copies_do():
    copy_b = Request("sm90", "copy", {"src": Operand("global", "f16", (128, 256)), "dst": BLOCK})

    sut = ask_all([COPY_A, copy_b, WIDE_MMA], verify=False)

    assert isinstance(sut, Infeasible) and sut.why is Why.COMBINE, sut
    assert sut.request == copy_b and "Bt" in sut.fix
    nearest = [copy_request("sm90", text) for text in sut.nearest]
    assert nearest and isinstance(ask_all([*nearest, WIDE_MMA], verify=False), Combined)


def test_a_copy_into_a_block_the_mma_does_not_load_does_not_combine():
    narrow = Request("sm90", "copy", {"src": Operand("global", "f16", (256, 128)), "dst": B128})

    sut = ask_all([narrow, WIDE_MMA], verify=False)

    assert isinstance(sut, Infeasible) and sut.why is Why.COMBINE
    assert "shared:f16:128x64:row_major:b128" in sut.reason


def test_two_mmas_do_not_combine_because_no_tile_program_runs_both():
    sut = ask_all([WIDE_MMA, WIDE_MMA], verify=False)

    assert isinstance(sut, Infeasible) and sut.why is Why.COMBINE


def test_requests_on_two_targets_are_invalid_as_one_kernel():
    sut = ask_all([COPY_A, LDS_MMA], verify=False)

    assert isinstance(sut, Invalid) and sut.why is Why.MIXED_TARGETS


def test_a_refused_request_in_a_list_is_refused_with_its_index():
    sut = ask_all([COPY_A, Request("sm90", "mma", TILE | {"b": B128})], verify=False)

    assert isinstance(sut, Infeasible) and sut.why is Why.LAYOUT
    assert sut.reason.startswith("request 1 (mma): ")


def test_a_kernel_whose_tile_program_fails_is_infeasible(monkeypatch):
    recording(monkeypatch, "failed")

    sut = ask_all([COPY_A, COPY_BT, WIDE_MMA])

    assert isinstance(sut, Infeasible) and sut.why is Why.CHECK_FAILED
    assert sut.reason.startswith("request 2 (mma): ")


def test_requests_no_program_runs_together_say_each_is_checked_alone():
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
def test_the_ask_all_cli_exit_code_and_json_status_tell_the_three_classes_apart(argv, code, status, capsys):
    exit_code = main(["ask-all", *argv, "--json", "--no-verify"])

    sut = json.loads(capsys.readouterr().out)
    assert exit_code == code and sut["status"] == status
