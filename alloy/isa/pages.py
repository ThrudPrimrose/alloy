# Copyright 2026 ETH Zurich and the Alloy authors.
"""The text of the Tensix and SoftHier answers: ``lookup tensix|softhier <op> <dtype>`` prints the lines of the rows
it picks, and ``ask`` its feasible or refused answers, through the functions here."""

from collections.abc import Sequence

from alloy.isa import OPS, ask, softhier, tensix, tensix_harness

__all__ = ["checked", "feasible_lines", "refusal_lines", "softhier_row_lines", "softhier_tail", "tensix_row_lines",
           "tensix_rung_lines", "tensix_target_note", "tensix_title"]  # fmt: skip


#: The tt-metal spelling of the card the eval runs on (Daisytuner Blackhole, tt-metal 0.63).
CARD_VERSION = "v06"


def tensix_title(dtypes: str, op: str) -> str:
    return f"tensix/{dtypes}/{op}: {OPS[op].semantics if op in OPS else op}, applied to a 32x32 tile"


def tensix_verdict_line(row: tensix.Row, verdict: tensix.Verdict | None, label: str) -> str:
    """One run of ``row``: the platform it ran on and its error; ``label`` names the dtype on a page."""
    said = f"{label}: " if label else ""
    if verdict is None:
        return f"    {said}unverified: no recorded run"
    if not verdict.ok:
        return f"    {said}FAILED on ttsim: {verdict.error[:200]}"
    # The ttsim run uses tt-metal 0.8x, so a row with per-version spellings is verified in its [v08] one only.
    which = "" if isinstance(row.init, str) and isinstance(row.call, str) else ", the [v08] spelling only"
    ttsim = tensix.recorded().get("ttsim", "").split(" ")[0]
    return (
        f"    {said}verified on ttsim {ttsim} (simulated Blackhole) with tt-metal 0.8x{which}: "
        f"max rel error {verdict.rel:.2g}"
    )


def tensix_row_lines(row: tensix.Row, runs: Sequence[tuple[str, tensix.Verdict | None]], dtype: str = "") -> list[str]:
    """A row's unit, includes per tt-metal version, init and call, its runs (label, verdict) and its note; a run's
    label is its dtype on a page, and empty in a lookup, which names the ``dtype``."""
    lines = [f"  {row.unit} ({row.kind}): header {row.header}"]
    fields = {"kind": row.kind, "header": row.header}
    # Only the card's tt-metal (0.63, the [v06] spelling): two versions side by side misled agents (owner, 11-19).
    compute = " ".join(f'#include "{h}"' for h in tensix_harness.compute_headers(fields, False))
    lines.append(f'    includes compute: {compute}; reader/writer: #include "{tensix_harness.dataflow_include(False)}"')
    for name, value in (("init", row.init), ("call", row.call)):
        lines.append(f"    {name}: {value if isinstance(value, str) else value[CARD_VERSION]}")
    lines += [tensix_verdict_line(row, verdict, label) for label, verdict in runs]
    for label, _ in runs:  # the card-0.63 measurement beside the ttsim run, where a probe measured the row
        if card := tensix.card_line(row, label or dtype):
            lines.append(card.replace("    measured", f"    {label}: measured", 1) if label else card)
    if row.note:
        lines.append(f"    note: {row.note}")
    return lines


def tensix_rung_lines(rung: tensix.Rung) -> list[str]:
    """An SFPI math kernel: its card-measured error, the calls that run it, its note and its whole code."""
    lines = [
        f"  SFPU math kernel {rung.name}: {rung.error_ulp:.3g} ulp, measured on the card ({rung.card})",
        f"    init: {rung.init}",
        f"    call: {rung.call}",
        f"    note: {rung.note}",
        "    code:",
    ]
    return lines + [f"      {line}" for line in rung.code.splitlines()]


def tensix_target_note() -> str:
    return f"  note: {tensix.table()['target']['note']}"


def softhier_row_lines(row: softhier.Row, title: str, spelled_as: str, verdict: softhier.Verdict | None) -> list[str]:
    """A SoftHier row under ``title`` (``softhier/<dtype>/<op>``): its call, its GVSoC run, its note and its code."""
    lines = [f"{title}: {row.key()} on {row.unit}: {softhier.spelled(row.call, spelled_as)}"]
    if verdict is None:
        lines.append("  unverified: no current GVSoC run")
    elif verdict.ok:
        inside = f" (inside the {row.checked_by} program)" if row.checked_by else ""
        error = f": max rel error {verdict.rel:.2g}" if verdict.rel else ""
        lines.append(f"  verified on GVSoC {softhier.TARGET}{inside}{error}")
    else:
        lines.append(f"  FAILED on GVSoC: {verdict.error[:200]}")
    if row.note:
        lines.append(f"  note: {row.note}")
    return [*lines, *softhier.code(row, spelled_as).splitlines(), ""]  # the blank line ends the code


def softhier_tail() -> list[str]:
    return [f"build: {softhier.build_line()}", f"note: {softhier.table()['target']['note']}"]


def refusal_lines(title: str, answer: ask.Infeasible | ask.Invalid) -> list[str]:
    near = answer.nearest if isinstance(answer, ask.Infeasible) else answer.expected
    word = "nearest" if isinstance(answer, ask.Infeasible) else "expected"
    lines = [f"{title}: {answer.status} ({answer.why.value}): {answer.reason}", *(f"  {word}: {n}" for n in near)]
    if isinstance(answer, ask.Infeasible) and answer.block:
        lines.append(f"  block: {'x'.join(map(str, answer.block))} (a shape the target takes is a whole multiple)")
    if isinstance(answer, ask.Infeasible) and answer.fix:
        lines.append(f"  fix: {answer.fix}")
    return lines


def checked(check: ask.Check) -> str:
    """The check as one phrase; a basis that starts with its status ("compiled for gfx942") is not repeated."""
    said = check.basis.split(" ", 1)[0] in (check.status, "ran")  # "compiled for ...", "ran on ..."
    return check.basis if said else f"{check.status} {check.basis}".rstrip()


def feasible_lines(title: str, answer: ask.Feasible) -> list[str]:
    lines = [f"{title}: feasible on {answer.unit}; check: {checked(answer.check)}"]
    lines += [
        f"  {s.count} x {s.unit}: {s.spelling}" if s.count > 1 else f"  {s.unit}: {s.spelling}" for s in answer.steps
    ]
    lines += [f"  setup {key}: {value}" for key, value in answer.setup.items()]
    lines += [f"  note: {note}" for note in answer.notes]
    if answer.completion is not None:
        done = answer.completion
        fences = f"; before it: {', '.join(done.fences)}" if done.fences else ""
        lines.append(f"  async: completes on {done.token}: {done.wait}{fences}")
    return [*lines, answer.code]
