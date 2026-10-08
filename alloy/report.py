# Copyright 2026 ETH Zurich and the Alloy authors.
"""Write the per-region build report (Markdown + JSON) of a sweep."""

import json
import pathlib
import shutil

from alloy.build import Build
from alloy.configuration_matrix import Matrix
from alloy.sweep import RegionReport


def row(b: Build) -> str:
    status = "error" if b.error else (f"= {b.duplicate_of}" if b.duplicate_of else "built")
    missed = b.remarks.missed[0] if b.remarks.missed else ""
    return (
        f"| {b.candidate.language} | {b.candidate.compiler} | {b.candidate.note} | {status} "
        f"| {b.remarks.vectorized} | {len(b.remarks.missed)} | {missed} |"
    )


def markdown(reports: list[RegionReport], matrix: Matrix) -> str:
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
            "| lang | compiler | change | object | vectorized | missed | first missed reason |",
            "|---|---|---|---|---|---|---|",
        ]
        lines += [row(b) for b in rep.builds]
        lines.append("")
    return "\n".join(lines)


def as_json(reports: list[RegionReport]) -> list[dict]:
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
                }
                for b in rep.builds
            ],
        }
        for rep in reports
    ]


def write(reports: list[RegionReport], matrix: Matrix, out: pathlib.Path) -> None:
    """Write ``report.md`` and ``report.json``, with a copy of the matrix that produced them."""
    shutil.copyfile(matrix.path, out / "configuration_matrix.toml")
    (out / "report.md").write_text(markdown(reports, matrix))
    (out / "report.json").write_text(json.dumps(as_json(reports), indent=2))
