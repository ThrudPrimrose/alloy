# Copyright 2026 ETH Zurich and the Alloy authors.
"""Time the verified candidates of every region inside the whole program, then alloy-full (every region's winner)
against DaCe's default CPU codegen. The arms of one comparison run in one child on one set of buffers, alternating
forward and reversed order, at sizes that keep the working set out of cache (``docs/design.md``, Timing)."""

import ctypes
import math
import pathlib
import statistics
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import dace
import numpy as np

from alloy import machine
from alloy.backend.build import Build
from alloy.backend.sweep import RegionReport
from alloy.evaluate.link import Linker
from alloy.evaluate.verify import (
    Children,
    Reference,
    Verdict,
    Verification,
    accumulation_length,
    in_child,
    judge,
)
from alloy.frontend import inputs
from alloy.frontend.inputs import Draw, Manifest

REFERENCE = "reference"


@dataclass(slots=True, frozen=True)
class Measured:
    """Median seconds of one arm with its 95% CI (NaN when its outputs failed at this size), and that verdict."""

    median: float
    low: float
    high: float
    verdict: Verdict


@dataclass(slots=True, frozen=True)
class RegionTiming:
    screen: dict[str, Measured]
    final: dict[str, Measured]
    winner: str
    screen_sizes: dict[str, int]
    final_sizes: dict[str, int]


@dataclass(slots=True, frozen=True)
class ProgramTiming:
    arms: dict[str, Measured]
    sizes: dict[str, int]


@dataclass(slots=True, frozen=True)
class Arms:
    """Programs compared on one input, the first being the reference; ``symbol`` names the region whose wrapper is
    read, or is empty to time the whole call."""

    folders: dict[str, pathlib.Path]
    tolerances: dict[str, str]
    symbol: str
    outputs: tuple[str, ...]
    nondeterministic: frozenset[str]


def median_ci(samples: list[float]) -> tuple[float, float, float]:
    """Median and its distribution-free 95% CI from order statistics (Hoefler and Belli, SC'15)."""
    s, n = sorted(samples), len(samples)
    spread = 1.96 * math.sqrt(n)
    low, high = max(math.floor((n - spread) / 2), 1), min(math.ceil(1 + (n + spread) / 2), n)
    return statistics.median(s), s[low - 1], s[high - 1]


def footprint(sdfg: dace.SDFG, sizes: dict[str, int]) -> int:
    """Bytes of the non-transient containers of ``sdfg`` at ``sizes``."""
    arrays = [d for d in sdfg.arrays.values() if not d.transient]
    return sum(int(dace.symbolic.evaluate(d.total_size, {**sizes})) * d.dtype.bytes for d in arrays)


def sized(sdfg: dace.SDFG, program: dace.SDFG, base: dict[str, int], target: float, cap: float) -> dict[str, int]:
    """``base`` with the array-extent symbols of ``sdfg`` scaled by the smallest factor that makes ``sdfg`` touch
    ``target`` bytes, but no further than ``program`` touching ``cap`` bytes: the symbols are shared, so a region
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
        for _ in range(40):
            mid = (low + high) / 2
            low, high = (mid, high) if footprint(g, scaled(mid)) < goal else (low, mid)
        return high

    return scaled(min(reaching(sdfg, target), reaching(program, cap)))


def stage_sizes(
    sdfg: dace.SDFG, program: dace.SDFG, manifest: Manifest, factor: float, cap_factor: float, *, grow_only: bool
) -> dict[str, int]:
    """The largest preset (among those whose program fits ``cap_factor`` x the largest cache) scaled to ``factor`` x
    the largest cache; with ``grow_only``, only when it is smaller."""
    cache = machine.largest_cache_bytes()
    cap = cap_factor * cache
    presets = inputs.presets(manifest)
    fits = [s for s in presets if footprint(program, s) <= cap] or [min(presets, key=lambda s: footprint(program, s))]
    base = max(fits, key=lambda s: footprint(sdfg, s))
    target = factor * cache
    return base if grow_only and footprint(sdfg, base) >= target else sized(sdfg, program, base, target, cap)


def clock(program: Any, symbol: str) -> Callable[[], float]:
    fn = program.get_exported_function(f"alloy_seconds_{symbol}", ctypes.c_double)
    if fn is None:
        raise RuntimeError(f"{program.filename} has no timer for {symbol}")
    return fn


def time_arms(folders: list[str], symbol: str, args: dict[str, Any], reps: int) -> list[list[float]]:
    """In a child: one warmup, then ``reps`` rounds calling every arm on the same buffers, reversed every other
    round; every array is reset before each call. Seconds per arm, from the region timer or the whole call."""
    from dace.codegen import compiler  # noqa: PLC0415 -- preloaded by the fork server

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
    # shortcut: holds every arm's outputs until judged; judge as they complete if arms x outputs nears memory
    with Children() as children:
        pending = {name: children.submit(folder, draw, arms.outputs) for name, folder in arms.folders.items()}
        first = next(iter(pending.values())).result()
        if isinstance(first, str):
            raise RuntimeError(f"the reference crashed at {draw.sizes}: {first}")  # noqa: TRY004 -- a crash, not a bad type
        ref = Reference([first], arms.nondeterministic)
        return {name: judge(arms.tolerances[name], ref, [f.result()], [length]) for name, f in pending.items()}


def measure(arms: Arms, draw: Draw, length: int, cpus: tuple[int, ...], reps: int) -> dict[str, Measured]:
    """Check every arm at ``draw``'s size, then time the passing ones together on ``cpus``."""
    verdicts = check(arms, draw, length)
    passing = [name for name in arms.folders if verdicts[name].ok]
    args = {**draw.values, **draw.sizes}
    times = in_child(time_arms, ([str(arms.folders[n]) for n in passing], arms.symbol, args, reps), cpus)
    if isinstance(times, str):
        raise RuntimeError(f"timing {arms.symbol or 'the program'} failed: {times}")  # noqa: TRY004 -- a crash, not a bad type
    measured = {name: Measured(*median_ci(t), verdicts[name]) for name, t in zip(passing, times, strict=True)}
    return {name: measured.get(name, Measured(math.nan, math.nan, math.nan, v)) for name, v in verdicts.items()}


