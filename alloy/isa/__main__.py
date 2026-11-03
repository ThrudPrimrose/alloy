# Copyright 2026 ETH Zurich and the Alloy authors.
"""The ISA lookup CLI: ``python -m alloy.isa lookup <isa> <op> <dtype>`` spells an abstract math op,
``reverse <name>`` maps an intrinsic or a disassembly mnemonic back to the op(s) it computes. Cheap
tool calls for an agent: the report and this table replace the ISA PDFs.

Every lookup is numerically validated on the host before it is returned (a small compiled kernel, or
a tier re-measure for transcendentals): on failure the exit code is 3 and the output lists the
potentially relevant spellings instead of endorsing a wrong answer. ``--no-verify`` skips the check;
``validate [isa op dtype]`` runs the gate over everything the host can execute.

``kernel <isa> <function> <dtype>`` returns a math function (sin, exp, log, pow, ...) as intrinsics: a strict, a
relaxed and a fast C function with measured ULP, for the loop to inline instead of a library call."""

import argparse
import dataclasses
import json
import platform
import signal
import sys
from typing import Any

from alloy.isa import ALIASES, OPS, load
from alloy.isa.mathcheck import validate_kernel, validate_kernels
from alloy.isa.mathkernels import ALIASES as FUNCTION_ALIASES
from alloy.isa.mathkernels import LEVELS, functions, libraries, library_function, render, target_of
from alloy.isa.mathkernels import kernel as find
from alloy.isa.schedules import legal, skeleton
from alloy.isa.schedules import verify as verify_skeleton
from alloy.isa.table import ALL_DTYPES, FMA_FORM, Hit, Table, masked_form, normalized, suggestion
from alloy.isa.validate import Verdict, emulated, host_can_run, validate, validate_all


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="alloy.isa",
        description="The machine abstract math ISA and its per-target intrinsic spellings.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    lookup_p = commands.add_parser("lookup", help="op -> intrinsic: lookup <isa> <op> <dtype>")
    lookup_p.add_argument("isa", help="avx2, avx512 (also avx512_256), neon, sve")
    lookup_p.add_argument("op", help=f"one of: {', '.join(OPS)}")
    lookup_p.add_argument("dtype", help="f64, f32, f16, i64 or i32")
    lookup_p.add_argument("--no-verify", action="store_true", help="skip the numerical validation gate")
    lookup_p.add_argument("--level", choices=LEVELS, help="for a math function: one kernel level; default all three")
    lookup_p.add_argument("--json", action="store_true", help="the row and its verdict as JSON")

    reverse_p = commands.add_parser(
        "reverse", help="intrinsic/mnemonic -> op: reverse _mm512_add_pd | vfmadd231pd | fmla | ld1d"
    )
    reverse_p.add_argument("name")
    reverse_p.add_argument("--json", action="store_true", help="the hits as JSON")

    assist_p = commands.add_parser("assist", help="a hardware assist: assist _mm512_scalef_pd | svexpa_f64 | vrcpps")
    assist_p.add_argument("name")

    validate_p = commands.add_parser(
        "validate", help="run the numerical gate: everything the host can execute, or one entry"
    )
    validate_p.add_argument("isa", nargs="?")
    validate_p.add_argument("op", nargs="?")
    validate_p.add_argument("dtype", nargs="?")

    kernel_p = commands.add_parser("kernel", help="sin, exp, log, ... as intrinsics: kernel <isa> <function> <dtype>")
    kernel_p.add_argument("isa", help="avx2, avx512 (also avx512_256), neon, sve")
    kernel_p.add_argument("function", help="sin, cos, tan, exp, exp2, exp10, expm1, log (ln), log2, log10, log1p, ...")
    kernel_p.add_argument("dtype", help="f64 or f32")
    kernel_p.add_argument("--level", choices=LEVELS, help="one level; default all three")
    kernel_p.add_argument("--no-verify", action="store_true", help="skip the numerical validation gate")

    tiers_p = commands.add_parser("tiers", help="a function's polynomial depths, cheapest first: tiers sin")
    tiers_p.add_argument("function", help="sin, cos, exp or log (ln)")
    tiers_p.add_argument("--json", action="store_true", help="one JSON record per depth")

    commands.add_parser("host", help="which ISA and dtype this host runs, so which answers come back verified")
    commands.add_parser("ops", help="the abstract math ISA")
    commands.add_parser("isas", help="the covered vector ISAs and their machine models")
    schedule_p = commands.add_parser("schedule", help="an ISA's legal loop schedules and gen_mask")
    schedule_p.add_argument("isa")
    skeleton_p = commands.add_parser("skeleton", help="the canonical axpy C source: skeleton <isa> <schedule> <dtype>")
    skeleton_p.add_argument("isa")
    skeleton_p.add_argument("schedule")
    skeleton_p.add_argument("dtype")
    skeleton_p.add_argument("--no-verify", action="store_true", help="skip the compile and run against a reference")

    args = parser.parse_args(argv)
    for field in ("isa", "op", "dtype", "function"):
        if isinstance(value := vars(args).get(field), str):
            setattr(args, field, value.lower())
    table = load()
    try:
        return dispatch(table, args)
    except KeyError as exc:
        print(f"alloy.isa: {exc.args[0]}", file=sys.stderr)
        return 2


