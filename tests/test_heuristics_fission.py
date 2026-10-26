# Copyright 2026 ETH Zurich and the Alloy authors.
"""Map fission: the work/depth heuristic cuts a map whose body keeps more values live than the registers hold, where
the fewest values cross; a cut at a node set splits the map into ``before | set | after`` with the scope's results
bit for bit."""

import copy
import pathlib
import re

import dace
import numpy as np
import pytest
from dace.config import set_temporary
from dace.frontend.python.parser import DaceProgram
from dace.sdfg import nodes
from dace.sdfg import utils as sdutil
from dace.sdfg.graph import SubgraphView
from dace.transformation import helpers

from alloy import machine
from alloy.backend.build import build
from alloy.backend.candidates import Candidate, flips
from alloy.frontend import scopes
from alloy.heuristics import fission, predict
from helpers import MATRIX, load_program

N = dace.symbol("N")
#: Values ``wide`` keeps live at once: more than any host's vector registers (32 at most).
WIDE = 40
#: An assignment tasklet's label ends in its source line and column.
LINE = re.compile(r"_\d+_\d+$")
STRICT = "-std=c++14 -fPIC -O2 -fopenmp -ffp-contract=off"


def wide(folder: pathlib.Path) -> DaceProgram:
    """``y[i] = x[i]*1.5 + x[i]*2.5 + ...``: :data:`WIDE` products, then their sum, one statement each."""
    products = "\n".join(f"        a{k} = x[i] * {k}.5" for k in range(WIDE))
    total = " + ".join(f"a{k}" for k in range(WIDE))
    source = folder / "wide.py"
    source.write_text(
        "import dace\n\nN = dace.symbol('N')\n\n\n@dace.program\n"
        "def wide(x: dace.float64[N], y: dace.float64[N]):\n"
        f"    for i in dace.map[0:N]:\n{products}\n        y[i] = {total}\n"
    )
    return load_program(f"{source}:wide")


@dace.program
def mix(x: dace.float64[N], y: dace.float64[N], z: dace.float64[N]):
    for i in dace.map[0:N]:
        t = np.exp(x[i]) * 2.0
        y[i] = t + x[i]
        z[i] = np.sin(t) - x[i]


def only_scope(program: DaceProgram) -> scopes.Scope:
    (scope,) = scopes.outline(program.to_sdfg(), MATRIX.libm_calls).scopes
    return scope


def maps(sdfg: dace.SDFG) -> list[list[str]]:
    """The sorted tasklet labels of every top-level map in execution order, an assignment's source line dropped."""
    out = []
    for state in sdutil.dfs_topological_sort(sdfg):
        children = state.scope_children()
        entries = [
            n for n in sdutil.dfs_topological_sort(state) if isinstance(n, nodes.MapEntry) and n in children[None]
        ]
        out += [sorted(LINE.sub("", n.label) for n in children[e] if isinstance(n, nodes.Tasklet)) for e in entries]
    return out


def cut_of(sdfg: dace.SDFG, *labels: str) -> fission.Cut:
    ((index, state),) = list(enumerate(sdfg.states()))
    entry = next(n for n in state.nodes() if isinstance(n, nodes.MapEntry))
    chosen = sorted(state.node_id(n) for n in state.nodes() if isinstance(n, nodes.Tasklet) and n.label in labels)
    return fission.Cut(index, state.node_id(entry), tuple(chosen))


def results(sdfg: dace.SDFG, outputs: tuple[str, ...]) -> dict[str, np.ndarray]:
    """``sdfg``'s outputs on one draw, compiled without fast math or contraction so a reordering would show."""
    x = np.random.default_rng(7).random(1000)
    out = {name: np.zeros_like(x) for name in outputs}
    with set_temporary("compiler", "cpu", "args", value=STRICT):
        sdfg(x=x, N=x.size, **out)
    return out


def test_a_body_holding_more_live_values_than_registers_is_cut_after_the_level_that_makes_them(tmp_path):
    scope = only_scope(wide(tmp_path))
    (state,) = scope.sdfg.states()

    (sut,) = fission.cuts(scope.sdfg, registers=32)

    chosen = [state.node(n) for n in sut.nodes]
    assert len(chosen) == WIDE and all(n.label.startswith("_Mult_") for n in chosen)


def test_a_body_whose_live_values_fit_the_registers_is_not_cut(tmp_path):
    assert fission.cuts(only_scope(wide(tmp_path)).sdfg, registers=WIDE) == ()
    assert fission.cuts(only_scope(mix).sdfg, registers=1) != ()
    assert fission.cuts(only_scope(mix).sdfg, registers=16) == ()


def test_a_cut_at_one_node_isolates_it_between_the_nodes_before_and_after_it_with_the_same_results():
    scope = only_scope(mix)

    sut = fission.split(scope.sdfg, (cut_of(scope.sdfg, "_Mult_"),))

    assert maps(sut) == [
        ["_numpy_exp_"],
        ["_Mult_"],
        ["_Add_", "_Sub_", "_numpy_sin_", "assign", "assign"],
    ]
    expected = results(scope.sdfg, ("y", "z"))
    assert all(np.array_equal(results(sut, ("y", "z"))[k], v) for k, v in expected.items())


