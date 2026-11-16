# Copyright 2026 ETH Zurich and the Alloy authors.
"""The CPUs Alloy runs on: one hardware thread per physical core, never an SMT sibling."""

import functools
import json
import os
import pathlib
import re
import resource
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable
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


def cpu_list(text: str) -> set[int]:
    """The CPUs of a sysfs list such as ``0-7,16-23``."""
    cpus: set[int] = set()
    for part in filter(None, text.strip().split(",")):
        low, _, high = part.partition("-")
        cpus.update(range(int(low), int(high or low) + 1))
    return cpus


def cache_instances() -> list[tuple[int, int]]:
    """The largest cache level among the usable CPUs: ``(bytes, usable physical cores sharing it)`` per instance,
    the instance of the first usable core first; empty when sysfs lists no cache with a size."""
    sizes: dict[tuple[str, str], int] = {}
    for cpu in os.sched_getaffinity(0):
        for index in pathlib.Path(f"/sys/devices/system/cpu/cpu{cpu}/cache").glob("index*"):
            if not (index / "size").is_file():  # some arm64 kernels list a cache with no size: sysconf below
                continue
            size = (index / "size").read_text().strip()
            if not size.endswith("K"):  # sysfs reports KiB on Linux
                raise ValueError(f"{index}/size: {size!r} is not in KiB")
            key = ((index / "level").read_text().strip(), (index / "shared_cpu_list").read_text().strip())
            sizes[key] = int(size[:-1]) * 1024
    if not sizes:
        return []
    top = max(level for level, unused in sizes)
    cores = physical_cores()
    instances = [(size, cpu_list(shared)) for (level, shared), size in sizes.items() if level == top]
    instances.sort(key=lambda inst: min(inst[1] & set(cores), default=1 << 30))
    return [(size, len(shared & set(cores))) for size, shared in instances]


def largest_cache_bytes(threads: int | None = None) -> int:
    """The bytes of the largest cache level a team of ``threads`` (one per physical core, packed onto the instances
    in turn) reaches; ``None``, every usable core: the sum over its instances. A serial build sees one instance."""
    instances = cache_instances()
    if not instances:
        if (l3 := os.sysconf("SC_LEVEL3_CACHE_SIZE")) > 0:  # containers and some aarch64 VMs hide sysfs cache
            return l3
        raise RuntimeError("/sys/devices/system/cpu/cpu*/cache lists no cache")
    total, left = 0, len(physical_cores()) if threads is None else max(1, threads)
    for size, cores in instances:
        if left <= 0:
            break
        total += size
        left -= max(1, cores)
    return total


def cpu_flags() -> frozenset[str]:
    """The CPU feature flags ``/proc/cpuinfo`` lists: ``flags`` on x86, ``Features`` on aarch64 (first core's line)."""
    for line in pathlib.Path("/proc/cpuinfo").read_text().splitlines():
        key, unused, value = line.partition(":")
        if key.strip() in ("flags", "Features"):
            return frozenset(value.split())
    raise RuntimeError("/proc/cpuinfo lists no CPU flags")


def available_memory() -> int:
    for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    raise RuntimeError("/proc/meminfo has no MemAvailable")


#: Copies of a timed program's containers alive at once (inputs, reference outputs, each arm's copies).
TIMING_COPIES = 8


