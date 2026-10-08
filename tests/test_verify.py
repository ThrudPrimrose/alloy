# Copyright 2026 ETH Zurich and the Alloy authors.
import pathlib
import subprocess

import numpy as np
from helpers import MATRIX, REDUCTIONS

from alloy import inputs, regions, verify
from alloy.build import build
from alloy.candidates import Candidate
from alloy.cli import load_program
from alloy.sweep import RegionReport

SCALE_MANIFEST = """name: scale
level: 1
parameters:
  S:
    N: 512
  fuzzed:
    N: [64, 512]
init:
  arrays:
    a: (N,)
    out: (N,)
input_args: [a, out]
output_args: [out]
"""
ROW_SUM_MANIFEST = """name: row sum
level: 1
parameters:
  S:
    M: 64
    N: 512
  fuzzed:
    M: [16, 64]
    N: [256, 1024]
init:
  arrays:
    a: (M, N)
    out: (M,)
input_args: [a, out]
output_args: [out]
"""


def program_and_cases(tmp: pathlib.Path, kernel: str, manifest_text: str) -> tuple[regions.Program, verify.Cases]:
    path = tmp / f"{kernel}.yaml"
    path.write_text(manifest_text)
    manifest = inputs.load(path, kernel)
    program = regions.outline(load_program(f"{REDUCTIONS}:{kernel}"), MATRIX.libm_calls)
    return program, verify.Cases([inputs.draw(manifest, i) for i in range(2)], manifest.outputs)


def handwritten_archive(tmp: pathlib.Path, region: regions.Region, body: str) -> pathlib.Path:
    """``lib<symbol>.a`` defining the region's entry with ``body``, outside every candidate."""
    source, obj, archive = tmp / "hand.c", tmp / "hand.o", tmp / "libhand.a"
    signature = region.signature.replace("__restrict__", "restrict")
    source.write_text(f"#include <stdint.h>\n#include <stdlib.h>\nvoid {region.symbol}({signature}) {{ {body} }}\n")
    subprocess.run(["gcc", "-O2", "-fPIC", "-c", str(source), "-o", str(obj)], check=True)
    subprocess.run(["ar", "rcs", str(archive), str(obj)], check=True)
    return archive


def reference_run(tmp: pathlib.Path, program: regions.Program, cases: verify.Cases) -> tuple:
    (region,) = program.regions
    ref = build(region, Candidate("c", "gcc"), MATRIX, tmp / "ref", {})
    assert ref.archive is not None
    linker = verify.Linker(program, MATRIX, tmp / "out")
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
