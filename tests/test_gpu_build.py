# Copyright 2026 ETH Zurich and the Alloy authors.
"""A10: a GPU program's device candidates (compiler and floating-point level), built into libraries with the judge's
recipe, and speculative mode's ranking of them by the compilers' resource reports."""

import pathlib
import shutil

import pytest

pytest.importorskip("hpcagent_bench", reason="the GPU candidates build with the bench's recipe")

from hpcagent_bench.categories import Language, SourceMode
from hpcagent_bench.cpf.bridge import render_canonical
from hpcagent_bench.cpf.cache import DEFAULT_HINTS, Target
from hpcagent_bench.harness.envelope import Submission
from hpcagent_bench.harness.task import Task
from hpcagent_bench.precision import Precision
from hpcagent_bench.spec import BenchSpec

from alloy import gpu_build
from alloy.gpu_build import GpuBuild, GpuCandidate
from alloy.hb_plugin import adapter

COMPILERS = gpu_build.load()


def test_the_default_is_the_dialects_first_compiler_and_every_other_candidate_changes_one_factor():
    sut = gpu_build.candidates(COMPILERS, "hip", accumulates=True)

    assert sut[0] == GpuCandidate("hipcc")
    assert [c.name for c in sut[1:]] == ["amdclang", "hipcc_nocontract", "hipcc_fast", "hipcc_unsafe-atomics"]
    assert not [c for c in gpu_build.candidates(COMPILERS, "hip", accumulates=False) if c.unsafe_atomics]
    assert [c.name for c in gpu_build.candidates(COMPILERS, "cuda", accumulates=True)] == [
        "nvcc", "clang_cuda", "nvcc_nocontract", "nvcc_fast"
    ]  # fmt: skip


def test_a_compiler_without_a_bench_recipe_builds_with_its_own_flags_and_the_target_filled_in(tmp_path):
    device, host, library = tmp_path / "k.cu", tmp_path / "k_host.cpp", tmp_path / "libk.so"

    sut = gpu_build.commands(
        COMPILERS["clang_cuda"], GpuCandidate("clang_cuda", "fast"), device, host, library, "sm_90"
    )

    assert len(sut) == 3 and sut[-1][-2:] == ["-o", str(library)]
    assert "--cuda-gpu-arch=sm_90" in sut[0] and "-ffast-math" in sut[0] and "-Xcuda-ptxas" in sut[0]
    assert [argv[argv.index("-c") + 1] for argv in sut[:2]] == [str(device), str(host)]


def test_speculative_mode_leaves_the_default_build_only_for_one_the_reports_rank_strictly_ahead(monkeypatch):
    def built(name: str, registers: int, spills: int) -> tuple[GpuBuild, Submission]:
        log = (f"ptxas info    : Compiling entry function '_Z1kv' for 'sm_89'\n"
               f"ptxas info    : Function properties for _Z1kv\n"
               f"    0 bytes stack frame, {spills} bytes spill stores, {spills} bytes spill loads\n"
               f"ptxas info    : Used {registers} registers, used 0 barriers, 376 bytes cmem[0]\n")  # fmt: skip
        result = GpuBuild(GpuCandidate(name), pathlib.Path(f"lib{name}.so"), name, log)
        return result, Submission(language=Language.CUDA, library=f"lib{name}.so")

    source = Submission(language=Language.CUDA, source="host", device_source="device")
    task = Task("tsvc_2_vpv", SourceMode.ANY, Language.CUDA, image="nvidia")
    monkeypatch.setattr(adapter, "device_submission", lambda *args: source)
    spec = BenchSpec.load("tsvc_2_vpv")

    monkeypatch.setattr(adapter, "gpu_libraries", lambda *args: [built("nvcc", 40, 0), built("nvcc_fast", 32, 0)])
    assert adapter.speculated_library(task, spec, None)[1] == "nvcc_fast"  # type: ignore[arg-type]
    monkeypatch.setattr(adapter, "gpu_libraries", lambda *args: [built("nvcc", 32, 0), built("nvcc_fast", 32, 0)])
    assert adapter.speculated_library(task, spec, None) == (source, "default")  # type: ignore[arg-type]
    monkeypatch.setattr(adapter, "gpu_libraries", lambda *args: [built("nvcc", 40, 0), built("nvcc_fast", 8, 16)])
    assert adapter.speculated_library(task, spec, None)[1] == "default", "a spill ranks behind any register count"  # type: ignore[arg-type]


@pytest.mark.cuda
def test_nvcc_builds_each_floating_point_level_of_a_bench_kernel_into_its_own_device_code(tmp_path):
    assert shutil.which("nvcc"), "the cuda mark needs nvcc"
    spec = BenchSpec.load("tsvc_2_vpv")
    sdfg = adapter.pipeline_sdfg(spec, "canon_gpu", Precision.FP64, Target.GPU)
    form = render_canonical(spec, spec.short_name, sdfg, "cuda", "float64", Target.GPU, DEFAULT_HINTS)
    nvcc = [c for c in gpu_build.candidates(COMPILERS, "cuda", accumulates=False) if c.compiler == "nvcc"]

    sut = [
        gpu_build.build(COMPILERS, c, form.code, form.device_code, tmp_path, "sm_89", tuple(form.libraries))
        for c in nvcc
    ]

    assert all(b.library is not None and b.library.is_file() for b in sut), [b.error for b in sut]
    assert len({b.device_hash for b in sut}) == len(sut), "contraction off and fast math change the device code"
    assert all(gpu_build.usage(b, "cuda") for b in sut), "each build printed its kernels' registers"
