# Copyright 2026 ETH Zurich and the Alloy authors.
"""The Tensix kernel split: a vectorized SDFG (DaCe's tile nodes at 1024 lanes, ``tensix`` implementations from
:mod:`alloy.tensixgen.backend`) partitioned into ``reader.cpp``, ``compute.cpp`` and ``writer.cpp`` with their
circular buffers, under the eval contract v2 (alloy-tenstorrent ``agents/SPEC.md``, "Eval tasks: the whole device").

Contract v2: the host splits the 1024 tiles of each float32 array over the cores. Reader args are ``[n, start,
addr...]``, input k (in the task's order) into CB k; the output leaves through CB 16. A map writes its tiles at the
same indices (writer args ``[n, start, out]``); a reduction writes one tile of partial results per core (``[1,
core_index, out]``), which the host folds in float64.

The tile body's loads become the reader and ``copy_tile`` from the CBs, its store the writer and ``pack_tile``, and
every compute node the code of its ``tensix`` expansion, on DST tiles assigned in order (a DST tile is reused once
its last reader has run). ``dst_block`` tiles go through one DST acquire, op by op, so an init is issued once per
block. A reduction folds the block's tiles and the running partial tile (CB 24) into one.

Each array's DaCe placement (``data.Array.placement``) says where its tiles lie: none or one tile per page dealt
round-robin over the DRAM banks is interleaved DRAM, read and written through a ``TensorAccessor``; one contiguous
block of the outermost dimension per core is L1 sharded over those cores, read and written in the core's own shard."""

import dataclasses
import json
import pathlib
import re
from dataclasses import dataclass

import dace
import sympy
from dace import dtypes, symbolic
from dace.frontend.operations import detect_reduction_type
from dace.libraries.standard.nodes import Reduce
from dace.libraries.tileops.nodes import MaskedCopyLibraryNode, TileBinop, TileITE
from dace.sdfg import nodes
from dace.sdfg.utils import dfs_topological_sort

from alloy.isa.tensix_harness import compute_include, dataflow_include
from alloy.jsontype import Json
from alloy.tensixgen import movement
from alloy.tensixgen.backend import TILE_NODES, Refused, code, constant, node_code, op_of, rule, use_tensix

__all__ = [
    "ACC_CB",
    "DST_TILES",
    "INTERLEAVED",
    "OUT_CB",
    "SHARDED",
    "Body",
    "Options",
    "Program",
    "Step",
    "body_of",
    "placement_of",
    "program",
    "tile_body",
]

CONTRACT = 2
OUT_CB = 16
#: The running partial tile of a reduction between blocks.
ACC_CB = 24
#: Core counts the sweep offers; 0 is the whole compute grid (what contract v2's host runs).
CORE_COUNTS = (0, 64, 32, 8)
#: The tiles of each array under contract v2; a reduction core with none would leave its writer waiting on CB 16.
TILES = 1024
#: DST tiles one acquire holds in half-sync mode (tt-metal's default) at fp32 accumulation, which the contract needs.
DST_TILES = 4
#: The one load and store subset admitted: one tile of consecutive elements.
LANES = 1024
#: The placements tt-metal 0.63 allocates, the sweep's axis: DRAM interleaved, L1 height sharded.
INTERLEAVED, SHARDED = "interleaved", "sharded"
TILE_BYTES = 4096
#: L1 bytes one core's shards may take; Wormhole's and Blackhole's L1 is about 1.4 MiB, the CBs and kernels need the
#: rest.
L1_SHARD_BYTES = 1 << 20


@dataclass(frozen=True, slots=True)
class Options:
    """The sweep axes: tiles per DST acquire (0: the most that fit), cores (0: the whole grid), and the placement the
    task's arrays get (:data:`INTERLEAVED` or :data:`SHARDED`)."""

    dst_block: int = 0
    cores: int = 0
    placement: str = INTERLEAVED


@dataclass(frozen=True, slots=True)
class Step:
    """One operation of one tile: ``init`` (an init equal to the previous step's is not repeated) and ``call``, whose
    connectors ``tiles`` name DST tiles of the tile."""

    init: str
    call: str
    tiles: tuple[tuple[str, int], ...] = ()


@dataclass(slots=True)
class Body:
    """One tile's program: its steps, the DST tiles it takes, the DST tile it stores or reduces, the reduction's fold
    (None for a map), and the rows' ops, headers and SFPI sources."""

    steps: list[Step]
    width: int
    result: int
    reduce: Step | None
    ops: list[str]
    fold_op: str = ""


