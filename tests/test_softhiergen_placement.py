"""Arrays placed over the HBM nodes: the checks, the element positions, the iDMA addresses and the split of copies,
and main.c's scatter with read_results' gather."""

import itertools
import json
import pathlib
import shutil
import subprocess
from collections.abc import Callable
from typing import Any

import dace
import numpy
import pytest
from dace import placement
from dace.libraries.standard.nodes.copy import CopyLibraryNode
from dace.memlet import Memlet
from dace.sdfg.state import SDFGState

from alloy.softhiergen import hbm, passes, program, storage
from alloy.softhiergen.arch import node_bases
from alloy.softhiergen.library import dma
from alloy.softhiergen.library.common import LoweringError

RUNTIME = pathlib.Path(program.__file__).parent / "runtime" / "include"

#: An index map over an array's indices: the node that holds the element
IndexMap = Callable[..., object]


def place(nodes: int, index_map: IndexMap) -> placement.Placement:
    return placement.Placement(nodes, placement.SymbolicLambda(index_map))


def test_node_bases_follow_the_channel_placement() -> None:
    """The v1 model has channels west and south: west0, west1, south0, south1, each 64 MiB apart on its edge."""
    assert node_bases() == [
        ("west0", 0xC0000000),
        ("west1", 0xC4000000),
        ("south0", 0xD8000000),
        ("south1", 0xDC000000),
    ]


