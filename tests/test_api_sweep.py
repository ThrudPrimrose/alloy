# Copyright 2026 ETH Zurich and the Alloy authors.
"""``alloy_sweep``'s core: a scope's edited translation unit swept in place of its rendering, verified against the
rendering of the program itself."""

import pathlib

import pytest

from alloy import api
from alloy.report import Mode
from helpers import REDUCTIONS, SCALE_MANIFEST, gcc_only, load_program, write_manifest


def edited_run(tmp_path: pathlib.Path, edit: str) -> tuple[api.Result, str]:
    """``scale`` generated once, its ``best/scopes`` unit edited by ``edit`` (old -> new), generated again from it."""
    manifest = write_manifest(tmp_path, "scale", SCALE_MANIFEST)
    matrix = gcc_only(tmp_path)
    sdfg = load_program(f"{REDUCTIONS}:scale").to_sdfg()
    first = api.generate(sdfg, tmp_path / "first", manifest=manifest, matrix=matrix, mode=Mode.SPECULATIVE)
    (unit,) = (tmp_path / "first" / "best" / "scopes").glob("*.c")
    old, new = edit.split(" -> ")
    text = unit.read_text()
    assert old in text, f"{old!r} not in the rendered scope"
    edited = tmp_path / "edited" / unit.name
    edited.parent.mkdir()
    edited.write_text(text.replace(old, new))  # every loop: an intrinsic unit repeats the body in its remainder loop
    sdfg = load_program(f"{REDUCTIONS}:scale").to_sdfg()
    result = api.generate(
        sdfg, tmp_path / "second", manifest=manifest, matrix=matrix, mode=Mode.SPECULATIVE, sources={unit.stem: edited}
    )
    assert first.best is not None
    return result, unit.stem


def test_a_correct_edit_is_built_by_every_candidate_and_verified_against_the_rendering(tmp_path: pathlib.Path) -> None:
    sut, symbol = edited_run(tmp_path, "2.0 -> (1.0 + 1.0)")

    (report,) = sut.scopes
    reference, *agent = report.builds
    assert not reference.name.startswith("agent_") and agent
    assert all(b.name.startswith("agent_") and not b.error for b in agent)
    assert sut.verification is not None
    verdicts = sut.verification.verdicts[symbol]
    assert all(verdicts[b.name].ok for b in agent if not b.duplicate_of)


def test_a_wrong_edit_fails_verification(tmp_path: pathlib.Path) -> None:
    sut, symbol = edited_run(tmp_path, "2.0 -> 3.0")

    assert sut.verification is not None
    verdicts = sut.verification.verdicts[symbol]
    agent = [b for b in sut.scopes[0].builds if b.name.startswith("agent_") and not b.duplicate_of]
    assert agent and not any(verdicts[b.name].ok for b in agent)
    assert sut.winners and not any(b.name.startswith("agent_") for b in sut.winners.values())


def test_a_unit_named_after_no_scope_is_refused(tmp_path: pathlib.Path) -> None:
    manifest = write_manifest(tmp_path, "scale", SCALE_MANIFEST)
    stray = tmp_path / "nope.c"
    stray.write_text("void nope(void) {}\n")
    sdfg = load_program(f"{REDUCTIONS}:scale").to_sdfg()

    with pytest.raises(api.NotAScope, match="nope"):
        api.generate(sdfg, tmp_path / "out", manifest=manifest, matrix=gcc_only(tmp_path), sources={"nope": stray})


def test_reference_mode_links_each_scopes_default_build_unswept(tmp_path: pathlib.Path) -> None:
    manifest = write_manifest(tmp_path, "scale", SCALE_MANIFEST)
    sdfg = load_program(f"{REDUCTIONS}:scale").to_sdfg()

    sut = api.generate(sdfg, tmp_path / "out", manifest=manifest, matrix=gcc_only(tmp_path), mode=Mode.REFERENCE)

    (report,) = sut.scopes
    assert len(report.builds) == 1 and not report.pruned
    assert sut.best is not None and sut.timings is None
    assert {s.symbol: s.candidate for s in sut.best.scopes} == {report.scope.symbol: report.builds[0].name}