def test_a_node_between_two_chosen_nodes_joins_their_piece():
    scope = only_scope(mix)

    sut = fission.split(scope.sdfg, (cut_of(scope.sdfg, "_numpy_exp_", "_numpy_sin_"),))

    assert maps(sut) == [
        ["_Mult_", "_numpy_exp_", "_numpy_sin_"],
        ["_Add_", "_Sub_", "assign", "assign"],
    ]
    expected = results(scope.sdfg, ("y", "z"))
    assert all(np.array_equal(results(sut, ("y", "z"))[k], v) for k, v in expected.items())


def test_the_heuristic_cut_widens_each_value_it_cuts_into_an_array_over_the_map(tmp_path):
    scope = only_scope(wide(tmp_path))

    sut = fission.fissioned(scope.sdfg)

    assert len(maps(sut)) == 2
    widened = [d for d in sut.arrays.values() if d.transient and d.total_size != 1]
    assert len(widened) == WIDE
    assert np.array_equal(results(sut, ("y",))["y"], results(scope.sdfg, ("y",))["y"])


def test_a_scope_with_a_cut_gets_one_fissioned_rendering_per_compiler_in_a_variant_of_its_own(tmp_path):
    scope = only_scope(wide(tmp_path))

    sut = flips(MATRIX, scope, "c", "gcc", finite_inputs=False, max_elements=None, fission=True)

    (cut,) = [c for c in sut if c.fission]
    assert cut == Candidate("c", "gcc", fission=True)
    assert cut.name(MATRIX).endswith("_fission")
    assert cut.variant_key(MATRIX) != Candidate("c", "gcc").variant_key(MATRIX)
    assert not any(c.fission for c in flips(MATRIX, scope, "c", "gcc", finite_inputs=False, max_elements=None))


@pytest.mark.gcc
def test_a_fissioned_build_is_predicted_per_piece_and_pays_for_the_values_it_widens(tmp_path):
    scope = only_scope(wide(tmp_path))
    plain = build(scope, Candidate("c", "gcc"), MATRIX, tmp_path, {})
    cut = build(scope, Candidate("c", "gcc", fission=True), MATRIX, tmp_path, {})
    beyond = {"N": 64 * machine.largest_cache_bytes() // 8}

    sut = [predict.predict(b, scope, beyond, sdfg) for b, sdfg in ((plain, None), (cut, fission.fissioned(scope.sdfg)))]

    assert sut[0] is not None and sut[1] is not None
    assert (len(sut[0].loops), len(sut[1].loops)) == (1, 2)
    assert sut[1].memory > sut[0].memory, "every widened value is stored and loaded once more per element"


def expanded(sdfg: dace.SDFG) -> tuple[dace.SDFG, dict[str, int]]:
    """A copy of ``mix``'s scope as NestForge's ``expand`` shows it: the map body one nested SDFG of three states
    (exp, then the multiply, then the rest), and the id of the block holding each of the first two tasklets."""
    sdfg = copy.deepcopy(sdfg)
    (state,) = sdfg.states()
    entry = next(n for n in state.nodes() if isinstance(n, nodes.MapEntry))
    nested = helpers.nest_state_subgraph(sdfg, state, state.scope_subgraph(entry, False, False))
    (inner,) = nested.sdfg.states()
    blocks = {}
    for label in ("_numpy_exp_", "_Mult_"):
        tasklet = next(n for n in inner.nodes() if isinstance(n, nodes.Tasklet) and n.label == label)
        blocks[label] = helpers.state_fission(SubgraphView(inner, [tasklet]))
    return sdfg, {label: nested.sdfg.node_id(block) for label, block in blocks.items()}


def cut_states(sdfg: dace.SDFG, *blocks: int) -> fission.Cut:
    ((index, state),) = list(enumerate(sdfg.states()))
    entry = next(n for n in state.nodes() if isinstance(n, nodes.MapEntry))
    return fission.Cut(index, state.node_id(entry), blocks, nested=True)


def test_a_cut_at_a_state_of_an_expanded_body_isolates_it_between_the_states_before_and_after_it():
    scope = only_scope(mix)
    sdfg, blocks = expanded(scope.sdfg)

    sut = fission.split(sdfg, (cut_states(sdfg, blocks["_Mult_"]),))

    assert maps(sut) == [
        ["_numpy_exp_"],
        ["_Mult_"],
        ["_Add_", "_Sub_", "_numpy_sin_", "assign", "assign"],
    ]
    expected = results(scope.sdfg, ("y", "z"))
    assert all(np.array_equal(results(sut, ("y", "z"))[k], v) for k, v in expected.items())


def test_a_cut_at_the_first_state_of_an_expanded_body_makes_two_maps():
    sdfg, blocks = expanded(only_scope(mix).sdfg)

    sut = fission.split(sdfg, (cut_states(sdfg, blocks["_numpy_exp_"]),))

    assert maps(sut) == [["_numpy_exp_"], ["_Add_", "_Mult_", "_Sub_", "_numpy_sin_", "assign", "assign"]]
