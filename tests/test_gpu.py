# Copyright 2026 ETH Zurich and the Alloy authors.
"""GPU threadblock speculation: the compiler reports are read right, occupancy follows the SM limits, every device
map of a bench kernel gets a shape the report ranks first, and a tie keeps the pipeline's own block."""

import shutil

import pytest

from alloy import gpu

NVCC_REPORT = """\
ptxas info    : Compiling entry function '_Z12kernel_map_1PdPKdl' for 'sm_89'
ptxas info    : Function properties for _Z12kernel_map_1PdPKdl
    0 bytes stack frame, 8 bytes spill stores, 4 bytes spill loads
ptxas info    : Used 40 registers, used 1 barriers, 2048 bytes smem, 376 bytes cmem[0]
ptxas info    : Compiling entry function '_Z12kernel_map_2PKdPdl' for 'sm_89'
ptxas info    : Function properties for _Z12kernel_map_2PKdPdl
    0 bytes stack frame, 0 bytes spill stores, 0 bytes spill loads
ptxas info    : Used 12 registers, used 0 barriers, 376 bytes cmem[0]
"""

HIP_REPORT = """\
unit.hip:2:1: remark: Function Name: _Z12kernel_map_1Pdi [-Rpass-analysis=kernel-resource-usage]
unit.hip:2:1: remark:     TotalSGPRs: 11 [-Rpass-analysis=kernel-resource-usage]
unit.hip:2:1: remark:     VGPRs: 24 [-Rpass-analysis=kernel-resource-usage]
unit.hip:2:1: remark:     Occupancy [waves/SIMD]: 8 [-Rpass-analysis=kernel-resource-usage]
unit.hip:2:1: remark:     SGPRs Spill: 0 [-Rpass-analysis=kernel-resource-usage]
unit.hip:2:1: remark:     VGPRs Spill: 3 [-Rpass-analysis=kernel-resource-usage]
unit.hip:2:1: remark:     LDS Size [bytes/block]: 512 [-Rpass-analysis=kernel-resource-usage]
"""


def test_the_nvcc_report_gives_each_kernel_its_registers_spills_and_shared_memory():
    sut = gpu.nvcc_usage(NVCC_REPORT)

    assert sut == {
        "_Z12kernel_map_1PdPKdl": gpu.Usage(registers=40, spill_bytes=12, shared_bytes=2048),
        "_Z12kernel_map_2PKdPdl": gpu.Usage(registers=12, spill_bytes=0, shared_bytes=0),
    }


def test_the_hip_report_gives_each_kernel_its_registers_spills_lds_and_waves():
    sut = gpu.hip_usage(HIP_REPORT)

    assert sut == {"_Z12kernel_map_1Pdi": gpu.Usage(registers=24, spill_bytes=12, shared_bytes=512, waves=8)}


def test_a_kernel_is_found_by_its_plain_name_in_a_mangled_report():
    usages = gpu.nvcc_usage(NVCC_REPORT)

    assert gpu.kernel_usage(usages, "kernel_map_2") == gpu.Usage(registers=12, spill_bytes=0, shared_bytes=0)
    assert gpu.kernel_usage(usages, "kernel_map_3") is None


@pytest.mark.parametrize(
    ("registers", "threads", "expected"),
    [
        (40, 256, 1.0),  # 6 blocks of 8 warps fill the 48 warps of an sm_89 SM
        (128, 256, 2 / 6),  # 4096 registers a warp: 2 blocks of 8 warps
        (32, 32, 0.5),  # 24 blocks of 1 warp: the block limit binds
    ],
)
def test_cuda_occupancy_is_bounded_by_registers_blocks_and_threads(registers: int, threads: int, expected: float):
    usage = gpu.Usage(registers=registers, spill_bytes=0, shared_bytes=0)

    assert gpu.cuda_occupancy(usage, threads, gpu.SM_LIMITS["8.9"]) == pytest.approx(expected)


def test_a_spilling_shape_ranks_below_any_shape_that_does_not_spill():
    clean = ((256, 1, 1), gpu.Usage(64, 0, 0), 0.25)
    spilling = ((128, 1, 1), gpu.Usage(255, 8, 0), 1.0)

    assert sorted([spilling, clean], key=lambda row: gpu.rank_key(*row)) == [clean, spilling]


def test_occupancy_past_saturation_does_not_reorder_shapes():
    first = ((64, 4, 1), gpu.Usage(40, 0, 0), 0.75)
    second = ((32, 8, 1), gpu.Usage(40, 0, 0), 1.0)

    assert gpu.rank_key(*first) == gpu.rank_key(*second)[:3] + (False, 40)


def bench_pipeline(kernel: str):
    from hpcagent_bench.cpf.cache import Target
    from hpcagent_bench.precision import Precision
    from hpcagent_bench.spec import BenchSpec

    from alloy.hb_plugin.adapter import pipeline_sdfg

    spec = BenchSpec.load(kernel)

    def run(shapes):
        return pipeline_sdfg(spec, "canon_gpu", Precision.FP64, Target.GPU, offloaded=gpu.blocks(shapes))

    return run


@pytest.mark.cuda
@pytest.mark.parametrize("kernel", ["jacobi_2d", "tsvc_2_vpv"])
def test_every_device_map_takes_a_shape_without_spills_and_the_program_carries_it(kernel: str):
    assert shutil.which("nvcc"), "the cuda mark needs nvcc"

    program, picks = gpu.speculate(bench_pipeline(kernel), "cuda", "8.9")

    assert picks, "every bench kernel here has a device map"
    for pick in picks.values():
        assert pick.usage.spill_bytes == 0 and pick.occupancy > 0
        assert pick.shape == pick.ranked[0][0] and len(pick.ranked) >= 2
    blocks = [tuple(entry.map.gpu_block_size) for entry in gpu.device_maps(program)]
    assert sorted(pick.shape for pick in picks.values()) == sorted(blocks)


@pytest.mark.cuda
def test_a_tie_keeps_the_block_the_pipeline_picks():
    run = bench_pipeline("tsvc_2_vpv")
    (default,) = [tuple(entry.map.gpu_block_size) for entry in gpu.device_maps(run({}))]

    _, picks = gpu.speculate(run, "cuda", "8.9")

    assert [pick.shape for pick in picks.values()] == [default]


@pytest.mark.hip
def test_a_hip_device_map_takes_a_shape_ranked_by_the_compilers_waves():
    assert shutil.which("hipcc"), "the hip mark needs hipcc with hipcub"

    _, picks = gpu.speculate(bench_pipeline("tsvc_2_vpv"), "hip", "gfx90a")

    (pick,) = picks.values()
    assert pick.usage.waves is not None and pick.occupancy == pick.usage.waves / 8


@pytest.mark.cuda
def test_the_submitted_hip_form_launches_every_kernel_with_its_picked_block():
    from hpcagent_bench.categories import Language, SourceMode
    from hpcagent_bench.harness.task import Task
    from hpcagent_bench.spec import BenchSpec

    from alloy.hb_plugin.adapter import device_submission

    program, picks = gpu.speculate(bench_pipeline("jacobi_2d"), "cuda", "8.9")

    sut = device_submission(
        Task("jacobi_2d", SourceMode.RESTRICTED, Language.HIP), BenchSpec.load("jacobi_2d"), program
    )

    assert sut.language is Language.HIP and sut.source and sut.device_source
    for pick in picks.values():
        assert f"__launch_bounds__({pick.shape[0] * pick.shape[1] * pick.shape[2]})" in sut.device_source
