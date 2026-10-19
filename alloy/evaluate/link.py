# Copyright 2026 ETH Zurich and the Alloy authors.
"""Whole programs from region archives: each region links its archive from one fixed path, so a candidate is one
archive copy plus a replayed DaCe build (command cache + precompiled header). A timer wraps every region's entry; it is
C++ against DaCe's runtime types, so it declares the entry with the signature DaCe gave it."""

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
from pydantic.dataclasses import dataclass as record

from alloy.backend import runtime
from alloy.backend.build import Build
from alloy.configuration_matrix import Matrix
from alloy.frontend.regions import Program, Region
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


def cmake_args(matrix: Matrix) -> str:
    """Make DaCe's own OpenMP the matrix runtime: its CMake would otherwise find the compiler's default one and load
    a second runtime next to the regions'."""
    soname = matrix.openmp_runtimes[matrix.defaults.openmp_runtime]
    return f"-DOpenMP_CXX_LIB_NAMES={soname} -DOpenMP_{soname}_LIBRARY={runtime.default_library(matrix)}"


@record(slots=True, frozen=True, config=RECORD)
class BestRegion:
    """How ``best/`` builds one region: its winning candidate's source, compiler and compile flags."""

    symbol: str
    candidate: str
    compiler: str
    flags: Strings
    source: str


@record(slots=True, frozen=True, config=RECORD)
class Best:
    """``best/link.json``: every region's build, the entry's parameter order and the program's link line."""

    regions: tuple[BestRegion, ...]
    arguments: Strings
    link: Strings


