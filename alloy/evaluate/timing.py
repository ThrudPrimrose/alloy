# Copyright 2026 ETH Zurich and the Alloy authors.
"""Time the verified candidates of every scope inside the whole program, then alloy-full (every scope's winner)
against DaCe's default CPU codegen. The arms of one comparison run in one child on one set of buffers, alternating
forward and reversed order, at sizes that keep the working set out of cache (``docs/design.md``, Timing)."""

import ctypes
import dataclasses
import math
import pathlib
import statistics
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

import dace
import numpy as np
import pydantic.dataclasses

from alloy import machine
from alloy.backend.build import Build
from alloy.backend.sweep import ScopeReport
from alloy.evaluate.link import Linker
from alloy.evaluate.verify import (
    CALL_TIMEOUT_S,
    Children,
    Reference,
    Verdict,
    Verification,
    accumulation_length,
    in_child,
    judge,
)
from alloy.frontend import inputs
from alloy.frontend.inputs import Draw, Grading, Manifest
from alloy.frontend.scopes import Program
from alloy.records import RECORD, Parameters

REFERENCE = "reference"


@pydantic.dataclasses.dataclass(slots=True, frozen=True, config=RECORD)
class Measured:
    """Median seconds of one arm with its 95% CI (NaN when its outputs failed at this size), and that verdict."""

    median: float
    low: float
    high: float
    verdict: Verdict


@pydantic.dataclasses.dataclass(slots=True, frozen=True, config=RECORD)
class ScopeTiming:
    """One scope's arms screened at ``screen_sizes`` and re-timed at ``final_sizes``, and the arm that won."""

    screen: dict[str, Measured]
    final: dict[str, Measured]
    winner: str
    screen_sizes: Parameters
    final_sizes: Parameters


@pydantic.dataclasses.dataclass(slots=True, frozen=True, config=RECORD)
class ProgramTiming:
    """alloy-full and DaCe's default codegen timed on the whole program at ``sizes``."""

    arms: dict[str, Measured]
    sizes: Parameters


@pydantic.dataclasses.dataclass(slots=True, frozen=True, config=RECORD)
class Timings:
    """Every scope's timing, and alloy-full against DaCe's default codegen."""

    scopes: dict[str, ScopeTiming]
    program: ProgramTiming


@dataclass(slots=True, frozen=True)
class Arms:
    """Programs compared on one input, the first being the reference; ``symbol`` names the scope whose wrapper is
    read, or is empty to time the whole call."""

    folders: dict[str, pathlib.Path]
    tolerances: dict[str, str]
    symbol: str
    outputs: tuple[str, ...]
    nondeterministic: frozenset[str]
    grading: Grading


def median_ci(samples: list[float]) -> tuple[float, float, float]:
    """Median and its distribution-free 95% CI from order statistics (Hoefler and Belli, SC'15)."""
    s, n = sorted(samples), len(samples)
    spread = 1.96 * math.sqrt(n)
    low, high = max(math.floor((n - spread) / 2), 1), min(math.ceil(1 + (n + spread) / 2), n)
    return statistics.median(s), s[low - 1], s[high - 1]


#: The most a size is scaled; past it a goal counts as unreachable.
MAX_GROWTH = 1 << 24


def bytes_at(containers: Iterable[dace.data.Data], sizes: Parameters) -> int:
    """Bytes of those of ``containers`` whose size ``sizes`` decides."""
    numeric: dict[dace.symbol | str, int | float] = {n: v for n, v in sizes.items() if isinstance(v, int | float)}
    return sum(
        int(dace.symbolic.evaluate(d.total_size, numeric)) * d.dtype.bytes
        for d in containers
        if {str(s) for s in dace.symbolic.pystr_to_symbolic(str(d.total_size)).free_symbols} <= numeric.keys()
    )


def footprint(sdfg: dace.SDFG, sizes: Parameters) -> int:
    """Bytes of the containers of ``sdfg`` whose size ``sizes`` decides, transients included."""
    return bytes_at(sdfg.arrays.values(), sizes)


def sized(sdfg: dace.SDFG, program: dace.SDFG, base: dict[str, int], target: float, cap: float) -> dict[str, int]:
    """``base`` with the array-extent symbols of ``sdfg`` scaled by the smallest factor that makes ``sdfg`` touch
    ``target`` bytes, but no further than ``program`` touching ``cap`` bytes: the symbols are shared, so a scope
    that touches one vector would otherwise grow the program's other arrays without bound."""
    extents = {str(s) for d in sdfg.arrays.values() if not d.transient for s in d.free_symbols} & base.keys()
    if not extents:
        return base

    def scaled(factor: float) -> dict[str, int]:
        return {k: max(1, round(v * factor)) if k in extents else v for k, v in base.items()}

    def reaching(g: dace.SDFG, goal: float) -> float:
        low, high = 0.0, 1.0
        while footprint(g, scaled(high)) < goal:
            high *= 2
            if high > MAX_GROWTH:  # the extents do not reach this goal: it does not bound the factor
                return math.inf
        for _ in range(40):
            mid = (low + high) / 2
            low, high = (mid, high) if footprint(g, scaled(mid)) < goal else (low, mid)
        return high

    factor = min(reaching(sdfg, target), reaching(program, cap))
    return base if math.isinf(factor) else scaled(factor)