def time_region(linker: Linker, rep: RegionReport, verification: Verification, manifest: Manifest) -> RegionTiming:
    """Screen every verified distinct candidate, re-time the fastest on every core, and pick the winner: the
    fastest whose CI lies below the reference's, else the reference."""
    matrix, symbol = linker.matrix, rep.region.symbol
    verified = [
        b
        for b in rep.builds[1:]
        if (symbol, b.name) in verification.programs and verification.verdicts[symbol][b.name].ok
    ]
    arms = Arms(
        {REFERENCE: verification.reference} | {b.name: verification.programs[symbol, b.name] for b in verified},
        {REFERENCE: "exact"} | {b.name: matrix.fp_levels[b.candidate.resolved(matrix)[1]].tolerance for b in verified},
        symbol,
        manifest.outputs,
        verification.nondeterministic,
    )
    t, cores = matrix.timing, machine.physical_cores()
    original, cap = linker.program.original, t.max_program_cache_factor
    screen_sizes = stage_sizes(rep.region.sdfg, original, manifest, t.screen_cache_factor, cap, grow_only=False)
    final_sizes = stage_sizes(rep.region.sdfg, original, manifest, t.final_cache_factor, cap, grow_only=True)
    screen = measure(
        arms, inputs.at(manifest, screen_sizes), length(linker, screen_sizes), cores[: t.screen_cores], t.screen_reps
    )
    ranked = sorted((n for n in screen if n != REFERENCE and screen[n].verdict.ok), key=lambda n: screen[n].median)
    keep = [REFERENCE, *ranked[: t.top]]
    top = Arms({n: arms.folders[n] for n in keep}, arms.tolerances, symbol, arms.outputs, arms.nondeterministic)
    final = measure(top, inputs.at(manifest, final_sizes), length(linker, final_sizes), cores, t.final_reps)
    best = min((n for n in ranked[: t.top] if final[n].verdict.ok), key=lambda n: final[n].median, default=REFERENCE)
    winner = best if final[best].high < final[REFERENCE].low else REFERENCE
    return RegionTiming(screen, final, winner, screen_sizes, final_sizes)


def length(linker: Linker, sizes: dict[str, int]) -> int:
    return accumulation_length(linker.program, sizes)


def time_program(
    linker: Linker, reports: list[RegionReport], verification: Verification, manifest: Manifest
) -> tuple[dict[str, RegionTiming], ProgramTiming]:
    """Every region's timing, then alloy-full against DaCe's default codegen on every core."""
    regions = {rep.region.symbol: time_region(linker, rep, verification, manifest) for rep in reports}
    winners = {rep.region.symbol: winning_build(rep, regions[rep.region.symbol].winner) for rep in reports}
    compilers = frozenset(b.candidate.compiler for b in winners.values())
    archives = {symbol: b.archive for symbol, b in winners.items() if b.archive}
    arms = Arms(
        {"dace_default": linker.compile_default(), "alloy_full": linker.compile(archives, "alloy_full", compilers)},
        {"dace_default": "exact", "alloy_full": "band"},
        "",
        manifest.outputs,
        frozenset(manifest.outputs),  # alloy-full mixes FP levels per region: compare every output by band
    )
    t, original = linker.matrix.timing, linker.program.original
    sizes = stage_sizes(original, original, manifest, t.final_cache_factor, t.max_program_cache_factor, grow_only=True)
    program = measure(arms, inputs.at(manifest, sizes), length(linker, sizes), machine.physical_cores(), t.final_reps)
    return regions, ProgramTiming(program, sizes)


def winning_build(rep: RegionReport, winner: str) -> Build:
    return rep.builds[0] if winner == REFERENCE else next(b for b in rep.builds if b.name == winner)
