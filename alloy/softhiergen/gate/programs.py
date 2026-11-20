# Copyright 2026 ETH Zurich and the Alloy authors.
"""The gate's NumPy programs, each with its inputs and its NumPy reference."""

from collections.abc import Callable
from dataclasses import dataclass

import dace
import numpy
from dace.libraries.comm.nodes import Allgather, Allreduce, Alltoall, Bcast, Gather, Reduce, ReduceScatter, Scatter
from dace.libraries.standard.nodes.copy import CopyLibraryNode
from dace.libraries.standard.nodes.sync import Sync, SyncScope
from dace.memlet import Memlet

from alloy.softhiergen import program, storage

N = 4096
#: Clusters of the v1 mesh: the allreduce has one row per cluster.
P = 4


@dace.program
def vadd(A: dace.float32[N], B: dace.float32[N], C: dace.float32[N]) -> None:
    C[:] = A + B


@dace.program
def axpy(a: dace.float32, x: dace.float32[N], y: dace.float32[N]) -> None:
    y[:] = a * x + y


@dace.program
def vmul16(A: dace.float16[N], B: dace.float16[N], C: dace.float16[N]) -> None:
    C[:] = A * B


@dace.program
def scalar_first(a: dace.float32, x: dace.float32[N], y: dace.float32[N], z: dace.float32[N]) -> None:
    y[:] = a / x
    z[:] = a - x


@dace.program
def vsum(x: dace.float32[N], s: dace.float32[1]) -> None:
    s[:] = numpy.sum(x)


@dace.program
def vmax(x: dace.float32[N], s: dace.float32[1]) -> None:
    s[:] = numpy.max(x)


@dace.program
def unary(x: dace.float32[N], y: dace.float32[N]) -> None:
    y[:] = -numpy.sqrt(numpy.abs(x))


@dace.program
def gemm(A: dace.float16[64, 64], B: dace.float16[64, 64], C: dace.float16[64, 64]) -> None:
    C[:] = A @ B


@dace.program
def copy_chain(A: dace.float32[N], C: dace.float32[N]) -> None:
    B = numpy.empty_like(A)
    B[:] = A
    C[:] = B


def allreduce() -> dace.SDFG:
    """``dace.comm.Allreduce(X, "MPI_SUM")`` as the frontend builds it (an in-place node on ``X``); the frontend
    itself needs mpi4py. Row ``c`` of ``X`` is cluster ``c``'s buffer."""
    sdfg = dace.SDFG("allreduce")
    sdfg.add_array("X", (P, 1024), dace.float32)
    state = sdfg.add_state()
    node = Allreduce("_Allreduce_", "MPI_SUM")
    state.add_edge(state.add_read("X"), None, node, "_inbuffer", Memlet("X[0:4, 0:1024]"))
    state.add_edge(node, "_outbuffer", state.add_write("X"), None, Memlet("X[0:4, 0:1024]"))
    return sdfg


def in_kernel(
    make: Callable[[], dace.nodes.LibraryNode], in_cols: int, out_cols: int, root: bool
) -> Callable[[], dace.SDFG]:
    """A kernel in which cluster c loads row c of X into TCDM, runs the collective, and stores its output to row c of
    Y: the collectives beyond the gate, each on the simulator. A rooted collective defines its output on the root only,
    so its output first holds row c of Y: the other clusters store Y unchanged."""

    def build() -> dace.SDFG:
        node = make()
        sdfg = dace.SDFG(f"collective_{node.label}")
        sdfg.add_array("X", (P, in_cols), dace.float32)
        sdfg.add_array("Y", (P, out_cols), dace.float32)
        sdfg.add_array("x", (in_cols,), dace.float32, storage=storage.TCDM, transient=True)
        sdfg.add_array("y", (out_cols,), dace.float32, storage=storage.TCDM, transient=True)
        state = sdfg.add_state()
        entry, exit_node = state.add_map("k", {"c": f"0:{P}"}, schedule=storage.DEVICE)
        load, store = CopyLibraryNode("load"), CopyLibraryNode("store")
        x, y = state.add_access("x"), state.add_access("y")
        state.add_memlet_path(state.add_read("X"), entry, load, dst_conn="_cpy_in", memlet=Memlet(f"X[c, 0:{in_cols}]"))
        state.add_edge(load, "_cpy_out", x, None, Memlet(f"x[0:{in_cols}]"))
        state.add_edge(x, None, node, "_inbuffer", Memlet(f"x[0:{in_cols}]"))
        state.add_edge(node, "_outbuffer", y, None, Memlet(f"y[0:{out_cols}]"))
        if root:
            init, before = CopyLibraryNode("init"), state.add_access("y")
            state.add_memlet_path(
                state.add_read("Y"), entry, init, dst_conn="_cpy_in", memlet=Memlet(f"Y[c, 0:{out_cols}]")
            )
            state.add_edge(init, "_cpy_out", before, None, Memlet(f"y[0:{out_cols}]"))
            state.add_edge(before, None, node, None, Memlet())
        state.add_edge(y, None, store, "_cpy_in", Memlet(f"y[0:{out_cols}]"))
        state.add_memlet_path(
            store, exit_node, state.add_write("Y"), src_conn="_cpy_out", memlet=Memlet(f"Y[c, 0:{out_cols}]")
        )
        if root:
            sdfg.add_scalar("r", dace.int32, transient=True)
            tasklet = state.add_tasklet("root", {}, {"o"}, "o = 0")
            state.add_edge(entry, None, tasklet, None, Memlet())
            state.add_edge(tasklet, "o", state.add_access("r"), None, Memlet("r[0]"))
            state.add_edge(
                next(n for n in state.nodes() if isinstance(n, dace.nodes.AccessNode) and n.data == "r"),
                None,
                node,
                "_root",
                Memlet("r[0]"),
            )
        return sdfg

    return build


