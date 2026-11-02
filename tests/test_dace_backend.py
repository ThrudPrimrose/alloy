# Copyright 2026 ETH Zurich and the Alloy authors.
"""Alloy as DaCe's backend: the compiled program keeps the SDFG's signature, links every scope from the build Alloy
picked, and computes what DaCe's own build computes; ``SDFG.compile`` hands over when ``compiler.build_plugin``
names Alloy's entry point."""

import dataclasses
import os
import pathlib
import pickle
import subprocess
from typing import Any

import dace
import numpy as np
import pytest
from dace.codegen import compiler
from dace.config import set_temporary
from dace.sdfg import nodes

from alloy import api, configuration_matrix, dace_backend, machine
from alloy.configuration_matrix import Matrix
from alloy.frontend import scopes
from alloy.frontend.inputs import Manifest
from alloy.heuristics import predict
from alloy.report import Mode
from helpers import (
    MATRIX,
    REDUCTIONS,
    SCALE_MANIFEST,
    gcc_only,
    handwritten_archive,
    load_program,
    variant,
    write_manifest,
)


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


def built_outputs(matrix: Matrix, out: pathlib.Path) -> np.ndarray:
    """``scale`` built and run; its handle ends with the call, as one a program keeps would warn the next load."""
    program = dace_backend.compile(load_program(f"{REDUCTIONS}:scale").to_sdfg(), matrix=matrix, out=out)
    assert program is not None
    return outputs(program)


@pytest.mark.gcc
def test_a_second_compile_of_the_same_program_loads_the_first_build(tmp_path):
    matrix, out = gcc_only(tmp_path), tmp_path / "alloy"
    expected = built_outputs(matrix, out)
    swept = (out / "report.md").stat().st_mtime_ns

    sut = built_outputs(matrix, out)

    assert (out / "report.md").stat().st_mtime_ns == swept, "nothing swept again"
    np.testing.assert_array_equal(sut, expected)


@pytest.mark.gcc
def test_the_program_links_the_build_alloy_picked(tmp_path, monkeypatch):
    """The picked build is wrong on purpose: only a program that really links it computes 3 * a."""
    sdfg_file, out, matrix = tmp_path / "program.sdfg", tmp_path / "alloy", gcc_only(tmp_path)
    load_program(f"{REDUCTIONS}:scale").to_sdfg().save(str(sdfg_file))
    job = tmp_path / "job.pickle"
    job.write_bytes(pickle.dumps((sdfg_file, None, Mode.SPECULATIVE, matrix, out, False)))
    generate = api.generate

    def wrong_pick(*args: Any, **kwargs: Any) -> api.Result:
        result = generate(*args, **kwargs)
        (scope,) = result.program.scopes
        wrong = handwritten_archive(tmp_path, scope, "for (int64_t i = 0; i < N; ++i) out[i] = 3.0 * a[i];")
        assert result.winners is not None
        winner = dataclasses.replace(result.winners[scope.symbol], archive=wrong)
        return dataclasses.replace(result, winners={scope.symbol: winner})

    monkeypatch.setattr(api, "generate", wrong_pick)
    monkeypatch.setattr(predict, "predictions", lambda *_: {})  # measures the machine, and the pick is not the point
    dace_backend.build(job)

    sut = compiler.load_precompiled_sdfg(out / dace_backend.PROGRAM_FOLDER)

    args = arguments()
    sut(**args)
    np.testing.assert_array_equal(args["out"], 3.0 * args["a"])


def doubled(sdfg: dace.SDFG, constant: str) -> dace.SDFG:
    """``sdfg`` with the constant of its one arithmetic tasklet replaced."""
    (tasklet,) = [
        n for n, _ in sdfg.all_nodes_recursive() if isinstance(n, nodes.Tasklet) and "2.0" in n.code.as_string
    ]
    tasklet.code.as_string = tasklet.code.as_string.replace("2.0", constant)
    return sdfg


