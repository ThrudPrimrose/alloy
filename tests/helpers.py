# Copyright 2026 ETH Zurich and the Alloy authors.
"""Shared test helpers: example programs, the shipped matrix, and matrix variants."""

import pathlib
import subprocess

from alloy import configuration_matrix
from alloy.cli import load_program
from alloy.evaluate import verify
from alloy.frontend import inputs, regions

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


SCALE_MANIFEST = """name: scale
level: 1
parameters:
  S:
    N: 512
  fuzzed:
    N: [64, 512]
init:
  arrays:
    a: (N,)
    out: (N,)
input_args: [a, out]
output_args: [out]
"""
ROW_SUM_MANIFEST = """name: row sum
level: 1
parameters:
  S:
    M: 64
    N: 512
  fuzzed:
    M: [16, 64]
    N: [256, 1024]
init:
  arrays:
    a: (M, N)
    out: (M,)
input_args: [a, out]
output_args: [out]
"""


def program_and_cases(tmp: pathlib.Path, kernel: str, manifest_text: str) -> tuple[regions.Program, verify.Cases]:
    manifest = write_manifest(tmp, kernel, manifest_text)
    program = regions.outline(load_program(f"{REDUCTIONS}:{kernel}"), MATRIX.libm_calls)
    return program, verify.Cases([inputs.draw(manifest, i) for i in range(2)], manifest.outputs)


def write_manifest(tmp: pathlib.Path, kernel: str, manifest_text: str) -> inputs.Manifest:
    path = tmp / f"{kernel}.yaml"
    path.write_text(manifest_text)
    return inputs.load(path, kernel)


def handwritten_archive(tmp: pathlib.Path, region: regions.Region, body: str) -> pathlib.Path:
    """``lib<symbol>.a`` defining the region's entry with ``body``, outside every candidate."""
    source, obj, archive = tmp / "hand.c", tmp / "hand.o", tmp / "libhand.a"
    signature = region.signature.replace("__restrict__", "restrict")
    headers = "#include <omp.h>\n#include <stdint.h>\n#include <stdlib.h>\n"
    source.write_text(f"{headers}void {region.symbol}({signature}) {{ {body} }}\n")
    subprocess.run(["gcc", "-O2", "-fPIC", "-c", str(source), "-o", str(obj)], check=True)
    subprocess.run(["ar", "rcs", str(archive), str(obj)], check=True)
    return archive
