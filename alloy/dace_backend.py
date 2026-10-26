# Copyright 2026 ETH Zurich and the Alloy authors.
"""Alloy as DaCe's CPU backend: an SDFG in, a ``CompiledSDFG`` out with the SDFG's own signature, every scope linked
from the build Alloy picked. DaCe calls :func:`compile` from ``SDFG.compile`` when ``compiler.alloy.mode`` is set."""

import pathlib
from typing import Any

import dace
from dace.codegen.compiled_sdfg import CompiledSDFG
from dace.config import Config, set_temporary

from alloy import api, configuration_matrix
from alloy.configuration_matrix import Matrix
from alloy.evaluate.link import Linker, built
from alloy.frontend.inputs import Manifest
from alloy.report import Mode


def compile(  # noqa: A001 -- DaCe's verb
    sdfg: dace.SDFG,
    *,
    manifest: Manifest | None = None,
    mode: Mode | None = None,
    matrix: Matrix | None = None,
    out: pathlib.Path | None = None,
    **compile_args: Any,
) -> CompiledSDFG | None:
    """Run Alloy on ``sdfg`` (under ``out``, default ``<build folder>/alloy``; ``mode`` defaults to
    ``compiler.alloy.mode``, speculative when that is off) and compile the outlined program with each scope's linked
    build through DaCe: called with the same arguments as ``sdfg``. ``compile_args`` go to ``SDFG.compile``. Profile
    mode needs a manifest (:func:`api.generate`)."""
    matrix = matrix or configuration_matrix.load()
    configured = Config.get("compiler", "alloy", "mode")
    mode = mode or (Mode(configured) if configured != "off" else Mode.SPECULATIVE)
    out = out or pathlib.Path(sdfg.build_folder) / "alloy"
    with set_temporary("compiler", "alloy", "mode", value="off"):  # Alloy's own programs compile the DaCe way
        result = api.generate(sdfg, out, manifest=manifest, matrix=matrix, mode=mode)
        if not result.winners:
            raise RuntimeError(f"{sdfg.name}: Alloy linked no build (profile mode without local timing)")
        archives = {symbol: built(b) for symbol, b in result.winners.items()}
        candidates = frozenset(b.candidate for b in result.winners.values())
        program = Linker(result.program, matrix, out).library_sdfg(archives, candidates)
        program.build_folder = str(out / "program")
        return program.compile(**compile_args)
