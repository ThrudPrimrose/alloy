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
from dace.sdfg import nodes
from dace.transformation.dataflow.sve.vectorization import SVEVectorization

from alloy.backend import intrinsics, runtime
from alloy.backend.candidates import Candidate, RenderKey
from alloy.configuration_matrix import Matrix
from alloy.frontend.scopes import Scope
from alloy.heuristics import fission
from alloy.isa import approximation

REMARK_LINE = re.compile(r":\d+:\d+: (?:remark|optimized|missed|note): (.*?)(?: \[-R[^\]]+\])?$")
#: nvc's -Minfo lines carry no file name: ``     25, Generated vector simd code for the loop``.
NVHPC_REMARK = re.compile(r"^\s+\d+, (.*)$")
#: A masked loop: an AVX-512 opmask operand or an SVE loop predicate; every SVE instruction names a predicate, so that
#: alone does not count.
MASKED_OPERAND = re.compile(r"\{%k[1-7]\}|\bwhile(?:lo|lt|le|ls)\b")


@dataclass(slots=True, frozen=True)
class Remarks:
    vectorized: int
    missed: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class Build:
    """One compiled candidate; ``duplicate_of`` names an earlier one with a byte-identical object."""

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
    masked_ops: int = 0


def render(scope: Scope, candidate: Candidate, matrix: Matrix) -> str:
    """The scope's CPF translation unit under ``candidate``'s language and codegen knobs; under an SVE tail its
    innermost maps are explicit SVE loops, under fission its maps are cut (:func:`rendered_sdfg`); an ``approx``
    candidate's unit starts with the inline kernels its libm calls go to (:func:`approximation.prelude`); an
    ``intrinsic`` candidate's innermost loop bodies are tasklets of its ISA's rows (:func:`intrinsics.rendered`) and
    its unit starts with their header."""
    rendered, header = rendering(scope, candidate, matrix)
    code: str = rendered.code
    if header:
        return f"{header}\n{code}"
    if not candidate.approx:
        return code
    called = approximation.called_functions(code)
    return approximation.prelude(candidate.approx, called) + code if called else code


def rendering(scope: Scope, candidate: Candidate, matrix: Matrix) -> tuple[cpf.Rendering, str]:
    """CPF's rendering of the SDFG ``candidate`` renders (:func:`rendered_sdfg`), and the header line its unit needs.
    The rendering's ``sdfg`` is CPF's prepared copy, whose tasklet labels the unit's line comments carry."""
    sdfg, header = rendered_sdfg(scope, candidate, matrix)
    sdfg = sve_loops(sdfg) if candidate.render(matrix) == "sve" else sdfg
    with ExitStack() as stack:
        for knob, value in candidate.codegen_params(matrix).items():
            stack.enter_context(set_temporary("compiler", "cpu", "codegen_params", knob, value=value))
        out = cpf.render(
            sdfg,
            language=matrix.languages[candidate.language].render,
            signature=cpf.EntrySignature(order=list(scope.abi_order)),
            check_compiles=False,
            tasklet_labels=True,  # predict maps each line of the object's line table to its tasklet
        )
    return out, header


def rendered_sdfg(scope: Scope, candidate: Candidate, matrix: Matrix) -> tuple[dace.SDFG, str]:
    """The SDFG ``candidate`` renders and the header line its unit needs: the scope's, a copy with its maps cut
    (:func:`fission.fissioned`), or a copy with intrinsic tasklets (:func:`intrinsics.rendered`)."""
    if candidate.intrinsic:
        axis = matrix.intrinsic_tasklets
        return intrinsics.rendered(scope.sdfg, axis.targets[candidate.intrinsic], candidate.fused(matrix), axis.rows)
    return (fission.fissioned(scope.sdfg) if candidate.fission else scope.sdfg), ""


#: :attr:`Remarks.vectorized` of a compiler that reports no vectorized loop.
UNKNOWN_LOOPS = -1


def sve_loops(sdfg: dace.SDFG) -> dace.SDFG:
    """A copy of ``sdfg`` with every map SVEVectorization takes rendered as an explicit SVE predicated loop."""
    vectorized = copy.deepcopy(sdfg)
    vectorized.apply_transformations_repeated(SVEVectorization)
    for node, state in vectorized.all_nodes_recursive():
        # a scalar holds one lane: CPF would broadcast the first element to every lane of the vector
        if isinstance(node, nodes.AccessNode) and isinstance(node.desc(vectorized), dace.data.Scalar):
            parent = state.scope_dict()[node] if isinstance(state, dace.SDFGState) else None
            if isinstance(parent, nodes.MapEntry) and parent.map.schedule == dace.ScheduleType.SVE_Map:
                raise NotImplementedError(f"scalar {node.data} inside an SVE map")
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
    vectorized, missed = set(), []
    for line in log.splitlines():
        match = REMARK_LINE.search(line) if source.name in line else NVHPC_REMARK.match(line)
        if match is None:
            continue
        text = match.group(1)
        if "loop vectorized" in text or "vectorized loop" in text or "Generated vector" in text:
            vectorized.add(line.partition(": ")[0])
        elif "not vectorized" in text or "couldn't vectorize" in text:
            missed.append(text.strip())
    return Remarks(vectorized=len(vectorized), missed=tuple(dict.fromkeys(missed)))


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
    # whatever a variant's transformation raises fails that candidate only, not the sweep
    except Exception as err:
        reason = " ".join(f"{type(err).__name__}: {err}".split())
        return f"#error alloy: {candidate.note} cannot be rendered: {reason}\n"


