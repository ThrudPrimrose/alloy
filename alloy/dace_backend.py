# Copyright 2026 ETH Zurich and the Alloy authors.
"""Alloy as DaCe's CPU backend: an SDFG in, a ``CompiledSDFG`` out with the SDFG's own signature, every scope linked
from the build Alloy picked. ``SDFG.compile`` calls :func:`speculative` when DaCe's ``compiler.build_plugin`` names
``alloy-speculative`` (an entry point of ``dace.build_plugins``); profile mode needs a manifest, so it goes through
:func:`compile`. The work runs in a process of its own, so a plain script needs no ``__main__`` guard: Alloy's worker
processes re-import ``__main__``, and the worker's is this module. A build is kept under ``out`` and loaded again while
:func:`build_key` stands, so calling a program twice sweeps once."""

import dataclasses
import hashlib
import importlib.metadata
import json
import os
import pathlib
import pickle
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any

import dace
from dace.codegen import compiler
from dace.codegen.compiled_sdfg import CompiledSDFG
from dace.config import Config, set_temporary

from alloy import api, configuration_matrix, machine
from alloy.configuration_matrix import Matrix
from alloy.evaluate.link import Linker, built
from alloy.frontend.inputs import Manifest
from alloy.report import Mode

#: The worker's exit code when no scope outlines, so DaCe's own build applies.
NOTHING_TO_GENERATE = 4
#: The linked program's folder under ``out``, and the file in it naming the :func:`build_key` it was built under.
PROGRAM_FOLDER, KEY_FILE = "program", "build.key"
#: The environment candidates' availability and link resolution read (:mod:`alloy.backend.runtime`).
LIBRARY_SEARCH = ("LIBRARY_PATH", "LD_LIBRARY_PATH")
#: An element's instrumentation in an SDFG's JSON.
INSTRUMENT = re.compile(r'"instrument": "(\w+)"')


def build(job: pathlib.Path) -> None:
    """Run the pickled ``job`` of :func:`compile`: the program lands in its ``out``."""
    with job.open("rb") as handle:
        sdfg_file, manifest, mode, matrix, out, finite_inputs, running = pickle.load(handle)
    sdfg = dace.SDFG.from_file(sdfg_file)
    with set_temporary("compiler", "build_plugin", value=""):  # Alloy's own programs compile the DaCe way
        declared = {"finite_inputs": finite_inputs, "running": running}
        result = api.generate(sdfg, out, manifest=manifest, matrix=matrix, mode=mode, **declared)
        if not result.winners:
            raise RuntimeError(f"{sdfg.name}: Alloy linked no build (profile mode without local timing)")
        archives = {symbol: built(b) for symbol, b in result.winners.items()}
        candidates = frozenset(b.candidate for b in result.winners.values())
        program = Linker(result.program, matrix, out).library_sdfg(archives, candidates)
        program.build_folder = str(out / PROGRAM_FOLDER)
        program.compile(return_program_handle=False)


def compiler_version(executable: str) -> str:
    """Where ``executable`` resolves and the banner it prints; empty when it is absent, which changes the sweep too."""
    path = shutil.which(executable)
    if path is None:
        return ""
    banner = subprocess.run([path, "--version"], capture_output=True, text=True, check=False)
    return f"{path} {banner.stdout}"


def installed(package: str) -> str:
    """``package``'s version and pinned commit, empty when it is absent (the bench is an optional extra)."""
    try:
        distribution = importlib.metadata.distribution(package)
    except importlib.metadata.PackageNotFoundError:
        return ""
    return f"{distribution.version} {distribution.read_text('direct_url.json')}"


def alloy_sources() -> str:
    """A digest of Alloy's own code and tables: an editable install names no commit."""
    digest = hashlib.sha256()
    root = pathlib.Path(__file__).parent
    for path in sorted(p for p in root.rglob("*") if p.suffix in (".py", ".toml")):
        digest.update(path.read_bytes())
    return digest.hexdigest()


def instrumentation(sdfg: dace.SDFG) -> list[str]:
    """What ``sdfg`` asks to instrument, which :meth:`dace.SDFG.hash_sdfg` leaves out."""
    return INSTRUMENT.findall(json.dumps(sdfg.to_json()))


def json_value(value: Any) -> Any:
    """A value ``json`` has no form for: a set's order follows the hash seed, so it is sorted."""
    return sorted(value) if isinstance(value, frozenset | set) else str(value)


