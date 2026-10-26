# Copyright 2026 ETH Zurich and the Alloy authors.
"""The report of one Alloy run: the program's control-flow tree, every scope with its own tree and its top-k
variants against its baseline (the matrix-default build), and the verdict -- scope x build config, the chosen
candidate per scope and the full compile and link argv. ``report.json`` is the record; ``report.md`` is rendered
from it, and :func:`load` reads the JSON back."""

import enum
import math
import pathlib
import shutil

from pydantic.dataclasses import dataclass

from alloy.backend.build import Build
from alloy.backend.sweep import ScopeReport
from alloy.configuration_matrix import Matrix
from alloy.evaluate.link import Commands
from alloy.evaluate.timing import REFERENCE, Measured, ScopeTiming, Timings
from alloy.evaluate.verify import Status, Verdict, Verification
from alloy.frontend import tree
from alloy.frontend.scopes import Program
from alloy.frontend.tree import CfgNode
from alloy.records import RECORD, Parameters, Strings, dumped_json, validated_json

#: The report layout; a reader refuses any other.
SCHEMA = 2
#: Variants listed per scope unless the caller asks for another count.
TOP_K = 5
#: Missed-vectorization remarks kept per variant.
MISSED_SHOWN = 3

#: ``{scope symbol: {candidate name: verdict}}``; empty when no manifest was given.
Verdicts = dict[str, dict[str, Verdict]]


class Mode(enum.StrEnum):
    #: Candidates verified and timed; variants ranked by time.
    PROFILE = "profile"
    #: Candidates verified, not timed; picked from the builds' reports and outputs.
    SPECULATIVE = "speculative"


@dataclass(slots=True, frozen=True, config=RECORD)
class Correctness:
    """A variant's verification: ``detail`` is ``None`` when the verdict gives none."""

    status: Status
    max_rel_error: float
    detail: str | None


@dataclass(slots=True, frozen=True, config=RECORD)
class Time:
    """Median milliseconds with its 95% CI; NaN when the arm's outputs failed at the timed size."""

    median_ms: float
    low_ms: float
    high_ms: float


@dataclass(slots=True, frozen=True, config=RECORD)
class Variant:
    """One build of a scope: its candidate, how it is built, what the compiler said, whether it is correct, and its
    times (screened, and re-timed for the top ones) with the speedup over the scope's baseline."""

    rank: int
    name: str
    change: str
    variant: str
    config: str
    language: str
    compiler: str
    flags: Strings
    codegen_params: dict[str, str]
    source: pathlib.Path
    object_hash: str
    vectorized_loops: int
    missed: Strings
    correctness: Correctness | None
    screen: Time | None
    final: Time | None
    speedup: float | None


@dataclass(slots=True, frozen=True, config=RECORD)
class ScopeRecord:
    """One outlined scope: its entry, traits, own control-flow tree, how many candidates were built and why the
    others dropped out, its baseline time and its top variants; ``accumulation_length`` is a sympy expression."""

    symbol: str
    signature: str
    abi_order: Strings
    calls_libm: bool
    has_reduction: bool
    accumulation_length: str
    tree: CfgNode
    candidates: int
    dropped: dict[str, int]
    baseline: Time | None
    top: tuple[Variant, ...]


@dataclass(slots=True, frozen=True, config=RECORD)
class MatrixRow:
    """One scope's row of the verdict matrix: config -> ``ms (speedup)``, or why that config has no time."""

    scope: str
    cells: dict[str, str]


@dataclass(slots=True, frozen=True, config=RECORD)
class ProgramRecord:
    """The whole program: DaCe's default build (the baseline) against the linked winners, at ``sizes``."""

    sizes: Parameters
    baseline: Time
    alloy: Time
    speedup: float
    correctness: Correctness