@pytest.mark.parametrize(
    "nodes, index_map, shape",
    [
        (4, lambda i: (i // 128) % 4, (4096,)),
        (4, lambda i: i // 1024, (4096,)),
        (3, lambda i, j: (j // 8) % 3, (16, 24)),
        (4, lambda i, j: 2 * ((i // 32) % 2) + (j // 32) % 2, (64, 64)),
        (4, lambda i, j: (2 * (i // 32) + j // 32) % 4, (64, 64)),
    ],
)
def test_positions_are_node_times_share_plus_offset(nodes: int, index_map: IndexMap, shape: tuple[int, ...]) -> None:
    """Each element's position in the shares laid end to end is node * share + offset, and no two elements meet."""
    desc = dace.data.Array(dace.float32, shape)
    desc.placement = place(nodes, index_map)
    share = hbm.share_size(desc, {})
    found = hbm.positions(desc, {})
    for flat, idx in enumerate(itertools.product(*map(range, shape))):
        offset = int(desc.placement.offset_of(idx, shape))
        assert found[flat] == int(desc.placement.node_of(idx)) * share + offset and offset < share
    assert len(set(found.tolist())) == found.size


@pytest.mark.parametrize(
    "nodes, index_map, reason",
    [
        (5, lambda i: (i // 128) % 5, "5 nodes"),
        (2, lambda i: i % 4, "not exactly 2"),
        (1, lambda i: 0, "capacity"),
    ],
)
def test_placement_the_nodes_cannot_hold_is_refused(nodes: int, index_map: IndexMap, reason: str) -> None:
    """More nodes than the model has, node ids outside 0 .. nodes - 1, and a share larger than one node all refuse."""
    desc = dace.data.Array(dace.float32, (32 * 1024 * 1024,))
    desc.placement = place(nodes, index_map)
    with pytest.raises(LoweringError, match=reason):
        hbm.node_count("X", desc, {})


def copy_sdfg(
    shape: tuple[int, ...],
    index_map: IndexMap,
    nodes: int,
    hbm_subset: str,
    tile_shape: tuple[int, ...],
    tile_subset: str,
    params: dict[str, str],
    load: bool = True,
) -> tuple[dace.SDFG, SDFGState, CopyLibraryNode]:
    """A copy between the placed HBM array X and the TCDM array t inside a map over ``params``."""
    sdfg = dace.SDFG("placed_copy")
    sdfg.add_array("X", shape, dace.float32, storage=storage.HBM)
    sdfg.arrays["X"].placement = place(nodes, index_map)
    sdfg.add_array("t", tile_shape, dace.float32, storage=storage.TCDM, transient=True)
    state = sdfg.add_state()
    entry, exit_node = state.add_map("k", params, schedule=storage.DEVICE)
    node = CopyLibraryNode("copy")
    if load:
        state.add_memlet_path(state.add_read("X"), entry, node, dst_conn="_cpy_in", memlet=Memlet(f"X[{hbm_subset}]"))
        state.add_edge(node, "_cpy_out", state.add_access("t"), None, Memlet(f"t[{tile_subset}]"))
        state.add_nedge(next(e.dst for e in state.out_edges(node)), exit_node, Memlet())
    else:
        tile = state.add_access("t")
        state.add_nedge(entry, tile, Memlet())
        state.add_edge(tile, None, node, "_cpy_in", Memlet(f"t[{tile_subset}]"))
        state.add_memlet_path(
            node, exit_node, state.add_write("X"), src_conn="_cpy_out", memlet=Memlet(f"X[{hbm_subset}]")
        )
    return sdfg, state, node


def run_on_host(
    tmp_path: pathlib.Path,
    sdfg: dace.SDFG,
    state: SDFGState,
    node: CopyLibraryNode,
    params: dict[str, range],
    load: bool,
) -> tuple[str, Any]:
    """Runs the copy's iDMA code on the host for every value of the map parameters, the transfers as memcpy: from
    shares holding X's element indices into t (load), or from t holding 1000 + its element index into the shares,
    which come back gathered (store). Returns the code and, per parameter value, t or X."""
    code = dma.dma_call(node, state, sdfg)
    desc, tile = sdfg.arrays["X"], sdfg.arrays["t"]
    count, share = hbm.node_count("X", desc, {}), hbm.share_size(desc, {})
    shares = numpy.zeros(count * share, dtype=numpy.float32)
    positions = hbm.positions(desc, {})
    shares[positions] = numpy.arange(positions.size)
    names = ", ".join(f"node{k}" for k in range(count))
    nodes = "\n".join(
        f"static float node{k}[{share}] = {{{', '.join(map(str, shares[k * share : (k + 1) * share]))}}};"
        for k in range(count)
    )
    loops = "".join(f"for (int {name} : {{{', '.join(map(str, values))}}}) " for name, values in params.items())
    if load:
        body = f'float* _cpy_out = t;\n{code}\nfor (int i = 0; i < {tile.total_size}; ++i) printf("%g ", t[i]);'
        after = ""
    else:
        body = f"for (int i = 0; i < {tile.total_size}; ++i) t[i] = 1000 + i;\nfloat* _cpy_in = t;\n{code}"
        after = f'for (float* node : __dsh_X_nodes) for (int i = 0; i < {share}; ++i) printf("%g ", node[i]);'
    source = f"""#include <cstdint>
#include <cstdio>
#include <cstring>
#include <initializer_list>
#include "softhiergen/dsh_math.h"
{nodes}
static float* const __dsh_X_nodes[] = {{{names}}};
static float t[{tile.total_size}];
static uint64_t dsh_addr(const void* p) {{ return (uint64_t)(uintptr_t)p; }}
static void dsh_dma_1d(uint64_t dst, uint64_t src, uint32_t bytes) {{ memcpy((void*)dst, (const void*)src, bytes); }}
static void dsh_dma_2d(uint64_t dst, uint64_t src, uint32_t row, uint32_t dst_stride, uint32_t src_stride,
                       uint32_t rows) {{
    for (uint32_t r = 0; r < rows; ++r) dsh_dma_1d(dst + r * dst_stride, src + r * src_stride, row);
}}
int main() {{
    {loops}{{
        {body}
        printf("\\n");
    }}
    {after}
    return 0;
}}
"""
    (tmp_path / "copy.cpp").write_text(source)
    binary = tmp_path / "copy"
    subprocess.run(["g++", "-std=c++17", "-I", str(RUNTIME), "-o", str(binary), str(tmp_path / "copy.cpp")], check=True)
    out = subprocess.run([str(binary)], check=True, capture_output=True, text=True).stdout.splitlines()
    if load:
        return code, [numpy.array(line.split(), dtype=numpy.float32) for line in out]
    return code, numpy.array(out[-1].split(), dtype=numpy.float32)[positions].reshape(desc.shape)


host = pytest.mark.skipif(shutil.which("g++") is None, reason="needs a host g++")


@host
@pytest.mark.parametrize("block, split", [(512, False), (256, False), (128, True), (96, True)])
def test_tile_load_is_one_transfer_inside_a_block_and_cut_at_block_ends(
    tmp_path: pathlib.Path, block: int, split: bool
) -> None:
    """A 256-element tile of a 1D array placed (i // block) % 4: one transfer when the block holds whole tiles, else
    one per run, cut where a block ends; on the host every tile comes back equal to X's slice."""
    shape, nodes = (3072,), 4
    sdfg, state, node = copy_sdfg(
        shape, lambda i: (i // block) % nodes, nodes, "__i0:__i0 + 256", (256,), "0:256", {"__i0": f"0:{shape[0]}:256"}
    )
    starts = range(0, shape[0], 256)
    code, tiles = run_on_host(tmp_path, sdfg, state, node, {"__i0": starts}, True)
    assert ("for (" in code) == split
    for start, tile in zip(starts, tiles, strict=True):
        numpy.testing.assert_array_equal(tile, numpy.arange(start, start + 256))


def test_alignment_needs_every_map_value_on_a_tile_boundary() -> None:
    """A tile start is proven a multiple of the tile only when the map's first value and step are."""
    assert dma.multiple_of(dace.symbolic.pystr_to_symbolic("16 * c"), 16, {"c": (0, 1)})
    assert dma.multiple_of(dace.symbolic.pystr_to_symbolic("i"), 256, {"i": (512, 256)})
    assert not dma.multiple_of(dace.symbolic.pystr_to_symbolic("i"), 256, {"i": (8, 256)})
    assert not dma.multiple_of(dace.symbolic.pystr_to_symbolic("i"), 256, {"i": (0, 128)})
    assert not dma.multiple_of(dace.symbolic.pystr_to_symbolic("i + n"), 256, {"i": (0, 256)})


@host
def test_2d_block_cyclic_whole_array_load_is_cut_per_row_and_block(tmp_path: pathlib.Path) -> None:
    """A 64 x 64 array in 32 x 32 blocks over 2 x 2 nodes, loaded whole: two runs per row, landing in row order."""
    index_map = lambda i, j: 2 * ((i // 32) % 2) + (j // 32) % 2
    sdfg, state, node = copy_sdfg((64, 64), index_map, 4, "0:64, 0:64", (64, 64), "0:64, 0:64", {"c": "0:1"})
    code, tiles = run_on_host(tmp_path, sdfg, state, node, {"c": range(1)}, True)
    assert "__room = 32" in code
    numpy.testing.assert_array_equal(tiles[0], numpy.arange(64 * 64))


@host
def test_row_block_load_stays_on_one_node_as_one_transfer(tmp_path: pathlib.Path) -> None:
    """Rows 16c .. 16c + 15 of a 64 x 64 array placed (i // 16) % 4 are one node's contiguous share: one 1D transfer."""
    sdfg, state, node = copy_sdfg(
        (64, 64), lambda i, j: (i // 16) % 4, 4, "16 * c:16 * c + 16, 0:64", (16, 64), "0:16, 0:64", {"c": "0:4"}
    )
    code, tiles = run_on_host(tmp_path, sdfg, state, node, {"c": range(4)}, True)
    assert code.startswith("dsh_dma_1d(") and code.endswith(", 4096);")
    for c, tile in enumerate(tiles):
        numpy.testing.assert_array_equal(tile, numpy.arange(c * 1024, (c + 1) * 1024))


@host
def test_page_cyclic_store_writes_every_element_to_its_page(tmp_path: pathlib.Path) -> None:
    """Each cluster stores 16 rows into a 64 x 64 array of 32 x 32 pages dealt round-robin to 4 nodes; gathered back,
    X holds every cluster's rows."""
    index_map = lambda i, j: (2 * (i // 32) + j // 32) % 4
    sdfg, state, node = copy_sdfg(
        (64, 64), index_map, 4, "16 * c:16 * c + 16, 0:64", (16, 64), "0:16, 0:64", {"c": "0:4"}, load=False
    )
    _, gathered = run_on_host(tmp_path, sdfg, state, node, {"c": range(4)}, False)
    numpy.testing.assert_array_equal(gathered, numpy.tile(1000 + numpy.arange(1024), 4).reshape(64, 64))


@host
def test_strided_rows_of_a_placed_matrix_land_packed(tmp_path: pathlib.Path) -> None:
    """X[0:16:2, 0:10] of a 16 x 24 matrix placed (j // 8) % 3: every other row, cut at column 8, packed into t."""
    sdfg, state, node = copy_sdfg(
        (16, 24), lambda i, j: (j // 8) % 3, 3, "0:16:2, 0:10", (8, 10), "0:8, 0:10", {"c": "0:1"}
    )
    _, tiles = run_on_host(tmp_path, sdfg, state, node, {"c": range(1)}, True)
    numpy.testing.assert_array_equal(tiles[0], numpy.arange(16 * 24).reshape(16, 24)[0:16:2, 0:10].ravel())


def test_copy_between_two_placed_arrays_is_refused() -> None:
    """Both sides placed would need a node table on each side of one transfer; the copy is refused."""
    sdfg, state, node = copy_sdfg((1024,), lambda i: (i // 256) % 4, 4, "0:256", (256,), "0:256", {"c": "0:1"})
    sdfg.arrays["t"].placement = place(1, lambda i: 0)
    with pytest.raises(LoweringError, match="two placed arrays"):
        dma.dma_call(node, state, sdfg)


def test_tasklet_on_a_placed_array_is_refused() -> None:
    """Only a copy computes a placed array's element addresses; a tasklet reading it in a kernel is refused."""
    sdfg = dace.SDFG("placed_tasklet")
    sdfg.add_array("X", (4,), dace.float32)
    sdfg.add_array("Y", (4,), dace.float32)
    state = sdfg.add_state()
    _, entry, _ = state.add_mapped_tasklet(
        "k", {"c": "0:4"}, {"x": Memlet("X[c]")}, "y = x", {"y": Memlet("Y[c]")}, external_edges=True
    )
    entry.map.schedule = storage.DEVICE  # a kernel, as lower() schedules it (its front refuses a 4-element map)
    sdfg.arrays["X"].placement = place(4, lambda i: i % 4)
    with pytest.raises(LoweringError, match="placed array X"):
        passes.check_placed_access(sdfg)


def test_main_scatters_shares_into_node_sections_and_results_gather_them(tmp_path: pathlib.Path) -> None:
    """main.c holds one array per node in its section, each 64-byte padded; dumping the shares in node order and
    reading them back gives the logical array."""
    sdfg = dace.SDFG("scatter")
    sdfg.add_array("X", (16, 24), dace.float32)
    sdfg.arrays["X"].placement = place(3, lambda i, j: (j // 8) % 3)
    values = numpy.arange(16 * 24, dtype=numpy.float32).reshape(16, 24) - 7
    source, meta = program.main_unit(sdfg, {"X": values})
    words = []
    for k, section in enumerate((".hbm", ".dsh_hbm1", ".dsh_hbm2")):
        line = next(line for line in source.splitlines() if f"__dsh_X_node{k}[128]" in line)
        assert f'section("{section}")' in line
        literals = line.split("{")[1].rstrip("};").split(", ")
        words += (
            numpy.array([float.fromhex(v.rstrip("f")) for v in literals], dtype=numpy.float32)
            .view(numpy.uint32)
            .tolist()
        )
    (tmp_path / "meta.json").write_text(json.dumps(meta))
    (tmp_path / "gvsoc.out").write_text("\n".join(f"DSH X {w:x}" for w in words))
    arrays, _ = program.read_results(tmp_path)
    numpy.testing.assert_array_equal(arrays["X"], values)
