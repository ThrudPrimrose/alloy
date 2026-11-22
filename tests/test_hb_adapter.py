# Copyright 2026 ETH Zurich and the Alloy authors.
"""The Alloy adapter's inner tier without a judge: the stub ranking keeps each scope's fastest candidate over the
best prefix so far, survives a failing stub, stops when the budget does, reads a stub's time from either profile, and
a rendered library asks for the scratch its entry carves transients from."""

import dataclasses
import pathlib
import tempfile

import pytest

from alloy import gpu, gpu_build
from alloy.gpu_build import GpuCandidate, GpuCompiler

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
    stub_affordable,
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

    sut, times = ranked(["r0", "r1"], start, candidates, time_stub, always)

    assert {s: b.name for s, b in sut.items()} == {"r0": "r0.fast", "r1": "r1.fast"}
    assert times == {"r0": {"r0.ref": 5.0, "r0.fast": 1.0, "r0.slow": 9.0}, "r1": {"r1.ref": 4.0, "r1.fast": 2.0}}
    assert set(prefixes) == {"r0.fast"}, "the later scope's stubs run over the earlier scope's winner"


def test_a_failing_stub_drops_out_and_the_start_build_stays_when_all_fail() -> None:
    start = {"r0": Fake("r0.ref")}

    def time_stub(selection: dict[str, Fake], symbol: str) -> float:
        raise RuntimeError("stub did not build")

    sut, _ = ranked(["r0"], start, {"r0": [Fake("r0.a")]}, time_stub, always)

    assert sut["r0"].name == "r0.ref"


def test_the_ranking_stops_when_the_budget_does() -> None:
    start = {"r0": Fake("r0.ref"), "r1": Fake("r1.ref")}
    timed: list[str] = []

    def time_stub(selection: dict[str, Fake], symbol: str) -> float:
        timed.append(selection[symbol].name)
        return 1.0

    sut, times = ranked(["r0", "r1"], start, {"r1": [Fake("r1.fast")]}, time_stub, lambda: len(timed) < 1)

    assert timed == ["r0.ref"]
    assert sut == start
    assert times == {"r0": {"r0.ref": 1.0}, "r1": {}}, "the record keeps the stubs timed before the budget ran out"


