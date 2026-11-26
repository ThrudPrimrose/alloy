# Copyright 2026 ETH Zurich and the Alloy authors.
"""The program folder: the data unit, the result parser and, with the toolchain, a full build."""

import os
import pathlib
import subprocess

import dace
import numpy
import pytest

from alloy.softhiergen import program, storage


@dace.program
def scale(a: dace.float32, x: dace.float16[512], y: dace.float16[512]) -> None:
    y[:] = a * x


def test_dump_round_trip_restores_float16_arrays(tmp_path: pathlib.Path) -> None:
    """main.c dumps 32-bit words; the parser reassembles an odd-length float16 array from them."""
    values = numpy.arange(5, dtype=numpy.float16)
    raw = numpy.frombuffer(values.tobytes() + b"\0\0", dtype=numpy.uint32).tolist()
    (tmp_path / "meta.json").write_text('[{"name": "v", "dtype": "<f2", "shape": [5]}]')
    lines = [f"DSH v {w:x}" for w in raw] + ["DSH-CYCLES 77"]
    (tmp_path / "gvsoc.out").write_text("\n".join(lines))
    arrays, cycles = program.read_results(tmp_path)
    numpy.testing.assert_array_equal(arrays["v"], values)
    assert cycles == 77


def test_scalar_argument_is_a_constant_of_the_data_unit() -> None:
    """A scalar argument is baked as a C constant (exact hex float); arrays go to .hbm."""
    sdfg = scale.to_sdfg(simplify=True)
    source, meta = program.main_unit(sdfg, {"a": numpy.float32(1.5), "x": numpy.ones(512, numpy.float16)})
    assert "const float a = 0x1.8000000000000p+0f;" in source
    assert '__attribute__((section(".hbm"), aligned(64))) _Float16 x[512] = {0x1.0000000000000p+0f, ' in source
    assert [entry["name"] for entry in meta] == ["x", "y"]
    assert '_Static_assert(ARCH_NUM_CLUSTER == 4, "' in source


def test_float64_scalar_argument_keeps_double_precision() -> None:
    """A double literal takes no ``f`` suffix, which would round it to float."""
    sdfg = dace.SDFG("double")
    sdfg.add_scalar("a", dace.float64)
    source, _ = program.main_unit(sdfg, {"a": numpy.float64(0.1)})
    assert "const double a = 0x1.999999999999ap-4;" in source


def test_bool_and_infinite_constants_are_c_literals() -> None:
    """SDFG constants print as C (``true``, ``INFINITY``), not as Python's ``True`` and ``inf``."""
    from alloy.softhiergen.gate.programs import vadd

    sdfg = vadd.to_sdfg(simplify=True)
    sdfg.add_constant("flag", True)
    sdfg.add_constant("big", numpy.inf)
    code = program.generate(sdfg)
    assert "constexpr bool flag = true;" in code
    assert "constexpr double big = INFINITY;" in code


def test_allreduce_calls_the_runtime_with_a_per_cluster_scratch() -> None:
    """The in-kernel Allreduce becomes one dsh_allreduce over TCDM, scratch one slot per cluster."""
    from alloy.softhiergen.gate.programs import allreduce

    code = program.generate(allreduce())
    assert "static float __scratch[4096]" in code
    assert "dsh_allreduce(reduced, mine, __scratch, 1024, DSH_F32, DSH_SUM);" in code


TOOLCHAIN = os.environ.get("SOFTHIER_TOOLCHAIN")


@pytest.mark.softhier_sdk
def test_generated_gemm_compiles_and_links(tmp_path: pathlib.Path) -> None:
    """The RedMulE GEMM folder builds with the SDK flags, start code and linker script."""
    from alloy.softhiergen.gate.programs import gemm

    sdfg = gemm.to_sdfg(simplify=True)
    program.write_folder(tmp_path, sdfg, program.generate(sdfg), {})
    env = os.environ | {"PATH": f"{TOOLCHAIN}:{os.environ['PATH']}"}
    done = subprocess.run(
        [str(tmp_path / "build_run.sh"), "build"], check=False, env=env, capture_output=True, text=True
    )
    assert done.returncode == 0, done.stderr[-2000:]
    assert (tmp_path / "softhier.elf").exists()


@pytest.mark.softhier_sdk
def test_vector_instructions_stay_in_the_spatz_helpers(tmp_path: pathlib.Path) -> None:
    """Only core 0 has Spatz: every vector instruction of the ELF lies in a dsh_rvv_* function, which the compute core
    alone calls; inlined into a guarded caller, GCC could hoist one above the guard."""
    from alloy.softhiergen.gate.programs import vsum

    sdfg = vsum.to_sdfg(simplify=True)
    program.write_folder(tmp_path, sdfg, program.generate(sdfg), {})
    env = os.environ | {"PATH": f"{TOOLCHAIN}:{os.environ['PATH']}"}
    done = subprocess.run(
        [str(tmp_path / "build_run.sh"), "build"], check=False, env=env, capture_output=True, text=True
    )
    assert done.returncode == 0, done.stderr[-2000:]
    listing = subprocess.run(
        ["riscv32-unknown-elf-objdump", "-d", str(tmp_path / "softhier.elf")],
        check=True,
        env=env,
        capture_output=True,
        text=True,
    ).stdout
    function, leaks = "", []
    for line in listing.splitlines():
        if line.endswith(">:"):
            function = line.split("<", 1)[1][:-2]
        elif line.count("\t") >= 2 and line.split("\t")[2].startswith("v") and not function.startswith("dsh_rvv_"):
            leaks.append(f"{function}: {line.strip()}")
    assert not leaks, "\n".join(leaks[:20])


def test_hbm_arrays_past_the_west_channels_are_refused(tmp_path: pathlib.Path) -> None:
    """The linker puts every HBM array on the west channels (2 x 64 MiB); a larger program would run off them."""
    sdfg = dace.SDFG("big")
    sdfg.add_array("x", (2 * 64 * 2**20 // 4 + 1,), dace.float32)
    sdfg.arrays["x"].storage = storage.HBM
    with pytest.raises(ValueError, match="west HBM channels"):
        program.write_folder(tmp_path, sdfg, "", {})


def test_rooted_collective_reads_its_root_from_a_register_scalar() -> None:
    """The root is a scalar every core computes: it stays in registers, and the call takes it by value."""
    from alloy.softhiergen.gate.programs import collective_cases

    bcast = next(case for case in collective_cases() if case.name == "bcast")
    code = program.generate(bcast.sdfg())
    assert "dsh_bcast(y, x, 4096, r);" in code
    assert "__dsh_l1_0_r" not in code
