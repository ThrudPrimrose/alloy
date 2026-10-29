# Copyright 2026 ETH Zurich and the Alloy authors.
"""Whole programs from scope archives: a candidate is one archive copy plus a replayed DaCe build. A timer wraps each
scope's entry; a stub keeps the program's signature but stops after one scope, so a judge can time that scope."""

import copy
import hashlib
import pathlib
import shlex
import shutil
import subprocess
from contextlib import ExitStack
from dataclasses import dataclass

import dace
from dace.codegen import cpf
from dace.config import set_temporary
from dace.libraries.standard.nodes import external_call
from dace.sdfg import utils as sdutils
from pydantic.dataclasses import dataclass as record

from alloy.backend import runtime
from alloy.backend.build import Build
from alloy.backend.candidates import Candidate
from alloy.configuration_matrix import Matrix
from alloy.frontend.scopes import Program, Scope
from alloy.records import RECORD, Strings, dumped_json

TIMER = """#include <dace/types.h>
#include <ctime>
static double seconds;
extern "C" void __real_{symbol}({signature});
extern "C" double alloy_seconds_{symbol}(void) {{ return seconds; }}
extern "C" void __wrap_{symbol}({signature}) {{
  struct timespec t0, t1;
  clock_gettime(CLOCK_MONOTONIC, &t0);
  __real_{symbol}({arguments});
  clock_gettime(CLOCK_MONOTONIC, &t1);
  seconds = (double)(t1.tv_sec - t0.tv_sec) + 1e-9 * (double)(t1.tv_nsec - t0.tv_nsec);
}}
"""
#: A scope that runs after the stubbed one: its entry, with no body.
EMPTY = """#include <dace/types.h>
extern "C" void {symbol}({signature}) {{}}
"""


def execution_order(sdfg: dace.SDFG) -> list[str]:
    """The scope symbols in run order: every call sits in a top-level state (a loop is outlined whole), so a
    topological walk of the top-level blocks, then of each state, orders them."""
    order: list[str] = []
    for block in sdutils.dfs_topological_sort(sdfg):
        if isinstance(block, dace.SDFGState):
            order += [
                n.symbol for n in sdutils.dfs_topological_sort(block) if isinstance(n, external_call.ExternalCall)
            ]
    return order


def cmake_args(matrix: Matrix) -> str:
    """Make DaCe's own OpenMP the matrix runtime: its CMake would otherwise find the compiler's default one and load
    a second runtime next to the scopes'."""
    soname = matrix.openmp_runtimes[matrix.defaults.openmp_runtime]
    return f"-DOpenMP_CXX_LIB_NAMES={soname} -DOpenMP_{soname}_LIBRARY={runtime.default_library(matrix)}"


def built(build: Build) -> pathlib.Path:
    """``build``'s archive; a failed build has none and raises with its error."""
    if build.error or build.archive is None:
        raise RuntimeError(f"{build.name} did not build: {build.error}")
    return build.archive


@record(slots=True, frozen=True, config=RECORD)
class BestScope:
    """How ``best/`` builds one scope: its winning candidate's source, compiler and compile flags."""

    symbol: str
    candidate: str
    compiler: str
    flags: Strings
    source: str


@record(slots=True, frozen=True, config=RECORD)
class Best:
    """``best/link.json``: every scope's build, the entry's parameter order and the program's link line."""

    scopes: tuple[BestScope, ...]
    arguments: Strings
    link: Strings


@record(slots=True, frozen=True, config=RECORD)
class Commands:
    """The full argv that builds ``best/``: each scope's compile, then the program's link (run in ``best/``)."""

    compile: dict[str, Strings]
    link: Strings
    library: str


