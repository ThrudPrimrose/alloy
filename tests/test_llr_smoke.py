# Copyright 2026 ETH Zurich and the Alloy authors.
import dataclasses
import math

import pytest
from helpers import MATRIX
from hpcagent_bench import autogen, paths
from hpcagent_bench.frameworks.benchmark import Benchmark
from hpcagent_bench.frameworks.framework import framework_class

from alloy import api
from alloy.frontend import inputs

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
    sdfg = framework.implementations(bench)[0][0].to_sdfg(simplify=False)
    manifest = inputs.load(paths.BENCHMARKS / bench.info["relative_path"] / f"{bench.info['module_name']}.yaml")

    sut = api.generate(sdfg, tmp_path, manifest=manifest, matrix=SMALL)

    assert sut.regions and sut.verification is not None and sut.timings is not None
    assert all(any(v.ok for v in sut.verification.verdicts[r.region.symbol].values()) for r in sut.regions)
    full, default = sut.timings[1].arms["alloy_full"], sut.timings[1].arms["dace_default"]
    assert full.verdict.ok
    assert math.isfinite(default.median / full.median)
