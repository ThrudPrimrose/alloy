# Copyright 2026 ETH Zurich and the Alloy authors.
"""An Alloy episode's plugin record: the delivered build's axes, the search's counts, the default's and the per-axis
best stub times, the compiler-only best, the plain program's empty axes, truncation under the bench's cap, and a tuner outside a run."""

import dataclasses
import pathlib

import pytest

pytest.importorskip("hpcagent_bench", reason="the HPCAgent-Bench plugin needs the bench extra")

from hpcagent_bench.harness import plugin_records

from alloy import configuration_matrix
from alloy.backend.build import Remarks
from alloy.backend.candidates import Candidate
from alloy.evaluate.verify import Verdict
from alloy.hb_plugin import episode
from alloy.hb_plugin.episode import EpisodeSeconds, axes, scope_record
from alloy.heuristics.predict import Prediction

MATRIX = configuration_matrix.load()
REFERENCE = Candidate("c", "gcc")
SERIAL = Candidate("c", "gcc", serial=True)
CONTRACT = Candidate("c", "gcc", fp_level="contract")
BOTH = Candidate("c", "gcc", fp_level="contract", serial=True)
WRONG = Candidate("c", "gcc", fp_level="reciprocal")
SECONDS = EpisodeSeconds(1.0, 2.0, 3.0, 6.0)


@dataclasses.dataclass(frozen=True, slots=True)
class FakeBuild:
    candidate: Candidate
    name: str
    archive: pathlib.Path | None = pathlib.Path("lib.a")
    duplicate_of: str = ""
    remarks: Remarks = Remarks(3, ())


@dataclasses.dataclass(frozen=True, slots=True)
class FakeScope:
    symbol: str


@dataclasses.dataclass(frozen=True, slots=True)
class FakeReport:
    scope: FakeScope
    builds: tuple[FakeBuild, ...]


def built(candidate: Candidate, **fields: str) -> FakeBuild:
    return FakeBuild(candidate, candidate.name(MATRIX), **fields)  # type: ignore[arg-type]


REF, SER, CON, BOT, BAD = (built(c) for c in (REFERENCE, SERIAL, CONTRACT, BOTH, WRONG))
DUP = FakeBuild(Candidate("c", "gcc", fp_level="noerrno"), "dup", duplicate_of=CON.name)
REPORT = FakeReport(FakeScope("s0"), (REF, SER, CON, BOT, BAD, DUP))
#: A duplicate is verified as its own build, but counts once, as the build it duplicates.
VERDICTS = {b.name: Verdict("pass") for b in (SER, CON, BOT, DUP)} | {BAD.name: Verdict("fail")}
#: Contract alone is fastest; serial alone is slower than the reference.
TIMED = {REF.name: 100.0, SER.name: 120.0, CON.name: 60.0, BOT.name: 80.0}


def test_axes_name_every_default_and_the_candidates_own_values() -> None:
    sut = axes(BOTH, MATRIX)

    assert axes(REFERENCE, MATRIX) | {"fp_level": "contract", "threading": "serial"} == sut
    assert axes(REFERENCE, MATRIX)["fp_level"] == MATRIX.defaults.fp_level


def test_a_scope_record_counts_the_search_and_keeps_each_axis_best_at_its_default() -> None:
    sut = scope_record(REPORT, MATRIX, CON, VERDICTS, TIMED)  # type: ignore[arg-type]

    assert (sut.reference, sut.chosen, sut.axes) == (REF.name, CON.name, axes(CONTRACT, MATRIX))
    assert sut.search is not None
    assert (sut.search.built, sut.search.verified, sut.search.rejected, sut.search.timed) == (4, 3, 1, 3)
    assert sut.search.default_ns == 100.0
    # without the contract level the best is the reference; without serial the contract build, the best overall
    assert sut.search.best_ns_by_axis["fp_level"] == 100.0
    assert sut.search.best_ns_by_axis["threading"] == 60.0
    assert sut.search.best_ns_by_axis["compiler"] == 60.0
    assert sut.search.predicted_gain is None
    assert sut.search.fastest == (CON.name, BOT.name, REF.name, SER.name)
    assert sut.search.vectorized == 3


