# Copyright 2026 ETH Zurich and the Alloy authors.
"""Speculative mode's score: the predicted cycles per element of a build's hot loop. The innermost loops come from
the object's disassembly (backward branches), their cycles from ``llvm-mca`` on the host CPU, and the elements one
iteration handles from the bytes its memory operations move."""

import functools
import math
import pathlib
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass as plain

import dace
from dace.sdfg import nodes
from pydantic.dataclasses import dataclass

from alloy import machine
from alloy.backend.build import Build
from alloy.backend.sweep import ScopeReport
from alloy.configuration_matrix import Matrix
from alloy.evaluate.verify import Verdict
from alloy.frontend.scopes import Scope
from alloy.heuristics import fp
from alloy.records import RECORD

__all__ = [
    "Instruction",
    "Loop",
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
#: Cycles charged per call in a loop: llvm-mca cannot see a callee (a vector math routine), so every call costs the
#: same, which ranks one call per vector of elements above one per element.
CALL_CYCLES = 30.0
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
    """One instruction; ``callee`` is the symbol a call's relocation names, ``""`` otherwise."""

    address: int
    mnemonic: str
    operands: str
    callee: str = ""


@plain(slots=True, frozen=True)
class Loop:
    """An innermost loop: its body (branches and calls excluded) and the callees of its calls."""

    body: tuple[Instruction, ...]
    callees: tuple[str, ...]


@dataclass(slots=True, frozen=True, config=RECORD)
class Prediction:
    """A build's predicted cost: cycles per element of its hot loop (the innermost loop moving the most data per
    iteration), that loop's cycles and elements per iteration, its calls, and the innermost loops found."""

    cycles_per_element: float
    loop_cycles: float
    elements_per_iteration: float
    calls: int
    loops: int


def disassembly(archive: pathlib.Path) -> dict[str, list[Instruction]]:
    """Every function of ``archive``'s objects, by name, as its instructions in address order."""
    listing = subprocess.run(
        ["llvm-objdump", "-d", "-r", "--no-show-raw-insn", str(archive)], capture_output=True, text=True, check=True
    ).stdout
    functions: dict[str, list[Instruction]] = {}
    current: list[Instruction] = []
    for line in listing.splitlines():
        if (head := FUNCTION.match(line)) is not None:
            current = functions.setdefault(head.group(1), [])
        elif (reloc := RELOCATION.match(line)) is not None and current and CALL.match(current[-1].mnemonic):
            last = current[-1]
            current[-1] = Instruction(last.address, last.mnemonic, last.operands, reloc.group(1))
        elif (insn := LINE.match(line)) is not None:
            operands = insn.group(3).split("#", 1)[0].split("//", 1)[0].strip()
            current.append(Instruction(int(insn.group(1), 16), insn.group(2), operands))
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
        loops.append(Loop(tuple(i for i in body if not CALL.match(i.mnemonic)), calls))
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


def accesses_per_element(scope: Scope) -> int:
    """Array accesses one element of the scope's innermost maps makes: the memlets at an innermost map whose subset
    depends on its last (vectorized) parameter; at least one."""
    best = 1
    for node, state in scope.sdfg.all_nodes_recursive():
        if not isinstance(node, nodes.MapEntry) or not isinstance(state, dace.SDFGState):
            continue
        if any(isinstance(n, nodes.MapEntry) for n in state.scope_children()[node]):
            continue
        param = node.map.params[-1]
        edges = [*state.out_edges(node), *state.in_edges(state.exit_node(node))]
        accessed = {  # a read and a write of one element are two accesses; two reads of it are one
            (e.data.data, str(e.data.subset), e.dst is state.exit_node(node))
            for e in edges
            if e.data.subset is not None and param in {str(s) for s in e.data.subset.free_symbols}
        }
        best = max(best, len(accessed))
    return best


def element_bytes(scope: Scope) -> int:
    return min((d.dtype.bytes for d in scope.sdfg.arrays.values() if not d.transient), default=8)


def hot_calls(loop: Loop, elements: float) -> int:
    """Calls every iteration makes: all of a scalar loop's; a vector loop's calls to vector math entries, its scalar
    calls being the fallback of a few lanes (errno, a special value)."""
    return len(loop.callees) if elements <= 1 else sum(bool(VECTOR_CALL.match(c)) for c in loop.callees)


def predict(build: Build, scope: Scope) -> Prediction | None:
    """``build``'s predicted cycles per element; ``None`` without an object, a loop or a model llvm-mca accepts."""
    if build.archive is None:
        return None
    loops = [loop for code in disassembly(build.archive).values() for loop in innermost_loops(code)]
    per_element = element_bytes(scope) * accesses_per_element(scope)
    scored = []
    for loop in loops:
        text = "\n".join(f"{i.mnemonic} {i.operands}" for i in loop.body) + "\n"
        cycles = mca_cycles(text)
        if cycles is None:
            continue
        elements = max(1.0, data_bytes(loop) / per_element)
        calls = hot_calls(loop, elements)
        cost = (cycles + CALL_CYCLES * calls) / elements
        scored.append(Prediction(cost, cycles, elements, calls, len(loops)))
    if not scored:
        return None
    return max(scored, key=lambda p: (p.elements_per_iteration, -p.cycles_per_element))


#: ``{scope symbol: {candidate name: prediction}}``; a build without one (no object, no loop) is absent.
Predictions = dict[str, dict[str, Prediction]]


def predictions(reports: list[ScopeReport]) -> Predictions:
    """The prediction of every distinct build of every scope, in parallel (llvm-mca runs per loop)."""
    jobs = [(rep, b) for rep in reports for b in rep.builds if not b.error and not b.duplicate_of]
    with ThreadPoolExecutor(max_workers=machine.compile_jobs()) as pool:
        scored = list(pool.map(lambda job: predict(job[1], job[0].scope), jobs))
    out: Predictions = {rep.scope.symbol: {} for rep in reports}
    for (rep, b), prediction in zip(jobs, scored, strict=True):
        if prediction is not None:
            out[rep.scope.symbol][b.name] = prediction
    return out


def choose(
    rep: ScopeReport, verdicts: dict[str, Verdict], predicted: Predictions, matrix: Matrix, *, finite_inputs: bool
) -> Build:
    """The scope's speculative winner: the correct distinct build with the fewest predicted cycles per element; a tie
    or no prediction goes to the default FP level (:func:`fp.default_level`), then to sweep order. Without verdicts
    (no manifest) every build that compiled counts as correct."""
    scores = predicted.get(rep.scope.symbol, {})
    level = fp.default_level(matrix, rep.scope, finite_inputs=finite_inputs)

    def correct(b: Build) -> bool:
        return not b.error and not b.duplicate_of and (not verdicts or (b.name in verdicts and verdicts[b.name].ok))

    def key(item: tuple[int, Build]) -> tuple[float, bool, int]:
        order, b = item
        cost = scores[b.name].cycles_per_element if b.name in scores else math.inf
        return cost, b.candidate.resolved(matrix)[1] != level, order

    usable = [(order, b) for order, b in enumerate(rep.builds) if correct(b)]
    return min(usable, key=key)[1] if usable else rep.builds[0]
