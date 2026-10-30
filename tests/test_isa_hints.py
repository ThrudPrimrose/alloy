# Copyright 2026 ETH Zurich and the Alloy authors.
"""Do-it-yourself advice: the response body when Alloy cannot emit or validate vector code — a text
reason, the do-it-yourself instruction, and hints computed from the scope's own Python tasklets (each
classified and mapped to the relevant intrinsics with their traps and validation status)."""


from alloy.isa import load
from alloy.isa.hints import advice, tasklet_hints

TABLE = load()


def test_every_tasklet_is_collected_and_classified():
    hints = tasklet_hints(_example_sdfg(), "avx2", "f64", TABLE)
    by_tasklet = {hint.use.tasklet: hint for hint in hints}

    scale = by_tasklet["scale"]
    assert scale.use.ops == ("fma", "mul", "add")
    assert scale.kind == "elementwise"
    acc = by_tasklet["acc"]
    assert acc.use.reduces
    assert acc.kind == "reduction"
    assert "reduce_add" in {spelling.op for spelling in acc.spellings}


def test_the_hints_name_the_relevant_spellings():
    hints = tasklet_hints(_example_sdfg(), "avx2", "f64", TABLE)
    by_tasklet = {hint.use.tasklet: hint for hint in hints}

    spellings = {s.op: s for s in by_tasklet["scale"].spellings}
    assert spellings["mul"].spelling == "_mm256_mul_pd"
    assert spellings["add"].spelling == "_mm256_add_pd"
    assert "fma" in spellings
    if spellings["mul"].verified is not None:
        assert spellings["mul"].verified is True
    reduce_spellings = {s.op: s for s in by_tasklet["acc"].spellings}
    assert "reduce_add" in reduce_spellings
    assert "recipe" in reduce_spellings["reduce_add"].spelling


def test_a_libm_tasklet_points_at_tiers_and_the_library():
    sdfg = _libm_sdfg()
    (hint,) = tasklet_hints(sdfg, "avx2", "f64", TABLE)

    assert hint.use.ops == ("sin",)
    assert "libm" in hint.kind
    (spelling,) = hint.spellings
    assert "sin-quad-cheb13" in spelling.spelling
    assert "_ZGVcN4v_sin" in spelling.spelling


def test_advice_carries_the_reason_the_instruction_and_the_hints():
    text = advice("the masked tail is not expressible", _example_sdfg(), "avx2", "f64", TABLE)

    assert "Reason: the masked tail is not expressible" in text
    assert "Do it yourself" in text
    assert "tasklet 'scale'" in text
    assert "_mm256_fmadd_pd" in text
    assert "tasklet 'acc'" in text
    assert "reduce_add" in text


def test_integer_ops_under_a_float_dtype_are_absent_not_errors():
    (hint,) = tasklet_hints(_integer_sdfg(), "avx2", "f64", TABLE)

    spellings = {s.op for s in hint.spellings}
    assert "and" not in spellings  # integer op, no f64 spelling


def _example_sdfg():
    """Two scopes' worth of tasklets: a contractable elementwise map and a sum reduction."""
    import dace

    sdfg = dace.SDFG("hints_example")
    sdfg.add_array("a", [8], dace.float64)
    sdfg.add_array("t", [8], dace.float64)
    sdfg.add_scalar("total", dace.float64)
    state = sdfg.add_state()
    entry, exit_ = state.add_map("m", dict(i="0:8"))
    scale = state.add_tasklet("scale", {"x"}, {"y"}, "y = x * 2.0 + 0.5")
    a = state.add_access("a")
    t = state.add_access("t")
    state.add_memlet_path(a, entry, scale, dst_conn="x", memlet=dace.Memlet("a[i]"))
    state.add_memlet_path(scale, exit_, t, src_conn="y", memlet=dace.Memlet("t[i]"))
    acc = state.add_tasklet("acc", {"x"}, {"o"}, "o = x")
    state.add_memlet_path(entry, acc, dst_conn="x", memlet=dace.Memlet("a[i]"))
    total = state.add_access("total")
    state.add_memlet_path(acc, exit_, total, src_conn="o", memlet=dace.Memlet("total[0]", wcr="lambda q, p: q + p"))
    return sdfg


def _libm_sdfg():
    import dace

    sdfg = dace.SDFG("hints_libm")
    sdfg.add_array("a", [8], dace.float64)
    sdfg.add_array("b", [8], dace.float64)
    state = sdfg.add_state()
    entry, exit_ = state.add_map("m", dict(i="0:8"))
    node = state.add_tasklet("wave", {"x"}, {"y"}, "import math\ny = math.sin(x)")
    a, b = state.add_access("a"), state.add_access("b")
    state.add_memlet_path(a, entry, node, dst_conn="x", memlet=dace.Memlet("a[i]"))
    state.add_memlet_path(node, exit_, b, src_conn="y", memlet=dace.Memlet("b[i]"))
    return sdfg


def _integer_sdfg():
    import dace

    sdfg = dace.SDFG("hints_int")
    sdfg.add_array("a", [8], dace.int64)
    sdfg.add_array("b", [8], dace.int64)
    sdfg.add_array("c", [8], dace.int64)
    state = sdfg.add_state()
    entry, exit_ = state.add_map("m", dict(i="0:8"))
    node = state.add_tasklet("mask", {"x", "y"}, {"z"}, "z = x & y")
    a, b, c = state.add_access("a"), state.add_access("b"), state.add_access("c")
    state.add_memlet_path(a, entry, node, dst_conn="x", memlet=dace.Memlet("a[i]"))
    state.add_memlet_path(b, entry, node, dst_conn="y", memlet=dace.Memlet("b[i]"))
    state.add_memlet_path(node, exit_, c, src_conn="z", memlet=dace.Memlet("c[i]"))
    return sdfg
