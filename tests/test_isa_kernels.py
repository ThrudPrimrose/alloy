# Copyright 2026 ETH Zurich and the Alloy authors.
"""Math kernels: every function comes back as intrinsics at three levels. Each kernel is run against a wider libm
at its recorded error, and the gate is shown to fail on a broken kernel."""

import dataclasses
import json
import math
import pathlib
import re
import subprocess

import pytest

from alloy import configuration_matrix
from alloy.isa import load
from alloy.isa.__main__ import main
from alloy.isa.hints import kernel_summary
from alloy.isa.mathcheck import HEADERS, Measured, emulated, inside, judged, measure, validate_kernel
from alloy.isa.mathkernels import (
    LEVELS,
    NO_LIBRARY,
    Kernel,
    Renderer,
    cheapest,
    functions,
    kernel,
    kernels_for,
    ladder,
    libraries,
    needs_ieee,
    render,
    spelled,
)
from alloy.isa.mathtime import time_function
from alloy.isa.validate import c_compiler, c_flags, host_can_run

ALL = [(fn, dtype, k.level) for fn in functions() for dtype in ("f64", "f32") for k in ladder(fn, dtype)]
FUNCTIONS = "sin cos tan exp exp2 exp10 expm1 log log2 log10 log1p pow fmod atan asin acos sinh cosh tanh".split()


def test_the_functions_an_agent_asks_for_all_have_kernels():
    assert set(FUNCTIONS) <= set(functions())
    assert kernel("ln", "f64", "strict") is kernel("log", "f64", "strict")


@pytest.mark.parametrize("isa", ["avx2", "avx512"])
@pytest.mark.parametrize(("fn", "dtype", "level"), ALL)
def test_a_kernel_reproduces_its_recorded_error_on_this_host(fn, dtype, level, isa):
    verdict = validate_kernel(fn, dtype, level, isa)

    assert verdict.ok is not False, verdict.detail
    assert verdict.ok is True or not host_can_run(isa, dtype)


@pytest.mark.parametrize(("fn", "dtype", "level"), ALL)
def test_an_avx512_kernel_builds_whatever_the_host_can_run(fn, dtype, level, tmp_path):
    """A runner without AVX-512 cannot execute these rows above; it can still refuse one that does not compile."""
    cc = c_compiler()
    assert cc is not None, "the gate needs a C compiler"
    unit = tmp_path / "kernel.c"
    body = render(kernel(fn, dtype, level), "avx512").source
    unit.write_text(f"#include <math.h>\n#include <{HEADERS['avx512']}>\n{body}\n")

    sut = subprocess.run(
        [cc, "-O1", *c_flags("avx512", dtype), "-c", str(unit), "-o", str(unit.with_suffix(".o"))],
        capture_output=True,
        text=True,
        check=False,
    )

    assert sut.returncode == 0, sut.stderr


@pytest.mark.parametrize("isa", ["neon", "sve"])
@pytest.mark.parametrize(("fn", "dtype", "level"), ALL)
def test_a_kernel_holds_on_the_arm_targets_or_at_least_builds(fn, dtype, level, isa):
    """Under qemu it reproduces its recorded error; without it, the cross compiler must take it."""
    verdict = validate_kernel(fn, dtype, level, isa)

    assert verdict.ok is not False, verdict.detail
    assert verdict.ok is True or verdict.detail in ("builds", "no cross compiler")


def measured(k: Kernel, samples: int, flags: tuple[str, ...] = ()) -> Measured:
    seen = measure(k, host_isa(), samples, flags)
    assert seen is not None
    return seen


def host_isa() -> str:
    for isa in ("avx512", "avx2"):
        if host_can_run(isa, "f64"):
            return isa
    pytest.skip("host runs no x86 vector kernels")


def test_a_wrong_coefficient_fails_the_gate():
    k = kernel("exp", "f64", "relaxed")
    body = tuple(line.replace("0.5", "0.51") if line.startswith("p = ") else line for line in k.body)
    assert body != k.body

    seen = measured(dataclasses.replace(k, body=body), 1 << 12)

    assert seen.ulp > 1000 * k.error_ulp


@pytest.mark.parametrize("fn", ["sin", "exp", "log", "pow", "fmod"])
def test_a_strict_kernel_without_its_guard_gets_specials_wrong(fn):
    k = kernel(fn, "f64", "strict")

    seen = measured(dataclasses.replace(k, guard=""), 1 << 10)

    assert seen.special > 0


