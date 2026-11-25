# Copyright 2026 ETH Zurich and the Alloy authors.
import pathlib
import re

import dace
import numpy as np
import pytest
from hpcagent_bench import paths
from hpcagent_bench.spec import BenchSpec

from alloy.frontend import inputs
from helpers import REDUCTIONS, SCALE_MANIFEST


def test_a_corpus_kernel_with_its_own_initializer_gets_the_dtypes_its_manifest_declares() -> None:
    """OMEN's initialize() builds complex128 arrays the float64 run precision would not: a draw that skipped it
    handed DaCe half-sized buffers."""
    spec = BenchSpec.load("scattering_self_energies")
    manifest = inputs.load(paths.BENCHMARKS / spec.relative_path / f"{spec.module_name}.yaml")
    # ``Norb`` is a manifest constant (10), not a drawn size
    sizes = {"Nkz": 2, "NE": 4, "Nqz": 2, "Nw": 2, "N3D": 1, "NA": 6, "NB": 2}

    sut = inputs.at(manifest, sizes)

    assert {name: value.dtype for name, value in sut.values.items()} == {
        "neigh_idx": np.dtype(np.int32),
        "dH": np.dtype(np.complex128),
        "G": np.dtype(np.complex128),
        "D": np.dtype(np.complex128),
        "Sigma": np.dtype(np.complex128),
    }
    assert sut.values["G"].shape == (2, 4, 6, 10, 10)


def test_a_manifest_drawn_at_a_datatype_that_is_not_a_string_is_refused_naming_the_file(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "scale.yaml"
    path.write_text(SCALE_MANIFEST)

    with pytest.raises(
        ValueError,
        match=re.escape(f"{path}: not a valid Manifest:\n  datatype: Input should be a valid string, got 64"),
    ):
        inputs.load(path, f"{REDUCTIONS}:scale", datatype=64)  # type: ignore[arg-type]


# Reproducer: a derived boolean argument takes both truth values (aa19cd0)
def test_a_derived_boolean_argument_takes_both_truth_values() -> None:
    sdfg = dace.SDFG("flags")
    sdfg.add_array("mask", [1000], dace.bool_)

    sut = inputs.derived_draw(sdfg, 0)

    assert 0 < np.count_nonzero(sut.values["mask"]) < 1000


# Reproducer: derived draws cover booleans and complex parts (aa19cd0)
def test_a_derived_complex_argument_has_an_imaginary_part() -> None:
    sdfg = dace.SDFG("waves")
    sdfg.add_array("z", [8], dace.complex128)

    sut = inputs.derived_draw(sdfg, 0)

    assert np.all(sut.values["z"].imag != 0)


# Reproducer: a symbol that only bounds a loop is a domain gap (aa19cd0)
def test_a_symbol_that_only_bounds_a_loop_is_a_domain_gap() -> None:
    sdfg = dace.SDFG("indexed")
    sdfg.add_array("a", ["N"], dace.float64)
    sdfg.add_symbol("K", dace.int64)
    sdfg.add_state().add_tasklet("t", {}, {}, "x = K", dace.Language.CPP)

    sut = inputs.domain_gap(sdfg)

    assert "K" in sut


# Reproducer: a specialized size still shapes derived draws (c6b1930)
def test_a_size_padded_by_one_is_still_an_array_extent() -> None:
    sdfg = dace.SDFG("padded")
    sdfg.add_array("a", ["N + 1"], dace.float64)

    sut = inputs.domain_gap(sdfg)

    assert sut == ""


# Reproducer: a specialized size still shapes derived draws (c6b1930)
def test_a_derived_draw_shapes_an_array_whose_size_was_specialized_to_a_constant() -> None:
    sdfg = dace.SDFG("specialized")
    sdfg.add_array("a", ["N"], dace.float64)
    sdfg.add_array("b", [4], dace.float64)
    sdfg.add_constant("N", 10)

    sut = inputs.derived_draw(sdfg, 0)

    assert sut.values["a"].shape == (10,)


# Reproducer: each preset carries the manifest's first config row (K) (cce80a9)
def test_a_preset_carries_the_manifests_first_configuration_the_initializer_reads() -> None:
    """ext_break_capture's initializer reads the config entry ``K``; a timing draw at a bare preset raised
    ``KeyError: 'K'`` and the profile episode delivered nothing (E1b, ault 921253)."""
    spec = BenchSpec.load("ext_break_capture")
    manifest = inputs.load(paths.BENCHMARKS / spec.relative_path / f"{spec.module_name}.yaml")

    sut = inputs.presets(manifest)

    assert all(sizes["K"] == 1 for sizes in sut)
    assert inputs.at(manifest, min(sut, key=lambda sizes: sizes["LEN_1D"])).values["a"].shape == (512,)
