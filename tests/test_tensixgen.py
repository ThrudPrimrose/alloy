# Copyright 2026 ETH Zurich and the Alloy authors.
"""The Tensix backend of DaCe's tile nodes: expansions from the checked rows, the kernel split under contract v2,
and (mark ``tensix``) every eval task's program correct on ttsim."""

import dataclasses
import json
import pathlib
import re
import shutil

import dace
import pytest

pytest.importorskip("hpcagent_bench", reason="the eval tasks are bench kernels")

from dace import placement
from dace.libraries.tileops.nodes import TileReduce, TileUnop

from alloy.hb_plugin import eval_set
from alloy.jsontype import Json
from alloy.tensixgen import ttsim
from alloy.tensixgen.backend import Refused, code, op_of, place, rule
from alloy.tensixgen.split import SHARDED, Options, Program, Slots, placement_of, program
from alloy.tensixgen.tasks import programs, tile_sdfg


@pytest.fixture(scope="module")
def tasks() -> dict[str, Json]:
    return {t.name: dataclasses.asdict(t) for t in eval_set.admitted()[0]}


@pytest.fixture(scope="module")
def card(tasks: dict[str, Json]) -> dict[str, Program]:
    return {p.name: p for p in programs(list(tasks.values()))}


def test_a_call_gets_its_dst_tiles_in_place_of_the_checked_literals_and_nothing_else() -> None:
    sut = place("MATH((f<APPROX>(face, 0, (int)VectorMode::RC)))", "f", {1: "t * 2 + 1"})

    assert sut == "MATH((f<APPROX>(face, t * 2 + 1, (int)VectorMode::RC)))"
    with pytest.raises(ValueError, match="no DST tile"):
        place("fill_tile(0, 2.5f)", "fill_tile", {1: "3"})


def test_log_runs_its_sfpi_rung_on_the_card_which_measured_the_row_outside_the_task_tolerance_and_its_row_on_ttsim() -> (
    None
):
    card, sim, sin = rule("log", "v06"), rule("log", "v08"), rule("sin", "v06")

    assert card.source.startswith("rung alloy_log_f32_sfpi") and "alloy_log_f32_face" in card.code
    assert sim.call == "log_tile(0)" and sim.code == ""
    assert sin.call == "sin_tile(0)" and sin.code == ""


def test_a_unary_op_of_a_constant_is_refused_not_taken_for_a_filled_tile() -> None:
    with pytest.raises(Refused, match="exp of a Symbol"):
        op_of(TileUnop("e", (1024,), op="exp", kind_a="Symbol", expr_a="2.0"))


def test_a_max_reduction_is_refused_because_the_contracts_host_sums_the_partial_tiles() -> None:
    with pytest.raises(Refused, match="no Tensix row"):
        op_of(TileReduce("r", (1024,), op="max"))


def test_a_row_without_a_card_run_is_refused_for_the_cards_spelling_only() -> None:
    assert rule("neg", "v08").call.startswith("negative_tile")
    with pytest.raises(Refused, match="no card run"):
        rule("neg", "v06")


def test_a_non_finite_constant_is_refused() -> None:
    with pytest.raises(Refused, match="not finite"):
        code("broadcast", ("_c",), float("inf"))


def test_a_dst_tile_is_reused_only_after_its_last_reader() -> None:
    sut = Slots({"x": 2, "y": 1})

    x, y = sut.take("x"), sut.take("y")
    sut.read("x")
    assert not sut.dead(x)
    sut.read("x")
    assert sut.dead(x) and sut.take("z") == x != y


def test_every_eval_task_has_a_program_in_the_agents_layout(card: dict[str, Program], tmp_path: pathlib.Path) -> None:
    assert len(card) == 14

    folder = card["tsvc_2_s1351"].write(tmp_path / "tsvc_2_s1351")

    assert {p.name for p in folder.iterdir()} == {"reader.cpp", "compute.cpp", "writer.cpp", "config.json",
                                                   "program.json"}  # fmt: skip


def test_an_operand_read_after_an_in_place_op_is_copied_from_its_cb_again(card: dict[str, Program]) -> None:
    sut = card["transc_log_sincos_sum"].compute  # t feeds cos and sin

    assert len(re.findall(r"copy_tile\(0, t, ", sut)) == 2 and "alloy_log_f32_face" in sut


def test_a_reduction_adds_the_partial_tile_from_another_dst_tile_and_packs_it_through_cb_24(
    card: dict[str, Program],
) -> None:
    for name in ("transc_log_sincos_sum", "tsvc_2_s311", "tsvc_2_s313"):
        sut = card[name].compute

        result = re.search(r"pack_tile\((\d+), into\)", sut)
        spare = re.search(r"copy_tile\(24, 0, (\d+)\)", sut)
        assert result and spare and result.group(1) != spare.group(1), name
        assert '"unpack_to_dest_fp32": [0, 24]' in json.dumps(card[name].config) or "[0, 1, 24]" in json.dumps(
            card[name].config
        )


