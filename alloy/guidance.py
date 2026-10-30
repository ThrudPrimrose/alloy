# Copyright 2026 ETH Zurich and the Alloy authors.
"""When Alloy leaves a scope short, say why and how to finish it by hand: :func:`alloy.isa.hints.advice` on the
scope's own tasklets, for the widest ISA the host runs and the scope's float type."""

from collections.abc import Mapping

from dace import dtypes

from alloy.backend.build import Build
from alloy.backend.sweep import ScopeReport
from alloy.evaluate.verify import Verdict
from alloy.frontend.scopes import Scope
from alloy.isa.hints import advice
from alloy.isa.mathkernels import level_for
from alloy.isa.table import Table, load

__all__ = ["advisable_isa", "guidance", "scope_dtype", "scope_reason"]

#: The ISA table covers these matrix ISAs; AVX-512 at 256 bits has no hints of its own.
ADVISED = ("avx512", "avx2", "sve", "neon")


def scope_reason(rep: ScopeReport, verdicts: Mapping[str, Verdict], winner: Build | None) -> str:
    """Why ``rep``'s scope needs a hand, or ``""`` when Alloy did what it could."""
    built = [b for b in rep.builds if not b.error]
    if not built:
        first = rep.builds[0].error.splitlines()[0] if rep.builds else "no candidate"
        return f"every candidate failed to build: {first}"
    if verdicts and not any(verdicts[b.name].ok for b in built if b.name in verdicts):
        return "no candidate passed verification, so the chosen build falls back to the matrix default"
    if winner is not None and winner.remarks.vectorized == 0:
        missed = f": {winner.remarks.missed[0]}" if winner.remarks.missed else ""
        return f"the chosen build vectorized no loop{missed}"
    if rep.scope.calls_libm:
        return "the scope calls libm: an inlined kernel replaces the call and its spills"
    return ""


def scope_dtype(scope: Scope) -> str:
    """The float lane the scope computes in: f64 when any container is, f32 when only f32 is, f64 by default."""
    floats = {desc.dtype for desc in scope.sdfg.arrays.values()}
    return "f32" if dtypes.float32 in floats and dtypes.float64 not in floats else "f64"


def advisable_isa(host_isas: tuple[str, ...]) -> str | None:
    """The widest of ``host_isas`` the table has hints for."""
    return next((isa for isa in ADVISED if isa in host_isas), None)


def guidance(
    reports: list[ScopeReport],
    verdicts: Mapping[str, Mapping[str, Verdict]],
    winners: Mapping[str, Build],
    host_isas: tuple[str, ...],
    table: Table | None = None,
    *,
    finite_inputs: bool = False,
) -> dict[str, str]:
    """``{scope symbol: do-it-yourself text}`` for the scopes that need a hand; a kernel is recommended from the
    chosen build's FP level and whether the inputs are declared finite."""
    isa = advisable_isa(host_isas)
    if isa is None:
        return {}
    table = table or load()
    texts = {}
    for rep in reports:
        symbol = rep.scope.symbol
        reason = scope_reason(rep, verdicts.get(symbol, {}), winners.get(symbol))
        if reason:
            winner = winners.get(symbol)
            fp_level = winner.candidate.fp_level if winner is not None else ""
            level = level_for(fp_level, finite_inputs=finite_inputs)
            texts[symbol] = advice(reason, rep.scope.sdfg, isa, scope_dtype(rep.scope), table, level)
    return texts
