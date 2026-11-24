# Copyright 2026 ETH Zurich and the Alloy authors.
"""Lowering and code generation, without the toolchain or the simulator."""

import dace
import numpy
import pytest
from dace.libraries.comm.nodes import Allgather, Barrier, Gather
from dace.libraries.standard.nodes.copy import CopyLibraryNode
from dace.libraries.standard.nodes.sync import Sync, SyncScope
from dace.libraries.tileops import TileBinop, TileMMA, TileReduce, TileUnop
from dace.memlet import Memlet

from alloy import tilelower
from alloy.softhiergen import passes, program, storage
from alloy.softhiergen.library import collectives, dma, redmule, rvv, sync
from alloy.softhiergen.library.common import LoweringError


def copy_state(
    src_shape: tuple[int, ...], src_subset: str, dst_shape: tuple[int, ...], dst_subset: str
) -> tuple[dace.SDFG, dace.SDFGState, CopyLibraryNode]:
    sdfg = dace.SDFG("copy")
    sdfg.add_array("A", src_shape, dace.float32, storage=storage.HBM)
    sdfg.add_array("T", dst_shape, dace.float32, storage=storage.TCDM, transient=True)
    state = sdfg.add_state()
    node = CopyLibraryNode("copy")
    state.add_edge(state.add_read("A"), None, node, "_cpy_in", Memlet(f"A[{src_subset}]"))
    state.add_edge(node, "_cpy_out", state.add_write("T"), None, Memlet(f"T[{dst_subset}]"))
    return sdfg, state, node


def test_contiguous_copy_is_one_1d_transfer() -> None:
    """A run of 256 floats is one flex_dma_async_1d of 1024 bytes."""
    sdfg, state, node = copy_state((1024,), "256:512", (256,), "0:256")
    assert dma.dma_call(node, state, sdfg) == "dsh_dma_1d(dsh_addr(_cpy_out), dsh_addr(_cpy_in), 1024);"


def test_block_of_rows_is_a_2d_transfer_with_both_strides() -> None:
    """An 8 x 10 block of a 16 x 24 matrix into a packed tile: 8 rows of 40 bytes, source stride 96, dest 40."""
    sdfg, state, node = copy_state((16, 24), "3:11, 5:15", (8, 10), "0:8, 0:10")
    assert dma.dma_call(node, state, sdfg) == ("dsh_dma_2d(dsh_addr(_cpy_out), dsh_addr(_cpy_in), 40, 40, 96, 8);")


def test_column_copy_is_refused() -> None:
    """A strided column has no 1D or 2D transfer of contiguous rows."""
    sdfg, state, node = copy_state((16, 24), "0:16, 3", (16,), "0:16")
    with pytest.raises(LoweringError):
        dma.dma_call(node, state, sdfg)


def binop_state(kind_b: str) -> tuple[dace.SDFG, dace.SDFGState, dace.nodes.LibraryNode]:
    sdfg = dace.SDFG("binop")
    for name in ("a", "c"):
        sdfg.add_array(name, (64,), dace.float32, storage=storage.TCDM, transient=True)
    sdfg.add_scalar("s", dace.float32, transient=True)
    state = sdfg.add_state()
    node = TileBinop("sub", (64,), op="-", kind_a="Scalar", kind_b=kind_b, expr_b=None)
    state.add_node(node)
    state.add_edge(state.add_read("s"), None, node, "_a", Memlet("s[0]"))
    state.add_edge(state.add_read("a"), None, node, "_b", Memlet("a[0:64]"))
    state.add_edge(node, "_c", state.add_write("c"), None, Memlet("c[0:64]"))
    return sdfg, state, node


