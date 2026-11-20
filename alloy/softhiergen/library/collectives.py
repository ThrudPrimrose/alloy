# Copyright 2026 ETH Zurich and the Alloy authors.
"""DaCe's communication nodes inside a SoftHier kernel: the ranks are the clusters of the mesh and the buffers TCDM
arrays. Each expands to one call of the runtime (``dsh_rt.c``): iDMA pushes into the peers' TCDM between global
barriers, Spatz combining the slots of a reduction in rank order.

shortcut: an all-to-all pattern runs as P turns of one sender each (all at once hangs the v1 model);
a ring or tree when meshes grow past a few clusters.
"""

from typing import ClassVar

import dace
from dace import dtypes, library
from dace.libraries.comm import utils
from dace.libraries.comm.nodes import (
    Allgather,
    Allreduce,
    Alltoall,
    Barrier,
    Bcast,
    Gather,
    Reduce,
    ReduceScatter,
    Scatter,
)
from dace.sdfg import nodes
from dace.transformation.transformation import ExpandTransformation

from alloy.softhiergen.arch import V1
from alloy.softhiergen.library.common import (
    LoweringError,
    edge_desc,
    in_edges,
    out_edges,
    pointer_to,
    side_effect_tasklet,
    tcdm_tile_reason,
)

IMPLEMENTATION = "SoftHier"

DTYPE_CODES = {dtypes.float32: "DSH_F32", dtypes.float16: "DSH_F16", dtypes.int32: "DSH_I32"}
OP_CODES = {"sum": "DSH_SUM", "prod": "DSH_PROD", "max": "DSH_MAX", "min": "DSH_MIN"}
#: The collectives whose runtime call reads its whole input before any cluster writes an output (dsh_rt.c).
IN_PLACE = (Allreduce, Reduce, ReduceScatter, Bcast)
#: (a, b) of each collective: its buffer sizes in elements satisfy ``a * in_count == b * out_count``.
COUNTS = {
    Allreduce: (1, 1),
    Reduce: (1, 1),
    Bcast: (1, 1),
    Alltoall: (1, 1),
    Allgather: (V1.num_clusters, 1),
    Gather: (V1.num_clusters, 1),
    Scatter: (1, V1.num_clusters),
    ReduceScatter: (1, V1.num_clusters),
}


def collective_tasklet(node: nodes.LibraryNode, state: dace.SDFGState, sdfg: dace.SDFG) -> nodes.Tasklet:
    """The tasklet calling the runtime collective of ``node``; every core of every cluster runs it."""
    ins, outs = in_edges(state, node), out_edges(state, node)
    buffers = {conn: edge for conn, edge in (*ins.items(), *outs.items()) if conn in ("_inbuffer", "_outbuffer")}
    for conn, edge in buffers.items():
        reason = tcdm_tile_reason(sdfg, edge, f"{node.label}: {conn}")
        if reason is not None:
            raise LoweringError(reason)
    inp, out = buffers["_inbuffer"], buffers["_outbuffer"]
    # The others write a peer's output while that peer still sends from its input (dsh_rt.c)
    if inp.data.data == out.data.data and not isinstance(node, IN_PLACE):
        raise LoweringError(f"{node.label}: a {type(node).__name__} in place on {inp.data.data} is not supported")
    dtype = edge_desc(sdfg, inp).dtype
    in_count, out_count = int(inp.data.subset.num_elements_exact()), int(out.data.subset.num_elements_exact())  # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess] -- DaCe's annotation
    clusters = V1.num_clusters
    a, b = COUNTS[type(node)]  # pyright: ignore[reportArgumentType] -- DaCe's annotation
    if a * in_count != b * out_count or (isinstance(node, Alltoall) and in_count % clusters):
        raise LoweringError(
            f"{node.label}: buffers of {in_count} and {out_count} elements do not fit a {type(node).__name__} over "
            f"{clusters} clusters"
        )
    scratch = ""
    if isinstance(node, (Allreduce, Reduce, ReduceScatter)):
        if dtype not in DTYPE_CODES:
            raise LoweringError(f"{node.label}: SoftHier reduces float32, float16 or int32, not {dtype}")
        op = utils.reduction_op(node.op)
        if op not in OP_CODES:
            raise LoweringError(f"{node.label}: SoftHier reduces with sum, prod, max or min, not {op}")
        if op == "sum" and dtype == dtypes.float16:  # pyright: ignore[reportOperatorIssue] -- DaCe's annotation
            raise LoweringError(f"{node.label}: a float16 sum would accumulate in float16")
        count = out_count
        scratch = f'static {dtype.ctype} __scratch[{clusters * count}] __attribute__((section(".l1"), aligned(64)));\n'
        tail = f"__scratch, {count}, {DTYPE_CODES[dtype]}, {OP_CODES[op]}"
        call = {
            Allreduce: f"dsh_allreduce(_outbuffer, _inbuffer, {tail});",
            Reduce: f"dsh_reduce(_outbuffer, _inbuffer, {tail}, _root);",
            ReduceScatter: f"dsh_reduce_scatter(_outbuffer, _inbuffer, {tail});",
        }[type(node)]
    else:
        size = dtype.bytes
        call = {  # pyright: ignore[reportArgumentType] -- DaCe's annotation
            Bcast: f"dsh_bcast(_outbuffer, _inbuffer, {in_count * size}, _root);",
            Allgather: f"dsh_allgather(_outbuffer, _inbuffer, {in_count * size});",
            Gather: f"dsh_gather(_outbuffer, _inbuffer, {in_count * size}, _root);",
            Scatter: f"dsh_scatter(_outbuffer, _inbuffer, {out_count * size}, _root);",
            Alltoall: f"dsh_alltoall(_outbuffer, _inbuffer, {in_count // clusters * size});",
        }[type(node)]
    inputs: dict[str, dtypes.typeclass | None] = {"_inbuffer": pointer_to(sdfg, inp)}
    if "_root" in ins:
        inputs["_root"] = None
    return nodes.Tasklet(
        node.label,
        inputs=inputs,
        outputs={"_outbuffer": pointer_to(sdfg, out)},
        code=scratch + call,
        language=dtypes.Language.CPP,
        side_effects=True,
    )


def register(node_type: type[nodes.LibraryNode]) -> None:
    @library.register_expansion(node_type, IMPLEMENTATION)  # pyright: ignore[reportArgumentType] -- DaCe's annotation
    class ExpandSoftHier(ExpandTransformation):
        environments: ClassVar[list[type]] = []

        @staticmethod
        def expansion(node: nodes.LibraryNode, parent_state: dace.SDFGState, parent_sdfg: dace.SDFG) -> nodes.Tasklet:
            return collective_tasklet(node, parent_state, parent_sdfg)


for collective in (Allreduce, Reduce, ReduceScatter, Bcast, Allgather, Gather, Scatter, Alltoall):
    register(collective)


@library.register_expansion(Barrier, IMPLEMENTATION)  # pyright: ignore[reportArgumentType] -- DaCe's annotation
class ExpandBarrierSoftHier(ExpandTransformation):
    environments: ClassVar[list[type]] = []

    @staticmethod
    def expansion(node: nodes.LibraryNode, parent_state: dace.SDFGState, parent_sdfg: dace.SDFG) -> nodes.Tasklet:
        return side_effect_tasklet(parent_state, node.label, "dsh_global_barrier();")
