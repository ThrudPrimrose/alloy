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
