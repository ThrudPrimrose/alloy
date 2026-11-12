# Copyright 2026 ETH Zurich and the Alloy authors.
"""The ISA lookup table: pinned rows in both directions, the abstract op set, agreement with the
matrix's ISA widths, every spelling verified against the clang resource headers, and the CLI."""

import functools
import pathlib
import re
import subprocess
import sys

import pytest

from alloy.isa import OPS, load, lookup, reverse
from alloy.isa.table import ALIASES, ALL_DTYPES, DEFAULT_PATH, DTYPES
from helpers import MATRIX

TABLE = load()


#: Pinned rows: (isa, op, dtype) -> (intrinsic or first recipe step, the pinned fact).
PINNED = {
    ("avx2", "fma", "f64"): ("_mm256_fmadd_pd", "a[j]*b[j] + c[j]"),  # accumulator last
    ("avx2", "fma", "f32"): ("_mm256_fmadd_ps", "a[j]*b[j] + c[j]"),
    ("avx512", "fma", "f64"): ("_mm512_fmadd_pd", "a[j]*b[j] + c[j]"),
    ("neon", "fma", "f64"): ("vfmaq_f64", "a[j] + b[j]*c[j]"),  # accumulator first: the trap
    ("neon", "fma", "f32"): ("vfmaq_f32", "a[j] + b[j]*c[j]"),
    ("sve", "fma", "f64"): ("svmla_f64_x", "add[j] + m1[j]*m2[j]"),  # accumulator first too
    ("sve", "fma", "f32"): ("svmla_f32_x", "add[j] + m1[j]*m2[j]"),
    ("avx512", "gen_mask", "f64"): ("_mm512_cmplt_epu64_mask", "iota[j] < n"),
    ("avx512", "gen_mask", "f32"): ("_mm512_cmplt_epu32_mask", "iota[j] < n"),
    ("sve", "gen_mask", "f64"): ("svwhilelt_b64_s64", "i + j < N"),
    ("sve", "gen_mask", "f32"): ("svwhilelt_b32_s64", "i + j < N"),
    ("neon", "reduce_add", "f32"): ("vaddvq_f32", "sum of the 4 lanes"),
    ("avx512", "reduce_add", "f64"): ("_mm512_reduce_add_pd", "sum of the 8 lanes"),
    ("sve", "reduce_add", "f64"): ("svaddv_f64", "sum of the active lanes"),
    ("avx512", "load", "f64"): ("_mm512_loadu_pd", "v[j] = p[j]"),
    ("neon", "load", "f64"): ("vld1q_f64", "v[j] = p[j]"),
    ("sve", "load", "f64"): ("svld1_f64", "v[j] = p[j]"),
}


@pytest.mark.parametrize(("isa", "op", "dtype"), PINNED)
def test_pinned_rows(isa, op, dtype):
    spelling, fact = PINNED[(isa, op, dtype)]
    entry = lookup(isa, op, dtype, TABLE)

    assert spelling in (entry.intrinsic, *entry.recipe)
    assert fact in entry.semantics


def test_the_abstract_isa_covers_the_core_math():
    for name in ("load", "store", "broadcast", "add", "sub", "mul", "div", "fma", "reduce_add"):
        assert name in OPS
    kinds = {"memory", "elementwise", "bitwise", "shift", "logical", "reduction", "mask", "constant", "transcendental"}
    assert {op.kind for op in OPS.values()} <= kinds
    assert OPS["reduce_add"].result == "scalar"  # full vector width to a single element
    assert OPS["gen_mask"].result == "mask"


def test_the_matrix_and_the_table_agree_on_isa_widths():
    for name in TABLE.isas:
        assert TABLE.isa(name).vector_bytes == MATRIX.isas[name].vector_bytes


@pytest.mark.parametrize("isa", ["avx2", "neon"])
def test_a_maskless_isa_has_no_gen_mask(isa):
    with pytest.raises(KeyError, match="no predication"):
        lookup(isa, "gen_mask", "f64", TABLE)


