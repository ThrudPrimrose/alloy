# Copyright 2026 ETH Zurich and the Alloy authors.
"""A scope Alloy leaves short gets the reason and the intrinsics its own tasklets need."""

from types import SimpleNamespace
from typing import Any

import dace

from alloy.evaluate.verify import Verdict
from alloy.guidance import advisable_isa, guidance, scope_dtype, scope_reason


def wave_sdfg(dtype=dace.float64) -> dace.SDFG:
    sdfg = dace.SDFG("wave")
    sdfg.add_array("a", [8], dtype)
    sdfg.add_array("b", [8], dtype)
    state = sdfg.add_state()
    state.add_mapped_tasklet(
        "wave",
        {"i": "0:8"},
        {"x": dace.Memlet("a[i]")},
        "y = math.sin(x)",
        {"y": dace.Memlet("b[i]")},
        external_edges=True,
    )
    return sdfg


def scope(calls_libm=True, sdfg=None) -> Any:
    return SimpleNamespace(symbol="s0", calls_libm=calls_libm, sdfg=sdfg or wave_sdfg())


def build(name="good", error="", vectorized=1, missed=()) -> Any:
    return SimpleNamespace(name=name, error=error, remarks=SimpleNamespace(vectorized=vectorized, missed=missed))


def report(*builds, calls_libm=False) -> Any:
    return SimpleNamespace(scope=scope(calls_libm), builds=builds)


GOOD, BAD = Verdict("exact"), Verdict("fail")


def test_a_clean_scope_needs_no_hand():
    rep = report(build())

    assert scope_reason(rep, {"good": GOOD}, rep.builds[0]) == ""


def test_every_failed_build_is_the_reason():
    rep = report(build(error="#error no SVE call\nmore"))

    assert scope_reason(rep, {}, None) == "every candidate failed to build: #error no SVE call"


def test_no_verified_candidate_is_the_reason():
    assert "no candidate passed verification" in scope_reason(report(build()), {"good": BAD}, None)


def test_a_scalar_winner_names_what_the_compiler_missed():
    rep = report(build(vectorized=0, missed=("a loop-carried dependence",)))

    assert scope_reason(rep, {"good": GOOD}, rep.builds[0]) == (
        "the chosen build vectorized no loop: a loop-carried dependence"
    )


def test_a_libm_scope_points_at_kernels():
    rep = report(build(), calls_libm=True)

    assert "inlined kernel" in scope_reason(rep, {"good": GOOD}, rep.builds[0])


def test_the_lane_follows_the_scope():
    assert scope_dtype(scope(sdfg=wave_sdfg(dace.float32))) == "f32"
    assert scope_dtype(scope()) == "f64"


def test_the_widest_covered_isa_is_advised():
    assert advisable_isa(("avx2", "avx512_256", "avx512")) == "avx512"
    assert advisable_isa(("avx512_256",)) is None


def test_the_advice_carries_the_reason_and_the_scopes_kernels():
    rep = report(build(), calls_libm=True)

    texts = guidance([rep], {"s0": {"good": GOOD}}, {"s0": rep.builds[0]}, ("avx2",))

    assert "Reason: the scope calls libm" in texts["s0"]
    assert "python -m alloy.isa kernel avx2 sin f64" in texts["s0"]


def test_a_clean_program_has_no_advice():
    rep = report(build())

    assert guidance([rep], {"s0": {"good": GOOD}}, {"s0": rep.builds[0]}, ("avx2",)) == {}


def test_a_host_outside_the_table_has_no_advice():
    assert guidance([report(build(error="x"))], {}, {}, ()) == {}