@dataclass(slots=True)
class Linker:
    """Builds the program with a chosen archive per scope, every scope's archive at ``link/<program>/lib<symbol>.a``."""

    program: Program
    matrix: Matrix
    out: pathlib.Path
    vendor: list[str] | None = None

    def link_flags(self) -> list[str]:
        library = runtime.default_library(self.matrix)
        return runtime.link_flags(library, self.matrix.openmp_runtimes[self.matrix.defaults.openmp_runtime])

    def support_flags(self, candidates: frozenset[Candidate]) -> list[str]:
        """Link flags for what the linked archives call beyond their objects: the support libraries of every
        compiler that built one, and every vector library one was built against. Linked explicitly, else a SLEEF
        build's ``_ZGV*`` calls bind to glibc's libmvec, which ``-lm`` pulls in under the same names."""
        flags: list[str] = []
        for name in sorted({c.compiler for c in candidates}):
            comp = self.matrix.compilers[name]
            executables = list(comp.executables.values())
            for soname in comp.support_libraries:
                flags += runtime.link_flags(runtime.resolve(soname, executables), soname)
        for lib in sorted({c.veclib for c in candidates} - {"none"}):
            probe = self.matrix.veclibs[lib].probe
            executables = [
                exe
                for c in candidates
                if c.veclib == lib
                for exe in self.matrix.compilers[c.compiler].executables.values()
            ]
            flags += runtime.link_flags(runtime.resolve(probe, executables), probe)
        return flags

    def vendor_flags(self) -> list[str]:
        """The vendor libraries the scopes call (``-lopenblas`` for a BLAS library node): a scope's archive
        carries the calls, not the libraries, so the program links them. Rendered once per Linker."""
        if self.vendor is None:
            tokens = (
                cpf.render(
                    scope.sdfg, signature=cpf.EntrySignature(order=list(scope.abi_order)), check_compiles=False
                ).link
                for scope in self.program.scopes
            )
            self.vendor = list(dict.fromkeys(token for link in tokens for token in link))
        return self.vendor

    def library_sdfg(self, archives: dict[str, pathlib.Path], candidates: frozenset[Candidate]) -> dace.SDFG:
        """A copy of the outlined program whose every scope calls ``archives[symbol]``, linked with the matrix's
        OpenMP runtime and the libraries ``candidates`` need: what a standalone (CPF) library renders."""
        sdfg = copy.deepcopy(self.program.sdfg)
        flags = self.link_flags() + self.support_flags(candidates) + self.vendor_flags()
        for call in external_call.external_calls(sdfg):
            call.implementation, call.lib_path, call.link_flags = "ExternCall", str(archives[call.symbol]), flags
        return sdfg

    def compile(
        self, archives: dict[str, pathlib.Path], tag: str, candidates: frozenset[Candidate] = frozenset()
    ) -> pathlib.Path:
        """The program with ``archives[symbol]`` linked for each scope, built under a name of its own so no cache
        or loaded library of another candidate can stand in for it."""
        safe = f"p{hashlib.sha256(tag.encode()).hexdigest()[:12]}"  # candidate names carry '-', SDFG names may not
        link = self.out / "link" / safe  # one folder per program: programs build in parallel
        link.mkdir(parents=True, exist_ok=True)
        sdfg = copy.deepcopy(self.program.sdfg)
        sdfg.name = f"{self.program.sdfg.name}_{safe}"  # pyright: ignore[reportAttributeAccessIssue]
        sdfg.build_folder = str(self.out / "programs" / safe)
        flags = self.link_flags() + self.support_flags(candidates) + self.vendor_flags()
        scopes = {r.symbol: r for r in self.program.scopes}
        for call in external_call.external_calls(sdfg):
            fixed = link / f"lib{call.symbol}.a"
            shutil.copyfile(archives[call.symbol], fixed)
            subprocess.run(["ar", "rs", str(fixed), str(self.timer(scopes[call.symbol]))], check=True)
            call.implementation, call.lib_path = "ExternCall", str(fixed)
            call.link_flags = [*flags, f"-Wl,--wrap={call.symbol}"]
        with ExitStack() as stack:
            for path, value in (
                (("compiler", "command_cache"), True),
                (("compiler", "precompiled_header"), True),
                (("compiler", "extra_cmake_args"), cmake_args(self.matrix)),
            ):
                stack.enter_context(set_temporary(*path, value=value))
            sdfg.compile()
        return pathlib.Path(sdfg.build_folder)

    def write_best(self, winners: dict[str, Build]) -> Best:
        """``out/best/``: each scope's winning source, the CPF program calling them, and a Makefile that builds each
        scope with its own compiler and flags, then ``lib<program>.so``. ``-ffast-math`` stays on a scope's compile
        line, never on the link line, so no ``crtfastmath.o`` sets FTZ/DAZ for the whole process."""
        best = self.out / "best"
        (best / "scopes").mkdir(parents=True, exist_ok=True)
        scopes = []
        for symbol, b in winners.items():
            source = f"scopes/{symbol}{b.source.suffix}"
            shutil.copyfile(b.source, best / source)
            compiler = self.matrix.compilers[b.candidate.compiler].executables[b.candidate.language]
            scopes.append(BestScope(symbol, b.name, compiler, b.flags, source))
        archives = {r.symbol: best / f"lib{r.symbol}.a" for r in scopes}
        candidates = frozenset(b.candidate for b in winners.values())
        rendering = cpf.render(self.library_sdfg(archives, candidates), language="c", check_compiles=False)
        (best / "program.c").write_text(rendering.code)
        link = tuple(token.removeprefix(f"{best}/") for token in rendering.link)  # make runs in best/
        plan = Best(tuple(scopes), rendering.arguments, link)
        (best / "link.json").write_text(dumped_json(plan))
        (best / "Makefile").write_text(self.makefile(plan))
        return plan

    def commands(self, plan: Best) -> Commands:
        """The argv of every compile and of the link that ``best/Makefile`` runs."""
        library = f"lib{self.program.sdfg.name}.so"
        usable, _ = self.matrix.usable_compilers()
        frame = next(comp.executables["c"] for comp in usable.values() if "c" in comp.executables)
        frame_flags = [self.matrix.languages["c"].std, "-O3", "-fPIC", "-shared"]
        compiles = {r.symbol: (r.compiler, *r.flags, "-c", r.source, "-o", f"{r.symbol}.o") for r in plan.scopes}
        link = (frame, *frame_flags, "program.c", "-o", library, *plan.link)
        return Commands(compile=compiles, link=link, library=library)

    def makefile(self, plan: Best) -> str:
        commands = self.commands(plan)
        archives = " ".join(f"lib{r.symbol}.a" for r in plan.scopes)
        lines = [f"all: {commands.library}", ""]
        for r in plan.scopes:
            compile_line = shlex.join(commands.compile[r.symbol])
            lines += [f"lib{r.symbol}.a: {r.source}", f"\t{compile_line}", f"\tar rcs $@ {r.symbol}.o", ""]
        link_line = shlex.join(commands.link)
        return "\n".join([*lines, f"{commands.library}: program.c {archives}", f"\t{link_line}", ""])

    def stub(self, selection: dict[str, Build], symbol: str) -> dace.SDFG:
        """The program, same signature, running the scopes before ``symbol`` and ``symbol`` from ``selection``; later
        scopes link an empty body. The prefix is equal across ``symbol``'s candidates, so stub times rank them."""
        order = execution_order(self.program.sdfg)
        later = set(order[order.index(symbol) + 1 :])
        scopes = {r.symbol: r for r in self.program.scopes}
        archives = {s: self.empty(scopes[s]) if s in later else built(selection[s]) for s in order}
        candidates = frozenset(selection[s].candidate for s in order if s not in later)
        return self.library_sdfg(archives, candidates)

    def empty(self, scope: Scope) -> pathlib.Path:
        """The archive of ``scope``'s entry with an empty body."""
        archive = self.out / "link" / f"libempty_{scope.symbol}.a"
        obj = self.cpp_object(f"empty_{scope.symbol}", EMPTY.format(symbol=scope.symbol, signature=scope.signature))
        if not archive.is_file() or archive.stat().st_mtime < obj.stat().st_mtime:
            archive.unlink(missing_ok=True)
            subprocess.run(["ar", "rcs", str(archive), str(obj)], check=True)
        return archive

    def timer(self, scope: Scope) -> pathlib.Path:
        """The object timing ``scope``'s entry; ``alloy_seconds_<symbol>()`` reads its last call."""
        text = TIMER.format(symbol=scope.symbol, signature=scope.signature, arguments=", ".join(scope.abi_order))
        return self.cpp_object(f"timer_{scope.symbol}", text)

    def cpp_object(self, name: str, text: str) -> pathlib.Path:
        """``link/<name>.o`` compiled from ``text`` against DaCe's runtime types, rebuilt when the text changes (a
        rerun into the same ``out`` after the program changed)."""
        (self.out / "link").mkdir(parents=True, exist_ok=True)
        obj = self.out / "link" / f"{name}.o"
        source = obj.with_suffix(".cpp")
        if not obj.is_file() or not source.is_file() or source.read_text() != text:
            source.write_text(text)
            usable, skipped = self.matrix.usable_compilers()
            compiler = next((comp.executables["cpp"] for comp in usable.values() if "cpp" in comp.executables), None)
            if compiler is None:
                raise RuntimeError(f"no usable C++ compiler builds {name}: {skipped}")
            include = pathlib.Path(dace.__file__).parent / "runtime" / "include"
            command = [compiler, self.matrix.languages["cpp"].std, *self.matrix.build_flags, f"-I{include}"]
            subprocess.run([*command, "-c", str(source), "-o", str(obj)], check=True)
        return obj

    def compile_default(self) -> pathlib.Path:
        """The program before outlining, as DaCe's default CPU codegen builds it, on the matrix's OpenMP runtime."""
        sdfg = copy.deepcopy(self.program.original)
        sdfg.name = f"{self.program.original.name}_dace_default"  # pyright: ignore[reportAttributeAccessIssue]
        sdfg.build_folder = str(self.out / "programs" / "dace_default")
        with set_temporary("compiler", "extra_cmake_args", value=cmake_args(self.matrix)):
            sdfg.compile()
        return pathlib.Path(sdfg.build_folder)