def timing_memory_cap() -> int:
    """Bytes one timed program may touch: its copies alive at once, and a verifying child's share of memory."""
    return min(available_memory() // TIMING_COPIES, available_memory() // (len(core_slots()) * 3))


def openmp_stack_bytes() -> int:
    """The stack one OpenMP worker reserves: ``OMP_STACKSIZE`` (a bare number is KiB), else the runtimes' 4 MiB
    default on x86-64 Linux."""
    text = os.environ.get("OMP_STACKSIZE", "").strip().upper()
    units = {"B": 1, "K": 1 << 10, "M": 1 << 20, "G": 1 << 30}
    if not text:
        return 4 << 20
    return int(text[:-1]) * units[text[-1]] if text[-1] in units else int(text) << 10


def data_segment_bytes() -> int:
    """This process's data segment now (``VmData``): every private writable mapping ``RLIMIT_DATA`` counts, the
    address space a runtime only reserved included (a GPU runtime's reservation can reach tens of GiB)."""
    for line in pathlib.Path("/proc/self/status").read_text().splitlines():
        if line.startswith("VmData:"):
            return int(line.split()[1]) * 1024
    raise RuntimeError("/proc/self/status has no VmData")


def limit_memory(share: float, threads: int) -> None:
    """Cap this process and its children (``RLIMIT_DATA``) at what it holds now plus ``share`` of the available
    memory and the stacks of ``threads`` OpenMP workers, so an oversized run fails instead of exhausting the machine.
    Never raises a cap."""
    soft, hard = resource.getrlimit(resource.RLIMIT_DATA)
    limit = data_segment_bytes() + int(share * available_memory()) + threads * openmp_stack_bytes()
    caps = [cap for cap in (soft, hard) if cap != resource.RLIM_INFINITY]
    limit = min([limit, *caps])
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
    """Main-memory bandwidth: from ``dmidecode`` (the modules' theoretical peak) or ``stream`` (a measured copy)."""

    bytes_per_second: float
    source: str


def memory_devices_file() -> pathlib.Path:
    cache = pathlib.Path(os.environ.get("XDG_CACHE_HOME", pathlib.Path.home() / ".cache"))
    return pathlib.Path(os.environ.get(MEMORY_DEVICES_VARIABLE, cache / "alloy" / "dmidecode-17.txt"))


def memory_devices_text() -> str:
    saved = memory_devices_file()
    if saved.is_file():
        return saved.read_text()
    try:
        run = subprocess.run(["dmidecode", "-t", "17"], capture_output=True, text=True, check=False, timeout=30)
    except FileNotFoundError:
        return ""
    return run.stdout if run.returncode == 0 else ""


def theoretical_bandwidth(text: str) -> float | None:
    """The installed modules' peak in bytes per second, or ``None`` when no module lists a speed and a width."""
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
    """The best of ``rounds`` parallel copies (numpy releases the GIL), in bytes read plus written per second."""
    sources = [np.ones(STREAM_BYTES_PER_THREAD // 8) for _ in range(threads)]
    targets = [np.empty_like(s) for s in sources]
    best = 0.0
    with ThreadPoolExecutor(max_workers=threads) as pool:
        for _ in range(rounds):
            start = time.perf_counter()
            list(pool.map(np.copyto, targets, sources))
            best = max(best, 2 * STREAM_BYTES_PER_THREAD * threads / (time.perf_counter() - start))
    return best


MEASURING = threading.Lock()


@functools.lru_cache(maxsize=1, typed=True)
def measured_bandwidth() -> float:
    return stream_bandwidth(len(physical_cores()))


def memory_bandwidth() -> Bandwidth:
    peak = theoretical_bandwidth(memory_devices_text())
    if peak is not None:
        return Bandwidth(peak, "dmidecode")
    # a cache does not serialize a miss: threads measuring at once run against each other and read low
    with MEASURING:
        return Bandwidth(measured_bandwidth(), "stream")


@dataclass(slots=True, frozen=True)
class Clock:
    """A CPU clock and its source: ``cpufreq`` (the first usable CPU's maximum), ``cpuinfo`` (the highest ``cpu MHz``
    listed), ``lscpu`` (its ``CPU max MHz``), or ``measured`` (the running clock of a chain of dependent additions, one
    per cycle on every current core; an aarch64 kernel lists no ``cpu MHz`` and a container often hides cpufreq)."""

    hz: float
    source: str


def cpufreq_hz() -> float | None:
    path = pathlib.Path(f"/sys/devices/system/cpu/cpu{min(os.sched_getaffinity(0))}/cpufreq/cpuinfo_max_freq")
    return int(path.read_text()) * 1e3 if path.is_file() else None


def cpuinfo_hz() -> float | None:
    mhz = re.findall(r"^cpu MHz\s*:\s*([\d.]+)", pathlib.Path("/proc/cpuinfo").read_text(), re.MULTILINE)
    return max(float(m) for m in mhz) * 1e6 if mhz else None


def lscpu_fields(entries: list[dict[str, object]]) -> dict[str, str]:
    """``lscpu --json``'s fields, its nested ``children`` flattened."""
    out: dict[str, str] = {}
    for entry in entries:
        out[str(entry.get("field", ""))] = str(entry.get("data", ""))
        children = entry.get("children")
        if isinstance(children, list):
            out |= lscpu_fields(children)
    return out


def lscpu_hz() -> float | None:
    try:
        run = subprocess.run(["lscpu", "--json"], capture_output=True, text=True, check=False, timeout=30)
    except FileNotFoundError:
        return None
    if run.returncode != 0:
        return None
    mhz = lscpu_fields(json.loads(run.stdout).get("lscpu", [])).get("CPU max MHz:", "")
    return float(mhz) * 1e6 if mhz.replace(".", "", 1).isdigit() and float(mhz) > 0 else None


#: Eight dependent additions per iteration, the chain the measured clock times (the loop counter runs beside it).
#: Register to register: recent x86 cores fold a chain of immediate additions at rename and run it three times faster.
CHAIN = """#include <stdint.h>
#include <stdio.h>
#include <time.h>
#if defined(__aarch64__)
#define ADD asm volatile("add %0, %0, %0" : "+r"(x));
#else
#define ADD asm volatile("add %0, %0" : "+r"(x));
#endif
static double now(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + 1e-9 * t.tv_nsec; }
int main(void) {
  double best = 0.0;
  uint64_t x = 1;
  for (int round = 0; round < 5; ++round) {
    double start = now(), took;
    uint64_t adds = 0;
    do {
      for (int i = 0; i < 1000000; ++i) { ADD ADD ADD ADD ADD ADD ADD ADD }
      adds += 8000000;
    } while ((took = now() - start) < 0.05);
    if (adds / took > best) best = adds / took;
  }
  printf("%.0f %llu\\n", best, (unsigned long long)(x & 1));
  return 0;
}
"""


def measured_hz() -> float | None:
    """The best of five 50-ms runs of :data:`CHAIN`, built by the system C compiler; ``None`` without one."""
    with tempfile.TemporaryDirectory(prefix="alloy_clock_") as folder:
        source, binary = pathlib.Path(folder) / "chain.c", pathlib.Path(folder) / "chain"
        source.write_text(CHAIN)
        try:
            subprocess.run(["cc", "-O2", str(source), "-o", str(binary)], check=True, capture_output=True, timeout=60)
        except (FileNotFoundError, subprocess.CalledProcessError):
            return None
        run = subprocess.run([str(binary)], capture_output=True, text=True, check=True, timeout=60)
    return float(run.stdout.split()[0])


#: The clock's sources in the order they are asked.
CLOCK_SOURCES: tuple[tuple[str, Callable[[], float | None]], ...] = (
    ("cpufreq", cpufreq_hz),
    ("cpuinfo", cpuinfo_hz),
    ("lscpu", lscpu_hz),
    ("measured", measured_hz),
)


@functools.lru_cache(maxsize=1, typed=True)
def clock() -> Clock:
    """The CPU clock from the first of :data:`CLOCK_SOURCES` that answers."""
    for source, probe in CLOCK_SOURCES:
        if (hz := probe()) is not None:
            return Clock(hz, source)
    raise RuntimeError("no CPU clock: no cpufreq, no cpu MHz, no lscpu maximum, and no C compiler to measure one")


def max_frequency_hz() -> float:
    """The clock the predictions turn cycles into seconds with (:func:`clock`)."""
    return clock().hz


def pin_worker(cpus: set[int]) -> None:
    """Confine a worker process to ``cpus``; an empty set (unreadable topology) leaves it unpinned. Lives here, not in
    the route module, because a spawned worker imports the module that defines its initializer."""
    if cpus:
        os.sched_setaffinity(0, cpus)


if __name__ == "__main__":
    found = clock()
    print(f"clock {found.hz / 1e9:.3f} GHz from {found.source}")