def stage_sizes(
    sdfg: dace.SDFG, program: dace.SDFG, manifest: Manifest, factor: float, cap_factor: float, *, grow_only: bool
) -> dict[str, int]:
    """The largest preset (among those whose program fits ``cap_factor`` x the largest cache, and the memory
    :func:`machine.timing_memory_cap` leaves) scaled to ``factor`` x the largest cache; with ``grow_only``, only when
    it is smaller."""
    cache = machine.largest_cache_bytes()
    cap = min(cap_factor * cache, machine.timing_memory_cap())
    presets = inputs.presets(manifest)
    if not presets:
        raise ValueError(f"{manifest.path}: no fixed size preset to time at")
    fits = [s for s in presets if footprint(program, s) <= cap] or [min(presets, key=lambda s: footprint(program, s))]
    base = max(fits, key=lambda s: footprint(sdfg, s))
    target = factor * cache
    if grow_only and footprint(sdfg, base) >= target:
        return base
    return inputs.constrained(manifest, sized(sdfg, program, base, target, cap)) or base


def clock(program: Any, symbol: str) -> Callable[[], float]:
    fn = program.get_exported_function(f"alloy_seconds_{symbol}", ctypes.c_double)
    if fn is None:
        raise RuntimeError(f"{program.filename} has no timer for {symbol}")
    return fn


def time_arms(folders: list[str], symbol: str, args: dict[str, Any], reps: int) -> list[list[float]]:
    """In a child: one warmup, then ``reps`` rounds calling every arm on the same buffers, reversed every other
    round; every array is reset before each call. Seconds per arm, from the scope timer or the whole call."""
    from dace.codegen import compiler

    programs = [compiler.load_precompiled_sdfg(f) for f in folders]
    clocks = [clock(p, symbol) for p in programs] if symbol else []
    pristine = {k: np.array(v, copy=True) for k, v in args.items() if isinstance(v, np.ndarray)}
    buffers = {**args, **{k: v.copy() for k, v in pristine.items()}}
    times: list[list[float]] = [[] for _ in programs]
    order = list(range(len(programs)))
    for rep in range(reps + 1):
        for i in order if rep % 2 == 0 else order[::-1]:
            for k, v in pristine.items():
                np.copyto(buffers[k], v)
            start = time.perf_counter()
            programs[i](**buffers)
            elapsed = time.perf_counter() - start
            if rep:
                times[i].append(clocks[i]() if clocks else elapsed)
    return times


def check(arms: Arms, draw: Draw, length: int) -> dict[str, Verdict]:
    """Every arm's outputs on ``draw`` against the first arm's, each in its own child, so a crash is a verdict."""
    with Children() as children:
        pending = {name: children.submit(folder, draw, arms.outputs) for name, folder in arms.folders.items()}
        first_name = next(iter(pending))
        first = pending.pop(first_name).result()
        if isinstance(first, str):
            raise RuntimeError(f"the reference crashed at {draw.sizes}: {first}")
        ref = Reference([first[0]], arms.nondeterministic, arms.grading)
        verdicts = {first_name: Verdict("exact")}  # judged against itself a nondeterministic output would fail its band
        for name in list(pending):  # judged in turn, so each arm's outputs go before the next
            verdicts[name] = judge(arms.tolerances[name], ref, [pending.pop(name).result()], [length])
        return verdicts


def measure(arms: Arms, draw: Draw, length: int, cpus: tuple[int, ...], reps: int) -> dict[str, Measured]:
    """Check every arm at ``draw``'s size, then time the passing ones together on ``cpus``."""
    verdicts = check(arms, draw, length)
    passing = [name for name in arms.folders if verdicts[name].ok]
    args = {**draw.values, **draw.sizes}
    times = timed(arms, passing, args, cpus, reps) if passing else None
    if isinstance(times, str):  # one arm crashed mid-round: find it, the others keep their times
        separate = {name: timed(arms, [name], args, cpus, reps) for name in passing}
        verdicts |= {n: Verdict("crashed", detail=t) for n, t in separate.items() if isinstance(t, str)}
        if not verdicts[passing[0]].ok:
            raise RuntimeError(f"timing {arms.symbol or 'the program'} failed: {verdicts[passing[0]].detail}")
        measured = {n: Measured(*median_ci(t[0]), verdicts[n]) for n, t in separate.items() if not isinstance(t, str)}
    else:
        measured = {name: Measured(*median_ci(t), verdicts[name]) for name, t in zip(passing, times or [], strict=True)}
    return {name: measured.get(name, Measured(math.nan, math.nan, math.nan, v)) for name, v in verdicts.items()}


