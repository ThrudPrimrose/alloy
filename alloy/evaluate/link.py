# Copyright 2026 ETH Zurich and the Alloy authors.
"""Whole programs from region archives: each region links its archive from one fixed path, so a candidate is one
archive copy plus a replayed DaCe build (command cache + precompiled header). A timer wraps every region's entry."""

import copy
import hashlib
import pathlib
import shutil
import subprocess
from contextlib import ExitStack
from dataclasses import dataclass

import dace
from dace.config import set_temporary
from dace.libraries.standard.nodes import external_call

from alloy.backend import runtime
from alloy.configuration_matrix import Matrix
from alloy.frontend.regions import Program, Region

TIMER = """#include <stdbool.h>
#include <stdint.h>
#include <time.h>
static double seconds;
void __real_{symbol}({signature});
double alloy_seconds_{symbol}(void) {{ return seconds; }}
void __wrap_{symbol}({signature}) {{
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


@dataclass(slots=True)
class Linker:
    """Builds the program with a chosen archive per region, every region's archive at ``link/lib<symbol>.a``."""

    program: Program
    matrix: Matrix
    out: pathlib.Path

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

    def library_sdfg(self, archives: dict[str, pathlib.Path], compilers: frozenset[str]) -> dace.SDFG:
        """A copy of the outlined program whose every region calls ``archives[symbol]``, linked with the matrix's
        OpenMP runtime and the support libraries of ``compilers``: what a standalone (CPF) library renders."""
        sdfg = copy.deepcopy(self.program.sdfg)
        flags = self.link_flags() + self.support_flags(compilers)
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
        flags = self.link_flags() + self.support_flags(compilers)
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

    def timer(self, region: Region) -> pathlib.Path:
        """The object timing ``region``'s entry, rebuilt when its source changes (a rerun into the same ``out`` after
        the program changed); ``alloy_seconds_<symbol>()`` reads its last call."""
        obj = self.out / "link" / f"timer_{region.symbol}.o"
        source = obj.with_suffix(".c")
        text = TIMER.format(symbol=region.symbol, signature=region.signature, arguments=", ".join(region.abi_order))
        if not obj.is_file() or not source.is_file() or source.read_text() != text:
            source.write_text(text)
            usable, skipped = self.matrix.usable_compilers()
            compiler = next((comp.executables["c"] for comp in usable.values() if "c" in comp.executables), None)
            if compiler is None:
                raise RuntimeError(f"no usable C compiler builds the region timer: {skipped}")
            subprocess.run([compiler, *self.matrix.build_flags, "-c", str(source), "-o", str(obj)], check=True)
        return obj

    def compile_default(self) -> pathlib.Path:
        """The program before outlining, as DaCe's default CPU codegen builds it, on the matrix's OpenMP runtime."""
        sdfg = copy.deepcopy(self.program.original)
        sdfg.name = f"{self.program.original.name}_dace_default"  # pyright: ignore[reportAttributeAccessIssue]
        sdfg.build_folder = str(self.out / "programs" / "dace_default")
        with set_temporary("compiler", "extra_cmake_args", value=cmake_args(self.matrix)):
            sdfg.compile()
        return pathlib.Path(sdfg.build_folder)
