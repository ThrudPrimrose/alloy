# Copyright 2026 ETH Zurich and the Alloy authors.
"""Renders the ISA table into markdown skill pages — the agent-facing context generated from the
single source of truth (``intrinsics.toml``). Run ``python -m alloy.isa.render`` after changing the
table; never edit the pages by hand."""

import argparse
import pathlib

from alloy.isa.table import ALL_DTYPES, F16, Table, load

__all__ = ["render"]

#: The default page folder, inside the shipped skill.
DEFAULT_OUT = pathlib.Path(__file__).parent.parent.parent / "skills" / "alloy" / "isa"


def _entry_row(op: str, entry) -> str:
    if entry.approximations:
        spelling = f"{len(entry.approximations)} polynomial tiers (see transcendentals.md)"
        mnemonic = "—"
    elif entry.intrinsic:
        spelling = f"`{entry.intrinsic}`"
        mnemonic = f"`{entry.mnemonic}`"
    else:
        steps = " -> ".join(entry.recipe[:3]) + (" -> ..." if len(entry.recipe) > 3 else "")
        spelling = f"recipe: {steps}"
        mnemonic = f"`{entry.mnemonic}`"
    masked = f"`{entry.masked}`" if entry.masked else "—"
    signature = f"`{entry.signature}`" if entry.signature else "—"
    return f"| `{op}` | {spelling} | {mnemonic} | {signature} | {masked} |"


def _dtype_section(isa_name: str, dtype: str, entries: dict[str, object]) -> list[str]:
    title = {"f64": "f64", "f32": "f32", F16: "f16", "i64": "i64 (integer lanes)", "i32": "i32 (integer lanes)"}[dtype]
    lines = [f"### {title}", "", "| op | spelling | mnemonic | signature | masked |", "|---|---|---|---|---|"]
    lines += [_entry_row(op, entry) for op, entry in entries.items()]
    lines.append("")
    return lines


def render_isa(table: Table, isa_name: str) -> str:
    """One ISA page: machine model, the op matrix per dtype, and the traps."""
    isa = table.isa(isa_name)
    mask = "opmask/predicate" if isa.mask else "no predication"
    lines = [f"# {isa_name} — {isa.title}", ""]
    lanes = ", ".join(f"{d}: {isa.lanes[d] or 'runtime'}" for d in ALL_DTYPES if d in isa.lanes)
    lines += [f"Vector bytes: {isa.vector_bytes or 'length-agnostic'}; lanes: {lanes}; {mask}.", ""]
    lines += [
        f"Legal schedules: {', '.join(isa.schedules)}. gen_mask: {isa.gen_mask or 'unsupported (no predication)'}.",
        "",
    ]
    for name in isa.schedules:
        info = table.schedule_info[name]
        lines.append(f"- **{name}** ({info.title}): {info.description} Tail: {info.tail}.")
        if info.gcc:
            lines.append(f"  - gcc: {info.gcc}")
        if info.clang:
            lines.append(f"  - clang: {info.clang}")
    lines.append("")
    if isa.embedded_broadcast:
        lines += [
            "A scalar operand fuses into any arithmetic instruction as an EVEX embedded broadcast "
            "(`{1to8}`/`{1to16}`) when it comes from memory; a register scalar broadcasts explicitly.",
            "",
        ]
    lines += [isa.note, ""]
    for dtype in ALL_DTYPES:
        entries = getattr(isa, dtype, {})
        if entries:
            lines += _dtype_section(isa_name, dtype, entries)
    if isa.assists:
        lines += ["## Hardware assists", "", "| intrinsic | mnemonic | helps | note |", "|---|---|---|---|"]
        lines += [f"| `{a.name}` | `{a.mnemonic}` | {a.helps} | {a.note} |" for a in isa.assists]
        lines.append("")
    traps = [
        (op, dtype, entry)
        for dtype in ALL_DTYPES
        for op, entry in getattr(isa, dtype, {}).items()
        if "trap" in entry.note
    ]
    if traps:
        lines += ["## Traps", ""]
        for op, dtype, entry in traps:
            lines.append(f"- **{op}** ({dtype}): {entry.note}")
        lines.append("")
    return "\n".join(lines)


def render_index(table: Table) -> str:
    lines = [
        "# Alloy ISA reference (generated from intrinsics.toml — do not edit)",
        "",
        "The machine abstract math ISA and its per-target spellings. The abstract ops:",
        "",
        "| op | math | kind | result |",
        "|---|---|---|---|",
    ]
    from alloy.isa import OPS

    lines += [f"| `{op.name}` | {op.semantics} | {op.kind} | {op.result} |" for op in OPS.values()]
    lines += [
        "",
        "Dtypes: `f64`/`f32` everywhere, `f16` where the hardware has it, `i64`/`i32` for the "
        "integer ops. A scalar operand of a binary op is broadcast.",
        "",
        "## Pages",
        "",
    ]
    for name in table.isas:
        isa = table.isas[name]
        lines.append(f"- [`{name}.md`]({name}.md) — {isa.title}")
    lines += [
        "- [`transcendentals.md`](transcendentals.md) — the exp/sin/cos polynomial tiers with "
        "measured ULP and the vector math library calls",
        "",
    ]
    return "\n".join(lines)


def render_transcendentals(table: Table) -> str:
    lines = [
        "# Transcendentals — polynomial tiers with measured ULP (generated, do not edit)",
        "",
        "ULP at function scale: max |approx − ref| / spacing(max(|ref|, 1.0)) against double-precision "
        "libm on dense grids; the reference's own 0.5 ulp is the floor. Recipes are Horner schemes in "
        "abstract-op steps (`fma`/`mul` with inline coefficients) — copyable implementations.",
        "",
        "| tier | op | domain | error (ulp) | error (abs) |",
        "|---|---|---|---|---|",
    ]
    for name, tier in table.approx.items():
        lines.append(f"| `{name}` | {tier.op} | {tier.domain} | {tier.error_ulp:.4g} | {tier.error_abs:.3g} |")
    lines += ["", "## Recipes", ""]
    for name, tier in table.approx.items():
        lines += [f"### {name}", "", "```", *tier.recipe, "```", ""]
        if tier.note:
            lines += [tier.note, ""]
    lines += [
        "## Vector math library calls",
        "",
        "| ISA | dtype | op | libmvec | SVML | SLEEF |",
        "|---|---|---|---|---|---|",
    ]
    for isa_name, isa in table.isas.items():
        for dtype in ("f64", "f32"):
            for op in ("exp", "sin", "cos"):
                entry = getattr(isa, dtype)[op]
                libs = entry.libraries
                lines.append(
                    f"| {isa_name} | {dtype} | {op} | `{libs.get('libmvec', '—')}` | "
                    f"`{libs.get('svml', '—')}` | `{libs.get('sleef', '—')}` |"
                )
    lines.append("")
    return "\n".join(lines)


def render(table: Table, out: pathlib.Path = DEFAULT_OUT) -> list[pathlib.Path]:
    """Write every page under ``out``; the paths written."""
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for name, content in [
        ("index", render_index(table)),
        ("transcendentals", render_transcendentals(table)),
        *[(n, render_isa(table, n)) for n in table.isas],
    ]:
        path = out / f"{name}.md"
        path.write_text(content + "\n", encoding="utf-8")
        written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="alloy.isa.render", description="Render the ISA table into skill pages.")
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT, help="the page folder")
    args = parser.parse_args(argv)
    for path in render(load(), args.out):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