@dataclass(frozen=True)
class Case:
    name: str
    sdfg: Callable[[], dace.SDFG]
    inputs: program.Inputs
    #: The arrays the program must leave, by name
    expected: dict[str, numpy.ndarray]
    #: max |out - ref| / max |ref|
    tolerance: float


def cases() -> list[Case]:
    rng = numpy.random.default_rng(7)
    f32 = numpy.float32
    a, b = rng.uniform(-4, 4, N).astype(f32), rng.uniform(-4, 4, N).astype(f32)
    alpha = f32(1.5)
    pos = rng.uniform(0.5, 1.0, N).astype(f32)
    ga, gb = (rng.uniform(-1, 1, (64, 64)).astype(numpy.float16) for _ in range(2))
    rows = rng.uniform(-4, 4, (P, 1024)).astype(f32)
    return [
        Case("vector add", lambda: vadd.to_sdfg(simplify=True), {"A": a, "B": b}, {"C": a + b}, 1e-6),
        Case(
            "float16 multiply",
            lambda: vmul16.to_sdfg(simplify=True),
            {"A": ga.ravel(), "B": gb.ravel()},
            {"C": (ga.ravel().astype(numpy.float64) * gb.ravel()).astype(numpy.float16)},
            1e-3,
        ),
        Case("axpy", lambda: axpy.to_sdfg(simplify=True), {"a": alpha, "x": a, "y": b}, {"y": alpha * a + b}, 1e-6),
        Case(
            "scalar first (s / x, s - x)",
            lambda: scalar_first.to_sdfg(simplify=True),
            {"a": alpha, "x": pos},
            {"y": alpha / pos.astype(numpy.float64), "z": alpha - pos.astype(numpy.float64)},
            1e-6,
        ),
        Case(
            "sum reduction",
            lambda: vsum.to_sdfg(simplify=True),
            {"x": pos},
            {"s": pos.astype(numpy.float64).sum(keepdims=True)},
            1e-5,
        ),
        Case("max reduction", lambda: vmax.to_sdfg(simplify=True), {"x": a}, {"s": a.max(keepdims=True)}, 0.0),
        Case(
            "tiled GEMM (RedMulE)",
            lambda: gemm.to_sdfg(simplify=True),
            {"A": ga, "B": gb},
            {"C": (ga.astype(numpy.float64) @ gb.astype(numpy.float64)).astype(numpy.float16)},
            1e-3,
        ),
        Case(
            "unary (neg, abs, sqrt)",
            lambda: unary.to_sdfg(simplify=True),
            {"x": a},
            {"y": -numpy.sqrt(numpy.abs(a.astype(numpy.float64)))},
            1e-6,
        ),
        Case("copy chain", lambda: copy_chain.to_sdfg(simplify=False), {"A": a}, {"C": a}, 0.0),
        Case(
            "allreduce",
            allreduce,
            {"X": rows},
            {"X": numpy.broadcast_to(rows.astype(numpy.float64).sum(axis=0), rows.shape)},
            1e-6,
        ),
    ]


def block_copy(subset: str) -> dace.SDFG:
    """``Y[:] = X[subset]`` (8 x 10) in one kernel: the block reaches TCDM by a 2D iDMA transfer."""
    sdfg = dace.SDFG("block_copy")
    sdfg.add_array("X", (16, 24), dace.float32)
    sdfg.add_array("Y", (8, 10), dace.float32)
    sdfg.add_array("t", (8, 10), dace.float32, storage=storage.TCDM, transient=True)
    state = sdfg.add_state()
    entry, exit_node = state.add_map("k", {"c": "0:1"}, schedule=storage.DEVICE)
    load, store, tile = CopyLibraryNode("load"), CopyLibraryNode("store"), state.add_access("t")
    state.add_memlet_path(state.add_read("X"), entry, load, dst_conn="_cpy_in", memlet=Memlet(f"X[{subset}]"))
    state.add_edge(load, "_cpy_out", tile, None, Memlet("t[0:8, 0:10]"))
    state.add_edge(tile, None, store, "_cpy_in", Memlet("t[0:8, 0:10]"))
    state.add_memlet_path(store, exit_node, state.add_write("Y"), src_conn="_cpy_out", memlet=Memlet("Y[0:8, 0:10]"))
    return sdfg


