# Copyright 2026 ETH Zurich and the Alloy authors.
"""Shared test helpers: example programs, the shipped matrix, and matrix variants."""

import importlib.util
import pathlib
import subprocess

from dace.frontend.python.parser import DaceProgram

from alloy import api, configuration_matrix
from alloy.backend.build import Build, compile_source, deduplicated, write_source
from alloy.backend.candidates import Candidate
from alloy.configuration_matrix import Matrix
from alloy.evaluate import verify
from alloy.frontend import inputs, scopes
from alloy.frontend.scopes import Scope

EXAMPLES = pathlib.Path(__file__).parent.parent / "examples"
EXAMPLE = EXAMPLES / "two_scopes.py"
REDUCTIONS = EXAMPLES / "reductions.py"
MATRIX = configuration_matrix.load()


def load_program(spec: str) -> DaceProgram:
    """The ``@dace.program`` named by ``file.py:function``."""
    path, _, name = spec.partition(":")
    module_spec = importlib.util.spec_from_file_location(pathlib.Path(path).stem, path)
    assert module_spec is not None and module_spec.loader is not None, f"cannot import {path}"
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    program = vars(module)[name]
    assert isinstance(program, DaceProgram), f"{spec} is not a @dace.program"
    return program


def outlined() -> scopes.Program:
    return scopes.outline(load_program(f"{EXAMPLE}:two_scopes").to_sdfg(), MATRIX.libm_calls)


def scope_with(program: scopes.Program, *, libm: bool, reduction: bool) -> scopes.Scope:
    (match,) = [r for r in program.scopes if r.calls_libm == libm and r.has_reduction == reduction]
    return match


def variant(tmp_path: pathlib.Path, old: str, new: str) -> pathlib.Path:
    """The shipped matrix with ``old`` replaced by ``new`` once."""
    text = MATRIX.path.read_text()
    if old not in text:
        raise ValueError(f"{old!r} not in the shipped matrix")
    path = tmp_path / "matrix.toml"
    path.write_text(text.replace(old, new, 1))
    return path


def without_compilers_from(tmp_path: pathlib.Path, section: str) -> configuration_matrix.Matrix:
    """The shipped matrix without the compiler sections from ``section`` to the codegen section."""
    text = MATRIX.path.read_text()
    return configuration_matrix.load(variant(tmp_path, text[text.index(section) : text.index("[codegen.knobs]")], ""))


def gcc_only(tmp_path: pathlib.Path) -> configuration_matrix.Matrix:
    return without_compilers_from(tmp_path, "[compilers.clang]")


def gcc_and_clang(tmp_path: pathlib.Path) -> configuration_matrix.Matrix:
    """The two compilers CI always has."""
    return without_compilers_from(tmp_path, "[compilers.icx]")


SCALE_MANIFEST = """name: scale
level: 1
parameters:
  S:
    N: 512
  fuzzed:
    N: [64, 512]
args:
  a: (N,)
  out: {shape: "(N,)", out: true}
"""
PREFIX_MANIFEST = """name: scale prefix
level: 1
parameters:
  S:
    N: 512
  fuzzed:
    N: [64, 512]
args:
  a: (N,)
  out: {shape: "(N,)", out: true}
  count: {shape: "(1,)", dtype: int64, out: true}
output_extent:
  out: count
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
args:
  a: (M, N)
  out: {shape: "(M,)", out: true}
"""


def program_and_cases(tmp: pathlib.Path, kernel: str, manifest_text: str) -> tuple[scopes.Program, verify.Cases]:
    manifest = write_manifest(tmp, kernel, manifest_text)
    program = scopes.outline(load_program(f"{REDUCTIONS}:{kernel}").to_sdfg(), MATRIX.libm_calls)
    cases = api.test_cases(program, manifest)
    assert cases is not None, "a manifest always gives draws"
    return program, cases


def write_manifest(tmp: pathlib.Path, kernel: str, manifest_text: str) -> inputs.Manifest:
    path = tmp / f"{kernel}.yaml"
    path.write_text(manifest_text)
    return inputs.load(path, f"{REDUCTIONS}:{kernel}")


def handwritten_archive(tmp: pathlib.Path, scope: scopes.Scope, body: str) -> pathlib.Path:
    """``lib<symbol>.a`` defining the scope's entry with ``body``, outside every candidate."""
    source, obj, archive = tmp / "hand.c", tmp / "hand.o", tmp / "libhand.a"
    signature = scope.signature.replace("__restrict__", "restrict")
    headers = "#include <omp.h>\n#include <stdint.h>\n#include <stdlib.h>\n"
    source.write_text(f"{headers}void {scope.symbol}({signature}) {{ {body} }}\n")
    subprocess.run(["gcc", "-O2", "-fPIC", "-c", str(source), "-o", str(obj)], check=True)
    subprocess.run(["ar", "rcs", str(archive), str(obj)], check=True)
    return archive


def build(scope: Scope, candidate: Candidate, matrix: Matrix, folder: pathlib.Path, seen: dict[str, str]) -> Build:
    """Render, compile and archive one candidate, as a sweep does for many."""
    return deduplicated(compile_source(write_source(scope, candidate, matrix, folder, {}), candidate, matrix), seen)
