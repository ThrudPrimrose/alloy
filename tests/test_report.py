# Copyright 2026 ETH Zurich and the Alloy authors.
import json

from helpers import MATRIX, outlined

from alloy import report, sweep
from alloy.build import build
from alloy.candidates import Candidate


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
