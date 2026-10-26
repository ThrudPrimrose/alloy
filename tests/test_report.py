# Copyright 2026 ETH Zurich and the Alloy authors.
"""The report: the program and scope trees, each scope's top-k variants ranked by time against its baseline with
the reasons the rest dropped out, the scope x build config verdict with the chosen candidate and full argv, and a
``report.json`` that loads back exactly and refuses anything else."""

import json
import math
import pathlib
import re
from collections.abc import Callable

import pytest

from alloy import report
from alloy.backend import sweep
from alloy.backend.build import Build, Remarks, build
from alloy.backend.candidates import Candidate
from alloy.evaluate.link import Commands
from alloy.evaluate.timing import Measured, ProgramTiming, ScopeTiming, Timings
from alloy.evaluate.verify import Verdict, Verification
from alloy.frontend import scopes
from alloy.frontend.tree import Kind
from alloy.heuristics import prune
from alloy.records import dumped_json
from helpers import MATRIX, outlined

PASSED = Verdict(status="pass", error=1e-16, detail="")
FAILED = Verdict(status="fail", error=math.inf, detail="out: outside the band")


def a_build(
    tmp_path: pathlib.Path,
    compiler: str = "gcc",
    isa: str = "",
    error: str = "",
    dup: str = "",
    tail: str = "",
    masked: int = 0,
) -> Build:
    c = Candidate("c", compiler, isa=isa, tail=tail)
    archive = None if error else tmp_path / "lib.a"
    remarks = Remarks(1, ("m",))
    return Build(c, c.name(MATRIX), {}, tmp_path / "v0.c", archive, ("-O3",), "0f", remarks, error, dup, masked)


def ms(median: float) -> Measured:
    return Measured(median=median, low=median, high=median, verdict=PASSED)


def scope_and_builds(tmp_path: pathlib.Path) -> tuple[scopes.Program, sweep.ScopeReport]:
    """The first scope with seven builds: the reference, four timed alternatives (two compilers), a wrong one, a
    duplicate and a failed build."""
    program = outlined()
    builds = (
        a_build(tmp_path),
        a_build(tmp_path, isa="avx2"),
        a_build(tmp_path, isa="avx512"),
        a_build(tmp_path, compiler="clang"),
        a_build(tmp_path, compiler="clang", isa="avx2"),
        a_build(tmp_path, isa="neon"),
        a_build(tmp_path, isa="sve", dup="reference"),
        a_build(tmp_path, isa="avx512_256", error="gcc: error"),
    )
    return program, sweep.ScopeReport(program.scopes[0], builds)


def timed(rep: sweep.ScopeReport) -> ScopeTiming:
    b = rep.builds
    screen = {"reference": ms(4e-3), b[1].name: ms(2e-3), b[2].name: ms(1e-3), b[3].name: ms(3e-3), b[4].name: ms(8e-3)}
    return ScopeTiming(
        screen=screen, final={b[2].name: ms(1e-3)}, winner=b[2].name, screen_sizes={"N": 64}, final_sizes={"N": 128}
    )


def verdicts(rep: sweep.ScopeReport) -> dict[str, Verdict]:
    return {b.name: FAILED if b is rep.builds[5] else PASSED for b in rep.builds}


def test_a_scope_lists_its_k_fastest_correct_variants_against_its_baseline(tmp_path):
    _, rep = scope_and_builds(tmp_path)

    sut = report.scope_record(rep, verdicts(rep), timed(rep), MATRIX, k=3)

    assert [v.name for v in sut.top] == [rep.builds[i].name for i in (2, 1, 3)]
    assert [v.speedup for v in sut.top] == [4.0, 2.0, pytest.approx(4 / 3)]
    assert sut.top[0].final is not None and sut.top[1].final is None, "only the re-timed carry a final time"
    assert sut.baseline is not None and sut.baseline.median_ms == 4.0
    assert sut.dropped == {"fail": 1, "duplicate": 1, "build_failed": 1}
    assert sut.tree.kind == Kind.SDFG


