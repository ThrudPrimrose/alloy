# Copyright 2026 ETH Zurich and the Alloy authors.
"""alloy_isa restricted to the task's target: the per-target packets set the env, the tool refuses other targets."""

import tomllib
from importlib import resources
from typing import Any

import pytest

pytest.importorskip("hpcagent_agent", reason="the agent tools need the bench extra")

from hpcagent_agent.tools import http_json

from alloy.hb_plugin.tools import alloy


@pytest.fixture
def posted(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    sent: list[dict[str, Any]] = []

    def post_judge(path: str, body: dict[str, Any]) -> dict[str, Any]:
        sent.append(body)
        return {"ok": True, "result": "row"}

    monkeypatch.setattr(http_json, "post_judge", post_judge)
    return sent


@pytest.mark.parametrize("target", ["tensix", "softhier"])
def test_each_target_packet_restricts_the_tool_to_its_target(target: str) -> None:
    packets = tomllib.loads(resources.files("alloy.hb_plugin").joinpath("plugin.toml").read_text())["packets"]
    packet = packets[f"alloy-isa-{target}"]
    assert packet["extends"] == "alloy-isa"
    assert packet["env"] == {alloy.TARGETS_ENV: target}


def test_a_restricted_tool_answers_its_target_and_refuses_the_others(
    monkeypatch: pytest.MonkeyPatch, posted: list[dict[str, Any]]
) -> None:
    monkeypatch.setenv(alloy.TARGETS_ENV, "tensix")
    own = {"command": "lookup", "arguments": ["tensix", "exp", "f32"]}
    assert alloy.isa_query(own) == {"ok": True, "result": "row"}
    assert alloy.isa_query({"command": "ops"})["ok"]
    for query in (
        {"command": "lookup", "arguments": ["avx512", "exp", "f64"]},
        {"command": "ask", "arguments": ["sm90", "mma"]},
        {"command": "reverse", "arguments": ["vfmadd231pd"]},
        {"command": "isas"},
        {"command": "tile", "arguments": []},
    ):
        answer = alloy.isa_query(query)
        assert answer["ok"] is False and "tensix" in answer["error"], query
    assert posted == [own, {"command": "ops"}]


def test_an_unrestricted_tool_answers_every_target(
    monkeypatch: pytest.MonkeyPatch, posted: list[dict[str, Any]]
) -> None:
    monkeypatch.delenv(alloy.TARGETS_ENV, raising=False)
    query = {"command": "reverse", "arguments": ["vfmadd231pd"]}
    assert alloy.isa_query(query)["ok"]
    assert posted == [query]
