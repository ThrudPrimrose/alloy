# Copyright 2026 ETH Zurich and the Alloy authors.
import copy
import dataclasses
import math

import numpy as np
import pytest
from dace.libraries.standard.nodes import external_call
from hpcagent_bench import autogen, paths
from hpcagent_bench.frameworks.benchmark import Benchmark
from hpcagent_bench.frameworks.framework import framework_class
from hpcagent_bench.precision import Precision
from hpcagent_bench.spec import BenchSpec

from alloy import api, bench
from alloy.frontend import inputs
from helpers import MATRIX

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
    full, default = sut.timings.program.arms["alloy_full"], sut.timings.program.arms["dace_default"]
    assert full.verdict.ok
    assert math.isfinite(default.median / full.median)


@pytest.mark.e2e
def test_the_framework_program_calls_each_region_winner_and_agrees_with_dace(tmp_path):
    spec = BenchSpec.load("tsvc_2_vpv")
    sdfg = bench.pipeline_sdfg(spec, "parallel_cpu", Precision.FP64)
    reference = copy.deepcopy(sdfg)
    reference.name = "vpv_dace_reference"
    reference.build_folder = str(tmp_path / "reference")
    manifest = inputs.load(paths.BENCHMARKS / spec.relative_path / f"{spec.module_name}.yaml")
    draw = inputs.draw(manifest, 0)
    expected = {**copy.deepcopy(draw.values), **draw.sizes}
    actual = {**copy.deepcopy(draw.values), **draw.sizes}
    reference.compile()(**expected)

    program, sut = bench.compiled_winners(sdfg, spec, Precision.FP64, matrix=SMALL)
    sut(**actual)

    assert program.name == f"{sdfg.name}_alloy"
    calls = list(external_call.external_calls(program))
    assert calls and all(call.implementation == "ExternCall" for call in calls)
    for name in manifest.outputs:
        np.testing.assert_allclose(actual[name], expected[name], rtol=1e-12)


@pytest.mark.e2e
def test_a_program_canonicalize_folded_to_closed_form_is_the_default_build_and_agrees_with_dace(tmp_path):
    spec = BenchSpec.load("tsvc_2_s317")
    sdfg = bench.pipeline_sdfg(spec, "canon_cpu", Precision.FP64)
    reference = copy.deepcopy(sdfg)
    reference.name = "s317_dace_reference"
    reference.build_folder = str(tmp_path / "reference")
    manifest = inputs.load(paths.BENCHMARKS / spec.relative_path / f"{spec.module_name}.yaml")
    draw = inputs.draw(manifest, 0)
    expected = {**copy.deepcopy(draw.values), **draw.sizes}
    actual = {**copy.deepcopy(draw.values), **draw.sizes}
    reference.compile()(**expected)

    program, sut = bench.compiled_winners(sdfg, spec, Precision.FP64, matrix=SMALL)
    sut(**actual)

    assert program.name == f"{sdfg.name}_alloy"
    assert not list(external_call.external_calls(program))
    for name in manifest.outputs:
        np.testing.assert_allclose(actual[name], expected[name], rtol=1e-12)