def test_scalar_minus_tile_takes_the_reversed_spatz_loop() -> None:
    """s - b is not b - s: the expansion calls the scalar-first loop."""
    sdfg, state, node = binop_state("Tile")
    tasklet = rvv.ExpandBinopRVV.expansion(node, state, sdfg)
    assert "dsh_rvv_sub_r_f32(_c, (float)(_a), _b, 64);" in tasklet.code.as_string
    assert "dsh_is_compute_core()" in tasklet.code.as_string


def test_tile_in_hbm_is_refused() -> None:
    """Spatz reads TCDM only; an HBM operand is a lowering error, not a silent wrong address."""
    sdfg, state, node = binop_state("Tile")
    sdfg.arrays["a"].storage = storage.HBM
    with pytest.raises(LoweringError):
        rvv.ExpandBinopRVV.expansion(node, state, sdfg)


def test_dma_gets_its_wait_and_a_barrier_before_its_reader() -> None:
    """After a DMA node: DmaWait, then a cluster Sync, which orders the reader of the copied tile."""
    sdfg, state, node = copy_state((1024,), "0:256", (256,), "0:256")
    entry, exit_node = state.add_map("k", {"c": "0:4"}, schedule=storage.DEVICE)
    reader = state.add_tasklet("use", {"x"}, {}, "")
    state.add_edge(entry, None, node, None, Memlet())
    written = next(e.dst for e in state.out_edges(node))
    state.add_edge(written, None, reader, "x", Memlet("T[0]"))
    state.add_edge(reader, None, exit_node, None, Memlet())
    node.implementation = dma.IMPLEMENTATION
    passes.insert_sync(sdfg)
    (wait,) = [n for n in state.nodes() if isinstance(n, sync.DmaWait)]
    (barrier,) = [n for n in state.nodes() if isinstance(n, Sync)]
    assert state.edges_between(node, wait) and state.edges_between(wait, barrier)
    assert state.edges_between(barrier, reader)


@dace.program
def vadd(A: dace.float32[2048], B: dace.float32[2048], C: dace.float32[2048]) -> None:
    C[:] = A + B


def test_vector_add_kernel_strides_over_clusters_and_uses_spatz() -> None:
    """8 tiles of 256 over 4 clusters: a strided loop, two DMA loads, one vfadd loop, one DMA store."""
    code = program.generate(vadd.to_sdfg(simplify=True))
    assert "for (int __it = __cid; __it < 8; __it += 4)" in code
    assert code.count("dsh_dma_1d(") == 3
    assert "dsh_rvv_add_f32(C_tile_out, A_tile, B_tile, 256);" in code
    assert 'extern "C" float A[];' in code


def test_relay_through_a_temporary_is_folded() -> None:
    """``s[:] = sum(x)`` writes the reduction straight into s, so no top-level copy is left."""

    @dace.program
    def total(x: dace.float32[1024], s: dace.float32[1]) -> None:
        s[:] = numpy.sum(x)

    sdfg = total.to_sdfg(simplify=True)
    passes.expand_whole_array_nodes(sdfg)
    top = [n for s in sdfg.states() for n in s.nodes() if s.entry_node(n) is None]
    assert not any(isinstance(n, (CopyLibraryNode, dace.nodes.Tasklet)) for n in top)


def unop_state(op: str) -> tuple[dace.SDFG, dace.SDFGState, dace.nodes.LibraryNode]:
    sdfg = dace.SDFG("unop")
    for name in ("a", "c"):
        sdfg.add_array(name, (64,), dace.float32, storage=storage.TCDM, transient=True)
    state = sdfg.add_state()
    node = TileUnop("u", (64,), op=op)
    state.add_node(node)
    state.add_edge(state.add_read("a"), None, node, "_a", Memlet("a[0:64]"))
    state.add_edge(node, "_c", state.add_write("c"), None, Memlet("c[0:64]"))
    return sdfg, state, node


