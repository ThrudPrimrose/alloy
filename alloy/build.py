# Copyright 2026 ETH Zurich and the Alloy authors.
"""Render a region under a candidate, compile it to a static archive, and keep the vectorizer's remarks."""

import hashlib
import pathlib
import re
import subprocess
from contextlib import ExitStack
from dataclasses import dataclass

from dace.codegen import cpf
from dace.config import set_temporary

from alloy.candidates import COMPILERS, Candidate
from alloy.regions import Region

GCC_REMARKS = ("-fopt-info-vec-optimized", "-fopt-info-vec-missed")
CLANG_REMARKS = ("-Rpass=loop-vectorize", "-Rpass-missed=loop-vectorize", "-Rpass-analysis=loop-vectorize")
REMARK_LINE = re.compile(r":\d+:\d+: (?:remark|optimized|missed|note): (.*?)(?: \[-R[^\]]+\])?$")


@dataclass(slots=True, frozen=True)
class Remarks:
    """Vectorizer outcome of one compile: loops vectorized, and the distinct reasons loops were not."""

    vectorized: int
    missed: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class Build:
    """One compiled candidate. ``duplicate_of`` names an earlier candidate with a byte-identical object."""

    candidate: Candidate
    source: pathlib.Path
    archive: pathlib.Path | None
    flags: tuple[str, ...]
    object_hash: str
    remarks: Remarks
    error: str = ""
    duplicate_of: str = ""


def render(region: Region, candidate: Candidate) -> str:
    """The region's CPF translation unit under ``candidate``'s language and codegen knobs."""
    with ExitStack() as stack:
        for knob, value in candidate.codegen_params().items():
            stack.enter_context(set_temporary("compiler", "cpu", "codegen_params", knob, value=value))
        rendering = cpf.render(
            region.sdfg, language=candidate.language, order=list(region.abi_order), check_compiles=False
        )
    return rendering.code


def parse_remarks(log: str, source: pathlib.Path) -> Remarks:
    """Count vectorized loops and collect missed reasons from a compiler's diagnostics about ``source``."""
    vectorized, missed = 0, []
    for line in log.splitlines():
        if source.name not in line:
            continue
        match = REMARK_LINE.search(line)
        if match is None:
            continue
        text = match.group(1)
        if "loop vectorized" in text or "vectorized loop" in text:
            vectorized += 1
        elif "not vectorized" in text or "couldn't vectorize" in text or "loop not vectorized" in text:
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


def compile_candidate(source: pathlib.Path, candidate: Candidate) -> tuple[subprocess.CompletedProcess, tuple]:
    """Compile ``source`` to ``<stem>.o`` next to it; returns the process and the flags used."""
    compiler = COMPILERS[candidate.compiler][candidate.language]
    remarks = GCC_REMARKS if candidate.compiler == "gcc" else CLANG_REMARKS
    flags = candidate.flags()
    command = [compiler, *flags, *remarks, "-c", str(source), "-o", str(source.with_suffix(".o"))]
    return subprocess.run(command, capture_output=True, text=True), flags


def build(region: Region, candidate: Candidate, folder: pathlib.Path, seen: dict[str, str]) -> Build:
    """Render, compile and archive ``candidate``. ``seen`` maps object hashes to the first candidate that
    produced them, so a duplicate keeps its record but points at the original."""
    folder.mkdir(parents=True, exist_ok=True)
    source = folder / f"{candidate.name}.{'c' if candidate.language == 'c' else 'cpp'}"
    source.write_text(render(region, candidate))
    proc, flags = compile_candidate(source, candidate)
    (folder / f"{candidate.name}.log").write_text(proc.stderr)
    remarks = parse_remarks(proc.stderr, source)
    if proc.returncode != 0:
        return Build(candidate, source, None, flags, "", remarks, error=proc.stderr.strip()[-2000:])
    obj = source.with_suffix(".o")
    digest = code_hash(obj)
    archive = folder / f"lib{candidate.name}.a"
    subprocess.run(["ar", "rcs", str(archive), str(obj)], check=True)
    duplicate = seen.setdefault(digest, candidate.name)
    return Build(
        candidate,
        source,
        archive,
        flags,
        digest,
        remarks,
        duplicate_of="" if duplicate == candidate.name else duplicate,
    )