def test_a_scalar_becomes_a_filled_tile_with_the_benchs_value(card: dict[str, Program]) -> None:
    assert "fill_tile(t * 2 + 1, 2.0f)" in card["mat_scaled_add"].compute
    assert "fill_tile(t * 2 + 1, 1.0f)" in card["neg_stride_rev"].compute


def test_the_ttsim_spelling_differs_only_where_tt_metal_renamed(
    tasks: dict[str, Json], card: dict[str, Program]
) -> None:
    (sim,) = programs([tasks["tsvc_2_s1351"]], version="v08")
    old = card["tsvc_2_s1351"].compute

    assert "void kernel_main()" in sim.compute and "copy_init(0);" in sim.compute
    assert "void MAIN" in old and "copy_tile_to_dst_init_short(0);" in old and "init_sfpu(0, 16);" in old
    assert (
        '#include "api/dataflow/dataflow_api.h"' in sim.reader
        and '#include "dataflow_api.h"' in card["tsvc_2_s1351"].reader
    )


def test_a_block_beyond_one_dst_acquire_is_refused(tasks: dict[str, Json]) -> None:
    sdfg, scalars = tile_sdfg("tsvc_2_s1351")

    with pytest.raises(Refused, match="exceed one DST acquire"):
        program(tasks["tsvc_2_s1351"], sdfg, scalars, Options(dst_block=3))


def test_more_cores_than_tiles_are_refused_because_a_reduction_core_without_a_tile_hangs(
    tasks: dict[str, Json],
) -> None:
    sdfg, scalars = tile_sdfg("tsvc_2_s313")

    with pytest.raises(Refused, match="leave a core without a tile"):
        program(tasks["tsvc_2_s313"], sdfg, scalars, Options(cores=1025))


def test_a_strided_load_is_refused_not_read_as_consecutive_tiles() -> None:
    sdfg, scalars = tile_sdfg("tsvc_2_s111")  # a[2i + 1] = a[2i] + b[i]
    task = {"name": "tsvc_2_s111", "kind": "map", "inputs": [["a", 0.0, 1.0], ["b", 0.0, 1.0]], "output": "a",
            "program": ["a = a + b"]}  # fmt: skip

    with pytest.raises(Refused, match="not one tile of consecutive elements"):
        program(task, sdfg, scalars)


def test_a_row_sum_is_refused_not_taken_for_a_full_sum() -> None:
    sdfg = dace.SDFG("row_sum")
    sdfg.add_array("A", [32, 1024], dace.float32)
    sdfg.add_array("out", [32], dace.float32)
    state = sdfg.add_state()
    node = state.add_reduce("lambda a, b: a + b", [1], 0)
    state.add_edge(state.add_read("A"), None, node, None, dace.Memlet("A[0:32, 0:1024]"))
    state.add_edge(node, None, state.add_write("out"), None, dace.Memlet("out[0:32]"))
    task = {"name": "row_sum", "kind": "reduce", "inputs": [["A", 0.0, 1.0]], "output": "out",
            "program": ["out = A.sum(1)"]}  # fmt: skip

    with pytest.raises(Refused, match="not the whole input"):
        program(task, sdfg, {})


def record(p: Program) -> Json:
    descriptor: Json = json.loads(json.dumps(p.descriptor))
    return descriptor


def array(shape: tuple[object, ...], nodes: object, body: object) -> dace.data.Array:
    desc = dace.data.Array(dace.float32, shape)
    desc.placement = placement.Placement(nodes, placement.SymbolicLambda(body))  # pyright: ignore[reportArgumentType] -- test double
    return desc


