# Copyright 2026 ETH Zurich and the Alloy authors.
"""One call of a scope at known sizes: the OpenMP regions it enters and the elements it handles."""

import dace
import numpy as np
from dace.dtypes import ScheduleType
from dace.libraries.blas.nodes import Dot
from dace.libraries.standard.nodes import Reduce
from dace.sdfg import nodes
from dace.sdfg.state import ConditionalBlock, ControlFlowRegion, LoopRegion

from alloy.frontend import scopes
from alloy.heuristics.load import Load, load_of
from helpers import MATRIX

N = dace.symbol("N", dace.int64)


@dace.program
def sums(a: dace.float64[N], out: dace.float64[1]):
    out[0] = np.sum(a)


def a_map(state: dace.SDFGState, scope: nodes.MapEntry | None, extent: str, schedule: ScheduleType) -> nodes.MapEntry:
    entry, leave = state.add_map(f"map_{len(state.nodes())}", {f"p{len(state.nodes())}": extent}, schedule=schedule)
    state.add_nedge(entry, leave, dace.Memlet())
    if scope is not None:
        state.add_nedge(scope, entry, dace.Memlet())
        state.add_nedge(leave, state.exit_node(scope), dace.Memlet())
    return entry


def one_state() -> tuple[dace.SDFG, dace.SDFGState]:
    sdfg = dace.SDFG("nest")
    sdfg.add_symbol("N", dace.int64)
    return sdfg, sdfg.add_state("block")


def a_loop(sdfg: dace.SDFG, extent: str = "N") -> dace.SDFGState:
    loop = LoopRegion("outer", f"i < {extent}", "i", "i = 0", "i = i + 1")
    sdfg.add_node(loop, is_start_block=True)
    return loop.add_state("body", is_start_block=True)


def test_a_flat_parallel_map_enters_one_region_and_splits_among_the_cores():
    sdfg, state = one_state()
    a_map(state, None, "0:N", ScheduleType.CPU_Multicore)

    assert load_of(sdfg, {"N": 1000}, 4) == Load(1.0, 1000.0, 250.0)


def test_a_map_of_fewer_iterations_than_cores_splits_among_its_iterations():
    sdfg, state = one_state()
    a_map(state, a_map(state, None, "0:2", ScheduleType.CPU_Multicore), "0:N", ScheduleType.Sequential)

    assert load_of(sdfg, {"N": 100}, 8) == Load(1.0, 200.0, 100.0)


def test_a_parallel_map_in_a_triangular_loop_enters_a_region_per_iteration():
    sdfg = dace.SDFG("nest")
    sdfg.add_symbol("N", dace.int64)
    a_map(a_loop(sdfg), None, "i+1:N", ScheduleType.CPU_Multicore)

    sut = load_of(sdfg, {"N": 64}, 2)

    assert sut is not None and (sut.regions, sut.elements) == (64.0, 2016.0), "2016 = 63 + 62 + ... + 0"


def test_a_team_around_a_worksharing_loop_counts_the_team_once_and_the_loop_per_iteration():
    inner = dace.SDFG("inner")
    inner.add_symbol("N", dace.int64)
    a_map(a_loop(inner), None, "0:N", ScheduleType.CPU_Multicore)
    sdfg, state = one_state()
    team = a_map(state, None, "0", ScheduleType.CPU_Persistent)
    nested = state.add_nested_sdfg(inner, {}, {}, symbol_mapping={"N": "N"})
    state.add_nedge(team, nested, dace.Memlet())
    state.add_nedge(nested, state.exit_node(team), dace.Memlet())

    sut = load_of(sdfg, {"N": 10}, 2)

    assert sut is not None and (sut.regions, sut.elements) == (11.0, 100.0)


def test_a_map_inside_a_worksharing_loop_enters_no_region_of_its_own():
    sdfg, state = one_state()
    a_map(state, a_map(state, None, "0:10", ScheduleType.CPU_Multicore), "0:N", ScheduleType.CPU_Multicore)

    assert load_of(sdfg, {"N": 100}, 2) == Load(1.0, 1000.0, 500.0)


def test_a_parallel_map_under_a_sequential_one_enters_a_region_per_outer_iteration():
    sdfg, state = one_state()
    a_map(state, a_map(state, None, "0:10", ScheduleType.Sequential), "0:N", ScheduleType.CPU_Multicore)

    assert load_of(sdfg, {"N": 100}, 2) == Load(10.0, 1000.0, 500.0)


def test_a_chosen_reduction_enters_one_region_over_its_input():
    sdfg = sums.to_sdfg()
    (reduce,) = [n for n, _ in sdfg.all_nodes_recursive() if isinstance(n, Reduce)]
    reduce.implementation = "CPU"
    (scope,) = scopes.outline(sdfg, MATRIX.libm_calls).scopes

    sut = load_of(scope.sdfg, {"N": 1000}, 4)

    assert sut == Load(1.0, 1000.0, 250.0)


def test_a_size_left_open_decides_no_load():
    sdfg, state = one_state()
    a_map(state, None, "0:N", ScheduleType.CPU_Multicore)

    assert load_of(sdfg, {}, 4) is None


def test_a_library_node_of_unknown_threading_decides_no_load():
    sdfg, state = one_state()
    state.add_node(Dot("dot"))

    assert load_of(sdfg, {"N": 100}, 4) is None


def a_branch() -> dace.SDFG:
    sdfg = dace.SDFG("nest")
    branch = ConditionalBlock("choice")
    branch.add_branch(dace.properties.CodeBlock("N > 0"), ControlFlowRegion("taken"))
    sdfg.add_node(branch, is_start_block=True)
    return sdfg


def test_a_branch_decides_no_load():
    assert load_of(a_branch(), {"N": 100}, 4) is None


def test_a_branch_inside_a_parallel_map_decides_no_load():
    sdfg, state = one_state()
    team = a_map(state, None, "0:N", ScheduleType.CPU_Multicore)
    nested = state.add_nested_sdfg(a_branch(), {}, {})
    state.add_nedge(team, nested, dace.Memlet())
    state.add_nedge(nested, state.exit_node(team), dace.Memlet())

    assert load_of(sdfg, {"N": 100}, 4) is None
