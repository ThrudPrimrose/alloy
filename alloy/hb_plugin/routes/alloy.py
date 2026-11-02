# Copyright 2026 ETH Zurich and the Alloy authors.
"""``POST /alloy/<mode>``: the judge half of the ``alloy_profile`` and ``alloy_speculative`` tools. Alloy runs in a
spawned process of its own (the judge's threads never fork) while the call holds a device slot, so profile mode times
alone. The agent's own mistake (a kernel Alloy cannot take) answers 400; Alloy failing is the judge's fault (500)."""

import concurrent.futures
import multiprocessing
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from http import HTTPMethod, HTTPStatus

from hpcagent_bench import config
from hpcagent_bench.harness.judge_wire import JudgeAnswer, JudgeError
from hpcagent_bench.harness.routes import Judge, RouteRequest, route
from hpcagent_bench.harness.sandbox import agent_root
from hpcagent_bench.harness.service import JUDGE_FAULT_CAUSE
from hpcagent_bench.plugins import openmp_environment
from hpcagent_bench.precision import precision_from_datatype
from hpcagent_bench.spec import BenchSpec
from hpcagent_bench.support.bindings.contract import graded_datatype

from alloy.api import NothingToGenerate
from alloy.hb_plugin.adapter import running_sizes
from alloy.hb_plugin.workbench import CodegenAnswer, CodegenRequest, codegen
from alloy.report import Mode

ROUTE = "alloy"
#: The route of the ``alloy_isa`` tool: a table query, outside the modes and the device slot.
ISA = "isa"
ISA_COMMANDS = frozenset(
    {"lookup", "reverse", "assist", "kernel", "tiers", "schedule", "skeleton", "ops", "isas", "host"}
)
MODES = (Mode.PROFILE.value, Mode.SPECULATIVE.value)
ISA_TIMEOUT = 120  # seconds; a query compiles at most a few kernels


class AlloyAnswer(JudgeAnswer):
    result: CodegenAnswer


class IsaAnswer(JudgeAnswer):
    result: str


def isa_query(judge: Judge, body: Mapping[str, object]) -> None:
    """``python -m alloy.isa``, in a process of its own: the judge's threads share stdout. Exit code 3 is an answer."""
    command, arguments = body.get("command"), body.get("arguments") or []
    if command not in ISA_COMMANDS or not isinstance(arguments, list):
        return judge.reply(HTTPStatus.BAD_REQUEST, JudgeError(error=f"alloy_isa: no query {command!r}"))
    argv = [sys.executable, "-m", "alloy.isa", str(command), *(str(a) for a in arguments)]
    if any("\0" in word for word in argv):
        return judge.reply(HTTPStatus.BAD_REQUEST, JudgeError(error="alloy_isa: a NUL byte in an argument"))
    try:
        run = subprocess.run(argv, capture_output=True, text=True, check=False, timeout=ISA_TIMEOUT)
    except subprocess.TimeoutExpired:
        error = f"alloy_isa: no answer in {ISA_TIMEOUT} s"
        return judge.reply(HTTPStatus.INTERNAL_SERVER_ERROR, JudgeError(error=error, cause=JUDGE_FAULT_CAUSE))
    if run.returncode not in (0, 3):
        return judge.reply(HTTPStatus.BAD_REQUEST, JudgeError(error=f"alloy_isa: {run.stderr.strip()}"))
    return judge.reply(HTTPStatus.OK, IsaAnswer(result=run.stdout + run.stderr))


@route(ROUTE, methods=(HTTPMethod.POST,))
def serve(judge: Judge, request: RouteRequest) -> None:
    spelled = request.parts[1] if len(request.parts) > 1 else ""
    if spelled == ISA:
        return isa_query(judge, request.body)
    if spelled not in MODES:
        error = f"no Alloy mode {spelled!r}; modes: {sorted(MODES)}"
        return judge.reply(HTTPStatus.NOT_FOUND, JudgeError(error=error))
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
        call = CodegenRequest(kernel=kernel, mode=Mode(spelled), precision=precision, folder=folder, running=running)
        spawn = multiprocessing.get_context("spawn")
        with concurrent.futures.ProcessPoolExecutor(1, mp_context=spawn) as pool:
            try:
                with openmp_environment("alloy"):  # the worker starts, in libomp's context, at the first submit
                    future = pool.submit(codegen, call)
                answer = future.result()
            except NothingToGenerate as err:
                return judge.reply(HTTPStatus.BAD_REQUEST, JudgeError(error=f"alloy_{spelled}: {err}"))
            except Exception as err:
                error = f"alloy_{spelled}: {type(err).__name__}: {err}"
                return judge.reply(HTTPStatus.INTERNAL_SERVER_ERROR, JudgeError(error=error, cause=JUDGE_FAULT_CAUSE))
    return judge.reply(HTTPStatus.OK, AlloyAnswer(result=answer))