def test_sqrt_is_one_spatz_loop_exp_a_loop_over_the_ladder_kernel_and_sin_is_refused() -> None:
    """sqrt maps to the vfsqrt loop; exp has no RVV instruction, so it is a scalar loop over the ladder's strict
    float32 kernel in the C unit the folder carries; sin is in neither set, so it is a lowering error."""
    sdfg, state, node = unop_state("sqrt")
    assert "dsh_rvv_sqrt_f32(_c, _a, 64);" in rvv.ExpandUnopRVV.expansion(node, state, sdfg).code.as_string
    sdfg, state, node = unop_state("exp")
    assert "dsh_scalar_exp_f32(_c, _a, 64);" in rvv.ExpandUnopRVV.expansion(node, state, sdfg).code.as_string
    unit = rvv.ladder_unit()
    for fn in rvv.LADDER:
        assert f"    for (int i = 0; i < n; ++i) z[i] = alloy_{fn}_f32_strict(x[i]);" in unit
    # newlib's rintf stops GVSoC: the unit rounds in one instruction, defined before the first kernel uses it
    assert unit.index("#define __builtin_rintf dsh_rintf") < unit.index("__builtin_rintf(")
    sdfg, state, node = unop_state("sin")
    with pytest.raises(LoweringError):
        rvv.ExpandUnopRVV.expansion(node, state, sdfg)


def test_2d_kernel_map_runs_every_iteration() -> None:
    """An 8 x 2 tile map on 4 clusters is one strided loop over its 16 iterations, not one iteration per cluster."""

    @dace.program
    def add2(A: dace.float32[8, 512], B: dace.float32[8, 512], C: dace.float32[8, 512]) -> None:
        C[:] = A + B

    code = program.generate(add2.to_sdfg(simplify=True))
    assert "for (int __it = __cid; __it < 16; __it += 4)" in code


def test_partial_copy_between_arrays_is_refused() -> None:
    """``C[2048:4096] = A[0:2048]`` keeps its subsets; the whole-array copy kernel refuses it instead of copying all
    of A over all of C."""

    @dace.program
    def part(A: dace.float32[4096], C: dace.float32[4096]) -> None:
        C[2048:4096] = A[0:2048]

    with pytest.raises(LoweringError, match="whole array"):
        program.generate(part.to_sdfg(simplify=True))


def kernel_with(node: dace.nodes.LibraryNode, size: int) -> dace.SDFG:
    """A kernel map of ``size`` iterations around ``node`` alone."""
    sdfg = dace.SDFG("kernel")
    state = sdfg.add_state()
    entry, exit_node = state.add_map("k", {"c": f"0:{size}"}, schedule=storage.DEVICE)
    state.add_node(node)
    state.add_edge(entry, None, node, None, Memlet())
    state.add_edge(node, None, exit_node, None, Memlet())
    return sdfg


def test_user_sync_in_a_kernel_gets_the_softhier_barrier() -> None:
    """A Sync node placed by the user expands to the cluster barrier, not to DaCe's default ``__syncthreads();``."""
    node = Sync("user_sync")
    passes.select_implementations(kernel_with(node, 4))
    assert node.implementation == sync.IMPLEMENTATION


def test_collective_in_a_map_of_more_iterations_than_clusters_is_refused() -> None:
    """With 8 iterations on 4 clusters a cluster calls the global barrier twice and the mesh deadlocks."""
    with pytest.raises(LoweringError, match="one iteration per cluster"):
        passes.select_implementations(kernel_with(Barrier("barrier"), 8))


def test_allgather_output_of_the_input_size_is_refused() -> None:
    """An allgather writes P times its input; an output of the input's size would be overrun."""
    from alloy.softhiergen.gate.programs import in_kernel

    with pytest.raises(LoweringError, match="allgather"):
        program.generate(in_kernel(lambda: Allgather("allgather"), 256, 256, False)())