@pytest.mark.gcc
def test_a_changed_program_never_loads_the_build_of_the_old_one(tmp_path):
    matrix, out = gcc_only(tmp_path), tmp_path / "alloy"
    dace_backend.compile(load_program(f"{REDUCTIONS}:scale").to_sdfg(), matrix=matrix, out=out)
    changed = doubled(load_program(f"{REDUCTIONS}:scale").to_sdfg(), "3.0")

    sut = dace_backend.compile(changed, matrix=matrix, out=out)

    args = arguments()
    assert sut is not None
    sut(**args)
    np.testing.assert_array_equal(args["out"], 3.0 * args["a"])


def key_of(
    sdfg: dace.SDFG,
    matrix: Matrix = MATRIX,
    manifest: Manifest | None = None,
    mode: Mode = Mode.SPECULATIVE,
    finite_inputs: bool = False,
) -> str:
    return dace_backend.build_key(sdfg, manifest, mode, matrix, finite_inputs)


def scale_sdfg() -> dace.SDFG:
    return load_program(f"{REDUCTIONS}:scale").to_sdfg()


def test_two_frontend_runs_of_one_program_share_a_build_key():
    assert key_of(scale_sdfg()) == key_of(scale_sdfg())


def test_the_build_key_changes_with_the_program():
    assert key_of(doubled(scale_sdfg(), "3.0")) != key_of(scale_sdfg())


def test_the_build_key_changes_with_the_program_name_the_library_exports():
    renamed = scale_sdfg()
    renamed.name = "other"  # pyright: ignore[reportAttributeAccessIssue] -- DaCe Property descriptor

    assert key_of(renamed) != key_of(scale_sdfg())


def test_the_build_key_changes_with_what_the_program_instruments():
    timed = scale_sdfg()
    timed.instrument = dace.InstrumentationType.Timer

    assert key_of(timed) != key_of(scale_sdfg())


def test_the_build_key_changes_with_the_matrix():
    flags = dataclasses.replace(MATRIX, build_flags=(*MATRIX.build_flags, "-funroll-loops"))

    assert key_of(scale_sdfg(), flags) != key_of(scale_sdfg())


def test_the_build_key_changes_with_the_manifest_and_what_it_draws(tmp_path):
    manifest = write_manifest(tmp_path, "scale", SCALE_MANIFEST)
    wider = write_manifest(tmp_path, "scale", SCALE_MANIFEST.replace("[64, 512]", "[64, 1024]"))

    assert key_of(scale_sdfg(), manifest=manifest) != key_of(scale_sdfg())
    assert key_of(scale_sdfg(), manifest=wider) != key_of(scale_sdfg(), manifest=manifest)
    narrow = dataclasses.replace(manifest, datatype="float32")
    assert key_of(scale_sdfg(), manifest=narrow) != key_of(scale_sdfg(), manifest=manifest)


def test_the_build_key_changes_with_what_the_caller_declares():
    plain = key_of(scale_sdfg())

    assert key_of(scale_sdfg(), finite_inputs=True) != plain
    assert key_of(scale_sdfg(), mode=Mode.PROFILE) != plain


def test_the_build_key_changes_with_a_compilers_version(tmp_path, monkeypatch):
    matrix = gcc_only(tmp_path)
    fake = tmp_path / "gcc"
    fake.write_text("#!/bin/sh\necho gcc 14.1\n")
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")
    old = key_of(scale_sdfg(), matrix)

    fake.write_text("#!/bin/sh\necho gcc 14.2\n")

    assert key_of(scale_sdfg(), matrix) != old


def test_the_build_key_changes_with_the_host_and_the_library_search_path(monkeypatch):
    plain = key_of(scale_sdfg())
    monkeypatch.setenv("LIBRARY_PATH", "/opt/vector/lib")
    searched = key_of(scale_sdfg())
    monkeypatch.setattr(machine, "cpu_flags", lambda: frozenset({"sve"}))

    assert searched != plain
    assert key_of(scale_sdfg()) != searched


def test_the_build_key_changes_with_dace_compiler_configuration():
    plain = key_of(scale_sdfg())

    with set_temporary("compiler", "cpu", "args", value="-O1"):
        assert key_of(scale_sdfg()) != plain


def test_the_build_key_of_an_absent_compiler_is_still_a_key(tmp_path):
    missing = configuration_matrix.load(variant(tmp_path, 'c = "gcc"', 'c = "no-such-gcc"'))

    assert key_of(scale_sdfg(), missing) != key_of(scale_sdfg())
