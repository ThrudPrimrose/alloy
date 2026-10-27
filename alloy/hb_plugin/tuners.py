# Copyright 2026 ETH Zurich and the Alloy authors.
"""Alloy's optimizer flavor: it tunes the SDFG of the extended column's DaCe pipeline and delivers the library the
judge grades."""

from hpcagent_bench.harness.envelope import Submission
from hpcagent_bench.harness.optimizers import FlavorOptimizer
from hpcagent_bench.harness.task import Task

__all__ = ["AlloyProfileOptimizer", "AlloySpeculativeOptimizer"]


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
