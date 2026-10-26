# Copyright 2026 ETH Zurich and the Alloy authors.
"""Speculative mode: the innermost loops of a build's disassembly, the bytes their memory operations move, llvm-mca's
cycles per element of the hot loop, the per-scope pick (fewest cycles, ties to the default FP level), and an untimed
run that links its picks."""

import pathlib

import dace
import numpy as np
import pytest

from alloy import api
from alloy.backend.build import Build, Remarks, build
from alloy.backend.candidates import Candidate
from alloy.backend.sweep import ScopeReport
from alloy.evaluate.verify import Verdict
from alloy.frontend import scopes
from alloy.heuristics import predict
from alloy.heuristics.predict import Instruction, Prediction
from alloy.report import Mode
from helpers import MATRIX, REDUCTIONS, SCALE_MANIFEST, gcc_only, load_program, write_manifest

N = dace.symbol("N")


@dace.program
def roots(x: dace.float64[N], y: dace.float64[N]):
    for i in dace.map[0:N]:
        y[i] = np.sqrt(x[i]) / x[i]


def listing(*lines: tuple[int, str, str]) -> list[Instruction]:
    return [Instruction(address, mnemonic, operands) for address, mnemonic, operands in lines]


def test_only_a_loop_holding_no_other_loop_is_innermost_and_a_forward_branch_spans_none():
    code = listing(
        (0x00, "xorl", "%eax, %eax"),
        (0x04, "vmovupd", "(%rdi,%rax,8), %zmm0"),
        (0x0A, "jne", "0x14 <f+0x14>"),
        (0x0C, "addq", "$0x8, %rax"),
        (0x10, "jne", "0x4 <f+0x4>"),
        (0x14, "incq", "%rcx"),
        (0x18, "jne", "0x0 <f>"),
    )

    (sut,) = predict.innermost_loops(code)

    assert [i.address for i in sut.body] == [0x04, 0x0C]


@pytest.mark.parametrize(
    ("mnemonic", "operands", "moved"),
    [
        ("vmovupd", "(%rdi,%rax,8), %zmm0", 64),
        ("vfmadd231pd", "(%rsi,%rax,8), %ymm1, %ymm0", 32),
        ("vmovsd", "(%rdi), %xmm0", 8),
        ("vbroadcastss", "(%rdi), %zmm1", 4),
        ("vaddpd", "%zmm1, %zmm2, %zmm0", 0),
    ],
)
def test_an_x86_memory_operation_moves_its_vector_width_or_one_element(mnemonic, operands, moved):
    assert predict.x86_bytes(Instruction(0, mnemonic, operands)) == moved


@pytest.mark.parametrize(
    ("mnemonic", "operands", "moved"),
    [("ldp", "q0, q1, [x0]", 32), ("ldr", "d0, [x1, x8, lsl #3]", 8), ("st1", "{v0.2d, v1.2d}, [x2]", 32)],
)
def test_an_aarch64_memory_operation_moves_its_register_width_twice_for_a_pair(mnemonic, operands, moved):
    assert predict.arm_bytes(Instruction(0, mnemonic, operands)) == moved


def test_stack_spills_do_not_count_as_data_the_loop_moves():
    loop = predict.Loop(
        tuple(listing((0, "vmovupd", "(%rdi,%rax,8), %zmm0"), (6, "vmovupd", "%zmm0, -0x40(%rsp)"))), ()
    )

    assert predict.data_bytes(loop) == 64


def test_a_vector_loop_pays_for_its_vector_math_calls_and_a_scalar_loop_for_every_call():
    loop = predict.Loop((), ("_ZGVeN8v_sin", "sin"))

    assert predict.hot_calls(loop, elements=8.0) == 1
    assert predict.hot_calls(loop, elements=1.0) == 2


def only_scope(program: dace.program) -> scopes.Scope:
    (scope,) = scopes.outline(program.to_sdfg(), MATRIX.libm_calls).scopes
    return scope


@pytest.mark.gcc
def test_a_wider_vector_build_is_predicted_cheaper_per_element(tmp_path):
    scope = only_scope(load_program(f"{REDUCTIONS}:scale"))
    wide = build(scope, Candidate("c", "gcc", isa="avx512"), MATRIX, tmp_path, {})
    narrow = build(scope, Candidate("c", "gcc", isa="avx2"), MATRIX, tmp_path, {})

    sut = [predict.predict(b, scope) for b in (wide, narrow)]

    assert sut[0] is not None and sut[1] is not None
    assert (sut[0].elements_per_iteration, sut[1].elements_per_iteration) == (8.0, 4.0)
    assert sut[0].cycles_per_element < sut[1].cycles_per_element


@pytest.mark.gcc
def test_an_errno_bound_scalar_sqrt_is_predicted_dearer_than_its_fast_math_vector_form(tmp_path):
    scope = only_scope(roots)
    strict = build(scope, Candidate("c", "gcc"), MATRIX, tmp_path, {})
    fast = build(scope, Candidate("c", "gcc", fp_level="fast"), MATRIX, tmp_path, {})

    sut = [predict.predict(b, scope) for b in (strict, fast)]

    assert sut[0] is not None and sut[1] is not None
    assert sut[0].elements_per_iteration == 1.0 < sut[1].elements_per_iteration
    assert sut[1].cycles_per_element < sut[0].cycles_per_element


def a_build(candidate: Candidate) -> Build:
    return Build(
        candidate, candidate.name(MATRIX), {}, pathlib.Path("v0.c"), pathlib.Path("lib.a"), (), "0f", Remarks(1, ())
    )


def scored(cost: float) -> Prediction:
    return Prediction(cost, cost, 1.0, 0, 1)


def test_the_pick_is_the_correct_build_with_the_fewest_cycles_and_a_tie_goes_to_the_default_fp_level():
    scope = only_scope(roots)
    builds = (a_build(Candidate("c", "gcc")), a_build(Candidate("c", "gcc", fp_level="noerrno")))
    wrong = a_build(Candidate("c", "gcc", fp_level="fast"))
    rep = ScopeReport(scope, (*builds, wrong))
    verdicts = {b.name: Verdict("pass") for b in builds} | {wrong.name: Verdict("fail")}

    tie = {scope.symbol: {b.name: scored(2.0) for b in builds} | {wrong.name: scored(0.5)}}
    cheaper = {scope.symbol: {builds[0].name: scored(1.0), builds[1].name: scored(2.0)}}

    assert predict.choose(rep, verdicts, tie, MATRIX, finite_inputs=False) is builds[1], "noerrno is roots' default"
    assert predict.choose(rep, verdicts, cheaper, MATRIX, finite_inputs=False) is builds[0]


@pytest.mark.gcc
def test_a_speculative_run_verifies_times_nothing_and_links_its_picks(tmp_path):
    manifest = write_manifest(tmp_path, "scale", SCALE_MANIFEST)
    sdfg = load_program(f"{REDUCTIONS}:scale").to_sdfg()

    sut = api.generate(sdfg, tmp_path / "out", manifest=manifest, matrix=gcc_only(tmp_path), mode=Mode.SPECULATIVE)

    assert sut.timings is None and sut.verification is not None and sut.predictions is not None
    assert sut.best is not None and (tmp_path / "out" / "best" / "Makefile").is_file()
    report = (tmp_path / "out" / "report.md").read_text()
    assert "(speculative)" in report.splitlines()[0]
    assert "cycles/elem" in report
