"""The agent studies' runner and the SoftHier judge (agents/): what they read, and how the judge decides."""

import importlib.util
import json
import math
import pathlib
import struct
import sys
from types import ModuleType

import pytest

from alloy.isa import softhier

AGENTS = pathlib.Path(__file__).resolve().parent.parent / "agents"


def loaded(path: pathlib.Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def host() -> ModuleType:
    return loaded(AGENTS / "softhier" / "host.py")


def test_the_judge_runs_the_configuration_the_table_was_checked_on() -> None:
    assert (AGENTS / "softhier" / "alloy_v1.py").read_text() == softhier.arch()


def test_softhier_runs_the_tenstorrent_tasks_and_the_running_example() -> None:
    tensix = json.loads((AGENTS / "tensix" / "agents" / "tasks.json").read_text())
    ours = json.loads((AGENTS / "softhier" / "tasks.json").read_text())

    assert ours[:-1] == tensix and ours[-1]["name"] == "gemm64"


def test_the_judge_accepts_the_reference_and_refuses_one_wrong_element(host: ModuleType) -> None:
    task = host.TASKS["tsvc_2_s251"]
    data = host.inputs(task)
    ref = host.reference(task, data)
    words = [struct.unpack("<I", struct.pack("<f", r))[0] for r in ref]
    wrong = [*words[:7], struct.unpack("<I", struct.pack("<f", ref[7] * 1.01 + 1e-3))[0], *words[8:]]

    assert host.compare(task, words, ref)[0]
    ok, _, why = host.compare(task, wrong, ref)
    assert not ok and why.startswith("element 7")


def test_a_reduce_is_graded_on_the_sum_of_the_cluster_partials(host: ModuleType) -> None:
    task = host.TASKS["tsvc_2_s311"]
    (total,) = host.reference(task, host.inputs(task))
    parts = [total / 4] * 4
    words = [struct.unpack("<I", struct.pack("<f", p))[0] for p in parts]

    assert host.compare(task, words, [total])[0]
    assert not host.compare(task, words[:3], [total])[0]
    assert math.isclose(sum(parts), total)


@pytest.mark.parametrize("name", json.loads((AGENTS / "softhier" / "tasks.json").read_text()), ids=lambda t: t["name"])
def test_every_task_has_a_scalar_reference_kernel(host: ModuleType, name: dict) -> None:
    kernel = host.reference_kernel(name)

    assert "void alloy_kernel(" in kernel and "flex_dma_async_wait_all();" in kernel


def test_a_task_line_with_a_temporary_becomes_one_c_statement_per_line(host: ModuleType) -> None:
    kernel = host.reference_kernel(host.TASKS["tsvc_2_s251"])

    assert "const float s = (b[i] + (c[i] * d[i])); a[i] = (s * s);" in kernel


def test_the_runner_reads_each_studys_spec_and_tasks(tmp_path: pathlib.Path) -> None:
    sys.path.insert(0, str(AGENTS))
    run_agent = loaded(AGENTS / "run_agent.py")

    assert "tsvc_2_va" in run_agent.call("read_file", {"path": "agents/tasks.json"}, tmp_path)[0]
    run_agent.STUDY = run_agent.STUDIES["softhier"]
    assert "alloy_kernel" in run_agent.call("read_file", {"path": "SPEC.md"}, tmp_path)[0]
    assert run_agent.call("write_file", {"path": "../escape", "content": "x"}, tmp_path)[0].startswith("error")
