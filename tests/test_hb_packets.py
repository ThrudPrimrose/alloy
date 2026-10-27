# Copyright 2026 ETH Zurich and the Alloy authors.
"""Alloy for an LLM agent: the ``alloy_<mode>`` tools' judge route answers with a library in the bench C ABI, built
from plain C/C++ translation units (no DaCe runtime) by a Makefile the agent can rerun, which the judge grades
correct. The ``alloy`` CI job runs it."""

import contextlib
import pathlib
import subprocess
import threading
from collections.abc import Iterator
from http import HTTPMethod, HTTPStatus

import pytest

pytest.importorskip("hpcagent_bench", reason="the HPCAgent-Bench plugin needs the bench extra")

from hpcagent_bench import config, plugins
from hpcagent_bench.api import RunConfig
from hpcagent_bench.categories import Baseline, InputMode, Language, Oracle
from hpcagent_bench.config import SubmitFeedback
from hpcagent_bench.harness import tools
from hpcagent_bench.harness.envelope import Submission
from hpcagent_bench.harness.judge_wire import GradeAnswer, JudgeAnswer
from hpcagent_bench.harness.routes import ROUTES, RouteRequest
from hpcagent_bench.harness.service import ServiceConfig, make_server

KERNEL = "tsvc_2_vpv"


class FakeJudge:
    """The part of the judge's request handler a route uses; keeps the last answer."""

    def __init__(self) -> None:
        self.cfg = RunConfig()
        self.code = 0
        self.answer: dict[str, object] = {}

    def reply(self, code: int, payload: JudgeAnswer) -> None:
        self.code, self.answer = code, payload.to_json()

    @contextlib.contextmanager
    def device_slot(self) -> Iterator[object]:
        yield object()


def call(mode: str, shared: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> FakeJudge:
    """``POST /alloy/<mode>`` for :data:`KERNEL` on episode ``e1``, writing into the shared folder ``shared``."""
    monkeypatch.setenv("HPCAGENT_BENCH_SHARED_DIR", str(shared))
    plugins.load()
    judge = FakeJudge()
    ROUTES["alloy"].handler(judge, RouteRequest(HTTPMethod.POST, ["alloy", mode], {}, {"kernel": KERNEL}, "e1"))
    return judge


@pytest.fixture
def judge_url(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> Iterator[str]:
    """An in-process judge grading at S, as HPCAgent-Bench's own suite does."""
    monkeypatch.setenv("HPCAGENT_BENCH_SHARED_DIR", str(tmp_path))
    monkeypatch.setenv("HPCAGENT_BENCH_FUZZ_SIZE_CAP", "4096")
    monkeypatch.setenv("HPCAGENT_BENCH_MEASUREMENT_TIMING_BACKEND", "min_of_k")
    monkeypatch.setenv("HPCAGENT_BENCH_SERVICE_PRESET", "S")
    monkeypatch.setenv("HPCAGENT_BENCH_FUZZ_ANCHOR", "S")
    server = make_server(
        "127.0.0.1", 0, ServiceConfig(baseline=Baseline.C, oracle=Oracle.AUTO, input_mode=InputMode.ANY, repeat=3)
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    with config.overridden("fuzz.hidden_correctness_presets", ["S"] * 5):
        yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def graded(url: str, result: dict[str, object]) -> GradeAnswer:
    submission = Submission(
        language=Language.C, library=str(result["library"]), workspace_bytes=str(result["workspace_bytes"])
    )
    with config.overridden("service.submit_feedback", SubmitFeedback.FULL):  # the measured grade, not the verdict
        grade = tools.JudgeClient(url).submit(submission, KERNEL)
    assert isinstance(grade, GradeAnswer), grade
    return grade


def test_the_speculative_tool_answers_c_sources_a_makefile_and_a_library_the_judge_grades_correct(
    judge_url: str, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sut = call("speculative", tmp_path, monkeypatch)

    assert sut.code == HTTPStatus.OK, sut.answer
    result = sut.answer["result"]
    assert isinstance(result, dict)
    folder = pathlib.Path(str(result["folder"]))
    assert folder.is_relative_to(tmp_path) and pathlib.Path(str(result["library"])).is_file()
    entry = (folder / "program.c").read_text()
    assert "#include <dace" not in entry and '#include "dace' not in entry, "the entry needs no DaCe runtime"
    for scope in result["scopes"]:
        assert (folder / scope["source"]).is_file()
        assert scope["compiler"] in (folder / "Makefile").read_text()
    assert "## " in str(result["report"]), "the report's sections come back"
    grade = graded(judge_url, result)
    assert grade.build_ok is True and grade.correct is True, grade.detail


def test_make_rebuilds_the_library_the_tool_built(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result = call("speculative", tmp_path, monkeypatch).answer["result"]
    assert isinstance(result, dict)
    library = pathlib.Path(str(result["library"]))
    library.unlink()

    subprocess.run([*str(result["make"]).split(), "-B"], check=True, capture_output=True)

    assert library.is_file()


def test_a_mode_alloy_does_not_have_is_not_found(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sut = call("fastest", tmp_path, monkeypatch)

    assert sut.code == HTTPStatus.NOT_FOUND
    assert "profile" in str(sut.answer["error"]) and "speculative" in str(sut.answer["error"])
