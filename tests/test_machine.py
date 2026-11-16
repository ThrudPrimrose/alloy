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
    truth = machine.cpufreq_hz() or machine.cpuinfo_hz() or machine.lscpu_hz()
    without_sources(monkeypatch, "cpufreq", "cpuinfo", "lscpu")

    sut = machine.clock()

    assert sut.source == "measured"
    if truth is not None:  # the running clock sits below the maximum, or above a listed base clock under boost
        assert 0.8 * truth <= sut.hz <= 1.25 * truth, (sut.hz, truth)
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
    entries = [{"field": "Architecture:", "data": "aarch64", "children": [{"field": "CPU max MHz:", "data": "3456.0"}]}]

    assert machine.lscpu_fields(entries)["CPU max MHz:"] == "3456.0"