def dispatch(table: Table, args: argparse.Namespace) -> int:
    """Run the subcommand; its exit code."""
    if args.command == "lookup":
        return lookup_command(table, args)
    if args.command == "kernel":
        return print_kernels(table, args.isa, args.function, args.dtype, args.level, not args.no_verify)
    if args.command == "tiers":
        return tiers_command(table, args)
    if args.command == "validate":
        return validate_command(table, args)
    if args.command == "skeleton":
        return print_skeleton(table, args.isa, args.schedule, args.dtype, not args.no_verify)
    if args.command == "reverse":
        print_hits(table, args.name, args.json)
    elif args.command == "assist":
        print_assists(table, args.name)
    elif args.command == "host":
        print_host(table)
    elif args.command == "ops":
        print_ops()
    elif args.command == "isas":
        print_isas(table)
    elif args.command == "schedule":
        print_schedule(table, args.isa)
    return 0


def refuse_width_knob(isa: str) -> None:
    """``avx512_256`` has no spellings: explicit ``_mm512_*`` intrinsics stay 512-bit under the width knob."""
    if isa in ALIASES:
        raise KeyError(f"{isa}: a compiler width knob with no intrinsics of its own; look up {ALIASES[isa]} or avx2")


def lanes_of(table: Table, isa: str, dtype: str) -> int | str:
    """Lanes per vector, or the runtime query on a length-agnostic ISA."""
    lanes = table.isa(isa).lanes[dtype]
    return lanes or {"f64": "svcntd()", "i64": "svcntd()", "f16": "svcnth()"}.get(dtype, "svcntw()")


def print_entry(table: Table, isa: str, op: str, dtype: str) -> None:
    entry = table.entry(isa, op, dtype)
    print(f"{isa}/{dtype}/{op}: {entry.semantics or OPS[op].semantics}  ({lanes_of(table, isa, dtype)} lanes)")
    if entry.intrinsic:
        print(f"  intrinsic: {entry.intrinsic}{entry.signature}")
    elif entry.recipe:
        print(f"  recipe (no single intrinsic): {' -> '.join(entry.recipe)}")
        print(f"  operands:  {entry.signature}")
        print("  code:      " + ";\n             ".join(entry.code))
    if entry.masked:
        print(f"  masked:    {entry.masked}")
    if entry.mnemonic:
        print(f"  mnemonic:  {entry.mnemonic}")
    for key in entry.approximations:
        tier = table.approx[key]
        print(f"  tier {key}: abs error {tier.error_abs:.3g} ({tier.error_ulp:.4g} f64 units of 2^-52); {tier.domain}")
    for library, call in entry.libraries.items():
        print(f"  {library}: {call}")
    if entry.note:
        print(f"  note:      {entry.note}")


def tiers_command(table: Table, args: argparse.Namespace) -> int:
    """Every polynomial depth of a function, cheapest first, so the caller picks the error it can afford."""
    function = FUNCTION_ALIASES.get(args.function, args.function)
    tiers = sorted(
        ((name, tier) for name, tier in table.approx.items() if tier.op == function),
        key=lambda item: (len(item[1].recipe), -item[1].error_abs),
    )
    if not tiers:
        known = sorted({tier.op for tier in table.approx.values()})
        raise KeyError(f"{args.function!r}: no polynomial tiers; tiers exist for {known}")
    if args.json:
        for name, tier in tiers:
            print(json.dumps({"name": name, "steps": len(tier.recipe), **dataclasses.asdict(tier)}))
        return 0
    print(f"{function}: {len(tiers)} depths; each holds on its domain only, so reduce x first or take `kernel`")
    for name, tier in tiers:
        print(f"{name}: {len(tier.recipe)} steps, abs error {tier.error_abs:.3g}, {tier.domain}")
        print(f"  {'; '.join(tier.recipe)}")
    return 0


