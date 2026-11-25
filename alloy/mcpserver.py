# Copyright 2026 ETH Zurich and the Alloy authors.
"""Alloy as an MCP server: the tools an HPCAgent-Bench agent gets (``alloy_profile``, ``alloy_speculative``,
``alloy_reference``, ``alloy_sweep``, ``alloy_isa``) for any MCP client, on this machine, outside the bench.

    pip install 'dace-alloy[mcp]'           # [mcp,bench] for profile mode and manifests
    alloy-mcp                               # stdio; e.g. `claude mcp add alloy -- alloy-mcp`

A program is a ``@dace.program`` named ``file.py:function`` or a saved ``.sdfg``; C goes through
``python -m alloy.frontend.cnumpy`` first. Each code-generation call runs :func:`alloy.api.generate` in a spawned
process whose stdout is the server's stderr, so compiler and worker output never reach the protocol stream.
"""

import concurrent.futures
import importlib.util
import multiprocessing
import os
import pathlib
import subprocess
from typing import TYPE_CHECKING, Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from alloy.isa import query
from alloy.report import Mode

if TYPE_CHECKING:
    import dace

__all__ = ["main", "server"]

PROGRAM = (
    "`program`: a @dace.program as `file.py:function`, or a saved `.sdfg` file. `out`: the folder Alloy writes "
    "(created). `manifest`: an HPCAgent-Bench style YAML with the sizes and inputs (needs dace-alloy[bench]); without "
    "one, candidates are verified on draws derived from the program when any input value is valid. `finite_inputs`: "
    "no input is NaN or Inf, which opens the FP levels that need it. `matrix`: a configuration matrix TOML in place "
    "of the shipped one (which compilers, FP levels and flags to sweep)."
)
ANSWER = (
    " Answers with the report path (report.md, every scope's candidates and verdicts), the `best/` folder (each "
    "scope's chosen source, program.c and a Makefile: run `make` there to build the shared library), each scope's "
    "pick, and advice for the scopes Alloy left short."
)
MODES = {
    Mode.PROFILE: "Every scope of the program rendered under every compiler, FP level, vector library and ISA flag "
    "set, each candidate verified, the survivors timed on this machine, and each scope's fastest linked. Needs a "
    "manifest (the sizes it times at). ",
    Mode.SPECULATIVE: "Every scope's candidates built and verified, and each scope's predicted best linked, untimed: "
    "fast, for a first pick. `running` (symbol -> size) ranks the builds at the sizes the program will run at. ",
    Mode.REFERENCE: "The program's default C from DaCe, one translation unit per scope at the compilers' defaults, "
    "nothing swept: the starting point to edit (then `alloy_sweep`). ",
}
SWEEP = (
    "Profile mode over your edits: each `scopes/<symbol>.c` (or .cpp) under `folder` (a `best/` folder an earlier "
    "answer gave, edited in place) is compiled with every configuration, verified against the program's own "
    "rendering, and timed. Keep each scope's function signature. "
)
#: A call writes a fresh folder and nothing else; a repeat gives the same.
WRITES = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False)
READS = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)
UNIT_SUFFIXES = (".c", ".cpp")

server = MCPServer("alloy", instructions="Alloy: verified per-scope code generation for DaCe programs, and a checked "
                   "intrinsics reference for CPU, GPU and Tensix targets.")  # fmt: skip


def stdout_to_stderr() -> None:
    """The worker's stdout is the protocol stream's neighbour: send it (and its children's) to stderr."""
    os.dup2(2, 1)


def loaded(program: str) -> "dace.SDFG":
    """The SDFG of ``program``: a ``.sdfg`` file or a ``@dace.program`` named ``file.py:function``."""
    import dace
    from dace.frontend.python.parser import DaceProgram

    if program.endswith(".sdfg"):
        return dace.SDFG.from_file(program)
    path, _, name = program.partition(":")
    spec = importlib.util.spec_from_file_location(pathlib.Path(path).stem, path)
    if not name or spec is None or spec.loader is None:
        raise ValueError(f"{program}: name a .sdfg file or a @dace.program as file.py:function")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    found = vars(module).get(name)
    if not isinstance(found, DaceProgram):
        raise ValueError(f"{program}: {name} is not a @dace.program in {path}")
    return found.to_sdfg()