def test_interleaved_tile_pages_and_height_shards_are_recognised() -> None:
    n, m, banks = dace.symbol("LEN_1D"), dace.symbol("M"), dace.symbol("NB")

    assert placement_of("x", dace.data.Array(dace.float32, (n,))) == 0
    assert placement_of("x", array((n,), banks, lambda i: (i // 1024) % banks)) == 0
    assert placement_of("x", array((m, n), banks, lambda i, j: ((i // 32) * (n // 32) + j // 32) % banks)) == 0
    assert placement_of("x", array((n,), 32, lambda i: (i // (n // 32)) % 32)) == 32
    assert placement_of("x", array((m, n), 64, lambda i, j: i // (m // 64))) == 64


@pytest.mark.parametrize(
    "shape, nodes, body, reason",
    [
        ((64, 64), 4, lambda i, j: (2 * (i // 2) + j // 3) % 4, "pages of one tile"),
        ((64, 64), 4, lambda i, j: (j // 16) % 4, "more than the outermost dimension"),
        ((96,), 3, lambda i: (i // 32) % 3, "a divisor of 1024"),
        ((1 << 20,), dace.symbol("P"), lambda i: (i // 1024) % 8, "a divisor of 1024"),
        ((1 << 20,), 32, lambda i: (i // 2048) % 32, "not one block of the outermost dimension per core"),
    ],
    ids=["pages_not_one_tile", "column_shards", "three_cores", "symbolic_cores", "block_cyclic_wraps"],
)
def test_a_placement_tt_metal_does_not_allocate_is_refused(
    shape: tuple[object, ...], nodes: object, body: object, reason: str
) -> None:
    with pytest.raises(Refused, match=reason):
        placement_of("x", array(shape, nodes, body))


def test_no_placement_generates_the_same_program_as_the_interleaved_placement(
    tasks: dict[str, Json], card: dict[str, Program]
) -> None:
    sdfg, scalars = tile_sdfg("tsvc_2_s1351")

    sut = program(tasks["tsvc_2_s1351"], sdfg, scalars)

    old = card["tsvc_2_s1351"]
    assert (sut.reader, sut.compute, sut.writer, sut.config) == (old.reader, old.compute, old.writer, old.config)
    assert record(sut)["placement"]["a"] == {"kind": "interleaved", "cores": 0, "tiles": 0, "map": None}


def test_a_sharded_map_reads_and_writes_its_cores_own_l1_shards(
    tasks: dict[str, Json], card: dict[str, Program]
) -> None:
    (sut,) = programs([tasks["tsvc_2_s1351"]], Options(cores=32, placement=SHARDED))

    assert "TensorAccessor" not in sut.reader + sut.writer and "start" not in sut.reader + sut.writer
    assert "noc_async_read(s1 + (i + t) * bytes1, w1 + t * bytes1, bytes1);" in sut.reader
    assert "const uint64_t s1 = get_noc_addr(get_arg_val<uint32_t>(3));" in sut.reader
    assert "noc_async_write(r + t * bytes, s + (i + t) * bytes, bytes);" in sut.writer
    assert sut.compute == card["tsvc_2_s1351"].compute
    assert sut.descriptor["options"] == {"dst_block": 2, "cores": 32, "placement": "sharded"}
    assert {k: (v["kind"], v["cores"], v["tiles"]) for k, v in record(sut)["placement"].items()} == dict.fromkeys(
        ("a", "b", "c"), ("sharded", 32, 32)
    )


def test_a_sharded_reduction_writes_its_partial_tiles_to_interleaved_dram(tasks: dict[str, Json]) -> None:
    (sut,) = programs([tasks["tsvc_2_s313"]], Options(cores=32, placement=SHARDED))

    assert "get_noc_addr" in sut.reader and "noc_async_write_tile(start + i + t, s, " in sut.writer
    assert record(sut)["placement"]["dot"]["kind"] == "interleaved"


def test_shards_beyond_the_l1_they_may_take_are_refused(tasks: dict[str, Json]) -> None:
    with pytest.raises(Refused, match="of L1 they may take"):
        programs([tasks["tsvc_2_s251"]], Options(cores=8, placement=SHARDED))  # 4 arrays of 128 tiles a core


def test_sharded_and_interleaved_arrays_of_one_map_are_refused(tasks: dict[str, Json]) -> None:
    sdfg, scalars = tile_sdfg("tsvc_2_vtv")
    n = sdfg.arrays["a"].shape[0]
    sdfg.arrays["a"].placement = placement.Placement(32, placement.SymbolicLambda(lambda i: (i // (n // 32)) % 32))

    with pytest.raises(Refused, match="one placement only"):
        program(tasks["tsvc_2_vtv"], sdfg, scalars)


def test_a_sharded_placement_without_the_cores_is_refused(tasks: dict[str, Json]) -> None:
    with pytest.raises(Refused, match="needs the cores"):
        programs([tasks["tsvc_2_vtv"]], Options(placement=SHARDED))


@pytest.mark.tensix
@pytest.mark.parametrize(
    "options",
    [Options(1), Options(0), Options(0, 32, SHARDED)],
    ids=["dst_block=1", "dst_block=max", "sharded,cores=32"],
)
def test_every_eval_task_runs_correct_on_ttsim(tasks: dict[str, Json], options: Options) -> None:
    if shutil.which("docker") is None:
        pytest.fail("the tensix mark needs docker")

    found = [v for task in tasks.values() for v in ttsim.run_tasks([task], ttsim.default_cache(), options)]

    assert [v.name for v in found if not v.ok] == [], found