def test_redmule_accumulator_must_be_the_output_container() -> None:
    """RedMulE accumulates into c in place, so ``_cin`` must be ``_c``'s container (DaCe's TileMMA convention)."""
    sdfg = dace.SDFG("mma")
    for name, shape in (("a", (16, 32)), ("b", (32, 48)), ("c", (16, 48)), ("d", (16, 48))):
        sdfg.add_array(name, shape, dace.float16, storage=storage.TCDM, transient=True)
    state = sdfg.add_state()
    node = TileMMA("mma", (16, 32, 48), beta=1)
    state.add_node(node)
    for conn, name in (("_a", "a"), ("_b", "b"), ("_cin", "d")):
        state.add_edge(state.add_read(name), None, node, conn, Memlet.from_array(name, sdfg.arrays[name]))
    state.add_edge(node, "_c", state.add_write("c"), None, Memlet.from_array("c", sdfg.arrays["c"]))
    with pytest.raises(LoweringError, match="same container"):
        redmule.ExpandMMARedMulE.expansion(node, state, sdfg)


def test_redmule_kernel_zeroes_c_passes_m_k_n_and_waits_before_the_store() -> None:
    """A 64 x 32 by 32 x 48 product on 4 clusters: RedMulE gets (16, 32, 48) in that order, c is zeroed first
    (beta 0), and the compute core waits for RedMulE before the DMA store of c."""

    @dace.program
    def mm(A: dace.float16[64, 32], B: dace.float16[32, 48], C: dace.float16[64, 48]) -> None:
        C[:] = A @ B

    code = program.generate(mm.to_sdfg(simplify=True))
    fill = code.index("dsh_rvv_fill_f16(c_tile, (dsh_f16)0, 768);")
    mma = code.index("dsh_redmule_mma(a_tile, b_tile, c_tile, 16, 32, 48);")
    assert fill < mma < code.index("dsh_redmule_wait();") < code.index("store_c_tile")


def test_copy_without_sync_gets_no_wait_and_no_barrier() -> None:
    """A copy with ``sync = False`` is left to the pass that cleared it, which places the wait and the barrier."""
    sdfg, state, node = copy_state((1024,), "0:256", (256,), "0:256")
    entry, exit_node = state.add_map("k", {"c": "0:4"}, schedule=storage.DEVICE)
    state.add_edge(entry, None, node, None, Memlet())
    state.add_edge(next(e.dst for e in state.out_edges(node)), None, exit_node, None, Memlet())
    node.implementation = dma.IMPLEMENTATION
    node.sync = False
    passes.insert_sync(sdfg)
    assert not any(isinstance(n, (sync.DmaWait, Sync)) for n in state.nodes())


def test_strided_rows_copy_strides_by_the_step() -> None:
    """X[0:16:2, 0:10] is 8 rows two matrix rows apart (192 bytes); a step inside the row has no iDMA transfer."""
    sdfg, state, node = copy_state((16, 24), "0:16:2, 0:10", (8, 10), "0:8, 0:10")
    assert dma.dma_call(node, state, sdfg) == "dsh_dma_2d(dsh_addr(_cpy_out), dsh_addr(_cpy_in), 40, 40, 192, 8);"
    sdfg, state, node = copy_state((8, 20), "0:8, 0:20:2", (8, 10), "0:8, 0:10")
    with pytest.raises(LoweringError):
        dma.dma_call(node, state, sdfg)


def mma_state(beta: int, cin: str | None) -> tuple[dace.SDFG, dace.SDFGState, dace.nodes.LibraryNode]:
    """A 16 x 32 by 32 x 48 TileMMA into the 16 x 48 TCDM array ``c``; ``_cin`` reads ``cin`` when given."""
    sdfg = dace.SDFG("mma")
    for name, shape in (("a", (16, 32)), ("b", (32, 48)), ("c", (16, 48))):
        sdfg.add_array(name, shape, dace.float16, storage=storage.TCDM, transient=True)
    state = sdfg.add_state()
    node = TileMMA("mma", (16, 32, 48), beta=beta)
    state.add_node(node)
    reads = [("_a", "a", "a[0:16, 0:32]"), ("_b", "b", "b[0:32, 0:48]")] + ([("_cin", "c", cin)] if cin else [])
    for conn, name, subset in reads:
        state.add_edge(state.add_read(name), None, node, conn, Memlet(subset))
    state.add_edge(node, "_c", state.add_write("c"), None, Memlet("c[0:16, 0:48]"))
    return sdfg, state, node


