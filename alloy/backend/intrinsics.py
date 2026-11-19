# Copyright 2026 ETH Zurich and the Alloy authors.
"""Intrinsic tasklets (owner, 11-19): a scope's innermost loop rewritten so that its body is one DaCe tasklet spelled
from the ISA lookup's checked rows (``alloy/isa/intrinsics.toml``).

:func:`admit` reads each innermost loop's body as one expression per write: elementwise arithmetic on contiguous
loads into contiguous stores, or one sum, min or max into a scalar. :func:`rewrite` splits an admitted loop in two: a
main loop over whole blocks, whose body is the tasklet, then the original loop over the remainder. A reduction keeps
its partial results in a block-wide accumulator between the two. :func:`offer` names the candidates a scope gets on a
host (one per ISA the host runs and FP level the tasklet needs), or why it gets none; every candidate is then built,
verified and timed like any other."""

import ast
import copy
import dataclasses
import functools
import re
from collections.abc import Iterable, Mapping
from typing import Any, Literal

import dace
import sympy
from dace import dtypes, symbolic
from dace.properties import CodeBlock
from dace.sdfg import nodes
from dace.sdfg.graph import MultiConnectorEdge
from dace.sdfg.state import ControlFlowBlock, LoopRegion
from dace.transformation.passes.analysis import loop_analysis

from alloy.configuration_matrix import Matrix
from alloy.isa import simt
from alloy.isa.ask import SVE_TYPES, cpu_setup
from alloy.isa.hints import CALL_NAMES
from alloy.isa.ops import called_name
from alloy.isa.table import Entry, Table, load
from alloy.isa.validate import SVE_MAX_BYTES, assigned, frame, validate

__all__ = ["Admission", "Leaf", "Offer", "Op", "Plan", "Refused", "Write", "admit", "offer", "rendered", "rewrite"]

#: A sympy expression: ``sympify`` types it ``Basic``, which declares no arithmetic.
Symbolic = Any
#: The one FP level that forbids contraction: a product feeding a sum stays two rows there, the fma row elsewhere.
UNFUSED_LEVEL = "strict"
#: The FP level a reduction's tasklet builds at: it sums in another order than the loop.
REASSOC_LEVEL = "reassoc"
#: The FP level an fma tasklet of a loop that does not reduce builds at.
CONTRACT_LEVEL = "contract"
#: Element types the rows spell, by DaCe type.
DTYPES = {dace.float64: "f64", dace.float32: "f32"}
#: Python operators of a tasklet -> lookup ops.
BINARY = {ast.Add: "add", ast.Sub: "sub", ast.Mult: "mul", ast.Div: "div"}
#: Calls a tasklet may make, and the ops they are: the lookup's own names (hints.CALL_NAMES) with one or two operands.
CALLS = {name: op for name, op in CALL_NAMES.items() if op in ("abs", "sqrt", "min", "max")}
#: Casts the frontend wraps a literal in.
CASTS = frozenset({"dace.float64", "dace.float32", "float"})
#: An update ``s = s op e`` -> the reduction row it folds a block with.
RECURRENCES = {"add": "reduce_add", "min": "reduce_min", "max": "reduce_max"}
#: The lane-wise row that combines a block into a reduction's accumulator.
COMBINE = {"reduce_add": "add", "reduce_min": "min", "reduce_max": "max"}
#: Product operands in an fma row's semantics: ``a[j]*b[j]``.
PRODUCT = re.compile(r"(\w+)\[j\]\s*\*\s*(\w+)\[j\]")


class Refused(ValueError):
    """A loop the rows cannot spell, and why."""


@dataclasses.dataclass(frozen=True, slots=True)
class Leaf:
    """A value the body reads: ``load`` one element per iteration of ``data`` at ``index`` (the loop variable in the
    last, contiguous dimension), ``scalar`` an element the loop does not move (``data`` a container, ``index`` its
    element) or a symbol (``index`` empty), ``constant`` a literal."""

    kind: Literal["load", "scalar", "constant"]
    data: str
    index: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True, slots=True)
class Op:
    """A lookup op on its operands, in the order of the tasklet's expression."""

    op: str
    args: tuple["Leaf | Op", ...]


Expr = Leaf | Op


@dataclasses.dataclass(frozen=True, slots=True)
class Write:
    """What one iteration writes: ``value`` into ``data`` at ``index``; ``reduce`` names the reduction row when the
    write folds ``value`` into one element (``index`` then the loop does not move), empty for a store."""

    data: str
    index: tuple[str, ...]
    value: Expr
    reduce: str = ""


@dataclasses.dataclass(frozen=True, slots=True, eq=False)
class Plan:
    """An admitted innermost loop: the region or map entry, the state a map is in, its variable, first and last
    (inclusive) value, its writes and their element type."""

    label: str
    loop: LoopRegion | nodes.MapEntry
    state: dace.SDFGState | None
    variable: str
    begin: Symbolic
    end: Symbolic
    writes: tuple[Write, ...]
    dtype: str

    @property
    def reduces(self) -> bool:
        return any(w.reduce for w in self.writes)

    def rows(self, fused: bool) -> frozenset[str]:
        """Every lookup op the tasklets of this loop call."""
        found = {"load", "store"}
        for w in self.writes:
            value = fused_value(w.value) if fused else w.value
            found |= expression_ops(value)
            if w.reduce:
                found |= {w.reduce, "zero" if w.reduce == "reduce_add" else "broadcast"}
                found.add("fma" if fused and isinstance(w.value, Op) and w.value.op == "mul" else COMBINE[w.reduce])
        return frozenset(found)


