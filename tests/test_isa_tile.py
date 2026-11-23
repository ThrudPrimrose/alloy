# Copyright 2026 ETH Zurich and the Alloy authors.
"""A11: the tile ISA. A CPU answers a GEMM tile with the FMA fallback (no AMX or SME on the evaluated CPUs), checked
against an f64 reference, and refuses a tile type it has no instruction for."""

import shutil
import subprocess
from dataclasses import replace

import pytest

from alloy.isa import tile
from alloy.isa.__main__ import main
from alloy.isa.table import load
from alloy.isa.validate import emulated, host_can_run


@pytest.mark.parametrize(("m", "n", "k", "in_type", "acc_type"), [(64, 64, 64, "f32", "f32"), (13, 7, 5, "f64", "f64"),
                                                                    (64, 32, 64, "f32", "f64")])  # fmt: skip
def test_a_cpu_tile_runs_the_fallback_and_matches_the_reference(
    m: int, n: int, k: int, in_type: str, acc_type: str
) -> None:
    sut = tile.verify(tile.plan("cpu", m, n, k, in_type, acc_type))

    assert sut.verified == "run", sut.detail
    assert f"alloy_mma_{in_type}_{acc_type}(M, N, K" in sut.program
    assert "no swizzle" in sut.layout and sut.descriptors == {
        "build": "cc -O3 -march=native -std=c11 tile.c -o tile -lm"
    }
    assert '#include "alloy' not in sut.program and f"ALLOY_MMA(alloy_mma_{in_type}_{acc_type}," in sut.program


def test_a_cpu_tile_of_half_precision_is_refused_with_the_types_it_takes() -> None:
    with pytest.raises(KeyError, match="--in f32 --acc f32.*no AMX or SME"):
        tile.plan("cpu", 64, 64, 64, "f16", "f32")


def test_an_unknown_target_and_an_empty_extent_are_refused() -> None:
    with pytest.raises(KeyError, match="tile targets"):
        tile.plan("sm80", 64, 64, 64, "f16", "f32")
    with pytest.raises(KeyError, match="positive extents"):
        tile.plan("cpu", 0, 64, 64, "f32", "f32")


def test_an_sm90_plan_loads_with_tma_into_128b_swizzled_tiles_and_runs_four_wgmma_per_k_block() -> None:
    sut = tile.plan("sm90", 128, 128, 128, "f16", "f32")

    assert sut.descriptors["tile"].startswith("alloy_gemm_128x128<ALLOY_F16>")
    assert "SWIZZLE_128B" in sut.descriptors["tensor map"] and "compute_90a" in sut.descriptors["build"]
    assert any("4 x wgmma.mma_async.m64n128k16.f32.f16.f16" in step for step in sut.steps)
    assert "alloy_make_tmap<ALLOY_F16>(&ta, dA, M, K, 128)" in sut.program


@pytest.mark.parametrize("target", tile.CDNA)
def test_a_cdna_plan_swizzles_lds_runs_eight_mfma_per_k_block_and_builds_for_its_own_arch(target: str) -> None:
    sut = tile.plan(target, 64, 128, 64, "f16", "f32")

    assert sut.target == target and sut.descriptors["build"] == f"hipcc --offload-arch={target} -O2 tile.hip -o tile"
    assert "chunk ^ (row % 8)" in sut.layout
    assert any("8 x v_mfma_f32_32x32x8_f16" in step for step in sut.steps)
    assert "alloy_gemm_64x64<ALLOY_F16><<<dim3(N / 64, M / 64), 256>>>" in sut.program


@pytest.mark.parametrize(("target", "shape", "types", "reason"), [
    ("sm90", (64, 64, 100), ("f16", "f32"), "K a multiple of 64"),
    ("sm90", (32, 64, 64), ("f16", "f32"), "64x64 blocks, 128x128 blocks"),
    ("gfx942", (64, 64, 64), ("f32", "f32"), "--in f16 --acc f32"),
    ("gfx90a", (64, 64, 64), ("f32", "f32"), "--in f16 --acc f32"),
])  # fmt: skip
def test_a_gpu_tile_the_kernels_do_not_cover_is_refused_with_what_they_take(
    target: str, shape: tuple[int, int, int], types: tuple[str, str], reason: str
) -> None:
    with pytest.raises(KeyError, match=reason):
        tile.plan(target, *shape, *types)


