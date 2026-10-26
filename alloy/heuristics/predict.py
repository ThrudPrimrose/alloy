# Copyright 2026 ETH Zurich and the Alloy authors.
"""Speculative mode's score: a build's predicted cycles per element of its scope. The innermost loops come from the
object's disassembly (backward branches), grouped into source loops by the tasklets their source lines render (a
main loop and its epilogues are one group); each group's hot copy costs llvm-mca's cycles on the host CPU over the
elements one iteration handles (the bytes its memory operations move), and the scope sums its groups weighted by
their maps' iteration volumes."""

import functools
import math
import pathlib
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass as plain

import dace
import sympy
from dace.sdfg import nodes
from pydantic.dataclasses import dataclass

from alloy import machine
from alloy.backend.build import Build
from alloy.backend.sweep import ScopeReport
from alloy.configuration_matrix import Matrix
from alloy.evaluate import timing
from alloy.evaluate.verify import Verdict
from alloy.frontend.scopes import Scope
from alloy.heuristics import fission, fp
from alloy.records import RECORD, Strings

__all__ = [
    "Instruction",
    "Loop",
    "LoopCost",
    "Prediction",
    "Predictions",
    "accesses_per_element",
    "choose",
    "innermost_loops",
    "predict",
    "predictions",
]

#: Iterations llvm-mca simulates; its total cycles over this count include loop-carried dependency chains.
MCA_ITERATIONS = 100
#: The share of the largest cache a scope's arrays may fill and still stay resident: the cache is shared with the rest
#: of the program and loses lines to conflicts and write-allocates, so beyond half of it the loops stream memory.
CACHE_RESIDENT = 0.5
#: Predictions within this fraction of the cheapest are a tie (left to the default FP level, then sweep order): a
#: memory-bound scope's builds all sit on the bandwidth floor.
TIE = 0.02
#: Cycles charged per call in a loop: llvm-mca cannot see a callee (a vector math routine), so every call costs the
#: same, which ranks one call per vector of elements above one per element.
CALL_CYCLES = 30.0
#: A source position ``llvm-objdump -l`` prints before the instructions it covers.
SOURCE_LINE = re.compile(r"^; .*:(\d+)$")
#: A rendered statement's trailing comment: the label of the tasklet it renders.
TASKLET_COMMENT = re.compile(r";\s*//\s*([A-Za-z_]\w*)\s*$")
#: A line of ``llvm-objdump -d --no-show-raw-insn``: address, mnemonic, operands.
LINE = re.compile(r"^\s*([0-9a-f]+):\s+(\S+)\s*(.*?)\s*$")
FUNCTION = re.compile(r"^[0-9a-f]+ <(.+)>:$")
#: A relocation ``llvm-objdump -r`` prints under the instruction it patches: names a call's callee.
RELOCATION = re.compile(r"^\s+[0-9a-f]+:\s+R_\S+\s+([A-Za-z_.$][\w.$@]*)")
#: Vector math entries (glibc/SLEEF GNU ABI, SLEEF, ArmPL, SVML): a call per vector of elements, on the hot path.
VECTOR_CALL = re.compile(r"^(_ZGV|Sleef_|armpl_|__svml_)")
TARGET = re.compile(r"\b(?:0x)?([0-9a-f]+) <")
X86_BRANCH = re.compile(r"^j[a-z]+$|^loop")
ARM_BRANCH = re.compile(r"^(b(\.[a-z]+)?|cbn?z|tbn?z)$")
CALL = re.compile(r"^(call[a-z]*|bl)$")
STACK = re.compile(r"%rsp|%rbp|\[sp\b|\[x29\b")
NO_ACCESS = re.compile(r"^(lea|nop|prfm|prefetch)")
SVE_LENGTH = pathlib.Path("/proc/sys/abi/sve_default_vector_length")


@plain(slots=True, frozen=True)
class Instruction:
    """One instruction; ``callee`` is the symbol a call's relocation names, ``""`` otherwise; ``line`` its source line
    (0 when unknown)."""

    address: int
    mnemonic: str
    operands: str
    callee: str = ""
    line: int = 0


