# Copyright 2026 ETH Zurich and the Alloy authors.
"""Speculative mode's score: a build's predicted cycles per element of its scope, from llvm-mca on the object's
innermost loops, grouped into source loops by the maps their lines render and weighted by their iteration volumes."""

import functools
import math
import pathlib
import re
import subprocess
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass as plain

import dace
import sympy
from dace.sdfg import nodes
from pydantic.dataclasses import dataclass

from alloy import machine
from alloy.backend import runtime
from alloy.backend.build import Build
from alloy.backend.sweep import ScopeReport
from alloy.configuration_matrix import Matrix
from alloy.evaluate import timing
from alloy.evaluate.verify import Verdict
from alloy.frontend.scopes import Scope
from alloy.heuristics import fission, fp, prune
from alloy.heuristics.load import Load, load_of
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

#: Iterations llvm-mca simulates, so its cycles include loop-carried chains.
MCA_ITERATIONS = 100
#: The share of the largest cache that stays resident: conflicts and write-allocates take the rest.
CACHE_RESIDENT = 0.5
#: Cycles per lane of a gather or scatter: llvm-mca prices them far too low on recent x86 cores.
GATHER_LANE_CYCLES = 4.0
GATHER = re.compile(r"^v(gather|scatter|pgather|pscatter)")
#: What a region or a worksharing loop costs a team: the cheapest empty region measured on libomp.
REGION_NS = 470.0

#: Predictions within this fraction of the cheapest tie: memory-bound builds all sit on the bandwidth floor.
TIE = 0.02
#: Cycles per call in a loop: llvm-mca cannot see a callee, so one call per vector ranks above one per element.
CALL_CYCLES = 30.0
SOURCE_LINE = re.compile(r"^; .*:(\d+)$")
#: A rendered statement's trailing comment: the label of the tasklet it renders.
TASKLET_COMMENT = re.compile(r";\s*//\s*([A-Za-z_]\w*)\s*$")
LINE = re.compile(r"^\s*([0-9a-f]+):\s+(\S+)\s*(.*?)\s*$")
FUNCTION = re.compile(r"^[0-9a-f]+ <(.+)>:$")
#: A relocation names a call's callee.
RELOCATION = re.compile(r"^\s+[0-9a-f]+:\s+R_\S+\s+([A-Za-z_.$][\w.$@]*)")
#: Vector math entries (glibc/SLEEF GNU ABI, SLEEF, ArmPL, SVML): one call per vector of elements.
VECTOR_CALL = re.compile(r"^(_ZGV|Sleef_|armpl_|__svml_)")
TARGET = re.compile(r"\b(?:0x)?([0-9a-f]+) <")
X86_BRANCH = re.compile(r"^j[a-z]+$|^loop")
ARM_BRANCH = re.compile(r"^(b(\.[a-z]+)?|cbn?z|tbn?z)$")
CALL = re.compile(r"^(call[a-z]*|bl)$")
RETURN = re.compile(r"^ret")
JUMP = re.compile(r"^(jmp[a-z]*|b)$")
STACK = re.compile(r"%rsp|%rbp|\[sp\b|\[x29\b")
NO_ACCESS = re.compile(r"^(lea|nop|prfm|prefetch)")
SVE_LENGTH = pathlib.Path("/proc/sys/abi/sve_default_vector_length")


@plain(slots=True, frozen=True)
class Instruction:
    """One instruction; ``callee`` is what a call's relocation names, ``line`` its source line (0 when unknown)."""

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
    """One source loop's hot copy: tasklets, cycles and elements per iteration, hot calls, main-memory bytes per
    element, and its share of the scope's iterations."""

    tasklets: Strings
    cycles: float
    elements: float
    calls: int
    bytes: float
    weight: float


@dataclass(slots=True, frozen=True, config=RECORD)
class Prediction:
    """A build's predicted cycles per element, a roofline: the larger of ``compute`` (its loops' cycles over its team,
    plus its regions) and ``memory`` (their bytes over the bandwidth once the arrays leave the cache). ``regions`` and
    ``elements`` are one call's at the running size; ``elements`` is 0 when that size is unknown."""

    cycles_per_element: float
    compute: float
    memory: float
    loops: tuple[LoopCost, ...]
    machine_loops: int
    regions: float = 0.0
    elements: float = 0.0


