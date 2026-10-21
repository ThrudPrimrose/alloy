# Copyright 2026 ETH Zurich and the Alloy authors.
"""Alloy as an HPCAgent-Bench flavor plugin end to end on one kernel: every region gets several verified
variants, and both CPU profile flavors submit a library the judge grades correct. The ``alloy`` CI job runs it."""

import pathlib
import threading
from collections.abc import Callable, Iterator
from http.server import ThreadingHTTPServer

import pytest

pytest.importorskip("hpcagent_bench", reason="the HPCAgent-Bench plugin needs the bench extra")

from hpcagent_bench import config
from hpcagent_bench.categories import Baseline, InputMode, Language, Oracle, SourceMode
from hpcagent_bench.config import SubmitFeedback
from hpcagent_bench.harness import tools
from hpcagent_bench.harness.judge_wire import GradeAnswer
from hpcagent_bench.harness.optimizers import optimizer_registry
from hpcagent_bench.harness.service import ServiceConfig, make_server
from hpcagent_bench.harness.task import Task
from hpcagent_bench.precision import Precision
from hpcagent_bench.spec import BenchSpec

KERNEL = "tsvc_2_vpv"


@pytest.fixture(autouse=True)
def small_grades(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Every grade at S, as HPCAgent-Bench's own suite runs them: the shipped rungs are XL, the timed draws are
    around the fuzz anchor and the held-out cases at declared rungs."""
    monkeypatch.setenv("HPCAGENT_BENCH_FUZZ_SIZE_CAP", "4096")
    monkeypatch.setenv("HPCAGENT_BENCH_MEASUREMENT_TIMING_BACKEND", "min_of_k")
    monkeypatch.setenv("HPCAGENT_BENCH_SERVICE_PRESET", "S")
    monkeypatch.setenv("HPCAGENT_BENCH_FUZZ_ANCHOR", "S")
    with config.overridden("fuzz.hidden_correctness_presets", ["S"] * 5):
        yield


@pytest.fixture
def make_judge() -> Iterator[Callable[..., tuple[ThreadingHTTPServer, str]]]:
    """An in-process judge on an OS-assigned port per call, shut down after the test."""
    servers: list[ThreadingHTTPServer] = []

    def make(cfg: ServiceConfig) -> tuple[ThreadingHTTPServer, str]:
        srv = make_server("127.0.0.1", 0, cfg)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        servers.append(srv)
        return srv, f"http://127.0.0.1:{srv.server_address[1]}"

    yield make
    for srv in servers:
        srv.shutdown()
        srv.server_close()


def test_every_region_gets_several_verified_variants(tmp_path: pathlib.Path) -> None:
    from alloy import configuration_matrix
    from alloy.hb_plugin import adapter as bench

    spec = BenchSpec.load(KERNEL)
    sdfg = bench.pipeline_sdfg(spec, "parallel_cpu", Precision.FP64)

    sut = bench.generated(sdfg, spec, Precision.FP64, configuration_matrix.load(), tmp_path)

    assert sut.regions
    assert sut.verification is not None
    for rep in sut.regions:
        variants = bench.verified(rep, sut.verification.verdicts[rep.region.symbol])
        assert len(variants) >= 2, f"{rep.region.symbol}: {[b.name for b in variants]}"


@pytest.mark.parametrize("flavor", ["dace_cpu_parallel_alloy_profile", "dace_cpu_canon_alloy_profile"])
def test_the_profile_flavor_submits_a_library_the_judge_grades_correct(
    flavor: str,
    make_judge: Callable[..., tuple[ThreadingHTTPServer, str]],
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HPCAGENT_BENCH_SHARED_DIR", str(tmp_path))
    url = make_judge(ServiceConfig(baseline=Baseline.C, oracle=Oracle.AUTO, input_mode=InputMode.ANY, repeat=3))[1]
    monkeypatch.setenv("JUDGE_URL", url)  # the optimizer scores its variants on this judge

    sub = optimizer_registry()[flavor](workdir=tmp_path).solve(Task(KERNEL, SourceMode.ANY, Language.C))

    assert sub.library is not None
    with config.overridden("service.submit_feedback", SubmitFeedback.FULL):  # need the measured grade, not the verdict
        r = tools.JudgeClient(url).submit(sub, KERNEL)
    assert isinstance(r, GradeAnswer), r
    assert r.build_ok is True, r.detail
    assert r.correct is True, r.detail
    assert r.speedup > 0.0
