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
#: An arg-max reduction seeded from ``omp_orig``, a form DaCe left for its neutral pair. Every thread waits inside the
#: loop for its whole team, so no thread starts after another left, and the highest thread leaves last holding its own
#: maximum; the true maximum sits in thread 0's chunk. A correct combine returns it whatever the arrival order. The wait
#: stays a relaxed ``omp atomic``: a sequentially consistent atomic in the loop body hides the icx miscompile below.
SEEDED_REDUCTION = """#include <omp.h>
#include <stdint.h>
#include <unistd.h>
typedef struct { double value; int64_t index; } pair;
static inline pair better(pair out, pair in) { return in.value > out.value ? in : out; }
#pragma omp declare reduction(arg_max : pair : omp_out = better(omp_out, omp_in)) initializer(omp_priv = omp_orig)
enum { N = 400, CALLS = 8 };
static double a[N];
static int entered, call;
static _Thread_local int seen;

static void wait_for_team(void) {
    if (seen == call) return;
    seen = call;
#pragma omp atomic update
    entered++;
    for (int in_loop = 0; in_loop < omp_get_num_threads();) {
#pragma omp atomic read
        in_loop = entered;
    }
    if (omp_get_thread_num() == omp_get_num_threads() - 1) usleep(2000);
}

__attribute__((noinline)) static int64_t arg_max(void) {
    pair best = {a[0], 0};
    ++call;
    entered = 0;
#pragma omp parallel for reduction(arg_max : best) schedule(static)
    for (int64_t i = 1; i < N; ++i) {
        wait_for_team();
        best = a[i] > best.value ? (pair){a[i], i} : best;
    }
    return best.index;
}

int main(void) {
    for (int i = 0; i < N; ++i) a[i] = i * 1e-3;
    a[1] = 1000.0;
    for (int c = 0; c < CALLS; ++c)
        if (arg_max() != 1) return 1;
    return 0;
}
"""


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


#: icx 2026.2 ``-fiopenmp`` at -O2 and above takes omp_out from the value read for omp_orig when the thread entered the
#: region, so threads that overlap overwrite each other and the last to arrive wins. Fails here once Intel fixes it.
ICX_LOSES_UPDATES = pytest.mark.xfail(
    strict=True, raises=AssertionError, reason="-fiopenmp: the combine reads a stale copy of the shared value"
)
SEEDED_COMPILERS = [
    pytest.param("gcc", marks=MARKS["gcc"]),
    pytest.param("clang", marks=MARKS["clang"]),
    pytest.param("icx", marks=[MARKS["icx"], ICX_LOSES_UPDATES]),
]
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


@pytest.mark.parametrize("name", SEEDED_COMPILERS)
def test_a_reduction_seeded_from_omp_orig_keeps_the_update_of_every_thread(tmp_path, name):
    comp = MATRIX.compilers[name]
    soname = MATRIX.openmp_runtimes[MATRIX.defaults.openmp_runtime]
    library = runtime.resolve(soname, executables())
    source, obj, binary = tmp_path / "seeded.c", tmp_path / "seeded.o", tmp_path / "seeded"
    source.write_text(SEEDED_REDUCTION)
    openmp = comp.openmp[MATRIX.defaults.openmp_runtime]
    subprocess.run([comp.executables["c"], "-O3", "-fPIC", *openmp, "-c", str(source), "-o", str(obj)], check=True)
    subprocess.run(["gcc", str(obj), *runtime.link_flags(library, soname), "-o", str(binary)], check=True)

    sut = subprocess.run([str(binary)], env={**os.environ, "OMP_NUM_THREADS": str(THREADS)}, check=False)

    assert sut.returncode == 0
