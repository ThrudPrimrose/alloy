# Copyright 2026 ETH Zurich and the Alloy authors.
"""Operand layouts as relayout index maps (alloy.isa.layouts): the named swizzles, their equality where they are one
map, and layouts given as relayout operations."""

import json
import pathlib
from collections.abc import Callable

import pytest

from alloy.isa import layouts
from alloy.isa.__main__ import main
from alloy.isa.ask import Feasible, Infeasible, Invalid, Operand, Request, Why, ask, parsed_request

#: The XOR swizzle of 128-byte rows as relayout operations: 16-byte chunk c of row i0 stored at c ^ (i0 % 8).
XOR8 = json.dumps([
    {"action": "block", "array": "x", "digit": "i1", "factor": 8, "into": ["c", "e"]},
    {"action": "shuffle", "array": "x", "digits": ["i0", "c"], "f": ["i0", "c ^ (i0 % 8)"], "f_inv": ["i0", "c ^ (i0 % 8)"]},
])  # fmt: skip
B_OPERAND = Operand("shared", "f16", (64, 64), "col_major", "b128")
C_OPERAND = Operand("register", "f32", (64, 64))


@pytest.mark.parametrize(("shape", "swizzle", "chunk"), [
    ((64, 64), "b128", lambda r, c: c ^ (r % 8)),
    ((64, 32), "b64", lambda r, c: c ^ ((r // 2) % 4)),
    ((64, 16), "b32", lambda r, c: c ^ ((r // 4) % 2)),
])  # fmt: skip
def test_the_sm90_swizzles_store_each_16_byte_chunk_where_cutlass_swizzle_b_4_3_puts_it(
    shape: tuple[int, int], swizzle: str, chunk: Callable[[int, int], int]
) -> None:
    rows, cols = shape

    sut = layouts.index_map(shape, "f16", "row_major", swizzle)

    assert sut == tuple(r * cols + chunk(r, c // 8) * 8 + c % 8 for r in range(rows) for c in range(cols))


def test_b128_and_xor8_are_one_map_on_128_byte_rows_and_a_misfit_swizzle_has_none() -> None:
    assert layouts.index_map((64, 64), "f16", "row_major", "b128") == layouts.index_map(
        (64, 64), "f16", "row_major", "xor:8"
    )
    assert layouts.index_map((64, 40), "f16", "row_major", "b128") is None  # 80-byte rows: not whole groups of chunks


def test_sm90_takes_a_tile_whose_map_is_its_128b_swizzle_under_another_name_and_says_so() -> None:
    for a in (
        Operand("shared", "f16", (64, 64), "row_major", "xor:8"),
        Operand("shared", "f16", (64, 64), relayout=XOR8),
    ):
        sut = ask(Request("sm90", "mma", {"a": a, "b": B_OPERAND, "c": C_OPERAND}), verify=False)

        assert isinstance(sut, Feasible), sut
        assert any(n.startswith("a: ") and "same index map as row_major:b128" in n for n in sut.notes), sut.notes


def test_sm90_refuses_a_tile_whose_map_is_another_swizzle() -> None:
    a = Operand("shared", "f16", (64, 64), "row_major", "b64")

    sut = ask(Request("sm90", "mma", {"a": a, "b": B_OPERAND, "c": C_OPERAND}), verify=False)

    assert isinstance(sut, Infeasible) and sut.why is Why.SWIZZLE, sut


@pytest.mark.parametrize(
    "given", ["[1]", "not json", json.dumps([{"action": "permute", "array": "x", "order": ["i0"]}])]
)
def test_relayout_operations_that_are_not_a_layout_of_the_operand_are_invalid(given: str) -> None:
    a = Operand("shared", "f16", (64, 64), relayout=given)

    sut = ask(Request("sm90", "mma", {"a": a, "b": B_OPERAND, "c": C_OPERAND}), verify=False)

    assert isinstance(sut, Invalid) and sut.why is Why.MALFORMED and "--a-layout" in sut.reason, sut


def test_the_cli_and_ask_all_take_a_layout_as_relayout_json(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = ["ask", "sm90", "mma", "--a", "shared:f16:64x64", "--a-layout", XOR8, "--b", "shared:f16:64x64:col_major:b128",
            "--c", "register:f32:64x64", "--no-verify"]  # fmt: skip
    assert main(argv) == 0 and "same index map" in capsys.readouterr().out
    (tmp_path / "a.json").write_text(XOR8)

    request = parsed_request(
        "sm90",
        f"mma a=shared:f16:64x64 a_layout=@{tmp_path / 'a.json'} b=shared:f16:64x64:col_major:b128 c=register:f32:64x64",
    )

    assert request.operands["a"].relayout == XOR8