@dataclasses.dataclass(frozen=True, slots=True)
class Admission:
    """A scope's admitted loops, and every other innermost loop with why it was not admitted."""

    plans: tuple[Plan, ...]
    refused: tuple[str, ...]


def expression_ops(e: Expr) -> set[str]:
    if isinstance(e, Leaf):
        return {"load"} if e.kind == "load" else {"broadcast"}
    return {e.op}.union(*(expression_ops(a) for a in e.args))


def fused_value(e: Expr) -> Expr:
    """``e`` with every product feeding a sum as the fma op: ``x*y + z`` and ``z + x*y`` as ``fma(x, y, z)``."""
    if isinstance(e, Leaf):
        return e
    args = tuple(fused_value(a) for a in e.args)
    if e.op == "add":
        for product, other in ((args[0], args[1]), (args[1], args[0])):
            if isinstance(product, Op) and product.op == "mul":
                return Op("fma", (*product.args, other))
    return Op(e.op, args)


def element_type(sdfg: dace.SDFG, data: str) -> str:
    desc = sdfg.arrays[data]
    if desc.dtype not in DTYPES:
        raise Refused(f"{data} holds {desc.dtype}: the rows spell f64 and f32")
    return DTYPES[desc.dtype]


def indices(subset: dace.subsets.Subset | None, data: str) -> tuple[Symbolic, ...]:
    """The element of a one-element subset, per dimension."""
    if not isinstance(subset, dace.subsets.Range) or subset.num_elements() != 1:
        raise Refused(f"{data} is accessed as {subset}, not one element per iteration")
    return tuple(sympy.sympify(begin) for begin, _, _ in subset.ranges)


def names(e: Symbolic) -> set[str]:
    """The symbols of ``e`` by name: DaCe's symbols differ from plain sympy ones of the same name."""
    return {str(s) for s in e.free_symbols}


def leaf(sdfg: dace.SDFG, data: str, subset: dace.subsets.Subset | None, variable: str) -> Leaf:
    """A read of ``data`` at ``subset``: a load when the loop variable is the last index plus a constant offset of a
    unit-stride dimension, a scalar when no index moves with it."""
    element = indices(subset, data)
    moving = [d for d, index in enumerate(element) if variable in names(index)]
    index = tuple(str(e) for e in element)
    if not moving:
        return Leaf("scalar", data, index)
    desc = sdfg.arrays[data]
    if moving != [len(element) - 1] or symbolic.issymbolic(desc.strides[-1]) or int(desc.strides[-1]) != 1:
        raise Refused(f"{data}[{', '.join(index)}] is not contiguous in {variable}")
    (i,) = (s for s in element[-1].free_symbols if str(s) == variable)
    if sympy.diff(element[-1], i) != 1 or variable in names(sympy.diff(element[-1], i)):
        raise Refused(f"{data}[{', '.join(index)}] does not step by one element with {variable}")
    return Leaf("load", data, index)


@dataclasses.dataclass(slots=True)
class Body:
    """The dataflow of a loop body: its SDFG and state, the loop variable, and the map entry it hangs off (or none)."""

    sdfg: dace.SDFG
    state: dace.SDFGState
    variable: str
    entry: nodes.MapEntry | None = None

    def value(self, edge: MultiConnectorEdge[dace.Memlet]) -> Expr:
        """The value ``edge`` carries."""
        src = edge.src
        if self.entry is not None and src is self.entry:
            return leaf(self.sdfg, str(edge.data.data), edge.data.subset, self.variable)
        if isinstance(src, nodes.Tasklet):
            return self.tasklet_value(src, edge.src_conn)
        if isinstance(src, nodes.AccessNode):
            if not self.sdfg.arrays[src.data].transient:
                return leaf(self.sdfg, src.data, edge.data.get_src_subset(edge, self.state), self.variable)
            writers = [e for e in self.state.in_edges(src) if not e.data.is_empty()]
            if len(writers) != 1:
                raise Refused(f"the transient {src.data} has {len(writers)} writers in the body")
            return self.value(writers[0])
        raise Refused(f"{type(src).__name__} {src} feeds the body")

    def tasklet_value(self, tasklet: nodes.Tasklet, connector: str) -> Expr:
        if tasklet.code.language != dace.Language.Python:
            raise Refused(f"tasklet {tasklet.label} is {tasklet.code.language.name}, not Python")
        body = ast.parse(tasklet.code.as_string).body
        if len(body) != 1 or not isinstance(body[0], ast.Assign) or len(body[0].targets) != 1:
            raise Refused(f"tasklet {tasklet.label} is not one assignment")
        target = body[0].targets[0]
        if not isinstance(target, ast.Name) or target.id != connector:
            raise Refused(f"tasklet {tasklet.label} assigns no {connector}")
        inputs = {e.dst_conn: e for e in self.state.in_edges(tasklet) if e.dst_conn}
        return self.translated(body[0].value, inputs, tasklet.label)

    def translated(self, node: ast.expr, inputs: dict[str, MultiConnectorEdge[dace.Memlet]], label: str) -> Expr:
        if isinstance(node, ast.Name):
            if node.id in inputs:
                return self.value(inputs[node.id])
            params = self.entry.map.params if self.entry is not None else [self.variable]
            if node.id in params:
                raise Refused(f"tasklet {label} uses the loop index {node.id} as a value")
            return Leaf("scalar", node.id)
        if isinstance(node, ast.Constant) and isinstance(node.value, int | float) and not isinstance(node.value, bool):
            return Leaf("constant", repr(node.value))
        if isinstance(node, ast.BinOp) and type(node.op) in BINARY:
            args = (self.translated(node.left, inputs, label), self.translated(node.right, inputs, label))
            return Op(BINARY[type(node.op)], args)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return Op("neg", (self.translated(node.operand, inputs, label),))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.UAdd):
            return self.translated(node.operand, inputs, label)
        if isinstance(node, ast.Call) and ast.unparse(node.func) in CASTS and len(node.args) == 1:
            return self.translated(node.args[0], inputs, label)  # the frontend's typed literal: dace.float32(2.0)
        if isinstance(node, ast.Call) and called_name(node) in CALLS and not node.keywords:
            op = CALLS[called_name(node)]
            if len(node.args) != (2 if op in ("min", "max") else 1):
                raise Refused(f"tasklet {label} calls {called_name(node)} with {len(node.args)} operands")
            return Op(op, tuple(self.translated(a, inputs, label) for a in node.args))
        raise Refused(f"tasklet {label} computes {ast.unparse(node)}, which no admitted row spells")


