# Copyright 2026 ETH Zurich and the Alloy authors.
"""Objects from several compilers, archived and linked into ONE binary against ONE OpenMP runtime. The runtime
check (``alloy.backend.runtime.unresolved``) must predict exactly which combinations link, and every one that links
must run on the requested threads with one runtime loaded. Each compiler is a mark: a box without it deselects
(``-m 'not icx'``)."""

import itertools
import os
import pathlib
import subprocess

import pytest

from alloy import configuration_matrix
from alloy.backend import runtime

MATRIX = configuration_matrix.load()
THREADS = 4
N = 1000
KERNEL = """#include <omp.h>
int k_{name}(double *restrict a, long n) {{
    int threads = 0;
#pragma omp parallel
    {{
#pragma omp single
        threads = omp_get_num_threads();
#pragma omp for
        for (long i = 0; i < n; ++i) a[i] = a[i] * 2.0 + 1.0;
    }}
    return threads;
}}
"""
#: One mark per compiler; a matrix compiler without one fails here, so a new compiler gets registered.
MARKS = {"gcc": pytest.mark.gcc, "clang": pytest.mark.clang, "nvhpc": pytest.mark.nvhpc, "icx": pytest.mark.icx}


def main_source(names: tuple[str, ...]) -> str:
    """A driver calling every kernel in turn on one array: each doubles and adds one, so the result is exact."""
    decls = "".join(f"int k_{n}(double *, long);\n" for n in names)
    calls = "".join(f'    if (k_{n}(a, N) != {THREADS}) {{ puts("threads {n}"); return 2; }}\n' for n in names)
    expect = "".join("        w = w * 2.0 + 1.0;\n" for _ in names)
    return (
        f"#include <stdio.h>\n{decls}int main(void) {{\n    enum {{ N = {N} }}; double a[N];\n"
        "    for (int i = 0; i < N; ++i) a[i] = i;\n"
        f"{calls}"
        "    for (int i = 0; i < N; ++i) {\n        double w = i;\n"
        f"{expect}"
        '        if (a[i] != w) { puts("value"); return 1; }\n    }\n    return 0;\n}\n'
    )


def kernel_archive(tmp: pathlib.Path, name: str, runtime_name: str) -> pathlib.Path:
    """``lib<name>.a`` built by compiler ``name`` with its spelling of ``runtime_name``, or of its first runtime when
    it has none (that object is then expected not to link)."""
    comp = MATRIX.compilers[name]
    openmp = comp.openmp.get(runtime_name) or next(iter(comp.openmp.values()))
    source, obj, archive = tmp / f"k_{name}.c", tmp / f"k_{name}.o", tmp / f"lib{name}.a"
    source.write_text(KERNEL.format(name=name))
    subprocess.run([comp.executables["c"], "-O2", "-fPIC", *openmp, "-c", str(source), "-o", str(obj)], check=True)
    subprocess.run(["ar", "rcs", str(archive), str(obj)], check=True)
    return archive


def compiler_param(names: tuple[str, ...]) -> object:
    return pytest.param(names, marks=[MARKS[n] for n in names], id="+".join(names))


COMBINATIONS = [
    compiler_param(names)
    for size in (1, 2, len(MATRIX.compilers))
    for names in itertools.combinations(MATRIX.compilers, size)
]


def executables() -> list[str]:
    return [exe for comp in MATRIX.compilers.values() for exe in comp.executables.values()]


@pytest.mark.parametrize("runtime_name", list(MATRIX.openmp_runtimes))
@pytest.mark.parametrize("names", COMBINATIONS)
def test_archives_from_several_compilers_link_exactly_when_the_runtime_exports_their_calls(
    tmp_path, names, runtime_name
):
    library = runtime.resolve(MATRIX.openmp_runtimes[runtime_name], executables())
    archives = [kernel_archive(tmp_path, n, runtime_name) for n in names]
    predicted = all(not runtime.unresolved(a, library) for a in archives)
    (tmp_path / "main.c").write_text(main_source(names))
    link = [
        "gcc",
        str(tmp_path / "main.c"),
        *map(str, archives),
        *runtime.link_flags(library, MATRIX.openmp_runtimes[runtime_name]),
        "-o",
        str(tmp_path / "main"),
    ]

    linked = subprocess.run(link, capture_output=True, text=True, check=False).returncode == 0

    assert linked == predicted
    if linked:
        env = {**os.environ, "OMP_NUM_THREADS": str(THREADS)}
        run = subprocess.run([str(tmp_path / "main")], capture_output=True, text=True, env=env, check=False)
        assert run.returncode == 0, run.stdout
        loaded = subprocess.run(["ldd", str(tmp_path / "main")], capture_output=True, text=True, check=True).stdout
        runtimes = {so for so in MATRIX.openmp_runtimes.values() if f"lib{so}.so" in loaded}
        assert runtimes == {MATRIX.openmp_runtimes[runtime_name]}
