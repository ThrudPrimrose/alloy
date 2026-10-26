# Copyright 2026 ETH Zurich and the Alloy authors.
"""The CPUs Alloy runs on: one hardware thread per physical core, never an SMT sibling."""

import functools
import os
import pathlib
import re
import resource
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import numpy as np

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


#: A saved ``dmidecode -t 17`` (reading the DMI tables needs root): this variable's path, else the default below.
MEMORY_DEVICES_VARIABLE = "ALLOY_MEMORY_DEVICES"
#: Bytes each thread of the copy measurement streams through, per copy (well beyond any cache).
STREAM_BYTES_PER_THREAD = 64 << 20


@dataclass(slots=True, frozen=True)
class Bandwidth:
    """Main-memory bandwidth in bytes per second and where it comes from: ``dmidecode`` (the installed modules'
    theoretical peak) or ``stream`` (a measured parallel copy)."""

    bytes_per_second: float
    source: str


def memory_devices_file() -> pathlib.Path:
    cache = pathlib.Path(os.environ.get("XDG_CACHE_HOME", pathlib.Path.home() / ".cache"))
    return pathlib.Path(os.environ.get(MEMORY_DEVICES_VARIABLE, cache / "alloy" / "dmidecode-17.txt"))


def memory_devices_text() -> str:
    """``dmidecode -t 17`` output: the saved file when there is one, else a direct run; empty when neither works."""
    saved = memory_devices_file()
    if saved.is_file():
        return saved.read_text()
    try:
        run = subprocess.run(["dmidecode", "-t", "17"], capture_output=True, text=True, check=False, timeout=30)
    except FileNotFoundError:
        return ""
    return run.stdout if run.returncode == 0 else ""


def theoretical_bandwidth(text: str) -> float | None:
    """The installed modules' peak in bytes per second: the sum of configured MT/s x data width over every device
    with a module; ``None`` when the text lists none with a speed and a width."""
    total = 0.0
    for device in text.split("Memory Device")[1:]:
        if re.search(r"^\s*Size:\s*No Module Installed", device, re.MULTILINE):
            continue
        speed = re.search(r"^\s*Configured (?:Memory|Clock) Speed:\s*(\d+)\s*MT/s", device, re.MULTILINE) or re.search(
            r"^\s*Speed:\s*(\d+)\s*MT/s", device, re.MULTILINE
        )
        width = re.search(r"^\s*Data Width:\s*(\d+)\s*bits", device, re.MULTILINE)
        if speed is not None and width is not None:
            total += int(speed.group(1)) * 1e6 * int(width.group(1)) / 8
    return total or None


def stream_bandwidth(threads: int, rounds: int = 3) -> float:
    """A measured parallel copy: every thread copies its own arrays (numpy releases the GIL), the best of ``rounds``;
    bytes read plus bytes written per second."""
    sources = [np.ones(STREAM_BYTES_PER_THREAD // 8) for _ in range(threads)]
    targets = [np.empty_like(s) for s in sources]
    best = 0.0
    with ThreadPoolExecutor(max_workers=threads) as pool:
        for _ in range(rounds):
            start = time.perf_counter()
            list(pool.map(np.copyto, targets, sources))
            best = max(best, 2 * STREAM_BYTES_PER_THREAD * threads / (time.perf_counter() - start))
    return best


@functools.lru_cache(maxsize=1, typed=True)
def memory_bandwidth() -> Bandwidth:
    """Main-memory bandwidth: the theoretical peak from ``dmidecode -t 17`` when available, else measured."""
    peak = theoretical_bandwidth(memory_devices_text())
    if peak is not None:
        return Bandwidth(peak, "dmidecode")
    return Bandwidth(stream_bandwidth(len(physical_cores())), "stream")


@functools.lru_cache(maxsize=1, typed=True)
def max_frequency_hz() -> float:
    """The first usable CPU's maximum clock: cpufreq's ``cpuinfo_max_freq``, else the highest ``cpu MHz`` listed."""
    cpu = min(os.sched_getaffinity(0))
    path = pathlib.Path(f"/sys/devices/system/cpu/cpu{cpu}/cpufreq/cpuinfo_max_freq")
    if path.is_file():
        return int(path.read_text()) * 1e3
    mhz = re.findall(r"^cpu MHz\s*:\s*([\d.]+)", pathlib.Path("/proc/cpuinfo").read_text(), re.MULTILINE)
    if not mhz:
        raise RuntimeError("neither cpufreq nor /proc/cpuinfo gives a CPU clock")
    return max(float(m) for m in mhz) * 1e6