@pytest.mark.parametrize("fn", functions())
def test_relaxed_and_fast_have_no_branch_and_strict_at_most_one(fn):
    for level in ("relaxed", "fast"):
        assert "if (" not in spelled(fn, "f64", level, "avx2").source
    assert spelled(fn, "f64", "strict", "avx2").source.count("if (__builtin_expect") <= 1


def test_the_strict_cold_path_calls_scalar_libm():
    source = spelled("log", "f32", "strict", "avx2").source

    assert "vs[j] = logf(xs[j]);" in source


def test_the_levels_get_cheaper():
    for fn in functions():
        counts = [s.intrinsics for s in kernels_for(fn, "f64", "avx512")]
        assert counts[0] >= counts[1] >= counts[2], fn


def test_strict_refuses_fast_math_at_compile_time():
    with pytest.raises(RuntimeError, match="strict math kernels need IEEE semantics"):
        measure(kernel("sin", "f64", "strict"), host_isa(), 1 << 10, ("-ffast-math",))


def test_log1p_refuses_fast_math_at_every_level():
    with pytest.raises(RuntimeError, match="IEEE semantics"):
        measure(kernel("log1p", "f64", "relaxed"), host_isa(), 1 << 10, ("-ffast-math",))


def test_a_relaxed_pow_refuses_fast_math_and_the_rung_below_it_survives():
    below = next(k for k in ladder("pow", "f64") if not needs_ieee(k))

    with pytest.raises(RuntimeError, match="IEEE semantics.*use the next rung down"):
        measure(kernel("pow", "f64", "relaxed"), host_isa(), 1 << 10, ("-ffast-math",))
    assert measured(below, 1 << 14, ("-ffast-math",)).ulp <= 3 * below.error_ulp


@pytest.mark.parametrize("fn", ["sin", "exp", "log", "atan"])
def test_a_relaxed_kernel_survives_fast_math_within_three_times_its_error(fn):
    k = kernel(fn, "f64", "relaxed")

    seen = measured(k, 1 << 14, ("-ffast-math",))

    assert seen.ulp <= 3 * k.error_ulp


def test_every_spelled_identifier_exists_in_the_x86_headers():
    include = subprocess.run(["clang", "-print-resource-dir"], capture_output=True, text=True, check=False).stdout
    folder = pathlib.Path(include.strip()) / "include"
    if not folder.exists():
        pytest.skip("no clang resource headers")
    text = "".join(path.read_text(errors="ignore") for path in folder.glob("*intrin*.h"))
    source = "\n".join(render(kernel(*key), isa).source for key in ALL for isa in ("avx2", "avx512"))
    names = set(re.findall(r"\b_mm\d+_\w+", source))

    assert names
    assert sorted(name for name in names if name not in text) == []


def test_avx512_at_256_bits_gets_the_256_bit_spelling():
    assert "_mm256_" in spelled("sin", "f64", "relaxed", "avx512_256").source


def test_an_unknown_function_names_what_exists():
    with pytest.raises(KeyError, match="sin, cos"):
        kernel("gamma", "f64", "strict")


def test_libmvec_has_every_listed_call():
    candidates = list(pathlib.Path("/lib").glob("*/libmvec.so.1"))
    if not candidates:
        pytest.skip("no glibc libmvec here")
    symbols = subprocess.run(["nm", "-D", str(candidates[0])], capture_output=True, text=True, check=False).stdout
    for fn, dtype, level in (row for row in ALL if row[0] not in NO_LIBRARY):
        for isa in ("avx2", "avx512"):
            call = libraries(fn, dtype, isa, level)["libmvec"]
            assert call in symbols, call


def test_the_library_call_follows_the_level():
    assert libraries("sin", "f64", "avx512", "strict")["svml"] == "__svml_sin8_ha"
    assert libraries("sin", "f64", "avx512", "relaxed")["sleef"] == "Sleef_sind8_u35avx512f"
    assert libraries("sin", "f32", "avx2", "fast")["svml"] == "__svml_sinf8_ep"
    assert libraries("sin", "f64", "neon", "strict") == {}


def test_the_cli_returns_all_three_levels_as_c(capsys):
    assert main(["kernel", "avx2", "ln", "f64", "--no-verify"]) == 0

    out = capsys.readouterr().out
    for level in LEVELS:
        assert f"alloy_log_f64_{level}" in out
    assert "_mm256_fmadd_pd" in out
    assert "contract: finite, positive, normal" in out
    assert "or call libmvec: _ZGVdN4v_log" in out


