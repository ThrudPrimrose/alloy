# Copyright 2026 ETH Zurich and the Alloy authors.
import re

import dace
import numpy as np
import pytest
from hpcagent_bench import paths
from hpcagent_bench.spec import BenchSpec

from alloy.frontend import inputs
from helpers import REDUCTIONS, SCALE_MANIFEST


def test_a_corpus_kernel_with_its_own_initializer_gets_the_dtypes_its_manifest_declares():
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


def test_a_manifest_drawn_at_a_datatype_that_is_not_a_string_is_refused_naming_the_file(tmp_path):
    path = tmp_path / "scale.yaml"
    path.write_text(SCALE_MANIFEST)

    with pytest.raises(
        ValueError,
        match=re.escape(f"{path}: not a valid Manifest:\n  datatype: Input should be a valid string, got 64"),
    ):
        inputs.load(path, f"{REDUCTIONS}:scale", datatype=64)  # type: ignore[arg-type]


def test_a_derived_boolean_argument_takes_both_truth_values():
    sdfg = dace.SDFG("flags")
    sdfg.add_array("mask", [1000], dace.bool_)

    sut = inputs.derived_draw(sdfg, 0)

    assert 0 < np.count_nonzero(sut.values["mask"]) < 1000


def test_a_derived_complex_argument_has_an_imaginary_part():
    sdfg = dace.SDFG("waves")
    sdfg.add_array("z", [8], dace.complex128)

    sut = inputs.derived_draw(sdfg, 0)

    assert np.all(sut.values["z"].imag != 0)


def test_a_symbol_that_only_bounds_a_loop_is_a_domain_gap():
    sdfg = dace.SDFG("indexed")
    sdfg.add_array("a", ["N"], dace.float64)
    sdfg.add_symbol("K", dace.int64)
    sdfg.add_state().add_tasklet("t", {}, {}, "x = K", dace.Language.CPP)

    sut = inputs.domain_gap(sdfg)

    assert "K" in sut
