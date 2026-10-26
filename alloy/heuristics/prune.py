# Copyright 2026 ETH Zurich and the Alloy authors.
"""Which sweep cells are worth building: a scope's static facts and each compiler's default build rule out the
cells that cannot change the code, and every pruned cell keeps its reason for the report."""

import ast
from collections.abc import Callable
from dataclasses import dataclass

import dace
import sympy
from dace.sdfg import nodes
from dace.sdfg.state import LoopRegion

from alloy.backend.build import Build
from alloy.backend.candidates import Candidate
from alloy.configuration_matrix import Matrix
from alloy.frontend.scopes import Scope

__all__ = ["Facts", "Pruned", "facts", "is_native", "prune"]

#: Iterations clang unrolls a vector loop by at most (its interleave count), so a remainder can exist after a trip
#: count the vector length divides; gcc does not interleave. A trip count must be a multiple of lanes x this.
MAX_INTERLEAVE = 4


@dataclass(slots=True, frozen=True)
class Facts:
    """What a scope's code does, read from its SDFG: whether a multiply feeds an add or subtract (contraction), a
    call sets errno (libm, sqrt), it reduces, it divides or takes a min/max (fast-math approximations); the trip count
    of every innermost loop (``None`` when not a constant) and the smallest element in bytes."""

    contracts: bool
    sets_errno: bool
    reduces: bool
    approximates: bool
    trip_counts: tuple[int | None, ...]
    element_bytes: int


@dataclass(slots=True, frozen=True)
class Pruned:
    candidate: Candidate
    reason: str


def operations(tasklet: nodes.Tasklet) -> tuple[set[type], set[str]]:
    """The binary operators and called names of a Python tasklet; a tasklet in another language yields nothing."""
    if tasklet.code.language != dace.Language.Python:
        return set(), set()
    ops: set[type] = set()
    calls: set[str] = set()
    for node in ast.walk(ast.parse(tasklet.code.as_string)):
        if isinstance(node, ast.BinOp):
            ops.add(type(node.op))
        elif isinstance(node, ast.Call):
            calls.add(ast.unparse(node.func).rsplit(".", 1)[-1])
    return ops, calls


def feeds_add(state: dace.SDFGState, tasklet: nodes.Tasklet) -> bool:
    """Whether ``tasklet``'s result reaches an add or subtract: a summing write conflict, or a tasklet reading it
    through one access node."""
    for edge in state.out_edges(tasklet):
        if edge.data.wcr is not None and "+" in str(edge.data.wcr):
            return True
        for path_edge in state.memlet_tree(edge):
            reader = path_edge.dst
            if not isinstance(reader, nodes.AccessNode):
                continue
            for out in state.out_edges(reader):
                if isinstance(out.dst, nodes.Tasklet) and operations(out.dst)[0] & {ast.Add, ast.Sub}:
                    return True
    return False


def extent(begin: object, end: object, step: object) -> int | None:
    value = dace.symbolic.pystr_to_symbolic(f"(({end}) - ({begin}) + 1) / ({step})")
    return int(value) if isinstance(value, sympy.Integer) else None


def trip_counts(sdfg: dace.SDFG) -> tuple[int | None, ...]:
    """The vectorizable trip count of every innermost map (its last dimension); a sequential loop counts as unknown."""
    counts: list[int | None] = []
    for block in sdfg.all_control_flow_blocks():
        if isinstance(block, LoopRegion):
            counts.append(None)
        if not isinstance(block, dace.SDFGState):
            continue
        children = block.scope_children()
        counts.extend(
            extent(*node.map.range[-1])
            for node in block.nodes()
            if isinstance(node, nodes.MapEntry) and not any(isinstance(n, nodes.MapEntry) for n in children[node])
        )
    return tuple(counts)


