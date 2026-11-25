# Copyright 2026 ETH Zurich and the Alloy authors.
"""GPU threadblock speculation: the compiler reports are read right, occupancy follows the SM limits, every device
map of a bench kernel gets a shape the report ranks first, and a tie keeps the pipeline's own block."""

import pathlib
import shutil
import sys
from collections.abc import Callable

import dace
import pytest
from dace.config import set_temporary
from dace.sdfg import nodes

from alloy import gpu
from helpers import REDUCTIONS, load_program

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


#: Stands in for a device compiler: answers the report recorded for the unit's block. ``spill_at`` is the block a real
#: compiler ran out of registers at.
RECORDED_COMPILER = """#!{python} -I
import pathlib, re, sys

unit = next(argument for argument in sys.argv if argument.endswith((".cu", ".hip")))
found = re.search(r"__launch_bounds__\\((\\d+)[^)]*\\)\\s+(\\w+)\\s*\\(", pathlib.Path(unit).read_text())
threads, kernel = found.groups()
spills = int(threads) == {spill_at}
report = {report!r}.replace("LENGTH", str(len(kernel))).replace("KERNEL", kernel)
print(report.replace("SPILL", "64" if spills else "0").replace("WAVES", "2" if spills else "8"))
"""
NVCC_RECORDED = NVCC_REPORT.split("ptxas info    : Compiling entry function '_Z12kernel_map_2")[0].replace(
    "_Z12kernel_map_1PdPKdl", "_ZLENGTHKERNELPdPKdl"
)


def device_pipeline(shapes: dict[int, gpu.Shape]) -> dace.SDFG:
    """``scale`` as one device map; its block comes from :func:`gpu.blocks`, as a bench pipeline's does."""
    sdfg = load_program(f"{REDUCTIONS}:scale").to_sdfg()
    sdfg.simplify()
    for desc in sdfg.arrays.values():
        desc.storage = dace.StorageType.GPU_Global
    for node, _ in sdfg.all_nodes_recursive():
        if isinstance(node, nodes.MapEntry):
            node.map.schedule = dace.ScheduleType.GPU_Device
            node.map.gpu_block_size = [64, 1, 1]
    gpu.blocks(shapes)(sdfg)
    return sdfg


def recorded_compiler(tmp_path: pathlib.Path, name: str, report: str, spill_at: int) -> None:
    script = tmp_path / name
    script.write_text(RECORDED_COMPILER.format(python=sys.executable, report=report, spill_at=spill_at))
    script.chmod(0o755)