class Slots:
    """DST tiles of one tile by linear scan: a DST tile is free once every reader of its tiles has run."""

    def __init__(self, reads: dict[str, int]) -> None:
        self.reads, self.of, self.left, self.width = reads, dict[str, int](), dict[int, int](), 0

    def take(self, data: str) -> int:
        free = [k for k in range(DST_TILES) if self.left.get(k, 0) <= 0]
        if not free:
            raise Refused(f"{data}: more live tiles than the {DST_TILES} DST tiles of one fp32 acquire")
        return self.bind(data, free[0])

    def bind(self, data: str, k: int) -> int:
        self.of[data] = k
        self.left[k] = self.left.get(k, 0) + max(self.reads.get(data, 0), 1)
        self.width = max(self.width, k + 1)
        return k

    def read(self, data: str) -> int:
        k = self.of[data]
        self.left[k] -= 1
        return k

    def dead(self, k: int) -> bool:
        return self.left.get(k, 0) <= 0


def copy(cb: int, version: str) -> Step:
    """``copy_tile`` of the block's tile ``t`` of CB ``cb`` to DST tile ``_o``."""
    init = f"{'copy_init' if version == 'v08' else 'copy_tile_to_dst_init_short'}({cb});"
    return Step(init, f"copy_tile({cb}, t, _o);")


def tile_body(sdfg: dace.SDFG) -> tuple[dace.SDFGState, Reduce | None]:
    """The one state holding the vectorized tile body's copies, or (no tile body) the state of the one ``Reduce`` node,
    and that node."""
    copies = [st for n, st in sdfg.all_nodes_recursive() if isinstance(n, MaskedCopyLibraryNode)]
    if copies:
        states = {id(st): st for st in copies}
        if len(states) != 1:
            raise Refused(f"tile copies in {len(states)} states; the kernel split takes one tile body")
        state = copies[0]
        if not isinstance(state, dace.SDFGState):
            raise Refused("tile copies outside a state")
        return state, None
    found = [
        (st, n) for n, st in sdfg.all_nodes_recursive() if isinstance(n, Reduce) and isinstance(st, dace.SDFGState)
    ]
    if len(found) != 1:
        raise Refused("neither a vectorized tile body nor one Reduce")
    return found[0]


def dense(subset: dace.subsets.Subset) -> bool:
    """Whether ``subset`` is one tile of consecutive elements: unit stride over :data:`LANES` in its last dimension,
    one index in every other."""
    *rest, (_, _, step) = subset.ndrange()
    return step == 1 and subset.num_elements() == LANES and all(b == e for b, e, _ in rest)


def placement_of(name: str, desc: dace.data.Array) -> int:
    """Where array ``name``'s tiles lie: 0 for interleaved DRAM (no placement, or pages of one tile dealt round-robin
    over all nodes, the banks), ``P`` for L1 sharded over ``P`` cores (``(i // B) % P`` or ``i // B`` of the outermost
    index, one block per core). :class:`Refused` for any other placement: tt-metal 0.63 allocates neither."""
    place = desc.placement
    if place is None:  # pyright: ignore[reportUnnecessaryComparison] -- DaCe types it without None
        return 0
    pages, dims = place.pages, place.dims
    if pages is not None:
        if sympy.Mul(*pages.blocks) != LANES or symbolic.equal(pages.count, place.nodes) is not True:
            raise Refused(
                f"{name}: pages of {pages.blocks} elements over {pages.count} of {place.nodes} nodes; interleaved DRAM"
                f" deals pages of one tile ({LANES} elements) over every bank"
            )
        return 0
    first = dims[0]
    if first is None or any(d is not None for d in dims[1:]) or first.stride != 1:
        raise Refused(f"{name}: {place} distributes more than the outermost dimension: no L1 sharding of tt-metal 0.63")
    # a placement does not name its memory: one tile per block over every node is interleaved, so a 1-D shard of one
    # tile per core reads as interleaved too
    wraps = first.count is not None and symbolic.equal(first.count, place.nodes) is True
    if len(dims) == 1 and first.block == LANES and wraps:
        return 0
    cores = place.nodes
    if not (isinstance(cores, sympy.Integer) and 0 < int(cores) and TILES % int(cores) == 0):
        raise Refused(
            f"{name}: L1 sharding over {cores} cores; the host shards {TILES} tiles over a divisor of {TILES}"
        )
    if not (first.count is None or wraps) or symbolic.equal(first.block * cores, desc.shape[0]) is False:
        raise Refused(f"{name}: {place} is not one block of the outermost dimension per core")
    return int(cores)


