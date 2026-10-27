# Copyright 2026 ETH Zurich and the Alloy authors.
"""Alloy's optimizer flavor: it tunes the SDFG of the extended column's DaCe pipeline and delivers the library the
judge grades."""

from hpcagent_agent.tools import http_json
from hpcagent_bench.harness.envelope import Submission
from hpcagent_bench.harness.optimizers import FlavorOptimizer
from hpcagent_bench.harness.task import Task

__all__ = ["AlloyProfileOptimizer", "AlloySpeculativeOptimizer", "AlloyToolStub"]


class AlloyProfileOptimizer(FlavorOptimizer):
    """Alloy's profile mode: candidates verified locally and timed by the judge via ``/profile``, the chosen one
    scored."""

    __slots__ = ()

    def tune(self, task: Task, pipeline: str) -> Submission:
        from alloy.hb_plugin import adapter  # noqa: PLC0415 -- dace and the build stack load on first tune

        return adapter.optimize(task, pipeline, lambda code, link: self.deliver(task, code, link))


class AlloySpeculativeOptimizer(FlavorOptimizer):
    """Alloy's speculative mode: every scope's predicted pick (heuristics, llvm-mca, roofline), verified locally and
    never timed, the selection scored once."""

    __slots__ = ()

    def tune(self, task: Task, pipeline: str) -> Submission:
        from alloy.hb_plugin import adapter  # noqa: PLC0415 -- dace and the build stack load on first tune

        return adapter.speculative(task, pipeline, lambda code, link: self.deliver(task, code, link))


class AlloyToolStub(FlavorOptimizer):
    """``alloy_stub``: the benchmark's CI stand-in for an LLM agent on the ``alloy-speculative`` packet. It calls the
    packet's tool (``POST /alloy/speculative`` under the episode's identity) once and returns the library it built."""

    __slots__ = ()

    def tune(self, task: Task, pipeline: str) -> Submission:
        answer = http_json.post_judge("/alloy/speculative", {"kernel": task.kernel})
        if "error" in answer:
            raise RuntimeError(f"alloy_speculative: {answer['error']}")
        result = answer["result"]
        return Submission(
            language=task.language, library=str(result["library"]), workspace_bytes=str(result["workspace_bytes"])
        )