def test_unknown_names_raise_with_the_choices():
    with pytest.raises(KeyError, match="unknown ISA"):
        lookup("mmx", "add", "f64", TABLE)
    with pytest.raises(KeyError, match="unknown op"):
        lookup("avx2", "atan2", "f64", TABLE)
    with pytest.raises(KeyError, match="unknown dtype"):
        lookup("avx2", "add", "bf16", TABLE)


def test_an_isa_alias_resolves_to_its_base_isa():
    entry = lookup("avx512_256", "add", "f64", TABLE)

    assert entry is lookup("avx512", "add", "f64", TABLE)
    assert ALIASES["avx512_256"] == "avx512"


def test_reverse_maps_an_intrinsic_back_to_the_math():
    (hit,) = reverse("_mm256_add_pd", TABLE)

    assert (hit.isa, hit.op, hit.dtype) == ("avx2", "add", "f64")
    assert hit.via == "intrinsic"


def test_reverse_maps_a_mnemonic_to_every_isa_that_uses_it():
    hits = reverse("vaddpd", TABLE)

    assert {(h.isa, h.dtype, h.op) for h in hits if h.via == "mnemonic"} == {
        ("avx2", "f64", "add"),
        ("avx512", "f64", "add"),
    }


def test_reverse_normalizes_an_fma_family_form():
    hits = reverse("vfmadd231pd", TABLE)

    assert {(h.isa, h.dtype, h.op) for h in hits} == {("avx2", "f64", "fma"), ("avx512", "f64", "fma")}


def test_reverse_strips_an_evex_dot_suffix():
    assert {h.isa for h in reverse("vaddpd.z", TABLE)} == {"avx2", "avx512"}


@pytest.mark.parametrize(
    ("name", "isa", "op", "dtype"),
    [
        ("fmla", "neon", "fma", "f64"),
        ("fmla", "sve", "fma", "f32"),
        ("ld1d", "sve", "load", "f64"),
        ("faddv", "sve", "reduce_add", "f64"),
        ("svaddv_f32", "sve", "reduce_add", "f32"),
        ("_mm512_maskz_loadu_pd", "avx512", "load", "f64"),
    ],
)
def test_reverse_reads_disassembly_spellings(name, isa, op, dtype):
    assert (isa, op, dtype) in {(h.isa, h.op, h.dtype) for h in reverse(name, TABLE)}


@pytest.mark.parametrize("name", ["svadd_f64_m", "svadd_f64_z", "_mm512_maskz_add_pd", "_mm512_mask3_fmadd_pd"])
def test_reverse_of_a_policy_variant_is_not_duplicated(name):
    hits = [(h.isa, h.op, h.dtype) for h in reverse(name, TABLE)]

    assert len(hits) == len(set(hits)) == 1


@pytest.mark.parametrize("dtype", ["i64", "i32"])
def test_sve_integer_mod_is_zero_for_a_zero_divisor_like_the_other_targets(dtype):
    code = " ".join(TABLE.entry("sve", "mod", dtype).code)

    assert f"svcmpeq_n_s{dtype[1:]}(pg, b, 0)" in code


@pytest.mark.parametrize(("isa", "dtype", "op"), [("avx512", "f32", "abs"), ("avx512", "f32", "neg")])
def test_a_note_names_intrinsics_of_its_own_lane_type(isa, dtype, op):
    assert "_pd" not in TABLE.entry(isa, op, dtype).note


@pytest.mark.parametrize("dtype", ["f64", "f32"])
def test_the_avx2_max_note_describes_max(dtype):
    assert "min(" not in TABLE.entry("avx2", "max", dtype).note


def test_the_avx2_f16_note_matches_its_256_bit_code():
    note = TABLE.entry("avx2", "add", "f16").note

    assert "_mm_loadu_si128" not in note and "-mf16c" in note


def test_the_kernel_page_does_not_claim_strict_is_never_more_accurate():
    from alloy.isa.render import render_kernels

    assert "not lower than" not in render_kernels()


