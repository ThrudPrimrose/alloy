# Copyright 2026 ETH Zurich and the Alloy authors.
"""Alloy as DaCe's backend: the compiled program keeps the SDFG's signature, links every scope from the build Alloy
picked, and computes what DaCe's own build computes; ``SDFG.compile`` hands over when ``compiler.build_plugin``
names Alloy's entry point."""

import pathlib
import subprocess

import dace
import numpy as np
import pytest
from dace.config import set_temporary

from alloy import dace_backend
from alloy.frontend import scopes
from helpers import MATRIX, REDUCTIONS, gcc_only, load_program


def arguments() -> dict[str, np.ndarray | int]:
    a = np.random.default_rng(3).random(1000)
    return {"a": a, "out": np.zeros_like(a), "N": a.size}


def scope_symbol(sdfg: dace.SDFG) -> str:
    (scope,) = scopes.outline(sdfg, MATRIX.libm_calls).scopes
    return scope.symbol


def defined_symbols(library: str) -> set[str]:
    listing = subprocess.run(["nm", "--defined-only", library], capture_output=True, text=True, check=True).stdout
    return {line.split()[-1] for line in listing.splitlines() if line.strip()}


def outputs(program: dace.SDFG | dace.codegen.compiled_sdfg.CompiledSDFG) -> np.ndarray:
    args = arguments()
    program(**args)
    return np.asarray(args["out"])


@pytest.mark.gcc
def test_the_program_alloy_builds_is_called_like_the_sdfg_and_computes_what_dace_computes(tmp_path):
    sdfg = load_program(f"{REDUCTIONS}:scale").to_sdfg()
    expected = outputs(sdfg)

    sut = dace_backend.compile(sdfg, matrix=gcc_only(tmp_path), out=tmp_path / "alloy")

    assert sut is not None
    assert pathlib.Path(sut.filename).is_relative_to(tmp_path / "alloy" / "program")
    assert scope_symbol(sdfg) in defined_symbols(sut.filename), "the scope runs from the archive Alloy linked"
    np.testing.assert_array_equal(outputs(sut), expected)


@pytest.mark.gcc
def test_sdfg_compile_hands_the_sdfg_to_alloy_when_the_build_plugin_names_it(tmp_path):
    sdfg = load_program(f"{REDUCTIONS}:scale").to_sdfg()
    sdfg.build_folder = str(tmp_path / "build")
    expected = outputs(load_program(f"{REDUCTIONS}:scale").to_sdfg())

    with set_temporary("compiler", "build_plugin", value="alloy-speculative"):
        sut = sdfg.compile()

    assert (tmp_path / "build" / "alloy" / "report.md").is_file()
    assert scope_symbol(sdfg) in defined_symbols(sut.filename)
    np.testing.assert_array_equal(outputs(sut), expected)
