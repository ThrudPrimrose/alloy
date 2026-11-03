# Copyright 2026 ETH Zurich and the Alloy authors.
"""Renders the ISA table into markdown skill pages — the agent-facing context generated from the
single source of truth (``intrinsics.toml``). Run ``python -m alloy.isa.render`` after changing the
table; never edit the pages by hand."""

import argparse
import pathlib

from alloy.isa.mathkernels import LEVELS, functions, kernel
from alloy.isa.mathkernels import render as render_kernel
from alloy.isa.ops import OPS
from alloy.isa.table import ALL_DTYPES, DTYPES, F16, Entry, Table, load

__all__ = ["render"]

#: The default page folder, inside the shipped skill.
DEFAULT_OUT = pathlib.Path(__file__).parent.parent.parent / "skills" / "alloy" / "isa"


def cell(text: str) -> str:
    """``text`` safe in a markdown table cell."""
    return text.replace("|", "\\|")


def entry_row(op: str, entry: Entry) -> str:
    if entry.approximations:
        spelling = f"{len(entry.approximations)} polynomial tiers (see transcendentals.md)"
        mnemonic = "—"
    elif entry.intrinsic:
        spelling = f"`{entry.intrinsic}`"
        mnemonic = f"`{entry.mnemonic}`"
    else:
        spelling = cell(f"recipe: {'; '.join(f'`{line}`' for line in entry.code)}")
        mnemonic = f"`{entry.mnemonic}`"
    masked = f"`{entry.masked}`" if entry.masked else "—"
    signature = f"`{entry.signature}`" if entry.signature else "—"
    return (
        f"| `{op}` | {spelling} | {mnemonic} | {signature} | {masked} | {cell(entry.semantics)} | {cell(entry.note)} |"
    )


def dtype_section(dtype: str, entries: dict[str, Entry]) -> list[str]:
    title = {"f64": "f64", "f32": "f32", F16: "f16", "i64": "i64 (integer lanes)", "i32": "i32 (integer lanes)"}[dtype]
    header = "| op | spelling | mnemonic | signature | masked | semantics | note |"
    lines = [f"### {title}", "", header, "|---|---|---|---|---|---|---|"]
    lines += [entry_row(op, entry) for op, entry in entries.items()]
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
        if entries := isa.entries(dtype):
            lines += dtype_section(dtype, entries)
    if isa.assists:
        lines += ["## Hardware assists", "", "| intrinsic | mnemonic | helps | note |", "|---|---|---|---|"]
        lines += [f"| `{a.name}` | `{a.mnemonic}` | {a.helps} | {cell(a.note)} |" for a in isa.assists]
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
    lines += [f"| `{op.name}` | {cell(op.semantics)} | {op.kind} | {op.result} |" for op in OPS.values()]
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
        "- [`kernels.md`](kernels.md) — sin, exp, log, pow and more as intrinsics: strict, relaxed and fast",
        "- [`transcendentals.md`](transcendentals.md) — the exp/sin/cos/log polynomial tiers with "
        "measured ULP and the vector math library calls",
        "",
    ]
    return "\n".join(lines)


def render_kernels() -> str:
    """The math kernel page: the levels, the measured table, and one kernel in full."""
    lines = [
        "# Math kernels — functions as intrinsics (generated, do not edit)",
        "",
        "Every function comes as three C functions built from intrinsics; copy one into the loop's translation "
        "unit and the call disappears. Get them with `python -m alloy.isa kernel <isa> <function> <dtype>`.",
        "",
        "- **strict**: libm's answer on every special input: NaN, infinities, signed zeros, subnormals and huge "
        "arguments are correct, and lanes the vector path cannot hold take one cold branch to scalar libm. Other "
        "inputs are within the listed ulp, which is not lower than `relaxed`'s: strict guarantees the domain.",
        "- **relaxed**: no branch. Holds under the contract below and gives garbage outside it. Pick it when "
        "the inputs are known finite and in range.",
        "- **fast**: `relaxed` at a lower degree, about half the digits. Pick it when the result feeds a "
        "tolerance, an activation, or a first guess.",
        "",
        "`strict` is a compile error under `-ffast-math` or `-fassociative-math`: reassociation undoes its error "
        "compensation; so is every `log1p`, which has no kernel under reassociation: call the library there. The "
        "other `relaxed` and `fast` kernels build under both at up to 2.5 times the listed error. `relaxed` and "
        "`fast` do not preserve the sign of a zero, and a kernel's division may raise FP flags on valid input.",
        "",
        "Inline them only when the loop has other work: the gain over a library call is the call and its spills. "
        "It is not universal: `atan` and AVX2 `sinh` lose to the libraries, and SVML `exp` and `pow` are about even. "
        "All kernels beat scalar libm by 4x to 13x. ULP is the worst sampled error against a wider libm, not a "
        "proven bound.",
        "",
        "| function | dtype | level | ulp | intrinsics (avx512) | branch | contract |",
        "|---|---|---|---:|---:|---|---|",
    ]
    for fn in functions():
        for dtype in DTYPES:
            for level in LEVELS:
                k = kernel(fn, dtype, level)
                branch = "cold" if k.guard else "none"
                count = render_kernel(k, "avx512").intrinsics
                contract = cell(f"any input; vector path for {k.contract}" if level == "strict" else k.contract)
                lines.append(f"| {fn} | {dtype} | {level} | {k.error_ulp:.3g} | {count} | {branch} | {contract} |")
    example = render_kernel(kernel("exp", "f64", "relaxed"), "avx2")
    lines += ["", "## Example: `exp`, f64, relaxed, AVX2", "", "```c", example.source, "```", ""]
    return "\n".join(lines)


def render_transcendentals(table: Table) -> str:
    lines = [
        "# Transcendentals — polynomial tiers with measured ULP (generated, do not edit)",
        "",
        "Error in units of 2^-52 at function scale: max \\|approx - ref\\| / spacing(max(\\|ref\\|, 1.0)) against "
        "double-precision libm on dense grids, so real f64 ulp is up to 2.7x larger and f32 rows get the same f64 "
        "figures. A tier holds on a reduced domain only: `kernel` gives whole functions with true ulp. Recipes are Horner schemes in "
        "abstract-op steps (`fma`/`mul` with inline coefficients) — copyable implementations.",
        "",
        "| tier | op | domain | error (ulp) | error (abs) |",
        "|---|---|---|---|---|",
    ]
    for name, tier in table.approx.items():
        lines.append(f"| `{name}` | {tier.op} | {cell(tier.domain)} | {tier.error_ulp:.4g} | {tier.error_abs:.3g} |")
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
                entry = isa.entries(dtype)[op]
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
        ("kernels", render_kernels()),
        ("transcendentals", render_transcendentals(table)),
        *[(n, render_isa(table, n)) for n in table.isas],
    ]:
        path = out / f"{name}.md"
        path.write_text(content.rstrip() + "\n", encoding="utf-8")
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