def timed(
    arms: Arms, names: list[str], args: dict[str, Any], cpus: tuple[int, ...], reps: int
) -> list[list[float]] | str:
    """``names`` timed together in the one running child: the whole memory, and one call's budget per timed call."""
    timeout = CALL_TIMEOUT_S * (reps + 1) * len(names)
    return in_child(time_arms, ([str(arms.folders[n]) for n in names], arms.symbol, args, reps), cpus, 1.0, timeout)


def band_compared(program: Program, verification: Verification, outputs: tuple[str, ...]) -> frozenset[str]:
    """The outputs a timing size compares by band: those the draws saw change, or all of a program that reduces, whose
    sums can round alike on every small draw and still differ at a size past them."""
    return frozenset(outputs) if any(s.has_reduction for s in program.scopes) else verification.nondeterministic


def time_scope(linker: Linker, rep: ScopeReport, verification: Verification, manifest: Manifest) -> ScopeTiming:
    """Screen every verified distinct candidate, re-time the fastest on every core, and pick the winner: the
    fastest whose CI lies below the reference's, else the reference."""
    matrix, symbol = linker.matrix, rep.scope.symbol
    verified = [
        b
        for b in rep.builds[1:]
        if (symbol, b.name) in verification.programs and verification.verdicts[symbol][b.name].ok
    ]
    arms = Arms(
        {REFERENCE: verification.reference} | {b.name: verification.programs[symbol, b.name] for b in verified},
        {REFERENCE: "exact"} | {b.name: b.candidate.tolerance(matrix) for b in verified},
        symbol,
        manifest.outputs,
        band_compared(linker.program, verification, manifest.outputs),
        inputs.grading(manifest),
    )
    t, cores = matrix.timing, machine.physical_cores()
    original, cap = linker.program.original, t.max_program_cache_factor
    screen_sizes = stage_sizes(rep.scope.sdfg, original, manifest, t.screen_cache_factor, cap, grow_only=False)
    final_sizes = stage_sizes(rep.scope.sdfg, original, manifest, t.final_cache_factor, cap, grow_only=True)
    screen = measure(
        arms, inputs.at(manifest, screen_sizes), length(linker, screen_sizes), cores[: t.screen_cores], t.screen_reps
    )
    ranked = sorted((n for n in screen if n != REFERENCE and screen[n].verdict.ok), key=lambda n: screen[n].median)
    keep = [REFERENCE, *ranked[: t.top]]
    top = dataclasses.replace(arms, folders={n: arms.folders[n] for n in keep})
    final = measure(top, inputs.at(manifest, final_sizes), length(linker, final_sizes), cores, t.final_reps)
    return ScopeTiming(screen, final, winner_of(final, ranked[: t.top]), screen_sizes, final_sizes)


def winner_of(final: dict[str, Measured], names: list[str]) -> str:
    """The fastest of ``names`` that passes and whose CI lies wholly below the reference's, else the reference."""
    clear = [n for n in names if final[n].verdict.ok and final[n].high < final[REFERENCE].low]
    return min(clear, key=lambda n: final[n].median, default=REFERENCE)


def length(linker: Linker, sizes: dict[str, int]) -> int:
    return accumulation_length(linker.program, sizes)


def time_program(linker: Linker, reports: list[ScopeReport], verification: Verification, manifest: Manifest) -> Timings:
    """Every scope's timing, then alloy-full against DaCe's default codegen on every core."""
    scopes = {rep.scope.symbol: time_scope(linker, rep, verification, manifest) for rep in reports}
    winners = {rep.scope.symbol: winning_build(rep, scopes[rep.scope.symbol].winner) for rep in reports}
    candidates = frozenset(b.candidate for b in winners.values())
    archives = {symbol: b.archive for symbol, b in winners.items() if b.archive}
    arms = Arms(
        {"dace_default": linker.compile_default(), "alloy_full": linker.compile(archives, "alloy_full", candidates)},
        {"dace_default": "exact", "alloy_full": "band"},
        "",
        manifest.outputs,
        frozenset(manifest.outputs),  # alloy-full mixes FP levels per scope: compare every output by band
        inputs.grading(manifest),
    )
    t, original = linker.matrix.timing, linker.program.original
    sizes = stage_sizes(original, original, manifest, t.final_cache_factor, t.max_program_cache_factor, grow_only=True)
    program = measure(arms, inputs.at(manifest, sizes), length(linker, sizes), machine.physical_cores(), t.final_reps)
    return Timings(scopes, ProgramTiming(program, sizes))


def winning_build(rep: ScopeReport, winner: str) -> Build:
    return rep.builds[0] if winner == REFERENCE else next(b for b in rep.builds if b.name == winner)