def facts(scope: Scope) -> Facts:
    """``scope``'s static facts (see :class:`Facts`)."""
    contracts = approximates = sets_errno = False
    for node, state in scope.sdfg.all_nodes_recursive():
        if not isinstance(node, nodes.Tasklet) or not isinstance(state, dace.SDFGState):
            continue
        ops, calls = operations(node)
        contracts |= ast.Mult in ops and (bool(ops & {ast.Add, ast.Sub}) or feeds_add(state, node))
        sets_errno |= "sqrt" in calls
        approximates |= ast.Div in ops or bool(calls & {"min", "max", "fmin", "fmax"})
    sizes = [d.dtype.bytes for d in scope.sdfg.arrays.values() if not d.transient] or [8]
    return Facts(
        contracts=contracts,
        sets_errno=sets_errno or scope.calls_libm,
        reduces=scope.has_reduction,
        approximates=approximates,
        trip_counts=trip_counts(scope.sdfg),
        element_bytes=min(sizes),
    )


def is_native(candidate: Candidate) -> bool:
    """A compiler's default candidate for a language: the build every pruning decision reads."""
    return candidate == Candidate(candidate.language, candidate.compiler)


#: Per FP level: the fact that gives its rewrite something to act on, and the reason it is pruned without it. A
#: level not listed (strict, or one a swapped matrix adds) is always built.
BITES: dict[str, tuple[Callable[[Facts], bool], str]] = {
    "contract": (lambda f: f.contracts, "no multiply feeds an add"),
    "noerrno": (lambda f: f.sets_errno, "no libm or sqrt call"),
    "reassoc": (lambda f: f.reduces, "no reduction"),
    "fast": (lambda f: f.contracts or f.sets_errno or f.reduces or f.approximates, "nothing fast-math rewrites"),
}


def fp_reason(level: str, f: Facts) -> str:
    if level not in BITES:
        return ""
    bites, why = BITES[level]
    return "" if bites(f) else why


def divides(f: Facts, vector_bytes: int) -> bool:
    """Whether every innermost trip count is a known multiple of the vector length times the interleave."""
    if vector_bytes == 0 or not f.trip_counts or None in f.trip_counts:
        return False
    step = max(1, vector_bytes // f.element_bytes) * MAX_INTERLEAVE
    return all(count is not None and count % step == 0 for count in f.trip_counts)


def tail_reason(candidate: Candidate, matrix: Matrix, f: Facts, host_isas: tuple[str, ...]) -> str:
    """A tail on one ISA is moot when that ISA's length divides every trip count; a tail of any ISA when every
    ISA the host runs does."""
    isas = (candidate.isa,) if candidate.isa else host_isas
    moot = bool(isas) and all(divides(f, matrix.isas[i].vector_bytes) for i in isas)
    return "every trip count divides the vector length" if moot else ""


def reason(candidate: Candidate, matrix: Matrix, f: Facts, vectorizes: bool, host_isas: tuple[str, ...]) -> str:
    """Why ``candidate`` is not worth building, or ``""``."""
    explicit = (
        bool(candidate.tail) and matrix.tails[candidate.tail].render == "sve"
    )  # vector code without the vectorizer
    vector_cell = bool(candidate.isa or candidate.tail)
    if vector_cell and not explicit and not vectorizes:
        return "nothing vectorizes"
    if candidate.tail and not explicit:
        why = tail_reason(candidate, matrix, f, host_isas)
        if why:
            return why
    is_fp_flip = candidate.fp_level and candidate.veclib == "none" and not vector_cell and not candidate.knobs
    return fp_reason(candidate.fp_level, f) if is_fp_flip else ""


def prune(
    candidates: list[Candidate], matrix: Matrix, f: Facts, native: list[Build], host_isas: tuple[str, ...]
) -> tuple[list[Candidate], list[Pruned]]:
    """``candidates`` split into those to build and those pruned, given the ``native`` builds of every compiler."""
    vectorizes = any(b.remarks.vectorized > 0 for b in native)
    keep: list[Candidate] = []
    pruned: list[Pruned] = []
    for c in candidates:
        why = "" if is_native(c) else reason(c, matrix, f, vectorizes, host_isas)
        if why:
            pruned.append(Pruned(c, why))
        else:
            keep.append(c)
    return keep, pruned