def test_the_compiler_only_best_is_the_fastest_build_differing_from_the_reference_in_the_compiler_alone() -> None:
    clang, clang_contract = built(Candidate("c", "clang")), built(Candidate("c", "clang", fp_level="contract"))
    report = FakeReport(FakeScope("s0"), (REF, SER, CON, clang, clang_contract))
    timed = TIMED | {clang.name: 70.0, clang_contract.name: 50.0}

    sut = scope_record(report, MATRIX, CON, VERDICTS, timed)  # type: ignore[arg-type]

    assert sut.search is not None
    # clang at the defaults beats gcc's reference; the faster contract and serial builds change another axis too
    assert sut.search.best_compiler_ns == 70.0
    assert sut.search.best_ns_by_axis["fp_level"] == 70.0
    only_gcc = scope_record(REPORT, MATRIX, CON, VERDICTS, TIMED)  # type: ignore[arg-type]
    assert only_gcc.search is not None and only_gcc.search.best_compiler_ns == 100.0


def test_a_scope_record_keeps_the_region_cost_its_predictions_charged() -> None:
    """The measured region cost (A15) must be in the record, or a speculative pick cannot be replayed."""
    predicted = {
        REF.name: Prediction(2.0, 2.0, 0.0, (), 1, 1.0, 1000.0, 310.0),
        CON.name: Prediction(1.0, 1.0, 0.0, (), 1),
    }

    sut = scope_record(REPORT, MATRIX, CON, VERDICTS, TIMED, predicted)  # type: ignore[arg-type]

    assert sut.search is not None
    assert (sut.search.region_ns, sut.search.predicted_gain) == (310.0, 2.0)
    unpredicted = scope_record(REPORT, MATRIX, CON, VERDICTS, TIMED)  # type: ignore[arg-type]
    assert unpredicted.search is not None and unpredicted.search.region_ns is None


def test_the_plain_program_records_no_axes_and_an_untimed_search_no_default() -> None:
    sut = scope_record(REPORT, MATRIX, None, VERDICTS, {})  # type: ignore[arg-type]

    assert (sut.chosen, sut.note, sut.axes) == (*episode.PLAIN, {})
    assert sut.search is not None
    assert (sut.search.timed, sut.search.default_ns, sut.search.best_ns_by_axis, sut.search.best_compiler_ns) == (
        0,
        None,
        {},
        None,
    )


def test_a_record_over_the_cap_keeps_every_delivered_build_and_says_it_is_truncated() -> None:
    scope = scope_record(REPORT, MATRIX, CON, VERDICTS, TIMED)  # type: ignore[arg-type]
    many = tuple(dataclasses.replace(scope, symbol=f"s{i}") for i in range(1000))

    sut = episode.episode("profile", "k", SECONDS, 4, many)

    assert isinstance(sut, dict) and isinstance(scopes := sut["scopes"], list)
    kept = [s for s in scopes if isinstance(s, dict)]
    assert sut["truncated"] is True
    assert [s["chosen"] for s in kept] == [CON.name] * 1000
    assert all(s["search"] is None and s["axes"] == {} for s in kept)
    assert len(plugin_records.PluginRecord(schema_version=episode.SCHEMA, data=sut).model_dump_json()) <= (
        plugin_records.CAP_BYTES
    )


def test_a_record_under_the_cap_is_kept_whole_where_the_judge_archives_it(tmp_path: pathlib.Path) -> None:
    scope = scope_record(REPORT, MATRIX, CON, VERDICTS, TIMED)  # type: ignore[arg-type]
    data = episode.episode("profile", "k", SECONDS, 4, (scope,))

    episode.keep_episode(lambda schema, d: plugin_records.keep(tmp_path, "alloy", schema, d), data)

    kept = plugin_records.found(tmp_path)["alloy"]
    assert (kept.schema_version, kept.data) == (episode.SCHEMA, data)
    assert isinstance(data, dict) and data["truncated"] is False


def test_a_tuner_outside_a_run_logs_and_keeps_going(capsys: pytest.CaptureFixture[str]) -> None:
    def refuse(schema: int, data: object) -> pathlib.Path:
        raise ValueError("a record needs an episode folder")

    episode.keep_episode(refuse, episode.episode("none", "k", SECONDS, 0, ()))

    assert "episode record not kept: a record needs an episode folder" in capsys.readouterr().err