def test_reverse_of_an_unknown_name_is_empty():
    assert reverse("_mm512_wibbel_pd", TABLE) == ()


def test_every_intrinsic_reverses_to_its_own_row():
    for isa_name, isa in TABLE.isas.items():
        for dtype in ALL_DTYPES:
            for op, entry in isa.entries(dtype).items():
                if not entry.intrinsic:
                    continue
                assert (isa_name, op, dtype) in {(h.isa, h.op, h.dtype) for h in reverse(entry.intrinsic, TABLE)}


def test_every_recipe_step_reverses_to_its_own_row():
    for isa_name, isa in TABLE.isas.items():
        for dtype in ALL_DTYPES:
            for op, entry in isa.entries(dtype).items():
                if not entry.recipe:
                    continue
                for step in entry.recipe:
                    if not IDENTIFIER.fullmatch(step):
                        continue  # pseudo step of a fallback story, not a spelling
                    assert (isa_name, op, dtype) in {(h.isa, h.op, h.dtype) for h in reverse(step, TABLE)}


@functools.lru_cache(maxsize=1)
def clang_include() -> pathlib.Path | None:
    """The clang resource include dir (the headers the spellings were verified against), or None. Only a clang built
    for AArch64 too generates arm_neon.h and arm_sve.h, so one without them cannot check the table's ARM spellings."""
    for command in ("clang-22", "clang-21", "clang"):
        try:
            run = subprocess.run([command, "-print-resource-dir"], capture_output=True, text=True, check=True)
        except (OSError, subprocess.CalledProcessError):
            continue
        if ((include := pathlib.Path(run.stdout.strip()) / "include") / "arm_sve.h").is_file():
            return include
    for include in sorted(pathlib.Path("/usr/lib/clang").glob("*/include")):
        if (include / "arm_sve.h").is_file():
            return include
    return None


@functools.lru_cache(maxsize=1)
def header_blob() -> str:
    include = clang_include()
    assert include is not None, "no clang resource headers on this host"
    return "\n".join(path.read_text(errors="ignore") for path in include.glob("*.h"))


IDENTIFIER = re.compile(r"^[A-Za-z_]\w*$")


@pytest.mark.skipif(clang_include() is None, reason="no clang resource headers on this host")
def test_every_spelling_exists_in_the_clang_headers():
    blob = header_blob()
    names = [
        name
        for isa in TABLE.isas.values()
        for dtype in ALL_DTYPES
        for entry in isa.entries(dtype).values()
        # recipes may carry pseudo steps (the fallback stories: "no vector remainder: ..."),
        # which are not spellings; identifier-shaped ones are checked
        for name in [entry.intrinsic, *entry.recipe]
        if name and IDENTIFIER.fullmatch(name)
    ]
    missing = [name for name in dict.fromkeys(names) if not re.search(rf"\b{re.escape(name)}\s*\(", blob)]
    assert not missing


def test_an_integer_op_is_refused_on_a_float_dtype():
    with pytest.raises(KeyError, match="integer op"):
        lookup("avx512", "and", "f64", TABLE)


def test_a_float_op_is_refused_on_an_integer_dtype():
    with pytest.raises(KeyError, match="float rows are not valid"):
        lookup("avx512", "exp", "i64", TABLE)


def test_f16_is_native_where_the_hardware_has_it_and_a_recipe_elsewhere():
    assert lookup("avx512", "fma", "f16", TABLE).intrinsic == "_mm512_fmadd_ph"
    assert lookup("neon", "add", "f16", TABLE).intrinsic == "vaddq_f16"
    assert lookup("sve", "add", "f16", TABLE).intrinsic == "svadd_f16_x"
    fallback = lookup("avx2", "fma", "f16", TABLE)
    assert fallback.recipe == ("_mm256_cvtph_ps", "_mm256_fmadd_ps", "_mm256_cvtps_ph")
    # bitwise f16 ops work directly on the storage even on AVX2
    assert lookup("avx2", "abs", "f16", TABLE).recipe == ("_mm256_set1_epi16", "_mm256_and_si256")


