# Copyright 2026 ETH Zurich and the Alloy authors.
"""The CPUs Alloy runs on: one hardware thread per physical core, never an SMT sibling."""

import os
import pathlib
import resource

#: Threads per verification child: comparisons stay multithreaded, so a parallel reduction shows its nondeterminism.
CHILD_THREADS = 4
#: Children running at once, whatever the core count (memory of the build box).
MAX_JOBS = 3


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
            if not size.endswith("K"):  # shortcut: sysfs reports KiB on Linux, extend if another unit appears
                raise ValueError(f"{index}/size: {size!r} is not in KiB")
            key = ((index / "level").read_text().strip(), (index / "shared_cpu_list").read_text().strip())
            sizes[key] = int(size[:-1]) * 1024
    top = max(level for level, _ in sizes)
    return sum(size for (level, _), size in sizes.items() if level == top)


def available_memory() -> int:
    """``MemAvailable`` from ``/proc/meminfo``, in bytes."""
    for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    raise RuntimeError("/proc/meminfo has no MemAvailable")


def limit_memory(share: float) -> None:
    """Cap this process and its children at ``share`` of the memory available now, so an oversized run fails with
    a MemoryError (or a crashed child) instead of exhausting the machine. Never raises an existing cap."""
    _, hard = resource.getrlimit(resource.RLIMIT_DATA)
    limit = int(share * available_memory())
    limit = limit if hard == resource.RLIM_INFINITY else min(limit, hard)
    resource.setrlimit(resource.RLIMIT_DATA, (limit, limit))


def core_slots() -> list[tuple[int, ...]]:
    """Disjoint sets of ``CHILD_THREADS`` physical cores, at most ``MAX_JOBS``; one set of every core when fewer."""
    cores = physical_cores()
    jobs = min(MAX_JOBS, len(cores) // CHILD_THREADS)
    if jobs == 0:
        return [cores]
    return [cores[i * CHILD_THREADS : (i + 1) * CHILD_THREADS] for i in range(jobs)]
