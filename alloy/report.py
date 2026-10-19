# Copyright 2026 ETH Zurich and the Alloy authors.
"""Write the per-region report (Markdown + JSON) of a sweep and, when it ran, its verification; read the JSON back
(:func:`load`)."""

import pathlib
import shutil

from pydantic.dataclasses import dataclass

from alloy.backend.build import Build
from alloy.backend.sweep import RegionReport
from alloy.configuration_matrix import Matrix
from alloy.evaluate.link import Best
from alloy.evaluate.timing import REFERENCE, Measured, ProgramTiming, RegionTiming, Timings
from alloy.evaluate.verify import Status, Verdict, Verification
from alloy.records import RECORD, Strings, dumped_json, validated_json

#: ``{region symbol: {candidate name: verdict}}``; empty when no manifest was given.
Verdicts = dict[str, dict[str, Verdict]]


def verdict_text(verdict: Verdict | None) -> str:
    if verdict is None:
        return "-"
    if verdict.status == "pass":
        return f"pass {verdict.error:.1e}"
    return verdict.status


def row(b: Build, verdict: Verdict | None) -> str:
    status = "error" if b.error else (f"= {b.duplicate_of}" if b.duplicate_of else "built")
    missed = b.remarks.missed[0] if b.remarks.missed else ""
    return (
        f"| {b.candidate.language} | {b.candidate.compiler} | {b.candidate.note} | {status} | {verdict_text(verdict)} "
        f"| {b.remarks.vectorized} | {len(b.remarks.missed)} | {missed} |"
    )


def best_lines(best: Best) -> list[str]:
    """How ``best/`` links the program: each region's winner with its compiler and flags, then the link line."""
    lines = [
        "## Linked program (`best/`: `make` builds it)",
        "",
        "| region | candidate | compiler | flags |",
        "|---|---|---|---|",
    ]
    lines += [f"| {r.symbol} | {r.candidate} | {r.compiler} | `{' '.join(r.flags)}` |" for r in best.regions]
    return [*lines, "", f"Entry arguments: {', '.join(best.arguments)}. Link: `{' '.join(best.link)}`", ""]


def markdown(
    reports: list[RegionReport],
    matrix: Matrix,
    verdicts: Verdicts,
    unstable: list[str],
    timing: Timings | None,
    best: Best | None,
) -> str:
    lines = ["# Alloy build report", ""]
    if unstable:
        note = "Nondeterministic outputs (differ between reference runs, always compared by band)"
        lines += [f"{note}: {', '.join(unstable)}", ""]
    lines += [f"OpenMP runtime: {matrix.defaults.openmp_runtime}", ""]
    lines += program_lines(timing.program) if timing else []
    lines += best_lines(best) if best else []
    _, skipped = matrix.usable_compilers()
    lines += [f"Skipped compiler {name}: {reason}" for name, reason in skipped.items()]
    lines += [""] if skipped else []
    for rep in reports:
        r = rep.region
        unique = sum(1 for b in rep.builds if not b.error and not b.duplicate_of)
        lines += [
            f"## {r.symbol}",
            "",
            f"`{r.signature}`",
            "",
            f"libm calls: {r.calls_libm}; reduction: {r.has_reduction}; accumulation length: {r.accumulation_length}; "
            f"{len(rep.builds)} candidates, {unique} distinct objects.",
            "",
            "| lang | compiler | change | object | verified | vectorized | missed | first missed reason |",
            "|---|---|---|---|---|---|---|---|",
        ]
        mine = verdicts.get(r.symbol, {})
        lines += [row(b, mine.get(b.name)) for b in rep.builds]
        lines.append("")
        lines += runtime_matrix(rep, timing.regions[r.symbol], matrix) if timing else []
        lines += timing_lines(timing.regions[r.symbol]) if timing else []
    return "\n".join(lines)


def runtime_matrix(rep: RegionReport, timing: RegionTiming, matrix: Matrix) -> list[str]:
    """The screened candidates as code variant (row) x build config (column): ``ms (speedup over the reference)``,
    ``*`` when re-timed, the verdict when it failed, ``-`` when not screened (not swept, duplicate or not verified)."""
    ref = timing.screen[REFERENCE].median
    cells: dict[str, dict[str, str]] = {}
    for b in rep.builds:
        m = timing.screen.get(REFERENCE if b is rep.builds[0] else b.name)
        text = "-" if m is None else m.verdict.status
        if m is not None and m.verdict.ok:
            text = f"{1e3 * m.median:.3f} ({ref / m.median:.2f}x){'*' if b.name in timing.final else ''}"
        cells.setdefault(b.source.stem, {})[b.candidate.config_name(matrix)] = text
    configs = list(dict.fromkeys(c for row in cells.values() for c in row))
    lines = ["| variant | " + " | ".join(configs) + " |", "|---" * (len(configs) + 1) + "|"]
    lines += [f"| {v} | " + " | ".join(row.get(c, "-") for c in configs) + " |" for v, row in cells.items()]
    return ["Screened ms (speedup), variant x build config:", "", *lines, ""]


