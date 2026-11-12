# Copyright 2026 ETH Zurich and the Alloy authors.
"""Speculative mode: the innermost loops of a build's disassembly, the bytes their memory operations move, llvm-mca's
cycles per element of the hot loop, the per-scope pick (fewest cycles, ties to the default FP level), and an untimed
run that links its picks."""

import pathlib
import subprocess

import dace
import numpy as np
import pytest
import sympy
from dace.libraries.standard.nodes import Scan

from alloy import api, machine
from alloy.backend.build import Build, Remarks
from alloy.backend.candidates import Candidate
from alloy.backend.sweep import ScopeReport
from alloy.evaluate.verify import Verdict
from alloy.frontend import scopes
from alloy.heuristics import predict
from alloy.heuristics.load import Load
from alloy.heuristics.predict import Instruction, Prediction
from alloy.report import Mode
from helpers import MATRIX, REDUCTIONS, SCALE_MANIFEST, build, gcc_only, load_program, write_manifest

N, M, K = dace.symbol("N"), dace.symbol("M"), dace.symbol("K")


@dace.program
def roots(x: dace.float64[N], y: dace.float64[N]):
    for i in dace.map[0:N]:
        y[i] = np.sqrt(x[i]) / x[i]


@dace.program
def two_rows(a: dace.float64[M, N], b: dace.float64[M, N], c: dace.float64[M, K], d: dace.float64[M, K]):
    for i in dace.map[0:M]:
        for j in dace.map[0:N]:
            b[i, j] = a[i, j] * 2.0
        for k in dace.map[0:K]:
            d[i, k] = c[i, k] + 1.0


@dace.program
def two_sums(
    a: dace.float64[M, N], b: dace.float64[M, N], c: dace.float64[M, K], d: dace.float64[M, K], e: dace.float64[M, K]
):
    for i in dace.map[0:M]:
        for j in dace.map[0:N]:
            b[i, j] = a[i, j] + 1.0
        for k in dace.map[0:K]:
            d[i, k] = c[i, k] + e[i, k]


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


def test_a_jump_back_to_the_epilogue_is_no_loop_so_the_errno_fallback_past_the_return_never_counts_as_one():
    code = listing(  # gcc's scalar sqrt: the hot loop, the return, then the out-of-line call for a negative input
        (0x40, "vmovsd", "(%rdi,%rax,8), %xmm1"),
        (0x45, "vucomisd", "%xmm1, %xmm2"),
        (0x49, "ja", "0x71 <f+0x71>"),
        (0x4B, "vsqrtsd", "%xmm1, %xmm1, %xmm0"),
        (0x53, "vmovsd", "%xmm0, (%rsi,%rax,8)"),
        (0x5E, "jne", "0x40 <f+0x40>"),
        (0x60, "addq", "$0x38, %rsp"),
        (0x64, "retq", ""),
        (0x71, "vmovapd", "%xmm1, %xmm0"),
    )
    fallback = Instruction(0x8F, "callq", "0x94 <f+0x94>", "sqrt")
    tail = listing(
        (0xB2, "vmovsd", "%xmm0, (%rsi,%rax,8)"), (0xBD, "jne", "0x40 <f+0x40>"), (0xBF, "jmp", "0x60 <f+0x60>")
    )

    (sut,) = predict.innermost_loops([*code, fallback, *tail])

    assert sut.callees == ()
    assert [i.address for i in sut.body] == [0x40, 0x45, 0x4B, 0x53]


def test_a_latch_laid_out_past_the_return_still_closes_its_loop():
    code = listing(  # gcc on a triangular nest: the trip test leaves through the return, the latch follows it
        (0x10, "vmovupd", "(%rdi,%rax,8), %ymm0"),
        (0x16, "cmpq", "%rax, %rdx"),
        (0x19, "jle", "0x22 <f+0x22>"),
        (0x1B, "retq", ""),
        (0x22, "incq", "%rax"),
        (0x25, "jmp", "0x10 <f+0x10>"),
    )

    (sut,) = predict.innermost_loops(code)

    assert [i.address for i in sut.body] == [0x10, 0x16, 0x1B, 0x22]


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