def test_the_verdict_matrix_has_each_configs_fastest_variant_and_the_chosen_one(tmp_path):
    program, rep = scope_and_builds(tmp_path)
    timing = Timings(
        scopes={rep.scope.symbol: timed(rep)},
        program=ProgramTiming(arms={"dace_default": ms(6e-3), "alloy_full": ms(2e-3)}, sizes={"N": 128}),
    )

    sut = report.final([rep], {rep.scope.symbol: verdicts(rep)}, timing, None, MATRIX)

    (row,) = sut.matrix
    assert row.cells["gcc_strict_default_none_avx512"] == "1.000 (4.00x)"
    assert row.cells["clang_strict_default_none_avx2"] == "8.000 (0.50x)"
    assert row.cells["gcc_strict_default_none_neon"] == "fail"
    assert {"gcc_strict_default_none_native", "clang_strict_default_none_native"} <= set(sut.configs)
    assert sut.chosen == {rep.scope.symbol: rep.builds[2].name}
    assert sut.program is not None and sut.program.speedup == pytest.approx(3.0)


def test_without_timing_every_built_variant_is_listed_in_sweep_order_up_to_k(tmp_path):
    _, rep = scope_and_builds(tmp_path)

    sut = report.scope_record(rep, {}, None, MATRIX, k=report.TOP_K)

    assert [v.rank for v in sut.top] == [1, 2, 3, 4, 5]
    assert sut.top[0].name == rep.builds[0].name and all(v.speedup is None for v in sut.top)


def a_report(tmp_path: pathlib.Path) -> report.Report:
    program, rep = scope_and_builds(tmp_path)
    nan = Measured(median=math.nan, low=math.nan, high=math.nan, verdict=FAILED)
    scope_timing = timed(rep)
    scope_timing.screen["unmeasured"] = nan
    timing = Timings(
        scopes={rep.scope.symbol: scope_timing},
        program=ProgramTiming(arms={"dace_default": ms(6e-3), "alloy_full": ms(2e-3)}, sizes={"N": 128, "f": True}),
    )
    verification = Verification(
        verdicts={rep.scope.symbol: verdicts(rep)}, nondeterministic=frozenset({"out"}), programs={}, reference=tmp_path
    )
    commands = Commands(
        compile={rep.scope.symbol: ("gcc", "-O3", "-c", "scopes/s.c", "-o", "s.o")},
        link=("gcc", "-std=c23", "program.c", "-o", "libp.so", "libs.a"),
        library="libp.so",
    )
    return report.assemble(program, [rep], MATRIX, verification, timing, commands)


def test_a_written_report_carries_the_trees_and_renders_every_scope_and_the_verdict(tmp_path):
    program = outlined()
    reports = [
        sweep.ScopeReport(s, (build(s, Candidate("c", "gcc"), MATRIX, tmp_path / s.symbol, {}),))
        for s in program.scopes
    ]

    sut = report.write(program, reports, MATRIX, tmp_path)

    assert [s.symbol for s in sut.scopes] == [s.symbol for s in program.scopes]
    scope_rows = [child for state in sut.tree.children for child in state.children if child.kind == Kind.SCOPE]
    assert [row.label for row in scope_rows] == [s.symbol for s in program.scopes]
    text = (tmp_path / "report.md").read_text()
    assert text.count("\n## ") == len(program.scopes) + 2, "vectorization options, every scope, the verdict"
    assert "## Verdict" in text
    assert (tmp_path / "configuration_matrix.toml").read_bytes() == MATRIX.path.read_bytes()


def test_the_verdict_renders_the_full_compile_and_link_argv(tmp_path):
    sut = report.markdown(a_report(tmp_path), MATRIX)

    assert "gcc -O3 -c scopes/s.c -o s.o" in sut
    assert "gcc -std=c23 program.c -o libp.so libs.a" in sut