def test_spatz_stores_are_fenced_before_barriers_and_redmule() -> None:
    """Spatz stores land late: each Spatz tasklet ends with dsh_vfence, and RedMulE starts after the fenced fill."""
    sdfg, state, node = binop_state("Tile")
    code = rvv.ExpandBinopRVV.expansion(node, state, sdfg).code.as_string
    assert code.index("dsh_rvv_sub_r_f32(") < code.index("dsh_vfence();")
    sdfg, state, node = mma_state(0, None)
    code = redmule.ExpandMMARedMulE.expansion(node, state, sdfg).code.as_string
    assert code.index("dsh_rvv_fill_f16(") < code.index("dsh_vfence();") < code.index("dsh_redmule_mma(")


def test_redmule_accumulator_must_be_the_output_subset() -> None:
    """``_cin`` reading part of c while ``_c`` writes all of it: RedMulE would accumulate onto rows _cin never read."""
    sdfg, state, node = mma_state(1, "c[0:8, 0:48]")
    with pytest.raises(LoweringError, match="same container"):
        redmule.ExpandMMARedMulE.expansion(node, state, sdfg)


def test_grid_sync_in_a_map_of_more_iterations_than_clusters_is_refused() -> None:
    """A grid barrier meets every cluster once: 8 iterations on 4 clusters deadlock the mesh."""
    with pytest.raises(LoweringError, match="one iteration per cluster"):
        passes.select_implementations(kernel_with(Sync("grid", scope=SyncScope.GRID), 8))


def test_in_place_gather_is_refused() -> None:
    """A gather into its own input lets a peer's block overwrite the root's input before the root copies it."""
    sdfg = dace.SDFG("gather")
    sdfg.add_array("x", (1024,), dace.float32, storage=storage.TCDM, transient=True)
    state = sdfg.add_state()
    node = Gather("gather")
    state.add_node(node)
    state.add_edge(state.add_read("x"), None, node, "_inbuffer", Memlet("x[0:256]"))
    state.add_edge(node, "_outbuffer", state.add_write("x"), None, Memlet("x[0:1024]"))
    with pytest.raises(LoweringError, match="in place"):
        collectives.collective_tasklet(node, state, sdfg)


def tile_state(
    dtype: dace.typeclass, node: dace.nodes.LibraryNode, inputs: dict[str, str], output: tuple[str, str]
) -> tuple[dace.SDFG, dace.SDFGState, dace.nodes.LibraryNode]:
    """``node`` on 64-element TCDM tiles of ``dtype``: ``inputs`` connector -> array, ``output`` (connector, array)."""
    sdfg = dace.SDFG("tile")
    for name in (*inputs.values(), output[1]):
        sdfg.add_array(name, (64,), dtype, storage=storage.TCDM, transient=True)
    state = sdfg.add_state()
    state.add_node(node)
    for conn, name in inputs.items():
        state.add_edge(state.add_read(name), None, node, conn, Memlet(f"{name}[0:64]"))
    state.add_edge(node, output[0], state.add_write(output[1]), None, Memlet(f"{output[1]}[0:64]"))
    return sdfg, state, node


def test_int32_division_is_refused() -> None:
    """There is no Spatz loop for an integer division; it must not emit a call to a missing dsh_rvv_div_i32."""
    node = TileBinop("div", (64,), op="/", kind_a="Tile", kind_b="Tile")
    sdfg, state, node = tile_state(dace.int32, node, {"_a": "a", "_b": "b"}, ("_c", "c"))  # pyright: ignore[reportArgumentType] -- test double
    with pytest.raises(LoweringError, match="division"):
        rvv.ExpandBinopRVV.expansion(node, state, sdfg)