def test_embedded_broadcast_marks_only_avx512():
    assert TABLE.isas["avx512"].embedded_broadcast
    assert not any(TABLE.isas[name].embedded_broadcast for name in ("avx2", "neon", "sve"))


@pytest.mark.parametrize(
    ("name", "isa", "dtype", "op"),
    [
        ("vblendvpd", "avx2", "f64", "select"),
        ("_mm512_mask_blend_pd", "avx512", "f64", "select"),
        ("vbslq_f64", "neon", "f64", "select"),
        ("svsel_f64", "sve", "f64", "select"),
        ("svlsl_u64_x", "sve", "i64", "shl"),
        ("vandq_s64", "neon", "i64", "and"),
        ("vandq_u64", "neon", "i64", "and"),
        ("svorr_u32_m", "sve", "i32", "or"),
        ("vshlq_u32", "neon", "i32", "shl"),
        ("_mm512_and_si512", "avx512", "i32", "and"),
        ("svld1_gather_s64index_f64", "sve", "f64", "gather"),
        ("vaddq_f16", "neon", "f16", "add"),
        ("_mm512_add_ph", "avx512", "f16", "add"),
    ],
)
def test_reverse_reads_the_new_spellings(name, isa, dtype, op):
    assert (isa, dtype, op) in {(h.isa, h.dtype, h.op) for h in reverse(name, TABLE)}


TRANSCENDENTALS = ("exp", "sin", "cos")


@pytest.mark.parametrize("op", TRANSCENDENTALS)
@pytest.mark.parametrize("dtype", ["f64", "f32"])
@pytest.mark.parametrize("isa", ["avx2", "avx512", "neon", "sve"])
def test_a_transcendental_has_no_native_intrinsic_but_lists_tiers(isa, op, dtype):
    entry = lookup(isa, op, dtype, TABLE)

    assert not entry.intrinsic and not entry.recipe and not entry.mnemonic
    assert entry.approximations
    assert entry.libraries


def test_the_taylor_ladder_improves_and_minimax_beats_taylor():
    ulp = {key: TABLE.approx[key].error_ulp for key in TABLE.approx}

    assert ulp["sin-taylor7"] > ulp["sin-taylor9"] > ulp["sin-taylor11"] > ulp["sin-quad-cheb9"]
    assert ulp["sin-quad-cheb9"] > ulp["sin-quad-cheb13"]
    assert ulp["cos-taylor6"] > ulp["cos-taylor8"] > ulp["cos-taylor10"]
    assert ulp["exp-taylor9"] > ulp["exp-cheb9"] > ulp["exp-cheb11"]


@pytest.mark.parametrize(
    ("call", "isa", "op", "dtype"),
    [
        ("_ZGVdN4v_sin", "avx2", "sin", "f64"),
        ("_ZGVeN16v_expf", "avx512", "exp", "f32"),
        ("__svml_cos4", "avx2", "cos", "f64"),
        ("__svml_exp8", "avx512", "exp", "f64"),
        ("Sleef_sind2_u10", "neon", "sin", "f64"),
        ("Sleef_sinf16_u10avx512f", "avx512", "sin", "f32"),
    ],
)
def test_library_calls_reverse_to_the_math(call, isa, op, dtype):
    (hit,) = (h for h in reverse(call, TABLE) if (h.isa, h.dtype) == (isa, dtype))

    assert (hit.op, hit.via) == (op, "library")


@functools.lru_cache(maxsize=1)
def libmvec_symbols() -> frozenset[str] | None:
    """The exported vector math symbols of the host's libmvec, or None when there is none."""
    for candidate in ("/lib/x86_64-linux-gnu/libmvec.so.1", "/usr/lib/libmvec.so.1"):
        if pathlib.Path(candidate).is_file():
            run = subprocess.run(["nm", "-D", candidate], capture_output=True, text=True, check=True)
            return frozenset(re.sub(r"@@.*$", "", line.split()[-1]) for line in run.stdout.splitlines())
    return None