def test_a_written_report_loads_back_unchanged_including_nan_times(tmp_path):
    path = tmp_path / "report.json"
    text = dumped_json(a_report(tmp_path))
    path.write_text(text)

    sut = report.load(path)

    assert dumped_json(sut) == text
    assert sut.timing is not None and math.isnan(next(iter(sut.timing.scopes.values())).screen["unmeasured"].median)
    assert sut.verdict.program is not None and type(sut.verdict.program.sizes["f"]) is bool


def edited(tmp_path: pathlib.Path, edit: Callable[[dict], None]) -> pathlib.Path:
    data = json.loads(dumped_json(a_report(tmp_path)))
    edit(data)
    path = tmp_path / "edited.json"
    path.write_text(json.dumps(data))
    return path


@pytest.mark.parametrize(
    ("edit", "error"),
    [
        (lambda d: d.update(typo=1), "typo: Unexpected keyword argument, got 1"),
        (
            lambda d: d["scopes"][0]["top"][0].update(vectorized_loops="2"),
            "scopes.0.top.0.vectorized_loops: Input should be a valid integer, got '2'",
        ),
        (lambda d: d.update(mode="guess"), "mode: Input should be 'profile' or 'speculative', got 'guess'"),
        (lambda d: d["tree"].update(kind="block"), "tree.kind: Input should be"),
        (lambda d: d["scopes"][0].pop("symbol"), "scopes.0.symbol: Field required"),
    ],
)
def test_a_report_with_an_unknown_key_or_a_wrong_type_is_refused_naming_the_file(tmp_path, edit, error):
    path = edited(tmp_path, edit)

    with pytest.raises(ValueError, match=re.escape(error)) as raised:
        report.load(path)

    assert str(raised.value).startswith(f"{path}: not a valid Report:"), raised.value


def test_a_report_of_another_schema_is_refused(tmp_path):
    path = edited(tmp_path, lambda d: d.update(schema=1))

    with pytest.raises(ValueError, match="report schema 1"):
        report.load(path)


def test_a_masked_tail_without_masked_instructions_is_marked_not_honored(tmp_path):
    program = outlined()
    builds = (
        a_build(tmp_path),
        a_build(tmp_path, isa="avx512", tail="full_mask", masked=0),
        a_build(tmp_path, isa="avx512", tail="masked_remainder", masked=6),
    )
    rep = sweep.ScopeReport(program.scopes[0], builds)
    timing = ScopeTiming(
        screen={"reference": ms(2e-3), builds[1].name: ms(1e-3), builds[2].name: ms(1e-3)},
        final={},
        winner="reference",
        screen_sizes={},
        final_sizes={},
    )

    sut = report.matrix_row(rep, {b.name: PASSED for b in builds}, timing, MATRIX)

    assert sut.cells["gcc_strict_default_none_avx512_full_mask"] == "1.000 (2.00x) not honored"
    assert sut.cells["gcc_strict_default_none_avx512_masked_remainder"] == "1.000 (2.00x)"


def test_the_report_lists_every_isa_and_tail_with_its_compilers_or_the_reason(tmp_path):
    sut = report.markdown(a_report(tmp_path), MATRIX)

    assert "## Vectorization options" in sut
    assert "| avx2 |" in sut and "avx2 has no masks" in sut


def test_a_pruned_candidate_shows_its_reason_in_the_scope_and_in_the_verdict_matrix(tmp_path):
    program = outlined()
    builds = (a_build(tmp_path),)
    skipped = Candidate("c", "gcc", isa="avx512", note="isa avx512")
    rep = sweep.ScopeReport(program.scopes[0], builds, (prune.Pruned(skipped, "nothing vectorizes"),))

    row = report.matrix_row(rep, {b.name: PASSED for b in builds}, None, MATRIX)
    record = report.scope_record(rep, {}, None, MATRIX, k=report.TOP_K)

    assert row.cells[skipped.config_name(MATRIX)] == "pruned: nothing vectorizes"
    assert record.pruned == {skipped.name(MATRIX): "nothing vectorizes"}
    assert f"Pruned (nothing vectorizes): {skipped.name(MATRIX)}" in report.scope_lines(record)
