# Copyright 2026 ETH Zurich and the Alloy authors.
"""Alloy's optimizer flavors: they tune a DaCe pipeline's SDFG and deliver the library the judge grades."""

from hpcagent_agent.tools import http_json
from hpcagent_bench.harness.envelope import Submission
from hpcagent_bench.harness.optimizers import FlavorOptimizer
from hpcagent_bench.harness.task import Task

__all__ = ["AlloyProfileOptimizer", "AlloyReferenceOptimizer", "AlloySpeculativeOptimizer", "AlloyToolStub"]


class AlloyProfileOptimizer(FlavorOptimizer):
    """Profile mode: candidates verified locally, timed by the judge, the chosen one scored."""

    __slots__ = ()

    def tune(self, task: Task, pipeline: str) -> Submission:
        from alloy.hb_plugin import adapter

        return adapter.optimize(task, pipeline, lambda code, link: self.deliver(task, code, link))


class AlloyReferenceOptimizer(FlavorOptimizer):
    """No Alloy: the pipeline's default rendering, the baseline both modes are measured against."""

    __slots__ = ()

    def tune(self, task: Task, pipeline: str) -> Submission:
        from alloy.hb_plugin import adapter

        return adapter.reference(task, pipeline, lambda code, link: self.deliver(task, code, link))


class AlloySpeculativeOptimizer(FlavorOptimizer):
    """Speculative mode: every scope's predicted pick, verified locally and never timed, scored once."""

    __slots__ = ()

    def tune(self, task: Task, pipeline: str) -> Submission:
        from alloy.hb_plugin import adapter

        return adapter.speculative(task, pipeline, lambda code, link: self.deliver(task, code, link))


class AlloyToolStub(FlavorOptimizer):
    """``alloy_stub``: CI's stand-in for an agent, calling the ``alloy-speculative`` tool once."""

    __slots__ = ()

    def tune(self, task: Task, pipeline: str) -> Submission:
        answer = http_json.post_judge("/alloy/speculative", {"kernel": task.kernel})
        if "error" in answer:
            raise RuntimeError(f"alloy_speculative: {answer['error']}")
        result = answer["result"]
        return Submission(
            language=task.language, library=str(result["library"]), workspace_bytes=str(result["workspace_bytes"])
        )
