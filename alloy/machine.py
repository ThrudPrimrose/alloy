# Copyright 2026 ETH Zurich and the Alloy authors.
"""The CPUs Alloy runs on: one hardware thread per physical core, never an SMT sibling."""

import os
import pathlib
import resource

#: Threads per verification child: comparisons stay multithreaded, so a parallel reduction shows its nondeterminism.
CHILD_THREADS = 4
#: Memory one scope compile is budgeted, bounding the compilers run at once on a machine short of memory.
COMPILE_BYTES = 1 << 30


def physical_cores() -> tuple[int, ...]:
    """The lowest usable CPU of every physical core among the usable CPUs (what ``nproc`` counts)."""
    seen: set[str] = set()
    cores: list[int] = []
    for cpu in sorted(os.sched_getaffinity(0)):
        siblings = pathlib.Path(f"/sys/devices/system/cpu/cpu{cpu}/topology/thread_siblings_list").read_text()
        if siblings not in seen:
            seen.add(siblings)
            cores.append(cpu)
    return tuple(cores)


def largest_cache_bytes() -> int:
    """The largest cache level among the usable CPUs, summed over its distinct instances."""
    sizes: dict[tuple[str, str], int] = {}
    for cpu in os.sched_getaffinity(0):
        for index in pathlib.Path(f"/sys/devices/system/cpu/cpu{cpu}/cache").glob("index*"):
            size = (index / "size").read_text().strip()
            if not size.endswith("K"):  # sysfs reports KiB on Linux
                raise ValueError(f"{index}/size: {size!r} is not in KiB")
            key = ((index / "level").read_text().strip(), (index / "shared_cpu_list").read_text().strip())
            sizes[key] = int(size[:-1]) * 1024
    top = max(level for level, _ in sizes)
    return sum(size for (level, _), size in sizes.items() if level == top)


def cpu_flags() -> frozenset[str]:
    """The CPU feature flags ``/proc/cpuinfo`` lists: ``flags`` on x86, ``Features`` on aarch64 (first core's line)."""
    for line in pathlib.Path("/proc/cpuinfo").read_text().splitlines():
        key, _, value = line.partition(":")
        if key.strip() in ("flags", "Features"):
            return frozenset(value.split())
    raise RuntimeError("/proc/cpuinfo lists no CPU flags")


def available_memory() -> int:
    """``MemAvailable`` from ``/proc/meminfo``, in bytes."""
    for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    raise RuntimeError("/proc/meminfo has no MemAvailable")


#: Copies of a timed program's containers alive at once (inputs, reference outputs, each arm's copies).
TIMING_COPIES = 8


def timing_memory_cap() -> int:
    """Bytes one timed program may touch: the available memory over :data:`TIMING_COPIES`."""
    return available_memory() // TIMING_COPIES


def openmp_stack_bytes() -> int:
    """The stack one OpenMP worker reserves: ``OMP_STACKSIZE`` (a bare number is KiB), else the runtimes' 4 MiB
    default on x86-64 Linux."""
    text = os.environ.get("OMP_STACKSIZE", "").strip().upper()
    units = {"B": 1, "K": 1 << 10, "M": 1 << 20, "G": 1 << 30}
    if not text:
        return 4 << 20
    return int(text[:-1]) * units[text[-1]] if text[-1] in units else int(text) << 10


def limit_memory(share: float, threads: int) -> None:
    """Cap this process and its children (``RLIMIT_DATA``) at ``share`` of the available memory plus the stacks of
    ``threads`` OpenMP workers, so an oversized run fails instead of exhausting the machine. Never raises a cap."""
    _, hard = resource.getrlimit(resource.RLIMIT_DATA)
    limit = int(share * available_memory()) + threads * openmp_stack_bytes()
    limit = limit if hard == resource.RLIM_INFINITY else min(limit, hard)
    resource.setrlimit(resource.RLIMIT_DATA, (limit, limit))


def core_slots() -> list[tuple[int, ...]]:
    """Disjoint sets of ``CHILD_THREADS`` physical cores; one set of every core when fewer. Each child running in a
    slot is capped at its share of memory (:func:`limit_memory`)."""
    cores = physical_cores()
    jobs = len(cores) // CHILD_THREADS
    if jobs == 0:
        return [cores]
    return [cores[i * CHILD_THREADS : (i + 1) * CHILD_THREADS] for i in range(jobs)]


def compile_jobs() -> int:
    """Compilers run at once: one per physical core, fewer when the available memory does not cover them."""
    return max(1, min(len(physical_cores()), available_memory() // COMPILE_BYTES))