def float32_tiles(state: dace.SDFGState, sdfg: dace.SDFG) -> None:
    """Refuses a tile of another type; a comparison's bool result stays inside, as 0.0 and 1.0 in a DST tile."""
    for n in state.data_nodes():
        desc = sdfg.arrays[n.data]
        if desc.dtype != dace.float32 and not (desc.dtype == dace.bool_ and desc.transient):
            raise Refused(f"{n.data} is {desc.dtype}: contract v2 moves float32 tiles")


def body_of(state: dace.SDFGState, sdfg: dace.SDFG, inputs: list[str], scalars: dict[str, float],
            version: str) -> Body:  # fmt: skip
    """The steps of one tile of the tile body ``state``; input k of ``inputs`` is read into CB k."""
    float32_tiles(state, sdfg)
    reads: dict[str, int] = {}
    for e in state.edges():
        if isinstance(e.src, nodes.AccessNode) and not e.data.is_empty():
            reads[e.src.data] = reads.get(e.src.data, 0) + 1
    body = BodyBuilder(state, sdfg, inputs, scalars, version, Slots(reads))
    for node in dfs_topological_sort(state):
        if isinstance(node, nodes.AccessNode):
            body.access(node)
        elif isinstance(node, MaskedCopyLibraryNode):
            body.masked_copy(node)
        elif type(node) in TILE_NODES:
            body.tile_node(node)
        else:
            raise Refused(f"{node.label}: {type(node).__name__} in the tile body")
    if body.result < 0:
        raise Refused("no tile leaves the body")
    return Body(body.steps, body.slots.width, body.result, body.fold, body.ops, body.fold_op)