@dataclass(slots=True, frozen=True, config=RECORD)
class Final:
    """The verdict: the chosen candidate per scope, scope x build config, the argv that builds the chosen program,
    and the program's speedup; the last two ``None`` when the run was not timed."""

    chosen: dict[str, str]
    configs: Strings
    matrix: tuple[MatrixRow, ...]
    commands: Commands | None
    program: ProgramRecord | None


@dataclass(slots=True, frozen=True, config=RECORD)
class Report:
    """``report.json``."""

    schema: int
    mode: Mode
    program: str
    tree: CfgNode
    nondeterministic_outputs: Strings
    scopes: tuple[ScopeRecord, ...]
    verdict: Final
    timing: Timings | None


def as_time(measured: Measured | None) -> Time | None:
    if measured is None:
        return None
    return Time(median_ms=1e3 * measured.median, low_ms=1e3 * measured.low, high_ms=1e3 * measured.high)


def correctness(verdict: Verdict | None) -> Correctness | None:
    if verdict is None:
        return None
    return Correctness(status=verdict.status, max_rel_error=verdict.error, detail=verdict.detail or None)


def arm(rep: ScopeReport, b: Build) -> str:
    """The timing key of ``b``: the scope's first build is timed as the reference."""
    return REFERENCE if b is rep.builds[0] else b.name


def drop_reason(rep: ScopeReport, b: Build, verdict: Verdict | None, timing: ScopeTiming | None) -> str | None:
    """Why ``b`` cannot be ranked, or ``None`` when it can."""
    if b.error:
        return "build_failed"
    if b.duplicate_of:
        return "duplicate"
    if verdict is not None and not verdict.ok:
        return verdict.status
    if timing is not None and arm(rep, b) not in timing.screen:
        return "not_screened"
    return None


def ranked(rep: ScopeReport, verdicts: dict[str, Verdict], timing: ScopeTiming | None) -> list[Build]:
    """The rankable builds, fastest screened first; untimed runs keep sweep order."""
    usable = [b for b in rep.builds if drop_reason(rep, b, verdicts.get(b.name), timing) is None]
    if timing is None:
        return usable
    return sorted(usable, key=lambda b: (math.isnan(m := timing.screen[arm(rep, b)].median), m))


def variant(
    rep: ScopeReport, b: Build, rank: int, verdict: Verdict | None, timing: ScopeTiming | None, matrix: Matrix
) -> Variant:
    screen = timing.screen.get(arm(rep, b)) if timing else None
    final = timing.final.get(arm(rep, b)) if timing else None
    base = timing.screen[REFERENCE].median if timing else math.nan
    return Variant(
        rank=rank,
        name=b.name,
        change=b.candidate.note,
        variant=b.source.stem,
        config=b.candidate.config_name(matrix),
        language=b.candidate.language,
        compiler=b.candidate.compiler,
        flags=b.flags,
        codegen_params=b.codegen_params,
        source=b.source,
        object_hash=b.object_hash,
        vectorized_loops=b.remarks.vectorized,
        missed=b.remarks.missed[:MISSED_SHOWN],
        correctness=correctness(verdict),
        screen=as_time(screen),
        final=as_time(final),
        speedup=base / screen.median if screen is not None and timing else None,
    )


def scope_record(
    rep: ScopeReport, verdicts: dict[str, Verdict], timing: ScopeTiming | None, matrix: Matrix, k: int
) -> ScopeRecord:
    dropped: dict[str, int] = {}
    for b in rep.builds:
        reason = drop_reason(rep, b, verdicts.get(b.name), timing)
        if reason is not None:
            dropped[reason] = dropped.get(reason, 0) + 1
    top = ranked(rep, verdicts, timing)[:k]
    s = rep.scope
    return ScopeRecord(
        symbol=s.symbol,
        signature=s.signature,
        abi_order=s.abi_order,
        calls_libm=s.calls_libm,
        has_reduction=s.has_reduction,
        accumulation_length=str(s.accumulation_length),
        tree=tree.cfg_tree(s.sdfg),
        candidates=len(rep.builds),
        dropped=dropped,
        baseline=as_time(timing.screen[REFERENCE]) if timing else None,
        top=tuple(variant(rep, b, rank, verdicts.get(b.name), timing, matrix) for rank, b in enumerate(top, start=1)),
    )


