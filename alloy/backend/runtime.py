# Copyright 2026 ETH Zurich and the Alloy authors.
"""The process's one OpenMP runtime: where its shared object is, what it exports, and whether an object file's
OpenMP calls resolve against it. gcc emits ``GOMP_*`` calls, clang/icx/nvc emit ``__kmpc_*``; LLVM libomp and NVHPC
libnvomp export both, gcc's libgomp only its own."""

import functools
import pathlib
import re
import shutil
import subprocess

#: Undefined symbols that belong to an OpenMP runtime.
OPENMP_SYMBOL = re.compile(r"^(GOMP_|__kmpc_|omp_|kmp_|__kmp_)")


def driver_path(executable: str, soname: str) -> pathlib.Path | None:
    """``lib<soname>.so`` as the compiler driver resolves it: ``-print-file-name`` (gcc, clang, icx), else the
    ``lib`` folder next to its ``bin`` (nvc, whose driver has no such query)."""
    found = shutil.which(executable)
    if found is None:
        return None
    query = subprocess.run(
        [found, f"-print-file-name=lib{soname}.so"], capture_output=True, text=True, check=False, timeout=60
    )
    named = pathlib.Path(query.stdout.strip())
    if query.returncode == 0 and named.is_absolute() and named.is_file():
        return named
    beside = pathlib.Path(found).resolve().parent.parent / "lib" / f"lib{soname}.so"
    return beside if beside.is_file() else None


@functools.lru_cache(maxsize=None, typed=True)
def runtime_library(soname: str, executables: tuple[str, ...]) -> pathlib.Path | None:
    """The first ``lib<soname>.so`` any of ``executables`` resolves, in order."""
    for executable in executables:
        if (path := driver_path(executable, soname)) is not None:
            return path
    return None


def symbols(path: pathlib.Path, *args: str) -> frozenset[str]:
    out = subprocess.run(["nm", *args, str(path)], capture_output=True, text=True, check=True).stdout
    # a versioned export reads ``GOMP_parallel@@GOMP_4.0``; the object asks for the bare name
    return frozenset(line.split()[-1].split("@")[0] for line in out.splitlines() if line.strip())


@functools.lru_cache(maxsize=None, typed=True)
def exported(library: pathlib.Path) -> frozenset[str]:
    """Dynamic symbols ``library`` defines."""
    return symbols(library, "-D", "--defined-only")


def openmp_needs(obj: pathlib.Path) -> frozenset[str]:
    """The OpenMP runtime symbols ``obj`` leaves undefined."""
    return frozenset(s for s in symbols(obj, "-u") if OPENMP_SYMBOL.match(s))


def unresolved(obj: pathlib.Path, library: pathlib.Path) -> list[str]:
    """OpenMP symbols ``obj`` needs that ``library`` does not export; empty means the two link."""
    return sorted(openmp_needs(obj) - exported(library))


def link_flags(library: pathlib.Path, soname: str) -> list[str]:
    """Link ``library`` and find it again at load time."""
    return [f"-L{library.parent}", f"-l{soname}", f"-Wl,-rpath,{library.parent}"]


def resolve(soname: str, compiler_executables: list[str]) -> pathlib.Path:
    """``lib<soname>.so`` as the matrix's compilers find it; the runtime is mandatory, so a miss raises."""
    library = runtime_library(soname, tuple(compiler_executables))
    if library is None:
        raise LookupError(f"no compiler in the matrix resolves lib{soname}.so")
    return library
