# Copyright 2026 ETH Zurich and the Alloy authors.
"""The ISA lookup CLI: ``python -m alloy.isa lookup <isa> <op> <dtype>`` spells an abstract math op,
``reverse <name>`` maps an intrinsic or a disassembly mnemonic back to the op(s) it computes. Cheap
tool calls for an agent: the report and this table replace the ISA PDFs.

Every lookup is numerically validated on the host before it is returned (a small compiled kernel, or
a tier re-measure for transcendentals): on failure the exit code is 3 and the output lists the
potentially relevant spellings instead of endorsing a wrong answer. ``--no-verify`` skips the check;
``validate [isa op dtype]`` runs the gate over everything the host can execute."""

import argparse
import sys

from alloy.isa import ALIASES, OPS, load


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

    reverse_p = commands.add_parser(
        "reverse", help="intrinsic/mnemonic -> op: reverse _mm512_add_pd | vfmadd231pd | fmla | ld1d"
    )
    reverse_p.add_argument("name")

    validate_p = commands.add_parser(
        "validate", help="run the numerical gate: everything the host can execute, or one entry"
    )
    validate_p.add_argument("isa", nargs="?")
    validate_p.add_argument("op", nargs="?")
    validate_p.add_argument("dtype", nargs="?")

    commands.add_parser("ops", help="the abstract math ISA")
    commands.add_parser("isas", help="the covered vector ISAs and their machine models")
    schedule_p = commands.add_parser("schedule", help="an ISA's legal loop schedules and gen_mask")
    schedule_p.add_argument("isa")
    skeleton_p = commands.add_parser("skeleton", help="the canonical axpy C source: skeleton <isa> <schedule> <dtype>")
    skeleton_p.add_argument("isa")
    skeleton_p.add_argument("schedule")
    skeleton_p.add_argument("dtype")
    skeleton_p.add_argument(
        "--verify", action="store_true", help="compile and run the skeleton against a scalar reference"
    )

    args = parser.parse_args(argv)
    table = load()
    try:
        if args.command == "lookup":
            _print_entry(table, args.isa, args.op, args.dtype)
            if not args.no_verify:
                return _verify(table, args.isa, args.op, args.dtype)
        elif args.command == "reverse":
            _print_hits(table, args.name)
        elif args.command == "validate":
            return _validate_cmd(table, args)
        elif args.command == "ops":
            _print_ops()
        elif args.command == "isas":
            _print_isas(table)
        elif args.command == "schedule":
            _print_schedule(table, args.isa)
        elif args.command == "skeleton":
            _print_skeleton(table, args.isa, args.schedule, args.dtype, args.verify)
    except KeyError as exc:
        print(f"alloy.isa: {exc.args[0]}", file=sys.stderr)
        return 2
    return 0


def _print_entry(table, isa: str, op: str, dtype: str) -> None:
    target, entry, abstract = table.isa(isa), table.entry(isa, op, dtype), OPS.get(op)
    if abstract is None:
        raise KeyError(f"{op!r}: unknown op (one of: {', '.join(OPS)})")
    lanes = target.lanes[dtype] or f"svcnt{'d' if dtype == 'f64' else 'w'}()"
    print(f"{isa}/{dtype}/{op}: {abstract.semantics}  ({lanes} lanes)")
    if isa in ALIASES:
        width = "256" if isa == "avx512_256" else "128"
        print(f"  note:      {isa} is {ALIASES[isa]} at {width} bits: same intrinsics, half the lanes")
    if entry.intrinsic:
        print(f"  intrinsic: {entry.intrinsic}{entry.signature}")
    elif entry.recipe:
        print(f"  recipe (no single intrinsic): {' -> '.join(entry.recipe)}")
    if entry.masked:
        print(f"  masked:    {entry.masked}")
    if entry.mnemonic:
        print(f"  mnemonic:  {entry.mnemonic}")
    for key in entry.approximations:
        tier = table.approx[key]
        print(f"  tier {key}: {tier.error_ulp:.4g} ulp (abs {tier.error_abs:.3g}); {tier.domain}")
    for library, call in entry.libraries.items():
        print(f"  {library}: {call}")
    if entry.note:
        print(f"  note:      {entry.note}")