def disassembly(archive: pathlib.Path) -> dict[str, list[Instruction]]:
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
        elif (reloc := RELOCATION.match(line)) is not None:
            if current and CALL.match(current[-1].mnemonic):
                last = current[-1]
                current[-1] = Instruction(last.address, last.mnemonic, last.operands, reloc.group(1), last.line)
        elif (insn := LINE.match(line)) is not None:
            operands = insn.group(3).split("#", 1)[0].split("//", 1)[0].strip()
            current.append(Instruction(int(insn.group(1), 16), insn.group(2), operands, line=source_line))
    return functions


def is_branch(i: Instruction) -> bool:
    return bool(X86_BRANCH.match(i.mnemonic) or ARM_BRANCH.match(i.mnemonic))


def successors(code: list[Instruction], place: int, places: dict[int, int]) -> list[int]:
    i = code[place]
    if RETURN.match(i.mnemonic):
        return []
    target = TARGET.search(i.operands) if is_branch(i) else None
    taken = [] if target is None else [places[a] for a in (int(target.group(1), 16),) if a in places]
    return taken if JUMP.match(i.mnemonic) or place + 1 == len(code) else [*taken, place + 1]


def closes_loop(code: list[Instruction], places: dict[int, int], start: int, latch: int) -> bool:
    """Whether control at ``start`` comes back to the branch at ``latch``: a real latch may sit past the function's
    return, but a fallback jumping back to the epilogue never returns to its own branch."""
    seen, frontier = set[int](), [places[start]]
    while frontier:
        place = frontier.pop()
        if code[place].address == latch:
            return True
        if place not in seen:
            seen.add(place)
            frontier += successors(code, place, places)
    return False


def innermost_spans(code: list[Instruction]) -> list[tuple[int, int]]:
    """A branch back to an earlier address it flows back from spans a loop; the innermost spans hold no other."""
    places = {i.address: place for place, i in enumerate(code)}
    spans = []
    for i in code:
        target = TARGET.search(i.operands) if is_branch(i) else None
        start = -1 if target is None else int(target.group(1), 16)
        if 0 <= start < i.address and (start not in places or closes_loop(code, places, start, i.address)):
            spans.append((start, i.address))
    return [s for s in spans if not any(o != s and s[0] <= o[0] and o[1] <= s[1] for o in spans)]


def innermost_loops(code: list[Instruction]) -> list[Loop]:
    """The loops of one function holding no other loop."""
    inner = innermost_spans(code)
    moving = [s for s in inner if any(s[0] <= i.address < s[1] and moves_data(i) for i in code)]
    loops = []
    for start, end in moving or inner:  # an outer latch laid out past the function's return moves nothing
        body = tuple(i for i in code if start <= i.address < end and not is_branch(i))
        calls = tuple(i.callee for i in body if CALL.match(i.mnemonic))
        lines = frozenset(i.line for i in body if i.line)
        loops.append(Loop(tuple(i for i in body if not CALL.match(i.mnemonic)), calls, lines))
    return loops


def moves_data(i: Instruction) -> bool:
    return "(" in i.operands or "[" in i.operands


@functools.lru_cache(maxsize=1, typed=True)
def sve_bytes() -> int:
    return int(SVE_LENGTH.read_text()) if SVE_LENGTH.is_file() else 16


def x86_bytes(i: Instruction) -> int:
    """AT&T: the vector register width, an element for a scalar or broadcast FP form, else the general register's."""
    if "(" not in i.operands or "%rip" in i.operands:  # a rip-relative operand is a constant, not an array
        return 0
    if i.mnemonic in {"vmovhpd", "vmovlpd", "vmovhps", "vmovlps"}:
        return 8
    scalar = re.search(r"(sd|ss|sh)$", i.mnemonic) or i.mnemonic.startswith("vbroadcast")
    if scalar or i.mnemonic in {"vmovq", "movq"}:
        return {"d": 8, "s": 4, "h": 2}.get(i.mnemonic[-1], 8)
    for register, width in (("%zmm", 64), ("%ymm", 32), ("%xmm", 16)):
        if register in i.operands:
            return width
    return 8 if re.search(r"%r[a-z0-9]+", i.operands) else 4


