# Copyright 2026 ETH Zurich and the Alloy authors.
"""Whole-array nodes of a NumPy program as SoftHier kernels.

The vectorizer turns elementwise maps into tile nodes but leaves a matrix product, a reduction, a copy between
arrays and a collective whole. Their ``SoftHierKernel`` expansion is a nested SDFG holding one ``SoftHier_Device``
map over the clusters; each cluster moves its share between HBM and TCDM with iDMA copy nodes and computes with tile
and communication nodes, which expand in turn. The pipeline inlines the nested SDFG.

shortcut: the leading dim is split evenly over the clusters (it must divide); a loop over tiles when one share no
longer fits in TCDM.
"""

from collections.abc import Callable
from typing import Any, ClassVar

import dace
from dace import data, dtypes, library
from dace.frontend.operations import detect_reduction_type
from dace.libraries.blas import Gemm, MatMul
from dace.libraries.comm.nodes import Allgather, Allreduce
from dace.libraries.standard import Reduce
from dace.libraries.standard.nodes.copy import CopyLibraryNode
from dace.libraries.standard.nodes.scan import Scan, ScanOp
from dace.libraries.tileops import TileBinop, TileMMA, TileReduce
from dace.libraries.tileops.kinds import SCALAR
from dace.libraries.tileops.nodes.tile_scan import TileScan
from dace.memlet import Memlet
from dace.sdfg import nodes
from dace.transformation.transformation import ExpandTransformation

from alloy.softhiergen import storage
from alloy.softhiergen.arch import V1
from alloy.softhiergen.library import collectives, dma, redmule, rvv
from alloy.softhiergen.library.common import LoweringError, edge_desc, in_edges, out_edges

IMPLEMENTATION = "SoftHierKernel"
#: The map parameter: the cluster.
CLUSTER = "c"

REDUCTIONS = {
    dtypes.ReductionType.Sum: ("+", "sum"),
    dtypes.ReductionType.Max: ("max", "max"),
    dtypes.ReductionType.Min: ("min", "min"),
}