def leaves(e: Expr) -> list[Leaf]:
    return [e] if isinstance(e, Leaf) else [x for a in e.args for x in leaves(a)]


def recurrence(write: Write, element: Leaf) -> Write:
    """``write`` as a reduction when its value folds the element it writes (``s = s + e``, ``max(s, e)``)."""
    value = write.value
    if not isinstance(value, Op) or value.op not in RECURRENCES:
        raise Refused(f"{write.data}[{', '.join(write.index)}] is written every iteration, not as a sum, min or max")
    rest = [a for a in value.args if a != element]
    if len(rest) != 1 or element in leaves(rest[0]):
        raise Refused(f"{write.data} is updated as {value.op} of more than its own element")
    return Write(write.data, write.index, rest[0], RECURRENCES[value.op])


def checked_writes(sdfg: dace.SDFG, raw: list[Write], variable: str) -> tuple[tuple[Write, ...], str]:
    """The writes of a body as stores, and as reductions where an element the loop does not move is updated; their
    one element type. Refused on a loop-carried dependence, a write the rows cannot spell, or mixed types."""
    out: list[Write] = []
    for write in raw:
        moves = any(variable in names(sympy.sympify(index)) for index in write.index)
        out.append(write if moves else recurrence(write, Leaf("scalar", write.data, write.index)))
    targets = [w.data for w in out]
    if len(set(targets)) != len(targets):
        raise Refused(f"the body writes {', '.join(sorted({n for n in targets if targets.count(n) > 1}))} twice")
    if any(w.reduce for w in out) and len(out) > 1:
        raise Refused("a reduction beside other writes")
    written = {w.data: w for w in out}
    for w in out:
        for read in leaves(w.value):
            owner = written.get(read.data) if read.kind != "constant" and read.index else None
            if owner is not None and (owner.reduce or read.kind != "load" or read.index != owner.index):
                raise Refused(
                    f"{read.data} is read at [{', '.join(read.index)}] and written at [{', '.join(owner.index)}]: "
                    "an iteration reads what another writes"
                )
    types = {element_type(sdfg, w.data) for w in out} | {
        element_type(sdfg, r.data) for w in out for r in leaves(w.value) if r.kind != "constant" and r.index
    }
    if len(types) != 1:
        raise Refused(f"the body mixes element types {', '.join(sorted(types))}")
    return tuple(out), types.pop()


def plain_dataflow(state: dace.SDFGState, members: Iterable[nodes.Node], where: str) -> None:
    for node in members:
        if not isinstance(node, nodes.AccessNode | nodes.Tasklet):
            raise Refused(f"{where} holds {type(node).__name__} {node}")


def loop_plan(sdfg: dace.SDFG, loop: LoopRegion) -> Plan:
    blocks = list(loop.nodes())
    if len(blocks) != 1 or not isinstance(blocks[0], dace.SDFGState):
        raise Refused("the body is more than one state")
    state = blocks[0]
    plain_dataflow(state, state.nodes(), "the body")
    begin, end, stride = (f(loop) for f in (loop_analysis.get_init_assignment, loop_analysis.get_loop_end,
                                            loop_analysis.get_loop_stride))  # fmt: skip
    if begin is None or end is None or stride != 1 or loop.inverted:
        raise Refused(f"not a loop from a known start to a known end by one ({loop.loop_condition.as_string})")
    body = Body(sdfg, state, loop.loop_variable)
    raw: list[Write] = []
    for n in state.data_nodes():
        if sdfg.arrays[n.data].transient:
            continue
        for e in state.in_edges(n):
            if e.data.is_empty():
                continue
            if e.data.wcr is not None:  # shortcut: the frontend writes s = s + e; fold a WCR when a pipeline emits one
                raise Refused(f"{n.data} is written through a write-conflict resolution")
            index = tuple(str(i) for i in indices(e.data.get_dst_subset(e, state), n.data))
            raw.append(Write(n.data, index, body.value(e)))
    if not raw:
        raise Refused("the body writes no container of the program")
    writes, dtype = checked_writes(sdfg, raw, loop.loop_variable)
    return Plan(loop.label, loop, None, loop.loop_variable, sympy.sympify(begin), sympy.sympify(end), writes, dtype)


