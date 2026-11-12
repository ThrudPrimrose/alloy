# Copyright 2026 ETH Zurich and the Alloy authors.
"""The Alloy adapter's inner tier without a judge: the stub ranking keeps each scope's fastest candidate over the
best prefix so far, survives a failing stub, stops when the budget does, reads a stub's time from either profile, and
a rendered library asks for the scratch its entry carves transients from."""

import dataclasses
import json
import pathlib
import tempfile

import pytest

pytest.importorskip("hpcagent_bench", reason="the HPCAgent-Bench plugin needs the bench extra")

from collections.abc import Sequence
from types import SimpleNamespace
from typing import cast

from hpcagent_bench.categories import Language, Preset, SourceMode
from hpcagent_bench.harness.envelope import Submission
from hpcagent_bench.harness.judge_wire import ScorePreview
from hpcagent_bench.harness.profile_wire import DeviceTraceReport, LinuxperfReport, ProfileAnswer
from hpcagent_bench.harness.task import Task
from hpcagent_bench.precision import Precision
from hpcagent_bench.spec import BenchSpec

from alloy.evaluate.verify import Verdict
from alloy.hb_plugin import adapter
from alloy.hb_plugin.adapter import (
    fast_size,
    faster_correct,
    graded_pick,
    pipeline_sdfg,
    ranked,
    rendered,
    stub_time,
    verified,
)


@dataclasses.dataclass(frozen=True, slots=True)
class Fake:
    name: str
    duplicate_of: str = ""


def always() -> bool:
    return True


def test_each_scope_keeps_its_fastest_stub_over_the_best_prefix() -> None:
    start = {"r0": Fake("r0.ref"), "r1": Fake("r1.ref")}
    candidates = {"r0": [Fake("r0.fast"), Fake("r0.slow")], "r1": [Fake("r1.fast")]}
    cost = {"r0.ref": 5.0, "r0.fast": 1.0, "r0.slow": 9.0, "r1.ref": 4.0, "r1.fast": 2.0}
    prefixes: list[str] = []

    def time_stub(selection: dict[str, Fake], symbol: str) -> float:
        if symbol == "r1":
            prefixes.append(selection["r0"].name)
        return cost[selection[symbol].name]

    sut = ranked(["r0", "r1"], start, candidates, time_stub, always)

    assert {s: b.name for s, b in sut.items()} == {"r0": "r0.fast", "r1": "r1.fast"}
    assert set(prefixes) == {"r0.fast"}, "the later scope's stubs run over the earlier scope's winner"


def test_a_failing_stub_drops_out_and_the_start_build_stays_when_all_fail() -> None:
    start = {"r0": Fake("r0.ref")}

    def time_stub(selection: dict[str, Fake], symbol: str) -> float:
        raise RuntimeError("stub did not build")

    sut = ranked(["r0"], start, {"r0": [Fake("r0.a")]}, time_stub, always)

    assert sut["r0"].name == "r0.ref"


def test_the_ranking_stops_when_the_budget_does() -> None:
    start = {"r0": Fake("r0.ref"), "r1": Fake("r1.ref")}
    timed: list[str] = []

    def time_stub(selection: dict[str, Fake], symbol: str) -> float:
        timed.append(selection[symbol].name)
        return 1.0

    sut = ranked(["r0", "r1"], start, {"r1": [Fake("r1.fast")]}, time_stub, lambda: len(timed) < 1)

    assert timed == ["r0.ref"]
    assert sut == start


def test_a_cpu_stub_time_is_the_elapsed_time_of_the_graded_thread_count() -> None:
    configs = [{"threads": 1, "elapsed_ns": 900}, {"threads": 8, "elapsed_ns": 200}]
    answer = ProfileAnswer.model_construct(root=LinuxperfReport.model_construct(configs=configs))

    assert stub_time(answer) == 200.0


