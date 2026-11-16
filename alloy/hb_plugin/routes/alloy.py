# Copyright 2026 ETH Zurich and the Alloy authors.
"""``POST /alloy/<mode>``: the judge half of the ``alloy_profile`` and ``alloy_speculative`` tools. Alloy runs in a
spawned process of its own (the judge's threads never fork) while the call holds a device slot, so profile mode times
alone. The agent's own mistake (a kernel Alloy cannot take) answers 400; Alloy failing is the judge's fault (500)."""

import concurrent.futures
import multiprocessing
import pathlib
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping
from http import HTTPMethod, HTTPStatus

from hpcagent_bench import config
from hpcagent_bench.harness.judge_wire import JudgeAnswer, JudgeError
from hpcagent_bench.harness.native_call import grading_cpus
from hpcagent_bench.harness.routes import Judge, RouteRequest, route
from hpcagent_bench.harness.sandbox import agent_root
from hpcagent_bench.harness.service import JUDGE_FAULT_CAUSE
from hpcagent_bench.plugins import openmp_environment
from hpcagent_bench.precision import precision_from_datatype
from hpcagent_bench.spec import BenchSpec
from hpcagent_bench.support.bindings.contract import graded_datatype

from alloy.api import NothingToGenerate
from alloy.hb_plugin.adapter import running_sizes
from alloy.hb_plugin.episode import ToolCall, append_tool_call, file_hash
from alloy.hb_plugin.workbench import CodegenAnswer, CodegenRequest, codegen
from alloy.machine import pin_worker
from alloy.report import Mode

ROUTE = "alloy"
#: The route of the ``alloy_isa`` tool: a table query, outside the modes and the device slot.
ISA = "isa"
ISA_COMMANDS = frozenset(
    {"lookup", "reverse", "assist", "kernel", "tiers", "time", "schedule", "skeleton", "ops", "isas", "host"}
)
MODES = (Mode.PROFILE.value, Mode.SPECULATIVE.value)
ISA_TIMEOUT = 120  # seconds; a query compiles at most a few kernels
#: The characters of an argument a tool record keeps.
ARGUMENT_CHARS = 200


class AlloyAnswer(JudgeAnswer):
    result: CodegenAnswer


class IsaAnswer(JudgeAnswer):
    result: str


Outcome = tuple[HTTPStatus, JudgeAnswer, CodegenAnswer | None]


def isa_query(body: Mapping[str, object]) -> Outcome:
    """``python -m alloy.isa``, in a process of its own: the judge's threads share stdout. Exit code 3 is an answer."""
    command, arguments = body.get("command"), body.get("arguments") or []
    if command not in ISA_COMMANDS or not isinstance(arguments, list):
        return HTTPStatus.BAD_REQUEST, JudgeError(error=f"alloy_isa: no query {command!r}"), None
    argv = [sys.executable, "-m", "alloy.isa", str(command), *(str(a) for a in arguments)]
    if any("\0" in word for word in argv):
        return HTTPStatus.BAD_REQUEST, JudgeError(error="alloy_isa: a NUL byte in an argument"), None
    try:
        run = subprocess.run(argv, capture_output=True, text=True, check=False, timeout=ISA_TIMEOUT)
    except subprocess.TimeoutExpired:
        error = f"alloy_isa: no answer in {ISA_TIMEOUT} s"
        return HTTPStatus.INTERNAL_SERVER_ERROR, JudgeError(error=error, cause=JUDGE_FAULT_CAUSE), None
    if run.returncode not in (0, 3):
        return HTTPStatus.BAD_REQUEST, JudgeError(error=f"alloy_isa: {run.stderr.strip()}"), None
    return HTTPStatus.OK, IsaAnswer(result=run.stdout + run.stderr), None


def generate(judge: Judge, request: RouteRequest, spelled: str) -> Outcome | None:
    """Alloy in mode ``spelled`` on the request's kernel; ``None`` when no device slot was granted (the judge has
    answered)."""
    kernel = str(request.body.get("kernel") or "")
    parent = agent_root(request.episode_id) / ROUTE / spelled / kernel.replace("/", "_")
    parent.mkdir(parents=True, exist_ok=True)
    spec = BenchSpec.load(kernel)
    precision = precision_from_datatype(graded_datatype(spec, judge.cfg.datatype))
    running = running_sizes(spec, config.current().service.preset)
    with judge.device_slot() as slot:
        if slot is None:
            return None
        # each call answers from a folder of its own: a repeat never pulls the files from under a running one
        folder = tempfile.mkdtemp(prefix="run", dir=parent)
        language = str(request.body.get("language") or "c")
        call = CodegenRequest(
            kernel=kernel, mode=Mode(spelled), precision=precision, folder=folder, running=running, language=language
        )
        spawn = multiprocessing.get_context("spawn")
        cpus = grading_cpus(slot.index)  # the slot's cores only, as a graded child; empty = unreadable, unpinned
        with concurrent.futures.ProcessPoolExecutor(
            1, mp_context=spawn, initializer=pin_worker, initargs=(cpus,)
        ) as pool:
            try:
                with openmp_environment("alloy"):  # the worker starts, in libomp's context, at the first submit
                    future = pool.submit(codegen, call)
                answer = future.result()
            except NothingToGenerate as err:
                return HTTPStatus.BAD_REQUEST, JudgeError(error=f"alloy_{spelled}: {err}"), None
            except Exception as err:
                error = f"alloy_{spelled}: {type(err).__name__}: {err}"
                return HTTPStatus.INTERNAL_SERVER_ERROR, JudgeError(error=error, cause=JUDGE_FAULT_CAUSE), None
    return HTTPStatus.OK, AlloyAnswer(result=answer), answer


def answered_units(answer: CodegenAnswer) -> dict[str, str]:
    """The SHA-256 of every source unit an answer returns: each scope's source and the program calling them."""
    best = pathlib.Path(answer.folder)
    return {unit: file_hash(best / unit) for unit in (*(scope.source for scope in answer.scopes), "program.c")}


def tool_call(tool: str, body: Mapping[str, object], seconds: float, outcome: Outcome) -> ToolCall:
    """The record of one call: its scalar arguments only (an agent's text never enters the record)."""
    status, _, answer = outcome
    arguments = {
        key: str(value)[:ARGUMENT_CHARS] for key, value in body.items() if isinstance(value, str | int | float | list)
    }
    library = file_hash(pathlib.Path(answer.library)) if answer is not None else ""
    units = answered_units(answer) if answer is not None else {}
    return ToolCall(tool, arguments, seconds, status == HTTPStatus.OK, library, units)


@route(ROUTE, methods=(HTTPMethod.POST,))
def serve(judge: Judge, request: RouteRequest) -> None:
    started = time.monotonic()
    spelled = request.parts[1] if len(request.parts) > 1 else ""
    if spelled not in (ISA, *MODES):
        error = f"no Alloy mode {spelled!r}; modes: {sorted(MODES)}"
        return judge.reply(HTTPStatus.NOT_FOUND, JudgeError(error=error))
    outcome = isa_query(request.body) if spelled == ISA else generate(judge, request, spelled)
    if outcome is None:
        return None
    call = tool_call(f"alloy_{spelled}", request.body, time.monotonic() - started, outcome)
    try:
        append_tool_call(agent_root(request.episode_id), call)
    except (OSError, ValueError) as exc:  # a flat-layout run has no episode folder; the answer still goes out
        print(f"alloy: tool call {call.tool} not recorded: {exc}", file=sys.stderr, flush=True)
    return judge.reply(outcome[0], outcome[1])
