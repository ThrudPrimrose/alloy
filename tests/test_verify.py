# Copyright 2026 ETH Zurich and the Alloy authors.
import dataclasses
import pathlib

import dace
import numpy as np
import pytest
from dace.libraries.standard.nodes.scan import Scan
from hpcagent_bench import paths
from hpcagent_bench.frameworks.test import kernel_tolerances
from hpcagent_bench.spec import BenchSpec

from alloy import api, machine
from alloy.backend import runtime
from alloy.backend.candidates import Candidate
from alloy.backend.sweep import ScopeReport
from alloy.evaluate import link, timing, verify
from alloy.frontend import inputs, scopes
from helpers import (
    EXAMPLE,
    MATRIX,
    PREFIX_MANIFEST,
    REDUCTIONS,
    ROW_SUM_MANIFEST,
    SCALE_MANIFEST,
    build,
    handwritten_archive,
    load_program,
    outlined,
    program_and_cases,
    write_manifest,
)


def reference_run(tmp: pathlib.Path, program: scopes.Program, cases: verify.Cases) -> tuple:
    (scope,) = program.scopes
    ref = build(scope, Candidate("c", "gcc"), MATRIX, tmp / "ref", {})
    assert ref.archive is not None
    linker = link.Linker(program, MATRIX, tmp / "out")
    compiled = linker.compile({scope.symbol: ref.archive}, "reference")
    return scope, ref, linker, verify.reference_outputs(compiled, cases)


def test_fuzzed_draws_stay_inside_the_manifest_range_and_shape_every_input(tmp_path):
    path = tmp_path / "scale.yaml"
    path.write_text(SCALE_MANIFEST)

    sut = [inputs.draw(inputs.load(path, f"{REDUCTIONS}:scale"), i) for i in range(3)]

    assert all(64 <= d.sizes["N"] <= 512 for d in sut)
    assert all(d.values["a"].shape == (d.sizes["N"],) for d in sut)


def test_the_reference_program_reproduces_itself_bit_for_bit(tmp_path):
    program, cases = program_and_cases(tmp_path, "scale", SCALE_MANIFEST)
    scope, ref, linker, refs = reference_run(tmp_path, program, cases)
    again = linker.compile({scope.symbol: ref.archive}, "again")

    sut = verify.judge("exact", refs, [verify.run(again, d, cases.outputs) for d in cases.draws], [1, 1])

    assert sut.status == "exact"
    assert np.array_equal(refs.outputs[0]["out"], 2.0 * cases.draws[0].values["a"])
    assert refs.nondeterministic == frozenset()


def test_a_wrong_archive_at_the_same_fixed_path_fails_so_no_stale_binary_is_reused(tmp_path):
    program, cases = program_and_cases(tmp_path, "scale", SCALE_MANIFEST)
    scope, _, linker, refs = reference_run(tmp_path, program, cases)
    wrong = handwritten_archive(tmp_path, scope, "for (int64_t i = 0; i < N; ++i) out[i] = 3.0 * a[i];")
    compiled = linker.compile({scope.symbol: wrong}, "wrong")

    sut = verify.judge("band", refs, [verify.run(compiled, d, cases.outputs) for d in cases.draws], [1, 1])

    assert sut.status == "fail"


def test_a_crashing_candidate_is_a_verdict_not_a_crash_of_the_sweep(tmp_path):
    program, cases = program_and_cases(tmp_path, "scale", SCALE_MANIFEST)
    scope, _, linker, refs = reference_run(tmp_path, program, cases)
    compiled = linker.compile({scope.symbol: handwritten_archive(tmp_path, scope, "abort();")}, "abort")

    sut = verify.judge("band", refs, [verify.run(compiled, d, cases.outputs) for d in cases.draws], [1, 1])

    assert sut.status == "crashed"


def test_a_child_runs_on_its_own_cores_whatever_the_parent_set_after_the_fork_server_started(tmp_path, monkeypatch):
    program, cases = program_and_cases(tmp_path, "scale", SCALE_MANIFEST)
    scope, _, linker, _ = reference_run(tmp_path, program, cases)  # the fork server is running from here on
    probe = "out[0] = omp_get_max_threads(); out[1] = omp_get_num_places();"
    compiled = linker.compile({scope.symbol: handwritten_archive(tmp_path, scope, probe)}, "probe")
    monkeypatch.setenv("OMP_NUM_THREADS", "1")

    sut = verify.run(compiled, cases.draws[0], cases.outputs)

    assert not isinstance(sut, str)
    threads, places = sut[0]["out"][:2]
    assert threads == places >= 2