def test_a_load_of_what_the_loop_stored_keeps_its_chain_where_llvm_mca_can_see_it():
    body = listing(  # nvhpc on y[j] = c[j] * y[j-1] + x[j]: two elements per iteration, y[j-1] read back from memory
        (0x00, "vmovsd", "-0x10(%rdx,%r9), %xmm0"),
        (0x06, "vmulsd", "-0x8(%rdi,%r9), %xmm0, %xmm0"),
        (0x0C, "vaddsd", "-0x8(%rsi,%r9), %xmm0, %xmm0"),
        (0x12, "vmovsd", "%xmm0, -0x8(%rdx,%r9)"),
        (0x18, "vmulsd", "(%rdi,%r9), %xmm0, %xmm0"),
        (0x1E, "vaddsd", "(%rsi,%r9), %xmm0, %xmm0"),
        (0x24, "vmovsd", "%xmm0, (%rdx,%r9)"),
        (0x2A, "addq", "$0x10, %r9"),
    )

    sut = predict.forwarded(tuple(body))

    assert (sut[0].mnemonic, sut[0].operands) == ("vmovapd", "%xmm0, %xmm0")
    assert sut[1:] == tuple(body[1:])
    assert predict.data_bytes(predict.Loop(sut, ())) == 48


def test_a_load_of_another_array_or_of_a_later_element_stays_a_load():
    body = listing(
        (0x00, "vmovsd", "(%rdi,%rax,8), %xmm0"),
        (0x06, "vmovsd", "0x8(%rdx,%rax,8), %xmm1"),
        (0x0C, "vmovsd", "%xmm0, (%rdx,%rax,8)"),
    )

    assert predict.forwarded(tuple(body)) == tuple(body)


def scan_scope() -> scopes.Scope:
    sdfg = dace.SDFG("scan")
    for name in "xcy":
        sdfg.add_array(name, [N], dace.float64)
    state = sdfg.add_state()
    scan = Scan("scan")
    for data, subset, connector in (("x", "1:N", "_scan_in"), ("c", "1:N", "_scan_coef"), ("y", "0", "_scan_init")):
        state.add_edge(state.add_read(data), None, scan, connector, dace.Memlet(f"{data}[{subset}]"))
    state.add_edge(scan, "_scan_out", state.add_write("y"), None, dace.Memlet("y[1:N]"))
    return scopes.Scope("scan", (), "", sdfg, False, False, sympy.Integer(1))


def test_a_library_node_touches_each_array_it_runs_over_per_element_and_a_seed_only_once():
    assert predict.accesses_per_element(scan_scope()) == 3


def only_scope(program: dace.program) -> scopes.Scope:
    (scope,) = scopes.outline(program.to_sdfg(), MATRIX.libm_calls).scopes
    return scope


@pytest.mark.gcc
@pytest.mark.avx512
def test_a_wider_vector_build_is_predicted_cheaper_per_element(tmp_path):
    scope = only_scope(load_program(f"{REDUCTIONS}:scale"))
    builds = (build(scope, Candidate("c", "gcc", isa=isa), MATRIX, tmp_path, {}) for isa in ("avx512", "avx2"))

    wide, narrow = (predict.predict(b, scope, MATRIX) for b in builds)

    assert wide is not None and narrow is not None
    assert (len(wide.loops), len(narrow.loops)) == (1, 1), "a main loop and its epilogues are one source loop"
    assert (wide.loops[0].elements, narrow.loops[0].elements) == (8.0, 4.0)
    assert wide.cycles_per_element < narrow.cycles_per_element