def ms(m: Measured) -> str:
    return f"{1e3 * m.median:.3f} [{1e3 * m.low:.3f}, {1e3 * m.high:.3f}]"


def timing_lines(timing: RegionTiming) -> list[str]:
    """The re-timed arms against the reference, with the screening median and the winner."""
    ref = timing.final["reference"].median
    lines = [
        f"Timing: screened at {timing.screen_sizes}, re-timed at {timing.final_sizes}. Winner: **{timing.winner}**.",
        "",
        "| candidate | screen ms | final ms [95% CI] | speedup | outputs at size |",
        "|---|---|---|---|---|",
    ]
    for name, m in timing.final.items():
        screen = f"{1e3 * timing.screen[name].median:.3f}"
        lines.append(f"| {name} | {screen} | {ms(m)} | {ref / m.median:.2f}x | {verdict_text(m.verdict)} |")
    return [*lines, ""]


def program_lines(program: ProgramTiming) -> list[str]:
    default, full = program.arms["dace_default"], program.arms["alloy_full"]
    return [
        f"Program at {program.sizes}: DaCe default {ms(default)} ms, alloy-full {ms(full)} ms "
        f"({verdict_text(full.verdict)}), speedup {default.median / full.median:.2f}x.",
        "",
    ]


@dataclass(slots=True, frozen=True, config=RECORD)
class VerdictRecord:
    """A candidate's verdict in ``report.json``: ``detail`` is ``None`` when the verdict gives none."""

    status: Status
    max_rel_error: float
    detail: str | None


@dataclass(slots=True, frozen=True, config=RECORD)
class CandidateRecord:
    """One built candidate in ``report.json``. ``archive`` is ``None`` when the build failed, ``duplicate_of`` and
    ``error`` are ``None`` when empty, and ``verdict`` is ``None`` when the candidate was not verified."""

    name: str
    change: str
    variant: str
    config: str
    flags: Strings
    codegen_params: dict[str, str]
    source: pathlib.Path
    archive: pathlib.Path | None
    object_hash: str
    duplicate_of: str | None
    vectorized_loops: int
    missed: Strings
    error: str | None
    verdict: VerdictRecord | None


@dataclass(slots=True, frozen=True, config=RECORD)
class RegionRecord:
    """One outlined region and its candidates in ``report.json``; ``accumulation_length`` is a sympy expression."""

    symbol: str
    signature: str
    abi_order: Strings
    calls_libm: bool
    has_reduction: bool
    accumulation_length: str
    candidates: tuple[CandidateRecord, ...]


@dataclass(slots=True, frozen=True, config=RECORD)
class Report:
    """``report.json``: outputs the reference does not reproduce, every region, and the timings (``None`` when the
    sweep was not timed)."""

    nondeterministic_outputs: Strings
    regions: tuple[RegionRecord, ...]
    timing: Timings | None


def verdict_record(verdict: Verdict | None) -> VerdictRecord | None:
    if verdict is None:
        return None
    return VerdictRecord(status=verdict.status, max_rel_error=verdict.error, detail=verdict.detail or None)


def candidate_record(b: Build, verdict: Verdict | None, matrix: Matrix) -> CandidateRecord:
    return CandidateRecord(
        name=b.name,
        change=b.candidate.note,
        variant=b.source.stem,
        config=b.candidate.config_name(matrix),
        flags=b.flags,
        codegen_params=b.codegen_params,
        source=b.source,
        archive=b.archive,
        object_hash=b.object_hash,
        duplicate_of=b.duplicate_of or None,
        vectorized_loops=b.remarks.vectorized,
        missed=b.remarks.missed,
        error=b.error or None,
        verdict=verdict_record(verdict),
    )


def region_records(reports: list[RegionReport], verdicts: Verdicts, matrix: Matrix) -> tuple[RegionRecord, ...]:
    return tuple(
        RegionRecord(
            symbol=rep.region.symbol,
            signature=rep.region.signature,
            abi_order=rep.region.abi_order,
            calls_libm=rep.region.calls_libm,
            has_reduction=rep.region.has_reduction,
            accumulation_length=str(rep.region.accumulation_length),
            candidates=tuple(
                candidate_record(b, verdicts.get(rep.region.symbol, {}).get(b.name), matrix) for b in rep.builds
            ),
        )
        for rep in reports
    )


def write(
    reports: list[RegionReport],
    matrix: Matrix,
    out: pathlib.Path,
    verification: Verification | None = None,
    timing: Timings | None = None,
    best: Best | None = None,
) -> None:
    """Write ``report.md`` and ``report.json``, with a copy of the matrix that produced them."""
    verdicts = verification.verdicts if verification else {}
    unstable = sorted(verification.nondeterministic) if verification else []
    shutil.copyfile(matrix.path, out / "configuration_matrix.toml")
    (out / "report.md").write_text(markdown(reports, matrix, verdicts, unstable, timing, best))
    payload = Report(
        nondeterministic_outputs=tuple(unstable), regions=region_records(reports, verdicts, matrix), timing=timing
    )
    (out / "report.json").write_text(dumped_json(payload))


def load(path: pathlib.Path) -> Report:
    """The ``report.json`` at ``path``."""
    return validated_json(Report, path)