@pytest.mark.cuda
@pytest.mark.parametrize("in_type", [t for t, _ in tile.TYPES["sm90"]])
def test_the_sm90_program_of_each_input_type_compiles_for_sm90a(in_type: str) -> None:
    sut = tile.verify(tile.plan("sm90", 128, 128, 2 * tile.k_block(in_type), in_type, "f32"))

    assert sut.verified in ("compiled", "run"), sut.detail


@pytest.mark.hip
@pytest.mark.parametrize(("target", "in_type", "acc_type"), [(t, i, a) for t in tile.CDNA for i, a in tile.TYPES[t]])
def test_the_cdna_program_of_each_input_type_compiles_for_its_arch(target: str, in_type: str, acc_type: str) -> None:
    sut = tile.verify(tile.plan(target, 64, 64, 2 * tile.k_block(in_type), in_type, acc_type))

    assert sut.verified in ("compiled", "run"), sut.detail
    assert target in sut.detail or sut.verified == "run"


@pytest.mark.skipif(
    not (shutil.which("aarch64-linux-gnu-gcc") and shutil.which("clang")),
    reason="needs clang and the aarch64 cross compiler",
)
def test_an_sme_tile_runs_under_qemu_where_it_can_and_compiles_everywhere_else() -> None:
    """No evaluated CPU has SME: CI runs the FMOPA tile under qemu (-cpu max,sme=on), a box without qemu compiles it."""
    sut = tile.verify(tile.plan("sme", 70, 33, 9, "f32", "f32"))

    expected = "run" if (shutil.which("qemu-aarch64") or shutil.which("qemu-aarch64-static")) else "compiled"
    assert sut.verified == expected, sut.detail
    assert any("svmopa_za32_f32_m" in step for step in sut.steps)