@pytest.mark.gcc
def test_an_errno_bound_scalar_sqrt_is_predicted_dearer_than_its_fast_math_vector_form(tmp_path):
    scope = only_scope(roots)
    strict = build(scope, Candidate("c", "gcc"), MATRIX, tmp_path, {})
    fast = build(scope, Candidate("c", "gcc", fp_level="fast"), MATRIX, tmp_path, {})

    sut = [predict.predict(b, scope, MATRIX) for b in (strict, fast)]

    assert sut[0] is not None and sut[1] is not None
    assert sut[0].loops[0].elements == 1.0 < sut[1].loops[0].elements
    assert sut[1].cycles_per_element < sut[0].cycles_per_element


#: gcc 14's ``-Q --help=target`` lines on a Zen 4, listed only for ``-march=native``.
GCC_TARGET_LISTING = """#!/bin/sh
[ "$1" = -march=native ] || exit 1
printf '  -march=                     \\t\\tznver4\\n  -mcpu=                      \\t\\t\\n'
"""


def test_llvm_mca_models_every_build_on_the_cpu_its_flags_name_else_on_the_host_gcc_resolves(tmp_path, monkeypatch):
    """LLVM's host guess can be an older core than gcc's (znver3 without AVX-512 for gcc's znver4), so a native build
    of any compiler is costed on gcc's host CPU, and a build whose flags name another CPU llvm-mca knows on that one."""
    gcc = tmp_path / "gcc"
    gcc.write_text(GCC_TARGET_LISTING)
    gcc.chmod(0o755)
    monkeypatch.setattr(predict, "mca_knows", lambda cpu: cpu in ("znver4", "x86-64-v3", "neoverse-v2"))
    native_gcc, native_clang = (Candidate("c", c, isa="avx512").flags(MATRIX) for c in ("gcc", "clang"))

    assert predict.target_cpu(str(gcc), native_clang) == predict.target_cpu(str(gcc), native_gcc) == "znver4"
    assert predict.target_cpu(str(gcc), (*native_gcc, "-march=x86-64-v3")) == "x86-64-v3", "the last -march wins"
    assert predict.target_cpu(str(gcc), ("-O3", "-mcpu=neoverse-v2+sve2")) == "neoverse-v2"
    assert predict.target_cpu(str(gcc), ("-O3", "-march=sandybridge")) == "znver4", "a CPU llvm-mca does not know"
    assert predict.target_cpu(str(tmp_path / "absent-gcc"), native_gcc) == "native"


def a_build(candidate: Candidate) -> Build:
    return Build(
        candidate, candidate.name(MATRIX), {}, pathlib.Path("v0.c"), pathlib.Path("lib.a"), (), "0f", Remarks(1, ())
    )


def scored(cost: float) -> Prediction:
    return Prediction(cost, cost, 0.0, (), 1)


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


def test_a_serial_build_never_wins_a_speculative_pick_however_cheap_it_looks():
    scope = only_scope(roots)
    default, serial = a_build(Candidate("c", "gcc")), a_build(Candidate("c", "gcc", serial=True))
    rep = ScopeReport(scope, (default, serial))
    cheaper = {scope.symbol: {default.name: scored(2.0), serial.name: scored(1.0)}}

    assert predict.choose(rep, {}, cheaper, MATRIX, finite_inputs=False) is default
    assert predict.choose(rep, {}, {}, MATRIX, finite_inputs=False) is default


@pytest.mark.gcc
def test_the_model_scores_openmp_builds_only_because_it_spreads_loops_over_the_cores(tmp_path):
    scope = only_scope(roots)
    default = build(scope, Candidate("c", "gcc"), MATRIX, tmp_path / "default", {})
    serial = build(scope, Candidate("c", "gcc", serial=True), MATRIX, tmp_path / "serial", {})

    sut = predict.predictions([ScopeReport(scope, (default, serial))], MATRIX)

    assert list(sut[scope.symbol]) == [default.name]


def parallel_and_serial(scope: scopes.Scope, folder: pathlib.Path) -> ScopeReport:
    default = build(scope, Candidate("c", "gcc"), MATRIX, folder / "default", {})
    return ScopeReport(
        scope, (default, build(scope, Candidate("c", "gcc", serial=True), MATRIX, folder / "serial", {}))
    )