class Kernel:
    """A nested SDFG with one map over the clusters; ``outer`` names the node's connectors' arrays."""

    def __init__(self, label: str, node: nodes.LibraryNode, state: dace.SDFGState, sdfg: dace.SDFG) -> None:
        self.sdfg = dace.SDFG(label)
        self.state = self.sdfg.add_state(is_start_block=True)
        for conn, edge in (*in_edges(state, node).items(), *out_edges(state, node).items()):
            desc = edge_desc(sdfg, edge)
            if edge.data.subset.num_elements_exact() != desc.total_size:  # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess] -- DaCe's annotation
                raise LoweringError(f"{node.label}: {conn} must be a whole array")
            inner = desc.clone()  # pyright: ignore[reportAttributeAccessIssue] -- DaCe's annotation
            inner.transient = False
            inner.storage = storage.HBM
            self.sdfg.add_datadesc(conn, inner)
        self.entry, self.exit = self.state.add_map(label, {CLUSTER: f"0:{V1.num_clusters}"}, schedule=storage.DEVICE)
        self.reads: dict[str, nodes.AccessNode] = {}
        self.writes: dict[str, nodes.AccessNode] = {}

    def share(self, conn: str) -> tuple[int, str]:
        """Rows per cluster of an array split along its leading dim, and the subset of cluster ``c``."""
        desc = self.sdfg.arrays[conn]
        rows = int(desc.shape[0])
        if rows % V1.num_clusters:
            raise LoweringError(f"{conn}: {rows} rows do not split over {V1.num_clusters} clusters")
        share = rows // V1.num_clusters
        rest = "".join(f", 0:{size}" for size in desc.shape[1:])
        return share, f"{conn}[{CLUSTER} * {share}:({CLUSTER} + 1) * {share}{rest}]"

    def tcdm(self, name: str, shape: tuple[int, ...], dtype: dtypes.typeclass) -> str:
        self.sdfg.add_array(name, shape, dtype, storage=storage.TCDM, transient=True)
        return name

    def load(self, conn: str, subset: str, tile: str) -> nodes.AccessNode:
        """An iDMA copy from HBM ``subset`` into the TCDM array ``tile``; the access node of ``tile``."""
        copy = CopyLibraryNode(f"load_{tile}")
        copy.implementation = dma.IMPLEMENTATION
        if conn not in self.reads:
            self.reads[conn] = self.state.add_read(conn)
        target = self.state.add_access(tile)
        self.state.add_memlet_path(self.reads[conn], self.entry, copy, dst_conn="_cpy_in", memlet=Memlet(subset))
        self.state.add_edge(copy, "_cpy_out", target, None, Memlet.from_array(tile, self.sdfg.arrays[tile]))
        return target

    def store(self, tile: nodes.AccessNode, conn: str, subset: str) -> None:
        copy = CopyLibraryNode(f"store_{tile.data}")
        copy.implementation = dma.IMPLEMENTATION
        if conn not in self.writes:
            self.writes[conn] = self.state.add_write(conn)
        self.state.add_edge(tile, None, copy, "_cpy_in", Memlet.from_array(tile.data, self.sdfg.arrays[tile.data]))
        self.state.add_memlet_path(copy, self.exit, self.writes[conn], src_conn="_cpy_out", memlet=Memlet(subset))

    def compute(
        self, node: nodes.LibraryNode, inputs: dict[str, nodes.AccessNode], output: str, conn: str
    ) -> nodes.AccessNode:
        """Adds ``node`` reading ``inputs`` (connector -> access node) and writing the TCDM array ``output``."""
        self.state.add_node(node)
        for dst_conn, access in inputs.items():
            desc = self.sdfg.arrays[access.data]
            self.state.add_edge(access, None, node, dst_conn, Memlet.from_array(access.data, desc))
        target = self.state.add_access(output)
        self.state.add_edge(node, conn, target, None, Memlet.from_array(output, self.sdfg.arrays[output]))
        return target


def expansion_of(
    build: Callable[[Any, dace.SDFGState, dace.SDFG], dace.SDFG],
) -> type[ExpandTransformation]:
    """An expansion class whose nested SDFG ``build(node, state, sdfg)`` returns."""

    @library.expansion
    class ExpandKernel(ExpandTransformation):
        environments: ClassVar[list[type]] = []

        @staticmethod
        def expansion(node: nodes.LibraryNode, parent_state: dace.SDFGState, parent_sdfg: dace.SDFG) -> dace.SDFG:
            return build(node, parent_state, parent_sdfg)

    return ExpandKernel


def matmul_kernel(node: MatMul | Gemm, state: dace.SDFGState, sdfg: dace.SDFG) -> dace.SDFG:
    """``C = A @ B`` (float16): cluster ``c`` takes a block of rows of A and C and all of B; RedMulE multiplies."""
    if isinstance(node, Gemm) and (node.alpha != 1 or node.beta != 0 or node.transA or node.transB):
        raise LoweringError(f"{node.label}: SoftHier computes C = A @ B (alpha 1, beta 0, no transposes)")
    kernel = Kernel(f"{node.label}_softhier", node, state, sdfg)
    a, b, c = (kernel.sdfg.arrays[conn] for conn in ("_a", "_b", "_c"))
    if not all(isinstance(desc, data.Array) and len(desc.shape) == 2 for desc in (a, b, c)):
        raise LoweringError(f"{node.label}: SoftHier multiplies two matrices")
    rows, a_share = kernel.share("_a")
    _, c_share = kernel.share("_c")
    k, n = (int(size) for size in b.shape)
    a_tile = kernel.load("_a", a_share, kernel.tcdm("a_tile", (rows, k), a.dtype))
    b_tile = kernel.load("_b", f"_b[0:{k}, 0:{n}]", kernel.tcdm("b_tile", (k, n), b.dtype))
    mma = TileMMA("mma", (rows, k, n), beta=0)
    mma.implementation = redmule.IMPLEMENTATION
    c_tile = kernel.compute(mma, {"_a": a_tile, "_b": b_tile}, kernel.tcdm("c_tile", (rows, n), c.dtype), "_c")
    kernel.store(c_tile, "_c", c_share)
    return kernel.sdfg