def matrix_row(rep: ScopeReport, verdicts: dict[str, Verdict], timing: ScopeTiming | None, matrix: Matrix) -> MatrixRow:
    """Per build config, the fastest rankable build in it as ``ms (speedup)``; else the first reason none is."""
    cells: dict[str, str] = {}
    best: dict[str, float] = {}
    base = timing.screen[REFERENCE].median if timing else math.nan
    for b in rep.builds:
        config = b.candidate.config_name(matrix)
        reason = drop_reason(rep, b, verdicts.get(b.name), timing)
        if reason is not None or timing is None:
            cells.setdefault(config, reason or "built")
            continue
        median = timing.screen[arm(rep, b)].median
        if config not in best or median < best[config]:
            best[config] = median
            cells[config] = f"{1e3 * median:.3f} ({base / median:.2f}x)"
    return MatrixRow(scope=rep.scope.symbol, cells=cells)


def final(
    reports: list[ScopeReport], verdicts: Verdicts, timing: Timings | None, commands: Commands | None, matrix: Matrix
) -> Final:
    rows = tuple(
        matrix_row(
            rep, verdicts.get(rep.scope.symbol, {}), timing.scopes.get(rep.scope.symbol) if timing else None, matrix
        )
        for rep in reports
    )
    configs = tuple(dict.fromkeys(config for row in rows for config in row.cells))
    chosen = {}
    for rep in reports:
        winner = timing.scopes[rep.scope.symbol].winner if timing else REFERENCE
        chosen[rep.scope.symbol] = rep.builds[0].name if winner == REFERENCE else winner
    program = None
    if timing is not None:
        default, full = timing.program.arms["dace_default"], timing.program.arms["alloy_full"]
        verdict = correctness(full.verdict)
        assert verdict is not None, "a timed program arm carries its verdict"
        baseline, alloy = as_time(default), as_time(full)
        assert baseline is not None and alloy is not None, "both program arms are timed"
        program = ProgramRecord(
            sizes=timing.program.sizes,
            baseline=baseline,
            alloy=alloy,
            speedup=default.median / full.median,
            correctness=verdict,
        )
    return Final(chosen=chosen, configs=configs, matrix=rows, commands=commands, program=program)


def assemble(
    program: Program,
    reports: list[ScopeReport],
    matrix: Matrix,
    verification: Verification | None = None,
    timing: Timings | None = None,
    commands: Commands | None = None,
    top_k: int = TOP_K,
) -> Report:
    """The report of one run; profile mode (the only one Alloy runs today)."""
    verdicts = verification.verdicts if verification else {}
    scopes = tuple(
        scope_record(
            rep,
            verdicts.get(rep.scope.symbol, {}),
            timing.scopes.get(rep.scope.symbol) if timing else None,
            matrix,
            top_k,
        )
        for rep in reports
    )
    return Report(
        schema=SCHEMA,
        mode=Mode.PROFILE,
        program=program.sdfg.name,
        tree=tree.cfg_tree(program.sdfg),
        nondeterministic_outputs=tuple(sorted(verification.nondeterministic)) if verification else (),
        scopes=scopes,
        verdict=final(reports, verdicts, timing, commands, matrix),
        timing=timing,
    )


def time_text(t: Time | None) -> str:
    return "-" if t is None else f"{t.median_ms:.3f} [{t.low_ms:.3f}, {t.high_ms:.3f}]"


