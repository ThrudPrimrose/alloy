# Copyright 2026 ETH Zurich and the Alloy authors.
"""Main-memory bandwidth: the installed modules' theoretical peak from a saved ``dmidecode -t 17``, else measured."""

from alloy import machine

TWO_DDR5_MODULES_ONE_EMPTY_SLOT = """# dmidecode 3.6
Handle 0x0010, DMI type 17, 92 bytes
Memory Device
\tTotal Width: 64 bits
\tData Width: 64 bits
\tSize: 16 GB
\tType: DDR5
\tSpeed: 6400 MT/s
\tConfigured Memory Speed: 5600 MT/s

Handle 0x0011, DMI type 17, 92 bytes
Memory Device
\tData Width: 64 bits
\tSize: No Module Installed
\tSpeed: Unknown

Handle 0x0012, DMI type 17, 92 bytes
Memory Device
\tData Width: 64 bits
\tSize: 16 GB
\tSpeed: 5600 MT/s
"""


def test_the_peak_sums_each_installed_modules_configured_speed_times_its_width():
    sut = machine.theoretical_bandwidth(TWO_DDR5_MODULES_ONE_EMPTY_SLOT)

    assert sut == 2 * 5600e6 * 8


def test_a_listing_without_a_module_gives_no_peak():
    assert machine.theoretical_bandwidth("# dmidecode 3.6\nNo SMBIOS nor DMI entry point found.\n") is None


def test_a_saved_dmidecode_listing_is_read_from_the_file_the_variable_names(tmp_path, monkeypatch):
    saved = tmp_path / "dmidecode-17.txt"
    saved.write_text(TWO_DDR5_MODULES_ONE_EMPTY_SLOT)
    monkeypatch.setenv(machine.MEMORY_DEVICES_VARIABLE, str(saved))

    assert machine.memory_devices_text() == TWO_DDR5_MODULES_ONE_EMPTY_SLOT


def test_a_measured_copy_moves_bytes_at_a_positive_rate():
    assert machine.stream_bandwidth(threads=1, rounds=1) > 0