@pytest.mark.skipif(libmvec_symbols() is None, reason="no libmvec on this host")
def test_the_committed_libmvec_names_exist_in_the_host_library():
    for isa in ("avx2", "avx512"):
        for dtype in DTYPES:
            for op in TRANSCENDENTALS:
                call = TABLE.isas[isa].entries(dtype)[op].libraries.get("libmvec")
                symbols = libmvec_symbols()
                assert symbols is not None
                assert call in symbols, f"{call} not in this host's libmvec"


def cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "alloy.isa", *args], capture_output=True, text=True, check=False)


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        (("lookup", "avx512", "fma", "f64"), ("_mm512_fmadd_pd", "a[j]*b[j] + c[j]")),
        (("lookup", "avx2", "sin", "f64"), ("tier sin-quad-cheb13: abs error", "libmvec: _ZGVdN4v_sin")),
        (("reverse", "svaddv_f32"), ("reduce_add on sve/f32",)),
        (("reverse", "_ZGVdN4v_sin"), ("sin on avx2/f64", "library")),
        (("ops",), ("load", "gather", "mod", "select", "sin")),
        (("isas",), ("avx2", "avx512", "neon", "sve")),
        (("schedule", "neon"), ("scalar_remainder", "unsupported")),  # no predication: the gen_mask line
        (("assist", "vscalefpd"), ("_mm512_scalef_pd", "helps exp")),
        (("tiers", "sin"), ("sin-taylor7: 4 steps", "sin-quad-cheb13", "t = mul(x, x)")),
        (("tiers", "log"), ("log-taylor5: 3 steps", "log-cheb13", "t = mul(x, x)")),
        (("tiers", "ln"), ("log-cheb13",)),
    ],
)
def test_the_cli_answers(args, expected):
    run = cli(*args)

    assert run.returncode == 0
    for text in expected:
        assert text in run.stdout


def test_the_cli_refuses_a_maskless_gen_mask():
    run = cli("lookup", "avx2", "gen_mask", "f64")

    assert run.returncode == 2
    assert "no predication" in run.stderr


def test_gen_mask_is_not_required_for_f16():
    with pytest.raises(KeyError, match="unsupported"):
        lookup("avx512", "gen_mask", "f16", TABLE)


def test_the_skill_pages_render_from_the_table(tmp_path):
    from alloy.isa.render import render

    written = render(TABLE, tmp_path)
    names = {path.name for path in written}

    assert names == {"index.md", "kernels.md", "transcendentals.md", "avx2.md", "avx512.md", "neon.md", "sve.md"}
    index = (tmp_path / "index.md").read_text()
    for op in ("load", "gather", "sin"):
        assert f"`{op}`" in index
    avx512 = (tmp_path / "avx512.md").read_text()
    assert "_mm512_fmadd_pd" in avx512
    assert "embedded broadcast" in avx512
    assert "| `and` | `_mm512_and_si512` | `vpandd` |" in avx512
    trans = (tmp_path / "transcendentals.md").read_text()
    assert "sin-quad-cheb13" in trans
    assert "_ZGVdN4v_sin" in trans


def test_the_assists_reverse_by_name_and_mnemonic():
    (hit,) = TABLE.assist("svexpa_f64")

    assert hit.isa == "sve" and hit.assist.helps == "exp"

    by_mnemonic = TABLE.assist("fexpa")
    assert [h.assist.name for h in by_mnemonic] == ["svexpa_f64"]
    assert {h.isa for h in TABLE.assist("frecps")} == {"sve", "neon"}


def test_every_assist_spelling_exists_in_the_clang_headers():
    include = clang_include()
    if include is None:
        pytest.skip("no clang resource headers on this host")
    blob = header_blob()
    missing = [
        assist.name
        for isa in TABLE.isas.values()
        for assist in isa.assists
        if not re.search(rf"\b{re.escape(assist.name)}\s*\(", blob)
    ]
    assert not missing


