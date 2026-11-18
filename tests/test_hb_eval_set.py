# Copyright 2026 ETH Zurich and the Alloy authors.
"""The Tensix eval set: which bench kernels the host contract runs, as whole-array programs."""

import pytest

pytest.importorskip("hpcagent_bench", reason="the eval set reads the bench's kernels")

from alloy.hb_plugin import eval_set
from alloy.hb_plugin.eval_set import Refused, Task, admit


@pytest.mark.parametrize(
    ("kernel", "kind", "inputs", "program"),
    [
        ("tsvc_2_s1351", "map", ["b", "c"], ("a = (b + c)",)),
        ("tsvc_2_vsumr", "reduce", ["a"], ("sum_out = sum(a)",)),  # s = sum(a); sum_out = s
        ("transc_log_sincos_sum", "reduce", ["t", "x"], ("out = sum(((log(x) * cos(t)) + sin(t)))",)),
        ("mat_scaled_add", "map", ["A", "B"], ("B = (B + (2.0 * A))",)),  # 2-D, the bench's scalar alpha
        ("tsvc_2_s1112", "map", ["b"], ("a = (b + 1.0)",)),  # a reversed loop
        ("tsvc_2_s251", "map", ["b", "c", "d"], ("s = (b + (c * d))", "a = (s * s)")),  # a scalar temporary
    ],
)
def test_an_admitted_kernel_is_its_program_over_whole_arrays(kernel, kind, inputs, program):
    sut = admit(kernel)

    assert (sut.kind, [name for name, *_ in sut.inputs], sut.program) == (kind, inputs, program)


def test_an_input_keeps_the_benchs_domain():
    (x,) = admit("transc_sin_wide").inputs

    assert x == ("x", -100.0, 100.0)


@pytest.mark.parametrize(
    ("kernel", "why"),
    [
        ("tsvc_2_s1113", "nest's index"),  # a[i] = a[LEN_1D // 2] + b[i]
        ("icon_aes_graupel", "not"),  # helpers and np.where, not the Tensix table
    ],
)
def test_a_kernel_outside_the_contract_is_refused_with_where(kernel, why):
    with pytest.raises(Refused, match=why):
        admit(kernel)


def test_the_set_holds_no_dev_kernel_and_one_kernel_per_program():
    tasks, refused = eval_set.admitted()

    names = {t.name for t in tasks}
    assert not names & eval_set.DEV
    assert refused["tsvc_2_vpv"] == "the same program as tsvc_2_s1351"  # a = a + b in place, as a = b + c
    assert len({eval_set.shape_of(t) for t in tasks}) == len(tasks)


def test_two_kernels_differing_only_in_domain_are_two_tasks():
    small, wide = admit("transc_sin_small"), admit("transc_sin_wide")

    assert small.program == wide.program
    assert eval_set.shape_of(small) != eval_set.shape_of(wide)


def test_a_task_round_trips_through_its_shape():
    task = Task("k", "map", (("p", 0.0, 1.0), ("q", 0.0, 1.0)), "r", ("r = (p * q)",))
    renamed = Task("k2", "map", (("u", 0.0, 1.0), ("v", 0.0, 1.0)), "w", ("w = (u * v)",))

    assert eval_set.shape_of(task) == eval_set.shape_of(renamed)