@plain(slots=True, frozen=True)
class Loop:
    """An innermost loop: its body (branches and calls excluded), the callees of its calls and its source lines."""

    body: tuple[Instruction, ...]
    callees: tuple[str, ...]
    lines: frozenset[int] = frozenset()


@dataclass(slots=True, frozen=True, config=RECORD)
class LoopCost:
    """One source loop's hot copy (the one handling the most elements per iteration): the tasklets it renders, its
    cycles and elements per iteration, its hot calls, the main-memory bytes one element moves, and its share of the
    scope's iterations."""

    tasklets: Strings
    cycles: float
    elements: float
    calls: int
    bytes: float
    weight: float


@dataclass(slots=True, frozen=True, config=RECORD)
class Prediction:
    """A build's predicted cycles per element of its scope, a roofline: the larger of its compute (its source loops'
    llvm-mca cycles, weighted, spread over the physical cores) and its memory term (their main-memory bytes over the
    bandwidth, 0 while the scope's arrays fill at most :data:`CACHE_RESIDENT` of the largest cache); the loops behind
    it, and the object's innermost machine loops."""

    cycles_per_element: float
    compute: float
    memory: float
    loops: tuple[LoopCost, ...]
    machine_loops: int


def disassembly(archive: pathlib.Path) -> dict[str, list[Instruction]]:
    """Every function of ``archive``'s objects, by name, as its instructions in address order."""
    listing = subprocess.run(
        ["llvm-objdump", "-d", "-r", "-l", "--no-show-raw-insn", str(archive)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    functions: dict[str, list[Instruction]] = {}
    current: list[Instruction] = []
    source_line = 0
    for line in listing.splitlines():
        if (head := FUNCTION.match(line)) is not None:
            current, source_line = functions.setdefault(head.group(1), []), 0
        elif (position := SOURCE_LINE.match(line)) is not None:
            source_line = int(position.group(1))
        elif (reloc := RELOCATION.match(line)) is not None:  # a call's callee, or a constant's address: no instruction
            if current and CALL.match(current[-1].mnemonic):
                last = current[-1]
                current[-1] = Instruction(last.address, last.mnemonic, last.operands, reloc.group(1), last.line)
        elif (insn := LINE.match(line)) is not None:
            operands = insn.group(3).split("#", 1)[0].split("//", 1)[0].strip()
            current.append(Instruction(int(insn.group(1), 16), insn.group(2), operands, line=source_line))
    return functions


def is_branch(i: Instruction) -> bool:
    return bool(X86_BRANCH.match(i.mnemonic) or ARM_BRANCH.match(i.mnemonic))


def innermost_loops(code: list[Instruction]) -> list[Loop]:
    """The loops of one function holding no other loop: a branch back to an earlier address spans a loop."""
    spans = []
    for i in code:
        target = TARGET.search(i.operands) if is_branch(i) else None
        if target is not None and int(target.group(1), 16) < i.address:
            spans.append((int(target.group(1), 16), i.address))
    inner = [s for s in spans if not any(o != s and s[0] <= o[0] and o[1] <= s[1] for o in spans)]
    loops = []
    for start, end in inner:
        body = tuple(i for i in code if start <= i.address < end and not is_branch(i))
        calls = tuple(i.callee for i in body if CALL.match(i.mnemonic))
        lines = frozenset(i.line for i in body if i.line)
        loops.append(Loop(tuple(i for i in body if not CALL.match(i.mnemonic)), calls, lines))
    return loops


@functools.lru_cache(maxsize=1, typed=True)
def sve_bytes() -> int:
    return int(SVE_LENGTH.read_text()) if SVE_LENGTH.is_file() else 16


def x86_bytes(i: Instruction) -> int:
    """Bytes an x86 instruction moves to or from memory (AT&T): its vector register width, an element for a scalar
    or broadcast FP form, else its general register width."""
    if "(" not in i.operands:
        return 0
    scalar = re.search(r"(sd|ss|sh)$", i.mnemonic) or i.mnemonic.startswith("vbroadcast")
    if scalar or i.mnemonic in {"vmovq", "movq"}:
        return {"d": 8, "s": 4, "h": 2}.get(i.mnemonic[-1], 8)
    for register, width in (("%zmm", 64), ("%ymm", 32), ("%xmm", 16)):
        if register in i.operands:
            return width
    return 8 if re.search(r"%r[a-z0-9]+", i.operands) else 4


def arm_bytes(i: Instruction) -> int:
    """Bytes an aarch64 load or store moves: by register class, twice for a pair, the SVE length for z registers."""
    if "[" not in i.operands or not re.match(r"^(ld|st)", i.mnemonic):
        return 0
    first = i.operands.lstrip("{").split(",")[0].strip()
    widths = {"q": 16, "d": 8, "s": 4, "h": 2, "b": 1, "x": 8, "w": 4}
    width = sve_bytes() if first.startswith("z") else 16 if first.startswith("v") else widths.get(first[:1], 8)
    lanes = len(re.findall(r"\bz\d+|\bv\d+", i.operands.split("}")[0])) if "{" in i.operands else 1
    return width * max(1, lanes) * (2 if i.mnemonic.startswith(("ldp", "stp")) else 1)


def data_bytes(loop: Loop) -> int:
    """Bytes one iteration of ``loop`` moves to and from the scope's arrays (stack spills excluded)."""
    return sum(
        x86_bytes(i) + arm_bytes(i)
        for i in loop.body
        if not STACK.search(i.operands) and not NO_ACCESS.match(i.mnemonic)
    )


@functools.lru_cache(maxsize=4096, typed=True)
def mca_cycles(body: str) -> float | None:
    """Cycles per iteration of ``body`` on the host CPU, or ``None`` when llvm-mca rejects it."""
    run = subprocess.run(
        ["llvm-mca", "-mcpu=native", f"-iterations={MCA_ITERATIONS}", "-"],
        input=body,
        capture_output=True,
        text=True,
        check=False,
    )
    total = re.search(r"^Total Cycles:\s+(\d+)", run.stdout, re.MULTILINE)
    return int(total.group(1)) / MCA_ITERATIONS if run.returncode == 0 and total is not None else None


@plain(slots=True, frozen=True)
class MapFacts:
    """What the innermost map around a tasklet tells the model: array accesses per element (distinct memlets that
    depend on its last, vectorized, parameter) and the iterations of it and every enclosing map."""

    accesses: int
    volume: sympy.Expr


def innermost_maps(sdfg: dace.SDFG) -> dict[str, MapFacts]:
    """Every tasklet label of ``sdfg``'s innermost maps, with its map's facts."""
    out: dict[str, MapFacts] = {}
    for node, state in sdfg.all_nodes_recursive():
        if not isinstance(node, nodes.MapEntry) or not isinstance(state, dace.SDFGState):
            continue
        inside = state.scope_children()[node]
        if any(isinstance(n, nodes.MapEntry) for n in inside):
            continue
        param, exit_node = node.map.params[-1], state.exit_node(node)
        accessed = {  # a read and a write of one element are two accesses; two reads of it are one
            (e.data.data, str(e.data.subset), e.dst is exit_node)
            for e in [*state.out_edges(node), *state.in_edges(exit_node)]
            if e.data.subset is not None and param in {str(s) for s in e.data.subset.free_symbols}
        }
        volume, entry = sympy.Integer(1), node
        while isinstance(entry, nodes.MapEntry):
            volume *= entry.map.range.num_elements()
            entry = state.entry_node(entry)
        facts = MapFacts(max(1, len(accessed)), volume)
        out |= {n.label: facts for n in inside if isinstance(n, nodes.Tasklet)}
    return out


def accesses_per_element(scope: Scope) -> int:
    """The most array accesses one element of any of the scope's innermost maps makes."""
    return max((f.accesses for f in innermost_maps(scope.sdfg).values()), default=1)


def element_bytes(scope: Scope) -> int:
    return min((d.dtype.bytes for d in scope.sdfg.arrays.values() if not d.transient), default=8)


def tasklet_lines(source: pathlib.Path) -> dict[int, str]:
    """Source line -> the tasklet label its trailing comment names."""
    lines = source.read_text().splitlines() if source.is_file() else []
    return {n: m.group(1) for n, text in enumerate(lines, start=1) if (m := TASKLET_COMMENT.search(text)) is not None}


def evaluated(volume: sympy.Expr, sizes: dict[str, int] | None) -> float | None:
    if not sizes:
        return None
    value = volume.subs({sympy.Symbol(k): v for k, v in sizes.items()})
    return float(value) if value.is_number else None


def temporaries(sdfg: dace.SDFG, sizes: dict[str, int]) -> int:
    """Bytes of ``sdfg``'s transient arrays that grow with the sizes: the values a fission cut widens."""
    grown = [d for d in sdfg.arrays.values() if d.transient and dace.symbolic.issymbolic(d.total_size)]
    numeric: dict[dace.symbol | str, int | float] = {k: v for k, v in sizes.items()}  # noqa: C416 -- widens types
    return sum(int(dace.symbolic.evaluate(d.total_size, numeric)) * d.dtype.bytes for d in grown)


def hot_calls(loop: Loop, elements: float) -> int:
    """Calls every iteration makes: all of a scalar loop's; a vector loop's calls to vector math entries, its scalar
    calls being the fallback of a few lanes (errno, a special value)."""
    return len(loop.callees) if elements <= 1 else sum(bool(VECTOR_CALL.match(c)) for c in loop.callees)


def loop_cost(loop: Loop, tasklets: tuple[str, ...], maps: dict[str, MapFacts], scope: Scope) -> LoopCost | None:
    """One machine loop's cost before weighting; ``None`` when llvm-mca rejects its body."""
    cycles = mca_cycles("\n".join(f"{i.mnemonic} {i.operands}" for i in loop.body) + "\n")
    if cycles is None:
        return None
    known = [maps[t] for t in tasklets if t in maps]
    accesses = max((f.accesses for f in known), default=accesses_per_element(scope))
    per_element = element_bytes(scope) * accesses
    elements = max(1.0, data_bytes(loop) / per_element)
    return LoopCost(tasklets, cycles, elements, hot_calls(loop, elements), float(per_element), 1.0)


def weight(tasklets: tuple[str, ...], maps: dict[str, MapFacts], sizes: dict[str, int] | None, total: float) -> float:
    """A source loop's iterations over the scope's largest map's; 1 when the sizes are unknown."""
    volumes = [v for t in tasklets if t in maps if (v := evaluated(maps[t].volume, sizes)) is not None]
    return max(volumes) / total if volumes and total > 0 else 1.0


def predict(
    build: Build, scope: Scope, sizes: dict[str, int] | None = None, sdfg: dace.SDFG | None = None
) -> Prediction | None:
    """``build``'s predicted cycles per element of ``scope`` (:class:`Prediction`): per source loop (machine loops
    grouped by the tasklets their lines render; loops rendering no statement only count when no loop renders one),
    the hot copy's ``(cycles + calls) / elements`` and main-memory bytes, weighted by its maps' iterations at
    ``sizes`` over the scope's largest map's. ``sdfg`` is what the build rendered (the scope's own by default).
    ``None`` without an object or a loop llvm-mca accepts."""
    if build.archive is None:
        return None
    machine_loops = [loop for code in disassembly(build.archive).values() for loop in innermost_loops(code)]
    labels = tasklet_lines(build.source)
    rendered = sdfg if sdfg is not None else scope.sdfg
    maps = innermost_maps(rendered)
    largest = max(
        (v for f in innermost_maps(scope.sdfg).values() if (v := evaluated(f.volume, sizes)) is not None), default=0.0
    )
    groups: dict[tuple[str, ...], LoopCost] = {}
    for loop in machine_loops:
        tasklets = tuple(sorted({labels[n] for n in loop.lines if n in labels}))
        cost = loop_cost(loop, tasklets, maps, scope)
        held = groups.get(tasklets)
        if cost is not None and (held is None or (cost.elements, -cost.cycles) > (held.elements, -held.cycles)):
            groups[tasklets] = cost
    if any(groups) and () in groups:  # a loop rendering no statement (OpenMP chunking) next to the loops that do
        del groups[()]
    if not groups:
        return None
    loops = tuple(
        LoopCost(c.tasklets, c.cycles, c.elements, c.calls, c.bytes, weight(c.tasklets, maps, sizes, largest))
        for c in groups.values()
    )
    compute = sum(c.weight * (c.cycles + CALL_CYCLES * c.calls) / c.elements for c in loops)
    compute /= len(machine.physical_cores())  # the scope's loops are OpenMP-parallel
    memory = 0.0
    footprint = timing.footprint(scope.sdfg, sizes) + temporaries(rendered, sizes) if sizes else 0
    if footprint > CACHE_RESIDENT * machine.largest_cache_bytes():
        bandwidth = machine.memory_bandwidth().bytes_per_second / machine.max_frequency_hz()
        memory = sum(c.weight * c.bytes for c in loops) / bandwidth
    return Prediction(max(compute, memory), compute, memory, loops, len(machine_loops))


#: ``{scope symbol: {candidate name: prediction}}``; a build without one (no object, no loop) is absent.
Predictions = dict[str, dict[str, Prediction]]


def predictions(reports: list[ScopeReport], sizes: dict[str, int] | None = None) -> Predictions:
    """The prediction of every distinct build of every scope at ``sizes`` (the loops weigh equally without), in
    parallel (llvm-mca runs per loop)."""
    jobs = [(rep, b) for rep in reports for b in rep.builds if not b.error and not b.duplicate_of]
    cut = {  # what each scope's fission builds rendered, split once per scope
        rep.scope.symbol: fission.fissioned(rep.scope.sdfg)
        for rep in reports
        if any(b.candidate.fission for owner, b in jobs if owner is rep)
    }

    def score(job: tuple[ScopeReport, Build]) -> Prediction | None:
        rep, b = job
        return predict(b, rep.scope, sizes, cut[rep.scope.symbol] if b.candidate.fission else None)

    with ThreadPoolExecutor(max_workers=machine.compile_jobs()) as pool:
        scored = list(pool.map(score, jobs))
    out: Predictions = {rep.scope.symbol: {} for rep in reports}
    for (rep, b), prediction in zip(jobs, scored, strict=True):
        if prediction is not None:
            out[rep.scope.symbol][b.name] = prediction
    return out


def choose(
    rep: ScopeReport, verdicts: dict[str, Verdict], predicted: Predictions, matrix: Matrix, *, finite_inputs: bool
) -> Build:
    """The scope's speculative winner: among the correct distinct builds within :data:`TIE` of the fewest predicted
    cycles per element (all of them when none is predicted), the default FP level's (:func:`fp.default_level`), then
    the first in sweep order. Without verdicts
    (no manifest) every build that compiled counts as correct."""
    scores = predicted.get(rep.scope.symbol, {})
    level = fp.default_level(matrix, rep.scope, finite_inputs=finite_inputs)

    def correct(b: Build) -> bool:
        return not b.error and not b.duplicate_of and (not verdicts or (b.name in verdicts and verdicts[b.name].ok))

    def cost(b: Build) -> float:
        return scores[b.name].cycles_per_element if b.name in scores else math.inf

    usable = [(order, b) for order, b in enumerate(rep.builds) if correct(b)]
    if not usable:
        return rep.builds[0]
    cheapest = min(cost(b) for _, b in usable)
    tied = [(order, b) for order, b in usable if cost(b) <= cheapest * (1 + TIE)]
    return min(tied, key=lambda item: (item[1].candidate.resolved(matrix)[1] != level, item[0]))[1]