def generated(mode: str, program: str, out: str, manifest: str | None, finite_inputs: bool,
              running: dict[str, int] | None, edited: str | None, matrix: str | None) -> dict[str, Any]:  # fmt: skip
    """:func:`alloy.api.generate` on ``program`` (the worker's body), as the tool's answer."""
    from alloy import api, configuration_matrix
    from alloy.frontend import inputs

    sources = {}
    if edited is not None:
        scopes = pathlib.Path(edited) / "scopes"
        sources = {unit.stem: unit for unit in sorted(scopes.glob("*")) if unit.suffix in UNIT_SUFFIXES}
        if not sources:
            raise ValueError(f"{edited}: no scopes/<symbol>.c or .cpp, the layout of a best/ folder")
    plan = inputs.load(pathlib.Path(manifest), program if ":" in program else None) if manifest else None
    swept = configuration_matrix.load(pathlib.Path(matrix)) if matrix else None
    result = api.generate(loaded(program), pathlib.Path(out), manifest=plan, matrix=swept, mode=Mode(mode),
                          finite_inputs=finite_inputs, running=running, sources=sources)  # fmt: skip
    best = pathlib.Path(out) / "best"
    return {
        "report": str(result.report),
        "best": str(best) if (best / "Makefile").is_file() else None,
        "picks": {symbol: build.name for symbol, build in (result.winners or {}).items()},
        "advice": result.advice or {},
    }


def run(mode: Mode, program: str, out: str, manifest: str | None = None, finite_inputs: bool = False,
        running: dict[str, int] | None = None, edited: str | None = None, matrix: str | None = None,
        ) -> dict[str, Any]:  # fmt: skip
    """``generated`` in a spawned worker; the caller's mistakes come back as a ``ToolError``."""
    spawn = multiprocessing.get_context("spawn")
    with concurrent.futures.ProcessPoolExecutor(1, mp_context=spawn, initializer=stdout_to_stderr) as pool:
        future = pool.submit(generated, mode.value, program, out, manifest, finite_inputs, running, edited, matrix)
        try:
            return future.result()
        except (ValueError, ImportError, FileNotFoundError) as err:  # api.NothingToGenerate and NotAScope included
            raise ToolError(f"alloy_{mode.value}: {err}") from err


@server.tool(description=MODES[Mode.PROFILE] + PROGRAM + ANSWER, annotations=WRITES)
def alloy_profile(program: str, out: str, manifest: str, finite_inputs: bool = False,
                  matrix: str | None = None) -> dict[str, Any]:  # fmt: skip
    return run(Mode.PROFILE, program, out, manifest, finite_inputs, matrix=matrix)


@server.tool(description=MODES[Mode.SPECULATIVE] + PROGRAM + ANSWER, annotations=WRITES)
def alloy_speculative(program: str, out: str, manifest: str | None = None, finite_inputs: bool = False,
                      running: dict[str, int] | None = None, matrix: str | None = None) -> dict[str, Any]:  # fmt: skip
    return run(Mode.SPECULATIVE, program, out, manifest, finite_inputs, running, matrix=matrix)


@server.tool(description=MODES[Mode.REFERENCE] + PROGRAM + ANSWER, annotations=WRITES)
def alloy_reference(program: str, out: str, manifest: str | None = None, matrix: str | None = None) -> dict[str, Any]:
    return run(Mode.REFERENCE, program, out, manifest, matrix=matrix)


@server.tool(description=SWEEP + PROGRAM + ANSWER, annotations=WRITES)
def alloy_sweep(program: str, folder: str, out: str, manifest: str, finite_inputs: bool = False,
                matrix: str | None = None) -> dict[str, Any]:  # fmt: skip
    return run(Mode.PROFILE, program, out, manifest, finite_inputs, edited=folder, matrix=matrix)


@server.tool(description=query.DESCRIPTION, annotations=READS)
def alloy_isa(command: query.Command, arguments: list[str] | None = None) -> str:
    """``arguments``: e.g. ["avx512", "sin", "f64"] for kernel, ["vfmadd231pd"] for reverse."""
    try:
        return query.answer(command, arguments or [])
    except query.QueryError as err:
        raise ToolError(str(err)) from err
    except subprocess.TimeoutExpired as err:
        raise ToolError(f"alloy_isa: no answer in {query.TIMEOUT} s") from err


def main() -> None:
    server.run()  # stdio


if __name__ == "__main__":
    main()
