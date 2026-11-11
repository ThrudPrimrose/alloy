# Copyright 2026 ETH Zurich and the Alloy authors.
import pytest

from alloy import machine
from alloy.backend.candidates import flips, one_factor_at_a_time, vector_options
from helpers import MATRIX, gcc_only, outlined, scope_with


def test_a_vector_math_library_is_tried_only_where_libm_is_called():
    program = outlined()
    libm_scope = scope_with(program, libm=True, reduction=False)
    reduction_scope = scope_with(program, libm=False, reduction=True)

    assert any(c.veclib != "none" for c in one_factor_at_a_time(MATRIX, libm_scope))
    assert all(c.veclib == "none" for c in one_factor_at_a_time(MATRIX, reduction_scope))


def test_reassociation_is_tried_only_where_something_reduces():
    program = outlined()
    libm_scope = scope_with(program, libm=True, reduction=False)
    reduction_scope = scope_with(program, libm=False, reduction=True)

    assert any(c.fp_level == "reassoc" for c in one_factor_at_a_time(MATRIX, reduction_scope))
    assert all(c.fp_level != "reassoc" for c in one_factor_at_a_time(MATRIX, libm_scope))


def test_the_candidates_are_exactly_what_the_matrix_lists(tmp_path, monkeypatch):
    monkeypatch.setattr(machine, "cpu_flags", lambda: frozenset({"sse2", "avx", "avx2", "fma"}))  # zen3
    matrix = gcc_only(tmp_path)
    scope = scope_with(outlined(), libm=False, reduction=True)

    sut = one_factor_at_a_time(matrix, scope)

    notes = ["default", "heap_ptr_restrict=none", "const_scalar_abi=by_value", "scalar_decl=late"]
    notes += ["fp contract", "fp reciprocal", "fp noerrno", "fp reassoc", "isa avx2", "tail scalar_remainder", "serial"]
    assert {c.compiler for c in sut} == {"gcc"}
    assert {c.resolved(matrix)[0] for c in sut} == {"strict", "contract", "reciprocal", "noerrno", "reassoc"}
    assert [(c.language, c.note) for c in sut] == [(lang, note) for lang in ("c", "cpp") for note in notes]


def test_fast_math_is_tried_only_when_inputs_are_declared_finite(tmp_path):
    matrix = gcc_only(tmp_path)
    scope = scope_with(outlined(), libm=False, reduction=True)

    sut = one_factor_at_a_time(matrix, scope, finite_inputs=True)

    assert "fast" in {c.resolved(matrix)[0] for c in sut}


def test_a_level_that_does_not_need_finite_inputs_never_assumes_them():
    finite_only = ("-ffast-math", "-ffinite-math-only", "-fp-model=fast", "-fast")
    open_levels = {name for name, level in MATRIX.fp_levels.items() if level.needs != "finite_inputs"}
    spellings = [
        (compiler, level, flags)
        for compiler, comp in MATRIX.compilers.items()
        for level, flags in comp.fp.items()
        if level in open_levels
    ]
    spellings += [
        (compiler, lib, flags)
        for compiler, comp in MATRIX.compilers.items()
        for lib, flags in comp.veclib.items()
        if MATRIX.veclibs[lib].fp_level in open_levels
    ]

    assert [(c, o) for c, o, flags in spellings if any(f.startswith(finite_only) for f in flags)] == []


def test_gccs_vector_math_is_tried_only_when_inputs_are_declared_finite(tmp_path):
    matrix = gcc_only(tmp_path)
    scope = scope_with(outlined(), libm=True, reduction=False)

    undeclared = one_factor_at_a_time(matrix, scope)
    declared = one_factor_at_a_time(matrix, scope, finite_inputs=True)

    assert all(c.veclib == "none" for c in undeclared)
    assert any(c.veclib == "libmvec_fast" for c in declared)


def test_an_isa_is_tried_only_where_the_host_runs_it_and_the_compiler_spells_it():
    scope = scope_with(outlined(), libm=False, reduction=True)
    host = ("avx2", "avx512")

    def tried(compiler: str, isas: tuple[str, ...]) -> set[str]:
        out = flips(MATRIX, scope, "c", compiler, finite_inputs=False, isas=isas)
        return {c.isa for c in out if c.isa}

    assert tried("gcc", host) == {"avx2", "avx512"}
    assert tried("nvhpc", host) == {"avx2"}
    assert tried("gcc", ()) == set()


