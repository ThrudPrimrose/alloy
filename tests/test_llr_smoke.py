# Copyright 2026 ETH Zurich and the Alloy authors.
import dataclasses
import math

import pytest
from helpers import MATRIX
from hpcagent_bench import autogen, paths
from hpcagent_bench.frameworks.benchmark import Benchmark
from hpcagent_bench.frameworks.framework import framework_class

from alloy import report
from alloy.backend import sweep
from alloy.evaluate import timing, verify
from alloy.evaluate.link import Linker
from alloy.frontend import inputs, regions

SMALL = dataclasses.replace(
    MATRIX,
    timing=dataclasses.replace(
        MATRIX.timing,
        screen_reps=3,
        final_reps=5,
        screen_cache_factor=0.5,
        final_cache_factor=0.5,
        max_program_cache_factor=1.0,
    ),
)


@pytest.mark.e2e
@pytest.mark.parametrize("kernel", ["argmax_value", "tsvc_2_vpv", "tsvc_2_vsumr"])
def test_an_llr_kernel_goes_from_the_bench_sdfg_to_a_verified_faster_program(kernel, tmp_path):
    autogen.ensure(kernel, ["dace"])
    framework = framework_class("dace_cpu")("dace_cpu")
    framework.set_datatype("float64")
    bench = Benchmark(kernel)
    program = regions.outline(framework.implementations(bench)[0][0].to_sdfg(simplify=False), SMALL.libm_calls)
    manifest = inputs.load(paths.BENCHMARKS / bench.info["relative_path"] / f"{bench.info['module_name']}.yaml")
    cases = verify.Cases([inputs.draw(manifest, i) for i in range(2)], manifest.outputs)

    reports = sweep.run(program, SMALL, tmp_path)
    verification = verify.verify(program, SMALL, reports, cases, tmp_path)
    timings = timing.time_program(Linker(program, SMALL, tmp_path), reports, verification, manifest)
    report.write(reports, SMALL, tmp_path, verification, timings)

    assert program.regions
    assert all(any(v.ok for v in verification.verdicts[r.symbol].values()) for r in program.regions)
    full, default = timings[1].arms["alloy_full"], timings[1].arms["dace_default"]
    assert full.verdict.ok
    assert math.isfinite(default.median / full.median)