def test_a_cuda_map_leaves_a_block_that_spills_for_one_the_compiler_reports_clean(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    recorded_compiler(tmp_path, "nvcc", NVCC_RECORDED.replace("8 bytes spill stores", "SPILL bytes spill stores"), 64)
    monkeypatch.setenv("PATH", str(tmp_path), prepend=":")

    program, picks = gpu.speculate(device_pipeline, "cuda", "8.9")

    (pick,) = picks.values()
    assert pick.shape != (64, 1, 1) and pick.usage.spill_bytes == 4, "the recorded loads still spill four bytes"
    assert [tuple(entry.map.gpu_block_size) for entry in gpu.device_maps(program)] == [pick.shape]


def test_a_hip_map_takes_the_block_the_compiler_reports_the_most_waves_for(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report = HIP_REPORT.replace("_Z12kernel_map_1Pdi", "KERNEL").replace("[waves/SIMD]: 8", "[waves/SIMD]: WAVES")
    recorded_compiler(tmp_path, "hipcc", report.replace("VGPRs Spill: 3", "VGPRs Spill: 0"), 64)
    monkeypatch.setenv("PATH", str(tmp_path), prepend=":")

    with set_temporary("compiler", "cuda", "chiplet_number", value=1):  # no device here to count them on
        program, picks = gpu.speculate(device_pipeline, "hip", "gfx90a")

    (pick,) = picks.values()
    assert pick.shape != (64, 1, 1) and pick.usage.waves == 8
    assert [tuple(entry.map.gpu_block_size) for entry in gpu.device_maps(program)] == [pick.shape]


def test_the_nvcc_report_gives_each_kernel_its_registers_spills_and_shared_memory() -> None:
    sut = gpu.nvcc_usage(NVCC_REPORT)

    assert sut == {
        "_Z12kernel_map_1PdPKdl": gpu.Usage(registers=40, spill_bytes=12, shared_bytes=2048),
        "_Z12kernel_map_2PKdPdl": gpu.Usage(registers=12, spill_bytes=0, shared_bytes=0),
    }


def test_the_hip_report_gives_each_kernel_its_registers_spills_lds_and_waves() -> None:
    sut = gpu.hip_usage(HIP_REPORT)

    assert sut == {"_Z12kernel_map_1Pdi": gpu.Usage(registers=24, spill_bytes=12, shared_bytes=512, waves=8)}


def test_a_kernel_is_found_by_its_plain_name_in_a_mangled_report() -> None:
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
def test_cuda_occupancy_is_bounded_by_registers_blocks_and_threads(
    registers: int, threads: int, expected: float
) -> None:
    usage = gpu.Usage(registers=registers, spill_bytes=0, shared_bytes=0)

    assert gpu.cuda_occupancy(usage, threads, gpu.SM_LIMITS["8.9"]) == pytest.approx(expected)


def test_a_spilling_shape_ranks_below_any_shape_that_does_not_spill() -> None:
    clean = ((256, 1, 1), gpu.Usage(64, 0, 0), 0.25)
    spilling = ((128, 1, 1), gpu.Usage(255, 8, 0), 1.0)

    assert sorted([spilling, clean], key=lambda row: gpu.rank_key(*row)) == [clean, spilling]


def test_occupancy_past_saturation_does_not_reorder_shapes() -> None:
    first = ((64, 4, 1), gpu.Usage(40, 0, 0), 0.75)
    second = ((32, 8, 1), gpu.Usage(40, 0, 0), 1.0)

    assert gpu.rank_key(*first) == gpu.rank_key(*second)[:3] + (False, 40)


# Reproducer: wave64 ranks a 32-wide row lower (7d94b16)
def test_a_row_of_half_a_wavefront_ranks_below_a_full_one_on_hip_only() -> None:
    half = ((32, 8, 1), gpu.Usage(40, 0, 0), 0.5)
    full = ((64, 4, 1), gpu.Usage(40, 0, 0), 0.5)

    assert gpu.rank_key(*half, gpu.LANES["cuda"]) == gpu.rank_key(*full, gpu.LANES["cuda"])
    assert gpu.rank_key(*full, gpu.LANES["hip"]) < gpu.rank_key(*half, gpu.LANES["hip"])


# Reproducer: the GPU path follows the task's dialect and the bench's parse, ISA checks no longer pass vacuously, Tensix
#  rows as tt-metal 0.63 runs them (7d94b16)
def test_the_gpu_form_follows_the_task_language_and_else_the_image() -> None:
    from hpcagent_bench.categories import Language, SourceMode
    from hpcagent_bench.harness.task import Task

    from alloy.hb_plugin.adapter import form_dialect

    assert form_dialect(Task("jacobi_2d", SourceMode.ANY, Language.CUDA)) == "cuda"
    assert form_dialect(Task("jacobi_2d", SourceMode.ANY, Language.HIP, image="nvidia")) == "hip"
    assert form_dialect(Task("jacobi_2d", SourceMode.ANY, Language.C, image="amd")) == "hip"


def bench_pipeline(kernel: str) -> Callable[[dict[int, gpu.Shape]], dace.SDFG]:
    from hpcagent_bench.cpf.cache import Target
    from hpcagent_bench.precision import Precision
    from hpcagent_bench.spec import BenchSpec

    from alloy.hb_plugin.adapter import pipeline_sdfg

    spec = BenchSpec.load(kernel)

    def run(shapes: dict[int, gpu.Shape]) -> dace.SDFG:
        return pipeline_sdfg(spec, "canon_gpu", Precision.FP64, Target.GPU, offloaded=gpu.blocks(shapes))

    return run


@pytest.mark.cuda
@pytest.mark.parametrize("kernel", ["jacobi_2d", "tsvc_2_vpv"])
def test_every_device_map_takes_a_shape_without_spills_and_the_program_carries_it(kernel: str) -> None:
    assert shutil.which("nvcc"), "the cuda mark needs nvcc"

    program, picks = gpu.speculate(bench_pipeline(kernel), "cuda", "8.9")

    assert picks, "every bench kernel here has a device map"
    for pick in picks.values():
        assert pick.usage.spill_bytes == 0 and pick.occupancy > 0
        assert pick.shape == pick.ranked[0][0] and len(pick.ranked) >= 2
    blocks = [tuple(entry.map.gpu_block_size) for entry in gpu.device_maps(program)]
    assert sorted(pick.shape for pick in picks.values()) == sorted(blocks)


@pytest.mark.cuda
def test_a_tie_keeps_the_block_the_pipeline_picks() -> None:
    run = bench_pipeline("tsvc_2_vpv")
    (default,) = [tuple(entry.map.gpu_block_size) for entry in gpu.device_maps(run({}))]

    _, picks = gpu.speculate(run, "cuda", "8.9")

    assert [pick.shape for pick in picks.values()] == [default]


@pytest.mark.hip
def test_a_hip_device_map_takes_a_shape_ranked_by_the_compilers_waves() -> None:
    assert shutil.which("hipcc"), "the hip mark needs hipcc with hipcub"

    _, picks = gpu.speculate(bench_pipeline("tsvc_2_vpv"), "hip", "gfx90a")

    (pick,) = picks.values()
    assert pick.usage.waves is not None and pick.occupancy == pick.usage.waves / 8


@pytest.mark.cuda
def test_the_submitted_hip_form_launches_every_kernel_with_its_picked_block() -> None:
    from hpcagent_bench.categories import Language, SourceMode
    from hpcagent_bench.harness.task import Task
    from hpcagent_bench.spec import BenchSpec

    from alloy.hb_plugin.adapter import device_submission

    program, picks = gpu.speculate(bench_pipeline("jacobi_2d"), "cuda", "8.9")

    sut = device_submission(
        Task("jacobi_2d", SourceMode.RESTRICTED, Language.HIP), BenchSpec.load("jacobi_2d"), program, "hip"
    )

    assert sut.language is Language.HIP and sut.source and sut.device_source
    for pick in picks.values():
        assert f"__launch_bounds__({pick.shape[0] * pick.shape[1] * pick.shape[2]})" in sut.device_source


def ranked_pick(*shapes: gpu.Shape) -> gpu.Pick:
    usage = gpu.Usage(registers=32, spill_bytes=0, shared_bytes=0)
    return gpu.Pick(shapes[0], usage, 0.5, tuple((shape, usage, 0.5) for shape in shapes))


A, B, C = (128, 1, 1), (256, 1, 1), (64, 1, 1)


def test_the_descent_keeps_a_maps_next_shape_only_when_the_program_runs_faster() -> None:
    seconds = {(A, A): 3.0, (B, A): 2.0, (C, A): 2.5, (B, B): 2.5, (B, C): 2.0}

    sut = gpu.descend(
        lambda shapes: (shapes[0], shapes[1]),  # pyright: ignore[reportArgumentType] -- test double
        {0: ranked_pick(A, B, C), 1: ranked_pick(A, B, C)},
        lambda program: seconds[program],  # pyright: ignore[reportArgumentType] -- test double
        lambda: True,
    )

    assert sut == {0: B, 1: A}  # (B, C) ties (B, A): a tie keeps the shape already held


def test_a_shape_that_fails_to_run_is_never_taken_and_a_running_one_replaces_a_failed_pick() -> None:
    seconds = {A: None, B: 4.0, C: None}

    sut = gpu.descend(
        lambda shapes: shapes[0],  # pyright: ignore[reportArgumentType] -- test double
        {0: ranked_pick(A, B, C)},
        lambda program: seconds[program],  # pyright: ignore[reportArgumentType] -- test double
        lambda: True,  # pyright: ignore[reportArgumentType] -- test double
    )

    assert sut == {0: B}


def test_the_descent_keeps_the_speculated_shapes_when_no_time_is_left() -> None:
    timed: list[gpu.Shape] = []

    def time_it(program: gpu.Shape) -> float:
        timed.append(program)
        return 1.0

    sut = gpu.descend(lambda shapes: shapes[0], {0: ranked_pick(A, B, C)}, time_it, lambda: False)  # pyright: ignore[reportArgumentType] -- test double

    assert sut == {0: A}
    assert timed == [A]


def test_the_descent_tries_no_more_shapes_of_a_map_than_its_width() -> None:
    timed: list[gpu.Shape] = []

    def time_it(program: gpu.Shape) -> float:
        timed.append(program)
        return 1.0

    gpu.descend(lambda shapes: shapes[0], {0: ranked_pick(A, B, C, (512, 1, 1))}, time_it, lambda: True, width=2)  # pyright: ignore[reportArgumentType] -- test double

    assert timed == [A, B]


@pytest.mark.hip
def test_the_gpu_tool_answers_the_ranked_hip_form_the_bench_builds(tmp_path: pathlib.Path) -> None:
    from hpcagent_bench.precision import Precision

    from alloy.hb_plugin.workbench import CodegenRequest, codegen
    from alloy.report import Mode

    request = CodegenRequest(
        kernel="tsvc_2_vpv", mode=Mode.SPECULATIVE, precision=Precision.FP64, folder=str(tmp_path), running={},
        language="hip",
    )  # fmt: skip

    sut = codegen(request)

    assert sut.checked_sha256, "the judge built the pair once to check it"
    assert (tmp_path / "best" / "device.hip").read_text().count("__global__") >= 1
    report = pathlib.Path(sut.report).read_text()
    assert "| Map | Picked |" in report and "| 0 |" in report


def test_the_build_plugin_compiles_a_gpu_sdfg_with_the_block_the_report_ranks_first(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from alloy import dace_backend

    recorded_compiler(tmp_path, "nvcc", NVCC_RECORDED.replace("8 bytes spill stores", "SPILL bytes spill stores"), 64)
    monkeypatch.setenv("PATH", str(tmp_path), prepend=":")
    monkeypatch.setattr(gpu, "native_dialect", lambda: "cuda")
    monkeypatch.setattr(gpu, "native_arch", lambda dialect: "8.9")
    compiled: list[tuple[list[gpu.Shape], str]] = []

    def dace_build(program: dace.SDFG, **_: object) -> str:
        from dace.config import Config

        blocks: list[gpu.Shape] = [
            (e.map.gpu_block_size[0], e.map.gpu_block_size[1], e.map.gpu_block_size[2])
            for e in gpu.device_maps(program)
        ]
        compiled.append((blocks, str(Config.get("compiler", "build_plugin"))))
        return "compiled"

    monkeypatch.setattr(dace.SDFG, "compile", dace_build)
    sdfg = device_pipeline({})
    before = [tuple(e.map.gpu_block_size) for e in gpu.device_maps(sdfg)]

    with set_temporary("compiler", "build_plugin", value="alloy-speculative"):
        result = dace_backend.speculative(sdfg)

    assert result == "compiled"
    ((shapes, plugin),) = compiled
    assert shapes != [(64, 1, 1)] and plugin == "", "the spilling 64-thread block is replaced; DaCe builds it"
    assert [tuple(e.map.gpu_block_size) for e in gpu.device_maps(sdfg)] == before, "the caller's SDFG is unchanged"


def test_an_amd_gpu_that_amdgpu_arch_omits_is_found_through_rocminfo(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # ROCm 7.2's amdgpu-arch prints nothing for an MI50, exit 0; rocminfo still lists the agent
    for name, text in (("amdgpu-arch", ""), ("rocminfo", "  Name:                    gfx906\n")):
        tool = tmp_path / name
        tool.write_text(f"#!/bin/sh\nprintf '{text}'\n")
        tool.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))

    assert gpu.native_dialect() == "hip"
    assert gpu.native_arch("hip") == "gfx906"