def test_a_lookup_of_a_function_returns_its_kernels(capsys):
    assert main(["lookup", "avx512", "sin", "f64", "--no-verify"]) == 0

    out = capsys.readouterr().out
    assert "tier sin-quad-cheb13" in out
    assert "alloy_sin_f64_strict" in out


def test_a_lookup_of_a_function_outside_the_ops_returns_its_kernels(capsys):
    assert main(["lookup", "avx2", "tanh", "f32", "--no-verify"]) == 0

    assert "alloy_tanh_f32_fast" in capsys.readouterr().out


def test_a_lookup_of_an_unknown_name_fails(capsys):
    assert main(["lookup", "avx2", "gamma", "f64", "--no-verify"]) != 0


def test_hints_quote_the_levels_and_the_call():
    line = kernel_summary("avx2", "f64", "log")

    assert "strict" in line and "relaxed" in line and "fast" in line
    assert "kernel avx2 log f64" in line


ARM_MOD = """
#include <math.h>
#include <stdio.h>
#include <@HEADER@>
int main(void) {
    @C@ a[64], b[64], r[64];
    int n = (int)(@LANES@), bad = 0;
    for (int j = 0; j < n; j++) {
        a[j] = (@C@)((j % 2 ? -1 : 1) * (7.5 + 1.37 * j));
        b[j] = (@C@)(0.75 + 0.31 * j);
    }
    @VEC@ va = @LOAD@, vb = @LOADB@;
    @VEC@ q = @ROUND@;
    @STORE@;
    for (int j = 0; j < n; j++)
        if (fabs(r[j] - fmod@SUFFIX@(a[j], b[j])) > 1e-5) bad++;
    printf("bad=%d lanes=%d\\n", bad, n);
    return bad != 0;
}
"""


@pytest.mark.parametrize("isa", ["neon", "sve"])
@pytest.mark.parametrize("dtype", ["f64", "f32"])
def test_the_arm_fmod_recipes_compute_fmod(isa, dtype, tmp_path):
    """The table's own recipe steps run: divide, truncate, subtract the multiple."""
    arm = emulated(isa)
    if arm is None:
        pytest.skip("needs qemu-aarch64 and aarch64-linux-gnu-gcc")
    cc, flags, launcher = arm
    div, trunc, fnma = load().entry(isa, "mod", dtype).recipe
    r = Renderer(isa, dtype)
    pg = "" if isa == "neon" else f"{r.fields['p']}, "
    # vfmsq and svmls both take the accumulator first: a - q*b
    holes = {
        "HEADER": HEADERS[isa],
        "C": r.fields["c"],
        "VEC": r.fields["vec"],
        "LANES": r.fields["lanes"],
        "LOAD": r.call("load", "a"),
        "LOADB": r.call("load", "b"),
        "ROUND": f"{trunc}({pg}{div}({pg}va, vb))",
        "STORE": r.call("store", "r", f"{fnma}({pg}va, q, vb)"),
        "SUFFIX": "" if dtype == "f64" else "f",
    }
    source = ARM_MOD
    for key, value in holes.items():
        source = source.replace(f"@{key}@", value)
    (tmp_path / "m.c").write_text(source)
    exe = tmp_path / "m"
    subprocess.run([cc, "-O1", *flags, str(tmp_path / "m.c"), "-lm", "-o", str(exe)], check=True)

    run = subprocess.run([*launcher, str(exe)], capture_output=True, text=True, check=False)

    assert run.returncode == 0, run.stdout


def test_a_kernel_past_its_recorded_error_fails_its_verdict():
    k = kernel("exp", "f64", "relaxed")

    assert judged(k, Measured(k.error_ulp * 100, 0.0, 0.0, 0.0, 0), "gate").ok is False


def test_a_special_value_off_libm_fails_the_verdict():
    k = kernel("exp", "f64", "strict")

    assert judged(k, Measured(k.error_ulp, 0.0, 0.0, 0.0, 1), "gate").ok is False


def test_a_kernel_at_its_record_passes_the_verdict():
    k = kernel("exp", "f64", "strict")

    assert judged(k, Measured(k.error_ulp, 0.0, 0.0, 0.0, 0), "gate").ok is True


