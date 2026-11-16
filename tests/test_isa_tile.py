# Copyright 2026 ETH Zurich and the Alloy authors.
"""A11: the tile ISA. A CPU answers a GEMM tile with the FMA fallback (no AMX or SME on the evaluated CPUs), checked
against an f64 reference, and refuses a tile type it has no instruction for."""

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

    assert sut.descriptors["tile"].startswith("alloy_gemm_128x128x64")
    assert "SWIZZLE_128B" in sut.descriptors["tensor map"] and "compute_90a" in sut.descriptors["build"]
    assert any("4 x wgmma.mma_async.m64n128k16.f32.f16.f16" in step for step in sut.steps)
    assert "alloy_make_tmap(&ta, dA, M, K, 128)" in sut.program


def test_a_gfx942_plan_swizzles_lds_and_runs_eight_mfma_per_k_block():
    sut = tile.plan("gfx942", 64, 128, 64, "f16", "f32")

    assert "chunk ^ (row % 8)" in sut.layout
    assert any("8 x v_mfma_f32_32x32x8_f16" in step for step in sut.steps)
    assert "alloy_gemm_64x64x64<<<dim3(N / 64, M / 64), 256>>>" in sut.program


@pytest.mark.parametrize(("target", "shape", "types", "reason"), [
    ("sm90", (64, 64, 100), ("f16", "f32"), "K a multiple of 64"),
    ("sm90", (32, 64, 64), ("f16", "f32"), "64x64 blocks, 128x128 blocks"),
    ("gfx942", (64, 64, 64), ("f32", "f32"), "--in f16 --acc f32"),
])  # fmt: skip
def test_a_gpu_tile_the_kernels_do_not_cover_is_refused_with_what_they_take(target, shape, types, reason):
    with pytest.raises(KeyError, match=reason):
        tile.plan(target, *shape, *types)


@pytest.mark.cuda
def test_the_sm90_program_compiles_for_sm90a():
    sut = tile.verify(tile.plan("sm90", 128, 128, 128, "f16", "f32"))

    assert sut.verified in ("compiled", "run"), sut.detail


@pytest.mark.hip
def test_the_gfx942_program_compiles_for_gfx942():
    sut = tile.verify(tile.plan("gfx942", 64, 64, 128, "f16", "f32"))

    assert sut.verified in ("compiled", "run"), sut.detail