def map_plan(sdfg: dace.SDFG, state: dace.SDFGState, entry: nodes.MapEntry, device: bool) -> Plan:
    exit_node = state.exit_node(entry)
    members = [n for n in state.scope_subgraph(entry).nodes() if n not in (entry, exit_node)]
    plain_dataflow(state, members, "the map")
    if (entry.map.schedule in (dace.ScheduleType.GPU_Device, dace.ScheduleType.GPU_ThreadBlock)) != device:
        raise Refused("a device map on the host, or a host map on the device")
    if any(not c.startswith("IN_") for c in entry.in_connectors):
        raise Refused("the map has a dynamic range input")
    begin, end, step = entry.map.range.ranges[-1]
    if step != 1:
        raise Refused(f"the map steps by {step}")
    variable = entry.map.params[-1]
    body = Body(sdfg, state, variable, entry)
    raw: list[Write] = []
    for e in state.in_edges(exit_node):
        if e.data.is_empty():
            continue
        if e.data.wcr is not None:
            raise Refused(f"{e.data.data} is reduced across the map's iterations: a sequential loop reduces")
        data = str(e.data.data)
        raw.append(Write(data, tuple(str(i) for i in indices(e.data.subset, data)), body.value(e)))
    if not raw:
        raise Refused("the map writes nothing")
    writes, dtype = checked_writes(sdfg, raw, variable)
    if any(w.reduce for w in writes):
        raise Refused("a reduction inside a map: its threads would share the accumulator; a sequential loop reduces")
    return Plan(entry.map.label, entry, state, variable, sympy.sympify(begin), sympy.sympify(end), writes, dtype)


def admitted_ops(plan: Plan, rows: frozenset[str]) -> Plan:
    if missing := sorted(plan.rows(fused=False) - rows):
        raise Refused(f"needs {', '.join(missing)}, which the matrix's intrinsic_tasklets.rows leave out")
    return plan


def admit(sdfg: dace.SDFG, rows: Iterable[str], device: bool = False) -> Admission:
    """Every innermost loop of ``sdfg``'s own graph (a nested SDFG is not entered): a sequential loop region with one
    state, or a map at the top of its state, as a :class:`Plan` when the rows ``rows`` spell its body. With
    ``device`` only the GPU device maps count."""
    allowed = frozenset(rows)
    plans: list[Plan] = []
    refused: list[str] = []
    loops = [
        r for r in sdfg.all_control_flow_regions()
        if isinstance(r, LoopRegion) and not any(isinstance(b, LoopRegion) for b in r.all_control_flow_regions()
                                                if b is not r)
    ]  # fmt: skip
    found = False
    for loop in [] if device else loops:
        maps = [n for s in loop.states() for n in s.nodes() if isinstance(n, nodes.MapEntry)]
        if maps:
            continue  # the map is the innermost loop
        found = True
        try:
            plans.append(admitted_ops(loop_plan(sdfg, loop), allowed))
        except Refused as why:
            refused.append(f"loop {loop.label}: {why}")
    for state in sdfg.states():
        scopes = state.scope_dict()
        for entry in (n for n in state.nodes() if isinstance(n, nodes.MapEntry)):
            inner = state.scope_subgraph(entry).nodes()
            if any(isinstance(n, nodes.MapEntry) and n is not entry for n in inner):
                continue
            found = True
            try:
                if scopes[entry] is not None:
                    raise Refused("a map inside another map")
                plans.append(admitted_ops(map_plan(sdfg, state, entry, device), allowed))
            except Refused as why:
                refused.append(f"map {entry.map.label}: {why}")
    if not found:
        refused.append("no loop in the scope's own graph (a library node or a nested SDFG)")
    return Admission(tuple(plans), tuple(refused))


@dataclasses.dataclass(frozen=True, slots=True)
class Spelling:
    """How one ISA spells a plan's tasklets: the lookup target, the element type, its table, and whether a product
    feeding a sum takes the fma row. ``block`` is the elements one tasklet handles: one register, or on SVE the
    longest register the architecture allows, looped over at the run-time length under a predicate."""

    lookup: str
    dtype: str
    table: Table
    fused: bool

    @property
    def scalable(self) -> bool:
        return self.table.isa(self.lookup).lanes.get(self.dtype, 0) == 0

    @property
    def block(self) -> int:
        lanes = self.table.isa(self.lookup).lanes.get(self.dtype, 0)
        return lanes or SVE_MAX_BYTES // {"f64": 8, "f32": 4}[self.dtype]

    @property
    def vector(self) -> str:
        return frame(self.lookup, self.dtype, self.table).vector

    @property
    def scalar(self) -> str:
        return frame(self.lookup, self.dtype, self.table).scalar

    def entry(self, op: str) -> Entry:
        return self.table.entry(self.lookup, op, self.dtype)

    def header(self) -> str:
        return cpu_setup(self.lookup, self.dtype, self.table)["header"]

    def call(self, target: str, op: str, operands: list[str], pointer: str = "", scalar: str = "", **named: str) -> str:
        """The row of ``op`` as C leaving its result in ``target`` (``"V v = "``, empty for a store): its operands in
        the order the row's ``signature`` states (:func:`validate.assigned`, as its check ran it); ``named`` binds
        further signature names."""
        row = self.entry(op)
        names = {"pg": "pg", "p": pointer, "s": scalar, **named}
        if op == "fma":
            product = PRODUCT.search(row.semantics)
            if product is None:
                raise Refused(f"{self.lookup} fma: no product in its semantics {row.semantics!r}")
            words = [w.strip() for w in row.signature.partition(")")[0].strip("( ").split(",")]
            addend = next(w for w in words if w not in (*product.groups(), "pg"))
            names |= {product.group(1): operands[0], product.group(2): operands[1], addend: operands[2]}
        elif len(operands) == 2:
            names |= {"a": operands[0], "b": operands[1], "v": operands[1]}
        elif operands:
            names |= {"v": operands[0], "a": operands[0]}
        return assigned(target, row, names)