@pytest.mark.parametrize("compiler", ["gcc", "clang"])
@pytest.mark.parametrize("fn", ["log", "log2", "log10", "pow"])
def test_an_avx2_kernel_survives_the_matrixs_reassoc_flags(compiler, fn, tmp_path):
    """The f64 float conversion was an FP subtraction, which reassociation cancelled."""
    k = next(k for k in ladder(fn, "f64") if not needs_ieee(k))
    args = ", ".join(f"_mm256_set1_pd({v})" for v in (8.0, 2.0)[: len(k.args)])
    source = tmp_path / "k.c"
    source.write_text(
        "#include <immintrin.h>\n#include <math.h>\n#include <stdio.h>\n"
        f"{render(k, 'avx2').source}\n"
        f'int main(void) {{ double o[4]; _mm256_storeu_pd(o, {k.name}({args})); printf("%.17g", o[0]); }}\n'
    )
    flags = [*configuration_matrix.load().compilers[compiler].fp["reassoc"], "-O2", "-mavx2", "-mfma"]
    subprocess.run([compiler, *flags, str(source), "-lm", "-o", str(tmp_path / "k")], check=True)

    sut = float(subprocess.run([str(tmp_path / "k")], capture_output=True, text=True, check=True).stdout)

    expected = {"log": math.log(8.0), "log2": 3.0, "log10": math.log10(8.0), "pow": 64.0}[fn]
    assert sut == pytest.approx(expected, rel=1e-13)


def test_clang_keeps_a_strict_kernel_exact_under_associative_math():
    k = kernel("sin", "f64", "strict")

    assert "#pragma clang fp reassociate(off)" in render(k, "avx2").source


def strict_value(fn: str, dtype: str, args: tuple[float, ...], tmp_path: pathlib.Path) -> float:
    """One strict kernel on ``args`` in every lane, as a program built like the agent's own."""
    k = kernel(fn, dtype, "strict")
    r = Renderer("avx2", dtype)
    c = r.fields["c"]
    loads = ", ".join(r.call("load", f"{name}s") for name in k.args)
    arrays = "".join(
        f"{c} {name}s[16]; for (int j = 0; j < 16; j++) {name}s[j] = {v!r};\n"
        for name, v in zip(k.args, args, strict=True)
    )
    source = tmp_path / "k.c"
    source.write_text(
        f"#include <immintrin.h>\n#include <math.h>\n#include <stdio.h>\n{render(k, 'avx2').source}\n"
        f"int main(void) {{ {arrays} {c} out[16]; {r.call('store', 'out', f'{k.name}({loads})')};\n"
        'printf("%a", (double)out[0]); }\n'
    )
    flags = c_flags("avx2", dtype)
    subprocess.run([str(c_compiler()), "-O2", *flags, str(source), "-lm", "-o", str(tmp_path / "k")], check=True)
    return float.fromhex(subprocess.run([str(tmp_path / "k")], capture_output=True, text=True, check=True).stdout)


@pytest.mark.skipif(not host_can_run("avx2", "f64"), reason="needs AVX2")
@pytest.mark.parametrize(
    "fn, dtype, args, exact",
    [
        ("cos", "f32", (0.0,), 1.0),
        ("cos", "f32", (-0.0,), 1.0),
        ("cos", "f32", (1e-5,), 1.0),
        ("cos", "f64", (0.0,), 1.0),
        ("cos", "f64", (1e-9,), 1.0),
        ("pow", "f64", (3.0, 1.0), 3.0),
        ("pow", "f32", (3.0, 1.0), 3.0),
        ("fmod", "f64", (0.7, 0.1), 0.09999999999999992),
        ("fmod", "f64", (-0.7, 0.1), -0.09999999999999992),
        ("fmod", "f32", (0.7, 0.1), 0.09999997913837433),
    ],
)
def test_a_strict_kernel_is_exact_where_a_truncating_caller_would_notice(fn, dtype, args, exact, tmp_path):
    """One ulp below 1 or 3 casts to 0 or 2, and 0.7/0.1 rounds up to 7: the listed bound excuses none of these."""
    sut = strict_value(fn, dtype, args, tmp_path)

    assert sut == exact


@pytest.mark.parametrize("fn", functions())
@pytest.mark.parametrize("dtype", ["f64", "f32"])
def test_a_ladder_trades_accuracy_for_intrinsics_rung_by_rung(fn, dtype):
    sut = [k for k in ladder(fn, dtype) if k.level != "strict"]

    errors = [k.error_ulp for k in sut]
    costs = [render(k, "avx2").intrinsics for k in sut]
    assert errors == sorted(errors)
    assert costs == sorted(costs, reverse=True)


def test_a_tolerance_picks_the_cheapest_kernel_that_holds_it():
    sut = cheapest("sin", "f64", "avx2", max_ulp=10.0)

    assert sut.kernel.error_ulp <= 10.0
    assert sut.intrinsics < spelled("sin", "f64", "relaxed", "avx2").intrinsics
    cheaper = [k for k in ladder("sin", "f64") if render(k, "avx2").intrinsics < sut.intrinsics]
    assert cheaper and all(k.error_ulp > 10.0 for k in cheaper)