def test_a_gpu_stub_time_is_the_device_time_per_repetition() -> None:
    answer = ProfileAnswer.model_construct(root=DeviceTraceReport.model_construct(device_ns_per_rep=1234.5))

    assert stub_time(answer) == 1234.5


def test_a_profile_without_a_time_is_refused() -> None:
    answer = ProfileAnswer.model_construct(root=LinuxperfReport.model_construct(configs=[]))

    with pytest.raises(ValueError, match="no stub time"):
        stub_time(answer)


#: A bare fuzzed run, seeded or not, anchors at XL.
FUZZED_XL = (("fuzzed", Preset.M), ("fuzzed:42", Preset.M))


FAST_SIZES = [("XL", Preset.M), ("L+fuzz", Preset.M), ("M", None), ("S", None), *FUZZED_XL, ("M+fuzz:7", None)]


@pytest.mark.parametrize(("token", "size"), FAST_SIZES)
def test_a_stub_is_timed_at_the_fast_size_only_where_the_run_is_larger(token: str, size: Preset | None) -> None:
    assert fast_size(token) is size


def as_source(code: str, link: Sequence[str]) -> Submission:
    return Submission(language=Language.CPP, source=code)


def test_a_library_whose_entry_keeps_a_transient_asks_for_its_scratch() -> None:
    spec = BenchSpec.load("atax")  # tmp = A @ x is an M-vector between the two products
    sdfg = pipeline_sdfg(spec, "canon_cpu", Precision.FP64)

    sut = rendered(Task("atax", SourceMode.ANY, Language.CPP), spec, sdfg, as_source)

    assert sut.workspace_bytes == "8*M + 64"


def test_a_library_without_transients_asks_for_no_scratch() -> None:
    spec = BenchSpec.load("tsvc_2_vpv")
    sdfg = pipeline_sdfg(spec, "canon_cpu", Precision.FP64)

    sut = rendered(Task("tsvc_2_vpv", SourceMode.ANY, Language.CPP), spec, sdfg, as_source)

    assert sut.workspace_bytes is None


@dataclasses.dataclass
class Judge:
    """Scores from a table; ``None`` is a judge that does not answer."""

    scores: dict[str, tuple[bool, float] | None]

    def score(self, submission: Submission, kernel: str) -> ScorePreview:
        answer = self.scores[submission.source]
        if answer is None:
            raise OSError("no answer")
        correct, speedup = answer
        return ScorePreview(correct=correct, speedup=speedup, native_ns=1, baseline_ns=1, baseline="c", speedups={})


PICK = Submission(language=Language.C, source="pick")
BASE = Submission(language=Language.C, source="base")


PICK_CASES = [
    ({"pick": (True, 2.0), "base": (True, 1.0)}, True),
    ({"pick": (True, 0.5), "base": (True, 1.0)}, False),
    ({"pick": (False, 9.0), "base": (True, 1.0)}, False),
    ({"pick": None, "base": (True, 1.0)}, False),
    ({"pick": (True, 0.5), "base": (False, 1.0)}, True),
]


@pytest.mark.parametrize(("scores", "expected"), PICK_CASES)
def test_a_pick_replaces_the_references_only_when_it_is_correct_and_no_slower(scores, expected) -> None:
    assert faster_correct(Judge(scores), lambda: PICK, lambda: BASE, "k") is expected  # type: ignore[arg-type]


def test_the_pick_is_graded_before_the_baseline_overwrites_the_library_they_share() -> None:
    shared = Submission(language=Language.C, source="unbuilt")

    def build(source: str) -> Submission:
        shared.source = source
        return shared

    judge = Judge({"pick": (True, 2.0), "base": (True, 1.0)})

    assert faster_correct(judge, lambda: build("pick"), lambda: build("base"), "k")  # type: ignore[arg-type]


PROFILE_CASES = [((True, 0.53), "base"), ((True, 2.0), "pick")]


