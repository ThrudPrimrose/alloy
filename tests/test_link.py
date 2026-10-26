# Copyright 2026 ETH Zurich and the Alloy authors.
import ctypes
import dataclasses
import shutil
import subprocess

import numpy as np
import pytest
from dace.codegen import cpf

from alloy.backend.build import build
from alloy.backend.candidates import Candidate
from alloy.evaluate.link import Best, Linker, built, execution_order
from alloy.frontend import scopes
from alloy.records import dumped_json, validated_json
from helpers import MATRIX, REDUCTIONS, load_program, outlined, scope_with


def test_a_library_of_scope_archives_renders_standalone_and_computes_the_program(tmp_path):
    program = scopes.outline(load_program(f"{REDUCTIONS}:row_sum").to_sdfg(), MATRIX.libm_calls)
    archives = {
        r.symbol: built(build(r, Candidate("c", "gcc"), MATRIX, tmp_path / r.symbol, {})) for r in program.scopes
    }
    sdfg = Linker(program, MATRIX, tmp_path).library_sdfg(archives, frozenset({Candidate("c", "gcc")}))

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


def test_a_library_links_the_vector_library_its_candidates_were_built_against(tmp_path):
    program = outlined()
    archives = {r.symbol: tmp_path / f"lib{r.symbol}.a" for r in program.scopes}
    linker = Linker(program, MATRIX, tmp_path)

    vector = linker.library_sdfg(archives, frozenset({Candidate("c", "gcc", fp_level="fast", veclib="libmvec_fast")}))
    plain = linker.library_sdfg(archives, frozenset({Candidate("c", "gcc")}))

    links = [cpf.render(sdfg, language="c", check_compiles=False).link for sdfg in (vector, plain)]
    assert "-lmvec" in links[0]
    assert "-lmvec" not in links[1]


@pytest.mark.clang
@pytest.mark.sleef
def test_a_sleef_build_binds_its_vector_calls_to_sleef_not_to_glibcs_libmvec(tmp_path):
    program = outlined()
    libm = scope_with(program, libm=True, reduction=False)
    sleef = Candidate("c", "clang", fp_level=MATRIX.veclibs["sleef"].fp_level, veclib="sleef")
    builds = {
        s.symbol: build(s, sleef if s is libm else Candidate("c", "gcc"), MATRIX, tmp_path / s.symbol, {})
        for s in program.scopes
    }
    linker = Linker(program, MATRIX, tmp_path)

    folder = linker.compile(
        {k: built(b) for k, b in builds.items()}, "sleef", frozenset(b.candidate for b in builds.values())
    )

    (library,) = folder.glob(f"build/lib{program.sdfg.name}_*.so")
    dynamic = subprocess.run(["readelf", "-d", str(library)], capture_output=True, text=True, check=True).stdout
    needed = [line.split("[")[1].rstrip("]") for line in dynamic.splitlines() if "(NEEDED)" in line]
    assert any(name.startswith("libsleefgnuabi.so") for name in needed)
    assert not any(name.startswith("libmvec.so") for name in needed)


def test_best_builds_with_make_into_a_library_that_computes_the_program(tmp_path):
    program = scopes.outline(load_program(f"{REDUCTIONS}:row_sum").to_sdfg(), MATRIX.libm_calls)
    winners = {
        r.symbol: build(r, Candidate("c", "gcc", fp_level="fast"), MATRIX, tmp_path / r.symbol, {})
        for r in program.scopes
    }

    sut = Linker(program, MATRIX, tmp_path).write_best(winners)

    best = tmp_path / "best"
    assert "-ffast-math" not in sut.link
    assert dumped_json(validated_json(Best, best / "link.json")) == dumped_json(sut)
    subprocess.run(["make", "-C", str(best)], check=True, capture_output=True)
    rng = np.random.default_rng(0)
    sizes = {"M": 7, "N": 13}
    arrays = {"a": rng.random((7, 13)), "out": np.zeros(7)}
    library = ctypes.CDLL(str(best / f"lib{program.sdfg.name}.so"))
    as_c: dict[str, object] = {k: ctypes.c_int64(v) for k, v in sizes.items()}
    as_c |= {k: v.ctypes.data_as(ctypes.c_void_p) for k, v in arrays.items()}
    getattr(library, program.sdfg.name)(*(as_c[name] for name in sut.arguments))
    np.testing.assert_allclose(arrays["out"], arrays["a"].sum(axis=1), rtol=1e-12)


def test_the_timer_of_a_complex_scope_declares_its_entry_as_dace_does(tmp_path):
    """DaCe spells a complex scope entry with its runtime types (``dace::complex128``); the timer compiles against them."""
    program = scopes.outline(load_program(f"{REDUCTIONS}:row_sum").to_sdfg(), MATRIX.libm_calls)
    scope = dataclasses.replace(
        program.scopes[0],
        symbol="complex_nest",
        abi_order=("G", "s", "N"),
        signature="const dace::complex128* __restrict__ G, dace::complex64 s, int64_t N",
    )
    (tmp_path / "link").mkdir()

    sut = Linker(program, MATRIX, tmp_path).timer(scope)

    assert sut.is_file()


def stub_library(linker: Linker, sdfg, tmp_path, name: str) -> ctypes.CDLL:
    """``sdfg`` rendered by CPF in the program's signature and built into ``lib<name>.so``."""
    rendered = cpf.render(sdfg, language="c", signature=cpf.EntrySignature(["N", "a", "b", "total"]))
    source, library = tmp_path / f"{name}.c", tmp_path / f"lib{name}.so"
    source.write_text(rendered.code)
    gcc = shutil.which("gcc")
    assert gcc is not None
    subprocess.run([gcc, "-O2", "-fPIC", "-shared", str(source), "-o", str(library), *rendered.link], check=True)
    return ctypes.CDLL(str(library))


def test_a_stub_runs_its_scope_and_the_scopes_before_it_and_no_later_one(tmp_path):
    program = outlined()
    linker = Linker(program, MATRIX, tmp_path)
    selection = {r.symbol: build(r, Candidate("c", "gcc"), MATRIX, tmp_path / r.symbol, {}) for r in program.scopes}
    elementwise = next(r.symbol for r in program.scopes if r.calls_libm)
    reduction = next(r.symbol for r in program.scopes if r.has_reduction)
    a = np.random.default_rng(0).random(64)
    total_of_the_program = float(np.sum(np.sin(a) * 2.0))

    for symbol in (elementwise, reduction):
        sut = linker.stub(selection, symbol)

        library = stub_library(linker, sut, tmp_path, f"stub_{symbol}")
        b, total = np.zeros(64), np.array([-1.0])
        pointers = (x.ctypes.data_as(ctypes.c_void_p) for x in (a, b, total))
        getattr(library, sut.name)(ctypes.c_int64(64), *pointers)
        np.testing.assert_allclose(b, np.sin(a) * 2.0, rtol=1e-12)
        if symbol == reduction:
            np.testing.assert_allclose(total[0], total_of_the_program, rtol=1e-12)
        else:
            assert total[0] != total_of_the_program, "the reduction runs after the stubbed scope, so it must not run"


def test_scopes_run_in_program_order():
    program = outlined()

    sut = execution_order(program.sdfg)

    assert sorted(sut) == sorted(r.symbol for r in program.scopes)
    reduction = next(r.symbol for r in program.scopes if r.has_reduction)
    assert sut[-1] == reduction