def test_an_absolute_tolerance_picks_by_the_absolute_error():
    sut = cheapest("sin", "f64", "avx512", max_abs=1e-9)

    assert sut.kernel.error_abs <= 1e-9
    assert sut.kernel.level not in ("strict", "relaxed")


def test_a_tolerance_no_kernel_holds_names_the_most_accurate_one():
    with pytest.raises(
        KeyError, match="pow f64: no kernel within the bound; the most accurate is (strict|relaxed) at 1"
    ):
        cheapest("pow", "f64", "avx2", max_ulp=0.1)


def test_a_rung_a_function_lacks_names_the_ones_it_has():
    with pytest.raises(KeyError, match="log f32 has no mid1 rung \\(it has: strict, relaxed, fast\\)"):
        kernel("log", "f32", "mid1")


def test_the_cli_lists_the_ladder_and_answers_a_bound_with_one_kernel(capsys):
    assert main(["kernel", "avx2", "sin", "f64", "--no-verify"]) == 0
    listing = capsys.readouterr().out
    assert main(["kernel", "avx2", "sin", "f64", "--max-ulp", "10", "--no-verify"]) == 0
    bounded = capsys.readouterr().out

    assert "// ladder: strict" in listing and "mid1" in listing
    picked = cheapest("sin", "f64", "avx2", max_ulp=10.0).kernel.name
    assert f"static inline __m256d {picked}(" in bounded
    assert bounded.count("static inline") == 1


def test_a_strict_sve_kernel_spills_into_arrays_of_constant_size():
    sut = spelled("sin", "f64", "strict", "sve").source

    assert "double xs[32], vs[32], bads[32];" in sut
    assert "[svcntd()]" not in sut


def test_a_relaxed_pow_carries_its_logarithm_as_a_double_word():
    sut = kernel("pow", "f64", "relaxed")

    assert sut.error_ulp < 2.0
    assert not sut.guard


@pytest.mark.parametrize("fn", [fn for fn in functions() if len(kernel(fn, "f32", "relaxed").args) == 1])
def test_a_one_argument_f32_kernel_is_measured_on_every_input_of_its_range(fn):
    assert all(k.exhaustive for k in ladder(fn, "f32"))


@pytest.mark.parametrize("key", [("pow", "f32"), ("fmod", "f32"), ("sin", "f64")])
def test_a_kernel_with_too_many_inputs_stays_sampled_and_says_so(key, capsys):
    assert not any(k.exhaustive for k in ladder(*key))

    assert main(["kernel", "avx2", key[0], key[1], "--level", "relaxed", "--no-verify"]) == 0
    assert "ulp sampled;" in capsys.readouterr().out


def test_an_unguarded_kernel_is_checked_inside_its_grids_and_a_guarded_one_everywhere():
    assert inside(kernel("sin", "f32", "strict")) == "1"
    assert inside(kernel("exp", "f32", "relaxed")).startswith("(-1.0 <= x && x <= 1.0) || (-87.0 <= x && x <= 87.0)")


needs_avx2 = pytest.mark.skipif(not host_can_run("avx2", "f64"), reason="host does not run AVX2")


@needs_avx2
def test_a_function_is_timed_rung_by_rung_next_to_its_library_calls():
    sut = time_function("exp", "f64", "avx2")

    names = [row.name for row in sut]
    assert names[: len(ladder("exp", "f64"))] == [k.level for k in ladder("exp", "f64")]
    assert "libm (scalar)" in names
    assert all(0.0 < row.ns < 1000.0 for row in sut)
    by_name = {row.name: row.ns for row in sut}
    assert by_name["fast"] < by_name["libm (scalar)"]


@needs_avx2
def test_the_cli_prints_a_time_per_way_to_compute_the_function(capsys):
    assert main(["time", "avx2", "exp", "f64", "--json"]) == 0

    records = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert {r["name"] for r in records} >= {"strict", "relaxed", "fast", "libm (scalar)"}
    assert all(r["function"] == "exp" and r["ns"] > 0 for r in records)


def test_the_advice_for_pow_says_its_recommended_kernel_steps_down_under_reassociation():
    sut = kernel_summary("avx2", "f64", "pow", "relaxed")

    assert "take relaxed where the inputs hold its contract" in sut
    assert "under reassociation relaxed does not compile: take the next rung down" in sut
    assert "does not compile" not in kernel_summary("avx2", "f64", "exp", "relaxed")
