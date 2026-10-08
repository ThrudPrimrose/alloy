# Copyright 2026 ETH Zurich and the Alloy authors.
"""Shared test helpers: example programs, the shipped matrix, and matrix variants."""

import pathlib

from alloy import configuration_matrix, regions
from alloy.cli import load_program

EXAMPLES = pathlib.Path(__file__).parent.parent / "examples"
EXAMPLE = EXAMPLES / "two_regions.py"
REDUCTIONS = EXAMPLES / "reductions.py"
MATRIX = configuration_matrix.load()


def outlined() -> regions.Program:
    return regions.outline(load_program(f"{EXAMPLE}:two_regions"), MATRIX.libm_calls)


def region_with(program: regions.Program, *, libm: bool, reduction: bool) -> regions.Region:
    (match,) = [r for r in program.regions if r.calls_libm == libm and r.has_reduction == reduction]
    return match


def variant(tmp_path: pathlib.Path, old: str, new: str) -> pathlib.Path:
    """The shipped matrix with ``old`` replaced by ``new`` once."""
    text = MATRIX.path.read_text()
    if old not in text:
        raise ValueError(f"{old!r} not in the shipped matrix")
    path = tmp_path / "matrix.toml"
    path.write_text(text.replace(old, new, 1))
    return path


def gcc_only(tmp_path: pathlib.Path) -> configuration_matrix.Matrix:
    text = MATRIX.path.read_text()
    first, last = text.index("# clang 22"), text.index("# Readable-codegen knobs")
    return configuration_matrix.load(variant(tmp_path, text[first:last], ""))