def test_float16_sum_is_refused() -> None:
    """The Spatz model has no widening reduction, so a float16 sum would accumulate in float16."""
    node = TileReduce("sum", (64,), op="+")
    sdfg, state, node = tile_state(dace.float16, node, {"_src": "a"}, ("_dst", "s"))  # pyright: ignore[reportArgumentType] -- test double
    with pytest.raises(LoweringError, match="float16 sum"):
        rvv.ExpandReduceRVV.expansion(node, state, sdfg)


def test_in_place_update_is_one_kernel_without_an_hbm_temporary() -> None:
    """``y[:] = a * x + y`` writes y in its kernel; no second copy kernel through an HBM array."""
    from alloy.softhiergen.gate.programs import axpy

    code = program.generate(axpy.to_sdfg(simplify=True))
    assert code.count("static void __dsh_kernel_") == 1
    assert '".hbm"' not in code


def test_length_the_tile_does_not_divide_is_a_lowering_error() -> None:
    """1000 elements do not split into tiles of 256: the shared front refuses it, as it does for Tensix."""

    @dace.program
    def odd(A: dace.float32[1000], B: dace.float32[1000], C: dace.float32[1000]) -> None:
        C[:] = A + B

    with pytest.raises(tilelower.Unsupported, match="tile width 256"):
        program.generate(odd.to_sdfg(simplify=True))


def test_ragged_length_takes_the_widest_tile_that_divides_it() -> None:
    """4000 elements: no tile of 256 divides them, 32 does, so the kernel runs 125 Spatz loops of 32."""
    from alloy.softhiergen.gate.programs import ragged

    code = program.generate(ragged.to_sdfg(simplify=True))
    assert "dsh_rvv_fma_f32(y_tile_out, x_tile, z_tile, x_tile_0, 32);" in code


def test_where_is_a_spatz_compare_then_select() -> None:
    """``numpy.where(x < z, x, z)`` compares into a bool tile and selects by it; ``relu`` selects a scalar arm."""
    from alloy.softhiergen.gate.programs import relu, where

    code = program.generate(where.to_sdfg(simplify=True))
    assert "dsh_rvv_lt_f32(" in code and "dsh_rvv_select_f32(y_tile_out" in code
    assert "dsh_rvv_select_es_f32(" in program.generate(relu.to_sdfg(simplify=True))


def test_int32_tiles_reach_the_spatz_loops_as_int32_t() -> None:
    """DaCe's int32 is ``int``, rv32 newlib's ``int32_t`` is ``long``: C++ refuses the pointer without the cast."""
    from alloy.softhiergen.gate.programs import at_least

    code = program.generate(at_least.to_sdfg(simplify=True))
    assert "dsh_rvv_ge_i32(y_tile_out, (int32_t*)" in code


def test_a_rooted_collective_keeps_the_copy_that_fills_its_output() -> None:
    """Gather writes its output on the root only: the other clusters store what the init copy loaded, so the shared
    front must not drop that copy as dead (dead-dataflow elimination did, and the gate's gather came out wrong)."""
    from alloy.softhiergen.gate.programs import collective_cases

    (gather,) = [case for case in collective_cases() if case.name == "gather"]
    assert "init_dma" in program.generate(gather.sdfg())


def test_cumsum_scans_each_share_and_adds_the_earlier_totals() -> None:
    """A cluster scans its share, the clusters allgather their totals, and each adds the totals before its own."""
    from alloy.softhiergen.gate.programs import cumsum

    code = program.generate(cumsum.to_sdfg(simplify=True))
    assert "dsh_allgather(" in code
    assert "dsh_rvv_add_s_f32(" in code
