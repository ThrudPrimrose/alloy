# Copyright 2026 ETH Zurich and the Alloy authors.
import pytest

from alloy import machine


@pytest.mark.parametrize(
    ("setting", "expected"),
    [("512M", 512 << 20), ("2g", 2 << 30), ("1024K", 1 << 20), ("2048", 2 << 20), ("", 4 << 20)],
)
def test_the_openmp_worker_stack_follows_omp_stacksize(monkeypatch, setting, expected):
    monkeypatch.setenv("OMP_STACKSIZE", setting)

    assert machine.openmp_stack_bytes() == expected


def without_sources(monkeypatch, *names: str) -> None:
    kept = tuple((source, probe) for source, probe in machine.CLOCK_SOURCES if source not in names)
    gone = tuple((source, lambda: None) for source, probe in machine.CLOCK_SOURCES if source in names)
    monkeypatch.setattr(machine, "CLOCK_SOURCES", gone + kept)
    machine.clock.cache_clear()


def test_a_host_without_cpufreq_cpuinfo_or_lscpu_measures_its_clock_within_a_fifth(monkeypatch):
    """A3: an aarch64 kernel lists no cpu MHz and a container hides cpufreq; the measured clock still answers."""
    # only cpufreq's maximum bounds a running clock: cpuinfo lists the current or the nominal clock, which a boosting
    # core exceeds (3.56 GHz measured against a listed 2.6 GHz on a CI VM)
    maximum = machine.cpufreq_hz()
    without_sources(monkeypatch, "cpufreq", "cpuinfo", "lscpu")

    sut = machine.clock()

    assert sut.source == "measured"
    if maximum is not None:
        assert 0.8 * maximum <= sut.hz <= 1.05 * maximum, (sut.hz, maximum)
    else:
        assert 0.5e9 <= sut.hz <= 6.5e9, sut.hz
    machine.clock.cache_clear()


def test_each_clock_source_is_named_and_asked_in_order(monkeypatch):
    calls: list[str] = []

    def answering(name: str, hz: float | None):
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


def test_lscpu_fields_are_read_from_nested_children():
    entries: list[dict[str, object]] = [
        {"field": "Architecture:", "data": "aarch64", "children": [{"field": "CPU max MHz:", "data": "3456.0"}]}
    ]

    assert machine.lscpu_fields(entries)["CPU max MHz:"] == "3456.0"


def test_a_team_reaches_the_l3_of_the_complexes_it_spans_and_a_serial_build_one(monkeypatch):
    """A9.1, team-aware (owner, 2026-11-16): three 32 MiB L3s of eight cores each, as an EPYC's complexes."""
    monkeypatch.setattr(machine, "cache_instances", lambda: [(32 << 20, 8)] * 3)
    monkeypatch.setattr(machine, "physical_cores", lambda: tuple(range(24)))

    assert machine.largest_cache_bytes() == 96 << 20
    assert machine.largest_cache_bytes(1) == 32 << 20
    assert machine.largest_cache_bytes(9) == 64 << 20


def test_a_sysfs_cpu_list_reads_ranges_and_singles():
    assert machine.cpu_list("0-3,8,10-11\n") == {0, 1, 2, 3, 8, 10, 11}


def test_the_copy_measurement_holds_at_most_an_eighth_of_the_available_memory(monkeypatch):
    """A9.3: 128 MiB per core on a 64-core node with little free memory would push the probe into swap."""
    monkeypatch.setattr(machine, "available_memory", lambda: 4 << 30)

    assert machine.stream_bytes_per_thread(64) == 8 << 20  # 512 MiB budget / (2 x 64) = 4 MiB, raised to the floor
    assert machine.stream_bytes_per_thread(2) == machine.STREAM_BYTES_PER_THREAD
    monkeypatch.setattr(machine, "available_memory", lambda: 1 << 30)
    assert machine.stream_bytes_per_thread(4) == 16 << 20