def test_a_reassociated_reduction_passes_the_accumulation_band(tmp_path):
    program, cases = program_and_cases(tmp_path, "row_sum", ROW_SUM_MANIFEST)
    init, reduce_scope = program.scopes
    builds = [
        ScopeReport(init, (build(init, Candidate("c", "gcc"), MATRIX, tmp_path / "i", {}),)),
        ScopeReport(
            reduce_scope,
            (
                build(reduce_scope, Candidate("c", "gcc"), MATRIX, tmp_path / "r", {}),
                build(reduce_scope, Candidate("c", "gcc", fp_level="reassoc"), MATRIX, tmp_path / "r2", {}),
            ),
        ),
    ]

    sut = verify.verify(program, MATRIX, builds, cases, tmp_path / "out")

    reassoc = builds[1].builds[1].name
    assert sut.verdicts[reduce_scope.symbol][reassoc].ok


@pytest.mark.gcc
def test_a_serial_build_of_a_parallel_map_reproduces_the_reference_outputs_bit_for_bit(tmp_path):
    program, cases = program_and_cases(tmp_path, "scale", SCALE_MANIFEST)
    scope, _, linker, refs = reference_run(tmp_path, program, cases)
    serial = build(scope, Candidate("c", "gcc", serial=True), MATRIX, tmp_path / "serial", {})
    assert serial.archive is not None
    compiled = linker.compile({scope.symbol: serial.archive}, "serial")

    sut = verify.judge(
        serial.candidate.tolerance(MATRIX), refs, [verify.run(compiled, d, cases.outputs) for d in cases.draws], [1, 1]
    )

    assert sut.status == "exact"
    assert np.array_equal(refs.outputs[0]["out"], 2.0 * cases.draws[0].values["a"])


@pytest.mark.gcc
def test_a_serial_build_of_a_reduction_stays_correct_through_the_whole_verification(tmp_path):
    program, cases = program_and_cases(tmp_path, "row_sum", ROW_SUM_MANIFEST)
    init, reduce_scope = program.scopes
    serial = build(reduce_scope, Candidate("c", "gcc", serial=True), MATRIX, tmp_path / "s", {})
    builds = [
        ScopeReport(init, (build(init, Candidate("c", "gcc"), MATRIX, tmp_path / "i", {}),)),
        ScopeReport(reduce_scope, (build(reduce_scope, Candidate("c", "gcc"), MATRIX, tmp_path / "r", {}), serial)),
    ]

    sut = verify.verify(program, MATRIX, builds, cases, tmp_path / "out")

    assert reduce_scope.has_reduction
    assert sut.verdicts[reduce_scope.symbol][serial.name].ok
    draw = cases.draws[0]
    outputs = verify.run(sut.programs[reduce_scope.symbol, serial.name], draw, cases.outputs)
    assert not isinstance(outputs, str) and outputs, outputs
    for output in outputs:
        np.testing.assert_allclose(output["out"], draw.values["a"].sum(axis=1), rtol=1e-12)


def parallel_scan() -> scopes.Program:
    """``running_sum`` with its scan in the blocked parallel lowering, the one with a region of its own."""
    sdfg = load_program(f"{REDUCTIONS}:running_sum").to_sdfg()
    for node, _ in sdfg.all_nodes_recursive():
        if isinstance(node, Scan):
            node.implementation, node.schedule = "CPU", dace.ScheduleType.CPU_Multicore
    return scopes.outline(sdfg, MATRIX.libm_calls)


@pytest.mark.gcc
def test_a_serial_build_of_a_parallel_scan_runs_with_no_openmp_call_and_folds_the_running_sum(tmp_path):
    program = parallel_scan()
    (scope,) = program.scopes
    manifest = write_manifest(tmp_path, "running_sum", SCALE_MANIFEST)
    default = build(scope, Candidate("c", "gcc"), MATRIX, tmp_path / "default", {})
    serial = build(scope, Candidate("c", "gcc", serial=True), MATRIX, tmp_path / "serial", {})
    assert default.archive is not None and serial.archive is not None
    assert "GOMP_parallel" in runtime.openmp_needs(default.archive)
    compiled = link.Linker(program, MATRIX, tmp_path / "out").compile({scope.symbol: serial.archive}, "serial")
    draw = inputs.draw(manifest, 0)

    sut = verify.run(compiled, draw, manifest.outputs)

    assert not isinstance(sut, str) and sut, sut
    assert runtime.openmp_needs(serial.archive) == frozenset()
    for outputs in sut:
        np.testing.assert_allclose(outputs["out"], np.cumsum(draw.values["a"]), rtol=0, atol=1e-10)