def _verify(table, isa: str, op: str, dtype: str) -> int:
    """The numerical gate on a lookup: print the verdict; on failure list the candidates and exit 3."""
    from alloy.isa.validate import validate  # noqa: PLC0415 -- compiles only when verifying

    verdict = validate(isa, op, dtype, table)
    if verdict.ok is True:
        print(f"verified:  {verdict.basis}; {verdict.detail}")
        return 0
    if verdict.ok is None:
        print(f"unverified: {verdict.basis}")
        return 0
    print(f"WARNING: validation FAILED ({verdict.basis}): {verdict.detail}", file=sys.stderr)
    print("potentially relevant spellings (not endorsed — check before use):", file=sys.stderr)
    for hit in verdict.candidates:
        detail = hit.entry.intrinsic or " -> ".join(hit.entry.recipe[:3])
        print(f"  {hit.op} on {hit.isa}/{hit.dtype} ({hit.via}: {detail})", file=sys.stderr)
    return 3


def _validate_cmd(table, args) -> int:
    """The ``validate`` subcommand: one entry, or every entry the host can run plus every tier."""
    from alloy.isa.validate import validate, validate_all  # noqa: PLC0415

    if args.isa or args.op or args.dtype:
        if not (args.isa and args.op and args.dtype):
            print("alloy.isa: validate takes either no arguments or isa op dtype", file=sys.stderr)
            return 2
        verdict = validate(args.isa, args.op, args.dtype, table)
        mark = "PASS" if verdict.ok else ("SKIP" if verdict.ok is None else "FAIL")
        print(f"{mark} {args.isa}/{args.dtype}/{args.op}: {verdict.basis}; {verdict.detail}")
        for hit in verdict.candidates:
            print(f"  candidate: {hit.op} on {hit.isa}/{hit.dtype} ({hit.via})")
        return 0 if verdict.ok is not False else 3
    results = validate_all(table)
    failed = [(ident, v) for ident, v in results if v.ok is False]
    skipped = [(ident, v) for ident, v in results if v.ok is None]
    for ident, verdict in results:
        if verdict.ok is False:
            print(f"FAIL {ident}: {verdict.detail}")
    print(
        f"validated {len(results) - len(skipped)} entries and tiers on this host: "
        f"{len(results) - len(skipped) - len(failed)} passed, {len(failed)} failed, "
        f"{len(skipped)} not verifiable here"
    )
    return 1 if failed else 0


def _print_hits(table, name: str) -> None:
    hits = table.reverse(name)
    if not hits:
        raise KeyError(f"{name!r}: neither an intrinsic, mnemonic nor library call in the table")
    for hit in hits:
        detail = {
            "intrinsic": hit.entry.intrinsic,
            "masked": hit.entry.masked,
            "recipe": " -> ".join(hit.entry.recipe),
            "library": name,
        }.get(hit.via, hit.entry.intrinsic)
        print(f"{name} = {hit.op} on {hit.isa}/{hit.dtype} ({hit.via}: {detail})")
        if hit.entry.semantics:
            print(f"  {hit.entry.semantics}")


def _print_ops() -> None:
    for op in OPS.values():
        print(f"{op.name:12} {op.symbol:10} {op.kind:12} -> {op.result:6} {op.semantics}")


def _print_isas(table) -> None:
    for name, isa in table.isas.items():
        mask = "opmask/predicate" if isa.mask else "no predication"
        print(f"{name:8} {isa.title}  [{mask}; schedules: {', '.join(isa.schedules)}]")
        print(f"  {isa.note}")


def _print_schedule(table, isa: str) -> None:
    from alloy.isa.schedules import legal  # noqa: PLC0415

    target = table.isa(isa)
    print(f"{isa}: {target.title}")
    print(f"  gen_mask:  {target.gen_mask or 'unsupported (no predication)'}")
    print(f"  {target.note}\n")
    for name, info in table.schedule_info.items():
        why = legal(isa, name, table)
        mark = "LEGAL" if not why else f"refused: {why}"
        print(f"  {name}: {info.title} — {info.tail}  [{mark}]")
        print(f"      {info.description}")
        if info.gcc:
            print(f"      gcc:   {info.gcc}")
        if info.clang:
            print(f"      clang: {info.clang}")


def _print_skeleton(table, isa: str, schedule: str, dtype: str, verify: bool = False) -> None:
    from alloy.isa.schedules import skeleton  # noqa: PLC0415
    from alloy.isa.schedules import verify as verify_skeleton

    try:
        print(skeleton(table, isa, schedule, dtype))
        if verify:
            verdict = verify_skeleton(isa, schedule, dtype, table)
            mark = "verified" if verdict.ok else ("unverified" if verdict.ok is None else "FAILED")
            print(f"// {mark}: {verdict.basis}; {verdict.detail}")
    except KeyError as exc:
        raise KeyError(exc.args[0]) from None


if __name__ == "__main__":
    sys.exit(main())