@pytest.mark.gcc
@pytest.mark.parametrize(("size", "serial"), [(16, True), (10**9, False)])
def test_a_scope_runs_serial_below_the_crossover_and_stays_parallel_above_it(tmp_path, monkeypatch, size, serial):
    monkeypatch.setattr(machine, "physical_cores", lambda: (0, 2, 4, 6))
    rep = parallel_and_serial(only_scope(roots), tmp_path)

    predicted = predict.predictions([rep], MATRIX, {"N": size}, running=True)

    assert predict.choose(rep, {}, predicted, MATRIX, finite_inputs=False).candidate.serial is serial


def ten_cycle_loop(archive: pathlib.Path, source: pathlib.Path) -> dict[str, list[Instruction]]:
    loop = (0x00, "vmovsd", "(%rdi,%rax,8), %xmm0"), (0x05, "vmovsd", "%xmm0, (%rsi,%rax,8)"), (0x0A, "jne", "0x0 <f>")
    return {"f": listing(*loop)}


@pytest.mark.gcc
def test_a_parallel_build_pays_for_its_region_and_a_serial_one_for_its_lone_core(tmp_path, monkeypatch):
    monkeypatch.setattr(machine, "physical_cores", lambda: (0, 2, 4, 6))
    monkeypatch.setattr(machine, "max_frequency_hz", lambda: 3.0e9)
    monkeypatch.setattr(predict, "disassembly", ten_cycle_loop)
    monkeypatch.setattr(predict, "mca_cycles", lambda body, cpu: 10.0)
    rep = parallel_and_serial(only_scope(roots), tmp_path)

    sut = predict.predictions([rep], MATRIX, {"N": 1000}, running=True)[rep.scope.symbol]

    parallel, serial = sut[rep.builds[0].name], sut[rep.builds[1].name]
    assert (parallel.regions, parallel.elements) == (1.0, 1000.0)
    assert (serial.regions, serial.elements) == (0.0, 1000.0)
    assert parallel.compute == pytest.approx(3.91), "2.5 for the four cores' share, 470 ns at 3 GHz over 1000 elements"
    assert serial.compute == pytest.approx(10.0)


@pytest.mark.gcc
def test_a_size_the_sdfg_does_not_decide_leaves_the_serial_build_unranked(tmp_path):
    rep = parallel_and_serial(only_scope(roots), tmp_path)

    sut = predict.predictions([rep], MATRIX, {}, running=True)[rep.scope.symbol]

    assert list(sut) == [rep.builds[0].name] and sut[rep.builds[0].name].elements == 0.0


@pytest.mark.gcc
def test_the_object_decides_whether_a_build_pays_for_a_team(tmp_path):
    rep = parallel_and_serial(only_scope(roots), tmp_path)
    load = Load(1.0, 1000.0, 250.0)
    parallel, serial = rep.builds[0].archive, rep.builds[1].archive
    assert parallel is not None and serial is not None

    assert predict.team_of(parallel, load, 4) == (1.0, 4.0)
    assert predict.team_of(serial, load, 4) == (0.0, 1.0)


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


@dace.program
def fixed(a: dace.float64[256], out: dace.float64[256]):
    for i in dace.map[0:256]:
        out[i] = a[i] * 2.0


@pytest.mark.gcc
@pytest.mark.parametrize(("running", "serial"), [({"N": 16}, True), ({"N": 10**9}, False), (None, False), ({}, False)])
def test_a_declared_size_decides_the_picks_thread_count_and_an_open_one_keeps_the_parallel_pick(
    tmp_path, monkeypatch, running, serial
):
    monkeypatch.setattr(machine, "physical_cores", lambda: (0, 1, 2, 3))  # a team pays off on any host
    sdfg = load_program(f"{REDUCTIONS}:scale").to_sdfg()
    matrix = gcc_only(tmp_path)

    sut = api.generate(sdfg, tmp_path / "out", matrix=matrix, mode=Mode.SPECULATIVE, running=running)

    (winner,) = (sut.winners or {}).values()
    assert winner.candidate.serial is serial