@dataclass
class BodyBuilder:
    """The state :func:`body_of` builds while it walks the tile body, one handler per kind of node."""

    state: dace.SDFGState
    sdfg: dace.SDFG
    inputs: list[str]
    scalars: dict[str, float]
    version: str
    slots: Slots
    #: Each load's and store's subset, with its array's shape.
    spans: set[tuple[str, tuple[object, ...]]] = dataclasses.field(default_factory=set)
    #: A tile copied from CB k, which a later reader may copy again.
    loaded: dict[str, int] = dataclasses.field(default_factory=dict)
    steps: list[Step] = dataclasses.field(default_factory=list)
    ops: list[str] = dataclasses.field(default_factory=list)
    result: int = -1
    fold: Step | None = None
    fold_op: str = ""

    def fill(self, tile: str, value: float) -> None:
        """``tile`` filled with ``value`` in a DST tile of its own."""
        init, call = code("broadcast", ("_c",), value, self.version)
        self.steps.append(Step(init, call, (("_c", self.slots.take(tile)),)))
        self.ops.append("broadcast")

    def one_output(self) -> None:
        if self.result >= 0:
            raise Refused("more than one tile leaves the body: contract v2 writes one output")

    def access(self, node: nodes.AccessNode) -> None:
        for e in self.state.in_edges(node):
            src = e.src
            if not isinstance(src, nodes.AccessNode) or e.data.is_empty():
                continue
            desc = self.sdfg.arrays[src.data]
            if not desc.transient and isinstance(desc, dace.data.Scalar):  # a scalar argument: a filled tile
                if src.data not in self.scalars:
                    raise Refused(f"the scalar {src.data} has no value at generation")
                self.fill(node.data, self.scalars[src.data])
            elif src.data in self.slots.of:  # a copy between tiles: one DST tile
                self.slots.bind(node.data, self.slots.read(src.data))
                if src.data in self.loaded:
                    self.loaded[node.data] = self.loaded[src.data]
            else:
                raise Refused(f"{node.data}: a copy from {src.data}, which no tile holds")

    def masked_copy(self, node: MaskedCopyLibraryNode) -> None:
        state, sdfg = self.state, self.sdfg
        if len(state.in_edges(node)) != 1:
            raise Refused(f"{node.label}: a masked copy")
        inner, outer = state.in_edges(node)[0], state.out_edges(node)[0]
        src, dst = inner.src, outer.dst
        if not (isinstance(src, nodes.AccessNode) and isinstance(dst, nodes.AccessNode)):
            raise Refused(f"{node.label}: a copy between non-data nodes")
        load = not sdfg.arrays[src.data].transient
        span = inner.data.get_src_subset(inner, state) if load else outer.data.get_dst_subset(outer, state)
        if span is None or not dense(span):
            raise Refused(f"{node.label}: {span} is not one tile of consecutive elements")
        self.spans.add((str(span), tuple(sdfg.arrays[src.data if load else dst.data].shape)))
        if len(self.spans) > 1:  # the host reads and writes tile k of every array at the same index
            raise Refused(f"{node.label}: the loads and stores take different tiles: {sorted(self.spans)}")
        if load:  # a load: the reader's CB copied to DST
            if src.data not in self.inputs:
                raise Refused(f"{node.label}: loads {src.data}, not an input of the task")
            cb = self.inputs.index(src.data)
            self.loaded[dst.data] = cb
            self.steps.append(dataclasses.replace(copy(cb, self.version), tiles=(("_o", self.slots.take(dst.data)),)))
        else:  # the store: packed to CB 16 after the block; its DST tile stays taken
            self.one_output()
            self.result = self.slots.of[src.data]

    def tile_node(self, node: nodes.LibraryNode) -> None:
        state, slots = self.state, self.slots
        init, call = node_code(node, self.version)
        self.ops.append(op_of(node))
        ins = {e.dst_conn: e.src.data for e in state.in_edges(node) if isinstance(e.src, nodes.AccessNode)}
        outs = {e.src_conn: e.dst.data for e in state.out_edges(node) if isinstance(e.dst, nodes.AccessNode)}
        if "_src" in ins:  # a reduction: its source's DST tile stays taken for the fold
            self.one_output()
            self.result, self.fold, self.fold_op = slots.of[ins["_src"]], Step(init, call), op_of(node)
        elif isinstance(node, TileBinop | TileITE):  # operands in DST tiles; the output may take a dying one's
            self.operands(node, ins, init, call, outs["_c" if isinstance(node, TileBinop) else "_o"])
        elif "_a" in ins:
            self.unary(node, ins["_a"], init, call, outs["_c"])
        else:  # a filled tile: a constant TileUnop (_c) or a constant TileGather (_dst)
            self.steps.append(Step(init, call, tuple((conn, slots.take(data)) for conn, data in outs.items())))

    def operands(self, node: TileBinop | TileITE, ins: dict[str, str], init: str, call: str, out: str) -> None:
        """A binary op (``_a``, ``_b`` into ``_c``) or a select (``_mask``, ``_t``, ``_e`` into ``_o``); a constant
        operand is a filled tile."""
        if isinstance(node, TileBinop):
            given: tuple[tuple[str, str, str | None], ...] = (
                ("_a", node.kind_a, node.expr_a),
                ("_b", node.kind_b, node.expr_b),
            )
        else:
            given = (("_mask", node.kind_mask, node.expr_mask), ("_t", node.kind_t, node.expr_t),
                     ("_e", node.kind_e, node.expr_e))  # fmt: skip
        for conn, kind, expr in given:
            if kind == "Symbol":
                ins[conn] = f"{node.label}{conn}"
                self.fill(ins[conn], constant(node, expr))
            elif conn not in ins:
                raise Refused(f"{node.label}: {conn} is a {kind}, not a tile or a constant")
        read = [(conn, self.slots.read(ins[conn])) for conn, _, _ in given]
        k = next((x for _, x in read if self.slots.dead(x)), None)
        k = self.slots.take(out) if k is None else self.slots.bind(out, k)
        self.steps.append(Step(init, call, (*read, ("_o" if isinstance(node, TileITE) else "_c", k))))

    def unary(self, node: nodes.LibraryNode, operand: str, init: str, call: str, out: str) -> None:
        """A unary op works in place on ``_c``: on its operand's DST tile when that dies here, else on a copy."""
        slots = self.slots
        a = slots.read(operand)
        if slots.dead(a):
            k = slots.bind(out, a)
        elif operand in self.loaded:  # the operand is read again later: copy it from its CB once more
            k = slots.take(out)
            self.steps.append(dataclasses.replace(copy(self.loaded[operand], self.version), tiles=(("_o", k),)))
        else:
            raise Refused(f"{node.label}: its operand is read again, and no checked row copies DST to DST")
        self.steps.append(Step(init, call, (("_c", k),)))


