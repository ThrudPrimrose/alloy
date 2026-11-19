# Copyright 2026 ETH Zurich and the Alloy authors.
"""The Tensix backend of DaCe's tile nodes: expansions from the checked rows, the kernel split under contract v2,
and (mark ``tensix``) every eval task's program correct on ttsim."""

import dataclasses
import json
import re
import shutil

import pytest

pytest.importorskip("hpcagent_bench", reason="the eval tasks are bench kernels")

from dace.libraries.tileops.nodes import TileBinop, TileReduce, TileUnop

from alloy.hb_plugin import eval_set
from alloy.tensixgen import ttsim
from alloy.tensixgen.backend import IMPLEMENTATION, Refused, place, rule
from alloy.tensixgen.split import Options, Program, Slots
from alloy.tensixgen.tasks import programs, tile_sdfg


@pytest.fixture(scope="module")
def tasks() -> dict[str, dict]:
    return {t.name: dataclasses.asdict(t) for t in eval_set.admitted()[0]}


@pytest.fixture(scope="module")
def card(tasks: dict[str, dict]) -> dict[str, Program]:
    return {p.name: p for p in programs(list(tasks.values()))}


def test_a_call_gets_its_dst_tiles_in_place_of_the_checked_literals_and_nothing_else():
    sut = place("MATH((f<APPROX>(face, 0, (int)VectorMode::RC)))", "f", {1: "t * 2 + 1"})

    assert sut == "MATH((f<APPROX>(face, t * 2 + 1, (int)VectorMode::RC)))"
    with pytest.raises(ValueError, match="no DST tile"):
        place("fill_tile(0, 2.5f)", "fill_tile", {1: "3"})


def test_log_runs_its_sfpi_rung_on_the_card_which_measured_the_row_outside_the_task_tolerance_and_its_row_on_ttsim():
    card, sim, sin = rule("log", "v06"), rule("log", "v08"), rule("sin", "v06")

    assert card.source.startswith("rung alloy_log_f32_sfpi") and "alloy_log_f32_face" in card.code
    assert sim.call == "log_tile(0)" and sim.code == ""
    assert sin.call == "sin_tile(0)" and sin.code == ""


def test_the_tile_nodes_have_a_tensix_implementation():
    assert all(IMPLEMENTATION in node.implementations for node in (TileBinop, TileUnop, TileReduce))


def test_a_dst_tile_is_reused_only_after_its_last_reader():
    sut = Slots({"x": 2, "y": 1})

    x, y = sut.take("x"), sut.take("y")
    sut.read("x")
    assert not sut.dead(x)
    sut.read("x")
    assert sut.dead(x) and sut.take("z") == x != y


def test_every_eval_task_has_a_program_in_the_agents_layout(card: dict[str, Program], tmp_path):
    assert len(card) == 14

    folder = card["tsvc_2_s1351"].write(tmp_path / "tsvc_2_s1351")

    assert {p.name for p in folder.iterdir()} == {"reader.cpp", "compute.cpp", "writer.cpp", "config.json",
                                                   "program.json"}  # fmt: skip


def test_an_operand_read_after_an_in_place_op_is_copied_from_its_cb_again(card: dict[str, Program]):
    sut = card["transc_log_sincos_sum"].compute  # t feeds cos and sin

    assert len(re.findall(r"copy_tile\(0, t, ", sut)) == 2 and "alloy_log_f32_face" in sut


def test_a_reduction_adds_the_partial_tile_from_another_dst_tile_and_packs_it_through_cb_24(
    card: dict[str, Program],
):
    for name in ("transc_log_sincos_sum", "tsvc_2_s311", "tsvc_2_s313"):
        sut = card[name].compute

        result = re.search(r"pack_tile\((\d+), into\)", sut)
        spare = re.search(r"copy_tile\(24, 0, (\d+)\)", sut)
        assert result and spare and result.group(1) != spare.group(1), name
        assert '"unpack_to_dest_fp32": [0, 24]' in json.dumps(card[name].config) or "[0, 1, 24]" in json.dumps(
            card[name].config
        )


def test_a_scalar_becomes_a_filled_tile_with_the_benchs_value(card: dict[str, Program]):
    assert "fill_tile(t * 2 + 1, 2.0f)" in card["mat_scaled_add"].compute
    assert "fill_tile(t * 2 + 1, 1.0f)" in card["neg_stride_rev"].compute


def test_the_ttsim_spelling_differs_only_where_tt_metal_renamed(tasks: dict[str, dict], card: dict[str, Program]):
    (sim,) = programs([tasks["tsvc_2_s1351"]], version="v08")
    old = card["tsvc_2_s1351"].compute

    assert "void kernel_main()" in sim.compute and "copy_init(0);" in sim.compute
    assert "void MAIN" in old and "copy_tile_to_dst_init_short(0);" in old and "init_sfpu(0, 16);" in old
    assert (
        '#include "api/dataflow/dataflow_api.h"' in sim.reader
        and '#include "dataflow_api.h"' in card["tsvc_2_s1351"].reader
    )


def test_a_block_beyond_one_dst_acquire_is_refused(tasks: dict[str, dict]):
    sdfg, scalars = tile_sdfg("tsvc_2_s1351")
    from alloy.tensixgen.split import program

    with pytest.raises(Refused, match="exceed one DST acquire"):
        program(tasks["tsvc_2_s1351"], sdfg, scalars, Options(dst_block=3))


@pytest.mark.tensix
def test_every_eval_task_runs_correct_on_ttsim(tasks: dict[str, dict]):
    if shutil.which("docker") is None:
        pytest.fail("the tensix mark needs docker")

    found = [v for task in tasks.values() for v in ttsim.run_tasks([task], ttsim.default_cache())]

    assert [v.name for v in found if not v.ok] == [], found
