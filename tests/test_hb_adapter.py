# Copyright 2026 ETH Zurich and the Alloy authors.
"""The Alloy adapter's inner tier without a judge: the stub ranking keeps each region's fastest candidate over the
best prefix so far, survives a failing stub, stops when the budget does, reads a stub's time from either profile, and
a rendered library asks for the scratch its entry carves transients from."""

import dataclasses

import pytest

pytest.importorskip("hpcagent_bench", reason="the HPCAgent-Bench plugin needs the bench extra")

from collections.abc import Sequence  # noqa: E402

from hpcagent_bench.categories import Language, Preset, SourceMode  # noqa: E402
from hpcagent_bench.harness.envelope import Submission  # noqa: E402
from hpcagent_bench.harness.profile_wire import DeviceTraceReport, LinuxperfReport, ProfileAnswer  # noqa: E402
from hpcagent_bench.harness.task import Task  # noqa: E402
from hpcagent_bench.precision import Precision  # noqa: E402
from hpcagent_bench.spec import BenchSpec  # noqa: E402

from alloy.hb_plugin.adapter import (  # noqa: E402 -- after the optional-extra skip
    fast_size,
    pipeline_sdfg,
    ranked,
    rendered,
    stub_time,
)


@dataclasses.dataclass(frozen=True, slots=True)
class Fake:
    name: str


def always() -> bool:
    return True


def test_each_region_keeps_its_fastest_stub_over_the_best_prefix() -> None:
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
    assert set(prefixes) == {"r0.fast"}, "the later region's stubs run over the earlier region's winner"


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


@pytest.mark.parametrize(
    ("token", "size"), [("XL", Preset.M), ("L+fuzz", Preset.M), ("M", None), ("S", None), ("fuzzed", None)]
)
def test_a_stub_is_timed_at_the_fast_size_only_where_the_run_is_larger(token: str, size: Preset | None) -> None:
    assert fast_size(token) is size


if __name__ == "__main__":
    test_each_region_keeps_its_fastest_stub_over_the_best_prefix()
    test_a_failing_stub_drops_out_and_the_start_build_stays_when_all_fail()
    test_the_ranking_stops_when_the_budget_does()
    test_a_cpu_stub_time_is_the_elapsed_time_of_the_graded_thread_count()
    test_a_gpu_stub_time_is_the_device_time_per_repetition()
    test_a_profile_without_a_time_is_refused()
    for token, size in (("XL", Preset.M), ("L+fuzz", Preset.M), ("M", None), ("S", None), ("fuzzed", None)):
        test_a_stub_is_timed_at_the_fast_size_only_where_the_run_is_larger(token, size)


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
