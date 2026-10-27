# Copyright 2026 ETH Zurich and the Alloy authors.
"""``POST /alloy/<mode>``: the judge half of the ``alloy_profile`` and ``alloy_speculative`` tools. Alloy runs in a
spawned process of its own (the judge's threads never fork) while the call holds a device slot, so profile mode times
alone. The agent's own mistake (a kernel Alloy cannot take) answers 400; Alloy failing is the judge's fault (500)."""

import concurrent.futures
import multiprocessing
import pathlib
import shutil
from http import HTTPMethod, HTTPStatus

from hpcagent_bench.harness.judge_wire import JudgeAnswer, JudgeError
from hpcagent_bench.harness.routes import Judge, RouteRequest, route
from hpcagent_bench.harness.sandbox import shared_dir
from hpcagent_bench.harness.service import JUDGE_FAULT_CAUSE
from hpcagent_bench.precision import precision_from_datatype

from alloy.hb_plugin.workbench import CodegenAnswer, CodegenRequest, codegen
from alloy.report import Mode

ROUTE = "alloy"


class AlloyAnswer(JudgeAnswer):
    result: CodegenAnswer


@route(ROUTE, methods=(HTTPMethod.POST,))
def serve(judge: Judge, request: RouteRequest) -> None:
    spelled = request.parts[1] if len(request.parts) > 1 else ""
    if spelled not in {mode.value for mode in Mode}:
        error = f"no Alloy mode {spelled!r}; modes: {sorted(mode.value for mode in Mode)}"
        return judge.reply(HTTPStatus.NOT_FOUND, JudgeError(error=error))
    kernel = str(request.body.get("kernel") or "")
    folder = pathlib.Path(shared_dir()) / ROUTE / request.episode_id / spelled / kernel.replace("/", "_")
    shutil.rmtree(folder, ignore_errors=True)  # each call answers from a fresh folder
    call = CodegenRequest(
        kernel=kernel, mode=Mode(spelled), precision=precision_from_datatype(judge.cfg.datatype), folder=str(folder)
    )
    with judge.device_slot() as slot:
        if slot is None:
            return None
        spawn = multiprocessing.get_context("spawn")
        with concurrent.futures.ProcessPoolExecutor(1, mp_context=spawn) as pool:
            try:
                answer = pool.submit(codegen, call).result()
            except ValueError as err:
                return judge.reply(HTTPStatus.BAD_REQUEST, JudgeError(error=f"alloy_{spelled}: {err}"))
            except Exception as err:  # noqa: BLE001 -- any other failure is Alloy's, reported as the judge's fault
                error = f"alloy_{spelled}: {type(err).__name__}: {err}"
                return judge.reply(HTTPStatus.INTERNAL_SERVER_ERROR, JudgeError(error=error, cause=JUDGE_FAULT_CAUSE))
    return judge.reply(HTTPStatus.OK, AlloyAnswer(result=answer))