def reduce_body(node: Reduce, state: dace.SDFGState, inputs: list[str], version: str) -> Body:
    """A ``Reduce`` that sums a whole input: one copy per tile, folded like a vectorized reduction."""
    # shortcut: the vectorizer leaves a whole-array Reduce node (tsvc_2_s311) unvectorized; the split takes it as a
    # load and a TileReduce. Upgrade when the vectorizer lifts Reduce nodes into tile bodies.
    (edge,) = state.in_edges(node)
    desc = state.sdfg.arrays[edge.data.data]
    rank = len(desc.shape)
    if detect_reduction_type(node.wcr) != dtypes.ReductionType.Sum or len(inputs) != 1:  # any spelling of a + b
        raise Refused(f"{node.label}: only a sum of one input reduces on Tensix")
    if node.axes is not None and sorted(node.axes) != list(range(rank)):
        raise Refused(f"{node.label}: reduces axes {node.axes} of {rank}, not the whole input")
    if desc.dtype != dace.float32:
        raise Refused(f"{edge.data.data}: contract v2 moves float32 tiles")
    init, call = code("add", ("_dst", "_src", "_dst"), version=version)
    load = dataclasses.replace(copy(0, version), tiles=(("_o", 0),))
    return Body([load], 1, 0, Step(init, call), ["add"], "add")


def slot(width: int, k: int) -> str:
    """DST tile ``k`` of the block's tile ``t`` when a tile takes ``width`` DST tiles."""
    if width == 1:
        return "t" if k == 0 else f"t + {k}"
    return f"t * {width}" if k == 0 else f"t * {width} + {k}"


def placed(step: Step, at: dict[str, str]) -> str:
    """``step``'s call with each DST connector replaced by its C expression in ``at``."""
    text = step.call
    for conn, value in at.items():
        text = re.sub(rf"\b{conn}\b", value, text)
    return text


def compute(name: str, title: str, body: Body, block: int, inputs: int, version: str) -> str:
    new = version == "v08"
    width, indent = body.width, "        "
    lines: list[str] = []
    last = ""
    for step in body.steps:
        if step.init != last:
            lines.append(indent + step.init)
            last = step.init
        lines.append(
            f"{indent}for (uint32_t t = 0; t < n; ++t) {placed(step, {c: slot(width, k) for c, k in step.tiles})}"
        )
    loop = [
        "    uint32_t num_tiles = get_arg_val<uint32_t>(0);",
        f"    {'compute_kernel_hw_startup' if new else 'init_sfpu'}(0, {OUT_CB});",
        f"    for (uint32_t i = 0; i < num_tiles; i += {block}) {{",
        f"        uint32_t n = num_tiles - i < {block} ? num_tiles - i : {block};",
        *(f"        cb_wait_front({k}, n);" for k in range(inputs)),
        "        tile_regs_acquire();",
        *lines,
    ]
    pops = [f"        cb_pop_front({k}, n);" for k in range(inputs)]
    s = body.result
    if body.reduce is not None:
        fold, spare = body.reduce, "0" if s else "1"  # after the fold only DST tile s holds data
        again = [] if fold.init == last else [indent + fold.init]
        loop += [
            *again,
            f"{indent}for (uint32_t t = 1; t < n; ++t) {placed(fold, {'_dst': str(s), '_src': slot(width, s)})}",
            f"{indent}if (i > 0) {{  // the partial tile of the earlier blocks",
            f"{indent}    cb_wait_front({ACC_CB}, 1);",
            f"{indent}    {copy(ACC_CB, version).init}",
            f"{indent}    copy_tile({ACC_CB}, 0, {spare});",
            f"{indent}    {fold.init}",
            f"{indent}    {placed(fold, {'_dst': str(s), '_src': spare})}",
            f"{indent}    cb_pop_front({ACC_CB}, 1);",
            f"{indent}}}",
            "        tile_regs_commit();",
            *pops,
            f"        uint32_t into = i + n < num_tiles ? {ACC_CB} : {OUT_CB};",
            "        cb_reserve_back(into, 1);",
            "        tile_regs_wait();",
            f"        pack_tile({s}, into);",
            "        tile_regs_release();",
            "        cb_push_back(into, 1);",
        ]
    else:
        loop += [
            "        tile_regs_commit();",
            *pops,
            f"        cb_reserve_back({OUT_CB}, n);",
            "        tile_regs_wait();",
            f"        for (uint32_t t = 0; t < n; ++t) pack_tile({slot(width, s)}, {OUT_CB});",
            "        tile_regs_release();",
            f"        cb_push_back({OUT_CB}, n);",
        ]
    loop.append("    }")
    rules = {op: rule(op, version) for op in dict.fromkeys(body.ops)}
    headers = ["common.h", "tile_move_copy.h", "eltwise_unary/eltwise_unary.h", *(r.header for r in rules.values())]
    sources = [r.code.strip("\n") for r in rules.values() if r.code]
    if sources:  # an SFPI rung needs compute_kernel_api.h: sfpi, SfpuType, VectorMode and the llk SFPU helpers
        headers.append("compute_kernel_api.h")
    head = [
        f"// {name}: {title}",
        (
            f"// Generated by alloy.tensixgen from DaCe's tile nodes (contract v{CONTRACT}, tt-metal {version}): {block}"
            f" tile(s) per DST acquire, {width} DST tile(s) per tile, fp32 accumulation."
        ),
        *(f"// {op}: {r.source}" for op, r in rules.items()),
        "#include <stdint.h>",
        *(f'#include "{compute_include(h, new)}"' for h in dict.fromkeys(headers)),
        *sources,
        "",
    ]
    if new:
        return "\n".join([*head, "void kernel_main() {", *loop, "}", ""])
    return "\n".join([*head, "namespace NAMESPACE {", "void MAIN {", *loop, "}", "}  // namespace NAMESPACE", ""])