def arm_bytes(i: Instruction) -> int:
    if "[" not in i.operands or not re.match(r"^(ld|st)", i.mnemonic):
        return 0
    first = i.operands.lstrip("{").split(",")[0].strip()
    widths = {"q": 16, "d": 8, "s": 4, "h": 2, "b": 1, "x": 8, "w": 4}
    width = sve_bytes() if first.startswith("z") else 16 if first.startswith("v") else widths.get(first[:1], 8)
    lanes = len(re.findall(r"\bz\d+|\bv\d+", i.operands.split("}")[0])) if "{" in i.operands else 1
    return width * max(1, lanes) * (2 if i.mnemonic.startswith(("ldp", "stp")) else 1)


def data_bytes(loop: Loop) -> int:
    return sum(
        x86_bytes(i) + arm_bytes(i)
        for i in loop.body
        if not STACK.search(i.operands) and not NO_ACCESS.match(i.mnemonic)
    )


@functools.lru_cache(maxsize=4096, typed=True)
def mca_cycles(body: str) -> float | None:
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
    """The innermost map around a tasklet: array accesses per element (distinct memlets on its last parameter) and
    the iterations of it and every enclosing map. ``index`` tells two maps with equal facts apart."""

    accesses: int
    volume: sympy.Expr
    index: int


def map_facts(state: dace.SDFGState, entry: nodes.MapEntry, index: int) -> MapFacts:
    param, exit_node = entry.map.params[-1], state.exit_node(entry)
    accessed = {  # a read and a write of one element are two accesses; two reads of it are one
        (e.data.data, str(e.data.subset), e.dst is exit_node)
        for e in [*state.out_edges(entry), *state.in_edges(exit_node)]
        if e.data.subset is not None and param in {str(s) for s in e.data.subset.free_symbols}
    }
    volume, enclosing = sympy.Integer(1), entry
    while isinstance(enclosing, nodes.MapEntry):
        volume *= enclosing.map.range.num_elements()
        enclosing = state.entry_node(enclosing)
    return MapFacts(max(1, len(accessed)), volume, index)


def innermost_maps(sdfg: dace.SDFG) -> dict[str, MapFacts]:
    """Every tasklet label of ``sdfg``'s innermost maps, with its map's facts."""
    out: dict[str, MapFacts] = {}
    states = [b for b in sdfg.all_control_flow_blocks(recursive=True) if isinstance(b, dace.SDFGState)]
    for index, (state, entry) in enumerate((s, e) for s in states for e in prune.innermost_entries(s)):
        facts = map_facts(state, entry, index)
        out |= {n.label: facts for n in state.scope_children()[entry] if isinstance(n, nodes.Tasklet)}
    return out


def accesses_per_element(scope: Scope) -> int:
    """The most array accesses one element of any of the scope's innermost maps makes."""
    return max((f.accesses for f in innermost_maps(scope.sdfg).values()), default=1)


def tasklet_lines(source: pathlib.Path) -> dict[int, str]:
    lines = source.read_text().splitlines() if source.is_file() else []
    return {n: m.group(1) for n, text in enumerate(lines, start=1) if (m := TASKLET_COMMENT.search(text)) is not None}


def evaluated(volume: sympy.Expr, sizes: dict[str, int] | None) -> float | None:
    value = volume.subs({sympy.Symbol(k): v for k, v in (sizes or {}).items()})
    return float(value) if value.is_number else None


def temporaries(sdfg: dace.SDFG, sizes: dict[str, int]) -> int:
    """Bytes of ``sdfg``'s transient arrays that grow with the sizes: the values a fission cut widens."""
    grown = [d for d in sdfg.arrays.values() if d.transient and dace.symbolic.issymbolic(d.total_size)]
    return timing.bytes_at([d for d in grown if {str(s) for s in d.free_symbols} <= sizes.keys()], sizes)


def element_lanes(i: Instruction, width: int) -> int:
    for register, bytes_wide in (("%zmm", 64), ("%ymm", 32), ("%xmm", 16)):
        if register in i.operands:
            return bytes_wide // width
    return 1


