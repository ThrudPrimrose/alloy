# Copyright 2026 ETH Zurich and the Alloy authors.
"""The report's control-flow tree: every block in execution order, loops with their domain, branches with their
condition, and each outlined scope as a row labeled with its entry symbol."""

import dace
import numpy as np

from alloy.frontend import scopes, tree
from alloy.frontend.tree import CfgNode, Kind
from helpers import MATRIX

N, T = dace.symbol("N"), dace.symbol("T")


@dace.program
def stepped(a: dace.float64[N], b: dace.float64[N], flag: dace.int64):
    for t in range(T):
        b[:] = a + 1.0
        a[:] = b * 2.0
    if flag > 0:
        a[:] = np.sin(b)
    else:
        a[:] = 0.0


def kinds(node: CfgNode) -> list[Kind]:
    """``node``'s subtree in preorder, by kind."""
    return [node.kind, *(kind for child in node.children for kind in kinds(child))]


def labels(node: CfgNode, kind: Kind) -> list[str]:
    return [node.label] * (node.kind == kind) + [label for child in node.children for label in labels(child, kind)]


def test_each_outlined_scope_is_a_row_named_by_its_entry_symbol():
    program = scopes.outline(stepped.to_sdfg(), MATRIX.libm_calls)

    sut = tree.cfg_tree(program.sdfg)

    assert sorted(labels(sut, Kind.SCOPE)) == sorted(scope.symbol for scope in program.scopes)
    assert Kind.MAP not in kinds(sut), "every top-level nest is outlined"


def test_the_time_loop_and_the_branches_keep_their_domain_and_conditions():
    sut = tree.cfg_tree(stepped.to_sdfg())

    (loop,) = [child for child in sut.children if child.kind == Kind.LOOP]
    (conditional,) = [child for child in sut.children if child.kind == Kind.CONDITIONAL]
    assert loop.detail == "t=0:T"
    assert [branch.detail for branch in conditional.children] == ["when (flag > 0)", "else"]
    assert sum(kind == Kind.MAP for kind in kinds(loop)) == 2


def test_the_text_tree_has_one_row_per_node_under_the_sdfg_header():
    sdfg = stepped.to_sdfg()
    sut = tree.cfg_tree(sdfg)

    text = tree.render(sut)

    assert text.splitlines()[0] == f"SDFG '{sdfg.label}'"
    assert len(text.splitlines()) == len(kinds(sut))
    assert any(line.startswith("`- ") or line.startswith("|- ") for line in text.splitlines()[1:])