@pytest.mark.parametrize(("pick", "expected"), PROFILE_CASES)
def test_profile_delivers_its_stub_timed_pick_only_when_the_judge_grades_it_no_slower(pick, expected) -> None:
    """A stub is timed at the fast size and the graded run is larger: a pick 0.53x the references at the graded
    size was delivered for being correct (s115, s119)."""
    judge = Judge({"pick": pick, "base": (True, 1.0)})

    def build(selection: dict[str, Fake]) -> Submission:
        return Submission(language=Language.C, source=selection["r"].name)

    sut = graded_pick(judge, {"r": Fake("pick")}, {"r": Fake("ref")}, build, lambda: BASE, "k")  # type: ignore[arg-type]

    assert (sut["r"].name if sut is not None else "base") == expected


PLAIN_CASES = [((True, 1.2), None), ((True, 2.0), "pick")]


def library_of(selection: dict[str, Fake]) -> Submission:
    return Submission(language=Language.C, source=selection["r"].name)


@pytest.mark.parametrize(("pick", "expected"), PLAIN_CASES)
def test_a_pick_is_delivered_only_when_no_slower_than_the_plain_program(pick, expected) -> None:
    """The per-scope references build at the strict level, slower than the plain program alloy_none delivers: a
    pick that beat them could still lose to it, and losing delivers the plain program (``None``)."""
    judge = Judge({"pick": pick, "ref": (True, 1.0), "base": (True, 1.5)})

    sut = graded_pick(judge, {"r": Fake("pick")}, {"r": Fake("ref")}, library_of, lambda: BASE, "k")  # type: ignore[arg-type]

    assert (sut["r"].name if sut is not None else None) == expected


def test_a_pick_of_every_reference_delivers_the_plain_program_ungraded() -> None:
    judge = Judge({})

    assert graded_pick(judge, {"r": Fake("ref")}, {"r": Fake("ref")}, library_of, lambda: BASE, "k") is None  # type: ignore[arg-type]


def test_an_episode_delivering_the_plain_program_records_no_scope_build(tmp_path) -> None:
    def built(name: str) -> SimpleNamespace:
        return SimpleNamespace(name=name, candidate=SimpleNamespace(note=name))

    library = Submission(language=Language.C, source="", library=str(tmp_path / "lib.so"))
    task = cast(Task, SimpleNamespace(kernel="k"))
    refs, pick = {"r": built("ref")}, {"r": built("pick")}

    adapter.record_episode("speculative", task, 0.0, library, references=refs, delivered=None)  # type: ignore[arg-type]
    plain_scopes = json.loads((tmp_path / adapter.EPISODE_RECORD).read_text())["scopes"]
    adapter.record_episode("speculative", task, 0.0, library, references=refs, delivered=pick)  # type: ignore[arg-type]
    pick_scopes = json.loads((tmp_path / adapter.EPISODE_RECORD).read_text())["scopes"]

    assert [(s["reference"], s["chosen"]) for s in plain_scopes] == [("ref", adapter.PLAIN[0])]
    assert [(s["reference"], s["chosen"]) for s in pick_scopes] == [("ref", "pick")]


def test_a_failed_verdict_is_not_offered_to_the_stub_ranking() -> None:
    builds = [Fake("good"), Fake("wrong")]
    rep = dataclasses.make_dataclass("Rep", [("builds", list)])([Fake("ref"), *builds])

    sut = verified(rep, {"good": Verdict("pass"), "wrong": Verdict("fail")})  # type: ignore[arg-type]

    assert [b.name for b in sut] == ["good"]


def test_a_duplicate_build_is_not_offered_to_the_stub_ranking() -> None:
    builds = [Fake("first"), Fake("again", duplicate_of="first")]
    rep = dataclasses.make_dataclass("Rep", [("builds", list)])([Fake("ref"), *builds])

    sut = verified(rep, {"first": Verdict("pass"), "again": Verdict("pass")})  # type: ignore[arg-type]

    assert [b.name for b in sut] == ["first"]