def lookup_command(table: Table, args: argparse.Namespace) -> int:
    """One op's entry, then its math kernels when it is a function; a function without an entry has only those. The
    gate runs first, so a failed row is never printed as the answer."""
    refuse_width_knob(args.isa)
    function = FUNCTION_ALIASES.get(args.op, args.op)
    if function not in OPS and function not in functions():
        raise KeyError(
            f"{args.op!r}: neither an abstract op nor a math function{suggestion(args.op, [*OPS, *functions()])}"
        )
    if function in OPS:
        verdict = None if args.no_verify else validate(args.isa, function, args.dtype, table)
        if verdict is not None and verdict.ok is False:
            return report_failure(verdict)
        if args.json:
            row = dataclasses.asdict(table.entry(args.isa, function, args.dtype))
            print(json.dumps({"isa": args.isa, "op": function, "dtype": args.dtype, **row, "verdict": record(verdict)}))
            return 0
        print_entry(table, args.isa, function, args.dtype)
        if verdict is not None:
            print(f"{'verified' if verdict.ok else 'unverified'}: {verdict.basis}; {verdict.detail}".rstrip())
    if function in functions():
        return print_kernels(table, args.isa, function, args.dtype, args.level, not args.no_verify)
    return 0


def record(verdict: Verdict | None) -> dict[str, Any] | None:
    """A verdict for ``--json``."""
    return None if verdict is None else {"ok": verdict.ok, "basis": verdict.basis, "detail": verdict.detail}


def report_failure(verdict: Verdict) -> int:
    """A failed gate on stderr with the candidates it found: exit 3, and no spelling is endorsed."""
    print(f"WARNING: validation FAILED ({verdict.basis}): {verdict.detail}", file=sys.stderr)
    print("potentially relevant spellings (not endorsed: check before use):", file=sys.stderr)
    for hit in verdict.candidates:
        detail = hit.entry.intrinsic or " -> ".join(hit.entry.recipe[:3])
        print(f"  {hit.op} on {hit.isa}/{hit.dtype} ({hit.via}: {detail})", file=sys.stderr)
    return 3


#: How a verdict reads in the C comment under an answer.
MARKS = {True: "verified", None: "unverified", False: "FAILED"}


def print_kernels(table: Table, isa: str, function: str, dtype: str, level: str | None, verify: bool) -> int:
    """The kernels as C. Exit code 3 when one fails its gate."""
    table.isa(isa)
    target = target_of(isa)
    status = 0
    for name in (level,) if level else LEVELS:
        k = find(function, dtype, name)
        spelled = render(k, target)
        branch = "one cold branch to scalar libm" if k.guard else "no branch"
        scope = f"any input; vector path for {k.contract}" if name == "strict" else f"contract: {k.contract}"
        print(f"// {name}: {k.error_ulp:.4g} ulp; {spelled.intrinsics} intrinsics; {branch}; {scope}")
        print(spelled.source)
        for library, call in libraries(function, dtype, target, name).items():
            print(f"// or call {library}: {call}")
        if verify:
            verdict = validate_kernel(k.fn, dtype, name, target)
            print(f"// {MARKS[verdict.ok]}: {verdict.basis}; {verdict.detail}")
            status = 3 if verdict.ok is False else status
        print()
    return status


def validate_one(table: Table, isa: str, op: str, dtype: str) -> int:
    """``validate isa op dtype``."""
    verdict = validate(isa, op, dtype, table)
    mark = "PASS" if verdict.ok else ("SKIP" if verdict.ok is None else "FAIL")
    print(f"{mark} {isa}/{dtype}/{op}: {verdict.basis}; {verdict.detail}")
    for hit in verdict.candidates:
        print(f"  candidate: {hit.op} on {hit.isa}/{hit.dtype} ({hit.via})")
    return 0 if verdict.ok is not False else 3


def validate_everything(table: Table) -> int:
    """Every entry the host can run, every tier and every kernel."""
    results = validate_all(table)
    if platform.machine() in ("x86_64", "aarch64"):
        results += validate_kernels()
    failed = [(ident, v) for ident, v in results if v.ok is False]
    skipped = sum(1 for _, v in results if v.ok is None)
    for ident, verdict in failed:
        print(f"FAIL {ident}: {verdict.detail}")
    ran = len(results) - skipped
    print(
        f"validated {ran} entries, tiers and kernels on this host: {ran - len(failed)} passed, {len(failed)} failed, "
        f"{skipped} not verifiable here"
    )
    return 3 if failed else 0


def validate_command(table: Table, args: argparse.Namespace) -> int:
    """The ``validate`` subcommand: one entry, or everything."""
    given = (args.isa, args.op, args.dtype)
    if all(given):
        return validate_one(table, args.isa, args.op, args.dtype)
    if any(given):
        print("alloy.isa: validate takes either no arguments or isa op dtype", file=sys.stderr)
        return 2
    return validate_everything(table)