@dataclasses.dataclass(slots=True)
class Emitter:
    """C statements for one block of a plan's writes, with each distinct leaf loaded or broadcast once."""

    spelling: Spelling
    pointers: dict[tuple[str, tuple[str, ...]], str]
    scalars: dict[tuple[str, tuple[str, ...]], str]
    offset: str
    lines: list[str] = dataclasses.field(default_factory=list)
    names: dict[Expr, str] = dataclasses.field(default_factory=dict)
    count: int = 0

    def fresh(self) -> str:
        self.count += 1
        return f"__v{self.count}"

    def at(self, pointer: str) -> str:
        return f"{pointer} + {self.offset}" if self.offset else pointer

    def emit(self, e: Expr) -> str:
        if e in self.names:
            return self.names[e]
        name, s = self.fresh(), self.spelling
        declared = f"{s.vector} {name} = "
        if isinstance(e, Leaf) and e.kind == "load":
            self.lines.append(s.call(declared, "load", [], pointer=self.at(self.pointers[e.data, e.index])))
        elif isinstance(e, Leaf):
            value = self.scalars.get((e.data, e.index), e.data)
            self.lines.append(s.call(declared, "broadcast", [], scalar=f"({s.scalar})({value})"))
        else:
            args = [self.emit(a) for a in e.args]
            self.lines.append(s.call(declared, e.op, args))
        self.names[e] = name
        return name


def register_loop(spelling: Spelling, body: list[str]) -> str:
    """``body`` once for a fixed-width ISA; on SVE over the block in steps of the run-time length, with the
    predicate ``pg`` of the lookup's gen_mask row and the element offset ``__k``."""
    if not spelling.scalable:
        return "\n".join(body)
    step = SVE_TYPES[spelling.dtype][0]
    mask = spelling.call("svbool_t pg = ", "gen_mask", [], i="__k", N=f"(int64_t){spelling.block}")
    inner = "\n".join(f"    {line}" for line in [mask, *body])
    return f"for (int64_t __k = 0; __k < {spelling.block}; __k += {step}) {{\n{inner}\n}}"


@dataclasses.dataclass(frozen=True, slots=True)
class Tasklets:
    """The code of a plan's tasklets and their connectors: ``loads`` and ``stores`` map a connector to the block it
    points at (container, element index); ``scalars`` to the element it reads."""

    main: str
    loads: dict[str, tuple[str, tuple[str, ...]]]
    stores: dict[str, tuple[str, tuple[str, ...]]]
    scalars: dict[str, tuple[str, tuple[str, ...]]]
    init: str = ""
    final: str = ""


ACC, ACC_OUT, TARGET, TARGET_OUT = "__acc", "__acc_out", "__s", "__s_out"


def tasklets(plan: Plan, spelling: Spelling) -> Tasklets:
    """The main tasklet of ``plan`` (one block per iteration) and, for a reduction, the tasklets that start its
    accumulator (zero for a sum, the target's value for a min or max) and fold it into the target."""
    loads: dict[tuple[str, tuple[str, ...]], str] = {}
    scalars: dict[tuple[str, tuple[str, ...]], str] = {}
    for w in plan.writes:
        for read in leaves(w.value):
            if read.kind == "load":
                loads.setdefault((read.data, read.index), f"__in{len(loads)}")
            elif read.kind == "scalar" and read.index:
                scalars.setdefault((read.data, read.index), f"__x{len(scalars)}")
    stores = {(w.data, w.index): f"__out{n}" for n, w in enumerate(plan.writes) if not w.reduce}
    offset = "__k" if spelling.scalable else ""
    emitter = Emitter(spelling, {**loads, (ACC, ()): ACC}, scalars, offset)
    s = spelling
    init = final = ""
    for w in plan.writes:
        value = fused_value(w.value) if s.fused else w.value
        if not w.reduce:
            result = emitter.emit(value)
            emitter.lines.append(s.call("", "store", [result], pointer=emitter.at(stores[w.data, w.index])))
            continue
        acc = emitter.emit(Leaf("load", ACC))
        if s.fused and isinstance(value, Op) and value.op == "mul" and w.reduce == "reduce_add":
            args = [emitter.emit(a) for a in value.args]
            combined = s.call(f"{s.vector} __r = ", "fma", [*args, acc])
        else:
            combined = s.call(f"{s.vector} __r = ", COMBINE[w.reduce], [acc, emitter.emit(value)])
        emitter.lines += [combined, s.call("", "store", ["__r"], pointer=emitter.at(ACC_OUT))]
        init, final = reduction_tasklets(w, s)
    return Tasklets(
        register_loop(s, emitter.lines),
        {c: k for k, c in loads.items()},
        {c: k for k, c in stores.items()},
        {c: k for k, c in scalars.items()},
        init,
        final,
    )


def reduction_tasklets(write: Write, s: Spelling) -> tuple[str, str]:
    """The accumulator's start (zero for a sum, the target's value broadcast for a min or max) and the fold of the
    accumulator into the target: ``target + reduce(acc)`` for a sum, ``reduce(acc)`` for a min or max (the target is
    in the accumulator already). On SVE each run-time register is reduced and the results combined in C."""
    offset = "__k" if s.scalable else ""
    at = f" + {offset}" if offset else ""
    start = (
        s.call(f"{s.vector} __z = ", "zero", [])
        if write.reduce == "reduce_add"
        else s.call(f"{s.vector} __z = ", "broadcast", [], scalar=TARGET)
    )
    init = register_loop(s, [start, s.call("", "store", ["__z"], pointer=f"{ACC_OUT}{at}")])
    load = s.call(f"{s.vector} __a = ", "load", [], pointer=f"{ACC}{at}")
    reduced = s.call(f"{s.scalar} __p = ", write.reduce, ["__a"])
    fold = {"reduce_add": "__t = __t + __p;", "reduce_min": "__t = __p < __t ? __p : __t;",
            "reduce_max": "__t = __p > __t ? __p : __t;"}[write.reduce]  # fmt: skip
    first = "0" if write.reduce == "reduce_add" else TARGET
    loop = register_loop(s, [load, reduced, fold])
    result = f"{TARGET} + __t" if write.reduce == "reduce_add" else "__t"
    final = f"{s.scalar} __t = {first};\n{loop}\n{TARGET_OUT} = {result};"
    return init, final


