# Copyright 2026 ETH Zurich and the Alloy authors.
"""The cost column: llvm-mca's model of each row's compiled instruction, in register form, on the paper's CPUs."""

import importlib.util
import pathlib

import pytest

from alloy.isa.__main__ import main
from alloy.isa.costs import CPUS, costs
from alloy.isa.table import ALL_DTYPES, Entry, load

HELPER = pathlib.Path(__file__).parents[1] / "helpers" / "isacost.py"


@pytest.fixture(scope="module")
def isacost():
    spec = importlib.util.spec_from_file_location("isacost", HELPER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("compiled", "op", "measured"),
    [
        ("vaddpd\t(%rsi), %ymm0, %ymm0", "add", "vaddpd\t%ymm15, %ymm0, %ymm0"),
        ("vandpd\t.LCPI0_0(%rip){1to8}, %zmm0, %zmm0", "abs", "vandpd\t%zmm15, %zmm0, %zmm0"),
        ("vmovups\t(%rdi), %zmm0", "load", "vmovups\t(%rdi), %zmm0"),
        ("fadd\tv0.4s, v0.4s, v1.4s", "add", "fadd\tv0.4s, v0.4s, v1.4s"),
    ],
)
def test_a_folded_load_is_costed_as_the_arithmetic_alone(isacost, compiled: str, op: str, measured: str):
    assert isacost.register_form(compiled, op) == measured


def test_an_instruction_info_row_reads_uops_latency_and_throughput(isacost):
    row = isacost.INFO_ROW.match(" 1      4     1.00                        vfmadd231pd\t%zmm1, %zmm2, %zmm0")

    assert row is not None
    assert row.groups() == ("1", "4", "1.00", "vfmadd231pd\t%zmm1, %zmm2, %zmm0")


def test_zen4_issues_a_512_bit_add_as_two_256_bit_halves():
    (wide,), (half,) = costs("avx512", "add", "f64"), costs("avx2", "add", "f64")

    assert wide.cpu == half.cpu == "znver4"
    assert wide.latency == half.latency
    assert wide.rthroughput == 2 * half.rthroughput


@pytest.mark.parametrize("isa", sorted(CPUS))
@pytest.mark.parametrize("op", ["add", "mul", "fma", "div"])
def test_the_core_arithmetic_has_a_cost_on_every_isa(isa: str, op: str):
    found = costs(isa, op, "f64")

    assert found, f"{isa}/f64/{op} has no cost"
    assert all(c.cpu == CPUS[isa] and c.latency > 0 and c.rthroughput > 0 for c in found)


def test_the_lookup_prints_the_rows_cost(capsys: pytest.CaptureFixture[str]):
    assert main(["lookup", "avx512", "div", "f64", "--no-verify"]) == 0

    assert "cost:      znver4 (llvm-mca): vdivpd" in capsys.readouterr().out


def test_every_row_with_a_mnemonic_has_a_cost():
    table = load()
    missing = [
        f"{isa}/{dtype}/{op}"
        for isa, target in table.isas.items()
        for dtype in ALL_DTYPES
        for op, entry in target.entries(dtype).items()
        if entry.mnemonic and not entry.approximations and not costs(isa, op, dtype)
    ]

    assert missing == []


def test_a_reduction_counts_every_add_and_keeps_its_shuffles():
    found = [c.instruction.split()[0] for c in costs("avx512", "reduce_add", "f64")]

    assert found.count("vaddpd") >= 2, found
    assert any(name.startswith(("vshuf", "vperm", "vextract", "vunpck")) for name in found), found


def test_matching_keeps_repeats_and_reads_a_float_domain_twin(isacost):
    lines = ["vaddpd\t%zmm1, %zmm0, %zmm0", "vaddpd\t%zmm2, %zmm0, %zmm0"]
    twin = ["vmovups\t(%rdi), %ymm0", "vandps\t(%rsi), %ymm0, %ymm0", "vmovups\t%ymm0, (%rcx)"]

    assert isacost.matching(lines, Entry(mnemonic="vaddpd", intrinsic="x")) == lines
    assert isacost.matching(twin, Entry(mnemonic="vpand", intrinsic="x")) == [twin[1]]


@pytest.mark.parametrize(
    ("op", "picked", "mnemonic"),
    [("store", "st1d\t{ z0.d }, p0, [x1]", "st1d"), ("load", "ld1d\t{ z0.d }, p0/z, [x0]", "ld1d")],
)
def test_an_arm_memory_row_is_costed_by_its_direction(isacost, op: str, picked: str, mnemonic: str):
    lines = ["ldr\tz1, [x2]", "ld1d\t{ z0.d }, p0/z, [x0]", "st1d\t{ z0.d }, p0, [x1]"]

    assert picked in isacost.directional(lines, op)
    assert all(line.startswith("st" if op == "store" else "ld") for line in isacost.directional(lines, op))
    assert [c.instruction.split()[0] for c in costs("sve", op, "f64")] == [mnemonic]


@pytest.mark.parametrize("isa", ["avx2", "avx512"])
@pytest.mark.parametrize("op", ["gather", "scatter"])
def test_an_x86_gather_or_scatter_says_its_cost_is_not_modelled(isa: str, op: str, capsys: pytest.CaptureFixture[str]):
    (found,) = costs(isa, op, "f64")

    assert found.note.startswith("not modelled") and found.rthroughput == 0
    assert main(["lookup", isa, op, "f64", "--no-verify"]) == 0
    assert "not modelled" in capsys.readouterr().out