def reduce_kernel(node: Reduce, state: dace.SDFGState, sdfg: dace.SDFG) -> dace.SDFG:
    """A full reduction of a vector: each cluster reduces its share with Spatz, an allreduce combines the partial
    results in rank order, and every cluster writes the same value."""
    kernel = Kernel(f"{node.label}_softhier", node, state, sdfg)
    source = kernel.sdfg.arrays["_in"]
    reduction = detect_reduction_type(node.wcr)
    if reduction not in REDUCTIONS or len(source.shape) != 1 or node.axes not in (None, [0], (0,)):
        raise LoweringError(f"{node.label}: SoftHier reduces a whole vector with +, max or min")
    tile_op, comm_op = REDUCTIONS[reduction]
    share, subset = kernel.share("_in")
    part = kernel.load("_in", subset, kernel.tcdm("part", (share,), source.dtype))
    tile = TileReduce("reduce_tile", (share,), op=tile_op)
    tile.implementation = rvv.IMPLEMENTATION
    partial = kernel.compute(tile, {"_src": part}, kernel.tcdm("partial", (1,), source.dtype), "_dst")
    combine = Allreduce("combine", op=comm_op)
    combine.implementation = collectives.IMPLEMENTATION
    total = kernel.compute(combine, {"_inbuffer": partial}, kernel.tcdm("total", (1,), source.dtype), "_outbuffer")
    kernel.store(total, "_out", "_out[0]")
    return kernel.sdfg


#: Scan ops with a SoftHier kernel: the tile op, and the C that folds the lower clusters' totals into the offset.
SCANS = {ScanOp.SUM: ("+", "off = off + t"), ScanOp.MAX: ("max", "off = t > off ? t : off"),
         ScanOp.MIN: ("min", "off = t < off ? t : off")}  # fmt: skip


