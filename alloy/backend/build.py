# Copyright 2026 ETH Zurich and the Alloy authors.
"""Render a scope under a candidate, compile it to a static archive, and keep the vectorizer's remarks."""

import copy
import hashlib
import pathlib
import re
import subprocess
from contextlib import ExitStack
from dataclasses import dataclass, replace

import dace
from dace.codegen import cpf
from dace.config import set_temporary
from dace.transformation.dataflow.sve.vectorization import SVEVectorization

from alloy.backend import runtime
from alloy.backend.candidates import Candidate, RenderKey
from alloy.configuration_matrix import Matrix
from alloy.frontend.scopes import Scope

REMARK_LINE = re.compile(r":\d+:\d+: (?:remark|optimized|missed|note): (.*?)(?: \[-R[^\]]+\])?$")
#: nvc's -Minfo lines carry no file name: ``     25, Generated vector simd code for the loop``.
NVHPC_REMARK = re.compile(r"^\s+\d+, (.*)$")
#: A masked loop: an AVX-512 opmask operand (``{%k1}``) or an SVE loop predicate (``whilelo``, ``whilelt``). Every SVE
#: instruction names a governing predicate (``p7/m``), all-true under ``ptrue`` in an unmasked loop, so those don't count.
MASKED_OPERAND = re.compile(r"\{%k[1-7]\}|\bwhile(?:lo|lt|le|ls)\b")


@dataclass(slots=True, frozen=True)
class Remarks:
    """Vectorizer outcome of one compile: loops vectorized, and the distinct reasons loops were not."""

    vectorized: int
    missed: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class Build:
    """One compiled candidate. ``source`` is its code variant (``variants/v<k>``, shared by every candidate rendered
    alike); ``duplicate_of`` names an earlier candidate with a byte-identical object."""

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
    #: Instructions of the object that run under a mask (:data:`MASKED_OPERAND`).
    masked_ops: int = 0


def render(scope: Scope, candidate: Candidate, matrix: Matrix) -> str:
    """The scope's CPF translation unit under ``candidate``'s language and codegen knobs; under an SVE tail its
    innermost maps are explicit SVE loops."""
    sdfg = sve_loops(scope.sdfg) if candidate.render(matrix) == "sve" else scope.sdfg
    with ExitStack() as stack:
        for knob, value in candidate.codegen_params(matrix).items():
            stack.enter_context(set_temporary("compiler", "cpu", "codegen_params", knob, value=value))
        rendering = cpf.render(
            sdfg,
            language=matrix.languages[candidate.language].render,
            signature=cpf.EntrySignature(order=list(scope.abi_order)),
            check_compiles=False,
        )
    return rendering.code


def sve_loops(sdfg: dace.SDFG) -> dace.SDFG:
    """A copy of ``sdfg`` with every map SVEVectorization takes rendered as an explicit SVE predicated loop."""
    vectorized = copy.deepcopy(sdfg)
    vectorized.apply_transformations_repeated(SVEVectorization)
    return vectorized


def masked_lines(listing: str) -> int:
    """How many instructions of a disassembly listing mask a loop."""
    return sum(1 for line in listing.splitlines() if MASKED_OPERAND.search(line))


def masked_ops(obj: pathlib.Path) -> int:
    """How many of ``obj``'s instructions mask a loop, from its disassembly."""
    listing = subprocess.run(["objdump", "-d", "--no-show-raw-insn", str(obj)], capture_output=True, text=True)
    return masked_lines(listing.stdout)


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
    source: pathlib.Path, obj: pathlib.Path, candidate: Candidate, matrix: Matrix, flags: tuple[str, ...]
) -> subprocess.CompletedProcess[str]:
    """Compile ``source`` with ``flags`` and the compiler's remark flags to ``obj``."""
    compiler = matrix.compilers[candidate.compiler]
    executable, remarks = compiler.executables[candidate.language], compiler.remarks
    command = [executable, *flags, *remarks, "-c", str(source), "-o", str(obj)]
    return subprocess.run(command, capture_output=True, text=True, check=False)


def rendered_or_error(scope: Scope, candidate: Candidate, matrix: Matrix) -> str:
    """:func:`render`, or a unit whose compile fails with the reason the scope cannot be rendered so (an SVE loop
    over a call SVE has no instruction for): the candidate is a failed build that names its cause."""
    try:
        return render(scope, candidate, matrix)
    except NotImplementedError as err:
        reason = " ".join(str(err).split())
        return f"#error alloy: {candidate.note} cannot be rendered: {reason}\n"


def write_source(
    scope: Scope, candidate: Candidate, matrix: Matrix, folder: pathlib.Path, renders: dict[RenderKey, pathlib.Path]
) -> pathlib.Path:
    """``candidate``'s code variant, ``folder/variants/v<k>.<suffix>``, rendered and written the first time its key
    appears; ``renders`` maps each key seen so far to its file, so ``k`` counts variants in order of appearance."""
    key = candidate.variant_key(matrix)
    if key not in renders:
        variants = folder / "variants"
        variants.mkdir(parents=True, exist_ok=True)
        source = variants / f"v{len(renders)}.{matrix.languages[candidate.language].suffix}"
        source.write_text(rendered_or_error(scope, candidate, matrix))
        renders[key] = source
    return renders[key]


def compile_source(source: pathlib.Path, candidate: Candidate, matrix: Matrix) -> Build:
    """Compile ``source`` (its code variant) for ``candidate`` into ``<scope>/builds/<candidate>.o`` and archive it;
    safe to run concurrently for distinct candidates."""
    name, params = candidate.name(matrix), candidate.codegen_params(matrix)
    flags = candidate.flags(matrix)
    builds = source.parent.parent / "builds"
    builds.mkdir(parents=True, exist_ok=True)
    obj = builds / f"{name}.o"
    proc = compile_candidate(source, obj, candidate, matrix, flags)
    obj.with_suffix(".log").write_text(proc.stderr)
    remarks = parse_remarks(proc.stderr, source)
    if proc.returncode != 0:
        return Build(candidate, name, params, source, None, flags, "", remarks, error=proc.stderr.strip()[-2000:])
    if missing := runtime.unresolved(obj, runtime.default_library(matrix)):
        error = f"the {matrix.defaults.openmp_runtime} runtime does not export {', '.join(missing)}"
        return Build(candidate, name, params, source, None, flags, "", remarks, error=error)
    archive = builds / f"lib{name}.a"
    subprocess.run(["ar", "rcs", str(archive), str(obj)], check=True)
    return Build(candidate, name, params, source, archive, flags, code_hash(obj), remarks, masked_ops=masked_ops(obj))


def deduplicated(built: Build, seen: dict[str, str]) -> Build:
    """``built`` pointing at the first candidate in ``seen`` (object and vector library -> name) with the same object
    linked against the same vector library: SLEEF and libmvec builds share an object but not the code it calls."""
    if built.archive is None:
        return built
    first = seen.setdefault(f"{built.object_hash}+{built.candidate.veclib}", built.name)
    return built if first == built.name else replace(built, duplicate_of=first)


def build(scope: Scope, candidate: Candidate, matrix: Matrix, folder: pathlib.Path, seen: dict[str, str]) -> Build:
    """Render, compile and archive ``candidate``. ``seen`` maps object hashes to the first candidate that
    produced them, so a duplicate keeps its record but points at the original."""
    return deduplicated(compile_source(write_source(scope, candidate, matrix, folder, {}), candidate, matrix), seen)