def hot_calls(loop: Loop, elements: float) -> int:
    """Calls every iteration makes: scalar calls in a vector loop count only when there are as many as lanes; fewer
    are the fallback of a few lanes (errno, a special value)."""
    vector = sum(bool(VECTOR_CALL.match(c)) for c in loop.callees)
    scalar = len(loop.callees) - vector
    return len(loop.callees) if elements <= 1 or scalar >= elements else vector


def loop_cost(loop: Loop, tasklets: tuple[str, ...], maps: dict[str, MapFacts], scope: Scope) -> LoopCost | None:
    cycles = mca_cycles("\n".join(f"{i.mnemonic} {i.operands}" for i in loop.body) + "\n")
    if cycles is None:
        return None
    known = [maps[t] for t in tasklets if t in maps]
    accesses = max((f.accesses for f in known), default=accesses_per_element(scope))
    width = prune.smallest_element(scope.sdfg)
    per_element = width * accesses
    elements = max(1.0, data_bytes(loop) / per_element)
    cycles += GATHER_LANE_CYCLES * sum(element_lanes(i, width) for i in loop.body if GATHER.match(i.mnemonic))
    return LoopCost(tasklets, cycles, elements, hot_calls(loop, elements), float(per_element), 1.0)


def weight(tasklets: tuple[str, ...], maps: dict[str, MapFacts], sizes: dict[str, int] | None, total: float) -> float:
    volumes = [v for t in tasklets if t in maps if (v := evaluated(maps[t].volume, sizes)) is not None]
    return max(volumes) / total if volumes and total > 0 else 1.0


def source_loop(tasklets: tuple[str, ...], maps: dict[str, MapFacts]) -> frozenset[MapFacts] | tuple[str, ...]:
    """What groups machine loops: the maps their statements render, so a main loop and its epilogue count once."""
    return frozenset(maps[t] for t in tasklets if t in maps) or tasklets


def hot_copies(
    machine_loops: list[Loop], labels: dict[int, str], maps: dict[str, MapFacts], scope: Scope
) -> dict[frozenset[MapFacts] | tuple[str, ...], LoopCost]:
    """Each source loop's hot copy: the most elements per iteration, then the fewest cycles."""
    groups: dict[frozenset[MapFacts] | tuple[str, ...], LoopCost] = {}
    for loop in machine_loops:
        tasklets = tuple(sorted({labels[n] for n in loop.lines if n in labels}))
        cost = loop_cost(loop, tasklets, maps, scope)
        key = source_loop(tasklets, maps)
        held = groups.get(key)
        if cost is not None and (held is None or (cost.elements, -cost.cycles) > (held.elements, -held.cycles)):
            groups[key] = cost
    if any(groups) and () in groups:  # a loop rendering no statement (OpenMP chunking) next to the loops that do
        del groups[()]
    return groups


def weighted(
    costs: Iterable[LoopCost], maps: dict[str, MapFacts], scope: Scope, sizes: dict[str, int] | None
) -> tuple[LoopCost, ...]:
    largest = max(
        (v for f in innermost_maps(scope.sdfg).values() if (v := evaluated(f.volume, sizes)) is not None), default=0.0
    )
    return tuple(
        LoopCost(c.tasklets, c.cycles, c.elements, c.calls, c.bytes, weight(c.tasklets, maps, sizes, largest))
        for c in costs
    )


def team_of(archive: pathlib.Path, load: Load | None, cores: int) -> tuple[float, float]:
    """``(regions, threads sharing the work)``: at an unknown size every core and no region is the whole model."""
    if load is None:
        return 0.0, float(cores)
    return (load.regions, load.elements / load.span) if runtime.openmp_needs(archive) else (0.0, 1.0)


def memory_term(loops: tuple[LoopCost, ...], footprint: int, share: float) -> float:
    """Cycles per element on ``share`` of the bandwidth, once ``footprint`` bytes leave the cache."""
    if footprint <= CACHE_RESIDENT * machine.largest_cache_bytes():
        return 0.0
    bandwidth = share * machine.memory_bandwidth().bytes_per_second / machine.max_frequency_hz()
    return sum(c.weight * c.bytes for c in loops) / bandwidth


