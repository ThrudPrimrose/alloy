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
