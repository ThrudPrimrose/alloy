# Copyright 2026 ETH Zurich and the Alloy authors.
"""One ``python -m alloy.isa`` query in a process of its own: what the ``alloy_isa`` tool answers, on the bench's
judge (:mod:`alloy.hb_plugin.routes.alloy`) and on Alloy's own MCP server (:mod:`alloy.mcpserver`)."""

import subprocess
import sys
from typing import Literal, get_args

Command = Literal[
    "lookup", "reverse", "assist", "kernel", "tiers", "time", "schedule", "skeleton", "ops", "isas", "host", "tile",
    "ask", "ask-all",
]  # fmt: skip
COMMANDS = frozenset(get_args(Command))
#: Exit codes that are answers, by command: ``ask`` exits 2 when the target cannot (the refusal with its block,
#: nearest requests, and fix is the answer); the other queries exit 3 for an answer that is no row.
ANSWER_CODES = {"ask": (0, 2), "ask-all": (0, 2)}
TIMEOUT = 120  # seconds; a query compiles at most a few kernels

#: What the tool tells the model.
DESCRIPTION = (
    "The intrinsics reference: `kernel` returns sin, exp, log, pow, fmod and more as C intrinsics at strict, relaxed "
    "and fast levels; `tiers` lists a function's polynomial depths with their error, for picking one; `time` "
    "measures what an element costs here with each kernel and library call; `lookup` spells "
    "an op for an ISA and dtype; `reverse` names what an intrinsic, a mnemonic or a pasted disassembly line computes; "
    "`skeleton` gives a loop in a legal schedule; `host` says which ISAs this machine runs. `ask` answers one "
    'operation on logical data for any target (CPU, sm90, gfx942, gfx90a, tensix), e.g. ["avx512", "reduce_add", '
    '"--x", "vector:f32:96"]: feasible with its steps, or refused with the block the target takes, the nearest '
    "requests, and a fix; `ask-all` combines requests into one kernel. `lookup`, `kernel` and "
    "`skeleton` answers carry their check: `run` names where it ran (this machine, a recorded GPU run, or ttsim), "
    "`compiled` means built and not run, and `unverified` neither."
)


class QueryError(ValueError):
    """The query is not one ``alloy.isa`` answers (the caller's mistake)."""


def answer(command: object, arguments: object) -> str:
    """The query's answer text. Raises :class:`QueryError` for a query the CLI refuses and ``TimeoutExpired`` past
    :data:`TIMEOUT`."""
    if command not in COMMANDS or not isinstance(arguments, list):
        raise QueryError(f"alloy_isa: no query {command!r}")
    argv = [sys.executable, "-m", "alloy.isa", str(command), *(str(a) for a in arguments)]
    if any("\0" in word for word in argv):
        raise QueryError("alloy_isa: a NUL byte in an argument")
    run = subprocess.run(argv, capture_output=True, text=True, check=False, timeout=TIMEOUT)
    if run.returncode not in ANSWER_CODES.get(str(command), (0, 3)):  # ask prints an invalid request's reason to stdout
        raise QueryError(f"alloy_isa: {(run.stderr or run.stdout).strip()}")
    return run.stdout + run.stderr