def predict(
    build: Build,
    scope: Scope,
    sizes: dict[str, int] | None = None,
    sdfg: dace.SDFG | None = None,
    *,
    running: bool = False,
) -> Prediction | None:
    """``build``'s predicted cycles per element of ``scope`` (:class:`Prediction`), each source loop weighted by its
    maps' iterations at ``sizes``. ``sdfg`` is what the build rendered (the scope's own by default). With ``running``
    the scope will run at ``sizes``: a build pays for its regions on its real team. ``None`` without an object or a
    loop llvm-mca accepts, and for a serial build at a size that does not decide the scope."""
    if build.archive is None:
        return None
    rendered = sdfg if sdfg is not None else scope.sdfg
    cores = len(machine.physical_cores())
    load = load_of(rendered, sizes or {}, cores) if running else None
    if build.candidate.serial and load is None:
        return None
    machine_loops = [loop for code in disassembly(build.archive).values() for loop in innermost_loops(code)]
    maps = innermost_maps(rendered)
    groups = hot_copies(machine_loops, tasklet_lines(build.source), maps, scope)
    if not groups:
        return None
    loops = weighted(groups.values(), maps, scope, sizes)
    regions, team = team_of(build.archive, load, cores)
    elements = load.elements if load is not None else 0.0
    compute = sum(c.weight * (c.cycles + CALL_CYCLES * c.calls) / c.elements for c in loops) / team
    if regions > 0:
        compute += regions * REGION_NS * 1e-9 * machine.max_frequency_hz() / elements
    footprint = timing.footprint(scope.sdfg, sizes) + temporaries(rendered, sizes) if sizes else 0
    memory = memory_term(loops, footprint, team / cores)
    return Prediction(max(compute, memory), compute, memory, loops, len(machine_loops), regions, elements)


#: ``{scope symbol: {candidate name: prediction}}``; a build without one (no object, no loop) is absent.
Predictions = dict[str, dict[str, Prediction]]


def predictions(reports: list[ScopeReport], sizes: dict[str, int] | None = None, running: bool = False) -> Predictions:
    """The prediction of every distinct build of every scope at ``sizes`` (the loops weigh equally without), in parallel
    (llvm-mca runs per loop). Without ``running``, :func:`predict`'s model, every core and no region, skips serial builds."""
    jobs = [
        (rep, b)
        for rep in reports
        for b in rep.builds
        if not (b.error or b.duplicate_of or (b.candidate.serial and not running))
    ]
    cut = {  # what each scope's fission builds rendered, split once per scope
        rep.scope.symbol: fission.fissioned(rep.scope.sdfg)
        for rep in reports
        if any(b.candidate.fission for owner, b in jobs if owner is rep)
    }

    def score(job: tuple[ScopeReport, Build]) -> Prediction | None:
        rep, b = job
        return predict(b, rep.scope, sizes, cut[rep.scope.symbol] if b.candidate.fission else None, running=running)

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
    """The scope's speculative winner: among the correct distinct builds at or below the default FP level
    (:func:`fp.default_level`) within :data:`TIE` of the fewest predicted cycles per element (all of them when none is
    predicted), the default level's, then the first in sweep order. Without verdicts
    (no manifest) every build that compiled counts as correct. A serial build counts only at a size that decides it."""
    scores = predicted.get(rep.scope.symbol, {})
    level = fp.default_level(matrix, rep.scope, finite_inputs=finite_inputs)

    def correct(b: Build) -> bool:
        verified = not verdicts or (b.name in verdicts and verdicts[b.name].ok)
        sized = not b.candidate.serial or (b.name in scores and scores[b.name].elements > 0)
        return not b.error and not b.duplicate_of and sized and verified

    def cost(b: Build) -> float:
        return scores[b.name].cycles_per_element if b.name in scores else math.inf

    usable = [(order, b) for order, b in enumerate(rep.builds) if correct(b)]
    if not usable:
        return rep.builds[0]
    levels = list(matrix.fp_levels)
    allowed = levels[: levels.index(level) + 1]  # a scope's default level is as far as a speculative pick relaxes
    usable = [item for item in usable if item[1].candidate.resolved(matrix)[0] in allowed] or usable
    cheapest = min(cost(b) for _, b in usable)
    tied = [(order, b) for order, b in usable if cost(b) <= cheapest * (1 + TIE)]
    return min(tied, key=lambda item: (item[1].candidate.resolved(matrix)[0] != level, item[0]))[1]