def test_an_isa_candidate_is_built_with_the_compilers_spelling_of_it():
    scope = scope_with(outlined(), libm=False, reduction=True)
    out = flips(MATRIX, scope, "c", "clang", finite_inputs=False, isas=("sve",))
    (sve,) = [c for c in out if c.isa == "sve" and not c.tail]

    assert sve.flags(MATRIX)[-4:] == (
        "-mllvm",
        "-scalable-vectorization=preferred",
        "-mllvm",
        "-sve-prefer-fixed-over-scalable-if-equal=false",
    )
    assert sve.config_name(MATRIX).endswith("_sve")
    assert sve.variant_key(MATRIX) == next(c for c in out if not c.isa and c.note == "default").variant_key(MATRIX)


def tails(compiler: str, isas: tuple[str, ...]) -> set[tuple[str, str]]:
    scope = scope_with(outlined(), libm=False, reduction=True)
    out = flips(MATRIX, scope, "c", compiler, finite_inputs=False, isas=isas)
    return {(c.tail, c.isa) for c in out if c.tail}


def test_a_masked_tail_is_tried_only_on_a_host_isa_with_masks():
    sut = tails("gcc", ("avx2", "avx512"))

    assert sut == {
        ("scalar_remainder", ""),
        ("masked_remainder", "avx512"),
        ("full_mask", "avx512"),
    }


def test_clang_has_no_masked_epilogue_and_explicit_sve_loops_need_an_sve_host():
    assert ("masked_remainder", "avx512") not in tails("clang", ("avx512",))
    assert ("full_mask", "avx512") in tails("clang", ("avx512",))
    assert ("sve_intrinsics", "sve") in tails("gcc", ("sve",))
    assert not any(tail == "sve_intrinsics" for tail, _ in tails("gcc", ("avx512",)))


def test_a_tail_is_built_with_the_compilers_spelling_and_names_its_config():
    scope = scope_with(outlined(), libm=False, reduction=True)
    out = flips(MATRIX, scope, "c", "gcc", finite_inputs=False, isas=("avx512",))
    (full,) = [c for c in out if c.tail == "full_mask"]
    (sve,) = [
        c for c in flips(MATRIX, scope, "c", "gcc", finite_inputs=False, isas=("sve",)) if c.tail == "sve_intrinsics"
    ]

    assert full.flags(MATRIX)[-1] == "--param=vect-partial-vector-usage=2"
    assert full.config_name(MATRIX).endswith("_avx512_full_mask")
    assert full.variant_key(MATRIX) == out[0].variant_key(MATRIX), "a flag tail renders the default source"
    assert sve.variant_key(MATRIX) != out[0].variant_key(MATRIX), "explicit SVE loops are a source of their own"


def test_a_scope_that_may_reach_the_reciprocal_level_also_tries_it_without_a_region():
    scope = scope_with(outlined(), libm=True, reduction=False)

    sut = flips(MATRIX, scope, "c", "gcc", finite_inputs=False)

    assert [c.fp_level for c in sut if c.serial] == ["", "reciprocal"]
    assert sut[-1].name(MATRIX) == "c_gcc_reciprocal_default_none_serial"


@pytest.mark.parametrize(
    "compiler, runtime, serial",
    [
        ("gcc", ("-fopenmp",), ("-fopenmp-simd",)),
        ("clang", ("-fopenmp=libomp",), ("-fopenmp-simd",)),
        ("icx", ("-fiopenmp",), ("-fopenmp-simd",)),
        ("nvhpc", ("-mp",), ()),
    ],
)
def test_the_sweep_tries_one_serial_build_of_the_default_source_without_the_openmp_runtime(compiler, runtime, serial):
    scope = scope_with(outlined(), libm=False, reduction=True)
    default, *rest = flips(MATRIX, scope, "c", compiler, finite_inputs=False)

    (sut,) = [c for c in rest if c.serial]

    assert sut.variant_key(MATRIX) == default.variant_key(MATRIX), "only the build changes, so it is one factor"
    assert set(sut.flags(MATRIX)) == (set(default.flags(MATRIX)) - set(runtime)) | set(serial)
    assert sut.name(MATRIX).endswith("_serial") and sut.config_name(MATRIX).endswith("_serial")
    assert rest[-1] == sut, "every OpenMP build precedes it in sweep order"


def test_each_isa_and_tail_says_which_compilers_build_it_or_why_none_can():
    zen4 = frozenset({"avx2", "avx512f"})

    sut = {(o.isa, o.tail): o for o in vector_options(MATRIX, zen4)}

    assert sut[("avx2", "full_mask")].reason == "avx2 has no masks"
    assert sut[("sve", "full_mask")].reason == "host lacks sve"
    assert sut[("avx512", "full_mask")].reason == "" and "gcc" in sut[("avx512", "full_mask")].compilers
    assert "clang" not in sut[("avx512", "masked_remainder")].compilers