@pytest.mark.gcc
def test_a_size_the_sdfg_fixes_needs_no_declaration(tmp_path):
    matrix = gcc_only(tmp_path)

    sut = api.generate(fixed.to_sdfg(), tmp_path / "out", matrix=matrix, mode=Mode.SPECULATIVE)

    (winner,) = (sut.winners or {}).values()
    assert winner.candidate.serial


def test_a_rendered_statement_names_its_tasklet_in_its_trailing_comment(tmp_path):
    source = tmp_path / "v0.c"
    source.write_text("for (i = 0; i < N; i += 1) {\n    t = (a * x);  // _Mult_\n    y[i] = t;  // assign_3\n}\n")

    assert predict.tasklet_lines(source) == {2: "_Mult_", 3: "assign_3"}


HEADER = "static inline double twice(double x) {\n  return x * 2.0 + 1.0;\n}\n"
#: Line 2 names a tasklet the loop never runs; line 2 of the header is the inlined body the loop does run.
UNIT = """#include "twice.h"
double unused = 0.0;  // other_tasklet
void k(double *restrict a, const double *restrict b, long n) {
  for (long i = 0; i < n; ++i)
    a[i] = twice(b[i]);  // loop_tasklet
}
"""


@pytest.mark.clang
def test_a_loop_names_only_the_tasklets_of_its_own_source_and_not_an_inlined_header_line_of_the_same_number(tmp_path):
    """clang's line table gives inlined code its header's lines: a header line must not name the scope source's
    statement that has the same number."""
    (tmp_path / "twice.h").write_text(HEADER)
    source = tmp_path / "v0.c"
    source.write_text(UNIT)
    obj = tmp_path / "v0.o"
    clang = MATRIX.compilers["clang"]
    command = ["clang", "-O3", "-fPIC", *clang.line_tables, "-c", str(source), "-o", str(obj)]
    subprocess.run(command, check=True)
    labels = predict.tasklet_lines(source)

    loops = [loop for code in predict.disassembly(obj, source).values() for loop in predict.innermost_loops(code)]

    named = {labels[n] for loop in loops for n in loop.lines if n in labels}
    assert loops and named == {"loop_tasklet"}


@pytest.mark.gcc
def test_each_source_loop_of_a_scope_is_costed_and_weighted_by_its_share_of_the_iterations(tmp_path, monkeypatch):
    scope = only_scope(two_rows)
    built = build(scope, Candidate("c", "gcc"), MATRIX, tmp_path, {})
    maps = predict.innermost_maps(scope.sdfg)
    first = {maps[t]: n for n, t in sorted(predict.tasklet_lines(built.source).items(), reverse=True) if t in maps}
    assert len(first) == 2, "a statement line of each map"
    copy = (0x00, "vmovsd", "(%rdi,%rax,8), %xmm0"), (0x05, "vmovsd", "%xmm0, (%rsi,%rax,8)")
    loops = {
        str(n): [*(Instruction(a, m, o, line=n) for a, m, o in copy), Instruction(0x0A, "jne", "0x0 <f>")]
        for n in first.values()
    }
    monkeypatch.setattr(machine, "physical_cores", lambda: (0, 2, 4, 6))
    monkeypatch.setattr(predict, "disassembly", lambda archive, source: loops)
    monkeypatch.setattr(predict, "mca_cycles", lambda body, cpu: 10.0)

    sut = predict.predict(built, scope, MATRIX, {"M": 4, "N": 64, "K": 16})

    assert sut is not None
    assert sorted(loop.weight for loop in sut.loops) == [0.25, 1.0]
    assert sut.compute == pytest.approx(3.125), "(1.0 + 0.25) * 10 cycles per element, over four cores"


