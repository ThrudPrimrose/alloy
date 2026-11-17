# Copyright 2026 ETH Zurich and the Alloy authors.
"""A11: the tile ISA. A CPU answers a GEMM tile with the FMA fallback (no AMX or SME on the evaluated CPUs), checked
against an f64 reference, and refuses a tile type it has no instruction for."""

import shutil
import subprocess

import pytest

from alloy.isa import tile


@pytest.mark.parametrize(("m", "n", "k", "in_type", "acc_type"), [(64, 64, 64, "f32", "f32"), (13, 7, 5, "f64", "f64"),
                                                                    (64, 32, 64, "f32", "f64")])  # fmt: skip
def test_a_cpu_tile_runs_the_fallback_and_matches_the_reference(m, n, k, in_type, acc_type):
    sut = tile.verify(tile.plan("cpu", m, n, k, in_type, acc_type))

    assert sut.verified == "run", sut.detail
    assert f"alloy_mma_{in_type}_{acc_type}(M, N, K" in sut.program
    assert "no swizzle" in sut.layout and sut.descriptors == {}


def test_a_cpu_tile_of_half_precision_is_refused_with_the_types_it_takes():
    with pytest.raises(KeyError, match="--in f32 --acc f32.*no AMX or SME"):
        tile.plan("cpu", 64, 64, 64, "f16", "f32")


def test_an_unknown_target_and_an_empty_extent_are_refused():
    with pytest.raises(KeyError, match="tile targets"):
        tile.plan("sm80", 64, 64, 64, "f16", "f32")
    with pytest.raises(KeyError, match="positive extents"):
        tile.plan("cpu", 0, 64, 64, "f32", "f32")


def test_an_sm90_plan_loads_with_tma_into_128b_swizzled_tiles_and_runs_four_wgmma_per_k_block():
    sut = tile.plan("sm90", 128, 128, 128, "f16", "f32")

    assert sut.descriptors["tile"].startswith("alloy_gemm_128x128<ALLOY_F16>")
    assert "SWIZZLE_128B" in sut.descriptors["tensor map"] and "compute_90a" in sut.descriptors["build"]
    assert any("4 x wgmma.mma_async.m64n128k16.f32.f16.f16" in step for step in sut.steps)
    assert "alloy_make_tmap<ALLOY_F16>(&ta, dA, M, K, 128)" in sut.program


@pytest.mark.parametrize("target", tile.CDNA)
def test_a_cdna_plan_swizzles_lds_runs_eight_mfma_per_k_block_and_builds_for_its_own_arch(target):
    sut = tile.plan(target, 64, 128, 64, "f16", "f32")

    assert sut.target == target and sut.descriptors["build"] == f"hipcc --offload-arch={target}"
    assert "chunk ^ (row % 8)" in sut.layout
    assert any("8 x v_mfma_f32_32x32x8_f16" in step for step in sut.steps)
    assert "alloy_gemm_64x64<ALLOY_F16><<<dim3(N / 64, M / 64), 256>>>" in sut.program


@pytest.mark.parametrize(("target", "shape", "types", "reason"), [
    ("sm90", (64, 64, 100), ("f16", "f32"), "K a multiple of 64"),
    ("sm90", (32, 64, 64), ("f16", "f32"), "64x64 blocks, 128x128 blocks"),
    ("gfx942", (64, 64, 64), ("f32", "f32"), "--in f16 --acc f32"),
    ("gfx90a", (64, 64, 64), ("f32", "f32"), "--in f16 --acc f32"),
])  # fmt: skip
def test_a_gpu_tile_the_kernels_do_not_cover_is_refused_with_what_they_take(target, shape, types, reason):
    with pytest.raises(KeyError, match=reason):
        tile.plan(target, *shape, *types)


@pytest.mark.cuda
@pytest.mark.parametrize("in_type", [t for t, _ in tile.TYPES["sm90"]])
def test_the_sm90_program_of_each_input_type_compiles_for_sm90a(in_type):
    sut = tile.verify(tile.plan("sm90", 128, 128, 2 * tile.k_block(in_type), in_type, "f32"))

    assert sut.verified in ("compiled", "run"), sut.detail


@pytest.mark.hip
@pytest.mark.parametrize(("target", "in_type"), [(t, i) for t in tile.CDNA for i, _ in tile.TYPES[t]])
def test_the_cdna_program_of_each_input_type_compiles_for_its_arch(target, in_type):
    sut = tile.verify(tile.plan(target, 64, 64, 2 * tile.k_block(in_type), in_type, "f32"))

    assert sut.verified in ("compiled", "run"), sut.detail
    assert target in sut.detail or sut.verified == "run"