def write_source(
    scope: Scope, candidate: Candidate, matrix: Matrix, folder: pathlib.Path, renders: dict[RenderKey, pathlib.Path]
) -> pathlib.Path:
    """``candidate``'s code variant, rendered and written the first time its key appears in ``renders``."""
    key = candidate.variant_key(matrix)
    if key not in renders:
        variants = folder / "variants"
        variants.mkdir(parents=True, exist_ok=True)
        text = rendered_or_error(scope, candidate, matrix)
        same = next((path for path in renders.values() if path.read_text() == text), None)
        source = same or variants / f"v{len(renders)}.{matrix.languages[candidate.language].suffix}"
        if same is None:
            source.write_text(text)
        renders[key] = source
    return renders[key]


def compile_source(source: pathlib.Path, candidate: Candidate, matrix: Matrix) -> Build:
    """Compile ``source`` (its code variant) for ``candidate`` into ``<scope>/builds/<candidate>.o`` and archive it;
    safe to run concurrently for distinct candidates."""
    name, params = candidate.name(matrix), candidate.codegen_params(matrix)
    flags = (*candidate.flags(matrix), *matrix.compilers[candidate.compiler].line_tables)  # nvc's change the code
    builds = source.parent.parent / "builds"
    builds.mkdir(parents=True, exist_ok=True)
    obj = builds / f"{name}.o"
    proc = compile_candidate(source, obj, candidate, matrix, flags)
    obj.with_suffix(".log").write_text(proc.stderr)
    remarks = parse_remarks(proc.stderr, source)
    if not matrix.compilers[candidate.compiler].remarks:
        remarks = replace(remarks, vectorized=UNKNOWN_LOOPS)
    if proc.returncode != 0:
        return Build(
            candidate,
            name,
            params,
            source,
            None,
            flags,
            "",
            remarks,
            error=(proc.stderr.strip() or proc.stdout.strip() or f"exit status {proc.returncode}")[-2000:],
        )
    if missing := runtime.unresolved(obj, runtime.default_library(matrix)):
        error = f"the {matrix.defaults.openmp_runtime} runtime does not export {', '.join(missing)}"
        return Build(candidate, name, params, source, None, flags, "", remarks, error=error)
    # such a call would count a team whose region the build dropped
    if candidate.serial and (calls := runtime.openmp_needs(obj)):
        error = f"a serial build still calls {', '.join(sorted(calls))}"
        return Build(candidate, name, params, source, None, flags, "", remarks, error=error)
    linked = obj
    if candidate.veclib != "none" and matrix.veclibs[candidate.veclib].private:
        executable = matrix.compilers[candidate.compiler].executables[candidate.language]
        linked, error = closed(obj, matrix.veclibs[candidate.veclib].probe, executable)
        if error:
            return Build(candidate, name, params, source, None, flags, "", remarks, error=error)
    archive = builds / f"lib{name}.a"
    subprocess.run(["ar", "rcs", str(archive), str(linked)], check=True)
    return Build(candidate, name, params, source, archive, flags, code_hash(obj), remarks, masked_ops=masked_ops(obj))


def static_archive(probe: str, executable: str) -> pathlib.Path | None:
    """``lib<probe>.a`` beside the ``lib<probe>.so`` the link resolves (:func:`runtime.find_library`), or ``None``."""
    shared = runtime.find_library(probe, (executable,))
    archive = shared.with_name(f"lib{probe}.a") if shared is not None else None
    return archive if archive is not None and archive.is_file() else None


def closed(obj: pathlib.Path, probe: str, executable: str) -> tuple[pathlib.Path, str]:
    """``obj`` with a private copy of the vector math library ``lib<probe>`` (A7): ``ld -r`` pulls in only the archive
    members the scope calls, and every symbol but the scope's own globals turns local, so no ``_ZGV*`` name of one
    scope binds another scope's calls. ``(closed object, "")``, or ``(obj, why)`` when it cannot be closed here."""
    archive = static_archive(probe, executable)
    if archive is None:
        return obj, f"lib{probe} has no static archive here, so the scope cannot keep a private copy of it"
    own = subprocess.run(["nm", "--defined-only", "-g", "-P", str(obj)], capture_output=True, text=True, check=True)
    keep = obj.with_suffix(".keep")
    keep.write_text("".join(f"{line.split()[0]}\n" for line in own.stdout.splitlines() if line.strip()))
    result = obj.with_suffix(".closed.o")
    for command in (
        ["ld", "-r", str(obj), str(archive), "-o", str(result)],
        ["objcopy", f"--keep-global-symbols={keep}", str(result)],
    ):
        run = subprocess.run(command, capture_output=True, text=True, check=False)
        if run.returncode != 0:
            return obj, f"closing over lib{probe} failed: {run.stderr.strip()[-500:]}"
    return result, ""


def deduplicated(built: Build, seen: dict[str, str]) -> Build:
    """``built`` pointing at the first candidate in ``seen`` (object and vector library -> name) with the same object
    linked against the same vector library: SLEEF and libmvec builds share an object but not the code it calls."""
    if built.archive is None:
        return built
    first = seen.setdefault(f"{built.object_hash}+{built.candidate.veclib}", built.name)
    return built if first == built.name else replace(built, duplicate_of=first)