def placements(task: Json, sdfg: dace.SDFG, inputs: list[str], output: str, reduce: bool,
               options: Options) -> tuple[dict[str, dace.data.Array], dict[str, int], int]:  # fmt: skip
    """The task's arrays, the cores each is sharded over (0: interleaved DRAM), and the one placement they share:
    a reduction's output stays in DRAM, and the shards of one core fit its L1."""
    arrays: dict[str, dace.data.Array] = {}
    for name in dict.fromkeys([*inputs, output]):
        desc = sdfg.arrays[name]
        if not isinstance(desc, dace.data.Array):
            raise Refused(f"{task['name']}: {name} is a {type(desc).__name__}; contract v2 moves arrays")
        arrays[name] = desc
    shards = {name: placement_of(name, desc) for name, desc in arrays.items()}
    if reduce and shards[output]:
        raise Refused(f"{task['name']}: a reduction writes one partial tile per core to DRAM, not to {output}'s shards")
    # each core reads and writes the same tiles of every array: sharded and interleaved arrays would need the host's
    # core order to equal the shard order
    kinds = {shards[name] for name in (inputs if reduce else shards)}
    if len(kinds) > 1:
        raise Refused(
            f"{task['name']}: arrays placed on {sorted(kinds)} cores (0: interleaved DRAM); one placement only"
        )
    (sharded,) = kinds
    if sharded and options.cores not in (0, sharded):
        raise Refused(f"{task['name']}: arrays sharded over {sharded} cores, the program runs on {options.cores}")
    held = sum(bool(cores) for cores in shards.values()) * (TILES // sharded if sharded else 0) * TILE_BYTES
    if held > L1_SHARD_BYTES:
        raise Refused(
            f"{task['name']}: {held} bytes of shards per core exceed the {L1_SHARD_BYTES} of L1 they may take"
        )
    return arrays, shards, sharded


def compute_config(count: int, block: int, reduce: bool) -> dict[str, object]:
    """The compute kernel's config for ``count`` inputs and ``block`` tiles per DST acquire: fp32 in DST, and the CBs
    sized for two blocks."""
    sized = [*range(count), OUT_CB] if block > 1 else []  # the host's CBs hold 2 tiles: room for 2 blocks
    extra = [{"index": k, "tiles": 2 * block, "format": "float32"} for k in sized]
    extra += [{"index": ACC_CB, "tiles": 2, "format": "float32"}] if reduce else []
    return {
        "fp32_dest_acc_en": True,
        "math_approx_mode": False,
        "math_fidelity": "HiFi4",
        "unpack_to_dest_fp32": [*range(count), *([ACC_CB] if reduce else [])],
        "extra_cbs": extra,
    }


def host_descriptor(task: Json, version: str, body: Body, options: Options, arrays: dict[str, dace.data.Array],
                    shards: dict[str, int], inputs: list[str], block: int, reduce: bool) -> dict[str, object]:  # fmt: skip
    """``program.json``: what the host needs to run the program (contract, options and sweep axes, each array's
    placement, the CBs, and the kernels' arguments)."""
    count = len(inputs)
    return {
        "contract": CONTRACT,
        "tt_metal": version,
        **{k: task[k] for k in ("name", "kind", "inputs", "output", "program")},
        "reduce": body.fold_op,
        "options": dataclasses.asdict(options),
        "axes": {
            "dst_block": list(range(1, DST_TILES // body.width + 1)),
            "cores": list(CORE_COUNTS),
            "placement": [INTERLEAVED, SHARDED],
        },
        "placement": {
            name: {
                "kind": SHARDED if cores else INTERLEAVED,
                "cores": cores,
                "tiles": TILES // cores if cores else 0,
                "map": None if arrays[name].placement is None else str(arrays[name].placement),  # pyright: ignore[reportUnnecessaryComparison] -- DaCe types it without None
            }
            for name, cores in shards.items()
        },  # fmt: skip
        "circular_buffers": {str(k): [2 * block, "float32"] for k in [*range(count), OUT_CB]}
        | ({str(ACC_CB): [2, "float32"]} if reduce else {}),
        "reader_args": ["num_tiles", "start_tile", *(f"{name}_addr" for name in inputs)],
        "writer_args": ["1", "core_index", "out_addr"] if reduce else ["num_tiles", "start_tile", "out_addr"],
        "compute_args": ["num_tiles"],
        "rows": {op: rule(op, version).source for op in dict.fromkeys(body.ops)},
    }


def reader(moves: movement.Movement, block: int, version: str, sharded: bool = False) -> str:
    """Spells the body's loads (:mod:`alloy.tensixgen.movement`): this core's tiles ``start .. start + n - 1`` of every
    input, ``block`` tiles per input per wait; sharded inputs, the core's ``n`` tiles from its own L1 shard."""
    loads = moves.loads
    what = "n tiles from its L1 shard" if sharded else "tiles start .. start + n - 1"
    lines = [
        f"// reader: this core's {what} of {len(loads)} input(s), input k into CB k, {block} per barrier",
        "#include <stdint.h>",
        f'#include "{dataflow_include(version == "v08")}"',
        "",
        "void kernel_main() {",
        "    uint32_t num_tiles = get_arg_val<uint32_t>(0);",
    ]
    if not sharded:
        lines.append("    uint32_t start = get_arg_val<uint32_t>(1);")
    for load in loads:
        k = load.cb
        offset = "0" if k == 0 else f"args{k - 1}.next_compile_time_args_offset()"
        if sharded:  # a shard lies at the same L1 address on every core
            lines += [
                f"    const uint32_t bytes{k} = get_tile_size({k});",
                f"    const uint64_t s{k} = get_noc_addr(get_arg_val<uint32_t>({k + 2}));",
            ]
            continue
        lines += [
            f"    constexpr auto args{k} = TensorAccessorArgs<{offset}>();",
            f"    const uint32_t bytes{k} = get_tile_size({k});",
            f"    const auto s{k} = TensorAccessor(args{k}, get_arg_val<uint32_t>({k + 2}), bytes{k});",
        ]
    lines += [
        f"    for (uint32_t i = 0; i < num_tiles; i += {block}) {{",
        f"        uint32_t n = num_tiles - i < {block} ? num_tiles - i : {block};",
        *(f"        cb_reserve_back({load.cb}, n);" for load in loads),
        *(f"        uint32_t w{load.cb} = get_write_ptr({load.cb});" for load in loads),
        "        for (uint32_t t = 0; t < n; ++t) {",
        *("            " + movement.read_line(load, sharded) for load in loads),
        "        }",
        f"        {moves.read_wait.call()}",
        *(f"        {movement.push_call(load)}" for load in loads),
        "    }",
        "}",
        "",
    ]
    return "\n".join(lines)


def writer(moves: movement.Movement, block: int, version: str, sharded: bool = False) -> str:
    """Writes this core's output tiles from CB 16 at ``start``: a map's ``n`` tiles, a reduction's one tile; a sharded
    map's ``n`` tiles into the core's own L1 shard."""
    if sharded:
        return "\n".join([
            f"// writer: n tiles from CB {OUT_CB} to this core's L1 shard of the output ({block} per barrier)",
            "#include <stdint.h>",
            f'#include "{dataflow_include(version == "v08")}"',
            "",
            "void kernel_main() {",
            "    uint32_t num_tiles = get_arg_val<uint32_t>(0);",
            f"    const uint32_t bytes = get_tile_size({OUT_CB});",
            "    const uint64_t s = get_noc_addr(get_arg_val<uint32_t>(2));",
            f"    for (uint32_t i = 0; i < num_tiles; i += {block}) {{",
            f"        uint32_t n = num_tiles - i < {block} ? num_tiles - i : {block};",
            f"        cb_wait_front({OUT_CB}, n);",
            f"        uint32_t r = get_read_ptr({OUT_CB});",
            "        for (uint32_t t = 0; t < n; ++t) {",
            f"            {movement.write_line(True)}",
            "        }",
            f"        {moves.write_wait.call()}",
            f"        cb_pop_front({OUT_CB}, n);",
            "    }",
            "}",
            "",
        ])  # fmt: skip
    return "\n".join([
        (f"// writer: n tiles from CB {OUT_CB} to output tiles start .. start + n - 1 ({block} per barrier); a reduction"
        " passes n = 1 and start = the core's index"),
        "#include <stdint.h>",
        f'#include "{dataflow_include(version == "v08")}"',
        "",
        "void kernel_main() {",
        "    uint32_t num_tiles = get_arg_val<uint32_t>(0);",
        "    uint32_t start = get_arg_val<uint32_t>(1);",
        "    constexpr auto args = TensorAccessorArgs<0>();",
        f"    const uint32_t bytes = get_tile_size({OUT_CB});",
        "    const auto s = TensorAccessor(args, get_arg_val<uint32_t>(2), bytes);",
        f"    for (uint32_t i = 0; i < num_tiles; i += {block}) {{",
        f"        uint32_t n = num_tiles - i < {block} ? num_tiles - i : {block};",
        f"        cb_wait_front({OUT_CB}, n);",
        f"        uint32_t r = get_read_ptr({OUT_CB});",
        "        for (uint32_t t = 0; t < n; ++t) {",
        f"            {movement.write_line(False)}",
        "        }",
        f"        {moves.write_wait.call()}",
        f"        cb_pop_front({OUT_CB}, n);",
        "    }",
        "}",
        "",
    ])  # fmt: skip


@dataclass(frozen=True, slots=True)
class Program:
    """A generated program in the layout of ``agents/reference/<task>/``, plus its host descriptor."""

    name: str
    reader: str
    compute: str
    writer: str
    config: dict[str, object]
    descriptor: dict[str, object]

    def write(self, folder: pathlib.Path) -> pathlib.Path:
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "reader.cpp").write_text(self.reader)
        (folder / "compute.cpp").write_text(self.compute)
        (folder / "writer.cpp").write_text(self.writer)
        (folder / "config.json").write_text(json.dumps(self.config) + "\n")
        (folder / "program.json").write_text(json.dumps(self.descriptor, indent=1) + "\n")
        return folder


def program(task: Json, sdfg: dace.SDFG, scalars: dict[str, float], options: Options = Options(),
            version: str = "v06") -> Program:  # fmt: skip
    """The tile program of eval task ``task`` (``agents/tasks.json``'s form) from its vectorized SDFG, for tt-metal
    ``version`` (``v06``: the card's 0.63, ``v08``: ttsim's image)."""
    # shortcut: the vectorizer's 1024 lanes are 1024 consecutive elements, the host's tile is a 32x32 TILE-layout
    # tile; equal for elementwise ops and whole-array reductions, which is all contract v2 admits. Upgrade when a
    # lane-dependent op (scan, gather, a 2-D stencil) reaches Tensix.
    if version not in ("v06", "v08"):
        raise ValueError(f"version {version}: v06 or v08")
    inputs = [str(name) for name, *_ in task["inputs"]]
    use_tensix(sdfg)
    if options.cores > TILES:
        raise Refused(f"{task['name']}: {options.cores} cores for {TILES} tiles leave a core without a tile")
    state, node = tile_body(sdfg)
    if node is None:
        body = body_of(state, state.sdfg, inputs, scalars, version)
    else:
        body = reduce_body(node, state, inputs, version)
    reduce = task["kind"] == "reduce"
    if reduce != (body.reduce is not None):
        raise Refused(
            f"{task['name']}: the task is a {task['kind']}, its tile body {'is not ' if reduce else ''}a reduction"
        )
    room = DST_TILES // body.width
    block = options.dst_block or room
    if not 1 <= block <= room:
        raise Refused(f"{task['name']}: {block} tile(s) of {body.width} DST tile(s) each exceed one DST acquire")
    output = str(task["output"])
    arrays, shards, sharded = placements(task, sdfg, inputs, output, reduce, options)
    options = dataclasses.replace(options, dst_block=block, cores=sharded or options.cores,
                                  placement=SHARDED if sharded else INTERLEAVED)  # fmt: skip
    count = len(inputs)
    config = compute_config(count, block, reduce)
    descriptor = host_descriptor(task, version, body, options, arrays, shards, inputs, block, reduce)
    title = " | ".join(task["program"])
    moves = movement.insert(state, inputs, output, reduce)
    return Program(
        str(task["name"]),
        reader(moves, block, version, bool(sharded)),
        compute(str(task["name"]), title, body, block, count, version),
        writer(moves, block, version, bool(sharded) and not reduce),
        config,
        descriptor,
    )