def test_masked_variant_names_reverse_without_their_notes():
    """The f16 masked variants carry a cast note after the name; the index must key the bare name."""
    (hit,) = reverse("_mm512_maskz_loadu_epi16", TABLE)

    assert (hit.isa, hit.dtype, hit.op, hit.via) == ("avx512", "f16", "load", "masked")


def test_masked_variant_names_exist_in_the_clang_headers():
    include = clang_include()
    if include is None:
        pytest.skip("no clang resource headers on this host")
    blob = header_blob()
    missing = []
    for isa in TABLE.isas.values():
        for dtype in ALL_DTYPES:
            for entry in isa.entries(dtype).values():
                if not entry.masked:
                    continue
                name = entry.masked.split("(", 1)[0].split(maxsplit=1)[0]
                if not re.search(rf"\b{re.escape(name)}\s*\(", blob):
                    missing.append(name)
    assert not missing


@pytest.mark.parametrize(
    "name, isa, op, dtype",
    [
        ("vfnmadd231pd", "avx2", "mod", "f64"),  # one step of a composite
        ("vfmadd231ph", "avx512", "fma", "f16"),
        ("vfmadd213sd", "avx2", "fma", "f64"),
        ("VADDPD", "avx2", "add", "f64"),
        ("vpsrlvq", "avx512", "shr", "i64"),
        ("kandb", "avx512", "land", "i64"),
        ("kandw", "avx512", "land", "i32"),
        ("_mm256_storeu_pd", "avx2", "scatter", "f64"),  # cited in a prose recipe step
        ("vld1q_lane_f64", "neon", "gather", "f64"),
        ("_mm512_castsi512_ph", "avx512", "load", "f16"),  # cited in a masked note
    ],
)
def test_reverse_reads_what_a_disassembly_or_a_recipe_spells(name, isa, op, dtype):
    assert (isa, op, dtype) in {(hit.isa, hit.op, hit.dtype) for hit in TABLE.reverse(name)}


@pytest.mark.parametrize("name", ["", "   "])
def test_an_empty_name_matches_nothing(name):
    assert TABLE.reverse(name) == ()
    assert TABLE.assist(name) == ()


def test_fmod_truncates_on_every_isa_with_a_float_recipe():
    """fmod needs a toward-zero quotient and the final a - q*b; the nearest-rounding step is remainder()."""
    assert TABLE.entry("neon", "mod", "f64").recipe == ("vdivq_f64", "vrndq_f64", "vfmsq_f64")
    assert TABLE.entry("sve", "mod", "f32").recipe == ("svdiv_f32_x", "svrintz_f32_x", "svmls_f32_x")


def test_a_masked_fma_takes_the_four_arguments_the_header_declares():
    masked = TABLE.entry("avx512", "fma", "f64").masked
    assert masked.count(",") == 3, masked


@pytest.mark.parametrize(
    ("old", "new", "refusal"),
    [
        ("[isa.avx2.i64.shr]", "[isa.avx2.i64.not_shr_at_all]", "lacks ops"),
        ("[isa.avx2.f64.sqrt]", "[isa.avx2.f64.not_sqrt_at_all]", "lacks ops"),
        ('mnemonic = "vaddpd"\n', "", "has no mnemonic"),
        ('intrinsic = "_mm256_add_pd"\n', "", "exactly one of intrinsic, recipe"),
        ('intrinsic = "_mm256_add_pd"\n', 'intrinsic = "_mm256_add_pd"\nrecipe = ["a"]\n', "exactly one"),
        ("error_ulp = 7.066085e+11", "error_ulp = 0.0", "positive error_ulp"),
        (
            'code = ["_mm256_and_pd(v, _mm256_castsi256_pd(_mm256_set1_epi64x(0x7fffffffffffffffLL)))"]\n',
            "",
            "needs code",
        ),
        ('_mm256_fnmadd_pd(q, b, a)"]', '_mm256_add_pd(q, b)"]', "the code never calls"),
    ],
)
def test_the_table_refuses_a_broken_row(tmp_path, old, new, refusal):
    text = DEFAULT_PATH.read_text(encoding="utf-8")
    assert old in text
    broken = tmp_path / "intrinsics.toml"
    broken.write_text(text.replace(old, new, 1), encoding="utf-8")
    with pytest.raises(ValueError, match=refusal):
        load(broken)


