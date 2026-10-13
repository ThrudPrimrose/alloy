# Copyright 2026 ETH Zurich and the Alloy authors.
import ctypes
import dataclasses
import shutil
import subprocess

import numpy as np
from dace.codegen import cpf

from alloy.backend.build import build
from alloy.backend.candidates import Candidate
from alloy.evaluate.link import Linker
from alloy.frontend import regions
from helpers import MATRIX, REDUCTIONS, load_program


def test_a_library_of_region_archives_renders_standalone_and_computes_the_program(tmp_path):
    program = regions.outline(load_program(f"{REDUCTIONS}:row_sum").to_sdfg(), MATRIX.libm_calls)
    archives = {
        r.symbol: build(r, Candidate("c", "gcc"), MATRIX, tmp_path / r.symbol, {}).archive for r in program.regions
    }
    sdfg = Linker(program, MATRIX, tmp_path).library_sdfg(archives, frozenset({"gcc"}))

    sut = cpf.render(sdfg, language="c", signature=cpf.EntrySignature(["M", "out", "N", "a"]))

    assert set(sut.link) >= {str(a) for a in archives.values()}
    source, library = tmp_path / "unit.c", tmp_path / "libunit.so"
    source.write_text(sut.code)
    gcc = shutil.which("gcc")
    assert gcc is not None
    subprocess.run([gcc, "-O2", "-fPIC", "-shared", str(source), "-o", str(library), *sut.link], check=True)
    a = np.random.default_rng(0).random((7, 13))
    out = np.zeros(7)
    entry = getattr(ctypes.CDLL(str(library)), sdfg.name)
    entry(ctypes.c_int64(7), out.ctypes.data_as(ctypes.c_void_p), ctypes.c_int64(13), a.ctypes.data_as(ctypes.c_void_p))
    np.testing.assert_allclose(out, a.sum(axis=1), rtol=1e-12)


def test_the_timer_of_a_complex_region_declares_its_entry_as_dace_does(tmp_path):
    """DaCe spells a complex region entry with its runtime types (``dace::complex128``); the timer compiles against them."""
    program = regions.outline(load_program(f"{REDUCTIONS}:row_sum").to_sdfg(), MATRIX.libm_calls)
    region = dataclasses.replace(
        program.regions[0],
        symbol="complex_nest",
        abi_order=("G", "s", "N"),
        signature="const dace::complex128* __restrict__ G, dace::complex64 s, int64_t N",
    )
    (tmp_path / "link").mkdir()

    sut = Linker(program, MATRIX, tmp_path).timer(region)

    assert sut.is_file()