def test_a_run_ranks_at_the_sizes_its_preset_grades_and_a_fuzzed_run_at_its_anchor() -> None:
    spec = cast(BenchSpec, SimpleNamespace(parameters={"S": {"N": 64, "dx": 0.5}, "L": {"N": 4096}}))

    assert adapter.running_sizes(spec, "S") == {"N": 64}, "a float parameter is no size"
    assert adapter.running_sizes(spec, "L+fuzz") == {"N": 4096}


def test_the_ci_stub_waits_on_the_speculative_route_as_long_as_the_tool_does(monkeypatch) -> None:
    from hpcagent_agent.tools import http_json

    from alloy.hb_plugin.tools.alloy import SWEEP_TIMEOUT_S
    from alloy.hb_plugin.tuners import AlloyToolStub

    timeouts: list[float] = []

    def call_json(url: str, data: bytes, timeout: float) -> dict[str, object]:
        timeouts.append(timeout)
        return {"result": {"library": "lib.so", "workspace_bytes": "0"}}

    monkeypatch.setattr(http_json, "call_json", call_json)

    AlloyToolStub("alloy_stub").tune(Task("k", SourceMode.ANY, Language.C), "canon_cpu")

    assert timeouts == [SWEEP_TIMEOUT_S]


def test_a_grade_slower_than_one_judge_call_is_still_read(monkeypatch) -> None:
    """A large kernel's ``/score`` outlasts an ordinary judge call (300 s): the client gave up, the judge logged the
    grade as abandoned, and the pick was dropped for the references (s4112, vag)."""
    from hpcagent_agent.tools import http_json

    monkeypatch.setenv("JUDGE_TIMEOUT_SECONDS", "1")
    monkeypatch.setenv(http_json.UPSTREAM_TIMEOUT_ENV, "5400")

    sut = adapter.judge_client()

    assert sut.timeout == http_json.terminal_timeout() and sut.timeout > 5400


if __name__ == "__main__":
    test_each_scope_keeps_its_fastest_stub_over_the_best_prefix()
    test_a_failing_stub_drops_out_and_the_start_build_stays_when_all_fail()
    test_the_ranking_stops_when_the_budget_does()
    test_a_cpu_stub_time_is_the_elapsed_time_of_the_graded_thread_count()
    test_a_gpu_stub_time_is_the_device_time_per_repetition()
    test_a_profile_without_a_time_is_refused()
    for token, size in FAST_SIZES:
        test_a_stub_is_timed_at_the_fast_size_only_where_the_run_is_larger(token, size)
    test_a_library_whose_entry_keeps_a_transient_asks_for_its_scratch()
    test_a_library_without_transients_asks_for_no_scratch()
    for scores, expected in PICK_CASES:
        test_a_pick_replaces_the_references_only_when_it_is_correct_and_no_slower(scores, expected)
    test_the_pick_is_graded_before_the_baseline_overwrites_the_library_they_share()
    for pick, delivered in PROFILE_CASES:
        test_profile_delivers_its_stub_timed_pick_only_when_the_judge_grades_it_no_slower(pick, delivered)
    for pick, delivery in PLAIN_CASES:
        test_a_pick_is_delivered_only_when_no_slower_than_the_plain_program(pick, delivery)
    test_a_pick_of_every_reference_delivers_the_plain_program_ungraded()
    with tempfile.TemporaryDirectory() as folder:
        test_an_episode_delivering_the_plain_program_records_no_scope_build(pathlib.Path(folder))
    test_a_failed_verdict_is_not_offered_to_the_stub_ranking()
    test_a_duplicate_build_is_not_offered_to_the_stub_ranking()
    test_a_run_ranks_at_the_sizes_its_preset_grades_and_a_fuzzed_run_at_its_anchor()
    with pytest.MonkeyPatch.context() as patch:
        test_the_ci_stub_waits_on_the_speculative_route_as_long_as_the_tool_does(patch)
    with pytest.MonkeyPatch.context() as patch:
        test_a_grade_slower_than_one_judge_call_is_still_read(patch)
