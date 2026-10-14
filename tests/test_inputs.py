# Copyright 2026 ETH Zurich and the Alloy authors.
import numpy as np
from hpcagent_bench import paths
from hpcagent_bench.spec import BenchSpec

from alloy.frontend import inputs


def test_a_corpus_kernel_with_its_own_initializer_gets_the_dtypes_its_manifest_declares():
    """OMEN's initialize() builds complex128 arrays the float64 run precision would not: a draw that skipped it
    handed DaCe half-sized buffers."""
    spec = BenchSpec.load("scattering_self_energies")
    manifest = inputs.load(paths.BENCHMARKS / spec.relative_path / f"{spec.module_name}.yaml")
    sizes = {"Nkz": 2, "NE": 4, "Nqz": 2, "Nw": 2, "N3D": 1, "NA": 6, "NB": 2, "Norb": 3}

    sut = inputs.at(manifest, sizes)

    assert {name: value.dtype for name, value in sut.values.items()} == {
        "neigh_idx": np.dtype(np.int32),
        "dH": np.dtype(np.complex128),
        "G": np.dtype(np.complex128),
        "D": np.dtype(np.complex128),
        "Sigma": np.dtype(np.complex128),
    }
    assert sut.values["G"].shape == (2, 4, 6, 3, 3)