def grid_sync() -> dace.SDFG:
    """Cluster c stores row c of X to row P - 1 - c of Y, a user's grid ``Sync`` between load and store."""
    sdfg = dace.SDFG("grid_sync")
    sdfg.add_array("X", (P, 256), dace.float32)
    sdfg.add_array("Y", (P, 256), dace.float32)
    sdfg.add_array("x", (256,), dace.float32, storage=storage.TCDM, transient=True)
    state = sdfg.add_state()
    entry, exit_node = state.add_map("k", {"c": f"0:{P}"}, schedule=storage.DEVICE)
    load, store, barrier = CopyLibraryNode("load"), CopyLibraryNode("store"), Sync("grid", scope=SyncScope.GRID)
    x = state.add_access("x")
    state.add_memlet_path(state.add_read("X"), entry, load, dst_conn="_cpy_in", memlet=Memlet("X[c, 0:256]"))
    state.add_edge(load, "_cpy_out", x, None, Memlet("x[0:256]"))
    state.add_edge(x, None, barrier, None, Memlet())
    state.add_edge(barrier, None, store, None, Memlet())
    state.add_edge(x, None, store, "_cpy_in", Memlet("x[0:256]"))
    state.add_memlet_path(
        store, exit_node, state.add_write("Y"), src_conn="_cpy_out", memlet=Memlet(f"Y[{P - 1} - c, 0:256]")
    )
    return sdfg


def collective_cases() -> list[Case]:
    """The other collectives, rank c = cluster c, root 0; 256 floats per rank; and the 2D iDMA copy."""
    n = 256
    X = numpy.random.default_rng(9).uniform(-4, 4, (P, P * n)).astype(numpy.float32)
    blocks = X.reshape(P, P, n)  # blocks[r, c]: rank r's block for rank c
    first = X[:, :n]
    gathered = first.reshape(1, P * n)
    matrix = numpy.arange(16 * 24, dtype=numpy.float32).reshape(16, 24)
    # The output rows a rooted reduce or gather leaves alone (every row but the root's)
    kept, kept_wide = -first, -X
    reduced, gathered_wide = kept.astype(numpy.float64), kept_wide.copy()
    reduced[0], gathered_wide[0] = first.astype(numpy.float64).sum(0), gathered
    return [
        Case("2D copy", lambda: block_copy("3:11, 5:15"), {"X": matrix}, {"Y": matrix[3:11, 5:15]}, 0.0),
        Case("strided rows copy", lambda: block_copy("0:16:2, 0:10"), {"X": matrix}, {"Y": matrix[0:16:2, 0:10]}, 0.0),
        Case("grid barrier", grid_sync, {"X": first}, {"Y": first[::-1]}, 0.0),
        Case(
            "bcast",
            in_kernel(lambda: Bcast("bcast"), n, n, True),
            {"X": first},
            {"Y": numpy.broadcast_to(first[0], (P, n))},
            0.0,
        ),
        Case(
            "reduce",
            in_kernel(lambda: Reduce("reduce", op="MPI_SUM"), n, n, True),
            {"X": first, "Y": kept},
            {"Y": reduced},
            1e-6,
        ),
        Case(
            "allgather",
            in_kernel(lambda: Allgather("allgather"), n, P * n, False),
            {"X": first},
            {"Y": numpy.broadcast_to(gathered, (P, P * n))},
            0.0,
        ),
        Case(
            "gather",
            in_kernel(lambda: Gather("gather"), n, P * n, True),
            {"X": first, "Y": kept_wide},
            {"Y": gathered_wide},
            0.0,
        ),
        Case("scatter", in_kernel(lambda: Scatter("scatter"), P * n, n, True), {"X": X}, {"Y": blocks[0]}, 0.0),
        Case(
            "reduce_scatter",
            in_kernel(lambda: ReduceScatter("reduce_scatter", op="MPI_SUM"), P * n, n, False),
            {"X": X},
            {"Y": blocks.astype(numpy.float64).sum(0)},
            1e-6,
        ),
        Case(
            "alltoall",
            in_kernel(lambda: Alltoall("alltoall"), P * n, P * n, False),
            {"X": X},
            {"Y": blocks.transpose(1, 0, 2).reshape(P, P * n)},
            0.0,
        ),
    ]