@pytest.mark.gcc
def test_a_build_with_a_source_loop_llvm_mca_rejects_every_copy_of_is_unranked(tmp_path, monkeypatch):
    """Costed on the loops llvm-mca accepts, a build whose heavy loop it rejects (zmm on a model without AVX-512)
    would look ten times cheaper and win the pick; it gets no prediction instead."""
    scope = only_scope(two_rows)
    built = build(scope, Candidate("c", "gcc"), MATRIX, tmp_path, {})
    maps = predict.innermost_maps(scope.sdfg)
    first = {maps[t]: n for n, t in sorted(predict.tasklet_lines(built.source).items(), reverse=True) if t in maps}
    assert len(first) == 2, "a statement line of each map"
    loops = {
        str(n): [
            Instruction(0x00, "vmovupd", f"(%rdi,%rax,8), {register}", line=n),
            Instruction(0x05, "vmovupd", f"{register}, (%rsi,%rax,8)", line=n),
            Instruction(0x0A, "jne", "0x0 <f>"),
        ]
        for n, register in zip(first.values(), ("%xmm0", "%zmm0"), strict=True)
    }
    monkeypatch.setattr(machine, "physical_cores", lambda: (0, 2, 4, 6))
    monkeypatch.setattr(predict, "disassembly", lambda archive, source: loops)
    monkeypatch.setattr(predict, "mca_cycles", lambda body, cpu: None if "zmm" in body else 10.0)

    assert predict.predict(built, scope, MATRIX, {"M": 4, "N": 64, "K": 16}) is None


@pytest.mark.gcc
def test_two_loops_of_one_operator_each_weigh_their_own_iterations(tmp_path):
    scope = only_scope(two_sums)
    built = build(scope, Candidate("c", "gcc"), MATRIX, tmp_path, {})

    sut = predict.predict(built, scope, MATRIX, {"M": 4, "N": 16, "K": 4000})

    assert sut is not None
    assert sorted(loop.weight for loop in sut.loops) == [0.004, 1.0]


@pytest.mark.gcc
def test_two_loops_of_one_operator_each_count_their_own_array_accesses(tmp_path):
    scope = only_scope(two_sums)
    built = build(scope, Candidate("c", "gcc"), MATRIX, tmp_path, {})

    sut = predict.predict(built, scope, MATRIX, {"M": 4, "N": 16, "K": 4000})

    assert sut is not None
    assert sorted(loop.bytes for loop in sut.loops) == [16.0, 24.0], "a read and a write, then two reads and a write"


@pytest.mark.gcc
def test_without_sizes_every_source_loop_weighs_the_same(tmp_path):
    scope = only_scope(two_rows)
    built = build(scope, Candidate("c", "gcc"), MATRIX, tmp_path, {})

    sut = predict.predict(built, scope, MATRIX)

    assert sut is not None and [loop.weight for loop in sut.loops] == [1.0, 1.0]


def test_a_build_on_the_bandwidth_floor_is_predicted_by_its_memory_term_only_beyond_the_cache(tmp_path):
    scope = only_scope(load_program(f"{REDUCTIONS}:scale"))
    built = build(scope, Candidate("c", "gcc"), MATRIX, tmp_path, {})
    elements = 64 * machine.largest_cache_bytes() // 8  # x and y: 16x the cache

    beyond = predict.predict(built, scope, MATRIX, {"N": elements})
    within = predict.predict(built, scope, MATRIX, {"N": 64})

    assert beyond is not None and within is not None
    assert within.memory == 0.0 and within.cycles_per_element == within.compute
    assert beyond.memory > beyond.compute, "a scaled copy streams two arrays through memory"
    assert beyond.cycles_per_element == beyond.memory


def test_builds_within_the_tie_band_go_to_the_default_fp_level():
    scope = only_scope(roots)
    builds = (a_build(Candidate("c", "gcc")), a_build(Candidate("c", "gcc", fp_level="noerrno")))
    rep = ScopeReport(scope, builds)
    near = {scope.symbol: {builds[0].name: scored(1.00), builds[1].name: scored(1.01)}}
    far = {scope.symbol: {builds[0].name: scored(1.00), builds[1].name: scored(1.10)}}

    assert predict.choose(rep, {}, near, MATRIX, finite_inputs=False) is builds[1]
    assert predict.choose(rep, {}, far, MATRIX, finite_inputs=False) is builds[0]