def test_the_profile_budget_is_the_agents_budget_scaled_by_the_e1b_factor(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = BenchSpec.load("tsvc_2_vpv")
    agent = adapter.resolve_kernel_timeout(spec)

    monkeypatch.setenv(adapter.BUDGET_SCALE_ENV, "3")

    assert adapter.budget(spec) == 3 * agent
    monkeypatch.setenv(adapter.BUDGET_SCALE_ENV, "0")
    with pytest.raises(ValueError):
        adapter.budget(spec)


def test_a_stub_is_timed_only_while_the_picks_grade_still_fits_after_it() -> None:
    """Stubs of 10 s and a /score of 100 s (the plain program's, graded first): on ault a /score took 110 to 490 s
    and a stub 9 s, so a reserve of a few stub costs left no time to grade the pick (job 920743)."""
    costs = [8.0, 10.0]

    assert stub_affordable(111.0, costs, 100.0)
    assert not stub_affordable(109.0, costs, 100.0)


def test_a_pick_is_compared_to_the_plain_programs_grade_when_it_is_given_without_grading_it_again() -> None:
    judge = Judge({"pick": (True, 2.0)})  # grading "base" would raise KeyError
    plain_grade = ScorePreview(correct=True, speedup=1.5, native_ns=1, baseline_ns=1, baseline="c", speedups={})

    sut = graded_pick(judge, {"r": Fake("pick")}, {"r": Fake("ref")}, library_of, lambda: BASE, "k", plain_grade)  # pyright: ignore[reportArgumentType] -- test double

    assert sut is not None and sut["r"].name == "pick"


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
        answer = self.scores[submission.source]  # pyright: ignore[reportArgumentType] -- test double
        if answer is None:
            raise OSError("no answer")
        correct, speedup = answer
        return ScorePreview(correct=correct, speedup=speedup, native_ns=1, baseline_ns=1, baseline="c", speedups={})


PICK = Submission(language=Language.C, source="pick")
BASE = Submission(language=Language.C, source="base")


PICK_CASES: list[tuple[dict[str, tuple[bool, float] | None], bool]] = [
    ({"pick": (True, 2.0), "base": (True, 1.0)}, True),
    ({"pick": (True, 0.5), "base": (True, 1.0)}, False),
    ({"pick": (False, 9.0), "base": (True, 1.0)}, False),
    ({"pick": None, "base": (True, 1.0)}, False),
    ({"pick": (True, 0.5), "base": (False, 1.0)}, True),
]


@pytest.mark.parametrize(("scores", "expected"), PICK_CASES)
def test_a_pick_replaces_the_references_only_when_it_is_correct_and_no_slower(
    scores: dict[str, tuple[bool, float] | None], expected: bool
) -> None:
    judge = Judge(scores)

    assert faster_correct(judge, lambda: PICK, lambda: judge.score(BASE, "k"), "k") is expected  # pyright: ignore[reportArgumentType] -- test double


def test_the_pick_is_graded_before_the_baseline_overwrites_the_library_they_share() -> None:
    shared = Submission(language=Language.C, source="unbuilt")

    def build(source: str) -> Submission:
        shared.source = source
        return shared

    judge = Judge({"pick": (True, 2.0), "base": (True, 1.0)})

    assert faster_correct(judge, lambda: build("pick"), lambda: judge.score(build("base"), "k"), "k")  # pyright: ignore[reportArgumentType] -- test double


PROFILE_CASES = [((True, 0.53), "base"), ((True, 2.0), "pick")]


@pytest.mark.parametrize(("pick", "expected"), PROFILE_CASES)
def test_profile_delivers_its_stub_timed_pick_only_when_the_judge_grades_it_no_slower(
    pick: tuple[bool, float], expected: str
) -> None:
    """A stub is timed at the fast size and the graded run is larger: a pick 0.53x the references at the graded
    size was delivered for being correct (s115, s119)."""
    judge = Judge({"pick": pick, "base": (True, 1.0)})

    def build(selection: dict[str, Fake]) -> Submission:
        return Submission(language=Language.C, source=selection["r"].name)

    sut = graded_pick(judge, {"r": Fake("pick")}, {"r": Fake("ref")}, build, lambda: BASE, "k")  # pyright: ignore[reportArgumentType] -- test double

    assert (sut["r"].name if sut is not None else "base") == expected


PLAIN_CASES = [((True, 1.2), None), ((True, 2.0), "pick")]


def library_of(selection: dict[str, Fake]) -> Submission:
    return Submission(language=Language.C, source=selection["r"].name)


@pytest.mark.parametrize(("pick", "expected"), PLAIN_CASES)
def test_a_pick_is_delivered_only_when_no_slower_than_the_plain_program(
    pick: tuple[bool, float], expected: str | None
) -> None:
    """The per-scope references build at the strict level, slower than the plain program alloy_none delivers: a
    pick that beat them could still lose to it, and losing delivers the plain program (``None``)."""
    judge = Judge({"pick": pick, "ref": (True, 1.0), "base": (True, 1.5)})

    sut = graded_pick(judge, {"r": Fake("pick")}, {"r": Fake("ref")}, library_of, lambda: BASE, "k")  # pyright: ignore[reportArgumentType] -- test double

    assert (sut["r"].name if sut is not None else None) == expected


def test_a_pick_of_every_reference_delivers_the_plain_program_ungraded() -> None:
    judge = Judge({})

    assert graded_pick(judge, {"r": Fake("ref")}, {"r": Fake("ref")}, library_of, lambda: BASE, "k") is None  # pyright: ignore[reportArgumentType] -- test double


def test_a_failed_verdict_is_not_offered_to_the_stub_ranking() -> None:
    builds = [Fake("good"), Fake("wrong")]
    rep = dataclasses.make_dataclass("Rep", [("builds", list)])([Fake("ref"), *builds])

    sut = verified(rep, {"good": Verdict("pass"), "wrong": Verdict("fail")})

    assert [b.name for b in sut] == ["good"]


def test_a_duplicate_build_is_not_offered_to_the_stub_ranking() -> None:
    builds = [Fake("first"), Fake("again", duplicate_of="first")]
    rep = dataclasses.make_dataclass("Rep", [("builds", list)])([Fake("ref"), *builds])

    sut = verified(rep, {"first": Verdict("pass"), "again": Verdict("pass")})

    assert [b.name for b in sut] == ["first"]


def test_a_run_ranks_at_the_sizes_its_preset_grades_and_a_fuzzed_run_at_its_anchor() -> None:
    spec = cast(BenchSpec, SimpleNamespace(parameters={"S": {"N": 64, "dx": 0.5}, "L": {"N": 4096}}))

    assert adapter.running_sizes(spec, "S") == {"N": 64}, "a float parameter is no size"
    assert adapter.running_sizes(spec, "L+fuzz") == {"N": 4096}


def test_the_ci_stub_waits_on_the_speculative_route_as_long_as_the_tool_does(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    from hpcagent_agent.tools import http_json

    from alloy.hb_plugin.tools.alloy import SWEEP_TIMEOUT_S
    from alloy.hb_plugin.tuners import AlloyToolStub

    timeouts: list[float] = []
    (tmp_path / "Makefile").write_text("all:\n\ttouch lib.so\n")

    def call_json(url: str, data: bytes, timeout: float) -> dict[str, object]:
        timeouts.append(timeout)
        return {"result": {"folder": str(tmp_path), "builds": "lib.so", "workspace_bytes": "0"}}

    monkeypatch.setattr(http_json, "call_json", call_json)

    sut = AlloyToolStub("alloy_stub").tune(Task("k", SourceMode.ANY, Language.C), "canon_cpu")

    assert timeouts == [SWEEP_TIMEOUT_S]
    assert sut.library == str(tmp_path / "lib.so"), "the stub makes the library from the answer, as an agent would"


def test_a_grade_slower_than_one_judge_call_is_still_read(monkeypatch: pytest.MonkeyPatch) -> None:
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
    test_a_failed_verdict_is_not_offered_to_the_stub_ranking()
    test_a_duplicate_build_is_not_offered_to_the_stub_ranking()
    test_a_run_ranks_at_the_sizes_its_preset_grades_and_a_fuzzed_run_at_its_anchor()
    with pytest.MonkeyPatch.context() as patch:
        with tempfile.TemporaryDirectory() as folder:
            test_the_ci_stub_waits_on_the_speculative_route_as_long_as_the_tool_does(patch, pathlib.Path(folder))
    with pytest.MonkeyPatch.context() as patch:
        test_a_grade_slower_than_one_judge_call_is_still_read(patch)


def test_the_judge_client_calls_the_workers_own_judge_when_the_run_lists_several(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HPCAGENT_BENCH_JUDGE_URLS", "http://judge-0:8000,http://judge-1:8000")
    monkeypatch.setenv("JUDGE_URL", "http://judge-1:8000")

    sut = adapter.judge_client()

    assert sut.base_url == "http://judge-1:8000"


def test_a_gpu_column_extends_only_the_pipeline_that_hands_a_tuner_its_offloaded_program() -> None:
    import tomllib

    plugin = tomllib.loads((pathlib.Path(adapter.__file__).parent / "plugin.toml").read_text())

    for flavor in ("alloy_profile", "alloy_speculative"):
        gpu_columns = [column for column in plugin["flavors"][flavor]["extends"] if "_gpu_" in column]
        assert gpu_columns == ["dace_gpu_canon"]


def test_a_gpu_episode_records_each_maps_block_or_the_pipelines_with_its_reason() -> None:
    shapes = {1: (32, 8, 1), 0: (256, 1, 1)}

    sut = adapter.gpu_scopes(shapes, True, "profiled")
    fallback = adapter.gpu_scopes(shapes, False, "graded wrong")

    assert [(s.symbol, s.chosen, s.axes) for s in sut] == [
        ("map0", "256,1,1", {"block": "256,1,1"}),
        ("map1", "32,8,1", {"block": "32,8,1"}),
    ]
    assert [(s.chosen, s.note, s.axes) for s in fallback] == [("none", "graded wrong", {})] * 2
    assert [s.symbol for s in adapter.gpu_scopes({}, False, "no maps")] == ["program"]


def test_a_speculative_gpu_episode_whose_shapes_fail_records_the_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    kept: list[tuple[int, object]] = []
    task = Task("tsvc_2_vpv", SourceMode.ANY, Language.CUDA, image="nvidia")

    def no_report(*_: object) -> object:
        raise RuntimeError("no compiler report")

    monkeypatch.setattr(gpu, "speculate", no_report)
    monkeypatch.setattr(gpu, "native_arch", lambda dialect: "8.9")
    monkeypatch.setattr(adapter, "device_submission", lambda *args: BASE)

    sut = adapter.speculative_gpu(task, "canon_gpu", lambda schema, data: kept.append((schema, data)))  # type: ignore[arg-type,return-value]

    assert sut is BASE
    ((schema, data),) = kept
    assert isinstance(data, dict) and (schema, data["mode"]) == (2, "gpu-speculative")
    assert data["scopes"] == [
        {"symbol": "program", "reference": "pipeline", "chosen": "none", "note": "dropped: no compiler report",
         "axes": {}, "search": None}
    ]  # fmt: skip


def test_a_gpu_form_calling_a_catalog_library_is_submitted_as_the_library_built_in_the_episode_folder(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The judge links a source pair's libraries only on a ``startup.load`` request, which Alloy's setups refuse, and
    takes a submitted library only from the episode's folder; so a form calling hipBLAS ships as the library built
    there with ``-lhipblas`` (S2 on MI200: atax's hipblasDgemv)."""
    form = SimpleNamespace(code="host", device_code="device", libraries=("hipblas",), workspace_bytes="0")
    monkeypatch.setattr(adapter, "render_canonical", lambda *args: form)
    monkeypatch.setattr(adapter, "gpu_arch", lambda dialect: "gfx90a")
    built: list[tuple[str, pathlib.Path, tuple[str, ...]]] = []

    def build(
        compilers: dict[str, GpuCompiler],
        candidate: GpuCandidate,
        host: str,
        device: str,
        folder: pathlib.Path,
        arch: str,
        libraries: tuple[str, ...],
    ) -> SimpleNamespace:
        built.append((candidate.name, folder, libraries))
        return SimpleNamespace(library=folder / "libhipcc.so", error="")

    monkeypatch.setattr(gpu_build, "build", build)
    task = Task("atax", SourceMode.ANY, Language.HIP, image="amd")
    spec = cast(BenchSpec, SimpleNamespace(short_name="atax"))

    sut = adapter.device_submission(task, spec, cast(object, None), "hip", tmp_path)  # pyright: ignore[reportArgumentType] -- test double

    ((name, folder, libraries),) = built
    assert (name, libraries) == ("hipcc", ("hipblas",))  # the default candidate, with the form's library
    assert folder.parent == tmp_path and folder.name.startswith("alloy-gpu-")  # inside the episode's folder
    assert sut.library == str(folder / "libhipcc.so") and not sut.source
    without_folder = adapter.device_submission(task, spec, cast(object, None), "hip")  # pyright: ignore[reportArgumentType] -- test double
    assert (without_folder.source, without_folder.library) == ("host", None)


def test_a_gpu_form_without_libraries_is_submitted_as_its_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    form = SimpleNamespace(code="host", device_code="device", libraries=(), workspace_bytes="0")
    monkeypatch.setattr(adapter, "render_canonical", lambda *args: form)
    task = Task("tsvc_2_vpv", SourceMode.ANY, Language.HIP, image="amd")

    sut = adapter.device_submission(
        task,
        cast(BenchSpec, SimpleNamespace(short_name="tsvc_2_vpv")),
        cast(object, None),  # pyright: ignore[reportArgumentType] -- test double
        "hip",  # pyright: ignore[reportArgumentType] -- test double
    )

    assert (sut.source, sut.device_source, sut.library) == ("host", "device", None)