@pytest.mark.parametrize("arch", tile.CDNA)
def test_an_amd_gpu_is_the_tile_target_of_its_own_arch_and_its_program_builds_for_it(
    arch: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[list[str]] = []

    def run(argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        out = f"{arch}\n" if argv[0] == "amdgpu-arch" else ""
        if argv[0] == "nvidia-smi":
            raise FileNotFoundError(argv[0])
        return subprocess.CompletedProcess(argv, 1 if argv[0] == "hipcc" else 0, out, "stopped after the build line")

    monkeypatch.setattr(subprocess, "run", run)

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
    target: str, in_type: str, instruction: str, k_per_block: int
) -> None:
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
def test_an_fp8_tile_names_the_encoding_its_target_reads_and_its_program_encodes_by_it(
    target: str, in_type: str, encoding: str
) -> None:
    sut = tile.plan(target, 64, 64, 128, in_type, "f32")

    assert sut.descriptors["type"] == f"{in_type} is {encoding}"
    bias = encoding.rsplit(" ", 1)[1]
    assert f"(unsigned)(exponent - 1 + {bias})" in sut.program
    assert "BYTES = 1" in sut.program


def test_gfx90a_takes_f16_bf16_and_f64_and_refuses_fp8_with_what_it_takes() -> None:
    assert tile.TYPES["gfx90a"] == (("f16", "f32"), ("bf16", "f32"), ("f64", "f64"))
    with pytest.raises(KeyError, match="gfx90a tiles take --in f16 --acc f32, --in bf16 --acc f32, --in f64 --acc f64"):
        tile.plan("gfx90a", 64, 64, 128, "e4m3", "f32")


def test_an_fp8_tile_needs_k_in_blocks_of_128() -> None:
    with pytest.raises(KeyError, match="K a multiple of 128 for e4m3; got 64x64x64"):
        tile.plan("gfx942", 64, 64, 64, "e4m3", "f32")


@pytest.mark.parametrize(("target", "starts_as_c"), [
    ("sm90", "d[4 * i + 0] = C[r * N + c]"),
    ("gfx942", "acc[g] = C[(m0 + 32 * wm"),
])  # fmt: skip
def test_a_gpu_tile_program_feeds_a_nonzero_c_and_checks_a_times_b_plus_c(target: str, starts_as_c: str) -> None:
    sut = tile.plan(target, 64, 64, 64, "f16", "f32")

    assert "hC[i] = fC[i] = (float)((i % 5) - 2);" in sut.program
    assert "Memcpy(dC, hC, sizeof(float) * M * N" in sut.program
    assert "double want = fC[i * N + j];" in sut.program
    assert starts_as_c in (tile.HERE / tile.GPU_HEADER[target]).read_text()
    assert "load its" in sut.steps[0] and "D = A x B + C" in sut.steps[0]


def test_a_tile_program_that_stops_before_its_comparison_reports_why_not_a_relative_error() -> None:
    launch = subprocess.CompletedProcess(["tile"], 2, "launch failed\n", "")
    above = subprocess.CompletedProcess(["tile"], 1, "3.000e-01\n", "")

    status, detail = tile.outcome(launch)

    assert status == "failed" and "launch failed" in detail and "relative error" not in detail
    assert tile.outcome(above) == ("failed", "relative error 3.000e-01 against the f64 reference")


@pytest.mark.parametrize(("verified", "code"), [("run", 0), ("compiled", 0), ("failed", 3), ("unverified", 3)])
def test_the_tile_command_exits_0_for_a_program_that_compiled_for_a_device_this_host_lacks(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], verified: str, code: int
) -> None:
    monkeypatch.setattr(tile, "verify", lambda found: replace(found, verified=verified, detail="stub"))

    assert main(["tile", "sm90", "gemm", "128", "128", "64", "--in", "f16", "--acc", "f32"]) == code
    assert f"check: {verified} (stub)" in capsys.readouterr().out


@pytest.mark.parametrize("isa", tile.SIMD)
@pytest.mark.parametrize("dtype", ["f32", "f64"])
def test_a_vector_isa_tile_is_the_row_wise_fma_in_its_own_intrinsics_and_runs_where_the_host_can(
    isa: str, dtype: str
) -> None:
    """avx2, avx512, neon, and sve answer an mma with 4 rows of C x one vector, spelled from the table's entries."""
    table = load()
    sut = tile.verify(tile.plan(isa, 64, 64, 64, dtype, dtype))

    runs = host_can_run(isa, dtype) or emulated(isa) is not None
    assert sut.verified == ("run" if runs else "unverified"), sut.detail
    for op in ("load", "broadcast", "fma", "store"):
        assert table.entry(isa, op, dtype).intrinsic in sut.program


def test_a_vector_isa_tile_off_its_blocks_is_refused_with_the_nearest_and_sve_takes_any_n() -> None:
    with pytest.raises(KeyError, match="nearest 64x112x64"):
        tile.plan("avx512", 64, 100, 64, "f32", "f32")

    sut = tile.verify(tile.plan("sve", 8, 33, 9, "f64", "f64"))

    assert sut.verified == ("run" if host_can_run("sve", "f64") or emulated("sve") else "unverified"), sut.detail


@pytest.mark.parametrize("target", tile.CDNA)
def test_an_f64_cdna_tile_accumulates_in_f64_with_the_f64_mfma_over_blocks_of_16(target: str) -> None:
    sut = tile.plan(target, 64, 128, 32, "f64", "f64")

    assert tile.k_block("f64") == 16 and sut.acc_type == "f64"
    assert any("v_mfma_f64_16x16x4f64" in step for step in sut.steps)
    assert "alloy_gemm_64x64_f64<<<dim3(N / 64, M / 64), 256>>>" in sut.program
    assert "alloy_mfma<" not in sut.program and "TOLERANCE" not in sut.program
