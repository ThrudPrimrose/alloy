# Copyright 2026 ETH Zurich and the Alloy authors.
import dataclasses
import json
import math
import pathlib
import re
from collections.abc import Callable

import pytest
from pydantic import ValidationError

from alloy import report
from alloy.backend import sweep
from alloy.backend.build import Build, Remarks, build, write_source
from alloy.backend.candidates import Candidate
from alloy.evaluate.timing import Measured, ProgramTiming, RegionTiming, Timings
from alloy.evaluate.verify import Verdict
from alloy.records import dumped_json
from helpers import MATRIX, outlined


def test_the_report_lists_every_candidate_of_every_region(tmp_path):
    program = outlined()
    reports = [
        sweep.RegionReport(r, (build(r, Candidate("c", "gcc"), MATRIX, tmp_path / r.symbol, {}),))
        for r in program.regions
    ]

    report.write(reports, MATRIX, tmp_path)

    data = json.loads((tmp_path / "report.json").read_text())
    assert [r["symbol"] for r in data["regions"]] == [r.symbol for r in program.regions]
    assert all(len(r["candidates"]) == 1 and r["candidates"][0]["archive"] for r in data["regions"])
    assert (tmp_path / "report.md").read_text().count("## ") == len(program.regions)
    assert (tmp_path / "configuration_matrix.toml").read_bytes() == MATRIX.path.read_bytes()


def test_the_runtime_matrix_puts_each_candidate_at_its_variant_and_build_config(tmp_path):
    region = outlined().regions[0]
    renders: dict = {}
    candidates = [
        Candidate("c", "gcc"),
        Candidate("c", "gcc", isa="avx2"),
        Candidate("c", "gcc", knobs=(("loop_access_form", "ptr_increment"),)),
    ]
    builds = []
    for c in candidates:
        source = write_source(region, c, MATRIX, tmp_path, renders)
        builds.append(Build(c, c.name(MATRIX), {}, source, None, (), "", Remarks(0, ())))
    passed = Verdict(status="pass", error=0.0, detail="")
    timed = Measured(median=2e-3, low=2e-3, high=2e-3, verdict=passed)
    timing = RegionTiming(
        screen={"reference": timed, builds[1].name: dataclasses.replace(timed, median=1e-3)},
        final={"reference": timed, builds[1].name: timed},
        winner="reference",
        screen_sizes={},
        final_sizes={},
    )

    sut = report.runtime_matrix(sweep.RegionReport(region, tuple(builds)), timing, MATRIX)

    assert sut[2:5] == [
        "| variant | gcc_strict_default_none_native | gcc_strict_default_none_avx2 |",
        "|---|---|---|",
        "| v0 | 2.000 (1.00x) | 1.000 (2.00x)* |",
    ]
    assert sut[5] == "| v1 | - | - |"


def a_report() -> report.Report:
    """A timed report of one region with a verified and a failed candidate; the failed arm's timing is NaN."""
    passed = Verdict(status="pass", error=2.5e-16, detail="")
    failed = Verdict(status="fail", error=math.inf, detail="out: not bit-identical to the reference")
    measured = Measured(median=1e-3, low=9e-4, high=1.1e-3, verdict=passed)
    unmeasured = Measured(median=math.nan, low=math.nan, high=math.nan, verdict=failed)
    candidate = report.CandidateRecord(
        name="c_gcc_int64_strict_default_none",
        change="default",
        variant="v0",
        config="gcc_strict_default_none_native",
        flags=("-std=c23", "-O3"),
        codegen_params={"index_type": "int64_t"},
        source=pathlib.Path("/out/regions/r0/c.c"),
        archive=pathlib.Path("/out/regions/r0/libc.a"),
        object_hash="0f",
        duplicate_of=None,
        vectorized_loops=2,
        missed=("loop not vectorized",),
        error=None,
        verdict=report.VerdictRecord(status="pass", max_rel_error=2.5e-16, detail=None),
    )
    region = report.RegionRecord(
        symbol="r0",
        signature="double* a, int64_t N",
        abi_order=("a", "N"),
        calls_libm=False,
        has_reduction=True,
        accumulation_length="N",
        candidates=(candidate,),
    )
    region_timing = RegionTiming(
        screen={"reference": measured, "fast": unmeasured},
        final={"reference": measured},
        winner="reference",
        screen_sizes={"N": 4096, "alpha": 1.5, "transpose": True},
        final_sizes={"N": 8192, "alpha": 1.5, "transpose": True},
    )
    program = ProgramTiming(arms={"dace_default": measured, "alloy_full": measured}, sizes={"N": 8192})
    return report.Report(
        nondeterministic_outputs=("out",),
        regions=(region,),
        timing=Timings(regions={"r0": region_timing}, program=program),
    )


