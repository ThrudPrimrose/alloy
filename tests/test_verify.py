# Copyright 2026 ETH Zurich and the Alloy authors.
import pathlib

import numpy as np
import pytest

from alloy import machine
from alloy.backend.build import build
from alloy.backend.candidates import Candidate
from alloy.backend.sweep import ScopeReport
from alloy.evaluate import link, verify
from alloy.frontend import inputs, scopes
from helpers import (
    MATRIX,
    REDUCTIONS,
    ROW_SUM_MANIFEST,
    SCALE_MANIFEST,
    handwritten_archive,
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
    threads, places = sut["out"][:2]
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


def test_a_floor_that_eats_the_whole_band_is_ungradeable_not_a_pass():
    ref = np.linspace(1.0, 2.0, 16)

    sut = verify.compare("band", ref, ref.copy(), 10**20, "float64")

    assert sut.status == "ungradeable"


def test_a_complex_output_is_judged_under_the_band_of_its_component_precision():
    expected = np.linspace(1.0, 2.0, 16) * (1 + 1j)
    reference = verify.Reference([{"Sigma": expected}], frozenset())

    sut = verify.judge("band", reference, [{"Sigma": expected * (1 + 1e-15)}], [1])

    assert sut.status == "pass"


def reserve(count: int) -> int:
    return np.empty(count).nbytes  # reserves without touching, so even an uncapped child stays harmless


def test_a_child_asking_for_more_memory_than_the_machine_has_is_a_crash_not_an_exhausted_machine():
    sut = verify.in_child(reserve, (2 * machine.available_memory() // 8,), machine.core_slots()[0], verify.slot_share())

    assert sut == "exit code 1"


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


def test_the_largest_array_is_counted_at_the_largest_preset(tmp_path):
    program, cases = program_and_cases(tmp_path, "row_sum", ROW_SUM_MANIFEST)
    manifest = write_manifest(tmp_path, "row_sum", ROW_SUM_MANIFEST)

    assert inputs.largest_array(manifest, program.original) == 64 * 512


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
    value = verify.compare("band", np.ones(8), np.ones(8), 8, "int64")

    assert same.status == "exact" and off.status == "fail" and value.status == "pass"
