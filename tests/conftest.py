# Copyright 2026 ETH Zurich and the Alloy authors.
import os
import resource
import sys

# No test uses MPI, and DaCe's usability probe (mpi4py_is_usable, reached from every
# ``@dace.program`` parse) runs ``from mpi4py import MPI``, which dlopens libmpi and MPI_Inits a
# singleton job; on a box without an MPI launcher that bring-up can stall and hang the run (seen as
# a parse stuck in preprocess_dace_program). Make the probe answer "no MPI": the import then raises
# ImportError, which the probe catches and reports as unavailable.
sys.modules.setdefault("mpi4py", None)  # type: ignore[arg-type]

from alloy import machine

# An oversized test fails with MemoryError instead of exhausting the machine. The cap is a share of the machine's
# total memory, not of what is free when a worker starts: parallel workers would make it depend on the load. The
# stacks of every CPU OpenMP may start a thread on are reserved, as a judge-run reference starts one per CPU.
TOTAL = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
LIMIT = int(0.75 * TOTAL) + len(os.sched_getaffinity(0)) * machine.openmp_stack_bytes()
_, HARD = resource.getrlimit(resource.RLIMIT_DATA)
CAP = LIMIT if HARD == resource.RLIM_INFINITY else min(LIMIT, HARD)
resource.setrlimit(resource.RLIMIT_DATA, (CAP, CAP))

import functools
import pathlib
import shutil
from collections.abc import Callable

import pytest

from alloy.isa.validate import emulated, host_can_run

#: Where a host keeps libmvec, glibc's vector math library.
LIBMVEC = ("/lib/x86_64-linux-gnu/libmvec.so.1", "/usr/lib/libmvec.so.1")

#: What each toolchain mark needs. A marked test on a host without it fails: deselect the mark (-m "not <mark>"),
#: never skip, so a run that reports green ran what it names.
NEEDS: dict[str, Callable[[], bool]] = {
    "gcc": lambda: shutil.which("gcc") is not None and shutil.which("g++") is not None,
    "avx2": lambda: host_can_run("avx2", "f64"),
    "avx512": lambda: host_can_run("avx512", "f64"),
    "aarch64": lambda: emulated("neon") is not None,
    "rvv": lambda: emulated("rvv") is not None,
    "libmvec": lambda: any(pathlib.Path(path).is_file() for path in LIBMVEC),
    "cuda": lambda: shutil.which("nvcc") is not None,
    "hip": lambda: shutil.which("hipcc") is not None,
    "softhier": lambda: bool(
        (os.environ.get("SOFTHIER_IMAGE") and shutil.which("singularity"))
        or (os.environ.get("SOFTHIER_GVSOC") and os.environ.get("SOFTHIER_SDK"))
    ),
    "softhier_sdk": lambda: bool(os.environ.get("SOFTHIER_TOOLCHAIN") and os.environ.get("SOFTHIER_SDK")),
}


@functools.cache
def has(mark: str) -> bool:
    return NEEDS[mark]()


def pytest_runtest_setup(item: pytest.Item) -> None:
    missing = [mark for mark in NEEDS if item.get_closest_marker(mark) is not None and not has(mark)]
    if missing:
        pytest.fail(f"this host lacks {', '.join(missing)}: deselect with -m 'not {missing[0]}'", pytrace=False)