@pytest.mark.parametrize(
    ("name", "op", "dtype"),
    [
        ("vmulsd", "mul", "f64"),
        ("vdivss", "div", "f32"),
        ("vmaxsd", "max", "f64"),
        ("vsqrtsd", "sqrt", "f64"),
        ("vaddsd", "add", "f64"),
        ("vmovsd", "load", "f64"),
    ],
)
def test_a_scalar_instruction_reverses_to_its_op_on_one_lane(name, op, dtype):
    sut = TABLE.reverse(name)[0]

    assert (sut.op, sut.dtype, sut.via) == (op, dtype, "scalar")


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        (("reverse", "vmulsd"), ("mul on one lane", "the scalar form of vmulpd")),
        (("reverse", "vzeroupper"), ("no math",)),
        (("reverse", "vucomisd"), ("sets the flags",)),
        (("reverse", "kmovb"), ("moves a mask",)),
    ],
)
def test_the_instructions_of_a_real_loop_get_an_answer(args, expected):
    run = cli(*args)

    assert run.returncode == 0, run.stderr
    for text in expected:
        assert text in run.stdout


@pytest.mark.parametrize(
    ("line", "isa", "absent"),
    [
        ("fmla z0.d, p0/m, z1.d, z2.d", "sve/f64", "neon/"),
        ("fmla v0.2d, v1.2d, v2.2d", "neon/f64", "sve/"),
        ("vaddpd %zmm1, %zmm2, %zmm0", "avx512/f64", "avx2/"),
        ("vaddpd %ymm1, %ymm2, %ymm0", "avx2/f64", "avx512/"),
    ],
)
def test_the_registers_of_a_pasted_line_narrow_its_answer(line, isa, absent):
    run = cli("reverse", line)

    assert isa in run.stdout
    assert absent not in run.stdout


def test_a_pasted_line_is_answered_by_its_mnemonic_and_not_echoed():
    run = cli("reverse", "vaddpd %zmm1, %zmm2, %zmm0")

    assert "%zmm" not in run.stdout


@pytest.mark.parametrize(
    ("word", "meant"), [("sum", "reduce_add"), ("hsum", "reduce_add"), ("blend", "select"), ("tail", "gen_mask")]
)
def test_the_word_an_agent_tries_suggests_the_op_it_means(word, meant):
    run = cli("lookup", "avx2", word, "f64", "--no-verify")

    assert run.returncode == 2
    assert f"did you mean {meant}?" in run.stderr


def test_a_min_or_max_reduction_says_the_table_has_no_row_for_it():
    run = cli("lookup", "avx512", "reduce_max", "f64")

    assert run.returncode == 2
    assert "only reduce_add" in run.stderr
    assert "did you mean" not in run.stderr


@pytest.mark.parametrize("isa", ["avx2", "neon"])
def test_a_tail_on_a_maskless_isa_points_at_its_remainder_loop(isa):
    run = cli("lookup", isa, "gen_mask", "f64")

    assert run.returncode == 2
    assert f"skeleton {isa} scalar_remainder f64" in run.stderr
    assert "integer lanes" not in run.stderr


def test_a_function_without_tiers_points_at_its_kernel():
    run = cli("tiers", "tan")

    assert run.returncode == 2
    assert "kernel" in run.stderr


def test_every_sve_dtype_has_a_tail_predicate():
    sut = TABLE.entry("sve", "gen_mask", "f16")

    assert sut.intrinsic == "svwhilelt_b16_s64"