def block_subset(index: tuple[str, ...], block: int) -> str:
    """The subset of ``block`` elements from ``index`` along the last dimension."""
    *outer, last = index
    return ", ".join([*outer, f"{last}:{last} + {block}"])


def element_subset(index: tuple[str, ...]) -> str:
    return ", ".join(index) or "0"


def python(e: Symbolic) -> str:
    return symbolic.symstr(e)


def whole_blocks(begin: Symbolic, end: Symbolic, block: int) -> tuple[str, Symbolic]:
    """Where the remainder starts: ``begin`` plus the elements of the whole blocks of ``[begin, end]``, as Python text
    and as an expression."""
    count = end - begin + 1
    text = f"({python(begin)}) + (({python(count)}) - (({python(count)}) % {block}))"
    return text, begin + count - sympy.Mod(count, block)


def add_tasklet(
    state: dace.SDFGState, label: str, code: str, inputs: Iterable[str], outputs: Iterable[str]
) -> nodes.Tasklet:
    """A C++ tasklet with the connectors ``inputs`` and ``outputs``."""
    return state.add_tasklet(
        label,
        dict.fromkeys(inputs),  # pyright: ignore[reportArgumentType] -- DaCe takes a dict of connector types
        dict.fromkeys(outputs),  # pyright: ignore[reportArgumentType]
        code,
        language=dace.Language.CPP,
    )


def wired(
    state: dace.SDFGState, tasklet: nodes.Tasklet, reads: Mapping[str, dace.Memlet], writes: Mapping[str, dace.Memlet]
) -> None:
    """Edges from one access node per container into ``tasklet`` and out of it into one per container."""
    sources: dict[str, nodes.AccessNode] = {}
    sinks: dict[str, nodes.AccessNode] = {}
    for connector, memlet in reads.items():
        data = str(memlet.data)
        node = sources.get(data) or sources.setdefault(data, state.add_read(data))
        state.add_edge(node, None, tasklet, connector, copy.deepcopy(memlet))
    for connector, memlet in writes.items():
        data = str(memlet.data)
        node = sinks.get(data) or sinks.setdefault(data, state.add_write(data))
        state.add_edge(tasklet, connector, node, None, copy.deepcopy(memlet))


def memlets(code: Tasklets, block: int) -> tuple[dict[str, dace.Memlet], dict[str, dace.Memlet]]:
    reads = {c: dace.Memlet(f"{d}[{block_subset(i, block)}]") for c, (d, i) in code.loads.items()}
    reads |= {c: dace.Memlet(f"{d}[{element_subset(i)}]") for c, (d, i) in code.scalars.items()}
    writes = {c: dace.Memlet(f"{d}[{block_subset(i, block)}]") for c, (d, i) in code.stores.items()}
    return reads, writes


def rewrite(sdfg: dace.SDFG, plan: Plan, spelling: Spelling) -> None:
    """``plan``'s loop in ``sdfg`` split into whole blocks, each one call of the main tasklet, and the original loop
    over the remainder."""
    code = tasklets(plan, spelling)
    if isinstance(plan.loop, LoopRegion):
        rewrite_loop(sdfg, plan.loop, plan, code, spelling.block)
    else:
        assert plan.state is not None, "a map's plan names its state"
        rewrite_map(plan.state, plan.loop, plan, code, spelling.block)


def rewrite_loop(sdfg: dace.SDFG, loop: LoopRegion, plan: Plan, code: Tasklets, block: int) -> None:
    parent = loop.parent_graph
    i = plan.variable
    start, _ = whole_blocks(plan.begin, plan.end, block)
    main = LoopRegion(
        f"{loop.label}_intrinsic",
        f"({i} + {block}) <= ({python(plan.end + 1)})",
        i,
        f"{i} = {python(plan.begin)}",
        f"{i} = ({i} + {block})",
    )
    state = main.add_state(f"{loop.label}_intrinsic_body", is_start_block=True)
    reads, writes = memlets(code, block)
    reduction = next((w for w in plan.writes if w.reduce), None)
    chain: list[ControlFlowBlock] = [main]
    if reduction is not None:
        acc, _ = sdfg.add_array(
            f"{loop.label}_acc",
            [block],
            sdfg.arrays[reduction.data].dtype,
            storage=dtypes.StorageType.Register,  # pyright: ignore[reportArgumentType] -- an aenum member
            transient=True,
            find_new_name=True,
        )
        whole = dace.Memlet(f"{acc}[0:{block}]")
        reads[ACC], writes[ACC_OUT] = whole, whole
        target = dace.Memlet(f"{reduction.data}[{element_subset(reduction.index)}]")
        init, final = dace.SDFGState(f"{loop.label}_acc_init"), dace.SDFGState(f"{loop.label}_acc_fold")
        start_reads = {TARGET: target} if reduction.reduce != "reduce_add" else {}
        wired(init, add_tasklet(init, f"{loop.label}_acc_init", code.init, start_reads, [ACC_OUT]), start_reads,
              {ACC_OUT: whole})  # fmt: skip
        fold_reads = {ACC: whole, TARGET: target}
        fold = add_tasklet(final, f"{loop.label}_acc_fold", code.final, fold_reads, [TARGET_OUT])
        wired(final, fold, fold_reads, {TARGET_OUT: target})
        chain = [init, main, final]
    wired(state, add_tasklet(state, f"{loop.label}_intrinsic", code.main, reads, writes), reads, writes)
    first = parent.start_block is loop
    for block_node in chain:
        parent.add_node(block_node)
    for edge in list(parent.in_edges(loop)):
        parent.add_edge(edge.src, chain[0], edge.data)
        parent.remove_edge(edge)
    for a, b in zip(chain, [*chain[1:], loop]):
        parent.add_edge(a, b, dace.InterstateEdge())
    if first:
        parent.start_block = parent.node_id(chain[0])
    loop.init_statement = CodeBlock(f"{i} = {start}")


