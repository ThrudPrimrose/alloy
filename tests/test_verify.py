# Copyright 2026 ETH Zurich and the Alloy authors.
import pathlib

import numpy as np
from helpers import MATRIX, ROW_SUM_MANIFEST, SCALE_MANIFEST, handwritten_archive, program_and_cases

from alloy import machine
from alloy.backend.build import build
from alloy.backend.candidates import Candidate
from alloy.backend.sweep import RegionReport
from alloy.evaluate import link, verify
from alloy.frontend import inputs, regions


def reference_run(tmp: pathlib.Path, program: regions.Program, cases: verify.Cases) -> tuple:
    (region,) = program.regions
    ref = build(region, Candidate("c", "gcc"), MATRIX, tmp / "ref", {})
    assert ref.archive is not None
    linker = link.Linker(program, MATRIX, tmp / "out")
    compiled = linker.compile({region.symbol: ref.archive}, "reference")
    return region, ref, linker, verify.reference_outputs(compiled, cases)


def test_fuzzed_draws_stay_inside_the_manifest_range_and_shape_every_input(tmp_path):
    path = tmp_path / "scale.yaml"
    path.write_text(SCALE_MANIFEST)

    sut = [inputs.draw(inputs.load(path, "scale"), i) for i in range(3)]

    assert all(64 <= d.sizes["N"] <= 512 for d in sut)
    assert all(d.values["a"].shape == (d.sizes["N"],) for d in sut)


def test_the_reference_program_reproduces_itself_bit_for_bit(tmp_path):
    program, cases = program_and_cases(tmp_path, "scale", SCALE_MANIFEST)
    region, ref, linker, refs = reference_run(tmp_path, program, cases)
    again = linker.compile({region.symbol: ref.archive}, "again")

    sut = verify.judge("exact", refs, [verify.run(again, d, cases.outputs) for d in cases.draws], [1, 1])

    assert sut.status == "exact"
    assert np.array_equal(refs.outputs[0]["out"], 2.0 * cases.draws[0].values["a"])
    assert refs.nondeterministic == frozenset()


def test_a_wrong_archive_at_the_same_fixed_path_fails_so_no_stale_binary_is_reused(tmp_path):
    program, cases = program_and_cases(tmp_path, "scale", SCALE_MANIFEST)
    region, _, linker, refs = reference_run(tmp_path, program, cases)
    wrong = handwritten_archive(tmp_path, region, "for (int64_t i = 0; i < N; ++i) out[i] = 3.0 * a[i];")
    compiled = linker.compile({region.symbol: wrong}, "wrong")

    sut = verify.judge("band", refs, [verify.run(compiled, d, cases.outputs) for d in cases.draws], [1, 1])

    assert sut.status == "fail"


def test_a_crashing_candidate_is_a_verdict_not_a_crash_of_the_sweep(tmp_path):
    program, cases = program_and_cases(tmp_path, "scale", SCALE_MANIFEST)
    region, _, linker, refs = reference_run(tmp_path, program, cases)
    compiled = linker.compile({region.symbol: handwritten_archive(tmp_path, region, "abort();")}, "abort")

    sut = verify.judge("band", refs, [verify.run(compiled, d, cases.outputs) for d in cases.draws], [1, 1])

    assert sut.status == "crashed"


def test_a_child_runs_on_its_own_cores_whatever_the_parent_set_after_the_fork_server_started(tmp_path, monkeypatch):
    program, cases = program_and_cases(tmp_path, "scale", SCALE_MANIFEST)
    region, _, linker, _ = reference_run(tmp_path, program, cases)  # the fork server is running from here on
    probe = "out[0] = omp_get_max_threads(); out[1] = omp_get_num_places();"
    compiled = linker.compile({region.symbol: handwritten_archive(tmp_path, region, probe)}, "probe")
    monkeypatch.setenv("OMP_NUM_THREADS", "1")

    sut = verify.run(compiled, cases.draws[0], cases.outputs)

    assert not isinstance(sut, str)
    threads, places = sut["out"][:2]
    assert threads == places >= 2


def test_a_reassociated_reduction_passes_the_accumulation_band(tmp_path):
    program, cases = program_and_cases(tmp_path, "row_sum", ROW_SUM_MANIFEST)
    init, reduce_region = program.regions
    builds = [
        RegionReport(init, (build(init, Candidate("c", "gcc"), MATRIX, tmp_path / "i", {}),)),
        RegionReport(
            reduce_region,
            (
                build(reduce_region, Candidate("c", "gcc"), MATRIX, tmp_path / "r", {}),
                build(reduce_region, Candidate("c", "gcc", fp_level="reassoc"), MATRIX, tmp_path / "r2", {}),
            ),
        ),
    ]

    sut = verify.verify(program, MATRIX, builds, cases, tmp_path / "out")

    reassoc = builds[1].builds[1].name
    assert sut.verdicts[reduce_region.symbol][reassoc].ok


def test_a_floor_that_eats_the_whole_band_is_ungradeable_not_a_pass():
    ref = np.linspace(1.0, 2.0, 16)

    sut = verify.compare("band", ref, ref.copy(), 10**20, "float64")

    assert sut.status == "ungradeable"


def reserve(count: int) -> int:
    return np.empty(count).nbytes  # reserves without touching, so even an uncapped child stays harmless


def test_a_child_asking_for_more_memory_than_the_machine_has_is_a_crash_not_an_exhausted_machine():
    sut = verify.in_child(reserve, (2 * machine.available_memory() // 8,), machine.core_slots()[0])

    assert sut == "exit code 1"
