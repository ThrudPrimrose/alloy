# Copyright 2026 ETH Zurich and the Alloy authors.
import asyncio
import pathlib
import sys

import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import TextContent

from alloy import mcpserver
from helpers import REDUCTIONS, gcc_only


def call(name: str, arguments: dict[str, object]) -> object:
    return asyncio.run(mcpserver.server.call_tool(name, arguments))


def test_a_client_over_stdio_sees_every_alloy_tool_and_reads_an_isa_answer_off_a_clean_stream() -> None:
    async def session() -> tuple[list[str], str]:
        params = StdioServerParameters(command=sys.executable, args=["-m", "alloy.mcpserver"])
        async with stdio_client(params) as (read, write), ClientSession(read, write) as client:
            await client.initialize()
            names = [tool.name for tool in (await client.list_tools()).tools]
            answer = await client.call_tool("alloy_isa", {"command": "lookup", "arguments": ["avx2", "fma", "f64"]})
            (text,) = answer.content
            assert isinstance(text, TextContent)
            return names, text.text

    names, text = asyncio.run(session())

    assert names == ["alloy_profile", "alloy_speculative", "alloy_reference", "alloy_sweep", "alloy_isa"]
    assert "_mm256_fmadd_pd" in text


def test_an_isa_query_the_cli_refuses_is_the_callers_error() -> None:
    with pytest.raises(ToolError, match="alloy_isa"):
        call("alloy_isa", {"command": "lookup", "arguments": ["avx2", "no_such_op", "f64"]})


def test_speculative_mode_on_a_dace_program_links_a_verified_pick_with_a_makefile(tmp_path: pathlib.Path) -> None:
    matrix = gcc_only(tmp_path).path
    out = tmp_path / "out"

    answer = mcpserver.run(mcpserver.Mode.SPECULATIVE, f"{REDUCTIONS}:scale", str(out), matrix=str(matrix))

    assert answer["picks"] and answer["best"] == str(out / "best")
    assert (out / "best" / "Makefile").is_file() and pathlib.Path(answer["report"]).is_file()


def test_a_program_that_names_no_dace_program_is_the_callers_error(tmp_path: pathlib.Path) -> None:
    with pytest.raises(ToolError, match="not a @dace.program"):
        mcpserver.run(mcpserver.Mode.SPECULATIVE, f"{REDUCTIONS}:np", str(tmp_path / "out"))