@dataclass(slots=True)
class Linker:
    """Builds the program with a chosen archive per region, every region's archive at ``link/lib<symbol>.a``."""

    program: Program
    matrix: Matrix
    out: pathlib.Path
    vendor: list[str] | None = None

    def link_flags(self) -> list[str]:
        library = runtime.default_library(self.matrix)
        return runtime.link_flags(library, self.matrix.openmp_runtimes[self.matrix.defaults.openmp_runtime])

    def support_flags(self, compilers: frozenset[str]) -> list[str]:
        """Link flags for the support libraries of every compiler that built one of the linked archives."""
        flags: list[str] = []
        for name in sorted(compilers):
            comp = self.matrix.compilers[name]
            executables = list(comp.executables.values())
            for soname in comp.support_libraries:
                flags += runtime.link_flags(runtime.resolve(soname, executables), soname)
        return flags

    def vendor_flags(self) -> list[str]:
        """The vendor libraries the regions call (``-lopenblas`` for a BLAS library node): a region's archive
        carries the calls, not the libraries, so the program links them. Rendered once per Linker."""
        if self.vendor is None:
            tokens = (
                cpf.render(
                    region.sdfg, signature=cpf.EntrySignature(order=list(region.abi_order)), check_compiles=False
                ).link
                for region in self.program.regions
            )
            self.vendor = list(dict.fromkeys(token for link in tokens for token in link))
        return self.vendor

    def library_sdfg(self, archives: dict[str, pathlib.Path], compilers: frozenset[str]) -> dace.SDFG:
        """A copy of the outlined program whose every region calls ``archives[symbol]``, linked with the matrix's
        OpenMP runtime and the support libraries of ``compilers``: what a standalone (CPF) library renders."""
        sdfg = copy.deepcopy(self.program.sdfg)
        flags = self.link_flags() + self.support_flags(compilers) + self.vendor_flags()
        for call in external_call.external_calls(sdfg):
            call.implementation, call.lib_path, call.link_flags = "ExternCall", str(archives[call.symbol]), flags
        return sdfg

    def compile(
        self, archives: dict[str, pathlib.Path], tag: str, compilers: frozenset[str] = frozenset()
    ) -> pathlib.Path:
        """The program with ``archives[symbol]`` linked for each region, built under a name of its own so no cache
        or loaded library of another candidate can stand in for it."""
        link = self.out / "link"
        link.mkdir(parents=True, exist_ok=True)
        sdfg = copy.deepcopy(self.program.sdfg)
        safe = f"p{hashlib.sha256(tag.encode()).hexdigest()[:12]}"  # candidate names carry '-', SDFG names may not
        sdfg.name = f"{self.program.sdfg.name}_{safe}"  # pyright: ignore[reportAttributeAccessIssue]
        sdfg.build_folder = str(self.out / "programs" / safe)
        flags = self.link_flags() + self.support_flags(compilers) + self.vendor_flags()
        regions = {r.symbol: r for r in self.program.regions}
        for call in external_call.external_calls(sdfg):
            fixed = link / f"lib{call.symbol}.a"
            shutil.copyfile(archives[call.symbol], fixed)
            subprocess.run(["ar", "rs", str(fixed), str(self.timer(regions[call.symbol]))], check=True)
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
        """``out/best/``: each region's winning source, the CPF program calling them, and a Makefile that builds each
        region with its own compiler and flags, then ``lib<program>.so``. ``-ffast-math`` stays on a region's compile
        line, never on the link line, so no ``crtfastmath.o`` sets FTZ/DAZ for the whole process."""
        best = self.out / "best"
        (best / "regions").mkdir(parents=True, exist_ok=True)
        regions = []
        for symbol, b in winners.items():
            source = f"regions/{symbol}{b.source.suffix}"
            shutil.copyfile(b.source, best / source)
            compiler = self.matrix.compilers[b.candidate.compiler].executables[b.candidate.language]
            regions.append(BestRegion(symbol, b.name, compiler, b.flags, source))
        archives = {r.symbol: best / f"lib{r.symbol}.a" for r in regions}
        compilers = frozenset(b.candidate.compiler for b in winners.values())
        rendering = cpf.render(self.library_sdfg(archives, compilers), language="c", check_compiles=False)
        (best / "program.c").write_text(rendering.code)
        link = tuple(token.removeprefix(f"{best}/") for token in rendering.link)  # make runs in best/
        plan = Best(tuple(regions), rendering.arguments, link)
        (best / "link.json").write_text(dumped_json(plan))
        (best / "Makefile").write_text(self.makefile(plan))
        return plan

    def makefile(self, plan: Best) -> str:
        library = f"lib{self.program.sdfg.name}.so"
        archives = " ".join(f"lib{r.symbol}.a" for r in plan.regions)
        usable, _ = self.matrix.usable_compilers()
        frame = next(comp.executables["c"] for comp in usable.values() if "c" in comp.executables)
        frame_flags = [self.matrix.languages["c"].std, "-O3", "-fPIC", "-shared"]
        lines = [f"all: {library}", ""]
        for r in plan.regions:
            compile_line = shlex.join([r.compiler, *r.flags, "-c", r.source, "-o", f"{r.symbol}.o"])
            lines += [f"lib{r.symbol}.a: {r.source}", f"\t{compile_line}", f"\tar rcs $@ {r.symbol}.o", ""]
        link_line = shlex.join([frame, *frame_flags, "program.c", "-o", library, *plan.link])
        return "\n".join([*lines, f"{library}: program.c {archives}", f"\t{link_line}", ""])

    def timer(self, region: Region) -> pathlib.Path:
        """The object timing ``region``'s entry, rebuilt when its source changes (a rerun into the same ``out`` after
        the program changed); ``alloy_seconds_<symbol>()`` reads its last call."""
        obj = self.out / "link" / f"timer_{region.symbol}.o"
        source = obj.with_suffix(".cpp")
        text = TIMER.format(symbol=region.symbol, signature=region.signature, arguments=", ".join(region.abi_order))
        if not obj.is_file() or not source.is_file() or source.read_text() != text:
            source.write_text(text)
            usable, skipped = self.matrix.usable_compilers()
            compiler = next((comp.executables["cpp"] for comp in usable.values() if "cpp" in comp.executables), None)
            if compiler is None:
                raise RuntimeError(f"no usable C++ compiler builds the region timer: {skipped}")
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
