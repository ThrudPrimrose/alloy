# Copyright 2026 ETH Zurich and the Alloy authors.
"""The judge half of ``alloy_sweep``: the agent's edited units are read from its own folder only."""

import pathlib
import sys
from collections.abc import Callable
from http import HTTPMethod

import pytest

pytest.importorskip("hpcagent_bench", reason="the HPCAgent-Bench plugin needs the bench extra")

from hpcagent_bench import plugins
from hpcagent_bench.harness.routes import ROUTES, RouteRequest
from hpcagent_bench.harness.sandbox import agent_root

plugins.load()  # the plugin's routes load under the bench's plugin package, once
copied_units: Callable[[RouteRequest, pathlib.Path], dict[str, str]] = sys.modules[
    ROUTES["alloy"].handler.__module__
].copied_units


def request(folder: str) -> RouteRequest:
    return RouteRequest(HTTPMethod.POST, ["alloy", "sweep"], {}, {"folder": folder}, "e1")


@pytest.fixture
def root(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> pathlib.Path:
    monkeypatch.setenv("HPCAGENT_BENCH_SHARED_DIR", str(tmp_path / "shared"))
    folder = agent_root("e1")
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def test_each_scope_unit_is_copied_under_its_symbol(root: pathlib.Path, tmp_path: pathlib.Path):
    scopes = root / "best" / "scopes"
    scopes.mkdir(parents=True)
    (scopes / "scale_0.c").write_text("void scale_0(void) {}\n")
    (scopes / "notes.md").write_text("not a unit\n")

    sut = copied_units(request("best"), tmp_path / "copies")

    assert list(sut) == ["scale_0"]
    assert pathlib.Path(sut["scale_0"]).read_text() == "void scale_0(void) {}\n"


def test_a_unit_linked_out_of_the_agents_folder_is_refused(root: pathlib.Path, tmp_path: pathlib.Path):
    outside = tmp_path / "other_agent.c"
    outside.write_text("void scale_0(void) {}\n")
    scopes = root / "best" / "scopes"
    scopes.mkdir(parents=True)
    (scopes / "scale_0.c").symlink_to(outside)

    with pytest.raises(ValueError, match="must live in"):
        copied_units(request("best"), tmp_path / "copies")


@pytest.mark.parametrize("folder", ["", "missing"])
def test_a_folder_without_scope_units_is_refused(root: pathlib.Path, tmp_path: pathlib.Path, folder: str):
    with pytest.raises(ValueError, match="name the edited folder|no scopes"):
        copied_units(request(folder), tmp_path / "copies")