def rewrite_map(state: dace.SDFGState, entry: nodes.MapEntry, plan: Plan, code: Tasklets, block: int) -> None:
    ranges = list(entry.map.range.ranges)
    begin, end, _ = ranges[-1]
    begin, end = sympy.sympify(begin), sympy.sympify(end)
    _, start = whole_blocks(begin, end, block)
    outer = {p: str(dace.subsets.Range([r])) for p, r in zip(entry.map.params, ranges)}
    outer[plan.variable] = f"{python(begin)}:{python(start)}:{block}"
    reads, writes = memlets(code, block)
    sources = {e.src.data: e.src for e in state.in_edges(entry) if isinstance(e.src, nodes.AccessNode)}
    sinks = {e.dst.data: e.dst for e in state.out_edges(state.exit_node(entry)) if isinstance(e.dst, nodes.AccessNode)}
    entry.map.range = dace.subsets.Range([*ranges[:-1], (start, end, 1)])
    _, main, _ = state.add_mapped_tasklet(
        f"{entry.map.label}_intrinsic",
        outer,
        reads,
        code.main,
        writes,
        schedule=entry.map.schedule,
        language=dace.Language.CPP,
        external_edges=True,
        input_nodes=sources,
        output_nodes=sinks,
    )
    main.map.gpu_block_size = entry.map.gpu_block_size


def rendered(sdfg: dace.SDFG, lookup: str, fused: bool, rows: Iterable[str]) -> tuple[dace.SDFG, str]:
    """A copy of ``sdfg`` with every admitted loop's body an intrinsic tasklet of ``lookup``, and the header line its
    unit needs; :class:`Refused` when no loop is admitted."""
    copied = copy.deepcopy(sdfg)
    admission = admit(copied, rows)
    if not admission.plans:
        raise Refused("; ".join(admission.refused))
    table = load()
    header = ""
    for plan in admission.plans:
        spelling = Spelling(lookup, plan.dtype, table, fused)
        header = spelling.header()
        rewrite(copied, plan, spelling)
    copied.validate()
    return copied, header


@functools.cache
def checked(lookup: str, op: str, dtype: str) -> bool:
    """Whether the lookup's ``(lookup, op, dtype)`` row ran correctly on this host (:func:`validate.validate`); a row
    the host cannot run is not checked."""
    # shortcut: verdicts live per process (about 0.5 s a row), keep them in a file once sweeps start many processes
    return validate(lookup, op, dtype).ok is True


@dataclasses.dataclass(frozen=True, slots=True)
class Offer:
    """A scope's intrinsic-tasklet candidates on this host: ``(ISA, FP level)`` cells ("" the default level), and
    the line the report gives the axis for the scope."""

    cells: tuple[tuple[str, str], ...]
    note: str


def levels(matrix: Matrix, plans: tuple[Plan, ...]) -> tuple[list[str], str]:
    """The FP levels the tasklets build at ("" the default), or why none: a reduction at the reassociating level,
    else the default and, when a product feeds a sum, the contracting level too."""
    if any(p.reduces for p in plans):
        if REASSOC_LEVEL not in matrix.fp_levels:
            return [], f"a reduction reassociates, and the matrix declares no {REASSOC_LEVEL} level"
        return [REASSOC_LEVEL], ""
    fusable = any(fused_value(w.value) != w.value for p in plans for w in p.writes)
    return ["", *([CONTRACT_LEVEL] if fusable and CONTRACT_LEVEL in matrix.fp_levels else [])], ""


def fuses(matrix: Matrix, level: str) -> bool:
    """Whether a tasklet at ``level`` ("" the default) takes the fma row."""
    return (level or matrix.defaults.fp_level) != UNFUSED_LEVEL


def offer(matrix: Matrix, sdfg: dace.SDFG, host_isas: tuple[str, ...]) -> Offer:
    """The intrinsic-tasklet cells of a scope rendered from ``sdfg``: each ISA of the matrix's axis the host runs,
    whose rows the loops need all ran correctly here (:func:`checked`), at each level of :func:`levels`."""
    axis = matrix.intrinsic_tasklets
    if not axis.targets:
        return Offer((), "none: the matrix's intrinsic_tasklets names no target")
    admission = admit(sdfg, axis.rows)
    refused = f"; not admitted: {'; '.join(admission.refused)}" if admission.refused else ""
    if not admission.plans:
        return Offer((), f"none: {'; '.join(admission.refused)}")
    wanted, why = levels(matrix, admission.plans)
    if not wanted:
        return Offer((), f"none: {why}")
    cells: list[tuple[str, str]] = []
    skipped: list[str] = []
    for isa, lookup in axis.targets.items():
        if isa not in host_isas:
            skipped.append(f"{isa} (host lacks {matrix.isas[isa].host_flag})")
            continue
        for level in wanted:
            fused = fuses(matrix, level)
            unchecked = sorted({f"{op} {p.dtype}" for p in admission.plans for op in p.rows(fused)
                                if not checked(lookup, op, p.dtype)})  # fmt: skip
            if unchecked:
                skipped.append(f"{isa} at {level or 'default'} (rows not checked here: {', '.join(unchecked)})")
            else:
                cells.append((isa, level))
    loops = ", ".join(f"{p.label} ({', '.join(sorted(p.rows(False)))})" for p in admission.plans)
    built = ", ".join(f"{isa}{f' at {level}' if level else ''}" for isa, level in cells) or "none"
    lacking = f"; skipped: {', '.join(skipped)}" if skipped else ""
    return Offer(tuple(cells), f"{built} on {loops}{lacking}{refused}")