def build_key(
    sdfg: dace.SDFG,
    manifest: Manifest | None,
    mode: Mode,
    matrix: Matrix,
    finite_inputs: bool,
    running: dict[str, int] | None = None,
) -> str:
    """A digest of all that decides the program :func:`compile` builds: the SDFG, what the caller declares, the matrix
    and its compilers, the manifest, the packages doing the work, and the host and configuration they read."""
    executables = sorted({e for spelled in matrix.compilers.values() for e in spelled.executables.values()})
    decided_by = {
        "sdfg": (sdfg.name, sdfg.hash_sdfg(), instrumentation(sdfg)),
        "declared": (mode, finite_inputs, running),
        "matrix": dataclasses.asdict(matrix),
        "compilers": [compiler_version(e) for e in executables],
        "manifest": None if manifest is None else (manifest.path, manifest.raw, manifest.datatype),
        "packages": (installed("dace"), installed("hpcagent-bench"), alloy_sources()),
        "host": sorted(machine.cpu_flags()),
        "search": [os.environ.get(name) for name in LIBRARY_SEARCH],
        "dace": Config.get("compiler"),
    }
    return hashlib.sha256(json.dumps(decided_by, sort_keys=True, default=json_value).encode()).hexdigest()


def run_worker(
    sdfg: dace.SDFG,
    manifest: Manifest | None,
    mode: Mode,
    matrix: Matrix,
    out: pathlib.Path,
    finite_inputs: bool,
    running: dict[str, int] | None,
) -> subprocess.CompletedProcess[str]:
    """:func:`build` for these arguments in a process of its own."""
    with tempfile.TemporaryDirectory(prefix="alloy_job_") as folder:
        job = pathlib.Path(folder) / "job.pickle"
        sdfg_file = pathlib.Path(folder) / "program.sdfg"
        sdfg.save(str(sdfg_file))
        with job.open("wb") as handle:
            pickle.dump((sdfg_file, manifest, mode, matrix, out, finite_inputs, running), handle)
        return subprocess.run(
            [sys.executable, "-m", "alloy.dace_backend", str(job)], check=False, capture_output=True, text=True
        )


def compile(
    sdfg: dace.SDFG,
    *,
    manifest: Manifest | None = None,
    mode: Mode = Mode.SPECULATIVE,
    matrix: Matrix | None = None,
    out: pathlib.Path | None = None,
    finite_inputs: bool = False,
    running: dict[str, int] | None = None,
    output_file: str | None = None,
    validate: bool = True,
    return_program_handle: bool = True,
) -> CompiledSDFG | None:
    """Run Alloy on ``sdfg`` (under ``out``, default ``<build folder>/alloy``) and compile the outlined program with
    each scope's linked build: called with the same arguments as ``sdfg``. A program with no scope builds the DaCe way.
    Profile mode needs a manifest (:func:`api.generate`); ``finite_inputs`` declares no input is NaN or Inf, ``running``
    the sizes the program will be called at (``SDFG.compile`` has no way to say). A build under ``out`` with the same
    :func:`build_key` is loaded, not repeated."""
    matrix = matrix or configuration_matrix.load()
    out = out or pathlib.Path(sdfg.build_folder) / "alloy"
    out.mkdir(parents=True, exist_ok=True)
    if validate:
        sdfg.validate()
    key = build_key(sdfg, manifest, mode, matrix, finite_inputs, running)
    folder, stamp = out / PROGRAM_FOLDER, out / PROGRAM_FOLDER / KEY_FILE
    if not stamp.is_file() or stamp.read_text() != key:
        stamp.unlink(missing_ok=True)  # a build that dies below leaves no key over its half-written program
        run = run_worker(sdfg, manifest, mode, matrix, out, finite_inputs, running)
        if run.returncode == NOTHING_TO_GENERATE:
            with set_temporary("compiler", "build_plugin", value=""):
                handle = return_program_handle
                return sdfg.compile(output_file=output_file, validate=False, return_program_handle=handle)
        if run.returncode != 0:
            raise RuntimeError(f"{sdfg.name}: Alloy failed:\n{run.stderr[-3000:]}")
        stamp.write_text(key)
    program = compiler.load_precompiled_sdfg(folder)
    if output_file is not None:
        shutil.copyfile(program.filename, output_file)
    return program if return_program_handle else None


def speculative(sdfg: dace.SDFG, **compile_args: Any) -> CompiledSDFG | None:
    """``alloy-speculative``: every scope's pick predicted, verified when no input needs a manifest."""
    return compile(sdfg, mode=Mode.SPECULATIVE, **compile_args)


if __name__ == "__main__":
    try:
        build(pathlib.Path(sys.argv[1]))
    except api.NothingToGenerate:
        sys.exit(NOTHING_TO_GENERATE)