def scan_kernel(node: Scan, state: dace.SDFGState, sdfg: dace.SDFG) -> dace.SDFG:
    """An inclusive scan of a vector: each cluster scans its share, an allgather shares the share totals, and each
    cluster combines its scan with the totals of the clusters before it."""
    if (
        node.op not in SCANS
        or node.exclusive
        or node.chains != 1
        or str(node.stride) != "1"
        or ("_scan_init" in in_edges(state, node))
    ):
        raise LoweringError(f"{node.label}: SoftHier scans inclusively with +, max or min, one chain, no init")
    kernel = Kernel(f"{node.label}_softhier", node, state, sdfg)
    source = kernel.sdfg.arrays["_scan_in"]
    if len(source.shape) != 1:
        raise LoweringError(f"{node.label}: SoftHier scans a vector")
    tile_op, fold = SCANS[node.op]
    share, subset = kernel.share("_scan_in")
    _, out_subset = kernel.share("_scan_out")
    part = kernel.load("_scan_in", subset, kernel.tcdm("part", (share,), source.dtype))
    scan = TileScan("scan_tile", (share,), op=tile_op)
    scan.implementation = rvv.IMPLEMENTATION
    scanned = kernel.compute(scan, {"_src": part}, kernel.tcdm("scanned", (share,), source.dtype), "_dst")
    total = TileReduce("total_tile", (share,), op=tile_op)
    total.implementation = rvv.IMPLEMENTATION
    mine = kernel.compute(total, {"_src": part}, kernel.tcdm("mine", (1,), source.dtype), "_dst")
    share_totals = Allgather("share_totals")
    share_totals.implementation = collectives.IMPLEMENTATION
    clusters = V1.num_clusters
    totals = kernel.compute(
        share_totals, {"_inbuffer": mine}, kernel.tcdm("totals", (clusters,), source.dtype), "_outbuffer"
    )
    # Every core folds the same values into the same offset: no role guard, and no barrier before the vector loop
    # that reads it on the core that wrote it
    seed = "0" if node.op == ScanOp.SUM else "_totals[0]"
    # Pointer connectors, as the guarded tasklets take: the SoftHier target defines no scalar output memlet
    offset = kernel.state.add_tasklet(
        "offset",
        {"_totals": dtypes.pointer(source.dtype)},
        {"_off": dtypes.pointer(source.dtype)},
        f"{source.dtype.ctype} off = {seed};\nfor (int r = {0 if node.op == ScanOp.SUM else 1}; r < {CLUSTER}; ++r) {{\n"
        f"    {source.dtype.ctype} t = _totals[r];\n    {fold};\n}}\n_off[0] = off;",
        language=dtypes.Language.CPP,
    )
    kernel.state.add_edge(
        totals, None, offset, "_totals", Memlet.from_array(totals.data, kernel.sdfg.arrays[totals.data])
    )
    off = kernel.state.add_access(kernel.tcdm("off", (1,), source.dtype))
    kernel.state.add_edge(offset, "_off", off, None, Memlet("off[0:1]"))
    combine = TileBinop("combine", (share,), op=tile_op, kind_b=SCALAR)
    combine.implementation = rvv.IMPLEMENTATION
    result = kernel.compute(combine, {"_a": scanned, "_b": off}, kernel.tcdm("result", (share,), source.dtype), "_c")
    kernel.store(result, "_scan_out", out_subset)
    return kernel.sdfg


def copy_kernel(node: CopyLibraryNode, state: dace.SDFGState, sdfg: dace.SDFG) -> dace.SDFG:
    """A copy between two HBM arrays: each cluster moves its share HBM -> TCDM -> HBM."""
    kernel = Kernel(f"{node.label}_softhier", node, state, sdfg)
    source = kernel.sdfg.arrays["_cpy_in"]
    share, src_subset = kernel.share("_cpy_in")
    _, dst_subset = kernel.share("_cpy_out")
    shape = (share, *(int(size) for size in source.shape[1:]))
    tile = kernel.load("_cpy_in", src_subset, kernel.tcdm("staged", shape, source.dtype))
    kernel.store(tile, "_cpy_out", dst_subset)
    return kernel.sdfg


def allreduce_kernel(node: Allreduce, state: dace.SDFGState, sdfg: dace.SDFG) -> dace.SDFG:
    """An allreduce over the rows of an HBM array: row ``c`` is cluster ``c``'s buffer."""
    kernel = Kernel(f"{node.label}_softhier", node, state, sdfg)
    buffer = kernel.sdfg.arrays["_inbuffer"]
    share, in_subset = kernel.share("_inbuffer")
    _, out_subset = kernel.share("_outbuffer")
    shape = (share, *(int(size) for size in buffer.shape[1:]))
    mine = kernel.load("_inbuffer", in_subset, kernel.tcdm("mine", shape, buffer.dtype))
    inner = Allreduce("allreduce", op=node.op)
    inner.implementation = collectives.IMPLEMENTATION
    reduced = kernel.compute(inner, {"_inbuffer": mine}, kernel.tcdm("reduced", shape, buffer.dtype), "_outbuffer")
    kernel.store(reduced, "_outbuffer", out_subset)
    return kernel.sdfg


for node_type, build in (
    (MatMul, matmul_kernel),
    (Gemm, matmul_kernel),
    (Reduce, reduce_kernel),
    (CopyLibraryNode, copy_kernel),
    (Allreduce, allreduce_kernel),
    (Scan, scan_kernel),
):
    node_type.register_implementation(IMPLEMENTATION, expansion_of(build))