def variant_row(v: Variant) -> str:
    status = "-" if v.correctness is None else v.correctness.status
    speedup = "-" if v.speedup is None else f"{v.speedup:.2f}x"
    missed = v.missed[0] if v.missed else ""
    return (
        f"| {v.rank} | {v.name} | {v.config} | {status} | {time_text(v.screen)} | {time_text(v.final)} | {speedup} "
        f"| {v.vectorized_loops} | {missed} |"
    )


def scope_lines(s: ScopeRecord) -> list[str]:
    dropped = ", ".join(f"{reason} {count}" for reason, count in s.dropped.items()) or "none"
    return [
        f"## {s.symbol}",
        "",
        f"`{s.signature}`",
        "",
        f"libm calls: {s.calls_libm}; reduction: {s.has_reduction}; accumulation length: {s.accumulation_length}; "
        f"{s.candidates} candidates, dropped: {dropped}. Baseline (matrix default): {time_text(s.baseline)} ms.",
        "",
        "```",
        tree.render(s.tree),
        "```",
        "",
        "| rank | candidate | config | verified | screen ms | final ms | speedup | vectorized | first missed |",
        "|---|---|---|---|---|---|---|---|---|",
        *(variant_row(v) for v in s.top),
        "",
    ]


def verdict_lines(v: Final) -> list[str]:
    lines = [
        "## Verdict",
        "",
        "| scope | chosen | " + " | ".join(v.configs) + " |",
        "|---" * (len(v.configs) + 2) + "|",
    ]
    lines += [
        f"| {row.scope} | {v.chosen[row.scope]} | " + " | ".join(row.cells.get(c, "-") for c in v.configs) + " |"
        for row in v.matrix
    ]
    lines.append("")
    if v.program is not None:
        p = v.program
        lines += [
            f"Program at {dict(p.sizes)}: DaCe default {time_text(p.baseline)} ms, Alloy {time_text(p.alloy)} ms "
            f"({p.correctness.status}), speedup {p.speedup:.2f}x.",
            "",
        ]
    if v.commands is not None:
        lines += ["Build (`best/`, `make` runs these):", "", "```"]
        lines += [" ".join(argv) for argv in v.commands.compile.values()]
        lines += [" ".join(v.commands.link), "```", ""]
    return lines


def markdown(r: Report, matrix: Matrix) -> str:
    """``report.md``: rendered from the record, nothing else."""
    lines = [f"# Alloy report: {r.program} ({r.mode})", "", "```", tree.render(r.tree), "```", ""]
    if r.nondeterministic_outputs:
        note = "Nondeterministic outputs (differ between reference runs, always compared by band)"
        lines += [f"{note}: {', '.join(r.nondeterministic_outputs)}", ""]
    lines += [f"OpenMP runtime: {matrix.defaults.openmp_runtime}", ""]
    _, skipped = matrix.usable_compilers()
    lines += [f"Skipped compiler {name}: {reason}" for name, reason in skipped.items()]
    lines += [""] if skipped else []
    for s in r.scopes:
        lines += scope_lines(s)
    return "\n".join([*lines, *verdict_lines(r.verdict)])


def write(
    program: Program,
    reports: list[ScopeReport],
    matrix: Matrix,
    out: pathlib.Path,
    verification: Verification | None = None,
    timing: Timings | None = None,
    commands: Commands | None = None,
    top_k: int = TOP_K,
) -> Report:
    """Write ``report.json`` and ``report.md`` (rendered from it), with a copy of the matrix that produced them."""
    shutil.copyfile(matrix.path, out / "configuration_matrix.toml")
    r = assemble(program, reports, matrix, verification, timing, commands, top_k)
    (out / "report.json").write_text(dumped_json(r))
    (out / "report.md").write_text(markdown(r, matrix))
    return r


def load(path: pathlib.Path) -> Report:
    """The ``report.json`` at ``path``; any other schema version is refused."""
    r = validated_json(Report, path)
    if r.schema != SCHEMA:
        raise ValueError(f"{path}: report schema {r.schema}, this Alloy reads {SCHEMA}")
    return r
