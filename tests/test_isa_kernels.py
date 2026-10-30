# Copyright 2026 ETH Zurich and the Alloy authors.
"""Math kernels: every function comes back as intrinsics at three levels. Each kernel is run against a wider libm
at its recorded error, and the gate is shown to fail on a broken kernel."""

import dataclasses
import pathlib
import re
import subprocess

import pytest

from alloy.isa.__main__ import main
from alloy.isa.hints import kernel_summary
from alloy.isa.mathcheck import Measured, measure, validate_kernel
from alloy.isa.mathkernels import LEVELS, Kernel, functions, kernel, kernels_for, libraries, render, spelled
from alloy.isa.validate import host_can_run

ALL = [(fn, dtype, level) for fn in functions() for dtype in ("f64", "f32") for level in LEVELS]
FUNCTIONS = "sin cos tan exp exp2 exp10 expm1 log log2 log10 log1p pow atan asin acos sinh cosh tanh".split()


def test_the_functions_an_agent_asks_for_all_have_kernels():
    assert set(FUNCTIONS) <= set(functions())
    assert kernel("ln", "f64", "strict") is kernel("log", "f64", "strict")


@pytest.mark.parametrize("isa", ["avx2", "avx512"])
@pytest.mark.parametrize(("fn", "dtype", "level"), ALL)
def test_a_kernel_reproduces_its_recorded_error_on_this_host(fn, dtype, level, isa):
    verdict = validate_kernel(fn, dtype, level, isa)

    assert verdict.ok is not False, verdict.detail
    assert verdict.ok is True or not host_can_run(isa, dtype)


@pytest.mark.parametrize("isa", ["neon", "sve"])
@pytest.mark.parametrize(("fn", "dtype", "level"), ALL)
def test_a_kernel_builds_for_the_arm_targets(fn, dtype, level, isa):
    verdict = validate_kernel(fn, dtype, level, isa)

    assert verdict.ok is None
    assert verdict.detail in ("builds", "no cross compiler")


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


@pytest.mark.parametrize("fn", ["sin", "exp", "log", "pow"])
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


@pytest.mark.parametrize("fn", ["sin", "exp", "log", "pow", "atan"])
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
    for fn, dtype, level in ALL:
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
    assert "python -m alloy.isa kernel avx2 log f64" in line