@pytest.mark.skipif(
    not (shutil.which("aarch64-linux-gnu-gcc") and shutil.which("clang")),
    reason="needs clang and the aarch64 cross compiler",
)
def test_an_sme_tile_runs_under_qemu_where_it_can_and_compiles_everywhere_else():
    """No evaluated CPU has SME: CI runs the FMOPA tile under qemu (-cpu max,sme=on), a box without qemu compiles it."""
    sut = tile.verify(tile.plan("sme", 70, 33, 9, "f32", "f32"))

    expected = "run" if (shutil.which("qemu-aarch64") or shutil.which("qemu-aarch64-static")) else "compiled"
    assert sut.verified == expected, sut.detail
    assert any("svmopa_za32_f32_m" in step for step in sut.steps)


@pytest.mark.parametrize("arch", tile.CDNA)
def test_an_amd_gpu_is_the_tile_target_of_its_own_arch_and_its_program_builds_for_it(arch, monkeypatch):
    calls: list[list[str]] = []

    def run(argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        out = f"{arch}\n" if argv[0] == "amdgpu-arch" else ""
        if argv[0] == "nvidia-smi":
            raise FileNotFoundError(argv[0])
        return subprocess.CompletedProcess(argv, 1 if argv[0] == "hipcc" else 0, out, "stopped after the build line")

    monkeypatch.setattr(tile.subprocess, "run", run)

    assert tile.native_gpu() == arch
    sut = tile.verify(tile.plan(arch, 64, 64, 64, "f16", "f32"))

    (hipcc,) = [argv for argv in calls if argv[0] == "hipcc"]
    assert f"--offload-arch={arch}" in hipcc and "-c" not in hipcc  # this machine has the GPU: built to run
    assert sut.verified == "failed" and "stopped after the build line" in sut.detail


@pytest.mark.parametrize(("target", "in_type", "instruction", "k_per_block"), [
    ("gfx90a", "bf16", "8 x v_mfma_f32_32x32x8_bf16", 64),
    ("gfx942", "bf16", "8 x v_mfma_f32_32x32x8_bf16", 64),
    ("gfx942", "e4m3", "8 x v_mfma_f32_32x32x16_fp8_fp8", 128),
    ("gfx942", "e5m2", "8 x v_mfma_f32_32x32x16_bf8_bf8", 128),
    ("sm90", "bf16", "4 x wgmma.mma_async.m64n64k16.f32.bf16.bf16", 64),
    ("sm90", "e4m3", "4 x wgmma.mma_async.m64n64k32.f32.e4m3.e4m3", 128),
    ("sm90", "e5m2", "4 x wgmma.mma_async.m64n64k32.f32.e5m2.e5m2", 128),
])  # fmt: skip
def test_a_gpu_tile_of_each_input_type_runs_its_instruction_over_a_k_block_of_128_bytes(
    target, in_type, instruction, k_per_block
):
    sut = tile.plan(target, 64, 64, 2 * k_per_block, in_type, "f32")

    assert tile.k_block(in_type) == k_per_block
    assert any(instruction in step for step in sut.steps)
    assert any(f"2 K blocks of {k_per_block} ({in_type}, 128 bytes of a row)" in step for step in sut.steps)
    assert f"<{tile.ELEM[in_type]}>" in sut.descriptors["tile"]


@pytest.mark.parametrize(("target", "in_type", "encoding"), [
    ("gfx942", "e4m3", "E4M3FNUZ (__hip_fp8_e4m3_fnuz): 4 exponent bits, 3 mantissa bits, bias 8"),
    ("gfx942", "e5m2", "E5M2FNUZ (__hip_fp8_e5m2_fnuz): 5 exponent bits, 2 mantissa bits, bias 16"),
    ("sm90", "e4m3", "OCP E4M3 (__nv_fp8_e4m3): 4 exponent bits, 3 mantissa bits, bias 7"),
    ("sm90", "e5m2", "OCP E5M2 (__nv_fp8_e5m2): 5 exponent bits, 2 mantissa bits, bias 15"),
])  # fmt: skip
def test_an_fp8_tile_names_the_encoding_its_target_reads_and_its_program_encodes_by_it(target, in_type, encoding):
    sut = tile.plan(target, 64, 64, 128, in_type, "f32")

    assert sut.descriptors["type"] == f"{in_type} is {encoding}"
    bias = encoding.rsplit(" ", 1)[1]
    assert f"(unsigned)(exponent - 1 + {bias})" in sut.program
    assert "BYTES = 1" in sut.program


def test_gfx90a_takes_f16_and_bf16_and_refuses_fp8_with_what_it_takes():
    assert tile.TYPES["gfx90a"] == (("f16", "f32"), ("bf16", "f32"))
    with pytest.raises(KeyError, match="gfx90a tiles take --in f16 --acc f32, --in bf16 --acc f32"):
        tile.plan("gfx90a", 64, 64, 128, "e4m3", "f32")


def test_an_fp8_tile_needs_k_in_blocks_of_128():
    with pytest.raises(KeyError, match="K a multiple of 128 for e4m3; got 64x64x64"):
        tile.plan("gfx942", 64, 64, 64, "e4m3", "f32")
