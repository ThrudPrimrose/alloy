# Copyright 2026 ETH Zurich and the Alloy authors.
"""Alloy as DaCe's CPU backend: an SDFG in, a ``CompiledSDFG`` out with the SDFG's own signature, every scope linked
from the build Alloy picked. ``SDFG.compile`` calls :func:`speculative` when DaCe's ``compiler.build_plugin`` names
``alloy-speculative`` (an entry point of ``dace.build_plugins``); profile mode needs a manifest, so it goes through
:func:`compile`. The work runs in a process of its own, so a plain script needs no ``__main__`` guard: Alloy's worker
processes re-import ``__main__``, and the worker's is this module."""

import pathlib
import pickle
import shutil
import subprocess
import sys
import tempfile
from typing import Any

import dace
from dace.codegen import compiler
from dace.codegen.compiled_sdfg import CompiledSDFG
from dace.config import set_temporary

from alloy import api, configuration_matrix
from alloy.configuration_matrix import Matrix
from alloy.evaluate.link import Linker, built
from alloy.frontend.inputs import Manifest
from alloy.report import Mode

#: The worker's exit code when no scope outlines, so DaCe's own build applies.
NOTHING_TO_GENERATE = 4


def build(job: pathlib.Path) -> pathlib.Path:
    """Run the pickled ``job`` of :func:`compile`: the folder of the program it built."""
    with job.open("rb") as handle:
        sdfg_file, manifest, mode, matrix, out, finite_inputs = pickle.load(handle)  # noqa: S301 -- our own file
    sdfg = dace.SDFG.from_file(sdfg_file)
    with set_temporary("compiler", "build_plugin", value=""):  # Alloy's own programs compile the DaCe way
        result = api.generate(sdfg, out, manifest=manifest, matrix=matrix, mode=mode, finite_inputs=finite_inputs)
        if not result.winners:
            raise RuntimeError(f"{sdfg.name}: Alloy linked no build (profile mode without local timing)")
        archives = {symbol: built(b) for symbol, b in result.winners.items()}
        candidates = frozenset(b.candidate for b in result.winners.values())
        program = Linker(result.program, matrix, out).library_sdfg(archives, candidates)
        program.build_folder = str(out / "program")
        program.compile(return_program_handle=False)
    return pathlib.Path(program.build_folder)


def compile(  # noqa: A001 -- DaCe's verb
    sdfg: dace.SDFG,
    *,
    manifest: Manifest | None = None,
    mode: Mode = Mode.SPECULATIVE,
    matrix: Matrix | None = None,
    out: pathlib.Path | None = None,
    finite_inputs: bool = False,
    output_file: str | None = None,
    validate: bool = True,
    return_program_handle: bool = True,
) -> CompiledSDFG | None:
    """Run Alloy on ``sdfg`` (under ``out``, default ``<build folder>/alloy``) and compile the outlined program with
    each scope's linked build: called with the same arguments as ``sdfg``. A program with no scope builds the DaCe way.
    Profile mode needs a manifest (:func:`api.generate`); ``finite_inputs`` declares no input is NaN or Inf."""
    matrix = matrix or configuration_matrix.load()
    out = out or pathlib.Path(sdfg.build_folder) / "alloy"
    out.mkdir(parents=True, exist_ok=True)
    if validate:
        sdfg.validate()
    with tempfile.TemporaryDirectory(prefix="alloy_job_") as folder:
        job = pathlib.Path(folder) / "job.pickle"
        sdfg_file = pathlib.Path(folder) / "program.sdfg"
        sdfg.save(str(sdfg_file))
        with job.open("wb") as handle:
            pickle.dump((sdfg_file, manifest, mode, matrix, out, finite_inputs), handle)
        run = subprocess.run(
            [sys.executable, "-m", "alloy.dace_backend", str(job)], check=False, capture_output=True, text=True
        )
    if run.returncode == NOTHING_TO_GENERATE:
        with set_temporary("compiler", "build_plugin", value=""):
            return sdfg.compile(output_file=output_file, validate=False, return_program_handle=return_program_handle)
    if run.returncode != 0:
        raise RuntimeError(f"{sdfg.name}: Alloy failed:\n{run.stderr[-3000:]}")
    program = compiler.load_precompiled_sdfg(run.stdout.strip().splitlines()[-1])
    if output_file is not None:
        shutil.copyfile(program.filename, output_file)
    return program if return_program_handle else None


def speculative(sdfg: dace.SDFG, **compile_args: Any) -> CompiledSDFG | None:
    """``alloy-speculative``: every scope's pick predicted, verified when no input needs a manifest."""
    return compile(sdfg, mode=Mode.SPECULATIVE, **compile_args)


if __name__ == "__main__":
    try:
        print(build(pathlib.Path(sys.argv[1])))
    except api.NothingToGenerate:
        sys.exit(NOTHING_TO_GENERATE)
