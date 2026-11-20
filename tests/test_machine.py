# Copyright 2026 ETH Zurich and the Alloy authors.
import pathlib
import re
import subprocess
from collections.abc import Callable

import pytest

from alloy import machine


@pytest.mark.parametrize(
    ("setting", "expected"),
    [("512M", 512 << 20), ("2g", 2 << 30), ("1024K", 1 << 20), ("2048", 2 << 20), ("", 4 << 20)],
)
def test_the_openmp_worker_stack_follows_omp_stacksize(
    monkeypatch: pytest.MonkeyPatch, setting: str, expected: int
) -> None:
    monkeypatch.setenv("OMP_STACKSIZE", setting)

    assert machine.openmp_stack_bytes() == expected


def without_sources(monkeypatch: pytest.MonkeyPatch, *names: str) -> None:
    kept = tuple((source, probe) for source, probe in machine.CLOCK_SOURCES if source not in names)
    gone = tuple((source, lambda: None) for source, _ in machine.CLOCK_SOURCES if source in names)
    monkeypatch.setattr(machine, "CLOCK_SOURCES", gone + kept)
    machine.clock.cache_clear()


def test_a_host_without_cpufreq_cpuinfo_or_lscpu_measures_its_clock_within_a_fifth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A3: an aarch64 kernel lists no cpu MHz and a container hides cpufreq; the measured clock still answers."""
    # only cpufreq's maximum bounds a running clock: cpuinfo lists the current or the nominal clock, which a boosting
    # core exceeds (3.56 GHz measured against a listed 2.6 GHz on a CI VM); a guest's cpufreq lists the maximum its
    # virtual ACPI tables advertise, which the boosting host core exceeds too (2.96 GHz against 2.3 GHz on a CI VM)
    maximum = machine.cpufreq_hz()
    guest = re.search(r"^flags\s*:.*\bhypervisor\b", pathlib.Path("/proc/cpuinfo").read_text(), re.MULTILINE)
    without_sources(monkeypatch, "cpufreq", "cpuinfo", "lscpu")

    sut = machine.clock()

    assert sut.source == "measured"
    if maximum is not None:
        assert 0.8 * maximum <= sut.hz <= (6.5e9 if guest else 1.05 * maximum), (sut.hz, maximum, bool(guest))
    else:
        assert 0.5e9 <= sut.hz <= 6.5e9, sut.hz
    machine.clock.cache_clear()


def test_each_clock_source_is_named_and_asked_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def answering(name: str, hz: float | None) -> Callable[[], float | None]:
        def probe() -> float | None:
            calls.append(name)
            return hz

        return probe

    monkeypatch.setattr(
        machine,
        "CLOCK_SOURCES",
        (("cpufreq", answering("cpufreq", None)), ("cpuinfo", answering("cpuinfo", None)),
         ("lscpu", answering("lscpu", 2.5e9)), ("measured", answering("measured", 1.0))),
    )  # fmt: skip
    machine.clock.cache_clear()

    assert machine.clock() == machine.Clock(2.5e9, "lscpu")
    assert calls == ["cpufreq", "cpuinfo", "lscpu"]
    machine.clock.cache_clear()


def test_lscpu_fields_are_read_from_nested_children() -> None:
    entries: list[dict[str, object]] = [
        {"field": "Architecture:", "data": "aarch64", "children": [{"field": "CPU max MHz:", "data": "3456.0"}]}
    ]

    assert machine.lscpu_fields(entries)["CPU max MHz:"] == "3456.0"


def test_a_team_reaches_the_l3_of_the_complexes_it_spans_and_a_serial_build_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A9.1, team-aware (owner, 2026-11-16): three 32 MiB L3s of eight cores each, as an EPYC's complexes."""
    monkeypatch.setattr(machine, "cache_instances", lambda: [(32 << 20, 8)] * 3)
    monkeypatch.setattr(machine, "physical_cores", lambda: tuple(range(24)))

    assert machine.largest_cache_bytes() == 96 << 20
    assert machine.largest_cache_bytes(1) == 32 << 20
    assert machine.largest_cache_bytes(9) == 64 << 20


def test_a_sysfs_cpu_list_reads_ranges_and_singles() -> None:
    assert machine.cpu_list("0-3,8,10-11\n") == {0, 1, 2, 3, 8, 10, 11}


def test_the_copy_measurement_holds_at_most_an_eighth_of_the_available_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    """A9.3: 128 MiB per core on a 64-core node with little free memory would push the probe into swap."""
    monkeypatch.setattr(machine, "available_memory", lambda: 4 << 30)

    assert machine.stream_bytes_per_thread(64) == 8 << 20  # 512 MiB budget / (2 x 64) = 4 MiB, raised to the floor
    assert machine.stream_bytes_per_thread(2) == machine.STREAM_BYTES_PER_THREAD
    monkeypatch.setattr(machine, "available_memory", lambda: 1 << 30)
    assert machine.stream_bytes_per_thread(4) == 16 << 20


def test_a_host_without_the_openmp_runtime_prices_a_region_at_the_default() -> None:
    assert machine.region_cost(None, "omp") == machine.RegionCost(machine.REGION_NS, "default")


def silent(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess("region", 0, stdout="", stderr="")


def raising(error: Exception) -> Callable[..., subprocess.CompletedProcess[str]]:
    def run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise error

    return run


@pytest.mark.parametrize(
    "run",
    [
        raising(FileNotFoundError("cc")),
        raising(subprocess.CalledProcessError(1, "cc")),
        raising(subprocess.TimeoutExpired("region", 120)),
        silent,
    ],
    ids=["no compiler", "failed build or crash", "timeout", "no number printed"],
)
def test_a_region_probe_that_fails_prices_a_region_at_the_default(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, run: Callable[..., object]
) -> None:
    """A probe that does not build, end, or print a number must not end the prediction that asked for it."""
    monkeypatch.setattr(subprocess, "run", run)

    sut = machine.region_cost(tmp_path / "libomp.so", "omp")

    assert sut == machine.RegionCost(machine.REGION_NS, "default")


def test_the_region_cost_is_measured_on_the_matrix_runtime_of_this_host() -> None:
    """A15: the prediction's region cost comes from this host and runtime, not Zen 4's constant."""
    from alloy import configuration_matrix
    from alloy.backend import runtime
    from alloy.heuristics import predict

    matrix = configuration_matrix.load()
    name = matrix.defaults.openmp_runtime
    sut = machine.region_cost(runtime.default_library(matrix, name), matrix.openmp_runtimes[name])

    assert sut.source == "measured"
    assert 0.0 < sut.ns < 1e6  # an empty region on a warm team: well under a millisecond on any host
    assert predict.region_ns(matrix) == sut.ns


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
