# Copyright 2026 ETH Zurich and the Alloy authors.
"""Render a region under a candidate, compile it to a static archive, and keep the vectorizer's remarks."""

import hashlib
import pathlib
import re
import subprocess
from contextlib import ExitStack
from dataclasses import dataclass, replace

from dace.codegen import cpf
from dace.config import set_temporary

from alloy.backend import runtime
from alloy.backend.candidates import Candidate
from alloy.configuration_matrix import Matrix
from alloy.frontend.regions import Region

REMARK_LINE = re.compile(r":\d+:\d+: (?:remark|optimized|missed|note): (.*?)(?: \[-R[^\]]+\])?$")
#: nvc's -Minfo lines carry no file name: ``     25, Generated vector simd code for the loop``.
NVHPC_REMARK = re.compile(r"^\s+\d+, (.*)$")


#: A rendering's identity: the language and every codegen knob it was rendered with.
RenderKey = tuple[str, tuple[tuple[str, str], ...]]


@dataclass(slots=True, frozen=True)
class Remarks:
    """Vectorizer outcome of one compile: loops vectorized, and the distinct reasons loops were not."""

    vectorized: int
    missed: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class Build:
    """One compiled candidate. ``duplicate_of`` names an earlier candidate with a byte-identical object."""

    candidate: Candidate
    name: str
    codegen_params: dict[str, str]
    source: pathlib.Path
    archive: pathlib.Path | None
    flags: tuple[str, ...]
    object_hash: str
    remarks: Remarks
    error: str = ""
    duplicate_of: str = ""


def render(region: Region, candidate: Candidate, matrix: Matrix) -> str:
    """The region's CPF translation unit under ``candidate``'s language and codegen knobs."""
    with ExitStack() as stack:
        for knob, value in candidate.codegen_params(matrix).items():
            stack.enter_context(set_temporary("compiler", "cpu", "codegen_params", knob, value=value))
        rendering = cpf.render(
            region.sdfg,
            language=matrix.languages[candidate.language].render,
            signature=cpf.EntrySignature(order=list(region.abi_order)),
            check_compiles=False,
        )
    return rendering.code


def parse_remarks(log: str, source: pathlib.Path) -> Remarks:
    """Count vectorized loops and collect missed reasons from a compiler's diagnostics about ``source``."""
    vectorized, missed = 0, []
    for line in log.splitlines():
        match = REMARK_LINE.search(line) if source.name in line else NVHPC_REMARK.match(line)
        if match is None:
            continue
        text = match.group(1)
        if "loop vectorized" in text or "vectorized loop" in text or "Generated vector" in text:
            vectorized += 1
        elif "not vectorized" in text or "couldn't vectorize" in text:
            missed.append(text.strip())
    return Remarks(vectorized=vectorized, missed=tuple(dict.fromkeys(missed)))


def code_hash(obj: pathlib.Path) -> str:
    """Hash of the object's code: stripped of the file symbol and ``.comment``, which name the source file and the
    compiler and would make every candidate's object unique."""
    stripped = obj.with_suffix(".stripped.o")
    subprocess.run(["strip", "--strip-unneeded", "-R", ".comment", "-o", str(stripped), str(obj)], check=True)
    digest = hashlib.sha256(stripped.read_bytes()).hexdigest()[:16]
    stripped.unlink()
    return digest


def compile_candidate(
    source: pathlib.Path, candidate: Candidate, matrix: Matrix, flags: tuple[str, ...]
) -> subprocess.CompletedProcess[str]:
    """Compile ``source`` with ``flags`` and the compiler's remark flags to ``<stem>.o`` next to it."""
    compiler = matrix.compilers[candidate.compiler]
    executable, remarks = compiler.executables[candidate.language], compiler.remarks
    command = [executable, *flags, *remarks, "-c", str(source), "-o", str(source.with_suffix(".o"))]
    return subprocess.run(command, capture_output=True, text=True, check=False)


def write_source(
    region: Region, candidate: Candidate, matrix: Matrix, folder: pathlib.Path, renders: dict[RenderKey, str]
) -> pathlib.Path:
    """Write ``candidate``'s translation unit into ``folder``. ``renders`` memoizes the text by language and codegen
    knobs, which most candidates share (they differ only in compile flags)."""
    folder.mkdir(parents=True, exist_ok=True)
    key = (candidate.language, tuple(sorted(candidate.codegen_params(matrix).items())))
    if key not in renders:
        renders[key] = render(region, candidate, matrix)
    source = folder / f"{candidate.name(matrix)}.{matrix.languages[candidate.language].suffix}"
    source.write_text(renders[key])
    return source


def compile_source(source: pathlib.Path, candidate: Candidate, matrix: Matrix) -> Build:
    """Compile and archive the unit :func:`write_source` wrote; safe to run concurrently for distinct candidates."""
    name, params = candidate.name(matrix), candidate.codegen_params(matrix)
    flags = candidate.flags(matrix)
    proc = compile_candidate(source, candidate, matrix, flags)
    source.with_suffix(".log").write_text(proc.stderr)
    remarks = parse_remarks(proc.stderr, source)
    if proc.returncode != 0:
        return Build(candidate, name, params, source, None, flags, "", remarks, error=proc.stderr.strip()[-2000:])
    obj = source.with_suffix(".o")
    if missing := runtime.unresolved(obj, runtime.default_library(matrix)):
        error = f"the {matrix.defaults.openmp_runtime} runtime does not export {', '.join(missing)}"
        return Build(candidate, name, params, source, None, flags, "", remarks, error=error)
    archive = source.parent / f"lib{name}.a"
    subprocess.run(["ar", "rcs", str(archive), str(obj)], check=True)
    return Build(candidate, name, params, source, archive, flags, code_hash(obj), remarks)


def deduplicated(built: Build, seen: dict[str, str]) -> Build:
    """``built`` pointing at the first candidate in ``seen`` (object hash -> name) with the same object."""
    if built.archive is None:
        return built
    first = seen.setdefault(built.object_hash, built.name)
    return built if first == built.name else replace(built, duplicate_of=first)


def build(region: Region, candidate: Candidate, matrix: Matrix, folder: pathlib.Path, seen: dict[str, str]) -> Build:
    """Render, compile and archive ``candidate``. ``seen`` maps object hashes to the first candidate that
    produced them, so a duplicate keeps its record but points at the original."""
    return deduplicated(compile_source(write_source(region, candidate, matrix, folder, {}), candidate, matrix), seen)
