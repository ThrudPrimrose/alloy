# Copyright 2026 ETH Zurich and the Alloy authors.
"""The CPUs Alloy runs on: one hardware thread per physical core, never an SMT sibling."""

import os
import pathlib

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


def core_slots() -> list[tuple[int, ...]]:
    """Disjoint sets of ``CHILD_THREADS`` physical cores, at most ``MAX_JOBS``; one set of every core when fewer."""
    cores = physical_cores()
    jobs = min(MAX_JOBS, len(cores) // CHILD_THREADS)
    if jobs == 0:
        return [cores]
    return [cores[i * CHILD_THREADS : (i + 1) * CHILD_THREADS] for i in range(jobs)]