def operand_rule(token: str) -> str:
    """An fma form's formula in Intel operand order: the digits name which registers multiply."""
    m = FMA_FORM.match(token.lower())
    if m is None:
        return ""
    product, added = {
        "132": ("dest*src3", "src2"),
        "213": ("src2*dest", "src3"),
        "231": ("src2*src3", "dest"),
    }.get(token.lower()[len(m.group(1)) :][:3], ("a*b", "c"))
    negated, sign = {"vfmadd": ("", "+"), "vfmsub": ("", "-"), "vfnmadd": ("-", "+"), "vfnmsub": ("-", "-")}[m.group(1)]
    return f"dest = {negated}{product} {sign} {added}"


def hit_text(name: str, hit: Hit) -> str:
    """One hit's line; a step of a composite never claims the composite's math."""
    if hit.via == "step":
        return f"{name} may be one step of {hit.op} on {hit.isa}/{hit.dtype} ({hit.entry.mnemonic})"
    detail = {
        "intrinsic": hit.entry.intrinsic,
        "masked": hit.entry.masked,
        "recipe": " -> ".join(hit.entry.recipe),
        "library": name,
        "mnemonic": hit.entry.mnemonic,
    }[hit.via]
    semantics = f"\n  {hit.entry.semantics}" if hit.entry.semantics else ""
    return f"{name} = {hit.op} on {hit.isa}/{hit.dtype} ({hit.via}: {detail}){semantics}"


def print_hits(table: Table, name: str, as_json: bool = False) -> None:
    hits = table.reverse(name)
    token = normalized(name)
    if as_json:
        print(json.dumps([{"isa": h.isa, "dtype": h.dtype, "op": h.op, "via": h.via} for h in hits]))
        return
    if hits:
        if masked_form(token) != token:
            print(f"{token}: indexed as {masked_form(token)}; the activity policy decides the inactive lanes")
        if rule := operand_rule(token):
            print(f"{token}: {rule}")
        for hit in hits:
            print(hit_text(name, hit))
    elif table.assist(name):
        print_assists(table, name)
    elif (found := library_function(token)) is not None:
        print(f"{token} = {found[0]} ({found[1]}) on {found[2]}: a vector math library call")
    else:
        known = [*table.by_intrinsic, *table.by_mnemonic, *table.by_assist]
        raise KeyError(
            f"{name!r}: neither an intrinsic, mnemonic nor library call in the table{suggestion(token, known)}"
        )


def print_assists(table: Table, name: str) -> None:
    hits = table.assist(name)
    if not hits:
        known = [*table.by_assist]
        raise KeyError(f"{name!r}: neither an assist intrinsic nor an assist mnemonic{suggestion(name, known)}")
    for hit in hits:
        a = hit.assist
        print(f"{name} = {a.name} on {hit.isa}: helps {a.helps} ({a.mnemonic})")
        print(f"  {a.note}")


def print_host(table: Table) -> None:
    """Which ISA and dtype this host executes; everything else comes back unverified."""
    print(f"host: {platform.machine()}")
    for name, isa in table.isas.items():
        runs = [dtype for dtype in ALL_DTYPES if isa.entries(dtype) and host_can_run(name, dtype)]
        if not runs and emulated(name):
            print(f"  {name}: runs under qemu")
            continue
        print(f"  {name}: {'runs ' + ' '.join(runs) if runs else 'does not run here; answers stay unverified'}")


def print_ops() -> None:
    for op in OPS.values():
        print(f"{op.name:12} {op.symbol:10} {op.kind:12} -> {op.result:6} {op.semantics}")


def print_isas(table: Table) -> None:
    for name, isa in table.isas.items():
        mask = "opmask/predicate" if isa.mask else "no predication"
        print(f"{name:8} {isa.title}  [{mask}; schedules: {', '.join(isa.schedules)}]")
        print(f"  {isa.note}")


def print_schedule(table: Table, isa: str) -> None:
    target = table.isa(isa)
    runnable = host_can_run(isa, "f64")
    print(f"{isa}: {target.title}")
    print(f"  gen_mask:  {target.gen_mask or 'unsupported (no predication)'}")
    print(f"  {target.note}\n")
    for name, info in table.schedule_info.items():
        why = legal(isa, name, table)
        mark = f"refused: {why}" if why else ("LEGAL" if runnable else "LEGAL, not runnable here")
        print(f"  {name}: {info.title} — {info.tail}  [{mark}]")
        print(f"      {info.description}")
        if info.gcc:
            print(f"      gcc:   {info.gcc}")
        if info.clang:
            print(f"      clang: {info.clang}")


def print_skeleton(table: Table, isa: str, schedule: str, dtype: str, verify: bool) -> int:
    print(skeleton(table, isa, schedule, dtype))
    if verify:
        verdict = verify_skeleton(isa, schedule, dtype, table)
        print(f"// {MARKS[verdict.ok]}: {verdict.basis}; {verdict.detail}")
        if verdict.ok is False:
            return 3
    return 0


if __name__ == "__main__":
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    sys.exit(main())
