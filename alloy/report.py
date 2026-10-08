# Copyright 2026 ETH Zurich and the Alloy authors.
"""Write the per-region report (Markdown + JSON) of a sweep and, when it ran, its verification."""

import json
import pathlib
import shutil

from alloy.build import Build
from alloy.configuration_matrix import Matrix
from alloy.sweep import RegionReport
from alloy.verify import Verdict, Verification

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


def markdown(reports: list[RegionReport], matrix: Matrix, verdicts: Verdicts) -> str:
    lines = ["# Alloy build report", "", f"OpenMP runtime: {matrix.defaults.openmp_runtime}", ""]
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
    return "\n".join(lines)


def verdict_json(verdict: Verdict | None) -> dict | None:
    if verdict is None:
        return None
    return {"status": verdict.status, "max_rel_error": verdict.error, "detail": verdict.detail or None}


def as_json(reports: list[RegionReport], verdicts: Verdicts) -> list[dict]:
    return [
        {
            "symbol": rep.region.symbol,
            "signature": rep.region.signature,
            "abi_order": list(rep.region.abi_order),
            "calls_libm": rep.region.calls_libm,
            "has_reduction": rep.region.has_reduction,
            "accumulation_length": str(rep.region.accumulation_length),
            "candidates": [
                {
                    "name": b.name,
                    "change": b.candidate.note,
                    "flags": list(b.flags),
                    "codegen_params": b.codegen_params,
                    "source": str(b.source),
                    "archive": str(b.archive) if b.archive else None,
                    "object_hash": b.object_hash,
                    "duplicate_of": b.duplicate_of or None,
                    "vectorized_loops": b.remarks.vectorized,
                    "missed": list(b.remarks.missed),
                    "error": b.error or None,
                    "verdict": verdict_json(verdicts.get(rep.region.symbol, {}).get(b.name)),
                }
                for b in rep.builds
            ],
        }
        for rep in reports
    ]


def write(
    reports: list[RegionReport], matrix: Matrix, out: pathlib.Path, verification: Verification | None = None
) -> None:
    """Write ``report.md`` and ``report.json``, with a copy of the matrix that produced them."""
    verdicts = verification.verdicts if verification else {}
    unstable = sorted(verification.nondeterministic) if verification else []
    shutil.copyfile(matrix.path, out / "configuration_matrix.toml")
    text = markdown(reports, matrix, verdicts)
    if unstable:
        note = (
            f"Nondeterministic outputs (differ between reference runs, always compared by band): {', '.join(unstable)}"
        )
        text = text.replace("\n\n", f"\n\n{note}\n\n", 1)
    (out / "report.md").write_text(text)
    payload = {"nondeterministic_outputs": unstable, "regions": as_json(reports, verdicts)}
    (out / "report.json").write_text(json.dumps(payload, indent=2))