def test_a_written_report_loads_back_unchanged_including_nan_timings(tmp_path):
    """A failed arm is timed as NaN; JSON without NaN constants would read it back as null and refuse it."""
    path = tmp_path / "report.json"
    text = dumped_json(a_report())
    path.write_text(text)

    sut = report.load(path)

    assert dumped_json(sut) == text
    assert sut.timing is not None
    assert math.isnan(sut.timing.regions["r0"].screen["fast"].median)


def test_a_preset_parameter_that_is_not_an_int_keeps_its_type_through_the_report(tmp_path):
    """Manifest presets carry floats and flags beside sizes; a bool read back as 1 changes the kernel's inputs."""
    path = tmp_path / "report.json"
    path.write_text(dumped_json(a_report()))

    sut = report.load(path)

    assert sut.timing is not None
    assert sut.timing.regions["r0"].final_sizes == {"N": 8192, "alpha": 1.5, "transpose": True}
    assert type(sut.timing.regions["r0"].final_sizes["transpose"]) is bool


def edited(tmp_path: pathlib.Path, edit: Callable[[dict], None]) -> pathlib.Path:
    data = json.loads(dumped_json(a_report()))
    edit(data)
    path = tmp_path / "report.json"
    path.write_text(json.dumps(data))
    return path


@pytest.mark.parametrize(
    ("edit", "error"),
    [
        (lambda d: d.update(typo=1), "typo: Unexpected keyword argument, got 1"),
        (
            lambda d: d["regions"][0]["candidates"][0].update(vectorized_loops="2"),
            "regions.0.candidates.0.vectorized_loops: Input should be a valid integer, got '2'",
        ),
        (
            lambda d: d["regions"][0].update(calls_libm=0),
            "regions.0.calls_libm: Input should be a valid boolean, got 0",
        ),
        (
            lambda d: d["timing"]["program"]["arms"]["alloy_full"]["verdict"].update(status="ok"),
            "timing.program.arms.alloy_full.verdict.status: Input should be 'exact', 'pass', 'fail', 'ungradeable', "
            "'crashed' or 'link_error', got 'ok'",
        ),
        (lambda d: d["regions"][0].pop("symbol"), "regions.0.symbol: Field required"),
    ],
)
def test_a_report_with_an_unknown_key_or_a_wrong_type_is_refused_naming_the_file(tmp_path, edit, error):
    path = edited(tmp_path, edit)

    with pytest.raises(ValueError, match=re.escape(error)) as raised:
        report.load(path)

    assert str(raised.value).startswith(f"{path}: not a valid Report:"), raised.value


def test_a_verdict_with_an_undeclared_status_is_refused():
    with pytest.raises(ValidationError, match="status"):
        Verdict(status="passed")  # pyright: ignore[reportArgumentType] -- the undeclared status is the point


def test_the_written_report_json_validates_as_a_report(tmp_path):
    program = outlined()
    failed = Build(
        candidate=Candidate("c", "gcc"),
        name="c_gcc",
        codegen_params={"index_type": "int64_t"},
        source=tmp_path / "c.c",
        archive=None,
        flags=("-O3",),
        object_hash="",
        remarks=Remarks(vectorized=0, missed=()),
        error="gcc: error",
    )
    reports = [sweep.RegionReport(r, (failed,)) for r in program.regions]

    report.write(reports, MATRIX, tmp_path)

    sut = report.load(tmp_path / "report.json")
    assert [r.symbol for r in sut.regions] == [r.symbol for r in program.regions]
    assert sut.regions[0].candidates[0].error == "gcc: error"