#: Elements one GPU thread of a device tasklet handles: the four floats of the checked ``load_wide`` row's float4.
DEVICE_BLOCK = 4
#: The ops a device tasklet spells: the fma by its SIMT row, the rest as C operators and CUDA/HIP math calls.
DEVICE_OPS = {"add": "({} + {})", "sub": "({} - {})", "mul": "({} * {})", "div": "({} / {})", "neg": "(-{})",
              "min": "fminf({}, {})", "max": "fmaxf({}, {})", "abs": "fabsf({})", "sqrt": "sqrtf({})"}  # fmt: skip
DEVICE_ROWS = ("load", "store", "broadcast", "fma", *DEVICE_OPS)
LANE_FIELDS = "xyzw"


def device_row(op: str, dialect: str) -> str:
    """The ``op`` row of ``simt.toml`` in ``dialect``, refused unless its recorded check passed."""
    found = {r.op: r for r in simt.rows()}[op]
    verdict = simt.verdicts().get((op, dialect))
    if verdict is None or verdict.ok is not True:
        raise Refused(f"the {dialect} {op} row has no passing check")
    return found.spelled(dialect)


def device_value(e: Expr, lane: int, wide: dict[tuple[str, tuple[str, ...]], str],
                 scalars: dict[tuple[str, tuple[str, ...]], str], fma: str) -> str:  # fmt: skip
    """One lane's C expression of ``e``: a load is that lane's component of its wide load."""
    if isinstance(e, Leaf):
        if e.kind == "load":
            return f"{wide[e.data, e.index]}.{LANE_FIELDS[lane]}"
        return f"(float)({scalars.get((e.data, e.index), e.data)})"
    args = [device_value(a, lane, wide, scalars, fma) for a in e.args]
    if e.op == "fma":
        return re.sub(r"\b[abc]\b", lambda m: args["abc".index(m[0])], fma)
    return DEVICE_OPS[e.op].format(*args)


def device_tasklet(plan: Plan, dialect: str) -> Tasklets:
    """A GPU thread's tasklet over :data:`DEVICE_BLOCK` elements: each load one float4 of the ``load_wide`` row (all
    four components, as its note says), each product feeding a sum the ``fma`` row, each lane stored on its own."""
    if plan.dtype != "f32":
        raise Refused(f"{plan.dtype}: the device rows load f32 four at a time")
    # shortcut: f32 only; the f16/bf16 load_wide/store_wide rows (8 per thread) join when a GPU task is half precision
    load_row = device_row("load_wide", dialect)
    pointer = load_row.split("[", 1)[0].replace("(wide)", "({})")
    fma = device_row("fma", dialect)
    loads: dict[tuple[str, tuple[str, ...]], str] = {}
    scalars: dict[tuple[str, tuple[str, ...]], str] = {}
    for w in plan.writes:
        for read in leaves(w.value):
            if read.kind == "load":
                if len(read.index) != 1 or str(read.index[0]) != plan.variable:
                    raise Refused(f"{read.data}[{', '.join(read.index)}] is not the thread's aligned float4")
                loads.setdefault((read.data, read.index), f"__in{len(loads)}")
            elif read.kind == "scalar" and read.index:
                scalars.setdefault((read.data, read.index), f"__x{len(scalars)}")
    wide = {key: f"__w{n}" for n, key in enumerate(loads)}
    lines = [f"float4 {wide[key]} = {pointer.format(c)}[0];" for key, c in loads.items()]
    stores = {(w.data, w.index): f"__out{n}" for n, w in enumerate(plan.writes)}
    for w in plan.writes:
        value = fused_value(w.value)
        connector = stores[w.data, w.index]
        lines += [f"{connector}[{j}] = {device_value(value, j, wide, scalars, fma)};" for j in range(DEVICE_BLOCK)]
    return Tasklets(
        "\n".join(lines),
        {c: k for k, c in loads.items()},
        {c: k for k, c in stores.items()},
        {c: k for k, c in scalars.items()},
    )


def device_rendered(sdfg: dace.SDFG, dialect: str) -> dace.SDFG:
    """A copy of a GPU program ``sdfg`` whose admitted device maps run :data:`DEVICE_BLOCK` elements per thread with
    a tasklet of ``dialect``'s SIMT rows (:func:`device_tasklet`), the rest in the original map; :class:`Refused`
    when no device map is admitted."""
    copied = copy.deepcopy(sdfg)
    admission = admit(copied, DEVICE_ROWS, device=True)
    done = 0
    refused = list(admission.refused)
    for plan in admission.plans:
        if plan.begin != 0:
            refused.append(f"map {plan.label}: starts at {plan.begin}, so its float4 loads are not aligned")
            continue
        try:
            code = device_tasklet(plan, dialect)
        except Refused as why:
            refused.append(f"map {plan.label}: {why}")
            continue
        assert plan.state is not None and isinstance(plan.loop, nodes.MapEntry), "a device plan is a map"
        rewrite_map(plan.state, plan.loop, plan, code, DEVICE_BLOCK)
        done += 1
    if not done:
        raise Refused("; ".join(refused))
    copied.validate()
    return copied
