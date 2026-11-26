# Copyright 2026 ETH Zurich and the Alloy authors.
"""A mock agent drives ``alloy-mcp`` over stdio as an MCP client would: it lists the tools, asks the ISA reference,
takes the reference C, edits a scope, sweeps the edit, and builds the program the answer points it to."""

import asyncio
import os
import pathlib
import subprocess
import sys
from typing import Any

import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.types import CallToolResult, TextContent

from alloy import report
from helpers import REDUCTIONS, SCALE_MANIFEST, gcc_only


def answer(result: CallToolResult) -> Any:
    """What the agent reads: the structured answer, else the text; a tool error fails the episode."""
    assert not result.is_error, result.content
    if result.structured_content is not None:
        return result.structured_content.get("result", result.structured_content)
    (text,) = result.content
    assert isinstance(text, TextContent)
    return text.text


async def episode(tmp_path: pathlib.Path, manifest: pathlib.Path, matrix: pathlib.Path) -> dict[str, Any]:
    """One scripted agent: every step through the protocol, nothing through Alloy's Python API."""
    program = f"{REDUCTIONS}:scale"
    # the server imports this checkout's alloy, as the test does
    params = StdioServerParameters(command=sys.executable, args=["-m", "alloy.mcpserver"], env=dict(os.environ))
    async with stdio_client(params) as (read, write), ClientSession(read, write) as client:
        await client.initialize()
        tools = [tool.name for tool in (await client.list_tools()).tools]
        isa = answer(await client.call_tool("alloy_isa", {"command": "lookup", "arguments": ["avx2", "fma", "f64"]}))
        reference = answer(
            await client.call_tool(
                "alloy_reference", {"program": program, "out": str(tmp_path / "reference"), "matrix": str(matrix)}
            )  # fmt: skip
        )
        (unit,) = (pathlib.Path(reference["best"]) / "scopes").glob("*.c")
        text = unit.read_text()
        assert "2.0" in text, "the rendered scope multiplies by 2.0"
        unit.write_text(text.replace("2.0", "(1.0 + 1.0)"))  # the agent's edit: the same value, spelled otherwise
        swept = answer(
            await client.call_tool(
                "alloy_sweep",
                {
                    "program": program,
                    "folder": reference["best"],
                    "out": str(tmp_path / "swept"),
                    "manifest": str(manifest),
                    "matrix": str(matrix),
                },
            )  # fmt: skip
        )
    return {"tools": tools, "isa": isa, "unit": unit.stem, "swept": swept}


@pytest.mark.gcc
def test_an_agent_over_stdio_edits_the_reference_c_sweeps_it_and_builds_the_answer(tmp_path: pathlib.Path) -> None:
    manifest = tmp_path / "scale.yaml"
    manifest.write_text(SCALE_MANIFEST)
    matrix = gcc_only(tmp_path).path

    sut = asyncio.run(episode(tmp_path, manifest, matrix))

    assert sut["tools"] == ["alloy_profile", "alloy_speculative", "alloy_reference", "alloy_sweep", "alloy_isa"]
    assert "_mm256_fmadd_pd" in sut["isa"]
    swept = sut["swept"]
    (scope,) = report.load(pathlib.Path(swept["report"]).with_suffix(".json")).scopes
    edited = [v for v in scope.top if v.name.startswith("agent_")]
    assert swept["picks"].keys() == {sut["unit"]}
    assert edited and all(v.correctness is not None and v.correctness.status == "exact" for v in edited)
    built = subprocess.run(["make", "-C", swept["best"]], capture_output=True, text=True, check=False)
    assert built.returncode == 0, built.stderr[-2000:]