def test_a_floor_that_eats_the_whole_band_is_ungradeable_not_a_pass():
    ref = np.linspace(1.0, 2.0, 16)

    sut = verify.compare("band", ref, ref.copy(), 10**20, "float64")

    assert sut.status == "ungradeable"


def test_a_complex_output_is_judged_under_the_band_of_its_component_precision():
    expected = np.linspace(1.0, 2.0, 16) * (1 + 1j)
    reference = verify.Reference([{"Sigma": expected}], frozenset())

    sut = verify.judge("band", reference, [[{"Sigma": expected * (1 + 1e-15)}]], [1])

    assert sut.status == "pass"


def reserve(count: int) -> int:
    return np.empty(count).nbytes  # reserves without touching, so even an uncapped child stays harmless


def test_a_child_asking_for_more_memory_than_the_machine_has_is_a_crash_not_an_exhausted_machine():
    sut = verify.in_child(reserve, (2 * machine.available_memory() // 8,), machine.core_slots()[0], verify.slot_share())

    assert sut.startswith("raised:") and "Unable to allocate" in sut


def test_the_reference_candidate_is_judged_on_the_reference_run_not_built_again(tmp_path):
    program, cases = program_and_cases(tmp_path, "row_sum", ROW_SUM_MANIFEST)
    builds = [
        ScopeReport(r, (build(r, Candidate("c", "gcc"), MATRIX, tmp_path / r.symbol, {}),)) for r in program.scopes
    ]

    sut = verify.verify(program, MATRIX, builds, cases, tmp_path / "out")

    assert [p.name for p in (tmp_path / "out" / "programs").iterdir()] == [sut.reference.name]
    for rep in builds:
        assert sut.programs[rep.scope.symbol, rep.builds[0].name] == sut.reference
        assert sut.verdicts[rep.scope.symbol][rep.builds[0].name].status == "exact"


def test_an_accumulation_length_over_a_size_the_draw_lacks_names_that_size():
    with pytest.raises(ValueError, match="N"):
        verify.accumulation_length(outlined(), {})


def test_scaled_sizes_snap_to_a_divisibility_and_a_broken_constraint_is_refused(tmp_path):
    text = ROW_SUM_MANIFEST.replace("args:", 'constraints: ["N % 64 == 0", "M <= N"]\nargs:')
    manifest = write_manifest(tmp_path, "row_sum", text)

    assert inputs.constrained(manifest, {"M": 64, "N": 1000}) == {"M": 64, "N": 960}
    assert inputs.constrained(manifest, {"M": 4096, "N": 1024}) is None


def test_an_integer_output_is_compared_bit_identical_whatever_the_kernel_datatype():
    """An integer kernel (``int64``) has no rounding band: its outputs match exactly or fail, and an integer kernel's
    float output takes the band of its own dtype."""
    index = np.arange(8, dtype=np.int64)

    same = verify.compare("band", index, index.copy(), 8, "int64")
    off = verify.compare("band", index, index + 1, 8, "int64")
    value = verify.compare("band", np.ones(8), np.ones(8), 8, "float64")

    assert same.status == "exact" and off.status == "fail" and value.status == "pass"


def test_a_returned_output_binds_to_the_manifest_name_and_not_to_the_unwritten_buffer():
    args = {"out": np.zeros(3)}
    returned = np.array([1.0, 2.0, 3.0])

    sut = verify.bound_outputs(("out",), args, returned, {"a": None, "__return": None})

    np.testing.assert_array_equal(sut["out"], returned)


def test_an_output_nothing_supplies_is_refused():
    with pytest.raises(ValueError, match="out"):
        verify.bound_outputs(("out",), {"out": np.zeros(3)}, None, {"a": None})


def test_exact_tells_a_signed_zero_apart_but_not_two_nans():
    plus, minus = np.array([0.0, np.nan]), np.array([-0.0, -np.nan])

    assert verify.compare("exact", plus, minus, 1, "float64").status == "fail"
    assert verify.compare("exact", plus, plus.copy(), 1, "float64").status == "exact"
    assert verify.compare("exact", np.array([np.nan]), np.array([-np.nan]), 1, "float64").status == "exact"


def test_verification_refuses_an_empty_draw_list():
    with pytest.raises(ValueError, match="at least one draw"):
        verify.verify(outlined(), MATRIX, [], verify.Cases([], ("a",)), pathlib.Path("."))


def test_a_wrong_candidate_fails_through_the_whole_verification(tmp_path):
    program, cases = program_and_cases(tmp_path, "scale", SCALE_MANIFEST)
    (scope,) = program.scopes
    good = build(scope, Candidate("c", "gcc"), MATRIX, tmp_path / "good", {})
    wrong = handwritten_archive(tmp_path, scope, "for (int64_t i = 0; i < N; ++i) out[i] = 3.0 * a[i];")
    bad = dataclasses.replace(good, name="wrong", archive=wrong, object_hash="wrong")

    sut = verify.verify(program, MATRIX, [ScopeReport(scope, (good, bad))], cases, tmp_path / "out")

    assert sut.verdicts[scope.symbol]["wrong"].status == "fail"


def candidate_writing(tmp: pathlib.Path, scope: scopes.Scope, body: str, fp_level: str = "") -> ScopeReport:
    """``scope``'s default build beside a hand-written candidate ``wrong`` at ``fp_level``."""
    good = build(scope, Candidate("c", "gcc"), MATRIX, tmp / "good", {})
    candidate = Candidate("c", "gcc", fp_level=fp_level)
    written = dataclasses.replace(
        good, name="hand", candidate=candidate, archive=handwritten_archive(tmp, scope, body), object_hash="hand"
    )
    return ScopeReport(scope, (good, written))


#: Writes the graded prefix right and the rest of ``out`` wrong.
WRONG_TAIL = "for (int64_t i = 0; i < N; ++i) out[i] = i < N / 2 ? 2.0 * a[i] : -1.0;"


def test_a_candidate_is_only_judged_on_the_prefix_the_manifest_grades(tmp_path):
    """``output_extent``: past ``count`` the answer is untouched buffer, so a candidate may leave anything there."""
    program, cases = program_and_cases(tmp_path, "scale_prefix", PREFIX_MANIFEST)
    (scope,) = program.scopes
    report = candidate_writing(tmp_path, scope, WRONG_TAIL)

    sut = verify.verify(program, MATRIX, [report], cases, tmp_path / "out")

    assert sut.verdicts[scope.symbol]["hand"].status == "exact"


def test_a_wrong_value_inside_the_graded_prefix_still_fails(tmp_path):
    program, cases = program_and_cases(tmp_path, "scale_prefix", PREFIX_MANIFEST)
    (scope,) = program.scopes
    wrong = "for (int64_t i = 0; i < N; ++i) out[i] = i == N / 2 - 1 ? -1.0 : 2.0 * a[i];"
    report = candidate_writing(tmp_path, scope, wrong)

    sut = verify.verify(program, MATRIX, [report], cases, tmp_path / "out")

    assert sut.verdicts[scope.symbol]["hand"].status == "fail"


def test_the_grading_of_a_manifest_reaches_the_timing_stage(tmp_path):
    """The sizes a scope is timed at are checked again: the same prefix is graded there."""
    program, cases = program_and_cases(tmp_path, "scale_prefix", PREFIX_MANIFEST)
    manifest = inputs.load(tmp_path / "scale_prefix.yaml", f"{REDUCTIONS}:scale_prefix")
    (scope,) = program.scopes
    report = candidate_writing(tmp_path, scope, WRONG_TAIL)
    verification = verify.verify(program, MATRIX, [report], cases, tmp_path / "out")

    sut = timing.time_scope(link.Linker(program, MATRIX, tmp_path / "out"), report, verification, manifest)

    assert sut.screen["hand"].verdict.status == "exact"


def test_a_band_candidate_may_miss_the_fraction_of_elements_the_manifest_forgives(tmp_path):
    forgiving = SCALE_MANIFEST.replace("level: 1", "level: 1\nmismatch_fraction: 0.02")
    program, cases = program_and_cases(tmp_path, "scale", forgiving)
    (scope,) = program.scopes
    flipped = "for (int64_t i = 0; i < N; ++i) out[i] = 2.0 * a[i];\nout[0] += 1.0;"
    report = candidate_writing(tmp_path, scope, flipped, fp_level="reassoc")

    sut = verify.verify(program, MATRIX, [report], cases, tmp_path / "out")

    assert sut.verdicts[scope.symbol]["hand"].status == "pass"


def test_a_candidate_past_the_forgiven_fraction_fails(tmp_path):
    forgiving = SCALE_MANIFEST.replace("level: 1", "level: 1\nmismatch_fraction: 0.02")
    program, cases = program_and_cases(tmp_path, "scale", forgiving)
    (scope,) = program.scopes
    wrong = "for (int64_t i = 0; i < N; ++i) out[i] = i % 8 ? 2.0 * a[i] : 0.0;"
    report = candidate_writing(tmp_path, scope, wrong, fp_level="reassoc")

    sut = verify.verify(program, MATRIX, [report], cases, tmp_path / "out")

    assert sut.verdicts[scope.symbol]["hand"].status == "fail"


def test_an_exact_candidate_gets_no_forgiven_fraction(tmp_path):
    """Bit-identity is the strict level's promise, stronger than what the judge grades."""
    forgiving = SCALE_MANIFEST.replace("level: 1", "level: 1\nmismatch_fraction: 0.02")
    program, cases = program_and_cases(tmp_path, "scale", forgiving)
    (scope,) = program.scopes
    flipped = "for (int64_t i = 0; i < N; ++i) out[i] = 2.0 * a[i];\nout[0] += 1.0;"
    report = candidate_writing(tmp_path, scope, flipped)

    sut = verify.verify(program, MATRIX, [report], cases, tmp_path / "out")

    assert sut.verdicts[scope.symbol]["hand"].status == "fail"


#: Every corpus kernel whose manifest sets ``conditioning_rtol`` or ``conditioning_atol``.
CONDITIONED_KERNELS = (
    "bdf_newton_krylov",
    "bicgstab",
    "contour_integral",
    "cp2k_density_matrix_trs4",
    "jfnk_bratu",
    "mixed_precision_ir",
    "rk45_ensemble",
)


def judged(grading: inputs.Grading, level: str, expected: np.ndarray, value: np.ndarray) -> verify.Verdict:
    return verify.judge(level, verify.Reference([{"x": expected}], frozenset(), grading), [[{"x": value}]], [1])


@pytest.mark.parametrize("kernel", CONDITIONED_KERNELS)
def test_a_conditioned_corpus_kernel_is_graded_at_the_tolerances_of_the_judge(kernel):
    spec = BenchSpec.load(kernel)
    sut = inputs.grading(inputs.load(paths.BENCHMARKS / spec.relative_path / f"{spec.module_name}.yaml"))
    rtol, atol = kernel_tolerances(spec, "float64")
    expected = np.array([1.0, 0.0])

    inside = judged(sut, "band", expected, np.array([1.0 + 0.9 * rtol, 0.9 * atol]))
    off_relative = judged(sut, "band", expected, np.array([1.0 + 2.0 * (rtol + atol), 0.0]))
    off_absolute = judged(sut, "band", expected, np.array([1.0, 2.0 * atol]))

    assert inside.status == "pass"
    assert (off_relative.status, off_absolute.status) == ("fail", "fail")


def test_a_conditioning_floor_under_the_band_of_the_precision_leaves_that_band():
    """``float32``'s band is wider than this floor, as ``kernel_tolerances`` takes the larger of the two."""
    expected = np.ones(4, dtype=np.float32)

    sut = judged(inputs.Grading(conditioning_rtol=1e-7), "band", expected, expected * (1.0 + 1e-4))

    assert sut.status == "pass"


def test_an_exact_candidate_gets_no_conditioning_band():
    """Bit-identity is the strict level's promise, stronger than what the judge grades."""
    expected = np.ones(4)

    sut = judged(inputs.Grading(conditioning_rtol=1e-3, conditioning_atol=1e-3), "exact", expected, expected + 1e-9)

    assert sut.status == "fail"


def reduction_reports(tmp: pathlib.Path, program: scopes.Program, report: ScopeReport) -> list[ScopeReport]:
    """``report`` of ``program``'s reducing scope after the default build of the scope that sets up its output."""
    return [
        ScopeReport(program.scopes[0], (build(program.scopes[0], Candidate("c", "gcc"), MATRIX, tmp / "i", {}),)),
        report,
    ]


#: A candidate of ``row_sum`` that sums every row and scales it by ``factor``.
ROW_SUM = (
    "for (int64_t i = 0; i < M; ++i) {{ for (int64_t j = 0; j < N; ++j) out[i] += a[i * N + j]; out[i] *= {factor}; }}"
)


@pytest.mark.parametrize(("factor", "status"), [("1.0 + 1e-7", "pass"), ("1.0 + 1e-5", "fail")])
def test_a_reduction_is_graded_inside_the_conditioned_band_at_every_team_size(tmp_path, factor, status):
    conditioned = ROW_SUM_MANIFEST.replace("level: 1", "level: 1\nconditioning_rtol: 1.0e-6")
    program, cases = program_and_cases(tmp_path, "row_sum", conditioned)
    report = candidate_writing(tmp_path, program.scopes[1], ROW_SUM.format(factor=factor), fp_level="reassoc")

    sut = verify.verify(program, MATRIX, reduction_reports(tmp_path, program, report), cases, tmp_path / "out")

    assert sut.verdicts[program.scopes[1].symbol]["hand"].status == status


def test_a_reduction_keeps_the_forgiven_fraction_at_every_team_size(tmp_path):
    forgiving = ROW_SUM_MANIFEST.replace("level: 1", "level: 1\nmismatch_fraction: 0.1")
    program, cases = program_and_cases(tmp_path, "row_sum", forgiving)
    flipped = ROW_SUM.format(factor="1.0") + "\nout[0] += 1.0;"
    report = candidate_writing(tmp_path, program.scopes[1], flipped, fp_level="reassoc")

    sut = verify.verify(program, MATRIX, reduction_reports(tmp_path, program, report), cases, tmp_path / "out")

    assert sut.verdicts[program.scopes[1].symbol]["hand"].status == "pass"


def test_an_integer_output_may_miss_the_forgiven_fraction_like_any_other():
    """mandelbrot2's escape counts are integers: the judge forgives its boundary pixels there too."""
    expected = np.arange(100, dtype=np.int64)
    flipped = expected.copy()
    flipped[0] += 1

    sut = verify.compare("band", expected, flipped, 1, "int64", inputs.Grading(mismatch_fraction=0.01))

    assert sut.status == "pass"


def test_an_integer_output_past_the_forgiven_fraction_fails():
    expected = np.arange(100, dtype=np.int64)

    sut = verify.compare("band", expected, expected + 1, 1, "int64", inputs.Grading(mismatch_fraction=0.01))

    assert sut.status == "fail"


def test_a_scalar_output_needs_no_extent():
    reference = verify.Reference([{"s": np.array(2.0)}], frozenset())

    sut = verify.judge("exact", reference, [[{"s": np.array(2.0)}]], [1])

    assert sut.status == "exact"


def test_an_ungradeable_verdict_is_not_correct():
    assert not verify.Verdict("ungradeable").ok


def test_a_nondeterministic_output_is_compared_by_band_even_at_exact():
    ref = verify.Reference([{"x": np.array([1.0])}], frozenset({"x"}))

    sut = verify.judge("exact", ref, [[{"x": np.array([1.0 + 1e-15])}]], [1])

    assert sut.ok


def test_an_output_that_changes_between_runs_is_marked_nondeterministic():
    cases = verify.Cases([inputs.Draw({}, {})], ("x",))
    runs: list[list[verify.Outcome]] = [[[{"x": np.array([1.0])}], [{"x": np.array([2.0])}], [{"x": np.array([1.0])}]]]

    sut = verify.reference_from(cases, runs)

    assert sut.nondeterministic == frozenset({"x"})


def test_an_output_that_changes_between_the_calls_of_one_child_is_marked_nondeterministic():
    cases = verify.Cases([inputs.Draw({}, {})], ("x",))
    runs: list[list[verify.Outcome]] = [[[{"x": np.array([1.0])}, {"x": np.array([2.0])}]]]

    sut = verify.reference_from(cases, runs)

    assert sut.nondeterministic == frozenset({"x"})


def team_runs(values: dict[int, dict[str, np.ndarray]]) -> list[list[verify.Outcome]]:
    """Three identical reference runs at each team size of ``values``, in that order."""
    return [[[outputs] for _ in range(verify.REFERENCE_RUNS)] for outputs in values.values()]


def test_a_value_that_follows_the_team_size_is_nondeterministic_though_each_team_reproduces_it():
    cases = verify.at_team_sizes(outlined(), verify.Cases([inputs.Draw({}, {})], ("sum", "scaled")))
    runs = team_runs(
        {team: {"sum": np.array([team * 1.0]), "scaled": np.array([2.0])} for team in verify.REDUCTION_TEAMS}
    )

    sut = verify.reference_from(cases, runs)

    assert sut.nondeterministic == frozenset({"sum"})


def test_two_draws_differing_from_each_other_are_no_nondeterminism():
    draws = [inputs.Draw({}, {}), inputs.Draw({}, {})]
    cases = verify.at_team_sizes(outlined(), verify.Cases(draws, ("x",)))
    per_draw = [{"x": np.array([float(draw)])} for draw in range(len(draws)) for _ in verify.REDUCTION_TEAMS]

    sut = verify.reference_from(cases, [[[outputs]] for outputs in per_draw])

    assert sut.nondeterministic == frozenset()


def test_a_team_size_changing_only_the_ungraded_tail_leaves_an_output_exact():
    grading = inputs.Grading({"x": "count"})
    cases = verify.at_team_sizes(outlined(), verify.Cases([inputs.Draw({}, {})], ("x", "count"), grading))
    count = np.array([1], dtype=np.int64)
    runs = team_runs({team: {"x": np.array([1.0, team * 1.0]), "count": count} for team in verify.REDUCTION_TEAMS})

    sut = verify.reference_from(cases, runs)

    assert sut.nondeterministic == frozenset()


def row_sum_reference(tmp: pathlib.Path, program: scopes.Program, chunked: str, body: str) -> list[ScopeReport]:
    """``row_sum``'s reducing scope with the reference ``chunked`` and the strict candidate ``hand`` writing ``body``."""
    scope = program.scopes[1]
    report = candidate_writing(tmp, scope, body)
    good, hand = report.builds
    (tmp / "reference").mkdir()
    reference = dataclasses.replace(good, archive=handwritten_archive(tmp / "reference", scope, chunked))
    return reduction_reports(tmp, program, ScopeReport(scope, (reference, hand)))


#: ``row_sum`` the way a parallel reduction rounds, with the order fixed: one partial sum per chunk, added up last.
CHUNKED = """for (int64_t i = 0; i < M; ++i) {{
    int64_t chunks = {chunks};
    for (int64_t c = 0; c < chunks; ++c) {{
        double partial = 0.0;
        for (int64_t j = c * N / chunks; j < (c + 1) * N / chunks; ++j) partial += a[i * N + j];
        out[i] += partial;
    }}
}}"""
TEAM_CHUNKS = CHUNKED.format(chunks="omp_get_max_threads()")


@pytest.mark.gcc
def test_a_correct_sum_passes_a_reference_that_reproduces_at_each_team_but_follows_the_team_size(tmp_path):
    """The reference never shows two values at one size, so nothing but the sizes tells its rounding is thread order."""
    program, cases = program_and_cases(tmp_path, "row_sum", ROW_SUM_MANIFEST)
    reports = row_sum_reference(tmp_path, program, TEAM_CHUNKS, ROW_SUM.format(factor="1.0"))

    sut = verify.verify(program, MATRIX, reports, cases, tmp_path / "out")

    assert sut.nondeterministic == frozenset({"out"})
    assert sut.verdicts[program.scopes[1].symbol]["hand"].status == "pass"


@pytest.mark.gcc
def test_a_serial_sum_passes_a_reference_that_differs_from_it_only_on_one_thread(tmp_path):
    """Two chunks at every size above 1: only the one-thread run has the left-to-right sum a serial build computes."""
    program, cases = program_and_cases(tmp_path, "row_sum", ROW_SUM_MANIFEST)
    two_chunks = CHUNKED.format(chunks="omp_get_max_threads() > 1 ? 2 : 1")
    reports = row_sum_reference(tmp_path, program, two_chunks, ROW_SUM.format(factor="1.0"))

    sut = verify.verify(program, MATRIX, reports, cases, tmp_path / "out")

    assert sut.verdicts[program.scopes[1].symbol]["hand"].status == "pass"


@pytest.mark.gcc
@pytest.mark.parametrize(
    "wrong",
    [
        "for (int64_t i = 0; i < M; ++i) for (int64_t j = 1; j < N; ++j) out[i] += a[i * N + j];",
        ROW_SUM.format(factor="1.0 + 1e-8"),
    ],
    ids=["a lost term", "ten times the band"],
)
def test_a_wrong_sum_fails_against_a_reference_whose_value_follows_the_team_size(tmp_path, wrong):
    program, cases = program_and_cases(tmp_path, "row_sum", ROW_SUM_MANIFEST)
    reports = row_sum_reference(tmp_path, program, TEAM_CHUNKS, wrong)

    sut = verify.verify(program, MATRIX, reports, cases, tmp_path / "out")

    assert sut.nondeterministic == frozenset({"out"})
    assert sut.verdicts[program.scopes[1].symbol]["hand"].status == "fail"


@pytest.mark.gcc
def test_a_parallel_sum_is_compared_by_band_and_the_map_beside_it_stays_exact(tmp_path):
    program = outlined()
    manifest = inputs.load(EXAMPLE.with_suffix(".yaml"), f"{EXAMPLE}:two_scopes")
    cases = api.test_cases(program, manifest)
    assert cases is not None
    reports = [
        ScopeReport(s, (build(s, Candidate("c", "gcc"), MATRIX, tmp_path / s.symbol, {}),)) for s in program.scopes
    ]

    sut = verify.verify(program, MATRIX, reports, cases, tmp_path / "out")

    assert sut.nondeterministic == frozenset({"total"})


@pytest.mark.gcc
def test_a_rounding_difference_fails_a_reduction_whose_reference_reproduces_at_every_team_size(tmp_path):
    """Every row is one thread's sum, whatever the team: this reference is exact, so a strict candidate must match."""
    program, cases = program_and_cases(tmp_path, "row_sum", ROW_SUM_MANIFEST)
    backwards = "for (int64_t i = 0; i < M; ++i) for (int64_t j = N - 1; j >= 0; --j) out[i] += a[i * N + j];"
    report = candidate_writing(tmp_path, program.scopes[1], backwards)

    sut = verify.verify(program, MATRIX, reduction_reports(tmp_path, program, report), cases, tmp_path / "out")

    assert sut.nondeterministic == frozenset()
    assert sut.verdicts[program.scopes[1].symbol]["hand"].status == "fail"


def test_one_wrong_result_among_the_calls_of_a_child_fails_the_candidate():
    ref = verify.Reference([{"x": np.array([1.0])}], frozenset())
    distinct: list[verify.Outcome] = [[{"x": np.array([1.0])}, {"x": np.array([2.0])}]]

    sut = verify.judge("exact", ref, distinct, [1])

    assert sut.status == "fail"


def test_a_build_wrong_only_after_its_first_call_fails_verification(tmp_path):
    """The shape of a reduction that loses updates only once its OpenMP team is awake."""
    program, cases = program_and_cases(tmp_path, "scale", SCALE_MANIFEST)
    (scope,) = program.scopes
    good = build(scope, Candidate("c", "gcc"), MATRIX, tmp_path / "good", {})
    body = "static int calls; double f = ++calls > 1 ? 3.0 : 2.0; for (int64_t i = 0; i < N; ++i) out[i] = f * a[i];"
    wrong = handwritten_archive(tmp_path, scope, body)
    bad = dataclasses.replace(good, name="wrong", archive=wrong, object_hash="wrong")

    sut = verify.verify(program, MATRIX, [ScopeReport(scope, (good, bad))], cases, tmp_path / "out")

    assert sut.verdicts[scope.symbol]["wrong"].status == "fail"


@pytest.mark.parametrize("team", [2, 3, 5])
def test_a_reduction_wrong_at_a_single_team_size_fails_verification(tmp_path, team):
    program, cases = program_and_cases(tmp_path, "row_sum", ROW_SUM_MANIFEST)
    init, reduce_scope = program.scopes
    wrong_factor = f"double f = omp_get_max_threads() == {team} ? 3.0 : 1.0;"
    body = "for (int64_t j = 0; j < N; ++j) out[i] += a[i * N + j]; out[i] *= f;"
    wrong = handwritten_archive(tmp_path, reduce_scope, f"{wrong_factor} for (int64_t i = 0; i < M; ++i) {{ {body} }}")
    good = build(reduce_scope, Candidate("c", "gcc"), MATRIX, tmp_path / "r", {})
    bad = dataclasses.replace(good, name="wrong", archive=wrong, object_hash="wrong")
    reports = [
        ScopeReport(init, (build(init, Candidate("c", "gcc"), MATRIX, tmp_path / "i", {}),)),
        ScopeReport(reduce_scope, (good, bad)),
    ]

    sut = verify.verify(program, MATRIX, reports, cases, tmp_path / "out")

    assert sut.verdicts[reduce_scope.symbol]["wrong"].status == "fail"


def test_a_correct_reduction_stays_correct_at_every_team_size(tmp_path):
    program, cases = program_and_cases(tmp_path, "row_sum", ROW_SUM_MANIFEST)
    init, reduce_scope = program.scopes
    body = "for (int64_t j = 0; j < N; ++j) out[i] += a[i * N + j];"
    right = handwritten_archive(tmp_path, reduce_scope, f"for (int64_t i = 0; i < M; ++i) {{ {body} }}")
    good = build(reduce_scope, Candidate("c", "gcc"), MATRIX, tmp_path / "r", {})
    hand = dataclasses.replace(good, name="hand", archive=right, object_hash="hand")
    reports = [
        ScopeReport(init, (build(init, Candidate("c", "gcc"), MATRIX, tmp_path / "i", {}),)),
        ScopeReport(reduce_scope, (good, hand)),
    ]

    sut = verify.verify(program, MATRIX, reports, cases, tmp_path / "out")

    assert sut.verdicts[reduce_scope.symbol]["hand"].ok


def test_a_child_starts_under_any_data_limit_of_its_parent():
    """``limit_memory`` runs first in every child: with no limit set at all it must still set one."""
    assert verify.in_child(int, (), machine.core_slots()[0], 1.0) == 0
